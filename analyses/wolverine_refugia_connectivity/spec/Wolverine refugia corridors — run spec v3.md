# Wolverine refugia corridors — run spec v3

Sep 28, 2026 · @Ethan

## 1. Purpose and what changed

This deliverable is **v2 at node level with the updated corridor-pressure rules**: the wolverine refugia network run and classed exactly as the northern IPCA corridors package as amended on 2026-09-29 — every non-touching link is a corridor on one pressure scale; near-contiguous links (fronts) are classed with width as the route sense rather than dismissed as "adjacent — no corridor needed". The complexes work of 2026-09-28/29 (contraction of near-contiguous patches into ecosystem-level nodes, routing between complex unions, the `v25_run00x` runs) is **parked for v3** (section 10) and does not appear in this product.

Three things differ from the northern package; everything else is inherited.

1. The resistance surface is the withheld-terrain variant (section 2).
2. Nodes are unprotected by definition, so node protection coverage is reported beside the links (section 5).
3. The as-published surface is compared at LCP-centreline level only (section 6).

Nothing is tuned. The allowance (D31, 13.6229 cost units = 4.09 km of extra travel on open ground) and the width-test floors are inherited and untouched.

## 1a. The deliverable due 2026-09-29 — from `v2_run001`, no new routing

The network is `v2_run001` as routed (130 nodes, 170 links). The `v25_run00x` complex-level runs are set aside and not reported. One post-processing notebook over the v2 outputs:

1. Front classes: every near-contiguous link gets its D23 class from the existing columns — edge sense (D7), width ratio (D17) as the whole route sense, and `lcp_max_cost`; a front is cut when its band width ratio against the barrier-free width (D17) is below the squeeze threshold — width only, per the northern D25c; path cost never drives the class. \`crossing\_class\` (maximum cost class on the least-cost path) is reported for every link and stated in profiles, as in the north. No branch decomposition on fronts. Strip classes are unchanged.
2. Link kind column: `front` / `strip`; and an `inter_cluster` flag = the two ends fall in different connected components of the front subgraph. The flag is a filter for "the long links", not a node definition.
3. Coverage columns, per node and per link's dissolved band: share in existing PAs; incremental share from proposed IPCAs; share in the prioritizr core (BALANCED, guarded frequent tier); share outside all three; one row of area expectation over the Y2Y frame.
4. Accounting: corridor land as a dissolved union; per-class band land dissolved; front area on its own line (D25b identity: strips + fronts + augmentation = total band area); branches as links with n branches.
5. Names: nodes named as refugia ("Refugium (Sustut)"), never as the PA; T1–T4 regenerated after the M6.7 fix.
6. Act check: Banff–Yoho links and the Bow Valley crossing in one act.

`05` outputs: nodes with protection shading; links by class, strips at full weight, fronts as bands in class colour with open fronts as a light tint; p10 pinch marked on strips.

Report text states the surface decision in one paragraph; states once that front edge sense is patch-pairwise (a front is "only link" between its two patches, not between ecosystems); lists the baseline comparison and glacier sensitivities as next steps.

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

## 3. Nodes

Nodes are the registered core-refugia patches; no contraction.

**Open item before the run:** the node set. This chat worked on 66 patches ≥ 500 km² (82% of 318,818 km² core); `v2_run001` ran 130 patches ≥ 250 km². Pin one threshold in the run record before anything is computed. The adjacency share and the 2.6 km median spacing are partly a consequence of it, so the choice is not cosmetic; if 250 km² is the registered value, say so and do not revisit it.

Each node carries: area, share in existing PAs, incremental share from proposed IPCAs, share in the prioritizr core, mean gHM, act, and the count of its links by kind (front / strip) and class.

Zero-cost adjacency (touching patches, northern §7) is unchanged and is not a link.

## 4. Network

MST, near-minimum augmentation (β = 2.5), no-affordable-alternative (D7), width tests (D17, D24, D26, D28), link classes (D23), tiers (D30) and current-flow centrality run on the node graph exactly as in the north.

Classification follows the northern reframe of 2026-09-29:

- **Strips** (path not shorter than the barrier-free width): D23 as written — edge sense × branch count × width.
- **Fronts** (near-contiguous, D25 trigger): D23 with width as the whole route sense; no branch decomposition. Open front with alternatives → corridor land with options; open front as only link → last affordable (alternative kind "far"); cut front (width ratio below squeeze, D25c — path cost is not a class driver) with alternatives → already narrowing; cut front as only link → only viable connection. A feature every route must cross raises every route's cost equally and is carried by link cost, D29 alternative kind and \`crossing\_class\`, the same treatment strips get; a feature running along the gap narrows the front and the width ratio catches it.
- The `inter_cluster` flag (section 1a) is a reporting filter; it does not change routing, classes or centrality.

Known consequence, reported not suppressed: D7 on fronts is patch-pairwise, so a front between two neighbours with no third patch between them is "only link" for that pair (43 of 133 fronts in v2). The report states this once. The ecosystem-level reading of D7 (bridge of a complex) is parked with the complexes (section 10).

An empty top class among strips is reported as measured. Bob Marshall ↔ Mission Mountains (Swan Valley; two branches under the relative floor, median width ratio 0.31, p10 0.05) is reported as "last affordable" with its p10 ratio alongside and flagged as the G21 boundary case; the decomposition is not reopened.

## 5. Product

One network, two tables, one map.

**Nodes table.** One row per refugia patch with the section 3 columns. The northern premise (nodes are secured; the analysis finds what is between them) does not hold here, so protection coverage of the nodes is reported with the same standing as the links, and the text says which linkages run into unsecured refugia.

**Links table.** One row per link: kind (front / strip), `inter_cluster`, class, D29 alternative kind, median and p10 width ratio, branch count (strips only), `lcp_max_cost`, band land (km², dissolved per link), share of band land outside PAs and IPCAs, W11 already-connected status, act.

**Headline statistics.** Links by kind and class, by act; strips whose band crosses unprotected land (37 of 40 in v2) and corridor land outside PAs, IPCAs and core; fronts by class with front area on its own line; narrowing links by act; the four last-affordable strips by name with p10 width ratio.

Nothing unprotected is taken as given: fronts are corridors with room, and a cut front carries more pressure than an open one, on the same table as strips.

## 6. Baseline comparison

The as-published surface is run once so the effect of the terrain assumption is measured, not assumed. The comparison is at LCP-centreline level over the v2 link set (same node pairs on both surfaces); corridor bands are not compared, because slack on a path that crosses several cost-1000 cells produces band widths set by barrier count rather than geometry and would confound the result.

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
| H-W1 | Fronts are the majority of links (76% in v2) and open fronts the majority of fronts; the network is mostly contiguous mountain blocks with a minority of strips. | Reported as measured; drives the narrative, not the rules. |
| H-W2 | The four last-affordable strips of v2 keep their class; the top class among strips stays empty. | A non-empty top class is not evidence for or against the rules. |
| H-W3 | Narrowing strips concentrate south of \~51°N (11 of 15 in v2); the north has none. | Reported as measured; drives the act structure, not the reverse. |
| H-W4 | Most strips cross unprotected land (37 of 40 in v2) while most node area south of 51°N is inside PAs. | Both numbers on one table. |
| H-W5 | As-published centrelines are displaced downhill and through settled land on most southern links; northern links move little. | Measured by section 6; no threshold. |
| H-W6 | Glacier cost at 10 or 1000 displaces no centreline by more than one cell width. | Otherwise list the link and escalate the glacier decision to the expert check. |
| H-W7 | Front classes driven by D7 (last affordable, only viable) cluster in dense, elongated groups of patches. | Reported; motivates the parked ecosystem-level D7 reading. |

The tuning prohibition applies to D25, D31, β, the width-test floors and the tier breaks. A result that looks wrong is a finding to report, or a bug to fix in code, never a constant to move.

## 8. Reporting

**Acts.** Keep three latitude acts (58.5 / 51 °N) only if the central act carries a message of its own; two acts is the default. Check which act the Banff–Yoho links fall in: the 51°N break sits about 20 km south of the Trans-Canada at Banff, and that corridor must not straddle a presentation seam. Move the break to the Bow Valley if it does and register the reason.

**Map.** Nodes with protection shading. Links by class on one scale: strips at full weight with the p10 pinch marked; fronts as bands in class colour, open fronts as the light "options" tint, cut fronts with an outline. `inter_cluster` strips may be emphasised in a second figure; they are not a separate class. Nodes named as refugia, not as the nearest PA — "Refugium (Sustut)" — so a reader cannot take a node for protected land; rename in `node_names.csv`.

**Accounting.** Corridor land is a dissolved union (52,572 km² in v2); per-class band land is a dissolved union per class, or the column is labelled as per-link sums (in v2 the per-class sums exceeded the union by 16,800 km²). Front area is its own line. Branch counts are reported as links with n branches.

**Numbers the deck leads with.** Links by kind and class, by act; node area protected, by act; strips crossing unprotected land; corridor land outside PAs, IPCAs and core; the four last-affordable strips by name with p10 width ratio; the section 6 displacement table when run.

## 9. Validation checks before any number is read

- [ ] Run record on a clean tree (v2 was `9003dfd, dirty`); node threshold, D31 allowance, β, floors and tier breaks pinned before any class count is read.
- [ ] Variant surface: cost-1000 area by layer of origin reconciles with the as-published surface minus the three withheld layers; no cell has a lower cost than the maximum of its remaining layers.
- [ ] RGI 7.0 vs CanVec ice area difference computed once and recorded.
- [ ] Front check (G23 ordering): every front passes the D24 floor; every front has a non-null width ratio and `lcp_max_cost`; front class counts sum to the front count.
- [ ] Area identity: strips + fronts + augmentation = total band area; corridor-land union equals the dissolved union of per-link bands; per-class sums labelled or dissolved.
- [ ] Branch arithmetic reconciles.
- [ ] Link names checked against node ids after the two-digit label parse fix (M6.7); T1–T4 regenerated.
- [ ] Act assignment: Banff–Yoho links and the Bow Valley crossing in one act.
- [ ] Section 6 table (when run): both surfaces routed between identical node pairs; displacement on centrelines, not bands.
- [ ] Glacier sensitivities (when run): displacement per link at cost 10 and 1000 recorded (H-W6).
- [ ] Every statistic in the report traced to a file in the run record before it is written into the deck.

## 10. Deviation register additions and parked items

New entries (numbering to follow the register; the northern package's D numbers are inherited unchanged unless listed):

| Id | Deviation | Reason |
| --- | --- | --- |
| D-W1 | Resistance surface: O'Brien 2025 with the three generic terrain rules withheld (section 2); as-published run once as baseline. | The rules are expert assignments for generic non-volant fauna that invert wolverine habitat use; ordinal 1000 on areal classes hard-excludes the alpine. |
| D-W2 | Glacier layer from RGI 7.0 on both sides of the border, not CanVec. | Seamless transboundary coverage; CanVec stops at 49°N. |
| D-W3 | Node protection coverage (PAs, IPCAs, prioritizr core) reported with the same standing as the links. | Refugia are unprotected by definition; the northern premise that nodes are secured does not hold. |
| D-W4 | Baseline comparison at LCP-centreline level over the v2 link set; bands not compared. | Slack on walled paths sets band width by barrier count and confounds the comparison. |
| D-W5 | Node naming as refugia, not as nearest PA. | Prevents reading nodes as protected land. |
| D31 (note) | Allowance inherited at 4.09 km; no wolverine-specific allowance derived. | No evidence to derive one from; any movement-based value would merge the network; the calibration clause is recorded as not exercised. |

**Parked for v3 (2026-09-29):** contraction of near-contiguous patches into complexes (components of the front subgraph), routing between complex unions, ecosystem-level D7 and centrality on the contracted graph, and the interior D7 reading (bridge of a complex) — the `v25_run00x` runs. Once fronts are corridors on the same pressure scale, the node-level network is the northern method as written; complexes add a second level of semantics whose value is meaningful ecosystem-scale irreplaceability, to be assessed when there is time to do it properly.

Parked, not blocking the draft:

- Expert check on glacier and large-lake treatment, framed narrowly (does a dispersing wolverine treat icefields and frozen lakes as passable), not as a re-weighting.
- Doctrine sign-off on running a corridor product on a modified published surface.
- Audit against the Day et al. 2024 wolverine genetic-connectivity surface: do variant corridors fall in its high-connectivity zones and baseline corridors not. Audit-only, as Carroll 2018 and Pither current density were retired to under D1–D3.
- Whether the within-complex sliver table is worth a small map inset for the few complexes with an interior highway.
