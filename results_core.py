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
from rasterio.enums import Resampling
from rasterio.features import rasterize
import pyproj

import config

# tab10: 10 saturated, well-separated hues, no pale twins (shared by maps AND star plots).
CLUSTER_CMAP = plt.get_cmap("tab10")

# Per-objective metadata: display name, native unit (raw table), raw-aggregation rule.
RAW_SPEC = {
    "human_modification":           ("Intactness",             "intactness 0-1 (mean; 1-gHM)",              "mean"),
    "transboundary_connectivity":   ("Connectivity",           "current density, amperes (mean)",          "mean"),
    "climate_corridors":            ("Climate corridors",      "current-flow centrality, amperes (mean)",  "mean"),
    "climate_type_macrorefugia":    ("Climate refugia",        "km/yr (mean; refugial value = vmax - backward velocity)", "mean"),
    "irrecoverable_carbon_biomass": ("Carbon: biomass",        "t C (total)",                              "tonnes"),
    "irrecoverable_carbon_m_soc":   ("Carbon: mineral soil",   "t C (total)",                              "tonnes"),
    "aoh_richness_mammals":         ("Mammal richness",        "species/cell (mean)",                      "mean"),
    "aoh_richness_birds":           ("Bird richness",          "species/cell (mean)",                      "mean"),
    "EFG_mean":                     ("Ecosystem groups (EFG)", None,                                       "efg_groups"),
}
METRIC_SPEC = {
    "richness":     dict(key="profs",   unit="relative richness (0-1, region 5-95 pctile)", rmax=1.0,  fmt="{:.2f}"),
    "contribution": dict(key="contrib", unit="% of Y2Y region total",                       rmax=None, fmt="{:.1f}"),
    "efficiency":   dict(key="eff",     unit="% of Y2Y total per 1,000 km^2",                rmax=None, fmt="{:.2f}"),
}


# ================= setup =================
def load(analysis):
    """Light setup: locate the run, read manifest/summary/representation, set the region label
    and the map outline (the ROI polygon for sub-regions, the full Y2Y boundary for y2y)."""
    a04 = config.RESULTS_04[analysis]
    run_dir = config.RESULTS_DIR / config.ANALYSES[analysis]["results_subdir"]
    assert run_dir.exists(), f"{run_dir} not found -- run 03{('a' if analysis=='y2y' else '')} first"
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

    return types.SimpleNamespace(
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


def _frame(A, ax):
    """Draw the ROI outline (solid black) + optional context outline (dashed grey).

    Framing (RESULTS_04[key]["frame"]):
      "window" (default) -> keep the map on the analysis window (context can't zoom it out);
      "context"          -> zoom OUT to the whole context extent (e.g. all of Alberta), so the
                            window/foothills data reads inside the full province.
    Axis direction (rioxarray may invert y) is preserved either way."""
    xlim, ylim = ax.get_xlim(), ax.get_ylim()                 # window extent from the raster
    A.outline.boundary.plot(ax=ax, color="black", linewidth=0.9)
    if A.context is not None:
        A.context.boundary.plot(ax=ax, color="0.35", linewidth=1.1, linestyle="--")
    if A.context is not None and A.a04.get("frame") == "context":
        minx, miny, maxx, maxy = A.context.total_bounds
        m = 0.03 * max(maxx - minx, maxy - miny)              # small margin
        xs, ys = (minx - m, maxx + m), (miny - m, maxy + m)
        ax.set_xlim(xs if xlim[0] <= xlim[1] else xs[::-1])   # preserve axis direction
        ax.set_ylim(ys if ylim[0] <= ylim[1] else ys[::-1])
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
    pa_grid = rioxarray.open_rasterio(config.HANDOFF_DIR / "mask_protected_areas.tif", masked=True).squeeze()
    pa_on = pa_grid.rio.reproject_match(A.freq)
    sol = A.portfolio.isel(band=0)
    existing = pa_on >= 0.5; new_alloc = (sol > 0.5) & ~existing
    cat = xr.where(existing, 1, xr.where(new_alloc, 2, np.nan))
    fig, ax = plt.subplots(figsize=(7, 12))
    cat.plot.imshow(ax=ax, cmap=ListedColormap(["#7a7a7a", "#1b9e77"]), vmin=1, vmax=2, add_colorbar=False)
    _frame(A, ax)
    ax.legend(handles=[Patch(color="#7a7a7a", label="existing protected area"),
                       Patch(color="#1b9e77", label="new allocation")] + _outline_handles(A),
              loc="lower left", fontsize=9, frameon=True)
    ax.set_title(f"{A.region_label} — existing protection vs new allocation\n"
                 f"existing PA: {int(existing.sum()):,} cells | new: {int(new_alloc.sum()):,} cells")
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

    A.valid_all = np.isfinite(A.cont_raw).all(axis=0)
    sel = A.sol0.fillna(0).values > 0.5
    A.pa_on = (rioxarray.open_rasterio(config.HANDOFF_DIR / "mask_protected_areas.tif", masked=True)
               .squeeze().rio.reproject_match(A.sol0).values >= 0.5)
    A.new_mask = sel & ~A.pa_on

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
    print(f"{kind:22s}: {n} components, {len(ids)} kept (>= {A.MIN_CELLS} cells, {A.cluster_select})")
    return dict(lab=lab, ids=ids, cnt=cnt, colors=colors, labnum={cid: cid for cid in ids},
                names={cid: f"cluster {cid}" for cid in ids},
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
        g = gpd.read_file(spec["vector"]).to_crs(A.crs); nf = spec["name_field"]
        labels = spec.get("labels", {})
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
    lab = np.zeros(A.sol0.shape, dtype=np.int32)
    ids, cnt, colors, names, labnum, geom_by = [], {}, {}, {}, {}, {}
    profs, contrib, eff, raw = {}, {}, {}, {}
    for j, (geom, short) in enumerate(geoms):
        rast = rasterize([(geom, 1)], out_shape=A.sol0.shape, transform=A.sol0.rio.transform(),
                         fill=0, dtype="uint8").astype(bool)
        m = rast & A.valid_all
        cells = int(m.sum())
        if cells < A.MIN_CELLS:
            print(f"  SKIP {short}: {cells} PU cells (< {A.MIN_CELLS})"); continue
        ids.append(short); cnt[short] = cells; names[short] = short
        colors[short] = CLUSTER_CMAP(j % 10); labnum[short] = j + 1; geom_by[short] = geom
        lab[m & (lab == 0)] = j + 1
        profs[short], contrib[short], eff[short], raw[short] = mask_profile(A, m)
    print(f"{'benchmark areas':22s}: {len(ids)} profiled [{A.a04['benchmark']['type']}]")
    return dict(lab=lab, ids=ids, cnt=cnt, colors=colors, names=names, labnum=labnum, geoms=geom_by,
                profs=profs, contrib=contrib, eff=eff, raw=raw)


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
    OTHER = "#ecdcae"
    other = A.new_mask & ~np.isin(A.NEW["lab"], A.NEW["ids"])
    fig, ax = plt.subplots(figsize=(8, 12))
    A.sol0.copy(data=np.where(A.pa_on, 1.0, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap=ListedColormap(["0.6"]), add_colorbar=False)
    A.sol0.copy(data=np.where(other, 1.0, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap=ListedColormap([OTHER]), add_colorbar=False)
    for cid in A.NEW["ids"]:
        A.sol0.copy(data=np.where(A.NEW["lab"] == cid, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([A.NEW["colors"][cid]]), add_colorbar=False)
        cy, cx = ndimage.center_of_mass(A.NEW["lab"] == cid)
        x, y = float(A.sol0.x.values[int(round(cx))]), float(A.sol0.y.values[int(round(cy))])
        ax.annotate(str(cid), xy=(x, y), xytext=(9, 9), textcoords="offset points", fontsize=7,
                    fontweight="bold", ha="center", va="center", color="black",
                    path_effects=[pe.withStroke(linewidth=2, foreground="white")],
                    arrowprops=dict(arrowstyle="-", lw=0.5, color="black", shrinkA=1, shrinkB=1),
                    annotation_clip=False, zorder=6)
    _frame(A, ax)
    n_other = int(other.sum()); n_top = int(np.isin(A.NEW["lab"], A.NEW["ids"]).sum())
    ax.legend(handles=[Patch(color="0.6", label="existing protected areas"),
                       Patch(color=OTHER, label=f"other new allocation ({n_other*A.cell_km2:,.0f} km²)"),
                       Patch(color="none", label=f"numbered = top {len(A.NEW['ids'])} ({n_top*A.cell_km2:,.0f} km²)")]
                      + _outline_handles(A),
              loc="lower left", fontsize=8, frameon=True)
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
    for n, cid in enumerate(B["ids"], 1):
        j = B["labnum"][cid]
        A.sol0.copy(data=np.where(B["lab"] == j, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([B["colors"][cid]]), add_colorbar=False)
        km2 = int(round(B["cnt"][cid]*A.cell_km2))
        handles.append(Patch(color=B["colors"][cid], label=f"{n}. {cid} ({km2:,} km²)"))
        cy, cx = ndimage.center_of_mass(B["lab"] == j)
        x, y = float(A.sol0.x.values[int(round(cx))]), float(A.sol0.y.values[int(round(cy))])
        ax.annotate(str(n), xy=(x, y), xytext=(10, 10), textcoords="offset points", fontsize=9,
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
    fig, ax = plt.subplots(figsize=(8, 12))
    A.sol0.copy(data=np.where(A.pa_on, 1.0, np.nan).astype("float32")).plot.imshow(
        ax=ax, cmap=ListedColormap(["0.6"]), add_colorbar=False)
    M["gdf"].plot(ax=ax, facecolor=M["color"], edgecolor="black", linewidth=0.8, alpha=0.55)
    rp = M["gdf"].geometry.iloc[0].representative_point()
    ax.annotate(nm, xy=(rp.x, rp.y), fontsize=9, fontweight="bold", ha="center", va="center",
                color="black", path_effects=[pe.withStroke(linewidth=3, foreground="white")], annotation_clip=False)
    _frame(A, ax)
    ax.legend(handles=[Patch(color="0.6", label="existing PA"),
                       Patch(color=M["color"], label=f"{nm} ({int(round(M['cnt'][nm]*A.cell_km2)):,} km²)")]
                      + _outline_handles(A),
              loc="lower left", fontsize=9)
    ax.set_title(f"{nm} — proposed area vs existing protection")
    ax.set_aspect("equal"); ax.set_axis_off()
    fig.savefig(A.fig_dir / "manual_area_map.png", dpi=150, bbox_inches="tight"); plt.show()
    plot_stars(A, M, "richness",     f"{nm}: relative richness", "manual_richness.png")
    plot_stars(A, M, "contribution", f"{nm}: contribution to Y2Y totals", "manual_contribution.png")
    plot_stars(A, M, "efficiency",   f"{nm}: value density (shared scale)", "manual_efficiency.png", rmax=A.EFF_RMAX)


# ---- consequences tables + heatmaps + plain language ----
def _blocks(A):
    b = [("NEW", "new", A.NEW), ("", "benchmark", A.BENCH)]
    if A.manual:
        b.append(("", "manual", A.manual))
    return b


def consequences(A):
    n_full = A.n_region_full
    options, area_km2, area_pct, kinds = [], [], [], {}
    contrib_by, eff_by, raw_by = {}, {}, {}
    for prefix, kind, C in _blocks(A):
        for cid in C["ids"]:
            label = f"{prefix}-{cid}" if prefix else str(cid)
            options.append(label)
            area_km2.append(int(round(C["cnt"][cid]*A.cell_km2)))
            area_pct.append(round(100.0*C["cnt"][cid]/n_full, 2))
            contrib_by[label] = C["contrib"][cid]; eff_by[label] = C["eff"][cid]; raw_by[label] = C["raw"][cid]
            kinds[label] = kind
    area_head = pd.DataFrame([dict(zip(options, area_km2)), dict(zip(options, area_pct))],
                             index=["area (km^2)", "area (% of Y2Y)"], columns=options)

    def build(values_by, dp, defn, unit=None):
        body = pd.DataFrame(values_by, index=A.OBJ_DISPLAY, columns=options).round(dp)
        df = pd.concat([area_head, body])
        if unit is not None:
            df.insert(0, "unit", ["km^2", "% of Y2Y"] + list(unit))
        df.index.name = defn
        return df

    contrib_tbl = build(contrib_by, 1, "Contribution = area's share of the Y2Y region-wide total per input (%). Rows: 2 area metrics + 9 inputs; columns: areas.")
    eff_tbl = build(eff_by, 3, "Efficiency = contribution per unit area (% of Y2Y total per 1,000 km^2). Rows: 2 area metrics + 9 inputs; columns: areas.")
    raw_tbl = build(raw_by, 1, "Raw = actual amount per input in the area, in the native units in the 'unit' column. Rows: 2 area metrics + 9 inputs; columns: areas.", unit=A.OBJ_UNIT)

    pd.set_option("display.width", 300); pd.set_option("display.max_columns", None)
    for name, tbl in [("CONTRIBUTION (% of Y2Y total)", contrib_tbl),
                      ("EFFICIENCY (% of Y2Y per 1,000 km^2)", eff_tbl),
                      ("RAW (native units)", raw_tbl)]:
        print(name + ":"); print(tbl.to_string()); print()

    # disjoint check: NEW + benchmark are spatially disjoint -> summed contribution <= 100%.
    disj = [o for o in options if kinds[o] in ("new", "benchmark")]
    tot = contrib_tbl.loc[A.OBJ_DISPLAY, disj].sum(axis=1)
    assert (tot <= 100.5).all(), f"contribution > 100% for {tot[tot > 100.5].index.tolist()}"

    for name, tbl in [("contribution", contrib_tbl), ("efficiency", eff_tbl), ("raw", raw_tbl)]:
        tbl.to_csv(A.run_dir / f"consequences_{name}.csv")
    print(f"wrote consequences_{{contribution,efficiency,raw}}.csv -> {A.run_dir.relative_to(config.PROJECT_DIR)}")
    A.contrib_tbl, A.eff_tbl, A.raw_tbl = contrib_tbl, eff_tbl, raw_tbl
    return contrib_tbl, eff_tbl, raw_tbl


def plain_language(A):
    print(f"{A.region_label} — per-area strongest / weakest inputs (by relative richness):\n")
    for prefix, kind, C in _blocks(A):
        for cid in C["ids"]:
            label = f"{prefix}-{cid}" if prefix else str(cid)
            order = np.argsort(C["profs"][cid])
            strongest = ", ".join(np.array(A.OBJ_DISPLAY)[order[::-1][:3]])
            weakest = ", ".join(np.array(A.OBJ_DISPLAY)[order[:3]])
            print(f"  {label:22s} strongest: {strongest}   |   weakest: {weakest}")


def heatmaps(A):
    def heatmap(tbl, title, fname):
        opts = [c for c in tbl.columns if c != "unit"]
        M = tbl.loc[A.OBJ_DISPLAY, opts].to_numpy(dtype=float)
        rmin = np.nanmin(M, axis=1, keepdims=True); rmax = np.nanmax(M, axis=1, keepdims=True)
        norm = np.where(rmax > rmin, (M - rmin) / (rmax - rmin), 0.5)
        words = np.empty(M.shape, dtype=object)
        for i in range(M.shape[0]):
            lo, hi = np.nanpercentile(M[i], [100/3, 200/3])
            words[i] = np.where(M[i] >= hi, "High", np.where(M[i] <= lo, "Low", "Med"))
        fig, ax = plt.subplots(figsize=(2.2 + 0.7*len(opts), 0.72*len(A.OBJ_DISPLAY) + 1.8))
        ax.imshow(norm, cmap="YlGn", aspect="auto", vmin=0, vmax=1)
        ax.set_xticks(range(len(opts))); ax.set_xticklabels(opts, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(A.OBJ_DISPLAY))); ax.set_yticklabels(A.OBJ_DISPLAY, fontsize=9)
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                ax.text(j, i, words[i, j], ha="center", va="center", fontsize=7, fontweight="bold",
                        color="white" if norm[i, j] > 0.6 else "black")
        ax.set_xticks(np.arange(-.5, len(opts), 1), minor=True)
        ax.set_yticks(np.arange(-.5, len(A.OBJ_DISPLAY), 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=1.5); ax.tick_params(which="minor", length=0)
        ax.set_title(title, fontsize=12, pad=10); fig.tight_layout()
        fig.savefig(A.fig_dir / fname, dpi=150, bbox_inches="tight"); plt.show()

    heatmap(A.contrib_tbl, f"{A.region_label} — contribution (High/Med/Low per objective)", "consequences_heatmap_contribution.png")
    heatmap(A.eff_tbl, f"{A.region_label} — efficiency (High/Med/Low per objective)", "consequences_heatmap_efficiency.png")
