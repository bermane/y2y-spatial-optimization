# PATCH — the land-aware "only viable connection" rule (D23), with the route sense (D12) folded in.
Splice into `spec/05_corridors_v2_addendum_run_and_alternatives.md` (§1, §2, §4, §6) and
`spec/06_corridors_north_director_package_spec.md` (§3 legend strings, changelog); do not
regenerate either. Update `spec/methods_log.md` (M4.8 already opened by Claude Code) and
`CLAUDE.md` in the same session. Naming rule applies: things named, codes in parentheses.

---

## 05 → Changelog (prepend)

- 2026-09-28 — **land-aware top class (D23).** "Only viable connection" now requires all
  three: no alternative link (D7), one route branch (D12), and band width below its
  barrier-free width (D17, ratio < `squeeze_ratio`). The route sense (D12) is **redefined**
  to include the width condition, so a single wide branch is no longer called
  route-irreplaceable anywhere. One threshold only: the existing `squeeze_ratio` (0.5). Full
  eight-cell precedence table added (§6). Adoption gated on the run002 eight-cell count table
  (the eight-cell adoption check, G18): if the four pinned only-viable links all already
  satisfy the width condition, this is documentation for run002 and a safeguard for run003;
  if not, the example-regeneration rule in 06 fires and is logged. Raised by the part-3
  bridge case; adopted on the general argument (a leaf's only tree edge is its cheapest edge
  by the cut property, so the edge flag measures isolation, not land; one wide lens is one
  branch, so the branch flag measures topology, not land). M4.8; R10.

## 05 → §1 decision table (append D23; amend the D12 row as noted)

| # | Decision | Rationale |
|---|---|---|
| D12 (amended 2026-09-28) | **Route-irreplaceable** = `n_branches == 1` **and** `squeeze_ratio_obs < squeeze_ratio`. The branch decomposition itself is unchanged; only the flag's definition changes. `route_irreplaceable_topo` (the old one-branch-only flag) is retained as a column for continuity with run001/run002 tables. | A single branch across a wide lens has no distinct alternative swath but abundant alternative land; calling it irreplaceable was a topology statement mistaken for a scarcity statement. With width folded in, the flag means "one route, and that route is already constrained," which is what a reader takes "no alternative route" to mean. |
| D23 | **Only viable connection** = edge-irreplaceable (D7) **and** route-irreplaceable as amended (D12: one branch and narrow). Equivalently: no alternative link, one branch, ratio < `squeeze_ratio`. No new constant. Precedence for every combination is fixed in §6 and is the single source for map classes, legend counts, and both alternatives tables. | The two existing senses can both fire on the least constrained land in the sector (remote leaf, open ground). The counterfactual width (D17) is the only measure of movement-land scarcity in the pipeline, so it is the missing condition. Folding it into the route sense rather than adding a third clause keeps the two-sense framing in the reporting rules intact and makes the route flag meaningful on its own. |

## 05 → §2 constants (no new keys)

`squeeze_ratio` = 0.5 is the only width threshold. **`resolve()` raises if any second
width/ratio key appears** (e.g. `only_viable_ratio`, `route_width_thresh`) — same doctrine as
the retired resistance keys (the no-dead-flags rule, D2).

## 05 → §4 gates (append)

| gate | invariant | where |
|---|---|---|
| G18 (eight-cell adoption check) | On run002 (pinned) and on every later baseline: the count table over edge-irreplaceable × one-branch × narrow (8 cells) is written to `class_truth_table.csv` and reported before class rasters are drawn. Class counts on the map must equal the table's row sums under the §6 precedence. **Adoption condition for run002:** the four links currently classed only-viable all sit in the (E, B1, S) cell — if any does not, the 06 example-regeneration rule fires and the change is logged as a post-pin class change, not silently absorbed. `squeeze_ratio_obs` must be non-null for every non-zero-cost edge, or the gate fails. | step 2, before any figure |

## 05 → §6 reporting rules (append; this table replaces the implicit precedence in the "four classes are derived, disjoint" line)

Precedence — one row per combination; E = no alternative link within β (D7), B1 = one
branch (D12 decomposition), S = width ratio < `squeeze_ratio` (D17). Applied top-down; first
match wins.

| E | B1 | S | class (director string) | route-irreplaceable (amended D12) | note |
|---|---|---|---|---|---|
| ✓ | ✓ | ✓ | only viable connection | ✓ | the top class; all three senses |
| ✓ | ✓ | ✗ | last affordable link | ✗ | one wide branch — a leaf across intact land lands here |
| ✓ | ✗ | ✓ | last affordable link | ✗ | alternatives within the band exist; land narrow — width shows in the table |
| ✓ | ✗ | ✗ | last affordable link | ✗ | |
| ✗ | ✓ | ✓ | already narrowing | ✓ | route-irreplaceable but a backup link exists; the flag shows in the table, not the map |
| ✗ | ✗ | ✓ | already narrowing | ✗ | |
| ✗ | ✓ | ✗ | corridor land with options | ✗ | one wide lens |
| ✗ | ✗ | ✗ | corridor land with options | ✗ | |

- The two irreplaceability senses are still reported together in the tables (edge flag,
  amended route flag, and the retained topology-only route flag) and never merged; the map
  shows the class, the tables show the flags.
- Provenance line for the methods text: the top-class rule was changed on 2026-09-28 after the
  part-3 bridge case exposed that neither existing sense measured land; adopted on the general
  argument and checked against the pinned run (G18) so it was not tuned to the case.

---

## 06 → §3 legend strings (replace one; note on a second)

- only viable connection → **"Only viable connection — no alternative link or route, and the
  land is already narrowing"**
- last affordable link → wording unchanged; its count will absorb any wide-lens leaves. The T1
  "Room to move" column already shows "single route" vs "N route options", so a
  last-affordable link with one wide branch reads correctly there.

## 06 → changelog (prepend)

- v1.2.10 (2026-09-28) — land-aware top class (05 D23; route sense D12 amended). Legend
  string for the top class updated. **Pinned examples hold only if the run002 eight-cell
  check (G18) passes**; otherwise S1–S3 are regenerated per the pin rule and the change is
  recorded here as a post-pin class change. Caption footnote on M1/M3 gains one clause: the
  top class also requires the corridor to be below its barrier-free width.
