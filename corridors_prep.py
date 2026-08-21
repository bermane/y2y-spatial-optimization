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

    min_lat = gc["region_filter"].get("min_lat")
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
          f"@ {res} m   (lat >= {min_lat})")
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
