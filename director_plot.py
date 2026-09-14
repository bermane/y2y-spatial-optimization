"""director_plot -- the director package's shared plotting state and helpers (split out of 20_figures on 2026-09-14
so that 20 (every output, the record) and 21_director_outputs (the curated few for the presentation) draw from ONE
codebase). `C = load()` reads the products 19 wrote (surfaces, tiers, clusters, tables) and returns a namespace whose
drawing helpers are closed over that state; a notebook can `globals().update(vars(C))` to use the bare names
(draw_pa, draw_hex, finish, ...) exactly as 20 always has. Cartography is pixel space (1 px = 1 km)."""
import json
import textwrap
from types import SimpleNamespace

import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd
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


def load(pkg=None, allow_partial=False):
    """Load the package products written by 19 and build the drawing helpers over them."""
    PKG = pkg or (dc.PKG / "_smoke" if allow_partial else dc.PKG)
    GEO, TAB, FIGD = PKG / "geotiffs", PKG / "tables", PKG / "figures"
    assert (PKG / "summary.json").exists(), "run 19_tiers_and_clusters first"
    S = json.loads((PKG / "summary.json").read_text())
    G = dc.grid()
    MAN = dc.package_manifest(pd.read_csv(dc.MANIFEST))
    assert S.get("version", "v2") == dc.VP.version, f"summary.json is from {S.get('version', 'v2')}, VERSION is {dc.VP.version} -- re-run 19"

    def rd(name):
        with rasterio.open(GEO / name) as src:
            return src.read(1)[G.pu]
    Fg, Fp, Ug = rd("F_guarded.tif"), rd("F_unguarded.tif"), rd("union_membership_guarded.tif")
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
    E17 = pd.read_csv(TAB / "E17_shifts.csv")
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
    IP = dc.ipca_layer(G)
    BM = dc.basemap_layer(G); HS = dc.read_hillshade(G); PAN = dc.pa_layer(G, 300)                 # the northern package's basemap on this frame (display only)
    HEX = {dc.HEX_KM2: dc.hex_grid(G, dc.HEX_KM2)}
    ADMIN = dc.admin_layer(G)

    halo = [pe.withStroke(linewidth=2.5, foreground="white")]
    # ramp purple -> green for F < 0.70 (viridis truncated before its own yellow): the CORE (>= 0.70) is the only
    # yellow on the map and reads as a category, not the top of the gradient; F = 0 falls under -> NEVER_COLOR
    FCMAP = ListedColormap(plt.get_cmap("viridis")(np.linspace(0, 0.70, 256))); FCMAP.set_over("#ffd93b"); FCMAP.set_under(NEVER_COLOR)
    FNORM = Normalize(1e-9, dc.FREQ_THR)
    N_NOTE = (f"n = {S['n_formulations']} formulations × 51 near-optimal plans · no value theme left more than {100 * S['floor_g']:.0f}% behind")
    PAg = np.full(G.shape, np.nan, np.float32); PAg[G.locked2d] = 1.0

    def rings_px(geom):
        polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        out = []
        for p in polys:
            x, y = np.asarray(p.exterior.coords)[:, :2].T      # some proposals carry a Z coordinate
            px, py = dc.xy_to_px(G, x, y)
            out.append(np.c_[px, py])
        return out

    def draw_pa(ax):
        ax.imshow(PAg, cmap=ListedColormap([PA_COLOR]), interpolation="nearest", zorder=1)

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
            if int(r.cid) in numbers and numbers[int(r.cid)][1]:
                c = r.geometry.centroid
                cx, cy = dc.xy_to_px(G, c.x, c.y)
                ax.annotate(numbers[int(r.cid)][0], xy=(cx, cy), xytext=(cx + 30, cy - 30), fontsize=fs, fontweight=600, clip_on=True,
                            color=col, path_effects=halo, zorder=6, arrowprops=dict(arrowstyle="-", color=col, lw=0.6))

    def draw_ipca(ax, lw=1.3):
        for _, r in IP.gdf.iterrows():
            for ring in rings_px(r.geometry):
                ax.plot(ring[:, 0], ring[:, 1], color=IPCA_COLOR, lw=lw, ls="-", zorder=3.5)

    def finish(ax, title, handles, note=N_NOTE, legend_loc="upper right", scale=True, names=None, towns=None, name_fs=None):
        dc.draw_basemap(ax, G, BM, hs=HS if STYLE["hillshade"] else None, water=STYLE["water"],
                        names=STYLE["province_names"] if names is None else names, towns=STYLE["towns"] if towns is None else towns,
                        name_fs=name_fs, fs_scale=STYLE.get("_fs_scale", 1.0), avoid_sw=scale)   # ocean / land / hillshade / water / outline / names
        dc.draw_admin(ax, G, ADMIN)                                   # coast, admin lines, border
        if STYLE["lat53"]:
            dc.graticule(ax, G, lats=(53,), lons=(), emph_lat=53)     # the 53°N line (E17 tie-in) -- off by default (Ethan 2026-09-14)
        ax.set_xlim(0, G.shape[1]); ax.set_ylim(G.shape[0], 0)
        if scale:                                                     # scale bar + north arrow, south-west corner (ocean)
            dc.scalebar(ax, G, loc=(0.05, 0.04), fs=STYLE["legend_fs"] - 1); dc.north_arrow(ax, G, loc=(0.075, 0.075), fs=STYLE["legend_fs"] - 1)
        dc.corner_note(ax, note)
        ax.set_title(title, fontsize=11.5)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
        lkw = dict(fontsize=STYLE["legend_fs"], frameon=True, framealpha=0.92, edgecolor="#9a9a9a")
        if legend_loc == "none" or not handles:
            pass
        elif handles and legend_loc == "outside":       # beside the frame, top right (the single-panel assets)
            ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0), **lkw)
        elif handles and legend_loc == "lower left":    # south-west corner above the scale bar: for maps whose NE corner is full
            ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, 0.12), **lkw)
        elif handles:                                    # north-east corner inside the frame (the paired record figures)
            ax.legend(handles=handles, loc="upper right", bbox_to_anchor=(1.0, 1.0), **lkw)

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

    IPCA_HANDLE = Patch(facecolor="none", edgecolor=IPCA_COLOR, label="IPCA proposals (not locked in)")
    BASE_HANDLES = [Patch(facecolor=PA_COLOR, label="Protected areas (locked in)"),
                    Patch(facecolor="none", edgecolor=CL_COLOR, label="numbered = deck picks")]      # ("never selected" dropped, Ethan 2026-09-14)

    def star_rows(rows, color):
        """One star per pick; a cluster with its own colour in STYLE["cluster_colors"] keeps it here (map ↔ stars ↔ numbers)."""
        return [dict(title=f"Cluster {int(r.number)}\n{r.area_km2:,.0f} km² · mean F {r.mean_guarded_F:.2f}"
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
    fig.savefig(path, dpi=200, bbox_inches="tight"); plt.show()


# ---- the values table (Laura's objectives hierarchy; biodiversity as its own sub-objective) -------------------------
def values_rows(C):
    sc = json.loads((dc.SPEC / "scenarios_v2.json").read_text()); t0 = sc["S0_balanced"]["targets"]; t4 = sc["S4_carbon"]["targets"]
    efg_t = json.loads((dc.SPEC_REC / "efg_targets.json").read_text())["targets"] if (dc.SPEC_REC / "efg_targets.json").exists() else {}
    pa_pct = C.S["protected_baseline"]["pa_pct_of_region"]; MS = "irrecoverable_carbon_m_soc"
    return [
     ("PROTECT — wildlife have sufficient core habitat", "Quantity of core habitat", "Protected land: today's protected areas are locked in and every plan protects 30% of Y2Y",
      "Y2Y protected areas 2025 (IUCN definitions)", f"The budget: 30% of the region, including the {pa_pct:.0f}% already protected"),
     ("", "Quality of core habitat", "Climate refugia: refugial residence time (1 / backward climate velocity), 2071–2100, two emission futures",
      "AdaptWest 2023, CMIP6 backward climate velocity (8-GCM ensemble)", "Core-habitat theme: 25% of the objective in the balanced position; the two futures (SSP2-4.5, SSP5-8.5) are separate value positions"),
     ("", "Quality of core habitat", "Naturalness: 1 − human modification", "Theobald et al., global human modification (gHM v3)",
      "In every formulation at its baseline weight; it cannot move the answer — disclosed, not a driver"),
     ("", "Biodiversity", "Mammal richness (species per km², area-of-habitat maps, all species)", "Lumbierres et al., AOH species richness (mammals)",
      "Biodiversity theme: 25% (balanced); the two layers weighted equally"),
     ("", "Biodiversity", "Bird richness (species per km², area-of-habitat maps, all species)", "Lumbierres et al., AOH species richness (birds)", ""),
     ("", "Representativeness", f"Presence of {dc.N_EFG} ecosystem functional groups (curated from 40 under the input pre-screen, rule R0)",
      "IUCN Global Ecosystem Typology, indicative maps (Keith et al. 2022)",
      (f"A representation floor, not a weighted theme: rarity-scaled targets of {100*min(efg_t.values()):.0f}–{100*max(efg_t.values()):.0f}% per class, rarity judged in the region + 250 km"
       if efg_t else "A representation floor, not a weighted theme")),
     ("CONNECT — wildlife corridors connect core habitats", "Quality of connectivity", "Climate corridors: current-flow centrality", "Carroll et al. 2018",
      "Connectivity theme: 25% (balanced); the two layers weighted equally"),
     ("", "Quality of connectivity", "Habitat connectivity: transboundary omnidirectional current density", "Pither et al. 2023 / O'Brien et al. (transboundary extension)", ""),
     ("ADDRESS CLIMATE CHANGE — keep carbon out of the air", "Carbon", "Irrecoverable carbon in biomass", "Berman & McDowell, irrecoverable carbon",
      "Carbon theme: 25% (balanced); the two pools split 74 / 26 by mass"),
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
    fig.savefig(path, dpi=200, bbox_inches="tight"); plt.show()

# ---- ONE place for the presentation knobs (Ethan iterates in 21; a change here reaches 20 and 21 alike) -------------
STYLE = dict(
    cluster_number_fs=13,      # size of the cluster numbers on maps
    cluster_lw=0.9,            # cluster outline width on the Y2Y-wide maps (insets: × cluster_lw_inset_scale)
    cluster_lw_inset_scale=2.5, cluster_halo=True, draw_unpicked=False,           # core complexes that are not deck picks: not outlined
    cluster_colors={1: "#D7263D", 2: "#E040A0", 3: "#1E90FF", 4: "#8B5A2B"},   # the core clusters, N → S: red, magenta, blue, brown (Ethan 2026-09-14)
    core_color="#2b4f7d",      # star fill/line for core clusters
    scenario_color="#a50f2d",  # star fill/line for scenario clusters
    star_fs_axis=17, star_fs_title=20, star_fs_tick=13, star_fs_suptitle=15, star_lw=2.6, star_title=False, star_footnote=False,   # Ethan 2026-09-14: no suptitle / footnote, big type
    map_title_fs=11.5, map_suptitle_fs=12.5,
    ramp_label="F = frequency in near-optimal plans; light grey = never (F = 0), yellow = core (F ≥ 0.70)",
    ramp_label_short="F = frequency in 30×30 plans", cbar_fs=12,          # the wide Act 1 maps
    values_table="spec",      # the objectives-table rendering: "spec" (the table spec, 2026-09-14) | "poster" | "digest" | "plain"
    conseq_cmap="RdYlGn", conseq_tint=0.55, conseq_scale_rows="all",   # consequences: red -> green per column, over "all" rows or "clusters" only
    legend_fs=13,              # map legends (bigger, outside the region)
    lat53=False,               # the 53°N graticule line on maps
    map_layout="wide",         # Act 1 maps: "wide" = slide-shaped with two zoom insets (clusters 1 and 2) | "tall" = the map alone
    inset_clusters=(1, 2), inset_pad_km=45, inset_min_km=320, inset_pa_names=5, inset_fs=11.5, inset_number_fs=18,
    wide_main_names="abbrev", wide_main_name_fs=15, wide_main_towns=(),      # the Y2Y-wide panel of the wide layout: postal codes only, big
    hillshade=True, water=True, province_names=True,                     # the basemap (corridors_mapstyle tokens, display only)
    towns=("Dawson City", "Whitehorse", "Watson Lake", "Fort Nelson", "Fort St. John", "Prince George", "Smithers", "Jasper",
           "Edmonton", "Calgary", "Banff", "Kamloops", "Cranbrook", "Missoula", "Helena", "Bozeman", "Boise", "Jackson", "Norman Wells"),
)

# ---- the shared assets: 20 (the record) and 21 (the presentation) call THESE, never their own copies -----------------
def values_table(C, path, title="Y2Y Objectives Hierarchy"):
    """THE objectives-table asset. Writes T-D0_values.csv (the rows) and renders in STYLE["values_table"]:
    "poster" = the Carbon-Poster spec (chosen by Ethan 2026-09-14 from the two iterations), "digest" = the Threat-Digest
    spec, "plain" = the original matplotlib table (superseded, kept)."""
    rows = values_rows(C)
    pd.DataFrame(rows, columns=VALUES_COLUMNS).to_csv(C.TAB / "T-D0_values.csv", index=False)
    fn = {"spec": values_table_spec, "poster": values_table_poster, "digest": values_table_digest, "plain": values_table_plain}[STYLE["values_table"]]
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
        C.finish(ax, "(a) mean F per ~250 km² hex over unprotected land, with declared IPCA proposals" if panel == "a"
                 else "(b) with the core clusters (F ≥ 0.70 at 1 km); numbered north → south",
                 C.BASE_HANDLES if panel == "b" else C.BASE_HANDLES[:2] + [C.IPCA_HANDLE], note=C.N_NOTE if panel == "b" else "")
    cax = fig.add_axes([0.30, 0.055, 0.40, 0.014])
    fig.colorbar(ScalarMappable(norm=C.FNORM, cmap=C.FCMAP), cax=cax, orientation="horizontal", extend="both", label=STYLE["ramp_label"])
    fig.suptitle(title or (f"Act 1 — these areas recur in near-optimal plans no matter whose values prevail\n"
                           f"core = {core_km2:,} km² of unprotected land, no value theme left more than 5% behind"), fontsize=STYLE["map_suptitle_fs"], y=0.985)
    fig.savefig(path, dpi=180, bbox_inches="tight"); plt.show()


def _stars(C, rows, color, path, title):
    with plt.rc_context(SPEC_RC):
        dc.plot_star_grid(C.star_rows(rows, color), path, title if STYLE["star_title"] else None,
                          fs_axis=STYLE["star_fs_axis"], fs_title=STYLE["star_fs_title"], fs_tick=STYLE["star_fs_tick"],
                          fs_suptitle=STYLE["star_fs_suptitle"], lw=STYLE["star_lw"], footnote=STYLE["star_footnote"])
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
    sc = json.loads((dc.SPEC / "scenarios_v2.json").read_text()); t0 = sc["S0_balanced"]["targets"]; t4 = sc["S4_carbon"]["targets"]
    MS = "irrecoverable_carbon_m_soc"
    efg_t = json.loads((dc.SPEC_REC / "efg_targets.json").read_text())["targets"] if (dc.SPEC_REC / "efg_targets.json").exists() else {}
    tgt = f"targets {100*min(efg_t.values()):.0f}–{100*max(efg_t.values()):.0f}% per class" if efg_t else "representation floor"
    return ["30% of the region", "25% of the objective", "baseline weight · not a driver", "12.5% of the objective", "12.5% of the objective",
            tgt, "12.5% of the objective", "12.5% of the objective", f"{100*0.25*0.258:.1f}% of the objective",
            f"{100*0.25*0.742:.1f}% · target {100*t0[MS]:.0f}% ({100*t4[MS]:.0f}%)", "—"]


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
    fig.savefig(path, dpi=200, facecolor=BG); plt.show()


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
    fig.savefig(path, dpi=200, facecolor=BG); plt.show()


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
                   fills=None, col_w=None, stub_w=None, stub_head="", base_px=None, dpi=200, stub_sep=False):
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
    fig.savefig(path, dpi=dpi, facecolor=T["bg"]); plt.show()


SOURCE_NOTE = "Y2Y spatial decision tool, frequency ensemble on manifest v3.1 (in review)."

# maps and star plots share the spec's type: Cronos Pro, weights 400/600, ink titles, cap text, mut fine print
SPEC_RC = {"font.family": TABLE_FONT, "font.weight": 400, "text.color": TABLE["cap"], "axes.titlecolor": TABLE["ink"],
           "axes.titleweight": 600, "figure.titleweight": 600, "axes.labelcolor": TABLE["cap"], "xtick.color": TABLE["cap"],
           "ytick.color": TABLE["cap"], "legend.labelcolor": TABLE["cap"], "axes.edgecolor": TABLE["cap"]}


def consequences_table(C, rows, path, label, title):
    """The consequences table to the spec, TRANSPOSED: one row per measure (area, mean F, the six value ratios), one column
    per cluster, then the two reference columns (existing protected areas; the proposed IPCAs' unprotected part). Ratio rows
    are tinted red → green across the row (STYLE['conseq_*']); clusters group by leading scenario where they differ."""
    ref = C.TD7[C.TD7.act.eq("reference")]
    body = pd.concat([rows, ref], ignore_index=True)
    nclu = len(rows)
    cols = [f"Cluster {int(n)}" for n in rows.number] + ["Existing\nprotected areas", "Proposed IPCAs\n(unprotected)"]
    if "driving_label" in rows and rows.driving_label.nunique() > 1:
        groups, j0 = [], 0
        for k, (lab, grp) in enumerate(rows.groupby("driving_label", sort=False)):
            groups.append((lab, j0, j0 + len(grp) - 1)); j0 += len(grp)
    else:
        groups = [("Core clusters", 0, nclu - 1)]
    groups.append(("Reference", nclu, nclu + 1))
    stub = ["Area (km²)"] + [a[0].upper() + a[1:] for a in dc.STAR_AXES]
    cells = [[f"{v:,.0f}" for v in body.area_km2]]
    cells += [[ratio_fmt(v) for v in body[f"ratio_{a}"]] for a in dc.STAR_AXES]
    numeric = [[True] * len(cols) for _ in stub]
    # fills: per ratio row, red -> green on log ratio, min -> max over the columns in scope, blended toward the mat
    cmap = plt.get_cmap(STYLE["conseq_cmap"]); tint = STYLE["conseq_tint"]; mat = np.array(matplotlib.colors.to_rgb(TABLE["mat"]))
    scope = np.arange(len(body)) if STYLE["conseq_scale_rows"] == "all" else np.arange(nclu)
    fills = [[None] * len(cols) for _ in stub]
    for r, a in enumerate(dc.STAR_AXES, start=1):
        x = np.log(body[f"ratio_{a}"].astype(float).values); lo, hi = np.nanmin(x[scope]), np.nanmax(x[scope])
        for j, v in enumerate(x):                      # 1.0× (log 0) = the inflection; reds scale to the row min, greens to the row max
            t = 0.5 + 0.5 * (v / hi if v > 0 and hi > 0 else (-v / lo if v < 0 and lo < 0 else 0.0))
            fills[r][j] = tuple(mat * (1 - tint) + np.array(cmap(float(np.clip(t, 0, 1)))[:3]) * tint)
    spec_table_png(path, stub, cols, cells, label=label, title=title, groups=groups, numeric=numeric, fills=fills,
                   units="Ratios: mean value inside the area ÷ mean over allocatable (unprotected) land · 1.0× = the average allocatable cell",
                   notes=[("Note", "Blocks combine their layers with the block weights (carbon 74 / 26 by mass); representativeness = ecosystem "
                                   "classes present per cell; naturalness = 1 − human modification. Colour runs red → green across each row, "
                                   "with 1.0× as the hinge and each side scaled to the row's own extreme."),
                          ("Source", SOURCE_NOTE)])


def values_table_spec(C, path, title="Y2Y Objectives Hierarchy"):
    """The objectives hierarchy to the table spec: stub = fundamental objective (first row of each group), then the
    sub-objective as a column-head group (heading → accent metric line → measure), the source in fine print, and how the
    layer enters the analysis. One frame separator after the stub; rules between rows; notes below."""
    rows = values_rows(C); metrics = values_metrics(C)
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
                   label="Y2Y SPATIAL DECISION TOOL  ·  PROACT OBJECTIVES", title=title,
                   units="How each objective is measured, and how it enters the optimization",
                   stub_head="Fundamental objective", col_w=col_w, stub_w=stub_w, numeric=numeric, stub_sep=True,
                   notes=[("Note", "Shares are of the objective's influence in the balanced position; each forward position doubles one "
                                   "theme's share. Targets are fractions of the regional total. Naturalness and representativeness enter "
                                   "outside the four weighted themes."),
                          ("Source", SOURCE_NOTE)])


def _f_1km(C):
    return dc.to_grid(C.G, np.where(C.G.disc, C.Fg, np.nan))


def _single_map(C, path, title, draw, handles, cbar_label=None):
    with plt.rc_context(SPEC_RC):
        fig, ax = plt.subplots(figsize=(8.2, 11.5))
        fig.subplots_adjust(left=0.02, right=0.98, top=0.89, bottom=0.085)
        ax.imshow(_f_1km(C), cmap=C.FCMAP, norm=C.FNORM, interpolation="nearest", zorder=0.5)
        C.draw_pa(ax); draw(ax)
        C.finish(ax, "", handles, note="", legend_loc="outside")
        cax = fig.add_axes([0.20, 0.048, 0.60, 0.013])
        cb = fig.colorbar(ScalarMappable(norm=C.FNORM, cmap=C.FCMAP), cax=cax, orientation="horizontal", extend="both")
        cb.set_label("\n".join(textwrap.wrap(cbar_label or STYLE["ramp_label"], 62)), fontsize=9, color=TABLE["mut"])
        fig.suptitle(title, fontsize=STYLE["map_suptitle_fs"], y=0.975, color=TABLE["ink"], fontweight=600)
        fig.savefig(path, dpi=200, bbox_inches="tight"); plt.show()


def _inset_window(C, number, aspect_hw):
    """Pixel window (x0, x1, y_top, y_bottom) around a numbered Act 1 cluster: its members' bounds + pad, at the inset's aspect."""
    p = C.PICKS[(C.PICKS.act == "Act 1") & (C.PICKS.number.astype(str) == str(number))].iloc[0]
    cids = [int(c) for c in str(p.cids).split(";")]
    g = C.CL["act1"]; minx, miny, maxx, maxy = g[g.cid.isin(cids)].geometry.total_bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2; pad = STYLE["inset_pad_km"] * 1000
    w = max(maxx - minx + 2 * pad, STYLE["inset_min_km"] * 1000); h = max(maxy - miny + 2 * pad, STYLE["inset_min_km"] * 1000 * aspect_hw)
    if h / w < aspect_hw: h = w * aspect_hw
    else: w = h / aspect_hw
    px0, pyb = dc.xy_to_px(C.G, cx - w / 2, cy - h / 2); px1, pyt = dc.xy_to_px(C.G, cx + w / 2, cy + h / 2)
    return (float(px0), float(px1), float(pyt), float(pyb)), p


def _draw_inset(C, ax, win, draw, title, with_ipca_names):
    px0, px1, pyt, pyb = win
    ax.imshow(_f_1km(C), cmap=C.FCMAP, norm=C.FNORM, interpolation="nearest", zorder=0.5)
    dc.draw_basemap(ax, C.G, C.BM, hs=None, water=STYLE["water"], names=False, towns=list(dc.Y2Y_TOWNS), window=win, fs_scale=STYLE["inset_fs"] / 8.0)
    hs = dc.read_hillshade_window(C.G, win, scale=3) if STYLE["hillshade"] else None
    if hs is not None:
        rgba = np.zeros(hs.shape + (4,), np.float32); rgba[..., 3] = dc.BASEMAP["hillshade_alpha"] * (1.0 - hs.astype(np.float32) / 255.0)
        ax.imshow(rgba, extent=[px0, px1, pyb, pyt], interpolation="bilinear", zorder=0.6)
    C.draw_pa(ax); draw(ax); dc.draw_admin(ax, C.G, C.ADMIN)
    fs = STYLE["inset_fs"]
    taken = dc.label_areas_px(ax, C.G, C.PAN, "PA_Name", win, top_n=STYLE["inset_pa_names"], color="0.25", fs=fs)
    if with_ipca_names:
        dc.label_areas_px(ax, C.G, C.IP.gdf, "name", win, top_n=3, color="#a04a00", fs=fs, taken=taken)
    ax.set_xlim(px0, px1); ax.set_ylim(pyb, pyt); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(True); sp.set_edgecolor("#333333"); sp.set_linewidth(0.9)
    # 50 km scale bar, south-west corner (1 px = 1 km)
    x, y = px0 + 0.05 * (px1 - px0), pyb - 0.05 * (pyb - pyt)
    ax.plot([x, x + 50], [y, y], color="black", lw=2.5, solid_capstyle="butt", zorder=7)
    ax.text(x + 25, y - 6, "50 km", ha="center", va="bottom", fontsize=STYLE["inset_fs"], zorder=7)
    ax.set_title(title, fontsize=STYLE["map_title_fs"] + 2, color=TABLE["ink"], fontweight=600, pad=6, loc="left")


def _wide_map(C, path, title, draw, handles, cbar_label=None, with_ipca_names=False):
    """Slide-shaped Act 1 map: the frame at left, zoom insets around STYLE['inset_clusters'] at right, legend + ramp below."""
    with plt.rc_context(SPEC_RC):
        fig = plt.figure(figsize=(13.33, 7.5))
        ax = fig.add_axes([0.03, 0.04, 0.215, 0.84]); ax.set_anchor("E")      # the frame hugs inset A
        ax.imshow(_f_1km(C), cmap=C.FCMAP, norm=C.FNORM, interpolation="nearest", zorder=0.5)
        C.draw_pa(ax); STYLE["_fs_scale"] = 0.9
        try:
            draw(ax); C.finish(ax, "", None, note="", legend_loc="none", names=STYLE["wide_main_names"], towns=STYLE["wide_main_towns"],
                               name_fs=STYLE["wide_main_name_fs"])
        finally:
            STYLE.pop("_fs_scale", None)
        rects = [(0.27, 0.19, 0.335, 0.66), (0.635, 0.19, 0.335, 0.66)]
        aspect_hw = (rects[0][3] * 7.5) / (rects[0][2] * 13.33)
        for (num, rect, tag) in zip(STYLE["inset_clusters"], rects, "ABCDEF"):   # windows sized on the clusters, titled A, B ... (Ethan)
            win, p = _inset_window(C, num, aspect_hw)
            iax = fig.add_axes(rect); STYLE["_fs_scale"] = STYLE["inset_number_fs"] / STYLE["cluster_number_fs"]; STYLE["_lw_scale"] = STYLE["cluster_lw_inset_scale"]
            try:
                _draw_inset(C, iax, win, draw, tag, with_ipca_names)
            finally:
                STYLE.pop("_fs_scale", None); STYLE.pop("_lw_scale", None)
            px0, px1, pyt, pyb = win                                                   # the window on the frame, tagged
            ax.add_patch(Rectangle((px0, pyt), px1 - px0, pyb - pyt, fill=False, edgecolor="#333333", lw=1.0, zorder=7))
            ax.text(px0 + 8, pyt + 8, tag, fontsize=8, fontweight=600, color="white", ha="left", va="top", zorder=8,
                    bbox=dict(boxstyle="square,pad=0.15", facecolor="#333333", edgecolor="none"))
        cax = fig.add_axes([0.29, 0.085, 0.30, 0.03])
        cb = fig.colorbar(ScalarMappable(norm=C.FNORM, cmap=C.FCMAP), cax=cax, orientation="horizontal", extend="both")
        cb.set_label(STYLE["ramp_label_short"], fontsize=STYLE["cbar_fs"], color=TABLE["cap"])
        cb.ax.tick_params(labelsize=STYLE["cbar_fs"] - 1)
        fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.635, 0.012), fontsize=STYLE["legend_fs"], frameon=True, framealpha=0.92, edgecolor="#9a9a9a")
        fig.suptitle(title, fontsize=STYLE["map_suptitle_fs"], y=0.995, color=TABLE["ink"], fontweight=600)
        fig.savefig(path, dpi=200, bbox_inches="tight"); plt.show()


def _act1_map(C, path, title, draw, handles, cbar_label=None, with_ipca_names=False):
    if STYLE["map_layout"] == "wide":
        _wide_map(C, path, title, draw, handles, cbar_label, with_ipca_names)
    else:
        _single_map(C, path, title, draw, handles, cbar_label)


def core_map_F(C, path, title=None):
    """Act 1 (a): F at 1 km over unprotected land, with the declared IPCA proposals outlined (+ zoom insets in the wide layout)."""
    core_km2 = C.S["frequent_km2"]["guarded"]
    _act1_map(C, path, title or ("Act 1 — these areas recur in near-optimal plans no matter whose values prevail\n"
                                 f"core = {core_km2:,} km² (F ≥ 0.70) · no value theme left more than 5% behind"),
              draw=lambda ax: C.draw_ipca(ax), handles=C.BASE_HANDLES[:1] + [C.IPCA_HANDLE], with_ipca_names=True)


def core_map_clusters(C, path, title=None):
    """Act 1 (b): the same surface with the core clusters outlined and numbered north → south (+ zoom insets)."""
    core_km2 = C.S["frequent_km2"]["guarded"]
    _act1_map(C, path, title or ("Act 1 — the core clusters, numbered north → south\n"
                                 f"core = {core_km2:,} km² of unprotected land at F ≥ 0.70"),
              draw=lambda ax: C.draw_clusters(ax, "act1", C.picks_for("Act 1"), fs=STYLE["cluster_number_fs"] * STYLE.get("_fs_scale", 1.0), lw=STYLE["cluster_lw"]),
              handles=C.BASE_HANDLES[:1] + [Patch(facecolor="none", edgecolor="#444444", lw=1.5, label="Core clusters")])


# ---- the bare-bones objectives table for the presentation (Ethan, 2026-09-14): fundamental → sub-objective → measure, no numbers ----
VALUES_SIMPLE = [
    ("PROTECT — wildlife have sufficient core habitat", "Quantity of core habitat", ["Protected land"]),
    ("", "Quality of core habitat", ["Climate refugia", "Naturalness"]),
    ("", "Biodiversity", ["Mammal richness", "Bird richness"]),
    ("", "Representativeness", ["Ecosystem functional groups"]),
    ("CONNECT — wildlife corridors connect core habitats", "Quality of connectivity", ["Climate corridors", "Habitat connectivity"]),
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
                   title=title, stub_head="Fundamental objective", stub_w=stub_w, numeric=numeric, stub_sep=True,
                   notes=[("Source", SOURCE_NOTE)])
