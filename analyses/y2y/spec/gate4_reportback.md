# Gate 4 report-back — the ensemble is measured (2026-09-01)

All 14 formulations solved and analyzed (Gates 3+4 complete). Full provenance: results_log
R8; methods_log M4.15–M4.17, M5.9–M5.11. Requesting Gate-5 entry (§5).

## 1. Execution record (R8.1–R8.2)

Manifest frozen (sha d45668bb…, committed = pre-registration). 13 open formulations solved
serially: anchors 44–58 s (all exact); Gurobi LP twins 10–14 s (every LP ≤ MILP check
passed); MGA 36–50 min each (~55 s/iteration); k-best pools 549–1,822 s at full 50 — except
`s3_ssp585_theta5`, which hit the 12 h time limit with 38/50 (same scenario on the 245
layer: 18 min; pool difficulty is formulation-specific, spread 79×; disclosed as certified
in-gap incumbents, not a proven top-38). Wall ≈ 22 h.

## 2. The headline results (R8.3–R8.4)

**F (Claim A):** across 14 value/climate positions × 51 maximally-diverse plans each, the
ensemble "always" band is **EMPTY — no discretionary cell appears in ≥95% of plans**. The
strongest tier is frequent (F ≥ 0.70): **6,816 km²**. Bands: frequent 6,816 / conditional
93,408 / rare 951,972 / never 29,689 km². `F_surface.tif` is the deliverable.

**E1 — the hierarchical estimand earns its keep:** mean |F − F_naive| = **0.169**, max 0.755;
726,287 cells (67% of ever-selected land) shift by >0.1 when within-formulation pools replace
one-solve-per-formulation. Under the k-best estimator this correction would have been ≈0.

**E3 — variance decomposition** (estimator-conditional; within = MGA band breadth):
**within-formulation 95.2% / value scenario 4.4% / climate 0.2%**; the crossed-formulation
carbon-regime contrast is small (mean |Δf| 0.017 / 0.002). Near-optimal freedom dwarfs value
disagreement; the climate axis barely registers on the frequency surface even though the
refugia layers themselves differ (top-30% Jaccard 0.574). Every formulation is plateau-rich
(D_s 0.809–1.000); both S5 formulations hit D = 1.000 exactly — when the pushed value is
inexpressible, a complete discretionary-turnover plan exists within 5%.

## 3. E7 — outcomes vs places (R8.5)

Anchor captures move in narrow ranges across all 14 formulations (refugia 0.40–0.49,
connectivity 0.31–0.39, biomass 0.27–0.33, birds/mammals ±3 pts) while anchor MAPS differ at
Jaccard down to 0.373: **value scenarios reallocate places far more than outcomes.** θ-tails:
S4@585 holds the pilot band (0.959/0.774); S4@245 = 0.974/**0.716** (biomass marginally below
0.75 under the 245 layer — the pilot was registered on 585; reported as a finding); crossed
formulations (deep target WITHOUT doubled weights): s1x 0.697/0.302, s3x 0.584/0.353 — the
dose-response completing M6.7: places semantics needs target AND weights together.

## 4. E11 — the two-level spread (R8.6, F10)

Between-anchor Jaccard 0.373–0.931 (mean 0.520); the envelope comparison lands cleanly:
within-formulation diameters (0.81–1.00) EXCEED between-anchor distances — value disagreement
fits INSIDE the near-optimal freedom of any single position. Δ(s,s′): **156/182 ordered pairs
sit inside each other's 5% bands — certified no-regrets value pluralism** — and all 26
out-of-band pairs are anchors evaluated under CARBON-FORWARD objectives (Δ 0.085–0.093): the
deep m_soc target is the one value position whose demands other near-optimal plans genuinely
fail. (Integrity note: the Δ diagonal self-check caught a layer-consistency bug on first
computation — ssp245 objectives initially scored on the 585 layer; fixed, diagonal now
≤ 9.3e-6, which simultaneously validates the capture-based reconstruction. M5.11.)

## 5. Requesting Gate-5 entry

Proposed: ratify R8 into the results inventory and begin the write-up architecture (the
two-instrument geometry + empty-always-band + E1 bias as the Claim-A spine; E7/E11 as Claims
B/C; numerics vignette as supplementary methods). Open items for the chat: (a) are E8–E10's
supplementary solves (notebook 14: inertness demo, weights-only + log-carbon arms, θ
sensitivity) wanted pre-draft or as revision ammunition? (b) Gate 5's blocking literature
checks (García-Quintas full text; Lehtomäki & Moilanen skim) — scheduling; (c) the
terminology note (M4.17): repo uses "formulation" for design points; next spec revision
should align.
