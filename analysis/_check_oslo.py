import geopandas as gpd
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
shps = list((REPO / "data" / "raw" / "territorial" / "osloagreement").rglob("*.shp"))
print("shapefiles found:")
for s in shps:
    print(f"  {s.relative_to(REPO)}")

for shp in shps:
    print(f"\n=== {shp.name} ===")
    df = gpd.read_file(shp)
    print("rows:", len(df), "  cols:", df.columns.tolist())
    for col in df.columns:
        if col.lower() in ("class", "type", "name", "area", "category"):
            print(f"\nvalue counts of {col!r}:")
            print(df[col].value_counts(dropna=False).to_string())
