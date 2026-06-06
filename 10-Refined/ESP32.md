---
type: entity
title: ESP32
created: 2026-01-04
updated: 2026-01-05
status: active
tags: [electronics]
sources: 2
---

# ESP32

A low-cost wifi/Bluetooth microcontroller — the compute board for the
[[Backyard Weather Station]].

## Key points

- Drives the [[BME280]] over I2C for the first version of the project.
- Runs on **3.3 V logic** — applying 5 V to a 3V3 pin can destroy the board (a spare was
  ordered after exactly that, see [[2026-01 Captures]]).
- v1 firmware goal: read the sensor once a minute and print; MQTT logging to a Raspberry Pi
  comes later (see [[Sensor fusion]]).

## Connections

- [[BME280]] · [[Backyard Weather Station]]

## Sources

- [[2026-01-04 Voice — weather station sensor ideas]]
- [[2026-01 Captures]]
