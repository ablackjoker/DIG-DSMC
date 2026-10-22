#!/bin/bash
# METIS bit-identical optimization harness.
# Modes:
#   harness.sh ref   <refdir>            capture reference outputs into refdir
#   harness.sh verify <refdir>           run each config once, cmp output vs refdir (bit-identical gate)
#   harness.sh bench  <label> <repeats>  serial timing, min-of-N, append to perf/RESULTS.tsv
#
# Run from repo root. Single-threaded build assumed (openmp off -> deterministic).

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
GP=./build/programs/gpmetis
ND=./build/programs/ndmetis
SEED=12345
TMPOUT=/tmp/metis_run.out

# label | tool | graph | nparts | extra
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

run_one() { # tool graph nparts extra -> sets OUTFILE, writes stdout to TMPOUT
  local tool=$1 graph=$2 nparts=$3 extra=$4
  if [ "$tool" = "ndmetis" ]; then
    $ND -dbglvl=2 -seed=$SEED $extra "$graph" >"$TMPOUT" 2>&1
    OUTFILE="$graph.iperm"
  else
    $GP -dbglvl=2 -seed=$SEED $extra "$graph" "$nparts" >"$TMPOUT" 2>&1
    OUTFILE="$graph.part.$nparts"
  fi
}

metric() { awk -v p="$1" '$0 ~ p {print $NF; exit}' "$TMPOUT"; }
metis_time() { awk '/\(METIS time\)/{print $2; exit}' "$TMPOUT"; }
edgecut() { awk '/Edgecut:/{gsub(",","",$3); print $3; exit}' "$TMPOUT"; }
opcount() { awk '/Operation Count:/{print $NF; exit}' "$TMPOUT"; }

MODE=${1:-}
case "$MODE" in
  ref|verify)
    DIR=${2:?need refdir}; mkdir -p "$DIR"
    pass=0; fail=0
    for c in "${CONFIGS[@]}"; do
      IFS='|' read -r label tool graph nparts extra <<<"$c"
      run_one "$tool" "$graph" "$nparts" "$extra"
      if [ ! -f "$OUTFILE" ]; then echo "MISSING OUTPUT: $label ($OUTFILE)"; fail=$((fail+1)); continue; fi
      if [ "$MODE" = "ref" ]; then
        cp "$OUTFILE" "$DIR/$label"
        echo "ref  $label -> $DIR/$label  ($(metis_time)s, cut=$(edgecut)$(opcount))"
      else
        if cmp -s "$OUTFILE" "$DIR/$label"; then echo "PASS $label"; pass=$((pass+1));
        else echo "FAIL $label  (output differs from reference)"; fail=$((fail+1)); fi
      fi
    done
    echo "----"; echo "pass=$pass fail=$fail"
    [ "$fail" -eq 0 ]
    ;;
  bench)
    LABEL=${2:?need label}; REP=${3:-3}
    OUT=perf/RESULTS.tsv
    [ -f "$OUT" ] || echo -e "variant\tconfig\tmetis_t\tmultilevel\tcoarsen\tmatch\tcontract\tinitpart\trefine\tproject\tcut" >"$OUT"
    echo "== bench '$LABEL' (min of $REP) =="
    printf "%-16s %8s %8s %8s %8s %8s %8s\n" config metis coarsen contract initpart refine
    for c in "${CONFIGS[@]}"; do
      IFS='|' read -r label tool graph nparts extra <<<"$c"
      runs=/tmp/metis_runs.txt; : >"$runs"
      for r in $(seq 1 "$REP"); do
        run_one "$tool" "$graph" "$nparts" "$extra"
        echo "$(metis_time) $(metric 'Multilevel:') $(metric 'Coarsening:') $(metric 'Matching:') $(metric 'Contract:') $(metric 'Initial Partition:') $(metric 'Refinement:') $(metric 'Projection:') $(edgecut)$(opcount)" >>"$runs"
      done
      best=$(sort -g "$runs" | head -1)
      read -r mt ml co ma ct ip rf pj cut <<<"$best"
      printf "%-16s %8s %8s %8s %8s %8s\n" "$label" "$mt" "$co" "$ct" "$ip" "$rf"
      echo -e "$LABEL\t$label\t$mt\t$ml\t$co\t$ma\t$ct\t$ip\t$rf\t$pj\t$cut" >>"$OUT"
    done
    ;;
  *) echo "usage: harness.sh {ref|verify <dir>|bench <label> [reps]}"; exit 2;;
esac
