"""Wolverine refugia corridors -- v2.5 post-processing (run spec v3 §1a, Ethan 2026-09-28; revised 2026-09-29).

TWO MODES over one set of functions.
  Patch mode (notebook 05, `load`): reads the finished patch-level run (`v2_run001`) and DERIVES the refugia complexes --
  connected components of the 130 near-contiguous D25 links -- the D-W7 names, the within-complex sliver table (the v2 links'
  only use: they are not reported), and writes the AUDIT OBJECTS the engine's contraction loader reads (`complex_membership.csv`,
  `complex_names.csv`, `complexes.gpkg`, `slivers_v2.csv`, `complexes_summary.json`, git-tracked) plus `postprocess/` copies.
  Run mode (notebook 07, `load_run`): reads the CONTRACTED run (`v25_run001`, routed between the complex unions by notebook 06)
  and computes the product on ITS inter-complex links: the coverage columns (existing PAs / proposed IPCAs incremental / the
  prioritizr balanced core on allocatable land) with an area-expectation row, the band-land accounting (dissolved unions beside
  per-link sums; branches as links-with-n) -> `<run>/postprocess/`; `attach(R)` hands it to the package (`wolverine_director`).
No baseline run, no glacier sensitivities (run spec v3 §6 = the next step).
"""
import json
import pathlib
import re

import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import rioxarray
from rasterio.enums import Resampling
from rasterio.features import rasterize
from types import SimpleNamespace

import config
import corridors_core as cc

PP_SUB = "postprocess"
CORE_TIF = config.PROJECT_DIR / "analyses" / "y2y" / "director_package" / "geotiffs" / "f_balanced_core.tif"
CORE_THRESHOLD = 0.70          # the balanced scenario's guarded tier (package spec v2.1; summary.json threshold)
CORE_PA_MASK = config.HANDOFF_DIR / "mask_protected_areas.tif"     # the flagship's locked PAs (f = 1 by construction) -- the core is the
CORE_KM2_EXPECTED = 51580       # tier on ALLOCATABLE land: (f >= 0.70) & ~locked = 51,580 km2 (summary.json frequent_km2.guarded)
GENERIC = {"park", "parks", "provincial", "national", "reserve", "of", "canada", "wilderness", "area", "areas", "protected",
           "conservancy", "conservation", "ecological", "recreation", "state", "forest", "corridor", "wildland", "wildlife",
           "management", "natural", "environment", "monument", "the", "and", "tribal"}


def label_num(label):
    """'Refugium · R108 name' -> 108, 'Complex · C03 name' -> 3 (any width)."""
    m = re.match(r"[RC](\d+)(?:\s|$)", str(label).split(" · ", 1)[-1])
    return int(m.group(1)) if m else None


def refugium_name(base, bearing=None, multi=False):
    """D-W7: named as refugia, never as the nearest park -- 'Refugium (Sustut)', 'Refugia complex (Nahanni)'."""
    words = [w for w in str(base).split(" (")[0].split(" - ")[0].split() if w.lower().strip(",") not in GENERIC]
    core = " ".join(words) or str(base)
    if bearing:
        core = f"{core}, {bearing}"
    return f"{'Refugia complex' if multi else 'Refugium'} ({core})"


def _base(row, pa_overlap_min=0.10):
    by_pa = pd.notna(row.get("pa_overlap_name")) and str(row.get("pa_overlap_name")) not in ("", "nan") and \
        float(row.get("pa_overlap_frac", 0) or 0) >= pa_overlap_min
    return (row["pa_overlap_name"], None) if by_pa else (row["nearest_pa"], row.get("bearing"))


# ================= load =================
def load(run_dir):
    """The v2 record as one namespace: the loaded results (cc.load_results) + the vectors and tables the product needs."""
    run_dir = pathlib.Path(run_dir)
    R = cc.load_results(run_dir)
    P0 = SimpleNamespace(R=R, run_dir=run_dir, out=run_dir / PP_SUB)
    P0.out.mkdir(parents=True, exist_ok=True)
    P0.edges = pd.read_csv(run_dir / "corridor_edges.csv", encoding="utf-8-sig")
    eid_col = "edge_id" if "edge_id" in P0.edges.columns else P0.edges.columns[0]
    P0.edges = P0.edges.rename(columns={eid_col: "edge_id"}).set_index("edge_id")
    P0.edges["i_id"] = [label_num(x) for x in P0.edges["label_i"]]
    P0.edges["j_id"] = [label_num(x) for x in P0.edges["label_j"]]
    assert P0.edges["i_id"].notna().all() and P0.edges["j_id"].notna().all(), "edge labels did not parse to node ids"
    P0.nodes = pd.read_csv(run_dir / "node_names.csv", encoding="utf-8-sig").fillna({"display_name": ""})
    P0.node_parts = gpd.read_file(run_dir / "node_parts.gpkg").to_crs(R.crs)
    P0.bands = gpd.read_file(run_dir / "corridor_edges.gpkg", layer="bands").to_crs(R.crs).set_index("edge_id")
    P0.centrelines = gpd.read_file(run_dir / "corridor_edges.gpkg", layer="centrelines").to_crs(R.crs).set_index("edge_id")
    P0.branches = pd.read_csv(run_dir / "branches.csv", encoding="utf-8-sig") if (run_dir / "branches.csv").exists() else None
    P0.rec = json.loads((run_dir / "run_config.json").read_text())
    nz = (P0.edges["cost"] > 0) & (~P0.edges["is_adjacency"].astype(bool))
    P0.adjacent = P0.edges[nz & P0.edges["near_contiguous"].astype(bool)]
    P0.corridor = P0.edges[nz & ~P0.edges["near_contiguous"].astype(bool)]
    P0.cell_km2, P0.cell_km = R.cell_km2, R.cell_km
    P0.node_id = np.nan_to_num(R.node_id.values, nan=0).astype(int)
    P0.pu = np.isfinite(R.resistance.values) & (R.resistance.values > 0)
    P0.node_land = R.pa_mask | R.anch
    print(f"{R.run_id}: {len(P0.nodes)} patches, {len(P0.edges)} links = {len(P0.adjacent)} near-contiguous + {len(P0.corridor)} corridor links "
          f"(+ {int((~nz).sum())} adjacency/zero-cost) | cutoff {R.cutoff:.4f} = {R.cutoff * R.cell_km:.2f} km detour")
    return P0


# ================= 1. complexes =================
def complexes(P0):
    """Connected components of the near-contiguous links -> complex_id per patch (numbered north -> south by the
    cell-weighted centroid), dissolved polygons, complex_id.tif. Single patches are complexes."""
    nd = P0.nodes.set_index("node_id")
    G = nx.Graph(); G.add_nodes_from(int(n) for n in nd.index)
    G.add_edges_from((int(a), int(b)) for a, b in zip(P0.adjacent["i_id"], P0.adjacent["j_id"]))
    comps = [sorted(c) for c in nx.connected_components(G)]

    def _lat(c):
        w = nd.loc[c, "n_cells"].values.astype(float); return float((nd.loc[c, "lat"].values * w).sum() / w.sum())
    comps.sort(key=lambda c: -_lat(c))
    rows, mem = [], []
    for k, c in enumerate(comps, start=1):
        sub = nd.loc[c]; w = sub["n_cells"].values.astype(float)
        big_id = int(sub["n_cells"].idxmax()); big = sub.loc[big_id]
        rows.append(dict(complex_id=k, n_patches=len(c), patch_ids=" ".join(str(int(x)) for x in c), largest_patch=big_id,
                         largest_patch_name=str(big["name"]) if "name" in sub.columns else str(big["label_auto"]),
                         area_km2=round(float(sub["area_km2"].sum()), 1), n_cells=int(sub["n_cells"].sum()),
                         lat=round(float((sub["lat"].values * w).sum() / w.sum()), 4), lon=round(float((sub["lon"].values * w).sum() / w.sum()), 4)))
        for nid in c:
            mem.append(dict(node_id=int(nid), complex_id=k))
    mem = pd.DataFrame(mem).sort_values("node_id"); cx = pd.DataFrame(rows)
    # names (D-W7): from the largest patch, designation words stripped; duplicates numbered
    seen = {}
    names = []
    for r in cx.itertuples():
        base, bearing = _base(nd.loc[r.largest_patch])
        nm = refugium_name(base, bearing, multi=r.n_patches > 1)
        if nm in seen:
            seen[nm] += 1; nm = nm[:-1] + f", {seen[nm]})"
        else:
            seen[nm] = 1
        names.append(nm)
    cx["name_auto"] = names; cx["name"] = names
    # geometry
    g = P0.node_parts.copy(); g["complex_id"] = g["node_id"].map(mem.set_index("node_id")["complex_id"])
    assert g["complex_id"].notna().all()
    geo = g.dissolve(by="complex_id", aggfunc={"area_km2": "sum"}).reset_index()[["complex_id", "geometry"]]
    cx = gpd.GeoDataFrame(cx.merge(geo, on="complex_id"), geometry="geometry", crs=P0.R.crs)
    # the complex_id grid from node_id.tif
    lut = np.zeros(int(P0.node_id.max()) + 1, np.int16)
    for r in mem.itertuples():
        lut[r.node_id] = r.complex_id
    cid = lut[P0.node_id]
    P0.complex_id = cid
    rioxarray.open_rasterio(P0.run_dir / "node_id.tif").squeeze().copy(data=cid).rio.write_nodata(0).rio.to_raster(
        P0.out / "complex_id.tif", compress="DEFLATE", tiled=True)
    mem.to_csv(P0.out / "node_complex.csv", index=False, encoding="utf-8-sig")
    P0.mem, P0.cx = mem, cx
    # checks (spec §9 contraction lines that apply without routing)
    assert set(mem.node_id) == set(int(x) for x in nd.index) and mem.node_id.is_unique
    assert abs(float(cx["area_km2"].sum()) - float(nd["area_km2"].sum())) < 1.0, "complex areas do not sum to the patch total"
    bp = cx.loc[cx.n_patches.idxmax()]; ba = cx.loc[cx.area_km2.idxmax()]
    print(f"complexes: {len(cx)} ({int((cx.n_patches == 1).sum())} single-patch; most patches {bp['name']} {int(bp.n_patches)}; largest "
          f"{ba['name']} {float(ba.area_km2):,.0f} km²) from {len(P0.adjacent)} near-contiguous links; complex land = patch total {float(cx.area_km2.sum()):,.0f} km²")
    return mem, cx


# ================= 2. corridor links =================
def corridor_links(P0):
    m2c = P0.mem.set_index("node_id")["complex_id"]
    c = P0.corridor.copy()
    c["complex_from"] = c["i_id"].map(m2c).astype(int); c["complex_to"] = c["j_id"].map(m2c).astype(int)
    c["inter_complex"] = c["complex_from"] != c["complex_to"]
    intra = c[~c["inter_complex"]]
    # run spec v3 §1a item 2: a corridor-class link with both ends in one complex is a WITHIN-complex link that the D25 rule did not
    # call a sliver (its path is longer than its barrier-free width): reported, listed with the slivers, never drawn as a corridor
    c["pair"] = [f"C{min(a, b)}-C{max(a, b)}" for a, b in zip(c["complex_from"], c["complex_to"])]
    inter = c[c["inter_complex"]]
    mult = inter["pair"].value_counts()
    c["links_on_pair"] = c["pair"].map(mult).where(c["inter_complex"])
    P0.links_all, P0.links, P0.intra_links = c, inter, intra
    multi = mult[mult > 1]
    print(f"corridor-class links: {len(c)} = {len(inter)} INTER-complex (between {inter['pair'].nunique()} complex pairs; pairs joined by more than one link: "
          f"{len(multi)}" + (f" -> {multi.to_dict()}" if len(multi) else "") + f") + {len(intra)} WITHIN one complex"
          + (f" ({', '.join(f'{k}: C{int(v)} {c.loc[k, 'link_class']}' for k, v in intra['complex_from'].items())}) -- listed with the slivers, not mapped" if len(intra) else ""))
    return c


# ================= 3. coverage =================
def _core300(P0):
    """The prioritizr balanced core on the 300 m routing grid (nearest): the balanced scenario's guarded tier on ALLOCATABLE land =
    (f >= 0.70 on the 1 km package layer) & ~(the flagship's locked PAs). The locked PAs sit at f = 1 by construction and are already
    the PA column here; with them excluded the layer reproduces the package's 51,580 km² exactly (asserted)."""
    f = rioxarray.open_rasterio(CORE_TIF, masked=True).squeeze()
    pa = rioxarray.open_rasterio(CORE_PA_MASK, masked=True).squeeze()
    assert pa.shape == f.shape, "the 1 km PA mask and the core layer are on different grids"
    core1k = (np.nan_to_num(f.values, nan=0.0) >= CORE_THRESHOLD) & ~(np.nan_to_num(pa.values, nan=0) > 0)
    km2_1k = float(core1k.sum()) * abs(f.rio.resolution()[0] * f.rio.resolution()[1]) / 1e6
    assert abs(km2_1k - CORE_KM2_EXPECTED) <= 50, f"core at 1 km = {km2_1k:,.0f} km², expected {CORE_KM2_EXPECTED:,} (package summary) -- layer or mask changed"
    c300 = f.copy(data=core1k.astype("float32")).rio.reproject_match(P0.R.resistance, resampling=Resampling.nearest)
    core = np.nan_to_num(c300.values, nan=0) > 0.5
    print(f"prioritizr core (balanced scenario, guarded tier on allocatable land, f >= {CORE_THRESHOLD} outside locked PAs): {km2_1k:,.0f} km² at 1 km "
          f"-> {float((core & P0.pu).sum()) * P0.cell_km2:,.0f} km² on the routable 300 m grid")
    return core & P0.pu


def coverage(P0):
    """Per complex and per corridor link's dissolved band: share inside existing PAs, incremental share added by the proposed
    IPCAs, share in the prioritizr core (and its increment beyond PAs + IPCAs), share outside all three; plus ONE area-expectation
    row = the same shares over the whole routable Y2Y frame, so an overlap reads against expectation."""
    R = P0.R
    pa = R.protected_pa & P0.pu; ip = R.protected_ipca & P0.pu; core = _core300(P0)
    P0.masks = dict(pa=pa, ipca=ip, core=core)

    def shares(m, label, kind, ident):
        n = int(m.sum())
        return dict(kind=kind, id=ident, label=label, area_km2=round(n * P0.cell_km2, 1),
                    pa=round(float((m & pa).sum() / n), 4), ipca_incremental=round(float((m & ip & ~pa).sum() / n), 4),
                    core=round(float((m & core).sum() / n), 4), core_incremental=round(float((m & core & ~pa & ~ip).sum() / n), 4),
                    outside_all=round(float((m & ~pa & ~ip & ~core).sum() / n), 4)) if n else None
    rows = [shares(P0.pu, "EXPECTATION: the whole routable Y2Y frame", "expectation", 0)]
    for r in P0.cx.itertuples():
        rows.append(shares(P0.complex_id == r.complex_id, r.name, "complex", int(r.complex_id)))
    tr = R.transform; shape = R.shape
    for eid, r in P0.links.iterrows():
        g = P0.bands.loc[eid, "geometry"]
        m = rasterize([(g, 1)], out_shape=shape, transform=tr, fill=0, dtype="uint8").astype(bool) & P0.pu & ~P0.node_land
        rows.append(shares(m, f"{r['pair']} {eid}", "link", eid))
    cov = pd.DataFrame([x for x in rows if x])
    cov.to_csv(P0.out / "coverage.csv", index=False, encoding="utf-8-sig")
    P0.cov = cov
    e = cov[cov.kind == "expectation"].iloc[0]
    print(f"expectation over the routable frame: PAs {100*e.pa:.1f}% · +IPCAs {100*e.ipca_incremental:.1f}% · core {100*e.core:.1f}% "
          f"(core beyond PAs+IPCAs {100*e.core_incremental:.1f}%) · outside all three {100*e.outside_all:.1f}%")
    cxc = cov[cov.kind == "complex"]; lk = cov[cov.kind == "link"]
    print(f"complexes (area-weighted): PAs {100*(cxc.pa*cxc.area_km2).sum()/cxc.area_km2.sum():.1f}% · +IPCAs {100*(cxc.ipca_incremental*cxc.area_km2).sum()/cxc.area_km2.sum():.1f}% "
          f"· core {100*(cxc.core*cxc.area_km2).sum()/cxc.area_km2.sum():.1f}% · outside {100*(cxc.outside_all*cxc.area_km2).sum()/cxc.area_km2.sum():.1f}%")
    print(f"corridor bands (area-weighted): PAs {100*(lk.pa*lk.area_km2).sum()/lk.area_km2.sum():.1f}% · +IPCAs {100*(lk.ipca_incremental*lk.area_km2).sum()/lk.area_km2.sum():.1f}% "
          f"· core {100*(lk.core*lk.area_km2).sum()/lk.area_km2.sum():.1f}% · outside {100*(lk.outside_all*lk.area_km2).sum()/lk.area_km2.sum():.1f}% | "
          f"links crossing land outside PAs + IPCAs: {int(((lk.outside_all + lk.core_incremental) > 0).sum())} of {len(lk)}")
    return cov


# ================= 4. slivers =================
def slivers(P0):
    """One row per near-contiguous link: complex, patches, path length, and the cost classes met along the centreline
    (cells on cost 10 / 100 / 1000, read from the run's resistance at the centreline vertices -- one vertex per path cell)."""
    R = P0.R; res = R.resistance.values
    xs, ys = R.template.x.values, R.template.y.values
    m2c = P0.mem.set_index("node_id")["complex_id"]
    rows = []
    for eid, r in P0.adjacent.iterrows():
        geom = P0.centrelines.loc[eid, "geometry"] if eid in P0.centrelines.index else None
        n10 = n100 = n1000 = np.nan
        if geom is not None:
            pts = np.asarray(geom.coords)
            cols = np.clip(np.searchsorted(xs, pts[:, 0]) - 1, 0, len(xs) - 1); rr = np.clip(np.searchsorted(-ys, -pts[:, 1]) - 1, 0, len(ys) - 1)
            v = res[rr, cols]; n10, n100, n1000 = int((v == 10).sum()), int((v == 100).sum()), int((v >= 1000).sum())
        rows.append(dict(complex_id=int(m2c.loc[int(r["i_id"])]), edge_id=eid, patch_i=int(r["i_id"]), patch_j=int(r["j_id"]),
                         path_len_km=round(float(r["lcp_len_cells"]) * P0.cell_km, 1) if pd.notna(r.get("lcp_len_cells")) else np.nan,
                         path_cells_cost10=n10, path_cells_cost100=n100, path_cells_cost1000=n1000,
                         has_feature=bool((n100 or 0) > 0 or (n1000 or 0) > 0), crosses_cost_1000=bool(r.get("crosses_cost_1000", False)),
                         barrier_between=bool(r.get("link_class", "") == "near_contiguous_barrier")))
    for eid, r in getattr(P0, "intra_links", pd.DataFrame()).iterrows():          # within-complex corridor-class links (item 2)
        geom = P0.centrelines.loc[eid, "geometry"] if eid in P0.centrelines.index else None
        n10 = n100 = n1000 = np.nan
        if geom is not None:
            pts = np.asarray(geom.coords)
            cols = np.clip(np.searchsorted(xs, pts[:, 0]) - 1, 0, len(xs) - 1); rr = np.clip(np.searchsorted(-ys, -pts[:, 1]) - 1, 0, len(ys) - 1)
            v = res[rr, cols]; n10, n100, n1000 = int((v == 10).sum()), int((v == 100).sum()), int((v >= 1000).sum())
        rows.append(dict(complex_id=int(r["complex_from"]), edge_id=eid, patch_i=int(r["i_id"]), patch_j=int(r["j_id"]),
                         path_len_km=round(float(r["lcp_len_cells"]) * P0.cell_km, 1) if pd.notna(r.get("lcp_len_cells")) else np.nan,
                         path_cells_cost10=n10, path_cells_cost100=n100, path_cells_cost1000=n1000,
                         has_feature=bool((n100 or 0) > 0 or (n1000 or 0) > 0), crosses_cost_1000=bool(r.get("crosses_cost_1000", False)),
                         barrier_between=False, kind="within-complex corridor-class link (not near-contiguous)", link_class=r.get("link_class")))
    sl = pd.DataFrame(rows)
    if "kind" not in sl.columns:
        sl["kind"] = "near-contiguous"
    sl["kind"] = sl["kind"].fillna("near-contiguous")
    sl = sl.sort_values(["complex_id", "has_feature", "path_len_km"], ascending=[True, False, True])
    sl.to_csv(P0.out / "slivers.csv", index=False, encoding="utf-8-sig")
    P0.slivers = sl
    per = sl.groupby("complex_id").agg(n_slivers=("edge_id", "size"), n_slivers_with_feature=("has_feature", "sum"))
    P0.cx = P0.cx.merge(per, left_on="complex_id", right_index=True, how="left").fillna({"n_slivers": 0, "n_slivers_with_feature": 0})
    P0.cx["n_slivers"] = P0.cx["n_slivers"].astype(int); P0.cx["n_slivers_with_feature"] = P0.cx["n_slivers_with_feature"].astype(int)
    print(f"slivers: {len(sl)} within-complex links; {int(sl.has_feature.sum())} with a cost-100/1000 cell on the path; "
          f"{int((sl.path_cells_cost10 > 0).sum())} touch cost 10; path length median {sl.path_len_km.median():.1f} km, max {sl.path_len_km.max():.1f}")
    return sl


# ================= 4b. fronts: the within-complex links as corridors (run spec v3 §1a / §5 revised 2026-09-29; D-W6) =================
BETA = 2.5                      # D7's ceiling, inherited (the interior reading applies it to the surviving detour)
SQUEEZE = 0.5                   # D17 / D23's width threshold, inherited


def fronts(P0):
    """Every within-complex link (the near-contiguous ones + the corridor-class links with both ends in one complex) as a FRONT
    on the pressure scale. Route sense = width alone (a front has no branches): CUT when the least-cost path carries cost 10 or
    the width ratio is below the squeeze threshold. Edge sense, TWO readings reported: `E_v2` = the patch-level D7 flag (a pairwise
    question that answers nothing inside a complex) and `E_interior` = D7 read on the complex's own front graph -- the front is a
    bridge of that graph, or the surviving detour costs more than BETA x the front (the chat's ruling of 2026-09-29). On v2's graph
    (MST + backups, a chain by construction) the interior reading fires on most fronts, so for the DRAFT the drawn class is width /
    road only (`front_class`: open | cut); the four-class reading is kept in `front_class_d23` for the table (M7.8). Bands = the
    v2 per-link band polygons -> fronts_v2.gpkg (audit + postprocess)."""
    e = P0.edges
    sl = P0.slivers.copy()
    sl = sl.merge(e[["cost", "edge_irreplaceable", "squeeze_ratio_obs", "width_ratio_p10", "band_new_km2", "in_mst"]], left_on="edge_id", right_index=True, how="left")
    sl["E_v2"] = sl["edge_irreplaceable"].fillna(False).astype(bool)
    sl["narrow"] = sl["squeeze_ratio_obs"] < SQUEEZE
    sl["road_on_path"] = sl["path_cells_cost10"].fillna(0) > 0
    sl["cut"] = sl["narrow"] | sl["road_on_path"]
    rows = {}
    for cid, grp in sl.groupby("complex_id"):
        Gc = nx.Graph()
        for r in grp.itertuples():
            Gc.add_edge(int(r.patch_i), int(r.patch_j), weight=float(r.cost) if pd.notna(r.cost) else 1.0)
        bridges = {tuple(sorted(b)) for b in nx.bridges(Gc)}
        for r in grp.itertuples():
            a, b = int(r.patch_i), int(r.patch_j); key = tuple(sorted((a, b)))
            if key in bridges:
                rows[r.edge_id] = (True, np.inf)
            else:
                H = Gc.copy(); H.remove_edge(a, b)
                rows[r.edge_id] = (False, nx.shortest_path_length(H, a, b, weight="weight") / max(float(r.cost), 1e-9))
    sl["bridge"] = sl["edge_id"].map(lambda k: rows[k][0]); sl["detour_ratio"] = sl["edge_id"].map(lambda k: rows[k][1])
    sl["E_interior"] = sl["bridge"] | (sl["detour_ratio"] > BETA)
    sl["front_class"] = np.where(sl["cut"], "cut", "open")                                   # DRAWN (the draft): width / road only
    sl["front_class_d23"] = np.select([sl["E_interior"] & sl["cut"], sl["E_interior"], sl["cut"]],
                                      ["only viable", "last affordable", "narrowing"], "options")   # TABLE: the interior reading (M7.8)
    P0.fronts = sl
    g = P0.bands.loc[[k for k in sl["edge_id"] if k in P0.bands.index], ["geometry"]].reset_index()      # index 'edge_id' -> a column
    g = g.merge(sl[["edge_id", "complex_id", "patch_i", "patch_j", "path_len_km", "front_class", "front_class_d23", "E_v2", "E_interior", "bridge", "cut", "narrow", "road_on_path",
                    "squeeze_ratio_obs", "band_new_km2"]], on="edge_id", how="left")
    P0.fronts_gdf = gpd.GeoDataFrame(g, geometry="geometry", crs=P0.R.crs)
    n = len(sl)
    print(f"fronts: {n} within-complex links -> drawn {int((sl.front_class == 'open').sum())} open + {int((sl.front_class == 'cut').sum())} cut "
          f"({int(sl.narrow.sum())} narrow, {int(sl.road_on_path.sum())} with a road on the path) | edge sense: patch-level D7 {int(sl.E_v2.sum())}, "
          f"interior reading {int(sl.E_interior.sum())} ({int(sl.bridge.sum())} bridges of v2's front graph + {int((~sl.bridge & (sl.detour_ratio > BETA)).sum())} detours > beta) -- table only for the draft (M7.8)")
    print("  four-class table reading:", sl["front_class_d23"].value_counts().to_dict())
    return sl


# ================= 5. accounting =================
def accounting(P0):
    """Corridor land as dissolved unions (the run's corridors.tif = every band incl. the near-contiguous ones; the corridor-class
    union = the 40 links' bands; per class), each beside the per-link SUM labelled as such; branches as links-with-n so the
    total reconciles with branches.csv."""
    R = P0.R; tr = R.transform; shape = R.shape
    classes = {}
    for cls_ in ("both", "edge", "squeezed", "securing", "near_contiguous", "near_contiguous_barrier"):
        ids = list(P0.edges.index[(P0.edges["link_class"] == cls_) & (P0.edges["cost"] > 0)])
        if not ids:
            continue
        u = np.zeros(shape, bool)
        for eid in ids:
            u |= rasterize([(P0.bands.loc[eid, "geometry"], 1)], out_shape=shape, transform=tr, fill=0, dtype="uint8").astype(bool)
        u &= P0.pu & ~P0.node_land
        classes[cls_] = dict(n_links=len(ids), dissolved_union_km2=round(float(u.sum()) * P0.cell_km2),
                             per_link_sum_km2=round(float(P0.edges.loc[ids, "band_new_km2"].sum())))
    corr_ids = list(P0.links.index)                    # INTER-complex corridor links only (Layer B)
    uc = np.zeros(shape, bool)
    for eid in corr_ids:
        uc |= rasterize([(P0.bands.loc[eid, "geometry"], 1)], out_shape=shape, transform=tr, fill=0, dtype="uint8").astype(bool)
    uc &= P0.pu & ~P0.node_land
    P0.corridor_union = uc
    fr = getattr(P0, "fronts_gdf", None)
    front_area = None
    if fr is not None and len(fr):
        fa = {}
        for cls_ in ("open", "cut"):
            sub = fr[fr.front_class == cls_]
            if not len(sub):
                fa[cls_] = 0; continue
            u = np.zeros(shape, bool)
            for geom in sub.geometry:
                u |= rasterize([(geom, 1)], out_shape=shape, transform=tr, fill=0, dtype="uint8").astype(bool)
            fa[cls_] = round(float((u & P0.pu & ~P0.node_land).sum()) * P0.cell_km2)
        front_area = dict(dissolved_by_class_km2=fa, per_link_sum_km2=round(float(fr["band_new_km2"].fillna(0).sum())),
                          note="within-complex fronts (v2 bands); reported on its own line, never summed into inter-complex corridor land")
    out = dict(all_bands_dissolved_km2=round(float(R.corridor.sum()) * P0.cell_km2), front_area=front_area,
               corridor_links_dissolved_km2=round(float(uc.sum()) * P0.cell_km2),
               corridor_links_outside_pas_ipcas_km2=round(float((uc & ~P0.masks["pa"] & ~P0.masks["ipca"]).sum()) * P0.cell_km2),
               corridor_links_outside_pas_ipcas_core_km2=round(float((uc & ~P0.masks["pa"] & ~P0.masks["ipca"] & ~P0.masks["core"]).sum()) * P0.cell_km2),
               corridor_links_per_link_sum_km2=round(float(P0.edges.loc[corr_ids, "band_new_km2"].sum())),
               near_contiguous_bands_inside_complexes_km2=classes.get("near_contiguous", {}).get("dissolved_union_km2"),
               within_complex_corridor_class_links=list(getattr(P0, "intra_links", pd.DataFrame()).index),
               n_inter_complex_links=len(corr_ids), by_class=classes)
    all_ids = list(P0.links_all.index)                  # every corridor-class link (the 37 inter-complex + the within-complex ones) carries branches
    nb = P0.edges.loc[all_ids, "n_branches"]
    by_n = nb.value_counts().sort_index()
    nb_inter = P0.edges.loc[corr_ids, "n_branches"]
    out["branches"] = dict(links_by_n={int(k): int(v) for k, v in by_n.items()}, total=int(nb.sum()),
                           inter_complex_links_by_n={int(k): int(v) for k, v in nb_inter.value_counts().sort_index().items()}, inter_complex_total=int(nb_inter.sum()),
                           branches_csv_rows=(int(len(P0.branches)) if P0.branches is not None else None),
                           reconciles=(P0.branches is None or int(nb.sum()) == int(len(P0.branches))))
    (P0.out / "accounting.json").write_text(json.dumps(out, indent=2))
    P0.acc = out
    print(f"accounting: all bands (v2 corridors.tif) {out['all_bands_dissolved_km2']:,} km² | the 40 corridor links dissolved {out['corridor_links_dissolved_km2']:,} km² "
          f"(per-link sum {out['corridor_links_per_link_sum_km2']:,}) | outside PAs + IPCAs {out['corridor_links_outside_pas_ipcas_km2']:,}, "
          f"outside PAs + IPCAs + core {out['corridor_links_outside_pas_ipcas_core_km2']:,} | branches: {out['branches']['links_by_n']} -> total {out['branches']['total']} "
          f"vs branches.csv {out['branches']['branches_csv_rows']} ({'reconciles' if out['branches']['reconciles'] else 'MISMATCH'})")
    return out


# ================= 6. names =================
def rename(P0, audit_names_path=None, write_audit=True):
    """D-W7: every patch 'Refugium (X)' (X = the PA it overlaps >= 10%, else the nearest PA + bearing; designation words
    stripped); complexes 'Refugia complex (X)' from the largest patch. Writes postprocess/node_names_v25.csv +
    complex_names.csv, and fills display_name in the tracked audit node_names.csv (Ethan may still edit it)."""
    nd = P0.nodes.copy()
    disp = []
    for _, r in nd.iterrows():
        base, bearing = _base(r); disp.append(refugium_name(base, bearing, multi=False))
    nd["display_name"] = disp
    nd["name"] = nd["display_name"]
    nd["complex_id"] = nd["node_id"].map(P0.mem.set_index("node_id")["complex_id"])
    nd.to_csv(P0.out / "node_names_v25.csv", index=False, encoding="utf-8-sig")
    cn = P0.cx[["complex_id", "name_auto", "n_patches", "patch_ids", "area_km2", "largest_patch", "largest_patch_name", "lat", "lon"]].copy()
    cn["display_name"] = ""
    cn.to_csv(P0.out / "complex_names.csv", index=False, encoding="utf-8-sig")
    if write_audit:
        ap = pathlib.Path(audit_names_path or (pathlib.Path(config.CORRIDORS["wolverine"]["audit_objects_dir"]) / "node_names.csv"))
        if ap.exists():
            a = pd.read_csv(ap, encoding="utf-8-sig").fillna({"display_name": ""})
            a["display_name"] = a["node_id"].map(nd.set_index("node_id")["display_name"]).fillna(a["display_name"])
            a.to_csv(ap, index=False, encoding="utf-8-sig")
            print(f"audit node_names.csv: display_name filled for {len(a)} patches (the run-dir copy stays pinned)")
    dup = nd["display_name"].value_counts(); dup = dup[dup > 1]
    print(f"names: {len(nd)} patches renamed as refugia; {len(dup)} display names shared by several patches (e.g. {dict(dup.head(3))}) -- disambiguated by their complex")
    return nd, cn


# ================= write + attach =================
def write_audit(P0, audit_dir=None):
    """Patch mode: the AUDIT OBJECTS the engine's contraction loader reads (cc._contract_complexes via new_run's pinned copies) --
    complex_membership.csv (node_id, complex_id, n_cells, area_km2), complex_names.csv (name_auto + a blank display_name to fill),
    complexes.gpkg (dissolved geometry), slivers_v2.csv (the within-complex table; `has_cost100_or_1000` = a cost-100/1000 cell
    on the path), complexes_summary.json (provenance: the source run and its edge-table sha). Git-tracked; refuses to overwrite a
    complex_names.csv with filled display names unless P0.force is set."""
    audit_dir = pathlib.Path(audit_dir or config.CORRIDORS["wolverine"]["audit_objects_dir"]); audit_dir.mkdir(parents=True, exist_ok=True)
    names_out = audit_dir / "complex_names.csv"
    if names_out.exists() and not getattr(P0, "force", False):
        old = pd.read_csv(names_out, encoding="utf-8-sig").fillna({"display_name": ""})
        if (old["display_name"].astype(str).str.strip() != "").any():
            raise FileExistsError(f"{names_out} carries filled display names -- set P0.force = True only if discarding them is intended")
    nd = P0.nodes.set_index("node_id")
    mem = P0.mem.copy(); mem["n_cells"] = mem["node_id"].map(nd["n_cells"]).astype(int); mem["area_km2"] = mem["node_id"].map(nd["area_km2"])
    mem.to_csv(audit_dir / "complex_membership.csv", index=False, encoding="utf-8-sig")
    cx = pd.DataFrame(P0.cx.drop(columns="geometry"))
    cn = pd.DataFrame(dict(complex_id=cx["complex_id"], name_auto=cx["name_auto"], display_name="", n_patches=cx["n_patches"], area_km2=cx["area_km2"],
                           n_cells=cx["n_cells"], largest_patch=cx["largest_patch"], largest_patch_name=cx["largest_patch_name"], patch_ids=cx["patch_ids"],
                           lat=cx["lat"], lon=cx["lon"],
                           share_north_model=[round(float((nd.loc[[int(x) for x in ids.split()], "share_north_model"].values * nd.loc[[int(x) for x in ids.split()], "n_cells"].values).sum()
                                                          / nd.loc[[int(x) for x in ids.split()], "n_cells"].sum()), 3) if "share_north_model" in nd.columns else np.nan for ids in cx["patch_ids"]]))
    cn.to_csv(names_out, index=False, encoding="utf-8-sig")
    g = P0.cx[["complex_id", "name", "name_auto", "n_patches", "area_km2", "patch_ids", "lat", "lon", "geometry"]]
    g.to_file(audit_dir / "complexes.gpkg", driver="GPKG")
    sl = (P0.fronts if getattr(P0, "fronts", None) is not None else P0.slivers).copy(); sl["has_cost100_or_1000"] = sl["has_feature"]
    sl.to_csv(audit_dir / "slivers_v2.csv", index=False, encoding="utf-8-sig")
    if getattr(P0, "fronts_gdf", None) is not None:
        P0.fronts_gdf.to_file(audit_dir / "fronts_v2.gpkg", driver="GPKG")
    summ = dict(from_run=P0.R.run_id, edges_sha256=cc._sha256(P0.run_dir / "corridor_edges.csv"), node_names_sha256=cc._sha256(P0.run_dir / "node_names.csv"),
                rule="complexes = connected components of the near-contiguous (D25) links of the patch-level network (MST + beta backups); no cap, no new threshold",
                node_min_km2=P0.rec["cfg"]["nodes"]["node_min_km2"], cwd_cutoff_abs=P0.rec["cfg"]["cwd_cutoff_abs"], cutoff_detour_km=P0.rec["cfg"].get("cutoff_detour_km"),
                n_patches=int(len(mem)), n_adjacent_links=int(len(P0.adjacent)), n_complexes=int(len(cx)), n_single_patch=int((cx["n_patches"] == 1).sum()),
                largest_complex_patches=int(cx["n_patches"].max()), largest_complex_km2=float(cx["area_km2"].max()),
                n_slivers=int(len(sl)), n_slivers_with_feature=int(sl["has_cost100_or_1000"].sum()), contraction_pass=1)
    (audit_dir / "complexes_summary.json").write_text(json.dumps(summ, indent=2, ensure_ascii=False))
    print(f"audit objects -> {audit_dir}: complex_membership.csv, complex_names.csv (display_name = your rename column), complexes.gpkg, slivers_v2.csv, complexes_summary.json")
    return summ


def write(P0):
    """Patch mode: postprocess/ copies of the complexes (complexes.gpkg with names + slivers), the complex_id raster and the
    summary. The corridor product itself is written in RUN mode (write_run_product) on the contracted run."""
    cx = P0.cx.copy()
    cx.to_file(P0.out / "complexes.gpkg", driver="GPKG")
    if getattr(P0, "fronts_gdf", None) is not None:
        P0.fronts_gdf.to_file(P0.out / "fronts_v2.gpkg", driver="GPKG"); P0.fronts.to_csv(P0.out / "fronts.csv", index=False, encoding="utf-8-sig")
    meta = dict(run=P0.R.run_id, run_git=P0.rec.get("git"), n_patches=int(len(P0.nodes)), n_complexes=int(len(cx)),
                n_near_contiguous=int(len(P0.adjacent)), n_v2_corridor_class_links=int(len(getattr(P0, "links_all", []))),
                within_complex_corridor_class_links=list(getattr(P0, "intra_links", pd.DataFrame()).index),
                rule="complexes = connected components of the near-contiguous (D25) links of v2_run001 (run spec v3 §1a); the v2 links are not reported")
    (P0.out / "postprocess_summary.json").write_text(json.dumps(meta, indent=2, default=str))
    print(f"written -> {P0.out}: complexes.gpkg ({len(cx)}), slivers.csv, node_names_v25.csv, complex_names.csv, complex_id.tif")
    return cx


# ================= run mode: the product on the CONTRACTED run =================
def load_run(run_dir):
    """The contracted run (v25_run001) as the product's namespace: R (cc.load_results, contracted), its inter-complex links with
    complex_from / complex_to from the C labels, band polygons + centrelines, the complex_id grid, the complexes."""
    run_dir = pathlib.Path(run_dir)
    R = cc.load_results(run_dir)
    assert getattr(R, "contracted", False), f"{run_dir.name} is not a contracted run (no complex_membership.csv / complexes_layer_a.csv)"
    P0 = SimpleNamespace(R=R, run_dir=run_dir, out=run_dir / PP_SUB, mode="run")
    P0.out.mkdir(parents=True, exist_ok=True)
    e = R.edges.copy()
    e["i_id"] = [label_num(x) for x in e["label_i"]]; e["j_id"] = [label_num(x) for x in e["label_j"]]
    nz = (e["cost"] > 0) & (~e["is_adjacency"].astype(bool))
    near = e["near_contiguous"].astype(bool) if "near_contiguous" in e.columns else pd.Series(False, index=e.index)
    c = e[nz & ~near].copy()
    c["complex_from"] = c["i_id"].astype(int); c["complex_to"] = c["j_id"].astype(int); c["inter_complex"] = c["complex_from"] != c["complex_to"]
    assert c["inter_complex"].all(), "a contracted run cannot carry a link inside one complex"
    c["pair"] = [f"C{min(a, b)}-C{max(a, b)}" for a, b in zip(c["complex_from"], c["complex_to"])]
    mult = c["pair"].value_counts(); c["links_on_pair"] = c["pair"].map(mult)
    P0.edges, P0.links, P0.links_all, P0.intra_links, P0.adjacent = e, c, c, c.iloc[0:0], e[nz & near]
    P0.bands = gpd.read_file(run_dir / "corridor_edges.gpkg", layer="bands").to_crs(R.crs).set_index("edge_id")
    P0.centrelines = gpd.read_file(run_dir / "corridor_edges.gpkg", layer="centrelines").to_crs(R.crs).set_index("edge_id")
    P0.branches = pd.read_csv(run_dir / "branches.csv", encoding="utf-8-sig") if (run_dir / "branches.csv").exists() else None
    P0.rec = json.loads((run_dir / "run_config.json").read_text())
    P0.cell_km2, P0.cell_km = R.cell_km2, R.cell_km
    P0.complex_id = np.nan_to_num(R.complex_id.values, nan=0).astype(int)
    P0.pu = np.isfinite(R.resistance.values) & (R.resistance.values > 0)
    P0.node_land = R.pa_mask | R.anch
    P0.cx = R.complexes.copy()
    P0.nodes = R.node_table
    P0.fronts_gdf = getattr(R, "fronts", None); P0.fronts = (pd.DataFrame(P0.fronts_gdf.drop(columns="geometry")) if P0.fronts_gdf is not None else None)
    print(f"{R.run_id}: {len(P0.cx)} complexes, {len(c)} inter-complex links between {c['pair'].nunique()} pairs "
          f"({int((mult > 1).sum())} pairs with more than one link; {int(near[nz].sum())} still near-contiguous -- expected 0 after the second pass) | "
          f"cutoff {R.cutoff:.4f} = {R.cutoff * R.cell_km:.2f} km detour")
    return P0


def write_run_product(P0):
    """Run mode: postprocess/coverage.csv, accounting.json, corridor_links.csv (with the band coverage columns) and the summary."""
    lk = P0.links.copy()
    covl = P0.cov[P0.cov.kind == "link"].set_index("id")
    for c in ("pa", "ipca_incremental", "core", "core_incremental", "outside_all"):
        lk["band_" + c + "_share"] = lk.index.map(covl[c])
    lk.to_csv(P0.out / "corridor_links.csv", encoding="utf-8-sig")
    meta = dict(run=P0.R.run_id, run_git=P0.rec.get("git"), n_complexes=int(len(P0.cx)), n_corridor_links=int(len(lk)),
                n_pairs=int(lk["pair"].nunique()), core_layer=str(CORE_TIF), core_threshold=CORE_THRESHOLD, mode="run",
                rule="the inter-complex network routed between the complex unions (run spec v3 §1a revised 2026-09-29; §3 stages 3-4, §4)")
    (P0.out / "postprocess_summary.json").write_text(json.dumps(meta, indent=2, default=str))
    print(f"written -> {P0.out}: corridor_links.csv ({len(lk)}), coverage.csv, accounting.json")
    return lk


def attach(R, out=None):
    """Hand the product to the package. RUN mode (a contracted run: load_results already set R.contracted / R.complexes /
    R.complex_id / R.centrelines / R.slivers): merge the coverage columns and the accounting from `<run>/postprocess/` (07) and
    apply display names from the run's complex_names.csv. PATCH mode (v2_run001 + 05's postprocess/): everything from that folder."""
    out = pathlib.Path(out) if out else pathlib.Path(R.run_dir) / PP_SUB
    if getattr(R, "contracted", False) and getattr(R, "complexes", None) is not None:          # run mode
        cx = R.complexes
        cn = pathlib.Path(R.run_dir) / "complex_names.csv"
        if cn.exists():
            names = pd.read_csv(cn, encoding="utf-8-sig").fillna({"display_name": ""}).set_index("complex_id")
            cx["name"] = [str(names.loc[c, "display_name"]).strip() or str(names.loc[c, "name_auto"]) if c in names.index else n for c, n in zip(cx["complex_id"], cx["name"])]
        if (out / "coverage.csv").exists():
            cov = pd.read_csv(out / "coverage.csv", encoding="utf-8-sig")
            cc_ = cov[cov.kind == "complex"].copy(); cc_["id"] = cc_["id"].astype(int); cc_ = cc_.set_index("id")   # the id column mixes complex numbers and link ids -> text on read
            for c, col in (("pa", "pa_share"), ("ipca_incremental", "ipca_added_share"), ("core", "core_share"), ("core_incremental", "core_incremental_share"), ("outside_all", "outside_all_share")):
                cx[col] = cx["complex_id"].map(cc_[c])
            R.coverage = cov
        if "n_slivers" not in cx.columns and getattr(R, "slivers", None) is not None:
            per = R.slivers.groupby("complex_id").agg(n_slivers=("edge_id", "size"), n_slivers_with_feature=("has_cost100_or_1000", "sum"))
            cx["n_slivers"] = cx["complex_id"].map(per["n_slivers"]).fillna(0).astype(int); cx["n_slivers_with_feature"] = cx["complex_id"].map(per["n_slivers_with_feature"]).fillna(0).astype(int)
        R.complexes = cx; R.complex_table = pd.DataFrame(cx.drop(columns="geometry"))
        R.postprocess = json.loads((out / "postprocess_summary.json").read_text()) if (out / "postprocess_summary.json").exists() else {}
        R.accounting = json.loads((out / "accounting.json").read_text()) if (out / "accounting.json").exists() else {}
        R.intra_complex_ids = []
        fp = pathlib.Path(R.run_dir) / "fronts_v2.gpkg"                        # the within-complex fronts (v2 bands + classes), pinned by new_run
        R.fronts = gpd.read_file(fp).to_crs(R.crs) if fp.exists() else getattr(R, "fronts", None)
        if R.fronts is not None:
            per = R.fronts.groupby("complex_id").agg(n_fronts=("edge_id", "size"), n_cut=("cut", "sum"), n_E_interior=("E_interior", "sum"))
            for c in ("n_fronts", "n_cut", "n_E_interior"):
                cx[c] = cx["complex_id"].map(per[c]).fillna(0).astype(int)
            R.complexes = cx; R.complex_table = pd.DataFrame(cx.drop(columns="geometry"))
        print(f"attached (run mode): {len(cx)} complexes, {R.postprocess.get('n_corridor_links', '?')} inter-complex links, coverage {'yes' if (out / 'coverage.csv').exists() else 'NOT YET (run 07)'}")
        return R
    assert (out / "complexes.gpkg").exists(), f"{out} -- run 05_complexes first"
    cx = gpd.read_file(out / "complexes.gpkg").to_crs(R.crs)
    cn = out / "complex_names.csv"
    if cn.exists():
        names = pd.read_csv(cn, encoding="utf-8-sig").fillna({"display_name": ""}).set_index("complex_id")
        cx["name"] = [str(names.loc[c, "display_name"]).strip() or str(names.loc[c, "name_auto"]) if c in names.index else n for c, n in zip(cx["complex_id"], cx["name"])]
    R.contracted = True
    R.complexes = cx; R.complex_table = pd.DataFrame(cx.drop(columns="geometry"))
    R.complex_id = rioxarray.open_rasterio(out / "complex_id.tif").squeeze()
    R.centrelines = gpd.read_file(R.run_dir / "corridor_edges.gpkg", layer="centrelines").to_crs(R.crs)
    R.slivers = pd.read_csv(out / "slivers.csv", encoding="utf-8-sig") if (out / "slivers.csv").exists() else None
    nv = out / "node_names_v25.csv"
    if nv.exists():
        R.node_table = pd.read_csv(nv, encoding="utf-8-sig").fillna({"display_name": ""})
    R.postprocess = json.loads((out / "postprocess_summary.json").read_text()) if (out / "postprocess_summary.json").exists() else {}
    R.accounting = json.loads((out / "accounting.json").read_text()) if (out / "accounting.json").exists() else {}
    R.coverage = pd.read_csv(out / "coverage.csv", encoding="utf-8-sig") if (out / "coverage.csv").exists() else None
    R.intra_complex_ids = list(R.postprocess.get("within_complex_corridor_class_links", []))
    print(f"attached v2.5 product: {len(cx)} complexes, corridor links {R.postprocess.get('n_corridor_links')}")
    return R
