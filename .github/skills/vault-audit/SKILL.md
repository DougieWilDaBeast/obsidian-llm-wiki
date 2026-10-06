---
name: vault-audit
description: 'Random, in-depth spot-audit of the Personal LLM Wiki (this vault). USE WHEN the user asks to "cross-check", "spot-check", "audit", "verify a random section", "check the pages are accurate", or wants an unpredictable integrity sweep. Randomly picks a few Refined pages at a random cadence, cross-checks each claim against its cited 00-Raw sources and against peer pages, drills into anything that does not line up, and — crucially — prepares QUESTIONS or OPTIONS for the human instead of assuming a fix. Treats every human reply as an INDICATOR (a perspective), not a verdict. DO NOT USE for ordinary ingest (use vault-ingest) or for self-narrative (use story-agent). NEVER auto-correct a page or close a finding off a single reply.'
---

# Vault Audit

The **random cross-check** workflow for the vault — a sharper, question-first variant of the
Lint operation. The authoritative schema is [`CLAUDE.md`](../../../CLAUDE.md) §8 (Lint), §9
(conservative synthesis), §10 (never) — this skill is the **operational shortcut**: the picker
script, templates, and exact steps.

The idea: like a spot-check auditor, scrutiny is **unpredictable**. You can't know which pages
get checked or when, so the whole vault has to stay honest everywhere. When something surfaces,
you chase it _with focus_ — but you never assume the answer. You prepare **questions or options**
and put them to the human. And even their reply is just an **indicator**: the human may have
added a perspective, not closed the matter. Convergence settles a finding — never one response.

## Golden rules (do not violate)

- **Random by design.** Pick pages at random, at a random cadence (the picker's `-Roll` gate).
  Do not turn this into a predictable full sweep — that defeats the purpose.
- **Cross-check against ground truth.** Verify each claim against the **verbatim 00-Raw** source
  it cites, and against peer Refined pages on the same entity/topic. `00-Raw/` is read-only (§10).
- **Never assume — ask.** When something doesn't line up, you **must** produce a QUESTION or a set
  of OPTIONS with the evidence. Never silently rewrite, "correct", or resolve a page.
- **Replies are indicators, not verdicts.** Record what the human says as a dated _indicator_ and
  your honest read of it (perspective added / partial / likely answer). A finding stays **open**
  unless the human **explicitly** says "settle it / fix it". One reply never closes a finding.
- **Edit only on explicit direction.** A page is changed only when the human directs the fix —
  and even then it's logged as their call, not the audit's assumption. Record contradictions,
  never overwrite a settled conclusion silently (§8/§10).
- **Audit machinery stays out of the content layers.** Findings + the ledger live in this skill's
  `state/` folder, never in `10-Refined/`, `index.md`, or the MOCs.

## Workflow

### 1. Roll & pick (one command — do this first)

```pwsh
pwsh -File .github/skills/vault-audit/scripts/pick-sections.ps1
# unpredictable cadence (e.g. wired after an ingest): only audits ~30% of the time
pwsh -File .github/skills/vault-audit/scripts/pick-sections.ps1 -Roll -Chance 0.3
# let coverage compound toward never-checked pages (still random):
pwsh -File .github/skills/vault-audit/scripts/pick-sections.ps1 -Count 2 -BiasUnaudited
```

It optionally flips a weighted coin (`-Roll`) to decide whether to audit at all, then prints
each randomly-picked page's full body, the **verbatim** body of every `00-Raw` source it cites
(word-wrapped so long Whisper transcripts aren't truncated), the Refined pages it links to, and
peer pages that mention its title (where contradictions hide). One shot — you should not need
to open the raws yourself.

### 2. Cross-check each page — broad, then focused

For each picked page, check (broad pass):

- **Source fidelity** — does each claim actually appear in / follow from the cited raw? Flag
  anything inflated, invented, or drifted from what was really said.
- **Cross-page consistency** — does it contradict a peer page on the same entity/topic?
- **Frontmatter accuracy** — does `sources:` match the `## Sources` list? Is `updated:` sane? Do
  the `[[links]]` resolve?
- **Staleness** — has a newer source quietly superseded a claim here?

When _anything_ surfaces, switch to the **focused pass**: pull the specific raw / peer page,
expand context, and pin down exactly what is and isn't supported. Depth over breadth on hits.

### 3. Prepare questions or options (never a fix)

For every finding, write it up using [`reference/templates.md`](reference/templates.md):

- a **QUESTION** when the honest move is to ask (no leading assumption baked in), or
- a small set of **OPTIONS** when there are a few plausible resolutions — always with an escape
  hatch ("none of these / it's more nuanced").

Surface these to the human in chat. **Do not edit any page yet.**

### 4. Record the reply as an indicator

When the human answers, add a dated **Indicator** line to the finding with your honest
classification (perspective added / partial / likely answer). Default status stays
`still-open`. Only flip to `settled` — and only then touch the page — if the human **explicitly**
directs the fix. Log both the old and new wording when you do change something (§8).

### 5. Close the run

- Append one `## [date] audit run` block to
  [`state/audit-ledger.md`](state/audit-ledger.md): an `audited ::` line per page (so future
  picks compound coverage) and any **Open findings** carried forward.
- Append one terse `## [date] audit | spot-check (N pages)` entry to
  [`log.md`](../../../log.md) — summary only, no raw findings, note "no pages edited (awaiting
  indicators)" unless the human directed a fix.
- Commit with a neutral message, e.g. `audit: spot-check 3 pages` (rides the same git + sync as
  the rest of the vault). In **headless mode**: pick, cross-check, and draft findings only —
  never edit a content page, never close a finding.

## Token-efficiency checklist

- Use the picker script instead of opening each page + its raws.
- Stay focused: a hit warrants pulling one or two specific files, not re-reading the vault.
- Don't re-read `CLAUDE.md` (auto-attached); the templates here suffice.

## Notes / gotchas

- "Random frequency" = unpredictable cadence, not "rarely". Wire `-Roll` into a post-ingest hook
  or just run it ad hoc; the point is that _which_ pages and _when_ are both unguessable.
- Digests / MOCs are excluded by default (they're roll-ups, not claim-bearing pages) — add
  `-IncludeDigests` to audit them too; for structured digests apply the §8b "flag missing/partial
  data" lens.
- This skill is **read-mostly**: its normal output is questions, not edits. If you find yourself
  rewriting pages without an explicit human "fix it", stop — that's the one thing it must not do.
