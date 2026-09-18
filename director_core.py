"""director_core.py -- helpers for the Y2Y DIRECTOR PACKAGE (Gate 5 deliverable).

Spec: `analyses/y2y/spec/director_package_spec.md` v1.1 (subordinate to the study plan v0.14.1).
Consumed by `19_tiers_and_clusters.ipynb` (surfaces, clustering, tables, GeoTIFFs) and
`20_figures.ipynb` (hex choropleths, cluster overlays, star grid, Act-3 map, E17 one-pager,
deck). Presentation decisions live in the package spec, methods decisions in the study plan; the
pre-stated constants below are copied from the spec verbatim and logged in methods_log.

Semantics: every surface here is the GUARDED band (per-block capture floors capture_b >= 0.95 x
anchor_b appended to the 5% band; spec v0.14 ruling = applied headline). The unguarded band is
carried alongside only for the T-D2 side-by-side (the E15 doubling slide). The estimator is the
hierarchical mean used by 13_gate4_analysis: f_s = mean over {anchor + 50 members}, F = mean over
formulations (one vote each).
"""
from pathlib import Path
from types import SimpleNamespace
import json
import math

import numpy as np
import pandas as pd
import rasterio
from rasterio import features as rfeatures
from scipy import ndimage
from pyproj import Transformer
import geopandas as gpd
from shapely.geometry import Polygon, Point, shape, box as shp_box
from shapely.ops import unary_union

import config
import leverage_core as lc
import ensemble_core as ec

ROOT = Path(config.PROJECT_DIR)
Y2Y = ROOT / "analyses" / "y2y"
SPEC = Y2Y / "spec"
VP = config.y2y_paths()                  # the active manifest/run VERSION (config.Y2Y_VERSION; v3 = curated EFG block)
RUNS = VP.runs                           # runs_<version>/ (v1: runs/)
SPEC_REC = VP.records                    # version-scoped records (T1 CSVs, E11 matrices, e17 geography, E19)
MANIFEST = VP.manifest
RUNS_V1 = config.y2y_paths("v1").runs    # v1 evidence that is never re-solved (E17-T3 anchors, E18 arms)
PKG = Y2Y / "director_package"

# ---- pre-stated constants (director_package_spec.md v1.1) ------------------------------------
FREQ_THR = 0.70            # pre-registered frequent band (decision b)
SENS_THRS = (0.60, 0.80)   # sensitivity companion thresholds (appendix)
NEVER_THR = 0.05
MIN_KM2 = 100              # decision (d); deliberately NOT config.CLUSTER_MIN_CELLS (the 04-era 25)
CLOSE_R = 1                # morphological closing radius in cells (bridge single-cell speckle only)
HEX_KM2 = 250              # decision (c) default
HEX_KM2_ALT = 800          # board-level legibility variant, rendered for comparison
POOL_JACCARD_MIN = 0.80    # decision (g): pool the two climate levels unless their frequent tiers diverge
TOPK_ACT1 = 6              # deck shows top-k by area (tie-break mean guarded F); the register ships in full
PICK_LINK_KM = 75          # deck picks: the top-k complexes are grouped into REGIONAL clusters by single linkage at this
SPECK_LINK_KM = 10         # core components below MIN_KM2 within this distance of a regional cluster join it (Ethan 2026-09-15: 10 km)
                           # edge-to-edge distance and numbered north -> south (Ethan 2026-09-14: "3, 4 and 6 become one")
COMPLEX_LINK_KM = 25       # presentational grouping: kept components within this edge-to-edge distance (single
                           # linkage) form one COMPLEX for the deck picks (Ethan 2026-09-04: the two Frank Church /
                           # Gospel Hump components, 8 km apart, merge; Eagle Cap at 72 km and the cluster west of
                           # Purcell/Robson stay separate). Components remain the analytic units.
TOPK_ACT2 = 2
FLOOR_G = 0.05
RARE_EFG_PCT = 0.01       # "rarest" EFG companion mask: presence <= 1% of the PU (disclosed alongside the spec mask)
BANDS = [("never", 0.0, NEVER_THR), ("rare", NEVER_THR, 0.30), ("conditional", 0.30, FREQ_THR),
         ("frequent", FREQ_THR, 0.95), ("always", 0.95, 1.0001)]
# block star axes: member percentiles are averaged with these weights (carbon = mass split 74.2/25.8,
# the Gate-1 measurement); representativeness is a DIFFERENT construction (EFG classes present / 40)
BLOCK_AXES_FOUR = {                 # manifests v1 / v3 / v3.1: connectivity = one axis averaging its two layers
    "core habitat":  {"climate_type_macrorefugia": 1.0},
    "connectivity":  {"transboundary_connectivity": 0.5, "climate_corridors": 0.5},
    "biodiversity":  {"aoh_richness_birds": 0.5, "aoh_richness_mammals": 0.5},
    "carbon":        {"irrecoverable_carbon_m_soc": 0.742, "irrecoverable_carbon_biomass": 0.258},
    "naturalness":   {"human_modification": 1.0},     # plain sixth axis in the package (Ethan 2026-09-04); "naturalness" = 1 - gHM (terminology, 2026-09-14)
}
BLOCK_AXES_FIVE = {                 # manifest v4 (study plan v0.20): the connectivity compound value de-bundled into its two components
    "core habitat":            {"climate_type_macrorefugia": 1.0},
    "structural connectivity": {"transboundary_connectivity": 1.0},
    "climate corridors":       {"climate_corridors": 1.0},
    "biodiversity":            {"aoh_richness_birds": 0.5, "aoh_richness_mammals": 0.5},
    "carbon":                  {"irrecoverable_carbon_m_soc": 0.742, "irrecoverable_carbon_biomass": 0.258},
    "naturalness":             {"human_modification": 1.0},
}
BLOCK_AXES = BLOCK_AXES_FIVE if VP.version == "v4" else BLOCK_AXES_FOUR
AXIS_OF_BLOCK = {b: b.replace("_", " ") for b in config.BLOCKS}          # config block name -> star-axis name
STAR_AXES = [a for a in BLOCK_AXES if a != "naturalness"] + ["representativeness", "naturalness"]   # 7 under v4, 6 before
MULTI_OWNER = 99                     # act2_owner.tif code for "frequent under two or more named scenarios" (was 5 = 4 + 1 before v4)
N_EFG = len(lc.efg_paths())          # 20 under the curated block (v3); 40 under v1
SCENARIO_LABEL = {"s0": "Balanced", "s1": "Core-habitat-forward", "s2": "Connectivity-forward", "s2c": "Climate-corridors-forward",
                  "s3": "Biodiversity-forward", "s4": "Carbon-forward", "s5": "Intactness push (S0 + gHM x10)",
                  "s1x": "Core-habitat x carbon regime", "s3x": "Biodiversity x carbon regime"}
if VP.version == "v4":               # manifest v4: s2 = structural connectivity alone; s2c = the climate-corridors forward (new)
    SCENARIO_LABEL["s2"] = "Structural-connectivity-forward"; SCENARIO_LABEL["s5"] = "Naturalness push (S0 + gHM x10)"
ACT2_SCENARIOS = ["s1", "s2", "s2c", "s3", "s4"] if VP.version == "v4" else ["s1", "s2", "s3", "s4"]   # the named forward scenarios (Act 2)
N_DESIGN = 14 if VP.version == "v4" else 12   # voting cells: 7 x 2 under v4, 6 x 2 before
# Director package votes = the 12 ELICITED positions (6 scenarios x 2 climate futures). The two crossed
# diagnostic hybrids (s1x, s3x: shares held, carbon target regime flipped alone) are near-duplicate votes for
# S1/S3 at SSP585 (frequent-tier Jaccard 0.84 / 0.95) and are EXCLUDED here (Ethan, 2026-09-04; R10.9).
# The paper's registered estimand stays F over all 14 (13_gate4_analysis); the package F12 is a deviation
# from the package spec's "across all 14 formulations", logged in methods_log.
PACKAGE_EXCLUDE = ("s1x", "s3x")
def package_manifest(MAN):
    """The 12 DESIGN formulations. Study plan v0.15 made this the paper's PRIMARY denominator too: `role` = design
    votes, diagnostic (s1x, s3x) never votes. Reads `role` from spec/manifest_v2.csv when 13b has written it;
    falls back to PACKAGE_EXCLUDE (identical membership) before that."""
    if "role" in MAN.columns:                          # manifest v3+ carries role itself
        m = MAN[MAN.role.eq("design")].reset_index(drop=True)
        assert len(m) == N_DESIGN, f"expected {N_DESIGN} design formulations, got {len(m)}"
        return m
    v2 = SPEC / "manifest_v2.csv"
    if v2.exists():
        roles = pd.read_csv(v2).set_index("formulation_id")["role"]
        m = MAN[MAN.formulation_id.map(roles).eq("design")].reset_index(drop=True)
    else:
        m = MAN[~MAN.scenario_id.isin(PACKAGE_EXCLUDE)].reset_index(drop=True)
    assert len(m) == N_DESIGN, f"expected {N_DESIGN} design formulations, got {len(m)}"
    return m
SCENARIO_STATEMENT = {
    "s0": f"all {'five' if VP.version == 'v4' else 'four'} value themes hold their intended influence shares",
    "s1": "climate macrorefugia (core habitat) carries a doubled influence share",
    "s2": ("structural connectivity (transboundary current, valued convexly) carries a doubled share" if VP.version == "v4"
           else "connectivity (transboundary current + climate corridors) carries a doubled share"),
    "s2c": "climate corridors (Carroll current-flow centrality) carry a doubled share",
    "s3": "AOH richness (birds + mammals) carries a doubled share",
    "s4": "carbon carries a doubled share and the mineral-soil target rises 0.332 -> 0.552 (theta 3x)",
    "s5": "S0 with the (inexpressible) intactness layer pushed x10 -- the Claim-B demonstration",
    "s1x": "S1's shares under the carbon-forward target regime (regime flipped alone)",
    "s3x": "S3's shares under the carbon-forward target regime (regime flipped alone)",
}
# ---- package spec v1.6: value-first architecture --------------------------------------------------
ACT_TITLE = {"act0": "Act 0 — Where the values are", "act1": "Act 1 — Core commitments",
             "act2": "Act 2 — Value-specific priorities", "act3": "Act 3 — The opportunity landscape (the measured gap)"}
# the acts follow THIS analysis (Ethan 2026-09-14): Act 0 = the values before any optimization (the v1.6 "value-first" prologue),
# Act 1 = the core, Act 2 = the scenario tiers, Act 3 = the opportunity landscape; 19's registers use the same numbers
ACT_DISPLAY = {"Act 1": "Act 1 core", "Act 2": "Act 2 scenario", "Act 1 (585)": "Act 1 core (SSP585)", "Act 1 (245)": "Act 1 core (SSP245)"}
VALUE_THEMES = [a for a in BLOCK_AXES if a != "naturalness"] + ["representativeness"]   # the PROACT themes: five before v4, six under v4
VALUE_TOP = 0.70                     # "top 30% of the discretionary landscape" = block percentile >= 0.70
THEME_OF_SCENARIO = ({"s1": "core habitat", "s2": "structural connectivity", "s2c": "climate corridors", "s3": "biodiversity", "s4": "carbon"}
                     if VP.version == "v4" else {"s1": "core habitat", "s2": "connectivity", "s3": "biodiversity", "s4": "carbon"})
# E18 carry-overs (package spec v1.6 / study plan v0.16). The deck is built on v3.1 only (Ethan, 2026-09-14): the E18
# dose numbers were measured on the 40-class block and stay in the paper's record (R10.13-R10.15), so the caveat and its
# mirror are stated STRUCTURALLY here -- what the design does, not a v1 measurement.
CARBON_CAVEAT = ("carbon-forward is the only scenario that also states a security target (55% of dense soil carbon); "
                 "its own land comes from that target, not from the share doubling the other values get")
CARBON_MIRROR = ("carbon has a target lever because its geometry admitted a stopping rule; the diffuse values cannot; "
                 "the asymmetry is the landscape's")
BIODIV_FINDING = "almost no land of its own; every near-optimal plan holds {lo:.0f}–{hi:.0f}% of AOH richness whichever value leads"

# decision (h): Nations' own DECLARED IPCA proposals only, never analyst-drawn: the IPCA-typed rows of the
# corridor-wide proposed-PA file + the Ross River NPR proposal (Kaska-led; the 04a "manual area").
IPCA_SPEC = dict(vector=config.PROPOSED_PA_VECTOR, name_field="PA_NAME")
# T-D4 (spec v1.3): tier area by ecozone/ecoregion. No such layer is in input_data yet -- drop a vector
# (e.g. CEC North American Level II/III ecoregions, seamless US+Canada) into this folder and 19 picks it
# up; until then the T-D4 cell reports itself PENDING rather than failing the run.
ECOREGIONS_DIR = config.INPUT_DIR / "ecoregions"
ECOREGION_NAME_FIELDS = ("ECO_NAME", "BIOME_NAME", "NA_L2NAME", "NA_L3NAME", "ECOZONE_NAME", "ZONE_NAME", "ECOREGION", "REGION_NAM", "NAME", "name")
def ipca_rule(df):
    # declared IPCA proposals only (+ the Kaska-led Ross River NPR proposal). The Indigenous-governed "Great Caribou
    # Rainforest" (PA_TYPE Conservation Area, 52% already inside Wells Gray / Bowron / Cariboo Mountains parks) is
    # NOT an IPCA and is excluded (Ethan, 2026-09-04).
    return (df["PA_TYPE"].astype(str).str.strip() == "IPCA") | df["PA_NAME"].astype(str).str.contains("Ross River")


def ensure_dirs(pkg=PKG):
    for sub in ("geotiffs", "tables", "figures"):
        (pkg / sub).mkdir(parents=True, exist_ok=True)
    return pkg


# ---- grid ------------------------------------------------------------------------------------
def grid():
    """The 1 km analysis grid + PU / locked / discretionary masks (1-D vectors run over PU cells)."""
    with rasterio.open(config.Y2Y_STACK_DIR / "cost_uniform.tif") as src:
        tr, shp, prof = src.transform, src.shape, src.profile
    pu = lc.pu_mask()
    with rasterio.open(config.Y2Y_STACK_DIR / "mask_protected_areas.tif") as src:
        locked2d = (src.read(1) == 1) & pu
    locked = locked2d[pu]
    G = SimpleNamespace(pu=pu, locked2d=locked2d, locked=locked, disc=~locked, n_pu=int(pu.sum()),
                        n_disc=int((~locked).sum()), shape=shp, transform=tr, crs=config.TARGET_CRS,
                        profile=prof, cell_km2=abs(tr.a * tr.e) / 1e6)
    G.rows, G.cols = np.where(pu)
    return G


def to_grid(G, v, fill=np.nan, dtype=np.float32):
    out = np.full(G.shape, fill, dtype=dtype)
    out[G.pu] = v
    return out


def latlon(G):
    """Per-PU-cell latitude/longitude (cached on G)."""
    if not hasattr(G, "lat"):
        xs = G.transform.c + (G.cols + 0.5) * G.transform.a
        ys = G.transform.f + (G.rows + 0.5) * G.transform.e
        lon, lat = Transformer.from_crs(G.crs, "EPSG:4326", always_xy=True).transform(xs, ys)
        G.lat, G.lon = lat.astype(np.float32), lon.astype(np.float32)
    return G.lat, G.lon


def write_tif(G, v, path, dtype="float32", nodata=np.nan):
    arr = v if v.ndim == 2 else to_grid(G, v, fill=nodata, dtype=dtype)
    prof = G.profile | dict(dtype=dtype, count=1, nodata=nodata, compress="deflate", tiled=True)
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(arr.astype(dtype), 1)
    return path


# ---- loading the sweeps ----------------------------------------------------------------------
def _diam(S, disc, m_disc):
    Sd = S[:, disc].astype(np.float32)
    sizes = Sd.sum(axis=1)
    ham = sizes[:, None] + sizes[None, :] - 2 * (Sd @ Sd.T)
    return float(ham.max() / (2 * m_disc))


def load_guarded(G, MAN, allow_partial=False, diameters=True):
    """Stream every formulation once: guarded + plain f, anchors, band unions, diameters, certificates.

    allow_partial=True is a DEV flag (smoke-runs on the S0/S4 artifacts from notebook 16); the
    production run asserts all 14 guarded sweeps exist (director spec step 0)."""
    L = SimpleNamespace(forms=[], f_guard={}, f_plain={}, anchors={}, union_guard={}, union_plain={},
                        D_guard={}, D_plain={}, cert={}, meta={}, f_maa_guard={})
    missing = []
    for _, row in MAN.iterrows():
        fid = row.formulation_id
        cd = RUNS / fid
        need = [cd / "anchor.tif", cd / "mga_guard_g05.tif", cd / "certificates_guard.csv"]      # the unguarded band is optional (v4: reference cell only)
        if not all(p.exists() for p in need):
            missing.append(fid)
            continue
        cert = pd.read_csv(cd / "certificates_guard.csv")
        assert bool(cert.band_ok.all()), f"{fid}: guarded band certificate violated"
        assert len(cert) == int(row.k_requested), f"{fid}: {len(cert)} guarded members, expected {row.k_requested}"
        A = ec.read_selections(cd / "anchor.tif", G.pu)[0]
        Sg = np.vstack([A[None, :], ec.read_selections(cd / "mga_guard_g05.tif", G.pu)])
        plain = cd / "mga_g05.tif"
        Sp = np.vstack([A[None, :], ec.read_selections(plain, G.pu)]) if plain.exists() else None
        m_disc = int(A[G.disc].sum())
        L.f_guard[fid] = Sg.mean(axis=0).astype(np.float32)
        L.union_guard[fid] = Sg.any(axis=0)
        L.anchors[fid] = A
        if diameters:
            L.D_guard[fid] = _diam(Sg, G.disc, m_disc)
        if Sp is not None:
            L.f_plain[fid] = Sp.mean(axis=0).astype(np.float32)
            L.union_plain[fid] = Sp.any(axis=0)
            if diameters:
                L.D_plain[fid] = _diam(Sp, G.disc, m_disc)
        L.cert[fid] = dict(n=len(cert), dup=int(cert.duplicate.sum()), runtime_min=float(cert.runtime_s.sum() / 60),
                           time_limited=int((cert.status == "TIME_LIMIT").sum()))
        L.meta[fid] = json.loads((cd / "formulation_meta.json").read_text())
        maa = cd / "maa_guard_g05.tif"
        if maa.exists():
            Sm = np.vstack([A[None, :], ec.read_selections(maa, G.pu)])
            L.f_maa_guard[fid] = Sm.mean(axis=0).astype(np.float32)
            del Sm
        L.forms.append(fid)
        del Sg, Sp
        print(f"{fid:<22} f_guard freq {int((L.f_guard[fid][G.disc] >= FREQ_THR).sum()):>7,} km2 | "
              + (f"plain {int((L.f_plain[fid][G.disc] >= FREQ_THR).sum()):>7,} km2" if fid in L.f_plain else "plain      (none)")
              + (f" | D {L.D_plain[fid]:.3f} -> {L.D_guard[fid]:.3f}" if diameters and fid in L.D_plain else (f" | D_guard {L.D_guard[fid]:.3f}" if diameters else "")))
    L.plain_forms = [f for f in L.forms if f in L.f_plain]         # v4: the reference cell only; v3.1 and before: every formulation
    if missing:
        msg = f"guarded sweep missing for {len(missing)} formulation(s): {missing} -- run 18_guarded_sweep first"
        if not allow_partial:
            raise FileNotFoundError(msg)
        print("ALLOW_PARTIAL:", msg)
    L.missing = missing
    return L


def ensemble(fdict, forms):
    """Hierarchical F: one vote per formulation (13_gate4_analysis's estimator)."""
    return np.mean([fdict[c] for c in forms], axis=0).astype(np.float32)


def union_membership(L, forms, guarded=True):
    U = L.union_guard if guarded else L.union_plain
    forms = [c for c in forms if c in U]
    return np.mean([U[c] for c in forms], axis=0).astype(np.float32)


# ---- tiers ------------------------------------------------------------------------------------
def band_masks(F):
    return {name: (F >= lo) & (F < hi) for name, lo, hi in BANDS}


def band_table(G, surfaces):
    """T-D2 part 1: spec bands x semantics, discretionary km2 and % (surfaces = {label: F})."""
    rows = []
    for name, lo, hi in BANDS:
        r = {"band": f"{name} [{lo:.2f}, {min(hi, 1.0):.2f}{')' if hi < 1 else ']'}"}
        for lab, F in surfaces.items():
            km2 = int(((F >= lo) & (F < hi) & G.disc).sum())
            r[f"{lab} km2"] = km2
            r[f"{lab} %disc"] = 100 * km2 / G.n_disc
        rows.append(r)
    return pd.DataFrame(rows)


def jaccard(a, b):
    u = int((a | b).sum())
    return float((a & b).sum() / u) if u else float("nan")


def pool_scenarios(G, fdict, MAN, thr=FREQ_THR, jmin=POOL_JACCARD_MIN, force=False):
    """Decision (g): per scenario, pool the two climate levels unless their frequent tiers diverge.

    force=True pools regardless (Ethan, 2026-09-04: the deck shows one map per scenario; the divergence check
    is still computed and reported). Returns (POOL {key: f}, report df); key = scenario_id when pooled,
    '<sid>@<level>' otherwise."""
    POOL, rep = {}, []
    for sid, grp in MAN.groupby("scenario_id", sort=False):
        fids = [f for f in grp.formulation_id if f in fdict]
        if not fids:
            continue
        if len(fids) == 1:
            POOL[sid] = fdict[fids[0]]
            rep.append(dict(scenario=sid, levels=1, jaccard=np.nan, decision="single level",
                            **{f"freq_km2_{i}": int((fdict[f][G.disc] >= thr).sum()) for i, f in enumerate(fids)}))
            continue
        tiers = [(fdict[f] >= thr) & G.disc for f in fids]
        J = jaccard(tiers[0], tiers[1])
        if J >= jmin or force:
            POOL[sid] = np.mean([fdict[f] for f in fids], axis=0).astype(np.float32)
            dec = "POOLED" if J >= jmin else f"POOLED (forced; rule would separate at Jaccard {J:.2f} < {jmin})"
        else:
            for f in fids:
                POOL[f"{sid}@{'245' if 'ssp245' in f else '585'}"] = fdict[f]
            dec = "SEPARATE (diverged)"
        rep.append(dict(scenario=sid, levels=len(fids), jaccard=J, decision=dec,
                        freq_km2_585=int(tiers[0].sum()), freq_km2_245=int(tiers[1].sum())))
    return POOL, pd.DataFrame(rep)


# ---- clustering (pre-stated procedure, spec v1.1) --------------------------------------------
def clusters(G, surf, thr=FREQ_THR, min_km2=MIN_KM2, close_r=CLOSE_R, subtract2d=None):
    """Threshold -> closing(r) -> 8-connected components -> register (all components; kept = >= min).

    subtract2d: Act-1 core footprint to remove AFTER clustering (Act 2), with % overlap reported."""
    F2 = to_grid(G, surf, fill=0.0)
    m = (F2 >= thr) & G.pu & ~G.locked2d
    if close_r:
        m = ndimage.binary_closing(m, structure=np.ones((3, 3), bool), iterations=close_r) & G.pu & ~G.locked2d
        m |= (F2 >= thr) & G.pu & ~G.locked2d          # closing never removes original cells
    lab, n = ndimage.label(m, structure=np.ones((3, 3), int))
    if n == 0:
        return lab, pd.DataFrame(columns=["cid", "cells", "km2", "meanF", "minF", "kept"])
    ids = np.arange(1, n + 1)
    cells = ndimage.sum(m, lab, ids).astype(int)
    meanF = ndimage.mean(F2, lab, ids)
    minF = ndimage.minimum(np.where(m, F2, 9.0), lab, ids)
    cy, cx = zip(*ndimage.center_of_mass(m, lab, ids))
    reg = pd.DataFrame(dict(cid=ids, cells=cells, km2=cells * G.cell_km2, meanF=meanF, minF=minF,
                            row=np.array(cy), col=np.array(cx)))
    if subtract2d is not None:
        ov = ndimage.sum(m & subtract2d, lab, ids).astype(int)
        reg["core_overlap_pct"] = 100 * ov / cells
        reg["residual_km2"] = (cells - ov) * G.cell_km2
        reg["kept"] = reg.residual_km2 >= min_km2
    else:
        reg["kept"] = reg.km2 >= min_km2
    x = G.transform.c + (reg.col + 0.5) * G.transform.a
    y = G.transform.f + (reg.row + 0.5) * G.transform.e
    lon, lat = Transformer.from_crs(G.crs, "EPSG:4326", always_xy=True).transform(x.values, y.values)
    reg["lat"], reg["lon"] = lat, lon
    reg = reg.sort_values(["km2", "meanF"], ascending=False).reset_index(drop=True)
    return lab, reg


def top_k(reg, k):
    return reg[reg.kept].sort_values(["km2", "meanF"], ascending=False).head(k)


def group_complexes(G, lab, reg, link_km=COMPLEX_LINK_KM):
    """Single-linkage grouping of KEPT components by edge-to-edge distance -> `complex` id on the register.

    Presentational (deck picks are complexes); the component rows are untouched. Returns (reg, complexes df) where
    complexes has one row per complex: cids (list), anchor_cid (largest member), km2 (sum), meanF (area-weighted),
    lat/lon (area-weighted), kept=True."""
    from scipy.cluster.hierarchy import linkage, fcluster
    from scipy.spatial.distance import squareform
    reg = reg.copy()
    reg["complex"] = -1
    kept = reg[reg.kept]
    ids = kept.cid.astype(int).tolist()
    if len(ids) == 0:
        return reg, pd.DataFrame(columns=["complex", "cids", "anchor_cid", "n", "km2", "meanF", "lat", "lon", "kept"])
    if len(ids) == 1:
        grp = np.array([1])
    else:
        n = len(ids); D = np.zeros((n, n))
        for i, a in enumerate(ids):
            dt = ndimage.distance_transform_edt(lab != a)
            for j in range(i + 1, n):
                D[i, j] = D[j, i] = dt[lab == ids[j]].min() * (abs(G.transform.a) / 1000.0)
        grp = fcluster(linkage(squareform(D), method="single"), t=link_km, criterion="distance")
    reg.loc[kept.index, "complex"] = grp
    rows = []
    area_col = "residual_km2" if "residual_km2" in reg.columns else "km2"
    for g, sub in reg[reg.kept].groupby("complex"):
        w = sub[area_col].values
        rows.append(dict(complex=int(g), cids=sub.cid.astype(int).tolist(), anchor_cid=int(sub.sort_values(area_col).cid.iloc[-1]),
                         n=len(sub), km2=float(w.sum()), meanF=float((sub.meanF.values * w).sum() / w.sum()),
                         lat=float((sub.lat.values * w).sum() / w.sum()), lon=float((sub.lon.values * w).sum() / w.sum()), kept=True))
    cx = pd.DataFrame(rows).sort_values(["km2", "meanF"], ascending=False).reset_index(drop=True)
    return reg, cx


def sensitivity(G, surf, thrs=(SENS_THRS[0], FREQ_THR, SENS_THRS[1]), **kw):
    rows = []
    for t in thrs:
        _, reg = clusters(G, surf, thr=t, **kw)
        kept = reg[reg.kept] if len(reg) else reg
        rows.append(dict(threshold=t, tier_km2=int(((surf >= t) & G.disc).sum()),
                         n_components=len(reg), n_kept=len(kept), kept_km2=float(kept.km2.sum()) if len(kept) else 0.0,
                         largest_km2=float(kept.km2.max()) if len(kept) else 0.0))
    return pd.DataFrame(rows)


def mask_of(lab, cid):
    return lab == cid


def vectorize(G, lab, ids, simplify_m=2000):
    """Cluster polygons (topology-preserving simplification, ~2 km tolerance) as a GeoDataFrame."""
    recs = []
    arr = np.where(np.isin(lab, ids), lab, 0).astype(np.int32)
    geoms = {}
    for geom, val in rfeatures.shapes(arr, mask=arr > 0, transform=G.transform):
        geoms.setdefault(int(val), []).append(shape(geom))
    for cid in ids:
        g = unary_union(geoms.get(int(cid), []))
        recs.append(dict(cid=int(cid), geometry=g.simplify(simplify_m, preserve_topology=True)))
    return gpd.GeoDataFrame(recs, geometry="geometry", crs=G.crs)


# ---- hex aggregation (presentation only; clustering ALWAYS runs at 1 km) ---------------------
def hex_grid(G, area_km2=HEX_KM2):
    """Flat-top hexagon lattice in the analysis CRS covering the PU extent; rasterized to hex ids."""
    R = math.sqrt(2 * area_km2 * 1e6 / (3 * math.sqrt(3)))      # circumradius (m)
    w, h = 2 * R, math.sqrt(3) * R
    x0 = G.transform.c; y1 = G.transform.f
    x1 = x0 + G.shape[1] * G.transform.a; y0 = y1 + G.shape[0] * G.transform.e
    polys, ids = [], []
    nx = int((x1 - x0) / (1.5 * R)) + 3
    ny = int((y1 - y0) / h) + 3
    k = 0
    for i in range(-1, nx):
        cx = x0 + i * 1.5 * R
        for j in range(-1, ny):
            cy = y0 + j * h + (h / 2 if i % 2 else 0)
            k += 1
            ids.append(k)
            polys.append(Polygon([(cx + R * math.cos(a), cy + R * math.sin(a))
                                  for a in np.arange(0, 2 * math.pi, math.pi / 3)]))
    lab = rfeatures.rasterize(zip(polys, ids), out_shape=G.shape, transform=G.transform, fill=0, dtype="int32")
    lab[~G.pu] = 0
    present = np.unique(lab[lab > 0])
    gdf = gpd.GeoDataFrame({"hex_id": ids, "geometry": polys}, crs=G.crs)
    gdf = gdf[gdf.hex_id.isin(present)].reset_index(drop=True)
    return gdf, lab


def hex_means(G, gdf, lab, surf, disc_only=True):
    """Mean of a PU surface per hex over DISCRETIONARY cells (PAs are drawn as their own layer)."""
    F2 = to_grid(G, surf, fill=np.nan)
    valid = G.pu & (~G.locked2d if disc_only else True) & np.isfinite(F2)
    labv = np.where(valid, lab, 0)
    ids = gdf.hex_id.values
    with np.errstate(invalid="ignore", divide="ignore"):      # hexes with no valid cell -> NaN, by design
        means = ndimage.mean(np.nan_to_num(F2), labv, ids)
    counts = ndimage.sum(valid, labv, ids)
    out = gdf.copy()
    out["value"] = np.where(counts > 0, means, np.nan)
    out["n_disc"] = counts.astype(int)
    out["n_pu"] = ndimage.sum(G.pu, lab, ids).astype(int)
    return out


# ---- cartography helpers (pixel-space maps: 1 px = 1 km) --------------------------------------
def xy_to_px(G, x, y):
    return (x - G.transform.c) / G.transform.a, (y - G.transform.f) / G.transform.e


def graticule(ax, G, lats=(45, 50, 53, 55, 60, 65), lons=(-130, -125, -120, -115, -110), emph_lat=53,
              color="#555555", lw=0.4):
    """Lat/lon graticule in pixel coordinates; 53 N emphasized (ties to the E17 one-pager)."""
    T = Transformer.from_crs("EPSG:4326", G.crs, always_xy=True)
    H, W = G.shape
    for la in lats:
        lo = np.linspace(-145, -95, 200)
        x, y = T.transform(lo, np.full_like(lo, la, dtype=float))
        px, py = xy_to_px(G, x, y)
        e = la == emph_lat
        ax.plot(px, py, color="#b00020" if e else color, lw=1.1 if e else lw, ls="-" if e else ":", zorder=3,
                clip_on=True)
        inside = (px >= 0) & (px < W) & (py >= 0) & (py < H)
        if inside.any():
            i = np.argmax(inside)
            ax.text(px[i] + 4, py[i] - 3, f"{la}°N", fontsize=7 if not e else 8, color="#b00020" if e else color,
                    fontweight=600 if e else 400, zorder=4)
    for lo in lons:
        la = np.linspace(38, 72, 200)
        x, y = T.transform(np.full_like(la, lo, dtype=float), la)
        px, py = xy_to_px(G, x, y)
        ax.plot(px, py, color=color, lw=lw, ls=":", zorder=3, clip_on=True)
    ax.set_xlim(0, W); ax.set_ylim(H, 0)


def scalebar(ax, G, km=250, loc=(0.70, 0.94), fs=8):     # loc = (x from left, y from bottom) as axes fractions
    H, W = G.shape
    px_per_km = 1000 / abs(G.transform.a)
    x0, y0 = loc[0] * W, (1 - loc[1]) * H
    ax.plot([x0, x0 + km * px_per_km], [y0, y0], color="black", lw=2.5, solid_capstyle="butt", zorder=5)
    ax.text(x0 + km * px_per_km / 2, y0 - 12, f"{km} km", ha="center", fontsize=fs, zorder=5)


def corner_note(ax, text, loc="lower right"):
    ha = "right" if "right" in loc else "left"
    ax.text(0.99 if ha == "right" else 0.01, 0.005, text, transform=ax.transAxes, ha=ha, va="bottom",
            fontsize=7.5, color="#333333", zorder=6)


# ---- block percentiles (star plots) -----------------------------------------------------------
def block_percentiles(G):
    """Per-cell percentile of each hand-off layer over the DISCRETIONARY landscape (0.5 = typical
    unprotected land), combined into the five block axes; EFG presence stack for representativeness."""
    axes = {}
    pct = {}
    feats = sorted({f for d in BLOCK_AXES.values() for f in d})
    for f in feats:
        v = np.nan_to_num(lc._read(config.Y2Y_STACK_DIR / f"{f}.tif")[G.pu], nan=0.0)
        ref = np.sort(v[G.disc])
        pct[f] = (np.searchsorted(ref, v, side="right") / len(ref)).astype(np.float32)
    for ax, members in BLOCK_AXES.items():
        axes[ax] = sum(w * pct[f] for f, w in members.items()).astype(np.float32)
    paths = lc.efg_paths()
    efg = np.zeros((len(paths), G.n_pu), bool)
    for i, p in enumerate(paths):
        efg[i] = np.nan_to_num(lc._read(p)[G.pu], nan=0.0) > 0
    # representativeness on the SAME construction as the other axes: per-cell count of EFG classes present,
    # ranked over the discretionary landscape (the spec's "classes present / 40" cannot exceed ~0.35 for any
    # cluster-sized patch -- no cell holds more than 15 classes -- so it read as "far below average" against
    # the 0.5 ring; R10.7. The raw class count is still reported in T-D1.)
    count = efg.sum(axis=0).astype(np.float32)
    ref = np.sort(count[G.disc])
    axes["representativeness"] = (np.searchsorted(ref, count, side="right") / len(ref)).astype(np.float32)
    return SimpleNamespace(axes=axes, pct=pct, efg=efg, efg_names=[p.stem for p in paths], efg_count=count)


def value_layers(G, P, rare_mask, top=VALUE_TOP):
    """Act 1 (package spec v1.6): where each PROACT theme's VALUE is, independent of any solve.
    Continuous themes: the top (1-top) share of the DISCRETIONARY landscape by block score (P.axes -- the star construction).
    Representativeness: presence of any rare-EFG class (rare_mask; the <=1%-footprint set by default, disclosed --
    the 36 rare-attainable classes cover 79% of the region and would vote almost everywhere).
    Naturalness (1 - gHM): same rule, a sixth map ("disclosed, not a driver") NOT counted in the convergence tally.
    Returns 1-D masks over PU (discretionary only) + convergence = number of the VALUE_THEMES voting (0-5; 0-6 under v4)."""
    # exact top-(1-top) share of the DISCRETIONARY landscape by the block score: for single-layer blocks this equals
    # "block percentile >= top"; for two-layer blocks (mean of two percentiles) a 0.70 cut on the mean would keep only
    # ~20% of cells, so the cut is the score's own (top)-quantile over unprotected land (ties may add a little)
    masks = {}
    for ax in BLOCK_AXES:                                          # every block axis incl. naturalness (disclosed, not counted)
        thr = float(np.quantile(P.axes[ax][G.disc], top))
        masks[ax] = (P.axes[ax] >= thr) & G.disc
    masks["representativeness"] = rare_mask & G.disc
    conv = sum(masks[t].astype(np.uint8) for t in VALUE_THEMES).astype(np.uint8)
    return SimpleNamespace(masks=masks, convergence=conv, top=top)


TIER_NAMES = {3: "core", 2: "scenario tiers", 1: "opportunity", 0: "never"}     # act_tiers_guarded.tif codes

def coverage_table(G, V, tier_code):
    """T-D6: each theme's top-value footprint and how the reliability tiers cover it (Act 4 = the gap)."""
    rows = []
    for t, m in V.masks.items():
        n = int(m.sum())
        r = {"theme": t, "top-value footprint km2": n, "% of unprotected land": 100 * n / G.n_disc}
        for code, nm in TIER_NAMES.items():
            r[f"% of footprint in {nm}"] = 100 * float((m & (tier_code == code)).sum()) / max(n, 1)
        rows.append(r)
    return pd.DataFrame(rows)


def crosstab(G, conv, tier_code):
    """Hinge figure: value-convergence count (0..len(VALUE_THEMES)) x reliability class, km2 over the discretionary landscape."""
    cols = {3: "core (F ≥ 0.70)", 2: "scenario tier", 1: "opportunity", 0: "never"}
    n = len(VALUE_THEMES)
    T = pd.DataFrame(0, index=[f"{k} of {n} themes" for k in range(n + 1)], columns=list(cols.values()), dtype=int)
    for k in range(n + 1):
        for code, nm in cols.items():
            T.loc[f"{k} of {n} themes", nm] = int(((conv == k) & (tier_code == code) & G.disc).sum())
    return T


def group_picks(G, lab, picks, link_km=PICK_LINK_KM):
    """Second presentational tier: merge deck-pick complexes whose masks lie within link_km (single linkage) into
    regional clusters; renumber NORTH -> SOUTH. picks: DataFrame rows for ONE act/key (number, cids, name, km2, meanF,
    lat, lon). Returns a DataFrame with the same columns + `members` (the merged pick numbers)."""
    rows = list(picks.itertuples()); n = len(rows)
    masks = [np.isin(lab, [int(c) for c in str(r.cids).split(";")]) for r in rows]
    parent = list(range(n))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i in range(n):
        dt = ndimage.distance_transform_edt(~masks[i])
        for j in range(i + 1, n):
            if float(dt[masks[j]].min()) <= link_km:
                parent[find(i)] = find(j)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    out = []
    for idx in groups.values():
        mem = [rows[i] for i in idx]; big = max(mem, key=lambda r: r.km2); km2 = sum(r.km2 for r in mem)
        out.append(dict(act=big.act, key=big.key, cid=int(big.cid), cids=";".join(str(r.cids) for r in mem), n_components=sum(int(r.n_components) for r in mem),
                        name=big.name, km2=float(km2), meanF=float(sum(r.meanF * r.km2 for r in mem) / km2),
                        lat=float(sum(r.lat * r.km2 for r in mem) / km2), lon=float(sum(r.lon * r.km2 for r in mem) / km2),
                        members=";".join(str(r.number) for r in mem)))
    out = sorted(out, key=lambda r: -r["lat"])                      # north -> south
    return pd.DataFrame(out)


def absorb_complexes(G, lab, gp, cx, link_km=PICK_LINK_KM, reg=None, speck_km=SPECK_LINK_KM):
    """Regional clusters (group_picks output) ABSORB (1) the kept complexes that are not deck picks -- a complex within
    link_km of a cluster joins the NEAREST one, passes repeating so a chain joins through an absorbed member -- and (2) the
    SPECKS: core components under MIN_KM2 within speck_km of a cluster (Ethan 2026-09-15: the yellow cells in a cluster's
    vicinity belong to it). Two clusters never merge. Returns gp with cids / km2 / meanF / lat / lon / members updated."""
    gp = gp.copy().reset_index(drop=True)
    cl_cids = [[int(c) for c in str(r.cids).split(";")] for r in gp.itertuples()]
    taken = set(c for cc in cl_cids for c in cc)
    free = [(j, [int(c) for c in r.cids], float(r.km2), float(r.meanF), float(r.lat), float(r.lon)) for j, r in cx.reset_index(drop=True).iterrows()
            if not set(int(c) for c in r.cids) & taken]
    absorbed = {i: [] for i in range(len(gp))}
    while free:
        dts = [ndimage.distance_transform_edt(~np.isin(lab, cc)) for cc in cl_cids]
        joins = []
        for f in free:
            m = np.isin(lab, f[1]); d = [float(dt[m].min()) for dt in dts]
            i = int(np.argmin(d))
            if d[i] <= link_km:
                joins.append((f, i))
        if not joins:
            break
        for f, i in joins:
            cl_cids[i] += f[1]; absorbed[i].append(f); free.remove(f)
    # the specks: core components under MIN_KM2 (never complexes) within speck_km of a cluster join the nearest one
    n_specks = {i: 0 for i in range(len(gp))}
    if reg is not None and speck_km:
        dts = [ndimage.distance_transform_edt(~np.isin(lab, cc)) for cc in cl_cids]
        for r_ in reg[~reg.kept].itertuples():
            m = lab == int(r_.cid); d = [float(dt[m].min()) for dt in dts]; i = int(np.argmin(d))
            if d[i] <= speck_km:
                cl_cids[i].append(int(r_.cid)); n_specks[i] += 1
                absorbed[i].append((None, [int(r_.cid)], float(r_.km2), float(r_.meanF), float(r_.lat), float(r_.lon)))
    for i, r in gp.iterrows():
        if not absorbed[i]:
            continue
        km2 = float(r.km2) + sum(f[2] for f in absorbed[i])
        gp.loc[i, "meanF"] = (float(r.meanF) * float(r.km2) + sum(f[3] * f[2] for f in absorbed[i])) / km2
        gp.loc[i, "lat"] = (float(r.lat) * float(r.km2) + sum(f[4] * f[2] for f in absorbed[i])) / km2
        gp.loc[i, "lon"] = (float(r.lon) * float(r.km2) + sum(f[5] * f[2] for f in absorbed[i])) / km2
        gp.loc[i, "km2"] = km2
        gp.loc[i, "cids"] = ";".join(str(c) for c in cl_cids[i])
        gp.loc[i, "n_components"] = int(r.n_components) + sum(len(f[1]) for f in absorbed[i])
        gp.loc[i, "members"] = str(r.members) + "".join(f"+cx{f[0] + 1}" for f in absorbed[i] if f[0] is not None) + (f"+{n_specks[i]}specks" if n_specks[i] else "")
    return gp.sort_values("lat", ascending=False).reset_index(drop=True)


class ValueRatios:
    """Consequences tables (Ethan 2026-09-14): mean raw value inside a cluster / mean raw value over ALLOCATABLE
    (discretionary) land, per star axis -- "2.3x" = 2.3 times the average unprotected cell. Blocks combine their
    members' ratios with the BLOCK_AXES weights; representativeness = ecosystem classes present per cell;
    naturalness = 1 - gHM."""
    def __init__(self, G, P):
        self.G = G
        self.raw = {f: np.nan_to_num(lc._read(config.Y2Y_STACK_DIR / f"{f}.tif")[G.pu], nan=0.0) for d in BLOCK_AXES.values() for f in d}
        self.raw["__efg_count"] = P.efg_count.astype(np.float32)
        self.base = {k: float(v[G.disc].mean()) for k, v in self.raw.items()}
    def of(self, mask1d):
        out = {}
        for ax, members in BLOCK_AXES.items():
            out[ax] = float(sum(w * (self.raw[f][mask1d].mean() / self.base[f]) for f, w in members.items()))
        out["representativeness"] = float(self.raw["__efg_count"][mask1d].mean() / self.base["__efg_count"])
        return {a: out[a] for a in STAR_AXES}


def star_profile(P, mask1d):
    return {ax: float(P.axes[ax][mask1d].mean()) for ax in STAR_AXES}


def efg_classes_present(P, mask1d):
    return int(P.efg[:, mask1d].any(axis=1).sum())


# ---- driver attribution masks (E13 definitions, notebook 15) ----------------------------------
def driver_masks(G):
    theta = config.AUDIT["theta"]
    rare_cap = config.AUDIT["rare_cap"]
    v = lc._read(config.Y2Y_STACK_DIR / "irrecoverable_carbon_m_soc.tif")
    masks = {"m_soc theta-tail": np.nan_to_num(v, nan=-1)[G.pu] >= theta * float(np.nanmean(v[G.pu]))}
    conn = lc._read(config.Y2Y_STACK_DIR / "transboundary_connectivity.tif")[G.pu]
    # the STRUCTURAL-connectivity spike (transboundary current only; a quantile cut, so identical under v4's I^2); the key is
    # kept verbatim because it names CSV columns across versions
    masks["connectivity spike (top 0.2%)"] = conn >= np.nanquantile(conn, 0.998)
    # refugia has no theta rule of its own (t = 1.0); its dense core is defined AREA-MATCHED to the m_soc
    # theta-tail so the two attribution columns are comparable (R10.6: refugia pins the core)
    refu = np.nan_to_num(lc._read(config.Y2Y_STACK_DIR / "climate_type_macrorefugia.tif")[G.pu], nan=0.0)
    k = int(masks["m_soc theta-tail"].sum())
    dens = np.zeros(G.n_pu, bool); dens[np.argsort(refu, kind="stable")[-k:]] = True    # exactly k cells (a velocity floor can tie at the top)
    masks["refugia densest (area-matched to the m_soc tail)"] = dens
    rare = np.zeros(G.n_pu, bool)
    n_rare = 0
    for p in lc.efg_paths():
        e = np.nan_to_num(lc._read(p)[G.pu], nan=0.0)
        cap_max = lc.leverage_of(e)[1]
        if cap_max >= rare_cap:            # rare-attainable = fits inside the budget entirely (Gate 0a rule)
            rare |= e > 0
            n_rare += 1
    masks["rare-attainable EFG footprint"] = rare
    # The spec's "rare-EFG footprint" is ambiguous: rare-ATTAINABLE (fits in the budget; 36/40) unions to
    # ~79% of the region and cannot attribute anything, so a discriminating companion is reported too:
    # EFGs whose presence covers <= RARE_EFG_PCT of the PU (the genuinely scarce classes). Both disclosed.
    rarest = np.zeros(G.n_pu, bool)
    n_rarest = 0
    win = SPEC_REC / "efg_window_footprints.csv"          # v3.1+: rarity judged in the buffered regional window (M4.29)
    if win.exists():
        W = pd.read_csv(win).set_index("feature")
        rare_set = set(W.index[W["rare_window"]])
        for p in lc.efg_paths():
            if p.stem in rare_set:
                rarest |= np.nan_to_num(lc._read(p)[G.pu], nan=0.0) > 0
                n_rarest += 1
        rare_key = (f"rarest-EFG footprint (rare in the extent+{config.EFG_TARGET_WINDOW_KM} km window: "
                    f"<= {100 * config.EFG_RARE_WINDOW_PCT:g}% of the window)")
    else:                                                  # v1 rule: <= 1% of the PU, on-extent
        for p in lc.efg_paths():
            e = np.nan_to_num(lc._read(p)[G.pu], nan=0.0) > 0
            if e.sum() <= RARE_EFG_PCT * G.n_pu:
                rarest |= e
                n_rarest += 1
        rare_key = f"rarest-EFG footprint (<= {100 * RARE_EFG_PCT:g}% of PU each)"
    masks[rare_key] = rarest
    print(f"driver masks: m_soc theta-tail {int(masks['m_soc theta-tail'].sum()):,} cells | refugia densest (same area) | spike "
          f"{int(masks['connectivity spike (top 0.2%)'].sum()):,} | rare-attainable EFG footprint "
          f"{int(rare.sum()):,} cells ({100 * rare.mean():.0f}% of PU) from {n_rare}/{len(lc.efg_paths())} EFGs | "
          f"rarest-EFG footprint {int(rarest.sum()):,} cells ({100 * rarest.mean():.1f}%) from {n_rarest} EFGs")
    return masks


# ---- vector context: proposed IPCAs, existing PAs, placeholder names --------------------------
def ipca_layer(G):
    g = gpd.read_file(IPCA_SPEC["vector"]).to_crs(G.crs)
    g = g[ipca_rule(g)].reset_index(drop=True)
    g["name"] = g[IPCA_SPEC["name_field"]].astype(str)
    mask2d = rfeatures.rasterize(((geom, 1) for geom in g.geometry), out_shape=G.shape,
                                 transform=G.transform, fill=0, dtype="uint8").astype(bool) & G.pu
    return SimpleNamespace(gdf=g, mask2d=mask2d)


def pa_layer(G, min_km2=300):
    pa = gpd.read_file(config.PA_VECTOR).to_crs(G.crs).dissolve(by="PA_Name").reset_index()
    pa["km2"] = pa.geometry.area / 1e6
    return pa[pa.km2 >= min_km2].reset_index(drop=True)


def _bearing(dx, dy):
    ang = (math.degrees(math.atan2(dx, dy)) + 360) % 360
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int((ang + 22.5) // 45) % 8]


def placeholder_name(G, comp_mask2d, named):
    """'near <area> (<bearing>)' from the nearest named PA/IPCA proposal -- Ethan renames (decision e)."""
    rows, cols = np.where(comp_mask2d)
    cx = G.transform.c + (cols.mean() + 0.5) * G.transform.a
    cy = G.transform.f + (rows.mean() + 0.5) * G.transform.e
    pt = Point(cx, cy)
    d = named.geometry.distance(pt)
    i = int(d.idxmin())
    nm = named.loc[i, "name"]
    lon, lat = Transformer.from_crs(G.crs, "EPSG:4326", always_xy=True).transform(cx, cy)
    tag = f" ({lat:.1f}°N {abs(lon):.1f}°W)"          # keeps names unique when two clusters share a neighbour
    if d[i] == 0:
        return f"{nm} vicinity{tag}"
    c = named.loc[i, "geometry"].centroid
    return f"{_bearing(cx - c.x, cy - c.y)} of {nm}{tag}"


def named_areas(G):
    pa = pa_layer(G)[["PA_Name", "geometry"]].rename(columns={"PA_Name": "name"})
    ip = ipca_layer(G).gdf[["name", "geometry"]]
    return gpd.GeoDataFrame(pd.concat([pa, ip], ignore_index=True), geometry="geometry", crs=G.crs)


# ---- cluster naming (package spec v1.12 decision e; communities analysis) ----------------------------------------------
# Every cluster is labelled "Cluster N (Region)" with the region words from the bear-coexistence communities layer -- a
# tessellation of Y2Y into 108 census divisions / counties -- through the CURATED lookup unit -> region / sub-region
# (analyses/communities/02_region_names -> spec/region_lookup.csv; Ethan vets the words). Naming only: no number in the
# optimization or the tiers depends on the layer. The landmark placeholder (placeholder_name) stays as the secondary descriptor.
COEX_GPKG = config.INPUT_DIR / "bear_coexistence" / "CoexistenceGroup_CDCounty_SpatJoin" / "CoexistenceGroup_CDCounty_Join.gpkg"
COEX_LOOKUP = ROOT / "analyses" / "communities" / "spec" / "region_lookup.csv"
REGION_SECONDARY_MIN = 0.15          # a unit holding >= this share of a cluster adds its sub-region to the label


def coexistence_layer(G):
    """The 108-unit communities tessellation joined to the region lookup, rasterized to 1 km zone ids (1..108, 0 outside);
    None when the lookup has not been written yet (labels then fall back to the landmark placeholder)."""
    if not (COEX_GPKG.exists() and COEX_LOOKUP.exists()):
        return None
    g = gpd.read_file(COEX_GPKG).to_crs(G.crs).reset_index(drop=True)
    lk = pd.read_csv(COEX_LOOKUP).set_index("fid")
    assert len(g) == len(lk) == 108, (len(g), len(lk))
    unit_col = "MappingUnit" if "MappingUnit" in g.columns else "MappingUni"
    assert (g[unit_col].values == lk.loc[g.index, "MappingUnit"].values).all(), "region_lookup.csv rows do not line up with the gpkg (fid order)"
    for c in ("region", "subregion", "admin1"):
        g[c] = lk.loc[g.index, c].values
    zones = rfeatures.rasterize(zip(g.geometry, g.index + 1), out_shape=G.shape, transform=G.transform, fill=0, dtype="int32")
    return SimpleNamespace(gdf=g, zones=zones, source=COEX_LOOKUP.name)


def region_of(CX, mask2d, secondary_min=REGION_SECONDARY_MIN):
    """(region, subregions, label) for a cluster mask: the unit holding the largest share of the cluster's cells names the
    region; every unit holding >= secondary_min adds its sub-region (share order, de-duplicated). label = 'Sub-region(s), Region'
    -- the package spec's examples ('Purcell-Columbia, Kootenays'; 'Sacred Headwaters, Stikine')."""
    if CX is None:
        return "", "", ""
    z = CX.zones[mask2d]; z = z[z > 0]
    if z.size == 0:
        return "", "", ""
    ids, n = np.unique(z, return_counts=True); order = np.argsort(-n); share = n / n.sum()
    lead = CX.gdf.loc[int(ids[order[0]]) - 1]
    subs = [str(CX.gdf.loc[int(i) - 1, "subregion"]) for i, s in zip(ids[order], share[order]) if s >= secondary_min]
    subs = [x for x in dict.fromkeys(subs) if x and x != "nan"]
    region = str(lead["region"])
    label = ", ".join([*(x for x in subs if x != region), region]) if subs else region
    return region, "; ".join(subs), label


# ---- E17 one-pager inputs ----------------------------------------------------------------------
def e17_shifts(G, version=None):
    """Leave-one-theme-out latitude shifts vs the S0 anchor. Reads the ACTIVE version's runs (`runs_<version>/e17_t3`,
    solved by 18b on the curated block) and falls back to the v1 record (`runs/e17_t3`, notebook 16) when the arms are
    absent; `basis` says which. Pass version="v1" for the 40-class comparison explicitly."""
    lat, _ = latlon(G)
    root = config.y2y_paths(version).runs if version else RUNS
    basis = version or VP.version
    if not (root / "e17_t3" / "efg_out" / "run" / "portfolio.tif").exists():
        root, basis = RUNS_V1, "v1 (40-class block; run 18b's E17-T3 cell for the curated block)"
    s0 = ec.read_selections(root / "s0_ssp585_theta5" / "anchor.tif", G.pu)[0]
    base = float(lat[s0 & G.disc].mean())
    rows = []
    for b in ["core_habitat", "connectivity", "biodiversity", "carbon", "structural_connectivity", "climate_corridors", "efg"]:   # v3.1 order first; absent arms skipped
        p = root / "e17_t3" / f"{b}_out" / "run" / "portfolio.tif"
        if not p.exists():
            continue
        sel = ec.read_selections(p, G.pu)[0]
        rows.append(dict(block_out=b, mean_lat=float(lat[sel & G.disc].mean()),
                         delta_lat=float(lat[sel & G.disc].mean() - base), jaccard_vs_s0=jaccard(sel, s0), basis=basis))
    return base, pd.DataFrame(rows)


# ---- star grid + deck --------------------------------------------------------------------------
STAR_GRID = dict(panel_w=5.8, panel_h=5.2, wspace=1.05, hspace=0.6, top=0.82, bottom=0.10)   # shared by the locator maps (same geometry)


def plot_star_grid(profiles, path, title, ncols=4, rmax=1.0, ref=0.5, fs_axis=11, fs_title=13, fs_tick=9, fs_suptitle=15, lw=2.0, footnote=True, tight=True, label_pad=8, dpi=200):
    """profiles: list of dict(title=, values={axis: v}, color=). One shared radial scale."""
    import matplotlib.pyplot as plt
    import textwrap
    n = len(profiles)
    ncols = min(ncols, max(n, 1))
    nrows = int(math.ceil(n / ncols))
    L = STAR_GRID
    fig, axes = plt.subplots(nrows, ncols, figsize=(L["panel_w"] * ncols, L["panel_h"] * nrows), subplot_kw=dict(polar=True))
    fig.subplots_adjust(wspace=L["wspace"], hspace=L["hspace"], top=L["top"], bottom=L["bottom"])   # room for the outward-anchored labels
    axes = np.atleast_1d(axes).ravel()
    k = len(STAR_AXES)
    ang = np.linspace(0, 2 * np.pi, k, endpoint=False)
    for ax, pr in zip(axes, profiles):
        vals = [pr["values"][a] for a in STAR_AXES]
        closed = np.r_[vals, vals[0]]
        ax.plot(np.r_[ang, ang[0]], closed, color=pr.get("color", "#2b4f7d"), lw=lw)
        ax.fill(np.r_[ang, ang[0]], closed, color=pr.get("color", "#2b4f7d"), alpha=0.25)
        ax.plot(np.r_[ang, ang[0]], [ref] * (k + 1), color="#888888", lw=0.9, ls="--")
        # naturalness (1 - gHM) drawn as a plain sixth axis (Ethan 2026-09-04): it is in the formulation; that it
        # cannot move the answer (leverage 0.042) is a paper finding, not a director-meeting caption
        ax.set_xticks(ang)
        ax.set_xticklabels([a.replace(" ", "\n") for a in STAR_AXES], fontsize=fs_axis)
        for t, a in zip(ax.get_xticklabels(), ang):                  # labels sit OUTSIDE the ring: anchor by their angle
            c, sn = math.cos(a), math.sin(a)
            t.set_ha("left" if c > 0.1 else "right" if c < -0.1 else "center")
            t.set_va("bottom" if sn > 0.1 else "top" if sn < -0.1 else "center")
        ax.set_ylim(0, rmax)
        ax.set_yticks([0.25, 0.5, 0.75, 1.0]); ax.set_yticklabels(["", "0.5", "", "1"], fontsize=fs_tick)
        ax.tick_params(axis="x", pad=label_pad)
        ax.set_title("\n".join(textwrap.fill(t, 34) for t in pr["title"].split("\n")), fontsize=fs_title, fontweight=600, pad=18)
    for ax in axes[n:]:
        ax.axis("off")
    if title:
        fig.suptitle(title, fontsize=fs_suptitle, y=1.01, fontweight=600)
    if footnote:
        fig.text(0.01, -0.01, "axes = cluster mean percentile vs the ALLOCATABLE landscape (dashed ring 0.5 = the typical unprotected cell); "
                 "representativeness = percentile of ecosystem classes present per cell; naturalness = 1 - human modification",
                 fontsize=9, color="#444444")
    fig.savefig(path, dpi=dpi, bbox_inches="tight" if tight else None)
    return fig


def build_deck(slides, path, subtitle=""):
    """Draft .pptx: one slide per dict(title=, image=, bullets=[], notes=). Editable starting point."""
    from pptx import Presentation
    from pptx.util import Inches, Pt
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    for s in slides:
        sl = prs.slides.add_slide(prs.slide_layouts[5])
        sl.shapes.title.text = s["title"]
        sl.shapes.title.text_frame.paragraphs[0].font.size = Pt(26)
        img = s.get("image")
        if img and Path(img).exists():
            pic = sl.shapes.add_picture(str(img), Inches(0.4), Inches(1.3), height=Inches(5.9))
            if pic.width > Inches(8.6):
                pic.width, pic.height = Inches(8.6), int(pic.height * Inches(8.6) / pic.width)
        tb = sl.shapes.add_textbox(Inches(9.2), Inches(1.3), Inches(3.9), Inches(5.9)).text_frame
        tb.word_wrap = True
        for i, b in enumerate(s.get("bullets", [])):
            p = tb.paragraphs[0] if i == 0 else tb.add_paragraph()
            p.text = b; p.font.size = Pt(13)
        if s.get("notes"):
            sl.notes_slide.notes_text_frame.text = s["notes"]
    prs.save(str(path))
    return path


# ---- T-D4: ecoregion layer (optional data dependency) -----------------------------------------
def ecoregion_layer(G):
    """First vector in input_data/ecoregions/ rasterized to 1 km zone ids; None when absent (T-D4 pending)."""
    if not ECOREGIONS_DIR.exists():
        return None
    files = sorted([*ECOREGIONS_DIR.glob("*.shp"), *ECOREGIONS_DIR.glob("*.gpkg"), *ECOREGIONS_DIR.glob("*.geojson")])
    if not files:
        return None
    g = gpd.read_file(files[0]).to_crs(G.crs)
    fld = next((f for f in ECOREGION_NAME_FIELDS if f in g.columns), None)
    if fld is None:
        if files[0].suffix.lower() == ".shp" and not files[0].with_suffix(".dbf").exists():
            raise FileNotFoundError(f"{files[0].name} has no .dbf beside it (attributes missing: {list(g.columns)}) -- re-export the "
                                    "ecoregion layer WITH its attribute table (RESOLVE 2017: ECO_NAME / BIOME_NAME) into input_data/ecoregions/")
        raise ValueError(f"{files[0].name}: no recognised name field among {ECOREGION_NAME_FIELDS}")
    g = g.dissolve(by=fld).reset_index()
    g["zone_id"] = np.arange(1, len(g) + 1)
    zones = rfeatures.rasterize(zip(g.geometry, g.zone_id), out_shape=G.shape, transform=G.transform,
                                fill=0, dtype="int32")
    return SimpleNamespace(gdf=g, name_field=fld, zones=zones, source=files[0].name)


def tier_achievement(G, cumulative_masks):
    """Capture per block for CUMULATIVE tier masks (1-D over PU, locked included) -- zero-solve.

    capture_f = share of feature f's regional total inside the mask; block = mean over its features
    (the T-D3 convention). Returns a long DataFrame (tier, block, feature, capture)."""
    rows = []
    vals = {}
    for b, feats in config.BLOCKS.items():
        for f in feats:
            vals[f] = np.nan_to_num(lc._read(config.Y2Y_STACK_DIR / f"{f}.tif")[G.pu], nan=0.0)
    for tier, m in cumulative_masks.items():
        for b, feats in config.BLOCKS.items():
            caps = [float(vals[f][m].sum() / vals[f].sum()) for f in feats]
            for f, c in zip(feats, caps):
                rows.append(dict(tier=tier, block=b, feature=f, capture=c))
            rows.append(dict(tier=tier, block=b, feature="BLOCK", capture=float(np.mean(caps))))
    return pd.DataFrame(rows)


# ---- basemap: Natural Earth 10 m admin-1 (states/provinces) + international border --------------
ADMIN_PATH = config.INPUT_DIR / "basemap" / "ne_10m_admin_1_states_provinces.shp"
ADMIN_LINES_PATH = config.INPUT_DIR / "basemap" / "ne_10m_admin_1_states_provinces_lines.shp"

def admin_layer(G, pad_m=150e3):
    """Internal admin-1 boundary lines, the coastline (country polygon boundaries), the shared Canada-US border
    (intersection of the two country boundaries) and label points -- all clipped to the map extent (+pad)."""
    x0 = G.transform.c; y1 = G.transform.f
    x1 = x0 + G.shape[1] * G.transform.a; y0 = y1 + G.shape[0] * G.transform.e
    bbox = shp_box(x0 - pad_m, y0 - pad_m, x1 + pad_m, y1 + pad_m)
    g = gpd.read_file(ADMIN_PATH).to_crs(G.crs)
    g = g[g.intersects(bbox)].copy(); g["geometry"] = g.geometry.intersection(bbox)
    lines = gpd.read_file(ADMIN_LINES_PATH).to_crs(G.crs)
    lines = lines[lines.intersects(bbox)].copy(); lines["geometry"] = lines.geometry.intersection(bbox)
    countries = g.dissolve(by="admin").reset_index()
    coast = countries.geometry.boundary
    border = None
    if len(countries) >= 2:
        b = [c.buffer(500) for c in countries.geometry.boundary]        # 500 m tolerance for the shared border
        border = b[0]
        for bb in b[1:]:
            border = border.intersection(bb)
    inner = shp_box(x0, y0, x1, y1)
    lab = g.copy(); lab["geometry"] = lab.geometry.intersection(inner)
    lab = lab[~lab.geometry.is_empty]; lab["pt"] = lab.geometry.representative_point()
    return SimpleNamespace(admin1_lines=lines, coast=coast, border=border, labels=lab[["postal", "name", "pt"]])


def _lines_px(G, geom):
    parts = geom.geoms if hasattr(geom, "geoms") else [geom]
    out = []
    for part in parts:
        if part.is_empty:
            continue
        if part.geom_type == "Polygon":
            out += _lines_px(G, part.exterior); continue
        if part.geom_type in ("GeometryCollection", "MultiPolygon", "MultiLineString"):
            out += _lines_px(G, part); continue
        x, y = np.asarray(part.coords)[:, :2].T
        px, py = xy_to_px(G, x, y)
        out.append(np.c_[px, py])
    return out


def draw_admin(ax, G, A, color="#7A7A7A", lw=0.6, coast_color="#9CB3C0", coast_lw=0.3,
               border_color="#4a4a4a", border_lw=1.0, labels=False, fs=7, dash=(4, 2)):
    """Coast, admin-1 lines (dashed) and the shared border in the corridors_mapstyle BASE tokens (2026-09-14; postal
    labels off by default -- draw_basemap places full province names on open land)."""
    import matplotlib.patheffects as _pe
    for geom in A.coast:
        for ln in _lines_px(G, geom):
            ax.plot(ln[:, 0], ln[:, 1], color=coast_color, lw=coast_lw, zorder=0.3)
    for geom in A.admin1_lines.geometry:
        for ln in _lines_px(G, geom):
            ax.plot(ln[:, 0], ln[:, 1], color=color, lw=lw, ls=(0, dash) if dash else "-", zorder=0.32)
    if A.border is not None:
        for ln in _lines_px(G, A.border):
            ax.plot(ln[:, 0], ln[:, 1], color=border_color, lw=border_lw, zorder=0.35)
    if labels:
        for _, r in A.labels.iterrows():
            px, py = xy_to_px(G, r.pt.x, r.pt.y)
            ax.text(px, py, r.postal, fontsize=fs, color="#555555", ha="center", va="center", zorder=4.5,
                    path_effects=[_pe.withStroke(linewidth=2, foreground="white", alpha=0.8)])


# ---- basemap: the northern package's cartography (corridors_mapstyle BASE tokens) ported to the Y2Y frame ------------
# DISPLAY ONLY -- nothing here enters any computation. Land / ocean / lakes / rivers from Natural Earth 10 m, the
# Copernicus GLO-90 hillshade warped to 300 m on this frame (input_data/basemap/hillshade_y2y_300m.tif, multiply at 18%),
# province names placed on open land OUTSIDE the region, hand-listed towns.
BASEMAP = dict(land="#F7F7F5", water="#CFE0EA", ocean="#E4EEF3", coast=("#9CB3C0", 0.3), admin=("#7A7A7A", 0.6, (4, 2)),
               border=("#4a4a4a", 1.0), y2y=("#333333", 0.8, (6, 3)), hillshade_alpha=0.18,
               jurisdiction=("#8A8A8A", 9.5), town=("#2B2B2B", 8.0))
HILLSHADE_PATH = config.INPUT_DIR / "basemap" / "hillshade_y2y_300m.tif"
Y2Y_TOWNS = {                                   # name: (lat, lon); the director maps draw STYLE["towns"] of these
    "Inuvik": (68.36, -133.72), "Norman Wells": (65.28, -126.83), "Dawson City": (64.06, -139.43),
    "Fort Simpson": (61.86, -121.35), "Whitehorse": (60.72, -135.06), "Watson Lake": (60.06, -128.71),
    "Fort Nelson": (58.81, -122.70), "Fort St. John": (56.25, -120.85), "Smithers": (54.78, -127.17),
    "Prince George": (53.92, -122.75), "Edmonton": (53.55, -113.49), "Jasper": (52.87, -118.08),
    "Kamloops": (50.67, -120.33), "Banff": (51.18, -115.57), "Calgary": (51.05, -114.07),
    "Revelstoke": (51.00, -118.20), "Cranbrook": (49.51, -115.77), "Nelson": (49.49, -117.29),
    "Kalispell": (48.20, -114.31), "Spokane": (47.66, -117.43), "Missoula": (46.87, -114.00),
    "Helena": (46.59, -112.04), "Bozeman": (45.68, -111.04), "Salmon": (45.18, -113.90),
    "Boise": (43.62, -116.21), "Jackson": (43.48, -110.76),
    # Tahltan territory / Highway 37 (inset A, Ethan 2026-09-15)
    "Iskut": (57.84, -129.98), "Dease Lake": (58.44, -130.01), "Telegraph Creek": (57.90, -131.16), "Stewart": (55.94, -129.99),
    "Hazelton": (55.26, -127.67),
}
POSTAL_DISPLAY = {"NT": "NWT"}                   # display form of a postal code where the common usage differs (Ethan 2026-09-15)
PROVINCE_LABEL = {"British Columbia": "BRITISH\nCOLUMBIA", "Northwest Territories": "NORTHWEST\nTERRITORIES",
                  "Yukon": "YUKON", "Alberta": "ALBERTA", "Alaska": "ALASKA", "Saskatchewan": "SASKATCHEWAN",
                  "Nunavut": "NUNAVUT", "Montana": "MONTANA", "Idaho": "IDAHO", "Wyoming": "WYOMING",
                  "Washington": "WASHINGTON", "Oregon": "OREGON", "Nevada": "NEVADA", "Utah": "UTAH",
                  "California": "CALIFORNIA", "North Dakota": "NORTH\nDAKOTA", "South Dakota": "SOUTH\nDAKOTA"}


def _frame_bounds(G):
    x0 = G.transform.c; y1 = G.transform.f
    return x0, y1 + G.shape[0] * G.transform.e, x0 + G.shape[1] * G.transform.a, y1


def _poly_rings_px(G, geom):
    """Exterior rings of a (Multi)Polygon in pixel coordinates (holes ignored: basemap fills only)."""
    out = []
    for p in (geom.geoms if hasattr(geom, "geoms") else [geom]):
        if p.is_empty or p.geom_type != "Polygon":
            continue
        x, y = np.asarray(p.exterior.coords)[:, :2].T
        px, py = xy_to_px(G, x, y)
        out.append(np.c_[px, py])
    return out


def basemap_layer(G, pad_m=150e3, river_rank=6, min_share=0.015, keepout_km=50, edge_margin=0.035):
    """Land polygons, lakes, rivers, the Y2Y outline, province label points and towns for the frame (map coordinates;
    drawn in pixel coordinates by draw_basemap). Province names sit at the pole of inaccessibility of the province's
    open land OUTSIDE the region (region buffered `keepout_km`) when that is at least a quarter of its area in frame."""
    from shapely.ops import polylabel
    x0, y0, x1, y1 = _frame_bounds(G)
    bbox = shp_box(x0 - pad_m, y0 - pad_m, x1 + pad_m, y1 + pad_m); inner = shp_box(x0, y0, x1, y1)
    bm = config.INPUT_DIR / "basemap"
    adm = gpd.read_file(ADMIN_PATH).to_crs(G.crs)
    adm = adm[adm.intersects(bbox)].copy(); adm["geometry"] = adm.geometry.intersection(bbox)
    land = adm.dissolve(by="admin").reset_index()
    lakes = pd.concat([gpd.read_file(bm / "ne_10m_lakes.shp"), gpd.read_file(bm / "ne_10m_lakes_north_america.shp")], ignore_index=True)
    lakes = gpd.GeoDataFrame(lakes, crs="EPSG:4326").to_crs(G.crs)
    lakes = lakes[lakes.intersects(bbox)].copy(); lakes["geometry"] = lakes.geometry.intersection(bbox)
    rivers = pd.concat([gpd.read_file(bm / "ne_10m_rivers_lake_centerlines.shp"), gpd.read_file(bm / "ne_10m_rivers_north_america.shp")], ignore_index=True)
    rivers = gpd.GeoDataFrame(rivers, crs="EPSG:4326").to_crs(G.crs)
    rivers = rivers[(rivers.scalerank <= river_rank) & rivers.intersects(bbox)].copy(); rivers["geometry"] = rivers.geometry.intersection(bbox)
    region = gpd.read_file(config.CORRIDOR_REF).to_crs(G.crs).geometry.union_all()
    T = Transformer.from_crs("EPSG:4326", G.crs, always_xy=True)
    town_pts = {n: T.transform(lon, lat) for n, (lat, lon) in Y2Y_TOWNS.items()}
    keep_out = unary_union([region.buffer(keepout_km * 1000)] + [Point(*xy).buffer(45_000) for xy in town_pts.values()])
    frame_area = (x1 - x0) * (y1 - y0)
    labels = []
    for _, r in adm.iterrows():
        g = r.geometry.intersection(inner)
        if g.is_empty or g.area / frame_area < min_share:
            continue
        free = g.difference(keep_out)                       # open land: outside the region and away from every town
        if free.is_empty:
            continue
        best, best_r = None, 0.0
        for piece in (list(free.geoms) if hasattr(free, "geoms") else [free]):
            if piece.geom_type != "Polygon" or piece.area < 0.02 * g.area:
                continue
            pt = polylabel(piece, tolerance=2000); rad = pt.distance(piece.boundary)
            if rad > best_r:
                best, best_r = pt, rad
        if best is None:
            continue
        fx, fy = (best.x - x0) / (x1 - x0), (best.y - y0) / (y1 - y0)
        if min(fx, 1 - fx, fy, 1 - fy) < edge_margin:                 # a name pinned to the frame edge is a sliver: skip it
            continue
        labels.append(dict(name=PROVINCE_LABEL.get(r["name"], str(r["name"]).upper()), postal=str(r["postal"]), x=best.x, y=best.y,
                           r_km=best_r / 1000))                        # draw_basemap applies the width threshold per mode
    return SimpleNamespace(land=land, lakes=lakes, rivers=rivers, region=region, labels=labels, towns=town_pts, admin1=adm[["postal", "name", "geometry"]].copy())


def read_hillshade(G, path=HILLSHADE_PATH):
    """The 300 m hillshade resampled onto this 1 km frame (0-255; None if the file is absent)."""
    if not Path(path).exists():
        return None
    from rasterio.windows import from_bounds
    from rasterio.enums import Resampling
    x0, y0, x1, y1 = _frame_bounds(G)
    with rasterio.open(path) as src:
        win = from_bounds(x0, y0, x1, y1, src.transform)
        return src.read(1, window=win, out_shape=G.shape, resampling=Resampling.average, boundless=True, fill_value=255)


def draw_basemap(ax, G, B, hs=None, water=True, names=True, towns=(), z_hs=0.6, alpha=None, fs_scale=1.0, window=None, name_fs=None,
                 min_radius_km=(45, 18), avoid_sw=True, skip=()):
    """names: True = full names in tracked caps (open land >= 45 km wide), 'abbrev' = postal codes (>= 18 km), False = none."""
    """Ocean ground, land fill, lakes + rivers, the region outline, province names, towns -- pixel coordinates."""
    from matplotlib.collections import PolyCollection
    import matplotlib.patheffects as _pe
    ax.set_facecolor(BASEMAP["ocean"])
    ax.add_collection(PolyCollection([r for g in B.land.geometry for r in _poly_rings_px(G, g)], facecolors=BASEMAP["land"], edgecolors="none", zorder=0.1))
    if hs is not None:                                           # darkening-only multiply: alpha = 0.18 x (1 - shade)
        rgba = np.zeros(hs.shape + (4,), np.float32); rgba[..., 3] = (alpha or BASEMAP["hillshade_alpha"]) * (1.0 - hs.astype(np.float32) / 255.0)
        ax.imshow(rgba, interpolation="bilinear", zorder=z_hs)
    if water:
        ax.add_collection(PolyCollection([r for g in B.lakes.geometry for r in _poly_rings_px(G, g)], facecolors=BASEMAP["water"], edgecolors="none", zorder=0.7))
        for _, r in B.rivers.iterrows():
            lw = float(np.clip(1.0 - 0.08 * float(r.scalerank), 0.3, 0.9))
            for ln in _lines_px(G, r.geometry):
                ax.plot(ln[:, 0], ln[:, 1], color=BASEMAP["water"], lw=lw, zorder=0.7)
    col, lw, dash = BASEMAP["y2y"]
    for ln in _lines_px(G, B.region.boundary):
        ax.plot(ln[:, 0], ln[:, 1], color=col, lw=lw, ls=(0, dash), zorder=3.2)
    px0, px1, py0, py1 = window or (0, G.shape[1], 0, G.shape[0])          # pixel window (x0, x1, y_top, y_bottom)
    inside = lambda px, py: px0 < px < px1 and py0 < py < py1
    mx, my = 0.12 * (px1 - px0), 0.03 * (py1 - py0)                          # a town's label must fit inside the window
    town_inside = lambda px, py: px0 + 0.02 * (px1 - px0) < px < px1 - mx and py0 + my < py < py1 - my
    if names:
        jc, jfs = BASEMAP["jurisdiction"]; fs = (name_fs or jfs) * fs_scale
        abbrev = names == "abbrev"; r_min = min_radius_km[1] if abbrev else min_radius_km[0]
        for L in B.labels:
            px, py = xy_to_px(G, L["x"], L["y"])
            if not inside(px, py) or L["r_km"] < r_min or L["postal"] in skip:
                continue
            if avoid_sw and px < px0 + 0.26 * (px1 - px0) and py > py1 - 0.13 * (py1 - py0):   # the scale bar / north arrow corner
                if not abbrev:
                    continue
                py = py1 - 0.16 * (py1 - py0)                                                    # a code is short: lift it above the bar
            text = POSTAL_DISPLAY.get(L["postal"], L["postal"]) if abbrev else " ".join(L["name"])
            ax.text(px, py, text, fontsize=fs, fontweight=600, color=jc, alpha=0.9, ha="center", va="center", zorder=4.5,
                    linespacing=1.15, clip_on=True, path_effects=[_pe.withStroke(linewidth=0.3 * fs, foreground="white", alpha=0.8)])
    tc, tfs = BASEMAP["town"]
    for n in towns:
        if n not in B.towns:
            continue
        px, py = xy_to_px(G, *B.towns[n])
        if not town_inside(px, py):
            continue
        ax.plot(px, py, marker="o", ms=3.2 * fs_scale, color=tc, mec="white", mew=0.7, zorder=6)
        ax.annotate(n, (px, py), xytext=(4, 3), textcoords="offset points", fontsize=tfs * fs_scale, color=tc, zorder=6, clip_on=True,
                    path_effects=[_pe.withStroke(linewidth=2.0, foreground="white")])


def north_arrow(ax, G, loc=(0.06, 0.055), length_px=70, fs=9):
    """A plain north arrow (grid north) at an axes fraction (x from left, y from bottom)."""
    H, W = G.shape
    x, y1 = loc[0] * W, (1 - loc[1]) * H; y0 = y1 - length_px
    ax.annotate("", xy=(x, y0), xytext=(x, y1), arrowprops=dict(arrowstyle="-|>", color="black", lw=1.4, mutation_scale=14), zorder=5)
    ax.text(x, y0 - 6, "N", ha="center", va="bottom", fontsize=fs, fontweight=600, zorder=5)


def read_hillshade_window(G, window, scale=3, path=HILLSHADE_PATH):
    """The 300 m hillshade for a pixel window (x0, x1, y_top, y_bottom) of the 1 km frame, at `scale` x the 1 km pixels."""
    if not Path(path).exists():
        return None
    from rasterio.windows import from_bounds
    from rasterio.enums import Resampling
    px0, px1, py0, py1 = window
    x0 = G.transform.c + px0 * G.transform.a; x1 = G.transform.c + px1 * G.transform.a
    yt = G.transform.f + py0 * G.transform.e; yb = G.transform.f + py1 * G.transform.e
    with rasterio.open(path) as src:
        win = from_bounds(x0, yb, x1, yt, src.transform)
        return src.read(1, window=win, out_shape=(int(round((py1 - py0) * scale)), int(round((px1 - px0) * scale))),
                        resampling=Resampling.average, boundless=True, fill_value=255)


def label_areas_px(ax, G, gdf, name_col, window, top_n=5, color="0.25", fs=7.5, taken=None):
    """Label the biggest named areas intersecting a pixel window (italic, white halo), greedy declutter on a 45 km grid."""
    import matplotlib.patheffects as _pe
    px0, px1, py0, py1 = window
    x0 = G.transform.c + px0 * G.transform.a; x1 = G.transform.c + px1 * G.transform.a
    yt = G.transform.f + py0 * G.transform.e; yb = G.transform.f + py1 * G.transform.e
    win = shp_box(x0, yb, x1, yt)
    g = gdf[gdf.intersects(win)].copy()
    if not len(g):
        return taken or []
    g["geometry"] = g.geometry.intersection(win); g = g[~g.geometry.is_empty]
    g["_a"] = g.geometry.area; g = g.sort_values("_a", ascending=False).head(top_n)
    taken = list(taken or [])
    import textwrap as _tw
    span = px1 - px0
    for _, r in g.iterrows():
        pt = r.geometry.representative_point(); px, py = xy_to_px(G, pt.x, pt.y)
        if any(abs(px - tx) < 16 * fs and abs(py - ty) < 3.3 * fs for tx, ty in taken):
            continue
        ax_w_in = ax.get_position(original=True).width * ax.figure.get_figwidth()                      # the axes box width in inches (before aspect)
        px_per_in = span / max(ax_w_in, 1e-6)                                                             # data px per inch
        chars = max(12, int(0.55 * ax_w_in * 72 / (0.5 * fs)))                                          # a line <= ~55% of the panel width
        name = "\n".join(_tw.wrap(str(r[name_col]).split(" [")[0].split(" (")[0], chars))
        half = 0.5 * max(len(l) for l in name.split("\n")) * 0.5 * fs / 72 * px_per_in                  # ~half label width (data px)
        hh = 0.5 * len(name.split("\n")) * 1.2 * fs / 72 * px_per_in                                    # ~half label height
        px = float(np.clip(px, px0 + half + 3, px1 - half - 3)); py = float(np.clip(py, py0 + hh + 3, py1 - hh - 3))   # inside the window
        ax.text(px, py, name, fontsize=fs, fontstyle="italic", color=color, ha="center", va="center", zorder=5.5, clip_on=True, linespacing=1.1,
                path_effects=[_pe.withStroke(linewidth=2.0, foreground="white", alpha=0.9)])
        taken.append((px, py))
    return taken


def label_jurisdictions_window(ax, G, B, window, fs=14, min_share=0.04, avoid_sw=True, skip=(), force=()):
    """Postal codes of the provinces / states inside a pixel window, each at the pole of inaccessibility of its part of the
    window (faint caps, white halo) -- for insets and locator windows. Returns the label positions (for decluttering)."""
    from shapely.ops import polylabel
    import matplotlib.patheffects as _pe
    px0, px1, py0, py1 = window
    x0 = G.transform.c + px0 * G.transform.a; x1 = G.transform.c + px1 * G.transform.a
    yt = G.transform.f + py0 * G.transform.e; yb = G.transform.f + py1 * G.transform.e
    win = shp_box(x0, yb, x1, yt); jc, _ = BASEMAP["jurisdiction"]; out = []; span = px1 - px0
    outside = win.difference(B.region)                                     # the open land around the region (Ethan: codes only there)
    for _, r in B.admin1.iterrows():
        code = str(r["postal"])
        if code in skip:
            continue
        g = r.geometry.intersection(win)
        if g.is_empty or (g.area < min_share * win.area and code not in force):
            continue
        free = g.intersection(outside)
        best, best_r = None, 0.0
        for q in (free.geoms if hasattr(free, "geoms") else [free]):
            if q.geom_type != "Polygon" or q.is_empty:
                continue
            pt = polylabel(q, tolerance=1000); rad = pt.distance(q.boundary)
            if rad > best_r:
                best, best_r = pt, rad
        if best is None or (best_r < 0.055 * span * abs(G.transform.a) and code not in force):   # no white space wide enough: leave it off (unless forced)
            continue
        px, py = xy_to_px(G, best.x, best.y)
        if avoid_sw and px < px0 + 0.30 * span and py > py1 - 0.17 * span:      # the scale-bar corner: lift the code above the bar
            py = py1 - 0.20 * span
        for _ in range(6):                                                      # stack upward if it lands on an earlier code
            if not any(abs(px - tx) < 0.14 * span and abs(py - ty) < 0.08 * span for tx, ty in out):
                break
            py -= 0.09 * span
        ax.text(px, py, POSTAL_DISPLAY.get(code, code), fontsize=fs, fontweight=600, color=jc, alpha=0.9, ha="center", va="center", zorder=4.6, clip_on=True,
                path_effects=[_pe.withStroke(linewidth=0.3 * fs, foreground="white", alpha=0.85)])
        out.append((px, py))
    return out
