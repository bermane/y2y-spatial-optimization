"""Prep for the 05 corridor analysis (v2): warp the published movement-cost surface onto the
300 m northern routing grid.

Standalone on purpose -- this does NOT go through notebook 02. Three reasons:
  * 02's stage 1 hardcodes the 1 km `-te`/`-tr`; this grid is 300 m.
  * The cost layer must never reach `aligned_stack/` or `manifest.json`. It is not a prioritizr
    feature, it is unoriented (higher = WORSE, unlike every hand-off layer), and adding it would
    corrupt the PU mask that 02/03/04/06 and the in-flight Morris batch all depend on. `config`'s
    `is_feature` flag is documented but read by no code, so it could not be relied on to hold it out.
  * It is one raster, warped once, into its own grid namespace.

Grid drift is the known failure mode for a second warp path (`scenario_core.check_identity` exists
for exactly that), so the grid is derived ONCE by `grid()` and every consumer reads it back off the
written raster rather than re-deriving it.

    import corridors_prep as cp
    g = cp.grid("north");  cp.warp(g);  cp.check(g)      # G2

Ethan runs this; it shells the system GDAL CLIs (osgeo bindings aren't in the venv).
"""
import math
import shutil
import subprocess

import numpy as np
import pyproj
import rasterio

import config


def grid(key="north"):
    """The 300 m northern routing grid: full Y2Y width, cut to lat >= region_filter["min_lat"].

    The lat cut follows v1's convention (`corridors_core.load`): latitude is evaluated down the
    grid's MIDDLE COLUMN and used as a horizontal row cut. Y2Y runs on a long diagonal so a
    parallel is not a straight line in Albers -- this is an approximation, and it is deliberately
    the SAME approximation v1 used, so the two runs describe the same window.

    The warp covers the whole window; `corridors_core.load` crops further to the node bbox plus
    `routing_buffer_km`. Warping generously once and cropping in memory keeps this step independent
    of the node set, which is not known until the vectors are read.
    """
    cfg = config.CORRIDORS[key]
    gc = cfg["grid"]
    res = gc["res_m"]

    sa = config.study_area(config.BUFFER_KM)          # Y2Y boundary, ESRI:102008, buffered
    minx, miny, maxx, maxy = sa.total_bounds

    rf = gc.get("region_filter") or {}          # None / {} = the whole study area (wolverine)
    min_lat = rf.get("min_lat")
    if min_lat is not None:
        to_ll = pyproj.Transformer.from_crs(config.TARGET_CRS, "EPSG:4326", always_xy=True)
        xmid = (minx + maxx) / 2.0
        ys = np.linspace(miny, maxy, 8000)
        lats = np.array([to_ll.transform(xmid, float(y))[1] for y in ys])
        keep = ys[lats >= min_lat]
        if not keep.size:
            raise ValueError(f"region_filter min_lat={min_lat} keeps no rows of the study area")
        miny = float(keep.min())

    left = math.floor(minx / res) * res               # snap out to a clean 300 m grid
    bottom = math.floor(miny / res) * res
    right = math.ceil(maxx / res) * res
    top = math.ceil(maxy / res) * res

    g = dict(
        key=key, res_m=res, crs=config.TARGET_CRS,
        te=[left, bottom, right, top],
        width=int(round((right - left) / res)),
        height=int(round((top - bottom) / res)),
        dir=gc["dir"],
        cutline=gc["dir"] / "_study_area.gpkg",
        src=cfg["resistance"]["source"],
        dst=gc["dir"] / cfg["resistance"]["out_name"],
        resampling=cfg["resistance"]["resampling"],
        expect_classes=cfg["resistance"]["expect_classes"],
    )
    print(f"300 m routing grid ({g['crs']}): {g['te']}")
    print(f"  {g['width']:,} x {g['height']:,} = {g['width']*g['height']/1e6:,.1f} M cells "
          f"@ {res} m   " + (f"(lat >= {min_lat})" if min_lat is not None else "(full study area)"))
    return g


def warp(g):
    """Reproject + clip the cost surface onto the routing grid.

    `-r near` is not a compromise here: the source is already 300 m, so this only changes projection
    (EPSG:3347 -> ESRI:102008) and nearest preserves the four ordinal classes exactly. Averaging
    would silently convert four published classes into a continuous surface dominated by the
    1000-class; mode would erase every sub-cell barrier. Neither trade is needed at native
    resolution.

    The cutline masks outside the buffered Y2Y corridor to NoData. That is a real modelling
    constraint -- ROUTES CANNOT LEAVE THE Y2Y REGION -- and must be stated in the methods. v1 had
    the same constraint implicitly, inherited from the aligned stack's extent.
    """
    for cli in ("gdalwarp",):
        assert shutil.which(cli), f"{cli} not found on PATH (need system GDAL CLIs)"

    g["dir"].mkdir(parents=True, exist_ok=True)
    config.study_area(config.BUFFER_KM).to_file(g["cutline"], driver="GPKG")

    with rasterio.open(g["src"]) as s:
        nodata = s.nodata if s.nodata is not None else float("nan")
        print(f"source: {g['src'].name}  {s.crs}  {s.res[0]:g} m  {s.width:,} x {s.height:,}  "
              f"nodata={nodata}")

    cmd = [
        "gdalwarp", "-overwrite",
        "-t_srs", g["crs"],
        "-te", *map(str, g["te"]),
        "-tr", str(g["res_m"]), str(g["res_m"]),
        "-r", g["resampling"],
        "-cutline", str(g["cutline"]),
        "-dstnodata", str(nodata),
        "-of", "GTiff",
        "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE", "-co", "BIGTIFF=IF_SAFER",
        "-multi", "-wo", "NUM_THREADS=ALL_CPUS",
        str(g["src"]), str(g["dst"]),
    ]
    print("warping (reads only the source window covering -te) ...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"gdalwarp failed for {g['src']}:\n{proc.stderr}")
    print(f"  wrote {g['dst'].relative_to(config.PROJECT_DIR)} "
          f"({g['dst'].stat().st_size/1e6:,.0f} MB)")
    return g["dst"]


def check(g):
    """G2 -- warp fidelity. Asserts, so a bad warp stops the run rather than routing on it."""
    with rasterio.open(g["dst"]) as s:
        assert s.crs.to_string() == rasterio.crs.CRS.from_string(g["crs"]).to_string(), \
            f"CRS drift: {s.crs} != {g['crs']}"
        assert (s.width, s.height) == (g["width"], g["height"]), \
            f"shape drift: {(s.width, s.height)} != {(g['width'], g['height'])}"
        assert s.res == (g["res_m"], g["res_m"]), f"resolution drift: {s.res}"
        assert [round(v) for v in s.bounds] == [round(v) for v in g["te"]], \
            f"extent drift: {list(s.bounds)} != {g['te']}"
        a = s.read(1, masked=True)

    valid = int(a.count())
    total = a.size
    vals = np.unique(a.compressed())
    expect = set(g["expect_classes"])
    extra = sorted(set(vals.tolist()) - expect)
    assert not extra, (f"resampling did not preserve the ordinal classes: found {extra[:10]} "
                       f"outside {sorted(expect)} -- was '-r near' used?")

    print(f"G2 warp fidelity OK: {s.width:,} x {s.height:,} @ {g['res_m']} m, {g['crs']}")
    print(f"  in-corridor cells {valid:,} of {total:,} ({100*valid/total:.1f}% of the window "
          f"rectangle; the rest is outside the buffered Y2Y cutline)")
    print("  class distribution (share of in-corridor cells):")
    for c in sorted(expect):
        n = int((a.compressed() == c).sum())
        print(f"    cost {c:>5}: {100*n/max(valid,1):5.1f}%  ({n:,} cells)")
    frac_max = (a.compressed() == max(expect)).sum() / max(valid, 1)
    if frac_max > 0.25:
        print(f"  NOTE {100*frac_max:.0f}% of the window sits at the maximum cost class. Routing "
              f"will be strongly channelled; if the network fails to connect that is a finding "
              f"about the surface, not a bug (see the Phase 1.3 spread diagnostic).")
    return dict(valid_cells=valid, classes={int(c): int((a.compressed() == c).sum())
                                            for c in sorted(expect)})


# ======================================================================================
# WOLVERINE (analyses/wolverine_refugia_connectivity): the node-class warp, the terrain
# layers behind the "generic terrain rules withheld" variant (W1), its calibration + derivation,
# and the two check-stop figures. Nothing here touches the northern warp.
# ======================================================================================
import json
import hashlib
import pathlib

import geopandas as gpd
import pandas as pd
from rasterio.features import rasterize as _rasterize
from rasterio.enums import Resampling as _Resampling


def _run(cmd, what):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{what} failed:\n{proc.stderr}")


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def warp_classes(g, key="wolverine"):
    """Warp the node-class raster (wolverine refugia classes) onto the SAME routing grid as the
    cost surface: same -te/-tr/-cutline, `-r near` (categorical), Byte with nodata 255."""
    rc = config.CORRIDORS[key]["nodes"]["raster"]
    src, dst = pathlib.Path(rc["source"]), g["dir"] / rc["out_name"]
    cmd = ["gdalwarp", "-overwrite", "-t_srs", g["crs"], "-te", *map(str, g["te"]),
           "-tr", str(g["res_m"]), str(g["res_m"]), "-r", rc.get("resampling", "near"),
           "-cutline", str(g["cutline"]), "-ot", "Byte", "-dstnodata", str(rc.get("nodata", 255)),
           "-of", "GTiff", "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE",
           "-multi", "-wo", "NUM_THREADS=ALL_CPUS", str(src), str(dst)]
    print(f"warping node classes {src.name} -> {dst.relative_to(config.PROJECT_DIR)} ...")
    _run(cmd, "gdalwarp (classes)")
    print(f"  wrote {dst.relative_to(config.PROJECT_DIR)} ({dst.stat().st_size/1e6:,.0f} MB)")
    return dst


def check_classes(g, key="wolverine"):
    """GW1 -- the class warp sits on the cost warp's grid, carries only the expected classes,
    and covers the routable area. Reports the class split either side of the model seam."""
    rc = config.CORRIDORS[key]["nodes"]["raster"]
    dst = g["dir"] / rc["out_name"]
    with rasterio.open(dst) as s, rasterio.open(g["dst"]) as c:
        assert (s.width, s.height) == (c.width, c.height), f"GW1 shape drift {s.width}x{s.height} vs cost"
        assert s.transform == c.transform, "GW1 transform drift vs the cost warp"
        assert s.crs.to_string() == c.crs.to_string(), "GW1 CRS drift vs the cost warp"
        a = s.read(1); cost = c.read(1, masked=True)
    nd = int(rc.get("nodata", 255))
    pu = ~cost.mask if np.ma.is_masked(cost) else np.ones(a.shape, bool)
    vals = np.unique(a[pu])
    extra = sorted(set(vals.tolist()) - set(rc["expect_classes"]) - {nd})
    assert not extra, f"GW1: unexpected class values {extra[:10]} -- was '-r near' used?"
    # Coverage is judged INSIDE the unbuffered Y2Y polygon: the routing grid carries the 20 km
    # buffer (routes may use it) but the refugia product stops at the region boundary, so buffer
    # cells legitimately carry no class (nodata -> class 0 = no refugia in the loader).
    region = _rasterize([(geom, 1) for geom in config.study_area(0).to_crs(g["crs"]).geometry],
                        out_shape=a.shape, transform=s.transform, fill=0, dtype="uint8").astype(bool) & pu
    valid_in = int((a[region] != nd).sum()); n_in = int(region.sum())
    valid = int((a[pu] != nd).sum()); n_pu = int(pu.sum())
    assert valid_in >= 0.999 * n_in, f"GW1: class raster covers only {100*valid_in/n_in:.2f}% of the routable area INSIDE the Y2Y polygon"
    cell_km2 = (g["res_m"] / 1000.0) ** 2
    print(f"GW1 class warp OK: {s.width:,} x {s.height:,} @ {g['res_m']} m on the cost grid; "
          f"{100*valid_in/n_in:.2f}% of routable cells inside the Y2Y polygon carry a class "
          f"({100*valid/n_pu:.1f}% of all routable cells -- the 20 km buffer ring has none, as expected)")
    seam = rc.get("seam_lat")
    rows = {}
    if seam is not None:
        to_ll = pyproj.Transformer.from_crs(g["crs"], "EPSG:4326", always_xy=True)
        xmid = (g["te"][0] + g["te"][2]) / 2.0
        ys = g["te"][3] - (np.arange(a.shape[0]) + 0.5) * g["res_m"]
        lat = np.array([to_ll.transform(xmid, float(y))[1] for y in ys])
        north = (lat >= seam)[:, None] & pu
        south = pu & ~north
        print(f"  class split at the model seam ({seam} N, middle-column latitude; km²):")
        for v in rc["expect_classes"]:
            n_n, n_s = int(((a == v) & north).sum()), int(((a == v) & south).sum())
            rows[v] = (n_n * cell_km2, n_s * cell_km2)
            print(f"    class {v:>2}: north {n_n*cell_km2:>10,.0f}   south {n_s*cell_km2:>10,.0f}")
    return dict(valid_cells=valid, classes={int(v): int((a[pu] == v).sum()) for v in vals if v != nd}, seam_split=rows)


# ---- the variant surface (W1): terrain layers -> tau -> derive -------------------------
def _vec_files(d, patterns):
    d = pathlib.Path(d)
    out = []
    for pat in patterns:
        out += sorted(d.rglob(pat))
    return [p for p in out if p.suffix.lower() in (".shp", ".gpkg")]


def _grid_meta(g):
    with rasterio.open(g["dst"]) as c:
        return c.transform, c.crs, (c.height, c.width), c.read(1, masked=True)


def _ras(geoms, shape, transform, all_touched=False):
    if not len(geoms):
        return np.zeros(shape, bool)
    return _rasterize([(geom, 1) for geom in geoms], out_shape=shape, transform=transform, fill=0,
                      dtype="uint8", all_touched=all_touched).astype(bool)


def _bbox_ll(g):
    to_ll = pyproj.Transformer.from_crs(g["crs"], "EPSG:4326", always_xy=True)
    x0, y0, x1, y1 = g["te"]
    xs, ys = zip(*[to_ll.transform(x, y) for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1),
                                                     ((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1))])
    return (min(xs) - 0.5, min(ys) - 0.5, max(xs) + 0.5, max(ys) + 0.5)


def terrain_layers(g, vcfg, force=False, verbose=True):
    """The layers behind the variant, each rasterized onto the routing grid and cached as a
    GeoTIFF under grid.dir/variant_layers/ (re-used across runs of derive_variant):
      elev_gt   DEM > elev_gt_m           (source rule: elevation > 2300 m, GMTED2010)
      slope_gt  slope > slope_gt_deg      (source rule: slope > 30 deg; np.gradient on the DEM,
                                           the source's ~250 m grain matches our 300 m DEM)
      glacier   RGI 7.0 polygons          (source rule: glaciers, CanVec)
      lake      HydroLAKES >= lake_min_km2 (RETAINED at 1000)
      river     HydroRIVERS DIS_AV_CMS > river_min_cms (RETAINED)
      ocean     outside the Natural Earth land polygons (RETAINED)
      ghm90max  max of the 90 m gHM within each 300 m cell (RETAINED human layers, via tau)
    Prints each layer's coverage and the share of the cost-1000 class it explains."""
    T = vcfg["terrain"]; R_ = vcfg["retained_1000"]
    out_dir = g["dir"] / "variant_layers"; out_dir.mkdir(parents=True, exist_ok=True)
    transform, crs, shape, cost = _grid_meta(g)
    pu = ~cost.mask if np.ma.is_masked(cost) else np.ones(shape, bool)
    cost = np.asarray(cost.filled(np.nan), "float32")
    prov = {}

    def _cached(name, build, dtype="uint8"):
        p = out_dir / f"{name}.tif"
        if p.exists() and not force:
            with rasterio.open(p) as s:
                arr = s.read(1)
            return arr.astype(bool) if dtype == "uint8" else arr
        arr = build()
        with rasterio.open(p, "w", driver="GTiff", height=shape[0], width=shape[1], count=1,
                           dtype=dtype, crs=crs, transform=transform, compress="DEFLATE", tiled=True) as d:
            d.write(arr.astype(dtype), 1)
        return arr

    import rioxarray
    tmpl = rioxarray.open_rasterio(g["dst"], masked=True).squeeze()

    # DEM (GMTED2010 if dropped in, else the 300 m Copernicus-derived DEM already in basemap/)
    gm = pathlib.Path(T.get("dem_gmted", "")) if T.get("dem_gmted") else None
    gm_files = sorted(gm.glob("*.tif")) if gm and gm.exists() else []
    dem_path = gm_files[0] if gm_files else pathlib.Path(T["dem"])
    prov["dem"] = str(dem_path)

    def _dem():
        d = rioxarray.open_rasterio(dem_path, masked=True).squeeze()
        return d.rio.reproject_match(tmpl, resampling=_Resampling.bilinear).values.astype("float32")
    dem = _cached("dem", _dem, "float32")
    dem = np.where(np.isfinite(dem) & (dem > -9000), dem, np.nan).astype("float32")
    elev_gt = _cached("elev_gt", lambda: np.nan_to_num(dem, nan=-1) > float(T["elev_gt_m"]))

    def _slope():
        z = np.nan_to_num(dem, nan=0.0).astype("float64")
        gy, gx = np.gradient(z, float(g["res_m"]))
        sl = np.degrees(np.arctan(np.hypot(gx, gy)))
        sl[np.isnan(dem)] = 0.0
        return sl > float(T["slope_gt_deg"])
    slope_gt = _cached("slope_gt", _slope)

    bbox = _bbox_ll(g)

    def _glacier():
        files = _vec_files(T["glacier_dir"], ["*.shp", "*.gpkg"])
        if not files:
            raise FileNotFoundError(f"no RGI files under {T['glacier_dir']} -- see data/acquire.py")
        parts = [gpd.read_file(f, bbox=bbox) for f in files]
        gl = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=parts[0].crs).to_crs(crs)
        prov["glacier"] = [str(f) for f in files]
        return _ras(gl.geometry, shape, transform, all_touched=True)
    glacier = _cached("glacier", _glacier)

    def _lake():
        files = _vec_files(R_["lakes_dir"], ["HydroLAKES_polys*.shp", "HydroLAKES_polys*.gpkg"])
        if not files:
            raise FileNotFoundError(f"no HydroLAKES polygons under {R_['lakes_dir']} -- see data/acquire.py")
        lk = gpd.read_file(files[0], bbox=bbox)
        lk = lk[lk["Lake_area"] >= float(R_["lake_min_km2"])].to_crs(crs)
        prov["lakes"] = str(files[0])
        return _ras(lk.geometry, shape, transform)
    lake = _cached("lake", _lake)

    def _river():
        files = _vec_files(R_["rivers_dir"], ["HydroRIVERS_v10_na*.shp", "HydroRIVERS_v10_na*.gpkg", "HydroRIVERS*.shp"])
        if not files:
            raise FileNotFoundError(f"no HydroRIVERS lines under {R_['rivers_dir']} -- see data/acquire.py")
        rv = gpd.read_file(files[0], bbox=bbox)
        rv = rv[rv["DIS_AV_CMS"] > float(R_["river_min_cms"])].to_crs(crs)
        prov["rivers"] = str(files[0])
        return _ras(rv.geometry, shape, transform, all_touched=True)
    river = _cached("river", _river)

    def _ocean():
        land = gpd.read_file(config.INPUT_DIR / "basemap" / "ne_10m_admin_1_states_provinces.shp").to_crs(crs)
        return pu & ~_ras(land.geometry, shape, transform, all_touched=True)
    ocean = _cached("ocean", _ocean)

    def _ghm():
        src = sorted(pathlib.Path(R_["human_ghm90_dir"]).glob("*.vrt")) or sorted(pathlib.Path(R_["human_ghm90_dir"]).glob("*.tif"))
        assert src, f"no gHM raster under {R_['human_ghm90_dir']}"
        tmp = out_dir / "ghm90max_raw.tif"
        _run(["gdalwarp", "-overwrite", "-t_srs", g["crs"], "-te", *map(str, g["te"]),
              "-tr", str(g["res_m"]), str(g["res_m"]), "-r", "max", "-dstnodata", "nan",
              "-of", "GTiff", "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE",
              "-multi", "-wo", "NUM_THREADS=ALL_CPUS", str(src[0]), str(tmp)], "gdalwarp (gHM max)")
        with rasterio.open(tmp) as s:
            arr = s.read(1).astype("float32")
        prov["ghm90"] = str(src[0])
        return np.where(np.isfinite(arr), np.clip(arr, 0, 1), np.nan).astype("float32")
    ghm = _cached("ghm90max", _ghm, "float32")

    L = dict(elev_gt=elev_gt & pu, slope_gt=slope_gt & pu, glacier=glacier & pu,
             lake=lake & pu, river=river & pu, ocean=ocean & pu, ghm90max=ghm)
    L["_pu"], L["_cost"], L["_shape"], L["_transform"], L["_crs"], L["_prov"] = pu, cost, shape, transform, crs, prov
    if verbose:
        cell_km2 = (g["res_m"] / 1000.0) ** 2
        c1000 = pu & (cost == 1000)
        print(f"terrain / retained layers on the routing grid ({int(pu.sum())*cell_km2:,.0f} km² routable; "
              f"cost-1000 = {int(c1000.sum())*cell_km2:,.0f} km²):")
        for k in ("elev_gt", "slope_gt", "glacier", "lake", "river", "ocean"):
            m = L[k]
            print(f"    {k:9s}: {int(m.sum())*cell_km2:>10,.0f} km²   explains {100*(m & c1000).sum()/max(c1000.sum(),1):5.1f}% "
                  f"of cost-1000   ({100*(m & c1000).sum()/max(m.sum(),1):5.1f}% of the layer is cost-1000)")
        rest = c1000 & ~(L["elev_gt"] | L["slope_gt"] | L["glacier"] | L["lake"] | L["river"] | L["ocean"])
        print(f"    remainder (cost-1000 explained by none = the human layers): {int(rest.sum())*cell_km2:,.0f} km² "
              f"({100*rest.sum()/max(c1000.sum(),1):.1f}%)")
    return L


def calibrate_human_tau(L, res_m=300, verbose=True):
    """tau for the 90 m-gHM proxy of the source's human cost-1000 layers: the threshold on
    ghm90max that best separates 'human 1000' cells (cost 1000 explained by NO natural layer)
    from 'not 1000' cells, by balanced accuracy. Reported, never asserted."""
    pu, cost, ghm = L["_pu"], L["_cost"], L["ghm90max"]
    nat = L["elev_gt"] | L["slope_gt"] | L["glacier"] | L["lake"] | L["river"] | L["ocean"]
    pos = pu & (cost == 1000) & ~nat & np.isfinite(ghm)
    neg = pu & (cost < 1000) & np.isfinite(ghm)
    bins = np.linspace(0.0, 1.0, 201)
    hp, _ = np.histogram(ghm[pos], bins=bins); hn, _ = np.histogram(ghm[neg], bins=bins)
    cp = np.cumsum(hp) / max(hp.sum(), 1); cn = np.cumsum(hn) / max(hn.sum(), 1)   # share BELOW each edge
    tpr = 1.0 - cp; tnr = cn                                                        # ghm >= tau positive
    ba = 0.5 * (tpr + tnr)
    k = int(np.argmax(ba)); tau = float(bins[k + 1])
    cell_km2 = (res_m / 1000.0) ** 2
    pred = np.isfinite(ghm) & (ghm >= tau)
    conf = dict(tau=tau, balanced_accuracy=round(float(ba[k]), 3),
                tp_km2=round(float((pos & pred).sum() * cell_km2)), fn_km2=round(float((pos & ~pred).sum() * cell_km2)),
                fp_km2=round(float((neg & pred).sum() * cell_km2)), tn_km2=round(float((neg & ~pred).sum() * cell_km2)),
                tpr=round(float(tpr[k]), 3), tnr=round(float(tnr[k]), 3))
    if verbose:
        print(f"human-layer proxy: tau = {tau:.3f} on ghm90max (balanced accuracy {conf['balanced_accuracy']:.3f}; "
              f"TPR {conf['tpr']:.2f} on {int(pos.sum())*cell_km2:,.0f} km² of human cost-1000, TNR {conf['tnr']:.2f})")
        print(f"    confusion (km²): TP {conf['tp_km2']:,}  FN {conf['fn_km2']:,}  FP {conf['fp_km2']:,}  TN {conf['tn_km2']:,}")
    return conf


def derive_variant(g, vcfg, L, tau, out_name, key="wolverine", label=None, verbose=True):
    """GW2 -- the variant surface: recompute-the-maximum with the `withhold` terrain rules
    removed. out = cost; where cost == 1000 AND a withheld layer covers the cell AND no retained
    layer (lake / river / ocean / human proxy ghm90max >= tau) covers it -> `withheld_take`
    (1); `reassign` = {layer: cost} applied the same way. Never raises a cost. Writes the
    surface + <out_name>.meta.json; asserts classes, change-set and grid identity."""
    T = vcfg["terrain"]
    pu, cost, shape, transform, crs = L["_pu"], L["_cost"], L["_shape"], L["_transform"], L["_crs"]
    layer_of = {"elevation_gt_2300_m": "elev_gt", "slope_gt_30_deg": "slope_gt", "glacier": "glacier"}
    withheld = np.zeros(shape, bool)
    for w in vcfg["withhold"]:
        withheld |= L[layer_of[w]]
    retained = L["lake"] | L["river"] | L["ocean"] | (np.nan_to_num(L["ghm90max"], nan=1.0) >= float(tau))
    high = int(max(config.CORRIDORS[key]["resistance"]["expect_classes"]))
    out = cost.copy()
    sel = pu & (cost == high) & withheld & ~retained
    out[sel] = float(vcfg.get("withheld_take", 1))
    reassigned = {}
    for lay, val in (vcfg.get("reassign") or {}).items():
        m = pu & (cost == high) & L[layer_of[lay]] & ~retained
        out[m] = float(val); reassigned[lay] = int(m.sum())
    # GW2 asserts
    fin = out[pu]
    assert set(np.unique(fin).tolist()) <= set(float(c) for c in config.CORRIDORS[key]["resistance"]["expect_classes"]), "GW2: classes"
    changed = pu & (out != cost)
    assert not (changed & (cost != high)).any(), "GW2: a cell below 1000 changed"
    assert not (out > cost)[pu].any(), "GW2: a cost was raised"
    dst = g["dir"] / out_name
    with rasterio.open(dst, "w", driver="GTiff", height=shape[0], width=shape[1], count=1, dtype="float32",
                       crs=crs, transform=transform, nodata=np.nan, compress="DEFLATE", tiled=True) as d:
        d.write(np.where(pu, out, np.nan).astype("float32"), 1)
    cell_km2 = (g["res_m"] / 1000.0) ** 2
    c1000 = pu & (cost == high)
    per_rule = {}
    for w in vcfg["withhold"]:
        m = sel & L[layer_of[w]]
        per_rule[w] = dict(withheld_km2=round(float(m.sum() * cell_km2)),
                           share_of_cost1000=round(float(m.sum() / max(c1000.sum(), 1)), 4))
    kept = pu & (cost == high) & withheld & retained
    dem = None
    p_dem = g["dir"] / "variant_layers" / "dem.tif"
    if p_dem.exists():
        with rasterio.open(p_dem) as s:
            dem = s.read(1)
    by_band = {}
    if dem is not None:
        for a, b in ((0, 1500), (1500, 2000), (2000, 2300), (2300, 2500), (2500, 9000)):
            q = sel & (dem >= a) & (dem < b)
            by_band[f"{a}-{b} m"] = round(float(q.sum() * cell_km2))
    shares = lambda arr: {str(c): round(100 * float((arr[pu] == c).mean()), 2)
                          for c in config.CORRIDORS[key]["resistance"]["expect_classes"]}
    meta = dict(label=label or vcfg.get("label"), key=key, out_name=out_name,
                withhold=list(vcfg["withhold"]), reassign=vcfg.get("reassign") or {},
                withheld_take=vcfg.get("withheld_take", 1), source_rule=vcfg.get("source_rule"),
                thresholds=dict(elev_gt_m=T["elev_gt_m"], slope_gt_deg=T["slope_gt_deg"],
                                lake_min_km2=vcfg["retained_1000"]["lake_min_km2"],
                                river_min_cms=vcfg["retained_1000"]["river_min_cms"], human_tau=float(tau)),
                inputs=dict(cost=str(g["dst"]), cost_sha256=_sha(g["dst"]), **{k: v for k, v in L["_prov"].items()}),
                withheld_total_km2=round(float(sel.sum() * cell_km2)),
                withheld_per_rule=per_rule, by_elevation_band=by_band,
                terrain_kept_at_1000_km2=round(float(kept.sum() * cell_km2)),
                reassigned_cells=reassigned,
                class_shares_before=shares(cost), class_shares_after=shares(out),
                cost1000_km2_before=round(float(c1000.sum() * cell_km2)),
                cost1000_km2_after=round(float((pu & (out == high)).sum() * cell_km2)))
    (g["dir"] / f"{out_name}.meta.json").write_text(json.dumps(meta, indent=2))
    if verbose:
        print(f"GW2 variant OK: {dst.relative_to(config.PROJECT_DIR)} -- {meta['withheld_total_km2']:,} km² withheld "
              f"(cost-1000 {meta['cost1000_km2_before']:,} -> {meta['cost1000_km2_after']:,} km²); "
              f"terrain cells kept at 1000 by a retained layer: {meta['terrain_kept_at_1000_km2']:,} km²")
        for w, r in per_rule.items():
            print(f"    {w:22s}: {r['withheld_km2']:>9,} km²  ({100*r['share_of_cost1000']:.1f}% of cost-1000)")
        if by_band:
            print("    withheld by elevation band: " + ", ".join(f"{k} {v:,}" for k, v in by_band.items()))
        print("    class shares before -> after: " + ", ".join(f"{c}: {meta['class_shares_before'][c]} -> {meta['class_shares_after'][c]}%"
                                                              for c in meta["class_shares_before"]))
    return meta


def variant_summary_under_nodes(g, L, out_name, key="wolverine"):
    """The withheld area UNDER the core refugia classes (what the variant does to the refugia)."""
    rc = config.CORRIDORS[key]["nodes"]
    with rasterio.open(g["dir"] / rc["raster"]["out_name"]) as s:
        cls = s.read(1)
    core = np.isin(cls, rc["classes_core"]) & L["_pu"]
    cell_km2 = (g["res_m"] / 1000.0) ** 2
    c1000 = core & (L["_cost"] == 1000)
    with rasterio.open(g["dir"] / out_name) as s:
        out = s.read(1)
    withheld = c1000 & (out < 1000)
    print(f"under core refugia ({int(core.sum())*cell_km2:,.0f} km²): cost-1000 {int(c1000.sum())*cell_km2:,.0f} km² "
          f"({100*c1000.sum()/max(core.sum(),1):.1f}%) -> withheld {int(withheld.sum())*cell_km2:,.0f} km² "
          f"({100*withheld.sum()/max(c1000.sum(),1):.1f}% of it); {100*(core & (out == 1000)).sum()/max(core.sum(),1):.1f}% of core stays cost-1000")
    return dict(core_km2=round(float(core.sum() * cell_km2)), core_cost1000_km2=round(float(c1000.sum() * cell_km2)),
                core_withheld_km2=round(float(withheld.sum() * cell_km2)))


def variant_maps(g, vcfg, L, out_name, key="wolverine", dec=4):
    """Check-stop-2 figures (inline): the variant surface in the four-class palette, and the
    change map -- one colour per withheld rule, plus terrain cells KEPT at 1000 by a retained
    layer. Review figures, not deliverables."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    pu, cost = L["_pu"], L["_cost"]
    with rasterio.open(g["dir"] / out_name) as s:
        out = s.read(1)
    y2y = config.study_area(0).to_crs(g["crs"])
    x0, y0, x1, y1 = g["te"]; ext = [x0, x1, y0, y1]
    pal = {1: "#FCF0B2", 10: "#F9795D", 100: "#942C80", 1000: "#1A1042"}
    def _cls(arr):
        idx = np.full(arr.shape, np.nan, "float32")
        for k, c in enumerate((1, 10, 100, 1000)):
            idx[arr == c] = k
        return idx
    fig, axes = plt.subplots(1, 3, figsize=(21, 13))
    for ax, arr, ttl in ((axes[0], cost, "published surface"), (axes[1], out, "variant: generic terrain rules withheld")):
        ax.imshow(_cls(arr)[::dec, ::dec], cmap=ListedColormap([pal[c] for c in (1, 10, 100, 1000)]), vmin=-0.5, vmax=3.5,
                  extent=ext, origin="upper", interpolation="nearest")
        y2y.boundary.plot(ax=ax, color="0.2", linewidth=0.6, linestyle="--")
        ax.set_title(ttl, fontsize=11); ax.set_aspect("equal"); ax.set_axis_off()
    axes[0].legend(handles=[Patch(color=pal[c], label=f"cost {c}") for c in (1, 10, 100, 1000)], loc="lower left", fontsize=9)
    # change map
    layer_of = {"elevation_gt_2300_m": ("elev_gt", "#1b9e77", "elevation > 2300 m -> 1"),
                "slope_gt_30_deg": ("slope_gt", "#7570b3", "slope > 30° -> 1"),
                "glacier": ("glacier", "#66c2ff", "glacier -> 1")}
    chg = np.full(cost.shape, np.nan, "float32"); handles = []
    changed = pu & (out != cost)
    k = 0
    for w in vcfg["withhold"]:
        lay, col, lbl = layer_of[w]
        m = changed & L[lay] & np.isnan(chg)
        chg[m] = k; handles.append(Patch(color=col, label=f"{lbl}  ({int(m.sum())*(g['res_m']/1000)**2:,.0f} km²)")); k += 1
    kept = pu & (cost == 1000) & (out == 1000) & (L["elev_gt"] | L["slope_gt"] | L["glacier"])
    chg[kept] = k; handles.append(Patch(color="#d95f02", label=f"terrain but KEPT at 1000 (lake / river / ocean / human)  ({int(kept.sum())*(g['res_m']/1000)**2:,.0f} km²)"))
    other = pu & (cost == 1000) & (out == 1000) & ~kept
    chg[other] = k + 1; handles.append(Patch(color="#bdbdbd", label="other cost-1000 (unchanged)"))
    cols = [layer_of[w][1] for w in vcfg["withhold"]] + ["#d95f02", "#bdbdbd"]
    axes[2].imshow(chg[::dec, ::dec], cmap=ListedColormap(cols), vmin=-0.5, vmax=len(cols) - 0.5, extent=ext, origin="upper",
                   interpolation="nearest")
    y2y.boundary.plot(ax=axes[2], color="0.2", linewidth=0.6, linestyle="--")
    axes[2].legend(handles=handles, loc="lower left", fontsize=8)
    axes[2].set_title("what changed (cost-1000 cells only)", fontsize=11); axes[2].set_aspect("equal"); axes[2].set_axis_off()
    fig.suptitle(f"CHECK STOP 2 — {vcfg.get('label')}", fontsize=13)
    plt.show()
    return fig

