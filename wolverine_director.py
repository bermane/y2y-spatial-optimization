"""wolverine_director -- director-level maps and tables for the wolverine refugia corridors
(analyses/wolverine_refugia_connectivity; spec/06_wolverine_director_package_spec.md).

Built on the northern cartographic contract (`corridors_mapstyle`, MAP coordinates on the 300 m
routing template) over the whole Y2Y frame, reusing the grid-independent pieces of
`director_core` (towns, province words, the PA layer) and the generic pieces of
`corridors_director` (routing classes, jurisdictions, pressure polygons, table renderer).
Every asset is ONE function with its knobs in STYLE; the record notebook (04) and the curated
notebook (05) both call it -- never copy drawing code into a notebook (Ethan's asset rule).

Nodes here are CORE WOLVERINE REFUGIA PATCHES, not protected areas: existing PAs are drawn as
outline context on every map and are never called nodes. The corridor-pressure classes are the
north's D7 / D12 (/ D17 when the counterfactual has run; the H8 logic withholds "squeezed"
otherwise). Ensemble attribution is absent until the ensemble runs (parked, spec section 7).
"""
import json
import pathlib
import re
from types import SimpleNamespace

import numpy as np
import pandas as pd
import geopandas as gpd
import pyproj
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from matplotlib.colors import ListedColormap
from rasterio.features import rasterize, shapes as _shapes
from shapely.geometry import shape as _shape, box as _box, Point

import config
import corridors_core as cc
import corridors_mapstyle as ms
import corridors_director as cd
import director_core as dc

PKG_SUB = "director_package"
# 2026-10-01 (Ethan, mirroring the northern change of the same day): the package lives beside the notebooks in the
# y2y / Alberta folder structure -- analyses/wolverine_refugia_connectivity/director_package/{geotiffs, tables, figures,
# director_outputs} + summary.json (the tracked index naming the run) -- not inside the gitignored run dir.
# `package(..., out=)` overrides. One package holds ONE run: building from another run first moves the previous
# contents to `_superseded_<run>/` (corridors_director._supersede_other_run, the y2y convention).
PKG_DIR = config.PROJECT_DIR / "analyses" / "wolverine_refugia_connectivity" / PKG_SUB
HILLSHADE = config.INPUT_DIR / "basemap" / "hillshade_y2y_300m.tif"

# ---- every knob a notebook may turn (Ethan's asset rule) ---------------------------------
STYLE = dict(
    frame_pad_km=40,            # full-frame maps: Y2Y bbox + pad
    full_step=3, act_step=1,    # raster decimation: full page (1 px ~ 1 km at 300 dpi) / act crops
    hillshade_max_px=2400,
    river_rank_full=6, river_rank_act=9,
    scale_km_full=250, scale_km_act=100,
    w0_names=12, w1_names=8, act_names=6, act_towns=6,     # how many node names / towns to try to place
    node_chips=True,            # number chips on every node (full maps) / every node in the window (acts)
    w1_marginal=True,           # draw the marginal refugia under the classes on W1
    pa_min_km2=300,             # PA outline context: PAs at or above this size
    k_close_per_act=1, k_open_per_act=1, max_examples=4,   # automatic example selection: the deck's numbered route options (the north shows 4)
    inset_max_km=700,                                       # two options share an inset window only when their land fits in this
    act_pad_km=40, act_min_km=450,                          # act windows
    act_breaks_lat=(58.5, 51.0),                            # north >= 58.5 N, central 51-58.5, south < 51 (fallback: terciles)
    towns_full=["Whitehorse", "Fort St. John", "Prince George", "Calgary", "Missoula", "Jackson"],
    withheld_colours={"elevation_gt_2300_m": "#1B9E77", "slope_gt_30_deg": "#7570B3", "glacier": "#80B1D3"},
    endpoint_protected_frac=0.5,                            # a node counts as 'protected' when PAs cover >= this share
    # W11 -- how protected land (existing PAs + proposed conservation areas, taken as given) enters the maps:
    #   "overlay":          draw every corridor band in full; hatch the protected land on top; links already
    #                       connected within protected land ('satisfied') drawn muted and labelled
    #   "unprotected_only": draw only the corridor land still to secure; satisfied links omitted
    protected_mode="overlay",
    satisfied_alpha=0.45,                                   # fill alpha for satisfied links in overlay mode
    satisfied_outline={"pa": "#4D4D4D", "ipca": "#3E6F70"}, # outline colour of a satisfied link: by existing PAs / by proposed conservation areas
    protected_hatch={"pa": "///", "ipca": "\\\\"},             # PA hatch vs IPCA hatch over the bands
    protected_hatch_colour={"pa": "#4D4D4D", "ipca": "#3E6F70"}, protected_hatch_lw=0.5,
    draw_near_contiguous=True,                              # v2: hatched grey under the classes; v2.5 sets False (D-W6)
    inset_label_slivers=True,                               # v2.5: complex labels carry [within-complex slivers]
    complex_shade_bins=(0.25, 0.50, 0.75),                  # v2.5: complex fill alpha steps by share inside existing PAs
    complex_shade_alphas=(0.25, 0.45, 0.65, 0.90),
    pinch_marker=True, bow_valley_lat=51.2, banff_lonlat=(-115.57, 51.18), banff_check_km=60,   # the p10 pinch on each corridor link; the act check
)
V25_STYLE = dict(act_breaks_lat=(51.0,), draw_near_contiguous=False, inset_label_slivers=True, pinch_marker=False, protected_layers=False,   # run spec v3 §1a defaults
                 front_style="plain",                              # Ethan 2026-09-29: fronts are links on the one pressure scale -- drawn in their class colour like
                 front_legend_rows=False)                          # strips, nothing separate ("tint" = the spec §8 tint treatment; "hidden" = strips only); no legend rows
# FIXED insets at the northern package's scale (Ethan 2026-09-29): every wide map (01-03 + the locators) shares two windows of the
# northern insets' extent (193 x 214 km after the fit to the inset aspect, measured on north/v2_run003), A centred on the links between
# the Nahanni complex and the complexes south of it, B on the Missoula / Helena / Salmon / Bozeman centroid.
INSET_KM = (312.0, 346.0)      # the northern insets are 193 x 214 km; Ethan 2026-09-29: enlarged so A holds the full Nahanni links south (fitted once)
STYLE.update(option_markers=False,                           # 04: the old leader markers OFF (Ethan 2026-09-29: 'get rid of clusters'); numbers come from the northern placer
             option_style="outline",                           # 04 (Ethan 2026-09-29): options OUTLINED in their colour so the pressure fill shows | "fill" = the coloured band
             option_legend="swatches",                         # 04's legend: "swatches" (the y2y cluster row, colours in option order) | "rows" | "none"
             options_protected=True,                           # 04 carries 03's protected-land layer + names
             surface_alpha=0.85,                               # the corridor-pressure surface + its key at this alpha so the boundary lines show through (Ethan 2026-09-29)
             cost_surface_alpha=0.70,                          # 01's cost surface (Ethan 2026-09-29: more see-through than 02/04 so the boundaries read); None = follow surface_alpha
             protection_surface_alpha=0.65,                    # 03's pressure surface over the grey: lower still, so band-over-protected-land reads (Ethan 2026-09-29); None = surface_alpha
             protection_fill="#8f8f8f", protection_alpha=0.85, # 06 · 03: existing PAs AND proposed conservation areas in the y2y layout's PA grey (director_plot.PA_COLOR) at 85%
             protection_fill_pa=None, protection_fill_ipca=None,   # set BOTH to split the kinds into two neutrals (two legend rows); None = protection_fill for both
             protection_label_pa="Existing protected areas", protection_label_ipca="Proposed conservation areas",
             protection_zorder=0.45,                           # ... drawn UNDER the corridor-pressure surface (0.5); 1.0 puts the grey over the bands
             protection_label="Existing PAs and proposed conservation areas",     # short: the box must stay inside inset B's width
             protection_pa_names=4, protection_ipca_names=3,   # 06 · 03 (Ethan 2026-09-29): the largest PAs / proposed conservation areas named in each inset (0 = none)
             protection_pa_min_km2=100,                        # PAs below this are never named there
             protection_ipca_suffix=", proposed",             # appended to a proposed area's name (both kinds share the one grey)
             protection_frame_names=False,                     # names on the Y2Y frame panel too (default: insets only)
             complex_labels="none",                          # "none" (Ethan 2026-09-29: the R numbers are just node ids) | "number" | "name" (when names are chosen)
             inset_km=INSET_KM,
             inset_specs={"A": dict(center_lonlat=(-126.05, 60.45), title="Nahanni's links south"),          # nudged ~20 km west, ~25 km south (Ethan 2026-09-29)   # fit = size the window to those links' corridor land + pad
                          "B": dict(towns=["Missoula", "Helena", "Salmon", "Bozeman"], title="The southern edge")})   # centre = the towns' centroid
# 06 · 01, the movement-cost map (Ethan 2026-09-29): no PAs / IPCAs, the refugia in a hue with no counterpart in magma (lime green:
# min dE 22 against the four cost swatches + water under every colour-vision simulation, as the indigo, but not in magma's purple
# family), a thin outline, plain labels. `cost_map_context=True` restores the PA / IPCA layers.
STYLE.update(protected_layers=False,                       # PAs / IPCAs on the wide maps (01-03, the locators): OFF (Ethan 2026-09-29) -- the
             cost_map_refugia_fill="#5BA699", cost_map_refugia_alpha=0.85, cost_map_outline=("#2F5F55", 0.3),   # protection analysis is a separate product.
             # Refugia fill (Ethan 2026-09-29: "a green-ish tint that works with the sand colour bar"): a muted sea-green, hue 170 / sat 0.45 /
             # val 0.65 from a grid search over the green family -- dE 20.1 vs the sand pressure classes + water, 22.0 vs the magma cost
             # swatches + water, 22.4 vs the four route-option colours (CIE76; normal + deuteranopia + protanopia). Pure greens / limes fail
             # against sand's brown or the option orange; indigo #4D4DBF (20.1 / 22.0 / 20.3) is the alternative.
             # (earlier note: indigo was the only NON-green candidate found before the green-family grid search)
             cost_map_refugia_label="Core wolverine refugia", cost_map_ramp_label="Cost of moving through the land",
             cost_tick_words={10: "roads and\nforestry\ncutblocks", 100: "farmland,\nother\nconverted\nland", 1000: "water,\nsettlement"},   # chat 2026-09-29: no jargon ("cuts"); no ice at 1000 (W1)
             frame_reduce="any",                               # 300 m -> 600 m frame by block ANY / nanmax (Ethan 2026-09-29: continuous bands stay continuous); "stride" = the old sampling
             cost_split_water=True, cost_water_fill="#4F63C9",   # 01 (chat 2026-09-29): open water out of the 1,000 swatch in a blue-purple; settlement keeps magma's dark
             cost_water_word="open\nwater", cost_settlement_word="settlement,\nother\nbarriers")

# hand-placed jurisdiction / town labels for the FULL Y2Y frame (lon/lat; Ethan signs)
FULL_SPEC = dict(
    jurisdictions=[("YUKON", (-134.5, 62.9)), ("NORTHWEST\nTERRITORIES", (-126.0, 64.9)),
                   ("BRITISH\nCOLUMBIA", (-126.5, 55.3)), ("ALBERTA", (-113.6, 53.3)),
                   ("MONTANA", (-110.6, 47.6)), ("IDAHO", (-115.2, 44.6)), ("WYOMING", (-108.9, 43.4))],
    towns=[("Whitehorse", "right", 5, 0), ("Fort St. John", "right", 5, 0), ("Prince George", "left", -5, 0),
           ("Calgary", "right", 5, 0), ("Missoula", "left", -5, 0), ("Jackson", "right", 5, 0)],
)
ACT_SPEC = {
    "north":   dict(fig_id="W2", title="Wolverine Corridors: The North", message="TBC after the run"),
    "central": dict(fig_id="W3", title="Wolverine Corridors: The Central Rockies", message="TBC after the run"),
    "south":   dict(fig_id="W4", title="Wolverine Corridors: The Southern Edge", message="TBC after the run"),
}
# The deck's route options (Ethan 2026-09-29; 06 · 04): inset A = the two southern branches from the Nahanni node that lie OUTSIDE
# Nahanni National Park Reserve (its two links south to the Muncho Lake refugia), inset B = the two big corridors in the middle of the
# panel -- Selway-Bitterroot <-> Lee Metcalf (one part) and Selway-Bitterroot <-> Skull-Odell (two route branches). Pinned by EDGE
# id (the run's stable link ids; the pair is the human-readable check), numbered north -> south by select_examples = 1-2 in A, 3-4 in B.
# Empty list = the automatic class-and-width rule. Schema otherwise = corridors_director.EXAMPLE_PICKS (pair / act / slot / side).
EXAMPLE_PICKS = [
    dict(edge_id="E020_023", pair=("R21 Nahanni", "R24 Muncho Lake"), act="north", slot="A-1", side="nw"),     # 4,013 km², options, 0% inside Nahanni NPR
    dict(edge_id="E020_026", pair=("R21 Nahanni", "R27 Muncho Lake"), act="north", slot="A-2", side="se"),     # 3,833 km², options, 0% inside Nahanni NPR
    dict(edge_id="E110_120", pair=("R111 Selway", "R121 Lee Metcalf"), act="south", slot="B-3", side="ne"),    # 758 km², narrowing, one branch
    dict(edge_id="E110_119", pair=("R111 Selway", "R120 Skull-Odell"), act="south", slot="B-4", side="sw"),    # 1,091 km², options, two branches
]
ACT_ORDER = ["north", "central", "south"]


# ================= package context =================
# the near-contiguous tokens: the mapstyle's when it carries them (D25a), else this local set -- the northern D25c refactor
# (2026-09-29) retired them from corridors_mapstyle; under v2.5 they are never drawn (D-W6) and the contracted run has none
NEAR_TOKENS = getattr(ms, "NEAR_CONTIGUOUS", None) or {
    "near_contiguous_open":    dict(fill="#D9D9D9", hatch="\\\\", hatch_color="#8A8A8A", outline=None, label="Adjacent areas — open front"),
    "near_contiguous_roads":   dict(fill="#D9D9D9", hatch="\\\\", hatch_color="#8A8A8A", outline=("#8A8A8A", 0.6), label="Adjacent areas — front crossed by roads or cuts"),
    "near_contiguous_barrier": dict(fill="#D9D9D9", hatch="\\\\", hatch_color="#8A8A8A", outline=("#3A3A3A", 0.8), label="Adjacent areas — barrier between"),
}
NEAR_KEYS = tuple(NEAR_TOKENS.keys())


def _norm_class(c):
    """A link_class value -> the package's class key: corridor classes as they are; any near-contiguous value mapped onto the
    mapstyle's tokens (a pre-D25a 'near_contiguous' -> the open-front token; '..._barrier' / '..._roads' kept)."""
    c = str(c)
    if c.startswith("near_contiguous"):
        if c in NEAR_KEYS:
            return c
        return "near_contiguous_barrier" if c.endswith("barrier") else ("near_contiguous_roads" if c.endswith("roads") else NEAR_KEYS[0])
    return c


def _is_near(c):
    return str(c).startswith("near_contiguous")


def package(R, out=None, picks=None):
    """Assemble everything the figures need from a loaded run (cc.load_results): the disjoint
    pressure classes, the owner partition, the node table with names and PA overlap, the
    refugia classes, the PA context, jurisdictions, acts and the example selection."""
    assert getattr(R, "refugia", None) is not None, "this run has no refugia classes -- not a raster-node run"
    P = SimpleNamespace(R=R, out=pathlib.Path(out) if out else PKG_DIR)
    cd._supersede_other_run(P.out, R.run_id)
    P.fig, P.tab, P.gis = P.out / "figures", P.out / "tables", P.out / "geotiffs"      # geotiffs/ (was gis/ until 2026-10-01)
    for d in (P.fig, P.tab, P.gis):
        d.mkdir(parents=True, exist_ok=True)
    e, classes = cc._routing_classes(R)
    P.edges = e
    P.h8_open = not ("squeezed" in R.edges.columns and R.edges["squeezed"].notna().any())
    P.classified = "link_class" in R.edges.columns                    # D23/D24/D25: classify_links ran (the single source)
    P.contracted = bool(getattr(R, "contracted", False))               # v2.5: nodes are refugia complexes (wolverine_postprocess.attach)
    if P.classified:                                                   # read the single source directly (robust to the D25a three-way split
        cls = e["link_class"].astype(str).map(_norm_class)             # of the near-contiguous class; run001 predates it)
    else:
        both, irr, sq = classes[0][1], classes[1][1], classes[2][1]
        cls = pd.Series("securing", index=e.index)
        cls[sq] = "squeezed"; cls[irr] = "edge"; cls[both] = "both"
    cls[e["is_adjacency"] | (e["cost"] <= 0)] = "adjacency"
    P.kind = (R.edges["kind"].reindex(e.index).fillna("strip") if "kind" in R.edges.columns else pd.Series("strip", index=e.index))   # node level: front / strip
    P.kind[cls == "adjacency"] = "adjacency"
    for k in getattr(R, "intra_complex_ids", []) or []:                 # v2.5: corridor-class links with both ends in one complex --
        if k in cls.index:                                              # listed with the slivers, never drawn or counted as corridors
            cls[k] = "intra_complex"
    P.cls = cls
    P.owner = np.nan_to_num(R.edge_owner.values, nan=-1).astype(int)
    P.order = {k: i for i, k in enumerate(R.edges.index)}
    P.node_mask = R.pa_mask | R.anch                     # every node, whatever kind; never "protected"
    P.refugia = R.refugia
    P.nodes = _node_table(R)
    P.pa_context = dc.pa_layer(SimpleNamespace(crs=R.crs), min_km2=STYLE["pa_min_km2"])
    # W11: protected land as a STATUS layer (grids from load_results; vectors for the hatch / outlines)
    P.protected = getattr(R, "protected", None)
    P.corridor_unprotected = getattr(R, "corridor_unprotected", None)
    if P.corridor_unprotected is None:
        P.corridor_unprotected = R.corridor if P.protected is None else (R.corridor & ~P.protected)
    P.pa_all = dc.pa_layer(SimpleNamespace(crs=R.crs), min_km2=0.0)
    pc = R.cfg.get("nodes", {}).get("protected") or {}
    P.ipca = (gpd.read_file(config.PROJECT_DIR / pathlib.Path(pc["proposed"])).to_crs(R.crs)
              if pc.get("include_proposed") and pc.get("proposed") else gpd.GeoDataFrame(geometry=[], crs=R.crs))
    P.secured_by = (R.edges["secured_by"].fillna("").astype(str) if "secured_by" in R.edges.columns
                    else pd.Series("", index=R.edges.index))
    P.secured = P.secured_by != ""
    P.pa_mask300 = R.context_pa if getattr(R, "context_pa", None) is not None else rasterize(
        [(g, 1) for g in P.pa_context.geometry], out_shape=R.shape, transform=R.transform, fill=0, dtype="uint8").astype(bool)
    P.prov_raster, P.prov_names = cd._province_raster(R, countries=None)
    P.jur = cd._edge_jurisdictions(P)
    P.acts = _act_of_edges(P)
    P.examples = select_examples(P, picks)
    P.qa = {}
    n = cls.value_counts()
    geo = (f" | geometric classes first (D25/D24): adjacent {sum(v for k, v in n.items() if _is_near(k))} "
           f"(barrier between {n.get('near_contiguous_barrier', 0)}), width not assessable "
           f"{int(R.edges['width_not_assessable'].fillna(False).astype(bool).sum()) if 'width_not_assessable' in R.edges.columns else 0}"
           if P.classified else " | classes from the flags (run classified BEFORE D23 -- re-run 03)")
    print(f"wolverine package: classes -> only viable {n.get('both', 0)} · last affordable {n.get('edge', 0)} · narrowing {n.get('squeezed', 0)} "
          f"· options {n.get('securing', 0)}{geo} | {len(P.nodes)} nodes | {len(P.examples)} examples | "
          f"H8 {'OPEN -- squeezed withheld' if P.h8_open else 'closed'} | already connected: {int((P.secured_by == 'pa').sum())} "
          f"within existing PAs, {int((P.secured_by == 'ipca').sum())} only with the proposed conservation areas (mode '{STYLE['protected_mode']}')")
    write_summary(P)                                                   # the tracked index: which run this package holds
    try:
        print(f"package -> {P.out.relative_to(config.PROJECT_DIR)}  (run {R.run_id})")
    except ValueError:
        print(f"package -> {P.out}  (run {R.run_id})")
    return P


def write_summary(P):
    """The package's tracked index (gitignore keeps summary.json + deck_outline.md): which run it was built
    from and the headline counts, so a commit still says what the package contained."""
    R, e = P.R, P.edges
    cls = P.cls[~P.cls.isin(["adjacency"])] if hasattr(P, "cls") else pd.Series(dtype=str)
    s = dict(
        analysis="wolverine_refugia_connectivity", run=R.run_id, run_dir=str(R.run_dir.relative_to(config.PROJECT_DIR)),
        run_git=R.rec.get("git"), cutoff=R.cutoff, cutoff_detour_km=R.cfg.get("cutoff_detour_km"),
        n_nodes=int(len(P.nodes)), n_links=int(len(e)), contracted=bool(P.contracted), classified=bool(P.classified),
        classes={k: int((cls == k).sum()) for k in ("both", "edge", "squeezed", "securing")},
        link_geometry=({str(k): int(v) for k, v in e["link_geometry"].value_counts().items()}
                       if "link_geometry" in e.columns else None),
        corridor_km2=R.summary.get("corridor_area_km2", R.summary.get("corridor_km2")), h8_open=bool(P.h8_open),
        already_connected=dict(pa=int((P.secured_by == "pa").sum()), ipca=int((P.secured_by == "ipca").sum())),
        layout="analyses/wolverine_refugia_connectivity/director_package/{geotiffs,tables,figures,director_outputs} (y2y convention, 2026-10-01)",
        built=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
    )
    (P.out / "summary.json").write_text(json.dumps(s, indent=2, ensure_ascii=False, default=str))
    return s


def _complex_table(R):
    """v2.5 (run spec v3 §1a; wolverine_postprocess.attach): the node table IS the complex table -- geometry, D-W7 names and the
    coverage + sliver columns from postprocess/complexes.gpkg; node_id = complex_id (north -> south); pa_overlap_frac = the
    share inside existing PAs."""
    g = R.complexes.copy()
    g["node_id"] = g["complex_id"].astype(int)
    mode = STYLE.get("complex_labels", "number")                    # Ethan 2026-09-29: the auto-names (nearest PA) are OFF the outputs until
    if mode == "name":                                              # real names are chosen; complexes are labelled by NUMBER (C12) meanwhile
        g["short"] = [cc._short_node_name("X · " + n.replace("Refugia complex (", "").replace("Refugium (", "").rstrip(")"), 22) for n in g["name"]]
    elif mode == "none":
        g["short"] = ""
    else:
        g["short"] = [f"C{int(c)}" for c in g["node_id"]]
    g["core_km2"] = g["area_km2"]
    g["pa_overlap_frac"] = g["pa_share"] if "pa_share" in g.columns else 0.0
    g["pa_overlap_name"] = ""
    g["name_label"] = [f"Complex · C{c:02d} {n}" for c, n in zip(g["node_id"], g["name"])]
    for c in ("n_slivers", "n_slivers_with_feature", "ipca_added_share", "core_share", "outside_all_share", "n_fronts", "n_cut", "n_E_interior"):
        if c not in g.columns:
            g[c] = 0
    return g.sort_values("node_id").reset_index(drop=True)


def _node_table(R):
    """One row per node: geometry from node_parts.gpkg, names from the run's node_names.csv
    (display_name if filled, else the auto-name), number = node_id (north -> south). Post-processed run -> the complexes."""
    if getattr(R, "contracted", False) and getattr(R, "complexes", None) is not None:
        return _complex_table(R)
    g = gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(R.crs)
    if "node_id" not in g.columns:
        g["node_id"] = np.arange(1, len(g) + 1)
    g = g.sort_values("node_id").reset_index(drop=True)
    nt = getattr(R, "node_table", None)
    if nt is not None:
        nt = nt.copy(); nt["display_name"] = nt["display_name"].astype(str).str.strip()
        nt["name"] = np.where(nt["display_name"] != "", nt["display_name"], nt["label_auto"])
        keep = [c for c in ("node_id", "name", "label_auto", "area_km2", "n_cells", "lat", "lon",
                            "pa_overlap_name", "pa_overlap_frac", "nearest_pa", "nearest_pa_km", "bearing", "share_north_model",
                            "pa_share", "ipca_added_share", "core_share", "core_incremental_share", "outside_all_share", "mean_ghm90max",   # the node-level
                            "n_links", "n_fronts", "n_strips", "n_securing", "n_squeezed", "n_edge", "n_both") if c in nt.columns]              # product (05)
        g = g.drop(columns=[c for c in keep if c in g.columns and c != "node_id"], errors="ignore").merge(nt[keep], on="node_id", how="left")
    if "name" not in g.columns:
        g["name"] = [cc._short_node_name(n, 40) for n in g.name_label]
    mode = STYLE.get("complex_labels", "number")                          # node level: "R12" until names are chosen (Ethan 2026-09-29)
    if mode == "name":
        g["short"] = [cc._short_node_name("X · " + str(n).replace("Refugium (", "").rstrip(")"), 22) for n in g["name"]]
    elif mode == "none":
        g["short"] = ""
    else:
        g["short"] = [f"R{int(c)}" for c in g["node_id"]]
    g["core_km2"] = g["area_km2"]
    if "pa_share" not in g.columns and "pa_overlap_frac" in g.columns:
        g["pa_share"] = g["pa_overlap_frac"]
    for c in ("ipca_added_share", "core_share", "core_incremental_share", "outside_all_share", "n_links", "n_fronts", "n_strips"):
        if c not in g.columns:
            g[c] = 0
    return g


def _short(P, node_id):
    r = P.nodes[P.nodes.node_id == int(node_id)]
    return str(r.iloc[0]["short"]) if len(r) else f"R{int(node_id):02d}"


def _node_id_of_label(P, label):
    """'Refugium · R12 name' -> 12; 'Refugium · R108 name' -> 108 (any number of digits -- 130 nodes here; a two-digit parse
    once mapped R108 to node 10)."""
    m = re.match(r"[RC](\d+)(?:\s|$)", str(label).split(" · ", 1)[-1])      # R = patch, C = complex (v2.5 post-processing)
    return int(m.group(1)) if m else None


def _act_of_edges(P):
    """Act per edge from the latitude of the median cell of its owned corridor land; edges with no
    owned land get NaN. Falls back to node-latitude terciles when a fixed band holds < 5 edges."""
    R = P.R
    to_ll = pyproj.Transformer.from_crs(R.crs, "EPSG:4326", always_xy=True)
    lat = {}
    for eid, k in P.order.items():
        m = (P.owner == k) & R.corridor
        xy = cd._median_cell(R, m)
        lat[eid] = to_ll.transform(*xy)[1] if xy else np.nan
    lat = pd.Series(lat)
    breaks = tuple(STYLE["act_breaks_lat"])
    if len(breaks) == 1:                                            # v3 default: two acts (run spec v3 section 8)
        P.act_order = ["north", "south"]
        act = pd.Series(np.where(lat >= breaks[0], "north", "south"), index=lat.index).where(lat.notna())
    else:
        n_br, s_br = breaks
        P.act_order = list(ACT_ORDER)
        act = pd.Series(np.where(lat >= n_br, "north", np.where(lat >= s_br, "central", "south")), index=lat.index).where(lat.notna())
        counts = act.value_counts()
        if any(counts.get(a, 0) < 5 for a in ACT_ORDER) and not getattr(P, "contracted", False):
            q = lat.dropna().quantile([1 / 3, 2 / 3]).values
            act = pd.Series(np.where(lat >= q[1], "north", np.where(lat >= q[0], "central", "south")), index=lat.index).where(lat.notna())
            print(f"  acts: a fixed latitude band held < 5 edges -> node-latitude terciles ({q[0]:.1f} N, {q[1]:.1f} N)")
    P.edge_lat = lat
    return act


def bow_valley_check(P, lonlat=None, radius_km=None):
    """Run spec v3 section 8: the Banff-Yoho links and the Bow Valley crossing must not straddle a presentation seam. Lists
    every corridor link whose band comes within `radius_km` of Banff with its act and its endpoints' latitudes; `straddles` is
    True when those links fall in more than one act or an endpoint sits on the other side of the southern break. The RULE
    (applied by the notebook, registered in the run record): move the southern break to STYLE["bow_valley_lat"]."""
    R = P.R
    lon, lat = lonlat or STYLE.get("banff_lonlat", (-115.57, 51.18)); radius_km = radius_km or STYLE.get("banff_check_km", 60)
    to_xy = pyproj.Transformer.from_crs("EPSG:4326", R.crs, always_xy=True); bx, by = to_xy.transform(lon, lat)
    xs, ys = R.template.x.values, R.template.y.values
    rows = []
    for eid, k in P.order.items():
        if P.cls.get(eid) not in cc.CORRIDOR_CLASSES or P.kind.get(eid, "strip") != "strip":
            continue
        m = (P.owner == k) & R.corridor
        rr, cc_ = np.nonzero(m)
        if not len(rr):
            continue
        d = np.hypot(xs[cc_] - bx, ys[rr] - by).min() / 1e3
        if d <= radius_km:
            r = R.edges.loc[eid]
            li, lj = _complex_of_edge(P, r)
            lat_i = float(P.nodes.set_index("node_id").loc[li, "lat"]) if li in P.nodes.node_id.values else np.nan
            lat_j = float(P.nodes.set_index("node_id").loc[lj, "lat"]) if lj in P.nodes.node_id.values else np.nan
            rows.append(dict(edge_id=eid, dist_to_banff_km=round(float(d), 1), act=P.acts.get(eid), band_lat=round(float(P.edge_lat.get(eid, np.nan)), 3),
                             lat_i=round(lat_i, 3), lat_j=round(lat_j, 3), link_class=P.cls.get(eid)))
    df = pd.DataFrame(rows)
    s_break = float(min(STYLE["act_breaks_lat"]))
    straddles = False
    if len(df):
        straddles = df["act"].nunique() > 1 or bool((((df["lat_i"] >= s_break) != (df["lat_j"] >= s_break))).any())
    print(f"Bow Valley check: {len(df)} corridor link(s) within {radius_km} km of Banff -> " + ("STRADDLE the southern break at "
          f"{s_break} N -> move it to {STYLE.get('bow_valley_lat', 51.2)} N (the rule; register the reason)" if straddles else "one act, no seam issue"))
    return df, straddles


# ================= example selection (automatic top-k, the north's picks schema as override) =================
def select_examples(P, picks=None):
    """Per act: the links under the most pressure (`both` by pairs lost / backup ratio, then
    `edge` by backup ratio, then `squeezed` by observed ratio) -> k_close_per_act; plus the
    securing links with the most route branches -> k_open_per_act. Numbered NORTH -> SOUTH.
    `picks` (or EXAMPLE_PICKS) in corridors_director's schema override the rule."""
    e = P.edges
    picks = picks if picks is not None else EXAMPLE_PICKS
    chosen = []
    if picks:
        for pk in picks:
            if pk.get("edge_id") is not None:                                  # pinned by the run's link id (wolverine, 2026-09-29); the pair is the readable check
                eid = pk["edge_id"] if pk["edge_id"] in e.index else None
                if eid is None:
                    print(f"  PIN RULE FIRES: {pk['edge_id']} ({pk.get('pair')}) is not a link of this run -- dropped")
                    continue
                r = e.loc[eid]
                if pk.get("pair") and not all(any(str(frag) in str(lab) for lab in (r.label_i, r.label_j)) for frag in pk["pair"]):
                    print(f"  WARNING: {eid}'s labels ({r.label_i} ↔ {r.label_j}) do not both match the pinned pair {pk['pair']} -- check the pin")
            else:
                eid = cd._find_edge(e, pk["pair"])
            if eid is None:
                continue
            chosen.append(dict(edge_id=eid, act=pk.get("act"), slot=pk.get("slot", ""), kind="pinned", side=pk.get("side", "nw")))
    else:
        for col in ("squeeze_ratio_obs", "width_ratio_p10", "n_pairs_lost", "n_branches"):
            if col not in e.columns:
                e[col] = np.nan
        for act in getattr(P, "act_order", ACT_ORDER):
            ids = [k for k in e.index if P.acts.get(k) == act and not bool(P.secured.get(k, False))    # W11: satisfied links are never examples
                   and P.cls.get(k) in cc.CORRIDOR_CLASSES and P.kind.get(k, "strip") == "strip"]         # examples = strips (spec §5: the last-affordable STRIPS)
            sub = e.loc[ids]
            close = []
            # class-and-width-first (the northern §2 rule, D26-D31): the top class ranked most-constrained first
            # (squeeze ratio asc, tenth-percentile width asc, then criticality), then "last affordable" by the p10 width
            for c, keys, asc in (("both", ["squeeze_ratio_obs", "width_ratio_p10", "n_pairs_lost"], [True, True, False]),
                                 ("edge", ["width_ratio_p10", "squeeze_ratio_obs", "n_pairs_lost"], [True, True, False]),
                                 ("squeezed", ["squeeze_ratio_obs", "width_ratio_p10"], [True, True])):
                cand = sub[P.cls.loc[ids] == c]
                if not len(cand):
                    continue
                cand = cand.sort_values(keys, ascending=asc, na_position="last")
                close += [dict(edge_id=k, act=act, slot=f"{act[0].upper()}-close", kind=c) for k in cand.index]
            chosen += close[:STYLE["k_close_per_act"]]
            sec = sub[(P.cls.loc[ids] == "securing")]
            if "n_branches" in sec.columns and len(sec):
                sec = sec[sec["n_branches"] >= 2].sort_values("n_branches", ascending=False)
                chosen += [dict(edge_id=k, act=act, slot=f"{act[0].upper()}-open", kind="securing") for k in sec.index[:STYLE["k_open_per_act"]]]
    # de-duplicate, cap BY PRIORITY (closing links first: both > edge > squeezed > room to choose), then number
    # north -> south by the latitude of the owned land (Ethan's convention)
    prio = {"both": 0, "edge": 1, "squeezed": 2, "securing": 3, "pinned": -1}
    seen, ex = set(), []
    for x in sorted(chosen, key=lambda x: prio.get(x["kind"], 9)):
        if x["edge_id"] in seen:
            continue
        seen.add(x["edge_id"]); ex.append(x)
    ex = ex[:STYLE["max_examples"]]
    ex.sort(key=lambda x: -float(P.edge_lat.get(x["edge_id"], -90)))
    for n, x in enumerate(ex, 1):
        r = e.loc[x["edge_id"]]
        x["num"] = n
        x["title"] = f"{_short(P, _node_id_of_label(P, r['label_i']) or 0)} ↔ {_short(P, _node_id_of_label(P, r['label_j']) or 0)}"
        x["cls"] = P.cls.get(x["edge_id"], "securing")
        # the northern package's example schema, so corridors_director's option machinery reads these as options
        x.setdefault("option_nums", [n]); x.setdefault("options", None); x.setdefault("mark", True); x.setdefault("side", "nw")
        if "squeeze_ratio_obs" in e.columns and x["cls"] == "squeezed" and pd.notna(r.get("squeeze_ratio_obs")):
            x["headline"] = f"already at {r['squeeze_ratio_obs']:.1f}× its natural width"
    P.appendix_flagged = [k for k in e.index if P.cls.get(k) in ("both", "edge") and k not in seen]
    return ex


def _example_mask(P, x):
    return (P.owner == P.order[x["edge_id"]]) & P.R.corridor


def _example_items(P):
    """(num, title, mask300, colour) per example -- the generic shape corridors_director's star
    and table machinery consumes (parked here; kept so the audit can bolt on)."""
    return [(x["num"], x["title"], _example_mask(P, x), ms.CLASS[x["cls"]][0] if x["cls"] in ms.CLASS else ms.CLASS["securing"][0])
            for x in P.examples]


# ================= frames =================
def full_frame(P):
    return ms.sector_frame(P.R, STYLE["frame_pad_km"])


def act_frames(P):
    """Per act: bbox of the act's example bands and their endpoint nodes + act_pad_km, widened to
    act_min_km and fitted to the SLIDE map panel's aspect (the cd.inset_frames method). Acts
    without examples fall back to the bbox of the act's edges' owned land."""
    if getattr(P, "_act_frames", None) is not None:
        return P._act_frames
    R = P.R
    T = ms.SLIDE; aspect = (T["map"][2] * T["size"][0]) / (T["map"][3] * T["size"][1])
    xs, ys = R.template.x.values, R.template.y.values
    out = {}
    for act in ACT_ORDER:
        exs = [x for x in P.examples if x["act"] == act]
        m = np.zeros(R.shape, bool)
        land = R.corridor if STYLE["protected_mode"] == "overlay" else P.corridor_unprotected
        for x in exs:
            m |= _example_mask(P, x) & land
            for lab in (R.edges.loc[x["edge_id"], "label_i"], R.edges.loc[x["edge_id"], "label_j"]):
                nid = _node_id_of_label(P, lab)
                if nid is not None and getattr(R, "node_id", None) is not None:
                    m |= (np.nan_to_num(R.node_id.values, nan=0) == nid)
        if not m.any():
            for k, a in P.acts.items():
                if a == act:
                    m |= (P.owner == P.order[k]) & R.corridor
        if not m.any():
            continue
        rr, cc_ = np.nonzero(m)
        x0, x1 = xs[cc_.min()], xs[cc_.max()]; y0, y1 = ys[rr.max()], ys[rr.min()]
        p = STYLE["act_pad_km"] * 1e3
        x0, x1, y0, y1 = x0 - p, x1 + p, y0 - p, y1 + p
        w, h = max(x1 - x0, STYLE["act_min_km"] * 1e3), max(y1 - y0, STYLE["act_min_km"] * 1e3 / aspect)
        if w / h < aspect:
            w = h * aspect
        else:
            h = w / aspect
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        out[act] = ((cx - w / 2, cx + w / 2), (cy - h / 2, cy + h / 2))
    P._act_frames = out
    return out


# ================= the shared layer stack =================
def _window(R, XL, YL):
    """Row/col slice of the template covering (XL, YL)."""
    xs, ys = R.template.x.values, R.template.y.values
    c0, c1 = int(np.clip(np.searchsorted(xs, XL[0]) - 1, 0, len(xs) - 1)), int(np.clip(np.searchsorted(xs, XL[1]) + 1, 1, len(xs)))
    r0, r1 = int(np.clip(np.searchsorted(-ys, -YL[1]) - 1, 0, len(ys) - 1)), int(np.clip(np.searchsorted(-ys, -YL[0]) + 1, 1, len(ys)))
    return slice(r0, r1), slice(c0, c1)


def _draw_mask(ax, R, mask, colour, z, alpha=1.0, XL=None, YL=None, step=1):
    """One flat fill from a boolean grid, cropped to the frame and decimated."""
    rs, cs = (_window(R, XL, YL) if XL is not None else (slice(None), slice(None)))
    sub = R.template.isel(y=rs, x=cs)
    arr = mask[rs, cs]
    if step > 1:
        sub = sub.isel(y=slice(None, None, step), x=slice(None, None, step)); arr = arr[::step, ::step]
    if not arr.any():
        return
    sub.copy(data=np.where(arr, 1.0, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap=ListedColormap([colour]), alpha=alpha, add_colorbar=False, zorder=z)
    ax.set_title(""); ax.set_xlabel(""); ax.set_ylabel("")


def _draw_outline(ax, R, mask, colour, z, XL, YL, lw=0.7):
    """Outline of a boolean grid's polygons (satisfied links: the outline names the satisfying layer)."""
    rs, cs = _window(R, XL, YL)
    sub = np.zeros(R.shape, bool); sub[rs, cs] = mask[rs, cs]
    if not sub.any():
        return
    polys = [_shape(g) for g, v in _shapes(sub.astype("uint8"), mask=sub, transform=R.template.rio.transform()) if v == 1]
    gpd.GeoSeries(polys, crs=R.crs).plot(ax=ax, facecolor="none", edgecolor=colour, linewidth=lw, zorder=z)


def _draw_near_contiguous(P, ax, XL, YL, step):
    """D25 on the contract maps: the near-contiguous links' bands in the neutral grey with the mapstyle hatch, UNDER the four
    corridor classes; the barrier variant outlined. Returns {class: n links}."""
    R = P.R; counts = {}
    rs, cs = _window(R, XL, YL)
    for c in NEAR_KEYS:
        ids = list(P.cls.index[P.cls == c])
        counts[c] = len(ids)
        if not ids:
            continue
        m = np.isin(P.owner, [P.order[k] for k in ids if k in P.order]) & R.corridor
        if not m[rs, cs].any():
            continue
        tok = NEAR_TOKENS[c]
        _draw_mask(ax, R, m, tok["fill"], ms.Z["securing"] - 0.2, 1.0, XL, YL, step)
        sub = R.template.isel(y=rs, x=cs); arr = m[rs, cs]
        if step > 1:
            sub = sub.isel(y=slice(None, None, step), x=slice(None, None, step)); arr = arr[::step, ::step]
        with plt.rc_context({"hatch.color": tok["hatch_color"], "hatch.linewidth": 0.5}):
            ax.contourf(sub.x.values, sub.y.values, arr.astype(float), levels=[0.5, 1.5], colors="none", hatches=[tok["hatch"]],
                        zorder=ms.Z["securing"] - 0.15)
        if tok["outline"]:
            ax.contour(sub.x.values, sub.y.values, arr.astype(float), levels=[0.5], colors=[tok["outline"][0]], linewidths=tok["outline"][1],
                       zorder=ms.Z["securing"] - 0.1)
    return counts


def _near_contiguous_legend(counts):
    rows = []
    for c in NEAR_KEYS:
        if not counts.get(c, 0):
            continue
        tok = NEAR_TOKENS[c]
        rows.append((Patch(facecolor=tok["fill"], hatch=tok["hatch"], edgecolor=(tok["outline"][0] if tok["outline"] else tok["hatch_color"]),
                           linewidth=(tok["outline"][1] if tok["outline"] else 0.0)), f"{tok['label']}  [{counts.get(c, 0)}]"))
    return rows


def _draw_common(P, ax, XL, YL, step, cost=False, classes=True, marginal=True, refugia=True, nodes=True, ns=None, chips=None):
    """The one layer stack every wolverine map and crop shares (spec 06w §3a.1.6):
    land -> [water under cost + cost] -> hillshade -> water -> refugia (marginal, core) ->
    PA outlines -> node outlines (+ chips) -> pressure classes -> boundaries."""
    R = P.R
    ms.draw_land(ax, R, XL, YL)
    if cost:
        ms.draw_water(ax, R, XL, YL, river_rank=STYLE["river_rank_full"], z=ms.Z["cost"] - 0.1)
        ms.draw_cost(ax, R, step=step)
    ms.draw_hillshade(ax, R, path=HILLSHADE, XL=XL, YL=YL, max_px=STYLE["hillshade_max_px"])
    ms.draw_water(ax, R, XL, YL, river_rank=STYLE["river_rank_act"] if step == 1 else STYLE["river_rank_full"])
    if refugia:
        if marginal:
            _draw_mask(ax, R, P.refugia == 1, ms.AREA["refugia_marginal"]["fill"], ms.Z["refugia_marginal"],
                       ms.AREA["refugia_marginal"]["alpha"], XL, YL, step)
        _draw_mask(ax, R, P.refugia == 2, ms.AREA["refugia_core"]["fill"], ms.Z["refugia_core"],
                   ms.AREA["refugia_core"]["alpha"], XL, YL, step)
    frame = _box(XL[0], YL[0], XL[1], YL[1])
    pas = P.pa_context[P.pa_context.intersects(frame)]
    ms.draw_outlines(ax, pas, "pa_outline")
    if len(P.ipca):
        ms.draw_outlines(ax, P.ipca[P.ipca.intersects(frame)], "ipca_outline")
    counts = {}
    if classes:
        overlay = STYLE["protected_mode"] == "overlay"
        land = R.corridor if overlay else P.corridor_unprotected
        if STYLE.get("draw_near_contiguous", True):
            counts.update(_draw_near_contiguous(P, ax, XL, YL, step))   # D25: under the corridor classes (v2.5: off, D-W6)
        for c in ms.CLASS_ORDER:
            ids = list(P.cls.index[P.cls == c])
            if c == "squeezed" and P.h8_open:
                ids = []
            if c == "securing" and P.h8_open:
                ids += list(P.cls.index[P.cls == "squeezed"])
            live = [k for k in ids if not bool(P.secured.get(k, False))]
            counts[c] = len(live)
            m = np.isin(P.owner, [P.order[k] for k in live if k in P.order]) & land
            _draw_mask(ax, R, m, ms.CLASS[c][0], ms.Z[c], 1.0, XL, YL, step)
            for by in ("pa", "ipca"):     # already connected within protected land: muted, same hue, outline says by which layer
                sat = [k for k in ids if P.secured_by.get(k, "") == by]
                counts.setdefault(f"satisfied_{by}", 0); counts[f"satisfied_{by}"] += len(sat)
                if overlay and sat:
                    ms_ = np.isin(P.owner, [P.order[k] for k in sat if k in P.order]) & land
                    _draw_mask(ax, R, ms_, ms.CLASS[c][0], ms.Z[c] - 0.01, STYLE["satisfied_alpha"], XL, YL, step)
                    _draw_outline(ax, R, ms_, STYLE["satisfied_outline"][by], ms.Z[c] + 0.05, XL, YL)
        if overlay:                       # protected land hatched over the bands (vector hatch: crisp at any scale)
            for by, gdf in (("pa", P.pa_all), ("ipca", P.ipca)):
                g = gdf[gdf.intersects(frame)]
                if len(g):
                    g.plot(ax=ax, facecolor="none", edgecolor=STYLE["protected_hatch_colour"][by], hatch=STYLE["protected_hatch"][by],
                           linewidth=STYLE["protected_hatch_lw"], zorder=ms.Z["both"] + 0.2)
    if nodes:
        nd = P.nodes[P.nodes.intersects(frame)]
        chips = STYLE["node_chips"] if chips is None else chips
        ms.draw_nodes(ax, nd, numbers=chips, ns=ns)
    ms.draw_boundaries(ax, R, XL, YL, sector=False)
    return counts


def _town_xy(R, name):
    lat, lon = dc.Y2Y_TOWNS[name]
    return pyproj.Transformer.from_crs("EPSG:4326", R.crs, always_xy=True).transform(lon, lat)


def _labels_full(P, ax, ns, n_names):
    """Jurisdictions (hand-placed), the largest nodes' names (greedy), towns (hand-placed)."""
    R = P.R
    to_map = pyproj.Transformer.from_crs("EPSG:4326", R.crs, always_xy=True)
    XL, YL = ax.get_xlim(), ax.get_ylim()
    for text, (lon, lat) in FULL_SPEC["jurisdictions"]:
        x, y = to_map.transform(lon, lat)
        if XL[0] <= x <= XL[1] and YL[0] <= y <= YL[1]:
            ms.label(ax, ns, text, (x, y), "jurisdiction")
    items = []
    for r in P.nodes.sort_values("area_km2", ascending=False).head(n_names).itertuples():
        g = r.geometry; big = max(g.geoms, key=lambda q: q.area) if hasattr(g, "geoms") else g
        pt = big.representative_point()
        items.append((r.short, (pt.x, pt.y), "area", 0, 9))
    ms.place_labels(ax, ns, items)
    for t, ha, dx, dy in FULL_SPEC["towns"]:
        if t in dc.Y2Y_TOWNS:
            x, y = _town_xy(R, t)
            if XL[0] <= x <= XL[1] and YL[0] <= y <= YL[1]:
                ms.town(ax, ns, t, (x, y), dx_pt=dx, dy_pt=dy, ha=ha)


def _node_key(P, ax):
    """Two-column node key in the TALL furniture column: '12  Banff'."""
    size = ms.TYPE["legend"][0] - 2.0
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    rows = P.nodes.sort_values("node_id")
    n = len(rows); per_col = int(np.ceil(n / 2))
    ax.text(0, 1.0, "Nodes (numbered north → south)", fontsize=size + 1.5, fontweight=600, color="#1A1A1A", ha="left", va="top")
    for i, r in enumerate(rows.itertuples()):
        col, row = divmod(i, per_col)
        y = 0.93 - row * (0.90 / per_col)
        ax.text(0.02 + 0.5 * col, y, f"{int(r.node_id):>2}  {str(r.short)[:22]}", fontsize=size, color=ms.TYPE["legend"][3],
                ha="left", va="top")                                   # the package font (Candara), not monospace (Ethan 2026-10-02)


def _qa_hexes():
    core = ms.AREA["refugia_core"]; marg = ms.AREA["refugia_marginal"]
    def blend(h, a):
        c = np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)]) / 255; land = np.array([int(ms.BASE["land"][i:i + 2], 16) for i in (1, 3, 5)]) / 255
        m = a * c + (1 - a) * land
        return "#%02X%02X%02X" % tuple(int(round(v * 255)) for v in m)
    return [blend(core["fill"], core["alpha"]), blend(marg["fill"], marg["alpha"]), ms.BASE["water"]]


def check_palette():
    """Item 4 of the QA on the wolverine colour set: the four class hues + the rendered refugia
    blends + water, and the three withheld-rule colours of W0c among themselves."""
    res = ms.cvd_separability([ms.CLASS[c][0] for c in ms.CLASS_ORDER] + _qa_hexes())
    res2 = ms.cvd_separability(list(STYLE["withheld_colours"].values()) + [ms.COST[1000][0], ms.BASE["water"]])
    for name, r in (("classes + refugia + water", res), ("W0c withheld rules", res2)):
        for sim, v in r.items():
            print(f"  {name:28s} {sim:12s} worst pair {v['worst_pair']} dE {v['dE']}  {'OK' if v['ok'] else 'FAIL'}")
    return res, res2


def _finish(P, fig, ns, fig_id, message, caption, run_tag=None, hexes=True):
    ms.caption(fig, ns, caption)
    paths = ms.export(fig, fig_id, run_tag or P.R.run_dir.name, P.fig)
    print(f"{fig_id}: exported " + ", ".join(p.name for p in paths) + f" | font {ms.font_in_use()}")
    P.qa[fig_id] = ms.qa(fig, ns, paths, message=message, expected_message=message, hexes=_qa_hexes() if hexes else None)
    plt.show()
    return fig


def _context_handles():
    y2y_line, adm = ms.line_handles()[1], ms.line_handles()[2]
    return [ms.area_handle("pa_outline"), y2y_line, adm]


def _node_handle():
    return (Patch(facecolor="none", edgecolor=ms.NODE["edge"], linewidth=ms.NODE["lw"]),
            f"Core refugia patch ≥ {int(config.CORRIDORS['wolverine']['nodes']['node_min_km2'])} km² (a node; numbered north → south)")


# ================= W0 -- refugia + nodes =================
def figure_w0(P, run_tag=None):
    ms.apply(); R = P.R
    fig, ns = ms.new_figure("Wolverine Climate Refugia: The Patches to Connect", "tall")
    ax = ns.map; XL, YL = full_frame(P)
    _draw_common(P, ax, XL, YL, STYLE["full_step"], classes=False, ns=ns)
    ms.set_frame(ax, XL, YL)
    _labels_full(P, ax, ns, STYLE["w0_names"])
    core_km2 = float((P.refugia == 2).sum()) * R.cell_km2; marg_km2 = float((P.refugia == 1).sum()) * R.cell_km2
    node_km2 = float(P.node_mask.sum()) * R.cell_km2
    ms.legend(ns.legend, [("Wolverine Refugia", [ms.area_handle("refugia_core"), ms.area_handle("refugia_marginal")]),
                          ("Nodes", [_node_handle()]),
                          ("Context", _context_rows(P))])
    _node_key(P, ns.key)
    fig.canvas.draw(); ms.scale_north(ns.scale, ax, fig, km=STYLE["scale_km_full"])
    cap = (f"Core refugia {core_km2:,.0f} km², marginal {marg_km2:,.0f} km²; {len(P.nodes)} core patches ≥ "
           f"{int(config.CORRIDORS['wolverine']['nodes']['node_min_km2'])} km² are the nodes ({node_km2:,.0f} km²). Existing "
           f"protected areas are context, not nodes. Basemap: Natural Earth, Copernicus GLO-90 hillshade.")
    return _finish(P, fig, ns, "W0", "where wolverine refugia are, and the patches the network connects", cap, run_tag)


# ================= W0b -- movement cost =================
def figure_w0b(P, run_tag=None):
    ms.apply(); R = P.R
    fig, ns = ms.new_figure("Wolverine Corridors: Movement Cost", "tall")
    ax = ns.map; XL, YL = full_frame(P)
    _draw_common(P, ax, XL, YL, STYLE["full_step"], cost=True, classes=False, refugia=False, ns=ns, chips=False)
    ms.set_frame(ax, XL, YL)
    _labels_full(P, ax, ns, 0)
    ms.legend(ns.legend, [("Cost Surface", ms.cost_handles()), ("Nodes", [_node_handle()]), ("Context", _context_rows(P))])
    _node_key(P, ns.key)
    fig.canvas.draw(); ms.scale_north(ns.scale, ax, fig, km=STYLE["scale_km_full"])
    cost = R.resistance.values; fin = cost[np.isfinite(cost) & (cost > 0)]
    sh = {int(c): 100 * float((fin == c).sum()) / fin.size for c in (1, 10, 100, 1000)}
    lab = R.cfg["resistance"].get("citation", "")
    cap = (f"{lab}, 300 m. Shares — intact land {sh[1]:.0f}%, roads and cuts {sh[10]:.0f}%, converted land {sh[100]:.1f}%, "
           f"water, settlement and retained barriers {sh[1000]:.0f}%. Basemap: Natural Earth, Copernicus GLO-90 hillshade.")
    return _finish(P, fig, ns, "W0b", "the cost sits in the valleys and the south", cap, run_tag, hexes=False)


# ================= W0c -- what the variant withheld =================
def _withheld_layers(P):
    """(published cost grid, {rule: bool grid}) from the run's variant provenance + grid.dir/variant_layers."""
    import rasterio
    R = P.R
    rv = R.rec["inputs"].get("resistance_variant")
    if not rv:
        return None, None, None
    meta = rv["meta"]
    with rasterio.open(meta["inputs"]["cost"]) as s:
        pub = s.read(1)
    gdir = config.PROJECT_DIR / pathlib.Path(R.cfg["grid"]["dir"]) / "variant_layers"
    lay = {}
    for rule, f in (("elevation_gt_2300_m", "elev_gt"), ("slope_gt_30_deg", "slope_gt"), ("glacier", "glacier")):
        p = gdir / f"{f}.tif"
        if p.exists() and rule in meta["withhold"]:
            with rasterio.open(p) as s:
                lay[rule] = s.read(1).astype(bool)
    return pub, lay, meta


def figure_w0c(P, run_tag=None):
    pub, lay, meta = _withheld_layers(P)
    if pub is None:
        print("W0c skipped: this run carries no variant surface"); return None
    ms.apply(); R = P.R
    fig, ns = ms.new_figure("Wolverine Corridors: Terrain Rules Withheld", "tall")
    ax = ns.map; XL, YL = full_frame(P)
    _draw_common(P, ax, XL, YL, STYLE["full_step"], classes=False, refugia=False, ns=ns, chips=False)
    var = np.nan_to_num(R.resistance.values, nan=-1)
    changed = (pub == 1000) & (var > 0) & (var < 1000)
    handles = []; done = np.zeros(R.shape, bool)
    for rule, col in STYLE["withheld_colours"].items():
        if rule not in lay:
            continue
        m = changed & lay[rule] & ~done; done |= m
        _draw_mask(ax, R, m, col, ms.Z["refugia_core"], 1.0, XL, YL, STYLE["full_step"])
        words = {"elevation_gt_2300_m": "Elevation > 2,300 m", "slope_gt_30_deg": "Slope > 30°", "glacier": "Glacier"}[rule]
        handles.append((Patch(facecolor=col), f"{words} → cost 1  ({m.sum() * R.cell_km2:,.0f} km²)"))
    kept = (pub == 1000) & (var == 1000) & np.any([lay[r] for r in lay], axis=0) if lay else np.zeros(R.shape, bool)
    _draw_mask(ax, R, kept, ms.COST[1000][0], ms.Z["refugia_core"] - 0.05, 1.0, XL, YL, STYLE["full_step"])
    handles.append((Patch(facecolor=ms.COST[1000][0]), f"Terrain kept at 1000 (lake, river, ocean or settled)  ({kept.sum() * R.cell_km2:,.0f} km²)"))
    ms.set_frame(ax, XL, YL)
    _labels_full(P, ax, ns, 0)
    ms.legend(ns.legend, [("Withheld Rules", handles), ("Nodes", [_node_handle()]), ("Context", _context_rows(P))])
    _node_key(P, ns.key)
    fig.canvas.draw(); ms.scale_north(ns.scale, ax, fig, km=STYLE["scale_km_full"])
    cap = (f"{meta['label']}: the source's generic-fauna terrain rules (Pither et al. 2023 S1 Table) are withheld and the "
           f"per-pixel maximum retaken; {meta['withheld_total_km2']:,} km² of cost 1000 falls to 1, every other layer keeps "
           f"its published cost. Human proxy τ = {meta['thresholds']['human_tau']:.2f} on the 90 m gHM.")
    return _finish(P, fig, ns, "W0c", "where the generic terrain rules were withheld", cap, run_tag, hexes=False)


# ================= W1 -- corridor pressure (the M1 analogue) =================
def _class_legend(counts):
    return [ms.class_handle(c, counts.get(c)) for c in ms.CLASS_ORDER if not (c == "squeezed" and counts.get(c, 0) == 0)]


def _protection_legend(P, counts):
    """The W11 rows: satisfied links (overlay mode) + the protected-land hatch / outlines."""
    rows = []
    n_pa, n_ip = counts.get("satisfied_pa", 0), counts.get("satisfied_ipca", 0)
    if STYLE["protected_mode"] == "overlay":
        rows.append((Patch(facecolor=ms.CLASS["securing"][0], alpha=STYLE["satisfied_alpha"], edgecolor=STYLE["satisfied_outline"]["pa"], linewidth=0.7),
                     f"Already connected within existing protected areas  [{n_pa}]"))
        rows.append((Patch(facecolor=ms.CLASS["securing"][0], alpha=STYLE["satisfied_alpha"], edgecolor=STYLE["satisfied_outline"]["ipca"], linewidth=0.7),
                     f"Already connected once the proposed conservation areas are realized  [{n_ip}]"))
        rows.append((Patch(facecolor="none", edgecolor=STYLE["protected_hatch_colour"]["pa"], hatch=STYLE["protected_hatch"]["pa"], linewidth=0.5),
                     "Existing protected areas"))
        rows.append((Patch(facecolor="none", edgecolor=STYLE["protected_hatch_colour"]["ipca"], hatch=STYLE["protected_hatch"]["ipca"], linewidth=0.5),
                     "Proposed conservation areas (taken as given)"))
    else:
        rows.append((Patch(facecolor="white", edgecolor=ms.AREA["pa_outline"]["edge"], linewidth=0.5),
                     f"Corridor land inside protected areas is not drawn; omitted links already connected: {n_pa} within existing PAs, "
                     f"{n_ip} once the proposed conservation areas are realized"))
    return rows


def _context_rows(P):
    rows = [ms.area_handle("pa_outline")]
    if len(P.ipca):
        rows.append(ms.area_handle("ipca_outline"))
    return rows + _context_handles()[1:]


def figure_w1(P, run_tag=None):
    ms.apply(); R = P.R
    fig, ns = ms.new_figure("Wolverine Corridors: Corridor Pressure", "tall")
    ax = ns.map; XL, YL = full_frame(P)
    counts = _draw_common(P, ax, XL, YL, STYLE["full_step"], marginal=STYLE["w1_marginal"], ns=ns)
    ms.set_frame(ax, XL, YL)
    for x in P.examples:                       # example chips in the class colour, at the median cell of the owned land
        xy = cd._median_cell(R, _example_mask(P, x))
        if xy:
            ms.number_chip(ax, ns, x["num"], xy, ms.CLASS[x["cls"]][0] if x["cls"] in ms.CLASS else ms.NODE["chip_ec"], fs=7.5)
    _labels_full(P, ax, ns, STYLE["w1_names"])
    ms.legend(ns.legend, [(ms.CLASS_HEADING, _class_legend(counts) + _near_contiguous_legend(counts)),
                          ("Protection Status", _protection_legend(P, counts)),
                          ("Wolverine Refugia", [ms.area_handle("refugia_core")] + ([ms.area_handle("refugia_marginal")] if STYLE["w1_marginal"] else [])),
                          ("Nodes And Examples", [_node_handle(), (Patch(facecolor="white", edgecolor=ms.CLASS["both"][0]), "Numbered example links (see the table)")]),
                          ("Context", _context_rows(P))])
    _node_key(P, ns.key)
    fig.canvas.draw(); ms.scale_north(ns.scale, ax, fig, km=STYLE["scale_km_full"])
    n_irr = int((P.cls == "both").sum() + (P.cls == "edge").sum())
    n_pa, n_ip = int((P.secured_by == "pa").sum()), int((P.secured_by == "ipca").sum())
    unp = float(P.corridor_unprotected.sum()) * R.cell_km2; tot = float(R.corridor.sum()) * R.cell_km2
    n_nc = int(P.cls.map(_is_near).sum())
    n_un = int(R.edges["width_not_assessable"].fillna(False).astype(bool).sum()) if "width_not_assessable" in R.edges.columns else 0
    cap = (f"Least-cost corridor bands between {len(P.nodes)} core refugia patches on the withheld-terrain surface (β = "
           f"{R.cfg.get('beta')}; the band admits routes within about {R.cutoff * R.cell_km:.1f} km of extra travel on open ground). "
           f"{len(P.edges)} links: {n_nc} join adjacent patches (no corridor to design), {n_un} too short for the width test and "
           f"classed on the alternative-link sense alone; {n_irr} corridor links with no affordable alternative; the top class also "
           f"requires the corridor to be below its barrier-free width. Already connected: {n_pa} within existing PAs, {n_ip} once the "
           f"proposed conservation areas are realized; {unp:,.0f} of {tot:,.0f} km² of corridor land lies outside PAs and proposed conservation areas. "
           + ("Squeezed class pending the counterfactual (H8 open). " if P.h8_open else "")
           + "Basemap: Natural Earth, Copernicus GLO-90 hillshade.")
    return _finish(P, fig, ns, "W1", "where the options are closing", cap, run_tag)


# ================= W2-W4 -- act crops =================
def _jurisdiction_points(P, XL, YL, max_labels=4):
    """Province / state code positions inside a window: the pole of inaccessibility of each
    admin polygon clipped to the window, largest first."""
    from shapely.ops import unary_union
    from shapely.algorithms.polylabel import polylabel
    R = P.R
    frame = _box(XL[0], YL[0], XL[1], YL[1])
    adm = ms._admin_polys().to_crs(R.crs)
    adm = adm[adm.intersects(frame)].copy()
    adm["clip"] = adm.geometry.intersection(frame)
    adm = adm[~adm["clip"].is_empty]
    adm["a"] = adm["clip"].area
    adm = adm[adm["a"] >= 0.04 * frame.area].sort_values("a", ascending=False).head(max_labels)
    out = []
    for r in adm.itertuples():
        g = r.clip
        big = max(g.geoms, key=lambda q: q.area) if hasattr(g, "geoms") else g
        try:
            pt = polylabel(big, tolerance=2000)
        except Exception:
            pt = big.representative_point()
        name = r.name_en if hasattr(r, "name_en") else r.name
        out.append((dc.PROVINCE_LABEL.get(name, str(name).upper()), (pt.x, pt.y)))
    return out


def figure_act(P, act, run_tag=None):
    ms.apply(); R = P.R
    spec = ACT_SPEC[act]
    frames = act_frames(P)
    if act not in frames:
        print(f"{spec['fig_id']} skipped: no corridor land in the {act} act"); return None
    XL, YL = frames[act]
    fig, ns = ms.new_figure(spec["title"], "slide", locator=True)
    ax = ns.map
    counts = _draw_common(P, ax, XL, YL, STYLE["act_step"], ns=ns)
    ms.set_frame(ax, XL, YL)
    exs = [x for x in P.examples if x["act"] == act]
    for x in exs:
        xy = cd._median_cell(R, _example_mask(P, x))
        if xy and XL[0] <= xy[0] <= XL[1] and YL[0] <= xy[1] <= YL[1]:
            ms.number_chip(ax, ns, x["num"], xy, ms.CLASS[x["cls"]][0] if x["cls"] in ms.CLASS else ms.NODE["chip_ec"], fs=8.5)
    spec_j = spec.get("jurisdictions")
    for text, xy in (spec_j if spec_j else _jurisdiction_points(P, XL, YL)):
        if spec_j:
            xy = pyproj.Transformer.from_crs("EPSG:4326", R.crs, always_xy=True).transform(*xy)
        ms.label(ax, ns, text, xy, "jurisdiction")
    frame = _box(XL[0], YL[0], XL[1], YL[1])
    # endpoint nodes of the window's examples first, then the largest other nodes in the window
    endpoint_ids = set()
    for x in exs:
        for lab in (R.edges.loc[x["edge_id"], "label_i"], R.edges.loc[x["edge_id"], "label_j"]):
            nid = _node_id_of_label(P, lab)
            if nid: endpoint_ids.add(nid)
    nd = P.nodes[P.nodes.intersects(frame)].copy()
    nd["pri"] = np.where(nd.node_id.isin(list(endpoint_ids)), 0, 1)
    nd = nd.sort_values(["pri", "area_km2"], ascending=[True, False]).head(STYLE["act_names"] + len(endpoint_ids))
    items = []
    for r in nd.itertuples():
        g = r.geometry.intersection(frame); big = max(g.geoms, key=lambda q: q.area) if hasattr(g, "geoms") else g
        if big.is_empty:
            continue
        pt = big.representative_point(); items.append((r.short, (pt.x, pt.y), "area", 0, 9))
    ms.place_labels(ax, ns, items)
    towns = []
    for t, (lat, lon) in dc.Y2Y_TOWNS.items():
        x, y = _town_xy(R, t)
        if XL[0] <= x <= XL[1] and YL[0] <= y <= YL[1]:
            towns.append((t, (x, y), "town", 5, 3))
    placed = ms.place_labels(ax, ns, towns[:STYLE["act_towns"]])
    for t in placed:
        ax.plot(*t.xy, marker="o", ms=2.5, color=ms.TYPE["town"][3], mec="white", mew=0.6, zorder=ms.Z["label_town"])
    ms.locator(ns.locator, R, window=(XL, YL))
    ms.legend(ns.legend, [(ms.CLASS_HEADING, _class_legend(counts) + _near_contiguous_legend(counts)),
                          ("Protection Status", _protection_legend(P, counts)),
                          ("Wolverine Refugia", [ms.area_handle("refugia_core"), ms.area_handle("refugia_marginal")]),
                          ("Nodes And Examples", [_node_handle(), (Patch(facecolor="white", edgecolor=ms.CLASS["both"][0]), "Numbered example links (see the table)")]),
                          ("Context", _context_rows(P))])
    fig.canvas.draw(); ms.scale_north(ns.scale, ax, fig, km=STYLE["scale_km_act"])
    ex_txt = "; ".join(f"{x['num']} = {x['title']} ({ms.CLASS[x['cls']][3] if x['cls'] in ms.CLASS else x['cls']})" for x in exs)
    cap = f"Examples: {ex_txt}. Same layers and classes as W1; window = the examples' land + {STYLE['act_pad_km']} km." if exs else "Same layers and classes as W1."
    return _finish(P, fig, ns, spec["fig_id"], spec["message"], cap, run_tag)


# ================= tables =================
def _endpoints_protected(P, r):
    ids = list(_complex_of_edge(P, r))
    f = []
    for nid in ids:
        row = P.nodes[P.nodes.node_id == nid]
        f.append(float(row.iloc[0].get("pa_overlap_frac", 0.0)) if len(row) and "pa_overlap_frac" in row.columns else 0.0)
    n = sum(v >= STYLE["endpoint_protected_frac"] for v in f)
    return {2: "both", 1: "one", 0: "neither"}[n]


def _link_rows(P, ids, nums=None):
    R, e = P.R, P.edges
    rows = []
    for eid in ids:
        r = e.loc[eid]; c = P.cls.get(eid, "securing")
        m = (P.owner == P.order[eid]) & R.corridor
        band = float(m.sum()) * R.cell_km2
        core = float((m & (P.refugia == 2)).sum()) * R.cell_km2; marg = float((m & (P.refugia == 1)).sum()) * R.cell_km2
        prot = float((m & P.pa_mask300).sum()) * R.cell_km2
        br = r.get("backup_ratio", np.nan)
        cpf = r.get("centreline_protected_frac", np.nan); cpa = r.get("centreline_pa_frac", np.nan); cpi = r.get("centreline_ipca_frac", np.nan)
        by = P.secured_by.get(eid, "")
        status = ("already connected within existing PAs" if by == "pa" else
                  "already connected once the proposed conservation areas are realized" if by == "ipca" else
                  ("partly protected" if pd.notna(cpf) and cpf > 0 else "unprotected"))
        geo = ("adjacent — barrier between" if c == "near_contiguous_barrier" else "adjacent — no corridor needed" if c == "near_contiguous"
               else ("width not assessable (too short)" if bool(r.get("width_not_assessable", False)) else "corridor link"))
        w10 = r.get("width_ratio_p10", np.nan); alt = r.get("alt_kind", "")
        rows.append({
            "#": (nums or {}).get(eid, ""),
            "Connects": " ↔ ".join(_short(P, c or 0) for c in _complex_of_edge(P, r)),
            "Pressure": ("Within one complex — corridor-class link, listed with the slivers, not mapped" if c == "intra_complex" else
                         (cc.LINK_CLASS_LABEL.get(c, c) if P.classified else (ms.CLASS[c][3] if c in ms.CLASS else c))),
            "Geometry": geo,
            "Alternative link is": (str(alt) if isinstance(alt, str) and alt else "—"),
            "Crossing class": (int(r["crossing_class"]) if pd.notna(r.get("crossing_class", np.nan)) else "—"),
            "Direct route": (r.get("crossing_note") if isinstance(r.get("crossing_note"), str) and r.get("crossing_note") else "all intact land"),
            "Narrowest tenth (p10 width ratio)": (f"{float(w10):.2f}" if pd.notna(w10) else "—"),
            "Protection status": status,
            "Route inside existing PAs (%)": (f"{100*cpa:.0f}" if pd.notna(cpa) else "—"),
            "Route inside proposed conservation areas only (%)": (f"{100*cpi:.0f}" if pd.notna(cpi) else "—"),
            "Corridor land to secure (km²)": round(float(bu) if pd.notna(bu := r.get("band_unprotected_km2", np.nan)) else band - prot),
            "Room to move (route branches)": (int(nb) if pd.notna(nb := r.get("n_branches", np.nan)) else "—"),   # D25: near-contiguous links have no decomposition
            "Cheapest alternative (× link cost)": ("none ≤ β" if pd.isna(br) or br is None else f"{float(br):.1f}×"),
            "Width vs natural": (f"{float(r['squeeze_ratio_obs']):.2f}" if "squeeze_ratio_obs" in e.columns and pd.notna(r.get("squeeze_ratio_obs")) and not P.h8_open else "pending"),
            "Corridor land (km²)": round(band),
            "Band: core / marginal / other (%)": (f"{100*core/band:.0f} / {100*marg/band:.0f} / {100*(band-core-marg)/band:.0f}" if band else "—"),
            "Band protected (%)": (f"{100*prot/band:.0f}" if band else "—"),
            "Endpoints protected": _endpoints_protected(P, r),
            "Jurisdictions": P.jur.get(eid, ""),
            "edge_id": eid, "act": P.acts.get(eid, ""),
        })
    return pd.DataFrame(rows)


def table_links(P, scope="examples"):
    """T1 (examples, numbered) / T2 (every flagged link not in the examples) / all."""
    if scope == "examples":
        ids = [x["edge_id"] for x in P.examples]; nums = {x["edge_id"]: x["num"] for x in P.examples}; fid, title = "T1_links", "Example links"
    elif scope == "flagged":
        ids = P.appendix_flagged; nums = None; fid, title = "T2_flagged_links", "Other links with no affordable alternative"
    elif scope == "satisfied":
        ids = list(P.edges.index[P.secured.reindex(P.edges.index).fillna(False)]); nums = None
        fid, title = "T4_satisfied_links", "Links already connected within protected land"
    else:
        ids = list(P.edges.index[P.cls != "adjacency"]); nums = None; fid, title = "T3_all_links", "All links"
    df = _link_rows(P, ids, nums)
    df.to_csv(P.tab / f"{fid}.csv", index=False, encoding="utf-8-sig")
    shown = df.drop(columns=["edge_id", "act"] + ([] if nums else ["#"]))
    if len(shown) and len(shown) <= 30:
        cd._table_png(shown, P.tab / f"{fid}.png", title)
    print(f"{fid}: {len(df)} rows -> {P.tab / (fid + '.csv')}")
    return df


def table_nodes(P):
    """T0 -- the node key: number, name, area, PA overlap, position."""
    cols = [c for c in ("node_id", "name", "area_km2", "pa_overlap_name", "pa_overlap_frac", "nearest_pa", "nearest_pa_km",
                        "bearing", "share_north_model", "lat", "lon") if c in P.nodes.columns]
    df = pd.DataFrame(P.nodes[cols]).sort_values("node_id")
    df.to_csv(P.tab / "T0_nodes.csv", index=False, encoding="utf-8-sig")
    print(f"T0_nodes: {len(df)} nodes -> {P.tab / 'T0_nodes.csv'}")
    return df


# ================= GIS export =================
def export_gis(P, out=None):
    """corridor_pressure.gpkg (per link, class attached), refugia.gpkg (core / marginal
    polygons), nodes.gpkg (numbered, named), examples.gpkg (numbered bands), style.json."""
    R = P.R
    out = pathlib.Path(out) if out else P.gis; out.mkdir(parents=True, exist_ok=True)
    pressure = cd._pressure_polygons(P)
    pressure["secured"] = [bool(P.secured.get(e, False)) for e in pressure.edge_id]
    pressure["secured_by"] = [P.secured_by.get(e, "") for e in pressure.edge_id]
    pressure.to_file(out / "corridor_pressure.gpkg", driver="GPKG")
    if P.protected is not None:                      # the corridor land still to secure, per link
        Pu = SimpleNamespace(**vars(P)); Pu.R = SimpleNamespace(**vars(R)); Pu.R.corridor = P.corridor_unprotected
        unp = cd._pressure_polygons(Pu)
        if len(unp):
            unp.to_file(out / "corridor_pressure_unprotected.gpkg", driver="GPKG")
    tr = R.template.rio.transform()
    rows = []
    for val, kind in ((2, "core"), (1, "marginal")):
        m = P.refugia == val
        polys = [_shape(g) for g, v in _shapes(m.astype("uint8"), mask=m, transform=tr) if v == 1]
        rows.append(dict(kind=kind, hex=ms.AREA[f"refugia_{kind}"]["fill"], km2=round(float(m.sum()) * R.cell_km2),
                         geometry=gpd.GeoSeries(polys, crs=R.crs).union_all()))
    gpd.GeoDataFrame(rows, crs=R.crs).to_file(out / "refugia.gpkg", driver="GPKG")
    nd = P.nodes[[c for c in ("node_id", "name", "short", "name_label", "area_km2", "pa_overlap_name", "pa_overlap_frac", "geometry") if c in P.nodes.columns]]
    nd.to_file(out / "nodes.gpkg", driver="GPKG")
    ex = []
    for x in P.examples:
        m = _example_mask(P, x)
        if not m.any():
            continue
        polys = [_shape(g) for g, v in _shapes(m.astype("uint8"), mask=m, transform=tr) if v == 1]
        ex.append(dict(num=x["num"], title=x["title"], pressure=x["cls"], hex=ms.CLASS[x["cls"]][0] if x["cls"] in ms.CLASS else "",
                       km2=round(float(m.sum()) * R.cell_km2, 1), geometry=gpd.GeoSeries(polys, crs=R.crs).union_all()))
    if ex:
        gpd.GeoDataFrame(ex, crs=R.crs).to_file(out / "examples.gpkg", driver="GPKG")
    style = dict(
        crs="ESRI:102008 (North America Albers Equal Area Conic); rasters 300 m",
        cost_surface=dict(raster=str(R.run_dir / "resistance.tif"), values="unique: 1, 10, 100, 1000 (nodata -1)",
                          swatches={str(c): dict(hex=ms.COST[c][0], label=ms.COST[c][1]) for c in (1, 10, 100, 1000)}),
        corridor_pressure=dict(vector=str(out / "corridor_pressure.gpkg"), field="pressure",
                               classes={c: dict(hex=ms.CLASS[c][0], label=ms.CLASS[c][3]) for c in ms.CLASS_ORDER}),
        refugia=dict(vector=str(out / "refugia.gpkg"), field="kind",
                     core=dict(hex=ms.AREA["refugia_core"]["fill"], opacity=ms.AREA["refugia_core"]["alpha"]),
                     marginal=dict(hex=ms.AREA["refugia_marginal"]["fill"], opacity=ms.AREA["refugia_marginal"]["alpha"]),
                     raster=str(config.PROJECT_DIR / R.rec["inputs"]["nodes_raster"]["warped"]["path"]) if R.rec["inputs"].get("nodes_raster") else None),
        nodes=dict(vector=str(out / "nodes.gpkg"), outline=ms.NODE["edge"], raster=str(R.run_dir / "node_id.tif")),
        protected_areas=dict(vector=str(config.PA_VECTOR), style="outline only", outline=ms.AREA["pa_outline"]["edge"], min_km2=STYLE["pa_min_km2"],
                             proposed=str((R.cfg.get("nodes", {}).get("protected") or {}).get("proposed", "")),
                             status_layer=dict(mode=STYLE["protected_mode"], hatch=STYLE["protected_hatch"],
                                               unprotected_pressure=str(out / "corridor_pressure_unprotected.gpkg"),
                                               unprotected_raster=str(R.run_dir / "corridors_unprotected.tif"))),
        examples=dict(vector=str(out / "examples.gpkg")),
        basemap=dict(land=ms.BASE["land"], ocean=ms.BASE["ocean"], water=ms.BASE["water"],
                     hillshade=str(HILLSHADE) + " (multiply, 18% opacity)",
                     admin_lines=str(ms.BASEMAP_DIR / "ne_10m_admin_1_states_provinces_lines.shp"),
                     y2y_boundary=str(config.CORRIDOR_REF)),
        fonts=f"{ms.font_in_use()} (system; DejaVu Sans fallback)", type=ms.TYPE,
    )
    (out / "style.json").write_text(json.dumps(style, indent=2, ensure_ascii=False))
    print(f"GIS export -> {out}: corridor_pressure.gpkg ({len(pressure)} links), refugia.gpkg, nodes.gpkg ({len(nd)}), "
          f"examples.gpkg ({len(ex)}), style.json")
    return out


def qa_report(P):
    """The §3a.3 checklist per figure -> tables/qa_checklist.csv; prints any FAIL."""
    rows = []
    for fid, res in P.qa.items():
        for item, (ok, detail) in res.items():
            rows.append(dict(figure=fid, item=item, ok=bool(ok), detail=str(detail)[:300] if not ok else ""))
    df = pd.DataFrame(rows)
    if len(df):
        df.to_csv(P.tab / "qa_checklist.csv", index=False, encoding="utf-8-sig")
        bad = df[~df.ok]
        print(f"QA: {len(df)} checks over {df.figure.nunique()} figures; {len(bad)} FAIL" + (":" if len(bad) else ""))
        for r in bad.itertuples():
            print(f"  FAIL {r.figure}: {r.item} — {r.detail}")
    return df


# ================= 06_director_outputs (05 until 2026-09-28): the curated maps on the y2y Act 1 WIDE layout ================
# Mirrors the northern 07 (corridors_director.director_frame / figure_cost_wide / figure_choices_wide, spec 06 v1.2.17,
# M5.21): layout, typography, basemap, insets, ramp + legend placement = `director_plot.wide_map` (ONE codebase with the y2y
# and northern packages); colours and words = `corridors_mapstyle` (ONE source). Differences here: the frame is the WHOLE
# Y2Y (drawn at 600 m -- the frame panel is ~2.9 in for 1,286 km, so one 300 dpi pixel is ~1.5 km and the 300 m grid gains
# nothing), the layout's grey layer is the existing PAs (context), the overlay in the IPCA role is the REFUGIA NODES (filled
# in the §3a core tone, outlined, named in the insets), and the proposed conservation areas are a second fill drawn OVER the corridor land
# -- so corridor land inside PAs / IPCAs reads as already satisfied by the overlay (Ethan 2026-09-28, W11 overlay mode).
WIDE_STYLE = dict(
    map_layout="wide", inset_clusters=(1, 2), inset_windows=None,
    inset_codes={"A": dict(inside=["YT", "NT"], force=["YT", "NT"]),        # Ethan 2026-09-29: YT + NWT on their parts inside the region (the window is all Y2Y land)
                 "B": dict(inside=["MT"], at={"ID": (-113.05, 44.80)})},   # Ethan 2026-09-29: MT inside the corridor (the Y2Y line reads as a state line), ID south-east of Salmon, clear of the scale bar
    inset_town_skip={}, main_skip_codes=("CA",),                          # the y2y frame's own skips; inset windows are ours
    wide_main_towns=(), wide_main_names="abbrev",                          # the frame panel: postal codes only, no towns
    pa_layer_min_km2=300, inset_pa_names=4, window_scale_km=250,           # named PAs in the insets; a 250 km bar on the Y2Y frame
    hillshade=True, water=True, titles=False, export_dpi=300, export_pdf=False,   # PNG only (Ethan 2026-10-01: no PDF twin)
    option_lw=0.8, option_halo=0.8,                # route-option outlines (04 + the 05b locators), pt on the frame (Ethan 2026-10-01: thinner, with the north)
    conseq_rep_mark="",                            # 06: row headers as before (no † on Representativeness; with the north, Ethan 2026-10-01)
    wide_legend_between=True, wide_legend_fit=True, wide_legend_fs_min=9,   # Ethan 2026-09-29: the legend box centred between inset B's bottom and the page bottom, its
                                                                             # items shrunk (font units) until the box fits the gap
    pa_alpha=0.85,                                                           # the layout's PA grey at 85% (the northern maps' value); inert here -- every frame is built without the PA layer
    north_arrow_beside_bar=True,                                             # the frame's north arrow to the right of the 250 km bar, not floating above it (chat 2026-09-29)
)
WIDE_FRAME_STEP = 2            # 300 m grid -> 600 m frame for the wide layout (memory: 47 M -> 12 M cells)
WIDE_INSET_KM = 350            # inset windows floor (each side), before the aspect fit
NODE_WIDE_LABEL = "Core wolverine refugia (the nodes)"
WIDE_TOWNS = {**dc.Y2Y_TOWNS, "Fort Liard": (60.24, -123.47), "Nahanni Butte": (61.03, -123.38),   # added for inset A (Ethan 2026-09-29) -- both fell off its east
              "Lower Post": (59.92, -128.49)}                                                       # edge after the window moved; Lower Post (Ethan's pick) sits on its west edge
IPCA_WIDE_LABEL = "Proposed conservation areas"
PA_WIDE_LABEL = "Existing protected areas"


def _reduce(a, step, how=None):
    """300 m -> the frame grid. STYLE["frame_reduce"]: "any" (Ethan 2026-09-29) = a frame cell is drawn if ANY 300 m cell in its
    step x step block is, so a band that is continuous at 300 m stays continuous at 600 m (striding dropped one-cell necks at
    road crossings and drew beads with gaps); "stride" = every step-th cell, the old sampling. Float images (NaN = nothing) take the
    block's nanmax, so at a boundary between two classes the higher index wins -- one 300 m cell at most; bool masks take any."""
    import warnings
    how = how or STYLE.get("frame_reduce", "any")
    a = np.asarray(a); s_ = int(step)
    if s_ == 1 or how == "stride":
        return a[::s_, ::s_]
    H, W = a.shape; Hp, Wp = -(-H // s_) * s_, -(-W // s_) * s_
    if a.dtype == bool:
        q = np.zeros((Hp, Wp), bool); q[:H, :W] = a
        return q.reshape(Hp // s_, s_, Wp // s_, s_).any(axis=(1, 3))
    q = np.full((Hp, Wp), np.nan, np.float32); q[:H, :W] = a
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)                        # all-NaN blocks are NaN, as they should be
        return np.nanmax(q.reshape(Hp // s_, s_, Wp // s_, s_), axis=(1, 3))


def director_frame(P, pad_km=None, step=WIDE_FRAME_STEP, pa=None, names=None):
    """The wolverine run as a director_plot frame (cached on P): G on the routing grid decimated by `step` (pu = routable
    cells, locked2d = the EXISTING PAs as the layout's grey layer), the refugia nodes as the overlay in the IPCA role (their
    short names label the insets), the Y2Y frame + pad as the pixel WINDOW, the y2y town table."""
    pa = bool(STYLE.get("protected_layers", True)) if pa is None else bool(pa)
    names = pa if names is None else bool(names)                               # PA names in the insets (06 · 04 draws the grey without them)
    key = (step, pa, names)
    if getattr(P, "_frames", None) and key in P._frames:
        return P._frames[key]
    import director_plot as dp
    from affine import Affine
    R = P.R
    s = int(step)
    cost = R.resistance.values
    pu = _reduce(np.isfinite(cost) & (cost > 0), s)
    pa2d = _reduce(np.asarray(R.protected_pa if getattr(R, "protected_pa", None) is not None else P.pa_mask300, bool), s) & pu
    if not pa:                                                                  # 06 · 01 (Ethan 2026-09-29): no protected-area layer
        pa2d = np.zeros_like(pa2d)
    tr = R.transform
    tr2 = Affine(tr.a * s, tr.b, tr.c, tr.d, tr.e * s, tr.f)
    G = SimpleNamespace(pu=pu, locked2d=pa2d, locked=pa2d[pu], disc=pu & ~pa2d, n_pu=int(pu.sum()), n_disc=int((pu & ~pa2d).sum()),
                        shape=pu.shape, transform=tr2, crs=pyproj.CRS.from_wkt(R.crs.to_wkt()), profile=None, cell_km2=R.cell_km2 * s * s)
    G.rows, G.cols = np.where(pu)
    nodes = P.nodes[["node_id", "name", "short", "geometry"]].copy()
    nodes["name"] = nodes["short"]                                          # the inset labels (director_plot reads gdf["name"])
    if getattr(P, "contracted", False) and STYLE.get("inset_label_slivers", True) and "n_fronts" in P.nodes.columns and getattr(R, "fronts", None) is not None:
        nodes["name"] = [(f"{sh} [{int(a)}/{int(b)}]" if sh else "") for sh, a, b in zip(P.nodes["short"], P.nodes["n_fronts"], P.nodes["n_cut"])]   # [fronts / cut]
    elif getattr(P, "contracted", False) and STYLE.get("inset_label_slivers", True) and "n_slivers" in P.nodes.columns:
        nodes["name"] = [(f"{sh} [{int(a)}]" if sh else "") for sh, a in zip(P.nodes["short"], P.nodes["n_slivers"])]      # [within-complex slivers]
    overlay = SimpleNamespace(gdf=nodes, mask2d=_reduce(np.asarray(P.node_mask, bool), s), label=NODE_WIDE_LABEL)
    (x0, x1), (y0, y1) = ms.sector_frame(R, STYLE["frame_pad_km"] if pad_km is None else pad_km)
    px0, pyb = dc.xy_to_px(G, x0, y0); px1, pyt = dc.xy_to_px(G, x1, y1)
    F = dp.load_frame(G, overlay=overlay, window=(float(px0), float(px1), float(pyt), float(pyb)), towns=WIDE_TOWNS,
                      pa_min_km2=(None if names else 1e15))                 # no PA layer / names off -> no named PAs in the insets / locators either
    F.STEP = s
    F.IPCA2D = (P.protected_ipca if getattr(P, "protected_ipca", None) is not None else
                (getattr(R, "protected_ipca", None) if getattr(R, "protected_ipca", None) is not None else np.zeros(R.shape, bool)))
    F.IPCA2D = _reduce(np.asarray(F.IPCA2D, bool), s) & pu
    F.IPCA_GDF = P.ipca
    F.PICKS, F.CL = None, {}
    if getattr(P, "_frames", None) is None:
        P._frames = {}
    P._frames[key] = F
    P._frame, P._frame_step = F, s                                              # the default (pa=True) stays the cached frame other assets read
    return F


def _near_contiguous_wide(P, F):
    """D25 on the wide layout: (draw, handles) for the near-contiguous links -- bands in the neutral grey with the mapstyle
    hatch (contourf in pixel space on the decimated frame), the barrier variant outlined; nothing when the run has none."""
    R = P.R; s = F.STEP; layers = []
    for c in NEAR_KEYS:
        ids = list(P.cls.index[P.cls == c])
        if not ids:
            continue
        m = _reduce(np.isin(P.owner, [P.order[k] for k in ids if k in P.order]) & R.corridor, s)
        if m.any():
            layers.append((c, m, len(ids)))
    if not layers:
        return (lambda ax: None), []

    def draw(ax):
        for c, m, _ in layers:
            tok = NEAR_TOKENS[c]
            ax.imshow(np.where(m, 1.0, np.nan).astype(np.float32), cmap=ListedColormap([tok["fill"]]), interpolation="nearest", zorder=0.85)
            with plt.rc_context({"hatch.color": tok["hatch_color"], "hatch.linewidth": 0.5}):
                ax.contourf(m.astype(float), levels=[0.5, 1.5], colors="none", hatches=[tok["hatch"]], zorder=0.86)
            if tok["outline"]:
                ax.contour(m.astype(float), levels=[0.5], colors=[tok["outline"][0]], linewidths=tok["outline"][1], zorder=0.87)
    handles = [Patch(facecolor=NEAR_TOKENS[c]["fill"], hatch=NEAR_TOKENS[c]["hatch"],
                     edgecolor=(NEAR_TOKENS[c]["outline"][0] if NEAR_TOKENS[c]["outline"] else NEAR_TOKENS[c]["hatch_color"]),
                     linewidth=(NEAR_TOKENS[c]["outline"][1] if NEAR_TOKENS[c]["outline"] else 0.0),
                     label=NEAR_TOKENS[c]["label"]) for c, _, _ in layers]
    return draw, handles


def _boundary_handles():
    """Legend rows for the two boundary lines the wide layout draws (director_core.BASEMAP): the Y2Y region and the province /
    state boundaries -- so neither reads as the other (Ethan 2026-09-29). STYLE["boundary_legend"] switches them off."""
    if not STYLE.get("boundary_legend", True):
        return []
    y2y = dc.BASEMAP["y2y"]; adm = dc.BASEMAP["admin"]
    return [Line2D([], [], color=y2y[0], lw=y2y[1] * 1.6, ls=(0, y2y[2]), label="Y2Y region"),
            Line2D([], [], color=adm[0], lw=adm[1] * 1.6, ls=(0, adm[2]), label="Province / state boundary")]


def _base_overlay(F, P):
    """The overlay every wide map starts from: the W11 layers (PAs grey, IPCAs filled, nodes) when STYLE["protected_layers"], else
    ONLY the core refugia in the 01 scheme (lime fill, thin outline) -- Ethan 2026-09-29: the protection analysis is a separate product."""
    return _wide_overlay(F, P) if STYLE.get("protected_layers", True) else _cost_overlay(F, P)


def _wide_overlay(F, P=None):
    """The overlay callback for the wide layout: the near-contiguous bands first (D25, with `P`), then the refugia nodes filled
    in the §3a core tone (opaque, like the layout's PA grey, so the two kinds read alike) + outlined, and the proposed conservation areas
    filled in the §3a IPCA tone OVER the corridor land (already satisfied) + dashed outlines. Called on the frame and on every inset."""
    import director_plot as dp
    core, ip = ms.AREA["refugia_core"], ms.AREA["ipca"]
    fill_n = np.full(F.G.shape, np.nan, np.float32); fill_n[F.IP.mask2d] = 1.0
    fill_i = np.full(F.G.shape, np.nan, np.float32); fill_i[F.IPCA2D] = 1.0
    nc_draw, nc_handles = _near_contiguous_wide(P, F) if (P is not None and STYLE.get("draw_near_contiguous", True)) else ((lambda ax: None), [])

    def draw(ax):
        nc_draw(ax)
        ax.imshow(fill_i, cmap=ListedColormap([ip["fill"]]), alpha=0.85, interpolation="nearest", zorder=1.05)
        ax.imshow(fill_n, cmap=ListedColormap([core["fill"]]), interpolation="nearest", zorder=1.1)
        lw = 0.9 * dp.STYLE.get("_lw_scale", 1.0)
        for _, r in F.IPCA_GDF.iterrows():
            for ring in F.rings_px(r.geometry):
                ax.plot(ring[:, 0], ring[:, 1], color=ip["edge"], lw=lw, ls=(0, (3, 2)), zorder=3.4)
        for _, r in F.IP.gdf.iterrows():
            for ring in F.rings_px(r.geometry):
                ax.plot(ring[:, 0], ring[:, 1], color=ms.NODE["edge"], lw=lw, zorder=3.5)
    handles = [Patch(facecolor=dp.PA_COLOR, label=PA_WIDE_LABEL),
               Patch(facecolor=ip["fill"], alpha=0.85, edgecolor=ip["edge"], label=IPCA_WIDE_LABEL),
               Patch(facecolor=core["fill"], edgecolor=ms.NODE["edge"], label=NODE_WIDE_LABEL)] + nc_handles
    return draw, handles


def inset_windows(P, mode="examples", same_scale=True):
    """Pixel windows (on the wide frame) for insets A and B. "examples": the northernmost and the southernmost example
    links (their corridor land + endpoint nodes + act_pad_km, floored at WIDE_INSET_KM); "clusters": the two densest node
    clusters (the check-stop-1 rule). Both windows take the larger width and height (one map scale, as in the north)."""
    F = director_frame(P)
    R = P.R
    xs, ys = R.template.x.values, R.template.y.values

    def _win_from_mask(m):
        rr, cc_ = np.nonzero(m)
        if not len(rr):
            return None
        p = STYLE["act_pad_km"] * 1e3
        x0, x1 = xs[cc_.min()] - p, xs[cc_.max()] + p; y0, y1 = ys[rr.max()] - p, ys[rr.min()] + p
        w, h = max(x1 - x0, WIDE_INSET_KM * 1e3), max(y1 - y0, WIDE_INSET_KM * 1e3)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        px0, pyb = dc.xy_to_px(F.G, cx - w / 2, cy - h / 2); px1, pyt = dc.xy_to_px(F.G, cx + w / 2, cy + h / 2)
        return (float(px0), float(px1), float(pyt), float(pyb))

    def _land(x):
        m = _example_mask(P, x)
        contracted = getattr(R, "contracted", False) and getattr(R, "complex_id", None) is not None
        grid = R.complex_id if contracted else getattr(R, "node_id", None)
        m2c = None
        if contracted:                                      # v2.5: the edge labels still carry PATCH ids; map them to complexes
            m2c = R.node_table.set_index("node_id")["complex_id"] if "complex_id" in getattr(R, "node_table", pd.DataFrame()).columns else None
        for lab in (R.edges.loc[x["edge_id"], "label_i"], R.edges.loc[x["edge_id"], "label_j"]):
            nid = _node_id_of_label(P, lab)
            if nid is not None and m2c is not None and str(lab).split(" · ", 1)[-1].startswith("R"):
                nid = int(m2c.get(nid, nid))
            if nid is not None and grid is not None:
                m = m | (np.nan_to_num(grid.values, nan=0) == nid)
        return m

    def _extent_km(m):
        rr, cc_ = np.nonzero(m)
        return max(np.ptp(rr), np.ptp(cc_)) * R.cell_km if len(rr) else 0.0

    out = {}
    if mode == "fixed":                                                  # the northern scale, fixed centres (STYLE["inset_specs"])
        w0, h0 = STYLE["inset_km"]
        to_xy = pyproj.Transformer.from_crs("EPSG:4326", R.crs, always_xy=True)
        cl = getattr(R, "centrelines", None)
        centres, sizes = {}, {}
        for tag, spec in STYLE["inset_specs"].items():
            cx = cy = None; w_km, h_km = w0, h0
            if spec.get("links_between") and cl is not None:
                cid = lambda lab: cc._label_num(lab)
                pairs = {tuple(sorted(pr)) for pr in spec["links_between"]}
                hit = [k for k, a, b in zip(cl["edge_id"], cl["label_i"], cl["label_j"]) if tuple(sorted((cid(a), cid(b)))) in pairs]
                if hit:
                    m = np.isin(P.owner, [P.order[k] for k in hit if k in P.order]) & R.corridor      # the links' full corridor land
                    rr, cc_ = np.nonzero(m)
                    if len(rr):
                        x0, x1 = xs[cc_.min()], xs[cc_.max()]; y0, y1 = ys[rr.max()], ys[rr.min()]
                    else:
                        b = cl.set_index("edge_id").loc[hit].total_bounds; x0, y0, x1, y1 = b
                    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                    if spec.get("fit"):                                            # size the window to the links + pad, never below the floor
                        pad = float(spec.get("pad_km", 30)) * 1e3
                        w_km = max(w0, (x1 - x0 + 2 * pad) / 1e3); h_km = max(h0, (y1 - y0 + 2 * pad) / 1e3)
                else:                                                    # no such link in this run: the complexes themselves
                    ids = sorted({c for pr in spec["links_between"] for c in pr})
                    g = P.nodes[P.nodes.node_id.isin(ids)]
                    if len(g):
                        b = g.total_bounds; cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            if cx is None and spec.get("towns"):
                pts = [to_xy.transform(dc.Y2Y_TOWNS[t][1], dc.Y2Y_TOWNS[t][0]) for t in spec["towns"] if t in dc.Y2Y_TOWNS]
                cx, cy = float(np.mean([q[0] for q in pts])), float(np.mean([q[1] for q in pts]))
            if cx is None and spec.get("center_lonlat"):
                cx, cy = to_xy.transform(*spec["center_lonlat"])
            if cx is None:
                continue
            centres[tag] = (cx, cy); sizes[tag] = (w_km, h_km)
        w_km = max(w for w, _ in sizes.values()); h_km = max(h for _, h in sizes.values())      # A and B at ONE size (the larger)
        for tag, (cx, cy) in centres.items():
            px0, pyb = dc.xy_to_px(F.G, cx - w_km * 500, cy - h_km * 500); px1, pyt = dc.xy_to_px(F.G, cx + w_km * 500, cy + h_km * 500)
            out[tag] = (float(px0), float(px1), float(pyt), float(pyb))
        print(f"  insets (fixed): {w_km:.0f} x {h_km:.0f} km each" + (" (A fitted to its links)" if any(sp.get('fit') for sp in STYLE['inset_specs'].values()) else ""))
        return out
    if mode == "examples" and len(P.examples) >= 1:
        ordered = sorted(P.examples, key=lambda x: x["num"])          # 1..k, north -> south
        half = max(1, (len(ordered) + 1) // 2)
        groups = [ordered[:half], ordered[half:]] if len(ordered) > 1 else [ordered]
        for tag, grp in zip("AB", groups):
            if not grp:
                continue
            m = np.zeros(R.shape, bool)
            for x in grp:
                m |= _land(x)
            if len(grp) > 1 and _extent_km(m) > STYLE["inset_max_km"]:     # the pair does not fit one window: the first alone
                m = _land(grp[0])
            w = _win_from_mask(m)
            if w:
                out[tag] = w
    if len(out) < 2:                                                     # clusters fallback (or mode == "clusters")
        pts = P.nodes.geometry.representative_point(); xy = np.c_[pts.x.values, pts.y.values]
        remaining = np.ones(len(xy), bool); out = {}
        for tag in "AB":
            if not remaining.any():
                break
            best, cnt = None, -1
            for i in np.flatnonzero(remaining):
                c = int(((np.abs(xy[:, 0] - xy[i, 0]) < WIDE_INSET_KM * 500) & (np.abs(xy[:, 1] - xy[i, 1]) < WIDE_INSET_KM * 500) & remaining).sum())
                if c > cnt:
                    best, cnt = i, c
            cx, cy = xy[best]; w = WIDE_INSET_KM * 1e3
            remaining &= ~((np.abs(xy[:, 0] - cx) < w / 2) & (np.abs(xy[:, 1] - cy) < w / 2))
            px0, pyb = dc.xy_to_px(F.G, cx - w / 2, cy - w / 2); px1, pyt = dc.xy_to_px(F.G, cx + w / 2, cy + w / 2)
            out[tag] = (float(px0), float(px1), float(pyt), float(pyb))
    return cd._same_scale(out) if same_scale else out


def cost_surface(P):
    """The movement-cost classes for the ramp slot (corridors_director.cost_surface: the §3a magma swatches), with the 1,000 class
    SPLIT for the reader (chat 2026-09-29): open water (lakes >= 10 ha, rivers > 28 m³/s, ocean -- the retained water layers of the
    variant derivation, `variant_layers/`) in STYLE["cost_water_fill"], settlement and the other retained barriers in the magma dark;
    both ticks read 1,000 -- the cost is unchanged, only the reading. STYLE["cost_split_water"]=False restores the four swatches.
    Tick words from STYLE["cost_tick_words"] over corridors_director.COST_TICK_WORDS (no jargon: "forestry cutblocks", "farmland")."""
    from matplotlib.colors import BoundaryNorm
    S_, shares = cd.cost_surface(P)
    words = dict(cd.COST_TICK_WORDS); words.update(STYLE.get("cost_tick_words", {}))
    S_ = dict(S_)
    wm = _water_mask(P) if STYLE.get("cost_split_water", True) else None
    if wm is not None:
        cost = P.R.resistance.values
        img = np.full(cost.shape, np.nan, np.float32)
        for k, c in enumerate((1, 10, 100)):
            img[cost == c] = k
        img[(cost == 1000) & wm] = 3; img[(cost == 1000) & ~wm] = 4
        fin = np.isfinite(cost) & (cost > 0); n_fin = float(fin.sum())
        shares = {**{c: shares[c] for c in (1, 10, 100)}, "1000 water": 100 * float(((cost == 1000) & wm).sum()) / n_fin,
                  "1000 settlement": 100 * float(((cost == 1000) & ~wm).sum()) / n_fin}
        cols = [ms.COST[1][0], ms.COST[10][0], ms.COST[100][0], STYLE["cost_water_fill"], ms.COST[1000][0]]
        S_.update(img=img, cmap=ListedColormap(cols), norm=BoundaryNorm(np.arange(-0.5, 5.5, 1), 5), ticks=list(range(5)),
                  ticklabels=[f"1\n{words[1]}", f"10\n{words[10]}", f"100\n{words[100]}", f"1,000\n{STYLE['cost_water_word']}", f"1,000\n{STYLE['cost_settlement_word']}"])
    else:
        if STYLE.get("cost_split_water", True):
            print("  cost surface: water layers not found -- the 1,000 class is drawn as one swatch")
        S_["ticklabels"] = [f"{c}\n{words[c]}" for c in cd.COST_CLASSES]
    a = STYLE.get("cost_surface_alpha")                                         # None = follow the corridor surface's alpha (Ethan 2026-09-29: boundaries show through)
    S_["alpha"] = float(STYLE.get("surface_alpha", 1.0) if a is None else a)
    return S_, shares


def _water_mask(P):
    """Open water on the routing grid = the variant derivation's retained water layers (lake | river | ocean in `variant_layers/`
    under the run's grid dir); cached on P; None when the files are missing."""
    if getattr(P, "_water_mask", None) is not None:
        return P._water_mask
    import rasterio
    cfg = getattr(P.R, "cfg", None)
    gd = cfg.get("grid", {}).get("dir") if isinstance(cfg, dict) else None
    cands = ([pathlib.Path(gd) / "variant_layers"] if gd else []) + [config.INPUT_DIR / "corridors_300m_y2y" / "variant_layers"]
    vl = next((c for c in cands if all((c / f).exists() for f in ("lake.tif", "river.tif", "ocean.tif"))), None)
    if vl is None:
        return None
    m = np.zeros(P.R.shape, bool)
    for f in ("lake.tif", "river.tif", "ocean.tif"):
        with rasterio.open(vl / f) as r:
            a = r.read(1)
            assert a.shape == tuple(P.R.shape), f"{f}: {a.shape} vs the routing grid {P.R.shape}"
            m |= a > 0
    P._water_mask = m
    return m

def classes_surface(P):
    """The corridor-pressure classes for the ramp slot (corridors_director.classes_surface: the §3a pressure levels and
    words, H8 folding). In W11 "unprotected_only" mode the surface is cut to the corridor land still to secure."""
    S_, counts = cd.classes_surface(P)
    if STYLE["protected_mode"] == "unprotected_only" and P.protected is not None:
        S_["img"] = np.where(P.corridor_unprotected, S_["img"], np.nan).astype(np.float32)
    S_["alpha"] = float(STYLE.get("surface_alpha", 1.0))       # the wide layout draws the surface + its key at this alpha (director_plot, 2026-09-29)
    return S_, counts


def _wide(P, path, surface, insets):
    import director_plot as dp
    F = director_frame(P)
    assert dp.STYLE.get("map_layout") == "wide" and dp.STYLE.get("inset_clusters"), "apply dp.STYLE.update(wd.WIDE_STYLE) first (05's setup cell)"
    dp.STYLE["inset_windows"] = inset_windows(P, insets)
    S_ = dict(surface); S_["img"] = _reduce(surface["img"], F.STEP)                    # the frame's reduction (block any / nanmax)
    draw, handles = _base_overlay(F, P)
    handles = handles + _boundary_handles()
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    log = dict(flipped=0, hidden=0)

    def post(ax, win):                                                         # no text overlaps (Ethan 2026-09-29): town labels flipped clear of the codes
        f, h = _declutter_texts(ax); log["flipped"] += f; log["hidden"] += h
    dp.wide_map(F, path, "", draw, handles, with_ipca_names=(STYLE.get("complex_labels", "none") != "none"), surface=S_, post_draw=post)
    if log["flipped"] or log["hidden"]:
        print(f"town labels flipped {log['flipped']}, hidden {log['hidden']}")
    _legend_note()
    return path


def _legend_note():
    """Print the legend font the fit settled on (director_plot's wide_legend_fit), for the record."""
    import director_plot as dp
    fs = dp.STYLE.pop("_wide_legend_fs_used", None)
    if fs is not None:
        print(f"legend: {len(dp.STYLE.get('inset_clusters', ()))} insets · items at {fs:g} pt (fit to the gap under inset B; configured {dp.STYLE['wide_legend_fs']} pt)")


def _cost_overlay(F, P):
    """06 · 01's overlay: ONLY the core refugia (the complexes' land), filled in STYLE["cost_map_refugia_fill"] with a thin outline.
    No PA fill, no IPCA fill or outline (Ethan 2026-09-29: too busy). Returns (draw, handles)."""
    import director_plot as dp
    fill = STYLE["cost_map_refugia_fill"]; ec, lw0 = STYLE["cost_map_outline"]
    fill_n = np.full(F.G.shape, np.nan, np.float32); fill_n[F.IP.mask2d] = 1.0

    def draw(ax):
        ax.imshow(fill_n, cmap=ListedColormap([fill]), alpha=STYLE["cost_map_refugia_alpha"], interpolation="nearest", zorder=1.1)
        lw = lw0 * dp.STYLE.get("_lw_scale", 1.0)
        for _, r in F.IP.gdf.iterrows():
            for ring in F.rings_px(r.geometry):
                ax.plot(ring[:, 0], ring[:, 1], color=ec, lw=lw, zorder=3.5)
    handles = [Patch(facecolor=fill, alpha=STYLE["cost_map_refugia_alpha"], edgecolor=ec, linewidth=0.6, label=STYLE["cost_map_refugia_label"])]
    return draw, handles


def figure_cost_wide(P, path, insets="examples"):
    """06 · 01 -- the movement-cost surface on the y2y Act 1 wide layout: the four cost swatches in the ramp slot ("Cost of moving
    through the land"), the core refugia (the complexes) as the only overlay -- no PAs, no IPCAs, no PA names in the insets
    (STYLE["cost_map_context"]=True restores the W11 layers) -- postal codes on the frame, refugia names + towns in the insets."""
    import director_plot as dp
    S_, shares = cost_surface(P)
    print("movement cost (withheld-terrain surface), share of the routable area: " + " · ".join(f"{c}: {v:.1f}%" for c, v in shares.items()))   # 5 keys when water is split
    S_ = dict(S_); S_["label"] = STYLE["cost_map_ramp_label"]
    return _wide(P, path, S_, insets)


def figure_choices_wide(P, path, insets="examples"):
    """05 · 02 -- "where the land still offers choices": the corridor-pressure classes in the ramp slot as the key; PA and
    IPCA fills over the corridor land mark what is already satisfied (W11 overlay mode); everything else as on 01."""
    S_, counts = classes_surface(P)
    n_pa, n_ip = int((P.secured_by == "pa").sum()), int((P.secured_by == "ipca").sum())
    n_nc = {c: int((P.cls == c).sum()) for c in NEAR_KEYS}
    print("links per class: " + " · ".join(f"{c} {n}" for c, n in counts.items())
          + f" | adjacent {sum(n_nc.values())} ({', '.join(f'{k.split(chr(95))[-1]} {v}' for k, v in n_nc.items())})"
          + (" | H8 OPEN -- squeezed folded into securing" if P.h8_open else "")
          + f" | already connected: {n_pa} within existing PAs, {n_ip} once the proposed conservation areas are realized"
          + f" | band = about {P.R.cutoff * P.R.cell_km:.1f} km of extra travel on open ground")
    return _wide(P, path, S_, insets)


# ================= 05 · 03-05: the route options (the northern 07 · 03-05 mirrored) =================
# The deck's numbered examples ("route options"): up to STYLE["max_examples"] links chosen by the automatic rule (or pinned),
# numbered north -> south. 03 = each option's corridor band in ITS NUMBER'S colour from the y2y cluster palette over the
# pressure classes (corridors_director.option_color / OPTION_COLOR_ORDER), numbered at the band's median cell; 04 = the y2y
# star grid + the two inset windows as locator panels; 05 = the y2y consequences table. Profiles on the Y2Y director
# construction (director_core.block_percentiles / ValueRatios, fractional 300 m -> 1 km cover) -- the same machinery as the
# north, with the reference columns taken from the PA / proposed-IPCA vectors (nodes here are refugia, not areas).
CONSEQ_REFERENCE = [("pa", "Banff National Park", "Banff National Park"),            # (layer, name fragment, column name): the y2y
                    ("ipca", "Dene K", "Dene Kʼéh Kusān (proposed IPCA)")]          # tables' rule -- real example areas, one PA + one IPCA


def option_nums(P):
    return tuple(x["num"] for x in P.examples)


def _options_overlay(P, F, nums=None):
    """The route options' overlay for any panel (Ethan 2026-09-29, the northern 07 · 03 construction): the protected-land overlay of
    03 underneath, each option's corridor band OUTLINED in its number's colour (a ring with a thin white halo) so the band's
    pressure fill shows through, the numbers placed by the northern post-draw placer (outside the band, no leader, clear of every
    other text). Returns (draw, handles, marks, colors); the legend gets the y2y cluster swatch row "Route options" (option_legend)."""
    import director_plot as dp
    nums = option_nums(P) if nums is None else tuple(nums)
    marks = cd._option_marks(P, F, nums)
    colors = {n: cd.option_color(n) for n, _, _, _ in marks}
    step = F.STEP
    layers = [(_reduce(np.asarray(m, bool), step), colors[n]) for n, m, _, _ in marks]
    base_draw, handles = (_protection_overlay(F, P) if STYLE.get("options_protected", True) else _base_overlay(F, P))
    fr_draw, fr_handles = _front_layer(F, P)
    handles = handles + fr_handles

    def draw(ax):
        fr_draw(ax); base_draw(ax)
        if STYLE.get("option_style", "outline") == "outline":
            lw = dp.STYLE.get("option_lw", 0.8) * dp.STYLE.get("_lw_scale", 1.0)          # thinner (Ethan 2026-10-01, with the north; was cluster_lw × 1.6)
            for m, col in layers:
                mf = m.astype(np.float32)
                ax.contour(mf, levels=[0.5], colors=["white"], linewidths=lw + dp.STYLE.get("option_halo", 0.8), zorder=3.55)
                ax.contour(mf, levels=[0.5], colors=[col], linewidths=lw, zorder=3.6)
        else:                                                                  # "fill": the band in its colour (the first wolverine 03)
            for m, col in layers:
                ax.imshow(np.where(m, 1.0, np.nan).astype(np.float32), cmap=ListedColormap([col]), interpolation="nearest", zorder=0.9)
        if STYLE.get("option_markers", False):                                 # the old leader markers; the default numbers come from the placer
            for num, _, xy, side in marks:
                cd._number_marker_px(ax, xy, num, colors[num], side)
    mode = STYLE.get("option_legend", "swatches")
    if mode == "swatches":
        handles = handles + [dp.cluster_handle("Route options", colors=[colors[n] for n in colors])]
    elif mode == "rows":
        handles = handles + [Patch(facecolor="none", edgecolor=colors[n], linewidth=2.0, label=f"Route option {n}") for n in colors]
    handles = handles + _boundary_handles()
    return draw, handles, marks, colors


def figure_options_wide(P, path, insets="fixed", nums=None):
    """06 · 04 -- the route options on the wide layout: 03's map (pressure surface over the grey protected land, names) with each
    option's corridor band outlined in its number's colour (y2y cluster palette, OPTION_COLOR_ORDER) and numbered 1-4 outside the
    band; inset A holds 1-2, B holds 3-4 (EXAMPLE_PICKS, numbered north -> south). Names, numbers and town labels never overlap."""
    import director_plot as dp
    F = director_frame(P)
    S_, _ = _strips_surface(P)
    assert dp.STYLE.get("map_layout") == "wide" and dp.STYLE.get("inset_clusters"), "apply dp.STYLE.update(wd.WIDE_STYLE) first (06's setup cell)"
    dp.STYLE["inset_windows"] = inset_windows(P, insets)
    S2 = dict(S_); S2["img"] = _reduce(S_["img"], F.STEP)
    a = STYLE.get("protection_surface_alpha")
    if a is not None and STYLE.get("options_protected", True):
        S2["alpha"] = float(a)                                                 # as on 03
    draw, handles, marks, colors = _options_overlay(P, F, nums)
    print("route options: " + " · ".join(f"{n} {colors[n]} at px {tuple(round(v) for v in xy)} ({side})" for n, _, xy, side in marks))
    names_post, log = _names_post(P, F) if STYLE.get("options_protected", True) else ((lambda ax, win: None), dict(names=[], flipped=0, hidden=0))
    marks_f = [(n, _reduce(np.asarray(m, bool), F.STEP), xy, side) for n, m, xy, side in marks]   # the placer walks the FRAME grid (600 m); the marks carry 300 m masks
    numbers_post = cd._option_marker_placer(P, F, marks_f, colors)

    def post(ax, win):                                                         # names first, then the numbers avoid them, then the towns flip clear of both
        if STYLE.get("options_protected", True):
            n_pa, n_ip = int(STYLE.get("protection_pa_names", 0)), int(STYLE.get("protection_ipca_names", 0))
            if (n_pa or n_ip) and not (tuple(win) == tuple(F.WINDOW) and not STYLE.get("protection_frame_names", False)):
                pan = P.pa_all[P.pa_all["km2"] >= float(STYLE.get("protection_pa_min_km2", 100))].copy()
                pan["_label"] = pan["PA_Name"].astype(str).str.split(" (", regex=False).str[0].str.split(" [", regex=False).str[0]
                log["names"] += _place_area_names(ax, F, win, pan, "_label", n_pa, dp.STYLE["inset_fs"]) if n_pa else []
                if n_ip and len(P.ipca):
                    ipg = P.ipca.copy(); nf = next((c for c in ipg.columns if "name" in c.lower()), None)
                    ipg["_label"] = (ipg[nf].astype(str) + str(STYLE.get("protection_ipca_suffix", ""))) if nf else ""
                    log["names"] += _place_area_names(ax, F, win, ipg, "_label", n_ip, dp.STYLE["inset_fs"])
        numbers_post(ax, win)
        f, h = _declutter_texts(ax); log["flipped"] += f; log["hidden"] += h
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    dp.wide_map(F, path, "", draw, handles, with_ipca_names=False, surface=S2, post_draw=post)
    print(f"names placed: {log['names']} · town labels flipped {log['flipped']}, hidden {log['hidden']}")
    _legend_note()
    return path

def _reference_masks(P):
    """The consequences references as 300 m masks from the PA / proposed-IPCA vectors (CONSEQ_REFERENCE)."""
    R = P.R
    out = []
    for layer, frag, name in CONSEQ_REFERENCE:
        if layer == "pa":
            g = P.pa_all[P.pa_all["PA_Name"].astype(str).str.contains(frag, regex=False)]
        else:
            g = P.ipca
            if len(g):
                nf = next((c for c in g.columns if "name" in c.lower()), None)
                g = g[g[nf].astype(str).str.contains(frag, regex=False)] if nf else g.iloc[0:0]
        if not len(g):
            print(f"  reference {name!r}: not found in the {layer} layer -- column skipped"); continue
        m = rasterize(((geom, 1) for geom in g.geometry), out_shape=R.shape, transform=R.transform, fill=0, dtype="uint8").astype(bool)
        out.append((layer, name, m))                                       # (layer "pa" | "ipca", column name, 300 m mask)
    return out


def option_profiles_y2y(P, nums=None):
    """Cached on P: the route options (+ the reference areas) on the y2y DIRECTOR CONSTRUCTION over the Y2Y-wide allocatable
    landscape -- per star axis the mean PERCENTILE (director_core.block_percentiles) and the consequences RATIO
    (director_core.ValueRatios), both with the fractional 300 m -> 1 km cover weights. DataFrame: kind (option | reference),
    number, name, area_km2, pct_<axis>, ratio_<axis>."""
    nums = option_nums(P) if nums is None else tuple(nums)
    key = ("_y2y_profiles", nums)
    cache = getattr(P, "_y2y_profiles", {})
    if key in cache:
        return cache[key]
    R = P.R
    G = dc.grid(); B = dc.block_percentiles(G); VR = dc.ValueRatios(G, B)
    COEX = dc.coexistence_layer(G)                                        # the bear-coexistence row (package spec v2.2); None -> empty cells
    items = [("option", n, t, m) for n, t, m, _ in cd._option_masks(P) if n in nums]
    items += [(f"reference_{layer}", "", name, m) for layer, name, m in _reference_masks(P)]
    rows = []
    for kind, num, name, m in items:
        w1 = cc._to_audit_frac(R, m)[G.pu]
        assert w1.sum() > 0, f"{kind} {num or name}: no 1 km cover"
        pct = {ax: float((w1 * B.axes[ax]).sum() / w1.sum()) for ax in dc.STAR_AXES}
        # the y2y consequences rule, package spec v2.2 (M4.42; with the northern option_profiles_y2y, 2026-10-01): representativeness = the
        # mean representation quotient -- a locked reference (Banff) on on-extent footprints + total land ("extent", footnoted); an option
        # band or an IPCA on its unprotected part with the allocatable basis; the other rows on the whole footprint
        basis = "extent" if kind == "reference_pa" else "allocatable"
        w_rep = w1 if basis == "extent" else w1 * G.disc
        rat = VR.of(None, weights=w1, basis=basis)
        if basis == "allocatable":
            rat["representativeness"] = VR.of(None, weights=w_rep, basis=basis)["representativeness"] if w_rep.sum() > 0 else np.nan
        extras = dc.rep_extras(VR, basis, weights=(w_rep if w_rep.sum() > 0 else w1))
        bear = dc.bear_programs(COEX, G, weights1d=w1)
        rows.append(dict(kind=("reference" if kind.startswith("reference") else kind), number=str(num), name=str(name).replace("\n", " — "),
                         area_km2=int(m.sum()) * R.cell_km2, pct_protected=100.0 * float((w1 * G.locked).sum() / w1.sum()),
                         **{f"pct_{a}": v for a, v in pct.items()}, **{f"ratio_{a}": v for a, v in rat.items()}, **extras, **bear))
    df = pd.DataFrame(rows)
    cache[key] = df; P._y2y_profiles = cache
    return df


def option_stars(P, path, nums=None):
    """05 · 04 -- star plots of the route options on the y2y asset (director_plot.star_grid, one star per option in its colour)."""
    import director_plot as dp
    df = option_profiles_y2y(P, nums)
    prof = [dict(title=("Option " + str(int(r.number)) + (f"\n{r.area_km2:,.0f} km²" if dp.STYLE.get("option_star_area", True) else "")), values={a: float(r[f"pct_{a}"]) for a in dc.STAR_AXES},
                 color=cd.option_color(int(r.number))) for _, r in df[df.kind == "option"].iterrows()]
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    dp.star_grid(prof, path, "Route options — value profile (percentile vs the allocatable landscape)")
    return df


def option_locators(P, path, nums=None, insets="examples", panel_px=None):
    """05 · 04b -- the two inset windows as locator panels on the star grid's geometry (the northern option_locators rule):
    A under the first half of the stars, B under the second; square windows at one scale, the classes + options as on 03."""
    import director_plot as dp
    nums = option_nums(P) if nums is None else tuple(nums)
    F = director_frame(P)
    S_, _ = classes_surface(P); S2 = dict(S_); S2["img"] = _reduce(S_["img"], F.STEP)
    draw, _, marks, _ = _options_overlay(P, F, nums)
    wins = inset_windows(P, insets)
    n_stars = len(nums); ncols = min(4, max(n_stars, 1)); L = dc.STAR_GRID; STYLE_ = dp.STYLE
    tags = list(wins)
    per = max(1, int(np.ceil(n_stars / max(len(tags), 1))))
    with plt.rc_context(dp.SPEC_RC):
        fig_w, fig_h = L["panel_w"] * ncols, max(L["panel_h"], STYLE_["locator_panel_in"] + 0.4)
        fig = plt.figure(figsize=(fig_w, fig_h))
        left, right = 0.125, 0.9
        aw = (right - left) / (ncols + (ncols - 1) * L["wspace"])
        pw = STYLE_["locator_panel_in"] / fig_w; ph = STYLE_["locator_panel_in"] / fig_h
        axes = []
        for i, tag in enumerate(tags):
            cols_ = range(i * per, min((i + 1) * per, ncols))
            cx = float(np.mean([left + aw * (c_ + 0.5) + c_ * aw * L["wspace"] for c_ in cols_])) if len(cols_) else 0.5
            axes.append(fig.add_axes([cx - pw / 2, 0.5 - ph / 2, pw, ph]))
        sc = STYLE_["locator_fs_scale"]
        STYLE_["_fs_scale"] = STYLE_["inset_number_fs"] / STYLE_["cluster_number_fs"] * sc; STYLE_["_lw_scale"] = STYLE_["cluster_lw_inset_scale"] * sc
        fs0, pa0 = STYLE_["inset_fs"], STYLE_["inset_pa_names"]; STYLE_["inset_fs"] = fs0 * sc; STYLE_["inset_pa_names"] = STYLE_["locator_pa_names"]
        try:
            for ax, tag in zip(axes, tags):
                win = dp._fit_window(F, wins[tag], 1.0)
                # no A / B title on the locator panels: the y2y locators carry none (Ethan 2026-10-03, with the north)
                dp._draw_inset(F, ax, win, draw, "", (STYLE.get("complex_labels", "none") != "none"), towns=STYLE_["locator_towns"], codes=None, img=S2["img"], cmap=S2["cmap"], norm=S2["norm"])
        finally:
            STYLE_.pop("_fs_scale", None); STYLE_.pop("_lw_scale", None); STYLE_["inset_fs"] = fs0; STYLE_["inset_pa_names"] = pa0
        path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=STYLE_["export_dpi"])
        if panel_px:
            fig.canvas.draw(); r = fig.canvas.get_renderer()
            for ax, tag in zip(axes, tags):
                bb = ax.get_tightbbox(r).transformed(fig.dpi_scale_trans.inverted()).padded(0.02)
                fig.savefig(path.with_name(f"{path.stem}_{tag}{path.suffix}"), bbox_inches=bb, dpi=STYLE_["panel_export_scale"] * panel_px / bb.width)
        plt.show()
    return path


def option_consequences(P, path, nums=None):
    """05 · 05 -- the consequences table for the route options on the y2y asset (director_plot.consequences_table): mean raw
    value in the option's land / mean over Y2Y-wide allocatable land per star axis; columns = the options, then the reference
    areas (CONSEQ_REFERENCE). Rows also to tables/route_option_consequences.csv."""
    import textwrap
    import director_plot as dp
    F = director_frame(P)
    df = option_profiles_y2y(P, nums)
    rows = df[df.kind == "option"].reset_index(drop=True); ref = df[df.kind == "reference"].reset_index(drop=True)
    P.tab.mkdir(parents=True, exist_ok=True); df.to_csv(P.tab / "route_option_consequences.csv", index=False, encoding="utf-8-sig")
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    dp.consequences_table(F, rows, path, "ROUTE OPTIONS  ·  CONSEQUENCES", "What the route options hold", ref=ref,
                          col_label=lambda r, wrap=18: f"Option {int(r.number)}", group_label="Route options", unit_word="option",      # the link name dropped (Ethan 2026-10-02, with the north)
                          source=f"Y2Y wolverine refugia corridors ({P.R.run_id}, least-cost network on the withheld-terrain surface); "
                                 f"values on the Y2Y director construction (manifest {dc.VP.version} layers).")
    return df

# ================= v2.5 (run spec v3 §1a): the two-layer product on the post-processed v2 run =================
def _complex_bins(P):
    """Per complex: the protection-shading bin (share inside existing PAs against STYLE["complex_shade_bins"])."""
    bins = np.asarray(STYLE["complex_shade_bins"], float)
    share = P.nodes.set_index("node_id")["pa_overlap_frac"].astype(float)
    return {int(c): int(np.searchsorted(bins, v, side="right")) for c, v in share.items()}


def _pinch_points(P):
    """(edge_id, x, y) of the tenth-percentile pinch on every corridor link (D28 `pinch_pos` along the centreline)."""
    R = P.R
    if getattr(R, "centrelines", None) is None or "pinch_pos" not in R.edges.columns:
        return []
    cl = R.centrelines.set_index("edge_id") if "edge_id" in R.centrelines.columns else None
    out = []
    for eid in P.cls.index[P.cls.isin(list(cc.CORRIDOR_CLASSES))]:
        pos = R.edges.loc[eid].get("pinch_pos", np.nan)
        if cl is None or eid not in cl.index or pd.isna(pos):
            continue
        g = cl.loc[eid, "geometry"]
        if g is None or g.is_empty:
            continue
        pt = g.interpolate(float(np.clip(pos, 0, 1)), normalized=True)
        out.append((eid, float(pt.x), float(pt.y)))
    return out


FRONT_STYLE = dict(open_alpha=0.40, cut_alpha=0.85, cut_outline=("#6E5A00", 0.5),   # open = the Minimum tint merged across the interior;
                   label_open="Fronts inside a complex, open ({n})",                    # cut = the Some (narrowing) colour + outline
                   label_cut="Fronts inside a complex, cut: narrow or a road on the path ({n})")


def _front_overlay(F, P):
    """Run spec v3 §8 (revised 2026-09-29): the within-complex fronts drawn as corridors UNDER the inter-complex links -- open fronts as a
    light tint of the Minimum class colour merged across the complex interior, cut fronts in the Some (narrowing) colour with an outline.
    The inter-complex class bands are re-drawn above them at full weight. Returns (draw, handles); nothing when the run carries no fronts."""
    R = P.R; fr = getattr(R, "fronts", None)
    if fr is None or not len(fr):
        return (lambda ax: None), []
    s = F.STEP; shape = R.shape; tr = R.transform
    layers = []
    for cls_, colour, alpha in (("open", ms.CLASS["securing"][0], FRONT_STYLE["open_alpha"]), ("cut", ms.CLASS["squeezed"][0], FRONT_STYLE["cut_alpha"])):
        sub = fr[fr.front_class == cls_]
        if not len(sub):
            continue
        u = rasterize([(g, 1) for g in sub.geometry if g is not None and not g.is_empty], out_shape=shape, transform=tr, fill=0, dtype="uint8").astype(bool)
        u &= ~P.node_mask                                        # the front land between the patches, never the patches themselves
        m = u[::s, ::s] & F.G.pu
        layers.append((cls_, np.where(m, 1.0, np.nan).astype(np.float32), m, colour, alpha, len(sub)))
    S_, _ = classes_surface(P)
    inter = np.asarray(S_["img"])[::s, ::s]

    def draw(ax):
        import director_plot as dp
        for cls_, img, m, colour, alpha, n in layers:
            ax.imshow(img, cmap=ListedColormap([colour]), alpha=alpha, interpolation="nearest", zorder=0.7)
            if cls_ == "cut":
                ec, lw = FRONT_STYLE["cut_outline"]
                ax.contour(m.astype(float), levels=[0.5], colors=[ec], linewidths=lw * dp.STYLE.get("_lw_scale", 1.0), zorder=0.75)
        ax.imshow(inter, cmap=S_["cmap"], norm=S_["norm"], interpolation="nearest", zorder=0.95)     # the inter-complex links over the fronts
    handles = [Patch(facecolor=colour, alpha=alpha, edgecolor=(FRONT_STYLE["cut_outline"][0] if cls_ == "cut" else "none"),
                     label=FRONT_STYLE["label_open" if cls_ == "open" else "label_cut"].format(n=n)) for cls_, _, _, colour, alpha, n in layers]
    return draw, handles


def _complex_overlay(F, P):
    """The v3 network map's overlay: complexes filled in the refugia tone with an alpha step by their share inside existing
    PAs (protection shading), outlined; the proposed conservation areas filled over corridor land (W11); the p10 pinch marked on every
    corridor link. No near-contiguous bands (D-W6). Returns (draw, handles)."""
    import director_plot as dp
    pins = _pinch_points(P) if STYLE.get("pinch_marker", True) else []
    pins_px = [(eid, *dc.xy_to_px(F.G, x, y)) for eid, x, y in pins]
    fr_draw, fr_handles = _front_overlay(F, P) if STYLE.get("fronts_on_map", True) else ((lambda ax: None), [])
    if not STYLE.get("protected_layers", True):                 # Ethan 2026-09-29: the refugia as on 01, no protection shading, no PAs / IPCAs
        base_draw, handles = _cost_overlay(F, P)
        handles = handles + fr_handles

        def draw(ax):
            fr_draw(ax); base_draw(ax)
            for eid, px, py in pins_px:
                ax.plot(px, py, marker="o", ms=4.5 * dp.STYLE.get("_fs_scale", 1.0), mfc="white", mec="black", mew=0.8, ls="none", zorder=3.5, clip_on=True)
        if pins_px:
            handles = handles + [Line2D([], [], marker="o", mfc="white", mec="black", mew=0.8, ls="none", ms=6, label="Narrowest tenth of the corridor (pinch)")]
        return draw, handles
    core, ip = ms.AREA["refugia_core"], ms.AREA["ipca"]
    s = F.STEP; R = P.R
    cid = np.nan_to_num(R.complex_id.values, nan=0).astype(int)[::s, ::s]
    bins = _complex_bins(P); nb = len(STYLE["complex_shade_alphas"])
    layers = []
    for b in range(nb):
        ids = [c for c, v in bins.items() if v == b]
        if ids:
            m = np.isin(cid, ids) & F.G.pu
            layers.append((b, np.where(m, 1.0, np.nan).astype(np.float32)))
    outline = (cid > 0) & F.G.pu
    fill_i = np.full(F.G.shape, np.nan, np.float32); fill_i[F.IPCA2D] = 1.0

    def draw(ax):
        fr_draw(ax)
        for b, img in layers:
            ax.imshow(img, cmap=ListedColormap([core["fill"]]), alpha=STYLE["complex_shade_alphas"][b], interpolation="nearest", zorder=1.0)
        ax.contour(outline.astype(float), levels=[0.5], colors=[ms.NODE["edge"]], linewidths=ms.NODE.get("lw", 0.5) * dp.STYLE.get("_lw_scale", 1.0), zorder=1.02)
        ax.imshow(fill_i, cmap=ListedColormap([ip["fill"]]), alpha=0.85, interpolation="nearest", zorder=1.05)
        for eid, px, py in pins_px:
            ax.plot(px, py, marker="o", ms=4.5 * dp.STYLE.get("_fs_scale", 1.0), mfc="white", mec="black", mew=0.8, ls="none", zorder=3.5, clip_on=True)

    edges_ = [f"< {int(STYLE['complex_shade_bins'][0]*100)}%"] + [f"{int(a*100)}–{int(b*100)}%" for a, b in zip(STYLE["complex_shade_bins"][:-1], STYLE["complex_shade_bins"][1:])] + [f"≥ {int(STYLE['complex_shade_bins'][-1]*100)}%"]
    handles = [Patch(facecolor=dp.PA_COLOR, label=PA_WIDE_LABEL),
               Patch(facecolor=ip["fill"], alpha=0.85, edgecolor=ip["edge"], label=IPCA_WIDE_LABEL)]
    handles += [Patch(facecolor=core["fill"], alpha=STYLE["complex_shade_alphas"][b], edgecolor=ms.NODE["edge"], label=f"Refugia complex, {edges_[b]} inside existing PAs")
                for b in range(nb) if any(bb == b for bb in bins.values())]
    handles += fr_handles
    if pins_px:
        handles.append(Line2D([], [], marker="o", mfc="white", mec="black", mew=0.8, ls="none", ms=6, label="Narrowest tenth of the corridor (pinch)"))
    return draw, handles


FRONT_TINT = dict(open_alpha=0.70, cut_alpha=0.95, cut_outline=("#3A3A3A", 0.45))   # node level (spec §8): open fronts = a lighter tint of the class colour; cut fronts outlined.
# The pressure palette is the SHARED default (corridors_mapstyle.CLASS_PALETTE = "sand" since 2026-09-29, as the northern 07): light ->
# dark = low -> high, so an open front's tint must not fade into the land (sand Minimum at 0.45 alpha sat at luminance 0.91 on land 0.97)


def _strips_surface(P):
    """The corridor-pressure surface for 02 / 03. STYLE["front_style"]: "plain" (Ethan 2026-09-29, the default) = every link -- strips
    AND fronts -- in its class colour on the one scale, nothing drawn separately; "tint" = the spec §8 treatment (strips only here,
    fronts as tinted bands from _fronts_tint); "hidden" = strips only, fronts not drawn."""
    S_, counts = classes_surface(P)
    if STYLE.get("front_style", "plain") == "plain":
        return S_, counts
    img = np.asarray(S_["img"]).copy()
    front_ids = [k for k in P.cls.index if P.kind.get(k) == "front"]
    if front_ids:
        img[np.isin(P.owner, [P.order[k] for k in front_ids if k in P.order])] = np.nan
    S_ = dict(S_); S_["img"] = img
    counts = {c: int(sum(1 for k in P.cls.index if P.cls.get(k) == c and P.kind.get(k) == "strip")) for c in counts}
    return S_, counts


def _front_layer(F, P):
    """The separate front layer, only under STYLE["front_style"] == "tint"."""
    return _fronts_tint(F, P) if STYLE.get("front_style", "plain") == "tint" else ((lambda ax: None), [])


def _fronts_tint(F, P):
    """Node level (spec §8): fronts as bands in their class colour -- open fronts as the light tint, cut fronts at full strength with an
    outline; drawn above the strip surface and below the nodes. Returns (draw, handles); nothing when the run has no fronts."""
    import director_plot as dp
    R = P.R; s = F.STEP
    front_ids = [k for k in P.cls.index if P.kind.get(k) == "front" and P.cls.get(k) in cc.CORRIDOR_CLASSES]
    if not front_ids:
        return (lambda ax: None), []
    cut = R.edges["front_cut"].fillna(False).astype(bool) if "front_cut" in R.edges.columns else pd.Series(False, index=R.edges.index)
    layers = []
    for c in ms.CLASS_ORDER:
        for is_cut in (False, True):
            ids = [k for k in front_ids if P.cls.get(k) == c and bool(cut.get(k, False)) == is_cut]
            if not ids:
                continue
            m = _reduce(np.isin(P.owner, [P.order[k] for k in ids if k in P.order]) & R.corridor, s)
            layers.append((c, is_cut, np.where(m, 1.0, np.nan).astype(np.float32), m, len(ids)))
    n_open = sum(n for _, cut_, _, _, n in layers if not cut_); n_cut = sum(n for _, cut_, _, _, n in layers if cut_)

    def draw(ax):
        for c, is_cut, img, m, n in layers:
            ax.imshow(img, cmap=ListedColormap([ms.CLASS[c][0]]), alpha=(FRONT_TINT["cut_alpha"] if is_cut else FRONT_TINT["open_alpha"]), interpolation="nearest", zorder=0.8)
            if is_cut:
                ec, lw = FRONT_TINT["cut_outline"]
                ax.contour(m.astype(float), levels=[0.5], colors=[ec], linewidths=lw * dp.STYLE.get("_lw_scale", 1.0), zorder=0.85)
    handles = []
    if STYLE.get("front_legend_rows", False):                    # Ethan 2026-09-29: no front rows in the legend -- the colour bar is the key
        handles = [Patch(facecolor=ms.CLASS["securing"][0], alpha=FRONT_TINT["open_alpha"], label=f"Fronts between neighbouring refugia, open: light tint of the class colour ({n_open})"),
                   Patch(facecolor=ms.CLASS["squeezed"][0], alpha=FRONT_TINT["cut_alpha"], edgecolor=FRONT_TINT["cut_outline"][0], linewidth=0.8,
                         label=f"Fronts, cut (narrower than half the barrier-free width): class colour, outlined ({n_cut})")]
    return draw, handles


def figure_network_wide(P, path, insets="fixed"):
    """06 · 02 -- the network by corridor pressure on the wide layout, one scale: strips at full weight in the ramp slot (the key),
    fronts as bands in their class colour (open = light tint, cut = outlined), the refugia in the 01 scheme, no protected layers."""
    import director_plot as dp
    S_, counts = _strips_surface(P)
    F = director_frame(P)
    assert dp.STYLE.get("map_layout") == "wide" and dp.STYLE.get("inset_clusters"), "apply dp.STYLE.update(wd.WIDE_STYLE) first"
    dp.STYLE["inset_windows"] = inset_windows(P, insets)
    S_ = dict(S_); S_["img"] = _reduce(S_["img"], F.STEP)
    base_draw, handles = (_complex_overlay(F, P) if P.contracted else _base_overlay(F, P))
    fr_draw, fr_handles = _front_layer(F, P)

    def draw(ax):
        fr_draw(ax); base_draw(ax)
    handles = handles + fr_handles + _boundary_handles()
    n_f = int(sum(1 for k in P.cls.index if P.kind.get(k) == "front")); n_pa, n_ip = int((P.secured_by == "pa").sum()), int((P.secured_by == "ipca").sum())
    print("strips per class: " + " · ".join(f"{c} {n}" for c, n in counts.items()) + f" | fronts {n_f} | {len(P.nodes)} nodes"
          + f" | already connected: {n_pa} within existing PAs, {n_ip} once the proposed conservation areas are realized | band = about {P.R.cutoff * P.R.cell_km:.1f} km of extra travel on open ground")
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    dp.wide_map(F, path, "", draw, handles, with_ipca_names=(STYLE.get("complex_labels", "none") != "none"), surface=S_)
    _legend_note()
    return path


def _protection_overlay(F, P):
    """06 · 03 / 04's overlay: the refugia as on 01, and the protected land UNDER the corridor-pressure surface (zorder 0.45 < the
    surface's 0.5; Ethan 2026-09-29: 'put the PAs and IPCAs under the corridor pressure colours'), so the bands keep their class
    colour and the grey reads through them at the surface's alpha. ONE grey for both kinds (protection_fill, one legend row) unless
    protection_fill_pa AND protection_fill_ipca are set (two neutrals, two rows; cells under both take the PA fill). The layout's
    own PA layer stays empty (the default no-PA frame). Returns (draw, handles)."""
    import director_plot as dp
    alpha = float(STYLE.get("protection_alpha", 0.85)); z = STYLE.get("protection_zorder", 0.45)
    one = STYLE.get("protection_fill") or dp.PA_COLOR
    f_pa, f_ip = STYLE.get("protection_fill_pa"), STYLE.get("protection_fill_ipca")
    split = bool(f_pa and f_ip)
    R = P.R; s_ = F.STEP
    pa2d = _reduce(np.asarray(R.protected_pa, bool) if getattr(R, "protected_pa", None) is not None else np.asarray(P.pa_mask300, bool), s_) & F.G.pu
    ip2d = F.IPCA2D & F.G.pu & ~pa2d
    ref_draw, ref_handles = _cost_overlay(F, P)
    if split:
        layers = [(pa2d, f_pa), (ip2d, f_ip)]
        handles = ref_handles + [Patch(facecolor=f_pa, alpha=alpha, label=STYLE["protection_label_pa"]),
                                 Patch(facecolor=f_ip, alpha=alpha, label=STYLE["protection_label_ipca"])]
    else:
        layers = [(pa2d | ip2d, one)]
        handles = ref_handles + [Patch(facecolor=one, alpha=alpha, label=STYLE["protection_label"])]
    imgs = []
    for m, col in layers:
        a = np.full(F.G.shape, np.nan, np.float32); a[m] = 1.0; imgs.append((a, col))

    def draw(ax):
        for a, col in imgs:
            ax.imshow(a, cmap=ListedColormap([col]), alpha=alpha, interpolation="nearest", zorder=z)
        ref_draw(ax)
    return draw, handles


def _place_area_names(ax, F, win, gdf, name_col, top_n, fs, color="0.25", pad_pt=2.0, wrap=22):
    """Names for the largest areas in a panel's window, each at the first position where its text box overlaps NO other text on the
    axes -- postal codes, towns, earlier names, option numbers (Ethan 2026-09-29: no text overlaps) -- and lies inside the panel:
    the area's pole of inaccessibility first, then a coarse grid of its interior points; an area with no clear spot stays unnamed.
    Returns the names placed."""
    from shapely.ops import polylabel
    import matplotlib.patheffects as _pe, textwrap as _tw
    G = F.G; px0, px1, py0, py1 = win
    x0 = G.transform.c + px0 * G.transform.a; x1 = G.transform.c + px1 * G.transform.a
    yt = G.transform.f + py0 * G.transform.e; yb = G.transform.f + py1 * G.transform.e
    winp = _box(x0, yb, x1, yt)
    g = gdf[gdf.intersects(winp)].copy()
    if not len(g):
        return []
    g["geometry"] = g.geometry.intersection(winp); g = g[~g.geometry.is_empty].copy(); g["_a"] = g.geometry.area
    g = g.sort_values("_a", ascending=False).head(int(top_n))
    fig = ax.figure; r = fig.canvas.get_renderer(); axbb = ax.get_window_extent(r); pad = pad_pt * fig.dpi / 72.0
    placed = []
    for _, row in g.iterrows():
        geom = row.geometry
        polys = sorted([q for q in (geom.geoms if hasattr(geom, "geoms") else [geom]) if q.geom_type == "Polygon" and not q.is_empty], key=lambda q: -q.area)
        cands = []
        for q in polys[:2]:
            try:
                cands.append(polylabel(q, tolerance=500))
            except Exception:
                cands.append(q.representative_point())
            minx, miny, maxx, maxy = q.bounds
            for fx in (0.5, 0.35, 0.65, 0.2, 0.8):
                for fy in (0.5, 0.35, 0.65, 0.2, 0.8):
                    pt = Point(minx + fx * (maxx - minx), miny + fy * (maxy - miny))
                    if q.contains(pt):
                        cands.append(pt)
        name = "\n".join(_tw.wrap(str(row[name_col]), wrap))
        others = [t.get_window_extent(r) for t in ax.texts if t.get_visible() and t.get_text().strip()]
        for pt in cands:
            px, py = dc.xy_to_px(G, pt.x, pt.y)
            t = ax.text(px, py, name, fontsize=fs, fontstyle="italic", color=color, ha="center", va="center", zorder=5.5, clip_on=True, linespacing=1.1,
                        path_effects=[_pe.withStroke(linewidth=2.0, foreground="white", alpha=0.9)])
            bb = t.get_window_extent(r).padded(pad)
            if axbb.contains(bb.x0, bb.y0) and axbb.contains(bb.x1, bb.y1) and not any(bb.overlaps(o) for o in others):
                placed.append(str(row[name_col])); break
            t.remove()
    return placed


def _declutter_texts(ax):
    """Ethan 2026-09-29: no text overlaps. A town label (an annotation anchored to its dot) that overlaps any other text is flipped
    through the offset quadrants; one that still overlaps is hidden (its dot stays). Returns (flipped, hidden)."""
    from matplotlib.text import Annotation
    fig = ax.figure; r = fig.canvas.get_renderer()
    texts = [t for t in ax.texts if t.get_visible() and t.get_text().strip()]
    flipped = hidden = 0
    for t in [t for t in texts if isinstance(t, Annotation)]:
        others = [o.get_window_extent(r) for o in texts if o is not t and o.get_visible()]
        if not any(t.get_window_extent(r).overlaps(o) for o in others):
            continue
        ok = False
        for dx, dy, ha, va in ((4, 3, "left", "baseline"), (-4, 3, "right", "baseline"), (4, -3, "left", "top"), (-4, -3, "right", "top"),
                               (0, 7, "center", "bottom"), (0, -7, "center", "top")):
            t.set_position((dx, dy)); t.set_ha(ha); t.set_va(va)
            if not any(t.get_window_extent(r).overlaps(o) for o in others):
                ok = True; break
        if ok:
            flipped += 1
        else:
            t.set_visible(False); hidden += 1
    return flipped, hidden


def _names_post(P, F):
    """post_draw(ax, win) for the protected-land maps: the largest PAs and proposed areas named (insets only unless
    protection_frame_names), then the town labels decluttered. Returns the callback and a dict it fills with what it did."""
    import director_plot as dp
    n_pa, n_ip = int(STYLE.get("protection_pa_names", 0)), int(STYLE.get("protection_ipca_names", 0))
    pan = P.pa_all[P.pa_all["km2"] >= float(STYLE.get("protection_pa_min_km2", 100))].copy() if n_pa else None
    if pan is not None:
        pan["_label"] = pan["PA_Name"].astype(str).str.split(" (", regex=False).str[0].str.split(" [", regex=False).str[0]
    ipg = None
    if n_ip and len(P.ipca):
        ipg = P.ipca.copy(); nf = next((c for c in ipg.columns if "name" in c.lower()), None)
        ipg["_label"] = (ipg[nf].astype(str) + str(STYLE.get("protection_ipca_suffix", ""))) if nf else ""
    log = dict(names=[], flipped=0, hidden=0)

    def post(ax, win):
        if not (tuple(win) == tuple(F.WINDOW) and not STYLE.get("protection_frame_names", False)):
            fs = dp.STYLE["inset_fs"]
            if pan is not None and len(pan):
                log["names"] += _place_area_names(ax, F, win, pan, "_label", n_pa, fs)
            if ipg is not None and len(ipg):
                log["names"] += _place_area_names(ax, F, win, ipg, "_label", n_ip, fs)
        f, h = _declutter_texts(ax); log["flipped"] += f; log["hidden"] += h
    return post, log

def figure_protection_wide(P, path, insets="fixed"):
    """06 · 03 -- the network by corridor pressure (02's surface and key) over protected land: existing PAs and the proposed
    IPCAs / PAs as ONE grey layer (director_plot.PA_COLOR #8f8f8f at 85%) UNDER the bands, the refugia as on 01, the largest PAs and
    proposed areas NAMED in each inset with no text overlapping (STYLE protection_pa_names / protection_ipca_names; the proposed
    ones carry protection_ipca_suffix). Prints the corridor land inside existing PAs / inside the proposed conservation areas only / outside both."""
    import director_plot as dp
    F = director_frame(P)                                                      # the default no-PA frame: the grey and the names are this map's
    S_, counts = _strips_surface(P)
    assert dp.STYLE.get("map_layout") == "wide" and dp.STYLE.get("inset_clusters"), "apply dp.STYLE.update(wd.WIDE_STYLE) first"
    dp.STYLE["inset_windows"] = inset_windows(P, insets)
    S2 = dict(S_); S2["img"] = _reduce(S_["img"], F.STEP)
    a = STYLE.get("protection_surface_alpha")
    if a is not None:
        S2["alpha"] = float(a)                                                 # this map's surface (and its key) more transparent than 02 / 04
    draw, handles = _protection_overlay(F, P)
    handles = handles + _boundary_handles()
    post, log = _names_post(P, F)
    R = P.R; corr = np.asarray(R.corridor, bool)
    pa = np.asarray(R.protected_pa, bool) if getattr(R, "protected_pa", None) is not None else P.pa_mask300
    ip = np.asarray(R.protected_ipca, bool) if getattr(R, "protected_ipca", None) is not None else np.zeros(R.shape, bool)
    a_ = R.cell_km2; k_pa, k_ip, k_out = (corr & pa).sum() * a_, (corr & ip & ~pa).sum() * a_, (corr & ~pa & ~ip).sum() * a_
    print(f"corridor land {corr.sum() * a_:,.0f} km²: inside existing PAs {k_pa:,.0f} ({k_pa / (corr.sum() * a_):.0%}) · inside the proposed conservation areas only "
          f"{k_ip:,.0f} ({k_ip / (corr.sum() * a_):.0%}) · outside both {k_out:,.0f} ({k_out / (corr.sum() * a_):.0%})"
          + f" | links already connected: {int((P.secured_by == 'pa').sum())} within existing PAs, {int((P.secured_by == 'ipca').sum())} once the IPCAs are realized")
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    dp.wide_map(F, path, "", draw, handles, with_ipca_names=False, surface=S2, post_draw=post)
    print(f"names placed: {log['names']} · town labels flipped {log['flipped']}, hidden {log['hidden']}")
    _legend_note()
    return path

def table_complexes(P):
    """Layer A (run spec v3 §1a): one row per complex with its coverage and act."""
    assert P.contracted
    g = P.nodes
    df = pd.DataFrame({
        "Complex": g["node_id"], "Name": g["name"], "Patches": g["n_patches"], "Patch ids": g["patch_ids"] if "patch_ids" in g.columns else "",
        "Area (km²)": g["area_km2"].round(0).astype(int),
        "Inside existing PAs (%)": (100 * g["pa_overlap_frac"]).round(0).astype("Int64"),
        "Added by proposed conservation areas (%)": (100 * g["ipca_added_share"]).round(0).astype("Int64") if "ipca_added_share" in g.columns else 0,
        "In the prioritizr core (%)": (100 * g["core_share"]).round(0).astype("Int64") if "core_share" in g.columns else np.nan,
        "Outside PAs, IPCAs and core (%)": (100 * g["outside_all_share"]).round(0).astype("Int64") if "outside_all_share" in g.columns else np.nan,
        "Within-complex slivers": g["n_slivers"], "Slivers with a cost-100/1000 feature": g["n_slivers_with_feature"],
        "Act": [_complex_act(P, c) for c in g["node_id"]], "lat": g["lat"].round(3), "lon": g["lon"].round(3)})
    df.to_csv(P.tab / "A_complexes.csv", index=False, encoding="utf-8-sig")
    print(f"A_complexes: {len(df)} complexes -> {P.tab / 'A_complexes.csv'}")
    return df


def _complex_act(P, cid):
    lat = float(P.nodes.set_index("node_id").loc[cid, "lat"]); br = tuple(STYLE["act_breaks_lat"])
    if len(br) == 1:
        return "north" if lat >= br[0] else "south"
    return "north" if lat >= br[0] else ("central" if lat >= br[1] else "south")


def table_slivers(P):
    """Layer A's backing table: the within-complex near-contiguous links of the patch-level run (slivers_v2.csv), listed not mapped."""
    R = P.R
    if getattr(R, "slivers", None) is None:
        print("no slivers_v2.csv in the run"); return pd.DataFrame()
    sl = R.slivers.copy()
    names = P.nodes.set_index("node_id")["name"]
    sl.insert(1, "complex", sl["complex_id"].map(names))
    sl = sl.sort_values(["complex_id", "has_feature", "path_len_km"], ascending=[True, False, True])
    sl.to_csv(P.tab / "A_slivers.csv", index=False, encoding="utf-8-sig")
    n_feat = int(sl["has_feature"].sum())
    print(f"A_slivers: {len(sl)} within-complex slivers, {n_feat} with a cost-100/1000 feature (the within-complex pinch points) -> {P.tab / 'A_slivers.csv'}")
    return sl


def table_fronts(P):
    """The within-complex fronts (run spec v3 §5 revised): one row per front with the drawn class (open / cut) and the table-only
    four-class reading (interior D7 on v2's front graph, M7.8) -> tables/A_fronts.csv; per complex counts + front area (per-link sums;
    the dissolved figure is in accounting.json) -> tables/A_fronts_by_complex.csv. Separate from Layer B: the two levels never share counts."""
    R = P.R; fr = getattr(R, "fronts", None)
    if fr is None or not len(fr):
        print("no fronts in the run"); return pd.DataFrame(), pd.DataFrame()
    f = pd.DataFrame(fr.drop(columns="geometry"))
    names = P.nodes.set_index("node_id")["short"]
    f.insert(1, "complex", f["complex_id"].map(names))
    cols = ["complex_id", "complex", "edge_id", "patch_i", "patch_j", "path_len_km", "front_class", "front_class_d23", "cut", "narrow", "road_on_path",
            "squeeze_ratio_obs", "E_v2", "E_interior", "bridge", "band_new_km2"]
    f = f[[c for c in cols if c in f.columns]].sort_values(["complex_id", "front_class", "path_len_km"])
    f.to_csv(P.tab / "A_fronts.csv", index=False, encoding="utf-8-sig")
    by = f.groupby("complex_id").agg(fronts=("edge_id", "size"), open=("front_class", lambda x: int((x == "open").sum())), cut=("cut", "sum"),
                                    narrow=("narrow", "sum"), road_on_path=("road_on_path", "sum"), E_patch_level=("E_v2", "sum"), E_interior_reading=("E_interior", "sum"),
                                    front_land_per_link_sum_km2=("band_new_km2", lambda x: round(float(x.fillna(0).sum()))))
    by.insert(0, "complex", by.index.map(names))
    by.to_csv(P.tab / "A_fronts_by_complex.csv", encoding="utf-8-sig")
    print(f"A_fronts: {len(f)} fronts ({int((f.front_class == 'open').sum())} open, {int(f.cut.sum())} cut) in {len(by)} complexes -> A_fronts.csv, A_fronts_by_complex.csv")
    return f, by


def table_corridors(P):
    """Layer B (run spec v3 §5): the inter-complex corridor links with class, D29 kind, median + p10 width, branches, band land
    (dissolved per link = its owned land), the share outside PAs and IPCAs, W11 status and the two complexes' protection."""
    R = P.R; e = R.edges
    ids = list(P.cls.index[P.cls.isin(list(cc.CORRIDOR_CLASSES))])
    prot = P.nodes.set_index("node_id")
    rows = []
    for eid in ids:
        r = e.loc[eid]
        band = float(r.get("band_new_km2", np.nan))                     # the link's own band, dissolved, node land excluded (spec: per link)
        if pd.isna(band):
            band = float(((P.owner == P.order[eid]) & R.corridor).sum()) * R.cell_km2
        unp = float(r.get("band_unprotected_km2", np.nan)); unp = unp if pd.notna(unp) else band     # same basis (the engine's W11 columns)
        ci, cj = _complex_of_edge(P, r)
        by = P.secured_by.get(eid, "")
        rows.append({"edge_id": eid, "Connects": f"{_short(P, ci or 0)} ↔ {_short(P, cj or 0)}", "Complexes": f"C{ci} ↔ C{cj}",
                     "Class": cc.LINK_CLASS_LABEL.get(P.cls.get(eid), P.cls.get(eid)),
                     "Alternative link is": (r.get("alt_kind") if isinstance(r.get("alt_kind"), str) and r.get("alt_kind") else "—"),
                     "Width ratio, median": (round(float(r["squeeze_ratio_obs"]), 2) if pd.notna(r.get("squeeze_ratio_obs")) else np.nan),
                     "Width ratio, tenth percentile": (round(float(r["width_ratio_p10"]), 2) if pd.notna(r.get("width_ratio_p10")) else np.nan),
                     "Route branches": (int(r["n_branches"]) if pd.notna(r.get("n_branches")) else np.nan),
                     "Band land (km², dissolved per link; links overlap)": round(band), "Outside PAs and IPCAs (km²)": round(unp),
                     "Crosses unprotected land": bool(unp > 0),
                     "Already connected": {"pa": "within existing PAs", "ipca": "once the proposed conservation areas are realized", "": "no"}.get(by, by),
                     "Complex i inside PAs (%)": int(round(100 * float(prot.loc[ci, "pa_overlap_frac"]))) if ci in prot.index else np.nan,
                     "Complex j inside PAs (%)": int(round(100 * float(prot.loc[cj, "pa_overlap_frac"]))) if cj in prot.index else np.nan,
                     "Path (km)": round(float(r.get("lcp_len_cells", np.nan)) * R.cell_km, 1) if pd.notna(r.get("lcp_len_cells")) else np.nan,
                     "Act": P.acts.get(eid, "")})
    df = pd.DataFrame(rows)
    if len(df):
        order = {c: i for i, c in enumerate(["both", "edge", "squeezed", "securing"])}
        df["_o"] = [order.get(P.cls.get(k), 9) for k in df["edge_id"]]
        df = df.sort_values(["_o", "Width ratio, tenth percentile"]).drop(columns="_o")
    df.to_csv(P.tab / "B_corridors.csv", index=False, encoding="utf-8-sig")
    print(f"B_corridors: {len(df)} corridor links, {int(df['Crosses unprotected land'].sum()) if len(df) else 0} crossing unprotected land -> {P.tab / 'B_corridors.csv'}")
    return df


def export_complexes_gis(P):
    """The complexes with Layer A attributes as a GeoPackage beside the corridor export."""
    if not P.contracted:
        return None
    out = P.gis; out.mkdir(parents=True, exist_ok=True)
    cols = [c for c in ("node_id", "name", "n_patches", "patch_ids", "area_km2", "pa_share", "ipca_added_share", "protected_share", "mean_ghm90max",
                        "n_slivers", "n_slivers_with_feature", "lat", "lon", "geometry") if c in P.nodes.columns]
    P.nodes[cols].rename(columns={"node_id": "complex_id"}).to_file(out / "complexes.gpkg", driver="GPKG")
    print(f"complexes.gpkg ({len(P.nodes)}) -> {out}")
    return out / "complexes.gpkg"


def _complex_of_edge(P, r):
    """(complex_i, complex_j) for an edge whose labels carry PATCH ids (v2.5) or complex ids."""
    R = P.R
    m2c = R.node_table.set_index("node_id")["complex_id"] if "complex_id" in getattr(R, "node_table", pd.DataFrame()).columns else None
    out = []
    for lab in (r["label_i"], r["label_j"]):
        nid = _node_id_of_label(P, lab)
        if nid is not None and m2c is not None and str(lab).split(" · ", 1)[-1].startswith("R"):
            nid = int(m2c.get(nid, nid))
        out.append(nid)
    return tuple(out)


def headline(P):
    """Run spec v3 §1a headline table -> tables/headline.json + .csv: complexes and share protected by act; corridor links and
    share crossing unprotected land; corridor land outside PAs, IPCAs and core; narrowing links by act; the last-affordable
    links by name with their tenth-percentile width ratio. Every number traced to a postprocess/ file."""
    R = P.R; e = R.edges
    g = P.nodes; acts = [_complex_act(P, c) for c in g["node_id"]]
    corr = list(P.cls.index[P.cls.isin(list(cc.CORRIDOR_CLASSES))])
    acc = getattr(R, "accounting", {}) or {}
    rows = []
    for a in getattr(P, "act_order", ACT_ORDER):
        sel = g[[x == a for x in acts]]
        if not len(sel):
            continue
        area = float(sel["area_km2"].sum())
        rows.append(dict(act=a, complexes=int(len(sel)), complex_area_km2=round(area),
                         share_in_pas=round(float((sel["area_km2"] * sel["pa_overlap_frac"]).sum() / area), 3),
                         share_with_ipcas=round(float((sel["area_km2"] * (sel["pa_overlap_frac"] + sel["ipca_added_share"])).sum() / area), 3),
                         share_in_core=round(float((sel["area_km2"] * sel["core_share"]).sum() / area), 3) if "core_share" in sel.columns else None,
                         corridor_links=int(sum(1 for k in corr if P.acts.get(k) == a)),
                         narrowing_links=int(sum(1 for k in corr if P.acts.get(k) == a and P.cls.get(k) in ("squeezed", "both"))),
                         last_affordable_links=int(sum(1 for k in corr if P.acts.get(k) == a and P.cls.get(k) in ("edge", "both")))))
    by_act = pd.DataFrame(rows)
    unp = [k for k in corr if float(e.loc[k].get("band_unprotected_km2", 0) or 0) > 0]
    last = [dict(edge_id=k, connects=" ↔ ".join(_short(P, c or 0) for c in _complex_of_edge(P, e.loc[k])), act=P.acts.get(k),
                 width_ratio_p10=(round(float(e.loc[k, "width_ratio_p10"]), 2) if pd.notna(e.loc[k].get("width_ratio_p10")) else None),
                 width_ratio_median=(round(float(e.loc[k, "squeeze_ratio_obs"]), 2) if pd.notna(e.loc[k].get("squeeze_ratio_obs")) else None),
                 alt_kind=e.loc[k].get("alt_kind"), n_branches=(int(e.loc[k, "n_branches"]) if pd.notna(e.loc[k].get("n_branches")) else None))
            for k in corr if P.cls.get(k) in ("edge", "both")]
    out = dict(run=R.run_id, n_complexes=int(len(g)), n_patches=int(g["n_patches"].sum()) if "n_patches" in g.columns else None,
               by_act=rows, n_corridor_links=len(corr), corridor_links_by_class={c: int((P.cls == c).sum()) for c in cc.CORRIDOR_CLASSES},
               n_corridor_links_crossing_unprotected=len(unp), share_crossing_unprotected=round(len(unp) / max(len(corr), 1), 3),
               corridor_land_dissolved_km2=acc.get("corridor_links_dissolved_km2"), corridor_land_outside_pas_ipcas_km2=acc.get("corridor_links_outside_pas_ipcas_km2"),
               corridor_land_outside_pas_ipcas_core_km2=acc.get("corridor_links_outside_pas_ipcas_core_km2"),
               all_bands_v2_km2=acc.get("all_bands_dissolved_km2"), near_contiguous_bands_inside_complexes_km2=acc.get("near_contiguous_bands_inside_complexes_km2"),
               fronts=(dict(n=int(len(R.fronts)), open=int((R.fronts.front_class == "open").sum()), cut=int(R.fronts.cut.sum()), area=acc.get("front_area"))
                       if getattr(R, "fronts", None) is not None else None),
               narrowing_by_act={r["act"]: r["narrowing_links"] for r in rows}, last_affordable=last, top_class_empty=bool((P.cls == "both").sum() == 0),
               n_secured_by_pa=int((P.secured_by == "pa").sum()), n_secured_by_ipca=int((P.secured_by == "ipca").sum()),
               cutoff_cost_units=float(R.cutoff), cutoff_detour_km=round(float(R.cutoff) * R.cell_km, 3),
               act_breaks_lat=list(STYLE["act_breaks_lat"]), act_note=getattr(P, "act_note", ""),
               sources=["postprocess/complexes.gpkg", "postprocess/coverage.csv", "postprocess/accounting.json", "corridor_edges.csv"])
    P.tab.mkdir(parents=True, exist_ok=True)
    (P.tab / "headline.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    by_act.to_csv(P.tab / "headline_by_act.csv", index=False, encoding="utf-8-sig")
    print(by_act.to_string(index=False))
    print(f"corridor links {len(corr)}: {len(unp)} cross unprotected land ({100*len(unp)/max(len(corr),1):.0f}%) | corridor land dissolved "
          f"{out['corridor_land_dissolved_km2']} km², outside PAs+IPCAs {out['corridor_land_outside_pas_ipcas_km2']}, outside PAs+IPCAs+core "
          f"{out['corridor_land_outside_pas_ipcas_core_km2']} | narrowing by act {out['narrowing_by_act']} | top class empty: {out['top_class_empty']}")
    for x in last:
        print(f"  last affordable: {x['connects']} ({x['act']}) p10 {x['width_ratio_p10']}, median {x['width_ratio_median']}, alt {x['alt_kind']}, branches {x['n_branches']}")
    return out



# ================= NODE LEVEL (run spec v3 §1a / §5 as revised 2026-09-29): the two tables, the headline, hypotheses, the §9 checklist =================
def _node_act(P, nid):
    return _complex_act(P, nid)


def table_nodes_v25(P):
    """§5 Nodes table: one row per refugia patch -- area, share in existing PAs, incremental share from proposed conservation areas, share in the
    prioritizr core, mean gHM (the 300 m human proxy), act, and its links by kind and class."""
    g = P.nodes
    df = pd.DataFrame({
        "Node": g["node_id"], "Name": g["name"], "Area (km²)": g["area_km2"].round(0).astype("Int64"),
        "Inside existing PAs (%)": (100 * g["pa_share"]).round(0).astype("Int64"),
        "Added by proposed conservation areas (%)": (100 * g["ipca_added_share"]).round(0).astype("Int64"),
        "In the prioritizr core (%)": (100 * g["core_share"]).round(0).astype("Int64"),
        "Outside PAs, IPCAs and core (%)": (100 * g["outside_all_share"]).round(0).astype("Int64"),
        "Mean human modification (gHM, 90 m max in cell)": g["mean_ghm90max"].round(3) if "mean_ghm90max" in g.columns else np.nan,
        "Links": g["n_links"], "Fronts": g["n_fronts"], "Strips": g["n_strips"],
        "Only viable": g.get("n_both", 0), "Last affordable": g.get("n_edge", 0), "Narrowing": g.get("n_squeezed", 0), "Options": g.get("n_securing", 0),
        "Act": [_node_act(P, n) for n in g["node_id"]], "lat": g["lat"].round(3), "lon": g["lon"].round(3)})
    df.to_csv(P.tab / "nodes_table.csv", index=False, encoding="utf-8-sig")
    print(f"nodes_table: {len(df)} refugia patches -> {P.tab / 'nodes_table.csv'}")
    return df


def table_links_v25(P):
    """§5 Links table: kind (front / strip), inter_cluster, class, D29 alternative kind, median and p10 width ratio, branches (strips
    only), lcp_max_cost, band land per link, share of the band outside PAs and IPCAs, W11 status, act."""
    R = P.R; e = R.edges
    ids = [k for k in P.cls.index if P.cls.get(k) in cc.CORRIDOR_CLASSES]
    rows = []
    for k in ids:
        r = e.loc[k]; a, b = _complex_of_edge(P, r)
        rows.append({"edge_id": k, "Connects": f"{_short(P, a or 0)} ↔ {_short(P, b or 0)}", "Kind": P.kind.get(k, "strip"),
                     "Inter-cluster": bool(r.get("inter_cluster", False)), "Class": cc.LINK_CLASS_LABEL.get(P.cls.get(k), P.cls.get(k)),
                     "Alternative link is": (r.get("alt_kind") if isinstance(r.get("alt_kind"), str) and r.get("alt_kind") else "—"),
                     "Width ratio, median": (round(float(r["squeeze_ratio_obs"]), 2) if pd.notna(r.get("squeeze_ratio_obs")) else np.nan),
                     "Width ratio, tenth percentile": (round(float(r["width_ratio_p10"]), 2) if pd.notna(r.get("width_ratio_p10")) else np.nan),
                     "Route branches (strips)": (int(r["n_branches"]) if P.kind.get(k) == "strip" and pd.notna(r.get("n_branches")) else pd.NA),
                     "Crossing class (max cost on the direct route)": (int(r["crossing_class"]) if pd.notna(r.get("crossing_class")) else pd.NA),
                     "Direct route": (r.get("crossing_note") if isinstance(r.get("crossing_note"), str) and r.get("crossing_note") else "all intact land"),
                     "Front cut (narrower than half the barrier-free width)": bool(r.get("front_cut", False)) if P.kind.get(k) == "front" else pd.NA,
                     "Band land (km², dissolved per link; links overlap)": round(float(r.get("band_new_km2", np.nan))) if pd.notna(r.get("band_new_km2")) else pd.NA,
                     "Outside PAs and IPCAs (km²)": round(float(r.get("band_unprotected_km2", np.nan))) if pd.notna(r.get("band_unprotected_km2")) else pd.NA,
                     "Already connected": {"pa": "within existing PAs", "ipca": "once the proposed conservation areas are realized", "": "no"}.get(P.secured_by.get(k, ""), ""),
                     "In the minimum network": bool(r.get("in_mst", False)), "Path (km)": round(float(r.get("lcp_len_cells", np.nan)) * R.cell_km, 1) if pd.notna(r.get("lcp_len_cells")) else pd.NA,
                     "Act": P.acts.get(k, "")})
    df = pd.DataFrame(rows)
    order = {c: i for i, c in enumerate(["both", "edge", "squeezed", "securing"])}
    df["_o"] = [order.get(P.cls.get(k), 9) for k in df["edge_id"]]; df["_k"] = [0 if P.kind.get(k) == "strip" else 1 for k in df["edge_id"]]
    df = df.sort_values(["_k", "_o", "Width ratio, tenth percentile"]).drop(columns=["_o", "_k"])
    df.to_csv(P.tab / "links_table.csv", index=False, encoding="utf-8-sig")
    print(f"links_table: {len(df)} links ({int((df.Kind == 'strip').sum())} strips, {int((df.Kind == 'front').sum())} fronts) -> {P.tab / 'links_table.csv'}")
    return df


def headline_v25(P):
    """§5 / §8 headline statistics -> tables/headline.json + headline_by_act.csv: links by kind and class by act; node area protected by
    act; strips crossing unprotected land; corridor land outside PAs, IPCAs and core; fronts by class with front area on its own line;
    narrowing links by act; the four last-affordable strips by name with p10. Every number traced to postprocess/ files."""
    R = P.R; e = R.edges; g = P.nodes; acc = getattr(R, "accounting", {}) or {}
    acts_n = [_node_act(P, n) for n in g["node_id"]]
    ids = [k for k in P.cls.index if P.cls.get(k) in cc.CORRIDOR_CLASSES]
    strips = [k for k in ids if P.kind.get(k) == "strip"]; fronts = [k for k in ids if P.kind.get(k) == "front"]
    rows = []
    for a in getattr(P, "act_order", ACT_ORDER):
        sel = g[[x == a for x in acts_n]]; area = float(sel["area_km2"].sum()) if len(sel) else 0.0
        row = dict(act=a, nodes=int(len(sel)), node_area_km2=round(area),
                   node_share_in_pas=round(float((sel["area_km2"] * sel["pa_share"]).sum() / area), 3) if area else None,
                   node_share_with_ipcas=round(float((sel["area_km2"] * (sel["pa_share"] + sel["ipca_added_share"])).sum() / area), 3) if area else None,
                   node_share_in_core=round(float((sel["area_km2"] * sel["core_share"]).sum() / area), 3) if area else None)
        for kind, lst in (("strips", strips), ("fronts", fronts)):
            for c in cc.CORRIDOR_CLASSES:
                row[f"{kind}_{c}"] = int(sum(1 for k in lst if P.acts.get(k) == a and P.cls.get(k) == c))
            row[f"{kind}_total"] = int(sum(1 for k in lst if P.acts.get(k) == a))
        row["narrowing_links"] = int(sum(1 for k in ids if P.acts.get(k) == a and P.cls.get(k) in ("squeezed", "both")))
        rows.append(row)
    by_act = pd.DataFrame(rows)
    unp = [k for k in strips if float(e.loc[k].get("band_unprotected_km2", 0) or 0) > 0]
    last = [dict(edge_id=k, connects=" ↔ ".join(_short(P, c or 0) for c in _complex_of_edge(P, e.loc[k])), act=P.acts.get(k),
                 width_ratio_p10=(round(float(e.loc[k, "width_ratio_p10"]), 2) if pd.notna(e.loc[k].get("width_ratio_p10")) else None),
                 width_ratio_median=(round(float(e.loc[k, "squeeze_ratio_obs"]), 2) if pd.notna(e.loc[k].get("squeeze_ratio_obs")) else None),
                 alt_kind=e.loc[k].get("alt_kind"), n_branches=(int(e.loc[k, "n_branches"]) if pd.notna(e.loc[k].get("n_branches")) else None))
            for k in strips if P.cls.get(k) in ("edge", "both")]
    out = dict(run=R.run_id, level="node", n_nodes=int(len(g)), n_links=len(ids), n_strips=len(strips), n_fronts=len(fronts),
               strips_by_class={c: int(sum(1 for k in strips if P.cls.get(k) == c)) for c in cc.CORRIDOR_CLASSES},
               fronts_by_class={c: int(sum(1 for k in fronts if P.cls.get(k) == c)) for c in cc.CORRIDOR_CLASSES},
               fronts_cut=int(e.loc[fronts, "front_cut"].fillna(False).astype(bool).sum()) if "front_cut" in e.columns and fronts else 0,
               n_strips_crossing_unprotected=len(unp), share_strips_crossing_unprotected=round(len(unp) / max(len(strips), 1), 3),
               corridor_land_dissolved_km2=acc.get("corridor_land_dissolved_km2"), strip_land=acc.get("strips"), front_land=acc.get("fronts"),
               corridor_land_outside_pas_ipcas_km2=acc.get("corridor_land_outside_pas_ipcas_km2"), corridor_land_outside_pas_ipcas_core_km2=acc.get("corridor_land_outside_pas_ipcas_core_km2"),
               d25b_identity=acc.get("d25b_identity"), branches=acc.get("branches"),
               narrowing_by_act={r["act"]: r["narrowing_links"] for r in rows}, last_affordable_strips=last,
               top_class_empty_among_strips=bool(sum(1 for k in strips if P.cls.get(k) == "both") == 0),
               n_secured_by_pa=int((P.secured_by == "pa").sum()), n_secured_by_ipca=int((P.secured_by == "ipca").sum()),
               cutoff_cost_units=float(R.cutoff), cutoff_detour_km=round(float(R.cutoff) * R.cell_km, 3), act_breaks_lat=list(STYLE["act_breaks_lat"]), act_note=getattr(P, "act_note", ""),
               sources=["postprocess/links_v25.csv", "postprocess/nodes_v25.csv", "postprocess/coverage.csv", "postprocess/accounting.json", "corridor_edges.csv"])
    P.tab.mkdir(parents=True, exist_ok=True)
    (P.tab / "headline.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str)); by_act.to_csv(P.tab / "headline_by_act.csv", index=False, encoding="utf-8-sig")
    print(by_act.to_string(index=False))
    print(f"strips {len(strips)}: {out['strips_by_class']} | {len(unp)} cross unprotected land ({100*out['share_strips_crossing_unprotected']:.0f}%) | fronts {len(fronts)}: {out['fronts_by_class']}, cut {out['fronts_cut']} | "
          f"corridor land dissolved {out['corridor_land_dissolved_km2']} km²; strips {acc.get('strips', {}).get('dissolved_union_km2')} (outside PAs+IPCAs {acc.get('strips', {}).get('outside_pas_ipcas_km2')}, +core {acc.get('strips', {}).get('outside_pas_ipcas_core_km2')}); "
          f"fronts {acc.get('fronts', {}).get('dissolved_union_km2')} | top class empty among strips: {out['top_class_empty_among_strips']}")
    for x in last:
        print(f"  last affordable strip: {x['connects']} ({x['act']}) p10 {x['width_ratio_p10']}, median {x['width_ratio_median']}, alt {x['alt_kind']}, branches {x['n_branches']}")
    return out


def hypotheses_v25(P):
    """§7 H-W1..H-W7 at node level, confirmed / refuted from the record; H-W5 / H-W6 wait for section 6."""
    R = P.R; e = R.edges; g = P.nodes
    ids = [k for k in P.cls.index if P.cls.get(k) in cc.CORRIDOR_CLASSES]; strips = [k for k in ids if P.kind.get(k) == "strip"]; fronts = [k for k in ids if P.kind.get(k) == "front"]
    cut = e["front_cut"].fillna(False).astype(bool) if "front_cut" in e.columns else pd.Series(False, index=e.index)
    rows = []
    n_open = sum(1 for k in fronts if not cut.get(k, False))
    rows.append(("H-W1", f"fronts {len(fronts)} of {len(ids)} links ({100*len(fronts)/max(len(ids),1):.0f}%); open fronts {n_open} of {len(fronts)}",
                 "confirmed" if len(fronts) > len(ids) / 2 and n_open > len(fronts) / 2 else "REFUTED (reported as measured)"))
    v2 = e["link_class_v2"] if "link_class_v2" in e.columns else e["link_class"]
    la_v2 = [k for k in strips if v2.get(k) in ("edge", "both")]; la_now = [k for k in strips if P.cls.get(k) in ("edge", "both")]
    rows.append(("H-W2", f"last-affordable strips v2 {len(la_v2)} -> now {len(la_now)} (same set: {set(la_v2) == set(la_now)}); top class among strips {sum(1 for k in strips if P.cls.get(k) == 'both')}",
                 "confirmed" if set(la_v2) == set(la_now) and sum(1 for k in strips if P.cls.get(k) == "both") == 0 else "reported as measured"))
    narrow = {a: sum(1 for k in strips if P.acts.get(k) == a and P.cls.get(k) in ("squeezed", "both")) for a in getattr(P, "act_order", ACT_ORDER)}
    rows.append(("H-W3", f"narrowing strips by act {narrow}", "confirmed" if narrow.get("north", 0) == 0 and narrow.get("south", 0) >= max(narrow.values() or [0]) else "REFUTED (reported as measured)"))
    unp = sum(1 for k in strips if float(e.loc[k].get("band_unprotected_km2", 0) or 0) > 0)
    south = g[g["lat"] < float(min(STYLE["act_breaks_lat"]))]; s_share = float((south["area_km2"] * south["pa_share"]).sum() / max(south["area_km2"].sum(), 1e-9)) if len(south) else np.nan
    rows.append(("H-W4", f"{unp} of {len(strips)} strips cross unprotected land; node area south of {min(STYLE['act_breaks_lat'])} N inside PAs {100*s_share:.0f}%",
                 "confirmed" if (len(strips) and unp / len(strips) > 0.5 and s_share > 0.5) else "partial / REFUTED (reported as measured)"))
    rows.append(("H-W5", "section 6 not run (parked)", "n/a")); rows.append(("H-W6", "section 6 not run (parked)", "n/a"))
    if "cluster_i" in e.columns and fronts:
        d7 = e.loc[fronts]; d7 = d7[d7["link_class"].isin(["edge", "both"])]
        per = d7.groupby("cluster_i").size().sort_values(ascending=False)
        rows.append(("H-W7", f"D7-driven front classes {len(d7)} of {len(fronts)} fronts, in {len(per)} front-subgraph components (largest {per.head(3).to_dict()})",
                     "reported (motivates the parked ecosystem-level D7 reading)"))
    df = pd.DataFrame(rows, columns=["id", "measured", "verdict"]); df.to_csv(P.tab / "hypotheses.csv", index=False, encoding="utf-8-sig")
    print(df.to_string(index=False))
    return df


def checklist_v25(P, extra=None):
    """§9 at node level -> tables/validation_checklist.csv."""
    R = P.R; e = R.edges; rec = R.cfg; git = getattr(R, "rec", {}).get("git", {}) if hasattr(R, "rec") else {}; acc = getattr(R, "accounting", {}) or {}; extra = extra or {}
    ids = [k for k in P.cls.index if P.cls.get(k) in cc.CORRIDOR_CLASSES]; fronts = [k for k in ids if P.kind.get(k) == "front"]; strips = [k for k in ids if P.kind.get(k) == "strip"]
    rows = []
    def add(item, ok, evidence):
        rows.append(dict(item=item, ok=(None if ok is None else bool(ok)), evidence=evidence))
    add("run record on a clean tree", (not git.get("dirty", True)) if git else None, f"git {git.get('sha', '')[:8]} dirty={git.get('dirty')} (v2_run001 was dirty; disclosed)")
    add("pins in the record", all(k in rec for k in ("cwd_cutoff_abs", "cutoff_detour_km", "beta", "width_floor_cells", "len_floor_cells", "near_opt_tiers")),
        f"node_min_km2 {rec.get('nodes', {}).get('node_min_km2')}, cutoff {rec.get('cwd_cutoff_abs')} = {rec.get('cutoff_detour_km')} km, beta {rec.get('beta')}, floors {rec.get('width_floor_cells')}/{rec.get('len_floor_cells')}")
    add("variant reconciles by layer of origin", extra.get("variant_ok"), extra.get("variant_note", "the variant meta (notebook 01 / 02)"))
    add("RGI 7.0 vs CanVec ice difference recorded", extra.get("ice_ok"), extra.get("ice_note", "not computed (CanVec not on disk)"))
    unass = e.loc[fronts, "width_not_assessable"].fillna(False).astype(bool).sum() if "width_not_assessable" in e.columns else 0
    ok23 = (unass == 0) and e.loc[fronts, "squeeze_ratio_obs"].notna().all() and e.loc[fronts, "crossing_class"].notna().all() if fronts else True
    fc = {c: int(sum(1 for k in fronts if P.cls.get(k) == c)) for c in cc.CORRIDOR_CLASSES}
    add("front check (G23): D24 floor, width ratio + crossing_class non-null, class counts sum", ok23 and sum(fc.values()) == len(fronts), f"{len(fronts)} fronts; not assessable {int(unass)}; classes {fc} (sum {sum(fc.values())})")
    ident = acc.get("d25b_identity", {})
    add("area identity: MST strips + MST fronts + augmentation = total (per-link sums); union dissolved", bool(ident.get("reconciles")), f"{ident} | corridor union {acc.get('corridor_land_dissolved_km2')} km²")
    br = acc.get("branches", {})
    add("branch arithmetic reconciles", bool(br.get("reconciles")), f"{br}")
    ok_names = all(_node_id_of_label(P, e.loc[k, c]) in set(P.nodes.node_id) for k in ids for c in ("label_i", "label_j"))
    add("link names map to node ids (post two-digit fix)", ok_names, f"{len(ids)} links parsed")
    add("act assignment: Banff-Yoho / Bow Valley in one act", extra.get("bow_ok"), extra.get("bow_note", "run wd.bow_valley_check"))
    add("section 6 table (when run)", None, "parked"); add("glacier sensitivities (when run)", None, "parked")
    add("every statistic traced to a file", (P.tab / "headline.json").exists(), "tables/headline.json lists its sources")
    df = pd.DataFrame(rows); df.to_csv(P.tab / "validation_checklist.csv", index=False, encoding="utf-8-sig")
    print(df.to_string(index=False))
    return df
