# Y2Y Director Package — Deliverables Spec (Gate 5, priority track)

**Status:** v1.1 — build spec for Claude Code. Source artifacts: R8/R9 ensemble outputs, E13 masks, E15 floor runs (S0+S4 ONLY — see step 0), E17 tables. Analysis resolution 1 km (native); presentation aggregation defined below. All maps ESRI:102008; CVD-checked ramps; locked PAs as a distinct layer on every map.

**STEP 0 (CORRECTION v1.1 — gating compute, ~8–10 h serial):** guarded MGA sweeps exist only for S0 and S4. Run the per-block-floor sweeps (capture_b ≥ 0.95·anchor_b rows; k=50; g=5%) for the remaining ~12 formulations; recompute guarded f per formulation and guarded ensemble F; run the queued guarded MAA spot-check on S0. Anchors, k-best pools, and LP twins all STAND (floors are anchor-relative; no anchor re-solve). The v1.0 "zero new solves" claim was wrong and is superseded.

## Story architecture (three acts, one guardrail)

- **Act 1 — Core commitments.** The guarded ensemble frequent tier: cells with F ≥ 0.70 under per-block floors, across all 14 formulations. Director sentence: "these areas recur in near-optimal plans no matter whose values prevail, with no value theme left more than 5% behind."
- **Act 2 — Value-specific priorities.** Per-formulation guarded frequent tiers minus the Act-1 core, labeled by scenario (core-habitat / connectivity / biodiversity / carbon-forward; climate levels pooled per scenario unless they diverge — check and report). Director sentence: "if Y2Y leans into value X, these areas join the core."
- **Act 3 — The opportunity landscape.** Union membership (share of formulations' bands in which each cell appears in ≥1 plan; at g=10% essentially all discretionary cells) + E11 (156/182 formulation pairs mutually near-optimal). Director sentence: "the analysis does not forbid working anywhere relationships and feasibility are positive — it tells you what can be promised about each tier." **Guardrail sentence on the slide: priority ≠ permission; tiers are levels of reliability, not a fence.**
- E17 endorsement one-pager rides with the package (below).

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

- **T-D1 Cluster register** (one row per cluster): name; act/tier; driving scenario(s); area km²; mean & min guarded F; block percentiles (6 cols); driver attribution = % of cluster inside m_soc θ-tail / rare-EFG footprint / connectivity spike; mean latitude; % overlapping existing PAs; # formulations in which cluster cells are frequent.
- **T-D2 Tier accounting:** area and % of discretionary landscape per tier (core / scenario-specific by scenario / opportunity / never), under guarded and unguarded semantics side by side (the doubling from E15 is a slide).
- **T-D3 Scenario summary** (from T1): per formulation — one-line value statement, realized captures by block, tail rates, anchor mean latitude.

## E17 endorsement one-pager

- The leave-one-block-out latitude figure (5 bars: Δ mean latitude vs S0 anchor; EFG-out +2.11°N flagged) + the 20/40-EFGs-south-of-53°N stat.
- Both-truths framing verbatim: the ~2° southern anchor was never explicitly endorsed AND it encodes real conservation logic (rare ecosystems are southern because conversion pressure squeezed them there).
- The question, stated for decision: does Y2Y affirm the representativeness anchor at its measured price? Alternative if not: regionally stratified representation targets (applied-paper scope).

## Slide skeleton (suggested, ~10 slides)

1 Title/context → 2 How to read the map (tiers, PAs, hexes) → 3 Act 1 core map → 4 Core star grid + T-D2 doubling slide → 5 Act 2 scenario maps (small multiples) → 6 Scenario star grid → 7 Act 3 opportunity map + guardrail sentence → 8 "Why these places" (driver attribution / E13 in one visual) → 9 E17 endorsement one-pager → 10 What we can promise (tier sentences, next steps).

## Decisions needed from Ethan before final render

(a) Guarded semantics as the single surface for all acts — CONFIRMED v1.1. (b) Threshold 0.70 confirmed (pre-registered band) with 0.60/0.80 sensitivity in appendix. (c) Hex size ~250 km² ok, or coarser (~800 km²) for board-level legibility. (d) Min cluster 100 km². (e) Cluster names. (f) E17 one-pager in the director deck vs held for Graham first. (g) Climate levels pooled per scenario in Act 2 (recommended unless divergence check fails). (h) NEW: authoritative proposed-IPCA dataset for the alignment overlay.

## Build order

0. **Guarded-sweep completion (~8–10 h serial; gates everything)** → 1. Tier surfaces + clustering with sensitivity companion + top-k selection → 2. T-D1/T-D2/T-D3 (incl. IPCA overlap column) → 3. Hex choropleths + cluster overlays → 4. Star grid → 5. Act 3 map → 6. IPCA alignment call-outs → 7. E17 one-pager → 8. Slide assembly.
