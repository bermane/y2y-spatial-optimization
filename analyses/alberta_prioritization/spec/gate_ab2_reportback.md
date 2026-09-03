# Gate AB-2 report-back (2026-09-03) — for chat: a decision the pre-registration did not anticipate

Numbers: `results_log.md` R5. Artifacts: `runs/ab_l/{A,B}/s0_ssp585_theta5/`, `spec/gate_ab2_verdicts.json`.

## What happened

1. **The Alberta near-optimal band is flatter than Y2Y's, not narrower.** D = 0.9999, C = 0 at both
   budget levels: a set of additions almost completely disjoint from the optimal one is within 5% of
   optimal. H-AB4 registered the opposite direction and is refuted.
2. **At g = 5% there is no core.** The frequent tier is 2 km² (A) / 0 km² (B); every discretionary
   cell appears in some near-optimal plan. Only at g = 2% does structure appear: 876 km² core,
   1,488 km² frequent (level A).
3. **The guardrails do nothing here** — the same members come back with or without block floors,
   and only 1 of 100 members ever drops a block below 0.95× anchor (parent: ~all). Cause: the locked
   estate already holds 24–71% of every feature, and the additions are a small slice of the unlocked
   land, so no rearrangement of the additions moves a block's capture by 5%.
4. The S4 pilot passes (binds at 0.772; θ-tail capture 0.877 ≥ 0.75).
5. **The nesting test is vacuous:** with empty cores N = 0 by arithmetic, so the frozen rule says
   "level B primary" without evidence.

The mechanism is one finding, stated once: **given the existing estate, the objective is nearly flat
over which 5–10k km² is added.** That is the honest applied result at the 5% tolerance — and it is
also why a 5% frequency surface cannot be Tim's map.

## The decision

The parent spec already sanctions the dial for exactly this situation (v0.13 rulings: "sanctioned
dials for cluster-drawing = tighter g (per-formulation surfaces at g = 2%) + the E12 bracket
reading"). Proposal, in three parts:

**(a) Presentational band for Alberta = g = 2%** (disclosed as a D-AB deviation in the applied layer
only). The estimand stays the 5% band and is reported as measured (empty core = a result about the
landscape, not a failure). The guarded/aggregate distinction is moot here and is reported as such.

**(b) Re-run the nesting test at g = 2%** — 07 is patched to add the 2% sweep at level B (~1 min);
08 now reports N at every band present at both levels and flags the 5% test as vacuous. The frozen
rule's threshold (0.80) is applied unchanged at the tightest band where cores exist. Pre-registration
status: the 5% outcome is recorded as it fell; the 2% evaluation is a disclosed amendment made
before any full run, on the parent's own sanctioned dial.

**(c) Primary budget level** then follows the 2% nesting result. If that too is vacuous or fails,
level B is primary by the realism argument (already your instinct) and A stays the methods mirror.

## What this means for the deliverable regardless of (a)–(c)

- Tim's map at AB scale will be a **2%-band frequency surface** with a core on the order of
  ~10^3 km² — an actionable list, and much smaller than either additions budget.
- The "opportunity landscape" statement is at its strongest here: within 5% of optimal, essentially
  any discretionary cell can be part of a near-optimal plan. Priority ≠ permission applies with force.
- The E1/E3/E11 machinery (AB-4) still runs at 5% for the methods mirror; the applied tiers use 2%.

Say (a)+(b)+(c) as written, or amend.
