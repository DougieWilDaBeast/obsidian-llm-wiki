#!/usr/bin/env bash
# Non-destructive self-test for ingest_one.sh (the ingest scaffold).
#
# Verifies the safety behaviour WITHOUT writing any real Refined pages or commits:
#   T1  missing arg            -> exit 2
#   T2  path outside 00-Raw    -> exit 2
#   T3  non-existent 00-Raw    -> exit 2
#   T4  dormant (no INGEST_CMD)-> NO-OP, exit 0, no lock left behind
#   T5  stub model (INGEST_CMD=true) on a real raw, ONLY if the tree is clean
#       -> "no changes" path, exit 0, no commit
#
# Safe to run anytime before activation:
#   VAULT_ROOT=/path/to/obsidian-llm-wiki ./pipeline/selftest_ingest.sh
#
# Env:  VAULT_ROOT  path to the vault/repo (default: $HOME/obsidian-llm-wiki)
set -uo pipefail

REPO="${VAULT_ROOT:-$HOME/obsidian-llm-wiki}"
INGEST_LOCK="${INGEST_LOCK:-/tmp/vault-ingest.lock}"
cd "$REPO" || { echo "cannot cd $REPO" >&2; exit 1; }
ING=./pipeline/ingest_one.sh
pass=0; fail=0
check() { # check <label> <expected-exit> <actual-exit>
  if [ "$2" = "$3" ]; then echo "  PASS  $1 (exit $3)"; pass=$((pass+1));
  else echo "  FAIL  $1 (expected $2, got $3)"; fail=$((fail+1)); fi
}

echo "== ingest_one.sh self-test =="
echo "-- shebang / mode --"
head -1 "$ING" | cat -A
ls -la "$ING"

echo "-- T1 missing arg --"
"$ING" >/dev/null 2>&1; check "missing arg -> 2" 2 $?

echo "-- T2 outside 00-Raw --"
"$ING" /tmp/nope.md >/dev/null 2>&1; check "outside 00-Raw -> 2" 2 $?

echo "-- T3 non-existent under 00-Raw --"
"$ING" "$REPO/00-Raw/Voice/__does_not_exist__.md" >/dev/null 2>&1
check "missing file -> 2" 2 $?

RAW="$(ls -1 00-Raw/Voice/*.md 2>/dev/null | head -1)"
if [ -z "$RAW" ]; then echo "  (no raw voice file found; skipping T4/T5)"; else
  echo "-- T4 dormant no-op on: $RAW --"
  unset INGEST_CMD
  "$ING" "$RAW" >/dev/null 2>&1; check "dormant no-op -> 0" 0 $?
  [ -e "$INGEST_LOCK" ] && { echo "  FAIL  lock left behind after T4"; fail=$((fail+1)); } || { echo "  PASS  no lock after T4"; pass=$((pass+1)); }

  if [ -n "$(git status --porcelain)" ]; then
    echo "-- T5 SKIPPED (working tree not clean; refusing stub run) --"
  else
    echo "-- T5 stub model (INGEST_CMD=true), clean tree --"
    before="$(git rev-parse HEAD)"
    INGEST_CMD=true "$ING" "$RAW" >/dev/null 2>&1; rc=$?
    after="$(git rev-parse HEAD)"
    check "stub no-change -> 0" 0 $rc
    [ "$before" = "$after" ] && { echo "  PASS  no commit created by T5"; pass=$((pass+1)); } || { echo "  FAIL  T5 created a commit ($before -> $after)"; fail=$((fail+1)); }
    [ -e "$INGEST_LOCK" ] && { echo "  FAIL  lock left behind after T5"; fail=$((fail+1)); } || { echo "  PASS  no lock after T5"; pass=$((pass+1)); }
  fi
fi

echo "-- final tree state --"
git status --short || true
echo "== result: $pass passed, $fail failed =="
[ "$fail" -eq 0 ]
