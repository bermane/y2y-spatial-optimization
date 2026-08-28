# Hierarchical Selection-Frequency Ensemble — Study Plan (Paper 1)

**Status:** v0.10 — Gates 0a/0/1 stand; Gate 2 executed, pre-registered verdict fired NEAR-BINARY but the instrument (k-best pool) was structurally unable to sample the g-band (M6.6). D-A resolved: estimator replaced with diversity-controlled (MGA) generation; estimand re-registered (§4). D-B resolved: S0 keeps AMOUNT semantics (formulation untouched — certified optimum and T1 stand); carbon-forward carries PLACES semantics via θ-tail-masked features. Next: masked-layer re-audit → new verdict rule pre-registration → Gate 2b (MGA on reference cell).
**Scope:** Single methods-forward paper. Value scenarios over PROACT-selected objectives aligned to Y2Y core mission (PROACT selected objectives; no weights/ranges were elicited). Robustness of prioritization claims + named forward scenarios (core-habitat-, connectivity-, biodiversity-, carbon-forward).
**Companion documents:** leverage/carbon-dominance analysis; novelty verification report (§12); gate0_reportback.md; gate2_reportback.md (R6, M4.10/M5.7/M6.6/M6.7).

## Changelog
- v0.10 — Gate 2 ratified and pivoted. (1) D-A(a): within-cell estimator = Brunel-style diversity-controlled generation (max Hamming distance from incumbents s.t. objective ≤ (1+g)·certified optimum, direct Gurobi calls via the compiled-model machinery). Estimand RE-REGISTERED: f_{i,s} = membership fraction across k maximally-diverse g-optimal solutions — interval logic (which cells survive every corner of the band), deliberately not volume-weighted sampling (uniform vertex sampling intractable; volume weighting is plateau geometry, not decision relevance). g retained as a certified hard wall and lens parameter; E4's g-grid {2,5,10%} becomes the central f(g) robustness curve (core erosion with tolerance). New degeneracy-verdict rule to be pre-registered BEFORE Gate 2b on MGA-appropriate statistics (achieved Hamming diameter vs discretionary size; f=1 core share — NOT conditional-cell %, which MGA inflates by construction); Claude Code proposes thresholds. k-best pool retained one-per-cell in the ensemble: per-formulation optimum-uniqueness statement + the k-best-vs-MGA contrast discharges E5 as a by-product. M6.6 promoted to results inventory (PoolGap acts as bound never sampling target; the estimator demonstrated E5's enumeration-order bias on itself). (2) D-B: amount-vs-places became a SCENARIO AXIS. S0 = amount (unchanged; Gate-2 artifacts stand as the measured record). Carbon-forward = amount dial (θ 5×→3×, m_soc t=0.552) PLUS places locks: two θ-masked tail features (m_soc ≥5×-mean; biomass ≥5×-mean) in EVERY cell's stack at t=0 (mathematically absent) and activated only in carbon-forward at adequacy-style t=1.0 (0.95 fallback pre-authorized), mirroring EFG treatment; masked layers re-audited under frozen §2.5 rules first (expected rare-attainable), disclosed as motivated by M6.7. M6.7 promoted to results inventory and reframed: "a total-capture target secures an amount, not places" is the empirical motivation for the places scenario; S0 tail expectation stays honestly-failed (~0.43), S4 expectation ≈1.0 by construction. (3) CORRECTION: v0.9.1's "weight sets depth, not order" rationale REFUTED by M6.7 (joint scoring lets competition invert within-feature hotspot preference; biomass tail 0.425 at w=0.199, m_soc tail 0.435 with target binding) — removed; within-block mass-proportional split stands on the S0 amount decision, not the refuted argument. (4) Rulings: m_soc +0.089 realized-influence miss ACCEPTED as structural (satiating member realizes 100% of claim; diffuse members ~40–50% of capacity under competition — Claim C's caveat, now measured; iterate-once NOT invoked: re-deriving against realized swing chases a competition equilibrium and destroys intended-influence interpretability). Ensemble LP twins run on Gurobi's LP path; HiGHS re-verification as 2-cell spot-check (open-verification = verifiable without Gurobi, not produced without it; 109-min HiGHS twin recorded as worst presolve pathology). (5) Costing: bundled rebuild = estimator swap + S4-only re-freeze (S0 untouched); ensemble ≈ 14 × (anchor 55 s + MGA k=50 ≈ 50 min + one k-best pool), serial on WLS.
- v0.9.1 — Carbon within-block split made diagnostic-driven; θ-tail capture rate adopted as standing T1/E7 diagnostic. [Rationale text corrected in v0.10.]
- v0.9 — Gate 0a/0 ratified: audit frozen; numerics standards (§2.6); block accounting (D1); S4=θ3× (D2); E5 HiGHS arm dropped (D4); SSP axis; two-regime swing; corrected pass criterion; degeneracy prior→unknown.
- v0.8 — Universal transform screening; feature cards; E9 log-carbon arm.
- v0.7 — D3(b); multi-budget deferred; E6 INACTIVE; licensing sequencing.
- v0.6 — EFGs locked foundation; doubling-only tilts.
- v0.5 — PROACT blocks confirmed; S1=core-habitat-forward.
- v0.4 — No elicited weights; S0 analyst-constructed; frequency surface is the deliverable.
- v0.3 — R2 tail-mass criterion; constants frozen (θ=5×, λ=0.10, a_min=0.5%, t_min=0.15).
- v0.2 — §2.5 protocol; (w,t)-pair scenarios; E8–E10.
- v0.1 — Initial plan.

---

## 1. Purpose and contribution claims

Two-level hierarchical selection-frequency estimand for exact-solver conservation planning, published with an expressivity audit distinguishing genuine value-robustness from structural inability to express values — demonstrated on the Y2Y prioritization.

**Claim A (estimand, re-registered v0.10).** Per planning unit i: F_i = (1/|S|) Σ_s f_{i,s}, where f_{i,s} = i's membership fraction across k_s maximally-diverse solutions certified within formulation s's g-band (objective ≤ (1+g)·optimum). One vote per formulation; the vote is fractional. The within-cell object is interval-logical — membership breadth across the band's extremes — chosen over volume-weighted sampling deliberately (uniform vertex sampling intractable; plateau volume is geometry, not decision relevance). g is a certified hard wall and the lens parameter; the f(g) curve (E4) is the central robustness product: which cells survive every plan within 2% / 5% / 10% of optimal.

**Claim B (expressivity audit).** A frequency surface is interpretable only alongside per-feature influence decomposition and saturation status per cell. "Robust to values" and "structurally unable to express values" are observationally identical in F_i and mean opposite things. Now includes the amount-vs-places finding (M6.7): total-capture targets are silent about WHERE — a semantic dimension of target-based planning the audit surfaced and the scenario axis now expresses.

**Claim C (influence-space scenarios).** Scenarios as target influence profiles translated via the two-regime swing w·(min(cap_max,t)−cap_min)/t (linear-arm special case: w=influence/leverage). First-order caveat MEASURED at Gate 2: satiating member realizes 100% of claim, diffuse members ~40–50% of capacity under competition (m_soc realized 0.275 vs intended 0.186). Intended and realized reported side by side in T1; no iteration against realized swing (ruling, v0.10).

Applied payoff (Discussion): frequency surface feeds post-hoc corridor/compactness delineation. Out of scope (§14).

## 2. Constraints and measured facts

1. Influence follows the two-regime swing under all linear objective families; levers are weights, targets, feature definitions.
2. **Dominance (a0 control):** m_soc 54.2% capture (1.8× area share) with no carbon treatment — hygiene fixes (penalty removal, 1/v) made it WORSE than iter6's 45.5%. Motivation: hygiene does not substitute for influence accounting.
3. **Lever-selection principle (a4):** attainable target = claim magnitude; weight = priority below target. a4 reproduces a0 exactly (0/1.27M cells).
4. **Targets bind at the kink to four decimals** (a1 0.3320; a2 0.3000; a3 0.4000). Pass criterion: only BELOW target fails; co-capture overshoot expected.
5. **Amount ≠ places (M6.7, Gate 2):** m_soc target binds exactly yet its ≥5× tail captures only 0.435; biomass tail 0.425 at w=0.199 (was 1.000 at w=1). A total-capture target secures an amount, not places; only a constraint or feature defined on the places secures places. (Supersedes the refuted "weight sets depth, not order" claim — joint scoring lets competition invert within-feature hotspot preference.) Context: connectivity tail 0.980, refugia 1.000.
6. **Optimum uniqueness (M6.6, Gate 2):** S0's certified optimum is essentially unique — 50 k-best solutions within 3.2e-6 relative, pairwise Jaccard 0.9999, conditional cells 0.09%. PoolSearchMode=2's PoolGap acts as a bound, never a sampling target: the g-band was NEVER SAMPLED by k-best. Band diversity is unmeasured until Gate 2b. Both findings are paper material.
7. **Saturation is capacity, not outcome** (36/40 EFGs CAN saturate; which DO is per-cell; E7 verifies).
8. **Intactness R3-inexpressible** (0.042); published per D3(b) with mechanism and measured cost (0.074 vs 0.055; AOH–footprint +0.636/+0.607). Carried in the S0 objective at a nominal weight, influence disclosed in T1.
9. **w = t is retired** (Gate-0 diagnostic convention; S0 weights come from block accounting).
10. **Compute (measured):** certified single 55 s; k-best pool 1,799 s; HiGHS LP twin 6,516 s (worst presolve pathology — twins move to Gurobi LP path, HiGHS spot-check ×2 cells); MGA ≈ 55 s/solve ⇒ k=50 ≈ 50 min/cell. All portfolios Gurobi-gated; WLS 2 sessions ⇒ serial cells.
11. **S0 LP relaxation effectively exact:** 100.00% integral; LP-vs-MILP Jaccard 0.9957; max capture delta 0.0006.

## 2.5 Feature characterization protocol — EXECUTED; FROZEN (2026-08-26) + v0.10 masked-layer addendum

Constants: θ=5×, λ=0.10, a_min=0.5%, t_min=0.15 (frozen v0.3). Rules R1–R4 as amended v0.8.

| feature | leverage | θ-tail area | implied target | class → lever |
|---|---|---|---|---|
| carbon m_soc | 0.884 | 4.06% | 0.332 | concentrated-satiating → target |
| carbon biomass | 0.801 | 1.17% | 0.066 < t_min | diffuse-linear (REVERTED by rule) → weight |
| transboundary connectivity | 0.461 | 0.20% < a_min | — | diffuse-linear → weight (pinch-point spike, not a tail) |
| climate macrorefugia (1/v) | 0.422 | 0.47% (fails a_min, t_min) | — | diffuse-linear → weight |
| climate corridors | 0.263 | no crossing | — | diffuse-linear → weight |
| AOH birds / mammals | 0.232 / 0.181 | no crossing | — | diffuse-linear → weight |
| gHM intactness | 0.042 | — | — | R3 inexpressible (disclosed) |
| EFG block (40) | — | — | — | 36 rare-attainable + 4 unsaturated disclosed |

Transform screening: log1p flips m_soc to diffuse-linear (0.884→0.486; E9 screening evidence) and pushes AOH birds under the floor (0.232→0.059). Only the standing 1/v orientation adopted. Cards: 10 pages, archived.

**Masked-layer addendum (v0.10, pre-Gate-2b):** two derived features — m_soc_tail (cells ≥5× regional mean m_soc density) and biomass_tail (≥5× biomass) — re-audited under the UNCHANGED frozen rules; expected class rare-attainable (4.06% / 1.17% of region, securable in full → adequacy-style lock, no scenario tilt). Disclosed as a post-execution addition motivated by M6.7. Present in every cell's stack; t=0 (mathematically absent — zero possible shortfall) outside carbon-forward cells.

## 2.6 Numerics and solver standards (ratified v0.9; extended v0.10)

1. False-certificate vignette (supplementary): Gurobi certified a wrong optimum twice, bit-identically (root LP mis-converged 0.42% high; matrix range [1e-11,1e5] from resampling dust). Caught by the integral LP twin.
2. Dust thresholding: <1e-9 of feature total → 0 (biomass 46,097 cells / 0.0015% mass; m_soc 19,262; connectivity 538). Range now [1e-4,1e5]. Audit invariant. Per-feature drop disclosure.
3. Standards: opt_gap 1e-4 (single solves); NumericFocus 2 (also 60× faster on a4); **LP twin beside every certified MILP** — v0.10: twins PRODUCED on Gurobi's LP path for the ensemble, HiGHS re-verification on 2 cells as spot-check; open-verification claim = twins verifiable without Gurobi, not produced without it.
4. Provenance: per-solution solver record (objective/status/gap/runtime) in run_summary; engine-vs-recomputation reconciliation ≤3e-5 abs. Shims disclosed (Gurobi-13 `xn`→`poolnx`; portfolio list-return).
5. MGA machinery (v0.10): compiled-model extraction adds the band constraint row (objective ≤ (1+g)·certified optimum) and swaps the objective to max Hamming distance from incumbents (discretionary cells); every member carries a per-solution band certificate.

## 3. Formulation space

### 3.1 Value scenarios (block-budgeted; amount-vs-places axis added v0.10)

Every scenario = complete (w, t) pair over ONE feature stack (incl. masked tail features at t=0 unless activated). Levers follow frozen classes.

**S0 — Balanced (AMOUNT semantics by decision, v0.10; formulation unchanged from Gate 2).** Equal discretionary influence per block via joint block accounting in two-regime swing currency; carbon block splits mass-proportional 74.2/25.8 (stands on the S0 amount decision). Frozen weights (scenarios_v1.json): refugia 1.460 / conn 0.669 / corridors 1.171 / m_soc 0.465 @ t=0.332 / biomass 0.199 / birds 1.329 / mammals 1.708; intactness nominal, disclosed. Measured (certified single): captures refugia 45.2 / conn 33.4 / corridors 26.0 / m_soc 33.2 (AT target) / biomass 31.0 (in the 30–37 pre-stated band — "co-benefit, not driver" achieved) / birds 33.0 / mammals 32.7 / intactness 29.9. θ-tail capture: m_soc 0.435, biomass 0.425 — the pre-stated biomass expectation FAILED and is REPORTED (v0.9.1 commitment): the honest signature of amount semantics. The +8.4-pt w=t biomass leak remains the motivation for block accounting.

| ID | Scenario | Lever(s) | Definition |
|---|---|---|---|
| S0 | Balanced | (w, t) as frozen | Amount semantics; tails ride co-capture only; tail features t=0 |
| S1 | Core-habitat-forward | Weights | Core habitat block share doubled; others scaled down |
| S2 | Connectivity-forward | Weights | Connectivity block share doubled. Carroll static-layer disclosure |
| S3 | Biodiversity-forward | Weights | Biodiversity block share doubled; mandatory gHM audit |
| S4 | Carbon-forward (PLACES + amount, v0.10) | Target + tail locks + weight | Amount dial: θ 5×→3× ⇒ m_soc t=0.552. Places locks: m_soc_tail AND biomass_tail activated at t=1.0 (0.95 fallback pre-authorized), adequacy-style like EFGs. Biomass weight re-derived under doubled block share. E7 expectation: tail capture ≈1.0 by construction (vs S0's ~0.43). T1 reports REALIZED block-influence ratio (doubling approximate for S4, exact for S1–S3). a0 (54.2%) cited as the unconstrained bracket. Paper sentence: the balanced position secures a third of the carbon; carbon-forward secures the carbon strongholds and more than half the stock — the same diagnostic measures both |
| S5 | Intactness-forward | R3-inexpressible per D3(b) | Published as expressivity finding; footprint-as-cost = future work |
| S1.5/S2.5 (optional) | Midpoints | Weights | Only if corners diverge cliff-like |

Each scenario ships: intended profile; (w, t) pair; realized captures; realized influence (two-regime swing; intended-vs-realized side by side, no iteration); per-cell saturation outcomes (only below-target fails); **θ-tail capture per feature with scenario-specific pre-stated expectations**; gHM audit (mandatory S3).

### 3.2 Other axes

| Axis | Levels | Crossing |
|---|---|---|
| Climate (emissions) | SSP245 vs SSP585, both 2071–2100; macrorefugia 1/v per realization (no anchor parameter; leverage 0.422–0.516; top-30% Jaccard 0.574). Constant-influence-per-scenario: intended profiles held fixed across climate levels; weight vectors re-derived per cell from layer-specific swing | Full cross |
| Carbon regime | S0-level (θ=5×, amount) vs S4-level (θ=3× + tail locks, places) | S4 + crossed subset {S1,S3}×carbon-forward for E3 |
| Budget | 30% fixed | Multi-budget deferred |
| Gaps | opt_gap 1e-4 (certificate); pool/band gap g (estimand lens) | g fixed for main results; E4 varies g |

Disclosure: climate corridors static (Carroll 2018); the axis propagates climate uncertainty through macrorefugia only. Cell count: 14 (6 scenarios × 2 climate + 2 crossed). Cost ≈ 14 × (55 s anchor + ~50 min MGA + one k-best pool), serial.

## 4. Estimand and aggregation (RE-REGISTERED v0.10)

- Within-cell: generate k maximally-diverse members of the g-band by iterative max-Hamming MGA against the certified anchor; f_{i,s} = membership fraction. Semantics: breadth across the band's extremes (robust core = f=1; never-set = f=0; exchangeable middle), NOT volume-weighted probability. Per-solution band certificates recorded.
- Cross-cell: F_i = mean over cells, one vote per cell; never flat-pool. Fewer-than-k members: use what exists.
- g and k reported; claims phrased "within the g-band." **f(g) at g∈{2%,5%,10%} is the central robustness product** (core erosion with tolerance). k sufficiency = diameter and core-share stabilization on the reference cell.
- **Degeneracy verdict rule v2 (pre-register BEFORE Gate 2b):** statistics = achieved Hamming diameter / discretionary size AND f=1 core share (NOT conditional-cell % — MGA inflates it by construction). Claude Code proposes thresholds; frozen pre-run. Fail branch remains live: a certifiably narrow band ⇒ "the S0 map is essentially unique within g of optimal" — a strong measured negative; pivot to Claims B+C with the uniqueness result as the robustness statement.
- Bands (presentational): always ≥0.95 / frequent 0.70–0.95 / conditional 0.30–0.70 / rare 0.05–0.30 / never <0.05. Analyses use continuous F. Overlap coefficient between cells.

## 5. Expressivity audit (E7)

Per cell s, per feature f: two-regime swing influence, w_f, t_f, saturation OUTCOME, realized capture ratio, θ-tail capture rate (scenario-specific expectations: S0 biomass ~0.43 reported-as-failed; S4 tails ≈1.0 by construction). Products: live-feature map of the design; robust-vs-inexpressible figure (Claim B); amount-vs-places panel (M6.7 → S0/S4 contrast).

## 6. Experiments

| ID | Comparison | Supports | Status / criterion |
|---|---|---|---|
| E1 | Hierarchical F vs one-solve-per-cell | Claim A | Under the MGA estimand; effect-size prior unknown; Gate 2b decisive |
| E2 | Hierarchical vs flat pooling | Claim A semantics | Divergence where cells return unequal k |
| E3 | Variance decomposition: scenario / climate / carbon-regime / within-cell | Attribution | Includes the amount-vs-places regime as an axis level |
| E4 | f(g) at g∈{2,5,10%} × k-sufficiency | Central robustness curve | Core-erosion curves; diameter/core-share stabilization in k |
| E5 (DISCHARGED BY DESIGN v0.10) | k-best pool vs MGA, per cell | Enumeration-order bias | One k-best pool retained per cell; M6.6 is the maximal demonstration; contrast reported from ensemble by-products |
| E6 (INACTIVE) | Marxan | — | Deferred; time-boxed if activated |
| E7 | Expressivity audit | Claim B | §5 |
| E8 | Carbon-weight ×10 inertness at S0 + most-hostile cell | Lever principle | a4 proves it at Gate-0 scale; confirm under S0/S4 weights |
| E9 (screening in hand) | S0-protocol vs influence-weights-100% vs log-carbon-100% | Target lever justification | log1p class-flip = screening result; solves confirm per-hectare predictions |
| E10 (partially discharged) | θ∈{3,5,10×} | R4 defensibility | Targets are archive lookups; capture-shift solves remain |

## 7. Gates

**0a — COMPLETE** (audit frozen 2026-08-26; cards archived). **0 — COMPLETE, ALL PASS** (2026-08-27; binding to 4 decimals; a4 exact reproduction; freed-budget map incl. corridors −1.4 mis-prediction reported; LP tightness measured).
**1 — COMPLETE as frozen** (scenarios_v1.json; S0 solved and certified; T1 measured; tail diagnostic fired and reported).
**2 — EXECUTED; verdict superseded by instrument finding** (M6.6). Artifacts stand as the measured record (anchor optimum, pool-cost, uniqueness result, E4 seed).
**2a (NEW) — Rebuild:** masked-layer re-audit under frozen rules; scenarios_v2.json (S4 redefinition; tail features t=0 elsewhere; S0 UNCHANGED); MGA loop implementation on compiled models; verdict rule v2 proposed and FROZEN.
**2b (NEW) — MGA reference run:** S0 cell, k=50, g=5%, plus f(g) probes at 2%/10%. Decisive for E1/Claim A; fail branch live per §4.
**3 — Manifest freeze** (per §9; incl. verdict-rule v2, MGA parameters, twin-solver ruling).
**4 — Ensemble** (14 cells serial: anchor + MGA + one k-best pool each; Gurobi-path LP twins; HiGHS spot-check ×2) **+ E1–E4, E7–E10.**
**5 — Write-up.** BLOCKING: García-Quintas et al. 2025 full text; Lehtomäki & Moilanen 2013 skim; fresh sweep at submission. Results inventory now includes M6.6 (pool mechanism) and M6.7 (amount≠places).

## 8. Compute plan

Serial cells on Gurobi WLS (2 sessions). Per cell: anchor 55 s + MGA k=50 ≈ 50 min + k-best pool ≈ 30 min + Gurobi-path LP twin. Ensemble ≈ 1.5–2 h/cell ⇒ ~1–1.5 days wall. E4's extra g-levels on the reference cell only. HiGHS spot-check twins ×2 cells budgeted separately (~2 h each, worst case 109 min observed).

## 9. Manifest schema

Per cell: `cell_id`, `scenario_id`, `scenario_name`, `climate_level` (ssp245_2071_2100 | ssp585_2071_2100), `carbon_regime` (theta5_amount | theta3_places), `budget_pct`(=30), `weight_vector` (JSON), `target_vector` (JSON incl. tail features), `influence_profile_intended` (JSON, two-regime swing), `k_requested`, `band_gap_g`, `opt_gap`(=1e-4), `numeric_focus`(=2), `dust_rule_version`, `estimator`(=mga_maxham_v1), `verdict_rule`(=v2_frozen_hash), `solver`, `seed_policy`, `input_layer_hashes` (JSON), `created_utc`, `frozen`. Companion: `manifest_freeze.sha256`. Post-freeze changes ⇒ new manifest version + changelog.

## 10. Directory / file contract

```
project_root/
  spec/frequency_ensemble_study_plan.md
  spec/manifest.csv + manifest_freeze.sha256
  spec/scenarios_v2.json                      # v0.10 re-freeze (S4 + tail features; S0 unchanged)
  audit/feature_cards/                        # 10 pages + masked-layer addendum cards
  audit/audit_objects/                        # budget-independent npz (any-θ/any-B lookups)
  analyses/y2y/01..04 + gate2 notebooks       # executed record
  runs/<cell_id>/anchor/ mga/ kbest/ twin/    # per-cell artifact set (v0.10 layout)
  runs/gate2_s0_ref/                          # superseded-but-kept measured record
  analysis/e1_bias/ ... analysis/e10_theta/
  figures/
  changelog.md  results_log.md  methods_log.md
```

## 11. Figures and tables plan

F1 estimand schematic (two-level + band wall). F2 E1 bias map. F3 frequency surface + always-core. F4 attribution small-multiples. F5 expressivity figure (Claim B). **F6 f(g) core-erosion curves (E4 — central).** F7 k-best-vs-MGA contrast (E5 by-product; M6.6 panel). F8 marginal-density trajectories with θ crossings. **F9 amount-vs-places panel (S0 vs S4 tail capture; M6.7).** T1 scenarios (intended → (w,t) → realized captures + realized influence side-by-side + realized block ratios + tail rates). T2 frozen characterization (+masked addendum). T3 expressivity summary incl. mission-selected-vs-implementable gap. Suppl.: numerics vignette (false certificate, dust, LP-twin methodology, 60× result, HiGHS pathology), gHM audits, E8–E10, manifest, cards. Maps ESRI:102008; CVD-checked ramps.

## 12. Positioning and citations (verify DOIs before tracker entry)

Formulation lineage: Jung et al. 2021 NEE (10.1038/s41559-021-01528-7); foil — Jung's "equal" carbon weight = cardinality normalization, blind to spatial structure. Scenario-ensemble lineage: Buenafe et al. 2023 (10.1002/eap.2852); Brito-Morales et al. 2022; Chapman et al. 2025 (10.1038/s41559-025-02671-1); Liczner et al. 2023 (10.1111/csp2.12994); Carpenter-Kling et al. 2025. Aggregate-solutions-not-inputs: Meller et al. 2014. Univariate-characteristics anchor: Kujala, Moilanen & Gordon 2018 MEE (10.1111/2041-210X.12939) — post-hoc/solve-based; §2.5 inverts to ex-ante/zero-solve (leverage↔μ* ρ=0.922). Partial precedents: Rodrigues et al. 2004 (rarity-scaled targets); Moilanen 2007 / Arponen et al. 2005 (benefit-function shapes chosen a priori); Marxan Good Practices (QA). MGA lineage now load-bearing for the estimator: Brill 1979; Brill, Chang & Hopkins 1982; Brunel et al. 2023 (10.1007/s10666-022-09862-1) — cite as the direct method parent. Highest prior-art risk: García-Quintas et al. 2025 (10.1016/j.biocon.2025.111447) — Gate 5 blocking. Novelty sentence unchanged; add the amount-vs-places finding as a second, independent contribution sentence for the targets literature. Gate 5 skim: Lehtomäki & Moilanen 2013.

## 13. Decisions

All resolved or deferred. v0.10: **D-A(a)** MGA estimator + re-registered estimand + verdict rule v2 (thresholds proposed pre-run); k-best retained one-per-cell (E5 by-product). **D-B** amount-vs-places as scenario axis: S0 amount (unchanged), carbon-forward places+amount (tail locks t=1.0, 0.95 fallback); masked-layer re-audit under frozen rules. **Rulings:** no iterate-once on the m_soc realized-share miss (structural; documented); ensemble LP twins on Gurobi LP path with HiGHS spot-check ×2. Standing: D3(b); EFGs locked; doubling-only; constants frozen; mass-proportional carbon split (on the S0 amount decision). Deferred: multi-budget (audit objects make re-derivation lookups); Marxan E6.

## 14. Out of scope (fenced)

Post-hoc delineation (Discussion only). PROACT elicitation methodology. Eastern-slopes grizzly analysis. Budget stratification beyond the deferred note. Sobol'. Applied-paper full PROACT treatment.
