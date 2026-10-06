# mushroom-mode — templates

Operational templates for the discovery skill. Mushroom mode **proposes**, it never commits — every
entry below is a candidate the user triages by hand. Nothing here is canonical.

---

## 1. Proposed-connection run (append keepers to `state/connections.md`)

One block per run. Write **only genuine keepers**; discard strained pairings rather than padding.

```markdown
## [YYYY-MM-DD] mushroom run · dose <Low|Medium|High> · <N> draws → <k> keeper(s)

- **[[Note A]] × [[Note B]]** — <the non-obvious link, in 1–2 plain sentences: the shared idea /
  analogy / tension / principle / spanning question>.
  _kind: analogy | shared-principle | tension | spanning-question_ ·
  _spark: faint | worth-a-look | strong_
- **[[Note C]] × [[Note D]] × [[Note E]]** — <…>. _kind: … · spark: …_

### Discarded (optional — for honesty about the hit rate)

- [[Note F]] × [[Note G]] — nothing meaningful between them.
```

Guidance:

- **Name the notes, describe the bridge plainly.** The user should be able to judge each in seconds.
- **Reach for the non-obvious.** If the connection is one the two notes' tags/MOCs/links already
  imply, it is not a keeper — that is the structure talking.
- **`spark`** is your honest read of how alive the link feels, not a correctness score. `faint` is
  allowed; `fabricated` is not.

## 2. Surfacing to the user (chat)

After writing keepers, present them in chat as a short list, then stop:

```markdown
Mushroom run (dose High, 5 draws) — 2 kept:

1. **[[Note A]] × [[Note B]]** — <one-sentence bridge>.
2. **[[Note C]] × [[Note D]]** — <one-sentence bridge>.

(3 draws discarded as strained.) These are candidates only — kept in
`.github/skills/mushroom-mode/state/connections.md` for you to keep or bin. Nothing was written into
the wiki.
```

> The user is the filter. Do not act on a keeper (create a page, add a link, edit a note) unless the
> user explicitly asks — and if they do, that is ordinary `vault-ingest` / editing work, not
> mushroom mode.
