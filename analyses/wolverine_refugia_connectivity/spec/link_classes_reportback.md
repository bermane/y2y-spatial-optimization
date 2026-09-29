# Wolverine refugia corridors — report-back after the link-class re-run

**Run:** `v2_run001` (git 9003dfd, dirty), the withheld-terrain surface, 130 core-refugia nodes ≥ 250 km², band
cutoff inherited from the north (13.6229 cost units = **4.09 km of extra travel on open ground**, D31). Notebook 03
re-run by Ethan 2026-09-28 with the northern link-classification rules mirrored (D23–D31; D12 amended; D17 now
required and run). Nothing tuned; every constant was pinned into the run record before a class count was read.
Notebook 04 (slimmed: tables + GIS) has run; 05 (the five presentation outputs) is next.

## 1. What did not change

- 170 links between 130 nodes: 129 minimum-network + 41 affordable backups (β = 2.5), ONE connected group.
- Corridor land 52,572 km² (nodes excluded); 33,907 km² of it outside existing PAs and proposed IPCAs.
- 47 links with no affordable alternative (D7).
- Already connected within protected land (W11, centre-line ≥ 0.95): 26 links by existing PAs alone, 23 more once the
  proposed IPCAs are realized (49 of 170).

## 2. The counterfactual width (D17) — run for the first time here

- 3.21 M cells relaxed (every cost ≥ 10 → 1); 16 links narrower than half their barrier-free width before precedence.
- **D25 near-contiguous: 130 of the 170 links (76%)**, none with a cost-1000 cell on the path. Their least-cost paths run
  0.9–20.4 km (median 3.8 km) against a barrier-free median band width of 14–511 cells (median 64.5 cells ≈ 19 km).
- D24: 0 links below the width-test floors. G19: halving or doubling the floors moves zero links.
- **43 of the 47 links with no affordable alternative are near-contiguous.** Only 4 corridor links are edge-irreplaceable.
- The near-contiguous links carry 27,060 km² of band land (51% of the corridor land); 46 of them are already connected
  within protected land (24 by PAs, 22 by IPCAs).

## 3. The 40 corridor links — classes (D23, `class_truth_table.csv`)

| class | links | band land km² | already connected |
|---|---|---|---|
| only viable connection (E ∧ one branch ∧ narrow) | **0** | 0 | — |
| last affordable link (E) | 4 | 1,221 | 0 |
| already narrowing (ratio < 0.5) | 15 | 10,075 | 0 |
| corridor land with options | 21 | 31,016 | 3 (2 PA, 1 IPCA) |

Eight-cell table: E·B1·¬S 3 → last affordable · E·¬B1·S 1 → last affordable · ¬E·B1·S 13 → narrowing · ¬E·B1·¬S 20 →
options · ¬E·¬B1·S 2 → narrowing · ¬E·¬B1·¬S 1 → options · **E·B1·S 0**.

- **The one candidate for the top class** — Bob Marshall Wilderness ↔ Mission Mountains Tribal Wilderness (no
  affordable alternative, median width ratio 0.31, tenth-percentile 0.05) — has **two** route branches under the relative
  floor (D26). G21 lists it as the only link whose branch count changed from the retired fixed floor. Under the old floor it
  would have been "only viable"; under the registered rule it is "last affordable".
- By act (latitude breaks 58.5 / 51 °N): north 6 corridor links, all "options" (25 near-contiguous); central 2 last
  affordable / 4 narrowing / 7 options (74 near-contiguous); south 2 last affordable / 11 narrowing / 8 options (31
  near-contiguous). **Eleven of the fifteen narrowing links are in the south.**
- D29 alternative kind: the 4 last-affordable links are all *far* (the next link is distant, not walled in). Among the
  near-contiguous links with an alternative: far 32, affordable 26, hard 6, both 5.
- D28: tenth-percentile width ratio on the corridor links 0.05–0.90 (median 0.24) against a median ratio of 0.23–1.99
  (median 0.58): every corridor link has a pinch well below its median width.
- D30 tiers (fixed breaks): robust core 5,310 km² · frequent 15,772 · occasional (the band) 52,572.
- Route branches under the relative floor: 44 over 170 links; 33 of the 40 corridor links have one branch (the superseded
  topology-only count was 133 of 170 — most of those were near-contiguous links that now get no decomposition).

## 4. Examples under the class-and-width-first rule (top class empty → filled from "last affordable" by p10 width)

1. **Sustut Park (SW) ↔ Babine River Corridor Park (E)** — central; last affordable, alternative far; path 10 km; median
   width ratio 1.02, tenth-percentile 0.23; one branch; open.
2. **Bob Marshall Wilderness ↔ Mission Mountains Tribal Wilderness** — south; last affordable, alternative far; path 11 km;
   median 0.31, tenth-percentile 0.05; two branches; open.
3. **Selway-Bitterroot Wilderness ↔ Skull-Odell (SE)** — south, the "room to choose" slot; options; path 33 km; median 0.58;
   two branches; open.

The north act has no closing candidate.

## 5. Questions for the chat

- **Q1 — D25 at this node density.** The rule is relative (path shorter than the barrier-free band width; no constant by
  design). On open ground the counterfactual band between two patches is wider than the path whenever the path is
  shorter than roughly twice the 4.1 km detour allowance, more when the patches present wide fronts. With a median node
  spacing of 2.6 km the rule declares 76% of the network "adjacent — no corridor needed", up to 20 km apart. Is that the
  right reading for wolverine (two refugia 10–20 km apart across open ground are effectively one), or does the wolverine
  analysis need (a) a separate "short link" reporting class, (b) an absolute path-length cap on D25, or (c) a wolverine
  detour allowance (D31's rule for a derived analysis)? Nothing has been tuned; the tuning prohibition applies.
- **Q2 — the empty top class.** Report as measured ("no link is at once isolated, single-route and narrow") and note the
  Bob Marshall ↔ Mission Mountains case as the G21 boundary case? Or is the two-branch decomposition there worth a look
  before the deck says so?
- **Q3 — the acts.** North = room to choose, south = options closing (11 of 15 narrowing links). Keep the three latitude
  acts, or drop to the northern package's two-act shape?
- **Q4 — the near-contiguous bands on the map.** The mirror draws them hatched grey under the four classes. Here they are
  half the corridor land; hatching 27,000 km² grey will dominate the Y2Y frame. Draw them, draw outlines only, or omit
  them and state the count in the legend?
- **Q5 — the detour allowance.** Inherited from the north (4.09 km). D31 says a derived analysis with no area target
  calibrates by detour distance. Is a wolverine-specific allowance wanted, and on what evidence? (Everything above scales
  with it, including D25.)

Disclosures: R5.1's "133 route-irreplaceable" is superseded (topology-only flag); node auto-names repeat where several
northern patches share a nearest PA (six "Nááts'Ihch'Oh …" variants) — cosmetic, renamed in `node_names.csv`. The T1–T4
tables of the first 04 run mis-named every link touching a node numbered ≥ 100 (a two-digit label parse; fixed, M6.7) — the
names above are from the labels and are correct; 04 is re-run for the record.
