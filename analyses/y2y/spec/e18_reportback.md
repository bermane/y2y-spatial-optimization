# E18 report-back — weight vs substitutability, all five arms (2026-09-08)

_For the spec chat. Provenance: `runs/e18_*` (21), `22_e18_analysis` → `spec/E18_dose_table.csv`;
results_log R10.13–R10.15; methods_log M4.21–M4.22 (+ addendum). Everything below is guarded (5 % band,
per-block floors), SSP585 only, k = 50, Gurobi certificates 50/50 in band for every arm._

## 1. Status

E18 is closed. Five arms ran (~55–66 min each): connectivity ×2 and ×5 on S2, biodiversity ×2 and ×5 on S3, and the
carbon **weights-only** counterfactual (S4's registered weight vector with m_soc's target reset from 0.552 to S0's
0.332 — carbon's influence share stays 0.499 because the swing normalization is target-insensitive, so this is
exactly "S4's share doubling at S0's targets", the lever S1–S3 get).

| scenario | influence share | lead vs refugia¹ | tier km² | own land km²² | enrich led / refugia | max F | D | verdict³ |
|---|---|---|---|---|---|---|---|---|
| Connectivity-forward (registered) | 0.50 | 1.6 | 11,086 | 861 | 1.37 / 4.65 | 1.00 | 0.963 | — |
| Connectivity ×2 (4× S0 weight) | 0.67 | 3.1 | 12,687 | 7,925 | 2.30 / 2.44 | 1.00 | 0.942 | AMBIGUOUS (crossover) |
| Connectivity ×5 (10× S0 weight) | 0.83 | 7.8 | 34,705 | 31,780 | 2.12 / 0.88 | 1.00 | 0.845 | WEIGHT-LIMITED |
| Biodiversity-forward (registered) | 0.50 | 1.7 | 6,471 | 521 | 1.15 / 4.24 | 1.00 | 0.969 | — |
| Biodiversity ×2 | 0.67 | 3.5 | 1,024 | 0 | 1.26 / 7.02 | 1.00 | 0.999 | SUBSTITUTABLE |
| Biodiversity ×5 | 0.83 | 8.7 | **0** | 0 | — (empty tier) | **0.63** | **1.000** | rule: AMBIGUOUS (NaN); substantively substitutable |
| Carbon-forward (registered, m_soc t 0.552) | 0.50 | 4.6 | 34,787 | 20,329 | 3.83 / 2.07 | 1.00 | 0.854 | — |
| **Carbon, weights only (t 0.332)** | 0.50 | 7.6 | 16,425 | **763** | 1.40 / 4.03 | 1.00 | 0.927 | **SUBSTITUTABLE** |

¹ per-cell min-shortfall cost of the led block's 10,000 densest unprotected cells ÷ refugia's, same (w, t).
² tier cells outside the 12-position core and outside the other scenarios' tiers. ³ pre-registered rule (M4.21).

## 2. Findings

1. **Carbon's Act-2 land is the target's doing, not the weight's.** With the same share doubling the other three get,
   carbon-forward is refugia country like the rest: tier 72 % inside the core (S4: 31 %), own land 763 km² (S4:
   20,329; S1–S3: 0–861), refugia enrichment 4.0 vs carbon 1.4. Mechanism, read off the members' m_soc capture: under
   t = 0.552 the members must dip below target to leave the dense tail (0.530–0.552 — they pay shortfall, the tail stays
   pinned); under t = 0.332 they never do (0.332–0.380): the θ-tail (4 % of the region) meets the target with a reservoir
   of nearly-as-dense cells outside the selection to swap in for free, whereas the deeper target has already consumed
   that reservoir. Binding scarcity (E13) is created by the target exhausting the substitutes.
2. **The lead-magnitude currency is conditional on the target binding.** The weights-only arm scores 7.6× refugia (above
   S4's 4.6, same weight over a smaller t) yet owns nothing, because the per-cell cost is charged only while the value
   sits below target. Together with biodiversity ×5 (8.7×, no tier) that gives two necessary conditions beyond the
   score: a steep tail AND a binding target / exhausted substitutes. Reported with this scope; not redefined (M4.22
   addendum).
3. **The two diffuse values differ.** Connectivity crosses over between share 0.67 and 0.83 (its spike/pinch-point
   structure reaches the pinning price at ~4× the elicited emphasis); AOH richness never pins at any dose — raising its
   share only dissolves refugia's pinning (tier 6,471 → 1,024 → 0 km², max F 0.63, D = 1.000).
4. **Fairness statement (paper + deck):** "carbon-forward is the only scenario that also states a security target
   (55 % of dense soil carbon); given only the share doubling the other values get it would own ~760 km², not ~20,300."
   Registered scenarios unchanged (M4.22). The deck now carries an E18 slide (dose table) and this caveat on the
   carbon-forward Act-2 slide.

## 3. Decision requested — should S1–S3 lead harder (3–4× S0) so the applied product shows where those themes have value?

Ethan's framing: this is applied work; the goal is to identify areas where connectivity / biodiversity / core habitat
have value, not to keep the registered design for its own sake. Two measurements bear on it (R10.15, zero-solve).

**(a) What it costs Act 1.** Swapping an arm in for its scenario's SSP585 formulation and re-voting the 12-position
core (245 twin unchanged, so these are lower bounds — the twin would move the same way):

| swap | core km² (registered 16,895) | Jaccard | lost / gained |
|---|---|---|---|
| S2 ×2 (4× S0) | 15,412 | 0.904 | −1,555 / +72 |
| S2 ×5 (10× S0) | 13,730 | 0.805 | −3,240 / +75 |
| S3 ×2 | 15,970 | 0.943 | −943 / +18 — for 0 km² of own land |
| S3 ×5 | 15,202 | 0.891 | −1,771 / +78 |
| S2 ×2 + S3 ×2 | 14,512 | 0.856 | |

**(b) Whether a tier can say "where the theme has value" at all.** The richest decile of unprotected land holds only
18 % of connectivity's value and 14 % of biodiversity's (108,188 km² each); 2–3 % of that decile is in the core. As the
weight rises the connectivity tier moves INTO the decile (share of tier inside it: 29 % → 87 % → 100 %) but never
covers much of it (2.9 % → 10.2 % → 32.1 % of the decile); the biodiversity tier does neither (20 % → 43 % of 1,024 km²
→ empty). A frequency tier answers "where is this theme irreplaceable within near-optimality"; for a diffuse value that
is a sliver of where the value is, by the nature of the data (leverage/concentration), not by our weights.

**Options.**

- **A (recommended). Keep S1–S4 as registered for the ensemble, the core and the paper; answer the applied question with
  products that already exist.** (i) Connectivity: an *emphasis ladder* as an Act-2 companion — registered (2× S0) →
  4× S0 → 10× S0, i.e. "at the elicited emphasis connectivity-forward re-affirms the core plus ~860 km²; if connectivity
  is dominant, these 8–32 k km² of pinch-point land are its own" — from the E18 arms already solved. SSP585 only unless
  we add the two 245 twins (~2 h) so the ladder pools like the rest of Act 2. (ii) Biodiversity: the finding IS the
  product — no irreplaceable places at any emphasis; every near-optimal plan holds ~34–36 % of AOH richness whatever
  leads; the richness layer is the value map and the applied statement is coverage of it by the tiers (T-D3 / tier
  achievement) plus Act 3 ("work where feasibility is positive"). (iii) Core habitat: already pins through refugia
  (owns 29,249 km²); more weight just swallows more map. Cost: 0–2 h of solves, no pre-registration change, no core
  erosion, no downstream re-runs beyond 19/20.
- **B. Re-register S2 only at share 0.67 (4× S0, the crossover) — connectivity is the one diffuse theme where weight
  buys places.** Cost: 245 twin (anchor + guarded + unguarded MGA, ~2–3 h) + unguarded MGA for the 585 arm for the
  paper's Claim-A estimand (~1 h), re-run 13/15/17/19/20, manifest v2 with the supersession disclosed (paper reports
  the registered F14 and the applied v2 set); Act 1 loses ~1.5 k km² (585 only; ~2–3 k with the twin); replaces one
  asymmetry (carbon's target) with another (one scenario at 4×, two at 2×). Defensible only if Y2Y's elicited
  "connectivity-forward" genuinely means "connectivity dominant".
- **C. S1–S3 all at 3–4× (the question as posed) — not recommended.** S3 gains nothing at any dose and erodes the core
  (−943 km² at ×2 for 0 km² own); S1 does not need it; only S2 benefits. A target lever for the diffuse values is not
  available either: their θ-rule targets are already 1.0 (never met, cost charged on every cell); a lower target
  reduces pressure (E10).

If A: I add the connectivity ladder to 19/20 (map + a T-D2 row per rung) and the biodiversity coverage line to the
Act-2 biodiversity slide; say whether to solve the two 245 twins. If B: I write the v2 freeze (11b) and the run plan.

## 4. Bookkeeping

- Logged: R10.13 (table now includes the carbon rows), R10.14 (cont.) outcome + mechanism + currency scope, R10.15
  (this section's measurements); M4.22 addendum. 22 now computes max f, Gate-2b D (max pairwise Hamming ÷
  2·discretionary-selected) and the currency, so `spec/E18_dose_table.csv` is the single source — the hand-computed
  values reproduced exactly.
- Deck: E18 slide (13 of 19) + carbon-target caveat on the carbon-forward Act-2 slide; `table_png` column widths fixed.
- Still open from the package spec: (e) cluster names, (f) E17 one-pager placement; T-D4 waits on an ecoregion layer.
