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
  components (`ndimage.label`, 3 × 3); patches ≥ 500 km² (`node_min_km2`; 5,556 cells) are the nodes;
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

## 7. QA gates (definitions; measured values in results_log R1)

G2, GW1, GW2, G4, G8, G0 + GW3, G3, GW4, G15, G10, G9 — see the spec §4.

## 8. Provenance conventions

Inherited from the north: `run_config.json` is the engine's only input after `cc.start` (git SHA, input
hashes incl. the class raster, the variant meta and `node_names.csv`); the run dir is the only record;
`output_data/` is gitignored; the audit objects are git-tracked (`.gitignore` exception for the gpkg).
