#!/usr/bin/env python3
"""Backfill WHOOP history from the manual "Download my data" export (CSV bundle).

WHOOP's data export merges cycle + sleep + recovery into one row per physiological cycle
(physiological_cycles.csv), with workouts in a separate file. This importer maps each daily
row into the SAME immutable per-day raw envelope the API pull writes — so history and the
ongoing feed share one storage shape and one adapter.

It is idempotent and API-friendly: a day already written by the API pull is left untouched
(the richer API envelope wins); only missing days are filled from the export.

    python whoop_import_export.py --bundle ~/Downloads/whoop_export
    python whoop_import_export.py --bundle export.zip --dry-run

`--bundle` may be a directory or a .zip of the export.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
RAW_DIR = REPO / "00-Raw" / "Wearables" / "whoop"
ENVELOPE_SCHEMA = "whoop-export/v1"

CYCLES_FILE_HINTS = ("physiological_cycles", "cycles")
WORKOUTS_FILE_HINTS = ("workouts",)
# Column headers (lowercased substrings) used to find the day's date in an export row.
DATE_HINTS = ("cycle start time", "cycle start", "start time", "date")


def _load_csvs(bundle: Path) -> dict[str, list[dict]]:
    """Return {logical_name: rows} for the cycle + workout CSVs in the bundle."""
    tables: dict[str, list[dict]] = {}

    def classify(name: str) -> str | None:
        low = name.lower()
        if any(h in low for h in CYCLES_FILE_HINTS):
            return "cycles"
        if any(h in low for h in WORKOUTS_FILE_HINTS):
            return "workouts"
        return None

    if bundle.is_file() and bundle.suffix.lower() == ".zip":
        with zipfile.ZipFile(bundle) as zf:
            for info in zf.infolist():
                kind = classify(info.filename) if info.filename.lower().endswith(".csv") else None
                if kind:
                    text = zf.read(info).decode("utf-8-sig", errors="replace")
                    tables[kind] = list(csv.DictReader(io.StringIO(text)))
    else:
        for path in bundle.rglob("*.csv"):
            kind = classify(path.name)
            if kind:
                tables[kind] = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    return tables


def _row_date(row: dict) -> str | None:
    for header, value in row.items():
        if header and any(h in header.lower() for h in DATE_HINTS) and value:
            raw = str(value).strip()
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    return dt.datetime.strptime(raw[:len(fmt) + 6], fmt).date().isoformat()
                except ValueError:
                    continue
            # Last resort: leading ISO date.
            if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
                return raw[:10]
    return None


def _day_path(date: str) -> Path:
    return RAW_DIR / date[:4] / f"{date}.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bundle", required=True, type=Path, help="Export directory or .zip.")
    ap.add_argument("--dry-run", action="store_true", help="Report only; no files written.")
    ap.add_argument("--overwrite", action="store_true",
                    help="Overwrite existing day files (default: keep richer API envelopes).")
    args = ap.parse_args()

    if not args.bundle.exists():
        print(f"Bundle not found: {args.bundle}", file=sys.stderr)
        return 2

    tables = _load_csvs(args.bundle)
    if "cycles" not in tables:
        print("No physiological_cycles CSV found in the bundle.", file=sys.stderr)
        return 2

    # Group workouts by their start date so they can be attached to the day envelope.
    workouts_by_day: dict[str, list[dict]] = {}
    for w in tables.get("workouts", []):
        date = _row_date(w)
        if date:
            workouts_by_day.setdefault(date, []).append({"row": w})

    written = skipped = 0
    for row in tables["cycles"]:
        date = _row_date(row)
        if not date:
            continue
        path = _day_path(date)
        if path.exists() and not args.overwrite:
            skipped += 1
            continue
        envelope = {
            "schema": ENVELOPE_SCHEMA, "source": "whoop", "date": date,
            "imported_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "row": row,
            "workouts": workouts_by_day.get(date, []),
        }
        if args.dry_run:
            print(f"  would write {path.relative_to(REPO)}")
            written += 1
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(envelope, indent=2, sort_keys=True), encoding="utf-8")
        written += 1

    print(f"Done. {written} day(s) {'to write' if args.dry_run else 'written'}, "
          f"{skipped} already present (kept).")
    print(f"Raw dir: {RAW_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
