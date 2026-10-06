---
type: dashboard
title: Dashboard
created: 2026-01-04
updated: 2026-01-12
status: active
tags: [meta, dashboard]
---

# Dashboard

Live health view of the wiki, built with Dataview. A **meta-view, not knowledge** — it sits
beside [[index]] and [[log]] and is deliberately not linked into the MOCs. Renders on laptop and
phone (Dataview is enabled on both). If a block shows raw query text, open in **Reading view**.

> [!info] How to read this
> Counts come from each Refined page's frontmatter (`type` / `status` / `sources` / `updated`).
> The **Coverage check** is the important one: it lists raw sources that have **no** Refined page
> yet — it replaces the manual coverage sweep that used to run each ingest session.

---

## Vault stats

Pages by type across `10-Refined/`.

```dataview
TABLE length(rows) AS Pages, sum(rows.sources) AS "Total sources"
FROM "10-Refined"
WHERE type != "dashboard"
GROUP BY type
SORT length(rows) DESC
```

Totals:

```dataview
TABLE WITHOUT ID length(rows) AS "Refined pages", sum(rows.sources) AS "Total sources fed in"
FROM "10-Refined"
WHERE type != "dashboard"
GROUP BY true
```

---

## Coverage check — un-ingested raw sources

Ordinary markdown sources in `00-Raw/Voice`, `00-Raw/Clippings`, `00-Raw/Inbox` and
`00-Raw/OCR` that **no Refined page links to yet**. This should normally be **empty**. Anything
listed here is waiting to be ingested. AI-chat archives are deliberately excluded because Stage A
catalogues them without ingesting every conversation.

```dataview
LIST
FROM "00-Raw/Voice" OR "00-Raw/Clippings" OR "00-Raw/Inbox" OR "00-Raw/OCR"
WHERE length(file.inlinks) = 0
SORT file.name ASC
```

---

## Structured-source digests — freshness

Digest pages for the **high-volume / structured** sources (wearables, task exports), newest
`updated` first. These sources are rolled into **digests, never a page per datapoint**
(`CLAUDE.md` §8b), so the Coverage check above (which expects one Refined page per raw) does
**not** apply to them. Instead, eyeball that each live source has a **recent** digest here.

```dataview
TABLE WITHOUT ID file.link AS Digest, provenance AS Source, updated AS Updated, sources AS Days/Tasks
FROM "10-Refined"
WHERE type = "source" AND contains(tags, "digest")
  AND contains(list("wearable", "tasks"), provenance)
SORT updated DESC, file.name ASC
```

> [!note] Raw `.json` exports aren't Obsidian notes, so Dataview can't track them.
> The authoritative raw-vs-digest coverage check is the pipeline itself
> (`pipeline/wearables/` weekly sidecars) plus `new-raws.ps1`. A digest going stale here while its pipeline keeps landing raws is the signal
> to run a digest-refresh ingest.

---

## Orphans — Refined pages with no real inbound link

Refined pages whose only links come from `index` / `log` / `Dashboard` (i.e. not woven into the
knowledge graph). Candidates to cross-link or fold into a related page.

```dataview
LIST
FROM "10-Refined"
WHERE type != "dashboard" AND type != "moc"
WHERE length(filter(file.inlinks, (l) => !contains(["index", "log", "Dashboard"], l.file.name))) = 0
SORT file.name ASC
```

---

## Stubs to flesh out

Pages flagged `status: stub`, most-sourced first (high sources + still a stub = ripe for promotion).

```dataview
TABLE type AS Type, sources AS Sources
FROM "10-Refined"
WHERE status = "stub"
SORT sources DESC, file.name ASC
```

---

## Most-sourced pages — knowledge hubs

Entities, concepts and projects that accumulate the most sources.

```dataview
TABLE type AS Type, sources AS Sources, status AS Status
FROM "10-Refined"
WHERE contains(list("entity", "concept", "project"), type)
SORT sources DESC
LIMIT 15
```

---

## Recently updated

```dataview
TABLE type AS Type, updated AS Updated, sources AS Sources
FROM "10-Refined"
WHERE type != "dashboard"
SORT updated DESC, file.name ASC
LIMIT 15
```

## Recently created

```dataview
TABLE type AS Type, created AS Created
FROM "10-Refined"
WHERE type != "dashboard"
SORT created DESC, file.name ASC
LIMIT 15
```

---

## Recent activity

Newest source pages (approximates the ingest timeline). For the full chronological record of
ingests and lints, see [[log]].

```dataview
TABLE created AS Created
FROM "10-Refined"
WHERE type = "source"
SORT created DESC, file.name ASC
LIMIT 12
```
