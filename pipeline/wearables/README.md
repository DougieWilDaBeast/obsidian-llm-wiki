# Wearables intake pipeline (WHOOP first)

Brings biometric/wearable data into the wiki as a first-class raw source,
mirroring the voice pipeline's contract (immutable raws, server-side timer, lock-coordinated
auto-commit). Designed **device-agnostically**: WHOOP is the first _adapter_ onto a generic
`daily-metrics/v1` format, so a future smartwatch (Suunto/Garmin/Oura/…) drops in as a new
adapter with **no change** to storage, aggregation, or the Refined side.

## Data flow

```
provider                 raw (immutable)                     transform (derived)        Refined (wiki)
────────                 ───────────────                     ───────────────────        ──────────────
WHOOP v2 API ─ whoop_pull.py ─┐
                              ├─► 00-Raw/Wearables/whoop/      aggregate_weekly.py        agent ingest:
manual export ─ whoop_import_ ┘     YYYY/YYYY-MM-DD.json  ──►  + <source>_adapter   ──►   [[Whoop]] entity +
                 export.py        (whoop-raw/v2 |              normalize() ─► weekly      `Whoop — YYYY-Www
                                   whoop-export/v1)            sidecar (~/whoop-           digest` (prose trends)
                                                               pipeline/weekly/*.json)
```

- **Raw layer is immutable** — one JSON per calendar day, written once, never edited (matches
  "one transcript per note"). Highest fidelity: provider-native records, no interpretation.
- **Transform is derived/cheap** — deterministic weekly stats; lives outside the repo like the
  voice ledger. Free to recompute; the agent reads it instead of hundreds of raw days.
- **Refined output is unchanged** from CLAUDE.md §8b: one `[[Whoop]]` entity page + periodic
  `Whoop — YYYY-Www digest` prose roll-ups of _trends_ (recovery/sleep/strain), never a page
  per day.

## The generic contract — `daily-metrics/v1`

Defined in [`daily_metrics.py`](daily_metrics.py). Every adapter emits the same normalized
record (a flat `metrics` dict over the canonical registry + a `workouts` list). Adding a
metric or a device is a one-line registry/adapter change; aggregation flows automatically.

## Files

| File                                 | Role                                                                |
| ------------------------------------ | ------------------------------------------------------------------- |
| `daily_metrics.py`                   | **Generic** schema, canonical metric registry, weekly aggregation.  |
| `whoop_adapter.py`                   | WHOOP: raw envelope (API or export) → `daily-metrics/v1`.           |
| `whoop_client.py`                    | WHOOP v2 API client (OAuth refresh, pagination) — stdlib only.      |
| `whoop_pull.py`                      | Ongoing API pull → immutable per-day raw envelopes.                 |
| `whoop_import_export.py`             | History backfill from the manual "Download my data" bundle.         |
| `whoop_oauth_bootstrap.py`           | One-time: mint the first refresh token (run with a browser).        |
| `aggregate_weekly.py`                | Transform: raw days → weekly stat sidecars (per ISO week).          |
| `whoop_pull.sh`                      | Server wrapper: flock + `/tmp/vault-ingest.lock`.                   |
| `systemd/whoop-pull.{service,timer}` | Daily server schedule (09:00 local).                                |
| `whoop.env.example`                  | Secret template → copy to `~/whoop-pipeline/whoop.env` (chmod 600). |

`~/whoop-pipeline/` is the default state dir (secrets, token, weekly sidecars, log); set
`WEARABLES_STATE_DIR` to put it elsewhere. It always lives **outside** the repo.

No third-party Python deps — everything runs on system `python3` (stdlib `urllib`).

## One-time setup

1. **WHOOP Developer Dashboard** (https://developer.whoop.com) → create an App → copy the
   **Client ID** + **Client Secret**.
2. Register a **Redirect URL** of `http://localhost` and enable the **`offline`** scope
   (required for a refresh token) alongside the six `read:*` scopes.
3. Mint the first refresh token (on a machine with a browser, e.g. your laptop):
   ```bash
   export WHOOP_CLIENT_ID="…" WHOOP_CLIENT_SECRET="…"
   python pipeline/wearables/whoop_oauth_bootstrap.py
   ```
   This writes `~/whoop-pipeline/state.json` (chmod 600) with the rotating refresh token.
   Then copy that `state.json` (and `whoop.env`) to the **server** at `~/whoop-pipeline/`.
4. **History backfill** — in the WHOOP app/web, _Download my data_, then:
   ```bash
   python pipeline/wearables/whoop_import_export.py --bundle <export.zip|dir> --dry-run
   python pipeline/wearables/whoop_import_export.py --bundle <export.zip|dir>
   ```
5. **Enable the ongoing pull on the server** — see the install header in
   [`systemd/whoop-pull.service`](systemd/whoop-pull.service).

## Verify

```bash
python pipeline/wearables/whoop_pull.py --dry-run            # network read, no files
python pipeline/wearables/whoop_pull.py --since 2026-01-05 --until 2026-01-08
python pipeline/wearables/aggregate_weekly.py --week 2026-W02 --stdout
python pipeline/wearables/whoop_pull.py --since 2026-01-05 --until 2026-01-08  # 0 new (idempotent)
```

## Security

- Client secret + refresh token **never** in git — they live in `~/whoop-pipeline/`
  (outside the repo) and are also belt-and-braces ignored in `.gitignore`. State file is 0600.
- The refresh token **rotates** on every refresh; the client persists the new one immediately
  (WHOOP invalidates the previous token on use).
- Raw day files are immutable; the pull only writes ended, **SCORED** cycles, so a day file is
  final when it lands. `--overwrite` exists only for repair and warns it breaks immutability.
- Health data stays on your own machines; no third-party services beyond the provider's API.
- Use a **private** remote for a real vault: day files are personal health data.
