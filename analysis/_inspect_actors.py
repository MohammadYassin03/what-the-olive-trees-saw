import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from pathlib import Path
import pandas as pd

p = Path(__file__).resolve().parents[1] / "data" / "raw" / "acled" / "palestine_events.csv"
df = pd.read_csv(p, low_memory=False)
wb = df[df["admin1"] == "West Bank"].copy()
print(f"West Bank rows: {len(wb):,}")
print()
ct = wb[wb["civilian_targeting"].notna() & (wb["civilian_targeting"] == "Civilian targeting")]
print(f"Civilian targeting events (WB): {len(ct):,}")
print()
print("Top actor1 values in civilian-targeting WB events:")
print(ct["actor1"].value_counts().head(20).to_string())
print()
print("Top sub_event_types in civilian-targeting WB events:")
print(ct["sub_event_type"].value_counts().head(15).to_string())
print()
# Spot-check notes for olive/tree mentions
import re
keys = ["olive","tree","grove","uproot","burn","sheep","livestock","goat","vehicle","home","house","mosque","crop","field","property"]
print("\nKeyword presence in notes (% of WB civilian-targeting events):")
for k in keys:
    pct = ct["notes"].fillna("").str.contains(k, case=False, regex=False).mean() * 100
    print(f"  {k:12s} {pct:5.1f}%  ({int(ct['notes'].fillna('').str.contains(k, case=False, regex=False).sum())} events)")
