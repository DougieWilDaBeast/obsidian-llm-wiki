#!/usr/bin/env python3
"""Generic daily-metrics intake — the device-agnostic core of the wearable pipeline.

This module owns the *normalized* contract that every wearable/biometric source maps
onto, so a future device (Garmin, Suunto, Oura, …) is just a new adapter that emits the
same `daily-metrics/v1` record — no change to storage, aggregation, or the Refined side.

Layering:
    provider raw  ->  adapter.normalize()  ->  daily-metrics/v1  ->  weekly_aggregate()

A normalized daily record:

    {
      "schema": "daily-metrics/v1",
      "date":   "2026-06-18",        # the calendar day the metrics describe (local)
      "source": "whoop",             # which adapter produced it
      "device": "whoop",             # device model, if known
      "metrics": { <canonical key>: <number|None>, ... },
      "workouts": [ { "sport", "start", "end", "strain", "energy_kj",
                      "avg_hr_bpm", "max_hr_bpm", "distance_m" }, ... ]
    }

Adapters fill whatever subset of canonical metrics the device provides; missing keys are
simply absent/None and the aggregator tolerates that. The canonical registry below is the
single source of truth for metric names, units, and direction (is higher better?).
"""
from __future__ import annotations

import datetime as dt
from typing import Iterable

SCHEMA = "daily-metrics/v1"
WEEKLY_SCHEMA = "weekly-metrics/v1"

# Canonical metric registry. Adding a metric here makes it flow through aggregation and
# into the weekly sidecar automatically. `higher_is_better` lets the digest say whether a
# trend is good or bad without hard-coding per-metric logic downstream.
METRICS: list[dict] = [
    {"key": "recovery_score",       "label": "Recovery",          "unit": "%",   "precision": 0, "higher_is_better": True},
    {"key": "hrv_rmssd_ms",         "label": "HRV (rMSSD)",       "unit": "ms",  "precision": 1, "higher_is_better": True},
    {"key": "resting_hr_bpm",       "label": "Resting HR",        "unit": "bpm", "precision": 0, "higher_is_better": False},
    {"key": "spo2_pct",             "label": "Blood oxygen",      "unit": "%",   "precision": 1, "higher_is_better": True},
    {"key": "skin_temp_c",          "label": "Skin temp",         "unit": "C",   "precision": 1, "higher_is_better": None},
    {"key": "sleep_asleep_min",     "label": "Sleep duration",    "unit": "min", "precision": 0, "higher_is_better": True},
    {"key": "sleep_performance_pct","label": "Sleep performance", "unit": "%",   "precision": 0, "higher_is_better": True},
    {"key": "sleep_efficiency_pct", "label": "Sleep efficiency",  "unit": "%",   "precision": 0, "higher_is_better": True},
    {"key": "sleep_consistency_pct","label": "Sleep consistency", "unit": "%",   "precision": 0, "higher_is_better": True},
    {"key": "sleep_disturbances",   "label": "Sleep disturbances","unit": "",    "precision": 0, "higher_is_better": False},
    {"key": "respiratory_rate",     "label": "Respiratory rate",  "unit": "rpm", "precision": 1, "higher_is_better": None},
    {"key": "day_strain",           "label": "Day strain",        "unit": "",    "precision": 1, "higher_is_better": None},
    {"key": "energy_kj",            "label": "Energy burned",     "unit": "kJ",  "precision": 0, "higher_is_better": None},
    {"key": "avg_hr_bpm",           "label": "Average HR",        "unit": "bpm", "precision": 0, "higher_is_better": None},
    {"key": "max_hr_bpm",           "label": "Max HR",            "unit": "bpm", "precision": 0, "higher_is_better": None},
]
METRIC_KEYS = [m["key"] for m in METRICS]
_METRIC_BY_KEY = {m["key"]: m for m in METRICS}


def new_record(date: str, source: str, device: str | None = None) -> dict:
    """Build an empty normalized daily record for `date` (ISO 'YYYY-MM-DD')."""
    return {
        "schema": SCHEMA,
        "date": date,
        "source": source,
        "device": device or source,
        "metrics": {},
        "workouts": [],
    }


def _nums(values: Iterable) -> list[float]:
    return [float(v) for v in values if v is not None]


def _mean(values: list[float]) -> float | None:
    nums = _nums(values)
    return sum(nums) / len(nums) if nums else None


def _round(value: float | None, precision: int) -> float | int | None:
    if value is None:
        return None
    r = round(value, precision)
    return int(r) if precision == 0 else r


def _trend(values: list) -> float | None:
    """Second-half mean minus first-half mean — a coarse within-week direction signal."""
    nums = _nums(values)
    if len(nums) < 2:
        return None
    mid = len(nums) // 2
    early, late = nums[:mid], nums[mid:]
    em, lm = _mean(early), _mean(late)
    if em is None or lm is None:
        return lm if em is None else -em
    return lm - em


def iso_week_bounds(any_date: dt.date) -> tuple[str, dt.date, dt.date]:
    """Return ('YYYY-Www', monday, sunday) for the ISO week containing `any_date`."""
    monday = any_date - dt.timedelta(days=any_date.weekday())
    sunday = monday + dt.timedelta(days=6)
    iso_year, iso_week, _ = any_date.isocalendar()
    return f"{iso_year}-W{iso_week:02d}", monday, sunday


def weekly_aggregate(records: list[dict]) -> dict:
    """Roll up a week's worth of normalized daily records into a deterministic sidecar.

    Order-independent on input; records are sorted by date internally so `trend`/`latest`
    are stable. Returns the `weekly-metrics/v1` structure the agent reads to write prose.
    """
    records = sorted(records, key=lambda r: r.get("date", ""))
    dates = [r["date"] for r in records if r.get("date")]
    week_id, monday, sunday = iso_week_bounds(dt.date.fromisoformat(dates[0])) if dates else ("", None, None)

    metrics_out: dict[str, dict] = {}
    for m in METRICS:
        key, prec = m["key"], m["precision"]
        series = [r.get("metrics", {}).get(key) for r in records]
        present = _nums(series)
        if not present:
            continue
        metrics_out[key] = {
            "label": m["label"],
            "unit": m["unit"],
            "higher_is_better": m["higher_is_better"],
            "n": len(present),
            "mean": _round(_mean(series), prec),
            "min": _round(min(present), prec),
            "max": _round(max(present), prec),
            "latest": _round(next((v for v in reversed(series) if v is not None), None), prec),
            "trend": _round(_trend(series), prec),
        }

    workouts = [w for r in records for w in r.get("workouts", [])]
    by_sport: dict[str, int] = {}
    total_strain = 0.0
    for w in workouts:
        sport = w.get("sport") or "unknown"
        by_sport[sport] = by_sport.get(sport, 0) + 1
        if w.get("strain") is not None:
            total_strain += float(w["strain"])

    return {
        "schema": WEEKLY_SCHEMA,
        "week": week_id,
        "start": monday.isoformat() if monday else None,
        "end": sunday.isoformat() if sunday else None,
        "days_present": len(dates),
        "sources": sorted({r.get("source") for r in records if r.get("source")}),
        "metrics": metrics_out,
        "workouts": {
            "count": len(workouts),
            "total_strain": round(total_strain, 1) if workouts else 0,
            "by_sport": dict(sorted(by_sport.items(), key=lambda kv: (-kv[1], kv[0]))),
        },
    }
