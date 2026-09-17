# Communities analysis — the bear coexistence layer: report-back for the spec chat (2026-09-16)

The communities analysis is the last piece of the Y2Y framework. Its first (and so far only) input is the
Communities & Conservation team's layer of **active local and regional bear coexistence groups per 2021 Canadian
Census Division / US county**, delivered 2026-09-16 to `input_data/bear_coexistence/CoexistenceGroup_CDCounty_SpatJoin/`
(`.shp` + `.gpkg` twins of one layer + `README_MetaData.docx`). No spec exists yet. This report-back is what the
exploratory notebook `analyses/communities/01_bear_coexistence_explore.ipynb` measured (read-only on the input;
audit tables in `analyses/communities/audit/`, figures in `figures/`; smoke-run headless, Ethan runs the record
copy), plus Ethan's two stated uses for the layer and the assessment of each. Nothing is registered in `config`,
nothing aligned, no solve touched.

## 0. Headline

**The layer is a complete, clean tessellation of Y2Y with one real defect: 21 of its 108 units carry the wrong
province/state suffix, and four of those copied a neighbour's group count.** The polygons themselves are genuine
2021 CDs / counties, already clipped to the unbuffered 2013 Y2Y boundary (99.99% coverage, no overlaps). The
suffix bug is a spatial-join tie-break at state borders — label text only — so it does not signal wider
corruption. The four copied counts (Madison ID, Teton ID, Lincoln WY, Park WY — all in the Greater Yellowstone
corner) are the one thing to set aside. **For Ethan's two uses the limiting facts are different from the bug:**
for *proximity*, `n_groups` sums three group types (Bear Smart communities are one) and the support is a county
or CD polygon spanning 0.02–296,959 km², so distance to a unit means little outside the southern counties and
cannot isolate Bear Smart communities; for *naming*, the layer works well in British Columbia (the Kootenays,
Columbia, Okanagan–Boundary, Stikine fall straight out of the regional-district names), needs a lookup in
Alberta (numbered divisions), and fails in the north (one 297,000 km² "Yukon" unit; NT "Region 1 / Region 4")
and the US south (a cluster spans nine counties). Both uses are best served by the same request to the C&C
team: the tracking-database rows behind the file (group, type, county, town).

## 1. What the dataset is (from its own metadata)

- Counts of **active local + regional bear coexistence groups**, desktop review + partial expert knowledge,
  **current to July 2026**; three types counted — (i) agencies + ENGOs working on coexistence, (ii) Bear Smart
  communities (certified or in progress) + local community working groups, (iii) rangeland collaboratives +
  watershed groups — **but only the total ships** (`n_groups`).
- Excluded: federal / provincial / state-level groups; groups with inactive or unknown status. The authors call
  it "a draft and underrepresentation of all cumulative efforts".
- Method (their words): in R, each group was "mapped as a binary 1 [to] the closest 2021 CD / county, and the
  total summed"; units with no group are **NA** (0 in the ArcGIS copies); groups with unclear boundaries were
  placed by best knowledge of the town / city / hamlet where activity occurs.
- Fields: `country` (Canada / USA), `MappingUnit` (`<name>_<province or state>`), `n_groups` (float). EPSG:4326.
- The metadata's file-name field reads "…_JoinFire" (stale); `~$ADME_MetaData.docx` is a Word lock file.

## 2. What was measured (01, all read-only)

**Files.** The `.shp` and `.gpkg` are the same layer: attributes identical; geometries topologically identical
(Hausdorff distance 0 m; only 10/108 vertex-exact because ring start / vertex order differs). The shapefile
truncates `MappingUnit` → `MappingUni`. Everything downstream reads the `.gpkg`.

**Attributes.** 108 units; **30 hold ≥1 group; 53 groups as shipped**; 78 NA. Counts: 1 × 13 units, 2 × 13,
3 × 2 (Division No. 15 AB, East Kootenay BC), 4 × 2 (Central Kootenay BC, Missoula County MT). By country:
Canada 18 groups in 9 of 26 units; USA 35 in 21 of 82. `MappingUnit` is **not unique** (104 distinct strings
for 108 rows) — §2 label QA.

**Geometry (in ESRI:102008).** 108 MultiPolygons, all valid, none empty; 98 single-part. Unit areas: min 0.02 km²
(Canyon County ID, a clip sliver), median 3,874, mean 12,684, **max 296,959 (the Yukon CD)**; 4 units < 100 km².
Sum of unit areas 1,369,830 km² vs union 1,369,827 → **overlap 3 km²**. Against the unbuffered 2013 Y2Y boundary
(1,369,970 km²): covered **1,369,825 km² (99.99%)**; every unit ≥ 99.2% inside; 2.2 km² of unit area outside.
Uncovered: **144 km² in 119 pieces**, of which one **133 km² piece at the Alaska corner (65.3° N, 141.0° W)** — the
northern tip of Y2Y crosses the 141st meridian and the file has no Alaska borough; the rest is boundary noise.
**Conclusion: a Y2Y-clipped tessellation, not a set of whole counties.**

**Label QA** (suffix vs the Natural Earth admin-1 polygon containing each unit's representative point; the
project basemap layer). `country` correct 108/108. **Suffix wrong 21/108** (Appendix A). In every case the CD /
county *name* is a real unit of the admin-1 that contains the polygon (Gallatin / Ravalli / Sanders → MT; Baker /
Malheur / Wallowa → OR; Asotin / Columbia / Garfield / Pend Oreille / Spokane / Walla Walla → WA; Regions 1, 2, 4
→ NT; Yukon → YT; Peace River → BC), so the polygons are right and the label is wrong. Where the units actually
are: AB 8 (4 with groups, 8 groups), BC 14 (5, 10), NT 3 (0), YT 1 (0), ID 33 (4, 6), MT 28 (14, 25), OR 6 (0),
WA 8 (0), WY 7 (3, 4).

**Mechanism.** **19 of the 21 wrong suffixes name a jurisdiction that physically touches the polygon** — the
signature of a spatial join to a state/province layer picking the neighbour at shared borders (roughly a third
of the ~62 border units were hit). The two exceptions, **Madison County ID (73 km from Montana) and Lincoln
County WY (140 km from Montana), both carry "Montana"** and cannot be adjacency; they got label *and* count
together from their Montana namesake by name. All four name collisions (Madison ID/MT, Teton ID/WY, Lincoln
WY/MT, Park WY/MT) carry **exactly the namesake's `n_groups`** (2, 1, 1, 2) — with 78/108 units NA, a chance
match on all four is implausible. **So: 53 groups as shipped, 47 if the four are copies.** Whether counts for the
other 17 mislabelled units (all NA) were *lost* — a genuine "Gallatin County_Montana" tally with no polygon to
land on — cannot be told from the file; the C&C team can tell from their database total.

**Support.** Groups per 10,000 km² of unit ranges 0.1–28.5; the top value is Madison County ID (a suspect unit),
then Division No. 6 AB 9.5, Pondera MT 8.6, Teton ID 8.6 (suspect), Teton MT 6.6. Count, density and presence
give different maps because unit size spans seven orders of magnitude.

## 3. Use 1 — proximity of conservation land / clusters to bear-smart communities (Ethan, 2026-09-16)

**Sound:** the polygons and their placement (distances to units are trustworthy); which correctly-labelled units
hold groups (87/108 units carry a key the count join could match).
**Not sound:** the four collision counts — false positives in the Yellowstone / ID–WY corner (Park County WY
alone is 15,949 km² inside Y2Y, adjacent to the park), which would create spurious "near a coexistence community"
land in exactly the southern region where the proximity measure has resolution. Set aside unless confirmed.
**Possible but unverifiable:** false negatives on the 17 mislabelled NA units (Gallatin, Ravalli, Sanders MT;
Spokane, Pend Oreille WA; …).
**The limiting facts for this use are not the bug:**
1. `n_groups` sums three types; "Bear Smart community" cannot be isolated from the file.
2. The support is a county / CD polygon. A cluster in the north is always hundreds of km from the nearest
   unit with a group; inside a 10,000 km² Montana county the polygon cannot say where the community is; 78 of
   108 units are NA. Proximity to *towns* (the level the metadata says groups were placed at) is the measure
   that answers the question; proximity to polygons is a coarse fallback.

## 4. Use 2 — naming regions of Y2Y for clusters ("the Kootenays", "Peace region") (Ethan, 2026-09-16)

A better fit than proximity: a complete tessellation with real administrative names, and the count field is
irrelevant. Overlay of the **12 deck picks** (v3.1 package, `director_package/tables/picks.csv` + `clusters.gpkg`)
with the units, share of pick area by unit (suffix corrected to the containing province/state):

| pick | current placeholder (nearest PA/IPCA + bearing) | units by area share |
|---|---|---|
| 1 (Act 1) | SW of Tahltan – Sacred Headwaters | Kitimat-Stikine 82%, Stikine 14% |
| 2 (Act 1) | Purcell Wilderness Conservancy vicinity | East Kootenay 53%, Columbia-Shuswap 29%, Central Kootenay 9%, Fraser-Fort George 9% |
| 3 (Act 1) | N of Granby Park | Thompson-Nicola 35%, North Okanagan 21%, Kootenay Boundary 16%, Central Kootenay 14% |
| 4 (Act 1) | NW of Frank Church Wilderness | Idaho County 29%, Valley County 19%, Wallowa (OR) 15%, Ravalli (MT) 13% — 9 units |
| 5 (Act 2, S1) | Tahltan – Sacred Headwaters vicinity | Kitimat-Stikine 59%, Stikine 34% |
| 6 (Act 2, S1) | Purcell Wilderness Conservancy vicinity | East Kootenay 57%, Columbia-Shuswap 23%, Central Kootenay 9%, Division No. 9 (AB) 7% |
| 7 (Act 2, S2) | NW of Wilps Gwininitxw | Kitimat-Stikine 71%, Stikine 24% |
| 8 (Act 2, S2) | S of Mount Robson Park | East Kootenay 43%, Columbia-Shuswap 32%, Fraser-Fort George 15% |
| 9 (Act 2, S3) | S of Purcell Wilderness Conservancy | East Kootenay 80%, Central Kootenay 20% |
| 10 (Act 2, S3) | NE of Gospel Hump Wilderness | Idaho County 100% |
| 11 (Act 2, S4) | E of Fishing Branch Wilderness Preserve | Yukon 72%, Region 1 (NT) 25% |
| 12 (Act 2, S4) | E of Nahanni National Park Reserve | Region 4 (NT) 97% |

- **Works in BC** (where most of the core sits): picks 2/6/8/9 → "Kootenays / Columbia"; 3 → "Okanagan–Boundary";
  1/5/7 → "Stikine". A largest-share rule with secondaries ≥ ~15% gives a defensible name every time.
- **Alberta:** divisions are numbered — needs a small lookup to principal places (8 Alberta units in Y2Y;
  StatCan's CD → CSD list).
- **The north fails:** "Yukon" is one 297,000 km² unit; NT units are "Region 1 / 2 / 4". Picks 11–12 get
  nothing usable → a different gazetteer there (the northern package's PA / IPCA names, watersheds, or First
  Nations territory names — the last with the C&C team).
- **The US south is too fine:** pick 4 spans nine counties in three states, none above 29%; the honest name is
  a landscape one ("Central Idaho", "Salmon–Bitterroot") that no county supplies.
- **The labels matter for this use** ("Yukon_British Columbia", "Peace River_Alberta" would name wrongly) — build
  from the audit table's containing-admin-1 column, not the shipped field. The four copied counts are irrelevant.
- **The deliverable is a curated lookup, unit → region**, vetted by Y2Y staff (the three Kootenay districts →
  "Kootenays"; Peace River RD + the matching Alberta divisions → "Peace region"; …), combined with the existing
  landmark placeholder: "Sacred Headwaters (Stikine)", "Purcell–Columbia (Kootenays)". Plug-in point:
  `director_core.placeholder_name` (decision (e) of the package spec, "Ethan renames") — a `region` column
  beside it on T-D1 and `picks.csv`, nothing else disturbed.

## 5. Decisions requested

- **D-C1 — Request to the C&C team (both uses hinge on it):** the tracking-database rows behind the file —
  group, type, status, county, **town / community** (coordinates if held); confirm whether Madison ID, Teton ID,
  Lincoln WY and Park WY really have groups; their database total (settles the false-negative question). The
  suffix fix we can do ourselves from the containing polygon; a re-export is optional.
- **D-C2 — Proximity design:** (a) target set = Bear Smart communities only, or all three types; (b) support =
  town points (preferred) vs the polygon units (fallback, with the four collision units set aside);
  (c) the statistic — distance from each cluster / tier cell to the nearest community, reported per cluster
  (min / median) and as a 1 km surface on the project grid; (d) **DECIDED (Ethan, 2026-09-16): NA stays NA, not recoded to 0** — the file has no zeros
  (78 NA / 30 counted; the metadata's 0 exists only in the team's ArcGIS copies), so "no record" is never
  painted as a measured zero and the 17 mislabelled NA units keep a possible lost count visible.
- **D-C3 — Naming:** adopt the unit → region lookup; rule = largest area share + secondaries ≥ 15%; the
  gazetteer for the north; the Alberta division lookup; the combined "landmark (region)" form; who vets the
  region words.
- **D-C4 — Scope:** whether the communities analysis has a third product beyond these two (e.g. an overlay on
  Act 3, high-value land *with* existing coexistence capacity) — asked, not proposed. The layer is a capacity /
  social layer, not a conservation value; it does not enter the optimizer as a feature.
- **D-C5 — Spec + logs:** the analysis needs its own spec and the binding `spec/methods_log.md` +
  `spec/results_log.md` pair, mirroring the other three analyses; the chat writes the spec, the folder layout
  follows `analyses/y2y/`.

## 6. Proposed next build (not started; waits on D-C1–D-C3)

- **02_proximity** (py, zero-solve): the community layer (points from D-C1, else polygon units with the four set
  aside), a nearest-community distance surface at 1 km on the project grid (`config.TARGET_CRS`, the aligned-stack
  frame), per-cluster tables for the 12 picks and the T-D1 register, one figure. Hours, not days.
- **03_region_names** (py, zero-solve): the 108-unit lookup CSV (drafted by me, vetted per D-C3) → overlay rule →
  `region` column on `picks.csv` / T-D1 via `director_core`; the north from the chosen gazetteer.
- Both read `01`'s audit table for the corrected suffix; neither registers the layer in `config.DATASETS`.

## Appendix A — the 21 mislabelled units (`audit/bear_coexistence_label_qa.csv`)

| unit as shipped | polygon is in | n_groups | wrong suffix adjacent? |
|---|---|---|---|
| Peace River_Alberta | British Columbia | NA | yes |
| Yukon_British Columbia | Yukon | NA | yes |
| Region 1_Yukon | Northwest Territories | NA | yes |
| Region 2_Yukon | Northwest Territories | NA | yes |
| Region 4_British Columbia | Northwest Territories | NA | yes |
| Gallatin County_Idaho | Montana | NA | yes |
| Ravalli County_Idaho | Montana | NA | yes |
| Sanders County_Idaho | Montana | NA | yes |
| Baker County_Idaho | Oregon | NA | yes |
| Malheur County_Idaho | Oregon | NA | yes |
| Wallowa County_Idaho | Oregon | NA | yes |
| Asotin County_Idaho | Washington | NA | yes |
| Pend Oreille County_Idaho | Washington | NA | yes |
| Spokane County_Idaho | Washington | NA | yes |
| Columbia County_Oregon | Washington | NA | yes |
| Garfield County_Oregon | Washington | NA | yes |
| Walla Walla County_Oregon | Washington | NA | yes |
| **Madison County_Montana** (701 km²) | Idaho | **2 = Madison MT's** | **no (73 km)** |
| **Teton County_Wyoming** (1,166 km²) | Idaho | **1 = Teton WY's** | yes |
| **Lincoln County_Montana** (6,929 km²) | Wyoming | **1 = Lincoln MT's** | **no (140 km)** |
| **Park County_Montana** (15,949 km²) | Wyoming | **2 = Park MT's** | yes |

## Appendix B — artifacts

- `analyses/communities/01_bear_coexistence_explore.ipynb` — §1 files + metadata, §2 attributes, §3 geometry,
  §4 label QA (writes `audit/bear_coexistence_units.csv` — per unit: corrected admin-1, flags, area, share
  inside Y2Y — and `audit/bear_coexistence_label_qa.csv`), §5 distributions, §6 map (count vs density),
  §7 findings. The adjacency test (§2 mechanism) and the pick overlay (§4) were run in-session and are not
  yet cells; both are a few lines and will be added if the chat wants them on the record.
- `figures/bear_coexistence_distributions.png`, `figures/bear_coexistence_map.png`.
- CLAUDE.md "ANALYSIS 4" section; project memory `communities-analysis`.
