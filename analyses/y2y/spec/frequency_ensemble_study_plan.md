# Hierarchical Selection-Frequency Ensemble — Study Plan (Paper 1)

**Status:** v0.9.1 — Gate 0a and Gate 0 COMPLETE (all arms PASS, 2026-08-26/27). Audit classifications frozen; solver/data standards ratified; D1/D2/D4 resolved. Gate 1 next, with ONE pre-freeze diagnostic outstanding: biomass θ-tail capture from archived a1/a0 (zero solves) decides the carbon within-block split.
**Scope:** Single methods-forward paper. Value scenarios over PROACT-selected objectives aligned to Y2Y core mission (PROACT selected objectives; no weights/ranges were elicited). Demonstrates robustness of prioritization claims AND presents named forward scenarios (core-habitat-forward, connectivity-forward, biodiversity-forward, carbon-forward).
**Companion documents:** leverage/carbon-dominance analysis (§2 constraints); novelty verification report (§12 positioning); `gate0_reportback.md` (executed results this version ratifies).

## Changelog
- v0.9.1 — Carbon within-block split converted from a convention call to a diagnostic-driven decision: biomass θ-tail capture rate (from archived a1/a0, zero solves), decomposed into SOC-claim co-capture vs independent selection, selects among mass-proportional / equal-split / combined-total-carbon-feature escalation. Rationale recorded: weight sets depth not order (each feature's tail is first-bought at any positive w), so the design question is effective pull depth, not target-vs-no-target. θ-tail capture rate per feature adopted as a standing T1/E7 diagnostic with a pre-stated S0 expectation for biomass. Equal-within-block confirmed as default for connectivity and biodiversity pairs.
- v0.9 — Gate 0a/0 results ratified into the spec. (1) Audit table frozen as executed: m_soc concentrated-satiating (t=0.332); biomass REVERTED to diffuse-linear by the R2 tail-mass rule as predicted; connectivity discriminated on a_min (pinch-point spike, not a tail — a case the spec did not pre-call); AOH watch item resolved (no tail); intactness R3; EFGs 36 rare-attainable + 4 unsaturated disclosed. Card count corrected to 10 (8 features + EFG block + summary). (2) Numerics standards ratified (new §2.6): dust thresholding with per-feature drop disclosure; opt_gap 1e-4; NumericFocus 2; LP twin beside every certified MILP as stated methodology; false-certificate vignette promoted to supplementary methods. (3) D1 resolved: block-level influence budgeting — a block's discretionary share is allocated JOINTLY across its members in two-regime swing currency; the +8.4-pt biomass leak under w=t is the motivating measurement; w=t fenced as a retired Gate-0 diagnostic convention. (4) D2 resolved: S4 = θ relax 5×→3× (m_soc t=0.552); S4 reports realized block-influence ratio, not promised doubling. (5) D4 resolved: E5 HiGHS-shuffle arm dropped (HiGHS cannot solve the 1 km binary MILP); E5 = Gurobi pool vs Brunel-style at 1 km; LP-twin open-verification replaces the open-source story. (6) Climate axis corrected: SSP245 vs SSP585, both 2071–2100 (axis = emissions; top-30% Jaccard 0.574; 1/v dissolves the anchor problem). (7) D7 corrections 1–7 applied throughout: compute model (portfolios Gurobi-gated; 12 s was the LP), EFG capacity-vs-outcome wording, two-regime swing replaces linear-arm Claim C conversion everywhere influence is computed, Gate-0 pass criterion corrected (only BELOW target fails; co-capture may exceed — propagated to E7), degeneracy prior recalibrated to "unknown" with Gate 2 decisive and the fail branch live. (8) E9/E10 marked partially discharged (log1p flips m_soc class 0.884→0.486 = E9 screening evidence; θ=3×/10× targets are archive lookups). (9) a0 dominance worsening (45.5%→54.2% after penalty removal + 1/v fix) recorded as motivation: hygiene fixes do not substitute for influence accounting.
- v0.8 — §2.5 amended pre-execution: transform screening universal (adoption gated by R1 value-model test; per-cell vs portfolio concavity distinction binding); feature cards specified; E9 third arm (log-carbon).
- v0.7 — D3 resolved (option b); D2 deferred (30% only, budget-independent audit objects archived); D5 deferred (E6 INACTIVE, time-boxed if activated); licensing sequencing added.
- v0.6 — D7 signed off (EFGs locked foundation); D1 resolved (doubling only).
- v0.5 — D4 resolved: PROACT blocks confirmed — core habitat {macrorefugia}; connectivity {transboundary + corridors}; carbon {SOC + biomass}; biodiversity {AOH ×2}; representativeness {EFGs}. S1 renamed core-habitat-forward.
- v0.4 — No elicited weights: S0 = analyst-constructed equal-influence-per-block reference; the frequency surface (not any single map) is the deliverable.
- v0.3 — R2 tail-mass criterion; constants frozen: θ=5×, λ=0.10, a_min=0.5%, t_min=0.15.
- v0.2 — §2.5 protocol + Gate 0a; (w,t)-pair scenarios; lever-selection principle; E8/E9/E10.
- v0.1 — Initial plan.

---

## 1. Purpose and contribution claims

The paper introduces and demonstrates, on the Y2Y prioritization, a two-level hierarchical selection-frequency estimand for exact-solver conservation planning, published together with an expressivity audit that distinguishes genuine value-robustness from structural inability to express values.

**Claim A (estimand).** Per planning unit i: F_i = (1/|S|) Σ_s f_{i,s}, where f_{i,s} is i's selection frequency within formulation s's near-optimal set (pool gap g), estimated from k_s pooled solutions. One vote per formulation; the vote is fractional. Novelty positioning per §12 (García-Quintas et al. 2025 full text remains the outstanding Gate 5 check).

**Claim B (expressivity audit).** A frequency surface is interpretable only alongside a per-feature influence decomposition and saturation status for every formulation cell. "Robust to values" and "structurally unable to express values" are observationally identical in F_i and mean opposite things.

**Claim C (influence-space scenarios) — CORRECTED v0.9.** Scenarios are specified as target influence profiles and translated to weights via the **two-regime swing**: a feature's influence currency is w·(min(cap_max, t) − cap_min)/t, which reduces to w × leverage on the linear arm (t ≥ cap_max) and caps at the target's claim for satiating features. The v0.2 formula w = influence/leverage is the linear-arm special case and is used NOWHERE influence is computed for satiating features. Caveat retained: the translation ignores competition and spatial correlation; it is first-order calibration, verified against realized influence per cell, iterated once if the miss is large.

Applied payoff (Discussion, not a claim): the frequency surface feeds post-hoc corridor/compactness delineation, replacing the removed boundary penalty. Delineation is out of scope (§14).

## 2. Constraints and measured facts (updated v0.9)

1. **Objective family is linear in captured fraction:** influence follows the two-regime swing under min_shortfall/max_utility/min_set. Only weights, targets, and feature definitions are real levers.
2. **Dominance is worse than the design-era numbers.** The a0 control (no carbon treatment, w=t) captures m_soc at **54.2%** (1.8× area share) — up from iter6's 45.5% — because two hygiene improvements (compactness-penalty removal, macrorefugia 1/v fix) each freed the optimizer to chase carbon harder. Motivating sentence for the paper: hygiene fixes do not substitute for influence accounting.
3. **Lever-selection principle (validated by a4):** for an attainable target, the target sets the magnitude of the claim; weight sets only priority below target. a4 (connectivity w=t=0.6, unreachable) reproduces a0 **exactly — 0 of 1.27M cells differ** — the empirical proof on exact certificates.
4. **Targets bind at the kink to four decimals** (a1: m_soc 0.3320; a2: both pools 0.3000; a3: 0.4000). **Corrected pass criterion: only capture BELOW target fails.** Co-capture can carry a weight-levered or satiating feature above its target (historical w=1 run: biomass 0.259 vs t=0.066); overshoot is an expected observation, not an anomaly. Propagated to E7.
5. **Saturation is capacity, not outcome.** 36/40 EFGs CAN saturate within budget (rare-attainable class); which DO saturate is per-cell and solve-dependent (5 did in iter6). E7 verifies outcomes; the audit classifies capacity.
6. **Intactness is R3-inexpressible** (leverage 0.042); published as a Claim B finding per D3(b), with mechanism (right-skewed gHM) and measured cost (new selections mean gHM 0.074 vs 0.055 passed over; AOH–footprint correlation +0.636/+0.607).
7. **w = t is a RETIRED diagnostic convention.** It equalized pull per proportional point so Gate 0 isolated stopping points. It is itself an influence profile and MUST NOT leak into Gate 1: S0 weights come from block accounting (§3.1) and will not satisfy w = t.
8. **Compute model (corrected):** the 12 s figure was the LP prototype. Production solves are binary MILP on Gurobi: a0/a4 ≈ 17–20 s with NumericFocus 2; target-constrained arms ran 81 s – 21 min. ALL portfolio methods are Gurobi-gated (shuffle/cuts need binary solves HiGHS cannot do at 1 km). Ensemble cost model ≈ cells × one MILP-with-pool; pool cost at 1 km is UNMEASURED — Gate 2's first act measures it. Gurobi WLS allows 2 concurrent sessions ⇒ cells run serially.
9. **Degeneracy prior recalibrated to UNKNOWN.** The 68k-cell a4-vs-a0 divergence was numerics artifact; exact solves reproduce exactly, so the certified optimum is (near-)unique at opt_gap 1e-4. But Claim A's estimand lives in the g=5% near-optimal set — a vastly larger object; the only plateau peek so far (LP-vs-MILP ~2% swaps at ≈equal objective) is at ~1e-4-equivalent looseness. Gate 2 is decisive, not confirmatory; the fail branch is LIVE. E4's g-grid doubles as the plateau-width measurement.

## 2.5 Feature characterization protocol — EXECUTED; classifications FROZEN (2026-08-26)

Constants as frozen v0.3: θ=5×, λ=0.10, a_min=0.5%, t_min=0.15. Battery run on the final dust-thresholded stack; classifications invariant to the conditioning change. Rules R1–R4 as amended v0.8 (universal transform screening; value-model adoption test; per-cell vs portfolio concavity distinction — carbon categorically fails per-cell concavity; identity retained for AOH with the alternative documented).

| feature | leverage | θ-tail area | implied target | class → lever |
|---|---|---|---|---|
| carbon m_soc | 0.884 | 4.06% | **0.332** | **concentrated-satiating → target** |
| carbon biomass | 0.801 | 1.17% | 0.066 < t_min | **diffuse-linear (REVERTED by rule) → weight** |
| transboundary connectivity | 0.461 | 0.20% < a_min | — | diffuse-linear → weight (pinch-point spike, not a tail — rule discriminated an un-pre-called case) |
| climate macrorefugia (1/v) | 0.422 | 0.47% (fails a_min and t_min) | — | diffuse-linear → weight |
| climate corridors | 0.263 | no crossing | — | diffuse-linear → weight |
| AOH birds / mammals | 0.232 / 0.181 | no crossing (watch item resolved) | — | diffuse-linear → weight |
| gHM intactness | 0.042 | — | — | **R3 inexpressible (disclosed)** |
| EFG block (40) | — | — | — | 36 rare-attainable (capacity) + 4 unsaturated, disclosed |

Transform screening findings (panel D): log1p FLIPS m_soc to diffuse-linear (0.884→0.486) — E9's screening-level evidence that concave transforms destroy the concentration signal; log1p pushes AOH birds below the expressivity floor (0.232→0.059). No transform adopted beyond the standing 1/v orientation fix; all declines documented per card.

Feature cards: **10 pages** (8 continuous features + EFG block + summary; earlier "12 cards" was a miscount) rendered pre-solve, reviewed, archived in `audit/feature_cards/`. Budget-independent objects archived per D2-deferred: targets at any θ or budget are npz lookups (verified: θ=3× → 0.552; θ=10× → 0.120).

## 2.6 Numerics and solver standards (RATIFIED v0.9 — methods-grade)

1. **False-certificate finding (supplementary vignette, promoted):** Gurobi twice issued a bit-identical FALSE optimality certificate on a4 (root LP mis-converged 0.42% high; best bound = incumbent at the wrong point). Cause: matrix range [1e-11, 1e+05] from resampling dust against shortfall scaling. Caught only by the integral LP twin pinning the true optimum. Framing: certified near-optimal sets are only as good as the numerics beneath the certificate; we document one false certificate, its cause, and the two-layer fix.
2. **Dust thresholding (pre-processing rule):** cells holding <1e-9 of a feature's total → 0 (biomass 46,097 cells / 0.0015% of mass; m_soc 19,262; connectivity 538; others clean). Matrix range now [1e-4, 1e5] every log. Audit invariant. Per-feature drop disclosure is the methods text.
3. **Solver standards:** opt_gap 1e-4 for single-solution solves (pool gap g is a separate, deliberately loose estimand parameter — now cleanly anchored by exact certificates); NumericFocus 2 engine-wide (also 60× faster on a4: 17 s vs 1080 s — careful arithmetic beat a numerically lost simplex); **an LP twin beside every certified MILP is stated methodology** (caught the false certificate and the earlier HiGHS presolve pathology). Open-verification sentence: every certified solution's LP twin is independently verifiable without a Gurobi license.
4. Environment shims (repo-level, disclosed): Gurobi-13 pool field rename (`xn`→`poolnx`) shimmed for prioritizr 8.1.0; portfolio `solve()` list-return stacked by the engine. Pool path verified toy-scale only; first 1 km pool run is Gate 2.

## 3. Formulation space

### 3.1 Value scenarios (influence-space, block-budgeted — D1 RESOLVED v0.9)

Every scenario is a complete (weight vector, target vector) pair. Levers follow §2.5's frozen classes: targets for concentrated-satiating (m_soc only), weights for diffuse-linear.

**S0 is an analyst-constructed equal-influence-per-block reference over PROACT-selected objectives.** No weight vector carries stakeholder endorsement; the frequency surface, not any single map, is the deliverable. **Block-level influence budgeting (binding, v0.9):** each block's equal discretionary share is allocated JOINTLY across its members in two-regime swing currency (Claim C). For the carbon block: m_soc's target claim plus biomass's weighted influence together equal the block share — biomass's S0 weight therefore lands well below pull-parity. Motivating measurement: under the retired w=t convention, demoting m_soc alone leaked +8.4 pts of freed budget into biomass (0.41→0.50 capture) — the leverage problem reappearing inside a block; block accounting closes it by construction, and the paper reports the leak as why block accounting is not optional. Because SOC and biomass are spatially correlated, co-capture blurs allocation: realized block influence is verified per cell, intended-vs-realized gaps reported in T1, biomass weight iterated once if the miss is large.

**Within-block split (v0.9.1 — OPEN, decided by diagnostic before Gate 1 freezes weights).** Candidate conventions: (a) mass-proportional (regional carbon share ≈ 74/26 SOC/biomass), (b) equal (50/50), (c) SOC-priority-residual. Design intent to protect: dense biomass IS wanted — but a weight already buys each feature's tail first (within-feature preference is density-descending at any w; weight sets depth, not order), and SOC's locked claim co-captures overlapping biomass hotspots. Decision procedure: compute from the archived a1/a0 solutions, zero solves, the **biomass θ-tail capture rate** (fraction of ≥5×-mean biomass cells selected) decomposed into SOC-claim co-capture vs independent selection. Tail already captured → adopt (a), concern discharged with evidence. Tail escaping → shift the within-block share toward (b), documented as evidence-driven. Tail escaping under every reasonable split → escalate to the **combined total-carbon feature** (single tC/ha layer, both pools, one derived target; per-tonne logic of E9 extended across pools) as a documented post-execution amendment: one derived layer re-audited under unchanged frozen rules, disclosed as motivated by this diagnostic; counterweight acknowledged (pools differ in irrecoverability semantics, vulnerability timescale, data provenance — the original reason for two features). Multi-member blocks elsewhere (connectivity, biodiversity) split equal-within-block as the default convention. **Standing diagnostic adopted: θ-tail capture rate per feature joins T1/E7 for every cell**, with a pre-stated S0 expectation for biomass — any scenario that abandons dense stands is reported, not buried.

Blocks (PROACT hierarchy, confirmed v0.5): core habitat {macrorefugia}; connectivity {transboundary, corridors}; carbon {m_soc target + biomass weight}; biodiversity {AOH birds, mammals}; representativeness {EFGs — locked adequacy foundation outside the scenario axis, 4 unsaturated disclosed}. Equal discretionary influence divides among core habitat, connectivity, biodiversity, and carbon-block-remainder per the joint accounting.

| ID | Scenario | Lever(s) | Definition |
|---|---|---|---|
| S0 | Balanced (reference) | Full (w, t) pair | Equal discretionary influence per block via joint block accounting; m_soc t=0.332 |
| S1 | Core-habitat-forward | Weights | Core habitat block share doubled from S0; others scaled down proportionally |
| S2 | Connectivity-forward | Weights | Connectivity block share doubled. Carroll static-layer disclosure attaches here |
| S3 | Biodiversity-forward | Weights | Biodiversity block share doubled; mandatory gHM audit |
| S4 | Carbon-forward (D2 RESOLVED) | Target (m_soc) + weight (biomass) | **θ relax 5×→3×: m_soc t=0.552** (@9.8% of region, archive lookup) + biomass block-share adjustment. Same derived-rule axis as S0 (θ is the dial; E10 stress-tests it). T1 reports S4's REALIZED block-influence ratio vs S0 — doubling is approximate for S4, exact by construction for S1–S3. The a0 control (54.2% capture) brackets extreme carbon-forward and is cited as such |
| S5 | Intactness-forward | R3-inexpressible per D3(b) | Published as expressivity finding; footprint-as-cost named as future formulation change |
| S1.5/S2.5 (optional) | Midpoints | Weights | Only if pilot shows cliff-like divergence between corners |

Every scenario ships with: intended influence profile; derived (w, t) pair; realized capture ratios; realized influence decomposition (two-regime swing); per-cell saturation verification (corrected criterion: only below-target fails); gHM audit (mandatory for S3).

### 3.2 Other axes (climate corrected v0.9 — D6)

| Axis | Levels | Crossing |
|---|---|---|
| Climate (emissions) | **SSP245 vs SSP585, both 2071–2100** (horizon fixed ⇒ axis means emissions). Macrorefugia 1/v re-derived per realization — orientation dissolves the shared-anchor problem (six realizations, leverage 0.422–0.516, no anchor parameter). Measured top-30% Jaccard between levels: 0.574 | Full cross with all scenarios |
| Carbon target regime | S0-level (θ=5×) vs S4-level (θ=3×) | S4 only, PLUS crossed subset {S1, S3} × carbon-forward for E3 attribution |
| Budget | 30% fixed (locked-in PAs count toward budget) | Fixed; multi-budget deferred (D2-deferred) |
| Solver gap | opt_gap 1e-4 (solve standard); pool gap g = estimand parameter | g fixed for main results; varied only in E4 |

Disclosure: climate corridors (Carroll 2018) are static and do not co-vary with the climate axis; the axis propagates climate uncertainty through macrorefugia only.

Cell count: 6 scenarios × 2 climate + 2 crossed carbon cells = **14 cells**. Cost = 14 × (one MILP-with-pool); pool cost measured at Gate 2; cells serial (WLS 2-session limit).

## 4. Estimand and aggregation rules

- Within-cell: f_{i,s} = selections of i among k_s retained pool solutions / k_s. Cross-cell: F_i = mean over cells, one vote per cell; never flat-pool k×N solutions (E2 demonstrates why). Fewer-than-k pools use what exists; the hierarchical mean is unaffected.
- g and k are reported estimand parameters; frequency claims are always "within g-near-optimal sets." opt_gap 1e-4 anchors the certificates beneath g.
- Bands (presentational): always ≥0.95 / frequent 0.70–0.95 / conditional 0.30–0.70 / rare 0.05–0.30 / never <0.05. Analyses use continuous F.
- Agreement between cells: overlap coefficient wherever selected-set sizes differ.

## 5. Expressivity audit (E7 — runs with every cell; first results section)

Per cell s, per feature f: two-regime swing influence, w_f, t_f, saturation OUTCOME (capacity per §2.5 is fixed; outcome is per-cell — capture ≥ target expected for some weight-levered features via co-capture; only below-target is a shortfall), realized capture ratio, **θ-tail capture rate (v0.9.1; pre-stated S0 expectation for biomass)**. Products: (1) live-feature map of the design (which features each scenario CAN move); (2) robust-vs-inexpressible demonstration (intactness invariant because inexpressible; a live feature showing genuine scenario response) — Claim B's figure.

## 6. Experiments

| ID | Comparison | Supports | Status / criterion |
|---|---|---|---|
| E1 | Hierarchical F vs naive one-solve-per-cell | Claim A motivation | Expectation RECALIBRATED (§2.9): prior on effect size is unknown; Gate 2 decisive. Bias map F_hier − F_naive; report magnitude + spatial structure |
| E2 | Hierarchical vs flat pooling | Claim A semantics | Divergence where pools return unequal k |
| E3 | Variance decomposition: scenario vs climate vs carbon-regime vs within-cell | Attribution | Per-region attribution maps; within-cell share quantifies degeneracy's part of "conditionality" |
| E4 | F at g ∈ {2%, 5%, 10%} × k ∈ {10, 30, 50}, diagnostic cells | Estimator behavior + plateau width | Convergence in k; g-flattening documented; doubles as plateau-width measurement per §2.9 |
| E5 (RE-SCOPED v0.9) | Gurobi pool (PoolSearchMode=2) vs Brunel-style dissimilarity-controlled generation, both 1 km Gurobi | Enumeration-order bias vs diversity-controlled sampling, solver held constant | HiGHS arm DROPPED (cannot solve 1 km binary; licensing insurance moot). Open-science story replaced by LP-twin verification (§2.6.3) |
| E6 (INACTIVE) | Marxan summed solution | "25-year-old practice" objection | Deferred per D5; time-boxed if activated |
| E7 | Expressivity audit (§5) | Claim B | Corrected saturation language per §2.4–2.5 |
| E8 | Carbon-weight ×10 inertness demo at S0 and most-hostile cell | Lever-selection principle | a4 already proves the principle at Gate 0 scale; E8 confirms under S0/S4 weights |
| E9 (three arms; screening evidence in hand) | S0-protocol vs S0-influence-weights-100% vs S0-log-carbon-100% | Target lever over weights-only AND concave-transform fixes | log1p class-flip (0.884→0.486) is the screening-level result; solves confirm the per-hectare predictions: weights arm loses densest-decile capture; log arm WORST on carbon-per-carbon-hectare |
| E10 (partially discharged) | θ ∈ {3×, 5×, 10×} | R4 defensibility | Targets already lookups (0.552 / 0.332 / 0.120); only capture-shift solves remain |

## 7. Gates

**Gate 0a — COMPLETE (2026-08-26).** Classifications frozen (§2.5 table); cards reviewed; budget-independent objects archived.
**Gate 0 — COMPLETE, ALL ARMS PASS (2026-08-27).** Targets bind at the kink to four decimals; a4 reproduces a0 exactly (0/1.27M cells); freed m_soc budget mapped (biomass +8.4 [→ D1 block accounting], birds +2.2, mammals +1.6, macrorefugia +1.1, connectivity +0.2, corridors −1.4 — the corridors prediction was partly wrong and is reported as such); a2 lifts under-served EFGs 0.22→0.53; LP-vs-MILP tightness measured (Jaccard 0.97–1.00, deltas ≤1.4 pts). Corrected pass criterion applied.
**Gate 1 — S0 construction (NEXT).** Inputs all in hand: joint block accounting in two-regime swing currency (D1); climate layer build-out per D6 (orient both SSP realizations in 02); scenario (w, t) pairs derived for S0–S4; intended-vs-realized influence verification plan; T1 skeleton.
**Gate 2 — First 1 km pool run.** Reference cell, k=50, g=5%. Triple duty: pool-cost measurement, real degeneracy test (§2.9 — decisive), and E4 seed. Fail branch LIVE: near-binary within-cell frequency ⇒ pivot options (Claims B+C focus, or add a demonstration problem where the correction matters) decided HERE before Gate 3.
**Gate 3 — Manifest freeze + pre-registration.** Manifest per §9 incl. k, g, aggregation rule, corrected pass criteria, §2.6 standards; hashed and timestamped before the ensemble.
**Gate 4 — Full ensemble (14 cells, serial) + E1–E5, E7–E10.**
**Gate 5 — Write-up.** BLOCKING: García-Quintas et al. 2025 full-text dissection (author request to Brunel's group acceptable); Lehtomäki & Moilanen 2013 workflow skim (§12); fresh literature sweep at submission.

## 8. Compute plan (corrected v0.9)

Production = binary MILP on Gurobi WLS (2 concurrent sessions ⇒ serial cells). Observed single-solve costs: 17–20 s (unconstrained arms, NumericFocus 2) to 81 s – 21 min (target-constrained). Pool cost at 1 km unmeasured until Gate 2; ensemble budget = 14 × (MILP + pool), revised after Gate 2. LP twins accompany every certified MILP (§2.6). All portfolio methods Gurobi-gated; no open-solver fallback exists at 1 km — reproducibility story is the LP twin, not solver substitution.

## 9. Manifest schema

One row per cell: `cell_id`, `scenario_id`, `scenario_name`, `climate_level` (ssp245_2071_2100 | ssp585_2071_2100), `carbon_regime` (theta5 | theta3), `budget_pct` (=30), `weight_vector` (JSON), `target_vector` (JSON), `influence_profile_intended` (JSON, two-regime swing), `k_requested`, `pool_gap`, `opt_gap` (=1e-4), `numeric_focus` (=2), `dust_rule_version`, `solver`, `seed_policy`, `input_layer_hashes` (JSON), `created_utc`, `frozen` (bool). Companion: `manifest_freeze.sha256`. Post-freeze changes require a new manifest version + changelog entry; frozen cells are never edited.

## 10. Directory / file contract

```
project_root/
  spec/frequency_ensemble_study_plan.md      # this file
  spec/manifest.csv + manifest_freeze.sha256
  audit/feature_cards/<feature>.pdf          # 10 pages, frozen 2026-08-26
  audit/audit_objects/                       # budget-independent Lorenz/marginal npz (any-θ/any-B lookups)
  analyses/y2y/01_feature_audit ... 04_results   # Gate 0a/0 notebooks (executed)
  runs/<cell_id>/solutions.npz               # PU × k binary matrix
  runs/<cell_id>/cell_audit.json             # §5 outputs
  analysis/e1_bias/ ... analysis/e10_theta/
  figures/
  changelog.md
```

## 11. Figures and tables plan

F1 estimand schematic. F2 E1 bias map. F3 frequency surface with bands + always-core. F4 attribution small-multiples. F5 expressivity figure (Claim B). F6 convergence panels (E4). F7 pool-method comparison (E5, re-scoped). F8 marginal-density trajectories with θ crossings (from the archived audit objects). T1 scenario table (intended influence → (w,t) → realized capture + realized block-influence ratios; absolute shares; S4's realized ratio flagged). T2 feature characterization table (frozen §2.5). T3 expressivity summary incl. mission-selected-vs-implementable gap. Suppl.: numerics vignette (§2.6.1 — false certificate, dust rule, LP-twin methodology, 60× NumericFocus result), per-scenario gHM audits, E8–E10, manifest, feature cards. All maps ESRI:102008; CVD-checked ramps.

## 12. Positioning and citations (verify all DOIs before tracker entry)

- Formulation lineage: Jung et al. 2021 NEE (10.1038/s41559-021-01528-7). Foil for §2.5: Jung's "equal" carbon weight = sum of species weights — cardinality-normalization that recognizes equal-weights≠equal-influence but is blind to spatial structure; leverage completes the correction.
- Scenario-ensemble lineage extended from climate/data axes to value axes: Buenafe et al. 2023 (10.1002/eap.2852); Brito-Morales et al. 2022; Chapman et al. 2025 (10.1038/s41559-025-02671-1); Liczner et al. 2023 (10.1111/csp2.12994); Carpenter-Kling et al. 2025.
- Aggregate-solutions-not-inputs: Meller et al. 2014. Univariate-characteristics-drive-priorities anchor: Kujala, Moilanen & Gordon 2018 MEE (10.1111/2041-210X.12939) — post-hoc/solve-based; §2.5 inverts to ex-ante/zero-solve (leverage↔Morris μ* ρ=0.922). Partial precedents cited so the protocol reads as synthesis-plus-novelty: rarity-scaled targets (Rodrigues et al. 2004 lineage); Zonation benefit functions (Moilanen 2007; Arponen et al. 2005 — satiating shapes chosen a priori, not derived); Marxan Good Practices pre-analysis (QA, not influence prediction). Gate 5 skim: Lehtomäki & Moilanen 2013.
- Within-problem near-optimal lineage: Brunel et al. 2023 (10.1007/s10666-022-09862-1); prioritizr portfolios; Marxan summed solutions (Ball, Possingham & Watts 2009).
- Highest prior-art risk: García-Quintas et al. 2025 (10.1016/j.biocon.2025.111447) — Gate 5 blocking.
- Novelty sentence: "to our knowledge, no published conservation prioritization nests within-formulation near-optimal selection frequency inside a cross-formulation ensemble with per-formulation averaging."

## 13. Decisions

**All design decisions resolved or deferred.** v0.9 resolutions: **D1** block-level influence budgeting (binding; two-regime swing currency; +8.4 leak reported as motivation; w=t retired). **D2** S4 = θ 3× relax (t=0.552). **D4** E5 HiGHS arm dropped. Standing: D3(b) intactness finding; D7 EFGs locked; D1-tilt doubling only; constants frozen v0.3. Deferred: multi-budget (20/30/40/50 interest recorded; audit objects make re-derivation a lookup); Marxan E6 (INACTIVE, time-boxed if activated).

## 14. Out of scope (fenced)

Post-hoc corridor/compactness delineation (Discussion mention only). PROACT elicitation methodology (Laura's component). Eastern-slopes grizzly analysis. Budget stratification beyond the deferred multi-budget note. Sobol' analysis. Applied-paper full PROACT weight treatment.
