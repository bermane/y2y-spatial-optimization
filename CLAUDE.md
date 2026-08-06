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
    HiGHS has no solution pool. The installed license is **TRIAL (size-limited ~2000 vars)**,
    so that real run is **blocked until a free academic license** is activated (`grbgetkey` →
    `~/gurobi.lic` should read `TYPE=ACADEMIC`; see `requirements-R.txt`). Meanwhile 03 runs a
    **HiGHS proportion-LP prototype** — the `highs` package IS used.

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

## Structure — two notebooks + shared config

- **`config.py`** = single source of truth imported by both notebooks: `DATASETS`
  registry, grid params (`TARGET_CRS`/`TARGET_RES_M`/`BUFFER_KM`), discovery helpers
  (`is_raster`/`find_rasters`/`pick_representative`), and `study_area()`. Add a dataset
  by adding one entry. Per-entry flags: `multi` (True only for `iucn_efg`), `resampling`
  (`average`/`bilinear`/`nearest`), `build_vrt` (True only for `human_modification`),
  `orient` (`complement` for gHM→intactness, `invert` for velocity→refugia, else raw).
  Also holds `HANDOFF_DIR`, `PA_VECTOR`, QA knobs `CONNECTIVITY_CAP_PCTILE` (None =
  no cap) / `CARBON_FLAG_PCTILE`, the **prioritizr run params** — `OBJECTIVE`
  (`min_shortfall`/`max_utility`/`min_set`), `BUDGET_PCT=0.30`, `TARGET_PCT=1.0`, `NORM_TOTAL`,
  `SOLVER`/`HIGHS_SOLVER`/`SOLVER_TIME_LIMIT`, `DECISION_TYPE`, `PROTOTYPE_AGG_FACTOR`,
  `OPT_GAP`, `PORTFOLIO_N/GAP`, `CONNECTIVITY_PENALTY`, `BOUNDARY_PENALTY`, `EXCLUDE_FEATURES`,
  the 04 cluster knobs (`CLUSTER_MIN_CELLS`/`CLUSTER_MAX_PLOTS`) — plus
  `RESULTS_DIR`/`RESULTS_SUBDIR`/`MANIFEST_PATH`, and
  `write_manifest()` (the Python→R contract writer). Notebooks `importlib.reload(config)`
  to pick up edits.
- **Resampling rule:** native finer than 1 km → `average` (down-sample); coarser/≈1 km →
  `bilinear` (up-sample); categorical (EFG) → `nearest`.

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
  backward velocity→refugia (`vmax−v`, vmax over the reference extent); carbon/connectivity
  already more=better. All features forced non-negative.
- **One PU mask** = cells valid in **all continuous features** (EFG `0`=absent is valid, so
  EFGs don't constrain it). Applied identically to every feature **and** the uniform
  `cost_uniform`=1 layer → no cell valid in one layer but NoData in another.
- **QA (surface, don't silently transform):** flag carbon tail cells (`CARBON_FLAG_PCTILE`);
  print connectivity quantiles and cap **only** if `CONNECTIVITY_CAP_PCTILE` is set.
- **Outputs = COGs** in `input_data/aligned_stack/` (`HANDOFF_DIR`; EFGs in `iucn_efg/`):
  continuous features + cost are float32/NaN-NoData; EFGs + `mask_protected_areas` are
  uint8 with `255`=NoData (so EFG `0` stays a valid value).
- Final cell validates: identical grid, NoData consistency, **matching PU cell counts**,
  non-negativity, orientation spot-check. Grid = **1286 × 3312**, PU = **1,272,914 cells**;
  hand-off = 9 continuous + cost + PA mask + **40 EFGs**.
- **Last cell writes `aligned_stack/manifest.json`** via `config.write_manifest()` — the
  Python→R contract (per-layer role/dtype/NoData/orient + grid + run params). Metadata-only,
  so re-running just that cell is cheap (no re-warp). **03 also regenerates it** (same
  function), so this cell is now just the "stack is ready" marker — a `config.py` edit does
  **not** require a trip back to 02.

### `03a/03b/03c` — three analyses over `prioritizr_core.R` (R, kernel `y2y-r`)

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
- **Objective** = `OBJECTIVE` knob. Current **`min_shortfall` with `TARGET_PCT=1.0`** under a
  **30%-of-area budget** (`BUDGET_PCT`) ≡ maximize the captured *fraction* of every input.
  Also supports `max_utility` and `min_set`. **Caveat:** min-shortfall@100% favours spatially
  *concentrated* inputs (carbon dominates; some EFGs neglected) — unresolved, see memory.
- **Normalization:** each feature sum-normalized to total = `NORM_TOTAL` (1e5) so 100% targets
  stay < 1e6 (prioritizr presolve guard); scale-invariant for min-shortfall.
- **PAs locked in** (counted toward budget); **EFG down-weighting** (`add_feature_weights`,
  continuous @1, each EFG @1/40); `sl_soc` carbon excluded (`EXCLUDE_FEATURES`).
- **Solver/decisions:** `SOLVER="highs"` + `DECISION_TYPE="proportion"` (LP, ~99% integral) is
  the **working prototype** — the binary MILP chokes HiGHS presolve at 1 km, and the real
  **Gurobi MGA gap-portfolio** (`add_gap_portfolio`, binary) is **blocked by a TRIAL Gurobi
  license** (need a free academic one). The boundary-penalty LP needs `HIGHS_SOLVER="ipm"`
  (dual simplex times out). `SOLVER_TIME_LIMIT` caps the solve — **a timed-out run returns an
  infeasible point (area > budget); discard it.**
- **Spatial penalties:** `CONNECTIVITY_PENALTY` (corridors, off) and `BOUNDARY_PENALTY`
  (compactness/clustering, on — edge-normalized, uncalibrated). The boundary penalty adds a
  constraint per adjacent cell pair → huge LP → run at `PROTOTYPE_AGG_FACTOR=2` (2 km).
- Outputs → `output_data/<RESULTS_SUBDIR>/`: `portfolio.tif` (proportion→float, binary→uint8),
  `selection_frequency.tif`, `portfolio_representation.csv` (`relative_held` → 04 radar),
  `run_summary.json`.

### `05_corridors_north.ipynb` — least-cost corridors over `corridors_core.py` (Python)

**Standalone corridor analysis (2026-07-23), NOT prioritizr.** Connects the northern proposed
IPCAs + existing PAs with **least-cost routing** — the tool the prioritizr connectivity *penalty*
could not be (the penalty aggregates permeable land; this *routes* between nodes). Driver = the
transboundary connectivity current-density (with gHM as a barrier guard). `corridors_core.py`
(`skimage.graph.MCP_Geometric` cost-distance + Prim MST + traceback centre-lines + swaths); params
in `config.CORRIDORS["north"]`; outputs → `output_data/corridors_north/` (corridors.tif/.gpkg,
resistance.tif, corridor_summary.json). Kernel `y2y-geo`. Reuses `config._load_source` and the
`results_core` map colours. **Resistance = a config-driven BLEND of driver layers** (current-density
+ climate corridors + refugia, each stretched 0-1, weighted) × a gHM barrier — edit
`resistance.drivers`. **`corridor_ensemble`** (the MGA analog) perturbs the resistance `n_runs`
times → `corridor_frequency.tif` (robust core vs flexible) + `corridors_alt{k}.gpkg` (distinct
near-optimal networks). Tune `corridor_width_frac`, the driver weights, and
`ensemble.{n_runs,jitter}`.

**Driver scaling (`resistance.scale`, decided 2026-07-27).** `"minmax"` stretches each driver over
`[lo_pctile, pctile]`; `"zero_max"` is the old `layer/pctile`. minmax is required because the drivers
don't all start at zero — macrorefugia runs ~10-15, so zero_max left it near-constant and **inert**
(corr with resistance −0.03 → −0.10 after the fix). Anchors are **p1/p99**: NOT p0/p100 (connectivity's
p100=65.4 vs p95=3.86 is a single-pixel pinch-point tail; anchoring there flattens resistance to a 2.2×
spread and the router stops following the landscape), NOT p5/p95 (clipping the bottom 5% to 0
manufactures hard walls at `perm_floor`). Top-end clipping costs little either way — `resistance=1/perm`
compresses the good end by construction. Directions verified empirically: all three drivers correlate
negatively with resistance, and the aligned `human_modification` layer really is **intactness**
(`orient="complement"`), so `gHM = 1 − it` feeds `base**gHM` correctly.

**`run_scenarios` / `compare_map` (2026-07-28).** `config.CORRIDORS[key]["scenarios"]` names
driver-stretch variants (currently `p1_p99` = `primary_scenario`, `p5_p95`); a scenario overrides
**only** the stretch anchors. `cc.run_scenarios(A)` replaces the resistance→ensemble cells and solves
each end to end, stashing a snapshot per scenario on `A.scenarios` — it deliberately **drops
`A.cwd`/`A.mcp` between scenarios** (one float64 grid per node ≈ 800 MB at 1 km) and restores the
primary onto `A`, so `map`/`write_outputs` are unchanged. `cc.compare_map(A)` = one row per scenario
(corridors | robustness) + a difference panel; `cc.compare_resistance(A)` is a **separate** plot of the
resistance surfaces on a **shared** log scale (they were a greyscale backdrop inside `compare_map` —
which both collided with the grey PAs and cluttered the corridor panels). Both frame to the **working
region** via `_region_extent`/`_nodes_overlay` (drawing `A.outline` otherwise expands the axes to the
whole Y2Y and wastes the canvas on the empty southern tail; `map()` keeps its wider framing). Diff
palette avoids the PA grey: shared = orange `SHARED_COLOR`, per-scenario = purple/blue.
`write_outputs` writes the primary at the top level **plus** a full set per scenario in `<scenario>/`,
and adds `scenarios` + `scenario_jaccard` blocks to the summary. **Figures land in
`output_data/corridors_north/figures/` (`A.fig_dir`), not the project `figures/` dir.**
Pre-fix figures (raw swath): p1_p99 29,031 km²/1,187 centre-line cells, p5_p95 33,185/1,295,
**Jaccard 0.72**, both 1 connected group — same 44 MST edges and trunk, differing at a few links.
**Superseded by the node-land fix below — re-run 05 to refresh every corridor number and figure.**

**Corridor = NEW LAND only; nodes de-duplicated (2026-08-05).** Two defects, both in accounting, not
in routing. (1) The swath test passed *inside* the source node by construction — `cwd[i]` is 0 across
the whole of node i, so `field = cwd[i]+cwd[j]` sits at its minimum there — putting **37% of the raw
swath (10,843 of 29,031 km²) on ground that is already a PA or an IPCA proposal**, and making map
panel 1 (corridor drawn over nodes) contradict panel 3 (nodes drawn over frequency). `_network_from_cwd`
now returns `corridor = swath & ~node_union` (`A.node_union`, built in `load`); the raw swath survives
as `A.swath` → `swath_incl_node_land_km2` in the summary. All consumers agree now — map legend
("new land"), summary, gpkg/tif, and the star plots, which always used `corridor & ~nodes`.
(2) Both source layers mix **nesting designation tiers** and neither is de-duplicated (the PA dissolve
is by name only), so one place entered as two nodes: Teetł'it Gwinjik ⊂ Peel Watershed SMA/WA
(4,143 km², both IPCA), Fishing Branch Wilderness Preserve ⊂ its HPA (5,353 km², both PA), Neah
Conservancy ⊂ Ne'ah – Horseranch Range Deadwood Lake PA (2,293 km², both PA) — ~11,800 km²
double-counted, and those three nodes came out 100% "corridor". `_dedupe_nodes` merges nodes whose
**rasterized masks** share ≥ `nodes.dedupe_overlap_frac` (0.5) of the smaller — masks, not polygons,
because a shared cell is exactly what makes the cost distance 0. **45 → 42 nodes** (10 IPCA + 32 PA;
all three merges are within-layer, so the IPCA/PA map colours and the 04-style benchmark split are
untouched). Cross-layer overlap is only **384 km² (0.2%)** — all slivers, e.g. Dene Kʼéh Kusān wraps
*around* 11 BC parks clipping each by 2-63 km², which is why the test needs a fraction, not a cell.
Those slivers still yield zero-distance MST edges, so `n_mst_edges` is now reported alongside
`n_mst_edges_separated` (was 44 edges, only 29 between separated nodes). **Dedup does not change the
routing** — Prim over a zero-distance pair takes the zero edge and then connects the rest exactly as
the merged node would; it corrects the accounting only.

**`corridor_profile` — co-benefit audit (2026-07-28).** Value star plots for the corridors, reusing
04's `results_core.mask_profile` + `plot_stars` **unchanged**. `_profile_stacks` is a minimal stand-in
for `build_stacks` (which is coupled to a solved run): it hands `rc._scaled`/`_read_match`/
`_region_total` a namespace whose grid reference is **05's own grid**, so 05 stays standalone from
03/04. Compares three areas — corridor's own new land, proposed IPCAs, existing PAs.
**Mask must exclude node land** (as of 2026-08-05 `A.corridor` already does; the `& ~nodes` here is a
guard): swath bands radiate from the nodes, so **37% of the raw swath lies inside PA/IPCA polygons**
and profiling it whole would credit corridors with already-protected land (18,188 km² new, 1.43% of
Y2Y — this was always the right number, and is now what every other output reports too).
Two scalings coexist: richness = 0-1 over the **northern
window**; contribution/efficiency = **full-Y2Y** denominators. **Frame as an audit, not a scorecard**
— corridors are routed for permeability, so a low value axis is a finding. RESULT: corridors are
**complementary, not redundant** — per 1,000 km² they beat both PA sets on biomass carbon (0.127 vs
0.050/0.068), connectivity (0.105 vs 0.088/0.084) and AOH richness, while the PAs/IPCAs dominate
**soil carbon** (0.119-0.125 vs 0.063). Outputs `corridors_stars_{richness,contribution,efficiency}
.png` + `corridor_profile.csv`.

**Corridor SEGMENTS (`n_groups=10` = a CEILING on clusters, default).** The corridor is profiled per
geographic segment, not as one blob: **removing the node polygons cuts the network at every PA/IPCA,
so the connected components ARE the physical links** — 23 of them. **Changed 2026-08-05: the 10
LARGEST components seed the clusters and every remaining component is absorbed into its nearest
seed**, so the segments account for 100% of corridor area. The old top-10 cut left 13 components
(1,133 km², 6%) plotted nowhere — printed, but absent from the stars and the CSV, a coverage hole in
an audit whose point is completeness. **Seeded, not free clustering:** average-linkage over all 23
centroids was tried first and allocates panels by ISOLATION rather than importance — it spent two of
ten panels on 8 km² and 67 km² far-north slivers while merging the two biggest links away, and a
7-component cluster named after 2 touched nodes is a dishonest label. Seeding keeps **one panel = one
physical link + its small neighbours**, so the "X ↔ Y" naming holds and the profiles stay comparable
to the previous run. **Nearest by CELL, not centroid** (segments are long and sinuous, so a scrap can
be adjacent to a link but far from its centroid): one `distance_transform_edt` over the seed union
gives every cell its nearest seed cell, and each component's own closest cell picks the owner.
Result on p1_p99: 23 → 10 clusters, **437 to 3,162 km²**, seven of them multi-part; the seeds match
the previous CSV rows exactly (top row still 2,901 km²) and 17,055 + 1,133 = 18,188 km² reconciles.
Clusters are numbered **north→south**
and named by the nodes their cells touch (via `binary_dilation` against a node-id raster), e.g. "3.
Dene Kʼéh Kusān ↔ Nahanni"; `seg["parts"]` carries the component count and `seg["anchor_xy"]` puts
the map number on the LARGEST part (a multi-part cluster's overall centroid can fall on empty
ground). **IPCAs and existing PAs stay WHOLE units** — and are unaffected by the node de-duplication
above, since those rows are boolean unions (verified: masks bit-identical, 146,525 / 78,405 km²). `_short_node_name` strips the IPCA·/PA· prefix,
parentheticals and generic designations ("Nahanni National Park Reserve Of Canada" → "Nahanni") for
star titles — the full names collide on a 4.8" polar panel; map legend and CSV keep them.
`cc.corridor_group_map(A)` draws the numbered map from the same `A.groups`, so numbering cannot drift
from the stars. `n_groups=None` restores the single whole-network profile.

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
  and **flags** infeasible/timed-out runs — `analyze_morris()` then *refuses* rather than
  analysing around them, because a Morris design with holes is invalid.
- **Config**: `ENSEMBLE` (rscript/driver/workers/threads/agg_factor/time_limit) and `MORRIS`
  (r=10, num_levels=4, seed, and the **12 factors** — 8 continuous feature weights + EFG group,
  each as a log2 multiplier ×0.25–×4; `budget_pct`; `target_pct`; `neighbor_penalty` as log10).
  Climate scenario is deliberately NOT a factor (needs shared-anchor orientation + a headline
  re-solve; deferred with Phase 1b). `min_shortfall` is scale-invariant in the weights, so
  scaling all nine together is a **null direction** — state this in methods.
- **Gates before the batch**: **G1 equivalence** (driver at 1 km must reproduce
  `iter5_lp_1km_neighbor`: same PU/budget/locked, Jaccard 1.0) → **G2 scale transfer** (fresh 2 km
  baseline vs the 1 km headline; `iter4_lp_2km_compact` can't serve — wrong penalty, predates
  `neighbor_penalty`) → **G3 noise floor** (10 identical solves at the same thread config; with
  `OPT_GAP=0.10` solutions aren't proven optimal, and Morris effects are *differences*, so an
  effect below the floor is solver noise, not signal).
- **Phase 3** = 130 solves (r(k+1)). Metrics: `dissim_vs_base` (1 − Jaccard vs baseline, primary),
  `held_*` per feature, and `pct_region` as a **deliberate validity check** — selected area must
  track `budget_pct` and nothing else. Outputs μ*/σ table, the μ*-vs-σ scatter, and **per-cell μ\***
  maps (computed by a vectorised elementary-effects routine, since 300k SALib calls is infeasible;
  `cross_check()` asserts it equals SALib on a scalar — verified to 1e-16). Figures → `figures/`.
- Requires **SALib** (added to `requirements.txt`). Phase 4 (Sobol' vs crossed factorial) is
  decided at the Phase-3 gate; Phases 1b / 5 / 7 remain out of scope.

### `04a/04b/04c` — three results notebooks over `results_core.py` (Python)

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
