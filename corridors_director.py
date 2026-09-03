"""Director package for the northern corridors (06 spec v1.1) -- the PRESENTATION layer.

Subordinate to `analyses/northern_connectivity/spec/05_corridors_v2_addendum_run_and_alternatives.md`
(methods) and built from `06_corridors_north_director_package_spec.md` (presentation). Consumes a
completed run through `corridors_core.load_results`; ZERO new solves. This module only renames
(director legend strings), selects (top-k by rule, never a new threshold), renders (flat
single-colour swaths, no ramps, no centrelines, CVD-checked palette) and assembles (profiles,
T1/T2, a draft .pptx via `director_core.build_deck`).

Story: Act 1, the north -- room to choose (securing regime; axis C = the sensitivity on the
IPCAs-as-given assumption). Act 2, the southern edge -- options are closing (both-senses
irreplaceable / edge-irreplaceable / squeezed). Guardrail: proposed IPCAs are taken as given,
visually and tabularly separable from existing PAs, never readable as a new priority.
"""
import json
import pathlib
import textwrap
from types import SimpleNamespace

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from rasterio.features import rasterize

import config
import corridors_core as cc
import results_core as rc
from corridors_core import PA_COLOR, ANCHOR_COLOR

PKG_SUB = "director_package"

# ---- director vocabulary (06 §3) -------------------------------------------------------------
# Class colours: securing light blue-grey, both-senses red, edge-irreplaceable orange, and
# SQUEEZED IN PURPLE -- the spec's orange/ochre pair fails the deuteranopia check (both collapse
# to a yellow-brown), so its own fallback applies. Chosen from the Okabe-Ito-compatible range.
CLASS = {
    "securing": ("#b8c4c9", "Corridor land with options — route and partners can be chosen"),
    "both":     ("#d7301f", "Only viable connection — no alternative link or route"),
    "edge":     ("#fc8d59", "Last affordable link — alternatives cost far more"),
    "squeezed": ("#7b3294", "Already narrowing — corridor below its natural width"),
}
OPTIONS_COLOR = "#2c7fb8"          # M2: route alternatives, ONE colour, equal weight
PA_LABEL = "Existing protected areas"
IPCA_LABEL = ("Proposed Indigenous Protected and Conserved Areas\n"
              "(as declared by Nations; treated as part of the network in this analysis)")
ATTR_BINS = (0.95, 0.75)           # decision (c): Unaffected >= .95 / Mostly unaffected >= .75
SOUTH_NAME = "the southern edge of the sector"   # decision (e): placeholder, directors' term TBC
CLAIM = "In the north we choose corridors; in the south they are chosen for us."


# ================= package context =================
def package(R, n_examples=7, south_of_frac=0.40, out=None):
    """Assemble everything the deck needs from a loaded run: disjoint classes (D7/D12/D17),
    axis-C attribution over PROPOSAL drops, endpoint classes, jurisdictions, and the example
    selection. Returns a namespace P; every renderer takes P."""
    P = SimpleNamespace(R=R, out=pathlib.Path(out) if out else R.run_dir / PKG_SUB)
    P.fig, P.tab = P.out / "figures", P.out / "tables"
    for d in (P.fig, P.tab):
        d.mkdir(parents=True, exist_ok=True)

    e, classes = cc._routing_classes(R)
    P.edges = e
    P.h8_open = not ("squeezed" in R.edges.columns and R.edges["squeezed"].notna().any())
    both, irr, sq = classes[0][1], classes[1][1], classes[2][1]
    cls = pd.Series("securing", index=e.index)
    cls[sq] = "squeezed"; cls[irr] = "edge"; cls[both] = "both"       # disjoint, precedence up
    cls[e["is_adjacency"] | (e["cost"] <= 0)] = "adjacency"
    P.cls = cls
    P.owner = np.nan_to_num(R.edge_owner.values, nan=-1).astype(int)
    P.order = {k: i for i, k in enumerate(R.edges.index)}

    P.endpoints = e.apply(lambda r: _endpoint_class(r["label_i"], r["label_j"]), axis=1)
    P.attr = _axis_c_attribution(R)                                  # per edge, proposal drops
    P.prov_raster, P.prov_names = _province_raster(R)
    P.jur = _edge_jurisdictions(P)
    P.examples = select_examples(P, n_examples, south_of_frac)
    P.south_of_frac = south_of_frac
    n = cls.value_counts()
    print(f"director package: classes -> both {n.get('both',0)} · edge {n.get('edge',0)} · "
          f"squeezed {n.get('squeezed',0)} · securing {n.get('securing',0)} | "
          f"{len(P.examples)} examples | H8 {'OPEN -- squeezed class withheld from deck' if P.h8_open else 'closed'}")
    return P


def _endpoint_class(li, lj):
    a, b = str(li).startswith("IPCA"), str(lj).startswith("IPCA")
    return "Proposed" if a and b else ("Established" if not a and not b else "Mixed")


def _axis_c_attribution(R):
    """Per edge: presence across axis-C members that drop a PROPOSAL (IPCA) which is not one of
    the edge's own endpoints -- 'we took every proposal as given; here is what depends on which
    one'. Endpoint drops are excluded (a link cannot exist without its endpoints: not a
    dependency finding); PA drops are excluded (not a proposal not proceeding)."""
    ens = R.run_dir / "ensemble"
    design = pd.read_csv(ens / "design.csv")
    rows = {}
    members = design[(design.kind == "C_loo")]
    presence, deps = {}, {}
    for r in members.itertuples():
        mj = json.loads((ens / f"run_{int(r.run_id):04d}" / "member.json").read_text())
        lbl = mj.get("drop_name_label") or ""
        if not lbl.startswith("IPCA"):
            continue
        present = set(pd.read_csv(ens / f"run_{int(r.run_id):04d}" / "edges.csv", index_col=0).index)
        for eid, er in R.edges.iterrows():
            if lbl in (er["label_i"], er["label_j"]):
                continue                              # endpoint drop -- structural, skipped
            presence.setdefault(eid, [0, 0])
            presence[eid][1] += 1
            if eid in present:
                presence[eid][0] += 1
            else:
                deps.setdefault(eid, []).append(lbl)
    out = pd.DataFrame({eid: dict(attr_c=v[0] / v[1] if v[1] else np.nan, n_c=v[1],
                                  depends_on="; ".join(deps.get(eid, [])))
                        for eid, v in presence.items()}).T
    out["attr_c"] = out["attr_c"].astype(float)
    return out


def attr_words(row):
    """Decision (c) bins -> T1 phrasing."""
    a = row.get("attr_c", np.nan)
    if pd.isna(a):
        return "n/a"
    if a >= ATTR_BINS[0]:
        return "Unaffected"
    if a >= ATTR_BINS[1]:
        return "Mostly unaffected"
    names = [cc._short_node_name(n, 22) for n in str(row.get("depends_on", "")).split("; ") if n]
    return "Depends on " + ", ".join(names[:2]) + (" …" if len(names) > 2 else "")


def _province_raster(R):
    """Natural Earth admin-1 polygons (public domain) rasterized on the routing grid: one id per
    province/territory. Display + 'who's at the table' only -- never enters routing."""
    p = config.INPUT_DIR / "basemap" / "ne_10m_admin_1_states_provinces.shp"
    if not p.exists():
        print("  note: admin-1 polygons absent -- jurisdiction tint/columns skipped")
        return None, []
    xs, ys = R.template.x.values, R.template.y.values
    g = gpd.read_file(p).to_crs(R.crs)
    g = g[g["admin"] == "Canada"].cx[xs.min():xs.max(), ys.min():ys.max()]
    names = list(g["name_en"] if "name_en" in g.columns else g["name"])
    ras = rasterize([(geom, i + 1) for i, geom in enumerate(g.geometry)], out_shape=R.shape,
                    transform=R.transform, fill=0, dtype="int16")
    return ras, names


def _edge_jurisdictions(P):
    if P.prov_raster is None:
        return pd.Series("pending authoritative layer", index=P.edges.index)
    out = {}
    for eid in P.edges.index:
        code = P.order.get(eid)
        cells = P.prov_raster[P.owner == code] if code is not None else np.empty(0)
        ids = [i for i in np.unique(cells) if i > 0]
        out[eid] = " / ".join(P.prov_names[i - 1] for i in ids) if ids else ""
    return pd.Series(out)


# ================= example selection (06 §2, top-k by rule) =================
def select_examples(P, n=7, south_of_frac=0.40):
    R, e = P.R, P.edges
    ex = []
    # N1: Dene K'éh Kusān leave-one-out pair (required)
    ex.append(dict(slot="N1", act=1, edge_id=None, title="Dene Kʼéh Kusān — network with / without",
                   kind="loo_pair"))
    # N2-N3: securing exemplars -- largest n_branches x attribution, tie-break toward
    # branches spanning >1 jurisdiction
    sec = e[(P.cls == "securing")].copy()
    sec["attr_c"] = P.attr["attr_c"].reindex(sec.index)
    sec["score"] = sec.get("n_branches", 1).fillna(1) * sec["attr_c"].fillna(0)
    sec["n_jur"] = P.jur.reindex(sec.index).str.count("/").fillna(0) + 1
    sec = sec.sort_values(["score", "n_jur", "ecfb_raw"], ascending=False)
    for k, eid in enumerate(sec.index[:2], 2):
        ex.append(dict(slot=f"N{k}", act=1, edge_id=eid, kind="link",
                       title=_pair_title(e.loc[eid])))
    # S1-S3: both-senses irreplaceable, highest criticality (n_pairs_lost, then backup ratio)
    both = e[P.cls == "both"].sort_values(["n_pairs_lost", "backup_ratio"], ascending=False)
    for k, eid in enumerate(both.index[:3], 1):
        ex.append(dict(slot=f"S{k}", act=2, edge_id=eid, kind="link", title=_pair_title(e.loc[eid])))
    P.appendix_both = list(both.index[3:])
    # S4: the most squeezed link (only with H8 closed and if total <= n)
    if not P.h8_open and len(ex) < n:
        sq = e[P.cls == "squeezed"]
        col = "squeeze_ratio_obs" if "squeeze_ratio_obs" in sq.columns else "squeeze_idx"
        if len(sq):
            eid = sq[col].idxmin()
            ex.append(dict(slot="S4", act=2, edge_id=eid, kind="link", title=_pair_title(e.loc[eid]),
                           headline=f"already at {sq.loc[eid, col]:.1f}× its natural width"))
    return ex[:n]


def _pair_title(r):
    return f"{cc._short_node_name(r['label_i'], 22)} ↔ {cc._short_node_name(r['label_j'], 22)}"


# ================= rendering primitives =================
def _base(P, ax, XL, YL, tint=False, towns=True):
    """PA/IPCA fills (distinct layers on every map), optional jurisdiction tint beneath,
    borders + towns."""
    R = P.R
    if tint and P.prov_raster is not None:
        pal = ["#eef3f7", "#f5efe6", "#eaf2ea", "#f3eaf2", "#f7f1e1"]
        for i in range(1, len(P.prov_names) + 1):
            m = P.prov_raster == i
            if m.any():
                cc._da(R, np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(
                    ax=ax, cmap=ListedColormap([pal[(i - 1) % len(pal)]]), add_colorbar=False)
    for layer, col in [(R.pa_mask, PA_COLOR), (R.anch, ANCHOR_COLOR)]:
        cc._da(R, np.where(layer, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    R.outline.boundary.plot(ax=ax, color="0.35", linewidth=1.0, linestyle="--")
    cc._draw_basemap(R, ax, XL, YL, towns=towns, max_towns=8)
    ax.set_xlim(*XL); ax.set_ylim(*YL); ax.set_aspect("equal"); ax.set_axis_off()


def _paint(P, ax, edge_ids, color):
    m = np.isin(P.owner, [P.order[k] for k in edge_ids if k in P.order]) & P.R.corridor
    if m.any():
        cc._da(P.R, np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([color]), add_colorbar=False)
    return m


def _node_handles():
    return [Patch(color=PA_COLOR, label=PA_LABEL), Patch(color=ANCHOR_COLOR, label=IPCA_LABEL)]


# ================= maps M1-M4 =================
def map_m1(P):
    """M1 -- the four-class regime map, full extent, flat swaths, director legend strings with
    bracket counts. Squeezed class withheld (drawn as securing) while H8 is open."""
    R = P.R
    XL, YL = cc._region_extent(R, 0.05)
    fig, ax = plt.subplots(figsize=(12, 13))
    handles = []
    order = ["securing", "squeezed", "edge", "both"]
    for c in order:
        ids = P.cls.index[P.cls == c]
        if c == "squeezed" and P.h8_open:
            ids = []
        col, lbl = CLASS[c]
        if c == "securing":
            ids = list(ids) + (list(P.cls.index[P.cls == "squeezed"]) if P.h8_open else [])
        if c == "squeezed" and P.h8_open:
            continue                          # withheld: not drawn, not in the legend
        _paint(P, ax, ids, col)
        handles.append(Patch(color=col, label=f"{lbl}  [{len(ids)}]"))
    _base(P, ax, XL, YL, towns=False)
    handles += _node_handles()
    ax.legend(handles=handles, loc="lower left", fontsize=9, frameon=True)
    ax.set_title("Where the land still offers choices — and where it does not", fontsize=13)
    fig.savefig(P.fig / "M1_regime.png", dpi=170, bbox_inches="tight"); plt.show()
    return P


def map_m2(P):
    """M2 -- Act 1: securing-regime bands only, N2/N3 route alternatives as EQUAL single-colour
    swaths, jurisdiction tint beneath."""
    R = P.R
    XL, YL = cc._region_extent(R, 0.05)
    fig, ax = plt.subplots(figsize=(12, 13))
    _base(P, ax, XL, YL, tint=True, towns=True)
    sec_ids = list(P.cls.index[P.cls == "securing"])
    _paint(P, ax, sec_ids, CLASS["securing"][0])
    lab = np.nan_to_num(R.branch_label.values, nan=0).astype(int)
    br = R.branches.reset_index(drop=True); br["value"] = np.arange(1, len(br) + 1)
    for ex in P.examples:
        if ex["slot"] in ("N2", "N3") and ex["edge_id"] is not None:
            vals = br.loc[br.edge_id == ex["edge_id"], "value"]
            m = np.isin(lab, vals)
            if m.any():
                cc._da(R, np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(
                    ax=ax, cmap=ListedColormap([OPTIONS_COLOR]), add_colorbar=False)
            rr, ccol = np.nonzero(m)
            if len(rr):
                ax.annotate(ex["slot"], (R.template.x.values[int(np.median(ccol))],
                                         R.template.y.values[int(np.median(rr))]),
                            fontsize=10, fontweight="bold", ha="center", va="center",
                            bbox=dict(boxstyle="circle,pad=0.28", fc="white", ec=OPTIONS_COLOR, lw=1.6))
    handles = [Patch(color=CLASS["securing"][0], label=CLASS["securing"][1]),
               Patch(color=OPTIONS_COLOR, label="Route options for the Act 1 examples (equal weight)")]
    handles += _node_handles()
    if P.prov_raster is not None:
        handles.append(Patch(color="#f5efe6", label="Jurisdiction tint (provinces/territories; "
                                                    "settlement lands pending)"))
    ax.legend(handles=handles, loc="lower left", fontsize=9, frameon=True)
    ax.set_title("Act 1 — the north: room to choose", fontsize=13)
    fig.savefig(P.fig / "M2_act1_securing.png", dpi=170, bbox_inches="tight"); plt.show()
    return P


def map_m3(P):
    """M3 -- Act 2: southern zoom, flagged links only, one colour per class, and the D17
    counterfactual 'natural width' as a thin outline around squeezed bands (H8 closed) --
    otherwise the ratio chip fallback (decision (d))."""
    R = P.R
    e, classes, owner, order, links, XL, YL = cc._zoom_links(R, 0.5, P.south_of_frac, 35)
    fig, ax = plt.subplots(figsize=(12.5 * (XL[1] - XL[0]) / (YL[1] - YL[0]) + 3, 13))
    _base(P, ax, XL, YL, towns=True)
    handles = []
    for c in ("squeezed", "edge", "both"):
        ids = list(P.cls.index[P.cls == c])
        if c == "squeezed" and P.h8_open:
            continue
        _paint(P, ax, ids, CLASS[c][0])
        handles.append(Patch(color=CLASS[c][0], label=CLASS[c][1]))
    if not P.h8_open and getattr(R, "cf_bands", None) is not None:
        sq_ids = list(P.cls.index[P.cls == "squeezed"])
        cf = R.cf_bands[R.cf_bands.edge_id.isin(sq_ids)]
        if len(cf):
            cf.boundary.plot(ax=ax, color=CLASS["squeezed"][0], linewidth=0.9, linestyle=":")
            handles.append(plt.Line2D([0], [0], color=CLASS["squeezed"][0], ls=":", lw=1,
                                      label="Natural width of a squeezed corridor (no barriers)"))
    handles += _node_handles()
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=9,
              frameon=True)
    ax.set_title(f"Act 2 — {SOUTH_NAME}: options are closing", fontsize=13)
    fig.savefig(P.fig / "M3_act2_flagged.png", dpi=170, bbox_inches="tight"); plt.show()
    return P


def map_m4(P):
    """M4 (N1) -- the with / without Dene Kʼéh Kusān pair, small multiples, identical extent
    and symbology; bands only."""
    R = P.R
    ens = R.run_dir / "ensemble"
    design = pd.read_csv(ens / "design.csv")
    rid = None
    for r in design[design.kind == "C_loo"].itertuples():
        mj = json.loads((ens / f"run_{int(r.run_id):04d}" / "member.json").read_text())
        if "Dene K" in (mj.get("drop_name_label") or ""):
            rid, drop_lbl = int(r.run_id), mj["drop_name_label"]; break
    assert rid is not None, "Dene Kʼéh Kusān leave-one-out member not found"
    import rioxarray
    without = rioxarray.open_rasterio(ens / f"run_{rid:04d}" / "corridors.tif", masked=True).squeeze()
    wo = np.nan_to_num(without.values, nan=0) > 0
    XL, YL = cc._region_extent(R, 0.05)
    fig, axes = plt.subplots(1, 2, figsize=(20, 12.5))
    for ax, mask, title in ((axes[0], R.corridor, "With Dene Kʼéh Kusān (as declared)"),
                            (axes[1], wo, "Without Dene Kʼéh Kusān (proposal not realised)")):
        cc._da(R, np.where(mask, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([CLASS["securing"][0]]), add_colorbar=False)
        _base(P, ax, XL, YL, towns=False)
        ax.set_title(f"{title} — {int(mask.sum())*R.cell_km2:,.0f} km² of corridor land",
                     fontsize=12)
    # outline the Dene polygon on the 'without' panel so the missing anchor is legible
    parts = gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(R.crs)
    dene_g = parts[parts.name_label.str.contains("Dene K", regex=False)]
    if len(dene_g):
        dene_g.dissolve().boundary.plot(ax=axes[1], color="0.1", linewidth=1.4, linestyle="--")
    axes[1].legend(handles=[Patch(color=CLASS["securing"][0], label="Corridor land (bands only)")]
                   + _node_handles(), loc="lower left", fontsize=9, frameon=True)
    fig.suptitle("N1 — what the network loses if the largest proposal is not realised "
                 "(axis C: the sensitivity on 'proposals as given')", fontsize=13)
    fig.tight_layout()
    fig.savefig(P.fig / "M4_N1_dene_pair.png", dpi=150, bbox_inches="tight"); plt.show()
    P.n1 = dict(run_id=rid, with_km2=int(R.corridor.sum()) * R.cell_km2, without_km2=int(wo.sum()) * R.cell_km2)
    return P


# ================= profiles (06 §2 one-pagers) =================
def link_profiles(P):
    """Framing-1 value profiles for EVERY non-adjacency link (owner cells, majority crossing --
    the corridor-audit path), so each example's audit row can be expressed as PERCENTILE CHIPS
    among all links (no raw numbers on director pages)."""
    R = P.R
    Pst = cc._profile_stacks(R)
    ids = [k for k in P.edges.index if P.cls.get(k) != "adjacency" and k in P.order]
    rows = {}
    for k in ids:
        m = (P.owner == P.order[k]) & R.corridor
        if not m.any():
            continue
        audit = cc._to_audit(R, m)
        if not audit.any():
            continue
        prof, contrib, eff, raw = rc.mask_profile(Pst, audit)
        rows[k] = {f"{ax}": prof[j] for j, ax in enumerate(Pst.axes_labels)}
    df = pd.DataFrame(rows).T
    P.profiles = df
    P.profile_pct = df.rank(pct=True) * 100          # percentile among links, per axis
    P.axes = list(Pst.axes_labels)
    df.round(3).to_csv(P.tab / "link_profiles_all.csv", encoding="utf-8-sig")
    print(f"  link profiles: {len(df)} links x {df.shape[1]} axes -> percentile chips")
    return P


_CHIP_AXES = {"irrecoverable carbon biomass": "carbon (biomass)", "irrecoverable carbon m soc": "carbon (soil)",
              "aoh richness mammals": "mammals", "aoh richness birds": "birds",
              "climate type macrorefugia": "climate refugia", "EFG (mean)": "ecosystem types",
              "climate corridors": "climate corridors (Carroll)"}


def _chips(P, eid, n=4):
    if getattr(P, "profile_pct", None) is None or eid not in P.profile_pct.index:
        return []
    s = P.profile_pct.loc[eid]
    s = s[[a for a in s.index if a in _CHIP_AXES]].sort_values(ascending=False)
    return [f"{_CHIP_AXES[a]} · p{int(round(v))}" for a, v in s.head(n).items()]


def profile_pages(P):
    """One page per example: zoom map (band swath, endpoints, borders, towns) + ~120 words +
    the 4-row mini-table + percentile chips (+ Act 1: the jurisdiction line)."""
    R, e = P.R, P.edges
    xs, ys = R.template.x.values, R.template.y.values
    out = []
    for ex in P.examples:
        fig = plt.figure(figsize=(15, 8.5))
        axm = fig.add_axes([0.02, 0.05, 0.50, 0.88])
        axt = fig.add_axes([0.55, 0.05, 0.43, 0.88]); axt.set_axis_off()
        if ex["kind"] == "loo_pair":
            XL, YL = cc._region_extent(R, 0.05)
            cc._da(R, np.where(R.corridor, 1.0, np.nan).astype("float32")).plot.imshow(
                ax=axm, cmap=ListedColormap([CLASS["securing"][0]]), add_colorbar=False)
            _base(P, axm, XL, YL, towns=False)
            n1 = getattr(P, "n1", {})
            touch = e[(e.label_i.str.contains("Dene K", regex=False))
                      | (e.label_j.str.contains("Dene K", regex=False))]
            n_touch, n_adj = len(touch), int(touch["is_adjacency"].sum())
            words = (f"Dene Kʼéh Kusān is the largest proposal in the sector, and the network "
                     f"leans on it: {n_touch} of the analysis' links touch it, {n_adj} of them "
                     f"free adjacencies with parks it wraps around. Taking the proposal "
                     f"as given, the network holds {n1.get('with_km2', 0):,.0f} km² of corridor "
                     f"land; without it the network reroutes around the gap and grows to "
                     f"{n1.get('without_km2', 0):,.0f} km² — more land, longer routes, lower "
                     f"certainty. This is the sensitivity on the analysis' central assumption, "
                     f"stated neutrally: the proposal is treated as part of the network; here "
                     f"is what depends on it.")
            rows = [("Connects", "eleven neighbouring parks + the Liard/Nahanni corridor"),
                    ("Status", "Act 1 — the assumption the north story rests on"),
                    ("Room to move", "with: adjacencies · without: reroutes"),
                    ("If the proposal doesn't proceed", f"+{n1.get('without_km2',0)-n1.get('with_km2',0):,.0f} km² of new corridor need")]
            chips, jur = [], ""
        else:
            eid = ex["edge_id"]; r = e.loc[eid]
            code = P.order[eid]
            cells = np.argwhere(P.owner == code)
            pad = 60_000
            XL = (xs[cells[:, 1].min()] - pad, xs[cells[:, 1].max()] + pad)
            YL = (ys[cells[:, 0].max()] - pad, ys[cells[:, 0].min()] + pad)
            c = P.cls[eid]
            col = CLASS["securing"][0] if c == "securing" else CLASS[c][0]
            _paint(P, axm, [eid], col)
            _base(P, axm, XL, YL, towns=True)
            status = CLASS[c if c != "adjacency" else "securing"][1]
            nb = int(r.get("n_branches", 1)) if pd.notna(r.get("n_branches", np.nan)) else 1
            room = f"{nb} route options" if nb > 1 else "single route"
            att = attr_words(P.attr.loc[eid]) if eid in P.attr.index else "n/a"
            chips = _chips(P, eid)
            jur = P.jur.get(eid, "")
            words = _profile_words(P, ex, r, c, nb, att, chips, jur)
            rows = [("Connects", _pair_title(r)), ("Status", status), ("Room to move", room),
                    ("If a proposal doesn't proceed", att)]
            if ex["act"] == 1:
                rows.append(("Who's at the table", jur or "pending authoritative layer"))
        axm.set_title("")
        y = 0.97
        axt.text(0, y, f"{ex['slot']} · {ex['title']}", fontsize=15, fontweight="bold", va="top")
        y -= 0.08
        axt.text(0, y, textwrap.fill(words, 78), fontsize=10.5, va="top", linespacing=1.4)
        y -= 0.42
        for k, v in rows:
            axt.text(0, y, textwrap.fill(k, 26), fontsize=9.5, fontweight="bold", va="top")
            axt.text(0.46, y, textwrap.fill(str(v), 40), fontsize=10, va="top")
            y -= 0.075
        if chips:
            axt.text(0, y - 0.01,
                     textwrap.fill("Co-benefits (percentile among all links): "
                                   + "  ·  ".join(chips), 72),
                     fontsize=9.5, va="top", color="0.25", linespacing=1.3)
        fn = P.fig / f"profile_{ex['slot']}.png"
        fig.savefig(fn, dpi=150, bbox_inches="tight"); plt.show()
        out.append(fn)
    P.profile_files = out
    return P


def _profile_words(P, ex, r, c, nb, att, chips, jur):
    a, b = cc._short_node_name(r["label_i"], 26), cc._short_node_name(r["label_j"], 26)
    if c == "both":
        w = (f"The corridor between {a} and {b} is the only viable connection: no other link "
             f"would reconnect the network at a reasonable price (the cheapest alternative costs "
             f"{r['backup_ratio']:.1f}× as much, about {(r['backup_ratio']-1)*r['cost']/(10/3):,.0f} km of "
             f"extra intact-land travel), and within the corridor there is a single physical route. "
             f"Losing this land leaves neither a plan B route nor a plan B link.")
    elif c == "edge":
        w = (f"{a} and {b} nearly touch, and the contact zone is the connection. There is no "
             f"affordable substitute link — the cheapest alternative costs {r['backup_ratio']:.1f}× "
             f"as much. What matters here is the junction itself rather than a swath of corridor.")
    elif c == "squeezed":
        hl = ex.get("headline", "")
        w = (f"The corridor between {a} and {b} is {hl or 'narrower than its natural width'}: "
             f"barriers on both flanks have removed most of the near-optimal alternatives, so the "
             f"mapped ribbon is a large share of all the land that still works. The link is still "
             f"substitutable at the network level — its neighbours are each other — so the risk is "
             f"correlated across this cluster, not independent.")
    else:
        w = (f"Between {a} and {b} the land still offers choices: {room_phrase(nb)}, and the "
             f"corridor is wanted under {'every' if att == 'Unaffected' else 'nearly every'} future "
             f"in which a proposal does not proceed. The decision here is not where — it is who "
             f"secures it, with whom, and in what order."
             + (f" Land between the endpoints: {jur}." if jur else ""))
    return w


def room_phrase(nb):
    return f"{nb} distinct route options" if nb > 1 else "a single route within a wide band"


# ================= tables T1 / T2 =================
def table_t1(P):
    R, e = P.R, P.edges
    rows = []
    for ex in P.examples:
        if ex["kind"] == "loo_pair":
            n1 = getattr(P, "n1", {})
            rows.append(dict(Example=ex["slot"], Connects="Dene Kʼéh Kusān ↔ its neighbours",
                             Status="Act 1 — the assumption tested", **{"Room to move": "adjacencies → reroutes"},
                             **{"If a proposal doesn't proceed": f"+{n1.get('without_km2',0)-n1.get('with_km2',0):,.0f} km² corridor need"},
                             Endpoints="Proposed", **{"Co-benefits": "—"}, **{"Who's at the table": "pending"}))
            continue
        eid = ex["edge_id"]; r = e.loc[eid]; c = P.cls[eid]
        nb = int(r.get("n_branches", 1)) if pd.notna(r.get("n_branches", np.nan)) else 1
        rows.append(dict(
            Example=ex["slot"], Connects=_pair_title(r),
            Status=CLASS[c if c != "adjacency" else "securing"][1].split(" — ")[0],
            **{"Room to move": f"{nb} route options" if nb > 1 else "single route"},
            **{"If a proposal doesn't proceed": attr_words(P.attr.loc[eid]) if eid in P.attr.index else "n/a"},
            Endpoints=P.endpoints[eid],
            **{"Co-benefits": ", ".join(x.split(" · ")[0] for x in _chips(P, eid, 2)) or "—"},
            **{"Who's at the table": (P.jur.get(eid, "") or "pending") if ex["act"] == 1 else ""}))
    t1 = pd.DataFrame(rows)
    t1.to_csv(P.tab / "T1_examples.csv", index=False, encoding="utf-8-sig")
    _table_png(t1, P.fig / "T1_examples.png", "T1 — the examples, in plain language")
    P.t1 = t1
    return t1


def table_t2(P):
    """Appendix: all flagged links x the full audit column set (framing 1, link profiles) +
    Carroll percentile + endpoint class. Captioned with the D13 row-unit caveat."""
    e = P.edges
    flagged = [k for k in e.index if P.cls.get(k) in ("both", "edge", "squeezed")]
    base = e.loc[flagged, ["label_i", "label_j", "cost", "irreplaceable", "backup_ratio",
                            "n_branches", "route_irreplaceable"]].copy()
    if "squeeze_ratio_obs" in e.columns:
        base["squeeze_ratio_obs"] = e.loc[flagged, "squeeze_ratio_obs"]
    base["class"] = P.cls[flagged].values
    base["endpoints"] = P.endpoints[flagged].values
    base["attr_c"] = P.attr["attr_c"].reindex(flagged).round(3).values
    prof = getattr(P, "profiles", pd.DataFrame()).reindex(flagged).round(3)
    prof.columns = [f"{c} | richness" for c in prof.columns]
    t2 = pd.concat([base, prof], axis=1)
    t2.to_csv(P.tab / "T2_flagged_links.csv", encoding="utf-8-sig")
    (P.tab / "T2_flagged_links.caption.txt").write_text(
        "Row unit = link (framing 1: the corridor land each link owns on the priority surface, "
        "0.5-majority crossing to the 1 km audit grid); columns follow the Y2Y-wide alternatives "
        "table for readability only and do not imply a shared estimand (D13). Branch-level values "
        "(framing 2, alternatives_branches.csv) are the nested route drill-down.")
    P.t2 = t2
    print(f"  T2: {len(t2)} flagged links x {t2.shape[1]} columns")
    return t2


def _table_png(df, path, title):
    fig, ax = plt.subplots(figsize=(min(24, 2.6 * df.shape[1] + 2), 0.55 * len(df) + 1.6))
    ax.set_axis_off()
    tb = ax.table(cellText=[[textwrap.fill(str(v), 28) for v in row] for row in df.values],
                  colLabels=list(df.columns), loc="center", cellLoc="left")
    tb.auto_set_font_size(False); tb.set_fontsize(8.5); tb.scale(1, 2.2)
    ax.set_title(title, fontsize=13, pad=12)
    fig.savefig(path, dpi=160, bbox_inches="tight"); plt.show()


# ================= deck (06 §5) =================
def build_deck(P, path=None):
    import director_core as dc
    F = P.fig
    slides = [
        dict(title="Keeping the North Connected", image=None,
             bullets=[CLAIM, "",
                      "This analysis treats declared IPCA proposals as part of the protected "
                      "network: they are routed between exactly as existing protected areas are.",
                      "Structural connectivity — landscape condition — not measured animal movement."]),
        dict(title="Where the land still offers choices — and where it does not",
             image=F / "M1_regime.png",
             bullets=["Act 1 (north): corridor land with options — route and partners can be chosen.",
                      f"Act 2 ({SOUTH_NAME}): the map makes the decision — the remaining work is timing."]),
        dict(title="Act 1 — the north: room to choose", image=F / "M2_act1_securing.png",
             bullets=["Wide bands, multiple routes, alternative links.",
                      "Connectivity is contingent on decisions, not on geography.",
                      "Sequencing can follow relationships, jurisdiction and the pace of IPCA realisation."]),
        dict(title="N1 — what depends on the largest proposal", image=F / "M4_N1_dene_pair.png",
             bullets=["We took every proposal as given; here is what depends on this one.",
                      f"With: {getattr(P,'n1',{}).get('with_km2',0):,.0f} km² · without: "
                      f"{getattr(P,'n1',{}).get('without_km2',0):,.0f} km² of corridor land."]),
    ]
    for ex in P.examples:
        if ex["slot"] in ("N2", "N3"):
            slides.append(dict(title=f"{ex['slot']} — {ex['title']}", image=F / f"profile_{ex['slot']}.png",
                               bullets=[]))
    slides.append(dict(title=f"Act 2 — {SOUTH_NAME}: options are closing",
                       image=F / "M3_act2_flagged.png",
                       bullets=["Both-senses irreplaceable: only viable connection.",
                                "Edge-irreplaceable: last affordable link.",
                                "Squeezed: already below natural width." if not P.h8_open
                                else "Squeezed class withheld pending H8."]))
    for ex in P.examples:
        if ex["slot"].startswith("S"):
            slides.append(dict(title=f"{ex['slot']} — {ex['title']}", image=F / f"profile_{ex['slot']}.png",
                               bullets=[ex.get("headline", "")] if ex.get("headline") else []))
    slides += [
        dict(title="T1 — the examples in plain language", image=F / "T1_examples.png", bullets=[]),
        dict(title="What this asks of directors", image=None,
             bullets=["Act 1 → sequencing and relationship investment: choose partners and order.",
                      "Act 2 → timing decisions: the corridor is where it is."]),
        dict(title="Appendix — methods one-pager", image=None,
             bullets=["Cost surface: O'Brien et al. transboundary movement-cost surface (Pither et al. 2023 extension), 4 ordinal classes at 300 m, used as published.",
                      "Network: least-cost routing between every protected area and declared IPCA; minimum spanning tree + affordable backups (β = 2.5).",
                      "Alternatives: route branches at half the corridor allowance; two irreplaceability senses reported together.",
                      "Robustness: 47-member structured ensemble (band width, leave-one-out by name, β).",
                      "Climate: audit-only (macrorefugia, Carroll 2018 centrality); no routing is climate-informed; velocity-modified routing deferred.",
                      "Claim scope: structural connectivity; nothing validated against movement, genetic or occurrence data."]),
    ]
    path = path or (P.out / "north_director_deck.pptx")
    dc.build_deck(slides, path, subtitle="")
    (P.out / "deck_outline.md").write_text("\n".join(f"{i+1}. {s['title']}" for i, s in enumerate(slides)))
    try:
        shown = path.relative_to(config.PROJECT_DIR)
    except ValueError:
        shown = path
    print(f"  deck: {len(slides)} slides -> {shown}")
    return path
