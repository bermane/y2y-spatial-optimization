# Plan — `05b` Alberta Eastern Slopes: grizzly movement & highway permeability

**Status: DRAFTED, NOT APPROVED. No code written.** Drafted 2026-08-05, parked 2026-08-07.
Resume by re-reading this file; the three open decisions at the bottom gate everything.

**Origin:** written after guidance from **Jordan (Y2Y program director)** — verbatim in the
appendix. Jordan named **Tim Johnson** as the person more familiar with the Eastern Slopes and
explicitly invited contact.

---

## Why this exists: `03c` answers a question Y2Y didn't ask

Jordan's decision rule is *"if grizzly bears aren't moving there, or trying to move there but
unable to, it's not really a priority."* That is a **movement** criterion on **one species**.

`03c_ab_foothills` optimizes over the 8 continuous features in the aligned stack, and **not one
of them is grizzly-specific or resolves highways as barriers**:

| Feature | Relevance to Jordan's rule |
|---|---|
| `human_modification` (intactness) | weak proxy — a highway barely survives 90 m → 1 km averaging |
| `transboundary_connectivity` (Pither) | **omnidirectional, structural, all-species** — not grizzly, not highway-aware |
| `climate_corridors` (Carroll) | climate-analog flow, not animal movement |
| `climate_type_macrorefugia` | not movement |
| `irrecoverable_carbon` ×2 | not movement |
| `aoh_richness_mammals` / `_birds` | grizzly is 1 of ~200 mammals; richness ≠ grizzly |
| 40 × `iucn_efg` | ecosystem types |

Two further mismatches:

- **Jordan splits intervention by land tenure** — *protection* on private land, *permeability* on
  public/Crown. The stack has no tenure layer, and `03c` cost is `cost_uniform = 1`, so it cannot
  distinguish "buy this" from "build a crossing here."
- **Prioritizr is the wrong instrument for permeability.** It selects a *set of cells*; it does not
  route A→B. Already proven and reverted — see project memory `prioritizr-run-design`. The right
  tool is `corridors_core.py` (05), currently pointed north.

**The claim this deliverable makes:** *"Here is where grizzly movement wants to cross the eastern
slopes; here is where a highway blocks it; here is which of those blockages are already mitigated,
and which are not."* Ranked, named, mappable.

---

## Engine gaps — what `corridors_core.py` can and cannot do

Roughly 60% of the machinery exists. The gaps are specific and were verified against the source:

| Capability | Status |
|---|---|
| Least-cost routing, MST, swaths | ✅ works as-is |
| Near-optimal ensemble (robustness) | ✅ works as-is |
| Per-segment profiling + naming | ✅ works as-is |
| Scenario comparison | ✅ works as-is |
| **Polygon ROI crop** | ❌ `corridors_core.py:80-87` supports only a **latitude band** (`min_lat`/`max_lat`). Foothills needs the AB ∩ foothills polygon. |
| **Nodes from existing PAs only** | ❌ `corridors_core.py:99-101` unconditionally loads a proposed-PA source. Foothills nodes are the mountain parks. |
| **Multiple barriers** | ❌ `corridors_core.py:126` hardcodes exactly one barrier layer (`base ** gHM`). Highways need a second. |
| **Highway-crossing detection** | ❌ **entirely new** — this is the actual product |
| **Crossing-structure / WVC intersection** | ❌ **entirely new** |

Also: `config.build_roi` is keyed off `ANALYSES[...]`, not `CORRIDORS[...]` — needs a small
refactor to accept a roi spec directly so both callers share one implementation.

---

## Phases

### Phase 1 — generalize the engine *(no new data; safe to start immediately)*
- `load()`: accept `region_filter: {"mode": "roi", ...}` alongside the existing lat-band, reusing a
  refactored `config.build_roi`. Lat-band path unchanged so `north` is untouched.
- `load()`: make `nodes.proposed` optional (`None` → existing PAs only).
- `resistance()`: `barrier` accepts a **list** of terms, each `base ** layer`. Single-dict form
  still accepted so `north` doesn't move.
- **Regression gate:** re-run `north`, assert byte-identical corridors + Jaccard 1.0 vs current
  output. Same doctrine as the 06 G1 equivalence gate.

### Phase 2 — highways as explicit barriers
The stack cannot represent highways: a 2-lane road averaged from 90 m gHM to 1 km is effectively
invisible. The network must be rasterized as a **line**, not inherited from gHM.

- Acquire AB highway centrelines; rasterize to grid with per-class barrier weight (divided 4-lane
  ≫ 2-lane paved ≫ gravel), optionally scaled by **AADT** where available.
- New aligned layer via 02's stage-1 pattern → `highway_barrier.tif`. It is a **barrier, not a
  prioritizr feature** (`is_feature: False`) — it must never touch the PU mask or a solve.
- Feeds `resistance` as barrier term #2.

### Phase 3 — crossing-site detection *(the new product)*
New function, roughly `cc.crossing_sites(A)`:
1. Intersect the corridor network (centre-lines **and** swaths) with the highway raster → candidate
   crossing cells.
2. Cluster contiguous cells into **sites**, each carrying: highway name, lat/lon, parent corridor
   segment, swath width (narrow = pinch point), **ensemble frequency** (how many of the 12 jittered
   runs route through here = robustness), least-cost flow volume.
3. Rank. Narrow + high-frequency + high-flow + major highway = top site.
4. Outputs: `crossing_sites.gpkg` + `.csv`, plus a map.

**Limitation to state up front:** at 1 km this identifies *a stretch of highway a few km long*, not
a structure location. Actionable for Jordan ("this segment of Highway 3"), but not engineering
siting. See resolution decision below.

### Phase 4 — grizzly driver swap *(blocked on the bear layer — Ethan sourcing as of 2026-08-05)*
Current driver blend is `transboundary_connectivity 0.5 / climate_corridors 0.3 /
climate_type_macrorefugia 0.2`. The latter two are **climate-analog layers with no bearing on where
a bear walks.** Proposed direction: grizzly habitat/RSF dominant, structural connectivity secondary,
climate layers dropped or held at low weight as a future-proofing term.

**This is a methods change and needs explicit sign-off** (per project memory `autonomy-vs-methods`).
Specific weights to be proposed once the layer is known.

Keep two roles separate: grizzly as **driver** (permeability surface) vs as **validation** (do
modeled corridors match known occupancy/mortality?).

### Phase 5 — wildlife crossings data *(blocked on knowing what the dataset contains)*
- **Validation:** do modeled sites reproduce the Banff/Bow Valley TCH structures — the most-studied
  crossing system on Earth? If yes, the model is credible on unmitigated stretches. A genuine
  methods result, not just a figure.
- **Gap map:** classify every site **mitigated** / **unmitigated** / **structure-with-no-modeled-
  movement**. The middle class is Jordan's target list; the third is either over-build or a
  resistance-model error — informative either way.
- **Jordan's exception clause:** if WVC/mortality points are present, cluster them and flag sites
  that are *both* a grizzly pinch point *and* a multi-species mortality hotspot. Highest-confidence
  recommendations in the deliverable.

### Phase 6 — the protect / permeate split
Jordan splits intervention by tenure: **protect** private land, **permeate** public land. Nothing in
the stack knows tenure. An Alberta tenure layer (Green/White Area, freehold vs Crown) lets every
output carry an intervention label — what makes the deliverable actionable rather than descriptive.

---

## Three open decisions (these gate the work)

**1. Resolution.** 1 km is coarse for highway crossings. The foothills window is ~118,000 km² (~9%
of Y2Y), so **300 m is genuinely tractable here** even though it isn't Y2Y-wide, and CLAUDE.md
already names 300 m as the ceiling. Would require a foothills-specific stage-1 warp at 300 m.
**Recommendation: build Phases 1–3 at 1 km to validate the pipeline, then re-run at 300 m for the
final product.** Resolution changes need approval (project memory `autonomy-vs-methods`).

**2. What happens to `03c`?** **Recommendation: keep it, but demote and reframe** as the
*protection* track — "where is the highest-value foothills land," pairing with tenure in Phase 6 —
and don't lead the deliverable with it. It answers a question Jordan didn't ask, so it shouldn't be
the headline. Alternative is dropping it entirely; not preferred, it's already built.

**3. Node set.** Default proposal: all AB mountain parks (Banff, Jasper, Willmore, Kananaskis
complex, Castle, Waterton) + foothills PAs above a size threshold, cropped to the window. **Ask Tim
whether Y2Y already thinks in terms of specific BMAs or named linkage zones** — if they have their
own nodes, use theirs, not ours.

---

## Data shopping list

| Layer | Purpose | Where | Status |
|---|---|---|---|
| **Grizzly RSF / habitat / density** | driver + validation | AB Grizzly Recovery Plan BMAs, fRI Research, ACA | **Ethan sourcing** |
| **AB highway centrelines + class** | barrier | GoA Open Data / Alberta Transportation; OSM fallback | not started (easy) |
| **AADT traffic volume** | barrier weighting + Jordan's threat list | Alberta Transportation | not started (moderate) |
| **Wildlife crossing structures** | validation + gap map | **Ethan has this** | contents unknown — see below |
| **WVC / mortality points** | Jordan's exception clause | maybe in the above; else AB Transportation / Parks Canada | unknown |
| **Land tenure (Green/White, freehold)** | protect vs permeate | AB Open Data | not started (easy) |

**Open question on the crossings data — Phase 5 branches hard on this.** Which is it?
- **Structure inventory** (locations/type/dimensions of over- and underpasses) → validation + gap map
- **WVC / mortality records** (point collisions, species, date) → hotspot analysis, Jordan's exception
- **Monitoring/telemetry** (camera or track counts at structures, GPS collar crossings) → best case;
  allows *calibrating* resistance rather than assuming it

Also: does it cover AB highways 1, 3, 11, 16, 40, 93, 22? Does it carry AADT?

---

## Jordan's longer-term list — triage

| Idea | Assessment |
|---|---|
| **PA/IPCA connectivity** ("don't create disconnected islands") | **Nearly free** — literally what 05 does; add new IPCAs as nodes |
| **Current/future development threats** (Calgary sprawl, traffic growth, mining leases, rare earth, data centres) | Architecturally clean — this is a **cost surface**, replacing `cost_uniform=1` in 03c. Real data lift; pairs with Phase 6 |
| **Aquatic connectivity** | Needs hydrography + barrier/culvert data. A real new workstream, but scoped and bounded |
| **Bison reintroduction** | Park — horizon-scanning, politically fraught, no analysis we can ground today |
| **Data centres** | Park — too emergent for a data layer |

---

## Appendix — Jordan's guidance, verbatim (received ~2026-08-05)

> Circling back to this (and with caveat that Tim Johnson will likely have additional helpful
> insights as he is more familiar with the Eastern Slopes- please feel free to contact him).
>
> -#1 factor for us is where grizzly bears are moving and ensuring protection (for private lands)
> and permeability (mostly across highways, but we also consider what's happening on public lands
> such as Crown lands that might impact bear movements - such as mining).   Under our current
> program objectives, if grizzly bears aren't moving there, or trying to move there but unable to,
> it's not really a priority for us.   Easten slopes have always been a bit on the fringe for us
> given this focus....
>
> -There may be exceptions to that, such as crucial hot spots where multiple species (like
> ungulates) are getting hit on highways.....and by engaging in crossings work in those hotspots we
> better strengthen enabling conditions for the crossings/permeability we need for grizzlies over
> the long run.......but we do and will scrutinize those opportunities and be very selective on
> if/how we engage
>
> -over the longer term- ie beyond our current 2030 objectives- and where this analysis could help
> us gain a better understanding of conditions to inform future decision-making, we may consider
> factors such as:
> Connectivity between Protected Areas, such as newly established IPCAs.......not sure how much we
> would prioritize investing in structural connectivity between IPCAs in the future but it would be
> interesting to look at the connectivity factors of any new Pas/IPCAs- whether structural or
> functional.......as we don't want to be creating P.A.s that are disconnected islands
> Aquatic connectivity......total new frontier for us but something that will be increasingly
> important for us to weigh........so some basic analysis or understanding of the "lay of the land"
> in this area could be useful
> Bison reintroduction and future connectivity-  also a new frontier, and politically fraught
> (especially with ranching communities) but something we are curious about across multiple programs
> Current and future development threats -  projected growth/development from Calgary (ie urban
> sprawl and conversion/sub-division of grassland/Eastern slopes), projections of increased in
> traffic volume on highways,  mining leases, presence of rare earth mining opportunities, data
> center potential (i realize this is emerging but its doing so quickly)
>
> Pretty "spitball" ideas but hopefully of some value- happy to clarify further if useful.
