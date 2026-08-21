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
#   PROPOSED_PA_VECTOR : 32 proposed PAs across the corridor (EPSG:3857). The northern_ipcas
#                      analysis uses the NORTHERN subset only, selected by `source_filter`
#                      (min_lat=55) -> the 13 in northern BC + Yukon (56-67N). There is a clean
#                      gap in the data at 54.05-56.26N, so 55 separates them unambiguously.
#   AB_BOUNDARY      : Alberta provincial boundary (Natural Earth 1:10m admin-1).
#   FOOTHILLS_VECTOR : the AB mountain-front study polygon for ab_foothills. Derived from the
#                      Alberta Natural Regions & Subregions (2005) service (geospatial.alberta.ca),
#                      union of SIX subregions: Upper + Lower Foothills (Foothills NR), Foothills
#                      Fescue (Grassland NR), Foothills Parkland (Parkland NR), Montane + Subalpine
#                      (Rocky Mountain NR). ~118,092 km2, running the full length of AB to the US
#                      border and butting against every AB mountain park (incl. the high Kananaskis
#                      parks — Subalpine closes that gap). The strict "Foothills NR" alone (central
#                      AB only, 51-56N) stops well north of the border, hence the broader union.
PROPOSED_PA_VECTOR = INPUT_DIR / "y2y_proposed_pa" / "proposed_pa_v2.shp"
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
TARGET_PCT = 1.0             # DEFAULT per-feature target (min_shortfall/min_set) for any feature
                             # not named in TARGETS. 1.0 = never satisfiable, so the feature keeps
                             # competing for area for its entire capture.
# Per-feature target OVERRIDES, by feature name. This is the lever that demotes a feature without
# touching its weight, and it is a POLICY statement rather than a tuning knob ("we aim to secure
# 33% of mineral-soil carbon"), which is why it is preferred here over re-weighting.
#
# WHY IT WORKS AS A STOPPING RULE. Under min_shortfall, shortfall_f = max(0, t_f - held_f)/t_f, so
# once held_f reaches t_f the feature contributes ZERO and the optimizer has no further incentive
# to spend area on it. The objective is linear, so it was already taking that feature's DENSEST
# cells first -- the target simply says how far down the distribution to keep going. Result: grab
# the hotspots, pass over the mediocre pixels, reallocate the rest.
#
# WHY CARBON. With every target at 1.0 the two carbon pools took 39.7% of the objective's
# achievable swing and were captured at 45.5% / 41.8% (1.52x / 1.39x their area share) while every
# other value landed at 0.96-1.06x -- i.e. the map was "the best 30% for carbon, everything else
# proportional". Y2Y's position is that carbon is an added benefit, not a driver.
#
# HOW THESE NUMBERS WERE DERIVED (not chosen): the rule "keep taking cells while marginal density
# >= 5x the regional mean" applied to each pool, via leverage_core.target_cost_curve. Mineral soil
# has a genuinely exceptional tail (33.2% of its total sits above 304 t/ha, in 4.1% of the region);
# biomass has almost none (only 6.6% above 106 t/ha), so it demotes itself on its own geometry.
#
# DO NOT lower every target. If all targets became simultaneously achievable the shortfall would be
# zero everywhere, the objective flat, and the solver would return an arbitrary member of a huge
# optimal set. Keeping the foundational features at 1.0 is what keeps this a real trade-off.
# UPDATED 2026-08-18 by the Gate-0a characterization protocol (leverage_core.classify, constants
# in AUDIT): biomass's entry is REMOVED -- it crosses theta but fails the R2 tail-mass criterion
# (implied target 0.066 < t_min 0.15: the rule would saturate instantly, leaving the feature
# governed by weight anyway), so it reverts to diffuse-linear (t = 1.0, weight-levered). This is
# the protocol overruling the initial hand treatment, adopted per spec s2.5. Gate-0 arms override
# this dict from 03a's RUN LEVER; this baseline matters for run_one.R / the 06 ensemble.
# NOTE the companion decision: the solve pairs every target with an equal weight (w = t, set in
# the lever as feature_weight_multipliers), keeping effective pull w/t at 1.0 so the target acts
# ONLY as a stopping rule -- at w = 1 this 0.332 target would raise m_soc's pull to 3.0x.
TARGETS = {
    "irrecoverable_carbon_m_soc": 0.332,     # >= 5x regional mean (60.7 t/ha) -> cutoff 304 t/ha
}
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
# that -- meaningful but not dominating. 1e-5 was a first guess.
#
# TURNED OFF 2026-08-17. Compactness moved OUT of the optimizer to post-hoc delineation from the
# ensemble's selection-frequency surface (results_core), for three measured reasons:
#   1. UNCALIBRATED AND DECISIVE. At 1e-5 -- a first guess, never calibrated -- Morris ranked it
#      the 3rd largest driver of the map out of 12 factors, and it relocates a THIRD of the
#      selection (Jaccard 0.662 between iter2_lp_1km and iter6_y2y).
#   2. IT WASN'T CREATING THE STRUCTURE. The unpenalized solution is already 66.6% clustered by
#      area (new area in components >= 100 km2), with singletons only 3% of new area. The penalty
#      consolidates structure the value surface already has -- it does not supply it.
#   3. IT COST 400x THE SOLVE TIME. 1 km: 12 s without it, 4,826 s with it. Every timeout, the
#      6 h cap, the machine contention and the 2 km screening compromise in 06 trace to this one
#      term. Removing it makes the ensemble affordable at full 1 km.
# Delineating afterwards also makes compactness re-tunable with ZERO re-solves, and matches 05's
# D9 decision to ship a graded priority surface rather than hard lines.
# The parameter stays so runs before this date remain reproducible.
NEIGHBOR_PENALTY = 0.0

# Leverage floor for the 02 QA (leverage_core). A feature whose captured fraction can only span
# `leverage` across ALL feasible selections cannot be moved by its weight; below this value,
# reweighting it is inert by construction. 0.10 sits just under macrorefugia's pre-fix 0.090 and
# gHM's 0.042 (both flagged) and clear of AOH mammals at 0.181 (the lowest passing feature).
LEVERAGE_MIN = 0.10

# ---- Feature characterization protocol (frequency-ensemble spec s2.5, Gate 0a) ------------
# FROZEN per rule R4 of the spec (v0.3, 2026-08-18) BEFORE the audit runs; no per-feature tuning.
# Every input passes the same univariate audit; leverage_core.classify() applies rules R1-R4 and
# the current formulation is RE-DERIVED from the protocol rather than asserted. Disclosures the
# spec requires carrying in Methods:
#   theta  was originally set on carbon and is generalized here (E10 theta-sensitivity at 3x/10x
#          is the empirical backstop);
#   t_min  chosen knowing the data BUT classification is insensitive across 0.07-0.33
#          (mineral soil 0.332 vs biomass 0.066 -- a five-fold margin);
#   lambda sits in the wide gap between AOH mammals (0.181) and gHM intactness (0.042) --
#          identical classification for any floor in 0.05-0.15; mammals flagged marginally live.
AUDIT = {
    "theta": 5.0,          # marginal-density ratio a stopping rule must clear (x regional mean)
    "a_min": 0.005,        # ...sustained over at least this AREA fraction of the region
    "t_min": 0.15,         # tail-mass criterion: the implied target must secure at least this
                           # captured fraction, else the rule saturates instantly and the feature
                           # is really weight-governed -> diffuse-linear (this is what reverts
                           # biomass: implied target 0.066)
    "leverage_min": LEVERAGE_MIN,   # R3 expressivity floor (lambda)
    "rare_cap": 0.999,     # cap_max at/above this = capturable in full within the budget
                           # -> rare-attainable (saturates for free; no scenario lever)
    "curve_points": 10_001,  # resolution of the ARCHIVED Lorenz / marginal-density curves --
                             # budget-independent objects (spec D2) so re-deriving targets at any
                             # theta or budget is interpolation on the archive, not a recompute
}

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
#   targets        : {feature_name: t} per-feature relative-target OVERRIDES; anything unlisted
#                    uses this analysis's target_pct. Set PER ANALYSIS deliberately -- the carbon
#                    demotion is a corridor-wide policy decision and is NOT inherited by the
#                    sub-regional analyses, which keep every target at 1.0 until reviewed.
ANALYSES = {
    "y2y": {
        "results_subdir": "iter6_y2y",
        "roi": {"mode": "full", "sources": None, "buffer_km": 0, "mask": False},
        "objective": OBJECTIVE, "budget_pct": BUDGET_PCT, "target_pct": TARGET_PCT,
        "targets": TARGETS,
        "decision_type": DECISION_TYPE, "solver": SOLVER, "highs_solver": HIGHS_SOLVER,
        "connectivity_penalty": CONNECTIVITY_PENALTY, "boundary_penalty": BOUNDARY_PENALTY,
        "neighbor_penalty": NEIGHBOR_PENALTY,
        "lock_in": {"source": "pa_mask", "vector_path": None},
        "feature_weight_multipliers": {},
    },
    "northern_ipcas": {
        # Connect the NORTHERN proposed IPCAs (northern BC + Yukon): crop to their convex hull,
        # lock them in as anchors alongside existing PAs, and up-weight connectivity so the solve
        # fills the best land linking them. SUPERSEDES the old 4-IPCA "north_bc" analysis.
        "results_subdir": "iter6_northern_ipcas",
        # 13 of the 32 proposed PAs, picked by source_filter below (56-67N, BC + Yukon; 176,998
        # km2 of anchors). ROI = their CONVEX HULL + 25 km, MASKED to that shape: the hull fills
        # the area BETWEEN anchors while avoiding a bbox's empty far corners.
        # -> 481,488 PU, locked 195,953 (40.7%).
        "roi": {"mode": "hull", "sources": [str(PROPOSED_PA_VECTOR)],
                "buffer_km": 25, "mask": True},
        # Northern subset only -- "everything north of the polygons we were previously using,
        # nothing further south". A clean data gap at 54.05-56.26N makes 55 unambiguous.
        "source_filter": {"min_lat": 55.0},
        # Lock BOTH existing PAs and the proposed IPCAs (drafts treated as effectively protected
        # since they are likely to be designated) -> 196,195 cells = 40.7% of the window.
        # budget 0.43 = that 40.7% + ~11,200 cells of NEW connective corridor. TRIMMED from 0.46
        # (~25,700) so the solve spends its area only on the best connective land -- a leaner
        # budget reads as corridors rather than swaths. Tune off 03b cell 3.
        "objective": "min_shortfall", "budget_pct": 0.43, "target_pct": 1.0,
        "targets": {},          # unchanged: the carbon demotion is a y2y-wide decision only
        "decision_type": DECISION_TYPE, "solver": SOLVER, "highs_solver": HIGHS_SOLVER,
        # CORRIDOR FORMULATION: the connectivity penalty is the actual corridor mechanism -- it
        # rewards selected units connected to EACH OTHER and to the locked anchors. The neighbor
        # penalty is OFF because it does the opposite: it penalises units with FEW selected
        # neighbours, so a thin corridor is penalised while a compact blob is rewarded.
        # (Deferred corridor-wide because the raw matrix spans ~40,000x; in THIS window it is
        # 20x raw / 2.7x capped, so it is calibratable. pr_penalty_matrices caps + normalises it
        # to mean weight ~1, putting this on the same scale as the neighbor penalty.)
        # Penalties reverted to the standard prototype (matching y2y): light neighbor compactness,
        # connectivity penalty OFF. The connectivity-penalty experiment (1e-5 -> 1e-4 -> 3e-4) was
        # CONCLUSIVELY the wrong tool for connecting the anchors -- tripling it to 122% of the
        # objective still left the 13 anchors in 12 components. It aggregates permeable LAND, it
        # does not route A->B corridors; the "connect the PAs" goal moved to a SEPARATE least-cost
        # corridor analysis. connectivity_cap_pctile is inert while connectivity_penalty = 0.
        "connectivity_penalty": 0.0, "connectivity_cap_pctile": 0.99,
        "boundary_penalty": 0.0, "neighbor_penalty": 1e-5,
        "lock_in": {"source": "both", "vector_path": str(PROPOSED_PA_VECTOR)},  # existing PAs + IPCAs
        # x2 (was x5): weights say WHAT to capture, the penalty says WHAT SHAPE. At x5 the solver
        # grabbed the highest-connectivity CELLS anywhere (hotspot clumps) instead of chains.
        "feature_weight_multipliers": {
            "transboundary_connectivity": 2.0, "climate_corridors": 2.0},
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
        "targets": {},          # unchanged: the carbon demotion is a y2y-wide decision only
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
    "northern_ipcas": {
        "region_label": "Northern BC + Yukon",
        "cluster_select": "spread",   # wide 56-67N window -> N->S spread reads better than "largest"
        # Benchmark = the proposed IPCA anchors themselves -> gap analysis vs the NEW connective
        # clusters the solve adds between them. 13 anchors is too many to star-plot, so `top_n`
        # keeps the largest few; the MAP still shows all 13 in the teal anchor layer. Labels come
        # straight from PA_NAME (already meaningful); add a `labels` dict to shorten any.
        "benchmark": {"type": "named_vector", "vector": PROPOSED_PA_VECTOR, "name_field": "PA_NAME",
                      "source_filter": {"min_lat": 55.0}, "top_n": 6},
        "benchmark_title": "Proposed IPCA anchors",
        "manual_area": None,
        # maps draw existing PAs (grey) and the locked proposed IPCAs (teal) as separate layers;
        # this labels the teal one.
        "anchor_label": "proposed IPCAs (committed)",
        "outline_label": "analysis window (IPCA hull + 25 km)",
        # show the Y2Y corridor boundary for geographic context, and zoom out 25% so there is
        # breathing room around the window. Framing to the FULL corridor ("context") would shrink
        # this northern window to a sliver, so the Y2Y outline is simply clipped by the view.
        "context_outline": str(CORRIDOR_REF), "context_label": "Y2Y corridor",
        "frame": "pad", "frame_pad": 0.25,
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

# ---- Ensemble runner + sensitivity design (06) --------------------------
# The runner (ensemble_core.py) solves the SAME prioritizr problem many times under different
# parameter sets, by PATCHING a copy of manifest.json per run -- config.py is never mutated per
# run. That keeps this file the single source of truth for the BASELINE while every perturbation
# stays an explicit delta in the design matrix, and it lets concurrent solves run without
# fighting over shared state. Each run's exact manifest sits beside its outputs, so any single
# run is reproducible in isolation.
ENSEMBLE = {
    "rscript": "/opt/homebrew/bin/Rscript",
    "driver": "run_one.R",
    # 10 cores here: 3 concurrent solves x 3 threads leaves one free for the OS. HiGHS IPM scales
    # sublinearly, so several narrow solves finish a batch sooner than one wide one.
    "workers": 3,
    "threads": 3,
    # Sensitivity runs are at 2 km (agg 2): ~1/4 the LP of the 1 km headline. The headline stays
    # 1 km -- G2 (scale transfer) checks that 2 km conclusions carry over before the batch runs.
    "agg_factor": 2,
    "analysis": "y2y",            # baseline analysis the ensemble perturbs
    # Per-run wall-clock cap -- a stuck-run guard so one pathological parameter set cannot eat the
    # batch. RAISED 7200 -> 21600 (2026-08-07): at 7200 the FIRST 130-run batch lost 19 runs, all at
    # budget_pct 26.67% (median solve there 7,313 s vs 206-916 s at every other level -- LP
    # degeneracy, many near-identical optima), and they fell in only 2 of the 10 trajectories, which
    # is exactly the correlated damage a Morris design cannot absorb. This is a CAP, not an
    # expectation: the median solve elsewhere is 843 s.
    # A timed-out run stops wherever it had got to -- it can land EITHER side of the budget, so the
    # collector flags `timed_out` on the clock as well as `over_budget` on the area.
    "time_limit": 21600,
    # Selected = allocation above this (the LP is ~99.98% integral, so 0.5 is a clean cut).
    "select_threshold": 0.5,
    # selection_frequency.tif == portfolio.tif when there is one solution (pr_summaries computes
    # it as sum(s)), so the collector drops the duplicate.
    "drop_duplicate_freq": True,
}

# Morris screening (Phase 3): rank ALL factors by how much each moves the priority map.
# `r` trajectories x (k+1) = the run count; r=10, k=12 -> 130 solves.
# Sampling spaces are chosen so the factor is uniform in the space that matters: weight
# multipliers in log2 (x0.25-x4 is symmetric around 1) and the neighbor penalty in log10.
# NOTE min_shortfall is scale-invariant in the weights, so scaling all nine together is a NULL
# direction -- harmless for Morris (it simply shows zero effect), but state it in methods.
# The climate scenario is deliberately NOT a factor: it would need shared-anchor orientation plus
# a headline re-solve (deferred with Phase 1b, 2026-07-30).
MORRIS = {
    "r": 10,                 # trajectories
    "num_levels": 4,         # standard Morris grid
    "seed": 20260730,
    "weight_log2_range": (-2.0, 2.0),          # x0.25 .. x4
    "factors": [
        # (name, kind, low, high) -- kind drives how the value is turned into a manifest patch
        ("w_human_modification",         "weight_log2", -2.0, 2.0),
        ("w_transboundary_connectivity", "weight_log2", -2.0, 2.0),
        ("w_climate_corridors",          "weight_log2", -2.0, 2.0),
        ("w_climate_type_macrorefugia",  "weight_log2", -2.0, 2.0),
        ("w_irrecoverable_carbon_biomass", "weight_log2", -2.0, 2.0),
        ("w_irrecoverable_carbon_m_soc", "weight_log2", -2.0, 2.0),
        ("w_aoh_richness_mammals",       "weight_log2", -2.0, 2.0),
        ("w_aoh_richness_birds",         "weight_log2", -2.0, 2.0),
        ("w_EFG_group",                  "efg_log2",    -2.0, 2.0),   # applied to all 40 EFGs
        ("budget_pct",                   "linear",       0.20, 0.40),
        # NOTE (2026-08-17): with per-feature TARGETS in play this factor now perturbs the target
        # of every feature EXCEPT the ones named in TARGETS -- carbon is pinned by its override and
        # does not move with it. Read it as "default target for the foundational features". That is
        # the right split: carbon's target is a POLICY choice, not an uncertainty, and it is tested
        # explicitly and legibly by the R0-R3 comparison runs instead of being blurred into a
        # screening factor.
        ("target_pct",                   "linear",       0.50, 1.00),
        # ("neighbor_penalty",           "log10",       -6.0, -4.0),
        # REMOVED 2026-08-17, and it must NOT come back while NEIGHBOR_PENALTY = 0. The design
        # SETS each factor per run, so leaving it here would have switched the compactness penalty
        # back on in all 130 runs -- screening a model we deliberately stopped using, and taking
        # each 1 km solve from ~12 s to ~4,826 s (the whole batch from ~30 min to weeks). It ranked
        # 3rd of 12 in the previous screening precisely because it moves the map so much; that is
        # why it was removed from the optimizer, not a reason to keep perturbing it.
    ],
}

# ---- Least-cost corridors (05) ------------------------------------------
# Standalone corridor analysis (corridors_core.py) that ROUTES between anchor areas -- the tool the
# prioritizr connectivity penalty could not be (that aggregates permeable land; it cannot answer
# "how does an animal get from park A to park B"). Not a prioritizr run; pure Python (skimage).
#
# ============================ v2 REBUILD (2026-08-07) ============================
# Decisions D1-D10 live in docs/05_methods_v2.md. What changed from v1, and why:
#
#   D1/D2  RESISTANCE IS A PUBLISHED MOVEMENT-COST SURFACE, not a weighted blend. v1 blended
#          Pither current density (0.5) + Carroll climate corridors (0.3) + AdaptWest macrorefugia
#          (0.2), raised it to conn_exponent, floored it, and multiplied by 10**gHM. That
#          triple-counted human footprint (all three of gHM, current density and centrality encode
#          it), used a circuit-theory OUTPUT as a routing INPUT, and mixed process-mismatched
#          climate-ANALOG layers into movement cost. Every blend knob is gone: scale, drivers,
#          conn_exponent, barrier, perm_floor, and the percentile-anchor scenarios.
#   D6     CORRIDOR BAND IS AN ABSOLUTE cost-weighted-distance cutoff (Linkage Mapper convention),
#          not a fraction of edge cost. The relative band made corridor width scale with edge cost
#          -- an unintended claim -- and blocked two-track equivalence with the operational LM run.
#   D7     NETWORK = MST + BRIDGE-BACKUP AUGMENTATION. A bare MST has n-1 edges, no cycles, so
#          every edge is a single point of failure. (The originally drafted criterion -- keep any
#          direct edge with cost <= alpha * MST-path cost -- is VACUOUS: least-cost distance obeys
#          the triangle inequality, so direct cost is never above tree-path cost and the test
#          admits the complete graph. `alpha` is retired; see "beta" below.)
#   D8     STRUCTURED ENSEMBLE over interpretable axes, replacing uniform multiplicative noise on
#          the final resistance surface, which represented no identifiable uncertainty.
#   +      ROUTING RUNS AT THE COST SURFACE'S NATIVE 300 m. At 1 km a 2-lane highway averaged from
#          90 m gHM effectively vanishes, which is exactly the signal this analysis is about.
#          The CO-BENEFIT AUDIT STAYS AT 1 km -- see "grid" below.
CORRIDORS = {
    "north": {
        "results_subdir": "corridors_north",
        "region_label": "Northern BC + Yukon",

        # ---- routing grid: 300 m, northern window --------------------------------------
        # ONLY routing is 300 m. The audit (star plots, "% of Y2Y") stays on the 1 km grid because
        # every value layer is natively 1 km -- upsampling adds no information, costs ~10 GB of
        # stacks, and would SILENTLY INFLATE contribution ~11x: results_core.mask_profile sums a
        # feature over the mask but results_core._region_total computes the denominator at native
        # 1 km, and there is no finer-than-source path (only a coarsening `agg`).
        # The warp covers the whole lat>=min_lat window; corridors_core.load() then crops to the
        # node bbox + routing_buffer_km, since memory scales with array size even where cells are
        # invalid (full window = 4,287 x 5,767 = 24.7 M cells, 11.1x the 1 km run).
        "grid": {
            "res_m": 300,
            "region_filter": {"min_lat": 54.0},   # routing room around the anchors
            "routing_buffer_km": 100,             # kept around the node bbox when cropping
            "dir": INPUT_DIR / "corridors_300m",
        },

        # ---- resistance = the published cost surface (D1/D2) ---------------------------
        # O'Brien et al. transboundary extension of Pither et al. 2023 -- seamless US+Canada, so it
        # covers the whole Y2Y rather than stopping at the border. Shipped in the same download as
        # Raw_CurrentDensity_Map.tif and never registered until the v2 rebuild.
        # Values are FOUR log-spaced ordinal classes {1, 10, 100, 1000}; over the Y2Y bbox they run
        # 58.8 / 7.3 / 5.2 / 28.7 %. Resampling is "near" and that is not a compromise: at
        # 300 m -> 300 m it reprojects EPSG:3347 -> ESRI:102008 while preserving the classes
        # exactly, so no averaging/mode/geometric-mean rule has to be defended.
        # NOTE this layer is deliberately NOT in DATASETS / aligned_stack / manifest.json: it is not
        # a prioritizr feature, it is unoriented (higher = WORSE, unlike every hand-off layer), and
        # adding it would corrupt the PU mask that 02/03/04/06 depend on. (config's `is_feature`
        # flag is documented but read by no code, so it cannot be relied on to hold it out.)
        "resistance": {
            "source": INPUT_DIR / "transboundary_connectivity" / "Movement_Cost_Layer.tif",
            "out_name": "movement_cost.tif",
            "resampling": "near",
            "expect_classes": [1, 10, 100, 1000],
            "citation": ("O'Brien et al., transboundary movement cost surface "
                         "(extension of Pither et al. 2023)"),
        },

        # ---- nodes to connect ----------------------------------------------------------
        # The northern proposed IPCAs + existing PAs above a size in the region.
        # dedupe_overlap_frac: merge two nodes when their rasterized masks share at least this
        # fraction of the SMALLER node -- the same place entered twice under nesting designations
        # (Teetł'it Gwinjik inside the Peel Watershed SMA/WA; Fishing Branch Wilderness Preserve
        # inside its Habitat Protection Area). Slivers stay separate, so an IPCA that merely wraps
        # around a park still routes to it. Set to None/1.1 to disable.
        # node_min_km2 REPLACES v1's node_min_cells=25: a cell count is resolution-dependent, and
        # at 300 m the same 25 cells would mean 2.25 km², silently changing the node set.
        "nodes": {"proposed": str(PROPOSED_PA_VECTOR), "source_filter": {"min_lat": 55.0},
                  "include_existing_pas": True, "existing_pa_min_km2": 200, "node_min_km2": 25,
                  "dedupe_overlap_frac": 0.5},

        # ---- corridor band: ABSOLUTE cwd cutoff (D6) ------------------------------------
        # Per edge, keep cells whose (CWD_i + CWD_j) is within `cwd_cutoff_abs` COST UNITS of that
        # edge's least-cost minimum -- no dependence on edge cost. Calibrated (not guessed) so the
        # MST-only corridor area on the new resistance reproduces v1's 18,188 km²: same edge set,
        # same `& ~node_union` area definition, so v1<->v2 route comparisons are not confounded by
        # band size. Augmentation adds area on top and is reported separately -- calibrating against
        # the augmented network would let the cutoff absorb the augmentation and conflate D6 with D7.
        # None until corridors_core.calibrate_cutoff has been run (resolve() refuses to solve).
        "cwd_cutoff_abs": None,
        "calibration": {"target_km2": 18188, "edges": "mst"},   # pre-registered before running

        # ---- network augmentation (D7) --------------------------------------------------
        # Bridge backup, processed SEQUENTIALLY in descending criticality with recomputation: one
        # added edge typically kills several bridges at once (any cycle it closes covers every tree
        # edge on that cycle), so independent per-bridge processing would overcount additions and
        # misstate which failure each edge insures. This is the standard greedy heuristic for
        # minimum-cost 2-edge-connectivity augmentation; trivial at n=42 with D already computed.
        #
        # beta = cost-ratio CEILING: add the cheapest restoring edge only when
        #   backup_cost <= beta * failed_edge_cost.
        # Adding a backup unconditionally would route "alternatives" through land so resistant that
        # nobody would treat them as real -- that does not create redundancy, it HIDES
        # irreplaceability. Where nothing clears the ceiling the link is flagged IRREPLACEABLE, and
        # those flags are the headline Phase-3 output: the augmented graph says where alternatives
        # exist, the flags say where Y2Y cannot afford to lose the land at any reasonable price.
        "beta": 2.5,

        # ---- linkage priority surface (D9) ----------------------------------------------
        # priority = max_e (ecfb_raw_e * (1 - slack_e / cutoff)); max, not sum, so overlap regions
        # are not inflated purely by edge redundancy and every cell keeps a single owning edge.
        # Tier breaks are percentiles of the non-zero priority surface, PRE-REGISTERED here before
        # the run (same doctrine as CLIMATE_SCENARIOS["rule"]).
        "priority_tiers": {"robust_core": 90, "frequent": 70, "occasional": 0},

        # ---- structured ensemble (D8) ---------------------------------------------------
        # Axes B/C/D all reuse the SAME resistance, and CWD depends only on resistance + node seeds
        # -- axis C drops a node, which removes a row/column from D but leaves every remaining
        # node's CWD field untouched. So the whole ensemble is ONE CWD computation plus cheap
        # re-derivations, and with band slack cached at the largest cutoff axis B needs no band
        # recomputation either. Axis A (component-cost perturbation) is the only one that changes
        # resistance and is DEFERRED pending H2 (perturbation ranges are a judgment call).
        "ensemble": {
            "cutoff_mult": [0.5, 1.0, 2.0],      # axis B, x cwd_cutoff_abs
            "leave_one_out": True,               # axis C, one run per node (mandatory-complete)
            "beta_sweep": [1.5, 2.5, 4.0],       # axis D
            "robust_core_freq": 0.9,
        },

        # ---- named variants -------------------------------------------------------------
        # A variant is an override dict merged over this config and solved into its own run dir.
        # This is where D4's climate scenario attaches in Phase 7 -- resist-vs-facilitate is an
        # adaptation-philosophy choice that must be a VISIBLE scenario axis, never a blend weight.
        "variants": {},
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
#                    "reciprocal" -> 1 / x   (backward velocity -> refugial residence time)
#                    "invert"     -> vmax - x (SUPERSEDED by "reciprocal"; kept so pre-2026-08-17
#                                    runs stay reproducible -- see the macrorefugia entry)
#                    omitted/None -> already "more = better", leave raw
#
#                    ADDITIVE FLIPS DESTROY LEVERAGE -- the trap this list now encodes. 03
#                    sum-normalizes each feature, so an additive offset does NOT cancel: it
#                    compresses the feature toward a constant, and a feature whose value is
#                    near-constant across cells contributes a near-constant objective term that
#                    NO weight can turn into a decision. Both additive flips did exactly this:
#                    `1 - gHM` cut gHM's leverage 0.742 -> 0.042 (94% lost, because gHM is
#                    right-skewed: median 0.018, so intactness piles up at ~0.98), and `vmax - v`
#                    cut velocity's 0.353 -> 0.090 (75% lost). Those were the two lowest-ranked
#                    factors in the 06 Morris screening -- an artefact read as a finding. Prefer a
#                    MULTIPLICATIVE orientation; see leverage_core for how to check one.
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
    # FILE NAMING (decoded from the dataset's own ReadMe_ClimateNA_CMIP6_zenodo.txt, Zenodo
    # 10.5281/zenodo.10631707): [direction][metric][version]_[GCM]_[SSP]_[period].tif
    #   bw / fw    inbound (backward) / outbound (forward) direction
    #   vel / disp velocity / proportion of disappearing (no-analog) climates
    #   731        ClimateNA software version 7.31  <- NOT a threshold or climate-type code
    #   245/370/585  SSP low-moderate / moderate / high emissions
    #   period     2041-2070 or 2071-2100, against a 1961-1990 historical normal baseline
    # Analogs are matched by multivariate PCA over 11 climate variables (MAT, MWMT, MCMT, TD,
    # MAP, MSP, MWP, DD5, NFFD, Eref, CMD); no-analog cells are NODATA.
    #
    # BACKWARD velocity = distance from a cell's FUTURE climate to its nearest analog in the
    # CURRENT climate, per year. Low = the future climate already exists nearby = macrorefugium,
    # hence an inverting orientation. Units km/yr are a per-year AVERAGE over the elapsed
    # baseline->future span, so the 2071-2100 layers divide by a LONGER denominator than 2041-2070
    # -- late-century values are diluted, not simply more extreme (the CMIP6 readme does not
    # restate the exact denominator; the CMIP5 sibling product documents distance / years-elapsed).
    #
    # ORIENTATION CHANGED 2026-08-17: "invert" (vmax - v) -> "reciprocal" (1/v). The additive flip
    # added a large constant (p1 rose 0.60 -> 9.23 km/yr) which, under 03's sum-normalization, does
    # not cancel -- it crushed the layer's leverage from 0.353 to 0.090 and made macrorefugia the
    # single least influential factor in the 06 Morris screening. That was an artefact of this
    # line, not a property of the climate data. 1/v restores leverage to 0.422 -- above the raw
    # layer's own 0.353 -- and reads as refugial residence time (yr/km) rather than
    # distance-from-the-worst-cell-in-the-window. The tail is safe: min velocity over the PU is
    # 0.097 km/yr, so 1/v maxes at 10.3 and the top 100 cells hold 0.1% of the total (checked).
    # NOTE this does NOT invalidate the Phase-1a scenario QA: top-q refugial set membership is
    # invariant under ANY monotone-decreasing transform of v, so the MATERIAL verdict and its
    # 0.460-0.910 Jaccards carry over unchanged.
    "climate_type_macrorefugia": {
        "path": INPUT_DIR / "climate_type_macrorefugia" / "ensemble_8gcm",
        "include": "bwvel731",  # backward climatic velocity scenarios only
        "rep_contains": "bwvel731_ensemble_8gcm_585_2071_2100",  # chosen scenario
        "multi": False,
        "resampling": "bilinear",
        "orient": "reciprocal",  # low backward velocity = high refugial value -> 1 / v
        "citation": ("AdaptWest Project 2023, Gridded CMIP6-based climate velocity data for "
                     "North America at 1km resolution (adaptwest.databasin.org; "
                     "doi:10.5281/zenodo.10631707), backward velocity, 8-GCM ensemble"),
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


# ---- Climate-scenario materiality diagnostic (02 stage-1 QA; Phase 1a) ---
# `DATASETS["climate_type_macrorefugia"]` uses ONE of six AdaptWest realizations
# (SSP 245/370/585 x 2041-2070/2071-2100) -- currently 585_2071_2100, the hottest SSP at the
# latest horizon, i.e. the LEAST refugial of the set. That single pick is an unstated choice.
# Before spending six full 1 km solves (~7.6 h) or a sensitivity-analysis factor slot on it, 02
# warps all six and measures whether they differ in a DECISION-RELEVANT way. Diagnostic only:
# these rasters live in their own subfolder, are never oriented, and can never reach a prioritizr
# problem (write_manifest builds features from DATASETS keys + aligned_stack/iucn_efg/*.tif, and
# never globs the hand-off top level).
#
# The comparison runs on RAW backward velocity, NOT the oriented `vmax - v` feature: the flip is
# a monotone affine map, so it leaves both correlation and top-quantile membership unchanged.
CLIMATE_SCENARIOS = {
    "src_dir": INPUT_DIR / "climate_type_macrorefugia" / "ensemble_8gcm",
    "out_dir": ALIGNED_DIR / "climate_scenarios",
    "prefix": "bwvel731_ensemble_8gcm_",     # backward velocity, 8-GCM ensemble
    # key -> source filename. Keys sort chronologically within SSP; order is the report order.
    "members": {
        "245_2041_2070": "bwvel731_ensemble_8gcm_245_2041_2070.tif",
        "245_2071_2100": "bwvel731_ensemble_8gcm_245_2071_2100.tif",
        "370_2041_2070": "bwvel731_ensemble_8gcm_370_2041_2070.tif",
        "370_2071_2100": "bwvel731_ensemble_8gcm_370_2071_2100.tif",
        "585_2041_2070": "bwvel731_ensemble_8gcm_585_2041_2070.tif",
        "585_2071_2100": "bwvel731_ensemble_8gcm_585_2071_2100.tif",
    },
    "current": "585_2071_2100",   # the member DATASETS currently points at (identity check)
    "resampling": "bilinear",     # same as the DATASETS entry -- must match to stay comparable
    # Overlap statistic: fraction of PU cells taken as "the priority set" for the Jaccard. Tied
    # to BUDGET_PCT so the number answers the decision question ("would the selected 30% move?"),
    # not just "are the surfaces correlated".
    "top_q": BUDGET_PCT,
    # Percentiles reported (NOT applied) as candidate SHARED anchors for a future Phase 1b, where
    # all six would need one common affine map. p1/p99 rather than min/max because the tails are
    # single-pixel artefacts -- the same reasoning that fixed CORRIDORS driver scaling (2026-07-27).
    "anchor_pctiles": (1, 99),
    # PRE-REGISTERED decision rule -- fixed here BEFORE the numbers are seen, so the downstream
    # consequence is not chosen post hoc. See the plan / CLAUDE.md.
    "rule": {
        # IMMATERIAL: keep one scenario (stated as a choice), document in the supplement, drop
        # the scenario factor from the sensitivity design, skip the six-solve Phase 1b.
        "immaterial": {"min_spearman": 0.90, "min_jaccard": 0.80},
        # MATERIAL: scenario enters the sensitivity design as a factor AND Phase 1b is warranted.
        "material": {"max_jaccard_below": 0.60},
        # anything else -> AMBIGUOUS: enters the design; Phase 1b decided at the screening gate.
    },
}


# ---- ROI + hand-off helpers ----------------------------------------------
def _rel(p):
    """Path relative to the project root, POSIX-style (for the R-readable manifest)."""
    return Path(p).resolve().relative_to(PROJECT_DIR).as_posix()


def _load_source(path, filt=None):
    """Read a vector in TARGET_CRS, optionally subset by the analysis' `source_filter`.

    Supports {"min_lat": deg} / {"max_lat": deg} on the feature CENTROID -- used to take only the
    northern (BC + Yukon) proposed PAs out of the corridor-wide file. Applied to BOTH the ROI
    sources and the lock-in vector so the window and the anchors can never disagree."""
    import geopandas as gpd

    g = gpd.read_file(path).to_crs(TARGET_CRS)
    if filt:
        # centroid in the PROJECTED CRS (g is already TARGET_CRS), then to lat/lon -- computing
        # centroids in EPSG:4326 directly is geometrically incorrect.
        cen = g.geometry.centroid.to_crs("EPSG:4326")
        if filt.get("min_lat") is not None:
            g = g[cen.y >= filt["min_lat"]]
        if filt.get("max_lat") is not None:
            g = g[cen.y <= filt["max_lat"]]
        if g.empty:
            raise ValueError(f"source_filter {filt} removed every feature from {path}")
    return g


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
    gdfs = [_load_source(s, ANALYSES[analysis].get("source_filter")) for s in srcs]

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
        _load_source(vp, a.get("source_filter")).to_file(out, driver="GPKG")   # same filter as ROI
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
            # Per-feature target overrides, emitted as a NAME->value object rather than a bare
            # vector on purpose: the R side rebuilds the vector by looking each feature up in
            # problem order, so it cannot silently drift out of alignment with the feature stack
            # (a bare vector would apply the wrong target to the wrong feature with no error).
            # Same guard pattern as feature_weight_multipliers.
            "targets": a.get("targets", {}),
            "opt_gap": OPT_GAP,
            "portfolio_n": PORTFOLIO_N,
            "portfolio_gap": PORTFOLIO_GAP,
            "connectivity_penalty": a["connectivity_penalty"],
            # percentile the connectivity matrix is winsorized at before normalising (R side)
            "connectivity_cap_pctile": a.get("connectivity_cap_pctile", 0.99),
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
