# Alberta Y2Y Prioritization — Results Log (living, binding)

Cumulative results record for analysis 3 (`analyses/alberta_prioritization/`). Same convention
as `analyses/y2y/spec/results_log.md`: every quantitative result destined for the applied report
(or the applied paper) gets an R-numbered entry with run provenance (notebook, run folder,
`run_summary.json` / manifest sha) in the SAME session it is measured; corrections supersede,
never delete. Pre-registered hypotheses H-AB1–H-AB5 and comparisons C1–C4 are scored here.

## R0. Pre-run facts inherited from the parent (for the AB comparisons)

- Parent lock-in: 191,029 locked of 1,272,914 PU (15.0%); budget RHS 381,874; discretionary
  cells 1,081,885; discretionary selected 190,845 → realized fill rate **17.6% of unlocked**
  (= the D-AB5 anchor). Parent `results_log.md` R9.8 erratum: earlier "1,082,069" was a swap.
- Parent characterization (C2 baseline): gHM intactness leverage 0.042 (R3-inexpressible);
  m_soc concentrated-satiating, t=0.332; biomass diffuse-linear; 36/40 EFGs rare-attainable
  (`analyses/y2y/audit/audit_objects/feature_characterization.csv`).
- Parent plateau geometry (H-AB4 baseline): D=0.953, C=0.020 at g=5% (S0 reference); D_s
  0.809–1.000 across formulations.

## R1. Gate AB-0a (i) — extent, stack, lock accounting (01 run 2026-09-03 18:05 UTC)

Provenance: `spec/ab_extent_v1.json`, `input_data/aligned_stack_ab/_build_meta.json` (parent
layer sha256s inside), `input_data/aligned_stack_ab/manifest.json`, `figures/ab_extent.png`,
`data/ab_extent_v1.gpkg`.

**R1.1 Extent.** AB PU = **85,133 cells (85,133 km²) = 6.7% of the parent's 1,272,914**.
Composition: 84,195 inside the unbuffered Y2Y boundary + **938 in the inherited 20 km buffer
(1.1%, disclosed, kept)**. Inherited non-PU holes: 3,420 of the 87,615 grid cells inside
Alberta ∩ Y2Y boundary (3.9%) and ~23,000 of the buffer cells are NOT parent PU — in both cases
because the irrecoverable-carbon layers do not cover them (biomass valid on 76 of 24,092 hole
cells; gHM valid on all) — the parent's known biomass-footprint constraint, inherited unchanged
(D-AB1). Extent polygon (Alberta ∩ buffered study area) = 109,249 km², so the PU covers 78%
of it. [01 §1; ab_extent.png]
**R1.2 Stack.** 9 continuous layers + 2 climate realizations + cost + PA mask written on the
parent grid. **Dust re-run zeroed 0 cells in every layer** (the parent's dust pass already
removed all residue; AB-relative thresholds found nothing further). Manifest: 8 continuous +
27 EFG features, grid identical to the parent, PU from the AB cost layer = 85,133 (asserted).
Cell-exactness asserted (0 differing cells on m_soc / biomass / macrorefugia). [01 §2, §4]
**R1.3 EFG contraction (H-AB2, first reading): 27 of 40 EFGs survive; 13 have no occurrence in
the AB PU** — F1.1, F1.2, F1.4, F1.6, F2.1, F2.2, F2.3, F2.6, F3.4 (nine freshwater/wetland
classes), S2.1 (subterranean), T3.4, T5.4, TF1.2. Rare-attainability/unsaturation of the 27
is measured in 02. [_build_meta.json]
**R1.4 Lock accounting — D-AB5 escalation FIRED as pre-registered.** Locked **27,972 cells =
32.9% of the AB extent** (parent: 15.0%). **30×30 lens: the Alberta strip is ALREADY above 30%
protected** — a Tim-facing headline; the live questions are composition and additions (spec §3).
Inherited 30%-total referent: budget 25,540 < locked 27,972 → **INFEASIBLE** (lb=1 exceeds RHS),
exactly the case §3 named. [01 §3]
**R1.5 Effective budget frozen.** X = **0.1764** derived in-notebook from the parent's artifacts
((381,874 − 191,029)/(1,272,914 − 191,029); asserted against 1,272,914 / 191,029). Budget =
27,972 + 0.1764 × 57,161 = **38,055 cells = 44.7% of the AB extent; additions 10,083 km²**.
Referents printed beside it for disclosure: 15%-of-unlocked → additions 8,574 km² (40.2%
extent); 15%-of-total → 12,770 km² (47.9%). The anchor sits between them; the choice moves the
additions budget by −15% / +27%. Applied by `pr_override(budget_pct=0.4470)` in every solve
notebook. [ab_extent_v1.json]
**R1.6 Geography (from the map, qualitative — quantified at 02/AB-5):** the locked estate is the
contiguous mountain-park spine (Jasper–Banff–Kananaskis–Waterton + Willmore/Kakwa); the
discretionary land is the foothills/parkland band east of it plus the **entire northern
boreal-foothills tip north of Willmore/Kakwa with essentially no protection** — the Upper
Smoky Sub-Regional Plan / Nature-First Zone geography (AOI-2).

## R2. Gate AB-0a (ii) — characterization audit (02 run 2026-09-03; zero solves)

Provenance: `audit/audit_objects_ab/` (feature_characterization.csv = the frozen AB T2,
feature_audit.npz, audit_constants.json n_pu 85,133, supplementary_columns.csv,
efg_supplementary_columns.csv), `audit/feature_cards_ab/` (10 pages),
`analysis/c2_audit_compare/c2_characterization_compare.csv`, `spec/gate_ab0a_verdicts.json`,
`figures/F8_ab_marginal_density_trajectories.png`. Audit at the parent's 30%-of-extent
convention; leverage at the effective 44.7% budget alongside.

**R2.1 AB characterization table (C2, leverage y2y → AB; class y2y → AB):**

| feature | lev y2y | lev AB | lev @44.7% | θ-target AB | class AB | lever |
|---|---|---|---|---|---|---|
| carbon m_soc | 0.884 | **0.916** | 0.953 | **0.322** (y2y 0.332) | concentrated-satiating | target |
| carbon biomass | 0.801 | 0.606 | 0.702 | 0.003 | diffuse-linear | weight |
| connectivity | 0.461 | **0.523** | 0.594 | 0.022 | diffuse-linear | weight |
| macrorefugia (1/v) | 0.422 | 0.309 | 0.358 | 0.000 | diffuse-linear | weight |
| corridors | 0.263 | **0.100** (= λ, marginal) | 0.114 | 0.000 | diffuse-linear | weight |
| AOH birds | 0.232 | 0.116 | 0.125 | 0.000 | diffuse-linear | weight |
| AOH mammals | 0.181 | **0.070** | 0.080 | 0.000 | **low-contrast-inexpressible (FLIP)** | none (disclosed) |
| gHM intactness | 0.042 | 0.086 | 0.094 | 0.000 | low-contrast-inexpressible | none (disclosed) |
| EFG block | 36/40 rare | **20/27 rare, 7 unsaturated** | — | — | locked adequacy foundation | — |

One class flip (mammals → inexpressible). Corridors sits exactly on λ = 0.10 and passes by the
rule's ≥ (disclosed as marginal). Transform screening: no concave transform admissible anywhere;
log1p would push corridors, birds and mammals below the floor; 1/v remains the best macrorefugia
orientation (0.309 vs raw-avoid 0.286, vmax−v 0.188). [02 R1/T2 cells]
**R2.2 H-AB1 (contrast recovery) — NOT SUPPORTED on its strongest expectation, and largely
refuted.** gHM doubles (0.042 → 0.086) but stays under λ; S5 remains inexpressible at AB extent
(0.094 even at the effective budget). Only connectivity gains (+0.062); macrorefugia (−0.113),
birds (−0.116), mammals (−0.111) and corridors (−0.163) LOSE contrast. Scale reading: the four
"flat" Y2Y layers are not flat because the extent is large — three of them are flatter inside
Alberta than across Y2Y. [gate_ab0a_verdicts.json]
**R2.3 H-AB2 (EFG contraction) — SUPPORTED:** 27/40 present, 20 rare-attainable, 7 unsaturated
(T6.4 0.576, F2.4 0.848, F3.2 0.611, SF2.1 0.613, T2.1 0.369, SF1.2 0.551, T7.5 0.659) vs the
parent's 4/40. Four EFGs are ≥90% banked in the locked estate (T6.1 0.980, S1.1 0.962, SF1.1
0.962, T6.2 0.916 — alpine/ice/subterranean classes); none is entirely inside it.
**R2.4 H-AB3 (carbon regime) — m_soc's classification is scale-STABLE:** concentrated-satiating
with θ-target 0.322 (parent 0.332) over a 5.2% shelf (parent 4.1%); leverage rises to 0.916.
Biomass stays diffuse-linear (θ-target 0.003 — its tail nearly vanishes inside Alberta).
**R2.5 H-AB5 (banked pre-satisfaction) — SUPPORTED, and it lands on carbon, not on the alpine
features predicted:** banked shares — m_soc **0.714**, macrorefugia 0.456, connectivity 0.385,
corridors 0.360, intactness 0.356, mammals 0.325, birds 0.298, biomass 0.239 (parent 12–19%).
**m_soc's 0.322 target is PRE-SATISFIED by the locked estate alone (residual 0)**; the zero-solve
window proxy puts its co-capture + banked floor at **0.765**, so any carbon target below that is
a decoration here (parent E10). No other continuous feature is pre-satisfied (targets 1.0).
Highest residual pulls: biomass 0.761, birds 0.702, mammals 0.675 — foothills-concentrated
features, as H-AB5 predicted for the additions driver.
**R2.6 θ-relaxation lookup on the AB archive (zero-solve; for the S4-analog decision):**
m_soc target at θ5/3/2/1.5/1.2/1.0 = 0.322 / **0.642** / **0.772** / 0.848 / 0.877 / 0.892
(area 5.2 / 13.2 / 18.5 / 22.9 / 25.0 / 26.4%). Parent: 0.332 / 0.552 / 0.699 / 0.783 / 0.832 /
0.862. **The parent's S4 recipe (θ 3×) gives 0.642 < the 0.765 floor → would not bind; θ 2× gives
0.772, barely above; θ 1.5× gives 0.848.** Biomass θ3/θ2 = 0.108 / 0.370.
**R2.7 D-AB5 disclosure at effective budget:** cap_max rises 0.33→0.49 (intactness), 0.59→0.75
(connectivity), 0.92→0.97 (m_soc) between the 30% audit convention and the 44.7% solve budget;
leverage ordering unchanged. [02 T2 cell]

**R2.8 Tenure estimate (03 run 2026-09-03 19:08 UTC; D-AB3 equation, no disposition layer —
private classes are OVER-counts by the crown-lease share, disclosed).** Provenance:
`spec/tenure_shares_v1.{csv,json}`, `data/derived/tenure_class.tif`, `data/provenance.json`.
Provincial layers on the extent: Green Area 68.9%, White Area 11.2%, neither 19.9% (= the
federal national parks, absent from the provincial layer; 16,786 of those 16,903 cells are locked).
Active Crown Land Reservations cover 41.8% of the extent (Green-Area notations mostly); PLUZ 12.6%.

| class | km² | % extent | % discretionary |
|---|---|---|---|
| pa_locked | 27,972 | 32.9 | — |
| crown_green | 47,716 | 56.1 | **83.5** |
| crown_white_ind (reservation/PLUZ inside the White Area) | 1,992 | 2.3 | 3.5 |
| private_presumed (non-ranch) | 1,943 | 2.3 | 3.4 |
| **private_ranchland** | **5,393** | 6.3 | **9.4** |
| unclassified | 117 | 0.1 | 0.2 |

**The discretionary land is 87% crown.** The OECM track (private ranchland) is a 5,393 km² pool,
9.4% of discretionary land, concentrated in the southern foothills fringe; ranch_frac threshold
sensitivity 0.3 / 0.5 / 0.7 → 5,973 / 5,393 / 4,836 km². Mean distance to the nearest PA:
private ranchland 17.8 km vs crown_green 26.2 km (discretionary overall 25.4 km).
**R2.9 Ranchland-cover seam (M6.2).** GVI covers 6,949 cells (8.2% of the extent, the southern
grassland/parkland inventory area); mean ranch_frac on discretionary cells is **0.88 where GVI
exists vs 0.07 where ACI 2024 is the source** — the two sources are not exchangeable (GVI maps
rangeland by construction; north of it the White Area is cropland/forest with sparse ACI grassland).
private_ranchland splits 5,010 km² (GVI) / 383 km² (ACI). The seam is a property of the sources,
reported, not smoothed.
**R2.10 AOI-2 (Upper Smoky Nature First) + the distance null (M6.3–M6.4).** Nature First zone in
extent 438 km²; **novel (minus PA) = 436 km² = 0.76% of discretionary land**, entirely
`crown_green`; identical to the "Proposed Conservation Area A/B" polygons (the press 2,200–3,200
km² figures include Willmore/Kakwa). Upper Smoky SRP planning area in extent 12,685 km², of which
10,028 km² unlocked (17.5% of discretionary land) — the whole unprotected northern tip. Distance-
to-PA null over discretionary land (for the tabled D-AB6 reading): 0–5 km 16.3%, 5–10 km 13.8%,
10–20 km 19.0%, >20 km 50.9%. PLUZ vs the parent lock: see R2.11.
**R2.11 PLUZ vs the parent PA compilation (spec §8 row 3 completeness information).** 17 PLUZs
intersect the extent, 10,744 km², of which only **361 km² (3.4%) are inside the lock** — the
parent PA layer does NOT treat Public Land Use Zones as protected (correctly: PLUZs are
recreation/access-management zones, not conservation designations), so they sit in the
discretionary pool as `crown_green`. Largest: Upper Clearwater/Ram 1,893 km² (2% locked),
Livingstone 1,406 (0%), Ghost 1,323 (8%), Job/Cline 1,295 (0%), Kananaskis Country 1,136 (1%),
Kiska/Willson 1,100 (1%); only Dormer/Sheep (108 km², 93%) and Cataract Creek (460, 19%) overlap
the lock materially. Whether any PLUZ carries a conservation-grade designation Y2Y would count
toward 30×30 (e.g. the Castle Special Management Area, 13 km² here) is a Tim question for AB-5;
the CPCAD cross-check (manual download) remains open.

## R3. Gate AB-0 — a-series analogs + scenario derivation (04/05 run 2026-09-03; level A)

Provenance: `runs/ab_l/gate0/<arm>/run_summary.json` + `portfolio_representation.csv`;
`spec/scenarios_ab_v1.json`, `spec/ab_budget_levels_v1.json`.

**R3.1 Solve cost.** Every arm ~1 s on Gurobi (root relaxation integral, 1 node) — the AB
problem (85,133 PU, 35 features) is trivial; compute is not a constraint anywhere downstream.
**R3.2 Captures vs targets (w = t):** a0 control m_soc **0.867** / biomass 0.413; a1 (m_soc t
0.322) **0.744** — ABOVE target by +0.42, the pre-satisfied target is inert (parent E10 observed
in the wild); a5 (m_soc t 0.772 = θ 2×) **0.7720 — AT THE KINK, binds**; a4 (connectivity t = w =
0.80, unreachable) reproduces a0 EXACTLY — common objective 4.20025 vs 4.20025, Jaccard 1.000,
0 differing cells (the raw objectives differ by exactly the 0.2 constant an unreachable target
contributes). G0 PASS on every criterion as re-read for a pre-satisfied target (M5.2).
**R3.3 The floor, measured (M5.7).** Co-capture + lock-in floor for m_soc at level A = a1's
zero-pull capture **0.744** (zero-solve proxy 0.765 was 2 pts high; a0's 0.867 includes carbon's
own pull and is not the floor — the first-run ladder stop and its correction are in M5.7).
Ladder: θ 2× 0.772 / 1.5× 0.848 / 1.2× 0.877 → **S4 target = 0.772 (θ 2×)**, margin 0.028,
binding certified by a5.
**R3.4 Reallocation (a1 − a0, pts):** m_soc −12.3 (the freed claim), biomass **+4.9**,
connectivity +2.0, birds +0.8, mammals +0.4, macrorefugia −1.0, corridors −0.1, intactness 0.0,
EFG mean +0.1. Same signature as the parent's Gate 0: the weight-levered biomass pool absorbs
most of the released area (the leak the block accounting exists for).
**R3.5 Carbon split diagnostic (parent Gate-1 rule, AB reading):** biomass θ5-tail = **42 cells
(0.049% of PU, cutoff 129.2 t/ha)**, m_soc tail 4,384 cells (5.15%, 267.8 t/ha) — both match the
frozen AB T2. a1 captures 42/42 tail cells (mass 1.000; 0 inside the m_soc tail → 100%
independent) → rule says mass-proportional split; **AB carbon mass split SOC 67.5% / biomass
32.5%** (parent 74.2/25.8). Disclosed as near-vacuous at 42 cells.
**R3.6 Frozen scenario family (`scenarios_ab_v1.json`, mean-1 normalized, AB 30% audit
convention).** S0: macrorefugia 1.038, connectivity **0.306**, corridors 1.598, m_soc 0.219 (t
0.322), biomass 0.172, birds 1.386, **mammals 2.281 (D-AB9: R3-inexpressible, weight inert,
disclosed)**; ssp245 re-derivation moves every weight < 9% (macrorefugia 0.954). S4 (carbon ×2,
t 0.772): m_soc 0.587, biomass 0.464. Compared with the parent S0 (refugia 1.460 / conn 0.669 /
corridors 1.171 / m_soc 0.465 / biomass 0.199 / birds 1.329 / mammals 1.708): Alberta's
connectivity weight halves (its swing doubled) while corridors' rises (swing collapsed to λ).
**R3.7 Climate axis on AB:** leverage 245 = 0.341 [0.159, 0.500] vs 585 = 0.309 [0.169, 0.478];
top-30% Jaccard between levels **0.629** (parent 0.574) — the two realizations agree slightly
more inside Alberta than across Y2Y.
**R3.8 Budget levels frozen (D-AB5 v2):** A = 38,055 cells (44.7%; additions 10,083 km²), B =
33,014 cells (38.8%; additions 5,042 km²); nesting threshold 0.80.

## R4. Gate AB-1 — anchors, twins, S4 pilot (06 run 2026-09-03)

Provenance: `runs/ab_l/<level>/<formulation_id>/{anchor,twin}/run_summary.json` (+
`artifact_meta.json` with the exact weight/target vectors).

**R4.1 Certified anchors (Gurobi binary, gap 0.0000%, ~1 s each):** S0-585 A 4.4609 / B 5.0220;
S0-245 A 4.4522 / B 5.0130; S4-585 A 4.2883. Every Gurobi-proportion twin equals its anchor to
the 4th decimal (LP ≤ MILP holds; the relaxation is TIGHT at this scale — the parent's Gate-2
result, 100% integral LP, reproduced).
**R4.2 S4 pilot BINDS under S4's own weights:** m_soc capture at level A = **0.7720 = target**
(carbon ×2 block share, t 0.772) — the certification M4.3 asked for; θ-tail band scored in 08.
S0 anchors carry m_soc at 0.755 (A) / 0.732 (B) with t 0.322 inert: the co-capture floor under S0
weights sits at 0.755, still below 0.772, so the θ 2× rung is the right one under both weight
regimes.
**R4.3 Budget level B is feasible and distinct:** S0-585 objective rises 4.461 → 5.022 (+12.6%)
when additions halve (10,083 → 5,042 km²); m_soc capture 0.755 → 0.732. Nesting measured in 08.

## R5. Gate AB-2 — MGA pilots, verdict rule v2, nesting, S4 pilot (07/08 run 2026-09-03)

Provenance: `runs/ab_l/{A,B}/s0_ssp585_theta5/` (anchor.tif, formulation_meta.json, mga_g05 /
mga_guard_g05 / g02 / g10 member stacks, certificates), `spec/gate_ab2_verdicts.json`.

**R5.1 Estimator run.** MGA anchors reproduce 06's engine certificates (rel drift 3.1e-6). Every
sweep certified: 50/50 members inside the band at every level and semantics, 0 time-limited,
≤2 duplicates (g=10% at A; g=5% at B); **iterations 1–2 s; a full k=50 sweep 0.5–1.5 min** (parent
10–16 s/iteration, 45–60 min/sweep).
**R5.2 H-AB4 REFUTED — in the opposite direction.** Level A, aggregate 5% band: **D = 0.9999,
C = 0.000 → PLATEAU-RICH** (parent 0.953 / 0.020); level B: D = 1.0000, C = 0. The first MGA
member is 20,126 Hamming from the anchor = 2 × 10,063: a near-DISJOINT set of additions sits
within 5% of optimal. Registered direction (narrower freedom in a smaller, more disturbed, more
constrained extent) is wrong: Alberta's near-optimal band is FLATTER than Y2Y's.
**R5.3 The 5% frequency surface is degenerate.** Frequent tier (F ≥ 0.70) over 51 plans: **2 km²
at A, 0 km² at B**; always-core 0; union = every one of the 57,161 discretionary cells at both
levels. f(g) at A: **g = 2% → core 876 km², frequent 1,488 km², union 50,824**; g = 5% → 0 / 2 /
57,161; g = 10% → 0 / 0 / 57,161. Structure exists only inside the 2% band.
**R5.4 Guardrails are inert here.** Guarded sweeps reproduce the aggregate sweeps almost exactly
(same max Hamming 20,126; frequent 2 km²); E14-analog: **1/50 (A) and 0/50 (B) members drop any
block below 0.95 × anchor** (parent: ~100% of members in every formulation). Mechanism: the locked
estate banks 24–71% of every feature and the additions are ≤ 17.6% of the unlocked land, so
turning the additions over completely moves each block's capture by less than 5% — the floors
never bind. The same mechanism explains R5.2–R5.3: with the banked shares this high the objective
is nearly flat in the additions.
**R5.5 Nesting test (D-AB5 v2) is VACUOUS at g = 5%:** core A 2 km², core B 0 km² → N = 0.000 by
arithmetic; the frozen rule returns "level B primary" with no evidence behind it (there is nothing
to nest). Escalated to chat (M9); 07/08 patched to run and evaluate the 2% band at both levels.
**R5.8 Nesting at g = 2% (07/08 re-run 2026-09-03, D-AB10): PERFECTLY NESTED — N = 1.000.**
Frequent tiers (F ≥ 0.70, 51 plans): level A **1,488 km²**, level B **404 km²**, and every one of
B's 404 cells lies inside A's tier. Always-cores (f = 1): A 876 km², B 84 km². Frozen rule (0.80)
applied at the tightest band with non-empty cores on both levels → **level A is PRIMARY**; the
tight-envelope answer is a strict subset of the wide envelope's tiers, so A's surfaces carry B's
answer (the 404 km² that survive even a 5k envelope = the innermost tier for the applied report).
Level B's g = 2% sweep: 50/50 certified, 1 duplicate, ~0.5 min.
**R5.6 S4 pilot PASS:** m_soc capture 0.7720 = target (binds at the kink under S4 weights);
θ5-tail mass capture **0.877 ≥ 0.75** (S0 reference 0.850); biomass tail 1.000 (vacuous, 42 cells).
**R5.7 T1-analog block captures (Σ member captured fractions):** S0-585 A: core habitat 0.557 /
connectivity 0.993 / carbon 1.141 / biodiversity 0.862 / gHM 0.463 / EFG mean 0.699; at B:
0.499 / 0.861 / 1.055 / 0.741 / 0.408 / 0.600. S4-A: carbon 1.177 (+0.036), others within
0.005 of S0. Climate 245 moves core habitat by +0.02, nothing else.

*Last updated 2026-09-03.*
