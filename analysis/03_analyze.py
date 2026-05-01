"""
Reads data/processed/, produces:
  figures/static/*.png,svg               static figures
  data/processed/linked_view_feed.json   JSON feed for the linked view
  data/processed/headline_stats.csv      numbers for the closing infographic
  interactive/heatmap.html               Plotly heatmap
  interactive/territorial_map.html       Folium territorial map

Run:
    conda run -n olives python analysis/03_analyze.py
"""

from __future__ import annotations

import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

import json
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from analysis.theme import apply_theme, PALETTE, annotate_source, savefig_pub  # noqa: E402

PROC = REPO_ROOT / "data" / "processed"
FIG_STATIC = REPO_ROOT / "figures" / "static"
FIG_STATIC.mkdir(parents=True, exist_ok=True)

apply_theme()

HARVEST_MONTHS = {10, 11}   # October and November (Palestinian olive harvest)


# ACLED and the OCHA admin layer disagree on two governorate spellings.
# ACLED follows the Palestinian Authority's Arabic-transliterated form;
# OCHA uses the shorter English form. We canonicalize to the OCHA form
# so the settlement layer (joined against OCHA polygons) and the ACLED
# event layer can be merged on `governorate` without dropping rows.
GOVERNORATE_CANONICAL = {
    "Al Quds": "Jerusalem",
    "Al-Quds": "Jerusalem",
    "Ramallah and Al Bireh": "Ramallah",
    "Ramallah and Al-Bireh": "Ramallah",
}


def _canonical_gov(s: pd.Series) -> pd.Series:
    return s.replace(GOVERNORATE_CANONICAL)


def _load_acled() -> pd.DataFrame:
    df = pd.read_csv(PROC / "acled_monthly_westbank.csv", parse_dates=["date"])
    if "governorate" in df.columns:
        df["governorate"] = _canonical_gov(df["governorate"])
    return df


def _load_orchards() -> pd.DataFrame:
    df = pd.read_csv(PROC / "orchards_by_governorate.csv")
    if "governorate" in df.columns:
        df["governorate"] = _canonical_gov(df["governorate"])
    return df


def _load_settler_population() -> pd.DataFrame | None:
    p = PROC / "settler_population_annual.csv"
    if not p.exists():
        return None
    return pd.read_csv(p)


def fig_settler_population_over_time() -> None:
    """Headline chart: annual settler population in the West Bank, 1972 onward."""
    print("[fig0] settler population over time ...")
    df = _load_settler_population()
    if df is None or df.empty:
        print("  [skip] settler_population_annual.csv missing")
        return

    years = df["year"].to_numpy()
    wb = df["west_bank_excl_jerusalem"].to_numpy() / 1000  # thousands
    ej = df["east_jerusalem"].to_numpy() / 1000

    fig, ax = plt.subplots(figsize=(11, 5.5))

    # Filled area for the West Bank (excl. East Jerusalem) line
    ax.fill_between(years, 0, wb,
                    color=PALETTE["terracotta"], alpha=0.18, zorder=2)
    ax.plot(years, wb,
            color=PALETTE["terracotta"], lw=2.4, zorder=4,
            marker="o", markersize=5, markerfacecolor=PALETTE["terracotta"],
            markeredgecolor="white", markeredgewidth=1.0,
            label="West Bank (excl. East Jerusalem)")

    # East Jerusalem as a secondary, lighter line
    mask = ~np.isnan(ej)
    ax.plot(years[mask], ej[mask],
            color=PALETTE["sage"], lw=1.6, zorder=3,
            marker="o", markersize=4, markerfacecolor=PALETTE["sage"],
            markeredgecolor="white", markeredgewidth=0.8,
            label="East Jerusalem")

    # Political markers
    markers = [
        (1979, "Elon Moreh ruling"),
        (1993, "Oslo I"),
        (2005, "Gaza disengagement"),
        (2023, "October 7"),
    ]
    for yr, label in markers:
        ax.axvline(yr, color="#595950", lw=0.6, ls=":", alpha=0.7, zorder=1)
        ax.text(yr, ax.get_ylim()[1] if False else 540,
                f" {label}", fontsize=8.5, color="#595950",
                rotation=90, va="top", ha="left", zorder=5)

    # Endpoint annotation: latest WB number
    last_yr = int(years[-1])
    last_val = float(wb[-1])
    base = float(wb[0])
    multiple = last_val / base
    ax.annotate(
        f"{last_yr}: ~{int(last_val)}k settlers\n({multiple:.0f}× the 1972 figure)",
        xy=(last_yr, last_val),
        xytext=(last_yr - 14, last_val * 0.78),
        fontsize=10.5, color=PALETTE["terracotta"], fontweight="600",
        arrowprops=dict(arrowstyle="-", color=PALETTE["terracotta"], lw=0.8),
    )

    ax.set_title(f"Israeli settler population in the West Bank, {int(years[0])}–{last_yr}",
                 loc="left", pad=18, fontsize=17, fontweight="600")
    ax.set_xlabel("")
    ax.set_ylabel("Settlers (thousands)")
    ax.set_xlim(1971, last_yr + 1)
    ax.set_ylim(0, max(wb.max(), np.nanmax(ej)) * 1.15)
    ax.legend(loc="upper left", frameon=False, fontsize=10)

    annotate_source(
        ax,
        "Source: compiled from Peace Now, FMEP, and Israeli CBS · "
        "outpost residents (~20–30k) excluded · East Jerusalem 2024 not yet published"
    )
    plt.tight_layout()
    savefig_pub(fig, str(FIG_STATIC / "settler_population"))
    plt.close(fig)
    print("  -> figures/static/settler_population.png,svg")



def fig_annual_targeting_with_harvest() -> None:
    print("[fig1] annual civilian-targeting with harvest-season split ...")
    df = _load_acled()
    df = df[df["event_type"] == "civilian_targeting"]

    # Aggregate: events per year, split into harvest (Oct–Nov) vs rest-of-year
    df["is_harvest"] = df["month"].isin(HARVEST_MONTHS)
    annual = (df.groupby(["year", "is_harvest"])["events"]
              .sum().unstack(fill_value=0)
              .rename(columns={True: "harvest", False: "rest_of_year"}))
    years = annual.index.tolist()

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.bar(years, annual["rest_of_year"],
           color=PALETTE["sage"], label="Rest of year",
           edgecolor="none", width=0.78, zorder=3)
    ax.bar(years, annual["harvest"],
           bottom=annual["rest_of_year"],
           color=PALETTE["terracotta"], label="October–November (olive harvest)",
           edgecolor="none", width=0.78, zorder=3)

    ax.set_title("Civilian-targeting events in the West Bank, 2016–2026",
                 loc="left", pad=18, fontsize=17, fontweight="600")
    ax.set_xlabel("")
    ax.set_ylabel("Reported events")
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    ax.set_xticks(years)
    # Emphasize the harvest-season fraction with annotation on the most recent complete year
    complete_years = [y for y in years if y < pd.Timestamp.now().year]
    if complete_years:
        yr = complete_years[-1]
        total = annual.loc[yr].sum()
        hv = annual.loc[yr, "harvest"]
        pct = hv / total * 100 if total else 0
        ax.annotate(
            f"{yr}: {pct:.0f}% of events\nfell in Oct–Nov",
            xy=(yr, total),
            xytext=(yr - 1.2, total * 1.08),
            fontsize=10,
            color=PALETTE["terracotta"],
            fontweight="600",
            arrowprops=dict(arrowstyle="-", color=PALETTE["terracotta"], lw=0.8),
        )
    annotate_source(ax, "Source: ACLED monthly aggregates via HDX · one-sixth of months fall in the olive-harvest window")
    plt.tight_layout()
    savefig_pub(fig, str(FIG_STATIC / "annual_targeting_harvest"))
    plt.close(fig)
    print("  -> figures/static/annual_targeting_harvest.png,svg")



def fig_seasonal_signature() -> None:
    print("[fig2] seasonal signature ...")
    df = _load_acled()
    df = df[df["event_type"] == "civilian_targeting"]

    # Mean across years, keeping year-over-year variability visible
    monthly = df.groupby(["year", "month"])["events"].sum().reset_index()
    monthly_mean = monthly.groupby("month")["events"].mean()
    monthly_p25  = monthly.groupby("month")["events"].quantile(0.25)
    monthly_p75  = monthly.groupby("month")["events"].quantile(0.75)

    months = list(range(1, 13))
    labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    fig, ax = plt.subplots(figsize=(11, 5.5))

    # Shade the harvest window
    ax.axvspan(9.5, 11.5, color=PALETTE["terracotta"], alpha=0.12, zorder=1)
    ax.text(10.5, ax.get_ylim()[1] if False else monthly_mean.max()*1.15,
            "olive harvest",
            ha="center", va="bottom",
            fontsize=10, fontweight="600",
            color=PALETTE["terracotta"],
            style="italic")

    # IQR band
    ax.fill_between(months,
                    [monthly_p25[m] for m in months],
                    [monthly_p75[m] for m in months],
                    color=PALETTE["sage_pale"], alpha=0.7,
                    label="Interquartile range (2016–2026)")

    # Mean line
    ax.plot(months, [monthly_mean[m] for m in months],
            color=PALETTE["olive_deep"], linewidth=2.6,
            marker="o", markersize=6, markerfacecolor=PALETTE["olive_deep"],
            label="Monthly mean")

    ax.set_xticks(months)
    ax.set_xticklabels(labels)
    ax.set_xlim(0.5, 12.5)
    ax.set_ylim(bottom=0)
    ax.set_title("Civilian-targeting events by calendar month",
                 loc="left", pad=18, fontsize=17, fontweight="600")
    ax.set_ylabel("Events per month (West Bank total)")
    ax.set_xlabel("")
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    annotate_source(ax, "Source: ACLED monthly aggregates · West Bank · averaged 2016–2026")
    plt.tight_layout()
    savefig_pub(fig, str(FIG_STATIC / "seasonal_signature"))
    plt.close(fig)
    print("  -> figures/static/seasonal_signature.png,svg")



def fig_orchard_area_by_governorate() -> None:
    print("[fig3] orchard area by governorate ...")
    df = _load_orchards().sort_values("area_dunums")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(df["governorate"], df["area_dunums"],
            color=PALETTE["olive_deep"], zorder=3)
    for i, (g, a) in enumerate(zip(df["governorate"], df["area_dunums"])):
        ax.text(a + 400, i, f"{int(a):,}", va="center",
                fontsize=9, color=PALETTE["ink_soft"])
    ax.set_title("Mapped orchard area by governorate",
                 loc="left", pad=18, fontsize=16, fontweight="600")
    ax.set_xlabel("Dunums (1 dunum = 1,000 m²)")
    ax.set_ylabel("")
    ax.grid(False, axis="y")
    annotate_source(ax, "Source: OSM landuse=orchard polygons, clipped to West Bank.\n"
                        "Under-counts in governorates where OSM orchard tagging is sparse (see appendix).")
    plt.tight_layout()
    savefig_pub(fig, str(FIG_STATIC / "orchard_area_by_governorate"))
    plt.close(fig)
    print("  -> figures/static/orchard_area_by_governorate.png,svg")



def export_linked_view_feed() -> None:
    print("[feed] building linked_view_feed.json ...")
    acled = _load_acled()
    orchards = _load_orchards().set_index("governorate")

    ct = acled[acled["event_type"] == "civilian_targeting"]
    years = sorted(ct["year"].unique().tolist())

    governorates = []
    for gov, sub in ct.groupby("governorate"):
        series_by_year = (sub.groupby("year")["events"].sum()
                          .reindex(years, fill_value=0).astype(int).to_dict())
        gov_totals = {
            "name": str(gov),
            "incidents_by_year": {str(y): int(n) for y, n in series_by_year.items()},
            "total": int(sub["events"].sum()),
            "fatalities_total": int(sub["fatalities"].sum()),
            "orchard_dunums": float(orchards.loc[gov, "area_dunums"]) if gov in orchards.index else None,
            "orchard_count":  int(orchards.loc[gov, "orchard_count"])  if gov in orchards.index else None,
        }
        governorates.append(gov_totals)

    feed = {"years": years, "governorates": governorates,
            "harvest_months": sorted(list(HARVEST_MONTHS))}

    out = PROC / "linked_view_feed.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(feed, f, indent=2)
    print(f"  -> {out.relative_to(REPO_ROOT)}  ({len(governorates)} governorates, "
          f"{len(years)} years)")

    # Also colocate with the HTML iframe so it ships in the rendered site
    interactive_copy = REPO_ROOT / "interactive" / "linked_view_feed.json"
    interactive_copy.parent.mkdir(exist_ok=True)
    with interactive_copy.open("w", encoding="utf-8") as f:
        json.dump(feed, f, indent=2)
    print(f"  -> {interactive_copy.relative_to(REPO_ROOT)}")

    # Inline the same feed as embedded JSON inside linked-view.html. This is
    # what the iframe actually reads at runtime, so the page works under
    # file:// where fetch() is blocked, and during static deploys where the
    # side-car JSON might be served with the wrong MIME type.
    import re
    lv_path = REPO_ROOT / "interactive" / "linked-view.html"
    if lv_path.exists():
        html = lv_path.read_text(encoding="utf-8")
        block = (
            '<script id="embedded-feed" type="application/json">\n'
            + json.dumps(feed, indent=2)
            + '\n</script>'
        )
        new_html, n = re.subn(
            r'<script id="embedded-feed"[^>]*>.*?</script>',
            lambda _m: block,
            html,
            count=1,
            flags=re.DOTALL,
        )
        if n:
            lv_path.write_text(new_html, encoding="utf-8")
            print(f"  -> {lv_path.relative_to(REPO_ROOT)}  (embedded feed updated)")
        else:
            print(f"  [warn] {lv_path.relative_to(REPO_ROOT)} has no embedded-feed slot")


# Headline stats

def compute_headline_stats() -> None:
    print("[stats] computing headline stats ...")
    acled = _load_acled()
    orchards = _load_orchards()

    ct = acled[acled["event_type"] == "civilian_targeting"]
    rows = []

    # Total documented civilian-targeting events
    total_events = int(ct["events"].sum())
    rows.append(("total_civilian_targeting_events", total_events))

    # Fatalities
    rows.append(("total_fatalities", int(ct["fatalities"].sum())))

    # Date range
    rows.append(("first_year", int(ct["year"].min())))
    rows.append(("last_year", int(ct["year"].max())))

    # Harvest-season concentration: share of events falling in Oct–Nov
    harvest = ct[ct["month"].isin(HARVEST_MONTHS)]["events"].sum()
    share = harvest / total_events * 100 if total_events else 0
    rows.append(("harvest_season_event_share_pct", f"{share:.1f}"))

    # Orchard totals
    rows.append(("mapped_orchard_polygons", int(orchards["orchard_count"].sum())))
    rows.append(("mapped_orchard_area_dunums", int(orchards["area_dunums"].sum())))
    rows.append(("mapped_orchard_area_hectares", int(orchards["area_ha"].sum())))

    # Top governorate by events
    top = ct.groupby("governorate")["events"].sum().sort_values(ascending=False).head(1)
    if len(top):
        rows.append(("top_governorate_events", top.index[0]))
        rows.append(("top_governorate_events_count", int(top.iloc[0])))

    # Event-level: perpetrator breakdown and proximity
    events_path = PROC / "acled_events_westbank.parquet"
    if events_path.exists():
        ev = pd.read_parquet(events_path)
        pal = ev[ev["targets_palestinian_civilians"]]
        rows.append(("events_targeting_pal_civilians", int(len(pal))))
        bucket_counts = pal["perpetrator"].value_counts().to_dict()
        rows.append(("events_perp_settlers", int(bucket_counts.get("Settlers", 0))))
        rows.append(("events_perp_state_forces", int(bucket_counts.get("Israeli state forces", 0))))
        # Olive/tree damage
        rows.append(("events_mention_olive_or_tree", int(pal["olive_or_tree"].sum())))
        rows.append(("events_mention_livestock", int(pal["livestock"].sum())))

        # Proximity stats
        try:
            import geopandas as gpd
            pts = pal.dropna(subset=["latitude", "longitude"]).copy()
            pts = pts[pts["latitude"].between(31.0, 33.0) & pts["longitude"].between(34.5, 36.0)]
            gdf = gpd.GeoDataFrame(pts, geometry=gpd.points_from_xy(pts["longitude"], pts["latitude"]), crs=4326).to_crs(2039)
            sett = gpd.read_file(PROC / "settlements.gpkg").to_crs(2039)
            d = gdf.geometry.distance(sett.geometry.union_all()).values / 1000.0
            rows.append(("events_within_2km_pct", f"{(d<=2).mean()*100:.0f}"))
            rows.append(("events_within_5km_pct", f"{(d<=5).mean()*100:.0f}"))
            rows.append(("event_settlement_distance_median_km", f"{float(np.median(d)):.1f}"))
        except Exception as e:
            print(f"  [warn] proximity stats failed: {e}")

    # Settlements (Peace Now)
    sett_csv = PROC / "settlements_by_governorate.csv"
    if sett_csv.exists():
        sett = pd.read_csv(sett_csv)
        rows.append(("total_settlements", int(sett["settlement_count"].sum())))
        rows.append(("settlement_area_dunums", int(sett["settlement_area_dunums"].sum())))
        # Correlation between settlement count and civilian-targeting events per gov
        ct_per_gov = ct.groupby("governorate")["events"].sum().reset_index()
        merged = ct_per_gov.merge(sett, on="governorate", how="left").fillna(0)
        if len(merged) > 2:
            r = merged["settlement_count"].corr(merged["events"])
            rows.append(("settlements_events_pearson_r", f"{r:.2f}"))

    # Settler population (curated annual series)
    pop = _load_settler_population()
    if pop is not None and not pop.empty:
        first = pop.iloc[0]
        last = pop.iloc[-1]
        rows.append(("settler_pop_first_year", int(first["year"])))
        rows.append(("settler_pop_first_wb", int(first["west_bank_excl_jerusalem"])))
        rows.append(("settler_pop_last_year", int(last["year"])))
        rows.append(("settler_pop_last_wb", int(last["west_bank_excl_jerusalem"])))
        # Latest with East Jerusalem (use most recent year that has both)
        with_ej = pop.dropna(subset=["east_jerusalem"]).iloc[-1]
        rows.append(("settler_pop_last_combined_year", int(with_ej["year"])))
        rows.append(("settler_pop_last_combined", int(with_ej["total_with_jerusalem"])))
        rows.append(("settler_pop_growth_multiple", f"{last['wb_growth_multiple']:.0f}"))
        # Growth since Oslo (1993)
        if (pop["year"] == 1993).any():
            oslo = int(pop.loc[pop["year"] == 1993, "west_bank_excl_jerusalem"].iloc[0])
            since_oslo = int(last["west_bank_excl_jerusalem"]) - oslo
            rows.append(("settler_pop_added_since_oslo", since_oslo))
            rows.append(("settler_pop_oslo_baseline", oslo))

    out = PROC / "headline_stats.csv"
    pd.DataFrame(rows, columns=["metric", "value"]).to_csv(out, index=False)
    print(f"  -> {out.relative_to(REPO_ROOT)}")
    for k, v in rows:
        print(f"    {k:40s} {v}")


def _load_events() -> pd.DataFrame | None:
    p = PROC / "acled_events_westbank.parquet"
    if not p.exists():
        return None
    return pd.read_parquet(p)


def fig_perpetrator_breakdown() -> None:
    """Annual events targeting Palestinian civilians, stacked by perpetrator."""
    print("[fig7] perpetrator breakdown over time ...")
    df = _load_events()
    if df is None:
        print("  [skip] event-level parquet not present")
        return
    pal = df[df["targets_palestinian_civilians"]].copy()
    # Collapse to 3 narrative-friendly buckets
    def bucket(p):
        if p == "Settlers": return "Settlers"
        if p == "Israeli state forces": return "Israeli state forces"
        if p in ("Other Israeli actor",): return "Other Israeli (civilians, unidentified)"
        return "Other / Palestinian"
    pal["bucket"] = pal["perpetrator"].apply(bucket)

    annual = (pal.groupby(["year", "bucket"]).size()
              .unstack(fill_value=0))
    order = ["Israeli state forces", "Settlers", "Other Israeli (civilians, unidentified)", "Other / Palestinian"]
    order = [c for c in order if c in annual.columns]
    annual = annual[order]

    color_map = {
        "Israeli state forces":                    PALETTE["olive_deep"],
        "Settlers":                                PALETTE["terracotta"],
        "Other Israeli (civilians, unidentified)": PALETTE["sage"],
        "Other / Palestinian":                     PALETTE["gold"],
    }

    years = annual.index.tolist()
    fig, ax = plt.subplots(figsize=(11, 5.5))
    bottom = np.zeros(len(years))
    for col in order:
        ax.bar(years, annual[col].values, bottom=bottom,
               label=col, color=color_map[col],
               edgecolor="none", width=0.78, zorder=3)
        bottom += annual[col].values

    ax.set_title("Events targeting Palestinian civilians, by perpetrator",
                 loc="left", pad=18, fontsize=17, fontweight="600")
    ax.set_ylabel("Events per year")
    ax.set_xlabel("")
    ax.set_xticks(years)
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    annotate_source(ax, "Source: ACLED event-level export · West Bank · actor1 classified into perpetrator buckets")
    plt.tight_layout()
    savefig_pub(fig, str(FIG_STATIC / "perpetrator_breakdown"))
    plt.close(fig)
    print("  -> figures/static/perpetrator_breakdown.png,svg")


def fig_damage_breakdown() -> None:
    """Bar chart: count of events targeting Palestinian civilians that mention
    each damage keyword in the ACLED notes field."""
    print("[fig8] damage-type breakdown ...")
    df = _load_events()
    if df is None:
        print("  [skip] event-level parquet not present")
        return
    pal = df[df["targets_palestinian_civilians"]].copy()
    keys = [
        ("olive_or_tree", "Olive trees / groves"),
        ("livestock",     "Livestock (sheep, goats)"),
        ("home_property", "Homes and property"),
        ("vehicle",       "Vehicles"),
        ("mosque_school", "Mosque, school, church"),
        ("crop_field",    "Crops and fields"),
        ("burn",          "Burning / arson"),
    ]
    counts = [(label, int(pal[col].sum())) for col, label in keys]
    counts.sort(key=lambda x: x[1])

    labels, vals = zip(*counts)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.barh(labels, vals, color=PALETTE["olive_deep"], zorder=3)
    for i, v in enumerate(vals):
        ax.text(v + max(vals) * 0.01, i, f"{v:,}",
                va="center", fontsize=10, color=PALETTE["ink_soft"])
    ax.set_title("Damage types described in event narratives",
                 loc="left", pad=14, fontsize=16, fontweight="600")
    ax.set_xlabel(f"Events mentioning the keyword (of {len(pal):,} targeting Palestinian civilians)")
    annotate_source(ax,
        "Source: keyword scan of ACLED `notes` field. Categories overlap (an event can mention multiple).\n"
        "These are descriptive counts, not a structured field. Use as indicative, not definitive.")
    plt.tight_layout()
    savefig_pub(fig, str(FIG_STATIC / "damage_breakdown"))
    plt.close(fig)
    print("  -> figures/static/damage_breakdown.png,svg")


def fig_settlement_proximity() -> None:
    """Histogram: distance from each event targeting Palestinian civilians to
    the nearest Israeli settlement polygon."""
    print("[fig9] settlement-proximity distribution ...")
    import geopandas as gpd
    df = _load_events()
    if df is None:
        print("  [skip] event-level parquet not present")
        return
    pal = df[df["targets_palestinian_civilians"]].copy()
    pal = pal.dropna(subset=["latitude", "longitude"])
    pal = pal[(pal["latitude"].between(31.0, 33.0)) & (pal["longitude"].between(34.5, 36.0))]

    pts = gpd.GeoDataFrame(
        pal[["perpetrator"]],
        geometry=gpd.points_from_xy(pal["longitude"], pal["latitude"]),
        crs=4326,
    ).to_crs(2039)

    settlements = gpd.read_file(PROC / "settlements.gpkg").to_crs(2039)
    sett_union = settlements.geometry.union_all()

    # Distance in meters from each point to nearest settlement boundary
    dists = pts.geometry.distance(sett_union).values / 1000.0  # km

    fig, ax = plt.subplots(figsize=(11, 5.2))
    bins = np.linspace(0, 10, 41)  # 0 - 10km, 0.25km bins
    ax.hist(dists, bins=bins, color=PALETTE["olive_deep"],
            edgecolor="white", linewidth=0.8, zorder=3)

    # Median annotation
    median = np.median(dists)
    ax.axvline(median, color=PALETTE["terracotta"], linewidth=2, linestyle="--", zorder=4)
    ax.text(median + 0.15, ax.get_ylim()[1] * 0.92,
            f"median = {median:.1f} km",
            color=PALETTE["terracotta"], fontsize=11, fontweight="600")

    pct_within_2 = (dists <= 2).mean() * 100
    pct_within_5 = (dists <= 5).mean() * 100
    ax.text(0.97, 0.95,
            f"{pct_within_2:.0f}% of events occur within 2 km of a settlement\n"
            f"{pct_within_5:.0f}% occur within 5 km",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=11, color=PALETTE["ink_soft"],
            bbox=dict(facecolor=PALETTE["bone_pale"], edgecolor=PALETTE["rule"], boxstyle="round,pad=0.4"))

    ax.set_title("How close are these events to a settlement?",
                 loc="left", pad=16, fontsize=17, fontweight="600")
    ax.set_xlabel("Distance from event to nearest settlement (km)")
    ax.set_ylabel("Events")
    ax.set_xlim(0, 10)
    annotate_source(ax,
        f"Source: ACLED event-level points (n={len(dists):,}, targeting Palestinian civilians) vs Peace Now settlements. "
        "Distances computed in EPSG:2039 (Israeli Transverse Mercator).")
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    savefig_pub(fig, str(FIG_STATIC / "settlement_proximity"))
    plt.close(fig)
    print(f"  -> figures/static/settlement_proximity.png,svg")
    print(f"     median = {median:.2f} km · within 2km = {pct_within_2:.1f}% · within 5km = {pct_within_5:.1f}%")


def fig_overlay_map() -> None:
    """Static overlay map: orchards (sage) + settlements (terracotta) on West Bank."""
    print("[fig5] overlay map (orchards + settlements) ...")
    import geopandas as gpd
    govs = gpd.read_file(PROC / "governorates.gpkg")
    orchards = gpd.read_file(PROC / "orchards_westbank.gpkg")
    settlements = gpd.read_file(PROC / "settlements.gpkg")
    for layer in (govs, orchards, settlements):
        if layer.crs is None or layer.crs.to_epsg() != 4326:
            layer.to_crs(4326, inplace=True)

    fig, ax = plt.subplots(figsize=(8.5, 10))
    govs.plot(ax=ax, facecolor=PALETTE["bone_pale"],
              edgecolor=PALETTE["rule"], linewidth=0.7, zorder=1)
    orchards.plot(ax=ax, facecolor=PALETTE["sage"], edgecolor="none",
                  alpha=0.85, zorder=2)
    settlements.plot(ax=ax, facecolor=PALETTE["terracotta"], edgecolor="white",
                     linewidth=0.3, alpha=0.85, zorder=3)

    # Governorate name labels at centroids
    name_col = next((c for c in govs.columns
                     if c.lower() in ("adm2_name","adm2_en","admin2name_en","name")), None)
    if name_col:
        for _, row in govs.iterrows():
            c = row.geometry.centroid
            ax.text(c.x, c.y, row[name_col], ha="center", va="center",
                    fontsize=8, color=PALETTE["ink_soft"], alpha=0.7,
                    fontweight="500", zorder=4)

    ax.set_title("Orchards and settlements, side by side",
                 loc="left", pad=14, fontsize=16, fontweight="600")
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values(): spine.set_visible(False)

    # Custom legend
    from matplotlib.patches import Patch
    handles = [
        Patch(facecolor=PALETTE["sage"], edgecolor="none", label="Mapped orchards (OSM)"),
        Patch(facecolor=PALETTE["terracotta"], edgecolor="white", label="Israeli settlements (Peace Now)"),
    ]
    ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=10)
    annotate_source(ax, "Sources: OSM landuse=orchard · Peace Now built-up settlement polygons · OCHA admin boundaries")
    plt.tight_layout()
    savefig_pub(fig, str(FIG_STATIC / "overlay_map"))
    plt.close(fig)
    print("  -> figures/static/overlay_map.png,svg")


def fig_settlements_vs_events() -> None:
    """Scatter: settlements per governorate vs events per governorate."""
    print("[fig6] settlements vs events scatter ...")
    settlements = pd.read_csv(PROC / "settlements_by_governorate.csv")
    acled = _load_acled()
    events = (acled[acled["event_type"] == "civilian_targeting"]
              .groupby("governorate")["events"].sum().reset_index()
              .rename(columns={"events": "ct_events"}))
    df = events.merge(settlements, on="governorate", how="left").fillna(0)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(df["settlement_count"], df["ct_events"],
               s=120, color=PALETTE["olive_deep"], edgecolor="white",
               linewidth=1.5, alpha=0.85, zorder=3)
    for _, row in df.iterrows():
        ax.annotate(row["governorate"],
                    (row["settlement_count"], row["ct_events"]),
                    xytext=(8, 4), textcoords="offset points",
                    fontsize=10, color=PALETTE["ink_soft"])

    # Light correlation indicator
    if len(df) > 2:
        r = df["settlement_count"].corr(df["ct_events"])
        ax.text(0.97, 0.05, f"Pearson r = {r:.2f}",
                transform=ax.transAxes, ha="right", va="bottom",
                fontsize=11, color=PALETTE["ink_soft"], style="italic")

    ax.set_title("Settlements per governorate vs civilian-targeting events",
                 loc="left", pad=18, fontsize=16, fontweight="600")
    ax.set_xlabel("Israeli settlements (count, Peace Now)")
    ax.set_ylabel("Civilian-targeting events 2016–2026 (ACLED)")
    annotate_source(ax, "Sources: Peace Now built-up settlements (HDX) · ACLED monthly aggregates")
    plt.tight_layout()
    savefig_pub(fig, str(FIG_STATIC / "settlements_vs_events"))
    plt.close(fig)
    print("  -> figures/static/settlements_vs_events.png,svg")


def fig_fatalities_by_event_type() -> None:
    """Static stacked-area chart: annual fatalities split by ACLED event type."""
    print("[fig4] fatalities by event type ...")
    df = _load_acled()
    pivot = (df.groupby(["year", "event_type"])["fatalities"]
             .sum().unstack(fill_value=0))
    # Order: civilian_targeting on top (the bright terracotta) for emphasis
    order = [c for c in ["demonstrations", "political_violence", "civilian_targeting"]
             if c in pivot.columns]
    pivot = pivot[order]

    label_map = {
        "civilian_targeting":  "Civilian targeting",
        "political_violence":  "Political violence",
        "demonstrations":      "Demonstrations",
    }
    color_map = {
        "civilian_targeting":  PALETTE["terracotta"],
        "political_violence":  PALETTE["olive_deep"],
        "demonstrations":      PALETTE["sage"],
    }

    years = pivot.index.tolist()
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.stackplot(years,
                 [pivot[c].values for c in order],
                 labels=[label_map[c] for c in order],
                 colors=[color_map[c] for c in order],
                 alpha=0.92, edgecolor="white", linewidth=1.2)
    ax.set_title("Recorded fatalities in West Bank events, by event type",
                 loc="left", pad=16, fontsize=17, fontweight="600")
    ax.set_ylabel("Fatalities per year")
    ax.set_xlabel("")
    ax.set_xticks(years)
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    annotate_source(ax, "Source: ACLED monthly aggregates · West Bank")
    plt.tight_layout()
    savefig_pub(fig, str(FIG_STATIC / "fatalities_by_event_type"))
    plt.close(fig)
    print("  -> figures/static/fatalities_by_event_type.png,svg")


def build_governorate_heatmap() -> None:
    """Interactive Plotly heatmap: governorate x year, civilian-targeting events."""
    print("[interactive] governorate x year heatmap ...")
    import plotly.graph_objects as go

    df = _load_acled()
    ct = df[df["event_type"] == "civilian_targeting"]

    pivot = (ct.groupby(["governorate", "year"])["events"].sum()
             .unstack(fill_value=0))
    # Order rows by total events, descending (densest at top)
    row_order = pivot.sum(axis=1).sort_values(ascending=True).index
    pivot = pivot.loc[row_order]

    years = pivot.columns.tolist()
    govs = pivot.index.tolist()
    z = pivot.values

    colorscale = [
        [0.00, "#F5F0E6"],
        [0.15, "#D9D4B8"],
        [0.35, "#9BAA85"],
        [0.65, "#6B7F54"],
        [0.85, "#4A5D3A"],
        [1.00, "#B95835"],
    ]

    hover = [[f"<b>{g}</b><br>{y}: {int(v):,} events"
              for y, v in zip(years, row)] for g, row in zip(govs, z)]

    fig = go.Figure(go.Heatmap(
        z=z, x=years, y=govs, colorscale=colorscale,
        hoverinfo="text", text=hover,
        colorbar=dict(title="Events", tickfont=dict(size=10)),
    ))
    fig.update_layout(
        title=dict(
            text="<b>Civilian-targeting events by governorate and year</b><br>"
                 "<span style='font-size:12px;color:#595950'>"
                 "Rows ordered by total events. 2023–2025 visible as a vertical band across every governorate.</span>",
            x=0.01, xanchor="left", font=dict(size=16)),
        font=dict(family="Cormorant Garamond, Georgia, serif", size=13, color="#2A2A26"),
        paper_bgcolor="#F5F0E6",
        plot_bgcolor="#F5F0E6",
        margin=dict(l=130, r=40, t=90, b=60),
        xaxis=dict(title="", dtick=1, tickfont=dict(size=11)),
        yaxis=dict(title="", tickfont=dict(size=12)),
        height=520,
        annotations=[dict(
            text="Source: ACLED monthly aggregates via HDX · West Bank",
            xref="paper", yref="paper", x=1.0, y=-0.12,
            xanchor="right", showarrow=False,
            font=dict(size=10, color="#595950"))],
    )

    out = REPO_ROOT / "interactive" / "heatmap.html"
    out.parent.mkdir(exist_ok=True)
    fig.write_html(out, include_plotlyjs="cdn", full_html=True,
                   config={"displayModeBar": False, "responsive": True})
    print(f"  -> {out.relative_to(REPO_ROOT)}")


def fig_territorial_map() -> None:
    """Crisis-Group-style interactive territorial map of the West Bank.

    Layered Folium HTML with toggleable feature groups:
      • Areas A / B / C / H1 / H2 / Nature Reserve / East Jerusalem (Oslo II)
      • The Separation Barrier (constructed / under construction / projected)
      • Israeli built-up settlements (Peace Now)
      • Governorate boundaries
      • Palestinian villages mentioned in this piece (Burin, Turmus Ayya,
        Al-Mughayyir, At-Tuwani) as named markers

    Sources: OCHA oPt (HDX) for the Oslo polygons and barrier alignment;
    Peace Now (HDX) for the settlement footprints; OCHA admin layer for the
    governorate boundaries.
    """
    print("[fig-territorial] building Crisis-Group-style territorial map ...")

    import folium
    import geopandas as gpd

    terr_gpkg = PROC / "territorial.gpkg"
    if not terr_gpkg.exists():
        print(f"  [skip] {terr_gpkg.relative_to(REPO_ROOT)} missing")
        return

    oslo = gpd.read_file(terr_gpkg, layer="oslo_areas").to_crs(4326)
    barrier = gpd.read_file(terr_gpkg, layer="barrier").to_crs(4326)

    sett = gpd.read_file(PROC / "settlements.gpkg", layer="settlements").to_crs(4326)
    govs = gpd.read_file(PROC / "governorates.gpkg", layer="governorates").to_crs(4326)

    # Simplify geometries for an in-page embed (Folium serialises to inline GeoJSON,
    # so detailed polygons quickly bloat the HTML to tens of MB). 0.0003 degrees
    # is roughly 30 m at this latitude (visually identical at West Bank zoom levels).
    oslo["geometry"] = oslo.geometry.simplify(0.0003, preserve_topology=True)
    barrier["geometry"] = barrier.geometry.simplify(0.0003, preserve_topology=True)
    sett["geometry"] = sett.geometry.simplify(0.0003, preserve_topology=True)
    govs["geometry"] = govs.geometry.simplify(0.0008, preserve_topology=True)

    # Centre on the West Bank
    minx, miny, maxx, maxy = oslo.total_bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2

    m = folium.Map(
        location=[cy, cx], zoom_start=10, control_scale=True,
        tiles="CartoDB positron", attr="© OpenStreetMap, © CartoDB",
    )

    # ----- Areas A / B / C / etc. -------------------------------------------
    AREA_STYLES = {
        "A":                                 {"color": "#4A5D3A", "fill": "#9BAA85", "label": "Area A: Palestinian civil + security"},
        "B":                                 {"color": "#6B7F54", "fill": "#C8D1B8", "label": "Area B: Palestinian civil, Israeli security"},
        "C":                                 {"color": "#B95835", "fill": "#D88562", "label": "Area C: full Israeli control"},
        "H1":                                {"color": "#4A5D3A", "fill": "#9BAA85", "label": "Hebron H1: Palestinian control"},
        "H2":                                {"color": "#B95835", "fill": "#D88562", "label": "Hebron H2: Israeli control"},
        "Israeli Declared East Jerusalem":   {"color": "#7A3A22", "fill": "#A06043", "label": "East Jerusalem: Israeli annexed (not recognised internationally)"},
        "Nature Reserve":                    {"color": "#C9A961", "fill": "#E0C58A", "label": "Nature Reserve / Israeli Park"},
        "No Man's Land":                     {"color": "#888", "fill": "#CCC", "label": "No Man's Land"},
    }

    for cls, style in AREA_STYLES.items():
        sub = oslo[oslo["class"] == cls]
        if sub.empty:
            continue
        fg = folium.FeatureGroup(name=style["label"], show=cls in ("A", "B", "C"))
        folium.GeoJson(
            sub.__geo_interface__,
            style_function=lambda _f, s=style: {
                "color": s["color"], "weight": 1.0,
                "fillColor": s["fill"], "fillOpacity": 0.45,
            },
            highlight_function=lambda _f: {"weight": 2.0, "fillOpacity": 0.65},
            tooltip=folium.GeoJsonTooltip(fields=["class"], aliases=["Area:"], sticky=False),
        ).add_to(fg)
        fg.add_to(m)

    # ----- Separation Barrier -----------------------------------------------
    BARRIER_STYLES = {
        "Constructed":        {"color": "#2A2A26", "dash": None,    "weight": 3.0, "label": "Barrier: constructed"},
        "Under Construction": {"color": "#4A4A44", "dash": "8,4",   "weight": 2.5, "label": "Barrier: under construction"},
        "Projected":          {"color": "#888",    "dash": "4,4",   "weight": 2.0, "label": "Barrier: projected"},
    }
    for status, style in BARRIER_STYLES.items():
        sub = barrier[barrier["status"] == status]
        if sub.empty:
            continue
        fg = folium.FeatureGroup(name=style["label"], show=(status == "Constructed"))
        folium.GeoJson(
            sub.__geo_interface__,
            style_function=lambda _f, s=style: {
                "color": s["color"], "weight": s["weight"],
                "dashArray": s["dash"],
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["status", "barrier_type"],
                aliases=["Status:", "Type:"], sticky=False,
            ),
        ).add_to(fg)
        fg.add_to(m)

    # ----- Settlement footprints --------------------------------------------
    fg_sett = folium.FeatureGroup(name="Israeli built-up settlements (Peace Now)", show=True)
    folium.GeoJson(
        sett.__geo_interface__,
        style_function=lambda _f: {
            "color": "#7A3A22", "weight": 0.8,
            "fillColor": "#B95835", "fillOpacity": 0.85,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["Name", "area_dunums"],
            aliases=["Settlement:", "Built-up area (dunums):"],
            sticky=False, localize=True,
        ),
    ).add_to(fg_sett)
    fg_sett.add_to(m)

    # ----- Governorate boundaries -------------------------------------------
    name_col = next((c for c in govs.columns
                     if c.lower() in ("adm2_en","admin2name_en","admin2name","adm2_name","name")), None)
    # Drop any non-JSON-serialisable columns (Timestamp etc.) before exporting
    govs_export = govs[[name_col, "geometry"]].copy() if name_col else govs[["geometry"]].copy()
    fg_gov = folium.FeatureGroup(name="Governorate boundaries", show=False)
    folium.GeoJson(
        govs_export.__geo_interface__,
        style_function=lambda _f: {
            "color": "#2A2A26", "weight": 1.5,
            "fillColor": "#000", "fillOpacity": 0,
            "dashArray": "3,3",
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[name_col] if name_col else [],
            aliases=["Governorate:"],
        ),
    ).add_to(fg_gov)
    fg_gov.add_to(m)

    # ----- Four villages mentioned in Part V --------------------------------
    VILLAGES = [
        ("Burin",        32.1772, 35.2553, "Nablus governorate"),
        ("Turmus Ayya",  32.0317, 35.2858, "Ramallah governorate (north)"),
        ("Al-Mughayyir", 32.0606, 35.3886, "Ramallah governorate (east)"),
        ("At-Tuwani",    31.4087, 35.1378, "South Hebron Hills"),
    ]
    fg_vil = folium.FeatureGroup(name="Villages featured in Part V", show=True)
    for name, lat, lon, region in VILLAGES:
        folium.CircleMarker(
            location=[lat, lon], radius=6,
            color="#4A5D3A", fill=True, fillColor="#F5F0E6", fillOpacity=1.0,
            weight=2.5,
            popup=folium.Popup(f"<b>{name}</b><br>{region}", max_width=240),
            tooltip=name,
        ).add_to(fg_vil)
    fg_vil.add_to(m)

    folium.LayerControl(collapsed=False, position="topright").add_to(m)

    # Top-left legend / source attribution
    legend_html = """
    <div style="
      position: fixed; bottom: 14px; left: 14px; z-index: 9999;
      background: rgba(245, 240, 230, 0.95);
      border: 1px solid #D9D2C0; padding: 10px 12px; border-radius: 2px;
      font-family: 'Cormorant Garamond', Georgia, serif; font-size: 0.9rem;
      color: #2A2A26; max-width: 320px; line-height: 1.4;">
      <div style="font-weight: 600; margin-bottom: 4px;">Territorial layers</div>
      <div style="font-size: 0.8rem; color: #595950;">
        Areas A / B / C from the 1995 Oslo II accord. Barrier alignment as of January 2018.
        Settlements are Peace Now's mapped built-up footprints.
        Toggle layers using the panel on the right.
      </div>
      <div style="font-size: 0.7rem; color: #888; margin-top: 6px;">
        Sources: OCHA oPt (HDX) · Peace Now via HDX
      </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    out = REPO_ROOT / "interactive" / "territorial_map.html"
    out.parent.mkdir(exist_ok=True)
    m.save(str(out))
    print(f"  -> {out.relative_to(REPO_ROOT)}")


def main() -> None:
    print("Analyzing / producing figures + feeds")
    fig_settler_population_over_time()
    fig_annual_targeting_with_harvest()
    fig_seasonal_signature()
    fig_orchard_area_by_governorate()
    fig_fatalities_by_event_type()
    fig_overlay_map()
    fig_settlements_vs_events()
    fig_perpetrator_breakdown()
    fig_damage_breakdown()
    fig_settlement_proximity()
    export_linked_view_feed()
    build_governorate_heatmap()
    fig_territorial_map()
    compute_headline_stats()
    print()
    print("Done.")
if __name__ == "__main__":
    main()
