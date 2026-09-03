# Methods log — northern connectivity corridors (living document)

**Purpose.** The cumulative record of every methods-relevant decision, data manipulation, and
fix in this analysis, in enough detail to write the paper's methods section without archaeology.
Each entry carries: what was done, exact parameters, the justification, and where it is
implemented.

**Maintenance rule (binding on every working session):** any change that alters the data, the
formulation, a parameter, or a QA rule gets an entry HERE in the same session it is made —
including reversals. Supersessions are marked, never deleted: the paper may need to say "we
initially X, then Y because Z."

Companion documents: **`results_log.md`** (the corresponding RESULTS register — same maintenance
rule; quantitative outcomes live there, methods decisions here);
`05_corridors_v2_addendum_run_and_alternatives.md` (the approved spec, D11–D16);
`docs/05_methods_v2.md` (the v2 rebuild, D1–D10 + amendments A1–A4);
`docs/context_05_corridors_for_lit_review.md` (v1 critique).

---

## 1. Claim scope and study system

- **M1.1 Claim scope (pre-registered):** structural-connectivity hypotheses only — a robust core
  vs a flexible periphery, and which links have no viable alternative. NOT species-movement
  predictions; nothing validated against movement, genetic, or occurrence data. Two distinct
  reasons, both stated in drafts: the resistance values are expert-assigned hypotheses (never
  fit to movement data), and the surface is species-agnostic. "Corridor" is reserved for
  bands/branches from this engine.
- **M1.2 Study system:** northern BC + Yukon PA/IPCA network, 42 named areas (10 proposed IPCAs
  ≥ 25 km² with centroid ≥ 55°N, 32 existing PAs ≥ 200 km²), routed over a 300 m grid
  (ESRI:102008) cropped to the anchors + 100 km buffer: 2,809 × 5,767 cells, 9,696,945 routable
  (872,725 km²). Routes cannot leave the buffered Y2Y region (cutline = real modelling
  constraint, stated).
- **M1.3 Two grids (correctness requirement):** routing at 300 m (linear barriers are the
  signal); the co-benefit audit at 1 km (every value layer is natively 1 km; profiling a 300 m
  mask would inflate "% of Y2Y" ~11×). Masks cross via areal-fraction ≥ 0.5
  (`corridors_core._to_audit`); `audit_area_check` reports the crossing discrepancy.
- **M1.4 Reporting rule — state the near-Euclidean mechanism (2026-08-30).** With 88% of the
  window at cost-1, least-cost routes through intact country are near-straight lines and slack
  ≈ distance off the direct line; the corridor ribbons are, to first order, "the direct links,
  bent around barriers." State this plainly (same doctrine as the leverage/Morris mechanism
  statement in the prioritizr work): the paper's claims rest on the products this does NOT
  reduce to — the irreplaceability ratios (what the landscape offers when the best route is
  taken away: barrier geometry × anchor constellation), the network-topology results (16/42
  articulation names, load-bearing anchors — properties of the PA/IPCA system, not the
  surface), and the priced exceptions where directness fails. Framing: the northern landscape
  is permeable enough that connectivity is a SECURING problem, not a routing problem — the
  contribution is locating and pricing where that forgiveness runs out.

## 2. Resistance surface

- **M2.1** Resistance = the published **O'Brien et al. transboundary movement-cost surface**
  (extension of Pither et al. 2023), used as published: four log-spaced ordinal classes
  {1, 10, 100, 1000}, native 300 m, EPSG:3347 → ESRI:102008 by `-r near` (class-preserving;
  asserted by gate G2). No blend, no exponents, no floors (D1/D2; v1's blend triple-counted
  footprint and used a circuit-theory output as a routing input).
- **M2.2** Class semantics for interpretation: cost-10 = the linear-infrastructure class
  (roads/rail; verified linear at 300 m, features to 395 km); crossing 1–2 cells of cost-10
  ≈ 3–6 km of equivalent detour, so routes cross roads rather than avoid them; one cost-1000
  cell ≈ 300 km equivalent — an effective wall. **Open item (H1):** in the northern window
  cost-1000 covers 6.1% — almost certainly dominated by water/ice, not settlement; confirm the
  class definition at licence/provenance sign-off before publication.
- **M2.3** Off-corridor cells are impassable (inf).

## 3. Node assembly and D16 multipart handling

- **M3.1** Names rasterized on the routing grid; dedupe merges two names when rasterized masks
  overlap ≥ 50% of the smaller (same-place-two-designations; wrapping neighbours stay separate).
  Measured: 3 merges (Peel Watershed SMA/WA + Teetł'it Gwinjik; Fishing Branch HPA + Wilderness
  Preserve; Neah Conservancy + Ne'ah–Horseranch/Deadwood). 2 IPCAs dropped < 25 km² in-region
  (Wëdzey Nähuzhi, Łuk Tthe K'ät).
- **M3.2 (D16)** A name whose mask has > 1 8-connected component ≥ `part_min_km2` = 25 km² is
  split into parts; each seed part gets its own CWD field. Treatments per multipart name from
  the **H7 human-signed** `multipart_review.csv` (canonical, git-tracked in
  `audit/audit_objects/`; sha256-pinned into each run's `run_config.json`): `merge_parts` /
  `link_locked` (intra-name MST locked into the backbone) / `link_competing` (parts independent,
  direct edge competes) / `no_link` (parts independent AND the direct intra-name edge excluded
  from candidacy). Non-seed slivers stay in `node_union` (area accounting) but never seed.
- **M3.3** Step-0a decision rules (proposal only; the human review is the decision): (1) gap
  < 3 cells → merge_parts (rasterization split); (2) multi-site-by-design designation →
  no_link unless parts ≤ 10 km apart with nothing intervening; (3) intervening node →
  link_competing; (4) default link_locked (a named area is a management unit). Evidence columns
  incl. per-pair CWD, `path_max_cost`, `path_cells_cost10plus` (added 2026-08-27 so road
  crossings are measured on the actual least-cost path, not inferred from cost arithmetic).
- **M3.4 Disclosure:** the PA layer carries no designation attribute (only `PA_Name`), so
  existing-PA designations in the review evidence are name-derived; the IPCA layer's `PA_TYPE`
  is genuine. Moot for the realized node set (no multipart WMAs/sanctuaries occurred; rule 2
  never fired).
- **M3.5** Multi-seed semantics: a multi-part unit's CWD field = pointwise min over its seed
  parts' fields (= multi-seed CWD from the part union); inter-name distance = min over part
  pairs. Leave-one-out drops a NAME (all parts, incl. no_link parts — independent in the graph
  but sharing the name's realisation risk).

## 4. Network formulation

- **M4.1 (D6)** Corridor band = absolute CWD cutoff: keep cells with (CWD_i + CWD_j) within
  `cwd_cutoff_abs` cost units of the edge's least-cost minimum. The cutoff is CALIBRATED
  (bisection, pre-registered target = v1's 18,188 km² on inter-name-MST-only edges, `&
  ~node_union`, tol 50 km²) so v1↔v2 comparisons are not confounded by band size; augmentation
  and locked-edge area are reported separately.
- **M4.2 (D7)** Network = inter-name MST + sequential bridge-backup augmentation in descending
  criticality with recomputation, under cost-ratio ceiling **β = 2.5**; links with no candidate
  ≤ β × failed cost are flagged **edge-irreplaceable** (headline output). Spanner stretch is a
  diagnostic only.
- **M4.3 Adjacency edges** (zero-cost; touching names): kept in the graph, excluded from failure
  enumeration and backup candidacy; centrality on the quotient graph (zero-cost cliques
  contracted); **contribute no corridor land**. **FIX 2026-08-27:** under the absolute cutoff,
  `edge_bands` originally grew a `cutoff`-deep lens around every adjacency contact zone
  (10,644 km² on the first calibrated pass) that was silently absorbed into the D6 calibration,
  narrowing every separated edge's band — contradicting the documented design (v1's relative
  band made this impossible: allow = frac × 0 = 0). Abs-mode adjacency edges now get empty
  bands; calibration re-run (13.38 → 13.62). The first pass is SUPERSEDED.
- **M4.4 (D16) Locked intra-name edges:** appended to the backbone with `edge_class =
  "intra_name"`; banded on part fields; included in criticality via an extended part-level
  graph (built unit edges attached to their argmin part pairs); a cheapest reconnecting
  part-pair edge is priced against the same β for the irreplaceable flag but never added
  (augmentation policy for internal links is the review's call). **OPEN METHODS QUESTION
  (flagged, default in place):** locked edges carry `ecfb_raw = NaN` (current-flow centrality
  is undefined inside a quotient supernode, as for adjacencies), so their land appears in
  `corridors.tif` and the near-optimality surface but contributes nothing to
  `linkage_priority.tif`.
- **M4.6 Squeeze index (2026-08-30, screening diagnostic).** Per link: mean band width
  (band_km2 / centreline_km) divided by the OPEN-GROUND expectation — on uniform cost-1 the
  band is a distance-ellipse with midpoint half-width sqrt(dL/2 + d²/4), d = cutoff/3.33 km;
  mean width = (π/4) × midpoint width. squeeze_idx ≈ 1 ⇒ geometry alone confines the corridor
  (securing regime); ≪ 1 ⇒ the landscape has removed the alternatives (routing regime).
  cost_per_km (3.33 = pure intact) flags barrier crossings en route. NaN for routes < 2 km
  (near-touching pairs; ratios undefined). A SCREENING INDEX, not an estimand: the ellipse
  normalisation assumes a straight link on uniform cost, AND width loss conflates two causes —
  costly flanks (the signal) and clipping by the study-window cutline / NoData (an artefact for
  links hugging the Y2Y boundary, e.g. the SE-corner Gwillim/Monkman/Kakwa group, whose squeeze
  values are therefore somewhat overstated). Disambiguate with cost_per_km: > 3.33 means even
  the optimal route pays crossings — the Peace cluster fires both signals, so its routing-regime
  reading stands on more than width alone (2026-08-31). Serves M1.4's reporting rule —
  `routing_problem_map` paints corridor land by regime (both-senses irreplaceable /
  edge-irreplaceable / squeezed < 0.5 / securing).
- **M4.5 Irreplaceable-flag semantics (for the paper):** the flag records "no affordable DIRECT
  backup existed when the bridge was processed" — affordable = within β; an alternative always
  exists at SOME price, and `backup_ratio` is that price. Later backups can close cycles that
  cover a flagged edge incidentally — its criticality row then shows `disconnects = False` with
  a finite (large) `cost_inflation`. Always read the flag together with those columns, AND
  (2026-08-30) with `backup_extra_km_equiv` = the ABSOLUTE price of the alternative in
  intact-land-km: the ratio alone misleads for near-touching pairs (direct cost ~1 makes any
  go-around look enormous — Edziza↔Stikine is 141× but only ~+42 km absolute; Gwillim↔Pine Le
  Moray is 2.6× but ~+116 km; the Liard internal link 4.6× but ~+6 km). Report ratio and
  absolute together, always.

## 5. Products

- **M5.1 (D9)** `linkage_priority.tif` = max over edges of (ecfb_raw × (1 − slack/cutoff)); max
  not sum (overlap must not be inflated by redundancy); per-cell owning edge in
  `edge_owner.tif`; tier breaks pre-registered as percentiles of the non-zero surface
  (robust_core p90 / frequent p70).
- **M5.2 (D11)** `near_optimality.tif` = min over baseline edges of slack, RAW cost units, every
  routable cell; independent of the calibrated cutoff by construction. Tiers = percentiles of
  slack over the union band at 2× cutoff (robust_core ≤ p10, frequent ≤ p30; cells outside the
  domain fall to occasional). Never labelled "frequency". Adjacency edges contribute nothing.
- **M5.3 (D12)** Route branch = 8-connected component of an edge's band at `branch_mult = 0.5`
  × cutoff, formed BEFORE node subtraction (G9 asserts each touches both endpoints), then node
  land removed, slivers < `branch_min_km2` = 10 km² dropped (count reported). `n_branches == 1`
  ⇒ **route-irreplaceable** — a second, distinct sense from M4.2's edge-irreplaceable; always
  reported together, never merged. Locked intra-name edges get branches too.
- **M5.4 (D13)** Per-branch values table imports the Y2Y-wide alternatives column spec
  (`results_core.RAW_SPEC` / `mask_profile`) — names, units, normalisations never redefined.
  Row unit = edge × route branch (caption ships in `alternatives_branches.meta.json`).
- **M5.5 (D14)** Carroll 2018 current-flow centrality NEVER enters resistance (same object type
  as Pither current density — rejected by D1–D3). Audit column only: `carroll2018_pctl` =
  branch mean percentile vs the routable-area percentile baseline (`carroll_ref =
  "routable_area"`); caveats travel with the column (RCP 8.5 late-century; shares anthropogenic
  signal with the cost surface). H6-guarded. Tie-break report ranks branches; no automated
  recommendation.
- **M5.6 (D8/D15)** Structured ensemble: axis B cutoff × {0.5, 1, 2}; axis C leave-one-out by
  name (42); axis D β ∈ {1.5, 2.5, 4.0}; duplicates removed by config-hash (G12: 47 distinct).
  One cached CWD set serves all members. Member fraction written as
  `ensemble_attribution.tif` (+ per-axis) and used for the robust-core threshold (0.9) and
  attribution ONLY — with ~42/47 members leave-one-out it is "share of dropped names that
  didn't matter," not a sampling frequency.

- **M5.7 FIX 2026-08-27 (ensemble edge identity):** leave-one-out members build their graph on
  a subset of units, and `cg.build`'s edge ids used SUBSET-LOCAL indices — every C member
  shifted the ids of all units above the dropped one, so the first `edge_frequency.csv` was
  index noise. `_member` now translates i/j back to original unit indices before banding/
  writing; the 47 existing members' `edges.csv` were repaired mechanically from their (always
  correct) labels and `edge_frequency.csv` regenerated. First-collect edge frequencies are
  SUPERSEDED and not citable; member corridors/attribution rasters were never affected.

- **M5.9 Priority-link star profiles (2026-08-31, for the PROACT consequences input):** the
  nine numbered routing-regime links profiled through the SAME co-benefit machinery as the
  corridor segments (`mask_profile` richness/contribution/efficiency, 1 km audit grid,
  0.5-majority crossing — the G5-anchored path, so the stars are directly comparable with the
  existing corridor/IPCA/PA stars; NOT the fractional crossing, which is branch-table-specific
  M6.5). Link land = the cells each link OWNS on the priority surface (`edge_owner` partition —
  unique attribution, no double counting between overlapping bands). IPCA/PA reference rows
  appended. Link 1 (Edziza↔Stikine) is a 12 km² contact zone — profile flagged indicative.
  Outputs: `priority_links_profile.csv` + `priority_links_stars_{richness,contribution,
  efficiency}.png` + `priority_links_map.png` (the framing-1 companion map: each link's owned
  land in its star colour, numbered — map/stars/CSV cross-reference by number AND colour;
  PROACT uses FRAMING 1, links-as-alternatives; branch values/tiebreak stay the nested
  route-level drill-down) (05_results). **2026-08-31: RAW native-unit columns added to
  BOTH tables** (`priority_links_profile.csv` and `alternatives_branches.csv`) —
  completing the Y2Y-wide three-table spec (contribution/efficiency/raw, units from
  RAW_SPEC); in passing, RAW_SPEC's stale macrorefugia unit label (still describing
  vmax − v) corrected to the 1/v orientation (also logged y2y M2.10).
- **M5.10 Background reference layers (2026-09-01, DISPLAY-ONLY):** the zoom figures
  (routing_problem_zoom / _cost_zoom / _cost_overlay, priority_links_map) carry
  provincial borders (Natural Earth 10m admin-1 lines, public domain, in
  `input_data/basemap/` with README) and a curated town list (hand-entered WGS84
  coordinates in `corridors_core._TOWNS` — chosen over NE populated-places, which is
  unreliable for small northern-BC towns). Enters NO computation; skips gracefully if
  the shapefile is absent.
- **M5.8 Results notebook (2026-08-27, presentation only):** `05_results.ipynb` +
  `cc.load_results` render the addendum-product figures and the joined
  `irreplaceability_summary.csv` read-only from a run dir — no engine state, no new estimands;
  figures write into the run dir's `figures/` so provenance stays with the run.

## 6. Audit / profiling methods

- **M6.1** Co-benefit profile: richness (0–1, 5–95 pctile stretch), contribution (% of full-Y2Y
  total), efficiency (contribution per 1,000 km²) via `results_core.mask_profile` on the 1 km
  audit grid; full-Y2Y denominators.
- **M6.2 FIX 2026-08-27 (richness stretch domain):** `_profile_stacks` stretched richness over
  the FULL Y2Y audit grid while v1 (and the stated convention, "relative to the north")
  stretched over the routing window. Caught by gate G5 on its first real execution: every
  contribution reproduced v1 to 0.01 while gradient-bearing richness axes shifted (macrorefugia
  −0.33, climate corridors +0.25, AOH −0.11..−0.22). The stretch is now computed over the
  routing window crossed to the audit grid. SUPERSEDED numbers from the first pass are not
  citable.
- **M6.3 G5 scope:** the invariance assert covers only axes whose FEATURE DEFINITION is
  unchanged since v1 froze (2026-08-07). `climate_type_macrorefugia` is excluded and reported:
  the 2026-08-17 leverage redesign re-oriented it vmax−v → 1/v, so that axis compares two
  different features (measured Δ −0.275 IPCAs / −0.260 PAs — the right-skewed 1/v sits low
  after the 5–95 stretch). Expected consequence of a documented change, not a regression.
- **M6.5 Branch crossing = FRACTIONAL COVER WEIGHTING (decided with Ethan 2026-08-27,
  resolving the G11 failure).** Route branches at 0.5× cutoff are ribbons ~1 km wide — all
  boundary — and the fixed 0.5 areal-fraction majority systematically inflated 9 of 41 by
  +5.4–16.6% on the 1 km audit grid (all positive; the known non-conserving regime of the
  majority rule). For BRANCH profiling only, each 1 km cell is now weighted by its actual 300 m
  coverage fraction (`_to_audit_frac` + `_profile_frac`): exactly area-conserving by
  construction. D13 compatibility: the weighted formulas REDUCE EXACTLY to
  `results_core.mask_profile` on binary weights (verified to float32 precision by an
  equivalence test), and the Y2Y-wide tables' masks are native 1 km cells — never fractional —
  so the two products remain computed identically wherever both exist; same estimands, same
  full-Y2Y denominators. The corridor-LEVEL profile keeps the fixed 0.5 majority (masks tens of
  km wide; G5 anchors that path to v1). Carroll percentile becomes a weighted mean percentile
  over the routable-area transform. Alternatives considered: per-branch area-matching threshold
  (kept boolean but adds a fitted dial); flag-not-fail (ships numbers that disagree with the
  map — rejected).
- **M6.4 Disclosure (inherited):** the whole prioritizr PU mask is set by
  `irrecoverable_carbon_biomass`'s footprint; 05 routing uses the cost surface's own footprint
  (872,725 vs v1's 751,614 km²), so v1's routable area was a strict subset. The audit layers
  are PU-masked, so liberated cells read NaN and do not move profile numbers (verified: node
  masks +8% area, contributions unchanged).

## 7. QA gates (definitions; measured values in results_log R1)

G0 name identity re-baselined by D16 (names + merges + part count + review hash) · G1 engine
equivalence on v1's own resistance (THE refactor gate) · G2 warp fidelity · G3 raster/graph
component agreement · G4 β=0 ⇒ locked + inter-name MST · G5 audit invariance on
definition-unchanged axes · G7 drop-nothing ensemble member reproduces baseline · G8 `resolve()`
raises on retired v1 keys AND missing addendum keys · G9 every branch component touches both
endpoints (hard assert) · G10 near-optimality exactly 0 on baseline least-cost paths; tiers
monotone · G11 branch audit-crossing discrepancy ≤ 5% for branches ≥ 50 km² · G12 ensemble = 47
distinct members by config-hash.

## 8. Provenance conventions

One run = one dir (`output_data/corridors_north/v2_runNNN/`) with `run_config.json` (resolved
params, git SHA + dirty flag, input sha256s, H7-artifact hashes) as the engine's only input
after creation; the calibrated cutoff is written back into it (`set_cutoff`). H7 artifacts are
git-tracked in `audit/audit_objects/` and copied+pinned per run. `output_data/` is gitignored —
the run dir + these logs are what survives.
