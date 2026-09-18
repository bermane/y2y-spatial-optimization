# Y2Y Director Package — Deliverables Spec (Gate 5, priority track)

**Status:** v2.0 — REBUILD ON MANIFEST v4 (study plan v0.20): five value blocks; Act 2 tiers by FIVE owning scenarios (core-habitat, structural-connectivity, climate-corridors, biodiversity, carbon); clusters re-derived and re-named from the v4 core; refugia column native-floored. Everything else in this spec stands. The v3.1 package is archived as the prior registration. Prior: v1.14 — consequence-table statistics fixed (mean ratios; velocity floor on the refugia column; attribution column as the concentration guard). Prior: v1.13 — FROZEN for the group presentation (Ethan, 2026-09-17); built on the registered manifest-v3.1 results; no pending re-solves. Prior: v1.12 — bear-coexistence data integrated as naming (all acts) + presence column in Act 3 consequence tables only; T-D4 ecoregion layer to be supplied by Ethan. All package decisions closed except cluster-map styling (Ethan, figures notebook). Prior: v1.11 — cluster naming decided (Cluster N + coexistence-layer region name); latitudinal-attribution page (E17) left out of the deck. Prior: v1.9 — connectivity-forward caveat updated from E20 (register entry in the study plan v0.18.1). Prior: v1.7 — BLOCKED on the EFG curation re-solve (study plan v0.17, manifest v3). Every tier, cluster, star, and the Act 1 representativeness layer rebuild on the curated block. Interim (Option D) only if the workshop date forces it: strip F2.10/SF2.2/F3.4 (+ curated drops) from the representativeness layer and driver attribution; label the F2.10 register cluster and pick #11 as map artifacts; disclose on the E17 page. Act 1 representativeness = presence of a class RARE IN THE BUFFERED REGIONAL WINDOW (extent + 250 km; study plan v0.17.3) — expected thin, which is the honest representativeness story for Y2Y. Prior: v1.6 — VALUE-FIRST restructure: four acts, Value → Core irreplaceability → Scenario irreplaceability (value reprised per theme) → Opportunity (the measured gap). Ladder/245 twins removed (no further solves). Prior: v1.5 — E18 products added: per-theme value-map/irreplaceability-map pairing in Act 2; connectivity emphasis ladder (pooled over climate once the 245 twins run); biodiversity coverage statement; carbon-forward fairness caveat + mirror. Prior: v1.4 — F denominator = 12 design formulations (crossed diagnostics excluded per study plan v0.15). Prior: v1.1 — build spec for Claude Code. Source artifacts: R8/R9 ensemble outputs, E13 masks, E15 floor runs (S0+S4 ONLY — see step 0), E17 tables. Analysis resolution 1 km (native); presentation aggregation defined below. All maps ESRI:102008; CVD-checked ramps; locked PAs as a distinct layer on every map.

**STEP 0 (v1.4 — gating compute, ~7–8 h serial):** guarded MGA sweeps exist only for S0 and S4. Run the per-block-floor sweeps (capture_b ≥ 0.95·anchor_b rows; k=50; g=5%) for the remaining DESIGN formulations only (10 more; s1x/s3x are diagnostic, non-voting per study plan v0.15 and are SKIPPED); recompute guarded f per formulation and guarded ensemble F; run the queued guarded MAA spot-check on S0. Anchors, k-best pools, and LP twins all STAND (floors are anchor-relative; no anchor re-solve). The v1.0 "zero new solves" claim was wrong and is superseded.

**Naming convention (binding for chat, notebooks, logs, and report-backs):** refer to any test, tier, gate, figure, or decision by WHAT IT IS, with the code in parentheses afterward — e.g. "the leave-EFG-out anchor cross-check (E19 T2)", "the degeneracy pilot (Gate 2b)", "the core-erosion curve (F6)", "the tilt-magnitude call (D1)". Never the bare code alone. Codes are for cross-referencing; the words are what get read.

## Story architecture (v1.6 — VALUE-FIRST; the workshop spine is value vs irreplaceability)

- **Act 1 — Where the values are.** Per-PROACT-theme value maps (block-aggregated layer, top-30% of the discretionary landscape shaded, hex display) plus the **value-convergence map** (count of themes, 0–5, in which each cell is top-30%; representativeness voted as presence of any rare-EFG class). Intactness shown as a sixth value map, labeled "disclosed, not a driver" — the audience sees the wild places here and then sees them absent from every tier. This is the map directors already hold in their heads; showing it first defuses the single-map (Currie/Jung) expectation because the single map IS Act 1.
- **Act 2 — Core irreplaceability.** Guarded ensemble frequent tier (F ≥ 0.70 under per-block floors, 12 design formulations). Director sentence: "of everything in Act 1, these areas recur in near-optimal plans no matter whose values prevail, with no value theme left more than 5% behind."
- **Act 3 — Scenario irreplaceability.** Per-formulation guarded tiers minus the core, by scenario (climate pooled). **Binding pairing rule:** each theme slide shows its Act-1 value map (left) beside its tier (right) — the shrinkage from value to irreplaceability is the visual argument. Biodiversity: the finding is the product (no irreplaceable places at any emphasis; every near-optimal plan holds ~34–36% of AOH richness). Carbon-forward carries the fairness caveat + mirror.
- **Act 4 — The opportunity landscape = the measured gap.** Value minus irreplaceability, backed by evidence that near-optimal plans absorb it: union membership (essentially every discretionary cell is in some near-optimal plan), Δ (156/182→recomputed on 12 design formulations mutually in-band), coverage statements. Director sentence: "the analysis doesn't forbid working anywhere relationships and feasibility are positive — it tells you what can be promised about each tier." Guardrail on the slide: priority ≠ permission.
- **Hinge figure (between Acts 3 and 4): value-convergence count × F tier cross-tab.** High-value/high-F = the easy sell; high-value/low-F = Act 4's territory; low-value/high-F = the E13 surprise (binding claims in unglamorous places) — point at it in the room.
- E17 endorsement one-pager rides with the package (placement per decision (f)).

## Clustering procedure (pre-stated; = E16 sanctioned fallback, now primary)

1. Surface: guarded f (per formulation) and guarded ensemble F. Threshold at the pre-registered frequent band, ≥ 0.70.
2. Morphological closing, radius 1 cell (bridge single-cell speckle only).
3. Connected components, 8-neighbor.
4. Minimum cluster size 100 km²; smaller components listed in an appendix table, not mapped.
5. Scenario-specific clusters: per-formulation clusters minus the Act-1 core footprint (report % overlap before subtraction).
6. Naming: dominant geographic feature (range/watershed/region), confirmed by Ethan before final render.
7. Sensitivity companion (appendix): cluster maps at thresholds 0.60 and 0.80; report count/area stability.
8. Clustering runs at 1 km ALWAYS; never on aggregated hexes (would smear tail-driven clusters — E13: S4 high-f is 80.8% inside a mask covering ~4% of the region).
9. **Presentation selection (v1.1):** clusters are found by the procedure above, unchanged; the DECK shows top-k by area (tie-break: mean guarded F) — k = 5–7 for Act 1; 1–2 per scenario for Act 2. Full cluster register (every component ≥ min size) ships in the appendix. Selection is presentational; the threshold is never tuned to a cluster count.

## Presentation aggregation

- Hex choropleth for director-facing F maps: ~250 km² hexes (H3 res 5 or equivalent in 102008), value = mean guarded F per hex (and per-formulation variants). 1-km GeoTIFFs remain the analytic products and ship in the package appendix.
- Clusters displayed as smoothed labeled polygons over the hex choropleth (simplify tolerance ~2 km; preserve topology; no smoothing into PA polygons without visual distinction).
- Every map: locked-PA layer (distinct fill), graticule with 53°N lightly marked (ties to E17 one-pager), scale bar, n-of-formulations note in the corner.

## Star plots (per cluster)

- Six axes: five PROACT blocks + intactness (intactness visually distinct — dashed/grey — captioned "disclosed, not a driver").
- Block member aggregation: carbon = mass-weighted mean of SOC + biomass percentiles (74.2/25.8); biodiversity = mean of birds + mammals percentiles; connectivity = mean of transboundary + corridors percentiles; core habitat = macrorefugia percentile; representativeness = count of EFG classes present in cluster ÷ 40 (different construction — footnote it).
- Normalization: cluster mean percentile relative to the DISCRETIONARY landscape (0.5 = typical unprotected land). One shared radial scale across all stars.
- Layout: grid of stars grouped Act-1 core first, then scenario-specific by scenario; each star titled with cluster name + area + mean guarded F.
- Expectation to preserve, not hide: core clusters spike on binding claims rather than excelling everywhere (E13). The star grid is the visual proof of "why these places."

## E18 carry-overs (v1.6 — no ladder, no further solves)

- The per-theme value/irreplaceability pairing (now Act 3's binding rule) and the biodiversity coverage statement are adopted. The connectivity emphasis ladder and the SSP245 twins are SET ASIDE; 4×/10× arms remain E18 evidence (dose-table slide retained in the appendix, not the main arc).
- **Carbon-forward caveat + mirror (verbatim):** "carbon-forward is the only scenario that also states a security target (55% of dense soil carbon); given only the share doubling the other values get it would own ~760 km², not ~20,300" — AND — "carbon has a target lever because its geometry admitted a stopping rule; the diffuse values cannot; the asymmetry is the landscape's."
- **Connectivity-forward caveat (v1.9, from the post-freeze sequence E20; replaces any "never owns tier land" wording):** "At the registered shapes and shares, connectivity-forward owns ~8k km²; with pinch points valued convexly and the block un-diluted it can own 13k km² at balanced weights and 32–61k km² when connectivity leads — every hectare bought from the refugia core, with the tier becoming less multi-claim and less diverse as it grows." Any quote of the pinning bracket states the per-layer share and the shape it was measured at ((0.125, 0.20] under I²; 0.33–0.42 at identity).

## Proposed-IPCA alignment overlay (v1.1, Act 2)

- Layer: Nations' own DECLARED IPCA proposals only (authoritative dataset confirmed by Ethan — presumed the northern-corridors polygon set); never analyst-drawn boundaries. Proposed IPCAs are NOT locked in the model — so cluster∩IPCA overlap is **independent convergence**: the values analysis and a Nation's declared initiative arriving at the same ground separately.
- Rendering: call-out styling on Act 2 maps where clusters overlap proposals; per-cluster % overlap with proposed IPCAs added to T-D1.
- Language rule (binding): ALIGNMENT, not assignment. The analysis does not set priorities inside IPCAs; it shows that where declared proposals advance, named value clusters would be protected. One slide carries the convergence sentence; slide 5/6 captions follow the same rule.

## Presentation conventions borrowed from precedent (v1.3)

Closest published analogues: Jung et al. 2021 (ranked hierarchical map + per-asset achievement triangle at 10%/30% + PA variant shown separately; displayed at 10 km); Buenafe et al. 2023 (per-scenario plan maps with % area annotated; selection-frequency map with inset histogram; kappa agreement matrix; feature-protection density across frequency bands); **Currie, Liang & Snider 2025 (CSP 7:e70087 — WWF-Canada, same audience):** prioritizr/Gurobi at 100 km² hexbins; headline = selection frequency summed across a 4-level target sweep (20–50%), Figure 5 as an (a) without / (b) with-PAs panel pair, legend "frequency in optimization solution"; ecozone summary of priorities (S9); species-only vs non-species attribution of the north–south split (S10); IPCA discussion. Adopted:
- **Tier-achievement figure (zero-solve):** capture achieved per PROACT block by cumulative tier — core / core+scenario / opportunity — with anchor-level captures as reference lines. Pairs with T-D2.
- % area annotated on every scenario map; inset histogram of guarded F on the Act 1 map; **Act 1 rendered as the Currie-style (a)/(b) pair — F alone, then F with locked PAs** — so WWF-literate directors recognize the genre, with the "51 × 14 plans vs 4" contrast stated on the how-to-read slide.
- Agreement matrix (pairwise Jaccard between formulation anchors) in the appendix.
- **T-D4 (NEW): tier area by ecozone/ecoregion** — the Currie S9 analogue directors will expect; also carries the E17 story regionally.
- **E17 one-pager precedent line:** the national 30×30 analysis found the same north–south tension (species targets pull south into high-footprint ecozones; non-species targets shape the north — Currie et al. 2025 §4.2.1–4.2.2, Fig. S10); this analysis is the first to decompose each value's pull causally (leave-one-block-out, in degrees of latitude). Lowers the temperature: a known property of Canadian prioritization, here measured.
- **IPCA slide citation:** Currie et al. 2025 state that proposed IPCAs coincide with priority areas and that Indigenous priorities should supersede top-down prioritization, rights and title not contingent on GBF compatibility; and that self-declared IPCAs are not counted in CPCAD — institutional precedent for "alignment, not assignment" and for the not-locked-in convergence framing.
- Scale sentence for directors: our DISPLAY hex (~250 km²) ≈ the national analysis's PLANNING unit (100 km²); our analysis runs at 1 km² — two orders of magnitude finer. "This ecodistrict" vs "this valley," with numbers.
- Hex aggregation for display is precedented (Jung 10 km; Currie 100 km² planning hexes; mangrove follow-up ~100× aggregation).

## Tables

- **T-D1 Cluster register** (one row per cluster): name; act/tier; driving scenario(s); area km²; mean & min guarded F; block percentiles (6 cols); driver attribution = % of cluster inside m_soc θ-tail / rare-EFG footprint / connectivity spike; **% ADEQUACY-FORCED (E19 T1) — clusters ≥50% forced captioned "adequacy pin: only X on the extent" (v1.8)**; mean latitude; % overlapping existing PAs; # formulations in which cluster cells are frequent.
- **T-D2 Tier accounting:** area and % of discretionary landscape per tier (core / scenario-specific by scenario / opportunity / never), under guarded and unguarded semantics side by side (the doubling from E15 is a slide).
- **T-D3 Scenario summary** (from T1): per formulation — one-line value statement, realized captures by block, tail rates, anchor mean latitude.

## E17 endorsement one-pager

- The leave-one-block-out latitude figure (5 bars: Δ mean latitude vs S0 anchor; EFG-out +2.11°N flagged) + the 20/40-EFGs-south-of-53°N stat.
- Both-truths framing verbatim: the ~2° southern anchor was never explicitly endorsed AND it encodes real conservation logic (rare ecosystems are southern because conversion pressure squeezed them there).
- The question, stated for decision: does Y2Y affirm the representativeness anchor at its measured price? Alternative if not: regionally stratified representation targets (applied-paper scope).

## Slide skeleton (v1.6, ~12 slides)

1 Title/context → 2 Act 1: value maps (per theme, small multiples) → 3 Act 1: value-convergence map → 4 Act 2: core map (Currie-style (a)/(b) pair) → 5 Core star grid + T-D2 doubling → 6 Act 3: per-theme pairings (value | tier), one slide per theme incl. carbon caveat → 7 Scenario star grid + IPCA alignment call-outs → 8 Hinge: convergence × F cross-tab → 9 "Why these places" (driver attribution / E13) → 10 Act 4: opportunity map + guardrail + tier-achievement figure → 11 E17 endorsement one-pager → 12 What we can promise (tier sentences, next steps). Appendix: E18 dose table, agreement matrix, sensitivity clusters, full cluster register, T-D4 by ecoregion.

## Decisions needed from Ethan before final render

(a) Guarded semantics as the single surface for all acts — CONFIRMED v1.1. (b) Threshold 0.70 confirmed (pre-registered band) with 0.60/0.80 sensitivity in appendix. (c) Hex size ~250 km² ok, or coarser (~800 km²) for board-level legibility. (d) Min cluster 100 km². (e) Cluster names — DECIDED (Ethan, 2026-09-17): clusters are labeled "Cluster N" (N→S numbering) with the region name in parentheses taken from the bear-coexistence communities layer's `region` column — e.g. "Cluster 2 (Purcell–Columbia, Kootenays)", "Cluster 1 (Sacred Headwaters, Stikine)". Implementation: add a `region` column beside the landmark placeholder in the cluster register (T-D1) and carry it into every pick, table, and map label; the landmark locator stays as a secondary descriptor. Zero analytical risk; the communities layer is baked in as naming only. (f) The latitudinal-attribution one-pager (E17) — DECIDED (Ethan, 2026-09-17): LEFT OUT of the director deck. The finding (ecosystem foundation moved the balanced plan +2.11°N on the artifact block → +0.14°N after curation; the audit caught its own lean) stays in the paper and the appendix record only; slide 11 (v1.6 skeleton) is dropped. (g) Climate levels pooled per scenario in Act 2 (recommended unless divergence check fails). (h) NEW: authoritative proposed-IPCA dataset for the alignment overlay. (i) T-D4 ecoregion layer — Ethan supplies it in `input_data/ecoregions/` (decided 2026-09-17).

## Consequence-table statistics (v1.14, Ethan 2026-09-17)

- **Ratios are MEAN-to-mean:** mean value in the area ÷ mean over allocatable land. Rationale: this is the quantity the optimizer saw (each feature enters as a share of its total), it is per-hectare density relative to average, and it is additive — cluster mean × area = what the cluster captures, which ties the consequences table to the capture numbers everywhere else in the package. Median-to-median is not used: it does not sum to anything the deck reports, and for additive quantities (carbon) a median tonne is not a thing.
- **Real tails stay in the mean.** Soil carbon's ≥5×-mean tail (4% of the region, a third of the stock) is a measurement: a cluster at 3× carbon holds three times the carbon per hectare, and a median would understate what protecting it secures. Skew that is physically true is the signal, not noise.
- **Refugia is the one exception — apply the velocity FLOOR before computing its column.** 1/v's tail top is partly a division artifact (analogs within one grid cell get values the data cannot distinguish but the arithmetic makes enormous). The floor (one cell width over the horizon; study plan Decision 2) removes contrast the measurement does not contain. Applied to the TABLE even though the frozen solve did not carry it; footnoted.
- **Reading guard, not a statistic change:** a high carbon ratio can mean uniformly carbon-rich or ordinary-with-a-hotspot. The cluster register's driver-attribution column (% of cluster inside the carbon θ-tail) is the concentration reading and is presented beside the ratio.
- **One-time check (not shown):** compute mean- and median-ratios for every cluster × value cell; flag pairs disagreeing by >1.5×. Expected flags: carbon (concentrated and real — keep) and refugia (removed by the floor — confirm). Any other flag is a tail worth knowing about before presenting.
- Naturalness stays a ratio (compressed against its ceiling; neither statistic discriminates), as ruled at v1.8.

## Bear-coexistence data integration (v1.12, Ethan 2026-09-17)

Two uses, both non-analytical (no number in the optimization or the tiers depends on the layer):
1. **Naming (decision e):** the `region` column labels every cluster — "Cluster N (Region, Sub-region)" — in every pick, table, and map.
2. **Consequence tables — Act 3 (the opportunity landscape) ONLY.** Existing coexistence capacity is a feasibility signal ("high-value land with existing capacity"); it does not belong in Act 1, where it muddles the value story. Column design, so it cannot be read as a score: the polygon support spans seven orders of magnitude, four units in the Yellowstone corner carry copied counts, and NA is under-representation, not zero. Therefore: column = **"coexistence groups recorded in overlapping units"**, rendered as PRESENCE with the corrected count in parentheses; suspect units flagged; NA rendered as "none recorded" (never 0). No ranking, no rate, no per-area normalization. A distance-to-capacity statistic waits for town points and is not built yet.
3. **Maps:** deferred — Ethan resolves in the directors' figures notebook. Standing guidance if useful: presence hatching on units with labelled counts, not a count choropleth (a choropleth lets the Yukon unit dominate the frame and erases the sub-100 km² units).

## Build order

0. **Guarded-sweep completion (~8–10 h serial; gates everything)** → 1. Tier surfaces + clustering with sensitivity companion + top-k selection → 2. T-D1/T-D2/T-D3 (incl. IPCA overlap column) → 3. Hex choropleths + cluster overlays → 4. Star grid → 5. Act 3 map → 6. IPCA alignment call-outs → 7. E17 one-pager → 8. Slide assembly.
