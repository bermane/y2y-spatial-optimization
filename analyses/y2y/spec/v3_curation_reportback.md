# Curated-block re-solve (manifest v3) — report-back for the spec chat (2026-09-09)

_Study plan v0.17 / v0.17.1 / v0.17.2 and package spec v1.7 are BUILT and verified headlessly where no solve is involved.
Logs: methods_log M2.11 (the curation under rule R0), M4.26 (manifest v3 re-solve), M4.27 (rarity-scaled targets),
M4.28 (the necessity test (E19), pre-registered); results_log R10.19 (block card v3) with R10.20–R10.22 placeholders.
Naming convention applied. Nothing solved yet — the re-solve is Ethan's ~22 h run._

## 1. The clip-edge ruling (v0.17.3) — implemented as manifest v3.1

The boundary-proximity check (R0 iii) had flagged five of the six small retained classes (72–100% of their cells within
10 km of the study boundary). The ruling keeps all 22 classes and derives the rarity-scaled targets from each class's
footprint in the study extent buffered by 250 km (100/500 km as sensitivity), counted on the GET archive maps. Measured:

| class | on-extent target (v3) | +250 km target (v3.1) | share of the +250 km footprint inside the extent | rare in the window? |
|---|---|---|---|---|
| F1.1 Permanent upland streams | 0.94 | **0.50** | 20% | yes (also at +100; not at +500) |
| F2.1 Large permanent freshwater lakes | 0.71 | **0.49** | 39% | yes (at all three buffers) |
| T6.1 Glaciers and perennial snowfields | 0.84 | 0.36 | 21% | no |
| T5.4 Cool deserts and semi-deserts | 0.87 | **0.105** | 9.5% | no |
| F1.6 Episodic arid rivers | 0.66 | **0.101** | 11% | no |
| T2.2 Deciduous temperate forests | 0.60 | 0.15 | 11% | no |

Twelve of the twenty features sit at the 0.10 floor. The diagnosis holds: the flagged classes are edges of ranges
centred outside the line, and they now stop pinning by construction; only upland streams and large lakes are rare in
the regional window, so the Act 1 representativeness layer votes on those two — thin, as v1.7 expects. Manifest v3.1
(sha 259f35ed…; weights unchanged; v3 superseded before any solve) is what 12 and 18 solve.

## 2. What the curation did (R10.19)

40 → 22 classes → 20 features (12 anthropogenic out; the point-record class F2.10 out; the sub-grain classes F2.6, F2.2,
F1.4, F2.3 out — below one native GET cell (~330 km²); F2.9 out — an envelope over 40% of the extent; TF1.6+TF1.7 and
S1.1+SF1.1 merged). Re-derived on the 20: rare-attainable **17/20** (was 36/40; T2.1, T6.4, F2.4 cannot be captured in
full within the budget); the ≤1%-footprint companion **6** (was 13); classes > 90% south of 53°N **9/20** (was 20/40;
median feature latitude 52.6°N) — half of E17's southern skew was artifact. Alberta mirror: 27 → 15 classes / 13 features,
stack built.

## 3. Rarity-scaled targets (M4.27, now window-derived per M4.29)

Rodrigues et al. (2004) convention on footprint within the PU: 1.0 at ≤ 1,000 km², 0.10 at ≥ 250,000 km², log-linear
between. Result: 0.10 for T2.1 / T6.4 / F2.4 / S1.1_SF1.1, 0.13–0.36 for the mid-sized classes, 0.60–0.94 for the six
small ones. One-line switch back to flat (`config.EFG_TARGET_RULE = "flat"`) then re-run 11b (minutes). Weights are
unchanged and asserted equal to v1's.

## 4. Build and run order (Ethan) — one command

`caffeinate -i bash analyses/y2y/run_v31.sh` from the repo root runs every step below in order, in place, resumable, and
handles the E19 gate itself. The table is what it does:

| step | notebook | what | cost |
|---|---|---|---|
| done | 11b curation + freeze v3 → v3.1 | both v3 stacks, block card, window footprints, targets, `manifest_v3.1.csv` (sha 259f35ed…) | minutes (ran) |
| 1 | 12 (`VERSION <- "v3.1"`) | anchors + MGA + twins, 12 design formulations → `runs_v3.1/` (k-best skipped) | ~10–12 h |
| 2 | 13, 15 | F, E1, E7 (T1), E11 → `spec/v3.1/`; E13 masks, E14 trigger, E17 T1/T2 on the 20 features (need only 12) | minutes |
| 3 | 18 (`VERSION <- "v3.1"`) | guarded sweep + S0 guarded MAA spot-check | ~12 h |
| 4 | 18b T2 | leave-EFG-out anchors ×12 | ~15 min |
| 5 | 18c | adequacy-forced set, core partition, T2 agreement, the 50% gate | minutes |
| 6 | 18c → 18b T3 | the no-EFG ensemble — ONLY if the gate opens | ~9 h + guarded |
| 7 | 19 → 20 | package v1.7 (archives the artifact-block package; adequacy-pin captions; E19 appendix) | ~20 min |

One switch (`config.Y2Y_VERSION`, env-overridable) selects everything; v1 is byte-identical and reproducible
(`Y2Y_VERSION=v1`); the R notebooks assert the block they solve on; never run two versions' R notebooks at once.
Verified without solving: 11b end-to-end; 12/18 dry-plans list 12 formulations on the 20-feature block; 13/15/19/20
under `Y2Y_VERSION=v1` reproduce yesterday's records byte-for-byte.

## 5. Pre-stated expectations to check against (M4.28)

The necessity test (E19): a real but MINORITY forced share of the core; T3 not triggered. If the forced share exceeds
50%, the no-EFG ensemble runs and the core is reported as "predominantly adequacy-forced".

## 6. Stage 2

Alberta re-run (09 re-freeze → 10–13 + 02 block card) on `aligned_stack_ab/iucn_efg_v3/`; needs the AB spec mirror
re-pinned to v0.17 first.
