"""Quick check of dimensions for the village before/after photos."""
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from pathlib import Path
from PIL import Image

src = Path(__file__).resolve().parents[1] / "figures" / "static"
for p in sorted(src.glob("*.jpg")):
    with Image.open(p) as im:
        print(f"{p.name:40s}  {im.size[0]}x{im.size[1]}")
