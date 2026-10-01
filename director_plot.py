"""director_plot -- the director package's shared plotting state and helpers (split out of 20_figures on 2026-09-14
so that 20 (every output, the record) and 21_director_outputs (the curated few for the presentation) draw from ONE
codebase). `C = load()` reads the products 19 wrote (surfaces, tiers, clusters, tables) and returns a namespace whose
drawing helpers are closed over that state; a notebook can `globals().update(vars(C))` to use the bare names
(draw_pa, draw_hex, finish, ...) exactly as 20 always has. Cartography is pixel space: 1 px = 1 km on the Y2Y grid, and every pixel constant is a km constant x C.PX_PER_KM, so a frame on
another grid (the northern corridors at 300 m, via load_frame) draws the same layout."""
import json
import textwrap
from types import SimpleNamespace

import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd
import logging
import math
import pathlib
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Patch, Rectangle, FancyBboxPatch
from matplotlib.collections import PolyCollection
from matplotlib.colors import ListedColormap, BoundaryNorm, Normalize
from matplotlib.cm import ScalarMappable

import config
import director_core as dc

PA_COLOR, IPCA_COLOR, CL_COLOR = "#8f8f8f", "#ff6a00", "crimson"     # IPCA orange: legible on viridis
NEVER_COLOR = "#e6e6e6"                                                # hexes with F = 0 exactly
BAND_COLORS = ["#f2f2f2", "#1f3a63", "#5b87ad", "#ffd93b", "#e6550d"]
BAND_BOUNDS = [-0.001, 0.05, 0.30, 0.70, 0.95, 1.001]
BAND_NAMES = ["never (<5% of plans)", "rare (5–30%)", "conditional (30–70%)", "frequent (70–95%)", "always (≥95%)"]


def _border_kw():
    """draw_admin kwargs for the international border from STYLE['border_style'] = (colour, lw, dash) or None (= draw_admin's defaults: #4a4a4a, 1.0, solid)."""
    b = STYLE.get("border_style")
    return dict(border_color=b[0], border_lw=b[1], border_dash=b[2]) if b else {}


def load_frame(G, *, overlay=None, window=None, note="", towns=None, pa_min_km2=None):
    """The drawing state for ANY director_core-style grid G, with no package files -- split out of load() on 2026-09-28 so a
    package on another grid (the northern corridors at 300 m: `corridors_director.director_frame`) draws on the same wide layout
    from the same code. Builds the basemap, hillshade, admin lines, named PAs, the overlay in the IPCA role, the pixel WINDOW
    every frame-level map clips to, and the closures over them (rings_px, draw_pa, draw_ipca, finish). Every pixel constant in
    the layout is a km constant x PX_PER_KM (= 1000 / cell size), which is exactly 1 on the 1 km grid, so the Y2Y and Alberta
    outputs are unchanged to the pixel. `towns` = {name: (lat, lon)} for the basemap (default director_core.Y2Y_TOWNS);
    `note` = the corner note finish() writes by default."""
    IP = overlay or dc.ipca_layer(G)
    IP_LABEL = getattr(IP, "label", "Proposed IPCAs (not locked in)")      # legend wording (Ethan 2026-09-30)
    BM = dc.basemap_layer(G, towns=towns)
    PAN = dc.pa_layer(G, STYLE["pa_layer_min_km2"] if pa_min_km2 is None else pa_min_km2)   # named PAs for the inset / locator labels (display only)
    ADMIN = dc.admin_layer(G)
    WINDOW = tuple(float(v) for v in window) if window is not None else None        # frame-level maps clip to it (None = the whole frame)
    PX_PER_KM = 1000.0 / abs(G.transform.a)                                          # 1 on the 1 km grid, 3.33 on the 300 m corridor grid
    if WINDOW is None:
        HS, HS_EXTENT = dc.read_hillshade(G), None                                    # the raster IS the frame: pixel space
    else:                                                                            # a windowed frame: the hillshade covers the WINDOW (which may run past the raster
        HS = dc.read_hillshade_window(G, WINDOW, scale=1)                            # edge -- the northern frame), one sample per grid pixel, drawn at the window's extent;
        HS_EXTENT = (WINDOW[0], WINDOW[1], WINDOW[3], WINDOW[2])                     # identical values to the raster read on an integer window inside the raster (Alberta)

    halo = [pe.withStroke(linewidth=2.5, foreground="white")]
    PAg = np.full(G.shape, np.nan, np.float32); PAg[G.locked2d] = 1.0
    PA_GDF = gpd.read_file(config.PA_VECTOR).to_crs(G.crs) if STYLE.get("pa_fill_all", False) else None
    if STYLE.get("pa_fill_all", False):                          # every protected-area cell grey, planning unit or not (Ethan 2026-09-30: "they should still show as
        from rasterio import features as _rf                      # protected areas") -- the icefields inside Jasper / Banff (no carbon data, so not PU) and the parks
        _foot = _rf.rasterize(((g, 1) for g in PA_GDF.geometry), out_shape=G.shape, transform=G.transform,   # beyond the PU edge
                              fill=0, dtype="uint8").astype(bool)
        PAg[_foot] = 1.0

    def rings_px(geom):
        polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        out = []
        for p in polys:
            x, y = np.asarray(p.exterior.coords)[:, :2].T      # some proposals carry a Z coordinate
            px, py = dc.xy_to_px(G, x, y)
            out.append(np.c_[px, py])
        return out

    PAB = dc.pa_layer(G, 0) if STYLE.get("pa_borders") else None            # every PA, dissolved by name: the light borders between adjoining parks

    def draw_pa(ax):
        ax.imshow(PAg, cmap=ListedColormap([PA_COLOR]), alpha=STYLE.get("pa_alpha", 1.0), interpolation="nearest", zorder=1)   # pa_alpha: the northern maps (0.85); y2y 1.0
        if PAB is not None:
            col, lw, al = STYLE["pa_borders"]
            for g in PAB.geometry:
                for ring in rings_px(g):
                    ax.plot(ring[:, 0], ring[:, 1], color=col, lw=lw * STYLE.get("_lw_scale", 1.0), alpha=al, zorder=1.05, solid_capstyle="round")

    def draw_ipca(ax, lw=1.3):
        for _, r in IP.gdf.iterrows():
            ls = r["ls"] if "ls" in IP.gdf.columns and r["ls"] is not None else "-"     # an overlay may carry its own linestyle per polygon
            for ring in rings_px(r.geometry):
                ax.plot(ring[:, 0], ring[:, 1], color=IPCA_COLOR, lw=lw, ls=ls, zorder=3.5)

    def place_cluster_numbers(ax, win=None):
        """The cluster numbers as the northern route options draw theirs (Ethan 2026-09-30): a white disc rimmed in the cluster's
        colour, the number inside, no leader line, sitting just OUTSIDE the cluster's convex hull at the hull-edge point nearest to
        actual cluster cells -- so it never covers the cluster, not even a gap between its fragments, yet stays adjacent to it --
        clear of every text already on the axes, of the other discs and of the towns. Runs after a panel's labels and limits exist
        (finish / _draw_inset)."""
        marks = getattr(ax, "_cluster_marks", [])
        if not marks:
            return
        from matplotlib.transforms import Bbox
        from scipy import ndimage as _ndi
        fig = ax.figure; r = fig.canvas.get_renderer()
        if win is None:
            x0, x1 = sorted(ax.get_xlim()); y0, y1 = sorted(ax.get_ylim()); win = (x0, x1, y0, y1)
        H, W = G.shape
        wx0, wx1 = int(max(np.floor(win[0]), 0)), int(min(np.ceil(win[1]), W)); wy0, wy1 = int(max(np.floor(win[2]), 0)), int(min(np.ceil(win[3]), H))
        if wx1 - wx0 < 4 or wy1 - wy0 < 4:
            return
        sl = (slice(wy0, wy1), slice(wx0, wx1))                                  # every distance field on the panel's window only
        blocked = np.zeros((wy1 - wy0, wx1 - wx0), bool)
        for _, _, env, _, _ in marks:
            blocked |= env[sl]
        clear = _ndi.distance_transform_edt(~blocked) if blocked.any() else np.full(blocked.shape, np.inf)   # distance to the nearest envelope cell
        texts = [t.get_window_extent(r) for t in ax.texts if t.get_visible() and t.get_text().strip()]
        towns_px = np.array([dc.xy_to_px(G, x, y) for x, y in BM.towns.values()]) if getattr(BM, "towns", None) else np.zeros((0, 2))
        ext = ax.get_window_extent(r); data_per_disp = (win[1] - win[0]) / max(ext.width, 1e-6); pt_px = fig.dpi / 72.0
        placed = []
        for num, raw, env, col, fs_ in marks:
            if not raw[sl].any():
                continue                                                         # this cluster is not in this panel
            rad_disp = 0.85 * fs_ * pt_px; rad = rad_disp * data_per_disp; margin = rad + 3.0 * data_per_disp * pt_px
            d_env = _ndi.distance_transform_edt(~env[sl])                         # distance outside this cluster's hull
            lab_, n_ = _ndi.label(raw[sl], structure=np.ones((3, 3)))              # its MAIN BODY (largest fragment in this panel), not an outlier speck
            body = (lab_ == (np.bincount(lab_.ravel())[1:].argmax() + 1)) if n_ > 1 else raw[sl]
            d_raw = _ndi.distance_transform_edt(~body)                             # distance to the main body
            chosen = None; best = None                                           # rings of growing radius: the disc never sits on a name while a clear spot exists further out (Ethan 2026-09-30)
            for k, mult in enumerate(STYLE.get("cluster_number_rings", (1.0, 1.6, 2.4, 3.5, 5.0, 7.0))):
                m_ = margin * mult
                ring = (d_env >= m_) & (d_env <= m_ + 2.5)
                ys, xs = np.nonzero(ring)
                if not len(xs):
                    continue
                order = np.argsort(d_raw[ys, xs], kind="stable")                 # nearest to the real cluster first
                step = max(1, len(order) // 3000)
                for j in order[::step]:
                    cx, cy = float(xs[j] + wx0), float(ys[j] + wy0)
                    if not (win[0] + rad < cx < win[1] - rad and win[2] + rad < cy < win[3] - rad):
                        continue
                    if clear[ys[j], xs[j]] < rad + STYLE.get("cluster_number_gap_px", 1.5):    # the whole disc clear of every cluster's hull
                        continue
                    if len(towns_px) and (np.hypot(towns_px[:, 0] - cx, towns_px[:, 1] - cy) < 2.5 * rad).any():
                        continue
                    c = ax.transData.transform((cx, cy)); bb = Bbox([[c[0] - rad_disp, c[1] - rad_disp], [c[0] + rad_disp, c[1] + rad_disp]])
                    n_over = sum(bb.overlaps(t) for t in texts) + sum(bb.overlaps(pb) for pb in placed)
                    if n_over == 0:
                        chosen = (cx, cy, bb); break
                    if k == 0 and (best is None or n_over < best[0]):
                        best = (n_over, cx, cy, bb)                              # the least-covered spot on the innermost ring, the last resort
                if chosen is not None:
                    break
            if chosen is None and best is not None:                              # nothing clear on any ring: the innermost spot covering the fewest labels
                chosen = best[1:]
            if chosen is None:
                continue
            cx, cy, bb = chosen
            ax.text(cx, cy, num, fontsize=fs_, fontweight=600, ha="center", va="center", zorder=8, clip_on=True, color=TABLE["ink"],
                    bbox=dict(boxstyle="circle,pad=0.3", fc="white", ec=col, lw=STYLE.get("cluster_number_rim_lw", 1.8)))
            placed.append(bb)
        ax._cluster_marks = []

    def finish(ax, title, handles, note=note, legend_loc="upper right", scale=True, names=None, towns=None, name_fs=None):
        names_ = STYLE["province_names"] if names is None else names
        if WINDOW is None:
            dc.draw_basemap(ax, G, BM, hs=HS if STYLE["hillshade"] else None, water=STYLE["water"],
                            names=names_, towns=STYLE["towns"] if towns is None else towns,
                            name_fs=name_fs, fs_scale=STYLE.get("_fs_scale", 1.0), avoid_sw=scale, skip=STYLE["main_skip_codes"])   # ocean / land / hillshade / water / outline / names
        else:                                                         # a windowed package: labels and towns filtered to the window, codes at their poles
            dc.draw_basemap(ax, G, BM, hs=HS if STYLE["hillshade"] else None, water=STYLE["water"], names=False, hs_extent=HS_EXTENT,
                            towns=STYLE["towns"] if towns is None else towns, fs_scale=STYLE.get("_fs_scale", 1.0), window=WINDOW, avoid_sw=scale)
            if names_:
                dc.label_jurisdictions_window(ax, G, BM, WINDOW, fs=(name_fs or STYLE["wide_main_name_fs"]) * STYLE.get("_fs_scale", 1.0),
                                              avoid_sw=scale, skip=STYLE["main_skip_codes"], **STYLE.get("main_codes", {}))   # main_codes: force / inside / at, as the insets' codes (Alberta: BC pinned)
        dc.draw_admin(ax, G, ADMIN, **_border_kw())                   # coast, admin lines, border (border_style: the international border's colour / lw / dash)
        if STYLE["lat53"]:
            dc.graticule(ax, G, lats=(53,), lons=(), emph_lat=53)     # the 53°N line (E17 tie-in) -- off by default (Ethan 2026-09-14)
        if WINDOW is None:
            ax.set_xlim(0, G.shape[1]); ax.set_ylim(G.shape[0], 0)
        else:
            ax.set_xlim(WINDOW[0], WINDOW[1]); ax.set_ylim(WINDOW[3], WINDOW[2])
        if scale:                                                     # scale bar + north arrow, south-west corner (ocean)
            if WINDOW is None:
                if STYLE.get("frame_north_arrow_beside_bar", True):       # the arrow LEFT of the bar, rising from its baseline (Ethan 2026-09-30, the Y2Y frame)
                    W_, H_ = G.shape[1], G.shape[0]; gap = STYLE.get("frame_north_arrow_gap", 0.05) * W_
                    xa = 0.05 * W_; y1 = (1 - 0.04) * H_; y0 = y1 - 70 * PX_PER_KM
                    dc.scalebar(ax, G, loc=(0.05 + gap / W_, 0.04), fs=STYLE["legend_fs"] - 1)      # the bar shifted right to make room
                    ax.annotate("", xy=(xa, y0), xytext=(xa, y1), arrowprops=dict(arrowstyle="-|>", color="black", lw=1.4, mutation_scale=14), zorder=5)
                    ax.annotate("N", xy=(xa, y0), xytext=(0, dc.SCALEBAR_GAP_PT), textcoords="offset points", ha="center", va="bottom", fontsize=STYLE["legend_fs"] - 1, fontweight=600, zorder=5)
                else:
                    dc.scalebar(ax, G, loc=(0.05, 0.04), fs=STYLE["legend_fs"] - 1); dc.north_arrow(ax, G, loc=(0.075, 0.075), fs=STYLE["legend_fs"] - 1)
            else:                                                     # the same corner of the WINDOW, in pixel units (km x PX_PER_KM)
                px0, px1, pyt, pyb = WINDOW; km = STYLE["window_scale_km"]; L = km * PX_PER_KM     # lengths / offsets = km x px_per_km
                x, y = px0 + 0.05 * (px1 - px0), pyb - 0.04 * (pyb - pyt)
                _left = STYLE.get("window_north_arrow_left", False)                 # the Y2Y frame's construction (Ethan 2026-09-30): the arrow LEFT of the bar on its baseline, N above the tip
                if _left:
                    xa_left = x; x = x + STYLE.get("frame_north_arrow_gap", 0.05) * (px1 - px0)   # the bar shifted right to make room, as on the Y2Y frame
                if STYLE.get("scalebar_box", False):                        # an opaque white backing under the bar + label, so nothing shows through it (Alberta, Ethan 2026-09-30)
                    _fs = STYLE["legend_fs"] - 1; _pt = (px1 - px0) / max(ax.get_window_extent(ax.figure.canvas.get_renderer()).width, 1e-6) * ax.figure.dpi / 72.0   # data px per pt
                    _h = 6 * PX_PER_KM + 1.35 * _fs * _pt; _pad = 5 * PX_PER_KM
                    ax.add_patch(Rectangle((x - _pad, y - _h - _pad), L + 2 * _pad, _h + 2 * _pad + 2, facecolor="white", edgecolor="none", alpha=1.0, zorder=4.9))
                ax.plot([x, x + L], [y, y], color="black", lw=2.5, solid_capstyle="butt", zorder=5)
                ax.annotate(f"{km} km", xy=(x + L / 2, y), xytext=(0, dc.SCALEBAR_GAP_PT), textcoords="offset points", ha="center", va="bottom", fontsize=STYLE["legend_fs"] - 1, zorder=5)
                if _left:
                    _pt = (px1 - px0) / max(ax.get_window_extent(ax.figure.canvas.get_renderer()).width, 1e-6) * ax.figure.dpi / 72.0   # data px per pt
                    _Lpx = (STYLE.get("north_arrow_pt") or 11) * _pt                  # the Y2Y frame's 70 km arrow is ~11 pt
                    ax.annotate("", xy=(xa_left, y - _Lpx), xytext=(xa_left, y), arrowprops=dict(arrowstyle="-|>", color="black", lw=1.4, mutation_scale=14), zorder=5)
                    ax.annotate("N", xy=(xa_left, y - _Lpx), xytext=(0, dc.SCALEBAR_GAP_PT), textcoords="offset points", ha="center", va="bottom", fontsize=STYLE["legend_fs"] - 1, fontweight=600, zorder=5)
                    xa = None
                elif STYLE.get("north_arrow_beside_bar", False):          # the arrow beside the bar, rising from its baseline (wolverine, 2026-09-29)
                    xa, y1 = x + L + 0.06 * (px1 - px0), y; y0 = y1 - 0.06 * (pyb - pyt)
                else:
                    xa, y1 = px0 + 0.075 * (px1 - px0), pyb - 0.075 * (pyb - pyt); y0 = y1 - 0.06 * (pyb - pyt)
                if _left:
                    pass                                                  # drawn above
                elif STYLE.get("north_arrow_pt"):                         # a fixed arrow length in POINTS (the Y2Y-wide frame's 70 km arrow is ~11 pt), so every frame's arrow matches (Alberta, 2026-09-30)
                    _L = STYLE["north_arrow_pt"]
                    ax.annotate("", xy=(xa, y1 - 0.0), xytext=(0, -_L), textcoords="offset points", arrowprops=dict(arrowstyle="-|>", color="black", lw=1.4, mutation_scale=14), zorder=5)
                    ax.annotate("N", xy=(xa, y1), xytext=(0, -_L - 3), textcoords="offset points", ha="center", va="top", fontsize=STYLE["legend_fs"] - 1, fontweight=600, zorder=5)
                else:
                    ax.annotate("", xy=(xa, y0), xytext=(xa, y1), arrowprops=dict(arrowstyle="-|>", color="black", lw=1.4, mutation_scale=14), zorder=5)
                    ax.text(xa, y0 - 6 * PX_PER_KM, "N", ha="center", va="bottom", fontsize=STYLE["legend_fs"] - 1, fontweight=600, zorder=5)
        dc.corner_note(ax, note)
        if not STYLE.get("_defer_numbers", False):                    # _wide_map places the frame's discs itself, after the inset tags exist
            place_cluster_numbers(ax)                                 # the cluster discs, once every label is on the axes
        ax.set_title(title, fontsize=11.5)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
        lkw = dict(fontsize=STYLE["legend_fs"], frameon=True, framealpha=0.92, edgecolor="#9a9a9a", handler_map=cluster_handler_map(*(handles or [])))
        if legend_loc == "none" or not handles:
            pass
        elif handles and legend_loc == "outside":       # beside the frame, top right (the single-panel assets)
            ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0), **lkw)
        elif handles and legend_loc == "lower left":    # south-west corner above the scale bar: for maps whose NE corner is full
            ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, 0.12), **lkw)
        elif handles:                                    # north-east corner inside the frame (the paired record figures)
            ax.legend(handles=handles, loc="upper right", bbox_to_anchor=(1.0, 1.0), **lkw)

    IPCA_HANDLE = Patch(facecolor="none", edgecolor=IPCA_COLOR, label=IP_LABEL)
    if "legend" in getattr(IP, "gdf", pd.DataFrame()).columns:                    # one entry per overlay polygon (its own linestyle + words): the Upper Smoky pair (Ethan 2026-09-30)
        IPCA_HANDLES = [Patch(facecolor="none", edgecolor=IPCA_COLOR, ls=(r["ls"] if "ls" in IP.gdf.columns and r["ls"] is not None else "-"), label=str(r["legend"]))
                        for _, r in IP.gdf.iterrows() if str(r["legend"])]
    else:
        IPCA_HANDLES = [IPCA_HANDLE]
    BASE_HANDLES = [Patch(facecolor=PA_COLOR, label="Protected areas (locked in)"),
                    Patch(facecolor="none", edgecolor=CL_COLOR, label="numbered = deck picks")]      # ("never selected" dropped, Ethan 2026-09-14)

    _skip = {"overlay", "window", "note", "towns", "pa_min_km2"}
    ns = {k: v for k, v in locals().items() if not k.startswith("_") and k not in _skip}
    return SimpleNamespace(**ns)


def load(pkg=None, allow_partial=False, *, grid=None, manifest=None, overlay=None, window=None, hex_grid=True, towns=None, context=None, focus=None):
    """Load the package products written by 19 and build the drawing helpers over them.
    Defaults = the Y2Y-wide package. Another package on the same 1 km grid (the Alberta mirror, 2026-09-15) passes its own
    `grid` (a director_core-style G), `manifest` (path), `overlay` (SimpleNamespace(gdf, mask2d, label) in the IPCA role;
    a `ls` column on the gdf sets each polygon's linestyle), a pixel `window` (x0, x1, y_top, y_bottom) that every
    frame-level map is clipped to, hex_grid=False to skip the 250 km2 lattice it does not use, and `towns` = its own gazetteer
    {name: (lat, lon)} for the basemap (default director_core.Y2Y_TOWNS; the Alberta package adds director_core.ALBERTA_TOWNS).
    `context` = another package's geotiffs dir on the same grid (the Y2Y-wide package for the Alberta maps, Ethan 2026-09-30): its core
    surface and Act 2 tiers are drawn BEYOND this package's PU at STYLE['context_alpha'], the PU outlined as the area of focus;
    `focus` = the 2-D mask to outline (default: the PU with its enclosed holes filled -- the raw PU would trace every icefield inside a park)."""
    PKG = pkg or (dc.PKG / "_smoke" if allow_partial else dc.PKG)
    GEO, TAB, FIGD = PKG / "geotiffs", PKG / "tables", PKG / "figures"
    assert (PKG / "summary.json").exists(), "run 19_tiers_and_clusters first"
    S = json.loads((PKG / "summary.json").read_text())
    G = grid or dc.grid()
    MAN = dc.package_manifest(pd.read_csv(manifest or dc.MANIFEST))
    assert S.get("version", "v2") == dc.VP.version, f"summary.json is from {S.get('version', 'v2')}, VERSION is {dc.VP.version} -- re-run 19"

    def rd(name):
        with rasterio.open(GEO / name) as src:
            return src.read(1)[G.pu]
    Fens, Ug = rd("F_guarded.tif"), rd("union_membership_guarded.tif")           # ensemble F (the paper's Claim-A estimand; appendix in the deck)
    CORE_BASIS = S.get("core_basis", "ensemble")                                   # package spec v2.1 (2026-09-23): "balanced" = the S0 pooled guarded f
    Fg = rd("f_balanced_core.tif") if CORE_BASIS == "balanced" else Fens          # THE core surface every Act 1 asset draws (F >= 0.70 = the core)
    Fp = rd("F_unguarded.tif") if (GEO / "F_unguarded.tif").exists() else (rd("f_unguarded_reference.tif") if (GEO / "f_unguarded_reference.tif").exists() else None)   # v4: reference cell only
    with rasterio.open(GEO / "act_tiers_guarded.tif") as src:
        TIERS = src.read(1)
    LAB = dict(np.load(GEO / "cluster_labels.npz"))
    PICKS = pd.read_csv(TAB / "picks.csv", dtype={"number": str, "cids": str, "members": str})
    TD1 = pd.read_csv(TAB / "T-D1_cluster_register.csv", dtype={"number": str})
    TD7 = pd.read_csv(TAB / "T-D7_consequences.csv")                       # consequences record: picks + reference rows (PAs, IPCAs)
    TD2a, TD2b = pd.read_csv(TAB / "T-D2_bands.csv"), pd.read_csv(TAB / "T-D2_acts.csv")
    TD3 = pd.read_csv(TAB / "T-D3_scenarios.csv")
    TD6 = pd.read_csv(TAB / "T-D6_value_coverage.csv"); XT = pd.read_csv(TAB / "hinge_crosstab.csv", index_col=0)
    VAL = {t: rd(f"value_top30_{t.replace(' ', '_')}.tif").astype(bool) for t in dc.VALUE_THEMES + ["naturalness"]}
    CONV = rd("value_convergence.tif").astype(np.uint8); GAP = rd("value_gap.tif").astype(np.uint8)
    SV, BIO = S["value"], S["biodiversity_plan_capture"]
    E17 = pd.read_csv(TAB / "E17_shifts.csv") if (TAB / "E17_shifts.csv").exists() else pd.DataFrame(columns=["block_out", "delta_lat"])
    POOL = {}
    for rec in S["pooling"]:
        sid = rec["scenario"]
        fids = [f for f in MAN[MAN.scenario_id == sid].formulation_id if f in S["forms"]]
        if rec["decision"].startswith("POOLED"):
            POOL[sid] = np.mean([rd(f"f_guarded_{f}.tif") for f in fids], axis=0)
        elif rec["decision"].startswith("SEPARATE"):
            for f in fids:
                POOL[f"{sid}@{'245' if 'ssp245' in f else '585'}"] = rd(f"f_guarded_{f}.tif")
        else:
            POOL[sid] = rd(f"f_guarded_{fids[0]}.tif")
    assert set(POOL) == set(S["pool_keys"]), "pooling keys drifted from 19"
    CL = {lyr: gpd.read_file(GEO / "clusters.gpkg", layer=lyr) for lyr in gpd.list_layers(GEO / "clusters.gpkg").name}
    HEX = {dc.HEX_KM2: dc.hex_grid(G, dc.HEX_KM2)} if hex_grid else {}
    # ramp purple -> green for F < 0.70 (viridis truncated before its own yellow): the CORE (>= 0.70) is the only
    # yellow on the map and reads as a category, not the top of the gradient; F = 0 falls under -> NEVER_COLOR
    FCMAP = ListedColormap(plt.get_cmap("viridis")(np.linspace(0, 0.70, 256))); FCMAP.set_over("#ffd93b"); FCMAP.set_under(NEVER_COLOR)
    FNORM = Normalize(1e-9, dc.FREQ_THR)
    N_NOTE = ((f"balanced scenario · 2 refugia futures × 51 near-optimal plans · no value theme left more than {100 * S['floor_g']:.0f}% behind")
              if CORE_BASIS == "balanced" else
              (f"n = {S['n_formulations']} formulations × 51 near-optimal plans · no value theme left more than {100 * S['floor_g']:.0f}% behind"))
    # the frame -- basemap, hillshade, admin lines, named PAs, the overlay, the window and the closures over them -- is
    # load_frame's (shared with packages on other grids, 2026-09-28); its members are re-bound here so `globals().update(vars(C))`
    # exposes the same names as always
    _frame = load_frame(G, overlay=overlay, window=window, note=N_NOTE, towns=towns)
    CTX_F = CTX_TIERS = CTX_OWNER = None; CONTEXT_HANDLE = None
    if context is not None:                                                        # the whole allocation of the context analysis, outside this PU only
        _cg = pathlib.Path(context)
        with rasterio.open(_cg / ("f_balanced_core.tif" if CORE_BASIS == "balanced" else "F_guarded.tif")) as _s:
            CTX_F = _s.read(1).astype(np.float32)
        with rasterio.open(_cg / "act_tiers_guarded.tif") as _s:
            CTX_TIERS = _s.read(1)
        with rasterio.open(_cg / "act2_owner.tif") as _s:
            CTX_OWNER = _s.read(1)
        CTX_F[G.pu] = np.nan; CTX_F[CTX_F <= 0] = np.nan                            # the focus PU draws itself; never-selected context land stays basemap
        if STYLE.get("context_label"):                                              # None = no legend entry for the context surface (Ethan 2026-09-30)
            CONTEXT_HANDLE = Patch(facecolor=plt.get_cmap("viridis")(0.45), alpha=STYLE["context_alpha"], label=STYLE["context_label"])

    if CTX_F is not None:
        from scipy import ndimage as _ndi
        FOCUS = np.asarray(focus, dtype=bool) if focus is not None else _ndi.binary_fill_holes(G.pu)   # the outer boundary only: no outline around the non-PU holes (icefields)
    else:
        FOCUS = None

    def draw_focus(ax):
        """The focus region's outline when a context surface is drawn around it (FOCUS: the extent polygon, or the hole-filled PU)."""
        if FOCUS is None or not STYLE.get("focus_outline"):
            return
        col, lw = STYLE["focus_outline"]
        ax.contour(FOCUS.astype(np.uint8), levels=[0.5], colors=[col], linewidths=lw * STYLE.get("_lw_scale", 1.0), zorder=3.3)

    IP, IP_LABEL, BM, HS, HS_EXTENT, PAN, ADMIN, WINDOW, PX_PER_KM = (_frame.IP, _frame.IP_LABEL, _frame.BM, _frame.HS, _frame.HS_EXTENT, _frame.PAN,
                                                                     _frame.ADMIN, _frame.WINDOW, _frame.PX_PER_KM)
    halo, PAg, rings_px, draw_pa, draw_ipca, finish = _frame.halo, _frame.PAg, _frame.rings_px, _frame.draw_pa, _frame.draw_ipca, _frame.finish
    place_cluster_numbers = _frame.place_cluster_numbers
    IPCA_HANDLE, IPCA_HANDLES, BASE_HANDLES = _frame.IPCA_HANDLE, _frame.IPCA_HANDLES, _frame.BASE_HANDLES

    def draw_hex(ax, hm, cmap, norm, alpha=1.0):
        ok = hm[np.isfinite(hm.value)]
        verts = [rings_px(g)[0] for g in ok.geometry]
        ax.add_collection(PolyCollection(verts, facecolors=cmap(norm(ok.value.values)), edgecolors="none", alpha=alpha, zorder=0.5))
        ax.set_aspect("equal")
        ax.set_xlim(0, G.shape[1]); ax.set_ylim(G.shape[0], 0)

    def draw_clusters(ax, layer, numbers, color=CL_COLOR, lw=0.9, fs=10):
        """Outlines + numbers; a numbered cluster takes its own colour from STYLE["cluster_colors"] (white halo under both)."""
        g = CL.get(layer)
        if g is None:
            return
        lw = lw * STYLE.get("_lw_scale", 1.0)
        ring_halo = [pe.withStroke(linewidth=lw + 1.4, foreground="white", alpha=0.85)] if STYLE["cluster_halo"] else None
        for _, r in g.iterrows():
            num = numbers.get(int(r.cid), (None, False))[0]
            picked = num not in (None, "") and str(num).isdigit()
            if not picked and layer == "act1" and not STYLE["draw_unpicked"]:
                continue
            col = STYLE["cluster_colors"].get(int(num), color) if picked else color
            for ring in rings_px(r.geometry):
                ax.plot(ring[:, 0], ring[:, 1], color=col, lw=lw, zorder=4, path_effects=ring_halo)
            if int(r.cid) in numbers and numbers[int(r.cid)][1]:            # the number: a rimmed disc placed AFTER the labels exist (place_cluster_numbers)
                cids = [c for c, (n, _) in numbers.items() if n == num]
                from rasterio import features as _rf
                mask = _rf.rasterize(((gg, 1) for gg in g[g.cid.isin(cids)].geometry), out_shape=G.shape, transform=G.transform, fill=0, dtype="uint8").astype(bool)
                # the cluster's ENVELOPE = its convex hull (Ethan 2026-09-30: a disc in a gap between fragments still "covers the cluster");
                # the disc goes just outside the hull, at the hull-edge point NEAREST to actual cluster cells (place_cluster_numbers)
                hull = g[g.cid.isin(cids)].geometry.unary_union.convex_hull
                env = _rf.rasterize([(hull, 1)], out_shape=G.shape, transform=G.transform, fill=0, dtype="uint8").astype(bool) | mask
                ax._cluster_marks = getattr(ax, "_cluster_marks", []) + [(str(num), mask, env, col, fs)]


    def picks_for(act, key=None):
        """{member cid: (number, is_anchor)} for every component of every pick; the number is drawn once, at the anchor."""
        p = PICKS[PICKS.act == act]
        if key is not None:
            p = p[p.key == key]
        out = {}
        for _, r in p.iterrows():
            for c in str(r.cids).split(";"):
                out[int(c)] = (str(r.number), int(c) == int(r.cid))
        return out

    def star_rows(rows, color):
        """One star per pick; a cluster with its own colour in STYLE["cluster_colors"] keeps it here (map ↔ stars ↔ numbers)."""
        return [dict(title=f"{cluster_label(r, wrap=36)}\n{r.area_km2:,.0f} km²"
                           + (f"\nADEQUACY PIN: only {r.adequacy_pin_class} on the extent" if bool(r.get("adequacy_pin", False)) else ""),
                     values={a: r[f"pct_{a}"] for a in dc.STAR_AXES}, color=STYLE["cluster_colors"].get(int(r.number), color))
                for _, r in rows.iterrows()]

    def numbered(act):
        """T-D1 rows of the numbered deck picks for an act ('Act 1' = the core, 'Act 2' = the scenarios), by number."""
        d = TD1[(TD1.act == act) & TD1.number.notna() & (TD1.number != "")].copy()
        d["number"] = d.number.astype(int)
        return d.sort_values("number")

    def consequences_png(rows, path, title):
        """T-D7: the cluster's mean value / the mean over allocatable land, shown as '2.3x' (two decimals below 1, one at or
        above 1), plus the reference rows written by 19 (existing protected areas, the proposed IPCAs); every ratio column is
        tinted red -> green on its own scale across the rows (STYLE['conseq_*'])."""
        ref = TD7[TD7.act.eq("reference")]                                   # written by 19 (empty on a pre-refinement T-D7)
        body = pd.concat([rows, ref], ignore_index=True)
        labels = [f"Cluster {int(n)}" if pd.notna(n) and str(n) not in ("", "nan") else nm for n, nm in zip(body.number, body.name)]
        d = pd.DataFrame({"cluster": labels, "km²": body.area_km2.map("{:,.0f}".format),
                          "mean F": body.mean_guarded_F.map(lambda v: "—" if pd.isna(v) else f"{v:.2f}"),
                          **{a: body[f"ratio_{a}"].map(ratio_fmt) for a in dc.STAR_AXES}})
        if "driving_label" in rows and rows.driving_label.nunique() > 1:
            d.insert(1, "leads with", list(rows.driving_label.values) + [""] * len(ref))
        # colour scale per ratio column, over the rows in STYLE["conseq_scale_rows"] ("all" | "clusters")
        cmap = plt.get_cmap(STYLE["conseq_cmap"]); tint = STYLE["conseq_tint"]
        colors = [[None] * len(d.columns) for _ in range(len(d))]
        scope = np.arange(len(body)) if STYLE["conseq_scale_rows"] == "all" else np.arange(len(rows))
        for a in dc.STAR_AXES:
            j = list(d.columns).index(a); x = np.log(body[f"ratio_{a}"].astype(float).values)
            lo, hi = np.nanmin(x[scope]), np.nanmax(x[scope])
            for i, v in enumerate(x):
                t = 0.5 if hi <= lo else float(np.clip((v - lo) / (hi - lo), 0, 1))
                c = np.array(cmap(t)[:3]); colors[i][j] = tuple(1 - tint * (1 - c))            # blended toward white
        table_png(d, path, title, fs=9, scale=1.6, colw=[2.4] + ([1.6] if "leads with" in d else []) + [0.9, 0.8] + [1.3 if a == "representativeness" else 1.0 for a in dc.STAR_AXES],
                  cell_colors=colors, italic_rows=list(range(len(rows), len(body))))

    ns = {k: v for k, v in locals().items() if not k.startswith("_")}
    ns.update(PA_COLOR=PA_COLOR, IPCA_COLOR=IPCA_COLOR, CL_COLOR=CL_COLOR, NEVER_COLOR=NEVER_COLOR,        # module constants, by name
              BAND_COLORS=BAND_COLORS, BAND_BOUNDS=BAND_BOUNDS, BAND_NAMES=BAND_NAMES, table_png=table_png, ratio_fmt=ratio_fmt)
    return SimpleNamespace(**ns)


AXIS_DISPLAY = {"core habitat": "climate refugia"}     # star / consequences axis words (Ethan 2026-09-21): the layer IS climate refugia; the block name stays in the data


def axis_label(a):
    """The word shown for a star axis / consequences row (T-D1 columns keep the block-axis name)."""
    return AXIS_DISPLAY.get(a, a)


def cluster_label(r, wrap=None):
    """'Cluster N (Region)' -- the region words from the communities lookup (package spec v1.12 decision e) when T-D1 carries
    them and STYLE['cluster_region_labels'] is on; 'Cluster N' otherwise. `wrap` folds the region onto its own line(s)."""
    n = int(r.number) if hasattr(r, "number") else int(r["number"])
    mode = STYLE.get("cluster_region_labels", "region")            # "region" = the region word; "full" = "Sub-region(s), Region"; False = none
    col = {"region": "region", "full": "region_label", True: "region"}.get(mode)
    reg = (getattr(r, col, "") if hasattr(r, col) else r.get(col, "")) if col else ""
    reg = "" if reg is None or (isinstance(reg, float) and np.isnan(reg)) else str(reg)
    if not reg or reg == "nan":
        return f"Cluster {n}"
    return f"Cluster {n}\n({textwrap.fill(reg, wrap)})" if wrap else f"Cluster {n} ({reg})"


def ratio_fmt(v):
    """'0.84×' below 1, '1.0×' / '2.3×' at or above 1 -- decided AFTER rounding to two decimals, so 0.998 prints 1.0× not 1.00×."""
    if pd.isna(v): return "—"
    return f"{v:.2f}×" if round(float(v), 2) < 1 else f"{v:.1f}×"


def table_png(df, path, title, fs=7.5, scale=1.45, colw=None, cell_colors=None, italic_rows=()):
    fig, ax = plt.subplots(figsize=(min(1.6 * len(df.columns) + 2, 22), 0.42 * len(df) + 1.6))
    ax.axis("off")
    t = ax.table(cellText=df.values, colLabels=df.columns, cellLoc="center", loc="center")
    t.auto_set_font_size(False); t.set_fontsize(fs); t.scale(1, scale)
    if colw is not None:                                  # relative column widths (sum -> full table width)
        tot = float(sum(colw))
        for (r, j), cell in t.get_celld().items():
            cell.set_width(colw[j] / tot)
    for j in range(len(df.columns)):
        t[0, j].set_facecolor("#2b4f7d"); t[0, j].set_text_props(color="white", fontweight="bold")
    if cell_colors is not None:                           # per-body-cell fills (row i, col j) or None
        for i, row in enumerate(cell_colors):
            for j, c in enumerate(row):
                if c is not None: t[i + 1, j].set_facecolor(c)
    for i in italic_rows:                                 # reference rows (not clusters)
        for j in range(len(df.columns)): t[i + 1, j].set_text_props(fontstyle="italic")
    ax.set_title(title, fontsize=11, pad=12)
    fig.savefig(path, dpi=STYLE["export_dpi"], bbox_inches="tight"); plt.show()


# ---- the values table (Laura's objectives hierarchy; biodiversity as its own sub-objective) -------------------------
SCENARIOS_FILE = "scenarios_v4.json" if dc.VP.version == "v4" else "scenarios_v2.json"
BLOCK_SHARE = "20%" if dc.VP.version == "v4" else "25%"        # each discretionary block's share in the balanced position


def values_rows(C):
    sc = json.loads((dc.SPEC / SCENARIOS_FILE).read_text()); t0 = sc["S0_balanced"]["targets"]; t4 = sc["S4_carbon"]["targets"]
    efg_t = json.loads((dc.SPEC_REC / "efg_targets.json").read_text())["targets"] if (dc.SPEC_REC / "efg_targets.json").exists() else {}
    pa_pct = C.S["protected_baseline"]["pa_pct_of_region"]; MS = "irrecoverable_carbon_m_soc"
    return [
     ("PROTECT — wildlife have sufficient core habitat", "Quantity of core habitat", "Protected land: today's protected areas are locked in and every plan protects 30% of Y2Y",
      "Y2Y protected areas 2025 (IUCN definitions)", f"The budget: 30% of the region, including the {pa_pct:.0f}% already protected"),
     ("", "Quality of core habitat", "Climate refugia: refugial residence time (1 / backward climate velocity), 2071–2100, two emission futures",
      "AdaptWest 2023, CMIP6 backward climate velocity (8-GCM ensemble)", f"Climate-refugia theme: {BLOCK_SHARE} of the objective in the balanced position; the two futures (SSP2-4.5, SSP5-8.5) are separate value positions"),
     ("", "Quality of core habitat", "Naturalness: 1 − human modification", "Theobald et al., global human modification (gHM v3)",
      "In every formulation at its baseline weight; it cannot move the answer — disclosed, not a driver"),
     ("", "Biodiversity", "Mammal richness (species per km², area-of-habitat maps, all species)", "Lumbierres et al., AOH species richness (mammals)",
      f"Biodiversity theme: {BLOCK_SHARE} (balanced); the two layers weighted equally"),
     ("", "Biodiversity", "Bird richness (species per km², area-of-habitat maps, all species)", "Lumbierres et al., AOH species richness (birds)", ""),
     ("", "Representativeness", f"Presence of {dc.N_EFG} ecosystem functional groups (curated from 40 under the input pre-screen, rule R0)",
      "IUCN Global Ecosystem Typology, indicative maps (Keith et al. 2022)",
      (f"A representation floor, not a weighted theme: rarity-scaled targets of {100*min(efg_t.values()):.0f}–{100*max(efg_t.values()):.0f}% per class, rarity judged in the region + 250 km"
       if efg_t else "A representation floor, not a weighted theme")),
     *([("CONNECT — wildlife corridors connect core habitats", "Structural connectivity", "Habitat connectivity: transboundary omnidirectional current density, valued convexly (current squared: a pinch point is worth more than its share of flow)",
         "Pither et al. 2023 / O'Brien et al. (transboundary extension)", "Structural-connectivity theme: 20% (balanced); no target -- pinch points are places, secured by the shape"),
        ("", "Climate corridors", "Climate corridors: current-flow centrality (breadth of climate-analog flow through a cell)", "Carroll et al. 2018",
         "Climate-corridors theme: 20% (balanced); its own value since manifest v4 (the two connectivity layers are spatially independent)")]
       if dc.VP.version == "v4" else
       [("CONNECT — wildlife corridors connect core habitats", "Quality of connectivity", "Climate corridors: current-flow centrality", "Carroll et al. 2018",
         "Connectivity theme: 25% (balanced); the two layers weighted equally"),
        ("", "Quality of connectivity", "Habitat connectivity: transboundary omnidirectional current density", "Pither et al. 2023 / O'Brien et al. (transboundary extension)", "")]),
     ("ADDRESS CLIMATE CHANGE — keep carbon out of the air", "Carbon", "Irrecoverable carbon in biomass", "Berman & McDowell, irrecoverable carbon",
      f"Carbon theme: {BLOCK_SHARE} (balanced); the two pools split 74 / 26 by mass"),
     ("", "Carbon", "Irrecoverable carbon in mineral soil", "Berman & McDowell, irrecoverable carbon",
      f"Security target: {100*t0[MS]:.0f}% of the regional total ({100*t4[MS]:.0f}% in the carbon-forward position)"),
     ("NOT IN THIS ANALYSIS", "Communities · Water · Cost", "Bear-smart communities; water; dollars", "—",
      "Communities and water were not flushed out in the objectives hierarchy; the 30% area budget stands in for cost"),
    ]

VALUES_COLUMNS = ["fundamental_objective", "sub_objective", "performance_measure", "source", "in_the_analysis"]
VALUES_HEADS = ["Fundamental objective", "Sub-objective", "Performance measure (the layer)", "Source", "How it enters the analysis"]


def grouped_table_png(rows, path, title, colw=(2.2, 1.5, 3.2, 2.4, 3.4), fs=9.0, heads=VALUES_HEADS):
    """A wrapped, row-grouped table: the first column is shaded per group and printed once per group."""
    W = sum(colw); chars = [int(w * 13) for w in colw]                       # ~13 characters per width unit at this font size
    wrapped = [[textwrap.wrap(str(c), ch) or [""] for c, ch in zip(r, chars)] for r in rows]
    heights = [max(len(x) for x in wr) for wr in wrapped]
    line_h = 0.19; row_h = [h * line_h + 0.22 for h in heights]; y_top = sum(row_h) + 0.36
    fig = plt.figure(figsize=(W * 1.05, y_top + 0.6)); ax = fig.add_axes([0.01, 0.01, 0.98, 0.92]); ax.set_xlim(0, W); ax.set_ylim(-0.05, y_top + 0.05); ax.axis("off")
    x_edges = np.r_[0, np.cumsum(colw)]; y = y_top - 0.36                     # header band on top, rows below, nothing clipped
    for j, hd in enumerate(heads):
        ax.add_patch(Rectangle((x_edges[j], y), colw[j], 0.36, facecolor="#2b4f7d", edgecolor="white"))
        ax.text(x_edges[j] + 0.08, y + 0.18, hd, color="white", fontweight="bold", fontsize=fs, va="center")
    y -= 0.36; group_color = {"PROTECT": "#e8f0e6", "CONNECT": "#e6ecf5", "ADDRESS": "#f6ede4", "NOT IN": "#f0f0f0"}; current = None
    for r, wr, rh in zip(rows, wrapped, row_h):
        if r[0]:
            current = r[0]
        fc = next((c for k, c in group_color.items() if current and current.startswith(k)), "white")
        for j in range(len(colw)):
            ax.add_patch(Rectangle((x_edges[j], y - rh), colw[j], rh, facecolor=fc if j == 0 else "white", edgecolor="#cccccc", lw=0.6))
            ax.text(x_edges[j] + 0.08, y - 0.12, "\n".join(wr[j]), fontsize=fs, va="top", fontweight="bold" if j == 0 else "normal")
        y -= rh
    fig.suptitle(title, fontsize=12, y=0.985)
    fig.savefig(path, dpi=STYLE["export_dpi"], bbox_inches="tight"); plt.show()

# ---- ONE place for the presentation knobs (Ethan iterates in 21; a change here reaches 20 and 21 alike) -------------
STYLE = dict(
    cluster_number_fs=13,      # size of the cluster numbers on maps
    cluster_lw=0.9,            # cluster outline width on the Y2Y-wide maps (insets: × cluster_lw_inset_scale)
    cluster_lw_inset_scale=1.5, cluster_halo=True, draw_unpicked=False,           # core complexes that are not deck picks: not outlined
    cluster_colors={1: "#D7263D", 2: "#E040A0", 3: "#1E90FF", 4: "#FF7F00", 5: "#1a1a1a"},   # the core clusters N -> S: red, magenta, blue, dark orange, + near-black for a 5th (the balanced-only comparison core has five, 2026-09-23) (Ethan 2026-09-14; 4 was brown until
                                                                              # 2026-09-21: brown vs red collapsed under protan/deutan, dE 9; dark purple was tried and vanished
                                                                              # into viridis (dE 14); orange clears dE 18 vs the others under every deficiency and 60 vs the ramp)
    core_color="#2b4f7d",      # star fill/line for core clusters
    scenario_color="#a50f2d",  # star fill/line for scenario clusters
    star_fs_axis=20, star_fs_title=20, star_fs_tick=16, star_fs_suptitle=15, star_lw=2.6, star_title=False, star_footnote=False, star_label_pad=1,   # Ethan 2026-09-15: big type, labels tight to the ring
    star_tight=False,          # full canvas (not cropped) so the cluster locators below align panel-for-panel
    locator_fs_scale=1.5, locator_pa_names=2, locator_towns=False, locator_panel_in=4.6,   # the locator windows: 4.6 in squares on the star centres, type scaled up, two park names, no towns
    locator_codes={1: dict(force=["AK"]), 2: dict(skip=["WA"]), 3: dict(skip=["WA"])},   # per-window code edits (Ethan 2026-09-15): AK on the coast of 1; no WA on 2 and 3
    locator_town_skip={},      # {cluster number: (town, ...)} left off that locator window (the towns themselves come from the gazetteer inside the window)
    locator_own_number_only=False,   # True = a locator panel numbers only its own cluster; the other clusters keep their outlines (Alberta 2026-09-30)
    # the Act 1 wide-map inset REGIONS are fixed (Ethan 2026-09-21): the v3.1 windows -- A = the Sacred Headwaters / Stikine window, B = the
    # Purcells / Kootenays window -- in grid pixels (the 1 km grid is identical across manifest versions), re-fitted to the inset aspect;
    # set to None to size the windows on STYLE["inset_clusters"] again
    inset_windows={"A": (174.6, 647.4, 990.0, 1514.0), "B": (570.9, 1103.1, 1826.0, 2416.0)},   # A moved 150 px east (Ethan 2026-09-21): Y2Y land 55% -> 85% of the window, Stewart + the AK border kept at its edge
    # ---- "the optimization behind the map": frames for a timelapse (Ethan 2026-09-21; method_frames) ----
    frames_reference_members=50, frames_sample_per_cell=10,   # every member of the reference cell; a fixed-seed sample of the other 13
    frames_fps=4, frames_hold_s=2.5, frames_seed=0,           # members per second; hold on each surface frame (values, anchor, f, F, core)
    frames_width_px=1920,                                     # frame width; the dpi is derived (13.33 x 7.5 in -> 1920 x 1080, an even HD size H.264 accepts); saved WITHOUT tight bbox so every frame is the same size
    frames_plan_color="#ffd93b", frames_value_color="#7b3294", frames_caption_fs=13,   # plan colour for the balanced scenario (and s5): the Act 2 CORE yellow (Ethan 2026-09-21);
                                                                                      # the theme-forward scenarios take their Act 2 colour from scenario_colors
    frames_climate_words={"ssp585": "SSP5-8.5 future", "ssp245": "SSP2-4.5 future"},
    frames_caption=False,      # no title line on the frames, as on the Act 1 panels (Ethan 2026-09-21); the key label under inset A names the scenario + plan instead
    frames_scenarios="balanced",   # "balanced" = the balanced scenario only (Ethan 2026-09-23: an example output, disregard the forwards); "all" = every voting cell
    frames_climate_order=("ssp245", "ssp585"),   # the balanced scenario's cells in this order: low emissions first, then high (Ethan 2026-09-23)
    frames_plans_only=True,        # ONLY the near-optimal plan frames (Ethan 2026-09-23: "the 100 balanced scenario frames, nothing else") -- no value maps, anchor, f or core frames
    frames_assemble=True, frames_video_fps=30,   # assemble method_timelapse.mp4 from the frames with the venv's bundled ffmpeg (imageio-ffmpeg; Ethan 2026-09-23)
    frames_video_max_mb=20, frames_video_crf=18,  # size cap (Ethan 2026-09-23): CRF 18 / preset slow first; if the file is over the cap, a two-pass encode at the bitrate that fits
    inset_codes={"A": dict(skip=["WA"]), "B": dict(skip=["WA"])},                     # the wide-map insets: no WA; AK no longer forced on A (a sliver since the window moved east, 2026-09-21)
    inset_town_skip={"A": ("Iskut", "Telegraph Creek"), "B": ("Jasper", "Banff")},   # towns left off a wide-map inset (Ethan 2026-09-15)
    # Act 2 tiers by owning scenario. Dark2 failed a colour-vision check (2026-09-21: core-habitat green vs carbon magenta dE 6 under deuteranopia;
    # three more pairs < 20); this set (Tol green / Tol blue / Okabe-Ito sky / Okabe-Ito orange / Tol magenta) clears dE 16 against every other
    # fill incl. the two-or-more navy, the core yellow and the PA grey under normal vision and all three deficiencies
    scenario_colors={"s1": "#228833", "s2": "#0077BB", "s2c": "#56B4E9", "s3": "#E69F00", "s4": "#EE3377"},
    scenario_multi_color="#1f3a63", opportunity_color="#f7f7f7", never_color="#f7f7f7", show_opportunity=False,   # Ethan 2026-09-15: the opportunity tier off the Act 2 map
    scenario_insets=(5, 6, 11),                                                     # Act 2 map: windows on these scenario picks (A, B, C)
    # the Act 2 map's inset REGIONS are fixed too (Ethan 2026-09-21: "one up north"): the v3.1 windows -- A = Sacred Headwaters / Stikine,
    # B = Purcells / Kootenays, C = the Yukon north of Fishing Branch -- in grid pixels; None = size them on STYLE["scenario_insets"].
    # Alternative C on the v4 structural-connectivity tier around Ddhaw Ghro (64°N, v4 pick 7): (144.0, 580.0, 154.4, 808.6)
    # C spans BOTH northern tiers (Ethan 2026-09-21): the carbon-forward land east of Fishing Branch and the structural-connectivity tier
    # around Ddhaw Ghro (v4 picks 13 + 7, 45 km pad); the earlier v3.1 C (Fishing Branch alone) was (229.0, 549.0, -49.6, 430.6)
    scenario_inset_windows={"A": (124.9, 492.1, 959.0, 1510.0), "B": (699.2, 1047.8, 1916.0, 2439.0), "C": (144.0, 580.0, 36.4, 690.6)},
    scenario_inset_area_skip={"C": ("Nahanni National Park Reserve Of Canada",)},   # its label sits on C's clipped south-east corner over Nááts'įhch'oh's
    scenario_inset_codes={"A": dict(force=["AK"], skip=["WA"]), "B": dict(skip=["WA"])},
    scenario_inset_town_skip={"A": ("Iskut", "Telegraph Creek"), "B": ("Jasper", "Banff")},
    scenario_legend_fs=16,     # same size as the Act 1 map legend (Ethan 2026-09-15); no legend title
    scenario_legend_order=(("s1", "s3", "s2", "s2c", "s4") if dc.VP.version == "v4" else ("s1", "s3", "s2", "s4")),   # core-habitat, biodiversity, (structural) connectivity, (climate corridors,) carbon (Ethan 2026-09-15)
    map_title_fs=11.5, map_suptitle_fs=12.5,
    ramp_label="F = frequency in near-optimal plans; light grey = never (F = 0), yellow = core (F ≥ 0.70)",
    ramp_label_short="F = frequency in 30×30 plans", cbar_fs=15,          # the wide Act 1 maps (ensemble basis)
    ramp_label_balanced="frequency in the balanced scenario's 30×30 plans",   # no "f =" (Ethan 2026-09-23)   # package spec v2.1: the core is the balanced scenario's tier
    ramp_end_labels=("Rarely selected", "Consistently selected"),   # words at the F ramp's two ends (Ethan 2026-09-21); None = numbers only. F is how often a cell
                                                          # recurs across near-optimal plans, so the ends are the literal reading, not "importance"; "irreplaceable" was
                                                          # rejected because it sits beside "irrecoverable carbon" on the same slides
    cluster_region_labels="region",   # "Cluster N (Region)" wherever a cluster is named (package spec v1.12 decision e): "region" = the region word, "full" = "Sub-region(s), Region", False = "Cluster N"
    values_table="spec",      # the objectives-table rendering: "spec" (the table spec, 2026-09-14) | "poster" | "digest" | "plain"
    conseq_cmap="RdBu", conseq_tint=0.55, conseq_scale_rows="clusters",   # consequences: red (lowest) -> blue (highest) over the CLUSTER columns; the reference columns stay unfilled (Ethan 2026-09-23); "all" = the 2026-09-21 rule
    conseq_fill_area=True,                                              # the Area row takes the same low -> high ramp (Ethan 2026-09-23)
    conseq_bear_row=True,                                               # "Bear coexistence programs*" row (Ethan 2026-09-30): a count, not a ratio -- starred, explained in the note
    conseq_mode="row",         # "row" = each row's lowest -> highest (Laura, 2026-09-21); "hinge" = centred on 1.0x (the 2026-09-14 rule)
    conseq_tail_row=False,     # the soil-carbon-tail concentration row under carbon (package spec v1.14): off (Ethan 2026-09-21)
    conseq_flat_ratio=1.10,    # "row" mode: a row whose max/min ratio is below this is a tie at display precision -> neutral fill, not a stretched ramp
    conseq_reference="named",  # reference columns: "named" = dc.CONSEQ_REFERENCE_AREAS (Banff National Park, Dene Kʼéh Kusān; Ethan 2026-09-23) or "aggregate" = all PAs + the IPCAs' unprotected part
    legend_fs=13,              # map legends (bigger, outside the region)
    wide_legend_fs=16,         # the wide Act 1 maps: legend under inset B
    wide_legend_loc="center", wide_legend_y=0.103,   # where the legend box sits under inset B: its `loc` point at (B's centre x, this y)
    wide_legend_between=False,                       # True (the northern package, Ethan 2026-09-28): ignore the two above and centre the box between inset B's bottom
                                                     # edge and the bottom of the ramp block under A, measured at draw time; a box taller than the gap hangs from B
    wide_legend_fit=False,                           # True (wolverine, Ethan 2026-09-29): with wide_legend_between, shrink the legend's font (its handles, padding and
    wide_legend_fs_min=9,                            # spacing are in font units, so the whole box scales) until the box fits the gap; never below this size
    frame_north_arrow_beside_bar=True, frame_north_arrow_gap=0.05,   # the Y2Y frame: N arrow to the right of the 250 km bar on its baseline (Ethan 2026-09-30); gap in frame widths
    north_arrow_beside_bar=False,                    # windowed frames: the north arrow to the right of the scale bar instead of above it (wolverine, 2026-09-29)
    lat53=False,               # the 53°N graticule line on maps
    titles=True,               # figure / table titles (21 sets False: the slide carries the title)
    export_dpi=200, panel_export_scale=2,   # PNG resolution (21 sets 300: 13.33 in wide -> 4,000 px, a 4K slide); locator panels at 2x their nominal px
    export_pdf=False,          # also write a .pdf twin beside each wide-layout PNG (the northern package sets True: its §3a export rule)
    pa_alpha=1.0,              # the protected-areas fill's alpha (the northern package sets 0.85 to match its IPCA fill; y2y opaque)
    pa_fill_all=True,          # the grey PA fill covers EVERY protected-area cell, planning unit or not (rasterized from the PA polygons; Ethan 2026-09-30, every package); False = locked PU cells only
    border_style=None,         # the international border: (colour, lw, dash) | None = draw_admin's defaults (#4a4a4a, 1.0 pt, solid); the Alberta frame draws it like the admin lines
    scalebar_box=False,        # a WINDOWED frame's scale bar on an opaque white backing (Alberta 2026-09-30)
    north_arrow_pt=None,       # a WINDOWED frame's north arrow at a fixed length in points (11 = the Y2Y-wide frame's arrow); None = 6% of the window height
    window_north_arrow_left=False,   # a WINDOWED frame: the Y2Y frame's construction -- the arrow LEFT of the bar on its baseline, N above the tip, the bar shifted right (Alberta 2026-09-30)
    pa_borders=("white", 0.3, 0.75),   # (colour, lw, alpha) = hairlines along the PA polygon edges (dissolved by name) over the grey fill, so Banff / Jasper / Yoho / Kootenay read apart (Ethan 2026-09-30); None = off
    context_alpha=0.45,        # the context package's surface beyond the focus PU (dp.load(context=...)): its alpha
    context_label="Y2Y-wide result beyond Alberta (context)",   # its legend entry; None = none (16, Ethan 2026-09-30)
    inset_shift_km={},         # {tag: (east km, north km)}: nudge a wide-map inset after the same-scale fit (Alberta B up 20 km, 2026-09-30); {} = none
    inset_same_scale=True, locator_same_scale=True,   # the Act 1 insets A/B, and the four locators, each set at ONE scale (the largest window's; Ethan 2026-09-30)
    wide_common_crop=True,     # every wide map (Act 1, Act 2, the frames) exports on one page box: the frame's left edge + inset top, full width, page bottom (Ethan 2026-09-30)
    scenario_legend_between=True,   # Act 2 map: the legend box centred between the inset boxes' bottom edge and the page bottom (Ethan 2026-09-30); False = scenario_legend_y
    scenario_insets_as_act1=False,  # True = the Act 2 map's windows are the Act 1 map's panels A / B (same regions, re-fitted to the Act 2 aspect) (Alberta 2026-09-30)
    wide_legend_floor="ramp",  # wide_legend_between's floor: "ramp" = the ramp block under inset A (north) | "frame" = the frame's bottom edge (Alberta)
    focus_outline=("#333333", 0.6),   # the focus PU's outline when a context surface is drawn; None = off
    map_layout="wide",         # Act 1 maps: "wide" = slide-shaped with two zoom insets (clusters 1 and 2) | "tall" = the map alone
    inset_clusters=(1, 2), inset_pad_km=45, inset_min_km=320, inset_pa_names=5, inset_ipca_names=3, inset_declutter=True, inset_fs=11.5, inset_number_fs=18, inset_abbrev=True, inset_abbrev_fs=15,   # inset_ipca_names / inset_declutter: knobs since 2026-09-28 (the y2y values unchanged)
    wide_main_names="abbrev", wide_main_name_fs=15, wide_main_towns=(),      # the Y2Y-wide panel of the wide layout: postal codes only, big
    main_skip_codes=("CA",),  # jurisdictions never labelled on the Y2Y-wide frame (California is a sliver)
    main_codes={},             # a WINDOWED frame's jurisdiction codes: label_jurisdictions_window kwargs (force / inside / at); the Alberta frame pins BC (2026-09-30)
    inset_fit_pu=False,        # cluster insets: widen the window to the PU strip's full width over its rows (+ pad) and centre it there, so the whole strip fits (Alberta, 2026-09-30)
    pa_layer_min_km2=300, window_scale_km=100,                            # named-PA floor for insets/locators (read at load); the scale bar on a WINDOWED frame
    hillshade=True, water=True, province_names=True,                     # the basemap (corridors_mapstyle tokens, display only)
    towns=("Dawson City", "Whitehorse", "Watson Lake", "Fort Nelson", "Fort St. John", "Prince George", "Smithers", "Jasper",
           "Edmonton", "Calgary", "Banff", "Kamloops", "Cranbrook", "Missoula", "Helena", "Bozeman", "Boise", "Jackson", "Norman Wells"),
)

# ---- the shared assets: 20 (the record) and 21 (the presentation) call THESE, never their own copies -----------------
def values_table(C, path, title="Y2Y Objectives Hierarchy", rows=None, metrics=None, label=None, units=None):
    """THE objectives-table asset. Writes T-D0_values.csv (the rows) and renders in STYLE["values_table"]:
    "poster" = the Carbon-Poster spec (chosen by Ethan 2026-09-14 from the two iterations), "digest" = the Threat-Digest
    spec, "plain" = the original matplotlib table (superseded, kept). `rows` / `metrics` (the shapes of values_rows /
    values_metrics) let another package on the same tool supply its own objectives rows (the "spec" rendering)."""
    rows = list(rows) if rows is not None else values_rows(C)
    pd.DataFrame(rows, columns=VALUES_COLUMNS).to_csv(C.TAB / "T-D0_values.csv", index=False)
    if STYLE["values_table"] == "spec":
        return values_table_spec(C, path, title, rows=rows, metrics=metrics, label=label, units=units)
    fn = {"poster": values_table_poster, "digest": values_table_digest, "plain": values_table_plain}[STYLE["values_table"]]
    fn(C, path, title)


def values_table_plain(C, path, title="Y2Y Objectives Hierarchy"):
    grouped_table_png(values_rows(C), path, title)


def core_map_hex250(C, path, title=None, with_ipca_on_a=True):
    """SUPERSEDED (Ethan 2026-09-14: 1 km, no hexes, two files -> core_map_F / core_map_clusters). Kept for the record."""
    gdf, hl = C.HEX[dc.HEX_KM2]
    hm = dc.hex_means(C.G, gdf, hl, C.Fg)
    core_km2 = C.S["frequent_km2"]["guarded"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 11.5))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.86, bottom=0.10, wspace=0.04)
    for ax, panel in zip(axes, ("a", "b")):
        C.draw_pa(ax); C.draw_hex(ax, hm, C.FCMAP, C.FNORM)
        if panel == "a" and with_ipca_on_a:
            C.draw_ipca(ax)
        if panel == "b":
            C.draw_clusters(ax, "act1", C.picks_for("Act 1"), fs=STYLE["cluster_number_fs"], lw=STYLE["cluster_lw"])
        C.finish(ax, "(a) mean F per ~250 km² hex over unprotected land, with proposed IPCAs" if panel == "a"
                 else "(b) with the core clusters (F ≥ 0.70 at 1 km); numbered north → south",
                 C.BASE_HANDLES if panel == "b" else C.BASE_HANDLES[:2] + [C.IPCA_HANDLE], note=C.N_NOTE if panel == "b" else "")
    cax = fig.add_axes([0.30, 0.055, 0.40, 0.014])
    fig.colorbar(ScalarMappable(norm=C.FNORM, cmap=C.FCMAP), cax=cax, orientation="horizontal", extend="both", label=STYLE["ramp_label"])
    fig.suptitle(title or (f"{core_sentence(C)}\n"
                           f"core = {core_km2:,} km² of unprotected land, no value theme left more than 5% behind"), fontsize=STYLE["map_suptitle_fs"], y=0.985)
    fig.savefig(path, dpi=STYLE["export_dpi"], bbox_inches="tight"); plt.show()


def star_grid(profiles, path, title):
    """THE star-grid asset for a list of profiles (dict(title=, values={axis: v}, color=)) with the STYLE knobs and the spec type;
    _stars builds the profiles from T-D1 rows, the northern package's route options build theirs (corridors_director.option_stars,
    2026-09-28) -- one drawing function either way."""
    with plt.rc_context(SPEC_RC):
        dc.plot_star_grid(profiles, path, title if STYLE["star_title"] else None,
                          fs_axis=STYLE["star_fs_axis"], fs_title=STYLE["star_fs_title"], fs_tick=STYLE["star_fs_tick"],
                          fs_suptitle=STYLE["star_fs_suptitle"], lw=STYLE["star_lw"], footnote=STYLE["star_footnote"], tight=STYLE["star_tight"],
                          label_pad=STYLE["star_label_pad"], dpi=STYLE["export_dpi"], labels=AXIS_DISPLAY)
        plt.show()


def _stars(C, rows, color, path, title):
    star_grid(C.star_rows(rows, color), path, title)


def cluster_locators(C, path, act="Act 1", layer="act1", panel_px=None):
    """One inset-style window per cluster on the star grid's geometry (same figure size, same panel rectangles, full canvas)
    so it sits under the star plots panel-for-panel: F at 1 km, hillshade, PAs, cluster outlines and numbers, towns, the five
    largest protected areas named, a 50 km bar. No titles, no legend (Ethan 2026-09-15)."""
    rows = C.numbered(act); nums = [int(n) for n in rows.number]
    n = len(nums); ncols = min(4, max(n, 1)); nrows = int(math.ceil(n / ncols)); L = dc.STAR_GRID
    with plt.rc_context(SPEC_RC):
        # the star grid's panel CENTRES, but square windows of STYLE["locator_panel_in"] (bigger than the star circles)
        fig_w, fig_h = L["panel_w"] * ncols, max(L["panel_h"], STYLE["locator_panel_in"] + 0.4) * nrows
        fig = plt.figure(figsize=(fig_w, fig_h))
        left, right = 0.125, 0.9                                          # matplotlib's subplot defaults, as the star grid uses
        aw = (right - left) / (ncols + (ncols - 1) * L["wspace"])         # star axes width (figure fraction)
        pw = STYLE["locator_panel_in"] / fig_w; ph = STYLE["locator_panel_in"] / fig_h
        axes = []
        for i in range(n):
            r_, c_ = divmod(i, ncols)
            cx = left + aw * (c_ + 0.5) + c_ * aw * L["wspace"]
            cy = 1 - (r_ + 0.5) / nrows
            axes.append(fig.add_axes([cx - pw / 2, cy - ph / 2, pw, ph]))
        axes = np.array(axes)
        _all = C.picks_for(act)
        def draw_for(num):                                           # locator_own_number_only: every cluster outlined, only THIS panel's cluster numbered (Ethan 2026-09-30)
            nums_ = {cid: (n, a and (not STYLE.get("locator_own_number_only", False) or str(n) == str(num))) for cid, (n, a) in _all.items()}
            return lambda ax: C.draw_clusters(ax, layer, nums_, fs=STYLE["cluster_number_fs"] * STYLE.get("_fs_scale", 1.0), lw=STYLE["cluster_lw"])
        sc = STYLE["locator_fs_scale"]
        STYLE["_fs_scale"] = STYLE["inset_number_fs"] / STYLE["cluster_number_fs"] * sc; STYLE["_lw_scale"] = STYLE["cluster_lw_inset_scale"] * sc
        fs0, pa0 = STYLE["inset_fs"], STYLE["inset_pa_names"]; STYLE["inset_fs"] = fs0 * sc; STYLE["inset_pa_names"] = STYLE["locator_pa_names"]
        try:
            wins = [_inset_window(C, num, aspect_hw=1.0)[0] for num in nums]
            if STYLE.get("locator_same_scale", True):                              # the four locators at one scale (Ethan 2026-09-30)
                wins = _equalize_windows(wins)
            for ax, num, win in zip(axes, nums, wins):
                _draw_inset(C, ax, win, draw_for(num), "", with_ipca_names=False, towns=STYLE["locator_towns"], codes=STYLE["locator_codes"].get(num),
                            skip_towns=STYLE.get("locator_town_skip", {}).get(num, ()))       # per-window town skips (Alberta 16, 2026-09-30); default none
        finally:
            STYLE.pop("_fs_scale", None); STYLE.pop("_lw_scale", None); STYLE["inset_fs"] = fs0; STYLE["inset_pa_names"] = pa0
        fig.savefig(path, dpi=STYLE["export_dpi"])
        if panel_px:                                                   # each window as its own file, ~panel_px wide (Ethan 2026-09-15)
            fig.canvas.draw(); r = fig.canvas.get_renderer(); stem = pathlib.Path(path)
            for ax, num in zip(axes, nums):
                bb = ax.get_tightbbox(r).transformed(fig.dpi_scale_trans.inverted()).padded(0.02)
                fig.savefig(stem.with_name(f"{stem.stem}_{num}{stem.suffix}"), bbox_inches=bb, dpi=STYLE["panel_export_scale"] * panel_px / bb.width)   # 2x for retina / full-screen
        plt.show()


def core_stars(C, path, title="Act 1 core clusters — value profile (percentile vs the allocatable landscape)"):
    _stars(C, C.numbered("Act 1"), STYLE["core_color"], path, title)


def scenario_stars(C, path, title="Act 2 scenario clusters — value profile (percentile vs the allocatable landscape)"):
    _stars(C, C.numbered("Act 2"), STYLE["scenario_color"], path, title)


def core_consequences(C, path, title="What the core clusters hold"):
    consequences_table(C, C.numbered("Act 1"), path, "ACT 1  ·  CONSEQUENCES", title)


def scenario_consequences(C, path, title="What the value-specific clusters hold"):
    consequences_table(C, C.numbered("Act 2"), path, "ACT 2  ·  CONSEQUENCES", title)



# =====================================================================================================================
# Two design iterations of the objectives table (Ethan, 2026-09-14): the Carbon-Poster spec (Charcoal) and the
# Threat-Digest spec (dark green-grey). Same rows (values_rows); only the look changes. Ethan chose the POSTER
# (STYLE["values_table"]); the digest stays one switch away.
# =====================================================================================================================
def values_metrics(C):
    """The scannable metric per row (the poster's 'metric line' / the digest's numeric cell), in row order of values_rows."""
    sc = json.loads((dc.SPEC / SCENARIOS_FILE).read_text()); t0 = sc["S0_balanced"]["targets"]; t4 = sc["S4_carbon"]["targets"]
    MS = "irrecoverable_carbon_m_soc"
    efg_t = json.loads((dc.SPEC_REC / "efg_targets.json").read_text())["targets"] if (dc.SPEC_REC / "efg_targets.json").exists() else {}
    tgt = f"targets {100*min(efg_t.values()):.0f}–{100*max(efg_t.values()):.0f}% per class" if efg_t else "representation floor"
    b = 0.20 if dc.VP.version == "v4" else 0.25                                                    # the balanced block share
    conn = ["20% of the objective", "20% of the objective"] if dc.VP.version == "v4" else ["12.5% of the objective", "12.5% of the objective"]
    return ["30% of the region", f"{100*b:.0f}% of the objective", "baseline weight · not a driver", f"{100*b/2:g}% of the objective", f"{100*b/2:g}% of the objective",
            tgt, *conn, f"{100*b*0.258:.1f}% of the objective",
            f"{100*b*0.742:.1f}% · target {100*t0[MS]:.0f}% ({100*t4[MS]:.0f}%)", "—"]


def _tracked(s, gap=" "):
    """Letter-spacing for caps labels (matplotlib has no tracking): thin spaces between characters."""
    return gap.join(s)


def _wrap_rows(rows, chars):
    return [[textwrap.wrap(str(c), ch) or [""] for c, ch in zip(r, chars)] for r in rows]


def _text_right_edge(fig, ax, t):
    """Data-x of a drawn text's right edge (needs the Agg renderer)."""
    bb = t.get_window_extent(fig.canvas.get_renderer()).transformed(ax.transData.inverted())
    return bb.x1


def values_table_poster(C, path, title="Y2Y Objectives Hierarchy"):
    """The Carbon-Poster spec, Charcoal theme: warm-dark ground, one warm off-white card, hairlines not boxes, accent
    for small type only, Cronos Pro at weights 400/600, the 'column head group' (heading → metric → body) per row."""
    BG, MAT, INK, CAP, MUT, ACC = "#211E1B", "#F6F2E9", "#F2EDE3", "#CDC7BB", "#B1ABA0", "#C79152"
    PINK, PCAP, PMUT = "#29261F", "#403B31", "#6C6557"                      # Paper tokens: text on the mat card
    RULE_D, RULE_L, FRAME = (1, 1, 1, 0.13), (0, 0, 0, 0.12), (0, 0, 0, 0.18)
    FONT = ["Cronos Pro", "DejaVu Sans"]                                    # fallback carries the thin space / arrow
    rows = values_rows(C); metrics = values_metrics(C)
    colw = [2.6, 4.2, 2.9, 3.9]; chars = [22, 46, 30, 42]                  # fundamental | sub-objective+metric+measure | source | how
    body = [[r[0], r[2], r[3], r[4]] for r in rows]
    wrapped = _wrap_rows(body, chars)
    lh = 0.20
    row_h = [max(2 + len(wr[1]), len(wr[2]), len(wr[3]), 2) * lh + 0.30 for wr in wrapped]
    W = sum(colw); table_h = sum(row_h) + 0.76
    card_pad = 0.30; note_h = 0.46; card_h = table_h + 2 * card_pad + note_h
    top_m, bot_m = 1.55 + 0.55, 0.85
    H = card_h + top_m + bot_m
    fig = plt.figure(figsize=(W + 1.4, H), facecolor=BG); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W + 1.4); ax.set_ylim(0, H); ax.axis("off")
    x0 = 0.7; y = H - 0.55
    ax.add_patch(Rectangle((x0, y - 0.03), 0.46, 0.03, color=ACC))                                         # eyebrow tick rule
    ax.text(x0, y - 0.22, _tracked("YELLOWSTONE TO YUKON  ·  SPATIAL DECISION TOOL"), color=ACC, fontsize=8.5, fontweight=600, fontfamily=FONT, va="top")
    ax.text(x0, y - 0.50, title, color=INK, fontsize=26, fontweight=600, fontfamily=FONT, va="top")
    ax.text(x0, y - 0.98, "How each PROACT objective is measured, and how it enters the optimization", color=CAP, fontsize=11, fontfamily=FONT, va="top")
    cy = bot_m
    ax.add_patch(FancyBboxPatch((x0 + 0.06, cy - 0.08), W, card_h, boxstyle="round,pad=0,rounding_size=0.04", facecolor=(0, 0, 0, 0.35), edgecolor="none"))
    ax.add_patch(FancyBboxPatch((x0, cy), W, card_h, boxstyle="round,pad=0,rounding_size=0.03", facecolor=MAT, edgecolor=RULE_D, lw=0.8))
    tx = x0 + card_pad; tw = W - 2 * card_pad; ty = cy + card_h - card_pad
    ax.text(tx, ty, _tracked("OBJECTIVES  ·  SUB-OBJECTIVES  ·  PERFORMANCE MEASURES"), color=ACC, fontsize=7.5, fontweight=600, fontfamily=FONT, va="top")
    ty -= 0.42
    xs = np.r_[tx, tx + np.cumsum(np.array(colw) / W * tw)]
    heads = ["Fundamental objective", "Sub-objective and performance measure", "Source", "How it enters the analysis"]
    for j, hd in enumerate(heads):
        ax.text(xs[j] + 0.14, ty, hd, color=PINK, fontsize=10, fontweight=600, fontfamily=FONT, va="top")
    ty -= 0.34; ax.plot([tx, tx + tw], [ty, ty], color=FRAME, lw=1.0)
    top_of_table = ty
    n = len(rows)
    for k, (r, wr, rh, met) in enumerate(zip(rows, wrapped, row_h, metrics)):
        yy = ty - 0.14
        if r[0]:
            ax.text(xs[0] + 0.14, yy, "\n".join(textwrap.wrap(r[0], chars[0])), color=PINK, fontsize=9.5, fontweight=600, fontfamily=FONT, va="top", linespacing=1.15)
        ax.text(xs[1] + 0.14, yy, r[1], color=PINK, fontsize=10, fontweight=600, fontfamily=FONT, va="top")                # heading
        ax.text(xs[1] + 0.14, yy - lh, met, color=ACC, fontsize=8.5, fontweight=600, fontfamily=FONT, va="top")           # metric line
        ax.text(xs[1] + 0.14, yy - 2 * lh, "\n".join(wr[1]), color=PCAP, fontsize=9, fontfamily=FONT, va="top", linespacing=1.3)   # body
        ax.text(xs[2] + 0.14, yy, "\n".join(wr[2]), color=PMUT, fontsize=8.5, fontfamily=FONT, va="top", linespacing=1.3)
        ax.text(xs[3] + 0.14, yy, "\n".join(wr[3]), color=PCAP, fontsize=9, fontfamily=FONT, va="top", linespacing=1.3)
        ty -= rh
        group_end = (k + 1 == n) or bool(rows[k + 1][0])                     # next row starts a new fundamental objective
        ax.plot([tx if group_end else xs[1], tx + tw], [ty, ty], color=RULE_L, lw=0.7)
    ax.plot([xs[1], xs[1]], [top_of_table, ty], color=FRAME, lw=0.8)         # the one real grouping: fundamental | the rest
    note = ("Shares are of the objective's influence in the balanced position; each forward position doubles one theme's share. "
            "Targets are fractions of the regional total. Naturalness and representativeness enter outside the four weighted themes.")
    ax.text(tx, ty - 0.16, "\n".join(textwrap.wrap(note, 150)), color=PMUT, fontsize=7.5, fontfamily=FONT, va="top", linespacing=1.4)
    ax.plot([x0, x0 + W], [0.50, 0.50], color=RULE_D, lw=0.8)
    ax.text(x0, 0.38, "Yellowstone to Yukon Conservation Initiative", color=CAP, fontsize=8.5, fontweight=600, fontfamily=FONT, va="top")
    ax.text(x0 + W, 0.38, _tracked("PROACT OBJECTIVES  ·  2026"), color=ACC, fontsize=7, fontweight=600, fontfamily=FONT, va="top", ha="right")
    fig.savefig(path, dpi=STYLE["export_dpi"], facecolor=BG); plt.show()


def values_table_digest(C, path, title="Y2Y Objectives Hierarchy"):
    """The Threat-Digest spec: dark green-grey canvas, one card per fundamental objective with a mono uppercase section
    head and hairline, a 4 px rail per row coloured by group, serif names with a mono sub-line, mono metrics right-aligned,
    sans prose."""
    BG, SURF, SURF2, INK, MUTED, FAINT, LINE, ACC, ACCI, AMB = "#0e1310", "#161d18", "#1b231d", "#e6efe8", "#9db0a5", "#74857b", "#263029", "#57c294", "#7ed3ac", "#d8ac5f"
    SERIF, SANS, MONO = ["Iowan Old Style", "DejaVu Serif"], ["Helvetica Neue", "DejaVu Sans"], ["Menlo", "DejaVu Sans Mono"]
    GROUP_COLOR = {"PROTECT": ACC, "CONNECT": ACCI, "ADDRESS": AMB, "NOT": FAINT}          # rail + section label, by group
    rows = values_rows(C); metrics = values_metrics(C)
    groups = []
    for r, m in zip(rows, metrics):
        if r[0]: groups.append([r[0], []])
        groups[-1][1].append((r, m))
    colw = [3.6, 2.6, 4.0, 2.0]; chars = [40, 26, 46, 22]; W = sum(colw); lh = 0.19
    blocks = []
    for gname, items in groups:
        rh = []
        for r, m in items:
            w_meas = textwrap.wrap(r[2], chars[0]); w_src = textwrap.wrap(r[3], chars[1]); w_how = textwrap.wrap(r[4], chars[2]) or [""]; w_met = textwrap.wrap(m, chars[3])
            rh.append(max(1 + len(w_meas), len(w_src), len(w_how), len(w_met)) * lh + 0.30)
        blocks.append((gname, items, rh, sum(rh) + 0.40))
    H = 1.9 + sum(b[3] + 0.75 for b in blocks) + 0.6
    fig = plt.figure(figsize=(W + 1.2, H), facecolor=BG); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W + 1.2); ax.set_ylim(0, H); ax.axis("off")
    x0 = 0.6; y = H - 0.45
    ax.text(x0, y, _tracked("YELLOWSTONE TO YUKON"), color=ACCI, fontsize=8, fontfamily=MONO, va="top")
    ax.text(x0, y - 0.26, title, color=INK, fontsize=24, fontweight=600, fontfamily=SERIF, va="top")
    ax.text(x0, y - 0.76, "The values in the spatial decision tool: what each objective measures, and how it enters the optimization.", color=MUTED, fontsize=10.5, fontfamily=SANS, va="top")
    ax.plot([x0, x0 + W], [y - 1.12, y - 1.12], color=LINE, lw=0.8)
    y -= 1.5
    heads = ["Sub-objective · measure", "Source", "How it enters the analysis", "Share / target"]
    for gname, items, rh, gh in blocks:
        col = GROUP_COLOR[gname.split()[0]]
        lab = _tracked(gname.split(" — ")[0]); sub = gname.split(" — ")[1] if " — " in gname else ""
        t = ax.text(x0, y, lab, color=col, fontsize=8.5, fontweight=600, fontfamily=MONO, va="center")
        badge_x = _text_right_edge(fig, ax, t) + 0.22
        ax.add_patch(FancyBboxPatch((badge_x, y - 0.11), 0.42, 0.22, boxstyle="round,pad=0,rounding_size=0.11", facecolor=SURF2, edgecolor=LINE, lw=0.6))
        ax.text(badge_x + 0.21, y, str(len(items)), color=FAINT, fontsize=7.5, fontweight=600, fontfamily=MONO, va="center", ha="center")
        rule_x = badge_x + 0.62
        if sub:
            t2 = ax.text(badge_x + 0.62, y, sub, color=MUTED, fontsize=8.5, fontfamily=SANS, va="center")
            rule_x = _text_right_edge(fig, ax, t2) + 0.25
        ax.plot([rule_x, x0 + W], [y, y], color=LINE, lw=0.7)
        y -= 0.32
        cy = y - gh
        ax.add_patch(FancyBboxPatch((x0, cy), W, gh, boxstyle="round,pad=0,rounding_size=0.13", facecolor=SURF, edgecolor=LINE, lw=0.8))
        ax.add_patch(Rectangle((x0 + 0.13, y - 0.36), W - 0.26, 0.36, facecolor=SURF2, edgecolor="none"))           # header band
        ax.plot([x0 + 0.13, x0 + W - 0.13], [y - 0.36, y - 0.36], color=LINE, lw=0.8)                               # its bottom hairline
        xs = np.r_[x0 + 0.18, x0 + 0.18 + np.cumsum(np.array(colw) / W * (W - 0.36))]
        for j, hd in enumerate(heads):
            ax.text(xs[j] if j < 3 else xs[4] - 0.05, y - 0.18, _tracked(hd.upper()), color=FAINT, fontsize=6.4, fontweight=600, fontfamily=MONO,
                    va="center", ha="left" if j < 3 else "right")
        yy = y - 0.36
        for (r, m), h in zip(items, rh):
            ax.add_patch(Rectangle((x0 + 0.13, yy - h), 0.04, h, facecolor=col, edgecolor="none"))                  # the 4 px rail
            ax.text(xs[0], yy - 0.15, r[1], color=INK, fontsize=10.5, fontweight=600, fontfamily=SERIF, va="top")
            ax.text(xs[0], yy - 0.15 - lh - 0.02, "\n".join(textwrap.wrap(r[2], chars[0])), color=FAINT, fontsize=7.4, fontfamily=MONO, va="top", linespacing=1.35)
            ax.text(xs[1], yy - 0.15, "\n".join(textwrap.wrap(r[3], chars[1])), color=FAINT, fontsize=7.4, fontfamily=MONO, va="top", linespacing=1.35)
            ax.text(xs[2], yy - 0.15, "\n".join(textwrap.wrap(r[4], chars[2])), color=MUTED, fontsize=9, fontfamily=SANS, va="top", linespacing=1.35)
            ax.text(xs[4] - 0.05, yy - 0.15, "\n".join(textwrap.wrap(m, chars[3])), color=INK, fontsize=8.5, fontfamily=MONO, va="top", ha="right", linespacing=1.35)
            yy -= h
            ax.plot([x0 + 0.17, x0 + W - 0.13], [yy, yy], color=LINE, lw=0.6)
        y = cy - 0.43
    ax.text(x0, 0.32, _tracked("PROACT OBJECTIVES  ·  Y2Y SPATIAL DECISION TOOL  ·  2026"), color=FAINT, fontsize=7, fontfamily=MONO, va="top")
    fig.savefig(path, dpi=STYLE["export_dpi"], facecolor=BG); plt.show()


# =====================================================================================================================
# THE TABLE SPEC (Ethan, 2026-09-14, "Y2Y Table Spec — for Python output"): a mat card on a bg page, Cronos Pro at
# 400/500/600, a caps accent label above a sentence-case header, 1 px hairlines (rule between rows, frame under the header
# and at real groupings only), numbers right-aligned in accent 600, notes in mut with 600 cap labels. Every size is a ratio
# of one base (STYLE["table_base_px"]; 16 = report, 30 = slide) so one knob rescales a table. `spec_table_png` is the
# renderer; the values table and the (transposed) consequences tables are built on it.
# =====================================================================================================================
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.font_manager import FontProperties

class _WeightFallbackFilter(logging.Filter):
    """matplotlib logs 'findfont: Failed to find font weight 600, now using 700' for every lookup that reaches the DejaVu
    fallback family (no 600 face). The substitution is the intended behaviour (Ethan 2026-09-15: use 700 where 600 is
    missing), so the message is dropped; every other font_manager message still shows."""
    def filter(self, rec):
        return "Failed to find font weight" not in rec.getMessage()


logging.getLogger("matplotlib.font_manager").addFilter(_WeightFallbackFilter())

TABLE = dict(bg="#211E1B", mat="#F6F2E9", ink="#29261F", cap="#403B31", mut="#6C6557", accent="#8A5F27",   # accent darkened for the mat
             rule=(0, 0, 0, 0.10), frame=(0, 0, 0, 0.18))
TABLE_FONT = ["Cronos Pro", "DejaVu Sans"]                  # (Jost, the spec fallback, is not installed) DejaVu carries the thin space / × / − that Cronos lacks
_PX = 1 / 96                                                 # one CSS px in inches (1 px hairline = 0.75 pt)
_MEASURE = Figure(dpi=100); FigureCanvasAgg(_MEASURE)        # off-pyplot scratch canvas for text measurement
STYLE.setdefault("table_base_px", 16)
STYLE.setdefault("conseq_tint", 0.45)


def _fp(pt, weight=400):
    return FontProperties(family=TABLE_FONT, size=pt, weight=weight)


def _text_w(s, pt, weight=400):
    """Width in inches of the widest line of `s` in the table font (real glyph metrics)."""
    r = _MEASURE.canvas.get_renderer(); fp = _fp(pt, weight)
    return max(r.get_text_width_height_descent(line, fp, ismath=False)[0] for line in str(s).split("\n")) / _MEASURE.dpi


def _wrap_to(s, width_in, pt, weight=400):
    """Greedy word-wrap of `s` to `width_in` inches using real metrics."""
    out = []
    for para in str(s).split("\n"):
        line = ""
        for w in para.split(" "):
            cand = (line + " " + w).strip()
            if line and _text_w(cand, pt, weight) > width_in:
                out.append(line); line = w
            else:
                line = cand
        out.append(line)
    return "\n".join(out)


# cell content: a str, or a list of (text, style) runs stacked as lines; styles = head / metric / body / fine
_CELL_STYLES = dict(head=("ink", 600), metric=("accent", 600), body=("cap", 400), fine=("mut", 400), num=("accent", 600))


def spec_table_png(path, stub, cols, cells, *, label=None, title=None, units=None, notes=(), groups=None, numeric=None,
                   fills=None, col_w=None, stub_w=None, stub_head="", base_px=None, dpi=None, stub_sep=False):
    """Render one table to the spec. stub: row labels; cols: header strings (may contain \\n); cells[i][j]: str or runs;
    numeric[i][j] (bool) -> right-aligned accent 600; fills[i][j] -> cell background (None = mat); groups: list of
    (label, j0, j1) column groups drawn as a spanner row + frame separators; col_w / stub_w in inches override the
    measured (uniform) data-column width and the 1.5× stub."""
    B = base_px or STYLE["table_base_px"]; u = B * _PX; pt = B * 0.75
    f_body, f_label, f_title, f_note = 0.87 * pt, 0.80 * pt, 1.70 * pt, 0.80 * pt
    pad_v, pad_h, card_pv, card_ph, gap, page = 0.67 * u, 0.47 * u, 1.2 * u, 1.5 * u, 0.67 * u, 3.0 * u
    lh = lambda f: 1.28 * f / 72
    T = TABLE; n, m = len(stub), len(cols)
    numeric = numeric or [[False] * m for _ in range(n)]
    fills = fills or [[None] * m for _ in range(n)]
    runs = lambda c: c if isinstance(c, list) else [(c, "body")]
    # ---- column widths (measured) ----
    def cell_w(c):
        return max(_text_w(t, f_body, _CELL_STYLES[s][1]) for t, s in runs(c))
    if col_w is None:
        w_data = max([_text_w(h, f_body, 600) for h in cols] + [cell_w(cells[i][j]) for i in range(n) for j in range(m)]) + 2 * pad_h
        col_w = [w_data] * m
    stub_w = stub_w or max(_text_w(stub_head, f_body, 600), max(_text_w(s, f_body) for s in stub), 1.5 * (sum(col_w) / m)) + 2 * pad_h
    xs = np.r_[0, np.cumsum([stub_w] + list(col_w))]; Wt = xs[-1]
    # ---- row heights ----
    n_lines = lambda c: sum(len(str(t).split("\n")) for t, _ in runs(c))
    h_head = max(len(h.split("\n")) for h in cols + [stub_head or " "]) * lh(f_body) + 2 * pad_v
    h_span = (lh(f_label) + pad_v) if groups else 0
    row_h = [max(max(n_lines(cells[i][j]) for j in range(m)), len(stub[i].split("\n"))) * lh(f_body) + 2 * pad_v for i in range(n)]
    Ht = h_span + h_head + sum(row_h)
    # ---- card height: label / title / units / table / notes ----
    Wc_inner = max(Wt, _text_w(title or "", f_title, 600), _text_w(units or "", f_body))
    note_lines = [(k, _wrap_to(v, Wc_inner - _text_w(k + "  ", f_note, 600), f_note)) for k, v in notes]
    h_top = (lh(f_label) + gap if label else 0) + (lh(f_title) + 0.25 * u if title else 0) + (lh(f_body) + gap if units else 0)
    h_notes = (gap + sum(len(v.split("\n")) * lh(f_note) + 0.15 * u for _, v in note_lines)) if note_lines else 0
    Hc = card_pv * 2 + h_top + Ht + h_notes; Wc = Wc_inner + 2 * card_ph
    fig = plt.figure(figsize=(Wc + 2 * page, Hc + 2 * page), facecolor=T["bg"])
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, Wc + 2 * page); ax.set_ylim(0, Hc + 2 * page); ax.axis("off")
    # ---- card + soft shadow ----
    for k in range(6, 0, -1):
        ax.add_patch(FancyBboxPatch((page - 0.02 * k * u, page - 0.16 * u - 0.03 * k * u), Wc + 0.04 * k * u, Hc + 0.04 * k * u,
                                    boxstyle="round,pad=0,rounding_size=0.05", facecolor=(0, 0, 0, 0.07), edgecolor="none"))
    ax.add_patch(FancyBboxPatch((page, page), Wc, Hc, boxstyle=f"round,pad=0,rounding_size={3 * _PX}", facecolor=T["mat"], edgecolor=T["frame"], lw=0.75))
    x0 = page + card_ph; y = page + Hc - card_pv
    if label:
        ax.text(x0, y, _tracked(label), color=T["accent"], fontproperties=_fp(f_label, 600), va="top"); y -= lh(f_label) + gap
    if title:
        ax.text(x0, y, title, color=T["ink"], fontproperties=_fp(f_title, 600), va="top"); y -= lh(f_title) + 0.25 * u
    if units:
        ax.text(x0, y, units, color=T["mut"], fontproperties=_fp(f_body), va="top"); y -= lh(f_body) + gap
    # ---- table ----
    tx = x0; top = y
    hair = dict(color=T["frame"], lw=0.75, solid_capstyle="butt")
    if groups:                                                                     # spanner row: label + frame underline per group
        for glab, j0, j1 in groups:
            xa, xb = tx + xs[j0 + 1], tx + xs[j1 + 2]
            ax.text((xa + xb) / 2, y - 0.5 * lh(f_label), glab, color=T["cap"], fontproperties=_fp(f_label, 600), ha="center", va="center")
            ax.plot([xa + pad_h, xb - pad_h], [y - h_span + 0.35 * pad_v] * 2, **hair)
        y -= h_span
    # header row (sentence case, ink 600, aligned with its column)
    yh = y - h_head / 2
    ax.text(tx + pad_h, yh, stub_head, color=T["ink"], fontproperties=_fp(f_body, 600), ha="left", va="center")
    for j, h in enumerate(cols):
        right = all(numeric[i][j] for i in range(n)) if n else False
        ax.text(tx + xs[j + 2] - pad_h if right else tx + xs[j + 1] + pad_h, yh, h, color=T["ink"], fontproperties=_fp(f_body, 600),
                ha="right" if right else "left", va="center", linespacing=1.28)
    y -= h_head; ax.plot([tx, tx + Wt], [y, y], **hair)                            # header underline, full width
    y_body_top = y
    for i in range(n):
        h = row_h[i]
        for j in range(m):
            if fills[i][j] is not None:
                ax.add_patch(Rectangle((tx + xs[j + 1], y - h), col_w[j], h, facecolor=fills[i][j], edgecolor="none", zorder=1))
        ax.text(tx + pad_h, y - pad_v, stub[i], color=T["cap"], fontproperties=_fp(f_body), ha="left", va="top", linespacing=1.28, zorder=2)
        for j in range(m):
            yy = y - pad_v; right = numeric[i][j]
            xa = tx + xs[j + 2] - pad_h if right else tx + xs[j + 1] + pad_h
            for t, sname in runs(cells[i][j]):
                col, wt = _CELL_STYLES["num" if right else sname]
                if fills[i][j] is not None: col = "ink"                          # on a tint, ink 600 (accent fails contrast)
                ax.text(xa, yy, t, color=T[col], fontproperties=_fp(f_body, wt), ha="right" if right else "left", va="top", linespacing=1.28, zorder=2)
                yy -= len(str(t).split("\n")) * lh(f_body)
        y -= h
        if i < n - 1:                                                              # rule between rows, none after the last
            ax.plot([tx, tx + Wt], [y, y], color=T["rule"], lw=0.75, solid_capstyle="butt")
    if stub_sep:                                                                   # stub | data is a real grouping
        ax.plot([tx + xs[1], tx + xs[1]], [top, y], **hair)
    if groups:                                                                     # frame separators at group boundaries only
        for _, j0, _ in groups[1:]:
            xg = tx + xs[j0 + 1]; ax.plot([xg, xg], [top, y], **hair)
    # ---- notes ----
    if note_lines:
        y -= gap
        for k, v in note_lines:
            ax.text(x0, y, k, color=T["cap"], fontproperties=_fp(f_note, 600), va="top")
            ax.text(x0 + _text_w(k + "  ", f_note, 600), y, v, color=T["mut"], fontproperties=_fp(f_note), va="top", linespacing=1.28)
            y -= len(v.split("\n")) * lh(f_note) + 0.15 * u
    fig.savefig(path, dpi=dpi or STYLE["export_dpi"], facecolor=T["bg"]); plt.show()


from matplotlib.legend_handler import HandlerBase


class _ClusterSwatches(HandlerBase):
    """Legend handler: the cluster colours as small outlined squares side by side (STYLE["cluster_colors"], N -> S)."""
    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        cols = getattr(orig_handle, "_swatch_colors", None) or [STYLE["cluster_colors"][k] for k in sorted(STYLE["cluster_colors"])]   # explicit colours (the northern route options, 2026-09-28) or the palette N -> S
        n_show = getattr(orig_handle, "_n_swatches", None)                        # only the clusters actually numbered on the map (Ethan 2026-09-23: no spare fifth box)
        cols = cols[:n_show] if n_show else cols
        n = len(cols); gap = 0.10 * width / n; w = (width - gap * (n - 1)) / n; h = height     # same box as the patch entries
        return [Rectangle((-xdescent + i * (w + gap), -ydescent), w, h, facecolor="none", edgecolor=c, lw=STYLE["cluster_lw"] * 2.2, transform=trans)
                for i, c in enumerate(cols)]                       # (-xdescent, -ydescent) = where matplotlib's own patch handler draws


def cluster_handle(label="Core clusters", n=None, colors=None):
    """A legend entry drawn by _ClusterSwatches (one swatch per numbered cluster when `n` is given, else every palette colour;
    `colors` = an explicit list in swatch order instead of the palette); pass `handler_map=cluster_handler_map(*handles)` to
    the legend call."""
    h = Patch(facecolor="none", edgecolor="none", label=label); h._cluster_swatches = True; h._n_swatches = n; h._swatch_colors = list(colors) if colors else None
    return h


def cluster_handler_map(*handles):
    """Only the entries made by cluster_handle get the swatch handler; everything else keeps matplotlib's default."""
    return {h: _ClusterSwatches() for h in handles if getattr(h, "_cluster_swatches", False)}


SOURCE_NOTE = f"Y2Y spatial decision tool, frequency ensemble on manifest {dc.VP.version} (in review)."
REF_LABELS = {"Existing protected areas": "Existing\nprotected areas", "Proposed IPCAs (unprotected part)": "Proposed IPCAs\n(unprotected)",
              "Banff National Park": "Banff\nNational Park", "Dene Kʼéh Kusān": "Dene Kʼéh Kusān\n(proposed IPCA)"}   # reference-column header text (other names wrap)

# maps and star plots share the spec's type: Cronos Pro, weights 400/600, ink titles, cap text, mut fine print
SPEC_RC = {"font.family": TABLE_FONT, "font.weight": 400, "text.color": TABLE["cap"], "axes.titlecolor": TABLE["ink"],
           "axes.titleweight": 600, "figure.titleweight": 600, "axes.labelcolor": TABLE["cap"], "xtick.color": TABLE["cap"],
           "ytick.color": TABLE["cap"], "legend.labelcolor": TABLE["cap"], "axes.edgecolor": TABLE["cap"]}


def consequences_table(C, rows, path, label, title, ref=None, col_label=None, group_label="Core clusters", source=None):
    """The consequences table to the spec, TRANSPOSED: one row per measure (area, the value ratios), one column
    per cluster, then the reference columns (named example areas -- Banff National Park, Dene Kʼéh Kusān -- or, by STYLE, the two
    aggregates: existing protected areas; the proposed IPCAs' unprotected part). Ratio rows
    are tinted red → green across the row (STYLE['conseq_*']); clusters group by leading scenario where they differ.
    `ref` = the reference rows (name, area_km2, ratio_<axis>) from outside instead of C.TD7; `col_label(r, wrap=)` = the column
    header per row instead of cluster_label; `group_label` = the spanner over the non-reference columns; `source` = the source
    note (default SOURCE_NOTE) -- the northern package's route options use all four (corridors_director.option_consequences)."""
    if ref is None:
        want = "reference" if STYLE.get("conseq_reference", "named") == "named" else "reference_aggregate"   # named example areas (Ethan 2026-09-23) or the two aggregates
        ref = C.TD7[C.TD7.act.eq(want)]
        if not len(ref):                                                             # a package from before the named rows: whatever is filed as reference
            ref = C.TD7[C.TD7.act.eq("reference")]
    body = pd.concat([rows, ref], ignore_index=True)
    nclu = len(rows)
    lab_fn = col_label or cluster_label
    cols = [lab_fn(r, wrap=18) for r in rows.itertuples()] + [REF_LABELS.get(str(nm), textwrap.fill(str(nm).replace(" (unprotected part)", "\n(unprotected part)"), 20)) for nm in ref.name]
    if "driving_label" in rows and rows.driving_label.nunique() > 1:
        groups, j0 = [], 0
        for k, (lab, grp) in enumerate(rows.groupby("driving_label", sort=False)):
            groups.append((lab, j0, j0 + len(grp) - 1)); j0 += len(grp)
    else:
        groups = [(group_label, 0, nclu - 1)]
    groups.append(("Reference", nclu, nclu + len(ref) - 1))
    cap = lambda a: (lambda w: w[0].upper() + w[1:])(axis_label(a))
    stub = ["Area (km²)"] + [cap(a) for a in dc.STAR_AXES]
    cells = [[f"{v:,.0f}" for v in body.area_km2]]
    cells += [[ratio_fmt(v) for v in body[f"ratio_{a}"]] for a in dc.STAR_AXES]
    bear = STYLE.get("conseq_bear_row", True) and "bear_programs_mean" in body
    if bear:                                                             # a count (mean groups recorded in the overlapped units), not a ratio
        stub.append("Bear coexistence programs*")
        cells.append([("—" if pd.isna(v) else f"{v:.1f}") for v in body.bear_programs_mean.astype(float)])
    # package spec v1.14 reading guard: a high carbon ratio can mean uniformly carbon-rich or ordinary-with-a-hotspot, so the
    # concentration reading (share of the area inside the soil-carbon theta-tail, T-D1's driver attribution) sits beside it
    tail_col = "driver_m_soc theta-tail"
    if STYLE.get("conseq_tail_row", False) and tail_col in rows:
        k = stub.index("Carbon") + 1
        tail_vals = list(rows[tail_col]) + [np.nan] * len(ref)
        stub.insert(k, "  of which in the soil-carbon tail (% of area)")
        cells.insert(k, [("—" if pd.isna(v) else f"{v:.0f}%") for v in tail_vals])
    numeric = [[True] * len(cols) for _ in stub]
    # fills per ratio ROW over the columns in scope (STYLE["conseq_scale_rows"]): "row" mode (Laura / Ethan 2026-09-21) runs the ramp from
    # the row's lowest value to its highest, no hinge; "hinge" mode (the 2026-09-14 rule) centres it on 1.0x. The ramp is a colour-blind-safe
    # diverging pair (STYLE["conseq_cmap"], default RdBu: red = lowest, blue = highest), blended toward the mat by STYLE["conseq_tint"].
    cmap = plt.get_cmap(STYLE["conseq_cmap"]); tint = STYLE["conseq_tint"]; mat = np.array(matplotlib.colors.to_rgb(TABLE["mat"]))
    all_cols = STYLE["conseq_scale_rows"] == "all"
    scope = np.arange(len(body)) if all_cols else np.arange(nclu)         # "clusters": scaled AND filled over the cluster columns only
    fills = [[None] * len(cols) for _ in stub]
    axis_rows = {a: stub.index(cap(a)) for a in dc.STAR_AXES}          # row index per ratio axis (the tail row, if shown, is untinted)
    filled = [(axis_rows[a], np.log(body[f"ratio_{a}"].astype(float).values)) for a in dc.STAR_AXES]
    if STYLE.get("conseq_fill_area", True):                               # the Area row on the same ramp (log area, lowest -> highest)
        filled.insert(0, (stub.index("Area (km²)"), np.log(body.area_km2.astype(float).values)))
    if bear:                                                             # the count row on the same low -> high ramp (linear; NaN unfilled)
        filled.append((stub.index("Bear coexistence programs*"), body.bear_programs_mean.astype(float).values))
    for r, x in filled:
        lo, hi = np.nanmin(x[scope]), np.nanmax(x[scope])
        flat = (hi - lo) < np.log(STYLE.get("conseq_flat_ratio", 1.10))   # every value in the row rounds to the same figure: a tie, not a ramp
        for j, v in enumerate(x):
            if j >= nclu and not all_cols:                             # reference columns: no fill
                continue
            if STYLE.get("conseq_mode", "row") == "hinge":       # 1.0x (log 0) = the inflection; each side scaled to the row's own extreme
                t = 0.5 + 0.5 * (v / hi if v > 0 and hi > 0 else (-v / lo if v < 0 and lo < 0 else 0.0))
            elif flat:                                             # row mode, tied row -> neutral (the ramp would stretch noise)
                t = 0.5
            else:                                                  # row min -> row max
                t = (v - lo) / (hi - lo) if hi > lo else 0.5
            if np.isnan(v):
                continue
            fills[r][j] = tuple(mat * (1 - tint) + np.array(cmap(float(np.clip(t, 0, 1)))[:3]) * tint)
    spec_table_png(path, stub, cols, cells, label=label, title=title if STYLE["titles"] else None, groups=groups, numeric=numeric, fills=fills,
                   units="Ratios: mean value inside the area ÷ mean over allocatable (unprotected) land · 1.0× = the average allocatable cell",
                   notes=[("Note", "Blocks combine their layers with the block weights (carbon 74 / 26 by mass); representativeness = ecosystem "
                                   "classes present per cell; naturalness = 1 − human modification. "
                                   + (("Colour runs red → blue across each row from its lowest value to its highest" + (" over the cluster columns" if not all_cols else "") + "; a row whose values all round to the same figure is left neutral.") if STYLE.get("conseq_mode", "row") == "row"
                                      else "Colour runs across each row with 1.0× as the hinge and each side scaled to the row's own extreme.")),
                          *([("*", "Bear coexistence programs: not a ratio — the mean number of active bear coexistence groups recorded in the census divisions / "
                                     "counties the area overlaps (Y2Y Communities & Conservation, July 2026), cell-weighted; divisions with no recorded group are left out; "
                                     "— = none recorded in any overlapped division.")] if bear else []),
                          ("Source", source or SOURCE_NOTE)])


def values_table_spec(C, path, title="Y2Y Objectives Hierarchy", rows=None, metrics=None, label=None, units=None):
    """The objectives hierarchy to the table spec: stub = fundamental objective (first row of each group), then the
    sub-objective as a column-head group (heading → accent metric line → measure), the source in fine print, and how the
    layer enters the analysis. One frame separator after the stub; rules between rows; notes below."""
    rows = list(rows) if rows is not None else values_rows(C); metrics = list(metrics) if metrics is not None else values_metrics(C)
    B = STYLE["table_base_px"]; u = B * _PX; pt = B * 0.75; f_body = 0.87 * pt; pad_h = 0.47 * u
    col_w = [4.4 * u * 6.25, 2.9 * u * 6.25, 4.2 * u * 6.25]                   # inches at base 16: 4.4 / 2.9 / 4.2
    stub_w = 2.5 * u * 6.25
    wrap = lambda t, w, wt=400: _wrap_to(t, w - 2 * pad_h, f_body, wt)
    stub = [wrap(r[0], stub_w, 600) if r[0] else "" for r in rows]
    cells, numeric = [], []
    for r, m in zip(rows, metrics):
        cells.append([[(r[1], "head"), (m, "metric"), (wrap(r[2], col_w[0]), "body")],
                      [(wrap(r[3], col_w[1]), "fine")],
                      [(wrap(r[4], col_w[2]), "body")]])
        numeric.append([False, False, False])
    # stub rendered in ink 600: pass through the head style by prefixing the stub as a run (spec_table_png draws stubs in cap 400)
    spec_table_png(path, stub, ["Sub-objective and performance measure", "Source", "How it enters the analysis"], cells,
                   label=label or "Y2Y SPATIAL DECISION TOOL  ·  PROACT OBJECTIVES", title=title if STYLE["titles"] else None,
                   units=units or "How each objective is measured, and how it enters the optimization",
                   stub_head="Fundamental objective", col_w=col_w, stub_w=stub_w, numeric=numeric, stub_sep=True,
                   notes=[("Note", "Shares are of the objective's influence in the balanced position; each forward position doubles one "
                                   "theme's share. Targets are fractions of the regional total. Naturalness and representativeness enter "
                                   "outside the four weighted themes."),
                          ("Source", SOURCE_NOTE)])


def _f_1km(C):
    return dc.to_grid(C.G, np.where(C.G.disc, C.Fg, np.nan))


def _single_map(C, path, title, draw, handles, cbar_label=None, surface=None):
    S_ = surface or _f_surface(C)
    with plt.rc_context(SPEC_RC):
        fig, ax = plt.subplots(figsize=(8.2, 11.5))
        fig.subplots_adjust(left=0.02, right=0.98, top=0.89, bottom=0.085)
        ax.imshow(S_["img"], cmap=S_["cmap"], norm=S_["norm"], interpolation="nearest", zorder=0.5)
        if S_.get("ctx") is not None:
            ax.imshow(S_["ctx"], cmap=S_["cmap"], norm=S_["norm"], interpolation="nearest", zorder=0.45, alpha=STYLE["context_alpha"]); handles = list(handles) + ([C.CONTEXT_HANDLE] if C.CONTEXT_HANDLE is not None else [])
        C.draw_pa(ax); getattr(C, "draw_focus", lambda _a: None)(ax); draw(ax)
        C.finish(ax, "", handles, note="", legend_loc="outside")
        cax = fig.add_axes([0.20, 0.048, 0.60, 0.013])
        cb = fig.colorbar(ScalarMappable(norm=S_["norm"], cmap=S_["cmap"]), cax=cax, orientation="horizontal", extend=S_["extend"], ticks=S_.get("ticks"))
        if S_.get("ticklabels") is not None:
            cb.ax.set_xticklabels(S_["ticklabels"])
        cb.set_label("\n".join(textwrap.wrap(cbar_label or S_["label"] or STYLE["ramp_label"], 62)), fontsize=9, color=TABLE["mut"])
        if STYLE["titles"]:
            fig.suptitle(title, fontsize=STYLE["map_suptitle_fs"], y=0.975, color=TABLE["ink"], fontweight=600)
        fig.savefig(path, dpi=STYLE["export_dpi"], bbox_inches="tight"); plt.show()


def _inset_window(C, number, aspect_hw, act="Act 1"):
    """Pixel window (x0, x1, y_top, y_bottom) around a numbered cluster (Act 1 core / Act 2 scenario pick): its members' bounds
    + pad, at the inset's aspect."""
    p = C.PICKS[(C.PICKS.act == act) & (C.PICKS.number.astype(str) == str(number))].iloc[0]
    cids = [int(c) for c in str(p.cids).split(";")]
    g = C.CL["act1" if act == "Act 1" else f"act2_{p.key}"]; minx, miny, maxx, maxy = g[g.cid.isin(cids)].geometry.total_bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2; pad = STYLE["inset_pad_km"] * 1000
    w = max(maxx - minx + 2 * pad, STYLE["inset_min_km"] * 1000); h = max(maxy - miny + 2 * pad, STYLE["inset_min_km"] * 1000 * aspect_hw)
    if h / w < aspect_hw: h = w * aspect_hw
    else: w = h / aspect_hw
    px0, pyb = dc.xy_to_px(C.G, cx - w / 2, cy - h / 2); px1, pyt = dc.xy_to_px(C.G, cx + w / 2, cy + h / 2)
    if STYLE.get("inset_fit_pu", False):                        # the whole PU strip over the window's rows fits, centred (a narrow region: Alberta)
        r0, r1 = max(int(pyt), 0), min(int(np.ceil(pyb)), C.G.shape[0]); cols = np.where(C.G.pu[r0:r1].any(axis=0))[0]
        if cols.size:
            pad_px = STYLE["inset_pad_km"] * C.PX_PER_KM; c_lo, c_hi = cols.min() - pad_px, cols.max() + 1 + pad_px
            wpx = max(px1 - px0, c_hi - c_lo); cxp = 0.5 * (c_lo + c_hi); hpx = max(pyb - pyt, wpx * aspect_hw)   # never shrunk; the aspect re-fitted about the centre
            wpx = hpx / aspect_hw; cyp = 0.5 * (pyt + pyb)
            px0, px1, pyt, pyb = cxp - wpx / 2, cxp + wpx / 2, cyp - hpx / 2, cyp + hpx / 2
    return (float(px0), float(px1), float(pyt), float(pyb)), p


def _common_crop(fig, tight=None):
    """ONE export box for every wide-layout map (Ethan 2026-09-30: the Act 1 and Act 2 left-hand frames must be the same): the
    tight box's left and top (the frame's left edge and the inset titles, identical on both layouts) with the page's full width
    and bottom, so a three-inset Act 2 map and a two-inset Act 1 map crop to the same page and the frame lands at the same size."""
    from matplotlib.transforms import Bbox
    tb = tight if tight is not None else fig.get_tightbbox(fig.canvas.get_renderer()).padded(0.1)
    if not STYLE.get("wide_common_crop", True):
        return tb
    return Bbox.from_extents(tb.x0, 0.0, fig.get_figwidth(), tb.y1)


def _equalize_windows(wins):
    """Every window at ONE scale (Ethan 2026-09-30): the largest width and height among them, each re-centred on its own centre
    (the panels share an aspect, so the largest of both keeps it)."""
    if len(wins) < 2:
        return list(wins)
    w = max(x1 - x0 for x0, x1, _, _ in wins); h = max(yb - yt for _, _, yt, yb in wins)
    return [((x0 + x1) / 2 - w / 2, (x0 + x1) / 2 + w / 2, (yt + yb) / 2 - h / 2, (yt + yb) / 2 + h / 2) for x0, x1, yt, yb in wins]


def _act1_windows(C, aspect_hw):
    """The Act 1 insets' windows (A, B ...): sized on STYLE['inset_clusters'] or fixed by STYLE['inset_windows'], then one scale
    (inset_same_scale) and the hand nudge (inset_shift_km). The Act 2 map reuses them when scenario_insets_as_act1 is on."""
    wins = []
    for num, tag in zip(STYLE["inset_clusters"], "ABCDEF"):                     # windows sized on the clusters, titled A, B ... (Ethan)
        if STYLE.get("inset_windows") and tag in STYLE["inset_windows"]:       # fixed regions (Ethan 2026-09-21: keep the v3.1 windows across versions)
            wins.append(_fit_window(C, STYLE["inset_windows"][tag], aspect_hw))
        else:
            wins.append(_inset_window(C, num, aspect_hw)[0])
    if STYLE.get("inset_same_scale", True):                                   # panels A and B at one scale (Ethan 2026-09-30)
        wins = _equalize_windows(wins)
    if STYLE.get("inset_shift_km"):                                           # a hand nudge per inset, (east km, north km), after the fit (Alberta B, Ethan 2026-09-30)
        wins = [(x0 + dx * C.PX_PER_KM, x1 + dx * C.PX_PER_KM, yt - dy * C.PX_PER_KM, yb - dy * C.PX_PER_KM)
                for (x0, x1, yt, yb), (dx, dy) in zip(wins, (STYLE["inset_shift_km"].get(tag, (0, 0)) for tag in "ABCDEF"))]
    return wins


def _fit_window(C, win_px, aspect_hw):
    """A fixed pixel window (x0, x1, y_top, y_bottom) re-fitted to the inset's aspect around its own centre (never shrunk)."""
    px0, px1, pyt, pyb = win_px; cx, cy = (px0 + px1) / 2, (pyt + pyb) / 2; w, h = px1 - px0, pyb - pyt
    if h / w < aspect_hw: h = w * aspect_hw
    else: w = h / aspect_hw
    return (float(cx - w / 2), float(cx + w / 2), float(cy - h / 2), float(cy + h / 2))


def _draw_inset(C, ax, win, draw, title, with_ipca_names, towns=True, codes=None, skip_towns=(), img=None, cmap=None, norm=None, skip_areas=(), post_draw=None, ctx=None):
    px0, px1, pyt, pyb = win
    ax.imshow(_f_1km(C) if img is None else img, cmap=cmap or C.FCMAP, norm=norm or C.FNORM, interpolation="nearest", zorder=0.5, alpha=STYLE.get("_surface_alpha", 1.0))
    ctx = getattr(C, "CTX_F", None) if (ctx is None and img is None) else ctx     # the context surface beyond the focus PU (the f default follows the F surface)
    if ctx is not None:
        ax.imshow(ctx, cmap=cmap or C.FCMAP, norm=norm or C.FNORM, interpolation="nearest", zorder=0.45, alpha=STYLE["context_alpha"])
    ppk = C.PX_PER_KM                                                                 # km -> px on this grid (1 on the 1 km grid)
    dc.draw_basemap(ax, C.G, C.BM, hs=None, water=STYLE["water"], names=False, towns=[t for t in C.BM.towns if t not in skip_towns] if towns else (), window=win, fs_scale=STYLE["inset_fs"] / 8.0)
    hs = dc.read_hillshade_window(C.G, win, scale=max(1, int(round(3 / ppk)))) if STYLE["hillshade"] else None   # ~100 m sampling of the 300 m hillshade
    if hs is not None:
        rgba = np.zeros(hs.shape + (4,), np.float32); rgba[..., 3] = dc.BASEMAP["hillshade_alpha"] * (1.0 - hs.astype(np.float32) / 255.0)
        ax.imshow(rgba, extent=[px0, px1, pyb, pyt], interpolation="bilinear", zorder=0.6)
    C.draw_pa(ax); getattr(C, "draw_focus", lambda _a: None)(ax); draw(ax); dc.draw_admin(ax, C.G, C.ADMIN, **_border_kw())
    fs = STYLE["inset_fs"]; taken = []
    if STYLE["inset_abbrev"]:                                     # jurisdiction codes first; the area names keep clear of them
        taken = dc.label_jurisdictions_window(ax, C.G, C.BM, win, fs=STYLE["inset_abbrev_fs"] * (fs / 11.5), **(codes or {}))
    pan = C.PAN[~C.PAN["PA_Name"].isin(skip_areas)] if len(skip_areas) else C.PAN     # per-window name skips (a label the window edge would clip)
    dcl = STYLE.get("inset_declutter", True)                                                   # False = every name (the northern insets, 2026-09-28)
    taken = dc.label_areas_px(ax, C.G, pan, "PA_Name", win, top_n=STYLE["inset_pa_names"], color="0.25", fs=fs, taken=taken, declutter=dcl)
    if with_ipca_names:
        dc.label_areas_px(ax, C.G, C.IP.gdf, "name", win, top_n=STYLE.get("inset_ipca_names", 3), color="#a04a00", fs=fs, taken=taken, declutter=dcl)
    ax.set_xlim(px0, px1); ax.set_ylim(pyb, pyt); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(True); sp.set_edgecolor("#333333"); sp.set_linewidth(0.9)
    # 50 km scale bar, south-west corner (km x px_per_km)
    x, y = px0 + 0.05 * (px1 - px0), pyb - 0.05 * (pyb - pyt)
    ax.plot([x, x + 50 * ppk], [y, y], color="black", lw=2.5, solid_capstyle="butt", zorder=7)
    ax.annotate("50 km", xy=(x + 25 * ppk, y), xytext=(0, dc.SCALEBAR_GAP_PT), textcoords="offset points", ha="center", va="bottom", fontsize=STYLE["inset_fs"], zorder=7)   # same gap as the frame's bar
    ax.set_title(title, fontsize=STYLE["map_title_fs"] + 2, color=TABLE["ink"], fontweight=600, pad=6, loc="left")
    if post_draw is not None:                                              # a second pass once the labels and limits exist (the northern route numbers)
        post_draw(ax, win)
    C.place_cluster_numbers(ax, win)                                       # the cluster discs (no-op unless draw registered any)


WIDE_RECTS = {2: [(0.27, 0.19, 0.335, 0.66), (0.635, 0.19, 0.335, 0.66)],      # two tall insets (the Y2Y-wide layout)
              1: [(0.30, 0.17, 0.67, 0.70)]}                                   # one landscape inset (a narrow region: the Alberta mirror)


def _wide_map(C, path, title, draw, handles, cbar_label=None, with_ipca_names=False, surface=None, caption=None, keep=False, post_draw=None):
    """Slide-shaped Act 1 map: the frame at left, zoom insets around STYLE['inset_clusters'] at right, legend + ramp below.
    `surface` (dict: img, cmap, norm, extend, ticks, ticklabels, label) swaps the F ramp for another 1 km layer; default = F.
    `caption` = one line above the insets (the frames' running caption). `keep=True` (method_frames) returns the open figure
    with its three surface images, the ramp axes and the caption text so later frames swap the surface without redrawing the
    basemap (one build ~2 min; a swapped frame seconds)."""
    S_ = surface or _f_surface(C)
    with plt.rc_context(SPEC_RC):
        fig = plt.figure(figsize=(13.33, 7.5))
        ax = fig.add_axes([0.03, 0.04, 0.215, 0.84]); ax.set_anchor("E")      # the frame hugs inset A
        im_main = ax.imshow(S_["img"], cmap=S_["cmap"], norm=S_["norm"], interpolation="nearest", zorder=0.5, alpha=S_.get("alpha", 1.0))   # a surface may carry an alpha (the northern maps: 0.85, so the admin lines show through)
        axes_all, ims = [ax], [im_main]
        if S_.get("ctx") is not None:                                                  # the context analysis beyond the focus PU, muted, under the focus surface
            ax.imshow(S_["ctx"], cmap=S_["cmap"], norm=S_["norm"], interpolation="nearest", zorder=0.45, alpha=STYLE["context_alpha"]); handles = list(handles) + ([C.CONTEXT_HANDLE] if C.CONTEXT_HANDLE is not None else [])
        C.draw_pa(ax); getattr(C, "draw_focus", lambda _a: None)(ax); STYLE["_fs_scale"] = 0.9; STYLE["_defer_numbers"] = True
        try:
            draw(ax); C.finish(ax, "", None, note="", legend_loc="none", names=STYLE["wide_main_names"], towns=STYLE["wide_main_towns"],
                               name_fs=STYLE["wide_main_name_fs"])
            if post_draw is not None:                                        # after the frame's labels and limits (2026-09-29)
                post_draw(ax, C.WINDOW if C.WINDOW is not None else (0.0, float(C.G.shape[1]), 0.0, float(C.G.shape[0])))
        finally:
            STYLE.pop("_fs_scale", None); STYLE.pop("_defer_numbers", None)
        rects = WIDE_RECTS[min(len(STYLE["inset_clusters"]), 2)]
        aspect_hw = (rects[0][3] * 7.5) / (rects[0][2] * 13.33)
        wins = _act1_windows(C, aspect_hw)
        for (num, rect, tag, win) in zip(STYLE["inset_clusters"], rects, "ABCDEF", wins):
            iax = fig.add_axes(rect); STYLE["_fs_scale"] = STYLE["inset_number_fs"] / STYLE["cluster_number_fs"]; STYLE["_lw_scale"] = STYLE["cluster_lw_inset_scale"]
            STYLE["_surface_alpha"] = S_.get("alpha", 1.0)
            try:
                _draw_inset(C, iax, win, draw, tag, with_ipca_names, codes=STYLE["inset_codes"].get(tag), skip_towns=STYLE["inset_town_skip"].get(tag, ()),
                            img=S_["img"], cmap=S_["cmap"], norm=S_["norm"], post_draw=post_draw, ctx=S_.get("ctx"))
            finally:
                STYLE.pop("_fs_scale", None); STYLE.pop("_lw_scale", None); STYLE.pop("_surface_alpha", None)
            axes_all.append(iax); ims.append(iax.images[0])                             # the inset's surface image is its first
            px0, px1, pyt, pyb = win                                                   # the window on the frame, tagged
            ax.add_patch(Rectangle((px0, pyt), px1 - px0, pyb - pyt, fill=False, edgecolor="#333333", lw=1.0, zorder=7))
            ax.text(px0 + 8 * C.PX_PER_KM, pyt + 8 * C.PX_PER_KM, tag, fontsize=8, fontweight=600, color="white", ha="left", va="top", zorder=8,
                    bbox=dict(boxstyle="square,pad=0.15", facecolor="#333333", edgecolor="none"))
        C.place_cluster_numbers(ax, C.WINDOW)                                                  # the frame's discs, now that the inset tags (A / B) are on the axes too
        cax_rect = [0.27 + 0.015, 0.12, 0.335 - 0.03, 0.04]                                     # inset A's full width; bar + ticks + caption centred in the strip below it
        cax = fig.add_axes(cax_rect)
        _wide_ramp(cax, S_, cbar_label, end_words=(STYLE.get("ramp_end_labels") if surface is None else S_.get("end_words")))
        leg = fig.legend(handles=handles, loc=STYLE.get("wide_legend_loc", "center"), bbox_to_anchor=(0.635 + 0.335 / 2, STYLE.get("wide_legend_y", 0.103)), fontsize=STYLE["wide_legend_fs"],
                         frameon=True, framealpha=0.92, edgecolor="#9a9a9a", handlelength=2.6, handleheight=1.3, borderpad=0.7, labelspacing=0.6,
                         handler_map=cluster_handler_map(*handles))   # centred under inset B; the cluster entry = four colour swatches
        if STYLE.get("wide_legend_between", False):                      # the northern package (Ethan 2026-09-28): centre the box between inset B's bottom edge and
            r = fig.canvas.get_renderer(); inv = fig.transFigure.inverted()   # the bottom of the ramp block under A (= the page bottom once the figure is trimmed)
            top = rects[-1][1]; bottom = cax.get_tightbbox(r).transformed(inv).y0
            if STYLE.get("wide_legend_floor", "ramp") == "frame":                  # the FRAME's bottom edge as the floor (Alberta, Ethan 2026-09-30); "ramp" = the ramp block's (north)
                bottom = min(bottom, ax.get_position().y0)
            h = leg.get_window_extent(r).transformed(inv).height; pad = 0.012
            if STYLE.get("wide_legend_fit", False):                          # wolverine (Ethan 2026-09-29): size the items so the box fits the gap
                fs_ = float(STYLE["wide_legend_fs"]); fs_min = float(STYLE.get("wide_legend_fs_min", 9))
                while h > (top - bottom) - 2 * pad and fs_ - 0.5 >= fs_min:
                    fs_ -= 0.5; leg.remove()
                    leg = fig.legend(handles=handles, loc="center", bbox_to_anchor=(0.635 + 0.335 / 2, 0.5 * (top + bottom)), fontsize=fs_,
                                     frameon=True, framealpha=0.92, edgecolor="#9a9a9a", handlelength=2.6, handleheight=1.3, borderpad=0.7, labelspacing=0.6,
                                     handler_map=cluster_handler_map(*handles))
                    h = leg.get_window_extent(r).transformed(inv).height
                STYLE["_wide_legend_fs_used"] = fs_                           # read back by the caller (printed for the record)
            y_leg = min(0.5 * (top + bottom), top - pad - h / 2)       # centred in the gap; a legend taller than the gap hangs from B's bottom edge instead
            leg.set_loc("center"); leg.set_bbox_to_anchor((0.635 + 0.335 / 2, y_leg), transform=fig.transFigure)
        if STYLE["titles"]:
            fig.suptitle(title, fontsize=STYLE["map_suptitle_fs"], y=0.995, color=TABLE["ink"], fontweight=600)
        cap = fig.text(0.27, 0.955, (caption or "") if (STYLE.get("frames_caption", False) or not keep) else "", fontsize=STYLE["frames_caption_fs"],
                       color=TABLE["ink"], ha="left", va="bottom", fontweight=500) if (caption is not None or keep) else None
        if keep:                                                                 # the frames' persistent figure (no show, no close)
            # the frames crop to the SAME box the Act 1 maps are saved with (bbox_inches="tight" + matplotlib's 0.1 in pad), computed
            # once with the caption hidden, so a frame and the Act 1 slide share one extent exactly (Ethan 2026-09-23)
            if cap is not None:
                cap.set_visible(False)
            cax.remove(); cax = fig.add_axes(cax_rect)                          # measure with the Act 1 maps' own F ramp (its end-words row sets the bottom edge)
            _wide_ramp(cax, _f_surface(C), None, end_words=STYLE.get("ramp_end_labels"))
            crop = _common_crop(fig)                                         # = the Act 1 maps' export box
            cax.remove(); cax = fig.add_axes(cax_rect)                          # then put this frame's own ramp back
            _wide_ramp(cax, S_, cbar_label, end_words=S_.get("end_words"))
            if cap is not None:
                cap.set_visible(True)
            W = SimpleNamespace(fig=fig, axes=axes_all, ims=ims, cax=cax, cax_rect=cax_rect, cap=cap, crop=crop)
            if path is not None:
                fig.savefig(path, dpi=_frames_dpi(W), bbox_inches=crop)
            return W
        if STYLE.get("export_pdf"):                                                       # a vector twin beside the PNG (the northern package's §3a export rule)
            fig.savefig(pathlib.Path(path).with_suffix(".pdf"), bbox_inches="tight")
        STYLE["_act1_crop"] = _common_crop(fig)                                             # the box every wide map is saved with (frame left + inset top, full width + page bottom)
        fig.savefig(path, dpi=STYLE["export_dpi"], bbox_inches=STYLE["_act1_crop"]); plt.show()


wide_map = _wide_map     # the public name: corridors_director draws the northern package's curated maps through it (2026-09-28)


def _frames_dpi(W):
    """The dpi that makes a frame exactly STYLE["frames_width_px"] wide over its crop box (the Act 1 maps' tight box): the canvas
    truncates width x dpi to an integer, so aim half a pixel over."""
    return (STYLE["frames_width_px"] + 0.5) / W.crop.width


def _wide_ramp(cax, S_, cbar_label=None, end_words=None):
    """The ramp under inset A for a surface dict, drawn on a FRESH `cax` (a colorbar re-shapes the axes it is given, so a
    swapped frame removes the old axes and adds a new one at the same rect rather than clearing it)."""
    cb = cax.figure.colorbar(ScalarMappable(norm=S_["norm"], cmap=S_["cmap"]), cax=cax, orientation="horizontal", extend=S_["extend"], ticks=S_.get("ticks"),
                             alpha=S_.get("alpha", 1.0))                                              # the key's swatches at the surface's alpha
    if S_.get("ticklabels") is not None:
        cb.ax.set_xticklabels(S_["ticklabels"])
    cb.set_label(cbar_label or S_["label"] or STYLE["ramp_label_short"], fontsize=STYLE["cbar_fs"], color=TABLE["cap"], labelpad=(26 if end_words else 4))
    cb.ax.tick_params(labelsize=STYLE["cbar_fs"] - 1, length=4)
    if end_words:                                                                # a row between the tick numbers and the caption (the F ramp's two ends, in words)
        lo, hi = end_words; fs_ = STYLE["cbar_fs"] - 1
        cb.ax.text(0.0, -1.05, lo, transform=cb.ax.transAxes, ha="left", va="top", fontsize=fs_, color=TABLE["cap"], style="italic")
        cb.ax.text(1.0, -1.05, hi, transform=cb.ax.transAxes, ha="right", va="top", fontsize=fs_, color=TABLE["cap"], style="italic")
    return cb


def _wide_frame_save(W, S_, caption, path, cbar_label=None):
    """Swap the surface + caption on a kept wide figure (from _wide_map(keep=True)) and save one same-size frame."""
    with plt.rc_context(SPEC_RC):                                                # the swapped text keeps the table spec's type
        for im in W.ims:
            im.set_data(S_["img"]); im.set_cmap(S_["cmap"]); im.set_norm(S_["norm"])
        W.cax.remove(); W.cax = W.fig.add_axes(W.cax_rect)
        _wide_ramp(W.cax, S_, cbar_label, end_words=S_.get("end_words"))
        W.cap.set_text(caption if STYLE.get("frames_caption", False) else "")
        W.fig.savefig(path, dpi=_frames_dpi(W), bbox_inches=W.crop)   # the Act 1 maps' crop; an exact width (1920) for the video encoder


def _act1_map(C, path, title, draw, handles, cbar_label=None, with_ipca_names=False, surface=None):
    if STYLE["map_layout"] == "wide" and len(STYLE["inset_clusters"]):
        _wide_map(C, path, title, draw, handles, cbar_label, with_ipca_names, surface=surface)
    else:
        _single_map(C, path, title, draw, handles, cbar_label, surface=surface)


# ---- surfaces the Act 1 layout can carry: F (the default) and the values-convergence count ------------------------------
def _f_surface(C):
    ticks = np.arange(0, 0.71, 0.1); ticks[0] = C.FNORM.vmin                                  # the norm starts a hair above 0 (0 = never, grey); label it 0.0
    return dict(img=_f_1km(C), cmap=C.FCMAP, norm=C.FNORM, extend="both", ticks=ticks, ticklabels=[f"{t:.1f}" for t in np.arange(0, 0.71, 0.1)], label=ramp_label(C),
                ctx=getattr(C, "CTX_F", None))


def ramp_label(C):
    """The F/f ramp caption for the package's core basis (package spec v2.1: balanced; earlier packages: ensemble)."""
    return STYLE["ramp_label_balanced"] if getattr(C, "CORE_BASIS", "ensemble") == "balanced" else STYLE["ramp_label_short"]


def core_sentence(C):
    """The one-line Act 1 claim for titles, per the core basis."""
    return ("Act 1 — the balanced position's core: land in at least 70% of its near-optimal plans" if getattr(C, "CORE_BASIS", "ensemble") == "balanced"
            else "Act 1 — these areas recur in near-optimal plans no matter whose values prevail")


CONV_COLORS_ALL = ["#f2f2f2", "#dbe7f1", "#9ecae1", "#4292c6", "#08519c", "#08306b", "#041e42"]  # 0..6 themes (the Act 0 convergence map's ramp)
CONV_COLORS = CONV_COLORS_ALL[:len(dc.VALUE_THEMES) + 1]                                          # 0..5 before v4, 0..6 under v4


def conv_surface(C):
    """The values-convergence count at 1 km (Ethan 2026-09-15): the number of the five PROACT themes (0-5) in which a cell is in the
    top 30% of the allocatable landscape by percentile (19's value_convergence.tif; Act 0), as a categorical surface for the Act 1 layout."""
    img = dc.to_grid(C.G, np.where(C.G.disc, C.CONV.astype(np.float32), np.nan))
    km2 = C.SV["convergence_km2"]; n = len(dc.VALUE_THEMES)
    return dict(img=img, cmap=ListedColormap(CONV_COLORS), norm=BoundaryNorm(np.arange(-0.5, n + 1.5, 1), n + 1), extend="neither", ticks=list(range(n + 1)),
                ticklabels=[f"{k}\n{km2[str(k)]:,} km²" if str(k) in km2 else str(k) for k in range(n + 1)],
                label=f"number of the {n} value themes (of {n}) in which the cell is in the top 30% of allocatable land")


def values_map(C, path, title=None, with_clusters=False):
    """Act 1 in the VALUES currency (Ethan 2026-09-15, the Alberta deck leads with it): the same frame + inset layout as core_map_F, but the
    surface is the convergence count (0-5 themes top-30%) instead of F; (a) with the overlay outlined, (b) with the core clusters
    outlined and numbered. The F maps stay in the record (core_map_F / core_map_clusters)."""
    S_ = conv_surface(C); high = C.SV["high_value_km2"]; core_km2 = C.S["frequent_km2"]["guarded"]
    if with_clusters:
        draw = lambda ax: C.draw_clusters(ax, "act1", C.picks_for("Act 1"), fs=STYLE["cluster_number_fs"] * STYLE.get("_fs_scale", 1.0), lw=STYLE["cluster_lw"])
        handles = C.BASE_HANDLES[:1] + [cluster_handle("Core clusters", n=len(C.numbered("Act 1")))]
        ttl = title or (f"Act 1 — where the values converge, with the core clusters (F ≥ 0.70: {core_km2:,} km²)\n"
                        f"{high:,} km² of unprotected land is top-30% for at least one theme")
    else:
        draw = lambda ax: C.draw_ipca(ax)
        handles = C.BASE_HANDLES[:1] + C.IPCA_HANDLES
        ttl = title or (f"Act 1 — where the values converge: number of themes (of {len(dc.VALUE_THEMES)}) rating the cell top-30%\n"
                        f"{high:,} km² of unprotected land is top-30% for at least one theme")
    _act1_map(C, path, ttl, draw=draw, handles=handles, with_ipca_names=not with_clusters, surface=S_)


def alt_core(C, key="s0", clusters=True):
    """A comparison core built from ONE scenario's pooled plans (Ethan 2026-09-23: "core defined by the balanced runs only") by the
    registered Act 1 procedure — f = the scenario's pooled guarded frequency (both climate futures), tier f >= 0.70, closing r = 1,
    8-connectivity, >= 100 km2, complexes at 25 km, the top-k grouped into regional clusters at 75 km + specks absorbed, numbered
    north -> south — and its cluster polygons registered on C.CL as layer "act1_<key>". Not the registered core (that is F over all
    design cells); a presentation comparison. Returns (key, f, numbers, layer, core_km2, n_clusters, picks)."""
    G = C.G
    if key == "ensemble":                                                           # F over all design cells (the paper's estimand; appendix in the deck)
        f = np.asarray(C.Fens, dtype=np.float32); label = f"all {len(C.S['forms'])} value positions (ensemble F)"
    else:
        f = np.asarray(C.POOL[key], dtype=np.float32); label = f"{dc.SCENARIO_LABEL.get(key, key)} scenario only"
    core_km2 = int(((f >= dc.FREQ_THR) & G.disc).sum())
    if not clusters:                                                                # the F map needs only the surface (21 ships that map alone)
        return SimpleNamespace(key=key, f=f, numbers={}, layer=None, core_km2=core_km2, n_clusters=0, picks=None, label=label)
    lab, reg = dc.clusters(G, f); reg["name"] = ""
    reg, cx = dc.group_complexes(G, lab, reg)
    raw = pd.DataFrame([dict(number=i + 1, act="Act 1", key=key, cid=int(c.anchor_cid), cids=";".join(map(str, c.cids)), n_components=int(c.n),
                             name="", km2=float(c.km2), meanF=float(c.meanF), lat=float(c.lat), lon=float(c.lon))
                        for i, (_, c) in enumerate(cx.head(dc.TOPK_ACT1).iterrows())])
    gp = dc.group_picks(G, lab, raw)
    gp = dc.absorb_complexes(G, lab, gp, cx, link_km=dc.PICK_LINK_KM, reg=reg, speck_km=dc.SPECK_LINK_KM)
    numbers = {}
    for i, r in enumerate(gp.itertuples(), 1):
        for c in str(r.cids).split(";"):
            if str(c).strip():
                numbers[int(c)] = (str(i), int(c) == int(r.cid))
    regk = reg[reg.kept | reg.cid.isin(list(numbers))]
    v = dc.vectorize(G, lab, regk.cid.tolist()).merge(regk[["cid", "name", "km2", "meanF"]], on="cid")
    layer = f"act1_{key}"; C.CL[layer] = v
    return SimpleNamespace(key=key, f=f, numbers=numbers, layer=layer, core_km2=core_km2, n_clusters=len(gp), picks=gp, label=label)


def _basis_surface(C, basis):
    if basis.key == "ensemble":
        return _freq_surface(C, basis.f, f"F = frequency in 30×30 plans across all {len(C.S['forms'])} value positions")
    n_plans = 50 * int((C.MAN.scenario_id == basis.key).sum())                      # k = 50 guarded members per voting cell (both futures)
    return _freq_surface(C, basis.f, f"frequency in the {basis.label.lower().replace(' only', '')}'s {n_plans} near-optimal plans")


def core_map_F(C, path, title=None, basis=None):
    """Act 1 (a): F at 1 km over unprotected land, with the declared IPCA proposals outlined (+ zoom insets in the wide layout).
    `basis` (from alt_core) swaps F for one scenario's pooled f — the comparison view, not the registered core."""
    core_km2 = C.S["frequent_km2"]["guarded"] if basis is None else basis.core_km2
    if basis is not None:
        _act1_map(C, path, title or f"{'Appendix' if basis.key == 'ensemble' else 'Act 1'} — {basis.label}: frequency over unprotected land, with the declared IPCA proposals\n"
                                    f"frequent = {core_km2:,} km² at ≥ 0.70",
                  draw=lambda ax: C.draw_ipca(ax), handles=C.BASE_HANDLES[:1] + C.IPCA_HANDLES, with_ipca_names=True, surface=_basis_surface(C, basis))
        return
    _act1_map(C, path, title or (f"{core_sentence(C)}\n"
                                 f"core = {core_km2:,} km² (F ≥ 0.70) · no value theme left more than 5% behind"),
              draw=lambda ax: C.draw_ipca(ax), handles=C.BASE_HANDLES[:1] + C.IPCA_HANDLES, with_ipca_names=True)


def core_map_clusters(C, path, title=None, basis=None):
    """Act 1 (b): the same surface with the core clusters outlined and numbered north → south (+ zoom insets).
    `basis` (from alt_core) draws that scenario's own clusters on its own f — the comparison view."""
    core_km2 = C.S["frequent_km2"]["guarded"] if basis is None else basis.core_km2
    layer, numbers = ("act1", C.picks_for("Act 1")) if basis is None else (basis.layer, basis.numbers)
    ttl = title or (("Act 1 — the core clusters, numbered north → south\n" f"core = {core_km2:,} km² of unprotected land at F ≥ 0.70") if basis is None
                    else (f"Act 1 — {basis.label}: its clusters, numbered north → south\n" f"frequent = {core_km2:,} km² of unprotected land at f ≥ 0.70"))
    _act1_map(C, path, ttl,
              draw=lambda ax: C.draw_clusters(ax, layer, numbers, fs=STYLE["cluster_number_fs"] * STYLE.get("_fs_scale", 1.0), lw=STYLE["cluster_lw"]),
              handles=C.BASE_HANDLES[:1] + [cluster_handle("Core clusters" if basis is None else f"Clusters, {basis.label.lower()}",
                                                          n=len(C.numbered("Act 1")) if basis is None else basis.n_clusters)],
              surface=None if basis is None else _basis_surface(C, basis))


# ---- "the optimization behind the map" (Ethan 2026-09-21): frames for a timelapse on the Act 1 wide layout -------------------------
def _mask_surface(C, sel, color, ticklabels, label):
    """A binary 1 km surface (in / not in) over discretionary land, for the wide layout's ramp slot as a two-swatch key."""
    img = dc.to_grid(C.G, np.where(C.G.disc, np.asarray(sel, dtype=np.float32), np.nan))
    return dict(img=img, cmap=ListedColormap([NEVER_COLOR, color]), norm=BoundaryNorm([-0.5, 0.5, 1.5], 2), extend="neither",
                ticks=[0, 1], ticklabels=list(ticklabels), label=label, end_words=None)


def _freq_surface(C, f, label):
    """One formulation's f, or F, on the F ramp (yellow = at or above the 0.70 core threshold, as on the Act 1 maps)."""
    S_ = _f_surface(C)
    S_["img"] = dc.to_grid(C.G, np.where(C.G.disc, np.asarray(f, dtype=np.float32), np.nan)); S_["label"] = label
    S_["end_words"] = STYLE.get("ramp_end_labels")
    return S_


def method_frames(C, out_dir, reference_members=None, sample=None, design=False, runs=None):
    """Numbered PNG frames for a timelapse that introduces the method ("the optimization behind the map"), on the Act 1 wide
    layout (whole Y2Y at left, insets A / B at right). Sequence: each value theme's top-30% mask -> the reference cell's single
    optimal plan (its anchor) -> its near-optimal members one by one -> its f -> for every other voting cell a fixed-seed sample of
    members -> its f -> F over all cells -> the core (F >= 0.70) with its clusters outlined; cells run in the Act 2 legend order
    (STYLE["scenario_legend_order"]: climate refugia, mammal + bird richness, structural connectivity, climate corridors, biomass + soil
    carbon; the naturalness push last), reference climate first. Under the balanced core (package spec v2.1) the core frame follows the
    balanced scenario's f directly and there is no ensemble-F frame. `reference_members` / `sample` default
    to STYLE["frames_reference_members"] / STYLE["frames_sample_per_cell"] (50 / 10 = the presentation; 20 passes a small budget
    for the record). The basemap + insets are drawn ONCE (one wide map ~2 min) and every frame swaps the surface + caption on that
    figure (seconds), saved at STYLE["frames_width_px"] wide (1920, the dpi derived) without a tight bbox so all frames are the same pixel size. Writes frames.csv
    (file, segment, formulation, member, hold_s) and concat.txt for ffmpeg's concat demuxer; prints the assembly command (ffmpeg is
    not installed here -- Ethan assembles in his editor or with that command).
    `design=True` (Ethan 2026-09-21, the design pass before any full run): ONE member frame (plan 1) for the balanced scenario and
    each theme-forward scenario at the reference climate, shown inline in the notebook for feedback; no csv / concat.
    `runs` = the directory holding <formulation_id>/{anchor.tif, mga_guard_g05.tif} (default dc.RUNS, the flagship; the Alberta
    mirror passes config.ab_paths().runs / "A")."""
    import ensemble_core as ec
    reference_members = STYLE["frames_reference_members"] if reference_members is None else int(reference_members)
    sample = STYLE["frames_sample_per_cell"] if sample is None else int(sample)
    out_dir = pathlib.Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    for old in list(out_dir.glob("*.png")) + [out_dir / "frames.csv", out_dir / "concat.txt"]:   # the folder is this function's alone
        if old.exists():
            old.unlink()
    G, MAN = C.G, C.MAN; RUNS = pathlib.Path(runs) if runs is not None else dc.RUNS   # `runs`: another package's members (the Alberta mirror passes its own runs dir)
    ref = MAN.formulation_id[MAN.reference_cell.astype(str).str.lower().eq("true")].tolist() if "reference_cell" in MAN.columns else []
    ref = ref[0] if ref else "s0_ssp585_theta5"
    sid_of = MAN.set_index("formulation_id").scenario_id
    order = ["s0"] + [x for x in STYLE["scenario_legend_order"] if x != "s0"]        # the Act 2 legend order (Ethan 2026-09-21): core, then the PROACT order
    order += [x for x in dict.fromkeys(sid_of) if x not in order]                     # anything without an Act 2 entry (s5) last
    others = [f for clim in ("ssp585", "ssp245") for sid in order for f in MAN.formulation_id
              if f != ref and sid_of[f] == sid and clim in f]                         # reference climate first, each in the Act 2 order
    hold, dt = float(STYLE["frames_hold_s"]), 1.0 / float(STYLE["frames_fps"])
    words = STYLE["frames_climate_words"]; rng = np.random.default_rng(STYLE["frames_seed"])
    core_km2 = C.S["frequent_km2"]["guarded"]; nF = len(C.S["forms"])

    def cell_words(fid):
        sid = MAN.set_index("formulation_id").scenario_id[fid]
        clim = next((w for k, w in words.items() if k in fid), fid)
        return f"{dc.SCENARIO_LABEL.get(sid, sid)} scenario · {clim}"

    def key_words(fid):                                                             # the short form for the key label under inset A
        sid = MAN.set_index("formulation_id").scenario_id[fid]
        clim = next((w for k, w in words.items() if k in fid), fid).replace(" future", "")
        return f"{dc.SCENARIO_LABEL.get(sid, sid)} · {clim}"

    def plan_color(fid):                                                            # the Act 2 scenario colour; balanced / s5 = the neutral default
        return STYLE["scenario_colors"].get(MAN.set_index("formulation_id").scenario_id[fid], STYLE["frames_plan_color"])

    def f_of(fid):
        with rasterio.open(C.GEO / f"f_guarded_{fid}.tif") as src:
            return src.read(1)[G.pu]

    def members_of(fid):
        return ec.read_selections(RUNS / fid / "mga_guard_g05.tif", G.pu)          # (k, n_pu) bool: the guarded band = the estimand

    def anchor_of(fid):
        return ec.read_selections(RUNS / fid / "anchor.tif", G.pu)[0]

    plan_key = ("not in this plan", "in this plan"); value_key = ("below", "top 30% of unprotected land")
    frames = []                                                                     # (segment, formulation, member, surface, caption, hold)
    only_balanced = STYLE.get("frames_scenarios", "balanced") == "balanced"
    plans_only = STYLE.get("frames_plans_only", False)
    if only_balanced:                                                               # the balanced scenario's plans only (Ethan 2026-09-23): BOTH climate cells, every member (100 plans),
        others = [f for clim in STYLE.get("frames_climate_order", ("ssp585", "ssp245")) for f in MAN.formulation_id if sid_of[f] == "s0" and clim in f]
        reference_members = 0                                                       # ... in STYLE["frames_climate_order"]; the reference cell takes its turn in that order, not first
    if design:                                                                      # plan 1 of the balanced (+ each theme-forward cell when frames_scenarios = "all"), reference climate
        clim = next(k for k in words if k in ref)
        for sid in ["s0"] + ([] if only_balanced else [x for x in STYLE["scenario_legend_order"] if x != "s0"]):     # the Act 2 legend order
            fid = MAN.formulation_id[(MAN.scenario_id == sid) & MAN.formulation_id.str.contains(clim)].iloc[0]
            M = members_of(fid); k = M.shape[0]
            frames.append(("member", fid, 1, _mask_surface(C, M[0], plan_color(fid), plan_key, f"{key_words(fid)} · plan 1 of {k}"),
                           f"{cell_words(fid)} · near-optimal plan 1 of {k} — within 5% of the optimum, no value theme more than 5% behind", dt))
    for t in ([] if (design or plans_only) else dc.VALUE_THEMES):
        frames.append(("values", "", "", _mask_surface(C, C.VAL[t], STYLE["frames_value_color"], value_key, f"{axis_label(t)}: top 30% by value"),
                       f"Where the value is · {axis_label(t)}", hold))
    if not design and not plans_only:
        frames.append(("anchor", ref, "", _mask_surface(C, anchor_of(ref), plan_color(ref), plan_key, f"{key_words(ref)} · the single optimal plan"),
                       f"{cell_words(ref)} · the single best plan (the optimum)", hold))
    M = members_of(ref) if not design else np.zeros((0, G.n_pu), bool); k = M.shape[0]
    for j in range(min(reference_members, k)):
        frames.append(("member", ref, j + 1, _mask_surface(C, M[j], plan_color(ref), plan_key, f"{key_words(ref)} · plan {j + 1} of {k}"),
                       f"{cell_words(ref)} · near-optimal plan {j + 1} of {k} — within 5% of the optimum, no value theme more than 5% behind", dt))
    balanced = getattr(C, "CORE_BASIS", "ensemble") == "balanced"
    if not design and not plans_only:
        frames.append(("f", ref, "", _freq_surface(C, f_of(ref), f"{key_words(ref)} · frequency in {k} near-optimal plans"),
                       f"{cell_words(ref)} · how often each cell appears across the {k} near-optimal plans", hold))
    for fid in ([] if design else others):
        if sample > 0 or only_balanced:
            M = members_of(fid); k = M.shape[0]
            idx = np.arange(k) if only_balanced else np.sort(rng.choice(k, size=min(sample, k), replace=False))   # balanced-only: all of them
            for j in idx:
                frames.append(("member", fid, int(j) + 1, _mask_surface(C, M[j], plan_color(fid), plan_key, f"{key_words(fid)} · plan {j + 1} of {k}"),
                               f"{cell_words(fid)} · near-optimal plan {j + 1} of {k}", dt))
        if not plans_only:
            frames.append(("f", fid, "", _freq_surface(C, f_of(fid), f"{key_words(fid)} · frequency in near-optimal plans"),
                           f"{cell_words(fid)} · how often each cell appears across its near-optimal plans", hold))
    if not design and balanced and not plans_only:                                  # package spec v2.1: the core IS the balanced scenario's tier (both futures averaged) -> after its cells
        frames.append(("core", "", "", _freq_surface(C, C.Fg, ramp_label(C)),
                       f"The core: cells in at least 70% of the balanced scenario's plans — {core_km2:,} km² of unprotected land, outlined by cluster", hold))
    if not design and not balanced and not plans_only:                              # ensemble basis (earlier packages): F over all cells, then the core
        frames.append(("F", "", "", _freq_surface(C, C.Fg, STYLE["ramp_label_short"]),
                       f"All {nF} scenario × future combinations · F = how often each cell appears across {nF} × 50 near-optimal plans", hold))
        frames.append(("core", "", "", _freq_surface(C, C.Fg, STYLE["ramp_label_short"]),
                       f"The core: cells in at least 70% of all plans — {core_km2:,} km² of unprotected land, outlined by cluster", hold))

    import time
    t0 = time.time()
    seg0, fid0, _, S0, cap0, _ = frames[0]
    W = _wide_map(C, None, "", draw=lambda ax: C.draw_ipca(ax), handles=C.BASE_HANDLES[:1] + [C.IPCA_HANDLE], with_ipca_names=True,
                  surface=S0, caption=cap0, keep=True)                              # the IPCA proposals outlined in orange, as on the first Act 1 map (Ethan 2026-09-23)
    print(f"wide layout built once: {time.time() - t0:.0f} s; {len(frames)} frames -> {out_dir}")
    rows = []
    try:
        for i, (seg, fid, mem, S_, cap, h) in enumerate(frames):
            if seg == "core":                                                       # the last frame: the clusters outlined on the frame + both insets
                picks = C.picks_for("Act 1")
                for ax_ in W.axes:
                    inset = ax_ is not W.axes[0]
                    STYLE["_fs_scale"] = (STYLE["inset_number_fs"] / STYLE["cluster_number_fs"]) if inset else 0.9
                    STYLE["_lw_scale"] = STYLE["cluster_lw_inset_scale"] if inset else 1.0
                    try:
                        C.draw_clusters(ax_, "act1", picks, fs=STYLE["cluster_number_fs"] * STYLE["_fs_scale"], lw=STYLE["cluster_lw"])
                    finally:
                        STYLE.pop("_fs_scale", None); STYLE.pop("_lw_scale", None)
            name = f"{i:04d}_{seg}" + (f"_{fid}" if fid else "") + (f"_{int(mem):02d}" if mem != "" else "") + ".png"
            _wide_frame_save(W, S_, cap, out_dir / name)
            rows.append(dict(frame=i, file=name, segment=seg, formulation=fid, member=mem, hold_s=h))
            if design:                                                              # show each design frame in the notebook
                try:
                    from IPython.display import display, Image as _Img
                    display(_Img(filename=str(out_dir / name), width=1100))
                except Exception:
                    pass
    finally:
        plt.close(W.fig)
    df = pd.DataFrame(rows)
    if design:
        print(f"{len(df)} design frames in {time.time() - t0:.0f} s -> {out_dir}")
        return df
    df.to_csv(out_dir / "frames.csv", index=False)
    lines = []
    for r in rows:
        lines += [f"file '{r['file']}'", f"duration {r['hold_s']:.3f}"]
    lines.append(f"file '{rows[-1]['file']}'")                                       # the concat demuxer needs the last file repeated
    (out_dir / "concat.txt").write_text("\n".join(lines) + "\n")
    total = df.hold_s.sum()
    print(f"{len(df)} frames in {time.time() - t0:.0f} s; clip length {total:.0f} s at the frames.csv holds")
    if STYLE.get("frames_assemble", True):
        assemble_timelapse(out_dir)
    else:
        print(f"assemble with:\n  cd '{out_dir}' && ffmpeg -f concat -safe 0 -i concat.txt -vf 'fps=30,format=yuv420p' -c:v libx264 -crf 18 method_timelapse.mp4")
    return df


def assemble_timelapse(out_dir, name="method_timelapse.mp4"):
    """concat.txt (frames + holds) -> an H.264 mp4 at STYLE["frames_video_fps"], using the ffmpeg binary bundled with the venv's
    imageio-ffmpeg package (no system ffmpeg on this Mac). Returns the video path."""
    import subprocess
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:                                                          # no bundled binary: leave the frames + the command
        print(f"no ffmpeg available ({e}); frames and concat.txt are in {out_dir}"); return None
    out_dir = pathlib.Path(out_dir); video = out_dir / name
    base = [exe, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(out_dir / "concat.txt"),
            "-vf", f"fps={STYLE.get('frames_video_fps', 30)},scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",   # even dimensions for H.264
            "-c:v", "libx264", "-preset", "slow", "-movflags", "+faststart"]
    subprocess.run(base + ["-crf", str(STYLE.get("frames_video_crf", 18)), str(video)], check=True, cwd=str(out_dir))
    mb = video.stat().st_size / 1e6; cap = STYLE.get("frames_video_max_mb")
    if cap and mb > cap:                                                            # over the cap: two-pass at the bitrate that fits (quality spread evenly)
        secs = float(pd.read_csv(out_dir / "frames.csv").hold_s.sum())
        kbps = int(0.92 * cap * 8000 / max(secs, 1e-6))                               # 8% headroom for the container + audio-less overhead
        log = out_dir / "ffmpeg2pass"
        subprocess.run(base + ["-b:v", f"{kbps}k", "-pass", "1", "-passlogfile", str(log), "-an", "-f", "null", "/dev/null"], check=True, cwd=str(out_dir))
        subprocess.run(base + ["-b:v", f"{kbps}k", "-pass", "2", "-passlogfile", str(log), str(video)], check=True, cwd=str(out_dir))
        for f in out_dir.glob("ffmpeg2pass*"):
            f.unlink()
        print(f"CRF {STYLE.get('frames_video_crf', 18)} gave {mb:.1f} MB > {cap} MB cap -> two-pass at {kbps} kb/s")
    info = subprocess.run([exe, "-i", str(video)], capture_output=True, text=True).stderr
    dur = next((l.strip() for l in info.splitlines() if "Duration" in l), "")
    print(f"timelapse -> {video} ({video.stat().st_size / 1e6:.1f} MB; {dur})")
    return video


# ---- the bare-bones objectives table for the presentation (Ethan, 2026-09-14): fundamental → sub-objective → measure, no numbers ----
VALUES_SIMPLE = [
    ("PROTECT — wildlife have sufficient core habitat", "Quantity of core habitat", ["Protected land"]),
    ("", "Quality of core habitat", ["Climate refugia", "Naturalness"]),
    ("", "Biodiversity", ["Mammal richness", "Bird richness"]),
    ("", "Representativeness", ["Ecosystem functional groups"]),
    *([("CONNECT — wildlife corridors connect core habitats", "Structural connectivity", ["Habitat connectivity"]),
       ("", "Climate corridors", ["Climate corridors"])] if dc.VP.version == "v4"
      else [("CONNECT — wildlife corridors connect core habitats", "Quality of connectivity", ["Climate corridors", "Habitat connectivity"])]),
    ("ADDRESS CLIMATE CHANGE — keep carbon out of the air", "Carbon", ["Irrecoverable carbon (biomass)", "Irrecoverable carbon (mineral soil)"]),
    ("NOT IN THIS ANALYSIS", "Communities · Water · Cost", ["—"]),
]


def values_table_simple(C, path, title="Y2Y Objectives Hierarchy"):
    """The presentation's objectives table: fundamental objective, sub-objective, performance measure(s); no shares or targets."""
    B = STYLE["table_base_px"]; u = B * _PX; pt = B * 0.75; f_body = 0.87 * pt; pad_h = 0.47 * u
    stub_w = 2.6 * u * 6.25
    stub = [_wrap_to(f, stub_w - 2 * pad_h, f_body) if f else "" for f, _, _ in VALUES_SIMPLE]
    cells = [[[(sub, "head")], [("\n".join(meas), "body")]] for _, sub, meas in VALUES_SIMPLE]
    numeric = [[False, False] for _ in VALUES_SIMPLE]
    spec_table_png(path, stub, ["Sub-objective", "Performance measure"], cells, label="Y2Y SPATIAL DECISION TOOL  ·  PROACT OBJECTIVES",
                   title=title if STYLE["titles"] else None, stub_head="Fundamental objective", stub_w=stub_w, numeric=numeric, stub_sep=True,
                   notes=[("Source", SOURCE_NOTE)])


def scenario_map(C, path, title=None):
    """ACT 2 = ONE MAP (Ethan 2026-09-15): the reliability tiers at 1 km with the scenario tier split by the value position that
    earns each cell -- core yellow, each forward position its own colour, two-or-more navy, opportunity pale, PAs grey -- on the
    Act 1 wide layout: the frame at left, three inset windows (STYLE['scenario_insets']) at right, and a legend below that
    states the area and the share of allocatable (unprotected) land each position adds to the core."""
    G, S = C.G, C.S
    with rasterio.open(C.GEO / "act2_owner.tif") as src:
        OWN = src.read(1)                                   # 2-D, like TIERS (rd() would give the PU vector)
    T = C.TIERS; SC = STYLE["scenario_colors"]
    NS = len(dc.ACT2_SCENARIOS)                          # owner codes 1..NS (19 cell 3); MULTI_OWNER = frequent under two or more
    cls = np.full(G.shape, np.nan, np.float32); cls[G.pu] = 0; cls[T == 1] = 1
    for i, sid in enumerate(dc.ACT2_SCENARIOS, 1):
        cls[(T == 2) & (OWN == i)] = 1 + i
    cls[(T == 2) & (OWN == dc.MULTI_OWNER)] = NS + 2; cls[T == 3] = NS + 3; cls[~G.pu] = np.nan
    cls_ctx = None
    if getattr(C, "CTX_TIERS", None) is not None:                               # the context analysis's tiers beyond the focus PU (same codes: 19 / 12 cell 3)
        Tc, Oc = C.CTX_TIERS, C.CTX_OWNER; cls_ctx = np.full(G.shape, np.nan, np.float32)
        cls_ctx[Tc == 1] = 1
        for i, sid in enumerate(dc.ACT2_SCENARIOS, 1):
            cls_ctx[(Tc == 2) & (Oc == i)] = 1 + i
        cls_ctx[(Tc == 2) & (Oc == dc.MULTI_OWNER)] = NS + 2; cls_ctx[Tc == 3] = NS + 3; cls_ctx[G.pu] = np.nan
    cmap = ListedColormap([STYLE["never_color"], STYLE["opportunity_color"]] + [SC[sid] for sid in dc.ACT2_SCENARIOS] + [STYLE["scenario_multi_color"], "#ffd93b"])
    norm = BoundaryNorm(np.arange(-0.5, NS + 4.5, 1), NS + 4)
    nd = G.n_disc; own = S["act2_owner_km2"]; core = S["frequent_km2"]["guarded"]; opp = int(((T == 1) & G.pu).sum())
    pct = lambda km2: f"{100 * km2 / nd:.1f}%" if 100 * km2 / nd >= 0.1 else f"{100 * km2 / nd:.2f}%"
    short = {sid: f"{w[0].upper()}{w[1:]}" for sid, w in dc.SCENARIO_WORD.items()}   # legend words (Ethan 2026-09-15; 2026-09-23: climate refugia, mammal + bird richness, biomass + soil carbon)
    core_word = "Balanced" if getattr(C, "CORE_BASIS", "ensemble") == "balanced" else "Core"     # the yellow tier IS the balanced scenario's core (Ethan 2026-09-23)
    handles = [Patch(facecolor="#ffd93b", label=f"{core_word} · {core:,} km² · {pct(core)}")]
    for sid in STYLE["scenario_legend_order"]:                                                  # core first, then the PROACT order
        km2 = own[dc.SCENARIO_LABEL[sid]]
        handles.append(Patch(facecolor=SC[sid], label=f"{short[sid]} · {km2:,} km² · {pct(km2)}"))
    handles += [Patch(facecolor=STYLE["scenario_multi_color"], label=f"Two or more · {own['2+ scenarios']:,} km² · {pct(own['2+ scenarios'])}")]
    if STYLE["show_opportunity"]:
        handles.append(Patch(facecolor=STYLE["opportunity_color"], label=f"In at least one near-optimal plan · {opp:,} km² · {pct(opp)}"))
    handles += [Patch(facecolor=PA_COLOR, label="Protected areas (locked in)")] + C.IPCA_HANDLES + ([C.CONTEXT_HANDLE] if (cls_ctx is not None and C.CONTEXT_HANDLE is not None) else [])
    with plt.rc_context(SPEC_RC):
        fig = plt.figure(figsize=(13.33, 7.5))
        ax = fig.add_axes([0.03, 0.04, 0.215, 0.84]); ax.set_anchor("E")
        ax.imshow(cls, cmap=cmap, norm=norm, interpolation="nearest", zorder=0.5)
        if cls_ctx is not None:
            ax.imshow(cls_ctx, cmap=cmap, norm=norm, interpolation="nearest", zorder=0.45, alpha=STYLE["context_alpha"])
        C.draw_pa(ax); getattr(C, "draw_focus", lambda _a: None)(ax); C.draw_ipca(ax); STYLE["_fs_scale"] = 0.9
        try:
            C.finish(ax, "", None, note="", legend_loc="none", names=STYLE["wide_main_names"], towns=STYLE["wide_main_towns"], name_fs=STYLE["wide_main_name_fs"])
        finally:
            STYLE.pop("_fs_scale", None)
        as_act1 = bool(STYLE.get("scenario_insets_as_act1", False)) and len(STYLE["inset_clusters"]) > 0   # the Act 1 panels A / B on the Act 2 map (Ethan 2026-09-30)
        keys = STYLE["inset_clusters"] if as_act1 else STYLE["scenario_insets"]
        n = len(keys); gap = 0.02; x0, x1 = 0.27, 0.985; w = (x1 - x0 - gap * (n - 1)) / n
        rects = [(x0 + i * (w + gap), 0.25, w, 0.60) for i in range(n)]
        if as_act1:                                                                # the Act 1 maps' own panel rectangles (and their footprint for the export crop)
            rects = list(WIDE_RECTS[min(n, 2)]); x0, x1 = rects[0][0], rects[-1][0] + rects[-1][2]
        aspect_hw = (rects[0][3] * 7.5) / (rects[0][2] * 13.33)
        if as_act1:
            _r1 = WIDE_RECTS[min(len(STYLE["inset_clusters"]), 2)][0]; _a1 = (_r1[3] * 7.5) / (_r1[2] * 13.33)
            wins = [_fit_window(C, wn, aspect_hw) for wn in _act1_windows(C, _a1)]      # the Act 1 windows, re-fitted to these panels' aspect about the same centres
        else:
            wins = []
            for num, tag in zip(keys, "ABCDEF"):
                if STYLE.get("scenario_inset_windows") and tag in STYLE["scenario_inset_windows"]:   # fixed regions (Ethan 2026-09-21), as on the Act 1 maps
                    wins.append(_fit_window(C, STYLE["scenario_inset_windows"][tag], aspect_hw))
                else:
                    wins.append(_inset_window(C, num, aspect_hw, act="Act 2")[0])
            if STYLE.get("inset_same_scale", True):                               # every inset of a panel set at ONE scale and size (Ethan 2026-10-01)
                wins = _equalize_windows(wins)
        for num, rect, tag, win in zip(keys, rects, "ABCDEF", wins):
            iax = fig.add_axes(rect)
            _draw_inset(C, iax, win, lambda ax_: C.draw_ipca(ax_), tag, with_ipca_names=True, codes=STYLE["scenario_inset_codes"].get(tag),
                        skip_towns=STYLE["scenario_inset_town_skip"].get(tag, ()), img=cls, cmap=cmap, norm=norm,
                        skip_areas=STYLE.get("scenario_inset_area_skip", {}).get(tag, ()), ctx=cls_ctx)
            px0, px1, pyt, pyb = win
            ax.add_patch(Rectangle((px0, pyt), px1 - px0, pyb - pyt, fill=False, edgecolor="#333333", lw=1.0, zorder=7))
            ax.text(px0 + 8 * C.PX_PER_KM, pyt + 8 * C.PX_PER_KM, tag, fontsize=8, fontweight=600, color="white", ha="left", va="top", zorder=8,
                    bbox=dict(boxstyle="square,pad=0.15", facecolor="#333333", edgecolor="none"))
        y_leg2 = (0.5 * (rects[0][1] + 0.04) if (STYLE.get("scenario_legend_between", True) or STYLE.get("wide_legend_between", False))   # centred between the insets' bottom edge and the
                  else STYLE.get("scenario_legend_y", 0.115))                                                                          # page bottom (= the frame's bottom, 0.04; Ethan 2026-09-30)
        # the box must FIT the gap between the insets' bottom edge and the page bottom (Ethan 2026-09-30): shrink the type and tighten the
        # spacing step by step until it does, then centre it in the gap
        gap_top, gap_bot = rects[0][1], 0.04; fs_ = STYLE["scenario_legend_fs"]; tight = STYLE.get("scenario_legend_between", True)
        kw = dict(handlelength=2.2, handleheight=1.2, borderpad=0.7, labelspacing=0.55, columnspacing=1.6)
        if tight:
            kw = dict(handlelength=1.8, handleheight=1.0, borderpad=0.45, labelspacing=0.3, columnspacing=1.2)
        for _ in range(12):
            leg = fig.legend(handles=handles, loc="center", bbox_to_anchor=((x0 + x1) / 2, y_leg2), ncol=2, fontsize=fs_,
                             frameon=True, framealpha=0.92, edgecolor="#9a9a9a", **kw)
            if not tight:
                break
            h_frac = leg.get_window_extent(fig.canvas.get_renderer()).height / fig.bbox.height
            if h_frac <= (gap_top - gap_bot) - 0.02 or fs_ <= 9:
                break
            leg.remove(); fs_ -= 1
        if STYLE["titles"]:
            fig.suptitle(title or "Act 2 — what each value-forward position adds to the core", fontsize=STYLE["map_suptitle_fs"], y=0.995, color=TABLE["ink"], fontweight=600)
        _crop = _common_crop(fig)                                   # the same export box as the Act 1 maps, so the left-hand frame lands at the same size and place (Ethan 2026-09-30)
        fig.savefig(path, dpi=STYLE["export_dpi"], bbox_inches=_crop); plt.show()
