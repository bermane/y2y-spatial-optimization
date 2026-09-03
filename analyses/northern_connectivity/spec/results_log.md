# Results log — northern connectivity corridors (living document)

**Purpose.** The running register of quantitative RESULTS destined for the paper's results
section (and its figures/tables), each with provenance so every number in a draft traces to
disk. Companion to `methods_log.md` (same binding maintenance rule: update in the same session
any result lands or changes; supersede, never delete).

Provenance shorthand: [run002] = `output_data/corridors_north/v2_run002/`; [0a] = step-0a
artifacts in `audit/audit_objects/` (H7-signed 2026-08-26, review sha256 6304fec2c148);
[v1] = `output_data/corridors_north/_v1_frozen/`; [G2] = warp-check cell output, NB01/NB02.

---

## R1. Gates — measured

| gate | measured | when |
|---|---|---|
| G1 | Jaccard **1.0000** vs v1 corridor on v1's own resistance; 41 edges (12 zero-cost); 18,188 km² | 2026-08-07, re-run clean 2026-08-26 |
| G2 | 4,285 × 5,767 @ 300 m ESRI:102008; classes exactly {1,10,100,1000} | 2026-08-26/27 |
| G0 | 42 names, 3 dedupe merges, 48 seed parts → 42 routing units; review sha 6304fec2c148 | 2026-08-27 [run002] |
| G3 | raster and graph agree: 1 component | 2026-08-27 [run002] |
| G5 | max Δrichness **0.0020** (IPCAs and PAs) over 8 definition-unchanged axes (tol 0.02); macrorefugia excluded/reported (M6.3) | 2026-08-27 [run002] |
| G8 | passes (incl. addendum-key requirement) | 2026-08-27 |
| G4, G7, G9–G12 | pending NB03/NB04 | — |

## R2. Cost surface over the northern window [G2]

Routable 9,696,945 cells = 872,725 km² (v1: 751,614 — v1 inherited the prioritizr PU mask;
M6.4). Class shares of in-corridor cells: cost-1 **88.2%**, cost-10 5.4%, cost-100 0.3%,
cost-1000 6.1%. Effective spread p95/p5 = 1,000× (v1 blend: 10.9×). Log-log correlation with
the v1 blend over 8.33 M shared cells: **r = +0.270** — the two surfaces are genuinely
different objects. Figure: `cost_surface_map.png` (05_results; full-extent cost surface BESIDE raw 1 km gHM —
the D2/A2 visual case: roads survive as continuous barriers at 300 m while 1 km gHM smears
them; gHM panel power-scaled with the heavy-tail reading note in the notebook caption;
named-area outlines + provincial borders/towns on both panels).

## R3. Step 0a — multipart names and the H7 review [0a]

5 multipart names of 42 (48 seed parts → 42 routing units). Treatments signed as proposed:

| name | parts (km²) | min gap | pair CWD | path max cost | treatment |
|---|---|---|---|---|---|
| Dene Kʼéh Kusān (IPCA) | 37,090; 2,064; 79.5 | 44 cells (~13 km) | 48.8–121.4 | 1 | link_locked |
| Liard River Corridor Park | 482; 252; 79.1 | 5 cells (~1.5 km) | 5.2–133.1 | 1 | link_locked |
| Nahanni NPR | 30,021; 43.2 | 34 cells (~10 km) | 36.5 | 1 | link_locked |
| Nááts'ihch'oh NPR | 4,383; 516 | 36 cells (~11 km) | 36.8 | 1 | link_locked |
| Tombstone NEP | 1,705; 344 | 2 cells (~600 m) | 2.8 | 1 | **merge_parts** (rule 1) |

**Headline:** every part-connecting least-cost route runs entirely through cost-1 land — zero
cells ≥ cost-10 on any pair path (`path_cells_cost10plus` = 0 everywhere). No road/rail
crossings; the multipart question is low-stakes for this node set. Rule 2 (multi-site
designations) never fired (no multipart WMAs/sanctuaries), so the name-derived-designation
caveat (M3.4) is moot here.

## R4. Calibration (D6) [run002]

`cwd_cutoff_abs = 13.622951589524746` → **18,150 km²** MST-only (target 18,188, tol 50;
residual −38). ≈ 13.6 cost units ≈ a ~4 km detour allowance through cost-1 land — bands are
tight because the surface is flat. SUPERSEDED: the 2026-08-27 morning pass calibrated 13.38 →
18,202 km² WITH the adjacency-lens bug (M4.3); not citable.

## R5. Baseline network [run002]

- **58 edges** = 41 inter-name MST + 11 backups + 13 adjacencies + 6 locked intra-name;
  **1 connected component** (all 42 names).
- Corridor NEW land **33,041 km²**; swath incl. node land 38,808 km²; centreline 1,918 km;
  node land 242,540 km². Band area by class: inter 41,576 km², intra_name 1,984 km²,
  adjacency **0** (post-M4.3-fix, as designed).
- **13 adjacencies vs v1's 12** — the new pair is Peel Watershed ↔ Tombstone (300 m grid /
  full-mask effect; disclose as a grid-resolution sensitivity of the adjacency count).
- Worst-case detour under no failures: 1.51× (Carp Lake ↔ Monkman).
- Priority tiers (D9): robust_core 3,250 km² / frequent 9,538 / occasional 31,792
  (cumulative ≥-threshold areas).

**R5.1 Irreplaceable links (β = 2.5) — the headline table.** 7 of 58:

| link | cheapest alternative | pairs stranded | note |
|---|---|---|---|
| Mount Edziza ↔ Stikine River | **141×** | 0† | |
| Gladys Lake ER ↔ Spatsizi Plateau | **47×** | 41 | |
| Tatonduk ↔ Fishing Branch HPA | **19×** | 41 | |
| Wədzih Yiné' ↔ Chase Park | **16×** | 0† | most load-bearing at flag time (245 pairs) |
| Liard River Corridor [part 1 ↔ 3] | 4.6× | 47 | intra_name (D16) |
| Wilps Gwininitxw ↔ Swan Lake Kispiox | 4.0× | 41 | |
| Gwillim Lake ↔ Pine Le Moray | **2.6×** | 117 | marginal — just over β; test vs axis D |

† later backups incidentally closed covering cycles: losing these no longer disconnects, but
forces ~30× / ~269× detours (M4.5 — report flag + disconnects + cost_inflation together).

**R5.2 D16 internal links:** Liard's part-1↔part-3 link is itself irreplaceable (external
detour 4.6×); Nahanni's and Nááts'ihch'oh's internal links have far cheaper external
reconnections (backup ratio ~0.03) — the parts machinery producing real criticality signal.

## R6. Co-benefit profile [run002]

Audit path equivalent to v1 at Δ ≤ 0.002 on all definition-unchanged axes (G5). Macrorefugia
richness under the re-oriented 1/v layer: IPCAs 0.229 (v1 vmax−v: 0.504), PAs 0.295 (v1:
0.555) — a feature-definition change, not a mask change (M6.3). Node-mask areas +8% vs v1
(PU-mask liberation, M6.4) with contributions unchanged (liberated cells are NaN in the
PU-masked audit layers).

## R7. Ensemble (NB03) — 47 members, 2026-08-27 [run002/ensemble]

Gates: **G7 OK** (drop-nothing Jaccard 1.000000, 52 vs 52 unit edges); **G12 OK** (47 distinct
by config-hash: 1 + 2 B + 42 C + 2 D).

**R7.1 Per-axis map movement** (1 − Jaccard vs baseline): **B (band width) mean 0.423** —
by far the largest lever, halving/doubling the band moves ~42% of the map; **D (β) mean 0.177**
(β = 1.5 → 0.272: stripping backups matters more than adding them at β = 4); **C (drop a name)
mean 0.081, max 0.317**.

**R7.2 Most structurally load-bearing names** (Jaccard when dropped): Nahanni **0.683**,
Dene Kʼéh Kusān 0.710, Liard River Corridor 0.792, Tū Łī́dlini (Ross River) 0.808, Pine Le
Moray 0.814 (**network splits into 2**), Wilps Gwininitxw 0.826. **16 of 42 name-drops
disconnect the network** — bridge-backup insures edge failures, not node failures, so a third
of the anchors are articulation points. Headline C-axis finding.

**R7.3 Robust core:** attribution ≥ 0.9 on **32,598 km²** of 95,844 km² ever used by any
member.

**R7.4 Edge presence** (post-repair, see M5.7): the 52 baseline edges sit at **0.894–0.957**
(0.957 = (47−2)/47, the exact ceiling for a two-endpoint edge under leave-one-out); 47
substitute edges appear at ≤ 0.085 — the reroutes specific name-drops force, now genuinely
interpretable. SUPERSEDED: the first collect's edge_frequency.csv mixed subset-local edge ids
(M5.7) and is not citable.

## R8. Near-optimality + branches (NB04, steps 4a–4b) — 2026-08-27 [run002]

**Gates: G10 OK** (max residual on baseline least-cost paths 6.1e-05 cost units); **G9 held**
on every component. **G11 FAILED — steps 4c/4d + finish PENDING** a methods decision (see
below).

**R8.1 Near-optimality surface:** written (near_optimality/near_opt_owner/class tifs); tier
thresholds from the 2× union band per M5.2.

**R8.2 Route branches** @ 0.5× cutoff (6.81 cost units ≈ 2 km detour allowance): **41 branches
over 45 banded edges; 35 edges route-irreplaceable; 3 edges have genuine alternatives**
(11 slivers < 10 km² dropped):

| edge | branches (area km², min slack) |
|---|---|
| Dene Kʼéh Kusān ↔ Liard River Corridor | 44.2 @ 0.0 · 29.7 @ 2.8 |
| Tsey Dëk ↔ Tintina Trench | 83.7 @ 0.0 · 152.2 @ 3.9 |
| Liard River Corridor ↔ Nahanni | 1,255.0 @ 0.0 · 342.3 @ 5.7 |

With a 4-class surface and a tight calibrated band, most links offer exactly one route at
0.5× cutoff — route-irreplaceability is the norm, alternatives the exception.

**R8.3 G11 failure → RESOLVED (M6.5):** 9 of 41 branches drifted **+5.4% to +16.6%** crossing
300 m → 1 km at the fixed 0.5 areal-fraction majority — all positive (systematic inflation on
ribbons a few cells wide relative to a 1 km cell; the known non-conservation regime of the
majority rule). Decision 2026-08-27: branch profiling switches to fractional cover weighting
(exactly area-conserving; reduces to `mask_profile` on binary masks — see M6.5).
**Re-run clean same day: G11 max |drift| = 0.04%** (tolerance 5%) — a ~150× improvement on the
worst branch.

**R8.4 Values table (4c) [run002/alternatives_branches.csv]:** 41 branch rows × 43 cols
(Y2Y-wide column spec + slack/criticality/Carroll). `carroll2018_pctl` vs the routable-area
baseline (50): median **42.9**, range 5.8–99.6 — branches as a population sit near the
baseline; individual links span nearly the full range.

**R8.5 Tie-break (4d) [run002/tiebreak.csv]:** 6 rows over the 3 edges with alternatives.
Dene Kʼéh Kusān ↔ Liard: primary branch wins on BOTH slack (0 vs 2.8) and values (rank 1.11 vs
1.89, Carroll 96.3 vs 87.8) — no tension. Liard ↔ Nahanni: primary wins values outright
(rank 1.00, slack 0); alternative's only edge is Carroll (73.3 vs 68.2). **Tsey Dëk ↔ Tintina
Trench is the genuine judgment call:** the 152 km² alternative ranks better on values (1.22 vs
1.78) but costs +3.9 slack; Carroll is identical (6.4 — both routes sit in the lowest decile
of the Carroll surface). Ranking only; recommendation is a human read (M5.5).

**R8.6 Both-senses irreplaceability [run002/irreplaceability_summary.csv]:** joining the D7
flag with the D12 branch count, **4 links are irreplaceable in BOTH senses** — no alternative
link at any price within β AND a single physical route within the link: Gwillim Lake ↔ Pine Le
Moray, Tatonduk ↔ Fishing Branch, Wilps Gwininitxw ↔ Swan Lake Kispiox, Wədzih Yiné' ↔ Chase.
The strongest criticality statement the analysis makes. (Edziza↔Stikine and Gladys Lake↔
Spatsizi are edge-irreplaceable at cost 1.0 — near-touching pairs whose 0.5×-cutoff band left
no branch ≥ 10 km², so `n_branches` = 0 there; read as trivially-connected neighbours, not as
having alternatives.)

**Absolute vs relative price of the alternative (added 2026-08-30, `backup_extra_km_equiv`;
M4.5):** every flagged link HAS an alternative — at a price. In intact-land-km equivalent:
Gwillim↔Pine Le Moray +116 km (2.6×), Wilps Gwininitxw↔Swan Lake +77 km (4.0×), Wədzih
Yiné'↔Chase +60 km (16×), Tatonduk↔Fishing Branch +49 km (19×), Edziza↔Stikine +42 km (141×),
Gladys Lake↔Spatsizi +14 km (47×), Liard internal +6 km (4.6×). The ratio ranking and the
absolute ranking nearly INVERT — the near-touching pairs have huge ratios but modest absolute
detours; the long southern links have modest ratios but the largest real replacement costs.
Report both, always.

**R8.7 The routing-problem geography (M4.6 squeeze index; 2026-08-30)
[run002/irreplaceability_summary.csv].** The routing regime is geographically coherent, not
scattered — two clusters + four point chokepoints:
- **Peace/Hart Ranges cluster (SE corner) — the clearest routing-problem region:** Gwillim
  Lake↔Monkman squeeze **0.35**, Graham Laurier↔Pine Le Moray **0.38**, Carp Lake↔Pine Le
  Moray **0.44** (cost/km 5.3, the network's highest), Gwillim↔Kakwa **0.44** — corridors at a
  third of open-ground width paying 30–60% cost premiums. Corroborated by three independent
  products: Gwillim↔Pine Le Moray is both-senses irreplaceable (R8.6), and Pine Le Moray is
  the articulation name whose removal splits the network (R7.2).
- **Skeena cluster:** Mount Blanchet↔Sustut 0.48, Wilps Gwininitxw↔Mount Blanchet 0.70; plus
  the both-senses Wilps Gwininitxw↔Swan Lake Kispiox link.
- **Point chokepoints (irreplaceability without squeeze — replacement geography, not width):**
  Edziza↔Stikine 141×, Gladys Lake↔Spatsizi 47×, Tatonduk↔Fishing Branch 19×, Wədzih
  Yiné'↔Chase 16×.
Everything else — the large majority of corridor land — sits in the securing regime (M1.4).
Figures: `routing_problem_map.png` (full extent) + `routing_problem_zoom.png` (southern
cluster, named areas + numbered links with squeeze/ratio/absolute-km legend; Tatonduk↔Fishing
Branch remains on the full-extent map) + `routing_problem_cost_zoom.png` (triptych: cost |
links | overlay on the same frame) + `routing_problem_cost_overlay.png` (single figure:
anchors + flagged links hard-coloured over the live cost ramp — candidate headline figure)
(05_results).

**R8.7a Cause, visualised (2026-08-31):** in the zoom window the region-wide class mix does NOT
hold — the Peace-country cost-10 road/seismic network saturates the frame and **Williston
Reservoir forms a contiguous cost-1000 wall through the middle of the cluster**, which links
4/5/7 (Mount Blanchet↔Sustut aside, i.e. the Pine Le Moray feeders) visibly route around. The
squeeze there is driven by real, mapped barrier structure, corroborating R8.7's regime reading
(with the M4.6 cutline caveat still standing for the SE-corner links).

**R8.8 Priority-link value profiles (2026-08-31, M5.9)
[run002/priority_links_profile.csv + priority_links_stars_*.png].** The nine numbered links
star-profiled on the corridor co-benefit axes, with IPCA/PA reference stars. Composite mean
richness: **link 2 (Wilps Gwininitxw↔Swan Lake) highest at 0.598** (strong macrorefugia,
corridors, connectivity), link 9 (Gwillim↔Kakwa) 0.525, link 4 (Mount Blanchet↔Sustut) 0.515
(the biomass-carbon + birds standout); the Peace-cluster links 5–8 run 0.45–0.48,
mammal/bird-dominated (valley-bottom AOH). References: proposed IPCAs 0.384, existing PAs
0.433 — **the priority links are on average RICHER land than the anchors they connect**
(low-elevation permeable valleys vs protected high country), the same gap-analysis pattern the
corridor-segment stars showed. Link 1 (Edziza↔Stikine, 12 km² contact zone) indicative only.
Purpose: the consequences input for the PROACT read over the link alternatives (FRAMING 1,
links-as-alternatives, per the 2026-08-31 decision; branch-level values remain the nested
route drill-down). Companion map: `priority_links_map.png`.

**R8.9 Campaign complete [runs.csv]:** v2_run002 done = TRUE — first full end-to-end v2
production run (calibration → baseline → 47-member ensemble → near-optimality → branches →
values → tiebreak), 2026-08-27.


## R9. D17 squeezed class + director package (2026-09-03) — PENDING the notebook-04 re-run

**R9.1 D17 (counterfactual) — pending.** `counterfactual_squeeze` lands `band_new_km2`,
`band_cf_km2`, `squeeze_ratio_obs`, `squeezed` and G13's verdict when notebook 04 re-runs;
until then the draft map's 5 squeezed links (analytic M4.6) are the only measurement and are
NOT citable as D17. Expected: the Peace-cluster links stay squeezed (their squeeze was
corroborated by cost-per-km and the mapped barrier field, R8.7a); the SE-corner values may
move because the cutline artefact cancels.

**R9.2 Director package smoke-run [run002/director_package, H8 open]:** classes both 4 / edge
3 / securing 33 (+5 analytic-squeezed withheld). Examples: N1 Dene Kʼéh Kusān pair — with
**33,041 km²**, without **37,412 km²** (+4,371 km² of corridor need when the largest proposal
is not realised; the network reroutes around the gap); N2 Liard River Corridor ↔ Nahanni
(2 route options, attribution 1.0, spans BC / Yukon / NWT); N3 Dene Kʼéh Kusān ↔ Liard River
Corridor (2 routes); S1 Gwillim Lake ↔ Pine Le Moray, S2 Tthetäwndëk ↔ Nj ‘Iinlii” Jjik, S3
Wilps Gwininitxw ↔ Swan Lake Kispiox (both-senses, by criticality); Wədzih Yiné' ↔ Chase to
the appendix. **Every flagged link reads 'Unaffected' on the proposal-drop test** — no
flagged link's existence depends on a non-endpoint proposal. T2: 12 flagged links × 19
columns. Final numbers/figures land when 04 → 06 run.
