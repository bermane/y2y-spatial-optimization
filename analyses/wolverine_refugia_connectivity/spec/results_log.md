# Results log — wolverine refugia connectivity (living document)

**Purpose.** Every quantitative result destined for the write-up, with run provenance. Same maintenance
rule as `methods_log.md`: a new measured result gets an entry here in the session it is measured;
supersede, never delete. Entries before the first run are the build-time measurements (read-only
characterisation, 2026-09-28).

---

## R0. Inputs, measured at build time (2026-09-28, read-only; the 300 m grid used here was a scratch
warp with the same snapping — notebook 01 re-measures on the engine's own grid)

- **R0.1 The refugia raster.** EPSG:4326, 0.002246° (~250 × 143 m at 55 °N), 14,584 × 11,395, float32,
  NaN nodata; covers 100% of the Y2Y polygon. Class areas inside Y2Y (km²): 0 → 315,573 · 1 → 52,540 ·
  2 → 201,592 · 10 → 557,687 · 11 → 115,805 · 12 → 114,457. Classes 10/11/12 lie north of 53.965 °N
  (and west of −122.07° at 49–54 °N); 0/1/2 fill a rectangle south / east of that (two stitched models).
- **R0.2 Core patches on the 300 m grid.** Core (2 ∪ 12) = 318,818 km² in 1,846 8-connected patches;
  ladder: ≥ 50 km² 352 patches (96.7% of core area) · ≥ 100 → 241 (94.2%) · ≥ 250 → 130 (88.8%) ·
  **≥ 500 → 66 (81.6%)** · ≥ 1,000 → 37 (75.3%) · ≥ 2,000 → 17 (66.2%); largest patch 78,430 km²;
  nearest-neighbour distance between the 66 nodes: median ≈ 2.6 km. Marginal (1 ∪ 11) = 170,018 km².
  A 1-cell morphological closing would have merged the two largest patches (78k + 32k km²) — rejected (W2).
- **R0.3 The published cost surface over Y2Y.** Class shares 75.4 / 9.7 / 1.1 / 13.8 % (1 / 10 / 100 /
  1000); under core refugia 63.8 / 7.7 / 0.0 / 28.4 %. Cost 1000 = 189,677 km²: 78% with raw gHM < 0.05,
  median elevation 2,183 m; by elevation band (km², mean gHM): < 500 m 7,083 (0.15); 500–1,000 27,206
  (0.27); 1,000–1,500 23,932 (0.15); 1,500–2,000 28,513 (0.07); 2,000–2,500 53,800 (0.03); > 2,500
  49,142 (0.02).
- **R0.4 The source's terrain rules confirmed on the data.** 96.4% of Y2Y cells above 2,300 m are cost
  1000; 73% of cells with slope > 30° on the 300 m DEM. Decomposition of Y2Y's cost 1000: 46.0%
  elevation > 2,300 m, +6.4% slope > 30° (52.4% either), 21.6% settled (gHM ≥ 0.05), 1.9% Natural Earth
  lakes, 28.1% natural / gentle / < 2,300 m (glaciers, HydroLAKES lakes, large rivers — median elevation
  1,573 m). Under core refugia (90,532 km² of cost 1000): 61.0% elevation, 12.0% slope (70.8% either),
  4.0% settled, 0.3% NE lakes, 27.2% remainder (median elevation 1,903 m).
- **R0.5 Machine / cost model.** 24 GB RAM, ~21 GB free disk; full-grid float32 CWD = 189 MB per node,
  compact = 69 MB; the north's empirical CWD pass ≈ 35 s at 16.2 M cells → ~1.5–2.5 min per pass here
  (notebook 01's probe re-measures).

## R1. Gates — measured [notebook 01/02, PENDING Ethan's run]

| gate | value |
|---|---|
| G2 (cost warp) | **PASS (build-time smoke 2026-09-28)**: 4,285 × 11,038 @ 300 m, ESRI:102008; 17,240,740 routable cells (36.5% of the window rectangle; 1,551,667 km²); class shares 74.6 / 10.0 / 2.0 / 13.4 % (buffered study area) |
| GW1 (class warp; seam split) | **PASS (build-time smoke 2026-09-28)**: 4,285 × 11,038 @ 300 m on the cost grid; 100.00% of routable cells inside the Y2Y polygon classed (88.5% of all routable cells — the 20 km buffer ring carries no refugia class, as expected; the gate judges coverage inside the unbuffered polygon). Seam split (middle-column 53.97 °N, km²): class 2 north 62 / south 203,121; class 12 north 113,326 / south 2,314; class 11 north 114,740 / south 2,290; class 1 north 12 / south 52,945 — the seam is not a straight parallel in Albers, hence the few thousand km² either side. |
| GW2 (variant change set) | pending |
| G0 / GW3 | pending |
| G3 / GW4 / G15 | pending |
| G10 / G9 | pending |

## R2. The variant surface [build-time smoke of `cp.terrain_layers` → `calibrate_human_tau` → `derive_variant` 2026-09-28 — notebook 01 reproduces it]

- **R2.1 Layers on the routing grid** (buffered study area, 1,551,667 km² routable; cost 1000 = 208,132 km²):
  elevation > 2,300 m 91,319 km² (96.1% of it is cost 1000 — the source rule confirmed) · slope > 30° 27,375 km² (69.1%
  cost 1000: the 300 m slope proxy is looser than the source's) · RGI 7.0 glaciers 12,026 km² (81.7% cost 1000 — the
  glacier rule confirmed) · HydroLAKES ≥ 10 ha 17,539 km² (85.1%) · HydroRIVERS > 28 m³/s 4,418 km² (81.6%) · ocean 0 (the
  cutline holds no sea). Cost 1000 explained by no natural layer (= the human layers): 83,508 km² (40.1%).
- **R2.2 Human proxy.** τ = 0.130 on the 90 m gHM maximum (balanced accuracy 0.633; TPR 0.43, TNR 0.84; TP 35,857 / FN
  47,651 / FP 220,036 / TN 1,123,499 km²). A weak proxy for the human layers in general, but immaterial to the variant:
  terrain cells coincident with a retained layer total only **2,831 km²** (kept at 1000), and the variant never raises a cost.
- **R2.3 The variant.** **104,604 km² withheld**: elevation 85,435 km² (41.0% of cost 1000), slope 18,427 (8.8%), glacier
  9,820 (4.7%); by elevation band < 1,500 m 4,960 · 1,500–2,000 9,216 · 2,000–2,300 4,992 · 2,300–2,500 36,700 · > 2,500
  48,735 km². Cost 1000 208,132 → 103,529 km²; class shares 74.6 / 10.0 / 2.0 / 13.4 % → 81.4 / 10.0 / 2.0 / 6.7 %.
  GW2 passed (only cost-1000 cells changed, none raised, classes ⊆ {1, 10, 100, 1000}, grid identical); G2 on the variant
  passed.
- **R2.4 Under core refugia** (318,822 km²): cost 1000 90,538 km² (28.4%) → **67,361 km² withheld (74.4% of it)**; 7.3% of
  core stays cost 1000 (lakes, rivers, human proxy and cost-1000 cells no natural layer explains).
- **R2.5 Cost.** terrain layers 32 s (HydroLAKES read over the Y2Y box), τ < 1 s, derivation 2 s; peak RSS 3.8 GB.

## R3. Nodes [build-time smoke of `cc.node_patches` 2026-09-28 — notebook 01 reproduces it]

- **R3.1** Core refugia 318,822 km² in 1,845 8-connected patches on the engine grid; marginal 169,988 km².
  Ladder: ≥ 250 km² 130 patches (88.8% of core area) · **≥ 500 → 67 (81.7%)** · ≥ 1,000 → 36 (75.0%).
  **67 nodes**, node land 260,613 km², largest 78,454 km², smallest 501 km². (The build-time scratch grid
  gave 66: one patch sits at the floor and crossed it with the engine's snapping.)
- **R3.1a (SUPERSEDES R3.1's node count; floor 500 → 250 km², Ethan 2026-09-28 after check stop 1):** ladder on the engine
  grid ≥ 100 km² 239 patches (94.2% of core) · **≥ 250 → 130 (88.8%)** · ≥ 500 → 67 (81.7%) · ≥ 1,000 → 36 (75.0%). **130 nodes**,
  node land 282,996 km² (43.5% of it inside existing PAs or proposed IPCAs), largest 78,454 km², smallest 254 km². Sub-floor
  patches of 50–500 km² (measured before the change): 286 holding 47,608 km² (14.9% of core), median 6.9 km from the nearest
  ≥ 500 km² node; within 5 km 120 patches / 7.0% of core. Compute at 250 km²: CWD ≈ 4.3 h at ~2 min per node, cache ≈ 9 GB
  compact, masks ≈ 6 GB.
- **R3.2** Naming (W9): at the 250 km² floor 51 nodes are named by PA overlap ≥ 10% and 79 by nearest PA + bearing (at 500 km²: 34 / 33). Several northern
  patches share a nearest PA (six "Nááts'Ihch'Oh …" variants, five "Nahanni …"); labels stay unique
  through the R-code, and `node_names.csv` is where Ethan renames. `node_patches` ran in 6 s at a
  5.2 GB peak RSS.

## R4. Baseline network [v2_run001, Ethan 2026-09-28; the withheld-terrain surface, 130 nodes, inherited cutoff 13.6229]

- **R4.1 Network:** 170 links = 129 minimum-network (MST) + 41 affordable backups (β = 2.5); no adjacency edges; ONE
  connected group. **47 links with no affordable alternative (D7 irreplaceable).**
- **R4.2 Corridor land:** 52,572 km² of new land (nodes excluded); **33,907 km² outside PAs and proposed IPCAs** (36% of
  corridor land already lies inside protected land). W11: **26 links already connected within existing PAs, 23 more only
  once the proposed IPCAs are realized** (centre-line ≥ 0.95 inside nodes + protected land).
- (MST-only area at the inherited cutoff, priority tiers, per-class counts: read from the run's `corridor_summary.json` /
  `criticality.csv` for the write-up.)

## R5. Products [v2_run001, notebook 03, Ethan 2026-09-28]

- **R5.1 Route branches (D12, the pre-amendment topology-only flag; SUPERSEDED by R5.3 on the re-run):** 133 of the 170 links had
  one branch at 0.5× cutoff under the retired fixed 10 km² floor. Near-optimality surface written (G10 passed in the notebook).
  (Under D12 as amended, one branch alone is not route-irreplaceable — the width condition must hold — and the branch floor is
  relative, so this count is a topology statement, kept for continuity as `route_irreplaceable_topo`.)
- **R5.2 The counterfactual width (D17; notebook 03 re-run, Ethan 2026-09-28; read off the run record):** constants pinned into
  `run_config.json` before any count was read (`width_floor_cells` 8, `len_floor_cells` 10, `branch_min_frac` 0.05, `branch_min_cells` 20,
  tiers cutoff/6, /2, /1; `cutoff_detour_km` 4.087). **130 of the 170 links are NEAR-CONTIGUOUS (D25) — none with a cost-1000 barrier on
  the path**; 0 links width-not-assessable (D24). Near-contiguous links: least-cost path 3–68 cells (0.9–20.4 km, median 12.5 cells = 3.8 km)
  against a barrier-free median band width of 14–511 cells (median 64.5). The 40 corridor links: path 26–562 cells (7.8–169 km, median
  169 cells = 51 km), width 24.5–156 cells (median 66). Reading: with a median node spacing of 2.6 km, most links join patches closer than
  the band is wide — on open ground the counterfactual band between two patches is wider than the path whenever the path is shorter than
  roughly twice the 4.1 km detour allowance (more when the patches present wide fronts), so D25 absorbs 76% of the links by construction of
  the network, not by any barrier. Floor effect (G19): halved / doubled floors move ZERO links. (Runtime and cache size of the compact
  counterfactual set: Ethan's notebook output — not recorded here.)
- **R5.3 Link classes (D23; `class_truth_table.csv`, same run):** eight-cell table over the 40 corridor links — E·B1·¬S 3 → last affordable;
  E·¬B1·S 1 → last affordable; ¬E·B1·S 13 → narrowing; ¬E·B1·¬S 20 → options; ¬E·¬B1·S 2 → narrowing; ¬E·¬B1·¬S 1 → options; **E·B1·S = 0
  → NO link in the top class "only viable connection"**. Counts: only viable 0 · last affordable 4 · already narrowing 15 · options 21 ·
  adjacent (no corridor needed) 130 · adjacent (barrier between) 0. Route branches under the relative floor: 44 (170 links; R5.1's
  topology-only count of 133 route-irreplaceable is superseded — 33 of the 40 corridor links have one branch, 14 of those also narrow).
  Package consequence: the examples fill from "last affordable" (4 links) by p10 width, 3 examples across the acts. `alt_kind` shares,
  G21 moved-links list and G22: in the notebook output (04's numbers cell prints them).

## R6. Director package [notebooks 04/05, PENDING]

Class counts per legend = R5.3 (0 / 4 / 15 / 21 + 130 adjacent); examples per act under the class-and-width-first rule (3, all from
"last affordable" — the top class is empty); tables T0/T3/T2/T4/T1 + GIS written by the slimmed 04; 05's five outputs (PENDING Ethan).


## R7. v2.5 — the two-layer product: complexes from v2_run001, the network re-routed between them [v25_run001; run spec v3 §1a revised
2026-09-29; PENDING Ethan's run of 05 → 06 → 07 → 08]

- **R7.0 Build-time read of the v2 record (2026-09-28, the module run into a scratch folder; notebook 06 reproduces it):** 130 patches +
  130 near-contiguous links → **23 complexes** (15 single-patch; Sustut 43 patches / 29,570 km²; Jasper 24 patches / **135,778 km²**;
  Selway-Bitterroot 7 / 31,816; Yellowstone 7 / 28,270; Nahanni 20 / 20,657; Northern Rocky Mountains 10 / 14,860; Glacier 2 / 13,557 —
  the two-patch Glacier complex = Glacier NP + Bob Marshall); complex land = the patch total 282,996 km². The 40 corridor-class links
  = **37 inter-complex** (27 complex pairs; 10 pairs joined by two links) **+ 3 within one complex** (β-backups 19–34 km: Mount Edziza ↔
  Todagin, Hoskins Lake ↔ Cabinet Mountains, Anaconda Pintler ↔ Sapphire Divide — listed with the slivers). **Coverage vs expectation**
  (routable frame: PAs 13.0% · +IPCAs 11.0% · core 3.3% · outside all three 73.0%): complexes (area-weighted) PAs **35.4%** · +IPCAs 8.1% ·
  core 7.5% · outside **49.7%**; corridor bands PAs 20.2% · +IPCAs 9.2% · core 4.2% · outside **66.4%**; **35 of the 37 inter-complex links cross
  land outside PAs + IPCAs.** Core = the balanced tier on allocatable land, 51,580 km² at 1 km → 51,575 on the 300 m grid. **Accounting:**
  all bands (the v2 corridors.tif) 52,572 km²; the 40 corridor-class links dissolved **36,230 km²** (per-link sum 39,181); outside PAs +
  IPCAs **24,995**, outside PAs + IPCAs + core **23,779**; branches {1: 36 links, 2: 4} → 44 = branches.csv. **Slivers:** 133 (130 + 3),
  62 with a cost-100/1000 cell ON THE PATH (the within-complex pinch points), 43 touch cost 10; path length median 3.9 km, max 33.9.
  **Acts (two, 51 °N):** north 12 complexes / 204,433 km² (30% in PAs, 41% with IPCAs, 9% core) / 18 corridor links / 4 narrowing / 2
  last-affordable; south 11 / 78,563 km² (49% / 49% / 4%) / 19 / 9 / 2. **Bow Valley check: 0 corridor links within 60 km of Banff** —
  the Banff–Yoho land lies inside the Jasper complex, so nothing straddles the break. Top class empty. Last affordable: Sustut ↔ Sustut E
  (p10 0.61), Sustut E ↔ Babine River (0.23), Glacier ↔ Mission Mountains (0.05, two branches), Absaroka Beartooth ↔ Yellowstone (0.32).
  Names: 14 patch display names repeat inside complexes (six 'Refugium (Nááts'Ihch'Oh)') — collapsed under 'Refugia complex (Nahanni)'.
- **R7.1 The contracted network (PENDING, `v25_run001`):** inter-complex links (MST + backups), links per class, the eight-cell table, D7
  irreplaceables as complex pairs (the four v2 corridor-level ones expected to survive, H-W2 informally), the second-pass count, W11,
  corridor land dissolved / outside PAs + IPCAs / outside PAs + IPCAs + core. (R7.0's coverage and accounting were measured on the v2
  patch-to-patch links and are SUPERSEDED by the contracted run's; R7.0's complexes, names and slivers stand.)
- **R7.2 Coverage (PENDING):** complexes and corridor bands vs the expectation row (PAs / +IPCAs / core / outside).
- **R7.3 Accounting (PENDING):** dissolved unions vs per-link sums; branches reconciled.
- **R7.4 Headline table (PENDING; `director_package/tables/headline.json`):** complexes + share protected by act; corridor links + share
  crossing unprotected land; corridor land outside PAs, IPCAs and core; narrowing links by act; the last-affordable links with p10;
  the Bow Valley act check.
