# Gate AB-0a report-back (2026-09-03) — for chat ratification before AB-0

Numbers: `results_log.md` R1–R2. Artifacts: `spec/ab_extent_v1.json`, `audit/audit_objects_ab/`,
`audit/feature_cards_ab/` (review the 10 pages before AB-0 solves — the protocol's human checkpoint),
`figures/ab_extent.png`, `figures/F8_ab_marginal_density_trajectories.png`.

## Headlines

1. **The Alberta strip is already 32.9% protected** (27,972 of 85,133 km²). Under a 30×30 lens the
   areal target is met; the questions are composition and additions. D-AB5 fired as pre-registered
   (inherited 30% budget infeasible); effective budget frozen at 44.7% = locked + 10,083 km² of
   additions (X = 0.1764, the parent's realized fill rate).
2. **Scale-transfer verdict: the flat layers do not recover contrast in Alberta — most get flatter.**
   Only gHM (0.042 → 0.086, still under λ) and connectivity (+0.06) gain; macrorefugia, corridors,
   birds, mammals lose. **AOH mammals flips to R3-inexpressible**; corridors sits exactly on λ.
   S5 stays inexpressible. (H-AB1 refuted on its strongest expectation.)
3. **Carbon is scale-stable and pre-satisfied.** m_soc keeps its concentrated-satiating class and
   derives t = 0.322 (parent 0.332) — but the locked estate already banks **71.4%** of Alberta's
   mineral-soil carbon, so the target is met at the root and the zero-solve floor for a *binding*
   carbon target is ≈ 0.765. The parent's S4 recipe (θ 3× → 0.642) would be a decoration here.
4. EFGs: 27/40 present, 20 rare-attainable, 7 unsaturated (parent 4). Four alpine/ice classes are
   >90% banked.
5. Geography: the discretionary land is the foothills band plus the unprotected northern tip north
   of Willmore/Kakwa — the Upper Smoky Nature-First Zone country (AOI-2 will matter).

## Decisions needed before `04_ab0_scenarios` is built

**D1 — Biodiversity block with one levered member.** Mammals is inexpressible by the frozen rule.
Mirror-faithful option (recommended): mammals joins the OUTSIDE set at w = 1 (disclosed, like gHM),
the biodiversity block's share is carried by birds alone, S3 (biodiversity-forward) doubles birds
only. Alternative: keep mammals in the block at its derived weight regardless (breaks the rule;
would need a D-AB entry). *Recommend the mirror.*

**D2 — S0–S3 carbon block under pre-satisfaction.** Mirror-faithful (recommended per the parent's
v0.10 ruling — intended and realized side by side, no iteration against realized swing): keep
t = 0.322 for m_soc in S0–S3 and let T1 report the realized carbon influence as arriving via
biomass only; the pre-satisfaction becomes the applied report's explanatory spine (spec §4).
Alternative: re-derive m_soc's target lock-conditionally (θ on the discretionary tail only) — a
new deviation. *Recommend the mirror; the AB-1 anchors measure the consequence.*

**D3 — S4 (carbon-forward) θ-relaxation must clear the floor.** Parent recipe = θ 3×. On the AB
archive θ 3× → 0.642 (< 0.765 floor: does not bind), θ 2× → 0.772 (bare), θ 1.5× → 0.848.
Options: (a) θ 2× — the smallest relaxation that clears the proxy floor, closest to the parent
recipe; (b) θ 1.5× — clears with margin; (c) keep θ 3× and let the pilot show non-binding as a
finding (wastes the S4 cell). The pre-registered S4 band (θ-tail mass capture ≥ 0.75 both pools)
also needs an AB reading: biomass's θ-tail here is 0.05% of the extent (θ-target 0.003) — the
band is vacuous for biomass; propose scoring S4 on m_soc's tail only, disclosed. *Recommend (a),
with the pilot's certified capture vs the true floor as the AB-1 check; the proxy is a lower
bound.*

**D4 — Corridors at λ exactly (0.100).** Rule says ≥ λ passes → diffuse-linear, weight-levered.
Keep by the rule and disclose as marginal (recommended); its lever will be near-inert either way.

**D5 — D-AB6 buffer distance.** 10 km proposed; 5/10/20 km sensitivity rows are zero-solve.
Freeze 10 km?

**D6 — X confirmation.** 0.1764 (parent fill rate) as frozen, or override.

Not decisions, noted: the 245 climate realization's AB leverage is computed at AB-0 when
`scenario_weights(layer_paths=…)` runs; the feature cards' summary-sheet diamonds are parent
values (AB raw/avoid leverages printed in 02: gHM 0.729, macrorefugia 0.286).
