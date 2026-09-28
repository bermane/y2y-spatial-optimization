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
    k_close_per_act=2, k_open_per_act=1, max_examples=7,   # automatic example selection
    act_pad_km=40, act_min_km=450,                          # act windows
    act_breaks_lat=(58.5, 51.0),                            # north >= 58.5 N, central 51-58.5, south < 51 (fallback: terciles)
    towns_full=["Whitehorse", "Fort St. John", "Prince George", "Calgary", "Missoula", "Jackson"],
    withheld_colours={"elevation_gt_2300_m": "#1B9E77", "slope_gt_30_deg": "#7570B3", "glacier": "#80B1D3"},
    endpoint_protected_frac=0.5,                            # a node counts as 'protected' when PAs cover >= this share
    # W11 -- how protected land (existing PAs + proposed IPCAs, taken as given) enters the maps:
    #   "overlay":          draw every corridor band in full; hatch the protected land on top; links already
    #                       connected within protected land ('satisfied') drawn muted and labelled
    #   "unprotected_only": draw only the corridor land still to secure; satisfied links omitted
    protected_mode="overlay",
    satisfied_alpha=0.45,                                   # fill alpha for satisfied links in overlay mode
    satisfied_outline={"pa": "#4D4D4D", "ipca": "#3E6F70"}, # outline colour of a satisfied link: by existing PAs / by proposed IPCAs
    protected_hatch={"pa": "///", "ipca": "\\\\"},             # PA hatch vs IPCA hatch over the bands
    protected_hatch_colour={"pa": "#4D4D4D", "ipca": "#3E6F70"}, protected_hatch_lw=0.5,
)

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
EXAMPLE_PICKS = []          # same schema as corridors_director.EXAMPLE_PICKS; non-empty = override the automatic rule
ACT_ORDER = ["north", "central", "south"]


# ================= package context =================
def package(R, out=None, picks=None):
    """Assemble everything the figures need from a loaded run (cc.load_results): the disjoint
    pressure classes, the owner partition, the node table with names and PA overlap, the
    refugia classes, the PA context, jurisdictions, acts and the example selection."""
    assert getattr(R, "refugia", None) is not None, "this run has no refugia classes -- not a raster-node run"
    P = SimpleNamespace(R=R, out=pathlib.Path(out) if out else R.run_dir / PKG_SUB)
    P.fig, P.tab, P.gis = P.out / "figures", P.out / "tables", P.out / "gis"
    for d in (P.fig, P.tab, P.gis):
        d.mkdir(parents=True, exist_ok=True)
    e, classes = cc._routing_classes(R)
    P.edges = e
    P.h8_open = not ("squeezed" in R.edges.columns and R.edges["squeezed"].notna().any())
    both, irr, sq = classes[0][1], classes[1][1], classes[2][1]
    cls = pd.Series("securing", index=e.index)
    cls[sq] = "squeezed"; cls[irr] = "edge"; cls[both] = "both"
    cls[e["is_adjacency"] | (e["cost"] <= 0)] = "adjacency"
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
    print(f"wolverine package: classes -> both {n.get('both', 0)} · edge {n.get('edge', 0)} · squeezed {n.get('squeezed', 0)} "
          f"· securing {n.get('securing', 0)} | {len(P.nodes)} nodes | {len(P.examples)} examples | "
          f"H8 {'OPEN -- squeezed withheld' if P.h8_open else 'closed'} | already connected: {int((P.secured_by == 'pa').sum())} "
          f"within existing PAs, {int((P.secured_by == 'ipca').sum())} only with the proposed IPCAs (mode '{STYLE['protected_mode']}')")
    return P


def _node_table(R):
    """One row per node: geometry from node_parts.gpkg, names from the run's node_names.csv
    (display_name if filled, else the auto-name), number = node_id (north -> south)."""
    g = gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(R.crs)
    if "node_id" not in g.columns:
        g["node_id"] = np.arange(1, len(g) + 1)
    g = g.sort_values("node_id").reset_index(drop=True)
    nt = getattr(R, "node_table", None)
    if nt is not None:
        nt = nt.copy(); nt["display_name"] = nt["display_name"].astype(str).str.strip()
        nt["name"] = np.where(nt["display_name"] != "", nt["display_name"], nt["label_auto"])
        keep = [c for c in ("node_id", "name", "label_auto", "area_km2", "n_cells", "lat", "lon",
                            "pa_overlap_name", "pa_overlap_frac", "nearest_pa", "nearest_pa_km", "bearing", "share_north_model") if c in nt.columns]
        g = g.drop(columns=[c for c in keep if c in g.columns and c != "node_id"], errors="ignore").merge(nt[keep], on="node_id", how="left")
    if "name" not in g.columns:
        g["name"] = [cc._short_node_name(n, 40) for n in g.name_label]
    g["short"] = [cc._short_node_name("X · " + str(n), 22) for n in g["name"]]
    g["core_km2"] = g["area_km2"]
    return g


def _short(P, node_id):
    r = P.nodes[P.nodes.node_id == int(node_id)]
    return str(r.iloc[0]["short"]) if len(r) else f"R{int(node_id):02d}"


def _node_id_of_label(P, label):
    """'Refugium · R12 name' -> 12."""
    s = str(label).split(" · ", 1)[-1]
    if s.startswith("R") and s[1:3].isdigit():
        return int(s[1:3])
    return None


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
    n_br, s_br = STYLE["act_breaks_lat"]
    act = pd.Series(np.where(lat >= n_br, "north", np.where(lat >= s_br, "central", "south")), index=lat.index).where(lat.notna())
    counts = act.value_counts()
    if any(counts.get(a, 0) < 5 for a in ACT_ORDER):
        q = lat.dropna().quantile([1 / 3, 2 / 3]).values
        act = pd.Series(np.where(lat >= q[1], "north", np.where(lat >= q[0], "central", "south")), index=lat.index).where(lat.notna())
        print(f"  acts: a fixed latitude band held < 5 edges -> node-latitude terciles ({q[0]:.1f} N, {q[1]:.1f} N)")
    P.edge_lat = lat
    return act


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
            eid = cd._find_edge(e, pk["pair"])
            chosen.append(dict(edge_id=eid, act=pk.get("act"), slot=pk.get("slot", ""), kind="pinned"))
    else:
        for act in ACT_ORDER:
            ids = [k for k in e.index if P.acts.get(k) == act and not bool(P.secured.get(k, False))]   # W11: satisfied links are never examples
            sub = e.loc[ids]
            close = []
            for c, keys in (("both", ["n_pairs_lost", "backup_ratio"]), ("edge", ["backup_ratio"]), ("squeezed", ["squeeze_ratio_obs"])):
                cand = sub[P.cls.loc[ids] == c]
                if not len(cand):
                    continue
                asc = c == "squeezed"
                cand = cand.sort_values([k for k in keys if k in cand.columns], ascending=asc)
                close += [dict(edge_id=k, act=act, slot=f"{act[0].upper()}-close", kind=c) for k in cand.index]
            chosen += close[:STYLE["k_close_per_act"]]
            sec = sub[(P.cls.loc[ids] == "securing")]
            if "n_branches" in sec.columns and len(sec):
                sec = sec[sec["n_branches"] >= 2].sort_values("n_branches", ascending=False)
                chosen += [dict(edge_id=k, act=act, slot=f"{act[0].upper()}-open", kind="securing") for k in sec.index[:STYLE["k_open_per_act"]]]
    # de-duplicate, cap, number north -> south by the latitude of the owned land
    seen, ex = set(), []
    for x in chosen:
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
                ha="left", va="top", family="monospace")


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
                     f"Already connected once the proposed IPCAs are realized  [{n_ip}]"))
        rows.append((Patch(facecolor="none", edgecolor=STYLE["protected_hatch_colour"]["pa"], hatch=STYLE["protected_hatch"]["pa"], linewidth=0.5),
                     "Existing protected areas"))
        rows.append((Patch(facecolor="none", edgecolor=STYLE["protected_hatch_colour"]["ipca"], hatch=STYLE["protected_hatch"]["ipca"], linewidth=0.5),
                     "Proposed IPCAs / PAs (taken as given)"))
    else:
        rows.append((Patch(facecolor="white", edgecolor=ms.AREA["pa_outline"]["edge"], linewidth=0.5),
                     f"Corridor land inside protected areas is not drawn; omitted links already connected: {n_pa} within existing PAs, "
                     f"{n_ip} once the proposed IPCAs are realized"))
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
    ms.legend(ns.legend, [(ms.CLASS_HEADING, _class_legend(counts)),
                          ("Protection Status", _protection_legend(P, counts)),
                          ("Wolverine Refugia", [ms.area_handle("refugia_core")] + ([ms.area_handle("refugia_marginal")] if STYLE["w1_marginal"] else [])),
                          ("Nodes And Examples", [_node_handle(), (Patch(facecolor="white", edgecolor=ms.CLASS["both"][0]), "Numbered example links (see the table)")]),
                          ("Context", _context_rows(P))])
    _node_key(P, ns.key)
    fig.canvas.draw(); ms.scale_north(ns.scale, ax, fig, km=STYLE["scale_km_full"])
    n_irr = int((P.cls == "both").sum() + (P.cls == "edge").sum())
    n_pa, n_ip = int((P.secured_by == "pa").sum()), int((P.secured_by == "ipca").sum())
    unp = float(P.corridor_unprotected.sum()) * R.cell_km2; tot = float(R.corridor.sum()) * R.cell_km2
    cap = (f"Least-cost corridor bands between {len(P.nodes)} core refugia patches on the withheld-terrain surface (β = "
           f"{R.cfg.get('beta')}, band = {R.cutoff:.1f} cost units ≈ 4 km detour). {len(P.edges)} links, {n_irr} with no "
           f"affordable alternative (D7 / D12); already connected: {n_pa} within existing PAs, {n_ip} once the proposed IPCAs are "
           f"realized; {unp:,.0f} of {tot:,.0f} km² of corridor land lies outside PAs and proposed IPCAs. " + ("Squeezed class pending the counterfactual (H8 open). " if P.h8_open else "")
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
    ms.legend(ns.legend, [(ms.CLASS_HEADING, _class_legend(counts)),
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
    ids = [_node_id_of_label(P, r["label_i"]), _node_id_of_label(P, r["label_j"])]
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
                  "already connected once the proposed IPCAs are realized" if by == "ipca" else
                  ("partly protected" if pd.notna(cpf) and cpf > 0 else "unprotected"))
        rows.append({
            "#": (nums or {}).get(eid, ""),
            "Connects": f"{_short(P, _node_id_of_label(P, r['label_i']) or 0)} ↔ {_short(P, _node_id_of_label(P, r['label_j']) or 0)}",
            "Pressure": ms.CLASS[c][3] if c in ms.CLASS else c,
            "Protection status": status,
            "Route inside existing PAs (%)": (f"{100*cpa:.0f}" if pd.notna(cpa) else "—"),
            "Route inside proposed IPCAs only (%)": (f"{100*cpi:.0f}" if pd.notna(cpi) else "—"),
            "Corridor land to secure (km²)": round(float(r.get("band_unprotected_km2", band - prot))),
            "Room to move (route branches)": int(r.get("n_branches", 0) or 0),
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
        fonts="Noto Sans (input_data/basemap/fonts)", type=ms.TYPE,
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
