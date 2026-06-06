#!/usr/bin/env bash
# Headless single-source ingest for the wiki (the ingest core).
#
# Takes ONE new raw file (a voice transcript or a web clipping) and runs the
# CLAUDE.md Ingest workflow on it via a swappable model backend, producing the
# Refined page(s) + index/log updates, committed as a single source-per-commit.
#
# DORMANT BY DEFAULT: the model backend ($INGEST_CMD) is unset out of the box, so
# this script is a safe no-op until a model is wired in. An accidental trigger
# therefore CANNOT half-ingest or write partial pages.
#
# Locking mirrors the rest of the pipeline:
#   - $INGEST_LOCK    : a presence lock (touch) that pauses vault_autocommit.sh so
#                       it never commits half-written pages. Held for the whole
#                       ingest and removed on exit.
#   - $RUN_LOCK       : an flock single-runner guard so two ingests (or a trigger
#                       firing twice) never overlap.
#
# Usage:  ingest_one.sh <path-to-raw-file>
# Env:    VAULT_ROOT  path to the vault/repo   (default: $HOME/obsidian-llm-wiki)
#         INGEST_CMD  command run as: "$INGEST_CMD" "<abs raw path>"
#                     (e.g. a wrapper around `claude -p`, an OpenAI/DeepSeek call,
#                     or `copilot`). UNSET => no-op (dormant).
set -uo pipefail

REPO="${VAULT_ROOT:-$HOME/obsidian-llm-wiki}"
INGEST_LOCK="${INGEST_LOCK:-/tmp/vault-ingest.lock}"
RUN_LOCK="${RUN_LOCK:-/tmp/vault-ingest-run.lock}"
LOG="${INGEST_LOG:-$HOME/.local/state/llm-wiki/ingest.log}"

mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
log() { echo "$(date -Iseconds) $*" >> "$LOG"; }

# --- args -------------------------------------------------------------------
RAW="${1:-}"
if [ -z "$RAW" ]; then
  echo "usage: ingest_one.sh <path-to-raw-file>" >&2
  exit 2
fi
# Resolve to an absolute path and sanity-check it lives under 00-Raw.
RAW="$(readlink -f -- "$RAW" 2>/dev/null || echo "$RAW")"
case "$RAW" in
  "$REPO"/00-Raw/*) : ;;
  *) echo "refusing: '$RAW' is not under $REPO/00-Raw" >&2; exit 2 ;;
esac
if [ ! -f "$RAW" ]; then
  echo "refusing: '$RAW' does not exist" >&2; exit 2
fi

# --- single-runner guard ----------------------------------------------------
exec 9>"$RUN_LOCK"
if ! flock -n 9; then
  log "SKIP (another ingest is running): $RAW"
  exit 0
fi

# --- dormant unless a model backend is configured ---------------------------
if [ -z "${INGEST_CMD:-}" ]; then
  log "NO-OP (INGEST_CMD unset; scaffold is dormant): $RAW"
  echo "INGEST_CMD is unset — ingest scaffold is dormant, nothing ingested." >&2
  exit 0
fi

# --- pause the auto-commit timer while we write pages -----------------------
touch "$INGEST_LOCK"
trap 'rm -f "$INGEST_LOCK"' EXIT

cd "$REPO" || { log "FAIL: cannot cd $REPO"; exit 1; }

name="$(basename -- "$RAW")"
log "INGEST start: $name (model: ${INGEST_CMD%% *})"

# Run the model on the raw file. The backend is responsible for following the
# CLAUDE.md Ingest workflow and writing into 10-Refined/ + index.md + log.md.
if ! "$INGEST_CMD" "$RAW"; then
  log "FAIL: model backend errored on $name — leaving tree for inspection, no commit"
  exit 1
fi

# --- one source per commit --------------------------------------------------
git add -A
if git diff --cached --quiet; then
  log "WARN: model produced no changes for $name — nothing to commit"
  exit 0
fi
git commit -q -m "ingest: $name"
git pull --rebase -q 2>/dev/null || true
git push -q 2>/dev/null || true
log "INGEST done + pushed: $name"
