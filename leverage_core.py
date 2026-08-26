"""Feature LEVERAGE — can a feature's weight move the solution at all? (02 QA + 03 target design)

WHY THIS EXISTS. The Morris screening in 06 found that four of the eight continuous layers barely
affect the priority map, and attributed it to spatial concentration (Spearman(mu*, Gini) = +0.905).
Gini is a correlate, not the mechanism. The mechanism is this:

    03 solves min-shortfall, whose objective is  sum_f  w_f * (1 - held_f)  at a 100% target,
    where held_f is the fraction of feature f's total captured by the selection. If a feature is
    spatially even, EVERY feasible selection of 30% of the cells captures ~30% of it, so its term
    is very nearly CONSTANT across the whole feasible set -- its weight multiplies a constant and
    cannot move the argmin. No weighting can rescue it.

So define

    leverage_f = (share of f's total held by its richest BUDGET_PCT of PUs)
               - (share held by its poorest BUDGET_PCT of PUs)

= the full range of captured fraction the budget can possibly span. leverage 0 => inert by
construction; leverage 0.88 (mineral-soil carbon) => the weight is a real lever. Measured against
the recorded Morris result this reproduces the mu* ranking at Spearman **+0.922**, i.e. as well as
Gini, but it is causal rather than correlational and it costs ZERO solves. `w_f * leverage_f`
therefore decomposes the objective's achievable swing exactly, which is what `influence_shares`
reports.

TWO USES.
  1. 02 QA -- flag any feature below `config.LEVERAGE_MIN` BEFORE a solve, so an inert layer is
     caught at design time instead of after a 130-solve sensitivity batch. Flag, never transform:
     same doctrine as the carbon-tail and connectivity QA in Stage 2. A flag is a prompt to ask
     WHICH of three causes applies -- (a) an orientation artefact (`vmax - v` destroyed 75% of
     macrorefugia's leverage; `1 - gHM` destroyed 94% of gHM's), (b) flattening by 1 km
     aggregation (the 05 finding that a 90 m highway vanishes at 1 km applies here too), or
     (c) genuine uniformity, in which case REPORT it and do not manufacture signal.
  2. 03 target design -- `target_cost_curve` derives a relative target from a stated density rule
     ("keep taking cells while marginal density >= M x the regional mean") instead of picking a
     round number. Under min-shortfall a feature that reaches its target drops out of the
     objective entirely, so a target is precisely a stopping rule: the optimizer already takes the
     densest cells first (the objective is linear), and the target says how far down the
     distribution to keep going.

DIAGNOSTIC ONLY. Nothing here writes a raster, touches `aligned_stack/`, the manifest or
`output_data/`.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

import config


# ---- readers ------------------------------------------------------------
def _read(path):
    """Band 1 as float64 with NoData -> NaN. float64 because Gini and the cumulative share are
    sums over ~1.3 M cells, where float32 accumulation error is visible in the 3rd decimal."""
    with rasterio.open(path) as src:
        return src.read(1, masked=True).astype("float64").filled(np.nan)


def pu_mask(handoff_dir=None):
    """The planning-unit mask, taken from the cost layer.

    02 applies ONE mask to every feature and to `cost_uniform` alike, so the cost layer's valid
    cells ARE the PU set -- no need to re-derive it by intersecting the features."""
    handoff_dir = Path(handoff_dir or config.HANDOFF_DIR)
    return np.isfinite(_read(handoff_dir / "cost_uniform.tif"))


def continuous_features():
    """Continuous feature names in manifest order (single-raster datasets, minus exclusions).

    Mirrors the continuous-layer loop in `config.write_manifest`, so the QA table lists exactly
    the features the optimizer will see."""
    return [k for k, c in config.DATASETS.items()
            if not c.get("multi") and k not in config.EXCLUDE_FEATURES]


def efg_paths(handoff_dir=None):
    handoff_dir = Path(handoff_dir or config.HANDOFF_DIR)
    return [p for p in sorted((handoff_dir / "iucn_efg").glob("*.tif"))
            if p.stem not in config.EXCLUDE_FEATURES]


# ---- the statistic ------------------------------------------------------
def _gini(v):
    v = np.sort(v)
    n = v.size
    tot = v.sum()
    if n == 0 or tot <= 0:
        return np.nan
    return float((2 * np.arange(1, n + 1) - n - 1).dot(v) / (n * tot))


def leverage_of(values, budget_pct=None):
    """(cap_min, cap_max, leverage) for one feature's values over the PU.

    cap_max = share of the total held by the richest `budget_pct` of cells (the most any feasible
    selection could capture); cap_min = the same for the poorest. Their difference is the entire
    range the objective term can span, so it bounds how far this feature's weight can move the
    solution -- irrespective of what the other features want."""
    budget_pct = config.BUDGET_PCT if budget_pct is None else budget_pct
    v = np.clip(values[np.isfinite(values)], 0.0, None)
    tot = v.sum()
    if v.size == 0 or tot <= 0:
        return (np.nan, np.nan, np.nan)
    k = int(round(budget_pct * v.size))
    sv = np.sort(v)
    cap_min = float(sv[:k].sum() / tot)
    cap_max = float(sv[-k:].sum() / tot)
    return (cap_min, cap_max, cap_max - cap_min)


def leverage_table(handoff_dir=None, budget_pct=None, include_efg=True, pu=None):
    """Per-feature gini / cap_min / cap_max / leverage / weight / influence share.

    EFGs are aggregated into ONE row, because 03 weights them as a group (each at 1/n_efg) and a
    40-row table would bury the continuous features. Note most EFGs score leverage ~1.0: they are
    rare enough to fit inside the budget entirely, so they can be captured fully or not at all.
    That makes their swing large but CHEAP -- bought with negligible area -- which is why the EFG
    group ranks below both carbon pools in Morris despite topping this table. Leverage bounds the
    achievable swing; it says nothing about the area price of achieving it. Use
    `target_cost_curve` for the price."""
    handoff_dir = Path(handoff_dir or config.HANDOFF_DIR)
    pu = pu_mask(handoff_dir) if pu is None else pu

    rows = []
    for name in continuous_features():
        v = _read(handoff_dir / f"{name}.tif")[pu]
        lo, hi, lev = leverage_of(v, budget_pct)
        rows.append(dict(feature=name, kind="continuous", weight=1.0,
                         gini=_gini(np.clip(v[np.isfinite(v)], 0, None)),
                         cap_min=lo, cap_max=hi, leverage=lev))

    if include_efg:
        paths = efg_paths(handoff_dir)
        levs = []
        for p in paths:
            _, _, lev = leverage_of(_read(p)[pu], budget_pct)
            if np.isfinite(lev):
                levs.append(lev)
        if levs:
            # Group weight totals 1.0 (each EFG at 1/n), so the group's contribution to the
            # objective swing is the MEAN of the member leverages, not their sum.
            rows.append(dict(feature=f"iucn_efg ({len(levs)} features)", kind="efg", weight=1.0,
                             gini=np.nan, cap_min=np.nan, cap_max=np.nan,
                             leverage=float(np.mean(levs))))

    tbl = pd.DataFrame(rows)
    swing = tbl.weight * tbl.leverage
    tbl["influence"] = swing / swing.sum()
    return tbl.sort_values("influence", ascending=False).reset_index(drop=True)


def achievable_band(cap_min, cap_max, held):
    """Where a realized capture sits inside what was ACHIEVABLE, on 0-1.

    The radar plots captured fraction against a 30% area-share ring, which reads as "neutral" for
    a low-leverage feature no matter what the solver did. Intactness captured 30.2% against a
    possible 27.2-31.4%: that is 71% of everything it could express, not a neutral result. This is
    the number that makes such an axis legible."""
    if not np.isfinite(cap_max - cap_min) or cap_max <= cap_min:
        return np.nan
    return float((held - cap_min) / (cap_max - cap_min))


# ---- deriving a target from a density rule ------------------------------
def target_cost_curve(feature, multiples=(10, 5, 3, 2, 1), handoff_dir=None, pu=None):
    """Stopping rule -> relative target, for a feature in NATIVE density units.

    For each M: take cells while the MARGINAL density is >= M x the regional mean, and report the
    relative target that secures (`target`), the minimum area it needs (`area_pct`, as a share of
    the region and of the budget), and the cutoff density. This turns "what target for carbon?"
    into "how exceptional must a cell be before we pay area for it?", which is a defensible
    conservation statement rather than a chosen number.

    `area_pct` is a LOWER BOUND: it assumes the area is bought for this feature alone. In a real
    solve those cells usually serve other features too, so the budget actually consumed is less.

    Only meaningful for layers still in interpretable native units (the carbon pools, t/ha). A
    transformed layer (intactness, 1/v refugia) has no "regional mean density" worth quoting."""
    handoff_dir = Path(handoff_dir or config.HANDOFF_DIR)
    pu = pu_mask(handoff_dir) if pu is None else pu
    v = _read(handoff_dir / f"{feature}.tif")[pu]
    v = np.clip(v[np.isfinite(v)], 0.0, None)
    n, mean = v.size, v.mean()
    sv = np.sort(v)[::-1]
    cum = np.cumsum(sv) / sv.sum()

    rows = []
    for M in multiples:
        cutoff = M * mean
        # side="right" makes this genuinely "cells with density >= cutoff" (ties included);
        # side="left" would exclude exact ties -- no float cell ties in practice, but the code
        # should match its own definition at the boundary.
        k = int(np.searchsorted(-sv, -cutoff, side="right"))
        if k == 0:
            continue                                # no cell is that exceptional
        rows.append(dict(rule=f">= {M}x mean", cutoff=cutoff, target=float(cum[k - 1]),
                         area_pct=k / n, pct_of_budget=(k / n) / config.BUDGET_PCT))
    return pd.DataFrame(rows)


# ==========================================================================
# Feature characterization protocol (frequency-ensemble spec s2.5; Gate 0a)
# ==========================================================================
# Replaces reactive per-feature fixes with ONE pre-registered audit applied to every input, so
# carbon's target treatment is a rule OUTCOME, not an exception. Constants live in config.AUDIT
# (frozen per R4 before the audit ran). Everything here is read-only diagnostics: no solve, no
# raster written; the archive it produces is the budget-independent record spec D2 requires.

def lorenz(values, n_points=None):
    """(area_frac, captured_frac) with cells in DESCENDING density order.

    The concentration curve the whole protocol reads: captured fraction of the feature's total as
    a function of the area fraction taken, always taking the densest remaining cell. Leverage's
    cap_max is one point of this curve (at area = BUDGET_PCT); target_cost_curve's rows are
    crossings of its derivative. Down-sampled to `n_points` evenly spaced area fractions for the
    archive -- interpolation error at 10k points is negligible against 1.27M cells."""
    n_points = int(n_points or config.AUDIT["curve_points"])
    v = np.clip(values[np.isfinite(values)], 0.0, None)
    sv = np.sort(v)[::-1]
    cum = np.cumsum(sv) / max(sv.sum(), 1e-300)
    area = np.linspace(0.0, 1.0, n_points)
    idx = np.clip((area * v.size).astype(int) - 1, 0, v.size - 1)
    cap = np.where(area > 0, cum[idx], 0.0)
    return area, cap


def marginal_trajectory(values, n_points=None):
    """(area_frac, marginal density / regional mean) with cells in descending density order.

    The protocol's key curve (figure F8): how exceptional is the NEXT cell you take, as a
    multiple of the regional mean, after already taking `area_frac` of the region. A stopping
    rule 'keep taking while marginal density >= theta x mean' reads its area cost and implied
    target straight off this curve; theta-crossings for ANY theta are lookups on the archive."""
    n_points = int(n_points or config.AUDIT["curve_points"])
    v = np.clip(values[np.isfinite(values)], 0.0, None)
    sv = np.sort(v)[::-1]
    mean = v.mean() if v.size else np.nan
    area = np.linspace(0.0, 1.0, n_points)
    idx = np.clip((area * v.size).astype(int) - 1, 0, v.size - 1)
    ratio = sv[idx] / max(mean, 1e-300)
    return area, ratio


def classify_values(values, audit=None):
    """Rules R2/R3/rare applied to a value vector (oriented, higher = better). Core of classify()
    and of the universal transform screening: returns (cls, lever, target, diagnostics)."""
    audit = audit or config.AUDIT
    lo, hi, lev = leverage_of(values)
    area, ratio = marginal_trajectory(values)
    _, cap = lorenz(values)
    above = ratio >= audit["theta"]
    x_area = float(area[above][-1]) if above.any() else 0.0
    x_target = float(cap[above][-1]) if above.any() else 0.0
    if hi >= audit["rare_cap"]:
        cls, lever, target = "rare-attainable", "none (saturates free)", 1.0
    elif x_area >= audit["a_min"] and x_target >= audit["t_min"]:
        cls, lever, target = "concentrated-satiating", "target", round(x_target, 3)
    elif lev < audit["leverage_min"]:
        cls, lever, target = "low-contrast-inexpressible", "none (disclosed)", 1.0
    else:
        cls, lever, target = "diffuse-linear", "weight", 1.0
    return cls, lever, target, dict(leverage=round(lev, 3), cap_min=round(lo, 3),
                                    cap_max=round(hi, 3), theta_area=round(x_area, 4),
                                    theta_target=round(x_target, 3))


def transform_response(name, handoff_dir=None, pu=None, audit=None):
    """UNIVERSAL transform screening (spec v0.8, battery item 3): leverage AND resulting
    classification under the candidate set for EVERY feature. Screening is universal; ADOPTION is
    gated by R1's value-model test, never by leverage improvement.

    Candidate set: {identity, log1p, sqrt} for all features, plus {1 - x} for bounded-cost layers
    (orient="complement") and {vmax - v, 1/v} for cost-oriented positive layers
    (orient="reciprocal"/"invert"). Rank/percentile stretches stay inadmissible.

    Admissibility per R1 (v0.8's concavity distinction is binding): a CONCAVE transform
    (log1p/sqrt) asserts diminishing value PER CELL DENSITY; a target asserts diminishing value at
    the PORTFOLIO level -- different claims, not interchangeable dominance fixes. Carbon fails the
    per-cell test (a tonne is a tonne: density-linearity physically mandated -> identity + target;
    E9's log arm is the measured demonstration). AOH richness is the open case (diminishing
    per-cell species value is ecologically arguable): reported, identity retained for paper 1.

    Returns {label: dict(leverage, cls, target, admissible, note)}."""
    handoff_dir = Path(handoff_dir or config.HANDOFF_DIR)
    pu = pu_mask(handoff_dir) if pu is None else pu
    audit = audit or config.AUDIT
    orient = config.DATASETS[name].get("orient")
    is_carbon = "carbon" in name
    is_aoh = name.startswith("aoh_")

    def entry(values, label, admissible, note):
        cls, _, target, d = classify_values(values, audit)
        return label, dict(leverage=d["leverage"], cls=cls, target=target,
                           admissible=admissible, note=note)

    out = {}
    if orient in ("complement", "reciprocal", "invert"):
        raw = _read(config.ALIGNED_DIR / f"{name}.tif")[pu]
        base = raw[np.isfinite(raw)]
        k, v = entry(np.clip(base, 0, None), "identity (avoid direction)", False,
                     "cost-oriented raw; not a candidate feature, reference only")
        out[k] = v
        if orient == "complement":
            k, v = entry(np.clip(1.0 - base, 0.0, 1.0), "1 - x", True,
                         "ADOPTED: intactness -- the honest bounded complement")
            out[k] = v
        else:
            with np.errstate(divide="ignore", invalid="ignore"):
                k, v = entry(np.nanmax(base) - base, "vmax - v", False,
                             "SUPERSEDED: additive flip; offset survives sum-normalization")
                out[k] = v
                k, v = entry(np.where(base > 0, 1.0 / base, np.nan), "1/v", True,
                             "ADOPTED: refugial residence time (yr/km)")
                out[k] = v
        oriented = np.clip(1.0 - base, 0, 1) if orient == "complement" else \
                   np.where(base > 0, 1.0 / base, np.nan)
    else:
        oriented = _read(handoff_dir / f"{name}.tif")[pu]
        note = ("ADOPTED: per-cell density-linearity physically mandated (a tonne is a tonne); "
                "dominance handled by TARGET, not transform" if is_carbon else
                "ADOPTED (open case: diminishing per-cell species value is ecologically arguable; "
                "alternative value model noted in paper, identity retained)" if is_aoh else
                "ADOPTED: raw benefit density")
        k, v = entry(np.clip(oriented[np.isfinite(oriented)], 0, None), "identity", True, note)
        out[k] = v
    # concave candidates screened on the ORIENTED (higher = better) values for every feature
    ov = np.clip(oriented[np.isfinite(oriented)], 0, None)
    for label, f in (("log1p", np.log1p), ("sqrt", np.sqrt)):
        note = ("screened only: concave = diminishing value per cell density -- no value-model "
                "claim adopted" + ("; for carbon this claim is physically false (E9 log arm "
                "demonstrates)" if is_carbon else
                "; ecologically arguable for richness -- the open R1 case" if is_aoh else ""))
        k, v = entry(f(ov), label, False, note)
        out[k] = v
    return out


def classify(name, handoff_dir=None, pu=None, audit=None):
    """Apply rules R1-R4 to one continuous feature. Returns a dict row for the T2 table.

    Rule order (each row falls through to the next):
      R1  transform      : the configured orientation IS the adopted interpretable transform;
                           reported via transform_response, never chosen here.
      rare-attainable    : cap_max >= rare_cap -- capturable in full within the budget, so it
                           saturates for free; no scenario lever (expected: most EFGs, no
                           continuous feature).
      R2  conc-satiating : marginal density >= theta x mean sustained over >= a_min of the region
                           AND implied target >= t_min. Target (the theta-crossing's captured
                           fraction) becomes the value dial. The t_min leg is the TAIL-MASS
                           criterion: a rule that saturates instantly leaves the feature governed
                           by weight anyway -> call it what it is (this reverts biomass, 0.066).
      R3  inexpressible  : leverage < leverage_min after the adopted transform -- no admissible
                           lever; excluded from scenario tilts and disclosed (expected: gHM).
      else diffuse-linear: 100% target; weight is the value dial."""
    handoff_dir = Path(handoff_dir or config.HANDOFF_DIR)
    pu = pu_mask(handoff_dir) if pu is None else pu
    audit = audit or config.AUDIT
    v = _read(handoff_dir / f"{name}.tif")[pu]
    cls, lever, target, d = classify_values(v, audit)
    return dict(feature=name, orient=config.DATASETS[name].get("orient") or "raw",
                leverage=d["leverage"], cap_min=d["cap_min"], cap_max=d["cap_max"],
                theta_area=d["theta_area"], theta_target=d["theta_target"],
                cls=cls, lever=lever, target=target)


def characterization_table(handoff_dir=None, audit=None):
    """T2: one classified row per continuous feature + the EFG block summary. Prints + returns.

    EFGs are audited per raster for rare-attainability but summarised as ONE block row, because
    the block is weight-levered as a group (each EFG at 1/n) and is locked adequacy foundation in
    the design; the unsaturated minority is the disclosure the spec requires."""
    handoff_dir = Path(handoff_dir or config.HANDOFF_DIR)
    pu = pu_mask(handoff_dir)
    audit = audit or config.AUDIT

    rows = [classify(n, handoff_dir, pu, audit) for n in continuous_features()]
    caps = {p.stem: leverage_of(_read(p)[pu])[1] for p in efg_paths(handoff_dir)}
    # A zero-total EFG would give cap_max = NaN, which fails BOTH >= and < comparisons and would
    # silently vanish from both counts below. Not live today (all 40 have positive totals), but a
    # future re-warp could produce one -- fail loudly instead of miscounting.
    bad = sorted(k for k, c in caps.items() if not np.isfinite(c))
    assert not bad, f"EFG raster(s) with no positive total inside the PU (cap_max=NaN): {bad}"
    n_rare = sum(1 for c in caps.values() if c >= audit["rare_cap"])
    unsat = sorted(k for k, c in caps.items() if c < audit["rare_cap"])
    tbl = pd.DataFrame(rows)

    print(f"{'feature':<34}{'orient':>11}{'leverage':>9}{'cap_max':>9}"
          f"{'theta_area':>11}{'theta_tgt':>10}   class -> lever (target)")
    for _, r in tbl.iterrows():
        print(f"{r.feature:<34}{r.orient:>11}{r.leverage:9.3f}{r.cap_max:9.3f}"
              f"{r.theta_area:11.4f}{r.theta_target:10.3f}   {r.cls} -> {r.lever} ({r.target})")
    print(f"\niucn_efg block ({len(caps)} rasters): {n_rare} rare-attainable "
          f"(cap_max >= {audit['rare_cap']}), {len(unsat)} unsaturated -- DISCLOSED, "
          f"block stays locked adequacy foundation:")
    for k in unsat:
        print(f"    {k}  cap_max={caps[k]:.3f}")
    return tbl, caps


def audit_archive(out_dir, tbl=None, handoff_dir=None):
    """Write the budget-independent audit objects (spec D2) + the frozen T2 + the constants.

    The npz holds each feature's full Lorenz and marginal-density curves, so re-deriving a target
    at ANY theta or ANY budget later is interpolation on this file -- no raster access, no
    recompute. Layer hashes pin exactly which rasters the classification was frozen against."""
    import hashlib, json as _json
    from datetime import datetime, timezone
    handoff_dir = Path(handoff_dir or config.HANDOFF_DIR)
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    pu = pu_mask(handoff_dir)

    arrs, hashes = {}, {}
    for n in continuous_features():
        p = handoff_dir / f"{n}.tif"
        v = _read(p)[pu]
        a, c = lorenz(v); _, r = marginal_trajectory(v)
        arrs[f"{n}__area"], arrs[f"{n}__captured"], arrs[f"{n}__dens_ratio"] = a, c, r
        hashes[n] = hashlib.sha256(p.read_bytes()).hexdigest()

    np.savez_compressed(out_dir / "feature_audit.npz", **arrs)
    if tbl is not None:
        tbl.to_csv(out_dir / "feature_characterization.csv", index=False)
    (out_dir / "audit_constants.json").write_text(_json.dumps(dict(
        constants=config.AUDIT, budget_pct=config.BUDGET_PCT,
        n_pu=int(pu.sum()), created_utc=datetime.now(timezone.utc).isoformat(),
        layer_sha256=hashes), indent=1))
    print(f"archived -> {out_dir}/feature_audit.npz + feature_characterization.csv + "
          f"audit_constants.json  ({len(hashes)} layers hashed)")
    return out_dir


def trajectory_figure(fig_path=None, handoff_dir=None, audit=None):
    """F8: marginal-density trajectories for all continuous features, theta crossings marked.

    THE protocol figure -- it shows, on one pair of axes, why mineral soil earns a stopping rule
    (a long high shelf: >= 5x mean sustained over 4% of the region) and biomass does not (a spike
    that collapses almost immediately), with no equations in sight."""
    import matplotlib.pyplot as plt
    handoff_dir = Path(handoff_dir or config.HANDOFF_DIR)
    pu = pu_mask(handoff_dir)
    audit = audit or config.AUDIT

    def _pct(x):        # 0.20% / 0.47% below 1, 4.1% above -- enough digits to distinguish
        return f"{x:.2f}%" if x < 1 else f"{x:.1f}%"

    fig, ax = plt.subplots(figsize=(9, 6))
    ymax = 1.0
    crossings = []
    for n in continuous_features():
        v = _read(handoff_dir / f"{n}.tif")[pu]
        area, ratio = marginal_trajectory(v)
        m = area > 0
        (line,) = ax.plot(100 * area[m], ratio[m], lw=1.4, label=n)
        ymax = max(ymax, float(np.nanmax(ratio[m])))
        above = ratio >= audit["theta"]
        if above.any():
            xa = 100 * float(area[above][-1])
            ax.plot([xa], [audit["theta"]], "o", ms=5, color=line.get_color())
            crossings.append((xa, line.get_color()))
    # Label each crossing with the area sitting ABOVE theta, in the curve's own colour --
    # the annotation that makes the log axis readable (log-x compresses exactly this quantity:
    # 4.1% sits visually close to 0.47% while being 9x the area, so the number rides the dot).
    # Collision detection works in LOG space: crossings within ~0.25 decades share a
    # neighbourhood, and successive labels in a cluster step downward.
    level, prev = 0, None
    for xa, colr in sorted(crossings):
        level = level + 1 if (prev is not None and np.log10(xa / prev) < 0.25) else 0
        dy = 9 if level == 0 else -13 - 11 * (level - 1)
        ax.annotate(_pct(xa), (xa, audit["theta"]), xytext=(0, dy),
                    textcoords="offset points", ha="center", fontsize=7.5,
                    color=colr, fontweight="bold")
        prev = xa
    ax.axhline(audit["theta"], color="0.25", lw=1.0, ls="--")
    ax.axvline(100 * audit["a_min"], color="0.6", lw=0.8, ls=":")
    ax.set_xscale("log"); ax.set_yscale("log")
    # Clamp the floor: every trajectory plunges to ~0 at 100% area (the layer's own zero tail),
    # which would stretch a log axis down to 1e-7 and flatten the entire story into the top
    # stripe. Everything the rules read happens at ratio >= ~1.
    ax.set_ylim(0.05, ymax * 1.6)
    ax.text(ax.get_xlim()[0] * 1.15, audit["theta"] * 1.12,
            f"theta = {audit['theta']:.0f}x regional mean", fontsize=8, color="0.25")
    ax.text(100 * audit["a_min"] * 1.08, 0.062, f"a_min = {100*audit['a_min']:.1f}%",
            fontsize=8, color="0.4", rotation=90, va="bottom")
    ax.set_xlabel("area taken, densest first (% of region, log)")
    ax.set_ylabel("marginal density / regional mean (log)")
    ax.set_title("Marginal-density trajectories — who earns a stopping rule (F8)")
    ax.legend(fontsize=7.5, loc="lower left", framealpha=0.92)
    ax.grid(True, which="both", lw=0.3, alpha=0.4)
    fig.tight_layout()
    if fig_path:
        fig.savefig(fig_path, dpi=200)
        print(f"wrote {fig_path}")
    return fig


# ---- feature cards (spec v0.8, s2.5 audit output) ------------------------
def feature_card(name, out_dir, handoff_dir=None, pu=None, audit=None):
    """One standardized 6-panel page per input, rendered at Gate 0a for review against the frozen
    rules BEFORE any Gate-0 solve. Panels (spec v0.8): A distribution, B Lorenz concentration,
    C stopping rule (the per-feature F8), D transform response, E spatial thumbnail (top decile;
    catches seams/artifacts the univariate panels miss), F verdict box (frozen-rule outputs with
    each test's actual values, so card review is a read, not a recomputation)."""
    import matplotlib.pyplot as plt
    from scipy.stats import skew as _skew
    handoff_dir = Path(handoff_dir or config.HANDOFF_DIR)
    pu = pu_mask(handoff_dir) if pu is None else pu
    audit = audit or config.AUDIT
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)

    grid = _read(handoff_dir / f"{name}.tif")
    v = np.clip(grid[pu][np.isfinite(grid[pu])], 0.0, None)
    row = classify(name, handoff_dir, pu, audit)
    tr = transform_response(name, handoff_dir, pu, audit)

    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    fig.suptitle(f"Feature card — {name}   [{row['cls']}]", fontsize=13, fontweight="bold")
    A, B, C, D, E, F = axes.ravel()

    # A -- distribution. Two regimes, and the BINS must match the axis:
    #   skewed (skew > 2): log-x with GEOMETRIC bins -- linear bins on a log axis render as a few
    #     giant slabs plus a spike, which is what made half the first-draft cards unreadable.
    #     Zeros cannot sit on a log axis, so the zero-inflated share is reported in the stats box
    #     (and for carbon it is substantial). The axis floor is p0.1 of the positive values, with
    #     anything smaller clipped into the first bin -- otherwise a single near-zero cell drags
    #     the axis across empty decades.
    #   otherwise: plain linear bins, LINEAR counts (no log-y: it turned smooth unimodal layers
    #     like AOH richness into jagged plateaus).
    sk = float(_skew(v))
    zero_frac = float((v == 0).mean())
    pos = v[v > 0]
    logx = sk > 2 and pos.size > 0
    if logx:
        lo = float(np.percentile(pos, 0.1))
        hi = float(pos.max())
        A.hist(np.clip(pos, lo, None), bins=np.geomspace(lo, hi, 60), color="#4878a8")
        A.set_xscale("log")
    else:
        # Integer-valued layers (AOH richness counts): align bins to integers, else a ~1.7-wide
        # bin alternates between holding one and two integers and prints a sawtooth that is pure
        # binning artifact. Step chosen so ~60 bars cover the range.
        if v.size and np.allclose(v, np.round(v)):
            step = max(1, int(np.ceil((v.max() - v.min()) / 60)))
            bins = np.arange(np.floor(v.min()) - 0.5, np.ceil(v.max()) + step + 0.5, step)
            A.hist(v, bins=bins, color="#4878a8")
        else:
            A.hist(v, bins=60, color="#4878a8")
    q = {p: float(np.percentile(v, p)) for p in (50, 90, 99)}
    A.set_title("A  distribution" + ("  (log-x, geometric bins)" if logx else ""),
                loc="left", fontsize=10)
    A.set_ylabel("cells")
    A.text(0.97, 0.95, f"mean {v.mean():.3g}\np50 {q[50]:.3g}  p90 {q[90]:.3g}  p99 {q[99]:.3g}\n"
                       f"skew {sk:.2f}   zeros {100*zero_frac:.1f}%"
                       + ("\n(zeros excluded from log axis)" if logx and zero_frac > 0 else ""),
           transform=A.transAxes, ha="right", va="top", fontsize=8,
           bbox=dict(fc="white", alpha=0.8, ec="0.7"))

    # B -- Lorenz with the 30%-budget vertical: leverage reads as a visual gap
    area, cap = lorenz(v)
    B.plot(100 * area, cap, lw=1.6, color="#4878a8")
    B.plot(100 * area, np.interp(area, [0, 1], [0, 1]), lw=0.8, ls=":", color="0.6")
    Bpct = config.BUDGET_PCT
    B.axvline(100 * Bpct, color="0.3", lw=1.0, ls="--")
    B.plot([100 * Bpct], [row["cap_max"]], "o", ms=5, color="#c04040")
    B.plot([100 * Bpct], [1 - float(np.interp(1 - Bpct, area, cap))], "o", ms=5, color="#40803f")
    B.set_title("B  concentration (Lorenz, cells descending)", loc="left", fontsize=10)
    B.set_xlabel("% of area"); B.set_ylabel("captured fraction")
    B.text(0.97, 0.08, f"cap_max {row['cap_max']:.3f}\ncap_min {row['cap_min']:.3f}\n"
                       f"LEVERAGE {row['leverage']:.3f}",
           transform=B.transAxes, ha="right", va="bottom", fontsize=9,
           bbox=dict(fc="white", alpha=0.85, ec="0.7"))

    # C -- stopping rule: per-feature F8 with 3x/5x/10x crossings + implied targets
    area, ratio = marginal_trajectory(v)
    m = area > 0
    C.plot(100 * area[m], ratio[m], lw=1.5, color="#4878a8")
    C.set_xscale("log"); C.set_yscale("log")
    ymax = float(np.nanmax(ratio[m])) if m.any() else 1.0
    C.set_ylim(0.05, max(ymax * 1.6, 1.5))
    _, capc = lorenz(v)
    lines = []
    for th, colr in ((3.0, "#40803f"), (audit["theta"], "#c04040"), (10.0, "#806040")):
        C.axhline(th, lw=0.7, ls="--", color=colr, alpha=0.7)
        ab = ratio >= th
        if ab.any():
            xa, tg = float(area[ab][-1]), float(capc[ab][-1])
            C.plot([100 * xa], [th], "o", ms=5, color=colr)
            pc = f"{100*xa:.2f}%" if 100 * xa < 1 else f"{100*xa:.1f}%"
            C.annotate(pc, (100 * xa, th), xytext=(5, 4), textcoords="offset points",
                       fontsize=7.5, color=colr, fontweight="bold")
            lines.append(f"{th:.0f}x: target {tg:.3f} @ {100*xa:.2f}% area")
        else:
            lines.append(f"{th:.0f}x: no crossing")
    C.axvline(100 * audit["a_min"], color="0.6", lw=0.8, ls=":")
    tmin_ok = row["theta_target"] >= audit["t_min"]
    lines.append(f"t_min {audit['t_min']}: {'PASS' if tmin_ok else 'fail'} "
                 f"(implied {row['theta_target']:.3f})")
    C.set_title("C  stopping rule (marginal density / mean)", loc="left", fontsize=10)
    C.set_xlabel("% of area taken, densest first (log)")
    C.text(0.03, 0.06, "\n".join(lines), transform=C.transAxes, fontsize=8, va="bottom",
           bbox=dict(fc="white", alpha=0.85, ec="0.7"))

    # D -- transform response table (universal screening; adoption per R1's value-model test)
    D.axis("off")
    D.set_title("D  transform response (screened universally; R1 gates adoption)",
                loc="left", fontsize=10)
    cells = [[lab, f"{d['leverage']:.3f}", d["cls"].replace("low-contrast-", ""),
              "ADMISSIBLE" if d["admissible"] else "screened only"] for lab, d in tr.items()]
    t = D.table(cellText=cells, colLabels=["transform", "leverage", "class", "R1"],
                loc="upper center", cellLoc="left", colWidths=[0.28, 0.15, 0.33, 0.24])
    t.auto_set_font_size(False); t.set_fontsize(7.5); t.scale(1, 1.35)

    # E -- spatial thumbnail: top decile highlighted (seam/artifact check)
    E.set_title("E  spatial thumbnail (top decile)", loc="left", fontsize=10)
    thr = np.nanpercentile(grid[pu], 90)
    img = np.full(grid.shape, np.nan, "float32")
    img[pu] = 0.0
    img[pu & (grid >= thr)] = 1.0
    E.imshow(img, cmap="cividis", interpolation="nearest", aspect="equal")
    E.set_xticks([]); E.set_yticks([])

    # F -- verdict box: each R-test's actual values so review is a read, not a recomputation
    F.axis("off")
    F.set_title("F  verdict (frozen rules R1-R4)", loc="left", fontsize=10)
    F.text(0.02, 0.95, "\n".join([
        f"transform adopted : {row['orient']}",
        f"class             : {row['cls']}",
        f"value lever       : {row['lever']}",
        f"target            : {row['target']}",
        "",
        f"R2(i)  theta-area  {row['theta_area']:.4f}  vs a_min {audit['a_min']}  "
        f"-> {'pass' if row['theta_area'] >= audit['a_min'] else 'fail'}",
        f"R2(ii) implied tgt {row['theta_target']:.3f}   vs t_min {audit['t_min']}   "
        f"-> {'pass' if row['theta_target'] >= audit['t_min'] else 'fail'}",
        f"R3     leverage    {row['leverage']:.3f}   vs lambda {audit['leverage_min']}  "
        f"-> {'inexpressible' if row['leverage'] < audit['leverage_min'] else 'expressible'}",
        f"rare   cap_max     {row['cap_max']:.3f}   vs {audit['rare_cap']}   "
        f"-> {'rare-attainable' if row['cap_max'] >= audit['rare_cap'] else 'not rare'}",
        "",
        f"predicted saturation at B={config.BUDGET_PCT:.0%}: "
        f"{'YES (target reachable)' if row['cap_max'] >= row['target'] else 'no'}",
    ]), transform=F.transAxes, fontsize=9, va="top", family="monospace")

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = out_dir / f"{name}.pdf"
    fig.savefig(out)
    plt.close(fig)
    return out


def feature_cards(cards_dir, handoff_dir=None, audit=None):
    """All cards + the summary sheet (all-features Lorenz overlay, T2, pre/post-transform leverage
    bars). 8 continuous cards + 1 EFG-block card; the spec says '12 cards' but counts the inputs
    as '8 continuous + EFG block', which is 9 pages -- the miscount is disclosed, not silently
    resolved. EFG block card: per-raster extent + cap_max, occurrence-richness thumbnail,
    rare-attainable verdict."""
    import matplotlib.pyplot as plt
    handoff_dir = Path(handoff_dir or config.HANDOFF_DIR)
    pu = pu_mask(handoff_dir)
    audit = audit or config.AUDIT
    cards_dir = Path(cards_dir); cards_dir.mkdir(parents=True, exist_ok=True)

    paths = [feature_card(n, cards_dir, handoff_dir, pu, audit) for n in continuous_features()]

    # -- EFG block card --
    epaths = efg_paths(handoff_dir)
    ext, caps, rich = {}, {}, np.zeros(pu.shape, "int16")
    for p in epaths:
        a = _read(p)
        occ = pu & (a > 0)
        ext[p.stem] = int(occ.sum())
        caps[p.stem] = leverage_of(a[pu])[1]
        rich += occ
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle(f"Feature card — iucn_efg block ({len(epaths)} rasters)   "
                 f"[locked adequacy foundation]", fontsize=13, fontweight="bold")
    (A, Bx), (E, F) = axes
    A.hist(list(ext.values()), bins=30, color="#4878a8")
    A.set_xscale("log"); A.set_title("A  per-EFG extent (cells with occurrence, log-x)",
                                     loc="left", fontsize=10)
    order = sorted(caps, key=caps.get)
    Bx.barh(range(len(order)), [caps[k] for k in order], color=["#c04040" if caps[k] < audit["rare_cap"]
            else "#4878a8" for k in order])
    Bx.axvline(audit["rare_cap"], color="0.3", lw=1.0, ls="--")
    Bx.set_yticks(range(len(order))); Bx.set_yticklabels(order, fontsize=4.5)
    Bx.set_title(f"B  per-EFG cap_max (red = unsaturated, {sum(1 for k in caps if caps[k] < audit['rare_cap'])} of {len(caps)})",
                 loc="left", fontsize=10)
    img = np.full(pu.shape, np.nan, "float32"); img[pu] = rich[pu]
    im = E.imshow(img, cmap="viridis", interpolation="nearest")
    E.set_title("E  EFG occurrence richness (count per cell)", loc="left", fontsize=10)
    E.set_xticks([]); E.set_yticks([]); fig.colorbar(im, ax=E, shrink=0.6)
    F.axis("off"); F.set_title("F  verdict", loc="left", fontsize=10)
    n_rare = sum(1 for k in caps if caps[k] >= audit["rare_cap"])
    unsat = [k for k in order if caps[k] < audit["rare_cap"]]
    F.text(0.02, 0.95, "\n".join([
        f"class            : rare-attainable x {n_rare} / diffuse x {len(caps)-n_rare}",
        f"value lever      : none (locked adequacy foundation; group weight 1/{len(caps)} each)",
        "scenario axis    : representativeness-forward EXCLUDED (spec D7)",
        f"unsaturated ({len(unsat)}):"] + [f"  {k}  cap_max={caps[k]:.3f}" for k in unsat]),
        transform=F.transAxes, fontsize=9, va="top", family="monospace")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    p = cards_dir / "iucn_efg_block.pdf"; fig.savefig(p); plt.close(fig)
    paths.append(p)

    # -- summary sheet --
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))
    S1, S2, S3 = axes
    tbl = pd.DataFrame([classify(n, handoff_dir, pu, audit) for n in continuous_features()])
    for n in continuous_features():
        v = _read(handoff_dir / f"{n}.tif")[pu]
        a, cp = lorenz(v)
        S1.plot(100 * a, cp, lw=1.2, label=n.replace("irrecoverable_carbon_", "carbon_"))
    S1.axvline(100 * config.BUDGET_PCT, color="0.3", lw=1.0, ls="--")
    S1.set_title("Lorenz overlay (all features)", loc="left", fontsize=10)
    S1.legend(fontsize=6.5, loc="lower right"); S1.set_xlabel("% of area")
    S2.axis("off"); S2.set_title("T2 — characterization", loc="left", fontsize=10)
    cells = [[r.feature.replace("irrecoverable_carbon_", "carbon_"), f"{r.leverage:.3f}",
              r.cls.replace("low-contrast-", ""), str(r.target)] for _, r in tbl.iterrows()]
    t = S2.table(cellText=cells, colLabels=["feature", "leverage", "class", "target"],
                 loc="center", cellLoc="left", colWidths=[0.42, 0.16, 0.28, 0.14])
    t.auto_set_font_size(False); t.set_fontsize(7); t.scale(1, 1.5)
    pre = {"human_modification": 0.742, "climate_type_macrorefugia": 0.353}
    names = list(tbl.feature)
    S3.barh(range(len(names)), tbl.leverage, color="#4878a8", label="adopted transform")
    for i, n in enumerate(names):
        if n in pre:
            S3.plot([pre[n]], [i], "D", color="#c04040", ms=5)
    S3.set_yticks(range(len(names)))
    S3.set_yticklabels([n.replace("irrecoverable_carbon_", "carbon_") for n in names], fontsize=7)
    S3.axvline(audit["leverage_min"], color="0.4", lw=0.8, ls=":")
    S3.set_title("leverage (diamond = raw/avoid direction)", loc="left", fontsize=10)
    fig.tight_layout()
    p = cards_dir / "_summary_sheet.pdf"; fig.savefig(p); plt.close(fig)
    paths.append(p)
    print(f"wrote {len(paths)} pages -> {cards_dir}  "
          f"({len(paths)-2} feature cards + EFG block card + summary sheet; the spec's '12 cards' "
          f"counts inputs as '8 continuous + EFG block' = 9 pages -- miscount disclosed)")
    return paths


# ---- reporting ----------------------------------------------------------
def report(tbl, leverage_min=None):
    """Print the leverage table and flag features that cannot move the solution.

    Returns the flagged subset so a notebook cell can assert on it if desired."""
    leverage_min = config.LEVERAGE_MIN if leverage_min is None else leverage_min
    print(f"{'feature':<36}{'gini':>7}{'cap_min':>9}{'cap_max':>9}{'leverage':>10}{'influence':>11}")
    for _, r in tbl.iterrows():
        g = f"{r.gini:7.3f}" if np.isfinite(r.gini) else f"{'--':>7}"
        lo = f"{r.cap_min:9.3f}" if np.isfinite(r.cap_min) else f"{'--':>9}"
        hi = f"{r.cap_max:9.3f}" if np.isfinite(r.cap_max) else f"{'--':>9}"
        print(f"{r.feature:<36}{g}{lo}{hi}{r.leverage:10.3f}{100*r.influence:10.1f}%")

    flagged = tbl[tbl.leverage < leverage_min]
    print(f"\ntotal achievable objective swing = {(tbl.weight * tbl.leverage).sum():.3f}")
    if len(flagged):
        print(f"\nFLAGGED (leverage < {leverage_min}) -- these features cannot move a "
              f"{100*config.BUDGET_PCT:.0f}%-of-area selection, so reweighting them is inert:")
        for _, r in flagged.iterrows():
            print(f"  {r.feature:<34} leverage {r.leverage:.3f}  "
                  f"(captured fraction is confined to {r.cap_min:.3f}-{r.cap_max:.3f})")
        print("  -> classify each: (a) orientation artefact -> fixable in cell 14; "
              "(b) flattened by 1 km aggregation; (c) genuinely uniform -> REPORT, do not "
              "manufacture signal.")
    else:
        print(f"\nno feature below LEVERAGE_MIN = {leverage_min}.")
    return flagged
