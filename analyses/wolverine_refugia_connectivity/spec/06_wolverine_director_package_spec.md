# Wolverine refugia corridors — Director Package Spec (v1.0, 2026-09-28)

**Status:** v1.0 BUILT 2026-09-28 (`wolverine_director.py` + `04_results.ipynb` / `05_director_package.ipynb`);
pending Ethan's run. Subordinate to `wolverine_refugia_connectivity_spec.md`. Mirrors the northern package spec
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
  fallback terciles), examples chosen by an **automatic top-k rule** per act (closing: `both` by pairs lost /
  backup ratio, then `edge` by backup ratio, then `squeezed`; room to choose: securing links with the most route
  branches), numbered north → south; Ethan's pinned picks (the north's `EXAMPLE_PICKS` schema) override.
- **No ensemble attribution column** until the ensemble runs; no "squeezed" class until D17 runs (H8 logic).
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
| T1 / T2 / T4 | `table_links("examples" / "flagged" / "satisfied")` — pressure, protection status, route inside PAs / IPCAs %, corridor land to secure, room to move, cheapest alternative, width vs natural, corridor land, band core / marginal / other %, band protected %, endpoints protected, jurisdictions | CSV + PNG | — |
| GIS | `export_gis` — corridor_pressure, refugia, nodes, examples gpkg + style.json | — | — |
| QA | `qa_report` — the §3a.3 checklist per figure → `qa_checklist.csv` | — | — |

Record = `04_results.ipynb` (every asset + the engine's record figures) → `<run>/director_package/`;
curated = `05_director_package.ipynb` (W0, W1, the acts, T1) → `<run>/director_package/director_outputs/`.

## 3. Open for Ethan after the first render

(a) the three act messages and titles (`ACT_SPEC`); (b) the latitude breaks; (c) pinned examples; (d) hand-placed
jurisdiction / town labels on the TALL frame (`FULL_SPEC`); (e) node display names (`node_names.csv`).
