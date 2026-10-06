#!/usr/bin/env python3
"""Transform layer: roll raw wearable day files into deterministic weekly stat sidecars.

Reads the immutable per-day raw envelopes under 00-Raw/Wearables/<device>/, normalizes each
through its source adapter into the generic `daily-metrics/v1` shape, then emits one
`weekly-metrics/v1` JSON per ISO week. The sidecar is cheap, exact, and lives OUTSIDE the
repo (derived state, like the voice ledger) — the agent reads it to author the prose
`Whoop — YYYY-Www digest` page during a normal (paid) ingest pass, instead of re-reading
hundreds of raw days.

    python aggregate_weekly.py                 # all weeks that have raw data
    python aggregate_weekly.py --week 2026-W25 # one ISO week
    python aggregate_weekly.py --stdout --week 2026-W25   # print, don't write

Adding a new device = registering its adapter in ADAPTERS; no other change here.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import daily_metrics
import whoop_adapter

REPO = Path(__file__).resolve().parent.parent.parent
RAW_ROOT = REPO / "00-Raw" / "Wearables"
# Derived state lives OUTSIDE the repo; override the base dir with $WEARABLES_STATE_DIR.
OUT_DIR = Path(os.environ.get("WEARABLES_STATE_DIR", Path.home() / "whoop-pipeline")) / "weekly"

# source name -> normalize(envelope) -> daily-metrics/v1
ADAPTERS = {whoop_adapter.SOURCE: whoop_adapter.normalize}


def _load_days() -> dict[str, dict]:
    """Return {date: normalized_record} for every raw day file across all devices."""
    days: dict[str, dict] = {}
    for path in sorted(RAW_ROOT.rglob("*.json")):
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  WARN skip {path.name}: {exc}", file=sys.stderr)
            continue
        normalize = ADAPTERS.get(envelope.get("source"))
        if not normalize:
            print(f"  WARN no adapter for source={envelope.get('source')} ({path.name})", file=sys.stderr)
            continue
        record = normalize(envelope)
        days[record["date"]] = record
    return days


def _group_by_week(days: dict[str, dict]) -> dict[str, list[dict]]:
    weeks: dict[str, list[dict]] = {}
    for date, record in days.items():
        week_id, _, _ = daily_metrics.iso_week_bounds(dt.date.fromisoformat(date))
        weeks.setdefault(week_id, []).append(record)
    return weeks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--week", help="Only this ISO week (e.g. 2026-W25).")
    ap.add_argument("--stdout", action="store_true", help="Print the aggregate(s) instead of writing files.")
    args = ap.parse_args()

    weeks = _group_by_week(_load_days())
    if args.week:
        weeks = {args.week: weeks.get(args.week, [])}
        if not weeks[args.week]:
            print(f"No raw days found for {args.week}.", file=sys.stderr)
            return 1

    if not args.stdout:
        OUT_DIR.mkdir(parents=True, exist_ok=True)

    for week_id in sorted(weeks):
        agg = daily_metrics.weekly_aggregate(weeks[week_id])
        if args.stdout:
            print(json.dumps(agg, indent=2))
            continue
        out = OUT_DIR / f"{week_id}.json"
        out.write_text(json.dumps(agg, indent=2, sort_keys=True), encoding="utf-8")
        print(f"  wrote {out}  ({agg['days_present']} day(s), {len(agg['metrics'])} metrics)")

    if not args.stdout:
        print(f"\nDone. {len(weeks)} week(s) -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
