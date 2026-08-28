# Gate 2 report-back — pool run executed, verdict NEAR-BINARY (2026-08-27)

For the Gate-2 review (spec v0.9.1 §2.9, §7): the fail branch fired; two decisions are
needed before anything else runs. §6 states them. Full provenance: results_log.md R6,
methods_log.md M4.10 / M5.7 / M6.6 / M6.7.

## 1. What ran

S0 (as frozen in scenarios_v1.json: mass-proportional split 74.2/25.8; weights refugia 1.460 /
conn 0.669 / corridors 1.171 / m_soc 0.465 @ t=0.332 / biomass 0.199 / birds 1.329 / mammals
1.708) solved three ways at full 1 km (1,272,914 PU), three folders:

| run | config | time | outcome |
|---|---|---|---|
| LP twin | HiGHS ipm, proportion | **6,516 s (109 min)** | 100.00% integral; objective 5.362810 |
| certified single | Gurobi binary, opt_gap 1e-4, NumericFocus 2 | **55 s** | 5.362860, cert gap 0.0009% |
| THE POOL | + PoolSearchMode=2, k=50, PoolGap=5% | **1,799 s (32.8× single)** | 50 solutions, all OPTIMAL |

True optimum pinned to [5.362810, 5.362813] (LP bound + pool best). Engine now records
per-solution solver provenance (objective/status/gap/runtime) in run_summary; objective
cross-check (engine vs exact recomputation from the representation CSV) reconciles to 3e-5
absolute (~5.6e-6 relative). All frequency and integrity cross-checks exact.

## 2. Verdict (pre-registered rule, frozen before the run): NEAR-BINARY

Rule (on the deduplicated pool, discretionary cells only): PLATEAU-RICH iff k_distinct ≥ 10
AND ≥5% of ever-selected discretionary cells have 0<f<1; NEAR-BINARY iff k_distinct ≤ 3 OR
<1%; else INTERMEDIATE.

Measured: k_distinct = **50** (no duplicates), BUT — discretionary union 190,926 cells;
**conditional (0<f<1) cells 165 = 0.09%** (<1% ⇒ fires); mean pairwise Jaccard **0.9999**;
**objective span across the pool 3.2e-6 relative** — nowhere near the 5% gap.

## 3. The mechanism (this reframes the verdict — M6.6)

PoolSearchMode=2 returns the k **best** solutions. S0's plateau at the optimum is so dense
(≥50 distinct solutions within 3.2e-6 of optimal, differing by a handful of cells) that the
enumeration never leaves the optimum's immediate neighborhood: **PoolGap acts as a bound,
never as a sampling target — the g=5% band was never sampled.** The within-cell estimand as
operationalized (§4 via add_gap_portfolio) therefore measures "indicator of the optimum," not
"membership across the g-near-optimal set." This is E5's enumeration-order-bias concern
demonstrated maximally, by the estimator itself, before E5 ran. Whether the 5% band is
actually diverse remains UNMEASURED by this estimator. Consequences: E4's k-grid is moot
under k-best (subsampling near-clones); E1 would trivially find no bias.

Note the finding is publishable regardless of the pivot: published solution-pool robustness
analyses commonly use exactly this mechanism.

## 4. T1 intended-vs-realized (certified single) — the standing diagnostic fired too

Captures: refugia 45.2% / connectivity 33.4% / corridors 26.0% / m_soc **33.2% (AT target)** /
**biomass 31.0%** (pre-run prediction band 30–37; anchors 25.9 co-capture floor / 41.3 a0 /
49.7 a1 — "co-benefit, not driver" achieved) / birds 33.0% / mammals 32.7% / intactness 29.9%.

**θ-tail capture rates (T1/E7 standing diagnostic): the pre-stated biomass expectation
FAILED.** Biomass tail mass capture **0.425** (was 1.000 at w=1 in a1); m_soc tail **0.435**
even though its total-capture target binds exactly. Reading (M6.7): **a total-capture target
does not protect the dense tail** — co-capture on cells chosen for other values satisfies the
claim off-tail, so the solver skips ~57% of both carbon tails. (Context: connectivity tail
0.980, refugia tail 1.000.) Reported per v0.9.1's commitment, not buried.

Realized-vs-intended influence: largest miss = m_soc +0.089 (realized 0.275 vs intended
0.186). Structural, not miscalibration: the satiating member realizes 100% of its claim while
diffuse members realize ~40–50% of their cap_max capacity under competition — Claim C's
stated first-order caveat, now measured. Invoke the iterate-once rule?

## 5. Also measured

- S0 LP relaxation effectively exact: 100.00% integral, LP-vs-MILP Jaccard 0.9957, max
  capture delta 0.0006.
- HiGHS-presolve pathology, worst case yet: the S0 LP twin took 109 min (Gurobi's equivalent:
  55 s). At 14 cells, HiGHS twins ≈ 25 h — should the ensemble's LP twins run on Gurobi's LP
  path instead, keeping HiGHS re-verification as a spot-check? (The open-verification story
  only needs the twin to be *verifiable* without Gurobi, not *produced* without it.)
- 14-cell ensemble cost under the current estimator: ≈ 7 h of pools + minutes of anchors.
- E4 seed written (runs/gate2_s0_ref/solutions.npz + cell_audit.json) either way.

## 6. The two decisions (requesting both in one pass — they bundle into ONE rebuild + re-run)

**D-A. Which estimator replaces k-best?**
  (a) **Diversity-controlled generation (Brunel-style MGA)**: iteratively maximize Hamming
      distance from incumbents subject to objective ≤ (1+g)·optimum. Feasible now: prioritizr
      cannot constrain its own objective, but the compiled-model extraction machinery from the
      false-certificate diagnosis lets us add the bound row + swap the objective in direct
      Gurobi calls; ~55 s/solve ⇒ k=50 ≈ 50 min/cell ≈ same order as the current pool.
      DESIGN CAVEAT to decide deliberately: max-dissimilarity samples the g-band's EXTREMES,
      not uniformly — f becomes "membership breadth across extreme members," a different,
      defensible estimand that must be pre-registered as such (uniform vertex sampling is
      intractable). A new degeneracy-verdict rule would be pre-registered with it.
  (b) **Accept within-cell degeneracy**: hierarchical estimand reduces toward
      one-solve-per-cell; Claim A collapses; pivot the paper to Claims B+C.
  (c) Add a demonstration problem where the within-cell correction matters.

**D-B. Does carbon get a tail-restricted feature?** If dense stands need a guarantee, the
formulation needs a θ-tail-masked carbon feature with its own target (re-audited under the
frozen §2.5 rules); that changes S0 ⇒ scenarios re-freeze ⇒ Gate-2 re-run — which is why
D-A and D-B should be decided together. Alternative: keep the tail result as a reported
finding (the diagnostic working as designed) and leave the formulation alone.

Also flagged: the twin-solver question in §5, and whether the m_soc +0.089 realized-share
miss triggers the iterate-once rule or is accepted as the documented structural property.

## 7. What stands regardless

The Gate-0/1 record; the certified S0 optimum (the anchor any MGA loop constrains against);
the pool-cost measurement; the LP-tightness result; both mechanism findings (M6.6, M6.7) as
paper material. Gate-2 artifacts are kept as the measured record — superseded if the
estimator changes, never deleted.
