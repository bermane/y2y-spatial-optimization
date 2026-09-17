# CLAUDE.md — Y2Y Spatial Optimization

Working context for Claude across sessions on this project.

## Assistant role & working norms

- **Never run notebook cells.** Claude writes and edits code; **Ethan runs everything
  in VS Code** cell-by-cell and follows along.
- **Consult before acting** on: any key decision, anything out of scope, or anything
  specific/ambiguous that surfaces. Otherwise proceed in "auto mode" to the agreed
  endpoint. Propose a plan and get approval before writing new code.
- **Keep this file current** — it's the cross-session reference for role + parameters.
- Tight scope, no premature abstraction, no framework-building unless asked.

## Project

Conservation-prioritization framework for the Yellowstone-to-Yukon (Y2Y) corridor.
Built as Jupyter notebooks, run cell-by-cell. Pipeline: **01** inventory →
**02** align to an **aligned raster stack** → **03** `prioritizr` optimization (R) →
**04** results analysis (Python). The Python→R hand-off is the stack +
`aligned_stack/manifest.json`; the R→Python hand-off is GeoTIFFs + CSV/JSON in
`output_data/`.

### Target grid (decided 2026-06-10)

- **Projection: ESRI:102008** — North America Albers Equal Area Conic. This is also the
  CRS of the Y2Y boundary reference layer.
- **Resolution: 1 km** for the **first iteration** of analysis. Rationale: most inputs
  are ~1 km native, so 1 km minimizes resampling distortion; it keeps `prioritizr`
  tractable over the large Y2Y extent; and coarse layers (climate_corridors at 5 km)
  are only mildly upsampled. The finer layers (gHM ~90 m, AOH ~100 m) are down-sampled
  for now — accepted for iteration 1.
- **Later ceiling: 300 m, not 100 m.** Only refine if the fine layers prove decisive;
  100 m is considered out of scope for Y2Y-wide prioritization (compute).
- Resampling method (for the alignment stage, later): average for down-sampling fine
  continuous layers, bilinear for up-sampling coarse ones, nearest/majority for
  categorical layers (IUCN EFG). Nothing aligns to this grid yet.
- **EXCEPTION — 05 routes at 300 m (decided 2026-08-07).** The corridor analysis runs on its
  own 300 m grid, because its resistance layer is natively 300 m and at 1 km a two-lane
  highway averaged down from 90 m gHM effectively vanishes — linear barriers are the signal
  there. It has its own grid namespace (`input_data/corridors_300m/`), never enters
  `aligned_stack/` or the manifest, and its **co-benefit audit still runs at 1 km**.
  **02/03/04/06 are unaffected and stay at 1 km.** See `docs/05_methods_v2.md` §3.

## Environment

- Geospatial stack lives in the project venv **`.venv` on Python 3.12.13** (Ethan
  recreated `.venv` on 3.12 — it was briefly 3.14.3, whose geo wheels are unreliable).
- Stack: `rioxarray rasterio(1.5.0) xarray pyproj(3.7.2) pandas(3.0.3) geopandas(1.1.3)`
  (+ `ipykernel jupyterlab`; `matplotlib` + `scipy` added for 04 plots/clustering). Pinned
  in `requirements.txt` (`pip freeze`).
- Jupyter kernel registered as **`y2y-geo`** (display "Python (y2y-geo)"). Select it
  for notebooks 01/02/04. System GDAL is 3.12.2; rasterio/fiona ship bundled GDAL wheels.
- **R stack (for 03)**: R 4.6.0 via Homebrew; `prioritizr(8.1.0) terra sf units jsonlite
  IRkernel highs` from CRAN (+ `gurobi` bindings from the Gurobi distro), pinned in
  `requirements-R.txt`. Kernel **`y2y-r`** (display
  "R (y2y)") — select it for 03. System libs via brew: `gdal geos proj udunits cmake`.
  - **macOS toolchain fix** in `~/.R/Makevars` (user-global, not in repo): R 4.6 + Apple
    CLT clang 16 need `CC=clang -std=gnu2x` (R hard-codes the unsupported `gnu23`) and
    `CXX=... -nostdinc++ -isystem .../SDKs/MacOSX.sdk/usr/include/c++/v1` (the CLT libc++
    headers are corrupted). Without these, every C/C++ R package fails to compile.
  - **Gurobi** is needed for the binary MGA gap-portfolio (`add_gap_portfolio`, build-time) —
    HiGHS has no solution pool. Gurobi 13.0.2 + R `gurobi` 13.0.2 are installed
    (`/Library/gurobi1302`). Meanwhile 03 runs a **HiGHS proportion-LP prototype** — the `highs`
    package IS used.
  - **UNBLOCKED 2026-08-26 — Gurobi WORKS.** History: the old TRIAL licence (size-limited
    ~2000 vars, `Error 10010`) was replaced 2026-08-17 by a **"Gurobi Gives Back" nonprofit WLS
    licence, LICENSEID 2853457, valid to 2027-08-14** (Brynn's ticket #120339; named users
    brynn@y2y.net + ethan@earthlineanalytics.com), which was then provisioned at 8 cores — below
    this Mac's 10 physical cores, so environment creation itself failed (`Error 10009`; the
    `Threads` parameter cannot work around it). Gurobi support raised the limit to **16 cores**
    2026-08-26; propagation from the Web License Manager to the WLS token servers took ~40 min
    (their "15 min" estimate was low), after which `gurobi_cl --license` passed and a toy LP
    solved end-to-end using all 10 threads. `~/gurobi.lic` was re-downloaded 2026-08-26 during
    diagnosis (fresh credentials, same LICENSEID). Old trial file backed up at
    `~/gurobi.lic.trial-backup-20260817`.
    Two live WLS properties: it needs a **live internet connection during optimization**, and the
    licence allows **2 concurrent sessions** — so `ENSEMBLE["workers"]=3` would fail on checkout.
    Keep ensemble runs on HiGHS; reserve Gurobi for the headline solve / MGA gap-portfolio.

## Data (`./input_data`, ~24.5 GB)

Mostly GeoTIFF/COG; one VRT mosaic; **no NetCDF present** (the AdaptWest climate layer
is extracted GeoTIFFs, not NetCDF as originally expected).

Datasets in scope (one inventory row each):
- `human_modification` — Theobald gHM v3 (VRT mosaic `HM_Y2Y_2024_90_60land.vrt`)
- `transboundary_connectivity` — Pither et al. omnidirectional connectivity
- `climate_corridors` — Carroll et al. 2018 current-flow centrality (**was a `.zip`**)
- `climate_type_macrorefugia` — AdaptWest CMIP6 **backward climatic velocity**, 8-GCM ensemble.
  **Naming decoded (2026-07-30) from the dataset's own `ReadMe_ClimateNA_CMIP6_zenodo.txt`,
  Zenodo doi:10.5281/zenodo.10631707** — `[direction][metric][version]_[GCM]_[SSP]_[period].tif`:
  `bw`/`fw` = inbound/outbound, `vel`/`disp` = velocity / disappearing-climate proportion,
  **`731` = ClimateNA software version 7.31** (*not* a threshold or climate-type code),
  `245`/`370`/`585` = SSP low-moderate/moderate/high, period = 2041-2070 or 2071-2100 against a
  **1961-1990** historical normal. Analogs matched by multivariate PCA over **11 variables**
  (MAT, MWMT, MCMT, TD, MAP, MSP, MWP, DD5, NFFD, Eref, CMD); no-analog cells = NODATA.
  Backward velocity = distance from a cell's *future* climate to its nearest *current* analog,
  per year → **low = macrorefugium**, hence `orient="invert"`. **km/yr is a per-year AVERAGE over
  the elapsed baseline→future span, so 2071-2100 divides by a LONGER denominator than 2041-2070**
  — late-century values are diluted, not simply more extreme (this is why SSP245 is flat across
  horizons: 1.995 → 1.998 km/yr on the PU). The CMIP6 readme does not restate the exact
  denominator; the CMIP5 sibling product documents distance ÷ years-elapsed. Cite as
  "AdaptWest Project. 2023. Gridded CMIP6-based climate velocity data for North America at 1km
  resolution." 6 realizations are on disk (3 SSP × 2 horizons); see the 02 stage-1 QA block.
- `irrecoverable_carbon` — Berman/McDowell irrecoverable carbon, **3 pools each its own
  feature** (`biomass`, `m_soc` mineral soil, `sl_soc` subsoil; all `t_ha` density)
- `iucn_efg` — IUCN GET EFG Level 3 (~109 GeoTIFFs, already extracted). **Source** value
  scheme: `0`=absent, **`1`=MAJOR occurrence, `2`=minor** (Byte, paletted; verified vs the
  IUCN GET Earth Engine catalog). Resample `nearest`. **02 SWAPS to `major=2`/`minor=1`** so
  the optimizer (higher value = more weight) weights major occurrences above minor.
- `aoh_richness_mammals` / `aoh_richness_birds` — Lumbierres AOH richness, **"all" (not Red List)**

Reference / masks / excluded:
- `y2y_boundary/y2y_region_boundary_2013.gpkg` — corridor reference extent for the
  coverage flag + study area (a vector; **not** a raster inventory row).
- `y2y_protected_areas/y2y_protected_areas_2025.gpkg` — protected-areas polygons (509,
  already ESRI:102008); rasterized in 02 as the **PA lock-in mask**. Prep only — its use
  as a constraint is R-side.
- **No urban/converted mask** — deferred on purpose; gHM-derived intactness already
  down-weights converted land.
- **Not using:** `bhi_beri_parc/`, `elevational_diversity/`.

## FLAGSHIP — `analyses/y2y/`: hierarchical selection-frequency ensemble (added 2026-08-18)

The methods paper this project now leads with; spec = **`analyses/y2y/spec/
frequency_ensemble_study_plan.md` (v0.8, accepted by Ethan 2026-08-21)** — read it before touching
anything here. (That on-disk copy was encoding-repaired from a chat attachment; Ethan dropping in
his original guarantees fidelity.) **v0.8 additions, both implemented:** transform screening is
UNIVERSAL ({identity, log1p, sqrt} for every feature + flip/reciprocal where cost-oriented;
adoption gated by R1's value-model test with the binding concavity distinction — measured payoff:
log1p FLIPS m_soc to diffuse-linear, the E9 log-arm story, and pushes AOH birds under the
expressivity floor), and Gate 0a renders **feature cards** (`leverage_core.feature_cards` → one
6-panel page per input + EFG block card + summary sheet = 10 pages into
`analyses/y2y/audit/feature_cards/`; archive now in `audit/audit_objects/`; the spec's "12 cards"
is a disclosed miscount — its own input list is 8 continuous + EFG block = 9). Cards are the human
review checkpoint BEFORE any Gate-0 solve. NOTE v0.8 did NOT absorb the five corrections this repo
already measured (Gurobi-gated pools, capacity-vs-outcome, SSP climate axis, Claim C linear-arm
limit, and the "capture lands at target (not above)" pass criterion that co-capture refutes) — they
remain owed to a future revision; the validation notebook keeps the measured-corrected verdicts.
**SPEC NOW v0.9.1 (2026-08-27): Gate 0a/0 ratified COMPLETE; the owed corrections were absorbed
(w=t RETIRED as a Gate-0-only convention; S4 = θ 3× → m_soc t 0.552; E5 HiGHS arm dropped;
climate axis SSP245 vs SSP585 both 2071–2100 → 14 serial formulations). GATE 1 DONE (run clean
2026-08-27):** the pre-registered biomass θ-tail diagnostic came back **capture 1.000 → (a)
mass-proportional split 74.2/25.8** (co-capture hypothesis REFUTED: 98.9% of tail mass is
independent selection — only 1.0% of the biomass tail overlaps the m_soc θ-tail; caveat:
measured at w=1, T1/E7 re-verifies at S0's w≈0.199); S0–S4 frozen in `spec/scenarios_v1.json`
(S0: refugia 1.460 / conn 0.669 / corridors 1.171 / m_soc 0.465@t0.332 / biomass 0.199 / birds
1.329 / mammals 1.708; EFGs 1/40 + intactness w=1 OUTSIDE, disclosed; machinery =
`config.BLOCKS` + `leverage_core.swing_per_unit_w`/`scenario_weights`); climate realizations
built in `aligned_stack/climate_realizations/` (585 BIT-identical to the stack layer, leverage
0.482/0.422, top-30% Jaccard 0.574). **GATE 2 RAN 2026-08-27 — VERDICT NEAR-BINARY, FAIL BRANCH
FIRED (pivot decision with chat before Gate 3): pool k=50 g=5% returned 50 near-clones (0.09%
conditional cells, Jaccard 0.9999, objective span 3.2e-6) because PoolSearchMode=2's k-BEST
enumeration never samples the g-band (M6.6; candidate fix = Brunel-style MGA ~1 min/solve);
costs: LP twin 6,516 s (HiGHS pathology, worst yet) / single 55 s / pool 1,799 s = 32.8× →
14-formulation ensemble ≈7 h; T1: biomass capture 31.0% (co-benefit achieved) but θ-tail expectation
FAILED (tail mass 0.425; M6.7: total-capture targets don't protect dense tails — co-capture
satisfies claims off-tail); S0 LP 100% integral, LP-vs-MILP Jaccard 0.9957. Full numbers
results_log R6.** **SPEC NOW v0.11 (2026-08-28); GATE 2a/2b COMPLETE 2026-08-30: S4 pilot
PASSED (tail capture m_soc 0.960 / biomass 0.772 vs band 0.75 — pressure redirected capture
dense-first, +1.9 pts total; F9 ready) and MGA verdict = PLATEAU-RICH (D 0.953 / C 0.020 at
g=5%, rule hash v2_8db80fed1c702638; CORE EROSION: always-core 22,866 cells @2% → 3,829 @5% →
ZERO @10%, union ≈ every discretionary cell — "any cell CAN, almost none is REQUIRED"; two-
instrument geometry: sharp unique optimum on wide shallow bowl = the E5 story; MGA ~32 min
total, iterations 10–16 s → ensemble ≈45–60 min/formulation). Report-back =
spec/gate2b_reportback.md; **SPEC v0.12/v0.12.1 RATIFIED GATE 3 + added E11. GATES 3+4
COMPLETE 2026-09-01 (results_log R8; gate4_reportback.md → chat for GATE 5): manifest frozen
d45668bb… (pre-registration committed); 13 formulations solved (~22 h wall; s3_ssp585 pool hit
the 12 h limit at 38/50 — disclosed; anchors exact 44–58 s; every LP twin ≤ MILP).
HEADLINES: ensemble ALWAYS band EMPTY (0 km² at F≥0.95; frequent tier 6,816 km²;
F_surface.tif = deliverable); E1 hierarchical-vs-naive bias mean 0.169 / max 0.755 (Claim A
vindicated); E3 within-formulation 95.2% / scenario 4.4% / climate 0.2% (estimator-
conditional); D_s 0.809–1.000 all plateau-rich, S5 = 1.000 exactly; E7 captures move ±4–9 pts
while maps hit Jaccard 0.373 (places not outcomes; S4@245 biomass tail 0.716 marginally under
the 585-registered band; crossed formulations prove target-without-weights fails tails);
E11 anchors Jaccard 0.373–0.931, 156/182 ordered pairs mutually in-band (no-regrets
pluralism), all 26 failures under carbon-forward objectives; Δ-diagonal self-check caught a
245-layer bug, fixed, diag ≤9.3e-6 (M5.11). E8–E10 → notebook 16. **SPEC v0.13/.13.1 (2026-09-02): GATE 5 entered in
parallel with the post-R8 round — BUILT as 15_post_r8_diagnostics (py, zero-solve: E13
CONFIRMED binding-scarcity, S4 high-f 80.8% inside the m_soc θ-tail; E14 trigger FIRED —
members sacrifice whole blocks inside the 5% band, so E15 runs; E17-T1/T2 latitude
attribution, 20/40 EFGs >90% southern; E9/E10 arms + e9_log_msoc.tif derived; writes
spec/e_round_v13.json) → 16_supplementary_solves (R: E12 MAA bracket ×3 formulations via
seeded `maa_generate`, E17-T3 five leave-one-block-out anchors, E8 ×10-satiation, E9 two
arms incl. log-layer patch, E10 θ-solves, E15 guardrailed MGA via `mga_block_floors` —
~3–5 h, resumable) → 17_e_round_analysis (py verdicts). E16 resolved to the sanctioned
F-clustering fallback (min-boundary MILP fails the compute gate). Notebook 14 =
gate4 results/decision views (presentation-grade, results_core star standard). Logs:
M4.18, R9.1–R9.6. Build record:** `11_gate3_freeze` (py: 14-formulation manifest.csv + sha256 =
the pre-registration; S5 = S0 + gHM×10 Claim-B demonstration; crossed s1x/s3x = shares held,
regime flipped alone; ssp245 = constant-intended-influence re-derivation via
`scenario_weights(layer_paths=…)`; reference formulation points kbest/twin at the Gate-2 record) →
`12_gate4_ensemble` (R: hash-verifies the freeze, two base contexts — 245 patches
`ctx$layers$path` before ingest — per cell kbest 50@5% + Gurobi-proportion twin + MGA
anchor/members into `runs/<formulation_id>/`, flat cell layout, per-artifact resumable, DRY-PLAN
cell first, ~10 h serial, live internet) → `13_gate4_analysis` (py: F + bands +
F_surface.tif, E1 bias, E2 definitional, E3 variance shares + crossed contrast, E7 per-cell
captures/θ-tails/gHM audits → T1 CSVs, E11 Jaccard + Δ(s,s′) matrices → F10; helper
`ensemble_core.read_selections`). E8–E10 = notebook 14, post-ensemble. Build record:**
D-A(a) = estimand RE-REGISTERED on MGA diversity generation (`mga_core.R`, toy-verified:
band-wall row `obj0·x ≤ (1+g)z*` appended to the COMPILED prioritizr model, linear
max-sum-Hamming distance objective over discretionary pu columns + 1e-3·obj0 shortfall-pinning
for honest per-member certificates, direct gurobi calls, warm starts; k-best pool kept
one-per-formulation = E5 discharged by design). S4 = pure (w,t) on the EXISTING 8-feature stack
(t=0.552 + block-doubled weights), judged by ONE certified pilot against the **pre-registered
band: θ-tail mass capture ≥0.75 BOTH pools** (S0 ref 0.435/0.425). **TAIL FEATURES RESCINDED
(Ethan 2026-08-28, M4.14): no separate tail values in the formulation, ever, without a new
decision — v0.10's locks AND v0.11's pre-authorized t=0.8 contingency both withdrawn; pilot
failure → chat. Knowledge kept as backup only (executed verification: both tails
rare-attainable, exact T2 matches; layers in `aligned_stack/_v010_tails_quarantine/`;
archived notebook `analyses/y2y/archive/08b_contingency_tails_RESCINDED.ipynb`; config wiring
removed, in git history). pr_targets now allows [0,1] (kept — correct generalization).**
Run order: **08_gate2a_pilot** (R: writes scenarios_v2 = v1 verbatim + band meta; solves
`iter10_y2y_s4_pilot`; scores band in-notebook, ~2 min) → **09_gate2b_mga** (R: anchor with
reproducibility assert vs 5.362813, then k=50 MGA at g=5% + 2%/10% probes, ~2.5–3 h,
resumable per g, live internet, outputs → `runs/s0_ssp585_theta5/`) →
**10_gate2b_analysis** (py: **PRE-REGISTERED verdict rule v2 frozen before the run** —
D = maxHam/(2·m_disc), C = f=1 core share, over anchor+members, discretionary only:
PLATEAU-RICH iff D≥0.10 ∧ C≤0.90; NEAR-UNIQUE iff D<0.02 ∨ C>0.98 → Claims-B+C pivot;
conditional-% reported NOT ruled — MGA inflates it; + f(g) core-erosion = E4's central
product) → verdict to chat = Gate 3 freeze vs pivot. Build record:**
`analyses/y2y/06_gate2_pool.ipynb` (R) solves S0 three ways into three folders — LP twin
`iter9_y2y_s0_lp`, certified single `iter9_y2y_s0_single` (opt_gap 1e-4), THE POOL
`iter9_y2y_s0_pool` (portfolio_n=50, portfolio_gap=0.05; cost unknown = the measurement; needs
live internet, fine overnight; all resumable) — then `07_gate2_analysis.ipynb` (Python):
pool integrity cross-checks, **PRE-REGISTERED degeneracy verdict frozen before the run**
(deduped pool, discretionary cells only: PLATEAU-RICH if k_distinct≥10 AND conditional
cells≥5%; NEAR-BINARY if k_distinct≤3 OR <1% → pivot with chat; else INTERMEDIATE), T1
intended-vs-realized (biomass capture vs anchors 25.9/41.3/49.7 + θ-tail rates), LP tightness,
E4 seed → `runs/gate2_s0_ref/`. Engine gained `run_summary$solver_provenance` (per-solution
objective/status/gap/runtime, harvested in pr_solve before stacking discards attrs;
toy-verified all three branches). Do NOT point `ensemble_core.collect` at portfolio folders
(it deletes selection_frequency.tif on the n_sol==1 assumption). Gate-2 verdict → chat decides
Gate 3 freeze vs pivot. **The whole campaign lives in `analyses/y2y/` (self-contained, 2026-08-18)** — the old `03a_y2y` /
`04a_y2y` root notebooks were MIGRATED here (outputs preserved; root-finding bootstraps added so
they run from the subfolder; `03b/03c`, `04b/04c` stay at root). Each notebook runs top-to-bottom
by Ethan, in numeric order: **`01_feature_audit.ipynb`** (Gate 0a: the §2.5 protocol over
`leverage_core`'s audit battery — `classify`/`characterization_table`/`trajectory_figure`/
`audit_archive`; constants FROZEN in `config.AUDIT`; archives budget-independent curves per spec
D2) → **`02_solve.ipynb` × 4–5** (the migrated 03a; Gate-0 arms in the RUN LEVER: `a0_control`/
`a1_protocol`/`a2_flat30`/`a3_flat40`/optional `a4_pullcheck`, ALL with **`WEIGHTS <- TARGETS`**,
i.e. w = t so pull `w/t` stays 1.00 and only the stopping point varies; **the lever call is
`ctx <- pr_override(...)` DIRECT assignment — never `modifyList(ctx, pr_override(...))`, which
deep-merges dict params so an arm's targets would MERGE with the config baseline instead of
replacing it; check the printed `EFFECTIVE targets:` line, `<none>` on a0**) →
**`03_gate0_validation.ipynb`** (verdict tables) → **`04_results.ipynb`** (the migrated 04a;
deep-dive one arm via its `RUN` variable). **02_solve has a BATCH cell at the end** (added
2026-08-21): Run All once solves the lever's default arm then every remaining arm in a loop —
resumable (arms with a `run_summary.json` are skipped), per-arm contexts isolated, dry-run
verified — so the campaign is one unattended pass instead of 4–5 manual lever edits. Gate-0a classifications (verified in code):
m_soc → concentrated-satiating (target **0.332**); **biomass REVERTED to diffuse-linear** by R2's
tail-mass criterion (implied target 0.066 < t_min 0.15) so `config.TARGETS`' biomass entry is
superseded by the protocol; intactness → R3-inexpressible; 36/40 EFGs rare-attainable.
**Measured on the superseded w=1 run (`iter7_y2y_r1_density5x`, 2026-08-18):** m_soc parked at
EXACTLY 0.332; biomass landed at 0.259 vs its 0.066 target — **min-shortfall never penalizes
exceeding a target** (excess = incidental co-capture, expected, not a failure; the spec's "lands
at target (not above)" pass criterion is wrong as written → v0.8 list); and the solve took
**4,289 s (~71 min, mostly HiGHS presolve) — NOT the 12 s of the untargeted LP**. Known spec-v0.7
errors carried for the v0.8 revision: shuffle-on-HiGHS fallback is false (all near-optimal
portfolios need BINARY decisions → Gurobi-gated), "36/40 EFGs saturate" conflates capacity with
outcome (5 did in iter6), climate axis must be **SSP245 vs SSP585 both 2071–2100** (not
"RCP4.5-2050s vs RCP8.5-2080s"), and Claim C's `w = influence/leverage` only holds on the linear
arm. 06's planned plausible-range ensemble is **superseded** by this study — do not build both.

**SPEC v0.14/.14.1 (2026-09-03): E-ROUND RATIFIED, EMPIRICAL PHASE CLOSED except one run; DIRECTOR
PACKAGE BUILT (subordinate spec `spec/director_package_spec.md` v1.1 = the Gate-5 deliverable).**
Rulings: E12 bracket accepted (no full-14 MAA; D quoted from MGA only); **E15 guarded semantics
PROMOTED to the applied headline** ("no value theme >5% behind"; aggregate band stays the Claim-A
estimand; E15b saturation = block accounting validated); E17 = disclosure + explicit Y2Y endorsement
decision; E16 = F-guided clustering is primary. Build (all headless smoke-run on the S0/S4 artifacts):
**`18_guarded_sweep.ipynb`** (R; step 0 — guarded MGA k=50 g=5% for the 12 open formulations + guarded
MAA spot-check on S0; anchors/kbest/twins STAND, anchor re-solved only for the compiled model with a
1e-3 assert vs formulation_meta; **RAN 2026-09-03/04: 12.3 h solve time (52–76 min per sweep — my ~3 h
projection from the 16-era S0/S4 timings was wrong; integrity perfect, 0 anchor cells differing)**;
`maa_generate` gained `floors=`, toy-verified) → **`19_tiers_and_clusters.ipynb`** (py; guarded
F + f per formulation + union membership → `director_package/geotiffs/`; T-D2 bands/acts, pooling
check (Jaccard ≥0.80), pre-stated clustering (0.70 → closing r=1 → 8-conn → ≥100 km² → core
subtraction; sensitivity 0.60/0.80; top-k presentational), T-D1 register with block percentiles +
driver attribution + IPCA overlap, T-D3, E17 shifts, `summary.json`) → **`20_figures.ipynb`**
(py; hex choropleths 250/800 km², Act 1/2/3 maps, star grid, why-these-places, E17 one-pager, table
PNGs, `deck_outline.md` + draft `director_deck.pptx` via python-pptx) over **`director_core.py`** (root
helper: grid/load_guarded/clusters/hex_grid/graticule/block_percentiles/driver_masks/ipca_layer/
plot_star_grid/build_deck). `ALLOW_PARTIAL=True` in 19/20 = DEV flag only (routes to `_smoke/`).
Open decisions for Ethan (spec list): (c) hex 250 vs 800, (e) cluster names (placeholders = nearest
named area + bearing), (f) E17 one-pager placement, (h) proposed-IPCA dataset (default: Indigenous-led
rows of `y2y_proposed_pa`, 9 polygons). Disclosed spec ambiguity: "rare-EFG footprint" = 36/40
rare-ATTAINABLE covers 79% of the region → a ≤1%-footprint companion (13 EFGs) ships alongside.
Logs: M4.18–M4.20 (numbering per methods_log), R10.1–R10.3 placeholders. **Spec v1.3 / v0.14.2 (same day)
added presentation conventions only — built: tier-achievement figure, Act 1 (a)/(b) pair + inset histogram,
% area on scenario maps, agreement matrix, Currie et al. 2025 precedent lines; T-D4 (tier area by
ecoregion) is PENDING a layer in `input_data/ecoregions/` (19 auto-detects; CEC Level II/III recommended).**
**2026-09-04 package rulings (all logged):** package votes with the 12 ELICITED formulations (crossed hybrids
out, F12; paper keeps F14); Act 2 pooled per scenario; intactness a plain star axis; representativeness =
per-cell EFG-count percentile; guarded/unguarded contrast paper-only; 'F' not 'guarded F'; complexes (25 km
single linkage) = deck picks; Natural Earth admin basemap; IPCA overlay = IPCA-typed + Ross River only;
summary map = tiers at 1 km with Act 2 split by owning scenario; climate axis KEPT (renamed refugia
realization) with by-future Act 1 pairs + the two-way map. Findings: the core is refugia country (R10.6);
PAs are value-average (R10.4); connectivity/biodiversity never own tier land (R10.12). **E18 RAN: WEIGHT-LIMITED (R10.13)** — connectivity ×5 (influence share 0.83) creates its own 34,705 km²
tier (refugia 0.88×); "binding" = weight × concentration; Act-2 statements for diffuse values are dose-dependent.
E18 dose table COMPLETE 2026-09-05: connectivity crosses over between share 0.67–0.83; biodiversity NEVER pins
(×5: tier 0 km², max f 0.63, D = 1.000) — weight × concentration, AOH richness unrescuable by weight. **Carbon weights-only arm RAN 2026-09-08 (fifth E18 arm, `runs/e18_s4x1_wonly_ssp585` = S4's registered
weights at S0's targets; R10.14 cont.): SUBSTITUTABLE — own land 763 km² vs S4's 20,329, tier 72% inside the 12-position core → carbon's
Act-2 land is the TARGET's doing (members never fall below t 0.332; under t 0.552 they must). Lead-magnitude currency is conditional on the
target binding (this arm scores 7.6× refugia yet owns nothing; M4.22 addendum). 23 now writes max f / D / lead currency into
`spec/E18_dose_table.csv`; 20 renders it as the E18 slide (`td_e18_dose.png`) + a carbon-target caveat on the carbon-forward Act-2 slide.**
**SPEC v0.15 / v0.16 / v0.16.1 + PACKAGE SPEC v1.6 (landed 2026-09-08; built the same day, all zero-solve):** (v0.15) s1x/s3x
reclassified DIAGNOSTIC (non-voting) — F denominator = 12 DESIGN formulations PRIMARY for paper and package alike; **`13b_denominator_v015.ipynb`**
writes `spec/manifest_v2.csv` (+ sha; `role` column; the frozen v1 manifest + hash untouched) and the 12-vs-14 record (R10.16: frequent
6,816 → 6,306 km², max per-cell |ΔF| 0.054, E11 156/182 → 109/132; 3 of the 26 failures involved a diagnostic, all as plan);
`director_core.package_manifest` reads `role`. (v0.16/.16.1) E18 closed on Option A; the connectivity ladder and the SSP245 twins were
RESCINDED (no further solves; arms = evidence, dose table in the deck appendix); carbon caveat + mirror verbatim. (v1.6) deck is
VALUE-FIRST, four acts: Act 1 where the values are (per-theme top-30% value maps by block score + value-convergence count 0–5;
representativeness = presence of a ≤1%-footprint EFG; intactness sixth, not counted) → Act 2 core (old Act 1) → Act 3 scenario tiers with
the BINDING value|tier pairing (old Act 2; biodiversity finding-as-product; carbon caveat + mirror) → hinge cross-tab (convergence ×
reliability class) → Act 4 = the measured gap (high-value land outside core ∪ scenario tiers, backed by union membership + E11).
19 gained the value cell (`value_top30_*.tif`, `value_convergence.tif`, `value_gap.tif`, T-D6/T-D6b, `hinge_crosstab.csv`, biodiversity
capture over all 612 guarded plans); 20 renumbered its figures to v1.6 acts and gained `act1_values_hex250`, `act1_value_convergence_hex250`,
`act3_<sid>_hex250` pairings, `hinge_convergence_x_F`, `act4_opportunity`, `td6_value_coverage`; internal act identifiers in 19's registers
keep v1.1 values (`ACT_DISPLAY` maps them). Ethan's 09-04 rulings stand where v1.6 text is stale (no doubling slide, EFG-count percentile
star axis, admin basemap). Logs M4.23–M4.25, R10.16–R10.17. Run order for the record: 13b → 19 → 20.**
**SPEC v0.17 / v0.17.1 / v0.17.2 + PACKAGE v1.7 (landed 2026-09-09; BUILT the same day): EFG BLOCK CURATION + MANIFEST v3 RE-SOLVE +
THE NECESSITY TEST (E19).** Trigger R10.18 / AB R7.9–R7.11: the 40-class block rewarded map artifacts (per-cell class value ∝ 1/footprint).
New rule R0 (input pre-screen: purpose, map validity, boundary proximity). Curation 40 → 22 classes / **20 features** (12 anthropogenic
out; point-record F2.10 out; sub-grain F2.6/F2.2/F1.4/F2.3 out; F2.9 out; TF1.6+TF1.7 and S1.1+SF1.1 merged) — M2.11, R10.19.
**ONE SWITCH: `config.Y2Y_VERSION` ("v3" default; `Y2Y_VERSION=v1` in the env reproduces the frozen run) derives `config.EFG_SUBDIR`
(`iucn_efg_v3` / `iucn_efg`) and `config.y2y_paths()` (runs_v3/ vs runs/, manifest_v3.csv vs manifest.csv, records spec/v3/ vs spec/).**
Supersede, never delete: v1 stack/manifests/runs/records byte-identical; `write_manifest` refuses an empty block folder; the R notebooks
assert the refreshed manifest enumerates the expected block; NEVER run two versions' R notebooks concurrently (they share
aligned_stack/manifest.json). Rarity-scaled log-linear EFG targets ADOPTED for v3 (`config.EFG_TARGET_RULE`, Rodrigues 2004 anchors
1,000 / 250,000 km²; M4.27). Build: **`11b_efg_curation_freeze_v3`** (py, RAN: curation table, both v3 stacks incl. the Alberta mirror
27 → 13 features, block card — rare-attainable 17/20, ≤1% companion 6, southern 9/20 — targets, manifest v3 frozen sha e47991bc…;
**R0 (iii) flags FIVE of the six small retained classes as clip-edges (72–100% within 10 km of the boundary) — reported for the spec
chat, not dropped**) → **12 + 18 with `VERSION <- "v3"`** (anchors, MGA, twins — k-best skipped; guarded sweep; ~22 h total; dry-plans
verified: 12 formulations, 20-feature block) → 13, 15 (version switch; v1 regression byte-identical) → **`18b_e19_solves`** (R: leave-EFG-out
anchors ×12 ~15 min; gated no-EFG ensemble T3) → **`18c_e19_analysis`** (py: adequacy-forced set, core partition, T2 agreement, the 50%
gate → `spec/v3/e19_gate.json`) → 19 → 20 (v1.7: archive the artifact-block package, `pct_adequacy_forced` + ADEQUACY PIN captions,
E19 partition table/appendix slide, curation disclosure on slide 1). 22 pinned to v1 (E18 = evidence). E12/E17-T3/E18 stand as v1
evidence. Logs M2.11, M4.26–M4.28, supersession rows, R10.19 (+ R10.20–R10.22 placeholders). **Naming convention (binding): name things by
what they are, code in parentheses.** Alberta re-run = stage 2 (its v3 stack exists; spec mirror re-pin pending). **REPORT-BACK for the v3.1 run + package: `spec/v31_reportback.md` (2026-09-15; R10.22 measured) → chat.** **SPEC v0.18 = FROZEN; post-freeze register PF-1 = E20 refugia transform conditionality (M4.34, R10.24): `18d_e20_refugia_audit` (py, RAN: floor inert, log1p(1/v) kills the θ-tail, ordering unchanged) → `18e_e20_solves` (R, Ethan ~1 h: S0@585 guarded under log1p(1/v) → `runs_v3.1/e20_log/`) → `18g_e20_analysis` (py: transform-conditional share per arm). **PF-2 (2026-09-16, M4.35, R10.25): the uniform value-shape audit in 18d (every continuous value × {linear, saturating, convex}; I² transboundary = concentrated-satiating → R2 target 0.198; Carroll layer = compressed index, I² not adopted; AOH log1p inexpressible; gHM convex tail only below precision) → `18f_e20_consistent_solves` (R, Ethan ~1 h: S0@585 under log1p(1/v) + I² connectivity at t 0.198 → `runs_v3.1/e20_consistent/`) → 18g reads every solved arm. **PF-1 RESULT (R10.24 cont.): transform-conditional share 4.3% — the core rests on the refugia ORDERING, not the 1/v tail; RULING: 1/v stays registered, log1p in the pocket. PF-2 arms (18f: t = 1 and R2-target 0.198; corridors squared too, M4.35 add. 4) pending Ethan's run. **PF-3 BUILT (spec v0.18 sequence, M4.36): 18d writes four block-split arms (A: five blocks at 20%; B: corridors removed) × (S0, S2) on the step-2 shapes; 18f runs all six arms (PF-3 gated on the step-2 baseline `e20_consistent`); 18g reports own land (E18 definition), pinch-point pinning, D, Jaccards vs the registered run and the baseline (`spec/v3.1/E20_pf3_summary.csv`). Weights per arm in `e20_refugia_transform.json`.**** Outside run_v31.sh; director outputs untouched.**
**v0.17.3 (same day) → MANIFEST v3.1 = the one to solve:** the clip-edge flags were resolved by deriving the rarity-scaled targets from each
class's footprint in the extent BUFFERED by 250 km (GET archive maps, 100/500 km sensitivity; M4.29, R10.19 cont.): F1.1 0.50, F2.1 0.49,
T6.1 0.36, twelve features at the 0.10 floor; rare-in-window = F1.1 + F2.1 only (the Act 1 representativeness vote). `config.Y2Y_VERSION`
default "v3.1" (runs_v3.1/, spec/v3.1/, manifest_v3.1.csv; block folder shared with v3 via `efg_subdir_for`); manifest v3 kept, never
solved; 11b has write-once freeze guards. **LAYOUT (2026-09-10): `analyses/y2y/` = the complete trail from step one in numeric order (01–11 gates, 11b v3.1 freeze, 12/13/15/18
Gate 4, 16/17 E-round, 18b/18c E19, 19/20 package, 22/23 E18); `evidence/` = ONLY superseded notebooks (13b → manifest role column; 14 →
the package); `archive/` = rescinded. Rule: a notebook whose artifacts a later step consumes stays in the trail. See `analyses/y2y/README.md`.** **NOTEBOOK NAMES (2026-09-14): 19_tiers_and_clusters (was director_surfaces), 20_figures (EVERY output, the record), 21_director_outputs (the
curated few for the presentation; `director_package/director_outputs/`), E18 → 22_e18_connectivity_weight / 23_e18_analysis. Shared plotting state/helpers =
`director_plot.py` (`C = dp.load()`; notebooks `globals().update(vars(C))`).** **ASSET RULE (Ethan 2026-09-14): a presentation asset is ONE function in
`director_plot` (`values_table`, `core_map`, `core_stars`, `core_consequences`, `scenario_stars`, `scenario_consequences`, ...) with its knobs in
`dp.STYLE`; 20 and 21 both call it — never copy drawing code into a notebook, or the record and the presentation drift. The objectives table renders in `STYLE["values_table"]` = "poster" (the Carbon-Poster spec, Ethan's pick 2026-09-14 over the Threat-Digest "digest" and the original "plain", both kept as `values_table_digest` / `values_table_plain`; Cronos Pro needs the DejaVu fallback in the family list for thin spaces). **SUPERSEDED the same day by the TABLE SPEC** (Ethan's "Y2Y Table Spec", `director_plot.spec_table_png` + `TABLE` tokens + `STYLE["table_base_px"]`): `STYLE["values_table"]="spec"`; consequences tables TRANSPOSED (measures × clusters + reference columns, row-wise red→green tint). **Act 1 maps = two 1 km files** (`core_map_F`, `core_map_clusters`; the hex pair `core_map_hex250` superseded). **BASEMAP (2026-09-14):** the northern package's cartography on the Y2Y frame — `director_core.basemap_layer/draw_basemap/read_hillshade` (NE land/water, GLO-90 hillshade `input_data/basemap/hillshade_y2y_300m.tif` at 18%, province names on open land, `STYLE["towns"]`), legend beside the frame, scale bar + north arrow SW; display only. **WIDE LAYOUT (same day):** `STYLE["map_layout"]="wide"` = 13.33×7.5 in slide with two zoom insets around `STYLE["inset_clusters"]` (1, 2) (PA/IPCA names, towns, 50 km bar); `values_table_simple` = the bare-bones objectives table (`01b_values_table_simple.png`).; **Act 2 in 21 = ONE map** (`scenario_map`, tiers split by owning scenario + three windows + area/share legend; also 20's `summary_tiers_1km.png`).** **ACT NUMBERING (Ethan 2026-09-14, overrides package spec v1.6):
Act 0 = the values (maps + convergence, a prologue); Act 1 = the core; Act 2 = the scenario tiers; Act 3 = the opportunity landscape; hinge
between 2 and 3. Files/titles/deck follow (`ACT_TITLE`); 19's internal ids unchanged.** **2026-09-14 team-output rules (M4.33): deck picks = top-k complexes grouped REGIONALLY (single linkage 75 km, `group_picks`) and numbered
NORTH → SOUTH (v3.1 core: four clusters); star titles "Cluster N"; "intactness" is now "naturalness" in every output (feature name unchanged);
T-D7 consequences tables per act = cluster mean value ÷ allocatable-land mean, shown as "2.3×" (`ValueRatios`); deck is v3.1-only (M4.32).** **RUN = ONE COMMAND: `caffeinate -i bash analyses/y2y/run_v31.sh`** (NUMERIC ORDER 12 → 13 → 15 → 18 → 18b → 18c
→ [18b + 18c again iff the E19 gate opens] → 19 → 20, in place, resumable, logs in analyses/y2y/logs/; 13/15 need only 12, the rest need 18 too). **EFG-BLOCK EXPOSURE (2026-09-08, R10.18): the five smallest classes (3–409 cells) are 100% inside the
Act 2 core; 8.2% of core, 2/14 deck picks (#11 = flooded-mines/aquafarms envelopes, #12 = T5.4), 27.9% of the Act 1 representativeness
layer sit on ≤1%-footprint map slivers — decision (rule A/B/C/D + re-solve vs presentation) with chat; see `spec/efg_block_reportback.md`.**

**LIVING PUBLICATION LOGS (added 2026-08-27, binding on every session touching this analysis):**
`analyses/y2y/spec/methods_log.md` (M-numbered: every methods-relevant decision, data
manipulation — e.g. the dust threshold, orientation changes — formulation, solver/numerics, QA
rules) and `analyses/y2y/spec/results_log.md` (R-numbered: every quantitative result destined for
the paper, with run provenance) are the cumulative methods + results sections of the publication.
**Any change to data, formulation, solver config, or QA rules → a methods_log entry in the SAME
session, including reversals (supersede, never delete); any new measured result → a results_log
entry.** Both are git-tracked in `spec/` so they persist across chats/restarts; keep them current
the way this file is kept current.
**GATE 0 RE-WIRED TO THE PRODUCTION FORMULATION (2026-08-26, Gurobi live).** Per Ethan's
consistency call, 02_solve's lever now carries a `MODE` switch defaulting to **binary MILP +
Gurobi, **opt_gap 1e-4 + numeric_focus** (standard adopted 2026-08-26 after the false-certificate diagnosis: without NumericFocus, Gurobi's root LP mis-converged 0.42% high on the a4 arm and certified the wrong optimum — the [1e-11,1e5] matrix range is the cause; with the fix the same solve hit the exact optimum in 17 s, 60× faster), portfolio off → folders `iter8_y2y_<arm>`**; the solved iter7 LP arms
(all five DONE 2026-08-21: a0 11 s / a1 70 min / a2–a3 ~11 min / a4 17 s) are KEPT as the
relaxation-tightness record. LP results: every target bound EXACTLY at the kink under w=t; a4
reproduced a0 with **0 differing cells** (the w/t proof); control m_soc capture rose to **54.4%**
(dominance got WORSE under penalty-removal + 1/v); a1's freed ~21 pts went mostly to **biomass
+8.4** (weight-levered leak → S0 block-design question), birds +2.2 / mammals +1.6 /
refugia +1.1, corridors **−1.4** (spec's freed-budget prediction partly wrong); a2 lifts the
under-served EFGs 0.234 → 0.507. 03_gate0_validation auto-detects the generation, checks binary
a4 by **objective-equivalence** (MILP near-ties may break differently — divergence at equal
capture is a degeneracy datum), and gained an LP-vs-MILP tightness cell. Engine: solver/portfolio
now decided from params at BUILD time (`pr_build_problem`), so `pr_override` can switch them;
**two latent portfolio-path bugs fixed on first execution** — the Gurobi-13 `xn`→`poolnx` pool
rename (documented shim wrapping `gurobi::gurobi` in prioritizr_core.R) and portfolio `solve()`
returning a list (pr_solve now stacks) — all three solver branches verified on a toy problem
including portfolio summaries + write round-trip.

## ANALYSIS 3 — `analyses/alberta_prioritization/`: the Alberta scale-transfer mirror (added 2026-09-03)

Applied decision-support run for Y2Y's Alberta program (Tim Burkhart) + a scale-transfer test of
the flagship protocol. **Spec = `spec/alberta_prioritization_spec.md` (v0.5, mirror of the parent
study plan v0.17.3 + package spec v1.7 — re-pin and log the delta whenever the parent spec changes; Ethan's
standing instruction). The spec file was found TRUNCATED to 3 lines in HEAD (2026-09-08) and restored from
`77d8713` on 2026-09-14 — if it ever reads as a header only again, restore from git before editing.** Read it
before touching anything here. **Binding living logs, same rule as y2y: `spec/methods_log.md` (M1–M17) +
`spec/results_log.md` (R1–R8), update in the SAME session.**
Mirrored = the frozen decision procedure (R0 pre-screen + R1–R4, θ=5×/λ=0.10/a_min=0.5%/t_min=0.15, block
accounting, scenario rules, numerics, estimator `mga_maxham_v1` k=50, the necessity test E19); NOT mirrored = the
Y2Y-extent measurements, E17/E18/E12. **Engine design (M2.2): `input_data/aligned_stack_ab/` = the parent stack
masked to Alberta on the SAME grid** (cell IDs identical; every parent module runs unchanged via
`config.AB_HANDOFF_DIR` / `config.ANALYSES["ab_y2y"]`; R side = `config.write_manifest(analysis=
"ab_y2y", handoff_dir=AB, manifest_path=…)` then `pr_setup`; budget via `pr_override(budget_pct=…)`).
**ONE VERSION SWITCH (M15.4): `config.ab_paths(version)` mirrors `y2y_paths()` on `config.Y2Y_VERSION`** — v1 =
`spec/manifest.csv`, `runs/ab_l/A/`, `analysis/ab4/`; **v3.1 = `spec/manifest_v3.1.csv`, `runs_v3.1/ab_l/A/`,
`analysis/ab4_v3.1/`, `spec/v3.1/`, `figures/v3.1/`, block `aligned_stack_ab/iucn_efg_v3/` (13 features).**

**Rulings (all logged):** D-AB5 budget = locked + X·unlocked, X = the parent's realized fill rate
0.1764 → **level A: 38,055 cells (44.7%), additions 10,083 km²; level B scratched (M9.6).** D-AB9 biodiversity
block kept whole. S4 = θ 2× (t 0.772) via the pre-registered ladder against the measured co-capture floor (a1's
0.744, M5.7). D-AB7: 1 km display, 10 km² clusters, 10 km complexes, 500 m simplification. D-AB6 tabled. D-AB8 on
hold (tenure = the M6.1 estimate). **v0.5 (2026-09-14, parent scope closed): D-AB11 the R0 curation is INHERITED
(27 → 15 classes → 13 features; the four v1 core-pinning classes F2.10/F3.5/SF2.2/F2.9 all leave); D-AB12
rarity-scaled targets from the ALBERTA extent + 250 km window (parent's rule on this extent; the parent's targets
for the same features written beside — CONFIRM the window with Ethan); D-AB13 the applied band is DECIDED BY RULE
in 11: guarded 5% (mirror) unless the 5% guarded frequent tier < 100 km² (flat, as on the v1 block), then 2%
(D-AB10) — outputs are named `*_applied*`; E19 mirrored (11b/11c) with adequacy-pin captions; package v1.6
value-first four acts + v1.7 in 12/13.**

**Measured so far (v1 block):** AB PU 85,133 km², **32.9% locked**; tenure — discretionary 87% crown, ranchland pool
5,393 km²; audit — H-AB1 refuted, m_soc scale-stable but 71% banked; 27/40 EFGs; AB-2 — D 0.9999, C 0 at 5%;
AB-4 ran 2026-09-03; 11 ran 2026-09-08 (R7): **71% of the 2%-band core sat on GET map slivers (R7.9–R7.11) — the
trigger for the parent's v0.17 curation.**
**Build record (spec §12): 01 extent/stack → 02 audit → 03 tenure/AOI → 04 arms (R) → 05 scenarios →
06 anchors (R) → 07 MGA pilots (R) → 08 AB-2 analysis → 09 freeze (v1) → **09b curation freeze v3.1** → 10 ensemble
(R; VERSION switch, no k-best on v3.1) → 11 analysis (D-AB13, M4.31, C1 at the same parent version) → **11b E19
solves + E17-T3 (R) → 11c E19 analysis** → **12_tiers_and_clusters → 13_figures** (renamed 2026-09-15 to the parent's
names; acts 0–3, regional picks at 30 km numbered N→S, "naturalness", T-D7 consequences with the Upper Smoky reference
rows, tables to the Y2Y table spec via `director_plot.spec_table_png`); or `run_v31.sh`. **Status 2026-09-15: v3.1 RUN END-TO-END
(09b → 14; R8.1–R8.6 measured; report-back `spec/gate_ab_v31_reportback.md` → chat). HEADLINE: the curated block REMOVED
the core — 5% guarded frequent tier 27 km² → D-AB13 fired → applied band 2% guarded → core 31 km² (v1: 1,117); E19 forced
set EMPTY, T3 not triggered; D = 1.000 at 5% on all 12, E11 132/132; cause MEASURED = values flat on unprotected land
(best additions-sized set 1.1–1.6× a random fill for 5/8 themes) + banked (m_soc 71%, refugia 46%); tiers: scenario 319 km²,
opportunity 99.4%, value gap 99.2%; threshold ladder 0.5 → 205 km², 0.4 → 1,111. Open with chat: deliverable = the flatness
finding carried by the value map + tiers; keep F ≥ 0.70; confirm D-AB12 window + D-AB13. 12/13 carry the settled record rules and, since
2026-09-15 (M18.6), `director_plot.load()` takes an external package (grid, manifest, overlay in the IPCA role, window,
hex_grid) with Y2Y defaults unchanged — 13 and **`14_director_outputs`** (the mirror of 21: values table, Act 1 core maps
as the Alberta frame + ONE inset on the key cluster, stars + locators, consequences) draw from the same asset functions;
Alberta knobs live in `dp.STYLE` set before load. `run_v31.sh` ends at 14.** Data: `data/acquire.py`.

## ANALYSIS 4 — `analyses/communities/`: bear coexistence groups (started 2026-09-16)

The last analysis piece. Input = `input_data/bear_coexistence/CoexistenceGroup_CDCounty_SpatJoin/` (Y2Y Communities &
Conservation team; `.shp` + `.gpkg` twins of ONE layer + `README_MetaData.docx`): counts of active local/regional bear
coexistence groups per **2021 Canadian Census Division / US county, ALREADY CLIPPED to the unbuffered Y2Y boundary**
(108 units, 99.99% coverage, no overlaps; EPSG:4326; `country`, `MappingUnit` = `<name>_<province/state>`, `n_groups`
float with NA = "no group recorded"; current to July 2026; only the TOTAL ships — the three group types in the metadata
are not in the file). **`01_bear_coexistence_explore.ipynb`** (py, kernel y2y-geo, read-only on the input; writes
`audit/bear_coexistence_units.csv` + `audit/bear_coexistence_label_qa.csv` + `figures/`) characterises it — no
alignment, no rasterization, no config registration yet. **Measured on first build: 30/108 units hold ≥1 group, 53 groups
as shipped; 21/108 units carry the WRONG province/state suffix** (polygons right, suffix from a neighbouring
jurisdiction — checked against the NE admin-1 basemap layer), and **4 of those collide with a same-name county next door
and copy its `n_groups`** (Madison ID/MT, Teton ID/WY, Lincoln WY/MT, Park WY/MT → true total possibly 47). Unit areas
span 0.02–296,959 km², so count ≠ density ≠ presence. **ROLE DECIDED (Ethan 2026-09-16): a PROXIMITY measure — distance of clusters / land identified for
conservation to bear-smart communities; NOT a feature in the optimizer.** Ethan is not worried about the label QA per se;
the check that matters is whether the suffix bug signals wider corruption. **Assessed the same day:** geometry sound
(genuine CD/county polygons, tessellating, clipped); 19/21 wrong suffixes name an ADJACENT jurisdiction (spatial-join
tie-break at state borders, label-only); the 2 non-adjacent cases (Madison ID, Lincoln WY, both far from Montana)
prove the 4 collision counts were copied by NAME from the Montana namesakes → treat those 4 as false positives (all in
the Greater Yellowstone / ID–WY corner, material for a southern proximity measure); false negatives on the 17
mislabelled NA units are possible but unverifiable from the file. Bigger limitation for the stated use: `n_groups` sums
three group types (Bear Smart is one), and the support is a county/CD polygon (0.02–296,959 km²) — proximity to a
297,000 km² CD is meaningless. Best fix for all of it = the C&C tracking-database rows (group, type, county, town). **Second use (Ethan, same day): a
NAMING gazetteer for clusters ("Kootenays", "Peace region") — overlay of the 12 deck picks shows it works in BC, needs a
lookup in Alberta (numbered CDs), fails in the north (one 297,000 km² Yukon unit, NT "Region N") and is too fine in the US
south; deliverable = a curated unit→region lookup beside `director_core.placeholder_name`. REPORT-BACK for the spec chat =
`analyses/communities/spec/bear_coexistence_reportback.md` (decisions D-C1–D-C5; next build 02_proximity / 03_region_names
waits on them). NA RULE (Ethan 2026-09-16): `n_groups` NA stays NA — the file has no zeros (78 NA / 30 counted); never recode to 0.**

## Structure — two notebooks + shared config

- **`config.py`** = single source of truth imported by both notebooks: `DATASETS`
  registry, grid params (`TARGET_CRS`/`TARGET_RES_M`/`BUFFER_KM`), discovery helpers
  (`is_raster`/`find_rasters`/`pick_representative`), and `study_area()`. Add a dataset
  by adding one entry. Per-entry flags: `multi` (True only for `iucn_efg`), `resampling`
  (`average`/`bilinear`/`nearest`), `build_vrt` (True only for `human_modification`),
  `orient` (`complement` for gHM→intactness, **`reciprocal` for velocity→refugia**, else raw;
  `invert` is SUPERSEDED but kept so pre-2026-08-17 runs reproduce — see the leverage note below).
  Also holds `HANDOFF_DIR`, `PA_VECTOR`, QA knobs `CONNECTIVITY_CAP_PCTILE` (None =
  no cap) / `CARBON_FLAG_PCTILE` / **`LEVERAGE_MIN=0.10`**, the **prioritizr run params** — `OBJECTIVE`
  (`min_shortfall`/`max_utility`/`min_set`), `BUDGET_PCT=0.30`, `TARGET_PCT=1.0`, **`TARGETS`**
  (per-feature target overrides; see 03), `NORM_TOTAL`,
  `SOLVER`/`HIGHS_SOLVER`/`SOLVER_TIME_LIMIT`, `DECISION_TYPE`, `PROTOTYPE_AGG_FACTOR`,
  `OPT_GAP`, `PORTFOLIO_N/GAP`, `CONNECTIVITY_PENALTY`, `BOUNDARY_PENALTY`, **`NEIGHBOR_PENALTY=0`**,
  `EXCLUDE_FEATURES`, the 04 cluster knobs (`CLUSTER_MIN_CELLS`/`CLUSTER_MAX_PLOTS`) — plus
  `RESULTS_DIR`/`RESULTS_SUBDIR`/`MANIFEST_PATH`, and
  `write_manifest()` (the Python→R contract writer). Notebooks `importlib.reload(config)`
  to pick up edits.
- **Resampling rule:** native finer than 1 km → `average` (down-sample); coarser/≈1 km →
  `bilinear` (up-sample); categorical (EFG) → `nearest`.
- **`leverage_core.py`** (added 2026-08-17) = the concept that reorganised the whole y2y-wide
  analysis. **LEVERAGE** = the range of a feature's captured fraction the budget can possibly span
  (share held by its richest `BUDGET_PCT` of PUs minus its poorest). At leverage ≈ 0 the feature's
  min-shortfall term is near-constant across *every* feasible selection, so its weight multiplies a
  constant and **cannot move the answer** — no re-weighting helps. It reproduces 06's Morris μ\*
  ranking at **Spearman +0.922 with zero solves**, so `w_f × leverage_f` decomposes the objective's
  achievable swing exactly. Three uses: the 02 QA gate (`report`, flags below `LEVERAGE_MIN`),
  deriving targets from a density rule (`target_cost_curve`), and reading a low-leverage radar axis
  honestly (`achievable_band`). **Two traps it exposes, both live:** an ADDITIVE orientation flip
  destroys leverage under 03's sum-normalization (`vmax−v` cost macrorefugia 75%, `1−gHM` cost gHM
  94%) — prefer multiplicative; and leverage bounds achievable swing but says nothing about its
  AREA PRICE, which is why 36 of 40 EFGs score ~1.0 (rare enough to fit in the budget entirely,
  so bought cheaply) yet rank below carbon in Morris.

### `01_raster_inventory.ipynb` — exploration (read-only)

Ingestion + a **native-characteristics** table. Characterization ONLY — no
reproject/resample/clip/align.

- Read **metadata only**; never read full pixel arrays. Optional sampled stats use
  decimated overviews and are **off by default**.
- One representative raster per dataset + `n_rasters`. gHM reads its `-0-0` tile (VRT was
  deleted), so its bounds/coverage are that one tile.
- Coverage flag: reproject the corridor **polygon geometry** into each raster's CRS (via
  `geopandas.to_crs`), then test bbox containment. Do **not** transform only the corridor
  bbox corners — Y2Y is a long diagonal, so its bbox bulges when reprojected and falsely
  fails covering rasters. Returns `None` when a raster has no CRS.
- Records `approx_res_x_m`/`approx_res_y_m` for degree-CRS rasters and the proposed
  `resampling` column (from config). Wide table → display sets `max_columns=None`.
- **No file export** — DataFrame shown inline only.

### `02_preprocess_align.ipynb` — cleaning / alignment (reads + writes full data)

**Two stages.** Produces the prioritizr-ready hand-off stack on the shared grid
(ESRI:102008, 1 km, Y2Y buffered by `BUFFER_KM`). Ethan runs it; heavy. Follows the
pre-processing hand-off (orientation, no normalization, raw carbon, PU-mask consistency,
NoData→NA) with **resolution held at 1 km** for iteration 1.

**Stage 1 — warp** (system `gdalwarp`/`gdalbuildvrt`/`gdal_rasterize` via subprocess;
osgeo bindings aren't in the venv): one streamed reproject+resample+cutline-clip per layer
to `cleaned_aligned/` (**intermediate, raw orientation**). Reads only the Y2Y window so
global rasters aren't warped in full. Fixed `-te`/`-tr` → shared grid. gHM VRT rebuilt from
its 4 tiles in-workflow. EFGs: warp all 109, **drop any with no presence (>0) in the
corridor**.

**Stage-1 QA — climate-scenario materiality (added 2026-07-30, cells 8–10 over `scenario_core.py`).**
`DATASETS["climate_type_macrorefugia"]` uses **one** of six AdaptWest realizations (SSP
245/370/585 × 2041–2070/2071–2100); `585_2071_2100` (hottest SSP, latest horizon, *least*
refugial) was an unstated pick. These cells warp all six to `cleaned_aligned/climate_scenarios/`
and measure whether the choice is decision-relevant, **before** spending six 1 km solves (~7.6 h)
or a sensitivity-analysis factor slot on it. Same doctrine as the Stage-2 QA: surface, don't
transform. Headline statistic = **top-`BUDGET_PCT` Jaccard** (overlap of the most-refugial 30% of
PUs — correlation alone is necessary but not sufficient), contextualised by the same statistic
between macrorefugia and each other input (**measured: 0.11–0.24**, i.e. what a genuinely
different input looks like). Verdict thresholds are **pre-registered** in
`config.CLIMATE_SCENARIOS["rule"]` → IMMATERIAL (drop the factor, skip the six solves) /
MATERIAL / AMBIGUOUS. Runs on **raw** velocity: the `vmax−v` flip is monotone, so correlation and
top-quantile membership are unchanged and no `vmax` decision is needed. `shared_anchor_report()`
prints candidate **pooled p1/p99 shared anchors** for a future six-scenario run — reported, never
applied (adopting them changes the feature even in the single-scenario case, because 03
sum-normalizes so an additive offset does *not* cancel → forces a re-solve). Diagnostic only:
nothing reaches `aligned_stack/`, the manifest, or a solve (`write_manifest` builds features from
`DATASETS` keys + `iucn_efg/*.tif`, never globbing the hand-off top level). Figure →
`figures/climate_scenario_spread.png`.

**Stage 2 — orient → mask → QA → COG** (numpy + rasterio, in memory; grid is small):
- **Orient** so higher = more conservation value: gHM→intactness (`1−gHM`, clip [0,1]),
  backward velocity→refugia (**`1/v`** — refugial residence time, yr/km; loud assert on `v<=0`
  rather than a silent epsilon floor, min over the PU is 0.097); carbon/connectivity
  already more=better. All features forced non-negative. **`vmax−v` was replaced 2026-08-17**: the
  additive flip does not cancel under 03's sum-normalization, so it crushed the layer's leverage
  0.353 → 0.090 and made macrorefugia the least influential factor in 06 — an artefact of the
  orientation, not a property of the climate data. `1/v` restores it to **0.422**, above the raw
  layer's own 0.353, with a verified-safe tail (max 10.3, top 100 cells = 0.1% of total).
- **One PU mask** = cells valid in **all continuous features** (EFG `0`=absent is valid, so
  EFGs don't constrain it). Applied identically to every feature **and** the uniform
  `cost_uniform`=1 layer → no cell valid in one layer but NoData in another.
- **QA (surface, don't silently transform):** flag carbon tail cells (`CARBON_FLAG_PCTILE`);
  print connectivity quantiles and cap **only** if `CONNECTIVITY_CAP_PCTILE` is set.
- **Stage-2 leverage QA (added 2026-08-17, cell over `leverage_core`).** The last gate before the
  stack reaches 03: prints per-feature leverage + the `w × leverage` influence share and **asserts**
  that the only feature below `LEVERAGE_MIN` is `human_modification`. That one is flagged
  DELIBERATELY — gHM is not recoverable by rescaling (a p1–p99 stretch only reaches 0.084), and the
  decision was to leave the layer alone and report the consequence (04a `footprint_audit`) rather
  than add an uncalibrated dial. Any *other* flag stops the run: classify it as (a) an orientation
  artefact, (b) 1 km aggregation flattening, or (c) genuine uniformity → report, never manufacture
  signal. Exists because 06 spent 130 solves discovering arithmetic.
- **Outputs = COGs** in `input_data/aligned_stack/` (`HANDOFF_DIR`; EFGs in `iucn_efg/`):
  continuous features + cost are float32/NaN-NoData; EFGs + `mask_protected_areas` are
  uint8 with `255`=NoData (so EFG `0` stays a valid value).
- Final cell validates: identical grid, NoData consistency, **matching PU formulation counts**,
  non-negativity, orientation spot-check. Grid = **1286 × 3312**, PU = **1,272,914 cells**;
  hand-off = 9 continuous + cost + PA mask + **40 EFGs**.
- **Last cell writes `aligned_stack/manifest.json`** via `config.write_manifest()` — the
  Python→R contract (per-layer role/dtype/NoData/orient + grid + run params). Metadata-only,
  so re-running just that cell is cheap (no re-warp). **03 also regenerates it** (same
  function), so this cell is now just the "stack is ready" marker — a `config.py` edit does
  **not** require a trip back to 02.

### `03a/03b/03c` — three analyses over `prioritizr_core.R` (R, kernel `y2y-r`)

> **03a MOVED (2026-08-18): the corridor-wide solve notebook is now
> `analyses/y2y/02_solve.ipynb`** (part of the flagship campaign above; outputs preserved, R
> root-finding bootstrap added, RUN LEVER carries the Gate-0 arms). 03b/03c remain at root and are
> unchanged. Everything below about the shared engine still applies to all three.

**03 was split (2026-07-20)** into three thin notebooks — `03a_y2y` (corridor-wide),
`03b_north_bc` (connect 4 draft IPCAs: crop to their buffered bbox, lock them in, up-weight
connectivity ×5), `03c_ab_foothills` (crop+mask to Alberta ∩ Foothills natural region,
compactness off) — all sourcing the shared engine **`prioritizr_core.R`** (one `pr_*` function
per old cell; each notebook differs by one line, `ANALYSIS <- "<key>"`). Per-analysis params
live in **`config.ANALYSES[key]`**; global params stay module-level. Each 03x cell 1 shells
`config.write_manifest(analysis='<key>')`. The one new capability is `terra::crop(+mask)` in
`pr_ingest` (ROI built Python-side by `config.build_roi`, which writes `roi_<analysis>.gpkg` +
reprojected `lockin_<analysis>.gpkg`); `BUDGET` auto-shrinks to the crop. 03a reproduces the
old y2y result exactly. **`03_prioritizr.ipynb` is the legacy monolith** (reference; rename to
`_LEGACY` once done with it). Alberta data derived into `input_data/alberta_boundary/` +
`input_data/ab_foothills/`. 04 sub-region adaptation is still pending (Phase 5). The rest of
this section describes the shared engine, unchanged from the monolith:

### `03_prioritizr.ipynb` (LEGACY monolith) — optimization (R, kernel `y2y-r`)

Builds + solves one `prioritizr` problem on the hand-off stack; writes results for 04.
**Configuring a run = edit `config.py`, then run 03 — no trip back to 02.** Cell 1 shells out
to `.venv/bin/python -c "import config; config.write_manifest()"` to **refresh** the manifest
(metadata-only; `write_manifest()` is standalone — it globs the hand-off dir and reads the grid
off the rasters), then reads + validates it. A failed refresh **stops** the run rather than
solving against a stale manifest — the drift bug that once mislabelled an iter4 run. 02 only
needs re-running when the *stack itself* changes. **All run params come from `config.py` via
the manifest.** Current
choices (full rationale + history in project memory `prioritizr-run-design`):
- **Objective** = `OBJECTIVE` knob. Current **`min_shortfall`, default `TARGET_PCT=1.0`** under a
  **30%-of-area budget** (`BUDGET_PCT`). Also supports `max_utility` and `min_set`. **The
  "concentrated inputs dominate" caveat is now QUANTIFIED, not vague:** influence ∝
  `w_f × leverage_f`, so under equal weights the two carbon pools held **39.7%** of the objective's
  achievable swing and were captured at 45.5%/41.8% (**1.52×/1.39× area share**) while every other
  value landed at 0.96–1.06× — the map was "the best 30% for carbon, everything else proportional".
  Note this is NOT fixable by switching objective: min_shortfall / max_utility / min_set are all
  linear in captured fraction, so the only levers are **weights** and **feature definitions**.
- **Per-feature targets (`config.TARGETS`, added 2026-08-17) — the carbon lever.** A target is a
  STOPPING RULE, not a weight: under min-shortfall a feature that reaches its target contributes
  zero and stops competing for area, and since the objective is linear the solver was already
  taking that feature's *densest* cells first. So a low target = "grab the hotspots, pass over the
  mediocre pixels, reallocate the rest". Preferred over re-weighting because it is a policy
  statement ("we aim to secure 33% of mineral-soil carbon") rather than a tuning knob.
  **Values are DERIVED, not chosen** — the rule "keep taking cells while marginal density ≥ 5× the
  regional mean" via `leverage_core.target_cost_curve` gives m_soc **0.332** (cutoff 304 t/ha, 4.1%
  of the region) and biomass **0.066** (cutoff 106 t/ha) — biomass demotes itself because it has
  almost no exceptional tail. **DO NOT lower every target**: if all became simultaneously
  achievable, shortfall is zero everywhere, the objective is flat, and the solver returns an
  arbitrary member of a huge optimal set. Foundational features stay at 1.0. Carried through the
  manifest as a NAME→value object and rebuilt R-side by `pr_targets` via `names(features)` lookup,
  so it cannot silently misalign; unknown names and out-of-range values `stop()`. **Set per
  analysis** — 03b/03c keep `{}`.
- **The RUN LEVER (03a cell 2) is where a sweep is driven from, NOT `config.py`.** `pr_override`
  patches `targets` + `results_subdir` into `ctx$params` after `pr_setup` (recomputing `out_dir`/
  `run_tag`, else the run overwrites whatever config pointed at), and `stop()`s on a param name
  the manifest doesn't define so a typo can't silently no-op into two identical runs. Overrides
  are deliberately NOT written back to `manifest.json`; `pr_build_problem` already snapshots
  `solve_params` and `pr_write_outputs` records those, so **`run_summary.json` is the record of
  what was actually solved** and is what sweep runs should be compared on. Same principle as
  `ensemble_core` patching a copy of the manifest per run rather than mutating `config.py`.
- **Normalization:** each feature sum-normalized to total = `NORM_TOTAL` (1e5) so 100% targets
  stay < 1e6 (prioritizr presolve guard); scale-invariant for min-shortfall.
- **PAs locked in** (counted toward budget); **EFG down-weighting** (`add_feature_weights`,
  continuous @1, each EFG @1/40); `sl_soc` carbon excluded (`EXCLUDE_FEATURES`).
- **Solver/decisions:** `SOLVER="highs"` + `DECISION_TYPE="proportion"` (LP, ~99% integral) is
  the **working prototype** — the binary MILP chokes HiGHS presolve at 1 km. The real
  **Gurobi MGA gap-portfolio** (`add_gap_portfolio`, binary) is **licence-UNBLOCKED as of
  2026-08-26** (see Environment) but not yet built/run — it waits on the Gate-0 review. The
  boundary-penalty LP needs `HIGHS_SOLVER="ipm"`
  (dual simplex times out). `SOLVER_TIME_LIMIT` caps the solve — **a timed-out run returns an
  infeasible point (area > budget); discard it.** With every penalty off, the 1 km LP solves in
  **~12 s**, so time limits are no longer the operative constraint for y2y.
- **Spatial penalties: ALL OFF as of 2026-08-17.** `CONNECTIVITY_PENALTY` (corridors) was always
  off; `BOUNDARY_PENALTY` needs `PROTOTYPE_AGG_FACTOR=2`; and **`NEIGHBOR_PENALTY` is now 0** —
  compactness moved OUT of the optimizer to post-hoc delineation. Three measured reasons:
  (1) at 1e-5, an uncalibrated first guess, Morris ranked it the **3rd** largest driver of the map
  and it **relocates a third of the selection** (Jaccard 0.662 vs the unpenalized `iter2_lp_1km`);
  (2) it wasn't creating the structure — the unpenalized solution is already **66.6% clustered by
  area** (blocks ≥100 km²) with singletons just 3% of new area; (3) it cost **400× the solve time**
  — 1 km takes **12 s** without it vs **4,826 s** with it, and every 06 timeout, the 6 h cap, the
  machine contention and the 2 km screening compromise trace to this one term. Removing it makes
  the ensemble affordable at full 1 km and matches 05's D9 (ship a graded surface, not hard lines).
- Outputs → `output_data/<RESULTS_SUBDIR>/`: `portfolio.tif` (proportion→float, binary→uint8),
  `selection_frequency.tif`, `portfolio_representation.csv` (`relative_held` → 04 radar),
  `run_summary.json`.

### `05_corridors_north.ipynb` — least-cost corridors, **v2** (Python)

> **CAMPAIGN MOVED (2026-08-21): the corridor analysis now runs from `analyses/northern_connectivity/`**
> (4 notebooks: 01_prep_and_parts → H7 human sign-off → 02_calibrate_baseline → 03_ensemble →
> 04_alternatives; spec = `spec/05_corridors_v2_addendum_run_and_alternatives.md`, D11–D16 on top of
> D1–D10). Engine modules stay at repo root; the root monolith is ARCHIVED at
> `archive/05_corridors_north_v2_monolith.ipynb`. **BINDING (same convention as the y2y flagship):**
> `analyses/northern_connectivity/spec/methods_log.md` + `spec/results_log.md` are the living paper
> registers — update them in the SAME session as any methods change or new result; supersede, never
> delete. **Status 2026-08-27: CAMPAIGN RUN END-TO-END (`v2_run002`)** — cutoff 13.62 → 18,150 km²
> MST-only; 58 edges, 33,041 km² new corridor land; **7 β-irreplaceable links + 35 route-irreplaceable
> edges; 16 of 42 name-drops disconnect the network** (axis C); 41-branch values table + tiebreak
> done. Four fixes measured into the logs during first execution: adjacency-band abs-mode (M4.3),
> richness stretch-domain (M6.2), ensemble edge identity (M5.7), fractional branch crossing (M6.5,
> G11 0.04%). `docs/05_methods_v2.md` patched with D11–D16 + measured gates. Remaining: deferred
> Phases 5–8 (H1–H6) + the two flagged open methods questions (locked-edge centrality; no_link
> direct-edge exclusion).
> **2026-09-03: D17 'squeezed' class CONFIRMED as a counterfactual band ratio (H8 closed; NB04 step 2b
> `cc.counterfactual_squeeze`, ~1 h extra CWD, G13) and the 06 DIRECTOR PACKAGE BUILT** for the October
> workshop (`corridors_director.py` + `06_director_package.ipynb`; spec `analyses/northern_connectivity/spec/
> 06_corridors_north_director_package_spec.md` v1.2 — two acts: north = room to choose, southern edge =
> options closing; IPCAs taken as given; H8 gate enforced in code; settlement-lands layer PENDING for M2/T1).
> Ethan runs NB04 (Run All) → 06. The 05 spec was regenerated by chat on 2026-09-03 and lost §8/§9 —
> restored from git HEAD and merged; keep that in mind if it is regenerated again.
> **2026-09-08: D17 MEASURED (NB04 clean: 8 squeezed links, G13 = `lcp_cf ≤ lcp_real`); M1 "Where the
> land still offers choices" is THE main plot, restyled to the director basemap (`_director_base`:
> NE coast/admin/border, province names auto-placed in open country, `MAJOR_TOWNS`, top-14 PA/IPCA
> names, legend below the map) + new M0 cost-surface map (`map_cost`, no corridors) — spec 06 v1.2.2,
> M5.12. Ethan re-runs NB06. Display-only name overrides (`AREA_OVERRIDES`) fix the PA layer's
> mis-encoded Fishing Branch string; Ethan to confirm the Ne’āh’ spelling.**
> **2026-09-09 (later): M2/M3 = crops at M1's map scale with Ethan's PINNED examples (options 1–4 north,
> links 5–7 south; `EXAMPLE_PICKS`), M4/N1 axed, star plots added after M3 on the y2y-wide construction
> (DECISION: star axes = mean PERCENTILE by theme, both packages; spec 06 v1.2.5, M5.15). The y2y EFG
> CURATION (40 → 20 features, y2y M2.11) is ADOPTED for the whole northern analysis (M5.16): G5 lives in
> `cc.gate_g5` (macrorefugia + EFG reported, not asserted), NB04 step 0b re-profiles; Ethan re-runs
> NB04 → 05_results → 06 so every EFG-bearing product is on the curated block (R9.4 pending).**
> **2026-09-11: the 05 AND 06 specs were regenerated by chat AGAIN (Linkage Mapper comparison: D18–D20,
> G14–G16; only D19 active) and lost §8/§9, the binding block, D17-confirmed and every entry after
> 2026-09-03 (06 also lost the UNCOMMITTED v1.2.3–v1.2.7, reconstructed) — merged from git HEAD (chat
> copies in the session scratchpad). D19's premise was wrong: centrality has been current-flow
> betweenness since the v2 rebuild; implemented as a pinned `centrality` key + `centrality_sp`
> comparison column + `cc.gate_g15` + `centrality_compare.csv` (M5.18); no product changes. NB02 gained
> a G15 cell; NB04 step 0b runs it. D18/D20 deferred. COMMIT the specs after each session — the chat
> regenerates from whatever it last saw. Same day: D21 ADJACENCY GRAPH (chat's surgical patch, spliced) =
> `cc.adjacency_graph` diagnostic universe (cost-allocation neighbours on the cached fields, Euclidean
> comparison, G17 MST ⊆ adjacency, `adjacency_*.csv`, `allocation.tif`, `adjacency_map.png`; no product
> changes; M5.19, R9.6 pending); NB02 step 2c, NB04 step 0b. Ethan runs NB04.**
> **CARTOGRAPHIC CONTRACT (06 §3a, 2026-09-11): `corridors_mapstyle.py` at root is the ONLY place a colour /
> font / line weight / extent / export setting may live; figures = `corridors_director.figure_*` with hand-placed
> label specs; run the §3a.3 QA before showing any figure; PDF + PNG. M0b built first; M1/M3/M2 pending
> Ethan's sign-off. Basemap data (hillshade, NE water, Noto Sans) = cartography only.**

Standalone corridor analysis, NOT prioritizr: it **routes** between anchor areas, which the
prioritizr connectivity penalty could not do (that aggregates permeable land; it cannot answer "how
does an animal get from park A to park B"). Kernel `y2y-geo`.

**REBUILT 2026-08-07 (decisions D1–D10).** Full rationale in **`docs/05_methods_v2.md`** — read that
before changing anything here. v1 is frozen at git tag **`05-v1`**, outputs in
`output_data/corridors_north/_v1_frozen/`, notebook `archive/05_corridors_north_v1.ipynb`, config
`configs/corridors/v1_baseline.json`. What changed:

- **D1/D2 — resistance is the published movement-cost surface, not a blend.** v1 blended Pither
  current density (0.5) + Carroll climate corridors (0.3) + AdaptWest macrorefugia (0.2), raised to
  `conn_exponent`, floored, and multiplied by `10**gHM`. That triple-counted human footprint, used a
  circuit-theory OUTPUT as a routing INPUT, and mixed climate-**analog** layers into **movement**
  cost. Every blend knob is deleted, and `resolve()` **raises** if one reappears in config.
  The layer is `input_data/transboundary_connectivity/Movement_Cost_Layer.tif` — the **O'Brien et al.
  transboundary extension of Pither et al. 2023** (seamless US+Canada), which shipped in the same
  download as `Raw_CurrentDensity_Map.tif` and was never registered. EPSG:3347, 300 m, values
  strictly `{1, 10, 100, 1000}`.
- **D6 — corridor band is an ABSOLUTE cwd cutoff**, not a fraction of edge cost (which made corridor
  width scale with edge cost). `cwd_cutoff_abs` is **calibrated** by `cc.calibrate_cutoff` to
  reproduce v1's 18,188 km² on **MST-only** edges, so v1↔v2 comparisons aren't confounded by band
  size; augmentation area is reported separately.
- **D7 — MST + bridge-backup augmentation.** The originally drafted criterion (keep any direct edge
  with cost ≤ α × MST-path cost) was **vacuous** — least-cost distance obeys the triangle inequality,
  so it admits the complete graph. `alpha` is retired. Replaced by sequential bridge backup, in
  descending criticality with recomputation, under a cost-ratio ceiling **`beta`**; links where
  nothing clears the ceiling are flagged **irreplaceable**, and those flags are the headline output.
- **D8 — structured ensemble** (`corridors_ensemble.py`) replaces the uniform-noise jitter: axis B
  band cutoff, C node leave-one-out, D β sweep. Axis A deferred (**H2**).
- **D9 — the deliverable is a graded `linkage_priority.tif`**, not hard corridor lines.

**TWO GRIDS, and this is a correctness requirement.** Routing is **300 m** (native, so roads survive
— verified: the cost-10 class forms linear features up to 395 km long); the **co-benefit audit stays
at 1 km**. `results_core.mask_profile` sums a feature over the mask while `_region_total` computes
the denominator at native 1 km with no finer-than-source path, so profiling a 300 m mask would
inflate every "% of Y2Y" figure ~11× while looking plausible (and cost ~10 GB of stacks). `A.template`
is the 300 m routing grid; `A.audit_template` is pinned to a 1 km hand-off layer; `_to_audit` crosses
masks at the boundary. **This overrides the 1 km grid decision for 05 only** — 02/03/04/06 stay 1 km.

**Modules.** `corridors_prep.py` (one-off warp + gate G2) · `corridor_graph.py` (raster-free: MST,
augmentation, quotient-graph centrality, criticality, `selftest()`) · `corridors_core.py` (grid,
nodes, CWD cache, bands, priority surface, audit, maps) · `corridors_ensemble.py`.

**Run convention.** `config.CORRIDORS["north"]` is the editable baseline; `cc.start()` resolves it,
writes `run_config.json` (params + git SHA + input hashes) into
`output_data/corridors_north/v2_runNNN/`, and the engine then reads **only** that file. Provenance is
load-bearing because `output_data/` is gitignored — the run dir is the only record that survives.

**CWD caching is what makes the ensemble affordable:** cost-weighted distance depends only on
(resistance, node seeds), and axes B/C/D change neither — axis C drops a node, which deletes a row
and column from the distance matrix but leaves every remaining node's field bit-identical. So the
whole ensemble reuses one cached CWD set. Cached as float32 memmaps under
`input_data/corridors_300m/cwd_cache/<sha>/`.

**Gates** (asserted notebook cells; no pytest in this repo). **G1 is the one that matters**: it runs
the new engine on **v1's own frozen resistance and grid** with MST-only edges and the relative band,
and requires v1's corridor back — isolating the refactor from every semantic change. **Measured:
Jaccard 1.0000**, 41 edges (12 zero-cost), 18,188 km². Also G0 node identity (42 nodes = 10 IPCA +
32 PA, same three dedupe merges), G2 warp fidelity, G3 raster-vs-graph component agreement, G4
β=0 ⇒ MST, G5 audit invariance, G7 cache reuse, G8 dead-config detection.

**Two traps preserved in comments — do not "optimise" them away.** `find_costs` returns MCP's
internal buffer (must copy); and `mcp.traceback` reads whichever `find_costs` ran **last**, so
regrouping traceback calls silently returns paths from the wrong source node with no exception. G1
is what catches that.

**Zero-cost "adjacency" edges (12 of 41)** — node pairs that already touch, chiefly Dene Kʼéh Kusān
wrapping 11 BC parks. Kept in the graph, contributing **no corridor land**; centrality computed on
the **quotient graph** (contracting zero-cost cliques is the correct physics, not a numerical
nuisance — and it is computation-scoped, so the 2026-08-05 dedupe decision is untouched); excluded
from failure enumeration and backup candidacy, since their failure mode is the *node* disappearing,
which leave-one-out covers. Flooring the cost is explicitly rejected — it would invent corridor land
between abutting polygons.

**Incidental finding, applies beyond 05:** v1's routable area was a strict subset of v2's (751,614
vs 872,725 km²) because v1 inherited the prioritizr PU mask. That mask is set by
**`irrecoverable_carbon_biomass`**, whose footprint (1,274,564 km²) is the binding constraint — every
other continuous feature covers ~1,551,000+ km² of the 1,551,654 km² buffered study area. So ~18% of
the study area is excluded from **every** prioritizr solve (03/04/06) by one layer's coverage.
Flagged, not acted on.

### `06_uncertainty_analysis.ipynb` — GSA over `ensemble_core.py` + `run_one.R` (Python)

**Added 2026-07-30 (Phases 2 / 2.5 / 3 of the uncertainty programme).** `03`/`04` say *where* the
priorities are; 06 says *what drives them* — it re-solves the same problem many times under
perturbed parameters and attributes the movement to individual factors. Post-solve, so it sits
after 03/04; it consumes the same aligned stack. Kernel `y2y-geo`.

- **`run_one.R`** — headless driver, mirrors 03a cells 1–9 **exactly** and holds no logic of its
  own. Takes `<manifest_path> <project_dir>` and calls `pr_setup()` directly (skipping
  `pr_refresh_manifest`, which hardcodes the canonical manifest path). Prints `RUN_ONE_OK` as the
  success sentinel. `prioritizr_core.R` needed **one line**: `n_threads` now honours an optional
  `params$threads` so concurrent solves each take a slice instead of all grabbing 10 cores.
- **`ensemble_core.py`** — the runner. **Design principle: patch a COPY of manifest.json per run;
  never mutate `config.py`.** config.py stays the baseline's single source of truth, every
  perturbation is an explicit delta in the design matrix, concurrent solves never share state, and
  each run's exact manifest sits beside its outputs so any single run is reproducible alone.
  `run()` is **resumable** (skips rows with a `run_summary.json`), runs `workers × threads`
  concurrently, logs per run. `collect()` returns a tidy table + an allocation matrix on a common
  domain; it deletes `selection_frequency.tif` (identical to `portfolio.tif` when `n_sol == 1`)
  and **flags unusable runs** — `analyze_morris()` then *refuses* rather than analysing around them,
  because a Morris design with holes is invalid. **The flag was wrong until 2026-08-07**: it tested
  only `over_budget` (area > budget), but a timed-out solve stops wherever it had got to and usually
  lands *under* budget, so the area test passes it. In the first 130-run batch **19 runs hit the
  7,200 s limit and exactly 1 was caught**. `collect()` now records `timed_out` (on the clock) and
  `over_budget` (on the area) separately plus a combined `unusable`, and reports **which
  trajectories** are hit — the number that matters, since an elementary effect is a difference
  between consecutive runs *within* a trajectory.
- **Config**: `ENSEMBLE` (rscript/driver/workers/threads/agg_factor/time_limit) and `MORRIS`
  (r=10, num_levels=4, seed, and the **12 factors** — 8 continuous feature weights + EFG group,
  each as a log2 multiplier ×0.25–×4; `budget_pct`; `target_pct`; `neighbor_penalty` as log10).
  Climate scenario is deliberately NOT a factor (needs shared-anchor orientation + a headline
  re-solve; deferred with Phase 1b). `min_shortfall` is scale-invariant in the weights, so
  scaling all nine together is a **null direction** — state this in methods.
- **Gates before the batch**: **G1 equivalence** (driver at 1 km must reproduce
  `iter5_lp_1km_neighbor`: same PU/budget/locked, Jaccard 1.0) → **G2 scale transfer** (fresh 2 km
  baseline vs the 1 km headline; `iter4_lp_2km_compact` can't serve — wrong penalty, predates
  `neighbor_penalty`) → **G3 noise floor** (10 identical solves at the same thread config; Morris
  effects are *differences*, so an effect below the floor would be solver noise, not signal).
  **G3 measured 0.000000, which is the CORRECT answer here, not a broken gate**: with
  `decision_type="proportion"` this is an LP, HiGHS IPM is deterministic, and `OPT_GAP` is a *MIP*
  gap and therefore inert. The "solutions aren't proven optimal at a 10% gap" concern applies only
  to a binary Gurobi run. A zero floor means all downstream variance is attributable to inputs.
- **Batch 1 (130 solves) failed, was repaired, and the cause was ENVIRONMENTAL — not the parameter
  space (2026-08-07).** 19 runs hit the 7,200 s limit, **18 of them silently** (see the flag bug
  above), and they were not randomly placed: **all at `budget_pct` 26.67%**, confined to **2 of the
  10 trajectories** — damage correlated with a factor level, the one thing a Morris design cannot
  absorb. Fix = `ENSEMBLE["time_limit"]` **7200 → 21600** + delete those 19 run dirs + re-run `run()`
  (resumable → 111 skipped, 19 re-solved). **The re-solves took 109-2,904 s, median 212 s** — same
  parameters, same `agg_factor`/solver/`workers`/`threads`, only the cap differed, and a cap cannot
  make a solve faster. So the stalls were **machine contention / memory pressure** (three heavy
  neighbour-penalty solves overlapping), NOT LP degeneracy at that budget level — an earlier
  degeneracy reading of the same numbers was wrong. Practical lesson: **a wall-clock cap is a poor
  convergence proxy**, since it conflates "hard problem" with "busy machine", and the batch stayed
  silently corrupt because the only validity test was on area. Watch `solve_seconds` spreads across
  a batch as a load symptom, and keep `agg_factor`/solver/`highs_solver`/`threads` identical across
  re-runs (thread count can change where an interior-point solve stops).
- **Phase 3** = 130 solves (r(k+1)). Metrics: `dissim_vs_base` (1 − Jaccard vs baseline, primary),
  `held_*` per feature, and `pct_region` as a **deliberate validity check** — selected area must
  track `budget_pct` and nothing else. Outputs μ*/σ table, the μ*-vs-σ scatter, and **per-cell μ\***
  maps (computed by a vectorised elementary-effects routine, since 300k SALib calls is infeasible;
  `cross_check()` asserts it equals SALib on a scalar — verified to 1e-16). Figures → `figures/`.
- **The primary metric's REFERENCE was wrong until 2026-08-07, and fixing it changed the headline.**
  `add_baseline_metrics(df, A, base_row=0)` took row 0 of the **Morris batch** as the reference, not
  the unperturbed baseline — despite `baseline_overrides`' own docstring saying the G2 run "doubles
  as the reference". morris/run_0000 is an arbitrary design corner (budget 26.7%, climate corridors
  ×4, intactness ×4, biomass carbon ×0.25, target 50%) sitting **Jaccard 0.67 from `baseline_2km`**.
  The tell was `dissim_vs_base` bottoming out at exactly 0.000 — a map compared with itself.
  Consequences: (1) a factor whose reference level sits at an END of its range can only be stepped
  one way, so its effects come out one-signed and μ collapses onto μ* (climate corridors read
  μ = −μ* exactly; macrorefugia μ = +μ*) — an artefact read as a finding; (2) the **μ\* ranking
  moves** — biomass carbon 3rd → **1st**, neighbour penalty 5th → 3rd, budget_pct 1st → 2nd.
  Signature is now `add_baseline_metrics(df, A, domain)`, reading `baseline_2km/run_0000` off disk;
  `base_row` is GONE so any stale call fails loudly. Verified against a **reference-free** ranking
  (per-cell μ* averaged over cells — built from consecutive-run differences, no baseline enters):
  it matches the corrected order to adjacent swaps, the as-run order much worse. Re-deriving is
  metric-only, **no re-solving**.
- **Read μ\* and σ, NOT μ.** `dissim_vs_base` is a *distance from a reference*, so the response
  surface is V-shaped in every factor and signed μ only reports which side of the baseline the
  trajectory steps fell on. The same V-shape **inflates σ** — every factor lands at σ/μ* 1.0–1.4,
  so "5+ survivors with high σ → Sobol'" is being fed a contaminated σ. Do not commit to Phase 4
  on it. Related: with `num_levels=4` the sampled levels are 0, ⅓, ⅔, 1 of each range while every
  baseline value is at 0.5 (×1 multiplier, budget 30%, penalty 1e-5), so **11 of 12 factors are
  off-baseline in every run** (only `target_pct=1.0` is sampled, as an endpoint) and dissim has a
  positive floor of 0.221. Valid for screening; the absolute level is NOT "how far plausible
  perturbations push the published map".
- **μ\* is predicted by LEVERAGE, not by ecological importance** — Spearman(μ*, leverage) =
  **+0.922** over the 8 continuous layers (Gini scores the same +0.922 and was the original
  reading, but it is a CORRELATE; leverage is the mechanism — see `leverage_core.py` above). So
  "the map is insensitive to how we weight connectivity / richness / refugia / intactness" is true,
  but the mechanism is **those layers cannot span enough captured-fraction to move a 30%-of-area
  selection** — a statement about the data (and, for two of them, about our own preprocessing),
  not a validation of the priorities. State the mechanism; a reviewer who spots it unacknowledged
  reads the bare claim as spin.
- **The 2026-08-17 redesign came out of this.** Leverage reproduces the whole Morris ranking with
  ZERO solves, so the screening's real yield was a mechanism, not a ranking. Consequences: two of
  the four "inert" layers were inert because of an ADDITIVE orientation flip (macrorefugia fixed to
  `1/v`; gHM left alone and reported), carbon's dominance was retargeted rather than re-weighted,
  and `neighbor_penalty` — 3rd of 12 — was removed from the optimizer entirely. **The Morris table
  in `docs/context_y2y_wide_methods.md` is therefore superseded** and must be re-derived after the
  re-solve; the leverage table predicts the new order (macrorefugia 12th → ~3rd–4th).
- **Weight-sensitivity ≠ content-sensitivity.** Morris varies *how much you weight* a layer; the
  Phase-1a QA varied *which version of the layer you use*. Macrorefugia being weight-inert does NOT
  discharge that QA's **MATERIAL** verdict — a different SSP/horizon changes the layer's spatial
  pattern, not its weight (the six realizations disagreed at Jaccard 0.46). The scenario factor
  still needs testing on its own terms.
- **PHASE 4 (Sobol') IS DROPPED — decided 2026-08-17, and this is a pre-registered gate outcome
  that must stay documented, not a silent omission** (there is already one live pre-registration
  deviation in the climate-scenario factor; a second undocumented one reads as a pattern). Four
  reasons: (1) **the gate cannot fire** — it triggers on "high σ" as evidence of interaction, but
  σ is inflated by the V-shaped distance metric, and the σ/μ* pattern (1.01–1.12 for the top four
  factors, 1.33–1.67 for the rest, rising as μ* falls) is scatter scaling inversely with effect
  size, i.e. a NOISE signature, not an interaction one; (2) **Sobol' inherits the contaminated
  metric and is hurt more by it** — Jaccard is bounded and compressed into ~[0.221, 0.550], so
  variance decomposition reads saturation as interaction, and Sobol' indices are defined relative
  to the input distribution, which here is an arbitrary ×0.25–×4 hypercube (a ranking degrades
  gracefully under a bad box; apportioned percentages do not); (3) **marginal information is
  small** — the ranking is now known twice, once analytically via leverage; (4) **cost**, measured
  off this batch (mean solve 1,001 s, workers=3): 1,792 solves ≈ **6.9 days** at N=128 without
  second order, 3,328 ≈ 12.8 days at SALib's default, 13,312 ≈ 51 days at N=512 — the "~4 days" in
  the original gate was off by an order of magnitude.
  **Replaced by a baseline-anchored plausible-range ensemble** (baseline as a real design point,
  defensible ranges instead of ×0.25–×4, ~40–60 solves) whose per-cell **selection frequency** is
  both the robustness answer Y2Y actually asks for and the surface post-hoc delineation grows
  candidate areas from — and a partial substitute for the MGA gap-portfolio while that was
  licence-blocked (unblocked 2026-08-26). Note the whole ensemble is now affordable at **full 1 km** (12 s/solve without
  the neighbour penalty), so the 2 km screening compromise and the G2 scale-transfer gate are moot.
- Requires **SALib** (added to `requirements.txt`). Phases 1b / 5 / 7 remain out of scope.

### `04a/04b/04c` — three results notebooks over `results_core.py` (Python)

> **04a MOVED (2026-08-18): the corridor-wide results notebook is now
> `analyses/y2y/04_results.ipynb`** (Python bootstrap added; its `RUN` variable selects which
> Gate-0 arm to deep-dive, and `rc.load(analysis, run=...)` is the mechanism). 04b/04c remain at
> root and are unchanged. Everything below about the shared views applies to all three.

**04 was split (2026-07-20)** to match 03: `04a_y2y` / `04b_north_bc` / `04c_ab_foothills`,
each `import results_core as rc` then `A = rc.load(ANALYSIS)` and one cell per view
(`rc.radar(A)`, `rc.new_map(A)`, `rc.consequences(A)`, …). Per-analysis 04 knobs live in
**`config.RESULTS_04[key]`** (region_label, cluster_select, **benchmark** spec, benchmark_title,
manual_area). **Contribution / efficiency denominators = the FULL Y2Y totals** (read off the
whole stack), so "% of Y2Y" is literally correct even for a cropped sub-region (a window area =
its share of the whole corridor); area% uses the full-Y2Y PU count. The **benchmark** block (the
"existing protection" star-plot set) is per-analysis: y2y = the 6 featured parks + Ross River;
north_bc = the 4 draft IPCA anchors; ab_foothills = the existing PAs ranked by cells inside the
foothills window. Figure names: `benchmark_*` / `manual_*` / `clusters_new_*`. 04a reproduces the
legacy y2y figures. **`bench_map` also draws the run's `new_mask` (2026-08-05)** in the same wheat as
the clusters map, so the benchmark parks can be read against where the solution actually expands —
the two maps share one constant, `results_core.NEW_ALLOC_COLOR` (was a local `OTHER` inside
`new_map`). Applies to all three 04x notebooks, since `bench_map` is shared. **`bench_map` also
appends the manual area as the LAST numbered entry** (y2y: "7. Ross River IPCA — proposed"), in its
own crimson rather than the next tab10 hue so it does not read as a seventh existing park; numbering
continues from `len(B["ids"])`, and the block is guarded by `if A.manual` so 04b/04c are unaffected.
**`manual_block` is therefore STAR PLOTS ONLY** — its standalone map was near-identical to the
benchmark map. `output_data/iter6_y2y/figures/manual_area_map.png` is now stale and no longer
regenerates. **`04_results_analysis.ipynb` is the legacy y2y-only monolith** (retire like
03).

**`footprint_audit(A)` (added 2026-08-17, 04a; runs after `build_stacks`).** The reporting half of
the "leave gHM alone" decision. Prints mean raw gHM for selected / locked-PA / NEW-allocation /
unselected, the selection rate inside the gHM top 10/1/0.1% tails against the 30% indifference
line, and Spearman(raw gHM, each feature). **The headline is the group split, and it reverses the
obvious reading:** the whole solution looks intact (0.048 vs 0.053 regional) only because the
locked PAs are already at 0.022; the optimizer's OWN new selection is at **0.074 — more modified
than the 0.055 land it passed over**. Cause: intactness holds ~1% of the objective's swing and
cannot counterweight AOH richness, which correlates with gHM at **+0.636 (birds) / +0.607
(mammals)** because richness peaks in the productive low valleys where people settle. Reads RAW gHM
from `cleaned_aligned/` (the hand-off layer is `1−gHM`) and skips gHM's own feature in the
correlation table (it would score −1.000 by construction).

**Consequences-table presentation (2026-07-28).** Columns carry a **two-level header**: level 0 =
the group — `"Alternatives (new options)"` (the NEW clusters) vs
`"Established Protected/Priority Areas"` (benchmark + manual, e.g. Ross River) — level 1 = the
area name. NEW clusters are named **`Option 1..N`** in `_select_clusters` order (the raw
connected-component id stays internal); `new_map` annotates the same 1..N, so map ↔ table ↔ star
plots cross-reference. Benchmark areas keep their real park/IPCA names. Every table cell is
rounded AND printed at **≥ 2 significant figures** via `_dec(v, dp)` — the per-row `dp` is now a
*minimum*, so a 0-1 index or a tiny sub-region contribution no longer flattens to `0.0`/`1.0`
(the whole ab_foothills contribution table read "0.0 / 0.1"). The tables print through one
per-cell string formatter (`_fmt`) with the long definition as a caption instead of `index.name`
(which padded the label column); the CSVs still carry it. `heatmaps` draws the group split as a
divider + group captions. Below describes the shared views, unchanged from the monolith:

### `04_results_analysis.ipynb` (LEGACY, y2y-only) — results (Python, kernel `y2y-geo`)

Adapts to the run type read from `run_summary` (objective/decision). **Whole-network views:**
radar (captured fraction per input vs a 30% area-share ring), allocation/priority map,
existing-vs-new map, trade-off table. **Cluster decomposition** (needs `BOUNDARY_PENALTY>0`):
splits the result into **NEW candidate areas** (`selected & not-PA`) and **EXISTING PA
clusters** (`scipy.ndimage.label`, 8-conn), each with a numbered map + **value-profile star
plots** — each axis = mean within the cluster of an input **scaled 0–1 over the whole region**
(5th–95th pctile) = relative richness vs the region. New-vs-PA profiles = gap analysis. Knobs
`CLUSTER_MIN_CELLS` / `CLUSTER_MAX_PLOTS`. Needs `scipy` + `matplotlib` in `.venv`. Figures →
`figures/`.
