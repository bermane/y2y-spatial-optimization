# PATCH — fronts are corridor land (D25c): the near-contiguous class is retired; front/strip
becomes a geometry descriptor and every non-touching link is classed on one pressure scale.
Supersedes the sub-classes (D25a) and amends the area accounting (D25b). Splice into
`spec/05_corridors_v2_addendum_run_and_alternatives.md` (§1, §4, §6) and
`spec/06_corridors_north_director_package_spec.md` (§2, §3, changelog); do not regenerate.
Naming rule applies: things named, codes in parentheses.

**Principle (Ethan, 2026-09-29, binding):** nothing that is not protected is taken as given.
Land between two areas is corridor land whatever its shape; a wide front means the corridor
has room, not that it does not exist. The only links with no corridor are touching pairs
(zero-cost adjacency, §7).

---

## 05 → Changelog (prepend)

- 2026-09-29 — **fronts are corridor land (D25c).** The "adjacent — no corridor needed"
  framing (D25, D25a) made a land claim the analysis cannot support and is retired. The
  front trigger is kept as a geometry descriptor (`link_geometry` ∈ {strip, front, contact});
  every strip and front is classed on the single pressure scale of the land-aware rule
  (D23), with the route sense reduced to width alone on fronts (no branches to count on a
  one-component front). Perpendicular road crossings are flagged, not classed (consistent
  with strips). Corridor area includes fronts again; front share is a descriptor (D25b
  amended). Example rules: contacts excluded from candidacy; northern slots by room (width),
  not branch count. Pre-D23 run002 products frozen. Gate G24. M4.12; R10.

## 05 → §1 decision table (append; D25 and D25a rows marked SUPERSEDED by D25c)

| # | Decision | Rationale |
|---|---|---|
| D25c | **Geometry descriptor, one pressure scale.** For every non-zero-cost edge set `link_geometry`: `contact` if `width_not_assessable` (D24 floor); `front` if `lcp_len_cells < open_ground_width_med` (the retired D25 trigger); `strip` otherwise. Then class **every strip and front** by the land-aware table (D23) with one substitution: on a `front`, the branch term B1 is **fixed true** (a front is one component by construction; `n_branches` is written null and the decomposition is skipped), so the route sense is the width ratio alone. `contact` links are classed from the edge sense only, as before. `lcp_max_cost` (maximum cost class on the least-cost path) is reported for every link and drives a `road_crossing` flag (`== 10`) used in tables and profiles, **never in the class**. | The near-contiguous class removed unprotected land from the corridor framework on the strength of its shape. Width is the measure of land scarcity the framework already uses; on a front it is the whole route sense, so no new scale is needed and fronts and strips rank on the same number. A road along a gap narrows the front and raises the class; a road across it does not change which routes are viable and is a crossing-structure question — the same treatment strips get. |
| D25b (amended) | `corridor_area_km2` **includes** fronts. `front_area_km2` and `front_share` are descriptor columns. The four-way identity (corridor + intra-name + augmentation = total band) is restored; the calibrated cutoff (D6) is unchanged. | Fronts are corridor land; excluding them understated the corridor estate and detached the area figure from the calibration set. |

## 05 → §4 gates (append; G23 retired with D25a)

| gate | invariant | where |
|---|---|---|
| G24 (one scale) | Every non-zero-cost edge has exactly one `link_geometry` and exactly one of the four classes (contacts: options or last-affordable only). Every `front` has `n_branches` null and B1 recorded as forced; every `strip` has a computed `n_branches`. Class counts on the map equal the eight-cell table (G18) row sums with fronts folded in under B1 = true. `road_crossing` never changes a class (assert class invariant under toggling the flag). Corridor-area identity holds. The run report gives class × geometry as a 4 × 3 table. | step 2, before any figure |

## 05 → §6 reporting rules (replace the near-contiguous precedence rows)

| condition | class | notes |
|---|---|---|
| zero-cost adjacency (§7) | *not a link on the map* | the only "no corridor" case |
| `contact` and E | last affordable link | edge sense only; `width_not_assessable` shown |
| `contact` | corridor land with options | |
| `front` or `strip` | the eight-cell table (D23), B1 := true on fronts | fronts: route sense = width alone |

- The methods text states the principle in one sentence — no unprotected land is treated as
  secured — and explains that a front is classed on width because it has no branches.
- Profiles for fronts say "wide front between the areas — N km of room" (open) or "front cut
  along its length — at X of its natural width" (narrowing), and carry the road-crossing flag
  as a separate sentence when set.
- The route flag (amended D12) is reported for fronts as the width condition alone, and the
  table footnote says so.

---

## 06 → §2 example selection

- **Candidacy:** `contact` links are never examples (table rows only).
- **N2–N3 (room to choose):** links in "corridor land with options" ranked by **actual band
  width** (`width_new_km`, the room the land offers), ties by ensemble attribution, then the
  multi-jurisdiction tie-break. Fronts are eligible and expected to lead (T'akú Tlatsini ↔
  Stikine / Mount Edziza). The two-branch link (Tsey Dëk ↔ Tintina Trench) is kept as a
  separate "two routes" example, not an N slot.
- **S1–S3:** unchanged (top class, then last-affordable, by width ratio); fronts eligible.
- All regenerations logged under the pin rule; the report's run003 picks are re-drawn under
  this rule before the deck is touched.

## 06 → §3 legend

- **Four corridor rows only**; the adjacent-areas rows are removed. Fronts are drawn in their
  class colour like any corridor; optionally a `#8A8A8A` 0.4 pt dotted outline marks fronts
  on M2 (Act 1) where the room story is told — a display choice, not a class.
- Corridor-area figures in T1/T2 and captions include fronts; the caption gives the front
  share once.

## 06 → changelog (prepend)

- v1.2.14 (2026-09-29) — fronts are corridor land (05 D25c). Adjacent-areas legend rows
  removed; fronts classed and coloured on the common pressure scale; N-slot rule by width;
  contacts excluded from candidacy; corridor-area figures include fronts. Pre-D23 run002
  director products frozen in `v2_run002/director_package/_preD23_frozen/` and referenced
  from this changelog; the live directory is the pinned run's post-pin state.
