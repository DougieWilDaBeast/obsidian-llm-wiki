---
name: vault-ingest
description: 'Ingest new raw sources into the Personal LLM Wiki (this vault). USE WHEN the user says there is an update/new files on the server, asks to "ingest", "follow the process", "update git", or to file voice notes / clippings / inbox notes into the wiki. Runs the full pipeline: git sync → detect uncovered raws → write source pages → update entity/concept/project pages → update index.md, MOCs, log.md → commit & push. Token-efficient: a bundled script does all discovery + content extraction in one shot. DO NOT USE for editing raw sources (immutable) or for general Obsidian questions.'
---

# Vault Ingest

The repeatable "new sources landed, file them" workflow for this vault. The authoritative
schema is [`CLAUDE.md`](../../../CLAUDE.md) (already in context) — this skill is the **operational
shortcut**: exact steps, templates, and a discovery script so you don't re-derive anything.

## Golden rules (from CLAUDE.md — do not violate)

- `00-Raw/` is **immutable**: read only, never edit/move/delete.
- `10-Refined/` is **flat** (only `MOCs/` is a subfolder). Structure = `[[links]]` + MOCs, not folders.
- Voice/OCR source pages keep the **verbatim transcript** at the bottom (`## Original transcript`
  / `## Original scan (OCR)`). Summaries in your own words; never bulk-copy clipping prose.
- Don't create pages for commodity terms (Markdown, HTML, SQL). Promote a thing to its own page
  only at **≥2 sources** or a clearly substantive single source. Check `index.md` first.
- AI-chat material is `trust: low` — quarantine model claims in `> [!review]`, never promote to fact.
- Record contradictions explicitly; never silently overwrite a settled conclusion.

## Workflow

### 1. Discover (one command — do this first)

```pwsh
pwsh -File .github/skills/vault-ingest/scripts/new-raws.ps1
```

It syncs git (`fetch` + `pull --rebase origin main`), then prints every **uncovered** raw
(not yet in the wiki) with its full clean body, tagged `NEW` (arrived since the last `ingest:`
commit) or `OLDER/MISSED`. Add `-NoSync` to skip the git step. If it prints
`UNCOVERED RAWS: 0`, there is nothing to ingest — stop and report that.

For long single-line voice transcripts, the script already prints the full untruncated body,
so you do **not** need `read_file` on the raws. Only open a raw if you need the exact bytes for
the verbatim block (then strip frontmatter).

### 2. Triage each uncovered raw (per CLAUDE.md §5b)

- **Substantive** (a real idea/decision/event) → its own **source page** (§3 template).
- **Minor one-liner** (reminder, fleeting thought, single task) → a dated bullet in the month's
  **`YYYY-MM Captures`** digest. Keep exact wording; wikilink any entity named.
- **Empty / garbled** → a flagged bullet in the digest (⚠️), never silently dropped.
- Multiple clips on one topic the same day → still one source page each (granularity confirmed by
  the user historically), but cross-link them.
- **Structured / high-volume exports** (wearable day files, task-app exports) → never a page per
  datapoint (CLAUDE.md §8b). Fold them into periodic digests (`<Device> — YYYY-Www digest`,
  `YYYY-MM Tasks`) and the relevant entity/project pages. Templates in
  [`reference/templates.md`](reference/templates.md).

### 3. Write source pages

Read `index.md` (skim the relevant sections only) to reuse existing page names before creating
anything. Use the templates in [`reference/templates.md`](reference/templates.md). Naming
(CLAUDE.md §4): `YYYY-MM-DD Voice — slug`, `Clipping — title`, `OCR — slug`, `AI-Chat — title`.

### 4. Update the graph

A single source typically touches 5–15 pages. For each entity/person/concept/project the source
mentions:

- Add a dated bullet / section; bump the `sources:` count and `updated:` date in frontmatter.
- Add the source to the page's `## Sources` list and `## Connections`.
- Create stubs (`status: stub`) + links for genuinely new entities (respect the ≥2-source bar).
- Add new pages to the most relevant **MOC** in `10-Refined/MOCs/`.

Batch edits across files where your agent supports it. Whisper mis-spellings: prefer the
canonical name in prose (e.g. "E S P 32" → ESP32), but leave verbatim transcripts unchanged.

### 5. Update index.md and log.md

- `index.md`: add new pages under the right type heading; bump changed `(N sources)` counts.
- `log.md`: append one entry (note the exact format):

```markdown
## [YYYY-MM-DD] ingest | <short label>

- One-line summary of pages created/updated, counts bumped, and any `[!review]` flags raised.
```

### 6. Commit & push

```pwsh
git add -A
git commit -m "ingest: <short label>"
git pull --rebase origin main
git push origin main
```

If the rebase pulls a server autocommit, re-check it didn't bring new raws (`git diff --stat`);
a `graph.json`-only change is harmless.

## Token-efficiency checklist

- Use the discovery script instead of opening each raw + manual transcript extraction.
- Read only the **needed** `index.md` sections and the specific pages you'll edit — never list
  every file in a large vault.
- Batch edits across files; append `log.md` in a single write.
- Don't re-read `CLAUDE.md` (it's auto-attached) or example pages — the templates here suffice.

## Notes / gotchas

- If a server runs `vault_autocommit.sh` on a timer and is the sole transcription brain, your
  editing machine just pulls. Check the server directly if you suspect raws that landed but were
  not yet committed.
- `OLDER/MISSED` raws are real gaps from earlier ingests — file them too unless the user says
  otherwise.
