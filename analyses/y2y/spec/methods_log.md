# Methods log — Y2Y frequency-ensemble flagship (living document)

**Purpose.** The cumulative record of every methods-relevant decision, data manipulation, and
measured finding in this analysis, in enough detail to write the paper's methods section without
archaeology. Each entry carries: what was done, exact parameters, the justification, the
evidence, where it is implemented, and its status.

**Maintenance rule (binding on every working session):** any change that alters the data, the
formulation, the solver configuration, or a QA rule gets an entry HERE in the same session it is
made — including reversals. Supersessions are marked, never deleted: the paper may need to say
"we initially X, then Y because Z."

Scope: paper 1 (the hierarchical selection-frequency ensemble) and the leverage redesign it
inherits. Companion documents: **`results_log.md` (the corresponding RESULTS register — same
maintenance rule; quantitative outcomes live there, methods decisions here)**,
`frequency_ensemble_study_plan.md` (the spec), `gate0_reportback.md` (checkpoint summaries),
`feature_characterization.csv` (the frozen T2).

---

## 1. Study system and grid

- **M1.1** Grid: ESRI:102008 (North America Albers equal-area), **1 km**, Y2Y boundary buffered
  20 km. Planning units = cells valid in ALL continuous features: **1,272,914** (≈1.27 M km²).
  Rationale: most inputs ~1 km native; minimizes resampling distortion; tractable. (2026-06-10)
- **M1.2** Resampling: finer-than-1 km → `average`; coarser → `bilinear`; categorical (EFG) →
  `nearest`. gHM (~90 m) and AOH (~100 m) down-sampled — accepted for iteration 1; 300 m is the
  stated ceiling, 100 m out of scope.
- **M1.3** PU-footprint caveat (disclosed, not acted on): the PU mask is set by
  `irrecoverable_carbon_biomass`'s footprint (1,274,564 km²); every other continuous layer covers
  ~1,551,000+ km² — one layer's coverage excludes ~18% of the buffered study area from every
  solve. (2026-08-07)

## 2. Input data manipulations (chronological; ALL tweaks to data live here)

- **M2.1** Orientation doctrine: every feature oriented so higher = more conservation value,
  BEFORE any solve; no normalization at the data stage.
- **M2.2** gHM → intactness as `1 − gHM`, clipped [0,1]. KEPT despite known consequence (M6.4):
  no interpretable transform recovers its leverage (p1–p99 stretch reaches only 0.084 vs raw
  0.742), and rank/percentile stretches are ruled inadmissible (M4.3). (decided 2026-08-17)
- **M2.3** Backward climatic velocity → refugia: **`vmax − v` REPLACED by `1/v`** (refugial
  residence time, yr/km). Justification: 03 sum-normalizes features, so an ADDITIVE flip does
  not cancel — it compressed the layer toward a constant, destroying 75% of its leverage
  (0.353 → 0.090) and making macrorefugia the least influential factor in the Morris screening:
  an artefact of preprocessing read as a finding. `1/v` restores leverage to **0.422** (above
  raw 0.353); tail verified safe (min v over PU = 0.097 km/yr → max 10.3; top 100 cells = 0.1%
  of total); loud assert on v ≤ 0 rather than a silent epsilon floor. Side benefit: makes the
  six climate realizations comparable without shared anchors (leverage 0.422–0.516 across all
  six vs 0.079–0.106 under per-layer vmax subtraction). (2026-08-17/18)
- **M2.4** EFG value recode: IUCN source 1=major/2=minor SWAPPED to major=2/minor=1 so the
  optimizer weights major occurrences above minor. 40 of 109 EFGs occur in the PU. (verified
  2026-07-16)
- **M2.5** **Numerical-dust threshold (the carbon floor tweak): cells holding < 1e-9 of a
  feature's total set to 0** (`config.DUST_SHARE_MIN`; 02 Stage 2, post-orientation).
  Justification: `average`-resampling near-zero fine cells leaves float residue (min share
  1e-16) that carries no information but stretched the optimizer matrix to [1e-11, 1e5] — the
  proximate cause of a false Gurobi optimality certificate (M5.4) and slow, numerically
  strained solves. Measured drops: biomass 46,097 cells / 1.5e-5 of mass; m_soc 19,262 /
  8.4e-6; connectivity 538 / 3.9e-7; all other layers clean (min share ≥ 4e-8). Matrix range
  after: **[1e-4, 1e5]** (verified in every solve log). **Invariance demonstrated:** the re-run
  audit reproduces every classification and the 0.332 target; PU count unchanged (zeroing
  changes values, never validity). NOT achievable by rescaling NORM_TOTAL (share-based ratio,
  scale-invariant). (2026-08-26)
- **M2.6** No urban/converted mask (gHM already down-weights converted land); `sl_soc` subsoil
  carbon excluded from the solve (near-collinear with m_soc); connectivity tail NOT capped
  (CONNECTIVITY_CAP_PCTILE=None; surfaced in QA instead).
- **M2.7** Climate realization: single layer `bwvel 585_2071_2100` in the stack. The choice is
  MATERIAL by pre-registered rule (six realizations, worst top-30% Jaccard 0.460 vs 0.11–0.24
  between genuinely different inputs). Climate axis for the ensemble: **SSP245 vs SSP585, both
  2071–2100** — horizon fixed so the axis means emissions uncertainty; per-year velocity
  denominators are horizon-dependent, so mixing horizons confounds. (QA 2026-07-30; axis
  decided 2026-08-18; ratified spec v0.9 D6)
- **M2.8** **Climate realization layers built as stack-grade features** (Gate 1, D6): both axis
  levels (`245_2071_2100`, `585_2071_2100`) put through the identical Stage-2 pipeline — orient
  `1/v` → non-negativity clip → dust threshold (M2.5's rule) → PU mask — and written to
  `aligned_stack/climate_realizations/` (a namespace outside the canonical manifest; ensemble
  formulations point the macrorefugia path there per formulation). Orientation is per-realization: `1/v`
  needs NO shared anchor (six-realization leverage 0.422–0.516), which is what made the axis
  implementable without re-anchoring every layer. QA: the 585 output must reproduce the stack's
  canonical macrorefugia layer (tolerance 1e-5 — provenance proof that the stack layer IS the
  ssp585 realization); PU set unchanged by construction. (built 2026-08-27; 02 closing section)

- **M2.9** **θ-tail carbon features (spec v0.10 D-B, built by 08_gate2a_tails):** two derived
  masked-DENSITY layers — `m_soc_tail`, `biomass_tail` = parent density where ≥ θ×regional
  mean, else 0 (PU-masked) — so capture = share of TAIL MASS and t=1.0 secures the whole tail
  (0.95 fallback pre-authorized). In EVERY analysis' manifest as feature_continuous at target
  **0.0 = mathematically absent** (verified: a 0-target feature's constraint row has rhs 0 and
  its shortfall column zero nonzeros); ONLY carbon-forward formulations activate them at 1.0.
  Motivated by M6.7; audited under the UNCHANGED frozen §2.5 rules (expected rare-attainable;
  addendum records in `audit_objects/tail_addendum.csv` + bespoke cards — the frozen T2 is
  untouched). Engineering constraints honored: manifest entries sit BEFORE the EFG block
  (pr_weights builds its vector positionally) and `pr_targets`' range guard relaxed
  (0,1] → [0,1]. (2026-08-28)
  **STATUS (v0.11, same day): DEMOTED to escalation contingency — see M4.13.** The machinery
  was incidentally EXECUTED end-to-end before v0.11 landed (Ethan ran the v0.10 notebook):
  tails built and audited under the frozen rules — **both rare-attainable exactly as
  predicted** (leverage 1.0, cap_max 1.0; m_soc_tail cutoff 303.7 t/ha @ 4.06% area / 33.2%
  of parent mass; biomass_tail 105.6 @ 1.17% / 6.6% — all matching the frozen T2/archive) —
  then STOOD DOWN: layers moved to `aligned_stack/_v010_tails_quarantine/`, manifest restored
  to the original 8 continuous features, audit addendum + cards kept as the pre-verification
  record. The escalation itself was subsequently RESCINDED (M4.14) — the record stays as
  backup knowledge only.

- **M2.10** Shared-code LABEL fix (2026-08-31, made from the northern-connectivity
  campaign): `results_core.RAW_SPEC`'s macrorefugia unit string still described the
  retired `vmax − v` orientation; corrected to "yr/km (mean; refugial residence =
  1/backward velocity)" per M2.3. Values were always computed from the hand-off layer
  and are unaffected — only the unit column of `consequences_raw.csv` (and any table
  importing RAW_SPEC) changes on its next regeneration.

## 3. Feature characterization protocol (Gate 0a; spec §2.5)

- **M3.1** LEVERAGE (the organizing statistic): share of a feature's total held by its richest
  30% of PUs minus its poorest 30% = the entire range its captured fraction can span. At
  leverage ≈ 0 the feature's objective term is near-constant over every feasible selection —
  no weight can move it. Reproduces the Morris μ* ranking at Spearman **+0.922 with zero
  solves**; `w × leverage` decomposes the objective's achievable swing exactly (two-regime
  general form under targets: `w·(min(cap_max,t) − cap_min)/t`).
- **M3.2** Pre-registered rule-set R1–R4, constants FROZEN before the audit ran: θ = 5× regional
  mean, a_min = 0.5% of region, t_min = 0.15, λ = 0.10. Disclosures: θ generalized from carbon
  (E10 sensitivity at 3×/10× is the backstop); t_min chosen knowing the data but classification
  insensitive across 0.07–0.33; λ sits in the wide gap between mammals (0.181) and intactness
  (0.042).
- **M3.3** Transform admissibility (R1): screening universal ({identity, log1p, sqrt} + flip/
  reciprocal where cost-oriented) but ADOPTION requires a value-model claim; rank/percentile
  stretches inadmissible (contrast without meaning manufactures influence from noise). The
  concavity distinction is binding: a concave transform asserts diminishing value per CELL, a
  target asserts it at the PORTFOLIO level. Measured support: log1p flips m_soc to
  diffuse-linear (0.884→0.486 — destroys the very tail that earns the target) and drops AOH
  birds below the floor (0.232→0.059). Carbon: per-cell linearity physically mandated
  (identity + target). AOH: open case disclosed, identity retained.
- **M3.4** Frozen classifications (invariant across the dust threshold): m_soc
  concentrated-satiating (target 0.332 = 5×-rule crossing @ 4.06% of region, cutoff 304 t/ha);
  biomass REVERTED to diffuse-linear by the t_min tail-mass criterion (implied target 0.066);
  connectivity diffuse-linear via a_min (0.20% pinch-point spike); macrorefugia diffuse-linear
  (near-miss a_min at 0.47% but fails t_min — robust to either leg); intactness R3
  inexpressible; 36/40 EFGs rare-attainable (unsaturated four disclosed).
- **M3.5** Audit outputs: T2 table, per-feature 6-panel cards + EFG block card + summary sheet,
  F8 marginal-density trajectories (log-x with color-matched area-% labels at θ crossings),
  budget-independent archive (Lorenz + marginal curves; target at any θ or budget = lookup;
  layer sha256s pin the stack version).

- **M3.6** **Accounting extents, stated explicitly (2026-09-02, prompted by review):**
  (1) ALL characterization quantities — leverage, cap_min/cap_max, θ-cutoffs and tails,
  implied targets, archived curves — are computed over the FULL 1,272,914-cell PU extent,
  locked PAs included. (2) The solve uses explicit lock-in (lb = 1; PA cells remain in the
  matrix), so locked amounts COUNT toward relative targets — the PA estate pre-banks 12.3%
  (biomass) to 19.2% (refugia) of each feature's total; m_soc's 0.332 target needs only 15.6
  further points from discretionary land (17.6% banked). (3) The 30% budget INCLUDES locked
  area (191,029 of 381,874 cells = 50.0%). No mixed accounting (no exclusion-plus-deduction
  variant). DISCLOSURE: audit capacities are unconstrained-by-lock-in, while the solve is
  lock-conditional — the feasible capture range is shifted (floor ≥ banked share; ceiling
  from the 85% unprotected pool). Leverage/swing therefore describe budget CAPACITY;
  realized influence operates on the lock-conditional set — one mechanism behind the R8.5
  structural intended-vs-realized misses.

## 4. Optimization formulation

- **M4.1** `min_shortfall` objective, 30%-of-area budget (381,874 cells), existing PAs locked in
  and counted (191,029 = 15.0%), uniform cost = 1 (area), features sum-normalized to 1e5
  (conditioning only; scale-invariant), weights: continuous @1, EFG group shares 1.0 (1/40
  each). t = 1.0 is NOT a target — it is unreachable by 1.1–3.2× for every continuous feature
  and encodes "no satiation point".
- **M4.2** Influence identity: below target the solver maximizes Σ (w_f/t_f)·h_f — weight and
  target enter ONLY as the ratio (pull), plus a reachable stopping point. Consequences: (a)
  equal weights silently chose an influence profile (carbon 39.7% of achievable swing, captured
  1.52×/1.39× area share vs 0.96–1.06× for all else); (b) not fixable by objective choice (all
  three families linear in captured fraction); (c) a low target at w=1 RAISES pull (0.332 →
  3.0×) — hence the **w = t discipline**: every targeted feature gets weight = target so pull
  stays 1.00 and the target acts ONLY as a stopping rule. Empirical proof: the a4 arm
  (connectivity w=t=0.6, unreachable) reproduces the control EXACTLY — LP: 0 differing cells;
  binary MILP on exact certificates: 0 differing cells.
- **M4.3** Warrant test for a stopping rule: only features over-served relative to their
  intended role. Carbon qualifies; EFG targets were examined and REJECTED on measurement (the
  5 over-served EFGs span 736 cells → capping frees ≤0.13% of budget; the 9 under-served span
  61.7% of the region → lifting them costs ≥12.7%).
- **M4.4** Compactness penalty REMOVED from the optimizer (was neighbor penalty 1e-5,
  uncalibrated): Morris ranked it 3rd of 12 drivers; it relocated a third of the selection
  (Jaccard 0.662 vs unpenalized); the unpenalized solution is already 66.6% clustered by area;
  it cost 400× solve time. Compactness moves to post-hoc delineation from the ensemble's
  selection-frequency surface. (2026-08-17)
- **M4.5** Decision types: proportion-LP (HiGHS) was the prototype; production = **binary MILP
  (Gurobi)**. Relaxation tightness MEASURED, not assumed: LP ~100% integral; LP-vs-MILP Jaccard
  0.97–1.00; capture deltas ≤ 1.4 pts.
- **M4.6** Gate-0 pass criterion corrected by measurement: min-shortfall never penalizes
  EXCEEDING a target (w=1 run: biomass 0.259 vs 0.066 target by incidental co-capture), so
  "capture lands at target (not above)" is wrong as written; only BELOW target fails. Under
  w = t no overshoot occurred (all targets bound to 4 decimals).

- **M4.7** **Spec v0.9/v0.9.1 ratified (2026-08-27); block-level influence budgeting adopted
  (D1, BINDING).** Scenarios are specified as influence profiles over four PROACT blocks
  (`config.BLOCKS`: core habitat {macrorefugia}; connectivity {transboundary, corridors};
  carbon {m_soc, biomass}; biodiversity {AOH ×2}) in **two-regime swing currency**
  `w·(min(cap_max,t) − cap_min)/t` (`leverage_core.swing_per_unit_w`; reduces to w×leverage at
  t=1). Each block's discretionary share is allocated JOINTLY across members; weights follow
  from linearity, `w_f = share_f / per-unit-swing_f`, mean-1 normalized
  (`leverage_core.scenario_weights`). Motivating measurement: under the retired w=t convention
  a1's implicit profile gave biomass ~29% of discretionary swing (the largest single share) —
  the mechanism of the +8.4-pt leak (M6.2); block accounting closes it by construction.
  OUTSIDE the accounting, disclosed: EFGs (locked foundation, 1/40) and gHM intactness
  (R3-inexpressible, w=1); realized influence reported in T1, never budgeted. **w = t is
  RETIRED** — it was itself an influence profile, valid only as the Gate-0 stopping-point
  isolator; S0 weights will not satisfy it. (spec §3.1, §2.7)
- **M4.8** **Carbon within-block split: decided by pre-registered diagnostic, not convention**
  (v0.9.1). Statistic: the a1 biomass θ-tail capture rate (fraction of ≥5×-mean biomass cells
  selected), mass-weighted, decomposed into SOC-claim co-capture (tail ∩ m_soc θ-tail) vs
  independent selection — computed from the archived a1/a0 portfolios, zero solves. Thresholds
  FROZEN in `analyses/y2y/05_s0_construction.ipynb` before the numbers were seen: ≥0.90 → (a)
  mass-proportional split (regional SOC/biomass mass shares); 0.50–0.90 → (b) equal 50/50;
  <0.50 → STOP (escalation to a combined total-carbon feature is a spec amendment decided with
  the chat, never a notebook branch). Rationale recorded: weight sets DEPTH not ORDER (any
  positive w buys a feature's tail first), so the design question is effective pull depth. The
  θ-tail capture rate joins T1/E7 as a standing per-formulation diagnostic. Connectivity and
  biodiversity pairs: equal-within-block default. (2026-08-27)
  **OUTCOME (same day, Ethan's run): a1 mass-weighted tail capture = 1.000 → (a)
  mass-proportional ADOPTED (74.2/25.8, computed live from regional mass).** The decomposition
  refuted the motivating co-capture hypothesis: only 1.0% of biomass-tail cells overlap the
  m_soc θ-tail, so 98.9% of the captured tail mass is INDEPENDENT selection — dense biomass is
  bought on its own merits, not via the SOC claim. Escalation (combined total-carbon feature)
  not triggered; concern discharged with evidence per the spec's procedure. Standing check
  retained: the diagnostic was measured at biomass w=1, so T1/E7 verifies the tail stays
  captured under S0's derived w≈0.20 (pre-stated expectation: high). Numbers → results_log R5.1.
- **M4.9** **Scenario family derivation (Gate 1):** S0 = equal block shares (0.25 ×4), targets
  {m_soc: 0.332}; S1–S3 = named block share doubled to 0.5, others scaled to 1/6; S4 = carbon
  doubled AND θ relaxed 5×→3× → m_soc t = **0.552** (an archive LOOKUP from the frozen
  budget-independent curves — spec D2's requirement demonstrated, zero recomputation). Derived
  (w,t) pairs frozen to `spec/scenarios_v1.json` (with split rule, diagnostic value, layer
  sha256s); this file is the Gate-3 manifest's input. First-order caveat carried from the spec:
  the translation ignores competition and spatial correlation — intended-vs-realized influence
  is verified per solved cell, biomass weight iterated once if the miss is large. (2026-08-27)

- **M4.10** **Gate-2 design (built 2026-08-27): the first 1 km pool run, three-run structure.**
  Reference formulation = S0, k=50, g=5%. Three runs into three DISTINCT folders (`iter9_y2y_s0_lp` /
  `_s0_single` / `_s0_pool`) because the engine's clobber guard compares only targets+weights,
  which are identical across the three — solver params are unguarded. (1) LP twin (HiGHS ipm,
  proportion) per M5.5; (2) certified single MILP (Gurobi, opt_gap 1e-4) — T1's
  intended-vs-realized source and the pool-cost denominator; (3) the pool (`add_gap_portfolio`,
  PoolSearchMode=2, number_solutions=50, pool_gap=0.05; prioritizr asserts opt_gap ≤ pool_gap).
  **Pre-registered degeneracy verdict, frozen in 07_gate2_analysis BEFORE the pool ran**, on the
  DEDUPLICATED pool over DISCRETIONARY (non-locked) cells only (locked PAs appear in every
  solution and would dilute the denominator): PLATEAU-RICH (Claim A carries) iff k_distinct ≥ 10
  AND ≥5% of ever-selected discretionary cells have 0<f<1; NEAR-BINARY (fail branch → pivot
  decided with the chat, spec §2.9) iff k_distinct ≤ 3 OR <1% fractional; else INTERMEDIATE →
  chat. Frequencies are computed over DISTINCT solutions (prioritizr returns main + pool, so
  the incumbent can repeat). (2026-08-27)
  **OUTCOME (same day, Ethan's run): NEAR-BINARY — the fail branch fired.** 50 distinct
  solutions, but conditional cells 0.09% (<1% threshold), mean pairwise Jaccard 0.9999,
  objective span 3.2e-6 relative. Mechanism (M6.6): PoolSearchMode=2's k-best enumeration
  never samples the g-band. Pivot decision → chat before Gate 3; numbers in results_log R6.3.

- **M4.11** **Spec v0.10 ratified (2026-08-28): the Gate-2 pivot.** (a) **Estimand
  re-registered (D-A(a))**: within-formulation f = membership fraction across k maximally-diverse
  members of the g-band (objective ≤ (1+g)·certified optimum) — interval logic (which cells
  survive every corner of the band), deliberately NOT volume-weighted sampling (uniform vertex
  sampling intractable; plateau volume is geometry, not decision relevance). Estimator
  `mga_maxham_v1`; g stays a certified hard wall + lens parameter; **f(g) at {2,5,10%} becomes
  E4's central robustness product**. One k-best pool retained per ensemble cell
  (optimum-uniqueness statement; the k-best-vs-MGA contrast discharges E5 by design).
  (b) **Amount-vs-places scenario axis (D-B)**: S0 keeps amount semantics UNCHANGED (Gate-2
  artifacts stand); S4 = amount dial (t=0.552) + places locks (tail features at t=1.0).
  (c) **Correction: the v0.9.1 "weight sets depth, not order" rationale is REFUTED** by M6.7
  (joint scoring lets competition invert within-feature hotspot preference); the
  mass-proportional split stands on the S0 amount decision instead. (d) Rulings: the m_soc
  +0.089 realized-share miss ACCEPTED as structural (no iterate-once — re-deriving against
  realized swing chases a competition equilibrium and destroys intended-influence
  interpretability); ensemble LP twins PRODUCED on Gurobi's LP path, HiGHS re-verification as
  a 2-cell spot-check (open-verification = verifiable without Gurobi, not produced without it).
- **M4.13** **Spec v0.11 (2026-08-28): S4's places mechanism simplified — pilot over locks.**
  Per Ethan's review ("I don't need the entire tails — can't w and t capture a lot of it?"):
  S4 = pure (w, t) on the EXISTING 8-feature stack (m_soc t=0.552 + block-doubled carbon
  weights, exactly the Gate-1 derivation), and its places claim is TESTED, not engineered —
  **one certified pilot solve scored against a pre-registered acceptance band: θ-tail mass
  capture ≥ 0.75 for BOTH pools** (S0 reference 0.435/0.425). Rationale: (i) sufficient pull
  demonstrably captures tails (biomass 1.000 at w=1); S0's skip was a low-pull condition
  carbon-forward reverses; (ii) at t=0.552 off-tail co-capture becomes area-expensive, making
  dense-first the cheap shortfall path; (iii) raised weights also buy diffuse biomass broadly
  — a cost elsewhere but ON-MESSAGE in carbon-forward; (iv) min-shortfall targets are
  pressure, not locks — v0.10's t=1.0 over-specified the places reading ("a lot of the tail,"
  not completeness). PASS → no formulation change, full stack symmetry (the original 8 + EFGs
  in every formulation). FAIL (either pool, incl. required w_bio exceeding the doubled block share) →
  pre-authorized escalation: masked tails at **t=0.8** (not 1.0), re-audited, disclosed,
  re-piloted. E7's S4 expectation updated from ≈1.0-by-construction to the band. Implemented:
  `08_gate2a_pilot.ipynb` (R: writes scenarios_v2 = v1 verbatim + band meta; solves
  `iter10_y2y_s4_pilot`; scores in-notebook); the v0.10 tail notebook reworked to
  `08b_contingency_tails.ipynb` (fires only on failure; writes scenarios_v3 with S4 tails
  at 0.8).
- **M4.14** **Tail-feature escalation RESCINDED (Ethan, 2026-08-28, after v0.11).** The
  carbon θ-tail masks will NOT enter the formulation as separate features under any standing
  authorization — v0.10's t=1.0 locks and v0.11's pre-authorized t=0.8 contingency are both
  withdrawn. If the S4 pilot fails its acceptance band, the response is a design discussion
  (chat), not an automatic formulation change. The knowledge is preserved as backup, not live
  machinery: the executed verification (M2.9 STATUS, R7.1), the quarantined layers, the
  archived notebook (`analyses/y2y/archive/08b_contingency_tails_RESCINDED.ipynb`), and git
  history for the removed config wiring (TAIL_FEATURES registry, manifest emission, target
  injection). The `pr_targets` [0,1] relaxation stays (a correct generalization; t=0 semantics
  documented). NOTE for the spec: v0.11's §2.5/§3.1 contingency language predates this ruling
  — carry the rescission into the next spec revision via the chat.
- **M4.15** **Gate-3 freeze design (spec v0.12; built 2026-08-30, 11_gate3_freeze).** 14 formulations
  = {S0…S5} × {ssp585, ssp245} + 2 crossed @ ssp585, frozen to `spec/manifest.csv` +
  `manifest_freeze.sha256` (git commit = the pre-registration). Definitions settled at build:
  **S5 intactness-forward** = S0 weights + `human_modification` ×10 — solving the
  R3-inexpressible push turns the classification into a measurement (Claim B / F5; audit
  predicts near-null response). **Crossed cells** (`s1x`, `s3x`) = S1/S3 block shares held,
  carbon regime flipped alone (m_soc t=0.552, weight re-derived at the same intended share) —
  one axis at a time for E3. **ssp245 formulations** = constant-intended-influence (§3.2): weights
  re-derived per formulation with macrorefugia's swing from the 245 realization
  (`scenario_weights(layer_paths=...)`; verified: 585 path reproduces frozen S0 exactly;
  245 moves only macrorefugia's w 1.460→1.313 with slight re-normalization). Reference formulation's
  kbest/twin recorded as POINTERS to the Gate-2 artifacts (its HiGHS twin is exact and 100%
  integral — more authoritative than a Gurobi LP would be). (2026-08-30)
- **M4.16** **E11 design (spec v0.12.1, Ethan's addition; implemented in 13).** Two-level
  solution-space spread in matched currency: between-anchor pairwise Jaccard (discretionary)
  vs within-formulation diameters D_s — **envelope comparison only** (MGA members are extremes by
  construction; anchor-vs-mean comparisons are forbidden) — plus the cross-objective
  suboptimality matrix Δ(s,s′) = (obj_{s′}(anchor_s) − z*_{s′})/z*_{s′}, computed with zero
  solves from anchor captures × each cell's frozen (w,t) (diagonal ≈ 0 is the built-in
  self-check). Readings: anchors mutually inside each other's 5% bands = certified no-regrets
  value pluralism; large-Δ pairs = measured value conflict, localized by E3. F10. (2026-08-30)
- **M5.9** **Gate-4 runner architecture (12_gate4_ensemble).** Serial over the frozen
  manifest, which is hash-verified against `manifest_freeze.sha256` before any solve. TWO
  ingested base contexts (one per climate level; the 245 context patches
  `ctx$layers$path` for macrorefugia BEFORE `pr_ingest` — the actually-loaded path is recorded
  in each `formulation_meta.json`). Per-cell artifacts land in `analyses/y2y/runs/<formulation_id>/` via the
  engine's `results_dir` + `results_subdir` overrides: `kbest/` (binary pool 50@5%), `twin/`
  (Gurobi **proportion** LP, per the v0.10 twin ruling), plus flat `anchor.tif` +
  `mga_g05.tif` + `certificates_g05.csv` + `formulation_meta.json` (the realized layout keeps
  Gate 2b's flat cell root rather than §10's nominal anchor/ mga/ subdirs — disclosed here).
  Every artifact independently resumable; per-formulation integrity print: twin LP objective ≤
  anchor MILP objective. Optional HiGHS spot-check twin cell (flag-gated). (2026-08-30)

- **M4.17** **Terminology convention (Ethan, 2026-08-30): "formulation", never "cell", for the
  14 ensemble design points.** In a raster analysis "cell" reads as pixel; the spec's
  "formulation" collides. Repo convention: **formulation** = one (scenario, climate,
  regime) design point (manifest column `formulation_id`, dirs `runs/<formulation_id>/`,
  `formulation_meta.json`); **cell / planning unit** stays reserved for pixels. Applied to
  notebooks 11–13 and the logs going forward; the spec's own wording is flagged for the next
  chat revision. The rename REVIEW flushed two latent reference-formulation bugs, both fixed:
  the Gate-2b directory (`runs/s0_ssp585_theta5`, renamed → `runs/s0_ssp585_theta5`)
  would not have matched the manifest id, so 12 would have re-solved the reference's MGA; and
  its meta file (`gate2b_meta.json`) was not the name 13 reads — 12 now derives
  `formulation_meta.json` from it once. Notebook 10's path constant updated for the rename.
- **M5.11** **E11 layer-consistency bug, caught by the designed self-check (2026-09-01).**
  The Δ(s,s′) recomputation initially measured macrorefugia captures on the canonical (585)
  layer for ALL formulations; ssp245 objectives are defined on the 245 realization, so every
  ssp245 diagonal came out positive (up to 3.9e-2) while every ssp585 diagonal was exactly 0 —
  the diagonal self-check localized the bug precisely. Fixed (per-formulation layer selection
  in `objective_of`); corrected diagonal ≤ 9.3e-6, which simultaneously validates the whole
  capture-based objective reconstruction. E11 CSVs + F10 regenerated; notebook 13 patched.
- **M5.10** **JSON-precision incident + rule (2026-08-30).** `08_gate2a_pilot`'s
  `jsonlite::write_json` (default `digits = 4` — significant digits, not decimals) silently
  truncated every numeric in `scenarios_v2.json`; the Gate-3 freeze then failed loudly
  (doubled-scenario block shares read 0.1667×3 + 0.5 = 1.0001, tripping `scenario_weights`'
  sum-to-1 assert — the guard did its job). Fixes: (a) scenarios_v2 regenerated at full
  precision from scenarios_v1 (repair note in its `_meta`); (b) the R writer now passes
  `digits = 10` (rule: any R cell serializing spec numerics must); (c) `11_gate3_freeze`
  re-normalizes shares/within-block on load (serialization residue at ANY precision — even
  6-decimal v1 sums to 1.000001 — is recovered to the exact intended fractions; a >5e-3
  deviation still stops as real corruption). DISCLOSED consequence: the Gate-2b anchor/MGA
  and the S4 pilot solved with the 4-digit weight vectors — ≤1e-4 relative weight
  perturbation, within every tolerance in use (anchor matched iter9's optimum inside the
  1e-3 assert); the frozen manifest carries the full-precision derivation. (pre-registered, frozen in 10_gate2b_analysis BEFORE
  the MGA run).** Statistics per spec §4, over anchor + k members at g=5%, discretionary cells
  only, m_disc = anchor's discretionary selection: **D** = max pairwise Hamming/(2·m_disc)
  (achieved band diameter; measured under a MAXIMIZING probe, so small D = narrow in every
  direction), **C** = share of m_disc selected in ALL solutions (f=1 robust core).
  PLATEAU-RICH iff D ≥ 0.10 AND C ≤ 0.90 → Gate 3; NEAR-UNIQUE iff D < 0.02 OR C > 0.98 →
  "S0 essentially unique within g" (strong negative; pivot to Claims B+C); else INTERMEDIATE →
  chat. Conditional-cell % reported for continuity but NOT ruled on (MGA inflates it by
  construction). Rule hash recorded in the cell audit per spec §9. (2026-08-28)

## 5. Solver configuration and numerical integrity

- **M5.1** Gurobi 13.0.2, nonprofit WLS licence (16 cores; needs live internet during solves;
  2 concurrent sessions max → ensemble formulations run serially). HiGHS 1.x for LP twins.
- **M5.2** `opt_gap = 1e-4` standard for single-solution solves (adopted after validation: the
  exact optimum was reachable in 17 s). The POOL gap g (2–10%) is a separate, deliberately
  loose parameter — it defines the near-optimal set that IS the estimand.
- **M5.3** `numeric_focus = TRUE` (Gurobi NumericFocus 2) engine-wide.
- **M5.4** **The false-certificate vignette (report in methods):** without NumericFocus, on the
  pre-threshold stack, Gurobi's root LP mis-converged 0.42% above the true optimum on the a4
  arm and CERTIFIED the wrong point (best bound = incumbent, gap 0.0000%), bit-identically
  across two runs. Caught because the integral LP twin pins the true optimum exactly (5.158146
  vs the "proven" 5.179758); model audit confirmed the intended affine-equivalent pair
  (objective reconstruction matches Gurobi to 6e-13). Cause: matrix range [1e-11, 1e5]. With
  NumericFocus the same solve found the exact optimum in 17 s — 60× FASTER (the un-focused
  simplex was numerically lost, not working hard). a0–a3 audited healthy against LP bounds
  (+3e-5..4e-4). Fix layered with M2.5. Diagnostic archive: iter8_y2y_a4_pullcheck_v2 (false
  proof) + _v3 (fix proof) + iter7 LP arms.
- **M5.5** **LP-twin methodology (stated, not luck):** an exactly solvable LP relaxation is kept
  beside every certified MILP. It caught (a) the false certificate, (b) the HiGHS presolve
  pathology (a targeted LP took 71 min on HiGHS presolve vs 24–81 s on Gurobi — solver path,
  not problem hardness).
- **M5.6** Engine-level compatibility fixes (disclosed for reproducibility): Gurobi 13 renamed
  pool solution vectors `xn` → `poolnx`, breaking prioritizr 8.1.0's gap portfolio — shimmed;
  portfolio `solve()` returns a list of rasters — stacked. Pool path verified toy-scale; first
  1 km pool run is Gate 2.
- **M5.7** **Solver provenance recorded in run_summary (engine change, 2026-08-27).** prioritizr
  attaches per-solution `objective/status/runtime/gap/objbound` attributes to `solve()`'s return,
  which `pr_solve`'s `terra::rast()` stacking silently discarded — so NO objective value was on
  record for the whole Gate-0 era. `pr_solve` now harvests them before stacking and
  `pr_write_outputs` writes them as `run_summary$solver_provenance` (optional block; absent on
  older runs). Toy-verified on all three branches (HiGHS LP, Gurobi single, Gurobi pool n=3 —
  per-solution objectives recorded). Matters for Gate 2+: the pool's objective span vs its 5%
  gap is a headline estimand check, cross-validated in 07 against objectives recomputed exactly
  from the per-solution representation CSV.
- **M5.8** **MGA machinery (`mga_core.R`, toy-verified 2026-08-28).** prioritizr cannot
  constrain its own objective, so the estimator works on the COMPILED model
  (`prioritizr::compile` R6 object; pu variables are columns 1..n_pu, locked-in = lb 1):
  one appended row `obj0·x ≤ (1+g)·z*` is the band wall; each iteration swaps in a LINEAR
  max-sum-of-Hamming distance objective (minimize Σ_j (2·count_j − n_inc)·x_j over
  discretionary pu columns) plus a **+1e-3·obj0 term that pins shortfall variables to their
  true minimum**, making each member's recorded band LHS its REAL objective (honest
  per-solution certificate; distance distortion ≤ ~6e-3 of one Hamming unit). Direct
  `gurobi::gurobi` calls mirror prioritizr's own solver construction (LC_CTYPE workaround,
  binary rounding, NumericFocus 2, Presolve 2); warm starts from the previous member.
  Estimator parameters (frozen in gate2b_meta): MIPGap_dist 0.01, TimeLimit_iter 900 s
  (a time-limited iterate is KEPT if feasible — it is a diversity probe, not a certificate).
  Toy-verified end-to-end: anchor == prioritizr's own solve; all band certificates hold;
  0-target absence; locked preservation; raster round-trip.

## 6. Findings register (results the paper reports; with provenance)

- **M6.1** Carbon dominance under equal weights: 39.7% of achievable swing; capture 1.52×/1.39×
  area share; control (penalty-free, 1/v) capture 54.2%/41.3% — dominance grew under the
  cleaner formulation.
- **M6.2** Gate-0 reallocation (a1 vs a0): m_soc −21 pts to its 0.332 target; biomass **+8.4**
  (weight-levered leak — S0 block-design input), birds +2.2, mammals +1.6, macrorefugia +1.1,
  connectivity +0.2, corridors −1.4 (the spec's predicted destination was corridors — partly
  refuted). a2 (both pools 0.30) lifts under-served EFGs 0.22 → 0.53. Map movement: Jaccard vs
  control 0.78 / 0.63 / 0.79 (a1/a2/a3).
- **M6.3** Morris (superseded era, kept for lineage): μ* predicted by leverage (+0.922);
  screening's real yield was the mechanism; Sobol' dropped by reasoned gate (σ contaminated by
  the V-shaped distance metric; cost re-measured 7–51 days).
- **M6.4** Footprint bias (disclosed limitation): the optimizer's NEW selections average gHM
  0.074 vs 0.055 for land passed over; whole-solution figures look intact only because locked
  PAs sit at 0.022. Mechanism: AOH richness correlates with gHM at +0.636/+0.607 and intactness
  (1% of swing) cannot counterweight. Left uncorrected by decision; footprint-as-cost named as
  future formulation change.
- **M6.5** Degeneracy status: OPEN. The 68k-cell a4-vs-a0 divergence was numerics artifact
  (exact solves agree exactly); remaining plateau evidence = LP-vs-MILP swaps ~2% of cells at
  ≈equal objective. Gate 2's pools are the real test; §2.8's prediction is weakened.
- **M6.6** **Gate-2 mechanism finding (2026-08-27): a k-best solution pool does not sample the
  g-band.** Gurobi PoolSearchMode=2 returns the k BEST solutions; on S0 the plateau at the
  optimum is so dense (≥50 distinct solutions within 3.2e-6 relative of optimal, differing by
  a handful of cells) that the pool never leaves the optimum's neighborhood — PoolGap=5% acts
  as a bound, never as a sampling target. Consequence: the within-formulation frequency estimand as
  operationalized (spec §4 via `add_gap_portfolio`) measures "indicator of the optimum", not
  "membership across the g-near-optimal set". This is E5's enumeration-order-bias concern,
  demonstrated maximally, and is the substance of the Gate-2 pivot decision. Candidate
  re-operationalization: Brunel-style diversity-controlled generation (maximize Hamming
  distance from incumbents s.t. objective ≤ (1+g)·optimum), which at S0's 55 s/solve costs
  ≈ k × 1 min per formulation — affordable. Decision belongs to the chat (spec §2.9).
- **M6.7** **A total-capture target does not protect the dense tail (2026-08-27, first T1/E7
  reading).** In S0, m_soc lands AT its 0.332 target but only 43.5% of its θ-tail mass is
  selected — co-capture on cells chosen for other features satisfies the claim off-tail.
  Biomass likewise: tail capture 0.425 at w≈0.199 (vs 1.000 at w=1), refuting the pre-stated
  "high" expectation. The standing diagnostic surfaced exactly what it was built to surface
  (v0.9.1: "any scenario that abandons dense stands is reported, not buried"). If a dense-stand
  guarantee is wanted, it needs a tail-restricted formulation element (e.g. a θ-tail-masked
  carbon feature with its own target) — a design question for the chat, NOT patched silently.

## 7. Supersession log (things we did and then undid — the paper may need to say why)

| was | replaced by | why | when |
|---|---|---|---|
| `vmax − v` refugia orientation | `1/v` | additive flip destroyed leverage under sum-normalization | 2026-08-17 |
| neighbor penalty 1e-5 | post-hoc delineation | uncalibrated 3rd-ranked driver; 400× cost | 2026-08-17 |
| biomass target 0.066 | weight-levered (t=1) | R2 tail-mass criterion (protocol overrules hand treatment) | 2026-08-18 |
| w=1 with low targets (run r1) | w = t discipline | low target at w=1 raises pull 3–15× | 2026-08-18 |
| Sobol' (Phase 4) | baseline-anchored ensemble → this study | gate could not fire; contaminated σ; cost | 2026-08-17 |
| opt_gap 0.10 (LP-era, inert) | 1e-4 | MIP gap became live; effect sizes ~1–3% | 2026-08-26 |
| Gate-0 arms pre-threshold | re-solved on conditioned stack | matrix conditioning; single-generation record | 2026-08-26 |
| w = t discipline (Gate-0 arms) | block-budgeted (w,t) via two-regime swing | w=t is itself an influence profile (gave biomass ~29% of swing); Gate-0-only isolator | 2026-08-27 (spec v0.9) |
| E5 HiGHS-shuffle arm | Gurobi pool vs Brunel-style, both 1 km | HiGHS cannot solve the 1 km binary MILP; open-verification story = LP twins | 2026-08-27 (spec v0.9) |
| Claim C `w = influence/leverage` | two-regime swing everywhere | linear-arm special case only; wrong for satiating features | 2026-08-27 (spec v0.9) |
| k-best pool estimator (add_gap_portfolio) | MGA max-Hamming generation (`mga_maxham_v1`) | PoolSearchMode=2 never samples the g-band (M6.6); one k-best pool kept per cell as the uniqueness statement | 2026-08-28 (spec v0.10) |
| "weight sets depth, not order" (v0.9.1 rationale) | REFUTED — joint scoring lets competition invert within-feature hotspot preference | M6.7: biomass tail 0.425 at w=0.199; m_soc tail 0.435 with target binding | 2026-08-28 (spec v0.10) |
| E5 as an experiment arm | discharged by design (k-best-vs-MGA contrast = ensemble by-product) | M6.6 is the maximal demonstration | 2026-08-28 (spec v0.10) |
| pr_targets range guard (0,1] | [0,1] | t=0 = mathematically absent, carries the places axis | 2026-08-28 |
| HiGHS-produced LP twins (ensemble) | Gurobi-path twins + HiGHS spot-check ×2 cells | 109-min worst-case presolve pathology; open-verification = verifiable, not produced, without Gurobi | 2026-08-28 (spec v0.10) |
| S4 places locks (tails t=1.0 in every stack) | pure (w,t) + pre-registered pilot band ≥0.75 both pools; tails = contingency @ t=0.8 | targets are pressure, not locks; "a lot of the tail," not completeness; sufficient pull demonstrably captures tails | 2026-08-28 (spec v0.11) |
| v0.11 pre-authorized tail contingency (t=0.8) | RESCINDED — no tail features as separate values, ever, without a new decision; pilot failure → chat | Ethan's ruling: no separate tail values in the problem; knowledge kept as backup (M4.14) | 2026-08-28 |

*Maintainer note: entries M-numbered for stable citation from drafts. Update same-session, every
methods-relevant change. Last updated 2026-08-27 (Gate 1 build).*
