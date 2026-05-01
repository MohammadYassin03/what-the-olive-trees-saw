print("step 1")
import sys
print("step 2")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception as e:
    print("reconfigure failed:", e)
print("step 3")
import pandas as pd
print("step 4")
from pathlib import Path
print("step 5")
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
print("RAW =", RAW)
print("exists:", RAW.exists())
p = RAW / "acled" / "palestine_civilian_targeting.xlsx"
print("file exists:", p.exists())
xl = pd.ExcelFile(p)
print("sheets:", xl.sheet_names)
for s in xl.sheet_names:
    df = xl.parse(s)
    print(f"\n-- {s} --  ({len(df)} rows, {len(df.columns)} cols)")
    print("cols:", list(df.columns))
    if len(df):
        print(df.head(3).to_string())
