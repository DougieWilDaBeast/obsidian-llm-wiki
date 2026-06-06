---
type: voice-transcript
source_audio: Voice 260104_191233.m4a
recorded: 2026-01-04T19:12:33
transcribed: 2026-01-04
model: faster-whisper-small
duration_s: 64
---

Okay so I've been thinking about the backyard weather station project again. The big question is which sensor to use for temperature and humidity. I keep coming back to the BME280 because it does temperature, humidity and pressure all in one little board and it talks over I2C which is dead simple on the ESP32. The only thing I'm not sure about is the self-heating issue, apparently the chip warms itself up a bit so the temperature reads a degree or two high if you mount it right next to the wifi radio. I should put the sensor on a little arm away from the board. Also I want to log everything to the Pi over MQTT eventually but for the first version just getting a reading every minute and printing it is fine. Oh and I need to order a spare ESP32 because I fried the last one with five volts on a three-three pin.
