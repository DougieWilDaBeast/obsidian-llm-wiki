---
type: story-chapter
title: The First Workshop
era: first-builds
arcs: [craft]
book_order: 300
story_date: 2026-01
status: living
fidelity: grounded
voice: first-person
aliases: []
created: 2026-01-15
updated: 2026-01-15
sources: 4
---

# The First Workshop

The first ESP32 died because I put 5 V into a 3V3 pin. I wrote "order a spare" in my inbox and
then forgot to order it.

The second attempt went slower on purpose. I drew the wiring on paper first and wrote "NOT 5V!!"
next to the power line, underlined twice. The sensor went on a ten-centimetre arm, away from the
wifi antenna, because the BME280 reads a degree or two high if it sits next to a warm board.

I finished the soldering at two in the morning on a work night. The strap on my wrist scored the
next day at 38% recovery. The headers were straight, though.

When it came to where the readings should go, I chose a Raspberry Pi in the house over a cloud
service. I would rather own the data than have the nicer dashboard.

---

## Sources & fidelity

- **fidelity:** grounded — every event above is in a dated raw note; the "rather own the data"
  line is the author's own words from the AI chat.
- **Evidence:** [[Story — Spine]] · [[2026-01 Captures]] · [[OCR — bench wiring sketch]] ·
  [[Whoop — 2026-W02 digest]] · [[AI-Chat — Should I log the weather station to a Pi or the cloud]].

## Revisions

- **2026-01-15** — first draft, written from the January captures, the wiring sketch, the W02
  digest and the logging decision. Craft rubric applied (one scene: the 2 am soldering).
