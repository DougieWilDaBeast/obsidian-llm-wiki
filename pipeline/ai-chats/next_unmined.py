#!/usr/bin/env python3
"""AI-Chats Stage B — dump chosen (or top-N unmined) conversations' HUMAN turns.

The token-saver for the `ai-chat-mine` skill: instead of opening each archive .md, dump ONLY the
author's turns for the conversations you're about to mine. Stage B needs the human side only — the
model's turns are quarantined (CLAUDE.md §8a), not mined. Pairs with shortlist.py (the ranker) and
mined.txt (progress).

Reads the harvest written by extract_human.py (.out/human_turns.jsonl), which is git-ignored and
lives wherever you ran extract_human.py (e.g. your server) — run this there:

    python3 pipeline/ai-chats/next_unmined.py --ids 1a2b3c4d,5e6f7a8b
    python3 pipeline/ai-chats/next_unmined.py --top 6        # top unmined by #user-turns

Args:
  --ids CSV    dump exactly these 8-char conversation ids (order preserved), even if mined
  --top N      otherwise, top N UNMINED conversations by #user-turns (default 6)
  --min-turns  skip convos with fewer than this many user turns (default 6; ignored with --ids)
  --max-chars  truncate each printed turn to this many chars (default 1200; 0 = no limit)
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARVEST = HERE / ".out" / "human_turns.jsonl"
MINED = HERE / "mined.txt"

# utility/low-signal titles to skip in the heuristic (not when --ids is given)
UTIL_RE = re.compile(
    r"\b(n8n|error|errors|bug|debug|install|config|ufw|ollama|docker|npm|git|syntax|traceback|"
    r"deploy|regex|stack trace|compile|css|sql)\b",
    re.I,
)


def mined_ids() -> set[str]:
    out: set[str] = set()
    if MINED.exists():
        for ln in MINED.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                out.add(ln.split()[0][:8])
    return out


def load() -> list[dict]:
    if not HARVEST.exists():
        raise SystemExit(f"error: {HARVEST} missing — run extract_human.py first.")
    with HARVEST.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--min-turns", type=int, default=6)
    ap.add_argument("--max-chars", type=int, default=1200)
    a = ap.parse_args()

    rows = load()
    done = mined_ids()
    want = [x.strip()[:8] for x in a.ids.split(",") if x.strip()]

    if want:
        by_id = {(r.get("id") or "")[:8]: r for r in rows}
        picked = [by_id[i] for i in want if i in by_id]
        missing = [i for i in want if i not in by_id]
        if missing:
            print(f"# WARNING: ids not found in harvest: {', '.join(missing)}")
    else:
        cand = [
            r
            for r in rows
            if (r.get("id") or "")[:8] not in done
            and r.get("n_user_turns", 0) >= a.min_turns
            and not UTIL_RE.search(r.get("title") or "")
        ]
        cand.sort(key=lambda r: r.get("n_user_turns", 0), reverse=True)
        picked = cand[: a.top]

    for r in picked:
        cid = (r.get("id") or "")[:8]
        print("=" * 72)
        print(f"[{cid}] {r.get('date', '')} · {r.get('source', '')} · {r.get('n_user_turns', 0)} user turns · {r.get('n_questions', 0)} Qs")
        print(f"TITLE: {r.get('title', '')}")
        print(f"PATH:  {r.get('path', '')}")
        print("-" * 72)
        for i, t in enumerate(r.get("user_turns", [])):
            txt = (t.get("text") or "").strip()
            if not txt:
                continue
            if a.max_chars and len(txt) > a.max_chars:
                txt = txt[: a.max_chars] + " …[trunc]"
            print(f"  ({i}) {txt}")
        print()

    print(f"# dumped {len(picked)} conversation(s); mined so far: {len(done)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
