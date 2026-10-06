#!/usr/bin/env python3
"""Pull WHOOP data via the v2 API and write one immutable raw envelope per calendar day.

Mirrors the voice pipeline's contract:
  * writes into 00-Raw/ only (immutable source layer) — one file per UTC-anchored day,
  * idempotent: an existing day file is never rewritten (raw is permanent),
  * the shell wrapper holds /tmp/vault-ingest.lock so the auto-commit timer won't pick up
    a half-written file; the finished JSON is committed by that timer afterwards.

Bucketing: WHOOP organises everything around *physiological cycles* (which can start the
prior evening), not calendar days. We anchor each day to the local date of its cycle's
`start`, then attach that cycle's recovery + sleep. Workouts are bucketed by their own
local start date. Only ended, SCORED cycles are written, so a day file is final when it
lands (the current in-progress cycle is skipped until it closes and is scored).

    python whoop_pull.py                 # incremental: last 3 days -> today
    python whoop_pull.py --since 2024-01-01 --until 2024-02-01   # explicit backfill window
    python whoop_pull.py --dry-run       # show what would be written, no files, no network writes
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from whoop_client import WhoopClient, WhoopAuthError

REPO = Path(__file__).resolve().parent.parent.parent
RAW_DIR = REPO / "00-Raw" / "Wearables" / "whoop"
ENVELOPE_SCHEMA = "whoop-raw/v2"


def _local_date(iso_ts: str, tz_offset: str | None) -> str:
    """Local calendar date for an ISO timestamp, applying WHOOP's timezone_offset (+hh:mm)."""
    ts = dt.datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    if tz_offset and tz_offset not in ("Z", ""):
        sign = 1 if tz_offset[0] == "+" else -1
        hh, mm = tz_offset[1:].split(":")
        ts = ts.astimezone(dt.timezone(sign * dt.timedelta(hours=int(hh), minutes=int(mm))))
    return ts.date().isoformat()


def _day_path(date: str) -> Path:
    return RAW_DIR / date[:4] / f"{date}.json"


def build_envelopes(client: WhoopClient, start: str, end: str) -> dict[str, dict]:
    """Pull all collections in [start, end) and assemble per-day raw envelopes."""
    cycle_date: dict[int, str] = {}            # cycle_id -> local day
    envelopes: dict[str, dict] = {}

    def env_for(date: str) -> dict:
        return envelopes.setdefault(date, {
            "schema": ENVELOPE_SCHEMA, "source": "whoop", "date": date,
            "pulled_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "cycle": None, "recovery": None, "sleep": [], "workouts": [],
        })

    for cycle in client.cycles(start, end):
        if not cycle.get("end") or cycle.get("score_state") != "SCORED":
            continue                            # skip in-progress / unscorable cycles
        date = _local_date(cycle["start"], cycle.get("timezone_offset"))
        cycle_date[cycle["id"]] = date
        env_for(date)["cycle"] = cycle

    for rec in client.recoveries(start, end):
        date = cycle_date.get(rec.get("cycle_id"))
        if date:
            env_for(date)["recovery"] = rec

    for sleep in client.sleeps(start, end):
        date = cycle_date.get(sleep.get("cycle_id"))
        if date is None and sleep.get("end"):   # sleep outside a pulled cycle: use wake date
            date = _local_date(sleep["end"], sleep.get("timezone_offset"))
        if date:
            env_for(date)["sleep"].append(sleep)

    for workout in client.workouts(start, end):
        if not workout.get("start"):
            continue
        date = _local_date(workout["start"], workout.get("timezone_offset"))
        env_for(date)["workouts"].append(workout)

    # Only keep days anchored on a real scored cycle (avoids stray workout-only stubs).
    return {d: e for d, e in envelopes.items() if e["cycle"] is not None}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", help="Backfill from this date (YYYY-MM-DD).")
    ap.add_argument("--until", help="Pull up to this date (YYYY-MM-DD, exclusive). Default: tomorrow.")
    ap.add_argument("--lookback", type=int, default=3,
                    help="Incremental mode: pull the last N days (default 3) to catch late scoring.")
    ap.add_argument("--dry-run", action="store_true", help="Report only; no files written.")
    ap.add_argument("--overwrite", action="store_true",
                    help="Rewrite existing day files (breaks immutability — repair use only).")
    args = ap.parse_args()

    today = dt.date.today()
    until = dt.date.fromisoformat(args.until) if args.until else today + dt.timedelta(days=1)
    since = dt.date.fromisoformat(args.since) if args.since else until - dt.timedelta(days=args.lookback)
    start_iso = dt.datetime.combine(since, dt.time.min, dt.timezone.utc).isoformat()
    end_iso = dt.datetime.combine(until, dt.time.min, dt.timezone.utc).isoformat()

    try:
        client = WhoopClient()
    except WhoopAuthError as exc:
        print(f"AUTH: {exc}", file=sys.stderr)
        return 2

    print(f"Pulling WHOOP {since} .. {until} (exclusive)…")
    envelopes = build_envelopes(client, start_iso, end_iso)

    written = skipped = 0
    for date in sorted(envelopes):
        path = _day_path(date)
        if path.exists() and not args.overwrite:
            skipped += 1
            continue
        if args.dry_run:
            env = envelopes[date]
            print(f"  would write {path.relative_to(REPO)}  "
                  f"(recovery={'y' if env['recovery'] else 'n'}, "
                  f"sleeps={len(env['sleep'])}, workouts={len(env['workouts'])})")
            written += 1
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(envelopes[date], indent=2, sort_keys=True), encoding="utf-8")
        print(f"  wrote {path.relative_to(REPO)}")
        written += 1

    print(f"\nDone. {written} day(s) {'to write' if args.dry_run else 'written'}, "
          f"{skipped} already present.")
    print(f"Raw dir: {RAW_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
