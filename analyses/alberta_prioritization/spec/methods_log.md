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

*Last updated 2026-09-03.*
