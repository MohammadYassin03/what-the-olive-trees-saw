"""Inspect the derived Area B polygon to see if it's a real area or thin slivers."""
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from pathlib import Path
import geopandas as gpd

REPO = Path(__file__).resolve().parents[1]
gpkg = REPO / "data" / "processed" / "territorial.gpkg"

oslo = gpd.read_file(gpkg, layer="oslo_areas").to_crs(2039)  # metric CRS
print("Per-class areas (km^2) and bounds:")
for cls, sub in oslo.groupby("class"):
    area_km2 = sub.geometry.area.sum() / 1e6
    minx, miny, maxx, maxy = sub.total_bounds
    width = (maxx - minx) / 1000
    height = (maxy - miny) / 1000
    print(f"  {cls:40s}  area={area_km2:7.1f} km^2   bbox={width:.1f} x {height:.1f} km")

# West Bank total
all_geom = oslo.geometry.union_all()
print(f"\nWest Bank (union of all classes) area: {all_geom.area/1e6:.1f} km^2")
expected_total = 5655  # roughly the West Bank area
print(f"  expected ~{expected_total} km^2")

# What fraction is Area B
b_area = oslo[oslo["class"] == "B"].geometry.area.sum() / 1e6
print(f"\nArea B share of total: {b_area / (all_geom.area/1e6) * 100:.1f}%")
print(f"  rubric expectation: ~18-22% of West Bank")
