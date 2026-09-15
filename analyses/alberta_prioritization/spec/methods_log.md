# Alberta Y2Y Prioritization — Methods Log (living, binding)

Cumulative methods record for analysis 3 (`analyses/alberta_prioritization/`). Same convention as
`analyses/y2y/spec/methods_log.md`: every methods-relevant decision, data manipulation,
formulation, solver/numerics, or QA-rule change gets an M-numbered entry in the SAME session it
is made; reversals supersede, never delete. Parent-mirrored procedure is NOT re-logged here —
only AB-specific decisions, deviations (D-AB*), measured re-pins, and anything the mirror
declaration in `alberta_prioritization_spec.md` does not already fix. Cross-reference parent
entries by their M-number.

## M1. Spec v0.4 — review round 1 + parent re-pin (2026-09-03)

**M1.1 Mirror re-pinned v0.13 → v0.14.1.** Absorbed parent rulings: dual-semantics ensemble
(aggregate 5% band = estimand; per-block-floor guarded sweep = applied headline — parent
E14/E15), D quoted from MGA only (E12), meaningful-target-window test on derived targets (E10),
audit-space vs lock-conditional disclosure (M3.6), "formulation" terminology (M4.17).
Consequences: guarded sweeps added at AB-2 (pilot) and AB-4 (all formulations); C1/C3 compare
matching semantics only; S4-analog θ-target must clear the AB co-capture + banked floor.
**M1.2 D-AB5 budget anchor corrected.** Primary AB-L budget = locked + X% of unlocked; anchor
X = **17.6%** = the parent's realized fill rate of discretionary land (190,845 / 1,081,885).
v0.3's "15%" was the parent's additions share of TOTAL extent — a different referent whose gap
vs the fill rate scales with the locked share. X is still set at AB-0a with disclosure;
infeasibility check (locked > budget) runs first.
**M1.3 Code provenance rule.** Working-tree import of the live pipeline modules (campaign-wide
pattern); `pipeline_git_sha` recorded in the manifest; AB-3 freeze asserts a clean working tree.
No package pin, no code copied into the folder.
**M1.4 Input count.** 8 continuous features + the 40-EFG block (v0.3's "12" echoed the parent's
disclosed card miscount).
**M1.5 Directory contract** fixed to `analyses/alberta_prioritization/`; this log and
`results_log.md` created as the binding registers.

## M2. Gate AB-0a build (2026-09-03; notebooks 01–02 written, PENDING-RUN)

**M2.1 AB extent rule (D-AB1 made concrete).** AB PU = parent PU ∩ rasterized Alberta polygon
(`input_data/alberta_boundary/alberta.gpkg`, ESRI:102008) with the centre-in-polygon cell rule
(`rasterio.features.rasterize`, `all_touched=False` — the same rule `gdal_rasterize` applied to
the parent PA mask). The Y2Y-side boundary rule — including the parent's 20 km study-area
buffer — is inherited through the parent PU; the count of AB PU cells outside the unbuffered
Y2Y boundary is printed as a disclosure, not removed.
**M2.2 AB hand-off stack = parent stack masked on the SAME grid** (`input_data/aligned_stack_ab/`,
identical layout: continuous COGs, `cost_uniform`, `mask_protected_areas`, `iucn_efg/`,
`climate_realizations/`). No crop, no re-snap ⇒ cell IDs identical to the parent grid (C1 is a
direct array comparison). R ingests the full grid with `roi.mode="full"`; PU = non-NaN cost
cells. Chosen over a crop because `leverage_core`'s audit entry points derive the PU mask from
`handoff_dir`, so a masked stack lets every parent module run unmodified.
**M2.3 Dust rule re-run against AB totals** (spec §4): parent `DUST_SHARE_MIN` = 1e-9 of the
feature's AB total; per-feature drop counts printed and archived in `_build_meta.json`; the
parent's <1e-4 mass-loss assert carries. Applied to the climate realizations too (both, so the
245 layer is AB-dust-consistent with the 585 canonical layer).
**M2.4 EFG drop rule re-applied**: an EFG with no occurrence (value 1/2) inside the AB PU is
not written (H-AB2 contraction measured here, disclosed by name).
**M2.5 Lock accounting order (D-AB5).** Infeasibility check (locked > 0.30·N_ab) runs BEFORE any
budget is set; X is DERIVED in-notebook from the parent's own artifacts (parent locked count,
parent budget cells ⇒ discretionary selected ÷ discretionary cells = 0.1764), not typed; the
effective AB budget = (locked + X·unlocked)/N_ab is frozen to `spec/ab_extent_v1.json` and
applied by `pr_override(budget_pct=…)` in every solve notebook (config's `ANALYSES["ab_y2y"]`
keeps the parent 0.30 as the documented baseline). The 15%-of-unlocked and 15%-of-total
alternatives are printed beside it for disclosure.
**M2.6 Audit budget convention.** R1–R4 at the parent's 30%-of-extent convention (C2
comparability, spec §4); leverage at the EFFECTIVE AB budget reported as a supplementary column.
**M2.7 Meaningful-target-window proxy (zero-solve).** For any target-bearing feature the floor
is approximated as banked_capture + (discretionary budget share × the feature's discretionary
mass share) — the incidental capture of an area-proportional fill. A derived target below this
proxy is flagged; the true window is priced at AB-1 when anchors exist (parent E10 pricing).
**M2.8 D-AB7 registered** (presentation scale re-set at AB-5; procedure inherited).
**M2.9 config.py**: `AB_HANDOFF_DIR` + `ANALYSES["ab_y2y"]` added (roi full, lock-in pa_mask,
penalties 0, targets {}, parent defaults otherwise).
**M2.10 Data sources scouted (2026-09-03; `data/README.md` + `data/acquire.py`, provenance
sha256 per file).** Open + verified: Green/White Area (REST, `GWA_NAME`), GVI (southern White
Area only, 48.9–52.5°N; ranchland = native-upland site types 11–24 + tame pasture PN/PI), AAFC
Annual Crop Inventory 2024 (fallback north of GVI: classes 110 grassland / 122 pasture-forage /
50 shrubland), Upper Smoky SRP zone package, PLUZ (REST), CPCAD (manual). **Dispositions are
NOT open** (Protected A; Altalis DIDs for-fee) → D-AB8 opened; the `crown_disposition` class
and hence the clean `private_presumed` class wait on it. Ranchland classifier is therefore
two-source by necessity (GVI where it exists, ACI elsewhere) — the seam at ~52.5°N is disclosed
in the tenure table.

## M3. Reporting-spec re-pin (2026-09-03)

**M3.1 Parent `director_package_spec.md` v1.3 conventions absorbed** (spec v0.4.2 §6): tier-
achievement figure; % area annotation + inset F histogram; Act-1 (a)/(b) pair recast under
D-AB2 as masked-additions view / locked-estate context view; anchor agreement matrix; T-D4-analog
by Alberta Natural Region/Subregion and by tenure class; E17 precedent line. Aggregation
constants (250 km² hexes, 100 km² minimum cluster, top-5–7) are NOT mirrored — D-AB7 governs;
AB display at or near 1 km. C4 adopts the "alignment, not assignment" language rule.
**M3.2 D-AB8 (dispositions / title data) ask ON HOLD** per Ethan; AB-5 tenure columns proceed on
the coarse route (White Area − PA ∩ grassland cover) with the crown-lease contamination disclosed
unless a licensed layer appears; at 1 km the class carries "mostly crown / mostly private", not
parcels.
**M3.3 Engine fix surfaced by the AB run (leverage_core.trajectory_figure).** On the AB extent
several features clear θ only at the first archived point (area 0%), which made the F8 label-
collision guard divide by zero. Crossings at 0% area are now skipped in the annotation loop
(no shelf to label; not representable on the log axis). Cosmetic; classification and archive
untouched; the parent's F8 is unaffected (every Y2Y crossing is > 0%).

## M4. Gate AB-0a rulings (Ethan, chat 2026-09-03; report-back D1–D6)

**M4.1 D1 → D-AB9:** biodiversity block stays whole (birds + mammals) despite mammals' R3 flip;
mammals' derived weight is inert by the R3 mechanism and is disclosed, not removed. Birds-only
rejected as misrepresenting the elicited value. S3 runs; 14 formulations intact.
**M4.2 D2 accepted (mirror):** S0–S3 keep m_soc t = 0.322 although pre-satisfied (banked 0.714);
intended vs realized reported side by side; no lock-conditional re-derivation.
**M4.3 D3 accepted:** S4-analog θ-relaxation = **θ 2×** (AB archive → t = 0.772, the smallest
relaxation clearing the 0.765 zero-solve floor; parent recipe θ 3× → 0.642 would not bind).
S4 acceptance band scored on m_soc's θ-tail only (biomass's AB θ-tail is 0.05% of the extent —
band vacuous), disclosed. The pilot's certified capture vs the true floor is the AB-1 check.
**M4.4 D4 accepted:** corridors (leverage 0.100 = λ) passes by the literal rule; disclosed marginal.
**M4.5 D5 TABLED:** D-AB6 not frozen; proximity-to-PA read post hoc from clusters (spec §3).
**M4.6 D6 OPEN — additions budget realism.** Ethan: ~10,000 km² of new protection in Alberta is
not realistic now; question = run at the derived X (10,083 km²) and let the frequency tiers
shrink the answer, or halve the budget from the start. Proposal in chat (two-level budget
design with an S0 nesting test). **RESOLVED same session: two-level test adopted (D-AB5 v2).**
Level A = X (10,083 km² additions, mirror); level B = X/2 (≈5,041 km², realistic envelope);
S0 at both levels at AB-1/AB-2; nesting rule frozen BEFORE solving: overlap coefficient of the
guarded frequent tiers N = |core_B ∩ core_A| / |core_B| ≥ 0.80 ⇒ level A primary, else level B
primary for the applied deliverable (A kept as the methods mirror). `ab_extent_v1.json` stands
as level A; `ab_budget_levels_v1.json` (04) carries both.

## M5. Gate AB-0 build (2026-09-03; notebooks 04–05 written, PENDING-RUN)

**M5.1 a-series analogs at level A only** (`04_ab0_arms`, R): w = t convention (Gate-0-only,
mirror), Gurobi binary opt_gap 1e-4 + NumericFocus, arms a0 / a1 / a4 / a5. a2/a3 (flat
double-pool targets) are NOT mirrored — biomass has no AB tail to demote (θ-target 0.003) and
m_soc's protocol target is pre-satisfied, so flat comparators would only measure decorations.
a5 (m_soc 0.772) is new: the floor probe. Outputs `runs/ab_l/gate0/<arm>/` inside the analysis
folder (results_dir overridden), not `output_data/`.
**M5.2 G0 exit criteria re-read for a pre-satisfied target**: a1 ABOVE target is the expected
E10 outcome, not a failure; the kink test is carried by a5; a4 by objective-equivalence within
2.5× opt_gap (parent binary convention); the a0 control's m_soc capture IS the measured floor.
**M5.3 S4 ladder** (spec §12): first θ ∈ {2, 1.5, 1.2} whose archive target ≥ a0 floor + 0.01;
AB-1 pilot certifies; step up if non-binding.
**M5.4 Carbon split diagnostic applied as written** (parent Gate-1 rule on a1's biomass θ-tail
mass capture) with the AB caveat that the tail is ~0.05% of the extent — near-vacuous;
disclosed. AB SOC/biomass mass split ≈ 67.5/32.5 (from the stack totals).
**M5.5 Scenario derivation** on the AB stack at the 30% audit convention via
`scenario_weights(handoff_dir=AB)`; blocks/within-block per the parent; biodiversity both
members (D-AB9); S5 = S0 + gHM×10 (inexpressible push, mirror); EFGs at 1/27. Frozen to
`spec/scenarios_ab_v1.json` (parent schema + `_meta.s4_ladder`, budget levels, rulings);
budget levels to `spec/ab_budget_levels_v1.json`.
**M5.7 CORRECTION to M5.3 (first 05 run, 2026-09-03 — the pre-registered stop fired and came to
chat as specified).** The ladder's reference arm was wrong: a0_control's m_soc capture (0.867)
includes carbon's own pull under equal weights, whereas the E10 floor is co-capture + lock-in =
capture with NO carbon pull. a1_protocol measures exactly that (its 0.322 target is pre-satisfied,
so the term is zero above it): **0.744** (proxy 0.765). Against the corrected floor θ 2× → 0.772
clears by 0.028, and a5_floor (t = w = 0.772) landed at 0.7720 — at the kink — the direct
certification that a target in that window binds. D3 (θ 2×) stands; a4's objective differs from
a0's by exactly the 0.2 constant an unreachable target contributes (pull-invariance holds). 05
patched to read the floor from a1 with an assert that a1 is indeed pre-satisfied; rule text in
spec §12 corrected with the history kept.
**M5.6 AB-U (unlocked, C3) not run at AB-0**: the engine has no "no lock-in" mode (`lock_in.source`
∈ {pa_mask, vector, both}); adding one is a small engine change deferred until C3 is activated.

## M6. Tenure estimate + AOI overlays (2026-09-03; `03_ab0a_tenure_aoi` built, PENDING-RUN)

**M6.1 Private-lands estimate equation** (spec v0.4.4 D-AB3): per 1 km cell, centre-in-polygon
(the parent PA-mask rule): PA → `pa_locked`; ¬PA ∧ Green → `crown_green`; ¬PA ∧ White ∧
CROWN_IND → `crown_white_ind`; ¬PA ∧ White ∧ ¬CROWN_IND → `private_presumed`; ∧ ranch_frac ≥ 0.5
→ `private_ranchland`. CROWN_IND = active Crown Land Reservation ∨ PLUZ (∨ Disposition when
present). Reservations and PLUZ apply only to public land, so inside the White Area they are
positive evidence of crown tenure; their ABSENCE is not evidence of private tenure — hence the
disclosed over-count (grazing leases). Cells in neither provincial area → `unclassified`.
**M6.2 ranch_frac** = GVI where the 1 km cell is ≥50% covered by GVI landscape polygons (per-
polygon fraction = Σ PCT_OF_POLYGON over ranchland site types ÷ 100; native upland types +
tame pasture/hay, irrigated and not; lentic/lotic/crop/rural/developed/urban/pits excluded;
rasterised at 100 m, block-averaged to 1 km), else AAFC ACI 2024 (30 m; classes 110 grassland,
122 pasture/forages, 50 shrubland → binary → `gdalwarp -r average` to the AB grid; ACI 0 =
nodata). Threshold 0.5 for the class; 0.3/0.7 sensitivity reported. The GVI→ACI seam is
disclosed with the GVI-covered cell count and northern limit.
**M6.3 AOI-2** = SRP zones `Zone == "Nature First"` ∩ AB PU, minus the parent PA mask = the
novel area (~440 km² by the shapefile; identity-checked against the "Proposed Conservation
Area A/B" polygons). SRP planning-area context and PLUZ-vs-lock overlap reported.
**M6.4 D-AB6 preparation**: `dist_to_pa_km.tif` = Euclidean distance (1 km cells) to the nearest
locked cell on the PARENT grid (BC parks count); discretionary land by distance band
(0–5/5–10/10–20/>20 km) printed as the extent-share null for the tabled adjacency reading.
**M6.5 Outputs** → `data/derived/` (tenure_class, ranch_frac, gvi_coverage, dist_to_pa_km,
aoi_nfz_novel; gitignored, regenerable), `spec/tenure_shares_v1.{csv,json}` (tracked),
`analysis/c4_aoi/aoi_areas.csv`, `figures/ab_tenure_classes.png`.

## M7. Gates AB-1 / AB-2 build (2026-09-03; notebooks 06–08 written, PENDING-RUN)

**M7.1 AB-1 artifact set** (`06_ab1_anchors`): per (formulation, level) an ENGINE binary anchor
(Gurobi, opt_gap 1e-4, NumericFocus; `anchor/`, writes representation + run_summary) and a
Gurobi-proportion twin (`twin/`), for S0 at {A, B} × {585, 245} and S4 at A. The ssp245 weight
vectors are re-derived by 05 (`weights_ssp245`, constant intended influence via
`scenario_weights(layer_paths=…)` on the AB 245 realization) — the parent does this at its
freeze; here it is needed earlier because AB-1 solves both climate levels.
**M7.2 AB-2 estimator run** (`07_ab2_mga`): `mga_maxham_v1` unchanged (k=50, g=5%, MIPGap_dist
0.01, TimeLimit_iter 900, NumericFocus 2); the MGA anchor is re-solved from the compiled model
and asserted within 1e-3 relative of 06's engine certificate (parent 18 convention). Aggregate
band + guarded band (per-block floors at 0.95, `mga_block_floors`, blocks = config.BLOCKS as
frozen in scenarios_ab_v1.json) at BOTH levels; f(g) ∈ {2%, 10%} at A only (E4 mirror).
**M7.3 Verdict + nesting analysis** (`08_ab2_analysis`): verdict rule v2 with the parent's exact
rule text (hash asserted = v2_8db80fed1c702638); E14-analog with the floor formula's block
capture (Σ member captured fractions); nesting N on the GUARDED frequent tiers (F ≥ 0.70,
discretionary; aggregate reported); S4 pilot scored on m_soc's θ5 tail only (M4.3) with the
kink test at ±0.005; T1-analog = block captures per anchor. Record → `spec/gate_ab2_verdicts.json`.
**M7.4 Layout**: `runs/ab_l/<level>/<formulation_id>/` (level directory added to the parent's
flat layout because the same formulation solves at two budgets).

## M8. Gates AB-3 / AB-4 build (2026-09-03; notebooks 09–10 written, PENDING-RUN)

**M8.1 Freeze (`09_ab3_freeze`)**: 14 formulations = (S0–S5) × {585, 245} + s1x/s3x at 585, derived
by the parent 11 recipes on the AB stack at the PRIMARY budget level from 08's nesting verdict;
S4/crossed regime label = `theta<θ>_places` with the ladder's θ; weights cross-checked against
05's frozen S0–S4 vectors (585 and 245). Schema = parent §9 + AB columns (`config`, `extent_id`,
`mirror_spec_version`, `lock_rule`, `budget_semantics`, `budget_level`, `budget_cells`,
`budget_pct`, `floor_g`, `anchor_ref`/`twin_ref`/`mga_ref` for the reference formulation,
`pipeline_git_sha`, `pipeline_module_sha256`).
**M8.2 Code-provenance reading of the v0.4 rule**: the freeze records HEAD's SHA and asserts the
five pipeline modules (`config.py`, `leverage_core.py`, `ensemble_core.py`, `prioritizr_core.R`,
`mga_core.R`) are unmodified vs HEAD (module sha256s stored). Notebooks/specs may be dirty — they
are the record being written. Ethan must commit the pipeline edits (config AB entries,
leverage_core M3.3 fix, .gitignore) before freezing.
**M8.3 Ensemble runner (`10_ab4_ensemble`)**: per formulation at the primary level — engine anchor,
Gurobi-proportion twin, **k-best pool (portfolio 50 @ 5%, kept: the two-instrument contrast is
cheap at AB scale)**, MGA anchor (drift ≤ 1e-3 vs the engine certificate), aggregate sweep and
guarded sweep — i.e. the parent's 12 + 18 in one pass. Reference-formulation artifacts from
AB-1/AB-2 are reused by the per-artifact skip logic (same paths), never re-solved.

## M9. Gate AB-2 outcome — the vacuous nesting test and the tighter-g dial (2026-09-03)

**M9.1 Finding that forces the entry (R5.2–R5.5):** at g = 5% the guarded and aggregate frequent
tiers are empty (2 km² / 0 km²), so the D-AB5 v2 nesting statistic N = |core_B ∩ core_A| / |core_B|
is 0 by arithmetic (guarded against division by zero) — the frozen rule returns "B primary" without
evidence. The pre-registration did not anticipate an empty core. Escalated to chat per the
"anything specific/ambiguous" norm; recorded here before any amendment.
**M9.2 Mechanism (stated as method, not result):** with 32.9% of the extent locked and banked
shares of 24–71% per feature, the additions (≤ 17.6% of unlocked land) cannot move any block's
capture by 5%; the objective is nearly flat in the additions, so the 5% band admits complete
turnover (D ≈ 1) and the per-block floors never bind. This is the lock-conditional face of the
audit-space vs lock-conditional gap (spec §4) made extreme.
**M9.3 Amendment proposed (parent-sanctioned dial):** presentational band for the applied layer =
g = 2% (the parent's v0.13 ruling names tighter g as the sanctioned cluster-drawing dial); the 5%
estimand is kept and reported as measured. 07 patched to run g = 2% at level B (A already had it);
08 patched to report N at every band present at both levels and to flag the vacuous 5% test. The
0.80 threshold is unchanged. Decision pending in chat (`gate_ab2_reportback.md`).
**M9.4 RATIFIED (Ethan, same session): (a)+(b)+(c) → D-AB10.** Applied band g = 2% for EVERY
frequency product; 5% stays the estimand; nesting at 2%; primary level follows (B if vacuous).
**Deliverable definition (Ethan's directive): the per-formulation frequency surfaces of the
value-forward scenarios are first-class products, not a by-product of the ensemble F** — the AB-4
runner therefore sweeps every formulation at g = 2% in both semantics (aggregate + guarded) in
addition to the 5% estimand sweeps (4 sweeps/formulation, ~4 min each at AB scale); 11/12 produce
per-scenario tiers and clusters (director-package Act-2 analogue) at 2%. `manifest.csv` gains
`applied_band_g = 0.02`.
**M9.5 Nesting resolved at g = 2% (R5.8): N = 1.000 → level A PRIMARY.** 08's rule now reads: if
the 5% test is vacuous, apply the unchanged 0.80 threshold at the tightest band where both levels
have non-empty cores (g = 2%); if none, B by the realism default. The frozen verdict record was
updated to A with a dated note (re-running 08 reproduces it). Consequence for the applied
product: A's 2% tiers are the deliverable, with B's 404 km² tier drawn as the innermost
"survives even a 5k envelope" ring — the two-level design collapses into one nested map.
**M9.6 Ethan ruling (same session): LEVEL A ONLY; B SCRATCHED for now.** No level-B product,
ring, or column in the applied outputs; the B pilot (R4.3, R5.8) stays in the record as the
measured nesting result and can be revived by re-running 10 with `budget_level = B` if a tighter
envelope is ever wanted. 09/10 already operate at A; 11/12 are built for A alone.

## M10. Gate AB-4 analysis build (2026-09-03; `11_ab4_analysis` written, PENDING-RUN after 10)

**M10.1 Two bands, one notebook.** Estimand block (g = 5%, plain semantics = the parent's
`F_surface` convention): hierarchical F (one vote per formulation), spec bands, E1 bias vs the
anchor-only F, E2 definitional note, E3 variance shares on the 12 factorial formulations +
crossed contrast, E7 T1 (anchor captures with banked shares beside them; θ5-tail rates; gHM audit
on S3), E11 (anchor Jaccard + Δ(s,s′) reconstructed from captures with the 245 realization for
ssp245 formulations and EFGs at 1/27; diagonal self-check). Applied block (g = 2%, D-AB10):
ensemble F₂ in both semantics, every formulation's f₂ written as a GeoTIFF, climate pooling per
scenario (parent decision (g): pool iff frequent-tier Jaccard ≥ 0.80), tiers = core (F₂ ≥ 0.70) /
per-scenario value-forward tiers for S1–S4 (pooled f₂ ≥ 0.70 minus core; S0/S5/crossed to the
appendix) / opportunity (in ≥ 1 plan, not above) / never; coded tier raster.
**M10.2 C1 like-for-like:** parent `ensemble_v1/F_surface.tif` (5%, plain) clipped to AB
discretionary cells vs AB F₅ plain — Spearman on shared cells, frequent-tier overlap coefficient
(Jaccard supplementary); per-formulation anchors by overlap coefficient with the parent's S4/crossed
ids mapped `theta2 → theta3`; at 2% the reference formulation only (the parent has g02 there alone).
**M10.3 C4 + tenure + distance:** AOI capture = share of the core inside the AOI vs the AOI's
share of discretionary land (the null), plus mean F₂ / per-scenario f₂ inside; tenure split of every
tier from the 03 estimate (over-count disclosure carries); distance-to-PA bands of the core vs the
null (the tabled D-AB6 reading).
**M10.4 Clusters (D-AB7, provisional constants):** the parent's procedure unchanged (threshold
0.70 → closing r=1 → 8-connected components → minimum size → core subtraction for scenario
clusters), with AB-scale constants `MIN_KM2_AB = 10` (parent 100) and polygon simplification 500 m
(parent 2 km); minimum-size sensitivity 5/10/25/50 km² printed so 12 can set the constants with
disclosure. Register columns mirror T-D1 with AB-local block percentiles (over AB discretionary
land), representativeness = EFG classes present / 27, driver masks (m_soc θ5-tail, rare EFGs ≤ 1%
of PU, connectivity top-1%), tenure mix, % within 5 km of a PA, % in the NFZ, n formulations frequent.
**M10.5 Natural Subregions (2005)** added to `acquire.py` (REST, OGL-A) for the T-D4 analogue;
consumed by 12 once on disk.

## M11. Gate AB-5 report build (2026-09-03; `12_ab5_report` written, PENDING-RUN after 11)

**M11.1 D-AB7 constants set (disclosed):** display unit = 1 km cells (25 km² and 100 km² hex
variants rendered only for the how-to-read comparison; parent 250/800); minimum cluster 10 km²
(from 11's provisional constant; parent 100; 5/25/50 sensitivity in 11's tables); polygon
simplification 500 m (parent 2 km); deck picks top-6 core by area, top-2 per scenario
(presentational; register ships in full); band = 2% guarded (D-AB10). Never tuned to a cluster count.
**M11.2 Applied grammar mirrored:** (a)/(b) core pair recast per D-AB2 (additions-only view with
the estate MASKED / context view with the estate drawn + picks + inset F histogram, % area
annotated); value-forward small multiples with the core outlined and NFZ dashed ("alignment,
not assignment" call-outs when a pick lies ≥ 5% inside the zone); opportunity pair (union
membership + tier map + guardrail sentence with the R5 flatness statement); core star grid on
AB-local percentiles (EFG classes / 27); driver bars; tier-achievement (cumulative tiers incl.
the locked estate; block = mean of member captures, T-D3 convention; anchor reference band from
T1); **T-D4 analogue = tier area by Natural Region and Subregion (2005) + tenure by tier**; AOI
table (C4); agreement matrix (E11 Jaccard); deck outline + draft pptx.
**M11.3 Names** are placeholders: bearing from the nearest PA (≥ 25 km², inside the extent) +
Natural Subregion + latitude; Ethan/Tim rename before final render (parent decision (e)).
**M11.4 Not mirrored:** E17 one-pager (no leave-one-block-out solves at AB; representativeness
context reported in R2 instead); IPCA overlay (no declared proposals in the AB strip; the AOI
overlays carry the same language rule).


## M12. Gate AB-4 run notes (2026-09-08)

**M12.1 Provenance precision.** `pr_write_outputs` writes `run_summary.json` with jsonlite's
default 4 significant decimals, so `solver_provenance$objective` for the engine anchor and twin
are rounded (4.3313 for 4.3312626). 10's integrity cell compared the rounded twin against the
full-precision MGA anchor with a 1e-6 tolerance and printed VIOLATED for 7 formulations; the raw
values show twin == engine anchor at 4 decimals in every case. Tolerance widened to 1e-4 in the
notebook (cosmetic). The engine fix (`digits = NA` in `write_json`) is deferred so the pinned
modules stay identical to the freeze record (R6); logged here for the parent too, whose twin
comparisons carry the same 4-decimal limit.

## M13. Director package mirror (2026-09-08; `12_director_surfaces` + `13_director_figures` built, PENDING-RUN; supersedes M11)

**M13.1 Structure = the Y2Y-wide 19/20**, with the 2026-09-04/05 package rulings applied: votes with the
**12 elicited positions** (crossed hybrids out; the paper's F14 stays in 11); Act 2 pooled per scenario
(forced; the divergence check reported — S1 diverges at Jaccard 0.76); intactness a plain star axis;
representativeness = per-cell EFG-count percentile (classes / 27 reported beside it); 'F' not 'guarded F'
in director-facing text; complexes = deck picks; Natural Earth admin basemap; summary tiers map with
Act 2 split by owning scenario; climate axis kept as the refugia realization with by-future Act 1 pairs +
the two-way map; guarded/unguarded contrast paper-only.
**M13.2 Alberta constants (D-AB7, disclosed):** band g = 2% guarded (D-AB10); display at 1 km (a ~25 km²
hex how-to-read comparison only); clusters ≥ 10 km², complexes within 10 km single linkage (parent 100 km²
/ 25 km); polygon simplification 500 m; picks top-6 core / top-2 per scenario; level A only.
**M13.3 The alignment overlay = the Upper Smoky Nature-First zone (solid orange) + SRP planning area
(dashed orange) on every (a) panel**, in the exact role of the declared IPCA proposals in the Y2Y-wide
package, with call-outs on (b) when a pick lies ≥ 5% inside either, `pct_in_NFZ` / `pct_in_SRP_area`
columns in T-D1, and a T-AOI alignment table; language rule "alignment, not assignment" (C4).
**M13.4 T-D4 = tier area by Natural Region and Subregion (2005)** (acquired layer; the parent's is
pending an ecoregion layer). T-D5's "new half" denominator = the level-A additions share
(budget_pct_A − PA share = 0.118). E17 one-pager not mirrored (no leave-one-block-out at AB).
**M13.5 Names** are the parent's placeholders (bearing from the nearest PA ≥ 25 km² in the extent or the
nearest AOI + lat/lon tag); Ethan/Tim rename before final render.

## M14. Spec restore + re-pin to the parent's closed scope (2026-09-14)

**M14.1 Spec file restored.** `alberta_prioritization_spec.md` was found truncated to its title and status line (3 lines) in the
working tree AND in HEAD (committed 2026-09-08, `d4c789b`); the last full version is `77d8713` (v0.4.6, 164 lines). Restored from
that commit, the v0.4.7 delta (director-package mirror build record; M13) re-applied from this log, then re-pinned as v0.5. The
truncation is recorded in the spec changelog; nothing in the logs was lost.

**M14.2 Mirror re-pinned v0.14.1 → v0.17.3 (parent scope CLOSED, Ethan 2026-09-14) + package spec v1.6/v1.7.** Absorbed, in
order: v0.15 (12 design formulations are the primary denominator; crossed diagnostics non-voting and not re-solved), v0.16/.16.1
(E18 closed; no further solves; package value-first), **v0.17–v0.17.3 (rule R0 + the EFG curation; rarity-scaled targets from the
buffered regional window; the necessity test E19; manifest v3.1; M4.31 band-width disclosure)**, package v1.7 (Act 1
representativeness = window-rare presence; adequacy-pin captions). What stays NOT mirrored: E17 (no leave-one-block-out solves at
AB), E18 (dose arms are parent evidence; caveat text carried), E12 (instrument bracket).

## M15. The curated block on Alberta, window targets, manifest v3.1 (2026-09-14; `09b_ab_curation_freeze_v3` built, PENDING-RUN)

**M15.1 D-AB11 — the curation is INHERITED, not re-decided.** Rule R0 (purpose relevance, map validity, the 330 km² grain floor,
the F2.9 utility drop, the TF1.6+TF1.7 and S1.1+SF1.1 merges) is a property of each class's GET map, decided on the parent
(M2.11 there) and applied to the Alberta block by the parent's 11b: 27 present → 15 retained → **13 features** in
`input_data/aligned_stack_ab/iucn_efg_v3/`. On Alberta the four classes that pinned the v1 core (R7.9–R7.11) all leave: F2.10 (rule
A, point record), F3.5 and SF2.2 (rule C, anthropogenic), F2.9 (utility). 09b re-applies the extent-relative parts (rule A's 1%
envelope threshold, rule B's grain floor, the boundary-proximity check R0 iii on the Alberta study boundary) as a DISCLOSURE only
and asserts the block folder equals the inherited set. The block card v3 (rare-attainable count, ≤1%-footprint companion, leverage,
banked share) is re-measured on the 13 (`spec/v3.1/efg_block_card_v3.csv`); 02's v1 audit record stands.

**M15.2 D-AB12 — targets from the ALBERTA extent buffered by 250 km.** The parent's v0.17.3 rule ("each class's footprint within the
study extent buffered by 250 km, zonal count on the GET archive maps; 100/500 km sensitivity; log-linear Rodrigues anchors
1,000 → 250,000 km², floor 0.10") applied to this extent: window = `data/ab_extent_v1.gpkg` buffered in Albers metres. Rationale:
a regional plan's rarity is judged in its own region (the parent's own wording); the parent's +250 km targets for the same 13
features are written beside Alberta's in `spec/v3.1/efg_window_footprints.csv` / `efg_targets.json` (`parent_targets_same_features`)
so the deviation is one column wide. "Rare" for the Act 1 representativeness layer and the T-D1 driver = ≤ 1% of the Alberta
window (`rare_window`). ALTERNATIVE not adopted: inherit the parent's Y2Y-window targets verbatim (would judge Alberta's rarity
against a window centred on BC and the US Rockies). **Flagged for Ethan's confirmation before 09b runs (one constant: the window
polygon).**

**M15.3 Manifest v3.1 (`spec/manifest_v3.1.csv` + `.sha256`; `spec/v3.1/` records).** 12 design rows (s1x/s3x diagnostic, not
re-solved — parent v0.15/v0.17; the E3 crossed contrast keeps the v1 record as evidence); weights re-derived on the AB stack via
`lc.scenario_weights` and asserted equal to the v1 freeze (EFGs sit outside the block accounting); EFG targets appended to every
`target_vector` by feature name; new columns `role`, `manifest_version`, `efg_block_version`, `efg_block_sha256`, `efg_features`,
`efg_target_rule`, `supersedes`, `trigger`, `applied_band_rule`; `anchor_ref/twin_ref/mga_ref` empty (the reference formulation is
re-solved too — its AB-1/AB-2 artifacts were on the v1 block); code provenance as M8.2 (commit `config.py` first — it gained
`ab_paths()`). Write-once guard (kept byte-identical once frozen). v1 (`spec/manifest.csv`, `runs/ab_l/`, `analysis/ab4/`, the
2026-09-08 package archived to `director_package/_superseded_v1_artifact_block/`) stays byte-identical: supersede, never delete.

**M15.4 One version switch.** `config.ab_paths(version)` mirrors `config.y2y_paths()` on the same `Y2Y_VERSION` (v3.1 → `runs_v3.1/ab_l/`,
`spec/manifest_v3.1.csv`, `spec/v3.1/`, `analysis/ab4_v3.1/`, `figures/v3.1/`, block `iucn_efg_v3`). Every AB notebook from 10 on
reads its paths through it; the R notebooks refresh `aligned_stack_ab/manifest.json` from the ACTIVE `config.EFG_SUBDIR` and assert
the ingested block matches VERSION. `Y2Y_VERSION=v1` reproduces the frozen run.

**M15.5 Ensemble (10) on v3.1:** anchors + LP twins + MGA at BOTH bands (g = 5% and 2%, plain and per-block-floor guarded) for the 12
formulations; **no k-best** (the E5 by-product, discharged in the parent v0.10; the v1 pools stand as the uniqueness record).
`formulation_meta.json` records z* and the absolute band widths at 5% and 2% (the parent's M4.31).

## M16. The applied band under the curated block — rule D-AB13; the necessity test (E19) mirror (2026-09-14; 11 patched, 11b/11c built)

**M16.1 D-AB13 — the applied band is DECIDED BY RULE in 11, not carried over.** D-AB10 chose g = 2% because the 5% band was flat on
the v1 block (D ≈ 1, empty frequent tier, guardrails inert — a representativeness-artifact plateau, R7.9–R7.11). On the curated
block the mirror is the parent's guarded g = 5%; the D-AB10 exception applies only if the flatness recurs: **applied band = 5%
guarded unless the 5% guarded ensemble frequent tier (F ≥ 0.70) is below 100 km² (1% of the additions budget), then 2%.** Both bands
are solved by 10, so the decision is a read; 11 records it (`gate_ab4_summary.json: applied_band_g, applied_band_rule,
freq5_guarded_km2`) and 12/13 consume it. Outputs are named `*_applied*` so the band can change without renaming. **Flagged for
Ethan's confirmation (the 100 km² flatness threshold is the one free constant).**

**M16.2 M4.31 mirrored:** 11 tabulates z* per formulation and the absolute 5%/2% widths against the v1 block
(`analysis/ab4_v3.1/tables/band_width_abs.csv`); any claim phrased "within g of optimal" ships with the absolute width beside it.

**M16.3 E11 reconstruction with per-feature targets.** The cross-objective suboptimality Δ(s,s′) now scores each EFG's shortfall
against its own target ((1/n)·max(0, t_e − c)/t_e), as the parent's 13 does under v3.1; under v1 (t = 1) this reduces to the old
form. The Δ-diagonal self-check remains the guard.

**M16.4 C1 like-for-like stays block-matched:** the parent surfaces are read at the SAME version (`config.y2y_paths(VERSION)`:
`runs_v3.1/ensemble/F_surface.tif`, its anchors); the 2% S0 probe (a v1-only artifact on the parent) is skipped under v3.1; **C1b
added** — the parent's guarded F (its director package at the same version) vs Alberta's applied guarded F.

**M16.5 The necessity test (E19) mirrored as `11b_ab_e19_solves` (R) + `11c_ab_e19_analysis` (py), pre-stated:** T1 = the
adequacy-forced set from the member rasters at the APPLIED band (guarded = the package basis; unguarded beside it): a class whose
capture is 1.0 in every member of a formulation forces every unlocked cell of the class to f = 1 by arithmetic; ensemble-forced =
forced in all 12; the core, each scenario tier and each deck pick partitioned into forced / multi-claim (≥ 2 non-EFG themes
top-30%) / other. T2 = leave-EFG-out anchors ×12 (every EFG multiplier 0; ~1 s each at AB scale); core cells absent from every
no-EFG anchor are EFG-necessary; agreement with T1 reported. T3 = the no-EFG ensemble at the applied band, run ONLY if the
ensemble-forced share of the core exceeds 50% (`spec/v3.1/e19_gate.json`; ~1 h at AB scale). Pre-stated expectation: a SMALL forced
share. Deck rule: clusters ≥ 50% forced are captioned ADEQUACY PIN (pinning class named); T-D1 gains `pct_adequacy_forced`.

## M17. Director package mirror re-pinned to package spec v1.6/v1.7 (2026-09-14; 12/13 rebuilt, PENDING-RUN)

**M17.1 Value-first structure (v1.6):** Act 1 = where the values are (per-theme top-30% masks at 1 km, `value_top30_*.tif`, plus the
0–5 convergence count; representativeness = presence of a window-rare class, D-AB12; intactness sixth, not counted) → Act 2 = core
irreplaceability (the old Act 1) → Act 3 = scenario irreplaceability with the BINDING value | tier pairing per theme (the old Act 2;
AOIs on the value panel) → hinge cross-tab (convergence × reliability class) → Act 4 = the measured gap (`value_gap.tif`, T-D6,
T-D6b, union membership). Internal act identifiers in 12's registers keep the v1.1 values; `act_v16` carries the display numbering
(`dc.ACT_DISPLAY`), as in the parent. Figure files carry the v1.6 act numbers (`act2_core_1km.png`, `act3_<key>_1km.png`,
`act4_opportunity.png`, `hinge_convergence_x_F.png`, `act1_values_1km.png`, `act1_value_convergence_1km.png`).

**M17.2 v1.7 additions:** the E19 columns in T-D1 (`pct_adequacy_forced`, `adequacy_pin`, `adequacy_pin_class`) with the ADEQUACY-PIN
caption on stars and the picks table; the E19 partition table + appendix slide; the biodiversity finding-as-product line uses
Alberta's own capture range over all guarded plans; the carbon caveat is stated in Alberta terms (m_soc t = 0.772 at the ladder)
and attributed to the parent's E18 (not re-measured).

**M17.3 Unchanged Alberta rulings:** 1 km display (25 km² hex for the how-to-read slide only), 10 km² clusters / 10 km complexes /
500 m simplification (D-AB7), the Upper Smoky overlay in the IPCA role (M13.3), T-D4 by Natural Region/Subregion (M13.4), tenure
by tier (D-AB8 disclosure), placeholder names (M13.5).

**M17.4 Runner.** `run_v31.sh` mirrors the parent's: 09b → 10 → 11 → 11b → 11c → (T3 if gated) → 12 → 13, in place, resumable, logs
in `logs/` (gitignored).

## M18. Comb of the parent, 2026-09-15 — methods frozen, outputs moving; what the mirror absorbs now and what waits

**M18.1 Split.** Since the v0.5 re-pin the parent changed nothing in the formulation, the estimand, the block or the solver
standards (study plan still v0.17.3, package spec still v1.7 with logged deviations M4.32–M4.33). Methods-side additions:
(a) M4.32 — the package is built on v3.1 ONLY, and the E17 leave-one-theme-out anchors were re-solved on the curated block
at S0 (18b's E17-T3 cell); (b) the necessity test came back EMPTY on the parent (R10.21: no adequacy-forced land, T3 not
triggered; the EFG-out latitude shift fell from +2.11° to +0.02–0.22°); (c) a developed-land PU mask was sized and PARKED
(R10.23 — a scoping choice, not adopted). Output-side (M4.33 + addenda): regional deck picks, "naturalness", T-D7
consequences with reference rows, acts 0–3, the table spec, two 1 km Act 1 maps, the basemap/hillshade port, the wide slide
layout, cluster locators, `director_plot.py` as the one asset codebase, 19/20/21 = tiers-and-clusters / the record / the
curated presentation set. Ethan (2026-09-15): the methods spec is set; only the Y2Y outputs are still changing.

**M18.2 Absorbed on the methods side.** 11b gains the parent's E17-T3 cell verbatim in Alberta terms (five S0 anchors at
level A: four PROACT block-outs at 1e-4, the EFG-out by the T2 convention; seconds each; `runs_v3.1/ab_l/A/e17_t3/`); 12
records the shifts (`E17_shifts.csv`, `summary.json: e17`) as a T-D line — the E17 one-pager stays not mirrored (M11.4;
the 2° southern-lean question is Y2Y-wide). T2 leave-EFG-out anchors keep the PRE-REGISTERED 1e-4 gap (seconds here) and
mirror only the parent's 20-minute cap (the parent relaxed to a 1e-3 witness gap for cost on 1.27 M cells — M4.28
addendum); disclosed. The `dc.BLOCK_AXES`/`STAR_AXES` rename (intactness → naturalness) flows into 11's cluster register
automatically (column `pct_naturalness`).

**M18.3 Absorbed on the record side (settled M4.33 rules), notebooks renamed to the parent's:** `12_tiers_and_clusters` (was
12_director_surfaces) — deck picks grouped a second time into REGIONAL clusters by single linkage at **`PICK_LINK_KM` = 30 km**
(3× the 10 km complex link, as the parent's 75 km is 3× its 25 km; D-AB7, disclosed) and numbered north → south, the core
first, then each scenario's picks (`dc.group_picks` + `dc.absorb_complexes`; `picks_raw_complexes.csv` keeps the complexes);
T-D1 lists the deck picks first, then every other kept complex; `dc.ValueRatios` (the parent stack IS the AB stack on this
grid; the denominator is Alberta's allocatable land) → `ratio_*` columns and **T-D7** with three REFERENCE rows — existing
protected areas, the Upper Smoky Nature-First zone's unprotected part (the IPCA analogue), the SRP planning area's unprotected
part; acts 0–3 in every label (`dc.ACT_TITLE`/`ACT_DISPLAY`). `13_figures` (was 13_director_figures) — file names, titles,
tier labels and the deck follow acts 0–3; stars titled "Cluster N"; "naturalness" everywhere; the objectives table (T-D0,
Alberta rows: level-A budget, m_soc 0.322/0.772, 13 curated features, the tenure line) and both T-D7 tables render to the
Y2Y table spec through `director_plot.spec_table_png` (transposed; red → green across each row, 1.0× the hinge; reference
column labels from 12's names); every figure takes `director_plot.SPEC_RC`. `run_v31.sh` updated.

**M18.4 Deferred until the parent's presentation layer settles (Ethan is iterating it):** the `director_plot` asset functions
(`load()` is hardwired to the Y2Y grid, package, IPCA layer and frame: basemap + hillshade, the wide slide layout with insets,
cluster locators, `STYLE`), and an Alberta `14_director_outputs` for the curated presentation set. Plan when it settles:
parameterize `director_plot.load()` on (grid, package, manifest, alignment overlay, frame) so BOTH packages draw from the
one codebase (Ethan's asset rule), and fold the Alberta-specific rows/labels in as parameters (`values_rows`, the T-D7
reference labels). The Alberta record figures keep their present 1 km cartography (admin lines, 53°N, AOIs) meanwhile. The
GLO-90 hillshade already covers the Alberta frame (`hillshade_y2y_300m.tif`, same grid), so no new basemap data is needed.

*Last updated 2026-09-15 (M18).*
