# Parked for v3 (run spec v3 §10, 2026-09-29)

The complex-level work of 2026-09-28/29: contraction of near-contiguous patches into refugia complexes
(`05_complexes`), routing between the complex unions (`06_v25_network`: runs `v25_run001` / `v25_run002`),
and the product on the contracted run (`07_v25_product`). Engine support (`nodes.contract`,
`cc._contract_complexes`, `config.CORRIDORS["wolverine"]["v25"]`) and the audit objects
(`audit/audit_objects/complex_*`, `complexes.gpkg`, `fronts_v2.gpkg`, `slivers_v2.csv`) stay in place, unused
by the node-level product. The baseline comparison and glacier surfaces are on branch `wolverine-v3`.
These notebooks are not in the run order; the deliverable is `05_postprocess` → `06_director_outputs`.
