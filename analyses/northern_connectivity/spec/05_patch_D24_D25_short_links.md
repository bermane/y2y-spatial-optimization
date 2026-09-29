# PATCH — short-link rules: the width-test resolution floor (D24) and the near-contiguous
link class (D25). Splice into `spec/05_corridors_v2_addendum_run_and_alternatives.md`
(§1, §2, §4, §6) and `spec/06_corridors_north_director_package_spec.md` (§3 legend,
changelog); do not regenerate. Companion to the land-aware top-class patch (D23) — apply
after it. Both rules are generic to the engine, so they apply to the northern IPCA network and
to every derived analysis (wolverine refugia) from the same code path; a derived analysis may
tighten a constant, never loosen one. Naming rule applies: things named, codes in parentheses.

---

## 05 → Changelog (prepend)

- 2026-09-28 — **short-link rules (D24, D25).** Raised by the wolverine refugia network
  (133 of 170 links one-branch at half cutoff) but baked into the northern engine because
  the failure is geometric, not network-specific. (D24) the width test (D17) is declared
  *not assessable* below a resolution floor in cells; such links are classed from the edge
  sense (D7) alone and flagged in the tables. (D25) links whose least-cost path is shorter
  than their barrier-free width are a **near-contiguous** class — no corridor to design
  unless a barrier intervenes — classed by the edge sense and the barrier-crossing flag
  only. Precedence table (§6) extended to eleven rows. Gate on the floor's effect (G19). Both
  constants pre-registered; tuning them to a class count is prohibited (§2). M4.9; R10.

## 05 → §1 decision table (append)

| # | Decision | Rationale |
|---|---|---|
| D24 | **Width-test resolution floor.** The squeeze test (D17) and therefore the amended route flag (D12) are evaluated only when `open_ground_width_med ≥ width_floor_cells` **and** `lcp_len_cells ≥ len_floor_cells`. Otherwise `width_not_assessable = True`, `squeezed = False`, `route_irreplaceable = False`, and the link is classed from the edge sense (D7) alone (§6). The unassessable count and the affected links are reported in `corridor_edges.csv` and in the run report. | A ratio of two small integers at 300 m is rasterisation noise: three cells against six is 0.5 with one cell of margin. Without a floor the "already narrowing" class fills with short links for numerical reasons. Declaring the test unassessable is honest; declaring such links narrowing or only-viable is not. |
| D25 | **Near-contiguous link class.** A non-zero-cost edge with `lcp_len_cells < open_ground_width_med` (path shorter than the band's barrier-free width) is `near_contiguous`. It is not a corridor-design object: no branch decomposition, no width class. It is reported with the edge sense (D7) and `crosses_cost_1000` (barrier between the two areas on the least-cost path). Director class: **"adjacent — no corridor needed"** when no barrier intervenes; **"adjacent — barrier between"** when one does. Both are drawn as the link's band in a neutral hatch, never as one of the four corridor classes; counts appear in the legend. Zero-cost adjacency (§7) is unchanged and remains a separate, earlier rule. | When the gap between two areas is smaller than the natural width of the near-optimal set, the band is a blob, not a route; "branch" and "narrowing" describe nothing. The information that matters for such a pair is whether anything stands between them and whether the link is the only one. Nodes a few kilometres apart are the norm in refugia networks and occur in the north wherever proposals abut existing parks. |

## 05 → §2 constants (append)

| key | value | note |
|---|---|---|
| `width_floor_cells` | `8` | D24; counterfactual median width below which the width test is unassessable |
| `len_floor_cells` | `10` | D24; least-cost-path length below which the width test is unassessable |
| `near_contiguous` | `{"rule": "lcp_len_cells < open_ground_width_med"}` | D25; no free parameter — the test is relative |

**Tuning prohibition.** The two floor constants are pre-registered here and recorded in
`run_config.json` before the eight-cell table (G18) or the floor-effect report (G19) is read
for the run in question. Changing either after reading a class count is a post-hoc
calibration and is not permitted; a derived analysis may raise a floor (stricter) with a
logged reason, never lower one. The near-contiguous rule has no constant by design.

## 05 → §4 gates (append)

| gate | invariant | where |
|---|---|---|
| G19 (floor effect) | For every baseline: report the histogram of `lcp_len_cells` and `open_ground_width_med` (cells) across non-zero-cost edges, the number of links `width_not_assessable`, the number `near_contiguous`, and — as a diagnostic only — how the class counts would differ with the floor halved and doubled. Assert: every `near_contiguous` link has `n_branches` unset (decomposition skipped) and no corridor class; every `width_not_assessable` link has `squeezed == False`; the four-class counts in the legend equal the §6 row sums. If the halved/doubled floors move more than 10 % of links between classes, the report says so and the floor is discussed, **not changed**, for that run. | step 2, with G18, before any figure |

## 05 → §6 reporting rules (extend the precedence table; first match wins, top-down)

Add before the eight-cell block:

| condition | class (director string) | notes |
|---|---|---|
| zero-cost adjacency (§7) | *not a link on the map* | unchanged |
| `near_contiguous` and E and `crosses_cost_1000` | adjacent — barrier between | edge-irreplaceable and a barrier: the only case in this class that asks for action; reported with the barrier's cost class |
| `near_contiguous` and `crosses_cost_1000` | adjacent — barrier between | |
| `near_contiguous` | adjacent — no corridor needed | |

Then, for the remaining links, the D24 gate on the eight-cell table:

| condition | class | notes |
|---|---|---|
| `width_not_assessable` and E | last affordable link | edge sense only; table shows `width_not_assessable` |
| `width_not_assessable` | corridor land with options | edge sense only |
| otherwise | the eight-cell table from D23 | unchanged |

- The methods text states that three link classes are decided by geometry before any
  corridor class is assigned: touching (zero-cost), near-contiguous, and too short for the
  width test. It gives the counts for each on the run in question.
- For a derived analysis (wolverine): the same table and constants apply; the report states
  how many of the links fell to each geometric class, because on a dense refugia network that
  is most of the answer to "why so few corridors on the map".

---

## 06 → §3 legend strings (add two; palette addition to `mapstyle.py`)

- near-contiguous, no barrier → **"Adjacent areas — no corridor needed"**
- near-contiguous, barrier → **"Adjacent areas — barrier between them"**
- Symbol: the link's band in `#D9D9D9` with a diagonal hatch `\\\\` in `#8A8A8A`, no
  fill hue; the barrier variant adds a `#8A8A8A` 0.6 pt outline. Neutral by design — these
  are not corridor priorities and must not read as a fifth and sixth corridor class.
- Legend order: four corridor classes, then the two adjacent rows, then PA, IPCA, lines.

## 06 → changelog (prepend)

- v1.2.11 (2026-09-28) — short-link rules (05 D24, D25). Two neutral "adjacent areas" legend
  rows added; `mapstyle.py` gains the hatch symbol. Pinned examples: unaffected unless the
  floor-effect gate (G19) on run002 reclassifies any of S1–S4, in which case the pin rule
  fires and it is logged. Map 02 of the wolverine analysis inherits both rules and its
  legend; its report leads with the geometric-class counts.
