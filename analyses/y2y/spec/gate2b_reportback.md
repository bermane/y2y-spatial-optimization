# Gate 2a/2b report-back — S4 pilot PASS + MGA verdict PLATEAU-RICH (2026-08-30)

Everything the v0.11 plan queued has run clean. Two results packages + the Gate-3 request.
Provenance: results_log R7; methods_log M4.13/M4.14/M5.8; runs in `iter10_y2y_s4_pilot/` and
`runs/s0_ssp585_theta5/`.

## 1. Housekeeping first: the tail rescission (M4.14)

After v0.11 landed, Ethan RESCINDED the pre-authorized escalation entirely: no tail masks as
separate features under any standing authorization; a pilot failure returns to design
discussion. Implemented: config wiring removed, contingency notebook archived
(`archive/08b_contingency_tails_RESCINDED.ipynb`), knowledge kept as backup (the machinery
was incidentally executed once under v0.10 and verified — both tails rare-attainable, exact
frozen-T2 matches — layers quarantined). The next spec revision should absorb this: v0.11's
§2.5/§3.1 contingency language is superseded.

## 2. The S4 pilot — PASS, mechanism validated (R7.2)

Certified single solve (`iter10_y2y_s4_pilot`, OPTIMAL, 54 s, objective 5.0144):

| | S0 (measured) | S4 pilot | band |
|---|---|---|---|
| m_soc θ-tail mass capture | 0.435 | **0.960** | ≥ 0.75 PASS |
| biomass θ-tail mass capture | 0.425 | **0.772** | ≥ 0.75 PASS |
| m_soc total capture | 0.332 (at target) | 0.552 (at target) | — |
| biomass total capture | 0.310 | 0.329 | — |

The mechanism claim held precisely: biomass TOTAL capture moved +1.9 pts while its TAIL
capture nearly doubled — carbon-forward pressure REDIRECTED capture dense-first rather than
buying more carbon everywhere. Places-through-pressure works on the existing stack with zero
formulation changes; full stack symmetry across all 14 formulations. The S0→S4 tail contrast
(0.435/0.425 → 0.960/0.772) is F9 (amount-vs-places panel), ready-made.

## 3. Gate 2b — MGA reference run + the frozen verdict (R7.3–R7.6)

**Execution:** anchor exact (gap 0) in 8.1 s, reproducing iter9's 5.3628; three k=50 sweeps
(g = 2/5/10%) in **~32 min total** (iterations 10–16 s, not the predicted ~55 s); 150/150
members, zero duplicates, zero time-limits, every band certificate binding EXACTLY at its
wall. Ensemble re-projection: ~45–60 min/formulation ⇒ ~10–14 h for all 14 formulations, serial.

**Verdict (rule v2, frozen pre-run, hash v2_8db80fed1c702638): PLATEAU-RICH — Claim A
carries.** At g=5%: **D = 0.953** (max pairwise Hamming = 95% of the theoretical two-disjoint-
selections ceiling), **C = 0.020** (f=1 core = 2% of the discretionary selection). Thresholds
were D ≥ 0.10 and C ≤ 0.90 — passed by an order of magnitude, not at the margin.

**The core-erosion curve f(g) — E4's central product, and a headline finding:**

| g | always-core (f=1) | union (appears in SOME plan) |
|---|---|---|
| 2% | 22,866 cells = 12.0% of selection | 737k discretionary cells |
| 5% | 3,829 = 2.0% | 1.07M |
| 10% | **0 — zero** | **1,081,885 ≈ every discretionary cell (1,082,069 exist)** |

At 10% tolerance, no individual discretionary cell is in every near-optimal plan, and
essentially every cell in the landscape is in some near-optimal plan. Paper sentence:
"almost any cell CAN be part of a near-optimal plan; almost no cell is REQUIRED by one" —
the strongest possible motivation for frequency surfaces over single maps.

**The two-instrument geometry (M6.6 + this):** k-best measured the peak (50 best solutions =
near-clones within 3.2e-6); MGA measured the bowl (near-total redraws within a few percent of
optimal). A sharp, essentially unique optimum on a very wide, shallow near-optimal plateau.
Both results are paper material; the contrast IS the E5 story, obtained as a by-product.

## 4. Requesting: Gate 3 ratification

The rule's own consequence line says proceed. Gate 3 = manifest freeze per §9 (14 formulations:
6 scenarios × 2 climate + 2 crossed; estimator mga_maxham_v1 with k=50 g=5%, MIPGap_dist
0.01, TimeLimit_iter 900; opt_gap 1e-4; NumericFocus 2; verdict_rule v2_8db80fed1c702638;
per-formulation artifact set anchor/mga/kbest/Gurobi-path twin; layer sha256s) + pre-registration
freeze, then Gate 4 (the ensemble + E1–E4, E7–E10). Items to settle in the freeze: (a) spec
revision absorbing the rescission (§1 above); (b) confirm the climate-formulation mechanics
(constant-influence-per-scenario: weight vectors re-derived per formulation from layer-specific
swing, per §3.2); (c) E4's extra g-levels stay reference-cell-only.
