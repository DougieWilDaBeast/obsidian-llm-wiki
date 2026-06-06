---
type: clipping
title: BME280 — Combined humidity, pressure and temperature sensor (overview)
source: https://example.com/bme280-overview
author: Example Electronics
published: 2025-11-02
clipped: 2026-01-04
site: example.com
description: A primer on the BME280 environmental sensor for hobbyist projects.
tags: clipping
---

> NOTE: This is synthetic example content for the obsidian-llm-wiki demo. It is not a real
> article and the URL is not real.

# BME280 — Combined humidity, pressure and temperature sensor (overview)

The BME280 is a small environmental sensor that combines three measurements — temperature,
relative humidity, and barometric pressure — in a single package. It is popular in hobbyist
electronics because of its low cost, low power draw, and simple digital interfaces.

## Interfaces

The sensor supports both I2C and SPI. For most microcontroller projects I2C is the easiest:
two wires (SDA/SCL) plus power and ground. The default I2C address is commonly 0x76 or 0x77
depending on the breakout board.

## Accuracy and the self-heating caveat

Temperature accuracy is typically within ±1 °C and humidity within a few percent RH. A common
pitfall is **self-heating**: the sensor and nearby components dissipate heat, so a board mounted
directly against a warm microcontroller can read a degree or two above ambient. Mounting the
sensor away from heat sources, or reading infrequently, mitigates this.

## Typical use

Read the registers over I2C, apply the factory calibration coefficients, and you get
temperature, humidity, and pressure. From pressure you can also estimate altitude.
