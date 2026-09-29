# Wolverine refugia connectivity (analysis 5)

Least-cost corridors connecting **wolverine climate refugia patches across the whole Y2Y**, with the
northern connectivity methodology (`analyses/northern_connectivity/`) and engine (`corridors_prep`,
`corridor_graph`, `corridors_core` at the repo root). Spec + the binding living logs: `spec/`.

**Run order (Ethan, VS Code, kernel `y2y-geo`, numeric order):**

| notebook | what | stops |
|---|---|---|
| `01_refugia_grid_and_nodes` | raster characterised; cost + class warps (G2, GW1); nodes vectorised (`cc.node_patches`); variant surface derived (GW2); timing probe | **check stop 1** (nodes) · **check stop 2** (variant surface) |
| `02_baseline` | run dir on the variant; G0; CWD (the long stage); inherited cutoff; network (G3); GW4; G15; protection status (W11); priority; write_run | — |
| `03_products` | near-optimality with fixed breaks (G10, G22); **the counterfactual width — the second CWD set (D17, G13; ~the 02 CWD runtime, ~8 GB)**; route branches with the relative floor (G9, G21); `classify_links` → `link_class` (D23–D25; G18/G19); protection status; finish | — |
| `04_tables_and_figures` | the record, slimmed (2026-09-28): link-class record (G18/G19), tables T0/T3/T2/T4/T1, GIS export, results-log numbers — minutes; contract figures on demand only (commented cell) | — |
| **`05_complexes`** | **v2.5 (run spec v3 §1a revised 2026-09-29)**: complexes from the 130 D25 links of `v2_run001`, sliver table, refugia names → the audit objects (commit them) | **check stop 3** (the complex map) |
| `06_v25_network` | `v25_run001`: the routing RE-RUN between the 23 complexes (unit fields = min over the cached patch fields, cache HIT), inherited cutoff, GW4/G15, near-optimality, counterfactual, the D25 second pass, branches + classes, W11, finish (~1 h) | — |
| `07_v25_product` | coverage (PAs / IPCAs / prioritizr core) with the expectation row, accounting, the Bow Valley act check, tables A / slivers / B + T1–T4, the headline, GIS → `<run>/postprocess/` + `director_package/` | — |
| `08_director_outputs` | the curated few on the contracted run: 01 movement cost, **02 complexes + the inter-complex links by class, pinch marked, no hatched bands**, 03 route options, 04 option stars + locators, 05 consequences table | — |

Before 01's variant cell: drop RGI 7.0 (regions 01 + 02) into `input_data/glaciers/` and HydroLAKES +
HydroRIVERS (NA) into `input_data/hydrosheds/` — `data/acquire.py` lists / fetches them.

Layout: `audit/audit_objects/` (git-tracked node files), `figures/` (check-stop figures), `spec/`
(spec, package spec, methods_log, results_log), `data/acquire.py`. Outputs: `output_data/corridors_wolverine/`.
**Run spec v3** (`spec/Wolverine refugia corridors — run spec v3.md`): §1a = v2.5 (this deliverable, 05 → 06 → 07 → 08; the routing between the complexes was pulled into it 2026-09-29); §3–6 (contraction re-run,
baseline comparison, glacier sensitivities) = the next iteration, built and parked on the `wolverine-v3` branch (not run). Tag `v2_run001`
= the tree that produced the run.

Parked for later (spec §7): comparison runs, the ensemble, the co-benefit / refugia audits. (D17 is REQUIRED since spec v1.1 —
the link classes need the barrier-free width.)
