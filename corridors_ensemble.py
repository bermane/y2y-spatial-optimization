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


def design(A):
    """One row per ensemble member. `kind` names the axis, so attribution is a groupby."""
    e = A.cfg["ensemble"]
    base_cut, base_beta = A.cutoff, A.cfg["beta"]
    rows = [dict(run_id=0, kind="baseline", cutoff=base_cut, beta=base_beta, drop_node=-1,
                 label="baseline")]

    for m in e.get("cutoff_mult", []):
        if m == 1.0:
            continue
        rows.append(dict(kind="B_cutoff", cutoff=base_cut * m, beta=base_beta, drop_node=-1,
                         label=f"cutoff x{m:g}"))
    for b in e.get("beta_sweep", []):
        if b == base_beta:
            continue
        rows.append(dict(kind="D_beta", cutoff=base_cut, beta=b, drop_node=-1,
                         label=f"beta {b:g}"))
    if e.get("leave_one_out"):
        for k, (lbl, _) in enumerate(A.nodes):
            rows.append(dict(kind="C_loo", cutoff=base_cut, beta=base_beta, drop_node=k,
                             label=f"drop {cc._short_node_name(lbl, 22)}"))

    df = pd.DataFrame(rows)
    df["run_id"] = np.arange(len(df))
    return df


def _member(A, row):
    """Solve one member off the cached CWD. Returns (corridor mask, edges table)."""
    keep = [k for k in range(len(A.nodes)) if k != int(row["drop_node"])]
    D = A.D[np.ix_(keep, keep)]
    labels = [A.nodes[k][0] for k in keep]
    kinds = [A.kinds[k] for k in keep]

    _, edges = cg.build(D, labels, kinds, beta=float(row["beta"]), verbose=False)
    bands, _, _, _ = cc.edge_bands(A, A.cwd, A.mcp, edges, float(row["cutoff"]), "abs",
                                   want_slack=False, nmap=keep)

    # Node land is excluded relative to THIS member's node set. Dropping a node must not silently
    # hand its footprint to the corridor -- that would read as "the corridor grew" when in fact an
    # anchor was removed.
    flat = np.zeros(A.shape[0] * A.shape[1], bool)
    for idx in bands.values():
        flat[idx] = True
    swath = flat.reshape(A.shape) & A.pu
    node_union = np.zeros(A.shape, bool)
    for k in keep:
        node_union |= A.nodes[k][1]
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
            cutoff=float(row["cutoff"]), beta=float(row["beta"]),
            drop_node=int(row["drop_node"]),
            drop_node_label=(A.nodes[int(row["drop_node"])][0]
                             if int(row["drop_node"]) >= 0 else None),
            corridor_km2=round(int(corr.sum()) * A.cell_km2),
            n_edges=len(edges), n_irreplaceable=int(edges.irreplaceable.sum()),
            n_groups=cc._n_groups(A, corr)), indent=2, ensure_ascii=False))
        if verbose:
            print(f"  [{n:>3}/{len(todo)}] run_{rid:04d} {row['kind']:10s} {row['label'][:34]:34s} "
                  f"{int(corr.sum())*A.cell_km2:>8,.0f} km²")
    return out_dir


def collect(A, out_dir=None):
    """Frequency surface, per-edge presence frequency, and PER-AXIS ATTRIBUTION.

    The attribution is the point. A jitter ensemble could only say "this cell was used 60% of the
    time"; this says which assumption the 40% depends on -- band width, redundancy ceiling, or one
    unrealized IPCA proposal -- and those have completely different consequences for a decision.
    """
    out_dir = pathlib.Path(out_dir or (A.run_dir / "ensemble"))
    members, freq, edge_seen = [], None, {}

    for d in sorted(out_dir.glob("run_*")):
        f = d / "member.json"
        if not f.exists():
            continue
        m = json.loads(f.read_text())
        import rioxarray
        corr = rioxarray.open_rasterio(d / "corridors.tif", masked=True).squeeze().values > 0
        freq = corr.astype("float32") if freq is None else freq + corr
        m["_mask"] = corr
        members.append(m)
        for eid in pd.read_csv(d / "edges.csv", index_col=0).index:
            edge_seen.setdefault(eid, []).append(m["kind"])

    n = len(members)
    assert n, f"no ensemble members found under {out_dir}"
    freq /= n
    A.frequency = freq

    core = A.cfg["ensemble"].get("robust_core_freq", 0.9)
    tidy = pd.DataFrame([{k: v for k, v in m.items() if k != "_mask"} for m in members])
    base = next(m["_mask"] for m in members if m["kind"] == "baseline")
    tidy["jaccard_vs_baseline"] = [round(cc._jaccard(base, m["_mask"]), 4) for m in members]

    print(f"ensemble over {n} members")
    print(f"  robust core (freq >= {core:g}): {int((freq >= core).sum())*A.cell_km2:,.0f} km² "
          f"of {int((freq > 0).sum())*A.cell_km2:,.0f} km² ever used")
    print("\n  per-axis attribution (1 - Jaccard vs baseline = how much that axis moves the network):")
    for kind, g in tidy[tidy.kind != "baseline"].groupby("kind"):
        d = 1 - g["jaccard_vs_baseline"]
        print(f"    {kind:10s} n={len(g):>3}  mean {d.mean():.3f}  max {d.max():.3f}  "
              f"({g.loc[d.idxmax(), 'label']})")

    loo = tidy[tidy.kind == "C_loo"].sort_values("jaccard_vs_baseline")
    if len(loo):
        print("\n  most structurally load-bearing nodes (lowest Jaccard when dropped):")
        for r in loo.head(5).itertuples():
            broke = "" if r.n_groups == 1 else f"  ** NETWORK SPLITS INTO {r.n_groups} **"
            print(f"    {r.drop_node_label[:52]:52s} J={r.jaccard_vs_baseline:.3f}{broke}")

    edge_freq = pd.DataFrame(
        [{"edge_id": e, "presence_freq": round(len(v) / n, 3)} for e, v in edge_seen.items()]
    ).set_index("edge_id").sort_values("presence_freq")

    cc._tif(A, freq, out_dir / "corridor_frequency.tif", "float32", -1)
    tidy.to_csv(out_dir / "members.csv", index=False, encoding="utf-8-sig")
    edge_freq.to_csv(out_dir / "edge_frequency.csv", encoding="utf-8-sig")
    print(f"\n  wrote corridor_frequency.tif, members.csv, edge_frequency.csv -> "
          f"{out_dir.relative_to(config.PROJECT_DIR)}")
    A.ensemble = dict(tidy=tidy, edge_freq=edge_freq, frequency=freq)
    return A


def gate_g7(A, out_dir=None):
    """G7 -- the cache-reuse shortcut is sound.

    A leave-one-out member that drops NOTHING must reproduce the baseline exactly. If it does not,
    the subset/nmap indexing is wrong and every axis-C result is quietly meaningless.
    """
    row = pd.Series(dict(run_id=-1, kind="C_loo", cutoff=A.cutoff, beta=A.cfg["beta"],
                         drop_node=-1, label="drop nothing"))
    corr, edges = _member(A, row)
    j = cc._jaccard(corr, A.corridor)
    print(f"G7 cache reuse: drop-nothing member vs baseline Jaccard = {j:.6f}, "
          f"edges {len(edges)} vs {len(A.edges)}")
    assert j == 1.0 and len(edges) == len(A.edges), (
        f"G7 FAILED: re-deriving from the cached CWD did not reproduce the baseline "
        f"(Jaccard {j:.6f}). The node-index mapping in edge_bands(nmap=...) is suspect.")
    print("  G7 OK")
    return True
