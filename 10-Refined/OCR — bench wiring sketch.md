---
type: source
title: OCR — bench wiring sketch
created: 2026-01-11
updated: 2026-01-11
status: active
tags: [ocr, weather-station]
provenance: ocr
trust: high
sources: 1
---

# OCR — bench wiring sketch

A photographed hand-drawn wiring note for the [[Backyard Weather Station]]: how the [[BME280]]
connects to the [[ESP32]] over I2C.

## Summary

- Power the BME280 from **3V3, never 5 V** (underlined in the sketch; the same mistake that fried
  the last [[ESP32]]).
- I2C on GPIO22 (SCL) and GPIO21 (SDA); address 0x76 with SDO tied to ground.
- Mount the sensor on a ~10 cm arm away from the wifi antenna, matching the self-heating caveat
  on [[BME280]].

## Connections

- [[Backyard Weather Station]] · [[BME280]] · [[ESP32]] · [[Weather Station MOC]]

## Sources

- [[00-Raw/OCR/OCR — bench wiring sketch]]

## Original scan (OCR)

> BME280 -> ESP32
> VIN -> 3V3 (NOT 5V!!)
> GND -> GND
> SCL -> GPIO22
> SDA -> GPIO21
> addr 0x76 (SDO to GND)
> sensor on 10cm arm, away from wifi antenna
