"""scene02 v5: start from v4/scene02.png, keep the sky/skyline/hologram, repaint the
lower half (tram line, three shop fronts with three clear neon signs, wet street with
soft vertical reflections) and give the hologram a continuous cyan outline.
Palette unchanged. Run: python paint_s02_v5.py"""
import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 120, 112
YY, XX = np.mgrid[0:H, 0:W]
B4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])
BAY = B4[YY & 3, XX & 3]

src = Image.open(os.path.join(HERE, 'v4', 'scene02.png'))
P = src.getpalette()[:48]
a = np.array(src).astype(np.int16)
old = a.copy()


def R(x0, y0, x1, y1, c):
    a[max(y0, 0):y1 + 1, max(x0, 0):x1 + 1] = c


def ell(cx, cy, rx, ry):
    return ((XX - cx) / rx) ** 2 + ((YY - cy) / ry) ** 2 <= 1


def sh(m, dx, dy):
    o = np.zeros_like(m)
    ys, yd = (slice(0, H - dy), slice(dy, H)) if dy >= 0 else (slice(-dy, H), slice(0, H + dy))
    xs, xd = (slice(0, W - dx), slice(dx, W)) if dx >= 0 else (slice(-dx, W), slice(0, W + dx))
    o[yd, xd] = m[ys, xs]
    return o


# ------------------------------------------------------------------ hologram outline
CX, TT = 92, 66
hair = ell(CX, 24, 16, 13) | ell(CX, 9, 10, 6.5) | ell(CX - 14, 29, 6, 9) | ell(CX + 14, 29, 6, 9)
face = ell(CX, 33, 10, 12.5) & (YY >= 23)
neck = (XX >= CX - 4) & (XX <= CX + 4) & (YY >= 43) & (YY <= 50) & ~face
# kimono polygon (CX-30,64)(CX-25,56)(CX-9,48)(CX+9,48)(CX+25,56)(CX+30,64)
xl = np.where(YY >= 56, CX - 25 - (YY - 56) * 5 / 8, CX - 9 - (YY - 48) * 16 / 8)
kim = (YY >= 48) & (YY <= TT - 3) & (XX >= np.ceil(xl)) & (XX <= 2 * CX - np.ceil(xl))
fig = hair | face | neck | kim
for y0, sx in ((24, 2), (25, 2), (51, -3), (52, -3)):          # v4's glitch slices
    fig[y0] = np.roll(fig[y0], sx)
rim = (sh(fig, 1, 0) | sh(fig, -1, 0) | sh(fig, 0, 1) | sh(fig, 0, -1)) & ~fig
rim &= YY <= 61
ORN = {3, 4, 6, 11, 12}                                       # hairpins and ornaments stay
# strays: cyan / magenta specks outside figure and rim around the hologram
near = np.zeros_like(fig)
for dy in range(-3, 4):
    for dx in range(-3, 4):
        near |= sh(fig, dx, dy)
stray = near & ~fig & ~rim & np.isin(a, (7, 15)) & (YY < 62)
for y, x in zip(*np.nonzero(stray)):                          # take the darker neighbour colour
    nb = [a[y, x + d] for d in (-2, 2, -1, 1) if 0 <= x + d < W and a[y, x + d] not in (7, 15, 3, 4, 11, 12)]
    a[y, x] = nb[0] if nb else 1
paint = rim & ~np.isin(a, list(ORN))
a[paint] = 7

# ------------------------------------------------------------------ lower half
Y0 = 64
R(0, Y0, W - 1, H - 1, 0)
# far wall behind the tram line: dark teal mass with a soft top edge
R(0, Y0, 61, 71, 1)
R(62, Y0, W - 1, 66, 1)
# projector deck under the hologram
R(62, 64, W - 1, 64, 9)
R(62, 65, W - 1, 65, 2)
R(62, 66, W - 1, 71, 10)
for ex in (CX - 20, CX, CX + 20):                             # three emitters
    R(ex - 1, 63, ex + 1, 63, 2)
    R(ex - 1, 64, ex + 1, 64, 13)
    R(ex, 64, ex, 64, 7)
for x in range(64, W, 6):                                     # deck railing posts
    R(x, 67, x, 71, 2)
R(62, 67, W - 1, 67, 2)
# tram car (left), heading right
TX0, TX1 = 4, 54
R(TX0 + 1, 64, TX1 - 2, 64, 9)                                # roof highlight
R(TX0, 65, TX1, 70, 2)
R(TX0, 70, TX1, 70, 10)
R(TX1 + 1, 66, TX1 + 3, 70, 2)                                # nose
R(TX1 + 1, 65, TX1 + 1, 65, 2)
R(TX1 + 4, 68, TX1 + 4, 70, 10)
R(TX1 + 3, 67, TX1 + 3, 67, 11)                               # headlight
for x in range(TX0 + 2, TX1 - 2, 6):                          # windows: pale glass, lit top row
    R(x, 66, x + 3, 67, 5)
    R(x, 66, x + 3, 66, 11)
R(TX0, 69, TX1 + 3, 69, 7)                                    # cyan belt line
R(TX0 + 24, 66, TX0 + 25, 68, 10)                             # door gap
R(TX0 + 24, 69, TX0 + 25, 69, 13)
for x in (TX0 + 6, TX1 - 8):                                  # bogies
    R(x, 71, x + 4, 71, 10)
# elevated line: beam full width
R(0, 72, W - 1, 72, 9)
R(0, 73, W - 1, 74, 2)
R(0, 75, W - 1, 75, 10)
for x in range(0, W, 4):                                      # beam rivets
    R(x, 74, x, 74, 10)

# street-level buildings 76..94: dark masses with three shop fronts
R(0, 76, W - 1, 94, 1)
for px_ in (30, 80):                                          # beam pillars
    R(px_, 76, px_ + 2, 94, 10)
    R(px_, 76, px_, 94, 2)
    R(px_ + 2, 76, px_ + 2, 94, 0)
# dim upper windows in the dark masses, regular 2x2 grid
for x0, x1 in ((22, 29), (34, 37), (74, 79), (84, 88)):
    for x in range(x0, x1 - 1, 4):
        for y in (78, 82):
            R(x, y, x + 1, y + 1, 10)


def glyph(x, y, rows, c):
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch == '#':
                a[y + j, x + i] = c


G = {  # 5x5 neon kanji-ish strokes
    'a': ["#####", "..#..", "#####", "..#..", "..#.."],
    'b': ["#...#", "#####", "#...#", "#####", "#...#"],
    'c': ["####.", "...#.", "#####", ".#...", ".####"],
    'd': ["..#..", "#####", "..#..", ".#.#.", "#...#"],
    'e': ["#####", "#...#", "#####", "#...#", "#####"],
}

# --- sign 1: tall magenta blade sign (15 flickers in game), left shop
R(3, 76, 11, 93, 15)
R(4, 77, 10, 92, 0)
for k, g in enumerate('abd'):
    glyph(5, 78 + k * 5, G[g][:4], 12)
R(5, 93, 9, 93, 12)                                           # bracket under the blade
R(13, 77, 13, 77, 2)
# shop 1 window 13..27
R(13, 84, 28, 85, 12)                                         # awning
R(13, 86, 28, 86, 6)
for x in range(13, 29, 4):
    R(x, 86, x + 1, 86, 12)
R(13, 87, 28, 94, 10)
R(14, 88, 27, 88, 13)                                         # lit counter edge
R(14, 89, 27, 91, 2)
R(14, 92, 27, 93, 10)
for x in (18, 23):
    R(x, 87, x, 94, 1)

# --- sign 2: wide cyan sign over the middle shop
SX0, SX1 = 37, 73
R(SX0, 77, SX1, 84, 7)
R(SX0 + 1, 78, SX1 - 1, 83, 0)
for k, g in enumerate('ceba'):
    gx = SX0 + 4 + k * 8
    rows = G[g]
    for j in range(4):                                         # 5 wide x 4 tall, squeezed
        for i, ch in enumerate(rows[[0, 1, 2, 4][j]]):
            if ch == '#':
                a[79 + j, gx + i] = 7
R(SX0 + 2, 85, SX0 + 2, 86, 2)                                # hangers
R(SX1 - 2, 85, SX1 - 2, 86, 2)
# shop 2 front
R(36, 87, 74, 87, 9)
R(36, 88, 74, 94, 10)
R(39, 88, 71, 93, 2)
R(39, 88, 71, 88, 13)                                         # cyan-lit shelf line
R(39, 89, 71, 89, 9)
for x in range(39, 72):                                       # warm glow at the counter, ordered dither
    for y in range(90, 94):
        if BAY[y, x] < (y - 89) * 3:
            a[y, x] = 10
for x in (47, 55, 63):                                        # window mullions
    R(x, 88, x, 94, 1)
R(53, 90, 57, 94, 0)                                          # open door
R(53, 90, 57, 90, 1)

# --- sign 3: gold lantern sign, right shop (solid shapes only)
R(108, 76, 116, 92, 3)
R(109, 77, 115, 91, 0)
for k, g in enumerate('eda'):
    glyph(110, 78 + k * 5, G[g][:4], 3)
R(112, 93, 112, 94, 2)
# shop 3 window 90..106
R(90, 84, 106, 85, 13)                                        # awning, cyan-green
R(90, 86, 106, 86, 9)
for x in range(90, 107, 4):
    R(x, 86, x + 1, 86, 13)
R(90, 87, 106, 94, 10)
R(91, 88, 105, 88, 5)
R(91, 89, 105, 91, 9)
R(91, 92, 105, 93, 2)
for x in (96, 101):
    R(x, 87, x, 94, 1)

# ------------------------------------------------------------------ wet street 95..111
R(0, 95, W - 1, 95, 9)                                        # curb highlight
R(0, 96, W - 1, 96, 2)
R(0, 97, W - 1, H - 1, 1)
for y in range(99, H):                                        # darken toward the bottom
    a[y, BAY[y] < (y - 99) * 16 // 10] = 0


def streak(x0, x1, cols, ln, step=2):
    """Soft vertical reflection: one column every `step`, lengths varied per column,
    broken by ripple rows (every 4th) so it reads as wet asphalt, not a grid."""
    for x in range(x0, x1 + 1, step):
        lx = int(ln * (.6 + .4 * (((x * 37) % 11) / 10)))
        for y in range(97, min(97 + lx, H)):
            if (y - 97) % 4 == 3 and y - 97 > 2:
                continue
            k = min((y - 97) * len(cols) // max(lx, 1), len(cols) - 1)
            a[y, x] = cols[k]


streak(4, 10, [15, 12, 12, 2], 13)                            # blade sign
streak(14, 27, [13, 9, 2], 8, 3)                              # shop 1 window
streak(38, 72, [7, 13, 13, 9, 2], 11)                             # cyan sign
streak(91, 105, [9, 2], 7, 3)                                 # shop 3 window
streak(109, 115, [3, 12, 12, 2], 12)                          # gold sign
streak(TX0 + 2, TX1 - 2, [2], 0)
# hologram glow on the wet road under the deck: faint rose columns
streak(78, 104, [12, 2, 10], 8, 3)

out = Image.fromarray(a.astype(np.uint8), 'P')
out.putpalette(P)
out.save(os.path.join(HERE, 'scene02.png'))


def rgb(arr):
    return Image.fromarray(np.array(P, np.uint8).reshape(16, 3)[arr]).resize((480, 448), Image.Resampling.NEAREST)


pv = Image.new('RGB', (970, 448), (30, 30, 30))
pv.paste(rgb(old), (0, 0))
pv.paste(rgb(a), (490, 0))
pv.save(os.path.join(HERE, 'preview_s02v5.png'))
print('done')
