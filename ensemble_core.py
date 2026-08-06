"""Ensemble runner + Morris screening (Phases 2 / 2.5 / 3) -- imported by 06_uncertainty_analysis.

WHAT THIS IS FOR. The headline prioritizr run answers "where are the priorities". This answers
"which of the inputs decides that" -- by solving the SAME problem many times under perturbed
parameters and attributing the movement in the priority map to individual factors.

HOW A RUN IS PARAMETERISED. `config.py` stays the single source of truth for the BASELINE. Each
run gets a COPY of manifest.json with its `params` block patched, written next to its own
outputs. config.py is never mutated per run: that keeps every perturbation an explicit delta in
the design matrix, lets concurrent solves run without fighting over shared state, and makes any
single run re-executable in isolation from the manifest sitting beside its results.

The R side is `run_one.R`, which mirrors 03a cells 1-9 exactly and holds no logic of its own.

THREE PHASES, ONE MACHINE:
  2   `run(design, tag)`          -- solve a design matrix, resumably, N at a time
  2.5 `noise_floor_design()`      -- N identical runs; the floor every later effect is read against
  3   `morris_design()` + `analyze_morris()` -- rank all 12 factors by mu*, plus per-cell maps
"""
import json
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import rasterio
from SALib.analyze import morris as salib_morris
from SALib.sample import morris as salib_morris_sample

import config

BAR_CMAP = plt.get_cmap("tab10")


# ================= manifest plumbing =================
def _run_dir(tag, run_id):
    return config.RESULTS_DIR / tag / f"run_{run_id:04d}"


def base_manifest(tag, analysis=None):
    """Generate the BASELINE manifest once per ensemble and return (dict, path).

    Uses the same `config.write_manifest()` the notebooks use, so the ensemble baseline cannot
    drift from what 03 would solve. Written to the ensemble root, not over aligned_stack's."""
    analysis = analysis or config.ENSEMBLE["analysis"]
    root = config.RESULTS_DIR / tag
    root.mkdir(parents=True, exist_ok=True)
    p = config.write_manifest(analysis=analysis, manifest_path=root / "base_manifest.json")
    m = json.loads(Path(p).read_text())
    return m, Path(p)


def efg_names(manifest):
    return [L["name"] for L in manifest["layers"] if L["role"] == "feature_efg"]


def cont_names(manifest):
    return [L["name"] for L in manifest["layers"] if L["role"] == "feature_continuous"]


def patch(manifest, overrides, tag, run_id, settings=None):
    """Baseline manifest + this run's deltas -> a complete, standalone manifest.

    Only the `params` block is touched; grid and layers are shared by every run. `results_subdir`
    is set per run, which is what gives each solve its own output folder (pr_write_outputs joins
    results_dir/results_subdir and creates it recursively).

    `settings` overrides the ENSEMBLE defaults for THIS batch (agg_factor / threads / time_limit)
    -- gate runs are single solves at a different resolution and deserve all the cores and the
    full time limit, not the ensemble's concurrency slice and stuck-run guard.
    `threads` of 0/None omits the key entirely, so R falls back to detectCores()."""
    s = {**config.ENSEMBLE, **(settings or {})}
    m = json.loads(json.dumps(manifest))          # deep copy
    m["params"].update({
        "prototype_agg_factor": s["agg_factor"],
        "solver_time_limit": s["time_limit"],
        "results_subdir": f"{tag}/run_{run_id:04d}",
    })
    if s.get("threads"):
        m["params"]["threads"] = s["threads"]
    else:
        m["params"].pop("threads", None)          # -> pr_build_problem uses every core
    m["params"].update(overrides)
    return m


# ================= design -> manifest overrides =================
def baseline_overrides(manifest):
    """An UNPERTURBED run at ensemble settings: every multiplier 1.0, config defaults elsewhere.

    Doubles as the G2 scale-transfer run (2 km vs the 1 km headline) and as the reference the
    `jaccard_vs_base` metric is measured against."""
    return {"feature_weight_multipliers": {}}


def overrides_from_row(row, manifest):
    """One design-matrix row -> a manifest `params` patch.

    Factor kinds (config.MORRIS["factors"]):
      weight_log2  per-feature weight multiplier, 2**x   (x=0 -> unchanged)
      efg_log2     the same multiplier applied to ALL EFG layers, so the EFG GROUP weight moves
                   as one factor rather than 40
      linear       used as-is (budget_pct, target_pct)
      log10        10**x (neighbor_penalty)
    """
    mult, params = {}, {}
    for name, kind, _lo, _hi in config.MORRIS["factors"]:
        v = float(row[name])
        if kind == "weight_log2":
            feat = name[2:]                                   # strip the "w_" prefix
            assert feat in cont_names(manifest), f"unknown feature in MORRIS factors: {feat}"
            mult[feat] = float(2.0 ** v)
        elif kind == "efg_log2":
            for e in efg_names(manifest):
                mult[e] = float(2.0 ** v)
        elif kind == "linear":
            params[name] = v
        elif kind == "log10":
            params[name] = float(10.0 ** v)
        else:
            raise ValueError(f"unknown factor kind {kind!r}")
    params["feature_weight_multipliers"] = mult
    return params


def salib_problem():
    """SALib problem dict built from config.MORRIS -- the single definition of the factor space."""
    f = config.MORRIS["factors"]
    return {"num_vars": len(f), "names": [n for n, _, _, _ in f],
            "bounds": [[lo, hi] for _, _, lo, hi in f]}


def morris_design():
    """Morris trajectory sample -> tidy design DataFrame (r*(k+1) rows, one column per factor)."""
    prob = salib_problem()
    M = config.MORRIS
    X = salib_morris_sample.sample(prob, N=M["r"], num_levels=M["num_levels"],
                                   seed=M["seed"])
    df = pd.DataFrame(X, columns=prob["names"])
    df.insert(0, "run_id", np.arange(len(df)))
    df["kind"] = "morris"
    print(f"Morris design: r={M['r']} trajectories x (k+1)={prob['num_vars']+1} = {len(df)} runs "
          f"| num_levels={M['num_levels']} seed={M['seed']}")
    return df, prob, X


def noise_floor_design(n=10):
    """N IDENTICAL runs. The floor every Morris effect is read against.

    OPT_GAP=0.10 means solutions are not proven optimal, so re-solves CAN differ. Morris effects
    are differences between paired runs -- if solver noise is comparable to a real perturbation,
    the ranking is noise. Must be run at the SAME workers/threads as the real batch: thread count
    can itself change where an interior-point solve stops."""
    df = pd.DataFrame({"run_id": np.arange(n)})
    df["kind"] = "noise"
    return df


# ================= run =================
def _solve_one(manifest_dict, tag, run_id, timeout_pad=600):
    d = _run_dir(tag, run_id)
    d.mkdir(parents=True, exist_ok=True)
    mpath = d / "manifest.json"
    mpath.write_text(json.dumps(manifest_dict, indent=1))
    cfg = config.ENSEMBLE
    t0 = time.perf_counter()
    proc = subprocess.run(
        [cfg["rscript"], str(config.PROJECT_DIR / cfg["driver"]), str(mpath), str(config.PROJECT_DIR)],
        capture_output=True, text=True, timeout=cfg["time_limit"] + timeout_pad,
    )
    (d / "log.txt").write_text(proc.stdout + "\n----- STDERR -----\n" + proc.stderr)
    ok = proc.returncode == 0 and "RUN_ONE_OK" in proc.stdout
    return dict(run_id=run_id, ok=ok, seconds=time.perf_counter() - t0,
                error="" if ok else proc.stderr.strip().splitlines()[-1][:200] if proc.stderr.strip() else "no sentinel")


def run(design, tag, manifest=None, overrides_fn=None, workers=None, settings=None):
    """Solve every row of `design`. RESUMABLE: rows whose run_summary.json exists are skipped.

    `overrides_fn(row, manifest) -> params patch`; defaults to the Morris translation. Pass
    `lambda r, m: baseline_overrides(m)` for the baseline / noise-floor designs.
    `settings` overrides ENSEMBLE's agg_factor / threads / time_limit for this batch."""
    workers = workers or config.ENSEMBLE["workers"]
    if manifest is None:
        manifest, _ = base_manifest(tag)
    overrides_fn = overrides_fn or overrides_from_row

    todo, skipped = [], []
    for _, row in design.iterrows():
        rid = int(row["run_id"])
        if (_run_dir(tag, rid) / "run_summary.json").exists():
            skipped.append(rid); continue
        todo.append((rid, patch(manifest, overrides_fn(row, manifest), tag, rid, settings)))

    print(f"[{tag}] {len(design)} rows | {len(skipped)} already done (skipped) | {len(todo)} to solve")
    if not todo:
        return status(tag, design)
    # Report the EFFECTIVE settings straight off the manifest R will actually read, so this
    # banner cannot drift from what is solved (it previously printed the ENSEMBLE defaults and
    # so misreported any per-run override).
    eff = todo[0][1]["params"]
    agg = eff["prototype_agg_factor"]
    print(f"       {workers} workers x {eff.get('threads', 'ALL')} threads | "
          f"agg={agg} ({config.TARGET_RES_M * agg / 1000:.0f} km) | "
          f"time limit {eff['solver_time_limit']}s | budget {eff['budget_pct']:.0%}")

    results, t0 = [], time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_solve_one, m, tag, rid): rid for rid, m in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            try:
                r = fut.result()
            except Exception as e:                                     # timeout / crash
                r = dict(run_id=futs[fut], ok=False, seconds=np.nan, error=str(e)[:200])
            results.append(r)
            el = time.perf_counter() - t0
            print(f"  [{i:>4}/{len(todo)}] run_{r['run_id']:04d} "
                  f"{'ok ' if r['ok'] else 'FAIL'} {r['seconds']:6.0f}s "
                  f"| elapsed {el/60:5.1f}m | eta {el/i*(len(todo)-i)/60:5.1f}m"
                  + ("" if r["ok"] else f"  <- {r['error']}"))
    bad = [r for r in results if not r["ok"]]
    if bad:
        print(f"\n  {len(bad)} FAILED: {[r['run_id'] for r in bad]} -- see run_*/log.txt; "
              f"re-running run() will retry only those")
    return status(tag, design)


def status(tag, design):
    """Which rows have a finished solve on disk."""
    rows = []
    for _, r in design.iterrows():
        rid = int(r["run_id"])
        rows.append(dict(run_id=rid, done=(_run_dir(tag, rid) / "run_summary.json").exists()))
    df = pd.DataFrame(rows)
    print(f"[{tag}] complete: {int(df.done.sum())}/{len(df)}")
    return df


# ================= collect =================
def _alloc(path):
    """Band 1 of a run's portfolio.tif as float32 with NoData -> NaN (the allocation surface)."""
    with rasterio.open(path) as s:
        return s.read(1, masked=True).astype("float32").filled(np.nan)


def collect(tag, design, drop_freq=None):
    """Read every finished run into (tidy DataFrame, allocation matrix, domain mask).

    The allocation matrix is (n_runs, n_domain_cells) over cells finite in EVERY run, so per-cell
    statistics are computed on one common footprint."""
    drop_freq = config.ENSEMBLE["drop_duplicate_freq"] if drop_freq is None else drop_freq
    base = json.loads((config.RESULTS_DIR / tag / "base_manifest.json").read_text())
    conts, efgs = cont_names(base), efg_names(base)
    rows, allocs = [], []
    for _, r in design.iterrows():
        rid = int(r["run_id"]); d = _run_dir(tag, rid)
        sp = d / "run_summary.json"
        if not sp.exists():
            continue
        s = json.loads(sp.read_text())
        stats = s["per_alternative"][0] if isinstance(s["per_alternative"], list) else s["per_alternative"]
        rec = dict(run_id=rid, n_selected=stats["n_selected"], pct_region=stats["pct_region"],
                   n_added_beyond_pa=stats["n_added_beyond_pa"], solve_seconds=s["solve_seconds"],
                   budget_cells=s["budget_cells"], n_planning_units=s["n_planning_units"])
        # a timed-out HiGHS run returns an infeasible point (area > budget) -- flag, don't use
        rec["infeasible"] = rec["n_selected"] > rec["budget_cells"] * 1.001
        rep = d / "portfolio_representation.csv"
        if rep.exists():
            t = pd.read_csv(rep)
            col = "relative_held" if "relative_held" in t else next(c for c in t if c.startswith("relative"))
            held = t.set_index("feature")[col]
            for f in conts:                       # captured fraction per continuous feature
                rec[f"held_{f}"] = float(held.get(f, np.nan))
            rec["held_EFG_mean"] = float(held.reindex(efgs).mean())   # EFG names from the manifest
        allocs.append(_alloc(d / "portfolio.tif"))
        rows.append(rec)
        if drop_freq and (d / "selection_frequency.tif").exists():
            (d / "selection_frequency.tif").unlink()   # identical to portfolio.tif at n_sol == 1

    if not rows:
        raise RuntimeError(f"no finished runs under {tag}")
    A = np.stack(allocs)
    domain = np.isfinite(A).all(axis=0)
    A = A[:, domain]
    out = design.merge(pd.DataFrame(rows), on="run_id", how="inner").sort_values("run_id")
    n_bad = int(out.infeasible.sum())
    print(f"[{tag}] collected {len(out)} runs | domain {int(domain.sum()):,} cells")
    if n_bad:
        # NOT dropped: a Morris design with holes is invalid (the trajectory structure is what
        # makes an elementary effect meaningful), so the fix is to re-solve these with a longer
        # time limit, not to analyse around them. analyze_morris() refuses while any remain.
        print(f"  WARNING: {n_bad} run(s) INFEASIBLE (area > budget => hit the time limit): "
              f"{out.loc[out.infeasible, 'run_id'].tolist()[:12]}")
        print(f"  -> raise ENSEMBLE['time_limit'], delete those run dirs, and re-run run()")
    return out, A, domain


def add_baseline_metrics(df, A, base_row=0):
    """Jaccard of each run's selected set against the baseline run -- the primary Morris metric."""
    thr = config.ENSEMBLE["select_threshold"]
    S = A > thr
    b = S[base_row]
    df = df.copy()
    df["jaccard_vs_base"] = [float((s & b).sum() / max((s | b).sum(), 1)) for s in S]
    df["dissim_vs_base"] = 1.0 - df["jaccard_vs_base"]
    return df


# ================= Phase 2.5: noise floor =================
def noise_report(A, tag=""):
    """How much do IDENTICAL re-solves differ? Everything downstream is read against this."""
    thr = config.ENSEMBLE["select_threshold"]
    S = A > thr
    n = len(A)
    js = [float((S[i] & S[j]).sum() / max((S[i] | S[j]).sum(), 1))
          for i in range(n) for j in range(i + 1, n)]
    sd = A.std(axis=0)
    print(f"SOLVER NOISE FLOOR{' [' + tag + ']' if tag else ''} -- {n} identical re-solves")
    print(f"  pairwise Jaccard of the selected set : min {min(js):.6f}  mean {np.mean(js):.6f}")
    print(f"  per-cell allocation SD               : max {sd.max():.6f}  mean {sd.mean():.6f}")
    print(f"  cells that ever flip selection       : {int((S.any(0) & ~S.all(0)).sum()):,}")
    floor = 1 - min(js)
    print(f"\n  -> noise floor (max dissimilarity between identical runs) = {floor:.6f}")
    print("     Any Morris effect on `dissim_vs_base` below this is SOLVER NOISE, not signal."
          if floor > 0 else
          "     Solver is DETERMINISTIC here -- all downstream variance is attributable to inputs.")
    return floor


# ================= Phase 3: Morris analysis =================
def analyze_morris(df, X, metric="dissim_vs_base", prob=None):
    """SALib Morris on one scalar metric -> mu*, mu, sigma, ranked."""
    prob = prob or salib_problem()
    d = df.sort_values("run_id")
    y = d[metric].to_numpy(dtype=float)
    assert len(y) == len(X), f"{len(y)} results vs {len(X)} design rows -- incomplete batch"
    if "infeasible" in d:
        bad = d.loc[d.infeasible, "run_id"].tolist()
        assert not bad, (f"{len(bad)} infeasible run(s) in the design ({bad[:8]}): their solutions "
                         f"are timed-out garbage. Morris needs every trajectory row valid -- "
                         f"re-solve them, don't analyse around them.")
    res = salib_morris.analyze(prob, X, y, num_levels=config.MORRIS["num_levels"])
    out = (pd.DataFrame({"factor": res["names"], "mu_star": res["mu_star"],
                         "mu": res["mu"], "sigma": res["sigma"],
                         "mu_star_conf": res["mu_star_conf"]})
           .sort_values("mu_star", ascending=False).reset_index(drop=True))
    print(f"\nMORRIS -- effects on `{metric}` (mu* = influence, sigma = interaction/nonlinearity)")
    print(out.round(4).to_string(index=False))
    return out


def _unit(X, prob):
    lo = np.array([b[0] for b in prob["bounds"]]); hi = np.array([b[1] for b in prob["bounds"]])
    return (X - lo) / (hi - lo)


def per_cell_mu_star(X, A, prob=None):
    """mu* per factor PER CELL -- the spatially explicit answer.

    A Morris trajectory changes exactly ONE factor between consecutive rows, so the elementary
    effect is (dY / dx) on the unit hypercube. Vectorised over cells, this is cheap once the runs
    exist -- no need to call SALib 300k times. Returns (n_factors, n_cells)."""
    prob = prob or salib_problem()
    U = _unit(np.asarray(X, dtype=float), prob)
    k = prob["num_vars"]
    acc = np.zeros((k, A.shape[1]), dtype="float64")
    cnt = np.zeros(k, dtype="int64")
    for j in range(len(U) - 1):
        d = U[j + 1] - U[j]
        nz = np.nonzero(np.abs(d) > 1e-9)[0]
        if len(nz) != 1:            # trajectory boundary (SALib stacks r trajectories end to end)
            continue
        i = int(nz[0])
        acc[i] += np.abs((A[j + 1] - A[j]) / d[i])
        cnt[i] += 1
    assert (cnt > 0).all(), f"factors with no elementary effects: {np.array(prob['names'])[cnt == 0]}"
    return acc / cnt[:, None], cnt


def cross_check(X, df, prob=None, metric="dissim_vs_base"):
    """Independent check: the vectorised elementary effects must equal SALib's on a scalar.

    Same maths, two implementations. If they disagree, the per-cell maps cannot be trusted --
    which matters because the per-cell path never goes through SALib (300k analyze calls would
    be far too slow), so this is its only validation. Verified to 1e-16 on synthetic data."""
    prob = prob or salib_problem()
    y = df.sort_values("run_id")[metric].to_numpy(dtype=float)
    mine, _ = per_cell_mu_star(X, y.reshape(-1, 1), prob)          # y as a single "cell"
    theirs = salib_morris.analyze(prob, X, y, num_levels=config.MORRIS["num_levels"])
    a, b = mine.ravel(), np.asarray(theirs["mu_star"])
    d = float(np.max(np.abs(a - b)))
    print(f"cross-check vs SALib on `{metric}`: max |diff| = {d:.3e}")
    assert d < 1e-8, "vectorised elementary effects disagree with SALib -- per-cell maps unsafe"
    return d


# ================= plots =================
def plot_morris(tbl, title="Morris screening", fname=None, fig_dir=None):
    """Ranked mu* bars + the standard mu*-vs-sigma scatter."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    t = tbl.sort_values("mu_star")
    axes[0].barh(t.factor, t.mu_star, xerr=t.mu_star_conf,
                 color=[BAR_CMAP(i % 10) for i in range(len(t))])
    axes[0].set_xlabel("mu*  (mean |elementary effect|)")
    axes[0].set_title("Influence ranking")
    axes[0].tick_params(axis="y", labelsize=8)
    axes[1].scatter(tbl.mu_star, tbl.sigma, s=45, color="#1b9e77", zorder=3)
    for _, r in tbl.iterrows():
        axes[1].annotate(r.factor, (r.mu_star, r.sigma), fontsize=7,
                         xytext=(4, 4), textcoords="offset points")
    lim = max(tbl.mu_star.max(), tbl.sigma.max()) * 1.1
    axes[1].plot([0, lim], [0, lim], ls="--", c="0.6", lw=1, label="sigma = mu*")
    axes[1].set_xlabel("mu*  (influence)"); axes[1].set_ylabel("sigma  (interaction / nonlinearity)")
    axes[1].set_title("High sigma = effect depends on the other factors")
    axes[1].legend(fontsize=8)
    fig.suptitle(title, fontsize=13)
    fig.tight_layout()
    if fig_dir and fname:
        Path(fig_dir).mkdir(parents=True, exist_ok=True)
        fig.savefig(Path(fig_dir) / fname, dpi=150, bbox_inches="tight")
    plt.show()


def plot_mu_star_maps(mu, domain, names, top=3, ref_tif=None, fig_dir=None, outline=None):
    """Per-cell mu* for the `top` most influential factors -- where each factor decides."""
    order = np.argsort(-mu.mean(axis=1))[:top]
    fig, axes = plt.subplots(1, len(order), figsize=(5.2 * len(order), 11))
    axes = np.atleast_1d(axes)
    for ax, i in zip(axes, order):
        img = np.full(domain.shape, np.nan, "float32")
        img[domain] = mu[i]
        im = ax.imshow(img, cmap="magma")
        fig.colorbar(im, ax=ax, shrink=0.35, label="mu* (allocation)")
        if outline is not None:
            outline.boundary.plot(ax=ax, color="black", linewidth=0.6)
        ax.set_title(f"{names[i]}", fontsize=10)
        ax.set_aspect("equal"); ax.set_axis_off()
    fig.suptitle("Where each factor drives the priorities (per-cell mu*)", fontsize=13, y=0.92)
    if fig_dir:
        Path(fig_dir).mkdir(parents=True, exist_ok=True)
        fig.savefig(Path(fig_dir) / "morris_mu_star_maps.png", dpi=150, bbox_inches="tight")
    plt.show()
