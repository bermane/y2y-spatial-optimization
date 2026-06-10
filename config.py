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

# Aligned outputs from 02 live inside input_data/ (EFGs in an iucn_efg/ subfolder).
ALIGNED_DIR = INPUT_DIR / "cleaned_aligned"

# ---- Target grid (decided 2026-06-10; see CLAUDE.md) ---------------------
TARGET_CRS = "ESRI:102008"   # North America Albers Equal Area Conic
TARGET_RES_M = 1000          # 1 km, first iteration
BUFFER_KM = 20               # study area = Y2Y boundary buffered by this many km

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
DATASETS = {
    "human_modification": {
        "path": INPUT_DIR / "human_modification",
        # VRT was deleted; 01 reads the main tile. 02 rebuilds the VRT from all tiles.
        "representative": "HM_Y2Y_2024_90_60land-0000000000-0000000000.tif",
        "multi": False,
        "resampling": "average",  # gHM ~90 m -> 1 km
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
