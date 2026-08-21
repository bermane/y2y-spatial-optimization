# 05 Corridors — methods (v2)

**Status:** engine rebuilt 2026-08-07. Phases 0–4 implemented; Phases 5–8 deferred (see the end).
**Scope:** northern BC + Yukon PA/IPCA network. The eastern-slopes / grizzly / highway-crossing work
is a separate analysis (`docs/plan_ab_foothills_grizzly_corridors.md`); nothing here is built for it.

**Claim scope.** Structural-connectivity hypotheses: a robust core versus a flexible periphery, and
which links have no viable alternative. **Not** species-movement predictions. Nothing is validated
against movement, genetic or occurrence data.

---

## 1. What v1 was, and why it was replaced

v1 built resistance as a weighted blend of three regional products — Pither current density (0.50),
Carroll climate-analog current-flow centrality (0.30), AdaptWest backward climate velocity (0.20) —
percentile-stretched, raised to `conn_exponent = 2.0`, floored at `perm_floor = 1e-3`, and
multiplied by `10 ** gHM`. Corridor bands were a fraction of edge cost; the network was a bare MST;
uncertainty came from multiplying the final surface by uniform noise.

`docs/context_05_corridors_for_lit_review.md` §4 sets out the problems. In short: a circuit-theory
*output* was used as a routing *input*; human footprint was counted three times (gHM, current
density and centrality all encode it); climate-**analog** surfaces were mixed into **movement**
cost, which is a process mismatch; every exponent was uncalibrated; an MST has zero redundancy by
construction; and uniform noise on a final surface represents no identifiable uncertainty.

**v1 is frozen**, not deleted: git tag `05-v1`, outputs in `output_data/corridors_north/_v1_frozen/`,
notebook at `archive/05_corridors_north_v1.ipynb`, resolved config at
`configs/corridors/v1_baseline.json`. Headline v1 result, for comparison:

> 42 nodes (10 IPCA + 32 PA) · 41 MST edges, 12 of them zero-cost · 1 connected group ·
> **18,188 km²** of new corridor land · robust core 14,066 of 22,846 km² ever used.

---

## 2. Decision log

| # | Decision | Rationale |
|---|---|---|
| D1 | Resistance = the published movement **cost surface**, not the current-density output | Current density is a derived flow quantity: circular as an input, and it conflates pinch-point constraint with permeability. |
| D2 | Retire the blend entirely — no `conn_exponent`, `perm_floor`, `barrier_base`, percentile anchors, driver weights | The cost surface already encodes footprint and roads at better thematic resolution than gHM; the blend triple-counted footprint and mixed process-mismatched layers. |
| D3 | Pither current density + Carroll 2018 become **corroboration overlays only** | Comparison against a product built on the same cost surface is an algorithm check, not validation. *(Phase 6, deferred.)* |
| D4 | Climate enters as a separate named **scenario**, never a blend weight | Resist-vs-facilitate is an adaptation-philosophy choice and must be a visible axis. *(Phase 7, deferred; attaches to `variants`.)* |
| D5 | Conservation values never enter resistance | Category separation: resistance is movement cost; values enter only the post-hoc audit. |
| D6 | Corridor band = **absolute** cost-weighted-distance cutoff | A relative width made corridor area scale with edge cost — an unintended claim — and blocked equivalence with an operational Linkage Mapper run. |
| D7 | Network = MST + **bridge-backup augmentation**, per-edge centrality, removal robustness | A bare tree has zero redundancy; every edge is a single point of failure. |
| D8 | **Structured ensemble** over interpretable axes replaces uniform-noise jitter | Each axis must map to a documented assumption. |
| D9 | Primary deliverable = graded **linkage priority surface** + per-edge tables, not hard lines | Lines invite site-level readings the model cannot support. |
| D10 | Two-track: this Python pipeline is research; a packaged Linkage Mapper workflow is operational | *(Phase 8, deferred.)* |

### Amendments made during implementation

**A1 — the cost surface was already on disk, and it is the transboundary version.**
`input_data/transboundary_connectivity/Movement_Cost_Layer.tif` shipped in the same download as
`Raw_CurrentDensity_Map.tif` and was never registered in `config.DATASETS`. It is the **O'Brien
et al. transboundary extension of Pither et al. 2023** — seamless US + Canada, i.e. better than the
Canada-only original H1 anticipated. EPSG:3347, 300 m, float32, values strictly `{1, 10, 100, 1000}`.
H1 therefore reduces to a provenance/licence sign-off.

**A2 — routing runs at native 300 m.** This overrides the rebuild plan's "out of scope: 300 m
northern regridding", and supersedes `CLAUDE.md`'s 1 km grid decision **for 05 only** (02/03/04/06
stay at 1 km). Rationale: at 1 km a two-lane highway averaged down from 90 m gHM effectively
vanishes, and linear barriers are the signal. It also dissolves the resampling question — at
300 m → 300 m, `nearest` preserves the four ordinal classes exactly, so no averaging, mode or
geometric-mean rule has to be defended.

*Verified after the warp:* the cost-10 class forms genuinely linear features (median elongation 3.2
over the 300 largest patches, spanning up to 395 km), confirming that roads and rail survive at this
grain.

**A3 — D7 as originally drafted was vacuous.** "Retain any node-pair direct edge with cost ≤ α ×
MST-path cost" admits **all** 861 pairs: least-cost distance obeys the triangle inequality, so the
direct cost is never greater than the tree-path cost. `alpha` is retired. See §4.

**A4 — Phase 5's terrain null has no data.** There is no DEM anywhere in `input_data/`;
`elevational_diversity/` is an unextracted `.7z` of a derived diversity metric, not slope or
ruggedness. New human task **H5**.

---

## 3. Grids — and why there are two

**Routing at 300 m; the co-benefit audit at 1 km.** This is a correctness requirement, not an
optimisation.

| | @1 km (v1) | @300 m (v2) |
|---|---|---|
| warped northern window | — | 4,285 × 5,767 = 24.7 M cells |
| working grid after the anchor crop | 1,286 × 1,730 = 2.2 M | 2,809 × 5,767 = 16.2 M |
| routable cells | 751,614 km² | **872,725 km²** |

Two consequences drove the design:

1. **CWD cannot be held in memory.** One field is ~200 MB in float64 at 300 m, so 42 nodes would be
   8.3 GB. Fields are computed once and cached as float32 memmaps keyed by resistance identity;
   band construction streams only the two an edge needs.
2. **A 300 m audit would silently overstate contribution ~11×.** `results_core.mask_profile`
   computes `sum(feature over mask) / region_total`, while `results_core._region_total` computes the
   denominator at the layer's native 1 km with no finer-than-source path (only a coarsening `agg`).
   Profiling a 300 m mask would sum ~11 replicated cells per source cell against a 1 km denominator.
   Every value layer is natively 1 km, so upsampling adds no information anyway.

So masks are built and segmented at 300 m and crossed to 1 km (`_to_audit`, areal fraction ≥ 0.5)
only for profiling. `results_core` is untouched, which is what makes gate **G5** meaningful.
`audit_area_check` reports the area discrepancy across that boundary rather than letting it pass
unnoticed — the majority threshold is area-conserving for corridors several km wide but not for
sub-kilometre ones.

### An incidental finding, with implications beyond 05

v1's routable area was a **strict subset** of v2's: the cost surface covers 126,250 km² (17%) more
of the northern window and misses nothing. The cause is that v1 inherited the prioritizr **planning-unit
mask**, which 02 defines as cells valid in *all* continuous features. Checking the pre-mask
intermediates in `input_data/cleaned_aligned/`:

| layer | coverage of the buffered study area |
|---|---|
| `irrecoverable_carbon_biomass` | **1,274,564 km²**  ← binding |
| `irrecoverable_carbon_m_soc` / `sl_soc` | 1,355,145 km² |
| every other continuous feature | ~1,551,000–1,557,000 km² |
| `study_area(20 km)` polygon | 1,551,654 km² |

So the whole project's PU mask (1,272,914 km²) is set by the irrecoverable-carbon biomass layer's
footprint, at a cost of ~280,000 km² (18%) of the buffered study area. For 05 this is now moot —
routing uses the cost surface's footprint, since nothing about carbon or bird richness constrains
where an animal can walk. **But it also applies to 03/04/06**, where every prioritizr solve is
confined to where that one layer has data. Flagged, not acted on; out of scope for this rebuild.

---

## 4. Network topology (D7, as amended)

**Bridge backup with a cost-ratio ceiling**, chosen over the two alternatives because it is the only
one whose acceptance condition *is* D7's stated motivation. A t-spanner bounds stretch — an
efficiency property, not robustness — and can leave a peripheral node untouched, so the
single-point-of-failure problem would survive the fix. Bridge backup also gives the criticality
table a one-to-one story per added corridor, which matters when every retained edge becomes mapped
land someone is asked to care about.

1. **Sequential, in descending criticality, with recomputation.** One added edge typically retires
   several bridges at once — any cycle it closes covers every tree edge on that cycle — so
   processing bridges independently would overcount additions and misstate which failure each edge
   insures. This is the standard greedy heuristic for minimum-cost 2-edge-connectivity augmentation.
2. **Cost-ratio ceiling β** (default 2.5): add the cheapest restoring edge only when
   `backup_cost ≤ β × failed_edge_cost`. Adding one unconditionally would route "alternatives"
   through land so resistant nobody would treat them as real — that does not create redundancy, it
   **hides irreplaceability**.
3. **Irreplaceability flags are the headline output.** The augmented graph says where alternatives
   exist; the flags say where Y2Y cannot afford to lose the land at any reasonable price.
4. **Spanner stretch is reported as a diagnostic** — worst-case detour under no failures — but never
   used as a selection criterion.

### Adjacency (zero-cost) edges — 12 of 41

Node pairs that already touch, chiefly Dene Kʼéh Kusān wrapping 11 BC parks and clipping each by a
2–63 km² sliver.

- **Kept as graph edges, contributing no corridor land.** There is genuinely no corridor to build
  between areas that already touch; this also reproduces v1's area semantics, so the D6 calibration
  stays comparable.
- **Centrality is computed on the quotient graph** with zero-cost cliques contracted, then mapped
  back. Infinite conductance between two nodes *is* a merged node — correct physics, not a numerical
  nuisance. A finite cap would approximate the same limit while adding an arbitrary constant and an
  ill-conditioned Laplacian. The contraction is **computation-scoped only**: the data model,
  banding, audit and leave-one-out keep the nodes distinct, so the 2026-08-05 dedupe decision
  (merge only on ≥50% mask overlap, so a wrapping neighbour stays separate) is untouched.
- **Excluded from failure enumeration and backup candidacy.** An adjacency has no corridor land
  whose loss could sever it; its failure mode is the *node* disappearing, which leave-one-out covers.
  The criticality table carries them as a distinct class.
- **Flooring the cost is explicitly rejected**: it would invent corridor land between abutting
  polygons — fictional deliverable area — to buy code uniformity.
- **Caveat for reporting:** "no corridor to build between touching areas" holds *only conditional on
  the proposals being realized*. Twelve free adjacencies, most hanging off proposal polygons, is a
  network property inherited from lines drawn for a process still under way. State it plainly rather
  than letting zero-cost edges read as settled geography.

---

## 5. Uncertainty (D8)

| axis | question | status |
|---|---|---|
| **A** component cost perturbation | how sensitive is the surface itself? | deferred, **H2** |
| **B** band cutoff × {0.5, 1, 2} | how wide is a corridor? | implemented |
| **C** node leave-one-out (one run per node) | what is contingent on a single unrealized proposal? | implemented |
| **D** β sweep {1.5, 2.5, 4.0} | what counts as a viable alternative? | implemented |

Cost-weighted distance depends only on (resistance, node seeds). B and D touch neither; C drops a
node, deleting a row and column from the distance matrix while leaving every remaining node's field
bit-identical. So the whole ensemble reuses **one** cached CWD set and each member is a graph
rebuild plus a band re-derivation. Serial with memmaps, deliberately — 05 is GIL-bound pure-Python
`MCP_Geometric`, so process workers would only multiply resident grids.

Attribution is the point: a jitter ensemble could say only "this cell was used 60% of the time",
whereas this says *which assumption* the other 40% depends on. **Axis C is the one to read closely.**

---

## 6. Gates

No pytest in this repo; the discipline is inline asserts plus named gates run as notebook cells.

| gate | what it holds invariant | status |
|---|---|---|
| **G0** | node set unchanged after the 300 m switch — 42 nodes (10 IPCA + 32 PA), same three dedupe merges | **PASS** |
| **G1** | new engine on **v1's own resistance and grid**, MST-only + relative band, reproduces v1's corridor | **PASS — Jaccard 1.0000**, 41 edges (12 zero-cost), 18,188 km² |
| **G2** | warp fidelity — CRS, shape, extent, and `unique(values) ⊆ {1,10,100,1000}` | **PASS** |
| **G3** | raster flood fill and graph component count agree | wired into `corridor_network` |
| **G4** | β = 0 reproduces the MST exactly; MST ⊆ augmented | in `cg.selftest` |
| **G5** | v1's IPCA / PA profile rows reproduce — equivalence-checks the whole audit path | notebook cell |
| **G7** | a drop-nothing leave-one-out member reproduces the baseline exactly | `ce.gate_g7` |
| **G8** | `resolve()` raises on every retired v1 config key | **PASS** |

**G1 is the one that matters.** Every other v2 change moves the answer on purpose, so
"re-run and expect the same corridors" is unavailable; G1 instead isolates the *refactor* from every
*semantic* change. It also catches the `mcp.traceback` trap: tracebacks read whichever `find_costs`
ran last, so a mis-grouped optimisation silently returns paths from the wrong source node — no
exception, plausible-looking output.

Timing, measured: the full 42-node CWD set at 1 km takes ~12 s, so 300 m (7.4× the cells) is
minutes, not the ~45 min budgeted. Caching still matters for the ensemble, not for a single run.

---

## 7. Run convention

`config.CORRIDORS["north"]` is the editable baseline. A run resolves it, writes the resolved dict
plus provenance to `run_config.json` in its own directory, and thereafter reads only from that file
— the same doctrine as `ensemble_core`'s "patch a copy of the manifest, never mutate config.py".
The provenance block (git SHA, config hash, input file hashes, GDAL version) is load-bearing because
`output_data/` is gitignored: the run directory is the only record that survives.

```
output_data/corridors_north/
  _v1_frozen/                     the frozen v1 baseline
  v2_run001/
    run_config.json               resolved params + provenance (the engine's only input)
    corridor_summary.json         also the ensemble's resumability sentinel
    resistance.tif  corridors.tif  corridors.gpkg
    linkage_priority.tif  linkage_priority_class.tif  edge_owner.tif
    corridor_edges.csv  corridor_edges.gpkg  criticality.csv  corridor_profile.csv
    figures/  ensemble/
  runs.csv
```

`resolve()` **raises** on any surviving v1 key (`drivers`, `conn_exponent`, `perm_floor`, `barrier`,
`corridor_width_frac`, `scenarios`, `alpha`, `node_min_cells`, …) — the enforcement of D2's "no dead
flags", and it stops a stale `config.py` producing a run that looks fine but was configured for the
v1 engine.

---

## 8. Deferred

| item | blocked on |
|---|---|
| Phase 1.4 vintage diff | **H4** + OlmoEarth / Sims layers, not in this repo |
| Phase 4 axis A | **H2** — perturbation ranges are a judgment call after reading the O'Brien/Pither code |
| Phase 5 terrain null | **H5** — no DEM in `input_data/` |
| Phase 6 corroboration overlays | Phases 1–4 landing |
| Phase 7 climate scenario | functional form needs review; attaches to `variants` |
| Phase 8 ops package + Linkage Mapper equivalence | **H3** (ArcGIS). The Dublin Core+ catalogue lives in a separate repo (`~/Dropbox/Earthline/Y2Y/Spatial_Data/`), so 05 outputs must carry title / summary / description / tags / terms_of_use / acknowledgements at creation time |

Also outstanding: consolidate the three `_jaccard` implementations
(`corridors_core`, `scenario_core`, inlined in `ensemble_core`). Deliberately **not** done yet — a
130-run Morris batch sits in `output_data/morris` and `ensemble_core.add_baseline_metrics` uses a
different empty-set denominator, so the equivalence needs verifying before the call sites move.
