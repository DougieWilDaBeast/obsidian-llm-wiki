---
type: project
title: Backyard Weather Station
created: 2026-01-04
updated: 2026-01-05
status: active
tags: [project]
sources: 2
---

# Backyard Weather Station

A hobby project to log temperature, humidity, and pressure in the backyard using an
[[ESP32]] and a [[BME280]] sensor.

## State

- **Sensor chosen:** [[BME280]] (one board for temp/humidity/pressure, simple I2C).
- **Compute:** [[ESP32]].
- **v1 scope:** read once a minute and print over serial. No logging yet.
- **Later:** publish readings to a Raspberry Pi over MQTT and combine multiple inputs — see
  [[Sensor fusion]].

## Open threads / decisions

- Mount the [[BME280]] on a small arm **away from the board** to avoid self-heating error
  (reads 1–2 °C high next to the wifi radio).
- Order a spare [[ESP32]] (previous one fried by 5 V on a 3V3 pin). — see [[2026-01 Captures]]

## Connections

- [[ESP32]] · [[BME280]] · [[Sensor fusion]] · [[Weather Station MOC]]

## Sources

- [[2026-01-04 Voice — weather station sensor ideas]]
- [[Clipping — BME280 sensor overview]]
