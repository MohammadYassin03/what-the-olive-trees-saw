"""
Shared visual theme for all static figures.

Keeps palette, fonts, and figure defaults consistent with the Quarto site's
SCSS theme. Import once at the top of every analysis notebook:

    from analysis.theme import apply_theme, PALETTE, olive_cmap
    apply_theme()
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

PALETTE = {
    "olive_deep":   "#4A5D3A",
    "olive_mid":    "#6B7F54",
    "sage":         "#9BAA85",
    "sage_pale":    "#C8D1B8",
    "bone":         "#F5F0E6",
    "bone_pale":    "#FAF6EC",
    "ink":          "#2A2A26",
    "ink_soft":     "#4A4A44",
    "terracotta":   "#B95835",
    "terracotta_pale": "#D88562",
    "gold":         "#C9A961",
    "rule":         "#D9D2C0",
}

# Ordered list for categorical series (olive primary, terracotta accent)
CATEGORICAL = [
    PALETTE["olive_deep"],
    PALETTE["terracotta"],
    PALETTE["gold"],
    PALETTE["olive_mid"],
    PALETTE["sage"],
    PALETTE["ink_soft"],
]

# Diverging sequential for change maps (loss → gain)
olive_cmap = LinearSegmentedColormap.from_list(
    "olive_diverging",
    [PALETTE["terracotta"], PALETTE["bone"], PALETTE["olive_deep"]],
    N=256,
)

# Sequential for single-variable maps
sage_cmap = LinearSegmentedColormap.from_list(
    "sage_sequential",
    [PALETTE["bone_pale"], PALETTE["sage"], PALETTE["olive_deep"]],
    N=256,
)


def apply_theme() -> None:
    """Apply the olive visual theme as matplotlib rcParams."""
    mpl.rcParams.update({
        # Figure
        "figure.facecolor": PALETTE["bone_pale"],
        "axes.facecolor":   PALETTE["bone_pale"],
        "savefig.facecolor": PALETTE["bone_pale"],
        "figure.dpi":        120,
        "savefig.dpi":       220,
        "figure.figsize":    (9, 5.5),

        # Text / fonts , fall back gracefully if serif missing
        "font.family":       "serif",
        "font.serif":        ["Cormorant Garamond", "Georgia", "DejaVu Serif"],
        "font.size":         12,
        "axes.titlesize":    16,
        "axes.titleweight":  "semibold",
        "axes.titlecolor":   PALETTE["ink"],
        "axes.labelsize":    11,
        "axes.labelcolor":   PALETTE["ink_soft"],
        "xtick.labelsize":   10,
        "ytick.labelsize":   10,
        "xtick.color":       PALETTE["ink_soft"],
        "ytick.color":       PALETTE["ink_soft"],

        # Axes , minimal frame
        "axes.edgecolor":    PALETTE["rule"],
        "axes.linewidth":    0.8,
        "axes.spines.top":   False,
        "axes.spines.right": False,
        "axes.spines.left":  False,

        # Grid
        "axes.grid":         True,
        "axes.grid.axis":    "y",
        "grid.color":        PALETTE["rule"],
        "grid.linestyle":    "-",
        "grid.linewidth":    0.5,
        "grid.alpha":        0.7,

        # Ticks
        "xtick.major.size":  3,
        "ytick.major.size":  0,
        "xtick.major.width": 0.8,

        # Legend
        "legend.frameon":    False,
        "legend.fontsize":   10,

        # Lines
        "lines.linewidth":   2.2,

        # Color cycle
        "axes.prop_cycle":   mpl.cycler(color=CATEGORICAL),
    })


def annotate_source(ax, text: str) -> None:
    """Add a small, consistent source annotation at the bottom right of an axes."""
    ax.figure.text(
        0.98, 0.01, text,
        ha="right", va="bottom",
        fontsize=8, style="italic",
        color=PALETTE["ink_soft"],
        family="sans-serif",
    )


def savefig_pub(fig, path: str, *, pad: float = 0.3) -> None:
    """Save a publication-quality PNG + SVG pair to the figures directory."""
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path + ".png", bbox_inches="tight", pad_inches=pad, dpi=220)
    fig.savefig(path + ".svg", bbox_inches="tight", pad_inches=pad)
