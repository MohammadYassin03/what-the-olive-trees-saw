"""Compose the social-share preview image (1200×630 PNG) at assets/og-card.png.

Used by the og:image / twitter:image meta tags in _quarto.yml. Designed to
echo the look of the page itself: bone background, terracotta rule, serif type.
"""
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parents[1] / "assets"
OUT = ASSETS / "og-card.png"

W, H = 1200, 630

# Theme colours mirrored from theme.scss
BONE       = (250, 246, 236)
BONE_DARK  = (245, 240, 230)
INK        = (42, 42, 38)
INK_SOFT   = (89, 89, 80)
OLIVE_DEEP = (74, 93, 58)
OLIVE_MID  = (107, 127, 84)
TERRACOTTA = (185, 88, 53)
GOLD       = (201, 169, 97)


def _font(size: int, *, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
    candidates: list[str] = []
    if bold and italic:
        candidates += [r"C:\Windows\Fonts\georgiaz.ttf",
                       r"C:\Windows\Fonts\timesbi.ttf"]
    elif bold:
        candidates += [r"C:\Windows\Fonts\georgiab.ttf",
                       r"C:\Windows\Fonts\timesbd.ttf"]
    elif italic:
        candidates += [r"C:\Windows\Fonts\georgiai.ttf",
                       r"C:\Windows\Fonts\timesi.ttf"]
    candidates += [r"C:\Windows\Fonts\georgia.ttf",
                   r"C:\Windows\Fonts\times.ttf"]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap(d: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words = text.split()
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if d.textbbox((0, 0), test, font=font)[2] <= max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def main() -> None:
    img = Image.new("RGB", (W, H), BONE)
    d = ImageDraw.Draw(img)

    # Subtle vertical gradient (bone → bone_dark) at the top edge for texture.
    for y in range(0, 240):
        t = y / 240.0
        r = int(BONE[0] * (1 - t) + BONE_DARK[0] * t)
        g = int(BONE[1] * (1 - t) + BONE_DARK[1] * t)
        b = int(BONE[2] * (1 - t) + BONE_DARK[2] * t)
        d.line([(0, y), (W, y)], fill=(r, g, b), width=1)

    # Top-left kicker
    kicker_font = _font(20, bold=True)
    kicker = "A DATA-DRIVEN NARRATIVE  ·  DSAN-5200  ·  SPRING 2026"
    d.text((68, 56), kicker, font=kicker_font, fill=OLIVE_DEEP)

    # Title (serif, large, centred-left)
    title_font = _font(96, bold=True)
    title = "What the Olive\nTrees Saw"
    title_y = 110
    for i, line in enumerate(title.split("\n")):
        d.text((68, title_y + i * 110), line, font=title_font, fill=INK)

    # Terracotta rule
    rule_y = 360
    d.rectangle([(68, rule_y), (200, rule_y + 4)], fill=TERRACOTTA)

    # Deck (italic serif)
    deck_font = _font(34, italic=True)
    deck_lines = _wrap(
        d,
        "A data narrative on West Bank settlement expansion, "
        "olive groves, and the violence between them.",
        deck_font,
        max_w=W - 136,
    )
    for i, line in enumerate(deck_lines):
        d.text((68, rule_y + 28 + i * 46), line, font=deck_font, fill=INK_SOFT)

    # Byline (bottom-left)
    byline_font = _font(20, bold=True)
    byline = "MOHAMMAD YASSIN  ·  GEORGETOWN UNIVERSITY"
    d.text((68, H - 56), byline, font=byline_font, fill=OLIVE_DEEP)

    # Right-side ornament: an olive-branch silhouette built from two
    # converging arcs and a row of dots , abstract, not figurative.
    branch_x = W - 280
    branch_y = H // 2
    d.line([(branch_x, branch_y - 180), (branch_x + 220, branch_y + 180)],
           fill=OLIVE_MID, width=4)
    leaf_positions = [
        (branch_x +  20, branch_y - 130),
        (branch_x +  60, branch_y -  70),
        (branch_x + 100, branch_y -  10),
        (branch_x + 140, branch_y +  50),
        (branch_x + 180, branch_y + 110),
    ]
    for cx, cy in leaf_positions:
        # Each "leaf" is a tilted ellipse drawn with two halves.
        d.ellipse([(cx - 36, cy - 12), (cx + 36, cy + 12)],
                  fill=OLIVE_DEEP, outline=None)
        d.ellipse([(cx - 32, cy - 30), (cx + 18, cy)],
                  fill=OLIVE_MID, outline=None)
    # A small terracotta dot at the branch tip , a nod to the headline colour.
    d.ellipse([(branch_x + 214, branch_y + 174),
               (branch_x + 226, branch_y + 186)], fill=TERRACOTTA)
    # Three small gold "olives" along the branch
    for cx, cy in [(branch_x + 70, branch_y -  90),
                   (branch_x + 130, branch_y - 30),
                   (branch_x + 190, branch_y +  90)]:
        d.ellipse([(cx - 7, cy - 7), (cx + 7, cy + 7)], fill=GOLD)

    img.save(OUT, "PNG", optimize=True)
    print(f"  wrote {OUT.relative_to(ASSETS.parent)}  ({W}x{H})")


if __name__ == "__main__":
    main()
