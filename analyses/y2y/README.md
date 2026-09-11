# analyses/y2y — the trail (2026-09-10)

Everything needed to reproduce the study from step one is in this folder, in numeric order. Numbers are the
identifiers used in `spec/methods_log.md`, `spec/results_log.md` and the study plan, so they are never renumbered;
letter suffixes (11b, 18b, 18c) are steps inserted later. `evidence/` holds only notebooks that a later step SUPERSEDED
(they still run, and their results stand in the logs). `archive/` holds rescinded code.

## From scratch — the record (manifest v1) then the current version (manifest v3.1)

The study was pre-registered and solved on the 40-class ecosystem block (manifest v1, `runs/`), then the block was
curated and the ensemble re-solved (manifest v3.1, `runs_v3.1/`). Both are reproducible; the E-round and E18 stand as
v1 evidence and are not re-run. Set `Y2Y_VERSION=v1` in the environment (or in `config.py`) for the v1 steps.

| step | notebook | kernel | produces |
|---|---|---|---|
| Gate 0a | 01_feature_audit | y2y-geo | the feature audit + cards → `audit/audit_objects/` (layer hashes, characterization) |
| Gate 0 | 02_solve → 03_gate0_validation → 04_results | y2y-r / y2y-geo | stopping-rule validation arms, verdict, views |
| Gate 1 | 05_s0_construction | y2y-geo | S0 and the block-budgeted scenarios (`spec/scenarios_v1.json`) |
| Gate 2 | 06_gate2_pool → 07_gate2_analysis | y2y-r / y2y-geo | the k-best pool and its NEAR-BINARY verdict (why the estimator is MGA) |
| Gate 2a/2b | 08_gate2a_pilot → 09_gate2b_mga → 10_gate2b_analysis | y2y-r / y2y-geo | S4 pilot (`spec/scenarios_v2.json`), the MGA reference run, PLATEAU-RICH |
| Gate 3 | 11_gate3_freeze | y2y-geo | the v1 pre-registration (`spec/manifest.csv` + hash) |
| Gate 4 (v1) | 12 → 13 → 15 | y2y-r / y2y-geo | anchors, members, twins; F, E1–E3, E7, E11; E13/E14/E17 → `runs/`, `spec/` |
| E-round (v1) | 16_supplementary_solves → 17_e_round_analysis | y2y-r / y2y-geo | E8–E10, E12, E15 demonstration, E17-T3 (feeds the E17 one-pager) |
| E15 completion (v1) | 18_guarded_sweep | y2y-r | guarded members on the v1 record |
| E18 (v1) | 21_e18_connectivity_weight → 22_e18_analysis | y2y-r / y2y-geo | the weight-vs-substitutability arms and dose table (`spec/E18_dose_table.csv`, deck appendix) |
| **v3.1 freeze** | **11b_efg_curation_freeze_v3** | y2y-geo | the block curation (rule R0), both curated stacks, window footprints, targets, `spec/manifest_v3.1.csv` |
| **Gate 4 (v3.1)** | **12 → 13 → 15 → 18** | y2y-r / y2y-geo | the same steps on the curated block (`runs_v3.1/`, `spec/v3.1/`) |
| **E19 (v3.1)** | **18b_e19_solves → 18c_e19_analysis** | y2y-r / y2y-geo | the necessity test: leave-EFG-out anchors, adequacy-forced set, the 50% gate |
| **Package** | **19_director_surfaces → 20_director_figures** | y2y-geo | the director package (`director_package/`) |

The v3.1 block (11b onward) is one command from the repo root: `caffeinate -i bash analyses/y2y/run_v31.sh`
(in place, resumable, logs in `logs/`; skips finished steps).

## evidence/ — superseded, kept as the record

| notebook | superseded by |
|---|---|
| 13b_denominator_v015 | the `role` column in manifest v3.1 (the v0.15 ruling applied to the v1 record; `spec/manifest_v2.csv`, the 12-vs-14 deltas) |
| 14_gate4_results | the director package (19/20) — Gate 4 decision views on v1 |
