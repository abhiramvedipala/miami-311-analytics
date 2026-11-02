#!/usr/bin/env bash
# The project's definition of working. Prints PASS or the first failing check.
# The pipeline runs on the offline sample, so this needs no network beyond package install.
set -u
cd "$(dirname "$0")/.."

WORK=$(mktemp -d)
PORT=8599
APP_PID=""
cleanup() {
  [ -n "$APP_PID" ] && kill "$APP_PID" 2>/dev/null
  rm -rf "$WORK"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $1"
  [ -f "$WORK/log" ] && tail -30 "$WORK/log"
  exit 1
}

echo "1/6 install from clean state"
rm -rf .venv
make setup >"$WORK/log" 2>&1 || fail "make setup"

echo "2/6 tests"
.venv/bin/python -m pytest -q >"$WORK/log" 2>&1 || fail "pytest"

echo "3/6 pipeline on sample data"
DUCKDB_PATH="$WORK/check.duckdb" RESULTS_PATH="$WORK/RESULTS.md" make sample >"$WORK/log" 2>&1 || fail "make sample"

echo "4/6 dashboard answers, then stops"
DUCKDB_PATH="$WORK/check.duckdb" .venv/bin/streamlit run dashboard/app.py \
  --server.port "$PORT" --server.headless true >"$WORK/log" 2>&1 &
APP_PID=$!
healthy=""
for _ in $(seq 1 30); do
  if curl -fs "http://localhost:$PORT/_stcore/health" >/dev/null 2>&1; then healthy=yes; break; fi
  sleep 1
done
[ -n "$healthy" ] || fail "dashboard health endpoint"
kill "$APP_PID"
wait "$APP_PID" 2>/dev/null
APP_PID=""
if curl -fs "http://localhost:$PORT/_stcore/health" >/dev/null 2>&1; then fail "dashboard still running"; fi

echo "5/6 RESULTS.md was written by scripts"
.venv/bin/python src/results.py RESULTS.md >"$WORK/log" 2>&1 || fail "RESULTS.md verification"

echo "6/6 git clean and pushed"
[ -z "$(git status --porcelain)" ] || { git status --short; fail "uncommitted changes"; }
git fetch -q origin main || fail "git fetch"
[ -z "$(git log origin/main..main --oneline)" ] || fail "unpushed commits"

echo PASS
