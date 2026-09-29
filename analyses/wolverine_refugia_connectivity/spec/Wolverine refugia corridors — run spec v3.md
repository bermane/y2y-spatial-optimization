# Wolverine refugia corridors — run spec v3

Sep 28, 2026 · @Ethan

## 1. Purpose and what changed from v2

v3 re-runs the wolverine refugia corridor analysis as a two-level network: refugia complexes (groups of patches the adjacency rule declares contiguous) and the linkages between them. v2 (`v2_run001`) treated every patch as a node and returned 170 links of which 130 (76%) were near-contiguous slivers inside mountain ecosystems; the corridor product was buried under them and the irreplaceability counts were a node-density artefact.

Three things change; everything else is inherited from the northern IPCA corridors package as in v2.

1. Nodes are contracted into complexes before routing, using the D25 adjacency rule as already registered (no new threshold).
2. The product is two layers with equal standing: complexes (with protection coverage and a within-complex sliver table) and inter-complex corridors. Refugia are a climate prediction, not a tenure, so a corridor between two unprotected complexes is not on its own actionable.
3. The as-published surface is compared at LCP-centreline level only, between fixed complex pairs; corridor bands are a product feature of the variant network and are not compared.

Nothing is tuned. The one allowance (D31, 13.6229 cost units = 4.09 km of extra travel on open ground) is inherited and untouched; every count below scales with it and that is the reason not to touch it.

## 1a. v2.5 — the deliverable due 2026-09-29 (do this first; v3 sections 3–6 are deferred)

v2.5 post-processes `v2_run001` outputs into the two-layer product without re-running routing. No new routing, no contraction re-run, no baseline run, no glacier sensitivities; those stay in the v3 spec as next steps. Work on a clean tree; tag `v2_run001` before starting.

One new notebook (`06_v2_postprocess`) reading the v2 link table, node table, node polygons and per-link band polygons:

1. Complexes: build a graph from the 130 near-contiguous (D25) links; connected components are complexes. Write `complex_id` to every node; dissolve node polygons per complex; compute complex area. Single-node components are complexes.
2. Corridor links: the 40 non-near-contiguous links, with `complex_from` and `complex_to`. Check that none has both ends in one complex; keep every link where several join the same complex pair and note the count.
3. Coverage columns, for each complex and for each corridor link's dissolved band: share in existing PAs; incremental share added by proposed IPCAs; share in the prioritizr core (BALANCED scenario, guarded frequent tier); share outside all three. Add one row of area expectation: the same shares over the whole Y2Y frame, so overlap is read against expectation, not as a raw percentage.
4. Within-complex sliver table: one row per near-contiguous link — patches, path length, and any cost-10 or cost-100 cell on the path if that is cheap to extract from v2 outputs; otherwise path length only, with the column marked as not computed.
5. Accounting: corridor land as a dissolved union, per-class band land as dissolved unions, and a separate per-link-sum column labelled as such; branch counts as links with n branches so the total reconciles.
6. Names: `node_names.csv` renamed as refugia ("Refugium (Sustut)"); the six Nááts'Ihch'Oh variants collapse under one complex name; T1–T4 regenerated after the M6.7 fix.
7. Act check: which act the Banff–Yoho links and the Bow Valley crossing fall in; if they straddle 51°N, move the break to the Bow Valley for the draft and record it.

`05` outputs for the draft: complex outlines with protection shading; the 40 corridor links by class with the tenth-percentile pinch marked; no hatched near-contiguous bands; legend carries the sliver count per complex. Headline table: complexes and share protected by act; corridor links and share crossing unprotected land (37 of 40); corridor land outside PAs, IPCAs and core; narrowing links by act; the four last-affordable links by name with p10 width ratio.

Report text states the surface decision (section 2) in one paragraph, notes that contraction will move the augmentation set slightly, and lists the baseline comparison, glacier sensitivities and the v3 re-run as next steps.

## 2. Resistance surface

The campaign runs on the variant "O'Brien 2025, generic terrain rules withheld": the O'Brien et al. 2025 movement-cost surface (US extension of Pither et al. 2023; 300 m; ordinal costs 1/10/100/1000; per-pixel maximum over the source's input layers) recomputed with the source's three expert-assigned natural-terrain rules withheld. It is not a wolverine-specific resistance surface and claims only that alpine terrain is not a wall.

| Rule (source) | Source cost | Variant | Basis |
| --- | --- | --- | --- |
| Elevation > 2,300 m (GMTED2010) | 1000 | withheld | inverts documented wolverine habitat use; no terrain resistance signal in the landscape genetics |
| Slope > 30° (GMTED2010) | 1000 | withheld | same; steep avalanche terrain is selected, not avoided |
| Glaciers (source: CanVec; here RGI 7.0 both sides of 49°N) | 1000 | withheld | no measured resistance; snow-covered ice in the dispersal season is not distinguishable from adjacent alpine |
| Lakes ≥ 10 ha, rivers > 28 m³/s, ocean | 1000 | 1000 (unchanged) | seasonally permeable but low-leverage; kept for scope discipline, noted as a bias for large intact northern lakes |
| All human layers; the 10 and 100 bands | as published | unchanged | — |

Implementation rules:

- Recompute the per-pixel maximum with the three layers removed; never flip cells to 1. A terrain cell coincident with a human or disturbance layer keeps that layer's cost.
- Check the OSF deposit of Pither et al. 2023 for the component layers before reconstructing elevation and slope from GMTED; use RGI 7.0 for ice on both sides of the border to avoid a seam. Quantify once the area difference between RGI 7.0 and CanVec ice (CanVec includes perennial snowfields RGI omits).
- Runs: variant (product); as-published baseline (one run, section 6); glacier sensitivities at cost 10 and at cost 1000 (expected immaterial; reported as route displacement on the affected links only).
- The earlier ad hoc floor (gHM < 0.05 and elevation ≥ 1,500 m) is withdrawn and does not appear in the register.

As-published diagnostics to carry into the report: 28.4% of core refugia sits on cost 1000 against 13.8% of Y2Y; the elevation and slope rules account for 71% of the cost 1000 under core refugia and 52% Y2Y-wide. Because the source's ordinal costs were designed for linear barriers crossed in one cell, an areal cost-1000 class makes a 5 km alpine belt equivalent to \~17 highway crossings, and with a 4.09 km band this hard-excludes the alpine rather than penalising it, with the effect concentrated south of \~51°N.

## 3. Nodes: patches, adjacency, complexes

Nodes for routing are refugia complexes: the connected components of the near-contiguous (D25) subgraph computed on the variant surface over the registered patch set. Patches remain the reporting unit inside a complex.

**Open item before the run:** the node set. This chat worked on 66 patches ≥ 500 km² (82% of 318,818 km² core); `v2_run001` ran 130 patches ≥ 250 km². Pin one threshold in the run record before anything is computed. The adjacency share and the 2.6 km median spacing are partly a consequence of it, so the choice is not cosmetic; if 250 km² is the registered value, say so and do not revisit it.

Stage order:

1. Compute D25 adjacency on the full patch graph (variant surface, D31 allowance, D17 counterfactual width) exactly as in v2. No path-length cap, no wolverine allowance, no "short link" class.
2. Take connected components of the adjacency subgraph as complexes. Every complex is a node, including single-patch complexes; isolated patches are stepping stones for a species with 100–300 km dispersal and MST plus augmentation decides whether they matter, not a size floor.
3. Contract: one node per complex; inter-complex candidate links are routed between the complex polygons (dissolved patch union), not between representative patches, so the LCP can leave any patch of the source complex and enter any patch of the target.
4. Record per complex: constituent patch ids, area, protected-area coverage (existing PAs; proposed IPCAs separately), mean gHM, and the within-complex sliver table (section 5).

Complexes are defined on the variant surface only. On the as-published baseline the terrain walls would split them; the baseline comparison (section 6) holds complexes fixed and compares centrelines between the same complex pairs.

Sanity check before contraction is accepted: a visual pass over the complexes. A complex that splits where a wolverine biologist would call one range indicates the D25 rule is slightly tight for a wide-front pair; that is the only case in which the allowance deserves a look, and it is recorded rather than acted on in v3.

## 4. Network on the contracted graph

MST, near-minimum augmentation (β = 2.5), no-affordable-alternative (D7), width tests (D17, D24, D26, D28), link classes (D23) and tiers (D30) all run unchanged on the contracted graph. The northern package contracted cliques for centrality only; v3 contracts for the whole graph because D25 fires on three quarters of the raw edges and leaves the raw topology meaningless.

Expected consequences, to be reported as they land rather than assumed:

- Node count drops from 130 (or 66) to the number of complexes; link count drops to the inter-complex links, the 40 corridor links of v2 being the upper bound.
- D7 no-affordable-alternative becomes meaningful: in v2, 43 of 47 were slivers with no alternative because no other node lay between them. The four corridor-level irreplaceables are the expected list.
- Per-edge centrality is computed once, on the contracted graph, with no intra-complex edges; bridge-backup redundancy is assessed between ecosystems.
- D25 can still fire between two complexes with wide facing fronts; if it does, the pair is merged and the merge is logged (a second-pass contraction, same rule).
- Route-branch decomposition (D26, relative floor) applies to corridor links only; near-contiguous edges get no decomposition, as in v2.

The class truth table keeps its eight cells. An empty top class ("only viable connection") is reported as measured: no link is at once isolated, single-route and narrow. Bob Marshall ↔ Mission Mountains (two branches under the relative floor, median width ratio 0.31, tenth-percentile 0.05) is reported as "last affordable" with its p10 ratio alongside and flagged as the G21 boundary case; the decomposition is not reopened to change its class.

## 5. Two-layer product

The product is two layers with equal standing. The northern package's premise (nodes are secured; the analysis finds what is between them) does not transfer, so a corridor into an unsecured complex is a different recommendation from one between two park-dominated complexes, and the report says which is which.

**Layer A — refugia complexes.** One row per complex: patches, area (km²), share in existing PAs, share added by proposed IPCAs, mean gHM, number of within-complex slivers, number of slivers containing a cost-100 or cost-1000 feature, act. The within-complex sliver table sits behind it: one row per near-contiguous edge inside the complex — the two patches, path length, cost-class composition of the spanning band, any road class or settlement present. Slivers that are all cost 1 need one line; slivers with a road are the within-complex pinch points and are listed, not mapped. No corridor polygons are drawn inside a complex.

**Layer B — inter-complex corridors.** The corridor links from section 4 with their class, D29 alternative kind, median and tenth-percentile width ratio, branch count, band land (km², dissolved per link), share of band land outside PAs and IPCAs, W11 already-connected status, and the two complexes' protection shares from Layer A. The headline statistic is the count of corridor links whose band crosses unprotected land (37 of 40 in v2) and the corridor land outside PAs and IPCAs.

**What is not in the product.** Band land for near-contiguous edges (27,060 km² in v2) is inside the complexes and is not corridor land; it is not drawn, not summed into corridor land, and appears only as the complex area it belongs to.

## 6. Baseline comparison

The as-published surface is run once so the effect of the terrain assumption is measured, not assumed. The comparison is at LCP-centreline level between the same complex pairs (complexes fixed from the variant); corridor bands are not compared, because relative or absolute slack on a path that crosses several cost-1000 cells produces band widths set by barrier count rather than geometry and would confound the result.

Per inter-complex link, on both surfaces:

| Metric | Unit |
| --- | --- |
| Cumulative LCP cost | cost units |
| Path length | km |
| Share of path on cost 1000 | % |
| Number of cost-1000 cells crossed, by layer of origin | count |
| Road crossings by class; settled land traversed | count; km |
| Route displacement (Hausdorff distance and mean separation between the two centrelines) | km |
| Elevation profile: median and maximum along the path | m |

Report the two networks' route displacement distribution and the number of links whose as-published path is routed through settled land or across a highway that the variant path avoids. That single table is the evidence for the surface decision; the deck states the terrain rule's effect from it and nothing else.

## 7. Pre-registered hypotheses and decision rules

Written before the v3 run; each is confirmed or refuted in the run record, not adjusted.

| Id | Hypothesis | Decision rule |
| --- | --- | --- |
| H-W1 | Contraction reduces the network to between 10 and 30 complexes and the corridor links to at most the 40 of v2. | Outside that range: report it, do not change the rule; check the node threshold pin first. |
| H-W2 | The four v2 corridor-level irreplaceables (D7) survive contraction; no near-contiguous edge becomes irreplaceable. | A new irreplaceable that is not a v2 corridor link is examined for a merge artefact (second-pass D25). |
| H-W3 | Narrowing links concentrate south of \~51°N (11 of 15 in v2); the north has none. | Reported as measured; drives the act structure, not the reverse. |
| H-W4 | The majority of corridor links cross unprotected land (37 of 40 in v2) while most complex area south of 51°N is inside PAs. | Both numbers reported together on the same table. |
| H-W5 | As-published centrelines are displaced downhill and through settled land relative to the variant on most southern links; northern links move little. | Measured by section 6; no threshold. |
| H-W6 | Glacier cost at 10 or 1000 displaces no inter-complex centreline by more than one cell width. | If any link moves further, it is listed and the glacier decision is escalated to the expert check (section 10). |
| H-W7 | The top class (isolated ∧ single-route ∧ narrow) remains empty. | Reported as measured; a non-empty result is not evidence for or against the rules. |

The tuning prohibition applies to D25, D31, β, the width-test floors and the tier breaks. A result that looks wrong is a finding to report, or a bug to fix in code, never a constant to move.

## 8. Reporting

**Acts.** Re-cut after contraction. Keep three latitude acts (58.5 / 51 °N) only if the central act carries a message of its own; at 2/4/7 in v2 it read as a transition zone, and two acts is the default. Before choosing, check which act the Banff–Yoho links fall in: the 51°N break sits about 20 km south of the Trans-Canada at Banff, and that corridor is the best-documented wolverine fragmentation in the region, so it must not straddle a presentation seam. Move the break to the Bow Valley if it does, and register the reason.

**Map.** Complexes draw as merged outlines with protection shading; no interior bands. Corridor links draw by class with the tenth-percentile pinch marked on each. Near-contiguous bands are not drawn; the count of within-complex slivers and the number containing a road appear in each complex's label or the legend. Refugia nodes are named as refugia, not as the nearest PA — "Refugium (Sustut)", not "Sustut Park" — so a reader cannot take a node for protected land. Rename in `node_names.csv`; the six Nááts'Ihch'Oh variants collapse under one complex.

**Accounting.** Corridor land is a dissolved union (52,572 km² in v2). Per-class band land is reported as a dissolved union per class, or the column is labelled as per-link sums; in v2 the per-class sums (42,312 km² corridor + 27,060 km² near-contiguous) exceeded the union by 16,800 km² and would have been added by a reader. Branch counts are reported as links with n branches, so the total reconciles.

**Numbers the deck leads with.** Number of complexes and share of complex area protected, by act; number of corridor links and share crossing unprotected land; corridor land outside PAs and IPCAs; narrowing links by act; the four last-affordable links by name with their p10 width ratio; the section 6 displacement table.

## 9. Validation checks before any number is read

- [ ] Run record on a clean tree (v2 was `9003dfd, dirty`); node threshold, D31 allowance, β, floors and tier breaks pinned in the record before notebook 03 runs.
- [ ] Variant surface: cost-1000 area by layer of origin reconciles with the as-published surface minus the three withheld layers; no cell in the variant has a lower cost than the maximum of its remaining layers.
- [ ] RGI 7.0 vs CanVec ice area difference computed once and recorded.
- [ ] Contraction: every patch belongs to exactly one complex; complex areas sum to the patch total; no inter-complex link starts or ends inside a complex polygon.
- [ ] D25 second pass: list of complex pairs merged after contraction (expected zero or few).
- [ ] Band land: corridor-land union equals the dissolved union of per-link bands; per-class sums labelled or dissolved.
- [ ] Branch arithmetic reconciles: sum over links of branches equals the reported branch total.
- [ ] Link names checked against node ids after the two-digit label parse fix (M6.7); T1–T4 regenerated.
- [ ] Act assignment: Banff–Yoho links and the Bow Valley crossing fall in one act.
- [ ] Section 6 table: both surfaces routed between identical complex pairs; displacement metrics computed on centrelines, not bands.
- [ ] Glacier sensitivities: displacement per link at cost 10 and 1000 recorded (H-W6).
- [ ] Every statistic in the report traced to a file in the run record before it is written into the deck.

## 10. Deviation register additions and parked items

New entries (numbering to follow the register; the northern package's D numbers are inherited unchanged unless listed):

| Id | Deviation | Reason |
| --- | --- | --- |
| D-W1 | Resistance surface: O'Brien 2025 with the three generic terrain rules withheld (section 2); as-published run once as baseline. | The rules are expert assignments for generic non-volant fauna that invert wolverine habitat use; ordinal 1000 on areal classes hard-excludes the alpine. |
| D-W2 | Glacier layer from RGI 7.0 on both sides of the border, not CanVec. | Seamless transboundary coverage; CanVec stops at 49°N. |
| D-W3 | Nodes contracted into complexes (connected components of D25) for the whole graph, not centrality only. | D25 fires on 76% of raw edges; raw topology, D7 and centrality are density artefacts. |
| D-W4 | Two-layer product with complex protection coverage reported alongside corridors. | Refugia are unprotected by definition; the northern premise that nodes are secured does not hold. |
| D-W5 | Baseline comparison at LCP-centreline level between fixed complex pairs; bands not compared. | Slack on walled paths sets band width by barrier count and confounds the comparison. |
| D-W6 | Near-contiguous bands not drawn and not counted as corridor land. | They are interior to complexes. |
| D-W7 | Node naming as refugia, not as nearest PA. | Prevents reading nodes as protected land. |
| D31 (note) | Allowance inherited at 4.09 km; no wolverine-specific allowance derived. | No evidence to derive one from; any movement-based value would merge the network; the calibration clause is recorded as not exercised. |

Parked, not blocking the draft:

- Expert check on glacier and large-lake treatment, framed narrowly (does a dispersing wolverine treat icefields and frozen lakes as passable), not as a re-weighting.
- Doctrine sign-off on running a corridor product on a modified published surface.
- Audit against the Day et al. 2024 wolverine genetic-connectivity surface: do variant corridors fall in its high-connectivity zones and baseline corridors not. Audit-only, as Carroll 2018 and Pither current density were retired to under D1–D3.
- Whether the within-complex sliver table is worth a small map inset for the few complexes with an interior highway.
