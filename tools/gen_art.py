"""Draws CHix's title screen art (128x128, the game's 16-colour palette) into CHix/Art.h.

Run: python tools/gen_art.py   (writes CHix/Art.h and out/title_art.png)
Colour indices are the game's (theme 0): 0 black, 1 blue, 3 yellow, 4 white, 5 red, 6 magenta,
7 cyan, 8 green, 9 light blue, 12 dark blue, 14 grey.
"""
import math
import os
import random
from PIL import Image

W = H = 128
img = [[0] * W for _ in range(H)]
rng = random.Random(1981)
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        img[y][x] = c


# deep-space gradient: dark blue dithered in from the bottom
for y in range(H):
    t = max(0.0, (y - 30) / 110.0)
    for x in range(W):
        if BAYER[y & 3][x & 3] / 16.0 < t * 0.55:
            img[y][x] = 12

# stars
for _ in range(95):
    x, y = rng.randrange(W), rng.randrange(0, 100)
    put(x, y, rng.choice([4, 9, 9, 7, 12, 12]))
for _ in range(7):                                   # a few bright four-point stars
    x, y = rng.randrange(4, W - 4), rng.randrange(2, 52)
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        put(x + dx, y + dy, 4 if (dx, dy) == (0, 0) else 9)

# ringed planet, lower right
cx, cy, r = 98, 84, 25


def ring(front):
    for t in range(0, 720):
        a = t * math.pi / 360
        for k, col in ((0, 7), (1, 8), (3, 12)):
            rx, ry = 44 + k, 9 + k * 0.35
            x = cx + rx * math.cos(a)
            y = cy + ry * math.sin(a) - 4
            if (math.sin(a) > 0) == front:
                put(round(x), round(y), col if k != 3 else 12)


ring(False)
for y in range(cy - r, cy + r + 1):
    for x in range(cx - r, cx + r + 1):
        d = math.hypot(x - cx, y - cy)
        if d <= r:
            nx, ny = (x - cx) / r, (y - cy) / r
            nz = math.sqrt(max(0, 1 - nx * nx - ny * ny))
            light = -0.55 * nx - 0.5 * ny + 0.65 * nz
            band = 0.08 * math.sin(y * 0.9 + 3 * math.sin(x * 0.2))
            v = light + band
            col = 4 if v > 1.0 else 9 if v > 0.72 else 1 if v > 0.38 else 12 if v > 0.08 else 0
            if d > r - 1 and light > 0.2:
                col = 7                                     # an atmosphere rim
            put(x, y, col)
ring(True)

# the fighter, left of centre, flying right
def tri(p, a, b, c):
    def s(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
    d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


ox, oy = 12, 66
hull = [((0, 5), (22, 0), (22, 10)), ((6, 5), (12, -6), (18, 3)), ((6, 5), (12, 16), (18, 7))]   # nose, wings
for y in range(oy - 8, oy + 20):
    for x in range(ox - 2, ox + 26):
        for t in hull:
            if tri((x - ox, y - oy), *t):
                put(x, y, 14)
top = [(x, y) for y in range(oy - 8, oy + 20) for x in range(ox - 2, ox + 26)
       if img[y][x] == 14 and img[y - 1][x] != 14]            # light from above: a bright upper edge
for x, y in top:
    put(x, y, 4)
under = [(ox + x, y) for x in range(4, 20) for y in range(oy + 5, oy + 12)
         if img[y][ox + x] == 14 and img[y + 1][ox + x] != 14]
for x, y in under:                                        # a dark underside
    put(x, y, 12)
for dx, dy in ((14, 3), (15, 3), (16, 3), (15, 2)):       # cockpit
    put(ox + dx, oy + dy, 7)
put(ox + 15, oy + 4, 9)
for i in range(12):                                       # engine flame, flowing left
    put(ox - 1 - i, oy + 5, 3 if i < 4 else 6)
    if i < 8:
        put(ox - 1 - i, oy + 4, 6)
        put(ox - 1 - i, oy + 6, 6)
for dx in (-2, -3):
    put(ox + dx, oy + 5, 4)
for i, (dx, dy) in enumerate(((7, 9), (10, 12), (7, 1), (10, -2))):   # wing-tip lights
    put(ox + dx, oy + dy, 5 if i % 2 else 8)

# a far-off station: a ring and a spire
sx, sy = 70, 38
for t in range(0, 360, 4):
    a = math.radians(t)
    put(round(sx + 9 * math.cos(a)), round(sy + 3 * math.sin(a)), 14)
for dy in range(-9, 8):
    put(sx, sy + dy, 14)
    if dy % 4 == 0:
        put(sx + 1, sy + dy, 3)
put(sx, sy - 10, 5)

# skyline with lit windows along the bottom
x = 0
while x < W:
    w = rng.randrange(5, 10)
    h = rng.randrange(7, 22)
    for xx in range(x, min(W, x + w)):
        for yy in range(H - h, H):
            put(xx, yy, 12 if (xx + yy) % 5 else 0)
        put(xx, H - h, 1)
    for xx in range(x + 1, min(W, x + w) - 1, 2):
        for yy in range(H - h + 2, H - 1, 3):
            if rng.random() < 0.45:
                put(xx, yy, rng.choice([3, 3, 7, 4]))
    if rng.random() < 0.4:                                   # an antenna
        put(x + w // 2, H - h - 1, 4)
        put(x + w // 2, H - h - 2, 5)
    x += w + rng.randrange(0, 3)

# write the header and a preview
os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'out'), exist_ok=True)
LUM = {0: 0, 12: 1, 1: 2, 14: 3, 5: 4, 6: 4, 8: 5, 9: 6, 7: 7, 3: 8, 4: 9}   # which pixel survives the halving: the brightest
small = [[max((img[2 * y + dy][2 * x + dx] for dy in (0, 1) for dx in (0, 1)), key=lambda v: LUM.get(v, 2))
          for x in range(64)] for y in range(64)]
data = bytearray()
for y in range(64):
    for x in range(0, 64, 2):
        data.append(small[y][x] | (small[y][x + 1] << 4))       # the left pixel in the low nibble
lines = []
for i in range(0, len(data), 24):
    lines.append("    " + ",".join("0x%02X" % b for b in data[i:i + 24]) + ",")
art = os.path.join(os.path.dirname(__file__), '..', 'CHix', 'Art.h')
with open(art, 'w', newline='') as f:
    f.write("// Generated by tools/gen_art.py: the title screen, 64x64 at 4 bits a pixel, drawn at 2x.\n"
            "#pragma once\n#include <stdint.h>\n\nstatic const uint8_t TITLE_ART[2048] = {\n" + "\n".join(lines) + "\n};\n")
PAL = [(0, 0, 0), (30, 70, 230), (230, 130, 20), (255, 255, 80), (255, 255, 255), (255, 50, 50), (255, 60, 255),
       (0, 255, 255), (0, 255, 100), (130, 175, 255), (255, 205, 120), (220, 220, 220), (15, 35, 115), (115, 65, 10),
       (90, 90, 90), (150, 30, 150)]
im = Image.new('RGB', (64, 64))
im.putdata([PAL[small[y][x]] for y in range(64) for x in range(64)])
im.resize((512, 512), Image.NEAREST).save(os.path.join(os.path.dirname(__file__), '..', 'out', 'title_art.png'))
print("wrote Art.h and out/title_art.png")
