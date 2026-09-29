# Report-back — run003 (D22) and the run002 re-classification under D23–D31

For the spec chat. Written 2026-09-29 from the run directories (`v2_run002` re-run through notebook 04 under the new rules;
`v2_run003` = the D22 network, notebooks 02 → 04 → 06 → 07). The ensemble (03) is not reflected here. Every number below is
read from `corridor_edges.csv`, `corridor_summary.json`, `class_truth_table.csv`, `floor_effect.csv`,
`near_contiguous_links.csv` and `run_config.json` of the run named.

## 1. The D22 network (run003 vs run002)

| | run002 (parts locked) | run003 (parts compete) |
|---|---|---|
| routing units | 42 | 48 |
| edges | 58 = 41 tree + 11 backups + 13 touching + 6 locked within-name | 60 = 47 tree + 13 backups + 15 touching + 0 locked |
| cutoff (calibrated on inter-name tree edges only; within-name edges excluded from the calibration set) | 13.62 units ≈ 4.09 km detour | 13.44 units ≈ 4.03 km detour (18,187 km² vs the 18,188 target) |
| corridor land, union of all bands | 33,041 km² | 31,103 km² |

**Dene Kʼéh Kusān's third part** (the trigger): part 2 → part 3 is a tree edge (cost 48.8, 384 km² band) and part 3 also
holds a backup link to Nahanni, so nothing strands if the bridge is lost. Under D25 the pair is an **open front**: gap 11.7 km,
barrier-free width 27.9 km, ratio 0.92, cost-1 ground. Three within-name links sit in the tree (Dene 2–3; Liard River
Corridor 1–2 and 1–3). Liard River Corridor 1–2 is edge-irreplaceable (47 pairs strand; alternative 6.7×, *far*) but a 2.1 km
gap on a 10 km front, so it is an open front, not an irreplaceable corridor — the D24/D25 case working as intended.
**Nahanni's second way south is gone:** Liard River Corridor ↔ Nahanni is not an edge on run003 (Nahanni is reached through Dene
part 2, backup through part 3), so the N2 pin fires.

## 2. D23 — the eight-cell tables (G18)

Both runs, over the links that reach the width test (E = no alternative link within β, B1 = one branch, S = ratio < 0.5):

| E | B1 | S | class | run002 | run003 |
|---|---|---|---|---|---|
| ✓ | ✓ | ✓ | only viable connection | 1 | 1 |
| ✓ | ✓ | ✗ | last affordable link | 1 | 1 |
| ✗ | ✓ | ✓ | already narrowing | 7 | 7 |
| ✗ | ✓ | ✗ | corridor land with options | 15 | 17 |
| ✗ | ✗ | ✗ | corridor land with options | 2 | 1 |

The only-viable class is **one link on both runs: Gwillim Lake ↔ Pine Le Moray** (ratio 0.41 / 0.40; its alternative is *hard*,
not far — resistance, not distance). Of the four links only-viable under the retired rule: Wilps Gwininitxw ↔ Swan Lake drops
to last affordable (ratio 0.96, alternative *far*); Tatonduk ↔ Fishing Branch and Wędzih Yiné' ↔ Chase are open fronts (gaps
3.0 and 4.2 km against fronts of 10.8 and 12.9 km). The adoption condition therefore fails as measured, and the change is a
post-pin class change on the pinned run. The amended route flag holds on 8 links (topology-only flag: 24 / 26).

## 3. D24 / D25 / D25a — fronts, floors, sub-classes

| | run002 | run003 |
|---|---|---|
| near-contiguous links (of 45 non-zero-cost) | 18 | 17 |
| open front / roads or cuts / barrier | 16 / 2 / 0 | 14 / 3 / 0 |
| roads-or-cuts by cost-10 on the path / by ratio < 0.5 | 0 / 2 | 1 (Dene part 1 ↔ Liard RC part 3) / 2 |
| edge-irreplaceable among them | 4 | 4 |
| gap km, p10 / p50 / p90 | 0.6 / 3.8 / 22.7 | 0.6 / 3.3 / 20.1 |
| barrier-free width km, p10 / p50 / p90 | 12.5 / 23.6 / 41.8 | 12.1 / 19.2 / 35.2 |
| width-not-assessable | 1 (Gladys Lake ↔ Spatsizi: 0.6 km, no front at all) | 1 (same) |

No cost-1000 cell lies on any near-contiguous path; the barrier sub-class is empty on both runs. The largest gaps classed as
fronts are T’akú Tlatsini ↔ Stikine (30.9 km against a 36.5 km front) and ↔ Mount Edziza (33.3 vs 38.8): two very large facing
areas make a very wide front. **The floors are inert on this network** (G19: halving or doubling both floors moves 0 links on
either run), and the D26 relative branch floor changes no link's branch count against the retired 10 km² floor (G21: 1
sliver dropped, 0 links changed). Both are safeguards here, not drivers.

## 4. D25b — area accounting (per-edge band sums, G23 identity holds)

| km² | run002 | run003 |
|---|---|---|
| corridor (inter-name tree edges off fronts) | 16,395 | 16,233 |
| near-contiguous fronts | 4,461 | 3,549 |
| intra-name | 0 (the six locked links are all fronts) | 0 |
| augmentation (backups) | 16,615 | 15,126 |
| total band area | 37,471 | 34,908 |

The cutoff was not recalibrated. Deck captions should quote the corridor line and say once that fronts are excluded.

## 5. Classes on the maps (run003, non-zero-cost links)

only viable 1 · last affordable 2 · already narrowing 7 · corridor land with options 18 · adjacent, open front 14 · adjacent,
roads or cuts 3 · (touching 15, not drawn). Act 1 sentence as it now reads: **17 of the sector's 45 links join areas that are
effectively adjacent; corridor design in the north is a question about the remaining 28.**

## 6. D28 / D29 / D30 / D31

- Narrowest pinches (width_ratio_p10 @ position): Carp Lake ↔ Pine Le Moray 0.05 @ 0.00; Gwillim ↔ Monkman 0.07 @ 0.29;
  **Tsey Dëk ↔ Tintina Trench 0.07 @ 0.63 while classed corridor-land-with-options** (a pinch inside a two-branch link — the
  D28 case the median cannot see); Klua Lakes ↔ Northern Rocky 0.09; Gwillim ↔ Kakwa 0.10.
- Alternative-link kinds over the 20 tested bridges (run003): affordable 13, far 3, both 3, hard 1.
- Fixed-break tiers (run003): robust core 10,048 km² (slack ≤ cutoff/6), frequent 10,057 (≤ cutoff/2), occasional 16,039 (the
  band), routable beyond the band 836,582. Detour twin: 4.03 km.

## 7. Route branches and the example slots

Run003 decomposes 27 links into 28 branches: **one link has two branches** (Tsey Dëk ↔ Tintina Trench). Run002 had two
(Liard River Corridor ↔ Nahanni, now gone, and Tatonduk ↔ Fishing Branch, now a front). The rule-based proposal on run003:

| slot | pick | basis |
|---|---|---|
| S1 | Gwillim Lake ↔ Pine Le Moray | only viable (0.40; alternative hard) |
| S2 | Wilps Gwininitxw ↔ Swan Lake | filled from last affordable (0.95; far) |
| S3 | Gladys Lake ↔ Spatsizi Plateau | filled from last affordable — **width-not-assessable, a 0.6 km gap; queried below** |
| N2 | Tsey Dëk ↔ Tintina Trench | the only two-branch link |
| N3 | — | no candidate with ≥ 2 branches |

Pin firings: N2's second option (Liard RC ↔ Nahanni) is not an edge; N3's two links (T’akú Tlatsini ↔ Edziza / Stikine) are
open fronts; S2 lost the top class. The pinned narrowing picks (Gwillim ↔ Monkman, Carp Lake ↔ Pine Le Moray) are unchanged.
The interim inset windows are pinned to their run002 positions (A over Dene / Nahanni / Liard River Corridor, B over Gwillim /
Pine Le Moray) at one scale.

## 8. Questions for the chat

1. Should width-not-assessable links be excluded from example-slot candidacy? Gladys Lake ↔ Spatsizi is a table row, not a
   deck example.
2. N3 has no candidate under the branch rule; with fronts removed the north's "room to choose" is carried by one two-branch
   link. Is N3 dropped, or re-defined (e.g. the widest corridor-land-with-options link)?
3. T’akú Tlatsini's links class as open fronts at 31–33 km gaps because the facing areas are huge. Accept, or cap the trigger?
4. Three neutral legend rows on the deck maps, or one "adjacent areas" row with the road / barrier split kept to the table?
5. Run002's directory is now the re-classified record (its 06/07 products change when re-rendered). Accept as the pinned
   run's post-pin state, or freeze the pre-D23 products separately?
6. Note for the record: the D24 floors and the D26 relative floor are inert on this network; the D25 trigger absorbs the
   short links first.
