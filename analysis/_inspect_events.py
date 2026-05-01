import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from pathlib import Path
import pandas as pd

p = Path(__file__).resolve().parents[1] / "data" / "raw" / "acled" / "palestine_events.csv"
df = pd.read_csv(p, low_memory=False)
print(f"rows: {len(df):,}")
print(f"columns ({len(df.columns)}):")
for c in df.columns: print(f"  {c}")
print()
print("event_type counts:")
print(df["event_type"].value_counts().to_string())
print()
print("admin1 counts:")
print(df["admin1"].value_counts().head(10).to_string())
print()
print("year range:", df["year"].min(), "-", df["year"].max())
print()
print("first 2 rows of key columns:")
keys = [c for c in ["event_date","year","disorder_type","event_type","sub_event_type",
                     "actor1","assoc_actor_1","actor2","assoc_actor_2","interaction",
                     "civilian_targeting","admin1","admin2","location","latitude","longitude",
                     "fatalities","notes"] if c in df.columns]
print(df[keys].head(2).to_string())
