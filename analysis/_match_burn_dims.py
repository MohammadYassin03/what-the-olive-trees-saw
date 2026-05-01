"""Match dimensions of the two Al-Mughayyir burn photos so the slider aligns.

The before/after JPGs the user pasted in have slightly different aspect ratios
(2.023 vs 1.970). The img-comparison-slider component overlays one image on top
of the other at identical extents , any difference in pixel size or aspect ratio
shows up as a visible mis-alignment when the divider moves.

Strategy:
  1. Pick the *smaller* of the two aspect ratios as the common target. This loses
     a thin horizontal strip from the wider image but keeps the entire vertical
     extent of the taller one.
  2. Center-crop both images to that common aspect ratio.
  3. Resize both to a common target width (the smaller of the two) so their
     pixel dimensions match exactly.
  4. Save back over the originals (after a one-shot backup).
"""
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

import shutil
from pathlib import Path
from PIL import Image

ASSETS = Path(__file__).resolve().parents[1] / "assets" / "img"
BEFORE = ASSETS / "mughayyir-burn-before.jpg"
AFTER  = ASSETS / "mughayyir-burn-after.jpg"
BACKUP = ASSETS / "_originals_burn"


def _center_crop_to_aspect(img: Image.Image, target_aspect: float) -> Image.Image:
    """Center-crop img so its width/height equals target_aspect."""
    w, h = img.size
    a = w / h
    if abs(a - target_aspect) < 1e-4:
        return img
    if a > target_aspect:
        # Image is wider than target , trim horizontal pixels.
        new_w = round(h * target_aspect)
        x0 = (w - new_w) // 2
        return img.crop((x0, 0, x0 + new_w, h))
    # Image is taller than target , trim vertical pixels.
    new_h = round(w / target_aspect)
    y0 = (h - new_h) // 2
    return img.crop((0, y0, w, y0 + new_h))


def main() -> None:
    BACKUP.mkdir(exist_ok=True)
    for src in (BEFORE, AFTER):
        bak = BACKUP / src.name
        if not bak.exists():
            shutil.copy2(src, bak)
            print(f"  backed up {src.name} -> _originals_burn/")

    a = Image.open(BEFORE)
    b = Image.open(AFTER)
    aw, ah = a.size; ba = aw / ah
    bw, bh = b.size; bb = bw / bh
    print(f"  before: {aw}x{ah}  aspect {ba:.4f}")
    print(f"  after : {bw}x{bh}  aspect {bb:.4f}")

    # Common aspect: smaller of the two (preserves the entire vertical extent
    # of the taller image, only trims horizontal from the wider one).
    target_aspect = min(ba, bb)
    print(f"  common aspect: {target_aspect:.4f}")

    a2 = _center_crop_to_aspect(a, target_aspect)
    b2 = _center_crop_to_aspect(b, target_aspect)
    print(f"  before cropped: {a2.size}")
    print(f"  after  cropped: {b2.size}")

    # Resize both to a common width = smaller of the two cropped widths.
    target_w = min(a2.size[0], b2.size[0])
    target_h = round(target_w / target_aspect)
    print(f"  common target:  {target_w}x{target_h}")

    a3 = a2.resize((target_w, target_h), Image.LANCZOS)
    b3 = b2.resize((target_w, target_h), Image.LANCZOS)
    a3.save(BEFORE, "JPEG", quality=92)
    b3.save(AFTER,  "JPEG", quality=92)
    print(f"  wrote matched pair at {target_w}x{target_h}")
    # Aspect ratio for the css attribute
    print(f"  css aspect-ratio:  {target_w} / {target_h}")


if __name__ == "__main__":
    main()
