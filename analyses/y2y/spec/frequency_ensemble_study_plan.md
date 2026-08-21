# Hierarchical Selection-Frequency Ensemble — Study Plan (Paper 1)

**Status:** Draft v0.8 — All design decisions resolved or deferred. §2.5 amended pre-execution (transform screening universal; feature cards specified). Gate 0a ready to run; Gurobi-dependent gates queue behind the license. Ready for Claude Code handoff.
**Scope:** Single methods-forward paper. Value scenarios over PROACT-selected objectives aligned to Y2Y core mission (PROACT selected objectives; no weights/ranges were elicited). Demonstrates robustness of prioritization claims AND presents named forward scenarios (core-habitat-forward, connectivity-forward, biodiversity-forward, carbon-forward).
**Companion documents:** leverage/carbon-dominance analysis (source of §2 constraints); novelty verification report (source of §12 positioning).

## Changelog
- v0.8 — Pre-execution amendment to §2.5 (logged; Gate 0a not yet run): (1) transform screening extended to ALL features — candidate set {identity, log1p, sqrt, + flip/reciprocal where orientation applies}; adoption gated by R1's new value-model test, with the binding per-cell vs portfolio concavity distinction (concave transform = diminishing value per cell density; target = diminishing value at portfolio level — for carbon, per-cell linearity is physically mandated, so identity + target; AOH richness noted as the open alternative-value-model case, identity retained). (2) Feature cards specified: one 6-panel page per input (distribution / Lorenz / stopping-rule / transform-response / spatial thumbnail / rule-verdict box) + summary sheet, output at Gate 0a for review against frozen rules before Gate 0 solves; budget-independent panels archived per D2. (3) E9 expanded to three arms adding S0-log-carbon-at-100%, with pre-stated prediction that the log arm is worst on carbon-per-carbon-hectare — the measured answer to "why not log-transform." Directory contract updated (audit/).
- v0.7 — D3 resolved: option (b), intactness inexpressibility published as finding; footprint-as-cost named as future formulation change. D2 deferred: paper 1 at 30% only; 20/30/40/50% interest recorded for later (likely applied paper); Gate 0a must archive budget-independent audit objects for cheap re-derivation. D5 deferred: E6 marked INACTIVE with time-box conditions if activated. §8 licensing sequencing added: pre-license work starts now (Gate 0a, Gate 0 on HiGHS, scaffolding, analysis code against the npz contract); pool-dependent gates wait days for Gurobi rather than running shuffle interims. D-list is EMPTY of blocking items.
- v0.6 — D7 signed off: representativeness-forward scenario excluded; EFGs remain locked adequacy foundation with unsaturated-EFG disclosure in the audit. D1 resolved: tilt magnitude = doubling only. Scenario axis is final in structure: S0 + four forwards (core-habitat, connectivity, biodiversity, carbon) × 2 climate levels + crossed carbon subset.
- v0.5 — D4 resolved with the confirmed PROACT objectives hierarchy: quality of core habitat {macrorefugia}; connectivity {transboundary + climate corridors}; carbon {SOC + biomass}; biodiversity {AOH birds + mammals}; representativeness {EFGs}. S1 renamed core-habitat-forward (corridors reassigned to connectivity), cleanly separating climate *value* emphasis from the climate *uncertainty* axis; Carroll static-layer disclosure moves to S2. Representativeness treated as locked adequacy foundation (SCP doctrine + 36/40 rare-attainable), with new D7 requiring explicit sign-off on excluding a representativeness-forward scenario. Equal discretionary influence divided among the three weight-levered blocks.
- v0.4 — Blocker 2 resolved: PROACT elicited no weights or ranges (objectives selection only). S0 reframed from "PROACT-elicited position" to analyst-constructed **equal-influence-per-block** reference over PROACT-selected objectives; framing consequence added — with no endorsed weight vector, the frequency surface (not any single map) is the paper's deliverable. Scenario symmetry adopted: S0 = equal shares per block; S1–S4 = each block's absolute share doubled in turn. D6 dissolved; D4 restated as block-structure confirmation against the PROACT objectives hierarchy (last Gate-1 input). Elicited-vs-implementable gap renamed mission-selected-vs-implementable, retained in T3.
- v0.3 — R2 amended with tail-mass criterion: concentrated-satiating now requires BOTH θ-crossing over a_min AND implied target ≥ t_min. Closes the hole where biomass passed the v0.2 test (1.2% of region at ≥5×) despite a shallow, small tail — the biomass reversion is now derivable by rule, not decreed. Constants frozen: θ = 5×, λ = 0.10, a_min = 0.5%, t_min = 0.15, with insensitivity-margin disclosures (t_min classification stable across 0.07–0.33; λ stable across 0.05–0.15; θ generalized-from-carbon disclosed, E10 backstop). S4 sketch updated: biomass expected diffuse-linear — S4 = mineral-soil target tilt + biomass weight tilt. Gate 0a unblocked.
- v0.2 — (1) New §2.5 feature characterization protocol: univariate audit of ALL inputs + pre-registered rule-set R1–R4 assigning transform, valuation class, and value lever per feature; carbon's target treatment becomes a rule outcome, not an exception. New Gate 0a runs the audit before the comparison solves. Biomass explicitly provisional: if it lacks a concentrated tail under R2, it reverts to diffuse-linear (100% target, weight-levered) — protocol overrules the initial hand treatment, reported as such. (2) S0 anchored at the PROACT-elicited mission-balanced position; forward scenarios defined as tilts FROM S0, not from a synthetic center. Elicited-vs-implementable influence gap reported as an audit result. (3) Scenarios formalized as complete (weight vector, target vector) pairs; lever-selection principle stated (targets = claim magnitude for attainable-target features; weights = priority for unbounded-target features). (4) E-table additions: carbon-weight inertness demo at most-hostile cell; S0-at-100%-targets comparison cell (hotspot-dilution prediction); θ-sensitivity cells. (5) D-list revised: D1 restated for S0-relative tilts, D6 added (elicitation method / swing-weight compatibility), biomass reclassification recorded as resolved principle. θ=5× (sensitivity 3×/10×) and λ=0.10 adopted pending final confirmation.
- v0.1 — Initial plan. Integrates leverage findings: influence-space scenario specification, carbon-forward via targets not weights, expressivity audit as core element, compactness penalty removed (frequency surface feeds post-hoc delineation), Gate 0 = four pending comparison solves.

---

## 1. Purpose and contribution claims

The paper introduces and demonstrates, on the Y2Y prioritization, a two-level hierarchical selection-frequency estimand for exact-solver conservation planning, published together with an expressivity audit that distinguishes genuine value-robustness from structural inability to express values.

**Claim A (estimand).** Per planning unit i: F_i = (1/|S|) Σ_s f_{i,s}, where f_{i,s} is i's selection frequency within formulation s's near-optimal set (gap g), estimated from k_s pooled solutions. One vote per formulation; the vote is fractional. Novelty positioning per §12: no published study nests within-formulation near-optimal ILP frequency inside a cross-formulation ensemble with per-formulation averaging (verified "no evidence found"; García-Quintas et al. 2025 full text is the outstanding check).

**Claim B (expressivity audit).** A frequency surface is interpretable only alongside a per-feature influence decomposition (w_f × leverage_f, plus saturation status) for every formulation cell. "Robust to values" and "structurally unable to express values" are observationally identical in F_i and mean opposite things. No paper in the scenario-ensemble lineage (Jung 2021; Buenafe 2023; Chapman 2025) reports this.

**Claim C (influence-space scenarios).** Because influence = w × leverage, value scenarios are specified as target *influence profiles* and translated to weights via w_f = influence_f / leverage_f, rather than as raw weight multipliers. This makes "climate-forward" mean the same thing across features with different leverage. Caveat carried throughout: leverage is computed feature-wise and ignores competition; treat translation as first-order calibration and always report *realized* capture ratios per scenario.

Applied payoff (stated in Discussion, not a claim): the frequency surface is the input to post-hoc corridor/compactness delineation, replacing the removed boundary penalty. Delineation itself is out of scope (§14).

## 2. Constraints inherited from the leverage analysis (binding)

1. **Objective family is linear in captured fraction** (min_shortfall / max_utility / min_set all): influence ∝ w × leverage under all three. No objective swap fixes dominance; only weights, targets, and feature definitions are real levers.
2. **Carbon is retargeted, not down-weighted.** Initial rule: marginal density ≥ 5× regional mean — targets 0.332 (mineral soil), 0.066 (biomass). Consequence when saturated: weight multiplies zero; **carbon-forward scenarios act through the target axis**. v0.2: this treatment is re-derived through the §2.5 protocol rather than asserted — mineral soil is expected to classify concentrated-satiating; **biomass is provisional** (almost no exceptional tail, nothing at 10× mean) and reverts to diffuse-linear if R2 says so. Lever-selection principle: for a feature with an attainable target, the target sets the *magnitude* of its budget claim and the weight only its *priority* below target (no weight expands a claim past target — the objective is flat there); for features whose 100% targets exceed the budget's reach, weight is the magnitude dial across the whole feasible range. Saturation is an ex-post solve outcome verified per cell by E7, never assumed.
3. **Saturation set:** 36/40 EFGs saturate at 30% budget. Live features for weight scenarios: transboundary connectivity (leverage 0.461), climate macrorefugia (0.422, post 1/v fix), climate corridors (0.263), AOH birds (0.232), AOH mammals (0.181).
4. **Intactness is inert by low leverage (0.042)** — inexpressible via weights; see Open Decision D3.
5. **Orientation-flip artefacts fixed:** macrorefugia = 1/v (refugial residence time). Intactness left as 1 — gHM deliberately; measured cost documented (new selections mean gHM 0.074 vs 0.055 passed over; driven by AOH–footprint correlation +0.636/+0.607).
6. **Compactness penalty removed** (uncalibrated 1e-5 ranked 3rd of 12 drivers, relocated a third of selection, 400× solve cost). Unpenalized solutions already 66.6% clustered.
7. **Solve cost:** ~12 s per solve at 1 km, 1,272,914 PUs, penalty-free. Full ensembles at k=30–50 are hours, not days. Gurobi licensing is no longer on the critical path (shuffle-on-HiGHS fallback affordable).
8. **Degeneracy prediction:** saturation flattens the objective toward large optimal sets. This *predicts* substantial within-cell degeneracy — the exact condition under which the hierarchical estimand outperforms one-solve-per-scenario. E1 is therefore expected to show a real effect; if it doesn't, see Gate 2 fail branch.
9. **Pending validation:** the four comparison solves (control / ≥5× rule / flat 30% / flat 40%) have NOT run. Retargeting-reallocates-area is a structural prediction, not a measured result. This is Gate 0.

## 2.5 Feature characterization protocol (new in v0.2; runs at Gate 0a)

Purpose: replace reactive per-feature fixes with a prospective, uniformly applied, pre-registered protocol. Every one of the 12 inputs (8 continuous + EFG block) passes through the same univariate audit and rule-set; the current formulation is then *re-derived* from the protocol. Agreements validate the rules; disagreements (expected candidate: biomass) are findings and are **adopted**, not just reported.

**Audit battery (per feature, at B = 30%, before any solve):**
1. *Distributional profile* — quantiles, skewness, zero-inflation, Lorenz-style concentration curve (captured fraction vs area fraction, cells in descending density). Leverage is the two-point summary of this curve; the rules read the full curve.
2. *Marginal-density trajectory* — marginal density ÷ regional mean vs area accumulated; crossings at 10×/5×/3× give candidate targets and their area costs for every feature.
3. *Transformation response (extended v0.8)* — for **all features**, leverage and resulting classification under the candidate set {identity, log1p, sqrt; additive flip and reciprocal where the layer is cost-oriented/inverted}. Screening is universal; **adoption** is gated by R1's value-model test, never by leverage improvement.
4. *Attainability geometry* — exceptional tail securable in a small budget slice? capturable in full by rarity? or diffuse everywhere?

**Audit output — feature cards (v0.8):** one standardized page per input (12 cards + summary sheet), rendered at Gate 0a for review against the frozen rules BEFORE Gate 0 solves. Panels: **A** distribution (histogram/density, log-x if skewed; quantiles, mean, zero-inflation, skewness annotated); **B** concentration (Lorenz curve, cells descending; 30%-budget verticals marked so leverage reads as a visual gap, value annotated); **C** stopping rule (marginal density ÷ regional mean vs area accumulated, log-y; θ = 3×/5×/10× crossings marked with implied targets and area costs; t_min pass/fail line) — the per-feature form of F8; **D** transform response (leverage + classification under each candidate transform, R1 admissibility marked per transform); **E** spatial thumbnail (ESRI:102008, top decile highlighted — catches seams/artifacts univariate panels miss); **F** verdict box (frozen-rule outputs — transform, class, lever, target, predicted saturation — with each R-test's actual values, so card review is a read, not a recomputation). Summary sheet: all-features Lorenz overlay; classification table T2; pre/post-transform leverage bars. Panels A/B/D and C's trajectory are budget-independent (only marked crossings move) — archived per D2's requirement. Cards land in `audit/feature_cards/`.

**Rule-set (pre-registered; global constants fixed before the audit runs):**

| Rule | Test | Assignment |
|---|---|---|
| R1 Transformation (amended v0.8) | Screened for ALL features (battery item 3). Adoption requires an explicit **value-model claim**: the transform's shape must mean something defensible for that feature (e.g., 1/v = refugial residence time). Concavity distinction is binding: a concave transform (log/sqrt) asserts diminishing value *per cell density*; a target asserts diminishing value *at the portfolio level* — different claims, not interchangeable dominance fixes. Carbon fails the per-cell concavity test (a tonne is a tonne — density-linearity is physically mandated — identity + target, per E9 demonstration). AOH richness is the open case (diminishing per-cell species value is ecologically arguable): audit reports it, paper notes it as an alternative value model, identity retained for paper 1 with footprint cost disclosed | Adopt only interpretable transforms; report leverage before/after. Never adopt because leverage improves — rank/percentile stretches inadmissible (contrast without meaning manufactures influence from noise). Keeps 1/v admissible; excludes rescuing intactness by rank stretch |
| R2 Valuation class | (i) Marginal-density ratio ≥ θ sustained over area ≥ a_min AND (ii) implied target ≥ t_min (tail-mass criterion: the stopping rule must secure a meaningful claim) | **Concentrated-satiating** — derived target via stopping rule at θ; target is the value dial |
| | Crosses θ but fails t_min (shallow/small tail — a target would saturate instantly, leaving most of the feature governed by nothing) | **Diffuse-linear** — 100% target; weight is the value dial. Expected: biomass (implied target 0.066; nothing at 10× mean) |
| | Capturable in full within budget by rarity | **Rare-attainable** — saturates; no scenario lever; adequacy locked (expected: most EFGs) |
| | None of the above; leverage ≥ λ | **Diffuse-linear** — 100% target; weight is the value dial |
| R3 Expressivity floor | Leverage < λ after best interpretable transform | **Low-contrast/inexpressible** — excluded from scenario tilts; disclosed in audit (expected: intactness at 0.042, unambiguous under any plausible floor) |
| R4 Global constants | θ = 5× (E10 sensitivity at 3×/10×); λ = 0.10; a_min = 0.5% of region; t_min = 0.15 | FROZEN v0.3, before the audit runs; no per-feature tuning. Disclosures carried in Methods: θ was originally set on carbon and is generalized here (E10 is the empirical backstop); t_min chosen knowing the data BUT classification is insensitive across 0.07–0.33 (mineral soil 0.332 vs biomass 0.066 — five-fold margin); λ sits in the wide gap between mammals (0.181) and intactness (0.042), identical classification for any floor in 0.05–0.15. Mammals at 0.181 flagged as marginally live; T1's absolute influence shares make this visible |

**Notes.** (a) The audit is conditional on B = 30%; classifications could shift at other budgets — stated in Methods, harmless while budget is fixed. (b) Classification is ex-ante; saturation is ex-post and verified per cell by E7 — protocol and E7 are one framework in two stages (assign levers from layer geometry; confirm the regime each feature landed in). (c) Watch item: AOH birds — if it shows a meaningful concentrated tail, R2 offers a target-levered option interacting with the footprint-correlation problem; handle as a documented decision if it arises.

## 3. Formulation space

### 3.1 Value scenarios (influence-space, PROACT-anchored)

**Every scenario is a complete (weight vector, target vector) pair** — a full formulation cell. The lever carrying a scenario's emphasis for each feature follows §2.5's classification: targets for concentrated-satiating features (claim magnitude), weights for diffuse-linear features (priority across an unbounded claim). No feature is "treated differently" ad hoc; the protocol assigns levers.

**S0 is an analyst-constructed equal-influence reference over PROACT-selected objectives.** PROACT selected and structured the objectives (mission alignment: which values are in the problem) but elicited no weights or ranges — no weight vector carries stakeholder endorsement. Consequence, stated as framing in the paper: **no single map is the deliverable; the frequency surface is.** The absence of elicited weights is the argument for the ensemble as primary product. S0 is a coordinate origin for the tilts, not a privileged answer.

**Operationalization of "equal" (v0.4):** equal *influence*, not equal weights — equal weights would reinstate the leverage-determined profile (connectivity 0.461 vs mammals 0.181 — 2.5× silent disparity) that Claim B indicts. S0 assigns each **value block** an equal share of discretionary influence, weights backed out per Claim C (w = influence/leverage). Per-block, not per-feature: per-feature "equality" would give two-feature blocks double weight in no sense anyone endorses. **Block structure (PROACT objectives hierarchy — CONFIRMED v0.5):** quality of core habitat {macrorefugia}; connectivity {transboundary connectivity, climate corridors}; carbon {mineral-soil (SOC) target claim; biomass weight, pending Gate 0a}; biodiversity {AOH birds, AOH mammals}; representativeness {40 EFGs}. Representativeness is treated as **locked adequacy foundation outside the scenario axis** (SCP doctrine: representation is targets-based adequacy, not preference; 36/40 EFGs classify rare-attainable with no scenario lever) — the four unsaturated EFGs are disclosed in the audit, and the exclusion of a representativeness-forward scenario is stated with this rationale (see D7). Equal discretionary influence is therefore divided among the three weight-levered blocks (core habitat, connectivity, biodiversity), with carbon's claim set by protocol targets. Scenario symmetry: **S0 = equal shares per block; S1–S4 = each block's share doubled in turn** (see D1). Note the corridors reassignment separates the axes cleanly: valuing climate-relevant features (S1 core-habitat-forward) is now orthogonal to climate *uncertainty* (the RCP layer axis); the Carroll static-layer disclosure attaches to S2's block membership.

**Mission-selected-vs-implementable gap (retained):** PROACT placed intactness among the objectives; the audit shows the formulation can express ≤1% of it. Reported in T3 as before — the gap is now "mission-selected vs implementable," not "elicited vs implementable."

Baseline influence shares recomputed at Gate 1 under protocol-derived targets (the leverage-doc table predates retargeting and will shift).

| ID | Scenario | Lever(s) (protocol-assigned) | Sketch (final numbers set at Gate 1) |
|---|---|---|---|
| S0 | Balanced (reference) | Full (w, t) pair | Equal discretionary influence per weight-levered block; protocol-derived targets |
| S1 | Core-habitat-forward | Weights | Core habitat block {macrorefugia} share doubled from S0; other blocks scaled down proportionally |
| S2 | Connectivity-forward | Weights | Connectivity block {transboundary, climate corridors} share doubled from S0. Carroll static-layer disclosure attaches here |
| S3 | Biodiversity-forward | Weights | Biodiversity block {AOH birds, AOH mammals} share doubled from S0; mandatory gHM audit |
| S4 | Carbon-forward | Targets (concentrated-satiating features only) | Carbon block claim doubled via target relaxation (5×→3× or flat level; choose at Gate 0). Biomass expected diffuse-linear under R2 tail-mass criterion (implied target 0.066 < t_min) — S4 then tilts SOC target + biomass weight; lever follows class as confirmed at Gate 0a |
| S5 | Intactness-forward | Documented-inexpressible (R3) per D3 recommendation | Reported as expressivity finding; gHM-cost variant deferred to future work. NB: intactness sits outside the PROACT block structure — strengthens the D3(b) exclusion rationale |
| S1.5/S2.5 (optional) | Midpoints | Weights | Convex combinations if corner scenarios diverge sharply (decide after pilot) |

Every scenario ships with: (a) intended influence profile, (b) derived (w, t) pair, (c) realized capture ratios (×area share), (d) realized influence decomposition, (e) per-cell saturation verification, (f) gHM audit (mean gHM of new selections vs passed-over land — mandatory for S3 given the footprint correlation).

### 3.2 Other axes

| Axis | Levels | Crossing |
|---|---|---|
| Climate scenario | RCP4.5-2050s vs RCP8.5-2080s macrorefugia layer (AdaptWest backward velocity, Mahony CMIP6 ensemble) | Full cross with all scenarios |
| Carbon target regime | Adopted (5×) vs carbon-forward level | S4 only, EXCEPT a small crossed subset {S1, S3} × carbon-forward for E3 attribution |
| Budget | 30% fixed (locked-in PAs count toward budget) | Fixed parameter; ±5% sensitivity appendix only (Open Decision D2) |
| Boundary penalty | REMOVED | — |
| Solver gap g | Lens parameter, not axis | Fixed at one value for main results; varied only in E4 |

**Disclosure carried in Methods:** climate corridors (Carroll 2018) are static RCP8.5/late-century and do not co-vary with the climate axis; the axis propagates climate uncertainty only through macrorefugia.

Cell count: 6–7 scenarios × 2 climate + 2–4 crossed carbon cells — **14–18 cells**. At k=50: 700–900 solves — 2.5–3 h single-threaded at 12 s/solve; trivially parallelizable.

## 4. Estimand and aggregation rules

- Within-cell: f_{i,s} = (selections of i among k_s retained solutions) / k_s.
- Cross-cell: F_i = mean over cells, one vote per cell. Never flat-pool k×N solutions (E2 demonstrates why).
- If Gurobi pool returns < k distinct solutions for a tight cell, use what exists; the hierarchical mean is unaffected (this is the argument for hierarchy over flat pooling).
- g and k are reported parameters of the estimand. Frequency claims are always "within g-near-optimal sets."
- Classification bands for maps: always (≥0.95) / frequent (0.70–0.95) / conditional (0.30–0.70) / rare (0.05–0.30) / never (<0.05). Bands are presentational; analyses use continuous F.
- Agreement statistics between cells: overlap coefficient (not Jaccard) wherever selected-set sizes differ.

## 5. Expressivity audit (runs with every cell; reported as first results section)

Per cell s, per feature f: leverage_f (under s's targets), w_f, influence share, saturation status (target met at optimum? y/n), realized capture ratio. Two derived products:

1. **Live-feature map of the design:** which features CAN each scenario move. Published as a table; the interpretive key for the entire frequency surface.
2. **Robust-vs-inexpressible demonstration:** show empirically that intactness-relevant areas have invariant f across S0–S3 *because inexpressible* (influence ≤1%), while a live feature (e.g., corridors) shows genuine scenario response. This is Claim B's figure.

## 6. Experiments

| ID | Comparison | Supports | Pass/interpretation criterion |
|---|---|---|---|
| E1 | Hierarchical F vs naive one-solve-per-cell frequency | Claim A motivation | Spatially structured bias map (F_hier — F_naive); report magnitude distribution and where it concentrates (predicted: saturated-feature-interchangeable regions) |
| E2 | Hierarchical vs flat pooling of all solutions | Claim A semantics | Divergence wherever cells return unequal k; document denominator distortion |
| E3 | Variance decomposition of f_{i,s}: scenario axis vs climate axis vs carbon-regime vs within-cell degeneracy | Attribution | Per-region attribution maps; within-cell share quantifies how much apparent "conditionality" is degeneracy |
| E4 | F at g — {2%, 5%, 10%} × k — {10, 30, 50} on diagnostic cells | Estimator behavior | Convergence in k; monotone flattening in g documented; pick production (g, k) |
| E5 | Gurobi pool (PoolSearchMode=2) vs shuffle-on-HiGHS vs Brunel-style dissimilarity-controlled generation | Pool-bias robustness + licensing insurance | If concordant: production method = cheapest. If divergent: finding about pool bias, reported |
| E6 (INACTIVE — deferred per D5) | Marxan summed solution, one cell, calibrated SPF, 100 runs | Pre-empts "25-year-old practice" objection | If activated: time-boxed ≤2 days; coarsened grid pre-authorized; one supplementary figure |
| E7 | Expressivity audit (§5) | Claim B | Robust-vs-inexpressible figure |
| E8 | Carbon-weight inertness demo: carbon w ×10 at S0 AND at the most carbon-hostile cell (strongest competing tilt) | Lever-selection principle | If solutions unchanged (0 PUs differ): inertness demonstrated across design range. If changed: conditional break located and reported via E7 |
| E9 (three arms, v0.8) | S0-protocol-targets vs S0-influence-weights-at-100%-targets vs S0-log-carbon-at-100%-targets | Justifies target lever over weights-only AND over concave-transform dominance fixes | Pre-stated predictions: (weights arm) carbon capture per carbon-allocated hectare drops, densest-decile capture rate specifically; (log arm) carbon influence lands between the other two but carbon-per-carbon-hectare is WORST — concave transform shrinks influence by blunting the density signal (still unbounded claim, inefficient pursuit), while the target bounds the claim and preserves within-claim efficiency. Measured answer to "why not just weights" and "why not log-transform" |
| E10 | θ-sensitivity: protocol targets at θ — {3×, 5×, 10×} (three solves, S0 otherwise) | R4 defensibility | Measured answer to "where did 5× come from"; report target/capture shifts |

## 7. Gates and sequencing

**Gate 0a — Feature characterization audit (NEW; BLOCKING; runs first, zero solves).** Execute the §2.5 battery on all 12 inputs; apply R1–R4 with θ and λ as frozen in R4; freeze the resulting per-feature (transform, class, lever, target) table into the manifest. Expected outcomes to confirm or overturn: mineral soil — concentrated-satiating; **biomass — decide by rule** (revert to diffuse-linear if no concentrated tail — adopted, per resolved principle); most EFGs — rare-attainable; intactness — R3 inexpressible; connectivity/macrorefugia/corridors/AOH — diffuse-linear. Any reclassification propagates to §3.1 lever assignments before Gate 0 runs.

**Gate 0 — Stopping-rule validation (BLOCKING; queued).** Run the four comparison solves — control, ≥θ rule (per Gate 0a table), flat 30%, flat 40% — as *validation of the protocol's target-levered classifications*: capture lands at target (not above); freed budget goes somewhere measurable (candidates: climate corridors at 0.96×, nine below-share EFGs). The control (100% target — extreme carbon-forward, 39.7% of objective swing) brackets S4 and is reported as such. Also selects the S4 level. Fail branch: revisit θ or the R2 test before any ensemble work.

**Gate 1 — Post-protocol expressivity baseline.** Recompute leverage, saturation, influence shares under the frozen Gate 0a targets. PROACT translation applied per D6 resolution; elicited-vs-implementable gap computed. Outputs: live-feature set confirmed; S0 (w, t) pair and all tilt-derived scenario pairs frozen into manifest.

**Gate 2 — Degeneracy pilot.** Reference cell (S0 × RCP4.5) + 4 corner cells. k=50, g=5% via best available pool method. Measure within-cell f distribution. Pass (fat middle, as predicted): proceed, calibrate production k from E4-style convergence. Fail (near-binary): the E1 effect is weak on this landscape — pivot options: (a) tighten focus to Claims B+C with E1 as a boundary-condition result, (b) add a deliberately degenerate demonstration problem (coarsened or synthetic) to show when the correction matters. Do not proceed to Gate 3 without choosing.

**Gate 3 — Manifest freeze + pre-registration.** Manifest (§9) written, hashed, timestamped BEFORE the full ensemble. Includes axis levels, scenario weight vectors, k, g, aggregation rule, band thresholds, E1–E7 analysis plan, and the Gate 2 outcome. This is the anti-post-hoc-pruning defense and a citable methods feature.

**Gate 4 — Full ensemble + analyses.** All cells × k. Then E1–E5, E7–E10; E6 optional supplementary. (E8–E10 are single-solve additions, ≈6 extra solves total.)

**Gate 5 — Write-up.** García-Quintas et al. 2025 (10.1016/j.biocon.2025.111447) full text MUST be dissected before the novelty framing is drafted (author request to Brunel's group acceptable). Positioning language per §12.

## 8. Compute plan

**Licensing sequencing (v0.7):** Gurobi license expected within days. Pre-license work proceeds now: Gate 0a (zero solves), Gate 0 comparison solves (HiGHS, four solves), manifest drafting, driver-script and storage scaffolding, E-analysis code written against the solutions.npz contract. Gurobi-dependent items — Gate 2 pool runs (PoolSearchMode=2), E4 grid, E5 pool-method comparison, production ensemble if pools are the chosen method — WAIT for the license rather than substituting shuffle interims; the wait is days and avoids duplicated runs. E5 retains its role as licensing insurance if the license falls through.

- Production solver: whichever E5 validates; plan for HiGHS-shuffle as guaranteed path (k full re-solves × 12 s), Gurobi pool as fast path (one tree search amortizes k).
- Full ensemble upper bound: 18 cells × 50 = 900 solves — 3 h serial; run parallel across cells.
- E4 grid: 5 diagnostic cells × 3 gaps × (k=50 superset, subsample for k-curves) — 750 solves.
- All solution vectors stored as compressed binary matrices (PU × solution) per cell; frequency computation vectorized downstream. Never store only the frequencies — raw solution sets are needed for E2/E3/E5.

## 9. Manifest schema (contract)

One row per cell. Columns: `cell_id`, `scenario_id`, `scenario_name`, `climate_level`, `carbon_regime`, `budget_pct` (=30), `weight_vector` (JSON, per-feature), `target_vector` (JSON, per-feature), `influence_profile_intended` (JSON), `k_requested`, `pool_gap`, `solver`, `solver_gap`, `seed_policy`, `input_layer_hashes` (JSON), `created_utc`, `frozen` (bool). Companion file: `manifest_freeze.sha256`. Any post-freeze change requires a new manifest version and a changelog entry; frozen cells are never edited.

## 10. Directory / file contract

```
project_root/
  spec/frequency_ensemble_study_plan.md      # this file
  spec/manifest.csv + manifest_freeze.sha256
  audit/feature_cards/<feature>.pdf          # §2.5 per-feature cards + summary sheet
  audit/audit_objects/                       # budget-independent Lorenz/trajectory arrays (per D2)
  runs/<cell_id>/solutions.npz               # PU × k binary matrix
  runs/<cell_id>/cell_audit.json             # expressivity audit outputs (§5)
  analysis/e1_bias/ ... analysis/e10_theta/
  figures/
  changelog.md
```

## 11. Figures and tables plan

F1 estimand schematic (two-level structure). F2 E1 bias map per the 30% budget. F3 main frequency surface with bands + always-core highlighted. F4 attribution small-multiples (per-axis conditional F). F5 expressivity figure (robust vs inexpressible; Claim B). F6 convergence panels (E4). F7 pool-method comparison (E5). F8 marginal-density trajectories, all features, with θ crossings marked (the protocol's key figure — visually shows why mineral soil earns a target and biomass may not). T1 scenario table (intended influence — (w, t) pairs — realized capture, absolute influence shares). T2 feature characterization table (§2.5 output: transform, class, lever, target per feature). T3 expressivity audit summary incl. elicited-vs-implementable gap. Suppl.: Marxan comparison, per-scenario gHM audits, E8 inertness demo, E9 hotspot-dilution comparison, E10 θ-sensitivity, manifest, ±5% budget sensitivity (if D2 approved). All maps ESRI:102008; CVD-checked ramps (single-hue sequential for F; categorical band palette CVD-simulated before adoption).

## 12. Positioning and citations (from novelty report — verify all DOIs before tracker entry)

- Formulation lineage: Jung et al. 2021 NEE (10.1038/s41559-021-01528-7).
- Scenario-ensemble lineage extended from climate/data axes to elicited value axes: Buenafe et al. 2023 (10.1002/eap.2852); Brito-Morales et al. 2022; Chapman et al. 2025 (10.1038/s41559-025-02671-1); Liczner et al. 2023 (10.1111/csp2.12994); participatory precedent Carpenter-Kling et al. 2025.
- Aggregate-solutions-not-inputs principle: Meller et al. 2014.
- Within-problem near-optimal lineage: Brunel et al. 2023 (10.1007/s10666-022-09862-1); prioritizr portfolio functions; Marxan summed solutions (Ball, Possingham & Watts 2009) — cite generously so the contribution reads as combination.
- Highest prior-art risk: García-Quintas et al. 2025 (10.1016/j.biocon.2025.111447) — Gate 5 blocking check; two positioning branches pre-drafted in the novelty report.
- Novelty sentence: "to our knowledge, no published conservation prioritization nests within-formulation near-optimal selection frequency inside a cross-formulation ensemble with per-formulation averaging."
- Fresh literature sweep immediately before submission (field moving fast, 2025–2026).

## 13. Open decisions (need Ethan's call before Gate 1)

**Resolved (v0.2–v0.7):** S0 = analyst-constructed equal-influence-per-block reference over PROACT-selected objectives (no weights/ranges were elicited — D6 dissolved; framing consequence: the frequency surface, not any single map, is the deliverable). "Equal" operationalized as equal discretionary influence per value block, weights via Claim C. Biomass reclassification: adopted by R2 tail-mass rule. Scenarios are complete (w, t) pairs with protocol-assigned levers. θ = 5×, λ = 0.10, a_min = 0.5%, t_min = 0.15 — FROZEN v0.3. **D4 (v0.5):** PROACT block structure confirmed — core habitat {macrorefugia}; connectivity {transboundary, corridors}; carbon {SOC, biomass}; biodiversity {AOH ×2}; representativeness {EFGs}. **D7 (v0.6):** representativeness-forward scenario excluded; EFGs locked adequacy foundation. **D1 (v0.6):** tilt magnitude = doubling only. **D3 (v0.7):** option (b) — intactness-forward excluded; inexpressibility published as a Claim B finding with mechanism (right-skewed gHM) and measured cost (new selections at mean gHM 0.074 vs 0.055 passed over); footprint-as-cost named in Discussion as the future formulation-change remedy, explicitly distinguished from a value tilt.

**Deferred (decide later; no current gate blocked):**
- **D2 — Multi-budget analysis.** Paper 1 runs at 30% only (30×30 policy anchor; B-conditionality of §2.5 stated in Methods). Genuine interest in 20/30/40/50% recognized — likely applied-paper scope. Requirement carried forward: Gate 0a archives budget-independent audit objects (Lorenz curves, marginal-density trajectories) so re-derivation at any B is a lookup of new crossings, not a re-computation.
- **D5 — Marxan comparison (E6).** Not needed now; may still run (pre-revision or at revision). If activated: time-boxed (≤2 days), coarsened grid pre-authorized if annealing runtime at 1.27M PUs demands it, stop-rule if SPF calibration turns pathological. E6 remains in the experiment table marked INACTIVE.

## 14. Out of scope (fenced)

Post-hoc corridor/compactness delineation from the frequency surface (separate work; Discussion mention only). PROACT elicitation methodology itself (cite the process; Laura's component). Eastern-slopes grizzly analysis. Budget stratification machinery beyond D2. Sobol' analysis. Applied-paper full PROACT weight treatment if the elicited vectors differ from the mission-aligned scenarios used here.
