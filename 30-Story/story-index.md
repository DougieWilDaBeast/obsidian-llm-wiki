---
type: story-index
title: Story Index
created: 2026-01-15
updated: 2026-01-15
---

# Story Index

Catalog of the **self-narrative** layer (`30-Story/`) for the synthetic example author. Two
tiers: the **Book** (chapters you read) and the **Bible** (the threads that back them). This is
the layer's own index — a **meta-view beside [[index]] and [[log]]**, deliberately not folded
into the MOCs. Schema: `CLAUDE.md` §12.

> [!info] How to read this
> `fidelity` = how well-evidenced a page is (`sketch` < `grounded` < `well-evidenced`).
> `status` = `draft` → `living` (agent-maintained) → `canonical` (human-signed, exportable).
> The **Book** reads in `Order` (story-time, not when written); the **Bible** is timeless lenses.

## The Book — chapters

```dataview
TABLE WITHOUT ID file.link AS Chapter, book_order AS "Order", era AS Era, status AS Status, fidelity AS Fidelity
FROM "30-Story"
WHERE type = "story-chapter"
SORT book_order ASC
```

## The Bible — threads

| Thread             | Lens      | Fidelity | Status | Updated    | Sources |
| ------------------ | --------- | -------- | ------ | ---------- | ------- |
| [[Story — Spine]]  | direction | sketch   | living | 2026-01-15 | 2       |

## Views

- [[Story — Arcs]] — per-arc reading orders over the Book.
