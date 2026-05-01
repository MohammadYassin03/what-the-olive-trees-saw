import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

from pathlib import Path
import geopandas as gpd
import pyogrio

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

gpkgs = list((RAW / "osm").rglob("*.gpkg"))
print("GeoPackages found:", [p.name for p in gpkgs])
if not gpkgs:
    sys.exit(0)

gpkg = gpkgs[0]
print(f"\nInspecting: {gpkg}")
layers = [n for n, _ in pyogrio.list_layers(gpkg)]
print(f"Layers ({len(layers)}):", layers)

# For each layer, print a few features — look for anything landuse/orchard related
for layer in layers:
    try:
        # Peek at a small slice
        gdf = gpd.read_file(gpkg, layer=layer, rows=5)
        print(f"\n-- {layer} --  (schema peek, 5 rows)")
        print("  columns:", list(gdf.columns)[:15])
        if "fclass" in gdf.columns:
            # Full scan for unique fclass values (might be slow, but we only care about distribution)
            full = gpd.read_file(gpkg, layer=layer, ignore_geometry=True)
            uniq = full["fclass"].value_counts().head(20)
            print("  fclass top:", uniq.to_dict())
    except Exception as e:
        print(f"  [warn] {layer}: {e}")
