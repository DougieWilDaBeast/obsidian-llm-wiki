#!/usr/bin/env bash
# Server-side auto-commit for the wiki.
# A sync transport (e.g. SyncThing) drops phone/device edits into the working
# tree; this commits them and syncs with the git remote. The server is the ONLY
# git brain — the phone never runs git.
# Order: commit local changes -> rebase onto remote -> push.
#
# Env:  VAULT_ROOT  path to the vault/repo (default: $HOME/obsidian-llm-wiki)
set -uo pipefail

REPO="${VAULT_ROOT:-$HOME/obsidian-llm-wiki}"
INGEST_LOCK="${INGEST_LOCK:-/tmp/vault-ingest.lock}"

cd "$REPO" || exit 0

# Refuse to run while an ingest holds the lock (avoids committing half-written pages).
[ -e "$INGEST_LOCK" ] && exit 0

git add -A
if ! git diff --cached --quiet; then
  git commit -q -m "sync: device edits $(date -Iseconds)"
fi
git pull --rebase -q 2>/dev/null || true
git push -q 2>/dev/null || true
