"""Download the OPEN tenure / AOI / PA-check layers for the Alberta prioritization (data/README.md).

Run from the repo root:  .venv/bin/python analyses/alberta_prioritization/data/acquire.py
Idempotent: existing files are skipped; every file's sha256 + source URL + UTC timestamp lands in
provenance.json (spec §10: "acquired layers, provenance sha256s"). Layers stay in their native CRS
here (EPSG:3400 / 30 m GeoTIFF); 03_ab0a_tenure_aoi reprojects onto the AB grid.

Blocked item (see README row 5): province-wide dispositions are not open data. If a licensed copy
is available, place it at tenure/dids_dispositions.gpkg and the tenure notebook will pick it up.
"""
import hashlib
import json
import pathlib
import sys
import urllib.request
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
PROV = HERE / "provenance.json"

ZIPS = [
    # (subdir, filename, url)
    ("tenure", "GrasslandVegetationInventory.zip",
     "https://extranet.gov.ab.ca/srd/geodiscover/srd_pub/biota/Vegetation/GrasslandVegetationInventory.zip"),
    ("tenure", "aci_2024_ab_v2.zip",
     "https://agriculture.canada.ca/atlas/data_donnees/annualCropInventory/data_donnees/tif/2024/aci_2024_ab_v2.zip"),
    ("tenure", "CrownlandReservations_SHP.zip",
     "https://extranet.gov.ab.ca/srd/geodiscover/srd_pub/boundaries/CrownlandReservations_SHP.zip"),
    ("aoi", "US_SRP_Zones.zip",
     "https://extranet.gov.ab.ca/srd/geodiscover/srd_pub/environment/SRP/US_SRP_Zones.zip"),
    ("aoi", "US_SRP_ConservationAreasParks.zip",
     "https://extranet.gov.ab.ca/srd/geodiscover/srd_pub/environment/SRP/US_SRP_ConservationAreasParks.zip"),
    ("aoi", "US_SRP_PlanningBoundary.zip",
     "https://extranet.gov.ab.ca/srd/geodiscover/srd_pub/environment/SRP/US_SRP_PlanningBoundary.zip"),
]

REST = [
    # (subdir, filename, layer url)  -- ArcGIS FeatureServer/MapServer layers, paged as GeoJSON
    ("tenure", "green_white_area.gpkg",
     "https://geospatial.alberta.ca/titan/rest/services/boundary/asrd_administrative_area/MapServer/1"),
    ("pa", "pluz.gpkg",
     "https://geospatial.alberta.ca/titan/rest/services/base/land_use_management_10tm_nad83_aep/MapServer/1"),
]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_prov():
    return json.loads(PROV.read_text()) if PROV.exists() else {}


def record(prov, rel, url, path, note=""):
    prov[rel] = dict(url=url, sha256=sha256(path), bytes=path.stat().st_size,
                     fetched_utc=datetime.now(timezone.utc).isoformat(), note=note)
    PROV.write_text(json.dumps(prov, indent=1))


def fetch_zip(prov, subdir, name, url):
    out = HERE / subdir / name
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        print(f"  exists   {subdir}/{name}")
        return
    print(f"  download {subdir}/{name} <- {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "y2y-alberta-prioritization/1.0"})
    with urllib.request.urlopen(req, timeout=600) as r, open(out, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    record(prov, f"{subdir}/{name}", url, out)
    print(f"           {out.stat().st_size/1e6:.1f} MB, sha256 {prov[f'{subdir}/{name}']['sha256'][:16]}...")


def fetch_rest(prov, subdir, name, layer_url, page=1000):
    """Page an ArcGIS REST layer as GeoJSON (max 1,000 records/request) into a GeoPackage."""
    import geopandas as gpd

    out = HERE / subdir / name
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        print(f"  exists   {subdir}/{name}")
        return
    print(f"  REST     {subdir}/{name} <- {layer_url}")
    feats, offset = [], 0
    while True:
        q = (f"{layer_url}/query?where=1%3D1&outFields=*&returnGeometry=true&f=geojson"
             f"&resultOffset={offset}&resultRecordCount={page}")
        req = urllib.request.Request(q, headers={"User-Agent": "y2y-alberta-prioritization/1.0"})
        with urllib.request.urlopen(req, timeout=300) as r:
            js = json.loads(r.read().decode())
        if "error" in js:
            raise RuntimeError(f"REST error from {layer_url}: {js['error']}")
        got = js.get("features", [])
        feats.extend(got)
        more = js.get("properties", {}).get("exceededTransferLimit") or js.get("exceededTransferLimit")
        if not got or not more:
            break
        offset += len(got)
    if not feats:
        raise RuntimeError(f"no features returned from {layer_url}")
    # ArcGIS geojson output is WGS84 (outSR defaults to 4326 for f=geojson); reproject downstream.
    gdf = gpd.GeoDataFrame.from_features(feats, crs="EPSG:4326")
    gdf.to_file(out, driver="GPKG")
    record(prov, f"{subdir}/{name}", layer_url, out, note=f"{len(gdf)} features, paged REST -> GeoJSON (EPSG:4326)")
    print(f"           {len(gdf)} features, sha256 {prov[f'{subdir}/{name}']['sha256'][:16]}...")


def main():
    prov = load_prov()
    print("open zip downloads:")
    for subdir, name, url in ZIPS:
        fetch_zip(prov, subdir, name, url)
    print("REST layers:")
    for subdir, name, url in REST:
        fetch_rest(prov, subdir, name, url)
    dids = HERE / "tenure" / "dids_dispositions.gpkg"
    print(f"\ndispositions (README row 5): {'FOUND ' + str(dids.name) if dids.exists() else 'NOT PRESENT -- restricted data; decision pending (see README)'}")
    if dids.exists() and "tenure/dids_dispositions.gpkg" not in prov:
        record(prov, "tenure/dids_dispositions.gpkg", "manual (licensed copy)", dids)
    cp = HERE / "pa" / "cpcad.zip"
    print(f"CPCAD: {'FOUND' if cp.exists() else 'not present (manual; completeness check only)'}")
    if cp.exists() and "pa/cpcad.zip" not in prov:
        record(prov, "pa/cpcad.zip", "manual (ECCC Databases directory)", cp)
    print(f"\nprovenance -> {PROV.relative_to(HERE.parent)} ({len(load_prov())} entries)")


if __name__ == "__main__":
    sys.exit(main())
