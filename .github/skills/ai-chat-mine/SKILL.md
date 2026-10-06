---
name: ai-chat-mine
description: 'Mine the archived ChatGPT/Claude conversations (Stage B of the AI-Chats funnel, CLAUDE.md §8a) into the Personal LLM Wiki. USE WHEN the user asks to "mine the AI chats", "deep-parse conversations", pull insights/concepts/reasoning from their chat history, grow the Question Bank, or surface story material from the chats. Runs the batch loop: pick from the ranked worklist (shortlist.py, honoring flagged.txt) → dump ONLY the human''s turns (next_unmined.py) → write trust:low insight pages that quarantine model claims → dual-route to regular Refined knowledge AND flagged story candidates → mined.txt + AI Conversations MOC + index → commit per batch. DO NOT USE for Stage A archiving (that is split_exports.py) or ordinary voice ingest (use vault-ingest).'
---

# AI-Chat Mine

The repeatable "deep-parse the archived AI conversations" workflow — **Stage B** of the AI-Chats
funnel (`CLAUDE.md` §8a, already in context). Stage A archived every ChatGPT/Claude conversation to
`00-Raw/AI-Chats/` and catalogued them ([[AI-Chats catalog]]); this skill mines the **human's side**
of the rich ones into the wiki, **resumably, a batch at a time**.

## Golden rules (from CLAUDE.md §8a — do not violate)

- **AI-chats are `trust: low`.** Only the **human's turns are authentic**; the model's turns
  hallucinate, flatter, and assume plans were carried out. Mine **their** side only.
- **Quarantine model claims.** Any factual claim originating from the AI goes in a `> [!review]`
  callout and **never becomes a fact** on an entity/concept page until an independent high-trust
  source corroborates it. Record the **model** used.
- **Segregate.** Insight pages are `provenance: ai-chat`, `trust: low`, listed under the
  **[[AI Conversations MOC]]** (+ index) so they enrich the graph without flooding it. Stage C
  (auto-extract everything) is rejected.
- **Dual output.** Each mined conversation feeds **two** places: (a) regular Refined knowledge
  (insight/concept pages + [[Question Bank]] gems); (b) **story material flagged** for the
  **story-agent** (never voiced here).
- Honor **flagged.txt** (the user's picks) ahead of the heuristic ranking.

## Workflow

### 1. Pick the batch (on the machine that holds the archive and `.out/`)

`shortlist.py` ranks the rich conversations (mined excluded, flagged jumped to top):

```bash
python3 pipeline/ai-chats/shortlist.py | head -30
```

Choose ~5–8 for the batch: **flagged.txt picks first**, then the top ranked, then anything the user
pointed at. (Conversations that back an existing concept page are high value.)

### 2. Dump the human side (one command — the token-saver)

Instead of opening each archive `.md`, dump ONLY the human's turns for the chosen ids:

```bash
python3 pipeline/ai-chats/next_unmined.py --ids <id8>,<id8>,…
# or:  --top 6   (top unmined by #user-turns, utility titles skipped)
```

GOTCHA: some conversations open with a **pasted article/prompt** as the first `You:` turn (an essay
the user is reacting to) — mine their **reactions**, not the pasted text.

### 3. Write insight pages (the human's insights, model quarantined)

Extract **what the human worked out** — their questions, decisions, reframes, frameworks, conclusions — not
the model's prose. One `AI-Chat — <title>` page per conversation (or per genuine concept; `CLAUDE.md`
§4). Use the **Stage-B template** in
[`../vault-ingest/reference/templates.md`](../vault-ingest/reference/templates.md). Frontmatter:
`provenance: ai-chat`, `trust: low`. Every model claim → `> [!review]` (record the model).

### 4. Dual-route the output

- **Regular knowledge** → the insight page + update any entity/concept it genuinely corroborates
  (respect the `trust: low` quarantine — never promote a model claim to fact). Surface a genuine
  **new gem-question** into the [[Question Bank]] themed pages.
- **Story material** → add a one-line **flag** (a `> [!note]` "story candidate" on the page) and note
  it for a later **story-agent** narrate pass. Do not voice it here.

### 5. Register + track progress

- List the new page(s) under the [[AI Conversations MOC]] and in `index.md` (Sources).
- Append the mined **8-char ids** (id + short note) to
  [`../../../pipeline/ai-chats/mined.txt`](../../../pipeline/ai-chats/mined.txt).
- Append one `stage-b` entry to `log.md`.

### 6. Commit the batch (resumable)

```pwsh
git add -A
git commit -m "stage-b: mine <N> AI chats — <themes>"
git pull --rebase origin main
git push origin main
```

The loop resumes next session from where `mined.txt` left off. Re-run `shortlist.py` for "next up".

## Token-efficiency checklist

- `next_unmined.py --ids …` dumps the human side in one shot — never open the archives one by one.
- Read only the `index.md` / entity sections you'll actually edit.
- Batch page edits; commit **per batch**, not per page.
- Don't re-read `CLAUDE.md` (auto-attached) — §8a + this skill suffice.

## Notes / gotchas (hard-won)

- **Scripts + state** (`pipeline/ai-chats/`): `shortlist.py` (ranker → `.out/shortlist.tsv`),
  `next_unmined.py` (dump human turns for `--ids` or `--top N`), `extract_human.py` (harvest →
  `.out/human_turns.jsonl`), `score.py` (optional local Ollama triage). `.out/` is **git-ignored**
  and lives wherever you run the scripts (e.g. your server). `mined.txt` + `flagged.txt` are
  **tracked**.
- **IDs:** conversation id = full UUID; `mined.txt` / `shortlist` use its **8-char prefix**.
- **Small-model scoring is a weak discriminator** (an older model like llama2 rates ~everything
  4/5) — coarse triage only; the value is hand-curating. A sharper small model (qwen2.5/phi) helps.
- **After re-harvesting** (`extract_human.py`) the per-question indices shift — wipe `scored_*` state
  if re-scoring.
- Stage A (archiving new exports) is a **separate** step (`split_exports.py`) — see the AI-chat
  section of [`../vault-ingest/reference/templates.md`](../vault-ingest/reference/templates.md).
