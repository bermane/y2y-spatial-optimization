> **APPLIED 2026-09-11** — spliced verbatim into `05_corridors_v2_addendum_run_and_alternatives.md` (header, changelog, D21, constants, step 2c, G17, §5, §6, §7) and `06_…_spec.md` (v1.2.9); implemented as `corridors_core.adjacency_graph` (M5.19). Kept as the record; nothing here is pending.

# PATCH — D21 adjacency (neighbour) graph. Splice into `spec/05_corridors_v2_addendum_run_and_alternatives.md`; do not regenerate the spec.

Every block below names its target section. Nothing existing is edited except the header line
and the D7 follow-up note in §7. Same-session update to `spec/methods_log.md` (M5.19) required.

---

## → Header line (replace "Adds D11–D20" with "Adds D11–D21")

## → Changelog (prepend)

- 2026-09-11 — **D21: Linkage Mapper–style adjacency graph computed as a diagnostic
  universe beside the backbone.** Cost-allocation neighbour graph on the part-level CWD
  fields, contracted to names; per-name degree (`n_neighbours`), adjacency status of every
  backbone/backup edge, gate G17 (MST ⊆ adjacency), one appendix map. **No change to bands,
  classes, `linkage_priority.tif`, the 58-link network, or the pinned examples.** A D7
  amendment (restrict backup candidates to adjacency edges) is logged as a follow-up decision
  contingent on the measured count of non-adjacent backups (§7). M5.19.

## → §1 decision table (append after D20)

| # | Decision | Rationale |
|---|---|---|
| D21 | **Adjacency graph as diagnostic universe.** `G_adj` = cost-weighted allocation adjacency: allocate every routable cell to the seed part with the minimum CWD (argmin over the cached part fields; ties → lowest part id); two parts are adjacent if their allocation zones share an 8-connected boundary; contract parts to names (and zero-cost cliques as in §7) to give the name-level graph. Optional LM-style filters are **off** (no distance cap; no intermediate-core drop) so the graph is the raw neighbour set — filters are reported as counts, not applied. Products: `adjacency_edges.csv` (i, j, `in_backbone`, `edge_class` if in the network, `min_e` cost, LCP length), `adjacency_nodes.csv` (`n_neighbours` per name; also per part), the `is_adjacent` column added to `corridor_edges.csv`, and one appendix figure (`adjacency_map`: thin neighbour links as lines — **not bands** — over the M1 basemap). **Not a routing input; no bands are computed for adjacency-only edges; no legend class.** | Linkage Pathways' network is the neighbour graph (McRae & Kavanagh 2011); ours is the minimum backbone plus affordable backups. Reporting both makes the relationship explicit: the difference is the choice space, which is the Act 1 quantity the current products cannot state — a name's number of possible partner links. Kept as a universe rather than adopted as the network because banding ~100 neighbour links destroys the must-have/optional distinction unless a weighted priority ranks them (the D5-rejected blend). Cost is trivial: the allocation is an argmin over fields already in memmaps. |

## → §2 constants (append)

| key | value | note |
|---|---|---|
| `adjacency` | `{"metric": "cwd", "connectivity": 8, "distance_cap_km": null, "drop_through_core": false}` | D21; filters off, counts reported. `metric: "euclid"` available for the comparison column only. |

## → §3 run sequence (insert after Step 2, before Step 3)

**Step 2c — adjacency graph (D21).** From the cached part-level CWD fields: allocation
raster (argmin; `allocation.tif`, int32 part id), zone-boundary pairs → part adjacency →
name adjacency (contracted as §7). Join to `corridor_edges.csv` (`is_adjacent`); write
`adjacency_edges.csv`, `adjacency_nodes.csv`. Report: |E_adj|, |E_adj ∩ backbone|,
number of backbone/backup edges **not** adjacent (with the intervening name(s) whose zone the
LCP crosses), and the counts LM's optional filters *would* remove (edges whose LCP crosses a
third name's mask; edges beyond a nominal 200 km). Euclidean-allocation adjacency computed
as a comparison column (`is_adjacent_euclid`) — the LM default — so the metric choice is
visible. **G17** here. Lives in notebook 02 after the network is built (or notebook 04 step 0b
when re-attaching); zero new CWD work.

## → §4 gates (append)

| gate | invariant | where |
|---|---|---|
| G17 | every inter-name MST edge is an adjacency edge (`is_adjacent` true for all `edge_class == "mst"`); locked intra-name edges are exempt (parts of one name may be separated by another name's zone by design — reported, not asserted). Failure is investigated, not auto-fixed: an MST edge whose LCP crosses a third name's zone is either a multipart-field bug (Clarification 1) or a genuine case to document. | step 2c, hard assert on `mst` edges |

## → §5 outputs (append to the list)

`allocation.tif`, `adjacency_edges.csv`, `adjacency_nodes.csv`, `figures/adjacency_map.png`;
`corridor_edges.csv` gains `is_adjacent`, `is_adjacent_euclid`, `via_names` (D21).

## → §6 reporting rules (append)

- The adjacency graph is reported as the **neighbour universe** (Linkage Pathways' network
  convention), the backbone as the **minimum network plus affordable backups**; the deck and
  methods text state that the difference between them is the choice space, never that the
  backbone is "the corridors" and adjacency "extra corridors". `n_neighbours` is the Act 1
  option count per area; it is a count of possible partner links, not of corridors.

## → §7 human tasks / follow-ups (append)

- **Follow-up decision (D7 amendment, not taken):** if step 2c reports ≥ 1 backup edge that is
  not adjacent (its LCP crosses a third name's allocation zone), decide whether backup
  candidates should be restricted to `E_adj` — LM's intermediate-core rule. Restriction would
  change the network and therefore the pinned examples (06 v1.2.4), so it is taken **after
  October** unless the count is zero, in which case it becomes documentation only
  ("backups are, empirically, all neighbour links"). Logged either way.

---

## → 06 spec, changelog (prepend; presentation impact only)

- v1.2.9 (2026-09-11) — from 05 D21: `n_neighbours` available per name (appendix; optionally
  one phrase in the Act 1 narrative — "X could connect to N neighbouring areas"); `adjacency_map`
  in the appendix beside the tier/attribution maps, links as thin lines, never bands. No change
  to M0–M3, stars, or the two alternatives tables. Methods note gains one sentence: the
  neighbour graph is Linkage Mapper's network convention; the maps show the minimum network
  plus affordable backups; the difference is the choice space.
