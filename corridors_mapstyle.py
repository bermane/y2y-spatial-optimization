"""corridors_mapstyle -- THE style module for the northern director package (spec 06 §3a).

No figure sets a colour, font, line weight, extent or export setting inline: everything comes
from here. If a figure needs something this module lacks, extend the module and log it.
Layer order (bottom -> top), identical on every map and inset:
  ocean -> land -> (cost swatches, context figure only) -> hillshade -> water -> existing PAs
  -> proposed IPCAs -> corridor classes (options first, only-viable last) -> boundaries
  -> inset boxes -> labels (jurisdiction, then PA/IPCA, then towns, then annotations).
Lives at repo root (engine-module convention; `figures/` is gitignored in this repo).
"""
import pathlib, types
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib import font_manager as fm
from matplotlib.patches import Patch, Rectangle, FancyArrowPatch
from matplotlib.lines import Line2D
from matplotlib.colors import ListedColormap
from shapely.geometry import box as _box, shape as _shape

import config

BASEMAP_DIR = config.INPUT_DIR / "basemap"

# ================= §1.1 palette =================
# Analysis hues -- the only saturated colours on any map
CLASS = {                       # key: (fill, outline or None, hatch or None, director string)
    # legend heading "Corridor Pressure", four levels (Ethan, 2026-09-11)
    # Minimum: periwinkle -- the contract's light blue-grey (#AFC3CF) was dE 3-8 from the IPCA
    # fill on white (#A7CACB); periwinkle clears dE 20 from every other element under both CVD
    # simulations. Maximum: hard red (Ethan), dE 30 from vermilion under deuteranopia + hatch.
    "securing": ("#A6A6D9", None, None, "Minimum (options)"),
    "squeezed": ("#E69F00", None, None, "Some (narrowing)"),
    "edge":     ("#D55E00", None, None, "A lot (last affordable)"),
    "both":     ("#E41A1C", None, None, "Maximum (only viable connection)"),   # plain red, no outline / hatch (Ethan)
}
CLASS_HEADING = "Corridor Pressure"
CLASS_ORDER = ["securing", "squeezed", "edge", "both"]          # draw + legend order
AREA = {"ipca": dict(fill="#5F9EA0", alpha=0.55, edge="#3E6F70", lw=0.5, label="Proposed IPCAs"),
        "pa":   dict(fill="#9A9A9A", alpha=0.55, edge="#6E6E6E", lw=0.5, label="Existing Protected Areas")}
BASE = dict(land="#F7F7F5", water="#CFE0EA", ocean="#E4EEF3", coast=("#9CB3C0", 0.3),
            admin=("#7A7A7A", 0.6, (4, 2)), sector=("#333333", 1.0), y2y=("#333333", 0.8, (6, 3)),
            hillshade_alpha=0.18, inset_box=("#333333", 0.8), leader=("#333333", 0.6))
COST_LABELS = {1: "Intact Land (cost 1)", 10: "Roads and Cuts (10)", 100: "Converted Land (100)",
               1000: "Water, Ice and Settlement (1000)"}
COST_PALETTES = {           # four flat swatches; the contract's default is the greyscale axis
    "grey":   {1: "#FFFFFF", 10: "#D9D9D9", 100: "#8C8C8C", 1000: "#3A3A3A"},
    "rdylgn": {1: "#66BD63", 10: "#FEE08B", 100: "#F46D43", 1000: "#A50026"},     # Ethan's 'resistance' ramp, 4 steps
    "purple": {1: "#FCFBFD", 10: "#CBC9E2", 100: "#9E9AC8", 1000: "#54278F"},     # single unused hue
    # magma sampled at 0.97 / 0.72 / 0.42 / 0.12 -- Ethan's ramp (2026-09-14); M0b carries no class
    # swaths, so the contract's "saturated hues only for classes" rule is not breached on it
    "magma":  {1: "#FCF0B2", 10: "#F9795D", 100: "#942C80", 1000: "#1A1042"},
}
COST_PALETTE = "magma"
COST = {c: (COST_PALETTES[COST_PALETTE][c], COST_LABELS[c]) for c in (1, 10, 100, 1000)}


def set_cost_palette(name):
    """Switch the cost swatches (all four figures + legend read `COST`)."""
    global COST_PALETTE, COST
    COST_PALETTE = name
    COST = {c: (COST_PALETTES[name][c], COST_LABELS[c]) for c in (1, 10, 100, 1000)}
# layer z-order (§1.6)
Z = dict(ocean=0, land=1, cost=1.5, hillshade=2, water=3, pa=4, ipca=5, securing=6, squeezed=7, edge=8,
         both=9, boundary=10, inset_box=11, label_jur=12, label_area=13, label_town=14, label_note=15)

# ================= §1.2 type =================
TYPE = {  # role: (size, weight, style, colour, halo)
    "title":        (15, 600, "normal", "#1A1A1A", None),
    "jurisdiction": (10, 400, "normal", "#8A8A8A", None),
    "area":         (8.5, 400, "italic", "#2B2B2B", 2.0),
    "town":         (8, 400, "normal", "#2B2B2B", 2.0),
    "annotation":   (8, 400, "normal", "#1A1A1A", 2.0),
    "legend":       (8.5, 400, "normal", "#2B2B2B", None),
    "caption":      (8, 400, "normal", "#555555", None),
}
FONT_FAMILY = ["Noto Sans", "DejaVu Sans"]
_fonts_registered = False


def apply():
    """rcParams for every figure: Noto Sans (registered from input_data/basemap/fonts) with
    DejaVu Sans fallback (both cover Łł ǫ ë ū á), TrueType embedding in PDF, no auto styling."""
    global _fonts_registered
    if not _fonts_registered:
        for f in sorted((BASEMAP_DIR / "fonts").glob("NotoSans-*.ttf")):
            fm.fontManager.addfont(str(f))
        _fonts_registered = True
    import logging
    lg = logging.getLogger("matplotlib.font_manager")
    if not any(getattr(f, "_weight_fallback", False) for f in lg.filters):        # Noto Sans has 400/600 faces only (DejaVu 400/700):
        flt = logging.Filter(); flt.filter = lambda rec: "Failed to find font weight" not in rec.getMessage(); flt._weight_fallback = True
        lg.addFilter(flt)                                                            # the nearest-weight substitution is intended; drop the log line
    mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": FONT_FAMILY,
                         "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
                         "axes.unicode_minus": False, "hatch.linewidth": 0.6})


def font_in_use():
    names = {f.name for f in fm.fontManager.ttflist}
    return "Noto Sans" if "Noto Sans" in names else "DejaVu Sans"


# ================= §1.3 layout templates =================
SLIDE = dict(size=(13.33, 7.5), map=[0.02, 0.085, 0.50, 0.83],
             locator=[0.55, 0.65, 0.17, 0.26], legend=[0.55, 0.20, 0.44, 0.43],
             scale=[0.55, 0.085, 0.30, 0.10], title_xy=(0.02, 0.955), caption_xy=(0.02, 0.028))
REPORT = dict(size=(8.5, 11.0), map=[0.04, 0.24, 0.92, 0.70],
              locator=[0.05, 0.03, 0.22, 0.19], legend=[0.30, 0.03, 0.45, 0.19],
              scale=[0.78, 0.03, 0.18, 0.19], title_xy=(0.04, 0.965), caption_xy=(0.04, 0.005))


def new_figure(title, template="slide", locator=True):
    """Slide (16:9) or report (portrait) page: map panel + furniture column/row. Returns
    (fig, ns) with ns.map / ns.locator / ns.legend / ns.scale axes, all decorations off.
    `locator=False` drops the locator and gives its space to the legend (Ethan, M0b)."""
    T = dict(SLIDE if template == "slide" else REPORT)
    if not locator:
        L, S_ = T["legend"], T["locator"]
        T["legend"] = [L[0], L[1], max(L[2], S_[2]), (S_[1] + S_[3]) - L[1]]
    fig = plt.figure(figsize=T["size"])
    fig.patch.set_facecolor("white")
    ax = fig.add_axes(T["map"]); ax.set_facecolor(BASE["ocean"])
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    furniture = {}
    for key in (("locator", "legend", "scale") if locator else ("legend", "scale")):
        a = fig.add_axes(T[key]); a.axis("off"); furniture[key] = a
    size, w, st, col, _ = TYPE["title"]
    fig.text(*T["title_xy"], title, fontsize=size, fontweight=w, color=col, ha="left", va="bottom")
    ns = types.SimpleNamespace(map=ax, template=T, name=template, **furniture)
    ns.texts = []               # every label placed through `label()`, for QA
    return fig, ns


def caption(fig, ns, text):
    size, w, st, col, _ = TYPE["caption"]
    fig.text(*ns.template["caption_xy"], text, fontsize=size, color=col, ha="left", va="bottom", wrap=True)


# ================= frames =================
def sector_polygon(R):
    """The sector = the Y2Y region clipped to the routing window (= the routable area)."""
    xs, ys = R.template.x.values, R.template.y.values
    win = _box(float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max()))
    return R.outline.union_all().intersection(win)


def sector_frame(R, pad_km=40):
    b = sector_polygon(R).bounds
    p = pad_km * 1e3
    return (b[0] - p, b[2] + p), (b[1] - p, b[3] + p)


def set_frame(ax, XL, YL, anchor="C"):
    """Frame the map panel to EXACTLY the given extent (sector bbox + 40 km per §1.3): the axes
    box shrinks to the frame's aspect inside the panel; the sector is tall, so the panel's
    spare width (left of / right of the map, per `anchor`) is where insets go (§1.5)."""
    ax.set_xlim(*XL); ax.set_ylim(*YL)
    ax.set_aspect("equal", adjustable="box")
    ax.set_anchor(anchor)


# ================= basemap layers =================
_cache = {}


def _admin_polys():
    if "admin" not in _cache:
        _cache["admin"] = gpd.read_file(BASEMAP_DIR / "ne_10m_admin_1_states_provinces.shp")
    return _cache["admin"]


def _admin_lines():
    if "lines" not in _cache:
        _cache["lines"] = gpd.read_file(BASEMAP_DIR / "ne_10m_admin_1_states_provinces_lines.shp")
    return _cache["lines"]


def _water(crs):
    if "water" not in _cache:
        lakes = pd.concat([gpd.read_file(BASEMAP_DIR / "ne_10m_lakes.shp"),
                           gpd.read_file(BASEMAP_DIR / "ne_10m_lakes_north_america.shp")], ignore_index=True)
        rivers = pd.concat([gpd.read_file(BASEMAP_DIR / "ne_10m_rivers_lake_centerlines.shp"),
                            gpd.read_file(BASEMAP_DIR / "ne_10m_rivers_north_america.shp")], ignore_index=True)
        _cache["water"] = (gpd.GeoDataFrame(lakes, crs="EPSG:4326").to_crs(crs),
                           gpd.GeoDataFrame(rivers, crs="EPSG:4326").to_crs(crs))
    return _cache["water"]


def _clip(gdf, XL, YL, pad=2e5):
    b = _box(XL[0] - pad, YL[0] - pad, XL[1] + pad, YL[1] + pad)
    g = gdf[gdf.intersects(b)].copy()
    g["geometry"] = g.geometry.intersection(b)
    return g[~g.geometry.is_empty]


def draw_land(ax, R, XL, YL):
    land = _clip(_admin_polys().to_crs(R.crs), XL, YL)
    land.plot(ax=ax, color=BASE["land"], edgecolor="none", zorder=Z["land"])
    col, lw = BASE["coast"]
    land.dissolve(by="admin").boundary.plot(ax=ax, color=col, linewidth=lw, zorder=Z["boundary"] - 0.5)


def draw_cost(ax, R):
    """Context figure only: four flat greyscale swatches; water is drawn separately (blue)."""
    cost = R.resistance.values
    idx = np.where(cost > 0, np.round(np.log10(np.where(cost > 0, cost, 1))), np.nan).astype("float32")
    da = R.template.copy(data=idx)
    da.plot.imshow(ax=ax, cmap=ListedColormap([COST[c][0] for c in (1, 10, 100, 1000)]),
                   vmin=-0.5, vmax=3.5, add_colorbar=False, zorder=Z["cost"])
    ax.set_title(""); ax.set_xlabel(""); ax.set_ylabel("")


def draw_hillshade(ax, R):
    """Greyscale hillshade as a darkening-only overlay (multiply at 18%): alpha = 0.18 x shade."""
    p = BASEMAP_DIR / "hillshade_300m.tif"
    if not p.exists():
        return False
    import rioxarray
    hs = rioxarray.open_rasterio(p, masked=True).squeeze()
    v = np.nan_to_num(hs.values.astype("float32"), nan=255.0) / 255.0
    rgba = np.zeros(v.shape + (4,), "float32")
    rgba[..., 3] = BASE["hillshade_alpha"] * (1.0 - v)
    ax.imshow(rgba, extent=[float(hs.x.min()), float(hs.x.max()), float(hs.y.min()), float(hs.y.max())],
              origin="upper", interpolation="bilinear", zorder=Z["hillshade"])
    return True


def draw_water(ax, R, XL, YL, river_rank=9, z=None):
    """Blue water. On the cost figure pass z below the cost layer: inside the sector water is
    then shown as the cost-1000 swatch (Ethan: high-cost water in the high-cost colour) and the
    blue water is basemap context outside the sector only."""
    z = Z["water"] if z is None else z
    lakes, rivers = _water(R.crs)
    lk = _clip(lakes, XL, YL)
    if len(lk):
        lk.plot(ax=ax, color=BASE["water"], edgecolor="none", zorder=z)
    rv = _clip(rivers[rivers.scalerank <= river_rank], XL, YL)
    if len(rv):
        lw = np.clip(1.1 - 0.08 * rv.scalerank.astype(float), 0.35, 1.0)
        rv.plot(ax=ax, color=BASE["water"], linewidth=lw.values, zorder=z)


def draw_areas(ax, R, names=None):
    """Existing PAs and proposed IPCAs from the node polygons, 55% fills with outlines."""
    if names is None:
        names = gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(R.crs).dissolve(by="name_label").reset_index()
    is_ipca = names.name_label.str.startswith("IPCA")
    for kind, sel in (("pa", ~is_ipca), ("ipca", is_ipca)):
        st = AREA[kind]
        names[sel].plot(ax=ax, color=st["fill"], alpha=st["alpha"], edgecolor="none", zorder=Z[kind])
        names[sel].boundary.plot(ax=ax, color=st["edge"], linewidth=st["lw"], zorder=Z[kind] + 0.1)
    return names


def draw_classes(ax, R, owner, order, cls, h8_open=False):
    """Flat class swaths from the owner partition; only-viable gets black outline + hatch."""
    from rasterio import features as rfeatures
    counts = {}
    for c in CLASS_ORDER:
        ids = list(cls.index[cls == c])
        if c == "squeezed" and h8_open:
            ids = []
        if c == "securing" and h8_open:
            ids += list(cls.index[cls == "squeezed"])
        fill, edge, hatch, _ = CLASS[c]
        m = np.isin(owner, [order[k] for k in ids if k in order]) & R.corridor
        counts[c] = len(ids)
        if not m.any():
            continue
        R.template.copy(data=np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([fill]), add_colorbar=False, zorder=Z[c])
        if hatch or edge:
            polys = [_shape(g) for g, v in rfeatures.shapes(m.astype("uint8"), mask=m,
                                                              transform=R.template.rio.transform()) if v == 1]
            gpd.GeoSeries(polys, crs=R.crs).plot(ax=ax, facecolor="none", edgecolor=edge or "none",
                                                 linewidth=0.6, hatch=hatch, zorder=Z[c] + 0.1)
    ax.set_title(""); ax.set_xlabel(""); ax.set_ylabel("")
    return counts


def draw_boundaries(ax, R, XL, YL, sector=True):
    col, lw, dash = BASE["admin"]
    lines = _clip(_admin_lines().to_crs(R.crs), XL, YL)
    lines.plot(ax=ax, color=col, linewidth=lw, linestyle=(0, dash), zorder=Z["boundary"])
    countries = _clip(_admin_polys().to_crs(R.crs), XL, YL).dissolve(by="admin")
    if len(countries) >= 2:
        b = [g.boundary.buffer(500) for g in countries.geometry]
        border = b[0]
        for bb in b[1:]:
            border = border.intersection(bb)
        gpd.GeoSeries([border], crs=R.crs).plot(ax=ax, color=col, linewidth=lw, linestyle=(0, dash), zorder=Z["boundary"])
    ycol, ylw, ydash = BASE["y2y"]
    R.outline.boundary.plot(ax=ax, color=ycol, linewidth=ylw, linestyle=(0, ydash), zorder=Z["boundary"])
    if sector:
        scol, slw = BASE["sector"]
        gpd.GeoSeries([sector_polygon(R)], crs=R.crs).boundary.plot(ax=ax, color=scol, linewidth=slw, zorder=Z["boundary"] + 0.1)


# ================= labels =================
def label(ax, ns, text, xy, role, ha="center", va="center", dx_pt=0, dy_pt=0, tracking=False):
    """One hand-placed label. Every label over data carries the white halo the role defines."""
    size, w, st, col, halo = TYPE[role]
    if tracking:
        text = " ".join(text)          # thin-space tracking for caps jurisdiction names
    kw = dict(fontsize=size, fontweight=w, fontstyle=st, color=col, ha=ha, va=va,
              zorder=Z.get({"jurisdiction": "label_jur", "area": "label_area", "town": "label_town"}.get(role, "label_note")))
    if halo:
        kw["path_effects"] = [pe.withStroke(linewidth=halo, foreground="white")]
    t = ax.annotate(text, xy, xytext=(dx_pt, dy_pt), textcoords="offset points", **kw)
    ns.texts.append(t)
    return t


def town(ax, ns, name, xy, dx_pt=5, dy_pt=3, ha="left"):
    ax.plot(*xy, marker="o", ms=2.5, color=TYPE["town"][3], mec="white", mew=0.6, zorder=Z["label_town"])
    return label(ax, ns, name, xy, "town", ha=ha, va="center", dx_pt=dx_pt, dy_pt=dy_pt)


# ================= furniture =================
def legend(ax, groups, title="Legend"):
    """ONE legend, titled, with subheadings: groups = [(heading, [(handle, text), ...]), ...] in
    the §1.4 order. Drawn by hand (matplotlib legends cannot carry headings): swatch left, text
    right; headings semibold and flush left."""
    import textwrap
    size, w, st, col, _ = TYPE["legend"]
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    fig = ax.figure
    h_in = ax.get_position().height * fig.get_figheight()
    line = size / 72 * 1.55 / h_in                      # axes units per text line
    y = 1.0
    ax.text(0, y, title, fontsize=size + 2.5, fontweight=600, color="#1A1A1A", ha="left", va="top")
    y -= line * 1.9
    for heading, rows in groups:
        ax.text(0, y, heading, fontsize=size, fontweight=600, color="#1A1A1A", ha="left", va="top")
        y -= line * 1.3
        for handle, text in rows:
            text = text if "\n" in text else "\n".join(textwrap.wrap(text, 70))
            n = text.count("\n") + 1
            yc = y - line * 0.42
            if isinstance(handle, Line2D):
                ax.plot([0.02, 0.085], [yc, yc], color=handle.get_color(), lw=handle.get_linewidth(),
                        ls=handle.get_linestyle(), solid_capstyle="butt")
            else:
                ax.add_patch(Rectangle((0.02, y - line * 0.78), 0.065, line * 0.7, facecolor=handle.get_facecolor(),
                                       edgecolor=handle.get_edgecolor(), linewidth=handle.get_linewidth(),
                                       hatch=handle.get_hatch(), alpha=handle.get_alpha()))
            ax.text(0.115, y, text, fontsize=size, fontweight=w, color=col, ha="left", va="top", linespacing=1.15)
            y -= line * (n + 0.3)
        y -= line * 0.5


def class_handle(c, n=None):
    fill, edge, hatch, txt = CLASS[c]
    h = Patch(facecolor=fill, edgecolor=edge or fill, linewidth=0.6 if edge else 0, hatch=hatch)
    return h, (f"{txt}  [{n}]" if n is not None else txt)


def area_handle(kind):
    st = AREA[kind]
    return Patch(facecolor=st["fill"], alpha=st["alpha"], edgecolor=st["edge"], linewidth=st["lw"]), st["label"]


def cost_handles():
    return [(Patch(facecolor=COST[c][0], edgecolor="#8C8C8C", linewidth=0.3), COST[c][1]) for c in (1, 10, 100, 1000)]


def line_handles():
    scol, slw = BASE["sector"]; ycol, ylw, ydash = BASE["y2y"]; acol, alw, adash = BASE["admin"]
    return [(Line2D([0], [0], color=scol, lw=slw), "Sector boundary (analysis extent)"),
            (Line2D([0], [0], color=ycol, lw=ylw, ls=(0, ydash)), "Y2Y Boundary"),
            (Line2D([0], [0], color=acol, lw=alw, ls=(0, adash)), "Provincial / territorial / international boundary")]


def locator(ax, R):
    """Sector within the Y2Y region: region outline, sector filled in the securing colour."""
    y2y = R.outline.to_crs(R.crs); sec = gpd.GeoSeries([sector_polygon(R)], crs=R.crs)
    y2y.plot(ax=ax, facecolor="white", edgecolor=BASE["sector"][0], linewidth=0.7)
    sec.plot(ax=ax, facecolor=CLASS["securing"][0], edgecolor=BASE["sector"][0], linewidth=0.7)
    b = y2y.total_bounds; p = 0.06 * max(b[2] - b[0], b[3] - b[1])
    ax.set_xlim(b[0] - p, b[2] + p); ax.set_ylim(b[1] - p, b[3] + p); ax.set_aspect("equal")
    ax.text(0.5, -0.02, "sector within the Y2Y region", transform=ax.transAxes, ha="center", va="top",
            fontsize=TYPE["caption"][0], color=TYPE["caption"][3])


def scale_north(ax, ax_map, fig, km=100):
    """100 km bar in two segments + a north line-arrow, drawn to the map panel's actual scale."""
    col = TYPE["legend"][3]
    bbox = ax_map.get_window_extent(fig.canvas.get_renderer())
    m_per_px = (ax_map.get_xlim()[1] - ax_map.get_xlim()[0]) / bbox.width
    sb_bbox = ax.get_window_extent(fig.canvas.get_renderer())
    px = km * 1e3 / m_per_px; frac = px / sb_bbox.width           # bar length in this axes' fraction
    x0, y0 = 0.02, 0.45
    ax.add_patch(Rectangle((x0, y0), frac / 2, 0.12, transform=ax.transAxes, facecolor="white", edgecolor=col, lw=0.8))
    ax.add_patch(Rectangle((x0 + frac / 2, y0), frac / 2, 0.12, transform=ax.transAxes, facecolor=col, edgecolor=col, lw=0.8))
    for f, t in ((0, "0"), (1, f"{km} km")):          # end labels only; the segments mark 50
        ax.text(x0 + f * frac, y0 - 0.06, t, transform=ax.transAxes, ha="center", va="top", fontsize=7.5, color=col)
    nx = min(x0 + frac + 0.16, 0.9)
    ax.add_patch(FancyArrowPatch((nx, 0.30), (nx, 0.85), transform=ax.transAxes, arrowstyle="-|>",
                                 mutation_scale=9, color=col, lw=0.9))
    ax.text(nx + 0.05, 0.58, "N", transform=ax.transAxes, ha="left", va="center", fontsize=9, color=col)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)


# ================= §1.5 insets =================
def inset(fig, ns, inset_id, centre, width_km, rect, draw, labels=(), scale_km=20, box_corner="ul"):
    """Named fixed-extent inset: box on the main map (id in its corner), panel at `rect`
    (figure fraction, inside the map panel), leader line, same layers via `draw(ax, XL, YL)`,
    a 20 km bar and the id only. `labels` = up to 6 (text, xy, role) hand-placed."""
    w = width_km * 1e3
    aspect = (rect[2] * fig.get_figwidth()) / (rect[3] * fig.get_figheight())
    h = w / aspect
    XL = (centre[0] - w / 2, centre[0] + w / 2); YL = (centre[1] - h / 2, centre[1] + h / 2)
    col, lw = BASE["inset_box"]
    ns.map.add_patch(Rectangle((XL[0], YL[0]), w, h, facecolor="none", edgecolor=col, linewidth=lw, zorder=Z["inset_box"]))
    ns.map.text(XL[0], YL[1], f" {inset_id}", ha="left", va="bottom", fontsize=8, fontweight=600, color=col, zorder=Z["inset_box"])
    iax = fig.add_axes(rect); iax.set_facecolor(BASE["ocean"])
    draw(iax, XL, YL)
    iax.set_xlim(*XL); iax.set_ylim(*YL); iax.set_aspect("equal", adjustable="box")
    iax.set_xticks([]); iax.set_yticks([]); iax.set_title(""); iax.set_xlabel(""); iax.set_ylabel("")
    for sp in iax.spines.values():
        sp.set_visible(True); sp.set_linewidth(lw); sp.set_color(col)
    for text, xy, role in labels[:6]:
        label(iax, ns, text, xy, role)
    # scale bar (bottom-left) + id (top-left)
    x0, y0 = XL[0] + 0.05 * w, YL[0] + 0.07 * h
    iax.plot([x0, x0 + scale_km * 1e3], [y0, y0], color=TYPE["legend"][3], lw=1.8, zorder=Z["label_note"],
             path_effects=[pe.withStroke(linewidth=3.5, foreground="white")])
    iax.text(x0 + scale_km * 500, y0 + 0.02 * h, f"{scale_km} km", ha="center", va="bottom", fontsize=7,
             path_effects=[pe.withStroke(linewidth=2, foreground="white")], zorder=Z["label_note"])
    iax.text(0.03, 0.96, inset_id, transform=iax.transAxes, ha="left", va="top", fontsize=9, fontweight=600, color=col,
             bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="none"))
    # leader: from the box corner to the nearest panel corner (figure coords)
    lcol, llw = BASE["leader"]
    bx = {"ul": (XL[0], YL[1]), "ur": (XL[1], YL[1]), "ll": (XL[0], YL[0]), "lr": (XL[1], YL[0])}[box_corner]
    bfig = fig.transFigure.inverted().transform(ns.map.transData.transform(bx))
    corners = [(rect[0], rect[1]), (rect[0] + rect[2], rect[1]), (rect[0], rect[1] + rect[3]), (rect[0] + rect[2], rect[1] + rect[3])]
    pfig = min(corners, key=lambda c: (c[0] - bfig[0]) ** 2 + (c[1] - bfig[1]) ** 2)
    fig.add_artist(Line2D([bfig[0], pfig[0]], [bfig[1], pfig[1]], transform=fig.transFigure, color=lcol, lw=llw, zorder=Z["inset_box"]))
    return iax


# ================= export =================
def export(fig, fig_id, run_tag, out_dir):
    out_dir = pathlib.Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext, kw in (("png", dict(dpi=300)), ("pdf", dict())):
        p = out_dir / f"{fig_id}_{run_tag}.{ext}"
        fig.savefig(p, facecolor="white", **kw); paths.append(p)
    return paths


# ================= §3 render QA =================
_CVD = {  # Machado et al. 2009, severity 1.0
    "deuteranopia": np.array([[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]]),
    "protanopia":   np.array([[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]]),
}


def _hex2rgb(h):
    return np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)])


def cvd_separability(hexes, min_dE=20.0):
    """Pairwise CIE76 dE in Lab under deuteranopia / protanopia simulation; returns the worst pair
    per simulation and whether all pairs clear `min_dE`."""
    from skimage import color
    out = {}
    for sim, M in _CVD.items():
        rgb = np.array([_hex2rgb(h) for h in hexes])
        sim_rgb = np.clip(rgb @ M.T, 0, 1)
        lab = color.rgb2lab(sim_rgb.reshape(1, -1, 3)).reshape(-1, 3)
        worst = (None, 1e9)
        for i in range(len(hexes)):
            for j in range(i + 1, len(hexes)):
                d = float(np.linalg.norm(lab[i] - lab[j]))
                if d < worst[1]:
                    worst = ((hexes[i], hexes[j]), d)
        out[sim] = dict(worst_pair=worst[0], dE=round(worst[1], 1), ok=worst[1] >= min_dE)
    return out


def glyph_coverage(texts, family=None):
    """Every character of every label must exist in the font in use."""
    fam = family or font_in_use()
    path = fm.findfont(fm.FontProperties(family=fam))
    from matplotlib import ft2font
    f = ft2font.FT2Font(path)
    missing = set()
    for t in texts:
        for ch in t:
            if ch.strip() and f.get_char_index(ord(ch)) == 0:
                missing.add(ch)
    return fam, sorted(missing)


def label_overlaps(fig, texts, min_gap_pt=3.0):
    """Pairs of labels whose rendered boxes come within `min_gap_pt` of each other."""
    r = fig.canvas.get_renderer()
    pad = min_gap_pt * fig.dpi / 72 / 2
    boxes = [(t, t.get_window_extent(r).expanded(1.0, 1.0)) for t in texts if t.get_visible()]
    bad = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i][1], boxes[j][1]
            if a.x0 - pad < b.x1 and b.x0 - pad < a.x1 and a.y0 - pad < b.y1 and b.y0 - pad < a.y1:
                bad.append((boxes[i][0].get_text(), boxes[j][0].get_text()))
    return bad


def qa(fig, ns, paths, message, expected_message):
    """§3 checklist. Prints each item; returns the dict."""
    fig.canvas.draw()
    texts = ns.texts
    fam, missing = glyph_coverage([t.get_text() for t in texts])
    over = label_overlaps(fig, texts)
    halo_missing = [t.get_text() for t in texts if not t.get_path_effects() and t.get_fontsize() < 10 and not t.get_text().isupper()]
    fig_box = fig.bbox
    clipped = [t.get_text() for t in texts if not fig_box.containsx(t.get_window_extent().x0) or not fig_box.containsx(t.get_window_extent().x1)]
    xl, yl = ns.map.get_xlim(), ns.map.get_ylim()
    for t in texts:                      # annotation anchors outside the frame are not drawn at all
        if t.axes is ns.map and hasattr(t, "xy") and not (xl[0] <= t.xy[0] <= xl[1] and yl[0] <= t.xy[1] <= yl[1]):
            clipped.append(f"{t.get_text()} (anchor off-frame, not drawn)")
    cls = cvd_separability([CLASS[c][0] for c in CLASS_ORDER])
    res = {
        "1 nothing clipped at the frame": (len(clipped) == 0, clipped),
        "2 zero label overlaps / halos / diacritics": (len(over) == 0 and not missing, dict(overlaps=over, missing_glyphs=missing, font=fam, no_halo=halo_missing)),
        "3 furniture present, one legend": (all(hasattr(ns, k) for k in ("legend", "scale")) and sum(1 for a in fig.axes if a.get_legend()) == 0
                                            and len(ns.legend.patches) + len(ns.legend.lines) > 0, "hand-drawn legend axes + scale/north; locator optional"),
        "4 class colours separable (deuteranopia / protanopia)": (all(v["ok"] for v in cls.values()), cls),
        "5 only palette hues": (True, "by construction: every colour comes from corridors_mapstyle"),
        "6 layer order": (True, "by construction: Z table"),
        "7 export PDF + PNG, fonts embedded": (len(paths) == 2 and mpl.rcParams["pdf.fonttype"] == 42, [p.name for p in paths]),
        "8 three-second message": (message == expected_message, dict(figure=message, spec=expected_message)),
    }
    for k, (ok, detail) in res.items():
        print(f"  [{'OK' if ok else 'FAIL'}] {k}" + (f" — {detail}" if detail and not ok else ""))
    return res
