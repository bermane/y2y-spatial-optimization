# PATCH — geometry-vs-ecology audit, run003 (D26–D31). Splice into
`spec/05_corridors_v2_addendum_run_and_alternatives.md` (§1, §2, §4, §6) and
`spec/06_corridors_north_director_package_spec.md` (§2 example selection, changelog); do not
regenerate. Apply after the land-aware top class (D23) and the short-link rules (D24, D25).
Every rule below is engine-generic and inherited by derived analyses (wolverine). The
zero-cost adjacency vector check was considered and **not adopted** (§7). Naming rule
applies: things named, codes in parentheses.

---

## 05 → Changelog (prepend)

- 2026-09-28 — **geometry-vs-ecology audit for run003 (D26–D31).** Rules whose result was
  driven by link length, node position, or raster resolution rather than land: (D26) the
  branch-sliver floor becomes relative to band area; (D27) locked intra-name links are
  ineligible for the irreplaceable classes until the alternative-link test (D7) is run against
  the full candidate set; (D28) a tenth-percentile width ratio joins the median so a single
  pinch is visible in the table; (D29) the alternative link's cost is decomposed into length
  and mean resistance; (D30) near-optimality tiers use fixed cost-unit breaks instead of
  area-weighted percentiles; (D31) the calibrated cutoff is also stated as detour distance on
  open ground, which is the calibration rule for derived analyses. Example selection in 06
  changed to class-and-width-first with criticality as tie-break. Gates G20–G22. Zero-cost
  adjacency vector check declined (§7). M4.10; R10.

## 05 → §1 decision table (append)

| # | Decision | Rationale |
|---|---|---|
| D26 | **Relative branch-sliver floor.** A band component at `cutoff_branch` is kept as a branch if its area ≥ `branch_min_frac` × (the link's band area at `cutoff_branch`) **and** ≥ `branch_min_cells`. `branch_min_km2` is retired; `resolve()` raises if it appears. Dropped-component count and the largest dropped fraction are reported per link. | A fixed 10 km² is noise on a 200 km link and a real second route on a 30 km one, so branch counts were length-biased. On open ground the band is one ellipse, so any second component is a barrier signal and the floor should protect it, not swallow it at short lengths. |
| D27 | **Locked intra-name links are class-ineligible until tested.** Every locked link (D16) carries `locked = True`. The alternative-link test (D7) is run for it against the full candidate set, including routes via other names; `edge_irreplaceable` is set only if that passes. Until run and passed, locked links are classed "corridor land with options" at most and never "last affordable link" or "only viable connection". The table shows `locked` and `alt_test_run`. | A locked link never competed in the tree, so an irreplaceability class on it is a management assertion presented as a finding. Running the test makes it a finding or removes the class. |
| D28 | **Pinch-aware width column.** Alongside `squeeze_ratio_obs` (median cross-section ratio, D17), report `width_ratio_p10` = tenth-percentile cross-section on the actual band ÷ the counterfactual's cross-section at the same positions along the path, and `pinch_pos` = fractional path position of the minimum. **Reported, not classed**; the squeezed class stays on the median. Subject to the resolution floor (D24). | The median cannot see a single constriction, which is the ecologically important case (Pinto & Keitt's merge point). This is the geometric half of the deferred pinch-point comparison (D20), computed for free from the existing cross-sections, so the circuit-based half has something to compare against when it runs. |
| D29 | **Alternative-link cost decomposed.** For every edge, the cheapest alternative link used by the β test (D7) is reported as `alt_cost`, `alt_len_km` (least-cost path length), `alt_mean_res` (= `alt_cost` / cells), and `alt_kind` ∈ {far, hard, both}: *far* if `alt_len_km / lcp_len_km ≥ β` with `alt_mean_res` within 1.5× the edge's own; *hard* if the length ratio is below β but the cost ratio is not; *both* otherwise. | "Alternatives cost far more" conflates distance and resistance. In the north, where resistance is nearly uniform, edge-irreplaceability is mostly node spacing; the profile text needs to be able to say "isolated" rather than "walled in". Legend string unchanged; the distinction lives in the table and the one-pagers. |
| D30 | **Fixed-break near-optimality tiers.** `near_opt_tiers` becomes fixed slack breaks in cost units: robust core ≤ `cwd_cutoff_abs`/6, frequent ≤ `cwd_cutoff_abs`/2, occasional ≤ `cwd_cutoff_abs` (the band). Percentile tiers retired. Appendix product only (unchanged). | Percentiles of slack over the union band are area-weighted, and area is dominated by the long northern links, so the breaks were set by the north. Raw slack is comparable across links; fixed breaks keep it so. Fractions of the calibrated cutoff keep the tiers consistent across the cutoff sweep (axis B). |
| D31 | **Cutoff stated as detour distance; calibration rule for derived analyses.** `run_config.json` and every caption that mentions the cutoff also carry `cutoff_detour_km` = `cwd_cutoff_abs` × cell size on cost-1 ground (13.6 units × 0.3 km ≈ 4.1 km on run002). The northern network keeps the v1 area calibration (D6) for comparability. **A derived analysis with no v1 target calibrates by detour distance**, choosing `cutoff_detour_km` and deriving the cost cutoff from it; it never calibrates by area or by class counts. | An area target is dominated by the long links and means nothing to a reader; "routes within about four kilometres of extra travel on open ground" does. It is also the only defensible way to set a cutoff where there is no prior area to match. |

## 05 → §2 constants (append / retire)

| key | value | note |
|---|---|---|
| `branch_min_frac` | `0.05` | D26; fraction of the link's band area at `cutoff_branch` |
| `branch_min_cells` | `20` | D26; absolute noise floor (≈ 1.8 km² at 300 m) |
| `branch_min_km2` | **retired** | D26; `resolve()` raises on presence |
| `alt_res_tol` | `1.5` | D29; resistance ratio within which an alternative is "far", not "hard" |
| `near_opt_tiers` | `{"robust_core": "cutoff/6", "frequent": "cutoff/2", "occasional": "cutoff"}` | D30; replaces the percentile spec |
| `cutoff_detour_km` | derived, written by `resolve()` | D31; northern: derived from `cwd_cutoff_abs`; derived analyses: set, and `cwd_cutoff_abs` derived from it |

Tuning prohibition from the short-link patch (D24) extends to `branch_min_frac`,
`branch_min_cells`, and `alt_res_tol`: pre-registered before any class count for the run is
read; a derived analysis may tighten, never loosen.

## 05 → §4 gates (append)

| gate | invariant | where |
|---|---|---|
| G20 (locked-link eligibility) | No link with `locked = True` carries `edge_irreplaceable = True` unless `alt_test_run = True`; every locked link with `alt_test_run = True` has a non-null `alt_cost`. Class counts in the legend reflect this. | step 2 |
| G21 (branch floor effect) | Per baseline: distribution of dropped-component fraction; number of links whose `n_branches` changes between the retired fixed floor and the relative floor, listed. Assert every kept branch satisfies both minima. | step 4b, with G19 |
| G22 (tier and cutoff consistency) | `width_ratio_p10 ≤ squeeze_ratio_obs` for every assessable edge; tier classes monotone in slack with breaks exactly at cutoff/6, cutoff/2, cutoff; `cutoff_detour_km` × cell size reproduces `cwd_cutoff_abs` to float tolerance. | step 4a |

## 05 → §6 reporting rules (append)

- Locked intra-name links (D27) are drawn with the class they earned after the alternative
  test, never the class they would have had without it; the profile for any locked link says
  it was locked and tested.
- Where an irreplaceable class appears in a profile, the text names the alternative's kind
  (D29): "the next link is far" versus "the next link crosses hard ground"; on the northern
  network most will be *far*, and the deck says so once.
- The cutoff is described in captions as detour distance (D31), with the cost-unit value in
  the methods note only.
- Tier maps in the appendix carry the fixed breaks in the legend (D30), not percentiles.

---

## 06 → §2 example selection (replace the S1–S3 rule)

- **S1–S3:** links in the top class ("only viable connection", D23), ranked by
  `squeeze_ratio_obs` ascending (most constrained first); ties by `width_ratio_p10`, then by
  criticality. If fewer than three links are in the top class after run003, fill from "last
  affordable link" ranked by `width_ratio_p10` ascending, and say in the profile which class
  each is. Criticality is no longer the primary key: on a spine-shaped network it ranks
  mid-chain links by graph position, not by how little room the land leaves.
- **N2–N3:** unchanged rule (branch count × attribution, jurisdiction tie-break), but with
  branch count from the relative floor (D26).
- Regeneration of the pinned slots is expected in run003 and is logged as such — the pin
  rule (v1.2.4) applies to the new picks from the moment they are signed.

## 06 → changelog (prepend)

- v1.2.12 (2026-09-28) — geometry-vs-ecology audit (05 D26–D31). Example selection for
  the southern slots is now class-and-width-first with criticality as tie-break; expect
  regeneration on run003. Profiles gain the alternative-kind sentence (D29) and, for locked
  links, the locked-and-tested line (D27). Captions state the cutoff as detour distance
  (D31). Appendix tier maps show fixed cost-unit breaks (D30).

---

## 7. Considered and not adopted — zero-cost adjacency vector check

A pair recorded as touching at 300 m could be separated by a road narrower than a cell. A
vector intersection of the shared boundary against the source road, rail, and hydro layers
would catch it and demote the pair to "adjacent — barrier between" (D25). **Declined for
run003** (Ethan, 2026-09-28): the northern handoff verified that the cost-10 linear class
survives the 300 m warp as genuine linear features, and no touching pair in the current
node set is known to straddle a highway. Logged so the omission is visible; revisit if a
derived analysis has finer-grained nodes or a denser road network.
