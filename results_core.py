"""Shared results-analysis engine for the sub-regional analyses (04a / 04b / 04c).

One function per 04 view, so each thin 04x notebook keeps cell-by-cell figures/tables. Every
function takes the context `A` built by `load(analysis)`; the per-analysis knobs come from
`config.ANALYSES[key]` (results_subdir) + `config.RESULTS_04[key]` (region label, benchmark
block, cluster-select, manual area). It hard-codes no analysis specifics.

Denominators: contribution / efficiency are shares of the FULL Y2Y region totals (read off the
whole aligned stack), and area% is a share of the full Y2Y PU count -- so "% of Y2Y" is
literally correct for every analysis (a sub-region area reads as its share of the whole
corridor). Ported cell-for-cell from 04_results_analysis.ipynb so 04a reproduces its figures.
"""
import json
import types
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import rioxarray
import xarray as xr
import geopandas as gpd
from scipy import ndimage
from scipy.stats import spearmanr
from rasterio.enums import Resampling
from rasterio.features import rasterize
import pyproj

import config

# tab10: 10 saturated, well-separated hues, no pale twins (shared by maps AND star plots).
CLUSTER_CMAP = plt.get_cmap("tab10")
PA_COLOR = "0.6"          # existing protected areas (map backdrop)
ANCHOR_COLOR = "#4f9d9d"  # committed anchors (e.g. draft IPCAs) -- muted teal, distinct from
                          # the grey PAs, the wheat "other allocation" and the tab10 clusters
NEW_ALLOC_COLOR = "#ecdcae"   # solver-selected land that is NOT already protected ("new allocation").
                              # One constant so the clusters map and the benchmark map read as the
                              # same quantity -- the benchmark map otherwise showed parks with no
                              # indication of where the run actually wants to expand.


class _NS(types.SimpleNamespace):
    """SimpleNamespace with a ONE-LINE repr.

    Every view function ends `return A` so calls can chain, and Jupyter echoes that return value
    after each cell — under the default repr that dumps the whole manifest, run summary and every
    cached stack/table after every single cell."""

    def __repr__(self):
        bits = [str(getattr(self, "analysis", "?"))]
        s = getattr(self, "summary", None)
        if s:
            bits.append(str(s.get("run_tag", "")))
        if getattr(self, "portfolio", None) is not None:
            bits.append(f"{self.portfolio.rio.width}x{self.portfolio.rio.height}")
        if getattr(self, "NEW", None):
            bits.append(f"{len(self.NEW['ids'])} new clusters")
        return f"<results {' | '.join(b for b in bits if b)}>"

# Per-objective metadata: display name, native unit (raw table), raw-aggregation rule, and the
# RAW-table decimal places. Decimals are PER ROW because the rows span wildly different scales:
# one shared dp would round a 0-1 intactness index to a flat "1.0" while carbon needs none.
RAW_SPEC = {
    "human_modification":           ("Intactness",             "intactness 0-1 (mean; 1-gHM)",              "mean",       3),
    "transboundary_connectivity":   ("Connectivity",           "current density, amperes (mean)",          "mean",       2),
    "climate_corridors":            ("Climate corridors",      "current-flow centrality, amperes (mean)",  "mean",       2),
    "climate_type_macrorefugia":    ("Climate refugia",        "km/yr (mean; refugial value = vmax - backward velocity)", "mean", 2),
    "irrecoverable_carbon_biomass": ("Carbon: biomass",        "t C (total)",                              "tonnes",     0),
    "irrecoverable_carbon_m_soc":   ("Carbon: mineral soil",   "t C (total)",                              "tonnes",     0),
    "aoh_richness_mammals":         ("Mammal richness",        "species/cell (mean)",                      "mean",       1),
    "aoh_richness_birds":           ("Bird richness",          "species/cell (mean)",                      "mean",       1),
    "EFG_mean":                     ("Ecosystem groups (EFG)", None,                                       "efg_groups", 0),
}
# fmt drives BOTH the radial tick labels and the composite in each star-plot subtitle.
# richness is a 0-1 index and efficiency is small (0-0.3), so both need 3 dp for depth: at 2 dp
# 108 richness values collapsed to 66 distinct (Banff 0.498 / NEW-90 0.497 / NEW-445 0.499 all
# read "0.50"), and efficiency ticks mis-rendered (0.075 -> "0.08", 0.225 -> "0.23").
# contribution stays at 1 dp -- it is a 0-100 % and the team asked for fewer decimals there.
METRIC_SPEC = {
    "richness":     dict(key="profs",   unit="relative richness (0-1, region 5-95 pctile)", rmax=1.0,  fmt="{:.3f}"),
    "contribution": dict(key="contrib", unit="% of Y2Y region total",                       rmax=None, fmt="{:.1f}"),
    "efficiency":   dict(key="eff",     unit="% of Y2Y total per 1,000 km^2",                rmax=None, fmt="{:.3f}"),
}


# ================= setup =================
def load(analysis, run=None):
    """Light setup: locate the run, read manifest/summary/representation, set the region label
    and the map outline (the ROI polygon for sub-regions, the full Y2Y boundary for y2y).

    `run` names the output folder to read, overriding `config.ANALYSES[analysis]["results_subdir"]`.
    REQUIRED when the solve came from 03a's RUN LEVER, because that lever patches `results_subdir`
    into the R run context only -- config.py still points at whatever it pointed at before, so
    without this argument 04 would quietly analyse a DIFFERENT (older) solve than the one just
    produced and every figure would be silently stale. Pass the same string the lever built,
    e.g. rc.load("y2y", run="iter7_y2y_r1_density5x")."""
    a04 = config.RESULTS_04[analysis]
    subdir = run or config.ANALYSES[analysis]["results_subdir"]
    run_dir = config.RESULTS_DIR / subdir
    # Test for run_summary.json, NOT for the directory: 03a's lever (pr_override) creates the
    # output folder eagerly when you run the lever cell, so an EMPTY folder exists as soon as a
    # run is named and long before it is solved. A bare directory check passes on that and the
    # failure then surfaces as a confusing raw "no such file" three lines later.
    if not (run_dir / "run_summary.json").exists():
        # List what IS on disk: during a sweep the usual cause is a typo'd or not-yet-solved run
        # name, and guessing from a bare "not found" is needless friction.
        avail = sorted(p.name for p in config.RESULTS_DIR.glob("*") if (p / "run_summary.json").exists())
        state = "exists but is EMPTY (named but not yet solved)" if run_dir.exists() else "does not exist"
        solve_nb = "analyses/y2y/02_solve.ipynb" if analysis == "y2y" else f"03{{b,c}} for {analysis}"
        raise FileNotFoundError(
            f"no solved run at {run_dir} -- it {state}.\n"
            f"  Run {solve_nb} through its write cell first, or set RUN to "
            f"one of: {', '.join(avail) if avail else '(none)'}")
    fig_dir = run_dir / "figures"; fig_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(Path(config.MANIFEST_PATH).read_text())
    summary = json.loads((run_dir / "run_summary.json").read_text())
    rep = pd.read_csv(run_dir / "portfolio_representation.csv")
    REL = "relative_held" if "relative_held" in rep.columns else \
          next(c for c in rep.columns if c.startswith("relative"))
    is_prop = summary["params"].get("decision_type") == "proportion"

    # Map outline (solid black): sub-region ROI polygon if present, else the full Y2Y boundary.
    roi_gpkg = config.HANDOFF_DIR / f"roi_{analysis}.gpkg"
    outline = gpd.read_file(roi_gpkg if roi_gpkg.exists() else config.CORRIDOR_REF).to_crs(config.TARGET_CRS)
    # Optional context outline (dashed grey), e.g. the Alberta boundary on the foothills maps.
    ctx_path = a04.get("context_outline")
    context = gpd.read_file(ctx_path).to_crs(config.TARGET_CRS) if ctx_path else None

    print(f"analysis={analysis} | run={summary['run_tag']} | objective={summary['objective']} | "
          f"{'proportion/LP' if is_prop else 'binary portfolio'}")
    print(f"region={a04['region_label']} | figures -> {fig_dir.relative_to(config.PROJECT_DIR)}")

    return _NS(
        analysis=analysis, a04=a04, run_dir=run_dir, fig_dir=fig_dir,
        manifest=manifest, summary=summary, rep=rep, REL=REL, is_prop=is_prop,
        region_label=a04["region_label"], outline=outline,
        outline_label=a04.get("outline_label", f"{a04['region_label']} boundary"),
        context=context, context_label=a04.get("context_label"),
        cont=[L["name"] for L in manifest["layers"] if L["role"] == "feature_continuous"],
        efg=[L["name"] for L in manifest["layers"] if L["role"] == "feature_efg"])


def load_rasters(A):
    """Load portfolio + selection-frequency rasters; note if the grid was coarsened."""
    A.portfolio = rioxarray.open_rasterio(A.run_dir / "portfolio.tif", masked=True)
    A.freq = rioxarray.open_rasterio(A.run_dir / "selection_frequency.tif", masked=True).squeeze()
    A.n_alt = A.portfolio.sizes["band"]
    A.pas = gpd.read_file(config.PA_VECTOR).to_crs(config.TARGET_CRS)
    print(f"portfolio: {A.n_alt} solution(s) | grid {A.portfolio.rio.width} x {A.portfolio.rio.height}")
    if A.is_prop:
        print(f"allocation surface: {float(A.freq.min()):.2f}..{float(A.freq.max()):.2f}")
    return A


# ================= map framing (shared) =================
def _outline_handles(A):
    """Legend handles labelling the map's boundary lines (ROI outline + optional context)."""
    h = [Line2D([0], [0], color="black", lw=0.9, label=A.outline_label)]
    if A.context is not None:
        h.append(Line2D([0], [0], color="0.35", lw=1.1, ls="--", label=A.context_label))
    return h


def _locked_mask(A, ref):
    """(existing_PA_mask, anchor_mask, locked_mask, label) on `ref`'s grid.

    `anchor_mask` is the rasterized lock-in vector (e.g. the draft IPCAs) on its own, so maps can
    draw existing PAs and committed anchors in DIFFERENT colours; it is all-False when the
    analysis locks only the PA mask.

    `locked` is what THIS analysis actually locked in, per the run's params: "pa_mask" = existing
    PAs, "vector" = rasterized anchors (e.g. the draft IPCAs), "both" = the union. NEW candidate
    areas are `selected & ~locked` -- using the existing-PA raster alone would mislabel locked
    draft anchors as "new", since drafts are not in mask_protected_areas.tif."""
    pa = (rioxarray.open_rasterio(config.HANDOFF_DIR / "mask_protected_areas.tif", masked=True)
          .squeeze().rio.reproject_match(ref).values >= 0.5)
    li = A.summary["params"].get("lock_in") or {"source": "pa_mask"}
    src = li.get("source", "pa_mask")
    anchors = np.zeros(pa.shape, dtype=bool)
    if src in ("vector", "both") and li.get("vector_path"):
        v = gpd.read_file(config.PROJECT_DIR / li["vector_path"]).to_crs(ref.rio.crs)
        anchors = rasterize([(g, 1) for g in v.geometry], out_shape=ref.shape[-2:],
                            transform=ref.rio.transform(), fill=0, dtype="uint8").astype(bool)
    locked = np.zeros(pa.shape, dtype=bool)
    if src in ("pa_mask", "both"):
        locked |= pa
    locked |= anchors
    label = ("existing PAs + committed anchors" if src == "both"
             else "locked-in anchors" if src == "vector" else "existing protected areas")
    return pa, anchors, locked, label


def _frame(A, ax):
    """Draw the ROI outline (solid black) + optional context outline (dashed grey).

    Framing (RESULTS_04[key]["frame"]):
      "window" (default) -> keep the map on the analysis window (context can't zoom it out);
      "pad"              -> zoom out by `frame_pad` (fraction of the window span) for breathing
                            room / surrounding context, WITHOUT jumping to the full context extent
                            (the context outline is then simply clipped by the view -- fine);
      "context"          -> zoom OUT to the whole context extent (e.g. all of Alberta).
    Axis direction (rioxarray may invert y) is preserved in every case."""
    xlim, ylim = ax.get_xlim(), ax.get_ylim()                 # window extent from the raster
    A.outline.boundary.plot(ax=ax, color="black", linewidth=0.9)
    if A.context is not None:
        A.context.boundary.plot(ax=ax, color="0.35", linewidth=1.1, linestyle="--")

    def _oriented(lo, hi, ref):                               # keep the axis' own direction
        return (lo, hi) if ref[0] <= ref[1] else (hi, lo)

    mode = A.a04.get("frame", "window")
    if A.context is not None and mode == "context":
        minx, miny, maxx, maxy = A.context.total_bounds
        m = 0.03 * max(maxx - minx, maxy - miny)              # small margin
        ax.set_xlim(_oriented(minx - m, maxx + m, xlim))
        ax.set_ylim(_oriented(miny - m, maxy + m, ylim))
    elif mode == "pad":
        f = A.a04.get("frame_pad", 0.25)
        for lim, setter in ((xlim, ax.set_xlim), (ylim, ax.set_ylim)):
            lo, hi = min(lim), max(lim); d = (hi - lo) * f
            setter(_oriented(lo - d, hi + d, lim))
    else:
        ax.set_xlim(xlim); ax.set_ylim(ylim)                  # stay framed on the window


# ================= whole-network views =================
def radar(A):
    """Captured-fraction radar (per input) with the budget area-share reference ring."""
    obj = A.summary["objective"]; budget = A.summary["params"]["budget_pct"]
    target = A.summary["params"]["target_pct"]; REL = A.REL

    def prof(df):
        held = df.set_index("feature")[REL]
        return [float(held.get(n, np.nan)) for n in A.cont] + [float(held.reindex(A.efg).mean())]

    labels = [n.replace("_", " ") for n in A.cont] + ["EFG (mean)"]
    ang = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist(); ang += ang[:1]
    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True))
    for alt, df in A.rep.groupby("alternative"):
        v = prof(df); v += v[:1]
        ax.plot(ang, v, linewidth=1.4, label=alt); ax.fill(ang, v, alpha=0.05)
    ax.plot(ang, [budget]*len(ang), "--", color="0.4", linewidth=1, label=f"area share {budget:.0%}")
    if obj == "min_set":
        ax.plot(ang, [target]*len(ang), ":", color="0.6", linewidth=1, label=f"target {target:.0%}")
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(0, max(1.0, float(A.rep[REL].max())))
    head = ("Representation per feature (min-set)" if obj == "min_set"
            else "Fraction of each input's full value captured (one solution)" if A.n_alt == 1
            else f"Captured fraction per input across {A.n_alt} alternatives")
    ax.set_title(f"{A.region_label} — {head}\n(dashed = {budget:.0%} area-share reference)", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.30, 1.10), fontsize=7)
    fig.savefig(A.fig_dir / "radar_representation.png", dpi=150, bbox_inches="tight"); plt.show()


def allocation_map(A):
    """Allocation surface (proportion) or selection frequency (binary), PAs + outline overlaid."""
    if A.is_prop:
        cmap, cbar, title, out = "viridis", "allocation (proportion of cell selected)", \
            "Allocation surface (min-shortfall LP): priority per cell", "priority_allocation.png"
    else:
        cmap, cbar, title, out = "magma", f"times selected (of {A.n_alt})", \
            "Selection frequency across the near-optimal suite", "priority_selection_frequency.png"
    fig, ax = plt.subplots(figsize=(7, 12))
    A.freq.plot.imshow(ax=ax, cmap=cmap, add_colorbar=True, cbar_kwargs=dict(label=cbar, shrink=0.5))
    A.pas.boundary.plot(ax=ax, color="cyan", linewidth=0.3, alpha=0.7)
    _frame(A, ax)
    ax.legend(handles=_outline_handles(A) + [Line2D([0], [0], color="cyan", lw=1, label="existing PAs")],
              loc="lower left", fontsize=8, frameon=True)
    ax.set_title(f"{A.region_label} — {title}"); ax.set_aspect("equal"); ax.set_axis_off()
    fig.savefig(A.fig_dir / out, dpi=150, bbox_inches="tight"); plt.show()


def solution_maps(A):
    """Up to two representative solution layers."""
    k = min(2, A.n_alt)
    fig, axes = plt.subplots(1, k, figsize=(6.5*k, 11)); axes = np.atleast_1d(axes)
    for i in range(k):
        ax = axes[i]
        A.portfolio.isel(band=i).plot.imshow(ax=ax, cmap="Greens", add_colorbar=A.is_prop,
            cbar_kwargs=dict(label="allocation", shrink=0.4) if A.is_prop else None)
        A.pas.boundary.plot(ax=ax, color="cyan", linewidth=0.3, alpha=0.6)
        _frame(A, ax)
        ax.legend(handles=_outline_handles(A), loc="lower left", fontsize=7, frameon=True)
        ax.set_title("LP solution (allocation)" if (A.is_prop and A.n_alt == 1) else f"alternative {i+1}")
        ax.set_aspect("equal"); ax.set_axis_off()
    fig.suptitle(f"{A.region_label} — " + ("proportion selected per cell" if (A.is_prop and A.n_alt == 1)
                 else "representative near-optimal alternatives"))
    fig.savefig(A.fig_dir / "solution_maps.png", dpi=150, bbox_inches="tight"); plt.show()


def existing_vs_new(A):
    """Split selected cells into locked-in PAs vs newly allocated."""
    sol = A.portfolio.isel(band=0)
    pa, anchors, locked, _ = _locked_mask(A, A.freq)      # what this analysis actually locked in
    new_alloc = (sol.fillna(0).values > 0.5) & ~locked
    has_anchors = bool(anchors.any())
    anchor_label = A.a04.get("anchor_label", "committed anchors")
    # 1 = existing PA, 2 = new allocation, 3 = committed anchors (drawn distinctly, over the PAs)
    cat = np.full(A.freq.shape, np.nan, dtype="float32")
    cat[pa & ~anchors] = 1.0
    cat[new_alloc] = 2.0
    if has_anchors:
        cat[anchors] = 3.0
    colors = [PA_COLOR, "#1b9e77"] + ([ANCHOR_COLOR] if has_anchors else [])
    fig, ax = plt.subplots(figsize=(7, 12))
    A.freq.copy(data=cat).plot.imshow(ax=ax, cmap=ListedColormap(colors), vmin=1, vmax=len(colors),
                                      add_colorbar=False)
    _frame(A, ax)
    handles = [Patch(color=PA_COLOR, label="existing protected area")]
    if has_anchors:
        handles.append(Patch(color=ANCHOR_COLOR, label=anchor_label))
    handles.append(Patch(color="#1b9e77", label="new allocation"))
    ax.legend(handles=handles + _outline_handles(A), loc="lower left", fontsize=9, frameon=True)
    ax.set_title(f"{A.region_label} — locked-in protection vs new allocation\n"
                 f"locked: {int(locked.sum()):,} cells"
                 + (f" (PA {int((pa & ~anchors).sum()):,} + anchors {int(anchors.sum()):,})" if has_anchors else "")
                 + f" | new: {int(new_alloc.sum()):,} cells")
    ax.set_aspect("equal"); ax.set_axis_off()
    fig.savefig(A.fig_dir / "existing_vs_new.png", dpi=150, bbox_inches="tight"); plt.show()


def tradeoff(A):
    """Per-solution stats + headline area/lock-in numbers."""
    stats = pd.DataFrame(A.summary["per_alternative"])
    print("Per-solution summary:"); print(stats.to_string(index=False))
    n_pu = A.summary["n_planning_units"]; n_locked = A.summary["n_locked_in"]
    print(f"\nwindow planning units : {n_pu:,}")
    print(f"area budget (cells)   : {A.summary['budget_cells']:,} ({A.summary['params']['budget_pct']:.0%})")
    print(f"locked-in             : {n_locked:,} ({100*n_locked/n_pu:.1f}% of window)")
    if A.n_alt == 1:
        print(f"area selected         : {stats['pct_region'].iloc[0]:.1f}% of window")


# ================= stacks + per-area profiling =================
def _read_match(A, path):
    """Feature -> array on the SOLUTION grid (cropped window)."""
    r = rioxarray.open_rasterio(config.PROJECT_DIR / path, masked=True).squeeze()
    return r.rio.reproject_match(A.sol0, resampling=Resampling.average).values.astype("float32")


def _region_total(A, path):
    """Full-Y2Y total of a feature at the solution's resolution (denominator for '% of Y2Y')."""
    r = rioxarray.open_rasterio(config.PROJECT_DIR / path, masked=True).squeeze()
    if A.agg > 1:
        r = r.coarsen(x=A.agg, y=A.agg, boundary="trim").mean()
    return float(np.nansum(r.values))


def _scaled(A, path):
    a = _read_match(A, path)
    lo, hi = np.nanpercentile(a, 5), np.nanpercentile(a, 95)
    return np.clip((a - lo) / (hi - lo if hi > lo else 1.0), 0, 1)


def mask_profile(A, m):
    """(richness, contribution, efficiency, raw) vectors for boolean mask m. ONE definition
    shared by NEW clusters, the benchmark areas and the manual area."""
    prof = [float(np.nanmean(A.cont_stack[k][m])) for k in range(len(A.cont))]
    prof.append(float(np.nanmean(A.efg_stack[:, m])))
    contrib = [100.0 * np.nansum(A.cont_raw[k][m]) / A.cont_region[k] for k in range(len(A.cont))]
    contrib.append(100.0 * float(np.nanmean(np.nansum(A.efg_raw[:, m], axis=1) / A.efg_region)))
    area = int(m.sum()) * A.cell_km2
    eff = [x / area * 1000.0 for x in contrib]
    raw = []
    for k, name in enumerate(A.cont):
        vals = A.cont_raw[k][m]
        raw.append(float(np.nansum(vals) * A.cell_ha) if RAW_SPEC[name][2] == "tonnes"
                   else float(np.nanmean(vals)))
    raw.append(int(np.sum([bool(np.any(A.efg_raw[j][m] > 0)) for j in range(len(A.efg))])))
    return prof, contrib, eff, raw


def build_stacks(A):
    """Feature stacks (window-aligned) + FULL-Y2Y region totals + masks + NEW clusters +
    the benchmark block + the shared efficiency scale (+ the manual area, if any)."""
    A.agg = A.summary["params"]["prototype_agg_factor"]
    A.sol0 = A.portfolio.isel(band=0)
    rx, ry = A.sol0.rio.resolution(); A.cell_km2 = abs(rx*ry)/1e6; A.cell_ha = A.cell_km2*100.0
    A.crs = A.sol0.rio.crs
    A.axes_labels = [n.replace("_", " ") for n in A.cont] + ["EFG (mean)"]
    A.axis_cols = list(A.cont) + ["EFG_mean"]
    A.OBJ_DISPLAY = [RAW_SPEC[c][0] for c in A.axis_cols]
    A.OBJ_UNIT = [RAW_SPEC[c][1] if RAW_SPEC[c][1] else f"groups present (of {len(A.efg)})" for c in A.axis_cols]
    A.TO_LATLON = pyproj.Transformer.from_crs(A.crs, "EPSG:4326", always_xy=True)

    cont_layers = [L for L in A.manifest["layers"] if L["role"] == "feature_continuous"]
    efg_layers  = [L for L in A.manifest["layers"] if L["role"] == "feature_efg"]
    A.cont_stack = np.stack([_scaled(A, L["path"]) for L in cont_layers])   # 0-1 richness (window)
    A.efg_stack  = np.stack([_scaled(A, L["path"]) for L in efg_layers])
    A.cont_raw = np.stack([_read_match(A, L["path"]) for L in cont_layers]) # native (window)
    A.efg_raw  = np.stack([_read_match(A, L["path"]) for L in efg_layers])
    A.cont_region = np.array([_region_total(A, L["path"]) for L in cont_layers])  # FULL Y2Y totals
    A.cont_region[A.cont_region == 0] = np.nan
    A.efg_region = np.array([_region_total(A, L["path"]) for L in efg_layers])
    A.efg_region[A.efg_region == 0] = np.nan
    A.n_region_full = _region_total(A, cost_path(A))                        # full Y2Y PU count

    # The analysis PU = cells the solve actually ran on. sol0 is NaN outside the ROI mask, so it
    # must be ANDed in: the feature rasters are only reproject_matched (grid-aligned), NOT masked,
    # so feature-validity alone spills outside a masked window.
    A.valid_all = np.isfinite(A.sol0.values) & np.isfinite(A.cont_raw).all(axis=0)
    sel = A.sol0.fillna(0).values > 0.5
    # NEW candidate areas exclude everything this analysis LOCKED (existing PAs and/or anchors),
    # so locked draft IPCAs are never mislabelled as new candidates.
    A.pa_on, A.anchors, A.locked, A.locked_label = _locked_mask(A, A.sol0)
    A.new_mask = sel & ~A.locked

    A.MIN_CELLS = config.CLUSTER_MIN_CELLS; A.MAX_PLOTS = config.CLUSTER_MAX_PLOTS
    A.cluster_select = A.a04["cluster_select"]
    A.NEW = _cluster_profile(A, A.new_mask, "new candidate areas")
    A.BENCH = _benchmark_profile(A)
    A.manual = _manual_profile(A)
    print(f"cell size {A.cell_km2:.1f} km^2 | full-Y2Y PU denom = {A.n_region_full:,.0f}")

    blocks = [A.NEW, A.BENCH] + ([A.manual] if A.manual else [])
    eff_all = np.array([v for C in blocks for cid in C["ids"] for v in C["eff"][cid]])
    A.EFF_RMAX = float(np.ceil(np.nanpercentile(eff_all, 98) / 0.1) * 0.1)
    print(f"shared efficiency scale EFF_RMAX = {A.EFF_RMAX:.2f} %/1,000 km^2")
    return A


def cost_path(A):
    return next(L["path"] for L in A.manifest["layers"] if L["role"] == "cost")


# ---- NEW clusters (connected components) ----
def _cluster_latitudes(A, lab, ids):
    coms = ndimage.center_of_mass(lab > 0, lab, ids)
    lat = {}
    for i, (cy, cx) in zip(ids, coms):
        x = float(A.sol0.x.values[int(round(cx))]); y = float(A.sol0.y.values[int(round(cy))])
        lat[i] = A.TO_LATLON.transform(x, y)[1]
    return lat


def _select_clusters(A, qual, cnt, lab):
    if len(qual) <= A.MAX_PLOTS or A.cluster_select != "spread":
        return sorted(qual, key=lambda i: -cnt[i])[:A.MAX_PLOTS]
    lat = _cluster_latitudes(A, lab, qual)
    lo, hi = min(lat.values()), max(lat.values())
    edges = np.linspace(lo, hi, A.MAX_PLOTS + 1); chosen = []
    for b in range(A.MAX_PLOTS):
        band = [i for i in qual if edges[b] <= lat[i] <= edges[b+1] and i not in chosen]
        if band:
            chosen.append(max(band, key=lambda i: cnt[i]))
    if len(chosen) < A.MAX_PLOTS:
        chosen += [i for i in sorted(qual, key=lambda i: -cnt[i]) if i not in chosen][:A.MAX_PLOTS-len(chosen)]
    chosen = sorted(chosen, key=lambda i: -lat[i])
    print(f"  spread: {len(chosen)} clusters over lat {min(lat[i] for i in chosen):.1f}-{max(lat[i] for i in chosen):.1f}N")
    return chosen


def _cluster_profile(A, mask, kind):
    lab, n = ndimage.label(mask, structure=np.ones((3, 3), int))
    cnt = np.bincount(lab.ravel())
    qual = [i for i in range(1, n+1) if cnt[i] >= A.MIN_CELLS]
    ids = _select_clusters(A, qual, cnt, lab)
    colors = {cid: CLUSTER_CMAP(j % 10) for j, cid in enumerate(ids)}
    profs, contrib, eff, raw = {}, {}, {}, {}
    for cid in ids:
        profs[cid], contrib[cid], eff[cid], raw[cid] = mask_profile(A, lab == cid)
    # Public identity = "Option 1..N" in the order `_select_clusters` returned (N->S for "spread",
    # largest-first for "largest"). The raw connected-component id (`cid`, e.g. 445) stays the
    # internal key that indexes the label raster, but it is never shown -- the map annotation, the
    # star titles and the consequences columns all read "Option k" so they cross-reference.
    labnum = {cid: j + 1 for j, cid in enumerate(ids)}
    print(f"{kind:22s}: {n} components, {len(ids)} kept (>= {A.MIN_CELLS} cells, {A.cluster_select})")
    return dict(lab=lab, ids=ids, cnt=cnt, colors=colors, labnum=labnum,
                names={cid: f"Option {labnum[cid]}" for cid in ids},
                profs=profs, contrib=contrib, eff=eff, raw=raw)


# ---- benchmark block (existing-protection comparison; per-analysis source) ----
def _benchmark_geoms(A):
    """(geometry, short_label) list for the benchmark block, per RESULTS_04[key]['benchmark']."""
    spec = A.a04["benchmark"]; t = spec["type"]
    if t == "named_pa":
        pa = gpd.read_file(config.PA_VECTOR).to_crs(A.crs).dissolve(by="PA_Name").reset_index()
        have = set(pa["PA_Name"]); missing = [n for n, _ in spec["featured"] if n not in have]
        assert not missing, f"benchmark PA_Name not found: {missing}"
        return [(pa.loc[pa.PA_Name == n, "geometry"].iloc[0], lab) for n, lab in spec["featured"]]
    if t == "named_vector":
        # honour the same source_filter the analysis used (e.g. northern subset only), and cap to
        # `top_n` largest so a long anchor list doesn't produce an unreadable star-plot grid.
        g = config._load_source(spec["vector"], spec.get("source_filter")).to_crs(A.crs)
        nf = spec["name_field"]; labels = spec.get("labels", {})
        if spec.get("top_n"):
            # largest first, but SKIP areas essentially nested inside an already-picked larger one
            # (e.g. Peel River sits 100% inside Peel Watershed): their profile is just a subset of
            # the parent's and they'd double-count in the consequences table. The slot goes to the
            # next-largest distinct area instead.
            g = g.assign(_km2=g.geometry.area).sort_values("_km2", ascending=False)
            keep = []
            for idx, row in g.iterrows():
                if len(keep) >= spec["top_n"]:
                    break
                if any(row.geometry.intersection(g.loc[k, "geometry"]).area >= 0.9 * row.geometry.area
                       for k in keep):
                    print(f"  skip nested benchmark area: {row[nf]}")
                    continue
                keep.append(idx)
            g = g.loc[keep]
        return [(row.geometry, labels.get(row[nf], str(row[nf]))) for _, row in g.iterrows()]
    if t == "in_window_pa":
        # Rank PAs by cells ACTUALLY inside the analysis window (valid_all = ROI-masked PUs),
        # NOT by bbox overlap -- otherwise a mountain park (Jasper/Banff) whose bbox clips the
        # window but which is then masked away by the foothills polygon would rank spuriously high.
        pa = gpd.read_file(spec["vector"]).to_crs(A.crs).dissolve(by=spec["name_field"]).reset_index()
        pa = pa[pa.intersects(A.outline.union_all())]                       # cheap prefilter
        scored = []
        for _, row in pa.iterrows():
            rast = rasterize([(row.geometry, 1)], out_shape=A.sol0.shape,
                             transform=A.sol0.rio.transform(), fill=0, dtype="uint8").astype(bool)
            n = int((rast & A.valid_all).sum())
            if n >= A.MIN_CELLS:
                scored.append((n, row.geometry, str(row[spec["name_field"]])))
        scored.sort(key=lambda x: -x[0])
        return [(g, lab) for _, g, lab in scored[:spec["top_n"]]]
    raise ValueError(f"unknown benchmark type {t!r}")


def _benchmark_profile(A):
    """Profile the benchmark areas over their FULL polygon clipped to the window's PUs -- same
    structure as _cluster_profile so the maps/stars/consequences consume it identically."""
    geoms = _benchmark_geoms(A)
    # Each area keeps its OWN mask. A shared first-wins label raster silently erased any area
    # fully overlapped by an earlier one (e.g. Peel River inside Peel Watershed) -- it kept a cell
    # count but had nothing to draw, so the map's center_of_mass returned NaN and blew up.
    ids, cnt, colors, names, labnum, geom_by, masks = [], {}, {}, {}, {}, {}, {}
    profs, contrib, eff, raw = {}, {}, {}, {}
    for j, (geom, short) in enumerate(geoms):
        rast = rasterize([(geom, 1)], out_shape=A.sol0.shape, transform=A.sol0.rio.transform(),
                         fill=0, dtype="uint8").astype(bool)
        m = rast & A.valid_all
        cells = int(m.sum())
        if cells < A.MIN_CELLS:
            print(f"  SKIP {short}: {cells} PU cells (< {A.MIN_CELLS})"); continue
        ids.append(short); cnt[short] = cells; names[short] = short; masks[short] = m
        colors[short] = CLUSTER_CMAP(j % 10); labnum[short] = j + 1; geom_by[short] = geom
        profs[short], contrib[short], eff[short], raw[short] = mask_profile(A, m)
    overlaps = [(a, b) for i, a in enumerate(ids) for b in ids[i+1:] if (masks[a] & masks[b]).any()]
    if overlaps:
        print(f"  note: {len(overlaps)} benchmark pair(s) overlap "
              f"(e.g. {overlaps[0][0][:24]} / {overlaps[0][1][:24]}) -- drawn in order, "
              f"contribution counts them separately")
    print(f"{'benchmark areas':22s}: {len(ids)} profiled [{A.a04['benchmark']['type']}]")
    return dict(ids=ids, cnt=cnt, colors=colors, names=names, labnum=labnum, geoms=geom_by,
                masks=masks, profs=profs, contrib=contrib, eff=eff, raw=raw)


def _manual_profile(A):
    """Optional hand-drawn area profiled like a cluster (Ross River for y2y; None otherwise)."""
    spec = A.a04["manual_area"]
    if not spec:
        return None
    g = gpd.read_file(spec["shp"]).to_crs(A.crs)
    rast = rasterize(((geom, 1) for geom in g.geometry), out_shape=A.sol0.shape,
                     transform=A.sol0.rio.transform(), fill=0, dtype="uint8").astype(bool)
    m = rast & A.valid_all
    if int(m.sum()) == 0:
        print(f"  manual '{spec['name']}': no PU cells in window -- skipped"); return None
    nm = spec["name"]; prof, contrib, eff, raw = mask_profile(A, m)
    return dict(ids=[nm], cnt={nm: int(m.sum())}, colors={nm: spec["color"]}, names={nm: nm},
                labnum={nm: 1}, geoms={nm: g.union_all()},
                profs={nm: prof}, contrib={nm: contrib}, eff={nm: eff}, raw={nm: raw},
                gdf=g, color=spec["color"])


# ---- star-plot renderer (shared by NEW / benchmark / manual) ----
def plot_stars(A, C, metric, title, fname, rmax=None):
    ids = C["ids"]
    if not ids:
        print(f"{title}: no areas to plot"); return
    spec = METRIC_SPEC[metric]; vecs = C[spec["key"]]
    rmax = rmax or spec["rmax"] or (max(max(vecs[cid]) for cid in ids) or 1.0)
    ticks = [rmax * t for t in (0.25, 0.5, 0.75, 1.0)]
    ang = np.linspace(0, 2*np.pi, len(A.axes_labels), endpoint=False).tolist(); ang += ang[:1]
    short = [l.replace("irrecoverable carbon ", "C:").replace("transboundary ", "")
              .replace("aoh richness ", "").replace("climate ", "") for l in A.axes_labels]
    ncol = min(3, len(ids)); nrow = int(np.ceil(len(ids) / ncol))
    fig, axx = plt.subplots(nrow, ncol, figsize=(4.8*ncol, 4.8*nrow), subplot_kw=dict(polar=True))
    axx = np.atleast_1d(axx).ravel()
    for ax, cid in zip(axx, ids):
        col = C["colors"].get(cid); ax.set_axisbelow(False)
        v = list(vecs[cid]) + list(vecs[cid])[:1]
        ax.plot(ang, v, color=col, linewidth=1.8, zorder=2); ax.fill(ang, v, color=col, alpha=0.25, zorder=1)
        ax.set_xticks(ang[:-1]); ax.set_xticklabels(short, fontsize=9); ax.tick_params(axis="x", pad=8)
        ax.set_ylim(0, rmax); ax.set_yticks(ticks)
        ax.set_yticklabels([spec["fmt"].format(t) for t in ticks], fontsize=8); ax.set_rlabel_position(0)
        ax.yaxis.grid(True, color="0.55", lw=0.9); ax.xaxis.grid(True, color="0.75", lw=0.6)
        comp = float(np.mean(vecs[cid]))
        ax.set_title(f"{C['names'].get(cid, cid)} · {int(round(C['cnt'][cid]*A.cell_km2))} km² "
                     f"· {spec['fmt'].format(comp)}", fontsize=12)
    for ax in axx[len(ids):]: ax.set_visible(False)
    fig.suptitle(f"{title}\n(axis = {spec['unit']})", y=1.02, fontsize=15); fig.tight_layout()
    fig.savefig(A.fig_dir / fname, dpi=150, bbox_inches="tight"); plt.show()


# ---- NEW candidate-area map + stars ----
def new_map(A):
    OTHER = NEW_ALLOC_COLOR
    other = A.new_mask & ~np.isin(A.NEW["lab"], A.NEW["ids"])
    has_anchors = bool(A.anchors.any())
    fig, ax = plt.subplots(figsize=(8, 12))
    # existing PAs (grey) and committed anchors (teal) drawn as SEPARATE layers so they read
    # distinctly, then the rest of the allocation, then the profiled clusters on top.
    A.sol0.copy(data=np.where(A.pa_on & ~A.anchors, 1.0, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap=ListedColormap([PA_COLOR]), add_colorbar=False)
    if has_anchors:
        A.sol0.copy(data=np.where(A.anchors, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([ANCHOR_COLOR]), add_colorbar=False)
    A.sol0.copy(data=np.where(other, 1.0, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap=ListedColormap([OTHER]), add_colorbar=False)
    for cid in A.NEW["ids"]:
        A.sol0.copy(data=np.where(A.NEW["lab"] == cid, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([A.NEW["colors"][cid]]), add_colorbar=False)
        cy, cx = ndimage.center_of_mass(A.NEW["lab"] == cid)
        x, y = float(A.sol0.x.values[int(round(cx))]), float(A.sol0.y.values[int(round(cy))])
        ax.annotate(str(A.NEW["labnum"][cid]), xy=(x, y), xytext=(9, 9), textcoords="offset points", fontsize=7,
                    fontweight="bold", ha="center", va="center", color="black",
                    path_effects=[pe.withStroke(linewidth=2, foreground="white")],
                    arrowprops=dict(arrowstyle="-", lw=0.5, color="black", shrinkA=1, shrinkB=1),
                    annotation_clip=False, zorder=6)
    _frame(A, ax)
    n_other = int(other.sum()); n_top = int(np.isin(A.NEW["lab"], A.NEW["ids"]).sum())
    handles = [Patch(color=PA_COLOR, label="existing protected areas")]
    if has_anchors:
        handles.append(Patch(color=ANCHOR_COLOR,
                             label=f"{A.a04.get('anchor_label', 'committed anchors')} "
                                   f"({A.anchors.sum()*A.cell_km2:,.0f} km²)"))
    handles += [Patch(color=OTHER, label=f"other new allocation ({n_other*A.cell_km2:,.0f} km²)"),
                Patch(color="none", label=f"numbered = Options 1–{len(A.NEW['ids'])} "
                                          f"({n_top*A.cell_km2:,.0f} km²)")]
    ax.legend(handles=handles + _outline_handles(A), loc="lower left", fontsize=8, frameon=True)
    ax.set_title(f"{A.region_label} — new candidate areas within the full allocation")
    ax.set_aspect("equal"); ax.set_axis_off()
    fig.savefig(A.fig_dir / "clusters_map.png", dpi=150, bbox_inches="tight"); plt.show()


def new_stars(A):
    plot_stars(A, A.NEW, "richness",     f"{A.region_label} — new candidate areas: relative richness", "clusters_new_richness.png")
    plot_stars(A, A.NEW, "contribution", f"{A.region_label} — new candidate areas: contribution to Y2Y totals", "clusters_new_contribution.png")
    plot_stars(A, A.NEW, "efficiency",   f"{A.region_label} — new candidate areas: value density (shared scale)", "clusters_new_efficiency.png", rmax=A.EFF_RMAX)


# ---- benchmark map + stars ----
def bench_map(A):
    B = A.BENCH
    fig, ax = plt.subplots(figsize=(8, 12))
    A.sol0.copy(data=np.where(A.pa_on, 1.0, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap=ListedColormap(["0.82"]), add_colorbar=False)
    handles = [Patch(color="0.82", label="other existing PAs")]
    # the run's new allocation, in the SAME wheat as the clusters map, so the benchmark parks can be
    # read against where the solution actually expands. Drawn under the benchmark areas; they cannot
    # overlap anyway (new_mask excludes locked-in PAs), so this only sets the backdrop.
    A.sol0.copy(data=np.where(A.new_mask, 1.0, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap=ListedColormap([NEW_ALLOC_COLOR]), add_colorbar=False)
    handles.append(Patch(color=NEW_ALLOC_COLOR,
                         label=f"new allocation ({A.new_mask.sum()*A.cell_km2:,.0f} km²)"))
    for n, cid in enumerate(B["ids"], 1):
        m = B["masks"][cid]                       # each area's OWN mask (overlap-safe)
        A.sol0.copy(data=np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([B["colors"][cid]]), add_colorbar=False)
        km2 = int(round(B["cnt"][cid]*A.cell_km2))
        handles.append(Patch(color=B["colors"][cid], label=f"{n}. {cid} ({km2:,} km²)"))
        cy, cx = ndimage.center_of_mass(m)
        x, y = float(A.sol0.x.values[int(round(cx))]), float(A.sol0.y.values[int(round(cy))])
        ax.annotate(str(n), xy=(x, y), xytext=(10, 10), textcoords="offset points", fontsize=9,
                    fontweight="bold", ha="center", va="center", color="black",
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")],
                    arrowprops=dict(arrowstyle="-", lw=0.6, color="black", shrinkA=1, shrinkB=1),
                    annotation_clip=False, zorder=6)
    # the hand-drawn proposal (Ross River for y2y) continues the numbering as the last entry, in its
    # OWN colour -- it is a PROPOSED area, not existing protection, so it should not read as one of
    # the featured parks. Map only; the star plots and tables keep it in its own block.
    if A.manual:
        M = A.manual; nm = M["ids"][0]; n = len(B["ids"]) + 1
        M["gdf"].plot(ax=ax, facecolor=M["color"], edgecolor="black", linewidth=0.8, alpha=0.85)
        handles.append(Patch(color=M["color"], label=f"{n}. {nm} — proposed "
                                                     f"({int(round(M['cnt'][nm]*A.cell_km2)):,} km²)"))
        rp = M["gdf"].geometry.iloc[0].representative_point()
        ax.annotate(str(n), xy=(rp.x, rp.y), xytext=(10, 10), textcoords="offset points", fontsize=9,
                    fontweight="bold", ha="center", va="center", color="black",
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")],
                    arrowprops=dict(arrowstyle="-", lw=0.6, color="black", shrinkA=1, shrinkB=1),
                    annotation_clip=False, zorder=6)
    _frame(A, ax)
    ax.legend(handles=handles + _outline_handles(A), loc="lower left", fontsize=8, frameon=True)
    ax.set_title(f"{A.region_label} — {A.a04['benchmark_title']}")
    ax.set_aspect("equal"); ax.set_axis_off()
    fig.savefig(A.fig_dir / "benchmark_map.png", dpi=150, bbox_inches="tight"); plt.show()


def bench_stars(A):
    t = A.a04["benchmark_title"]
    plot_stars(A, A.BENCH, "richness",     f"{A.region_label} — {t}: relative richness", "benchmark_richness.png")
    plot_stars(A, A.BENCH, "contribution", f"{A.region_label} — {t}: contribution to Y2Y totals", "benchmark_contribution.png")
    plot_stars(A, A.BENCH, "efficiency",   f"{A.region_label} — {t}: value density (shared scale)", "benchmark_efficiency.png", rmax=A.EFF_RMAX)


# ---- manual area (Ross River; y2y only) ----
def manual_block(A):
    if not A.manual:
        print("no manual area for this analysis"); return
    M = A.manual; nm = M["ids"][0]
    # STAR PLOTS ONLY. The area used to get its own map too; it is now drawn on the benchmark map as
    # the last numbered entry (bench_map), so a second, near-identical map earned nothing.
    plot_stars(A, M, "richness",     f"{nm}: relative richness", "manual_richness.png")
    plot_stars(A, M, "contribution", f"{nm}: contribution to Y2Y totals", "manual_contribution.png")
    plot_stars(A, M, "efficiency",   f"{nm}: value density (shared scale)", "manual_efficiency.png", rmax=A.EFF_RMAX)


# ---- consequences tables + heatmaps + plain language ----
# Column groups for the consequences tables: the model's NEW candidate areas are decision
# OPTIONS; the benchmark areas (parks / proposed IPCAs) and any hand-drawn area are the
# already-designated yardstick they are read against.
GRP_NEW = "Alternatives (new options)"
GRP_EST = "Established Protected/Priority Areas"
UNIT_COL = ("", "unit")


def _blocks(A):
    """(column group, kind, block) per profiled set, in table order."""
    b = [(GRP_NEW, "new", A.NEW), (GRP_EST, "benchmark", A.BENCH)]
    if A.manual:
        b.append((GRP_EST, "manual", A.manual))
    return b


def _dec(v, dp, sig=2, dp_max=6):
    """Decimals for `v`: at least `dp`, extended until `sig` significant figures show.

    A fixed dp per row silently flattened small values -- at 1 dp the whole Alberta-foothills
    contribution table read "0.0 / 0.1", and a 0-1 index at 1 dp reads a flat "1.0". Only the
    small cells gain decimals; everything else keeps the row's declared dp."""
    if v is None or not np.isfinite(v) or v == 0:
        return dp
    return int(min(max(dp, sig - 1 - int(np.floor(np.log10(abs(v))))), dp_max))


def consequences(A):
    n_full = A.n_region_full
    options, area_km2, area_pct, kinds = [], [], [], {}
    contrib_by, eff_by, raw_by = {}, {}, {}
    for group, kind, C in _blocks(A):
        for cid in C["ids"]:
            # public name: "Option k" for the new areas, the park / IPCA name for the rest
            col = (group, C["names"].get(cid, str(cid)))
            options.append(col)
            area_km2.append(int(round(C["cnt"][cid]*A.cell_km2)))
            pct = 100.0*C["cnt"][cid]/n_full
            area_pct.append(round(pct, _dec(pct, 2)))      # >= 2 sig figs for tiny sub-regions
            contrib_by[col] = C["contrib"][cid]; eff_by[col] = C["eff"][cid]; raw_by[col] = C["raw"][cid]
            kinds[col] = kind
    assert len(set(options)) == len(options), f"duplicate area names: {options}"
    cols = pd.MultiIndex.from_tuples(options)          # level 0 = group, level 1 = area name
    area_head = pd.DataFrame([area_km2, area_pct], index=["area (km^2)", "area (% of Y2Y)"],
                             columns=cols)

    def build(values_by, dp, defn, unit=None):
        body = pd.DataFrame(values_by, index=A.OBJ_DISPLAY, columns=cols)
        dps = dp if isinstance(dp, (list, tuple)) else [dp]*len(body)   # per-row minimum decimals
        body = pd.DataFrame([[round(v, _dec(v, d)) for v in row] for (_, row), d in zip(body.iterrows(), dps)],
                            index=body.index, columns=body.columns)
        df = pd.concat([area_head, body])
        if unit is not None:
            df.insert(0, UNIT_COL, ["km^2", "% of Y2Y"] + list(unit))
        df.index.name = defn
        return df

    contrib_tbl = build(contrib_by, 1, "Contribution = area's share of the Y2Y region-wide total per input (%). Rows: 2 area metrics + 9 inputs; columns: areas.")
    eff_tbl = build(eff_by, 3, "Efficiency = contribution per unit area (% of Y2Y total per 1,000 km^2). Rows: 2 area metrics + 9 inputs; columns: areas.")
    raw_dp = [RAW_SPEC[c][3] for c in A.axis_cols]      # per-objective decimals (mixed scales)
    raw_tbl = build(raw_by, raw_dp, "Raw = actual amount per input in the area, in the native units in the 'unit' column. Rows: 2 area metrics + 9 inputs; columns: areas.", unit=A.OBJ_UNIT)

    def _fmt(df, dp):
        """String-format per CELL so a 0-1 index and tonnes both read correctly (pandas otherwise
        formats per COLUMN and forces scientific notation on mixed scales) and so the >= 2 sig-fig
        rule survives display -- a cell rounded to 0.045 must not print back as "0.0"."""
        out = df.copy().astype(object)
        dps = [0, 2] + (list(dp) if isinstance(dp, (list, tuple)) else [dp]*len(A.OBJ_DISPLAY))
        for (idx, row), d in zip(df.iterrows(), dps):
            out.loc[idx] = [v if isinstance(v, str) else f"{v:,.{_dec(v, d)}f}" for v in row]
        return out

    pd.set_option("display.width", 300); pd.set_option("display.max_columns", None)
    for name, tbl, dp in [("CONTRIBUTION (% of Y2Y total)", contrib_tbl, 1),
                          ("EFFICIENCY (% of Y2Y per 1,000 km^2)", eff_tbl, 3),
                          ("RAW (native units)", raw_tbl, raw_dp)]:
        # the definition rides along as index.name for the CSV, but printing it there pads the
        # row-label column to its own width -- print it as a caption instead.
        print(f"{name}:\n  {tbl.index.name}")
        print(_fmt(tbl, dp).rename_axis(None).to_string()); print()

    # disjoint check: NEW + benchmark are spatially disjoint -> summed contribution <= 100%.
    disj = [o for o in options if kinds[o] in ("new", "benchmark")]
    tot = contrib_tbl.loc[A.OBJ_DISPLAY, disj].sum(axis=1)
    assert (tot <= 100.5).all(), f"contribution > 100% for {tot[tot > 100.5].index.tolist()}"

    for name, tbl in [("contribution", contrib_tbl), ("efficiency", eff_tbl), ("raw", raw_tbl)]:
        # utf-8-SIG: row labels include Indigenous place names (the 04b IPCA benchmark especially).
        # Excel on macOS assumes Mac Roman without a BOM and mangles them.
        tbl.to_csv(A.run_dir / f"consequences_{name}.csv", encoding="utf-8-sig")
    print(f"wrote consequences_{{contribution,efficiency,raw}}.csv -> {A.run_dir.relative_to(config.PROJECT_DIR)}")
    A.contrib_tbl, A.eff_tbl, A.raw_tbl = contrib_tbl, eff_tbl, raw_tbl
    return contrib_tbl, eff_tbl, raw_tbl


def footprint_audit(A):
    """Does the solution avoid human-modified land -- and if so, is it the OPTIMIZER doing it?

    WHY THIS EXISTS. `human_modification` enters the solve as intactness (1 - gHM), which over a
    uniformly wild region has leverage 0.042: its captured fraction is confined to 27.2-31.4%
    whatever we select, so it holds ~1% of the objective's achievable swing and cannot counterweight
    anything. The consequence is measurable and was not visible in any existing view, because the
    whole-solution average hides it: the locked PAs are very intact (they are existing parks), which
    drags the overall mean down and makes the run look like it avoids modified land. Split out the
    NEW selection and the sign flips.

    Reported deliberately rather than fixed. Restoring intactness would need either a role change
    (gHM as a penalty/cost) or an aggressive nonlinearity -- a p1-p99 stretch only reaches 0.084 --
    and both introduce a new uncalibrated dial. The decision (2026-08-17) was to leave the layer
    alone and publish the bias with its mechanism, so a reader can weigh it.

    Reads RAW gHM from `cleaned_aligned/` (pre-orientation), because "how modified is this cell" is
    the interpretable quantity; the hand-off layer holds 1 - gHM."""
    ghm = _read_match(A, str((config.ALIGNED_DIR / "human_modification.tif")
                             .relative_to(config.PROJECT_DIR)))
    v = A.valid_all
    sel, new, locked = (A.sol0.fillna(0).values > 0.5) & v, A.new_mask & v, A.locked & v
    uns = v & ~sel

    rows = [("selected (all)", sel), ("  of which: locked PAs", locked),
            ("  of which: NEW allocation", new), ("unselected", uns), ("whole region", v)]
    print(f"mean raw gHM by group ({A.region_label})")
    for label, m in rows:
        print(f"  {label:<28}{np.nanmean(ghm[m]):7.4f}   ({int(m.sum()):,} cells)")

    # THE HEADLINE. If the optimizer were avoiding modified land, new < unselected.
    mean_new, mean_uns = float(np.nanmean(ghm[new])), float(np.nanmean(ghm[uns]))
    verdict = ("MORE modified than the land it passed over" if mean_new > mean_uns
               else "less modified than the land it passed over")
    print(f"\n  -> the NEW selection is {verdict}: {mean_new:.4f} vs {mean_uns:.4f}")
    if mean_new > mean_uns:
        print("     (the overall solution looks intact only because the locked PAs already are)")

    # Selection rate inside the modified tail: 30% = indifferent.
    print(f"\nselection rate within the gHM tail (vs {100*config.BUDGET_PCT:.0f}% if indifferent)")
    tail_rows = []
    for q in (90, 99, 99.9):
        thr = float(np.nanpercentile(ghm[v], q))
        tail = v & (ghm >= thr)
        rate = 100.0 * (tail & sel).sum() / max(int(tail.sum()), 1)
        tail_rows.append(dict(pctile=q, threshold=thr, pct_selected=rate))
        print(f"  top {100-q:>4.1f}% (gHM >= {thr:.3f}): {rate:5.1f}% selected")

    # WHY. Any feature correlated with gHM pulls the solution toward modified land; nothing in the
    # stack pushes back hard enough. Richness peaks in productive low valleys, which is also where
    # people are -- a confound, not a modelling error, but it decides the outcome here.
    print("\nSpearman(raw gHM, feature) -- which inputs pull TOWARD modified land?")
    conf = []
    for name in A.cont:
        # Skip the gHM-derived feature itself: it is a monotone transform of the variable we are
        # correlating against, so it scores -1.000 by construction and says nothing.
        if name == "human_modification":
            continue
        path = next(L["path"] for L in A.manifest["layers"] if L["name"] == name)
        f = _read_match(A, path)
        ok = v & np.isfinite(f) & np.isfinite(ghm)
        # rank-correlate on a subsample: full-PU spearman on ~1.3M cells is slow and the estimate
        # is already stable at 200k.
        idx = np.flatnonzero(ok.ravel())
        if idx.size > 200_000:
            idx = np.random.default_rng(0).choice(idx, 200_000, replace=False)
        r = float(spearmanr(ghm.ravel()[idx], f.ravel()[idx]).statistic)
        conf.append(dict(feature=name, spearman_vs_ghm=r))
        flag = "  <-- pulls toward modified land" if r > 0.15 else ""
        print(f"  {name:<34}{r:+.3f}{flag}")

    A.footprint = dict(
        by_group={label.strip(): float(np.nanmean(ghm[m])) for label, m in rows},
        tail=pd.DataFrame(tail_rows), confound=pd.DataFrame(conf).sort_values(
            "spearman_vs_ghm", ascending=False).reset_index(drop=True))
    return A


def corridor_report(A):
    """Is the new allocation CORRIDORS between anchors, or fresh clumps?

    For connectivity analyses (northern_ipcas) the goal is land that LINKS the locked anchors.
    Prints objective shape metrics; the decisive one is the last: label `locked | new` and count
    how many distinct connected components still contain anchors -- corridors working means the
    anchors merge into FEWER components (ideally 1)."""
    new, locked, anchors = A.new_mask, A.locked, A.anchors
    k = A.cell_km2
    lab, n = ndimage.label(new, structure=np.ones((3, 3), int))
    cnt = np.bincount(lab.ravel())[1:]
    print(f"{A.region_label} — corridor report\n")
    print(f"  new allocation      : {new.sum():,} cells ({new.sum()*k:,.0f} km²) in {n:,} components")
    print(f"  singletons          : {int((cnt == 1).sum()):,} | median component {np.median(cnt):.0f} cells"
          if n else "  (no new allocation)")

    # attachment: new area sitting in components that touch a locked area
    grow = ndimage.binary_dilation(locked, np.ones((3, 3), bool))
    touch = set(np.unique(lab[new & grow])) - {0}
    att = np.isin(lab, list(touch)) & new
    pct = 100 * att.sum() / max(new.sum(), 1)
    print(f"  attached to locked  : {att.sum():,} cells ({pct:.0f}%)  ->  {100-pct:.0f}% DETACHED "
          f"(connects nothing)")

    # shape: exposed edges per new cell (0 = solid blob, 4 = isolated pixels; corridors sit high)
    p = np.pad(new, 1)
    e = sum(((p[1:-1, 1:-1] == 1) & (p[a:b, c:d] == 0)).sum()
            for a, b, c, d in [(None, -2, 1, -1), (2, None, 1, -1), (1, -1, None, -2), (1, -1, 2, None)])
    print(f"  edges per new cell  : {e/max(new.sum(),1):.2f}   (0 = solid blob, ~4 = scattered pixels)")

    # THE corridor test: do the anchors end up in the same connected network?
    if anchors.any():
        alab, na = ndimage.label(anchors, structure=np.ones((3, 3), int))

        def n_components(mask):
            """Distinct connected components of `mask` that the anchors occupy (0 = outside the
            PU, excluded -- an anchor lying off the planning units is not its own component)."""
            net, _ = ndimage.label(mask, structure=np.ones((3, 3), int))
            comps = set()
            for i in range(1, na + 1):
                comps |= {int(v) for v in np.unique(net[alab == i]) if v}
            return len(comps)

        now, was = n_components(locked | new), n_components(locked)
        verdict = "corridors ARE joining anchors" if now < was else "new area is NOT joining anchors"
        print(f"\n  anchors span {was} connected component(s) of `locked` alone")
        print(f"           -> {now} component(s) once the new allocation is added   [{verdict}]")
    return None


def plain_language(A):
    print(f"{A.region_label} — per-area strongest / weakest inputs (by relative richness):\n")
    seen = set()
    for group, kind, C in _blocks(A):
        if C["ids"] and group not in seen:      # benchmark + manual share one group heading
            print(f"  [{group}]"); seen.add(group)
        for cid in C["ids"]:
            label = C["names"].get(cid, str(cid))
            order = np.argsort(C["profs"][cid])
            strongest = ", ".join(np.array(A.OBJ_DISPLAY)[order[::-1][:3]])
            weakest = ", ".join(np.array(A.OBJ_DISPLAY)[order[:3]])
            print(f"  {label:22s} strongest: {strongest}   |   weakest: {weakest}")


def heatmaps(A):
    def heatmap(tbl, title, fname):
        opts = [c for c in tbl.columns if c != UNIT_COL]
        names = [c[1] for c in opts]                       # leaf label; c[0] is the column group
        M = tbl.loc[A.OBJ_DISPLAY, opts].to_numpy(dtype=float)
        rmin = np.nanmin(M, axis=1, keepdims=True); rmax = np.nanmax(M, axis=1, keepdims=True)
        norm = np.where(rmax > rmin, (M - rmin) / (rmax - rmin), 0.5)
        words = np.empty(M.shape, dtype=object)
        for i in range(M.shape[0]):
            lo, hi = np.nanpercentile(M[i], [100/3, 200/3])
            words[i] = np.where(M[i] >= hi, "High", np.where(M[i] <= lo, "Low", "Med"))
        fig, ax = plt.subplots(figsize=(2.2 + 0.7*len(opts), 0.72*len(A.OBJ_DISPLAY) + 1.8))
        ax.imshow(norm, cmap="YlGn", aspect="auto", vmin=0, vmax=1)
        ax.set_xticks(range(len(opts))); ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(A.OBJ_DISPLAY))); ax.set_yticklabels(A.OBJ_DISPLAY, fontsize=9)
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                ax.text(j, i, words[i, j], ha="center", va="center", fontsize=7, fontweight="bold",
                        color="white" if norm[i, j] > 0.6 else "black")
        ax.set_xticks(np.arange(-.5, len(opts), 1), minor=True)
        ax.set_yticks(np.arange(-.5, len(A.OBJ_DISPLAY), 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=1.5); ax.tick_params(which="minor", length=0)
        # column groups: a divider between them + the group name centred over its columns, so the
        # heatmap carries the same Alternatives / Established split as the tables.
        groups = [c[0] for c in opts]
        for g in dict.fromkeys(groups):
            js = [j for j, gg in enumerate(groups) if gg == g]
            ax.text((js[0] + js[-1]) / 2, -0.75, g, ha="center", va="bottom", fontsize=8,
                    fontweight="bold", color="0.25")
            if js[0] > 0:
                ax.axvline(js[0] - 0.5, color="0.25", lw=1.6)
        ax.set_title(title, fontsize=12, pad=24)     # pad clears the group labels drawn above row 0
        fig.tight_layout()
        fig.savefig(A.fig_dir / fname, dpi=150, bbox_inches="tight"); plt.show()

    heatmap(A.contrib_tbl, f"{A.region_label} — contribution (High/Med/Low per objective)", "consequences_heatmap_contribution.png")
    heatmap(A.eff_tbl, f"{A.region_label} — efficiency (High/Med/Low per objective)", "consequences_heatmap_efficiency.png")
