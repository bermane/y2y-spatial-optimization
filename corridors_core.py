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
    "branch_mult", "branch_min_km2", "near_opt_tiers",              # D11/D12
    "part_min_km2", "multisite_designations", "multipart_link_km",  # D16
    "carroll_ref", "audit_objects_dir",                             # D14 / H7
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
    return cfg, cost


# ---- H7 artifacts (D16) -----------------------------------------------------------------
# The canonical node_parts.csv/.gpkg + multipart_review.csv live GIT-TRACKED in
# cfg["audit_objects_dir"] (output_data/ is gitignored and later runs must reproduce the review
# hash). new_run() copies them into the run dir and pins their sha256 in run_config.json, so each
# run dir stays self-contained; load() then reads ONLY the run-dir copies.
_H7_FILES = ("node_parts.csv", "node_parts.gpkg", "multipart_review.csv")


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
    for f in _H7_FILES:
        src = audit_dir / f
        if src.exists():
            h7[f] = {"path": str(_jsonable(src)), "sha256": _sha256(src)}

    if run_id is None:
        used = [int(p.name[6:]) for p in root.glob("v2_run[0-9][0-9][0-9]") if p.is_dir()]
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
            "proposed_pa": cfg["nodes"]["proposed"],
            **h7,                       # H7 artifacts, hash-pinned (D16)
        },
        "overrides": overrides or {},
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
    for d in sorted(root.glob("v2_run*")):
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
    part_min = max(1, int(round(A.cfg["part_min_km2"] / A.cell_km2)))
    names, parts, part_name = [], [], []
    units, unit_kinds, unit_name, unit_parts = [], [], [], []

    for k, ((lbl, mask), kind) in enumerate(zip(A.names_raw, A.kinds_raw)):
        comps, seeds = _split_parts(mask, part_min)
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
def _cwd_all(A, res, masks, cache_dir=None, prefix="node"):
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
    seeds = [[tuple(x) for x in np.argwhere(m)] for m in masks]
    if cache_dir is None:
        cwd = []
        for s in seeds:
            cum, _ = mcp.find_costs(s)
            cwd.append(cum.copy())
        return cwd, mcp

    cache_dir = pathlib.Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for k, s in enumerate(seeds):
        p = cache_dir / f"{prefix}_{k:03d}.npy"
        if not p.exists():
            cum, _ = mcp.find_costs(s)
            np.save(p, cum.astype("float32"))
        paths.append(p)
    return _CwdCache(paths), mcp


class _CwdCache:
    """Lazy list-like view over cached CWD fields; loads one memmap at a time."""

    def __init__(self, paths):
        self.paths = list(paths)

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, k):
        return np.load(self.paths[k], mmap_mode="r")

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
    for n in getattr(A, "names", []):
        h.update(n["treatment"].encode())
    h.update(str(len(A.nodes)).encode())
    return h.hexdigest()[:16]


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


def edge_bands(A, cwd, mcp, edges, cutoff, cutoff_mode="abs", want_slack=True, nmap=None):
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
    for _, e in edges.iterrows():
        i, j, cost_ij = nm(int(e["i"])), nm(int(e["j"])), float(e["cost"])
        eid = e.name
        fi, fj = cwd[i], cwd[j]

        # Centre-line: an explicit traceback, kept from v1. With an absolute cutoff it is no longer
        # strictly needed for continuity, but path_cells is the resistance-independent length
        # yardstick and G1 compares it directly.
        # traceback() reads the LAST find_costs, so re-seed from node i immediately before it.
        n_path = 0
        if cost_ij > 0:
            mcp.find_costs([tuple(x) for x in np.argwhere(A.nodes[i][1])])
            tgt_cells = np.argwhere(A.nodes[j][1])
            target = tuple(tgt_cells[np.argmin(np.asarray(fi)[A.nodes[j][1]])])
            path = mcp.traceback(target)
            paths[eid] = np.asarray(path, dtype=np.int32)
            n_path = len(path)

        field = np.asarray(fi, dtype="float64") + np.asarray(fj, dtype="float64")
        lcp = np.nanmin(field)
        allow = _band_slack(cutoff_mode, cutoff, cost_ij)
        keep = np.isfinite(field) & (field <= lcp + allow)
        if n_path:
            keep[paths[eid][:, 0], paths[eid][:, 1]] = True
        idx = np.flatnonzero(keep.ravel())
        bands[eid] = idx.astype(np.int32)
        if want_slack:
            slack[eid] = (field.ravel()[idx] - lcp).astype("float32")
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
                             ecfb_raw=np.nan, ecfb_norm=np.nan,
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
    if cache:
        # A.cfg comes back from run_config.json as strings; joining under PROJECT_DIR keeps
        # absolute paths absolute (pathlib: an absolute right side wins) and fixes relative ones.
        gdir = config.PROJECT_DIR / pathlib.Path(A.cfg["grid"]["dir"])
        cache_dir = pathlib.Path(gdir) / "cwd_cache" / _resistance_sha(A)
        hit = cache_dir.exists() and len(list(cache_dir.glob("part_*.npy"))) == len(A.parts)
        print(f"cost-weighted distance from {len(A.parts)} seed parts "
              f"({'cache HIT' if hit else 'computing'}: {cache_dir.name})")
    A.cwd_parts, A.mcp = _cwd_all(A, A.resistance_arr, [m for _, m in A.parts],
                                  cache_dir, prefix="part")

    # ---- derive per-UNIT fields (min over the unit's parts) ---------------------------
    if cache:
        upaths = []
        for u in range(len(A.nodes)):
            pidx = A.unit_parts[u]
            if len(pidx) == 1:
                upaths.append(A.cwd_parts.paths[pidx[0]])
            else:
                p = cache_dir / f"unit_{u:03d}.npy"
                if not p.exists():
                    fld = np.asarray(A.cwd_parts[pidx[0]], dtype="float32").copy()
                    for pi in pidx[1:]:
                        np.minimum(fld, np.asarray(A.cwd_parts[pi], dtype="float32"), out=fld)
                    np.save(p, fld)
                upaths.append(p)
        A.cwd = _CwdCache(upaths)
        print(f"  cache {A.cwd_parts.nbytes_on_disk/1e9:.1f} GB on disk, one field resident at a time")
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
    A.graph, A.edges = cg.build(A.D, labels, A.kinds, beta=beta, verbose=verbose)
    A.edges["edge_class"] = np.where(A.edges["is_adjacency"], "adjacency", "inter")

    A.bands, A.slack, A.paths, A.band_meta = edge_bands(
        A, A.cwd, A.mcp, A.edges, cutoff, cutoff_mode)

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
    A.rec["calibration_result"] = {"cwd_cutoff_abs": float(cutoff),
                                   "area_km2": (None if area_km2 is None else float(area_km2)),
                                   "target_km2": A.cfg.get("calibration", {}).get("target_km2")}
    (A.run_dir / "run_config.json").write_text(json.dumps(A.rec, indent=2, ensure_ascii=False))
    print(f"cwd_cutoff_abs = {cutoff:,.1f} written into {A.run_id}/run_config.json")
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

    # Tiers: percentiles OF SLACK over the union band at 2x cutoff (== cells with min-slack
    # <= 2x cutoff, exactly the axis-B 2x member's union). Cells outside that domain but routable
    # fall to "occasional" (queued clarification 3).
    t = A.cfg["near_opt_tiers"]
    dom = no[np.isfinite(no) & (no <= 2.0 * A.cutoff)]
    thr = {k: float(np.percentile(dom, v)) for k, v in t.items() if v < 100}
    ordered = sorted(thr.items(), key=lambda kv: kv[1])
    assert all(a[1] <= b[1] for a, b in zip(ordered, ordered[1:])), f"G10: tiers not monotone {thr}"
    cls = np.zeros(A.shape, "uint8")
    cls[A.pu] = len(ordered) + 1                                   # occasional = rest of routable
    # assign the tightest tier last so the smallest threshold wins
    for c, (name, v) in list(enumerate(ordered, start=1))[::-1]:
        cls[np.isfinite(no) & (no <= v)] = c
    cls[~A.pu] = 0

    A.near_opt, A.near_opt_owner, A.near_opt_class, A.near_opt_thresholds = \
        no.astype("float32"), owner, cls, thr
    print(f"near-optimality surface over {int(A.pu.sum()):,} routable cells "
          f"(tier domain = union band at 2x cutoff, {dom.size:,} cells)")
    for c, (name, v) in enumerate(ordered, start=1):
        print(f"  {name:12s} (slack <= {v:>12,.0f} = p{t[name]:>2}): "
              f"{int((cls == c).sum())*A.cell_km2:>9,.0f} km²")
    print(f"  {'occasional':12s} (rest of routable):        "
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
    bm, bmin = A.cfg["branch_mult"], A.cfg["branch_min_km2"]
    cutoff_b = bm * A.cutoff
    min_cells = max(1, int(round(bmin / A.cell_km2)))
    eids = [e for e in A.edges.index
            if A.edges.loc[e, "cost"] > 0 and not A.edges.loc[e, "is_adjacency"]]

    lab_out = np.zeros(A.shape, "int32")
    lab_pri = np.full(A.shape, np.inf, "float32")     # overlap resolution: lower min_slack wins
    rows, idx_store = [], {}
    n_dropped = 0
    bid = 0
    struct = np.ones((3, 3), int)
    for eid in eids:
        e = A.edges.loc[eid]
        idx, sl = A.bands[eid], A.slack[eid]
        keep = idx[sl <= cutoff_b]
        m = np.zeros(A.shape[0] * A.shape[1], bool)
        m[keep] = True
        m = m.reshape(A.shape)

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
            if cells < min_cells:
                n_dropped += 1
                continue
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
        A.edges["n_branches"] = per_edge.reindex(A.edges.index).fillna(0).astype(int)
        A.edges["route_irreplaceable"] = A.edges["n_branches"] == 1
    A.branches, A.branch_idx = br, idx_store
    A.branch_label = lab_out

    n_multi = int((A.edges.get("n_branches", pd.Series(dtype=int)) > 1).sum())
    n_route_irr = int(A.edges.get("route_irreplaceable", pd.Series(dtype=bool)).sum())
    print(f"route branches @ {bm:g}x cutoff ({cutoff_b:,.0f}): {len(br)} branches over "
          f"{len(eids)} edges | {n_route_irr} ROUTE-irreplaceable edges, {n_multi} with "
          f"alternatives | {n_dropped} slivers < {bmin} km² dropped")
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
    return A


# ================= per-branch values table (D13/D14) =================
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
        ref = raw[routable_1k & np.isfinite(raw)]
        order = np.argsort(ref)
        # percentile transform over the ROUTABLE audit area
        def _pctl(vals):
            v = vals[np.isfinite(vals)]
            if not v.size:
                return np.nan
            return float(100.0 * np.searchsorted(ref[order], v, side="right").mean() / ref.size)
        pct_grid = _pctl

    rows, g11 = [], []
    for r in A.branches.itertuples():
        m = np.zeros(A.shape[0] * A.shape[1], bool)
        m[A.branch_idx[r.branch]] = True
        m = m.reshape(A.shape)
        audit = _to_audit(A, m)
        a300 = r.cells * A.cell_km2
        a1k = int(audit.sum()) * P.cell_km2
        rel = abs(a1k - a300) / max(a300, 1e-9)
        g11.append((r.branch_id, a300, a1k, rel))
        if not audit.any():
            print(f"  {r.branch_id}: too narrow for the 1 km audit grid -- values row skipped")
            continue
        prof, contrib, eff, rawv = rc.mask_profile(P, audit)
        e = A.edges.loc[r.edge_id]
        row = dict(branch_id=r.branch_id, edge_id=r.edge_id, edge_class=r.edge_class,
                   label_i=e["label_i"], label_j=e["label_j"],
                   area_km2=round(a300, 1), area_km2_audit=round(a1k, 1),
                   min_slack=r.min_slack, mean_slack=r.mean_slack,
                   n_branches=int(e.get("n_branches", 1)),
                   route_irreplaceable=bool(e.get("route_irreplaceable", False)),
                   edge_irreplaceable=bool(e.get("irreplaceable", False)),
                   edge_cost=float(e["cost"]), ecfb_raw=e.get("ecfb_raw"))
        for j, ax in enumerate(P.axes_labels):
            row[f"{ax} | richness"] = round(prof[j], 3)
            row[f"{ax} | contribution %"] = round(contrib[j], 4)
            row[f"{ax} | efficiency"] = round(eff[j], 4)
        if pct_grid is not None:
            vals = P.cont_raw[carroll_k][audit]
            row["carroll2018_pctl"] = round(pct_grid(vals), 1)
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
               "Y2Y-wide alternatives table for readability only. carroll2018_pctl is an audit "
               "column (D14): RCP 8.5 late-century only, shares anthropogenic signal with the "
               "cost surface; no routing is climate-informed.")
    (dst / "alternatives_branches.meta.json").write_text(json.dumps(
        dict(caption=caption, row_unit="edge x route branch",
             column_spec="results_core.RAW_SPEC / mask_profile (imported, not redefined)",
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
    print(f"G0 OK (re-baselined): {len(A.names)} names ({A.n_dedupe_merges} dedupe merges) | "
          f"{len(A.parts)} seed parts -> {len(A.nodes)} routing units | "
          f"review sha256 {rev.get('sha256', 'MISSING')[:12]}")
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
                 "n_branches", "route_irreplaceable", "band_km2", "centreline_km"]
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
        n_ipca=sum(k == "ipca" for k in A.kinds),
        n_existing_pa=sum(k == "pa" for k in A.kinds),
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

    ax = axes[0]
    for layer, col in [(pa_mask, PA_COLOR), (anch, ANCHOR_COLOR), (A.corridor, CORRIDOR_COLOR)]:
        _da(A, np.where(layer, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    A.outline.boundary.plot(ax=ax, color="0.35", linewidth=1.0, linestyle="--")
    _frame_region(A, ax)
    ax.legend(handles=[Patch(color=PA_COLOR, label="existing PAs (nodes)"),
                       Patch(color=ANCHOR_COLOR, label="proposed IPCAs (nodes)"),
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
        ax3.legend(handles=[Patch(color=PA_COLOR, label="existing PAs"),
                            Patch(color=ANCHOR_COLOR, label="proposed IPCAs")],
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
    for m, k in src:
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
