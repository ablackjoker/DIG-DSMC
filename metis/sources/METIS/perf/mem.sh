#!/bin/bash
# Peak-memory A/B: baseline binary (/tmp/baseline_bin) vs current (./build/programs).
# Reports METIS gk-tracked heap high-water ("Max memory used", dbglvl=0) for each,
# plus OS max RSS via /usr/bin/time -l as a ground-truth cross-check.
# Usage: perf/mem.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT" || exit 1
BASE=/tmp/baseline_bin; CUR=./build/programs; SEED=12345

CONFIGS=(
  "kway_cit_10|gpmetis|graphs/cit-Patents.metis|10|"
  "kway_cit_100|gpmetis|graphs/cit-Patents.metis|100|"
  "kway_mdual_10|gpmetis|graphs/mdual.graph|10|"
  "kway_mdual_100|gpmetis|graphs/mdual.graph|100|"
  "rb_mdual_100|gpmetis|graphs/mdual.graph|100|-ptype=rb"
  "nd_mdual|ndmetis|graphs/mdual.graph||"
)
metismem() { awk '/Max memory used/{print $4; exit}'; }   # MB, gk-tracked
rss() { /usr/bin/time -l "$@" 2>&1 | awk '/maximum resident set size/{printf "%.1f", $1/(1024*1024); exit}'; } # MB

run() { local d=$1 tool=$2 g=$3 np=$4 ex=$5
  if [ "$tool" = ndmetis ]; then "$d/ndmetis" -dbglvl=0 -seed=$SEED $ex "$g" 2>/tmp/m.out | metismem
  else "$d/gpmetis" -dbglvl=0 -seed=$SEED $ex "$g" "$np" 2>/tmp/m.out | metismem; fi; }
runrss() { local d=$1 tool=$2 g=$3 np=$4 ex=$5
  if [ "$tool" = ndmetis ]; then rss "$d/ndmetis" -seed=$SEED $ex "$g"
  else rss "$d/gpmetis" -seed=$SEED $ex "$g" "$np"; fi; }

printf "%-16s %12s %12s %8s | %10s %10s\n" config base_heapMB cur_heapMB delta% base_rssMB cur_rssMB
for c in "${CONFIGS[@]}"; do
  IFS='|' read -r label tool graph nparts extra <<<"$c"
  bh=$(run "$BASE" "$tool" "$graph" "$nparts" "$extra")
  ch=$(run "$CUR"  "$tool" "$graph" "$nparts" "$extra")
  br=$(runrss "$BASE" "$tool" "$graph" "$nparts" "$extra")
  cr=$(runrss "$CUR"  "$tool" "$graph" "$nparts" "$extra")
  d=$(awk -v b="$bh" -v c="$ch" 'BEGIN{if(b>0)printf "%+.1f",100*(c-b)/b; else print "na"}')
  printf "%-16s %12s %12s %8s | %10s %10s\n" "$label" "$bh" "$ch" "$d" "$br" "$cr"
done
