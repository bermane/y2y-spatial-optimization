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

## R2. The variant surface [notebook 01, PENDING]

τ, confusion table, km² withheld per rule (Y2Y-wide / under core / by elevation band), class shares
before → after, terrain kept at 1000 by a retained layer.

## R3. Nodes [build-time smoke of `cc.node_patches` 2026-09-28 — notebook 01 reproduces it]

- **R3.1** Core refugia 318,822 km² in 1,845 8-connected patches on the engine grid; marginal 169,988 km².
  Ladder: ≥ 250 km² 130 patches (88.8% of core area) · **≥ 500 → 67 (81.7%)** · ≥ 1,000 → 36 (75.0%).
  **67 nodes**, node land 260,613 km², largest 78,454 km², smallest 501 km². (The build-time scratch grid
  gave 66: one patch sits at the floor and crossed it with the engine's snapping.)
- **R3.2** Naming (W9): 34 nodes named by PA overlap ≥ 10%, 33 by nearest PA + bearing. Several northern
  patches share a nearest PA (six "Nááts'Ihch'Oh …" variants, five "Nahanni …"); labels stay unique
  through the R-code, and `node_names.csv` is where Ethan renames. `node_patches` ran in 6 s at a
  5.2 GB peak RSS.

## R4. Baseline network [notebook 02, PENDING]

MST-only new land at the inherited cutoff (the north's R4 analogue: 18,150 km² on 41 edges); edges
(MST / backup / adjacency); irreplaceable links (D7); corridor km²; network groups; priority tiers km²;
W11: links already connected within existing PAs / only with the proposed IPCAs; corridor land inside PAs,
inside IPCAs, unprotected (km²).

## R5. Products [notebook 03, PENDING]

Near-optimality tiers km²; route branches; route-irreplaceable edges.

## R6. Director package [notebooks 04/05, PENDING]

Class counts (both / edge / securing; squeezed withheld), examples per act, QA checklist result.
