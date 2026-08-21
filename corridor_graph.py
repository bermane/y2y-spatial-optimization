"""Corridor network topology (05 v2, decision D7) -- MST backbone + bridge-backup augmentation.

Deliberately RASTER-FREE. Everything here takes an N x N least-cost distance matrix and node
labels, and returns a graph plus a per-edge table. That seam exists because this is the most
volatile code in the rebuild (the augmentation criterion, the centrality normalisation and the
criticality definitions are all likely to churn) and because it is the only part of 05 that can be
exercised on a hand-written 5 x 5 matrix -- see `selftest()`, which is the closest thing this repo
has to a unit test for the corridor engine.

WHY BRIDGE BACKUP, AND NOT A SPANNER
The rebuild plan originally proposed "retain any node-pair direct edge with cost <= alpha x MST
path cost". That criterion is VACUOUS: least-cost distance obeys the triangle inequality, so the
direct cost D[i,j] is never greater than the tree-path cost P_ij, and the test admits the complete
graph. Reversing it gives a t-spanner, which bounds STRETCH -- an efficiency property, not the
robustness property D7 actually asks for. A spanner can also leave a peripheral node untouched, so
the single-point-of-failure problem survives the fix.

Bridge backup is the only candidate whose acceptance condition IS D7's stated motivation, and it
gives the funder-facing criticality table a one-to-one story per added corridor: every retained
edge is justified by the named failure it insures. Two refinements matter:

  1. SEQUENTIAL, in descending criticality, with recomputation -- not independent per bridge. One
     added edge typically kills several bridges at once (any cycle it closes covers every tree edge
     on that cycle), so processing bridges independently would both overcount additions and
     misstate which failure each edge insures. This is the standard greedy heuristic for
     minimum-cost 2-edge-connectivity augmentation.
  2. A COST-RATIO CEILING beta. Adding the cheapest restoring edge unconditionally would route
     "alternatives" through land so resistant nobody would treat them as real. That does not create
     redundancy, it HIDES irreplaceability. Where no candidate clears the ceiling the link is
     flagged IRREPLACEABLE -- and those flags are the headline output: the augmented graph says
     where alternatives exist, the flags say where Y2Y cannot afford to lose the land at any
     reasonable price.

ADJACENCY (ZERO-COST) EDGES
Node pairs that already touch produce cost-0 edges -- in the northern run, Dene K'eh Kusan wraps 11
BC parks and clips each by a 2-63 km2 sliver. They are kept in the graph (connectivity and
criticality must see them) but they are excluded from failure enumeration and from backup
candidacy: an adjacency has no corridor land whose loss could sever it, so its failure mode is the
NODE disappearing, which the leave-one-out ensemble covers instead. They also carry infinite
conductance, which is why centrality is computed on the quotient graph (see `centrality`).
"""
import itertools

import networkx as nx
import numpy as np
import pandas as pd

ADJACENCY_COST = 0.0          # nodes that already touch; see the module docstring


def edge_id(i, j):
    """Stable, order-independent edge key."""
    a, b = (int(i), int(j)) if i < j else (int(j), int(i))
    return f"E{a:03d}_{b:03d}"


# ================= backbone =================
def mst_edges(D):
    """Minimum spanning forest over the finite entries of D, as a list of (i, j, cost).

    A forest, not a tree: D can contain inf (unreachable node pairs), and v1's hand-rolled Prim
    silently `break`ed in that case, quietly returning a partial tree. Here disconnection is
    reported by the caller instead of being masked.
    """
    G = _graph_from_matrix(D)
    return [(min(u, v), max(u, v), d["cost"])
            for u, v, d in nx.minimum_spanning_edges(G, weight="cost", data=True)]


def _graph_from_matrix(D):
    N = D.shape[0]
    G = nx.Graph()
    G.add_nodes_from(range(N))
    for i, j in itertools.combinations(range(N), 2):
        c = float(D[i, j])
        if np.isfinite(c):
            G.add_edge(i, j, cost=c)
    return G


def _components_after_removal(G, u, v):
    """Sizes of the two sides if edge (u,v) is cut. Restores the edge and its attributes."""
    attrs = dict(G[u][v])
    G.remove_edge(u, v)
    side = nx.node_connected_component(G, u)
    G.add_edge(u, v, **attrs)
    return len(side), G.number_of_nodes() - len(side), side


# ================= augmentation (D7) =================
def augment(D, beta, labels=None, verbose=True):
    """MST + sequential bridge backup under a cost-ratio ceiling.

    Returns (G, backup) where `backup` maps a bridge (i,j) -> dict(added=(a,b) or None,
    ratio=float or None, irreplaceable=bool).

    beta = None or 0 disables augmentation entirely (used by gate G4 to prove the backbone is
    untouched: with no additions the network must be exactly the MST).
    """
    N = D.shape[0]
    G = nx.Graph()
    G.add_nodes_from(range(N))
    mst = mst_edges(D)
    for i, j, c in mst:
        G.add_edge(i, j, cost=c, in_mst=True)

    backup = {}
    if not beta:
        if verbose:
            print(f"augmentation disabled (beta={beta!r}) -- MST only, {len(mst)} edges")
        return G, backup

    name = (lambda k: labels[k]) if labels is not None else (lambda k: f"node{k}")
    n_add = n_irrep = 0
    while True:
        # Recompute every iteration: one addition can retire several bridges at once.
        bridges = [(min(u, v), max(u, v)) for u, v in nx.bridges(G)]
        todo = [e for e in bridges
                if e not in backup and G[e[0]][e[1]]["cost"] > ADJACENCY_COST]
        if not todo:
            break

        # Descending criticality: the bridge whose loss strands the most node pairs goes first.
        scored = []
        for (u, v) in todo:
            a, b, side = _components_after_removal(G, u, v)
            scored.append((a * b, (u, v), side))
        scored.sort(key=lambda t: (-t[0], t[1]))
        pairs_lost, (u, v), side = scored[0]

        # Cheapest edge that reconnects the two sides, excluding adjacencies and existing edges.
        other = set(G.nodes) - side
        best, best_c = None, np.inf
        for i in side:
            for j in other:
                c = float(D[i, j])
                if (np.isfinite(c) and c > ADJACENCY_COST and not G.has_edge(i, j)
                        and c < best_c and (min(i, j), max(i, j)) != (u, v)):
                    best, best_c = (min(i, j), max(i, j)), c

        e_cost = G[u][v]["cost"]
        if best is not None and best_c <= beta * e_cost:
            G.add_edge(*best, cost=best_c, in_mst=False)
            backup[(u, v)] = dict(added=best, ratio=best_c / e_cost, irreplaceable=False)
            n_add += 1
            if verbose:
                print(f"  backup for {name(u)} <-> {name(v)}: add {name(best[0])} <-> "
                      f"{name(best[1])}  ({best_c:,.0f} = {best_c/e_cost:.2f}x)")
        else:
            backup[(u, v)] = dict(
                added=None,
                ratio=(best_c / e_cost) if best is not None and np.isfinite(best_c) else None,
                irreplaceable=True)
            n_irrep += 1
            if verbose:
                cheapest = (f"cheapest alternative {best_c/e_cost:.1f}x"
                            if best is not None and np.isfinite(best_c) else "no alternative exists")
                print(f"  IRREPLACEABLE {name(u)} <-> {name(v)}  ({cheapest} > beta={beta}) "
                      f"-- {pairs_lost} node pairs stranded if lost")

    if verbose:
        print(f"augmented: {len(mst)} MST edges + {n_add} backups = {G.number_of_edges()} edges | "
              f"{n_irrep} links IRREPLACEABLE at beta={beta}")
    return G, backup


# ================= centrality =================
def centrality(G):
    """Edge current-flow betweenness on the QUOTIENT graph (zero-cost cliques contracted).

    Infinite conductance between two nodes IS a merged node -- that is the correct physics, not a
    numerical nuisance to be capped away. A finite cap would approximate the same limit while
    introducing an arbitrary constant and a Laplacian ill-conditioned across orders of magnitude.

    The contraction is COMPUTATION-SCOPED ONLY: the caller's node list, banding, audit and
    leave-one-out all keep the nodes distinct, so the deliberate 2026-08-05 dedupe decision (merge
    only on >=50% mask overlap, so a wrapping neighbour stays a separate node) is untouched.

    Returns {(i,j): (raw, normalised)}. Adjacency edges get (nan, nan) -- they live inside a
    supernode, so betweenness through them is undefined. Store BOTH values: networkx normalises by
    2/[(n-1)(n-2)], which changes with n, so normalised centrality is NOT comparable across a
    leave-one-out ensemble where n varies.
    """
    # contract zero-cost cliques
    uf = {n: n for n in G.nodes}

    def find(x):
        while uf[x] != x:
            uf[x] = uf[uf[x]]
            x = uf[x]
        return x

    for u, v, d in G.edges(data=True):
        if d["cost"] <= ADJACENCY_COST:
            uf[find(u)] = find(v)

    Q = nx.Graph()
    for u, v, d in G.edges(data=True):
        qu, qv = find(u), find(v)
        if qu == qv:
            continue                                   # inside a supernode
        if not Q.has_edge(qu, qv) or d["cost"] < Q[qu][qv]["cost"]:
            Q.add_edge(qu, qv, cost=d["cost"], conductance=1.0 / d["cost"])

    raw = {}
    for comp in nx.connected_components(Q):
        sub = Q.subgraph(comp)
        if sub.number_of_nodes() < 3:                  # normalisation needs n >= 3
            for e in sub.edges:
                raw[tuple(sorted(e))] = 0.0
            continue
        for e, val in nx.edge_current_flow_betweenness_centrality(
                sub, normalized=False, weight="conductance").items():
            raw[tuple(sorted(e))] = float(val)

    n = Q.number_of_nodes()
    scale = 2.0 / ((n - 1) * (n - 2)) if n > 2 else 1.0
    out = {}
    for u, v, d in G.edges(data=True):
        qu, qv = find(u), find(v)
        key = tuple(sorted((qu, qv)))
        if qu == qv:
            out[(min(u, v), max(u, v))] = (np.nan, np.nan)
        else:
            r = raw.get(key, 0.0)
            out[(min(u, v), max(u, v))] = (r, r * scale)
    return out


# ================= criticality =================
def criticality(G, D):
    """Per-edge failure analysis. `nx.bridges` gives the disconnecting set in one pass, so single
    deletions only have to be enumerated for the cost question, not the connectivity question."""
    bridges = {(min(u, v), max(u, v)) for u, v in nx.bridges(G)}
    # Materialise the edge list first: the loop mutates G (remove/add) to price each failure, and
    # iterating G.edges() live while doing so raises "dictionary keys changed during iteration".
    edges = [(min(u, v), max(u, v), dict(d)) for u, v, d in G.edges(data=True)]
    intact = dict(nx.all_pairs_dijkstra_path_length(G, weight="cost"))   # hoisted: same every edge

    out = {}
    for u, v, d in edges:
        e = (u, v)
        if d["cost"] <= ADJACENCY_COST:
            # An adjacency cannot be severed by corridor loss; its failure mode is the node
            # disappearing, which the leave-one-out ensemble covers.
            out[e] = dict(is_adjacency=True, disconnects=False, n_pairs_lost=0,
                          cost_inflation=np.nan, mean_pair_inflation=np.nan)
            continue
        if e in bridges:
            a, b, _ = _components_after_removal(G, u, v)
            out[e] = dict(is_adjacency=False, disconnects=True, n_pairs_lost=a * b,
                          cost_inflation=np.inf, mean_pair_inflation=np.inf)
            continue
        G.remove_edge(u, v)
        detour = nx.shortest_path_length(G, u, v, weight="cost")
        cut = dict(nx.all_pairs_dijkstra_path_length(G, weight="cost"))
        G.add_edge(u, v, **d)
        ratios = [cut[a][b] / intact[a][b]
                  for a, b in itertools.combinations(sorted(G.nodes), 2)
                  if intact.get(a, {}).get(b, 0) > 0 and b in cut.get(a, {})]
        out[e] = dict(is_adjacency=False, disconnects=False, n_pairs_lost=0,
                      cost_inflation=detour / d["cost"],
                      mean_pair_inflation=float(np.mean(ratios)) if ratios else 1.0)
    return out


def stretch(G, D):
    """Worst-case detour factor over the network under NO failures -- reported as a diagnostic, not
    used as a selection criterion (that is what makes this not a spanner)."""
    sp = dict(nx.all_pairs_dijkstra_path_length(G, weight="cost"))
    worst, pair = 1.0, None
    for i, j in itertools.combinations(G.nodes, 2):
        d = D[i, j]
        p = sp.get(i, {}).get(j)
        if p is not None and np.isfinite(d) and d > 0:
            if p / d > worst:
                worst, pair = p / d, (i, j)
    return worst, pair


# ================= assembly =================
def build(D, labels, kinds=None, beta=2.5, verbose=True):
    """D + labels -> (G, edges_df). The one entry point corridors_core calls."""
    D = np.asarray(D, float)
    assert D.shape[0] == D.shape[1] == len(labels), "D must be square and match labels"
    assert np.allclose(D, D.T, equal_nan=True), "D must be symmetric before graph construction"

    G, backup = augment(D, beta, labels=labels, verbose=verbose)
    n_comp = nx.number_connected_components(G)
    if verbose and n_comp > 1:
        print(f"  WARNING network is a FOREST: {n_comp} components (some node pairs unreachable)")

    cen = centrality(G)
    crit = criticality(G, D)
    insured = {}                       # added edge -> the bridge it insures
    for br, info in backup.items():
        if info["added"]:
            insured[info["added"]] = br

    rows = []
    for u, v, d in sorted(G.edges(data=True), key=lambda t: (t[0], t[1])):
        e = (min(u, v), max(u, v))
        c = crit[e]
        b = backup.get(e, {})
        rows.append({
            "edge_id": edge_id(*e), "i": e[0], "j": e[1],
            "label_i": labels[e[0]], "label_j": labels[e[1]],
            "kind_pair": None if kinds is None else "-".join(sorted((kinds[e[0]], kinds[e[1]]))),
            "cost": d["cost"], "in_mst": bool(d.get("in_mst", False)),
            "is_adjacency": c["is_adjacency"],
            "ecfb_raw": cen[e][0], "ecfb_norm": cen[e][1],
            "disconnects": c["disconnects"], "n_pairs_lost": c["n_pairs_lost"],
            "cost_inflation": c["cost_inflation"],
            "mean_pair_inflation": c["mean_pair_inflation"],
            "backup_edge_id": edge_id(*b["added"]) if b.get("added") else None,
            "backup_ratio": b.get("ratio"),
            "irreplaceable": bool(b.get("irreplaceable", False)),
            "insures_edge_id": edge_id(*insured[e]) if e in insured else None,
        })
    df = pd.DataFrame(rows).set_index("edge_id")

    if verbose:
        s, pair = stretch(G, D)
        print(f"  worst-case detour under no failures: {s:.2f}x"
              + (f" ({labels[pair[0]]} <-> {labels[pair[1]]})" if pair else ""))
        print(f"  {int(df.is_adjacency.sum())} adjacency edges (already touching; no corridor land)")
        print(f"  {int(df.irreplaceable.sum())} IRREPLACEABLE links -- no viable alternative at any "
              f"cost within beta")
    return G, df


# ================= self-test (G2/G4 in miniature) =================
def selftest(verbose=True):
    """Assertions on a hand-built graph. The only genuinely unit-testable piece of the engine, and
    this repo has no pytest -- so it runs as a notebook cell."""
    # 5 nodes in a line: 0-1-2-3-4, plus an expensive shortcut 0-4.
    inf = np.inf
    D = np.array([
        [0,   10,  20,  30,  35],
        [10,  0,   10,  20,  30],
        [20,  10,  0,   10,  20],
        [30,  20,  10,  0,   10],
        [35,  30,  20,  10,  0.],
    ])
    labels = [f"n{k}" for k in range(5)]

    mst = mst_edges(D)
    assert len(mst) == 4, f"MST of 5 nodes must have 4 edges, got {len(mst)}"
    assert {(a, b) for a, b, _ in mst} == {(0, 1), (1, 2), (2, 3), (3, 4)}, mst

    # beta=0 -> augmentation disabled -> exactly the MST (this is gate G4 in miniature)
    G0, bk0 = augment(D, beta=0, verbose=False)
    assert G0.number_of_edges() == 4 and not bk0
    # every MST edge of a path graph is a bridge
    assert len(list(nx.bridges(G0))) == 4

    # beta large -> the 0-4 shortcut (35) closes the cycle and retires every bridge
    G1, bk1 = augment(D, beta=10, verbose=False)
    assert set(G0.edges) <= set(G1.edges), "augmentation must never perturb the backbone"
    assert G1.number_of_edges() > G0.number_of_edges()
    assert not list(nx.bridges(G1)), "a cycle over the whole path should leave no bridges"

    # beta tight -> nothing clears the ceiling -> everything irreplaceable, MST unchanged
    G2, bk2 = augment(D, beta=1.01, verbose=False)
    assert G2.number_of_edges() == 4
    assert all(v["irreplaceable"] for v in bk2.values()), bk2

    # adjacency edges are excluded from candidacy and from failure enumeration
    Dadj = D.copy()
    Dadj[0, 1] = Dadj[1, 0] = 0.0
    G3, bk3 = augment(Dadj, beta=10, verbose=False)
    assert (0, 1) not in bk3, "an adjacency must never be treated as a failable bridge"
    crit3 = criticality(G3, Dadj)
    assert crit3[(0, 1)]["is_adjacency"] and not crit3[(0, 1)]["disconnects"]
    cen3 = centrality(G3)
    assert np.isnan(cen3[(0, 1)][0]), "adjacency centrality is undefined (inside a supernode)"
    assert all(np.isfinite(v[0]) for k, v in cen3.items() if k != (0, 1)), \
        "contracting the zero-cost clique must leave every other edge finite"

    _, df = build(D, labels, beta=10, verbose=False)
    assert df.index.is_unique and len(df) == G1.number_of_edges()
    assert df.loc[df.in_mst, "cost"].notna().all()

    if verbose:
        print("corridor_graph.selftest OK — MST size, backbone containment, beta ceiling, "
              "adjacency handling, quotient centrality, edge table")
    return True
