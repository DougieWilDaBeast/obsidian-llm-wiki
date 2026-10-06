#!/usr/bin/env bash
# Ongoing WHOOP pull — server wrapper, modelled on transcribe_new.sh.
#
# - Holds $INGEST_LOCK while writing raws so vault_autocommit.sh won't commit a
#   half-written day file; the finished JSON is committed by the auto-commit timer after.
# - A separate flock prevents overlapping pull runs.
# - Writes ONLY into 00-Raw/Wearables/whoop/ (immutable source layer). No git here — the
#   server's auto-commit timer is the sole git writer.
#
# Secrets: WHOOP_CLIENT_ID / WHOOP_CLIENT_SECRET come from the systemd EnvironmentFile
# ($WEARABLES_STATE_DIR/whoop.env, chmod 600) — never from the repo.
#
# Env:  VAULT_ROOT           path to the vault/repo (default: $HOME/obsidian-llm-wiki)
#       WEARABLES_STATE_DIR  secrets + derived state, outside the repo (default: $HOME/whoop-pipeline)
set -uo pipefail

REPO="${VAULT_ROOT:-$HOME/obsidian-llm-wiki}"
STATE_DIR="${WEARABLES_STATE_DIR:-$HOME/whoop-pipeline}"
SCRIPT="$REPO/pipeline/wearables/whoop_pull.py"
LOG="$STATE_DIR/pull.log"
INGEST_LOCK="${INGEST_LOCK:-/tmp/vault-ingest.lock}"
RUN_LOCK="${WHOOP_RUN_LOCK:-/tmp/whoop-pull.lock}"

mkdir -p "$STATE_DIR"

# Single-runner guard: bail if a previous pull is still going.
exec 9>"$RUN_LOCK"
flock -n 9 || exit 0

# Pause the auto-commit timer while we write raw day files.
touch "$INGEST_LOCK"
trap 'rm -f "$INGEST_LOCK"' EXIT

{
  echo "=== $(date -Iseconds) whoop pull run ==="
  python3 "$SCRIPT" "$@"
} >> "$LOG" 2>&1
