"""
Reads data/raw/ and writes tidy CSVs and a clipped GeoPackage to
data/processed/.

Outputs:
  data/processed/acled_monthly_westbank.csv   long-format: gov x year x month x event_type x (events, fatalities)
  data/processed/orchards_westbank.gpkg       clipped OSM orchard polygons (West Bank only)
  data/processed/orchards_by_governorate.csv  gov -> total orchard area (dunums, hectares)
  data/processed/places_westbank.gpkg         clipped OSM villages/towns/hamlets
  data/processed/governorates.gpkg            West Bank governorate polygons, ready for mapping

Run:
    conda run -n olives python analysis/02_clean.py
"""

from __future__ import annotations

import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

from pathlib import Path

import pandas as pd
import geopandas as gpd

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW = REPO_ROOT / "data" / "raw"
PROC = REPO_ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)


# 1. ACLED , stack the three event-type files into one long-format CSV

ACLED_FILES = {
    "political_violence": RAW / "acled" / "palestine_political_violence.xlsx",
    "civilian_targeting": RAW / "acled" / "palestine_civilian_targeting.xlsx",
    "demonstrations":     RAW / "acled" / "palestine_demonstrations.xlsx",
}
ACLED_EVENTS_CSV = RAW / "acled" / "palestine_events.csv"
SETTLER_POP_CSV  = RAW / "settlements" / "settler_population_annual.csv"


def _classify_perpetrator(actor1: str) -> str:
    """Bucket actor1 into a small, defensible set of perpetrator labels."""
    if not isinstance(actor1, str) or not actor1.strip():
        return "Unknown"
    a = actor1.lower()
    if "settler" in a or "settlement emergency" in a or "private security forces (israel)" in a:
        return "Settlers"
    if "military forces of israel" in a or "police forces of israel" in a:
        return "Israeli state forces"
    if "(israel)" in a:
        return "Other Israeli actor"
    if "(palestine)" in a:
        return "Palestinian actor"
    return "Other"


# Damage-type keyword scan over the ACLED notes field
DAMAGE_KEYWORDS = {
    "olive_or_tree": ["olive", "tree", "grove", "uproot"],
    "livestock":     ["sheep", "goat", "livestock", "cattle"],
    "home_property": ["house", "home", "property", "building"],
    "vehicle":       ["vehicle", "car", "truck"],
    "mosque_school": ["mosque", "school", "church"],
    "crop_field":    ["crop", "field", "farm", "harvest"],
    "burn":          ["burn", "torch", "set fire"],
}


def _tag_damage(notes: str) -> dict:
    if not isinstance(notes, str): return {k: False for k in DAMAGE_KEYWORDS}
    n = notes.lower()
    return {k: any(w in n for w in words) for k, words in DAMAGE_KEYWORDS.items()}


def clean_acled_events() -> None:
    """Process event-level ACLED CSV into a tidy parquet, with perpetrator
    bucketing and damage-keyword tags."""
    if not ACLED_EVENTS_CSV.exists():
        print(f"[events] [skip] {ACLED_EVENTS_CSV.name} not found , Layer 1 disabled")
        return
    print("[events] reading event-level ACLED CSV ...")
    df = pd.read_csv(ACLED_EVENTS_CSV, low_memory=False)
    df = df[df["admin1"] == "West Bank"].copy()
    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    df["year"] = df["event_date"].dt.year
    df["month"] = df["event_date"].dt.month
    df["is_civilian_targeting"] = df["civilian_targeting"].fillna("").str.contains(
        "Civilian targeting", case=False)
    df["targets_palestinian_civilians"] = df["actor2"].fillna("").str.contains(
        "Civilians (Palestine)", case=False, regex=False)

    df["perpetrator"] = df["actor1"].apply(_classify_perpetrator)
    tags = pd.DataFrame(df["notes"].apply(_tag_damage).tolist(), index=df.index)
    df = pd.concat([df, tags], axis=1)

    keep = ["event_id_cnty","event_date","year","month","disorder_type","event_type",
            "sub_event_type","actor1","actor2","perpetrator","is_civilian_targeting",
            "targets_palestinian_civilians","admin1","admin2","location",
            "latitude","longitude","fatalities","notes"] + list(DAMAGE_KEYWORDS)
    out = PROC / "acled_events_westbank.parquet"
    df[keep].to_parquet(out, index=False)
    print(f"  -> {out.relative_to(REPO_ROOT)}  ({len(df):,} events, "
          f"{df['is_civilian_targeting'].sum():,} CT, "
          f"{df['targets_palestinian_civilians'].sum():,} target Pal. civilians)")
    print(f"  perpetrator counts (events targeting Palestinian civilians):")
    print(df[df["targets_palestinian_civilians"]]["perpetrator"]
          .value_counts().to_string())

MONTH_TO_INT = {m: i for i, m in enumerate(
    ["January","February","March","April","May","June",
     "July","August","September","October","November","December"], start=1)}


def clean_acled() -> pd.DataFrame:
    print("[acled] building unified monthly panel ...")
    frames = []
    for event_type, path in ACLED_FILES.items():
        if not path.exists():
            print(f"  [skip] {path.name} not found")
            continue
        df = pd.read_excel(path, sheet_name="Data")
        df = df.rename(columns={
            "Admin1": "admin1",
            "Admin2": "governorate",
            "Admin1 Pcode": "admin1_pcode",
            "Admin2 Pcode": "gov_pcode",
            "Month": "month_name",
            "Year":  "year",
            "Events": "events",
            "Fatalities": "fatalities",
        })
        # Demonstrations file has no fatalities column
        if "fatalities" not in df.columns:
            df["fatalities"] = 0
        df["month"] = df["month_name"].map(MONTH_TO_INT)
        df["event_type"] = event_type
        df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
        frames.append(df[[
            "date", "year", "month", "month_name", "admin1", "governorate",
            "gov_pcode", "event_type", "events", "fatalities",
        ]])

    full = pd.concat(frames, ignore_index=True)
    # West Bank only , ACLED tags Gaza as admin1=="Gaza Strip"
    wb = full[full["admin1"] == "West Bank"].copy()
    out = PROC / "acled_monthly_westbank.csv"
    wb.to_csv(out, index=False)
    print(f"  -> {out.relative_to(REPO_ROOT)}  ({len(wb):,} rows, "
          f"{wb['year'].min()}–{wb['year'].max()}, "
          f"{wb['governorate'].nunique()} governorates)")
    return wb


# 2. Governorate polygons (West Bank subset)

def load_governorates() -> gpd.GeoDataFrame:
    print("[admin] loading governorate polygons ...")
    shp_candidates = list((RAW / "boundaries").rglob("*adm2*.shp")) \
                   + list((RAW / "boundaries").rglob("*adm_2*.shp")) \
                   + list((RAW / "boundaries").rglob("*ADM2*.shp")) \
                   + list((RAW / "boundaries").rglob("*admin2*.shp")) \
                   + list((RAW / "boundaries").rglob("*level2*.shp"))
    if not shp_candidates:
        # Fall back to the largest .shp , usually the most detailed level
        all_shp = list((RAW / "boundaries").rglob("*.shp"))
        all_shp.sort(key=lambda p: p.stat().st_size, reverse=True)
        shp_candidates = all_shp
    print("  candidate shapefiles:", [p.name for p in shp_candidates[:5]])

    for shp in shp_candidates:
        gdf = gpd.read_file(shp)
        cols_lower = [c.lower() for c in gdf.columns]
        # Governorate level should have ~11 West Bank polygons plus Gaza ones
        if len(gdf) >= 11 and len(gdf) < 50:
            print(f"  using: {shp.name}  ({len(gdf)} features, cols={list(gdf.columns)})")
            break
    else:
        shp = shp_candidates[0]
        gdf = gpd.read_file(shp)
        print(f"  fallback: {shp.name}  ({len(gdf)} features)")

    return gdf


def clip_west_bank(govs: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep West Bank governorates. Works across common naming conventions."""
    # Try various columns , CODs typically have "ADM1_EN", "admin1Name_en", etc.
    name_col = next((c for c in govs.columns if c.lower() in
                     ("adm1_en","admin1name_en","admin1name","adm1_name","region","admin1")), None)
    if name_col:
        wb = govs[govs[name_col].astype(str).str.contains("West Bank", case=False, na=False)].copy()
        if len(wb) == 0:
            # Sometimes the West Bank is named "oPt West Bank" or similar
            wb = govs.copy()
    else:
        # No admin1 column , just keep all; downstream join by name will filter
        wb = govs.copy()

    # Normalize CRS to WGS84 for simplicity
    if wb.crs is None:
        wb = wb.set_crs(4326)
    wb = wb.to_crs(4326)
    return wb


# 3. OSM orchards , clip to West Bank, compute area by governorate

def clean_orchards(governorates: gpd.GeoDataFrame) -> None:
    print("[osm] extracting orchards ...")
    gpkgs = list((RAW / "osm").rglob("*.gpkg"))
    if not gpkgs:
        print("  [skip] no OSM GeoPackage found")
        return
    gpkg = gpkgs[0]

    landuse = gpd.read_file(gpkg, layer="gis_osm_landuse_a_free")
    print(f"  landuse loaded: {len(landuse):,} polygons (all land uses)")
    orchards = landuse[landuse["fclass"] == "orchard"].copy()
    print(f"  orchards: {len(orchards):,} polygons")

    orchards = orchards.to_crs(4326)
    gov_wb = governorates.to_crs(4326)

    # Clip to the union of West Bank governorate polygons
    wb_union = gov_wb.unary_union
    orchards_wb = orchards[orchards.geometry.intersects(wb_union)].copy()
    print(f"  orchards inside West Bank: {len(orchards_wb):,}")

    # Compute area in a projected CRS (ITM is appropriate for this region)
    orchards_itm = orchards_wb.to_crs(2039)
    orchards_wb["area_m2"] = orchards_itm.geometry.area
    orchards_wb["area_dunums"] = orchards_wb["area_m2"] / 1000   # 1 dunum = 1000 m²
    orchards_wb["area_ha"]     = orchards_wb["area_m2"] / 10_000

    # Spatial join to governorates
    gov_for_join = gov_wb[[c for c in gov_wb.columns if c != "geometry"] + ["geometry"]]
    joined = gpd.sjoin(orchards_wb, gov_for_join, how="left", predicate="intersects")

    # Find the governorate-name column (heuristic)
    name_col = next((c for c in gov_for_join.columns
                     if c.lower() in ("adm2_en","admin2name_en","admin2name","adm2_name","name")), None)
    if name_col is None:
        # Fall back to any string column with roughly governorate-count unique values
        cand = [c for c in gov_for_join.columns
                if gov_for_join[c].dtype == object and 5 <= gov_for_join[c].nunique() <= 30]
        name_col = cand[0] if cand else None
    print(f"  governorate-name column: {name_col}")

    if name_col:
        by_gov = (joined.groupby(name_col, dropna=True)
                  .agg(orchard_count=("osm_id","nunique"),
                       area_dunums=("area_dunums","sum"),
                       area_ha=("area_ha","sum"))
                  .sort_values("area_dunums", ascending=False)
                  .reset_index()
                  .rename(columns={name_col: "governorate"}))
        out_csv = PROC / "orchards_by_governorate.csv"
        by_gov.to_csv(out_csv, index=False)
        print(f"  -> {out_csv.relative_to(REPO_ROOT)}  ({len(by_gov)} rows)")
        print(by_gov.head(15).to_string(index=False))

    # Save the clipped orchards as a GeoPackage for mapping
    out_gpkg = PROC / "orchards_westbank.gpkg"
    orchards_wb[["osm_id","name","area_dunums","area_ha","geometry"]].to_file(
        out_gpkg, layer="orchards", driver="GPKG")
    print(f"  -> {out_gpkg.relative_to(REPO_ROOT)}  ({len(orchards_wb):,} polygons)")


# Main

def clean_settlements(governorates: gpd.GeoDataFrame) -> None:
    """Peace Now built-up settlement polygons. Reproject, spatial-join to governorate."""
    print("[settlements] processing Peace Now layer ...")
    shp_paths = list((RAW / "settlements").rglob("*.shp"))
    if not shp_paths:
        print("  [skip] no settlement shapefile found")
        return
    s = gpd.read_file(shp_paths[0]).to_crs(4326)

    # Compute area in projected CRS (ITM, EPSG:2039) BEFORE sjoin
    s_itm = s.to_crs(2039)
    s["area_m2"] = s_itm.geometry.area
    s["area_dunums"] = s["area_m2"] / 1000

    # Save polygons
    out_gpkg = PROC / "settlements.gpkg"
    keep = [c for c in s.columns if c in ("Name", "GIS_ID", "area_m2", "area_dunums", "geometry")]
    s[keep].to_file(out_gpkg, layer="settlements", driver="GPKG")
    print(f"  -> {out_gpkg.relative_to(REPO_ROOT)}  ({len(s)} polygons)")

    # Spatial-join to governorates to attach a governorate name
    gov_wb = governorates.to_crs(4326)
    name_col = next((c for c in gov_wb.columns
                     if c.lower() in ("adm2_en","admin2name_en","admin2name","adm2_name","name")), None)

    if name_col:
        joined = gpd.sjoin(
            s, gov_wb[[name_col, "geometry"]],
            how="left", predicate="intersects",
        )
        # If a settlement straddles a boundary, keep the first match
        joined = joined.drop_duplicates(subset=["Name"], keep="first")
        by_gov = (joined.groupby(name_col, dropna=True)
                  .agg(settlement_count=("Name", "nunique"),
                       settlement_area_dunums=("area_dunums", "sum"))
                  .sort_values("settlement_count", ascending=False)
                  .reset_index()
                  .rename(columns={name_col: "governorate"}))
        out_csv = PROC / "settlements_by_governorate.csv"
        by_gov.to_csv(out_csv, index=False)
        print(f"  -> {out_csv.relative_to(REPO_ROOT)}  ({len(by_gov)} rows)")
        print(by_gov.head(15).to_string(index=False))


def clean_territorial(wb_clip: gpd.GeoDataFrame) -> None:
    """Areas A/B/C (Oslo Agreement) and the Separation Barrier (OCHA via HDX).

    Both are written to data/processed/territorial.gpkg as separate layers,
    in EPSG:4326 so the Folium territorial map can consume them directly.

    Note on Area B: the OCHA "Oslo Agreement" shapefile encodes A, C, H1, H2,
    Nature Reserve, East Jerusalem, and No Man's Land explicitly, but does
    *not* encode Area B as a polygon. Area B is the residual of the West
    Bank that is none of those classes, so we derive it here by subtracting
    the explicit polygons from the West Bank outline (the unioned governorate
    boundaries) and writing the result back into the same `oslo_areas` layer
    with class = "B".
    """
    print("[territorial] processing Oslo A/B/C and Separation Barrier ...")
    out_gpkg = PROC / "territorial.gpkg"
    out_gpkg.parent.mkdir(parents=True, exist_ok=True)

    oslo_shps = list((RAW / "territorial" / "osloagreement").rglob("*.shp"))
    if oslo_shps:
        oslo = gpd.read_file(oslo_shps[0]).to_crs(4326)
        oslo = oslo[["CLASS", "geometry"]].rename(columns={"CLASS": "class"})

        # Derive Area B as: West Bank outline minus everything explicitly classed.
        wb_outline = wb_clip.to_crs(4326).geometry.union_all()
        explicit_union = oslo.geometry.union_all()
        b_geom = wb_outline.difference(explicit_union)
        # The geometric difference can leave tiny slivers along boundaries; we
        # drop anything below 0.0001 deg² (~1 km² at this latitude) so the
        # resulting Area B layer is a clean set of polygons rather than a
        # cloud of fragments.
        if b_geom.geom_type == "MultiPolygon":
            keep = [p for p in b_geom.geoms if p.area > 1e-4]
            from shapely.geometry import MultiPolygon
            b_geom = MultiPolygon(keep) if keep else b_geom
        b_row = gpd.GeoDataFrame({"class": ["B"], "geometry": [b_geom]}, crs=4326)
        oslo = pd.concat([oslo, b_row], ignore_index=True)

        oslo.to_file(out_gpkg, layer="oslo_areas", driver="GPKG")
        counts = oslo["class"].value_counts().to_dict()
        print(f"  -> {out_gpkg.relative_to(REPO_ROOT)}::oslo_areas  ({len(oslo)} polygons)")
        print(f"     class counts: {counts}")
    else:
        print("  [skip] osloagreement shapefile not found")

    # Separation Barrier
    barrier_shps = list((RAW / "territorial" / "barrier_jan2018").rglob("*.shp"))
    if barrier_shps:
        barrier = gpd.read_file(barrier_shps[0]).to_crs(4326)
        # Status: Constructed, Under Construction, Projected
        # Type:   Concrete, Fence, NA
        barrier = barrier[["Status", "Type", "geometry"]].rename(
            columns={"Status": "status", "Type": "barrier_type"}
        )
        barrier.to_file(out_gpkg, layer="barrier", driver="GPKG")
        print(f"  -> {out_gpkg.relative_to(REPO_ROOT)}::barrier  ({len(barrier)} segments)")
    else:
        print("  [skip] barrier shapefile not found")


def clean_settler_population() -> None:
    """Curated annual settler-population series (West Bank + East Jerusalem).

    Reads the curated CSV at data/raw/settlements/settler_population_annual.csv
    and writes a tidy version to data/processed/. Adds derived columns:
    total (excl. East Jerusalem), total_with_jerusalem, and growth_since_1972.
    """
    print("[settler-pop] processing curated annual series ...")
    if not SETTLER_POP_CSV.exists():
        print(f"  [skip] not found: {SETTLER_POP_CSV.relative_to(REPO_ROOT)}")
        return
    df = pd.read_csv(SETTLER_POP_CSV)
    df = df.sort_values("year").reset_index(drop=True)
    df["total_with_jerusalem"] = (
        df["west_bank_excl_jerusalem"].fillna(0)
        + df["east_jerusalem"].fillna(0)
    ).astype(int)
    base = df.loc[df["year"] == 1972, "west_bank_excl_jerusalem"].iloc[0]
    df["wb_growth_multiple"] = (df["west_bank_excl_jerusalem"] / base).round(1)
    out = PROC / "settler_population_annual.csv"
    df.to_csv(out, index=False)
    print(f"  -> {out.relative_to(REPO_ROOT)}  ({len(df)} rows, "
          f"{df['year'].min()}\u2013{df['year'].max()})")
    print(df[["year", "west_bank_excl_jerusalem", "east_jerusalem",
              "wb_growth_multiple"]].to_string(index=False))


def main() -> None:
    print("Cleaning raw data into: data/processed/")
    clean_acled()
    clean_acled_events()
    govs = load_governorates()
    wb = clip_west_bank(govs)
    out_gpkg = PROC / "governorates.gpkg"
    wb.to_file(out_gpkg, layer="governorates", driver="GPKG")
    print(f"[admin] -> {out_gpkg.relative_to(REPO_ROOT)}  ({len(wb)} West Bank features)")
    clean_orchards(wb)
    clean_settlements(wb)
    clean_territorial(wb)
    clean_settler_population()

    print()
    print("Done. Next: python analysis/03_analyze.py")
if __name__ == "__main__":
    main()
