---
name: mushroom-mode
description: 'A discovery mode that deliberately ignores the wiki''s existing organisation to surface novel, non-obvious connections between distant notes — modelled on how psilocybin loosens habitual thought patterns so far-apart ideas link up. USE WHEN the user wants fresh cross-topic insight, wants to break out of how their notes are already organised, wants to brainstorm surprising links across unrelated topics, or explicitly invokes "mushroom mode". Picks far-apart anchor notes at random (a "dose" controls how far it reaches), strips their existing structure, forces a bridge, and writes candidate connections to a scratch review area for the user to triage. DO NOT USE for ordinary retrieval or search, for organising or tidying notes, or when the user needs reliable, on-the-rails answers (use vault-ingest / vault-audit / a normal query). NEVER write connections into the canonical wiki — it only proposes candidates; the user is the filter.'
---

# Mushroom Mode

A **generative discovery pass** over the wiki whose whole purpose is to find connections between
notes that the existing structure would never put next to each other. It is the deliberate opposite
of normal search: instead of returning the obvious neighbours (the links the user has probably
already made), it **suppresses the established organisation** so weaker, more surprising links get a
chance to surface.

The metaphor is the point. Psilocybin works by quieting the top-down networks that enforce habitual,
structured thinking; with those constraints relaxed, regions that don't normally talk to each other
start connecting, and distant ideas link up in ways that produce genuine insight. Mushroom mode does
the same thing to a body of notes — it relaxes the structure so far-apart notes can touch.

Unlike the vault's other skills, this one **sits outside** the [`CLAUDE.md`](../../../CLAUDE.md)
schema — it reads the wiki but never files into it. It still honours the vault's core ethos: it is
**human-gated** (it proposes candidates; the user disposes) and it **never auto-edits** a content
page.

## Golden rules (do not violate)

- **Ignore the existing structure — this is the one rule everything else serves.** Folders, `type`,
  `tags`, MOC membership, existing `[[links]]`, ordering — all of it encodes the connections
  **already made**. Work _around_ it, not along it. If a step would end up surfacing links that
  follow the grain of how the notes are already arranged, that step is wrong.
- **Far apart, on purpose.** Anchors are chosen to be _distant_ — different topics, different areas,
  notes that would never normally be considered together. Never pick already-related or
  already-linked notes; those pairings produce nothing new. Deliberate randomness is desired.
- **Strip the context before you look.** Set aside how the anchors are already connected (their
  links, shared tags, MOCs) and read each note's **actual content fresh**. The picker does this for
  you and lists the suppressed structure separately so you can consciously avoid re-deriving it.
- **Be honest about quality.** Most attempts yield nothing — that's expected and fine. If two
  anchors genuinely have nothing meaningful between them, **say so and discard the pairing** rather
  than inventing a strained link. A run may keep very few, or none. Noise is the price of the
  occasional real signal; fabricated links defeat the purpose.
- **Never write into the canonical wiki.** Mushroom mode generates candidates only. It writes them
  to its own scratch area (`state/connections.md`) and surfaces them in chat — **never** into
  `10-Refined/`, `30-Story/`, `index.md`, the MOCs, or even `log.md`. The user keeps
  what's real and discards the rest; **the user is the filter.**

## How a run works

### 1. Pull anchors (one command — do this first)

```pwsh
pwsh -File .github/skills/mushroom-mode/scripts/pick-anchors.ps1
# gentler, more usable links (anchors still share something, but aren't linked):
pwsh -File .github/skills/mushroom-mode/scripts/pick-anchors.ps1 -Dose Low -Draws 5
# reach far from one note the user points at:
pwsh -File .github/skills/mushroom-mode/scripts/pick-anchors.ps1 -Seed "BME280" -Dose High
```

It pulls several independent **anchor sets** (`-Draws`) of far-apart notes (`-Count` each), prints
each anchor's **prose only** — frontmatter, `## Connections` / `## Sources` / transcript trailers and
every `[[link]]` bracket stripped out — plus a per-draw **relatedness score** (0 = nothing in common)
and a **"do NOT reuse"** block of each anchor's real tags/MOCs/links. One shot; you should not need
to open the notes yourself.

### 2. Force a bridge (per draw)

For each anchor set, look at the **stripped content** together and find what _genuinely_ connects
them: a shared underlying idea, an analogy, a tension between them, a principle that shows up in
both, or a question that spans both. Reach for the **non-obvious** link, not the surface one.
Consult the suppressed-structure block only to make sure you are **not** proposing something the
wiki already encodes.

### 3. Be honest — keep the rare signal, bin the rest

Judge each attempt cold. Keep only the ones that are actually interesting; discard the strained ones
explicitly. It is completely fine for a run to produce one keeper out of five draws, or zero. Do not
pad the output to look productive.

### 4. Integrate — deliver candidates for triage

Carry the metaphor through to the **integration** phase, where the raw material gets sorted into
what's actually useful. Write each **keeper** to `state/connections.md` using the format in
[`reference/templates.md`](reference/templates.md): name the two (or more) notes it links and
describe the connection in a plain sentence or two so the user can judge it fast. Then surface the
list in chat and **stop** — the user decides what, if anything, graduates into the wiki.

## Controlling the intensity — the dose

`-Dose` governs how far the mode wanders:

- **Low** — anchors are still _somewhat_ related (they share a tag / MOC / mention) but are **not**
  directly linked; connections are novel yet grounded and usually usable.
- **Medium** — at most a faint overlap; a balance of reach and usability.
- **High** (default) — anchors share **nothing** (no link, tag, MOC, or mention); connections are
  the wildest, the hit rate is the lowest, but the rare success is the most surprising.

A run can range over the **whole** collection, or be **seeded** from one note (`-Seed "<title>"`):
the seed becomes one anchor and the mode reaches far from it for the others.

## When to use / when not to

Use it when the user wants fresh perspective, wants to escape the current organisation of their
thinking, is after cross-topic insight, or explicitly asks for mushroom mode.

Do **not** use it for ordinary retrieval, for organising or tidying notes, or anywhere the user
needs reliable, on-the-rails answers (use `vault-ingest` / `vault-audit` / a normal query instead).
This mode is intentionally unreliable in exchange for novelty — a **brainstorming instrument, not a
search tool**.

## Notes / gotchas

- **Randomness is the feature.** Two runs won't pick the same anchors; pass `-RngSeed <n>` only when
  you deliberately want to reproduce a draw.
- Digests and MOCs are excluded from the anchor pool by default (they're roll-ups, not idea notes);
  add `-IncludeDigests` to let them in.
- `state/connections.md` is **not** part of the wiki graph — it's a holding pen the user triages by
  hand. Nothing in it is canonical until the user chooses to act on it.
- **Headless behaviour is identical to interactive:** draft candidates only, never edit content, and
  never fold results into `index.md` / MOCs / `log.md`.
