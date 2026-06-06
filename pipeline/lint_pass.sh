#!/usr/bin/env bash
# Weekly Lint pass for the wiki (dormant by default).
#
# Runs the CLAUDE.md Lint workflow over the whole wiki (reconcile counts, surface
# stubs/orphans/contradictions, append a `lint` entry to log.md) via the same
# swappable model backend as ingest_one.sh.
#
# DORMANT BY DEFAULT: no-op unless INGEST_CMD is configured, so the disabled timer
# can never half-run a lint.
#
# Env:  VAULT_ROOT  path to the vault/repo (default: $HOME/obsidian-llm-wiki)
#       INGEST_CMD  the model backend (same var ingest_one.sh uses). UNSET => no-op.
set -uo pipefail

REPO="${VAULT_ROOT:-$HOME/obsidian-llm-wiki}"
INGEST_LOCK="${INGEST_LOCK:-/tmp/vault-ingest.lock}"
RUN_LOCK="${LINT_RUN_LOCK:-/tmp/vault-lint-run.lock}"
LOG="${LINT_LOG:-$HOME/.local/state/llm-wiki/lint.log}"

mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
log() { echo "$(date -Iseconds) $*" >> "$LOG"; }

# Single-runner guard.
exec 9>"$RUN_LOCK"
if ! flock -n 9; then
  log "SKIP (a lint is already running)"
  exit 0
fi

# Dormant unless a model backend is configured.
if [ -z "${INGEST_CMD:-}" ]; then
  log "NO-OP (INGEST_CMD unset; lint scaffold is dormant)"
  exit 0
fi

# Pause auto-commit while the lint rewrites pages.
touch "$INGEST_LOCK"
trap 'rm -f "$INGEST_LOCK"' EXIT

cd "$REPO" || { log "FAIL: cannot cd $REPO"; exit 1; }
log "LINT start"

# The backend is invoked with the literal token "LINT" instead of a raw file
# path; the model wrapper is responsible for recognising it and running the
# CLAUDE.md Lint workflow rather than a single-source ingest.
if ! "$INGEST_CMD" LINT; then
  log "FAIL: model backend errored during lint — no commit"
  exit 1
fi

git add -A
if git diff --cached --quiet; then
  log "LINT done: no changes"
  exit 0
fi
git commit -q -m "lint: weekly automated pass"
git pull --rebase -q 2>/dev/null || true
git push -q 2>/dev/null || true
log "LINT done + pushed"
