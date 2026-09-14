> **APPLIED 2026-09-11** — spliced into `06_corridors_north_director_package_spec.md` as §3a; implemented as `corridors_mapstyle.py` + `corridors_director.figure_m0b` (M5.20). Kept as the record.

# PATCH — cartographic contract for the director package (06 §3a, new). Splice into
`spec/06_corridors_north_director_package_spec.md` as §3a "Cartography"; do not regenerate.
Naming rule applies: things named, codes in parentheses.

**Why:** current figures decide colour, legend placement, extent, and labels per script. The
result is a cost ramp that shares hues with the class swaths, three legends per figure, no
basemap, no scale/north/locator, and label collisions. Everything below is a rule that
removes one of those local decisions. Zero analysis changes.

---

## 1. One style module — `figures/mapstyle.py` — imported by every figure

No figure script may set a colour, font, line weight, extent, or export setting inline.
If a figure needs something the module lacks, the module is extended and the change logged.

### 1.1 Palette (all hex; CVD-checked with a deuteranopia + protanopia simulation before use)

**Analysis hues — the only saturated colours on any map**

| element | fill | outline | note |
|---|---|---|---|
| corridor land with options (securing) | `#AFC3CF` | none | light blue-grey, sits back |
| already narrowing (squeezed, D17) | `#E69F00` | none | amber (Okabe–Ito) |
| last affordable link (edge-irreplaceable, D7) | `#D55E00` | none | vermilion (Okabe–Ito) |
| only viable connection (both senses, D7+D12) | `#8C1A1A` | `#000000` 0.6 pt + diagonal hatch `///` | hatch is the CVD fallback — vermilion/maroon must remain separable in simulation; if not, hatch stays and the maroon darkens |
| proposed IPCA | `#5F9EA0` at 55% opacity | `#3E6F70` 0.5 pt | teal kept (established); opacity so labels and hillshade read through |
| existing PA | `#9A9A9A` at 55% opacity | `#6E6E6E` 0.5 pt | |

**Basemap — greyscale plus one blue; nothing else**

| element | value |
|---|---|
| land | `#F7F7F5` |
| hillshade | greyscale, multiply blend, 18% opacity (90 m Copernicus or SRTM; cartographic use only — not the terrain-null input, H5) |
| water (lakes ≥ 10 ha, rivers ≥ 28 m³/s from the same hydro sources as the cost surface) | `#CFE0EA` fill, no outline |
| ocean | `#E4EEF3` |
| coastline | `#9CB3C0` 0.3 pt |
| provincial / territorial / international boundary | `#7A7A7A` 0.6 pt dash `4 2` |
| sector boundary | `#333333` 1.0 pt solid |
| Y2Y region boundary | `#333333` 0.8 pt dash `6 3` |

**Cost surface (context figure only, never a basemap):** four flat swatches on the greyscale
axis — cost 1 `#FFFFFF`, 10 `#D9D9D9`, 100 `#8C8C8C`, 1000 `#3A3A3A` — with water drawn
separately in `#CFE0EA` over the cost-1000 class so water/ice/settlement are not one colour.
No colourbar; four swatches in the legend. Percentages go in the caption, not the title.

### 1.2 Type

One family with full diacritic coverage for Indigenous place names (Łł, ǫ, ë, ū, á): **Noto
Sans** (fallback DejaVu Sans, which also covers them; verify glyphs render before sign-off).
Sizes are fixed at the slide scale (figure width 13.33 in):

| role | size / weight / case | colour | halo |
|---|---|---|---|
| figure title | 15 / semibold / sentence | `#1A1A1A` | — |
| jurisdiction | 10 / regular / caps, +0.08 em tracking | `#8A8A8A` | none |
| PA / IPCA name | 8.5 / italic / as declared | `#2B2B2B` | white 2 pt |
| town | 8 / regular | `#2B2B2B`, dot `#2B2B2B` 2.5 pt | white 2 pt |
| annotation / callout | 8 / regular | `#1A1A1A` | white 2 pt |
| legend | 8.5 / regular | `#2B2B2B` | — |
| caption | 8 / regular | `#555555` | — |

Every label is placed by hand in the figure spec (§2) or by `adjustText` with a 3 pt minimum
gap; a label that still collides is dropped, not shrunk. Halo on every label over data.

### 1.3 Layout — one template, two aspect ratios

- **Slide** 13.33 × 7.5 in (16:9). Map panel occupies the left 68% of width; a fixed
  **furniture column** on the right 30% holds, top to bottom: locator inset (sector within
  the Y2Y region, `#333333` boundary, sector filled `#AFC3CF`), the legend, then scale bar
  and north indicator. Title above the map panel, caption line below it. Nothing else is
  ever auto-placed.
- **Report** 8.5 × 11 in portrait for the appendix, same furniture column at the bottom as
  a row.
- The sector is tall; on the slide template the map panel is cropped to the sector's
  bounding box plus 40 km, and the empty north-east (NWT interior) is allowed to be cut by
  the frame — the locator carries the context.
- Scale bar: `matplotlib-scalebar`, 100 km, two segments, `#2B2B2B`, bottom of furniture
  column. North indicator: single line-arrow with "N", same colour, beside it. Graticule:
  none on slides; 2° hairlines `#C8C8C8` 0.2 pt on report figures only.
- Export: PDF (vector, fonts embedded) + PNG 300 dpi, both, every figure, from the same
  call. Filenames as the figure ids (M1, M2 …) plus the run tag.

### 1.4 Legend policy

- **One legend per figure**, in the furniture column, built from patches using the director
  strings already in §3 — never from artist labels.
- Class rows in fixed order: options → narrowing → last affordable → only viable, then
  existing PAs, proposed IPCAs (with the as-declared / treated-as-network line), then the
  boundary lines. Link counts stay as `[n]` chips after the class name.
- No colourbars anywhere in the deck. Continuous surfaces (near-optimality tiers, ensemble
  attribution) appear only in the appendix and use three flat tiers with three swatches.

### 1.5 Insets

- An inset is a **named, fixed-extent box** declared in the figure spec: id, centre,
  width in km, which figure it belongs to. Maximum three per figure.
- Drawn on the main map as a `#333333` 0.8 pt rectangle with the inset id in its corner;
  placed inside the map panel along its lower or left edge with a 0.6 pt leader line to the
  box. Never in the furniture column.
- Insets use the same `mapstyle`, same layer order, no legend, no title; a 20 km scale bar
  and the id only. The main-map label set does not repeat inside an inset; the inset has its
  own hand-placed list (≤ 6).
- Same three-second rule: each inset exists to make one thing obvious, named in the spec.

### 1.6 Layer order (bottom → top), identical on every map and inset

ocean → land → hillshade → water → existing PAs → proposed IPCAs → corridor classes
(options first, only-viable last) → boundaries → inset boxes → labels (jurisdiction,
then PA/IPCA, then towns, then annotations).

---

## 2. Figure spec table (one row per figure; Claude Code fills the label lists, Ethan signs)

| id | template | extent | layers (from §1.6) | hand-placed labels | insets | legend rows | three-second message |
|---|---|---|---|---|---|---|---|
| M0b context — what the land is made of | slide | sector + 40 km | basemap, cost-surface swatches, PAs, IPCAs, class swaths, boundaries | ≤ 10: 5 jurisdictions/towns, 5 anchor areas | none | 4 cost swatches, 4 classes, PA, IPCA, 2 lines | "the south is where the cost is" |
| M1 regime map (anchor) | slide | sector + 40 km | basemap, PAs, IPCAs, class swaths, boundaries | ≤ 12 | none | 4 classes, PA, IPCA, 2 lines | "options in the north, forced in the south" |
| M2 Act 1 — room to choose | slide | northern two-thirds | basemap + light jurisdiction tint, options swaths, branch alternatives equal-weight, PAs, IPCAs | ≤ 10 + partner labels for N2–N3 | up to 2 (N2, N3 branches) | options, PA, IPCA, jurisdiction tint key | "these corridors can be secured along more than one path" |
| M3 Act 2 — options are closing | slide | southern third | basemap, all four classes, open-ground outline on squeezed bands, PAs, IPCAs | ≤ 10 | up to 3 (S1–S3) | 4 classes + open-ground outline | "the map makes the decision here" |
| M4 with / without (N1 pair) | slide, two panels | identical extent both panels | basemap, PAs, IPCAs (dropped one hatched grey in right panel), class swaths | ≤ 6, same in both | none | shared legend, one column | "what the network loses if this one proposal does not proceed" |

Insets get their own rows beneath (id, parent, centre, width km, ≤ 6 labels, message).

---

## 3. Render QA — Claude Code runs this on the PNG before showing any figure

1. Nothing clipped at the frame except the allowed NWT crop.
2. Zero label overlaps; every label over data has a halo; all diacritics rendered.
3. Legend, locator, scale bar, north present and in the furniture column; one legend only.
4. Class colours separable in deuteranopia and protanopia simulations; only-viable hatch visible at 100% and at 50% zoom.
5. No saturated hue outside the analysis palette; basemap greys + one blue only.
6. Layer order matches §1.6 (spot-check: a class swath is never under a PA fill).
7. Export produced both PDF and PNG; fonts embedded.
8. The three-second message: describe in one sentence what the figure shows at a glance and compare to the spec row. Report any mismatch rather than fixing the message.

Report the checklist result with the figure. A figure that fails any item is not shown.

---

## 4. Build order and the prompt

Anchor first: **M1 only** until signed; then M0b (same extent, adds the cost swatches);
then M3 with its insets (hardest layout); then M2; then M4. Insets are built only after the
parent figure is signed.

Prompt to Claude Code (verbatim is fine):

> Create `figures/mapstyle.py` from 06 §3a.1 before writing any figure code — palette, type,
> layout templates, legend builder, inset helper, export function. Then render **only M1**
> per the §3a.2 row. Run the §3a.3 QA list on the PNG, fix every failure, and show me the
> figure with the checklist result. Do not start M0b, M2, M3, or M4 until I sign off M1.
> If M1 needs something `mapstyle.py` doesn't provide, add it to the module and note the
> addition; never style inline.
