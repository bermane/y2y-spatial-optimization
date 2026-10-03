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
- **M4.7 D17 — the squeezed class, CONFIRMED definition (2026-09-03, H8 closed; supersedes
  M4.6 as the class definition).** `squeeze_ratio_obs` = real band NEW-land area ÷ the same
  edge's band on a COUNTERFACTUAL surface with every cost class ≥ 10 set to 1, both at
  `cwd_cutoff_abs`; `squeezed` = ratio < 0.5. Chosen (Ethan) over the analytic ellipse index
  because it needs no straight-link assumption, both bands share the cutline clipping (the
  M4.6 SE-corner caveat cancels), and it produces a drawable natural width. One extra CWD set
  per seed part (cached `_cf`). Gate G13: counterfactual band ≥ real band (2% tolerance).
  `squeeze_idx` (M4.6) retained as a screening diagnostic column only; `_routing_classes`
  prefers the D17 column and prints 'H8 OPEN' while it is absent. Implemented
  `corridors_core.counterfactual_squeeze`, notebook 04 step 2b; synthetic-verified.
  **AMENDED 2026-09-08 after the first real execution:** the ratio is WIDTH (band NEW-land
  area ÷ own least-cost route length), not raw area. G13's area inequality fired on 6 links
  (E003_026, E003_036, E007_008, E009_038, E023_028, L002_003): relaxing barriers SHORTENS
  routes that detoured around water/ice, and area ∝ length × width, so a straighter
  counterfactual can be smaller in area while wider per km. G13 restated to assert the
  mechanism — a narrower-per-km counterfactual is admissible only with a shorter
  counterfactual route; such links are reported, never classed squeezed. Counterfactual CWD
  set cached (`8487b2284c1a19a3_cf`). **Second amendment, same day:** the shorter-route
  mechanism assertion also fired (E009_015, E023_028, L032_033: narrower counterfactual,
  route not shorter). Cause: barriers on the real surface EQUALISE two routes into a
  near-tie — a braided, wide band (Liard↔Nahanni's two branches) — and relaxation breaks
  the tie, collapsing the band to one ribbon. So the counterfactual band bounds the real
  band in neither direction; it is a comparator. G13 is now the one true relaxation
  invariant, on the optimum: `lcp_cf ≤ lcp_real` for every banded edge (hard assert);
  narrower-counterfactual links are reported (widths + lengths), never classed squeezed.
  MEASURED 2026-09-08: G13 holds on all 58 banded edges; 8 squeezed (the 5 analytic-index
  links in the same order + Gwillim↔Pine Le Moray [already red] + Wilps Gwininitxw↔Mount
  Blanchet + Wilps Gwininitxw↔Sustut); 6 narrower-counterfactual links reported, Liard↔Nahanni
  the textbook braided case (results_log R9.1). H8 CLOSED on measured data.
- **M4.9 Short-link rules (D24 width-test resolution floor, D25 near-contiguous class; 2026-09-28; applied from
  `spec/05_patch_D24_D25_short_links.md`):** in `counterfactual_squeeze`, per non-zero-cost link, `open_ground_width_med` =
  the counterfactual band's median cross-section (cells, from the D28 profiles), `lcp_len_cells`, `path_max_cost` and
  `crosses_cost_1000` (a cost-1000 cell on the least-cost path); `near_contiguous` = path shorter than the barrier-free
  width (D25; no constant); `width_not_assessable` = width < `width_floor_cells` (8) or length < `len_floor_cells` (10)
  (D24; both pinned into run_config BEFORE any class count is read — tuning prohibition; a derived analysis may raise,
  never lower). The 2 km length floor that used to blank short links' widths is gone (D24 governs; G18 needs the ratio on
  every non-zero-cost edge). `route_branches` skips near-contiguous links (no decomposition; `n_branches` NaN) and
  therefore requires the counterfactual first — notebook 04 runs step 2b before 4b (the wolverine notebooks must do the
  same). `classify_links` (the single source, called at the end of `route_branches` and by `finish`) applies the eleven-row
  precedence → `link_class` / `link_class_label`; **G19** (in it): p10/50/90 of `lcp_len_cells` and `open_ground_width_med`,
  the unassessable and near-contiguous counts, the halved / doubled floors' effect on the class counts (`floor_effect.csv`,
  > 10% moved → "discussed, not changed"), and the three asserts. Presentation: `corridors_mapstyle.NEAR_CONTIGUOUS`
  (grey #D9D9D9, hatch, the barrier variant outlined), drawn UNDER the four corridor classes on M1 (`_paint_near_contiguous`)
  and the 07 maps (`_near_contiguous_wide`); legend rows after the four. Approximate run002 read (area/length width): ~11 of
  45 links near-contiguous (T’akú Tlatsini ↔ Mount Edziza / Stikine, Dene ↔ Liard River Corridor, Tatonduk ↔ Fishing Branch,
  Wędzih Yiné' ↔ Chase, …), 0 below the width floor, 8 below the length floor (R10, to be measured properly on run003).
- **M5.35 Locators without the A / B titles (2026-10-03, Ethan; presentation):** 07 · 04b's panels drop the tag letter, as the y2y cluster
  locators (`cluster_locators` passes an empty title). The panel files keep their `_A` / `_B` suffixes. Wolverine 06 · 05b the same.
- **M5.34 Candara everywhere (Ethan 2026-10-02, presentation):** `corridors_mapstyle.FONT_FAMILY` = ["Candara", "DejaVu Sans"] (was Noto Sans), so the §3a record figures draw in the same typeface as the curated outputs, which already took it through `director_plot.SPEC_RC` (y2y M4.40 addendum); Candara's Bold face serves the 600-weight roles; Noto stays registered for the earlier record. The §3a contract's typeface line is superseded. Nothing measured changes.
- **M5.33 Star titles "Option N" + area (2026-10-02, Ethan; presentation):** the 07 · 04 star titles drop the link name ("Option 1 / 3,682 km²");
  the area line stays as on the y2y cluster stars (`WIDE_STYLE["option_star_area"]` = False removes it). Wolverine 06 · 05 the same.
  **M5.31 addendum (2026-10-02, later; "the .png outputs are cropped wrong"):** the full-page export had left the block low on the canvas — a blank
  band above the insets, the cost key's caption off the bottom. The shared asset now centres the drawn block vertically before saving
  (`director_plot._fit_page`, y2y M4.40 addendum); 07's maps inherit it. Re-render 07.
- **M5.32 Wording (Ethan 2026-10-02, presentation):** every legend, caption, table header and key that said "Proposed IPCAs" (or "Proposed IPCAs / PAs") now says "Proposed conservation areas" — `corridors_mapstyle.AREA['ipca']`, the wide-layout labels, the option / consequences tables, the W11 status words, `config.CORRIDORS` anchor label; the y2y package made the same change in `director_plot` the same day. Named reference columns (Dene Kʼéh Kusān) and every data key are unchanged; nothing measured changes.
- **M5.31 Full-page map export + plain option headers (2026-10-02, Ethan; presentation):** the 07 wide maps export the whole 13.33 × 7.5 in
  slide (`director_plot.STYLE["wide_export_page"] = "full"`, shared with y2y; the 09-30 trimmed box had read as cropped); the 05
  consequences table's column headers read "Option N" alone — the link name under each is dropped (stars keep it).
- **M5.30 Route-option consequences table = the y2y package-spec v2.2 rule (2026-10-01, Ethan: "match the new updates to the y2y-wide
  consequence table"; presentation / register):** `option_profiles_y2y` now computes the representativeness row as the MEAN REPRESENTATION
  QUOTIENT over the 20 curated ecosystem groups (y2y M4.42; `director_core.ValueRatios`, cover-weighted — `quotients` / `standout` /
  `flat_count_ratio` gained `weights=`): option bands and the IPCA reference (Dene Kʼéh Kusān) on their UNPROTECTED cells with the allocatable
  basis, the locked reference (Nahanni National Park Reserve) on on-extent footprints + total land (`rep_basis` = extent, ‡ in the table);
  the other rows stay on the whole footprint. New rows: "Standout ecosystem group (N×)" and "Bear coexistence programs*" (one entry per
  overlapped census division / county with a record, "N (P%)", cover-weighted shares, divisions under 1% dropped; `director_core.bear_programs`
  = the y2y 19 semantics as a shared helper); the register (`tables/route_option_consequences.csv`) gains `pct_protected`, `rep_basis`,
  `ratio_representativeness_flatcount` (the v2.1 statistic), `standout_group` / `standout_quotient`, `rq_alloc_*` / `rq_extent_*` (40
  columns) and the seven bear columns. Measured on run003 (zero render): representativeness options 0.27 / 0.50 / 0.46 / 1.06×
  (flat count 0.89 / 1.24 / 0.91 / 1.19×), Nahanni 0.62× on extent, Dene 0.52×; standouts = temperate alpine grasslands (1), caves +
  underground streams (2), groundwater ecosystems (3, 4). Star axes unchanged (percentile of the flat count).
  **M5.30 addendum (2026-10-01, later): the y2y deck tables stepped back the same day** (y2y M4.42 addendum: bear row = the cell-weighted MEAN
  count, `STYLE["conseq_bear_mode"] = "mean"`; standout-group row OFF, `conseq_standout_row = False`; the representativeness quotient KEPT).
  The route-option table follows without a code change: `option_profiles_y2y` writes every v2.2 column (mean, per-division list, standout)
  and the shared `director_plot.consequences_table` chooses what to show by the y2y STYLE defaults, which `WIDE_STYLE` does not override.
  Rendered rows = area, the seven ratios (representativeness as the quotient, Nahanni ‡), bear mean count*. Register unchanged.
  The y2y bear note ("Mean number of bear coexistence programs recorded for the census division or county each cluster cell falls in
  (divisions with none recorded excluded). Not used in the model.") is shared; its noun is now the asset's `unit_word` argument, "option"
  from both corridor tables (y2y default "cluster"). Same wording otherwise. Later the same day the y2y asset moved the bear row BEFORE
  Carbon (the objectives hierarchy's order), right-set and on the row ramp with "none recorded" cells unfilled (`conseq_bear_fill`) —
  inherited unchanged; on run003 only option 3 carries a record (1.0), so that row renders neutral with three "none recorded" cells.
  **Headers as before (Ethan 2026-10-01):** the row header stays "Representativeness" without the y2y † mark (`WIDE_STYLE["conseq_rep_mark"]`
  = ""; the shared asset then labels the definition note "Note"); the ‡ on the locked reference's cell and its sentence stay; column
  headers, spanners and title were never changed.
- **M5.29 Thinner route-option outlines (2026-10-01, Ethan; presentation):** on 07 · 03 and the 04b locators the option rings draw at
  `WIDE_STYLE["option_lw"]` = 0.8 pt on the frame with a halo `option_halo` = 0.8 pt wider (were cluster_lw × 1.6 = 1.44 pt and +1.4 pt);
  the inset scale still multiplies on insets and locators. Nothing measured changes.
- **M5.28 PNG only (2026-10-01, Ethan; presentation):** every map and figure exports as PNG at 300 dpi and nothing else — the §3a PDF twin
  (06 record figures via `corridors_mapstyle.export`, now `EXPORT_FORMATS = (("png", 300 dpi),)`; QA item 7 counts the formats) and the
  07 wide-layout twin (`WIDE_STYLE["export_pdf"] = False`) are retired; the PDFs already written in both corridor packages were deleted.
  Nothing drawn changes.
- **M5.27 Package folder structure = the y2y / Alberta convention (2026-10-01, Ethan; presentation / provenance only):**
  the director package moves from `output_data/corridors_north/<run>/director_package/` (gitignored, one per run) to
  **`analyses/northern_connectivity/director_package/`** with the y2y layout — `geotiffs/` (the GIS export, formerly `gis/`),
  `tables/`, `figures/` (06, the record), `director_outputs/` (07, the curated few), `deck_outline.md` + `summary.json` (tracked
  by the existing `analyses/*/director_package/**` gitignore rule's two exceptions). `summary.json` is the run pointer the
  layout would otherwise lose: `run`, the run_config git record, cutoff + detour km, link / class / geometry counts, corridor
  km², H8 state, build time. One package holds one run: `package()` moves a different run's contents to `_superseded_<run>/`
  before writing (y2y `_superseded_*` convention). `corridors_director.PKG_DIR`; `package(out=)` overrides; `export_gis`
  default → `P.gis`. run003's package relocated on disk (22 MB); run002's stays in its run dir (historical, `_preD23_frozen/`).
  06 `RUN` set to v2_run003 (only run003 is re-run under D25c, M4.12). No methods, numbers or figures change.
- **M5.26 Pressure palette "sand" (2026-09-29, Ethan: the cividis yellow on the dominant Minimum class was rejected on sight;
  presentation):** `CLASS_PALETTE = "sand"` — four BrBG steps #ead59f / #cfa256 / #a5691b / #6e4007 (pale sand → tan → brown →
  dark umber) for Minimum → Maximum: light → dark like 01's cost swatches, a muted low end (L* 86, chroma < 32, so the 31-link
  Minimum class no longer shouts), and ≥ ΔE 20.1 from every option colour, the IPCA fill, the PA grey and the basemap under
  normal vision, deuteranopia and protanopia (grid search over 24 colormaps constrained to light → dark with a muted low end;
  the runner-up families — gist_earth, cubehelix — end in black). cividis / cividis_r / okabe / viridis stay registered.
- **M5.25 Pressure palette direction (2026-09-29, Ethan; presentation):** `CLASS_PALETTE = "cividis_r"` — the same four cividis
  steps reversed, pale yellow (#fee838) for Minimum through mustard and olive to navy (#00224e) for Maximum, so 02/03 read light →
  dark = low → high exactly as 01's cost swatches (cream intact → near-black barrier); the two keys had run in opposite
  directions. Colour-vision separations unchanged (the same set of colours).
- **M5.24 Option numbers on the band edge (2026-09-29, Ethan; presentation):** on 07 · 03 and the locators the numbered discs
  sit OUTSIDE their band, on its edge, with no leader, and clear of every other label: a post-draw pass (`director_plot`
  `post_draw=` on `_wide_map` / `_draw_inset`, run after each panel's labels and limits exist; y2y unaffected, default None)
  walks from the option's median cell outward — the pinned side first, then the other compass points — to the band's edge plus
  a few points, and takes the first disc inside the window that overlaps no option band, PA / IPCA fill, town, text label or
  earlier disc (display-space test with the renderer); a fallback sits on the pinned side's edge. `_option_marker_placer`.
- **M5.23 N2 re-pinned on run003 + composite options (2026-09-29, Ethan; presentation):** option 1 = Nahanni ↔ Dene Kʼéh
  Kusān part 2 (the tree edge, pinned explicitly by part label); **option 2 = Nahanni's second way south via part 3** — the
  backup link Nahanni ↔ part 3 continuing over the part 3 ↔ part 2 link, as ONE option whose band is the union of the two
  links' bands (`EXAMPLE_PICKS` accepts a list of pairs per option; `_option_masks`, M2 and the pin checks handle the
  composite). Replaces the pre-D22 option 2 (Liard River Corridor ↔ Nahanni), which is no longer an edge. Numbering 1–8
  follows the pins; the rest of the slots await the re-pick from `propose_examples` under D25c.
- **M5.22 Pin rule in code (2026-09-29, presentation):** a pinned example pair that a run's network does not hold no longer
  crashes `package` — `_find_edge` returns None with a printed "PIN RULE FIRES" line, `select_examples` drops the option (or the
  slot when nothing resolves) and renumbers the survivors; 07's setup prints `propose_examples` so the re-pick is in front of
  Ethan. First fired on run003: N2's second option, Liard River Corridor ↔ Nahanni, is not an edge there (the tree reaches Nahanni
  through Dene Kʼéh Kusān part 2, with part 3 as the backup), so the interim numbering shifts until EXAMPLE_PICKS is re-signed.
  The interim inset windows are keyed by example SLOT (`INSET_SPEC[...]["slots"]`: A = N2's options, B = S1) instead of option
  numbers, so they follow whatever a slot holds on the run; a `nums` key is still honoured.
  *Same day, Ethan:* both interim windows are then FIXED to their run002 pixel windows (`INSET_SPEC[...]["window_px"]`: A over
  Dene Kʼéh Kusān / Nahanni / Liard River Corridor, B over Gwillim Lake ↔ Pine Le Moray) so the links between the three northern
  areas stay in view whatever the pins hold and A and B share one scale across runs — the y2y fixed-inset rule; drop the key to
  size a window on its slot again.
- **M4.12 D25c — fronts are corridor land (2026-09-29; applied from `spec/05_patch_D25c_fronts_as_corridors.md`; supersedes
  the D25 / D25a class and amends D25b):** Ethan's binding principle — nothing that is not protected is taken as given. In
  `counterfactual_squeeze`: `link_geometry` = contact (D24: width not assessable — width < 8 cells, absent, or path < 10
  cells), front (path shorter than the barrier-free width), strip (otherwise); `road_crossing` = `lcp_max_cost == 10`,
  flagged never classed; `near_contiguous` kept as a column (= front) for table continuity. `route_branches` decomposes STRIPS
  only (fronts: one component by construction, `n_branches` null; contacts: nothing to decompose — disclosed choice). In
  `classify_links`: contacts by the edge sense only; strips and fronts on D23's eight-cell table with B1 forced true on fronts
  (`b1_forced`), so the amended route flag on a front is the width condition alone; `link_class` is one of the four corridor
  classes for every non-zero-cost link. **G24** (G23 retired): one geometry and one class per link, fronts B1-forced and
  undecomposed, strips decomposed, the class invariant to the road flag, the eight-cell table folded, the 4 × 3 class ×
  geometry table (`class_by_geometry.csv`), and the amended D25b identity corridor + intra-name + augmentation = total band
  with `front_area_km2` / `front_share` as descriptors (`fronts.csv` replaces `near_contiguous_links.csv`). Presentation:
  the adjacent-areas rows retired from `corridors_director.CLASS` and `corridors_mapstyle` (tokens gone); fronts drawn in
  their class colour; `FRONT_OUTLINE` dotted on M2; `front_sentence` on M1's title; `propose_examples`: contacts never
  examples, N2–N3 by `width_new_km`, the two-branch link as slot R1, the pin check on contacts. NB04 order unchanged (2b
  before 4b: the geometry is measured there). Re-run on run003 only (04 → 06 → 07); numbers to R10. **run002 is NOT re-run**
  (Ethan 2026-09-29): it is the historical record — its pre-D23 products are frozen in `_preD23_frozen/`, its directory
  otherwise holds the 2026-09-28 D23–D25a re-classification (G18 measured there, R10), and nothing downstream reads it now.
- **M4.11 D25a / D25b (2026-09-28; applied from `spec/05_patch_D25a_near_contiguous.md`; supersedes the provisional build
  noted under M4.9 below):** sub-classes exactly as the patch — barrier (`lcp_max_cost` ≥ 100), roads or cuts (`lcp_max_cost`
  == 10 or ratio < `squeeze_ratio`), open front (otherwise); `near_contiguous_links.csv` with the five per-link columns (gap_km,
  open_ground_width_med, squeeze_ratio_obs, lcp_max_cost, both areas' sizes); **D25b** accounting on per-edge band sums —
  `corridor_area_km2` (inter-name tree edges off fronts), `near_contiguous_area_km2`, `intra_name_area_km2`,
  `augmentation_area_km2`, `total_band_area_km2` — in `corridor_summary.json`; cutoff NOT recalibrated (comparability;
  the dependence of the area calibration on fronts is a known limitation the detour rule D31 avoids); **G23** = width floor
  before the trigger (the zero-new-land extension of the provisional build is WITHDRAWN: a link with no counterfactual front
  is width-not-assessable), non-null ratio and lcp_max_cost on every front, sub-class counts sum, and the area identity.
  Legend symbols per the patch (#8A8A8A 0.6 pt / #3A3A3A 0.8 pt outlines). `adjacent_sentence` for the Act 1 count.
- **M4.9 addendum — D25a (spec chat, 2026-09-28; implemented PROVISIONALLY ahead of the formal patch, which the chat files once
  the 18-link table is seen):** the near-contiguous trigger is unchanged (path shorter than the counterfactual median width; plus the
  zero-new-land case); the two sub-classes become THREE, decided by the maximum cost class on the least-cost path and the actual
  band's width ratio (D17, assessable on these links) — **barrier between** (cost ≥ 100 on the path), **front crossed by roads or
  cuts** (cost 10 on the path, or ratio < `squeeze_ratio`), **open front** (cost-1 ground, ratio ≥ threshold; a front with no
  width to measure counts as open). Nothing new is tuned. Per link `near_contiguous_links.csv`: gap length, counterfactual width,
  ratio, max cost class, the two areas' sizes, sub-class, edge flag, band area. **Knock-ons settled as proposed:** the cutoff is
  NOT recalibrated (it would move every band and break run002 comparability); the near-contiguous fronts' band area is reported
  as its own line (`near_contiguous_band_km2`, `corridor_km2_excl_near_contiguous` in corridor_summary.json and the classify
  printout) so the deck's corridor figure stops counting fronts; the pin check flags any pinned example link (N2–N3 option links
  included) that is now near-contiguous. Map symbol: hatch only / hatch + dashed outline / hatch + solid outline
  (`corridors_mapstyle.NEAR_CONTIGUOUS`). Story line for the chat: 18 of 45 links join areas that are effectively adjacent;
  corridor design in the north is a question about the remaining 27.
- **M4.9 addendum (2026-09-28, first execution — notebook 04 re-run on run002 under the new rules):** two amendments.
  (i) **D25 by its rationale:** a non-zero-cost link whose band holds NO new land (Gladys Lake Ecological Reserve ↔ Spatsizi
  Plateau, cost 1.0, path 0.6 km, every band cell inside the two parks) is near-contiguous — it has no width to measure and
  nothing to design; the rule is `lcp_len_cells < open_ground_width_med OR band_new_km2 == 0` (still no parameter).
  (ii) **G18's ratio requirement** holds on every link that REACHES the width test; a link declared near-contiguous or
  width-not-assessable may carry no ratio and is listed with its reason (the gate had failed on that one link). Measured on
  run002 at this re-run: **18 of 45 non-zero-cost links are near-contiguous under D25** (path shorter than the counterfactual
  band's MEDIAN cross-section, which is wider than the area/length width the earlier approximate read used), 0 with a
  cost-1000 barrier, 1 unassessable, 26 assessable; 8 squeezed; 28 branches over 27 decomposed links. **Record note:** this
  re-run wrote the D30 tiers, the D26 branch products and the D28 counterfactual bands (+ pinned constants) into run002's
  directory before G18 stopped it, so run002 on disk is mixed until 04 is re-run to completion there — intended by the D23
  patch (G18 is checked on run002, the pinned run), and the deck's run002 products change accordingly (post-pin class change).
- **M4.8 addendum — D23 ADOPTED (2026-09-28; applied from `spec/05_patch_D23_only_viable.md`; the proposal in M4.8 above
  is now the rule):** "only viable connection" = edge-irreplaceable (D7) ∧ one branch (D12) ∧ narrow (D17: `squeeze_ratio_obs`
  < `squeeze_ratio` 0.5, the ONLY width threshold — `resolve()` raises on `only_viable_ratio` / `route_width_thresh`). D12
  amended: `route_irreplaceable` = one branch ∧ narrow; `route_irreplaceable_topo` retained. Precedence (spec 05 §6, eight
  cells after the D24/D25 rows) in `_link_class`; `classify_links` writes `class_truth_table.csv` and runs **G18**: row sums =
  map counts, `squeeze_ratio_obs` non-null on every non-zero-cost edge, and the adoption check — links E ∧ B1 ∧ ¬S (only-viable
  under the retired rule, not now) are listed and, when pinned, the 06 regeneration rule fires. **Measured on run002 (R10):
  1 of the 4 pinned only-viable links sits in (E, B1, S) — Gwillim ↔ Pine Le Moray 0.41; Tatonduk ↔ Fishing Branch 1.00,
  Wilps Gwininitxw ↔ Swan Lake 0.96, Wędzih Yiné' ↔ Chase 0.99 fall to "last affordable link"** → post-pin class change,
  S1–S3 regenerated on run003 (`propose_examples`). Legend string updated (spec 06 v1.2.19); the 07 key and M1/M3 captions
  gain the "below its barrier-free width" clause. Every class consumer (`_routing_classes`, `package`, the 06/07 maps, the
  tables) reads `link_class`.
- **M4.10 Geometry-vs-ecology audit, run003 (D26–D31; 2026-09-28; applied from
  `spec/05_patch_D26_D31_geometry_audit.md`; adopted before D23–D25 landed, then the stand-ins were REMOVED the same session
  once they did — D28's assessable set is D24's, the example rule's top class is D23's):** six
  engine-generic rules (inherited by derived analyses), three gates. **D26** relative branch-sliver floor:
  `branch_min_frac` 0.05 × the link's new-land band at `cutoff_branch` AND `branch_min_cells` 20; `branch_min_km2` retired
  (`resolve()` raises); per link `branch_dropped_n`, `branch_dropped_max_frac`, and `n_branches_fixed_floor` (what the
  10 km² floor would have kept) for **G21** (dropped-fraction distribution; every link whose branch count changes, listed;
  kept branches asserted against both minima). **D27** `locked`, `alt_test_run`, `edge_irreplaceable`: a locked link's
  irreplaceable class is eligible only after the D7 test on the full candidate set — `_locked_criticality` already prices
  the cheapest part-pair alternative under β on the extended part graph for every locked link, so `alt_test_run` is True
  for all of them and `alt_cost` = the priced backup (or the detour's cost when a route via other names survives); every
  class consumer (`_routing_classes`) reads `edge_irreplaceable`; **G20** asserts the eligibility invariant. Moot on
  run003 (D22: no locked links) and on wolverine (single-component raster nodes); kept for the engine. **D28**
  `width_ratio_p10`, `width_ratio_p50`, `pinch_pos` from per-position cross-sections (each band cell allocated to its
  nearest least-cost-path cell by distance transform on the band's window, new land only, 50 fractional bins along each
  band's OWN path; ratio real/counterfactual per position) — reported, not classed; **G22 (width)** asserts p10 ≤
  `squeeze_ratio_obs` with 5% tolerance (the latter is the area/length ratio, not a quantile — disclosed). **D29**
  `cg.augment` records the alternative the β test compared (`alt_i`, `alt_j`, `alt_cost`); `alt_len_km` = one early-stop
  traceback per tested bridge, `alt_mean_res` = cost/cells, `alt_kind` far / hard / both (plus affordable / none) with
  `alt_res_tol` 1.5. **D30** `near_opt_tiers` = fixed slack breaks cutoff/6, cutoff/2, cutoff (+ a fourth class, routable
  land beyond the band); percentile tiers retired (a run predating the constants takes config.py's and pins them);
  **G22 (tiers)** asserts the breaks. **D31** `cutoff_detour_km` = `cwd_cutoff_abs` × cell size written by `resolve()` and
  `set_cutoff()`; a derived analysis may set the detour and get the cost cutoff (both set and inconsistent → raise);
  **G22 (cutoff)** asserts the identity; `near_opt_map` / `near_opt_tiers_map` captions state the detour (≈ 4.1 km on
  run002). Constants in both config blocks (north + wolverine). 06: `propose_examples` (class-and-width-first S1–S3,
  N2–N3 unchanged) prints the proposal; `_profile_words` gains the D29 / D27 sentences. Zero-cost adjacency vector check
  declined (patch §7). Measured on run003 → R10.
- **M4.8 (D22) Within-name part links COMPETE (Ethan 2026-09-28; supersedes M4.4 / D16's rule-4 default
  for every `link_locked` name):** trigger = the 80 km² third part of Dene Kʼéh Kusān, 12.9 km from part 2, drawn
  as orphaned on the 07 maps although the network held a locked 695 km² band to it (locked edges have no
  centrality, owner or class, so their land is invisible on every class map and absent from
  `linkage_priority.tif` — the open question logged 2026-08-21). Ruling: option 2 of three (1 = draw the locked
  bands as their own class; 3 = merge the part) — the four `link_locked` names (Dene Kʼéh Kusān 3 parts, Liard
  River Corridor 3, Nahanni 2, Nááts'ihch'oh 2) become `link_competing` in `multipart_review.csv`: each part
  its own routing unit, its direct edges competing like any other (classified, owned, banded, prioritised);
  Tombstone stays `merge_parts`. The review file is Ethan's to edit and re-sign (H7); the run is a NEW run dir
  (`v2_run003`; the CWD cache is reused — seeds unchanged). **Calibration:** D16's rule "inter-name MST only"
  stands, so `calibrate_cutoff` now drops within-name part edges from the calibration set (they still enter the
  network; the count is printed) — otherwise the cutoff would absorb the new intra-name bands. Engine path
  verified (`_build_units`: link_competing → one unit per part; `_unit_D`; `_locked_edges` empty).
  `corridors_director._find_edge` resolves a pinned pair to the MST edge, then the cheapest, when parts give
  several matches (printed). **OPEN — D23 proposal, for the spec chat (Ethan: "we may need to rethink the
  criteria for 'only viable connection', since there is no scarcity there"):** today both = edge-irreplaceable
  (D7: cheapest alternative LINK > β × the bridge's cost) ∧ route-irreplaceable (`n_branches == 1` in the
  near-optimal band). Neither measures land scarcity: a leaf's bridge is the cheapest by construction, and one
  WIDE lens across intact land counts as one branch. The D17 counterfactual already measures scarcity (band
  width ÷ its barrier-free width). Proposed: 'only viable connection' := edge-irreplaceable ∧ n_branches == 1
  ∧ `squeeze_ratio_obs` < θ (θ = the D17 threshold 0.5, or 0.75 for a 'narrowing' margin); a leaf across
  intact land then reads 'last affordable link' at most. Expected on run003: part 3's bridge (cost 48.8) has
  Dene part 1 at 121.4 (≤ β·48.8 = 122.0) and cheaper neighbours (Liard River Corridor Park 3 km from option
  2's band) → a backup → 'securing', so the criterion change is a general safeguard, not a rescue of this case.
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
- **M5.11 Director package (2026-09-03, PRESENTATION ONLY — spec 06 v1.2):**
  `corridors_director.py` + `06_director_package.ipynb` (→ `06_tables_and_figures`, 2026-09-28) over a loaded run; zero new solves.
  Renames (director legend strings), selects (top-k by rule), renders (flat swaths, CVD
  palette — squeezed in purple), assembles (profiles, T1/T2, draft .pptx). Two items that are
  METHODS-ADJACENT and therefore logged here: (i) axis-C attribution for T1 is computed over
  members that drop a PROPOSAL that is not an endpoint of the link (bins ≥0.95 / ≥0.75 /
  else) — 'we took every proposal as given; here is what depends on which one'; (ii) T2 and
  the profile chips use framing-1 link profiles (owner cells, majority crossing; M5.9), so
  every flagged link — including the near-touching ones with zero branches — has a row;
  chips are percentiles among all profiled links, never raw values. Jurisdictions from
  Natural Earth admin-1 polygons (display + 'who's at the table' only); settlement lands
  pending an authoritative layer. H8 gate enforced in code.
- **M5.12 Director basemap for M1 + the new M0 cost map (2026-09-08, PRESENTATION ONLY — spec
  06 v1.2.2):** `corridors_director._director_base` — Natural Earth coast / admin-1 lines /
  Canada–US border, PA + IPCA fills, province NAMES, ten prominent cities (`MAJOR_TOWNS`), the
  14 biggest PA/IPCA names via `cc.label_named_areas`. Province names are placed
  automatically on EMPTY land: the province ∩ routing window minus a 35 km buffer around every
  named area and a 40 km buffer around every labelled city, then the pole of inaccessibility of
  the largest free piece (`shapely.maximum_inscribed_circle`); provinces holding < 4% of the
  window (Alberta) get no name. City labels default to the right of the dot; Mackenzie and
  Prince George goes left (`TOWN_LABEL_SIDE`) because the right side is corridor; Mackenzie was dropped from the city list 2026-09-09 because its label covered the Pine Le Moray links on either side. Two DISPLAY
  name overrides (`AREA_OVERRIDES`): the PA layer's string for Fishing Branch is mis-encoded
  ("Nj ‘Iinlii” Jjik") and is shown as "Ni’iinlii Njik (Fishing Branch)"; "Neah Conservancy"
  is shown with BC Parks' spelling "Ne’āh’". Node ids, tables and every computation keep the
  source strings. Legends sit below the map (`fig.legend`, lower centre). M0b = the same cost
  map with the four-class network hard-coloured on top (`map_cost(P, corridors=True)`; the
  region-scale sibling of the zoom overlay in M5.10's family). **Cost palette on the director
  maps (2026-09-09, Ethan: the class colours were lost in the magma ramp):** the four cost
  classes are drawn as DISCRETE muted warm-neutral tones — cream / khaki-grey / dark brown /
  near-black (`COST_COLORS`, a luminance ramp, CVD-safe) — so the surface is a quiet ground and
  the corridor classes, PA grey and IPCA teal sit on top as the figure; the cost classes are
  legend patches (with their land shares) instead of a colorbar. **SUPERSEDED the same day
  (Ethan: keep the cost colour as it was):** M0/M0b are back on the magma_r log ramp with the
  colorbar; the figure/ground separation on M0b is instead a WHITE HALO under every corridor
  swath (`halo_cells=6` × 300 m ≈ 1.8 km, `scipy.ndimage.binary_dilation` of the painted
  union) so the class colours never merge with the red/purple part of the ramp. Mackenzie was
  dropped from the city list (its label covered the Pine Le Moray links). The science figures
  (`cc.cost_surface_map`, the zoom overlays) keep magma_r and no halo. Nothing here enters any
  computation.
- **M5.13 M2/M3 rebuilt as half-window maps + example numbering (2026-09-09, PRESENTATION
  ONLY — spec 06 v1.2.3):** M2 (Act 1) and M3 (Act 2) now share M1's page layout and EXACT
  aspect ratio (`_half_extent`: bounding box of PAs + IPCAs + corridor land in the northern /
  southern half of the M1 frame, 4% pad, then widened or heightened to M1's aspect with the
  extra height taken toward the other half). Because the region is a diagonal band, each half
  frame covers ~¾ of M1's height (≈1.35× zoom) — a tighter zoom at this aspect would cut named
  areas. Both draw EVERY link in the M1 palette (`_paint_classes`, shared with M1); M2 adds the
  Act-1 examples' route branches in the options colour, M3 the D17 natural-width outlines. The
  six LINK examples are numbered 1–6 in act order (N2→1, N3→2, S1→3, S2→4, S3→5, S4→6; N1 the
  with/without pair stays unnumbered) and the number is carried on the map markers (circle
  up-left of the link's median corridor cell, leader line), profile-page titles, T1's Example
  column and deck slide titles. Markers: M2 = Act-1 examples + any Act-2 example outside the
  southern frame (S2 Tthetäwndëk ↔ Ni'iinlii Njik is a northern link, so 4 appears on M2);
  M3 = Act-2 examples in frame (3, 5, 6). Jurisdiction tint OFF by default on M2 (M1 look);
  a few local towns added per half (`NORTH_TOWNS` / `SOUTH_TOWNS`). Admin clip pad 150 → 500 km
  (the half frames exposed the clip edge). No computation touched.
- **M5.14 Examples pinned + M2/M3 as scale-preserving crops (2026-09-09, PRESENTATION ONLY —
  spec 06 v1.2.4, supersedes M5.13's framing and the rule-based example selection):**
  `EXAMPLE_PICKS` resolves Ethan's chosen pairs to edge ids (assert exactly one match).
  Numbering is per OPTION on M2 — N2's two route branches (D12 components) are 1 and 2, the
  two links from T'akú Tlatsini to the Mount Edziza / Stikine complex (Edziza and Stikine touch,
  so both links reach the same place) are 3 and 4 — then the Act-2 links 5–7; a multi-option
  example carries "1–2" / "3–4" on its profile page, T1 row and deck slide. Frames: `_crop_extent`
  (bbox of drawn content within a y-range + 15 km) drawn at M1's metres-per-inch
  (`_m1_scale`; figure sized to the crop, legend below), M2 north of the min-y of the Edziza /
  Spatsizi / Dene Kʼéh Kusān / Dune Za Keyih / Northern Rocky polygons, M3 south of the M1
  midline. Natural-width outlines removed from M3 (the ratio lives in T2 / S3's headline).
  Hudson's Hope dropped from the southern city list (collided with Fort St. John at this
  scale). No computation touched.
- **M5.15 Star-plot construction = mean percentile by theme (DECISION 2026-09-09, Ethan; spec 06
  v1.2.5; presentation only):** the director star plots for the numbered options (1–6) and for
  the proposed IPCAs / existing PAs as wholes use the Y2Y-wide director construction
  (`director_core.block_percentiles` + `plot_star_grid`): per-cell percentile of each hand-off
  layer over the DISCRETIONARY (unprotected) landscape, combined into the six block axes (core
  habitat = refugia; connectivity = 0.5 transboundary + 0.5 Carroll; biodiversity = 0.5 birds +
  0.5 mammals; carbon = 0.742 m_soc + 0.258 biomass; representativeness = percentile of EFG
  classes present per cell; intactness = gHM), then the COVER-WEIGHTED mean over the option's
  land (300 m mask → fractional 1 km cover, M6.5). Reference population = ALL unprotected Y2Y
  land by default (cross-package comparability); `reference="window"` re-ranks over the routing
  window's unprotected land. Rationale for percentile over value-per-area: one 0–1 scale with a
  plain meaning ("this land ranks at the 70th percentile for refugia"), robust to the carbon
  tails that compress a 5–95 stretch, and identical to the y2y-wide deck. The science stars
  (`results_core` richness / contribution / efficiency, `priority_link_stars`,
  `corridor_profile.csv`) are UNCHANGED — they carry magnitude, which the percentile does not.
  N1 / M4 (the Dene with/without pair) retired from the deck the same day.
- **M5.16 EFG block version — INHERITED CHANGE, ruling needed (found 2026-09-09):** the star
  plots' representativeness axis (M5.15) reads the block through `leverage_core.efg_paths`, i.e.
  the y2y R0-CURATED block (`iucn_efg_v3`: 20 features / 22 classes; y2y M2.11) with the R10.7
  construction (per-cell class-count percentile) — correct and identical to the y2y deck. But
  the northern package's OWN profiles read the EFG layers from the shared
  `aligned_stack/manifest.json`, which was rewritten under Y2Y_VERSION v3.1 on 2026-09-09 and
  now lists the 20 curated layers, whereas every stored northern profile (`corridor_profile.csv`
  2026-08-27, `priority_links_profile.csv` 2026-09-08, the T2 chips, G5) was computed on the
  40-class block ("groups present (of 40)"). Re-running any profile cell now silently switches
  the EFG axis to the curated block; G5 (audit invariance vs v1) would move on that axis.
  OPTIONS for Ethan: (a) adopt the curated block for the northern profiles (re-run the profile
  cells; "of 40" → "of 20"; exclude the EFG axis from G5 as macrorefugia already is, M6.3) —
  RECOMMENDED for cross-package consistency and because the curation removed artefact classes;
  (b) pin the northern notebooks to `Y2Y_VERSION=v1` for reproduction of the stored profiles.
  **RULED same day (Ethan): (a) — the curated block is adopted for the WHOLE northern analysis.**
  Mechanics: gate G5 moved into the engine (`cc.gate_g5`, `G5_REDEFINED` = macrorefugia + EFG
  (mean): reported, not asserted; NB02's G5 cell calls it); NB04 gained step 0b (re-attach →
  `cc.corridor_profile` + `cc.gate_g5`) so the audit regenerates without re-running NB02's
  `cc.start`. Products that carry an EFG axis and must be regenerated on the curated block:
  `corridor_profile.csv` + audit figures (NB04 step 0b), `alternatives_branches.csv` (NB04
  step 4c), `priority_links_profile.csv` + PROACT stars (05_results), `link_profiles_all.csv`
  / T2 chips / star plots / deck (06). "groups present (of 40)" becomes "(of 20)" everywhere.
  Every other axis is untouched. The stored 40-class values remain in git history / the run
  dir until overwritten; results_log R9.4 records the re-measured EFG axis.
- **M5.21 Output notebooks re-mapped to the y2y trail; the curated maps on the y2y Act 1 wide layout
  (2026-09-28, PRESENTATION ONLY — spec 06 v1.2.17):** `06_director_package` → `06_tables_and_figures`
  (the record, every output; unchanged otherwise) + `07_director_outputs` (the curated few, the mirror
  of `analyses/y2y/21`). 07's maps — 01 the movement-cost surface, 02 "where the land still offers
  choices" — are drawn by `director_plot.wide_map`, the y2y Act 1 asset (slide 13.33 × 7.5 in, frame
  panel + two insets at right, key under A, legend under B, hillshade + Natural Earth basemap, Cronos
  Pro; PNG 300 dpi + PDF), through a frame built by `corridors_director.director_frame`: G on the
  300 m routing grid (pu = routable cells, locked2d = the 32 PA nodes), the 10 draft IPCAs as the
  overlay (filled in the §3a IPCA tone + outlined, names in the insets), the §3a sector frame + 40 km
  as the window, the northern town table. Surfaces are categorical: the four cost classes in
  `ms.COST`'s magma swatches; the routing classes in `ms.CLASS`'s pressure levels (H8 folding as on
  M1) — the ramp slot is the key. Colours / words = `corridors_mapstyle` (one source); layout / type
  = `director_plot` (one codebase with the y2y package: `load_frame` split out of `load()`, the
  1 px = 1 km constants replaced by km × px-per-km, identity on the 1 km grid — the y2y `load()`
  namespace verified name-for-name; Alberta shares the path; y2y methods_log M4.41). The §3a slide
  template, Noto Sans, hand-drawn legend and `ms.inset` do not apply to 07; §3a keeps governing 06's
  record figures. Insets: `INSETS = "clusters"` sizes A / B on the package's numbered clusters in the
  y2y schema (`tables/picks.csv` + `geotiffs/clusters.gpkg`, the next build step); `"interim"`
  (current) = the v1.2.13 frames A (options 1–2, Nahanni's ways south) and B (option 5, Gwillim Lake ↔
  Pine Le Moray) as pixel windows, re-fitted to the panel aspect. Zero-render smoke on `v2_run002`
  passed (frame 5,767 × 2,809 px; window (−67, 2942, −66, 5900) px; A 152 × 214 km, B 114 × 83 km
  before the fit; cost shares 88.2 / 5.4 / 0.3 / 6.1 %; class cells 353,248). Nothing analytical
  changed. Ethan renders 07 (numeric order 06 → 07).
  *Addendum (2026-09-28, first render):* the IPCA legend string is the §3a jurisdictions row "Proposed IPCAs" (the
  parenthetical had pushed the legend box past inset B); the ramp tick words are hand-wrapped to ≤ 11–12 characters a line
  (four ticks share a ~4 in bar at 14 pt); and the frame's hillshade is read over the WINDOW rather than the raster
  (`director_plot.load_frame` → `read_hillshade_window(scale=1)` + `draw_basemap(hs_extent=)`): the sector window runs
  20 km past the raster edge, so the raster-shaped shading footprint had drawn as a grey box inside the frame (measured on
  the PNG: shaded land 235/235/233 inside, unshaded 247/247/245 in the margin). Y2Y (no window) unchanged; Alberta's
  integer window inside its raster reads identical values.
  *Addendum (2026-09-28, Ethan: "inset box B should be same scale as A"):* `corridors_director.inset_windows` gives every
  inset window the largest width and the largest height among them, about each window's own centre
  (`INSET_SAME_SCALE = True`, `_same_scale`), before director_plot's aspect fit, so A and B draw at ONE map scale — interim:
  A 152 × 214 km and B 114 × 83 km both become 193 × 214 km after the fit (B was 114 × 126). The same rule applies in
  cluster mode, which now returns explicit windows (member polygons' bounds + `STYLE["inset_pad_km"]`, floored at
  `STYLE["inset_min_km"]`, then equalized) instead of leaving the sizing to director_plot.
  *Addendum (2026-09-28, Ethan):* **07 · 03 = the route options 1–4** (`figure_options_wide`): the record's M2 on the wide
  layout — the pressure classes as on 02, each option's corridor band on top in ONE colour (`OPTIONS_COLOR`, equal weight)
  with a ~1.2 km dark rim per option, numbered 1–4 at the band's median cell (M2's white-disc marker, offset in points so
  it reads alike on the frame and in the insets), PA / IPCA fills over the options as on M2. **Inset B = options 3–4**
  (T’akú Tlatsini → Mount Edziza / Stikine) instead of option 5 — `INSET_SPEC` changed, so 06's `map_cost` insets and
  07's interim windows (01–03) all carry A = options 1–2, B = options 3–4; option 5 (Gwillim Lake ↔ Pine Le Moray)
  keeps its M3 marker and its star / table rows.
  *Addendum (2026-09-28, later — SUPERSEDES the inset-B change above; Ethan mistyped):* inset B stays the Gwillim Lake ↔
  Pine Le Moray window it always was. The deck's EXAMPLE NUMBERING changes instead (`EXAMPLE_PICKS`, list order = numbers):
  1–2 Nahanni's two ways south (inset A); **3 = Gwillim Lake ↔ Pine Le Moray** (was 5); **4 = Gwillim Lake ↔ Monkman**, a
  NEW pick — a narrowing (squeezed) corridor lying 100% inside inset B (515 km²; Carp Lake ↔ Pine Le Moray, 0.23× its
  natural width and 99% inside B, is the alternative, one line to switch); 5–6 = T’akú Tlatsini → Mount Edziza / Stikine
  (were 3–4); 7 = Wilps Gwininitxw ↔ Swan Lake; 8 = Carp Lake ↔ Pine Le Moray (unmarked). The numbering runs through the
  record (M2 draws 1, 2, 5, 6; M3 marks 3, 4, 7; `star_options` / `table_options` rows follow). On 07 · 03 each option's band
  is filled in ITS NUMBER'S colour from the y2y cluster palette (`director_plot.STYLE["cluster_colors"]`: 1 red, 2 magenta,
  3 blue, 4 dark orange; the single options blue of M2 stays on the record), the marker rim in the same colour, and the
  legend entry is the y2y cluster swatch handle reading "Route options" (Ethan: the same icon as the y2y analysis).
  *Addendum (2026-09-28, Ethan: "red and pink aren't adjacent"; "corridor pressure colours ... viridis steps?"):* the options
  take the y2y palette in a PERMUTED order, `OPTION_COLOR_ORDER` = 1 red, 2 blue, 3 magenta, 4 dark orange, so the two
  adjacent options in each inset (1 & 2 overlap; 3 & 4 meet at Gwillim Lake) are red / blue (ΔE 97 / 72 under deutan /
  protan) and magenta / orange (97 / 105) rather than red / magenta (45 / 46); the legend swatches follow option order
  (`director_plot.cluster_handle(colors=)`, y2y M4.41 addendum). **Corridor-pressure palette → viridis steps**
  (`corridors_mapstyle.CLASS_PALETTES["viridis"]`, `CLASS_PALETTE = "viridis"`, `set_class_palette` to switch back to the
  Okabe set): viridis at 0 / 0.70 / 0.80 / 1.0 = #440154 / #44bf70 / #7ad151 / #fde725 for Minimum / Some / A lot / Maximum —
  dark purple → green → light green → yellow, the y2y ramp's own reading (purple low, yellow the top). Chosen by a grid
  search over step positions (0.05 grid, all 4-subsets) maximising the worst CIE76 ΔE between each class and every other
  class, the four option colours, the IPCA fill (#5F9EA0) and the PA grey (#8f8f8f) under normal vision, deuteranopia and
  protanopia: 21.3 (green vs the PA grey, deutan). The Okabe set scored 7.3 (its orange vs the option orange) and the evenly
  spaced viridis sets 4.6–14.3 (their blue step vs the magenta option under deutan). The §3a.1.1 palette table is superseded
  for the class fills on every `ms.CLASS` consumer (07's maps, `figure_m0b(corridors=True)`, `export_gis`, the QA); the
  record's own M1–M3 keep `corridors_director.CLASS`.
  *Addendum (2026-09-28, later — Ethan rejected the viridis steps on sight):* **corridor-pressure palette → cividis steps**
  (`CLASS_PALETTE = "cividis"`; viridis and the Okabe set stay registered): cividis at 0 / 0.70 / 0.85 / 1.0 = #00224e /
  #aea371 / #d6c35d / #fee838 for Minimum / Some / A lot / Maximum — navy → olive → mustard → yellow (yellow = the top, as on
  the y2y ramp; `"cividis_r"` = the same steps reversed, one line to switch). The search now also scores the basemap land
  and water tones so no step goes pale: worst ΔE 22.7 (mustard vs the option orange, deutan), classes ≥ 28 apart. Of the
  28 colormaps searched, only afmhot (black + cream), plasma (magenta / orange, the option hues) and gist_earth (black +
  navy) scored higher; cividis is the muted, CVD-designed one.
  *Addendum (2026-09-28, Ethan: "star plots for the four route options, same as y2y ... two insets ... the same consequences
  table"):* **07 · 04 stars + locators, 07 · 05 consequences**, all on the y2y CONSTRUCTION and the y2y ASSETS.
  `corridors_director.option_profiles_y2y` (cached on P) puts each option and the two reference nodes on the y2y director
  construction over the Y2Y-wide allocatable landscape: per star axis the mean percentile (`director_core.block_percentiles`,
  M5.15) and the consequences ratio (`director_core.ValueRatios`: mean raw value ÷ mean over allocatable land), both with the
  fractional 300 m → 1 km cover weights (M6.5; `ValueRatios.of(weights=)` added for it, y2y M4.41 addendum). Stars =
  `director_plot.star_grid` (split out of the y2y `_stars`: one drawing function), one star per option in the option's colour,
  titles "Option N / (the link) / km²". Locators = the two inset windows A (1–2) and B (3–4) on the star grid's geometry
  (`option_locators`: A centred under stars 1–2, B under 3–4; square, one scale, the classes + options as on 03) — two panels
  for four stars, Ethan's call. Consequences = `director_plot.consequences_table` (transposed, per-row RdBu over the option
  columns) with `ref=` / `col_label=` / `group_label=` / `source=` from outside; reference columns = Nahanni National Park
  Reserve + Dene Kʼéh Kusān (`CONSEQ_REFERENCE_NODES`, the y2y rule of one real PA + one real IPCA; both are network nodes).
  Rows to `director_package/tables/route_option_consequences.csv`. Nothing analytical changed; the record's `star_options` /
  `table_options` stand.
  *Addendum (2026-09-28, Ethan: "label all the PAs and IPCAs in the insets"):* the northern frame's PA name layer is the
  network's 32 PA nodes (node_parts, display names via `AREA_OVERRIDES`, no area floor) instead of the y2y PA vector at
  ≥ 300 km² (which drops Klua Lakes, Stone Mountain, Mount Blanchet); `WIDE_STYLE` sets `inset_pa_names` / `inset_ipca_names`
  / `locator_pa_names` = 99 and `inset_declutter = False` (new director_plot knobs, y2y defaults 5 / 3 / True unchanged;
  `director_core.label_areas_px(declutter=)`), so every PA and IPCA node inside a wide-map inset or a locator panel is named.
  *Addendum (2026-09-28, Ethan: "the legend box on 03 needs to be moved down"):* the wide layout's legend is anchored by
  its TOP edge just under inset B (`WIDE_STYLE`: `wide_legend_loc = "upper center"`, `wide_legend_y = 0.165`; new
  director_plot knobs, y2y default `"center"` / 0.103 unchanged), so the three-entry legend on 03 grows downward instead of
  into inset B, and the legends on 01–03 share one top edge.
  *Superseded the same day (Ethan: "center it between the bottom of panel B and bottom of page"):* `wide_legend_between = True`
  — director_plot measures, at draw time, the gap from inset B's bottom edge to the bottom of the ramp block under A (the
  page bottom once the figure is trimmed) and centres the legend box in it; a box taller than the gap hangs from B's bottom
  edge instead. The y2y default (False: the fixed "center" / 0.103 anchor) is unchanged.
- **M5.20 Cartographic contract + basemap data (2026-09-11, PRESENTATION ONLY — spec 06 §3a,
  v1.2.14):** `corridors_mapstyle.py` is the single style source (palette, type, templates,
  layers in the §3a.1.6 order, legend builder, locator, 100 km bar + north, PDF/PNG export,
  render QA with Machado-2009 deuteranopia / protanopia simulation and CIE76 ΔE ≥ 20 between
  class hues, glyph-coverage and label-overlap checks). Data acquired for CARTOGRAPHY ONLY (never
  analysis inputs): Copernicus GLO-90 DEM (AWS open data, 408 1° tiles, lat 52–69 / lon 144–119 W)
  → `dem_300m.tif` → `hillshade_300m.tif` (gdaldem, az 315 / alt 45) on the routing grid + 60 km;
  Natural Earth 10 m lakes + rivers (+ North America supplements; stand-in for the contract's
  HydroSHEDS layers); Noto Sans TTFs. The four cost classes are drawn as flat greys on the context
  figure (no colour ramp, no colourbar); water is drawn over the cost-1000 class in blue. M0b built
  first at Ethan's request; slide layout 50 / 48 instead of 68 / 30 (sector aspect), disclosed.
- **M5.19 D21 adjacency (neighbour) graph — diagnostic universe (2026-09-11; `05_patch_D21_adjacency.md`
  spliced into spec 05, 06 v1.2.9):** `cc.adjacency_graph`. Cost-allocation adjacency on the CACHED
  part-level CWD fields: argmin over the 48 part fields (ties → lowest part id; `allocation.tif`,
  int32, −1 off the routable window), zone boundaries by 8-connectivity, parts contracted to routing
  units (= names here; zero-cost cliques are NOT contracted — touching names count as neighbours,
  which matches the network's adjacency edges; noted as a deviation from the patch's "as in §7").
  Euclidean allocation (`scipy.ndimage.distance_transform_edt`, LM's default) as the comparison
  column. Per pair, with no new routing: the least-cost path is read as the ridge `CWD_u + CWD_v ≤
  min + 0.5` on the unit fields; intervening zones (`via_zones`) and crossed masks (the LM
  drop-through-core count) come from that ridge; length = the traced `centreline_km` for backbone
  edges, else a straight-line proxy between the ridge's two ends (the ridge's cell COUNT is an area
  on uniform land — 78 vs 21.6 km on the harness — so it is not used). LM's optional filters are
  OFF; their would-remove counts are printed. G17 = every inter-name MST edge is adjacent (hard
  assert; locked intra-name edges exempt). Products: `adjacency_edges.csv` (every adjacent pair +
  every backbone pair), `adjacency_nodes.csv` (`n_neighbours`, Euclidean and backbone degrees),
  `is_adjacent` / `is_adjacent_euclid` / `via_names` on `corridor_edges.csv`, `figures/adjacency_map.png`
  (lines between area centres, never bands). NOT a routing input; no bands; no legend class; no
  change to any product. Config `adjacency` dict (filters off). NB02 step 2c after G15; NB04 step 0b
  runs it on the loaded run. Toy-verified. Follow-up D7 amendment (restrict backups to adjacency)
  is NOT taken: decided after October from the measured count of non-adjacent backups.
  Same day (M5.17 addendum, presentation): the option masks for the star plots and the two
  alternatives tables are the route BRANCHES at the tightened allowance for EVERY option
  (options 3–4 had used whole bands) — one definition, 06 v1.2.11. SUPERSEDED the same day
  (06 v1.2.12, Ethan): every option is a LINK's full owned corridor band, as on M1; the Act-1
  example is re-pinned as Nahanni ↔ Dene Kʼéh Kusān (1) and Nahanni ↔ Liard River Corridor (2)
  — the two links' bands overlap on the plateau south of Nahanni (the Dene link owns 3,703 km²
  of it), and the Liard link's western route crosses the Dene IPCA.
  Same day, fix on first real-data run: locked intra-name edges carry PART ids in i/j (D16), so
  they are matched at part level (part-zone adjacency on the part fields) and reported
  separately, G17-exempt; the first pass had mislabelled three of them as non-adjacent
  inter-name edges. Presentation: `corridors_director.map_adjacency` (M1b, 06 v1.2.10) draws the
  universe beside M1.
- **M5.18 D19 centrality (2026-09-11; spec 05 changelog 2026-09-11 + merge note):** the chat's
  new D19 asked to switch centrality to current-flow betweenness; the engine has computed
  exactly that since the v2 rebuild (`corridor_graph.centrality`: edge current-flow betweenness
  on the quotient graph, conductance = 1/cost, zero-cost cliques contracted — column
  `ecfb_raw`). Implemented as a pin + comparison: config key `centrality: "current_flow"`
  (default when absent, so v2_run002 loads unchanged; `"shortest_path"` would route the
  priority surface off least-cost-path edge betweenness), both measures written on every
  edge as `centrality_cf` / `centrality_sp`, `cc.gate_g15` asserts finiteness / non-negativity
  and the tree-case identity (β = 0: the two are proportional — asserted as proportionality,
  since a rank test is broken by solver noise on exact ties) and writes
  `centrality_compare.csv`. NO product changes (linkage_priority.tif, classes, tables). Toy-
  verified (`corridor_graph.selftest` + harnesses). D18 (Linkage Pathways validation, G14, H9)
  and D20 (within-band circuit pinch points, step 4e, G16, H10) are DEFERRED per the spec's
  own later note; their constants are not written to run_config (dead-flag rule). The 06 spec's
  uncommitted v1.2.3–v1.2.7 entries were overwritten by the regeneration and reconstructed.
- **M5.17 Alternatives table for the options (2026-09-10, PRESENTATION ONLY — spec 06 v1.2.7):**
  `corridors_director.table_options` — the y2y-wide consequences-table format on the option
  masks (route branches 1–2, links 3–6, IPCAs and PAs as wholes): raw values per input in
  `results_core.RAW_SPEC` units (means for indices / densities, t C totals for carbon, EFG
  groups present of the curated 20), computed by `cc._profile_frac` with fractional 300 m → 1 km
  cover weights (M6.5; identical to `mask_profile` for binary weights, so the estimands match
  the Y2Y-wide tables), plus land km² and share of Y2Y. Rows grouped by the six y2y themes.
  The example profile pages, T1, T2 and the draft deck are retired from the notebook (functions
  kept). Same day (Ethan): TWO tables, never mixed — DENSITY (per-cell means; carbon = total ÷
  covered hectares, t C/ha; representativeness = mean number of curated EFG groups present per
  cell, the y2y per-cell-count construction) and ABSOLUTE (land, share of Y2Y, carbon totals,
  groups present, and THRESHOLD-FREE absolutes for the per-cell indices (Ethan's final call,
  2026-09-10, `ABS_SPEC`): where the raster sum has a physical reading it is shown in native
  units — bird / mammal richness × area = habitat km² summed across species (Σ_s AOH area of s
  inside the option), intactness × area = intact km²; where it does not (current density,
  Carroll centrality, refugial residence) the absolute is the option's share of the Y2Y-wide
  total (%) = `mask_profile`'s contribution metric. A top-30% 'high-value land km²' alternative
  (the y2y Act-1 VALUE_TOP cut) was considered and rejected as threshold-dependent. No
  computation touched.
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
