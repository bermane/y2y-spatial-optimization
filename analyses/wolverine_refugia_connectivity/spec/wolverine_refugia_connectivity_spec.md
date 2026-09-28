# Wolverine refugia connectivity — analysis spec (v1.0, 2026-09-28)

**Status:** v1.0 BUILT 2026-09-28 (Ethan's decisions W1–W10 the same day); pending Ethan's run of
notebooks 01 → 05. Results-first scope: **the output maps and results only**; sensitivity analyses and
audits are PARKED (§7). Subordinate to the northern methodology — `docs/05_methods_v2.md` (D1–D10),
`analyses/northern_connectivity/spec/05_corridors_v2_addendum_run_and_alternatives.md` (D11–D21) — which
this analysis MIRRORS; every departure is a numbered decision here. Living logs: `methods_log.md` +
`results_log.md` in this folder (binding: update in the same session as any methods change or result).

## 0. Question and claim scope

Which land connects **wolverine climate refugia** across the whole Yellowstone-to-Yukon region, where
are the links with no affordable alternative, and where do the options still exist? Structural
connectivity on a published movement-cost surface between refugia patches — NOT a wolverine movement
model: the resistance is expert-assigned and species-agnostic apart from one documented adjustment (W1),
the refugia are a climate-envelope product, and nothing is validated against wolverine movement or
genetic data. "Corridor" is reserved for the bands and branches this engine produces.

## 1. Decisions (pre-registered)

| # | Decision | Value |
|---|---|---|
| **W1** | Resistance | The published O'Brien et al. 2025 surface (US extension of Pither et al. 2023; 300 m; ordinal costs 1/10/100/1000 = per-pixel maximum over 23 layers) with the source's **three expert-assigned generic-fauna terrain rules withheld equally — elevation > 2,300 m, slope > 30°, glaciers** — and the maximum retaken. A cell that was 1000 on those rules alone falls to 1; every other layer (built-up, lights, mining, oil & gas, dams, rail, all road classes, lakes ≥ 10 ha, rivers > 28 m³/s, ocean) keeps its published cost; the 10 and 100 bands are untouched; a terrain cell coincident with a retained layer keeps 1000. Labelled **"O'Brien 2025, generic terrain rules withheld"**; it is not a wolverine-specific surface and claims only that alpine terrain is not a barrier. Applied as the named variant `config.CORRIDORS["wolverine"]["variants"]["terrain_withheld"]` (the published surface stays the config baseline; the run passes the variant as `overrides`). **Justification:** the three rules are the only cost-1000 assignments the source describes as expert opinion on natural features for terrestrial non-volant fauna generally; for wolverine they invert documented habitat use (selection for high-elevation alpine, boulder fields and steep avalanche terrain) and topographic variables do not enter the top landscape-genetic resistance models. Because the source's costs were designed for linear barriers crossed in a single cell, applying 1000 to an areal class makes a 5 km alpine belt equivalent to ~17 highway crossings, and with the ~4 km absolute band it hard-excludes the alpine rather than penalising it. Measured on the published surface: 28.4% of core refugia is cost 1000 against 13.8% of Y2Y; the elevation and slope rules alone account for 71% of the cost 1000 under core refugia and 52% Y2Y-wide; 96% of Y2Y cells above 2,300 m are cost 1000. Lakes and rivers are retained at 1000 for scope discipline despite being seasonally permeable to dispersing wolverines (known bias for large intact northern lakes, disclosed). |
| **W1a** | Implementation of W1 (disclosed approximation) | The repo holds the published surface, not the source's 23 layers. The recompute is therefore `cost == 1000 & terrain & ¬retained → 1`, where `terrain` = elevation > 2,300 m OR slope > 30° (both from the 300 m DEM — the source's GMTED2010 is ~250 m, the same grain; GMTED itself if dropped into `input_data/dem_gmted/`) OR RGI 7.0 glacier, and `retained` = HydroLAKES polygons ≥ 10 ha, HydroRIVERS `DIS_AV_CMS` > 28, ocean (Natural Earth), and the human layers by proxy: the 90 m gHM maximum within the 300 m cell ≥ τ, with τ calibrated by balanced accuracy on the cost-1000 cells explained by no natural layer (reported with its confusion table in the variant meta; never asserted). Sub-1000 layers under withheld terrain are taken as 1 (croplands, pasture and two-lane highways above 2,300 m or on > 30° slopes are essentially absent in Y2Y; resource roads are possible — disclosed). The earlier ad hoc floor (gHM < 0.05 and elevation ≥ 1,500 m) is withdrawn. |
| **W2** | Nodes | 8-connected components of the **core** refugia classes (2 ∪ 12) on the 300 m routing grid, **≥ 500 km²** (67 patches holding 81.7% of the 318,822 km² of core on the engine grid — 66 on the build-time scratch grid; ladder 250 / 500 / 1,000 km² → 130 / 67 / 36; node land 260,613 km²). No morphological closing. Kind `refugium`. Existing protected areas are CONTEXT on every map and never nodes. |
| **W3** | Marginal refugia (1 ∪ 11) | Map context only in this pass; never enters resistance (D5). (The per-band marginal share and stepping-stone accounting are parked, §7.) |
| **W4** | The model seam / non-refugia classes | One layer: core = {2, 12}, marginal = {1, 11}; components may span the ~53.97 °N seam between the two stitched source models (values 10/11/12 north, 0/1/2 south). Classes 0 and 10 are simply NOT refugia (Ethan 2026-09-28): they are never labelled or shown on any output. Source citation: deferred (Ethan). |
| **W5** | Band cutoff (D6) | **Inherited** from `north/v2_run002`: `cwd_cutoff_abs = 13.622951589524746` (same 300 m grid and cost units ⇒ the same ≈ 4 km detour allowance through intact land). Pinned via `set_cutoff`; `calibrate_cutoff` is never called (no v1 target exists). |
| **W6** | Network, tiers, branches | Verbatim from the north: β = 2.5, priority tiers p90/p70, near-optimality tiers p10/p30, `branch_mult` 0.5, `branch_min_km2` 10, current-flow centrality (D19). |
| **W7** | D16 / H7 | Not applicable: raster patches are single components by construction. The step-0a analogue `cc.node_patches` writes the H7-FORMAT `node_parts.csv` / `node_parts.gpkg` (every figure reads the gpkg) and `node_names.csv`; there is no review file and `require_review=False`. |
| **W8** | D21 adjacency | Skipped (`skip_adjacency`), diagnostic only. |
| **W9** | Node names | Auto: the PA with the largest overlap when it covers ≥ 10% of the patch, else the nearest PA + 8-point bearing ("Banff National Park (NW)"); `node_id` 1..N numbered **north → south**; labels `Refugium · R12 <name>` (the Kind · Name shape every helper expects; never "IPCA"). Optional human overrides in `audit/audit_objects/node_names.csv` (`display_name`), copied + sha-pinned into the run and fingerprint-checked (GW3). |
| **W11** | Protected land (Ethan 2026-09-28) | **Existing PAs (`PA_VECTOR`, all sizes) + the proposed IPCAs/PAs (`PROPOSED_PA_VECTOR`, 32 polygons, taken as given) enter as a STATUS layer, never as resistance (D5) and never as nodes.** Per separated link, `secured_status` measures the share of the least-cost centre-line inside nodes + existing PAs, and inside nodes + PAs + proposed IPCAs; at ≥ **0.95** (pre-registered; "near 1") the link is **already connected — by existing PAs alone (`secured_by = pa`), or only once the proposed IPCAs are realized (`ipca`)**. Such links are listed (T4) and never used as examples. The corridor land inside protected land is "already secured": `corridors_unprotected.tif` = the land still to secure; per link `band_pa_frac`, `band_ipca_frac`, `band_unprotected_km2`. **Presentation (one knob, `wd.STYLE["protected_mode"]`):** `"overlay"` (default) draws every band in full, hatches existing PAs (grey ///) and proposed IPCAs (teal \\) on top, and draws satisfied links muted with an outline in the satisfying layer's colour; `"unprotected_only"` draws only the land still to secure and omits satisfied links. The pressure classes (D7 / D12) are properties of the landscape and are unchanged by protection. |
| **W10** | Check stops (Ethan) | Two, both in notebook 01 before any CWD: (1) the raster → node transformation (node map, ladder, node table, `node_parts.gpkg` / `refugia_class.tif` for GIS); (2) the updated resistance layer (published vs variant vs change map by rule; the variant meta with km² withheld per rule Y2Y-wide / under core / by elevation band, τ + confusion, class shares before/after; `movement_cost_terrain_withheld.tif` for GIS). Notebook 02 solves ONLY the variant surface. |

## 2. Mirror table — what is inherited from the northern methodology, what is not

| Northern decision | Here |
|---|---|
| D1/D2 published surface, no blend | Inherited, with the one named variant of W1 (D4's "visible named scenario, never a blend weight" doctrine) |
| D5 values never enter resistance | Inherited (refugia enter as NODES, never as cost) |
| D6 absolute band cutoff | Inherited value (W5) |
| D7 MST + β-backup, irreplaceability | Inherited |
| D8 structured ensemble B/C/D | **Parked** (§7) |
| D9 linkage priority surface | Inherited |
| D11 near-optimality, D12 route branches | Inherited |
| D13/D14 per-branch values table, Carroll audit column | **Parked** (§7) |
| D15 ensemble attribution | **Parked** (with D8) |
| D16 multipart parts + H7 | Not applicable (W7) |
| D17 counterfactual squeeze | **Parked** (§7); the "squeezed" class is withheld by the existing H8 logic until it runs |
| D19 current-flow centrality | Inherited |
| D21 adjacency graph | Skipped (W8) |
| Nodes = IPCA + PA vectors | **Raster patches** (W2); PAs + proposed IPCAs = a protection STATUS layer (W11), never nodes |
| Grid = northern window | The whole study area (no latitude cut), own namespace `input_data/corridors_300m_y2y/` |

## 3. Constants (spec §2 analogue) — `config.CORRIDORS["wolverine"]`

| key | value | note |
|---|---|---|
| `grid.res_m` / `region_filter` / `dir` | 300 / None / `corridors_300m_y2y` | whole study area |
| `nodes.node_min_km2` | 500 | W2 |
| `nodes.classes_core` / `classes_marginal` | [2, 12] / [1, 11] | W4 |
| `nodes.context_pa_min_km2` | 200 | context only |
| `nodes.naming.pa_overlap_min` | 0.10 | W9 |
| `cwd_cutoff_abs` | 13.622951589524746 | inherited (W5) |
| `nodes.protected` | all existing PAs + `PROPOSED_PA_VECTOR` | W11 status layer |
| `secured_centreline_frac` | 0.95 | W11: "already connected within protected land" |
| `beta`, `priority_tiers`, `near_opt_tiers`, `branch_mult`, `branch_min_km2` | 2.5, {90, 70, 0}, {10, 30, 100}, 0.5, 10 | W6 |
| `variants.terrain_withheld` | withhold = elevation > 2,300 m, slope > 30°, glacier; `withheld_take` 1; retained: lakes ≥ 0.10 km², rivers > 28 m³/s, ocean, gHM-90 ≥ τ | W1 / W1a |
| `cwd_compact`, `band_cache`, `band_cache_mult` | True, True, 2.0 | Y2Y-scale efficiency (§5) |

## 4. Gates (asserted in the notebooks; measured values → `results_log.md` R1)

| gate | holds invariant |
|---|---|
| G2 | cost warp fidelity (CRS, shape, extent, classes ⊆ {1, 10, 100, 1000}); also run on the variant surface |
| **GW1** | the class warp is on the cost warp's grid, values ⊆ {0, 1, 2, 10, 11, 12}, ≥ 99.9% of routable cells classed |
| **GW2** | the variant changes only cost-1000 cells, never raises a cost, classes and grid unchanged |
| G4 | graph-layer self-test (β = 0 ⇒ MST, MST ⊆ augmented) |
| G8 | config validity (dead keys, addendum keys, cutoff, warps present) |
| G0 | the node set: count = the frozen `refugia_summary.json`, 0 dedupe merges, naming-file hash pinned |
| **GW3** | `node_names.csv` rows fingerprint-match the current node set (node_id, cell count, lat/lon) |
| G3 | raster flood-fill components = graph components |
| **GW4** | the band store + early-stop traceback reproduce a fresh full-field computation bit-exactly (3 sampled edges) |
| G15 | centralities finite; current-flow ∝ shortest-path on the β = 0 tree |
| G10 | near-optimality ≈ 0 on every least-cost path; tiers monotone |
| G9 | every branch component touches both endpoints |

## 5. Engine at Y2Y scale (all changes additive and default-off; the north is byte-reproducible)

47.3 M cells (17.2 M routable) on a 24 GB machine with ~21 GB of free disk: (i) **one boolean array per
node** (the mask is the seed part and the routing unit); (ii) **compact CWD cache** — `cum[pu]` float32,
69 MB per node instead of 189 MB, expanded on read (`cwd_cache/<sha>_c/`); (iii) **compact cost matrix**
(gathers on the 1-D vectors — the 2-D memmap path touches the whole file per pair); (iv) a **per-run band
store** (idx + float64 field values at 2× the requested allowance under `run_dir/band_cache/<tag>/`) so any
smaller allowance is the identical predicate on stored values and every later notebook's re-attach is
seconds; (v) on a store miss the traceback re-seeds with `find_costs(ends=[target])` (early stop), verified
bit-exact by GW4 and by a toy-grid test (`methods_log.md` M5.2). The north's cache
(`148af4ab9b8b898a`, full-grid memmaps) is untouched and still hits.

## 6. Outputs

`output_data/corridors_wolverine/v2_runNNN/`: `run_config.json` (+ the variant meta, the class raster and
`node_names.csv` hash-pinned), `resistance.tif` (the variant), `node_id.tif`, `corridors.tif/.gpkg`, `corridors_unprotected.tif` (W11),
`corridor_edges.csv/.gpkg`, `criticality.csv`, `linkage_priority*.tif`, `edge_owner.tif`,
`near_optimality*.tif`, `branches.*`, `band_cache/`, `corridor_summary.json`; `director_package/`
(figures W0, W0b, W0c, W1, W2–W4 as PDF + PNG; tables T0–T2; `gis/`; `qa_checklist.csv`) and
`director_package/director_outputs/` (the curated set). Package spec: `06_wolverine_director_package_spec.md`.

**Run sequence (Ethan, numeric order):** 01 (warps, nodes → check stop 1; variant → check stop 2; timing
probe) → 02 (run dir on the variant, CWD, inherited cutoff, network, GW4, G15, priority, write_run) →
03 (near-optimality, branches, finish) → 04 (the record) → 05 (the curated set).

## 7. Parked (bolt-on later; each is additive to the same run dir)

- **Comparison runs**: the as-published surface, and glaciers kept at 1000 — one baseline network each
  (`cc.start(KEY, overrides=…)`; ~3–5 h and 4.5 GB each).
- **Ensemble B/C/D** (D8/D15): `03_ensemble` as in the north; `ce._member` gets the band-store tag; adds the
  attribution column and the robust core.
- **D17 counterfactual squeeze**: a second CWD set on the cf surface (~4–5 h); adds the "squeezed" class.
- **Co-benefit audit** (D13/D14: `corridor_profile`, `alternatives_table` + `tiebreak`, star plots,
  `T_options`) and the **refugia audit** (per-band marginal share, stepping stones).
- **D21 adjacency graph.**

## 8. Data

- Refugia: `input_data/wolverine_refugia/baseline_wolverine_climate_refugia.tif` (EPSG:4326, ~250 m, float32,
  NaN nodata; covers 100% of Y2Y; class areas inside Y2Y (km²): 0 → 315,573 · 1 → 52,540 · 2 → 201,592 ·
  10 → 557,687 · 11 → 115,805 · 12 → 114,457).
- Cost: `input_data/transboundary_connectivity/Movement_Cost_Layer.tif` (EPSG:3347, 300 m; 100% of Y2Y).
- Variant inputs (open; `data/acquire.py`): RGI 7.0 regions 01 + 02 → `input_data/glaciers/`; HydroLAKES v1.0 +
  HydroRIVERS v1.0 NA → `input_data/hydrosheds/`; the 90 m gHM `input_data/human_modification/HM_Y2Y_2024_90_60land_v202606.tif`;
  DEM `input_data/basemap/dem_y2y_300m.tif` (GMTED2010 optional).
