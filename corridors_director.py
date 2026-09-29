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
import pyproj
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
    "both":     ("#d7301f", "Only viable connection — no alternative link or route, and the land is already narrowing"),   # D23 (2026-09-28)
    "edge":     ("#fc8d59", "Last affordable link — alternatives cost far more"),
    "squeezed": ("#7b3294", "Already narrowing — corridor below its natural width"),
    # D25 / D25a (2026-09-28): near-contiguous links -- neutral grey, drawn UNDER the four corridor classes, never one of them
    "near_contiguous_open":    ("#D9D9D9", "Adjacent areas — open front"),
    "near_contiguous_roads":   ("#D9D9D9", "Adjacent areas — front crossed by roads or cuts"),
    "near_contiguous_barrier": ("#D9D9D9", "Adjacent areas — barrier between"),
}
NEAR_CONTIGUOUS_KEYS = ("near_contiguous_open", "near_contiguous_roads", "near_contiguous_barrier")
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
    if len(classes) >= 6:                                              # D25a (a run classified by classify_links): the three near-contiguous rows
        cls[classes[3][1]] = "near_contiguous_open"; cls[classes[4][1]] = "near_contiguous_roads"; cls[classes[5][1]] = "near_contiguous_barrier"
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


def _province_raster(R, countries=("Canada",)):
    """Natural Earth admin-1 polygons (public domain) rasterized on the routing grid: one id per
    province/territory. Display + 'who's at the table' only -- never enters routing.
    `countries=None` keeps every country in the window (wolverine: Canada + USA)."""
    p = config.INPUT_DIR / "basemap" / "ne_10m_admin_1_states_provinces.shp"
    if not p.exists():
        print("  note: admin-1 polygons absent -- jurisdiction tint/columns skipped")
        return None, []
    xs, ys = R.template.x.values, R.template.y.values
    g = gpd.read_file(p).to_crs(R.crs)
    if countries:
        g = g[g["admin"].isin(list(countries))]
    g = g.cx[xs.min():xs.max(), ys.min():ys.max()]
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
# Examples PINNED by Ethan (2026-09-09) -- label fragments resolved to edge ids at package time.
# Act 1 shows OPTIONS: N2 = one link with two route branches (numbers 1-2), N3 = two links to
# the same complex (3-4). Act 2 shows the three southern example links (5-7).
EXAMPLE_PICKS = [
    # Every option = one LINK's full corridor band (its owned land, exactly as M1 draws it) --
    # Ethan 2026-09-11, after seeing that the Dene<->Nahanni and Liard<->Nahanni bands overlap.
    # NUMBERING (Ethan 2026-09-28; the deck's 07 · 03 map shows 1-4, inset A = 1-2, inset B = 3-4):
    #   1 = Nahanni to Dene Kʼéh Kusān, 2 = Nahanni to the Liard River Corridor (two ways south);
    #   3 = Gwillim Lake <-> Pine Le Moray (the only viable connection; was option 5);
    #   4 = Gwillim Lake <-> Monkman -- a NARROWING corridor inside inset B (new; the pick is this one
    #       line: Carp Lake <-> Pine Le Moray, 0.23x its natural width, is the alternative, also inside B);
    #   5-6 = the two links from T'akú Tlatsini to the Mount Edziza / Stikine complex (were 3-4);
    #   7 = Wilps Gwininitxw <-> Swan Lake; 8 = Carp Lake <-> Pine Le Moray (no M3 marker, Ethan).
    dict(slot="N2", act=1, pair=("Dene K", "Nahanni National"), options="links",
         option_pairs=[("Dene K", "Nahanni National"), ("Liard River Corridor", "Nahanni National")],
         side=["sw", "ne"]),
    dict(slot="S1", act=2, pair=("Gwillim", "Pine Le Moray"), side="nw"),
    dict(slot="S1b", act=2, pair=("Gwillim", "Monkman"), side="ne"),
    dict(slot="N3", act=1, pair=("T’akú", "Mount Edziza"), options="links",
         option_pairs=[("T’akú", "Mount Edziza"), ("T’akú", "Stikine")], side=["sw", "ne"]),
    dict(slot="S2", act=2, pair=("Wilps Gwininitxw", "Swan Lake")),
    dict(slot="S3", act=2, pair=("Carp Lake", "Pine Le Moray"), mark=False),   # no M3 marker (Ethan)
]
OPTIONS_MAP_NUMS = (1, 2, 3, 4)    # the options on the deck's 07 · 03 map; colours = director_plot STYLE["cluster_colors"] in OPTION_COLOR_ORDER
OPTION_COLOR_ORDER = {1: 1, 2: 3, 3: 2, 4: 4}   # option -> palette key: 1 red, 2 blue, 3 magenta, 4 dark orange -- so the two adjacent options in
                                                 # each inset (1 & 2 overlap; 3 & 4 meet at Gwillim Lake) are never red next to magenta (Ethan 2026-09-28)


def option_color(num):
    """The y2y cluster-palette colour an option draws in (OPTION_COLOR_ORDER; the palette itself is director_plot's)."""
    import director_plot as dp
    return dp.STYLE["cluster_colors"].get(OPTION_COLOR_ORDER.get(num, num), OPTIONS_COLOR)


def propose_examples(P, n_south=3, n_north=2):
    """Spec 06 §2 (v1.2.18, patch D26–D31): the RULE-BASED proposal for the example slots, printed for signing into
    EXAMPLE_PICKS (the pins govern the deck; regeneration is expected on run003).
      S1–S3: links in the top class ("only viable connection", D23: no alternative link, one branch AND narrow -- classify_links'
             `link_class == "both"`; on a run classified before D23 the old both-senses flag, which the printout says), ranked by squeeze_ratio_obs
             ascending (most constrained first), ties by width_ratio_p10, then by criticality (n_pairs_lost desc). Fewer than
             n_south in the top class -> filled from "last affordable link" ranked by width_ratio_p10 ascending; the class is
             stated per pick. Criticality is no longer the primary key.
      N2–N3: unchanged rule -- n_branches (relative floor, D26) x axis-C attribution, ties toward links whose branches fall
             in different jurisdictions.
    Returns a DataFrame (slot, edge_id, pair, class, the ranking columns)."""
    e = P.edges.copy(); e["class"] = [P.cls.get(k, "securing") for k in e.index]
    for col in ("squeeze_ratio_obs", "width_ratio_p10", "n_pairs_lost", "n_branches"):
        if col not in e.columns:
            e[col] = np.nan
    def _rank(d, keys):
        return d.sort_values(keys, ascending=[True, True, False][:len(keys)], na_position="last")
    top = _rank(e[e["class"] == "both"], ["squeeze_ratio_obs", "width_ratio_p10", "n_pairs_lost"])
    rows = [dict(slot=f"S{i+1}", edge_id=k, pair=_pair_title(e.loc[k]), cls="both") for i, k in enumerate(top.index[:n_south])]
    if len(rows) < n_south:
        fill = _rank(e[e["class"] == "edge"], ["width_ratio_p10", "squeeze_ratio_obs", "n_pairs_lost"])
        for k in fill.index[:n_south - len(rows)]:
            rows.append(dict(slot=f"S{len(rows)+1}", edge_id=k, pair=_pair_title(e.loc[k]), cls="edge (filled: fewer than %d in the top class)" % n_south))
    attr = getattr(P, "attr", None)
    att = lambda k: float(attr.get(k, 0.0)) if isinstance(attr, (dict, pd.Series)) and k in attr else 0.0
    jur = getattr(P, "jur", None)
    njur = lambda k: len(set(jur.get(k, []))) if isinstance(jur, dict) and k in jur else (len(set(jur.loc[k])) if isinstance(jur, pd.Series) and k in jur.index else 0)
    north = e[(e["class"] != "adjacency") & (e["n_branches"].fillna(0) >= 2)].copy()
    north["score"] = north["n_branches"].fillna(0) * [att(k) for k in north.index]; north["n_jur"] = [njur(k) for k in north.index]
    north = north.sort_values(["score", "n_jur"], ascending=[False, False])
    for i, k in enumerate(north.index[:n_north]):
        rows.append(dict(slot=f"N{i+2}", edge_id=k, pair=_pair_title(e.loc[k]), cls=e.loc[k, "class"]))
    out = pd.DataFrame(rows)
    keep = [c for c in ("squeeze_ratio_obs", "width_ratio_p10", "n_pairs_lost", "n_branches", "alt_kind") if c in e.columns]
    out = out.join(e[keep], on="edge_id")
    src = "D23 land-aware top class (classify_links)" if "link_class" in P.R.edges.columns else "the RETIRED both-senses flag (run classified before D23)"
    print(f"proposed example slots (spec 06 §2 v1.2.18 -- class-and-width-first; top class = {src}; sign into EXAMPLE_PICKS):")
    print(out.to_string(index=False))
    # G18 / the pin rule: a pinned example that was only-viable under the retired rule and is not under D23 (classify_links'
    # G18 list in run_config) is a post-pin class change -- said here, logged by hand
    lost = set((getattr(P.R, "rec", {}) or {}).get("g18", {}).get("old_rule_only_viable_now_last_affordable", []))
    moved = [f"{ex['slot']} {ex['title']} -> {P.cls.get(ex['edge_id'])}" for ex in getattr(P, "examples", []) if ex.get("edge_id") in lost]
    if moved:
        print("  G18 pin check: pinned example(s) lost the top class under D23 -> the 06 regeneration rule fires: " + "; ".join(moved))
    elif lost:
        print(f"  G18: {len(lost)} link(s) lost the top class under D23, none of them pinned")
    near = [f"{ex['slot']} {ex['title']} ({k}: {P.cls.get(k)})" for ex in getattr(P, "examples", [])
            for k in ([ex.get("edge_id")] + list(ex.get("option_edges", []))) if k is not None and str(P.cls.get(k, "")).startswith("near_contiguous")]
    if near:
        print("  D25 pin check: pinned example link(s) are now near-contiguous (no corridor to design) -> the pin rule fires: " + "; ".join(dict.fromkeys(near)))
    return out


def _find_edge(e, pair):
    """The edge for a pinned example pair (two name fragments). Under D22 (2026-09-28: within-name parts are their own routing
    units, labelled 'name [part k]') a pair can match several part-level edges: prefer the MST edge, then the cheapest, and say
    which was taken -- the pick stays reviewable in the printed line."""
    a, b = pair
    m = e[(e.label_i.str.contains(a, regex=False) & e.label_j.str.contains(b, regex=False)) |
          (e.label_i.str.contains(b, regex=False) & e.label_j.str.contains(a, regex=False))]
    assert len(m) >= 1, f"example pair {pair} resolves to no edge"
    if len(m) > 1:
        order = m.assign(_mst=(m["in_mst"] == True) if "in_mst" in m.columns else False).sort_values(["_mst", "cost"], ascending=[False, True])
        print(f"  example pair {pair}: {len(m)} part-level edges -> {order.index[0]} ({order.iloc[0].label_i} ↔ {order.iloc[0].label_j}; "
              f"{'MST' if order.iloc[0]._mst else 'backup'}, cost {order.iloc[0].cost:,.0f})")
        return order.index[0]
    return m.index[0]


def select_examples(P, n=None, south_of_frac=0.40):
    """Ethan's pinned examples (EXAMPLE_PICKS), numbered in list order: every OPTION of a
    multi-option example gets its own number (N2 = 1, 2), a single link one number (3, 4, ...;
    see the EXAMPLE_PICKS comment). A link example carries `num` (a string such as "1–2" for a multi-option
    example) for its profile page, T1 row and deck slide. Remaining both-senses links go to
    the appendix."""
    R, e = P.R, P.edges
    ex = []                      # N1 (the Dene with/without pair, M4) AXED by Ethan 2026-09-09
    counter = 0
    for pk in EXAMPLE_PICKS:
        eid = _find_edge(e, pk["pair"])
        x = dict(slot=pk["slot"], act=pk["act"], edge_id=eid, kind="link", title=_pair_title(e.loc[eid]),
                 side=pk.get("side", "nw"), mark=pk.get("mark", True))
        if pk.get("options") == "branches":
            k = int(e.loc[eid].get("n_branches", 1) or 1)
            x["options"] = "branches"; x["option_nums"] = list(range(counter + 1, counter + k + 1))
        elif pk.get("options") == "links":
            ids = [_find_edge(e, q) for q in pk["option_pairs"]]
            x["options"] = "links"; x["option_edges"] = ids
            x["option_nums"] = list(range(counter + 1, counter + len(ids) + 1))
        else:
            x["option_nums"] = [counter + 1]
        counter = x["option_nums"][-1]
        x["num"] = (str(x["option_nums"][0]) if len(x["option_nums"]) == 1
                    else f"{x['option_nums'][0]}–{x['option_nums'][-1]}")
        if "squeeze_ratio_obs" in e.columns and P.cls.get(eid) == "squeezed":
            x["headline"] = f"already at {e.loc[eid, 'squeeze_ratio_obs']:.1f}× its natural width"
        ex.append(x)
    used = {x["edge_id"] for x in ex}
    both = e[P.cls == "both"].sort_values(["n_pairs_lost", "backup_ratio"], ascending=False)
    P.appendix_both = [k for k in both.index if k not in used]
    return ex


def _example_label(ex):
    return f"{ex['num']} — {ex['title']}" if ex.get("num") else f"{ex['slot']} — {ex['title']}"


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


# ================= director basemap (y2y-wide conventions) =================
# Coast light grey, admin-1 lines grey, Canada-US border dark, province NAMES (the y2y package
# uses postal codes; directors asked for names), prominent cities, and the biggest named areas
# labelled -- all from the Natural Earth admin-1 polygons already in input_data/basemap/.
ADMIN_POLY = config.INPUT_DIR / "basemap" / "ne_10m_admin_1_states_provinces.shp"
# Mackenzie dropped 2026-09-09: its label sat on the Pine Le Moray links whichever side it went
MAJOR_TOWNS = ["Whitehorse", "Dawson City", "Watson Lake", "Fort Nelson", "Fort St. John",
               "Dawson Creek", "Prince George", "Terrace", "Smithers"]
PROVINCE_LABEL = {"British Columbia": "BRITISH COLUMBIA", "Yukon": "YUKON",
                  "Northwest Territories": "NORTHWEST\nTERRITORIES", "Alberta": "ALBERTA",
                  "Alaska": "ALASKA"}


def _admin(P, pad_m=500e3):
    """Cached admin layer clipped to the routing window (+pad): coast, admin-1 lines, the shared
    Canada-US border, and province label points inside the window."""
    if getattr(P, "_admin", None) is not None:
        return P._admin
    from shapely.geometry import box as _box
    R = P.R
    xs, ys = R.template.x.values, R.template.y.values
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    bbox = _box(x0 - pad_m, y0 - pad_m, x1 + pad_m, y1 + pad_m)
    g = gpd.read_file(ADMIN_POLY).to_crs(R.crs)
    g = g[g.intersects(bbox)].copy(); g["geometry"] = g.geometry.intersection(bbox)
    countries = g.dissolve(by="admin").reset_index()
    coast = countries.geometry.boundary
    border = None
    if len(countries) >= 2:
        b = [c.buffer(500) for c in countries.geometry.boundary]
        border = b[0]
        for bb in b[1:]:
            border = border.intersection(bb)
    lines = gpd.read_file(config.INPUT_DIR / "basemap" / "ne_10m_admin_1_states_provinces_lines.shp") \
        .to_crs(R.crs)
    lines = lines[lines.intersects(bbox)].copy(); lines["geometry"] = lines.geometry.intersection(bbox)
    inner = _box(x0, y0, x1, y1)
    lab = g.copy(); lab["geometry"] = lab.geometry.intersection(inner)
    lab = lab[~lab.geometry.is_empty].copy()
    # only provinces that occupy a meaningful share of the window (a border sliver -- Alberta
    # here -- gets no label: it would land on whatever city sits at the window edge)
    win_area = (x1 - x0) * (y1 - y0)
    lab = lab[lab.geometry.area / win_area >= 0.04].copy()
    # place each name on EMPTY land: the province clipped to the window minus a 35 km buffer
    # around every named area, so the label never sits on the PA/IPCA cluster
    parts = gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(R.crs)
    busy = parts.geometry.buffer(35_000).union_all()
    # the labelled cities are busy too (a 13 pt province name spans ~200 km at region scale)
    from shapely.geometry import Point
    tr = pyproj.Transformer.from_crs("EPSG:4326", R.crs, always_xy=True)
    for n in MAJOR_TOWNS:
        if n in cc._TOWNS:
            lat, lon = cc._TOWNS[n]
            busy = busy.union(Point(*tr.transform(lon, lat)).buffer(40_000))
    pts = []
    for geom in lab.geometry:
        free = geom.difference(busy)
        if not free.is_empty and free.area > 0.25 * geom.area:
            # largest free piece, then its pole of inaccessibility (centre of the biggest
            # inscribed circle) so the name sits in the MOST open country, not merely off-cluster
            pieces = list(free.geoms) if hasattr(free, "geoms") else [free]
            free = max(pieces, key=lambda q: q.area)
            try:
                import shapely
                pts.append(Point(shapely.maximum_inscribed_circle(free, 5_000).coords[0]))
            except Exception:
                pts.append(free.representative_point())
        else:
            pts.append(geom.representative_point())
    lab["pt"] = pts
    nm = "name_en" if "name_en" in lab.columns else "name"
    P._admin = SimpleNamespace(coast=coast, lines=lines, border=border,
                               labels=lab[[nm, "pt"]].rename(columns={nm: "name"}))
    return P._admin


AREA_OVERRIDES = {"Tū Łī́dlini": "Tū Łī́dlini (Ross River)",
                  "Northern Rocky": ("Northern Rocky Mountains", 25_000, -30_000),
                  "Dune Za Keyih": "Dune Za Keyih",
                  # the PA layer's name string is mis-encoded ("Nj ‘Iinlii” Jjik"); display the
                  # park's spelling. DISPLAY ONLY -- the node id / tables keep the source string.
                  "Nj ‘Iinlii": ("Ni’iinlii Njik (Fishing Branch)", 40_000, 30_000),
                  "Neah": "Ne’āh’", "Liard River": "Liard River Corridor"}
# which side of the dot a city label goes (default right); left where the right side is corridor
TOWN_LABEL_SIDE = {"Prince George": "left"}


def _director_base(P, ax, XL, YL, tint=False, province_names=True, cities=True, area_names=14,
                   area_overrides=AREA_OVERRIDES, towns=None):
    """The shared director backdrop: (optional) province tint, coast/admin/border lines, PA + IPCA
    fills, Y2Y outline, province names, prominent cities, biggest named areas."""
    import matplotlib.patheffects as pe
    R = P.R
    A = _admin(P)
    if tint and P.prov_raster is not None:
        pal = ["#eef3f7", "#f5efe6", "#eaf2ea", "#f3eaf2", "#f7f1e1"]
        for i in range(1, len(P.prov_names) + 1):
            m = P.prov_raster == i
            if m.any():
                cc._da(R, np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(
                    ax=ax, cmap=ListedColormap([pal[(i - 1) % len(pal)]]), add_colorbar=False)
    for geom in A.coast:
        gpd.GeoSeries([geom], crs=R.crs).plot(ax=ax, color="#b5b5b5", linewidth=0.5, zorder=0.3)
    A.lines.plot(ax=ax, color="#8c8c8c", linewidth=0.6, zorder=0.32)
    if A.border is not None:
        gpd.GeoSeries([A.border], crs=R.crs).plot(ax=ax, color="#4a4a4a", linewidth=1.0, zorder=0.35)
    for layer, col in [(R.pa_mask, PA_COLOR), (R.anch, ANCHOR_COLOR)]:
        cc._da(R, np.where(layer, 1.0, np.nan).astype("float32")).plot.imshow(
            ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
    # thin BLACK hairline around every NAMED area (parts dissolved by name), so adjoining PAs /
    # IPCAs read as distinct polygons even where they share a border -- black, not white, so a
    # shared border cannot be mistaken for a real gap between two areas (Ethan, 2026-09-10)
    if getattr(P, "_names_gdf", None) is None:
        P._names_gdf = (gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(R.crs)
                        .dissolve(by="name_label").reset_index())
    P._names_gdf.boundary.plot(ax=ax, color="black", linewidth=0.45, zorder=2.5)
    R.outline.boundary.plot(ax=ax, color="0.35", linewidth=1.0, linestyle="--", zorder=3)
    if province_names:
        for _, r in A.labels.iterrows():
            if XL[0] < r.pt.x < XL[1] and YL[0] < r.pt.y < YL[1]:
                ax.text(r.pt.x, r.pt.y, PROVINCE_LABEL.get(r["name"], str(r["name"]).upper()),
                        fontsize=13, color="#555555", alpha=0.75, ha="center", va="center",
                        zorder=4.5, fontweight=600,
                        path_effects=[pe.withStroke(linewidth=3, foreground="white", alpha=0.8)])
    if cities:
        if not hasattr(R, "_towns"):
            cc._draw_basemap(R, ax, XL, YL, towns=False)     # warms R._towns; borders already drawn
        for n, x, y in R._towns:
            if n in (towns or MAJOR_TOWNS) and XL[0] < x < XL[1] and YL[0] < y < YL[1]:
                ax.plot(x, y, marker="o", ms=5, color="0.1", mec="white", mew=1.0, zorder=6)
                left = TOWN_LABEL_SIDE.get(n) == "left"
                ax.annotate(n, (x, y), xytext=(-5 if left else 5, 4), textcoords="offset points",
                            ha="right" if left else "left", fontsize=8.5,
                            color="0.1", zorder=6, fontweight=600,
                            path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
    if area_names:
        cc.label_named_areas(R, ax, top_n=area_names, overrides=area_overrides, fontsize=8.5,
                             XL=XL, YL=YL, ipca_color="#1a6363", pa_color="0.25")
    ax.set_xlim(*XL); ax.set_ylim(*YL); ax.set_aspect("equal"); ax.set_axis_off()


def adjacent_sentence(P, prefix=""):
    """Spec 06 §2 (D25a patch): 'N of the sector's links join areas that are effectively adjacent; corridor design in the north is a
    question about the remaining M.' Empty on a run classified before D25."""
    if not any(str(v).startswith("near_contiguous") for v in P.cls.values):
        return ""
    n_near = int(P.cls.astype(str).str.startswith("near_contiguous").sum()); n_links = int((P.cls != "adjacency").sum())
    return f"{prefix}{n_near} of the sector's {n_links} links join areas that are effectively adjacent; corridor design in the north is a question about the remaining {n_links - n_near}"


def _paint_near_contiguous(P, ax):
    """D25: the near-contiguous links' bands in the neutral grey with the mapstyle hatch (contourf carries the hatch; imshow
    cannot), the barrier variant outlined. Returns the two legend handles (empty list on a run without the class)."""
    import corridors_mapstyle as ms
    R = P.R; handles = []
    for c in NEAR_CONTIGUOUS_KEYS:
        ids = list(P.cls.index[P.cls == c])
        if not ids:
            continue
        m = np.isin(P.owner, [P.order[k] for k in ids if k in P.order]) & R.corridor
        if not m.any():
            continue
        tok = ms.NEAR_CONTIGUOUS[c]
        cc._da(R, np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(ax=ax, cmap=ListedColormap([tok["fill"]]), add_colorbar=False)
        with plt.rc_context({"hatch.color": tok["hatch_color"], "hatch.linewidth": 0.5}):
            ax.contourf(R.template.x.values, R.template.y.values, m.astype(float), levels=[0.5, 1.5], colors="none", hatches=[tok["hatch"]])
        if tok["outline"]:
            ax.contour(R.template.x.values, R.template.y.values, m.astype(float), levels=[0.5], colors=[tok["outline"][0]], linewidths=tok["outline"][1],
                       linestyles=[tok["outline"][2] if len(tok["outline"]) > 2 else "solid"])
        handles.append(Patch(facecolor=tok["fill"], hatch=tok["hatch"], edgecolor=(tok["outline"][0] if tok["outline"] else tok["hatch_color"]),
                             linewidth=(tok["outline"][1] if tok["outline"] else 0.0), linestyle=(tok["outline"][2] if tok["outline"] and len(tok["outline"]) > 2 else "solid"),
                             label=f"{CLASS[c][1]}  [{len(ids)}]"))
    return handles


def _paint_classes(P, ax):
    """The four corridor classes in the M1 palette (squeezed folded into securing while H8 is open), over the near-contiguous
    rows (D25, neutral hatch, drawn first). Returns the legend handles in legend order: the four, then the adjacent rows."""
    nc_handles = _paint_near_contiguous(P, ax)
    handles = []
    for c in ("securing", "squeezed", "edge", "both"):
        ids = list(P.cls.index[P.cls == c])
        if c == "squeezed" and P.h8_open:
            ids = []
        if c == "securing" and P.h8_open:
            ids += list(P.cls.index[P.cls == "squeezed"])
        col, lbl = CLASS[c]
        _paint(P, ax, ids, col)
        if not (c == "squeezed" and P.h8_open):
            handles.append(Patch(color=col, label=f"{lbl}  [{len(ids)}]"))
    return handles + nc_handles


def _m1_scale(P):
    """Map scale of M1 in metres per inch of axes (M1 is height-limited on its 12x17 page)."""
    XL, YL = cc._region_extent(P.R, 0.07)
    return max((XL[1] - XL[0]) / (0.96 * 12), (YL[1] - YL[0]) / (0.87 * 17))


def _crop_extent(P, y_from=None, y_to=None, pad_km=15):
    """Bounding box of everything drawn (PAs, IPCAs, corridor land) whose cells lie between
    y_from and y_to (map units), padded. The aspect is free: the crop is drawn at M1's SCALE."""
    R = P.R
    xs, ys = R.template.x.values, R.template.y.values
    content = R.pa_mask | R.anch | R.corridor
    rows = np.nonzero(content.any(axis=1))[0]
    if y_from is not None:
        rows = rows[ys[rows] >= y_from]
    if y_to is not None:
        rows = rows[ys[rows] <= y_to]
    cols = np.nonzero(content[rows].any(axis=0))[0]
    p = pad_km * 1e3
    return ((xs[cols.min()] - p, xs[cols.max()] + p), (ys[rows].min() - p, ys[rows].max() + p))


def _crop_figure(P, XL, YL, legend_in=1.9, title_in=0.8, min_w_in=12.0):
    """Figure + axes sized so the crop renders at exactly M1's scale; legend room below."""
    sc = _m1_scale(P)
    w, h = (XL[1] - XL[0]) / sc, (YL[1] - YL[0]) / sc
    fw, fh = max(w + 0.6, min_w_in), h + legend_in + title_in
    fig = plt.figure(figsize=(fw, fh))
    ax = fig.add_axes([(fw - w) / 2 / fw, legend_in / fh, w / fw, h / fh])
    return fig, ax


def _polys_y(P, fragments):
    """Min/max y over the named-area polygons whose label contains any of the fragments."""
    parts = gpd.read_file(P.R.run_dir / "node_parts.gpkg").to_crs(P.R.crs)
    sel = parts[parts.name_label.apply(lambda l: any(f in str(l) for f in fragments))]
    b = sel.total_bounds
    return b[1], b[3]


def _median_cell(R, m):
    """Median cell of the LARGEST 8-connected piece of m (a link's owned land can be several
    pieces, and the median of all of them can fall in the gap between)."""
    from scipy import ndimage
    rr, cc_ = np.nonzero(m)
    if not len(rr):
        return None
    lab, n = ndimage.label(m, structure=np.ones((3, 3)))
    if n > 1:
        big = 1 + int(np.argmax(ndimage.sum(m, lab, range(1, n + 1))))
        rr, cc_ = np.nonzero(lab == big)
    return R.template.x.values[int(np.median(cc_))], R.template.y.values[int(np.median(rr))]


def _number_marker(ax, xy, num, color, XL, YL, side="nw"):
    x, y = xy
    if XL[0] < x < XL[1] and YL[0] < y < YL[1]:
        dx = 22 if side in ("ne", "se") else -22
        dy = 22 if side in ("ne", "nw") else -22
        ax.annotate(str(num), (x, y), xytext=(dx, dy),
                    textcoords="offset points",
                    fontsize=11, fontweight=600, ha="center", va="center", zorder=8,
                    bbox=dict(boxstyle="circle,pad=0.3", fc="white", ec=color, lw=1.8),
                    arrowprops=dict(arrowstyle="-", color=color, lw=1.2, shrinkB=0))
        return True
    return False


def _marker_handle(nums):
    return plt.Line2D([0], [0], marker="o", color="none", markerfacecolor="white",
                      markeredgecolor="0.2", markersize=10,
                      label=f"Example links {', '.join(str(n) for n in nums)} "
                            "(profiles and table T1)")


# ================= maps M1-M4 =================
def map_m1(P, pad=0.07, area_names=14):
    """M1 -- the four-class regime map (the main plot): flat swaths on the director basemap
    (province names, prominent cities, biggest PA/IPCA names), legend BELOW the map so it covers
    nothing. Squeezed class withheld (drawn as securing) while H8 is open."""
    R = P.R
    XL, YL = cc._region_extent(R, pad)
    fig = plt.figure(figsize=(12, 17))
    ax = fig.add_axes([0.02, 0.09, 0.96, 0.87])
    handles = _paint_classes(P, ax)
    _director_base(P, ax, XL, YL, area_names=area_names)
    handles += _node_handles()
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.01), ncol=2,
               fontsize=9.5, frameon=True)
    ax.set_title("Where the land still offers choices — and where it does not" + adjacent_sentence(P, prefix="\n"), fontsize=15,
                 pad=12)
    fig.savefig(P.fig / "M1_regime.png", dpi=170, bbox_inches="tight"); plt.show()
    return P


def map_adjacency(P, adjacency_dir=None, pad=0.07, area_names=14, show_degree=True):
    """M1b -- M1 beside the NEIGHBOUR UNIVERSE (D21): left = the four-class regime map, right =
    the same basemap with every cost-allocation neighbour link drawn as a LINE between area
    centres (adjacency-only thin blue; backbone backups dashed; MST links heavy) and each area's
    neighbour count. Lines, never bands: the difference between the two panels is the choice
    space. Reads adjacency_edges/nodes.csv from the run dir (notebook 04 step 0b) unless
    `adjacency_dir` points elsewhere."""
    R = P.R
    adir = pathlib.Path(adjacency_dir) if adjacency_dir else R.run_dir
    fe, fn = adir / "adjacency_edges.csv", adir / "adjacency_nodes.csv"
    if not fe.exists():
        print(f"  adjacency products not found in {adir} -- run notebook 04 (step 0b) first"); return None
    adj, nodes = pd.read_csv(fe), pd.read_csv(fn)
    XL, YL = cc._region_extent(R, pad)
    fig = plt.figure(figsize=(24, 17))
    axL = fig.add_axes([0.01, 0.09, 0.485, 0.87]); axR = fig.add_axes([0.505, 0.09, 0.485, 0.87])
    handles = _paint_classes(P, axL)
    _director_base(P, axL, XL, YL, area_names=area_names)
    axL.set_title("Where the land still offers choices — and where it does not", fontsize=15, pad=12)
    # right panel: NO area names -- the neighbour-count circles sit at the same points and the
    # left panel already names every area at the same position
    _director_base(P, axR, XL, YL, area_names=0)
    # area centres: the largest polygon of each name (a multipart name's midpoint can fall between parts)
    names = gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(R.crs).dissolve(by="name_label").reset_index()
    cent = {}
    for _, r in names.iterrows():
        g = r.geometry
        big = max(g.geoms, key=lambda q: q.area) if hasattr(g, "geoms") else g
        pt = big.representative_point(); cent[str(r["name_label"])] = (pt.x, pt.y)
    def xy(lbl):
        if lbl in cent:
            return cent[lbl]
        k = next((n for n in cent if n.startswith(str(lbl)[:24])), None)
        return cent.get(k)
    n_lines = {"adj": 0, "backup": 0, "mst": 0}
    for r in adj.itertuples():
        if r.edge_class == "intra_name" or not (r.is_adjacent or r.in_backbone):
            continue
        a, b = xy(r.label_i), xy(r.label_j)
        if a is None or b is None:
            continue
        if r.in_backbone and r.in_mst:
            axR.plot([a[0], b[0]], [a[1], b[1]], color="0.15", lw=2.0, zorder=4); n_lines["mst"] += 1
        elif r.in_backbone:
            axR.plot([a[0], b[0]], [a[1], b[1]], color="0.3", lw=1.4, ls="--", zorder=4); n_lines["backup"] += 1
        else:
            axR.plot([a[0], b[0]], [a[1], b[1]], color=OPTIONS_COLOR, lw=0.9, alpha=0.85, zorder=3.5); n_lines["adj"] += 1
    if show_degree:
        import matplotlib.patheffects as pe
        for r in nodes.itertuples():
            c = xy(r.label)
            if c is not None and XL[0] < c[0] < XL[1] and YL[0] < c[1] < YL[1]:
                axR.annotate(str(int(r.n_neighbours)), c, fontsize=7.5, fontweight=600, ha="center",
                             va="center", zorder=7, color="0.1",
                             bbox=dict(boxstyle="circle,pad=0.22", fc="white", ec="0.4", lw=0.7, alpha=0.95))
    axR.set_title("The neighbour universe — every possible partner link", fontsize=15, pad=12)
    handles += [plt.Line2D([0], [0], color=OPTIONS_COLOR, lw=1.2, label=f"Possible partner link not in the network — neighbouring areas [{n_lines['adj']}]"),
                plt.Line2D([0], [0], color="0.3", lw=1.4, ls="--", label=f"Backup link in the network [{n_lines['backup']}]"),
                plt.Line2D([0], [0], color="0.15", lw=2.0, label=f"Minimum-network link [{n_lines['mst']}]"),
                plt.Line2D([0], [0], marker="o", color="none", markerfacecolor="white", markeredgecolor="0.4",
                           markersize=9, label="Number of neighbouring areas")]
    handles += _node_handles() + [plt.Line2D([0], [0], color="0.35", lw=1.0, ls="--", label="Y2Y corridor")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.01), ncol=3, fontsize=9.5, frameon=True)
    fig.text(0.5, 0.075, "Left: the minimum network plus affordable backups, classed by the tests. Right: every pair of areas "
                         "whose cost-allocation zones touch (lines join area centres; no corridor is drawn for them). "
                         "The difference between the two is the choice space.", ha="center", fontsize=10, color="#333333")
    fig.savefig(P.fig / "M1b_adjacency_pair.png", dpi=150, bbox_inches="tight"); plt.show()
    return adj


# ================= GIS export (for ArcGIS Pro / QGIS rendering; Ethan 2026-09-14) =================
def export_gis(P, out=None):
    """Write the director package's layers as GIS-ready files with the presentation attributes
    attached, so the figures can be rebuilt in ArcGIS Pro: corridor_pressure.gpkg (owner-partition
    polygons per link with the four-class attribute + hex), areas.gpkg (PAs / IPCAs by name with
    kind + hex), options.gpkg (the numbered options 1-6), and style.json (every colour used).
    Rasters are NOT copied -- resistance.tif (cost 1/10/100/1000), edge_owner.tif, corridors.tif
    and the hillshade are referenced by path in style.json."""
    import corridors_mapstyle as ms
    from rasterio import features as rfeatures
    from shapely.geometry import shape as _shape
    R = P.R
    out = pathlib.Path(out) if out else P.out / "gis"; out.mkdir(parents=True, exist_ok=True)
    tr = R.template.rio.transform()
    # 1. corridor pressure: owner partition -> one multipolygon per link, class attached
    pressure = _pressure_polygons(P)
    rows = pressure.to_dict("records")
    pressure.to_file(out / "corridor_pressure.gpkg", driver="GPKG")
    # 2. areas
    names = gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(R.crs).dissolve(by="name_label").reset_index()
    names["kind"] = np.where(names.name_label.str.startswith("IPCA"), "Proposed IPCA", "Existing Protected Area")
    names["hex"] = np.where(names.kind == "Proposed IPCA", ms.AREA["ipca"]["fill"], ms.AREA["pa"]["fill"])
    names["display_name"] = [cc._short_node_name(n, 40) for n in names.name_label]
    names[["name_label", "display_name", "kind", "hex", "area_km2", "geometry"]].to_file(out / "areas.gpkg", driver="GPKG")
    # 3. options 1-6
    orows = []
    for num, title, m, col in _option_masks(P):
        if not isinstance(num, int) or not m.any():
            continue
        polys = [_shape(g) for g, v in rfeatures.shapes(m.astype("uint8"), mask=m, transform=tr) if v == 1]
        orows.append(dict(option=num, title=title.replace(chr(10), " — "), km2=round(float(m.sum()) * R.cell_km2, 1),
                          geometry=gpd.GeoSeries(polys, crs=R.crs).union_all()))
    if orows:
        gpd.GeoDataFrame(orows, crs=R.crs).to_file(out / "options.gpkg", driver="GPKG")
    # 4. style sheet
    style = dict(
        crs="ESRI:102008 (North America Albers Equal Area Conic); rasters 300 m",
        cost_surface=dict(raster=str(R.run_dir / "resistance.tif"), values="unique: 1, 10, 100, 1000 (nodata -1)",
                          swatches={str(c): dict(hex=ms.COST[c][0], label=ms.COST[c][1]) for c in (1, 10, 100, 1000)}),
        corridor_pressure=dict(vector=str(out / "corridor_pressure.gpkg"), field="pressure",
                               classes={c: dict(hex=ms.CLASS[c][0], label=ms.CLASS[c][3]) for c in ms.CLASS_ORDER},
                               raster_alternative=dict(owner=str(R.run_dir / "edge_owner.tif"), mask=str(R.run_dir / "corridors.tif"),
                                                       join="edge index in corridor_edges.csv (row order) -> pressure via corridor_pressure.gpkg")),
        areas=dict(vector=str(out / "areas.gpkg"), field="kind", fill_opacity=0.55,
                   ipca=dict(hex=ms.AREA["ipca"]["fill"], outline=ms.AREA["ipca"]["edge"]),
                   pa=dict(hex=ms.AREA["pa"]["fill"], outline=ms.AREA["pa"]["edge"])),
        options=dict(vector=str(out / "options.gpkg"), hex=OPTIONS_COLOR),
        basemap=dict(land=ms.BASE["land"], ocean=ms.BASE["ocean"], water=ms.BASE["water"],
                     hillshade=str(ms.BASEMAP_DIR / "hillshade_300m.tif") + " (multiply, 18% opacity)",
                     admin_lines=str(ms.BASEMAP_DIR / "ne_10m_admin_1_states_provinces_lines.shp"),
                     lakes=[str(ms.BASEMAP_DIR / f) for f in ("ne_10m_lakes.shp", "ne_10m_lakes_north_america.shp")],
                     rivers=[str(ms.BASEMAP_DIR / f) for f in ("ne_10m_rivers_lake_centerlines.shp", "ne_10m_rivers_north_america.shp")],
                     y2y_boundary=str(config.CORRIDOR_REF)),
        fonts="Noto Sans (input_data/basemap/fonts)", type=ms.TYPE,
    )
    (out / "style.json").write_text(json.dumps(style, indent=2, ensure_ascii=False))
    print(f"GIS export -> {out}: corridor_pressure.gpkg ({len(rows)} links), areas.gpkg ({len(names)}), "
          f"options.gpkg ({len(orows)}), style.json")
    return out


def _pressure_polygons(P):
    """Owner partition -> one multipolygon per link with the pressure class attached (shared by
    the northern and the wolverine GIS exports)."""
    import corridors_mapstyle as ms
    from rasterio import features as rfeatures
    from shapely.geometry import shape as _shape
    R = P.R
    tr = R.template.rio.transform()
    rows = []
    for eid, k in P.order.items():
        m = (P.owner == k) & R.corridor
        if not m.any():
            continue
        c = P.cls.get(eid, "securing")
        if c == "adjacency":
            continue
        polys = [_shape(g) for g, v in rfeatures.shapes(m.astype("uint8"), mask=m, transform=tr) if v == 1]
        e = R.edges.loc[eid]
        if c in ms.CLASS:
            label, hx = ms.CLASS[c][3], ms.CLASS[c][0]
        else:                                                    # D25 near-contiguous rows: the mapstyle's neutral tokens
            tok = ms.NEAR_CONTIGUOUS.get(c, {}); label, hx = tok.get("label", c), tok.get("fill", "#D9D9D9")
        nb = e.get("n_branches", np.nan)
        rows.append(dict(edge_id=eid, label_i=e["label_i"], label_j=e["label_j"], pressure=c,
                         pressure_label=label, hex=hx, cost=float(e["cost"]),
                         in_mst=bool(e["in_mst"]), irreplaceable=bool(e.get("irreplaceable", False)),
                         route_irreplaceable=bool(e.get("route_irreplaceable", False)),
                         squeezed=bool(e.get("squeezed", False)) if pd.notna(e.get("squeezed", np.nan)) else False,
                         squeeze_ratio=float(e.get("squeeze_ratio_obs", np.nan)),
                         n_branches=(int(nb) if pd.notna(nb) else -1),         # -1 = no decomposition (near-contiguous, D25)
                         band_km2=round(float(m.sum()) * R.cell_km2, 1),
                         geometry=gpd.GeoSeries(polys, crs=R.crs).union_all()))
    return gpd.GeoDataFrame(rows, crs=R.crs)


# ================= cartographic contract figures (spec 06 §3a; corridors_mapstyle) =================
import corridors_mapstyle as ms

# Figure spec row for M0b (hand-placed label list; Ethan signs). <= 10 labels: 5 jurisdictions /
# towns + 5 anchor areas. Jurisdiction points = the pole-of-inaccessibility positions already
# verified on M1 (data coords, ESRI:102008).
M0B_SPEC = dict(
    fig_id="M0b",
    title="Northern Corridors: Movement Cost",
    message="the south is where the cost is",
    # jurisdiction names in lon/lat (hand-placed on open ground for THIS frame)
    jurisdictions=[("YUKON", (-138.6, 62.6)), ("NORTHWEST\nTERRITORIES", (-126.5, 67.2)),
                   ("BRITISH COLUMBIA", (-128.6, 53.9))],
    towns=[("Whitehorse", "right", -5, 0), ("Fort St. John", "left", 5, 2)],
    areas=[("Peel Watershed", "Peel Watershed", 0, 0), ("Nahanni National", "Nahanni", 0, 0),
           ("Tū Łī́dlini", "Tū Łī́dlini (Ross River)", 0, 0), ("Dene K", "Dene Kʼéh Kusān", 0, 0),
           ("Pine Le Moray", "Pine Le Moray", -34, 6)],
)


def _area_point(names, fragment):
    row = names[names.name_label.str.contains(fragment, regex=False)]
    if not len(row):
        return None
    g = row.iloc[0].geometry
    big = max(g.geoms, key=lambda q: q.area) if hasattr(g, "geoms") else g
    pt = big.representative_point(); return (pt.x, pt.y)


def _town_xy(R, name):
    import pyproj
    lat, lon = cc._TOWNS[name]
    return pyproj.Transformer.from_crs("EPSG:4326", R.crs, always_xy=True).transform(lon, lat)


def figure_m0b(P, template="slide", run_tag=None, spec=M0B_SPEC, corridors=False):
    """M0b -- context figure on the §3a slide template: greyscale cost swatches, water in blue,
    PAs + IPCAs, the four corridor classes, boundaries; one legend in the furniture column;
    locator, 100 km scale bar, north. Exports PDF + PNG and runs the §3a.3 QA."""
    ms.apply()
    R = P.R
    fig, ns = ms.new_figure(spec["title"], template, locator=False)
    ax = ns.map
    XL, YL = ms.sector_frame(R, 40)
    ms.draw_land(ax, R, XL, YL)
    ms.draw_water(ax, R, XL, YL, z=ms.Z["cost"] - 0.1)   # under the cost swatches: water = cost-1000 colour inside the sector
    ms.draw_cost(ax, R)
    hs = ms.draw_hillshade(ax, R)
    names = ms.draw_areas(ax, R)
    counts = ms.draw_classes(ax, R, P.owner, P.order, P.cls, P.h8_open) if corridors else {}
    ms.draw_boundaries(ax, R, XL, YL, sector=False)     # Y2Y region boundary only (Ethan)
    ms.set_frame(ax, XL, YL)
    # labels: jurisdictions, then areas, then towns (§1.6)
    import pyproj
    to_map = pyproj.Transformer.from_crs("EPSG:4326", R.crs, always_xy=True)
    for text, (lon, lat) in spec["jurisdictions"]:
        ms.label(ax, ns, text, to_map.transform(lon, lat), "jurisdiction")
    for frag, text, dx, dy in spec["areas"]:
        xy = _area_point(names, frag)
        if xy:
            ms.label(ax, ns, text, xy, "area", dx_pt=dx, dy_pt=dy)
    for t, ha, dx, dy in spec["towns"]:
        ms.town(ax, ns, t, _town_xy(R, t), dx_pt=dx, dy_pt=dy, ha=ha)
    # furniture: one legend, three headings (Ethan): Cost Surface / Corridors / Jurisdictions
    y2y_line = ms.line_handles()[1]
    groups = [("Cost Surface", ms.cost_handles())]
    if corridors:
        groups.append((ms.CLASS_HEADING, [ms.class_handle(c, counts.get(c)) for c in ms.CLASS_ORDER]))
    groups.append(("Jurisdictions", [ms.area_handle("pa"), ms.area_handle("ipca"), y2y_line]))
    ms.legend(ns.legend, groups)
    fig.canvas.draw()
    ms.scale_north(ns.scale, ax, fig)
    cost = R.resistance.values; fin = cost[np.isfinite(cost) & (cost > 0)]
    sh = {int(c): 100 * float((fin == c).sum()) / fin.size for c in (1, 10, 100, 1000)}
    ms.caption(fig, ns,
               f"Movement-cost surface: O'Brien et al. (transboundary extension of Pither et al. 2023), 300 m. Sector shares — intact land {sh[1]:.0f}%, "
               f"roads and cuts {sh[10]:.0f}%, converted land {sh[100]:.1f}%, water, ice and settlement {sh[1000]:.0f}%."
               + (" Corridor classes from the partner, route and squeeze tests (spec 05: D7, D12, D17)." if corridors else "")
               + " Basemap: Natural Earth (public domain)"
               + (", Copernicus GLO-90 hillshade." if hs else "."))
    paths = ms.export(fig, spec["fig_id"], run_tag or R.run_dir.name, P.fig)
    print(f"{spec['fig_id']}: exported " + ", ".join(p.name for p in paths) + f" | font {ms.font_in_use()}")
    ms.qa(fig, ns, paths, message=spec["message"], expected_message=spec["message"])
    plt.show()
    return fig


# ================= insets (shared frames for every map; Ethan 2026-09-11) =================
# Two zoom boxes, defined ONCE from the option land so every map shows the same windows:
#   A = the land around options 1-2 (Nahanni's ways south), B = the land around option 5
#   (Gwillim Lake <-> Pine Le Moray). Panels sit in the page corners the diagonal region leaves
#   empty; each frame is padded and then widened/heightened to its panel's aspect.
INSET_RECTS = {"A": [0.745, 0.50, 0.25, 0.25],       # figure-fraction [left, bottom, width, height]
               "B": [0.025, 0.115, 0.30, 0.25]}       # A east of the region's edge, B in the SW corner
INSET_SPEC = {"A": dict(nums=(1, 2), title="A · options 1–2: Nahanni's ways south", pad_km=25),
              "B": dict(nums=(3,), title="B · option 3: Gwillim Lake ↔ Pine Le Moray", pad_km=25)}   # the same window as before 2026-09-28 (then numbered option 5)


def inset_frames(P, fig_w=12, fig_h=17):
    """{key: (XL, YL, title)} -- bbox of the named options' corridor land + pad, fitted to the
    panel's aspect. Cached on P so every map uses identical windows."""
    if getattr(P, "_inset_frames", None) is not None:
        return P._inset_frames
    R = P.R
    opts = {num: m for num, _, m, _ in _option_masks(P) if isinstance(num, int)}
    xs, ys = R.template.x.values, R.template.y.values
    out = {}
    for key, spec in INSET_SPEC.items():
        m = np.zeros(R.shape, bool)
        for n in spec["nums"]:
            if n in opts:
                m |= opts[n]
        rr, cc_ = np.nonzero(m)
        if not len(rr):
            continue
        p = spec["pad_km"] * 1e3
        x0, x1 = xs[cc_.min()] - p, xs[cc_.max()] + p
        y0, y1 = ys[rr].min() - p, ys[rr].max() + p
        rect = INSET_RECTS[key]
        aspect = (rect[2] * fig_w) / (rect[3] * fig_h)
        w, h = x1 - x0, y1 - y0
        if w / h < aspect:
            cx = 0.5 * (x0 + x1); w = aspect * h; x0, x1 = cx - w / 2, cx + w / 2
        else:
            cy = 0.5 * (y0 + y1); h = w / aspect; y0, y1 = cy - h / 2, cy + h / 2
        out[key] = ((x0, x1), (y0, y1), spec["title"])
    P._inset_frames = out
    return out


def add_insets(P, fig, ax_main, draw, area_names=6, scale_km=50):
    """Place the shared inset panels on a map. `draw(ax, XL, YL, area_names)` must paint the
    map's layers into any axes for the given frame (the same function the main map used)."""
    from mpl_toolkits.axes_grid1.inset_locator import mark_inset
    import matplotlib.patheffects as pe
    for key, (XL, YL, title) in inset_frames(P).items():
        iax = fig.add_axes(INSET_RECTS[key])
        draw(iax, XL, YL, area_names)
        iax.set_axis_on(); iax.set_xticks([]); iax.set_yticks([])
        iax.set_title(""); iax.set_xlabel(""); iax.set_ylabel("")     # xarray's imshow labels
        for sp in iax.spines.values():
            sp.set_visible(True); sp.set_linewidth(1.4); sp.set_color("0.15")
        iax.set_facecolor("white")
        # scale bar + title inside the panel
        w = XL[1] - XL[0]; h = YL[1] - YL[0]
        x0, y0 = XL[1] - 0.05 * w - scale_km * 1e3, YL[0] + 0.06 * h      # bottom-right corner
        iax.plot([x0, x0 + scale_km * 1e3], [y0, y0], color="0.1", lw=2.5, zorder=9,
                 path_effects=[pe.withStroke(linewidth=4.5, foreground="white")])
        iax.text(x0 + scale_km * 500, y0 + 0.025 * h, f"{scale_km} km", ha="center", va="bottom",
                 fontsize=8, zorder=9, path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        iax.text(0.015, 0.975, title, transform=iax.transAxes, ha="left", va="top", fontsize=9,
                 fontweight=600, zorder=9,
                 bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="0.15", lw=0.8, alpha=0.95))
        # box on the main map + connectors (matplotlib draws the box from the inset's data limits)
        # connectors from the two corners tangent to the panel's direction (UL + LR for a panel
        # to the NE or the SW of its box)
        mark_inset(ax_main, iax, loc1=2, loc2=4, fc="none", ec="0.15", lw=1.3, zorder=8)
        ax_main.text(XL[0], YL[1], f" {key}", ha="left", va="bottom", fontsize=10, fontweight=600,
                     zorder=9, path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])


def map_cost(P, pad=0.07, area_names=14, corridors=False, halo_cells=6, insets=True):
    """The movement-cost surface (magma ramp, log colour, four ordinal classes) with existing
    PAs + proposed IPCAs hard-coloured -- the 'what the land is made of' companion to M1, same
    basemap and legend placement; class shares in the subtitle. `corridors=False` -> M0 (no
    corridors); `corridors=True` -> M0b, the four-class network HARD-COLOURED on top of the
    ramp with a thin WHITE HALO (`halo_cells` x 300 m) under every swath so the classes read
    as the figure and never merge with the red/purple part of the ramp; the land between the
    swaths is cost. Region-scale sibling of the zoom overlay `cc.routing_problem_cost_overlay`.
    `insets=True` adds the shared zoom panels (INSET_SPEC) drawn with the same layers."""
    from matplotlib.colors import LogNorm
    from scipy.ndimage import binary_dilation
    R = P.R
    XL, YL = cc._region_extent(R, pad)
    cost = R.resistance.values
    fin = cost[np.isfinite(cost) & (cost > 0)]
    sh = {int(c): 100 * float((fin == c).sum()) / fin.size for c in (1, 10, 100, 1000)}
    cost_da = cc._da(R, np.where(cost > 0, cost, np.nan).astype("float32"))
    layers, union, handles = [], np.zeros(P.owner.shape, bool), []
    if corridors:
        for c in ("securing", "squeezed", "edge", "both"):
            ids = list(P.cls.index[P.cls == c])
            if c == "squeezed" and P.h8_open:
                ids = []
            if c == "securing" and P.h8_open:
                ids += list(P.cls.index[P.cls == "squeezed"])
            col, lbl = CLASS[c]
            m = np.isin(P.owner, [P.order[k] for k in ids if k in P.order]) & R.corridor
            layers.append((m, col)); union |= m
            if not (c == "squeezed" and P.h8_open):
                handles.append(Patch(color=col, label=f"{lbl}  [{len(ids)}]"))
        halo = binary_dilation(union, iterations=halo_cells) & ~union
    else:
        halo = None

    def draw(ax, XL_, YL_, names):
        """Every layer of this map for any frame -- the main map and the insets share it."""
        im_ = cost_da.plot.imshow(ax=ax, cmap="magma_r", norm=LogNorm(vmin=1, vmax=1000), add_colorbar=False)
        if corridors:
            cc._da(R, np.where(halo, 1.0, np.nan).astype("float32")).plot.imshow(
                ax=ax, cmap=ListedColormap(["white"]), add_colorbar=False)
            for m, col in layers:
                if m.any():
                    cc._da(R, np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(
                        ax=ax, cmap=ListedColormap([col]), add_colorbar=False)
        _director_base(P, ax, XL_, YL_, area_names=names)
        return im_

    fig = plt.figure(figsize=(12, 17))
    ax = fig.add_axes([0.02, 0.09, 0.96, 0.87])
    im = draw(ax, XL, YL, area_names)
    if insets:
        add_insets(P, fig, ax, draw)
    # colour bar: horizontal, in the empty south-east corner of the page (the insets take the
    # right margin the vertical bar used to occupy)
    cax = fig.add_axes([0.60, 0.135, 0.36, 0.014])
    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    cb.set_label("cost of moving through the land (log colour scale)\n"
                 "1 intact · 10 roads and cuts · 100 converted land · 1000 water, ice, settlement", fontsize=8.5)
    handles += _node_handles() + [
        plt.Line2D([0], [0], color="0.35", lw=1.0, ls="--", label="Y2Y corridor")]
    if insets:
        handles.append(plt.Line2D([0], [0], color="0.15", lw=1.3, label="Inset frames A, B (same on every map)"))
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.01), ncol=2,
               fontsize=9.5, frameon=True)
    head = ("What the land is made of — the corridor network over the movement-cost surface"
            if corridors else "What the land is made of — the movement-cost surface")
    ax.set_title(f"{head}\n"
                 f"intact land {sh[1]:.0f}% · roads and cuts {sh[10]:.0f}% · converted "
                 f"{sh[100]:.1f}% · water, ice and settlement {sh[1000]:.0f}%", fontsize=14, pad=12)
    name = "M0b_cost_surface_corridors.png" if corridors else "M0_cost_surface.png"
    fig.savefig(P.fig / name, dpi=170, bbox_inches="tight"); plt.show()
    return P


# Crop-map settings for M2 / M3 (restored 2026-09-28: commit 45b949d deleted these three
# constants while adding the §3a contract figures, but map_m2 / map_m3 still use them).
NORTH_TOWNS = MAJOR_TOWNS + ["Mayo", "Ross River", "Faro", "Dease Lake"]
SOUTH_TOWNS = MAJOR_TOWNS + ["Chetwynd", "Tumbler Ridge", "Dease Lake", "Fort St. James"]
# M2's southern edge = the top of this group of named areas (see map_m2's docstring)
M2_SOUTH_LIMIT = ["Mount Edziza", "Spatsizi", "Dene K", "Dune Za Keyih", "Northern Rocky"]


def map_m2(P, area_names=14, tint=False):
    """M2 -- Act 1, the north at M1's MAP SCALE (crop: everything north of the Edziza /
    Spatsizi / Dene Kʼéh Kusān group). Every link in its M1 colour; the Act-1 examples' OPTIONS
    drawn on top in one colour and numbered 1-4: the two route branches of Nahanni ↔ Liard
    River Corridor (1, 2) and the two links from T'akú Tlatsini to the Mount Edziza / Stikine
    complex (3, 4)."""
    R = P.R
    y_lo, _ = _polys_y(P, M2_SOUTH_LIMIT)
    XL, YL = _crop_extent(P, y_from=y_lo)
    fig, ax = _crop_figure(P, XL, YL)
    handles = _paint_classes(P, ax)
    lab = np.nan_to_num(R.branch_label.values, nan=0).astype(int)
    br = R.branches.reset_index(drop=True); br["value"] = np.arange(1, len(br) + 1)
    marks = []
    for ex in P.examples:
        if ex["act"] != 1 or ex["edge_id"] is None:
            continue
        if ex.get("options") == "branches":
            vals = list(br.loc[br.edge_id == ex["edge_id"], "value"])
            masks = [lab == v for v in vals]
            cells = [(_median_cell(R, m), m) for m in masks]
            cells = sorted([c for c in cells if c[0] is not None], key=lambda t: t[0][0])   # west -> east
        else:
            # each option = the link's FULL corridor band (its owned land, exactly as M1 draws
            # it), in the order the picks list them (Ethan 2026-09-11)
            masks = [(P.owner == P.order[k]) & R.corridor for k in ex["option_edges"]]
            cells = [(_median_cell(R, m), m) for m in masks]
            cells = [c for c in cells if c[0] is not None]
        sides = ex.get("side", "nw"); sides = sides if isinstance(sides, list) else [sides] * len(cells)
        from scipy import ndimage
        for num, (xy, m), side in zip(ex["option_nums"], cells, sides):
            cc._da(R, np.where(m, 1.0, np.nan).astype("float32")).plot.imshow(
                ax=ax, cmap=ListedColormap([OPTIONS_COLOR]), add_colorbar=False)
            # dark rim (~1.2 km) so two adjacent options in the same blue read as two shapes
            rim = m & ~ndimage.binary_erosion(m, iterations=4)
            cc._da(R, np.where(rim, 1.0, np.nan).astype("float32")).plot.imshow(
                ax=ax, cmap=ListedColormap(["#08306b"]), add_colorbar=False)
            marks.append((xy, num, side))
    for xy, num, side in marks:
        _number_marker(ax, xy, num, OPTIONS_COLOR, XL, YL, side=side)
    _director_base(P, ax, XL, YL, tint=tint, area_names=area_names, towns=NORTH_TOWNS)
    nums = [n for _, n, _ in marks]
    handles.append(Patch(color=OPTIONS_COLOR,
                         label=(f"Options {', '.join(map(str, nums))} — alternative links, corridor land as on M1 "
                                "(equal weight)") if nums else "Route options"))
    handles += _node_handles() + [
        plt.Line2D([0], [0], color="0.35", lw=1.0, ls="--", label="Y2Y corridor")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.01), ncol=2,
               fontsize=9.5, frameon=True)
    ax.set_title("Act 1 — the north: room to choose", fontsize=15, pad=12)
    fig.savefig(P.fig / "M2_act1_securing.png", dpi=170, bbox_inches="tight"); plt.show()
    return P


def map_m3(P, area_names=14):
    """M3 -- Act 2, the south at M1's MAP SCALE (crop: everything south of the M1 midline).
    Every link in its M1 colour; the Act-2 example links numbered 5-7."""
    R = P.R
    XL1, YL1 = cc._region_extent(R, 0.07)
    XL, YL = _crop_extent(P, y_to=0.5 * (YL1[0] + YL1[1]))
    fig, ax = _crop_figure(P, XL, YL)
    handles = _paint_classes(P, ax)
    nums = []
    for ex in P.examples:
        if ex["act"] != 2 or ex["edge_id"] is None or not ex.get("mark", True):
            continue
        xy = _median_cell(R, (P.owner == P.order[ex["edge_id"]]) & R.corridor)
        col = CLASS[P.cls.get(ex["edge_id"], "securing")][0]
        if xy is not None and _number_marker(ax, xy, ex["num"], col, XL, YL, side=ex.get("side", "nw")):
            nums.append(ex["num"])
    _director_base(P, ax, XL, YL, area_names=area_names, towns=SOUTH_TOWNS)
    if nums:
        handles.append(_marker_handle(nums))
    handles += _node_handles() + [
        plt.Line2D([0], [0], color="0.35", lw=1.0, ls="--", label="Y2Y corridor")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.01), ncol=2,
               fontsize=9.5, frameon=True)
    ax.set_title(f"Act 2 — {SOUTH_NAME}: options are closing", fontsize=15, pad=12)
    fig.savefig(P.fig / "M3_act2_flagged.png", dpi=170, bbox_inches="tight"); plt.show()
    return P


def map_m4(P):
    """M4 (N1) -- the with / without Dene Kʼéh Kusān pair. RETIRED from the deck and the
    notebook (Ethan, 2026-09-09); kept callable for the appendix."""
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


# ================= star plots (06 §2b, added 2026-09-09) =================
def _option_masks(P):
    """Every numbered option on the maps, in number order: (num, title, mask300m, colour)."""
    R = P.R
    lab = np.nan_to_num(R.branch_label.values, nan=0).astype(int)
    br = R.branches.reset_index(drop=True); br["value"] = np.arange(1, len(br) + 1)
    out = []
    for ex in P.examples:
        if ex["edge_id"] is None:
            continue
        if ex.get("options") == "branches":
            vals = list(br.loc[br.edge_id == ex["edge_id"], "value"])
            ms = [lab == v for v in vals]
            ms = sorted([m for m in ms if m.any()], key=lambda m: _median_cell(R, m)[0])
            side = ["western route", "eastern route"] if len(ms) == 2 else [f"route {i+1}" for i in range(len(ms))]
            for num, m, sd in zip(ex["option_nums"], ms, side):
                out.append((num, f"{ex['title']}\n{sd}", m, OPTIONS_COLOR))
        elif ex.get("options") == "links":
            # each option = the link's FULL corridor band (owned land, as on M1), in the order
            # the picks list them (Ethan 2026-09-11)
            for num, k in zip(ex["option_nums"], ex["option_edges"]):
                m = (P.owner == P.order[k]) & R.corridor
                out.append((num, _pair_title(P.edges.loc[k]), m, OPTIONS_COLOR))
        elif ex.get("mark", True):
            m = (P.owner == P.order[ex["edge_id"]]) & R.corridor
            out.append((ex["option_nums"][0], ex["title"], m, CLASS[P.cls.get(ex["edge_id"], "securing")][0]))
    return out


def star_options(P, reference="y2y", ncols=4):
    """Star plots for the numbered options (1-6) + the proposed IPCAs and the existing PAs as
    wholes, on the Y2Y-WIDE DIRECTOR CONSTRUCTION (`director_core.block_percentiles` ->
    `plot_star_grid`): each axis = the option's mean PERCENTILE of a theme, per-cell percentiles
    ranked over the discretionary (unprotected) landscape, themes = the y2y package's six block
    axes; dashed ring 0.5 = typical unprotected land. Fractional 300 m -> 1 km cover weights
    (M6.5). `reference`: "y2y" = percentiles over ALL unprotected Y2Y land (comparable with the
    y2y-wide deck); "window" = over the routing window's unprotected land (north-relative).
    Decision 2026-09-09 (Ethan): mean percentile, not value-per-area, for both packages."""
    import director_core as dc
    R = P.R
    G = dc.grid()
    if reference == "window":
        win = cc._to_audit(R, np.ones(R.shape, bool))
        assert win.shape == G.shape, "audit grid != hand-off grid"
        G = SimpleNamespace(**{**vars(G), "disc": G.disc & win[G.pu]})
    B = dc.block_percentiles(G)
    items = _option_masks(P) + [("IPCA", "Proposed IPCAs (as a whole)", R.anch, ANCHOR_COLOR),
                                ("PA", "Existing protected areas (as a whole)", R.pa_mask, PA_COLOR)]
    profiles, rows = [], []
    for num, title, m, col in items:
        w = cc._to_audit_frac(R, m)
        assert w.shape == G.shape, "audit grid != hand-off grid"
        w1 = w[G.pu]
        if w1.sum() <= 0:
            print(f"  option {num}: no 1 km cover -- skipped"); continue
        vals = {ax: float((w1 * B.axes[ax]).sum() / w1.sum()) for ax in dc.STAR_AXES}
        head = f"{num} — {title}" if isinstance(num, int) else title
        profiles.append(dict(title=head, values=vals, color=col))
        rows.append(dict(option=num, title=title.replace("\n", " — "), km2=round(int(m.sum()) * R.cell_km2),
                         **{ax: round(v, 3) for ax, v in vals.items()}))
    ref_txt = ("all unprotected land in Y2Y" if reference == "y2y"
               else "unprotected land in the northern routing window")
    dc.plot_star_grid(profiles, P.fig / "S1_star_options.png",
                      f"What each option delivers — mean percentile by theme, ranked against {ref_txt}",
                      ncols=ncols)
    df = pd.DataFrame(rows)
    df.to_csv(P.tab / "star_options.csv", index=False, encoding="utf-8-sig")
    P.stars = df
    print(f"  star plots: {len(profiles)} profiles -> S1_star_options.png + star_options.csv "
          f"(reference: {ref_txt})")
    plt.show()
    return df


# ================= alternatives table (06 §2c, added 2026-09-10) =================
# Themes in the y2y-wide order; each value in its RAW native unit (results_core.RAW_SPEC).
# ABSOLUTE table, THRESHOLD-FREE (Ethan, 2026-09-10). Per index: ("sum", label) = the raster
# summed over the option's cover x km2, where that sum has a physical reading; ("share", label) =
# the option's share of the Y2Y-wide total (%), for the flow-like / quality-like indices whose sum
# means nothing (current density, centrality, refugial residence). Carbon = t C, EFG = groups.
ABS_SPEC = {
    "climate_type_macrorefugia":  ("share", "share of Y2Y-wide refugial residence (%)"),
    "transboundary_connectivity": ("share", "share of Y2Y-wide movement flow (%)"),
    "climate_corridors":          ("share", "share of Y2Y-wide corridor centrality (%)"),
    "aoh_richness_birds":         ("sum",   "habitat km², summed across species (AOH)"),
    "aoh_richness_mammals":       ("sum",   "habitat km², summed across species (AOH)"),
    "human_modification":         ("sum",   "intact land, km² (Σ (1−gHM) × km²)"),
}
TABLE_THEMES = [
    ("Core habitat",       ["climate_type_macrorefugia"]),
    ("Connectivity",       ["transboundary_connectivity", "climate_corridors"]),
    ("Biodiversity",       ["aoh_richness_birds", "aoh_richness_mammals"]),
    ("Carbon",             ["irrecoverable_carbon_m_soc", "irrecoverable_carbon_biomass"]),
    ("Representativeness", ["EFG_mean"]),
    ("Intactness",         ["human_modification"]),
]


def _option_profiles(P):
    """Per option: raw values, % of Y2Y totals, cover weights (fractional 300 m -> 1 km, M6.5)."""
    R = P.R
    Pst = cc._profile_stacks(R)
    items = _option_masks(P) + [("IPCA", "Proposed IPCAs (as a whole)", R.anch, ANCHOR_COLOR),
                                ("PA", "Existing protected areas (as a whole)", R.pa_mask, PA_COLOR)]
    out = []
    efg_count = (np.nan_to_num(Pst.efg_raw, nan=0.0) > 0).sum(axis=0).astype("float64")   # groups per cell
    for num, title, m, _ in items:
        w = cc._to_audit_frac(R, m)
        if w.sum() <= 0:
            print(f"  option {num}: no 1 km cover -- skipped"); continue
        prof, contrib, eff, raw = cc._profile_frac(Pst, w)
        sums = [float(np.nansum(np.nan_to_num(Pst.cont_raw[k], nan=0.0) * w)) * Pst.cell_km2
                for k in range(len(Pst.cont))]          # Σ value × km² over the option's cover
        group = ("Route options" if isinstance(num, int) and num <= 4 else
                 "Example links" if isinstance(num, int) else "As a whole")
        head = (f"{num} — {title.replace(chr(10), ' — ')}" if isinstance(num, int) else title)
        out.append(dict(col=(group, head), km2=int(m.sum()) * R.cell_km2, w_km2=float(w.sum()) * Pst.cell_km2,
                        w_ha=float(w.sum()) * Pst.cell_ha, share=100.0 * float(w.sum()) / Pst.n_region_full,
                        raw=raw, contrib=contrib, sums=sums,
                        efg_per_cell=float((efg_count * w).sum() / w.sum())))
    return Pst, out


def table_options(P, kind="density"):
    """The ALTERNATIVES TABLES for the numbered options (1-6) + the proposed IPCAs and the
    existing PAs as wholes, in the y2y-wide consequences-table format (results_core.RAW_SPEC
    units; fractional cover weights, M6.5), rows grouped by theme, one column per option.
      kind="density"  -> what the land is LIKE: per-cell means, carbon as t C / ha, ecosystem
                         groups per cell. Comparable across columns regardless of area.
      kind="absolute" -> how much it HOLDS, threshold-free: land, share of Y2Y, carbon totals
                         (t C), groups present (of N), habitat km² summed across species (AOH),
                         intact km², and -- for the flow / quality indices whose sum means
                         nothing -- the option's share of the Y2Y-wide total (%) (ABS_SPEC).
    Writes T_options_<kind>.csv + .png (Ethan, 2026-09-10: two tables, never mixed)."""
    assert kind in ("density", "absolute")
    Pst, profs = _option_profiles(P)
    ci = {n: k for k, n in enumerate(Pst.cont)}
    n_efg = len(Pst.efg)
    cols, data, dps = [], {}, {}
    for pr in profs:
        raw, contrib = pr["raw"], pr["contrib"]
        d = {("Area", "land (km²)"): pr["km2"]}; dps[("Area", "land (km²)")] = 0
        if kind == "absolute":
            d[("Area", "share of Y2Y (%)")] = pr["share"]; dps[("Area", "share of Y2Y (%)")] = 2
        for theme, feats in TABLE_THEMES:
            for f in feats:
                label, unit, agg, dp = rc.RAW_SPEC[f]
                if f == "EFG_mean":
                    if kind == "density":
                        k = (theme, f"{label} — groups per cell (mean, of {n_efg})"); d[k] = pr["efg_per_cell"]; dps[k] = 1
                    else:
                        k = (theme, f"{label} — groups present (of {n_efg})"); d[k] = raw[-1]; dps[k] = 0
                elif agg == "tonnes":
                    if kind == "density":
                        k = (theme, f"{label} — t C / ha (mean)"); d[k] = raw[ci[f]] / pr["w_ha"]; dps[k] = 1
                    else:
                        k = (theme, f"{label} — t C (total)"); d[k] = raw[ci[f]]; dps[k] = 0
                elif kind == "density":
                    k = (theme, f"{label} — {unit}"); d[k] = raw[ci[f]]; dps[k] = dp
                else:
                    how, lab = ABS_SPEC[f]
                    k = (theme, f"{label} — {lab}")
                    if how == "sum":
                        d[k] = pr["sums"][ci[f]]; dps[k] = 0
                    else:
                        d[k] = contrib[ci[f]]; dps[k] = 2
        cols.append(pr["col"]); data[pr["col"]] = d
    df = pd.DataFrame(data); df.columns = pd.MultiIndex.from_tuples(cols)
    df.index = pd.MultiIndex.from_tuples(df.index, names=["theme", "value"])
    name = f"T_options_{kind}"
    P.tab.mkdir(parents=True, exist_ok=True)
    # Display rule (Ethan's hand-edited table, 2026-09-10): ONE number of decimals per ROW --
    # the decimals the row's smallest non-zero value needs to show 2 significant figures
    # (results_core._dec with dp 0), applied to every cell of the row; so a row whose values are
    # all >= 10 has none, and a share row reads 0.016 ... 12.448 with three throughout. The
    # ecosystem-group rows are whole numbers. The CSV carries the same rounded numbers (plain);
    # the PNG adds thousands separators.
    def row_dp(r):
        if r[0] == "Representativeness":
            return 0
        fin = df.loc[r].astype(float); fin = fin[np.isfinite(fin) & (fin != 0)]
        return int(max((rc._dec(v, 0) for v in fin), default=0))
    row_dps = {r: row_dp(r) for r in df.index}
    def cell(v, dp, sep):
        return "—" if pd.isna(v) else (f"{v:,.{dp}f}" if sep else f"{v:.{dp}f}")
    plain = pd.DataFrame([[cell(float(v), row_dps[r], False) for v in df.loc[r]] for r in df.index],
                         index=df.index, columns=df.columns)          # fixed decimals, e.g. 0.080
    plain.to_csv(P.tab / f"{name}.csv", encoding="utf-8-sig")
    shown = pd.DataFrame([[cell(float(v), row_dps[r], True) for v in df.loc[r]] for r in df.index],
                         index=df.index, columns=df.columns)
    shown.columns = df.columns
    title = ("What each option's land is LIKE — per-unit values by theme (comparable across columns)"
             if kind == "density" else
             "How much each option HOLDS — threshold-free absolutes by theme (sums in native units; "
             "shares of the Y2Y-wide total where a sum has no meaning)")
    _table_png_grouped(shown, P.fig / f"{name}.png", title)
    setattr(P, f"table_{kind}", df)
    print(f"  alternatives table ({kind}): {df.shape[1]} columns x {df.shape[0]} values -> {name}.csv / .png")
    return shown


def _table_png_grouped(shown, path, title):
    """Render a (theme, value) x (group, option) table to PNG with theme bands and group headers."""
    import textwrap
    nrow, ncol = shown.shape
    fig_w = 3.2 + 1.55 * ncol
    fig_h = 1.6 + 0.34 * (nrow + len(set(shown.index.get_level_values(0))) + 2)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h)); ax.axis("off")
    cell_text, row_labels, row_colors = [], [], []
    last_theme = None
    for (theme, value), row in shown.iterrows():
        if theme != last_theme:
            cell_text.append([""] * ncol); row_labels.append(theme.upper()); row_colors.append("#e8edf0")
            last_theme = theme
        cell_text.append(list(row.values)); row_labels.append("   " + value); row_colors.append("white")
    col_labels = ["\n".join(textwrap.wrap(c[1], 18)) for c in shown.columns]
    tbl = ax.table(cellText=cell_text, rowLabels=row_labels, colLabels=col_labels, loc="center",
                   cellLoc="right", rowLoc="left")
    tbl.auto_set_font_size(False); tbl.set_fontsize(8.5); tbl.scale(1.0, 1.35)
    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_text_props(fontweight=600, va="center"); cell.set_height(cell.get_height() * 2.2)
            cell.set_facecolor("#dfe6ea")
        elif r > 0:
            cell.set_facecolor(row_colors[r - 1])
            if row_colors[r - 1] != "white":
                cell.set_text_props(fontweight=600, color="#2b4f7d")
    # group header line above the columns
    groups = [c[0] for c in shown.columns]
    ax.set_title(title + "\n" + "   |   ".join(f"{g}: {groups.count(g)} column{'s' if groups.count(g)>1 else ''}"
                                             for g in dict.fromkeys(groups)), fontsize=10, pad=14)
    fig.savefig(path, dpi=200, bbox_inches="tight"); plt.close(fig)


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
        axt.text(0, y, f"{_example_label(ex)}", fontsize=15, fontweight=600, va="top")
        y -= 0.08
        axt.text(0, y, textwrap.fill(words, 78), fontsize=10.5, va="top", linespacing=1.4)
        y -= 0.42
        for k, v in rows:
            axt.text(0, y, textwrap.fill(k, 26), fontsize=9.5, fontweight=600, va="top")
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
    kind = r.get("alt_kind") if hasattr(r, "get") else None                       # D29: why the alternative failed
    alt_sentence = {"far": " The next link is far: the alternative route is much longer over similar ground.",
                    "hard": " The next link crosses hard ground: the alternative is not much longer but runs through costlier land.",
                    "both": " The next link is both far and over hard ground."}.get(kind, "")
    locked_line = (" This link was locked as part of one named area and tested against every alternative (D27)."
                   if bool(r.get("locked", False)) else "")
    if c == "both":
        w = (f"The corridor between {a} and {b} is the only viable connection: no other link "
             f"would reconnect the network at a reasonable price (the cheapest alternative costs "
             f"{r['backup_ratio']:.1f}× as much, about {(r['backup_ratio']-1)*r['cost']/(10/3):,.0f} km of "
             f"extra intact-land travel), and within the corridor there is a single physical route. "
             f"Losing this land leaves neither a plan B route nor a plan B link." + alt_sentence + locked_line)
    elif c == "edge":
        w = (f"{a} and {b} nearly touch, and the contact zone is the connection. There is no "
             f"affordable substitute link — the cheapest alternative costs {r['backup_ratio']:.1f}× "
             f"as much. What matters here is the junction itself rather than a swath of corridor." + alt_sentence + locked_line)
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
            Example=(f"{ex['num']} ({ex['slot']})" if ex.get("num") else ex["slot"]),
            Connects=_pair_title(r),
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
        dict(title="What the land is made of", image=F / "M0_cost_surface.png",
             bullets=["The movement-cost surface: four classes only — intact land, roads and "
                      "cuts, converted land, and water / ice / settlement.",
                      "Existing protected areas and declared IPCA proposals hard-coloured; no "
                      "corridors yet."]),
        dict(title="The corridor network over the movement-cost surface",
             image=F / "M0b_cost_surface_corridors.png",
             bullets=["The same surface with the four-class network drawn on top: the land "
                      "between the swaths is what a route has to cross.",
                      "In the north the swaths sit on intact land; along the southern edge they "
                      "thread between roads, cuts and settlement."]),
        dict(title="Where the land still offers choices — and where it does not",
             image=F / "M1_regime.png",
             bullets=["Act 1 (north): corridor land with options — route and partners can be chosen.",
                      f"Act 2 ({SOUTH_NAME}): the map makes the decision — the remaining work is timing."]),
        dict(title="Act 1 — the north: room to choose", image=F / "M2_act1_securing.png",
             bullets=["Wide bands, multiple routes, alternative links.",
                      "Connectivity is contingent on decisions, not on geography.",
                      "Sequencing can follow relationships, jurisdiction and the pace of IPCA realisation."]),
    ]
    slides.append(dict(title="What each option delivers", image=F / "S1_star_options.png",
                       bullets=["One star per numbered option, plus the proposed IPCAs and the "
                                "existing protected areas as wholes.",
                                "Each axis = the average percentile of that value across the option's "
                                "land, ranked against unprotected land Y2Y-wide; the dashed ring is "
                                "typical unprotected land.",
                                "Same construction as the Y2Y-wide package, so the two decks read "
                                "against each other."]))
    for ex in P.examples:
        if ex["slot"] in ("N2", "N3"):
            slides.append(dict(title=_example_label(ex), image=F / f"profile_{ex['slot']}.png",
                               bullets=[]))
    slides.append(dict(title=f"Act 2 — {SOUTH_NAME}: options are closing",
                       image=F / "M3_act2_flagged.png",
                       bullets=["Both-senses irreplaceable: only viable connection.",
                                "Edge-irreplaceable: last affordable link.",
                                "Squeezed: already below natural width." if not P.h8_open
                                else "Squeezed class withheld pending H8."]))
    for ex in P.examples:
        if ex["slot"].startswith("S"):
            slides.append(dict(title=_example_label(ex), image=F / f"profile_{ex['slot']}.png",
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


# ================= 07_director_outputs: the curated maps on the y2y Act 1 WIDE layout ===============================
# Ethan 2026-09-28: "formatted exactly like the Act 1 maps from the y2y analysis -- main panel and two insets on the right",
# insets to be sized on the clusters the package builds next. Layout, typography, basemap, insets, ramp + legend placement =
# `director_plot.wide_map` (the y2y asset: ONE codebase, so the two packages cannot drift); the colours and words for the
# corridor classes and the cost swatches = `corridors_mapstyle` (the §3a tokens: ONE source). The record's portrait maps
# (map_cost / map_m1, notebook 06_tables_and_figures) are untouched. Spec 06 v1.2.17; methods_log M5.21.

WIDE_STYLE = dict(
    map_layout="wide", inset_clusters=(1, 2),      # two insets, A and B: windows from inset_windows() (interim) or the numbered clusters
    inset_windows=None,                            # set per figure by _wide()
    inset_codes={}, inset_town_skip={}, main_skip_codes=(),          # the y2y skips (WA / CA, Jasper / Banff) do not apply on this frame
    wide_main_towns=(), wide_main_names="abbrev",                    # the frame panel: postal codes only, no towns (as on the y2y Act 1 panel)
    pa_layer_min_km2=300, window_scale_km=100,                       # the y2y values; the scale bar on the (windowed) frame
    inset_pa_names=99, inset_ipca_names=99, inset_declutter=False, locator_pa_names=99,   # Ethan 2026-09-28: EVERY PA and IPCA node named in the insets + locators (F.PAN = the network's PA nodes)
    hillshade=True, water=True, titles=False, export_dpi=300, export_pdf=True,   # 21's export settings + the §3a PDF twin
    wide_legend_between=True,                                        # the legend box centred between inset B's bottom edge and the bottom of the page (Ethan 2026-09-28)
)
IPCA_WIDE_LABEL = "Proposed IPCAs"                     # the §3a jurisdictions row (v1.2.15); no parenthetical (Ethan 2026-09-28: it widened the legend past inset B)
COST_CLASSES = (1, 10, 100, 1000)
COST_TICK_WORDS = {1: "intact\nland", 10: "roads\nand cuts", 100: "converted\nland", 1000: "water, ice,\nsettlement"}   # ms.COST_LABELS re-wrapped to <= 11 chars a line: four ticks share a ~4 in bar at 14 pt


def _display_name(label):
    """A node label for the inset name lists: drop the 'IPCA · ' prefix, apply the display overrides (AREA_OVERRIDES)."""
    s = str(label).split(" · ", 1)[-1]
    for frag, ov in AREA_OVERRIDES.items():
        if frag in s:
            return ov[0] if isinstance(ov, tuple) else ov
    return s.split(" [", 1)[0]


def director_frame(P, pad_km=40):
    """The northern run as a director_plot frame (cached on P): G on the 300 m routing grid (pu = the routable cells, locked2d =
    the 32 PA nodes as the layout's grey layer), the 10 draft IPCAs as the overlay in the IPCA role (outline + names in the
    insets), the §3a sector frame (Y2Y ∩ the routing window + pad_km) as the pixel WINDOW, and the northern town table on top
    of the y2y one. If the package holds clusters in the y2y schema (`tables/picks.csv` + `geotiffs/clusters.gpkg` -- the next
    step) they are attached as PICKS / CL so the insets can size on them."""
    if getattr(P, "_frame", None) is not None:
        return P._frame
    import director_core as dc
    import director_plot as dp
    import corridors_mapstyle as ms
    R = P.R
    cost = R.resistance.values
    pu = np.isfinite(cost) & (cost > 0)
    locked2d = R.pa_mask
    crs = pyproj.CRS.from_wkt(R.crs.to_wkt())
    G = SimpleNamespace(pu=pu, locked2d=locked2d, locked=locked2d[pu], disc=pu & ~locked2d, n_pu=int(pu.sum()),
                        n_disc=int((pu & ~locked2d).sum()), shape=R.shape, transform=R.transform, crs=crs, profile=None,
                        cell_km2=R.cell_km2)
    G.rows, G.cols = np.where(pu)
    parts = gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(crs)
    ip = parts[parts["name_label"].astype(str).str.startswith("IPCA")].dissolve(by="name_label").reset_index()
    ip["name"] = [_display_name(s) for s in ip["name_label"]]
    overlay = SimpleNamespace(gdf=ip, mask2d=R.anch, label=IPCA_WIDE_LABEL)
    (x0, x1), (y0, y1) = ms.sector_frame(R, pad_km)
    px0, pyb = dc.xy_to_px(G, x0, y0); px1, pyt = dc.xy_to_px(G, x1, y1)
    F = dp.load_frame(G, overlay=overlay, window=(px0, px1, pyt, pyb), towns={**dc.Y2Y_TOWNS, **cc._TOWNS})
    # the PA name layer = the network's 32 PA nodes (every one, no area floor; display names via AREA_OVERRIDES) instead of the y2y
    # PA vector at >= 300 km2, which drops Klua Lakes / Stone Mountain / Mount Blanchet (Ethan 2026-09-28: label all the PAs and IPCAs)
    pan = parts[~parts["name_label"].astype(str).str.startswith("IPCA")].dissolve(by="name_label").reset_index()
    pan["PA_Name"] = [_display_name(s) for s in pan["name_label"]]; pan["km2"] = pan.geometry.area / 1e6
    F.PAN = pan[["PA_Name", "km2", "geometry"]]
    picks, clusters = P.out / "tables" / "picks.csv", P.out / "geotiffs" / "clusters.gpkg"
    if picks.exists() and clusters.exists():
        F.PICKS = pd.read_csv(picks, dtype={"number": str, "cids": str})
        F.CL = {lyr: gpd.read_file(clusters, layer=lyr) for lyr in gpd.list_layers(clusters).name}
    else:
        F.PICKS, F.CL = None, {}
    P._frame = F
    return F


INSET_SAME_SCALE = True    # Ethan 2026-09-28: "inset box B should be same scale as A" -- every inset window takes the largest width and height


def _same_scale(wins):
    """Every window at the same width and height (the largest of each, about each window's own centre), so the insets share one
    map scale; director_plot then fits them to the panel aspect identically."""
    if len(wins) < 2:
        return wins
    W = max(x1 - x0 for x0, x1, _, _ in wins.values()); H = max(yb - yt for _, _, yt, yb in wins.values())
    return {tag: ((x0 + x1) / 2 - W / 2, (x0 + x1) / 2 + W / 2, (yt + yb) / 2 - H / 2, (yt + yb) / 2 + H / 2) for tag, (x0, x1, yt, yb) in wins.items()}


def inset_windows(P, mode="interim", same_scale=INSET_SAME_SCALE):
    """Pixel windows for the two insets (director_plot re-fits each to the inset aspect, never shrinking). "interim" = the
    record's frames A (options 1–2, Nahanni's ways south) and B (option 5, Gwillim Lake ↔ Pine Le Moray): the option land +
    the INSET_SPEC pad. "clusters" = clusters 1 and 2 of the package's picks (the y2y rule: member polygons' bounds +
    STYLE["inset_pad_km"], floored at STYLE["inset_min_km"]) -- requires the cluster products of the next step. With
    `same_scale` both windows take the larger width and height, so A and B draw at one map scale."""
    F = director_frame(P)
    import director_core as dc
    if mode == "clusters":
        assert F.PICKS is not None and "act1" in F.CL, ("no clusters in the package yet (tables/picks.csv + geotiffs/clusters.gpkg, "
                                                        "the next step): use insets='interim'")
        import director_plot as dp
        out = {}
        for tag, num in zip("AB", dp.STYLE["inset_clusters"]):
            pick = F.PICKS[(F.PICKS.act == "Act 1") & (F.PICKS.number.astype(str) == str(num))].iloc[0]
            cids = [int(c) for c in str(pick.cids).split(";")]
            g = F.CL["act1"]; minx, miny, maxx, maxy = g[g.cid.isin(cids)].geometry.total_bounds
            pad = dp.STYLE["inset_pad_km"] * 1000; floor = dp.STYLE["inset_min_km"] * 1000
            w = max(maxx - minx + 2 * pad, floor); h = max(maxy - miny + 2 * pad, floor)
            cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
            px0, pyb = dc.xy_to_px(F.G, cx - w / 2, cy - h / 2); px1, pyt = dc.xy_to_px(F.G, cx + w / 2, cy + h / 2)
            out[tag] = (float(px0), float(px1), float(pyt), float(pyb))
        return _same_scale(out) if same_scale else out
    assert mode == "interim", f"insets = 'interim' | 'clusters', got {mode!r}"
    R = P.R
    opts = {num: m for num, _, m, _ in _option_masks(P) if isinstance(num, int)}
    xs, ys = R.template.x.values, R.template.y.values
    out = {}
    for tag, spec in INSET_SPEC.items():
        m = np.zeros(R.shape, bool)
        for n in spec["nums"]:
            if n in opts:
                m |= opts[n]
        rr, cc_ = np.nonzero(m)
        if not len(rr):
            continue
        p = spec["pad_km"] * 1e3
        x0, x1 = xs[cc_.min()] - p, xs[cc_.max()] + p
        y0, y1 = ys[rr].min() - p, ys[rr].max() + p
        px0, pyb = dc.xy_to_px(F.G, x0, y0); px1, pyt = dc.xy_to_px(F.G, x1, y1)
        out[tag] = (float(px0), float(px1), float(pyt), float(pyb))
    return _same_scale(out) if same_scale else out


def cost_surface(P):
    """The movement-cost classes as a four-swatch surface for the wide layout's ramp slot (corridors_mapstyle.COST -- the magma
    samples M0b uses), NaN off the routable area. Returns (surface, class shares in % of the routable area)."""
    import corridors_mapstyle as ms
    from matplotlib.colors import BoundaryNorm
    cost = P.R.resistance.values
    img = np.full(cost.shape, np.nan, np.float32)
    for i, c in enumerate(COST_CLASSES):
        img[cost == c] = i
    fin = cost[np.isfinite(cost) & (cost > 0)]
    shares = {c: 100 * float((fin == c).sum()) / fin.size for c in COST_CLASSES}
    n = len(COST_CLASSES)
    S_ = dict(img=img, cmap=ListedColormap([ms.COST[c][0] for c in COST_CLASSES]), norm=BoundaryNorm(np.arange(-0.5, n + 0.5, 1), n),
              extend="neither", ticks=list(range(n)), ticklabels=[f"{c}\n{COST_TICK_WORDS[c]}" for c in COST_CLASSES],
              label="cost of moving through the land (the four movement-cost classes)", end_words=None)
    return S_, shares


def classes_surface(P):
    """The routing classes as a categorical surface: the §3a pressure levels in CLASS_ORDER with the corridors_mapstyle tokens
    and words, so the ramp slot becomes the "Corridor Pressure" key; H8 open -> squeezed folded into securing, as on every
    record map. Returns (surface, links per class)."""
    import corridors_mapstyle as ms
    from matplotlib.colors import BoundaryNorm
    R = P.R
    order = [c for c in ms.CLASS_ORDER if not (c == "squeezed" and P.h8_open)]
    img = np.full(R.shape, np.nan, np.float32); counts = {}
    for i, c in enumerate(order):
        ids = list(P.cls.index[P.cls == c])
        if c == "securing" and P.h8_open:
            ids += list(P.cls.index[P.cls == "squeezed"])
        img[np.isin(P.owner, [P.order[k] for k in ids if k in P.order]) & R.corridor] = i
        counts[c] = len(ids)

    def _tick(c):
        head, _, tail = ms.CLASS[c][3].partition(" (")
        return "\n".join([head] + textwrap.wrap(f"({tail}", 12)) if tail else head        # <= 12 chars a line: four ticks share a ~4 in bar at 14 pt
    n = len(order)
    S_ = dict(img=img, cmap=ListedColormap([ms.CLASS[c][0] for c in order]), norm=BoundaryNorm(np.arange(-0.5, n + 0.5, 1), n),
              extend="neither", ticks=list(range(n)), ticklabels=[_tick(c) for c in order],
              label=f"{ms.CLASS_HEADING.lower()} — how much the network's connection depends on this land"
                    + ("; the top class also requires the corridor to be below its barrier-free width" if "link_class" in R.edges.columns else ""),   # D23 clause
              end_words=None)
    return S_, counts


def _near_contiguous_wide(P, F):
    """D25 on the wide layout: (draw, handles) for the near-contiguous links -- their bands in the neutral grey with the mapstyle
    hatch (contourf in pixel space), the barrier variant outlined; nothing when the run has no such link."""
    import corridors_mapstyle as ms
    R = P.R; layers = []
    for c in NEAR_CONTIGUOUS_KEYS:
        ids = list(P.cls.index[P.cls == c])
        m = np.isin(P.owner, [P.order[k] for k in ids if k in P.order]) & R.corridor if ids else None
        if m is not None and m.any():
            layers.append((c, m, len(ids)))
    if not layers:
        return (lambda ax: None), []

    def draw(ax):
        for c, m, _ in layers:
            tok = ms.NEAR_CONTIGUOUS[c]
            ax.imshow(np.where(m, 1.0, np.nan).astype(np.float32), cmap=ListedColormap([tok["fill"]]), interpolation="nearest", zorder=0.85)
            with plt.rc_context({"hatch.color": tok["hatch_color"], "hatch.linewidth": 0.5}):
                ax.contourf(m.astype(float), levels=[0.5, 1.5], colors="none", hatches=[tok["hatch"]], zorder=0.86)
            if tok["outline"]:
                ax.contour(m.astype(float), levels=[0.5], colors=[tok["outline"][0]], linewidths=tok["outline"][1],
                           linestyles=[tok["outline"][2] if len(tok["outline"]) > 2 else "solid"], zorder=0.87)
    handles = [Patch(facecolor=ms.NEAR_CONTIGUOUS[c]["fill"], hatch=ms.NEAR_CONTIGUOUS[c]["hatch"],
                     edgecolor=(ms.NEAR_CONTIGUOUS[c]["outline"][0] if ms.NEAR_CONTIGUOUS[c]["outline"] else ms.NEAR_CONTIGUOUS[c]["hatch_color"]),
                     linewidth=(ms.NEAR_CONTIGUOUS[c]["outline"][1] if ms.NEAR_CONTIGUOUS[c]["outline"] else 0.0),
                     linestyle=(ms.NEAR_CONTIGUOUS[c]["outline"][2] if ms.NEAR_CONTIGUOUS[c]["outline"] and len(ms.NEAR_CONTIGUOUS[c]["outline"]) > 2 else "solid"),
                     label=CLASS[c][1]) for c, _, _ in layers]
    return draw, handles


def _wide_overlay(F, P=None):
    """The overlay callback for the wide layout: the draft IPCAs as filled nodes (the §3a IPCA fill, opaque like the layout's PA
    grey so the two node kinds read alike) with their outlines; with `P`, the near-contiguous links' bands first (D25).
    Called on the frame and on every inset."""
    import director_plot as dp
    import corridors_mapstyle as ms
    a = ms.AREA["ipca"]
    fill = np.full(F.G.shape, np.nan, np.float32); fill[F.IP.mask2d] = 1.0
    nc_draw, nc_handles = _near_contiguous_wide(P, F) if P is not None else ((lambda ax: None), [])

    def draw(ax):
        nc_draw(ax)
        ax.imshow(fill, cmap=ListedColormap([a["fill"]]), interpolation="nearest", zorder=1.1)
        lw = 0.9 * dp.STYLE.get("_lw_scale", 1.0)
        for _, r in F.IP.gdf.iterrows():
            for ring in F.rings_px(r.geometry):
                ax.plot(ring[:, 0], ring[:, 1], color=a["edge"], lw=lw, zorder=3.5)
    handles = [Patch(facecolor=dp.PA_COLOR, label=PA_LABEL), Patch(facecolor=a["fill"], edgecolor=a["edge"], label=IPCA_WIDE_LABEL)] + nc_handles
    return draw, handles


def _wide(P, path, surface, insets):
    import director_plot as dp
    F = director_frame(P)
    assert dp.STYLE.get("map_layout") == "wide" and dp.STYLE.get("inset_clusters"), "apply dp.STYLE.update(cd.WIDE_STYLE) first (07's setup cell)"
    dp.STYLE["inset_windows"] = inset_windows(P, insets)
    draw, handles = _wide_overlay(F, P)
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    dp.wide_map(F, path, "", draw, handles, with_ipca_names=True, surface=surface)
    return path


def figure_cost_wide(P, path, insets="interim"):
    """07 · 01 -- the movement-cost surface on the y2y Act 1 wide layout (frame + insets A, B): the four cost swatches in the
    ramp slot, PAs grey, IPCAs filled + outlined, postal codes on the frame, names + towns in the insets; PNG at 300 dpi + PDF.
    Prints the class shares (the record map's subtitle line) for the slide."""
    S_, shares = cost_surface(P)
    print("movement cost, share of the routable area: " + " · ".join(f"{c}: {shares[c]:.1f}%" for c in COST_CLASSES))
    return _wide(P, path, S_, insets)


def _option_marks(P, F, nums=OPTIONS_MAP_NUMS):
    """The numbered options for the wide layout: (num, mask, (px, py), side) -- each option = one link's full corridor band (or
    a route branch), numbered at the median cell of its largest piece (as M2), in pixel coordinates."""
    import director_core as dc
    sides = {}
    for ex in P.examples:
        sd = ex.get("side", "nw"); sd = sd if isinstance(sd, list) else [sd] * len(ex["option_nums"])
        sides.update(dict(zip(ex["option_nums"], sd)))
    out = []
    for num, _, m, _ in _option_masks(P):
        if num not in nums or num not in sides:
            continue
        xy = _median_cell(P.R, m)
        if xy is None:
            continue
        px, py = dc.xy_to_px(F.G, *xy)
        out.append((num, m, (float(px), float(py)), sides[num]))
    return out


def _number_marker_px(ax, xy, num, color, side="nw", fs=None):
    """M2's numbered marker in pixel space: a white disc with a coloured rim and a short leader, offset in POINTS (so it
    reads the same on the frame and in the insets; the size follows STYLE["_fs_scale"] like the y2y cluster numbers). An
    annotation whose anchor lies outside the axes is not drawn (matplotlib's default clip), so an inset shows only its own."""
    import director_plot as dp
    fs = (fs or dp.STYLE["cluster_number_fs"]) * dp.STYLE.get("_fs_scale", 1.0); off = 1.7 * fs
    dx = off if side in ("ne", "se") else -off
    dy = off if side in ("ne", "nw") else -off
    ax.annotate(str(num), xy, xytext=(dx, dy), textcoords="offset points", fontsize=fs, fontweight=600, ha="center", va="center", zorder=8,
                bbox=dict(boxstyle="circle,pad=0.3", fc="white", ec=color, lw=1.8), arrowprops=dict(arrowstyle="-", color=color, lw=1.2, shrinkB=0))


def _options_overlay(P, F, nums=OPTIONS_MAP_NUMS):
    """The route options' overlay for any panel (the wide map's frame + insets, the locators): the IPCA nodes, each option's band
    in its colour (under the PA / IPCA fills, as on M2), the numbered markers. Returns (draw, handles, marks, colors) with the
    legend handles = PA, IPCA, the y2y cluster swatch reading "Route options" in option order."""
    import director_plot as dp
    marks = _option_marks(P, F, nums)
    colors = {n: option_color(n) for n, _, _, _ in marks}
    layers = [(np.where(m, 1.0, np.nan).astype(np.float32), colors[n]) for n, m, _, _ in marks]
    ipca_draw, handles = _wide_overlay(F, P)

    def draw(ax):
        ipca_draw(ax)
        for img, col in layers:
            ax.imshow(img, cmap=ListedColormap([col]), interpolation="nearest", zorder=0.9)     # under the PA (1) / IPCA (1.1) fills
        for num, _, xy, side in marks:
            _number_marker_px(ax, xy, num, colors[num], side)
    handles = handles + [dp.cluster_handle("Route options", colors=[colors[n] for n in colors])]     # swatches in option order
    return draw, handles, marks, colors


def figure_options_wide(P, path, insets="interim", nums=OPTIONS_MAP_NUMS):
    """07 · 03 -- the route options on the wide layout (Ethan 2026-09-28: "the options, 1–4; 1 and 2 in panel A, 3 and 4 in
    panel B"): the pressure classes as on 02, each option's corridor band on top in ITS NUMBER'S COLOUR from the y2y cluster
    palette (director_plot STYLE["cluster_colors"] in OPTION_COLOR_ORDER: 1 red, 2 blue, 3 magenta, 4 dark orange), numbered at the band's median
    cell with a marker rimmed in the same colour; the legend entry is the y2y cluster swatch handle, reading "Route options".
    Options under the PA / IPCA fills, as on M2. Inset A holds 1–2, inset B holds 3–4 (INSET_SPEC)."""
    import director_plot as dp
    F = director_frame(P)
    S_, _ = classes_surface(P)
    draw, handles, marks, colors = _options_overlay(P, F, nums)
    print("route options: " + " · ".join(f"{n} {colors[n]} at px {tuple(round(v) for v in xy)} ({side})" for n, _, xy, side in marks))
    assert dp.STYLE.get("map_layout") == "wide" and dp.STYLE.get("inset_clusters"), "apply dp.STYLE.update(cd.WIDE_STYLE) first (07's setup cell)"
    dp.STYLE["inset_windows"] = inset_windows(P, insets)
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    dp.wide_map(F, path, "", draw, handles, with_ipca_names=True, surface=S_)
    return path


def figure_choices_wide(P, path, insets="interim"):
    """07 · 02 -- "where the land still offers choices" on the wide layout: the routing classes (corridor pressure) in the ramp
    slot as the key, everything else as on 01."""
    S_, counts = classes_surface(P)
    print("links per class: " + " · ".join(f"{c} {n}" for c, n in counts.items())
          + (" | H8 OPEN -- squeezed folded into securing" if P.h8_open else ""))
    return _wide(P, path, S_, insets)


# ---- 07 · 04 / 05: the route options' stars, locators and consequences on the y2y construction + assets (Ethan 2026-09-28) ----
CONSEQ_REFERENCE_NODES = [("Nahanni National", "Nahanni National Park Reserve"),   # (fragment of the node_parts name_label, column name);
                          ("Dene K", "Dene Kʼéh Kusān")]                          # the y2y tables' rule: real example areas, one PA + one IPCA


def option_profiles_y2y(P, nums=OPTIONS_MAP_NUMS):
    """Cached on P: the deck's route options (+ the reference nodes) on the y2y DIRECTOR CONSTRUCTION over the Y2Y-wide
    allocatable landscape -- per star axis the mean PERCENTILE (director_core.block_percentiles; M5.15) and the consequences
    RATIO (director_core.ValueRatios: mean raw value / mean over allocatable land, "2.3x"), both with the fractional 300 m ->
    1 km cover weights (M6.5). Returns a DataFrame: kind (option | reference), number, name, area_km2 (300 m native),
    pct_<axis>, ratio_<axis> -- the T-D1 / T-D7 columns the y2y assets read."""
    key = ("_y2y_profiles", tuple(nums))
    cache = getattr(P, "_y2y_profiles", {})
    if key in cache:
        return cache[key]
    import director_core as dc
    from rasterio.features import rasterize as _rasterize
    R = P.R
    G = dc.grid(); B = dc.block_percentiles(G); VR = dc.ValueRatios(G, B)
    items = [("option", n, t, m) for n, t, m, _ in _option_masks(P) if n in nums]
    parts = gpd.read_file(R.run_dir / "node_parts.gpkg").to_crs(R.crs)
    for frag, name in CONSEQ_REFERENCE_NODES:
        sel = parts[parts["name_label"].astype(str).str.contains(frag, regex=False)]
        assert len(sel), f"reference node {frag!r} not in node_parts"
        m = _rasterize(((g, 1) for g in sel.geometry), out_shape=R.shape, transform=R.transform, fill=0, dtype="uint8").astype(bool)
        items.append(("reference", "", name, m))
    rows = []
    for kind, num, name, m in items:
        w1 = cc._to_audit_frac(R, m)[G.pu]
        assert w1.sum() > 0, f"{kind} {num or name}: no 1 km cover"
        pct = {ax: float((w1 * B.axes[ax]).sum() / w1.sum()) for ax in dc.STAR_AXES}
        rat = VR.of(None, weights=w1)
        rows.append(dict(kind=kind, number=str(num), name=name.replace("\n", " — "), area_km2=int(m.sum()) * R.cell_km2,
                         **{f"pct_{a}": v for a, v in pct.items()}, **{f"ratio_{a}": v for a, v in rat.items()}))
    df = pd.DataFrame(rows)
    cache[key] = df; P._y2y_profiles = cache
    return df


def option_stars(P, path, nums=OPTIONS_MAP_NUMS):
    """07 · 04 -- star plots of the route options on the y2y asset (director_plot.star_grid, one star per option in the option's
    colour): axes = mean percentile per theme vs the Y2Y-wide allocatable landscape (dashed ring 0.5 = the typical unprotected
    cell), titles "Option N / (the link) / km²" as the y2y clusters' "Cluster N / (Region) / km²"."""
    import director_core as dc
    import director_plot as dp
    df = option_profiles_y2y(P, nums)
    prof = [dict(title=f"Option {int(r.number)}\n({r['name']})\n{r.area_km2:,.0f} km²", values={a: float(r[f"pct_{a}"]) for a in dc.STAR_AXES},
                 color=option_color(int(r.number))) for _, r in df[df.kind == "option"].iterrows()]
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    dp.star_grid(prof, path, "Route options — value profile (percentile vs the allocatable landscape)")
    return df


def option_locators(P, path, nums=OPTIONS_MAP_NUMS, insets="interim", panel_px=None):
    """07 · 04b -- the two inset windows as locator panels on the star grid's geometry (the y2y cluster_locators rule: same
    figure width, panels of STYLE["locator_panel_in"]): A (options 1–2) centred under the first two stars, B (3–4) under the
    last two -- two panels for four stars (Ethan 2026-09-28). Square windows at one scale, the pressure classes + the options
    drawn as on 03, the tag letter as the title; `panel_px` also writes each panel as its own file."""
    import math
    import director_core as dc
    import director_plot as dp
    F = director_frame(P)
    S_, _ = classes_surface(P)
    draw, _, marks, _ = _options_overlay(P, F, nums)
    wins = inset_windows(P, insets)
    n_stars = len(nums); ncols = min(4, max(n_stars, 1)); L = dc.STAR_GRID; STYLE = dp.STYLE
    tags = list(wins)                                                         # A, B
    per = max(1, n_stars // len(tags))                                        # stars per window (2)
    with plt.rc_context(dp.SPEC_RC):
        fig_w, fig_h = L["panel_w"] * ncols, max(L["panel_h"], STYLE["locator_panel_in"] + 0.4)
        fig = plt.figure(figsize=(fig_w, fig_h))
        left, right = 0.125, 0.9
        aw = (right - left) / (ncols + (ncols - 1) * L["wspace"])
        pw = STYLE["locator_panel_in"] / fig_w; ph = STYLE["locator_panel_in"] / fig_h
        axes = []
        for i, tag in enumerate(tags):
            cols_ = range(i * per, min((i + 1) * per, ncols))
            cx = float(np.mean([left + aw * (c_ + 0.5) + c_ * aw * L["wspace"] for c_ in cols_]))
            axes.append(fig.add_axes([cx - pw / 2, 0.5 - ph / 2, pw, ph]))
        sc = STYLE["locator_fs_scale"]
        STYLE["_fs_scale"] = STYLE["inset_number_fs"] / STYLE["cluster_number_fs"] * sc; STYLE["_lw_scale"] = STYLE["cluster_lw_inset_scale"] * sc
        fs0, pa0 = STYLE["inset_fs"], STYLE["inset_pa_names"]; STYLE["inset_fs"] = fs0 * sc; STYLE["inset_pa_names"] = STYLE["locator_pa_names"]
        try:
            for ax, tag in zip(axes, tags):
                win = dp._fit_window(F, wins[tag], 1.0)                       # square, never shrunk: both at the same scale (INSET_SAME_SCALE)
                dp._draw_inset(F, ax, win, draw, tag, True, towns=STYLE["locator_towns"], codes=None, img=S_["img"], cmap=S_["cmap"], norm=S_["norm"])   # every PA + IPCA node named
        finally:
            STYLE.pop("_fs_scale", None); STYLE.pop("_lw_scale", None); STYLE["inset_fs"] = fs0; STYLE["inset_pa_names"] = pa0
        path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=STYLE["export_dpi"])
        if panel_px:
            fig.canvas.draw(); r = fig.canvas.get_renderer()
            for ax, tag in zip(axes, tags):
                bb = ax.get_tightbbox(r).transformed(fig.dpi_scale_trans.inverted()).padded(0.02)
                fig.savefig(path.with_name(f"{path.stem}_{tag}{path.suffix}"), bbox_inches=bb, dpi=STYLE["panel_export_scale"] * panel_px / bb.width)
        plt.show()
    return path


def option_consequences(P, path, nums=OPTIONS_MAP_NUMS):
    """07 · 05 -- the consequences table for the route options on the y2y asset (director_plot.consequences_table: transposed,
    per-row RdBu fills over the option columns, the spec type): mean raw value in the option's land / mean over Y2Y-wide
    allocatable land per star axis, columns = the options then the reference nodes (CONSEQ_REFERENCE_NODES). The rows also
    go to tables/route_option_consequences.csv."""
    import director_plot as dp
    F = director_frame(P)
    df = option_profiles_y2y(P, nums)
    rows = df[df.kind == "option"].reset_index(drop=True); ref = df[df.kind == "reference"].reset_index(drop=True)
    P.tab.mkdir(parents=True, exist_ok=True); df.to_csv(P.tab / "route_option_consequences.csv", index=False, encoding="utf-8-sig")
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    dp.consequences_table(F, rows, path, "ROUTE OPTIONS  ·  CONSEQUENCES", "What the route options hold", ref=ref,
                          col_label=lambda r, wrap=18: f"Option {int(r.number)}\n({textwrap.fill(str(r.name), wrap)})", group_label="Route options",
                          source=f"Y2Y northern corridors ({P.R.run_id}, least-cost network); values on the Y2Y director construction (manifest {__import__('director_core').VP.version} layers).")
    return df
