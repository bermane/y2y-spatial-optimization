"""Climate-scenario materiality diagnostic (Phase 1a) — imported by 02_preprocess_align.

QUESTION: `DATASETS["climate_type_macrorefugia"]` uses ONE of six AdaptWest realizations
(SSP 245/370/585 x 2041-2070/2071-2100). Does that choice change conservation priorities enough
to be worth six full 1 km solves, or a factor slot in the sensitivity design? This module
measures it directly off the aligned layers, with no prioritizr run.

DIAGNOSTIC ONLY — it reads, reports and plots. It never orients, never writes a raster, and
never touches `aligned_stack/`, the manifest, or `output_data/`.

WHY RAW VELOCITY IS THE RIGHT INPUT. The feature is oriented in 02 as `vmax - v` ("invert"),
because low backward velocity = the cell's future climate already exists nearby = macrorefugium.
That flip is a monotone affine map, so it changes neither correlation nor top-quantile set
membership -- the diagnostic is identical on raw velocity and needs no `vmax` decision. (Choosing
a SHARED vmax only matters if the six ever enter a solve together; `shared_anchor_report` prints
candidate anchors for that future decision without applying them.)

STATISTICS. Correlation is necessary but not sufficient: two surfaces can correlate at 0.95 and
still disagree about which cells make the top 30%. So the headline number is the **top-q Jaccard**
-- the overlap of the most-refugial `CLIMATE_SCENARIOS["top_q"]` (= BUDGET_PCT) of planning units,
which is the set the optimizer is actually choosing between. `context_ratio` puts that number on a
scale by computing the same statistic between macrorefugia and the eight other inputs.

The verdict rule lives in `config.CLIMATE_SCENARIOS["rule"]`, fixed before the numbers were seen.
"""
import types

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import rasterio
import geopandas as gpd
from matplotlib.lines import Line2D
from scipy.stats import rankdata

import config

SPREAD_CMAP = "magma"          # per-cell disagreement (sequential, dark = low)
OUTLINE_COLOR = "black"


# ---- paths + warp verification (the warp itself is 02's job) ----
def warp_paths():
    """key -> expected stage-1 output path. 02 cell 6a writes these via its own warp_to_grid."""
    cs = config.CLIMATE_SCENARIOS
    return {k: cs["out_dir"] / f"{k}.tif" for k in cs["members"]}


def check_identity(atol=1e-6):
    """The scenario 02 already uses must re-warp to the EXISTING stage-1 intermediate.

    `cleaned_aligned/climate_type_macrorefugia.tif` was produced by 02's normal alignment path
    from `rep_contains` = the `current` member. Re-warping that member through the same helper
    must reproduce it cell-for-cell. This is the guard that the six new rasters really are
    comparable to the layer already in the analysis -- if it fails, the warp arguments drifted."""
    cs = config.CLIMATE_SCENARIOS
    new = warp_paths()[cs["current"]]
    old = config.ALIGNED_DIR / "climate_type_macrorefugia.tif"
    if not old.exists():
        print(f"  identity check SKIPPED: {old.name} not present (stage 1 not run?)")
        return None
    a, b = _read(new), _read(old)
    both = np.isfinite(a) & np.isfinite(b)
    d = float(np.nanmax(np.abs(a[both] - b[both]))) if both.any() else np.nan
    n_mismatch = int((np.isfinite(a) != np.isfinite(b)).sum())
    assert n_mismatch == 0, f"NoData footprint differs from {old.name} in {n_mismatch:,} cells"
    assert d <= atol, f"re-warp of {cs['current']} differs from {old.name} by {d:g} (> {atol:g})"
    print(f"  identity check OK: {cs['current']} reproduces {old.name} (max |diff| = {d:g})")
    return d


def _read(path):
    with rasterio.open(path) as s:
        return s.read(1, masked=True).astype("float32").filled(np.nan)


# ---- load ----
def load(verbose=True):
    """Stack the six warped scenarios + define the analysis domain.

    Domain = cells finite in ALL six AND valid planning units in the hand-off stack, so every
    statistic is computed over the cells the optimizer actually decides about -- not over the
    cutline rectangle, which includes NoData corners."""
    cs = config.CLIMATE_SCENARIOS
    paths = warp_paths()
    missing = [k for k, p in paths.items() if not p.exists()]
    assert not missing, f"run 02 cell 6a first -- missing warped scenarios: {missing}"

    keys = list(cs["members"])
    arrs, ref = [], None
    for k in keys:
        with rasterio.open(paths[k]) as s:
            grid = (s.width, s.height, s.transform, s.crs.to_string())
            if ref is None:
                ref, transform, crs = grid, s.transform, s.crs
            assert grid == ref, f"{k} is not on the canonical grid: {grid} != {ref}"
            arrs.append(s.read(1, masked=True).astype("float32").filled(np.nan))
    stack = np.stack(arrs)

    cost = config.HANDOFF_DIR / "cost_uniform.tif"
    pu = np.isfinite(_read(cost)) if cost.exists() else np.ones(stack.shape[1:], bool)
    if not cost.exists():
        print("  NOTE: cost_uniform.tif absent -- domain falls back to scenario overlap only")
    domain = np.isfinite(stack).all(axis=0) & pu
    assert domain.any(), "empty analysis domain"

    A = types.SimpleNamespace(
        keys=keys, stack=stack, domain=domain, shape=stack.shape[1:],
        transform=transform, crs=crs, top_q=cs["top_q"],
        vals={k: stack[i][domain] for i, k in enumerate(keys)},
        outline=gpd.read_file(config.CORRIDOR_REF).to_crs(config.TARGET_CRS),
    )
    if verbose:
        print(f"scenarios : {len(keys)} on {A.shape[1]} x {A.shape[0]} grid")
        print(f"domain    : {int(domain.sum()):,} planning units "
              f"(finite in all six {'∩ hand-off PU' if cost.exists() else ''})")
        print(f"top_q     : {A.top_q:.0%} of PUs = the priority set used for the Jaccard")
    return A


# ---- statistics ----
def _top_set(vals, q):
    """Boolean over the domain: the `q` fraction with the LOWEST backward velocity.

    Low velocity = most refugial, so this is the "best q" set. Equivalent to the top q of the
    oriented `vmax - v` feature -- the flip is monotone, so the SET is identical either way."""
    k = max(1, int(round(q * vals.size)))
    m = np.zeros(vals.size, bool)
    m[np.argpartition(vals, k - 1)[:k]] = True     # k smallest
    return m


def _jaccard(a, b):
    u = int((a | b).sum())
    return float((a & b).sum() / u) if u else np.nan


def pairwise(A, show=True):
    """All 15 pairs: Pearson r, Spearman rho, and top-q Jaccard of the priority sets."""
    n = len(A.keys)
    X = np.stack([A.vals[k] for k in A.keys]).astype("float64")
    R = np.stack([rankdata(x) for x in X])          # rank once, then Pearson on ranks = Spearman
    pear, spear = np.corrcoef(X), np.corrcoef(R)
    sets = {k: _top_set(A.vals[k], A.top_q) for k in A.keys}

    jac = np.ones((n, n))
    rows = []
    for i in range(n):
        for j in range(i + 1, n):
            jac[i, j] = jac[j, i] = _jaccard(sets[A.keys[i]], sets[A.keys[j]])
            rows.append(dict(a=A.keys[i], b=A.keys[j], pearson=pear[i, j],
                             spearman=spear[i, j], jaccard=jac[i, j]))
    long = pd.DataFrame(rows).sort_values("jaccard").reset_index(drop=True)
    mats = {name: pd.DataFrame(m, index=A.keys, columns=A.keys)
            for name, m in (("pearson", pear), ("spearman", spear), ("jaccard", jac))}
    A.pairwise_long, A.pairwise_mats = long, mats

    if show:
        pd.set_option("display.width", 200)
        for name in ("spearman", "jaccard"):
            print(f"\n{name.upper()}" + (f" (top {A.top_q:.0%} priority-set overlap)"
                                         if name == "jaccard" else " (rank correlation)"))
            print(mats[name].round(3).to_string())
        print(f"\nmost divergent pair: {long.iloc[0].a} vs {long.iloc[0].b}  "
              f"(Jaccard {long.iloc[0].jaccard:.3f}, Spearman {long.iloc[0].spearman:.3f})")
        print(f"least divergent pair: {long.iloc[-1].a} vs {long.iloc[-1].b}  "
              f"(Jaccard {long.iloc[-1].jaccard:.3f}, Spearman {long.iloc[-1].spearman:.3f})")
    return long


def verdict(A, show=True):
    """Apply the PRE-REGISTERED rule from config -- fixed before these numbers existed."""
    assert hasattr(A, "pairwise_long"), "call pairwise(A) first"
    rule = config.CLIMATE_SCENARIOS["rule"]
    lo_s = float(A.pairwise_long.spearman.min())
    lo_j = float(A.pairwise_long.jaccard.min())
    imm, mat = rule["immaterial"], rule["material"]

    if lo_s >= imm["min_spearman"] and lo_j >= imm["min_jaccard"]:
        v, act = "IMMATERIAL", (
            "keep ONE scenario (state it as a deliberate choice), document with the pairwise\n"
            "    table in the supplement; DROP the scenario factor from the sensitivity design;\n"
            "    SKIP Phase 1b (the six 1 km solves).")
    elif lo_j < mat["max_jaccard_below"]:
        v, act = "MATERIAL", (
            "scenario ENTERS the sensitivity design as a factor; Phase 1b (six 1 km solves)\n"
            "    is WARRANTED, and the shared-vmax decision below becomes live.")
    else:
        v, act = "AMBIGUOUS", (
            "scenario ENTERS the sensitivity design as a factor; Phase 1b decided at the\n"
            "    screening gate on the strength of its Morris index.")
    A.verdict = v
    if show:
        print(f"\nworst-case across all 15 pairs: Spearman {lo_s:.3f} | Jaccard {lo_j:.3f}")
        print(f"thresholds: IMMATERIAL needs Spearman >= {imm['min_spearman']} AND "
              f"Jaccard >= {imm['min_jaccard']}; MATERIAL is any Jaccard < {mat['max_jaccard_below']}")
        print(f"\n  VERDICT: {v}\n    -> {act}")
    return v


def shared_anchor_report(A, show=True):
    """Candidate SHARED anchors for a future Phase 1b. REPORTS ONLY -- applies nothing.

    If the six ever enter a solve together they must share ONE affine map, else each sits on its
    own offset and between-scenario magnitude differences get laundered away. This prints the
    pooled percentile anchors alongside each layer's own range so that decision is made against a
    visible distribution rather than in the moment. Adopting them changes the macrorefugia feature
    even in the single-scenario case (03 sum-normalizes, so an additive offset does NOT cancel)
    and therefore forces a re-solve -- a separate sign-off."""
    plo, phi = config.CLIMATE_SCENARIOS["anchor_pctiles"]
    rows = [dict(scenario=k, min=v.min(), p_lo=np.percentile(v, plo),
                 mean=v.mean(), p_hi=np.percentile(v, phi), max=v.max())
            for k, v in A.vals.items()]
    tbl = pd.DataFrame(rows).set_index("scenario")
    pooled = np.concatenate(list(A.vals.values()))
    A.shared_anchors = (float(np.percentile(pooled, plo)), float(np.percentile(pooled, phi)))
    if show:
        print(f"\nper-scenario backward velocity, km/yr (p_lo/p_hi = p{plo}/p{phi}):")
        print(tbl.round(3).to_string())
        print(f"\ncandidate SHARED anchors (pooled p{plo}/p{phi}): "
              f"{A.shared_anchors[0]:.3f} / {A.shared_anchors[1]:.3f} km/yr")
        print(f"  vs the per-layer vmax currently used by 02: {max(r['max'] for r in rows):.3f}")
        print("  REPORTED ONLY -- not applied. Adopting shared anchors changes the feature and "
              "forces a re-solve.")
    return tbl


def context_ratio(A, show=True):
    """What does 'different' look like on this landscape? Same top-q Jaccard, but macrorefugia
    vs each OTHER input -- so a scenario-pair Jaccard can be read against genuinely distinct
    inputs rather than against an abstract 0-1 scale.

    Uses the ORIENTED hand-off layers for the other features (higher = better there), restricted
    to the same domain, so 'top q' means the same thing for every input."""
    ref = _top_set(A.vals[config.CLIMATE_SCENARIOS["current"]], A.top_q)
    rows = []
    for key, cfg in config.DATASETS.items():
        if cfg.get("multi") or key == "climate_type_macrorefugia":
            continue
        p = config.HANDOFF_DIR / f"{key}.tif"
        if not p.exists():
            continue
        v = _read(p)[A.domain]
        ok = np.isfinite(v)
        if not ok.all():                       # hand-off NoData inside our domain: compare on the
            v = np.where(ok, v, -np.inf)       # overlap only, never letting NaN win the partition
        rows.append(dict(input=key, jaccard=_jaccard(ref, _top_set(-v, A.top_q))))
    tbl = pd.DataFrame(rows).sort_values("jaccard", ascending=False).reset_index(drop=True)
    A.context_tbl = tbl
    if show:
        j = A.pairwise_long.jaccard if hasattr(A, "pairwise_long") else None
        print(f"\ntop {A.top_q:.0%} priority-set overlap: macrorefugia vs each OTHER input")
        print(tbl.round(3).to_string(index=False))
        if j is not None:
            print(f"\n  scenario-to-scenario Jaccard spans {j.min():.3f}-{j.max():.3f}")
            print(f"  input-to-input      Jaccard spans {tbl.jaccard.min():.3f}-"
                  f"{tbl.jaccard.max():.3f}   <- what a genuinely different input looks like")
    return tbl


# ---- maps ----
def _extent(A):
    t, (h, w) = A.transform, A.shape
    return [t.c, t.c + w * t.a, t.f + h * t.e, t.f]


def spread_map(A, fig_dir=None):
    """Two panels: per-cell SD across the six (absolute disagreement, km/yr) and the count of
    scenarios placing the cell in the top-q priority set (0 = never, 6 = always -- the direct
    analogue of a selection-frequency map, and the one to read for decision relevance)."""
    sd = np.full(A.shape, np.nan, "float32")
    sd[A.domain] = A.stack[:, A.domain].std(axis=0)

    votes = np.zeros(A.domain.sum(), "int8")
    for k in A.keys:
        votes += _top_set(A.vals[k], A.top_q)
    vote_map = np.full(A.shape, np.nan, "float32")
    vote_map[A.domain] = votes
    n_always = int((votes == len(A.keys)).sum())
    n_ever = int((votes > 0).sum())

    fig, axes = plt.subplots(1, 2, figsize=(13, 11))
    for ax, arr, title, cmap, cbar in (
        (axes[0], sd, "Disagreement: SD across the 6 scenarios", SPREAD_CMAP, "SD (km/yr)"),
        (axes[1], vote_map, f"Priority-set agreement (top {A.top_q:.0%})", "viridis",
         "scenarios selecting the cell"),
    ):
        im = ax.imshow(arr, extent=_extent(A), cmap=cmap, interpolation="nearest")
        A.outline.boundary.plot(ax=ax, color=OUTLINE_COLOR, linewidth=0.7)
        fig.colorbar(im, ax=ax, shrink=0.45, label=cbar)
        ax.set_title(title, fontsize=11)
        ax.set_aspect("equal"); ax.set_axis_off()
    axes[1].legend(handles=[Line2D([0], [0], color=OUTLINE_COLOR, lw=0.9, label="Y2Y boundary")],
                   loc="lower left", fontsize=8)
    fig.suptitle("Macrorefugia: do the six climate realizations disagree where it matters?",
                 fontsize=13, y=0.94)
    if fig_dir:
        fig_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(fig_dir / "climate_scenario_spread.png", dpi=150, bbox_inches="tight")
    plt.show()

    core = 100 * n_always / max(n_ever, 1)
    print(f"cells in the top {A.top_q:.0%} under ALL six : {n_always:,}")
    print(f"cells in the top {A.top_q:.0%} under ANY      : {n_ever:,}")
    print(f"robust core = {core:.1f}% of the ever-selected set "
          f"({'stable' if core >= 80 else 'scenario-dependent'})")
    return A
