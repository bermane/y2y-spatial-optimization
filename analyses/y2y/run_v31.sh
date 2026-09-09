#!/usr/bin/env bash
# ONE COMMAND for the curated-block re-solve, its analysis and the director package (study plan v0.17.3, manifest v3.1):
#
#     caffeinate -i bash analyses/y2y/run_v31.sh          # from the repo root; ~22 h; laptop awake + online (Gurobi WLS)
#
# Each notebook is executed IN PLACE (outputs stay in the .ipynb for VS Code) with its own log in analyses/y2y/logs/.
# Every step is resumable (finished artifacts are skipped), so re-running the command after an interruption continues.
# The only branch -- the no-EFG ensemble (E19 T3) -- is decided by the gate 25 writes and handled here automatically.
set -euo pipefail
cd "$(dirname "$0")/../.."
PY=.venv/bin/python; NB=analyses/y2y; LOG=$NB/logs; mkdir -p "$LOG"
run() {   # run <notebook> <kernel>
  local nb=$1 k=$2
  echo "== $(date '+%F %T')  $nb"
  if ! $PY -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name="$k" \
        --ExecutePreprocessor.timeout=-1 "$NB/$nb.ipynb" > "$LOG/$nb.log" 2>&1; then
    echo "FAILED: $nb -- see $LOG/$nb.log (fix, then re-run this command; finished steps are skipped)"; exit 1
  fi
}
# NUMERIC ORDER: 13 and 15 need only 12's anchors and members; 18c, 19 and 20 need 18's guarded members as well.
run 12_gate4_ensemble        y2y-r     # anchors + MGA members + twins, 12 formulations (~10-12 h)
run 13_gate4_analysis        y2y-geo   # F, bands, E1, E7, E11 on v3.1 (minutes)
run 15_post_r8_diagnostics   y2y-geo   # E13 masks, E14 trigger, E17 latitude products (minutes)
run 18_guarded_sweep         y2y-r     # guarded members (~12 h)
run 18b_e19_solves            y2y-r     # leave-EFG-out anchors (~15 min); its T3 cell is a no-op until the gate exists
run 18c_e19_analysis          y2y-geo   # the necessity test; writes spec/v3.1/e19_gate.json
if $PY -c "import json,sys; sys.exit(0 if json.load(open('$NB/spec/v3.1/e19_gate.json'))['t3_triggered'] else 1)"; then
  echo "T3 gate TRIGGERED (core predominantly adequacy-forced) -> the no-EFG ensemble (~9 h + guarded), then re-analyse"
  run 18b_e19_solves          y2y-r
  run 18c_e19_analysis        y2y-geo
else
  echo "T3 gate not triggered (pre-stated expectation)"
fi
run 19_director_surfaces     y2y-geo   # tiers, clusters, tables (archives the artifact-block package first)
run 20_director_figures      y2y-geo   # figures + deck
echo "DONE $(date '+%F %T') -- analyses/y2y/director_package/ rebuilt on manifest v3.1"
