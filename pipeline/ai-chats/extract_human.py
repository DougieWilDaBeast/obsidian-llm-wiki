#!/usr/bin/env python3
"""AI-Chats Stage B, Phase 1 — mechanical harvest of the HUMAN side.

Parses the per-conversation archive Markdown (written by split_exports.py, with
**You:** / **Assistant:** turn tags) and emits a JSONL of the author's own turns
and the questions they asked. This is the safe, free, zero-risk foundation of
Stage B (CLAUDE.md §8a): only the human's turns are authentic, so harvesting them
carries no hallucination risk — the model's answers are left untouched.

NO model is called here. Output is intermediate pipeline state (git-ignored).

Run from repo root:  python pipeline/ai-chats/extract_human.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AI_CHATS = REPO / "00-Raw" / "AI-Chats"
OUT_DIR = Path(__file__).resolve().parent / ".out"
OUT_JSONL = OUT_DIR / "human_turns.jsonl"

HEADER_KEYS = ("source", "model", "conversation id", "created", "messages")
TURN_RE = re.compile(r"\*\*(You|Assistant):\*\*\s*(.*?)(?=\n\*\*(?:You|Assistant):\*\*|\Z)", re.S)
# question clauses: a run of text ending in '?'
QUESTION_RE = re.compile(r"[^.?!\n][^.?!]*\?")
# drop code / URL / fragment false-positives so only natural-language questions survive
_NOISE_RE = re.compile(
    r"[{}=;<>_|\\]|::|0x|https?://|www\.|\.com|com/|\.ie|aspx|\bf\""
    r"|\b(return|assign|module|always|input|output|logic|reg|def|class|import|override|fun|val|var|private|public|binding|fragment|savedInstanceState)\b",
    re.I,
)
_START_RE = re.compile(r"^(?:[A-Z]|wh|how|can|could|would|should|is|are|do|does|did|if|why|when|where|which|who)", re.I)


def is_clean_question(q: str) -> bool:
    """Keep only natural-language questions (CLAUDE.md: the human's real questions)."""
    if len(q.split()) < 4:
        return False
    if sum(c.isalpha() or c.isspace() for c in q) / max(len(q), 1) < 0.75:
        return False
    if _NOISE_RE.search(q):
        return False
    return bool(_START_RE.match(q.strip()))


def parse_header(text: str) -> dict:
    meta = {}
    m = re.search(r"^#\s+(.*)$", text, re.M)
    meta["title"] = (m.group(1).strip() if m else "").strip()
    for key in HEADER_KEYS:
        km = re.search(rf"^- {re.escape(key)}:\s*(.*)$", text, re.M)
        if km:
            meta[key.replace(" ", "_")] = km.group(1).strip()
    return meta


def clean(t: str) -> str:
    return re.sub(r"[ \t]+", " ", t.strip())


def harvest_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    meta = parse_header(text)
    # body starts after the '---' separator the splitter writes
    body = text.split("\n---\n", 1)[-1]
    user_turns = []
    for role, chunk in TURN_RE.findall(body):
        if role != "You":
            continue
        chunk = chunk.strip()
        if not chunk:
            continue
        questions = [clean(q) for q in QUESTION_RE.findall(chunk)]
        questions = [q for q in questions if is_clean_question(q)]
        user_turns.append(
            {
                "text": chunk,
                "is_question": "?" in chunk,
                "questions": questions,
            }
        )
    # dedup questions across the conversation, preserve order
    seen = set()
    all_questions = []
    for t in user_turns:
        for q in t["questions"]:
            k = q.lower()
            if k not in seen:
                seen.add(k)
                all_questions.append(q)
    return {
        "id": meta.get("conversation_id", ""),
        "source": meta.get("source", ""),
        "model": meta.get("model", ""),
        "date": meta.get("created", ""),
        "title": meta.get("title", ""),
        "path": path.relative_to(REPO).as_posix()[:-3],
        "n_user_turns": len(user_turns),
        "n_questions": len(all_questions),
        "user_turns": user_turns,
        "questions": all_questions,
    }


def main() -> int:
    files = sorted((AI_CHATS / "ChatGPT").glob("*.md")) + sorted((AI_CHATS / "Claude").glob("*.md"))
    OUT_DIR.mkdir(exist_ok=True)
    convos = 0
    tot_user_turns = 0
    tot_questions = 0
    convos_with_q = 0
    with OUT_JSONL.open("w", encoding="utf-8") as fh:
        for f in files:
            rec = harvest_file(f)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            convos += 1
            tot_user_turns += rec["n_user_turns"]
            tot_questions += rec["n_questions"]
            if rec["n_questions"]:
                convos_with_q += 1
    print(f"conversations parsed : {convos}")
    print(f"total user turns     : {tot_user_turns}")
    print(f"total questions asked: {tot_questions}")
    print(f"convos with >=1 question: {convos_with_q}")
    print(f"wrote {OUT_JSONL.relative_to(REPO).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
