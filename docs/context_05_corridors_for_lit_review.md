# Context: least-cost corridor analysis in a Y2Y conservation-prioritization project

*Prepared as a self-contained briefing to discuss against the wildlife-corridor literature. I want a
critical read on where this sits relative to best practice, and what to weigh when planning changes.*

---

## 1. The project

A conservation-prioritization framework for the **Yellowstone-to-Yukon (Y2Y) corridor** — a
~1.3 million km² transboundary region from Wyoming to Yukon. Grid is **1 km, ESRI:102008 (North
America Albers Equal Area Conic)**, 1,286 × 3,312 cells, **1,272,914 planning units**.

The main line of work is systematic conservation planning with `prioritizr` (integer/linear
programming): minimum-shortfall objective, 100% targets, 30%-of-area budget, existing protected
areas locked in. Features are 8 continuous layers + 40 IUCN Global Ecosystem Typology ecosystem
functional groups.

**This briefing is about a separate, standalone piece — the corridor analysis ("05").**

### Why the corridor analysis exists

We first tried to get connectivity out of the optimizer, using `prioritizr`'s connectivity penalty.
It doesn't do what we needed: **the penalty rewards selecting aggregated permeable land, but it does
not route between specified endpoints.** You cannot ask it "how does an animal get from park A to
park B." We built it, confirmed the limitation, and reverted.

So the corridor analysis is a separate least-cost routing model. It is **not** an optimization
output — it's a graph/routing model over a resistance surface.

---

## 2. What the corridor model actually does

Implemented in Python (`scikit-image`'s `MCP_Geometric` for cost-distance). The pipeline:

### 2a. Resistance surface

Resistance is built from a **weighted blend of existing regional data products**, not from
species data or expert opinion:

```
each driver d scaled to 0–1:   s_d = clip( (x_d − p_lo) / (p_hi − p_lo), 0, 1 )
permeability:                  P   = ( Σ_d w_d · s_d ) ^ conn_exponent
resistance:                    R   = ( 1 / max(P, perm_floor) ) · barrier_base ^ gHM
```

Current parameterization (northern run):

| Driver | Weight | What it is |
|---|---|---|
| `transboundary_connectivity` | 0.50 | Pither et al. **omnidirectional connectivity current density** (a circuit-theory product) |
| `climate_corridors` | 0.30 | Carroll et al. 2018 **climate-analog current-flow centrality** |
| `climate_type_macrorefugia` | 0.20 | AdaptWest CMIP6 **backward climate velocity**, inverted (low velocity = refugium) |

- `conn_exponent = 2.0` — sharpens the permeability blend
- `barrier`: `base = 10.0` raised to the power of **gHM** (Theobald global Human Modification, 0–1),
  i.e. resistance is multiplied by up to 10× through the human footprint
- `perm_floor = 1e-3` caps maximum resistance
- Percentile anchors **p1/p99**

**On the anchors — a decision we tested empirically.** We compared p0/p100, p1/p99, p2/p98, p5/p95.
p0/p100 fails because the connectivity layer's max (65.4) is a single-pixel pinch-point tail vs. p95
of 3.86 — anchoring there flattens the whole resistance surface to a 2.2× spread and the router
stops following the landscape and draws near-straight lines. p5/p95 fails differently: clipping the
bottom 5% to zero manufactures hard walls at `perm_floor` out of merely poor land. p1/p99 keeps an
~11× spread. We also had to switch from `x/p_hi` scaling to full min–max, because the macrorefugia
layer's values run ~10–15 and never approach zero, so the old scaling left it **near-constant and
effectively inert** (its correlation with resistance was −0.03; after the fix, −0.10).

### 2b. Network topology

1. Nodes = protected areas and proposed Indigenous Protected and Conserved Areas (IPCAs),
   rasterized as **areal polygons** (not points).
2. Cost-weighted distance computed from every node.
3. Node-to-node least-cost distance matrix → **minimum spanning tree (Prim)**.
4. Per MST edge: an explicit **traceback centre-line** (guarantees continuity) **plus** a width band —
   cells where `CWD_i + CWD_j ≤ LCP_cost + width_frac · edge_cost`, with `corridor_width_frac = 0.05`.
5. **Node land is subtracted from the final corridor.** This mattered: `CWD_i = 0` throughout node i,
   so the band criterion passes across the entire node by construction, and ~37% of the raw swath
   was landing inside ground that is already a protected area or IPCA proposal. We report both.

### 2c. Uncertainty handling

- **Jitter ensemble** (our analog to modelling-to-generate-alternatives): 12 re-solves with
  resistance multiplied by uniform noise `1 + 0.2·U(−1,1)`, producing a **corridor frequency
  surface** (robust core vs. flexible periphery) plus the 3 most-distinct near-optimal networks,
  scored by route overlap and by a resistance-independent **centre-line length premium**.
- **Scenario comparison**: the percentile-anchor choice is itself run as two full end-to-end
  scenarios (p1/p99 vs p5/p95), each with its own ensemble, compared by Jaccard.

### 2d. Post-hoc co-benefit audit

The corridor network is decomposed into **segments** — removing node polygons cuts the network at
every protected area, so the connected components *are* the physical links (23 of them; top 10 hold
94% of area). Each segment gets a value profile (star plot) across the biodiversity/carbon/climate
layers, compared against IPCAs and existing PAs. **Framed deliberately as an audit, not a
scorecard** — corridors are routed for permeability, so a low value on some axis is a finding, not a
failure.

---

## 3. Current results (northern BC + Yukon run)

- 42 nodes (10 proposed IPCAs + 32 existing PAs ≥ 200 km²), 41 MST edges (29 between genuinely
  separated nodes), **1 connected network group**
- **18,188 km²** of new corridor land; robust core (frequency ≥ 0.9) 14,066 km² of 22,846 km²
  ever-used
- Near-optimal alternatives: 77–83% route overlap with the baseline, length premium −1.4% to +1.3%
  (a perturbed run can find a *shorter* centre-line, since length rather than cost is the yardstick)
- **Scenario Jaccard p1/p99 vs p5/p95 = 0.618** — same 41 MST edges and same trunk, differing at
  several links
- Co-benefit audit: corridors are **complementary, not redundant** — per 1,000 km² they beat both
  existing PAs and proposed IPCAs on biomass carbon (0.127 vs 0.050/0.068), connectivity (0.105 vs
  0.088/0.084) and mammal AOH richness, while the PAs/IPCAs dominate **soil carbon**
  (0.119–0.125 vs 0.063)

---

## 4. What I already know is weak

Stating these up front so the discussion can go past them:

1. **No organism.** This is **structural** connectivity. No species, no movement data, no dispersal
   parameters. The resistance surface encodes "landscape features associated with connectivity in
   general," which is a very different claim from "an animal can get through here."
2. **A circuit-theory product is an input to a least-cost model.** Our dominant driver (weight 0.50)
   is an omnidirectional current-density surface — itself the output of a connectivity model with
   its own resistance assumptions. I am effectively stacking a routing model on top of someone
   else's connectivity model. I don't know whether this is defensible or circular.
3. **Nothing is calibrated.** `conn_exponent = 2.0`, `barrier_base = 10.0`, `corridor_width_frac =
   0.05`, and the driver weights (0.5/0.3/0.2) are all reasoned but arbitrary. The percentile anchors
   are the *only* parameter we tested systematically.
4. **MST gives zero redundancy by construction.** It's the minimum-total-cost tree — n−1 edges, no
   alternative paths, no cycles. Real networks presumably want redundancy.
5. **No validation of any kind.** Nothing has been checked against movement data, genetic data,
   occurrence data, or observed crossings.
6. **The jitter ensemble is ad hoc.** Uniform multiplicative noise on the final resistance surface is
   not a principled representation of any actual uncertainty (parameter? data? model structure?).
7. **1 km grain** across the whole extent.

---

## 5. The change I'm now planning — and where I most want a critical read

A Y2Y program director gave us their actual decision rule for the **Alberta eastern slopes**:

> "#1 factor for us is where grizzly bears are moving and ensuring protection (for private lands) and
> permeability (mostly across highways)... if grizzly bears aren't moving there, or trying to move
> there but unable to, it's not really a priority for us."

With an exception clause for **multi-species highway mortality hotspots**, because engaging there
builds the enabling conditions for grizzly crossings later.

So the plan is to redirect the corridor model to the eastern slopes and shift it from generic
structural connectivity toward **grizzly-specific functional connectivity**:

- **Swap the drivers.** The two climate layers (weights 0.3 and 0.2) are climate-*analog* surfaces
  with no bearing on where a bear walks. Proposed: a grizzly habitat/RSF layer dominant, structural
  connectivity secondary, climate dropped or held at low weight as a future-proofing term.
- **Add highways as explicit linear barriers.** They are currently invisible: a 2-lane highway
  averaged from 90 m gHM to 1 km effectively vanishes. Plan is to rasterize the highway network as
  lines with per-class weights, possibly scaled by traffic volume (AADT).
- **New output: crossing-site detection.** Intersect the corridor network with the highway raster,
  cluster into sites, rank by pinch-point narrowness, ensemble frequency, and highway class.
- **Validate against wildlife-crossing structure data** we have in hand — including the Banff/Bow
  Valley Trans-Canada system, probably the most-studied crossing complex anywhere.
- Nodes would be the Alberta mountain parks (Banff, Jasper, Willmore, Kananaskis, Castle, Waterton)
  plus foothills PAs.
- Considering refining to **300 m** for this window (~118,000 km²), since 1 km identifies a *stretch*
  of highway, not a crossing site.

---

## 6. What I want to discuss

**On the resistance surface:**
1. How does the literature treat resistance built from **stacked existing connectivity products**
   rather than from species data or expert elicitation? Is that a recognized approach with a name, or
   is it a shortcut people warn about?
2. I'm about to derive resistance from a **grizzly habitat-suitability/RSF layer**. My understanding
   is there's a substantial critique that habitat suitability ≠ movement resistance — animals move
   through things they don't live in, and dispersers behave differently from residents. How serious
   is this, and what's the recommended practice when you have habitat models but no telemetry?
3. Is there guidance on the **transformations** — my `1/P^2` and `10^gHM` are invented. Does the
   literature give defensible functional forms, and how much do corridors actually move when you
   change them?

**On method choice:**
4. **Least-cost path vs. circuit theory vs. individual-based / agent-based movement models** — where
   does the field currently sit, and does the answer change when the deliverable is "site a wildlife
   crossing structure" rather than "map regional connectivity"?
5. Is **MST** a defensible network topology for conservation, or should I be using something with
   redundancy? What do people use, and how is redundancy justified to funders who see it as
   duplication?
6. **Corridor width** — my `width_frac` slices a cost-distance band. Is there ecological guidance on
   corridor width, particularly for a wide-ranging carnivore like grizzly, or is it inherently a
   policy/pragmatics choice?

**On the highway/crossing application specifically:**
7. What's the established methodology for **siting wildlife crossing structures**, and how do
   connectivity models actually feed into it? Am I reinventing something with an established
   literature and toolset?
8. How is **traffic volume** typically handled — as resistance, as mortality risk, or as a separate
   barrier term? Is there a standard treatment?
9. What is the appropriate **grain**? Is 300 m defensible for crossing-site identification, or does
   this class of question require finer?

**On validation:**
10. Given crossing-structure locations and possibly wildlife-vehicle-collision records, what's the
    **strongest validation design** available? Corridor models seem rarely validated — what counts as
    convincing, and what are the pitfalls (e.g. structures were sited by people using similar
    reasoning, so agreement may be circular)?
11. Is the **jitter ensemble** a recognized approach to corridor uncertainty, or is there a more
    principled sensitivity/uncertainty framework I should adopt?

**On framing:**
12. This is intended as an **applied decision-support product for an NGO**, with a possible
    application paper. What are the field's expectations for reporting connectivity analyses — is
    there a standard (assumptions, validation, uncertainty) I should be meeting? What are the common
    failure modes in applied corridor work that reviewers and practitioners flag?

Please push back where the approach is weak. I would rather rebuild now than defend something
indefensible later.
