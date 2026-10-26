"""CHix's box art for the CHGame menu: the title picture with the logo, 128x128, 11 colours.

Reads CHix/Art.h (the 64x64 title picture), doubles it, draws the logo as the game does, and writes
docs/cart.png. Run: python tools/make_boxart.py
"""
import os
import re
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
PAL = [(0, 0, 0), (30, 70, 230), (230, 130, 20), (255, 255, 80), (255, 255, 255), (255, 50, 50), (255, 60, 255),
       (0, 255, 255), (0, 255, 100), (130, 175, 255), (255, 205, 120), (220, 220, 220), (15, 35, 115), (115, 65, 10),
       (90, 90, 90), (150, 30, 150)]
EDGE, Q0, FASTL, FAST, FASTD = 4, 7, 9, 1, 12
GLYPH = [[0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E], [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
         [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x1F], [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11]]
GRAD = [EDGE, Q0, Q0, FASTL, FAST, FAST, FASTD]

text = open(os.path.join(ROOT, 'CHix', 'Art.h')).read()
data = [int(h, 16) for h in re.findall(r'0x([0-9A-Fa-f]{2})', text)]
assert len(data) == 2048
small = [[(data[y * 32 + x // 2] >> (4 * (x & 1))) & 15 for x in range(64)] for y in range(64)]
img = [[small[y // 2][x // 2] for x in range(128)] for y in range(128)]


def rect(x, y, w, h, c):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if 0 <= xx < 128 and 0 <= yy < 128:
                img[yy][xx] = c


def lit(l, r, c):
    return 0 <= r < 7 and 0 <= c < 5 and (GLYPH[l][r] >> (4 - c)) & 1


y0 = 30
for pas in (0, 1):
    for l in range(4):
        for r in range(7):
            for c in range(5):
                if not lit(l, r, c):
                    continue
                bx, by = 9 + l * 28 + c * 5, y0 + r * 5
                if not pas:
                    rect(bx + 2, by + 2, 5, 5, 0)
                    continue
                rect(bx, by, 5, 5, GRAD[r])
                if not lit(l, r - 1, c):
                    rect(bx, by, 5, 1, EDGE)
                if not lit(l, r, c - 1):
                    rect(bx, by, 1, 5, EDGE)
                if not lit(l, r + 1, c):
                    rect(bx, by + 4, 5, 1, FASTD)
                if not lit(l, r, c + 1):
                    rect(bx + 4, by, 1, 5, FASTD)
rect(9, y0 + 38, 110, 1, Q0)

os.makedirs(os.path.join(ROOT, 'docs'), exist_ok=True)
im = Image.new('RGB', (128, 128))
im.putdata([PAL[img[y][x]] for y in range(128) for x in range(128)])
im.save(os.path.join(ROOT, 'docs', 'cart.png'))
print("wrote docs/cart.png,", len({v for row in img for v in row}), "colours")
