"""Generate placeholder before/after images for the Al-Mughayyir burn slider.

The X-post media that should fill these slots cannot be fetched programmatically
(x.com returns 403 to all unauthenticated requests). The user needs to save the
two images manually from the X post and replace these files in place. The
placeholders below are visually distinct so it is obvious from the rendered
page which slot each file belongs to.
"""
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "assets" / "img"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1600, 900

# Colour palette pulled from theme.scss
OLIVE_DEEP = (74, 93, 58)
TERRACOTTA = (185, 88, 53)
BONE       = (245, 240, 230)
INK        = (42, 42, 38)
INK_SOFT   = (74, 74, 68)


def _font(size: int) -> ImageFont.FreeTypeFont:
    """Best-effort serif font; fall back to PIL default."""
    candidates = [
        r"C:\Windows\Fonts\georgia.ttf",
        r"C:\Windows\Fonts\georgiab.ttf",
        r"C:\Windows\Fonts\times.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _draw(path: Path, label: str, sub: str, accent: tuple[int, int, int], bg: tuple[int, int, int]) -> None:
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    # Accent bar across the bottom
    d.rectangle([(0, H - 18), (W, H)], fill=accent)
    # Cross-hatching to make it visually distinct from real imagery
    for x in range(-H, W, 60):
        d.line([(x, 0), (x + H, H)], fill=(bg[0] - 4, bg[1] - 4, bg[2] - 4), width=1)
    # Label block
    label_font = _font(96)
    sub_font   = _font(36)
    note_font  = _font(28)
    label_bbox = d.textbbox((0, 0), label, font=label_font)
    sub_bbox   = d.textbbox((0, 0), sub,   font=sub_font)
    label_w = label_bbox[2] - label_bbox[0]
    sub_w   = sub_bbox[2]   - sub_bbox[0]
    label_x = (W - label_w) // 2
    sub_x   = (W - sub_w)   // 2
    d.text((label_x, H // 2 - 100), label, fill=accent,    font=label_font)
    d.text((sub_x,   H // 2 + 20),  sub,   fill=INK,       font=sub_font)
    # Filename hint near the bottom
    note = f"Replace this file: assets/img/{path.name}"
    note_bbox = d.textbbox((0, 0), note, font=note_font)
    note_w = note_bbox[2] - note_bbox[0]
    d.text(((W - note_w) // 2, H - 90), note, fill=INK_SOFT, font=note_font)
    img.save(path, "JPEG", quality=88)
    print(f"  wrote {path.name}  ({W}x{H})")


def main() -> None:
    _draw(OUT / "mughayyir-burn-before.jpg", "BEFORE", "Al-Mughayyir grove · pre-attack",  OLIVE_DEEP, BONE)
    _draw(OUT / "mughayyir-burn-after.jpg",  "AFTER",  "Al-Mughayyir grove · post-attack", TERRACOTTA, (240, 232, 220))
    print("Placeholders ready. Replace the two files with the X-post imagery when downloaded.")


if __name__ == "__main__":
    main()
