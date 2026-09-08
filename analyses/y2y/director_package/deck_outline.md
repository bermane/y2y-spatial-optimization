# Y2Y director package — deck outline (spec v1.1)

_generated from analyses/y2y/director_package; n = 12 formulations_

## Slide 1 — Where Y2Y's values agree — and where they diverge

- 12 value positions (6 scenarios × 2 climate futures for refugia) × 51 near-optimal plans each
- 30% of the region; existing PAs locked in — they are 15% of the region (50% of the budget) and already bank 12–19% of every value (35/40 ecosystem groups present) — remarkably AVERAGE land for these values (enrichment 0.8–1.3×); the tiers are about the other half, where the optimizer works 1–1.7× harder per km²
- Every plan keeps every value theme within 5% of its best
- Tiers = reliability, not a fence

> Context slide. Methods live in the study plan v0.14.1; this package = director_package_spec v1.1.

## Slide 2 — How to read the maps

figure: `slide2_how_to_read.png`

- Grey = existing protected areas (fixed in every plan)
- 1 km tiers drive the clustering; cluster outlines are 1 km polygons, not hex unions
- Hexes (~250 km²) are for legibility only — our DISPLAY hex ≈ the national 30×30 analysis's PLANNING unit (100 km²); our analysis runs at 1 km², two orders of magnitude finer ('this valley', not 'this ecodistrict')
- 51 near-optimal plans × 12 value positions, versus 4 plans in the national analysis
- 53°N marked: see the E17 one-pager

## Slide 3 — Act 1 — Core commitments

figure: `act1_core_hex250.png`

- Core = F ≥ 0.70 across ALL positions: 16,895 km² of unprotected land
- These areas recur in near-optimal plans no matter whose values prevail, with no value theme left more than 5% behind
- Numbered = the largest core clusters (full register in the appendix)

## Slide 4 — Act 1 under the high-emissions refugia future

figure: `act1_core_ssp585_hex250.png`

- 6 value positions at SSP585: core 17,308 km²
- 80% of the 12-position core lies inside it
- The 12-position core = what survives BOTH refugia futures

## Slide 5 — Act 1 under the low-emissions refugia future

figure: `act1_core_ssp245_hex250.png`

- 6 value positions at SSP245: core 28,612 km²
- 87% of the 12-position core lies inside it
- The 12-position core = what survives BOTH refugia futures

## Slide 6 — Where the promise depends on the climate future

figure: `act1_two_way_climate.png`

- One hex, two refugia futures: bivariate F
- Yellow = core under both futures; orange = only if emissions run high; green = only if they stay low
- The 12-position core is what survives both

## Slide 7 — Why these places

figure: `act1_star_grid.png`

- Core clusters spike on BINDING claims (dense soil carbon, scarce ecosystems) rather than excelling everywhere
- Histogram of F: act1_F_histogram.png

## Slide 8 — Act 2 — Core-habitat-forward

figure: `act2_s1_hex250.png`

- If Y2Y leans into this value, these areas join the core
- Both refugia futures pooled into one map per scenario (divergence check in pooling_check.csv)
- Orange outlines (panel a) = Nations' declared IPCA proposals — overlap is independent convergence, not assignment
- Precedent: the national 30×30 analysis (Currie et al. 2025) reports that proposed IPCAs coincide with priority areas and that Indigenous priorities supersede top-down prioritization — rights and title are not contingent on GBF compatibility

## Slide 9 — Act 2 — Connectivity-forward

figure: `act2_s2_hex250.png`

- If Y2Y leans into this value, these areas join the core
- Both refugia futures pooled into one map per scenario (divergence check in pooling_check.csv)
- Orange outlines (panel a) = Nations' declared IPCA proposals — overlap is independent convergence, not assignment
- Precedent: the national 30×30 analysis (Currie et al. 2025) reports that proposed IPCAs coincide with priority areas and that Indigenous priorities supersede top-down prioritization — rights and title are not contingent on GBF compatibility

## Slide 10 — Act 2 — Biodiversity-forward

figure: `act2_s3_hex250.png`

- If Y2Y leans into this value, these areas join the core
- Both refugia futures pooled into one map per scenario (divergence check in pooling_check.csv)
- Orange outlines (panel a) = Nations' declared IPCA proposals — overlap is independent convergence, not assignment
- Precedent: the national 30×30 analysis (Currie et al. 2025) reports that proposed IPCAs coincide with priority areas and that Indigenous priorities supersede top-down prioritization — rights and title are not contingent on GBF compatibility

## Slide 11 — Act 2 — Carbon-forward

figure: `act2_s4_hex250.png`

- If Y2Y leans into this value, these areas join the core
- Both refugia futures pooled into one map per scenario (divergence check in pooling_check.csv)
- Orange outlines (panel a) = Nations' declared IPCA proposals — overlap is independent convergence, not assignment
- Precedent: the national 30×30 analysis (Currie et al. 2025) reports that proposed IPCAs coincide with priority areas and that Indigenous priorities supersede top-down prioritization — rights and title are not contingent on GBF compatibility
- Carbon-forward is the one scenario that also states a security target (55% of dense soil carbon); given only the share doubling the others get, it would own 763 km², not 20,329 km² (E18)

## Slide 12 — Scenario clusters — value profiles

figure: `act2_star_grid.png`

- Each scenario's two largest clusters outside the core
- Same radial scale as Act 1

## Slide 13 — How hard must a value lead before it owns land? (E18)

figure: `td_e18_dose.png`

- Pre-registered test: raise one value's emphasis and ask whether its tier is its own land or the refugia core under another name
- Connectivity: at 2× the elicited emphasis it begins to own land (7,925 km²); at 5× it owns 31,780 km² — weight-limited, so its Act-2 statement holds at the elicited emphasis
- Species richness: owns nothing at any emphasis — at 5× the tier is empty (max F 0.63); leaning harder only dissolves the refugia core
- Carbon-forward is the one scenario that also states a security target (55% of dense soil carbon); given only the share doubling the others get, it would own 763 km², not 20,329 km² (E18) — the target, not the weight, is what buys carbon its own places
- Reading rule for Act 2: each scenario's tier is stated at the elicited emphasis (influence share 0.50)

> Dose table from 22 (spec/E18_dose_table.csv; results_log R10.13/R10.14, methods_log M4.21/M4.22). 'Lead vs refugia' = per-cell shortfall cost of the led block's 10,000 densest unprotected cells relative to refugia's under the same weights/targets; it is charged only while the value sits below its target, which is why the weights-only carbon arm scores high yet owns almost nothing.

## Slide 14 — Act 3 — The opportunity landscape

figure: `act3_opportunity.png`

- 100% of unprotected land appears in ≥1 near-optimal plan
- 109/132 pairs of value positions are mutually near-optimal
- The analysis does not forbid working anywhere relationships and feasibility are positive — it tells you what can be promised about each tier
- PRIORITY ≠ PERMISSION

## Slide 15 — What each tier delivers

figure: `tier_achievement.png`

- Value captured per theme by cumulative tier (PAs → + core → + scenario tiers → + opportunity)
- Red line/band = what a single optimal plan captures (balanced; range across all positions)
- Pairs with T-D2: the promise per tier, in the currency of each value

## Slide 16 — Why these places (driver attribution)

figure: `why_these_places.png`

- High frequency follows binding scarcity, not the most-valued layer
- Dense climate refugia pin the core under every value position; dense soil carbon under carbon-forward values

## Slide 17 — E17 — an un-chosen 2° southern lean

figure: `e17_one_pager.png`

- 20/40 EFGs >90% south of 53°N
- Removing representativeness moves the plan +2.1° north
- Decision for Y2Y: affirm the representativeness anchor at its measured price?

## Slide 18 — What we can promise — the map in one picture

figure: `summary_tiers_1km.png`

- Yellow = commit regardless of values
- Coloured = joins the core if that value leads (dark blue = more than one)
- Light blue = defensible wherever feasibility is positive
- Tiers are levels of reliability, not a fence

## Slide 19 — What we can promise

figure: `td2_bands.png`

- Core: recurs under every value position (commit)
- Scenario tiers: join the core if that value leads (choose)
- Opportunity: defensible wherever feasibility is positive (enable)
- Next: cluster naming, hex size, IPCA dataset confirmation

## Appendix
- `act1_core_1km.png` (the same pair at 1 km, no hexes), `act1_F_histogram.png` (distribution of F), `act1_core_1km_tiers.png` (five-tier analytic surface)
- `td1_picks.png` + `tables/T-D1_cluster_register.csv` (full register), `tables/cluster_sensitivity.csv` (0.60/0.80)
- `td2_acts.png`, `td3_scenarios.png`, `td5_protected_baseline.png` (what PAs already bank), `td5b_enrichment_by_scenario.png`, `tables/pooling_check.csv`, 1 km GeoTIFFs in `geotiffs/`
- `act2_scenarios_overview.png` (all scenarios as small multiples), `agreement_matrix.png` (pairwise Jaccard between the 12 optimal plans), `td4_ecoregions.png` + `tables/T-D4_ecoregions.csv` (tier area by ecoregion — needs an ecoregion layer in `input_data/ecoregions/`)
- `td_e18_dose.png` + `spec/E18_dose_table.csv` (E18 dose–response: weight vs substitutability, incl. the carbon weights-only counterfactual; from 22)
- Decided: (c) hex 250 km². Open: (e) cluster names, (f) E17 placement, (h) proposed-IPCA dataset