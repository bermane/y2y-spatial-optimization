# Alberta Y2Y Prioritization — Analysis Spec (Mirror of Y2Y-Wide v0.13)

**Status:** v0.3 — DRAFT for review. No gates entered. Data acquisition list open (§8); D-AB5 resolved in structure (X and infeasibility check land at AB-0a); D-AB6 open.
**Scope:** Applied decision-support run for Y2Y Alberta program (per Tim Burkhart scoping answers, 2026-09) + scale-transfer methods test: how the frozen Y2Y-wide methodology behaves at subregional extent on a substantially more disturbed landscape. Separate analysis folder; consumes the Y2Y-wide pipeline as a library. NOT a paper-1 component (parent §14 fences remain; anything here that feeds a paper is applied-paper material).
**Mirror declaration:** Mirrors `frequency_ensemble_study_plan.md` **v0.13** (read 2026-09-02). What is mirrored is the frozen **decision procedure** — §2.5 rules R1–R4 with constants θ=5×, λ=0.10, a_min=0.5%, t_min=0.15; block accounting in two-regime swing currency; scenario-construction rules (§3.1 structure); numerics standards (§2.6); estimand and aggregation (§4); manifest discipline (§9) — NOT the Y2Y-extent measurements. Leverage values, class assignments, θ-tails, and the frozen (w,t) vectors in parent §2.5/§3.1 are properties of the Y2Y extent and are expected to differ here. Alberta derives its own characterization table and `scenarios_ab_v1.json` by the identical protocol. Upstream spec amendments propagate by re-pin: bump the mirror version here, log the delta, re-run affected stages.
**Companion documents:** parent spec v0.13; `gate_ab0a_reportback.md` (future); Tim Burkhart scoping thread (2026-09).

## Changelog
- v0.3 — Parent accounting CONFIRMED from code (Ethan read-back): characterization on full 1.27M extent; targets value-counting (locked amounts bank; Y2Y banked shares 12.3–19.2%); budget 30%-total with locked area consuming RHS (191,029 of 381,874). D-AB5 re-resolved: escalation now expected — primary AB-L budget pre-registered as locked + X% of unlocked (additions semantics; X set at AB-0a, anchor 15% of unlocked ≈ parent realized discretionary share); infeasibility case (locked > 0.30·N) named. AB characterization table gains supplementary zero-solve columns `banked_capture` / `residual_target` / `pre_satisfied` (disclosure of the audit-unconstrained vs lock-conditional gap, first-order at AB banked shares). H-AB5 registered (alpine-affine features pre-satisfied at lock; additions driven by residual-target foothills features). Parent methods disclosure line mirrored (§4).
- v0.2 — CORRECTION: the parent formulation already locks in existing PAs (evidence: 1.27M total vs 1,082,069 discretionary cells ≈ 15% locked; MGA Hamming space and verdict rule defined on discretionary cells; E17-T1 "locked-PA baseline separated" convention). D-AB2 rewritten — lock-in is inherited, not a deviation; AB-L is the exact mirror and primary config; AB-U demoted to optional S0-only diagnostic (C3). D-AB5 narrowed — budget-lock semantics inherited from the parent pipeline (read from code at AB-0a, recorded, not re-decided); only a degenerate-headroom contingency remains open. Invented lock rule (0.5 majority) removed — parent rule inherited. C1 re-pointed to AB-L vs Y2Y clip on discretionary cells.
- v0.1 — Initial draft. Deviation register D-AB1–D-AB4; open decisions D-AB5 (budget semantics under lock-in) and D-AB6 (adjacency buffer distance); gates AB-0a…AB-5; data acquisition table; pre-registered transfer hypotheses H-AB1–H-AB4.

---

## 1. Purpose

Two audiences, one build.

**Applied (primary deliverable).** Priority landscapes for protection within the Alberta portion of the Y2Y region, per Tim Burkhart's confirmed scope: full Alberta Y2Y extent; public and private tenure considered, private ranchlands retained for the OECM pathway; no a-priori exclusions; existing parks/protected areas not to be surfaced as recommendations (satisfied by the parent formulation's inherited PA lock-in with masked display — see D-AB2, corrected v0.2); areas of interest reported as audit overlays (§6). Deliverables: locked-config F surface and anchor maps with PAs masked from display; tenure-split reporting (crown → protection candidates, private ranchland → OECM candidates); AOI capture columns.

**Methods (secondary, feeds applied paper only).** Scale-transfer characterization of the frozen Y2Y-wide protocol: (a) does the feature-behavior regime change at subregional extent (§5, H-AB1–H-AB3); (b) do zoomed-in priorities spatially concur with the Alberta clip of zoomed-out priorities (§7, C1); (c) does plateau richness survive a smaller, more disturbed, more constrained extent (H-AB4).

## 2. Deviation register

Everything not listed here is identical to parent v0.13 by construction (library import + config).

| ID | Deviation | Detail |
|---|---|---|
| D-AB1 | Extent | Alberta portion of Y2Y region boundary. Planning-unit grid is the **exact subset of the Y2Y-wide grid** (same cell IDs, same alignment, ESRI:102008) — never re-snapped or re-gridded, so every cross-solution comparison is cell-exact. Cells intersecting the AB boundary follow the parent's boundary-cell rule unchanged. |
| D-AB2 | PA lock-in (CORRECTED v0.2: inherited, not added) | The parent formulation locks in existing PAs (discretionary-cell machinery; E17-T1 locked-PA baseline). **AB-L (locked) is therefore the exact procedural mirror and the primary config**, inheriting the parent's lock rule and PA layer (clipped to AB) unchanged. The only D-AB2 deviation is presentational: applied outputs mask locked cells so only additions display. Rationale for lock-in over Tim's literal "exclude" stands and is now also a mirror argument: hard exclusion would remove PA feature amounts from target accounting, so alpine EFGs / macrorefugia / high-intactness read as unmet and the additions map re-imports the rock-and-ice bias. **AB-U (unlocked)** is a genuine deviation and is demoted to an optional diagnostic — S0 cells only — feeding C3 (how much priority structure the existing PA network absorbs vs reorganizes). |
| D-AB3 | Tenure attribute join | Post-hoc reporting only; **never** enters the objective, constraints, or costs in v0.x (jurisdiction-blind principle; a tenure-weighted cost variant is future work, out of scope §11). Classes: `crown_green` (Green Area), `crown_disposition` (grazing/other disposition polygons), `private_presumed` (White Area minus crown dispositions minus PA), `private_ranchland` (private_presumed ∩ grassland/pasture cover), `pa_locked`. Reporting split: crown selections → protection candidates; private_ranchland selections → OECM candidates. |
| D-AB4 | AOI audit columns | Per-AOI capture % and mean F (locked config), `carroll2018_pctl`-style — never lock-ins. AOI-1: parks/wildlands adjacency buffer (distance = D-AB6). AOI-2: Upper Smoky SRP Nature-First Zone, computed **NFZ minus PA compilation** to isolate the novel area (NFZ includes Willmore/Kakwa); area from shapefile, not press figures (sources conflict: 3,200 vs 2,200 km²). AOI-3: "west of Grande Cache" — DEFERRED to reporting stage per Ethan 2026-09; candidate polygons identified from results geography, confirmed with Tim by map, then added as a column (zero solves). |

Explicitly NOT deviations: feature stack (original eight + 40 EFGs), budget percentage (30%, but see D-AB5), scenario structure S0–S5, climate axis (SSP245/SSP585, 2071–2100, constant-influence-per-scenario with per-cell weight re-derivation), estimator (`mga_maxham_v1`, k=50, g=5%), f(g) grid on reference cell, numerics standards (opt_gap 1e-4, NumericFocus 2, LP twin per certified MILP, dust rule), presentational bands, CRS.

## 3. Open decisions (resolve before AB-1)

**D-AB5 (re-resolved v0.3) — Budget semantics.** Parent semantics CONFIRMED from code: budget is 30%-total (RHS = 0.30 × 1,272,914 = 381,874 cells), locked cells sit in the A-matrix with lb=1 and consume RHS (191,029 locked; 190,845 discretionary selected). In the AB extent the mountain-park estate is concentrated, so the locked share will be a multiple of the parent's 15%; the inherited referent is expected to fail here — either infeasible (locked count > 0.30·N_ab: lb=1 exceeds RHS; check this FIRST at AB-0a, before any solve attempt) or near-trivial (sliver of additions). **Pre-registered resolution: primary AB-L budget = locked + X% of unlocked area (additions semantics). X is set at AB-0a with disclosure; anchor X = 15% of unlocked, which reproduces the parent's realized discretionary share of extent.** Report alongside it, at zero solve cost, the factual current-protected share of the AB extent against the 30×30 lens — if that share is at or near 30%, that is itself a Tim-facing headline (the Alberta strip is near the areal target; the live questions are composition and additions, which the OECM track reinforces: OECMs are additions by definition). C1 caveats the changed budget referent wherever it applies.

**D-AB6 — Adjacency buffer distance (AOI-1).** Candidate: 10 km (defensible for wide-ranging large-bodied mammals, the connectivity layer's taxonomic scope). Freeze one distance before solving; report a 5/10/20 km sensitivity row in the AOI table (zero solves — overlay arithmetic only).

## 4. Extent-relative targets (declaration)

All targets, leverage values, θ-tails, and a_min/t_min tests are computed on Alberta-extent feature totals. A target of t on a feature means t of *Alberta's* amount of that feature, not the Alberta share of the Y2Y-wide amount. This is intended: the Alberta solve is a different problem, not a crop of the Y2Y solution — the C1 comparison (§7) exists precisely because the two can disagree. Consequence for the dust rule: the <1e-9-of-feature-total threshold re-applies against Alberta totals; per-feature drop counts disclosed fresh (parent §2.6.2 discipline).

**Audit-space vs lock-conditional disclosure (mirrored from parent, v0.3).** Characterization quantities (leverage, cap_min/cap_max, two-regime swing, θ-tails) are computed over the unconstrained selection space of the full planning-unit set, locked cells included; all solves are lock-in-conditional. Under lock-in the feasible capture interval per feature is [banked + poorest-discretionary-fill, banked + best-discretionary-fill] — floor above audit cap_min, ceiling generally below audit cap_max — so intended influence is a budget-capacity currency and realized influence operates on the lock-conditional feasible set. Estimand choice, not inconsistency; intended and realized reported side by side, no iteration against realized swing (parent v0.10 ruling). Because AB banked shares will far exceed the parent's 12.3–19.2%, this gap is **first-order here**, so the AB characterization table carries three supplementary zero-solve columns computed from the audit objects plus the PA mask: `banked_capture` (feature amount inside locked cells, as share of AB total), `residual_target` (max(0, t − banked_capture)), and `pre_satisfied` (banked_capture ≥ implied target). The primary R1–R4 characterization remains on the parent convention — required for C2 comparability; the supplementary columns are the disclosure made quantitative and the explanatory spine of the applied report (the additions map is driven by residual-target features).

## 5. Gate AB-0a — Feature characterization audit (full re-run)

R1–R4 verbatim on the clipped extent, frozen constants, all 12 inputs, feature cards regenerated, budget-independent audit objects rebuilt for the AB extent. Class assignments follow the rules wherever they land — **class flips relative to the parent table are results, not problems**, and the AB-vs-Y2Y characterization table is the first headline comparison (C2). Pre-registered directional hypotheses (stated now so they cannot become post-hoc stories):

- **H-AB1 (contrast recovery).** The four Y2Y-wide low-contrast, weight-insensitive layers (intactness, macrorefugia, connectivity, AOH) regain spatial contrast in Alberta. Strongest expectation: gHM intactness — the foothills disturbance gradient is steep, so leverage should rise materially from 0.042; if it crosses out of R3-inexpressibility, S5 (intactness-forward) becomes expressible at this extent and D3(b)'s published-inexpressibility finding acquires a scale-dependence footnote. That flip alone would justify the exercise.
- **H-AB2 (EFG contraction).** The EFG set present in Alberta is much smaller than 40; several survivors sit near a_min = 0.5% of the (smaller) extent and R1/R2 dispositions will differ. Expect a shorter locked-adequacy foundation and possibly a larger unsaturated-disclosure set.
- **H-AB3 (carbon regime shift).** m_soc's concentrated-satiating classification is driven by boreal/foothills peat-adjacent tails that are partly inside Alberta; whether the θ-tail crossing and implied target survive the clip is genuinely uncertain — no directional prediction registered, which is itself the registered statement.
- **H-AB4 (plateau richness, tested at AB-2).** Smaller extent + steeper disturbance gradients + (in AB-L) locked structure should *narrow* near-optimal freedom: expect D below the parent's 0.953 and C above 0.020, direction only. If AB-L turns plateau-poor (D < 0.10 or C > 0.90 under the parent's frozen verdict rule v2), the F surface for Alberta is closer to a single map than an ensemble — which is itself the decision-relevant answer for Tim (little implementation flexibility) and must be reported as such, not treated as a failure.

- **H-AB5 (banked pre-satisfaction, v0.3).** The AB locked estate is refugia-rich and alpine-EFG-rich (parent banked shares already peak on refugia at 19.2% with only 15% of cells locked); expect several alpine-affine features (macrorefugia, high-elevation EFGs, intactness) to arrive `pre_satisfied` — zero residual target pull, constraint slack at the root — while foothills-concentrated features carry near-full residual targets into a thin discretionary pool. Prediction: the additions map is driven by residual-target features on the disturbance gradient, and this, not weight choice, is the first-order determinant of AB-L selection. Verdict from the supplementary columns at AB-0a, before any solve.

Gate AB-0a also measures: locked-cell count and share (D-AB5 infeasibility check first, then X), per-feature `banked_capture`/`residual_target`/`pre_satisfied`, tenure class shares, AOI overlay areas.

## 6. Scenario set, ensemble, and outputs

- `scenarios_ab_v1.json` derived by parent §3.1 rules from the AB-0a characterization: S0 equal-discretionary-influence-per-block (joint block accounting, two-regime swing on AB-extent layers); S1–S3 block-share doubling; S4 carbon-forward by the parent's θ-relaxation + block-doubling recipe *re-derived on AB tails* (parent's t=0.552 is a Y2Y number; the AB analog comes from the AB audit); S5 status contingent on H-AB1. Climate axis crossed as parent. Cell count 14 if S5 remains inexpressible-disclosed; 16 if S5 activates (then reconcile against parent structure in the report).
- AB-L runs the full cell set; AB-U runs S0 cells only (C3 diagnostic, optional). Compute is not a constraint: the AB extent is roughly an order of magnitude fewer planning units than the parent's 1.27M, so anchors are expected in seconds and full MGA ensembles in minutes per cell; budget the wall generously at parent-per-cell rates anyway and report measured.
- Estimand: F_i per config, parent §4 unchanged. E4's f(g) grid on one reference cell per config.
- Applied outputs (AB-L): F surface with `pa_locked` masked; anchor maps masked; T1-analog scenario table; tenure-split selection summaries; AOI table (capture %, mean F, sensitivity rows per D-AB6); one-page map set for Tim (plain-language captions — no estimand jargon in the deliverable layer).

## 7. Comparisons (the "zoom-in" question, made concrete)

| ID | Comparison | Instrument | Reading |
|---|---|---|---|
| C1 | AB-L anchors & F vs Y2Y-wide anchors & F clipped to AB — both locked; computed on discretionary cells with the locked-PA baseline separated (parent E17 convention; the two configs share the same locked set by construction, so discretionary cells align) | **Overlap coefficient** per scenario cell (Jaccard only as supplementary — set-size artifact when the clip's selected share ≠ 30% of AB; parent Morris lesson) + F–F rank correlation on shared cells | Do subregional priorities concur with the AB portion of whole-region priorities? Divergence localizes where extent-relative targets bite. |
| C2 | AB-0a characterization table vs parent §2.5 table | Side-by-side: leverage, θ-tail, class, lever per feature; flip list | Does the feature-behavior regime change with scale? (H-AB1–H-AB3 verdicts.) |
| C3 | AB-L vs AB-U (S0 cells only; optional) | Selection delta maps; per-feature capture deltas; F delta | How much priority structure does the existing PA network absorb vs reorganize? The additions logic, isolated. |
| C4 | AOI columns (AB-L) | Capture % and mean F per AOI vs extent-share null | Does the tool independently find what Y2Y already believes matters? Low NFZ capture is informative, not embarrassing (zone drawn for caribou + existing parks, not complementarity) — pre-stated so it can be reported straight. |

## 8. Data acquisition

| # | Layer | Role | Source | Status |
|---|---|---|---|---|
| 1 | Y2Y boundary, AB clip | Extent | In hand | Clip + grid-subset only |
| 2 | 12 feature inputs | Features | In hand (Y2Y-wide stack) | Clip to grid subset; re-run dust rule |
| 3 | PA compilation (CPCAD / Y2Y PA classification incl. AB parks+PLUZ from GeoDiscover) | AB-L lock-in; NFZ subtraction; tenure class `pa_locked` | In hand | Verify AB completeness (national + provincial + wildland + PLUZ conservation designations) against CPCAD before lock rule applies |
| 4 | Green Area / White Area boundary | Tenure: crown vs settled split | GeoDiscover Alberta (open) | **Acquire** |
| 5 | Public land dispositions (grazing et al.) | Tenure: `crown_disposition` | GeoDiscover Alberta (open) | **Acquire** |
| 6 | Grassland/pasture cover (GVI in White Area; AAFC land use fallback) | Tenure: `private_ranchland` classifier | GoA / AAFC (open) | **Acquire** |
| 7 | Upper Smoky SRP spatial data (`US_SRP_Zones` package) | AOI-2 (NFZ) | GeoDiscover / open.canada.ca (open; plan effective 2026-01-01) | **Acquire** |
| 8 | AltaLIS cadastral (ETM) | Parcel-level ranchland (optional refinement) | AltaLIS (paywalled; possible UBC access) | Deferred — class-level tenure (rows 4–6) suffices for the OECM reporting split |

Naming note for all documents and the Tim-facing report: the plan is the **Upper Smoky Sub-Regional Plan** (Tim's "Upper Little Smoky" corrected; likely conflation with the Little Smoky caribou range).

## 9. Gates

| Gate | Content | Exit criterion |
|---|---|---|
| AB-0a | Grid subset; dust re-run; full R1–R4 audit (parent convention) + supplementary banked/residual/pre_satisfied columns; cards; locked count & share (infeasibility check first), tenure shares, AOI areas | Audit frozen; H-AB1–H-AB3 and H-AB5 verdicts recorded; D-AB5 X set with disclosure; D-AB6 frozen |
| AB-0 | `scenarios_ab_v1.json` frozen; comparison solves (a-series analogs) on AB extent, both configs | Targets bind at kink; lever-principle reproduction holds at AB extent |
| AB-1 | S0 anchors ×2 configs ×2 climate; T1-analog; LP twins | Certified; captures in pre-stated bands or reported-as-failed (parent honesty convention) |
| AB-2 | MGA pilot, reference cell (AB-L; AB-U only if C3 activated); verdict rule v2 (parent hash, unmodified) | H-AB4 verdict; plateau-poor outcome is a finding, not a fail |
| AB-3 | Manifest freeze (schema = parent §9 + `config` ∈ {ab_u, ab_l}, `extent_id=ab_y2y_v1`, `mirror_spec_version=v0.13`, `lock_rule`, `budget_semantics`) | `manifest_freeze.sha256` |
| AB-4 | Full run AB-L (+ AB-U S0 subset if activated); C1–C4 measured | F surface delivered; comparisons in report |
| AB-5 | Applied reporting: masked maps, tenure split, AOI table incl. AOI-3 candidates → Tim map-confirm | Tim-facing packet out; AOI-3 column added post-confirmation |

## 10. Directory / file contract

```
alberta_prioritization/
  spec/alberta_prioritization_spec.md          # this file
  spec/manifest.csv + manifest_freeze.sha256
  spec/scenarios_ab_v1.json
  audit/feature_cards_ab/
  audit/audit_objects_ab/
  data/tenure/  data/aoi/  data/pa/            # acquired layers, provenance sha256s
  runs/<config>/<cell_id>/anchor/ mga/ twin/
  analysis/c1_concordance/ c2_audit_compare/ c3_lock_delta/ c4_aoi/
  figures/  report_tim/
  changelog.md  results_log.md
```
Pipeline code is imported from the Y2Y-wide repo as a package pinned to a commit; the pinned SHA is recorded in the manifest. No pipeline code is copied into this folder.

## 11. Out of scope (fenced)

OECM policy analysis and parcel-level ranchland identification (class-level tenure only). Tenure-weighted costs (future variant; would break jurisdiction-blindness of v0.x). Corridors v2 / least-cost machinery (separate track). "West of Grande Cache" boundary definition before results exist (D-AB4/AOI-3 sequencing). Paper-1 claims (parent owns the estimand novelty; anything AB-derived is applied-paper material). Multi-budget beyond D-AB5's resolution. Ranchland OECM feasibility scoring.
