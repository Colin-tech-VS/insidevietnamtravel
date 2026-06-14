"""Generate static/images/icon-1024.png from brand marks (1024×1024)."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "images" / "icon-1024.png"
SIZE = 1024

TEAL_DEEP = (15, 51, 48)
TEAL = (27, 77, 74)
TEAL_LIGHT = (42, 107, 102)
GOLD = (196, 160, 83)
GOLD_LIGHT = (212, 184, 106)


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _gradient_bg() -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE))
    px = img.load()
    for y in range(SIZE):
        for x in range(SIZE):
            t = (x / (SIZE - 1) + y / (SIZE - 1)) / 2
            if t < 0.45:
                u = t / 0.45
                c = tuple(_lerp(TEAL_DEEP[i], TEAL[i], u) for i in range(3))
            else:
                u = (t - 0.45) / 0.55
                c = tuple(_lerp(TEAL[i], TEAL_LIGHT[i], u) for i in range(3))
            px[x, y] = c
    return img


def _qbezier(p0, p1, p2, steps: int = 120) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]
        y = u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]
        pts.append((x, y))
    return pts


def main() -> None:
    img = _gradient_bg()
    draw = ImageDraw.Draw(img, "RGBA")

    cx = cy = SIZE // 2
    draw.ellipse(
        (cx - 448, cy - 448, cx + 448, cy + 448),
        outline=(*GOLD, 56),
        width=10,
    )

    arc = _qbezier((176, 656), (512, 176), (848, 656))
    stroke = 52
    for i in range(len(arc) - 1):
        draw.line([arc[i], arc[i + 1]], fill=(*GOLD, 255), width=stroke)

    dot_r = 84
    dot_y = 448
    draw.ellipse(
        (cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r),
        fill=(*GOLD_LIGHT, 255),
    )
    draw.ellipse(
        (cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r),
        outline=(240, 226, 184, 115),
        width=6,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, format="PNG", optimize=True)
    print(f"Wrote {OUT} ({SIZE}x{SIZE})")


if __name__ == "__main__":
    main()
