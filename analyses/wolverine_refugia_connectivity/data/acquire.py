"""Open datasets the wolverine variant surface needs (W1), where they go, and a best-effort
downloader. Run from notebook 01 (section 5): `acquire.check()` then, if wanted, `acquire.fetch()`.

  input_data/glaciers/     RGI 7.0 glacier outlines, regions 01 (Alaska) + 02 (Western Canada & USA)
                           -- the source's glacier rule (CanVec) reproduced on both sides of the border
  input_data/hydrosheds/   HydroLAKES v1.0 polygons (lakes >= 10 ha retained at cost 1000)
                           HydroRIVERS v1.0 North America (rivers > 28 m3/s retained at cost 1000)
  input_data/dem_gmted/    OPTIONAL: GMTED2010 7.5" mean, the source's own DEM for the elevation /
                           slope rules (else basemap/dem_y2y_300m.tif -- same grain, 96% agreement
                           at 2,300 m measured)

Licences: HydroSHEDS products are CC BY 4.0 (Lehner & Messager 2016; Lehner & Grill 2013); RGI 7.0
is CC BY 4.0 (RGI Consortium 2023). Cite them in the methods. Nothing here is a prioritizr feature.
"""
import pathlib
import shutil
import sys
import urllib.request
import zipfile

ROOT = next(p for p in [pathlib.Path(__file__).resolve(), *pathlib.Path(__file__).resolve().parents]
            if (p / "config.py").exists())
INPUT = ROOT / "input_data"

DATASETS = {
    "rgi70_r01": dict(dir=INPUT / "glaciers", glob="*01_alaska*/*.shp", required=True,
                      urls=["https://daacdata.apps.nsidc.org/pub/DATASETS/nsidc0770_rgi_v7/regional_files/RGI2000-v7.0-G/RGI2000-v7.0-G-01_alaska.zip"],
                      landing="https://nsidc.org/data/nsidc-0770/versions/7 (NASA Earthdata Login required; ~/.netrc, see _opener)",
                      note="RGI 7.0 region 01 (Alaska) -- the St Elias / Yukon side"),
    "rgi70_r02": dict(dir=INPUT / "glaciers", glob="*02_western_canada_usa*/*.shp", required=True,
                      urls=["https://daacdata.apps.nsidc.org/pub/DATASETS/nsidc0770_rgi_v7/regional_files/RGI2000-v7.0-G/RGI2000-v7.0-G-02_western_canada_usa.zip"],
                      landing="https://nsidc.org/data/nsidc-0770/versions/7 (NASA Earthdata Login required; ~/.netrc, see _opener)",
                      note="RGI 7.0 region 02 (Western Canada and USA)"),
    "hydrolakes": dict(dir=INPUT / "hydrosheds", glob="**/HydroLAKES_polys_v10*.shp", required=True,
                       urls=["https://data.hydrosheds.org/file/hydrolakes/HydroLAKES_polys_v10_shp.zip"],
                       landing="https://www.hydrosheds.org/products/hydrolakes",
                       note="HydroLAKES v1.0 polygons, global (~1.5 GB zip; the loader reads only the Y2Y bbox)"),
    "hydrorivers_na": dict(dir=INPUT / "hydrosheds", glob="**/HydroRIVERS_v10_na*.shp", required=True,
                           urls=["https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_na_shp.zip"],
                           landing="https://www.hydrosheds.org/products/hydrorivers",
                           note="HydroRIVERS v1.0, North America (~200 MB zip)"),
    "gmted2010": dict(dir=INPUT / "dem_gmted", glob="*.tif", required=False,
                      urls=[], landing="https://www.usgs.gov/coastal-changes-and-impacts/gmted2010  (7.5 arc-second mean tiles)",
                      note="OPTIONAL -- the source's DEM; without it the 300 m Copernicus-derived DEM is used"),
}


def present(key):
    d = DATASETS[key]
    return bool(list(d["dir"].glob(d["glob"]))) if d["dir"].exists() else False


def check(verbose=True):
    status = {}
    if verbose:
        print(f"{'dataset':16s} {'present':8s} location")
    for k, d in DATASETS.items():
        ok = present(k)
        status[k] = ok or not d["required"]
        if verbose:
            print(f"{k:16s} {'yes' if ok else ('NO' if d['required'] else 'no (optional)'):8s} {d['dir'].relative_to(ROOT)}  -- {d['note']}")
            if not ok and d["required"]:
                print(f"{'':16s} download: {d['landing']}")
    return status


USER_AGENT = "Mozilla/5.0 (Macintosh) y2y-spatial-optimization/acquire"   # data.hydrosheds.org returns 403 to Python's default agent
EARTHDATA_HOST = "urs.earthdata.nasa.gov"


def _opener(url):
    """urllib opener: a browser-style User-Agent everywhere; for NSIDC (RGI 7.0) the NASA Earthdata Login flow --
    credentials from ~/.netrc (`machine urs.earthdata.nasa.gov login <user> password <password>`, chmod 600),
    HTTP basic auth against URS plus a cookie jar for the redirect dance. Never paste credentials into a notebook."""
    import http.cookiejar
    import netrc
    handlers = [urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())]
    if "nsidc.org" in url or EARTHDATA_HOST in url:
        try:
            auth = netrc.netrc().authenticators(EARTHDATA_HOST)
        except (FileNotFoundError, netrc.NetrcParseError):
            auth = None
        if not auth:
            raise PermissionError(f"NSIDC needs a NASA Earthdata Login: add to ~/.netrc the line "
                                  f"'machine {EARTHDATA_HOST} login <user> password <password>' (chmod 600) -- free account at "
                                  f"https://{EARTHDATA_HOST}/users/new")
        pm = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        pm.add_password(None, f"https://{EARTHDATA_HOST}", auth[0], auth[2])
        handlers.append(urllib.request.HTTPBasicAuthHandler(pm))
    op = urllib.request.build_opener(*handlers)
    op.addheaders = [("User-Agent", USER_AGENT)]
    return op


def _download(url, dst, chunk=1 << 20):
    if "nsidc.org" in url:
        # NASA Earthdata's redirect chain (daacdata -> urs /oauth/authorize -> back) trips urllib's auth handler; curl's --netrc
        # flow completes it (verified 2026-09-28). Same ~/.netrc line, cookies kept in a temp jar beside the file.
        import subprocess
        jar = pathlib.Path(str(dst) + ".cookies")
        cmd = ["curl", "-L", "--netrc", "-c", str(jar), "-b", str(jar), "-A", USER_AGENT, "--fail", "--progress-bar",
               "--retry", "3", "--max-time", "3600", "-o", str(dst), url]
        print("    (curl, Earthdata login from ~/.netrc)")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        jar.unlink(missing_ok=True)
        if proc.returncode != 0:
            raise RuntimeError(f"curl failed ({proc.returncode}): {proc.stderr.strip()[-300:]}")
        return
    op = _opener(url)
    with op.open(url, timeout=120) as r, open(dst, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0); done = 0
        while True:
            b = r.read(chunk)
            if not b:
                break
            f.write(b); done += len(b)
            if total:
                sys.stdout.write(f"\r    {done/1e6:8.0f} / {total/1e6:.0f} MB"); sys.stdout.flush()
    print()


def fetch(keys=None, keep_zip=False):
    """Download + unzip the missing datasets that have direct URLs; prints the manual step when
    a URL fails (RGI on NSIDC needs an Earthdata login in some setups)."""
    keys = keys or [k for k, d in DATASETS.items() if d["required"]]
    for k in keys:
        d = DATASETS[k]
        if present(k):
            print(f"{k}: already present"); continue
        if not d["urls"]:
            print(f"{k}: no direct URL -- download manually from {d['landing']} into {d['dir']}"); continue
        d["dir"].mkdir(parents=True, exist_ok=True)
        ok = False
        for url in d["urls"]:
            zpath = d["dir"] / url.rsplit("/", 1)[-1]
            try:
                print(f"{k}: fetching {url}")
                _download(url, zpath)
                with zipfile.ZipFile(zpath) as z:
                    z.extractall(d["dir"] / zpath.stem)
                if not keep_zip:
                    zpath.unlink()
                ok = present(k)
                if ok:
                    print(f"{k}: OK -> {d['dir'] / zpath.stem}"); break
            except Exception as ex:               # noqa: BLE001 -- report and try the next mirror
                print(f"    failed: {ex}")
                if zpath.exists():
                    zpath.unlink()
        if not ok:
            print(f"{k}: could not fetch automatically -- download from {d['landing']} and unzip into {d['dir']}")
    return check(verbose=False)


if __name__ == "__main__":
    check()
