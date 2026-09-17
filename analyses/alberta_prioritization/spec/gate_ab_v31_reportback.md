# Alberta v3.1 report-back — the curated block on the Alberta mirror (2026-09-15)

The whole v3.1 chain has run on Alberta: 09b (curation freeze) → 10 (ensemble) → 11 (analysis) → 11b/11c
(necessity test) → 12 (tiers and clusters) → 13 (figures) → 14 (director outputs). AB spec v0.5/v0.5.1 =
the mirror of the parent study plan v0.17.3 + package spec v1.7. Provenance: AB results_log R8.1–R8.6;
methods_log M14–M18. This is the stage-2 transfer of the parent's v3.1 result (parent R10.20–R10.22).

## 0. The headline in one paragraph

**The curated block removed Alberta's core.** On the v1 (40-class) block the 2% core was 1,117 km², and
71% of it sat on GET map slivers (R7.9–R7.11). On the curated block the guarded 5% frequent tier is
**27 km²**, so the D-AB13 flatness rule fired and the applied band is **2% guarded**; the 2% core is
**31 km²** (28 frequent + 3 always) — 0.05% of allocatable land, one patch east of White Goat Wilderness
(52.3°N 116.4°W). No plain-band cell is frequent at all. The necessity test is empty (0 km² forced by any
class in any formulation), so nothing about this is an EFG artefact any more. The reason is measured, not
inferred: the values Alberta's unprotected land can offer are flat (best additions-sized set only
1.1–1.6× a random fill for five of eight themes) and the concentrated ones are already banked (soil carbon
71% inside PAs; refugia 46%), so D = 1.000 at 5% for every formulation and 132/132 anchor pairs are
mutually in-band. The deliverable for the Alberta program is therefore the value map and the scenario
tiers, not a core. The deck already leads with the value-convergence map.

## 1. Execution record (09b, 10, 11b)

- **Block:** 27 → 15 classes → **13 features** by the inherited R0 curation (D-AB11). Out: F2.10 (point record),
  F3.5 / SF2.2 / F2.9 (the other three v1 core-pinning classes), F3.1, F3.2, SF2.1, T7.1–T7.5. Merged:
  TF1.6+TF1.7, S1.1+SF1.1. Re-applying the extent rule on the Alberta extent would drop none of the 15;
  the boundary rule flags one clip-edge class, T6.1 (247 cells, 98% inside PAs, 99.6% within 10 km of
  the boundary) — reported, not dropped, the same disposition as the parent's five.
- **Block card v3 (Alberta extent):** rare-attainable 9/13; ≤1%-footprint companion 1 (T6.1); no class
  banked ≥0.999 (v1 had the artefact classes at 0); banked shares T6.1 0.98, S1.1_SF1.1 0.96, T6.2 0.92,
  T6.3 0.78, T6.4 0.62, F2.4 0.45, F1.3 0.33, T2.1 0.29; the rest < 0.10.
- **Window targets (D-AB12, +250 km around the Alberta extent):** T6.1 0.72, T6.3 0.42, T6.2 0.34,
  T4.4 0.31, S1.1_SF1.1 0.29, TF1.6_TF1.7 0.21, SF1.2 0.20, T5.1 0.19, F1.3 0.18, T2.2 0.16; three at the
  0.10 floor (T6.4, F2.4, T2.1). The parent's targets for the same 13 features: T6.1 0.36, T2.2 0.15, the
  other eleven at the floor — the Alberta window makes the block a stronger claim than the parent's,
  because every class is rarer in a 250 km window around Alberta than in one around Y2Y. Sensitivity:
  +100 km lifts most classes (T4.4 0.53, T6.3 0.44); +500 km sends nine to the floor. **Window-rare
  (≤1% of the window) = T6.1 only** — the Act 0 representativeness vote — and T6.1 has **5 unlocked
  cells**. Manifest v3.1 sha `6e66ec3f…`, 12 design rows, weights asserted equal to v1.
- **Ensemble (10):** 12/12 design formulations (no crossed hybrids, no k-best on v3.1). Anchors 0.5–1.5 s
  each (rel. drift vs the compiled model ≤ 8.6e-6); LP twins ≤ MILP 12/12; four sweeps × 12 formulations
  × 50 members (plain and guarded, at 5% and 2%): **2,400/2,400 certificates in band, 0 time-limited,
  8 duplicates** (all in the plain 5% sweeps of S3 and S5), ~61 min of solver time in total.
- **E19 solves (11b):** 12 leave-EFG-out anchors; the five E17-T3 leave-one-block-out anchors were
  also solved (mirror, disclosed); the gated T3 no-EFG ensemble was not triggered (§4).

## 2. The applied band and the frequency surface (11)

**D-AB13 fired.** 5% guarded frequent tier 27 km² < the 100 km² flatness threshold → applied band = 2%
guarded (D-AB10). At 5% every band is degenerate: never 0 / rare 53,833 / conditional 3,301 / frequent
27 / always 0 km²; D = 1.000 for all twelve formulations (every one has a member that turns over the
whole allocation within 5%).

| 2% band (guarded / plain), km² | never | rare | conditional | frequent | always |
|---|---|---|---|---|---|
| guarded | 2,020 | 49,978 | 5,132 | 28 | 3 |
| plain | 2,110 | 51,226 | 3,825 | 0 | 0 |

Guarded-vs-plain frequent-tier Jaccard 0.0 (the plain tier is empty). D at 2%: 0.938–1.000 (S1@245
lowest). E1 mean |F − F_naive| 0.241, max 0.825. E3: within-formulation 99.98% / scenario 0.01% /
climate 0.0005%. E11: 132/132 ordered anchor pairs mutually in each other's 5% band; anchor Jaccard
0.38–0.82 (mean 0.56). Anchor captures barely move across formulations (refugia 0.57–0.60, connectivity
0.56–0.59, corridors 0.48, m_soc 0.73–0.77, biomass 0.39–0.46, birds 0.43, mammals 0.45, EFG mean 0.55).
Pooling (M4.33): S0, S2, S5 pooled (climate Jaccard 0.82–0.88); S1, S3, S4 kept separate (0.19 / 0.71 /
0.69 — the core-habitat-forward scenario is where the two refugia futures disagree).

**M4.31 absolute widths:** z* fell 5.2–10.1% from v1 on every formulation (the four removed classes
carried that much of the objective); the 2% band is 0.077–0.174 in objective units, the 5% band
0.19–0.44.

**Threshold ladder (guarded F on allocatable land, 8-connected patches ≥10 km²):**

| F ≥ | 0.95 | 0.80 | 0.70 | 0.60 | 0.50 | 0.40 | 0.30 |
|---|---|---|---|---|---|---|---|
| km² | 3 | 15 | **31** | 75 | 205 | 1,111 | 5,163 |
| patches ≥10 km² | 0 | 1 | 1 (17) | 1 (35) | 3 (68/28/21) | 23 | 34 |

Relaxing the tier to 0.50 buys three patches east of Jasper (52.1–52.9°N); 0.40 is the first threshold
that produces a landscape (23 patches, largest 315 km²). The pre-registered sensitivity (0.60 / 0.80)
brackets 15–75 km².

**Why the core is empty — measured on the stack, level A additions = 10,083 km²:**

| theme | banked in PAs | best additions-sized set ÷ random fill | best set as % of the total |
|---|---|---|---|
| refugia | 46% | 1.63× | 15.7 |
| connectivity | 39% | 2.17× | 23.6 |
| corridors | 36% | 1.21× | 13.7 |
| soil carbon | **71%** | 4.71× | 23.7 |
| biomass carbon | 24% | 2.37× | 31.9 |
| mammals | 33% | 1.12× | 13.3 |
| birds | 30% | 1.11× | 13.7 |
| naturalness | 36% | 1.14× | 13.0 |

On Y2Y the same statistic runs 1.4–2.3×. Soil carbon is the only concentrated value and it is inert:
its banked share (0.71) already exceeds S0's target (0.332), and even the carbon-forward target (0.772,
θ 2×) needs 6 points — which is exactly what S4's anchors add. With the artefact classes gone, nothing
on the unprotected land is both concentrated and unsatisfied, so the objective is flat over it and the
ensemble reports that honestly.

**Where the v1 core went.** The 412 km² northern pick (F2.10, 53.4°N) is gone by construction; the
one genuine multi-value v1 core (T4.4 fescue woodlands, 275 km² at 49.9°N) survives only as a
core-habitat-forward SSP245 scenario cluster (265 km², mean F 0.3). The v3.1 core patch east of White
Goat (23 km² with specks, mean F 0.83, 100% crown, 5.9% of it in the soil-carbon tail) is a carbon and
core-habitat place: 1.68× the allocatable mean for core habitat, 3.14× for carbon, 0.74× for
representativeness (existing PAs: 1.71× / 3.95× / 1.40×).

**C1 (same parent version):** at 5% the two frequency surfaces correlate at Spearman 0.28 (v1: 0.85)
with no tier overlap (both tiers < 30 km²); at the applied guarded band Spearman 0.65, overlap
coefficient 0.74 (AB core 31 km² vs the parent's Alberta-clip core 263 km²). Per formulation, Alberta's
10,083 additions fall 73–93% inside the parent anchor's Alberta selection (v1: 91–99%) — the block's
artefact pins were part of what made the two runs agree. **C4:** 0 km² of core inside either Upper
Smoky area of interest; mean F inside the Nature-First zone 0.34 vs 0.18 on allocatable land (1.9×),
inside the SRP planning area 0.19. **Tenure:** core 29/31 km² crown Green; all scenario tiers 847/870
crown, 10 km² ranchland (connectivity-forward).

## 3. Package v1.7 on the curated block (12 → 13 → 14)

Allocatable land 57,161 km². Tiers (guarded, applied band): **core 31 km² (0.05%); scenario tiers
319 km² (0.56%)** — core-habitat-forward 160, connectivity-forward 151, two or more 8, biodiversity- and
carbon-forward 0 — **opportunity 56,811 km² (99.4%)**, never 0. By refugia future: SSP585 core 33 km²,
SSP245 30 km², Jaccard 0.85. Regional deck picks (30 km single linkage, numbered N→S): one core pick
(**Cluster 1**, E of White Goat, 23 km²) and four scenario picks (Upper Smoky Nature-First vicinity 39 km²,
S of White Goat 63, SE of Whitehorse Wildland 17, E of White Goat 41). Biodiversity capture is
0.431–0.441 over all 612 guarded plans (the finding-as-product: no plan moves it).

**Act 0 values:** top-30% footprints 17,149 km² per theme; representativeness 5 km² (T6.1's unlocked
cells); value convergence 0 → 13,500 km², 1 → 25,569, 2 → 11,811, 3 → 5,648, 4 → 633, 5 → 0. High-value
land (≥1 theme) 43,661 km², of which **43,321 km² (99.2%) lies outside core ∪ scenario tiers** — the
opportunity landscape is the map. E19 partition: 0% adequacy-forced in every unit; multi-claim 100% for
the core and every pick. E17-T3 (mirror, disclosed): dropping the core-habitat block shifts S0's
anchor +0.58° north (Jaccard 0.52 vs S0); the other four blocks shift ≤0.10° (Jaccard 0.64–0.78).

**What the team output now leads with (14):** the objectives table; the **value-convergence map**
(count of themes in which a cell is top-30%, one inset on Cluster 1) with and without the clusters;
the core star and locator; the consequences table with the three reference columns (existing PAs,
the Nature-First zone's unprotected part, the SRP planning area's unprotected part). The F-surface
maps are one call away and kept in 13's record.

## 4. The necessity test (11b/11c)

**T1 — forced set EMPTY.** No class is captured in full by every member of any formulation; the
least-selecting member holds 0.00–0.26 of each class's unlocked cells; 0 km² forced in ≥1 formulation,
0 in all twelve; core 0.0% forced; **T3 gate (> 50%) not triggered.** **T2 — leave-EFG-out anchors:**
Jaccard with the with-EFG anchor 0.68–0.87, 0 core cells dropped without the block, mean latitude shift
−0.05°. The block moves 13–32% of each plan but pins none of the core — the opposite of the v1 block,
where it pinned 71% of it.

## 5. Decisions for the chat

1. **What the Alberta deliverable is.** A 31 km² core is not a program product. Proposal: the Alberta
   result is the flatness finding — values banked or diffuse, no single answer — carried by the
   value-convergence map, the scenario tiers (core-habitat 160 km², connectivity 151) and the 99.2%
   opportunity gap, with the core reported at its measured size. The deck is already built that way.
2. **Threshold.** Keep F ≥ 0.70 as the estimand and report the ladder (§2) rather than lowering the
   tier to manufacture a core; 0.60/0.80 stay the pre-registered sensitivity. A `CORE_THR` knob for
   an exploratory 0.50 view (205 km², three patches) is one line if wanted.
3. **D-AB12 window: confirm +250 km around the Alberta extent.** It makes the Alberta claim stronger
   than the parent's for the same 13 features (three at the floor vs eleven; T6.1 0.72 vs 0.36); the
   alternative is to adopt the parent's targets verbatim (a weaker block, same emptiness expected).
4. **D-AB13 fired: confirm 2% guarded as the applied band** (the same choice D-AB10 made on v1).
5. **C1 reading.** Agreement with the parent's Alberta portion fell (overlap 0.91–0.99 → 0.73–0.93,
   Spearman 0.85 → 0.28 at 5%) because the shared pins were the artefact classes; report as a
   consequence of the curation, not a transfer failure.
6. **Disclosures to carry:** T6.1 clip-edge flag; E17-T3 solved on Alberta as a mirror extra;
   the values table and value maps are measured over allocatable land only.
