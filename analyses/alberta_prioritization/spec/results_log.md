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

## R6. Gate AB-3 — manifest freeze (09 run + committed 2026-09-03)

`spec/manifest.csv`: **14 formulations at level A** — (S0–S5) × {ssp585, ssp245} + s1x/s3x at
585; S4/crossed regime `theta2_places` (t 0.772); `applied_band_g` 0.02, `band_gap_g` 0.05,
`floor_g` 0.05, k 50, opt_gap 1e-4, verdict rule v2_8db80fed1c702638. Weights reproduce 05's
frozen S0–S4 vectors at both climate levels (assert passed). Freeze sha256
**0fc766674b2cb44a…**; pipeline pinned at git **832e76fc50c7** with the five modules clean vs
HEAD; pre-registration commit **77d8713**. Reference formulation points at the AB-1/AB-2
artifacts (`runs/ab_l/A/s0_ssp585_theta5/`).


## R7. Gate AB-4 — the ensemble run (10 run 2026-09-03 20:13–22:32 UTC; analysis 11 PENDING-RUN)

**R7.0 Run record.** 14/14 formulations at level A, each with engine anchor (Gurobi binary,
gap 0.0000%, ~1 s), Gurobi-proportion twin, k-best pool (50 @ 5%), MGA anchor (drift vs the
engine certificate 1.3e-6–1.0e-5), and four sweeps of 50 members (aggregate + guarded at g = 5%,
aggregate + guarded at g = 2%): **every one of the 2,800 member certificates inside its band**,
0 time-limited. **5.2–7.4 min per formulation, 2.3 h total** (parent: ~45–60 min per sweep,
12.3 h for the guarded sweeps alone). Anchor objectives: S0 4.4609 / S1 4.3313 / S2 4.4502 /
S3 4.6298 / S4 4.2883 / S5 9.1991 (585); 245 within ±0.03 of each; crossed s1x 4.3319, s3x
4.6326. **Every LP twin equals its engine anchor to four decimals** — the relaxation is tight
for all 14 (the summary cell's "VIOLATED" flags on 7 formulations were a comparison of a
4-decimal twin against the full-precision MGA anchor; gaps ≤ 4.3e-5; M12.1).


**R7.1 (11 run 2026-09-08 18:27 UTC; provenance `analysis/ab4/{geotiffs,tables}/`, `spec/gate_ab4_summary.json`.)
The 5% estimand, ensemble-wide.** D_s = **0.996–1.000 for all 14 formulations** (parent 0.809–1.000);
ensemble frequent tier **1 km²**, always-tier 0, 98.5% of unprotected land "rare" (0.05–0.30), never-band
0 — every unprotected cell is in some near-optimal plan of some formulation. E1 bias (hierarchical −
anchor-only F) mean 0.231 / max 0.807 (parent 0.169 / 0.755). E3 variance shares: within-formulation
**0.997**, scenario 0.003, climate 0.000 (parent 0.952 / 0.044 / 0.002); crossed-regime contrast mean
|Δf| 0.004 (s1), 0.001 (s3). Guarded = plain everywhere (tier Jaccard 1.000 at 2%).
**R7.2 E11 — total no-regrets pluralism.** Between-anchor discretionary Jaccard 0.373–0.9996 (mean
0.618); **182/182 ordered pairs mutually inside each other's 5% band** (parent 156/182, whose 26
failures were carbon-forward); Δ-diagonal self-check max 0.0. Anchor captures move ≤ 0.02 across
formulations for every feature (m_soc 0.751–0.773; S5's gHM push lifts intactness 0.463 → 0.478 only);
θ5-tail mass capture m_soc 0.849–0.879 (S4 highest), biomass 0.977 (S5 0.860) — the carbon-forward
regime is visible in the tail, not the total, as the parent found.
**R7.3 The 2% applied band (D-AB10).** Ensemble F₂: core (≥ 0.70) **1,117 km² = 1.95% of
unprotected land**, always (≥ 0.95) 87 km², conditional 7,018, rare 39,887, **never 9,139 km² (16%)**.
Per-formulation frequent tiers 1,129–1,774 km² (S5: 86); D₂ 0.836–0.888 (S5 1.000). Climate levels
pool for every scenario (tier Jaccard 0.91–1.00) **except S1 core-habitat (0.756 → shown per level)**.
Tiers: core 1,117; value-forward minus core — S1@585 427 / S1@245 443 / S2 606 / S3 **35** / S4 310,
union 1,121 km² (1.96%); opportunity 54,185 (94.8%); never 738 km² (1.3%). Biodiversity-forward adds
almost nothing of its own (35 km²) — the AB echo of the parent's R10.12 ("connectivity/biodiversity
never own tier land"); here connectivity does (606 km²).
**R7.4 C1 — the zoom-in agrees with the zoom-out's Alberta portion.** Spearman(F_AB, F_Y2Y|AB) =
**0.85** over 57,161 unprotected cells at the 5% band; frequent-tier overlap coefficient 1.0 (tiers of
1–2 km², Jaccard 0.002 — degenerate, reported). Per formulation, AB's 10,083 additions lie **91–99%
inside the Y2Y-wide anchor's selection within Alberta** (overlap coefficient 0.908–0.986), while
the Y2Y-wide anchors select 15,426–25,377 Alberta cells (the clip's share ≠ AB's additions share, so
Jaccard 0.385–0.560 is the set-size artifact the spec anticipated). Divergence is a matter of budget
size, not location.
**R7.5 C4 — AOIs.** Core inside the Upper Smoky Nature-First zone: **0 km²** (mean F₂ inside 0.27 vs
0.18 over unprotected land — above average, no core); core inside the whole Upper Smoky planning area
(10,028 unlocked km², 17.5% of discretionary land): **0 km²** (mean F₂ 0.19). The pre-stated C4 reading
(zone drawn for caribou + parks, not complementarity) applies as written. AOI-3 ("west of Grande
Cache") cannot come from the core; it reads from the value-forward surfaces (an S1 cluster at 54.0°N,
49 km², 98% inside the NFZ) or the opportunity tier.
**R7.6 Tenure and distance (2% tiers).** Core: crown Green 478 / crown White-notated 106 / private
non-ranch 122 / **private ranchland 345 km² (31%)** / unclassified 66 — the OECM track holds 3.3× its
9.4% share of unprotected land; protection track 52%. Value-forward union: crown 806 / ranchland 282.
Core distance to the nearest park: 0–5 km 10.7% (null 16.3%), 5–10 10.2% (13.8), 10–20 11.2% (19.0),
**> 20 km 67.9% (null 50.9%)** — the core is farther from the estate than average land, not adjacent to it.
**R7.7 Clusters (provisional AB constants: ≥ 10 km², closing r=1).** Core tier → 65 components, **6
kept (1,073 km²)**; min-size sensitivity 5/10/25/50 km² → 16/6/5/4 clusters (1,139/1,073/1,058/1,029
km²). Core clusters: **412 km² at 53.4°N** (−116.8°W; mean F₂ 0.91; 99% inside the rare-EFG footprint;
100% crown; frequent in 12/14 formulations), **307 km² at 50.3°N** (−114.2°W; F₂ 0.71; no driver mask;
57% ranchland), 214 km² at 49.7°N (F₂ 0.92; 99% rare-EFG; 69% ranchland), 96 km² at 50.0°N (98%
rare-EFG; 47% ranchland), 29 km² at 50.0°N (F₂ 0.95; 31% m_soc tail; frequent in 14/14), 15 km² at
49.6°N (100% within 5 km of a park). Driver masks on the extent: m_soc θ-tail 716 unprotected cells,
rare EFGs (≤ 1% of PU) 5 classes / 875 cells, connectivity spike (top 1%) 572. Scenario clusters after
core subtraction: S1@585 6 (584 km²), S1@245 11 (561), S2 6 (770), S3 1 (113), S4 10 (359). Total kept 40.
**R7.8 Reading.** Two cores, two mechanisms: the northern one (53.4°N, Foothills/Boreal edge) is the
scarce-ecosystem claim; the southern ones (49.6–50.3°N, the ranchland fringe) are frequency without a
single binding claim — the diffuse values agreeing. Neither touches the Upper Smoky country.


**R7.9 The northern core is one ecosystem class — and a suspected mapping artifact (found 2026-09-08
while explaining pick 1 to Ethan).** Pick 1 (412 km², 53.4°N, Lower Foothills NE of Whitehorse
Wildland) is 99.3% inside the footprint of **IUCN GET F2.10 ("Subglacial lakes")**, whose ENTIRE
footprint on the AB extent — and on the whole Y2Y region — is those 409 cells (all "major"
occurrence, 0% inside PAs). Per-cell marginal value under S0: an F2.10 cell is worth **1.8× an
average unprotected cell, and F2.10 alone supplies 50% of it** (9.1e-5 of a 1.8e-4 total; the
continuous values on those cells sum to 8.5e-5, slightly BELOW the 8.9e-5 unprotected average).
Biodiversity is not the driver: birds are 8% above the unprotected mean (p80) and mammals 3%
(p56) — high percentiles only because AOH is nearly flat in Alberta (leverage 0.12 / 0.07);
mammals + birds are 55% of the continuous part, which is itself average. Mechanism = the
representativeness block's design: each EFG carries 1/27 of the block's weight regardless of
extent, so a class's per-cell value is (1/27) ÷ footprint — 409 cells make F2.10 worth 0.9× an
average cell's ENTIRE value on its own (T6.1 at 247 cells 1.5×; T4.4 at 1,371 cells 0.3×). Rare
classes that fit inside the additions are bought whole by every formulation (the parent's E13
binding-scarcity mechanism). **The Y2Y-wide F pins the same polygon** (F 0.89, guarded 0.86,
100% ≥ 0.70). A 409 km² subglacial-lake polygon in the foothills is implausible; treated as a
data-quality flag for the deck (not a core commitment as-is) and a formulation question (drop
F2.10 from the EFG block?) that belongs with the parent's representativeness discussion, since
the parent core carries it too. Picks 3–6 are also 87–99% inside the rarest-EFG footprint and
need the same class-by-class check before the deck.


**R7.10 Class-by-class audit of the core picks (2026-09-08): the representativeness block is being
completed on anthropogenic and artifact classes.** Per pick (GET names from the v2.0/2.1 typology):
- #1 (412 km², Lower Foothills): F2.10 *Subglacial lakes* — 99% of the cluster; the cluster holds 100%
  of the class (409 cells, 0% in PAs). Artifact (R7.9).
- #2 (275 km², Foothills Parkland/Fescue): T4.4 *Temperate woodlands* — 100% of the cluster; the
  class covers 1,371 cells, 2.6% in PAs; the cluster holds 20% of it. Connectivity 1.20× / corridors
  1.26× / refugia 1.06× the unprotected mean. **The one genuine multi-value core**, and a real
  under-protected vegetation class.
- #3 (214 km², Mixedgrass) and #4 (96 km²): T5.1 *Semi-desert steppes* (2,391 cells, 0.1% in PAs;
  plausible for the Dry Mixedgrass) **plus SF2.2 *Flooded mines and other voids*** (341 cells, 0% in
  PAs; the two clusters hold 62% + 28% = 90% of the class — the Lethbridge coalfield). Every other value
  on these cells is BELOW the unprotected mean (intactness 0.67/0.47×, refugia 0.60×, carbon ≈ 0,
  birds/mammals 0.7–0.8×): they are bought to complete a mined-void class and a steppe class.
- #5 (29 km², Alpine/Subalpine) and #6 (15 km², Montane): F2.9 *Geothermal pools and wetlands* (450
  cells, 73% in PAs) + F3.5 *Canals, ditches and drains* (254 cells, 68% in PAs) — 93%/87% of each
  cluster; #5 is also 31% m_soc θ-tail with SOC 8.5× and refugia 1.8× (genuine value), #6 is not.
**Aggregate:** 766 of the 1,073 kept core km² (71%) sit ≥ 87% inside the rarest-EFG footprint, and the
classes doing the pinning are one artifact (F2.10), two anthropogenic (SF2.2, F3.5), one coarse envelope
(F2.9 covers 40% of the Y2Y PU and 0.5% of Alberta), and two real vegetation classes (T4.4, T5.1).
**The EFG block admits anthropogenic biomes by construction:** 10 of Alberta's 27 classes are T7
(intensive land use: croplands, pastures, plantations, urban, derived pastures), F3 (artificial
wetlands: reservoirs, constructed wetlands, canals) or SF2 (anthropogenic subterranean: pipes,
flooded mines); 11 of the parent's 40 likewise (T7.4 *Urban and industrial* included). Mechanism = R7.9:
per-cell class value ∝ 1/footprint, so the scarce anthropogenic/artifact classes are the cheapest
units of "representativeness" to complete. → Decision needed (spec, and the parent's): restrict the
representativeness block to natural biomes (and drop physically implausible classes) — a formulation
change requiring a re-run of AB 10–13 (~2.5 h) and, for the parent, of its Gate-4/guarded sweeps.

**R7.11 Method audit of the pinning classes (2026-09-08, after Ethan's challenge "are they really not physically
plausible?"): the R7.10 diagnosis is CORRECTED — the classes belong in Alberta; the MAPS do not put them where they are.**
Read from the GET archive's own `map-details.xml` (per-class construction) and measured on the AB stack (zero-solve):
- The GET README states its maps are 10 arcmin–1° grain and "should be used to query which EFG are likely to occur within
  areas, rather than which occur at particular point locations". Of Alberta's 27 classes, 9 are ENVELOPE maps (whole
  freshwater/terrestrial ecoregions selected by description + expert review: F2.9, F3.2, F3.5, SF2.1, SF2.2, T4.4, T6.4,
  TF1.6, TF1.7), 1 is a POINT-RECORD map (F2.10), the rest are land-cover/inventory/proxy maps.
- **F2.10 Subglacial lakes** — 409 cells, ALL "major" (= a point record from the Antarctic/Greenland/Iceland inventories
  the GET cites: Wright & Siegert 2012, Bowling 2019, Marteinsson 2013, Livingstone 2016), 121 km from the BC border, in
  ice-free Lower Foothills (nearest glacier ≈100 km SW). Minor occurrences were to come from permanent snow/ice, yet the
  Rockies' icefields carry none. **Physically impossible here: a misplaced record. Artifact stands.**
- **F3.5 Canals, ditches and drains** — the class is real in Alberta (the prairie irrigation districts), but the mapped
  Alberta footprint is 254 cells with **median distance 0.5 km (p90 1.3 km) to the BC border, 68% inside national parks**:
  the overshoot of a Columbia/Missouri freshwater-ecoregion envelope across the divide. Not a canal in it.
- **F2.9 Geothermal pools** — real in the AB Rockies (Banff, Miette, Mist Mountain), but built as "small lakes within
  freshwater ecoregions deemed to contain the EFG" (40% of the Y2Y PU); Alberta footprint 450 minor cells, **median 0.7 km
  (p90 1.7 km) from the border, 73% in PAs** — the same divide-overshoot sliver.
- **SF2.2 Flooded mines** — real in southern Alberta (Lethbridge underground workings, Crowsnest, Coal Branch), but the map
  paints WHOLE terrestrial ecoregions "with concentrations of flooded-mine records"; the Alberta footprint is the strip where
  that prairie ecoregion crosses the Y2Y line (**median 4.0 km, max 11.2 km from the Y2Y boundary**, 66 km from the BC border,
  0% PA). An ecoregion-edge sliver, not mine sites.
- **T4.4 Temperate woodlands** is ALSO an envelope map, but there the envelope IS the ecosystem (the aspen-parkland strip =
  Foothills Parkland; 1,302-cell body, 37 km from any border) — so envelope construction is not disqualifying per se.
- **T7.x / F3.1 / F3.2 (croplands, pastures, urban, reservoirs, constructed wetlands)** are land-cover/inventory maps with
  broadly correct footprints (3–49% of the AB PU) and drive none of the core picks; whether a conservation
  representativeness block should hold shares of them is a separate purpose question, second-order for this result.
**Corrected mechanism:** the block scores per-cell presence in coarse envelope/point maps as an ecosystem occurrence, and
per-cell value ∝ 1/footprint, so the smallest cartographic slivers (border overshoots, a misplaced point) are the most
valuable cells in the block. The R7.10 remedy ("restrict to natural biomes") targets the wrong thing: 3 of the 4 pinning
classes are natural-or-plausible classes with sliver maps. **Candidate rule for the decision (not applied):** exclude
point-record classes and envelope-method classes whose footprint on the extent is < 1% of the PU (AB: F2.10, F2.9, F3.5,
SF2.2 → 23 classes); direct/land-cover classes are kept at any footprint (T6.1 glaciers, 0.29%, 98% in PAs, stays). The
anthropogenic-biome purpose question is logged as open and separable.
Parent exposure measured the same day (Y2Y results_log R10.18): 8.2% of the Y2Y core, 2 of 14 deck picks, 27.9% of the
Act 1 representativeness layer. Both extents' class tables + options A–D + costs → `analyses/y2y/spec/efg_block_reportback.md`
(the report-back for the spec chat). **12–13 PARKED pending the rule decision.**

*Last updated 2026-09-08.*
