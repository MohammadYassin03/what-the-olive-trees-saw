# What the Olive Trees Saw

**DSAN-5200 Final Project · Spring 2026 · Georgetown University**
Author: Mohammad Yassin

A data narrative on West Bank settlement expansion, olive groves, and the violence between them.

**Live site:** https://olives.myassin.georgetown.domains/ *(pending deploy)*

---

## Repository layout

```
.
├── _quarto.yml              Quarto site config
├── index.qmd                Main narrative (what the reader sees)
├── appendix.qmd             Technical appendix (data scientist audience)
├── about.qmd                About + AI-usage log
├── theme.scss               Site-wide SCSS theme (palette, type, layout)
├── styles.css               Supplementary CSS
├── environment.yml          Conda environment spec
│
├── analysis/
│   ├── theme.py             Shared matplotlib theme (mirrors SCSS palette)
│   ├── 01_acquire.py        Download raw data from public sources
│   ├── 02_clean.py          Tidy raw data into data/processed/*.csv
│   ├── 03_analyze.py        Produce static figures + headline stats + Folium maps
│   └── 04_interactive.py    Produce Plotly HTML for the seven main figures
│
├── data/
│   ├── raw/                 (gitignored) raw downloads
│   └── processed/           cleaned CSVs + JSON feeds (small files committed)
│
├── figures/
│   ├── static/              publication PNG/SVG exports of static charts
│   └── hero/                (gitignored) high-res satellite scenes
│
├── interactive/
│   └── linked-view.html     Map ↔ time-series linked view (Leaflet + D3)
│
└── assets/
    └── img/                 Hero image, infographic icons, etc.
```

## Reproducing the pipeline

```bash
# 1. Environment
conda env create -f environment.yml
conda activate olives

# 2. Data
python analysis/01_acquire.py     # downloads what it can; prints manual-download URLs for the rest
python analysis/02_clean.py
python analysis/03_analyze.py

# 3. Site
quarto preview                    # local dev server
quarto render                     # builds _site/
```

## Data sources

| Source | What it provides | Access |
|---|---|---|
| ACLED via HDX | Civilian-targeting events, fatalities, perpetrator | Auto |
| Peace Now via HDX | Built-up settlement boundary polygons | Auto |
| Israeli CBS / Peace Now / FMEP | Annual settler population (1972 to 2025) | Compiled CSV |
| UN OCHA oPt via HDX | Areas A/B/C polygons; Separation Barrier alignment | Auto |
| UN OCHA oPt via HDX | Governorate (admin level 2) boundaries | Auto |
| OpenStreetMap (Geofabrik) | `landuse=orchard` polygons | Auto |

Raw data is **not committed** per course policy and repo-size limits. See `analysis/01_acquire.py` for exact URLs and manual-download instructions.

## Hosting

The rendered site is published via GU Domains to the subdomain `olives.myassin.georgetown.domains`. Root site at `myassin.georgetown.domains` is unaffected.

## License / attribution

See `about.qmd` for the AI-usage log and full source attribution.
