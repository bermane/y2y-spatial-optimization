# Methods log — wolverine refugia connectivity (living document)

**Purpose.** The cumulative record of every methods-relevant decision, data manipulation and fix in
this analysis, in enough detail to write the methods section without archaeology. Each entry carries
what was done, exact parameters, the justification and where it is implemented.

**Maintenance rule (binding on every working session):** any change that alters the data, the
formulation, a parameter or a QA rule gets an entry HERE in the same session it is made — including
reversals. Supersessions are marked, never deleted.

Companion documents: **`results_log.md`** (the RESULTS register, same rule); `wolverine_refugia_connectivity_spec.md`
(decisions W1–W10); `06_wolverine_director_package_spec.md`; the northern methodology this analysis mirrors
(`docs/05_methods_v2.md`, `analyses/northern_connectivity/spec/…`).

---

## 1. Claim scope and study system

- **M1.1 Claim scope (pre-registered, 2026-09-28):** structural connectivity between wolverine climate
  refugia patches on a published movement-cost surface; NOT a wolverine movement model (expert-assigned,
  species-agnostic resistance apart from W1; a climate-envelope refugia product; no validation against
  movement or genetic data). "Corridor" = the bands/branches of this engine.
- **M1.2 Study system:** the whole Y2Y region (buffered 20 km cutline; routes cannot leave it), routed
  on a 300 m ESRI:102008 grid = the northern engine's grid convention with no latitude cut
  (`grid.region_filter = None`), own namespace `input_data/corridors_300m_y2y/`. ≈ 4,285 × 11,040 cells,
  17.2 M routable (measured in R1).
- **M1.3 Two grids:** routing at 300 m; the 1 km co-benefit audit is PARKED (spec §7), so no crossing
  happens in this pass.

## 2. Resistance surface

- **M2.1 Baseline = the published O'Brien et al. 2025 transboundary surface** (US extension of Pither
  et al. 2023), warped `-r near` onto the routing grid (G2), classes {1, 10, 100, 1000} preserved.
- **M2.2 The source's class rules (from Pither et al. 2023, PLOS ONE 18:e0281980, S1 Table, retrieved
  2026-09-28):** per-pixel MAXIMUM over 23 layers; 1000 = built environments, nighttime lights, mining,
  oil & gas, dams, rails, multi-lane highways, elevation > 2,300 m and slope > 30° (GMTED2010), glaciers
  (CanVec 2017), lakes ≥ 10 ha (HydroLAKES), rivers > 28 m³/s (HydroRIVERS), ocean; 100 = croplands,
  two-lane highways; 10 = pasturelands, minor roads, forestry cut 1985–2015, sea ice; 1 = everything else
  and no-data. The US extension mirrors the tiers (Global Human Footprint layers; a 500 m road buffer at
  100) and reuses the Canadian surface unchanged. This closes the northern log's open item H1 on what
  cost 1000 encodes.
- **M2.3 Variant "O'Brien 2025, generic terrain rules withheld" (W1; the surface the campaign runs on;
  chat ruling 2026-09-28, amended by Ethan the same day so that all three terrain rules are withheld
  EQUALLY — glaciers to 1, not 10).** Withheld: elevation > 2,300 m, slope > 30°, glaciers. Everything
  else retained; 10 and 100 bands untouched; recompute-the-maximum semantics (a terrain cell under a
  retained layer keeps 1000). Rationale in the spec (W1). Implemented as the named variant
  `variants["terrain_withheld"]` passed as `overrides` to `cc.start` (D4 doctrine: a visible named
  scenario, never a blend); the published surface stays the config baseline.
- **M2.4 Implementation by proxy (W1a, disclosed):** the source's 23 layers are not in the repo.
  `corridors_prep.terrain_layers` rasterizes onto the routing grid: `elev_gt` (DEM > 2,300 m; DEM =
  `basemap/dem_y2y_300m.tif` `reproject_match` bilinear — the source's GMTED2010 is ~250 m, the same
  grain; GMTED used instead if present in `input_data/dem_gmted/`), `slope_gt` (`np.gradient` slope in
  degrees on that DEM > 30°), `glacier` (RGI 7.0 regions 01 + 02, any-overlap rasterization), `lake`
  (HydroLAKES `Lake_area` ≥ 0.10 km², cell-centre rasterization), `river` (HydroRIVERS `DIS_AV_CMS` > 28,
  line rasterization), `ocean` (routable cells outside the Natural Earth admin-1 land polygons),
  `ghm90max` (`gdalwarp -r max` of the 90 m Theobald gHM v3 to 300 m). `calibrate_human_tau`: τ on
  `ghm90max` maximising balanced accuracy between the cost-1000 cells explained by NO natural layer
  ("human 1000") and the cells below 1000 (reported with the confusion table; no assert).
  `derive_variant`: `out = cost; out[cost == 1000 & terrain & ¬retained] = 1` with `retained = lake |
  river | ocean | ghm90max ≥ τ`; GW2 asserts the change set. Sub-1000 layers under withheld terrain are
  taken as 1 (disclosed). Meta → `movement_cost_terrain_withheld.tif.meta.json`, hash-pinned in
  `run_config.json` (`inputs.resistance_variant`).
- **M2.5 Withdrawn:** the ad hoc floor "gHM < 0.05 and elevation ≥ 1,500 m" drafted 2026-09-28 before the
  source rule was retrieved (the 1,500 m was a data cut on where the cost-1000 class turns natural, not
  a biological threshold). Superseded by M2.3/M2.4 the same day; never run.
- **M2.6 Off-corridor cells are impassable (inf)** — inherited (M2.3 north).

## 3. Node assembly

- **M3.1 Nodes from a raster (W2):** `corridors_core._raster_nodes` — the refugia raster warped `-r near`
  (Byte, nodata 255) onto the routing grid (GW1); core = classes {2, 12} ∧ routable; 8-connected
  components (`ndimage.label`, 3 × 3); patches ≥ **250 km²** (`node_min_km2`; 2,778 cells) are the nodes — SUPERSEDES
  the 500 km² floor of the first build (Ethan 2026-09-28, after check stop 1: 500 km² captured 81.7% of core in 67 nodes;
  250 km² captures 88.8% in 130; the ladder and the compute per step are in results_log R3);
  no morphological closing. Numbered north → south by centroid row. One boolean array per node (the
  mask is the seed part AND the routing unit — `_apply_parts` aliases instead of copying).
- **M3.2 The model seam (W4):** values 10/11/12 come from the northern source model, 0/1/2 from the
  southern; classes are merged (core = {2, 12}, marginal = {1, 11}) and components may span the seam.
  The class split either side of the seam (middle-column latitude 53.97 °N) is reported (GW1,
  `refugia_summary.json`). Classes 0 and 10 are simply not refugia (Ethan 2026-09-28) and are never labelled on any output; the source citation is deferred.
- **M3.3 Naming (W9):** PA (`PA_VECTOR` dissolved by name, ≥ 1 km²) with the largest overlap when it
  covers ≥ 10% of the patch, else the nearest PA + 8-point bearing; labels `Refugium · R{id:02d} <name>`;
  human overrides via `audit/audit_objects/node_names.csv` (`display_name`), copied + sha-pinned into the
  run (`_NODE_FILES`), fingerprint-checked (GW3: node_id, cell count, lat/lon to 3 dp).
- **M3.4 D16/H7 not applicable (W7):** `cc.node_patches` writes the H7-format `node_parts.csv/.gpkg`
  (one `shapes()` pass over the `node_id` grid) + `node_names.csv` + `refugia_summary.json`; no review;
  `new_run(require_review=False)`. `_grid_nodes` (vector nodes) is untouched; `load` dispatches on
  `nodes.source`.
- **M3.6 Protected land as a STATUS layer (W11, Ethan 2026-09-28):** `_raster_nodes` rasterizes every
  existing PA (`protected_pa`) and every proposed IPCA/PA (`protected_ipca`, `PROPOSED_PA_VECTOR`, taken as
  given) onto the routing grid; neither enters resistance (D5) or the node set. `secured_status(A)` (after
  `corridor_network`) computes per separated link the centre-line share inside nodes + PAs and inside
  nodes + PAs + IPCAs, the band's new land inside each, `band_unprotected_km2`, and `secured_by` ∈ {pa, ipca,
  ""} at the pre-registered threshold `secured_centreline_frac` = 0.95; `A.corridor_unprotected` = corridor
  ∧ ¬protected is written as `corridors_unprotected.tif`; columns land in `corridor_edges.csv` /
  `criticality.csv`; the summary carries `corridor_unprotected_km2`, `n_secured_by_pa`, `n_secured_by_ipca`.
  Presentation modes in the package spec (§1). Routing, classes and the priority surface are untouched.
- **M3.5 Existing PAs are context, never nodes:** `context_pa` (PAs ≥ 200 km²) is drawn by the engine
  map and the package as outlines; it is kept OUT of `_node_masks` (which `corridor_profile` uses to cut
  segments).

## 4. Network formulation

- **M4.1 Band cutoff inherited (W5):** `cwd_cutoff_abs = 13.622951589524746` from `north/v2_run002`
  (same grid, same cost units ⇒ ≈ 4 km detour allowance); pinned with `set_cutoff`, `calibration =
  {inherited_from: north/v2_run002}`; `calibrate_cutoff` never called.
- **M4.3 Link classes mirrored from the north (W12; 2026-09-28, the same day the north adopted D23–D25):** `cc.classify_links` is
  the one derivation of `link_class` for this analysis too — precedence adjacency → near-contiguous (D25: `lcp_len_cells <
  open_ground_width_med`; barrier variant when a cost-1000 cell sits on the path) → width not assessable (D24: barrier-free median
  width < 8 cells or path < 10 cells; classed on the alternative-link sense alone) → only viable connection (D23: no affordable
  alternative AND one branch AND `squeeze_ratio_obs` < 0.5) → last affordable → already narrowing → options. **D12 amended** the
  same way (route-irreplaceable = one branch AND narrow; `route_irreplaceable_topo` kept), so R5.1's "133 route-irreplaceable" is
  the topology-only count and is SUPERSEDED on the re-run. **Consequence: D17 (the counterfactual width) moves from parked to
  REQUIRED** — it is the only measure of movement-land scarcity in the pipeline and the top class cannot be assigned without it;
  notebook 03 now runs it BEFORE the branch decomposition (the near-contiguous rule decides which links get no decomposition).
  D27 is vacuous here (no locked links, W7; G20 has nothing to check). Constants pre-registered in `config.CORRIDORS["wolverine"]`
  and pinned into `run_config.json` on re-attach BEFORE any class count is read (the northern tuning prohibition): `width_floor_cells`
  8, `len_floor_cells` 10, `near_contiguous` rule, `alt_res_tol` 1.5. Gates G13, G18, G19 (spec §4).
- **M4.4 Geometry rules mirrored (D26, D28–D31; 2026-09-28):** the branch sliver floor is RELATIVE (`branch_min_frac` 0.05 × the
  link's band area at `cutoff_branch` AND ≥ `branch_min_cells` 20; `branch_min_km2` 10 retired — G21 lists the links whose branch
  count moves); `width_ratio_p10` + `pinch_pos` reported, not classed (D28); the cheapest alternative decomposed into `alt_cost` /
  `alt_len_km` / `alt_mean_res` / `alt_kind` ∈ {far, hard, both} at `alt_res_tol` 1.5 (D29); near-optimality tiers are FIXED slack
  breaks at cutoff/6, /2, /1 (D30; the percentile tiers of M4.2 retired; G22); the cutoff is stated as **detour distance:
  `cutoff_detour_km` = 13.6229 × 0.3 km = 4.087 km** on cost-1 ground (D31) — pinned beside `cwd_cutoff_abs` in the run record and
  used in every caption; the cost-unit value stays in the methods note. W5 restated accordingly: the allowance is per link and the
  corridor AREA is an outcome (Y2Y-wide, 130 nodes), never a target — a derived analysis with no v1 area calibrates by detour
  distance (D31's rule), and this one inherits the north's.
- **M4.2 Everything else verbatim from the north (W6):** MST + β = 2.5 bridge backup (D7), priority
  tiers p90/p70 (D9), near-optimality tiers p10/p30 (D11), route branches at 0.5× cutoff, ≥ 10 km²
  (D12), current-flow centrality (D19). D21 skipped (W8).

## 5. Engine changes for Y2Y scale (2026-09-28; all additive, default-off; the north byte-reproducible)

- **M5.1 Compact CWD cache** (`cwd_compact`): `_cwd_all(pu=…)` saves `cum[pu]` float32 (row-major over
  the routable mask; 69 MB vs 189 MB per node) under `cwd_cache/<sha>_c/`; `_CwdCache(paths, pu)`
  expands on read to a full float32 grid with inf off-PU (exact: off-PU cells are inf by construction)
  and exposes `compact(k)`. `cost_matrix` gathers on the 1-D vectors via per-unit compact indices
  (`A.node_cidx`); the 2-D memmap path touched the whole file per (i, j).
- **M5.2 Band store + early-stop traceback** (`band_cache`, `band_cache_mult` 2.0): `edge_bands(tag=…)`
  stores idx (int32) + float64 field values + path at 2× the requested allowance under
  `run_dir/band_cache/<tag>/<edge>.<mode>.npz`; a request at a smaller allowance is the IDENTICAL
  predicate `field ≤ lcp + allow` on the stored values (bit-exact); a miss re-seeds the traceback with
  `MCP_Geometric.find_costs(seeds, ends=[target])` (skimage 0.26), which stops once the target is
  popped — the traced path is identical because the target's predecessor chain is fixed before it is
  finalised. Verified bit-exact on a 220 × 260 toy grid with 6 seeds and 9 edges against the untouched
  full-field path (idx, slack, centre-line, lcp; corridors, priority identical; re-attach from the store
  0.01 s) and by GW4 on 3 sampled real edges in notebook 02. `corridor_network` passes `A.cwd_tag`; the
  ensemble and the counterfactual keep the untouched path until the parked items are built.
- **M5.3 Seed lists built per node** inside `_cwd_all` (not all up front) and one array per node in
  `_apply_parts` (memory).
- **M5.4 Kind generalisation:** `_node_masks` uses `nodes.anchor_kinds`; `_node_legend` / `_is_anchor_label`
  replace the literal "existing PAs" / "proposed IPCAs" / `startswith("IPCA")` sites; defaults reproduce the
  north. `new_run` takes `nodes.proposed` optionally and records `inputs.nodes_raster` + the variant meta.
- **M5.6 The counterfactual CWD set at Y2Y scale (2026-09-28, with M4.3):** `counterfactual_squeeze` honours `cwd_compact` and the
  band store — the relaxed-surface fields are saved compact under `cwd_cache/<sha_cf>_cf_c/` (≈ 8 GB for 130 nodes instead of
  ≈ 25 GB full-grid), the unit-minimum derivation reads the compact vectors, and the counterfactual bands go through `edge_bands`
  with their own store tag (`cf_<sha_cf>`, `run_dir/band_cache/cf_<sha>/`) with early-stop tracebacks — so re-attaching after the
  counterfactual is seconds, like the baseline. Same predicate, same numbers as the northern full-grid path (the compact path is
  the toy-verified one of M5.1/M5.2; the north's `counterfactual_squeeze` is unchanged because its config has neither flag).
- **M5.5 Regression:** `cc.load(north/v2_run002)` + `cost_distances` still HITS cache `148af4ab9b8b898a`
  (full-grid memmaps, no band store) — verified 2026-09-28.

## 6. Presentation (the package spec holds the rest)

- **M6.1** `corridors_mapstyle` gains the TALL template, `AREA` tokens for refugia core / marginal / PA
  outline, `NODE` tokens, `draw_hillshade(path, XL, YL, max_px)` (windowed + decimated), `draw_cost` /
  `draw_classes(step)`, `draw_refugia`, `draw_outlines`, `draw_nodes` + `number_chip`, `place_labels`
  (greedy; collisions dropped, never shrunk), `locator(window)`, `qa(hexes)`. The northern figures render
  unchanged (every addition is a new key or a defaulted parameter).
- **M6.2** `corridors_director._province_raster(countries=None)` keeps both countries;
  `_pressure_polygons` extracted from `export_gis` (shared).
- **M6.3** `wolverine_director.py` = the assets (spec 06w §2); examples by the automatic top-k rule
  unless pinned.

- **M6.4 Output notebooks mapped to the northern 2026-09-28 structure (PRESENTATION ONLY):** `04_tables_and_figures`
  (the record, every asset) + `05_director_outputs` (the curated few; renumbered `06_director_outputs` 2026-09-28) — the same first two maps as the northern 07, drawn
  through `director_plot.wide_map` from `wolverine_director.director_frame` (G = the routing grid decimated ×2 to 600 m:
  pu = routable cells, locked2d = existing PAs; overlay = the refugia nodes with their short names; window = the Y2Y frame +
  40 km; y2y towns), surfaces from `corridors_director.cost_surface` / `classes_surface` (the §3a swatches and pressure
  words; H8 folding), the proposed IPCAs as a second fill over the corridor land (W11 overlay), insets by
  `wolverine_director.inset_windows` (examples or densest clusters; equalised by `corridors_director._same_scale`). The
  decimation is display-only: nothing analytical changes.
- **M6.5 05 · 03–05 = the northern 07 · 03–05 mirrored (2026-09-28, PRESENTATION ONLY):** the route options = the package's
  numbered examples (automatic rule, `max_examples` 4, capped by pressure priority, numbered north → south; the northern
  example schema so `corridors_director`'s option machinery reads them), drawn in the y2y cluster palette
  (`corridors_director.option_color`); stars + consequences on the Y2Y director construction exactly as the north
  (`option_profiles_y2y`: `director_core.block_percentiles` / `ValueRatios`, `cc._to_audit_frac` cover weights); reference
  columns = Banff National Park (PA) + Dene Kʼéh Kusān (proposed IPCA) rasterized from the vectors (the nodes are refugia,
  so the north's node-based references do not apply). Nothing analytical changes.

- **M6.6 Package mirror of the northern link-class presentation (2026-09-28, PRESENTATION ONLY; package spec v1.1):** classes read
  `link_class` (`P.classified`; the record notebook asserts it); the near-contiguous links drawn in `ms.NEAR_CONTIGUOUS` (neutral grey,
  hatch, barrier outline) UNDER the corridor classes on the TALL maps, the act crops and the wide layout (`_draw_near_contiguous`,
  `_near_contiguous_wide`), two legend rows with counts after the four classes; example selection class-and-width-first (top class by
  `squeeze_ratio_obs` asc → `width_ratio_p10` → `n_pairs_lost`; fill from last-affordable by `width_ratio_p10`; near-contiguous and
  already-connected links never examples); tables gain Geometry / Alternative link is / p10 width; captions state the band as detour
  distance and the geometric class counts. Pressure strings = `cc.LINK_CLASS_LABEL`.
- **M6.7 04 slimmed to the record that matters (Ethan 2026-09-28, PRESENTATION ONLY):** the Y2Y-scale contract figures (W0, W0b, W0c, W1,
  the three act crops — each minutes of hillshade + 130 node chips + 170 link labels) and the Y2Y-wide engine record maps were never going to
  be shared, and 05 does not consume anything 04 writes (it loads the run and calls the asset functions itself). 04 now writes only the
  link-class record (G18/G19 tables, class counts), T0/T3/T2/T4/T1 as CSV (+ PNG when ≤ 30 rows), the GIS export and a results-log numbers
  cell; the figure functions remain in `wolverine_director` / `corridors_core` for on-demand use (a commented cell). Nothing analytical
  changes; the §3a.3 QA checklist is not produced unless a contract figure is drawn. Two first-execution fixes on the classified run
  (both presentation): the link tables and the shared GIS exporter (`corridors_director._pressure_polygons`) now carry near-contiguous
  links — no branch decomposition (D25) meant `n_branches` NaN ("—" in the tables, −1 in the GeoPackage) and no `ms.CLASS` entry
  (the `ms.NEAR_CONTIGUOUS` label + grey fill instead). The north's exports are unchanged until a northern run is classified. Measured:
  the slimmed 04 = ~3 min on run001 (tables 10 s, GIS export 94 s). Third fix, found while drafting the report-back: the label
  parser behind the tables' "Connects" column, the endpoint-protection and jurisdiction lookups read two digits of the node number
  (`R108` → node 10 — a northern Nááts'Ihch'Oh patch), so every link touching a node numbered ≥ 100 was mis-named in the T1–T4 tables
  Ethan's first 04 run wrote; now any width (`_node_id_of_label`, regex). Maps were unaffected (they draw from node ids, not labels).
  Ethan re-runs 04 (3 min) so the run-dir tables carry the right names.

## 7. v2.5 — the two-layer product: complexes by post-processing, the network RE-ROUTED between them (run spec v3 §1a, revised by Ethan 2026-09-29)

- **M7.1 Scope and provenance (REVISED 2026-09-29):** the deliverable due 2026-09-29 derives the refugia COMPLEXES from `v2_run001`
  (tag `v2_run001`, commit 6c79be6 — the tree that produced and classified the run) and RE-RUNS THE ROUTING between them (run spec v3
  §3 stages 3–4 and §4, pulled into §1a by Ethan the same day); the v2 patch-to-patch links are used only to derive the complexes and
  the within-complex sliver table and are not reported. No baseline run and no glacier sensitivities (§6 = the next step; that code
  stays on the `wolverine-v3` branch, commit 2da23c2). The contraction engine (M7.2b) was brought onto main from that branch.
  Module `wolverine_postprocess.py` (root; patch mode + run mode) + notebooks **05_complexes** (zero routing; writes the audit
  objects; CHECK STOP 3 = the complex map) → **06_v25_network** (the routing run `v25_run001`, ~1 h) → **07_v25_product** (coverage,
  accounting, act check, tables, headline, GIS on the contracted run) → **08_director_outputs**. Numeric order = run order. The
  earlier same-day build (05 post-processing on the v2 links → 06 outputs) is superseded; its complex derivation, names and sliver
  table carry over unchanged.
- **M7.2 Complexes (D-W3 by post-processing):** connected components of the 130 near-contiguous (D25) links of the v2 network
  (a pair not linked there is separated by a third patch; components are robust to missing triangle-closing edges — disclosed),
  numbered north → south by the cell-weighted centroid; `complex_id` on every patch; polygons dissolved from `node_parts.gpkg`;
  `complex_id.tif`. Single patches are complexes. Checks: every patch in exactly one complex; complex areas = the patch total.
  The 40 corridor links carry `complex_from` / `complex_to` (labels still carry PATCH ids; the package maps them); a link joining
  one complex to itself is a WITHIN-complex corridor-class link (its path is longer than its barrier-free width, so D25 did not call it a
  sliver): reported, listed with the slivers (`kind` column), never drawn or counted as a corridor — on run001 THREE of the 40 (all β-backups,
  19–34 km: Mount Edziza ↔ Todagin South Slope in the Sustut complex, Hoskins Lake ↔ Cabinet Mountains in the Jasper complex,
  Anaconda Pintler ↔ Sapphire Divide in the Selway-Bitterroot complex), so Layer B has 37 inter-complex links; several links on one pair
  are kept and counted. The augmentation set is v2's — contraction
  will move it slightly (the report says so).
- **M7.2b Contraction engine on main (from the branch; additive, the north and v2 byte-reproducible):** `nodes.contract` in the config
  (`CORRIDORS['wolverine']['v25']['overrides']`) makes `load()` call `_contract_complexes` on the run's pinned copies of
  `complex_membership.csv` / `complex_names.csv` (new_run pins them with the other audit objects: `complexes.gpkg`, `slivers_v2.csv`,
  `complexes_summary.json`): complexes = names (label 'Complex · C03 Refugia complex (Nahanni)'), the 130 patches stay the SEED
  PARTS in their cached order (prebuilt for `_apply_parts`, treatment 'contract'), ONE routing unit per complex whose field is the
  pointwise MIN over its patches (the D16 unit-min rule = multi-seed CWD from the complex union: a path may leave any patch of the
  source and enter any patch of the target). `_resistance_sha` hashes the SEED structure on contracted runs (`seed_names`,
  `seed_n_nodes`) so the CWD cache dir is v2's (`860bb26ec2dec42b_c`, verified) and the counterfactual's identity is v2's too (the cf
  copy carries the seed attributes); unit files are named by part composition (`_unit_fname`) so a second-pass merge never reads a
  stale file; `_locked_edges` skips units whose treatment is not `link_locked` (a contracted unit has parts but NO intra-complex links);
  GW5 (partition + area gate); `second_pass_merges` (D25 on the inter-complex links → `merge_complexes` + a new run id; 06 asserts
  none); `complex_layer` (Layer A: patches, area, PA share, IPCA-added share, mean of the 300 m human proxy, slivers) written by
  `write_run` (`complexes_layer_a.csv`, `complex_id.tif`); `load_results` exposes the complexes, the complex grid, the centrelines and
  the sliver table. Run ids `v25_runNNN` (the globs accept any `v[0-9]_run`). MST + β backups, D7, D17 width tests, D23–D25 classes,
  D26 branches, D30 tiers, W11 all run unchanged on the contracted graph; centrality is computed once on it.
- **M7.3 Coverage (D-W4):** per complex and per INTER-COMPLEX link's dissolved band (the contracted run's per-link band polygon, node
  land excluded; run mode of the module, notebook 07): share inside existing PAs, incremental share added by the proposed IPCAs, share in the prioritizr core (the
  balanced scenario's guarded tier ON ALLOCATABLE LAND: `analyses/y2y/director_package/geotiffs/f_balanced_core.tif` ≥ 0.70 AND
  outside the flagship's locked PAs (`aligned_stack/mask_protected_areas.tif`; the locked cells sit at f = 1 by construction and
  are the PA column here) — reproduces the package's 51,580 km² exactly, asserted; resampled nearest to 300 m) and its increment
  beyond PAs + IPCAs, share outside all three; ONE area-expectation row =
  the same shares over the whole routable Y2Y frame (pu, incl. the 20 km buffer), so an overlap reads against expectation.
- **M7.4 Slivers, accounting, names:** the sliver table (from the v2 record, notebook 05) = one row per within-complex link — the 130
  near-contiguous links + the three v2 corridor-class links with both ends in one complex — with path length and the cost-10 / 100 /
  1000 cells along the centreline (read at the centreline vertices = the path cells; cheap); accounting (on the contracted run, 07) =
  corridor land as DISSOLVED unions (all bands; the inter-complex links; per class) beside per-link SUMS labelled as such, and branches
  as links-with-n reconciled with `branches.csv`; names (D-W7): every patch 'Refugium (X)' (X = the PA it overlaps ≥ 10%,
  else the nearest PA + bearing; designation words stripped), complexes 'Refugia complex (X)' from the largest patch — written to
  `postprocess/node_names_v25.csv` + `complex_names.csv` and into `display_name` of the tracked audit `node_names.csv` (the run-dir
  copy stays pinned). T1–T4 are regenerated on the product (after the M6.7 parser fix).
- **M7.5 Package (PRESENTATION):** on an attached run the node table IS the complex table; two acts by default (`V25_STYLE`, one
  break at 51 °N) with `bow_valley_check` (corridor links within 60 km of Banff; if they straddle the southern break the rule
  moves it to the Bow Valley, 51.2 °N, recorded in `postprocess/acts.json` and re-applied by 06); `figure_network_wide` = 06 · 02
  (complexes filled in the refugia tone at four alpha steps by their share inside existing PAs, outlined; the 40 corridor links by
  class in the ramp slot; the D28 pinch marked on each; inset labels '<name> [slivers]'; near-contiguous bands NOT drawn, D-W6);
  tables A (complexes with coverage), A-slivers, B (corridors), `headline.json` (the §1a headline table, traced to postprocess/
  files); `export_complexes_gis`. 06 · 01 keeps the cost map with the complexes as the node layer; 03–05 unchanged on the
  corridor links.
- **M7.5a D25a compatibility:** the engine on main now splits the near-contiguous class three ways (open / roads / barrier; the
  northern D25a patch, committed with the tag) while `v2_run001` was classified with the single `near_contiguous` key. The package
  reads `link_class` directly and maps any near-contiguous value onto the mapstyle's tokens (`_norm_class`), so the v2.5 product
  needs no re-classification; the run is not re-run.
- **M7.7 The D25 second pass FIRED (Ethan's run of 06, 2026-09-29):** on the 23-complex graph one inter-complex link was
  near-contiguous — Jasper complex ↔ Selway-Bitterroot complex (E011_019: least-cost path 56 cells = 16.8 km against a barrier-free
  median width of 78 cells = 23 km; no cost-1000 cell on the path). Per the registered rule (run spec v3 §4) the pair was MERGED
  (`cc.merge_complexes`, pass 2): 22 complexes; the merged 'Refugia complex (Jasper)' = 31 patches / 167,594 km² (centroid 50.8 °N,
  from Jasper to the Bitterroots — the wide-front case the spec anticipated: recorded, the allowance NOT touched). Audit objects
  rewritten and renumbered north → south (Glacier is C13 as before; Yellowstone C22); `v25_run001` stays on disk as the pass-1 record
  (no network products written); the run is `v25_run002` (config `v25.run_id`).
- **M7.8 Fronts as corridors, and the interior D7 reading (spec §1a / §5 / §8 / D-W6 revised by Ethan 2026-09-29, mirroring the northern
  D25c; chat ruling the same day):** (i) NO second-pass merge — complexes are fixed from the v2 adjacency (23) and an inter-complex link
  that comes back near-contiguous is a front classed on the same pressure scale (the engine's D25c: one component, width as the route
  sense). The C12 + C20 merge of M7.7 is UNDONE (audit objects regenerated; `v25_run001` / `v25_run002` remain as the merge-era records;
  the run is `v25_run003`). The pair was REAL, not a naming artefact: the Jasper complex's southern tail (Cabinet Mountains, Barktable
  Ridge, 47.8–48.2 °N) faces the Selway-Bitterroot complex's northern patch across ~17 km of the Clark Fork valley; 700 km is the
  centroid distance of two elongated complexes. (ii) Every within-complex link (the 130 near-contiguous ones + the 3 corridor-class
  links with both ends in one complex) is a FRONT: route sense = width alone (CUT when the least-cost path carries cost 10 or the width
  ratio is below 0.5), drawn as corridors under the inter-complex links (open = the Minimum tint merged across the interior; cut = the
  Some colour with an outline), reported in a per-complex table separate from Layer B, front area on its own line (never summed into
  inter-complex corridor land). (iii) The edge sense on fronts: the ruling = D7 read on the complex's OWN front graph (the front is a
  bridge, or the surviving detour costs > β × the front), expected to collapse the 43 patch-level flags to a handful. MEASURED: it fires
  on 91 of 133 (60 bridges + 31 detours > β), because the front graph available is v2's network — the MST plus seven backups, a chain by
  construction, so almost every interior link is a bridge. The reading needs the full adjacency graph (fronts on pairs v2 never linked),
  which is not a same-day change. Per the ruling's fallback, THE DRAFT DRAWS FRONTS ON WIDTH AND ROAD ONLY; both edge readings
  (`E_v2` patch-level, `E_interior` on v2's graph) are TABLE-ONLY (`A_fronts.csv`, `front_class_d23`), pending the interior D7 reading on
  the full adjacency graph (next step). Register: D7 at the reported level = the contracted graph for inter-complex links; the interior
  reading for fronts is defined but not yet computable on the right graph.
- **M7.9 BACK TO NODE LEVEL (Ethan's spec revision of 2026-09-29, the third that day; the one in force):** the deliverable is `v2_run001`
  as routed (130 nodes, 170 links) with the northern reframe — every non-touching link a corridor on ONE pressure scale. One post-
  processing notebook (**05_postprocess**, zero routing; `wolverine_postprocess` node-level functions): (i) `kind` front / strip;
  a FRONT's class from the existing columns — edge sense D7 as routed, route sense = width alone (CUT when the least-cost path carries
  a cost-10 cell or the width ratio is below 0.5; no branch decomposition; `lcp_max_cost` reported and reconciled with the engine's
  `crosses_cost_1000`, M7.11); strips keep their v2 classes; (ii) `inter_cluster`
  = the two ends in different components of the front subgraph (23 components = the former complexes; a reporting filter, not a node
  definition); (iii) coverage per NODE and per link band (PAs / IPCAs incremental / the balanced core on allocatable land / outside)
  with the expectation row; (iv) accounting: corridor land dissolved, per-class dissolved beside per-link sums, front area its own line,
  the D25b identity on per-link sums (MST strips + MST fronts + augmentation = total), branches as links-with-n; (v) names in the audit
  `node_names.csv` (D-W5), labels by NUMBER (R12) on every output until names are chosen; (vi) the act check, the Nodes and Links tables,
  T1–T4, the headline, H-W1–H-W7, the §9 checklist. Then **06_director_outputs** with every style decision kept: no protected layers,
  refugia lime on all maps, fixed insets at 312 × 346 km (A on the Nahanni links south, B on Missoula–Helena–Salmon–Bozeman), no pinch
  marker; 02 = strips at full weight in the ramp slot with fronts as bands in their class colour (open = light tint, cut = outlined);
  03 = the route options (strips only as examples) over the same base. **Parked (spec §10, `parked_v3/`):** the complexes chain
  (05_complexes / 06_v25_network / 07_v25_product, runs v25_run001–002, the contraction engine, the interior D7 reading) and, on the
  `wolverine-v3` branch, the baseline comparison and glacier surfaces. M7.7 / M7.8 stand as the record of that detour.
- **M7.11 Path-cell lookup bug, found by the chat's reconciliation check (2026-09-29):** the post-processing read the cost class along a
  link by sampling the resistance at the centreline vertices with `searchsorted(...) - 1`; the vertices are written at CELL CENTRES
  (corridors_core._edge_vectors), so that landed one cell WEST and one SOUTH of the true path cell — a diagonal neighbour. Symptoms:
  '59 fronts cross a cost-1000 cell' against the engine's `crosses_cost_1000` = 0 on every link; '43 slivers touch cost 10' and '62 with a
  cost-100/1000 cell'. Fixed (`_path_cells`: the nearest centre from the grid origin); verified on all 170 links — max cost ≥ 1000 = 0 =
  the engine's flag on every link, vertex count = the recorded path length on every link. Corrected: 15 fronts carry a cost-10 cell,
  none carry cost 100 or 1000, 115 are all cost 1. Every count that used the lookup was regenerated (R7.2 / R7.3 corrected; the parked
  audit artefacts `slivers_v2.csv` / `fronts_v2.gpkg` rewritten). The rule stands as the spec writes it (cut = a cost-10 cell on the path
  or width ratio < 0.5) and now applies to the same number the engine reports.
- **M7.12 Cut = width only; `crossing_class` on every link (spec §1a / §4 as amended by Ethan 2026-09-29 after the M7.11 reconciliation):**
  a front is cut when its width ratio against the barrier-free width is below the squeeze threshold (0.5) — the northern D25c; path
  cost never drives the class. `lcp_max_cost` / the road flag become `crossing_class` (the maximum cost class on the least-cost path,
  exact-cell lookup) carried on every link — strips and fronts — with a profile sentence (`crossing_note`: 'the direct route crosses a
  road or cut (cost 10)' / '… converted land or a two-lane highway (cost 100)' / '… a multi-lane highway, water or settlement (cost
  1000)'), in the Links table and T1–T4; the class rule reads width alone. MEASURED on the 130 fronts: the class table is UNCHANGED
  by the amendment — every front whose direct route crosses a cost-10 cell (15) is also narrower than half its barrier-free width
  (a road along the gap narrows the front, as the spec's own reasoning says), so cut stays 34 = narrow 34, and the 15 road fronts sit in
  narrowing (8) and only viable (7), never in options / last affordable. Classes 72 / 15 / 24 / 19, sum 130 (G23). Strips: 21 with an
  all-intact direct route, 19 crossing cost 10. The parked 133-front artefacts were regenerated the same way (97 open / 36 cut; crossing
  class 117 at 1, 16 at 10; sum check passes).
- **M7.14 Presentation set, 06 (Ethan 2026-09-29, five rulings, all knobs, nothing measured changes):** (i) 03 draws the route options as
  coloured bands only — no numbered circles / leader lines, no cluster-swatch legend row (the y2y cluster construction; the stars and
  consequences carry the number + colour) — `option_markers=False`, `option_legend="none"`; (ii) the legend box is centred between
  inset B's bottom edge and the page bottom (the ramp block's bottom) and its items shrink in font units until the box fits the gap —
  `director_plot.STYLE` `wide_legend_between` + NEW `wide_legend_fit` / `wide_legend_fs_min` (default off; y2y and the north unchanged;
  simulated: 3 rows fit at 16 pt, 4 rows at 13 pt); (iii) NEW 03 = 02's pressure surface over protected land as ONE grey layer —
  existing PAs and the proposed IPCAs / PAs, their union filled `#8f8f8f` at 0.85 UNDER the surface (zorder 0.45; Ethan's second
  ruling the same evening, first drawn on top) — `figure_protection_wide`, with the largest PAs (4) and proposed areas (3, suffixed ', proposed') named per inset through the
  layout's post-draw hook (one declutter set); route options → 04, stars → 05, consequences → 06; (iv) the corridor-pressure surface and its
  key at alpha 0.85 (`surface_alpha`, the northern maps' value) so the boundary lines show through, 01's cost surface at 0.70
  (`cost_surface_alpha`; None = follow `surface_alpha`, 1.0 = opaque) and 03's pressure surface at 0.65 over the grey
  (`protection_surface_alpha`) — Ethan's second pass the same evening: 0.85 hid the boundaries on 01 and the band-over-protected-land
  overlap on 03; (v) inset A carries YT and NWT on
  their parts inside the region (`inset_codes["A"]`, verified at 0.20/0.71 of the window width, both on the top fifth). (vi, later the same
  evening) 04 = 03's base with the four route options OUTLINED in the option colours (the northern construction: white halo + colour
  ring, so the pressure fill shows) and numbered 1–4 by the northern post-draw placer; the options are PINNED by link id
  (`EXAMPLE_PICKS`): A = E020_023 / E020_026 (the Nahanni node's two links south to the Muncho Lake refugia, 0% of their bands inside
  Nahanni NPR; 4,013 / 3,833 km²), B = E110_120 (Selway-Bitterroot ↔ Lee Metcalf, one branch, narrowing) / E110_119 (Selway-Bitterroot
  ↔ Skull-Odell, two branches, options); numbered north → south. (vii) NO TEXT OVERLAPS (Ethan's rule): PA / proposed-area names are
  placed by `_place_area_names` only where the text box overlaps no existing text (codes, towns, earlier names, option numbers) and
  lies inside the panel (pole of inaccessibility first, then interior grid points; else unnamed); town labels are flipped through the
  offset quadrants away from any overlap by `_declutter_texts` (hidden if none is clear) on every wide map. (viii) two-neutral split of
  the protected fills is a knob pair (`protection_fill_pa` / `protection_fill_ipca`, both None = the one grey), decision pending. (ix, chat review of 01, 2026-09-29) the 1,000 cost
  class is DRAWN as two swatches -- open water (the variant derivation's retained lake / river / ocean layers) in blue-purple `#4F63C9`,
  settlement and other retained barriers in magma's dark -- both ticks 1,000; the cost surface itself is untouched (display only, no
  re-route); tick words "roads and forestry cutblocks" / "farmland, other converted land"; ID pinned clear of inset B's scale bar; the
  frame's north arrow beside the 250 km bar (`director_plot` `north_arrow_beside_bar`, default off). (x, Ethan 2026-09-29, 'why are there breaks in the corridors'):
  DIAGNOSED on inset B -- every band holds its least-cost path at 300 m (the two option links are 1 and 2 connected pieces), the
  visible breaks were (1) the wide layout's 2x STRIDE to the 600 m frame dropping one-cell necks (band pieces in the window 20 -> 28),
  (2) bands stopping at the refugia they cross (correct, drawn green), (3) overlap cells owned by one link (04's outlines only); the
  beads are road crossings (3.8% of B's band cells lie on cost 10, none on 100 / 1,000; beside the path the 4.1 km allowance is spent
  in one or two cost-10 cells). FIX (display only, `frame_reduce="any"`): every surface and mask is reduced to the frame by block
  ANY (masks) / nanmax (class images), so a band continuous at 300 m renders continuous; at a class boundary the higher index wins by
  at most one 300 m cell. The class question ('options' with a one-cell pinch) is the D28 median-width rule -- p10 reported, not
  classed -- and goes to the chat.
- **M7.13 Refugia fill = sea-green `#5BA699` (Ethan 2026-09-29, 'any green-ish tint that works with the sand colour bar'):** a grid search
  over the green family (hue 90–200°, saturation 0.45–0.9, value 0.35–0.65) against the sand pressure classes + water, the magma cost
  swatches + water and the four route-option colours, CIE76 under normal vision, deuteranopia and protanopia: pure greens and limes fail
  (sand's 'A lot' brown, the option orange); the passing region is the blue-green corner at moderate saturation. `#5BA699` (hue 170,
  sat 0.45, val 0.65): 20.1 / 22.0 / 22.4. Replaces the indigo of M7.10 on all three maps; outline `#2F5F55` 0.3 pt.
- **M7.10 Colour (Ethan 2026-09-29, 'the colour bar as the northern analysis'):** the pressure key on 02/03 is the SHARED default of
  `corridors_mapstyle` (`CLASS_PALETTE = "sand"`: pale sand → tan → brown → dark umber for Minimum → Maximum, set by Ethan in the
  northern package the same day); the wolverine package reads the same tokens, so nothing is set locally. Consequences measured:
  (i) the open-front tint is 0.70 alpha (0.45 of pale sand sat at luminance 0.91 on the 0.97 land); (ii) the refugia fill reverts
  to indigo `#4D4DBF` on every map — the only candidate ≥ dE 20 (CIE76, normal + deuteranopia + protanopia) against sand, the magma
  cost swatches, water AND the four route-option colours (min 20.1); the lime of 06·01 (chosen against magma alone) is dE 12.0 from
  sand's 'A lot' brown and 6.4 from the option orange, so it fails the §3a test on 02/03. One knob (`cost_map_refugia_fill`).
- **M7.6 Not exercised at build time:** the wide figures on the node-level product (first render = Ethan's 06). Smoked: the node-level
  pipeline end to end into a scratch folder and the package on it (tables, headline, hypotheses, checklist, overlays, windows).
- **M7.6 (superseded text) Not exercised at build time:** the contracted routing run itself (06 = a solve; first execution = Ethan's), run mode of the
  module and the package on the contracted run (07/08 need that run), the second-pass merge path. Smoked: 05 end to end into scratch
  folders and its audit objects through the engine's contraction loader (23 complexes, GW5, the v2 cache identity reproduced); on the
  branch build the same loader + `_apply_parts` + GW5; the package's tables / headline / overlay on the v2-derived product.

## 8. QA gates (definitions; measured values in results_log R1)

G2, GW1, GW2, G4, G8, G0 + GW3, G3, GW4, G15, G10, G22, G13, G9, G21, G18, G19 — see the spec §4 (G20 vacuous: no locked links).

## 9. Provenance conventions

Inherited from the north: `run_config.json` is the engine's only input after `cc.start` (git SHA, input
hashes incl. the class raster, the variant meta and `node_names.csv`); the run dir is the only record;
`output_data/` is gitignored; the audit objects are git-tracked (`.gitignore` exception for the gpkg).
