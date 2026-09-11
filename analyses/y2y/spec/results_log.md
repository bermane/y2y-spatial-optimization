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
14-formulation ensemble projection: 14 × pool ≈ **7.0 h** of pools + ~13 min of single anchors (+ LP
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
about the ESTIMATOR as operationalized (k-best pool ⇒ within-formulation frequency ≈ indicator of the
optimum); whether the full 5% band is diverse remains unmeasured by this estimator. Pivot
options → chat (spec §2.9): (a) diversity-controlled within-formulation generation (Brunel-style MGA:
maximize dissimilarity s.t. objective ≤ (1+g)·opt — E5's comparator becomes the estimator; at
55 s/solve, k=50 ≈ 46 min/formulation, same order as the pool); (b) accept within-formulation ≈ degenerate →
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
**R6.6 E4 seed written:** `runs/gate2_s0_ref/solutions.npz` (50 × 1,272,914) + formulation_audit.json;
frequency figure `figures/gate2_s0_frequency.png`. Note for E4's design: with a k-best pool,
k-subsampling (10/30/50) varies only trivial perturbations — E4 is moot unless the estimator
changes per R6.3. [07 §E]

## R7. Gate 2a/2b — S4 pilot + MGA reference run (spec v0.11; built 2026-08-28)

**R7.1 Tail contingency PRE-VERIFIED (executed 2026-08-28 under v0.10, then stood down per
v0.11):** both masked-density tail features audited under the unchanged frozen rules came back
**rare-attainable exactly as predicted** — leverage 1.0, cap_max 1.0; m_soc_tail cutoff
303.7 t/ha @ 4.06% of PU / 33.2% of parent mass; biomass_tail 105.6 @ 1.17% / 6.6% — all
matching the frozen T2/archive to the printed digits. Layers quarantined
(`aligned_stack/_v010_tails_quarantine/`); addendum CSV + cards kept. The escalation path, if
it ever fires, starts from a verified mechanism. [08b run record; tail_addendum.csv]
**R7.2 S4 pilot — PASS (run 2026-08-28, `iter10_y2y_s4_pilot`, certified OPTIMAL, 54 s,
objective 5.0144).** θ-tail mass capture vs the pre-registered ≥0.75 band: **m_soc 0.960,
biomass 0.772** (S0 reference 0.435 / 0.425). Totals: m_soc **0.552 exactly at target**;
biomass 0.329 (vs S0's 0.310). **The mechanism finding:** carbon-forward pressure redirected
rather than expanded biomass capture — total +1.9 pts while tail capture nearly doubled
(0.425 → 0.772) — validating v0.11's places-through-pressure claim with zero formulation
change. Other captures under S4: refugia 0.418 (S0 0.452), corridors 0.284, birds 0.308,
mammals 0.310, connectivity 0.321, intactness 0.302. The S0→S4 tail contrast is the
amount-vs-places panel (F9). No escalation question arises (and none exists — M4.14).
**R7.3 MGA anchor (run 2026-08-28):** objective 5.3628, **gap 0 (exact), 8.1 s** — reproduces
iter9's certified optimum (assert passed). The direct-Gurobi compiled-model path is faster
than the engine path (8 s vs 55 s; no prioritizr build overhead).
**R7.4 MGA sweeps (run 2026-08-28, all three g levels clean):** 50/50 members per g, **zero
duplicates, zero time-limits, every band certificate binding EXACTLY at its wall** (2.00 /
5.00 / 10.00% over optimum — the distance maximizer pushes to the boundary, as designed).
**Iterations averaged 10–16 s (not the predicted ~55 s); whole Gate 2b = ~32 min** (g02 10.0 /
g05 13.3 / g10 8.4 min). **Headline raw signal: the band is WIDE.** Hamming-to-anchor ranges:
g02 135k–260k; g05 **180k–359k**; g10 121k–**381,691** — against a theoretical same-size
maximum of 2×m_disc ≈ 381,690, i.e. at g=10% a member exists sharing essentially ZERO
discretionary cells with the anchor, and even at 2% up to 68% of the discretionary selection
can be swapped. Together with R6.3 (k-best: 50 near-clones), the shape is now clear: **a
sharp, essentially unique optimum sitting on a very wide, shallow near-optimal bowl** — the
two instruments measured different properties, and both are paper results. Formal D/C verdict
(rule v2, frozen) → 10_gate2b_analysis. Ensemble cost re-projection: ≈13 min MGA + ~10 s
anchor per cell (+ one k-best pool + Gurobi-path twin) ⇒ ~45–60 min/formulation, ~10–14 h for the
14-formulation ensemble, serial. [certificates_g*.csv; gate2b_meta.json]
**R7.5 Verdict rule v2 — PLATEAU-RICH (run 2026-08-30; rule hash v2_8db80fed1c702638;
"Claim A carries; proceed to Gate 3").** At g=5%: **D = 0.953, C = 0.020** — decisively past
the frozen thresholds (D ≥ 0.10, C ≤ 0.90). All 51 solutions per g; every band certificate
holds; diversity does not collapse over the sweep (g05 Hamming-to-anchor trajectory: 359k
first member, stabilizing ~250k by the tail). Conditional share 96.9–100% (reported, not
ruled — MGA inflates it by construction). D at g10 = 1.0000052 (>1 by 5e-6: members are not
forced to identical size under the ≤-budget row; trivial). [formulation_audit.json]
**R7.6 Core erosion f(g) — E4's central product, and a headline finding:** the f=1 always-core
among the 51 solutions is **22,866 discretionary cells (12.0% of the selection) at g=2% →
3,829 (2.0%) at g=5% → 0 (ZERO) at g=10%**. At 10% tolerance no individual discretionary cell
appears in every near-optimal plan; even at 5% only ~3.8k cells are unconditional. The union
runs the other way: 737k discretionary cells appear in SOME 2%-optimal plan, 1.07M at 5%,
**1,081,885 at 10% ≈ every discretionary cell in the landscape** (1,082,069 exist). Paper
sentences this buys: "essentially any cell can be part of a near-optimal plan; almost no cell
is required by one" — the strongest possible motivation for frequency surfaces over single
maps, and the exact geometry (sharp unique optimum, wide shallow bowl, vanishing core) the
two-instrument pair measured. Figures: `gate2b_core_erosion.png`,
`gate2b_s0_frequency_mga.png`; seed `solutions_g05.npz`. [10 §B–§D]

## R8. Gate 3 freeze + Gate 4 ensemble (built 2026-08-30; PENDING-RUN)

**R8.1 The freeze EXECUTED (2026-08-30, 11_gate3_freeze):** `spec/manifest.csv` (14
formulations, all frozen=true, ids unique) + `manifest_freeze.sha256` = d45668bb… (hash
verified). Roster: {S0–S5} × {ssp585, ssp245} + s1x/s3x crossed @ ssp585-θ3. Measured ssp245
re-derivations (constant intended influence): S0's macrorefugia w 1.460→1.313 (leverage
0.422→0.482), all others re-normalize upward slightly; crossed formulations reproduce their
parents' vectors with only the m_soc t=0.552 re-derivation (w 0.328→0.326 in s1x). S5 = S0 +
gHM×10. Commit of the two spec files = the pre-registration timestamp. [11 outputs]
**R8.2 Ensemble EXECUTED (2026-08-31→09-01, 13 open formulations + reference pointers; all
artifacts complete).** Anchors 44–58 s (all exact/1e-4); twins 10–14 s (Gurobi LP; every
LP ≤ MILP check passed); MGA 36–50 min per formulation (~55 s/iteration; the reference's
13 min was the outlier); k-best pools 549–1,822 s with full 50 — EXCEPT `s3_ssp585_theta5`,
which hit the 12 h solver_time_limit (43,210 s) with 38/50 (same scenario on the 245 layer:
1,067 s — pool difficulty is formulation-specific, spread 79×; disclosed: a time-limited pool
holds certified in-gap incumbents, not a proven top-38). Wall ≈ 22 h including that solve.
**R8.3 F (Claim A) + E1 + E2:** ensemble bands over discretionary land — **always (F≥0.95):
0 km²**; frequent (0.70–0.95): **6,816**; conditional: 93,408; rare: 951,972; never: 29,689.
Across 14 value/climate positions × 51 diverse plans each, NO discretionary cell is universal
— the strongest ensemble tier is "frequent," 6,816 km². `runs/ensemble_v1/F_surface.tif`
written (the deliverable surface). **E1: the hierarchical correction is large — mean |F −
F_naive| = 0.169, max 0.755, 726,287 cells shifted by >0.1** (under the k-best estimator this
would have been ≈0; Claim A's motivating effect is real at full scale). E2: equal k across
formulations ⇒ flat pooling ≡ hierarchical mean (definitional; divergence requires unequal k).
**R8.4 E3 variance decomposition (per-PU, estimator-conditional — within = MGA band breadth,
not sampling noise):** within-formulation **95.2%**, scenario 4.4%, climate **0.2%**; crossed
regime contrast mean |Δf|: s1 0.017, s3 0.002. Reading: near-optimal freedom dwarfs value
disagreement, and the climate axis barely moves the frequency surface at all (despite the
realizations' own top-30% Jaccard of 0.574 — the objective's economics dominate the refugia
pattern shift). Per-formulation diameters D_s = 0.809–1.000: EVERY formulation is
plateau-rich; both S5 formulations hit D = 1.000 exactly (a full discretionary-turnover plan
exists within 5% when the pushed feature is inexpressible).
**R8.5 E7 (T1/T3):** anchor captures move in NARROW ranges across the 14 formulations —
refugia 0.397–0.486, connectivity 0.306–0.388, biomass 0.271–0.329, birds 0.308–0.344,
mammals 0.310–0.339 (m_soc 0.332–0.552 by target design) — while anchor MAPS differ at
Jaccard down to 0.373: **value scenarios reallocate places far more than outcomes.** θ-tail
rates: S4_ssp585 0.959/0.774 (pilot band HELD); S4_ssp245 0.974/**0.716** (biomass marginally
below the 0.75 band under the 245 layer — the pilot was registered on 585; finding, not
gate-fail); crossed s1x 0.697/0.302, s3x 0.584/0.353 — **a deep target WITHOUT the doubled
carbon weights does not hold the tails** (dose-response completing M6.7: places semantics
needs target + weights together). S3 gHM audits consistent with R4.1's bias. T1 CSVs in spec/.
**R8.5b Crossed-formulation target shortfalls (surfaced by 14_gate4_results, 2026-09-01):**
in s1x/s3x the deep m_soc target is NOT met — captures 0.442 / 0.366 vs t = 0.552 (the S4
formulations hit 0.552 exactly). A real, correctly-signed shortfall, not a QA failure: with
S1/S3's low carbon weights, the solver accepts m_soc shortfall rather than pay the area cost.
Completes the lever picture: **a target binds only as far as its weight makes pursuit
worthwhile** — under-weighted deep targets are aspirations, not guarantees (pairs with M6.7
and the tail dose-response). [T1_anchor_captures.csv]
**R8.6 E11 (F10):** between-anchor discretionary Jaccard 0.373–0.931 (mean 0.520); envelope
comparison: within-formulation diameters (0.81–1.00) EXCEED between-anchor distances — value
disagreement fits INSIDE the near-optimal freedom of any single value position. Δ(s,s′)
matrix (diagonal ≤ 9.3e-6 after the layer-consistency fix, M5.11): **156/182 ordered pairs
sit inside each other's 5% bands — the certified no-regrets form of value pluralism** — and
all 26 out-of-band pairs are other anchors under CARBON-FORWARD objectives (Δ 0.085–0.093):
the deep m_soc target is the one value position whose demands other near-optimal plans
genuinely fail. E11 CSVs in spec/; F10 regenerated.
## R9. v0.13 post-R8 round (15 run 2026-09-02; 16/17 PENDING-RUN)

**R9.1 E13 — binding-scarcity mechanism CONFIRMED (zero solves):** S4's f≥0.70 set lies
**80.8% inside the m_soc θ-tail**; S0's and S2's high-f sets sit only 4–5% on the tail and
1–4% on the connectivity spike — high frequency follows BINDING CLAIMS, not valued layers
(the Q2 explanation may now enter Discussion). The EFG-presence mask is uninformative as an
overlay (EFGs cover ~100% of every high-f set). Decile fingerprints figure written.
**R9.2 E14 — the aggregate band is NOT a per-value band; E15 trigger FIRED:** in EVERY
formulation, ~100% of members carry at least one value block below 0.95× its anchor capture
(e.g., S0 members drop the core-habitat block 0.428 → 0.364, ~15% below anchor). The 5%
aggregate tolerance is routinely financed by sacrificing whole blocks — itself a paper
finding about band semantics. E15 (guardrailed band, S0 + S4) authorized by the
pre-registered rule.
**R9.3 E17-T2 — the representativeness foundation is strongly southern:** 20/40 EFGs have
>90% of their footprint south of 53°N; median EFG mean-latitude 48.6°N (several classes
entirely at 42–44°N). A representativeness-adequacy disclosure regardless of other results;
per-EFG table in `spec/e17_efg_geography.csv`. T1 latitude profiles figure written.
**R9.4 E12 bracket — f is estimator-robust; only the diameter is estimator-sensitive (run
2026-09-02):** corr(f_MGA, f_MAA) = 0.916 / 0.851 / 0.964 (S0/S2/S4); frequent-band sizes
agree within ~5% (11.2k vs 10.8k; 4.7k vs 4.9k; 28.7k vs 30.1k km²); f=1 cores essentially
identical. D is lower under MAA (0.66–0.79 vs 0.88–0.98) — expected: random directions do
not find the extreme diameter, which is precisely why MGA is the right instrument for D
(a maximizing probe) while f is instrument-independent. **Recommendation: bracket is narrow —
full-14 MAA unnecessary; report the 3-formulation bracket.**
**R9.5 E17-T3 — every pre-stated direction confirmed; the EFG foundation is the biggest
latitudinal force:** vs the S0 anchor's mean discretionary latitude 50.96°N — biodiversity-out
**+1.18°** north (as pre-stated: AOH mass is southern); carbon-out −1.18° south (as
pre-stated); connectivity-out −0.96°; core-habitat-out −0.17°; **EFG-out +2.11° north,
Jaccard 0.695 — the largest single mover.** Combined with R9.3 (20/40 EFGs >90% southern):
the representativeness foundation is a ~2-degree southern anchor on every plan — the
formulation's strongest un-chosen geographic lean, now measured causally. → chat (disclosure
+ scenario-reading remedy ladder per spec).
**R9.6 E8/E9/E10 (run 2026-09-02):** **E8** — m_soc ×10 → Jaccard vs anchor 0.996/0.994 (S0/
S3), capture identical 0.3320: satiation-inertness CONFIRMED at scale. **E9** — the lever
justification in one table: weights-only drifts (capture 0.462, uncontrolled, densest-decile
0.632); the target is the precision instrument (0.332 exact, densest-decile 0.392);
**log-carbon is the value-destroying instrument (capture 0.266, densest-decile 0.236 — worst
per-hectare, exactly as the frozen screening predicted).** **E10** — θ3 parks exactly
(0.5520); **θ10 does NOT bind: capture 0.229 vs target 0.121** — below the incidental
co-capture level (~0.23 under S0 shares) a target is a non-binding decoration; the corrected
pass criterion observed in the wild. Capture-vs-θ curve: 0.229 / 0.332 / 0.552 at t = 0.121 /
0.332 / 0.552.
**R9.7 E15 — guardrails DOUBLE the nameable land at almost no flexibility cost:** with
per-block floors (capture_b ≥ 0.95·anchor_b), S0's frequent tier grows **11,247 → 23,108 km²**
while D falls only 0.953 → 0.913 (C 0.020 → 0.042); S4: 28,748 → 34,787 km² (D 0.875 → 0.854).
"No value block left behind" buys ~2× the committed area for ~4% of the diameter. **E15b MEASURED (2026-09-03):
per-VALUE floors add almost nothing beyond the block floors — the commitment curve SATURATES
at the theme level.** S0: value-guarded frequent 23,996 km² vs block-guarded 23,108 (+4%),
D 0.909 vs 0.913; S4: 34,427 vs 34,787 (within noise), D 0.850 vs 0.854. Both sweeps clean
(50/50 members, all certificates, 15 min each — the extra floors also make the solves FASTER,
~15 vs ~50 min, by shrinking the feasible set). Reading: the plain→block step is the whole
effect (11.2k→23.1k km² at S0); block→value is marginal — the guardrail dial's natural
resting point is the elicited theme level, and finer granularity is free but redundant. — the honest
commitment dial the force-targets discussion was groping toward, at pre-registered secondary
semantics. → chat: promote to a headline product?
**R9.8 ERRATUM to R7.6 (found 2026-09-02 during AB-spec verification; supersedes the R7.6
denominator, strengthens the finding):** the discretionary-cell count is **1,081,885**
(= 1,272,914 PU − 191,029 locked; matches nb 10's own printed header), not the 1,082,069 in
R7.6 and `gate2b_reportback.md` — that figure is 1,272,914 − 190,845, i.e. the anchor's
discretionary-SELECTION size mistaken for the locked count. Re-measured from
`runs/s0_ssp585_theta5/mga_g10.tif` (all 50 bands) + `anchor.tif`: union at g=10% =
**1,081,885 of 1,081,885 — EXACTLY every discretionary cell (100.000%), not "≈ every"**. The
paper sentence gets stronger, not weaker. Same swap appears in spec v0.12 changelog item (4)
("1,081,885/1,082,069") and AB-spec v0.2's changelog ("1,082,069 discretionary cells");
AB-spec v0.3's D-AB5 numbers (191,029 locked / 190,845 discretionary selected) are correct.

## R10. E15 completion + director package (built 2026-09-03; 18 PENDING-RUN, 19/20 follow)

**R10.1 Guarded-sweep cost, measured on the two existing sweeps (S0/S4 certificates):** guarded
MGA 11.2 min (S0, median iterate 14.1 s) / 12.0 min (S4, 15.8 s) vs the plain band's 13.3 / 46.1 min;
per-value floors 15.1 / 15.3 min; MAA 13.2 / 18.0 min. Floors SHRINK the feasible set — S4's plain
sweep was the slow one, its guarded sweep is not. Projection for the 12 open formulations ≈ 2.5–3 h
serial (director spec's 8–10 h superseded).
**R10.1 CORRECTION (18 RUN 2026-09-03/04): the projection was WRONG.** The 12 open guarded sweeps took
52.5–75.6 min each (median iterate ~60–90 s), the S0 guarded MAA spot-check 59.7 min; total guarded solve
time **12.27 h** — the director spec's 8–10 h was the better estimate. The 16-era S0/S4 sweeps (11–12 min)
were not representative; the uniform ~5× slowdown across every formulation points to machine/WLS
conditions rather than problem difficulty (S0 itself is 11 min in the 16 record). Integrity is perfect:
14/14 sweeps × 50 members, every band certificate OK, zero duplicates, zero time-limited iterates,
re-solved anchors within ≤9e-6 relative of the frozen record and **0 cells differing from anchor.tif**
in all 12 (no near-tie divergence); band edges reached exactly (max +5.000% of z*; S5 +4.3%).
Within the same run window the guarded iterate is only ~1.2× the plain one (medians 64–96 s vs the
Gate-4 record's 50–62 s for the same formulations); the fast/slow split is BY DATE, not by semantics —
Gate 2b S0 (16 s/iterate) and the 16-era S0/S4 sweeps (14–16 s) vs Gate 4 and 18 (50–96 s) — i.e. the
machine-conditions lesson of 06 again. Wall time 2026-09-03 18:25 → 09-04 05:39 (~11.3 h).
Cause confirmed by Ethan: concurrent analyses on the same machine (a MacBook Air) during 18 — solve
times here are wall time under contention, not problem difficulty; report the compute platform as such.
**R10.2 Guarded ensemble — PENDING 18:** guarded F bands (never/rare/conditional/frequent/always,
discretionary km²) side by side with the unguarded record (R8: frequent 6,816 km², always 0);
Act tiers (core / scenario-specific / opportunity / never); per-formulation guarded frequent tiers
and D (plain → guarded); pooling verdict per scenario (Jaccard of frequent tiers, rule ≥ 0.80);
guarded MAA spot-check on S0 (corr f_guardMGA vs f_guardMAA, tier Jaccard). All printed
results_log-ready by 19 (`director_package/summary.json` + `tables/`).
**R10.3 Cluster register — PENDING 19:** Act-1 core clusters ≥ 100 km² (count, total km², largest),
sensitivity at 0.60/0.80, Act-2 residual clusters per scenario after core subtraction (mean core
overlap), driver attribution per cluster (θ-tail / spike / rarest-EFG), IPCA-proposal overlap.
(A partial smoke-run on S0+S4 only — NOT a result — exercised every cell end-to-end.)
**R10.4 Protected baseline (T-D5; zero-solve, measured 2026-09-03 from the hand-off stack under M3.6
accounting):** the locked PA estate (191,029 km² = 15.0% of the PU = 50.0% of the 30% budget) already
holds **12.3% (biomass) – 19.2% (refugia)** of every value's regional total — intactness 15.5, transboundary
connectivity 14.9, climate corridors 14.3, m_soc 17.6, mammals 15.9, birds 15.3 — and **35/40 EFG
classes are present inside PAs**. Against the S0 targets that is 12–19% of each t = 1.0 target banked and
**53% of m_soc's 0.332 target** (15.6 points still needed from unprotected land). Director reading: the
PA half of the budget delivers roughly one-sixth of each value; the tiers are about the other half.
**Enrichment (capture share ÷ area share, PAs = 15.0% of the PU): the existing estate is VALUE-PROPORTIONAL
for the mission values — 0.82× (biomass) to 1.28× (refugia); m_soc 1.18, mammals 1.06, intactness 1.03,
birds 1.02, connectivity 0.99, corridors 0.95.** The optimizer's discretionary half (S0 anchor minus the
banked share, over the remaining 15% of area) works at 0.78× (corridors) – 1.74× (refugia); biomass 1.25,
connectivity 1.23, birds 1.18, mammals 1.12, m_soc 1.04 (target-limited), intactness 0.96 (inexpressible).
Caveat: intactness ≈ 1.0× because 1−gHM saturates near 1 almost everywhere (leverage 0.042) — in RAW gHM
the PAs ARE cleaner (0.022 vs 0.053 regional, 04a footprint audit); the share-of-sum currency cannot see
it, which is the R3-inexpressibility story in one number. Paper-worthy disclosure: a 2025 PA estate
that is average for every PROACT value, i.e. it was not built for them.
**R10.5 T-D5b enrichment by scenario (capture share ÷ area share; anchors FINAL, frequent tiers for
S0/S4 FINAL (already guarded, from 16), the other 12 tiers + the ensemble core PENDING 18):** every
anchor's new half concentrates its lead value modestly — S1 refugia 1.97×, S2 connectivity 1.59×, S3
birds 1.27×, S4 m_soc 2.51× — while the guarded FREQUENT tiers concentrate the BINDING value far harder:
S0's frequent tier is 4.11× on refugia (1.02× connectivity, 0.85× corridors, 0.93× biomass), S1's 3.29×
refugia, S4's **7.13× on m_soc and 0.53× on biomass** (0.80× birds); the 2-formulation ensemble core
3.92× refugia. Reading (E13 in enrichment currency): an optimal plan spreads its 15% across everything
at ~1–2×, but the cells that RECUR across near-optimal plans are the ones a binding claim cannot
substitute — the promise tier is a scarcity map, not a value map. Refugia's dominance in the frequent
tiers = its θ-tail-like concentration (leverage 0.422, reciprocal orientation) under the guarded band.
**R10.6 THE CORE IS REFUGIA COUNTRY (production, 14 formulations; Ethan's observation 2026-09-04,
verified):** climate macrorefugia is the most-enriched value of the frequent tier in 12 of 14 formulations
(2.60–4.65×; the ensemble core 4.37×) and second in the two carbon-forward ones (m_soc 7.13× / 5.92×,
refugia 2.07× / 1.85×). Mechanism, three facts: (i) it is ALREADY the pinned value in the unguarded band
(S0 plain frequent tier 2.16× refugia; ensemble 1.35×) — the guard AMPLIFIES it (S0 4.11×, ensemble 4.37×)
by forbidding the sacrifice E14 caught (members financed the aggregate band by dropping the core-habitat
block 0.428 → 0.364); (ii) it is INDEPENDENT of floor granularity and estimator — S0 block floors 4.11×,
per-value floors (E15b) 4.05×, MAA-guarded 3.99×; (iii) it is the value the balanced optimum leans on
hardest (anchor capture 0.452, the highest-leverage feature without a target cap; new-half enrichment 1.74×)
AND, among the uncapped values, the one whose 5% of the regional sum lives in the fewest unprotected cells
(12,788 vs connectivity 16,436, birds 41,496; m_soc 3,489 but target-capped) — so a 5% floor on it is
satisfied by the fewest, most fixed cells, which therefore recur in every member. E13 in one sentence: the
promise tier is the set of cells the tightest un-substitutable claim cannot do without. Director framing:
the durable core is climate-refugia country (plus dense soil carbon under carbon-forward values) — a
representativeness-style endorsement question of the same kind as E17: is Y2Y comfortable that the land it
can promise under every value position is defined by climate refugia?
**R10.7 Representativeness axis — the spec's construction misreads (Ethan's observation 2026-09-04):** with
"EFG classes present ÷ 40" the six Act-1 clusters score 0.20–0.35 and read as far below the 0.5 ring, but no
1 km cell holds more than 15 of the 40 classes (unprotected mean 4.5, median 4), so no cluster-sized patch
can approach 40. Tested against 300 equal-area random patches of unprotected land per cluster: the clusters
hold an AVERAGE-TO-ABOVE-AVERAGE number of classes (44th–81st percentile: Purcells 14 classes vs median 10,
p68; Mount Robson 12 vs 7, p81; Tahltan 8 vs 8, p44). On a per-cell EFG-count percentile — the same
construction as the other five axes — they sit at 0.73–0.96. Ruling: the star axis uses the per-cell
percentile; the raw class count ships in T-D1 (`efg_classes_present`). Refugia country is not ecosystem-poor.
**R10.8 Climate-level pooling check (decision g, production 19, 2026-09-04): NO scenario pools.** Frequent-tier
Jaccard between the SSP585 and SSP245 levels: S0 0.34, S1 0.41, S2 0.36, S3 0.34, S4 0.61, S5 0.34 — all
below the pre-stated 0.80 — so Act 2 shows every scenario per level (eight pairs). The low-emissions tiers
are consistently LARGER (S0 35,089 vs 23,108 km²; S1 60,940 vs 51,032; S3 15,349 vs 6,471; S4 42,479 vs
34,787). E3's "climate = 0.2% of variance" is a within-formulation variance share over all cells; tier
MEMBERSHIP at 0.70 is a sharper statistic and it moves — the two are not in conflict, but the paper must not
cite the former as if it implied the latter. The carbon-forward pair agrees most (0.61) because its tier is
pinned by the m_soc tail, which the climate layer does not touch.
**R10.9 Crossed hybrids as votes (2026-09-04):** s1x/s3x reproduce their parents' frequent tiers (Jaccard vs
S1-585 0.836, vs S3-585 0.947; corr(f) 0.971 / 0.992) and are unlike S4 (0.223 / 0.156) — they are second votes
for two positions, not new positions. Core (F ≥ 0.70) over all 14: 16,610 km²; over the 12 elicited: 16,895
km²; Jaccard 0.938 (681 km² gained, 396 lost). Ruling: package uses F12; paper keeps F14 + this sensitivity.
Also measured for the climate-axis question: SSP585-only core 17,880 km² (1.4% of Y2Y), SSP245-only 28,612
(2.2%), all-14 16,610 (1.3%); 21% of the SSP585-only core (3,829 km²) fails 0.70 once the other refugia
future is included; anchor Jaccard across climate levels (same scenario) mean 0.67 vs 0.54 across scenarios
(same level) — the refugia-realization axis moves plans about as much as the value axis. Ruling: axis KEPT
(the promise must survive both refugia futures; R10.6 makes that the exposure that matters), to be RENAMED
"refugia realization (two climate futures)" — it is not a climate-scenario axis, only one layer changes.
**R10.10 Act 1 by refugia future, 6 formulations each (package F12 basis; 2026-09-04):** SSP585 core 17,308 km²
(1.6% of unprotected land), SSP245 core 28,612 km² (2.6%), the 12-formulation core 16,895 km² (1.6%). The two
futures' cores overlap at Jaccard 0.33 (intersection 11,333 km², union 34,587 km²); 80% of the 12-core lies inside
the SSP585 core and 87% inside the SSP245 core. Reading: the 12-formulation core ≈ the intersection of the two
futures' cores plus a rim of cells that are strong in one future and moderate in the other; reporting "6 and 6"
separately would put ~35,000 km² on the table (union) of which only a third survives both futures. Low-emissions
refugia are more diffuse (larger core at the same threshold). ERRATUM to this session's earlier deck text: the
core was briefly double-counted (frequent + always, where "frequent" already meant ≥ 0.70) — figures and tables
were never affected, only one bullet string; fixed before any production render.
**R10.11 Climate-conditional core (T-D2 rows + the two-way map, 2026-09-04):** cell-level, F ≥ 0.70 under BOTH
refugia futures 11,333 km² (1.05% of unprotected land); core only under the high-emissions future 5,975 km²
(0.55%); only under the low-emissions future 17,279 km² (1.60%). The low-emissions-only land is three times the
high-emissions-only land — low-emissions refugia are more diffuse, so more cells clear 0.70 — and it sits in the
southern Rockies/Idaho, while the high-emissions-only land is north-western (Tahltan–Skeena). Director framing:
commit to the 11,333 regardless; the other 23,000 km² is a climate bet, labelled by which way it pays.
**R10.12 Act 2 by scenario (the summary map, 2026-09-04; package F12 basis, pooled f per scenario, ownership =
highest f where a cell is frequent under exactly one named scenario):** core-habitat-forward 29,249 km²,
carbon-forward 19,937, connectivity-forward 844, biodiversity-forward 407, frequent under 2+ named scenarios
3,549; Act 1 core 16,895. The two concentrated claims (refugia, soil carbon) own almost all scenario-specific
land; the two diffuse values add a few hundred km² each even when they lead at the ELICITED (doubled) emphasis — see
R10.13: at ~4× that emphasis connectivity does define its own tier; the statement is dose-dependent.
**R10.13 E18 RUN 2026-09-04 — VERDICT: WEIGHT-LIMITED. The "substitutability" reading of Act 2 (R10.12 prose,
and the chat explanation that preceded it) is RETRACTED.** Arm: S2 with connectivity weights × 5 (influence share
0.83), certified anchor (14 s, gap 0), 50 guarded members, all certificates OK, 55 min. Anchor: connectivity block
capture 0.297 (S0) → 0.335 (S2) → **0.384**; core habitat 0.452 → 0.420 → 0.340; anchor Jaccard vs S2 0.330. Frequent
tier: **34,705 km²** (S2-585: 11,086), Jaccard with S2's tier 0.054, only 3% inside the 12-position core (S2: 81%),
**own land 31,780 km²** (S2: 861); enrichment connectivity **3.09×** (S2 tier 1.92×), corridors 1.15× (0.82×),
refugia **0.88×** (4.65×), biomass 0.67×, birds 0.83×. So weight alone DOES create a connectivity tier — larger than
carbon-forward's (19,937 own) — once connectivity dominates the objective. Mechanism (share of the residual
shortfall objective at the anchor, w × relative shortfall): connectivity 0.31 (S0) → 0.55 (S2) → **0.84** (×5);
core habitat 0.19 → 0.12 → 0.05. What recurs is the value whose shortfall dominates the band's objective slack —
i.e. binding = WEIGHT × CONCENTRATION, not concentration alone. At the elicited doubling (S2) refugia still binds
(fewer cells per unit of its sum: 12,788 vs 16,436 for 5% of the sum, and still 12% of the objective); at ~4× the
elicited emphasis the price of dropping connectivity cells exceeds the band, and they pin. Implications: (i) the
Act 2 statement for connectivity/biodiversity is a DOSE statement — "at the doubled emphasis these values add
almost nothing to the promise; at dominance (≥0.8 of the objective) connectivity defines ~32,000 km² of its own" —
and the deck must say which magnitude "forward" means; (ii) R10.6's mechanism sentence is refined: the core is
refugia country at the elicited magnitudes because refugia is the most concentrated claim per unit weight, not
because diffuse values cannot pin; (iii) the earlier claim that "a bigger weight is not the route to a
connectivity tier" is withdrawn — it is A route, at a price (core habitat capture −0.08, biodiversity −0.03 at the
anchor). Open: the crossover multiplier (×3?) and the same test for biodiversity (21/22 now take BLOCK and MULT).
**R10.13 (cont.) E18 FULL DOSE TABLE (arms ran 2026-09-04/05, ~55 min each, all certificates OK; `spec/E18_dose_table.csv`):**

| arm | influence share | anchor capture of led block | frequent tier km² | own land km² | enrich led / refugia | max f | D | rule |
|---|---|---|---|---|---|---|---|---|
| S2 (base) | 0.50 | 0.335 | 11,086 | 861 | 1.37 / 4.65 | 1.00 | 0.963 | — |
| S2 ×2 | 0.67 | 0.366 | 12,687 | 7,925 | 2.30 / 2.44 | 1.00 | 0.942 | AMBIGUOUS (crossover) |
| S2 ×5 | 0.83 | 0.384 | 34,705 | 31,780 | 2.12 / 0.88 | 1.00 | 0.845 | WEIGHT-LIMITED |
| S3 (base) | 0.50 | 0.341 | 6,471 | 521 | 1.15 / 4.24 | 1.00 | 0.969 | — |
| S3 ×2 | 0.67 | 0.349 | 1,024 | 0 | 1.27 / 7.02 | 1.00 | 0.999 | SUBSTITUTABLE |
| S3 ×5 | 0.83 | 0.363 | **0** | 0 | n/a (empty tier) | **0.63** | **1.000** | rule: AMBIGUOUS (NaN); substantively the strongest SUBSTITUTABLE outcome |
| S4 carbon (base, m_soc t 0.552) | 0.50 | 0.440 | 34,787 | 20,329 | 3.83 / 2.07 | 1.00 | 0.854 | — |
| S4 weights-only (S0 targets, t 0.332; RAN 2026-09-08) | 0.50 | 0.370 | 16,425 | **763** | 1.40 / 4.03 | 1.00 | 0.927 | SUBSTITUTABLE |

(Carbon rows added 2026-09-08 when the fifth arm ran; the CSV now also carries max f, Gate-2b D = max pairwise Hamming ÷ 2·discretionary-
selected, and the R10.14 lead-magnitude currency, all computed in 22 — the earlier hand-computed values reproduce exactly.)

Reading. (1) The two diffuse blocks are NOT alike. Connectivity crosses over between influence share 0.67 and 0.83:
at ×2 its tier is already 62% own land with connectivity ≈ refugia enrichment (2.30 vs 2.44), at ×5 it owns
31,780 km². Biodiversity never pins at ANY dose: raising its share dissolves refugia's pinning (refugia's
objective share falls) without creating its own — the frequent tier shrinks 6,471 → 1,024 → 0 km², the maximum
frequency of any unprotected cell drops to 0.63, and D reaches exactly 1.000 (complete discretionary turnover
inside the 5 % band). (2) Mechanism, consistent with R10.13: pinning needs weight × concentration to make some
cells too expensive to drop within the band; connectivity's spike/pinch-point structure (5 % of its sum in 16,436
cells) reaches that price at ~4× the elicited emphasis, AOH richness (5 % in 41,496 cells, no tail) never does.
(3) The anchor moves monotonically for both (weights move the optimum: +0.05 connectivity, +0.02 biodiversity
capture at ×5) — the E7 places-not-outcomes result. (4) The verdict rule's NaN case (an EMPTY tier) was not
anticipated: recorded as the rule printed it, with the interpretation stated separately. Director sentence:
"leaning harder on connectivity eventually buys places of its own (≥ ~4× the elicited emphasis); leaning harder on
species richness buys none at any emphasis — it only erases the refugia core."
**R10.14 How hard does each scenario lead? (Ethan's fairness question, 2026-09-08; zero-solve):** the intended
influence share is 0.50 for all four forward scenarios by design, so on that currency they lead equally. On the
currency that decides recurrence — the min-shortfall cost of losing a cell, w_f·(v_i/T_f)/t_f, averaged over the led
block's 10,000 densest unprotected cells and divided by refugia's under the same scenario — they do not: S1 1.00
(led = refugia), S2 1.56, S3 1.74, **S4 4.59**; calibration from E18: S2 ×2 (crossover) 3.12, S2 ×5 (pins) 7.80,
S3 ×2 3.47, S3 ×5 8.68. Carbon-forward therefore leads at roughly the emphasis that took ×3 on S2 to reach — the
target does it twice over (a higher derived weight and the 1/t = 1.8× term on every dense-carbon cell). Caveat:
per-cell cost alone is not sufficient for pinning (S3 ×5 scores 8.7 yet has NO tier — its top cells are all
alike, so substitutes exist at the same cost); the currency ranks lead magnitude, the tail's steepness decides
whether it pins. Also: residual-shortfall share at the anchor UNDER-reads carbon (0.086 at S4) because its target
is nearly met there — not a usable lead currency for a satiating value. Fairness remedy (no formulation change):
the **carbon weights-only counterfactual** (S4's doubled carbon share at S0's targets, the lever the others get)
ran as the fifth E18 arm on 2026-09-08 — outcome next entry.

**R10.14 (cont.) CARBON WEIGHTS-ONLY ARM RAN 2026-09-08 (`runs/e18_s4x1_wonly_ssp585`; 21 solves, 22 verdict; PRE-REGISTERED
RULE → SUBSTITUTABLE).** Design as executed: S4's registered weight vector VERBATIM (m_soc 1.166, biomass 0.501, refugia 1.229 …)
with m_soc's target reset to S0's 0.332 — no re-derivation was needed because the registered influence share is target-
insensitive under the swing normalization (carbon share 0.499 vs S4's 0.500), so the arm is exactly "S4's share doubling at S0's
targets", the lever S1–S3 get. Anchor 54 s (objective 4.898 vs S4's 5.014), guarded MGA 66 min, 50/50 certificates in band,
D 0.927. Measured against S4: anchor carbon-block capture 0.440 → 0.370 (m_soc parks at 0.332 exactly, as in S0; biomass 0.329 →
0.409 under its doubled weight), refugia 0.418 → 0.434, anchor Jaccard 0.595; frequent tier 34,787 → **16,425 km²** (Jaccard
0.335), share inside the 12-position core 31% → **72%**; own land 20,329 → **763 km²** (S1–S3 own 0–861); tier enrichment
carbon 3.83 → 1.40, refugia 2.07 → **4.03**; max f 1.000. **Answer to the fairness question: given only the lever the other
three get, carbon-forward is refugia country like the rest — its 20,329 km² of Act-2 land is the TARGET's doing, not the
weight's.** Mechanism (members' m_soc capture): under S4 the members dip BELOW target (0.530–0.552 — they pay shortfall to
leave the tail, and the tail stays pinned); under the weights-only arm they never do (0.332–0.380): t = 0.332 is met by the
θ-tail (4.1% of the region) with a reservoir of nearly-as-dense cells outside the selection to swap in at zero shortfall,
whereas t = 0.552 has already consumed that reservoir, so every departure from the tail is charged. Binding scarcity (E13) is
therefore created by the target exhausting the substitutes. **Currency caveat:** the per-cell shortfall cost scores this arm
at 7.63× refugia — ABOVE S4's 4.59, because the same weight sits over a smaller t — yet it owns 763 km²: the cost is charged
only while the feature is below target, so the currency ranks lead magnitude CONDITIONAL on the target binding inside the
band. With S3 ×5 (8.68×, no tier) that makes two necessary conditions beyond the score: a steep tail AND a binding target
(exhausted substitutes). Statement for the paper and the deck (E18 slide, 20): "carbon-forward is the only scenario that also
states a security target (55% of dense soil carbon); with the same share doubling the other values get it would own ~760 km²,
not ~20,300 — the target, not the weight, buys carbon its own places." Registered scenarios unchanged (M4.22).

**R10.15 What raising S1–S3's emphasis would cost Act 1, and whether it answers "where do these themes have value"
(Ethan's question after R10.14, 2026-09-08; zero-solve on the E18 arms):** (a) Swapping an E18 arm in for its scenario's
SSP585 formulation and re-voting the 12-position core (245 twin unchanged — no 245 arms exist, so these are LOWER bounds on
the erosion): S2 ×2 (share 0.67 = 4× S0 weight) core 16,895 → 15,412 km² (Jaccard 0.904; −1,555 / +72); S2 ×5 → 13,730
(0.805); S3 ×2 → 15,970 (0.943; −943 for 0 km² of own land); S3 ×5 → 15,202 (0.891); S2 ×2 + S3 ×2 together → 14,512
(0.856). (b) Where the diffuse values actually sit: the richest decile of unprotected land holds only 18% (connectivity)
and 14% (biodiversity) of the block's unprotected value — 108,188 km² each — and 2–3% of that decile lies in the core. The
connectivity tier moves INTO that decile as the weight rises (share of tier inside it: S2 29% → ×2 87% → ×5 100%) but never
covers much of it (2.9% → 10.2% → 32.1%); the biodiversity tier does neither (20% → 43% of a 1,024 km² tier → empty).
Reading: for a diffuse value the frequency tier can only ever pin a sliver of where the value is; "where the theme has
value" is the value layer itself, and the applied statement is coverage (T-D3 / tier achievement), not a tier. Raising
S3's emphasis buys nothing at any dose and erodes the core; raising S2's buys pinch-point land at ≥ 4× S0 at the price of
~1.5–3 k km² of core (more once its 245 twin moves too). See `spec/e18_reportback.md` for the options put to chat.

**R10.16 Denominator ruling measured (13b, 2026-09-08; unguarded band, the paper's Claim-A estimand; zero-solve):**
F12 (12 design cells, PRIMARY) vs F14 (as frozen, supplement): per-cell |ΔF| over unprotected land mean 0.0056, max
**0.054** — inside the single-vote bound 1/14 = 0.071 for every cell (the analytic bound for two removed votes is 2/14 =
0.143; the measured maximum is well below both); 10 cells exceed 0.05. Bands (km² unprotected, F14 → F12): always 0 → 0;
frequent 6,816 → **6,306** (Jaccard 0.925); conditional 93,408 → 89,786; rare 951,972 → 968,313; never 29,689 → 17,480
(the crossed hybrids, both SSP585, had pushed 12 k km² of never-selected land below 0.05 — dropping them lifts it into
rare). E1 bias (hierarchical − naive): 14-cell mean 0.169 / max 0.755 → 12-design **0.173 / 0.765** (Claim A unchanged).
**E11 recount: 156/182 → 109/132 ordered pairs mutually in-band**; of the 26 out-of-band pairs in the 14-cell record,
**3 involved a diagnostic cell — all as the PLAN (s3x under both S4 objectives, s1x under S4@245), none as the objective**;
the 23 remaining failures are unchanged and all carbon-forward objectives (Δ 0.051–0.093) plus the two S4-plan-under-S1
cases. Between-anchor Jaccard on the 12: min 0.373 / mean 0.519 / max 0.777. Products: `runs/ensemble_v1/
F_surface_design12.tif`, `spec/T_denominator_v015.csv`, `spec/E11_recount_v015.json`, `figures/gate4_F_design12_vs_14.png`.
The guarded package surfaces (19) were already F12 (R10.9); nothing there moves.

**R10.17 Value vs irreplaceability (package spec v1.6 Acts 1/4 + hinge; 19 headless verification run 2026-09-08 on the
production artifacts — PROVISIONAL until Ethan's run; zero-solve):** (1) **Value footprints** = the top 30% of unprotected
land by block score, 324,566 km² each for core habitat / connectivity / biodiversity / carbon / intactness (exact quantile
cut; M4.25); representativeness (presence of any ≤1%-footprint EFG class) 32,108 km² = 3.0% (the 36-class alternative would be
834,226 km² = 77%, reported not used). (2) **Coverage by reliability tier** (% of each theme's footprint in core / scenario
tiers / opportunity): core habitat 5.1 / 10.3 / 84.6; connectivity 0.7 / 4.6 / 94.6; biodiversity 2.9 / 5.1 / 92.1; carbon
2.0 / 9.3 / 88.7; intactness 1.5 / 4.9 / 93.6; representativeness 4.3 / 12.5 / 83.2; never ≈ 0 for all. Share of each
block's REGIONAL value by tier (PAs / core / scenario / opportunity): biodiversity 0.156 / 0.015 / 0.039 / 0.790; carbon
0.149 / 0.014 / 0.111 / 0.726; connectivity 0.146 / 0.012 / 0.043 / 0.798; core habitat 0.192 / 0.057 / 0.076 / 0.675 —
the core holds 1–6% of any theme's value; irreplaceability is a sliver of value by construction of a plateau-rich problem.
(3) **Convergence** (themes voting a cell top-30%, km² unprotected): 0: 195,628; 1: 495,036; 2: 339,403; 3: 50,666; 4:
1,152; 5: 0. High-value land (≥1 theme) 886,257 km² = 82% of unprotected land; **the gap (Act 4) = 815,442 km² = 92% of
high-value land lies outside the core and every scenario tier**, and 99.9% of it is in ≥1 near-optimal plan (R10.3 union
membership). (4) **Hinge cross-tab** (km²; rows = convergence, cols = core / scenario / opportunity): 0: 0 / 66 / 194,818;
1: 1,691 / 15,653 / 477,661; 2: 11,493 / 31,684 / 296,226; 3: 3,440 / 6,316 / 40,910; 4: 271 / 267 / 614. Corners: high value
(≥3 themes) in the core 3,711 km² (the easy sell); high value in opportunity 41,524 km² (Act 4's territory); LOW value (≤1
theme) in the core **1,691 km²** = 10% of the core — the E13 surprise, binding claims in unglamorous places (the core is
mostly 2-theme land: 11,493 of 16,895 km²). (5) **Biodiversity, the finding as the product:** AOH-richness block capture over
ALL 612 guarded near-optimal plans (12 × 51) = **29.5–34.2% (median 31.4%)** — the slide states this measured range rather
than the anchor-only "34–36%". Products: `geotiffs/value_top30_*.tif`, `value_convergence.tif`, `value_gap.tif`,
`tables/T-D6_value_coverage.csv`, `T-D6b_value_share_by_tier.csv`, `hinge_crosstab.csv`; figures `act1_values_hex250`,
`act1_value_convergence_hex250`, `act3_<sid>_hex250` (value | tier pairings), `hinge_convergence_x_F`, `act4_opportunity`,
`td6_value_coverage`; deck 22 slides (v1.6 skeleton + by-future pairs + summary map + E18 appendix).

**R10.19 The curated representativeness block (v3) — block card measured (`11b_efg_curation_freeze_v3`, 2026-09-09; zero-solve;
M2.11, M4.26–M4.27).** Curation 40 → 22 classes → **20 features** on the parent extent (Alberta mirror 27 → 15 → 13).
Re-derived facts on the 20: **rare-attainable 17/20** (was 36/40; the three that cannot be captured in full within the
budget are T2.1 cap_max 0.41, T6.4 0.60, F2.4 0.84); **≤1%-footprint companion 6 features** (F1.1, T5.4, T6.1, F2.1, F1.6,
T2.2; was 13); **classes > 90% south of 53°N: 9/20** (was 20/40; median feature mean-latitude 52.6°N) — the southern skew
that drove E17's EFG-out attribution was half artifact. Rarity-scaled targets (M4.27): 0.10 for the four largest classes
up to 0.94 for F1.1. **R0 (iii) boundary-proximity check:** of the six retained classes below 1% of the extent, FIVE have
more than half their cells within 10 km of the study boundary — F1.1 79%, T5.4 100%, T6.1 93%, F2.1 72%, F1.6 87%
(T2.2 47%) — i.e. the "honest rare-ecosystem presence" set is, on this extent, mostly range edges of classes centred
outside it. Reported, not dropped (v0.17.1 leaves this to the spec chat); under the log-linear targets they will pin at
F ≈ 1 by rarity and will be captioned as adequacy pins (M4.28). Manifest v3 frozen: sha e47991bc…, EFG block sha
4dc60559…, weights identical to v1 (asserted). Products: `spec/v3/efg_curation_v3.csv`, `efg_block_card_v3.csv`,
`efg_targets.json`; `input_data/aligned_stack{,_ab}/iucn_efg_v3/`.

**R10.19 (cont.) The clip-edge resolution measured — manifest v3.1 (11b, last cell; 2026-09-09; zero-solve; M4.29).**
Windows (study extent 1,551,653 km² = boundary + 20 km, buffered further): +100 km 2,435,283 km²; **+250 km 3,813,704
km²**; +500 km 6,373,984 km². Class footprints counted on the GET archive maps (30-arc-second, presence = value > 0,
nearest warp to the 1 km Albers grid); note the on-extent counts here are polygon counts, larger than the PU counts in
the block card because the PU mask (biomass coverage) trims ~18% of the extent — most of T5.4, T6.1 and F1.6 lies in
that trimmed fringe (deserts, ice, arid basins). **The flagged classes are range edges, as diagnosed:** share of the
+250 km footprint that lies inside the extent — T5.4 9.5%, F1.6 10.9%, T2.2 11.1%, T4.4 18.6%, F1.1 19.8%, T6.1 21.0%,
F2.1 39.0%; the large classes 36–67%. **Targets v3 → v3.1 (+250 km):** F1.1 0.94 → **0.50**, F2.1 0.71 → **0.49**, T6.1
0.84 → 0.36, F1.2 0.49 → 0.25, T2.2 0.60 → 0.15, T3.4 0.18 → 0.11, T5.4 0.87 → **0.105**, F1.6 0.66 → **0.101**; every other
feature (T4.4, SF1.2, T6.2, T6.3, S1.1_SF1.1, T5.1, F1.3, TF1.2, TF1.6_TF1.7, T6.4, F2.4, T2.1) at the 0.10 floor — the
block is now adequacy-semantic for two genuinely regionally rare classes and proportional for the rest. Sensitivity:
+100 km lifts the small classes (F1.1 0.63, F2.1 0.57, T6.1 0.47, T2.2 0.30, T5.4 0.26, F1.6 0.27); +500 km lowers them
(F1.1 0.29, F2.1 0.46, T6.1 0.23; the rest 0.10). **Rare in the window (≤ 1% of it): F1.1 and F2.1 at +100 and +250 km;
F2.1 alone at +500 km** — the Act 1 representativeness layer therefore votes on two classes (streams, large lakes),
"expected thin — the honest representativeness story" (package spec v1.7). Manifest v3.1 frozen (sha 259f35ed…;
weights unchanged; supersedes v3 e47991bc…, never solved). Products: `spec/v3.1/efg_window_footprints.csv`,
`efg_targets.json`, `manifest_v3.1.csv` + sha.

**R10.20 The v3.1 ensemble solved (12 under manifest v3.1; run by Ethan 2026-09-09/10; integrity from 12's closing cell +
the certificates):** 12/12 design formulations complete — anchor, 50 MGA members (g = 5%), LP twin, meta — in **4.0 h wall**
(MGA 7.2 h of solver time across formulations is the certificates' sum; anchors 55 min, twins 7 min); far under the ~10–12 h
projection because the machine was uncontended (members 12–15 s each). Every twin ≤ its anchor (LP ≤ MILP OK, 12/12);
anchor gaps 6e-6 – 2e-5; **certificates: 600/600 members in band, 0 time-limited, 4 duplicates (2 in each S5)**; every
member sits at exactly +5.0% of z* at most. Anchor objectives (SSP585 / SSP245): S0 4.9025 / 4.8655, S1 4.7034 / 4.6195,
S2 5.0657 / 5.0560, S3 5.0934 / 5.0672, S4 4.5241 / 4.4866, S5 11.1315 / 11.1055 — lower than the v1 record throughout
(e.g. S0 v1 5.3628 at Gate 2b) because twelve of twenty EFG targets sit at 0.10 under the window-derived rule and the
block no longer pays shortfall on the artifact classes. Anchor solve times 49–693 s (S2, the connectivity scenarios,
slowest as before). k-best pools not re-solved (M4.26). Next: 13 → 15 → 18 (or the one-command runner, which skips 12).

**R10.20 (cont.) The unguarded frequency surface on the curated block (13 + 15 under v3.1, Ethan's run 2026-09-10;
zero-solve comparison against the v1 record on the same 12 design formulations):** **the unguarded frequent tier all but
vanishes — F ≥ 0.70: 6,306 km² (v1, F12) → 4 km²; F ≥ 0.50: 15,097 → 2,051; F ≥ 0.30: 96,092 → 61,871; never (< 0.05)
17,480 → 829** (bands: conditional 61,867, rare 1,019,185). Max F 0.784; corr(F_v1, F_v3.1) 0.723 over unprotected land;
mean F identical by construction (0.1764). Where the v1 tier went: its 6,306 km² now average F 0.25 (median 0.21; 613 km²
still ≥ 0.50) — and **99% of the v1 unguarded frequent tier sat on a ≤ 1%-footprint class (artifact or retained-small)**:
the shared frequent land across all twelve positions was rarity-pinned EFG land, exactly as R10.18 diagnosed ("the
classes cheapest to hold"). The retained small classes no longer pin: F1.1's unlocked cells fall from mean F 0.84 to 0.41
(0% ≥ 0.70) under its 0.50 target; F2.1 0.36 → 0.33. Per formulation (f ≥ 0.70, v1 → v3.1): S0 11,247 → 650 / 13,513 →
1,844 (585/245); S2 4,748 → 29 / 6,107 → 63; S3 8,186 → 0 / 9,830 → 21; **S1 27,843 → 23,106 / 39,161 → 34,491 and S4
28,748 → 20,351 / 30,818 → 22,135 keep most of theirs** — the two concentrated claims (dense refugia, the carbon target)
pin on their own; the diffuse scenarios and the balanced position had been pinned by the block. S5 stays empty. E-round
statistics on v3.1: within-formulation degeneracy share 0.961 (v1 0.952; scenario 0.034, climate 0.002); E1 bias mean
0.179 / max 0.81 (v1 0.173 / 0.77); D_s 0.836–1.000; E11 107/132 pairs mutually in-band (v1 twelve: 109/132; largest
conflict S4@245 at Δ 0.106); the E14 trigger FIRES again (members sacrifice whole blocks inside the 5% band); E17-T2
southern statistic 9/20 (was 20/40); E13 overlap on the 4-cell core is moot. **Reading for the paper:** the aggregate
5% band's "always/frequent" core was a representativeness artifact on the 40-class block; on the curated block the
Claim-A estimand says almost no cell is required by every value position within 5% of optimal — the pluralism result
sharpens, and the applied core now rests entirely on the guarded (per-block-floor) semantics, measured by 18 (running).

**R10.21 (placeholder) The necessity test (E19) — PENDING 18b/18c.** To record: the per-class forced ledger, forced land
(≥ 1 / all formulations), the ensemble-forced share of the core vs the 50% gate, T2 necessary-vs-forced agreement and the
leave-EFG-out latitude shift, T3 outcome if triggered, the adequacy-pin count in the register.

**R10.22 (placeholder) Package v1.7 on the curated block — PENDING 19/20.** To record: core/tier/gap areas vs the
artifact-block package (R10.17), the Act 1 representativeness layer on the retained ≤1% classes, cluster picks that
changed, the E19 partition of core/tiers/picks.

## Figure/table candidates (running)

- F8 marginal-density trajectories (θ crossings + area labels) — rendered, final stack.
- Feature cards ×10 — rendered (review artifacts / supplement).
- T2 characterization table — frozen CSV.
- Gate-0 capture-vs-target + reallocation table — from R2.1/R2.4.
- LP-vs-MILP tightness table — R2.5.
- Numerics vignette box/figure — R3.1–R3.3 (matrix-range before/after; 60× speedup).

**R10.18 Cross-reference from the Alberta mirror (2026-09-08; AB results_log R7.9–R7.11): the EFG block rewards
cartographic slivers of the GET indicative maps.** The largest Alberta core cluster (412 km², 53.4°N) is 99% the footprint of
GET **F2.10 "Subglacial lakes"** — 409 "major-occurrence" cells (= a POINT RECORD; the GET's sources are Antarctic/Greenland/
Iceland inventories) in ice-free Lower Foothills, the class's ENTIRE footprint on the Y2Y extent (0% in PAs); **the Y2Y-wide F
pins the same polygon (F 0.89 / guarded 0.86, 100% ≥ 0.70)**, so the parent core carries it too. Mechanism: each EFG holds 1/n
of the block regardless of extent and capture is scored against the class's own total, so per-cell class value ∝ 1/footprint
(E13's binding scarcity) — and the GET's own README says its maps (10 arcmin–1° grain; 9 of AB's 27 and a comparable share of
the 40 Y2Y classes are ecoregion ENVELOPES) are for "which EFG are likely to occur within areas, rather than which occur at
particular point locations". On the Alberta extent three of the four pinning classes are natural-or-plausible classes whose
mapped footprint is a border-overshoot or Y2Y-line sliver (F3.5 canals median 0.5 km from the BC border; F2.9 0.7 km; SF2.2
4 km from the Y2Y line) — see R7.11 for the measurements. On the Y2Y extent F2.9 (40% of PU) and F3.5 (19%) are too large to
pin; the parent's exposure is F2.10 (0.03%) plus any small-footprint envelope class (SF2.2 0.42%, T2.2 0.90%, T7.4 1.19% are
the candidates). Earlier reading ("restrict the block to natural biomes") SUPERSEDED: the anthropogenic-biome question is a
separate purpose decision and drove none of the picks. **Decision flagged for the parent (spec amendment, candidate rule =
exclude point-record classes and envelope-method classes with footprint < 1% of the PU): would re-derive the EFG foundation
(36/40 rare-attainable), E17-T3's EFG-out counterfactual and the director package's core clusters** — check which Y2Y core
picks sit on these classes before the director deck ships.
**R10.18 (cont.) Measured parent exposure (zero-solve on `director_package/`, 12 design formulations, guarded F,
core = F ≥ 0.70 discretionary = 16,895 km²):** the five smallest classes — F2.6 (3 cells), F2.2 (9), F1.4 (93), F2.3
(222), F2.10 (409) — are **100% of unlocked cells inside the core** (734 km²); core cells inside any ≤ 1%-footprint
class = 1,377 (8.2%); register clusters ≥ 50% inside a ≤ 1% class = 12 of 99 (3,983 of 108,853 km²): the F2.10 polygon
(412 km², register cluster "NE of Jasper 53.4°N", not a numbered pick) + a Wyoming group (Bridger / Gros Ventre /
Jedediah Smith on the SF2.2 flooded-mines, F3.4 aquafarms and F1.6 episodic-rivers envelopes) + T5.4 cool deserts.
**Deck pick #11 (Act 3 biodiversity-forward, "NW of Bridger Wilderness", 348 km²) is 100% inside ≤ 1% classes (SF2.2
85% / F3.4 100% / F1.6 100%); pick #12 (234 km²) is 99% T5.4** (real but scarce); picks #1–#10, #13, #14 are 0–4.2%.
The v1.6 Act 1 `value_top30_representativeness` layer (32,108 cells) is **27.9% F2.10 + SF2.2 + F3.4** (2.3% on the
< 0.1% slivers); 4,324 of 51,818 `value_convergence ≥ 3` cells reach 3 only through representativeness. Tier composition: Act 2 core 7.5% / core-habitat 6.7% / connectivity 9.1% / carbon 8.8% inside ≤ 1% classes, but the
**biodiversity-forward tier 40.6% (16.5% on F2.10 + SF2.2 + F3.4 alone)** — what S3 "owns" is largely the EFG block completing
map slivers (cf. R10.13: AOH richness never pins). Anthropogenic
count corrected to **12/40** (S2.1 anthropogenic subterranean voids included). Full class tables, option verdicts
(A map-method rule / B sliver floor / C purpose rule / D presentation-only) and costs → `spec/efg_block_reportback.md`.

*Last updated 2026-09-03 (R10 placeholders; R9.7 E15b).*
