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
Built as Jupyter notebooks, run cell-by-cell. The eventual pipeline produces an
**aligned raster stack** that feeds `prioritizr` (in R) — **not there yet**.

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
  (+ `ipykernel jupyterlab`). Pinned in `requirements.txt` (`pip freeze`).
- Jupyter kernel registered as **`y2y-geo`** (display "Python (y2y-geo)"). Select it
  for all notebooks here. System GDAL is 3.12.2; rasterio/fiona ship bundled GDAL wheels.

## Data (`./input_data`, ~24.5 GB)

Mostly GeoTIFF/COG; one VRT mosaic; **no NetCDF present** (the AdaptWest climate layer
is extracted GeoTIFFs, not NetCDF as originally expected).

Datasets in scope (one inventory row each):
- `human_modification` — Theobald gHM v3 (VRT mosaic `HM_Y2Y_2024_90_60land.vrt`)
- `transboundary_connectivity` — Pither et al. omnidirectional connectivity
- `climate_corridors` — Carroll et al. 2018 current-flow centrality (**was a `.zip`**)
- `climate_type_macrorefugia` — Carroll 2023 / AdaptWest backward climatic velocity
- `irrecoverable_carbon` — Berman/McDowell irrecoverable carbon (3 pools)
- `iucn_efg` — IUCN GET EFG Level 3 (~109 GeoTIFFs, already extracted)
- `aoh_richness_mammals` / `aoh_richness_birds` — Lumbierres AOH richness, **"all" (not Red List)**

Reference / excluded:
- `y2y_boundary/y2y_region_boundary_2013.gpkg` — corridor reference extent for the
  coverage flag (a vector; **not** a raster inventory row).
- **Not using:** `bhi_beri_parc/`, `elevational_diversity/`.

## Structure — two notebooks + shared config

- **`config.py`** = single source of truth imported by both notebooks: `DATASETS`
  registry, grid params (`TARGET_CRS`/`TARGET_RES_M`/`BUFFER_KM`), discovery helpers
  (`is_raster`/`find_rasters`/`pick_representative`), and `study_area()`. Add a dataset
  by adding one entry. Per-entry flags: `multi` (True only for `iucn_efg`), `resampling`
  (`average`/`bilinear`/`nearest`), `build_vrt` (True only for `human_modification`).
  Both notebooks `importlib.reload(config)` in their import cell to pick up edits.
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

Reproject/resample/clip every layer to the shared grid (ESRI:102008, 1 km, Y2Y boundary
buffered by `BUFFER_KM`) → coregistered stack in `input_data/cleaned_aligned/` (EFGs in
an `iucn_efg/` subfolder). Ethan runs it; heavy.

- **Engine = system `gdalwarp`/`gdalbuildvrt` via subprocess** (osgeo bindings are NOT in
  the venv; system GDAL CLIs are on PATH). One streamed reproject+resample+cutline-clip
  per layer; reads only the Y2Y window so global rasters aren't warped in full
  (clip-before-reproject is implicit). Fixed `-te`/`-tr` → every output shares the grid.
- gHM VRT is rebuilt from its 4 tiles in-workflow (`gdalbuildvrt`) then aligned.
- EFGs: warp all 109, then **drop any with no presence (value > 0) inside the corridor**
  — assumes EFG values encode occurrence as `> 0`; verify if kept/dropped looks off.
- Final cell asserts all outputs share CRS/transform/shape. Grid ≈ 1286 × 3312 cells.
