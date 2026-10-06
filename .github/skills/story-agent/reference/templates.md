# Story templates

Copy-paste skeletons for the `30-Story/` layer. Keep frontmatter keys in this order. Dates are
`YYYY-MM-DD`. Schema: `CLAUDE.md` §12.

## Thread page (`Story — <thread>.md`)

```markdown
---
type: story
title: <Thread>
thread: <slug> # spine | want-vs-need | arc | theme | character | velocity | …
lens: [direction] # direction | velocity | intangibles  (one or more)
status: living # draft | living | canonical | retired
fidelity: grounded # sketch | grounded | well-evidenced
created: <today>
updated: <today>
sources: 1 # how many evidence sources feed this thread
---

# Story — <Thread>

One- or two-sentence statement of the thread, in plain words.

## <free-form sections — evolve as the thread grows>

- Grounded prose with [[evidence links]] into Raw/Refined.

## Entries

<!-- newest first; each entry dated, with its own fidelity + evidence links -->

- **<today>** · _grounded_ — <what this thread really says>. Evidence:
  [[10-Refined/…]] · [[00-Raw/…]]. (Or the author's own stated framing, e.g. a raw story-dossier note.)

## Connections

- [[Story — …]] · [[Story — …]]
```

## Chapter page (`Chapter — <title>.md`) — the Book

The voiced, first-person memoir. Ordered by `book_order` (story-time), not when written. Ends
with two mandatory footers. Schema: `CLAUDE.md` §12d / §12f / §12g.

```markdown
---
type: story-chapter
title: The First Workshop
era: first-builds # free-form slug for the life-era this chapter covers
arcs: [] # cross-cutting arc views: career | craft | relationships | health | … (several, or none — see Story — Arcs)
book_order: 300 # gap-numbered (100, 200, 300…) so earlier chapters insert without renumbering
story_date: 2025-09/2026-01 # approx point/range on the LIFE timeline (not the ingest date)
status: draft # stub | draft | living | canonical | retired
fidelity: grounded # sketch | grounded | well-evidenced
voice: first-person
aliases: [] # old titles kept here when re-titled (§12g), so links survive
created: <today>
updated: <today>
sources: 1
---

# <Title>

First-person, arc-shaped prose written _from_ the Bible threads' evidence. Held to the
[`craft-rubric.md`](craft-rubric.md): concrete specifics over generic summary, ≥ 1 real scene, the
author's own plain voice, stock phrases cut. Keep the honest friction in — a tension-free chapter is
a brochure. A horizon (future) chapter is `fidelity: sketch` and flagged as anticipation, not record.

---

## Sources & fidelity

- **fidelity:** <sketch | grounded | well-evidenced> — one line on why.
- **Evidence:** [[Story — …]] (the threads this expresses) · [[10-Refined/…]] · [[00-Raw/…]] ·
  [[00-Raw/…]] (the author's own framing, if any).

## Revisions

- **<today>** — first draft, written from <sources>. _Voice: first-person — provisional._
```

When a chapter is **re-titled** (§12g), add the old title to `aliases:` and log it in `## Revisions`.
When a chapter is **corrected**, the correction is a _new_ `00-Raw/` note (raws are immutable);
record both the old and new wording in `## Revisions` with the superseding raw linked.

## Draft (`_Drafts/Story — <thread>.md` or `_Drafts/Chapter — <title>.md`)

Same as a thread/chapter page but `status: draft`, holding the not-yet-grounded version. Promote
into `30-Story/` as `living` once it's evidenced, and `canonical` once the human signs off.

## Single dated entry (to append under `## Entries`)

```markdown
- **<today>** · _sketch | grounded | well-evidenced_ — <the entry>. Evidence: [[10-Refined/…]] ·
  [[00-Raw/…]].
```

## story-index.md row

```markdown
| [[Story — Thread]] | direction | grounded | living | <today> | 2 |
```
