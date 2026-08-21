# Y2Y corridor-wide prioritization + uncertainty analysis — methods summary

Self-contained description of the corridor-wide pathway (notebooks `00` → `01` → `02` → `03a` →
`04a`) and the sensitivity/uncertainty analysis (`06`), as implemented on 2026-08-07. Written to
be pasted into a discussion thread: it states what was done, the parameter values actually used,
the results obtained, and the decisions that are still open.

> ## ⚠️ SUPERSEDED IN PART — 2026-08-17 redesign, not yet re-solved
>
> Everything below describes the **`iter6_y2y` configuration and results**. A redesign was agreed
> on 2026-08-17 and the code is in place, but **02 has not been re-run and no new solve exists**,
> so the numbers here are still the current published ones. What changes when it is re-run:
>
> 1. **Leverage replaces Gini as the explanation of §6's Morris result.** *Leverage* = the range of
>    captured fraction the budget can span for a feature (richest 30% of PUs minus poorest). At
>    leverage ≈ 0 a feature's objective term is near-constant across every feasible selection, so
>    its weight multiplies a constant and cannot move the answer. It reproduces the μ\* ranking at
>    **Spearman +0.922 with zero solves**, and `w_f × leverage_f` decomposes the objective exactly:
>    EFGs 24.6%, mineral-soil carbon 22.6%, biomass carbon 20.5%, connectivity 11.8%, corridors
>    6.7%, birds 5.9%, mammals 4.6%, macrorefugia 2.3%, intactness 1.1%.
> 2. **Macrorefugia orientation `vmax − v` → `1/v`.** The additive flip did not cancel under §4's
>    sum-normalization and destroyed 75% of the layer's leverage (0.353 → 0.090) — §6 ranked it
>    last on an artefact of preprocessing. `1/v` restores it to 0.422. Expected to move from 12th
>    to ~3rd–4th. (`1 − gHM` does the same to gHM, 0.742 → 0.042 — see item 5.)
> 3. **Carbon demoted by per-feature targets, not weights.** Under min-shortfall a feature that
>    reaches its target stops competing for area, and the objective is linear so the solver already
>    takes the densest cells first — a low target is therefore "grab the hotspots, pass over the
>    mediocre pixels". Targets are *derived* from the rule "keep taking cells while marginal density
>    ≥ 5× the regional mean": mineral soil **0.332**, biomass **0.066**. Everything else stays 1.0.
> 4. **The compactness penalty is removed from the optimizer** (`NEIGHBOR_PENALTY = 0`) and
>    delineation moves post-hoc. It was uncalibrated yet §6's 3rd-ranked driver, relocated a third
>    of the map, was not creating the clustering (the unpenalized solution is already 66.6%
>    clustered by area), and cost **400× the solve time** — 1 km runs in **12 s** without it versus
>    4,826 s with it.
> 5. **A measured bias is now reported rather than fixed** (§7 gains an item): the new selection is
>    **more human-modified than the land it passes over** (mean gHM 0.074 vs 0.055), because
>    intactness holds ~1% of the objective's swing and cannot counterweight AOH richness, which
>    correlates with gHM at ≈ +0.62.
> 6. **Phase 4 (Sobol') is dropped** — see the revised §7 item 7.
>
> §6's Morris table must be re-derived after the re-solve; the leverage table predicts the new
> order. Nothing in §§1–3 (inputs, grid, preprocessing) changes except the macrorefugia
> orientation.

Out of scope here: the two sub-regional prioritizr analyses (`03b` northern IPCAs, `03c` Alberta
foothills) and the standalone least-cost corridor analysis (`05`).

---

## 1. What the analysis is

A systematic conservation-prioritization framework for the Yellowstone-to-Yukon region. The
question it answers is: **given a fixed area budget, which 30% of the Y2Y region best captures the
full value of every conservation input simultaneously?** Existing protected areas are locked in
and counted toward the budget, so the operational output is *where the next increment of
protection should go*.

It is an **application** paper, not a methods paper. The optimizer (`prioritizr`) and the
sensitivity method (Morris screening) are both standard; the contribution is the integrated
input stack over this region plus a robustness treatment.

Pipeline: `00` download → `01` inventory → `02` align to a common raster stack → `03a` optimize
(R) → `04a` interpret (Python) → `06` sensitivity analysis (re-solves the same problem many times).

The Python→R hand-off is a directory of aligned COGs plus `manifest.json`, an explicit contract
carrying every layer's role/dtype/NoData/orientation and every run parameter. The R→Python
hand-off is GeoTIFFs + CSV/JSON. `config.py` is the single source of truth for all parameters;
no notebook hard-codes any.

---

## 2. Input data (8 continuous features + 40 categorical + cost)

All layers are oriented so that **higher value = more conservation value** before they reach the
optimizer. No normalization at the data stage (that happens inside `03a`); no winsorizing.

| Feature | Source | Native res | Orientation applied |
|---|---|---|---|
| `human_modification` | Theobald *et al.* gHM v3, Y2Y asset v202606 (downloaded from GEE in `00`) | ~90 m | `1 − gHM` → **intactness** |
| `transboundary_connectivity` | Pither *et al.* omnidirectional connectivity (raw current density) | ~300 m | raw (more = better) |
| `climate_corridors` | Carroll *et al.* 2018 current-flow centrality | ~5 km | raw |
| `climate_type_macrorefugia` | AdaptWest CMIP6 **backward climatic velocity**, 8-GCM ensemble, SSP585 2071–2100 | 1 km | `vmax − v` → **refugial value** (low velocity = macrorefugium) |
| `irrecoverable_carbon_biomass` | Berman/McDowell irrecoverable carbon, biomass pool (t/ha) | ~1 km | raw |
| `irrecoverable_carbon_m_soc` | same, mineral soil organic carbon (t/ha) | ~1 km | raw |
| `irrecoverable_carbon_sl_soc` | same, subsoil organic carbon | ~1 km | **excluded from the solve** (kept in the stack) |
| `aoh_richness_mammals` | Lumbierres *et al.* AOH species richness, "all" species (not Red List) | ~100 m | raw |
| `aoh_richness_birds` | same, birds | ~100 m | raw |
| `iucn_efg` (×40) | IUCN Global Ecosystem Typology, Ecosystem Functional Groups Level 3 | ~1 km | recoded `major=2 / minor=1 / absent=0` |

Plus: `cost_uniform` = 1 everywhere (so "cost" is literally area), and
`mask_protected_areas` = 509 existing PA polygons rasterized (the lock-in mask).

**Notes on the two subtler layers.**
- *Backward climatic velocity*: distance from a cell's future climate to its nearest present-day
  analog, per year, with analogs matched by PCA over 11 ClimateNA variables. Low = the future
  climate already exists nearby = macrorefugium. Its km/yr units are a per-year **average over a
  horizon-dependent denominator**, so the 2071–2100 layers divide by a longer span than
  2041–2070 — late-century values are diluted, not simply more extreme. (This is why SSP245 is
  nearly flat across horizons: 1.995 → 1.998 km/yr regional mean.)
- *EFGs*: 109 rasters were warped; the 40 with any presence inside the corridor were kept. The
  `major=2 / minor=1` recode means the optimizer weights major occurrences above minor ones.

Deliberately **not** used: a separate urban/converted mask (gHM-derived intactness already
down-weights converted land), `bhi_beri_parc`, `elevational_diversity`.

---

## 3. Preprocessing (`02`) — the aligned stack

**Target grid: ESRI:102008 (North America Albers Equal Area Conic), 1 km, Y2Y boundary buffered
20 km.** 1 km was chosen because most inputs are natively ~1 km, so it minimizes resampling
distortion while keeping the LP tractable over the full corridor. The accepted ceiling for a
later iteration is 300 m, not 100 m.

Two stages:

1. **Warp** — one streamed `gdalwarp` reproject + resample + cutline-clip per layer, reading only
   the Y2Y window so global rasters are never warped in full. Resampling rule: finer than 1 km →
   `average`; coarser/≈1 km → `bilinear`; categorical (EFG) → `nearest`.
2. **Orient → mask → QA → COG** — apply the orientations in the table above; build **one planning-
   unit mask** = cells valid in *all* continuous features, applied identically to every feature and
   to the cost layer, so no cell is valid in one layer and NoData in another (EFG `0`=absent is a
   valid value, so EFGs do not constrain the mask). QA surfaces problems rather than silently
   transforming: carbon tail cells above p99.9 are flagged for inspection, connectivity quantiles
   are printed and capped only if a knob is set (it is not).

**Result: a 1286 × 3312 grid with 1,272,914 planning units** (≈1.27 M km²), 9 continuous features
+ cost + PA mask + 40 EFGs.

### 3a. Climate-scenario materiality QA (Phase 1a) — verdict MATERIAL

The macrorefugia entry uses one of six AdaptWest realizations (SSP 245/370/585 × two horizons).
That unstated pick is an obvious review target, so before spending six 1 km solves on it, `02`
warps all six and measures whether the choice is decision-relevant. The decision rule was
**pre-registered in `config.py` before the numbers existed**.

Headline statistic = top-30% Jaccard (overlap of the most-refugial 30% of planning units), because
correlation alone is necessary but not sufficient — two surfaces can correlate at 0.95 and still
disagree about which cells make the cut.

Results across the 15 scenario pairs:
- worst pair: SSP245 2041–2070 vs SSP585 2071–2100 → **Jaccard 0.460**, Spearman 0.631
- best pair: SSP245 2041–2070 vs SSP370 2041–2070 → Jaccard 0.910, Spearman 0.991
- **41.9%** of the ever-selected set is in the top 30% under *all six*; the rest is scenario-dependent
- for scale: macrorefugia vs each *other* input scores **0.110–0.243** — that is what a genuinely
  different layer looks like

**Verdict: MATERIAL** (rule: any Jaccard < 0.60). By the pre-registered rule this means the
scenario should enter the sensitivity design as a factor, and Phase 1b (six full solves) is
warranted. **Neither has been done yet** — see §7, open item 1.

The comparison runs on raw velocity, since the `vmax − v` flip is monotone and leaves both
correlation and top-quantile membership unchanged. Candidate pooled p1/p99 shared anchors
(0.290 / 6.672 km/yr) are reported but **not applied**: adopting them changes the feature even in
the single-scenario case, because `03` sum-normalizes so an additive offset does not cancel.

---

## 4. Optimization (`03a`, R / prioritizr 8.1.0)

### Problem formulation

- **Objective: minimum shortfall**, with per-feature relative targets of **100%**, under an area
  budget of **30% of the region**. With a 100% target this is equivalent to *maximize the captured
  fraction of every input, balanced across inputs* — each feature is on a 0–100% scale, so no
  feature can dominate purely by having larger raw units. It is scale-invariant.
- **Budget: 30%** of 1,272,914 PU = **381,874 cells**. (This is the "30×30" framing.)
- **Existing PAs locked in and counted toward the budget**: 191,029 cells (15.0% of the region),
  leaving ~190,700 cells of genuinely new selection.
- **Normalization**: each feature sum-normalized to a total of 1e5 — a conditioning constant only
  (prioritizr's presolve wants targets < 1e6). min-shortfall is scale-invariant so this does not
  change the solution.
- **Weights**: each of the 8 continuous features @ 1.0; the EFG *group* shares a total of 1.0, so
  each of the 40 EFGs is @ 1/40. Without this the 40 EFGs would collectively outvote everything
  else 40:9.
- **Compactness: neighbour penalty @ 1e-5** — penalizes planning units with few selected
  neighbours (binary rook adjacency). prioritizr explicitly recommends this over a boundary
  penalty "for large-scale problems or open-source solvers", which is exactly the bind here. The
  boundary (perimeter) penalty was tried and works at 2 km, but its per-adjacent-pair
  linearisation blows the LP up (~1.3 M rows at 2 km) and is intractable at 1 km on HiGHS.
- **Connectivity penalty: OFF.** It was tested extensively in the sub-regional analysis and is the
  wrong tool for linking areas: it aggregates permeable land, it does not route A→B. Corridor
  routing moved to a separate least-cost analysis (`05`). The raw connectivity matrix also spans
  ~40,000× corridor-wide (a single-pixel pinch-point tail), so the penalty is uncalibratable
  without first capping that tail.
- **`irrecoverable_carbon_sl_soc` excluded** from the feature set (subsoil carbon; mineral soil is
  retained), on the grounds that the two soil pools are near-collinear.

### Solver

**HiGHS, interior-point (IPM), with proportion decisions.** This is a deliberate prototype
compromise and is the biggest methodological caveat in the pipeline:

- The *correct* formulation is binary (each cell in or out) — but the binary MILP chokes HiGHS
  presolve at 1 km.
- `proportion` decisions relax it to a pure LP, which HiGHS solves at full 1 km resolution. The
  returned solution is **~99.98% integral**, so a 0.5 cut is clean, but it is a relaxation, not a
  reserve.
- The intended real run is a **Gurobi MGA gap-portfolio** (`add_gap_portfolio`, 8 near-optimal
  alternatives within 10% of optimal), which would let the analysis present *a suite of equally
  good options* rather than one map. This is currently **blocked by a size-limited trial Gurobi
  license**; a free academic license would unblock it. Note the blocker is the *binary decisions*
  the portfolio requires, not the portfolio itself.
- `OPT_GAP = 0.10` is a *MIP* gap and is therefore inert for the LP.

**Solve: 4,826 s (~80 min) at 1 km**, single solution, 30.0% of region selected.

### Result (run `iter6_y2y`) — captured fraction of each input

| Input | Captured |
|---|---|
| irrecoverable carbon (mineral soil) | 45.5% |
| irrecoverable carbon (biomass) | 41.8% |
| transboundary connectivity | 31.1% |
| AOH richness — birds | 31.7% |
| AOH richness — mammals | 31.6% |
| climate macrorefugia | 30.4% |
| human modification (intactness) | 30.2% |
| climate corridors | 28.9% |
| EFGs (mean of 40) | 51.6% (range 26.7%–100%) |

Read against the 30% area share: carbon is captured well above area share (it is spatially
concentrated, so it is cheap to capture), climate corridors slightly below. Several EFGs are
captured at 100% simply because they are rare and small enough to fit inside the budget for free;
others sit at ~27%.

**Known caveat: min-shortfall at a 100% target structurally favours spatially concentrated
inputs.** Concentrated features (carbon) are cheap to capture and so get over-served; diffuse ones
are under-served. This is unresolved and should be stated in methods.

---

## 5. Results analysis (`04a`, Python)

Reads the solution back and produces:

- **Radar / representation plot** — captured fraction per input against a 30% area-share ring.
- **Allocation and existing-vs-new maps** — separating locked PAs from newly selected area.
- **Cluster decomposition** — the new selection (`selected & not-PA`) is split into connected
  components (8-connectivity, ≥25 cells). Six are profiled, chosen by **latitude spread**
  (the corridor split into 6 latitude bands, largest cluster in each) rather than by size,
  because the six largest all bunch at 51–60°N and miss both the US south and the Yukon north.
  Clusters are publicly named **"Option 1..N"**, north→south, and the map annotation, star plots
  and tables all use that same numbering so they cross-reference.
- **Value-profile star plots**, on three scalings that coexist:
  - *richness* — mean of each input within the area, scaled 0–1 over the region (5th–95th pctile)
  - *contribution* — % of the **full Y2Y total** of that input captured
  - *efficiency* — contribution per 1,000 km², on a shared axis across all areas
- **Benchmark block** — the same profiles for six named existing parks chosen for N→S spread
  (Nahanni, Spatsizi, Jasper, Banff, Glacier MT, Yellowstone), plus the proposed **Ross River
  IPCA** as a manual area. New-vs-existing profiles are effectively a gap analysis.
- **Consequences tables** — two column groups, "Alternatives (new options)" vs "Established
  Protected/Priority Areas", every cell printed at ≥2 significant figures.

Denominators for contribution/efficiency are always the **full Y2Y totals**, so "% of Y2Y" is
literally correct and comparable across analyses.

---

## 6. Uncertainty / sensitivity analysis (`06`)

`03a`/`04a` say *where* the priorities are; `06` says *what drives them*. It re-solves the same
problem 130 times under perturbed parameters and attributes the movement in the priority map to
individual factors. Framed as a **robustness section of an application paper**, not as a
methods contribution.

### Design principle

`config.py` stays the single source of truth for the baseline. Each run gets a **copy of
`manifest.json` with its `params` block patched**, written next to its own outputs. `config.py` is
never mutated per run. This keeps every perturbation an explicit delta in the design matrix, lets
concurrent solves run without shared state, and makes any single run reproducible in isolation
from the manifest sitting beside its results. The R driver (`run_one.R`) mirrors `03a` cells 1–9
exactly and holds no logic of its own.

Screening runs at **2 km** (aggregation factor 2, ≈1/4 the LP) while the headline stays 1 km.

### Three pre-registered gates, all passed

- **G1 — driver equivalence.** Does the headless driver reproduce the notebook? One unperturbed
  1 km solve vs the existing headline: identical planning units (1,272,914), identical budget
  (381,874), identical lock-in (191,029), **selected-set Jaccard = 1.000000**. ✅
- **G2 — scale transfer.** Do 2 km conclusions carry to the 1 km headline? Fresh 2 km baseline vs
  the 1 km solution, compared on the 2 km grid: **Jaccard 0.833** (pre-registered: >0.8 transfers,
  <0.6 does not). ✅
- **G3 — solver noise floor.** Morris effects are *differences between paired runs*, so if solver
  noise is the size of a real perturbation the whole ranking is noise. Ten identical solves at the
  same worker/thread configuration: **pairwise Jaccard 1.000000, per-cell allocation SD 0.000000,
  zero cells ever flip**. The floor is **exactly 0**, which is the correct answer rather than a
  broken gate: with proportion decisions this is an LP, HiGHS IPM is deterministic, and `OPT_GAP`
  is a MIP gap and therefore inert. A zero floor means **all downstream variance is attributable
  to inputs**. ✅

### Morris screening (Phase 3)

Elementary-effects screening over **12 factors**, `r = 10` trajectories × (k+1) = **130 solves**,
`num_levels = 4`, seeded. Factors are sampled in the space where they are naturally uniform:

| Factor | Range | Space |
|---|---|---|
| 8 continuous feature weights (one factor each) | ×0.25 – ×4 | log₂ |
| EFG group weight (applied to all 40 as one factor) | ×0.25 – ×4 | log₂ |
| `budget_pct` | 0.20 – 0.40 | linear |
| `target_pct` | 0.50 – 1.00 | linear |
| `neighbor_penalty` | 1e-6 – 1e-4 | log₁₀ |

Primary metric: **`dissim_vs_base` = 1 − Jaccard** of the selected set against the unperturbed 2 km
baseline. Secondary: captured fraction per feature (`held_*`), and `pct_region` as a deliberate
validity check.

Note that min-shortfall is scale-invariant in the weights, so scaling all nine weight factors
together is a **null direction** — it correctly shows zero effect, and this should be stated in
methods rather than left to be discovered.

### Validity self-check

Morris on `pct_region` (total selected area): `budget_pct` μ* = 20.0, **every other factor exactly
0.0**. Selected area tracks the budget and nothing else, exactly as it must. If any other factor
had moved area, the design or the manifest patching would be wrong.

### Headline result — what drives the priority map

μ* = mean absolute elementary effect (influence); σ = interaction/nonlinearity. Noise floor is
0.000000, so **every one of these effects is signal**. Dissimilarity range across the 130 runs:
0.221 – 0.550.

| Rank | Factor | μ* | ±95% | σ |
|---|---|---|---|---|
| 1 | weight: irrecoverable carbon (biomass) | 0.102 | 0.032 | 0.104 |
| 2 | `budget_pct` | 0.089 | 0.028 | 0.100 |
| 3 | `neighbor_penalty` | 0.071 | 0.031 | 0.079 |
| 4 | weight: irrecoverable carbon (mineral soil) | 0.071 | 0.024 | 0.072 |
| 5 | weight: EFG group | 0.045 | 0.021 | 0.049 |
| 6 | `target_pct` | 0.031 | 0.017 | 0.043 |
| 7 | weight: climate corridors | 0.023 | 0.011 | 0.031 |
| 8 | weight: transboundary connectivity | 0.023 | 0.012 | 0.031 |
| 9 | weight: AOH mammals | 0.011 | 0.006 | 0.015 |
| 10 | weight: AOH birds | 0.009 | 0.006 | 0.012 |
| 11 | weight: human modification | 0.007 | 0.005 | 0.010 |
| 12 | weight: climate macrorefugia | 0.003 | 0.003 | 0.005 |

> **Correction, 2026-08-07.** An earlier version of this table measured `dissim_vs_base` against
> row 0 of the Morris batch rather than the unperturbed baseline (`base_row=0` indexed the design,
> not the G2 run). That reference sat Jaccard 0.67 from the true baseline, which forced one-signed
> elementary effects for any factor whose reference level was at an end of its range, and moved the
> ranking — biomass carbon 3rd→1st, neighbour penalty 5th→3rd, `budget_pct` 1st→2nd. Fixed in
> `ensemble_core.add_baseline_metrics`; the table above is the corrected one, confirmed against a
> reference-free per-cell ranking that never uses a baseline.

**Confidence intervals overlap heavily — read tiers, not ranks.** The top four (0.071–0.102, CIs
±0.024–0.032) are not separable from each other. There are really three tiers: the two carbon
weights plus `budget_pct` and `neighbor_penalty`; then EFG group and `target_pct`; then everything
else, with macrorefugia the only factor whose interval includes zero.

**Influence is almost entirely explained by spatial concentration.** Ranking the eight continuous
layers by Gini coefficient reproduces the μ* ranking at **Spearman +0.905 (p = 0.002)**:

| Layer | μ* | Gini | share of total in richest 10% of cells |
|---|---|---|---|
| carbon — mineral soil | 0.071 | 0.74 | 56% |
| carbon — biomass | 0.102 | 0.65 | 39% |
| transboundary connectivity | 0.023 | 0.38 | 25% |
| climate corridors | 0.023 | 0.21 | 15% |
| AOH birds | 0.009 | 0.18 | 15% |
| AOH mammals | 0.011 | 0.14 | 14% |
| macrorefugia | 0.003 | 0.07 | 12% |
| human modification | 0.007 | 0.04 | 11% |

Intactness sits at Gini 0.036 — Y2Y is uniformly wild, so gHM-derived intactness barely
discriminates between cells and reweighting it cannot move the solution. Carbon is the opposite:
over half the mineral-soil total is in 10% of cells, so its weight strongly reorders which cells
win. **Morris is therefore measuring layer geometry, not ecological importance.** The robustness
claim should be stated with that mechanism attached: "the map is insensitive to how connectivity,
richness, refugia and intactness are weighted" is true, but *because those layers are too spatially
even to move a 30%-of-area selection* — a fact about the data, not a validation of the priorities.

**Read μ\* and σ; ignore μ.** `dissim_vs_base` is a distance from a reference, so the response
surface is V-shaped in every factor (moving toward the baseline lowers dissimilarity, moving past
it raises it). Signed μ only reports which side of the baseline the trajectory steps fell on. The
same V-shape inflates σ, which is why every factor lands at σ/μ* between 1.0 and 1.4 — that is
largely metric geometry, not genuine factor interaction.

**The baseline is not a design point.** With `num_levels = 4` the sampled levels are 0, ⅓, ⅔, 1 of
each range, while every baseline value sits at 0.5 (weight multiplier ×1, budget 30%, penalty
1e-5). Only `target_pct = 1.0` is sampled, as an endpoint. So 11 of 12 factors are off-baseline in
every run, and dissimilarity has a floor of 0.221. Valid for screening; but the absolute level
cannot be read as "how far plausible perturbations push the published map".

### Per-input view

For 7 of the 9 objectives, `budget_pct` is the top driver of how much of that input gets captured.
The two exceptions are self-consistent: mineral-soil carbon capture is driven by its own weight,
and EFG capture by the EFG group weight. Mineral-soil carbon weight is the *second* driver for
four other inputs, which again marks it as the layer that reorganizes the solution.

### Per-cell μ* maps

Morris is also run per grid cell, producing maps of *where* each factor decides. A trajectory
changes exactly one factor between consecutive runs, so the elementary effect is a simple
difference ratio; this is computed by a vectorised routine because ~300k SALib calls is
infeasible. It is validated by `cross_check()` against SALib on a scalar metric —
**max |difference| = 2.1e-17**.

### One batch failure worth reporting honestly

The first 130-run batch lost 19 runs to a 2-hour wall-clock cap, **18 of them silently**, because
the validity flag tested only "is the solution over budget" — and a timed-out solve usually stops
*under* budget, so it passed. Worse, the failures were not random: all 19 sat at the same
`budget_pct` level and fell inside only 2 of the 10 trajectories, which is exactly the
factor-correlated damage a Morris design cannot absorb.

Fix: the collector now flags `timed_out` (on the clock) and `over_budget` (on the area)
separately, reports *which trajectories* are affected, and `analyze_morris()` **refuses to run**
while any unusable run remains rather than analysing around the holes. The cap was raised to 6 h
and the 19 runs re-solved.

The diagnosis is worth stating because the obvious one was wrong: the re-solves took a **median
212 s** under identical parameters and identical solver settings — and a longer cap cannot make a
solve faster. So the stalls were **machine contention / memory pressure** from overlapping heavy
solves, not LP degeneracy at that budget level. Practical lesson: a wall-clock cap is a poor
convergence proxy because it conflates "hard problem" with "busy machine".

---

## 7. Open items and known weaknesses

1. **The climate-scenario factor is missing from the Morris design.** The Phase-1a QA returned
   **MATERIAL** against a pre-registered rule, whose stated consequence was "scenario enters the
   sensitivity design as a factor AND Phase 1b is warranted". It has not entered the design (it
   needs a shared-anchor orientation across all six realizations plus a headline re-solve, and was
   deferred). This is the clearest place where the analysis currently does not do what it
   pre-registered, and is the first thing a reviewer following the audit trail would find.
   Note that macrorefugia ranking last in Morris does **not** discharge this: Morris varies *how
   much you weight* a layer, the QA varied *which version of the layer you use*, and a different
   SSP/horizon changes the layer's spatial pattern rather than its weight.
2. **Proportion (LP) decisions, not binary.** The published map is a ~99.98%-integral relaxation of
   the true reserve-selection problem. Unblocking it needs a working Gurobi licence — still
   outstanding as of 2026-08-17, though the obstacle has changed: the size-limited trial was
   replaced by a "Gurobi Gives Back" nonprofit WLS licence, but that licence is capped at **8 cores
   while the workstation has 10**, so Gurobi refuses to initialise at all (`Error 10009`). Gurobi
   documents no programmatic workaround; a support request to raise the cap is pending.
3. **No portfolio of alternatives.** The MGA gap-portfolio — the mechanism for presenting *several*
   near-optimal options instead of one map — requires binary decisions, so it is blocked by the
   same thing. Given that the priority map moves by up to 0.57 dissimilarity under plausible
   weight perturbations, presenting a single deterministic map is arguably the weakest framing
   choice in the current pipeline. The plausible-range ensemble in item 7 partially substitutes,
   since a selection-frequency surface also distinguishes a robust core from a contested fringe.
3a. **The new selection is biased toward human-modified land, and this is now measured.** Mean gHM
   is **0.074 across the newly selected area versus 0.055 across the land it passed over**. The
   whole-solution figure (0.048 against 0.053 regionally) hides this, because the locked-in
   protected areas sit at 0.022 — existing parks are already in wild places. The cause is a
   confound rather than a modelling error: AOH richness peaks in productive low-elevation valleys,
   which is also where people settle (Spearman vs gHM: **+0.636** birds, **+0.607** mammals), and
   the one layer positioned to counterbalance it holds ~1% of the objective's achievable swing
   because `1 − gHM` over a uniformly wild region has leverage 0.042. Reported rather than
   corrected, by decision: restoring intactness needs either a role change (gHM as a penalty or
   cost) or an aggressive nonlinearity — a p1–p99 stretch reaches only 0.084 — and both add a new
   uncalibrated parameter. Quantified in `04a` by `results_core.footprint_audit`.
4. **min-shortfall @ 100% favours spatially concentrated inputs.** Carbon is over-served relative
   to area share; some EFGs are neglected. Unresolved.
5. **`neighbor_penalty = 1e-5` is a first guess, not calibrated.** It ranks 5th of 12 in influence,
   so it is not negligible.
6. **Resolution.** 1 km down-samples gHM (~90 m) and AOH (~100 m) substantially; accepted for
   iteration 1, with 300 m as the eventual ceiling.
7. **Phase 4 (Sobol') is DROPPED — decided 2026-08-17.** The pre-registered rule said: 2–3
   survivors → crossed factorial; 5+ survivors with high σ → Sobol' earns its cost. Recorded here
   as a reasoned gate outcome rather than a silent omission, since item 1 is already one live
   deviation from pre-registration.
   - **The gate cannot fire.** It keys on σ as evidence of interaction, but σ is inflated by the
     V-shaped distance metric. The σ/μ\* pattern — 1.01–1.12 for the top four factors, 1.33–1.67
     for the rest, rising as μ\* falls — is scatter scaling inversely with effect size, i.e. a
     noise signature. No subset of factors can be identified as interacting.
   - **Sobol' inherits the contaminated metric and is hurt more by it.** Jaccard is bounded and the
     observed dissimilarity is compressed into ~[0.221, 0.550], so variance decomposition would
     read saturation as interaction. And Sobol' indices are defined relative to the input
     distribution, which here is an arbitrary ×0.25–×4 hypercube: a ranking degrades gracefully
     under a badly chosen box, apportioned variance percentages do not.
   - **The marginal information is small** — the ranking is now known twice, the second time
     analytically via leverage, which also supplies the mechanism a Sobol' index would not.
   - **Cost, measured off this batch** (mean solve 1,001 s, 3 workers): 1,792 solves ≈ **6.9 days**
     at N=128 without second-order terms, 3,328 ≈ 12.8 days at SALib's default, 13,312 ≈ 51 days at
     N=512. The original gate's "~4 days" was optimistic by an order of magnitude.
   - **Replaced by a baseline-anchored plausible-range ensemble**: the baseline as an actual design
     point, ranges reflecting defensible uncertainty instead of ×0.25–×4, ~40–60 solves. Its
     per-cell **selection frequency** is simultaneously the robustness statement Y2Y actually asks
     for ("how much of this map should we trust?"), the surface post-hoc delineation grows
     candidate areas from, and a partial substitute for the MGA gap-portfolio that the Gurobi
     licence still blocks. With the compactness penalty gone this runs at **full 1 km**, so the
     2 km screening compromise and the G2 scale-transfer gate are no longer needed.

## 8. Software

Python 3.12 (`rioxarray`, `rasterio` 1.5.0, `geopandas` 1.1.3, `scipy`, `SALib`) for
preprocessing/analysis; R 4.6.0 with `prioritizr` 8.1.0, `terra` 1.9.34, `highs` for optimization.
GDAL called via subprocess for the warp stage. All parameters in `config.py`; the Python→R
contract in `aligned_stack/manifest.json`.
