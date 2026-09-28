# Wolverine refugia connectivity (analysis 5)

Least-cost corridors connecting **wolverine climate refugia patches across the whole Y2Y**, with the
northern connectivity methodology (`analyses/northern_connectivity/`) and engine (`corridors_prep`,
`corridor_graph`, `corridors_core` at the repo root). Spec + the binding living logs: `spec/`.

**Run order (Ethan, VS Code, kernel `y2y-geo`, numeric order):**

| notebook | what | stops |
|---|---|---|
| `01_refugia_grid_and_nodes` | raster characterised; cost + class warps (G2, GW1); nodes vectorised (`cc.node_patches`); variant surface derived (GW2); timing probe | **check stop 1** (nodes) · **check stop 2** (variant surface) |
| `02_baseline` | run dir on the variant; G0; CWD (the long stage); inherited cutoff; network (G3); GW4; G15; protection status (W11); priority; write_run | — |
| `03_products` | near-optimality (G10); route branches (G9); finish | — |
| `04_results` | the record: engine figures + W0/W0b/W0c/W1/W2–W4, T0–T2, GIS, QA | — |
| `05_director_package` | the curated set from the same functions | — |

Before 01's variant cell: drop RGI 7.0 (regions 01 + 02) into `input_data/glaciers/` and HydroLAKES +
HydroRIVERS (NA) into `input_data/hydrosheds/` — `data/acquire.py` lists / fetches them.

Layout: `audit/audit_objects/` (git-tracked node files), `figures/` (check-stop figures), `spec/`
(spec, package spec, methods_log, results_log), `data/acquire.py`. Outputs: `output_data/corridors_wolverine/`.
Parked for later (spec §7): comparison runs, the ensemble, D17 squeeze, the co-benefit / refugia audits.
