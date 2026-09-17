# Report-back — the curated block (manifest v3.1) run end to end, and the director package on it

*2026-09-15 · for the spec chat · zero new solves since the guarded sweep (18) and the necessity test (18b/18c) · logs: methods M2.11, M4.26–M4.33
(+ addenda), results R10.19–R10.23.*

## 1. What was run

Manifest v3.1 (sha 259f35ed…): the 12 design formulations on the curated 20-feature representativeness block with window-derived
rarity-scaled targets (rule R0, spec v0.17–v0.17.3). Solved and analysed in numeric order: 12 (anchors, MGA k = 50 at g = 5%, LP
twins; 4.0 h) → 13, 15 (unguarded surface, E-round statistics) → 18 (guarded sweep, the applied result; 12.2 h) → 18b/18c (the
necessity test E19) → 19/20 (package v1.7) → 21 (the presentation set, added 2026-09-14). Integrity clean throughout: 600/600 guarded
members in band, 0 duplicates, 0 time-limited; every LP twin ≤ its anchor; re-solved anchors reproduce 12's objectives to ≤ 1e-11.

## 2. The headline results (R10.20–R10.21)

- **The unguarded (Claim-A) frequent tier all but vanishes on the curated block: 6,306 km² → 4 km² at F ≥ 0.70.** 99% of the old
  tier sat on a ≤1%-footprint class: the shared land across all twelve positions was rarity-pinned artifact land, as R10.18 diagnosed.
  The pluralism result sharpens — almost no cell is required by every value position within 5% of optimal.
- **The guarded (applied) core GROWS: 16,895 km² → 29,194 km² (2.7% of allocatable land).** 1,077 km² lost (99.4% on old
  ≤1% classes — the artifact land, gone as designed); 13,376 km² gained, two thirds inside the densest-refugia mask. Mechanism (M4.31):
  the band is 5% of the optimum and the optimum fell ~8% once the block stopped paying shortfall on artifact classes, so the absolute
  tolerance tightened. Composition: 82% densest refugia, 2.7% soil-carbon tail, 1.1% on any old small class (v1 8.2%).
- **Refugia futures:** core under SSP585 alone 31,358 km², under SSP245 alone 41,083 km², both
  19,296 km²; 83% / 83% of the 12-formulation core lies inside each.
- **The necessity test (E19): nothing is forced.** Adequacy-forced set 0 km²; EFG-necessary core 0 km² (the union of leave-EFG-out anchors
  keeps every core cell); the T3 gate is closed; no adequacy pins in the register. E17 re-measured: removing the block moves the anchors
  +0.02 to +0.22°N (S0 +0.14°N) against +2.11°N on the 40-class block — the southern pull was the artifact classes.
- **E-round on v3.1:** within-formulation degeneracy share 0.961; E1 bias mean 0.179; E11 107/132 pairs
  mutually in-band; D_s 0.836–1.000; the E14 trigger fires again; E17-T2 southern statistic 9/20.

## 3. The package on v3.1 (R10.22, now measured)

**Tiers (guarded, 12 design formulations; shares of 1,081,885 km² allocatable land):** core 29,194 km² (2.7%); scenario tiers
70,166 km² (6.5%), split by the position that earns each cell — core-habitat-forward 31,308 (2.9%),
carbon-forward 23,805 (2.2%), connectivity-forward 8,429 (0.8%),
biodiversity-forward 271 (0.03%), two or more 6,353 (0.6%);
opportunity (in ≥ 1 plan) 955,262 km² (88.3%); never 27,263 km² (2.5%).

**Deck clusters (M4.33 + addenda i, k):** the six core complexes group into four regional clusters (75 km single linkage), numbered
north → south; nearby kept complexes (≤ 75 km) and sub-100 km² core specks (≤ 10 km) join the nearest cluster:

| Cluster | km² | mean F | leading value |
|---|---|---|---|
| 1 SW of Tahltan - Sacred Headwaters | 11,490 | 0.78 | core habitat 3.5× |
| 2 Purcell Wilderness Conservancy Park vicinity | 12,105 | 0.83 | core habitat 3.9× |
| 3 N of Granby Park | 2,507 | 0.80 | core habitat 3.1× |
| 4 NW of Frank Church River Of No Return Wilderness | 5,229 | 0.84 | core habitat 4.5× |

**Consequences (T-D7; mean value in the area ÷ mean over allocatable land):**

| | core habitat | connectivity | biodiversity | carbon | representativeness | naturalness |
|---|---|---|---|---|---|---|
| Cluster 1 (11,490 km²) | 3.5× | 1.2× | 0.82× | 1.4× | 1.3× | 1.0× |
| Cluster 2 (12,105 km²) | 3.9× | 0.99× | 1.2× | 1.2× | 1.2× | 1.0× |
| Cluster 3 (2,507 km²) | 3.1× | 0.76× | 1.4× | 0.81× | 1.1× | 0.88× |
| Cluster 4 (5,229 km²) | 4.5× | 0.86× | 1.3× | 0.19× | 1.4× | 1.0× |
| Existing protected areas (191,029 km²) | 1.3× | 0.97× | 1.0× | 1.1× | 1.2× | 1.0× |
| Proposed IPCAs (unprotected part) (86,360 km²) | 1.0× | 1.1× | 0.90× | 1.0× | 1.1× | 1.0× |

Existing protected areas remain value-average on every axis (R10.4 holds on v3.1); the unprotected part of the IPCA proposals is
average on every axis but connectivity, with mean F 0.15 — the proposals and the ensemble point at different places.
Naturalness is compressed against its ceiling (allocatable mean 0.94, 77% of cells ≥ 0.95), so its ratio spans 0.88–1.05 while
the star percentiles spread; kept as a ratio at Ethan's call.

**Values (Act 0) → tiers (hinge):** of the core, 90% is top-30% land for ≥ 2 of the five themes and
24% for ≥ 3; the representativeness vote (presence of a window-rare class: F1.1 streams, F2.1 large lakes) covers
6,287 km² (0.6% of allocatable land), 0.3% of it inside the core.
Biodiversity capture over the 612 guarded plans: 29–35% of AOH richness (median 31%) whichever value leads — almost no land of its own.

**E19 partition of the core:** 0% forced, 90% multi-claim (top-30% for ≥ 2 non-EFG themes), 10% other;
the carbon-forward tier is the least multi-claim (45%) — the target's land, not a convergence of values.

## 4. Presentation rulings taken on the way (package-spec deviations for the chat to carry)

1. **Act numbering follows this analysis:** Act 0 = the values prologue; Act 1 = the core; Act 2 = the scenario tiers; Act 3 = the
   opportunity landscape (overrides v1.6's four-act renumbering; M4.33 addendum).
2. **"Intactness" → "naturalness"** in every output (feature name unchanged).
3. **Deck picks = regional clusters** (75 km single linkage, N → S numbering) that absorb nearby complexes (≤ 75 km) and core specks
   (≤ 10 km); the 100 km² floor and the 25 km complexes are unchanged for the paper.
4. **Consequences = ratios to the average allocatable cell** (per act, with reference rows for PAs and IPCAs), replacing percentiles
   in the directors' tables; percentiles stay on the stars and in T-D1.
5. **Cartography:** 1 km surfaces, no hex aggregation, on the northern package's basemap (Natural Earth land/water, GLO-90 hillshade,
   jurisdiction codes, towns); Act 1 = two slide-shaped maps with inset windows; **Act 2 = one map** (tiers by owning scenario, three
   windows, area + share legend; no Act 2 pairings/stars/tables in the presentation — they remain in the 20 record).
6. **Tables** render to Ethan's Y2Y Table Spec (`spec_table_png`); the objectives table exists in full and bare-bones forms.
7. **Naturalness** stays a ratio row despite its compression (see §3).

## 5. Open for the chat

- Ratify R10.22 as the package record on v3.1 and the rulings in §4 as package-spec text (v1.8).
- Cluster names (decision e): the register still carries "nearest named area + bearing" placeholders; the deck says "Cluster N".
- E17 placement (f): the one-pager now carries the v3.1 shifts (+0.14°N for the block); its slide position is unchanged.
- T-D4 (tier area by ecoregion) still waits on a layer in `input_data/ecoregions/`.
- The developed-land PU mask (R10.23) is parked: ~1% of the PU by any threshold; not worth a re-solve for the core's size.
- Alberta stage 2 (09b → 13 on v3.1) is built and pending Ethan's run; the AB spec mirror is at v0.5.
