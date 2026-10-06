---
type: story-index
title: Story Arcs
created: 2026-01-15
updated: 2026-01-15
---

# Story Arcs

The **arc views** over the Book — cross-cutting reading paths that the flat `book_order` sequence
in [[story-index]] can't show on its own. A chapter can sit on several arcs, or none. Membership
lives in each chapter's `arcs:` frontmatter; this page is a **view**, not a folder.

## craft — learning to build things that work

```dataview
TABLE WITHOUT ID file.link AS Chapter, book_order AS "Order", era AS Era, status AS Status
FROM "30-Story"
WHERE type = "story-chapter" AND contains(arcs, "craft")
SORT book_order ASC
```
