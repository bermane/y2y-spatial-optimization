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
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Patch, Rectangle
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
        g = CL.get(layer)
        if g is None:
            return
        for _, r in g.iterrows():
            for ring in rings_px(r.geometry):
                ax.plot(ring[:, 0], ring[:, 1], color=color, lw=lw, zorder=4)
            if int(r.cid) in numbers and numbers[int(r.cid)][1]:
                c = r.geometry.centroid
                cx, cy = dc.xy_to_px(G, c.x, c.y)
                ax.annotate(numbers[int(r.cid)][0], xy=(cx, cy), xytext=(cx + 30, cy - 30), fontsize=fs, fontweight="bold",
                            color=color, path_effects=halo, zorder=6, arrowprops=dict(arrowstyle="-", color=color, lw=0.6))

    def draw_ipca(ax, lw=1.3):
        for _, r in IP.gdf.iterrows():
            for ring in rings_px(r.geometry):
                ax.plot(ring[:, 0], ring[:, 1], color=IPCA_COLOR, lw=lw, ls="-", zorder=3.5)

    def finish(ax, title, handles, note=N_NOTE, legend_loc="upper right", scale=True):
        dc.draw_admin(ax, G, ADMIN)                                   # provinces/states + border as the background
        dc.graticule(ax, G, lats=(53,), lons=(), emph_lat=53)         # only the 53°N line (E17 tie-in)
        ax.set_xlim(0, G.shape[1]); ax.set_ylim(G.shape[0], 0)
        if scale:
            dc.scalebar(ax, G)
        dc.corner_note(ax, note)
        ax.set_title(title, fontsize=11.5)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
        if handles and legend_loc == "lower left":      # south-west corner (ocean): for value maps whose NE corner is full
            ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, 0.02), fontsize=8, frameon=True)
        elif handles:                                    # north-east corner: the one region every F map leaves empty
            ax.legend(handles=handles, loc="upper right", bbox_to_anchor=(1.0, 0.90), fontsize=8, frameon=True)

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

    IPCA_HANDLE = Patch(facecolor="none", edgecolor=IPCA_COLOR, label="declared IPCA proposals (not locked in)")
    BASE_HANDLES = [Patch(facecolor=PA_COLOR, label="Existing protected areas (locked in)"),
                    Patch(facecolor=NEVER_COLOR, edgecolor="#bbbbbb", label="never selected (F = 0)"),
                    Patch(facecolor="none", edgecolor=CL_COLOR, label="numbered = deck picks")]

    def star_rows(rows, color):
        return [dict(title=f"Cluster {int(r.number)}\n{r.area_km2:,.0f} km² · mean F {r.mean_guarded_F:.2f}"
                           + (f"\nADEQUACY PIN: only {r.adequacy_pin_class} on the extent" if bool(r.get("adequacy_pin", False)) else ""),
                     values={a: r[f"pct_{a}"] for a in dc.STAR_AXES}, color=color) for _, r in rows.iterrows()]

    def numbered(act):
        """T-D1 rows of the numbered deck picks for an act ('Act 1' = the core, 'Act 2' = the scenarios), by number."""
        d = TD1[(TD1.act == act) & TD1.number.notna() & (TD1.number != "")].copy()
        d["number"] = d.number.astype(int)
        return d.sort_values("number")

    def consequences_png(rows, path, title):
        """T-D7: the cluster's mean value / the mean over allocatable land, shown as '2.3x'."""
        d = pd.DataFrame({"cluster": rows.number.map(lambda n: f"Cluster {int(n)}"), "km²": rows.area_km2.map("{:,.0f}".format),
                          "mean F": rows.mean_guarded_F.map("{:.2f}".format),
                          **{a: rows[f"ratio_{a}"].map(lambda v: f"{v:.2f}×" if v < 1 else f"{v:.1f}×") for a in dc.STAR_AXES}})   # "0.79x", "2.3x", "4.0x"
        if "driving_label" in rows and rows.driving_label.nunique() > 1:
            d.insert(1, "leads with", rows.driving_label.values)
        table_png(d, path, title, fs=9, scale=1.6, colw=[1.0] + ([1.6] if "leads with" in d else []) + [0.9, 0.8] + [1.0] * len(dc.STAR_AXES))

    ns = {k: v for k, v in locals().items() if not k.startswith("_")}
    ns.update(PA_COLOR=PA_COLOR, IPCA_COLOR=IPCA_COLOR, CL_COLOR=CL_COLOR, NEVER_COLOR=NEVER_COLOR,        # module constants, by name
              BAND_COLORS=BAND_COLORS, BAND_BOUNDS=BAND_BOUNDS, BAND_NAMES=BAND_NAMES, table_png=table_png)
    return SimpleNamespace(**ns)


def table_png(df, path, title, fs=7.5, scale=1.45, colw=None):
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
     ("", "Biodiversity", "Mammal richness and bird richness (species per km², area-of-habitat maps, all species)", "Lumbierres et al., AOH species richness",
      "Biodiversity theme: 25% (balanced); the two layers weighted equally"),
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
