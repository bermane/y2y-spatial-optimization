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

## R5. Gate 1 — S0 construction (run 2026-08-27, all asserts clean)

**R5.1 Biomass θ-tail capture diagnostic — TAIL CAPTURED, (a) mass-proportional adopted by the
pre-registered rule.** Tail = 14,919 cells (1.17% of PU, cutoff 105.6 t/ha; m_soc tail 4.06% @
303.7 t/ha — both match frozen T2 exactly). a1 selected 14,917/14,919 tail cells: capture
**0.9999 by cells, 1.000 by mass** (a0: 0.9979 / 0.9981). **Decomposition REFUTES the co-capture
hypothesis:** only 1.0% of biomass-tail cells lie inside the m_soc θ-tail, so SOC-claim
co-capture is 0.011 of tail mass and **0.989 is independent selection** — the tail is bought
because dense biomass is attractive in its own right, not because the SOC claim overlaps it.
Regional carbon mass split: SOC 74.2% / biomass 25.8% (spec's ~74/26 confirmed). Caveat carried
forward by design: measured at biomass w=1; the standing T1/E7 θ-tail diagnostic verifies the
tail stays captured under S0's w≈0.20 when cells solve (pre-stated expectation: high).
[05_s0_construction §A]
**R5.2 Climate realization QA:** 585 realization **bit-identical** to the stack's canonical
macrorefugia layer (max |delta| = 0.0 — provenance proven, and the independently re-derived
pipeline reproduces Stage 2 exactly); dust zeroed **0 cells** on both realizations (1/v of
velocity has no near-zero residue: min v 0.097 → 1/v ≥ 0.097); leverage 245 = 0.482
[0.116, 0.599], 585 = 0.422 [0.135, 0.558]; top-30% Jaccard = **0.574** (equals the D6
raw-velocity measurement, as the monotone-map argument predicts). PU unchanged at 1,272,914.
[02 closing section]
**R5.3 Derived scenario family (frozen to `spec/scenarios_v1.json`, split_rule=mass 74.2/25.8,
mean-1 normalized).** S0: macrorefugia **1.460**, connectivity 0.669, corridors 1.171, m_soc
**0.465** (t 0.332), biomass **0.199**, birds 1.329, mammals 1.708 — biomass's implicit ~29%
share under the retired w=t convention falls to 6.45% by construction. S1–S3 double their block
(e.g. S1 macrorefugia 3.091; S3 mammals 2.743); S4 (carbon ×2 + θ=3×): m_soc 1.166 @ t 0.552,
biomass 0.501. Realized == intended shares asserted for every scenario. [05 §B]
**R5.4** S4 target via θ=3× archive lookup = **0.552** (@ 9.8% of region; θ=10× → 0.121) —
recomputed live from the frozen `feature_audit.npz`, zero solves: the D2 budget-independence
demonstration. [audit archive]

## R6. Gate 2 — first 1 km pool run (RUN 2026-08-27; verdict = NEAR-BINARY, fail branch fired)

**R6.1 Pool cost:** LP twin **6,516 s** (109 min — the worst HiGHS-presolve case yet, extending
M5.5's record: targeted+weighted LPs are the pathological shape; Gurobi's LP-equivalent single
took 55 s); certified single MILP **55 s**; pool (k=50, g=5%) **1,799 s = 32.8× the single**.
14-cell ensemble projection: 14 × pool ≈ **7.0 h** of pools + ~13 min of single anchors (+ LP
twins only if kept on HiGHS — 14 × 109 min ≈ 25 h, a reason to reconsider the twin's solver).
[06 report cell]
**R6.2 Pool integrity:** 50 returned, **50 distinct**; frequency cross-check exact (engine ==
recomputed); objective cross-check engine-vs-CSV max |Δ| = 2.98e-05 (≈5.6e-6 relative —
CSV-precision level, reconciled); pool best 5.362813 / worst 5.362830 → **span 3.2e-6 relative,
vs the 5% pool gap**; single certified 5.362860 (its own gap cert 0.0009%); LP lower bound
5.362810 → true optimum pinned in [5.362810, 5.362813]. All 50 solutions: identical size
381,874 cells, statuses OPTIMAL. [07 §A; run_summary solver_provenance]
**R6.3 Degeneracy verdict — NEAR-BINARY (pre-registered rule, M4.10):** k_distinct 50, but the
50 are near-clones: discretionary union 190,926 cells, **conditional (0<f<1) cells 165 = 0.09%**
(rule threshold: <1% fires), mean pairwise Jaccard **0.9999**. **Mechanistic reading (the finding
that frames the pivot):** PoolSearchMode=2 returns the k BEST solutions, and the plateau at the
optimum is so dense (≥50 solutions within 3e-6 relative) that the enumeration never leaves the
optimum's immediate neighborhood — **the g=5% band exists as a constraint but is never sampled**.
This is E5's enumeration-order-bias concern demonstrated maximally. The verdict is therefore
about the ESTIMATOR as operationalized (k-best pool ⇒ within-cell frequency ≈ indicator of the
optimum); whether the full 5% band is diverse remains unmeasured by this estimator. Pivot
options → chat (spec §2.9): (a) diversity-controlled within-cell generation (Brunel-style MGA:
maximize dissimilarity s.t. objective ≤ (1+g)·opt — E5's comparator becomes the estimator; at
55 s/solve, k=50 ≈ 46 min/cell, same order as the pool); (b) accept within-cell ≈ degenerate →
hierarchical estimand reduces toward one-solve-per-cell, pivot to Claims B+C; (c) demonstration
problem. [07 §B]
**R6.4 S0 realized vs intended (certified single):** biomass capture **31.0%** (prediction band
was 30–37; anchors 25.9 floor / 41.3 a0 / 49.7 a1) — "co-benefit, not driver" achieved. Captures:
refugia 45.2%, m_soc 33.2% (AT target), birds 33.0%, mammals 32.7%, connectivity 33.4%, corridors
26.0%, intactness 29.9%. **θ-tail capture (standing T1/E7 diagnostic) — the pre-stated biomass
expectation FAILED: biomass tail mass capture 0.425** (vs 1.000 at w=1 in a1), m_soc tail 0.435;
connectivity tail 0.980, refugia tail 1.000. Design insight the diagnostic surfaced as intended:
**a total-capture target does not protect the dense tail** — co-capture elsewhere satisfies the
claim, letting the solver skip ~57% of both carbon tails. Reported, not buried; a dense-stand
guarantee would need a tail-restricted feature (chat question). Realized-vs-intended influence
shares: largest miss m_soc +0.089 (realized 0.275 vs intended 0.186) — structural, not
miscalibration: a satiating feature realizes 100% of its claim while diffuse features realize
only ~40–50% of their cap_max range under competition, so realized shares tilt toward the
satiating member (Claim C's stated first-order caveat, now measured). [07 §C]
**R6.5 LP-twin tightness on S0:** LP **100.00% integral**, LP-vs-MILP Jaccard 0.9957, max
capture delta 0.0006 — the S0 LP relaxation is effectively exact. [07 §D]
**R6.6 E4 seed written:** `runs/gate2_s0_ref/solutions.npz` (50 × 1,272,914) + cell_audit.json;
frequency figure `figures/gate2_s0_frequency.png`. Note for E4's design: with a k-best pool,
k-subsampling (10/30/50) varies only trivial perturbations — E4 is moot unless the estimator
changes per R6.3. [07 §E]

## R7. Gate 2a/2b — tail features + MGA reference run (built 2026-08-28; PENDING-RUN)

**R7.1 (PENDING-RUN)** Tail-feature build + re-audit [08]: cutoffs and area/mass shares vs the
frozen T2 (expect 303.7 t/ha @ 4.06% / 33.2% mass; 105.6 @ 1.17% / 6.6%); audit class under
frozen rules (expected rare-attainable, both); manifest = 10 continuous features, tail targets
0.0 everywhere by default.
**R7.2 (PENDING-RUN)** Anchor equivalence [09]: v2-stack S0 anchor objective vs iter9's
5.362813 (t=0 tails must be inert; assert <1e-3).
**R7.3 (PENDING-RUN)** MGA sweeps [09]: per-g member counts, band certificates, duplicate /
time-limited counts, Hamming-to-anchor ranges, wall time (~1 min/iterate predicted; per-cell
ensemble cost revision).
**R7.4 (PENDING-RUN)** Verdict rule v2 [10 §B]: D and C at g = 2/5/10%, conditional share
(reported only), verdict at g=5% (PLATEAU-RICH / NEAR-UNIQUE / INTERMEDIATE) → the Gate-3 vs
Claims-B+C decision with the chat.
**R7.5 (PENDING-RUN)** f(g) core-erosion curves [10 §C] — E4's central product; figures
`gate2b_core_erosion.png`, `gate2b_s0_frequency_mga.png`.

## Figure/table candidates (running)

- F8 marginal-density trajectories (θ crossings + area labels) — rendered, final stack.
- Feature cards ×10 — rendered (review artifacts / supplement).
- T2 characterization table — frozen CSV.
- Gate-0 capture-vs-target + reallocation table — from R2.1/R2.4.
- LP-vs-MILP tightness table — R2.5.
- Numerics vignette box/figure — R3.1–R3.3 (matrix-range before/after; 60× speedup).

*Last updated 2026-08-27.*
