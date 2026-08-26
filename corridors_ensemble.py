"""Structured corridor ensemble (05 v2, decision D8) -- axes B, C and D.

REPLACES v1's jitter ensemble, which multiplied the final resistance surface by uniform noise. That
represented no identifiable uncertainty: not parameter, not data, not model structure, so a cell's
"frequency" answered no question anyone had asked. Here every axis maps to a documented assumption
and the output says WHICH assumption moved WHICH link.

    A. component cost perturbation   DEFERRED behind H2 (ranges are a judgment call, and it is the
                                     only axis that changes the resistance surface)
    B. band cutoff                   cwd_cutoff_abs x {0.5, 1, 2} -- how wide is a corridor?
    C. node leave-one-out            one run per node -- what is contingent on a single proposal?
    D. beta sweep                    the redundancy ceiling -- what counts as a viable alternative?

WHY THIS IS CHEAP, WHICH IS THE WHOLE DESIGN
Cost-weighted distance depends only on (resistance, node seeds). Axes B and D never touch either.
Axis C drops a node, which deletes a row and column from the distance matrix but leaves every
REMAINING node's field bit-identical. So the entire ensemble reuses ONE cached CWD set -- the
expensive stage runs once -- and each member is a graph rebuild plus a band re-derivation. At 300 m
that is the difference between minutes and days.

Serial, with memmaps, deliberately: the re-derivations are cheap, and 05 is GIL-bound pure-Python
MCP_Geometric rather than ensemble_core's R subprocesses, so process workers would only multiply
resident grids. Resumability follows ensemble_core: a member is done when its summary exists.
"""
import json
import pathlib

import numpy as np
import pandas as pd

import config
import corridor_graph as cg
import corridors_core as cc


def _config_hash(cutoff, beta, drop_name):
    """Duplicate members are resolved by CONFIG-HASH EQUALITY, not by name (G12): e.g. the 1.0x
    axis-B row and the base-beta axis-D row are the baseline under different labels."""
    import hashlib
    return hashlib.md5(f"{float(cutoff):.6g}|{float(beta):.6g}|{int(drop_name)}"
                       .encode()).hexdigest()[:12]


def design(A):
    """One row per ensemble member. `kind` names the axis, so attribution is a groupby.

    Axis C is leave-one-out BY NAME (D16): dropping a name drops ALL its routing units together --
    including `no_link` parts, which are independent in the graph but share the name's realisation
    risk. Expected member count (G12): 1 baseline + (|cutoff_mult|-1) B + |names| C +
    (|beta_sweep|-1) D = 47 on the 42-name network.
    """
    e = A.cfg["ensemble"]
    base_cut, base_beta = A.cutoff, A.cfg["beta"]
    rows = [dict(kind="baseline", cutoff=base_cut, beta=base_beta, drop_name=-1,
                 label="baseline")]
    for m in e.get("cutoff_mult", []):
        rows.append(dict(kind="B_cutoff", cutoff=base_cut * m, beta=base_beta, drop_name=-1,
                         label=f"cutoff x{m:g}"))
    for b in e.get("beta_sweep", []):
        rows.append(dict(kind="D_beta", cutoff=base_cut, beta=b, drop_name=-1,
                         label=f"beta {b:g}"))
    if e.get("leave_one_out"):
        for k, n in enumerate(A.names):
            rows.append(dict(kind="C_loo", cutoff=base_cut, beta=base_beta, drop_name=k,
                             label=f"drop {cc._short_node_name(n['label'], 22)}"))

    df = pd.DataFrame(rows)
    df["config_hash"] = [_config_hash(r.cutoff, r.beta, r.drop_name) for r in df.itertuples()]
    dupes = df.duplicated("config_hash")
    if dupes.any():
        print(f"  design: {int(dupes.sum())} duplicate member(s) removed by config-hash "
              f"({', '.join(df.loc[dupes, 'label'])})")
    df = df[~dupes].reset_index(drop=True)
    df["run_id"] = np.arange(len(df))
    return df


def _locked_flat(A, keep_names):
    """Flat band indices of locked intra-name edges whose name survives this member."""
    flat = np.zeros(A.shape[0] * A.shape[1], bool)
    for eid in getattr(A, "locked_edge_ids", []):
        nlbl = A.edges.loc[eid, "name_label"]
        k = next(i for i, n in enumerate(A.names) if n["label"] == nlbl)
        if k in keep_names:
            flat[A.bands[eid]] = True
    return flat


def _member(A, row):
    """Solve one member off the cached CWD. Returns (corridor mask, edges table)."""
    drop = int(row["drop_name"])
    keep_names = {k for k in range(len(A.names)) if k != drop}
    keep = [u for u in range(len(A.nodes)) if A.unit_name[u] in keep_names]
    D = A.D[np.ix_(keep, keep)]
    labels = [A.nodes[k][0] for k in keep]
    kinds = [A.kinds[k] for k in keep]

    _, edges = cg.build(D, labels, kinds, beta=float(row["beta"]), verbose=False)
    bands, _, _, _ = cc.edge_bands(A, A.cwd, A.mcp, edges, float(row["cutoff"]), "abs",
                                   want_slack=False, nmap=keep)

    # Node land is excluded relative to THIS member's name set. Dropping a name must not silently
    # hand its footprint to the corridor -- that would read as "the corridor grew" when in fact an
    # anchor was removed. Locked intra-name bands of SURVIVING names are part of every member.
    flat = np.zeros(A.shape[0] * A.shape[1], bool)
    for idx in bands.values():
        flat[idx] = True
    flat |= _locked_flat(A, keep_names)
    swath = flat.reshape(A.shape) & A.pu
    node_union = np.zeros(A.shape, bool)
    for k in keep_names:
        node_union |= A.names[k]["mask"]
    return swath & ~node_union, edges


def run(A, out_dir=None, verbose=True):
    """Solve every member, resumably. Writes one small directory per member."""
    assert getattr(A, "D", None) is not None, "run corridor_network(A) first (needs A.D and A.cwd)"
    out_dir = pathlib.Path(out_dir or (A.run_dir / "ensemble"))
    out_dir.mkdir(parents=True, exist_ok=True)
    df = design(A)
    df.to_csv(out_dir / "design.csv", index=False)

    todo = [r for _, r in df.iterrows()
            if not (out_dir / f"run_{int(r['run_id']):04d}" / "member.json").exists()]
    print(f"ensemble: {len(df)} members | {len(df)-len(todo)} already done | {len(todo)} to solve")

    for n, row in enumerate(todo, 1):
        rid = int(row["run_id"])
        d = out_dir / f"run_{rid:04d}"
        d.mkdir(exist_ok=True)
        corr, edges = _member(A, row)
        cc._tif(A, np.where(corr, 1, 0), d / "corridors.tif", "uint8", 0)
        edges.to_csv(d / "edges.csv", encoding="utf-8-sig")
        (d / "member.json").write_text(json.dumps(dict(
            run_id=rid, kind=row["kind"], label=row["label"],
            config_hash=row["config_hash"],
            cutoff=float(row["cutoff"]), beta=float(row["beta"]),
            drop_name=int(row["drop_name"]),
            drop_name_label=(A.names[int(row["drop_name"])]["label"]
                             if int(row["drop_name"]) >= 0 else None),
            corridor_km2=round(int(corr.sum()) * A.cell_km2),
            n_edges=len(edges), n_irreplaceable=int(edges.irreplaceable.sum()),
            n_groups=cc._n_groups(A, corr)), indent=2, ensure_ascii=False))
        if verbose:
            print(f"  [{n:>3}/{len(todo)}] run_{rid:04d} {row['kind']:10s} {row['label'][:34]:34s} "
                  f"{int(corr.sum())*A.cell_km2:>8,.0f} km²")
    return out_dir


def gate_g12(A):
    """G12 -- distinct member count: 1 baseline + (B - the 1x duplicate) + one C per NAME +
    (D - the base-beta duplicate), duplicates resolved by config-hash equality, not by name."""
    e = A.cfg["ensemble"]
    df = design(A)
    expect = (1 + sum(1 for m in e.get("cutoff_mult", []) if float(m) != 1.0)
              + (len(A.names) if e.get("leave_one_out") else 0)
              + sum(1 for b in e.get("beta_sweep", []) if float(b) != float(A.cfg["beta"])))
    assert df["config_hash"].is_unique, "G12 FAILED: duplicate config hashes survived dedup"
    assert len(df) == expect, (
        f"G12 FAILED: {len(df)} distinct members, expected {expect} "
        f"(1 + B{sum(1 for m in e.get('cutoff_mult', []) if float(m) != 1.0)} + "
        f"C{len(A.names)} + D{sum(1 for b in e.get('beta_sweep', []) if float(b) != float(A.cfg['beta']))})")
    print(f"G12 OK: {len(df)} distinct members (baseline + "
          f"{sum(1 for m in e.get('cutoff_mult', []) if float(m) != 1.0)} B + {len(A.names)} C + "
          f"{sum(1 for b in e.get('beta_sweep', []) if float(b) != float(A.cfg['beta']))} D), "
          f"duplicates removed by config-hash")
    return True


def collect(A, out_dir=None):
    """ATTRIBUTION surface, per-edge presence, and per-axis attribution rasters (D15).

    The attribution is the point. A jitter ensemble could only say "this cell was used 60% of the
    time"; this says which assumption the 40% depends on -- band width, redundancy ceiling, or one
    unrealized IPCA proposal -- and those have completely different consequences for a decision.

    NAMING IS LOAD-BEARING (D11/D15): ~42 of ~47 members are leave-one-out, so the member fraction
    is "share of dropped names that didn't matter", NOT a near-optimal sampling frequency. It is
    written as ensemble_attribution.tif and must never be labelled "frequency" or "selection
    frequency"; the wall-to-wall near-optimal product is cc.near_optimality's slack surface.
    """
    out_dir = pathlib.Path(out_dir or (A.run_dir / "ensemble"))
    members, attr, edge_seen = [], None, {}
    by_axis = {}

    for d in sorted(out_dir.glob("run_*")):
        f = d / "member.json"
        if not f.exists():
            continue
        m = json.loads(f.read_text())
        import rioxarray
        corr = rioxarray.open_rasterio(d / "corridors.tif", masked=True).squeeze().values > 0
        attr = corr.astype("float32") if attr is None else attr + corr
        ax = by_axis.setdefault(m["kind"], [np.zeros(A.shape, "float32"), 0])
        ax[0] += corr; ax[1] += 1
        m["_mask"] = corr
        members.append(m)
        for eid in pd.read_csv(d / "edges.csv", index_col=0).index:
            edge_seen.setdefault(eid, []).append(m["kind"])

    n = len(members)
    assert n, f"no ensemble members found under {out_dir}"
    attr /= n
    A.attribution = attr

    core = A.cfg["ensemble"].get("robust_core_freq", 0.9)
    tidy = pd.DataFrame([{k: v for k, v in m.items() if k != "_mask"} for m in members])
    base = next(m["_mask"] for m in members if m["kind"] == "baseline")
    tidy["jaccard_vs_baseline"] = [round(cc._jaccard(base, m["_mask"]), 4) for m in members]

    print(f"ensemble over {n} members")
    print(f"  robust core (attribution >= {core:g}): {int((attr >= core).sum())*A.cell_km2:,.0f} km² "
          f"of {int((attr > 0).sum())*A.cell_km2:,.0f} km² ever used")
    print("\n  per-axis attribution (1 - Jaccard vs baseline = how much that axis moves the network):")
    for kind, g in tidy[tidy.kind != "baseline"].groupby("kind"):
        d = 1 - g["jaccard_vs_baseline"]
        print(f"    {kind:10s} n={len(g):>3}  mean {d.mean():.3f}  max {d.max():.3f}  "
              f"({g.loc[d.idxmax(), 'label']})")

    loo = tidy[tidy.kind == "C_loo"].sort_values("jaccard_vs_baseline")
    if len(loo):
        print("\n  most structurally load-bearing names (lowest Jaccard when dropped) -- "
              "AXIS C IS THE ONE TO READ CLOSELY:")
        for r in loo.head(5).itertuples():
            broke = "" if r.n_groups == 1 else f"  ** NETWORK SPLITS INTO {r.n_groups} **"
            print(f"    {r.drop_name_label[:52]:52s} J={r.jaccard_vs_baseline:.3f}{broke}")

    edge_freq = pd.DataFrame(
        [{"edge_id": e, "presence_freq": round(len(v) / n, 3)} for e, v in edge_seen.items()]
    ).set_index("edge_id").sort_values("presence_freq")

    cc._tif(A, attr, out_dir / "ensemble_attribution.tif", "float32", -1)
    for kind, (s, k) in by_axis.items():
        if kind != "baseline":
            cc._tif(A, s / k, out_dir / f"attribution_{kind}.tif", "float32", -1)
    tidy.to_csv(out_dir / "members.csv", index=False, encoding="utf-8-sig")
    edge_freq.to_csv(out_dir / "edge_frequency.csv", encoding="utf-8-sig")
    print(f"\n  wrote ensemble_attribution.tif, attribution_<axis>.tif, members.csv, "
          f"edge_frequency.csv -> {out_dir.relative_to(config.PROJECT_DIR)}")
    A.ensemble = dict(tidy=tidy, edge_freq=edge_freq, attribution=attr)
    return A


def gate_g7(A, out_dir=None):
    """G7 -- the cache-reuse shortcut is sound.

    A leave-one-out member that drops NOTHING must reproduce the baseline exactly. If it does not,
    the subset/nmap indexing is wrong and every axis-C result is quietly meaningless.
    """
    row = pd.Series(dict(run_id=-1, kind="C_loo", cutoff=A.cutoff, beta=A.cfg["beta"],
                         drop_name=-1, label="drop nothing", config_hash="g7"))
    corr, edges = _member(A, row)
    j = cc._jaccard(corr, A.corridor)
    n_unit = len(A.edges) - len(getattr(A, "locked_edge_ids", []))
    print(f"G7 cache reuse: drop-nothing member vs baseline Jaccard = {j:.6f}, "
          f"edges {len(edges)} vs {n_unit} unit edges (+{len(getattr(A, 'locked_edge_ids', []))} "
          f"locked, shared)")
    assert j == 1.0 and len(edges) == n_unit, (
        f"G7 FAILED: re-deriving from the cached CWD did not reproduce the baseline "
        f"(Jaccard {j:.6f}). The node-index mapping in edge_bands(nmap=...) is suspect.")
    print("  G7 OK")
    return True
