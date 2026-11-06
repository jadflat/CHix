# CHix 1.4.2: the enemy cores, 12x12, drawn straight in the game's FIXED palette indices (0 black, 3 gold, 4 white,
# 6 red, 8 green, 14 slate; 15 = transparent), so they look the same on every stage (make_card.py does not remap them).
# They sit inside the wireframe cage (which is what kills): the old 24x24 cores (sprites/boss_*.png) were bigger than it.
# Run: python tools/paint/paint_cores_v4.py   -> tools/paint/sprites/core_*.png, tools/paint/preview_cores4.png
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'sprites')
# the RGB only matters for previews: make_card.py keeps these indices as they are
PAL = [(4, 4, 12), (17, 10, 38), (58, 29, 92), (255, 200, 40), (255, 255, 255), (190, 215, 255), (255, 70, 70), (0, 230, 255),
       (60, 255, 120), (94, 47, 132), (34, 18, 62), (232, 240, 255), (255, 122, 46), (154, 104, 192), (96, 108, 170), (255, 0, 255)]
HOT = (14, 6, 3, 11)  # shade 0..3: slate, red, gold, near-white (4 = white specular)
TOX = (14, 8, 8, 11)  # slate, slate, green, near-white
N = 12


def inside_poly(x, y, pts):
    c = False
    for i in range(len(pts)):
        (x0, y0), (x1, y1) = pts[i], pts[i - 1]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            c = not c
    return c


def make(maskf, shadef, ramp):
    """maskf(x, y) -> inside; shadef(x, y) -> 0..3 dark to light, 4 specular."""
    px = [[15] * N for _ in range(N)]
    m = [[maskf(x + 0.5, y + 0.5) for x in range(N)] for y in range(N)]
    for y in range(N):
        for x in range(N):
            if m[y][x]:
                s = shadef(x, y)
                px[y][x] = 4 if s == 4 else ramp[s]
            elif any(0 <= x + dx < N and 0 <= y + dy < N and m[y + dy][x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[y][x] = 0                                     # the black outline: it reads on any picture
    return px


def by_light(x, y, cx=5.5, cy=5.5):                              # light from the top left
    d = (x - cx) + (y - cy)
    return 3 if d < -6 else 2 if d < 0 else 1 if d < 6 else 0


def orb(ramp, facet=False):
    def mk(x, y): return (x - 6) ** 2 + (y - 6) ** 2 < 22
    def sh(x, y):
        if (x, y) in ((3, 3), (4, 3)): return 4
        if facet and (x + 2 * y) % 5 == 0 and 2 < x < 10 and 1 < y < 10: return 0
        return by_light(x, y)
    return make(mk, sh, ramp)


def cube(ramp):
    pts = [(6, 1), (11, 3.5), (11, 8.5), (6, 11), (1, 8.5), (1, 3.5)]
    def sh(x, y):
        if (x, y) == (5, 2): return 4
        if y + 0.5 < 6 - abs(x + 0.5 - 6) * 0.5: return 3 if y < 3 else 2   # the top face
        return 1 if x < 6 else 0
    return make(lambda x, y: inside_poly(x, y, pts), sh, ramp)


def octa(ramp):
    pts = [(6, 0.5), (11.5, 6), (6, 11.5), (0.5, 6)]
    def sh(x, y):
        if (x, y) == (4, 4): return 4
        if y < 6: return 3 if x < 6 and x + y < 8 else 2 if x < 6 else 1
        return 1 if x < 6 else 0
    return make(lambda x, y: inside_poly(x, y, pts), sh, ramp)


def pyra(ramp):
    pts = [(6, 0.5), (11.5, 11), (0.5, 11)]
    def sh(x, y):
        if (x, y) == (5, 3): return 4
        if y >= 9: return 0
        return 3 if x < 6 and y < 5 else 2 if x < 6 else 1
    return make(lambda x, y: inside_poly(x, y, pts), sh, ramp)


def prism(ramp):                                                 # a three-sided prism seen end on, a little turned
    pts = [(6, 1), (11.5, 10.5), (0.5, 10.5)]
    inner = [(6, 3.5), (9, 9), (3, 9)]
    def sh(x, y):
        if (x, y) == (5, 5): return 4
        if inside_poly(x + 0.5, y + 0.5, inner): return 3 if y < 6 else 2
        return 1 if x < 6 else 0
    return make(lambda x, y: inside_poly(x, y, pts), sh, ramp)


def hexa(ramp):
    pts = [(3.5, 1), (8.5, 1), (11.5, 6), (8.5, 11), (3.5, 11), (0.5, 6)]
    def sh(x, y):
        if (x, y) == (5, 5): return 4                         # the eye
        if 5 <= x <= 6 and 5 <= y <= 6: return 3
        if (x - 5.5) ** 2 + (y - 5.5) ** 2 < 5: return 0
        return by_light(x, y)
    return make(lambda x, y: inside_poly(x, y, pts), sh, ramp)


def tess(ramp):
    def mk(x, y): return 1 <= x < 11 and 1 <= y < 11
    def sh(x, y):
        if (x, y) == (5, 5): return 4
        if 5 <= x <= 6 and 5 <= y <= 6: return 3
        if 4 <= x <= 7 and 4 <= y <= 7: return 2
        if 3 <= x <= 8 and 3 <= y <= 8: return 0
        if x == y or x + y == 11: return 0
        return by_light(x, y)
    return make(mk, sh, ramp)


CORES = [('core', orb(HOT)), ('cube', cube(HOT)), ('octa', octa(TOX)), ('pyra', pyra(HOT)), ('prism', prism(TOX)),
         ('hex', hexa(HOT)), ('icosa', orb(TOX, True)), ('tess', tess(HOT))]


def save(px, path):
    im = Image.new('P', (N, N))
    im.putpalette([c for rgb in PAL for c in rgb])
    im.putdata([v for row in px for v in row])
    im.save(path)


os.makedirs(OUT, exist_ok=True)
for name, px in CORES:
    save(px, os.path.join(OUT, 'core_%s.png' % name))
prev = Image.new('RGB', (len(CORES) * 14 * 8, 14 * 8), (60, 40, 90))
for i, (name, px) in enumerate(CORES):
    im = Image.new('RGB', (N, N), (60, 40, 90))
    for y in range(N):
        for x in range(N):
            if px[y][x] != 15: im.putpixel((x, y), PAL[px[y][x]])
    prev.paste(im.resize((N * 8, N * 8), Image.Resampling.NEAREST), (i * 14 * 8 + 8, 8))
prev.save(os.path.join(HERE, 'preview_cores4.png'))
print('cores written')
