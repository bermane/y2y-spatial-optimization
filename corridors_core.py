"""Least-cost corridor engine (05) -- connect anchor areas with routed corridors.

The prioritizr connectivity PENALTY could not connect the northern IPCAs: it rewards aggregating
on permeable land, not routing between two specific nodes. This does the routing directly --
least-cost paths (Linkage-Mapper style) between every anchor over a resistance surface blended
from corridor-relevant layers (current-density + climate corridors + refugia) with gHM as a
barrier. A perturbation ENSEMBLE then yields a corridor frequency/robustness surface + a few
distinct near-optimal alternative networks (the MGA analog).

One function per stage so a thin 05 notebook keeps cell-by-cell inspection:
    A = load("north"); resistance(A); cost_distances(A); corridor_network(A)
    corridor_ensemble(A); map(A); write_outputs(A)
All params come from config.CORRIDORS[key]. Pure Python (skimage.graph.MCP_Geometric); no prioritizr.
"""
import json
import types
import copy
import pathlib
import pandas as pd

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, LogNorm
from matplotlib.patches import Patch
import rioxarray
import xarray as xr
import geopandas as gpd
from rasterio.features import rasterize, shapes
from shapely.geometry import shape as _shape
from skimage.graph import MCP_Geometric
from scipy import ndimage
from collections import defaultdict
import pyproj

import config
import results_core as rc
from results_core import PA_COLOR, ANCHOR_COLOR   # shared map colours

CORRIDOR_COLOR = "#e6550d"   # routed corridors (orange), distinct from grey PAs + teal anchors


class _NS(types.SimpleNamespace):
    """SimpleNamespace with a ONE-LINE repr.

    Every cc.* function ends `return A` so calls can chain, and Jupyter echoes that return value
    after each cell — under the default repr that dumps the entire config, every scenario snapshot
    and the profile DataFrame after every single cell."""

    def __repr__(self):
        bits = [str(getattr(self, "key", "?"))]
        if getattr(self, "nodes", None) is not None:
            bits.append(f"{len(self.nodes)} nodes")
        if getattr(self, "shape", None):
            bits.append(f"{self.shape[1]}x{self.shape[0]}")
        if getattr(self, "corridor", None) is not None:
            bits.append(f"corridor {int(self.corridor.sum()) * self.cell_km2:,.0f} km²")
        if getattr(self, "scenarios", None):
            bits.append("scenarios: " + ", ".join(self.scenarios))
        if getattr(self, "groups", None):
            bits.append(f"{len(self.groups)} segments")
        return f"<corridors {' | '.join(bits)}>"


# ================= setup =================
def load(key):
    """Read every layer the resistance config references, crop the working grid to the region,
    assemble the anchor nodes (proposed IPCAs + large existing PAs), rasterize them onto the grid."""
    cfg = config.CORRIDORS[key]
    run_dir = config.RESULTS_DIR / cfg["results_subdir"]; run_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = run_dir / "figures"; fig_dir.mkdir(parents=True, exist_ok=True)

    rc = cfg["resistance"]
    names = list(dict.fromkeys([d["layer"] for d in rc["drivers"]] + [rc["barrier"]["layer"]]))
    rasters = {nm: rioxarray.open_rasterio(config.HANDOFF_DIR / f"{nm}.tif", masked=True).squeeze()
               for nm in names}
    template = rasters[rc["drivers"][0]["layer"]]           # coords/plotting + crop reference

    # crop north for routing room
    to_ll = pyproj.Transformer.from_crs(template.rio.crs, "EPSG:4326", always_xy=True)
    xmid = float(template.x.values[template.shape[1] // 2])
    latrow = np.array([to_ll.transform(xmid, float(y))[1] for y in template.y.values])
    rf = cfg["region_filter"]
    keep = np.ones(template.shape[0], bool)
    if rf.get("min_lat") is not None: keep &= latrow >= rf["min_lat"]
    if rf.get("max_lat") is not None: keep &= latrow <= rf["max_lat"]
    r = np.where(keep)[0]; sl = slice(r.min(), r.max() + 1)
    template = template.isel(y=sl)
    layers = {nm: ras.isel(y=sl).values for nm, ras in rasters.items()}
    crs = template.rio.crs; transform = template.rio.transform(); shape = template.shape
    rx, ry = template.rio.resolution(); cell_km2 = abs(rx * ry) / 1e6; cell_km = abs(rx) / 1000.0
    pu = np.isfinite(template.values)
    print(f"{cfg['region_label']}: working grid {shape[1]}x{shape[0]} = {int(pu.sum()):,} PU cells "
          f"@ {cell_km:.0f} km | layers: {', '.join(names)}")

    # ---- nodes ----
    nc = cfg["nodes"]
    def _rast(geom):
        return rasterize([(geom, 1)], out_shape=shape, transform=transform, fill=0, dtype="uint8").astype(bool) & pu
    nodes, dropped = [], []
    ipca = config._load_source(nc["proposed"], nc.get("source_filter")).to_crs(crs)
    nfield = next(c for c in ipca.columns if "name" in c.lower())
    for _, row in ipca.iterrows():
        m = _rast(row.geometry); (nodes if m.sum() >= nc["node_min_cells"] else dropped).append(
            (f"IPCA · {row[nfield]}", m, "ipca"))
    n_ipca = sum(k == "ipca" for _, _, k in nodes)
    if nc.get("include_existing_pas"):
        pas = gpd.read_file(config.PA_VECTOR).to_crs(crs).dissolve(by="PA_Name").reset_index()
        pas = pas[pas.geometry.area / 1e6 >= nc["existing_pa_min_km2"]]
        for _, row in pas.iterrows():
            m = _rast(row.geometry)
            if m.sum() >= nc["node_min_cells"]:
                nodes.append((f"PA · {row['PA_Name']}", m, "pa"))
    nodes = [(lbl, m) for lbl, m, _ in nodes]
    kinds = ["ipca"] * n_ipca + ["pa"] * (len(nodes) - n_ipca)
    print(f"nodes: {len(nodes)} ({n_ipca} IPCAs + {len(nodes)-n_ipca} existing PAs "
          f">= {nc['existing_pa_min_km2']} km²)")
    if dropped:
        print(f"  dropped {len(dropped)} IPCA(s) with < {nc['node_min_cells']} PU cells in region: "
              + ", ".join(d[0].split('· ')[1] for d in dropped))

    outline = gpd.read_file(config.CORRIDOR_REF).to_crs(crs)
    return _NS(
        key=key, cfg=cfg, run_dir=run_dir, fig_dir=fig_dir, region_label=cfg["region_label"],
        template=template, layers=layers, crs=crs, transform=transform, shape=shape, pu=pu,
        cell_km2=cell_km2, cell_km=cell_km, nodes=nodes, kinds=kinds, outline=outline)


# ================= resistance =================
def resistance(A):
    """Blend the driver layers into a permeability, invert, and multiply by the gHM barrier.

    each driver is stretched to 0-1 before weighting. Two modes (rc["scale"], default "minmax"):
      "minmax":   clip( (layer - p_lo) / (p_hi - p_lo), 0, 1 )   -- full 0-1 range per layer
      "zero_max": clip(  layer / p_hi, 0, 1 )                    -- assumes layer starts near 0
    "minmax" matters for drivers that don't start at zero (e.g. macrorefugia ~10-15): "zero_max"
    would leave them near-constant (no route contrast); "minmax" gives every layer real spread.
    p_hi = driver "pctile"; p_lo = driver "lo_pctile" (default 5).

    permeability = ( Σ_d w_d · scaled_d ) ** conn_exponent                             (want high)
    resistance   = ( 1 / max(permeability, perm_floor) ) · barrier_base ** gHM        (want low)
    off-PU cells are impassable (inf). The drivers say where a route WANTS to go; the gHM factor
    multiplies resistance up through the human footprint the coarse driver layers miss."""
    rc = A.cfg["resistance"]; pu = A.pu
    mode = rc.get("scale", "minmax")
    ws = np.array([d["weight"] for d in rc["drivers"]], float); ws = ws / ws.sum()
    perm = np.zeros(A.shape, float)
    for d, w in zip(rc["drivers"], ws):
        v = A.layers[d["layer"]]
        hi = np.nanpercentile(v[pu], d["pctile"])
        if mode == "minmax":
            lo = np.nanpercentile(v[pu], d.get("lo_pctile", 5))
            s01 = np.clip((np.where(pu, v, lo) - lo) / max(hi - lo, 1e-9), 0, 1)
        else:
            s01 = np.clip(np.where(pu, v, 0) / hi, 0, 1)
        perm += w * s01
        print(f"  driver {d['layer']:28s} w={w:.2f}  scaled[{mode}] p50={np.percentile(s01[pu],50):.2f} "
              f"p95={np.percentile(s01[pu],95):.2f}")
    perm = perm ** rc["conn_exponent"]
    bl = rc["barrier"]; ghm = np.where(pu, 1 - A.layers[bl["layer"]], 0.0)   # 1 - intactness
    res = (1.0 / np.maximum(perm, rc["perm_floor"])) * (bl["base"] ** ghm)
    A.resistance_arr = np.where(pu, res, np.inf)
    fin = A.resistance_arr[np.isfinite(A.resistance_arr)]
    print(f"resistance: p5={np.percentile(fin,5):.2f} p50={np.percentile(fin,50):.2f} "
          f"p95={np.percentile(fin,95):.1f} max={fin.max():.0f}   (low = preferred corridor land)")
    return A


# ================= network primitives (shared by baseline + ensemble) =================
def _prim_mst(D):
    """Minimum spanning tree (Prim) over the node-to-node least-cost distance matrix D."""
    N = D.shape[0]; inmst = {0}; edges = []
    while len(inmst) < N:
        best = (np.inf, None, None)
        for i in inmst:
            for j in range(N):
                if j not in inmst and D[i, j] < best[0]:
                    best = (D[i, j], i, j)
        if best[1] is None:
            break
        edges.append(best); inmst.add(best[2])
    return edges


def _cwd_all(A, res):
    """(cwd_list, mcp): least-cost accumulated distance from each node over resistance `res`.
    find_costs returns MCP's INTERNAL buffer (overwritten each call) -- MUST .copy()."""
    mcp = MCP_Geometric(res)
    cwd = []
    for _, m in A.nodes:
        cum, _ = mcp.find_costs([tuple(x) for x in np.argwhere(m)])
        cwd.append(cum.copy())
    return cwd, mcp


def _n_groups(A, corr):
    """Number of connected node-groups in (corr | nodes). Union-find over shared components: a
    node can straddle a tiny PU speck, so a single max-label per node over-counts."""
    net = corr.copy()
    for _, m in A.nodes: net |= m
    lab, _ = ndimage.label(net, structure=np.ones((3, 3), int))
    N = len(A.nodes); parent = list(range(N))
    def _find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    lab_nodes = defaultdict(list)
    for k, (_, m) in enumerate(A.nodes):
        for v in np.unique(lab[m]):
            if v > 0: lab_nodes[int(v)].append(k)
    for ks in lab_nodes.values():
        for k in ks[1:]: parent[_find(k)] = _find(ks[0])
    return len({_find(k) for k in range(N)})


def _network_from_cwd(A, cwd, mcp):
    """node-to-node least-cost distances -> Prim MST -> per-edge traceback centre-line + swath band
    -> union. Returns corridor mask, MST, edge labels, path-cell length, and node-group count."""
    N = len(A.nodes)
    D = np.full((N, N), np.inf)
    for i in range(N):
        for j in range(N):
            if i != j:
                D[i, j] = np.nanmin(cwd[i][A.nodes[j][1]])
    mst = _prim_mst(D)
    frac = A.cfg["corridor_width_frac"]
    corr = np.zeros(A.shape, bool); lengths = []; path_cells = 0
    for cost_ij, i, j in mst:
        # explicit least-cost PATH as a guaranteed-continuous centre-line (the width band alone
        # leaves gaps for short edges where frac*cost_ij is tiny) ...
        mcp.find_costs([tuple(x) for x in np.argwhere(A.nodes[i][1])])
        target = tuple(np.argwhere(A.nodes[j][1])[np.argmin(cwd[i][A.nodes[j][1]])])
        path = mcp.traceback(target); path_cells += len(path)
        for rr, cc in path: corr[rr, cc] = True
        # ... plus the width band for a swath
        field = cwd[i] + cwd[j]; lcp = np.nanmin(field)
        corr |= np.isfinite(field) & (field <= lcp + frac * cost_ij)
        lengths.append((A.nodes[i][0], A.nodes[j][0], cost_ij))
    corr &= A.pu
    return dict(corridor=corr, mst=mst, lengths=lengths, path_cells=path_cells,
                n_groups=_n_groups(A, corr))


# ================= baseline network =================
def cost_distances(A):
    """Baseline cost-weighted distance from each node."""
    A.cwd, A.mcp = _cwd_all(A, A.resistance_arr)
    print(f"cost-weighted distance computed from {len(A.nodes)} nodes")
    return A


def corridor_network(A):
    """Baseline corridor network on the un-perturbed resistance."""
    net = _network_from_cwd(A, A.cwd, A.mcp)
    A.corridor = net["corridor"]; A.mst = net["mst"]; A.mst_lengths = net["lengths"]
    A.n_groups = net["n_groups"]; A.base_path_cells = net["path_cells"]
    area = int(A.corridor.sum()) * A.cell_km2
    print(f"MST: {len(A.mst)} edges | corridor swath {int(A.corridor.sum()):,} cells = {area:,.0f} km²")
    print(f"anchors connected: {len(A.nodes)} nodes in {A.n_groups} network group(s) (1 = fully connected)")
    return A


# ================= near-optimal ensemble =================
def _jaccard(a, b):
    u = int((a | b).sum())
    return int((a & b).sum()) / u if u else 1.0


def corridor_ensemble(A):
    """Perturb the resistance +-jitter, re-solve n_runs times -> a corridor FREQUENCY surface
    (fraction of runs each cell is a corridor: 1 = robust core, low = flexible) + n_alternatives
    distinct near-optimal networks (most different from the baseline by route overlap)."""
    ec = A.cfg["ensemble"]; rng = np.random.default_rng(ec["seed"])
    freq = A.corridor.astype(float).copy()               # baseline counts as one member
    runs = []
    for _ in range(ec["n_runs"]):
        jit = 1.0 + ec["jitter"] * rng.uniform(-1, 1, A.shape)
        res_r = np.where(np.isfinite(A.resistance_arr), A.resistance_arr * jit, np.inf)
        cwd_r, mcp_r = _cwd_all(A, res_r)
        net_r = _network_from_cwd(A, cwd_r, mcp_r)
        runs.append(net_r); freq += net_r["corridor"]
    freq /= (ec["n_runs"] + 1)
    A.frequency = freq

    # distinct alternatives: most different from baseline by route overlap; report physical-length
    # premium (centre-line km, resistance-independent) so "near-optimal" is comparable.
    scored = [dict(i=r, jaccard=_jaccard(A.corridor, n["corridor"]),
                   premium=(n["path_cells"] - A.base_path_cells) / max(A.base_path_cells, 1),
                   groups=n["n_groups"], corridor=n["corridor"]) for r, n in enumerate(runs)]
    A.alternatives = sorted(scored, key=lambda s: s["jaccard"])[:ec["n_alternatives"]]

    core = int((freq >= 0.9).sum()) * A.cell_km2; ever = int((freq > 0).sum()) * A.cell_km2
    prem = [s["premium"] for s in scored]
    print(f"ensemble: {ec['n_runs']} runs (jitter ±{ec['jitter']:.0%}) | "
          f"robust core (freq≥0.9) {core:,.0f} km² of {ever:,.0f} km² ever-used")
    # premium is signed: a perturbed run CAN find a shorter centre-line, since length (not cost) is
    # the resistance-independent yardstick here -- so let the sign print itself, no literal "+".
    print(f"  all runs fully connected: {all(s['groups'] == 1 for s in scored)} | "
          f"centre-line length vs optimum: {min(prem):+.0%}..{max(prem):+.0%}")
    print(f"  {len(A.alternatives)} distinct near-optimal alternatives (route overlap w/ baseline):")
    for s in A.alternatives:
        print(f"     {s['premium']:+.1%} length | {100*s['jaccard']:.0f}% overlap")
    return A


# ================= scenarios (driver-stretch variants, each a full run) =================
def _snapshot(A):
    """Everything downstream (map / compare_map / write_outputs) needs from one solved run.

    Deliberately EXCLUDES A.cwd / A.mcp: cwd is one float64 grid per node (~800 MB for 45 nodes at
    1 km), so holding it for every scenario would blow memory. Nothing downstream reads it."""
    r = A.resistance_arr[A.pu]
    return dict(
        resistance_arr=A.resistance_arr, corridor=A.corridor, mst=A.mst, mst_lengths=A.mst_lengths,
        n_groups=A.n_groups, base_path_cells=A.base_path_cells, cfg=A.cfg,
        frequency=getattr(A, "frequency", None), alternatives=getattr(A, "alternatives", None),
        spread=float(np.percentile(r, 95) / np.percentile(r, 5)),
        anchors=[A.cfg["resistance"]["drivers"][0].get("lo_pctile", 5),
                 A.cfg["resistance"]["drivers"][0]["pctile"]])


def _apply_scenario(cfg, overrides):
    """A scenario overrides ONLY the driver stretch anchors; everything else stays as configured."""
    cfg = copy.deepcopy(cfg)
    for d in cfg["resistance"]["drivers"]:
        d.update(overrides)
    return cfg


def run_scenarios(A, keys=None, ensemble=True):
    """Solve each named driver-stretch scenario end to end (resistance -> cost distances -> network
    -> near-optimal ensemble) and stash a snapshot per scenario on A.scenarios.

    The PRIMARY scenario is restored onto A's top-level attrs afterwards, so cc.map(A) and
    cc.write_outputs(A) behave exactly as they do for a single run. SLOW: roughly
    n_scenarios x (n_nodes + n_runs x n_nodes) MCP passes."""
    base_cfg = copy.deepcopy(A.cfg)
    scenarios = base_cfg.get("scenarios")
    if not scenarios:
        raise ValueError(f"config.CORRIDORS['{A.key}'] has no 'scenarios' block")
    primary = base_cfg.get("primary_scenario", next(iter(scenarios)))
    keys = list(keys) if keys else [primary] + [k for k in scenarios if k != primary]

    A.scenarios = {}; A.primary_scenario = primary
    for key in keys:
        print(f"\n=== scenario {key}{'  (primary)' if key == primary else ''} "
              f"{scenarios[key]} ===")
        A.cfg = _apply_scenario(base_cfg, scenarios[key])
        resistance(A); cost_distances(A); corridor_network(A)
        if ensemble:
            corridor_ensemble(A)
        A.scenarios[key] = _snapshot(A)
        A.cwd = A.mcp = None          # free ~800 MB before the next scenario

    # restore the primary so map()/write_outputs() see a normal single-run A
    A.cfg = _apply_scenario(base_cfg, scenarios[primary])
    for k, v in A.scenarios[primary].items():
        if k not in ("spread", "anchors", "cfg"):
            setattr(A, "resistance_arr" if k == "resistance_arr" else k, v)

    print(f"\n{len(A.scenarios)} scenarios solved; primary '{primary}' restored onto A")
    for key, s in A.scenarios.items():
        core = "" if s["frequency"] is None else \
            f" | robust core {int((s['frequency'] >= 0.9).sum()) * A.cell_km2:,.0f} km²"
        print(f"  {key:8s} anchors p{s['anchors'][0]}/p{s['anchors'][1]} | "
              f"swath {int(s['corridor'].sum()) * A.cell_km2:,.0f} km² | "
              f"centre-line {s['base_path_cells']} cells | {s['n_groups']} group(s) | "
              f"spread {s['spread']:.1f}x{core}")
    ks = list(A.scenarios)
    for i, a in enumerate(ks):
        for b in ks[i + 1:]:
            print(f"  route agreement {a} vs {b}: Jaccard "
                  f"{_jaccard(A.scenarios[a]['corridor'], A.scenarios[b]['corridor']):.2f}")
    return A


# ================= outputs =================
def _tif(A, arr, path, dtype, nodata):
    da = xr.DataArray(arr.astype(dtype), dims=("y", "x"), coords={"y": A.template.y, "x": A.template.x})
    da.rio.write_crs(A.crs, inplace=True); da.rio.write_transform(A.transform, inplace=True)
    da.rio.write_nodata(nodata, inplace=True)
    da.rio.to_raster(path, compress="DEFLATE")


def _gpkg(A, mask, path):
    polys = [shp for shp, v in shapes(mask.astype("uint8"), mask=mask, transform=A.transform) if v == 1]
    g = gpd.GeoDataFrame(geometry=[_shape(p) for p in polys], crs=A.crs)
    if len(g): g = gpd.GeoDataFrame(geometry=[g.union_all()], crs=A.crs)
    g.to_file(path, driver="GPKG")


def _write_set(A, dst, s):
    """Write one run's full file set into dst. `s` is a snapshot dict (see run_scenarios) or the
    live attrs off A. Returns (summary dict, written filenames)."""
    dst.mkdir(parents=True, exist_ok=True)
    written = []
    _tif(A, np.where(s["corridor"], 1, 0), dst / "corridors.tif", "uint8", 0)
    _tif(A, np.where(np.isfinite(s["resistance_arr"]), s["resistance_arr"], -1),
         dst / "resistance.tif", "float32", -1)
    _gpkg(A, s["corridor"], dst / "corridors.gpkg")
    written += ["corridors.tif", "resistance.tif", "corridors.gpkg"]

    summary = dict(
        region=A.region_label, n_nodes=len(A.nodes),
        n_ipca=sum(k == "ipca" for k in A.kinds), n_existing_pa=sum(k == "pa" for k in A.kinds),
        n_mst_edges=len(s["mst"]), n_network_groups=s["n_groups"],
        corridor_km2=round(int(s["corridor"].sum()) * A.cell_km2),
        resistance=s["cfg"]["resistance"], corridor_width_frac=s["cfg"]["corridor_width_frac"],
        mst_edges=[dict(a=a, b=b, lcp_cost=round(float(c), 1)) for a, b, c in s["mst_lengths"]])

    if s.get("frequency") is not None:
        _tif(A, s["frequency"], dst / "corridor_frequency.tif", "float32", -1)
        written.append("corridor_frequency.tif")
        for k, alt in enumerate(s["alternatives"], 1):
            _gpkg(A, alt["corridor"], dst / f"corridors_alt{k}.gpkg")
            written.append(f"corridors_alt{k}.gpkg")
        summary["ensemble"] = dict(
            n_runs=s["cfg"]["ensemble"]["n_runs"], jitter=s["cfg"]["ensemble"]["jitter"],
            robust_core_km2=round(int((s["frequency"] >= 0.9).sum()) * A.cell_km2),
            ever_used_km2=round(int((s["frequency"] > 0).sum()) * A.cell_km2),
            alternatives=[dict(length_premium_pct=round(100 * a["premium"], 1),
                               overlap_pct=round(100 * a["jaccard"], 1)) for a in s["alternatives"]])
    return summary, written


def write_outputs(A):
    """corridors.tif/.gpkg, resistance.tif, (ensemble) corridor_frequency.tif + corridors_alt*.gpkg,
    corridor_summary.json -> run_dir. When run_scenarios has run, each scenario ALSO gets the full
    set in run_dir/<scenario>/ and the summary gains a "scenarios" comparison block; the top-level
    files stay the primary scenario so existing paths keep working."""
    written = []
    summary, w = _write_set(A, A.run_dir, _snapshot(A))
    written += w

    scen = getattr(A, "scenarios", None)
    if scen:
        summary["primary_scenario"] = A.primary_scenario
        summary["scenarios"] = {}
        for key, s in scen.items():
            sub_summary, sub_w = _write_set(A, A.run_dir / key, s)
            written += [f"{key}/{f}" for f in sub_w]
            (A.run_dir / key / "corridor_summary.json").write_text(json.dumps(sub_summary, indent=2))
            written.append(f"{key}/corridor_summary.json")
            summary["scenarios"][key] = dict(
                anchors=s["anchors"], corridor_km2=sub_summary["corridor_km2"],
                centre_line_cells=s["base_path_cells"], n_network_groups=s["n_groups"],
                resistance_spread=round(s["spread"], 1),
                **({} if s.get("frequency") is None else dict(
                    robust_core_km2=sub_summary["ensemble"]["robust_core_km2"],
                    ever_used_km2=sub_summary["ensemble"]["ever_used_km2"])))
        # pairwise route agreement between scenarios
        keys = list(scen)
        summary["scenario_jaccard"] = {
            f"{a}__vs__{b}": round(_jaccard(scen[a]["corridor"], scen[b]["corridor"]), 3)
            for i, a in enumerate(keys) for b in keys[i + 1:]}

    (A.run_dir / "corridor_summary.json").write_text(json.dumps(summary, indent=2))
    written.append("corridor_summary.json")
    for f in written:
        p = A.run_dir / f
        try:
            p = p.relative_to(config.PROJECT_DIR)
        except ValueError:
            pass                      # run_dir redirected outside the project (tests)
        print(f"  wrote {p}")
    return A


# ================= map =================
def _frame_region(A, ax, pad=0.06):
    xl, yl = ax.get_xlim(), ax.get_ylim()
    for lim, setter in ((xl, ax.set_xlim), (yl, ax.set_ylim)):
        lo, hi = min(lim), max(lim); d = (hi - lo) * pad
        setter((lo - d, hi + d) if lim[0] <= lim[1] else (hi + d, lo - d))


def _da(A, arr):
    return A.template.copy(data=arr)


def map(A):
    """Panels: (1) corridors over PAs + IPCA anchors; (2) resistance; (3) ensemble frequency
    (if corridor_ensemble has run)."""
    has_freq = getattr(A, "frequency", None) is not None
    n = 3 if has_freq else 2
    fig, axes = plt.subplots(1, n, figsize=(7.5 * n, 12)); axes = np.atleast_1d(axes)
    pa_mask, anch = _node_masks(A)

    ax = axes[0]
    for layer, col in [(pa_mask, PA_COLOR), (anch, ANCHOR_COLOR), (A.corridor, CORRIDOR_COLOR)]:
        _da(A, np.where(layer, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    A.outline.boundary.plot(ax=ax, color="0.35", linewidth=1.0, linestyle="--")
    _frame_region(A, ax)
    ax.legend(handles=[Patch(color=PA_COLOR, label="existing PAs (nodes)"),
                       Patch(color=ANCHOR_COLOR, label="proposed IPCAs (nodes)"),
                       Patch(color=CORRIDOR_COLOR, label=f"least-cost corridors "
                             f"({A.corridor.sum()*A.cell_km2:,.0f} km²)"),
                       plt.Line2D([0], [0], color="0.35", ls="--", label="Y2Y corridor")],
              loc="lower left", fontsize=9, frameon=True)
    ax.set_title(f"{A.region_label} — least-cost corridors connecting the anchors")
    ax.set_aspect("equal"); ax.set_axis_off()

    ax2 = axes[1]
    _da(A, np.where(np.isfinite(A.resistance_arr), A.resistance_arr, np.nan).astype("float32")).plot.imshow(
        ax=ax2, cmap="magma_r", norm=LogNorm(), add_colorbar=True,
        cbar_kwargs=dict(label="resistance (log)", shrink=0.5))
    A.outline.boundary.plot(ax=ax2, color="0.35", linewidth=1.0, linestyle="--")
    _frame_region(A, ax2)
    ax2.set_title("Resistance (drivers blend, gHM barrier)")
    ax2.set_aspect("equal"); ax2.set_axis_off()

    if has_freq:
        ax3 = axes[2]
        _da(A, np.where(A.frequency > 0, A.frequency, np.nan).astype("float32")).plot.imshow(
            ax=ax3, cmap="viridis", vmin=0, vmax=1, add_colorbar=True,
            cbar_kwargs=dict(label="corridor frequency (robust=1)", shrink=0.5))
        # both node sets for context: existing PAs (grey) + proposed IPCAs (teal), same as panel 1
        for layer, col in [(pa_mask, PA_COLOR), (anch, ANCHOR_COLOR)]:
            _da(A, np.where(layer, 1.0, np.nan).astype("float32")).plot.imshow(
                ax=ax3, cmap=ListedColormap([col]), add_colorbar=False)
        A.outline.boundary.plot(ax=ax3, color="0.35", linewidth=1.0, linestyle="--")
        _frame_region(A, ax3)
        ax3.legend(handles=[Patch(color=PA_COLOR, label="existing PAs"),
                            Patch(color=ANCHOR_COLOR, label="proposed IPCAs")],
                   loc="lower left", fontsize=8, frameon=True)
        ax3.set_title(f"Robustness across {A.cfg['ensemble']['n_runs']} near-optimal runs")
        ax3.set_aspect("equal"); ax3.set_axis_off()

    fig.savefig(A.fig_dir / "corridors_map.png", dpi=150, bbox_inches="tight"); plt.show()
    return A


def _node_masks(A):
    pa_mask = np.zeros(A.shape, bool); anch = np.zeros(A.shape, bool)
    for (lbl, m), k in zip(A.nodes, A.kinds):
        (anch if k == "ipca" else pa_mask)[m] = True
    return pa_mask, anch


SHARED_COLOR = "#e6550d"   # corridor both scenarios agree on -- same orange as the corridor panels
ONLY_A_COLOR = "#7b3294"   # first scenario only (purple)
ONLY_B_COLOR = "#1f77b4"   # second scenario only (blue)


def _region_extent(A, pad=0.05):
    """Axis limits covering the WORKING REGION. Drawing A.outline expands the axes to the whole Y2Y
    corridor, which spends most of the canvas on the empty southern tail -- so re-apply these after
    the outline goes on. (map() deliberately keeps its wider framing.)"""
    xs, ys = A.template.x.values, A.template.y.values
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    dx, dy = (x1 - x0) * pad, (y1 - y0) * pad
    return (x0 - dx, x1 + dx), (y0 - dy, y1 + dy)


def _nodes_overlay(A, ax, XL, YL, pa_mask, anch, legend=False):
    for layer, col in [(pa_mask, PA_COLOR), (anch, ANCHOR_COLOR)]:
        _da(A, np.where(layer, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    A.outline.boundary.plot(ax=ax, color="0.35", linewidth=1.0, linestyle="--")
    ax.set_xlim(*XL); ax.set_ylim(*YL)
    if legend:
        ax.legend(handles=[Patch(color=PA_COLOR, label="existing PAs"),
                           Patch(color=ANCHOR_COLOR, label="proposed IPCAs")],
                  loc="lower left", fontsize=8, frameon=True)
    ax.set_aspect("equal"); ax.set_axis_off()


def _scenario_keys(A, keys):
    scen = getattr(A, "scenarios", None)
    if not scen:
        raise ValueError("no scenarios on A — run cc.run_scenarios(A) first")
    return scen, (list(keys) if keys else list(scen))


def compare_resistance(A, keys=None, pad=0.05):
    """The resistance surfaces side by side, on a SHARED log colour scale so the scenarios are
    actually comparable (they span different ranges — the whole point of the anchor choice).
    Kept out of compare_map so the corridor panels stay clean."""
    scen, keys = _scenario_keys(A, keys)
    XL, YL = _region_extent(A, pad)
    pa_mask, anch = _node_masks(A)

    finite = [s["resistance_arr"][np.isfinite(s["resistance_arr"])] for s in (scen[k] for k in keys)]
    vmin = min(np.percentile(f, 1) for f in finite)
    vmax = max(np.percentile(f, 99) for f in finite)

    panel_h = 9.0
    panel_w = panel_h * (XL[1] - XL[0]) / (YL[1] - YL[0])
    fig, axes = plt.subplots(1, len(keys), figsize=(panel_w * len(keys) + 2.0, panel_h))
    axes = np.atleast_1d(axes)

    im = None
    for ax, key in zip(axes, keys):
        s = scen[key]
        lo, hi = s["anchors"]
        primary = " (primary)" if key == getattr(A, "primary_scenario", None) else ""
        im = _da(A, np.where(np.isfinite(s["resistance_arr"]), s["resistance_arr"], np.nan
                             ).astype("float32")).plot.imshow(
            ax=ax, cmap="magma_r", norm=LogNorm(vmin=vmin, vmax=vmax), add_colorbar=False)
        _nodes_overlay(A, ax, XL, YL, pa_mask, anch, legend=(ax is axes[0]))
        r = s["resistance_arr"][A.pu]
        ax.set_title(f"{key} — stretch p{lo}/p{hi}{primary}\n"
                     f"p5 {np.percentile(r,5):.1f} | p50 {np.percentile(r,50):.1f} | "
                     f"p95 {np.percentile(r,95):.0f} | spread {s['spread']:.0f}x", fontsize=11)

    fig.colorbar(im, ax=list(axes), label="resistance (log, shared scale) — low = preferred",
                 shrink=0.6, fraction=0.03, pad=0.02)
    fig.suptitle(f"{A.region_label} — resistance surface by driver-stretch scenario", fontsize=15)
    fig.savefig(A.fig_dir / "corridors_scenario_resistance.png", dpi=130, bbox_inches="tight")
    plt.show()
    return A


def compare_map(A, keys=None, pad=0.05):
    """Scenario comparison: one row per scenario (corridors | ensemble robustness) plus a
    difference panel when exactly two are compared.

    The resistance surfaces live in compare_resistance() so these panels stay clean."""
    scen, keys = _scenario_keys(A, keys)
    has_freq = all(scen[k]["frequency"] is not None for k in keys)
    ncol = 2 if has_freq else 1
    show_diff = len(keys) == 2
    total_col = ncol + (1 if show_diff else 0)

    XL, YL = _region_extent(A, pad)
    pa_mask, anch = _node_masks(A)

    def _nodes(ax, legend=False):
        _nodes_overlay(A, ax, XL, YL, pa_mask, anch, legend)

    panel_h = 9.0
    panel_w = panel_h * (XL[1] - XL[0]) / (YL[1] - YL[0])
    fig = plt.figure(figsize=(panel_w * total_col + 2.0, panel_h * len(keys)))
    gs = fig.add_gridspec(len(keys), total_col)

    for i, key in enumerate(keys):
        s = scen[key]
        lo, hi = s["anchors"]
        primary = " (primary)" if key == getattr(A, "primary_scenario", None) else ""
        ax = fig.add_subplot(gs[i, 0])
        _da(A, np.where(s["corridor"], 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([CORRIDOR_COLOR]), add_colorbar=False)
        _nodes(ax, legend=(i == 0))
        ax.set_title(f"{key} — stretch p{lo}/p{hi}{primary}\n"
                     f"{int(s['corridor'].sum())*A.cell_km2:,.0f} km² swath | "
                     f"{s['base_path_cells']} centre-line cells | {s['n_groups']} group | "
                     f"resistance spread {s['spread']:.0f}x", fontsize=11)

        if has_freq:
            axf = fig.add_subplot(gs[i, 1])
            _da(A, np.where(s["frequency"] > 0, s["frequency"], np.nan).astype("float32")).plot.imshow(
                ax=axf, cmap="viridis", vmin=0, vmax=1, add_colorbar=True,
                cbar_kwargs=dict(label="corridor frequency (robust=1)", shrink=0.6,
                                 fraction=0.04, pad=0.01))
            _nodes(axf)
            core = int((s["frequency"] >= 0.9).sum()) * A.cell_km2
            ever = int((s["frequency"] > 0).sum()) * A.cell_km2
            prem = [a["premium"] for a in s["alternatives"]]
            axf.set_title(f"{key} — robustness over {s['cfg']['ensemble']['n_runs']} runs "
                          f"(jitter ±{s['cfg']['ensemble']['jitter']:.0%})\n"
                          f"robust core {core:,.0f} km² of {ever:,.0f} km² ever-used | "
                          f"alt length premium {min(prem):+.1%}..{max(prem):+.1%}", fontsize=11)

    if show_diff:
        a, b = (scen[k]["corridor"] for k in keys)
        d = np.full(A.shape, np.nan, "float32")
        d[a & b] = 0.0; d[a & ~b] = 1.0; d[~a & b] = 2.0
        axd = fig.add_subplot(gs[:, ncol])
        _da(A, d).plot.imshow(ax=axd, cmap=ListedColormap([SHARED_COLOR, ONLY_A_COLOR, ONLY_B_COLOR]),
                              vmin=-0.5, vmax=2.5, add_colorbar=False)
        _nodes(axd)
        axd.legend(handles=[
            Patch(color=SHARED_COLOR, label=f"shared ({(a & b).sum()*A.cell_km2:,.0f} km²)"),
            Patch(color=ONLY_A_COLOR, label=f"{keys[0]} only ({(a & ~b).sum()*A.cell_km2:,.0f} km²)"),
            Patch(color=ONLY_B_COLOR, label=f"{keys[1]} only ({(~a & b).sum()*A.cell_km2:,.0f} km²)"),
            Patch(color=PA_COLOR, label="existing PAs"),
            Patch(color=ANCHOR_COLOR, label="proposed IPCAs")],
            loc="lower left", fontsize=9, frameon=True)
        axd.set_title(f"Difference — Jaccard overlap {_jaccard(a, b):.2f}", fontsize=11)

    fig.suptitle(f"{A.region_label} — driver-stretch scenarios: corridors and near-optimal spread",
                 fontsize=15)
    fig.tight_layout()
    fig.savefig(A.fig_dir / "corridors_scenario_compare.png", dpi=130, bbox_inches="tight")
    plt.show()
    return A


# ================= value profile (co-benefit audit) =================
def _profile_stacks(A):
    """A minimal stand-in for `results_core.build_stacks`, on 05's grid.

    build_stacks is coupled to a SOLVED prioritizr run (it needs A.portfolio, _locked_mask,
    _cluster_profile). The primitives underneath it are not — `_scaled` / `_read_match` /
    `_region_total` / `mask_profile` only need a grid reference and the feature layers. So we hand
    them a namespace whose grid IS the corridor grid, and 05 stays standalone from 03/04."""
    man = json.loads(pathlib.Path(config.MANIFEST_PATH).read_text())
    cont = [L for L in man["layers"] if L["role"] == "feature_continuous"]
    efg = [L for L in man["layers"] if L["role"] == "feature_efg"]
    P = types.SimpleNamespace(
        sol0=A.template, agg=1, manifest=man, fig_dir=A.fig_dir,
        cont=[L["name"] for L in cont], efg=[L["name"] for L in efg],
        cell_km2=A.cell_km2, cell_ha=A.cell_km2 * 100.0)
    P.axes_labels = [n.replace("_", " ") for n in P.cont] + ["EFG (mean)"]
    print(f"  building {len(cont)} continuous + {len(efg)} EFG stacks on the corridor grid…")
    P.cont_stack = np.stack([rc._scaled(P, L["path"]) for L in cont])      # 0-1, scaled over WINDOW
    P.cont_raw = np.stack([rc._read_match(P, L["path"]) for L in cont])    # native units
    P.efg_stack = np.stack([rc._scaled(P, L["path"]) for L in efg])
    P.efg_raw = np.stack([rc._read_match(P, L["path"]) for L in efg])
    P.cont_region = np.array([rc._region_total(P, L["path"]) for L in cont])   # FULL-Y2Y denominators
    P.cont_region[P.cont_region == 0] = np.nan
    P.efg_region = np.array([rc._region_total(P, L["path"]) for L in efg])
    P.efg_region[P.efg_region == 0] = np.nan
    P.n_region_full = rc._region_total(P, rc.cost_path(P))                     # full-Y2Y PU count
    return P


_GENERIC = {"park", "protected", "area", "national", "reserve", "of", "canada",
            "provincial", "wildland", "wilderness", "recreation", "conservancy", "sma/wa"}


def _short_node_name(label, width=16):
    """Compact a node label for star-plot titles: drop the IPCA·/PA· prefix, the parenthetical or
    dash-suffixed alternate name, and generic designations ('Nahanni National Park Reserve Of
    Canada' -> 'Nahanni'). Truncates on a word boundary so names never break mid-word."""
    s = label.split(" · ", 1)[-1].split(" (", 1)[0].split(" - ", 1)[0].strip()
    kept = [w for w in s.split() if w.lower().strip(",") not in _GENERIC]
    s = " ".join(kept) or s
    if len(s) > width:
        cut = s[:width].rsplit(" ", 1)[0]
        s = (cut if len(cut) >= width // 2 else s[:width]) + "…"
    return s


def _corridor_groups(A, corr, nodes, n_groups):
    """Split the corridor's own land into geographic segments, numbered north -> south.

    Removing the node polygons cuts the network at every PA/IPCA, so the connected components ARE
    the physical links between protected areas — no arbitrary clustering needed. Keeps the
    `n_groups` largest (currently the top 10 hold ~94% of corridor area) and reports the remainder
    rather than dropping it silently. Each segment is named by the nodes it actually touches."""
    lab, n = ndimage.label(corr & ~nodes, structure=np.ones((3, 3), int))
    cnt = np.bincount(lab.ravel())
    order = sorted(range(1, n + 1), key=lambda i: cnt[i], reverse=True)
    keep, rest = order[:n_groups], order[n_groups:]

    # node-id raster once, so each segment's touching nodes is a single unique() per segment
    node_id = np.zeros(A.shape, np.int16)
    for k, (_, m) in enumerate(A.nodes, 1):
        node_id[m] = k
    lat = pyproj.Transformer.from_crs(A.crs, "EPSG:4326", always_xy=True)

    segs = []
    for cid in keep:
        m = lab == cid
        touch = np.unique(node_id[ndimage.binary_dilation(m, np.ones((3, 3), bool))])
        names = [A.nodes[k - 1][0] for k in touch if k > 0]
        r, c = np.nonzero(m)
        y = lat.transform(A.template.x.values[c].mean(), A.template.y.values[r].mean())[1]
        segs.append(dict(cid=cid, mask=m, cells=int(cnt[cid]), lat=y, ends=names))
    segs.sort(key=lambda s: -s["lat"])                       # number north -> south
    for j, s in enumerate(segs, 1):
        ends = " ↔ ".join(s["ends"][:2]) if len(s["ends"]) >= 2 else (s["ends"] or ["unattached"])[0]
        extra = f" +{len(s['ends'])-2}" if len(s["ends"]) > 2 else ""
        s["name"] = f"{j}. {ends}{extra}"                     # full — map legend + CSV
        # compact form for star-plot titles: a 4.8" polar panel cannot fit the full names, and
        # they collide with their neighbours.
        short = [_short_node_name(e) for e in s["ends"][:2]] or ["unattached"]
        s["short"] = f"{j}. {' ↔ '.join(short)}{extra}"
        s["color"] = rc.CLUSTER_CMAP((j - 1) % 10)
    dropped = int(sum(cnt[i] for i in rest))
    return segs, dropped, len(rest)


def corridor_profile(A, n_groups=10, scenario=None):
    """Value star plots for the corridor network — a CO-BENEFIT AUDIT, not a scorecard.

    The corridors are routed for PERMEABILITY, never for conservation value, so a low carbon or EFG
    axis is not a failure — it is the finding that connection and representation are different
    objectives. Compares three areas on shared axes: the corridor's OWN new land, the proposed
    IPCAs, and the existing PAs = what the connective tissue adds over the protected areas.

    The corridor mask is `corridor & ~nodes`: swath bands radiate outward from the nodes, so ~37% of
    the raw swath lies INSIDE PA/IPCA polygons and profiling it whole would credit the corridors
    with already-protected land.

    Two different scalings share these figures — say which is which when reading them:
      richness              = 0-1 over the WORKING REGION (5-95 pctile), i.e. relative to the north
      contribution/efficiency = FULL-Y2Y denominators, i.e. literally "% of Y2Y"
    """
    corr = A.scenarios[scenario]["corridor"] if scenario else A.corridor
    tag = f" [{scenario}]" if scenario else ""
    pa_mask, anch = _node_masks(A)
    nodes = pa_mask | anch

    # corridors split into geographic segments; the PA sets stay WHOLE units for comparison
    if n_groups:
        segs, dropped, n_rest = _corridor_groups(A, corr, nodes, n_groups)
        A.groups = segs
        areas = [(s["name"], s["mask"], s["color"]) for s in segs]
        print(f"corridor segments: {len(segs)} kept of {len(segs)+n_rest} components "
              f"({100*sum(s['cells'] for s in segs)/max((corr & ~nodes).sum(),1):.0f}% of corridor "
              f"area); {n_rest} smaller segments totalling {dropped*A.cell_km2:,.0f} km² not plotted")
    else:
        A.groups = None
        areas = [("corridor (new land)", corr & ~nodes, CORRIDOR_COLOR)]
    areas += [("proposed IPCAs", anch, ANCHOR_COLOR), ("existing PAs", pa_mask, PA_COLOR)]

    # star titles use the compact segment names (the full ones collide); the map legend and the
    # CSV carry the full "X <-> Y" naming.
    short = {s["name"]: s["short"] for s in (A.groups or [])}
    P = _profile_stacks(A)
    C = dict(ids=[n for n, _, _ in areas], colors={n: c for n, _, c in areas},
             names={n: short.get(n, n) for n, _, _ in areas},
             cnt={n: int(m.sum()) for n, m, _ in areas},
             profs={}, contrib={}, eff={}, raw={})
    for name, m, _ in areas:
        C["profs"][name], C["contrib"][name], C["eff"][name], C["raw"][name] = rc.mask_profile(P, m)

    print(f"\nvalue profile{tag} (area denominators = full Y2Y, {P.n_region_full:,.0f} PU):")
    for name, m, _ in areas:
        print(f"  {name[:44]:44s} {int(m.sum())*A.cell_km2:8,.0f} km²  "
              f"({100*int(m.sum())/P.n_region_full:.2f}% of Y2Y)")
    print(f"  overlap check: {100*(corr & nodes).sum()/max(corr.sum(),1):.0f}% of the raw swath sits "
          f"inside node polygons and is EXCLUDED from the corridor rows")

    for metric in ("richness", "contribution", "efficiency"):
        rc.plot_stars(P, C, metric,
                      f"{A.region_label} — corridor co-benefits vs protected areas{tag}\n"
                      f"corridors are routed for permeability, not value",
                      f"corridors_stars_{metric}.png")

    rows = []
    for name, m, _ in areas:
        km2 = int(m.sum()) * A.cell_km2
        base = dict(area=name, km2=round(km2), pct_y2y=round(100 * int(m.sum()) / P.n_region_full, 2))
        for j, ax in enumerate(P.axes_labels):
            base[f"{ax} | richness"] = round(C["profs"][name][j], 3)
            base[f"{ax} | contribution %"] = round(C["contrib"][name][j], 2)
            base[f"{ax} | efficiency"] = round(C["eff"][name][j], 3)
        rows.append(base)
    df = pd.DataFrame(rows)
    out = A.run_dir / "corridor_profile.csv"
    # utf-8-SIG: segment names carry Indigenous place names (Tū Łī́dlini, Dene Kʼéh Kusān, Wədzih
    # Yiné') plus · and ↔. Excel on macOS assumes Mac Roman without a BOM and mangles every one of
    # them. The BOM makes it read UTF-8 — the names are never stripped or transliterated.
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"  wrote {out.name}")
    A.profile = dict(P=P, C=C, table=df)
    return A


def corridor_group_map(A, pad=0.05):
    """Numbered map of the corridor segments, matching the star-plot numbering (both read
    A.groups, so the numbers can never drift apart). Run corridor_profile first."""
    segs = getattr(A, "groups", None)
    if not segs:
        raise ValueError("no corridor segments on A — run cc.corridor_profile(A) first")
    XL, YL = _region_extent(A, pad)
    pa_mask, anch = _node_masks(A)

    panel_h = 11.0
    fig, ax = plt.subplots(figsize=(panel_h * (XL[1]-XL[0]) / (YL[1]-YL[0]) + 4.0, panel_h))
    for layer, col in [(pa_mask, PA_COLOR), (anch, ANCHOR_COLOR)]:
        _da(A, np.where(layer, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    for s in segs:
        _da(A, np.where(s["mask"], 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([s["color"]]), add_colorbar=False)
        r, c = np.nonzero(s["mask"])
        ax.annotate(s["name"].split(".")[0], (A.template.x.values[c].mean(), A.template.y.values[r].mean()),
                    fontsize=11, fontweight="bold", ha="center", va="center",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec=s["color"], lw=1.6))
    A.outline.boundary.plot(ax=ax, color="0.35", linewidth=1.0, linestyle="--")
    ax.set_xlim(*XL); ax.set_ylim(*YL); ax.set_aspect("equal"); ax.set_axis_off()
    ax.legend(handles=[Patch(color=PA_COLOR, label="existing PAs"),
                       Patch(color=ANCHOR_COLOR, label="proposed IPCAs")] +
                      [Patch(color=s["color"], label=f"{s['name'][:52]} "
                             f"({s['cells']*A.cell_km2:,.0f} km²)") for s in segs],
              loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=9, frameon=True)
    ax.set_title(f"{A.region_label} — corridor segments (numbered north → south)")
    fig.savefig(A.fig_dir / "corridors_segments_map.png", dpi=150, bbox_inches="tight")
    plt.show()
    return A
