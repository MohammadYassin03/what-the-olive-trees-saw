"""Quick inspection of downloaded raw data — not part of the pipeline."""
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

import pandas as pd
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

for fname in ["palestine_civilian_targeting.xlsx",
              "palestine_political_violence.xlsx",
              "palestine_demonstrations.xlsx"]:
    path = RAW / "acled" / fname
    print(f"\n{'='*70}\n{fname}\n{'='*70}")
    xl = pd.ExcelFile(path)
    print("Sheets:", xl.sheet_names)
    for s in xl.sheet_names[:3]:
        df = xl.parse(s)
        print(f"\n-- Sheet: {s}  ({len(df):,} rows, {len(df.columns)} cols) --")
        print("Columns:", list(df.columns))
        print(df.head(5).to_string())
