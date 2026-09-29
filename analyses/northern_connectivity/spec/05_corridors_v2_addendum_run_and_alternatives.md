# 05 corridors (north) — v2 addendum: production run, near-optimality surface, route-branch alternatives

> Addendum to `docs/05_methods_v2.md`. Surgical: nothing in D1–D10 or A1–A4 is reopened.
> Adds D11–D21 (D18/D20 deferred), Phases 4b/4c (4e deferred), gates G9–G17, and the run sequence. Written 2026-08-21.
> Claude Code: patch `docs/05_methods_v2.md` with the new sections and append to its changelog;
> do not rewrite the existing document.

**Status:** approved in design discussion 2026-08-21. Implemented 2026-08-21; NB01+H7 done
2026-08-26; NB02 baseline done 2026-08-27 (`v2_run002`); NB03/NB04 done 2026-08-27; 05_results figures incl. the draft regime map as of 2026-08-31. **Subordinate build spec for the director package: `06_corridors_north_director_package_spec.md` (v1.1) — consumes this addendum's artifacts; presentation decisions live there, methods decisions here, ambiguous items logged in both.** 2026-09-11: Linkage Mapper comparison added — D19 (centrality) active, D18/D20 deferred; see changelog.

> **Living paper documents (BINDING maintenance rule):** `spec/methods_log.md` and
> `spec/results_log.md` are the cumulative methods and results registers for the publication.
> Any session that changes data, formulation, parameters, or a QA rule — or lands/changes a
> quantitative result — updates the corresponding log IN THAT SAME SESSION. Supersede, never
> delete. Same convention as the y2y flagship's spec/ logs.

**Changelog**
- 2026-09-29 — **fronts are corridor land (D25c).** The "adjacent — no corridor needed" framing (D25, D25a) made a land
  claim the analysis cannot support and is retired. **Principle (Ethan, binding): nothing that is not protected is taken as
  given.** The front trigger is kept as a geometry descriptor (`link_geometry` ∈ {strip, front, contact}); every strip and
  front is classed on the single pressure scale of the land-aware rule (D23), with the route sense reduced to width alone on
  fronts (no branches to count on a one-component front). Perpendicular road crossings are flagged (`road_crossing`), not
  classed (consistent with strips). Corridor area includes fronts again; front share is a descriptor (D25b amended). Example
  rules: contacts excluded from candidacy; northern slots by room (width), not branch count; the two-branch link kept as a
  separate "two routes" example. Pre-D23 run002 products frozen where they still exist (see spec 06 changelog). Gate G24 (G23
  retired). M4.12; R10. Applied from `05_patch_D25c_fronts_as_corridors.md`.
- 2026-09-28 — **geometry-vs-ecology audit for run003 (D26–D31).** Rules whose result was driven by link length, node
  position, or raster resolution rather than land: (D26) the branch-sliver floor becomes relative to band area; (D27)
  locked intra-name links are ineligible for the irreplaceable classes until the alternative-link test (D7) is run against
  the full candidate set; (D28) a tenth-percentile width ratio joins the median so a single pinch is visible in the
  table; (D29) the alternative link's cost is decomposed into length and mean resistance; (D30) near-optimality tiers use
  fixed cost-unit breaks instead of area-weighted percentiles; (D31) the calibrated cutoff is also stated as detour
  distance on open ground, which is the calibration rule for derived analyses. Example selection in 06 changed to
  class-and-width-first with criticality as tie-break. Gates G20–G22. Zero-cost adjacency vector check declined (patch
  §7). M4.10; R10. Applied from `05_patch_D26_D31_geometry_audit.md` (kept in spec/ as the record). **Adopted 2026-09-28
  BEFORE D23–D25 landed** (the patch says apply after them): D23's land-aware top class is still the proposal logged under
  D22/M4.8 (the 'both' class stands in for it in §2 of spec 06); D24's resolution floor is a hook (`assessable` = every
  eligible edge in D28's G22); D25 is not referenced by any implemented rule. **SUPERSEDED the same day:** D23–D25 landed
  and were spliced (below); the stand-ins are gone — the top class in the example rule is D23's, and D28's assessable set is
  D24's.
- 2026-09-28 — **near-contiguous sub-classes (D25a) and area accounting (D25b).** Run002 classed 18 of 45 non-zero-cost
  links near-contiguous under the D25 trigger. The count is correct: between two large facing areas the barrier-free
  near-optimal set is a front spanning the facing perimeters, not an ellipse, so its median width exceeds the gap by a wide
  margin. Two defects in D25 as written are fixed. (D25a) The barrier variant keyed on cost-1000 only; roads and cuts are
  cost 10 in this surface, so a highway along the gap did not register. Sub-classes are now decided by the actual band's
  width ratio (D17, assessable because the front is wide) and the maximum cost class on the least-cost path. (D25b)
  Near-contiguous band area is reported separately from corridor area; the calibrated cutoff (D6) is **not** recalibrated.
  Gate G23. Northern example slots N2–N3 re-checked against the pin rule. M4.11; R10. Applied from
  `05_patch_D25a_near_contiguous.md` (a provisional build of the same rules preceded it the same day, M4.9 addendum).
  Implementation note: the WIDTH floor (D24) precedes the trigger (G23 ordering); the LENGTH floor applies only off fronts —
  a short gap between facing areas is the near-contiguous case itself.
- 2026-09-28 — **short-link rules (D24, D25).** Raised by the wolverine refugia network (133 of 170 links one-branch at
  half cutoff) but baked into the northern engine because the failure is geometric, not network-specific. (D24) the width
  test (D17) is declared *not assessable* below a resolution floor in cells; such links are classed from the edge sense (D7)
  alone and flagged in the tables. (D25) links whose least-cost path is shorter than their barrier-free width are a
  **near-contiguous** class — no corridor to design unless a barrier intervenes — classed by the edge sense and the
  barrier-crossing flag only. Precedence table (§6) extended to eleven rows. Gate on the floor's effect (G19). Both constants
  pre-registered; tuning them to a class count is prohibited (§2). M4.9; R10. Applied from `05_patch_D24_D25_short_links.md`.
  **Implementation note:** the counterfactual step (D17) now runs BEFORE the branch decomposition in notebook 04 (it measures
  the barrier-free width that decides both rules); `route_branches` refuses to run without it.
- 2026-09-28 — **land-aware top class (D23).** "Only viable connection" now requires all three: no alternative link (D7),
  one route branch (D12), and band width below its barrier-free width (D17, ratio < `squeeze_ratio`). The route sense (D12)
  is **redefined** to include the width condition, so a single wide branch is no longer called route-irreplaceable anywhere.
  One threshold only: the existing `squeeze_ratio` (0.5). Full eight-cell precedence table added (§6). Adoption gated on the
  run002 eight-cell count table (G18): **measured on run002 — only Gwillim Lake ↔ Pine Le Moray (0.41) sits in the
  (E, B1, S) cell; Tatonduk ↔ Fishing Branch (1.00), Wilps Gwininitxw ↔ Swan Lake (0.96) and Wędzih Yiné' ↔ Chase (0.99) do
  not, so the 06 example-regeneration rule FIRES and the change is a post-pin class change** (R10). Raised by the part-3
  bridge case; adopted on the general argument (a leaf's only tree edge is its cheapest edge by the cut property, so the edge
  flag measures isolation, not land; one wide lens is one branch, so the branch flag measures topology, not land). M4.8; R10.
  Applied from `05_patch_D23_only_viable.md`.
- 2026-09-28 — **D22: within-name part links COMPETE** (Ethan; supersedes D16's rule-4 default for every
  `link_locked` name — Dene Kʼéh Kusān, Liard River Corridor, Nahanni, Nááts'ihch'oh → `link_competing`; Tombstone
  stays `merge_parts`). Trigger: Dene Kʼéh Kusān's 80 km² third part read as orphaned on the deck maps while the
  network held a locked, unclassified, unprioritised 695 km² band to it. Re-sign H7 → new run (`v2_run003`).
  `calibrate_cutoff` keeps D16's "inter-name MST only" rule by dropping within-name part edges from the
  calibration set. **D23 (PROPOSED, for the chat):** 'only viable connection' should require land scarcity, not
  graph topology alone — edge-irreplaceable ∧ one branch ∧ D17 width ratio < θ (0.5 or 0.75); a leaf across intact
  land would otherwise read as irreplaceable by construction. methods_log M4.8.
- 2026-09-11 — **D21: Linkage Mapper–style adjacency graph computed as a diagnostic
  universe beside the backbone.** Cost-allocation neighbour graph on the part-level CWD
  fields, contracted to names; per-name degree (`n_neighbours`), adjacency status of every
  backbone/backup edge, gate G17 (MST ⊆ adjacency), one appendix map. **No change to bands,
  classes, `linkage_priority.tif`, the 58-link network, or the pinned examples.** A D7
  amendment (restrict backup candidates to adjacency edges) is logged as a follow-up decision
  contingent on the measured count of non-adjacent backups (§7). M5.19. Applied from `05_patch_D21_adjacency.md` (kept in spec/ as the record).
- 2026-09-11 (merge note) — the chat-regenerated copy of this spec (saved as
  `scratchpad/spec_merge/05_chat_20260911.md` for the session) again dropped §8/§9, the
  living-docs binding block, the D17-confirmed / G13-final text, `squeeze_cf_min_cost`, the
  as-implemented §5 output names and the 2026-08-27 → 2026-09-08 changelog; restored from git
  HEAD and the chat's additions (D18–D20, G14–G16, constants, §6/§7 lines, the deferred step
  4e spec as §10) spliced in. **D19's premise was wrong:** the engine has computed edge
  CURRENT-FLOW betweenness on the quotient graph since the v2 rebuild (`corridor_graph.
  centrality`, 2026-08-07; column `ecfb_raw`), never shortest-path betweenness. D19 is
  therefore implemented as: the method is PINNED by a config key (`centrality`), the
  shortest-path measure is added as the comparison column `centrality_sp` beside
  `centrality_cf`, `centrality_compare.csv` is written and gate G15 asserts the tree-case
  identity. `linkage_priority.tif` and every product are UNCHANGED by D19. M5.18.
- 2026-09-11 (later) — scope narrowed: **only D19 (current-flow centrality) is active now.**
  D18 (LM validation, G14, H9) and D20 (pinch beside squeeze, step 4e, G16, H10) are
  **deferred** to a future comparison and marked as such below; their specs are kept intact
  so they can be switched on without redesign. Nothing in the run sequence calls them.
- 2026-09-11 — Linkage Mapper comparison (McRae & Kavanagh 2011 is the method precedent; v2 is a
  Linkage Pathways–equivalent corridor model on a published surface). Three additions: D18
  external validation against Linkage Pathways (G14, H9); D19 centrality switched to
  current-flow betweenness (G15; quotient-graph betweenness retained as a comparison column);
  D20 Pinchpoint-style within-band circuit solve added as a Phase 6 diagnostic that sits
  **beside** D17, with an explicit comparison product (step 4e); implemented natively in
  scipy (Linkage Mapper's Pinchpoint tool is bound to unmaintained Circuitscape 4; Circuitscape
  5 is Julia) and cross-checked once against Circuitscape 5 (G16, H10). Linkage Priority (weighted
  blend) explicitly not adopted — D5 stands.
- 2026-09-08 — D17 ratio restated as WIDTH (area ÷ own route length) after the first real
  execution falsified the area inequality (G13 fired on 6 links: the counterfactual shortens
  detouring routes); a second execution then showed narrower counterfactuals WITHOUT shorter
  routes (Wədzih↔Finlay Russel, Liard↔Nahanni, Nahanni internal) — real-surface near-ties
  broken by relaxation — so G13 is now the relaxation invariant on the OPTIMUM
  (`lcp_cf ≤ lcp_real`), with narrower cases reported. Counterfactual CWD set cached.
- 2026-09-03 — **D17 CONFIRMED / H8 CLOSED** (counterfactual band-area ratio, Ethan's
  call over the analytic index), `squeeze_cf_min_cost` constant, G13 restated for the
  implemented definition, §5 output names as implemented, §9 gains notebook-04 step 2b and
  the 06 director-package notebook.
- 2026-09-03 (merge note) — the chat-regenerated copy of this spec dropped §8 (file
  structure), §9 (notebook breakdown + clarifications), the living-docs binding block and
  the 2026-08-21/27 changelog entries; restored from git HEAD and the chat's additions
  (D17 stub, `squeeze_ratio`, G13, H8, §5/§6 rules, 06 cross-reference) spliced in.
  NOTE the source-artifact pointer in 06 (`v2_run001`) is stale: the production run is
  `v2_run002` (run001 was an aborted first pass, deleted 2026-08-27).
- 2026-09-03 — cross-reference to `06_corridors_north_director_package_spec.md` added. D17
  stub: the "squeezed" link class (band width < `squeeze_ratio` × open-ground width) appears
  in the draft regime map and in 06's legend but had no methods definition here; definition,
  constant, and gate G13 added pending confirmation against what the engine actually
  computed (H8). Logged in both documents.
- 2026-08-21 — addendum: execute the v2 production run; define the wall-to-wall near-optimality
  surface; define route-branch alternatives and the per-branch values table (same column spec
  as the Y2Y-wide alternatives table); Carroll 2018 enters as an audit column only; Phase 7
  deferred pending baseline evidence.
- 2026-08-21 — D16: multipart named areas split into parts and routed internally (locked
  intra-name MST); G0 re-baselined at name level + part count; H7 review gate added.
- 2026-08-21 — §8 file structure (`analyses/northern_connectivity/`; engines stay at repo root;
  H7 artifacts git-tracked in `audit/audit_objects/`) + §9 four-notebook run breakdown; §3
  preamble amended accordingly; three clarifications queued for the methods-doc patch (multipart
  field semantics, intra-name branches, tier domain).
- 2026-08-27 — **living paper docs created**: `spec/methods_log.md` (M-entries: decisions,
  data manipulations, fixes — incl. the adjacency-band abs-mode fix M4.3 and the richness
  stretch-domain fix M6.2) + `spec/results_log.md` (R-entries: gates, step-0a review outcome,
  calibration 13.62 → 18,150 km², baseline network, 7 irreplaceable links). Binding same-session
  maintenance rule added above.

---

## 0. Scope of this addendum

Three asks, mapped onto what the v2 engine actually produces:

1. **Run v2 end to end** — calibration → baseline → structured ensemble (axes B, C, D). Not yet
   executed; `cwd_cutoff_abs` is still `None`.
2. **Wall-to-wall "frequency" layer** → implemented as a **near-optimality surface** (raw slack,
   cost units). A least-cost model has no solution pool; the band *is* the closed-form
   near-optimal set and slack is its continuous degree. The ensemble member fraction is retained
   as **attribution only** and is never labelled "frequency" or "selection frequency".
3. **Cluster + alternatives table for all values** → clustering unit is the **route branch**
   (connected component of a per-edge band at a tightened cutoff), not a whole-network mask.
   One row per edge × branch; columns match the Y2Y-wide alternatives table, plus a Carroll
   2018 climate-corridor audit column.

Out of scope, unchanged: Phase 5 (no DEM, H5), ensemble axis A (H2), Phase 6 overlays beyond
the single audit column defined here, Phase 7 (see D14), Phase 8 ops package (H3). Eastern-slopes
grizzly work remains a separate unapproved plan.

---

## 1. New decisions (append to the decision log)

| # | Decision | Rationale |
|---|---|---|
| D11 | Primary wall-to-wall product is `near_optimality.tif` = `min_e slack_e` in **raw cost units**, defined on every routable cell. `linkage_priority.tif` (`max_e ecfb_e × (1 − slack_e/cutoff)`) is retained unchanged as the D9 deliverable. | Slack is defined everywhere the CWD fields are, which is what makes it wall-to-wall; raw units make the surface independent of `cwd_cutoff_abs`, which is calibrated for v1 area comparability, not for meaning. The cutoff enters only the binary band and area accounting. |
| D12 | The unit of "alternative" is the **route branch**: a connected component of an edge's band at a tightened cutoff `cutoff_branch = branch_mult × cwd_cutoff_abs`. Per edge, `n_branches = 1` ⇒ **route-irreplaceable** (no alternative routing within the link). This is distinct from, and reported alongside, the D7 β-ceiling **edge-irreplaceable** flag (no alternative link). | Band components are provably genuine i→j alternatives (see G9), so no heuristic clustering is needed. Whole-network clustering over ~49 structured members would cluster by which node was dropped — not a meaningful object. |
| D13 | The per-branch values table uses the **same column specification** as the Y2Y-wide alternatives table. Import the column spec from the existing table code; do not redefine names or normalisations here. Row unit differs (edge × branch vs solution cluster) and the caption must say so. | Side-by-side readability with the Y2Y-wide product without implying a shared estimand. |
| D14 | **Carroll 2018 (climate corridors) never enters resistance.** It is a post-hoc audit column (`carroll2018_pctl`) and the input to the Phase 8 tie-break among near-equivalent branches. **Phase 7 (velocity-modified routing) is deferred** pending the baseline + axis C results and is recorded as a claim-scope extension requiring its own justification. | Carroll 2018 is current-flow centrality — a derived flow quantity, same object type as Pither current density, rejected as a routing input by D1–D3 for circularity, pinch-point/permeability conflation, and footprint double-counting. The 05 claim scope is structural only; any climate term in resistance changes the claim. Caveats travel with the column: RCP 8.5 late-century only, shares anthropogenic signal with the cost surface. |
| D15 | Ensemble member fraction (cell in member's corridor union / members) is written as `ensemble_attribution.tif` and used for the robust-core threshold (0.9) and per-axis attribution rasters only. | ~42 of ~49 members are leave-one-out; the fraction is "share of dropped nodes that didn't matter," not a near-optimal sampling frequency. |
| D16 | **Multipart named areas are routed internally.** A named PA/IPCA whose rasterized mask has >1 8-connected component is split into **parts**; each part ≥ `part_min_km2` is its own seed/routing unit. For each multipart name, the MST over its parts (on CWD) is **locked into the backbone** before the inter-name MST is built. Parts < `part_min_km2` remain in `node_union` (area accounting) but are not seeds. Leave-one-out (axis C) drops a **name** (all parts), not a part. Calibration (`calibrate_cutoff`) uses the **inter-name MST only**; intra-name corridor area is reported separately, as augmentation area is. | Seeding all parts at CWD = 0 as one node means the model never asks how to move between them. A named area is a management unit, so connecting its parts is a defensible default — but it is an assertion about intent for multi-site designations, so the part list is reviewed by a human before the run (H7). Locked rather than competing so a part is never connected to its sibling only via a third park. |
| D17 (CONFIRMED 2026-09-03, H8 closed) | **Squeezed link class.** A non-adjacency edge is `squeezed` when `squeeze_ratio_obs = width_new_km / width_cf_km < squeeze_ratio` (0.5), where width = the band's NEW-land area (`& ~node_union`) divided by its OWN least-cost route length (the implementable analogue of the spec's cross-sectional width); the real band is at `cwd_cutoff_abs`, and the counterfactual band is the SAME edge banded at the SAME cutoff on a COUNTERFACTUAL surface with every cost class ≥ `squeeze_cf_min_cost` (10) set to 1 — 'how wide would the near-optimal set be if nothing constrained it'. One extra CWD set per seed part (cached `cwd_cache/<sha>_cf`), unit fields derived as in step 1. Reported per edge in `corridor_edges.csv` as `band_new_km2`, `band_cf_km2`, `centreline_cf_km`, `width_new_km`, `width_cf_km`, `squeeze_ratio_obs`, `squeezed`; counterfactual band polygons in `bands_counterfactual.gpkg` (the M3 natural-width outline). Class is **disjoint from** the two irreplaceability senses for presentation (irreplaceable takes precedence; the ratio stays in the table). The analytic ellipse index (`squeeze_idx`, methods_log M4.6) that produced the draft map is RETAINED as a screening diagnostic column only. | H8 outcome: the draft map used an analytic index (mean band width ÷ the straight-link open-ground ellipse width); the counterfactual replaces it because it needs no straight-link assumption, both bands share the study-window clipping (the boundary artefact cancels), and it yields a drawable natural width. WIDTH (area ÷ own route length) rather than raw area — measured 2026-09-08: raw area failed G13 on 6 links because relaxing barriers SHORTENS detouring routes, and area ∝ length × width; rather than median perpendicular width: equivalent for ribbons, no path-normal geometry. Implemented as `corridors_core.counterfactual_squeeze` (notebook 04 step 2b); synthetic-verified (a cost-1000 wall drives the ratio down monotonically; G13 holds). Measured count on `v2_run002` lands when notebook 04 re-runs. |
| D18 (DEFERRED — future comparison) | **External validation against Linkage Mapper.** v2's per-edge slack (`CWD_i + CWD_j − min_e`) is, term for term, Linkage Pathways' normalized least-cost corridor (McRae & Kavanagh 2011), and its calibrated band is the CWD-truncated corridor. Validate: run Linkage Pathways in ArcGIS Pro on `validation_pairs` (5 MST edges spanning short/long and open/constrained cases) with the identical O'Brien surface and node rasters; compare NLCC to our slack (Pearson r over the union of both corridors at matched cutoff; Jaccard of the truncated bands). Recorded as G14; performed once per resistance-surface hash. | Buys external credibility for the whole engine at the cost of an afternoon; the comparison is exact in principle, so disagreement is a bug, not a difference of opinion. Not a routing input; nothing changes in the pipeline on pass. |
| D19 | **Centrality = current-flow betweenness** on the backbone graph (locked intra-name + inter-name MST + β augmentation), edge weights = corridor cost (`min_e`), nodes = names (parts contracted). Implemented via `networkx.current_flow_betweenness_centrality` / `edge_current_flow_betweenness_centrality`. **As implemented (2026-09-11, M5.18): the engine has used exactly this measure since the v2 rebuild** (`corridor_graph.centrality`, conductance = 1/cost, zero-cost cliques contracted), so nothing in `linkage_priority.tif` changes; D19 PINS the method via the `centrality` config key, ADDS the shortest-path edge betweenness as the comparison column `centrality_sp` beside `centrality_cf`, writes `centrality_compare.csv` and asserts G15. | Linkage Mapper's Centrality Mapper standard: cores as nodes, linkages as resistors weighted by corridor cost, current flow summed over all pairs. Credits all paths, not only the shortest, so it behaves on a sparse augmented graph where shortest-path betweenness is brittle to a single cheap backup. Zero-cost adjacency edges are contracted as before (§7). |
| D20 (DEFERRED — future comparison) | **Pinch points sit beside D17, not instead of it.** Phase 6 diagnostic: a pairwise circuit solve (`i` source / `j` ground) run **inside each edge's band** on the O'Brien surface, giving within-band current density `pinch_e`. **Implemented natively**: graph Laplacian on band cells (8-neighbour, conductance = 1/mean resistance of the two cells, diagonal scaled by 1/√2), source cells fixed at unit potential and ground cells at zero, `scipy.sparse.linalg` solve, cell current = sum of |branch currents| / 2 — i.e. the Circuitscape pairwise formulation (McRae et al. 2008) without the Circuitscape runtime. Cross-checked against Circuitscape 5 on one band (G16). Per edge: `pinch_max_pctl`, `pinch_len_km` (contiguous run of cells ≥ p95 of within-band current), `pinch_loc` (fractional position along the path). Never a routing input; never a legend class in the director deck until the comparison in step 4e has been read. | Two different questions. D17 asks *is the near-optimal set geometrically narrower than it would be without barriers* (director-visible, map-legible). Pinch points ask *where within a corridor would area loss hurt most* (ops-package question, Linkage Mapper's Pinchpoint Mapper). They can disagree — a wide band with a single internal choke, or a uniformly narrow band with no choke — and the disagreement is itself informative. D3's rejection of current density applies to *routing on external circuit outputs*, not to a diagnostic run on our own bands with our own surface. Native implementation because Linkage Mapper's Pinchpoint tool still depends on Circuitscape 4 (unmaintained Python 2.7-era) and Circuitscape 5 is a Julia runtime — neither belongs as a hard dependency of a gated Python pipeline; bands are small enough that a sparse solve is seconds per edge. Circuitscape 5 is used once, for the cross-check only (H10). |
| D12 (amended 2026-09-28) | **Route-irreplaceable** = `n_branches == 1` **and** `squeeze_ratio_obs < squeeze_ratio`. The branch decomposition itself is unchanged; only the flag's definition changes. `route_irreplaceable_topo` (the old one-branch-only flag) is retained as a column for continuity with run001/run002 tables. | A single branch across a wide lens has no distinct alternative swath but abundant alternative land; calling it irreplaceable was a topology statement mistaken for a scarcity statement. With width folded in, the flag means "one route, and that route is already constrained," which is what a reader takes "no alternative route" to mean. |
| D23 | **Only viable connection** = edge-irreplaceable (D7) **and** route-irreplaceable as amended (D12: one branch and narrow). Equivalently: no alternative link, one branch, ratio < `squeeze_ratio`. No new constant. Precedence for every combination is fixed in §6 and is the single source for map classes, legend counts, and both alternatives tables (`classify_links` → `link_class`). | The two existing senses can both fire on the least constrained land in the sector (remote leaf, open ground). The counterfactual width (D17) is the only measure of movement-land scarcity in the pipeline, so it is the missing condition. Folding it into the route sense rather than adding a third clause keeps the two-sense framing in the reporting rules intact and makes the route flag meaningful on its own. |
| D24 | **Width-test resolution floor.** The squeeze test (D17) and therefore the amended route flag (D12) are evaluated only when `open_ground_width_med ≥ width_floor_cells` **and** `lcp_len_cells ≥ len_floor_cells` (`open_ground_width_med` = the counterfactual band's median cross-section in cells, from the D28 profiles). Otherwise `width_not_assessable = True`, `squeezed = False`, `route_irreplaceable = False`, and the link is classed from the edge sense (D7) alone (§6). The unassessable count and the affected links are reported in `corridor_edges.csv` and in the run report. | A ratio of two small integers at 300 m is rasterisation noise: three cells against six is 0.5 with one cell of margin. Without a floor the "already narrowing" class fills with short links for numerical reasons. Declaring the test unassessable is honest; declaring such links narrowing or only-viable is not. |
| D25 | **Near-contiguous link class.** A non-zero-cost edge with `lcp_len_cells < open_ground_width_med` (path shorter than the band's barrier-free width) is `near_contiguous`. It is not a corridor-design object: no branch decomposition, no width class. It is reported with the edge sense (D7) and `crosses_cost_1000` (a cost-1000 cell on the least-cost path; `path_max_cost` carries the barrier's class). Director class: **"adjacent — no corridor needed"** when no barrier intervenes; **"adjacent — barrier between"** when one does. Both are drawn as the link's band in a neutral hatch, never as one of the four corridor classes; counts appear in the legend. Zero-cost adjacency (§7) is unchanged and remains a separate, earlier rule. | When the gap between two areas is smaller than the natural width of the near-optimal set, the band is a blob, not a route; "branch" and "narrowing" describe nothing. The information that matters for such a pair is whether anything stands between them and whether the link is the only one. Nodes a few kilometres apart are the norm in refugia networks and occur in the north wherever proposals abut existing parks. |
| D25c | **Geometry descriptor, one pressure scale.** For every non-zero-cost edge set `link_geometry`: `contact` if `width_not_assessable` (D24 floor); `front` if `lcp_len_cells < open_ground_width_med` (the retired D25 trigger); `strip` otherwise. Then class **every strip and front** by the land-aware table (D23) with one substitution: on a `front`, the branch term B1 is **fixed true** (a front is one component by construction; `n_branches` is written null and the decomposition is skipped; `b1_forced` recorded), so the route sense is the width ratio alone. `contact` links are classed from the edge sense only, as before. `lcp_max_cost` is reported for every link and drives a `road_crossing` flag (`== 10`) used in tables and profiles, **never in the class**. | The near-contiguous class removed unprotected land from the corridor framework on the strength of its shape. Width is the measure of land scarcity the framework already uses; on a front it is the whole route sense, so no new scale is needed and fronts and strips rank on the same number. A road along a gap narrows the front and raises the class; a road across it does not change which routes are viable and is a crossing-structure question — the same treatment strips get. |
| D25b (amended by D25c) | `corridor_area_km2` **includes** fronts. `front_area_km2` and `front_share` are descriptor columns. The three-way identity (corridor + intra-name + augmentation = total band) is restored; the calibrated cutoff (D6) is unchanged. | Fronts are corridor land; excluding them understated the corridor estate and detached the area figure from the calibration set. |
| D25a (SUPERSEDED by D25c, 2026-09-29) | **Near-contiguous sub-classes.** For every `near_contiguous` link (trigger: `lcp_len_cells < open_ground_width_med`, D25), compute `squeeze_ratio_obs` (D17) as usual — the counterfactual front satisfies the resolution floor (D24) by construction — and `lcp_max_cost` = maximum cost class on the least-cost path (1, 10, 100, 1000). Sub-class, first match wins: **adjacent — barrier between** if `lcp_max_cost ≥ 100`; **adjacent — front crossed by roads or cuts** if `lcp_max_cost == 10` **or** `squeeze_ratio_obs < squeeze_ratio`; **adjacent — open front** otherwise. Branch decomposition remains skipped (no route sense on a front). The edge sense (D7) is still reported. Per link the table (`near_contiguous_links.csv`) carries `gap_km` (= least-cost path length), `open_ground_width_med`, `squeeze_ratio_obs`, `lcp_max_cost`, and both areas' sizes. | Branches are meaningless on a front, but width is not: the ratio of the actual band to the barrier-free front says directly whether the frontage is intact or cut. Keying "barrier" on cost 1000 missed the case that matters most for abutting areas in this sector — a road along the gap — because roads are cost 10. The three sub-classes map onto three different asks: nothing to design; a crossing-structure question; a genuine separation. |
| D25b | **Near-contiguous area is not corridor area.** `corridor_area_km2` in every table and caption excludes near-contiguous bands; `near_contiguous_area_km2` is its own line (with `intra_name_area_km2`, `augmentation_area_km2`, `total_band_area_km2` — per-edge band sums, in `corridor_summary.json`). The calibrated cutoff (D6) stays as calibrated over all tree edges on run002 and is **not** recomputed with near-contiguous links excluded. | Recalibrating would move every band in the sector and break comparability across run002/run003 and with v1. Reporting the front area separately is enough to stop the deck counting fronts as corridors. The area-calibration rule's dependence on fronts is noted as a known limitation for the derived-analysis calibration by detour distance (D31), which does not have this problem. |
| D26 | **Relative branch-sliver floor.** A band component at `cutoff_branch` is kept as a branch if its area ≥ `branch_min_frac` × (the link's band area at `cutoff_branch`) **and** ≥ `branch_min_cells`. `branch_min_km2` is retired; `resolve()` raises if it appears. Dropped-component count and the largest dropped fraction are reported per link. | A fixed 10 km² is noise on a 200 km link and a real second route on a 30 km one, so branch counts were length-biased. On open ground the band is one ellipse, so any second component is a barrier signal and the floor should protect it, not swallow it at short lengths. |
| D27 | **Locked intra-name links are class-ineligible until tested.** Every locked link (D16) carries `locked = True`. The alternative-link test (D7) is run for it against the full candidate set, including routes via other names; `edge_irreplaceable` is set only if that passes. Until run and passed, locked links are classed "corridor land with options" at most and never "last affordable link" or "only viable connection". The table shows `locked` and `alt_test_run`. | A locked link never competed in the tree, so an irreplaceability class on it is a management assertion presented as a finding. Running the test makes it a finding or removes the class. |
| D28 | **Pinch-aware width column.** Alongside `squeeze_ratio_obs` (the D17 width ratio), report `width_ratio_p10` = tenth percentile of the per-position cross-section ratio (actual band ÷ counterfactual band, both allocated to their own least-cost path and binned to 50 fractional positions) and `pinch_pos` = fractional path position of the minimum. **Reported, not classed**; the squeezed class stays on the D17 ratio. Subject to the resolution floor (D24). | The median cannot see a single constriction, which is the ecologically important case (Pinto & Keitt's merge point). This is the geometric half of the deferred pinch-point comparison (D20), computed for free from the existing bands, so the circuit-based half has something to compare against when it runs. |
| D29 | **Alternative-link cost decomposed.** For every edge, the cheapest alternative link used by the β test (D7) is reported as `alt_cost`, `alt_len_km` (least-cost path length), `alt_mean_res` (= `alt_cost` / cells), and `alt_kind` ∈ {far, hard, both} (or affordable / none): *far* if `alt_len_km / lcp_len_km ≥ β` with `alt_mean_res` within `alt_res_tol` × the edge's own; *hard* if the length ratio is below β but the cost ratio is not; *both* otherwise. | "Alternatives cost far more" conflates distance and resistance. In the north, where resistance is nearly uniform, edge-irreplaceability is mostly node spacing; the profile text needs to be able to say "isolated" rather than "walled in". Legend string unchanged; the distinction lives in the table and the one-pagers. |
| D30 | **Fixed-break near-optimality tiers.** `near_opt_tiers` becomes fixed slack breaks in cost units: robust core ≤ `cwd_cutoff_abs`/6, frequent ≤ `cwd_cutoff_abs`/2, occasional ≤ `cwd_cutoff_abs` (the band); routable land beyond the band is a fourth class. Percentile tiers retired. Appendix product only (unchanged). | Percentiles of slack over the union band are area-weighted, and area is dominated by the long northern links, so the breaks were set by the north. Raw slack is comparable across links; fixed breaks keep it so. Fractions of the calibrated cutoff keep the tiers consistent across the cutoff sweep (axis B). |
| D31 | **Cutoff stated as detour distance; calibration rule for derived analyses.** `run_config.json` and every caption that mentions the cutoff also carry `cutoff_detour_km` = `cwd_cutoff_abs` × cell size on cost-1 ground (13.6 units × 0.3 km ≈ 4.1 km on run002). The northern network keeps the v1 area calibration (D6) for comparability. **A derived analysis with no v1 target calibrates by detour distance**, choosing `cutoff_detour_km` and deriving the cost cutoff from it; it never calibrates by area or by class counts. | An area target is dominated by the long links and means nothing to a reader; "routes within about four kilometres of extra travel on open ground" does. It is also the only defensible way to set a cutoff where there is no prior area to match. |
| D21 | **Adjacency graph as diagnostic universe.** `G_adj` = cost-weighted allocation adjacency: allocate every routable cell to the seed part with the minimum CWD (argmin over the cached part fields; ties → lowest part id); two parts are adjacent if their allocation zones share an 8-connected boundary; contract parts to names (and zero-cost cliques as in §7) to give the name-level graph. Optional LM-style filters are **off** (no distance cap; no intermediate-core drop) so the graph is the raw neighbour set — filters are reported as counts, not applied. Products: `adjacency_edges.csv` (i, j, `in_backbone`, `edge_class` if in the network, `min_e` cost, LCP length), `adjacency_nodes.csv` (`n_neighbours` per name; also per part), the `is_adjacent` column added to `corridor_edges.csv`, and one appendix figure (`adjacency_map`: thin neighbour links as lines — **not bands** — over the M1 basemap). **Not a routing input; no bands are computed for adjacency-only edges; no legend class.** | Linkage Pathways' network is the neighbour graph (McRae & Kavanagh 2011); ours is the minimum backbone plus affordable backups. Reporting both makes the relationship explicit: the difference is the choice space, which is the Act 1 quantity the current products cannot state — a name's number of possible partner links. Kept as a universe rather than adopted as the network because banding ~100 neighbour links destroys the must-have/optional distinction unless a weighted priority ranks them (the D5-rejected blend). Cost is trivial: the allocation is an argmin over fields already in memmaps. |

---

## 2. Pre-registered constants (set in `config.CORRIDORS["north"]` **before** `cc.start()`)

| key | value | note |
|---|---|---|
| `calibrate_cutoff` | `{"target_km2": 18188, "edges": "mst"}` | unchanged |
| `branch_mult` | `0.5` | reuses the 0.5× axis-B member; no new CWD work |
| `branch_min_km2` | `10` | drop slivers; ~111 cells at 300 m. Report dropped count. |
| `near_opt_tiers` | percentiles **of slack** over the union band at 2× cutoff: robust_core ≤ p10, frequent ≤ p30, occasional = rest | mirrors p90/p70 on the inverted scale; defined on the 2× union so the tier domain is wall-to-wall-ish, not band-only |
| `carroll_ref` | `"routable_area"` | first pass: branch mean percentile vs routable-area percentile baseline. Matched random strips (Phase 6 method) deferred. |
| `robust_core_freq` | `0.9` | unchanged (applies to `ensemble_attribution.tif`) |
| `part_min_km2` | `25` | = node minimum; parts below this are area-only, not seeds (D16) |
| `width_floor_cells` | `8` | D24; counterfactual median width (cells) below which the width test is unassessable |
| `len_floor_cells` | `10` | D24; least-cost-path length (cells) below which the width test is unassessable |
| `near_contiguous` | `{"rule": "lcp_len_cells < open_ground_width_med"}` | D25; no free parameter — the test is relative |
| *(D23)* | — | `squeeze_ratio` = 0.5 is the ONLY width threshold; `resolve()` raises on any second width / ratio key (`only_viable_ratio`, `route_width_thresh`) |
| `branch_min_frac` | `0.05` | D26; fraction of the link's band area at `cutoff_branch` |
| `branch_min_cells` | `20` | D26; absolute noise floor (≈ 1.8 km² at 300 m) |
| `branch_min_km2` | **retired** | D26; `resolve()` raises on presence |
| `alt_res_tol` | `1.5` | D29; resistance ratio within which an alternative is "far", not "hard" |
| `near_opt_tiers` | `{"robust_core": "cutoff/6", "frequent": "cutoff/2", "occasional": "cutoff"}` | D30; replaces the percentile spec |
| `cutoff_detour_km` | derived, written by `resolve()` | D31; northern: derived from `cwd_cutoff_abs`; derived analyses: set, and `cwd_cutoff_abs` derived from it |

**Tuning prohibition (D24).** The two floor constants are pre-registered here and recorded in `run_config.json` before the
eight-cell table (G18) or the floor-effect report (G19) is read for the run in question. Changing either after reading a
class count is a post-hoc calibration and is not permitted; a derived analysis may raise a floor (stricter) with a logged
reason, never lower one. The near-contiguous rule has no constant by design. The prohibition extends to `branch_min_frac`,
`branch_min_cells`, and `alt_res_tol` (D26 / D29).
| `multisite_designations` | `["Ecological Reserve", "Wildlife Management Area", "National Wildlife Area", "Migratory Bird Sanctuary"]` | step 0a rule 2; extend from the reviewed list |
| `multipart_link_km` | `10` | step 0a rule 2 exception distance |
| intra-name treatment | per name, from reviewed `multipart_review.csv` (`merge_parts` / `link_locked` / `link_competing` / `no_link`) | `link_competing` uses the D7 β ceiling against the cheapest inter-name path between the parts; `no_link` parts are independent nodes in the inter-name graph |
| `squeeze_ratio` | `0.5` | D17; matches the draft map. Confirmed 2026-09-03 (H8 closed). |
| `squeeze_cf_min_cost` | `10` | D17: cost classes at or above this are relaxed to 1 on the counterfactual surface (roads, converted land, water/ice). |
| `centrality` | `"current_flow"` | D19; `"shortest_path"` retained only as the `centrality_sp` comparison column |
| `validation_pairs` (deferred, D18) | 5 MST edge ids, chosen by rule: shortest, longest, one crossing a cost-1000 mask, one with `n_branches ≥ 2`, one both-senses irreplaceable | D18 / G14; ids recorded in `run_config.json` once the baseline exists |
| `pinch_pctl` (deferred, D20) | `95` | D20; within-band percentile defining a pinch cell |
| `pinch_edges` (deferred, D20) | `"all_nonzero"` | D20; run on every non-zero-cost baseline edge (band count is small; cost is per-band Circuitscape solves) |
| `pinch_conc_thresh` (deferred, D20) | `4.0` (proposed) | D20 comparison 2×2; set from the baseline distribution before class counts are read, and logged |
| `adjacency` | `{"metric": "cwd", "connectivity": 8, "distance_cap_km": null, "drop_through_core": false}` | D21; filters off, counts reported. `metric: "euclid"` available for the comparison column only. |

These go into `run_config.json` via `resolve()`. `resolve()` should raise if `branch_mult`,
`branch_min_km2`, or `near_opt_tiers` are absent (same no-dead-flags doctrine as D2). `centrality`
defaults to `"current_flow"` when absent (runs that predate D19 load unchanged). Deferred keys are
**not** written to `run_config.json` until their decision is activated — a deferred constant in
the config would be a dead flag.

---

## 3. Run sequence

The steps below are distributed across the four numbered notebooks in
`analyses/northern_connectivity/` (see §9 for the exact mapping; §8 for the folder layout).
Provenance is unchanged: `cc.start()` into `output_data/corridors_north/v2_run001/`, and the
engine reads only `run_config.json` thereafter.

**Step 0a — part split and multipart review (D16).** Rasterize nodes at 300 m (existing
path), label 8-connected components per name, apply `part_min_km2`. Write `node_parts.csv`
(name, part_id, area_km2, is_seed) and `node_parts.gpkg` — into
`analyses/northern_connectivity/audit/audit_objects/` (git-tracked; see §8 for why this is the
canonical home, not the run dir).

Then the analysis reviews every name with >1 seed part and writes `multipart_review.csv`, one
row per name, with a proposed treatment and the evidence for it. Evidence columns:

| column | what it carries |
|---|---|
| `designation` | from the source attribute (PAD-US/CPCAD `TYPE`/`IUCN_CAT`; IPCA tracker category). Ecological reserves, wildlife management areas with scattered sites, and marine/lake units are the designations most often deliberately multi-site. |
| `n_parts`, `part_areas_km2` | count and sizes; note largest-to-second ratio |
| `min_gap_cells` | minimum cell gap between any two parts at 300 m; < 3 cells ⇒ **rasterization split** (river, road, polygon slivers) |
| `max_euclid_km` | farthest part pair, centroid to centroid |
| `cwd_between_parts` | CWD-path cost and length between each part pair, on the O'Brien surface (cheap: parts only, not the full 42-name set) |
| `intervening_nodes` | other names whose masks the intra-name least-cost path crosses |
| `crosses_cost_1000` | whether any intra-name path traverses a cost-1000 cell |
| `proposed` | one of `merge_parts` (rasterization split — re-join into one seed), `link_locked` (default D16), `link_competing` (parts far apart or a third node intervenes — a forced link would route through or around another park), `no_link` (designation is multi-site by design, or gap is geographic — separate lake/island units) |
| `reason` | one sentence tying the proposal to the columns above |

Decision rules, applied in order and recorded in `run_config.json`:
1. `min_gap_cells < 3` → `merge_parts`.
2. designation in the multi-site-by-design list (maintained in config, starts with: Ecological
   Reserve, Wildlife Management Area, National Wildlife Area, Migratory Bird Sanctuary) →
   `no_link`, unless the parts are within 10 km and nothing intervenes, then `link_locked`.
3. any `intervening_nodes` → `link_competing` (the inter-name network already carries the
   connection; a locked intra-name edge would duplicate it).
4. otherwise → `link_locked`.

**G0 is re-baselined**: the gate becomes "name set = 42, same 3 dedupe merges" (name level,
unchanged) plus a recorded part count and the `multipart_review.csv` hash that later runs must
reproduce. **H7** is now a confirmation of the proposed column, not a from-scratch review:
the human edits `proposed` where the rules get it wrong, and the edited file is the input to
step 1. The run does not proceed to CWD until the file carries a `reviewed_by` line.
`multipart_review.csv` lives beside `node_parts.csv` in `audit/audit_objects/` (git-tracked —
the reproduce-this-hash requirement cannot be met by a file in gitignored `output_data/`);
`cc.start()` copies both into the run dir for self-containment and records their sha256 in
`run_config.json`, preserving the run-dir-is-the-only-record doctrine.

**Step 0 — preconditions.** G0 (as re-baselined), G2, G8 re-assert on current disk state. Confirm CWD cache
directory keyed by the O'Brien surface hash is present or will be built. H1 (licence/provenance
sign-off on the O'Brien surface) is a human task and does **not** block the run; it blocks
external release of outputs.

**Step 1 — calibrate.** CWD fields computed per **seed part** (cache keyed by resistance hash
+ part mask hash). Intra-name MSTs built and locked (D16). `calibrate_cutoff` on the
**inter-name MST edges only**, `& ~node_union`, target 18,188 km². Write `cwd_cutoff_abs`
into `run_config.json`. Record the calibrated value and the achieved area (expect exact or
within one cell-area of target; report the residual). Inter-name distance between two
multipart names = min over part pairs (standard multi-seed semantics; state it).

**Step 2 — baseline.** Locked intra-name edges + inter-name MST + bridge-backup augmentation
(β = 2.5), **current-flow betweenness centrality on the quotient graph (D19)** with shortest-path
betweenness kept as `centrality_sp`, criticality, bands at `cwd_cutoff_abs`,
`linkage_priority.tif`, `edge_owner.tif`, audit, maps. Locked edges carry `edge_class =
"intra_name"` in `corridor_edges.csv`, are included in criticality and failure enumeration
(they are real corridor land), and their band area is reported as a separate line from MST
and augmentation area. G3, G4, G5 run here; G4 ("β = 0 reproduces the MST") is read as
"reproduces locked + inter-name MST".

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

**Step 3 — ensemble.** Axes B {0.5, 1, 2}×, C (42 leave-one-out **by name**, all parts
dropped together — including `no_link` parts, which are independent in the graph but share
the name's realisation risk), D β {1.5, 2.5, 4.0}. G7 on the drop-nothing member. Serial, memmap-backed, one CWD set (unchanged). Write
`ensemble_attribution.tif` + per-axis attribution rasters (D15).

**Step 4a — near-optimality surface (D11).** For every routable cell,
`near_optimality = min over baseline edges e of (CWD_i + CWD_j − min_e)`. Zero-cost adjacency
edges contribute nothing (no CWD band, consistent with §7). Stream edge by edge from the
memmaps; keep a running minimum and an `near_opt_owner.tif` (argmin edge). Tier with
`near_opt_tiers` → `near_optimality_class.tif`. G10 here.

**Step 4b — route branches (D12).** Per non-zero-cost baseline edge (MST + augmentation):
1. Band at `cutoff_branch` **including node cells** (do not subtract `node_union` yet).
2. 8-connected components.
3. G9: assert every component intersects **both** endpoint node masks. Property: a band cell c
   has slack(c) ≤ cutoff, and every cell on the least-cost i→c→j path has slack ≤ slack(c), so
   each component is connected to both endpoints inside the band. A failing assert means a
   masking or seed-handling bug, not a legitimate outcome.
4. Subtract `node_union`; drop components < `branch_min_km2` (count reported); label
   remaining `branch_id = {edge_id}_{k}` ordered by min slack.
5. Per branch: `area_km2`, `min_slack`, `mean_slack`, `cells`, `bbox`, and a length proxy
   (major-axis length of the component; state it is a proxy, not a path length).
6. Per edge: `n_branches`, `route_irreplaceable = (n_branches == 1)`.
Write `branches.tif` (branch label raster, 0 = none), `branches.gpkg`, `branches.csv`.

**Step 4c — values table (D13, D14).** For each branch: `_to_audit` (300 m → 1 km, areal
fraction ≥ 0.5), `audit_area_check`, then `mask_profile` for every value layer in the
Y2Y-wide alternatives column spec (import it). Add `carroll2018_pctl` = mean percentile of
Carroll 2018 current-flow centrality within the 1 km branch mask, with the routable-area
percentile as the reference column (`carroll_ref`). Join branch metrics + edge metrics
(cost, criticality, β-irreplaceable flag, `n_branches`). Write `alternatives_branches.csv`.
Caption text (stored with the table metadata): "Row unit is edge × route branch, not a solution
cluster; columns follow the Y2Y-wide alternatives table for readability only."

**Step 4d — tie-break report (Phase 8.3, small).** For edges with `n_branches ≥ 2`, rank
branches by the audit columns and write `tiebreak.csv` with both the connectivity-equivalence
evidence (slack difference) and the values evidence. Ranking only — no automated
"recommended" flag; the recommendation is a human read of the table.

**Step 4e — DEFERRED (D20).** Not run in v2_run002 or its ensemble. Spec retained in §10 for
the future comparison. G15 (`centrality_compare.csv`) runs in step 2 and again in notebook 04's
step 0b when a run is re-attached.

---

## 4. Gates (add to §10)

| gate | invariant | where |
|---|---|---|
| G9 | every branch component (pre node-subtraction) intersects both endpoint node masks | step 4b, hard assert |
| G10 | `near_optimality == 0` exactly on every baseline least-cost path cell; tier classes monotone in slack | step 4a |
| G18 (eight-cell adoption check) | On run002 (pinned) and on every later baseline: the count table over edge-irreplaceable × one-branch × narrow (8 cells) is written to `class_truth_table.csv` and reported before class rasters are drawn. Class counts on the map must equal the table's row sums under the §6 precedence (plus the unassessable links classed from the edge sense). **Adoption condition for run002:** the four links classed only-viable under the retired rule all sit in the (E, B1, S) cell — measured: they do NOT (1 of 4), so the 06 example-regeneration rule fires and the change is logged as a post-pin class change. `squeeze_ratio_obs` must be non-null for every non-zero-cost edge, or the gate fails. | step 4b (`classify_links`, after the branches), before any figure |
| G19 (floor effect) | For every baseline: the histogram (p10/p50/p90) of `lcp_len_cells` and `open_ground_width_med` across non-zero-cost edges, the number of links `width_not_assessable`, the number `near_contiguous`, and — as a diagnostic only — how the class counts would differ with the floor halved and doubled (`floor_effect.csv`). Assert: every `near_contiguous` link has `n_branches` unset (decomposition skipped) and no corridor class; every `width_not_assessable` link has `squeezed == False`; the four-class counts in the legend equal the §6 row sums. If the halved/doubled floors move more than 10 % of links between classes, the report says so and the floor is discussed, **not changed**, for that run. | step 4b, with G18, before any figure |
| G24 (one scale, D25c; G23 retired) | Every non-zero-cost edge has exactly one `link_geometry` and exactly one of the four classes (contacts: options or last-affordable only). Every `front` has `n_branches` null and B1 recorded as forced; every `strip` has a computed `n_branches`. Class counts on the map equal the eight-cell table (G18) row sums with fronts folded in under B1 = true. `road_crossing` never changes a class (asserted). Corridor-area identity holds. The run report gives class × geometry as a 4 × 3 table (`class_by_geometry.csv`). | step 4b (`classify_links`), before any figure |
| G23 (RETIRED with D25a) | Every near-contiguous link has `open_ground_width_med ≥ width_floor_cells` (if not, the D24 floor applies first and the link is `width_not_assessable`, not near-contiguous — the ordering is asserted); every near-contiguous link has a non-null `squeeze_ratio_obs` and `lcp_max_cost`; sub-class counts sum to the near-contiguous count; `corridor_area_km2 + near_contiguous_area_km2 + intra_name_area_km2 + augmentation_area_km2` reproduces the total band area (per-edge band sums). Report the 18-link table (run002) with the five per-link columns from D25a. | step 4b (`classify_links`), with G19 |
| G20 (locked-link eligibility) | No link with `locked = True` carries `edge_irreplaceable = True` unless `alt_test_run = True`; every locked link with `alt_test_run = True` has a non-null `alt_cost` (unless no alternative exists). Class counts in the legend reflect this. | step 2 (inside `corridor_network`) |
| G21 (branch floor effect) | Per baseline: distribution of dropped-component fraction; number of links whose `n_branches` changes between the retired fixed floor and the relative floor, listed (`n_branches_fixed_floor` column). Assert every kept branch satisfies both minima. | step 4b (inside `route_branches`; with G19 once it lands) |
| G22 (tier and cutoff consistency) | `width_ratio_p10 ≤ squeeze_ratio_obs` for every assessable edge (5% tolerance: the p10 is a quantile of per-position ratios, `squeeze_ratio_obs` the area/length ratio); tier classes monotone in slack with breaks exactly at cutoff/6, cutoff/2, cutoff; `cutoff_detour_km` / cell size reproduces `cwd_cutoff_abs` to float tolerance. | step 4a (tiers, cutoff) + step 2b (width) |
| G11 | per-branch `audit_area_check` discrepancy ≤ 5% for branches ≥ 50 km²; all discrepancies logged | step 4c |
| G12 | ensemble member count = 1 baseline + 2 (B, excluding the 1× duplicate) + 42 (C) + 2 (D, excluding the 2.5 duplicate) = 47 distinct members; duplicates resolved by config-hash equality, not by name | step 3 |
| G13 (restated 2026-09-08, final) | The counterfactual band bounds the real band in NEITHER direction — measured on v2_run002 it is narrower per km on some links for two legitimate reasons: relaxation SHORTENS a detouring route, or barriers on the real surface EQUALISE two routes into a near-tie (a braided, wide band: Liard↔Nahanni's two branches) that relaxation breaks, collapsing the band to one ribbon. The gate is therefore the one true relaxation invariant: `lcp_cf ≤ lcp_real` for every banded edge (lowering costs can never make the least-cost route costlier) — hard assert. Narrower-counterfactual links are reported with widths and lengths, never classed squeezed. The `squeezed` count is reported and, if it differs from the draft map's 5, the director package regenerates from the confirmed definition | notebook 04 step 2b, hard assert |
| G14 (deferred, D18) | Linkage Pathways validation (D18): for each of `validation_pairs`, Pearson r between LM's normalized least-cost corridor and our slack over the union of both corridors ≥ 0.99, and Jaccard of the truncated bands at matched cutoff ≥ 0.95. Recorded with the LM version, the resistance-surface hash, and the LM run parameters. Failure halts: it is a bug in one of the two implementations until shown otherwise. | once per resistance hash; before any external release (with H1) |
| G15 | current-flow centrality is finite and non-negative on every edge; on a pure tree (β = 0 member) current-flow and shortest-path edge betweenness rank identically (on a tree there is one path per pair, so both reduce to the same count) — assert the two are PROPORTIONAL there (exact ties; a rank test is broken by solver noise), Spearman reported; `centrality_compare.csv` written | step 2 |
| G16 (deferred, D20) | native circuit solve vs Circuitscape 5 on one validation band (the `n_branches ≥ 2` member of `validation_pairs`): Pearson r of cell current ≥ 0.99 and the top-5 % current cells overlap by Jaccard ≥ 0.9. Recorded once per resistance hash with the Circuitscape version. | before step 4e results are read |
| G17 | every inter-name MST edge is an adjacency edge (`is_adjacent` true for all `edge_class == "mst"`); locked intra-name edges are exempt (parts of one name may be separated by another name's zone by design — reported, not asserted). Failure is investigated, not auto-fixed: an MST edge whose LCP crosses a third name's zone is either a multipart-field bug (Clarification 1) or a genuine case to document. | step 2c, hard assert on `mst` edges |

G1 stays the gate that matters; none of the above replaces it.

---

## 5. Outputs (add to §11 per-run list)

`node_parts.csv/.gpkg`, `multipart_review.csv` (run-dir copies — the canonical, H7-signed
originals live git-tracked in `audit/audit_objects/`, hash-pinned by `run_config.json`; see
step 0a and §8), `near_optimality.tif`, `near_optimality_class.tif`, `near_opt_owner.tif`,
`ensemble_attribution.tif` (+ per-axis), `branches.tif/.gpkg/.csv`,
`alternatives_branches.csv`, `tiebreak.csv`, `centrality_compare.csv` (D19); `corridor_edges.csv` gains
`centrality_cf`, `centrality_sp` (D19), `band_new_km2`, `band_cf_km2`, `squeeze_ratio_obs`, `squeezed` (D17) and
`bands_counterfactual.gpkg` is written (D17 natural-width polygons). All rasters COG, ESRI:102008 at 300 m (audit
crossings stay internal), Dublin Core+ metadata written at creation. Every product that is not a
frequency is named so it cannot be read as one. D21 adds `allocation.tif`, `adjacency_edges.csv`,
`adjacency_nodes.csv`, `figures/adjacency_map.png`; `corridor_edges.csv` gains `is_adjacent`,
`is_adjacent_euclid`, `via_names` (D21).

---

## 6. Reporting rules (carry into the methods text)

- "Corridor" is reserved for bands/branches from this engine. The near-optimality surface is
  described as a near-optimality (slack) surface; `ensemble_attribution.tif` as attribution.
- Two irreplaceability senses are always reported together and never merged: edge-irreplaceable
  (D7, β ceiling — no alternative link) and route-irreplaceable (D12 — no alternative routing
  within a link).
- The four presentation classes (securing / both-senses irreplaceable / edge-irreplaceable /
  squeezed) are derived, disjoint, and defined here (D7, D12, D17), not in the director package.
  The package renames them; it does not redefine them.
- Zero-cost adjacency caveat (§7) applies to branch counts: "no corridor needed between touching
  areas" is conditional on IPCA proposals being realised.
- The climate dimension in this product is audit-only (macrorefugia and `carroll2018_pctl`
  columns). No routing is climate-informed. Phase 7 status is "deferred, scope extension".
- Method precedent is stated: the corridor model is equivalent to Linkage Mapper's Linkage
  Pathways (McRae & Kavanagh 2011) — formal validation against it is deferred (D18/G14) and
  the text says so; centrality follows Centrality Mapper's current-flow formulation (D19).
  Linkage Mapper's Linkage Priority (weighted multi-factor blend) is deliberately not adopted:
  values are reported as an audit rather than folded into a weighted priority, so that every
  priority statement traces to a single, checkable reason (D5).
- Pinch points (D20) are deferred; the squeezed class (D17) stands alone in this version and
  is described as a geometric measure of narrowing, not a flow bottleneck.
- The adjacency graph is reported as the **neighbour universe** (Linkage Pathways' network
  convention), the backbone as the **minimum network plus affordable backups**; the deck and
  methods text state that the difference between them is the choice space, never that the
  backbone is "the corridors" and adjacency "extra corridors". `n_neighbours` is the Act 1
  option count per area; it is a count of possible partner links, not of corridors.

---

**Reporting rules added by the geometry-vs-ecology audit (D26–D31, 2026-09-28):**
- Locked intra-name links (D27) are drawn with the class they earned after the alternative test, never the class they
  would have had without it; the profile for any locked link says it was locked and tested.
- Where an irreplaceable class appears in a profile, the text names the alternative's kind (D29): "the next link is far"
  versus "the next link crosses hard ground"; on the northern network most will be *far*, and the deck says so once.
- The cutoff is described in captions as detour distance (D31), with the cost-unit value in the methods note only.
- Tier maps in the appendix carry the fixed breaks in the legend (D30), not percentiles.

**Precedence (D23 / D24 / D25, 2026-09-28) — one row per combination, applied top-down, first match wins; this table replaces
the implicit precedence in the "four classes are derived, disjoint" line and is the single source for map classes, legend
counts and both alternatives tables (`classify_links` → `link_class`).** E = no alternative link within β (D7), B1 = one
branch (D12 decomposition), S = width ratio < `squeeze_ratio` (D17).

| condition | class (director string) | notes |
|---|---|---|
| zero-cost adjacency (§7) | *not a link on the map* | unchanged |
| `contact` (D24: width not assessable) and E | last affordable link | edge sense only; `width_not_assessable` shown |
| `contact` | corridor land with options | edge sense only |
| `front` or `strip` | the eight-cell table (D23), B1 := true on fronts | fronts: route sense = width alone (D25c) |
| `width_not_assessable` and E | last affordable link | edge sense only; table shows `width_not_assessable` |
| `width_not_assessable` | corridor land with options | edge sense only |

Then the eight-cell table for the remaining links:

| E | B1 | S | class (director string) | route-irreplaceable (amended D12) | note |
|---|---|---|---|---|---|
| ✓ | ✓ | ✓ | only viable connection | ✓ | the top class; all three senses |
| ✓ | ✓ | ✗ | last affordable link | ✗ | one wide branch — a leaf across intact land lands here |
| ✓ | ✗ | ✓ | last affordable link | ✗ | alternatives within the band exist; land narrow — width shows in the table |
| ✓ | ✗ | ✗ | last affordable link | ✗ | |
| ✗ | ✓ | ✓ | already narrowing | ✓ | route-irreplaceable but a backup link exists; the flag shows in the table, not the map |
| ✗ | ✗ | ✓ | already narrowing | ✗ | |
| ✗ | ✓ | ✗ | corridor land with options | ✗ | one wide lens |
| ✗ | ✗ | ✗ | corridor land with options | ✗ | |

- The two irreplaceability senses are still reported together in the tables (edge flag, amended route flag, and the
  retained topology-only route flag `route_irreplaceable_topo`) and never merged; the map shows the class, the tables show
  the flags.
- The methods text states the principle in one sentence — no unprotected land is treated as secured — and explains that a
  front is classed on width because it has no branches (D25c). Corridor-area figures include fronts; the caption gives the
  front share once (D25b amended).
- Profiles for fronts say "wide front between the areas — N km of room" (open) or "front cut along its length — at X of its
  natural width" (narrowing), and carry the road-crossing flag as a separate sentence when set.
- The methods text states that three link classes are decided by geometry before any corridor class is assigned: touching
  (zero-cost), near-contiguous, and too short for the width test. It gives the counts for each on the run in question. For a
  derived analysis (wolverine) the same table and constants apply, and its report states how many links fell to each
  geometric class.
- Provenance line for the methods text: the top-class rule was changed on 2026-09-28 after the part-3 bridge case exposed
  that neither existing sense measured land; adopted on the general argument and checked against the pinned run (G18) so it
  was not tuned to the case.


## 7. Human tasks touched

- **H1** (O'Brien provenance/licence) — unchanged; gates release, not the run.
- **H7 (new, blocking)** — confirm or edit the `proposed` column in `multipart_review.csv`
  (produced by step 0a). Sign with a `reviewed_by` line. The run does not proceed to CWD
  until signed.
- **H6 (new)** — confirm Carroll 2018 current-flow centrality raster is on disk and catalogued;
  if absent, step 4c runs without the column and logs the gap rather than failing.
- **H8 (new, blocking for the director package)** — Claude Code reports how `squeezed` and
  "open-ground width" were actually computed for the draft regime map. If it matches D17,
  mark D17 confirmed; if not, replace D17's definition with the implemented one, update the
  rationale, and re-check G13. The director package's "already narrowing" class does not ship
  until this is closed.
- **H9 (deferred with D18)** — run Linkage Pathways on `validation_pairs` with the exported O'Brien
  surface and node rasters (identical grid, CRS, nodata). Preferred form: a batch script
  `validation_lm/run_lm.py` in the ArcGIS Pro Python (arcpy) environment using Linkage
  Mapper ≥ 3.0.1's scripted-run entry points, so G14 is reproducible; manual tool runs are
  acceptable as a fallback. arcpy is confined to `validation_lm/` and is **not** a pipeline
  dependency. Hand back the NLCC and truncated-corridor rasters plus the LM run log; Claude
  Code computes G14. Open: whether ArcGIS Pro is on the pipeline machine or a separate box.
- **H10 (deferred with D20)** — run Circuitscape 5 (Julia, any machine) pairwise on the one G16
  validation band exported by the pipeline (resistance ASCII + source/ground rasters) and
  hand back the current raster. Not a pipeline dependency: step 4e runs natively regardless;
  its results are marked unvalidated until G16 is recorded.
- Decision after step 3: whether to open Phase 7 at all, based on axis C stability.
- Future comparison (not scheduled): activate D18 and D20 together — LM validation of the
  corridor engine and the squeeze-vs-pinch comparison — and only then decide whether `pinch`
  products enter the ops package.

- **Follow-up decision (D7 amendment, not taken):** if step 2c reports ≥ 1 backup edge that is
  not adjacent (its LCP crosses a third name's allocation zone), decide whether backup
  candidates should be restricted to `E_adj` — LM's intermediate-core rule. Restriction would
  change the network and therefore the pinned examples (06 v1.2.4), so it is taken **after
  October** unless the count is zero, in which case it becomes documentation only
  ("backups are, empirically, all neighbour links"). Logged either way.

---

## 8. File structure (added 2026-08-21)

The corridor analysis is promoted to a self-contained campaign folder,
**`analyses/northern_connectivity/`**, mirroring the `analyses/y2y/` flagship convention:
notebooks + spec + small frozen human-review artifacts live in the analysis folder (tracked);
engines stay at repo root; every run product stays in gitignored `output_data/`.

```
analyses/northern_connectivity/
├── 01_prep_and_parts.ipynb        # kernel y2y-geo
├── 02_calibrate_baseline.ipynb    # kernel y2y-geo
├── 03_ensemble.ipynb              # kernel y2y-geo
├── 04_alternatives.ipynb          # kernel y2y-geo
├── spec/
│   └── 05_corridors_v2_addendum_run_and_alternatives.md   [tracked — this file]
├── audit/
│   └── audit_objects/             [tracked]
│       ├── node_parts.csv / node_parts.gpkg               (step 0a)
│       └── multipart_review.csv   (H7-signed; sha256 recorded in run_config.json)
└── figures/                       [gitignored via analyses/*/figures/ — for any
                                    notebook-level figure not tied to a run dir]
```

Conventions:

- **Engine modules stay at repo root** — `corridors_prep.py`, `corridor_graph.py`,
  `corridors_core.py`, `corridors_ensemble.py`, plus `config.CORRIDORS["north"]` in `config.py`.
  Same convention as `leverage_core` / `prioritizr_core` / `results_core` for the y2y campaign;
  `corridors_core` imports `results_core`, so root placement also avoids import churn.
- **All run products stay in `output_data/corridors_north/v2_runNNN/`** (gitignored; provenance
  via `run_config.json`, unchanged from §7 of the methods doc). Per-run figures stay in the run
  dir's own `figures/`.
- **H7 artifacts are git-tracked in `audit/audit_objects/`** — `output_data/` is gitignored and
  later runs must reproduce the review file's hash, so the signed review must live somewhere
  version-controlled. This mirrors the y2y pattern (frozen, load-bearing review conclusions —
  `audit_constants.json`, `feature_characterization.csv` — tracked in the analysis folder).
  `cc.start()` copies them into the run dir and records their sha256, so each run dir remains
  self-contained.
- **Every notebook opens with the root-finding bootstrap** — the exact `_cands` pattern from
  `analyses/y2y/01_feature_audit.ipynb` cell 1 (probe cwd + parents for `config.py`,
  `sys.path.insert(0, str(ROOT))`, then define `HERE` / `AUDIT_OBJ`). The corridor modules are
  verified cwd-independent: every path derives from `config.PROJECT_DIR` (which is
  `__file__`-anchored) and the git-SHA subprocess passes `cwd=config.PROJECT_DIR` explicitly, so
  the bootstrap is the **only** move-related change the engine needs.
- The existing `analyses/*/figures/`, `analyses/*/audit/feature_cards/`, `analyses/*/runs/`
  gitignore globs cover this folder automatically — **no .gitignore edit**.
- **Migration at build time**: the four notebooks are carved from the root
  `05_corridors_north.ipynb` (40 cells; mapping in §9). Once they run end-to-end, the old
  notebook is `git mv`'d to `archive/` beside `05_corridors_north_v1.ipynb`;
  `docs/05_methods_v2.md` is patched with this addendum's sections (per the header note) and the
  CLAUDE.md 05 section gets a pointer to this folder at the same time.

---

## 9. Notebook breakdown (added 2026-08-21)

Run top-to-bottom, in numeric order, by Ethan. **One run (`v2_runNNN`) spans notebooks 02–04**:
02 creates it via `cc.start()`; 03 and 04 re-attach to it with a `RUN` variable + `cc.load()`
(same mechanism as `analyses/y2y/04_results.ipynb`'s `RUN`). The hard break between 01 and 02 is
**H7** — nothing downstream of step 0a runs until `multipart_review.csv` is signed.

### `01_prep_and_parts.ipynb` — prep, engine gates, part split → H7

- Bootstrap; imports `config, corridors_prep as cp, corridor_graph as cg, corridors_core as cc,
  corridors_ensemble as ce`; `KEY = "north"`.
- Warp the cost surface to the 300 m routing grid + **G2** (`cp.grid` / `cp.warp` / `cp.check`).
- `cg.selftest()` (**G4** in miniature + adjacency handling).
- **G1** engine equivalence on v1's own resistance (`cc.gate_g1`).
- **Step 0a**: rasterize parts at 300 m, write `node_parts.csv/.gpkg`; compute the evidence
  columns (`min_gap_cells`, `cwd_between_parts`, `intervening_nodes`, `crosses_cost_1000`, …);
  apply decision rules 1–4; write `multipart_review.csv` with the `proposed` column →
  `audit/audit_objects/`.
- **ENDS at the H7 stop**: a closing markdown cell instructs the reviewer — edit `proposed`
  where the rules got it wrong, add the `reviewed_by` line. (Absorbs cells 1–8 of the root
  notebook.)

### `02_calibrate_baseline.ipynb` — steps 0–2

- Bootstrap; **step 0** preconditions: assert `multipart_review.csv` carries `reviewed_by`;
  re-baselined **G0** (name set = 42, same 3 dedupe merges, part count, review-file hash);
  **G2 / G8** re-assert on current disk state.
- `A = cc.start(KEY, label="v2 baseline", require_cutoff=False)`; resistance diagnostics.
- **Step 1** calibrate: CWD per seed part (cache keyed by resistance hash + part-mask hash),
  intra-name MSTs locked, `calibrate_cutoff` on the inter-name MST only → `cwd_cutoff_abs` into
  `run_config.json`; report the residual vs 18,188 km².
- **Step 2** baseline: locked + inter-name MST + β = 2.5 augmentation (**G3**; **G4** read as
  "locked + inter-name MST"), criticality table, bands, `linkage_priority.tif` +
  `edge_owner.tif`, v1 compare, co-benefit audit (**G5**), maps. Edge table carries
  `edge_class`. (Absorbs cells 9–32.)

- **G15** (D19, added 2026-09-11) right after `cc.corridor_network`: `cc.gate_g15(A)` → `centrality_compare.csv`.
- **Step 2c / G17** (D21, added 2026-09-11) next: `cc.adjacency_graph(A)` → `allocation.tif`, `adjacency_edges.csv`, `adjacency_nodes.csv`, `figures/adjacency_map.png`, `is_adjacent` columns; hard assert on inter-name MST edges.

### `03_ensemble.ipynb` — step 3

- Bootstrap; `RUN = "v2_runNNN"`; `A = cc.load(...)`.
- **G7** drop-nothing member; `ce.run`: axis B {0.5, 1, 2}×, axis C 42 leave-one-out **by name**
  (all parts dropped together, incl. `no_link`), axis D β {1.5, 2.5, 4.0}; `ce.collect`.
- **G12** (47 distinct members by config-hash); write `ensemble_attribution.tif` + per-axis
  rasters (D15). Resumable — a member is done when its summary exists. (Absorbs cells 33–36.)

### `04_alternatives.ipynb` — steps 4a–4d

- Bootstrap; `RUN`; `A = cc.load(...)`.
- **Step 4a** near-optimality surface, streamed edge-by-edge from the memmaps;
  `near_opt_owner.tif`; tiers (**G10**).
- **Step 4b** route branches at `branch_mult × cwd_cutoff_abs` (**G9** hard assert);
  `branches.tif/.gpkg/.csv`; `route_irreplaceable` flags.
- **Step 4c** values table: `_to_audit` 300 m → 1 km, `audit_area_check` (**G11**),
  `mask_profile` over the imported Y2Y-wide alternatives column spec, `carroll2018_pctl`
  (H6-guarded: an absent layer logs the gap, doesn't fail) → `alternatives_branches.csv` with
  its caption.
- **Step 4d** `tiebreak.csv` (ranking only, no recommended flag).
- **Step 2b (D17, added 2026-09-03)** `cc.counterfactual_squeeze(A)` — one extra CWD set on
  the relaxed surface (cached), bands at the same cutoff, **G13**, `bands_counterfactual.gpkg`,
  D17 columns into the edge table; placed before `finish` so `corridor_edges.csv` carries them.
- `cc.finish(A)` + the `runs.csv` index. The two irreplaceability senses are reported side by
  side per §6. (Absorbs cells 37–39.)

The "decision after step 3" (whether to open Phase 7, based on axis-C stability) sits between
notebooks 03 and 04 in wall-clock terms but does **not** block 04 — steps 4a–4d are
climate-free by construction (D14).

- **Step 0b** (added 2026-09-09/11): after the re-attach, `cc.corridor_profile` + `cc.gate_g15` + `cc.gate_g5` regenerate the audit, `centrality_compare.csv`, the D21 adjacency products (G17) and G5 on the loaded run without re-running notebook 02.

### `06_tables_and_figures.ipynb` (was `06_director_package` until 2026-09-28) — the October-workshop package (added 2026-09-03)

The curated presentation set is `07_director_outputs.ipynb` (spec 06 v1.2.17, 2026-09-28: the y2y Act 1 wide layout).

Read-only over the run via `cc.load_results` + `corridors_director.py` (root module; zero new
solves): `cd.package` (disjoint D7/D12/D17 classes, axis-C attribution over PROPOSAL drops,
endpoint classes, jurisdictions, top-k example selection) → `link_profiles` (percentile
chips) → M1–M4 → profile pages → T1/T2 → draft .pptx via `director_core.build_deck`.
Outputs → `<run>/director_package/`. The squeezed class is withheld (M1/M3/S4) while
`corridor_edges.csv` lacks the D17 columns (H8 gate enforced in code). Presentation
decisions live in the 06 spec.

### `05_results.ipynb` — deliverable figures + the headline table (added 2026-08-27)

Read-only over a completed run dir via `cc.load_results` — no engine state, no CWD, no
re-attach; loads in ~a minute so figures iterate freely during writing without touching the
production pipeline (01–04). Renders the addendum-product figures into the run dir's
`figures/` — `near_opt_map` + `near_opt_tiers_map` (D11, split; IPCAs burnt orange there, the house
teal vanishes into viridis/tier greens), `attribution_map` (D15), `branches_map` (D12), and
the routing-regime set (`routing_problem_map` / `_zoom` / `_cost_zoom` / `_cost_overlay`,
M1.4/M4.6) — and writes `irreplaceability_summary.csv` (D7 flag + D12 branch count + ensemble
presence + squeeze/cost-intensity + absolute replacement cost, one row per non-adjacency
edge). Presentation only: no new estimands (the M4.6 screening index is defined in the
methods log).

### Clarifications (structural review 2026-08-21)

Three ambiguities surfaced while mapping the run sequence onto notebooks; each is a proposal to
confirm when `docs/05_methods_v2.md` is patched, not a settled decision:

1. **Multipart band/slack semantics.** §3 fixes inter-name *distance* (min over part pairs) but
   not the *field* used on an inter-name edge. Proposed: a multipart name's CWD field =
   pointwise min over its seed parts' fields (equivalent to multi-seed CWD from the part union),
   used everywhere a name-level field is needed — bands, near-optimality, branches.
2. **Intra-name edges in step 4b.** Step 4b enumerates "MST + augmentation" edges, but step 2
   declares locked `intra_name` edges real corridor land included in criticality and failure
   enumeration. Proposed: locked edges get branches too, carrying `edge_class` into
   `branches.csv` / `alternatives_branches.csv`.
3. **Tier domain.** `near_opt_tiers` percentiles are computed over the 2× union band, so cells
   outside it fall to "occasional" implicitly. Proposed: state that explicitly.

---

## 10. Deferred specs (added 2026-09-11) (kept intact for the future comparison; not part of the run)

**Step 4e (deferred) — pinch points beside squeeze (D20; Phase 6 diagnostic).** Per non-zero-cost
baseline edge: clip the O'Brien surface to the edge's band (at `cwd_cutoff_abs`, node cells
included), solve the pairwise circuit natively with node `i` cells as source and `j` cells as
ground (D20), write
`pinch_{edge_id}.tif` and mosaic to `pinch.tif` (max where bands overlap; owner in
`pinch_owner.tif`). Per edge: `pinch_max_pctl` (max current as a within-band percentile is
trivially 100 — report instead the ratio of max to median within-band current,
`pinch_concentration`), `pinch_len_km` (longest contiguous run of cells ≥ `pinch_pctl` along
the least-cost path), `pinch_loc` (fractional position of the run's midpoint along the path,
0 = node i, 1 = node j).

Then the comparison product — this is the point of "sits beside":
- `squeeze_vs_pinch.csv`: one row per edge with `squeeze_ratio_obs`, `squeezed`,
  `pinch_concentration`, `pinch_len_km`, `pinch_loc`, and a 2×2 class:
  *narrow-and-choked* / *narrow-not-choked* / *wide-but-choked* / *neither*, using
  `squeezed` and `pinch_concentration ≥ pinch_conc_thresh` (pre-registered, proposed 4.0 —
  set from the baseline distribution before reading the class counts; log the value).
- `squeeze_vs_pinch.png`: scatter of `squeeze_ratio_obs` (x) vs `pinch_concentration` (y,
  log), one point per edge, labelled, quadrant lines at the two thresholds. Flagged classes
  (D7, D12) as marker shape.
- Per-edge panel for every edge in the *wide-but-choked* and *narrow-not-choked* cells (the
  disagreements): band outline, within-band current, least-cost path, the pinch run
  highlighted. These are the cases to read, because they are where the two definitions tell
  different stories.
- One paragraph in the run report stating what the disagreements look like on the ground
  (e.g. river crossings and mountain passes produce chokes inside wide bands; long valley
  corridors squeezed by parallel linear features produce narrow bands with no choke).

Nothing in 4e feeds routing, priority, or the director legend. Whether `pinch` earns a
place in the ops package (Phase 8) is decided after this comparison is read, and logged.
