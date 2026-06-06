---
type: source
title: Clipping — BME280 sensor overview
created: 2026-01-04
updated: 2026-01-04
status: active
tags: []
sources: 1
---

# Clipping — BME280 sensor overview

A primer on the [[BME280]] environmental sensor, clipped while researching the
[[Backyard Weather Station]] sensor choice.

## Summary

- The [[BME280]] combines temperature, humidity, and pressure in one low-cost, low-power
  package — confirming the appeal noted in [[2026-01-04 Voice — weather station sensor ideas]].
- Supports both I2C and SPI; I2C needs just SDA/SCL + power/ground. Default address 0x76/0x77.
- Accuracy ≈ ±1 °C temperature, a few % RH humidity.
- Independently confirms the **self-heating** caveat: a board mounted against a warm MCU can
  read 1–2 °C high. Mount away from heat sources or read infrequently.

## Connections

- [[BME280]] · [[Backyard Weather Station]]

## Sources

- Raw: [[Clipping — BME280 sensor overview]] (`00-Raw/Clippings/`)
