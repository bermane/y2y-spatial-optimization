"""Shared configuration for the Y2Y spatial-optimization notebooks.

Single source of truth imported by both `01_raster_inventory.ipynb` (exploration)
and `02_preprocess_align.ipynb` (cleaning / alignment): dataset registry, target-grid
parameters, and the raster-discovery helpers. Add a dataset by adding one entry to
`DATASETS`; no logic changes needed.
"""

from pathlib import Path

# ---- Project paths -------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parent  # repo root (where this file lives)
INPUT_DIR = PROJECT_DIR / "input_data"

# Corridor reference extent (vector) for the coverage flag and the study area.
CORRIDOR_REF = INPUT_DIR / "y2y_boundary" / "y2y_region_boundary_2013.gpkg"

# Protected-areas polygons (vector) -> rasterized to the grid as the PA lock-in mask.
PA_VECTOR = INPUT_DIR / "y2y_protected_areas" / "y2y_protected_areas_2025.gpkg"

# Aligned outputs from 02 live inside input_data/ (EFGs in an iucn_efg/ subfolder).
#   ALIGNED_DIR  : intermediate, single-layer warps (stage 1, raw orientation)
#   HANDOFF_DIR  : final oriented + masked COGs on the canonical grid (R reads these)
ALIGNED_DIR = INPUT_DIR / "cleaned_aligned"
HANDOFF_DIR = INPUT_DIR / "aligned_stack"

# Prioritizr results from 03 (R) land here; 04 (Python) reads them back.
#   RESULTS_DIR    : root for all optimization outputs
#   RESULTS_SUBDIR : per-run folder (objective + budget tag)
#   MANIFEST_PATH  : the Python->R hand-off contract describing the HANDOFF_DIR stack
RESULTS_DIR = PROJECT_DIR / "output_data"
RESULTS_SUBDIR = "iter1_minshortfall30"
MANIFEST_PATH = HANDOFF_DIR / "manifest.json"

# ---- Target grid (decided 2026-06-10; see CLAUDE.md) ---------------------
TARGET_CRS = "ESRI:102008"   # North America Albers Equal Area Conic
TARGET_RES_M = 1000          # 1 km, first iteration
BUFFER_KM = 20               # study area = Y2Y boundary buffered by this many km

# ---- QA knobs (02) -------------------------------------------------------
# Connectivity current-flow has a long high tail (partly resistance-model
# artefact). OPEN decision: 02 prints its distribution; set a percentile here to
# cap pinch points (e.g. 0.999), or leave None to keep raw. Do not bake silently.
CONNECTIVITY_CAP_PCTILE = None
# Carbon tail QA: cells above this percentile are *flagged* for review (not
# transformed). Winsorize only confirmed artefacts after inspection.
CARBON_FLAG_PCTILE = 0.999

# ---- Prioritizr run parameters (03) -------------------------------------
# Single source of truth for the optimization; written into manifest.json so the
# R notebook reads them instead of hard-coding. Iteration 1: minimum-shortfall
# objective with a 30%-of-region area budget (existing PAs locked in and counted
# toward it), a Gurobi gap-portfolio of near-optimal alternatives, EFG down-
# weighting, and an (initially off) connectivity penalty for contiguity.
# Solver: "highs" = single solution, open-source, NO license cap (use for rapid
# prototyping today); "gurobi" = enables the MGA gap-portfolio (needs an unlimited
# academic license -- the trial license is size-limited and cannot solve this).
SOLVER = "highs"
SOLVER_TIME_LIMIT = 1800     # seconds; caps the solve and returns the best so far (0 = no cap)
# HiGHS LP algorithm: "simplex" (dual simplex, default) struggles on the huge sparse
# boundary-penalty LP; "ipm" (interior point) plows through it far faster. Same LP optimum.
# "choose" lets HiGHS decide. Ignored when no boundary penalty (clean LP solves fine either way).
HIGHS_SOLVER = "ipm"
# Decision type: "binary" = each cell selected or not (a reserve; the real formulation,
# but the MILP is too big for HiGHS at 1 km). "proportion" = fractional 0-1 allocation per
# cell -> a pure LP that HiGHS solves fast at full 1 km. Use "proportion" for the rapid
# prototype; "binary" with Gurobi for the real run.
DECISION_TYPE = "proportion"
# Objective (within the 30%-of-area budget):
#   "min_shortfall" = minimize the weighted shortfall from per-feature targets (TARGET_PCT).
#       With TARGET_PCT = 1.0 this maximizes the captured FRACTION of every input, balanced
#       across inputs (each on a 0-100% scale) -- "protect 30% of area, get the most full
#       value of every input." Scale-invariant.  <-- current choice
#   "max_utility"  = maximize total (weighted) captured amount; value-first, no floor (can
#       under-serve some inputs). NOT scale-invariant.
#   "min_set"      = ignore the budget; minimize AREA needed to meet TARGET_PCT of every input.
OBJECTIVE = "min_shortfall"
# Prototype coarsening: >1 aggregates the grid in 03 by this factor (2 -> 2 km).
PROTOTYPE_AGG_FACTOR = 2
BUDGET_PCT = 0.30            # area budget = 30% of the region (30x30); binds for both objectives
TARGET_PCT = 1.0             # per-feature target (min_shortfall/min_set). 1.0 = maximize the
                             # captured fraction of each input within the budget (balanced)
# 03 normalizes each feature so its TOTAL = NORM_TOTAL (conditioning constant). With a 100%
# target the target equals the full total, which must stay < 1e6 for prioritizr's presolve;
# 1e5 keeps it safe with well-scaled coefficients. min_shortfall is scale-invariant, so this
# does not change the solution.
NORM_TOTAL = 1e5
OPT_GAP = 0.10               # relative MIP gap (raise for a faster, rougher prototype)
PORTFOLIO_N = 8              # number of near-optimal alternatives (gurobi MGA portfolio only)
PORTFOLIO_GAP = 0.10         # pool gap: keep solutions within 10% of optimal shortfall
# Connectivity penalty magnitude is scale-dependent: start at 0 for a baseline
# solve, then raise after 03 prints the connectivity-matrix scale (see notebook).
CONNECTIVITY_PENALTY = 0.0
# Boundary penalty = compactness / anti-scatter (clustering). 03 normalizes the boundary
# to edge units, so this is "shortfall-equivalent cost per exposed cell edge". TUNE: if the
# map is still scattered, raise x10; if the radar drops well below the target (representation
# sacrificed for compactness), lower it. 0 = off. NOTE: starting guess -- boundary penalties
# span orders of magnitude; expect to tune. ON now to force clustering into coherent blocks
# (so 04 can decompose them into candidate areas). 03 prints the boundary/objective scale.
BOUNDARY_PENALTY = 1e-4

# Features to exclude from the optimization (kept in the aligned stack, dropped from the
# manifest 03 reads). Use to trial feature subsets without re-running 02's heavy warp.
EXCLUDE_FEATURES = ["irrecoverable_carbon_sl_soc"]   # subsoil carbon; keep only m_soc for now

# ---- Results analysis (04) ----------------------------------------------
# Decompose the selected network into spatial clusters (candidate areas) for per-cluster
# value-profile star plots. Read directly by 04 (imports config); not needed in the manifest.
CLUSTER_MIN_CELLS = 25   # drop connected components smaller than this (~100 km^2 at 2 km)
CLUSTER_MAX_PLOTS = 16   # cap the per-cluster small-multiples grid (largest clusters first)

# ---- Raster discovery ----------------------------------------------------
# Raster extensions to characterize/align; GDAL sidecars are excluded.
RASTER_EXTS = {".tif", ".tiff", ".vrt", ".img", ".asc", ".nc"}
SIDECAR_SUFFIXES = (".aux.xml", ".ovr", ".xml")


def is_raster(p):
    """A raster file we should characterize (excludes GDAL sidecars)."""
    name = p.name.lower()
    if name.endswith(SIDECAR_SUFFIXES):
        return False
    return p.suffix.lower() in RASTER_EXTS


def find_rasters(cfg):
    """All rasters under a dataset path (recursive), optionally filtered by `include`."""
    rasters = sorted(p for p in cfg["path"].rglob("*") if p.is_file() and is_raster(p))
    inc = cfg.get("include")
    if inc:
        rasters = [p for p in rasters if inc.lower() in p.name.lower()]
    return rasters


def pick_representative(cfg, rasters):
    """Choose the representative raster: explicit filename, then substring, else first."""
    if not rasters:
        raise FileNotFoundError(f"No rasters found under {cfg['path']}")
    if cfg.get("representative"):
        for p in rasters:
            if p.name == cfg["representative"]:
                return p
    if cfg.get("rep_contains"):
        for p in rasters:
            if cfg["rep_contains"].lower() in p.name.lower():
                return p
    return rasters[0]


def study_area(buffer_km=BUFFER_KM):
    """Y2Y boundary reprojected to TARGET_CRS and buffered by `buffer_km` (metres in
    Albers). Returned GeoDataFrame is used for both clipping and EFG overlap tests."""
    import geopandas as gpd  # imported lazily so config stays light for 01

    gdf = gpd.read_file(CORRIDOR_REF).to_crs(TARGET_CRS)
    gdf["geometry"] = gdf.buffer(buffer_km * 1000)
    return gdf


# ---- Dataset registry ----------------------------------------------------
# One entry == one inventory row (01) and one (or many, for `multi`) aligned
# outputs (02). Fields:
#   path           : dataset folder (globbed recursively)
#   representative : exact filename used as the single raster (01; single-file in 02)
#   rep_contains   : substring fallback to pick the representative
#   include        : substring filter for which rasters count
#   citation       : source attribution
#   multi          : True if the dataset is many rasters aligned individually (EFGs)
#   resampling     : 02 resampling method -- "average" (down-sample fine continuous),
#                    "bilinear" (up-sample coarse / near-1 km continuous),
#                    "nearest" (categorical)
#   build_vrt      : True -> 02 rebuilds a mosaic VRT from the tiles before aligning
#   orient         : value transform so HIGHER = more conservation value (02, post-warp):
#                    "complement" -> 1 - x   (gHM modification -> intactness; x in [0,1])
#                    "invert"     -> vmax - x (backward velocity -> refugial value; vmax
#                                    over the study area, documented at run time)
#                    omitted/None -> already "more = better", leave raw
#   is_feature     : True (default) -> a prioritizr feature; contributes to the PU mask
#                    if continuous. (All current entries are features.)
DATASETS = {
    "human_modification": {
        "path": INPUT_DIR / "human_modification",
        # VRT was deleted; 01 reads the main tile. 02 rebuilds the VRT from all tiles.
        "representative": "HM_Y2Y_2024_90_60land-0000000000-0000000000.tif",
        "multi": False,
        "resampling": "average",  # gHM ~90 m -> 1 km
        "orient": "complement",   # gHM (0-1 modification) -> intactness 1 - gHM
        "build_vrt": True,
        "citation": "Theobald et al. 2024, gHM v3 human modification",
    },
    "transboundary_connectivity": {
        "path": INPUT_DIR / "transboundary_connectivity",
        "representative": "Raw_CurrentDensity_Map.tif",
        "multi": False,
        "resampling": "average",  # native ~300 m -> 1 km (down-sample)
        "citation": "Pither et al., transboundary omnidirectional connectivity",
    },
    "climate_corridors": {
        "path": INPUT_DIR / "climate_corridors" / "centrality",
        "include": "currentflow",  # current-flow centrality (not the shortest-path tifs)
        "representative": "currentflow.tif",
        "multi": False,
        "resampling": "bilinear",  # ~5 km -> 1 km
        "citation": "Carroll et al. 2018, current-flow centrality",
    },
    "climate_type_macrorefugia": {
        "path": INPUT_DIR / "climate_type_macrorefugia" / "ensemble_8gcm",
        "include": "bwvel731",  # backward climatic velocity scenarios only
        "rep_contains": "bwvel731_ensemble_8gcm_585_2071_2100",  # chosen scenario
        "multi": False,
        "resampling": "bilinear",
        "orient": "invert",  # low backward velocity = high refugial value -> vmax - v
        "citation": "Carroll 2023 (AdaptWest), backward climatic velocity",
    },
    "irrecoverable_carbon_biomass": {
        "path": INPUT_DIR / "irrecoverable_carbon",
        "include": "biomass",
        "representative": "irrecoverable_biomass_2021_t_ha.tif",
        "multi": False,
        "resampling": "average",
        "citation": "Berman/McDowell, irrecoverable carbon (biomass)",
    },
    "irrecoverable_carbon_m_soc": {
        "path": INPUT_DIR / "irrecoverable_carbon",
        "include": "m_soc",
        "representative": "irrecoverable_m_soc_t_ha.tif",
        "multi": False,
        "resampling": "average",
        "citation": "Berman/McDowell, irrecoverable carbon (mineral soil organic carbon)",
    },
    "irrecoverable_carbon_sl_soc": {
        "path": INPUT_DIR / "irrecoverable_carbon",
        "include": "sl_soc",
        "representative": "irrecoverable_sl_soc_t_ha.tif",
        "multi": False,
        "resampling": "average",
        "citation": "Berman/McDowell, irrecoverable carbon (subsoil organic carbon)",
    },
    "iucn_efg": {
        "path": INPUT_DIR / "iucn_efg" / "all-maps-raster-geotiff",
        "multi": True,  # 109 rasters; 02 aligns every one that overlaps the study area
        "resampling": "nearest",  # categorical occurrence maps
        "citation": "IUCN GET Ecosystem Functional Groups, Level 3",
    },
    "aoh_richness_mammals": {
        "path": INPUT_DIR / "aoh_richness" / "Richness_mammals",
        "include": "all",  # "all", not Red List
        "rep_contains": "all",
        "multi": False,
        "resampling": "average",  # AOH ~100 m -> 1 km
        "citation": "Lumbierres et al., AOH species richness (mammals, all)",
    },
    "aoh_richness_birds": {
        "path": INPUT_DIR / "aoh_richness" / "Richness_birds",
        "include": "all",
        "rep_contains": "all",
        "multi": False,
        "resampling": "average",
        "citation": "Lumbierres et al., AOH species richness (birds, all)",
    },
}


# ---- Python -> R hand-off contract ---------------------------------------
def write_manifest(handoff_dir=HANDOFF_DIR, manifest_path=MANIFEST_PATH):
    """Describe the aligned hand-off stack as JSON so 03 (R) reads an explicit
    contract instead of globbing/guessing. Metadata-only -- safe to run anytime
    without re-warping. Output filename convention (set by 02): <dataset_key>.tif
    for single-raster features, EFGs in iucn_efg/, plus cost_uniform.tif and
    mask_protected_areas.tif."""
    import json
    import math
    import rasterio  # local import keeps config light for 01

    def rel(p):
        return Path(p).resolve().relative_to(PROJECT_DIR).as_posix()

    def clean_nodata(nd):
        # NaN is not valid JSON; emit null. R reads the actual NaN NoData from the
        # GeoTIFF itself, so the manifest only needs to flag integer sentinels (255).
        if nd is None or (isinstance(nd, float) and math.isnan(nd)):
            return None
        return nd

    def layer_meta(path, name, role, orient=None, citation=None):
        with rasterio.open(path) as src:
            return {
                "name": name,
                "path": rel(path),
                "role": role,
                "dtype": src.dtypes[0],
                "nodata": clean_nodata(src.nodata),
                "orient": orient,
                "citation": citation,
            }

    handoff_dir = Path(handoff_dir)
    layers = []

    # Continuous features: every single-raster dataset entry (minus exclusions).
    for key, cfg in DATASETS.items():
        if cfg.get("multi") or key in EXCLUDE_FEATURES:
            continue
        layers.append(
            layer_meta(
                handoff_dir / f"{key}.tif", key, "feature_continuous",
                orient=cfg.get("orient"), citation=cfg.get("citation"),
            )
        )

    # Categorical EFG features (kept survivors from 02; minus exclusions).
    efg_citation = DATASETS["iucn_efg"]["citation"]
    for p in sorted((handoff_dir / "iucn_efg").glob("*.tif")):
        if p.stem in EXCLUDE_FEATURES:
            continue
        layers.append(layer_meta(p, p.stem, "feature_efg", citation=efg_citation))

    # Cost layer and the locked-in (protected-areas) mask.
    layers.append(layer_meta(handoff_dir / "cost_uniform.tif", "cost_uniform", "cost"))
    layers.append(
        layer_meta(
            handoff_dir / "mask_protected_areas.tif",
            "mask_protected_areas", "mask_locked_in",
        )
    )

    # Canonical grid, read from a representative continuous feature.
    with rasterio.open(handoff_dir / "human_modification.tif") as src:
        grid = {
            "crs": TARGET_CRS,
            "width": src.width,
            "height": src.height,
            "res_m": TARGET_RES_M,
            "transform": list(src.transform)[:6],  # affine a,b,c,d,e,f
            "bounds": [src.bounds.left, src.bounds.bottom,
                       src.bounds.right, src.bounds.top],
        }

    manifest = {
        "grid": grid,
        "params": {
            "solver": SOLVER,
            "solver_time_limit": SOLVER_TIME_LIMIT,
            "highs_solver": HIGHS_SOLVER,
            "objective": OBJECTIVE,
            "decision_type": DECISION_TYPE,
            "prototype_agg_factor": PROTOTYPE_AGG_FACTOR,
            "norm_total": NORM_TOTAL,
            "budget_pct": BUDGET_PCT,
            "target_pct": TARGET_PCT,
            "opt_gap": OPT_GAP,
            "portfolio_n": PORTFOLIO_N,
            "portfolio_gap": PORTFOLIO_GAP,
            "connectivity_penalty": CONNECTIVITY_PENALTY,
            "boundary_penalty": BOUNDARY_PENALTY,
            "results_dir": rel(RESULTS_DIR),
            "results_subdir": RESULTS_SUBDIR,
        },
        "layers": layers,
    }

    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, allow_nan=False)  # strict JSON for R/jsonlite
    return manifest_path
