#!/usr/bin/env python3
"""WHOOP adapter — maps a stored raw WHOOP envelope to the generic `daily-metrics/v1`.

This is the *only* WHOOP-specific normalization in the pipeline. Two raw envelope shapes
are handled, both written by the pull/import scripts into 00-Raw/Wearables/whoop/:

  * `whoop-raw/v2`     — from the v2 API (cycle / recovery / sleep / workout records)
  * `whoop-export/v1`  — from the manual "Download my data" CSV bundle (one merged row/day)

Field names mirror the WHOOP v2 API data models (recovery.score.hrv_rmssd_milli,
sleep.score.sleep_performance_percentage, cycle.score.strain, …). Keeping this isolated
means a different device just ships its own adapter with the same `normalize()` contract.
"""
from __future__ import annotations

from typing import Any

import daily_metrics

SOURCE = "whoop"


def _g(obj: Any, *path, default=None):
    """Safe nested get: _g(rec, 'score', 'strain')."""
    cur = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur or cur[key] is None:
            return default
        cur = cur[key]
    return cur


def _ms_to_min(value) -> float | None:
    return round(value / 60000.0, 1) if isinstance(value, (int, float)) else None


def normalize(envelope: dict) -> dict:
    schema = envelope.get("schema", "")
    if schema.startswith("whoop-export"):
        return _normalize_export(envelope)
    return _normalize_api(envelope)


def _normalize_api(envelope: dict) -> dict:
    rec = daily_metrics.new_record(envelope["date"], SOURCE, device="whoop")
    m = rec["metrics"]

    recovery = envelope.get("recovery") or {}
    rscore = recovery.get("score") or {}
    m["recovery_score"] = rscore.get("recovery_score")
    m["hrv_rmssd_ms"] = rscore.get("hrv_rmssd_milli")
    m["resting_hr_bpm"] = rscore.get("resting_heart_rate")
    m["spo2_pct"] = rscore.get("spo2_percentage")
    m["skin_temp_c"] = rscore.get("skin_temp_celsius")

    # Pick the main sleep (non-nap, longest in-bed) for the day's sleep metrics.
    sleeps = [s for s in (envelope.get("sleep") or []) if isinstance(s, dict)]
    main = _pick_main_sleep(sleeps)
    if main:
        sscore = main.get("score") or {}
        stage = sscore.get("stage_summary") or {}
        in_bed = stage.get("total_in_bed_time_milli")
        awake = stage.get("total_awake_time_milli") or 0
        no_data = stage.get("total_no_data_time_milli") or 0
        if isinstance(in_bed, (int, float)):
            m["sleep_asleep_min"] = _ms_to_min(in_bed - awake - no_data)
        m["sleep_performance_pct"] = sscore.get("sleep_performance_percentage")
        m["sleep_efficiency_pct"] = sscore.get("sleep_efficiency_percentage")
        m["sleep_consistency_pct"] = sscore.get("sleep_consistency_percentage")
        m["sleep_disturbances"] = stage.get("disturbance_count")
        m["respiratory_rate"] = sscore.get("respiratory_rate")

    cscore = _g(envelope, "cycle", "score") or {}
    m["day_strain"] = cscore.get("strain")
    m["energy_kj"] = cscore.get("kilojoule")
    m["avg_hr_bpm"] = cscore.get("average_heart_rate")
    m["max_hr_bpm"] = cscore.get("max_heart_rate")

    for w in envelope.get("workouts") or []:
        wscore = w.get("score") or {}
        rec["workouts"].append({
            "sport": w.get("sport_name"),
            "start": w.get("start"),
            "end": w.get("end"),
            "strain": wscore.get("strain"),
            "energy_kj": wscore.get("kilojoule"),
            "avg_hr_bpm": wscore.get("average_heart_rate"),
            "max_hr_bpm": wscore.get("max_heart_rate"),
            "distance_m": wscore.get("distance_meter"),
        })

    rec["metrics"] = {k: v for k, v in m.items() if v is not None}
    return rec


def _pick_main_sleep(sleeps: list[dict]) -> dict | None:
    if not sleeps:
        return None
    non_nap = [s for s in sleeps if not s.get("nap")] or sleeps

    def in_bed(s: dict) -> float:
        v = _g(s, "score", "stage_summary", "total_in_bed_time_milli")
        return float(v) if isinstance(v, (int, float)) else 0.0

    return max(non_nap, key=in_bed)


# --- Manual export (CSV) -------------------------------------------------------------
# The "Download my data" bundle merges cycle+sleep+recovery into one row per day. The
# importer stores that row verbatim under envelope["row"]; we map known headers here.
# Header matching is case-insensitive and substring-based to survive minor label changes.
_EXPORT_MAP = {
    "recovery_score": ["recovery score"],
    "resting_hr_bpm": ["resting heart rate"],
    "hrv_rmssd_ms": ["heart rate variability"],
    "spo2_pct": ["blood oxygen"],
    "skin_temp_c": ["skin temp"],
    "day_strain": ["day strain"],
    "energy_kj": ["energy burned"],          # NOTE: export is in cal — converted below
    "avg_hr_bpm": ["average hr"],
    "max_hr_bpm": ["max hr"],
    "sleep_performance_pct": ["sleep performance"],
    "sleep_efficiency_pct": ["sleep efficiency"],
    "sleep_consistency_pct": ["sleep consistency"],
    "respiratory_rate": ["respiratory rate"],
    "sleep_asleep_min": ["asleep duration"],
    "sleep_disturbances": ["sleep disturbance", "disturbances"],
}


def _normalize_export(envelope: dict) -> dict:
    rec = daily_metrics.new_record(envelope["date"], SOURCE, device="whoop")
    row = {str(k).strip().lower(): v for k, v in (envelope.get("row") or {}).items()}
    out: dict = {}
    for key, needles in _EXPORT_MAP.items():
        val = _match_column(row, needles)
        if val is None:
            continue
        if key == "energy_kj":
            val = round(val * 4.184, 0)  # WHOOP export 'Energy burned (cal)' -> kJ
        out[key] = val
    rec["metrics"] = out
    rec["workouts"] = envelope.get("workouts") or []
    return rec


def _match_column(row: dict, needles: list[str]) -> float | None:
    for header, raw in row.items():
        if any(n in header for n in needles):
            try:
                return float(str(raw).replace(",", "").strip())
            except (TypeError, ValueError):
                return None
    return None
