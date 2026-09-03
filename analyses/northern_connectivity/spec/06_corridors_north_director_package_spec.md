# Northern corridors — Director Package Spec

**Status:** v1.2 — BUILT 2026-09-03 (`corridors_director.py` + `06_director_package.ipynb`; see §8). Originally v1.1 build spec for Claude Code. Subordinate to `05_corridors_v2_addendum_run_and_alternatives.md` (methods live there; presentation decisions live here; ambiguous items logged in both — same rule as `director_package_spec.md` v1.1 for the Y2Y-wide analysis). **Key difference from the Y2Y-wide package: proposed IPCAs are taken as given here — seed nodes with the same treatment as existing PAs — so the alignment-only IPCA language from that package does not apply; see §1 guardrail.** Source artifacts: **v2_run002** (v2_run001 was an aborted pass, deleted) baseline + ensemble, `branches.*`, `alternatives_branches.csv`, `ensemble_attribution.tif`, axis C leave-one-out results, `multipart_review.csv`. All maps ESRI:102008, CVD-checked palette, existing PAs and proposed IPCAs as distinct layers on every map. Zero new solves.

## Changelog
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
