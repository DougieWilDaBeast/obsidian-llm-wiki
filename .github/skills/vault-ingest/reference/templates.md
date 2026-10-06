# Page templates

Copy-paste skeletons for the vault. Keep frontmatter keys in this order. Dates are `YYYY-MM-DD`.

## Voice source page

```markdown
---
type: source
title: 2026-01-12 Voice — short slug
created: <today>
updated: <today>
status: active
tags: [voice, <theme>]
provenance: voice
trust: high
sources: 1
---

# 2026-01-12 Voice — short slug

One- or two-sentence framing of what this note is.

## Summary

- Bullet synthesis in your own words.
- Wikilink every entity/concept/person/project that has (or should have) a page.

> [!note] Optional: flag Whisper mis-spellings, low-confidence bits, or context.

## Connections

- [[Related page]] · [[Another]]

## Sources

- Raw: [[00-Raw/Voice/Voice 260112_191045]]

## Original transcript

> (verbatim Whisper output, unedited — paste the full single line)
```

## Clipping source page

```markdown
---
type: source
title: Clipping — article title
created: <today>
updated: <today>
status: active
tags: [clipping, <theme>]
provenance: clipping
trust: high
sources: 1
---

# Clipping — article title

What it is + why it's in the vault (tie to an existing thread). Summarise in your own words;
do NOT paste large verbatim chunks — the raw clipping holds the original.

## Summary

- Key points, paraphrased.

> [!review] Any vendor/marketing or unverified claims quarantined here.

## Connections

- [[Related page]]

## Sources

- Raw: [[00-Raw/Clippings/Clipping — article title]]
- URL: <https://…>
```

## Entity / concept / project / person page

```markdown
---
type: entity # entity | concept | project | person | moc
title: Natural Name
created: <today>
updated: <today>
status: active # active | stub | archived
tags: [<theme>]
sources: 1
---

# Natural Name

One- or two-sentence definition / synthesis up top.

## Key points

- Synthesis in your own words.

## Connections

- [[Related]] · [[Related]]

## Sources

- [[2026-01-12 Voice — short slug]]
```

## Capture bullet (in `YYYY-MM Captures`)

One dated bullet per minor note; exact wording preserved; raw linked at the end.

```markdown
- **2026-01-13 HH:MM** — exact/echoed wording of the one-liner. Short gloss if needed. See
  [[Entity]]. _([[00-Raw/Voice/Voice 260113_000000]])_
```

Garbled/empty variant:

```markdown
- **2026-01-13** — ⚠️ _Garbled clip_ — "…". Meaning unclear; flagged per CLAUDE.md §5b; raw kept.
  _([[00-Raw/Voice/Voice 260113_000000]])_
```

## Task-app export — monthly digest (`YYYY-MM Tasks`)

For a JSON export from a to-do / task-matrix app (CLAUDE.md §8b). It's a **structured,
high-volume** source: never make a page per task. Fold active/notable tasks into project pages
and roll the rest into a monthly digest. **Keep each task's stable id in a trailing code span** so
a future two-way sync can match them back.

```markdown
---
type: source
title: YYYY-MM Tasks
created: <today>
updated: <today>
status: active
tags: [tasks, digest]
provenance: tasks
trust: high
sources: 1
---

# YYYY-MM Tasks

Monthly roll-up of **active** tasks from the YYYY-MM-DD export (per CLAUDE.md §8b). Stable task
ids retained for future status sync.

## Active

- Exact/echoed task title · due YYYY-MM-DD · [[Project page]] `task_…id…`

> [!note] Completed this month: list or count, linking the raw export.

> [!review] Gaps: flag junk/test tasks or an export that contradicts the previous one.

## Sources

- Raw: [[00-Raw/Tasks/<file>]]
```

## Wearable weekly digest (`<Device> — YYYY-Www digest`)

One per ISO week, written from the weekly stat sidecar (`pipeline/wearables/aggregate_weekly.py`),
never from the raw day files. Trends in prose, not tables of numbers.

```markdown
---
type: source
title: Wearable — 2026-W02 digest
created: <today>
updated: <today>
status: active
tags: [wearable, digest]
provenance: wearable
trust: high
sources: 7
---

# Wearable — 2026-W02 digest

Two or three sentences on the week's trend (recovery, sleep, strain) and anything that lines up
with other notes (a late-night build session, a race, travel).

> [!review] Data gaps: e.g. "no data Wed–Thu (device not worn)" — never let a partial week read
> as complete.

## Connections

- [[Wearable]] · [[Related project or note]]

## Sources

- Raw: `00-Raw/Wearables/<device>/2026-01-05.json` … `2026-01-11.json`
```

## index.md entry

```markdown
- [[Page Name]] — one-line summary. _status_ (N sources)
```

## log.md entry

```markdown
## [YYYY-MM-DD] ingest | short label

- Created [[A]], [[B]]; updated [[C]] (n→m); 2 captures; bumped index/MOCs. Flags: …
```

## AI-chat exports (ChatGPT / Claude) — `trust: low`, two-stage funnel

AI conversations are **structured/high-volume** and **low-trust** (CLAUDE.md §8a). Do **not** run
`new-raws.ps1` on them (it would dump the giant export JSON) and never absorb them wholesale.

**Stage A — archive + catalog (mechanical).** Run the splitter, which writes one immutable
archive file per conversation and (re)generates the catalog digest. Idempotent — re-run when a new
export lands:

```pwsh
python pipeline/ai-chats/split_exports.py
```

It produces `00-Raw/AI-Chats/<source>/<date> <slug> - <id>.md` (role-tagged **You:** /
**Assistant:**), a git-ignored `pipeline/ai-chats/catalog.json` sidecar, and ``10-Refined/AI-Chats catalog.md``. gitignore the bulky raw blobs (`conversations.json`, `*.zip`). Segregate everything
under [[AI Conversations MOC]]; never link AI-chat pages from unrelated entity/concept pages.

**Stage B — extract the author's insights (only for chats the author flags).** Capture **what the human
worked out**, not the model's prose. Quarantine any model-originated claim in `> [!review]` and
record the model.

```markdown
---
type: source
title: AI-Chat — conversation title
created: <today>
updated: <today>
status: active
tags: [ai-chat, <theme>]
provenance: ai-chat
trust: low
sources: 1
---

# AI-Chat — conversation title

What the author was working through here (model: <model>), and why it's worth keeping. Only the
author's turns are authentic.

## What the author worked out

- Their questions, decisions, reframes, conclusions — in your own words, paraphrasing the human side.

> [!review]
> Model-originated claim(s) to verify before they become facts anywhere: «…». Model: <model>.

## Connections

- [[AI Conversations MOC]] · [[Related entity]]

## Sources

- Raw: [[00-Raw/AI-Chats/<source>/<file>]]
```
