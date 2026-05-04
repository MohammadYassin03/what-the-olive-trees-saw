"""
Interactive (Plotly) versions of the headline static figures.

Outputs to `interactive/*.html` so each can be embedded as an `<iframe>` from
the Quarto narrative. The static PNGs in `figures/static/` are kept as
fallbacks and for the print/export PDF rendering. The in-browser narrative
embeds the interactive HTML versions.

Run:
    conda run -n olives python analysis/04_interactive.py
"""
from __future__ import annotations

import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[1]
PROC = REPO_ROOT / "data" / "processed"
OUT = REPO_ROOT / "interactive"
OUT.mkdir(exist_ok=True)

# Theme palette mirrored from analysis/theme.py + theme.scss so the interactive
# figures sit visually next to the prose. Keep these in sync if the SCSS palette
# is ever retuned.
PALETTE = {
    "olive_deep": "#4A5D3A",
    "olive_mid":  "#6B7F54",
    "sage":       "#9BAA85",
    "sage_pale":  "#C8D1B8",
    "bone":       "#F5F0E6",
    "bone_pale":  "#FAF6EC",
    "ink":        "#2A2A26",
    "ink_soft":   "#595950",
    "terracotta": "#B95835",
    "gold":       "#C9A961",
    "rule":       "#D9D2C0",
}

HARVEST_MONTHS = {10, 11}

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


def _load_events() -> pd.DataFrame | None:
    p = PROC / "acled_events_westbank.parquet"
    if not p.exists():
        return None
    return pd.read_parquet(p)


def _base_layout(title: str, subtitle: str = "", height: int = 540) -> dict:
    """Shared Plotly layout: bone background, serif type, legend below x-axis,
    sourcing in the bottom margin. Heights are tuned to match the iframe
    min-height in index.qmd so the chart fills its container."""
    full_title = (
        f"<b>{title}</b>"
        + (f"<br><span style='font-size:12px;color:{PALETTE['ink_soft']};font-weight:400'>{subtitle}</span>"
           if subtitle else "")
    )
    return dict(
        title=dict(text=full_title, x=0.02, xanchor="left",
                   y=0.96, yanchor="top",
                   font=dict(size=17, color=PALETTE["ink"])),
        font=dict(family="Cormorant Garamond, Georgia, serif",
                  size=13, color=PALETTE["ink"]),
        paper_bgcolor=PALETTE["bone_pale"],
        plot_bgcolor=PALETTE["bone_pale"],
        margin=dict(l=80, r=40, t=110 if subtitle else 80, b=130),
        hoverlabel=dict(bgcolor=PALETTE["bone"], bordercolor=PALETTE["rule"],
                        font=dict(family="Inter, system-ui, sans-serif",
                                  size=13, color=PALETTE["ink"])),
        legend=dict(orientation="h", yanchor="top", y=-0.18,
                    xanchor="center", x=0.5, font=dict(size=11),
                    bgcolor="rgba(0,0,0,0)"),
        height=height,
    )


def _attribution(text: str) -> dict:
    return dict(text=f"<span style='font-size:10px;color:{PALETTE['ink_soft']}'>{text}</span>",
                xref="paper", yref="paper", x=1.0, y=-0.32,
                xanchor="right", yanchor="top", showarrow=False)


def _write(fig: go.Figure, name: str) -> None:
    out = OUT / f"{name}.html"
    fig.write_html(
        out,
        include_plotlyjs="cdn",
        full_html=True,
        config={"displayModeBar": False, "responsive": True},
    )
    print(f"  -> {out.relative_to(REPO_ROOT)}")


# 1. Settler population over time (the headline)
def fig_settler_population() -> None:
    print("[i1] settler population (interactive) ...")
    df = pd.read_csv(PROC / "settler_population_annual.csv")
    years = df["year"].to_numpy()
    wb = df["west_bank_excl_jerusalem"].to_numpy() / 1000  # thousands
    ej = df["east_jerusalem"].to_numpy() / 1000

    fig = go.Figure()
    # Filled area for visual weight
    fig.add_trace(go.Scatter(
        x=years, y=wb, mode="lines+markers",
        name="West Bank (excl. East Jerusalem)",
        line=dict(color=PALETTE["terracotta"], width=2.6),
        marker=dict(size=7, color=PALETTE["terracotta"],
                    line=dict(color="white", width=1.2)),
        fill="tozeroy", fillcolor="rgba(185,88,53,0.15)",
        hovertemplate="<b>%{x}</b><br>%{y:.1f}k settlers (West Bank)<extra></extra>",
    ))
    mask = ~np.isnan(ej)
    fig.add_trace(go.Scatter(
        x=years[mask], y=ej[mask], mode="lines+markers",
        name="East Jerusalem",
        line=dict(color=PALETTE["sage"], width=1.8),
        marker=dict(size=5, color=PALETTE["sage"],
                    line=dict(color="white", width=1.0)),
        hovertemplate="<b>%{x}</b><br>%{y:.1f}k settlers (East Jerusalem)<extra></extra>",
    ))

    last_year = int(years[-1])
    last_wb = float(wb[-1])
    multiple = last_wb / float(wb[0])

    markers = [
        (1979, "Elon Moreh ruling"),
        (1993, "Oslo I"),
        (2005, "Gaza disengagement"),
        (2023, "October 7"),
    ]
    shapes, annotations = [], []
    # The political-marker labels sit at 95% of the y-axis maximum so they
    # don't crash into the title; vertical lines run the full plot height.
    y_top = max(np.nanmax(wb), np.nanmax(ej)) * 1.18
    label_y = y_top * 0.93
    for yr, label in markers:
        shapes.append(dict(type="line", x0=yr, x1=yr,
                           y0=0, y1=y_top, xref="x", yref="y",
                           line=dict(color=PALETTE["ink_soft"], width=0.7, dash="dot")))
        annotations.append(dict(x=yr, y=label_y, xref="x", yref="y",
                                text=label, showarrow=False,
                                font=dict(size=10, color=PALETTE["ink_soft"]),
                                textangle=-90, xanchor="left", yanchor="top"))

    annotations.append(dict(
        x=last_year, y=last_wb,
        text=f"<b>{last_year}: ~{int(last_wb)}k settlers</b><br>"
             f"<span style='color:{PALETTE['terracotta']}'>{multiple:.0f}× the 1972 figure</span>",
        showarrow=True, arrowhead=0, ax=-100, ay=-30,
        font=dict(size=11, color=PALETTE["terracotta"]),
        align="left", bgcolor="rgba(245,240,230,0.9)",
        bordercolor=PALETTE["rule"], borderwidth=1, borderpad=6,
    ))
    annotations.append(_attribution(
        "Source: compiled from Peace Now, FMEP, Israeli CBS. "
        "Outpost residents (~20–30k) excluded. 2025 figure: CBS Population Registry."))

    fig.update_layout(**_base_layout(
        f"Israeli settler population in the West Bank, {int(years[0])}–{last_year}",
        height=580,
    ))
    fig.update_layout(shapes=shapes, annotations=annotations)
    fig.update_xaxes(title="", gridcolor=PALETTE["rule"], zeroline=False,
                     range=[int(years[0]) - 1, last_year + 1])
    fig.update_yaxes(title="Settlers (thousands)",
                     gridcolor=PALETTE["rule"], zeroline=False,
                     range=[0, y_top])
    _write(fig, "settler_population")


# 2. Annual civilian-targeting events with harvest-season split
def fig_annual_targeting_harvest() -> None:
    print("[i2] annual targeting + harvest split ...")
    df = _load_acled()
    df = df[df["event_type"] == "civilian_targeting"].copy()
    df["is_harvest"] = df["month"].isin(HARVEST_MONTHS)
    annual = (df.groupby(["year", "is_harvest"])["events"]
              .sum().unstack(fill_value=0)
              .rename(columns={True: "harvest", False: "rest"}))
    years = annual.index.tolist()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=years, y=annual["rest"].values,
        name="Rest of year",
        marker=dict(color=PALETTE["sage"], line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>Rest of year: %{y:,} events<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=years, y=annual["harvest"].values,
        name="October–November (olive harvest)",
        marker=dict(color=PALETTE["terracotta"], line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>Harvest months: %{y:,} events<extra></extra>",
    ))
    fig.update_layout(**_base_layout(
        f"Civilian-targeting events in the West Bank, {int(min(years))}–{int(max(years))}",
        "October–November olive harvest in terracotta; rest of year in sage.",
        height=540,
    ))
    fig.update_layout(barmode="stack",
                      annotations=[_attribution(
                          "Source: ACLED monthly aggregates via HDX")])
    fig.update_xaxes(title="", gridcolor=PALETTE["rule"], dtick=1,
                     tickfont=dict(size=11))
    fig.update_yaxes(title="Reported events", gridcolor=PALETTE["rule"], zeroline=False)
    _write(fig, "annual_targeting_harvest")


# 3. Perpetrator breakdown over time
def fig_perpetrator_breakdown() -> None:
    print("[i3] perpetrator breakdown ...")
    df = _load_events()
    if df is None:
        print("  [skip] event-level parquet not present")
        return
    pal = df[df["targets_palestinian_civilians"]].copy()

    def bucket(p):
        if p == "Settlers": return "Settlers"
        if p == "Israeli state forces": return "Israeli state forces"
        if p == "Other Israeli actor": return "Other Israeli (civilians, unidentified)"
        return "Other / Palestinian"
    pal["bucket"] = pal["perpetrator"].apply(bucket)

    annual = (pal.groupby(["year", "bucket"]).size().unstack(fill_value=0))
    order = ["Israeli state forces", "Settlers",
             "Other Israeli (civilians, unidentified)", "Other / Palestinian"]
    order = [c for c in order if c in annual.columns]
    annual = annual[order]
    color_map = {
        "Israeli state forces":                    PALETTE["olive_deep"],
        "Settlers":                                PALETTE["terracotta"],
        "Other Israeli (civilians, unidentified)": PALETTE["sage"],
        "Other / Palestinian":                     PALETTE["gold"],
    }

    years = annual.index.tolist()
    fig = go.Figure()
    for col in order:
        fig.add_trace(go.Bar(
            x=years, y=annual[col].values, name=col,
            marker=dict(color=color_map[col], line=dict(width=0)),
            hovertemplate=f"<b>%{{x}}</b><br>{col}: %{{y:,}} events<extra></extra>",
        ))
    fig.update_layout(**_base_layout(
        "Events targeting Palestinian civilians, by perpetrator",
        "ACLED actor-1 classified into four buckets.",
        height=560,
    ))
    fig.update_layout(barmode="stack",
                      annotations=[_attribution(
                          "Source: ACLED event-level export · West Bank")])
    fig.update_xaxes(title="", gridcolor=PALETTE["rule"], dtick=1,
                     tickfont=dict(size=11))
    fig.update_yaxes(title="Events per year", gridcolor=PALETTE["rule"], zeroline=False)
    _write(fig, "perpetrator_breakdown")


# 4. Fatalities by event type (stacked area)
def fig_fatalities_by_event_type() -> None:
    print("[i4] fatalities by event type ...")
    df = _load_acled()
    pivot = (df.groupby(["year", "event_type"])["fatalities"]
             .sum().unstack(fill_value=0))
    # We exclude the demonstrations band: ACLED records 0 fatalities under
    # protests/riots for the West Bank in this period because incidents that
    # begin as stone-throwing demonstrations and end with IDF live fire are
    # re-coded by ACLED as Battles (and thus land in political_violence).
    # A flat-zero band would only add visual noise; the prose under the
    # chart calls this out explicitly.
    order = [c for c in ["political_violence", "civilian_targeting"]
             if c in pivot.columns]
    pivot = pivot[order]

    label_map = {
        "civilian_targeting": "Civilian targeting",
        "political_violence": "Political violence",
    }
    color_map = {
        "civilian_targeting": PALETTE["terracotta"],
        "political_violence": PALETTE["olive_deep"],
    }

    years = pivot.index.tolist()
    fig = go.Figure()
    for col in order:
        fig.add_trace(go.Scatter(
            x=years, y=pivot[col].values, mode="lines",
            name=label_map[col], stackgroup="one",
            line=dict(color=color_map[col], width=0.5),
            fillcolor=color_map[col],
            hovertemplate=f"<b>%{{x}}</b><br>{label_map[col]}: %{{y:,}} fatalities<extra></extra>",
        ))
    fig.update_layout(**_base_layout(
        "Recorded West Bank fatalities by event type",
        "Stacked annual fatalities. ACLED's third bucket (Demonstrations) carries zero fatalities in this period; see prose below.",
        height=540,
    ))
    fig.update_layout(annotations=[_attribution(
        "Source: ACLED monthly aggregates · West Bank")])
    fig.update_xaxes(title="", gridcolor=PALETTE["rule"], dtick=1,
                     tickfont=dict(size=11))
    fig.update_yaxes(title="Fatalities per year", gridcolor=PALETTE["rule"], zeroline=False)
    _write(fig, "fatalities_by_event_type")


# 5. Settlements per governorate vs civilian-targeting events
def fig_settlements_vs_events() -> None:
    print("[i5] settlements vs events scatter ...")
    settlements = pd.read_csv(PROC / "settlements_by_governorate.csv")
    acled = _load_acled()
    events = (acled[acled["event_type"] == "civilian_targeting"]
              .groupby("governorate")["events"].sum().reset_index()
              .rename(columns={"events": "ct_events"}))
    df = events.merge(settlements, on="governorate", how="left").fillna(0)

    r = df["settlement_count"].corr(df["ct_events"]) if len(df) > 2 else float("nan")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["settlement_count"], y=df["ct_events"], mode="markers+text",
        marker=dict(size=16, color=PALETTE["olive_deep"],
                    line=dict(color="white", width=2)),
        text=df["governorate"],
        textposition="top center",
        textfont=dict(size=11, color=PALETTE["ink_soft"]),
        customdata=df[["governorate", "settlement_count", "ct_events"]].values,
        hovertemplate=("<b>%{customdata[0]}</b><br>"
                       "Settlements: %{customdata[1]:,}<br>"
                       "Civilian-targeting events: %{customdata[2]:,}<extra></extra>"),
        showlegend=False,
        cliponaxis=False,
    ))
    fig.update_layout(**_base_layout(
        "Settlements per governorate vs civilian-targeting events",
        f"Pearson r = {r:.2f} across the West Bank's eleven governorates.",
        height=620,
    ))
    # The scatter has no legend, so the default attribution position (y=-0.32,
    # which assumes the legend takes up the upper part of the bottom margin)
    # falls outside the chart. Override the bottom margin and the attribution
    # y so the source line sits comfortably inside the visible area.
    fig.update_layout(
        margin=dict(l=80, r=40, t=110, b=90),
        annotations=[dict(
            text=f"<span style='font-size:10px;color:{PALETTE['ink_soft']}'>"
                 "Sources: Peace Now built-up settlements (HDX). ACLED monthly aggregates."
                 "</span>",
            xref="paper", yref="paper", x=1.0, y=-0.16,
            xanchor="right", yanchor="top", showarrow=False)],
    )
    # Pad the axes a bit so the governorate labels don't kiss the chart edges.
    x_max = float(df["settlement_count"].max())
    y_max = float(df["ct_events"].max())
    fig.update_xaxes(title="Israeli settlements (count, Peace Now)",
                     gridcolor=PALETTE["rule"], zeroline=False,
                     range=[-x_max * 0.06, x_max * 1.12])
    fig.update_yaxes(title="Civilian-targeting events 2016–2026 (ACLED)",
                     gridcolor=PALETTE["rule"], zeroline=False,
                     range=[-y_max * 0.04, y_max * 1.15])
    _write(fig, "settlements_vs_events")


# 6. Settlement-proximity histogram (the strongest finding)
def fig_settlement_proximity() -> None:
    print("[i6] settlement-proximity histogram ...")
    import geopandas as gpd
    df = _load_events()
    if df is None:
        print("  [skip] event-level parquet not present")
        return
    pal = df[df["targets_palestinian_civilians"]].copy()
    pal = pal.dropna(subset=["latitude", "longitude"])
    pal = pal[(pal["latitude"].between(31.0, 33.0)) &
              (pal["longitude"].between(34.5, 36.0))]
    pts = gpd.GeoDataFrame(
        pal[["perpetrator"]],
        geometry=gpd.points_from_xy(pal["longitude"], pal["latitude"]),
        crs=4326,
    ).to_crs(2039)
    settlements = gpd.read_file(PROC / "settlements.gpkg").to_crs(2039)
    sett_union = settlements.geometry.union_all()
    dists = pts.geometry.distance(sett_union).values / 1000.0  # km

    median = float(np.median(dists))
    pct2 = float((dists <= 2).mean() * 100)
    pct5 = float((dists <= 5).mean() * 100)

    bin_edges = np.linspace(0, 10, 41)
    counts, _ = np.histogram(dists, bins=bin_edges)
    centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=centers, y=counts,
        marker=dict(color=PALETTE["olive_deep"],
                    line=dict(color="white", width=0.6)),
        width=0.24,
        hovertemplate="<b>%{x:.2f} km</b><br>%{y:,} events<extra></extra>",
        showlegend=False,
    ))
    # Median line
    fig.add_shape(type="line", x0=median, x1=median, y0=0, y1=counts.max() * 1.05,
                  line=dict(color=PALETTE["terracotta"], width=2.4, dash="dash"))
    fig.update_layout(**_base_layout(
        "How close are these events to a settlement?",
        f"Median distance: {median:.1f} km. {pct2:.0f}% within 2 km, {pct5:.0f}% within 5 km.",
        height=540,
    ))
    fig.update_layout(annotations=[
        dict(x=median + 0.2, y=counts.max() * 0.95,
             text=f"<b>median = {median:.1f} km</b>",
             showarrow=False, font=dict(color=PALETTE["terracotta"], size=12),
             xanchor="left"),
        _attribution(
            f"Source: ACLED event points (n={len(dists):,}, targeting Palestinian civilians) "
            "vs Peace Now settlements · EPSG:2039"),
    ])
    fig.update_xaxes(title="Distance from event to nearest settlement (km)",
                     gridcolor=PALETTE["rule"], zeroline=False, range=[0, 10])
    fig.update_yaxes(title="Events", gridcolor=PALETTE["rule"], zeroline=False)
    _write(fig, "settlement_proximity")


# 7. Damage-type keyword breakdown (horizontal bar)
def fig_damage_breakdown() -> None:
    print("[i7] damage-type breakdown ...")
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

    fig = go.Figure(go.Bar(
        x=list(vals), y=list(labels), orientation="h",
        marker=dict(color=PALETTE["olive_deep"],
                    line=dict(color="white", width=0.4)),
        text=[f"{v:,}" for v in vals],
        textposition="outside",
        textfont=dict(size=11, color=PALETTE["ink_soft"]),
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{x:,} events mention this keyword<extra></extra>",
        showlegend=False,
    ))
    fig.update_layout(**_base_layout(
        "Damage types described in event narratives",
        f"Of {len(pal):,} events targeting Palestinian civilians. Categories overlap.",
        height=560,
    ))
    # No legend on this chart, so override the base bottom margin (which the
    # other charts use to seat the legend) and pull the citation closer to
    # the x-axis.
    fig.update_layout(
        margin=dict(l=180, r=80, t=110, b=90),
        annotations=[dict(
            text=f"<span style='font-size:10px;color:{PALETTE['ink_soft']}'>"
                 "Source: keyword scan of ACLED event-level `notes` field · indicative, not definitive"
                 "</span>",
            xref="paper", yref="paper", x=1.0, y=-0.16,
            xanchor="right", yanchor="top", showarrow=False)],
    )
    # Pad the x-axis on the right so the right-edge data labels (e.g. "5,253"
    # for Homes and property) are not clipped by the plot area edge.
    x_max = float(max(vals))
    fig.update_xaxes(title="", gridcolor=PALETTE["rule"], zeroline=False,
                     range=[0, x_max * 1.13])
    fig.update_yaxes(title="", gridcolor=PALETTE["rule"], zeroline=False)
    _write(fig, "damage_breakdown")


def main() -> None:
    print("Building interactive figures (Plotly HTML)")
    fig_settler_population()
    fig_annual_targeting_harvest()
    fig_perpetrator_breakdown()
    fig_fatalities_by_event_type()
    fig_settlements_vs_events()
    fig_settlement_proximity()
    fig_damage_breakdown()
    print("Done.")
if __name__ == "__main__":
    main()
