---
name: story-agent
description: 'Maintain the author''s voiced self-narrative — the public-but-meta 30-Story layer. USE WHEN the user asks to work on "my story", capture direction/velocity/intangibles, define or refresh the spine/throughline/arc/theme/character, build a narrative dossier of who they are or are becoming, or prepare self-narrative as seed context for another system. Gathers narrative evidence across 00-Raw + 10-Refined, drafts/updates Story — <thread> pages with evidence + a fidelity rating, and canonises settled threads after human sign-off. DO NOT USE for ordinary ingest (use vault-ingest) or for writing about OTHER people, and NEVER canonise without human sign-off.'
---

# Story Agent

The workflow for the vault's **public self-narrative layer** (`30-Story/`) — the _voiced_, exportable
account of the author. The authoritative schema is [`CLAUDE.md`](../../../CLAUDE.md)
§12 — this skill is the **operational shortcut**: the gather script, templates, and exact steps.
Origin: the user wanting a deliberate, exportable account of "what and who I am trying to
achieve / have achieved — direction, velocity, intangibles."

## Golden rules (from CLAUDE.md §12 — do not violate)

- **Public-but-meta.** Story is a meta-layer beside `index.md` / `log.md` with its **own**
  `story-index.md`; it is not folded into the MOCs. It links _into_ Raw/Refined for evidence, and
  Refined _may_ link back to it.
- **Grounded, never inflated.** Every claim traces to evidence (or is flagged as the author's own
  stated framing). Set `fidelity` honestly. The story must never outrun the record.
- **Light fidelity gate.** The agent may write/refresh a thread to `status: living` on its own.
  Only `status: canonical` (the settled, exportable version) needs the human's sign-off. In
  headless mode, never canonise.
- **Accumulate, don't sprawl.** One `Story — <thread>` page per thread, with **dated entries** —
  let threads evolve; don't pre-build rigid buckets.
- **Two tiers.** The **Bible** = `Story — <thread>` pages (analytical lenses, timeless). The
  **Book** = `Chapter — <title>` pages (first-person memoir written _from_ the threads). Same
  evidence, same fidelity discipline; each chapter links back to the threads it expresses. See
  `CLAUDE.md` §12d.
- **The Book lives in story-time.** Chapters are ordered by `book_order` (when things _happened_),
  not when written; older memories backfill earlier slots, the start point moves backward over
  time, and the forward/horizon edge is `fidelity: sketch`. Best effort, not perfection — chapters
  are provisional and re-titleable.
- **Arcs are views; export is output.** Each chapter carries an `arcs:` list rendered by
  `Story — Arcs` (a cross-cutting view over the Book, **never** a folder). `90-Export/` is generated
  _from_ the Story layer by `assemble-book.ps1` — never hand-edited, and never allowed to read
  outside `30-Story/` (CLAUDE.md §12d, §13).

## Method — craft a story, not a CV

Read the evidence through narrative tools, not biography: **spine / controlling idea**,
**character over plot**, **want vs need**, **arc / transformation**, **theme**, and **honest
stakes**. The user's three lenses map onto these: _direction_ (spine, want/need, where it heads),
_velocity_ (arc, momentum, what keeps stalling), _intangibles_ (character, theme, voice).

## Workflow

### 1. Gather (one command — do this first)

For a **Bible thread**, gather by theme:

```pwsh
pwsh -File .github/skills/story-agent/scripts/gather-narrative.ps1 -Theme "weather station"
# widen with extra keywords / synonyms:
pwsh -File .github/skills/story-agent/scripts/gather-narrative.ps1 -Theme "purpose" -Keywords vocation,calling,teach
```

For a **Book chapter**, gather by **era / time window** instead (every note in the window,
oldest-first):

```pwsh
pwsh -File .github/skills/story-agent/scripts/gather-narrative.ps1 -Era first-builds -Since 2026-01-01 -Until 2026-03-31
```

It prints every raw + Refined passage (by theme, or every note in the window for an era),
**oldest-first**, so the arc and any change-over-time are visible. It assembles evidence only —
it interprets nothing.

### 2. Read for the narrative signals

- **Spine** — what single idea does all of it express?
- **Want vs Need** — the stated external goal vs the internal change that actually unlocks it.
- **Arc** — how has it changed over time? What was the forcing function?
- **Theme** — what meaning recurs across unrelated domains?
- **Stakes** — the honest friction. Keep it in; a tension-free story is a brochure.

Be honest about `fidelity`: `sketch` (one faint source), `grounded` (recurs across ≥2 sources or
the author's explicit framing), `well-evidenced` (multiple corroborating sources).

### 3. Update the Bible (threads)

Write or update a `Story — <thread>` page using the template in
[`reference/templates.md`](reference/templates.md), with **evidence links** and an honest
`fidelity`. The agent may set `status: living` directly. For a brand-new, low-confidence thread,
stage it in `30-Story/_Drafts/` as `status: draft` first.

### 4. Update the Book (chapters)

Classify each genuinely new piece of narrative evidence and route it (see `CLAUDE.md` §12g):

- **Enrich** an era that already has a chapter → weave it into that `Chapter — <title>` (an
  even-earlier memory may appear as an in-chapter _flashback_).
- **New chapter** for an era with no chapter yet, or a substantial stand-alone beat → create
  `Chapter — <title>` at the right `book_order` (gap-numbered; earlier eras fill in over time).
- **Re-frame** when the _meaning_ of a chapter changes → rewrite the prose; **re-title** if it's
  now about something else, keeping the old title in `aliases:` and logging it in `## Revisions`.
- **Correction** when the author says something is wrong → the correction is a _new_ `00-Raw/`
  note (raws are immutable); rewrite the chapter and record **both** old + new in `## Revisions`
  with the superseding raw linked.

Write chapters in the **first person**, keep the honest friction in, and never let a chapter
outrun its `## Sources & fidelity` footer. New / heavily-rewritten chapters stage in `_Drafts/`.

**Write to the craft rubric.** Every chapter is held to
[`reference/craft-rubric.md`](reference/craft-rubric.md) — concrete specifics over generic summary,
at least one real scene, the author's own plain voice, stock phrases cut. After drafting, self-review
against its eight checks and note in `## Revisions` that the rubric was applied. The rubric governs
_prose_, never facts — specific ≠ invented; every detail still traces to a listed source.

**Detect from content, not tags.** The author won't reliably tag memoir material — this repo
carries many parallel threads. A narrate pass **reads** what's new in Raw/Refined and decides what
is autobiographical / reflective / corrective. Don't depend on a capture tag.

**Tag the arcs.** Every chapter carries an `arcs:` frontmatter list — the cross-cutting reading
paths rendered on `Story — Arcs`. When you create or re-frame a chapter, set its `arcs:` from the
current arcs (e.g. `career`, `craft`, `relationships`, `health`); a chapter may sit on **several,
or none** (childhood/character vignettes are often `arcs: []`). Don't force a fit — arcs are honest
trajectories, not labels, and a new arc is added only when one genuinely earns it. The per-arc
reading orders update themselves from this field; no list to maintain by hand.

### 5. Canonise (the gate)

When a thread **or chapter** is settled and ready to be the **exportable** version, present it to
the human and set `status: canonical` only on sign-off. Update the row in
[`30-Story/story-index.md`](../../../30-Story/story-index.md).

### 6. Export (regenerate the Book)

After canonising — or any change to what should ship — regenerate the terminal `90-Export/`
artifacts so the exportable Book stays current (CLAUDE.md §13):

```pwsh
pwsh -File .github/skills/story-agent/scripts/assemble-book.ps1          # default: living + canonical
pwsh -File .github/skills/story-agent/scripts/assemble-book.ps1 -ByArc   # + one manuscript per arc
```

`Book.md` + `Seed.md` are committed and refreshed here; per-arc `Book — <arc>.md` are git-ignored.
The builder reads `30-Story/` only and **asserts it never reads outside that folder** — don't weaken that.
Commit the refreshed exports alongside the canonise change.

### 7. Keep the layers straight

Story is public: it **may** be referenced from Refined and appears in its own `story-index.md`.
Keep anything you would not want exported out of it — Story is built to travel.
Commit with a clear message, e.g. `story: refresh Velocity thread` or `story: new chapter`.

## Status lifecycle

`draft` (staged) → `living` (agent-maintained, grounded) → `canonical` (human-signed, exportable)
or `retired` (superseded — mark retired with the date, keep the entry, never delete).
