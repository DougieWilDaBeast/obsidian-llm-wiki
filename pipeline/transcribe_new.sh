#!/usr/bin/env bash
# Ongoing voice pipeline: transcribe NEW clips that the sync transport dropped
# into the live staging dir, then move their audio into Processed/.
#
# - Only scans the live staging dir (new phone clips); the historical archive is
#   handled by the backfill script (ledger-tracked).
# - The sha256 ledger makes this idempotent: already-transcribed clips are skipped.
# - Holds $INGEST_LOCK while running so vault_autocommit.sh won't commit a
#   half-written transcript; the auto-commit timer commits the finished .md after.
# - A separate flock prevents overlapping transcribe runs (a long batch + the timer).
#
# Env:  VAULT_ROOT  path to the vault/repo   (default: $HOME/obsidian-llm-wiki)
#       AUDIO_STAGING  dir new phone clips land in (default: $HOME/VoiceRecordings/Voice Recorder)
#       WHISPER_VENV   path to the python venv activate script
set -uo pipefail

REPO="${VAULT_ROOT:-$HOME/obsidian-llm-wiki}"
STAGING="${AUDIO_STAGING:-$HOME/VoiceRecordings/Voice Recorder}"
VENV="${WHISPER_VENV:-$HOME/voice-pipeline/venv/bin/activate}"
SCRIPT="$REPO/pipeline/backfill_transcribe.py"
LOG="${TRANSCRIBE_LOG:-$HOME/.local/state/llm-wiki/transcribe.log}"
INGEST_LOCK="${INGEST_LOCK:-/tmp/vault-ingest.lock}"
RUN_LOCK="${TRANSCRIBE_RUN_LOCK:-/tmp/voice-transcribe.lock}"

mkdir -p "$(dirname "$LOG")" 2>/dev/null || true

# Single-runner guard: bail if a previous transcribe run is still going.
exec 9>"$RUN_LOCK"
flock -n 9 || exit 0

# Nothing to do if the staging dir is missing.
[ -d "$STAGING" ] || exit 0

# Pause the auto-commit timer while we write transcripts.
touch "$INGEST_LOCK"
trap 'rm -f "$INGEST_LOCK"' EXIT

{
  echo "=== $(date -Iseconds) ongoing transcribe run ==="
  # shellcheck disable=SC1090
  source "$VENV"
  python "$SCRIPT" --sources "$STAGING" --move-processed
} >> "$LOG" 2>&1
