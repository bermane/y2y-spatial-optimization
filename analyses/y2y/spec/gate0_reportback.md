# Gate 0 report-back — frequency-ensemble flagship (2026-08-27)

Status summary for the spec-v0.8 review checkpoint. Everything through Gate 0 is implemented,
solved, and validated on the final configuration; Gate 1+ awaits this review. Written to be
pasted into the design discussion.

---

## 1. What was executed

**Scope held:** Gate 0a (feature characterization audit) + Gate 0 (stopping-rule validation),
then stop. Nothing downstream was built: no S0 construction, no scenario (w,t) pairs, no pool
runs, no manifest freeze, no E-experiments.

**The campaign lives in `analyses/y2y/`** as four notebooks run in order: `01_feature_audit`
(Gate 0a, zero solves) → `02_solve` (arms via a batch cell) → `03_gate0_validation` (verdicts)
→ `04_results` (per-arm deep dive). Final configuration for every solve: **binary MILP, Gurobi,
opt_gap 1e-4, NumericFocus 2, w = t on every arm, dust-thresholded stack** (see §4).

## 2. Gate 0a — the audit (v0.8 §2.5, constants frozen: θ=5×, a_min=0.5%, t_min=0.15, λ=0.10)

Re-frozen on the final stack 2026-08-26; classifications INVARIANT to the conditioning change.

| feature | leverage | θ-tail area | implied target | class → lever |
|---|---|---|---|---|
| carbon m_soc | 0.884 | 4.06% | **0.332** | **concentrated-satiating → target** |
| carbon biomass | 0.801 | 1.17% | 0.066 < t_min | **diffuse-linear (REVERTED by rule) → weight** |
| transboundary connectivity | 0.461 | 0.20% < a_min | — | diffuse-linear → weight |
| climate macrorefugia (1/v) | 0.422 | 0.47% (near-miss a_min, also fails t_min) | — | diffuse-linear → weight |
| climate corridors | 0.263 | no crossing | — | diffuse-linear → weight |
| AOH birds / mammals | 0.232 / 0.181 | no crossing (watch item resolved: no tail) | — | diffuse-linear → weight |
| gHM intactness | 0.042 | — | — | **R3 inexpressible (disclosed)** |
| EFG block (40) | — | — | — | 36 rare-attainable + 4 unsaturated disclosed (F2.4, F2.9, T2.1, T6.4) |

- v0.8's expected outcomes all confirmed; the rules also discriminated a case the spec did not
  pre-call (connectivity fails on a_min — pinch-point spike, not a tail).
- **Universal transform screening (v0.8 amendment) paid off measurably:** log1p FLIPS m_soc to
  diffuse-linear (0.884→0.486 — the E9 log-arm story in one row) and pushes AOH birds below the
  expressivity floor (0.232→0.059). Feature cards (8 + EFG block + summary = 10 pages; the
  spec's "12 cards" is a disclosed miscount) rendered for review pre-solve.
- Archive per D2: budget-independent Lorenz/marginal curves; targets at any θ or budget are
  lookups (verified: θ=3× → 0.552, θ=10× → 0.120 from the npz alone).

## 3. Gate 0 — the five arms (all PASS)

All arms `WEIGHTS <- TARGETS` (w = t): pull = 1.00 everywhere; ONLY the stopping point varies.

| arm | carbon treatment | solve | key result |
|---|---|---|---|
| a0_control | none (t=1) | 17 s | m_soc capture **54.2%** (1.8× area share) — dominance WORSE than iter6's 45.5% after penalty-removal + 1/v; the problem the target solves grew |
| a1_protocol | m_soc t=0.332 only | 81 s | m_soc **exactly 0.3320**; Jaccard vs a0 0.78 |
| a2_flat30 | both pools 0.30 | 20 min | both **exactly 0.3000**; Jaccard 0.63 |
| a3_flat40 | both pools 0.40 | 21 min | both **exactly 0.4000**; Jaccard 0.79 |
| a4_pullcheck | conn w=t=0.6 (unreachable) | 20 s | **reproduces a0 EXACTLY — 0 of 1.27M cells differ** |

- **Targets bind at the kink, to four decimals, every time.** (Historical note: the superseded
  w=1 run showed capture can EXCEED a target via incidental co-capture — biomass 0.259 vs 0.066
  — so the spec's "lands at target (not above)" criterion is wrong as written; under w=t no
  overshoot occurred. Validation notebook implements the corrected criterion: only BELOW fails.)
- **a4 is the empirical proof of the w/t claim** — on exact certificates the binary MILP
  reproduces the control perfectly, as the LP did.
- **Where a1's freed ~21 pts of m_soc went:** biomass **+8.4** (see D1 below), birds +2.2,
  mammals +1.6, macrorefugia +1.1, connectivity +0.2, corridors **−1.4** (the spec's predicted
  destination was corridors — partly wrong). a2 (both pools capped) lifts the under-served EFGs
  0.22 → 0.53.
- **Relaxation tightness (supplementary-grade):** LP twins ~100% integral; LP-vs-MILP Jaccard
  0.97–1.00; capture deltas ≤1.4 pts. The LP prototype era is measured as sound.

## 4. Infrastructure findings (the numerics vignette — publishable methods material)

1. **Gurobi issued a FALSE optimality certificate**, twice, bit-identically: on the a4 arm its
   root LP mis-converged 0.42% high and certified the wrong point (best bound = incumbent).
   Caught only because the integral LP twin pins a4's true optimum EXACTLY. Cause: matrix range
   **[1e-11, 1e+05]** — resampling dust in the carbon layers against the shortfall scaling.
   Gurobi's own log warned about the range.
2. **Fixes, both layers:** (a) `numeric_focus` (Gurobi NumericFocus 2) engine-wide — with it the
   same solve found the exact optimum **60× faster** (17 s vs 1080 s; careful arithmetic was
   faster because the un-focused simplex was numerically lost); (b) **dust thresholding** in 02:
   cells holding <1e-9 of a feature's total → 0 (biomass 46,097 cells / 0.0015% of mass, m_soc
   19,262, connectivity 538, others clean). Matrix range now **[1e-4, 1e5]** in every log;
   audit invariant (§2). Also fixed en route: Gurobi-13 renamed pool field `xn`→`poolnx`
   (breaks prioritizr 8.1.0's gap portfolio; shimmed), and portfolio `solve()` returns a list
   (engine now stacks). Pool path verified toy-scale; **not yet exercised at 1 km** — that is
   Gate 2's first act.
3. **Standards adopted (ratify):** opt_gap **1e-4** for single-solution solves (pool gap g stays
   a separate, deliberately loose estimand parameter); NumericFocus stays on as defense in
   depth; **the LP twin beside every certified MILP becomes stated methodology** — it caught
   the false certificate and the earlier HiGHS presolve pathology.

## 5. Discussion points for THIS review (in priority order)

**D1 — The biomass leak (S0 carbon-block design).** a1 demotes m_soc and biomass promptly
absorbs +8.4 pts of the freed budget (0.41→0.50 capture) — weight-levered at pull 1, it simply
expands. Is that acceptable ("biomass is a legitimate diffuse value") or a leak ("we demoted
carbon and the other pool took the money")? v0.8's S0 already plans carbon block = SOC target +
biomass weight; Gate 1 must set the block's influence share knowing this number. Needs a
position before S0 is constructed.

**D2 — Choose S4's carbon-forward level (the spec says choose at Gate 0).** Evidence: relaxing
the rule 5×→3× gives m_soc target **0.552** (@ 9.8% of region, from the archive); flat-40 gives
a map at Jaccard 0.79 from control; the control itself brackets "extreme carbon-forward" at
54.2% capture. Recommendation: **the 3× relax** — keeps S4 on the same derived-rule axis as S0
(θ is the dial, E10 already stress-tests it), rather than introducing a flat level with no rule.

**D3 — Recalibrate the degeneracy prediction (§2.8) before Gate 2.** The 68k-cell a4-vs-a0
divergence that looked like plateau evidence was numerics artifact — exact solves reproduce
EXACTLY. Remaining plateau evidence is thinner: LP-vs-MILP swaps ~2% of cells at ≈equal
objective. E1's expected effect may be smaller than §2.8 predicts; the Gate-2 fail-branch
(pivot to Claims B+C, or add a demonstration problem) should be treated as live, not remote.
Also note: with certificates now exact and cheap, the pool gap g is cleanly anchored.

**D4 — E5 has a feasibility problem.** The "shuffle-on-HiGHS" comparator requires binary
decisions, and HiGHS cannot solve the 1 km binary MILP (that is why Gurobi exists here). E5 as
written (Gurobi pool vs HiGHS-shuffle vs Brunel) cannot run at 1 km. Options: drop the HiGHS
arm (pool vs Brunel-style only), run the HiGHS arm at 2 km with a scale caveat, or re-scope E5.

**D5 — Ratify the two data/solver changes into v0.9:** the dust-threshold rule (pre-processing,
with per-feature drop disclosure + audit invariance as the methods text) and the solver
standards of §4.3. Both are implemented and validated; they need to live in the spec, not just
the repo.

**D6 — Climate axis build-out is unblocked and ready for Gate 1.** Settled here: **SSP245 vs
SSP585, both 2071–2100** (horizon fixed ⇒ the axis means emissions; measured top-30% Jaccard
0.574). The 1/v orientation dissolved the shared-anchor problem (six realizations, leverage
0.422–0.516 — no anchor parameter needed). §3.2's "RCP4.5-2050s vs RCP8.5-2080s" must be
corrected in v0.9. Implementation (orient both realizations into the hand-off) is a small 02
extension, ready when Gate 1 starts.

**D7 — Spec corrections owed to v0.9** (accumulated, none blocking): (1) §2.7/§8 compute model —
all portfolios are Gurobi-gated (shuffle/cuts need binary), correct model ≈ cells × one
MILP-with-pool; 12 s/solve was the LP; (2) §2.3 capacity-vs-outcome (36/40 EFGs CAN saturate;
5 DID in iter6); (3) §3.2 climate axis (D6); (4) Claim C `w = influence/leverage` valid only on
the linear arm — use the two-regime swing `w·(min(cap_max,t)−cap_min)/t`; (5) Gate-0 pass
wording "lands at target (not above)" — co-capture refutes it; (6) the §4 numerics vignette and
standards; (7) "12 cards" count.

## 6. Open items on the runway (post-review)

Gate 1: S0 equal-influence-per-block construction (needs D1) + scenario (w,t) pairs + climate
layers (D6). Gate 2: first 1 km pool run (k=50, g=5%) — doubles as the pool-cost measurement
and the real degeneracy test (D3); WLS allows 2 concurrent sessions ⇒ cells run serially.
Gate 3: manifest freeze. Gate 4: ensemble + E1–E4, E7–E10 (E9's log-carbon arm already has its
screening-level evidence: log1p flips m_soc's class).
