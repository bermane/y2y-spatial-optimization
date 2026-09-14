# Northern corridors — Director Package Spec

**Status:** v1.2.14 (2026-09-11) — BUILT 2026-09-03, trimmed 2026-09-10 (maps M0–M3, star plots, two alternatives tables) (`corridors_director.py` + `06_director_package.ipynb`; see §8). Originally v1.1 build spec for Claude Code. Subordinate to `05_corridors_v2_addendum_run_and_alternatives.md` (methods live there; presentation decisions live here; ambiguous items logged in both — same rule as `director_package_spec.md` v1.1 for the Y2Y-wide analysis). **Key difference from the Y2Y-wide package: proposed IPCAs are taken as given here — seed nodes with the same treatment as existing PAs — so the alignment-only IPCA language from that package does not apply; see §1 guardrail.** Source artifacts: **v2_run002** (v2_run001 was an aborted pass, deleted) baseline + ensemble, `branches.*`, `alternatives_branches.csv`, `ensemble_attribution.tif`, axis C leave-one-out results, `multipart_review.csv`. All maps ESRI:102008, CVD-checked palette, existing PAs and proposed IPCAs as distinct layers on every map. Zero new solves.

## Changelog
- v1.2.16 (2026-09-14, Ethan) — M0b carries **no corridor-pressure layer** (cost surface +
  jurisdictions only; legend groups Cost Surface / Jurisdictions); the cost swatches switch from
  greyscale to four **magma** samples (#FCF0B2 / #F9795D / #942C80 / #1A1042 for
  1 / 10 / 100 / 1000) — with no class swaths on the figure the contract's saturated-hue rule is
  not breached; `corridors_mapstyle.COST_PALETTE = "magma"`, the greyscale stays available.
- v1.2.15 (2026-09-11, Ethan; M0b review) — figure title "Northern Corridors: Movement Cost";
  legend titled "Legend" with subheadings **Cost Surface / Corridor Pressure / Jurisdictions**;
  the four class strings become the pressure levels **Minimum · Some (narrowing) · A lot (last
  affordable) · Maximum (only viable connection)** (counts kept as [n] chips; the long §3 legend
  strings are superseded on every contract figure via `corridors_mapstyle.CLASS`); the sector
  boundary is dropped (Y2Y region boundary only) and the locator removed from M0b.
  Same review: "Minimum" → **"Minimum (options)"** and its fill moves from the contract's light
  blue-grey `#AFC3CF` (ΔE 3–8 from the IPCA fill on white — indistinguishable) to periwinkle
  `#A6A6D9` (ΔE ≥ 22 from every other element under deuteranopia / protanopia); "Maximum" fill
  becomes hard red `#E41A1C` (ΔE 30 from vermilion under deuteranopia; hatch + black outline
  kept). §3a.1.1's palette table is superseded for those two rows.
  Jurisdictions rows renamed **"Existing Protected Areas" / "Proposed IPCAs" / "Y2Y Boundary"**
  (the as-declared / treated-as-network line moves to the caption or the claim slide).
  Cost Surface rows title-cased; **water inside the sector is drawn in the cost-1000 swatch**
  (not blue) — the contract's "water drawn separately in blue over the cost-1000 class" is
  superseded; blue water remains basemap context outside the sector only.
  "Maximum" is plain hard red — no black outline, no hatch (Ethan); the contract's CVD hatch
  fallback is retired because red vs vermilion clears ΔE 30 under deuteranopia on its own.
- v1.2.14 (2026-09-11, Ethan) — **CARTOGRAPHIC CONTRACT** (§3a, spliced from
  `06_patch_cartography.md`): one style module (`corridors_mapstyle.py`), Okabe–Ito-based class
  palette with hatch on only-viable, 55% area fills, greyscale + one-blue basemap with Copernicus
  hillshade and Natural Earth water, Noto Sans, slide / report templates with a furniture column,
  one legend per figure, no colourbars, PDF + PNG export, the 8-item render QA. **M0b rebuilt on
  it first** (Ethan's order); the v1.2.13 inset panels on `map_cost` are superseded by the §3a.1.5
  inset rule (fixed-extent boxes inside the map panel) and will return on M2 / M3.
- v1.2.13 (2026-09-11, Ethan) — **INSETS.** The region is too large for a single-frame figure to
  read, so every map gains the same two zoom panels, defined once from the option land
  (`INSET_SPEC` / `inset_frames`, cached on the package): **A** = the land around options 1–2
  (Nahanni's ways south), **B** = the land around option 5 (Gwillim Lake ↔ Pine Le Moray); each
  frame = bbox + 25 km, fitted to its panel's aspect; panels in the page corners the diagonal
  region leaves empty (A east of the region, B south-west), drawn with the SAME layer function as
  the main map, with a 50 km bar and connectors from the frame box. Built on M0 / M0b first
  (`map_cost(..., insets=True)`; colour bar moved to a horizontal bar in the south-east); the
  other maps follow.
- v1.2.12 (2026-09-11, Ethan; supersedes v1.2.11) — every M2 option is a LINK's FULL corridor
  band (its owned land, exactly as M1 draws it), and the Act-1 example is re-pinned around
  Nahanni's ways south after the Dene ↔ Nahanni and Liard ↔ Nahanni bands were found to
  overlap: **1 = Nahanni ↔ Dene Kʼéh Kusān** (minimum-network link, 41 km wide), **2 = Nahanni
  ↔ Liard River Corridor** (its backup), 3–4 = the two T'akú Tlatsini links, 5–6 unchanged.
  Route branches are no longer drawn or measured for any option; stars and both alternatives
  tables follow the same masks. Option 2's western route threads through the Dene IPCA
  (worked example `figures/route_test_liard_nahanni*.png`).
- v1.2.11 (2026-09-11) — M2's blue options now share ONE definition: the route BRANCH at the
  tightened (half-slack) allowance, the route test's own object. Options 3–4 (the two T'akú
  Tlatsini links) had been drawn as whole bands while 1–2 were branches; the star plots and the
  two alternatives tables use the same branch masks, so options 3–4 are re-measured on their
  branches (single-branch links: the branch is the tightened band). Display + measurement scope
  of the four option columns only; nothing else changes.
- v1.2.10 (2026-09-11, Ethan) — the neighbour universe is shown BESIDE the main output, not only
  in an appendix: **M1b** = M1 (left) | the same basemap with every D21 neighbour link as a line
  between area centres and each area's neighbour count (right); lines never bands; one legend.
  `map_adjacency`, cell after M1 in `06_director_package`; needs notebook 04 step 0b's products.
- v1.2.9 (2026-09-11) — from 05 D21: `n_neighbours` available per name (appendix; optionally
  one phrase in the Act 1 narrative — "X could connect to N neighbouring areas"); `adjacency_map`
  in the appendix beside the tier/attribution maps, links as thin lines, never bands. No change
  to M0–M3, stars, or the two alternatives tables. Methods note gains one sentence: the
  neighbour graph is Linkage Mapper's network convention; the maps show the minimum network
  plus affordable backups; the difference is the choice space.
- v1.2.8 (2026-09-11) — from 05 D19 (the only active change of the Linkage Mapper comparison;
  D18/D20 deferred). The chat-regenerated copy of this spec (v1.2 base, saved as
  `scratchpad/spec_merge/06_chat_20260911.md`) dropped v1.2.1–v1.2.7 and was NOT adopted; it
  also overwrote the uncommitted v1.2.3–v1.2.7 entries, which are reconstructed below from the
  session record and methods_log M5.13–M5.17. Effect of D19 on the package: **none on any map,
  star or table** — the classes are D7 / D12 / D17, the examples are PINNED (v1.2.4), and the
  engine's centrality was already current-flow betweenness (05 merge note, M5.18);
  `centrality_compare.csv` is available for an appendix. The "already narrowing" class remains
  D17 and is described as geometric narrowing, not a flow bottleneck. Any methods note gains the
  Linkage Mapper precedent line (formal validation deferred, D18) and the values-as-audit
  sentence from 05 §6.
- v1.2.7 (2026-09-10) — **Notebook trimmed to what the workshop needs (Ethan):** link-profile
  chips, example profile pages, T1, T2 and the draft deck RETIRED from `06_director_package`
  (functions kept). After the star plots: TWO alternatives tables in the y2y-wide consequences
  format for options 1–6 + the IPCAs and the PAs as wholes, rows by theme, never mixed —
  `T_options_density` (per-cell means, carbon t C/ha, EFG groups per cell) and
  `T_options_absolute` (land, share of Y2Y, carbon totals, groups present, and THRESHOLD-FREE
  absolutes for the rest: habitat km² summed across species for richness, intact km² for
  intactness, share of the Y2Y-wide total for refugial residence / movement flow / corridor
  centrality; a top-30% high-value-land alternative was rejected as threshold-dependent).
  Decimals: one per row, set by the row's smallest value to two significant figures, none
  when every value ≥ 10, EFG rows whole numbers; CSV = fixed decimals, PNG adds separators.
  M5.17.
- v1.2.6 (2026-09-10) — thin black hairline (0.45 pt) around every named PA / IPCA polygon on
  M0–M3 so adjoining areas (Mount Edziza / Stikine River) read as distinct. Display only.
- v1.2.5 (2026-09-09) — **M4 / N1 AXED.** New section after M3: star plots of options 1–6 +
  IPCAs and PAs as wholes (`star_options`) on the Y2Y-wide director construction. **DECISION
  (Ethan, both packages): star axes = mean PERCENTILE by theme** over the discretionary
  landscape (y2y block axes; ring 0.5 = typical unprotected land), not value ÷ area; reference
  = all unprotected Y2Y land (IPCA land included; `reference="window"` = north-relative). M5.15.
  EFG curation (40 → 20) adopted for the whole northern analysis (M5.16, `cc.gate_g5`).
- v1.2.4 (2026-09-09) — **Examples PINNED by Ethan** (`EXAMPLE_PICKS`; rule-based selection
  retired): options 1–2 = the two route branches of Nahanni ↔ Liard River Corridor, 3–4 = the
  two links from T'akú Tlatsini to the touching Mount Edziza / Stikine complex, 5 Gwillim Lake ↔
  Pine Le Moray, 6 Wilps Gwininitxw ↔ Swan Lake, 7 Carp Lake ↔ Pine Le Moray (unmarked on M3).
  M2 / M3 = CROPS AT M1's MAP SCALE (M2 north of the Edziza / Spatsizi / Dene group, M3 south
  of the M1 midline), every link in its M1 colour, natural-width outlines dropped; numbers
  carried on markers and every downstream product. Tthetäwndëk ↔ Ni'iinlii Njik and Wədzih
  Yiné' ↔ Chase → appendix. M5.14.
- v1.2.3 (2026-09-09) — first M2 / M3 rebuild at M1's exact aspect ratio (superseded by v1.2.4's
  scale-preserving crops). M5.13.
- v1.2.2 (2026-09-08) — M1 promoted to the main plot and restyled to the y2y-wide basemap
  conventions (coast / admin-1 lines / Canada–US border from Natural Earth; province NAMES rather
  than postal codes, per Ethan; prominent cities; the biggest PA/IPCA names with the decluttered
  labeller); legend moved BELOW the map so it covers nothing; slight zoom-out. New **M0**: the
  movement-cost surface with PAs + IPCAs hard-coloured and no corridors — the 'what the land is
  made of' companion, same basemap and legend placement (deck slot: before M1). Province
  names are placed automatically in the most open country of each province (named areas +
  labelled cities buffered out; pole of inaccessibility); Alberta (< 4% of the window) is
  unnamed. Two display-only name fixes: Fishing Branch (mis-encoded in the PA layer) shown as
  "Ni’iinlii Njik (Fishing Branch)", Neah Conservancy as "Ne’āh’" — Ethan to confirm both
  spellings before the deck ships. M5.12. **M0b** (same day, Ethan's ask): the four-class
  network hard-coloured over the cost surface (`map_cost(P, corridors=True)`), so the land
  between the swaths reads as cost — deck order M0 → M0b → M1. 2026-09-09: the cost surface on
  M0/M0b switched from the magma ramp to four discrete muted tones (cream / khaki-grey / dark
  brown / near-black) with the classes as legend patches — the corridor palette was being lost
  in the ramp — then REVERTED the same day at Ethan's call: the magma ramp + colorbar stay, and
  M0b separates the swaths from the ramp with a ~1.8 km white halo under every corridor
  instead. Mackenzie dropped from the city labels (covered the Pine Le Moray links). M5.12.
- v1.2.1 (2026-09-08) — H8 CLOSED on measured data: D17 (width ratio vs the barrier-free
  counterfactual) yields **8 squeezed links**, not the draft map's 5 — the 5 survive in the same
  order; Gwillim↔Pine Le Moray is also squeezed but stays red (both-senses precedence); the two
  new ones are Skeena links (Wilps Gwininitxw↔Mount Blanchet 0.41, ↔Sustut 0.49). Presentation
  classes now both 4 / edge 3 / squeezed 7 / securing 31; flagged links 14 (T2). M1/M3/S4
  regenerate from the D17 column (automatic); S4 = Carp Lake↔Pine Le Moray at 0.23× ("already at
  0.2× its natural width"). The squeezed class now SHIPS.
- v1.2 (2026-09-03) — built. Decisions closed: (a) 7 examples incl. S4; (b) jurisdiction
  tint from Natural Earth admin-1 polygons (public domain, `input_data/basemap/`), settlement
  lands / Nations' initiatives = explicit 'pending authoritative layer' placeholder, never
  approximated; (c) attribution bins ≥0.95 / 0.75–0.95 / else computed over axis-C members
  that drop a PROPOSAL (IPCA) which is not one of the link's own endpoints (endpoint drops are
  structural, PA drops are not 'a proposal not proceeding'); (d) natural-width outline drawn
  from `bands_counterfactual.gpkg` once H8 is closed, ratio chip otherwise; (e) sector name =
  placeholder 'the southern edge of the sector' (constant `SOUTH_NAME`) pending the directors'
  own term. Palette: squeezed moved to PURPLE (#7b3294) — the orange/ochre pair fails the
  deuteranopia check, per the spec's own fallback. H8 gate is enforced in code: the squeezed
  class is withheld from M1/M3/S4 (and its legend row omitted, not shown as [0]) until
  notebook 04 has written the D17 columns. T2 uses framing-1 link profiles (owner cells,
  0.5-majority crossing) rather than `alternatives_branches.csv` so the three near-touching
  flagged links (zero branches) get rows; logged in both documents.
- v1.1 (2026-09-03) — IPCAs-as-given: guardrail rewritten, legend string and T1
  column phrasing updated, axis C reframed as stated-assumption sensitivity.
  Cross-log with 05 addendum: the "already narrowing" (squeezed) class is defined
  there as D17 (constant `squeeze_ratio` = 0.5, gate G13), pending H8 confirmation
  of how the draft map computed it. **This class does not ship in the deck until
  H8 is closed**; if the count changes from 5, M1/M3 and the S4 slot are
  regenerated from the confirmed definition.
- v1.0 (2026-09-03) — initial spec from design discussion.

---

## 1. Story architecture (two acts, one guardrail)

The package tells one story in two geographies, and the two-axis logic is the
established one from the linkage-prioritization literature (biological value ×
threat-and-opportunity; see §6): every link is placed by *how many options remain*
and *who can act on them*.

- **Act 1 — The north: room to choose.** Most corridor land sits in the securing
  regime — wide bands, multiple route branches, alternative links. Connectivity is
  not at risk from the landscape; it is contingent on decisions. The analysis's
  job here is not to point at a pinch point but to show that *because* options are
  open, corridor creation can follow relationships, jurisdiction, and the pace of
  IPCA realisation rather than being dictated by geography. Analytic backbone:
  axis C (leave-one-out). Director sentence: "here the land still offers choices —
  the question is who secures them, with whom, and in what order."
- **Act 2 — The southern edge of the sector: options are closing.** The flagged
  links — both-senses irreplaceable, edge-irreplaceable, squeezed — cluster at the
  sector's southern end. Here the corridor is where it is; the alternatives table
  is short or empty; band width is already below open-ground width. Director
  sentence: "here the map makes the decision — the remaining work is timing."
- **Guardrail — differs from the Y2Y-wide package on IPCAs.** In the Y2Y-wide
  analysis IPCAs were not locked in and were presented with alignment language
  only. **Here, proposed IPCAs are taken as given**: they are seed nodes with the
  same analytical treatment as existing PAs, the network assumes them realised,
  and corridors are routed between them. State this once, up front, on the claim
  slide and the methods one-pager: "This analysis treats declared IPCA proposals
  as part of the protected network." Consequences: (i) existing PAs and proposed
  IPCAs remain *visually and tabularly separable* (distinct fills, separate rows
  where node identity matters) so a director can see which endpoints are
  established and which are proposals — but neither is ever readable as a new
  priority, and the corridors are never described as reasons to create an IPCA;
  (ii) IPCAs enter only as declared by Nations (boundaries and names from the
  Nations' own initiatives), never as territory the analyst draws; (iii) axis C
  is presented as the sensitivity on this assumption — "we took every proposal as
  given; here is what depends on which one" — and is not framed as a hedge on
  the north story. Jurisdiction and tenure appear only in the presentation layer;
  the routing itself is jurisdiction-blind.

## 2. Examples (5–7 total, top-k presentational)

Selection is a presentation decision (top-k by rule, not a new threshold — same
doctrine as the Y2Y-wide cluster count). Slots:

- **N1 (required): Dene K'éh Kusān leave-one-out.** The single most
  decision-relevant output on record: what the network loses if the largest
  proposal is not realised. Rendered as a pair — network with / without — bands
  only.
- **N2–N3: securing exemplars.** Links where ≥2 route branches exist and the
  ensemble attribution is high across axis C members — i.e., corridors that are
  wanted under nearly every future and can be secured along more than one path.
  Pick the two with the largest `n_branches` × attribution product; tie-break
  toward links whose branches fall in different jurisdictions (that *is* the Act 1
  story).
- **S1–S3 (required): the both-senses irreplaceable links** [4 on current run —
  pick the 3 with highest criticality; the 4th goes in the appendix table].
- **S4 (optional, use if total ≤ 7): the most squeezed link** — smallest
  band-to-open-ground width ratio, presented with that ratio as the headline
  number ("this corridor is already at 0.4× its natural width").

Each example gets a one-page profile (map + ~120 words + 4-row mini-table),
following the South Coast Missing Linkages / Linking Colorado per-linkage profile
format (§6): what it connects, what the flag means in plain language, the values
audit row (carbon / AOH / macrorefugia / EFG / Carroll overlap, percentile chips,
no raw numbers), and — Act 1 profiles only — the tenure/jurisdiction line naming
who holds the land between the endpoints.

## 3. Maps

- **M1 (anchor, exists in draft):** the four-class regime map — securing regime,
  both-senses irreplaceable, edge-irreplaceable, squeezed — over existing PAs +
  proposed IPCAs, sector boundary dashed. Keep exactly this composition.
- **M2:** Act 1 map — securing-regime bands only, with branch alternatives for
  N2–N3 shown as *equally weighted* single-color swaths (no ranking implied), and
  a light jurisdiction tint beneath (BC / Yukon / NWT / settlement lands as
  declared).
- **M3:** Act 2 map — southern zoom, flagged links only, one color per class,
  open-ground width shown as a thin outline around the squeezed bands so
  "narrowing" is visible without annotation.
- **M4 (N1):** the with/without pair, small multiples, identical extent and
  symbology.

**Rendering rules (apply to all):** band/branch polygons as flat single-color
swaths — no slack ramps, no `linkage_priority` gradient, no least-cost
centrelines, no arrows. The near-optimality surface, tier maps, and
`ensemble_attribution.tif` are analysis products and appear only in the technical
appendix. Class colors: securing = light blue-grey; both-senses = red;
edge-irreplaceable = orange; squeezed = ochre (as drafted; verify CVD contrast of
orange/ochre pair — if inadequate, move squeezed to purple). Counts stay in the
legend as bracket chips.

**Legend strings (director-facing, replace engine vocabulary):**
- securing regime → **"Corridor land with options — route and partners can be chosen"**
- both-senses irreplaceable → **"Only viable connection — no alternative link or route"**
- edge-irreplaceable → **"Last affordable link — alternatives cost far more"** (β
  stays out of the legend; it lives in the profile footnote)
- squeezed → **"Already narrowing — corridor below its natural width"**
- existing PAs → **"Existing protected areas"**; proposed IPCAs → **"Proposed
  Indigenous Protected and Conserved Areas (as declared by Nations; treated as
  part of the network in this analysis)"**

## 3a. Cartography (cartographic contract; spliced from `06_patch_cartography.md`, 2026-09-11)

### 3a.1 One style module — `figures/mapstyle.py` — imported by every figure

No figure script may set a colour, font, line weight, extent, or export setting inline.
If a figure needs something the module lacks, the module is extended and the change logged.

#### 3a.1.1 Palette (all hex; CVD-checked with a deuteranopia + protanopia simulation before use)

**Analysis hues — the only saturated colours on any map**

| element | fill | outline | note |
|---|---|---|---|
| corridor land with options (securing) | `#AFC3CF` | none | light blue-grey, sits back |
| already narrowing (squeezed, D17) | `#E69F00` | none | amber (Okabe–Ito) |
| last affordable link (edge-irreplaceable, D7) | `#D55E00` | none | vermilion (Okabe–Ito) |
| only viable connection (both senses, D7+D12) | `#8C1A1A` | `#000000` 0.6 pt + diagonal hatch `///` | hatch is the CVD fallback — vermilion/maroon must remain separable in simulation; if not, hatch stays and the maroon darkens |
| proposed IPCA | `#5F9EA0` at 55% opacity | `#3E6F70` 0.5 pt | teal kept (established); opacity so labels and hillshade read through |
| existing PA | `#9A9A9A` at 55% opacity | `#6E6E6E` 0.5 pt | |

**Basemap — greyscale plus one blue; nothing else**

| element | value |
|---|---|
| land | `#F7F7F5` |
| hillshade | greyscale, multiply blend, 18% opacity (90 m Copernicus or SRTM; cartographic use only — not the terrain-null input, H5) |
| water (lakes ≥ 10 ha, rivers ≥ 28 m³/s from the same hydro sources as the cost surface) | `#CFE0EA` fill, no outline |
| ocean | `#E4EEF3` |
| coastline | `#9CB3C0` 0.3 pt |
| provincial / territorial / international boundary | `#7A7A7A` 0.6 pt dash `4 2` |
| sector boundary | `#333333` 1.0 pt solid |
| Y2Y region boundary | `#333333` 0.8 pt dash `6 3` |

**Cost surface (context figure only, never a basemap):** four flat swatches on the greyscale
axis — cost 1 `#FFFFFF`, 10 `#D9D9D9`, 100 `#8C8C8C`, 1000 `#3A3A3A` — with water drawn
separately in `#CFE0EA` over the cost-1000 class so water/ice/settlement are not one colour.
No colourbar; four swatches in the legend. Percentages go in the caption, not the title.

#### 3a.1.2 Type

One family with full diacritic coverage for Indigenous place names (Łł, ǫ, ë, ū, á): **Noto
Sans** (fallback DejaVu Sans, which also covers them; verify glyphs render before sign-off).
Sizes are fixed at the slide scale (figure width 13.33 in):

| role | size / weight / case | colour | halo |
|---|---|---|---|
| figure title | 15 / semibold / sentence | `#1A1A1A` | — |
| jurisdiction | 10 / regular / caps, +0.08 em tracking | `#8A8A8A` | none |
| PA / IPCA name | 8.5 / italic / as declared | `#2B2B2B` | white 2 pt |
| town | 8 / regular | `#2B2B2B`, dot `#2B2B2B` 2.5 pt | white 2 pt |
| annotation / callout | 8 / regular | `#1A1A1A` | white 2 pt |
| legend | 8.5 / regular | `#2B2B2B` | — |
| caption | 8 / regular | `#555555` | — |

Every label is placed by hand in the figure spec (§2) or by `adjustText` with a 3 pt minimum
gap; a label that still collides is dropped, not shrunk. Halo on every label over data.

#### 3a.1.3 Layout — one template, two aspect ratios

- **Slide** 13.33 × 7.5 in (16:9). Map panel occupies the left 68% of width; a fixed
  **furniture column** on the right 30% holds, top to bottom: locator inset (sector within
  the Y2Y region, `#333333` boundary, sector filled `#AFC3CF`), the legend, then scale bar
  and north indicator. Title above the map panel, caption line below it. Nothing else is
  ever auto-placed.
- **Report** 8.5 × 11 in portrait for the appendix, same furniture column at the bottom as
  a row.
- The sector is tall; on the slide template the map panel is cropped to the sector's
  bounding box plus 40 km, and the empty north-east (NWT interior) is allowed to be cut by
  the frame — the locator carries the context.
- Scale bar: `matplotlib-scalebar`, 100 km, two segments, `#2B2B2B`, bottom of furniture
  column. North indicator: single line-arrow with "N", same colour, beside it. Graticule:
  none on slides; 2° hairlines `#C8C8C8` 0.2 pt on report figures only.
- Export: PDF (vector, fonts embedded) + PNG 300 dpi, both, every figure, from the same
  call. Filenames as the figure ids (M1, M2 …) plus the run tag.

#### 3a.1.4 Legend policy

- **One legend per figure**, in the furniture column, built from patches using the director
  strings already in §3 — never from artist labels.
- Class rows in fixed order: options → narrowing → last affordable → only viable, then
  existing PAs, proposed IPCAs (with the as-declared / treated-as-network line), then the
  boundary lines. Link counts stay as `[n]` chips after the class name.
- No colourbars anywhere in the deck. Continuous surfaces (near-optimality tiers, ensemble
  attribution) appear only in the appendix and use three flat tiers with three swatches.

#### 3a.1.5 Insets

- An inset is a **named, fixed-extent box** declared in the figure spec: id, centre,
  width in km, which figure it belongs to. Maximum three per figure.
- Drawn on the main map as a `#333333` 0.8 pt rectangle with the inset id in its corner;
  placed inside the map panel along its lower or left edge with a 0.6 pt leader line to the
  box. Never in the furniture column.
- Insets use the same `mapstyle`, same layer order, no legend, no title; a 20 km scale bar
  and the id only. The main-map label set does not repeat inside an inset; the inset has its
  own hand-placed list (≤ 6).
- Same three-second rule: each inset exists to make one thing obvious, named in the spec.

#### 3a.1.6 Layer order (bottom → top), identical on every map and inset

ocean → land → hillshade → water → existing PAs → proposed IPCAs → corridor classes
(options first, only-viable last) → boundaries → inset boxes → labels (jurisdiction,
then PA/IPCA, then towns, then annotations).

---

### 3a.2 Figure spec table (one row per figure; Claude Code fills the label lists, Ethan signs)

| id | template | extent | layers (from §1.6) | hand-placed labels | insets | legend rows | three-second message |
|---|---|---|---|---|---|---|---|
| M0b context — what the land is made of | slide | sector + 40 km | basemap, cost-surface swatches, PAs, IPCAs, class swaths, boundaries | ≤ 10: 5 jurisdictions/towns, 5 anchor areas | none | 4 cost swatches, 4 classes, PA, IPCA, 2 lines | "the south is where the cost is" |
| M1 regime map (anchor) | slide | sector + 40 km | basemap, PAs, IPCAs, class swaths, boundaries | ≤ 12 | none | 4 classes, PA, IPCA, 2 lines | "options in the north, forced in the south" |
| M2 Act 1 — room to choose | slide | northern two-thirds | basemap + light jurisdiction tint, options swaths, branch alternatives equal-weight, PAs, IPCAs | ≤ 10 + partner labels for N2–N3 | up to 2 (N2, N3 branches) | options, PA, IPCA, jurisdiction tint key | "these corridors can be secured along more than one path" |
| M3 Act 2 — options are closing | slide | southern third | basemap, all four classes, open-ground outline on squeezed bands, PAs, IPCAs | ≤ 10 | up to 3 (S1–S3) | 4 classes + open-ground outline | "the map makes the decision here" |
| M4 with / without (N1 pair) | slide, two panels | identical extent both panels | basemap, PAs, IPCAs (dropped one hatched grey in right panel), class swaths | ≤ 6, same in both | none | shared legend, one column | "what the network loses if this one proposal does not proceed" |

Insets get their own rows beneath (id, parent, centre, width km, ≤ 6 labels, message).

---

### 3a.3 Render QA — Claude Code runs this on the PNG before showing any figure

1. Nothing clipped at the frame except the allowed NWT crop.
2. Zero label overlaps; every label over data has a halo; all diacritics rendered.
3. Legend, locator, scale bar, north present and in the furniture column; one legend only.
4. Class colours separable in deuteranopia and protanopia simulations; only-viable hatch visible at 100% and at 50% zoom.
5. No saturated hue outside the analysis palette; basemap greys + one blue only.
6. Layer order matches §1.6 (spot-check: a class swath is never under a PA fill).
7. Export produced both PDF and PNG; fonts embedded.
8. The three-second message: describe in one sentence what the figure shows at a glance and compare to the spec row. Report any mismatch rather than fixing the message.

Report the checklist result with the figure. A figure that fails any item is not shown.

---

### 3a.4 Build order and the prompt

Anchor first: **M1 only** until signed; then M0b (same extent, adds the cost swatches);
then M3 with its insets (hardest layout); then M2; then M4. Insets are built only after the
parent figure is signed.

Prompt to Claude Code (verbatim is fine):

> Create `figures/mapstyle.py` from 06 §3a.1 before writing any figure code — palette, type,
> layout templates, legend builder, inset helper, export function. Then render **only M1**
> per the §3a.2 row. Run the §3a.3 QA list on the PNG, fix every failure, and show me the
> figure with the checklist result. Do not start M0b, M2, M3, or M4 until I sign off M1.
> If M1 needs something `mapstyle.py` doesn't provide, add it to the module and note the
> addition; never style inline.


**Build record (2026-09-11) — deviations and additions, all logged in M5.20:**
- Module lives at repo root as `corridors_mapstyle.py` (the spec's `figures/mapstyle.py` would be
  gitignored by `analyses/*/figures/`); engine-module convention.
- Layout: the sector's aspect (0.49) leaves a 68%-wide map panel mostly empty on 16:9, so the
  slide template uses map panel 50% / furniture column from 54% (locator, legend, scale + north);
  the map is height-limited (≈290 km per inch) and the panel's spare width is where §3a.1.5
  insets go. Ethan to confirm or restore the 68/30 split.
- Hillshade: Copernicus GLO-90 (AWS open data, 408 tiles) warped to the 300 m routing grid + 60 km
  margin (`input_data/basemap/hillshade_300m.tif`; cartographic use only, never an analysis
  input — H5 stands). Water: Natural Earth 10 m lakes + rivers (+ North America supplements)
  instead of the HydroSHEDS layers the contract names (not on disk; swap when acquired).
- Type: Noto Sans downloaded to `input_data/basemap/fonts/` and registered at import; DejaVu
  Sans fallback. Letter-spacing (+0.08 em tracking) is not supported by matplotlib; jurisdiction
  names are plain caps.
- Built first: **M0b** (Ethan's order, ahead of §3a.4's "M1 first"): `corridors_director.figure_m0b`
  with its hand-placed label list `M0B_SPEC` (3 jurisdictions, 2 towns, 5 areas); QA checklist
  8/8 on the run002 render. M1, M3, M2 follow once M0b is signed.

## 4. Tables

- **T1 (main deck, one slide):** one row per example, plain-language columns:
  *Connects* (endpoint names) · *Status* (legend string) · *Room to move*
  (`n_branches`, as "3 route options" / "single route") · *If a proposal
  doesn't proceed* (axis C attribution, as Unaffected / Mostly unaffected /
  Depends on <name>) · *Endpoints* (Established / Proposed / Mixed — the
  PA-vs-IPCA separation directors asked to keep visible) ·
  *Co-benefits* (top-2 audit columns by percentile, as words) · *Who's at the
  table* (Act 1 rows only; jurisdictions + declared Nations' initiatives
  intersecting the band).
- **T2 (appendix):** the full flagged-link table — all 12 flagged links ×
  the complete audit column set from `alternatives_branches.csv`, plus
  `carroll2018_pctl` and endpoint class. Numeric, captioned with the row-unit
  caveat from D13.
- Every "Depends on <name>" cell must name the proposal. Because IPCAs are taken
  as given, this column is the analysis's disclosure of its own assumption, and
  it is the only place that assumption is tested — it belongs in the main deck,
  stated neutrally, not as a caveat.

## 5. Slide skeleton

1. Title + one-sentence claim ("In the north we choose corridors; in the south
   they are chosen for us.")
2. M1 with the two-act annotation (two callout boxes, no other labels).
3. Act 1: M2 + N1 pair (M4) + N2/N3 profiles.
4. Act 2: M3 + S1–S3 profiles (+S4).
5. T1.
6. What this asks of directors: Act 1 → sequencing and relationship investment;
   Act 2 → timing decisions. One slide, two bullets, no new analysis.
7. Backstop appendix: T2, tier/attribution maps, methods one-pager (cost surface
   provenance incl. terrain thresholds; climate = audit-only disclosure; Phase 7
   deferred).

## 6. Precedent (what comparable products did — checked 2026-09-03)

- **Two-axis prioritization (corridordesign.org / Beier et al. linkage work):**
  rank linkages on biological value × threat-and-opportunity and let stakeholders
  argue about criteria, not favorites. Our two acts are that graph's two
  quadrants, told as geography. T1 keeps both axes as columns.
- **Linking Colorado's Landscapes (SREP 2005):** priority ranks binned to
  very-high/high/medium/low; explicit *conservation opportunity* criterion
  (political support, willing landowners, local groups) scored per linkage — the
  precedent for T1's "who's at the table" column.
- **South Coast Missing Linkages:** per-linkage profile pages (map + narrative +
  land-status table) as the unit of communication — the precedent for §2's
  one-pagers.
- **Belote et al. 2016 / Dickson et al. 2017 (US corridor mapping):** national
  composite corridor-value maps with continuous ramps — the style we are
  deliberately *not* using at director level; ramps and centrelines stay in the
  appendix.
- **Pither et al. 2023 / O'Brien et al. 2026:** continuous current-density maps;
  same appendix-only treatment; cite as provenance on the methods one-pager.

## 7. Open decisions before build

- (a) Confirm example count (5 vs 7) and whether S4 (squeezed exemplar) makes the
  main deck.
- (b) Jurisdiction tint source for M2 (which authoritative boundary layers, incl.
  settlement lands) — needs the same declared-initiatives-only discipline.
- (c) Attribution phrasing bins for "Unaffected / Mostly unaffected / Depends on
  <name>" (proposed: ≥0.95 / 0.75–0.95 / else, computed over axis C members
  only).
- (d) Whether the open-ground width outline on M3 reads at print size; fallback
  is the ratio as a number chip per link.
- (e) Sector name to use publicly for "the southern edge" (avoid inventing a
  region name directors don't use).


## 8. Build record (v1.2, 2026-09-03)

- **`corridors_director.py`** (repo root, same convention as `director_core.py`): `package`
  (classes via `corridors_core._routing_classes` — D17-aware; axis-C attribution over proposal
  drops; endpoint class; Natural Earth jurisdictions rasterized on the routing grid; top-k
  example selection: N1 fixed, N2–N3 by `n_branches × attr_c` with a multi-jurisdiction
  tie-break, S1–S3 both-senses by `n_pairs_lost` then backup ratio, S4 min squeeze ratio),
  `link_profiles` (framing-1 profiles of every link → percentile chips), `map_m1..m4`,
  `profile_pages`, `table_t1`, `table_t2`, `build_deck` (via `director_core.build_deck`).
- **`06_director_package.ipynb`**: read-only; outputs → `<run>/director_package/{figures,tables}`
  + `north_director_deck.pptx` + `deck_outline.md`.
- Smoke-run on `v2_run002` (H8 open at the time): classes both 4 / edge 3 / squeezed 5 (analytic,
  withheld) / securing 33; examples N1, N2 = Liard River Corridor ↔ Nahanni (2 routes, spans
  BC/Yukon/NWT), N3 = Dene Kʼéh Kusān ↔ Liard River Corridor (2 routes), S1 Gwillim Lake ↔ Pine
  Le Moray, S2 Tthetäwndëk ↔ Nj ‘Iinlii” Jjik, S3 Wilps Gwininitxw ↔ Swan Lake Kispiox; 4th
  both-senses (Wədzih Yiné' ↔ Chase) → appendix; N1 pair: 33,041 km² with → 37,412 km² without
  Dene Kʼéh Kusān (+4,371 km² of corridor need). Final figures land when Ethan runs 04 → 06.
