#!/bin/bash
# Interleaved A/B: baseline binary (/tmp/baseline_bin) vs current (./build/programs).
# Alternates the two per repeat so machine-state drift hits both equally.
# Reports min-of-N METIS time per config and the delta. Usage: perf/compare.sh [reps]
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT" || exit 1
BASE=/tmp/baseline_bin
CUR=./build/programs
REP=${1:-7}
SEED=12345

CONFIGS=(
  "kway_cit_10|gpmetis|graphs/cit-Patents.metis|10|"
  "kway_cit_50|gpmetis|graphs/cit-Patents.metis|50|"
  "kway_cit_100|gpmetis|graphs/cit-Patents.metis|100|"
  "kway_mdual_10|gpmetis|graphs/mdual.graph|10|"
  "kway_mdual_50|gpmetis|graphs/mdual.graph|50|"
  "kway_mdual_100|gpmetis|graphs/mdual.graph|100|"
  "rb_mdual_10|gpmetis|graphs/mdual.graph|10|-ptype=rb"
  "rb_mdual_50|gpmetis|graphs/mdual.graph|50|-ptype=rb"
  "rb_mdual_100|gpmetis|graphs/mdual.graph|100|-ptype=rb"
  "nd_mdual|ndmetis|graphs/mdual.graph||"
  "nd_mdual_cc|ndmetis|graphs/mdual.graph||-ccorder"
)

run() { # bindir tool graph nparts extra -> echo metis time
  local d=$1 tool=$2 g=$3 np=$4 ex=$5
  if [ "$tool" = "ndmetis" ]; then "$d/ndmetis" -seed=$SEED $ex "$g" >/tmp/cmp.out 2>&1
  else "$d/gpmetis" -seed=$SEED $ex "$g" "$np" >/tmp/cmp.out 2>&1; fi
  awk '/\(METIS time\)/{print $2; exit}' /tmp/cmp.out
}
mn() { sort -g | head -1; }

printf "%-16s %9s %9s %7s\n" config baseline current "delta%"
for c in "${CONFIGS[@]}"; do
  IFS='|' read -r label tool graph nparts extra <<<"$c"
  bf=/tmp/cmp_b.txt; cf=/tmp/cmp_c.txt; : >"$bf"; : >"$cf"
  for r in $(seq 1 "$REP"); do
    run "$BASE" "$tool" "$graph" "$nparts" "$extra" >>"$bf"
    run "$CUR"  "$tool" "$graph" "$nparts" "$extra" >>"$cf"
  done
  b=$(mn <"$bf"); c2=$(mn <"$cf")
  d=$(awk -v b="$b" -v c="$c2" 'BEGIN{ if(b>0) printf "%+.1f", 100*(c-b)/b; else print "na"}')
  printf "%-16s %9s %9s %7s\n" "$label" "$b" "$c2" "$d"
done
