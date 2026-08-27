# Results log — Y2Y frequency-ensemble flagship (living document)

**Purpose.** The running register of quantitative RESULTS destined for the paper's results
section (and its figures/tables), each with provenance (which run/notebook produced it) so
every number in a draft can be traced to disk. Companion to `methods_log.md` (same maintenance
rule: update in the same session any result lands or changes; supersede, never delete).

Provenance shorthand: [T2] = frozen audit `audit/audit_objects/feature_characterization.csv`;
[iter8/<arm>] = `output_data/iter8_y2y_<arm>/`; [iter7/<arm>] = LP twins; [02s] = 02_solve logs.

---

## R1. Feature characterization (Gate 0a) — final stack, frozen 2026-08-26

**R1.1 Classification table [T2]:**

| feature | leverage | cap30 range | class → lever | target |
|---|---|---|---|---|
| carbon m_soc | 0.884 | 0.005–0.889 | concentrated-satiating → target | **0.332** |
| carbon biomass | 0.801 | 0.001–0.803 | diffuse-linear (reverted by t_min) → weight | 1.0 |
| connectivity | 0.461 | 0.091–0.552 | diffuse-linear → weight | 1.0 |
| macrorefugia (1/v) | 0.422 | 0.253→0.135–0.558 | diffuse-linear → weight | 1.0 |
| corridors | 0.263 | 0.156–0.419 | diffuse-linear → weight | 1.0 |
| AOH birds | 0.232 | 0.181–0.413 | diffuse-linear → weight | 1.0 |
| AOH mammals | 0.181 | 0.209–0.390 | diffuse-linear → weight | 1.0 |
| gHM intactness | 0.042 | 0.272–0.314 | inexpressible (disclosed) | — |
| EFG block (40) | 36 @ ~1.0 | — | rare-attainable ×36; 4 unsaturated disclosed | 1.0 |

**R1.2 Influence under equal weights (t=1):** carbon pools 39.7% of achievable objective swing;
under w=t + protocol target: connectivity 23.1 / macrorefugia 21.2 / m_soc 16.4 / corridors
13.2 / birds 11.6 / mammals 9.1 / biomass 3.2 / intactness 2.1 (%).

**R1.3 Transform screening (universal):** log1p(m_soc) 0.884→0.486 AND class flips to
diffuse-linear (the E9 log-arm demonstration); log1p(birds) 0.232→0.059 (below floor);
1/v(velocity) 0.422 vs raw-avoid 0.353 vs vmax−v 0.090.

**R1.4 Orientation-artefact result:** additive flips cost gHM 94% (0.742→0.042) and
macrorefugia 75% (0.353→0.090) of leverage; multiplicative 1/v recovers 0.422. [pre/post audit]

**R1.5 Leverage predicts Morris μ\*:** Spearman +0.922 over 8 continuous features, zero solves.

## R2. Gate 0 — stopping-rule validation (binary MILP, Gurobi, gap 1e-4, NumericFocus, w=t)

**R2.1 All targets bind at the kink** (capture = target to 4 decimals) [iter8/a1,a2,a3]:
a1 m_soc 0.3320/0.332; a2 0.3000+0.3000/0.30; a3 0.4000+0.4000/0.40. No overshoot under w=t.
(Contrast, superseded w=1 arm: biomass 0.259 vs 0.066 target — co-capture; basis of the
corrected pass criterion.)

**R2.2 Pull-invariance proof (a4):** connectivity w=t=0.6 (unreachable target) reproduces the
control EXACTLY — 0 of 1,272,914 cells differ; common-objective identical to 6 decimals.
[iter8/a4 vs a0; also LP twins: 0 cells]

**R2.3 Control dominance (the problem the target solves):** a0 m_soc capture **54.2%** (1.81×
area share), biomass 41.3%; every non-carbon value 0.96–1.06×. Dominance GREW from iter6's
45.5% after penalty removal + 1/v. [iter8/a0]

**R2.4 Reallocation (a1 − a0, percentage points):** biomass **+8.4**; birds +2.2; mammals
+1.6; macrorefugia +1.1; connectivity +0.2; corridors **−1.4**; intactness −0.2. Under-served
EFGs (below area share in a0): mean 0.22 → a1 0.27 → a2 **0.53**. Map movement vs control:
Jaccard 0.78 (a1), 0.63 (a2), 0.79 (a3). [iter8 representation CSVs]

**R2.5 Relaxation tightness:** LP twins ~100% integral; LP-vs-MILP Jaccard 0.97–1.00 per arm;
max capture delta ≤ 1.4 pts. (Caveat: iter7 twins are pre-dust-threshold; cross-stack deltas
include a ≤1.5e-5 mass effect.) [iter7 vs iter8]

**R2.6 Solve times (final config):** a0 17 s / a1 81 s / a2 1,197 s / a3 1,269 s / a4 20 s;
batch 43 min. Flat double-target arms are the expensive ones. [iter8 run_summaries]

## R3. Numerical-integrity results (methods-validation, reportable)

**R3.1 False certificate:** un-focused Gurobi certified 5.179758 as optimal on a4 (true optimum
5.158146, exact via integral LP twin); bit-identical across two runs; root LP mis-convergence
0.42%; matrix range [1e-11, 1e5] with Gurobi's own range warning. [iter8/a4_pullcheck_v2]
**R3.2 Fix effect:** NumericFocus 2 → exact optimum in **17 s vs 1,080 s** (60× faster);
a0 304→17 s. [v3 + final a0]
**R3.3 Dust threshold effect:** 65,897 cells zeroed (≤1.5e-5 of any feature's mass); matrix
range → **[1e-4, 1e5]** in all five logs; audit classifications and the 0.332 target invariant;
PU unchanged at 1,272,914. [02 output; T2 re-freeze]
**R3.4 Solver-path result:** the targeted LP that took 71 min on HiGHS (presolve) solves in
24–81 s on Gurobi — pathology was solver-specific, not problem hardness.
**R3.5 Degeneracy status: OPEN.** The 68k-cell divergence was numerics artifact (R2.2 shows
exact agreement); surviving plateau evidence: LP-vs-MILP swaps ~2% of cells at ≈equal
objective. Gate 2 pools are the designed test.

## R4. Standing results from the inherited redesign (context/limitations)

**R4.1 Footprint bias (disclosed):** NEW selections mean gHM 0.074 vs 0.055 passed-over;
locked PAs 0.022 mask it in whole-solution averages; driver: AOH–gHM Spearman +0.636 (birds) /
+0.607 (mammals). [footprint_audit on iter6; re-run on final arm pending 04]
**R4.2 Climate-scenario materiality:** six realizations, worst-pair top-30% Jaccard 0.460
(inter-input context 0.11–0.24) → MATERIAL by pre-registered rule; axis = SSP245 vs SSP585 both
2071–2100 (measured Jaccard 0.574).
**R4.3 EFG-target rejection numbers:** 5 over-served EFGs = 736 cells (cap frees ≤0.13% of
budget); 9 under-served span 61.7% of region (lifting costs ≥12.7%).

## R5. Gate 1 — S0 construction (built 2026-08-27; entries PENDING-RUN until Ethan executes)

**R5.1 (PENDING-RUN)** Biomass θ-tail capture diagnostic [05_s0_construction §A]: a1 and a0
capture rates (cell-count + mass-weighted), SOC-claim co-capture vs independent selection,
regional SOC/biomass mass split, and the pre-registered verdict (rule: ≥0.90 → mass-proportional;
0.50–0.90 → equal; <0.50 → STOP). Fill measured numbers here.
**R5.2 (PENDING-RUN)** Climate realization QA [02 closing section]: 585-vs-stack max |delta|
(provenance), per-realization leverage (expect within 0.42–0.52), top-30% Jaccard between axis
levels (expect ≈0.574).
**R5.3 (PENDING-RUN)** Derived scenario table (T1 skeleton) [05 §B → `spec/scenarios_v1.json`]:
S0–S4 weight vectors + targets. Dry-run values on the frozen stack (mass-proportional
illustration, mean-1 normalized): macrorefugia w 1.460, connectivity 0.669, corridors 1.171,
m_soc 0.463 (t 0.332), biomass 0.200, birds 1.329, mammals 1.707 — a1's implicit biomass share
~29% of discretionary swing falls to ~6.5% by construction. Final values depend on R5.1's split.
**R5.4** S4 target via θ=3× archive lookup = **0.552** (@ ~9.8% of region) — verified against the
frozen `feature_audit.npz` during the build; the D2 budget-independence demonstration. [audit
archive]

## Figure/table candidates (running)

- F8 marginal-density trajectories (θ crossings + area labels) — rendered, final stack.
- Feature cards ×10 — rendered (review artifacts / supplement).
- T2 characterization table — frozen CSV.
- Gate-0 capture-vs-target + reallocation table — from R2.1/R2.4.
- LP-vs-MILP tightness table — R2.5.
- Numerics vignette box/figure — R3.1–R3.3 (matrix-range before/after; 60× speedup).

*Last updated 2026-08-27.*
