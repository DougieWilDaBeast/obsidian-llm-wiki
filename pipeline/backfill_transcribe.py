#!/usr/bin/env python3
"""Backfill voice transcription.

Scans audio folders, de-duplicates, denoises (ffmpeg afftdn), and transcribes
(faster-whisper) into Whisper transcript files under 00-Raw/Voice/.

This script deliberately does NOT run the agent ingest. Transcription is free
(local); ingest may cost API credits, so it is a separate, cost-managed step.

The repo location is taken from $VAULT_ROOT (default: the repo this file lives in).
The ledger and default audio sources live under $HOME; override with flags/env.

Usage:
    # Inventory only — no transcription, no writes:
    python pipeline/backfill_transcribe.py --dry-run

    # Transcribe everything not already in the ledger:
    python pipeline/backfill_transcribe.py

    # Limit / pick model:
    python pipeline/backfill_transcribe.py --limit 5 --model small
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Repo root: $VAULT_ROOT if set, else two levels up from this file.
REPO = Path(os.environ.get("VAULT_ROOT", Path(__file__).resolve().parent.parent))
VOICE_OUT = REPO / "00-Raw" / "Voice"
LEDGER = Path(os.environ.get("WHISPER_LEDGER", Path.home() / ".local" / "state" / "llm-wiki" / "ledger.json"))

DEFAULT_SOURCES = [
    Path.home() / "VoiceRecordings" / "Voice Recorder",
]

AUDIO_EXTS = {".m4a", ".wav", ".mp3", ".ogg", ".opus", ".aac", ".flac"}
# Folders whose contents are skipped entirely (known dupes / pipeline output).
# Exact-match set, plus any folder whose name contains 'processed' (e.g.
# 'Processed', 'm4aProcessed') is skipped — those hold already-transcribed audio.
SKIP_DIR_NAMES = {"duplicates", ".stfolder", ".stversions"}
# Prefer original recordings over derived formats when the same note exists twice.
EXT_PRIORITY = {".m4a": 0, ".flac": 1, ".wav": 2, ".mp3": 3, ".ogg": 4, ".opus": 5, ".aac": 6}

DENOISE_FILTER = "afftdn=nf=-25,highpass=f=80,lowpass=f=8000"


def sha256(path: Path, buf: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(buf):
            h.update(chunk)
    return h.hexdigest()


def load_ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {}


def save_ledger(d: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    tmp = LEDGER.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(LEDGER)


def norm_name(p: Path) -> str:
    """Dedup key: stem without extension and without a trailing ' (N)' suffix."""
    stem = re.sub(r"\s*\(\d+\)\s*$", "", p.stem)
    return stem.strip()


def parse_recorded(stem: str):
    """Parse 'Voice 251026_092634' -> datetime(2025-10-26 09:26:34)."""
    m = re.search(r"(\d{6})_(\d{6})", stem)
    if not m:
        return None
    try:
        return dt.datetime.strptime(m.group(1) + m.group(2), "%y%m%d%H%M%S")
    except ValueError:
        return None


def gather(src_dirs: list[Path]) -> list[Path]:
    files: list[Path] = []
    for d in src_dirs:
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in AUDIO_EXTS:
                continue
            parts = [part.lower() for part in p.parts]
            if SKIP_DIR_NAMES & set(parts):
                continue
            if any("processed" in part for part in parts):
                continue
            # Skip dotfiles, incl. Android '.trashed-*' (deleted) and sync temp files.
            if p.name.startswith("."):
                continue
            files.append(p)
    return files


def dedup(files: list[Path]) -> dict[str, Path]:
    """Collapse same-note duplicates by normalized name, preferring originals."""
    best: dict[str, Path] = {}
    for p in files:
        key = norm_name(p).lower()
        cur = best.get(key)
        if cur is None:
            best[key] = p
            continue
        # Lower priority number wins; tie-break on shallower path then shorter name.
        pk = (EXT_PRIORITY.get(p.suffix.lower(), 9), len(p.parts), len(p.name))
        ck = (EXT_PRIORITY.get(cur.suffix.lower(), 9), len(cur.parts), len(cur.name))
        if pk < ck:
            best[key] = p
    return best


def denoise(src: Path, dst: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
         "-af", DENOISE_FILTER, "-ar", "16000", "-ac", "1", str(dst)],
        check=True,
    )


def write_transcript(stem: str, src: Path, text: str, recorded, duration: float, model: str) -> Path:
    VOICE_OUT.mkdir(parents=True, exist_ok=True)
    out = VOICE_OUT / f"{stem}.md"
    rec = recorded.isoformat() if recorded else "unknown"
    fm = (
        "---\n"
        "type: voice-transcript\n"
        f"source_audio: {src.name}\n"
        f"recorded: {rec}\n"
        f"transcribed: {dt.date.today().isoformat()}\n"
        f"model: faster-whisper-{model}\n"
        f"duration_s: {int(duration)}\n"
        "---\n\n"
    )
    out.write_text(fm + text.strip() + "\n", encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", nargs="*", type=Path, default=DEFAULT_SOURCES,
                    help="Audio source directories (scanned recursively).")
    ap.add_argument("--model", default="small", help="faster-whisper model size.")
    ap.add_argument("--dry-run", action="store_true", help="Inventory only; no transcription or writes.")
    ap.add_argument("--limit", type=int, default=0, help="Process at most N recordings (0 = all).")
    ap.add_argument("--move-processed", action="store_true",
                    help="After transcribing, move the source audio into a sibling 'Processed/' folder.")
    args = ap.parse_args()

    files = gather(args.sources)
    unique = dedup(files)
    ledger = load_ledger()

    print(f"Sources scanned : {len(args.sources)}")
    print(f"Audio files found: {len(files)}")
    print(f"Unique notes     : {len(unique)} (after name-dedup, duplicates/ excluded)")
    print(f"Already in ledger: {sum(1 for p in unique.values() if sha256(p) in ledger) if not args.dry_run else '(skipped hashing in dry-run)'}")

    todo = sorted(unique.values(), key=lambda p: (parse_recorded(norm_name(p)) or dt.datetime.min))

    if args.dry_run:
        print("\n-- Sample of unique notes (first 15) --")
        for p in todo[:15]:
            rec = parse_recorded(norm_name(p))
            print(f"  {rec.isoformat() if rec else 'unknown-date':19}  {p.name}")
        print("\nDry run only — nothing transcribed. Re-run without --dry-run to process.")
        return 0

    from faster_whisper import WhisperModel  # imported lazily so --dry-run needs no deps
    print(f"\nLoading model '{args.model}' (cpu/int8)…")
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    done = 0
    skipped = 0
    for p in todo:
        if args.limit and done >= args.limit:
            break
        digest = sha256(p)
        if digest in ledger:
            skipped += 1
            continue
        stem = norm_name(p)
        recorded = parse_recorded(stem)
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
                denoise(p, Path(tmp.name))
                segments, info = model.transcribe(tmp.name, language="en", vad_filter=True)
                text = "".join(s.text for s in segments).strip()
            out = write_transcript(stem, p, text, recorded, info.duration, args.model)
        except Exception as exc:  # noqa: BLE001 - log and continue the batch
            print(f"  ERROR {p.name}: {exc}", file=sys.stderr)
            continue
        ledger[digest] = {
            "source_audio": str(p),
            "transcript": str(out.relative_to(REPO)),
            "recorded": recorded.isoformat() if recorded else None,
            "transcribed": dt.date.today().isoformat(),
            "chars": len(text),
        }
        save_ledger(ledger)
        done += 1
        print(f"  [{done}] {stem}  ({int(info.duration)}s, {len(text)} chars)")

        if args.move_processed:
            proc = p.parent / "Processed"
            proc.mkdir(exist_ok=True)
            target = proc / p.name
            if target.exists():
                target = proc / f"{p.stem}__{digest[:8]}{p.suffix}"
            try:
                p.replace(target)
                print(f"      moved audio -> {target}")
            except OSError as exc:  # noqa: BLE001 - keep going; ledger already recorded it
                print(f"      WARN could not move {p.name}: {exc}", file=sys.stderr)

    print(f"\nDone. Transcribed {done}, skipped {skipped} already-in-ledger.")
    print(f"Transcripts in: {VOICE_OUT}")
    print(f"Ledger        : {LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
