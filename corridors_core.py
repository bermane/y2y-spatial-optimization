"""Least-cost corridor engine (05, v2) -- connect anchor areas with routed corridors.

The prioritizr connectivity PENALTY could not connect the northern IPCAs: it rewards aggregating
on permeable land, not routing between two specific nodes. This does the routing directly --
least-cost paths (Linkage-Mapper style) between every anchor over a published movement-cost
surface.

v2 REBUILD (2026-08-07, decisions D1-D10 in docs/05_methods_v2.md). See config.CORRIDORS for the
per-decision rationale. In one paragraph: resistance is no longer a weighted blend of three
regional products but the published O'Brien/Pither transboundary movement-cost surface (D1/D2);
the corridor band is an absolute cost-weighted-distance cutoff rather than a fraction of edge cost
(D6); the network is an MST plus bridge-backup augmentation rather than a bare tree with no
redundancy (D7); uncertainty comes from a structured ensemble over interpretable axes rather than
uniform noise on the resistance surface (D8); and routing runs at the cost surface's native 300 m
so linear barriers survive.

TWO GRIDS. Routing is 300 m (`A.template`); the co-benefit audit is 1 km (`A.audit_template`).
That split is a correctness requirement, not an optimisation: every value layer is natively 1 km,
and `results_core.mask_profile` sums a feature over the mask while `results_core._region_total`
computes the denominator at native 1 km with no finer-than-source path -- profiling a 300 m mask
would inflate every "% of Y2Y" figure ~11x while looking entirely plausible.

One function per stage so a thin 05 notebook keeps cell-by-cell inspection:
    A = start("north"); resistance(A); cost_distances(A); corridor_network(A)
    map(A); corridor_profile(A); finish(A)
Params come from run_config.json inside the run dir -- never from config.CORRIDORS directly, so a
run is reproducible from its own directory. Pure Python (skimage.graph.MCP_Geometric).
"""
import json
import types
import copy
import hashlib
import itertools
import pathlib
import subprocess
import time
import pandas as pd

import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, LogNorm
from matplotlib.patches import Patch
import rioxarray
import xarray as xr
import geopandas as gpd
from rasterio.enums import Resampling
from rasterio.features import rasterize, shapes
from shapely.geometry import shape as _shape
from skimage.graph import MCP_Geometric
from scipy import ndimage
from collections import defaultdict
import pyproj

import config
import corridor_graph as cg
import results_core as rc
from results_core import PA_COLOR, ANCHOR_COLOR   # shared map colours

CORRIDOR_COLOR = "#e6550d"   # routed corridors (orange), distinct from grey PAs + teal anchors

# The 1 km hand-off layer that defines the AUDIT grid. Pinned deliberately: results_core._read_match
# reproject-matches every feature onto whatever grid it is handed, so if this ever became the 300 m
# cost raster every profile would silently change (and "% of Y2Y" would inflate ~11x -- the
# denominator in _region_total is computed at native 1 km with no finer-than-source path).
AUDIT_TEMPLATE = "cost_uniform.tif"


class _NS(types.SimpleNamespace):
    """SimpleNamespace with a ONE-LINE repr.

    Every cc.* function ends `return A` so calls can chain, and Jupyter echoes that return value
    after each cell — under the default repr that dumps the entire config, every scenario snapshot
    and the profile DataFrame after every single cell."""

    def __repr__(self):
        # Every access stays getattr-guarded: this runs after EVERY notebook cell, so a missing
        # attribute surfaces as a confusing Jupyter display error rather than a clean traceback.
        bits = [str(getattr(self, "run_id", None) or getattr(self, "key", "?"))]
        if getattr(self, "nodes", None) is not None:
            bits.append(f"{len(self.nodes)} nodes")
        if getattr(self, "shape", None):
            bits.append(f"{self.shape[1]}x{self.shape[0]}")
        if getattr(self, "edges", None) is not None:
            bits.append(f"{len(self.edges)} edges")
        if getattr(self, "corridor", None) is not None:
            bits.append(f"corridor {int(self.corridor.sum()) * self.cell_km2:,.0f} km²")
        if getattr(self, "groups", None):
            bits.append(f"{len(self.groups)} segments")
        return f"<corridors {' | '.join(bits)}>"


# ================= run dirs (the v2 config contract) =================
# config.CORRIDORS[key] is the EDITABLE BASELINE. A run resolves it, writes the resolved dict to
# run_config.json inside its own directory, and from then on reads only from that file. Same
# doctrine as ensemble_core's "patch a copy of the manifest, never mutate config.py": config.py
# stays one source of truth, every deviation is an explicit override recorded beside its outputs,
# and any single run is reproducible from its own directory alone.
#
# The provenance block is load-bearing rather than decorative: output_data/ is gitignored, so the
# run dir is the ONLY record that survives. Without the git SHA and the input hashes there is no
# way to tell later which code and which raster produced a given corridor.

# Config keys retired by the v2 rebuild. resolve() RAISES on each rather than ignoring it -- that
# is the enforcement of D2's "no dead flags", and it stops a stale config.py from silently
# producing a run that looks fine but was configured for the v1 engine.
_DEAD_KEYS = {
    "resistance.scale":        "D2 -- percentile stretch retired with the blend",
    "resistance.drivers":      "D1/D2 -- resistance is one published cost surface, not a blend",
    "resistance.conn_exponent": "D2 -- uncalibrated blend sharpener, retired",
    "resistance.barrier":      "D2 -- gHM barrier double-counted footprint already in the cost surface",
    "resistance.perm_floor":   "D2 -- retired with the permeability formulation",
    "corridor_width_frac":     "D6 -- replaced by cwd_cutoff_abs (absolute cost units)",
    "scenarios":               "replaced by 'variants' (an override dict per named run)",
    "primary_scenario":        "replaced by 'variants'",
    "alpha":                   "D7 -- the alpha criterion was vacuous; replaced by 'beta'",
    "nodes.node_min_cells":    "resolution-dependent; replaced by nodes.node_min_km2",
    "region_filter":           "moved into grid.region_filter (applied by corridors_prep)",
    "ensemble.n_runs":         "D8 -- jitter ensemble retired",
    "ensemble.jitter":         "D8 -- jitter ensemble retired",
    "ensemble.n_alternatives": "D8 -- jitter ensemble retired",
    "branch_min_km2":          "D26 (2026-09-28) -- a fixed km2 sliver floor is length-biased; replaced by branch_min_frac x band area AND branch_min_cells",
    "only_viable_ratio":       "D23 (2026-09-28) -- squeeze_ratio is the ONLY width threshold (no second width / ratio key)",
    "route_width_thresh":      "D23 (2026-09-28) -- squeeze_ratio is the ONLY width threshold (no second width / ratio key)",
}


def _dig(cfg, dotted):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


def _merge(base, over):
    """Recursive dict merge; `over` wins. Used for variants and ensemble overrides."""
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def _sha256(path, cap=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            if cap and f.tell() > cap:
                break
    return h.hexdigest()


def _git():
    def run(*a):
        p = subprocess.run(["git", *a], cwd=config.PROJECT_DIR, capture_output=True, text=True)
        return p.stdout.strip() if p.returncode == 0 else None
    return {"sha": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain"))}


# Keys the 2026-08-21 addendum PRE-REGISTERS (spec §2). resolve() raises when one is absent --
# the same no-dead-flags doctrine as _DEAD_KEYS, pointed the other way: a config predating the
# addendum must not silently produce a run missing the D11/D12/D16 products.
_REQUIRED_ADDENDUM_KEYS = [
    "branch_mult", "branch_min_frac", "branch_min_cells", "near_opt_tiers",   # D11/D12 (D26: relative sliver floor)
    "alt_res_tol",                                                  # D29
    "width_floor_cells", "len_floor_cells",                         # D24
    "part_min_km2", "multisite_designations", "multipart_link_km",  # D16
    "carroll_ref", "audit_objects_dir",                             # D14 / H7
    "squeeze_ratio", "squeeze_cf_min_cost",                         # D17
]


def resolve(key, overrides=None, require_cutoff=True):
    """config.CORRIDORS[key] + overrides -> a validated, fully resolved run config."""
    cfg = _merge(config.CORRIDORS[key], overrides)

    dead = [f"  {k}  ({why})" for k, why in _DEAD_KEYS.items() if _dig(cfg, k)]
    if dead:
        raise ValueError("config.CORRIDORS[%r] still carries v1 keys retired by the v2 rebuild:\n%s"
                         % (key, "\n".join(sorted(dead))))

    def _val(dotted):
        cur = cfg
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]
        return cur

    missing = [k for k in _REQUIRED_ADDENDUM_KEYS if _val(k) is None]
    if missing:
        raise ValueError(
            f"config.CORRIDORS[{key!r}] is missing addendum-required keys: {missing}. These are "
            f"pre-registered constants (spec §2 of the 2026-08-21 addendum) and must be set in "
            f"config.py BEFORE cc.start().")

    # D31 (2026-09-28): the cutoff stated as detour distance on open ground -- cost-1 cells x cell size. The northern network
    # keeps its v1 AREA calibration (D6); a derived analysis with no v1 target SETS cutoff_detour_km and the cost cutoff is
    # derived from it (never calibrated by area or by class counts). Both are written; they must agree.
    cell_km = float(cfg["grid"]["res_m"]) / 1000.0
    if cfg.get("cwd_cutoff_abs") is None and cfg.get("cutoff_detour_km") is not None:
        cfg["cwd_cutoff_abs"] = float(cfg["cutoff_detour_km"]) / cell_km
    if cfg.get("cwd_cutoff_abs") is not None:
        want = float(cfg["cwd_cutoff_abs"]) * cell_km
        if cfg.get("cutoff_detour_km") is not None and abs(float(cfg["cutoff_detour_km"]) - want) > 1e-6 * max(want, 1e-9):
            raise ValueError(f"config.CORRIDORS[{key!r}]: cutoff_detour_km {cfg['cutoff_detour_km']} disagrees with cwd_cutoff_abs x cell "
                             f"size = {want:.6f} km (D31) -- set ONE of them")
        cfg["cutoff_detour_km"] = want
    if require_cutoff and cfg.get("cwd_cutoff_abs") is None:
        raise ValueError(
            f"config.CORRIDORS[{key!r}]['cwd_cutoff_abs'] is None. The absolute band cutoff (D6) is "
            f"CALIBRATED, not guessed: run cc.calibrate_cutoff(A) once, then write the value into "
            f"config.py with the area it reproduces. Pass require_cutoff=False to build a run for "
            f"the calibration itself.")

    gc = cfg["grid"]
    cost = gc["dir"] / cfg["resistance"]["out_name"]
    if not cost.exists():
        raise FileNotFoundError(
            f"{cost} not found -- run corridors_prep first:\n"
            f"    import corridors_prep as cp; g = cp.grid({key!r}); cp.warp(g); cp.check(g)")
    # raster node source (wolverine, W2): the class raster must already be warped onto the SAME grid
    nc = cfg.get("nodes", {})
    if nc.get("source", "vector") == "raster":
        cls_path = gc["dir"] / nc["raster"]["out_name"]
        if not cls_path.exists():
            raise FileNotFoundError(
                f"{cls_path} not found -- warp the node raster onto the routing grid first:\n"
                f"    cp.warp_classes(g, {key!r}); cp.check_classes(g, {key!r})   (notebook 01)")
    return cfg, cost


# ---- H7 artifacts (D16) -----------------------------------------------------------------
# The canonical node_parts.csv/.gpkg + multipart_review.csv live GIT-TRACKED in
# cfg["audit_objects_dir"] (output_data/ is gitignored and later runs must reproduce the review
# hash). new_run() copies them into the run dir and pins their sha256 in run_config.json, so each
# run dir stays self-contained; load() then reads ONLY the run-dir copies.
_H7_FILES = ("node_parts.csv", "node_parts.gpkg", "multipart_review.csv")
# Raster-node analyses (wolverine) carry an optional human NAMING file beside the H7-format
# node_parts files: node_names.csv (display_name per node_id). Copied + hash-pinned like the H7
# files when present; absent in the north.
_NODE_FILES = ("node_names.csv",
               # v3 contraction (D-W3): the membership + names + geometry + the v2 sliver table, pinned like the H7 files
               "complex_membership.csv", "complex_names.csv", "complexes.gpkg", "slivers_v2.csv", "complexes_summary.json", "fronts_v2.gpkg")


def _review_signed(path):
    """True when the review file carries a filled `reviewed_by` line (the H7 signature)."""
    path = pathlib.Path(path)
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.lstrip("# ").strip()
        if s.lower().startswith("reviewed_by"):
            rest = s.split(":", 1)[-1].split(",", 1)[-1] if ":" in s or "," in s else ""
            if rest.strip():
                return True
    return False


def read_review(path):
    """multipart_review.csv -> {name label: treatment}. Validates the treatment vocabulary."""
    allowed = {"merge_parts", "link_locked", "link_competing", "no_link"}
    df = pd.read_csv(path, comment="#", encoding="utf-8-sig")
    treatments = {}
    for r in df.itertuples():
        t = str(r.proposed).strip()
        if t not in allowed:
            raise ValueError(f"multipart_review.csv: name {r.name_label!r} has treatment {t!r}, "
                             f"expected one of {sorted(allowed)}")
        treatments[str(r.name_label)] = t
    return treatments


def new_run(key, overrides=None, label="", run_id=None, require_cutoff=True, require_review=True):
    """Create the next run dir and write its run_config.json. Refuses to clobber an existing run.

    require_review (H7): the run must not proceed to CWD until multipart_review.csv exists in
    cfg["audit_objects_dir"] AND carries a filled `reviewed_by` line. The signed file + node_parts
    are copied into the run dir and hash-pinned, so re-running step 0a later cannot silently
    change what this run was built on.
    """
    cfg, cost = resolve(key, overrides, require_cutoff)
    root = config.RESULTS_DIR / cfg["results_subdir"]
    root.mkdir(parents=True, exist_ok=True)

    audit_dir = pathlib.Path(cfg["audit_objects_dir"])
    review = audit_dir / "multipart_review.csv"
    h7 = {}
    if require_review:
        if not (audit_dir / "node_parts.csv").exists():
            raise FileNotFoundError(
                f"{audit_dir / 'node_parts.csv'} not found -- run step 0a first: "
                f"cc.node_parts({key!r}) (notebook 01), then review + sign multipart_review.csv (H7).")
        if not _review_signed(review):
            raise ValueError(
                f"H7 GATE: {review} is missing or unsigned. Edit the `proposed` column where the "
                f"step-0a rules got it wrong, then fill in the `# reviewed_by:` line. The run does "
                f"not proceed to CWD until the file is signed.")
        read_review(review)                      # vocabulary check before anything is written
    for f in _H7_FILES + _NODE_FILES:
        src = audit_dir / f
        if src.exists():
            h7[f] = {"path": str(_jsonable(src)), "sha256": _sha256(src)}

    if run_id is None:
        used = [int(p.name[6:]) for p in root.glob("v[0-9]_run[0-9][0-9][0-9]") if p.is_dir()]
        run_id = f"v2_run{max(used, default=0) + 1:03d}"
    run_dir = root / run_id
    if run_dir.exists():
        raise FileExistsError(f"{run_dir} already exists -- pass a new run_id, or delete it first")
    run_dir.mkdir(parents=True)
    (run_dir / "figures").mkdir()

    import shutil
    for f in h7:
        shutil.copy2(audit_dir / f, run_dir / f)

    rec = {
        "run_id": run_id, "key": key, "label": label,
        "engine": "corridors_core v2",
        "git": _git(),
        "versions": {"numpy": np.__version__, "networkx": nx.__version__,
                     "rasterio": __import__("rasterio").__version__,
                     "gdal": _gdal_version()},
        "inputs": {
            "movement_cost": {"path": str(cost.relative_to(config.PROJECT_DIR)),
                              "sha256": _sha256(cost)},
            "movement_cost_source": {"path": str(cfg["resistance"]["source"].relative_to(config.PROJECT_DIR)),
                                     "sha256": _sha256(cfg["resistance"]["source"])},
            "audit_template": str((config.HANDOFF_DIR / AUDIT_TEMPLATE).relative_to(config.PROJECT_DIR)),
            "pa_vector": str(config.PA_VECTOR.relative_to(config.PROJECT_DIR)),
            "proposed_pa": cfg["nodes"].get("proposed") or (cfg["nodes"].get("protected") or {}).get("proposed"),
            **h7,                       # H7 artifacts, hash-pinned (D16)
            **_extra_inputs(cfg, cost),  # raster node source + variant meta (wolverine), when present
        },
        "overrides": _jsonable(overrides or {}),      # a variant override carries Paths (wolverine): project-relative strings
        "cfg": _jsonable(cfg),
    }
    (run_dir / "run_config.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False))
    print(f"run {run_id}" + (f" ({label})" if label else "") +
          f" -> {run_dir.relative_to(config.PROJECT_DIR)}")
    if rec["git"]["dirty"]:
        print("  NOTE working tree is dirty; the recorded git SHA does not fully describe this run")
    return run_dir


def _gdal_version():
    p = subprocess.run(["gdalinfo", "--version"], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


def _extra_inputs(cfg, cost):
    """Provenance rows that exist only for raster-node / variant-surface runs (wolverine)."""
    out = {}
    nc = cfg.get("nodes", {})
    if nc.get("source", "vector") == "raster":
        src = pathlib.Path(nc["raster"]["source"])
        warped = pathlib.Path(cfg["grid"]["dir"]) / nc["raster"]["out_name"]
        out["nodes_raster"] = {"source": {"path": str(_jsonable(src)), "sha256": _sha256(src)},
                               "warped": {"path": str(_jsonable(warped)), "sha256": _sha256(warped)},
                               "classes_core": nc["classes_core"], "classes_marginal": nc["classes_marginal"]}
    meta = pathlib.Path(str(cost) + ".meta.json")
    if meta.exists():
        out["resistance_variant"] = {"path": str(_jsonable(meta)), "sha256": _sha256(meta),
                                     "meta": json.loads(meta.read_text())}
    return out


def _jsonable(o):
    """Paths -> project-relative strings, so run_config.json carries no absolute home paths."""
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, pathlib.Path):
        try:
            return str(o.relative_to(config.PROJECT_DIR))
        except ValueError:
            return str(o)
    return o


def runs(key="north"):
    """Index of every run under this analysis, newest last."""
    root = config.RESULTS_DIR / config.CORRIDORS[key]["results_subdir"]
    rows = []
    for d in sorted(root.glob("v[0-9]_run*")):
        rc = d / "run_config.json"
        if not rc.exists():
            continue
        r = json.loads(rc.read_text())
        row = {"run_id": r["run_id"], "label": r.get("label", ""),
               "git": (r.get("git") or {}).get("sha", "")[:8], "done": False}
        s = d / "corridor_summary.json"
        if s.exists():
            sm = json.loads(s.read_text())
            row.update(done=True, corridor_km2=sm.get("corridor_km2"),
                       n_edges=sm.get("n_edges"), n_groups=sm.get("n_network_groups"))
        rows.append(row)
    return pd.DataFrame(rows)


# ================= setup =================
def _dedupe_nodes(raw, frac, cell_km2):
    """Merge nodes that are the SAME PLACE under two designations, e.g. Teetł'it Gwinjik inside the
    Peel Watershed SMA/WA, or Fishing Branch Wilderness Preserve inside its Habitat Protection Area.
    Both source layers mix designation tiers that nest, and neither is de-duplicated (the PA dissolve
    is by name only), so a nested pair enters as two nodes covering one piece of ground: it is
    double-counted in the node area and it spends an MST edge on a zero-distance link.

    Merge test is on the RASTERIZED masks, not the polygons -- a shared cell is exactly the condition
    that makes the node-to-node cost distance 0. Requires an overlap of `frac` of the SMALLER node,
    so genuine neighbours that merely abut are left alone: Dene Kʼéh Kusān wraps around 11 BC parks
    and clips each by a 2-63 km² sliver, but they are different places and stay separate nodes.

    Note this does not change the routing -- an MST over a zero-distance pair picks the zero edge and
    then connects the rest exactly as the merged node would. It corrects the accounting."""
    idx = [np.flatnonzero(m) for _, m, _ in raw]
    parent = list(range(len(raw)))
    def _find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i, j in itertools.combinations(range(len(raw)), 2):
        shared = np.intersect1d(idx[i], idx[j], assume_unique=True).size
        if shared >= frac * min(idx[i].size, idx[j].size):
            parent[_find(i)] = _find(j)
    groups = defaultdict(list)
    for i in range(len(raw)): groups[_find(i)].append(i)

    nodes, kinds, n_merges = [], [], 0
    for members in groups.values():
        members.sort(key=lambda i: -idx[i].size)             # largest member names the merged node
        lbl, m, kind = raw[members[0]]
        for i in members[1:]: m = m | raw[i][1]
        if len(members) > 1:
            absorbed = [raw[i][0].split("· ")[-1] for i in members[1:]]
            print(f"  merged node: {lbl} absorbs {', '.join(absorbed)} "
                  f"({idx[members[1]].size * cell_km2:,.0f} km² nested)")
            lbl = f"{lbl} (+{len(members)-1})"
            n_merges += 1
        nodes.append((lbl, m)); kinds.append(kind)
    return nodes, kinds, n_merges


def _grid_nodes(cfg, cost_path):
    """The 300 m routing grid cropped to the anchors + the rasterized, deduped NAMED areas.

    Shared by load() and node_parts() (step 0a) so the two can never disagree on the name set.
    Returns a namespace with NAME-level masks; the D16 part split happens on top (_apply_parts).
    """
    full = rioxarray.open_rasterio(cost_path, masked=True).squeeze()
    crs_full = full.rio.crs

    # ---- node GEOMETRIES first, so the grid can be cropped to them --------------------
    # Order matters at 300 m: the full warped window is 24.7 M cells and memory scales with array
    # size even where cells are invalid, so the grid is cropped to the anchors' bbox + a routing
    # buffer BEFORE anything is rasterized. Vectors are cheap to read, rasters are not.
    nc = cfg["nodes"]
    ipca = config._load_source(config.PROJECT_DIR / nc["proposed"],
                               nc.get("source_filter")).to_crs(crs_full)
    nfield = next(c for c in ipca.columns if "name" in c.lower())
    pas = None
    if nc.get("include_existing_pas"):
        pas = gpd.read_file(config.PA_VECTOR).to_crs(crs_full).dissolve(by="PA_Name").reset_index()
        pas = pas[pas.geometry.area / 1e6 >= nc["existing_pa_min_km2"]]
        # only PAs that fall inside the warped window are candidates
        wx0, wy0, wx1, wy1 = full.rio.bounds()
        pas = pas.cx[wx0:wx1, wy0:wy1]

    buf = cfg["grid"]["routing_buffer_km"] * 1000.0
    anchors = ipca if pas is None else gpd.GeoDataFrame(
        pd.concat([ipca[["geometry"]], pas[["geometry"]]], ignore_index=True), crs=crs_full)
    ax0, ay0, ax1, ay1 = anchors.total_bounds
    template = full.rio.clip_box(minx=ax0 - buf, miny=ay0 - buf, maxx=ax1 + buf, maxy=ay1 + buf)

    crs = template.rio.crs; transform = template.rio.transform(); shape = template.shape
    rx, ry = template.rio.resolution(); cell_km2 = abs(rx * ry) / 1e6; cell_km = abs(rx) / 1000.0
    cost = template.values.astype("float32")
    pu = np.isfinite(cost)
    print(f"{cfg['region_label']}: routing grid {shape[1]}x{shape[0]} @ {cell_km*1000:.0f} m "
          f"= {int(pu.sum()):,} routable cells ({int(pu.sum())*cell_km2:,.0f} km²)")
    print(f"  cropped from the {full.shape[1]}x{full.shape[0]} warped window "
          f"({100*(shape[0]*shape[1])/(full.shape[0]*full.shape[1]):.0f}% of its cells) "
          f"= anchors + {cfg['grid']['routing_buffer_km']} km routing buffer")

    # ---- rasterize nodes -------------------------------------------------------------
    # node_min_km2, not a cell count: at 300 m the v1 threshold of 25 CELLS would mean 2.25 km²
    # and would silently admit a different node set.
    min_cells = max(1, int(round(nc["node_min_km2"] / cell_km2)))

    def _rast(geom):
        return rasterize([(geom, 1)], out_shape=shape, transform=transform, fill=0,
                         dtype="uint8").astype(bool) & pu

    # designation evidence (D16 step 0a): the IPCA layer carries PA_TYPE; the PA layer has NO
    # designation attribute, so existing-PA designations are name-derived downstream (flagged).
    desig = {}
    nodes, dropped = [], []
    for _, row in ipca.iterrows():
        m = _rast(row.geometry)
        lbl = f"IPCA · {row[nfield]}"
        desig[lbl] = str(row["PA_TYPE"]) if "PA_TYPE" in ipca.columns and pd.notna(row.get("PA_TYPE")) else ""
        (nodes if m.sum() >= min_cells else dropped).append((lbl, m, "ipca"))
    if pas is not None:
        for _, row in pas.iterrows():
            m = _rast(row.geometry)
            if m.sum() >= min_cells:
                nodes.append((f"PA · {row['PA_Name']}", m, "pa"))

    nodes, kinds, n_merges = _dedupe_nodes(nodes, nc.get("dedupe_overlap_frac", 0.5), cell_km2)
    n_ipca = sum(k == "ipca" for k in kinds)
    print(f"nodes: {len(nodes)} ({n_ipca} IPCAs + {len(nodes)-n_ipca} existing PAs "
          f">= {nc['existing_pa_min_km2']} km²)  [min node size {nc['node_min_km2']} km² "
          f"= {min_cells} cells @ {cell_km*1000:.0f} m]")
    if dropped:
        print(f"  dropped {len(dropped)} IPCA(s) below {nc['node_min_km2']} km² in region: "
              + ", ".join(d[0].split('· ')[1] for d in dropped))

    node_union = np.zeros(shape, bool)
    for _, m in nodes:
        node_union |= m
    print(f"  node land: {int(node_union.sum()) * cell_km2:,.0f} km² (excluded from the corridor)")

    outline = gpd.read_file(config.CORRIDOR_REF).to_crs(crs)
    return _NS(cfg=cfg, template=template, cost=cost, crs=crs, transform=transform, shape=shape,
               pu=pu, cell_km2=cell_km2, cell_km=cell_km,
               names_raw=nodes, kinds_raw=kinds, n_dedupe_merges=n_merges, desig=desig,
               node_union=node_union, outline=outline)


# ================= raster nodes (wolverine refugia, W2/W9) =================
def _pa_polys(min_km2):
    pas = gpd.read_file(config.PA_VECTOR).dissolve(by="PA_Name").reset_index()
    pas["km2"] = pas.geometry.area / 1e6
    return pas[pas.km2 >= min_km2].reset_index(drop=True)


def _bearing8(dx, dy):
    import math
    ang = (math.degrees(math.atan2(dx, dy)) + 360) % 360
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int((ang + 22.5) // 45) % 8]


def _raster_nodes(cfg, cost_path, names_path=None, verbose=True):
    """Nodes = 8-connected components of the CORE refugia classes on the routing grid, >= the
    area floor (W2). Returns the SAME namespace shape as _grid_nodes (names_raw / kinds_raw /
    node_union / template / cost / pu ...) so every downstream stage runs unchanged, plus:
      node_id      int16 grid, 1..N numbered NORTH -> SOUTH (0 = not a node)
      refugia      uint8 class grid (the warped raster; nodata -> 0)
      marginal     bool grid of the marginal classes (map context only, W3)
      node_table   one row per node (area, centroid, lat/lon, auto-name, PA overlap, seam share)
      context_pa   bool grid of existing PAs >= context_pa_min_km2 (presentation only; NOT nodes)
      single_component_nodes / nodes_disjoint = True (D16 part split and dedupe are no-ops)
    ONE boolean array per node: the mask doubles as the seed part and the routing unit (see
    _apply_parts), which is what keeps 66 nodes x 47 M cells inside a 24 GB machine.
    The routing grid is the WHOLE warped window (the refugia span it; no bbox crop).
    Auto-naming (W9): the PA with the largest overlap (>= pa_overlap_min of the node), else the
    nearest PA + 8-point bearing; `names_path` (node_names.csv) overrides display names after a
    fingerprint check (GW3) so a stale naming file can never label the wrong patch.
    """
    nc = cfg["nodes"]; rcfg = nc["raster"]
    gdir = config.PROJECT_DIR / pathlib.Path(cfg["grid"]["dir"])
    full = rioxarray.open_rasterio(cost_path, masked=True).squeeze()
    cls_da = rioxarray.open_rasterio(gdir / rcfg["out_name"]).squeeze()
    assert cls_da.shape == full.shape and cls_da.rio.transform() == full.rio.transform(), (
        "GW1 FAILED: the refugia class warp is not on the cost surface's grid -- re-run "
        "cp.warp_classes + cp.check_classes")
    template = full
    crs = template.rio.crs; transform = template.rio.transform(); shape = template.shape
    rx, ry = template.rio.resolution(); cell_km2 = abs(rx * ry) / 1e6; cell_km = abs(rx) / 1000.0
    cost = template.values.astype("float32")
    pu = np.isfinite(cost)
    ref = np.nan_to_num(cls_da.values, nan=0).astype("uint8")
    ref[ref == int(rcfg.get("nodata", 255))] = 0
    del cls_da

    core = np.isin(ref, nc["classes_core"]) & pu
    marginal = np.isin(ref, nc["classes_marginal"]) & pu
    conn = int(nc.get("connectivity", 8))
    struct = np.ones((3, 3), int) if conn == 8 else ndimage.generate_binary_structure(2, 1)
    lab, n = ndimage.label(core, structure=struct)
    sizes = np.bincount(lab.ravel())[1:]
    min_cells = max(1, int(round(nc["node_min_km2"] / cell_km2)))
    if verbose:
        print(f"{cfg['region_label']}: routing grid {shape[1]}x{shape[0]} @ {cell_km*1000:.0f} m "
              f"= {int(pu.sum()):,} routable cells ({int(pu.sum())*cell_km2:,.0f} km²) -- whole window")
        print(f"  core refugia {int(core.sum())*cell_km2:,.0f} km² in {n:,} {conn}-connected patches; "
              f"marginal {int(marginal.sum())*cell_km2:,.0f} km²")
        tot = sizes.sum()
        for thr in nc.get("ladder_km2", [nc["node_min_km2"]]):
            k = int((sizes * cell_km2 >= thr).sum()); share = sizes[sizes * cell_km2 >= thr].sum() / max(tot, 1)
            print(f"    >= {thr:>5} km²: {k:>4} patches holding {100*share:5.1f}% of core area"
                  + ("   <- node floor" if thr == nc["node_min_km2"] else ""))
    keep_ids = np.flatnonzero(sizes >= min_cells) + 1
    if not len(keep_ids):
        raise ValueError(f"no core refugia patch reaches node_min_km2 = {nc['node_min_km2']} km²")
    cms = ndimage.center_of_mass(core, lab, keep_ids)                   # (row, col) per kept patch
    rows_c = np.array([c[0] for c in cms]); cols_c = np.array([c[1] for c in cms])
    order = np.argsort(rows_c)                                            # north first (row 0 = top)
    keep_ids, rows_c, cols_c = keep_ids[order], rows_c[order], cols_c[order]
    N = len(keep_ids)
    lut = np.zeros(n + 1, "int16"); lut[keep_ids] = np.arange(1, N + 1, dtype="int16")
    node_id = lut[lab]
    del lab
    node_union = node_id > 0

    # ---- auto-names (W9) --------------------------------------------------------------
    nm = nc.get("naming", {})
    pas = _pa_polys(nm.get("pa_min_km2", 1.0)).to_crs(crs)
    pa_id = rasterize([(g, i + 1) for i, g in enumerate(pas.geometry)], out_shape=shape,
                      transform=transform, fill=0, dtype="int32")
    to_ll = pyproj.Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    from shapely.geometry import Point
    north_cls = [c for c in nc["classes_core"] if c >= 10]
    masks, table = [], []
    for k in range(1, N + 1):
        m = node_id == k                                                  # the ONE array per node
        cells = int(m.sum())
        ids = pa_id[m]; ids = ids[ids > 0]
        ov_name, ov_frac = "", 0.0
        if ids.size:
            bc = np.bincount(ids); j = int(bc.argmax()); ov_name, ov_frac = str(pas.loc[j - 1, "PA_Name"]), bc[j] / cells
        x = transform.c + (cols_c[k - 1] + 0.5) * transform.a
        y = transform.f + (rows_c[k - 1] + 0.5) * transform.e
        lon, lat = to_ll.transform(x, y)
        d = pas.geometry.distance(Point(x, y)); jn = int(d.idxmin())
        near_name, near_km = str(pas.loc[jn, "PA_Name"]), float(d[jn]) / 1e3
        cen = pas.loc[jn, "geometry"].centroid
        bearing = _bearing8(x - cen.x, y - cen.y)
        if ov_frac >= nm.get("pa_overlap_min", 0.10):
            auto = ov_name
        else:
            auto = f"{near_name} ({bearing})"
        share_n = float(np.isin(ref[m], north_cls).mean()) if north_cls else float("nan")
        masks.append(m)
        table.append(dict(node_id=k, label_auto=auto, display_name="", area_km2=round(cells * cell_km2, 1),
                          n_cells=cells, x=round(float(x), 1), y=round(float(y), 1),
                          lat=round(float(lat), 4), lon=round(float(lon), 4),
                          pa_overlap_name=ov_name, pa_overlap_frac=round(float(ov_frac), 3),
                          nearest_pa=near_name, nearest_pa_km=round(near_km, 1), bearing=bearing,
                          share_north_model=round(share_n, 3)))
    del pa_id
    df = pd.DataFrame(table)

    # ---- human naming overrides (GW3 fingerprint) --------------------------------------
    if names_path is not None and pathlib.Path(names_path).exists():
        nf = pd.read_csv(names_path, encoding="utf-8-sig").fillna({"display_name": ""})
        for r in nf.itertuples():
            k = int(r.node_id)
            if not (1 <= k <= N):
                raise ValueError(f"GW3 FAILED: node_names.csv row node_id={k} does not exist ({N} nodes)")
            row = df.loc[k - 1]
            if int(r.n_cells) != int(row.n_cells) or abs(float(r.lat) - row.lat) > 1e-3 or abs(float(r.lon) - row.lon) > 1e-3:
                raise ValueError(f"GW3 FAILED: node_names.csv row node_id={k} does not match the current node set "
                                 f"(cells {r.n_cells} vs {row.n_cells}, lat/lon {r.lat},{r.lon} vs {row.lat},{row.lon}) "
                                 f"-- re-run cc.node_patches and re-vet the names")
            if str(r.display_name).strip():
                df.loc[k - 1, "display_name"] = str(r.display_name).strip()
        print(f"  node_names.csv applied: {int((df.display_name != '').sum())} display names overridden")
    df["name"] = np.where(df.display_name != "", df.display_name, df.label_auto)
    kind, klabel = nc.get("kind", "refugium"), nc.get("kind_label", "Refugium")
    df["name_label"] = [f"{klabel} · R{k:02d} {nmz}" for k, nmz in zip(df.node_id, df.name)]
    names_raw = [(lbl, m) for lbl, m in zip(df.name_label, masks)]
    kinds_raw = [kind] * N

    ctx = None
    if nc.get("context_pa_min_km2"):
        big = pas[pas.km2 >= nc["context_pa_min_km2"]]
        ctx = rasterize([(g, 1) for g in big.geometry], out_shape=shape, transform=transform,
                        fill=0, dtype="uint8").astype(bool) & pu
    # W11: protected land (existing PAs + proposed IPCAs/PAs, taken as given) -- a STATUS layer
    protected_pa = protected_ipca = None
    pc = nc.get("protected")
    if pc:
        allp = pas[pas.km2 >= float(pc.get("pa_min_km2", 0.0))]
        protected_pa = rasterize([(g, 1) for g in allp.geometry], out_shape=shape, transform=transform,
                                 fill=0, dtype="uint8").astype(bool) & pu
        if pc.get("include_proposed") and pc.get("proposed"):
            ip = gpd.read_file(config.PROJECT_DIR / pathlib.Path(pc["proposed"])).to_crs(crs)
            protected_ipca = rasterize([(g, 1) for g in ip.geometry], out_shape=shape, transform=transform,
                                       fill=0, dtype="uint8").astype(bool) & pu
        else:
            protected_ipca = np.zeros(shape, bool)
        if verbose:
            print(f"  protected land (status layer, W11): existing PAs {int(protected_pa.sum())*cell_km2:,.0f} km², "
                  f"proposed {int(protected_ipca.sum())*cell_km2:,.0f} km² | "
                  f"{100*float((protected_pa | protected_ipca)[node_union].mean()):.1f}% of node land is protected")
    if verbose:
        print(f"nodes: {N} core refugia patches >= {nc['node_min_km2']} km² "
              f"({int(node_union.sum())*cell_km2:,.0f} km² of node land, numbered north -> south) | "
              f"largest {df.area_km2.max():,.0f} km², smallest {df.area_km2.min():,.0f} km²")
    outline = gpd.read_file(config.CORRIDOR_REF).to_crs(crs)
    return _NS(cfg=cfg, template=template, cost=cost, crs=crs, transform=transform, shape=shape,
               pu=pu, cell_km2=cell_km2, cell_km=cell_km,
               names_raw=names_raw, kinds_raw=kinds_raw, n_dedupe_merges=0, desig={},
               node_union=node_union, outline=outline,
               node_id=node_id, refugia=ref, marginal=marginal, node_table=df, context_pa=ctx,
               protected_pa=protected_pa, protected_ipca=protected_ipca,
               protected=(None if protected_pa is None else (protected_pa | protected_ipca)),
               single_component_nodes=True, nodes_disjoint=True)


def node_patches(key="wolverine", force=False):
    """Step-0a analogue for raster nodes (W7): vectorize the patches once, write the H7-FORMAT
    node_parts.csv / node_parts.gpkg (every figure reads node_parts.gpkg), the naming file
    node_names.csv (display_name blank = auto-name; Ethan may fill it) and refugia_summary.json
    into the git-tracked audit_objects dir. No review file: there is nothing to sign (single
    components). Refuses to overwrite a node_names.csv that already carries filled display
    names unless force=True. Returns the loader namespace (for cc.node_map)."""
    cfg, cost_path = resolve(key, require_cutoff=False)
    audit_dir = pathlib.Path(cfg["audit_objects_dir"]); audit_dir.mkdir(parents=True, exist_ok=True)
    names_path = audit_dir / cfg["nodes"].get("naming", {}).get("names_file", "node_names.csv")
    if names_path.exists() and not force:
        old = pd.read_csv(names_path, encoding="utf-8-sig").fillna({"display_name": ""})
        if (old["display_name"].astype(str).str.strip() != "").any():
            raise FileExistsError(
                f"{names_path} already carries filled display names. Re-running node_patches would "
                f"discard them -- pass force=True only if that is intended.")
    A = _raster_nodes(cfg, cost_path, names_path=None)
    df = A.node_table
    kind = cfg["nodes"].get("kind", "refugium")

    parts = pd.DataFrame(dict(name_label=df.name_label, kind=kind, part_id=1, area_km2=df.area_km2, is_seed=True))
    parts.to_csv(audit_dir / "node_parts.csv", index=False, encoding="utf-8-sig")
    geoms = defaultdict(list)
    for shp, v in shapes(A.node_id.astype("int32"), mask=A.node_union, transform=A.transform):
        geoms[int(v)].append(_shape(shp))
    polys = [dict(name_label=r.name_label, part_id=1, is_seed=True, area_km2=r.area_km2,
                  node_id=int(r.node_id), display_name=r.name,
                  geometry=gpd.GeoSeries(geoms[int(r.node_id)], crs=A.crs).union_all())
             for r in df.itertuples()]
    gpd.GeoDataFrame(polys, crs=A.crs).to_file(audit_dir / "node_parts.gpkg", driver="GPKG")
    cols = ["node_id", "name_label", "label_auto", "display_name", "area_km2", "n_cells", "lat", "lon",
            "pa_overlap_name", "pa_overlap_frac", "nearest_pa", "nearest_pa_km", "bearing", "share_north_model"]
    df[cols].to_csv(names_path, index=False, encoding="utf-8-sig")

    ref = A.refugia; pu = A.pu
    ys = A.template.y.values
    to_ll = pyproj.Transformer.from_crs(A.crs, "EPSG:4326", always_xy=True)
    xmid = float(A.template.x.values[len(A.template.x) // 2])
    lat_rows = np.array([to_ll.transform(xmid, float(y))[1] for y in ys])
    seam = float(cfg["nodes"]["raster"].get("seam_lat", 0) or 0)
    north = (lat_rows >= seam)[:, None] & pu
    vals = cfg["nodes"]["raster"]["expect_classes"]
    summ = dict(
        n_patches_total=int(len(np.bincount(A.node_id.ravel()))),
        n_nodes=int(len(df)), node_min_km2=cfg["nodes"]["node_min_km2"],
        core_km2=round(float(np.isin(ref, cfg["nodes"]["classes_core"])[pu].sum() * A.cell_km2)),
        marginal_km2=round(float(A.marginal.sum() * A.cell_km2)),
        node_land_km2=round(float(A.node_union.sum() * A.cell_km2)),
        class_km2={str(v): round(float(((ref == v) & pu).sum() * A.cell_km2)) for v in vals},
        class_km2_north_of_seam={str(v): round(float(((ref == v) & north).sum() * A.cell_km2)) for v in vals},
        class_km2_south_of_seam={str(v): round(float(((ref == v) & pu & ~north).sum() * A.cell_km2)) for v in vals},
        seam_lat=seam,
        ladder={str(t): int((df.area_km2 >= t).sum()) for t in cfg["nodes"].get("ladder_km2", [])},
    )
    (audit_dir / "refugia_summary.json").write_text(json.dumps(summ, indent=2))
    print(f"node_patches: wrote node_parts.csv, node_parts.gpkg, {names_path.name}, refugia_summary.json "
          f"-> {audit_dir.relative_to(config.PROJECT_DIR)}")
    print(f"  CHECK STOP 1: review the node map + table; optionally fill display_name in {names_path.name}; commit the four files")
    return A


def node_map(A, n_insets=3, win_km=350, save=None):
    """Check-stop-1 figure: numbered nodes over core / marginal refugia with existing PAs as
    outline context, plus `n_insets` zoom panels on the densest node clusters. Inline only."""
    from matplotlib.patches import Rectangle
    import matplotlib.patheffects as pe
    xs, ys = A.template.x.values, A.template.y.values
    df = A.node_table
    d = 4
    rgb = np.ones(A.shape[:2] + (3,), "float32") * 0.97
    rgb[~A.pu] = (0.90, 0.93, 0.95)
    rgb[A.marginal] = (0.80, 0.90, 0.70)
    core = np.isin(A.refugia, A.cfg["nodes"]["classes_core"]) & A.pu
    rgb[core] = (0.55, 0.78, 0.55)
    rgb[A.node_union] = (0.14, 0.55, 0.27)
    ext = [xs[0] - abs(xs[1]-xs[0])/2, xs[-1] + abs(xs[1]-xs[0])/2, ys[-1] - abs(ys[1]-ys[0])/2, ys[0] + abs(ys[1]-ys[0])/2]

    def _draw(ax, XL=None, YL=None, num_fs=7):
        ax.imshow(rgb[::d, ::d], extent=ext, origin="upper", interpolation="nearest")
        if A.context_pa is not None:
            ctx = A.context_pa[::d, ::d]
            ax.contour(ctx.astype(float), levels=[0.5], colors="0.35", linewidths=0.4,
                       extent=[ext[0], ext[1], ext[3], ext[2]], origin="upper")
        A.outline.boundary.plot(ax=ax, color="0.2", linewidth=0.6, linestyle="--")
        for r in df.itertuples():
            if XL is None or (XL[0] <= r.x <= XL[1] and YL[0] <= r.y <= YL[1]):
                ax.annotate(str(r.node_id), (r.x, r.y), fontsize=num_fs, fontweight="bold", ha="center", va="center",
                            color="white", path_effects=[pe.withStroke(linewidth=2.2, foreground="#0b3d1c")])
        ax.set_aspect("equal"); ax.set_axis_off()

    fig = plt.figure(figsize=(18, 13))
    ax = fig.add_axes([0.02, 0.03, 0.40, 0.94]); _draw(ax)
    ax.set_title(f"{A.cfg['region_label']} — {len(df)} core refugia nodes (numbered north → south)\n"
                 f"dark = nodes, mid green = core below the floor, pale = marginal, grey lines = PAs ≥ "
                 f"{A.cfg['nodes'].get('context_pa_min_km2')} km²", fontsize=10)
    # densest clusters: greedy -- the node with most neighbours within win_km/2, remove, repeat
    pts = df[["x", "y"]].values.astype(float); remaining = np.ones(len(df), bool); wins = []
    for _ in range(n_insets):
        if not remaining.any(): break
        best, cnt = None, -1
        for i in np.flatnonzero(remaining):
            c = int(((np.abs(pts[:, 0] - pts[i, 0]) < win_km * 500) & (np.abs(pts[:, 1] - pts[i, 1]) < win_km * 500) & remaining).sum())
            if c > cnt: best, cnt = i, c
        cx, cy = pts[best]; XL = (cx - win_km * 500, cx + win_km * 500); YL = (cy - win_km * 500, cy + win_km * 500)
        remaining &= ~((pts[:, 0] > XL[0]) & (pts[:, 0] < XL[1]) & (pts[:, 1] > YL[0]) & (pts[:, 1] < YL[1]))
        wins.append((XL, YL))
    for k, (XL, YL) in enumerate(wins):
        ax.add_patch(Rectangle((XL[0], YL[0]), XL[1]-XL[0], YL[1]-YL[0], fill=False, ec="#c0392b", lw=1.0))
        ax.text(XL[0], YL[1], f" {chr(65+k)}", color="#c0392b", fontsize=9, fontweight="bold", va="bottom")
        iax = fig.add_axes([0.46 + 0.27 * (k % 2), 0.52 - 0.49 * (k // 2), 0.25, 0.45]) if n_insets <= 4 else None
        if iax is None: continue
        _draw(iax, XL, YL, num_fs=9); iax.set_xlim(*XL); iax.set_ylim(*YL)
        iax.set_title(f"{chr(65+k)} — {win_km} km window", fontsize=9)
        for sp in iax.spines.values(): sp.set_visible(True); sp.set_edgecolor("#c0392b")
    if save:
        fig.savefig(save, dpi=130, bbox_inches="tight")
    plt.show()
    return fig



# ================= v2.5 contraction: refugia complexes (run spec v3 §1a revised 2026-09-29; §3 stages 3-4, D-W3 / D-W6 / D-W7) =================
# The complexes are built by wolverine_postprocess (notebook 05) into the audit objects; the loader below contracts a run onto them.
_COMPLEX_GENERIC = {"park", "parks", "provincial", "national", "reserve", "of", "canada", "wilderness", "area", "areas",
                    "protected", "conservancy", "conservation", "ecological", "recreation", "state", "forest", "corridor",
                    "wildland", "wildlife", "management", "natural", "environment", "monument", "the", "and"}


def _label_num(label):
    """'Refugium · R108 name' -> 108, 'Complex · C03 name' -> 3 (any number of digits)."""
    import re as _re
    m = _re.match(r"[RC](\d+)(?:\s|$)", str(label).split(" · ", 1)[-1])
    return int(m.group(1)) if m else None


def _refugium_name(base, bearing=None, multi=False):
    """D-W7: nodes are named as refugia, never as the nearest park -- 'Refugium (Sustut)', 'Refugia complex (Nahanni)'."""
    words = [w for w in str(base).split(" (")[0].split(" - ")[0].split() if w.lower().strip(",") not in _COMPLEX_GENERIC]
    core = " ".join(words) or str(base)
    if bearing:
        core = f"{core}, {bearing}"
    return f"{'Refugia complex' if multi else 'Refugium'} ({core})"


def _human_proxy(cfg, rec=None):
    """(ghm90max grid, tau) from the variant layers + the variant meta -- the human-layer proxy of W1a; (None, None) if absent."""
    gdir = config.PROJECT_DIR / pathlib.Path(cfg["grid"]["dir"])
    p = gdir / "variant_layers" / "ghm90max.tif"
    hv = cfg.get("headline_variant"); meta = None
    if hv:
        mp = gdir / (cfg["variants"][hv]["resistance"]["out_name"] + ".meta.json")
        if mp.exists():
            meta = json.loads(mp.read_text())
    if not p.exists() or meta is None:
        return None, None
    return rioxarray.open_rasterio(p).squeeze().values, float(meta["thresholds"]["human_tau"])


def merge_complexes(key, pairs, verbose=True):
    """Second-pass D25 (run spec v3 §4): merge the listed complex pairs in the audit membership, renumber north -> south,
    regenerate names (display names are carried over by name_auto where the complex is unchanged) and bump the pass
    counter. Then re-run the routing notebook (06) with a NEW run id."""
    cfg = config.CORRIDORS[key]; audit_dir = pathlib.Path(cfg["audit_objects_dir"])
    mem = pd.read_csv(audit_dir / "complex_membership.csv"); nmd = pd.read_csv(audit_dir / "complex_names.csv", encoding="utf-8-sig").fillna({"display_name": ""})
    summ = json.loads((audit_dir / "complexes_summary.json").read_text())
    G = nx.Graph(); G.add_nodes_from(int(c) for c in nmd.complex_id); G.add_edges_from((int(a), int(b)) for a, b in pairs)
    groups = sorted((sorted(c) for c in nx.connected_components(G)), key=lambda c: float(nmd.set_index("complex_id").loc[c, "lat"].max()), reverse=True)
    old2new = {old: k for k, grp in enumerate(groups, start=1) for old in grp}
    mem["complex_id"] = mem["complex_id"].map(old2new)
    nd = nmd.set_index("complex_id")
    rows = []
    for k, grp in enumerate(groups, start=1):
        sub = nd.loc[grp]; w = sub["n_cells"].values.astype(float)
        big = sub.sort_values("n_cells", ascending=False).iloc[0]
        nm = big["name_auto"] if len(grp) == 1 else big["name_auto"].replace("Refugium (", "Refugia complex (")
        rows.append(dict(complex_id=k, name_auto=nm, display_name=(big["display_name"] if len(grp) == 1 else ""),
                         n_patches=int(sub["n_patches"].sum()), area_km2=round(float(sub["area_km2"].sum()), 1), n_cells=int(sub["n_cells"].sum()),
                         largest_patch=int(big["largest_patch"]), largest_patch_name=big.get("largest_patch_name", ""),
                         patch_ids=" ".join(str(x) for x in sorted(int(v) for s_ in sub["patch_ids"] for v in str(s_).split())),
                         lat=round(float((sub["lat"].values * w).sum() / w.sum()), 4), lon=round(float((sub["lon"].values * w).sum() / w.sum()), 4),
                         share_north_model=round(float((sub["share_north_model"].fillna(0).values * w).sum() / w.sum()), 3)))
    nmd2 = pd.DataFrame(rows)
    mem.sort_values("node_id").to_csv(audit_dir / "complex_membership.csv", index=False, encoding="utf-8-sig")
    nmd2.to_csv(audit_dir / "complex_names.csv", index=False, encoding="utf-8-sig")
    g = gpd.read_file(audit_dir / "complexes.gpkg"); g["complex_id"] = g["complex_id"].map(old2new)
    cg_ = g.dissolve(by="complex_id", aggfunc={"area_km2": "sum"}).reset_index().merge(nmd2[["complex_id", "name_auto", "n_patches", "patch_ids", "lat", "lon"]], on="complex_id")
    cg_["name"] = cg_["name_auto"]
    cg_[["complex_id", "name", "name_auto", "n_patches", "area_km2", "patch_ids", "lat", "lon", "geometry"]].to_file(audit_dir / "complexes.gpkg", driver="GPKG")
    sl = pd.read_csv(audit_dir / "slivers_v2.csv"); sl["complex_id"] = sl["complex_id"].map(old2new); sl.to_csv(audit_dir / "slivers_v2.csv", index=False, encoding="utf-8-sig")
    summ.update(n_complexes=int(len(nmd2)), contraction_pass=int(summ.get("contraction_pass", 1)) + 1,
                second_pass_merges=[[int(a), int(b)] for a, b in pairs], n_single_patch=int((nmd2["n_patches"] == 1).sum()))
    (audit_dir / "complexes_summary.json").write_text(json.dumps(summ, indent=2, ensure_ascii=False))
    if verbose:
        print(f"second-pass merge: {len(pairs)} pair(s) -> {len(nmd2)} complexes (pass {summ['contraction_pass']}); re-run 07 with a new run id")
    return mem, nmd2


def _contract_complexes(A, membership_path, names_path=None, verbose=True):
    """Turn the patch-level loader namespace into the contracted one (D-W3): names_raw = complexes (union of member
    patches), the 130 patches kept as the SEED PARTS in their cached order (prebuilt for _apply_parts), one routing unit
    per complex. GW5 fingerprint: every current patch appears exactly once in the membership with its cell count."""
    mem = pd.read_csv(membership_path)
    df = A.node_table
    assert set(mem.node_id) == set(int(x) for x in df.node_id), "GW5 FAILED: the membership's patch set differs from the current node set"
    assert mem.node_id.is_unique, "GW5 FAILED: a patch appears twice in the membership"
    cells = df.set_index("node_id")["n_cells"]
    bad = [int(n) for n, c in zip(mem.node_id, mem.n_cells) if int(cells.loc[int(n)]) != int(c)]
    assert not bad, f"GW5 FAILED: cell counts differ for patches {bad[:8]} -- rebuild the membership (wolverine_postprocess, notebook 05)"
    names = None
    if names_path is not None and pathlib.Path(names_path).exists():
        names = pd.read_csv(names_path, encoding="utf-8-sig").fillna({"display_name": ""}).set_index("complex_id")
    lbl2mask = dict(A.names_raw)
    order = list(df.node_id.astype(int))                         # the seed order = node_id order (the v2 cache's part order)
    lbl_of = dict(zip(df.node_id.astype(int), df.name_label))
    parts = [(lbl_of[n], lbl2mask[lbl_of[n]]) for n in order]
    pos = {n: i for i, n in enumerate(order)}
    m2c = mem.set_index("node_id")["complex_id"]
    cids = sorted(int(c) for c in mem.complex_id.unique())
    nc = A.cfg["nodes"]; klabel = nc.get("kind_label", "Complex"); kind = nc.get("kind", "complex")
    names_raw, kinds_raw, unit_parts, part_name = [], [], [], [None] * len(parts)
    complex_id = np.zeros(A.shape, np.int16)
    trows = []
    for ci, c in enumerate(cids):
        members = [int(n) for n in mem.node_id[mem.complex_id == c]]
        pidx = sorted(pos[n] for n in members)
        if len(pidx) == 1:
            union = parts[pidx[0]][1]                                # alias, never copy
        else:
            union = np.zeros(A.shape, bool)
            for pi in pidx:
                union |= parts[pi][1]
        nm = None
        if names is not None and c in names.index:
            r = names.loc[c]; nm = str(r["display_name"]).strip() or str(r["name_auto"])
        nm = nm or f"complex {c}"
        lbl = f"{klabel} · C{c:02d} {nm}"
        names_raw.append((lbl, union)); kinds_raw.append(kind); unit_parts.append(pidx)
        for pi in pidx:
            part_name[pi] = ci
        complex_id[union] = c
        sub = df[df.node_id.isin(members)]; w = sub["n_cells"].values.astype(float)
        trows.append(dict(complex_id=c, name=nm, label=lbl, n_patches=len(members), patch_ids=" ".join(str(n) for n in sorted(members)),
                          area_km2=round(float(sub["area_km2"].sum()), 1), n_cells=int(sub["n_cells"].sum()),
                          lat=float((sub["lat"].values * w).sum() / w.sum()), lon=float((sub["lon"].values * w).sum() / w.sum())))
    A.seed_names = [dict(treatment="single") for _ in parts]      # the cache identity of the v2 patch run (_resistance_sha)
    A.seed_n_nodes = len(parts)
    A.patch_names_raw, A.patch_kinds_raw = A.names_raw, A.kinds_raw
    A.names_raw, A.kinds_raw = names_raw, kinds_raw
    A.prebuilt = dict(parts=parts, part_name=part_name, unit_parts=unit_parts)
    A.complex_id, A.complex_table, A.patch_complex = complex_id, pd.DataFrame(trows), m2c
    A.contracted = True
    A.contraction_meta = dict(membership_sha256=_sha256(membership_path), n_patches=len(parts), n_complexes=len(cids),
                              rule="connected components of the near-contiguous (D25) links of the patch-level run")
    if verbose:
        multi = sum(1 for x in unit_parts if len(x) > 1)
        print(f"GW5 OK: {len(parts)} patches -> {len(cids)} complexes ({multi} multi-patch), membership sha {A.contraction_meta['membership_sha256'][:12]}")
    return A


def gate_gw5(A):
    """GW5 (run spec v3 §9): every patch in exactly one complex; complex areas sum to the patch total; no complex is empty."""
    assert getattr(A, "contracted", False), "GW5: not a contracted run"
    n_p = sum(len(x) for x in A.unit_parts)
    assert n_p == len(A.parts) and sorted(i for x in A.unit_parts for i in x) == list(range(len(A.parts))), "GW5 FAILED: parts not partitioned"
    tot_patch = sum(int(m.sum()) for _, m in A.parts); tot_cx = sum(int(m.sum()) for _, m in A.nodes)
    assert tot_patch == tot_cx, f"GW5 FAILED: complex cells {tot_cx} != patch cells {tot_patch}"
    assert all(int(m.sum()) > 0 for _, m in A.nodes), "GW5 FAILED: an empty complex"
    print(f"GW5 OK: {len(A.parts)} patches partitioned into {len(A.nodes)} complexes; {tot_cx * A.cell_km2:,.0f} km² of complex land = the patch total")
    return True


def second_pass_merges(A, write=True):
    """Run spec v3 §4: inter-complex links that D25 still calls near-contiguous -> complex pairs to merge (a second-pass
    contraction, same rule). Empty = accept the contraction. Writes second_pass_merges.csv into the run dir."""
    e = A.edges
    assert "near_contiguous" in e.columns, "run counterfactual_squeeze first"
    nz = e[(e["cost"] > 0) & (~e["is_adjacency"].astype(bool)) & e["near_contiguous"].astype(bool)]
    rows = [dict(edge_id=eid, complex_i=_label_num(r["label_i"]), complex_j=_label_num(r["label_j"]),
                 lcp_len_cells=r.get("lcp_len_cells"), open_ground_width_med=r.get("open_ground_width_med"),
                 crosses_cost_1000=bool(r.get("crosses_cost_1000", False))) for eid, r in nz.iterrows()]
    df = pd.DataFrame(rows, columns=["edge_id", "complex_i", "complex_j", "lcp_len_cells", "open_ground_width_med", "crosses_cost_1000"])
    if write:
        df.to_csv(A.run_dir / "second_pass_merges.csv", index=False, encoding="utf-8-sig")
    print(f"D25 second pass: {len(df)} inter-complex link(s) near-contiguous" + (" -> merge and re-run (cc.merge_complexes)" if len(df) else " -> contraction accepted"))
    return df


def complex_layer(A):
    """Layer A (run spec v3 §5): one row per complex -- patches, area, share inside existing PAs, share ADDED by the proposed
    IPCAs, mean of the 300 m human-modification proxy (the max of the 90 m gHM within each cell -- the W1a layer; disclosed),
    within-complex slivers and how many carry a cost-100/1000 feature (from slivers_v2.csv)."""
    ghm, tau = _human_proxy(A.cfg, A.rec)
    pa = A.protected_pa if getattr(A, "protected_pa", None) is not None else np.zeros(A.shape, bool)
    ip = A.protected_ipca if getattr(A, "protected_ipca", None) is not None else np.zeros(A.shape, bool)
    sl = pd.read_csv(A.run_dir / "slivers_v2.csv", encoding="utf-8-sig") if (A.run_dir / "slivers_v2.csv").exists() else None
    rows = []
    for u, (lbl, m) in enumerate(A.nodes):
        t = A.complex_table.iloc[u]; n = int(m.sum())
        r = dict(t.to_dict())
        r.update(pa_share=round(float((m & pa).sum() / n), 4), ipca_added_share=round(float((m & ip & ~pa).sum() / n), 4),
                 protected_share=round(float((m & (pa | ip)).sum() / n), 4),
                 mean_ghm90max=(round(float(np.nanmean(ghm[m])), 4) if ghm is not None else np.nan))
        if sl is not None:
            s_ = sl[sl["complex_id"] == int(t["complex_id"])]
            r.update(n_slivers=int(len(s_)), n_slivers_with_feature=int(s_["has_cost100_or_1000"].sum()),
                     n_slivers_crossing_1000=int(s_["crosses_cost_1000"].sum()))
        rows.append(r)
    return pd.DataFrame(rows)


def complex_map(A, save=None, label_min_km2=2000):
    """Check stop 3 (run spec v3 §3): the complexes as a numbered categorical map over the refugia + PA context."""
    from matplotlib.colors import ListedColormap as _LCM
    nodes = getattr(A, "nodes", None) or A.names_raw          # before _apply_parts (check stop 3) the complexes are names_raw
    K = len(nodes)
    rng = np.random.default_rng(7); cols = plt.get_cmap("tab20")(np.arange(20) / 20.0)[rng.permutation(20)]
    cmap = _LCM(np.vstack([[1, 1, 1, 0]] + [cols[(i % 20)] for i in range(K)]))
    step = max(1, A.shape[1] // 2400)
    fig, ax = plt.subplots(figsize=(9, 14))
    ctx = getattr(A, "context_pa", None)
    if ctx is not None:
        ax.imshow(np.where(ctx[::step, ::step], 1, np.nan), cmap=_LCM([PA_COLOR]), alpha=0.35, interpolation="nearest")
    ax.imshow(np.where(A.marginal[::step, ::step], 1, np.nan), cmap=_LCM(["#C5E1A5"]), alpha=0.5, interpolation="nearest")
    cid = A.complex_id[::step, ::step]
    ax.imshow(np.where(cid > 0, cid, np.nan), cmap=cmap, vmin=0, vmax=K, interpolation="nearest")
    for u, (lbl, m) in enumerate(nodes):
        t = A.complex_table.iloc[u]
        rr, cc_ = np.nonzero(m[::step, ::step])
        if not len(rr):
            continue
        ax.text(np.median(cc_), np.median(rr), f"C{int(t['complex_id'])}", fontsize=7 if t["area_km2"] < label_min_km2 else 9,
                ha="center", va="center", fontweight="bold", bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))
    ax.set_axis_off(); ax.set_title(f"Refugia complexes — {K} (check stop 3: does any split where one range is expected?)")
    if save:
        fig.savefig(save, dpi=150, bbox_inches="tight")
    plt.show()
    return fig


def _name_designation(label, kind, desig, multisite):
    """Designation string for a name. IPCAs carry PA_TYPE from the source; the PA layer has no
    designation attribute, so for existing PAs the designation is DERIVED from PA_Name by matching
    the multisite list (flagged as name-derived in the review file)."""
    base = label.split(" (+", 1)[0]                     # strip the dedupe "(+n)" suffix
    if kind == "ipca":
        return desig.get(base, "")
    nm = base.split(" · ", 1)[-1].lower()
    for d in multisite:
        if d.lower() in nm:
            return f"{d} (name-derived)"
    return ""


def _split_parts(mask, min_cells):
    """A name's mask -> (all 8-connected components, the SEED components >= part_min_km2)."""
    lab, n = ndimage.label(mask, structure=np.ones((3, 3), int))
    comps = [lab == k for k in range(1, n + 1)]
    comps.sort(key=lambda m: -int(m.sum()))
    seeds = [m for m in comps if int(m.sum()) >= min_cells]
    return comps, seeds


def _apply_parts(A, treatments):
    """D16: split every name into parts, apply the H7-reviewed treatment, build the ROUTING UNITS.

    Data model layered on the v1 one so everything downstream keeps working:
      A.names   name-level dicts (label, kind, full mask, treatment, part indices)
      A.parts   [(part label, mask)] -- the CWD SEEDS (each cached as its own field)
      A.nodes   [(label, seed-union mask)] per ROUTING UNIT -- the graph's node set, exactly the
                shape the whole engine already consumes
      Treatments: merge_parts -> one seed (the full mask; the split was a rasterization artefact);
      link_locked -> one unit holding several seed parts, intra-name MST locked at network build;
      link_competing -> each part its own unit (the direct edge competes like any other);
      no_link -> each part its own unit AND the direct intra-name edges are excluded from
      candidacy (D set to inf in corridor_network).
    A.node_union stays the union of FULL name masks: parts < part_min_km2 remain area-accounted
    but are never seeds (spec §2).
    """
    pre = getattr(A, "prebuilt", None)
    if pre is not None:                          # wolverine v3 (D-W3): complexes = names, patches = parts, ONE unit per complex
        A.names = [dict(label=lbl, kind=kind, mask=m, treatment="contract", parts=list(pidx), n_comps=len(pidx), n_seeds=len(pidx))
                   for (lbl, m), kind, pidx in zip(A.names_raw, A.kinds_raw, pre["unit_parts"])]
        A.parts, A.part_name = pre["parts"], pre["part_name"]
        A.nodes = [(lbl, m) for lbl, m in A.names_raw]
        A.kinds, A.unit_name, A.unit_parts = list(A.kinds_raw), list(range(len(A.names_raw))), [list(x) for x in pre["unit_parts"]]
        multi = sum(1 for x in A.unit_parts if len(x) > 1)
        print(f"contraction (D-W3): {len(A.parts)} patches (the cached seed parts) -> {len(A.nodes)} complexes as routing units "
              f"({multi} multi-patch; unit field = pointwise min over member patches; no intra-complex links)")
        return A
    part_min = max(1, int(round(A.cfg["part_min_km2"] / A.cell_km2)))
    names, parts, part_name = [], [], []
    units, unit_kinds, unit_name, unit_parts = [], [], [], []

    single = getattr(A, "single_component_nodes", False)     # raster nodes: no split (W7)
    for k, ((lbl, mask), kind) in enumerate(zip(A.names_raw, A.kinds_raw)):
        comps, seeds = ([mask], [mask]) if single else _split_parts(mask, part_min)
        multi = len(seeds) > 1
        if multi and lbl not in treatments:
            raise ValueError(
                f"D16: {lbl!r} has {len(seeds)} seed parts but no row in multipart_review.csv -- "
                f"re-run step 0a (cc.node_parts) and get the review re-signed (H7).")
        t = treatments.get(lbl, "single") if multi else "single"

        if t in ("single", "merge_parts"):
            seed_masks = [mask if t == "merge_parts" else (seeds[0] if seeds else mask)]
        else:
            seed_masks = seeds

        p0 = len(parts)
        for pi, m in enumerate(seed_masks):
            plbl = lbl if len(seed_masks) == 1 else f"{lbl} [part {pi+1}]"
            parts.append((plbl, m)); part_name.append(k)
        pidx = list(range(p0, len(parts)))
        names.append(dict(label=lbl, kind=kind, mask=mask, treatment=t,
                          parts=pidx, n_comps=len(comps), n_seeds=len(seed_masks)))

        if t in ("single", "merge_parts", "link_locked"):
            if len(pidx) == 1:
                union = parts[pidx[0]][1]        # one seed = the unit: alias, never copy (memory at Y2Y scale)
            else:
                union = np.zeros(A.shape, bool)
                for pi in pidx:
                    union |= parts[pi][1]
            units.append((lbl, union)); unit_kinds.append(kind)
            unit_name.append(k); unit_parts.append(pidx)
        else:                                        # link_competing / no_link: one unit per part
            for pi in pidx:
                units.append((parts[pi][0], parts[pi][1]))
                unit_kinds.append(kind); unit_name.append(k); unit_parts.append([pi])

    A.names, A.parts, A.part_name = names, parts, part_name
    A.nodes, A.kinds, A.unit_name, A.unit_parts = units, unit_kinds, unit_name, unit_parts
    multi = [n for n in names if n["n_seeds"] > 1]
    if multi or len(units) != len(names):
        print(f"D16 parts: {len(names)} names -> {len(parts)} seed parts -> {len(units)} routing "
              f"units  ({len(multi)} multipart: "
              + "; ".join(f"{n['label'].split(' · ')[-1]} {n['n_seeds']}p/{n['treatment']}"
                          for n in multi) + ")")
    return A


def load(run_dir):
    """Open a run dir: read run_config.json, build the 300 m routing grid cropped to the anchors,
    assemble + rasterize the nodes, and apply the D16 part treatments from the run's own signed
    multipart_review.csv copy.

    Reads ONLY run_config.json + the run-dir H7 copies, never config.CORRIDORS or the tracked
    audit_objects/ originals -- so re-opening an old run reproduces that run's parameters and
    review rather than today's.
    """
    run_dir = pathlib.Path(run_dir)
    rec = json.loads((run_dir / "run_config.json").read_text())
    cfg = rec["cfg"]
    key = rec["key"]
    cost_path = config.PROJECT_DIR / rec["inputs"]["movement_cost"]["path"]

    if cfg.get("nodes", {}).get("source", "vector") == "raster":
        names_path = run_dir / "node_names.csv"
        A = _raster_nodes(cfg, cost_path, names_path if names_path.exists() else None)
        if cfg["nodes"].get("contract"):                            # wolverine v3: complexes from the pinned membership
            _contract_complexes(A, run_dir / "complex_membership.csv",
                                run_dir / "complex_names.csv" if (run_dir / "complex_names.csv").exists() else None)
    else:
        A = _grid_nodes(cfg, cost_path)
    A.key, A.rec, A.run_id, A.run_dir = key, rec, rec["run_id"], run_dir
    A.fig_dir = run_dir / "figures"
    A.region_label = cfg["region_label"]

    review = run_dir / "multipart_review.csv"
    treatments = read_review(review) if review.exists() else {}
    _apply_parts(A, treatments)

    # ---- the 1 km AUDIT grid (pinned; see AUDIT_TEMPLATE) -----------------------------
    A.audit_template = rioxarray.open_rasterio(config.HANDOFF_DIR / AUDIT_TEMPLATE,
                                               masked=True).squeeze()
    return A


def start(key="north", overrides=None, label="", run_id=None, require_cutoff=True,
          require_review=True):
    """new_run + load, so the notebook's first cell stays one line."""
    return load(new_run(key, overrides, label, run_id, require_cutoff, require_review))


# ================= resistance =================
def resistance(A):
    """Resistance IS the published movement-cost surface (D1/D2). No blend, no free parameters.

    v1 computed (1 / permeability**conn_exponent) * barrier_base**gHM from three weighted regional
    products. That is gone: it triple-counted human footprint, used a circuit-theory OUTPUT as a
    routing INPUT, mixed climate-analog layers into movement cost, and every exponent was
    uncalibrated. This function now has nothing to tune -- the surface is somebody else's
    peer-reviewed resistance hypothesis, used as published.

    Off-corridor cells are impassable (inf), which is a real modelling constraint: routes cannot
    leave the buffered Y2Y region. State it in the methods.
    """
    A.resistance_arr = np.where(A.pu, A.cost, np.inf)
    print(f"resistance = {A.cfg['resistance']['citation']}")
    print(f"  {A.cfg['resistance']['out_name']} @ {A.cell_km*1000:.0f} m, "
          f"'{A.cfg['resistance']['resampling']}' resampled (ordinal classes preserved exactly)")
    return A


def resistance_report(A, v1_path=None, save=True):
    """Phase 1.3 diagnostics. The SPREAD statistic is the headline: it bounds how much the routing
    can discriminate at all, which is the standing worry about running a least-cost model over
    intact northern landscape where most cells are equally passable."""
    fin = A.resistance_arr[np.isfinite(A.resistance_arr)]
    classes = A.cfg["resistance"]["expect_classes"]
    q = np.percentile(fin, [5, 50, 95])
    print(f"resistance over {fin.size:,} routable cells  (low = preferred corridor land)")
    for c in classes:
        n = int((fin == c).sum())
        print(f"    cost {c:>5}: {100*n/fin.size:5.1f}%  ({n:,} cells)")
    print(f"  p5={q[0]:g}  p50={q[1]:g}  p95={q[2]:g}  max={fin.max():g}")
    print(f"  EFFECTIVE SPREAD p95/p5 = {q[2]/max(q[0],1e-9):,.0f}x   (v1 blend was 10.9x)")

    fig, axes = plt.subplots(1, 2 if v1_path else 1, figsize=(13 if v1_path else 7, 5.5),
                             squeeze=False)
    ax = axes[0][0]
    ax.imshow(_da(A, np.where(A.pu, A.cost, np.nan)).values, cmap="magma_r",
              norm=LogNorm(vmin=min(classes), vmax=max(classes)), interpolation="nearest")
    ax.set_title(f"Movement cost, {A.cell_km*1000:.0f} m\n(O'Brien/Pither, 4 ordinal classes)",
                 fontsize=10)
    ax.axis("off")

    if v1_path:
        # v1 lived on the 1 km grid; match it onto this one purely to compare patterns.
        v1 = rioxarray.open_rasterio(v1_path, masked=True).squeeze()
        v1 = v1.where(v1 >= 0)                       # v1 wrote off-PU as -1
        v1m = v1.rio.reproject_match(A.template).values
        both = np.isfinite(v1m) & A.pu
        r = np.corrcoef(np.log10(v1m[both]), np.log10(A.cost[both]))[0, 1]
        print(f"  correlation with the v1 blend (log-log, {both.sum():,} shared cells): r = {r:+.3f}")
        ax2 = axes[0][1]
        ax2.imshow(_da(A, np.where(both, v1m, np.nan)).values, cmap="magma_r",
                   norm=LogNorm(), interpolation="nearest")
        ax2.set_title(f"v1 blended resistance, 1 km\n(log-log r = {r:+.3f})", fontsize=10)
        ax2.axis("off")
    fig.tight_layout()
    if save:
        p = A.fig_dir / "resistance_diagnostics.png"
        fig.savefig(p, dpi=150, bbox_inches="tight")
        print(f"  wrote {p.relative_to(config.PROJECT_DIR)}")
    return A


# ================= network primitives =================
def _cwd_all(A, res, masks, cache_dir=None, prefix="node", pu=None):
    """Least-cost accumulated distance from each seed mask over resistance `res`.

    Returns (cwd, mcp) where `cwd` is an indexable sequence of 2-D arrays. At 300 m one field is
    ~200 MB in float64, so 42 nodes would be 8.3 GB in RAM. When `cache_dir` is given each field is
    written once as a float32 .npy and handed back as a MEMMAP, so only the two fields an edge
    actually needs are ever resident.

    Two traps preserved from v1:
      * `find_costs` returns MCP's INTERNAL buffer, overwritten on the next call -- it must be
        copied before the next node is processed.
      * `mcp.traceback` reads whatever `find_costs` ran LAST. Anything that reorders the calls must
        keep tracebacks grouped with their own source node, or paths silently come back from the
        wrong node -- no exception, plausible-looking output. Gate G1 is what catches that.
    """
    mcp = MCP_Geometric(res)
    # seed lists are built PER NODE inside the loop (not all up front): 66 Y2Y-wide patches would
    # otherwise hold ~3 M Python tuples at once
    _seeds = lambda m: [tuple(x) for x in np.argwhere(m)]
    if cache_dir is None:
        cwd = []
        for m in masks:
            cum, _ = mcp.find_costs(_seeds(m))
            cwd.append(cum.copy())
        return cwd, mcp

    cache_dir = pathlib.Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for k, m in enumerate(masks):
        p = cache_dir / f"{prefix}_{k:03d}.npy"
        if not p.exists():
            t0 = time.time()
            cum, _ = mcp.find_costs(_seeds(m))
            # compact cache (wolverine `cwd_compact`): only the routable cells, in row-major
            # order of `pu` -- 69 MB instead of 189 MB per field at Y2Y scale. Off-PU cells are
            # inf by construction (cost inf), so the expansion in _CwdCache is exact.
            np.save(p, (cum[pu] if pu is not None else cum).astype("float32"))
            if pu is not None:
                print(f"    {prefix} {k:03d}/{len(masks)-1}: {int(m.sum())*int(round(A.cell_km2*1e4))/1e4:,.0f} km² seed, "
                      f"{time.time()-t0:,.0f} s")
        paths.append(p)
    return _CwdCache(paths, pu), mcp


class _CwdCache:
    """Lazy list-like view over cached CWD fields; loads one memmap at a time.

    Two on-disk formats: 2-D full-grid files (the north) are returned as memmaps; 1-D COMPACT
    files (`pu` given; wolverine) are expanded on read into a full float32 grid with inf off-PU,
    so every consumer written against full grids works unchanged. `compact(k)` returns the raw
    1-D vector (row-major over pu) for the fast paths in cost_matrix / edge_bands.
    """

    def __init__(self, paths, pu=None):
        self.paths = list(paths)
        self.pu = pu
        if pu is not None:
            self.shape = pu.shape
            self.flat_pu = np.flatnonzero(pu.ravel()).astype(np.int32)

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, k):
        arr = np.load(self.paths[k], mmap_mode="r")
        if self.pu is None or arr.ndim == 2:
            return arr
        out = np.full(self.shape, np.inf, "float32")
        out[self.pu] = arr
        return out

    def compact(self, k):
        arr = np.load(self.paths[k], mmap_mode="r")
        if arr.ndim == 2:
            return np.asarray(arr)[self.pu]
        return arr

    @property
    def nbytes_on_disk(self):
        return sum(p.stat().st_size for p in self.paths)


def _resistance_sha(A):
    """Identity of (resistance, seed structure), so a CWD cache is never reused across either a
    different surface or a different D16 part split. Per-part seed masks + treatments are hashed
    (spec step 1: cache keyed by resistance hash + part mask hash) -- editing multipart_review.csv
    and re-running therefore computes fresh fields instead of silently reusing stale ones."""
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(A.cost).tobytes())
    h.update(np.ascontiguousarray(A.node_union).tobytes())
    for plbl, m in getattr(A, "parts", [(lbl, m) for lbl, m in A.nodes]):
        h.update(np.packbits(m).tobytes())
    # contracted runs (wolverine v3, D-W3): the SEED structure is the patch set exactly as v2 ran it (130 single-part
    # names), so the per-part fields are byte-identical and the cache dir is v2's; unit fields carry their own
    # composition hash (_unit_fname). Uncontracted runs hash their names/units as before.
    for n in (getattr(A, "seed_names", None) or getattr(A, "names", [])):
        h.update(n["treatment"].encode())
    h.update(str(getattr(A, "seed_n_nodes", None) or len(A.nodes)).encode())
    return h.hexdigest()[:16]


def _unit_fname(A, u):
    """Materialised multi-part unit field: `unit_UUU.npy` (north, D16) or, on a contracted run, a name keyed by the
    unit's part composition so a second-pass merge never reads a stale file."""
    if getattr(A, "contracted", False):
        key = ",".join(str(int(i)) for i in sorted(A.unit_parts[u]))
        return f"unit_{hashlib.sha1(key.encode()).hexdigest()[:12]}.npy"
    return f"unit_{u:03d}.npy"


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


def cost_matrix(A, cwd):
    """Node-to-node least-cost distance matrix, symmetrised.

    v1 filled both triangles independently from the two CWD fields. Those agree only up to
    floating-point accumulation, and networkx needs an exactly symmetric matrix, so take the
    elementwise minimum and assert the disagreement was numerical rather than structural.
    """
    N = len(A.nodes)
    D = np.full((N, N), np.inf)
    cidx = getattr(A, "node_cidx", None)
    if cidx is not None and getattr(cwd, "pu", None) is not None:
        # compact path (wolverine): gather each node's cells from the 1-D vector -- the 2-D
        # memmap indexing below touches the WHOLE field file per (i, j) pair
        for i in range(N):
            fi = cwd.compact(i)
            for j in range(N):
                if i != j:
                    D[i, j] = np.nanmin(np.asarray(fi[cidx[j]]))
    else:
        for i in range(N):
            fi = cwd[i]
            for j in range(N):
                if i != j:
                    D[i, j] = np.nanmin(fi[A.nodes[j][1]])
    np.fill_diagonal(D, 0.0)
    fin = np.isfinite(D) & np.isfinite(D.T)
    if fin.any():
        rel = np.abs(D - D.T)[fin] / np.maximum(np.abs(D)[fin], 1e-9)
        assert rel.max() < 1e-3, (
            f"cost matrix is structurally asymmetric (max relative gap {rel.max():.2e}) -- "
            f"expected only floating-point noise between the two CWD directions")
    return np.minimum(D, D.T)


def _band_slack(cutoff_mode, cutoff, cost_ij):
    """Allowed detour above an edge's least-cost minimum, in COST units.

    "abs"  -> `cutoff` (D6, the convention). Corridor width no longer scales with edge cost.
    "frac" -> `cutoff * cost_ij` (v1). Kept ONLY so gate G1 can reproduce the v1 network exactly;
              it is the cheapest possible regression harness in a repo with no test runner.
    """
    if cutoff_mode == "abs":
        return float(cutoff)
    if cutoff_mode == "frac":
        return float(cutoff) * float(cost_ij)
    raise ValueError(f"cutoff_mode must be 'abs' or 'frac', got {cutoff_mode!r}")


class _BandStore:
    """Per-run, per-CWD-set store of computed bands (wolverine `band_cache`), persisted under
    run_dir/band_cache/<tag>/ so later notebooks re-attach in seconds instead of re-running one
    full find_costs per edge. A band is stored at `allow_stored` >= the requested allowance
    with its float64 field values; any smaller allowance is the IDENTICAL predicate
    (field <= lcp + allow) on those values, i.e. bit-exact with a fresh computation."""

    def __init__(self, root):
        self.root = pathlib.Path(root); self.mem = {}

    def _path(self, key, mode):
        return self.root / f"{key}.{mode}.npz"

    def get(self, key, mode):
        k = (key, mode)
        if k in self.mem:
            return self.mem[k]
        p = self._path(key, mode)
        if not p.exists():
            return None
        z = np.load(p, allow_pickle=False)
        rec = dict(idx=z["idx"], field=z["field"], path=z["path"], is_path=z["is_path"],
                   lcp=float(z["lcp"]), allow=float(z["allow"]))
        self.mem[k] = rec
        return rec

    def put(self, key, mode, rec):
        self.mem[(key, mode)] = rec
        self.root.mkdir(parents=True, exist_ok=True)
        np.savez(self._path(key, mode), idx=rec["idx"], field=rec["field"], path=rec["path"],
                 is_path=rec["is_path"], lcp=rec["lcp"], allow=rec["allow"])


def edge_bands(A, cwd, mcp, edges, cutoff, cutoff_mode="abs", want_slack=True, nmap=None, tag=None):
    """Per-edge corridor geometry, keyed by edge_id -- NOT a single union.

    Retaining per-edge identity is what D7 (per-edge centrality/criticality) and D9 (a graded
    priority surface with per-cell attribution) both need. Bands are stored as flat indices plus
    slack, not as boolean grids: ~60 edges x 24.7 M bools would be 1.5 GB of mostly-False, and
    caching slack at the LARGEST cutoff makes any smaller cutoff a pure filter -- which is what
    makes ensemble axis B free.
    """
    # nmap translates edge endpoints into CWD/node indices. Identity for a normal run; for a
    # leave-one-out ensemble member the graph is built on a SUBSET of nodes, so its edge indices
    # are subset-local and have to be mapped back to the cached per-node fields.
    nm = (lambda k: k) if nmap is None else (lambda k: int(nmap[k]))
    bands, slack, paths, meta = {}, {}, {}, {}
    # wolverine band store (opt-in via cfg band_cache; `tag` names the CWD set) + compact fields
    store = None
    if tag is not None and getattr(A, "band_memo", None) is not None:
        store = A.band_memo.setdefault(tag, _BandStore(A.run_dir / "band_cache" / tag))
    mult = float(A.cfg.get("band_cache_mult", 2.0)) if store is not None else 1.0
    compact = (getattr(cwd, "pu", None) is not None and getattr(A, "node_flat", None) is not None
               and cwd.pu.shape == tuple(A.shape))
    n_edges, t_start = len(edges), time.time()
    for n_done, (_, e) in enumerate(edges.iterrows(), 1):
        i, j, cost_ij = nm(int(e["i"])), nm(int(e["j"])), float(e["cost"])
        eid = e.name
        skey = cg.edge_id(i, j)                          # store key = GLOBAL unit indices

        # ADJACENCY EDGES GET NO BAND (methods doc §4: "no corridor to build between areas that
        # already touch"). Under v1's RELATIVE band this fell out for free (allow = frac x 0 = 0);
        # under D6's ABSOLUTE cutoff a zero-cost edge would otherwise grow a `cutoff`-deep lens
        # around the contact zone -- 10,644 km² of invented band on the first real run
        # (v2_run002), silently absorbed into the D6 calibration and narrowing every separated
        # edge's band to compensate. Skipping them here restores the documented semantics for
        # banding, calibration, the priority surface and the ensemble alike.
        if cost_ij <= cg.ADJACENCY_COST and cutoff_mode == "abs":
            bands[eid] = np.empty(0, np.int32)
            if want_slack:
                slack[eid] = np.empty(0, "float32")
            meta[eid] = dict(lcp=0.0, allow=0.0, centreline_cells=0)
            continue
        allow = _band_slack(cutoff_mode, cutoff, cost_ij)

        # ---- store HIT: the identical predicate on the stored float64 values (bit-exact) ----
        hit = store.get(skey, cutoff_mode) if store is not None else None
        if hit is not None and hit["allow"] >= allow - 1e-12:
            sel = (hit["field"] <= hit["lcp"] + allow) | hit["is_path"]
            idx = hit["idx"][sel]
            bands[eid] = idx
            if want_slack:
                slack[eid] = (hit["field"][sel] - hit["lcp"]).astype("float32")
            paths[eid] = hit["path"]
            meta[eid] = dict(lcp=float(hit["lcp"]), allow=float(allow), centreline_cells=int(len(hit["path"])))
            continue

        allow_used = allow * mult                          # store at the larger allowance
        t0 = time.time()
        if compact:
            # ---- compact fields (wolverine): the same arithmetic on the routable vector ----
            fic, fjc = cwd.compact(i), cwd.compact(j)
            n_path = 0; path = np.zeros((0, 2), np.int32)
            if cost_ij > 0:
                cj = A.node_cidx[j]
                tgt_k = int(np.argmin(np.asarray(fic[cj])))
                target = tuple(int(v) for v in np.unravel_index(int(A.node_flat[j][tgt_k]), A.shape))
                seeds_i = [tuple(x) for x in np.argwhere(A.nodes[i][1])]
                if store is not None:
                    mcp.find_costs(seeds_i, ends=[target])          # early stop: the target is popped, its traceback fixed
                else:
                    mcp.find_costs(seeds_i)
                path = np.asarray(mcp.traceback(target), dtype=np.int32)
                n_path = len(path)
            fc = np.asarray(fic, dtype="float64"); fc = fc + np.asarray(fjc, dtype="float64")
            lcp = float(np.nanmin(fc))
            keepc = np.isfinite(fc) & (fc <= lcp + allow_used)
            is_path_c = np.zeros(fc.shape, bool)
            if n_path:
                pflat = (path[:, 0].astype(np.int64) * A.shape[1] + path[:, 1]).astype(np.int32)
                pos = np.searchsorted(cwd.flat_pu, pflat)
                assert np.array_equal(cwd.flat_pu[pos], pflat), "traceback left the routable set"
                keepc[pos] = True; is_path_c[pos] = True
            idx = cwd.flat_pu[keepc]
            fvals = fc[keepc]
            is_path = is_path_c[keepc]
        else:
            fi, fj = cwd[i], cwd[j]
            # Centre-line: an explicit traceback, kept from v1. With an absolute cutoff it is no
            # longer strictly needed for continuity, but path_cells is the resistance-independent
            # length yardstick and G1 compares it directly.
            # traceback() reads the LAST find_costs, so re-seed from node i immediately before it.
            n_path = 0; path = np.zeros((0, 2), np.int32)
            if cost_ij > 0:
                mcp.find_costs([tuple(x) for x in np.argwhere(A.nodes[i][1])])
                tgt_cells = np.argwhere(A.nodes[j][1])
                target = tuple(tgt_cells[np.argmin(np.asarray(fi)[A.nodes[j][1]])])
                path = np.asarray(mcp.traceback(target), dtype=np.int32)
                n_path = len(path)
            field = np.asarray(fi, dtype="float64") + np.asarray(fj, dtype="float64")
            lcp = float(np.nanmin(field))
            keep = np.isfinite(field) & (field <= lcp + allow_used)
            is_path_g = np.zeros(A.shape, bool)
            if n_path:
                keep[path[:, 0], path[:, 1]] = True; is_path_g[path[:, 0], path[:, 1]] = True
            idx = np.flatnonzero(keep.ravel()).astype(np.int32)
            fvals = field.ravel()[idx]
            is_path = is_path_g.ravel()[idx]

        if store is not None:
            store.put(skey, cutoff_mode, dict(idx=idx.astype(np.int32), field=fvals, path=path,
                                              is_path=is_path, lcp=lcp, allow=float(allow_used)))
            print(f"    band {n_done}/{n_edges} {eid}: {int(idx.size)} cells @ {allow_used:g}, "
                  f"{time.time()-t0:,.0f} s (elapsed {time.time()-t_start:,.0f} s)")
        # filter to the requested allowance (identity when mult == 1)
        sel = (fvals <= lcp + allow) | is_path
        idx_r = idx[sel]
        bands[eid] = idx_r.astype(np.int32)
        if want_slack:
            slack[eid] = (fvals[sel] - lcp).astype("float32")
        if n_path:
            paths[eid] = path
        meta[eid] = dict(lcp=float(lcp), allow=float(allow), centreline_cells=int(n_path))
    return bands, slack, paths, meta


def network_mask(A, bands):
    """Union the per-edge bands into the two masks every downstream consumer expects.

    `swath` is the raw union; `corridor` is the NEW land only. Node cells never count: cwd[i] is 0
    across the whole of node i, so the band test passes there by construction -- in v1 that put
    ~37% of the raw swath inside ground already protected or proposed, and made the map disagree
    with the star plots (which always profiled `corridor & ~nodes`). Both are reported.
    """
    flat = np.zeros(A.shape[0] * A.shape[1], bool)
    for idx in bands.values():
        flat[idx] = True
    swath = flat.reshape(A.shape) & A.pu
    return swath & ~A.node_union, swath


# ================= D16 locked intra-name network =================
def _unit_D(A):
    """Unit-level least-cost distance matrix, with no_link intra-name pairs excluded.

    For a `no_link` name the parts are independent units in the inter-name graph AND their direct
    edge is excluded from MST/backup candidacy (a designation that is multi-site by design, or a
    genuinely geographic gap, must not have a corridor invented between its own sites); they still
    connect through the wider network wherever that is cheapest.
    """
    D = cost_matrix(A, A.cwd)
    for n_idx, n in enumerate(A.names):
        if n["treatment"] == "no_link":
            us = [u for u in range(len(A.nodes)) if A.unit_name[u] == n_idx]
            for a, b in itertools.combinations(us, 2):
                D[a, b] = D[b, a] = np.inf
    return D


def _locked_edges(A, cutoff, cutoff_mode="abs"):
    """Intra-name MSTs for link_locked multi-part units, banded on the PART fields (D16).

    Locked BEFORE the inter-name MST is built -- structurally: each link_locked name is ONE unit
    (one graph node), so the inter-name MST is automatically the contracted quotient MST, and
    these edges are the pre-committed internal spanning structure. A part is therefore never
    connected to its sibling only via a third park.
    """
    rows = []
    for u in range(len(A.nodes)):
        pidx = A.unit_parts[u]
        if len(pidx) < 2:
            continue
        n = A.names[A.unit_name[u]]
        if n["treatment"] != "link_locked":        # contracted complexes (v3, D-W3) have parts but NO intra-name links
            continue
        k = len(pidx)
        Dp = np.full((k, k), np.inf)
        for a in range(k):
            fa = np.asarray(A.cwd_parts[pidx[a]], dtype="float64")
            for b in range(k):
                if a != b:
                    Dp[a, b] = np.nanmin(fa[A.parts[pidx[b]][1]])
        np.fill_diagonal(Dp, 0.0)
        Dp = np.minimum(Dp, Dp.T)
        for a, b, c in cg.mst_edges(Dp):
            p, q = pidx[a], pidx[b]
            rows.append(dict(edge_id=f"L{p:03d}_{q:03d}", i=p, j=q,
                             label_i=A.parts[p][0], label_j=A.parts[q][0],
                             kind_pair=f"{n['kind']}-{n['kind']}", cost=float(c),
                             in_mst=True, is_adjacency=False,
                             # centrality on the unit quotient is undefined for an edge INSIDE a
                             # supernode (same reasoning as adjacency edges). Consequence: locked
                             # edges contribute NO linkage-priority weight -- their land shows in
                             # corridors.tif and the near-optimality surface but not
                             # linkage_priority.tif. OPEN METHODS QUESTION flagged for review.
                             ecfb_raw=np.nan, ecfb_norm=np.nan, centrality_cf=np.nan, centrality_sp=np.nan,
                             edge_class="intra_name", name_label=n["label"]))
    if not rows:
        return None, {}, {}, {}, {}
    df = pd.DataFrame(rows).set_index("edge_id")
    parts_ns = _NS(nodes=A.parts, shape=A.shape)
    bands, slack, paths, meta = edge_bands(parts_ns, A.cwd_parts, A.mcp, df, cutoff, cutoff_mode)
    return df, bands, slack, paths, meta


def _unit_edge_parts(A, ui, uj):
    """Map a built unit edge to its closest part pair (the argmin cell), for the extended
    part-level graph that prices locked-edge failures."""
    fi = np.asarray(A.cwd[ui])
    mj = A.nodes[uj][1]
    cells = np.argwhere(mj)
    cell = cells[int(np.nanargmin(fi[mj]))]
    pj = next(p for p in A.unit_parts[uj] if A.parts[p][1][cell[0], cell[1]])
    pi_ = min(A.unit_parts[ui],
              key=lambda p: float(np.asarray(A.cwd_parts[p])[cell[0], cell[1]]))
    return pi_, pj


def _locked_criticality(A, locked_df, beta):
    """Failure enumeration for locked intra-name edges (spec step 2: they are real corridor land).

    Runs on the EXTENDED part-level graph: parts as nodes, locked edges + every built unit edge
    attached to its closest part pair. Per locked edge: does cutting it disconnect the network,
    how many PART pairs strand (column is part-level for intra_name rows), the detour ratio when
    it survives, and -- mirroring augment()'s candidate semantics -- the cheapest single part-pair
    edge that would reconnect the sides, tested against the same beta ceiling for the
    irreplaceable flag. The backup is PRICED but never ADDED: augmentation policy for internal
    links is the review's call (H7), not the engine's.
    """
    EG = nx.Graph()
    EG.add_nodes_from(range(len(A.parts)))
    for eid, e in locked_df.iterrows():
        EG.add_edge(int(e["i"]), int(e["j"]), cost=float(e["cost"]))
    for eid, e in A.edges.iterrows():
        pi_, pj = _unit_edge_parts(A, int(e["i"]), int(e["j"]))
        if pi_ != pj and (not EG.has_edge(pi_, pj) or float(e["cost"]) < EG[pi_][pj]["cost"]):
            EG.add_edge(pi_, pj, cost=float(e["cost"]))

    out = {}
    for eid, e in locked_df.iterrows():
        p, q, c = int(e["i"]), int(e["j"]), float(e["cost"])
        attrs = dict(EG[p][q])
        EG.remove_edge(p, q)
        if nx.has_path(EG, p, q):
            detour = nx.shortest_path_length(EG, p, q, weight="cost")
            out[eid] = dict(disconnects=False, n_pairs_lost=0,
                            cost_inflation=detour / c if c > 0 else np.inf,
                            mean_pair_inflation=np.nan,
                            backup_edge_id=None, backup_ratio=None, irreplaceable=False)
        else:
            side = nx.node_connected_component(EG, p)
            other = set(EG.nodes) - side
            src = side if len(side) <= len(other) else other
            dst = other if src is side else side
            best, best_c = None, np.inf
            for a in src:
                fa = np.asarray(A.cwd_parts[a], dtype="float64")
                for b in dst:
                    v = float(np.nanmin(fa[A.parts[b][1]]))
                    if np.isfinite(v) and v > 0 and v < best_c and {a, b} != {p, q}:
                        best, best_c = (a, b), v
            irrep = not (best is not None and best_c <= beta * c)
            out[eid] = dict(disconnects=True, n_pairs_lost=len(side) * len(other),
                            cost_inflation=np.inf, mean_pair_inflation=np.inf,
                            backup_edge_id=(f"P{min(best):03d}_{max(best):03d}" if best else None),
                            backup_ratio=(best_c / c if best is not None and c > 0 else None),
                            irreplaceable=irrep)
        EG.add_edge(p, q, **attrs)
    return out


def _locked_eligibility(A):
    """D27 (2026-09-28): a locked intra-name link (D16) never competed in the tree, so an irreplaceable class on it is a
    management assertion until the alternative-link test (D7) has been run against the full candidate set. _locked_criticality
    prices the cheapest part-pair alternative under beta for EVERY locked link on the extended part graph (routes via other
    names included), so `alt_test_run` is True for all of them; `edge_irreplaceable` = the class-eligible flag every consumer
    reads. Its `alt_cost` = the priced backup (disconnecting) or the detour's cost (a route via other names survives).
    G20: no locked link is edge-irreplaceable without the test; every tested locked link has a non-null alt_cost unless no
    alternative exists at all."""
    e = A.edges
    e["locked"] = e["edge_class"].eq("intra_name")
    e["alt_test_run"] = e["locked"]
    if "alt_cost" not in e.columns:
        e["alt_cost"] = np.nan
    for eid in e.index[e["locked"]]:
        r = e.loc[eid]
        if pd.notna(r.get("backup_ratio")) and r["cost"] > 0:
            e.loc[eid, "alt_cost"] = float(r["backup_ratio"]) * float(r["cost"])
        elif not bool(r.get("disconnects", False)) and pd.notna(r.get("cost_inflation")) and np.isfinite(r["cost_inflation"]):
            e.loc[eid, "alt_cost"] = float(r["cost_inflation"]) * float(r["cost"])
    e["edge_irreplaceable"] = (e["irreplaceable"] == True) & (~e["locked"] | e["alt_test_run"])
    bad = e.index[e["locked"] & (e["edge_irreplaceable"] == True) & ~e["alt_test_run"]]
    assert not len(bad), f"G20 FAILED: locked link(s) carry an irreplaceable class without the alternative-link test: {list(bad)}"
    untested = e.index[e["locked"] & e["alt_test_run"] & e["alt_cost"].isna() & ~(e["irreplaceable"] == True)]
    assert not len(untested), f"G20 FAILED: tested locked link(s) without a priced alternative: {list(untested)}"
    n_lk = int(e["locked"].sum())
    print(f"  G20 OK: {n_lk} locked link(s), all tested against the full candidate set; "
          f"{int(e['edge_irreplaceable'].sum())} edge-irreplaceable links after eligibility")


def _pair_path_cells(A, a, b):
    """Least-cost path length (cells) between units a and b on the baseline fields -- the alternative link's own route (D29).
    Mirrors edge_bands' traceback in both storage modes; seeds from a, stops at b's nearest cell (early stop)."""
    cwd, mcp = A.cwd, A.mcp
    compact = (getattr(cwd, "pu", None) is not None and getattr(A, "node_flat", None) is not None
               and cwd.pu.shape == tuple(A.shape))
    if compact:
        fa = np.asarray(cwd.compact(a)); cb = A.node_cidx[b]
        k = int(np.argmin(fa[cb]))
        target = tuple(int(v) for v in np.unravel_index(int(A.node_flat[b][k]), A.shape))
    else:
        fa = np.asarray(cwd[a]); mb = A.nodes[b][1]
        cells = np.argwhere(mb)
        target = tuple(int(v) for v in cells[int(np.nanargmin(fa[mb]))])
    mcp.find_costs([tuple(x) for x in np.argwhere(A.nodes[a][1])], ends=[target])
    return int(len(mcp.traceback(target)))


def _alt_kind(len_ratio, cost_ratio, res_ratio, beta, tol):
    """D29: why the alternative failed the beta test. far = the route is >= beta x longer at similar resistance; hard = not
    that much longer, so resistance did it; both = longer AND harder; affordable = it passed (a backup); none = no alternative."""
    if not np.isfinite(cost_ratio):
        return "none"
    if cost_ratio < beta:
        return "affordable"
    far, hard = len_ratio >= beta, res_ratio > tol
    return "far" if far and not hard else ("hard" if not far else "both")


def _alt_link_metrics(A, beta):
    """D29 (2026-09-28): decompose the cheapest alternative link the beta test compared against (cg.augment's `alt`) into
    least-cost path length (`alt_len_km`) and mean resistance per cell (`alt_mean_res` = alt_cost / cells), and name its kind
    (`alt_kind`) against the edge's own route. One early-stop traceback per tested bridge."""
    e = A.edges
    if "alt_i" not in e.columns:
        for col in ("alt_i", "alt_j", "alt_cost"):
            e[col] = np.nan
    live = config.CORRIDORS[A.key]
    tol = float(A.cfg.get("alt_res_tol", live.get("alt_res_tol", 1.5)))
    e["alt_len_km"] = np.nan; e["alt_mean_res"] = np.nan; e["alt_kind"] = None
    n = 0
    for eid in e.index:
        r = e.loc[eid]
        if pd.isna(r.get("alt_i")) or pd.isna(r.get("alt_cost")) or r["cost"] <= 0:
            if bool(r.get("irreplaceable", False)) and pd.isna(r.get("alt_cost")):
                e.loc[eid, "alt_kind"] = "none"
            continue
        cells = _pair_path_cells(A, int(r["alt_i"]), int(r["alt_j"])); n += 1
        own = max(float(r["centreline_cells"]), 1.0)
        e.loc[eid, "alt_len_km"] = cells * A.cell_km
        e.loc[eid, "alt_mean_res"] = float(r["alt_cost"]) / max(cells, 1)
        own_res = float(r["cost"]) / own
        e.loc[eid, "alt_kind"] = _alt_kind(cells / own, float(r["alt_cost"]) / float(r["cost"]),
                                           (float(r["alt_cost"]) / max(cells, 1)) / own_res if own_res > 0 else np.inf, beta, tol)
    kinds = e["alt_kind"].value_counts(dropna=True).to_dict()
    print(f"  D29: alternative links decomposed for {n} tested bridge(s) -- kinds {kinds} (alt_res_tol {tol:g})")


# ================= baseline network =================
def cost_distances(A, cache=True):
    """Cost-weighted distance from every SEED PART; unit fields derived on top. The expensive
    stage: one MCP pass per part.

    Cached to disk by (resistance, part-structure) identity, because the whole ensemble (axes
    B/C/D) reuses exactly these fields -- axis C drops a NAME, which removes rows and columns from
    the distance matrix but leaves every remaining field untouched, and axes B/D never touch
    resistance at all. So the ensemble costs one CWD computation plus cheap re-derivations.

    D16 field semantics (queued clarification 1): a multi-part unit's field is the POINTWISE MIN
    over its seed parts' fields -- identical to multi-seed CWD from the part union -- and is what
    bands, near-optimality and branches all read. It is materialised once per multi-part unit
    (`unit_XXX.npy`) so edge_bands can memmap it like any other field; single-part units alias
    their part's file with no copy.
    """
    cache_dir = None
    compact = bool(A.cfg.get("cwd_compact", False))          # wolverine: routable cells only
    pu = A.pu if compact else None
    if cache:
        # A.cfg comes back from run_config.json as strings; joining under PROJECT_DIR keeps
        # absolute paths absolute (pathlib: an absolute right side wins) and fixes relative ones.
        gdir = config.PROJECT_DIR / pathlib.Path(A.cfg["grid"]["dir"])
        sha = _resistance_sha(A)
        cache_dir = pathlib.Path(gdir) / "cwd_cache" / (sha + ("_c" if compact else ""))
        hit = cache_dir.exists() and len(list(cache_dir.glob("part_*.npy"))) == len(A.parts)
        print(f"cost-weighted distance from {len(A.parts)} seed parts "
              f"({'cache HIT' if hit else 'computing'}: {cache_dir.name}"
              f"{', compact' if compact else ''})")
    A.cwd_parts, A.mcp = _cwd_all(A, A.resistance_arr, [m for _, m in A.parts],
                                  cache_dir, prefix="part", pu=pu)

    # ---- derive per-UNIT fields (min over the unit's parts) ---------------------------
    if cache:
        upaths = []
        for u in range(len(A.nodes)):
            pidx = A.unit_parts[u]
            if len(pidx) == 1:
                upaths.append(A.cwd_parts.paths[pidx[0]])
            else:
                p = cache_dir / _unit_fname(A, u)
                if not p.exists():
                    rd = (A.cwd_parts.compact if compact else A.cwd_parts.__getitem__)
                    fld = np.asarray(rd(pidx[0]), dtype="float32").copy()
                    for pi in pidx[1:]:
                        np.minimum(fld, np.asarray(rd(pi), dtype="float32"), out=fld)
                    np.save(p, fld)
                upaths.append(p)
        A.cwd = _CwdCache(upaths, pu)
        A.cwd_tag = f"unit_{sha}"
        print(f"  cache {A.cwd_parts.nbytes_on_disk/1e9:.1f} GB on disk, one field resident at a time")
        if compact:
            # flat + compact cell indices per routing unit: the gathers cost_matrix / edge_bands use
            A.node_flat = [np.flatnonzero(m.ravel()) for _, m in A.nodes]
            A.node_cidx = [np.searchsorted(A.cwd.flat_pu, nf).astype(np.int32) for nf in A.node_flat]
            for nf, ci in zip(A.node_flat, A.node_cidx):
                assert np.array_equal(A.cwd.flat_pu[ci], nf), "node cells must lie inside the routable set"
        if A.cfg.get("band_cache"):
            A.band_memo = {}                                  # tag -> _BandStore (persisted per run dir)
    else:
        fields = []
        for u in range(len(A.nodes)):
            pidx = A.unit_parts[u]
            fld = np.asarray(A.cwd_parts[pidx[0]], dtype="float64")
            for pi in pidx[1:]:
                fld = np.minimum(fld, np.asarray(A.cwd_parts[pi], dtype="float64"))
            fields.append(fld)
        A.cwd = fields
    return A


def corridor_network(A, cutoff=None, cutoff_mode="abs", beta=None, verbose=True):
    """Cost matrix -> locked intra-name MSTs (D16) + inter-name graph (MST + bridge backup) ->
    per-edge bands -> masks."""
    cutoff = A.cfg["cwd_cutoff_abs"] if cutoff is None else cutoff
    beta = A.cfg.get("beta") if beta is None else beta

    A.D = _unit_D(A)
    labels = [lbl for lbl, _ in A.nodes]
    A.graph, A.edges = cg.build(A.D, labels, A.kinds, beta=beta, verbose=verbose,
                                centrality_method=A.cfg.get("centrality", "current_flow"))   # D19
    A.edges["edge_class"] = np.where(A.edges["is_adjacency"], "adjacency", "inter")

    A.bands, A.slack, A.paths, A.band_meta = edge_bands(
        A, A.cwd, A.mcp, A.edges, cutoff, cutoff_mode, tag=getattr(A, "cwd_tag", None))

    # D16: locked intra-name edges appended -- real corridor land with its own bands + criticality,
    # reported as a separate area line (never folded into MST/augmentation area).
    lk_df, lk_bands, lk_slack, lk_paths, lk_meta = _locked_edges(A, cutoff, cutoff_mode)
    if lk_df is not None:
        crit = _locked_criticality(A, lk_df, beta)
        for col in ("disconnects", "n_pairs_lost", "cost_inflation", "mean_pair_inflation",
                    "backup_edge_id", "backup_ratio", "irreplaceable"):
            lk_df[col] = [crit[e][col] for e in lk_df.index]
        A.edges = pd.concat([A.edges, lk_df])
        A.bands.update(lk_bands); A.slack.update(lk_slack)
        A.paths.update(lk_paths); A.band_meta.update(lk_meta)
    A.locked_edge_ids = list(lk_df.index) if lk_df is not None else []

    A.corridor, A.swath = network_mask(A, A.bands)
    A.cutoff, A.cutoff_mode = cutoff, cutoff_mode

    A.edges["band_cells"] = [len(A.bands[e]) for e in A.edges.index]
    A.edges["band_km2"] = A.edges["band_cells"] * A.cell_km2
    A.edges["centreline_cells"] = [A.band_meta[e]["centreline_cells"] for e in A.edges.index]
    A.edges["centreline_km"] = A.edges["centreline_cells"] * A.cell_km
    A.base_path_cells = int(A.edges["centreline_cells"].sum())
    A.n_groups = _n_groups(A, A.corridor)
    _locked_eligibility(A)                    # D27 + G20: locked links carry an irreplaceable class only once tested
    _alt_link_metrics(A, beta)                # D29: the alternative link's length and resistance, and its kind

    if verbose:
        n_adj = int(A.edges.is_adjacency.sum())
        n_lk = len(A.locked_edge_ids)
        print(f"network: {len(A.edges)} edges ({len(A.edges)-n_adj-n_lk} between separated nodes, "
              f"{n_adj} adjacencies, {n_lk} locked intra-name) | band cutoff {cutoff:g} "
              f"({cutoff_mode})")
        print(f"  corridor (NEW land) {int(A.corridor.sum()):,} cells = "
              f"{int(A.corridor.sum())*A.cell_km2:,.0f} km²  |  raw swath incl. node land "
              f"{int(A.swath.sum())*A.cell_km2:,.0f} km²")
        by = A.edges.groupby("edge_class")["band_km2"].sum()
        print("  band area by class (incl. node land): "
              + "  ".join(f"{k} {v:,.0f} km²" for k, v in by.items()))
        print(f"  anchors connected: {len(A.nodes)} nodes in {A.n_groups} network group(s) "
              f"(1 = fully connected)")
        # G3: two independent implementations of one quantity -- a raster flood fill over the
        # painted corridor, and the graph's own component count. They must agree.
        g_comp = nx.number_connected_components(A.graph)
        assert A.n_groups == g_comp, (
            f"G3 FAILED: raster says {A.n_groups} connected group(s) but the graph says {g_comp}. "
            f"A band that connects visually but not graph-theoretically (or vice versa) means the "
            f"cutoff and the edge set disagree.")
        print(f"  G3 OK: raster and graph agree on {g_comp} component(s)")
    return A


def gate_g1(key="north", v1_dir=None, frac=0.05, tol=0.999, verbose=True):
    """G1 -- ENGINE EQUIVALENCE ON THE OLD RESISTANCE. The real refactor gate.

    Everything else in the v2 rebuild changes the answer on purpose, so "re-run and expect the same
    corridors" is unavailable. This isolates the REFACTOR from every semantic change: feed the new
    pipeline v1's own frozen resistance raster on v1's own 1 km grid, restrict it to MST-only edges
    (beta=0) and the relative band (`mode="frac"`, 0.05), and require it to reproduce v1's corridor.

    If this passes, the split of `_network_from_cwd` into cost_matrix / build / edge_bands /
    network_mask preserved behaviour, and any later difference is attributable to D1/D6/D7 rather
    than to a bug. It is also what catches the `mcp.traceback` trap -- tracebacks read whichever
    `find_costs` ran last, so a mis-grouped optimisation silently returns paths from the wrong
    source node, and the centre-line comparison below is what notices.

    Not exactly 1.0: v1's resistance.tif is float32 on disk while v1 solved in float64, so ties in
    MCP_Geometric can flip a handful of cells.
    """
    v1_dir = pathlib.Path(v1_dir or (config.RESULTS_DIR /
                                     config.CORRIDORS[key]["results_subdir"] / "_v1_frozen"))
    cfg = copy.deepcopy(config.CORRIDORS[key])

    res_da = rioxarray.open_rasterio(v1_dir / "resistance.tif", masked=True).squeeze()
    arr = res_da.values.astype("float64")
    pu = np.isfinite(arr) & (arr >= 0)                      # v1 wrote off-PU as -1
    template = res_da
    crs = template.rio.crs
    transform = template.rio.transform()
    shape = template.shape
    rx, ry = template.rio.resolution()
    cell_km2 = abs(rx * ry) / 1e6

    nc = cfg["nodes"]
    min_cells = max(1, int(round(nc["node_min_km2"] / cell_km2)))
    ipca = config._load_source(pathlib.Path(nc["proposed"]), nc.get("source_filter")).to_crs(crs)
    nfield = next(c for c in ipca.columns if "name" in c.lower())

    def _rast(geom):
        return rasterize([(geom, 1)], out_shape=shape, transform=transform, fill=0,
                         dtype="uint8").astype(bool) & pu

    raw = []
    for _, row in ipca.iterrows():
        m = _rast(row.geometry)
        if m.sum() >= min_cells:
            raw.append((f"IPCA · {row[nfield]}", m, "ipca"))
    pas = gpd.read_file(config.PA_VECTOR).to_crs(crs).dissolve(by="PA_Name").reset_index()
    pas = pas[pas.geometry.area / 1e6 >= nc["existing_pa_min_km2"]]
    for _, row in pas.iterrows():
        m = _rast(row.geometry)
        if m.sum() >= min_cells:
            raw.append((f"PA · {row['PA_Name']}", m, "pa"))
    nodes, kinds, _ = _dedupe_nodes(raw, nc.get("dedupe_overlap_frac", 0.5), cell_km2)

    node_union = np.zeros(shape, bool)
    for _, m in nodes:
        node_union |= m

    A = _NS(key=key, cfg=cfg, run_id="gate_g1", template=template, crs=crs, transform=transform,
            shape=shape, pu=pu, cell_km2=cell_km2, cell_km=abs(rx) / 1000.0,
            nodes=nodes, kinds=kinds, node_union=node_union,
            resistance_arr=np.where(pu, arr, np.inf), cost=arr)

    print(f"G1: replaying the v1 network on v1's own resistance ({shape[1]}x{shape[0]} @ "
          f"{A.cell_km:.0f} km, {len(nodes)} nodes)")
    A.cwd, A.mcp = _cwd_all(A, A.resistance_arr, [m for _, m in A.nodes], cache_dir=None)
    D = cost_matrix(A, A.cwd)
    _, edges = cg.build(D, [l for l, _ in nodes], kinds, beta=0, verbose=False)
    bands, _, _, meta = edge_bands(A, A.cwd, A.mcp, edges, frac, "frac", want_slack=False)
    corr, swath = network_mask(A, bands)

    v1 = rioxarray.open_rasterio(v1_dir / "corridors.tif", masked=True).squeeze().values > 0
    j = _jaccard(corr, v1)
    n_adj = int(edges.is_adjacency.sum())
    v1s = json.loads((v1_dir / "corridor_summary.json").read_text())
    path_cells = int(sum(m["centreline_cells"] for m in meta.values()))

    print(f"  edges      new {len(edges)} ({n_adj} zero-cost)   v1 {v1s['n_mst_edges']} "
          f"({v1s['n_mst_edges']-v1s['n_mst_edges_separated']} zero-cost)")
    print(f"  corridor   new {int(corr.sum())*cell_km2:,.0f} km²   v1 {v1s['corridor_km2']:,} km²")
    print(f"  centreline new {path_cells} cells")
    print(f"  JACCARD vs v1 corridors.tif = {j:.4f}")
    assert len(edges) == v1s["n_mst_edges"], (
        f"G1 FAILED: MST has {len(edges)} edges, v1 had {v1s['n_mst_edges']}")
    assert j >= tol, (
        f"G1 FAILED: Jaccard {j:.4f} < {tol}. The refactor changed the network on IDENTICAL "
        f"inputs, so a later v1-vs-v2 difference could not be attributed to D1/D6/D7.")
    print(f"  G1 OK — the refactor is behaviour-preserving on identical inputs")
    return dict(jaccard=j, n_edges=len(edges), corridor_km2=int(corr.sum()) * cell_km2, A=A)


def secured_status(A, frac=None, verbose=True):
    """W11 -- protection as a STATUS on the routed network (routing untouched; D5 keeps values and
    status out of resistance). Per separated edge:
        centreline_protected_frac  share of the least-cost centre-line cells inside nodes + protected land
        band_protected_frac        share of the band's NEW land inside protected land
        band_unprotected_km2       the corridor land there is still to secure
        secured                    centreline_protected_frac >= secured_centreline_frac (0.95): the link is
                                   already connected within protected land -- listed, never mapped
    Also A.corridor_unprotected = corridor & ~protected (what the maps show)."""
    prot = getattr(A, "protected", None)
    if prot is None:
        print("secured_status: no protected layer on this run (nodes.protected unset)"); return A
    frac = float(A.cfg.get("secured_centreline_frac", 0.95)) if frac is None else float(frac)
    pa = A.protected_pa if getattr(A, "protected_pa", None) is not None else prot
    ipca = A.protected_ipca if getattr(A, "protected_ipca", None) is not None else np.zeros(A.shape, bool)
    inside_pa = A.node_union | pa                      # existing PAs only
    inside_all = inside_pa | ipca                      # + proposed IPCAs (taken as given)
    cp, cpa, cpi, bp, bpa, bpi, bu, by = {}, {}, {}, {}, {}, {}, {}, {}
    for eid in A.edges.index:
        e = A.edges.loc[eid]
        if e["cost"] <= 0 or e["is_adjacency"]:
            cp[eid] = cpa[eid] = cpi[eid] = bp[eid] = bpa[eid] = bpi[eid] = np.nan; bu[eid] = 0.0; by[eid] = ""
            continue
        pth = A.paths.get(eid)
        if pth is not None and len(pth):
            f_pa = float(inside_pa[pth[:, 0], pth[:, 1]].mean())
            f_all = float(inside_all[pth[:, 0], pth[:, 1]].mean())
            f_ip = float((ipca & ~inside_pa)[pth[:, 0], pth[:, 1]].mean())
        else:
            f_pa = f_all = f_ip = np.nan
        idx = A.bands[eid]
        new = ~A.node_union.ravel()[idx]
        n_new = int(new.sum())
        n_pa = int((pa.ravel()[idx] & new).sum())
        n_ip = int((ipca.ravel()[idx] & ~pa.ravel()[idx] & new).sum())
        cp[eid], cpa[eid], cpi[eid] = f_all, f_pa, f_ip
        bp[eid] = ((n_pa + n_ip) / n_new) if n_new else np.nan
        bpa[eid] = (n_pa / n_new) if n_new else np.nan
        bpi[eid] = (n_ip / n_new) if n_new else np.nan
        bu[eid] = (n_new - n_pa - n_ip) * A.cell_km2
        # which layer satisfies the link: existing PAs alone, or only once the proposed IPCAs are real
        by[eid] = ("pa" if np.isfinite(f_pa) and f_pa >= frac else
                   ("ipca" if np.isfinite(f_all) and f_all >= frac else ""))
    A.edges["centreline_protected_frac"] = pd.Series(cp)
    A.edges["centreline_pa_frac"] = pd.Series(cpa)
    A.edges["centreline_ipca_frac"] = pd.Series(cpi)
    A.edges["band_protected_frac"] = pd.Series(bp)
    A.edges["band_pa_frac"] = pd.Series(bpa)
    A.edges["band_ipca_frac"] = pd.Series(bpi)
    A.edges["band_unprotected_km2"] = pd.Series(bu)
    A.edges["secured_by"] = pd.Series(by)
    A.edges["secured"] = A.edges["secured_by"] != ""
    A.corridor_unprotected = A.corridor & ~prot
    A.secured_frac = frac
    if verbose:
        n_sep = int(((A.edges["cost"] > 0) & ~A.edges["is_adjacency"]).sum())
        n_pa_ = int((A.edges["secured_by"] == "pa").sum()); n_ip_ = int((A.edges["secured_by"] == "ipca").sum())
        tot, unp = int(A.corridor.sum()) * A.cell_km2, int(A.corridor_unprotected.sum()) * A.cell_km2
        in_pa = int((A.corridor & pa).sum()) * A.cell_km2; in_ip = int((A.corridor & ipca & ~pa).sum()) * A.cell_km2
        print(f"protection status (W11, centreline >= {frac:g} inside nodes + protected land): of {n_sep} separated links, "
              f"{n_pa_} already connected within EXISTING PAs, {n_ip_} more only once the proposed IPCAs are realized")
        print(f"  corridor land {tot:,.0f} km²: inside existing PAs {in_pa:,.0f}, inside proposed IPCAs (not PAs) {in_ip:,.0f}, "
              f"UNPROTECTED {unp:,.0f} km²")
    return A


def gate_gw4(A, n=3):
    """GW4 -- the band store + early-stop traceback (wolverine `band_cache`) reproduce a fresh,
    full-field computation EXACTLY on `n` sampled baseline edges (idx, slack, centre-line)."""
    cand = [e for e in A.edges.index
            if A.edges.loc[e, "cost"] > 0 and not A.edges.loc[e, "is_adjacency"]
            and A.edges.loc[e, "edge_class"] != "intra_name"]
    if not cand:
        print("GW4: no separated edges to test"); return True
    pick = [cand[int(k)] for k in np.linspace(0, len(cand) - 1, min(n, len(cand))).round()]
    B = _NS(**{k: getattr(A, k) for k in ("nodes", "shape", "pu", "cfg", "node_flat", "node_cidx")
               if hasattr(A, k)})
    B.band_memo = None
    bands, slack, paths, meta = edge_bands(B, A.cwd, A.mcp, A.edges.loc[pick], A.cutoff, A.cutoff_mode, tag=None)
    for e in pick:
        assert np.array_equal(bands[e], A.bands[e]), f"GW4 FAILED on {e}: band cells differ"
        assert np.array_equal(slack[e], A.slack[e]), f"GW4 FAILED on {e}: slack differs"
        assert np.array_equal(paths.get(e, np.zeros((0, 2))), A.paths.get(e, np.zeros((0, 2)))), \
            f"GW4 FAILED on {e}: centre-line differs (early-stop traceback)"
        assert abs(meta[e]["lcp"] - A.band_meta[e]["lcp"]) == 0.0, f"GW4 FAILED on {e}: lcp differs"
    print(f"GW4 OK: band store + early-stop traceback bit-exact on {len(pick)} sampled edges "
          f"({', '.join(pick)})")
    return True


def calibrate_cutoff(A, target_km2=None, edges="mst", lo=0.0, hi=None, tol_km2=50, max_iter=20):
    """Find the absolute cutoff whose MST-only corridor area matches `target_km2` (D6).

    Calibrated on MST-ONLY edges with the same `& ~node_union` area definition v1 used, so a
    v1<->v2 route comparison is not confounded by band size. Augmentation adds area on top and is
    reported separately -- calibrating against the augmented network would let the cutoff quietly
    absorb the augmentation and conflate D6 with D7.

    Area is monotone in the cutoff, so this is a bisection. Prints the whole curve: the value has
    to be visible as a choice, not fitted silently.
    """
    cal = A.cfg.get("calibration", {})
    target_km2 = cal.get("target_km2") if target_km2 is None else target_km2
    edges = cal.get("edges", edges)

    # INTER-NAME MST only (spec step 1): _unit_D contracts link_locked names into single units, so
    # cg.build's MST is the quotient MST; locked intra-name bands never enter -- calibrating
    # against them would let the cutoff absorb D16 and conflate it with D6.
    D = getattr(A, "D", None)
    if D is None:
        D = A.D = _unit_D(A)
    labels = [lbl for lbl, _ in A.nodes]
    _, df = cg.build(D, labels, A.kinds, beta=0 if edges == "mst" else A.cfg["beta"], verbose=False)
    # D22 (2026-09-28): under link_competing a name's parts are separate units, so the unit MST can hold WITHIN-NAME edges.
    # D16's rule stands -- calibration uses the inter-name MST only, intra-name area is reported separately -- so those
    # edges are dropped from the calibration set here (they still enter the network and its bands).
    if edges == "mst" and hasattr(A, "unit_name") and {"i", "j"} <= set(df.columns):
        same = [A.unit_name[int(r.i)] == A.unit_name[int(r.j)] for r in df.itertuples()]
        if any(same):
            print(f"  D16/D22: {sum(same)} within-name part edge(s) in the unit MST excluded from calibration (inter-name MST only)")
            df = df[[not x for x in same]]

    if hi is None:                       # start from a cutoff that comfortably overshoots
        hi = float(np.nanpercentile(D[np.isfinite(D) & (D > 0)], 50))
    print(f"calibrating cwd_cutoff_abs -> {target_km2:,} km² on {len(df)} {edges} edges")

    def area_at(c):
        bands, _, _, _ = edge_bands(A, A.cwd, A.mcp, df, c, "abs", want_slack=False)
        corr, _ = network_mask(A, bands)
        return int(corr.sum()) * A.cell_km2

    best = None
    for it in range(max_iter):
        mid = 0.5 * (lo + hi)
        a = area_at(mid)
        print(f"  iter {it+1:>2}: cutoff {mid:12,.1f} -> {a:10,.0f} km²")
        best = (mid, a)
        if abs(a - target_km2) <= tol_km2:
            break
        lo, hi = (mid, hi) if a < target_km2 else (lo, mid)
    print(f"\ncwd_cutoff_abs = {best[0]:,.1f}  reproduces {best[1]:,.0f} km² "
          f"(target {target_km2:,}, {edges} edges; residual {best[1]-target_km2:+,.0f} km²)")
    print(f"  -> cc.set_cutoff(A, {best[0]:.1f}, {best[1]:.0f}) writes it into run_config.json "
          f"(and mirror it into config.CORRIDORS[{A.key!r}] for future runs)")
    return best


def set_cutoff(A, cutoff, area_km2=None):
    """Write the calibrated cwd_cutoff_abs into THIS run's run_config.json (spec step 1).

    The run dir is the engine's only input after cc.start(), so the calibrated value must land
    there -- notebooks 03/04 re-attach via cc.load() and read it back. Mirroring the value into
    config.CORRIDORS is a separate, manual act (it changes the baseline for FUTURE runs)."""
    A.cfg["cwd_cutoff_abs"] = float(cutoff)
    A.rec["cfg"]["cwd_cutoff_abs"] = float(cutoff)
    A.cfg["cutoff_detour_km"] = A.rec["cfg"]["cutoff_detour_km"] = float(cutoff) * A.cell_km     # D31: the same cutoff as detour distance on open ground
    A.rec["calibration_result"] = {"cwd_cutoff_abs": float(cutoff),
                                   "area_km2": (None if area_km2 is None else float(area_km2)),
                                   "target_km2": A.cfg.get("calibration", {}).get("target_km2")}
    (A.run_dir / "run_config.json").write_text(json.dumps(A.rec, indent=2, ensure_ascii=False))
    print(f"cwd_cutoff_abs = {cutoff:,.1f} (= {cutoff * A.cell_km:.2f} km of extra travel on open ground, D31) written into {A.run_id}/run_config.json")
    return A


# ================= linkage priority (D9) =================
def _jaccard(a, b):
    u = int((a | b).sum())
    return int((a & b).sum()) / u if u else 1.0


def priority_surface(A):
    """D9 -- the graded linkage priority surface, the primary deliverable.

    Per edge, within-band quality q_e = 1 - slack_e/allow_e falls from 1 on the least-cost line to
    0 at the band edge. Per cell:
        priority   = max_e ( ecfb_raw_e * q_e )
        edge_owner = argmax_e
    MAX, not sum: it stays bounded, it gives every cell a single owning edge (so the map can be
    interrogated), and it stops overlap regions being inflated purely because edges are redundant
    there -- which would invert the meaning, since redundancy is the opposite of criticality.

    Deliberately NOT hard corridor lines: lines invite site-level readings this model cannot
    support at 300 m over a structural-connectivity surface.
    """
    n = A.shape[0] * A.shape[1]
    pri = np.zeros(n, "float32")
    owner = np.full(n, -1, "int16")
    w = A.edges["ecfb_raw"].to_dict()
    order = {e: k for k, e in enumerate(A.edges.index)}

    for eid, idx in A.bands.items():
        allow = A.band_meta[eid]["allow"]
        we = w.get(eid, 0.0)
        if not np.isfinite(we) or we <= 0 or allow <= 0:
            continue                      # adjacency edges (nan) contribute no corridor land
        q = 1.0 - (A.slack[eid] / allow)
        val = (we * np.clip(q, 0.0, 1.0)).astype("float32")
        hit = val > pri[idx]
        sel = idx[hit]
        pri[sel] = val[hit]
        owner[sel] = order[eid]

    pri = pri.reshape(A.shape)
    owner = owner.reshape(A.shape)
    keep = A.corridor                     # NEW land only, consistent with every other output
    A.priority = np.where(keep, pri, 0.0).astype("float32")
    A.edge_owner = np.where(keep, owner, -1).astype("int16")

    # Tiers are percentiles of the non-zero surface, pre-registered in config BEFORE the run.
    t = A.cfg["priority_tiers"]
    nz = A.priority[A.priority > 0]
    A.tiers = {k: float(np.percentile(nz, v)) if nz.size else 0.0 for k, v in t.items()}
    A.priority_class = np.zeros(A.shape, "uint8")
    for cls, (name, _) in enumerate(sorted(t.items(), key=lambda kv: kv[1]), start=1):
        A.priority_class[A.priority >= A.tiers[name]] = cls
    A.priority_class[~keep] = 0

    print(f"linkage priority surface over {int(keep.sum()):,} corridor cells")
    for name in sorted(t, key=lambda k: -t[k]):
        m = A.priority_class == (sorted(t.items(), key=lambda kv: kv[1]).index(
            (name, t[name])) + 1)
        print(f"  {name:12s} (>= p{t[name]:>2}): {int(m.sum())*A.cell_km2:>8,.0f} km²")
    return A


# ================= near-optimality surface (D11) =================
def _edge_fields(A, eid):
    """(field_i, field_j) for an edge row -- unit fields for inter edges, part fields for locked
    intra-name edges (D16 clarification 1)."""
    e = A.edges.loc[eid]
    if e["edge_class"] == "intra_name":
        return A.cwd_parts[int(e["i"])], A.cwd_parts[int(e["j"])]
    return A.cwd[int(e["i"])], A.cwd[int(e["j"])]


def _tier_breaks(spec, cutoff):
    """D30: {tier: slack break in cost units} from a spec whose values are 'cutoff', 'cutoff/N' or a number (absolute)."""
    out = {}
    for name, v in spec.items():
        if isinstance(v, str):
            s = v.replace(" ", "").lower()
            if s == "cutoff":
                out[name] = float(cutoff)
            elif s.startswith("cutoff/"):
                out[name] = float(cutoff) / float(s.split("/", 1)[1])
            else:
                raise ValueError(f"near_opt_tiers[{name!r}] = {v!r}: expected 'cutoff', 'cutoff/N' or a number (D30)")
        else:
            out[name] = float(v)
    return out


def near_optimality(A):
    """D11 -- the wall-to-wall near-optimality surface: min over baseline edges of slack, in RAW
    COST UNITS, defined on every routable cell.

    A least-cost model has no solution pool; the band IS the closed-form near-optimal set and
    slack is its continuous degree. Raw units keep the surface independent of cwd_cutoff_abs
    (calibrated for v1 area comparability, not meaning) -- the cutoff enters only the binary band
    and area accounting. Never label this or the ensemble fraction "frequency".

    Zero-cost adjacency edges contribute nothing (consistent with §7 of the methods doc). Streams
    edge by edge from the memmaps with a running minimum + argmin owner (step 4a).
    """
    eids = [e for e in A.edges.index
            if A.edges.loc[e, "cost"] > 0 and not A.edges.loc[e, "is_adjacency"]]
    no = np.full(A.shape, np.inf, "float64")
    owner = np.full(A.shape, -1, "int16")
    order = {e: k for k, e in enumerate(A.edges.index)}
    for eid in eids:
        fi, fj = _edge_fields(A, eid)
        field = np.asarray(fi, dtype="float64") + np.asarray(fj, dtype="float64")
        slack = field - A.band_meta[eid]["lcp"]
        upd = np.isfinite(slack) & (slack < no)
        no[upd] = slack[upd]
        owner[upd] = order[eid]
    no[~A.pu] = np.nan
    owner[~A.pu] = -1

    # G10 -- exact-zero on every baseline least-cost path cell (float32 field storage allows a
    # tiny relative residual), and tier classes monotone in slack.
    worst = 0.0
    for eid in eids:
        pth = A.paths.get(eid)
        if pth is None or not len(pth):
            continue
        res = np.nanmax(no[pth[:, 0], pth[:, 1]])
        worst = max(worst, float(res))
        eps = 1e-4 * max(A.band_meta[eid]["lcp"], 1.0)
        assert res <= eps, (
            f"G10 FAILED: near_optimality reaches {res:g} on the least-cost path of {eid} "
            f"(lcp {A.band_meta[eid]['lcp']:g}) -- slack must be ~0 there by construction.")
    print(f"G10 OK: max residual on baseline least-cost paths = {worst:.3g} cost units")

    # Tiers (D30, 2026-09-28): FIXED slack breaks in cost units -- fractions of the calibrated cutoff (robust core <= cutoff/6,
    # frequent <= cutoff/2, occasional <= cutoff = the band); routable cells beyond the band form a fourth class. Percentile
    # tiers were retired: over the union band they were area-weighted, and area is dominated by the long northern links, so
    # the breaks were set by the north; raw slack is comparable across links and fixed breaks keep it so.
    t = A.cfg.get("near_opt_tiers")
    live = config.CORRIDORS[A.key]["near_opt_tiers"]
    if not (isinstance(t, dict) and all(isinstance(v, str) for v in t.values())):
        print("  D30: this run's near_opt_tiers are the retired percentile spec -- using config.py's fixed breaks and pinning them into run_config")
        t = live; A.cfg["near_opt_tiers"] = t; A.rec["cfg"]["near_opt_tiers"] = t
        (A.run_dir / "run_config.json").write_text(json.dumps(A.rec, indent=2, ensure_ascii=False))
    thr = _tier_breaks(t, A.cutoff)
    ordered = sorted(thr.items(), key=lambda kv: kv[1])
    assert all(a[1] <= b[1] for a, b in zip(ordered, ordered[1:])), f"G10: tiers not monotone {thr}"
    cls = np.zeros(A.shape, "uint8")
    cls[A.pu] = len(ordered) + 1                                   # routable land beyond the band (slack > cutoff)
    # assign the tightest tier last so the smallest threshold wins
    for c, (name, v) in list(enumerate(ordered, start=1))[::-1]:
        cls[np.isfinite(no) & (no <= v)] = c
    cls[~A.pu] = 0
    # G22 (tiers + cutoff): breaks exactly at the registered fractions of the cutoff; the detour twin reproduces the cutoff
    for name, frac in (("robust_core", 6.0), ("frequent", 2.0), ("occasional", 1.0)):
        if name in thr:
            assert abs(thr[name] - A.cutoff / frac) <= 1e-9 * max(A.cutoff, 1.0), f"G22 FAILED: tier {name} break {thr[name]} != cutoff/{frac:g}"
    det = A.cfg.get("cutoff_detour_km")
    if det is not None:
        assert abs(float(det) / A.cell_km - A.cutoff) <= 1e-6 * max(A.cutoff, 1.0), f"G22 FAILED: cutoff_detour_km / cell size != cwd_cutoff_abs"
    print("  G22 OK: tier breaks at the registered fractions of the cutoff" + ("; detour twin consistent" if det is not None else ""))

    A.near_opt, A.near_opt_owner, A.near_opt_class, A.near_opt_thresholds = \
        no.astype("float32"), owner, cls, thr
    print(f"near-optimality surface over {int(A.pu.sum()):,} routable cells "
          f"(tiers = fixed slack breaks, fractions of the cutoff {A.cutoff:,.1f} = {A.cutoff * A.cell_km:.1f} km of detour on open ground)")
    for c, (name, v) in enumerate(ordered, start=1):
        print(f"  {name:12s} (slack <= {v:>10,.2f} = {t[name]:>9s}): "
              f"{int((cls == c).sum())*A.cell_km2:>9,.0f} km²")
    print(f"  {'beyond band':12s} (routable, slack > cutoff): "
          f"{int((cls == len(ordered)+1).sum())*A.cell_km2:>9,.0f} km²")

    dst = A.run_dir
    _tif(A, np.where(np.isfinite(A.near_opt), A.near_opt, -1), dst / "near_optimality.tif",
         "float32", -1)
    _tif(A, A.near_opt_owner, dst / "near_opt_owner.tif", "int16", -1)
    _tif(A, A.near_opt_class, dst / "near_optimality_class.tif", "uint8", 0)
    pd.DataFrame({"owner_code": [order[e] for e in eids], "edge_id": eids}) \
        .to_csv(dst / "near_opt_owner_legend.csv", index=False)
    print(f"  wrote near_optimality.tif, near_opt_owner.tif, near_optimality_class.tif "
          f"(+ owner legend)")
    return A


# ================= route branches (D12) =================
def route_branches(A):
    """D12 -- the unit of "alternative" is the ROUTE BRANCH: an 8-connected component of an edge's
    band at cutoff_branch = branch_mult x cwd_cutoff_abs.

    Band components are provably genuine i->j alternatives (G9): a band cell c has slack(c) <=
    cutoff, and every cell on the least-cost i->c->j path has slack <= slack(c), so each component
    is connected to both endpoints inside the band -- a failing assert means a masking or
    seed-handling bug, not a legitimate outcome. Per edge, n_branches == 1 => ROUTE-irreplaceable
    (no alternative routing within the link), reported alongside -- never merged with -- the D7
    beta-ceiling EDGE-irreplaceable flag. Locked intra_name edges get branches too (queued
    clarification 2), carrying edge_class through.

    Components are formed BEFORE node subtraction (an intermediate node splitting a route does not
    make it two alternatives), then node land is removed and slivers < branch_min_km2 dropped
    (count reported).
    """
    # D26 (2026-09-28): the sliver floor is RELATIVE to the link's band -- a component is a branch if its new-land area is
    # >= branch_min_frac x the link's new-land band area at cutoff_branch AND >= branch_min_cells. A fixed 10 km2 was noise on a
    # 200 km link and a real second route on a 30 km one (branch counts were length-biased). Runs predating the constants take
    # config.py's values and pin them. G21 reports the effect against the retired fixed floor.
    live = config.CORRIDORS[A.key]
    bm = A.cfg["branch_mult"]
    if "branch_min_frac" not in A.cfg or "branch_min_cells" not in A.cfg:
        print("  D26 constants not in this run's run_config (run predates them) -- taken from config.py and pinned into run_config.json")
        A.cfg["branch_min_frac"] = A.rec["cfg"]["branch_min_frac"] = float(live["branch_min_frac"])
        A.cfg["branch_min_cells"] = A.rec["cfg"]["branch_min_cells"] = int(live["branch_min_cells"])
        (A.run_dir / "run_config.json").write_text(json.dumps(A.rec, indent=2, ensure_ascii=False))
    bfrac, bcells = float(A.cfg["branch_min_frac"]), int(A.cfg["branch_min_cells"])
    cutoff_b = bm * A.cutoff
    legacy_cells = max(1, int(round(10.0 / A.cell_km2)))          # the retired fixed floor (10 km2), for G21 only
    # D25c (2026-09-29): only STRIPS are decomposed -- a front is one component by construction (its route sense is the width
    # ratio alone; n_branches written null, B1 forced true in classify_links) and a contact has nothing to decompose. The
    # counterfactual step (which measures the geometry) must therefore run first; notebook 04 orders step 2b before 4b.
    if "link_geometry" not in A.edges.columns:
        raise RuntimeError("route_branches: run cc.counterfactual_squeeze(A) FIRST (D25c: the link geometry -- strip / front / contact -- "
                           "decides which links are decomposed) -- notebook 04 step 2b before 4b")
    eids = [e for e in A.edges.index if A.edges.loc[e, "link_geometry"] == "strip"]
    n_skipped = int(A.edges["link_geometry"].isin(["front", "contact"]).sum())

    lab_out = np.zeros(A.shape, "int32")
    lab_pri = np.full(A.shape, np.inf, "float32")     # overlap resolution: lower min_slack wins
    rows, idx_store = [], {}
    n_dropped = 0
    dropped_frac, per_edge_drop, per_edge_legacy = [], {}, {}
    bid = 0
    struct = np.ones((3, 3), int)
    for eid in eids:
        e = A.edges.loc[eid]
        idx, sl = A.bands[eid], A.slack[eid]
        keep = idx[sl <= cutoff_b]
        m = np.zeros(A.shape[0] * A.shape[1], bool)
        m[keep] = True
        m = m.reshape(A.shape)
        band_new_cells = int((m & ~A.node_union).sum())                              # the link's new-land band at cutoff_branch
        floor_cells = max(bcells, int(np.ceil(bfrac * band_new_cells)))
        per_edge_drop[eid] = [0, 0.0]; per_edge_legacy[eid] = 0

        if e["edge_class"] == "intra_name":
            mi, mj = A.parts[int(e["i"])][1], A.parts[int(e["j"])][1]
        else:
            mi, mj = A.nodes[int(e["i"])][1], A.nodes[int(e["j"])][1]

        lab, n = ndimage.label(m, structure=struct)
        comps = []
        for k in range(1, n + 1):
            cm = lab == k
            # G9 -- hard assert: every component touches BOTH endpoint seed masks.
            assert (cm & mi).any() and (cm & mj).any(), (
                f"G9 FAILED on {eid}: a branch-band component does not reach both endpoints. "
                f"By the slack-monotonicity property this cannot happen on a correct band -- "
                f"suspect masking or seed handling, not the landscape.")
            comps.append(cm)

        for cm in comps:
            cm2 = cm & ~A.node_union
            cells = int(cm2.sum())
            if cells >= legacy_cells:
                per_edge_legacy[eid] += 1                                             # what the retired fixed floor would have kept (G21)
            if cells < floor_cells:
                n_dropped += 1
                frac = cells / band_new_cells if band_new_cells else 0.0
                dropped_frac.append(frac)
                per_edge_drop[eid][0] += 1; per_edge_drop[eid][1] = max(per_edge_drop[eid][1], frac)
                continue
            assert cells >= bcells and cells >= bfrac * band_new_cells, "G21: a kept branch violates the floor"
            fidx = np.flatnonzero(cm2.ravel())
            sl_sel = A.slack[eid][np.isin(A.bands[eid], fidx)]
            rr, cc = np.nonzero(cm2)
            # length proxy: extent along the component's principal axis (NOT a path length)
            xy = np.stack([cc - cc.mean(), rr - rr.mean()])
            w, v = np.linalg.eigh(np.cov(xy) if cells > 1 else np.eye(2))
            proj = v[:, -1] @ xy
            bid += 1
            rows.append(dict(
                branch=bid, branch_id=f"{eid}_{bid}", edge_id=eid,
                edge_class=e["edge_class"], label_i=e["label_i"], label_j=e["label_j"],
                area_km2=round(cells * A.cell_km2, 1), cells=cells,
                min_slack=float(sl_sel.min()) if sl_sel.size else 0.0,
                mean_slack=float(sl_sel.mean()) if sl_sel.size else 0.0,
                length_proxy_km=round(float(np.ptp(proj)) * A.cell_km, 1) if cells > 1 else round(A.cell_km, 1),
                bbox=[int(rr.min()), int(cc.min()), int(rr.max()), int(cc.max())]))
            idx_store[bid] = fidx
            pri = rows[-1]["min_slack"]
            win = cm2 & (pri < lab_pri)
            lab_out[win] = bid
            lab_pri[win] = pri

    br = pd.DataFrame(rows)
    if len(br):
        # branch numbering per edge, ordered by min slack (spec step 4b.4)
        br["k"] = br.groupby("edge_id")["min_slack"].rank(method="first").astype(int)
        br["branch_id"] = br["edge_id"] + "_" + br["k"].astype(str)
        per_edge = br.groupby("edge_id").size()
        nb = per_edge.reindex(A.edges.index).astype(float)
        nb[[e for e in A.edges.index if e in eids and e not in per_edge.index]] = 0.0     # decomposed, nothing kept
        A.edges["n_branches"] = nb                                                          # NaN = not decomposed (near-contiguous / adjacency)
        A.edges["route_irreplaceable_topo"] = (A.edges["n_branches"] == 1)                 # the old one-branch-only flag, retained (D12 amended)
    A.edges["branch_dropped_n"] = pd.Series({k: v[0] for k, v in per_edge_drop.items()}).reindex(A.edges.index)
    A.edges["branch_dropped_max_frac"] = pd.Series({k: v[1] for k, v in per_edge_drop.items()}).reindex(A.edges.index)
    A.edges["n_branches_fixed_floor"] = pd.Series(per_edge_legacy).reindex(A.edges.index)     # G21 comparison column
    A.branches, A.branch_idx = br, idx_store
    A.branch_label = lab_out

    n_multi = int((A.edges.get("n_branches", pd.Series(dtype=float)) > 1).sum())
    n_topo = int((A.edges.get("route_irreplaceable_topo", pd.Series(dtype=bool)) == True).sum())
    print(f"route branches @ {bm:g}x cutoff ({cutoff_b:,.0f}): {len(br)} branches over "
          f"{len(eids)} strips ({n_skipped} fronts / contacts not decomposed, D25c) | {n_topo} one-branch strips (topology), "
          f"{n_multi} with alternatives | {n_dropped} slivers dropped under the relative floor "
          f"(>= {bfrac:g} x band AND >= {bcells} cells, D26)")
    # G21 -- the floor's effect: dropped-fraction distribution, and every link whose branch count differs from the retired fixed floor
    if dropped_frac:
        q = np.percentile(dropped_frac, [50, 90, 100])
        print(f"  G21: dropped components' share of their band -- median {q[0]:.3f}, p90 {q[1]:.3f}, max {q[2]:.3f}")
    changed = [(eid, int(A.edges.loc[eid, "n_branches_fixed_floor"]), int(A.edges.loc[eid, "n_branches"]))
               for eid in eids if int(A.edges.loc[eid, "n_branches_fixed_floor"]) != int(A.edges.loc[eid, "n_branches"])]
    print(f"  G21: {len(changed)} link(s) change branch count vs the retired 10 km² floor"
          + (": " + ", ".join(f"{e} {a}->{b}" for e, a, b in changed) if changed else ""))
    A.rec.setdefault("g21", {}).update(dict(n_dropped=n_dropped, dropped_frac_p50=(float(np.median(dropped_frac)) if dropped_frac else None),
                                            dropped_frac_max=(float(max(dropped_frac)) if dropped_frac else None), n_links_changed=len(changed),
                                            links_changed=[e for e, _, _ in changed]))
    print("  route-irreplaceable (D12, within-link) vs edge-irreplaceable (D7, no alternative "
          "link) are DIFFERENT senses -- always reported together, never merged")

    dst = A.run_dir
    _tif(A, A.branch_label, dst / "branches.tif", "int32", 0)
    polys = []
    for r in br.itertuples():
        m = np.zeros(A.shape[0] * A.shape[1], bool)
        m[idx_store[r.branch]] = True
        m = m.reshape(A.shape)
        geom = [_shape(s) for s, v in shapes(m.astype("uint8"), mask=m, transform=A.transform)
                if v == 1]
        polys.append(dict(branch_id=r.branch_id, edge_id=r.edge_id, edge_class=r.edge_class,
                          area_km2=r.area_km2, min_slack=r.min_slack,
                          geometry=gpd.GeoSeries(geom, crs=A.crs).union_all()))
    if polys:
        gpd.GeoDataFrame(polys, crs=A.crs).to_file(dst / "branches.gpkg", driver="GPKG")
    br.drop(columns=["branch"]).to_csv(dst / "branches.csv", index=False, encoding="utf-8-sig")
    print(f"  wrote branches.tif, branches.gpkg, branches.csv")
    classify_links(A)                                              # D23 / D24 / D25: the classes, G18, G19 -- now that both senses exist
    return A


# ================= the link classes (D23 / D24 / D25) =================
LINK_CLASS_LABEL = {                       # internal key -> director string (spec 06 §3; D23 top-class string). D25c: four classes only --
    "both": "Only viable connection — no alternative link or route, and the land is already narrowing",   # the adjacent-areas rows are retired
    "edge": "Last affordable link — alternatives cost far more",
    "squeezed": "Already narrowing — corridor below its natural width",
    "securing": "Corridor land with options — route and partners can be chosen",
    "adjacency": "touching (zero-cost adjacency; not a link on the map)",
}
CORRIDOR_CLASSES = ("securing", "squeezed", "edge", "both")
GEOMETRIES = ("strip", "front", "contact")


def _link_class(adj, contact, E, B1, S):
    """The spec 05 §6 precedence under D25c, top-down, first match wins: touching -> not a link; contact -> the edge sense only;
    strip or front -> D23's eight-cell table (B1 already forced true on a front by the caller)."""
    if adj:
        return "adjacency"
    if contact:
        return "edge" if E else "securing"
    if E and B1 and S:
        return "both"
    if E:
        return "edge"
    if S:
        return "squeezed"
    return "securing"


def classify_links(A, floors=None, verbose=True):
    """D23 (land-aware top class; D12 amended) + D24 (resolution floor) + D25 (near-contiguous): the ONE derivation of every
    link's class -- map classes, legend counts and both alternatives tables read `link_class`. Needs the counterfactual step
    (width, near_contiguous, width_not_assessable) and the branch decomposition (n_branches). Writes class_truth_table.csv
    (G18) and floor_effect.csv (G19) into the run dir. `floors` = (width_floor_cells, len_floor_cells) override for the G19
    diagnostic only (never written)."""
    e = A.edges
    need = [c for c in ("link_geometry", "width_not_assessable", "squeeze_ratio_obs", "n_branches", "edge_irreplaceable") if c not in e.columns]
    if need:
        raise RuntimeError(f"classify_links: missing {need} -- run counterfactual_squeeze then route_branches first")
    rmax = float(A.cfg["squeeze_ratio"])
    wf, lf = floors if floors else (float(A.cfg["width_floor_cells"]), float(A.cfg["len_floor_cells"]))
    nz = (e["cost"] > 0) & (~e["is_adjacency"])
    ogw = e["open_ground_width_med"]
    unass = nz & (ogw.isna() | (ogw < wf) | (e["lcp_len_cells"] < lf))                  # D24 -> contact
    front = (nz & ~unass & (e["lcp_len_cells"] < ogw)).fillna(False).astype(bool)          # D25c descriptor
    if not floors:
        assert (front == e["link_geometry"].eq("front")).all() and (unass == e["link_geometry"].eq("contact")).all(), \
            "G24 FAILED: link_geometry disagrees with the D24 floor / front trigger re-derived here"
    E = e["edge_irreplaceable"] == True
    B1 = (e["n_branches"] == 1) | front                                                    # D25c: B1 forced true on a front (one component by construction)
    S = e["squeeze_ratio_obs"] < rmax
    cls = pd.Series([_link_class(bool(a), bool(u), bool(x), bool(y), bool(z))
                     for a, u, x, y, z in zip(e["is_adjacency"], unass, E, B1, S)], index=e.index)
    if floors:                                                     # diagnostic call: return the classes, touch nothing
        return cls
    near = front                                                   # (name kept for the descriptor lines below)
    e["width_not_assessable"] = unass.astype(bool)
    e["b1_forced"] = front
    e["squeezed"] = (nz & ~unass & S).astype(bool)
    e["route_irreplaceable_topo"] = ((e["n_branches"] == 1) & nz).astype(bool)
    e["route_irreplaceable"] = (nz & ~unass & B1 & S).astype(bool)                       # D12 amended: one branch (forced on fronts) AND narrow
    e["link_class"] = cls
    e["link_class_label"] = cls.map(LINK_CLASS_LABEL)
    counts = cls[nz].value_counts()
    # ---- G18: the eight-cell table over E x B1 x S for the links that reach it (fronts folded in under B1 = true), before any class raster ----
    reach = nz & ~unass
    tt = (pd.DataFrame({"E": E[reach].astype(int), "B1": B1[reach].astype(int), "S": S[reach].astype(int), "link_class": cls[reach],
                        "geometry": e.loc[reach, "link_geometry"]})
          .groupby(["E", "B1", "S", "link_class", "geometry"]).size().rename("n").reset_index().sort_values(["E", "B1", "S"], ascending=False))
    tt.to_csv(A.run_dir / "class_truth_table.csv", index=False)
    for k in CORRIDOR_CLASSES:
        assert int(tt.loc[tt.link_class == k, "n"].sum()) + int(((cls == k) & unass).sum()) == int(counts.get(k, 0)), \
            f"G18 FAILED: class {k} count on the map != the truth table's row sums (+ the unassessable links classed from the edge sense)"
    # G18's ratio requirement holds on every link that REACHES the width test; a link declared near-contiguous or
    # width-not-assessable (D24: no counterfactual band / below the floors) may carry no ratio -- it is listed with its reason
    # (amended 2026-09-28 on run002: E017_035, a link whose counterfactual band holds no new land, has no width to measure)
    missing_ratio = list(e.index[reach & e["squeeze_ratio_obs"].isna()])
    assert not missing_ratio, f"G18 FAILED: squeeze_ratio_obs is null on link(s) that reach the width test: {missing_ratio}"
    no_ratio = e.index[nz & ~reach & e["squeeze_ratio_obs"].isna()]
    reasons = {k: ("contact: no counterfactual band" if pd.isna(e.loc[k, "open_ground_width_med"]) else "contact: below the resolution floor") for k in no_ratio}
    old_top = list(e.index[reach & E & B1 & ~S])                                   # only-viable under the retired rule, not now
    A.rec["g18"] = dict(truth_table=tt.to_dict("records"), old_rule_only_viable_now_last_affordable=old_top,
                        n_only_viable=int(counts.get("both", 0)))
    # ---- G19: the floor's effect (histograms, counts, the halved / doubled diagnostic; asserts) ----
    hist = {c: {f"p{q}": float(np.nanpercentile(e.loc[nz, c], q)) for q in (10, 50, 90)} for c in ("lcp_len_cells", "open_ground_width_med")}
    alt = {}
    for tag, mult in (("halved", 0.5), ("doubled", 2.0)):
        c2 = classify_links(A, floors=(wf * mult, lf * mult), verbose=False)
        alt[tag] = int((c2[nz] != cls[nz]).sum())
    moved = max(alt.values()) / max(int(nz.sum()), 1)
    assert not (front & e["n_branches"].notna()).any(), "G19/G24 FAILED: a front carries a branch decomposition"
    assert not (unass & e["squeezed"]).any(), "G19 FAILED: a contact (width not assessable) is classed squeezed"
    # ---- G24 (D25c, one scale): one geometry and one class per link; fronts B1-forced; strips decomposed; the road flag never classes ----
    assert (e.loc[nz, "link_geometry"].isin(GEOMETRIES)).all() and (cls[nz].isin(CORRIDOR_CLASSES)).all(), "G24 FAILED: a link lacks a geometry or a corridor class"
    assert cls[unass].isin(["securing", "edge"]).all(), "G24 FAILED: a contact carries a class beyond the edge sense"
    strips = e["link_geometry"].eq("strip")
    assert e.loc[strips, "n_branches"].notna().all(), "G24 FAILED: a strip has no branch decomposition"
    cls_toggled = pd.Series([_link_class(bool(a), bool(u), bool(x), bool(y), bool(z)) for a, u, x, y, z in zip(e["is_adjacency"], unass, E, B1, S)], index=e.index)
    assert (cls_toggled == cls).all(), "G24 FAILED: the class depends on the road-crossing flag"   # the flag is not an input; asserted for the record
    xg = pd.crosstab(cls[nz], e.loc[nz, "link_geometry"]).reindex(index=list(CORRIDOR_CLASSES), columns=list(GEOMETRIES), fill_value=0)
    xg.index.name = "link_class"; xg.columns.name = "link_geometry"
    xg.to_csv(A.run_dir / "class_by_geometry.csv")
    # ---- D25c: the front descriptor table (gap, barrier-free width, ratio, lcp_max_cost, road flag, the two areas' sizes) ----
    nc = e.index[front]
    def _unit_km2(u):
        try:
            return float(np.asarray(A.nodes[int(u)][1]).sum()) * A.cell_km2
        except Exception:
            return np.nan
    rep_df = pd.DataFrame([dict(edge_id=k, label_i=e.loc[k, "label_i"], label_j=e.loc[k, "label_j"],
                                gap_km=float(e.loc[k, "centreline_km"]), open_ground_width_med=float(e.loc[k, "open_ground_width_med"]),
                                open_ground_width_km=float(e.loc[k, "open_ground_width_med"]) * A.cell_km,
                                squeeze_ratio_obs=(float(e.loc[k, "squeeze_ratio_obs"]) if pd.notna(e.loc[k, "squeeze_ratio_obs"]) else np.nan),
                                lcp_max_cost=(float(e.loc[k, "lcp_max_cost"]) if pd.notna(e.loc[k, "lcp_max_cost"]) else np.nan),
                                area_i_km2=_unit_km2(e.loc[k, "i"]), area_j_km2=_unit_km2(e.loc[k, "j"]),
                                edge_irreplaceable=bool(e.loc[k, "edge_irreplaceable"]), band_new_km2=float(e.loc[k, "band_new_km2"]))
                           for k in nc]).sort_values("gap_km") if len(nc) else pd.DataFrame()
    if len(rep_df):
        rep_df["road_crossing"] = [bool(e.loc[k, "road_crossing"]) for k in rep_df.edge_id]; rep_df["link_class"] = [cls[k] for k in rep_df.edge_id]
    rep_df.to_csv(A.run_dir / "fronts.csv", index=False, encoding="utf-8-sig")
    # ---- D25b (amended by D25c): corridor area INCLUDES fronts; front area / share are descriptors; the three-way identity ----
    bn = e["band_new_km2"].fillna(0.0)
    intra = e["edge_class"].eq("intra_name")
    backup = (e["in_mst"] == False) & ~e["is_adjacency"] & ~intra
    acct = dict(corridor_area_km2=float(bn[nz & ~intra & ~backup].sum()),
                intra_name_area_km2=float(bn[intra].sum()),
                augmentation_area_km2=float(bn[backup].sum()),
                total_band_area_km2=float(bn[nz | intra].sum()),
                front_area_km2=float(bn[front].sum()))
    acct["front_share"] = (acct["front_area_km2"] / acct["total_band_area_km2"]) if acct["total_band_area_km2"] > 0 else 0.0
    A.band_accounting = acct
    parts_sum = acct["corridor_area_km2"] + acct["intra_name_area_km2"] + acct["augmentation_area_km2"]
    assert abs(parts_sum - acct["total_band_area_km2"]) <= 1e-6 * max(acct["total_band_area_km2"], 1.0), \
        f"G24 FAILED: corridor + intra-name + augmentation ({parts_sum:,.1f}) != total band area ({acct['total_band_area_km2']:,.1f})"
    A.rec["d25c"] = dict(n_by_geometry={g: int((e.loc[nz, "link_geometry"] == g).sum()) for g in GEOMETRIES}, class_by_geometry=xg.to_dict(),
                         n_road_crossing=int(e.loc[nz, "road_crossing"].sum()), **acct)
    fe = pd.DataFrame([dict(floor="registered", width_floor_cells=wf, len_floor_cells=lf, **{k: int(counts.get(k, 0)) for k in LINK_CLASS_LABEL if k != "adjacency"})]
                      + [dict(floor=tag, width_floor_cells=wf * m, len_floor_cells=lf * m,
                              **{k: int((classify_links(A, floors=(wf * m, lf * m), verbose=False)[nz] == k).sum()) for k in LINK_CLASS_LABEL if k != "adjacency"})
                         for tag, m in (("halved", 0.5), ("doubled", 2.0))])
    fe.to_csv(A.run_dir / "floor_effect.csv", index=False)
    A.rec["g19"] = dict(hist=hist, n_width_not_assessable=int(unass.sum()), n_near_contiguous=int(near.sum()), moved_halved=alt["halved"],
                        moved_doubled=alt["doubled"], moved_frac_max=float(moved))
    (A.run_dir / "run_config.json").write_text(json.dumps(A.rec, indent=2, ensure_ascii=False))
    if verbose:
        print("link classes (D23 on one scale, D25c; the single source):  " + " · ".join(f"{k} {int(counts.get(k, 0))}" for k in CORRIDOR_CLASSES))
        print("  G24 OK -- class x geometry (-> class_by_geometry.csv):\n" + "\n".join("      " + l for l in xg.to_string().splitlines()))
        print(f"  D25c: {len(nc)} front(s) -> fronts.csv (gap, barrier-free width, ratio, lcp_max_cost, road flag, the two areas' sizes); "
              f"{int(e.loc[nz, 'road_crossing'].sum())} road crossing(s) flagged (never classed)")
        print(f"  D25b (amended): corridor {acct['corridor_area_km2']:,.0f} (fronts INCLUDED: {acct['front_area_km2']:,.0f} km² = {100*acct['front_share']:.0f}% of the band) "
              f"+ intra-name {acct['intra_name_area_km2']:,.0f} + augmentation {acct['augmentation_area_km2']:,.0f} = {acct['total_band_area_km2']:,.0f} km²")
        print(f"  G18 OK: eight-cell table -> class_truth_table.csv; {len(old_top)} link(s) only-viable under the retired rule but not "
              f"now (E and one branch, land NOT narrowing): {old_top or 'none'}" + ("  -> the 06 example-regeneration rule FIRES (post-pin class change)" if old_top else ""))
        if reasons:
            print(f"  G18: {len(reasons)} non-zero-cost link(s) carry no width ratio, each outside the width test: " + ", ".join(f"{k} ({v})" for k, v in reasons.items()))
        print(f"  G19 OK: {int(unass.sum())} width-not-assessable, {int(near.sum())} near-contiguous; lcp_len_cells p10/50/90 "
              f"{hist['lcp_len_cells']['p10']:.0f}/{hist['lcp_len_cells']['p50']:.0f}/{hist['lcp_len_cells']['p90']:.0f}, open_ground_width_med "
              f"{hist['open_ground_width_med']['p10']:.1f}/{hist['open_ground_width_med']['p50']:.1f}/{hist['open_ground_width_med']['p90']:.1f}; "
              f"floor halved moves {alt['halved']}, doubled moves {alt['doubled']} of {int(nz.sum())} links"
              + (f"  -> more than 10% move: the floor is DISCUSSED for this run, not changed" if moved > 0.10 else ""))
    return A


# ================= D17 -- the squeezed class (counterfactual band) =================
def _cross_sections(shape, band_idx, path, n_pos=50, exclude=None):
    """D28: width along a route. Every band cell (optionally excluding `exclude`, a flat boolean such as node land) is
    allocated to its nearest least-cost-path cell (distance transform on the band's bounding window); the cell count per path
    cell is the cross-section there (cells; x cell size = km); the profile is binned to n_pos fractional positions along the
    path. Returns n_pos widths (NaN where a bin holds no path cell)."""
    if path is None or len(path) < 2 or band_idx is None or len(band_idx) == 0:
        return np.full(n_pos, np.nan)
    band_idx = np.asarray(band_idx, dtype=np.int64)
    if exclude is not None:
        band_idx = band_idx[~np.asarray(exclude)[band_idx]]
    if len(band_idx) == 0:
        return np.full(n_pos, np.nan)
    rr, cc = np.divmod(band_idx, shape[1]); pr, pc = path[:, 0].astype(np.int64), path[:, 1].astype(np.int64)
    r0, r1 = int(min(rr.min(), pr.min())), int(max(rr.max(), pr.max())); c0, c1 = int(min(cc.min(), pc.min())), int(max(cc.max(), pc.max()))
    H, W = r1 - r0 + 1, c1 - c0 + 1
    bg = np.ones((H, W), bool); bg[pr - r0, pc - c0] = False                         # zeros at the path cells
    _, (ir, ic) = ndimage.distance_transform_edt(bg, return_indices=True)
    order = np.full((H, W), -1, np.int64); order[pr - r0, pc - c0] = np.arange(len(path))
    pos = order[ir[rr - r0, cc - c0], ic[rr - r0, cc - c0]]
    counts = np.bincount(pos[pos >= 0], minlength=len(path)).astype(float)
    t = np.arange(len(path)) / max(len(path) - 1, 1)
    bins = np.minimum((t * n_pos).astype(int), n_pos - 1)
    s = np.bincount(bins, weights=counts, minlength=n_pos); n = np.bincount(bins, minlength=n_pos)
    width = np.full(n_pos, np.nan); ok = n > 0; width[ok] = s[ok] / n[ok]
    return width


def counterfactual_squeeze(A, cache=True, tol=0.02):
    """D17 (H8 closed 2026-09-03): per link, how wide is the real band relative to the band the
    SAME link would have on a surface with nothing constraining it?

    The counterfactual surface sets every cost class >= squeeze_cf_min_cost to 1 (all barriers
    -- water/ice, roads, converted land -- become intact ground); CWD is recomputed once per
    seed part on it (cached under cwd_cache/<sha>_cf), unit fields derived exactly as in
    cost_distances, and every baseline edge is banded at the SAME cwd_cutoff_abs. Then
        squeeze_ratio_obs = width_new_km / width_cf_km      (width = NEW-land band area / own
                                                            least-cost route length)
        squeezed          = squeeze_ratio_obs < squeeze_ratio   (non-adjacency edges only)
    Why this and not the analytic ellipse index (M4.6, kept as `squeeze_idx`): no straight-link
    assumption, and both bands are clipped by the same study-window cutline, so the boundary
    artefact cancels in the ratio. G13: band_cf_km2 >= band_new_km2 (within `tol`) for every
    edge -- the counterfactual can only widen a band. Writes the counterfactual band polygons
    (bands_counterfactual.gpkg, the M3 'natural width' outline) and the D17 columns into A.edges;
    write_run/finish carry them into corridor_edges.csv. Records the constants in run_config.
    """
    # A.cfg is the run's frozen run_config.json; runs created before the addendum constants
    # existed (v2_run002, 2026-08-27) don't carry them, so fall back to config.py and PIN the
    # values into run_config below -- the run dir stays the record of what was actually used.
    live = config.CORRIDORS[A.key]
    missing = [k for k in ("squeeze_cf_min_cost", "squeeze_ratio") if k not in A.cfg]
    if missing:
        print(f"  D17 constants {missing} not in this run's run_config (run predates them) -- "
              f"taken from config.CORRIDORS[{A.key!r}] and pinned into run_config.json")
    thr = float(A.cfg.get("squeeze_cf_min_cost", live["squeeze_cf_min_cost"]))
    rmax = float(A.cfg.get("squeeze_ratio", live["squeeze_ratio"]))
    A.cfg["squeeze_cf_min_cost"], A.cfg["squeeze_ratio"] = thr, rmax
    cf_cost = np.where(A.cost >= thr, 1.0, A.cost).astype("float32")
    res_cf = np.where(A.pu, cf_cost, np.inf)
    n_changed = int(((A.cost >= thr) & A.pu).sum())
    print(f"D17 counterfactual: {n_changed:,} cells ({100*n_changed/A.pu.sum():.1f}% of routable) "
          f"with cost >= {thr:g} set to 1; banding every edge at cutoff {A.cutoff:g}")

    # ---- CWD on the counterfactual surface (per part -> unit min-fields), cached ------------
    A_cf = _NS(cost=cf_cost, node_union=A.node_union, parts=A.parts, names=A.names, nodes=A.nodes,
               seed_names=getattr(A, "seed_names", None), seed_n_nodes=getattr(A, "seed_n_nodes", None))   # contracted runs: v2's cf identity
    cache_dir = None
    if cache:
        gdir = config.PROJECT_DIR / pathlib.Path(A.cfg["grid"]["dir"])
        compact = bool(A.cfg.get("cwd_compact", False))          # wolverine: routable cells only (M5.1), as the real set
        sha_cf = _resistance_sha(A_cf)
        cache_dir = gdir / "cwd_cache" / f"{sha_cf}_cf{'_c' if compact else ''}"
        hit = cache_dir.exists() and len(list(cache_dir.glob("part_*.npy"))) == len(A.parts)
        print(f"  counterfactual CWD from {len(A.parts)} seed parts "
              f"({'cache HIT' if hit else 'computing -- expect ~the cost_distances runtime'}: "
              f"{cache_dir.name})")
    else:
        compact, sha_cf = False, None
    pu_cf = A.pu if compact else None
    cwd_parts_cf, mcp_cf = _cwd_all(A, res_cf, [m for _, m in A.parts], cache_dir, prefix="part", pu=pu_cf)
    if cache:
        upaths = []
        for u in range(len(A.nodes)):
            pidx = A.unit_parts[u]
            if len(pidx) == 1:
                upaths.append(cwd_parts_cf.paths[pidx[0]])
            else:
                p = cache_dir / _unit_fname(A, u)
                if not p.exists():
                    rd = (cwd_parts_cf.compact if compact else cwd_parts_cf.__getitem__)
                    fld = np.asarray(rd(pidx[0]), dtype="float32").copy()
                    for pi in pidx[1:]:
                        np.minimum(fld, np.asarray(rd(pi), dtype="float32"), out=fld)
                    np.save(p, fld)
                upaths.append(p)
        cwd_cf = _CwdCache(upaths, pu_cf)
    else:
        cwd_cf = []
        for u in range(len(A.nodes)):
            pidx = A.unit_parts[u]
            fld = np.asarray(cwd_parts_cf[pidx[0]], dtype="float64")
            for pi in pidx[1:]:
                fld = np.minimum(fld, np.asarray(cwd_parts_cf[pi], dtype="float64"))
            cwd_cf.append(fld)

    # ---- bands at the same cutoff: unit edges on unit fields, locked edges on part fields ---
    unit_rows = A.edges[A.edges["edge_class"] != "intra_name"]
    # wolverine band store (M5.2): the counterfactual bands under their own tag, early-stop tracebacks -- absent in the north
    cf_tag = f"cf_{sha_cf}" if (sha_cf and getattr(A, "band_memo", None) is not None) else None
    bands_cf, _, paths_cf, meta_cf = edge_bands(A, cwd_cf, mcp_cf, unit_rows, A.cutoff, "abs",
                                                want_slack=False, tag=cf_tag)
    lk_rows = A.edges[A.edges["edge_class"] == "intra_name"]
    if len(lk_rows):
        b2, _, p2, m2 = edge_bands(_NS(nodes=A.parts, shape=A.shape), cwd_parts_cf, mcp_cf,
                                   lk_rows, A.cutoff, "abs", want_slack=False)
        bands_cf.update(b2); paths_cf.update(p2); meta_cf.update(m2)

    # ---- WIDTH, not area (measured 2026-09-08 on v2_run002): relaxing barriers also SHORTENS
    # routes that detoured around water/ice, and band area ∝ length × width -- on 6 links the
    # counterfactual band was SMALLER in area while plainly wider per km. D17's concept is
    # narrowing, so the ratio is width = band area / own route length (the implementable
    # analogue of the spec's cross-sectional width), each band over its OWN least-cost route.
    flat_nodes = A.node_union.ravel()
    new_km2, cf_km2, cf_len = {}, {}, {}
    for eid in A.edges.index:
        idx = A.bands.get(eid, np.empty(0, np.int32))
        new_km2[eid] = float((~flat_nodes[idx]).sum()) * A.cell_km2
        idc = bands_cf.get(eid, np.empty(0, np.int32))
        cf_km2[eid] = float((~flat_nodes[idc]).sum()) * A.cell_km2
        cf_len[eid] = float(meta_cf.get(eid, {}).get("centreline_cells", 0)) * A.cell_km
    A.edges["band_new_km2"] = pd.Series(new_km2)
    A.edges["band_cf_km2"] = pd.Series(cf_km2)
    A.edges["centreline_cf_km"] = pd.Series(cf_len)
    # (the 2 km length floor that used to blank short links' widths is gone: D24's resolution floor, below, governs which
    # links are width-ASSESSABLE; the ratio itself is computed wherever both bands hold new land, so G18 can require it)
    L_new = A.edges["centreline_km"].where(A.edges["centreline_km"] > 0)
    L_cf = A.edges["centreline_cf_km"].where(A.edges["centreline_cf_km"] > 0)
    A.edges["width_new_km"] = (A.edges["band_new_km2"] / L_new).round(3)
    A.edges["width_cf_km"] = (A.edges["band_cf_km2"] / L_cf).round(3)
    nz = (A.edges["cost"] > 0) & (~A.edges["is_adjacency"])
    eligible = nz & A.edges["width_new_km"].notna() & (A.edges["width_cf_km"] > 0)
    A.edges["squeeze_ratio_obs"] = np.where(
        eligible, A.edges["width_new_km"] / A.edges["width_cf_km"].replace(0, np.nan), np.nan)

    # ---- D24 (2026-09-28): the width test's RESOLUTION FLOOR, pre-registered and pinned into run_config BEFORE any class
    # count is read (tuning prohibition). open_ground_width_med = the counterfactual band's median cross-section (cells);
    # lcp_len_cells = the least-cost path length. Below either floor the width test is NOT ASSESSABLE: such links are classed
    # from the edge sense alone (classify_links), never 'narrowing' or 'only viable' from two-cell arithmetic.
    # ---- D25: NEAR-CONTIGUOUS -- a path shorter than the band's barrier-free width is a blob, not a route: no branch
    # decomposition, no width class; reported with the edge sense and whether a cost-1000 barrier sits on the path.
    for k in ("width_floor_cells", "len_floor_cells"):
        if k not in A.cfg:
            A.cfg[k] = A.rec["cfg"][k] = live[k]
            print(f"  D24 constant {k} not in this run's run_config -- taken from config.py ({live[k]}) and pinned")
    (A.run_dir / "run_config.json").write_text(json.dumps(A.rec, indent=2, ensure_ascii=False))
    wfloor, lfloor = float(A.cfg["width_floor_cells"]), float(A.cfg["len_floor_cells"])
    N_POS = 50
    p10, p50, ppos, ogw = {}, {}, {}, {}
    pmax, x1000 = {}, {}
    for eid in A.edges.index[nz]:
        w_r = _cross_sections(A.shape, A.bands.get(eid, np.empty(0, np.int32)), A.paths.get(eid), N_POS, exclude=flat_nodes)
        w_c = _cross_sections(A.shape, bands_cf.get(eid, np.empty(0, np.int32)), paths_cf.get(eid), N_POS, exclude=flat_nodes)
        ogw[eid] = float(np.nanmedian(w_c)) if np.isfinite(w_c).any() else np.nan            # cells: the barrier-free median width
        pth = A.paths.get(eid)
        if pth is not None and len(pth):
            pc = A.cost[pth[:, 0], pth[:, 1]]; pmax[eid] = float(np.nanmax(pc)); x1000[eid] = bool(pmax[eid] >= 1000)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where((w_c > 0) & np.isfinite(w_c) & np.isfinite(w_r), w_r / w_c, np.nan)
        ok = np.isfinite(ratio)
        if ok.sum() < 5:
            continue
        p10[eid] = float(np.nanpercentile(ratio, 10)); p50[eid] = float(np.nanpercentile(ratio, 50))
        ppos[eid] = float(np.nanargmin(np.where(ok, ratio, np.inf)) / max(N_POS - 1, 1))
    A.edges["open_ground_width_med"] = pd.Series(ogw).reindex(A.edges.index)
    A.edges["lcp_len_cells"] = A.edges["centreline_cells"].astype(float)
    A.edges["lcp_max_cost"] = pd.Series(pmax).reindex(A.edges.index)                       # D25a: the maximum cost class on the least-cost path
    A.edges["crosses_cost_1000"] = pd.Series(x1000).reindex(A.edges.index).fillna(False).astype(bool)
    # D25c (2026-09-29, Ethan's principle: nothing unprotected is taken as given): the front trigger is a GEOMETRY DESCRIPTOR, not a
    # class. link_geometry = "contact" if the width test is not assessable (D24: barrier-free width below width_floor_cells, or
    # absent, or path shorter than len_floor_cells); "front" if the path is shorter than the barrier-free width (the retired D25
    # trigger); "strip" otherwise. Fronts and strips are classed on ONE pressure scale (classify_links); contacts by the edge
    # sense only. `near_contiguous` is kept as a column (= front) for table continuity with the 2026-09-28 runs.
    ogw = A.edges["open_ground_width_med"]
    A.edges["width_not_assessable"] = (nz & (ogw.isna() | (ogw < wfloor) | (A.edges["lcp_len_cells"] < lfloor))).astype(bool)
    front = (nz & ~A.edges["width_not_assessable"] & (A.edges["lcp_len_cells"] < ogw)).fillna(False).astype(bool)
    A.edges["near_contiguous"] = front
    geom = pd.Series("", index=A.edges.index, dtype=object)
    geom[nz] = "strip"; geom[front] = "front"; geom[A.edges["width_not_assessable"]] = "contact"
    A.edges["link_geometry"] = geom
    A.edges["road_crossing"] = (A.edges["lcp_max_cost"] == 10)                   # flagged, never classed (D25c)
    assessable = eligible & ~A.edges["width_not_assessable"]
    A.edges["squeezed"] = assessable & (A.edges["squeeze_ratio_obs"] < rmax)      # provisional: classify_links (after the branches) is the record
    print(f"  D24/D25c geometry: {int((geom == 'strip').sum())} strips, {int(front.sum())} fronts (path shorter than the barrier-free width; "
          f"classed on width alone), {int(A.edges['width_not_assessable'].sum())} contacts (width test not assessable: floors {wfloor:g} cells wide / "
          f"{lfloor:g} cells long; edge sense only) of {int(nz.sum())} non-zero-cost; road crossings flagged on {int(A.edges['road_crossing'].sum())}")
    # ---- D28 (2026-09-28): pinch-aware width -- width_ratio_p10 / p50 = quantiles of the per-position real/counterfactual
    # cross-section ratio, pinch_pos = the fractional position of the minimum. REPORTED, NOT CLASSED; strips and fronts (D25c).
    for d in (p10, p50, ppos):
        for eid in [k for k in d if not bool(assessable.get(k, False))]:
            d.pop(eid)
    A.edges["width_ratio_p10"] = pd.Series(p10).reindex(A.edges.index)
    A.edges["width_ratio_p50"] = pd.Series(p50).reindex(A.edges.index)
    A.edges["pinch_pos"] = pd.Series(ppos).reindex(A.edges.index)
    # G22 (width): the tenth percentile cannot exceed the link's width ratio (5% tolerance: squeeze_ratio_obs is the AREA/length
    # ratio, the p10 a quantile of per-position ratios; a violation beyond that means the two constructions disagree -- report)
    viol = [e for e in p10 if pd.notna(A.edges.loc[e, "squeeze_ratio_obs"]) and p10[e] > 1.05 * float(A.edges.loc[e, "squeeze_ratio_obs"])]
    assert not viol, (f"G22 FAILED: width_ratio_p10 exceeds squeeze_ratio_obs on {viol} -- the per-position cross-sections and the "
                      f"area/length ratio disagree; inspect before shipping the width columns")
    n_p = len(p10); pinched = sorted(p10, key=p10.get)[:5]
    print(f"  G22 OK: width_ratio_p10 <= squeeze_ratio_obs on all {n_p} assessable edges | narrowest pinches: "
          + ", ".join(f"{_short_node_name(A.edges.loc[e,'label_i'],12)}↔{_short_node_name(A.edges.loc[e,'label_j'],12)} p10 {p10[e]:.2f} @ {ppos[e]:.2f}" for e in pinched))

    # ---- G13 (restated 2026-09-08, second time -- measured on v2_run002) --------------------
    # The counterfactual band bounds the real band in NEITHER direction. Two legitimate ways it
    # can be narrower per km: (1) relaxing barriers SHORTENS a detouring route; (2) barriers on
    # the real surface EQUALISE two routes into a near-tie (a braided, wide band, e.g. the two
    # Liard<->Nahanni branches), and relaxation breaks the tie so the band collapses to one
    # ribbon. Neither is a squeeze; both are reported. The one true relaxation invariant is on
    # the OPTIMUM: lowering costs can never make the least-cost route costlier -- lcp_cf <=
    # lcp_real for every banded edge. That is the gate.
    lcp_real = pd.Series({e: A.band_meta[e]["lcp"] for e in A.edges.index if e in A.band_meta})
    lcp_cf = pd.Series({e: meta_cf[e]["lcp"] for e in A.edges.index if e in meta_cf})
    both = lcp_real.index.intersection(lcp_cf.index)
    bad = [e for e in both if lcp_cf[e] > lcp_real[e] * (1 + 1e-6) + 1e-6]
    assert not bad, (
        f"G13 FAILED: the counterfactual least-cost route is COSTLIER than the real one on {bad} "
        f"-- impossible under a cost relaxation; suspect the cache key or the cutoff.")
    A.edges["lcp_real"] = lcp_real.reindex(A.edges.index)
    A.edges["lcp_cf"] = lcp_cf.reindex(A.edges.index)
    narrower = A.edges.index[eligible & (A.edges["width_cf_km"] < A.edges["width_new_km"] * (1 - tol))]
    if len(narrower):
        print(f"  G13 note: {len(narrower)} link(s) have a NARROWER counterfactual (shorter route "
              f"and/or a real-surface near-tie broken by relaxation) -- reported, not squeezed: "
              + ", ".join(f"{e} w {A.edges.loc[e,'width_new_km']:.1f}->{A.edges.loc[e,'width_cf_km']:.1f} km, "
                          f"L {A.edges.loc[e,'centreline_km']:.0f}->{A.edges.loc[e,'centreline_cf_km']:.0f} km"
                          for e in narrower))
    n_sq = int(A.edges["squeezed"].sum())
    print(f"  G13 OK: counterfactual optimum <= real optimum on all {len(both)} banded edges "
          f"(relaxation invariant); {int(eligible.sum())} edges eligible for the width ratio")
    print(f"  SQUEEZED (ratio < {rmax:g}): {n_sq} links -- "
          + ", ".join(f"{_short_node_name(r.label_i, 14)}↔{_short_node_name(r.label_j, 14)} "
                      f"{r.squeeze_ratio_obs:.2f}"
                      for r in A.edges[A.edges["squeezed"]].sort_values("squeeze_ratio_obs")
                      .itertuples()))

    # ---- outputs: counterfactual band polygons (M3 outline) + constants into run_config ------
    rows = []
    for eid, idc in bands_cf.items():
        m = np.zeros(A.shape[0] * A.shape[1], bool); m[idc] = True
        m = m.reshape(A.shape) & ~A.node_union
        if not m.any():
            continue
        polys = [_shape(s) for s, v in shapes(m.astype("uint8"), mask=m, transform=A.transform)
                 if v == 1]
        rows.append(dict(edge_id=eid, band_cf_km2=cf_km2[eid], band_new_km2=new_km2[eid],
                         centreline_km=float(A.edges.loc[eid, "centreline_km"]),
                         centreline_cf_km=cf_len[eid],
                         width_new_km=(float(A.edges.loc[eid, "width_new_km"])
                                       if pd.notna(A.edges.loc[eid, "width_new_km"]) else None),
                         width_cf_km=(float(A.edges.loc[eid, "width_cf_km"])
                                      if pd.notna(A.edges.loc[eid, "width_cf_km"]) else None),
                         squeeze_ratio_obs=float(A.edges.loc[eid, "squeeze_ratio_obs"])
                         if pd.notna(A.edges.loc[eid, "squeeze_ratio_obs"]) else None,
                         geometry=gpd.GeoSeries(polys, crs=A.crs).union_all()))
    gpd.GeoDataFrame(rows, crs=A.crs).to_file(A.run_dir / "bands_counterfactual.gpkg",
                                              driver="GPKG")
    A.rec.setdefault("d17", {}).update(dict(squeeze_ratio=rmax, squeeze_cf_min_cost=thr,
                                            n_squeezed=n_sq, cells_relaxed=n_changed))
    A.rec["cfg"]["squeeze_ratio"] = rmax; A.rec["cfg"]["squeeze_cf_min_cost"] = thr
    (A.run_dir / "run_config.json").write_text(json.dumps(A.rec, indent=2, ensure_ascii=False))
    print(f"  wrote bands_counterfactual.gpkg ({len(rows)} edges) + D17 constants into run_config")
    return A


# ================= per-branch values table (D13/D14) =================
def _to_audit_frac(A, mask):
    """A 300 m boolean mask -> COVERAGE FRACTION per 1 km audit cell (0..1).

    The fractional crossing used for BRANCH profiling (M6.5): route branches at 0.5x cutoff are
    ribbons ~1 km wide -- all boundary -- and the fixed 0.5 majority rule systematically
    inflated 9 of 41 of them by 5-17% (the G11 failure, 2026-08-27). Weighting by actual
    coverage is exactly area-conserving by construction. The corridor-LEVEL profile keeps the
    fixed 0.5 majority (_to_audit): its masks are tens of km wide, and G5 anchors that path to
    v1."""
    src = A.template.copy(data=mask.astype("float32"))
    src.rio.write_nodata(None, inplace=True)
    frac = src.rio.reproject_match(A.audit_template, resampling=Resampling.average).values
    return np.nan_to_num(frac, nan=0.0).astype("float64")


def _profile_frac(P, w):
    """results_core.mask_profile generalised to FRACTIONAL cell weights w (0..1).

    With binary weights this reduces EXACTLY to mask_profile (asserted by the equivalence
    test), so D13's "same column specification as the Y2Y-wide alternatives table" holds: same
    estimands, same normalisations, same full-Y2Y denominators. The Y2Y-wide tables' masks are
    native 1 km cells (weights always 0/1 there), so the two products remain computed
    identically wherever both exist.
    """
    def wmean(a):
        fin = np.isfinite(a)
        d = float(np.sum(w[fin]))
        return float(np.nansum(np.where(fin, a, 0.0) * w) / d) if d > 0 else np.nan

    prof = [wmean(P.cont_stack[k]) for k in range(len(P.cont))]
    efg_d = sum(float(np.sum(w[np.isfinite(P.efg_stack[j])])) for j in range(len(P.efg)))
    prof.append(float(np.nansum(P.efg_stack * w[None, :, :]) / efg_d) if efg_d > 0 else np.nan)

    contrib = [100.0 * float(np.nansum(P.cont_raw[k] * w)) / P.cont_region[k]
               for k in range(len(P.cont))]
    contrib.append(100.0 * float(np.nanmean(
        [np.nansum(P.efg_raw[j] * w) / P.efg_region[j] for j in range(len(P.efg))])))
    area = float(np.sum(w)) * P.cell_km2
    eff = [x / area * 1000.0 for x in contrib]

    raw = []
    for k, name in enumerate(P.cont):
        if rc.RAW_SPEC[name][2] == "tonnes":
            raw.append(float(np.nansum(P.cont_raw[k] * w) * P.cell_ha))
        else:
            raw.append(wmean(P.cont_raw[k]))
    raw.append(int(np.sum([bool(np.any((P.efg_raw[j] > 0) & (w > 0)))
                           for j in range(len(P.efg))])))
    return prof, contrib, eff, raw


def alternatives_table(A):
    """Step 4c -- the per-branch values table, SAME column specification as the Y2Y-wide
    alternatives (consequences) tables: display names, units and normalisations are IMPORTED from
    results_core.RAW_SPEC / mask_profile, never redefined here (D13). Row unit differs -- edge x
    route branch, not a solution cluster -- and the caption says so.

    D14: Carroll 2018 current-flow centrality enters ONLY as the audit column carroll2018_pctl
    (branch mean percentile vs the routable-area percentile baseline, carroll_ref). H6-guarded:
    an absent layer logs the gap and the table ships without the column, rather than failing.
    """
    assert getattr(A, "branches", None) is not None and len(A.branches), \
        "run cc.route_branches(A) first"
    P = A.profile["P"] if getattr(A, "profile", None) else _profile_stacks(A)

    # routable area on the audit grid = the Carroll percentile reference (carroll_ref)
    routable_1k = _to_audit(A, A.pu)
    carroll_k = P.cont.index("climate_corridors") if "climate_corridors" in P.cont else None
    if carroll_k is None:
        print("H6: climate_corridors not in the audit stack -- carroll2018_pctl SKIPPED "
              "(logged, not fatal)")
        pct_grid = None
    else:
        raw = P.cont_raw[carroll_k]
        ref = np.sort(raw[routable_1k & np.isfinite(raw)])
        # weighted mean percentile (percentile transform over the ROUTABLE audit area)
        def _pctl(vals, wts):
            fin = np.isfinite(vals) & (wts > 0)
            if not fin.any():
                return np.nan
            p = 100.0 * np.searchsorted(ref, vals[fin], side="right") / ref.size
            return float(np.average(p, weights=wts[fin]))
        pct_grid = _pctl

    rows, g11 = [], []
    for r in A.branches.itertuples():
        m = np.zeros(A.shape[0] * A.shape[1], bool)
        m[A.branch_idx[r.branch]] = True
        m = m.reshape(A.shape)
        w = _to_audit_frac(A, m)                       # fractional crossing (M6.5)
        a300 = r.cells * A.cell_km2
        a1k = float(w.sum()) * P.cell_km2
        rel = abs(a1k - a300) / max(a300, 1e-9)
        g11.append((r.branch_id, a300, a1k, rel))
        if not (w > 0).any():
            print(f"  {r.branch_id}: no overlap with the 1 km audit grid -- values row skipped")
            continue
        prof, contrib, eff, rawv = _profile_frac(P, w)
        e = A.edges.loc[r.edge_id]
        row = dict(branch_id=r.branch_id, edge_id=r.edge_id, edge_class=r.edge_class,
                   label_i=e["label_i"], label_j=e["label_j"],
                   area_km2=round(a300, 1), area_km2_audit=round(a1k, 1),
                   min_slack=r.min_slack, mean_slack=r.mean_slack,
                   n_branches=int(e.get("n_branches", 1)),
                   route_irreplaceable=bool(e.get("route_irreplaceable", False)),
                   edge_irreplaceable=bool(e.get("irreplaceable", False)),
                   edge_cost=float(e["cost"]), ecfb_raw=e.get("ecfb_raw"))
        units = [rc.RAW_SPEC[n][1] or "index" for n in P.cont] \
            + [f"groups present (of {len(P.efg)})"]
        dps = [rc.RAW_SPEC[n][3] for n in P.cont] + [0]
        for j, ax in enumerate(P.axes_labels):
            row[f"{ax} | richness"] = round(prof[j], 3)
            row[f"{ax} | contribution %"] = round(contrib[j], 4)
            row[f"{ax} | efficiency"] = round(eff[j], 4)
            row[f"{ax} | raw [{units[j]}]"] = round(float(rawv[j]), dps[j])
        if pct_grid is not None:
            row["carroll2018_pctl"] = round(pct_grid(P.cont_raw[carroll_k], w), 1)
            row["carroll2018_pctl_ref"] = 50.0       # routable-area baseline, by construction
        rows.append(row)

    # G11 -- audit-crossing discrepancy <= 5% for branches >= 50 km²; ALL discrepancies logged.
    print("G11 audit-crossing check (300 m -> 1 km):")
    bad = []
    for bid, a300, a1k, rel in g11:
        flag = "OK " if (a300 < 50 or rel <= 0.05) else "FAIL"
        if flag == "FAIL":
            bad.append(bid)
        print(f"  {flag} {bid:24s} {a300:8,.0f} km² -> {a1k:8,.0f} km²  ({rel:+.1%})")
    assert not bad, (f"G11 FAILED for {bad}: audit-grid area drifts > 5% on branches >= 50 km² -- "
                     f"contribution/efficiency would be computed on a different footprint than "
                     f"the map shows.")

    df = pd.DataFrame(rows)
    dst = A.run_dir
    df.to_csv(dst / "alternatives_branches.csv", index=False, encoding="utf-8-sig")
    caption = ("Row unit is edge x route branch, not a solution cluster; columns follow the "
               "Y2Y-wide alternatives table for readability only. Branch masks cross 300 m -> "
               "1 km by FRACTIONAL cover weighting (exactly area-conserving; reduces to the "
               "Y2Y-wide mask_profile on binary masks). carroll2018_pctl is an audit column "
               "(D14): RCP 8.5 late-century only, shares anthropogenic signal with the cost "
               "surface; no routing is climate-informed.")
    (dst / "alternatives_branches.meta.json").write_text(json.dumps(
        dict(caption=caption, row_unit="edge x route branch",
             column_spec="results_core.RAW_SPEC / mask_profile estimands, fractional-weight "
                         "generalisation (M6.5; exact on binary masks)",
             crossing="fractional cover (0.5-majority retained for corridor-level profile)",
             carroll_ref=A.cfg["carroll_ref"]), indent=2))
    print(f"  wrote alternatives_branches.csv (+ .meta.json caption) -- {len(df)} branch rows")
    A.alternatives = df
    return A


def tiebreak(A):
    """Step 4d -- for edges with n_branches >= 2, rank branches by the audit columns, with both
    the connectivity-equivalence evidence (slack difference) and the values evidence. RANKING
    ONLY: no automated "recommended" flag -- the recommendation is a human read of the table."""
    df = getattr(A, "alternatives", None)
    assert df is not None, "run cc.alternatives_table(A) first"
    multi = df[df["n_branches"] >= 2].copy()
    if not len(multi):
        print("tiebreak: no edges with >= 2 branches -- nothing to write")
        return A
    contrib_cols = [c for c in df.columns if c.endswith("| contribution %")]
    multi["slack_delta_vs_best"] = multi.groupby("edge_id")["min_slack"].transform(
        lambda s: s - s.min())
    multi["mean_contrib_rank"] = (multi.groupby("edge_id")[contrib_cols]
                                  .rank(ascending=False).mean(axis=1).round(2))
    cols = (["edge_id", "branch_id", "area_km2", "min_slack", "slack_delta_vs_best",
             "mean_contrib_rank"] + contrib_cols
            + (["carroll2018_pctl"] if "carroll2018_pctl" in df.columns else []))
    out = multi[cols].sort_values(["edge_id", "mean_contrib_rank"])
    out.to_csv(A.run_dir / "tiebreak.csv", index=False, encoding="utf-8-sig")
    print(f"tiebreak.csv: {len(out)} branch rows over {out.edge_id.nunique()} edges with "
          f"alternatives (ranking only; recommendation is a human read)")
    return A


# ================= step 0a -- part split + multipart review (D16) =================
def node_parts(key="north", force=False):
    """Step 0a: rasterize the names at 300 m, split into parts, write node_parts.csv/.gpkg and
    the PROPOSED multipart_review.csv into the git-tracked audit_objects dir.

    Standalone (no run dir): runs BEFORE any run exists, in notebook 01. The analysis proposes a
    treatment per multipart name from decision rules 1-4 (spec step 0a) with the evidence beside
    it; H7 is then a CONFIRMATION -- the human edits `proposed` where the rules got it wrong and
    signs the `# reviewed_by:` line. Refuses to overwrite an already-SIGNED review unless
    force=True (re-running 0a must not silently discard a human's edits).
    """
    cfg, cost_path = resolve(key, require_cutoff=False)
    audit_dir = pathlib.Path(cfg["audit_objects_dir"])
    audit_dir.mkdir(parents=True, exist_ok=True)
    review_path = audit_dir / "multipart_review.csv"
    if _review_signed(review_path) and not force:
        raise FileExistsError(
            f"{review_path} is already SIGNED. Re-running step 0a would discard the human "
            f"review -- pass force=True only if that is intended (H7 must then re-sign).")

    A = _grid_nodes(cfg, cost_path)
    A.cfg = cfg
    part_min = max(1, int(round(cfg["part_min_km2"] / A.cell_km2)))
    res = np.where(A.pu, A.cost, np.inf)

    # ---- node_parts.csv/.gpkg: every name, every component ---------------------------
    prows, polys = [], []
    per_name = {}
    for (lbl, mask), kind in zip(A.names_raw, A.kinds_raw):
        comps, seeds = _split_parts(mask, part_min)
        per_name[lbl] = (comps, seeds, kind)
        for k, cm in enumerate(comps, 1):
            cells = int(cm.sum())
            prows.append(dict(name_label=lbl, kind=kind, part_id=k,
                              area_km2=round(cells * A.cell_km2, 1),
                              is_seed=cells >= part_min))
            geom = [_shape(s) for s, v in shapes(cm.astype("uint8"), mask=cm,
                                                 transform=A.transform) if v == 1]
            polys.append(dict(name_label=lbl, part_id=k, is_seed=cells >= part_min,
                              area_km2=round(cells * A.cell_km2, 1),
                              geometry=gpd.GeoSeries(geom, crs=A.crs).union_all()))
    pd.DataFrame(prows).to_csv(audit_dir / "node_parts.csv", index=False, encoding="utf-8-sig")
    gpd.GeoDataFrame(polys, crs=A.crs).to_file(audit_dir / "node_parts.gpkg", driver="GPKG")
    multi = {lbl: v for lbl, v in per_name.items() if len(v[1]) > 1}
    print(f"node_parts: {len(per_name)} names -> {len(prows)} components, "
          f"{sum(r['is_seed'] for r in prows)} seed parts | {len(multi)} multipart names to review")
    print(f"  wrote node_parts.csv, node_parts.gpkg -> {audit_dir.relative_to(config.PROJECT_DIR)}")

    # ---- evidence + proposed treatment per multipart name ----------------------------
    mcp = MCP_Geometric(res)
    max_cost = max(cfg["resistance"]["expect_classes"])
    multisite = cfg["multisite_designations"]
    link_km = cfg["multipart_link_km"]
    name_masks = {lbl: m for (lbl, m), _ in zip(A.names_raw, A.kinds_raw)}

    rrows = []
    for lbl, (comps, seeds, kind) in multi.items():
        areas = sorted((round(int(m.sum()) * A.cell_km2, 1) for m in seeds), reverse=True)
        desig = _name_designation(lbl, kind, A.desig, multisite)

        # min cell gap between any two seed parts (EDT per part, min over the others)
        min_gap = np.inf
        for a in range(len(seeds)):
            d = ndimage.distance_transform_edt(~seeds[a])
            for b in range(len(seeds)):
                if a != b:
                    min_gap = min(min_gap, float(d[seeds[b]].min()))
        cents = [np.argwhere(m).mean(axis=0) for m in seeds]
        max_eu = max(np.hypot(*(ca - cb)) for ca, cb in itertools.combinations(cents, 2))

        # CWD between the parts on the O'Brien surface (parts only -- cheap), with the traceback
        # path giving intervening names, the cost-1000 crossing flag, AND the per-pair barrier
        # evidence: highways/rail are the cost-10 CLASS (not 1000), so "no cost-1000 on the path"
        # alone cannot rule out a road crossing -- path_max_cost / path_cells_cost10plus measure it
        # directly instead of leaving it to be inferred from cost-per-cell arithmetic.
        pair_costs, pair_max, pair_n10, intervening, crosses = [], [], [], set(), False
        for a in range(len(seeds)):
            cum, _ = mcp.find_costs([tuple(x) for x in np.argwhere(seeds[a])])
            for b in range(a + 1, len(seeds)):
                c = float(np.nanmin(cum[seeds[b]]))
                pair_costs.append(round(c, 1))
                cells_b = np.argwhere(seeds[b])
                tgt = tuple(cells_b[int(np.nanargmin(cum[seeds[b]]))])
                mcp.find_costs([tuple(x) for x in np.argwhere(seeds[a])])   # re-seed (traceback trap)
                pth = np.asarray(mcp.traceback(tgt), dtype=np.int32)
                if len(pth):
                    on = res[pth[:, 0], pth[:, 1]]
                    crosses = crosses or bool((on == max_cost).any())
                    pair_max.append(int(np.nanmax(on)))
                    pair_n10.append(int((on >= 10).sum()))
                    for other_lbl, om in name_masks.items():
                        if other_lbl != lbl and om[pth[:, 0], pth[:, 1]].any():
                            intervening.add(other_lbl)
                else:
                    pair_max.append(0); pair_n10.append(0)

        # decision rules, in order (spec step 0a), recorded verbatim in `reason`
        gap_km = min_gap * A.cell_km
        if min_gap < 3:
            prop, why = "merge_parts", f"rule 1: min gap {min_gap:.0f} cells < 3 -- rasterization split"
        elif desig and any(d.lower() in desig.lower() for d in multisite):
            if gap_km <= link_km and not intervening:
                prop, why = "link_locked", (f"rule 2 exception: multi-site designation but parts "
                                            f"within {link_km} km and nothing intervenes")
            else:
                prop, why = "no_link", f"rule 2: designation {desig!r} is multi-site by design"
        elif intervening:
            prop, why = "link_competing", (f"rule 3: intra-name path crosses "
                                           f"{sorted(intervening)} -- the inter-name network "
                                           f"already carries the connection")
        else:
            prop, why = "link_locked", "rule 4: default -- a named area is a management unit"

        rrows.append(dict(
            name_label=lbl, kind=kind, designation=desig, n_parts=len(seeds),
            part_areas_km2=";".join(str(a) for a in areas),
            min_gap_cells=(int(min_gap) if np.isfinite(min_gap) else None),
            max_euclid_km=round(max_eu * A.cell_km, 1),
            cwd_between_parts=";".join(str(c) for c in pair_costs),
            path_max_cost=";".join(str(v) for v in pair_max),
            path_cells_cost10plus=";".join(str(v) for v in pair_n10),
            intervening_nodes=";".join(sorted(intervening)),
            crosses_cost_1000=crosses, proposed=prop, reason=why))
        print(f"  {lbl.split(' · ')[-1][:40]:40s} {len(seeds)}p  -> {prop:15s} ({why.split(':')[0]})")

    hdr = ("# multipart_review.csv -- D16/H7 (spec step 0a). Edit `proposed` where the rules got\n"
           "# it wrong (merge_parts | link_locked | link_competing | no_link), then SIGN below.\n"
           "# PA designations are name-derived (the PA layer has no designation attribute).\n")
    body = pd.DataFrame(rrows).to_csv(index=False) if rrows else \
        "name_label,kind,designation,n_parts,part_areas_km2,min_gap_cells,max_euclid_km," \
        "cwd_between_parts,intervening_nodes,crosses_cost_1000,proposed,reason\n"
    review_path.write_text(hdr + body + "# reviewed_by: \n", encoding="utf-8")
    print(f"  wrote multipart_review.csv ({len(rrows)} names to review) -- H7: edit `proposed` "
          f"where needed, then fill in the `# reviewed_by:` line. NOTHING downstream runs "
          f"until it is signed.")
    return pd.DataFrame(rrows)


def gate_g0(A, expect_names=42, expect_merges=3):
    """G0, re-baselined by D16: name set unchanged (42 names, same 3 dedupe merges) PLUS the part
    count and the multipart_review.csv hash this run was built on (pinned by new_run)."""
    assert len(A.names) == expect_names, \
        f"G0 FAILED: {len(A.names)} names, expected {expect_names}"
    assert A.n_dedupe_merges == expect_merges, \
        f"G0 FAILED: {A.n_dedupe_merges} dedupe merges, expected {expect_merges}"
    rev = A.rec["inputs"].get("multipart_review.csv", {})
    nmf = A.rec["inputs"].get("node_names.csv")
    print(f"G0 OK (re-baselined): {len(A.names)} names ({A.n_dedupe_merges} dedupe merges) | "
          f"{len(A.parts)} seed parts -> {len(A.nodes)} routing units | "
          + (f"node_names sha256 {nmf['sha256'][:12]}" if nmf else
             f"review sha256 {rev.get('sha256', 'MISSING')[:12]}"))
    return True


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


def _edge_vectors(A, path):
    """Per-edge bands (polygons) and centre-lines, both carrying the edge table's attributes."""
    from shapely.geometry import LineString
    xs, ys = A.template.x.values, A.template.y.values

    rows = []
    for eid, idx in A.bands.items():
        m = np.zeros(A.shape[0] * A.shape[1], bool); m[idx] = True
        m = m.reshape(A.shape) & A.corridor
        if not m.any():
            continue
        polys = [_shape(shp) for shp, v in shapes(m.astype("uint8"), mask=m,
                                                  transform=A.transform) if v == 1]
        rec = A.edges.loc[eid].to_dict()
        rec["edge_id"] = eid
        rec["geometry"] = gpd.GeoSeries(polys, crs=A.crs).union_all()
        rows.append(rec)
    if rows:
        gpd.GeoDataFrame(rows, crs=A.crs).to_file(path, layer="bands", driver="GPKG")

    lines = []
    for eid, pth in A.paths.items():
        if len(pth) < 2:
            continue
        rec = A.edges.loc[eid].to_dict(); rec["edge_id"] = eid
        rec["geometry"] = LineString([(xs[c], ys[r]) for r, c in pth])
        lines.append(rec)
    if lines:
        gpd.GeoDataFrame(lines, crs=A.crs).to_file(path, layer="centrelines", driver="GPKG")


def write_run(A):
    """Every output of one run into its own run dir. `corridor_summary.json` doubles as the
    completion sentinel the ensemble resumes on (the ensemble_core pattern)."""
    dst = A.run_dir
    dst.mkdir(parents=True, exist_ok=True)
    written = []

    _tif(A, np.where(A.corridor, 1, 0), dst / "corridors.tif", "uint8", 0)
    _tif(A, np.where(np.isfinite(A.resistance_arr), A.resistance_arr, -1),
         dst / "resistance.tif", "float32", -1)
    _gpkg(A, A.corridor, dst / "corridors.gpkg")
    written += ["corridors.tif", "resistance.tif", "corridors.gpkg"]
    if getattr(A, "node_id", None) is not None:                 # raster nodes: the numbered patches
        _tif(A, A.node_id, dst / "node_id.tif", "int16", 0)
        written.append("node_id.tif")
    if getattr(A, "contracted", False):                         # v3: the complexes (Layer A) beside the patches
        _tif(A, A.complex_id, dst / "complex_id.tif", "int16", 0)
        la = complex_layer(A)
        la.to_csv(dst / "complexes_layer_a.csv", index=False, encoding="utf-8-sig")
        written += ["complex_id.tif", "complexes_layer_a.csv"]
    if getattr(A, "corridor_unprotected", None) is not None:    # W11: the corridor land still to secure
        _tif(A, np.where(A.corridor_unprotected, 1, 0), dst / "corridors_unprotected.tif", "uint8", 0)
        written.append("corridors_unprotected.tif")

    if getattr(A, "priority", None) is not None:
        _tif(A, A.priority, dst / "linkage_priority.tif", "float32", -1)
        _tif(A, A.priority_class, dst / "linkage_priority_class.tif", "uint8", 0)
        _tif(A, A.edge_owner, dst / "edge_owner.tif", "int16", -1)
        written += ["linkage_priority.tif", "linkage_priority_class.tif", "edge_owner.tif"]

    A.edges.to_csv(dst / "corridor_edges.csv", encoding="utf-8-sig")
    written.append("corridor_edges.csv")
    crit_cols = ["label_i", "label_j", "edge_class", "cost", "in_mst", "is_adjacency", "ecfb_raw",
                 "disconnects", "n_pairs_lost", "cost_inflation", "mean_pair_inflation",
                 "backup_edge_id", "backup_ratio", "irreplaceable", "insures_edge_id",
                 "locked", "alt_test_run", "edge_irreplaceable",                            # D27
                 "alt_cost", "alt_len_km", "alt_mean_res", "alt_kind",                      # D29
                 "width_ratio_p10", "width_ratio_p50", "pinch_pos",                         # D28
                 "open_ground_width_med", "lcp_len_cells", "width_not_assessable",          # D24
                 "near_contiguous", "lcp_max_cost", "crosses_cost_1000", "link_geometry", "road_crossing", "b1_forced",   # D25 / D25c
                 "route_irreplaceable_topo", "link_class", "link_class_label",              # D23 / D12 amended
                 "branch_dropped_n", "branch_dropped_max_frac", "n_branches_fixed_floor",   # D26 / G21
                 "n_branches", "route_irreplaceable", "band_new_km2", "band_cf_km2",
                 "centreline_cf_km", "width_new_km", "width_cf_km", "lcp_real", "lcp_cf",
                 "squeeze_ratio_obs", "squeezed", "band_km2", "centreline_km",
                 "centreline_protected_frac", "centreline_pa_frac", "centreline_ipca_frac", "band_protected_frac",
                 "band_pa_frac", "band_ipca_frac", "band_unprotected_km2", "secured_by", "secured"]
    (A.edges[[c for c in crit_cols if c in A.edges.columns]]
     .sort_values(["irreplaceable", "n_pairs_lost", "ecfb_raw"], ascending=False)
     .to_csv(dst / "criticality.csv", encoding="utf-8-sig"))
    written.append("criticality.csv")

    _edge_vectors(A, dst / "corridor_edges.gpkg")
    written.append("corridor_edges.gpkg")

    n_adj = int(A.edges.is_adjacency.sum())
    n_lk = len(getattr(A, "locked_edge_ids", []))
    summary = dict(
        schema="05.v2",
        run_id=A.run_id, region=A.region_label,
        n_names=len(getattr(A, "names", [])) or None,
        n_seed_parts=len(getattr(A, "parts", [])) or None,
        n_nodes=len(A.nodes),
        n_complexes=(len(A.nodes) if getattr(A, "contracted", False) else None),
        n_patches=(len(A.parts) if getattr(A, "contracted", False) else None),
        contraction=(getattr(A, "contraction_meta", None) if getattr(A, "contracted", False) else None),
        n_ipca=sum(k == "ipca" for k in A.kinds),
        n_existing_pa=sum(k == "pa" for k in A.kinds),
        n_by_kind={k: int(sum(kk == k for kk in A.kinds)) for k in sorted(set(A.kinds))},
        calibration=A.rec.get("calibration_result"),
        corridor_unprotected_km2=(round(int(A.corridor_unprotected.sum()) * A.cell_km2)
                                  if getattr(A, "corridor_unprotected", None) is not None else None),
        **(getattr(A, "band_accounting", {}) or {}),                                       # D25b: corridor_area_km2 / near_contiguous_area_km2 / intra_name / augmentation / total (per-edge band sums)
        n_secured_links=(int(A.edges["secured"].sum()) if "secured" in A.edges.columns else None),
        n_secured_by_pa=(int((A.edges["secured_by"] == "pa").sum()) if "secured_by" in A.edges.columns else None),
        n_secured_by_ipca=(int((A.edges["secured_by"] == "ipca").sum()) if "secured_by" in A.edges.columns else None),
        secured_centreline_frac=getattr(A, "secured_frac", None),
        n_edges=len(A.edges),
        n_edges_mst=int(A.edges.in_mst.sum()) - n_lk,
        n_edges_backup=int((~A.edges.in_mst).sum()),
        n_edges_adjacency=n_adj,
        n_edges_intra_name=n_lk,
        n_edges_separated=len(A.edges) - n_adj - n_lk,
        n_irreplaceable=int(A.edges.irreplaceable.sum()),
        n_route_irreplaceable=(int(A.edges["route_irreplaceable"].sum())
                               if "route_irreplaceable" in A.edges.columns else None),
        n_network_groups=A.n_groups,
        # corridor_km2 is the NEW land only; the raw swath additionally covers node interiors,
        # which are already protected or proposed (see network_mask).
        corridor_km2=round(int(A.corridor.sum()) * A.cell_km2),
        swath_incl_node_land_km2=round(int(A.swath.sum()) * A.cell_km2),
        centreline_km=round(float(A.edges["centreline_km"].sum())),
        cwd_cutoff_abs=A.cutoff, cutoff_mode=A.cutoff_mode, beta=A.cfg.get("beta"),
        resolution_m=int(round(A.cell_km * 1000)),
        resistance=_jsonable(A.cfg["resistance"]),
        priority_tiers_km2=({k: round(int((A.priority >= v).sum()) * A.cell_km2)
                             for k, v in A.tiers.items()} if getattr(A, "tiers", None) else None),
        irreplaceable_links=[
            dict(a=r.label_i, b=r.label_j, cost=round(float(r.cost), 1),
                 n_pairs_lost=int(r.n_pairs_lost),
                 cheapest_alternative_ratio=(None if r.backup_ratio is None or
                                             not np.isfinite(r.backup_ratio)
                                             else round(float(r.backup_ratio), 2)))
            for r in A.edges[A.edges.irreplaceable].itertuples()],
    )
    (dst / "corridor_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    written.append("corridor_summary.json")

    for f in written:
        p = dst / f
        try:
            p = p.relative_to(config.PROJECT_DIR)
        except ValueError:
            pass                      # run_dir redirected outside the project (tests)
        print(f"  wrote {p}")
    A.summary = summary
    return A


def finish(A):
    """write_run + append this run to the analysis-level index."""
    if "link_class" not in A.edges.columns and {"near_contiguous", "n_branches", "edge_irreplaceable"} <= set(A.edges.columns):
        classify_links(A)
    write_run(A)
    idx = config.RESULTS_DIR / config.CORRIDORS[A.key]["results_subdir"] / "runs.csv"
    runs(A.key).to_csv(idx, index=False)
    print(f"  wrote {idx.relative_to(config.PROJECT_DIR)}")
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
    """Panels: (1) corridors over PAs + IPCA anchors; (2) movement cost; (3) the graded linkage
    priority surface (if priority_surface has run)."""
    has_pri = getattr(A, "priority", None) is not None
    n = 3 if has_pri else 2
    fig, axes = plt.subplots(1, n, figsize=(7.5 * n, 12)); axes = np.atleast_1d(axes)
    pa_mask, anch = _node_masks(A)
    ctx = getattr(A, "context_pa", None)
    if ctx is not None:                      # raster nodes: existing PAs as context, never nodes
        pa_mask = pa_mask | ctx

    ax = axes[0]
    for layer, col in [(pa_mask, PA_COLOR), (anch, ANCHOR_COLOR), (A.corridor, CORRIDOR_COLOR)]:
        _da(A, np.where(layer, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    A.outline.boundary.plot(ax=ax, color="0.35", linewidth=1.0, linestyle="--")
    _frame_region(A, ax)
    _pa_lbl, _an_lbl = _node_legend(A)
    ax.legend(handles=[Patch(color=PA_COLOR, label=f"{_pa_lbl} (nodes)" if "context" not in _pa_lbl else _pa_lbl),
                       Patch(color=ANCHOR_COLOR, label=f"{_an_lbl}" if "(nodes)" in _an_lbl else f"{_an_lbl} (nodes)"),
                       Patch(color=CORRIDOR_COLOR, label=f"least-cost corridors — new land "
                             f"({A.corridor.sum()*A.cell_km2:,.0f} km²)"),
                       plt.Line2D([0], [0], color="0.35", ls="--", label="Y2Y corridor")],
              loc="lower left", fontsize=9, frameon=True)
    ax.set_title(f"{A.region_label} — least-cost corridors connecting the anchors")
    ax.set_aspect("equal"); ax.set_axis_off()

    ax2 = axes[1]
    _da(A, np.where(np.isfinite(A.resistance_arr), A.resistance_arr, np.nan).astype("float32")).plot.imshow(
        ax=ax2, cmap="magma_r", norm=LogNorm(), add_colorbar=True,
        cbar_kwargs=dict(label="movement cost (log)", shrink=0.5))
    A.outline.boundary.plot(ax=ax2, color="0.35", linewidth=1.0, linestyle="--")
    _frame_region(A, ax2)
    ax2.set_title(f"Movement cost — {A.cfg['resistance']['citation'].split(',')[0]}\n"
                  f"{A.cell_km*1000:.0f} m, 4 ordinal classes")
    ax2.set_aspect("equal"); ax2.set_axis_off()

    if has_pri:
        ax3 = axes[2]
        _da(A, np.where(A.priority > 0, A.priority, np.nan).astype("float32")).plot.imshow(
            ax=ax3, cmap="viridis", add_colorbar=True,
            cbar_kwargs=dict(label="linkage priority (edge centrality × band quality)", shrink=0.5))
        # both node sets for context: existing PAs (grey) + proposed IPCAs (teal), same as panel 1
        for layer, col in [(pa_mask, PA_COLOR), (anch, ANCHOR_COLOR)]:
            _da(A, np.where(layer, 1.0, np.nan).astype("float32")).plot.imshow(
                ax=ax3, cmap=ListedColormap([col]), add_colorbar=False)
        A.outline.boundary.plot(ax=ax3, color="0.35", linewidth=1.0, linestyle="--")
        _frame_region(A, ax3)
        ax3.legend(handles=[Patch(color=PA_COLOR, label=_node_legend(A)[0]),
                            Patch(color=ANCHOR_COLOR, label=_node_legend(A)[1])],
                   loc="lower left", fontsize=8, frameon=True)
        n_irr = int(A.edges.irreplaceable.sum())
        ax3.set_title(f"Linkage priority (graded, not hard lines)\n"
                      f"{len(A.edges)} edges · {n_irr} irreplaceable")
        ax3.set_aspect("equal"); ax3.set_axis_off()

    fig.savefig(A.fig_dir / "corridors_map.png", dpi=150, bbox_inches="tight"); plt.show()
    return A


def _node_masks(A):
    # FULL name masks where available (D16): maps and the G5 audit rows show whole named areas,
    # not just the seed parts. gate_g1's context has no A.names and falls back to A.nodes.
    pa_mask = np.zeros(A.shape, bool); anch = np.zeros(A.shape, bool)
    src = ([(n["mask"], n["kind"]) for n in A.names] if getattr(A, "names", None)
           else [(m, k) for (lbl, m), k in zip(A.nodes, A.kinds)])
    anchor_kinds = set(_nodes_cfg(A).get("anchor_kinds", ["ipca"]))
    for m, k in src:
        (anch if k in anchor_kinds else pa_mask)[m] = True
    return pa_mask, anch


def _nodes_cfg(A):
    cfg = getattr(A, "cfg", None) or {}
    return cfg.get("nodes", {}) if isinstance(cfg, dict) else {}


def _node_legend(A):
    """(pa label, anchor label) for figure legends: the north's 'existing PAs' / 'proposed IPCAs'
    unless the analysis config names its node kinds differently (wolverine: refugia patches)."""
    lg = _nodes_cfg(A).get("legend", {})
    return lg.get("pa", "existing PAs"), lg.get("anchor", "proposed IPCAs")


def _is_anchor_label(A, label):
    """Prefix test behind every 'is this an IPCA?' branch in the figure code (north: 'IPCA')."""
    return str(label).startswith(tuple(_nodes_cfg(A).get("anchor_label_prefixes", ["IPCA"])))


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


def _nodes_overlay(A, ax, XL, YL, pa_mask, anch, legend=False,
                   pa_color=PA_COLOR, anchor_color=ANCHOR_COLOR):
    # pa_color/anchor_color overrides exist for figures whose data colormap collides with the
    # house colours -- e.g. the near-optimality maps, where the muted-teal IPCA reads as part
    # of the viridis ramp / tier greens (user-flagged 2026-08-31).
    for layer, col in [(pa_mask, pa_color), (anch, anchor_color)]:
        _da(A, np.where(layer, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    A.outline.boundary.plot(ax=ax, color="0.35", linewidth=1.0, linestyle="--")
    ax.set_xlim(*XL); ax.set_ylim(*YL)
    if legend:
        ax.legend(handles=[Patch(color=pa_color, label=_node_legend(A)[0]),
                           Patch(color=anchor_color, label=_node_legend(A)[1])],
                  loc="lower left", fontsize=8, frameon=True)
    ax.set_aspect("equal"); ax.set_axis_off()


# On the near-optimality figures the data colormaps (viridis_r ramp; green tier fills) swallow
# the house teal, so proposed IPCAs get burnt orange there -- absent from both palettes.
NEAR_OPT_ANCHOR_COLOR = "#d95f02"


# ---- background reference for the zoom figures (DISPLAY-ONLY; enters no computation) ------
# Provincial borders: Natural Earth 10m admin-1 boundary lines (public domain), downloaded
# 2026-09-01 into input_data/basemap/ (README.txt there). Towns: a curated list of well-known
# settlements with WGS84 coordinates -- curated rather than NE populated-places because NE is
# unreliable for small northern-BC towns, and a transparent hand list is easier to audit.
_TOWNS = {
    "Fort St. John": (56.25, -120.85), "Dawson Creek": (55.76, -120.24),
    "Fort Nelson": (58.81, -122.70), "Mackenzie": (55.34, -123.09),
    "Chetwynd": (55.70, -121.63), "Tumbler Ridge": (55.13, -120.99),
    "Hudson's Hope": (56.03, -121.91), "Prince George": (53.92, -122.75),
    "Smithers": (54.78, -127.17), "Hazelton": (55.26, -127.67),
    "Terrace": (54.52, -128.60), "Fort St. James": (54.44, -124.25),
    "Dease Lake": (58.44, -130.01), "Telegraph Creek": (57.90, -131.16),
    "Iskut": (57.84, -129.98), "Watson Lake": (60.06, -128.71),
    "Whitehorse": (60.72, -135.06), "Atlin": (59.58, -133.70),
    "Ross River": (61.98, -132.45), "Faro": (62.23, -133.35),
    "Mayo": (63.60, -135.90), "Dawson City": (64.06, -139.43),
    "Tsay Keh": (56.90, -124.96), "Fort Ware (Kwadacha)": (57.43, -125.63),
}
_ADMIN_PATH = "basemap/ne_10m_admin_1_states_provinces_lines.shp"


def _draw_basemap(R, ax, XL, YL, towns=True, max_towns=10):
    """Provincial borders + towns on a zoom axes. Cached on R; skips gracefully (with a note)
    if the Natural Earth file is absent. DISPLAY-ONLY: nothing here enters any computation."""
    import matplotlib.patheffects as pe
    if not hasattr(R, "_admin"):
        p = config.INPUT_DIR / _ADMIN_PATH
        if p.exists():
            tr = pyproj.Transformer.from_crs(R.crs, "EPSG:4326", always_xy=True)
            xs = (float(R.template.x.min()), float(R.template.x.max()))
            ys = (float(R.template.y.min()), float(R.template.y.max()))
            lons, lats = zip(*[tr.transform(x, y) for x in xs for y in ys])
            R._admin = gpd.read_file(
                p, bbox=(min(lons) - 2, min(lats) - 2, max(lons) + 2, max(lats) + 2)
            ).to_crs(R.crs)
        else:
            R._admin = None
            print(f"  note: {p} absent -- provincial borders skipped "
                  f"(see input_data/basemap/README.txt)")
        tr = pyproj.Transformer.from_crs("EPSG:4326", R.crs, always_xy=True)
        R._towns = [(n, *tr.transform(lon, lat)) for n, (lat, lon) in _TOWNS.items()]
    if R._admin is not None and len(R._admin):
        R._admin.plot(ax=ax, color="0.15", linewidth=1.0, linestyle=(0, (6, 3)),
                      alpha=0.75, zorder=4)
    if towns:
        for n, x, y in [(n, x, y) for n, x, y in R._towns
                        if XL[0] < x < XL[1] and YL[0] < y < YL[1]][:max_towns]:
            ax.plot(x, y, marker="o", ms=3.5, color="0.1", mec="white", mew=0.8, zorder=6)
            ax.annotate(n, (x, y), xytext=(4, 4), textcoords="offset points", fontsize=7.5,
                        color="0.1", zorder=6,
                        path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])


def compare(A, other, pad=0.05, label_a=None, label_b=None):
    """Compare this run against another RUN DIRECTORY (v1's frozen output works too).

    v1 compared in-memory scenario snapshots; runs now live on disk, so a comparison reads the
    other run's corridors.tif instead of needing both solved in one kernel. That also makes
    v1-vs-v2 a first-class comparison rather than a special case.
    """
    other = pathlib.Path(other)
    b_da = rioxarray.open_rasterio(other / "corridors.tif", masked=True).squeeze()
    b = (b_da.rio.reproject_match(A.template).values > 0) & A.pu      # onto THIS run's grid
    a = A.corridor
    label_a = label_a or A.run_id
    label_b = label_b or other.name

    XL, YL = _region_extent(A, pad)
    pa_mask, anch = _node_masks(A)
    panel_h = 9.0
    panel_w = panel_h * (XL[1] - XL[0]) / (YL[1] - YL[0])
    fig, axes = plt.subplots(1, 3, figsize=(panel_w * 3 + 2.0, panel_h))

    for ax, m, lbl in ((axes[0], a, label_a), (axes[1], b, label_b)):
        _da(A, np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([CORRIDOR_COLOR]), add_colorbar=False)
        _nodes_overlay(A, ax, XL, YL, pa_mask, anch, legend=(ax is axes[0]))
        ax.set_title(f"{lbl} — {int(m.sum())*A.cell_km2:,.0f} km²", fontsize=11)

    d = np.full(A.shape, np.nan, "float32")
    d[a & b] = 0.0; d[a & ~b] = 1.0; d[~a & b] = 2.0
    axd = axes[2]
    _da(A, d).plot.imshow(ax=axd, cmap=ListedColormap([SHARED_COLOR, ONLY_A_COLOR, ONLY_B_COLOR]),
                          vmin=-0.5, vmax=2.5, add_colorbar=False)
    _nodes_overlay(A, axd, XL, YL, pa_mask, anch)
    j = _jaccard(a, b)
    axd.legend(handles=[
        Patch(color=SHARED_COLOR, label=f"shared ({(a & b).sum()*A.cell_km2:,.0f} km²)"),
        Patch(color=ONLY_A_COLOR, label=f"{label_a} only ({(a & ~b).sum()*A.cell_km2:,.0f} km²)"),
        Patch(color=ONLY_B_COLOR, label=f"{label_b} only ({(~a & b).sum()*A.cell_km2:,.0f} km²)"),
        Patch(color=PA_COLOR, label="existing PAs"),
        Patch(color=ANCHOR_COLOR, label="proposed IPCAs")],
        loc="lower left", fontsize=9, frameon=True)
    axd.set_title(f"Difference — Jaccard {j:.3f}", fontsize=11)

    fig.suptitle(f"{A.region_label} — {label_a} vs {label_b}", fontsize=15)
    fig.tight_layout()
    fig.savefig(A.fig_dir / f"compare_{label_b}.png", dpi=130, bbox_inches="tight")
    plt.show()
    print(f"Jaccard {label_a} vs {label_b}: {j:.3f}")
    return j


# ================= value profile (co-benefit audit) =================
# THE AUDIT RUNS ON THE 1 km GRID, not the 300 m routing grid. Every value layer is natively 1 km,
# so upsampling adds no information -- and it would actively corrupt the numbers:
# results_core.mask_profile computes contribution as sum(feature over mask) / region_total, while
# results_core._region_total computes that denominator at the layer's native 1 km with no
# finer-than-source path (only a coarsening `agg`). A 300 m mask would sum ~11 replicated cells per
# source cell against a 1 km denominator and inflate every "% of Y2Y" figure by ~11x, silently.
# It would also cost ~10 GB of stacks. So masks cross the boundary here and results_core is
# untouched -- which is what makes gate G5 (v1's IPCA/PA profile rows reproduce exactly) meaningful.
def _to_audit(A, mask, min_frac=0.5):
    """A 300 m boolean mask -> a 1 km boolean mask, by areal coverage fraction.

    `min_frac=0.5` (majority) is area-conserving for corridors several km wide, which these are
    (the calibrated band averages a few km across). It is NOT safe for sub-kilometre features, so
    `audit_area_check` reports the discrepancy rather than letting it pass unnoticed.
    """
    src = A.template.copy(data=mask.astype("float32"))
    src.rio.write_nodata(None, inplace=True)
    frac = src.rio.reproject_match(A.audit_template, resampling=Resampling.average).values
    return np.nan_to_num(frac, nan=0.0) >= min_frac


def audit_area_check(A, mask, name="corridor", tol=0.10):
    """G5 support: the 1 km audit mask must carry ~the same area as the 300 m mask it came from.

    If it ever drifts, contribution and efficiency are being computed over a different footprint
    than the map shows -- which is exactly the class of silent error the grid split exists to avoid.
    """
    a300 = int(mask.sum()) * A.cell_km2
    a1k = int(_to_audit(A, mask).sum()) * 1.0          # 1 km cells == 1 km²
    rel = abs(a1k - a300) / max(a300, 1e-9)
    flag = "OK " if rel <= tol else "WARN"
    print(f"  {flag} audit grid: {name} {a300:,.0f} km² @300 m -> {a1k:,.0f} km² @1 km "
          f"({rel:+.1%})")
    if rel > tol:
        print(f"       the corridor is narrow relative to a 1 km cell; contribution/efficiency "
              f"are computed on the 1 km footprint, so treat them as indicative for this run.")
    return a300, a1k


def _profile_stacks(A):
    """A minimal stand-in for `results_core.build_stacks`, on the 1 km AUDIT grid.

    build_stacks is coupled to a SOLVED prioritizr run (it needs A.portfolio, _locked_mask,
    _cluster_profile). The primitives underneath it are not — `_scaled` / `_read_match` /
    `_region_total` / `mask_profile` only need a grid reference and the feature layers. So we hand
    them a namespace whose grid is the 1 km audit grid, and 05 stays standalone from 03/04."""
    man = json.loads(pathlib.Path(config.MANIFEST_PATH).read_text())
    cont = [L for L in man["layers"] if L["role"] == "feature_continuous"]
    efg = [L for L in man["layers"] if L["role"] == "feature_efg"]
    rx, _ = A.audit_template.rio.resolution()
    cell_km2 = (abs(rx) / 1000.0) ** 2
    P = types.SimpleNamespace(
        sol0=A.audit_template, agg=1, manifest=man, fig_dir=A.fig_dir,
        cont=[L["name"] for L in cont], efg=[L["name"] for L in efg],
        cell_km2=cell_km2, cell_ha=cell_km2 * 100.0)
    P.axes_labels = [n.replace("_", " ") for n in P.cont] + ["EFG (mean)"]
    print(f"  building {len(cont)} continuous + {len(efg)} EFG stacks on the "
          f"{abs(rx):.0f} m AUDIT grid…")

    # RICHNESS STRETCH DOMAIN = THE ROUTING WINDOW, not the full Y2Y audit grid. The audit grid
    # is full-Y2Y for the "% of Y2Y" DENOMINATORS only; the 0-1 richness stretch is "relative to
    # the north" (corridor_profile's stated scaling, and what v1 did -- gate G5 encodes it).
    # Stretching over full Y2Y instead silently rescaled every gradient-bearing axis: measured on
    # v2_run001, macrorefugia -0.33 / climate corridors +0.25 / AOH -0.1..-0.2 while every
    # contribution reproduced v1 to 0.01 -- the G5 failure that exposed this.
    win = _to_audit(A, np.ones(A.shape, bool))          # routing-window rectangle on the audit grid

    def _scaled_win(path):
        a = rc._read_match(P, path)
        v = a[win & np.isfinite(a)]
        if not v.size:
            return np.zeros_like(a)
        lo, hi = np.percentile(v, 5), np.percentile(v, 95)
        return np.clip((a - lo) / (hi - lo if hi > lo else 1.0), 0, 1)

    P.cont_stack = np.stack([_scaled_win(L["path"]) for L in cont])        # 0-1 over the WINDOW
    P.cont_raw = np.stack([rc._read_match(P, L["path"]) for L in cont])    # native units
    P.efg_stack = np.stack([_scaled_win(L["path"]) for L in efg])
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
    the physical links between protected areas. There are more of them (~23) than can be read as star
    panels, so the `n_groups` LARGEST components seed the clusters and every remaining component is
    absorbed into its nearest seed: the segments then account for 100% of corridor area (the earlier
    top-N cut left ~6% in 13 unplotted components — printed, but absent from the stars and the CSV),
    while each panel is still ONE PHYSICAL LINK plus a few small neighbours, which is what makes the
    "X <-> Y" naming honest and keeps the profiles comparable to a top-N run.

    Seeded, not free clustering (e.g. average-linkage over all 23 centroids): free clustering
    allocates panels by ISOLATION rather than by importance — it spent two of ten panels on 8 km² and
    67 km² far-north slivers while merging the two biggest links away.

    Nearest by CELL, not by centroid. Segments are long and sinuous, so a scrap lying alongside a
    link is adjacent to it while being far from its centroid. One EDT over the seed union gives every
    cell its nearest seed cell, so each component's own closest cell picks the owner."""
    lab, n = ndimage.label(corr & ~nodes, structure=np.ones((3, 3), int))
    cnt = np.bincount(lab.ravel())
    ids = np.arange(1, n + 1)

    order = ids[np.argsort(cnt[ids])[::-1]]
    seeds, rest = order[:n_groups], order[n_groups:]
    cl = np.zeros(n + 1, int)
    cl[seeds] = seeds                                        # a seed is its own cluster
    if len(rest):
        dist, (ri, ci) = ndimage.distance_transform_edt(~np.isin(lab, seeds), return_indices=True)
        for c in rest:
            m = lab == c
            r, co = np.nonzero(m)
            k = np.argmin(dist[r, co])                       # the component's cell closest to a seed
            cl[c] = lab[ri[r[k], co[k]], ci[r[k], co[k]]]
    cl = cl[ids]

    # node-id raster once, so each segment's touching nodes is a single unique() per segment
    node_id = np.zeros(A.shape, np.int16)
    for k, (_, m) in enumerate(A.nodes, 1):
        node_id[m] = k
    lat = pyproj.Transformer.from_crs(A.crs, "EPSG:4326", always_xy=True)

    segs = []
    for c_id in np.unique(cl):
        members = ids[cl == c_id]
        m = np.isin(lab, members)
        touch = np.unique(node_id[ndimage.binary_dilation(m, np.ones((3, 3), bool))])
        names = [A.nodes[k - 1][0] for k in touch if k > 0]
        r, c = np.nonzero(m)
        y = lat.transform(A.template.x.values[c].mean(), A.template.y.values[r].mean())[1]
        # label the map at the LARGEST part: a multi-part cluster's overall centroid can fall on
        # empty ground between its pieces.
        big = members[np.argmax(cnt[members])]
        br, bc = np.nonzero(lab == big)
        segs.append(dict(cid=int(c_id), mask=m, cells=int(cnt[members].sum()), lat=y, ends=names,
                         parts=len(members),
                         anchor_xy=(A.template.x.values[bc].mean(), A.template.y.values[br].mean())))
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
    return segs, n


# Axes whose FEATURE DEFINITION changed after v1's profile froze (2026-08-07); G5 reports them
# instead of asserting on them:
#   climate type macrorefugia -- re-oriented vmax-v -> 1/v (2026-08-17 leverage redesign, M6.3)
#   EFG (mean) -- the EFG block was R0-CURATED 40 -> 20 features (y2y M2.11, 2026-09-09) and Ethan
#                 adopted the curated block for this analysis the same day (M5.16): the axis now
#                 counts a different class set, so v1's 40-class value is not a regression target
G5_REDEFINED = ("climate type macrorefugia", "EFG (mean)")


def gate_g5(A, redefined=G5_REDEFINED, tol=0.02):
    """Gate G5 -- audit invariance: v1's frozen IPCA / PA profile rows must reproduce on every
    richness axis whose feature definition is unchanged (`redefined` axes are reported, not
    asserted). Reads A.profile["table"] (corridor_profile) and the frozen v1 profile."""
    old = pd.read_csv(config.RESULTS_DIR / "corridors_north" / "_v1_frozen" / "corridor_profile.csv")
    new = A.profile["table"]
    for area in ("proposed IPCAs", "existing PAs"):
        o = old[old.area == area].iloc[0]; n = new[new.area == area].iloc[0]
        cols = [c for c in new.columns if c.endswith("| richness") and c in old.columns]
        inv = [c for c in cols if not any(k in c for k in redefined)]
        d = max(abs(float(o[c]) - float(n[c])) for c in inv)
        print(f"  {area:16s} max |Δrichness| over {len(inv)} unchanged axes = {d:.4f}")
        for c in cols:
            if any(k in c for k in redefined):
                print(f"    reported, not asserted ({c.split(' |')[0]}: feature redefined after v1 froze): "
                      f"v1 {float(o[c]):.3f} -> v2 {float(n[c]):.3f}")
        assert d < tol, f"G5 FAILED on {area}: the audit path changed (max Δ {d:.4f})"
    print("G5 OK — audit path unchanged on every axis with an unchanged feature definition")


def gate_g15(A, tol=1e-9):
    """Gate G15 (D19): the priority centrality is finite and non-negative on every inter-name
    edge; on a pure tree (beta = 0) current-flow and shortest-path edge betweenness rank
    identically (one path per pair, so both reduce to the same pair count) -- Spearman rho = 1.
    Writes centrality_compare.csv (edge, both centralities, ranks, rank delta) so the effect of
    the D19 choice is inspectable."""
    from scipy.stats import spearmanr
    e = A.edges
    inter = e[(e["edge_class"] == "inter") & ~e["is_adjacency"].astype(bool)]
    cf, sp = inter["centrality_cf"].astype(float), inter["centrality_sp"].astype(float)
    assert np.isfinite(cf).all() and (cf >= -tol).all(), "G15: non-finite / negative current-flow centrality"
    assert np.isfinite(sp).all() and (sp >= -tol).all(), "G15: non-finite / negative shortest-path centrality"
    cmp = inter[["label_i", "label_j", "edge_class", "in_mst", "cost", "centrality_cf", "centrality_sp"]].copy()
    cmp["rank_cf"] = cmp["centrality_cf"].rank(ascending=False, method="min").astype(int)
    cmp["rank_sp"] = cmp["centrality_sp"].rank(ascending=False, method="min").astype(int)
    cmp["rank_delta"] = cmp["rank_cf"] - cmp["rank_sp"]
    cmp = cmp.sort_values("rank_cf")
    cmp.to_csv(A.run_dir / "centrality_compare.csv", encoding="utf-8-sig")
    rho_full = float(spearmanr(cf, sp).correlation) if len(inter) > 2 else np.nan
    # tree case: rebuild at beta = 0 on the same distance matrix
    labels = [lbl for lbl, _ in A.nodes]
    _, tree = cg.build(A.D, labels, A.kinds, beta=0, verbose=False)
    t = tree[~tree["is_adjacency"].astype(bool)]
    cf_t, sp_t = t["centrality_cf"].astype(float).values, t["centrality_sp"].astype(float).values
    # on a tree both are the same pair count up to networkx's constant factor: assert
    # PROPORTIONALITY (ties are exact there; a rank test would be broken by solver noise)
    prop = bool(np.allclose(cf_t / cf_t.sum(), sp_t / sp_t.sum(), rtol=1e-6, atol=1e-9))
    rho_tree = float(spearmanr(np.round(cf_t / cf_t.sum(), 9), np.round(sp_t / sp_t.sum(), 9)).correlation)
    print(f"  G15: {len(inter)} inter-name edges | rank agreement current-flow vs shortest-path: "
          f"Spearman {rho_full:.3f} on the augmented graph, {rho_tree:.3f} on the beta=0 tree "
          f"| top-5 by current flow: " + ", ".join(
              f"{_short_node_name(r.label_i, 12)}<->{_short_node_name(r.label_j, 12)}" for r in cmp.head(5).itertuples()))
    assert prop, f"G15 FAILED: on the beta=0 tree current-flow and shortest-path betweenness are not proportional (Spearman {rho_tree:.4f})"
    print("G15 OK — centrality_compare.csv written")
    return cmp


# ================= D21 adjacency (neighbour) graph -- diagnostic universe =================
ADJACENCY_DEFAULT = {"metric": "cwd", "connectivity": 8, "distance_cap_km": None,
                     "drop_through_core": False}


def _allocation(A, fields, n):
    """argmin over n fields (memmap-friendly; ties -> lowest id); -1 where no field is finite."""
    best = np.full(A.shape, np.inf, "float32"); alloc = np.full(A.shape, -1, "int32")
    for k in range(n):
        f = np.asarray(fields[k], dtype="float32")
        better = f < best                       # strict: the first (lowest id) wins ties
        best[better] = f[better]; alloc[better] = k
    return alloc


def _zone_pairs(alloc, connectivity=8):
    """Unordered (a, b) pairs of zone ids that share a boundary (a != b, both >= 0)."""
    H, W = alloc.shape
    shifts = [(0, 1), (1, 0)] + ([(1, 1), (1, -1)] if connectivity == 8 else [])

    def sl(d, n):
        return (slice(0, n - d), slice(d, n)) if d >= 0 else (slice(-d, n), slice(0, n + d))
    pairs = set()
    for dr, dc in shifts:
        (ra, rb), (ca, cb) = sl(dr, H), sl(dc, W)
        a, b = alloc[ra, ca], alloc[rb, cb]
        m = (a != b) & (a >= 0) & (b >= 0)
        if m.any():
            ab = np.stack([a[m], b[m]], axis=1); ab.sort(axis=1)
            pairs |= {tuple(x) for x in np.unique(ab, axis=0).tolist()}   # NB: `map` is shadowed by cc.map
    return pairs


def adjacency_graph(A, write=True, ridge_tol=0.5, cap_km=200.0, verbose=True):
    """D21 -- Linkage Mapper-style ADJACENCY GRAPH as a diagnostic universe beside the backbone.

    Cost-allocation neighbour graph on the cached part-level CWD fields: every routable cell is
    allocated to the seed part with the minimum CWD (argmin; ties -> lowest part id); two parts
    are adjacent when their zones share an 8-connected boundary; parts are contracted to
    ROUTING UNITS (names; a name's parts are one unit unless `no_link`). LM's optional filters
    (distance cap, drop-through-core) are OFF: the counts they *would* remove are reported.
    A Euclidean allocation (LM's default metric) is computed as the comparison column.

    Per adjacent pair the LCP length and the intervening zones/masks are read off the cached
    UNIT fields without any new routing: the least-cost path is the ridge where
    CWD_u + CWD_v <= min + ridge_tol (G10: exactly 0 slack on path cells). Length = the traced
    centreline for backbone edges, else a straight-line proxy between the ridge's two ends.

    Products (write=True): allocation.tif, adjacency_edges.csv, adjacency_nodes.csv,
    figures/adjacency_map.png; A.edges gains is_adjacent, is_adjacent_euclid, via_names.
    NOT a routing input; no bands for adjacency-only edges; no legend class. Gate G17.
    """
    from scipy import ndimage
    cfg = dict(ADJACENCY_DEFAULT); cfg.update(A.cfg.get("adjacency", {}) or {})
    conn = int(cfg.get("connectivity", 8))
    U = len(A.nodes); labels = [lbl for lbl, _ in A.nodes]
    P_ = len(A.parts)
    part_unit = np.full(P_, -1, "int32")
    for u, pidx in enumerate(A.unit_parts):
        for pi in pidx:
            part_unit[pi] = u
    if verbose:
        print(f"D21 adjacency graph: allocating {int(A.pu.sum()):,} routable cells to {P_} seed parts -> {U} units")
    alloc_p = _allocation(A, A.cwd_parts, P_)
    alloc = np.where(alloc_p >= 0, part_unit[np.clip(alloc_p, 0, None)], -1).astype("int32")
    part_pairs = _zone_pairs(alloc_p, conn)                       # part level (locked edges live here)
    pairs = {tuple(sorted((int(part_unit[a]), int(part_unit[b])))) for a, b in part_pairs}
    pairs = {pq for pq in pairs if pq[0] != pq[1]}
    # Euclidean allocation (LM default) for the comparison column
    seed = np.full(A.shape, -1, "int32")
    for pi, (_, m) in enumerate(A.parts):
        seed[m] = pi
    _, (ri, ci) = ndimage.distance_transform_edt(seed < 0, return_indices=True)
    alloc_e = np.where(A.pu, seed[ri, ci], -1).astype("int32")
    pairs_e = {tuple(sorted((int(part_unit[a]), int(part_unit[b])))) for a, b in _zone_pairs(alloc_e, conn)}
    pairs_e = {pq for pq in pairs_e if pq[0] != pq[1]}

    # backbone lookup by UNIT pair (inter-name + adjacency edges); locked intra-name edges carry
    # PART ids in i/j (D16) and are handled at part level below, exempt from G17
    bb, locked = {}, {}
    for eid, r in A.edges.iterrows():
        if pd.isna(r.get("i")):
            continue
        key = tuple(sorted((int(r["i"]), int(r["j"]))))
        (locked if r.get("edge_class") == "intra_name" else bb)[key] = eid
    masks = [m for _, m in A.nodes]
    D = np.asarray(A.D, float)

    def ridge_info(u, v):
        fu = np.asarray(A.cwd[u], dtype="float32"); fv = np.asarray(A.cwd[v], dtype="float32")
        tot = fu + fv
        d = float(D[u, v])
        ridge = np.isfinite(tot) & (tot <= d + ridge_tol) & ~masks[u] & ~masks[v]
        rr, cc_ = np.nonzero(ridge)
        if not len(rr):
            return 0.0, [], []
        # straight-line proxy between the ridge cell nearest u and the one nearest v (a lower
        # bound on path length; the ridge's cell COUNT is an area on uniform land, where exactly
        # tied staircase paths widen it into a lens -- measured 78 vs 21.6 km on the harness)
        a, b = np.argmin(fu[rr, cc_]), np.argmin(fv[rr, cc_])
        L = float(np.hypot(rr[a] - rr[b], cc_[a] - cc_[b])) * A.cell_km
        zones = sorted({int(z) for z in np.unique(alloc[ridge]) if z >= 0 and z not in (u, v)})
        crossed = [w for w in range(U) if w not in (u, v) and bool(np.any(ridge & masks[w]))]
        return L, zones, crossed

    rows = []
    all_pairs = sorted(pairs | set(bb.keys()))          # every adjacent pair + every backbone pair
    for (u, v) in all_pairs:
        cost = float(D[u, v])
        eid = bb.get((u, v))
        L, zones, crossed = ridge_info(u, v) if np.isfinite(cost) and cost > 0 else (0.0, [], [])
        rows.append(dict(edge_id=eid, label_i=labels[u], label_j=labels[v], i=u, j=v,
                         is_adjacent=(u, v) in pairs, is_adjacent_euclid=(u, v) in pairs_e,
                         in_backbone=eid is not None,
                         edge_class=(A.edges.loc[eid, "edge_class"] if eid else None),
                         in_mst=(bool(A.edges.loc[eid, "in_mst"]) if eid else False),
                         cost=cost, lcp_len_km_proxy=round(L, 1),
                         centreline_km=(float(A.edges.loc[eid, "centreline_km"]) if eid and "centreline_km" in A.edges.columns else np.nan),
                         via_zones=" | ".join(labels[z] for z in zones),
                         crosses_masks=" | ".join(labels[w] for w in crossed),
                         lm_drop_through_core=bool(crossed),
                         lm_beyond_cap=((float(A.edges.loc[eid, "centreline_km"]) if eid and "centreline_km" in A.edges.columns else L) > cap_km)))
    # locked intra-name edges: part-level adjacency on the PART fields (reported, G17-exempt)
    part_pairs_e = _zone_pairs(alloc_e, conn)
    for (pa, pb), eid in locked.items():
        fa = np.asarray(A.cwd_parts[pa], dtype="float32"); fb = np.asarray(A.cwd_parts[pb], dtype="float32")
        tot = fa + fb; d = float(np.nanmin(tot))
        ridge = np.isfinite(tot) & (tot <= d + ridge_tol) & ~A.parts[pa][1] & ~A.parts[pb][1]
        u = int(part_unit[pa])
        zones = sorted({int(z) for z in np.unique(alloc[ridge]) if z >= 0 and z != u})
        rows.append(dict(edge_id=eid, label_i=A.edges.loc[eid, "label_i"], label_j=A.edges.loc[eid, "label_j"],
                         i=u, j=u, is_adjacent=(pa, pb) in part_pairs, is_adjacent_euclid=(pa, pb) in part_pairs_e,
                         in_backbone=True, edge_class="intra_name", in_mst=bool(A.edges.loc[eid, "in_mst"]),
                         cost=d, lcp_len_km_proxy=np.nan,
                         centreline_km=float(A.edges.loc[eid, "centreline_km"]) if "centreline_km" in A.edges.columns else np.nan,
                         via_zones=" | ".join(labels[z] for z in zones), crosses_masks="",
                         lm_drop_through_core=False, lm_beyond_cap=False))
    adj = pd.DataFrame(rows)
    # columns onto the network edge table
    for col in ("is_adjacent", "is_adjacent_euclid", "via_names"):
        A.edges[col] = None
    for r in adj[adj.in_backbone].itertuples():
        A.edges.loc[r.edge_id, "is_adjacent"] = bool(r.is_adjacent)
        A.edges.loc[r.edge_id, "is_adjacent_euclid"] = bool(r.is_adjacent_euclid)
        A.edges.loc[r.edge_id, "via_names"] = r.via_zones
    # per-unit table
    deg = {u: 0 for u in range(U)}; deg_e = {u: 0 for u in range(U)}; deg_b = {u: 0 for u in range(U)}
    for u, v in pairs: deg[u] += 1; deg[v] += 1
    for u, v in pairs_e: deg_e[u] += 1; deg_e[v] += 1
    for u, v in bb: deg_b[u] += 1; deg_b[v] += 1
    nodes = pd.DataFrame([dict(unit=u, label=labels[u], kind=A.kinds[u], n_parts=len(A.unit_parts[u]),
                               n_neighbours=deg[u], n_neighbours_euclid=deg_e[u], n_backbone_links=deg_b[u])
                          for u in range(U)]).sort_values("n_neighbours", ascending=False)
    # report + G17
    adj_only = adj[adj.is_adjacent & ~adj.in_backbone]
    bb_not_adj = adj[adj.in_backbone & ~adj.is_adjacent & (adj.cost > 0) & (adj.edge_class != "intra_name")]
    lk_not_adj = adj[(adj.edge_class == "intra_name") & ~adj.is_adjacent]
    mst_not_adj = bb_not_adj[bb_not_adj.in_mst & (bb_not_adj.edge_class == "inter")]
    if verbose:
        print(f"  |E_adj| = {len(pairs)} unit pairs (euclid: {len(pairs_e)}) | backbone pairs {len(bb)} | "
              f"E_adj ∩ backbone = {int((adj.is_adjacent & adj.in_backbone).sum())} | adjacency-only {len(adj_only)}")
        print(f"  backbone/backup edges NOT adjacent: {len(bb_not_adj)}" +
              ("".join(f"\n    {_short_node_name(r.label_i,16)} <-> {_short_node_name(r.label_j,16)} [{r.edge_class}{', mst' if r.in_mst else ''}] via {r.via_zones or '—'}"
                       for r in bb_not_adj.itertuples()) if len(bb_not_adj) else ""))
        if len(lk_not_adj):
            print(f"  locked intra-name edges whose PARTS are not zone-adjacent (reported, G17-exempt): {len(lk_not_adj)}" +
                  "".join(f"\n    {_short_node_name(r.label_i,16)} <-> {_short_node_name(r.label_j,16)} via {r.via_zones or '—'}" for r in lk_not_adj.itertuples()))
        print(f"  LM filters would remove (not applied): through-core {int(adj[adj.is_adjacent].lm_drop_through_core.sum())}, "
              f"beyond {cap_km:.0f} km {int(adj[adj.is_adjacent].lm_beyond_cap.sum())} of {len(pairs)} adjacency edges")
        print(f"  n_neighbours: median {nodes.n_neighbours.median():.0f}, max {nodes.n_neighbours.max()} "
              f"({_short_node_name(nodes.iloc[0].label, 20)})")
    A.adjacency = types.SimpleNamespace(edges=adj, nodes=nodes, alloc=alloc, pairs=pairs, pairs_euclid=pairs_e, cfg=cfg)
    if write:
        _da(A, alloc).astype("int32").rio.write_nodata(-1, inplace=False).rio.to_raster(A.run_dir / "allocation.tif", compress="DEFLATE")
        adj.to_csv(A.run_dir / "adjacency_edges.csv", index=False, encoding="utf-8-sig")
        nodes.to_csv(A.run_dir / "adjacency_nodes.csv", index=False, encoding="utf-8-sig")
        _adjacency_map(A)
    assert len(mst_not_adj) == 0, ("G17 FAILED: inter-name MST edge(s) not in the adjacency graph: " +
                                   "; ".join(f"{r.label_i} <-> {r.label_j} via {r.via_zones}" for r in mst_not_adj.itertuples()))
    if verbose:
        print("G17 OK — every inter-name MST edge is an adjacency edge")
    return adj


def _adjacency_map(A):
    """Appendix figure: neighbour links as thin LINES (never bands) over the M1-style basemap;
    backbone edges darker, MST edges heavier."""
    import matplotlib.patheffects as pe
    adj = A.adjacency.edges
    pa_mask, anch = _node_masks(A)
    XL, YL = _region_extent(A, 0.05)
    fig, ax = plt.subplots(figsize=(12, 15))
    for layer, col in [(pa_mask, PA_COLOR), (anch, ANCHOR_COLOR)]:
        _da(A, np.where(layer, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    cent = {}
    for u, (lbl, m) in enumerate(A.nodes):
        rr, cc_ = np.nonzero(m)
        cent[u] = (A.template.x.values[int(np.median(cc_))], A.template.y.values[int(np.median(rr))])
    for r in adj.itertuples():
        if not r.is_adjacent and not r.in_backbone:
            continue
        (x0, y0), (x1, y1) = cent[r.i], cent[r.j]
        if r.in_backbone and r.in_mst:
            ax.plot([x0, x1], [y0, y1], color="0.15", lw=1.8, zorder=4)
        elif r.in_backbone:
            ax.plot([x0, x1], [y0, y1], color="0.35", lw=1.2, ls="--", zorder=4)
        else:
            ax.plot([x0, x1], [y0, y1], color="#2c7fb8", lw=0.6, alpha=0.7, zorder=3)
    for u, (x, y) in cent.items():
        ax.plot(x, y, "o", ms=3, color="0.1", zorder=5)
    if hasattr(A, "outline"):
        A.outline.boundary.plot(ax=ax, color="0.35", linewidth=1.0, linestyle="--", zorder=3)
    try:
        _draw_basemap(A, ax, XL, YL, towns=False)
    except Exception:
        pass
    ax.set_xlim(*XL); ax.set_ylim(*YL); ax.set_aspect("equal"); ax.set_axis_off()
    n_adj, n_bb = len(A.adjacency.pairs), int(adj.in_backbone.sum())
    ax.legend(handles=[plt.Line2D([0], [0], color="#2c7fb8", lw=0.8, label=f"neighbour link (cost-allocation adjacency; {n_adj} pairs)"),
                       plt.Line2D([0], [0], color="0.35", lw=1.2, ls="--", label="backbone backup link"),
                       plt.Line2D([0], [0], color="0.15", lw=1.8, label="backbone MST link"),
                       Patch(color=PA_COLOR, label="existing PAs"), Patch(color=ANCHOR_COLOR, label="proposed IPCAs")],
              loc="lower left", fontsize=9, frameon=True)
    ax.set_title(f"{A.region_label} — neighbour universe (D21) vs the minimum network + backups ({n_bb} links)\n"
                 "lines join area centres; the difference between the two graphs is the choice space", fontsize=12)
    (A.fig_dir).mkdir(parents=True, exist_ok=True)
    fig.savefig(A.fig_dir / "adjacency_map.png", dpi=150, bbox_inches="tight"); plt.close(fig)


def corridor_profile(A, n_groups=10):
    """Value star plots for the corridor network — a CO-BENEFIT AUDIT, not a scorecard.

    The corridors are routed for PERMEABILITY, never for conservation value, so a low carbon or EFG
    axis is not a failure — it is the finding that connection and representation are different
    objectives. Compares three areas on shared axes: the corridor's OWN new land, the proposed
    IPCAs, and the existing PAs = what the connective tissue adds over the protected areas.

    The corridor mask excludes node land -- `network_mask` does that at construction, so this is
    the same mask the map and the summary report. (Swath bands radiate outward from the
    nodes, so the raw swath lies ~37% inside PA/IPCA polygons; profiling it whole would credit the
    corridors with already-protected land. The `& ~nodes` below is left as a cheap guard.)

    Two different scalings share these figures — say which is which when reading them:
      richness              = 0-1 over the WORKING REGION (5-95 pctile), i.e. relative to the north
      contribution/efficiency = FULL-Y2Y denominators, i.e. literally "% of Y2Y"
    """
    corr = A.corridor
    tag = ""
    pa_mask, anch = _node_masks(A)
    nodes = pa_mask | anch

    # corridors split into geographic segments; the PA sets stay WHOLE units for comparison
    if n_groups:
        segs, n_comp = _corridor_groups(A, corr, nodes, n_groups)
        A.groups = segs
        areas = [(s["name"], s["mask"], s["color"]) for s in segs]
        covered = sum(s["cells"] for s in segs)
        print(f"corridor segments: {n_comp} components merged by location into {len(segs)} clusters "
              f"({100*covered/max((corr & ~nodes).sum(),1):.0f}% of corridor area — all of it)")
        multi = [s for s in segs if s["parts"] > 1]
        if multi:
            print("  multi-part clusters: " + "; ".join(
                f"{s['name'].split('.')[0]} = {s['parts']} components" for s in multi))
    else:
        A.groups = None
        areas = [("corridor (new land)", corr & ~nodes, CORRIDOR_COLOR)]
    areas += [("proposed IPCAs", anch, ANCHOR_COLOR), ("existing PAs", pa_mask, PA_COLOR)]

    # star titles use the compact segment names (the full ones collide); the map legend and the
    # CSV carry the full "X <-> Y" naming.
    short = {s["name"]: s["short"] for s in (A.groups or [])}
    P = _profile_stacks(A)

    # CROSS TO THE AUDIT GRID. Segmentation and mapping stay at 300 m (full routing detail); only
    # the profiling masks are coarsened, because every value layer is natively 1 km.
    print("  crossing masks 300 m -> 1 km for profiling:")
    audit = {}
    for name, m, _ in areas:
        audit[name] = _to_audit(A, m)
        audit_area_check(A, m, name[:38])

    C = dict(ids=[n for n, _, _ in areas], colors={n: c for n, _, c in areas},
             names={n: short.get(n, n) for n, _, _ in areas},
             cnt={n: int(audit[n].sum()) for n, _, _ in areas},
             profs={}, contrib={}, eff={}, raw={})
    for name, _, _ in areas:
        C["profs"][name], C["contrib"][name], C["eff"][name], C["raw"][name] = \
            rc.mask_profile(P, audit[name])

    print(f"\nvalue profile{tag} (area denominators = full Y2Y, {P.n_region_full:,.0f} PU):")
    for name, m, _ in areas:
        print(f"  {name[:44]:44s} {int(m.sum())*A.cell_km2:8,.0f} km²  "
              f"({100*int(audit[name].sum())/P.n_region_full:.2f}% of Y2Y)")
    swath = getattr(A, "swath", corr)
    print(f"  overlap check: {100*(swath & nodes).sum()/max(swath.sum(),1):.0f}% of the raw swath sits "
          f"inside node polygons and is EXCLUDED from the corridor rows")

    for metric in ("richness", "contribution", "efficiency"):
        rc.plot_stars(P, C, metric,
                      f"{A.region_label} — corridor co-benefits vs protected areas{tag}\n"
                      f"corridors are routed for permeability, not value",
                      f"corridors_stars_{metric}.png")

    rows = []
    for name, m, _ in areas:
        km2 = int(m.sum()) * A.cell_km2                      # reported at the ROUTING resolution
        base = dict(area=name, km2=round(km2),
                    km2_audit_grid=round(int(audit[name].sum()) * P.cell_km2),
                    pct_y2y=round(100 * int(audit[name].sum()) / P.n_region_full, 2))
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


# ================= results context (05_results notebook) =================
# Read-only, engine-free: everything below draws from a run dir's ON-DISK artifacts (rasters,
# tables, node_parts.gpkg) -- no resistance, no CWD cache, no MCP. That is what lets figure
# styling iterate in minutes without ever touching the production pipeline (notebooks 01-04).

def load_results(run_dir):
    """Open a completed run for figures/tables only. Assembles a lightweight namespace from the
    run dir alone; loads in ~a minute."""
    run_dir = pathlib.Path(run_dir)
    rec = json.loads((run_dir / "run_config.json").read_text())
    summary = json.loads((run_dir / "corridor_summary.json").read_text())

    def _open(name, sub=""):
        p = run_dir / sub / name
        return rioxarray.open_rasterio(p, masked=True).squeeze() if p.exists() else None

    template = _open("corridors.tif")
    R = _NS(run_dir=run_dir, fig_dir=run_dir / "figures", rec=rec, summary=summary,
            run_id=rec["run_id"], region_label=rec["cfg"]["region_label"],
            cfg=rec["cfg"], cutoff=summary["cwd_cutoff_abs"],
            template=template, crs=template.rio.crs, transform=template.rio.transform(),
            shape=template.shape)
    rx, ry = template.rio.resolution()
    R.cell_km2, R.cell_km = abs(rx * ry) / 1e6, abs(rx) / 1000.0

    R.corridor = np.nan_to_num(template.values, nan=0) > 0
    R.priority = _open("linkage_priority.tif")
    R.near_opt = _open("near_optimality.tif")
    R.near_opt_class = _open("near_optimality_class.tif")
    R.attribution = _open("ensemble_attribution.tif", "ensemble")
    R.attr_axis = {k: _open(f"attribution_{k}.tif", "ensemble")
                   for k in ("B_cutoff", "C_loo", "D_beta")}
    R.branch_label = _open("branches.tif")
    R.edge_owner = _open("edge_owner.tif")
    R.resistance = _open("resistance.tif")

    R.edges = pd.read_csv(run_dir / "corridor_edges.csv", index_col=0)
    R.branches = pd.read_csv(run_dir / "branches.csv")
    ef = run_dir / "ensemble" / "edge_frequency.csv"
    R.edge_freq = pd.read_csv(ef, index_col=0) if ef.exists() else None
    alt = run_dir / "alternatives_branches.csv"
    R.alternatives = pd.read_csv(alt) if alt.exists() else None
    cfb = run_dir / "bands_counterfactual.gpkg"
    R.cf_bands = gpd.read_file(cfb) if cfb.exists() else None       # D17 outline (M3)

    # node overlays from the H7 gpkg; IPCA/PA kind from the label prefix
    parts = gpd.read_file(run_dir / "node_parts.gpkg").to_crs(R.crs)
    R.pa_mask = np.zeros(R.shape, bool)
    R.anch = np.zeros(R.shape, bool)
    for _, row in parts.iterrows():
        m = rasterize([(row.geometry, 1)], out_shape=R.shape, transform=R.transform,
                      fill=0, dtype="uint8").astype(bool)
        (R.anch if _is_anchor_label(R, row["name_label"]) else R.pa_mask)[m] = True
    R.outline = gpd.read_file(config.CORRIDOR_REF).to_crs(R.crs)
    # raster-node analyses (wolverine): PA context, the refugia classes and the node table
    nc = R.cfg.get("nodes", {})
    R.context_pa, R.refugia, R.node_table, R.node_id = None, None, None, None
    if nc.get("context_pa_min_km2"):
        big = _pa_polys(nc["context_pa_min_km2"]).to_crs(R.crs)
        R.context_pa = rasterize([(g, 1) for g in big.geometry], out_shape=R.shape, transform=R.transform,
                                 fill=0, dtype="uint8").astype(bool)
    R.protected, R.protected_ipca, R.corridor_unprotected = None, None, None
    pc = nc.get("protected")
    if pc:
        allp = _pa_polys(float(pc.get("pa_min_km2", 0.0))).to_crs(R.crs)
        R.protected = rasterize([(g, 1) for g in allp.geometry], out_shape=R.shape, transform=R.transform,
                                fill=0, dtype="uint8").astype(bool)
        R.protected_pa = R.protected.copy()                 # existing PAs only (the wide layout's grey layer)
        R.protected_ipca = np.zeros(R.shape, bool)
        if pc.get("include_proposed") and pc.get("proposed"):
            ip = gpd.read_file(config.PROJECT_DIR / pathlib.Path(pc["proposed"])).to_crs(R.crs)
            R.protected_ipca = rasterize([(g, 1) for g in ip.geometry], out_shape=R.shape, transform=R.transform,
                                         fill=0, dtype="uint8").astype(bool)
            R.protected |= R.protected_ipca
        cu = _open("corridors_unprotected.tif")
        R.corridor_unprotected = (np.nan_to_num(cu.values, nan=0) > 0) if cu is not None else (R.corridor & ~R.protected)
    nr = rec["inputs"].get("nodes_raster")
    if nr:
        cls = rioxarray.open_rasterio(config.PROJECT_DIR / nr["warped"]["path"]).squeeze().values
        cls = np.nan_to_num(cls, nan=0).astype("uint8")
        R.refugia = np.where(np.isin(cls, nr["classes_core"]), 2,
                             np.where(np.isin(cls, nr["classes_marginal"]), 1, 0)).astype("uint8")
        R.node_id = _open("node_id.tif")
        nm = run_dir / "node_names.csv"
        if nm.exists():
            R.node_table = pd.read_csv(nm, encoding="utf-8-sig").fillna({"display_name": ""})
    # v3 contraction (D-W3): the complexes as the node layer the package reads, the patches kept underneath
    R.contracted, R.complexes, R.complex_table, R.complex_id, R.slivers, R.centrelines = False, None, None, None, None, None
    if (run_dir / "complex_membership.csv").exists() and (run_dir / "complexes_layer_a.csv").exists():
        R.contracted = True
        R.complex_table = pd.read_csv(run_dir / "complexes_layer_a.csv", encoding="utf-8-sig")
        R.complex_id = _open("complex_id.tif")
        cg_ = gpd.read_file(run_dir / "complexes.gpkg").to_crs(R.crs)
        R.complexes = cg_.merge(R.complex_table.drop(columns=[c for c in R.complex_table.columns if c in cg_.columns and c != "complex_id"]),
                                on="complex_id", how="left")
        if (run_dir / "slivers_v2.csv").exists():
            R.slivers = pd.read_csv(run_dir / "slivers_v2.csv", encoding="utf-8-sig")
        try:
            R.centrelines = gpd.read_file(run_dir / "corridor_edges.gpkg", layer="centrelines").to_crs(R.crs)
        except Exception:      # noqa: BLE001 -- a run written before centrelines were a layer
            R.centrelines = None
    # the 1 km audit grid (pinned; see AUDIT_TEMPLATE) -- needed by the value-profiling views
    R.audit_template = rioxarray.open_rasterio(config.HANDOFF_DIR / AUDIT_TEMPLATE,
                                               masked=True).squeeze()
    print(f"{R.run_id}: results context loaded ({len(R.edges)} edges, {len(R.branches)} "
          f"branches, corridor {int(R.corridor.sum())*R.cell_km2:,.0f} km²)")
    return R


def priority_links_map(R, squeeze_max=0.5, south_of_frac=0.40, pad_km=35):
    """The framing-1 companion MAP to priority_link_stars: each numbered link's OWNED corridor
    land (edge_owner partition -- the exact land the stars profile) in the SAME tab10 colour as
    its star plot, so map <-> stars <-> priority_links_profile.csv cross-reference by both
    number and colour (the 04 clusters convention). Securing-regime corridor in light grey for
    context; named areas labelled as in the zoom."""
    import matplotlib.patheffects as pe
    e, classes, owner, order, links, XL, YL = _zoom_links(R, squeeze_max, south_of_frac, pad_km)
    xs, ys = R.template.x.values, R.template.y.values
    ordered = sorted(links, key=lambda t: t[2][:, 0].mean())

    w = 12.5 * (XL[1] - XL[0]) / (YL[1] - YL[0])
    fig, ax = plt.subplots(figsize=(w + 3.0, 13))
    link_codes = [order[k] for k, _, _ in ordered]
    rest = R.corridor & ~np.isin(owner, link_codes)
    _da(R, np.where(rest, 1.0, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap=ListedColormap(["#c9d2d6"]), add_colorbar=False)
    for layer, col in [(R.pa_mask, PA_COLOR), (R.anch, ANCHOR_COLOR)]:
        _da(R, np.where(layer, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    handles = []
    for n, (k, _, cells) in enumerate(ordered, 1):
        col = rc.CLUSTER_CMAP((n - 1) % 10)
        m = (owner == order[k]) & R.corridor
        if m.any():
            _da(R, np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(
                ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
        r = e.loc[k]
        ax.annotate(str(n), (xs[int(np.median(cells[:, 1]))], ys[int(np.median(cells[:, 0]))]),
                    fontsize=10, fontweight="bold", ha="center", va="center",
                    bbox=dict(boxstyle="circle,pad=0.28", fc="white", ec=col, lw=1.8))
        handles.append(Patch(color=col,
                             label=f"{n}. {_short_node_name(r['label_i'], 16)} ↔ "
                                   f"{_short_node_name(r['label_j'], 16)} "
                                   f"({m.sum() * R.cell_km2:,.0f} km²)"))
    ax.set_xlim(*XL); ax.set_ylim(*YL); ax.set_aspect("equal"); ax.set_axis_off()

    from shapely.geometry import box as _box
    frame = _box(XL[0], YL[0], XL[1], YL[1])
    parts = gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(R.crs)
    for _, row in parts.dissolve(by="name_label").reset_index().iterrows():
        clip = row.geometry.intersection(frame)
        if clip.is_empty or clip.area < 25e6:
            continue
        pt = clip.representative_point()
        ax.annotate(_short_node_name(row["name_label"], 20), (pt.x, pt.y),
                    fontsize=8.5, ha="center", va="center", fontstyle="italic",
                    color=("#1a6363" if _is_anchor_label(R, row["name_label"]) else "0.25"),
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    _draw_basemap(R, ax, XL, YL)
    handles += [Patch(color="#c9d2d6", label="other corridor land (securing regime)"),
                Patch(color=PA_COLOR, label="existing PAs"),
                Patch(color=ANCHOR_COLOR, label="proposed IPCAs"),
                plt.Line2D([0], [0], color="0.15", lw=1.0, ls=(0, (6, 3)), label="provincial border")]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.16, 0.5),
              fontsize=8.5, frameon=True)
    ax.set_title(f"{R.region_label} — the nine priority links (PROACT alternatives)\n"
                 f"colours and numbers match the value-profile star plots and "
                 f"priority_links_profile.csv", fontsize=12)
    fig.savefig(R.fig_dir / "priority_links_map.png", dpi=160, bbox_inches="tight")
    plt.show()
    return R


def priority_link_stars(R, squeeze_max=0.5, south_of_frac=0.40, include_reference=True):
    """Value-profile STAR PLOTS for the numbered priority links (the PROACT consequences
    input): one star per link, same estimands and machinery as the corridor co-benefit audit
    (richness / contribution / efficiency via results_core.mask_profile on the 1 km audit
    grid, 0.5-majority crossing -- the G5-anchored path, so these stars are directly comparable
    with the corridor/IPCA/PA stars already produced).

    Link land = the cells each link OWNS on the priority surface (edge_owner partition -- the
    same attribution the routing-problem maps use, so no double counting between overlapping
    bands). Numbering matches the zoom/board figures (north -> south). Reference rows for
    proposed IPCAs and existing PAs are appended for the gap-analysis read.
    Writes priority_links_stars_{richness,contribution,efficiency}.png + a
    priority_links_profile.csv row per link (corridor_profile.csv format)."""
    e, classes, owner, order, links, XL, YL = _zoom_links(R, squeeze_max, south_of_frac, 35)
    P = _profile_stacks(R)

    areas = []
    for n, (k, col, cells) in enumerate(sorted(links, key=lambda t: t[2][:, 0].mean()), 1):
        m = np.zeros(R.shape, bool)
        m[cells[:, 0], cells[:, 1]] = True
        r = e.loc[k]
        name = (f"{n}. {_short_node_name(r['label_i'], 14)} ↔ "
                f"{_short_node_name(r['label_j'], 14)}")
        areas.append((name, m, rc.CLUSTER_CMAP((n - 1) % 10)))
    if include_reference:
        areas += [("proposed IPCAs", R.anch, ANCHOR_COLOR), ("existing PAs", R.pa_mask, PA_COLOR)]

    print("  crossing masks 300 m -> 1 km for profiling:")
    audit = {}
    for name, m, _ in areas:
        audit[name] = _to_audit(R, m)
        audit_area_check(R, m, name[:38])

    C = dict(ids=[n for n, _, _ in areas], colors={n: c for n, _, c in areas},
             names={n: n for n, _, _ in areas},
             cnt={n: int(audit[n].sum()) for n, _, _ in areas},
             profs={}, contrib={}, eff={}, raw={})
    for name, _, _ in areas:
        if not audit[name].any():
            print(f"  {name}: too narrow for the 1 km audit grid -- skipped")
            C["ids"].remove(name)
            continue
        C["profs"][name], C["contrib"][name], C["eff"][name], C["raw"][name] = \
            rc.mask_profile(P, audit[name])

    for metric in ("richness", "contribution", "efficiency"):
        rc.plot_stars(P, C, metric,
                      f"{R.region_label} — priority-link value profiles (PROACT consequences)\n"
                      f"links routed for permeability, never for value — low axes are findings,"
                      f" not failures",
                      f"priority_links_stars_{metric}.png")

    # raw native units per axis, straight from RAW_SPEC (imported, not redefined -- the third
    # table of the Y2Y-wide consequences family)
    units = [rc.RAW_SPEC[n][1] or "index" for n in P.cont] + [f"groups present (of {len(P.efg)})"]
    dps = [rc.RAW_SPEC[n][3] for n in P.cont] + [0]
    rows = []
    for name, m, _ in areas:
        if name not in C["ids"]:
            continue
        rows.append(dict(area=name, km2=round(int(m.sum()) * R.cell_km2),
                         km2_audit_grid=round(int(audit[name].sum()) * P.cell_km2),
                         pct_y2y=round(100 * int(audit[name].sum()) / P.n_region_full, 3),
                         **{f"{ax} | richness": round(C["profs"][name][j], 3)
                            for j, ax in enumerate(P.axes_labels)},
                         **{f"{ax} | contribution %": round(C["contrib"][name][j], 3)
                            for j, ax in enumerate(P.axes_labels)},
                         **{f"{ax} | efficiency": round(C["eff"][name][j], 3)
                            for j, ax in enumerate(P.axes_labels)},
                         **{f"{ax} | raw [{units[j]}]": round(float(C["raw"][name][j]), dps[j])
                            for j, ax in enumerate(P.axes_labels)}))
    df = pd.DataFrame(rows)
    out = R.run_dir / "priority_links_profile.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"  wrote {out.name} ({len(df)} rows) + priority_links_stars_*.png")
    return df


def cost_surface_map(R, pad=0.05):
    """Full-extent movement-cost surface beside raw gHM — the comparison behind D2/A2.

    Left: the O'Brien 4-class surface at 300 m (the routing input; log ramp, class shares in
    the title). Right: Theobald gHM at the 1 km audit resolution (power-scaled colour — the
    layer is heavy-tailed and a linear ramp hides everything below towns). Same extent, same
    overlays. The point the pairing makes: the cost surface carries roads as continuous linear
    barriers at 300 m, while 1 km gHM smears them toward invisibility -- the reason 05 routes
    on the published surface at native resolution (A2) rather than a gHM blend (D2)."""
    from matplotlib.colors import PowerNorm
    XL, YL = _region_extent(R, pad)
    cost = R.resistance.values
    fin = cost[np.isfinite(cost) & (cost > 0)]
    shares = {int(c): 100 * float((fin == c).sum()) / fin.size for c in (1, 10, 100, 1000)}
    parts = gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(R.crs)
    bounds = parts.dissolve(by="name_label").boundary
    handles = [plt.Line2D([0], [0], color="#2b6a6a", lw=1, label="named-area boundaries"),
               plt.Line2D([0], [0], color="0.15", lw=1.0, ls=(0, (6, 3)),
                          label="provincial border"),
               plt.Line2D([0], [0], color="0.35", lw=1.0, ls="--", label="Y2Y corridor")]

    fig, axes = plt.subplots(1, 2, figsize=(21, 12.5))
    ax = axes[0]
    _da(R, np.where(cost > 0, cost, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap="magma_r", norm=LogNorm(vmin=1, vmax=1000), add_colorbar=True,
        cbar_kwargs=dict(label="movement cost — 4 ordinal classes only (log colour scale; "
                               "intermediate shades do not occur)", shrink=0.55))
    bounds.plot(ax=ax, color="#2b6a6a", linewidth=0.6)
    R.outline.boundary.plot(ax=ax, color="0.35", linewidth=1.0, linestyle="--")
    _draw_basemap(R, ax, XL, YL, max_towns=12)
    ax.set_xlim(*XL); ax.set_ylim(*YL); ax.set_aspect("equal"); ax.set_axis_off()
    ax.legend(handles=handles, loc="lower left", fontsize=9, frameon=True)
    ax.set_title(f"Movement cost (O'Brien/Pither, 300 m)\n"
                 f"class shares: cost-1 {shares[1]:.1f}% · 10 {shares[10]:.1f}% · "
                 f"100 {shares[100]:.1f}% · 1000 {shares[1000]:.1f}%", fontsize=12)

    ax = axes[1]
    gp = config.PROJECT_DIR / "input_data" / "cleaned_aligned" / "human_modification.tif"
    if gp.exists():
        ghm = rioxarray.open_rasterio(gp, masked=True).squeeze() \
            .rio.clip_box(minx=XL[0], miny=YL[0], maxx=XL[1], maxy=YL[1])
        ghm.plot.imshow(ax=ax, cmap="magma_r", norm=PowerNorm(0.4, vmin=0, vmax=1),
                        add_colorbar=True,
                        cbar_kwargs=dict(label="global human modification (raw gHM, 0–1; "
                                               "power-scaled colour)", shrink=0.55))
        ax.set_title("Human modification (Theobald gHM v3 at the 1 km audit grid)\n"
                     "continuous index; linear features smear toward invisibility at 1 km",
                     fontsize=12)
    else:
        ax.text(0.5, 0.5, "cleaned_aligned/human_modification.tif absent",
                ha="center", va="center", transform=ax.transAxes)
    bounds.plot(ax=ax, color="#2b6a6a", linewidth=0.6)
    R.outline.boundary.plot(ax=ax, color="0.35", linewidth=1.0, linestyle="--")
    _draw_basemap(R, ax, XL, YL, max_towns=12)
    ax.set_xlim(*XL); ax.set_ylim(*YL); ax.set_aspect("equal"); ax.set_axis_off()

    fig.suptitle(f"{R.region_label} — the routing input vs the footprint index it replaces "
                 f"(D2/A2: roads survive at 300 m; 1 km gHM smears them)", fontsize=13)
    fig.tight_layout()
    fig.savefig(R.fig_dir / "cost_surface_map.png", dpi=150, bbox_inches="tight")
    plt.show()
    return R


def near_opt_map(R, pad=0.05):
    """D11 deliverable figure 1 of 2: the wall-to-wall near-optimality (slack) surface."""
    XL, YL = _region_extent(R, pad)
    slack = R.near_opt.values
    fig, ax = plt.subplots(figsize=(12, 13))
    lo, hi = max(R.cutoff / 10.0, 1e-2), float(np.nanpercentile(slack[slack > 0], 99.5))
    _da(R, np.where(np.isfinite(slack), np.maximum(slack, lo), np.nan).astype("float32")) \
        .plot.imshow(ax=ax, cmap="viridis_r", norm=LogNorm(vmin=lo, vmax=hi),
                     add_colorbar=True,
                     cbar_kwargs=dict(label="slack above the least-cost route "
                                            "(raw cost units; log COLOUR scale)",
                                      shrink=0.55))
    _nodes_overlay(R, ax, XL, YL, R.pa_mask, R.anch, legend=True,
                   anchor_color=NEAR_OPT_ANCHOR_COLOR)
    ax.set_title(f"{R.region_label} — near-optimality surface (D11): min slack over all links\n"
                 f"a slack surface, NOT a frequency; the band cutoff = about {R.cutoff * R.cell_km:.1f} km of extra travel on open ground "
                 f"({R.cutoff:,.1f} cost units) sits at the low end", fontsize=12)
    fig.savefig(R.fig_dir / "near_optimality_map.png", dpi=150, bbox_inches="tight")
    plt.show()
    return R


def label_named_areas(R, ax, top_n=12, overrides=None, fontsize=9, XL=None, YL=None,
                      ipca_color="#7a3402", pa_color="0.2", dx_m=150_000, dy_m=32_000,
                      min_frame_km2=25):
    """Label the biggest named areas (IPCAs coloured, PAs grey; italic, white halo) with a greedy
    anisotropic declutter: biggest first, and a label is skipped when an already-placed one sits
    within dx_m horizontally AND dy_m vertically (a 9 pt label spans ~150 km of map at region
    scale, so a plain radius either drops nothing or everything). `overrides` = {fragment: text
    | (text, dx_m, dy_m)} for board wording / nudges. With XL/YL the names are clipped to the
    frame first (zooms)."""
    import matplotlib.patheffects as pe
    from shapely.geometry import box as _box
    names = (gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(R.crs)
             .dissolve(by="name_label").reset_index())
    if XL is not None:
        frame = _box(XL[0], YL[0], XL[1], YL[1])
        names["geometry"] = names.geometry.intersection(frame)
        names = names[~names.geometry.is_empty]
    names["km2"] = names.geometry.area / 1e6
    names = names[names["km2"] >= min_frame_km2]
    placed = []
    for _, row in names.sort_values("km2", ascending=False).iterrows():
        if len(placed) >= top_n:
            break
        pt = row.geometry.representative_point()
        if any(abs(pt.x - x) < dx_m and abs(pt.y - y) < dy_m for x, y in placed):
            continue
        placed.append((pt.x, pt.y))
        is_ipca = _is_anchor_label(R, row["name_label"])
        ov = next((v for k, v in (overrides or {}).items() if k in str(row["name_label"])), None)
        disp, dx, dy = (ov if isinstance(ov, tuple)
                        else (ov or _short_node_name(row["name_label"], 18), 0, 0))
        ax.annotate(disp, (pt.x + dx, pt.y + dy), fontsize=fontsize, ha="center", va="center",
                    fontstyle="italic", color=(ipca_color if is_ipca else pa_color), zorder=6,
                    path_effects=[pe.withStroke(linewidth=2.4, foreground="white")])
    return placed


def near_opt_map_board(R, pad=0.05,
                       title="Keeping the North Connected",
                       subtitle="Searching for low-cost movement corridors between protected "
                                "areas and proposed IPCAs",
                       footnote="Based on landscape structure (human footprint and natural "
                                "barriers), not tracked animal movement. Yellowstone to Yukon "
                                "— northern BC & Yukon analysis.",
                       label_top_n=12,
                       label_overrides={"Tū Łī́dlini": "Tū Łī́dlini (Ross River)",
                                        "Northern Rocky": ("Northern Rocky Mountains",
                                                           25_000, -30_000)}):
    """PRESENTATION variant of the near-optimality surface (board audience; separate file,
    the science figure near_opt_map is untouched). Plain-language framing, no decision codes,
    larger type, and the structural-claim caveat carried as a footnote instead of jargon."""
    XL, YL = _region_extent(R, pad)
    slack = R.near_opt.values
    fig, ax = plt.subplots(figsize=(12, 13.5))
    lo, hi = max(R.cutoff / 10.0, 1e-2), float(np.nanpercentile(slack[slack > 0], 99.5))
    _da(R, np.where(np.isfinite(slack), np.maximum(slack, lo), np.nan).astype("float32")) \
        .plot.imshow(ax=ax, cmap="viridis_r", norm=LogNorm(vmin=lo, vmax=hi),
                     add_colorbar=True,
                     cbar_kwargs=dict(label="extra travel cost of passing through this land\n"
                                            "(bright = on or near a best route)",
                                      shrink=0.5))
    _nodes_overlay(R, ax, XL, YL, R.pa_mask, R.anch, legend=False,
                   anchor_color=NEAR_OPT_ANCHOR_COLOR)
    ax.legend(handles=[Patch(color=PA_COLOR, label="existing protected areas"),
                       Patch(color=NEAR_OPT_ANCHOR_COLOR, label="proposed IPCAs")],
              loc="lower left", fontsize=11, frameon=True)

    if label_top_n:
        label_named_areas(R, ax, top_n=label_top_n, overrides=label_overrides)

    fig.suptitle(title, fontsize=20, fontweight="bold", y=0.97)
    ax.set_title(subtitle, fontsize=13, pad=12)
    fig.text(0.5, 0.015, footnote, ha="center", fontsize=9, color="0.35")
    fig.savefig(R.fig_dir / "near_optimality_map_board.png", dpi=180, bbox_inches="tight")
    plt.show()
    return R


def near_opt_tiers_map(R, pad=0.05):
    """D11 deliverable figure 2 of 2: the pre-registered near-optimality tiers."""
    XL, YL = _region_extent(R, pad)
    cls = np.nan_to_num(R.near_opt_class.values, nan=0)
    colors = ["#1a9850", "#a6d96a", "#ffffbf", "#f2f2f2"]          # robust / frequent / occasional / routable beyond the band (D30)
    fig, ax = plt.subplots(figsize=(12, 13))
    _da(R, np.where(cls > 0, cls, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap=ListedColormap(colors), vmin=0.5, vmax=4.5, add_colorbar=False)
    _nodes_overlay(R, ax, XL, YL, R.pa_mask, R.anch,
                   anchor_color=NEAR_OPT_ANCHOR_COLOR)
    km2 = {c: int((cls == c).sum()) * R.cell_km2 for c in (1, 2, 3, 4)}
    c6, c2, c1 = R.cutoff / 6, R.cutoff / 2, R.cutoff                                   # D30 fixed breaks
    ax.legend(handles=[Patch(color=colors[0], label=f"robust core — slack ≤ cutoff/6 = {c6:,.1f} ({km2[1]:,.0f} km²)"),
                       Patch(color=colors[1], label=f"frequent — slack ≤ cutoff/2 = {c2:,.1f} ({km2[2]:,.0f} km²)"),
                       Patch(color=colors[2], label=f"occasional — slack ≤ cutoff = {c1:,.1f} (the band; {km2[3]:,.0f} km²)"),
                       Patch(color=colors[3], label=f"routable land beyond the band"),
                       Patch(color=PA_COLOR, label="existing PAs"),
                       Patch(color=NEAR_OPT_ANCHOR_COLOR, label="proposed IPCAs")],
              loc="lower left", fontsize=9, frameon=True)
    ax.set_title(f"{R.region_label} — near-optimality tiers (fixed slack breaks in cost units, D30; "
                 f"the cutoff = about {R.cutoff * R.cell_km:.1f} km of extra travel on open ground)", fontsize=12)
    fig.savefig(R.fig_dir / "near_optimality_tiers_map.png", dpi=150, bbox_inches="tight")
    plt.show()
    return R


def attribution_map(R, pad=0.05, core=None):
    """D15 figure: ensemble attribution + the three per-axis panels, robust-core contour on the
    main panel. Attribution, not frequency: ~42/47 members are leave-one-out."""
    core = core if core is not None else R.cfg["ensemble"].get("robust_core_freq", 0.9)
    XL, YL = _region_extent(R, pad)
    panels = [("all 47 members", R.attribution),
              ("axis B — band cutoff × {0.5, 1, 2}", R.attr_axis["B_cutoff"]),
              ("axis C — leave-one-out by name (42)", R.attr_axis["C_loo"]),
              ("axis D — β ∈ {1.5, 2.5, 4}", R.attr_axis["D_beta"])]
    fig, axes = plt.subplots(2, 2, figsize=(16.5, 19))
    for ax, (title, da) in zip(axes.ravel(), panels):
        a = da.values
        _da(R, np.where(a > 0, a, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap="magma", vmin=0, vmax=1, add_colorbar=True,
            cbar_kwargs=dict(label="share of members using the cell", shrink=0.5))
        if title.startswith("all"):
            ax.contour(R.template.x, R.template.y, (np.nan_to_num(a, nan=0) >= core),
                       levels=[0.5], colors=["#00d0ff"], linewidths=0.8)
        _nodes_overlay(R, ax, XL, YL, R.pa_mask, R.anch, legend=False)
        if title.startswith("all"):
            # the contour is an OVERLAY, not a colour on the ramp -- it needs its own legend
            # entry or it reads as an unexplained colour (user-reported, 2026-08-30)
            ax.legend(handles=[
                plt.Line2D([0], [0], color="#00d0ff", lw=1.5,
                           label=f"robust core (attribution ≥ {core:g})"),
                Patch(color=PA_COLOR, label="existing PAs"),
                Patch(color=ANCHOR_COLOR, label="proposed IPCAs")],
                loc="lower left", fontsize=9, frameon=True)
        ax.set_title(title, fontsize=11)
    fig.suptitle(f"{R.region_label} — ensemble ATTRIBUTION (which assumption a cell depends on;"
                 f" not a selection frequency)", fontsize=13)
    fig.tight_layout()
    fig.savefig(R.fig_dir / "ensemble_attribution_map.png", dpi=140, bbox_inches="tight")
    plt.show()
    return R


def branches_map(R, pad=0.05):
    """D12 figure: route-irreplaceable branch land in a muted tone; the edges with genuine
    alternatives highlighted, one colour per edge (primary branch solid, alternative lighter)."""
    from matplotlib.colors import to_rgb
    XL, YL = _region_extent(R, pad)
    lab = np.nan_to_num(R.branch_label.values, nan=0).astype(int)
    br = R.branches.reset_index(drop=True)
    br["value"] = np.arange(1, len(br) + 1)             # branches.tif values follow row order
    multi = br.groupby("edge_id").filter(lambda g: len(g) > 1)

    fig, ax = plt.subplots(figsize=(13, 12))
    base = np.isin(lab, br.loc[~br.index.isin(multi.index), "value"])
    _da(R, np.where(base, 1.0, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap=ListedColormap(["#c9b8a0"]), add_colorbar=False)
    handles = [Patch(color="#c9b8a0",
                     label=f"route-irreplaceable branches "
                           f"(n = {int(R.edges.get('route_irreplaceable', pd.Series()).sum())} edges)")]
    for k, (eid, g) in enumerate(multi.groupby("edge_id")):
        col = np.asarray(to_rgb(plt.get_cmap("tab10")(k)))
        pair = f"{g.iloc[0].label_i.split(' · ')[-1]} ↔ {g.iloc[0].label_j.split(' · ')[-1]}"
        for j, r in enumerate(g.sort_values("k").itertuples()):
            # lighter per extra branch; clipped so a link with >= 4 branches (wolverine) stays a valid colour
            c = tuple(np.clip(col * (1 - 0.45 * j) + 0.45 * j * np.array([1, 1, 1]), 0.0, 1.0))
            _da(R, np.where(lab == r.value, 1.0, np.nan).astype("float32")).plot.imshow(
                ax=ax, cmap=ListedColormap([c]), add_colorbar=False)
            handles.append(Patch(color=c, label=f"{pair} — branch {r.k} "
                                                f"({r.area_km2:,.0f} km², slack {r.min_slack:.1f})"))
    _nodes_overlay(R, ax, XL, YL, R.pa_mask, R.anch)
    handles += [Patch(color=PA_COLOR, label="existing PAs"),
                Patch(color=ANCHOR_COLOR, label="proposed IPCAs")]
    ax.legend(handles=handles, loc="lower left", fontsize=8.5, frameon=True)
    ax.set_title(f"{R.region_label} — route branches (D12): {len(br)} branches; "
                 f"alternatives exist on {multi.edge_id.nunique()} links only", fontsize=12)
    fig.savefig(R.fig_dir / "branches_map.png", dpi=150, bbox_inches="tight")
    plt.show()
    return R


def _edge_squeeze(edges, cutoff, cost_per_km_intact=10.0 / 3.0):
    """Per-link routing-constraint diagnostics (M4.6): mean band width vs the OPEN-GROUND
    expectation, plus cost intensity.

    On uniform cost-1 ground the band is a distance-ellipse: for route length L and detour
    allowance d = cutoff / 3.33 km, the midpoint half-width is sqrt(dL/2 + d²/4), and an
    ellipse's mean width is (π/4) x its midpoint width. squeeze_idx = actual mean width /
    that expectation: ~1 = geometry alone confines the corridor (SECURING regime, land
    interchangeable); << 1 = the landscape has eaten the alternatives (ROUTING regime).
    cost_per_km ≈ 3.33 = pure intact land; higher = barrier crossings en route. The ellipse
    normalisation assumes a straight link on uniform cost — a screening index, not an estimand.
    """
    e = edges.copy()
    d = cutoff / cost_per_km_intact
    # width/L ratios are meaningless for near-touching pairs (routes of 1-2 cells): NaN under 2 km
    L = e["centreline_km"].where(e["centreline_km"] >= 2.0)
    e["width_km"] = (e["band_km2"] / L).round(1)
    e["squeeze_idx"] = (e["width_km"] /
                        ((np.pi / 4) * 2 * np.sqrt(d * L / 2 + d * d / 4))).round(2)
    e["cost_per_km"] = (e["cost"] / L).round(1)
    return e


def _routing_classes(R, squeeze_max=0.5):
    """The routing-regime edge classes shared by routing_problem_map and its zoom panel."""
    e = _edge_squeeze(R.edges, R.cutoff)
    if "link_class" in e.columns:                                   # D23 / D25c: classify_links is the single source; four classes only
        lc = e["link_class"]
        return e, [
            (LINK_CLASS_LABEL["both"], e.index[lc == "both"], "#d73027"),
            (LINK_CLASS_LABEL["edge"], e.index[lc == "edge"], "#fc8d59"),
            (LINK_CLASS_LABEL["squeezed"], e.index[lc == "squeezed"], "#dfb515"),
        ]
    ri = e.get("route_irreplaceable", pd.Series(False, index=e.index))
    ei = e["edge_irreplaceable"] if "edge_irreplaceable" in e.columns else e["irreplaceable"]   # D27: the class-eligible flag (runs before it: the raw flag)
    both = e.index[(ei == True) & (ri == True)]
    irr = e.index[(ei == True) & ~e.index.isin(both)]
    if "squeezed" in e.columns and e["squeezed"].notna().any():
        # D17 (H8 closed): the counterfactual band ratio from corridor_edges.csv
        rmax = float(R.cfg.get("squeeze_ratio", squeeze_max))
        sq = e.index[(e["squeezed"] == True) & (e["irreplaceable"] != True)]
        sq_label = f"squeezed (D17: band < {rmax:g}× its no-barrier counterfactual)"
    else:
        print("  H8 OPEN: 'squeezed' drawn from the analytic screening index (M4.6), not D17 -- "
              "re-run notebook 04 (counterfactual_squeeze) before this class ships")
        sq = e.index[(e["squeeze_idx"] < squeeze_max) & (e["irreplaceable"] != True)]
        sq_label = f"squeezed (screening: band < {squeeze_max:g}× open-ground ellipse; H8 OPEN)"
    return e, [
        ("both-senses irreplaceable (no alternative link OR routing)", both, "#d73027"),
        ("edge-irreplaceable (D7, cheapest alternative > β)", irr, "#fc8d59"),
        (sq_label, sq, "#dfb515"),
    ]


def _zoom_links(R, squeeze_max=0.5, south_of_frac=0.40, pad_km=35):
    """Frame selection shared by the zoom figures: the routing-regime links whose corridor land
    lies in the lower window, plus the axis extent that frames them."""
    e, classes = _routing_classes(R, squeeze_max)
    owner = np.nan_to_num(R.edge_owner.values, nan=-1).astype(int)
    order = {k: i for i, k in enumerate(R.edges.index)}
    H = R.shape[0]
    links = []
    for lbl, ks, col in classes:
        for k in ks:
            cells = np.argwhere(owner == order[k])
            if len(cells) and cells[:, 0].mean() >= south_of_frac * H:
                links.append((k, col, cells))
    assert links, "no routing-regime links in the southern window -- lower south_of_frac"
    rr = np.concatenate([c[:, 0] for _, _, c in links])
    cc_ = np.concatenate([c[:, 1] for _, _, c in links])
    xs, ys = R.template.x.values, R.template.y.values
    pad = pad_km * 1000.0
    XL = (xs[cc_.min()] - pad, xs[cc_.max()] + pad)
    YL = (ys[rr.max()] - pad, ys[rr.min()] + pad)
    return e, classes, owner, order, links, XL, YL


def routing_problem_cost_zoom(R, squeeze_max=0.5, south_of_frac=0.40, pad_km=35):
    """Triptych on the zoom frame: (1) the movement-cost surface -- the CAUSE of the squeeze --
    (2) the classified links, (3) both together (cost in greys under the class colours). Node
    polygons are drawn as OUTLINES on the cost panels so the surface under and between the
    anchors stays visible (the contact zones are exactly where the orange links live)."""
    e, classes, owner, order, links, XL, YL = _zoom_links(R, squeeze_max, south_of_frac, pad_km)
    parts = gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(R.crs)
    outline = parts.dissolve(by="name_label").reset_index()

    w = 6.2 * (XL[1] - XL[0]) / (YL[1] - YL[0])
    fig, axes = plt.subplots(1, 3, figsize=(3 * w + 3.5, 8.5))
    cost = R.resistance.values

    ax = axes[0]
    _da(R, np.where(cost > 0, cost, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap="magma_r", norm=LogNorm(vmin=1, vmax=1000), add_colorbar=True,
        cbar_kwargs=dict(label="movement cost (4 ordinal classes, log colour)", shrink=0.55))
    outline.boundary.plot(ax=ax, color="#2b6a6a", linewidth=0.7)
    _draw_basemap(R, ax, XL, YL, towns=False)
    ax.set_xlim(*XL); ax.set_ylim(*YL); ax.set_aspect("equal"); ax.set_axis_off()
    ax.set_title("Movement cost (O'Brien) — the cause", fontsize=11)

    ax = axes[1]
    rest = R.corridor & ~np.isin(owner, [order[k] for _, ks, _ in classes for k in ks])
    _da(R, np.where(rest, 1.0, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap=ListedColormap(["#b8c4c9"]), add_colorbar=False)
    for lbl, ks, col in classes:
        m = np.isin(owner, [order[k] for k in ks]) & R.corridor
        if m.any():
            _da(R, np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(
                ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    for layer, col in [(R.pa_mask, PA_COLOR), (R.anch, ANCHOR_COLOR)]:
        _da(R, np.where(layer, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    _draw_basemap(R, ax, XL, YL)
    ax.set_xlim(*XL); ax.set_ylim(*YL); ax.set_aspect("equal"); ax.set_axis_off()
    ax.set_title("Routing-regime links — the classification", fontsize=11)

    ax = axes[2]
    _da(R, np.where(cost > 0, cost, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap="Greys", norm=LogNorm(vmin=1, vmax=1000), add_colorbar=False)
    for lbl, ks, col in classes:
        m = np.isin(owner, [order[k] for k in ks]) & R.corridor
        if m.any():
            _da(R, np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(
                ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    outline.boundary.plot(ax=ax, color="#2b6a6a", linewidth=0.7)
    xs, ys = R.template.x.values, R.template.y.values
    for n, (k, col, cells) in enumerate(sorted(links, key=lambda t: t[2][:, 0].mean()), 1):
        ax.annotate(str(n), (xs[int(np.median(cells[:, 1]))], ys[int(np.median(cells[:, 0]))]),
                    fontsize=9, fontweight="bold", ha="center", va="center",
                    bbox=dict(boxstyle="circle,pad=0.24", fc="white", ec=col, lw=1.6))
    _draw_basemap(R, ax, XL, YL)
    ax.set_xlim(*XL); ax.set_ylim(*YL); ax.set_aspect("equal"); ax.set_axis_off()
    ax.set_title("Overlay — barriers (grey) under the flagged links", fontsize=11)

    handles = [Patch(color=col, label=lbl) for lbl, _, col in classes]
    handles += [Patch(color="#b8c4c9", label="securing regime"),
                plt.Line2D([0], [0], color="#2b6a6a", lw=1, label="named-area boundaries"),
                plt.Line2D([0], [0], color="0.15", lw=1.0, ls=(0, (6, 3)), label="provincial border")]
    axes[2].legend(handles=handles, loc="lower left", fontsize=8, frameon=True)
    fig.suptitle(f"{R.region_label} — the routing-problem cluster against its cause "
                 f"(link numbers as in routing_problem_zoom)", fontsize=13)
    fig.tight_layout()
    fig.savefig(R.fig_dir / "routing_problem_cost_zoom.png", dpi=150, bbox_inches="tight")
    plt.show()
    return R


def routing_problem_cost_overlay(R, squeeze_max=0.5, south_of_frac=0.40, pad_km=35,
                                 show_securing=False):
    """One figure: the flagged links + anchors HARD-COLOURED over the live movement-cost ramp,
    so the land IN BETWEEN reads as cost values. PAs grey / IPCAs teal / classes solid; the
    securing-regime corridor is omitted by default (show_securing=True adds it in light grey)
    to keep the between-land legible as cost."""
    import matplotlib.patheffects as pe
    e, classes, owner, order, links, XL, YL = _zoom_links(R, squeeze_max, south_of_frac, pad_km)
    xs, ys = R.template.x.values, R.template.y.values

    w = 12.5 * (XL[1] - XL[0]) / (YL[1] - YL[0])
    fig, ax = plt.subplots(figsize=(w + 3.0, 13))
    cost = R.resistance.values
    _da(R, np.where(cost > 0, cost, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap="magma_r", norm=LogNorm(vmin=1, vmax=1000), add_colorbar=True,
        cbar_kwargs=dict(label="movement cost between the hard-coloured land "
                               "(4 ordinal classes, log colour)", shrink=0.5))
    if show_securing:
        rest = R.corridor & ~np.isin(owner, [order[k] for _, ks, _ in classes for k in ks])
        _da(R, np.where(rest, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap(["#c3ced2"]), add_colorbar=False)
    for layer, col in [(R.pa_mask, PA_COLOR), (R.anch, ANCHOR_COLOR)]:
        _da(R, np.where(layer, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    for lbl, ks, col in classes:
        m = np.isin(owner, [order[k] for k in ks]) & R.corridor
        if m.any():
            _da(R, np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(
                ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    ax.set_xlim(*XL); ax.set_ylim(*YL); ax.set_aspect("equal"); ax.set_axis_off()

    # named-area labels + numbered link markers, as in routing_problem_zoom
    from shapely.geometry import box as _box
    frame = _box(XL[0], YL[0], XL[1], YL[1])
    parts = gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(R.crs)
    for _, row in parts.dissolve(by="name_label").reset_index().iterrows():
        clip = row.geometry.intersection(frame)
        if clip.is_empty or clip.area < 25e6:
            continue
        is_ipca = _is_anchor_label(R, row["name_label"])
        pt = clip.representative_point()
        ax.annotate(_short_node_name(row["name_label"], 20), (pt.x, pt.y),
                    fontsize=8.5, ha="center", va="center", fontstyle="italic",
                    color=("#0f4747" if is_ipca else "0.15"),
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
    handles = [Patch(color=col, label=lbl) for lbl, _, col in classes]
    if show_securing:
        handles.append(Patch(color="#c3ced2", label="securing regime"))
    for n, (k, col, cells) in enumerate(sorted(links, key=lambda t: t[2][:, 0].mean()), 1):
        r = e.loc[k]
        ax.annotate(str(n), (xs[int(np.median(cells[:, 1]))], ys[int(np.median(cells[:, 0]))]),
                    fontsize=10, fontweight="bold", ha="center", va="center",
                    bbox=dict(boxstyle="circle,pad=0.28", fc="white", ec=col, lw=1.8))
        handles.append(plt.Line2D([0], [0], marker="o", color="none", markerfacecolor="white",
                                  markeredgecolor=col, markersize=9,
                                  label=f"{n}. {_short_node_name(r['label_i'], 16)} ↔ "
                                        f"{_short_node_name(r['label_j'], 16)}"))
    _draw_basemap(R, ax, XL, YL)
    handles += [Patch(color=PA_COLOR, label="existing PAs"),
                Patch(color=ANCHOR_COLOR, label="proposed IPCAs"),
                plt.Line2D([0], [0], color="0.15", lw=1.0, ls=(0, (6, 3)), label="provincial border")]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.16, 0.5),
              fontsize=8.5, frameon=True)
    ax.set_title(f"{R.region_label} — flagged links over the movement-cost surface\n"
                 f"(anchors + flagged corridors hard-coloured; everything between is cost)",
                 fontsize=12)
    fig.savefig(R.fig_dir / "routing_problem_cost_overlay.png", dpi=160, bbox_inches="tight")
    plt.show()
    return R


def routing_problem_zoom(R, squeeze_max=0.5, south_of_frac=0.40, pad_km=35):
    """Zoom on the southern highlight cluster, with NAMED areas and NUMBERED links.

    Frames the routing-regime links whose corridor land lies in the lower part of the window
    (row centroid below `south_of_frac` of the map height — a display choice, stated in the
    caption); labels every named area intersecting the frame (IPCAs dark teal, PAs grey) and
    marks each highlighted link with a circled number keyed to a legend row carrying the full
    pair, squeeze, backup ratio and absolute replacement cost."""
    import matplotlib.patheffects as pe
    e, classes, owner, order, links, XL, YL = _zoom_links(R, squeeze_max, south_of_frac, pad_km)
    xs, ys = R.template.x.values, R.template.y.values

    fig, ax = plt.subplots(figsize=(13, 13))
    rest = R.corridor & ~np.isin(owner, [order[k] for _, ks, _ in classes for k in ks])
    _da(R, np.where(rest, 1.0, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap=ListedColormap(["#b8c4c9"]), add_colorbar=False)
    for lbl, ks, col in classes:
        m = np.isin(owner, [order[k] for k in ks]) & R.corridor
        if m.any():
            _da(R, np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(
                ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    for layer, col in [(R.pa_mask, PA_COLOR), (R.anch, ANCHOR_COLOR)]:
        _da(R, np.where(layer, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    ax.set_xlim(*XL); ax.set_ylim(*YL)
    ax.set_aspect("equal"); ax.set_axis_off()

    # ---- named-area labels inside the frame ------------------------------------------
    from shapely.geometry import box as _box
    frame = _box(XL[0], YL[0], XL[1], YL[1])
    parts = gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(R.crs)
    names = parts.dissolve(by="name_label").reset_index()
    for _, row in names.iterrows():
        clip = row.geometry.intersection(frame)
        if clip.is_empty or clip.area < 25e6:            # < 25 km² in frame: skip the sliver
            continue
        is_ipca = _is_anchor_label(R, row["name_label"])
        pt = clip.representative_point()
        ax.annotate(_short_node_name(row["name_label"], 20), (pt.x, pt.y),
                    fontsize=8.5, ha="center", va="center", fontstyle="italic",
                    color=("#1a6363" if is_ipca else "0.25"),
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
    _draw_basemap(R, ax, XL, YL)

    # ---- numbered link markers + legend ----------------------------------------------
    handles = [Patch(color=col, label=lbl) for lbl, _, col in classes]
    handles.append(Patch(color="#b8c4c9", label="securing regime"))
    handles.append(plt.Line2D([0], [0], color="0.15", lw=1.0, ls=(0, (6, 3)), label="provincial border"))
    for n, (k, col, cells) in enumerate(sorted(links, key=lambda t: t[2][:, 0].mean()), 1):
        r = e.loc[k]
        cx, cy = xs[int(np.median(cells[:, 1]))], ys[int(np.median(cells[:, 0]))]
        ax.annotate(str(n), (cx, cy), fontsize=10, fontweight="bold", ha="center",
                    va="center",
                    bbox=dict(boxstyle="circle,pad=0.28", fc="white", ec=col, lw=1.8))
        stats = []
        if np.isfinite(r.get("squeeze_idx", np.nan)):
            stats.append(f"squeeze {r['squeeze_idx']:.2f}")
        if pd.notna(r.get("backup_ratio")):
            stats.append(f"alt {r['backup_ratio']:.1f}× (+{(r['backup_ratio']-1)*r['cost']/(10/3):,.0f} km)")
        handles.append(plt.Line2D([0], [0], marker="o", color="none", markerfacecolor="white",
                                  markeredgecolor=col, markersize=9,
                                  label=f"{n}. {_short_node_name(r['label_i'], 16)} ↔ "
                                        f"{_short_node_name(r['label_j'], 16)} — "
                                        + ", ".join(stats)))
    handles += [Patch(color=PA_COLOR, label="existing PAs"),
                Patch(color=ANCHOR_COLOR, label="proposed IPCAs")]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5),
              fontsize=8.5, frameon=True)
    ax.set_title(f"{R.region_label} — the routing-problem cluster (southern window; "
                 f"links numbered north → south)", fontsize=12)
    fig.savefig(R.fig_dir / "routing_problem_zoom.png", dpi=160, bbox_inches="tight")
    plt.show()
    return R


def routing_problem_map(R, squeeze_max=0.5, pad=0.05):
    """THE highlight figure: where connectivity is a ROUTING problem vs a securing problem.

    Corridor land painted by its owning link's regime: both-senses irreplaceable (D7 + D12) in
    red; edge-irreplaceable in orange; SQUEEZED links (squeeze_idx < squeeze_max -- band under
    half its open-ground width) in gold; everything else (the securing regime) muted. Uses
    edge_owner.tif, so each cell is attributed to the link whose priority it carries."""
    e, classes = _routing_classes(R, squeeze_max)
    owner = np.nan_to_num(R.edge_owner.values, nan=-1).astype(int)
    order = {k: i for i, k in enumerate(R.edges.index)}      # owner codes = edge-table row order
    both, irr, sq = (classes[0][1], classes[1][1], classes[2][1])
    XL, YL = _region_extent(R, pad)
    fig, ax = plt.subplots(figsize=(13, 12))
    rest = R.corridor & ~np.isin(owner, [order[k] for lbls, ks, _ in classes for k in ks
                                         if k in order])
    _da(R, np.where(rest, 1.0, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap=ListedColormap(["#b8c4c9"]), add_colorbar=False)
    handles = [Patch(color="#b8c4c9", label="securing regime — corridor land with alternatives")]
    for lbl, ks, col in classes:
        codes = [order[k] for k in ks if k in order]
        m = np.isin(owner, codes) & R.corridor
        if m.any():
            _da(R, np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(
                ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
        handles.append(Patch(color=col, label=f"{lbl}  [{len(ks)} links]"))
    _nodes_overlay(R, ax, XL, YL, R.pa_mask, R.anch)
    handles += [Patch(color=PA_COLOR, label="existing PAs"),
                Patch(color=ANCHOR_COLOR, label="proposed IPCAs")]
    ax.legend(handles=handles, loc="lower left", fontsize=9, frameon=True)
    ax.set_title(f"{R.region_label} — where connectivity is a ROUTING problem\n"
                 f"(everywhere grey, the landscape still offers alternatives — a securing "
                 f"problem)", fontsize=12)
    fig.savefig(R.fig_dir / "routing_problem_map.png", dpi=150, bbox_inches="tight")
    plt.show()
    return e.loc[list(both) + list(irr) + list(sq),
                 ["label_i", "label_j", "squeeze_idx", "cost_per_km", "irreplaceable",
                  "backup_ratio", "n_branches"]].sort_values("squeeze_idx")


def irreplaceability_table(R, out_name="irreplaceability_summary.csv"):
    """The paper's headline edge table: BOTH irreplaceability senses + ensemble presence, one
    row per non-adjacency edge, sorted most-critical first. Joins criticality (D7), route
    branches (D12) and edge presence (D8) -- currently spread across three CSVs."""
    e = _edge_squeeze(R.edges[~R.edges["is_adjacency"]].copy(), R.cutoff)
    if R.edge_freq is not None:
        e = e.join(R.edge_freq, how="left")
    # ABSOLUTE price of the cheapest alternative, in intact-land-km equivalent. The ratio alone
    # misleads for near-touching pairs (direct cost ~1 makes any go-around look enormous):
    # Edziza<->Stikine is 141x but only ~+42 km absolute; Gwillim<->Pine Le Moray is 2.6x but
    # ~+120 km. Report both, always.
    e["backup_extra_km_equiv"] = (((e["backup_ratio"] - 1) * e["cost"]) / (10 / 3)).round(0)
    cols = ["label_i", "label_j", "edge_class", "cost", "in_mst", "ecfb_raw",
            "irreplaceable", "backup_ratio", "backup_extra_km_equiv", "disconnects",
            "n_pairs_lost", "cost_inflation", "n_branches", "route_irreplaceable",
            "width_km", "squeeze_idx", "cost_per_km", "presence_freq", "band_km2"]
    t = (e[[c for c in cols if c in e.columns]]
         .sort_values(["irreplaceable", "route_irreplaceable", "n_pairs_lost", "ecfb_raw"],
                      ascending=[False, False, False, False]))
    t.to_csv(R.run_dir / out_name, encoding="utf-8-sig")
    n_both = int((t["irreplaceable"] & t.get("route_irreplaceable", False)).sum())
    print(f"{out_name}: {len(t)} edges | {int(t.irreplaceable.sum())} edge-irreplaceable (D7) | "
          f"{int(t.get('route_irreplaceable', pd.Series()).sum())} route-irreplaceable (D12) | "
          f"{n_both} BOTH -- the land with no alternative link AND no alternative routing")
    return t


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
        ax.annotate(s["name"].split(".")[0], s["anchor_xy"],
                    fontsize=11, fontweight="bold", ha="center", va="center",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec=s["color"], lw=1.6))
    A.outline.boundary.plot(ax=ax, color="0.35", linewidth=1.0, linestyle="--")
    ax.set_xlim(*XL); ax.set_ylim(*YL); ax.set_aspect("equal"); ax.set_axis_off()
    seg_handles = []
    for s in segs:
        parts = f", {s['parts']} parts" if s["parts"] > 1 else ""
        seg_handles.append(Patch(color=s["color"],
                                 label=f"{s['name'][:52]} ({s['cells']*A.cell_km2:,.0f} km²{parts})"))
    ax.legend(handles=[Patch(color=PA_COLOR, label="existing PAs"),
                       Patch(color=ANCHOR_COLOR, label="proposed IPCAs")] + seg_handles,
              loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=9, frameon=True)
    ax.set_title(f"{A.region_label} — corridor segments (numbered north → south)")
    fig.savefig(A.fig_dir / "corridors_segments_map.png", dpi=150, bbox_inches="tight")
    plt.show()
    return A
