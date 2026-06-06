---
type: source
title: 2026-01-04 Voice — weather station sensor ideas
created: 2026-01-04
updated: 2026-01-04
status: active
tags: []
sources: 1
---

# 2026-01-04 Voice — weather station sensor ideas

Planning note for the [[Backyard Weather Station]] project, deciding on the temperature/
humidity sensor.

## Summary

- Leaning towards the [[BME280]] because it combines temperature, humidity, and pressure on
  one board and speaks I2C, which is simple on the [[ESP32]].
- Concern: BME280 **self-heating** can read 1–2 °C high if mounted next to the wifi radio —
  plan is to mount the sensor on a small arm away from the board.
- v1 scope: read once a minute and print. Logging to a Raspberry Pi over MQTT is a later
  goal (see [[Sensor fusion]] for the longer-term plan).
- Action: order a spare [[ESP32]] (the last one was fried by 5 V on a 3V3 pin).

## Connections

- [[Backyard Weather Station]] · [[BME280]] · [[ESP32]] · [[Sensor fusion]]

## Sources

- Raw: [[2026-01-04 Voice — weather station sensor ideas]] (`00-Raw/Voice/`)

## Original transcript

> Okay so I've been thinking about the backyard weather station project again. The big question
> is which sensor to use for temperature and humidity. I keep coming back to the BME280 because
> it does temperature, humidity and pressure all in one little board and it talks over I2C which
> is dead simple on the ESP32. The only thing I'm not sure about is the self-heating issue,
> apparently the chip warms itself up a bit so the temperature reads a degree or two high if you
> mount it right next to the wifi radio. I should put the sensor on a little arm away from the
> board. Also I want to log everything to the Pi over MQTT eventually but for the first version
> just getting a reading every minute and printing it is fine. Oh and I need to order a spare
> ESP32 because I fried the last one with five volts on a three-three pin.
