# PATCH — near-contiguous sub-classes (D25a) and near-contiguous area accounting (D25b).
Amends the near-contiguous link class (D25) after its first application on run002 (18 of 45
non-zero-cost links). Splice into `spec/05_corridors_v2_addendum_run_and_alternatives.md`
(§1, §4, §6) and `spec/06_corridors_north_director_package_spec.md` (§2, §3, changelog); do
not regenerate. The trigger in D25 is unchanged; only its sub-classes and its accounting change.
Naming rule applies: things named, codes in parentheses.

---

## 05 → Changelog (prepend)

- 2026-09-28 — **near-contiguous sub-classes (D25a) and area accounting (D25b).** Run002
  classed 18 of 45 non-zero-cost links near-contiguous under the D25 trigger. The count is
  correct: between two large facing areas the barrier-free near-optimal set is a front
  spanning the facing perimeters, not an ellipse, so its median width exceeds the gap by a
  wide margin. Two defects in D25 as written are fixed. (D25a) The barrier variant keyed on
  cost-1000 only; roads and cuts are cost 10 in this surface, so a highway along the gap did
  not register. Sub-classes are now decided by the actual band's width ratio (D17, assessable
  because the front is wide) and the maximum cost class on the least-cost path. (D25b)
  Near-contiguous band area is reported separately from corridor area; the calibrated cutoff
  (D6) is **not** recalibrated. Gate G23. Northern example slots N2–N3 re-checked against the
  pin rule. M4.11; R10.

## 05 → §1 decision table (append; D25 trigger row unchanged)

| # | Decision | Rationale |
|---|---|---|
| D25a | **Near-contiguous sub-classes.** For every `near_contiguous` link (trigger: `lcp_len_cells < open_ground_width_med`, D25), compute `squeeze_ratio_obs` (D17) as usual — the counterfactual front satisfies the resolution floor (D24) by construction — and `lcp_max_cost` = maximum cost class on the least-cost path (1, 10, 100, 1000). Sub-class, first match wins: **adjacent — barrier between** if `lcp_max_cost ≥ 100`; **adjacent — front crossed by roads or cuts** if `lcp_max_cost == 10` **or** `squeeze_ratio_obs < squeeze_ratio`; **adjacent — open front** otherwise. Branch decomposition remains skipped (no route sense on a front). The edge sense (D7) is still reported. Per link the table carries `gap_km` (= least-cost path length), `open_ground_width_med`, `squeeze_ratio_obs`, `lcp_max_cost`, and both areas' sizes. | Branches are meaningless on a front, but width is not: the ratio of the actual band to the barrier-free front says directly whether the frontage is intact or cut. Keying "barrier" on cost 1000 missed the case that matters most for abutting areas in this sector — a road along the gap — because roads are cost 10. The three sub-classes map onto three different asks: nothing to design; a crossing-structure question; a genuine separation. |
| D25b | **Near-contiguous area is not corridor area.** `corridor_area_km2` in every table and caption excludes near-contiguous bands; `near_contiguous_area_km2` is its own line. The calibrated cutoff (D6) stays as calibrated over all tree edges on run002 and is **not** recomputed with near-contiguous links excluded. | Recalibrating would move every band in the sector and break comparability across run002/run003 and with v1. Reporting the front area separately is enough to stop the deck counting fronts as corridors. The area-calibration rule's dependence on fronts is noted as a known limitation for the derived-analysis calibration by detour distance (D31), which does not have this problem. |

## 05 → §4 gates (append)

| gate | invariant | where |
|---|---|---|
| G23 (front check) | Every near-contiguous link has `open_ground_width_med ≥ width_floor_cells` (if not, the D24 floor applies first and the link is `width_not_assessable`, not near-contiguous — assert this ordering); every near-contiguous link has a non-null `squeeze_ratio_obs` and `lcp_max_cost`; sub-class counts sum to the near-contiguous count; `corridor_area_km2 + near_contiguous_area_km2 + intra_name_area_km2 + augmentation_area_km2` reproduces the total band area. Report the 18-link table (run002) with the five per-link columns from D25a. | step 2, with G19 |

## 05 → §6 reporting rules (replace the three near-contiguous precedence rows)

| condition | class (director string) | notes |
|---|---|---|
| zero-cost adjacency (§7) | *not a link on the map* | unchanged |
| `near_contiguous` and `lcp_max_cost ≥ 100` | adjacent — barrier between | water, ice or settlement on the direct path |
| `near_contiguous` and (`lcp_max_cost == 10` or `squeeze_ratio_obs < squeeze_ratio`) | adjacent — front crossed by roads or cuts | the crossing-structure case |
| `near_contiguous` | adjacent — open front | nothing to design |

- Corridor-area statements in the methods text and captions exclude near-contiguous bands
  and say so once (D25b).
- The methods text explains the front mechanism in one sentence: between two large facing
  areas the barrier-free near-optimal set spans the facing perimeters, so a short gap is
  classed adjacent rather than as a corridor.

---

## 06 → §2 example selection (add a check)

- Before any northern slot is rendered: if N2 or N3 is now near-contiguous, the pin rule
  fires and the slot is re-picked from the remaining securing links by the existing rule
  (branch count × attribution, jurisdiction tie-break). Logged either way.
- Act 1 narrative gains the count: "N of the sector's links join areas that are effectively
  adjacent; corridor design in the north is a question about the remaining M."

## 06 → §3 legend (replace the two adjacent rows with three)

- **"Adjacent areas — open front"** — band in `#D9D9D9`, hatch `\\\\` `#8A8A8A`, no outline.
- **"Adjacent areas — front crossed by roads or cuts"** — same hatch, `#8A8A8A` 0.6 pt outline.
- **"Adjacent areas — barrier between"** — same hatch, `#3A3A3A` 0.8 pt outline.
- Order: four corridor classes, then the three adjacent rows, then PA, IPCA, lines. The three
  rows are neutral by design and are never coloured as corridor priorities.

## 06 → changelog (prepend)

- v1.2.13 (2026-09-28) — near-contiguous sub-classes (05 D25a) and area accounting (D25b).
  Three adjacent-areas legend rows replace two; corridor-area figures in T1/T2 and captions
  exclude near-contiguous bands; N2–N3 re-checked against the pin rule; Act 1 narrative
  gains the adjacent-vs-corridor count.
