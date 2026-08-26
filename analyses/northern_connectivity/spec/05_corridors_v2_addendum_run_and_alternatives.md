# 05 corridors (north) — v2 addendum: production run, near-optimality surface, route-branch alternatives

> Addendum to `docs/05_methods_v2.md`. Surgical: nothing in D1–D10 or A1–A4 is reopened.
> Adds D11–D15, Phases 4b/4c, gates G9–G12, and the run sequence. Written 2026-08-21.
> Claude Code: patch `docs/05_methods_v2.md` with the new sections and append to its changelog;
> do not rewrite the existing document.

**Status:** approved in design discussion 2026-08-21. Implementation not started.

**Changelog**
- 2026-08-21 — addendum: execute the v2 production run; define the wall-to-wall near-optimality
  surface; define route-branch alternatives and the per-branch values table (same column spec
  as the Y2Y-wide alternatives table); Carroll 2018 enters as an audit column only; Phase 7
  deferred pending baseline evidence.
- 2026-08-21 — D16: multipart named areas split into parts and routed internally (locked
  intra-name MST); G0 re-baselined at name level + part count; H7 review gate added.
- 2026-08-21 — §8 file structure (`analyses/northern_connectivity/`; engines stay at repo root;
  H7 artifacts git-tracked in `audit/audit_objects/`) + §9 four-notebook run breakdown; §3
  preamble amended accordingly; three clarifications queued for the methods-doc patch (multipart
  field semantics, intra-name branches, tier domain).

---

## 0. Scope of this addendum

Three asks, mapped onto what the v2 engine actually produces:

1. **Run v2 end to end** — calibration → baseline → structured ensemble (axes B, C, D). Not yet
   executed; `cwd_cutoff_abs` is still `None`.
2. **Wall-to-wall "frequency" layer** → implemented as a **near-optimality surface** (raw slack,
   cost units). A least-cost model has no solution pool; the band *is* the closed-form
   near-optimal set and slack is its continuous degree. The ensemble member fraction is retained
   as **attribution only** and is never labelled "frequency" or "selection frequency".
3. **Cluster + alternatives table for all values** → clustering unit is the **route branch**
   (connected component of a per-edge band at a tightened cutoff), not a whole-network mask.
   One row per edge × branch; columns match the Y2Y-wide alternatives table, plus a Carroll
   2018 climate-corridor audit column.

Out of scope, unchanged: Phase 5 (no DEM, H5), ensemble axis A (H2), Phase 6 overlays beyond
the single audit column defined here, Phase 7 (see D14), Phase 8 ops package (H3). Eastern-slopes
grizzly work remains a separate unapproved plan.

---

## 1. New decisions (append to the decision log)

| # | Decision | Rationale |
|---|---|---|
| D11 | Primary wall-to-wall product is `near_optimality.tif` = `min_e slack_e` in **raw cost units**, defined on every routable cell. `linkage_priority.tif` (`max_e ecfb_e × (1 − slack_e/cutoff)`) is retained unchanged as the D9 deliverable. | Slack is defined everywhere the CWD fields are, which is what makes it wall-to-wall; raw units make the surface independent of `cwd_cutoff_abs`, which is calibrated for v1 area comparability, not for meaning. The cutoff enters only the binary band and area accounting. |
| D12 | The unit of "alternative" is the **route branch**: a connected component of an edge's band at a tightened cutoff `cutoff_branch = branch_mult × cwd_cutoff_abs`. Per edge, `n_branches = 1` ⇒ **route-irreplaceable** (no alternative routing within the link). This is distinct from, and reported alongside, the D7 β-ceiling **edge-irreplaceable** flag (no alternative link). | Band components are provably genuine i→j alternatives (see G9), so no heuristic clustering is needed. Whole-network clustering over ~49 structured members would cluster by which node was dropped — not a meaningful object. |
| D13 | The per-branch values table uses the **same column specification** as the Y2Y-wide alternatives table. Import the column spec from the existing table code; do not redefine names or normalisations here. Row unit differs (edge × branch vs solution cluster) and the caption must say so. | Side-by-side readability with the Y2Y-wide product without implying a shared estimand. |
| D14 | **Carroll 2018 (climate corridors) never enters resistance.** It is a post-hoc audit column (`carroll2018_pctl`) and the input to the Phase 8 tie-break among near-equivalent branches. **Phase 7 (velocity-modified routing) is deferred** pending the baseline + axis C results and is recorded as a claim-scope extension requiring its own justification. | Carroll 2018 is current-flow centrality — a derived flow quantity, same object type as Pither current density, rejected as a routing input by D1–D3 for circularity, pinch-point/permeability conflation, and footprint double-counting. The 05 claim scope is structural only; any climate term in resistance changes the claim. Caveats travel with the column: RCP 8.5 late-century only, shares anthropogenic signal with the cost surface. |
| D15 | Ensemble member fraction (cell in member's corridor union / members) is written as `ensemble_attribution.tif` and used for the robust-core threshold (0.9) and per-axis attribution rasters only. | ~42 of ~49 members are leave-one-out; the fraction is "share of dropped nodes that didn't matter," not a near-optimal sampling frequency. |
| D16 | **Multipart named areas are routed internally.** A named PA/IPCA whose rasterized mask has >1 8-connected component is split into **parts**; each part ≥ `part_min_km2` is its own seed/routing unit. For each multipart name, the MST over its parts (on CWD) is **locked into the backbone** before the inter-name MST is built. Parts < `part_min_km2` remain in `node_union` (area accounting) but are not seeds. Leave-one-out (axis C) drops a **name** (all parts), not a part. Calibration (`calibrate_cutoff`) uses the **inter-name MST only**; intra-name corridor area is reported separately, as augmentation area is. | Seeding all parts at CWD = 0 as one node means the model never asks how to move between them. A named area is a management unit, so connecting its parts is a defensible default — but it is an assertion about intent for multi-site designations, so the part list is reviewed by a human before the run (H7). Locked rather than competing so a part is never connected to its sibling only via a third park. |

---

## 2. Pre-registered constants (set in `config.CORRIDORS["north"]` **before** `cc.start()`)

| key | value | note |
|---|---|---|
| `calibrate_cutoff` | `{"target_km2": 18188, "edges": "mst"}` | unchanged |
| `branch_mult` | `0.5` | reuses the 0.5× axis-B member; no new CWD work |
| `branch_min_km2` | `10` | drop slivers; ~111 cells at 300 m. Report dropped count. |
| `near_opt_tiers` | percentiles **of slack** over the union band at 2× cutoff: robust_core ≤ p10, frequent ≤ p30, occasional = rest | mirrors p90/p70 on the inverted scale; defined on the 2× union so the tier domain is wall-to-wall-ish, not band-only |
| `carroll_ref` | `"routable_area"` | first pass: branch mean percentile vs routable-area percentile baseline. Matched random strips (Phase 6 method) deferred. |
| `robust_core_freq` | `0.9` | unchanged (applies to `ensemble_attribution.tif`) |
| `part_min_km2` | `25` | = node minimum; parts below this are area-only, not seeds (D16) |
| `multisite_designations` | `["Ecological Reserve", "Wildlife Management Area", "National Wildlife Area", "Migratory Bird Sanctuary"]` | step 0a rule 2; extend from the reviewed list |
| `multipart_link_km` | `10` | step 0a rule 2 exception distance |
| intra-name treatment | per name, from reviewed `multipart_review.csv` (`merge_parts` / `link_locked` / `link_competing` / `no_link`) | `link_competing` uses the D7 β ceiling against the cheapest inter-name path between the parts; `no_link` parts are independent nodes in the inter-name graph |

These go into `run_config.json` via `resolve()`. `resolve()` should raise if `branch_mult`,
`branch_min_km2`, or `near_opt_tiers` are absent (same no-dead-flags doctrine as D2).

---

## 3. Run sequence

The steps below are distributed across the four numbered notebooks in
`analyses/northern_connectivity/` (see §9 for the exact mapping; §8 for the folder layout).
Provenance is unchanged: `cc.start()` into `output_data/corridors_north/v2_run001/`, and the
engine reads only `run_config.json` thereafter.

**Step 0a — part split and multipart review (D16).** Rasterize nodes at 300 m (existing
path), label 8-connected components per name, apply `part_min_km2`. Write `node_parts.csv`
(name, part_id, area_km2, is_seed) and `node_parts.gpkg` — into
`analyses/northern_connectivity/audit/audit_objects/` (git-tracked; see §8 for why this is the
canonical home, not the run dir).

Then the analysis reviews every name with >1 seed part and writes `multipart_review.csv`, one
row per name, with a proposed treatment and the evidence for it. Evidence columns:

| column | what it carries |
|---|---|
| `designation` | from the source attribute (PAD-US/CPCAD `TYPE`/`IUCN_CAT`; IPCA tracker category). Ecological reserves, wildlife management areas with scattered sites, and marine/lake units are the designations most often deliberately multi-site. |
| `n_parts`, `part_areas_km2` | count and sizes; note largest-to-second ratio |
| `min_gap_cells` | minimum cell gap between any two parts at 300 m; < 3 cells ⇒ **rasterization split** (river, road, polygon slivers) |
| `max_euclid_km` | farthest part pair, centroid to centroid |
| `cwd_between_parts` | CWD-path cost and length between each part pair, on the O'Brien surface (cheap: parts only, not the full 42-name set) |
| `intervening_nodes` | other names whose masks the intra-name least-cost path crosses |
| `crosses_cost_1000` | whether any intra-name path traverses a cost-1000 cell |
| `proposed` | one of `merge_parts` (rasterization split — re-join into one seed), `link_locked` (default D16), `link_competing` (parts far apart or a third node intervenes — a forced link would route through or around another park), `no_link` (designation is multi-site by design, or gap is geographic — separate lake/island units) |
| `reason` | one sentence tying the proposal to the columns above |

Decision rules, applied in order and recorded in `run_config.json`:
1. `min_gap_cells < 3` → `merge_parts`.
2. designation in the multi-site-by-design list (maintained in config, starts with: Ecological
   Reserve, Wildlife Management Area, National Wildlife Area, Migratory Bird Sanctuary) →
   `no_link`, unless the parts are within 10 km and nothing intervenes, then `link_locked`.
3. any `intervening_nodes` → `link_competing` (the inter-name network already carries the
   connection; a locked intra-name edge would duplicate it).
4. otherwise → `link_locked`.

**G0 is re-baselined**: the gate becomes "name set = 42, same 3 dedupe merges" (name level,
unchanged) plus a recorded part count and the `multipart_review.csv` hash that later runs must
reproduce. **H7** is now a confirmation of the proposed column, not a from-scratch review:
the human edits `proposed` where the rules get it wrong, and the edited file is the input to
step 1. The run does not proceed to CWD until the file carries a `reviewed_by` line.
`multipart_review.csv` lives beside `node_parts.csv` in `audit/audit_objects/` (git-tracked —
the reproduce-this-hash requirement cannot be met by a file in gitignored `output_data/`);
`cc.start()` copies both into the run dir for self-containment and records their sha256 in
`run_config.json`, preserving the run-dir-is-the-only-record doctrine.

**Step 0 — preconditions.** G0 (as re-baselined), G2, G8 re-assert on current disk state. Confirm CWD cache
directory keyed by the O'Brien surface hash is present or will be built. H1 (licence/provenance
sign-off on the O'Brien surface) is a human task and does **not** block the run; it blocks
external release of outputs.

**Step 1 — calibrate.** CWD fields computed per **seed part** (cache keyed by resistance hash
+ part mask hash). Intra-name MSTs built and locked (D16). `calibrate_cutoff` on the
**inter-name MST edges only**, `& ~node_union`, target 18,188 km². Write `cwd_cutoff_abs`
into `run_config.json`. Record the calibrated value and the achieved area (expect exact or
within one cell-area of target; report the residual). Inter-name distance between two
multipart names = min over part pairs (standard multi-seed semantics; state it).

**Step 2 — baseline.** Locked intra-name edges + inter-name MST + bridge-backup augmentation
(β = 2.5), quotient-graph centrality, criticality, bands at `cwd_cutoff_abs`,
`linkage_priority.tif`, `edge_owner.tif`, audit, maps. Locked edges carry `edge_class =
"intra_name"` in `corridor_edges.csv`, are included in criticality and failure enumeration
(they are real corridor land), and their band area is reported as a separate line from MST
and augmentation area. G3, G4, G5 run here; G4 ("β = 0 reproduces the MST") is read as
"reproduces locked + inter-name MST".

**Step 3 — ensemble.** Axes B {0.5, 1, 2}×, C (42 leave-one-out **by name**, all parts
dropped together — including `no_link` parts, which are independent in the graph but share
the name's realisation risk), D β {1.5, 2.5, 4.0}. G7 on the drop-nothing member. Serial, memmap-backed, one CWD set (unchanged). Write
`ensemble_attribution.tif` + per-axis attribution rasters (D15).

**Step 4a — near-optimality surface (D11).** For every routable cell,
`near_optimality = min over baseline edges e of (CWD_i + CWD_j − min_e)`. Zero-cost adjacency
edges contribute nothing (no CWD band, consistent with §7). Stream edge by edge from the
memmaps; keep a running minimum and an `near_opt_owner.tif` (argmin edge). Tier with
`near_opt_tiers` → `near_optimality_class.tif`. G10 here.

**Step 4b — route branches (D12).** Per non-zero-cost baseline edge (MST + augmentation):
1. Band at `cutoff_branch` **including node cells** (do not subtract `node_union` yet).
2. 8-connected components.
3. G9: assert every component intersects **both** endpoint node masks. Property: a band cell c
   has slack(c) ≤ cutoff, and every cell on the least-cost i→c→j path has slack ≤ slack(c), so
   each component is connected to both endpoints inside the band. A failing assert means a
   masking or seed-handling bug, not a legitimate outcome.
4. Subtract `node_union`; drop components < `branch_min_km2` (count reported); label
   remaining `branch_id = {edge_id}_{k}` ordered by min slack.
5. Per branch: `area_km2`, `min_slack`, `mean_slack`, `cells`, `bbox`, and a length proxy
   (major-axis length of the component; state it is a proxy, not a path length).
6. Per edge: `n_branches`, `route_irreplaceable = (n_branches == 1)`.
Write `branches.tif` (branch label raster, 0 = none), `branches.gpkg`, `branches.csv`.

**Step 4c — values table (D13, D14).** For each branch: `_to_audit` (300 m → 1 km, areal
fraction ≥ 0.5), `audit_area_check`, then `mask_profile` for every value layer in the
Y2Y-wide alternatives column spec (import it). Add `carroll2018_pctl` = mean percentile of
Carroll 2018 current-flow centrality within the 1 km branch mask, with the routable-area
percentile as the reference column (`carroll_ref`). Join branch metrics + edge metrics
(cost, criticality, β-irreplaceable flag, `n_branches`). Write `alternatives_branches.csv`.
Caption text (stored with the table metadata): "Row unit is edge × route branch, not a solution
cluster; columns follow the Y2Y-wide alternatives table for readability only."

**Step 4d — tie-break report (Phase 8.3, small).** For edges with `n_branches ≥ 2`, rank
branches by the audit columns and write `tiebreak.csv` with both the connectivity-equivalence
evidence (slack difference) and the values evidence. Ranking only — no automated
"recommended" flag; the recommendation is a human read of the table.

---

## 4. Gates (add to §10)

| gate | invariant | where |
|---|---|---|
| G9 | every branch component (pre node-subtraction) intersects both endpoint node masks | step 4b, hard assert |
| G10 | `near_optimality == 0` exactly on every baseline least-cost path cell; tier classes monotone in slack | step 4a |
| G11 | per-branch `audit_area_check` discrepancy ≤ 5% for branches ≥ 50 km²; all discrepancies logged | step 4c |
| G12 | ensemble member count = 1 baseline + 2 (B, excluding the 1× duplicate) + 42 (C) + 2 (D, excluding the 2.5 duplicate) = 47 distinct members; duplicates resolved by config-hash equality, not by name | step 3 |

G1 stays the gate that matters; none of the above replaces it.

---

## 5. Outputs (add to §11 per-run list)

`node_parts.csv/.gpkg`, `multipart_review.csv` (run-dir copies — the canonical, H7-signed
originals live git-tracked in `audit/audit_objects/`, hash-pinned by `run_config.json`; see
step 0a and §8), `near_optimality.tif`, `near_optimality_class.tif`, `near_opt_owner.tif`,
`ensemble_attribution.tif` (+ per-axis), `branches.tif/.gpkg/.csv`,
`alternatives_branches.csv`, `tiebreak.csv`. All rasters COG, ESRI:102008 at 300 m (audit
crossings stay internal), Dublin Core+ metadata written at creation. Every product that is not a
frequency is named so it cannot be read as one.

---

## 6. Reporting rules (carry into the methods text)

- "Corridor" is reserved for bands/branches from this engine. The near-optimality surface is
  described as a near-optimality (slack) surface; `ensemble_attribution.tif` as attribution.
- Two irreplaceability senses are always reported together and never merged: edge-irreplaceable
  (D7, β ceiling — no alternative link) and route-irreplaceable (D12 — no alternative routing
  within a link).
- Zero-cost adjacency caveat (§7) applies to branch counts: "no corridor needed between touching
  areas" is conditional on IPCA proposals being realised.
- The climate dimension in this product is audit-only (macrorefugia and `carroll2018_pctl`
  columns). No routing is climate-informed. Phase 7 status is "deferred, scope extension".

---

## 7. Human tasks touched

- **H1** (O'Brien provenance/licence) — unchanged; gates release, not the run.
- **H7 (new, blocking)** — confirm or edit the `proposed` column in `multipart_review.csv`
  (produced by step 0a). Sign with a `reviewed_by` line. The run does not proceed to CWD
  until signed.
- **H6 (new)** — confirm Carroll 2018 current-flow centrality raster is on disk and catalogued;
  if absent, step 4c runs without the column and logs the gap rather than failing.
- Decision after step 3: whether to open Phase 7 at all, based on axis C stability.

---

## 8. File structure (added 2026-08-21)

The corridor analysis is promoted to a self-contained campaign folder,
**`analyses/northern_connectivity/`**, mirroring the `analyses/y2y/` flagship convention:
notebooks + spec + small frozen human-review artifacts live in the analysis folder (tracked);
engines stay at repo root; every run product stays in gitignored `output_data/`.

```
analyses/northern_connectivity/
├── 01_prep_and_parts.ipynb        # kernel y2y-geo
├── 02_calibrate_baseline.ipynb    # kernel y2y-geo
├── 03_ensemble.ipynb              # kernel y2y-geo
├── 04_alternatives.ipynb          # kernel y2y-geo
├── spec/
│   └── 05_corridors_v2_addendum_run_and_alternatives.md   [tracked — this file]
├── audit/
│   └── audit_objects/             [tracked]
│       ├── node_parts.csv / node_parts.gpkg               (step 0a)
│       └── multipart_review.csv   (H7-signed; sha256 recorded in run_config.json)
└── figures/                       [gitignored via analyses/*/figures/ — for any
                                    notebook-level figure not tied to a run dir]
```

Conventions:

- **Engine modules stay at repo root** — `corridors_prep.py`, `corridor_graph.py`,
  `corridors_core.py`, `corridors_ensemble.py`, plus `config.CORRIDORS["north"]` in `config.py`.
  Same convention as `leverage_core` / `prioritizr_core` / `results_core` for the y2y campaign;
  `corridors_core` imports `results_core`, so root placement also avoids import churn.
- **All run products stay in `output_data/corridors_north/v2_runNNN/`** (gitignored; provenance
  via `run_config.json`, unchanged from §7 of the methods doc). Per-run figures stay in the run
  dir's own `figures/`.
- **H7 artifacts are git-tracked in `audit/audit_objects/`** — `output_data/` is gitignored and
  later runs must reproduce the review file's hash, so the signed review must live somewhere
  version-controlled. This mirrors the y2y pattern (frozen, load-bearing review conclusions —
  `audit_constants.json`, `feature_characterization.csv` — tracked in the analysis folder).
  `cc.start()` copies them into the run dir and records their sha256, so each run dir remains
  self-contained.
- **Every notebook opens with the root-finding bootstrap** — the exact `_cands` pattern from
  `analyses/y2y/01_feature_audit.ipynb` cell 1 (probe cwd + parents for `config.py`,
  `sys.path.insert(0, str(ROOT))`, then define `HERE` / `AUDIT_OBJ`). The corridor modules are
  verified cwd-independent: every path derives from `config.PROJECT_DIR` (which is
  `__file__`-anchored) and the git-SHA subprocess passes `cwd=config.PROJECT_DIR` explicitly, so
  the bootstrap is the **only** move-related change the engine needs.
- The existing `analyses/*/figures/`, `analyses/*/audit/feature_cards/`, `analyses/*/runs/`
  gitignore globs cover this folder automatically — **no .gitignore edit**.
- **Migration at build time**: the four notebooks are carved from the root
  `05_corridors_north.ipynb` (40 cells; mapping in §9). Once they run end-to-end, the old
  notebook is `git mv`'d to `archive/` beside `05_corridors_north_v1.ipynb`;
  `docs/05_methods_v2.md` is patched with this addendum's sections (per the header note) and the
  CLAUDE.md 05 section gets a pointer to this folder at the same time.

---

## 9. Notebook breakdown (added 2026-08-21)

Run top-to-bottom, in numeric order, by Ethan. **One run (`v2_runNNN`) spans notebooks 02–04**:
02 creates it via `cc.start()`; 03 and 04 re-attach to it with a `RUN` variable + `cc.load()`
(same mechanism as `analyses/y2y/04_results.ipynb`'s `RUN`). The hard break between 01 and 02 is
**H7** — nothing downstream of step 0a runs until `multipart_review.csv` is signed.

### `01_prep_and_parts.ipynb` — prep, engine gates, part split → H7

- Bootstrap; imports `config, corridors_prep as cp, corridor_graph as cg, corridors_core as cc,
  corridors_ensemble as ce`; `KEY = "north"`.
- Warp the cost surface to the 300 m routing grid + **G2** (`cp.grid` / `cp.warp` / `cp.check`).
- `cg.selftest()` (**G4** in miniature + adjacency handling).
- **G1** engine equivalence on v1's own resistance (`cc.gate_g1`).
- **Step 0a**: rasterize parts at 300 m, write `node_parts.csv/.gpkg`; compute the evidence
  columns (`min_gap_cells`, `cwd_between_parts`, `intervening_nodes`, `crosses_cost_1000`, …);
  apply decision rules 1–4; write `multipart_review.csv` with the `proposed` column →
  `audit/audit_objects/`.
- **ENDS at the H7 stop**: a closing markdown cell instructs the reviewer — edit `proposed`
  where the rules got it wrong, add the `reviewed_by` line. (Absorbs cells 1–8 of the root
  notebook.)

### `02_calibrate_baseline.ipynb` — steps 0–2

- Bootstrap; **step 0** preconditions: assert `multipart_review.csv` carries `reviewed_by`;
  re-baselined **G0** (name set = 42, same 3 dedupe merges, part count, review-file hash);
  **G2 / G8** re-assert on current disk state.
- `A = cc.start(KEY, label="v2 baseline", require_cutoff=False)`; resistance diagnostics.
- **Step 1** calibrate: CWD per seed part (cache keyed by resistance hash + part-mask hash),
  intra-name MSTs locked, `calibrate_cutoff` on the inter-name MST only → `cwd_cutoff_abs` into
  `run_config.json`; report the residual vs 18,188 km².
- **Step 2** baseline: locked + inter-name MST + β = 2.5 augmentation (**G3**; **G4** read as
  "locked + inter-name MST"), criticality table, bands, `linkage_priority.tif` +
  `edge_owner.tif`, v1 compare, co-benefit audit (**G5**), maps. Edge table carries
  `edge_class`. (Absorbs cells 9–32.)

### `03_ensemble.ipynb` — step 3

- Bootstrap; `RUN = "v2_runNNN"`; `A = cc.load(...)`.
- **G7** drop-nothing member; `ce.run`: axis B {0.5, 1, 2}×, axis C 42 leave-one-out **by name**
  (all parts dropped together, incl. `no_link`), axis D β {1.5, 2.5, 4.0}; `ce.collect`.
- **G12** (47 distinct members by config-hash); write `ensemble_attribution.tif` + per-axis
  rasters (D15). Resumable — a member is done when its summary exists. (Absorbs cells 33–36.)

### `04_alternatives.ipynb` — steps 4a–4d

- Bootstrap; `RUN`; `A = cc.load(...)`.
- **Step 4a** near-optimality surface, streamed edge-by-edge from the memmaps;
  `near_opt_owner.tif`; tiers (**G10**).
- **Step 4b** route branches at `branch_mult × cwd_cutoff_abs` (**G9** hard assert);
  `branches.tif/.gpkg/.csv`; `route_irreplaceable` flags.
- **Step 4c** values table: `_to_audit` 300 m → 1 km, `audit_area_check` (**G11**),
  `mask_profile` over the imported Y2Y-wide alternatives column spec, `carroll2018_pctl`
  (H6-guarded: an absent layer logs the gap, doesn't fail) → `alternatives_branches.csv` with
  its caption.
- **Step 4d** `tiebreak.csv` (ranking only, no recommended flag).
- `cc.finish(A)` + the `runs.csv` index. The two irreplaceability senses are reported side by
  side per §6. (Absorbs cells 37–39.)

The "decision after step 3" (whether to open Phase 7, based on axis-C stability) sits between
notebooks 03 and 04 in wall-clock terms but does **not** block 04 — steps 4a–4d are
climate-free by construction (D14).

### Clarifications (structural review 2026-08-21)

Three ambiguities surfaced while mapping the run sequence onto notebooks; each is a proposal to
confirm when `docs/05_methods_v2.md` is patched, not a settled decision:

1. **Multipart band/slack semantics.** §3 fixes inter-name *distance* (min over part pairs) but
   not the *field* used on an inter-name edge. Proposed: a multipart name's CWD field =
   pointwise min over its seed parts' fields (equivalent to multi-seed CWD from the part union),
   used everywhere a name-level field is needed — bands, near-optimality, branches.
2. **Intra-name edges in step 4b.** Step 4b enumerates "MST + augmentation" edges, but step 2
   declares locked `intra_name` edges real corridor land included in criticality and failure
   enumeration. Proposed: locked edges get branches too, carrying `edge_class` into
   `branches.csv` / `alternatives_branches.csv`.
3. **Tier domain.** `near_opt_tiers` percentiles are computed over the 2× union band, so cells
   outside it fall to "occasional" implicitly. Proposed: state that explicitly.
