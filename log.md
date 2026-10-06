# log.md — operation timeline

> Append-only. Every operation gets an entry prefixed `## [YYYY-MM-DD] <op> | <desc>` so it's
> greppable: `grep "^## \[" log.md | tail -10`. Example entries for the synthetic demo vault.

## [2026-01-04] ingest | Voice — weather station sensor ideas

- Created [[2026-01-04 Voice — weather station sensor ideas]] (source page, verbatim transcript kept).
- Created [[Backyard Weather Station]] (project), [[BME280]] (entity), [[ESP32]] (entity).
- Created stub [[Sensor fusion]] (flagged for promotion if it recurs).
- Created [[Weather Station MOC]]; updated index.

## [2026-01-04] ingest | Clipping — BME280 sensor overview

- Created [[Clipping — BME280 sensor overview]] (source page).
- Updated [[BME280]] (sources 1→2): independently confirms the self-heating caveat and adds
  interface/accuracy detail. Updated index.

## [2026-01-05] ingest | Inbox — order a spare ESP32

- Minor one-liner → added dated bullet to [[2026-01 Captures]] (no standalone source page).
- Updated [[ESP32]] (added 3V3 warning + spare-ordered note, sources 1→2). Updated index.

## [2026-01-10] stage-a | AI-chat export archived

- Ran `split_exports.py` on a Claude export: 2 conversations archived to `00-Raw/AI-Chats/Claude/`,
  [[AI-Chats catalog]] generated. Nothing ingested (Stage A).

## [2026-01-10] stage-b | mine 1 AI chat — weather station logging

- Created [[AI-Chat — Should I log the weather station to a Pi or the cloud]] (`trust: low`; one
  model claim quarantined in `[!review]`). Created [[AI Conversations MOC]].
- Updated [[Backyard Weather Station]] with the author's Pi + MQTT decision. Flagged one story
  candidate. Updated index.

## [2026-01-11] ingest | OCR — bench wiring sketch

- Created [[OCR — bench wiring sketch]] (verbatim OCR text kept). Updated
  [[Backyard Weather Station]] (sources 3→4) and [[Weather Station MOC]]. Updated index.

## [2026-01-12] ingest | Whoop — 2026-W02 digest

- Created [[Whoop]] (entity) and [[Whoop — 2026-W02 digest]] from the weekly sidecar (5 of 7
  days; gap flagged in `[!review]`). Added the 2026-01-07 capture to [[2026-01 Captures]].
  Updated index.

