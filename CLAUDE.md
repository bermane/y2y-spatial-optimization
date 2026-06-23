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
- `climate_type_macrorefugia` — Carroll 2023 / AdaptWest backward climatic velocity
- `irrecoverable_carbon` — Berman/McDowell irrecoverable carbon, **3 pools each its own
  feature** (`biomass`, `m_soc` mineral soil, `sl_soc` subsoil; all `t_ha` density)
- `iucn_efg` — IUCN GET EFG Level 3 (~109 GeoTIFFs, already extracted). Value scheme:
  `0`=absent/NoData, `1`=minor occurrence, `2`=major (Byte, paletted). Resample `nearest`.
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
  so re-running just that cell is cheap (no re-warp).

### `03_prioritizr.ipynb` — optimization (R, kernel `y2y-r`)

Builds + solves one `prioritizr` problem on the hand-off stack; writes results for 04. Reads +
validates `manifest.json`. **All run params come from `config.py` via the manifest.** Current
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

### `04_results_analysis.ipynb` — results (Python, kernel `y2y-geo`)

Adapts to the run type read from `run_summary` (objective/decision). **Whole-network views:**
radar (captured fraction per input vs a 30% area-share ring), allocation/priority map,
existing-vs-new map, trade-off table. **Cluster decomposition** (needs `BOUNDARY_PENALTY>0`):
splits the result into **NEW candidate areas** (`selected & not-PA`) and **EXISTING PA
clusters** (`scipy.ndimage.label`, 8-conn), each with a numbered map + **value-profile star
plots** — each axis = mean within the cluster of an input **scaled 0–1 over the whole region**
(5th–95th pctile) = relative richness vs the region. New-vs-PA profiles = gap analysis. Knobs
`CLUSTER_MIN_CELLS` / `CLUSTER_MAX_PLOTS`. Needs `scipy` + `matplotlib` in `.venv`. Figures →
`figures/`.
