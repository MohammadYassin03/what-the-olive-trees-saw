"""Build the inline SVG locator used by the Part V scrollytelling layout.

The SVG sits in a sticky container on the left of the Part V two-column block.
As the reader scrolls into each village, scrollama dispatches a class onto the
container, and CSS targets the village's circle by `id` to highlight it.

The four village circles are emitted with `gid` (which matplotlib serialises
as `id` in the resulting SVG) so the JS can find them by selector.

Output:
    assets/villages_locator.svg

Run:
    conda run -n olives python analysis/_make_villages_locator.py
"""
from __future__ import annotations

import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
PROC = REPO / "data" / "processed"
OUT  = REPO / "assets" / "villages_locator.svg"

# Mirror of theme.scss palette
PAL = {
    "olive_deep": "#4A5D3A",
    "olive_mid":  "#6B7F54",
    "sage":       "#9BAA85",
    "sage_pale":  "#C8D1B8",
    "bone":       "#F5F0E6",
    "bone_pale":  "#FAF6EC",
    "ink":        "#2A2A26",
    "ink_soft":   "#595950",
    "terracotta": "#B95835",
    "rule":       "#D9D2C0",
}

VILLAGES = [
    ("burin",      "Burin",        32.1772, 35.2553),
    ("turmus",     "Turmus Ayya",  32.0317, 35.2858),
    ("mughayyir",  "Al-Mughayyir", 32.0606, 35.3886),
    ("tuwani",     "At-Tuwani",    31.4087, 35.1378),
]


def main() -> None:
    govs = gpd.read_file(PROC / "governorates.gpkg").to_crs(4326)
    sett = gpd.read_file(PROC / "settlements.gpkg").to_crs(4326)

    # Aggressive geometry simplification , this SVG is inlined into the page
    # on every render, so we trade a few pixels of polygon precision for a
    # ~10× reduction in SVG path size. ~110 m at this latitude is invisible
    # at the locator's thumbnail size (~260×420 pt).
    govs["geometry"] = govs.geometry.simplify(0.001, preserve_topology=True)
    # Settlements: union into a single polygon, then simplify. We do not need
    # individual settlement boundaries at this scale, only "where they sit".
    sett_union = sett.geometry.union_all()
    sett_simple = gpd.GeoSeries([sett_union], crs=4326).simplify(0.0005,
                                                                preserve_topology=True)

    fig, ax = plt.subplots(figsize=(4.5, 7.5))
    fig.patch.set_facecolor("none")
    ax.set_facecolor("none")

    # Governorate boundaries , faint olive border, no fill
    govs.plot(ax=ax,
              facecolor=PAL["bone_pale"], edgecolor=PAL["rule"],
              linewidth=0.8, zorder=1)
    # West Bank outline emphasised , outer boundary only
    outline = govs.geometry.union_all().boundary
    gpd.GeoSeries([outline], crs=4326).plot(ax=ax,
        edgecolor=PAL["ink_soft"], linewidth=1.0, zorder=2)
    # Settlements , single unioned polygon, terracotta fill
    sett_simple.plot(ax=ax,
                     facecolor=PAL["terracotta"], edgecolor="none",
                     alpha=0.55, zorder=3)

    # Four village markers , give each a `gid` so the SVG carries `id="..."`.
    # We draw an outer ring (always visible) and an inner dot , the inner dot
    # is what CSS will scale up when the marker becomes active.
    for slug, name, lat, lon in VILLAGES:
        ring = ax.scatter([lon], [lat], s=240,
                          facecolors="none", edgecolors=PAL["olive_deep"],
                          linewidths=2.0, zorder=5)
        ring.set_gid(f"locator-ring-{slug}")
        dot = ax.scatter([lon], [lat], s=70,
                         facecolors=PAL["bone"], edgecolors=PAL["olive_deep"],
                         linewidths=1.5, zorder=6)
        dot.set_gid(f"locator-dot-{slug}")
        # Label text , push slightly to the right of the marker
        text = ax.text(lon + 0.025, lat, name,
                       fontsize=9, color=PAL["ink"],
                       fontweight="600",
                       va="center", ha="left", zorder=7,
                       fontfamily="serif")
        text.set_gid(f"locator-label-{slug}")

    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    # Tighten to the West Bank's bbox plus a small margin
    minx, miny, maxx, maxy = govs.total_bounds
    pad_x = (maxx - minx) * 0.04
    pad_y = (maxy - miny) * 0.02
    ax.set_xlim(minx - pad_x, maxx + pad_x)
    ax.set_ylim(miny - pad_y, maxy + pad_y)
    ax.set_aspect("equal")

    # SVG output, no surrounding white box
    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, format="svg", bbox_inches="tight",
                pad_inches=0.05, transparent=True)
    plt.close(fig)
    print(f"  wrote {OUT.relative_to(REPO)}")
    # Print a summary of the gids we emitted
    for slug, name, _lat, _lon in VILLAGES:
        print(f"    locator-ring-{slug}  /  locator-dot-{slug}  /  locator-label-{slug}  ({name})")


if __name__ == "__main__":
    main()
