#!/usr/bin/env python3
"""AI-Chats Stage B — rank conversations by how worth-mining they are.

Phase 3 needs a worklist: which of the (often thousands of) conversations are
genuinely reflective (worldview / self / career / design / insight) versus utility
chatter (error messages, installs, quick fixes). This scores every conversation with a fast,
free heuristic over the AUTHOR's turns and emits a ranked worklist, marking the
ones already deep-mined (pipeline/ai-chats/mined.txt) so progress is trackable.

No model needed. Run from repo root:  python pipeline/ai-chats/shortlist.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARVEST = HERE / ".out" / "human_turns.jsonl"
MINED = HERE / "mined.txt"
FLAGGED = HERE / "flagged.txt"
OUT = HERE / ".out" / "shortlist.tsv"

REFLECTIVE = re.compile(
    r"worldview|purpose|meaning|philosoph|conscious|identit|who am i|myself|\bself\b|values?|belief|"
    r"truth|universe|potential|life goal|career|transition|decision|future|vision|insight|"
    r"\bstory\b|mastery|principle|ideal|reflect|mindset|fear|ambition|legacy|character|"
    r"how do i|why do i|should i|what makes|spot your own|impact|the world|human race|society",
    re.I,
)
# Tune this to your own chat history: add the tools / topics your utility chats are about.
UTILITY = re.compile(
    r"\bn8n\b|error|\bnode\b|docker|ollama|install|permission|\bfix\b|convert|format|\bjson\b|\bapi\b|"
    r"\bssl\b|kernel|regex|syntax|compile|\bfunction\b|script|workflow|trigger|webhook|endpoint|"
    r"debug|database|\bui\b|deploy|vector|embedding|integration|\bxml\b|\bclass\b|\bcode\b|import|"
    r"csv|sql",
    re.I,
)
RICH_THRESHOLD = 10


def _load_list(path: Path):
    """Return (set of 8-char ids, list of title substrings) from a ledger file."""
    ids, subs = set(), []
    if not path.exists():
        return ids, subs
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tok = line.split("  ")[0].strip()
        if re.fullmatch(r"[0-9a-fA-F]{8}", tok):
            ids.add(tok.lower())
        else:
            subs.append(line.lower())
    return ids, subs


def main() -> int:
    mined_ids, _ = _load_list(MINED)
    flag_ids, flag_subs = _load_list(FLAGGED)

    rows = []
    with HARVEST.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            blob = (r["title"] + " " + " ".join(t["text"] for t in r["user_turns"]))[:8000]
            refl = len(REFLECTIVE.findall(blob))
            util = len(UTILITY.findall(blob))
            score = min(r["n_user_turns"], 15) + min(refl, 6) * 3 - min(util, 8) * 4
            sid = r["id"][:8].lower()
            done = sid in mined_ids
            tlow = r["title"].lower()
            flagged = sid in flag_ids or any(s in tlow for s in flag_subs)
            rows.append((round(score, 1), refl, util, done, flagged, r))

    # your flagged-and-unmined first, then everything by score
    rows.sort(key=lambda x: (x[4] and not x[3], x[0]), reverse=True)
    rich = [x for x in rows if x[0] >= RICH_THRESHOLD]
    done_rich = sum(1 for x in rich if x[3])

    with OUT.open("w", encoding="utf-8") as out:
        out.write("rank\tscore\trefl\tutil\tdone\tflag\tsource\tdate\tturns\ttitle\tpath\n")
        for i, (score, refl, util, done, flagged, r) in enumerate(rows, 1):
            out.write(
                f"{i}\t{score}\t{refl}\t{util}\t{'x' if done else ''}\t{'F' if flagged else ''}\t"
                f"{r['source']}\t{r['date']}\t{r['n_user_turns']}\t{r['title']}\t{r['path']}\n"
            )

    print(f"conversations ranked : {len(rows)}")
    print(f"rich (score >= {RICH_THRESHOLD}) : {len(rich)}   (deep-mined so far: {done_rich})")
    flagged_pending = [x for x in rows if x[4] and not x[3]]
    if flagged_pending:
        print(f"\n=== YOUR FLAGGED picks ({len(flagged_pending)}) — mined first ===")
        for score, refl, util, done, flagged, r in flagged_pending[:25]:
            print(f"{score:5}  {r['source']:7}  {r['date']}  {r['title'][:50]}")
    print("\n=== top-ranked unmined (heuristic) ===")
    shown = 0
    for score, refl, util, done, flagged, r in rows:
        if done or flagged:
            continue
        print(f"{score:5}  {r['source']:7}  {r['date']}  {r['title'][:50]}")
        shown += 1
        if shown >= 20:
            break
    print(f"\nwrote {OUT.relative_to(HERE.parents[1]).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
