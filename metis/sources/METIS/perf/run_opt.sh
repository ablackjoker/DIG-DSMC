#!/bin/bash
# Build -> bit-identical verify gate -> bench, in one shot. Run from anywhere.
# Usage: perf/run_opt.sh <label> [reps]
# Exits non-zero (and does NOT bench) if build fails or output is not bit-identical.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT" || exit 1
LABEL=${1:?need label}; REP=${2:-5}

echo "=== [$LABEL] build ==="
if ! make >/tmp/opt_build.log 2>&1; then
  echo "BUILD FAILED"; grep -iE "error" /tmp/opt_build.log | head; exit 1
fi
echo "build ok"

echo "=== [$LABEL] verify (bit-identical gate) ==="
if ! perf/harness.sh verify perf/ref; then
  echo ">>> VERIFY FAILED — output not bit-identical; NOT benching <<<"; exit 2
fi

echo "=== [$LABEL] bench (min of $REP) ==="
perf/harness.sh bench "$LABEL" "$REP"
echo "=== [$LABEL] done ==="
