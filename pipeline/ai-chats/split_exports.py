#!/usr/bin/env python3
"""Split ChatGPT / Claude conversation exports into one Markdown file per
conversation (the immutable per-conversation archive), and emit a catalog
sidecar for the Stage-A digest.

Implements CLAUDE.md s8a (Stage A — archive + catalog). It does NO synthesis and
ingests NO content into the wiki: it only normalises the bulky export JSON into
human-readable, role-tagged archive files plus a machine-readable catalog the
agent reads to build `10-Refined/AI-Chats catalog.md`.

Design:
- Adapter per source (ChatGPT mapping-graph / Claude chat_messages) -> a generic
  conversation/v1 shape, so a future export (Gemini/Grok) plugs in by adding one
  adapter.
- Idempotent: filenames are keyed on the conversation id (8-char suffix), so a
  re-run after a new export overwrites the same files and adds only new ones.
- The human-vs-model "tell" is preserved:
  every turn is tagged **You:** / **Assistant:** and the source/model recorded.

Run from repo root:  python pipeline/ai-chats/split_exports.py
"""
from __future__ import annotations

import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AI_CHATS = REPO / "00-Raw" / "AI-Chats"
OUT_SIDECAR = Path(__file__).resolve().parent / "catalog.json"
CATALOG_PAGE = REPO / "10-Refined" / "AI-Chats catalog.md"

SNIPPET_LEN = 140


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def slugify(title: str, fallback: str) -> str:
    s = re.sub(r"[^\w\s-]", "", (title or "").strip(), flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return (s or fallback)[:80].strip()


def short_id(conv_id: str) -> str:
    return re.sub(r"[^0-9a-zA-Z]", "", conv_id or "")[:8] or "00000000"


def to_date(value) -> str:
    """Return YYYY-MM-DD from an epoch float or ISO string; '0000-00-00' if unknown."""
    if value is None or value == "":
        return "0000-00-00"
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%d")
        # ISO string, possibly with trailing Z
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return "0000-00-00"


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\u0000", "")).strip()


def snippet(text: str) -> str:
    t = clean(text)
    return (t[:SNIPPET_LEN] + "\u2026") if len(t) > SNIPPET_LEN else t


# --------------------------------------------------------------------------- #
# adapters -> generic conversation/v1: {id, source, title, date, model, messages}
#   messages: [{role: 'user'|'assistant'|'system', text}]
# --------------------------------------------------------------------------- #
def adapt_claude(raw: list) -> list[dict]:
    convs = []
    for c in raw:
        msgs = []
        for m in c.get("chat_messages", []):
            role = "user" if m.get("sender") == "human" else "assistant"
            parts = [
                b.get("text", "")
                for b in (m.get("content") or [])
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            text = "\n".join(p for p in parts if p) or (m.get("text") or "")
            if text.strip():
                msgs.append({"role": role, "text": text})
        convs.append(
            {
                "id": c.get("uuid", ""),
                "source": "Claude",
                "title": (c.get("name") or "").strip(),
                "date": to_date(c.get("created_at")),
                "model": "claude (unspecified)",
                "messages": msgs,
            }
        )
    return convs


def _chatgpt_linear(mapping: dict, current: str | None) -> list[dict]:
    """Walk the ChatGPT mapping graph from current_node up to root, then reverse."""
    order = []
    node = current
    # if no current_node, fall back to any leaf
    if not node:
        node = next((nid for nid, n in mapping.items() if not n.get("children")), None)
    seen = set()
    while node and node in mapping and node not in seen:
        seen.add(node)
        order.append(mapping[node])
        node = mapping[node].get("parent")
    return list(reversed(order))


def adapt_chatgpt(raw: list) -> list[dict]:
    convs = []
    for c in raw:
        mapping = c.get("mapping", {}) or {}
        nodes = _chatgpt_linear(mapping, c.get("current_node"))
        msgs = []
        model = ""
        for n in nodes:
            msg = n.get("message")
            if not msg:
                continue
            role = (msg.get("author") or {}).get("role", "")
            if role not in ("user", "assistant"):
                continue
            content = msg.get("content") or {}
            if content.get("content_type") != "text":
                continue
            text = "\n".join(p for p in content.get("parts", []) if isinstance(p, str) and p)
            if not text.strip():
                continue
            model = model or (msg.get("metadata") or {}).get("model_slug", "")
            msgs.append({"role": role, "text": text})
        convs.append(
            {
                "id": c.get("conversation_id") or c.get("id", ""),
                "source": "ChatGPT",
                "title": (c.get("title") or "").strip(),
                "date": to_date(c.get("create_time")),
                "model": model or c.get("default_model_slug") or "gpt (unspecified)",
                "messages": msgs,
            }
        )
    return convs


# --------------------------------------------------------------------------- #
# writers
# --------------------------------------------------------------------------- #
def write_conversation(conv: dict) -> str:
    """Write one archive Markdown file; return its repo-relative path (no .md)."""
    sid = short_id(conv["id"])
    title = conv["title"] or f"Untitled {conv['source']} chat"
    slug = slugify(conv["title"], f"untitled-{sid}")
    fname = f"{conv['date']} {slug} - {sid}.md"
    dest = AI_CHATS / conv["source"] / fname

    lines = [
        f"# {title}",
        "",
        f"- source: {conv['source']}",
        f"- model: {conv['model']}",
        f"- conversation id: {conv['id']}",
        f"- created: {conv['date']}",
        f"- messages: {len(conv['messages'])}",
        "",
        "> Immutable archive of an AI conversation (CLAUDE.md s8a, trust: low).",
        "> Only the **You:** turns are the author's own words; **Assistant:** turns are"
        " unverified model output and must never become facts without corroboration.",
        "",
        "---",
        "",
    ]
    for m in conv["messages"]:
        speaker = "You" if m["role"] == "user" else "Assistant"
        lines.append(f"**{speaker}:**")
        lines.append("")
        lines.append(m["text"].rstrip())
        lines.append("")
    dest.write_text("\n".join(lines), encoding="utf-8")
    rel = dest.relative_to(REPO).as_posix()
    return rel[:-3]  # strip .md for wikilinks


def catalog_row(conv: dict, rel_no_ext: str) -> dict:
    user_msgs = [m["text"] for m in conv["messages"] if m["role"] == "user"]
    first = user_msgs[0] if user_msgs else ""
    last = user_msgs[-1] if len(user_msgs) > 1 else ""
    mid = ""
    middles = user_msgs[1:-1]
    if middles:
        rng = random.Random(conv["id"])  # deterministic per conversation
        mid = rng.choice(middles)
    return {
        "id": conv["id"],
        "source": conv["source"],
        "model": conv["model"],
        "date": conv["date"],
        "title": conv["title"] or "(untitled)",
        "turns": len(conv["messages"]),
        "path": rel_no_ext,
        "opens": snippet(first),
        "mid": snippet(mid),
        "ends": snippet(last),
    }


def load_source(name: str, adapter) -> list[dict]:
    """Load a source's conversations from one or many JSON files.

    Claude exports a single top-level `conversations.json`; ChatGPT exports a
    nested hash subfolder with chunked `conversations-000.json` ... files. Both
    are matched by a recursive `conversations*.json` glob and concatenated.
    """
    base = AI_CHATS / name
    if not base.exists():
        print(f"  [skip] {name}: folder missing")
        return []
    files = sorted(base.rglob("conversations*.json"))
    if not files:
        print(f"  [skip] {name}: no conversations*.json yet")
        return []
    raw: list = []
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        raw.extend(data if isinstance(data, list) else [data])
    convs = adapter(raw)
    print(f"  [{name}] {len(convs)} conversations from {len(files)} file(s)")
    return convs


def build_catalog_page(rows: list[dict]) -> None:
    """Generate the Stage-A digest body. Frontmatter + review banner included."""
    today = datetime.now().strftime("%Y-%m-%d")
    by_source: dict[str, dict[str, list[dict]]] = {}
    for r in rows:
        ym = r["date"][:7] if r["date"] != "0000-00-00" else "undated"
        by_source.setdefault(r["source"], {}).setdefault(ym, []).append(r)

    out = [
        "---",
        "type: source",
        "title: AI-Chats catalog",
        f"created: {today}",
        f"updated: {today}",
        "status: active",
        "tags: [ai-chat, digest, catalog]",
        "provenance: ai-chat",
        "trust: low",
        f"sources: {len(rows)}",
        "---",
        "",
        "# AI-Chats catalog",
        "",
        "Stage-A index (CLAUDE.md s8a) of exported ChatGPT/Claude conversations. **No content "
        "is ingested here** — this is a browsable map so the author can flag which conversations "
        "are worth mining for *their own* insights (Stage B).",
        "",
        "> [!review]",
        "> Everything below is **`trust: low`**. Each entry's snippets are the author's own "
        "questions (first / a random middle / last user message) — *not* model output. Nothing "
        "in these conversations is a fact until corroborated by a high-trust source. Generated by "
        "`pipeline/ai-chats/split_exports.py`; do not hand-edit — re-run the splitter.",
        "",
    ]
    total = 0
    for source in sorted(by_source):
        src_rows = by_source[source]
        n = sum(len(v) for v in src_rows.values())
        total += n
        out.append(f"## {source} ({n})")
        out.append("")
        for ym in sorted(src_rows, reverse=True):
            out.append(f"### {ym}")
            out.append("")
            for r in sorted(src_rows[ym], key=lambda x: x["date"], reverse=True):
                out.append(
                    f"- **{r['date']}** — [[{r['path']}|{r['title']}]] · _{r['model']}_ · "
                    f"{r['turns']} turns"
                )
                gloss = " · ".join(
                    f"{label} \u201c{r[key]}\u201d"
                    for label, key in (("opens:", "opens"), ("mid:", "mid"), ("ends:", "ends"))
                    if r[key]
                )
                if gloss:
                    out.append(f"  - {gloss}")
            out.append("")
    out.append("## Connections")
    out.append("")
    out.append("- [[AI Conversations MOC]]")
    out.append("")
    CATALOG_PAGE.write_text("\n".join(out), encoding="utf-8")
    print(f"  [catalog] wrote {CATALOG_PAGE.relative_to(REPO).as_posix()} ({total} entries)")


def main() -> int:
    if not AI_CHATS.exists():
        print(f"error: {AI_CHATS} not found", file=sys.stderr)
        return 1
    print("Splitting AI-chat exports...")
    convs = load_source("ChatGPT", adapt_chatgpt) + load_source("Claude", adapt_claude)
    convs = [c for c in convs if c["messages"]]  # drop empty/deleted conversations
    rows = []
    for c in convs:
        rel = write_conversation(c)
        rows.append(catalog_row(c, rel))
    rows.sort(key=lambda r: (r["source"], r["date"]))
    OUT_SIDECAR.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [sidecar] wrote {OUT_SIDECAR.relative_to(REPO).as_posix()} ({len(rows)} rows)")
    build_catalog_page(rows)
    print(f"Done: {len(rows)} conversations archived + cataloged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
