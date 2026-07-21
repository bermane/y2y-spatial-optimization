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

# ROI / lock-in vectors for the sub-regional analyses (03b/03c); see ANALYSES below.
#   DRAFT_PA_VECTOR  : 4 proposed IPCAs in northern BC (EPSG:3857) -> north_bc window + anchors.
#   AB_BOUNDARY      : Alberta provincial boundary (Natural Earth 1:10m admin-1).
#   FOOTHILLS_VECTOR : the AB mountain-front study polygon for ab_foothills. Derived from the
#                      Alberta Natural Regions & Subregions (2005) service (geospatial.alberta.ca),
#                      union of SIX subregions: Upper + Lower Foothills (Foothills NR), Foothills
#                      Fescue (Grassland NR), Foothills Parkland (Parkland NR), Montane + Subalpine
#                      (Rocky Mountain NR). ~118,092 km2, running the full length of AB to the US
#                      border and butting against every AB mountain park (incl. the high Kananaskis
#                      parks — Subalpine closes that gap). The strict "Foothills NR" alone (central
#                      AB only, 51-56N) stops well north of the border, hence the broader union.
DRAFT_PA_VECTOR  = INPUT_DIR / "y2y_northern_bc_proposed_ipcas" / "proposed_pa_v2_northern_bc.shp"
AB_BOUNDARY      = INPUT_DIR / "alberta_boundary" / "alberta.gpkg"
FOOTHILLS_VECTOR = INPUT_DIR / "ab_foothills" / "foothills.gpkg"

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
RESULTS_SUBDIR = "iter5_lp_1km_neighbor"
MANIFEST_PATH = HANDOFF_DIR / "manifest.json"

# ---- Target grid (decided 2026-06-10; see CLAUDE.md) ---------------------
TARGET_CRS = "ESRI:102008"   # North America Albers Equal Area Conic
TARGET_RES_M = 1000          # 1 km, first iteration
BUFFER_KM = 20               # study area = Y2Y boundary buffered by this many km

# ---- QA knobs (02) -------------------------------------------------------
# Connectivity current-flow has a long high tail (partly resistance-model
# artefact). None = raw (current). Only needed for the connectivity-penalty idea (deferred):
# the raw connectivity_matrix spans ~40,000x, so capping (~0.99, tighten to 0.95) would be
# required before that penalty is calibratable. 02 prints the distribution + capped count.
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
SOLVER_TIME_LIMIT = 43200    # seconds (12 h) -- an overnight cap for the 1 km NEIGHBOR-penalty
                             # trial. 2 km boundary-penalty LP solved in ~500 s; 1 km is a much
                             # bigger LP, so give it room. A timed-out HiGHS run returns an
                             # infeasible point (area > budget) -- discard it and coarsen / soften.
                             # NOT 0 = "no cap": prioritizr asserts is.count(time_limit), i.e. a
                             # POSITIVE integer, so 0 raises an assertion error and solves nothing.
                             # prioritizr's own "no limit" default is .Machine$integer.max.
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
# 1 = native 1 km. The BOUNDARY penalty is intractable here on HiGHS (hence the 2 km fallback),
# but the lighter NEIGHBOR penalty is being trialled at 1 km -- that is the point of this run.
# Downstream area (04) derives from the output resolution, so km^2 / area-% / efficiency stay
# correct at either resolution automatically.
PROTOTYPE_AGG_FACTOR = 1
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
# Connectivity penalty (corridor-following via transboundary_connectivity). OFF for now:
# the raw connectivity_matrix spans ~40,000x (pinch-point tail), so the penalty is
# uncalibratable without first capping the tail (CONNECTIVITY_CAP_PCTILE). Deferred -- Ethan
# will revisit. To try it: cap the tail, re-run 02, then set this from 03's printed scale.
CONNECTIVITY_PENALTY = 0.0
# ---- Compactness: pick ONE of the two anti-scatter penalties (or combine) ----
# Boundary penalty = compactness via exposed EDGES (perimeter). 03 normalizes the boundary to
# edge units, so this is "shortfall-equivalent cost per exposed cell edge". Worked at 2 km @
# 5e-5 (~500 s), but the per-adjacent-pair linearisation blows the LP up (2 km: ~1.3M rows /
# 980k cols) -> intractable at 1 km on HiGHS. 0 = off.
BOUNDARY_PENALTY = 0.0
# Neighbor penalty = compactness via NEIGHBOUR COUNT (penalises planning units with few
# selected neighbours; binary rook adjacency, derived from the raster). prioritizr explicitly
# recommends this one "for reducing spatial fragmentation in large-scale problems or when
# using open source solvers" -- i.e. exactly our 1 km + HiGHS bind, so it is the candidate for
# getting compactness at full resolution without Gurobi. 0 = off.
# CALIBRATION: separate scale from BOUNDARY_PENALTY -- it acts on INTERIOR adjacent pairs
# (~2 per selected cell) rather than the perimeter, so it needs a smaller coefficient. The 03
# solve prints the objective (iter4 @2 km was ~6.4); aim for the penalty term to land ~1-3 of
# that -- meaningful but not dominating. 1e-5 is a first guess: raise x10 if still fragmented,
# lower x10 if the radar/representation collapses.
NEIGHBOR_PENALTY = 1e-5

# Features to exclude from the optimization (kept in the aligned stack, dropped from the
# manifest 03 reads). Use to trial feature subsets without re-running 02's heavy warp.
EXCLUDE_FEATURES = ["irrecoverable_carbon_sl_soc"]   # subsoil carbon; keep only m_soc for now

# ---- Sub-regional analyses (03a / 03b / 03c) ----------------------------
# Three prioritizr analyses share ONE preprocessing step (02's aligned stack); they differ
# only in configuration, collected here. Each 03x notebook selects its key; prioritizr_core.R
# reads these via the manifest and hard-codes NO parameter, so tweaking one entry cannot affect
# another. GLOBAL run params (SOLVER_TIME_LIMIT, PROTOTYPE_AGG_FACTOR, NORM_TOTAL, OPT_GAP,
# PORTFOLIO_*, EXCLUDE_FEATURES) stay module-level and apply to all three. The "y2y" entry
# mirrors the module defaults verbatim, so the corridor-wide run is unchanged.
# Per-entry keys:
#   results_subdir : output_data/<this> for the run.
#   roi            : sub-window to crop the stack to. mode="full" (whole stack, no crop),
#                    "bbox_union" (buffered bounding box of the union of `sources`), or
#                    "intersect" (overlay-intersection of `sources`). buffer_km buffers the ROI
#                    (km); mask=True also terra::mask()s to the ROI polygon (else bbox crop only).
#   objective / budget_pct / target_pct / decision_type / solver / highs_solver.
#   {connectivity,boundary,neighbor}_penalty : per-analysis coherence / compactness.
#   lock_in        : {"source":"pa_mask"} = existing y2y PAs (mask_protected_areas.tif); or
#                    {"source":"vector","vector_path":...} = rasterize + lock a polygon
#                    (write_manifest reprojects it to TARGET_CRS first).
#   feature_weight_multipliers : {feature_name: x} scales that feature's min-shortfall weight.
ANALYSES = {
    "y2y": {
        "results_subdir": "iter6_y2y",
        "roi": {"mode": "full", "sources": None, "buffer_km": 0, "mask": False},
        "objective": OBJECTIVE, "budget_pct": BUDGET_PCT, "target_pct": TARGET_PCT,
        "decision_type": DECISION_TYPE, "solver": SOLVER, "highs_solver": HIGHS_SOLVER,
        "connectivity_penalty": CONNECTIVITY_PENALTY, "boundary_penalty": BOUNDARY_PENALTY,
        "neighbor_penalty": NEIGHBOR_PENALTY,
        "lock_in": {"source": "pa_mask", "vector_path": None},
        "feature_weight_multipliers": {},
    },
    "north_bc": {
        # Connect 4 draft IPCAs: crop to their buffered bbox, lock them in as anchors, and
        # up-weight connectivity so the solve fills the best land linking them.
        "results_subdir": "iter6_north_bc",
        # ROI = CONVEX HULL of the 4 IPCAs + 50 km, MASKED to that shape. The hull fills the area
        # BETWEEN the anchors (which a buffered union alone may not) while avoiding a bbox's empty
        # far corners; mask=True means the analysis really is that shape, not its rectangle.
        # -> 178,040 PU, anchors lock 43,257 (24.3%).
        "roi": {"mode": "hull", "sources": [str(DRAFT_PA_VECTOR)],
                "buffer_km": 50, "mask": True},
        # Lock BOTH the existing PAs and the draft IPCAs (the drafts are treated as effectively
        # protected since they are likely to be designated) -> 73,297 cells locked = 41.2% of the
        # window (IPCAs 43,257 + existing PAs 30,375; they overlap by only 335).
        # budget 0.52 = that 41.2% + ~19,300 cells of NEW connective corridor. Raise for more
        # corridor (0.55 -> ~24,600), lower for less (0.45 -> ~6,800). Tune off 03b cell 3.
        "objective": "min_shortfall", "budget_pct": 0.52, "target_pct": 1.0,
        "decision_type": DECISION_TYPE, "solver": SOLVER, "highs_solver": HIGHS_SOLVER,
        "connectivity_penalty": 0.0, "boundary_penalty": 0.0, "neighbor_penalty": 1e-5,
        # anchors total ~45,039 km^2 (one giant IPCA dominates); budget_pct MUST exceed the
        # locked fraction of the WINDOW or the feasibility guard stops the run -- tune off the
        # printed "locked-in / budget" line (start 0.55).
        "lock_in": {"source": "both", "vector_path": str(DRAFT_PA_VECTOR)},   # existing PAs + IPCAs
        "feature_weight_multipliers": {
            "transboundary_connectivity": 5.0, "climate_corridors": 5.0},
    },
    "ab_foothills": {
        # Candidate small areas in the Alberta eastern foothills: crop AND mask to
        # (Alberta boundary ∩ foothills), compactness OFF so small high-value areas surface.
        "results_subdir": "iter6_ab_foothills",
        "roi": {"mode": "intersect", "sources": [str(AB_BOUNDARY), str(FOOTHILLS_VECTOR)],
                "buffer_km": 0, "mask": True},
        # Extending the window to butt against the parks pulled the big MOUNTAIN parks
        # (Banff/Jasper/Willmore/Kananaskis) into it -> they lock in ~30.4% of the window on their
        # own, so budget_pct must exceed that. 0.45 = existing parks (~30%) + ~15% for NEW candidate
        # foothills area (~11,000 cells). Tune off the "locked-in / budget" line in 03c cell 3.
        "objective": "min_shortfall", "budget_pct": 0.45, "target_pct": 1.0,
        "decision_type": DECISION_TYPE, "solver": SOLVER, "highs_solver": HIGHS_SOLVER,
        "connectivity_penalty": 0.0, "boundary_penalty": 0.0, "neighbor_penalty": 0.0,
        "lock_in": {"source": "pa_mask", "vector_path": None},
        "feature_weight_multipliers": {},
    },
}

# ---- Results analysis (04) ----------------------------------------------
# Decompose the selected network into spatial clusters (candidate areas) for per-cluster
# value-profile star plots. Read directly by 04 (imports config); not needed in the manifest.
CLUSTER_MIN_CELLS = 25   # drop connected components smaller than this (25 km^2 at 1 km, 100 at 2 km)
CLUSTER_MAX_PLOTS = 6    # cap the per-cluster small-multiples grid
# How to pick which NEW candidate clusters to profile (all still >= CLUSTER_MIN_CELLS):
#   "largest" = the CLUSTER_MAX_PLOTS biggest by area (biggest opportunities; but they can
#               bunch mid-corridor -- iter5's top 6 all sat at 51-60N, missing the US south
#               and the Yukon north).
#   "spread"  = split the corridor's latitude range into CLUSTER_MAX_PLOTS bands and take the
#               largest cluster in each -> examples from N to S, still the most significant
#               block per region. Empty bands are backfilled with the next-largest overall.
# Mirrors the featured named PAs, which are chosen for N->S spread. Does not affect the PA
# block (that list is manual) or the consequences tables' disjointness.
CLUSTER_SELECT = "spread"

# Named protected areas profiled in 04 as the "existing protection" benchmark, REPLACING the
# old connected-component PA clusters (components merged adjacent parks into unnamed blobs
# nobody could act on). Chosen as large + recognizable + spread N->S across the corridor:
# latitudes 61.6, 57.5, 52.9, 51.5, 48.7, 44.6 span Y2Y's full range (66.5N .. 42.8N).
# Each entry = (EXACT PA_Name in the PA gpkg, short label for plots/tables).
# CAUTION: the Montana park is stored as plain "Glacier" -- "Glacier National Park Of Canada"
# is a DIFFERENT, smaller BC park (1,358 km^2 at 51.3N). Names must match the layer exactly;
# 04 asserts on any that are missing.
PA_FEATURED = [
    ("Nahanni National Park Reserve Of Canada", "Nahanni NPR"),
    ("Spatsizi Plateau Wilderness Park",        "Spatsizi Plateau"),
    ("Jasper National Park Of Canada",          "Jasper NP"),
    ("Banff National Park Of Canada",           "Banff NP"),
    ("Glacier",                                 "Glacier NP (MT)"),
    ("Yellowstone National Park",               "Yellowstone NP"),
]

# ---- Per-analysis results-analysis config (04a / 04b / 04c) --------------
# results_core.py reads RESULTS_04[key] for the 04 knobs that differ per analysis. Contribution
# / efficiency denominators are the FULL Y2Y region totals for every analysis, so "% of Y2Y"
# stays literally correct (a sub-region area reads as its share of the whole corridor). Keys:
#   region_label     : short name for titles / the map outline.
#   cluster_select   : "spread" (N->S bands; corridor-wide) or "largest" (narrow sub-windows).
#   benchmark        : the "existing protection" star-plot block. type ∈
#       "named_pa"      -> dissolve PA_VECTOR by PA_Name, profile the `featured` (name,label) list.
#       "named_vector"  -> profile each feature of `vector` (label from `labels` or `name_field`).
#       "in_window_pa"  -> dissolve PA_VECTOR by PA_Name, profile the `top_n` largest that fall
#                          inside the analysis window.
#   benchmark_title  : heading for that block.
#   manual_area      : an extra hand-drawn area profiled like a cluster (Ross River for y2y), or None.
#   outline_label    : legend label for the solid black boundary drawn on every map (= the ROI
#                      outline, roi_<analysis>.gpkg, or the full Y2Y boundary for y2y).
#   context_outline / context_label : an EXTRA boundary drawn on every map for geographic context
#                      (dashed grey, labelled), framed to the window so it never zooms out. None = off.
RESULTS_04 = {
    "y2y": {
        "region_label": "Y2Y",
        "cluster_select": "spread",
        "benchmark": {"type": "named_pa", "featured": PA_FEATURED},
        "benchmark_title": "Featured protected areas",
        "manual_area": {"name": "Ross River IPCA", "color": "crimson",
                        "shp": INPUT_DIR / "y2y_ross_river" / "RRA_nonoverlap_3_revised.shp"},
        "outline_label": "Y2Y boundary",
        "context_outline": None, "context_label": None,
    },
    "north_bc": {
        "region_label": "Northern BC",
        "cluster_select": "largest",   # narrow window; connective corridors, not N->S spread
        # Benchmark = the 4 draft IPCAs (the locked anchors) -> gap analysis vs the NEW
        # connective clusters the solve adds between them.
        "benchmark": {"type": "named_vector", "vector": DRAFT_PA_VECTOR, "name_field": "PA_NAME",
                      "labels": {"Dene Kʼéh Kusān": "Dene Kʼéh Kusān",
                                 "Tahltan - Sacred Headwaters (Klappan)": "Klappan",
                                 "Wilps Gwininitxw": "Wilps Gwininitxw",
                                 "Wədzih Yiné’ (Caribou Song)": "Caribou Song"}},
        "benchmark_title": "Proposed IPCA anchors",
        "manual_area": None,
        # maps draw existing PAs (grey) and the locked draft IPCAs (teal) as separate layers;
        # this labels the teal one.
        "anchor_label": "draft IPCAs (committed)",
        "outline_label": "analysis window (IPCA hull + 50 km)",
        "context_outline": None, "context_label": None,
    },
    "ab_foothills": {
        "region_label": "Alberta foothills",
        "cluster_select": "largest",
        # CURATED PROVINCIAL PAs spread N->S across the whole study area (foothills/montane/
        # subalpine, 49.4-54.0N) -- no national parks; mid-sized provincial parks / wildlands /
        # wilderness areas are a more apt comparison for the candidate areas than the giant
        # mountain NPs. South -> north; names must match PA_Name exactly. Edit to taste.
        "benchmark": {"type": "named_pa", "featured": [
            ("Castle Provincial Park", "Castle PP"),           # 49.4N, provincial park (far south)
            ("Peter Lougheed",         "Peter Lougheed PP"),   # 50.7N, provincial park (Kananaskis)
            ("Siffleur",               "Siffleur Wilderness"), # 51.9N, wilderness area (central)
            ("Whitehorse Wildland",    "Whitehorse Wildland"), # 53.0N, wildland (north-central)
            ("Willmore",               "Willmore"),            # 53.6N, wilderness park (north)
            ("Kakwa Wildland",         "Kakwa Wildland")]},     # 54.0N, wildland (far north)
        "benchmark_title": "AB provincial PAs (N–S spread)",
        "manual_area": None,
        "outline_label": "foothills extent",           # the solid black ROI outline
        "context_outline": str(AB_BOUNDARY), "context_label": "Alberta",   # dashed grey context
        "frame": "context",   # zoom maps out to show the WHOLE province (foothills sits inside it);
                              # "window" (default) frames tight on the analysis window instead.
    },
}

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
        # Single mosaicked GeoTIFF downloaded from GEE by 00 (asset v202606); no VRT needed.
        # The old 4-tile export still sits in this folder but is unused (exact-name match below).
        "representative": "HM_Y2Y_2024_90_60land_v202606.tif",
        "multi": False,
        "resampling": "average",  # gHM ~90 m -> 1 km
        "orient": "complement",   # gHM (0-1 modification) -> intactness 1 - gHM
        "build_vrt": False,
        "citation": "Theobald et al., gHM human modification (Y2Y asset v202606)",
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


# ---- ROI + hand-off helpers ----------------------------------------------
def _rel(p):
    """Path relative to the project root, POSIX-style (for the R-readable manifest)."""
    return Path(p).resolve().relative_to(PROJECT_DIR).as_posix()


def build_roi(analysis, handoff_dir=HANDOFF_DIR):
    """Build a sub-analysis ROI and return (bounds_snapped | None, mask_path | None).

    Reprojects the analysis' `roi.sources` to TARGET_CRS, forms the buffered bbox-union
    (mode="bbox_union") or the overlay-intersection (mode="intersect"), snaps the bounding box
    to the aligned-stack grid AND clips it to the grid so the R crop is always aligned and fully
    contained, and writes roi_<analysis>.gpkg (TARGET_CRS) to `handoff_dir` for provenance / as
    the mask cutline. mode="full" -> (None, None) (no crop). Raises FileNotFoundError if a
    source vector is missing (e.g. the not-yet-supplied ab_foothills inputs) so the run stops
    rather than solving a stale/undefined window."""
    import math
    import geopandas as gpd
    import pandas as pd
    import rasterio

    roi = ANALYSES[analysis]["roi"]
    if roi["mode"] == "full":
        return None, None

    handoff_dir = Path(handoff_dir)
    srcs = [Path(s) for s in roi["sources"]]
    missing = [str(s) for s in srcs if not s.exists()]
    if missing:
        raise FileNotFoundError(
            f"ROI source(s) for analysis '{analysis}' not found: {missing}. "
            "Supply the vector(s) before running this analysis (see Phase 4 / config comments).")
    gdfs = [gpd.read_file(s).to_crs(TARGET_CRS) for s in srcs]

    if roi["mode"] == "bbox_union":
        poly = pd.concat(gdfs, ignore_index=True).union_all()
    elif roi["mode"] == "hull":
        # CONVEX HULL of the sources, then buffered: a shape that encompasses the anchors AND
        # the area between them, without a bounding box's far-flung empty corners. Use with
        # mask=True so the analysis really is that shape (not its bbox).
        poly = pd.concat(gdfs, ignore_index=True).union_all().convex_hull
    elif roi["mode"] == "intersect":
        inter = gdfs[0]
        for g in gdfs[1:]:
            inter = gpd.overlay(inter, g, how="intersection")
        poly = inter.union_all()
    else:
        raise ValueError(f"unknown roi mode {roi['mode']!r}")
    if roi["buffer_km"]:
        poly = poly.buffer(roi["buffer_km"] * 1000)

    # Snap the ROI bbox to the aligned-stack grid, then clip to the grid extent.
    with rasterio.open(handoff_dir / "human_modification.tif") as src:
        gb = src.bounds
        ox, oy = src.transform.c, src.transform.f   # grid origin (left, top)
    res = TARGET_RES_M
    minx, miny, maxx, maxy = poly.bounds
    left   = max(ox + math.floor((minx - ox) / res) * res, gb.left)
    right  = min(ox + math.ceil((maxx - ox) / res) * res, gb.right)
    bottom = max(oy - math.ceil((oy - miny) / res) * res, gb.bottom)
    top    = min(oy - math.floor((oy - maxy) / res) * res, gb.top)
    bounds_snapped = [left, bottom, right, top]

    roi_path = handoff_dir / f"roi_{analysis}.gpkg"
    gpd.GeoDataFrame(geometry=[poly], crs=TARGET_CRS).to_file(roi_path, driver="GPKG")
    return bounds_snapped, (_rel(roi_path) if roi["mask"] else None)


# ---- Python -> R hand-off contract ---------------------------------------
def write_manifest(analysis="y2y", handoff_dir=HANDOFF_DIR, manifest_path=MANIFEST_PATH):
    """Describe the aligned hand-off stack + one analysis' run params as JSON so 03x (R) reads
    an explicit contract instead of globbing/guessing. Metadata-only -- safe to run anytime
    without re-warping. The grid + layers are analysis-agnostic; the `params` block is assembled
    from ANALYSES[analysis] (plus the module-level GLOBAL params) and the computed ROI. Output
    filename convention (set by 02): <dataset_key>.tif for single-raster features, EFGs in
    iucn_efg/, plus cost_uniform.tif and mask_protected_areas.tif."""
    import json
    import math
    import rasterio  # local import keeps config light for 01

    rel = _rel
    a = ANALYSES[analysis]

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

    # ROI (crops the stack in 03x) + lock-in. A "vector" lock-in is reprojected to TARGET_CRS
    # here and written as lockin_<analysis>.gpkg, so R rasterizes an already-aligned polygon.
    roi_bounds, roi_mask = build_roi(analysis, handoff_dir)
    lock_in = dict(a["lock_in"])
    if lock_in["source"] in ("vector", "both"):   # "both" also needs the reprojected rel path
        import geopandas as gpd
        vp = Path(lock_in["vector_path"])
        if not vp.exists():
            raise FileNotFoundError(f"lock-in vector for analysis '{analysis}' not found: {vp}")
        out = Path(handoff_dir) / f"lockin_{analysis}.gpkg"
        gpd.read_file(vp).to_crs(TARGET_CRS).to_file(out, driver="GPKG")
        lock_in["vector_path"] = rel(out)

    # Per-analysis params come from ANALYSES[analysis]; GLOBAL params stay module-level.
    manifest = {
        "grid": grid,
        "params": {
            "analysis": analysis,
            "solver": a["solver"],
            "solver_time_limit": SOLVER_TIME_LIMIT,
            "highs_solver": a["highs_solver"],
            "objective": a["objective"],
            "decision_type": a["decision_type"],
            "prototype_agg_factor": PROTOTYPE_AGG_FACTOR,
            "norm_total": NORM_TOTAL,
            "budget_pct": a["budget_pct"],
            "target_pct": a["target_pct"],
            "opt_gap": OPT_GAP,
            "portfolio_n": PORTFOLIO_N,
            "portfolio_gap": PORTFOLIO_GAP,
            "connectivity_penalty": a["connectivity_penalty"],
            "boundary_penalty": a["boundary_penalty"],
            "neighbor_penalty": a["neighbor_penalty"],
            "feature_weight_multipliers": a["feature_weight_multipliers"],
            "lock_in": lock_in,
            "roi": {"mode": a["roi"]["mode"], "bounds": roi_bounds, "mask_path": roi_mask},
            "results_dir": rel(RESULTS_DIR),
            "results_subdir": a["results_subdir"],
        },
        "layers": layers,
    }

    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, allow_nan=False)  # strict JSON for R/jsonlite
    return manifest_path
