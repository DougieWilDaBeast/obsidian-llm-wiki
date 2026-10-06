#!/usr/bin/env python3
"""AI-Chats Stage B, Phase 2 — local-model scoring of harvested questions.

Reads the human-turn harvest (extract_human.py) and asks a LOCAL model (Ollama,
e.g. on your server at :11434) to rate each question and classify it, producing a
RANKED WORKLIST. No third-party API; the questions never leave your own machines
(CLAUDE.md §8a).

Cheap/coarse on purpose: the local model only TRIAGES (which questions are worth
a closer look); the nuanced extraction is done by your agent in-session on the
top-ranked slice.

Resumable: a ledger records scored question ids, so this can chip through
thousands of questions over many runs (and pick up new exports) with `--limit`.

Env / args:
  OLLAMA_URL   (default http://localhost:11434)   --url
  OLLAMA_MODEL (default llama2:latest)             --model
  --limit N    score at most N new questions this run (0 = all)

Run wherever Ollama lives (e.g. your server):
  python pipeline/ai-chats/score.py --limit 50
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / ".out"
HARVEST = OUT_DIR / "human_turns.jsonl"
SCORED = OUT_DIR / "scored_questions.jsonl"
LEDGER = OUT_DIR / "scored.ledger"

TYPES = {"socratic", "chain-reasoning", "conceptual", "factual", "story", "mundane"}

SYSTEM = (
    "You rate questions a person asked an AI assistant, to surface their most "
    "valuable ones to keep. Reply with ONE JSON object only, no prose."
)
PROMPT = (
    'Rate this question on a 1-5 keep-score (5 = rare, generative, personally '
    'distinctive, or deep/Socratic; 1 = mundane factual lookup anyone could ask). '
    'Classify type as one of: socratic, chain-reasoning, conceptual, factual, '
    'story, mundane.\n\nQuestion: "{q}"\n\n'
    'Reply JSON exactly: {{"keep": <1-5>, "type": "<type>", "why": "<max 6 words>"}}'
)


def load_ledger() -> set[str]:
    if LEDGER.exists():
        return set(LEDGER.read_text(encoding="utf-8").split())
    return set()


def iter_questions():
    """Yield (qid, context) for every harvested question."""
    with HARVEST.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            for i, q in enumerate(r.get("questions", [])):
                qid = f"{r['id'] or r['path']}#{i}"
                yield qid, {
                    "qid": qid,
                    "conv_id": r["id"],
                    "source": r["source"],
                    "date": r["date"],
                    "title": r["title"],
                    "path": r["path"],
                    "text": q,
                }


def call_ollama(url: str, model: str, question: str) -> dict:
    body = json.dumps(
        {
            "model": model,
            "system": SYSTEM,
            "prompt": PROMPT.format(q=question.replace('"', "'")[:600]),
            "stream": False,
            "options": {"temperature": 0},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + "/api/generate", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        out = json.loads(resp.read())["response"]
    return parse_score(out)


def parse_score(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {"keep": None, "type": "?", "why": "", "raw": text[:120]}
    try:
        d = json.loads(m.group(0))
    except Exception:
        return {"keep": None, "type": "?", "why": "", "raw": text[:120]}
    keep = d.get("keep")
    try:
        keep = int(keep)
    except (TypeError, ValueError):
        keep = None
    typ = str(d.get("type", "?")).strip().lower()
    if typ not in TYPES:
        typ = "?"
    return {"keep": keep, "type": typ, "why": str(d.get("why", ""))[:60]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("OLLAMA_URL", "http://localhost:11434"))
    ap.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "llama2:latest"))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if not HARVEST.exists():
        print(f"error: run extract_human.py first ({HARVEST} missing)")
        return 1

    done = load_ledger()
    pending = [(qid, ctx) for qid, ctx in iter_questions() if qid not in done]
    if args.limit:
        pending = pending[: args.limit]
    print(f"model {args.model} @ {args.url} | {len(done)} already scored | scoring {len(pending)} now")

    scored = 0
    with SCORED.open("a", encoding="utf-8") as out, LEDGER.open("a", encoding="utf-8") as ledg:
        for qid, ctx in pending:
            try:
                res = call_ollama(args.url, args.model, ctx["text"])
            except Exception as e:  # network/model hiccup — skip, retry next run
                print(f"  [skip] {qid}: {e}")
                continue
            ctx.update(res)
            out.write(json.dumps(ctx, ensure_ascii=False) + "\n")
            out.flush()
            ledg.write(qid + "\n")
            ledg.flush()
            scored += 1
            if scored % 25 == 0:
                print(f"  scored {scored}/{len(pending)}")
    print(f"done: scored {scored} this run -> {SCORED.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
