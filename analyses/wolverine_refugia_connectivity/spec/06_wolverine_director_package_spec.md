# Wolverine refugia corridors — Director Package Spec (v1.1, 2026-09-28)

**Status:** v1.1 BUILT 2026-09-28 — the northern package changes for the link classes (06 v1.2.17–v1.2.19: five-class legend with
the two near-contiguous rows, class-and-width-first examples, detour-distance captions, the D28/D29 columns) mirrored; Ethan
re-runs 03 → 04 → 05. v1.0 BUILT 2026-09-28 (`wolverine_director.py` + `04_tables_and_figures.ipynb` / `05_director_outputs.ipynb`).

**Changelog.** v1.1 (2026-09-28) — classes read `link_class` (analysis spec W12): the package refuses a run classified before
D23 (`P.classified`); the near-contiguous links (D25) are drawn in the neutral grey with the mapstyle hatch UNDER the four
corridor classes on every map (TALL, act crops, the wide layout), the barrier variant outlined, two legend rows with counts
after the four classes (`ms.NEAR_CONTIGUOUS`); examples are class-and-width-first (below); tables gain Geometry (adjacent /
width not assessable / corridor link), Alternative link is (far / hard / both, D29) and the p10 width ratio (D28); every caption
that mentions the band states it as detour distance (D31) and the geometric class counts; the wide 02 map prints the adjacent
counts and the detour distance. Pressure strings = `cc.LINK_CLASS_LABEL` (the northern words). Subordinate to `wolverine_refugia_connectivity_spec.md`. Mirrors the northern package spec
(`analyses/northern_connectivity/spec/06_corridors_north_director_package_spec.md` v1.2.16) — the §3a
cartographic contract (`corridors_mapstyle.py`: one style module, Okabe–Ito class palette, 55% area fills,
greyscale + one-blue basemap with the Copernicus hillshade, Noto Sans, one legend per figure, PDF + PNG at 300 dpi
named `<fig_id>_<run_tag>`, the 8-item render QA before any figure ships) applies unchanged. Zero new solves.

## 1. What differs from the north

- **Nodes are refugia patches, not protected areas.** Existing PAs are drawn as OUTLINE context on every map
  (`AREA["pa_outline"]`) and never called nodes; a filled PA grey would fail the CVD check against the refugia
  fills (measured: every pale marginal tint is ΔE 9–18 from the 55% grey).
- **New area tokens** (`corridors_mapstyle.AREA`): core `#238B45` @ 0.85, marginal `#C5E1A5` @ 0.70 — ΔE ≥ 20
  against the four class hues and the water blue under deuteranopia / protanopia (worst 24.8 / 26.6); node
  outlines + number chips (`NODE`). Layer order: … water → refugia marginal (3.5) → refugia core (3.7) → PA
  outlines (4.1) → node outlines (4.2) → classes → boundaries → chips / labels.
- **The frame is the whole Y2Y** (aspect 0.39). Full-extent maps use the new **TALL** template (8.5 × 11 in
  portrait, map on the full height ≈ 343 km/in, furniture column = legend, two-column node key, scale + north);
  act crops use SLIDE with the locator showing the window within the region. The Y2Y-wide hillshade
  (`hillshade_y2y_300m.tif`) is read windowed and decimated.
- **Three acts by latitude** (north ≥ 58.5 °N, central 51–58.5, south < 51; `STYLE["act_breaks_lat"]`,
  fallback terciles), examples chosen by an **automatic top-k rule** per act — **class-and-width-first (v1.1, the northern
  06 v1.2.12 rule):** closing = links in the top class "only viable connection" ranked by `squeeze_ratio_obs` ascending (most
  constrained first), ties by `width_ratio_p10`, then criticality (`n_pairs_lost`); when the act has none, fill from "last
  affordable link" ranked by `width_ratio_p10` ascending, then "already narrowing"; room to choose = corridor-land-with-options
  links with the most route branches (relative floor, D26). Near-contiguous links (D25) and links already connected within
  protected land (W11) are never examples. Numbered north → south; Ethan's pinned picks (the north's `EXAMPLE_PICKS` schema)
  override.
- **No ensemble attribution column** until the ensemble runs. The "already narrowing" class needs the counterfactual (D17,
  notebook 03); until it has run the package folds it into "options" (H8 logic) and the record notebook refuses to render.
- **Protection status (W11), one knob `wd.STYLE["protected_mode"]`:** `"overlay"` (default) — every band drawn in
  full, existing PAs hatched grey (///) and proposed IPCAs hatched teal (\\) on top, links already connected
  within protected land drawn muted (α 0.45) with an outline in the satisfying layer's colour, legend rows
  "Already connected within existing protected areas [n]" / "… once the proposed IPCAs are realized [n]";
  `"unprotected_only"` — only the corridor land still to secure is drawn and satisfied links are omitted (the
  legend says so). Satisfied links are never examples. Tables carry the status, the route share inside PAs and
  inside IPCAs only, and the corridor land to secure; T4 lists the satisfied links; the GIS export adds
  `secured_by` and `corridor_pressure_unprotected.gpkg`.

## 2. Figures and tables (`wolverine_director`; knobs in `wd.STYLE`)

| id | asset | template | three-second message |
|---|---|---|---|
| W0 | `figure_w0` — core / marginal refugia, the numbered nodes, PA outlines | TALL | where wolverine refugia are, and the patches the network connects |
| W0b | `figure_w0b` — movement cost (four swatches), nodes | TALL | the cost sits in the valleys and the south |
| W0c | `figure_w0c` — what the variant withheld, one colour per rule + terrain kept at 1000 | TALL | where the generic terrain rules were withheld |
| W1 | `figure_w1` — corridor pressure classes over all links, example chips | TALL | where the options are closing (TBC after the run) |
| W2–W4 | `figure_act(act)` — north / central / south windows with the examples | SLIDE + locator | per `ACT_SPEC` (TBC after the run) |
| T0 | `table_nodes` — node key (number, name, km², PA overlap, position) | CSV | — |
| T1 / T2 / T4 | `table_links("examples" / "flagged" / "satisfied")` — pressure (the `LINK_CLASS_LABEL` string), geometry (adjacent / width not assessable / corridor link; D24/D25), alternative link is (far / hard / both; D29), narrowest tenth (p10 width ratio; D28), protection status, route inside PAs / IPCAs %, corridor land to secure, room to move, cheapest alternative, width vs natural, corridor land, band core / marginal / other %, band protected %, endpoints protected, jurisdictions | CSV + PNG | — |
| GIS | `export_gis` — corridor_pressure, refugia, nodes, examples gpkg + style.json | — | — |
| QA | `qa_report` — the §3a.3 checklist per figure → `qa_checklist.csv` | — | — |

Record = `04_tables_and_figures.ipynb` → `<run>/director_package/` — **slimmed 2026-09-28 (Ethan): tables + GIS + the link-class record
only, minutes.** W0–W4 and the engine record maps are never shared, so 04 no longer renders them (the functions stay; one commented cell
draws a figure on demand); the §3a.3 QA checklist therefore has nothing to check by default. 05 reads the run directly and does not depend
on 04 (the northern `06_tables_and_figures` mirror in role, not in volume). **Curated = `05_director_outputs.ipynb`** (the northern `07_director_outputs`
mirror, 2026-09-28): the same first two maps as the north, drawn through `director_plot.wide_map` (the y2y Act 1 wide layout:
the Y2Y frame at left, insets A / B at right, the key under A, the legend under B; PNG 300 dpi + PDF) via
`wd.director_frame` (a 600 m decimated frame — one 300 dpi pixel of the frame panel is ~1.5 km; existing PAs = the layout's
grey layer; the refugia nodes = the overlay in the IPCA role, filled in the core tone, outlined, named in the insets; the
proposed IPCAs = a second fill over the corridor land, so what is already satisfied reads as such — W11 overlay mode):
**01 the movement-cost surface** (`figure_cost_wide`: the four swatches in the ramp slot) and **02 where the land still
offers choices** (`figure_choices_wide`: the pressure classes in the ramp slot; H8 folding as on W1). Insets: `"examples"`
(A = the northernmost example link, B = the southernmost; band + endpoint nodes + 40 km, floored at 350 km, both at one scale)
or `"clusters"` (the two densest node clusters). Knobs `wd.WIDE_STYLE` → `dp.STYLE`. The TALL contract figures stay in the record.
**03–05 (the northern 07 · 03–05 mirrored, 2026-09-28):** **03 the route options** (`figure_options_wide`: up to four numbered
examples — the link under the most pressure per act, then a room-to-choose link, or `wd.EXAMPLE_PICKS`; each option's band in
its number's colour from the y2y cluster palette via `corridors_director.option_color`, under the PA / IPCA / node fills; inset A
= options 1–2, B = 3–4, one each when a pair exceeds `STYLE["inset_max_km"]`), **04 the option stars** (`option_stars` →
`director_plot.star_grid`; `option_profiles_y2y` = mean percentile + value ratio per star axis on the Y2Y director construction,
fractional 300 m → 1 km cover) **+ 04b the locator panels** (`option_locators`, the northern rule), **05 the consequences table**
(`option_consequences` → `director_plot.consequences_table`; reference columns Banff National Park + Dene Kʼéh Kusān from the
PA / proposed vectors, `wd.CONSEQ_REFERENCE`; rows to `tables/route_option_consequences.csv`).

## 3. Open for Ethan after the first render

(a) the three act messages and titles (`ACT_SPEC`); (b) the latitude breaks; (c) pinned examples; (d) hand-placed
jurisdiction / town labels on the TALL frame (`FULL_SPEC`); (e) node display names (`node_names.csv`).
