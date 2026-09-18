# Report-back: the post-freeze sequence PF-1 → PF-3 (E20, study plan v0.18)

Y2Y flagship, manifest v3.1, 2026-09-17. All arms solved by Ethan (18e, 18f), analysed in 18g. Records: `results_log.md` R10.24
(cont.) and R10.25 (cont.); methods `M4.34`–`M4.36` (+ addenda). Nothing registered has changed; this is evidence for the chat.

## What ran

Seven guarded runs of the frozen machinery (anchor at gap 1e-4; guarded MGA `mga_maxham_v1`, k = 50, g = 5%, per-block floors at
95% of the anchor's capture; Gurobi), each at SSP585, each with weights re-derived under constant intended influence for its own
shapes and block structure, registered targets unless stated. Every run returned 50/50 members OPTIMAL and inside the band.

| arm | scenario | shapes | block shares | note |
|---|---|---|---|---|
| PF-1 `e20_log` | S0 | refugia log1p(1/v); everything else identity | registered | already reported (R10.24 cont.) |
| PF-2 `e20_consistent` | S0 | refugia log1p(1/v), transboundary I², corridors I² | registered (connectivity 0.25, split 0.125 / 0.125) | **the step-2 baseline** |
| PF-2 `e20_consistent_target` | S0 | same | registered | + R2's transboundary target t = 0.198 |
| PF-3 A@S0 | S0 | step-2 shapes | five blocks at 0.20 (transboundary and corridors separate) | |
| PF-3 A@S2 | S2 | step-2 shapes | transboundary 0.25, corridors 0.25, the other three 1/6 | |
| PF-3 B@S0 | S0 | step-2 shapes | corridors removed; transboundary alone at 0.25 | |
| PF-3 B@S2 | S2 | step-2 shapes | corridors removed; transboundary alone at 0.50 | |

Reference rows (the registered v3.1 runs, identity shapes) are in the same table so nothing is read against v1-era numbers.

## Definitions

- **Transform-conditional share** = of the core cells S0 keeps frequent (f ≥ 0.70) under the registered shapes (26,499 of the
  29,194 km² core), the fraction it drops under the arm. **Survival** = share of the whole core frequent under the arm.
- **Own land** (E18's definition) = the arm's frequent tier outside the frozen core and outside the other named scenarios'
  registered SSP585 tiers. The registered S0 owns 0 km² by construction; the registered S2 owns 7,796 km².
- **Pinch points** = the top 0.2% of raw current on allocatable land (the "spike"); **pinned** = frequent in the arm.
- **D** = `mga_maxham_v1` diversity (max Hamming ÷ 2 × mean plan size, discretionary cells); plateau-rich if ≥ 0.10.

## Results

| arm | tier km² | own land km² | survival | cond. share | Jaccard vs registered / vs baseline | spike pinned | densest-refugia share of tier | multi-claim | D |
|---|---|---|---|---|---|---|---|---|---|
| registered S0 (identity) | 42,733 | 0 | 91% | — | 1.000 / 0.758 | 22.9% | 78.7% | 89.4% | 0.804 |
| registered S2 (identity) | 30,509 | 7,796 | 60% | — | 1.000 / 0.587 | 100% | 60.0% | 83.6% | 0.853 |
| PF-1 log refugia | 36,287 | 0 | 87% | 4.3% | 0.846 / 0.841 | 24.4% | 84.5% | 90.3% | 0.838 |
| PF-2 consistent, t = 1 (baseline) | 41,111 | 4 | 87% | 5.0% | 0.758 / 1.000 | **100%** | 73.9% | 87.2% | 0.812 |
| PF-2 consistent + target 0.198 | 46,197 | 0 | 91% | 1.5% | 0.852 / 0.655 | **7.0%** | 75.7% | 87.5% | 0.776 |
| PF-3 A@S0 | 45,137 | 12,832 | 63% | 32.4% | 0.341 / 0.463 | 100% | 41.3% | 73.3% | 0.788 |
| PF-3 B@S0 | 45,749 | 12,713 | 65% | 30.2% | 0.349 / 0.468 | 100% | 41.6% | 73.9% | 0.793 |
| PF-3 A@S2 | 46,902 | 31,877 | 35% | 62.6% | 0.388 / 0.256 | 100% | 21.0% | 62.6% | 0.780 |
| PF-3 B@S2 | 73,254 | 60,954 | 23% | 76.3% | 0.200 / 0.137 | 100% | 7.9% | 52.1% | 0.658 |

Other measured facts:

- Tiers A@S0 vs B@S0: Jaccard 0.846. Tiers A@S2 vs B@S2: 0.543.
- What the arms drop from the core is densest-refugia land: 50% of the PF-2 baseline's 1,335 km² lost; 86% of A@S0's 8,580 km²;
  87% of B@S0's 8,009; 92% of A@S2's 16,598; 94% of B@S2's 20,218.
- What the PF-2 baseline gains (287 km²) is 97% multi-claim and 13% spike land; what the target arm loses (398 km²) is 34% spike land.
- Anchors' Jaccard with the registered S0 anchor: PF-1 0.957, PF-2 baseline 0.873, PF-2 target 0.675, A@S0 0.596, B@S0 0.656.

## Readings against the pre-stated expectations

1. **PF-1 (reported before): the core rests on the refugia ordering, not the 1/v tail.** Conditional share 4.3%. Ruling taken
   (Ethan, 2026-09-16): 1/v stays registered; log1p is the reported sensitivity.
2. **PF-2: the consistent shapes pin the pinch points at the balanced weights, at a 5% cost to the core, and add no land of their
   own.** Under identity shapes the spike was frequent only under S2's 0.5 block (registered S2 100%, S0 22.9%); under I² at t = 1
   it is 100% frequent under S0. The tier's make-up otherwise barely moves (densest refugia 78.7 → 73.9%, multi-claim 89.4 →
   87.2%); own land is 4 km² because the spike already sits inside S2's registered tier. The expectation "the refugia share of the
   core falls, multi-claim rises, the core becomes easier to defend" is NOT met beyond the pinning itself.
3. **PF-2 with R2's target: the target un-pins the spike (7.0%).** Once the anchor meets t = 0.198 with margin, the layer has no
   pull inside the band and the 95% floor is met off-spike. This is M6.7 again (targets secure amounts, not places): applying the
   protocol's lever to the convex shape removes the one thing the convex shape bought. The core survives at 91%.
4. **PF-3: the ownership crossover moved down, as expected, and the second connectivity layer carries nothing.** At identity
   shapes transboundary began to own land between per-layer shares 0.33 and 0.42 (E18). Under I² it owns ~12.8k km² at the
   balanced scenario at a per-layer share of 0.20–0.25 and 4 km² at the baseline's 0.125, so the crossover lies in (0.125, 0.20].
   Splitting the block (A) and removing corridors (B) give the same map at S0 (Jaccard 0.846; own land within 1%): corridors,
   squared or absent, do not change what transboundary owns. The two-layer block halves transboundary's per-layer share by
   construction — that is the dilution, and it is arithmetic, not a landscape property.
5. **The connectivity land is bought with the refugia core.** Every split arm's lost core is 86–94% densest-refugia land; the
   tier's densest-refugia share falls 79% → 41% (S0 arms) → 8% (B@S2), multi-claim 89% → 73% → 52%. D stays plateau-rich
   throughout (0.66–0.81); B@S2 is the least diverse guarded arm measured so far.

## Decisions for the chat

- **D-PF1 (shapes).** v0.18 is frozen with 1/v refugia and identity connectivity. PF-2 shows I² transboundary at t = 1 pins the
  pinch points at S0 for a 5% core cost and no own land, and that R2's target removes the pinning. Does the chat (a) keep the
  frozen shapes with PF-2 as the reported sensitivity, or (b) reopen the connectivity value model for the applied paper? If (b), the
  protocol's own answer is shape + target, which un-pins — so (b) would also need a ruling on whether R2 applies to the connectivity
  layer (M4.35 addendum 1 vs addendum 2).
- **D-PF2 (block structure).** Corridors carry no ownership under any tested share. Options: keep the two-layer block and state the
  per-layer share explicitly when quoting E18's bracket (now (0.125, 0.20] under I², 0.33–0.42 at identity); or make transboundary
  the connectivity block on its own (B) with corridors as a reported co-benefit. Either is a registration change for a future
  version, not v3.1.
- **D-PF3 (the applied statement).** R10.12's "connectivity never owns tier land" is dose- and shape-conditional: at identity it
  needs a per-layer share ≥ 0.33–0.42; under I² it needs ≥ 0.20. The deck's connectivity-forward caveat (E18 dose slide) should
  carry the shape condition if the chat wants it quoted.
- **Scope note.** All arms are S0/S2 at SSP585 only; no ensemble, no package rebuild, nothing in `run_v31.sh`. E12 / E17-T3 / E18
  remain v1 evidence.

## Products

`spec/v3.1/E20_pf3_summary.csv` (nine rows incl. references), `E20_transform_conditionality.json` + one CSV per arm,
`E20_shape_audit_table.csv`, `E20_value_shape_audit.csv`, `e20_refugia_transform.json` (every arm's weights, targets, layer patches),
`figures/v3.1/e20_s0_f_arms.png`; runs in `runs_v3.1/e20_*/s0_ssp585_theta5/`.

## Addendum 2026-09-17: the corridors-out isolation test (PF-4, v0.18.1) has returned

One certified anchor on the registered balanced formulation (identity shapes, manifest v3.1 targets) with climate corridors at
weight 0 and transboundary connectivity on the connectivity block's full 25% (weight 0.669 → 1.236; other blocks re-derived under
constant intended influence). Solved by Ethan (39 s, gap 2e-6). Record: R10.26.

| measure | registered S0 anchor | corridors-out anchor |
|---|---|---|
| Jaccard on discretionary selections | 1.000 | **0.686** (35,578 km² swapped each way; 18.6% of discretionary land) |
| frozen core inside the anchor (of 29,194 km²) | 29,088 | 28,782 |
| transboundary capture | 0.354 | 0.386 (+3.2 pts) |
| climate-corridor capture | 0.281 | 0.267 (−1.4 pts; 90% of the discretionary capture kept at weight 0) |
| refugia / biomass / soil carbon | 0.474 / 0.372 / 0.332 | 0.454 / 0.344 / 0.332 |
| birds / mammals / naturalness | 0.329 / 0.326 / 0.306 | 0.334 / 0.331 / 0.305 |
| EFG block mean capture; targets met | 0.336; 20 of 20 | 0.346; 19 of 20 (F2.1 at 0.4912 vs 0.4912) |

**Reading rule applied:** 0.686 is noticeably below 1 (operationalized at 0.95, the level a single shape change reached; disclosed,
not in the register) → **corridors was shaping the balanced map; B is a real change and must be stated as such.**

**What kind of change.** The swap is off-core: the core stays in the anchor (306 km² leave), and the land that moves is diffuse
discretionary land (dropped: 63% multi-claim, 2% densest refugia; gained: 31% multi-claim, 0% densest refugia, 76% rare-attainable
EFG footprint; no spike cells either way). Captures move by at most 3.2 points and corridors itself keeps 90% of its discretionary
capture as a co-benefit. So corridors shapes where the balanced anchor goes, not what it captures or what the core is — the
"places, not outcomes" pattern (E7). Decision 1 (B vs the registered 50/50 block) is the chat's; the statement under B would be:
"a map-level change of ~18% of discretionary land at the balanced anchor, no core-level or capture-level cost, corridor capture
retained at 90% as a co-benefit."
