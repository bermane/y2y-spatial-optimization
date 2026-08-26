# Northern IPCAs corridor analysis (05) — full plan & status handoff

> Self-contained briefing for discussing updates. Everything a reader needs is in this document;
> no repo access assumed. Written 2026-08-21 from `docs/05_methods_v2.md`, `config.CORRIDORS`,
> and current on-disk state.

## 0. What this analysis is

A standalone least-cost corridor analysis (`05_corridors_north.ipynb`, Python) connecting the
**northern BC + Yukon protected-area / IPCA network**: 42 nodes = 10 proposed IPCAs + 32 existing
PAs (≥200 km², above 55°N for proposals). It **routes** between anchor areas — the thing the
prioritizr connectivity *penalty* in the main Y2Y-wide optimization could not do (a penalty
aggregates permeable land; it cannot answer "how does an animal get from park A to park B").

**Claim scope (important, pre-registered):** structural-connectivity hypotheses only — a robust
core vs a flexible periphery, and which links have no viable alternative. **Not**
species-movement predictions; nothing is validated against movement, genetic, or occurrence data.

**Primary deliverables:** (1) per-edge **irreplaceability flags** — links where no alternative
route exists at any reasonable cost — and (2) a graded **`linkage_priority.tif`** surface with
pre-registered tier breaks, *not* hard corridor lines (lines invite site-level readings the model
cannot support).

The eastern-slopes / grizzly / highway work is a **separate, unapproved** plan
(`docs/plan_ab_foothills_grizzly_corridors.md`); nothing here serves it.

## 1. Status snapshot (2026-08-21)

- **Engine rebuilt 2026-08-07 ("v2"). Phases 0–4 implemented; Phases 5–8 deferred.**
- Gates G0/G1/G2/G8 measured **PASS** (G1: Jaccard 1.0000 vs v1); G3/G4/G5/G7 wired as
  notebook cells / selftests.
- **The full v2 production run has not been executed yet.** On disk under
  `output_data/corridors_north/` are the v1-era outputs, the frozen v1 baseline (`_v1_frozen/`),
  and a `v2_gate_G0/` gate run — no `v2_runNNN/` baseline or ensemble yet. Consistent with that,
  `cwd_cutoff_abs` is still `None` in config (the band-cutoff calibration runs as part of the
  first real v2 pass; `resolve()` refuses to solve until it's set).
- v1 is **frozen, not deleted**: git tag `05-v1`, outputs in `_v1_frozen/`, notebook in
  `archive/`, resolved config in `configs/corridors/v1_baseline.json`. Headline v1 result for
  comparison: 42 nodes · 41 MST edges (12 zero-cost) · 1 connected component · **18,188 km²**
  new corridor land.

## 2. Why v1 was replaced

v1 built resistance as a weighted blend — Pither current density (0.50) + Carroll 2018
climate-analog current-flow centrality (0.30) + AdaptWest backward climate velocity (0.20) —
percentile-stretched, raised to `conn_exponent = 2.0`, floored at `perm_floor = 1e-3`, and
multiplied by `10 ** gHM`. Problems, per the lit review (`context_05_corridors_for_lit_review.md` §4):

1. A circuit-theory **output** (current density) was used as a routing **input** — circular, and
   it conflates pinch-point constraint with permeability.
2. **Human footprint counted three times** (gHM, current density, and centrality all encode it).
3. Climate-**analog** surfaces mixed into **movement** cost — a process mismatch.
4. Every exponent/floor was uncalibrated.
5. A bare MST has **zero redundancy** by construction — every edge a single point of failure.
6. Uniform noise on the final surface represented no identifiable uncertainty.
7. Corridor width was a *fraction of edge cost*, so band area scaled with edge cost — an
   unintended claim.

## 3. The decision log (D1–D10) — the v2 spec

| # | Decision |
|---|---|
| D1 | Resistance = the **published movement-cost surface**, not the current-density output. |
| D2 | Retire the blend entirely — no `conn_exponent`, `perm_floor`, `barrier_base`, percentile anchors, or driver weights. `resolve()` **raises** if any v1 key reappears in config (no dead flags). |
| D3 | Pither current density + Carroll 2018 become **corroboration overlays only** (Phase 6, deferred). Comparing against a product built on the same cost surface is an algorithm check, not validation. |
| D4 | Climate enters as a separate named **scenario** (a `variants` entry), never a blend weight — resist-vs-facilitate is an adaptation-philosophy choice and must be a visible axis (Phase 7, deferred). |
| D5 | Conservation values **never enter resistance**; they appear only in the post-hoc co-benefit audit. |
| D6 | Corridor band = **absolute** cost-weighted-distance cutoff, calibrated (see §6). |
| D7 | Network = MST + **bridge-backup augmentation** + per-edge centrality + removal robustness (see §7). |
| D8 | **Structured ensemble** over interpretable axes replaces uniform-noise jitter — each axis maps to a documented assumption (see §8). |
| D9 | Primary deliverable = graded **linkage-priority surface** + per-edge tables, not hard lines. |
| D10 | Two-track: this Python pipeline is research; a packaged Linkage Mapper workflow is the operational track (Phase 8, deferred, needs ArcGIS — H3). |

### Amendments made during implementation

- **A1 — the cost surface was already on disk, and it's the transboundary version.**
  `input_data/transboundary_connectivity/Movement_Cost_Layer.tif` is the **O'Brien et al.
  transboundary extension of Pither et al. 2023** — seamless US+Canada (better than the
  Canada-only original anticipated). EPSG:3347, 300 m, float32, values strictly the four
  log-spaced ordinal classes **{1, 10, 100, 1000}** (over the Y2Y bbox: 58.8 / 7.3 / 5.2 /
  28.7%). Remaining human task on it is a provenance/licence sign-off (H1).
- **A2 — routing runs at native 300 m** (overriding the project-wide 1 km grid decision *for 05
  only*). At 1 km, a two-lane highway averaged down from 90 m gHM effectively vanishes, and
  linear barriers are the signal. Verified after the warp: the cost-10 class forms genuinely
  linear features (median elongation 3.2 over the 300 largest patches, spans up to 395 km).
  300 m→300 m also means `nearest` resampling preserves the four classes exactly — no
  averaging/mode rule to defend.
- **A3 — D7 as originally drafted was vacuous.** "Keep any direct edge with cost ≤ α ×
  MST-path cost" admits **all 861 node pairs**: least-cost distance obeys the triangle
  inequality, so direct cost never exceeds tree-path cost. `alpha` is retired; replaced by
  bridge backup with a β ceiling (§7).
- **A4 — the terrain null (Phase 5) has no data**: no DEM anywhere in `input_data/` (H5).

## 4. Two grids — a correctness requirement, not an optimization

**Routing at 300 m; the co-benefit audit at 1 km.**

- Working grid after the anchor crop: 2,809 × 5,767 ≈ 16.2 M cells; routable area
  **872,725 km²** (vs v1's 751,614 km²).
- **CWD can't be held in memory** at 300 m (~200 MB/field × 42 nodes ≈ 8.3 GB), so
  cost-weighted-distance fields are computed once and cached as **float32 memmaps** keyed by
  resistance identity (`input_data/corridors_300m/cwd_cache/<sha>/`); band construction streams
  only the two fields an edge needs.
- **A 300 m audit would silently overstate contribution ~11×**: `results_core.mask_profile`
  sums a feature over the mask while the "% of Y2Y" denominator is computed at the layer's
  native 1 km with no finer-than-source path — a 300 m mask sums ~11 replicated cells per
  source cell. Every value layer is natively 1 km anyway. So masks are built at 300 m and
  crossed to 1 km (`_to_audit`, areal fraction ≥ 0.5) only for profiling; `audit_area_check`
  reports the area discrepancy across that boundary.

**Incidental finding with implications beyond 05:** v1's routable area was a strict subset of
v2's because v1 inherited the prioritizr planning-unit mask, which is set by the
`irrecoverable_carbon_biomass` layer's footprint (1,274,564 km² vs ~1,551,000+ km² for every
other layer over a 1,551,654 km² buffered study area). So **~18% of the study area is excluded
from every prioritizr solve (03/04/06) by one layer's coverage**. Flagged, not acted on; moot
for 05 since routing uses the cost surface's own footprint.

## 5. Nodes

From `config.CORRIDORS["north"]["nodes"]`: proposed IPCAs above 55°N + existing PAs ≥ 200 km²
in the region; minimum node size 25 km² (replaces v1's resolution-dependent 25-*cell* rule);
dedupe merges two nodes only when rasterized masks overlap ≥ 50% of the smaller node — catches
the same place entered twice under nesting designations (Teetł'it Gwinjik inside the Peel
Watershed SMA/WA; Fishing Branch Wilderness Preserve inside its Habitat Protection Area) while
keeping an IPCA that merely *wraps* a park separate. Result: 42 nodes (10 IPCA + 32 PA), same
three dedupe merges as v1 (gate G0).

## 6. Corridor band (D6)

Per edge, keep cells whose `CWD_i + CWD_j` is within **`cwd_cutoff_abs` cost units** of that
edge's least-cost minimum — no dependence on edge cost. The cutoff is **calibrated, not
guessed** (`calibrate_cutoff`, pre-registered as `{"target_km2": 18188, "edges": "mst"}`): it
reproduces v1's 18,188 km² of MST-only corridor area on the new resistance, same edge set and
same `& ~node_union` area definition, so v1↔v2 route comparisons aren't confounded by band
size. Augmentation area is reported separately — calibrating against the augmented network
would let the cutoff absorb the augmentation and conflate D6 with D7.

## 7. Network topology (D7 as amended)

**MST + sequential bridge-backup augmentation with a cost-ratio ceiling.** Chosen over a
t-spanner (bounds stretch — efficiency, not robustness — and can leave a peripheral node as a
single point of failure) and over unconditional backup.

1. **Sequential, descending criticality, with recomputation** — one added edge typically retires
   several bridges at once (any cycle it closes covers every tree edge on that cycle), so
   independent per-bridge processing would overcount additions. Standard greedy heuristic for
   minimum-cost 2-edge-connectivity augmentation; trivial at n=42.
2. **β = 2.5** (default): add the cheapest restoring edge only when
   `backup_cost ≤ β × failed_edge_cost`. Adding one unconditionally would route "alternatives"
   through land so resistant nobody would treat them as real — that hides irreplaceability
   rather than creating redundancy.
3. **Links where nothing clears the ceiling are flagged IRREPLACEABLE — the headline output.**
4. Spanner stretch is reported as a diagnostic, never used as a selection criterion.

**Zero-cost "adjacency" edges (12 of 41)** — node pairs that already touch, chiefly Dene Kʼéh
Kusān wrapping 11 BC parks:

- Kept as graph edges contributing **no corridor land** (no corridor to build between touching
  areas; also preserves v1's area semantics for the D6 calibration).
- **Centrality is computed on the quotient graph** (zero-cost cliques contracted, then mapped
  back) — infinite conductance between two nodes *is* a merged node; correct physics. The
  contraction is computation-scoped only; the data model, banding, audit, and leave-one-out
  keep nodes distinct.
- Excluded from failure enumeration and backup candidacy — their failure mode is the *node*
  disappearing, which leave-one-out covers.
- Flooring the cost is explicitly rejected (would invent fictional corridor land between
  abutting polygons).
- **Reporting caveat:** "no corridor needed between touching areas" holds only *conditional on
  the IPCA proposals being realized* — most adjacencies hang off proposal polygons drawn for a
  process still under way. State plainly.

## 8. Linkage priority surface (D9)

`priority = max_e (ecfb_raw_e × (1 − slack_e / cutoff))` — **max, not sum**, so overlap regions
aren't inflated purely by edge redundancy and every cell keeps a single owning edge
(`edge_owner.tif`). Tier breaks are percentiles of the non-zero surface, **pre-registered in
config before the run**: robust_core = p90, frequent = p70, occasional = rest.

## 9. Structured ensemble (D8)

| axis | question | design | status |
|---|---|---|---|
| A | component cost perturbation — how sensitive is the surface itself? | needs perturbation ranges from reading the O'Brien/Pither code | **deferred (H2)** |
| B | band cutoff × {0.5, 1, 2} | how wide is a corridor? | implemented |
| C | node leave-one-out, one run per node | what is contingent on a single unrealized proposal? | implemented |
| D | β sweep {1.5, 2.5, 4.0} | what counts as a viable alternative? | implemented |

CWD depends only on (resistance, node seeds); B and D touch neither, and C deletes a
row/column from the distance matrix while leaving every remaining field bit-identical — so the
**whole ensemble reuses one cached CWD set**; each member is a graph rebuild + band
re-derivation. Runs serial with memmaps deliberately (GIL-bound pure-Python `MCP_Geometric`;
process workers would only multiply resident grids). Robust-core frequency threshold 0.9.

**Attribution is the point**: a jitter ensemble says "this cell was used 60% of the time"; this
says *which assumption* the other 40% depends on. **Axis C is the one to read closely** — the
network is anchored on unrealized proposals.

## 10. Gates (inline asserts + named notebook cells; no pytest in the repo)

| gate | invariant | status |
|---|---|---|
| G0 | node set unchanged after the 300 m switch — 42 nodes, same 3 dedupe merges | **PASS** |
| G1 | new engine on **v1's own resistance and grid** (MST-only, relative band) reproduces v1's corridor | **PASS — Jaccard 1.0000**, 41 edges (12 zero-cost), 18,188 km² |
| G2 | warp fidelity — CRS, shape, extent, `unique(values) ⊆ {1,10,100,1000}` | **PASS** |
| G3 | raster flood-fill vs graph component count agree | wired in |
| G4 | β = 0 reproduces the MST exactly; MST ⊆ augmented | selftest |
| G5 | v1's IPCA/PA profile rows reproduce — equivalence-checks the whole audit path | notebook cell |
| G7 | drop-nothing leave-one-out member reproduces the baseline exactly | `ce.gate_g7` |
| G8 | `resolve()` raises on every retired v1 config key | **PASS** |

**G1 is the one that matters**: every other v2 change moves the answer *on purpose*, so G1
isolates the refactor from the semantic changes. It also catches the two preserved traps:
scikit-image's `find_costs` returns MCP's internal buffer (must copy), and `mcp.traceback`
reads whichever `find_costs` ran **last** — a mis-grouped optimization silently returns paths
from the wrong source node with no exception.

**Timing, measured:** the full 42-node CWD set at 1 km takes ~12 s, so 300 m (7.4× cells) is
minutes, not the ~45 min budgeted. Caching matters for the ensemble, not a single run.

## 11. Run convention & outputs

`config.CORRIDORS["north"]` is the editable baseline; `cc.start()` resolves it, writes
`run_config.json` (resolved params + git SHA + config hash + input hashes + GDAL version) into
`output_data/corridors_north/v2_runNNN/`, and the engine thereafter reads **only** that file —
same doctrine as the ensemble runner elsewhere in the project ("patch a copy, never mutate
config.py"). Provenance is load-bearing because `output_data/` is gitignored. Per-run outputs:
`corridor_summary.json` (also the ensemble resumability sentinel), `resistance.tif`,
`corridors.tif/.gpkg`, `linkage_priority.tif`, `linkage_priority_class.tif`, `edge_owner.tif`,
`corridor_edges.csv/.gpkg`, `criticality.csv`, `corridor_profile.csv`, `figures/`, `ensemble/`.

Modules: `corridors_prep.py` (one-off warp + G2) · `corridor_graph.py` (raster-free graph:
MST, augmentation, quotient-graph centrality, criticality, `selftest()`) · `corridors_core.py`
(grid, nodes, CWD cache, bands, priority surface, audit, maps) · `corridors_ensemble.py`.

## 12. Deferred phases & human tasks

| item | blocked on |
|---|---|
| Phase 1.4 vintage diff | H4 + OlmoEarth / Sims layers (not in repo) |
| Phase 4 ensemble axis A | **H2** — perturbation ranges need a read of the O'Brien/Pither code |
| Phase 5 terrain null | **H5** — no DEM in `input_data/` |
| Phase 6 corroboration overlays (Pither current density, Carroll 2018) | Phases 1–4 landing |
| Phase 7 climate scenario (attaches to `variants`) | functional form needs review |
| Phase 8 ops package + Linkage Mapper equivalence | **H3** (ArcGIS); outputs must carry Dublin Core+ metadata at creation for the separate catalogue repo |
| H1 | licence/provenance sign-off on the O'Brien cost surface |

Also outstanding: consolidate three `_jaccard` implementations across `corridors_core` /
`scenario_core` / `ensemble_core` — deliberately deferred until an empty-set-denominator
equivalence is verified against the archived 130-run Morris batch.

## 13. Relationship to the rest of the project

- 02/03/04/06 (the prioritizr pipeline and the flagship frequency-ensemble campaign in
  `analyses/y2y/`) are **unaffected** and stay at 1 km; 05 has its own grid namespace
  (`input_data/corridors_300m/`) and never enters `aligned_stack/` or the manifest.
- The cost surface is deliberately NOT in `config.DATASETS` — it's not a prioritizr feature,
  it's unoriented (higher = worse), and registering it would corrupt the shared PU mask.
- A previously deferred idea — expanding the northern network with prioritizr "new-area
  headroom" (~11k km², budget_pct 0.43) — waits on a working Gurobi licence for near-optimal
  portfolios (currently blocked by an 8-core cap on the WLS licence).

## 14. Natural discussion points for updates

1. **Running the v2 baseline + ensemble** — the engine is built and gated but the production
   run (calibration → baseline → axes B/C/D) hasn't been executed.
2. Whether to unblock **axis A** (H2) and what defensible perturbation ranges on a 4-class
   ordinal cost surface look like.
3. **Phase 7 climate scenario** functional form (resist vs facilitate as named variants).
4. Whether Phase 6 corroboration overlays add anything given the circularity caveat (D3).
5. The **β = 2.5 default** and the {1.5, 2.5, 4.0} sweep — is the ceiling range defensible?
6. Pre-registered **priority tier breaks** (p90/p70) — presentation vs pre-registration.
7. The **carbon-biomass PU-mask finding** (§4) — whether/how to act on it project-wide.
