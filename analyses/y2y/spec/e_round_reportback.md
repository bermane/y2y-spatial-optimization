# E-round report-back — v0.13 experiments measured (2026-09-02)

All of E8–E17 executed (notebooks 15–17; provenance results_log R9.1–R9.7, methods M4.18 +
M3.6). Three decisions requested (§6). One accounting disclosure added along the way (§5).

## 1. E12 — the estimator bracket: f is instrument-robust

corr(f_MGA, f_MAA) = 0.916 / 0.851 / 0.964 (S0 / S2 / S4); frequent-band sizes agree within
~5% (11.2k vs 10.8k; 4.7k vs 4.9k; 28.7k vs 30.1k km²); f=1 cores essentially identical.
Only the DIAMETER is estimator-sensitive (MAA 0.66–0.79 vs MGA 0.88–0.98) — as it must be:
D is defined by a maximizing probe, and random directions cannot find the extremes. So every
frequency claim survives the bracket, and D stays quoted from MGA (the correct instrument).
**Recommendation: full-14 MAA is unnecessary; report the 3-formulation bracket** and soften
E3's estimator-conditionality caveat to cite it.

## 2. E13 + E14 — mechanism confirmed; the aggregate band is not a per-value band

E13 (zero-solve): S4's f≥0.70 set lies **80.8% inside the m_soc θ-tail**; S0/S2's high-f
sets sit 4–5% on the tail, 1–4% on the connectivity spike — high frequency follows BINDING
CLAIMS, not valued layers. The Q2 explanation ("the carbon cluster out-connects the
connectivity cluster") is confirmed and cleared for Discussion. E14: in EVERY formulation,
~100% of members carry ≥1 value block below 0.95× its anchor capture (e.g., S0 members drop
core-habitat 0.428 → 0.364) — the 5% aggregate tolerance is routinely financed by
sacrificing whole blocks. The pre-registered trigger fired → E15 ran.

## 3. E15 — guardrails DOUBLE the nameable land at almost no flexibility cost

With per-block floors (capture_b ≥ 0.95·anchor_b) added to the band: S0's frequent tier
grows **11,247 → 23,108 km²** while D falls only 0.953 → 0.913 (C 0.020 → 0.042); S4 grows
28,748 → 34,787 km² (D 0.875 → 0.854). "No value block left more than 5% behind" buys ~2×
the committed area for ~4% of the diameter — commitment manufactured honestly (secondary,
pre-registered semantics; no budget conscription; no feature-semantics corruption).
A further variant ran at Ethan's request — **E15b, per-VALUE floors** (all 8
continuous values individually within 5%): it adds almost nothing beyond the block floors
(S0 frequent 23,996 vs 23,108 km²; S4 within noise) — **the commitment curve saturates at
the theme level**, so the elicited block granularity is the dial's natural resting point. **Decision: promote the guardrailed band to a headline product** (e.g., report F under both
semantics, with the guarded frequent tier as the applied deliverable)?

## 4. E17 — the latitudinal audit: an un-chosen 2-degree southern lean, now causal

T2: 20/40 EFGs have >90% of their footprint south of 53°N (median EFG mean-latitude 48.6°N).
T3 (leave-one-block-out anchors at S0; ALL pre-stated directions confirmed): vs the S0
anchor's mean discretionary latitude 50.96°N — biodiversity-out +1.18°N; carbon-out −1.18°;
connectivity-out −0.96°; core-habitat-out −0.17°; **EFG-out +2.11°N (Jaccard 0.695) — the
largest single force in the formulation.** Chain complete: the representativeness
foundation's southern geography anchors every plan ~2° south of where the other values would
put it — the strongest thing the formulation decided that nobody chose. **Decision: remedy
rung** — disclosure + scenario reading (my read: sufficient for paper 1, per the spec's
ladder), with applied-paper layer replacement noted?

## 5. E8/E9/E10 + one disclosure

**E8**: m_soc ×10 → Jaccard 0.996/0.994 vs anchors, capture exactly 0.3320 — satiation-
inertness confirmed at scale. **E9** (the lever-justification table): weights-only DRIFTS
(0.462, uncontrolled; densest-decile 0.632); the target is PRECISE (0.332 exact; 0.392);
**log-carbon DESTROYS per-hectare value (0.266; densest-decile 0.236)** — the frozen
screening's prediction confirmed by solve. **E10**: θ3 parks exactly (0.5520); **θ10 does
NOT bind — capture 0.229 vs target 0.121**: co-capture alone carries m_soc to ~0.23 under
S0 shares, so targets below the co-capture floor are decorations; the meaningful target
range is a window (floored by co-capture, priced by the Lorenz curve). Disclosure added
(M3.6): characterization, targets, and budget all live on the full 1.27M-cell extent with
explicit lock-in — PAs pre-bank 12–19% of each feature's total (m_soc: 17.6 of its 33.2-pt
target) and consume 50.0% of the 30% budget; audit capacities are unconstrained-by-lock-in
while the solve is lock-conditional (one mechanism behind R8.5's structural misses).

## 6. Decisions requested

(a) **E12**: accept the bracket; no full-14 MAA. (b) **E15**: promote guardrailed semantics
to a headline/applied product, or keep secondary? (c) **E17**: settle the remedy rung for
the EFG southern lean (disclosure + scenario reading vs more). Also for the record: E16
resolved to the sanctioned F-clustering fallback (min-boundary MILP fails the compute gate
at ~2.5M edge binaries).
