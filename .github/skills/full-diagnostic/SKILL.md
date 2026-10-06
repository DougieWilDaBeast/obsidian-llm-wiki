---
name: full-diagnostic
description: 'Whole-repo diagnostic + orchestrated update for the Personal LLM Wiki (this vault). USE WHEN the user asks for a "full diagnostic", "full update", "health check the whole repo", "diagnostic update", "check everything and bring it up to date", or wants to know which skills to run. HYBRID: Phase A runs a read-only consolidated health report across the vault (ingest backlog, structural health, audit coverage, story freshness) and recommends a run order; then on the human go-ahead, Phase B hands each flagged skill (vault-ingest, vault-audit, story-agent) to its own workflow, in order. DO NOT USE for a single-layer task — call that one skill directly. NEVER edit pages in Phase A; honor each sub-skill''s own human gates in Phase B.'
---

# Full Diagnostic

The **meta-skill** that diagnoses the whole vault and then orchestrates the single-purpose
skills to bring it up to date. It is the "run everything, in the right order, safely" workflow.
The authoritative schema is [`CLAUDE.md`](../../../CLAUDE.md) §8 (Query/Lint), §9 (headless
discipline), §10 (never) — this skill is the **operational shortcut**: one read-only report
engine plus the orchestration steps.

It does **not** reimplement the other skills — it sequences them:

| Layer                   | Skill            | What it does                                        |
| ----------------------- | ---------------- | --------------------------------------------------- |
| `00-Raw` → `10-Refined` | **vault-ingest** | file uncovered raws, update the graph               |
| `10-Refined` integrity  | **vault-audit**  | random cross-check vs sources; raise questions      |
| `30-Story`              | **story-agent**  | fold new narrative into the self-narrative (drafts) |

## Golden rules (do not violate)

- **Phase A is read-only.** The diagnostic inspects and prints — it never edits, commits, pulls,
  or pushes. Present the report, then **stop and wait** for the human's go-ahead.
- **Ingest is the hard prerequisite.** vault-audit and story-agent both read
  `10-Refined/`. If there's an ingest backlog, run **vault-ingest first** so the others work on a
  current wiki.
- **Honor each sub-skill's own gates.** ingest writes + auto-commits; **audit and story only
  DRAFT and ask** — the human confirms findings and canonises Story. This skill never overrides
  those gates.
- **Headless mode = diagnose + draft only.** Run Phase A, run ingest if needed, and let
  audit/story produce drafts/candidates — never confirm, canonise, or edit settled pages.

## Workflow

### Phase A — Diagnose (one command — do this first)

```pwsh
pwsh -File .github/skills/full-diagnostic/scripts/run-diagnostic.ps1
# summary only (verdict lines + run order):
pwsh -File .github/skills/full-diagnostic/scripts/run-diagnostic.ps1 -Quiet
```

It prints five sections — **Sync, Ingest backlog, Structural health, Audit coverage, Story
freshness** — each ending in `OK` or `ATTENTION -> <skill>`, then a
**RECOMMENDED RUN ORDER** footer built from whatever raised attention. It makes **no** changes.

Present the consolidated report to the human in chat: each verdict, the key numbers, and the
recommended order. Then **stop** — do not start Phase B until the human says go (or names a subset).

### Phase B — Update (on the human's go-ahead)

Run the flagged skills **in the footer's order** (always ingest → audit → story for any that are
flagged). For each, hand off to that skill's own `SKILL.md` and follow it fully:

1. **vault-ingest** — if there's a backlog. Files raws, updates the graph + `index.md`/`log.md`,
   commits & pushes. _Re-run the diagnostic's ingest check afterwards to confirm 0 uncovered._
2. **vault-audit** — random cross-check of `-AuditSample` pages; surfaces QUESTIONS/OPTIONS.
   Make **no** page edits unless the human directs a fix; replies are indicators, not verdicts.
3. **story-agent** — narrate pass; draft/refresh `Story —`/`Chapter —` pages. Stage in `_Drafts/`;
   the human canonises.

Each sub-skill writes its **own** `log.md` entry per its spec (and ingest commits atomically).

### Close the run

- **Re-run Phase A** to confirm the sections that were flagged now read `OK` (or note what's
  intentionally left for the human, e.g. open audit findings awaiting indicators).
- Append **one umbrella** entry to [`log.md`](../../../log.md) using the template in
  [`reference/templates.md`](reference/templates.md):

```markdown
## [YYYY-MM-DD] diagnostic | <one-line summary>

- Ran full-diagnostic. <which skills ran, what changed, what's left for the human>.
```

- Commit with a neutral message, e.g. `diagnostic: full pass (ingest + audit)`.

## Token-efficiency checklist

- Run `run-diagnostic.ps1` once instead of invoking each skill's discovery script by hand.
- In Phase B, defer to each sub-skill's own bundled script (`new-raws.ps1`, `pick-sections.ps1`,
  `gather-narrative.ps1`) — don't re-derive their work here.
- Use `-Quiet` when you only need the verdicts + run order.

## Notes / gotchas

- The diagnostic is **status-only on git** — it never pulls/pushes (so it's safe to run any
  time). vault-ingest does the actual sync in Phase B.
- "All `OK`" is a valid outcome — report it and stop; there's nothing to run.
- If only one layer is flagged, you can skip this skill and run that single skill directly — this
  meta-skill earns its keep when several layers need attention in order.
- Structured-source digests (wearables / task exports) are roll-ups, not page-per-raw; the diagnostic's
  coverage check excludes them (same rule as Dashboard.md / CLAUDE.md §8b).
