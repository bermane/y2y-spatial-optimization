# EFG representativeness block — report-back for the spec chat (2026-09-08)

**Scope: both extents — the Y2Y-wide flagship (`analyses/y2y/`, spec v0.16.1 / package v1.6) and the Alberta mirror
(`analyses/alberta_prioritization/`, spec v0.4.7).** Zero-solve; every number below is read off frozen artifacts
(AB `analysis/ab4/`, Y2Y `director_package/`, both aligned stacks, and the GET archive's own `map-details.xml`).
Log entries: AB results_log **R7.9–R7.11**; Y2Y results_log **R10.18**. Nothing in either formulation has been changed;
AB notebooks 12–13 (director package) are parked pending the decisions in §6.

## 0. Headline

The representativeness block (one IUCN GET Ecosystem Functional Group = one feature, each weighted 1/n, target 1.0,
capture scored against the class's own total on the extent) rewards **the smallest cartographic slivers of the GET
indicative maps** — a misplaced point record, ecoregion envelopes overshooting a border, and clip artifacts where an
ecoregion crosses the study-area line. Per-cell class value ∝ 1/footprint, so these cells are the cheapest
"representativeness" in the problem and every formulation buys them; the frequency core inherits them at F ≈ 1.

- **Alberta:** 71% of the kept 2%-band core km² (766 of 1,073) sits ≥ 87% inside one of four such classes; the largest
  core cluster (412 km²) is the GET "Subglacial lakes" polygon in ice-free foothills. Only one of six core picks is a
  genuine multi-value core.
- **Y2Y-wide:** the five smallest classes (3 to 409 cells) are **100% inside the Act 2 core**; 8.2% of core cells sit on
  ≤ 1%-footprint classes; 12 of 99 register clusters (3,983 km²) are ≥ 50% inside one; **deck pick #11 (Act 3
  biodiversity-forward, 348 km²) is 100% inside the flooded-mines / freshwater-aquafarms / episodic-rivers envelopes**,
  pick #12 (234 km²) is 99% one cool-desert class; and **27.9% of the v1.6 Act 1 "representativeness" value layer is
  subglacial lakes + flooded mines + aquafarms.** Picks #1–#10, #13, #14 are clean (≤ 4%). **The Act 3 biodiversity-forward
  tier is 40.6% inside ≤ 1% classes (16.5% on subglacial lakes / flooded mines / aquafarms alone)** versus 7–9% for the
  other tiers — consistent with E18's finding that AOH richness never pins: what the biodiversity scenario "owns" is
  largely the EFG block completing map slivers.

## 1. Mechanism (why this happens)

Each class holds 1/n of the block regardless of extent (1/27 in AB, 1/40 in Y2Y) and its capture is a fraction of the
class's own total, so a cell's contribution to the class's shortfall term is (1/n)/footprint. A 409-cell class is worth
~3,000× more per cell than a 1.2-million-cell class inside the same block; the 3-cell Y2Y salt-lake class is worth
~400,000× more. Nothing in the block distinguishes a real rare ecosystem from a rare artifact — it only sees scarcity.
This is the flip side of E13's "binding scarcity" and of the "36/40 rare-attainable" audit result: rare-attainable
classes are exactly the ones every solution completes, and the audit never asked whether the class footprint was real.

A reading (consistent with the numbers, not separately measured): within a g-band, dropping any one class fully costs
the same 1/n of the block, so max-Hamming members discard the classes whose full drop *frees the most cells* and keep
the tiniest ones — which is why on Y2Y a 1,429-cell class (F1.1) is 0.3% in core while five classes of 3–409 cells are
100% in core. The frequency core is, in part, "the classes cheapest to hold".

## 2. What the GET indicative maps are

The archive README: maps have a spatial grain of **10 arcmin to 1 degree** and *"should be used to query which EFG are
likely to occur within areas, rather than which occur at particular point locations."* Per-class construction from
`map-details.xml` falls into: **direct** (inventory/habitat maps: HydroLAKES, GLIMS, Jung 2020, WHYMAP, GloRiC),
**proxy** (land cover or hydrography clipped to selected ecoregions), **envelope** (whole freshwater/terrestrial
ecoregions selected by description + expert review, painted in full), and one **point-record** map (F2.10, from the
Antarctic/Greenland/Iceland subglacial-lake inventories). Envelope construction is not disqualifying per se — T4.4
Temperate woodlands is an envelope and in Alberta the envelope *is* the aspen-parkland strip — but a small envelope
footprint on our extent is almost always an edge of a polygon centred elsewhere.

Anthropogenic biomes in the block (a separate purpose question): **12 of 40** Y2Y classes (T7.1–T7.5 croplands /
pastures / plantations / urban / derived pastures; F3.1 / F3.2 / F3.4 / F3.5 reservoirs / constructed wetlands /
aquafarms / canals; SF2.1 / SF2.2 pipes / flooded mines; S2.1 anthropogenic subterranean voids) and **10 of 27** in AB.

## 3. Alberta findings (R7.9–R7.11)

Core picks at the applied 2% band (10 km² clusters, level A):

| pick | km² | pinning class | what the map actually is there | verdict |
|---|---|---|---|---|
| 1 (53.4°N, Lower Foothills) | 412 | F2.10 Subglacial lakes — 99% of cluster = 100% of class | 409 "major" cells = one point record, 121 km from the BC border, no glacier within ~100 km; the Rockies' icefields carry no F2.10 at all | physically impossible: misplaced record |
| 2 (50.3°N, Foothills Parkland) | 275 | T4.4 Temperate woodlands + connectivity 1.2× / corridors 1.3× / refugia 1.1× | aspen-parkland strip, 1,302-cell body, 37 km from any border | **genuine** |
| 3, 4 (49.7–50.0°N, Mixedgrass) | 310 | T5.1 Semi-desert steppe **+ SF2.2 Flooded mines** (clusters hold 90% of the class) | SF2.2 = whole ecoregions "with concentrations of flooded-mine records"; AB footprint = the strip where that prairie ecoregion crosses the Y2Y line (median 4 km, max 11 km from it); every other value below the unprotected mean | anthropogenic envelope edge |
| 5, 6 (50.0°N / 49.6°N, Subalpine/Montane) | 44 | F2.9 Geothermal pools (93%) + F3.5 Canals (87%) | both = freshwater-ecoregion envelopes overshooting the divide: AB cells median **0.7 km / 0.5 km from the BC border**, 73% / 68% inside national parks; #5 also SOC 8.5× (real) | envelope overshoot |

Correction to my first reading: the classes *belong* in Alberta (irrigation canals, Lethbridge's flooded workings,
Banff/Miette/Mist Mountain hot springs are all real); only subglacial lakes are impossible. What is wrong is the
footprint the maps give them here. The anthropogenic T7.x / F3.1 / F3.2 classes have broadly correct footprints
(3–49% of the AB PU) and drive none of the picks.

Other AB context: 32.9% of the PU is locked; 5% band flat (D ≈ 1, empty frequent tier) → applied band g = 2%; the
2% core is 1,073 km² total, so a 412 km² artifact is not a footnote — it is the largest thing on the map.

## 4. Y2Y-wide findings (R10.18)

Measured on `director_package/` (12 design formulations, guarded F, core = F ≥ 0.70 on discretionary cells = 16,895 km²):

| item | measurement |
|---|---|
| Five smallest classes — F2.6 salt lakes (3 cells), F2.2 small lakes (9), F1.4 seasonal streams (93), F2.3 seasonal lakes (222), F2.10 subglacial lakes (409) | **100% of unlocked cells inside the core** (734 km²) |
| Core cells inside any ≤ 1%-footprint class (13 classes) | 1,377 of 16,895 (**8.2%**) |
| Register clusters ≥ 50% inside a ≤ 1% class | **12 of 99**, 3,983 of 108,853 km² — the F2.10 polygon (412 km², Act 2 register cluster "NE of Jasper 53.4°N", not a numbered pick) + a Wyoming group (Bridger / Gros Ventre / Jedediah Smith: SF2.2 flooded mines, F3.4 aquafarms, F1.6 episodic rivers envelopes) + T5.4 cool deserts in Idaho |
| Deck pick **#11** "NW of Bridger Wilderness", Act 3 biodiversity-forward, 348 km² | **100%** inside ≤ 1% classes: SF2.2 85% / F3.4 100% / F1.6 100% |
| Deck pick **#12** "SW of Frank Church", Act 3 biodiversity-forward, 234 km² | 99% T5.4 Cool deserts (a real land-cover class at 0.18% of PU — scarce, not spurious) |
| Deck picks #1–#10, #13, #14 | 0–4.2% inside any ≤ 1% class — clean |
| v1.6 Act 1 `value_top30_representativeness` (= presence of a ≤ 1%-footprint EFG), 32,108 cells | **27.9%** on F2.10 / SF2.2 / F3.4; 2.3% on the < 0.1% slivers |
| `value_convergence` ≥ 3 (51,818 cells) | 4,324 cells reach 3 only through representativeness |

Tier composition (share of tier cells inside ≤ 1% classes / inside the Option-A drop classes):

| tier | km² | any ≤ 1% class | F2.10 + SF2.2 + F3.4 |
|---|---|---|---|
| Act 2 core (12-formulation F ≥ 0.70) | 19,295 | 7.5% | 4.2% |
| Act 3 core-habitat tier | 53,903 | 6.7% | 4.6% |
| Act 3 connectivity tier | 12,054 | 9.1% | 5.3% |
| Act 3 biodiversity tier | 9,077 | 40.6% | 16.5% |
| Act 3 carbon tier | 40,803 | 8.8% | 2.8% |

Parent exposure is therefore bounded (~8% of core, 2 of 14 picks, one register cluster, the Act 1 representativeness
layer) rather than structural as in Alberta — because on the Y2Y extent the envelope classes that pin Alberta (F2.9
40% of PU, F3.5 19%) are far too large to pin, and the exposed classes are the boundary slivers.

## 5. Options (candidate rules; none applied)

Three separable rules; the appendix tables show each class's verdict under each.

- **A. Map-method rule.** Exclude point-record classes, and envelope-method classes whose footprint on the extent is
  < 1% of the PU (direct / proxy classes kept at any size — T6.1 glaciers at 0.2–0.3% stay). Justification = the GET's
  own statement of what its maps are for. Y2Y drops **3** (F2.10, SF2.2, F3.4) → 37 classes; AB drops
  **4** (F3.5, SF2.2, F2.10, F2.9) → 23.
- **B. A + sliver floor.** Additionally exclude any non-direct class below 0.1% of the PU (clip artifacts where an
  ecoregion crosses the study-area line). Y2Y drops **7** (A + F2.6, F2.2, F1.4, F2.3) → 33; AB unchanged
  (23). A 1% floor instead would also take F1.1, T5.4, F1.6, T2.2 on Y2Y (→ 29) — range-edge but real
  ecosystems; not recommended without a purpose argument.
- **C. Purpose rule.** Exclude anthropogenic biomes from a *conservation* representativeness block (T7.x, F3.x,
  SF2.x, S2.1). Y2Y 40 → 28; AB 27 → 17. Separable from A/B; it drove none of the AB picks, but on Y2Y
  it removes the two classes under pick #11 (SF2.2, F3.4) and F3.5 / F3.2 / SF2.1, which are large envelopes.
- **D. Keep the frozen results, change the presentation.** Strip the Option-A classes from the Act 1 representativeness
  layer and driver attribution, label the F2.10 cluster and pick #11 as map artifacts, disclose in E17. No re-solve,
  but the F surfaces still carry the cells and the AB core would remain 71% artifact.

Recommendation: **A + C for Alberta (re-run 10–13), and for Y2Y at minimum A on the representativeness value layer and
the register (presentation) with the re-solve decision taken on cost.** B is a judgment call I would leave with the
chat: the < 0.1% classes are 5 on Y2Y and they are the ones sitting at 100% core.

Costs of re-solving. **Alberta:** 10 (ensemble, 2.3 h) → 11 → 12 → 13, plus 09 re-freeze (manifest hash changes) and
the 02 audit re-run for the block card; ~3 h solve + notebooks; C1/C2 scale-transfer comparisons become block-mismatched
against the frozen parent unless the parent moves too. **Y2Y:** the block is in every solve — Gate-4 ensemble
(12 formulations, MGA + anchors + twins; the 14-formulation run took ~22 h wall) + guarded sweep (12.3 h) + 13b / 15–17 /
19 / 20; E12 / E17-T3 / E18 arms would be stale but could stand as evidence with disclosure. The Gate-3 pre-registration
(manifest v1/v2 hashes) would be superseded by a v3 manifest with the trigger stated. Also re-derive: the 36/40
rare-attainable count, E17's "20/40 EFGs > 90% southern" (the Wyoming slivers are part of that skew), and the
≤ 1%-footprint companion (13 → fewer).

## 6. Decisions requested

1. Which rule(s) — A, A+B, A+C, A+B+C — and the thresholds (1% envelope cutoff; 0.1% sliver floor).
2. Y2Y scope: re-solve the ensemble under the amended block, or Option D (presentation + disclosure) for the director
   package with the re-solve deferred to the paper.
3. Alberta scope: re-run under the amended block (recommended; the current core cannot be presented as core), accepting a
   block mismatch with the frozen parent in C1/C2 if Y2Y does not move.
4. Whether the v1.6 Act 1 representativeness definition ("presence of a ≤ 1%-footprint EFG") should be restated as
   presence of a ≤ 1%-footprint *retained* class regardless of the re-solve decision.
5. How to log the amendment: it is a post-hoc formulation change discovered from results (spec amendment + methods_log
   entry stating the trigger; supersede, never delete).

## Appendix A — Y2Y-wide classes (40), sorted by footprint; A/B/C = verdict under each option

| class | name | cells | % PU | % in PAs | map method | category | anthro | A | B | C | % of unlocked class in core |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F2.6 | Permanent salt and soda lakes | 3 | 0.00% | 0% | named salt lakes (major) + arid fw-ecoregion (minor) | mixed |  |  | drop |  | 100% |
| F2.2 | Small permanent freshwater lakes | 9 | 0.00% | 0% | small lakes ∩ fw-ecoregion | proxy |  |  | drop |  | 100% |
| F1.4 | Seasonal upland streams | 93 | 0.01% | 2% | streams ∩ fw-ecoregion | proxy |  |  | drop |  | 100% |
| F2.3 | Seasonal freshwater lakes | 222 | 0.02% | 0% | small lakes ∩ fw-ecoregion | proxy |  |  | drop |  | 100% |
| F2.10 | Subglacial lakes | 409 | 0.03% | 0% | POINT RECORDS (polar inventories) + snow/ice minor | point |  | drop | drop |  | 100% |
| F1.1 | Permanent upland streams | 1,429 | 0.11% | 1% | streams ∩ fw-ecoregion | proxy |  |  |  |  | 0% |
| T5.4 | Cool deserts and semi-deserts | 2,234 | 0.18% | 0% | landcover ∩ ecoregion | proxy |  |  |  |  | 4% |
| T6.1 | Ice sheets, glaciers and perennial snowfields | 2,730 | 0.21% | 49% | glacier inventories + landcover | direct |  |  |  |  | 26% |
| SF2.2 | Flooded mines and other voids | 5,288 | 0.42% | 1% | terr-ecoregion w/ flooded-mine records | envelope | A | drop | drop | drop | 7% |
| F3.4 | Freshwater aquafarms | 5,710 | 0.45% | 27% | fw-ecoregion, expert | envelope | A | drop | drop | drop | 3% |
| F2.1 | Large permanent freshwater lakes | 6,075 | 0.48% | 20% | HydroLAKES large lakes | direct |  |  |  |  | 0% |
| F1.6 | Episodic arid rivers | 8,215 | 0.65% | 19% | ephemeral water ∩ fw-ecoregion | proxy |  |  |  |  | 8% |
| T2.2 | Deciduous temperate forests | 11,495 | 0.90% | 0% | landcover ∩ ecoregion | proxy |  |  |  |  | 0% |
| T7.4 | Urban and industrial ecosystems | 15,120 | 1.19% | 2% | night lights | proxy | A |  |  | drop | 1% |
| F1.2 | Permanent lowland rivers | 23,187 | 1.82% | 15% | streams ∩ fw-ecoregion | proxy |  |  |  |  | 1% |
| T7.1 | Annual croplands | 26,595 | 2.09% | 1% | Jung 2020 habitat map | direct | A |  |  | drop | 1% |
| T4.4 | Temperate woodlands | 33,263 | 2.61% | 11% | terr-ecoregion, expert | envelope |  |  |  |  | 4% |
| S2.1 | Anthropogenic subterranean voids | 40,750 | 3.20% | 8% | terr-ecoregion, expert | envelope | A |  |  | drop | 5% |
| T7.3 | Plantations | 46,516 | 3.65% | 8% | Jung 2020 habitat map | direct | A |  |  | drop | 1% |
| SF2.1 | Water pipes and subterranean canals | 49,671 | 3.90% | 32% | fw-ecoregion w/ urban water infra | envelope | A |  |  | drop | 1% |
| T5.1 | Semi-desert steppe | 50,897 | 4.00% | 0% | landcover ∩ ecoregion | proxy |  |  |  |  | 1% |
| SF1.2 | Groundwater ecosystems | 56,842 | 4.47% | 6% | aquifer map (WHYMAP) | direct |  |  |  |  | 1% |
| T7.2 | Sown pastures and fields | 78,834 | 6.19% | 2% | irrigation ∩ livestock | proxy | A |  |  | drop | 1% |
| TF1.6 | Boreal, temperate and montane peat bogs | 83,382 | 6.55% | 7% | terr-ecoregion, expert | envelope |  |  |  |  | 0% |
| TF1.7 | Boreal and temperate fens | 83,382 | 6.55% | 7% | terr-ecoregion, expert | envelope |  |  |  |  | 0% |
| T6.2 | Polar/alpine cliffs, screes, outcrops and lava flows | 98,830 | 7.76% | 30% | gazetteer + glacier inventories | direct |  |  |  |  | 8% |
| F3.1 | Large reservoirs | 103,165 | 8.10% | 17% | reservoir points, 15-min buffer | direct | A |  |  | drop | 2% |
| T7.5 | Derived semi-natural pastures and old fields | 107,334 | 8.43% | 1% | landcover ∩ ecoregion | proxy | A |  |  | drop | 1% |
| T3.4 | Young rocky pavements, lava flows and screes | 149,811 | 11.77% | 29% | landcover ∩ ecoregion | proxy |  |  |  |  | 3% |
| T6.3 | Polar tundra and deserts | 196,397 | 15.43% | 20% | Köppen tundra + radiation | proxy |  |  |  |  | 2% |
| TF1.2 | Subtropical/temperate forested wetlands | 205,540 | 16.15% | 21% | terr-ecoregion, expert | envelope |  |  |  |  | 3% |
| F1.3 | Freeze-thaw rivers and streams | 208,825 | 16.41% | 15% | river reaches (GloRiC) | direct |  |  |  |  | 1% |
| F3.5 | Canals, ditches and drains | 240,086 | 18.86% | 17% | fw-ecoregion, expert | envelope | A |  |  | drop | 4% |
| S1.1 | Aerobic caves | 278,764 | 21.90% | 23% | carbonate outcrop | proxy |  |  |  |  | 1% |
| SF1.1 | Underground streams and pools | 278,764 | 21.90% | 23% | carbonate outcrop | proxy |  |  |  |  | 1% |
| F3.2 | Constructed lacustrine wetlands | 283,559 | 22.28% | 20% | fw-ecoregion, expert | envelope | A |  |  | drop | 3% |
| F2.4 | Freeze-thaw freshwater lakes | 491,075 | 38.58% | 15% | HydroLAKES freeze-thaw lakes | direct |  |  |  |  | 1% |
| F2.9 | Geothermal pools and wetlands | 514,094 | 40.39% | 18% | small lakes ∩ fw-ecoregion flagged for geothermal | envelope |  |  |  |  | 4% |
| T6.4 | Temperate alpine grasslands and shrublands | 812,880 | 63.86% | 18% | terr-ecoregion, expert | envelope |  |  |  |  | 2% |
| T2.1 | Boreal and temperate high montane forests and woodlands | 1,225,770 | 96.30% | 16% | landcover ∩ ecoregion | proxy |  |  |  |  | 2% |

## Appendix B — Alberta classes (27)

| class | name | cells | % PU | % in PAs | map method | category | anthro | A | B | C |
|---|---|---|---|---|---|---|---|---|---|---|
| T6.1 | Ice sheets, glaciers and perennial snowfields | 247 | 0.29% | 98% | glacier inventories + landcover | direct |  |  |  |  |
| F3.5 | Canals, ditches and drains | 254 | 0.30% | 68% | fw-ecoregion, expert | envelope | A | drop | drop | drop |
| SF2.2 | Flooded mines and other voids | 341 | 0.40% | 0% | terr-ecoregion w/ flooded-mine records | envelope | A | drop | drop | drop |
| F2.10 | Subglacial lakes | 409 | 0.48% | 0% | POINT RECORDS (polar inventories) + snow/ice minor | point |  | drop | drop |  |
| F2.9 | Geothermal pools and wetlands | 450 | 0.53% | 73% | small lakes ∩ fw-ecoregion flagged for geothermal | envelope |  | drop | drop |  |
| T4.4 | Temperate woodlands | 1,371 | 1.61% | 3% | terr-ecoregion, expert | envelope |  |  |  |  |
| T5.1 | Semi-desert steppe | 2,391 | 2.81% | 0% | landcover ∩ ecoregion | proxy |  |  |  |  |
| T7.4 | Urban and industrial ecosystems | 2,717 | 3.19% | 8% | night lights | proxy | A |  |  | drop |
| T7.1 | Annual croplands | 3,172 | 3.73% | 1% | Jung 2020 habitat map | direct | A |  |  | drop |
| TF1.6 | Boreal, temperate and montane peat bogs | 3,919 | 4.60% | 0% | terr-ecoregion, expert | envelope |  |  |  |  |
| TF1.7 | Boreal and temperate fens | 3,919 | 4.60% | 0% | terr-ecoregion, expert | envelope |  |  |  |  |
| T7.3 | Plantations | 3,975 | 4.67% | 2% | Jung 2020 habitat map | direct | A |  |  | drop |
| T7.2 | Sown pastures and fields | 5,108 | 6.00% | 5% | irrigation ∩ livestock | proxy | A |  |  | drop |
| T2.2 | Deciduous temperate forests | 5,290 | 6.21% | 1% | landcover ∩ ecoregion | proxy |  |  |  |  |
| T6.2 | Polar/alpine cliffs, screes, outcrops and lava flows | 10,206 | 11.99% | 92% | gazetteer + glacier inventories | direct |  |  |  |  |
| F3.1 | Large reservoirs | 12,214 | 14.35% | 42% | reservoir points, 15-min buffer | direct | A |  |  | drop |
| T6.3 | Polar tundra and deserts | 13,634 | 16.01% | 78% | Köppen tundra + radiation | proxy |  |  |  |  |
| S1.1 | Aerobic caves | 14,417 | 16.93% | 96% | carbonate outcrop | proxy |  |  |  |  |
| SF1.1 | Underground streams and pools | 14,417 | 16.93% | 96% | carbonate outcrop | proxy |  |  |  |  |
| F1.3 | Freeze-thaw rivers and streams | 15,487 | 18.19% | 33% | river reaches (GloRiC) | direct |  |  |  |  |
| F2.4 | Freeze-thaw freshwater lakes | 31,225 | 36.68% | 41% | HydroLAKES freeze-thaw lakes | direct |  |  |  |  |
| T7.5 | Derived semi-natural pastures and old fields | 40,793 | 47.92% | 1% | landcover ∩ ecoregion | proxy | A |  |  | drop |
| SF2.1 | Water pipes and subterranean canals | 41,668 | 48.94% | 31% | fw-ecoregion w/ urban water infra | envelope | A |  |  | drop |
| F3.2 | Constructed lacustrine wetlands | 41,922 | 49.24% | 31% | fw-ecoregion, expert | envelope | A |  |  | drop |
| T6.4 | Temperate alpine grasslands and shrublands | 44,340 | 52.08% | 62% | terr-ecoregion, expert | envelope |  |  |  |  |
| SF1.2 | Groundwater ecosystems | 47,710 | 56.04% | 7% | aquifer map (WHYMAP) | direct |  |  |  |  |
| T2.1 | Boreal and temperate high montane forests and woodlands | 82,742 | 97.19% | 34% | landcover ∩ ecoregion | proxy |  |  |  |  |

*Sources: GET indicative maps v2.1 archive (Keith et al. 2022; Zenodo 10.5281/zenodo.3546513), `README.md` and
`map-details.xml`; stacks `input_data/aligned_stack/` and `aligned_stack_ab/`; `analyses/y2y/director_package/`;
`analyses/alberta_prioritization/analysis/ab4/`. Written 2026-09-08 from the session that produced AB R7.9–R7.11.*
