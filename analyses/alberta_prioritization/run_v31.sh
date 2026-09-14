#!/usr/bin/env bash
# ONE COMMAND for the Alberta mirror's curated-block re-solve, its analysis and the director package (AB spec v0.5; manifest v3.1):
#
#     caffeinate -i bash analyses/alberta_prioritization/run_v31.sh      # from the repo root; ~3-4 h; laptop awake + online (Gurobi WLS)
#
# Mirrors analyses/y2y/run_v31.sh. Each notebook is executed IN PLACE (outputs stay in the .ipynb for VS Code) with its own log in
# analyses/alberta_prioritization/logs/. Every step is resumable (finished artifacts are skipped). The only branch -- the no-EFG
# ensemble (E19 T3) -- is decided by the gate 11c writes and handled here automatically. Commit config.py + the pipeline modules
# before running: 09b refuses to freeze against a dirty module (M8.2).
set -euo pipefail
cd "$(dirname "$0")/../.."
PY=.venv/bin/python; NB=analyses/alberta_prioritization; LOG=$NB/logs; mkdir -p "$LOG"
run() {   # run <notebook> <kernel>
  local nb=$1 k=$2
  echo "== $(date '+%F %T')  $nb"
  if ! $PY -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name="$k" \
        --ExecutePreprocessor.timeout=-1 "$NB/$nb.ipynb" > "$LOG/$nb.log" 2>&1; then
    echo "FAILED: $nb -- see $LOG/$nb.log (fix, then re-run this command; finished steps are skipped)"; exit 1
  fi
}
run 09b_ab_curation_freeze_v3   y2y-geo   # inherited curation on the AB extent, block card, window targets, manifest v3.1 (minutes)
run 10_ab4_ensemble             y2y-r     # anchors + twins + MGA at both bands, 12 formulations, no k-best (~2-3 h)
run 11_ab4_analysis             y2y-geo   # estimand + applied band (rule D-AB13), C1-C4, clusters (minutes)
run 11b_ab_e19_solves           y2y-r     # leave-EFG-out anchors (~1 min); its T3 cell is a no-op until the gate exists
run 11c_ab_e19_analysis         y2y-geo   # the necessity test; writes spec/v3.1/e19_gate.json
if $PY -c "import json,sys; sys.exit(0 if json.load(open('$NB/spec/v3.1/e19_gate.json'))['t3_triggered'] else 1)"; then
  echo "T3 gate TRIGGERED (core predominantly adequacy-forced) -> the no-EFG ensemble (~1 h at Alberta scale), then re-analyse"
  run 11b_ab_e19_solves         y2y-r
  run 11c_ab_e19_analysis       y2y-geo
else
  echo "T3 gate not triggered (pre-stated expectation)"
fi
run 12_director_surfaces        y2y-geo   # tiers, clusters, tables (archives the v1 artifact-block package first)
run 13_director_figures         y2y-geo   # figures + deck
echo "DONE $(date '+%F %T') -- analyses/alberta_prioritization/director_package/ rebuilt on manifest v3.1"
