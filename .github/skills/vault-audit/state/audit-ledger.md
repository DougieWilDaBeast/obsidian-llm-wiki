# vault-audit — ledger

Running record of random spot-audits. The `pick-sections.ps1` script **reads** the `audited`
lines below to bias coverage (with `-BiasUnaudited`); the agent **appends** to this file after
each run (see the skill). Open findings stay here, with the human's replies recorded as
_indicators_ — a finding only moves to **Resolved** when the human explicitly directs a fix.

This file is audit machinery, not knowledge — it lives in the skill folder, never in the content
layers, and is never surfaced in `index.md` / MOCs / query answers.

<!-- runs are appended below, newest last -->

## [2026-01-06] audit run (example)

Random spot-check of 2 never-audited pages (`-BiasUnaudited`), cross-checked against cited raws +
peer pages.

- [2026-01-06] audited :: 10-Refined/BME280.md
- [2026-01-06] audited :: 10-Refined/ESP32.md

Clean: **ESP32** (matches the inbox reminder and the voice note); **BME280** (the ±1 °C / few %
RH accuracy claim matches the clipping verbatim).

### Open findings

- (none open)

### Resolved

- (none yet)
