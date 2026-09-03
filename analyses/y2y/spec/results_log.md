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

## Figure/table candidates (running)

- F8 marginal-density trajectories (θ crossings + area labels) — rendered, final stack.
- Feature cards ×10 — rendered (review artifacts / supplement).
- T2 characterization table — frozen CSV.
- Gate-0 capture-vs-target + reallocation table — from R2.1/R2.4.
- LP-vs-MILP tightness table — R2.5.
- Numerics vignette box/figure — R3.1–R3.3 (matrix-range before/after; 60× speedup).

*Last updated 2026-08-27.*
