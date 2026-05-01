"""
Pulls every source we can fetch programmatically and leaves clear instructions
for the ones that need a manual download.

All URLs below were verified at the time of writing. If any 404s, re-check
the source page (linked in each section) and update the URL in this file.

Run from the repo root:
    conda activate olives
    python analysis/01_acquire.py
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import requests

# Windows consoles default to cp1252 , force stdout to UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW = REPO_ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (DSAN-5200-OliveTrees-Research; academic; Georgetown)"
}


def _fetch(url: str, dest: Path, *, label: str, force: bool = False) -> bool:
    if dest.exists() and not force:
        print(f"  [skip] {label} already at {dest.relative_to(REPO_ROOT)}")
        return True
    print(f"  [get ] {label}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=90, allow_redirects=True)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"  [FAIL] {label}: {e}")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    size_kb = len(r.content) / 1024
    print(f"  [ok  ] {label} - {size_kb:,.0f} KB -> {dest.relative_to(REPO_ROOT)}")
    return True


def _unzip(archive: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        z.extractall(out_dir)
    print(f"  [unzip] {archive.name} -> {out_dir.relative_to(REPO_ROOT)}/")


# 1. ACLED , Palestine conflict events (aggregated monthly)
# HDX dataset: palestine-acled-conflict-data
# These are month-level aggregates (counts by type). Good for the temporal
# backbone. Note: event-level ACLED with coordinates requires sign-up on
# acleddata.com , we use the HDX aggregates here for reproducibility.

ACLED_FILES = {
    "palestine_political_violence.xlsx":
        "https://data.humdata.org/dataset/a01fb41d-b89c-4de0-abbd-b5046695d448/resource/8f383970-b41a-414a-a70e-fd9d2b7b8ba1/download/palestine_hrp_political_violence_events_and_fatalities_by_month-year_as-of-22apr2026.xlsx",
    "palestine_civilian_targeting.xlsx":
        "https://data.humdata.org/dataset/a01fb41d-b89c-4de0-abbd-b5046695d448/resource/534ff0b1-3f31-4d46-a6a1-5b611840953d/download/palestine_hrp_civilian_targeting_events_and_fatalities_by_month-year_as-of-22apr2026.xlsx",
    "palestine_demonstrations.xlsx":
        "https://data.humdata.org/dataset/a01fb41d-b89c-4de0-abbd-b5046695d448/resource/3dbd57de-01b9-49d2-89fc-5c5d599c5107/download/palestine_hrp_demonstration_events_by_month-year_as-of-22apr2026.xlsx",
}

def acquire_acled() -> None:
    print("[1/5] ACLED Palestine (HDX monthly aggregates)")
    for name, url in ACLED_FILES.items():
        _fetch(url, RAW / "acled" / name, label=name)


# 2. Administrative boundaries (OCHA COD-AB-PSE)
# HDX dataset: cod-ab-pse , admin levels 0/1/2 (country / governorate / locality)

ADMIN_URL = ("https://data.humdata.org/dataset/2caf8373-816f-458c-9913-71bddb9cab7c/"
             "resource/ebf1cc7b-45e0-43bb-bec5-2464cd2d26fc/download/pse_admin_boundaries.shp.zip")

def acquire_admin() -> None:
    print("[2/5] OCHA admin boundaries (shapefile)")
    dest = RAW / "boundaries" / "pse_admin.shp.zip"
    if _fetch(ADMIN_URL, dest, label="pse_admin_boundaries.shp.zip"):
        try:
            _unzip(dest, dest.parent)
        except Exception as e:
            print(f"  [warn] unzip failed: {e}")


# 3. OpenStreetMap extract (Geofabrik)
# Geofabrik publishes Israel+Palestine as one region. We use the free
# GeoPackage (ready-to-read, no .pbf parsing required).

OSM_URL = "https://download.geofabrik.de/asia/israel-and-palestine-latest-free.gpkg.zip"

def acquire_osm() -> None:
    print("[3/5] OSM extract (Geofabrik, Israel+Palestine GeoPackage)")
    dest = RAW / "osm" / "israel_and_palestine.gpkg.zip"
    if _fetch(OSM_URL, dest, label="israel-and-palestine-latest-free.gpkg.zip"):
        try:
            _unzip(dest, dest.parent)
        except Exception as e:
            print(f"  [warn] unzip failed: {e}")


# 4. UN OCHA oPt , Protection of Civilians & Settler-Violence database
# Not available as a stable programmatic download. Published as interactive
# dashboards at:
#   - https://www.ochaopt.org/data/casualties
#   - https://www.ochaopt.org/data/settler-violence
# Both pages have a "Download the data" link (CSV). The file name rotates
# with each quarterly update, so we don't hard-code the URL.

def acquire_ocha_manual() -> None:
    print("[4/5] OCHA oPt Protection of Civilians (MANUAL)")
    dest_dir = RAW / "ocha"
    dest_dir.mkdir(parents=True, exist_ok=True)
    print("  Go to each of these pages and click 'Download the data':")
    print("    - https://www.ochaopt.org/data/casualties")
    print("    - https://www.ochaopt.org/data/settler-violence")
    print(f"  Save the CSVs to: {dest_dir.relative_to(REPO_ROOT)}/")
    print("  Suggested filenames: ocha_casualties.csv, ocha_settler_violence.csv")


# 5. PCBS , olive oil production & cultivated area
# Palestinian Central Bureau of Statistics , browse the agriculture section.
# No stable direct-download URLs; the XLSX are linked from year-by-year pages.

def acquire_pcbs_manual() -> None:
    print("[5/5] PCBS olive statistics (MANUAL)")
    dest_dir = RAW / "pcbs"
    dest_dir.mkdir(parents=True, exist_ok=True)
    print("  Go to: https://www.pcbs.gov.ps/site/lang__en/881/default.aspx")
    print("  Download 'Main Indicators of Olive Trees' and 'Olive Oil Production'")
    print(f"  Save XLSX files to: {dest_dir.relative_to(REPO_ROOT)}/")


# Main

def main() -> None:
    print(f"Acquiring raw data into: {RAW.relative_to(REPO_ROOT)}/")
    acquire_acled()
    acquire_admin()
    acquire_osm()
    acquire_ocha_manual()
    acquire_pcbs_manual()
    print()
    print("Done. Manual-download steps listed above.")
    print("Next: python analysis/02_clean.py")
if __name__ == "__main__":
    main()
