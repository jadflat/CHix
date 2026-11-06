"""CHix upgrade art: title.png (128x128) and sprites/*.png with one shared palette.
Run: python tools/paint/paint_sprites.py"""
import math
import os
import random
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SPR = os.path.join(HERE, 'sprites')
os.makedirs(SPR, exist_ok=True)
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def save(img, path, pal):
    flat = []
    for c in pal:
        flat += list(c)
    im = Image.new('P', (len(img[0]), len(img)))
    im.putpalette(flat + [0] * (768 - len(flat)))
    im.putdata([v for r in img for v in r])
    im.save(path)


# ---------------- sprite palette ----------------
SP = [(10, 10, 26), (28, 36, 80), (58, 74, 154), (106, 140, 240), (184, 212, 255), (255, 255, 255),
      (90, 10, 26), (212, 30, 60), (255, 106, 80), (138, 90, 0), (255, 184, 24), (255, 240, 138),
      (10, 138, 138), (56, 232, 232), (138, 144, 168), (255, 0, 255)]
T = 15


def canvas(w, h):
    return [[T] * w for _ in range(h)]


def shade_ramp(lum, x, y, ramp):
    f = max(0, min(0.999, lum)) * (len(ramp) - 1)
    i = int(f)
    return ramp[i + 1] if (f - i) > BAYER[y & 3][x & 3] / 16.0 else ramp[i]


def sphere(c, cx, cy, r, ramp, dith=True):
    for y in range(len(c)):
        for x in range(len(c[0])):
            nx, ny = (x + .5 - cx) / r, (y + .5 - cy) / r
            d = nx * nx + ny * ny
            if d <= 1:
                nz = math.sqrt(1 - d)
                lum = (-nx * .5 - ny * .55 + nz * .7) * .85 + .1
                c[y][x] = shade_ramp(lum, x, y, ramp) if dith else ramp[min(len(ramp) - 1, int(max(0, lum) * len(ramp)))]


def poly(c, pts, col):
    im = Image.new('P', (len(c[0]), len(c)), T)
    ImageDraw.Draw(im).polygon(pts, fill=col)
    d = im.load()
    for y in range(len(c)):
        for x in range(len(c[0])):
            if d[x, y] != T:
                c[y][x] = d[x, y]


def outline(c, col=0):
    h, w = len(c), len(c[0])
    src = [r[:] for r in c]
    for y in range(h):
        for x in range(w):
            if src[y][x] == T:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    X, Y = x + dx, y + dy
                    if 0 <= X < w and 0 <= Y < h and src[Y][X] != T and src[Y][X] != col:
                        c[y][x] = col
                        break


def pset(c, x, y, v):
    if 0 <= y < len(c) and 0 <= x < len(c[0]):
        c[y][x] = v


def L(c, x0, y0, x1, y1, v):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(n + 1):
        pset(c, round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n), v)


def R_(c, x0, y0, x1, y1, v):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            pset(c, x, y, v)


# ---------------- ship ----------------
M = {'o': 0, 'a': 1, 'b': 2, 'c': 3, 'd': 4, 'w': 5, 'r': 7, 'R': 8, 'q': 13, 'Q': 12, 'e': 14, '.': T}
SHIP_HALF = [
    ".......o",
    "......od",
    "......od",
    ".....ocd",
    ".....ocw",
    "....ocqw",
    "....ocqq",
    "...ocdqQ",
    "...ocdbb",
    "..ocddcb",
    ".ocdRcbb",
    "ocdRrbbb",
    "odcRrbaa",
    "oabrrbao",
    "oaoeeaoo",
    ".ooeaoo.",
]
DARK = {5: 4, 4: 3, 3: 2, 2: 1, 8: 7, 7: 6, 13: 12, 14: 2}


def ship(frame):
    c = []
    for r in SHIP_HALF:
        left = [M[ch] for ch in r]
        right = [DARK.get(v, v) for v in reversed(left)]
        row = left + right
        row[7] = left[7]
        row[8] = left[7]
        c.append(row)
    seq = {0: [(13, 11), (14, 10), (15, 8)], 1: [(14, 11), (15, 10)]}
    for y, v in seq[frame]:
        c[y][7] = v
        c[y][8] = v
    return c


# ---------------- spark ----------------
def spark(f):
    c = canvas(12, 12)
    sphere(c, 6, 6, 4.4, [6, 7, 8, 10, 11], False)
    a = f * math.pi / 8
    for k in range(4):
        ang = a + k * math.pi / 2
        for t in (3.6, 4.6, 5.4):
            x, y = 6 + math.cos(ang) * t, 6 + math.sin(ang) * t
            pset(c, int(math.floor(x)), int(math.floor(y)), 11 if t < 4 else 10)
    for x, y in ((4, 4), (5, 4), (4, 5)):
        pset(c, x, y, 5)
    outline(c)
    return c


# ---------------- power-up icons ----------------
def plate(rim, body, glyph_fn):
    c = canvas(12, 12)
    poly(c, [(1, 0), (10, 0), (11, 1), (11, 10), (10, 11), (1, 11), (0, 10), (0, 1)], 1)
    for y in range(12):
        for x in range(12):
            if c[y][x] != T:
                c[y][x] = body[0] if x + y < 14 else body[1]
    glyph_fn(c)
    # dark outline ring, light bevel top-left
    for i in range(1, 11):
        c[0][i] = 0
        c[11][i] = 0
        c[i][0] = 0
        c[i][11] = 0
    for x, y in ((0, 1), (1, 0), (10, 0), (11, 1), (0, 10), (1, 11), (10, 11), (11, 10)):
        c[y][x] = 0
    for x, y in ((0, 0), (11, 0), (0, 11), (11, 11)):
        c[y][x] = T
    for i in range(2, 10):
        c[1][i] = rim[0]
        c[i][1] = rim[0]
    c[1][1] = rim[0]
    for i in range(2, 11):
        c[10][i] = rim[1]
        c[i][10] = rim[1]
    return c


def g_freeze(c):
    for a in range(4):
        ang = a * math.pi / 4
        L(c, round(5.5 - 3.6 * math.cos(ang)), round(5.5 - 3.6 * math.sin(ang)),
          round(5.5 + 3.6 * math.cos(ang)), round(5.5 + 3.6 * math.sin(ang)), 13)
    R_(c, 5, 5, 6, 6, 5)


def g_speed(c):
    poly(c, [(7, 2), (3, 6), (6, 6), (4, 9), (9, 5), (6, 5), (8, 2)], 10)
    for x, y in ((6, 3), (5, 4), (4, 5), (5, 5)):
        pset(c, x, y, 11)
    L(c, 4, 9, 8, 5, 9)


def g_laser(c):
    R_(c, 5, 2, 6, 9, 7)
    R_(c, 2, 5, 9, 6, 7)
    R_(c, 5, 3, 5, 8, 8)
    R_(c, 3, 5, 8, 5, 8)
    R_(c, 5, 5, 6, 6, 5)
    pset(c, 4, 4, 11)


def g_shield(c):
    poly(c, [(2, 2), (9, 2), (9, 6), (5, 9), (2, 6)], 13)
    poly(c, [(3, 3), (8, 3), (8, 6), (5, 8), (3, 6)], 3)
    R_(c, 3, 3, 4, 5, 4)
    R_(c, 6, 5, 8, 5, 2)
    L(c, 5, 3, 5, 7, 12)


def g_slow(c):
    sphere(c, 6, 6, 4.2, [1, 2, 3, 4, 5], False)
    L(c, 6, 6, 6, 3, 0)
    L(c, 6, 6, 8, 7, 0)
    for x, y in ((6, 2), (6, 9), (2, 6), (9, 6)):
        pset(c, x, y, 10)


def g_bonus(c):
    pts = [(5.5, 1.5), (7, 4.5), (10, 4.8), (8, 7), (8.8, 10), (5.5, 8.4), (2.5, 10), (3.2, 7), (1, 4.8), (4, 4.5)]
    poly(c, [(int(round(x)), int(round(y))) for x, y in pts], 10)
    R_(c, 5, 3, 5, 6, 11)
    R_(c, 3, 5, 4, 5, 11)
    pset(c, 4, 4, 5)
    pset(c, 7, 8, 9)
    pset(c, 8, 9, 9)


def g_x2(c):
    L(c, 2, 3, 4, 7, 11)
    L(c, 4, 3, 2, 7, 11)
    R_(c, 6, 3, 9, 3, 10)
    pset(c, 9, 4, 10)
    R_(c, 6, 5, 9, 5, 10)
    pset(c, 6, 6, 10)
    R_(c, 6, 7, 9, 7, 10)
    R_(c, 3, 9, 8, 9, 9)


def g_ghost(c):
    poly(c, [(2, 3), (3, 1), (8, 1), (9, 3), (9, 9), (8, 8), (6, 9), (5, 8), (3, 9), (2, 8)], 5)
    for y in range(4, 9):
        for x in range(2, 10):
            if c[y][x] == 5 and (x >= 7 or y >= 8):
                c[y][x] = 4
    R_(c, 3, 4, 4, 5, 0)
    R_(c, 6, 4, 7, 5, 0)
    pset(c, 3, 4, 13)
    pset(c, 6, 4, 13)


def g_bomb(c):
    # a round black bomb with a lit fuse
    for y, x0, x1 in ((4, 4, 7), (5, 3, 8), (6, 2, 8), (7, 2, 8), (8, 2, 8), (9, 3, 7)):
        R_(c, x0, y, x1, y, 1)
    for x, y in ((3, 5), (2, 6), (2, 7), (3, 8)):
        pset(c, x, y, 2)
    pset(c, 3, 6, 3)
    pset(c, 4, 5, 3)
    R_(c, 3, 10, 7, 10, 0)
    R_(c, 8, 5, 8, 9, 0)
    L(c, 7, 4, 8, 2, 14)
    pset(c, 9, 1, 11)
    pset(c, 8, 1, 10)
    pset(c, 10, 2, 10)
    pset(c, 9, 2, 5)


def g_life(c):
    # a heart: salmon, pale highlight top left, crimson right and bottom
    rows = [".XX.XX.", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."]
    for ry, row in enumerate(rows):
        for rx, ch in enumerate(row):
            if ch == "X":
                pset(c, 3 + rx, 3 + ry, 8)
    for x, y in ((4, 3), (3, 4), (4, 4)):
        pset(c, x, y, 11)
    for x, y in ((9, 4), (9, 5), (8, 6), (7, 7), (6, 8), (8, 5)):
        pset(c, x, y, 7)


PUS = [
    ((4, 12), [1, 0], g_freeze), ((11, 9), [9, 1], g_speed),
    ((8, 6), [1, 0], g_laser), ((4, 2), [1, 0], g_shield),
    ((4, 2), [1, 0], g_slow), ((11, 9), [9, 1], g_bonus),
    ((11, 9), [6, 1], g_x2), ((4, 14), [1, 0], g_ghost),
    ((8, 6), [9, 6], g_bomb), ((8, 7), [6, 1], g_life)]

# ---------------- bosses (24x24) ----------------
N = 24


def faceted(polys):
    c = canvas(N, N)
    for pts, col in polys:
        poly(c, pts, col)
    return c


def b_core():
    c = canvas(N, N)
    sphere(c, 12, 12, 10.5, [0, 1, 12, 2, 13, 3, 4])
    sphere(c, 12, 12, 4.2, [9, 10, 11, 5])
    for a in range(8):
        ang = a * math.pi / 4
        pset(c, 12 + int(round(math.cos(ang) * 6.6)) - (1 if math.cos(ang) < 0 else 0),
             12 + int(round(math.sin(ang) * 6.6)) - (1 if math.sin(ang) < 0 else 0), 3)
    for x, y in ((6, 6), (7, 5), (6, 7)):
        pset(c, x, y, 5)
    return c


def b_cube():
    c = faceted([([(3, 7), (12, 2), (21, 7), (12, 12)], 4), ([(3, 7), (12, 12), (12, 22), (3, 16)], 3),
                 ([(12, 12), (21, 7), (21, 16), (12, 22)], 2)])
    L(c, 4, 7, 12, 3, 5)
    L(c, 12, 12, 12, 21, 1)
    L(c, 3, 8, 3, 16, 4)
    for x, y in ((7, 12), (8, 13), (16, 14), (17, 13)):
        pset(c, x, y, 13 if x < 12 else 12)
    return c


def b_octa():
    c = faceted([([(12, 1), (3, 12), (12, 12)], 4), ([(12, 1), (21, 12), (12, 12)], 3),
                 ([(3, 12), (12, 22), (12, 12)], 2), ([(21, 12), (12, 22), (12, 12)], 1)])
    L(c, 11, 3, 5, 11, 5)
    L(c, 3, 12, 21, 12, 13)
    return c


def b_pyra():
    c = faceted([([(12, 2), (2, 20), (12, 17)], 11), ([(12, 2), (12, 17), (22, 20)], 10),
                 ([(2, 20), (12, 17), (22, 20), (12, 22)], 9)])
    L(c, 11, 4, 4, 18, 5)
    L(c, 12, 4, 12, 16, 8)
    return c


def b_prism():
    return faceted([([(7, 3), (17, 3), (22, 12), (17, 21), (7, 21), (2, 12)], 3),
                    ([(7, 3), (17, 3), (12, 12)], 4), ([(2, 12), (7, 3), (12, 12)], 3),
                    ([(17, 3), (22, 12), (12, 12)], 2), ([(2, 12), (7, 21), (12, 12)], 2),
                    ([(12, 12), (7, 21), (17, 21)], 1), ([(22, 12), (17, 21), (12, 12)], 1),
                    ([(10, 10), (14, 10), (14, 14), (10, 14)], 8)])


def b_hex():
    pts = [(int(round(11.5 + 10.5 * math.cos(math.pi / 3 * k))), int(round(11.5 + 10.5 * math.sin(math.pi / 3 * k))))
           for k in range(6)]
    c = faceted([([(12, 12), pts[k], pts[(k + 1) % 6]], [14, 5, 4, 14, 2, 3][k]) for k in range(6)])
    s = canvas(N, N)
    sphere(s, 12, 12, 3.8, [1, 12, 13, 5])
    for y in range(N):
        for x in range(N):
            if s[y][x] != T:
                c[y][x] = s[y][x]
    return c


def b_icosa():
    c = canvas(N, N)
    sphere(c, 12, 12, 10.5, [1, 2, 3, 4, 5])
    for x0, y0, x1, y1 in [(12, 2, 5, 15), (12, 2, 19, 15), (5, 15, 19, 15), (12, 22, 5, 9), (12, 22, 19, 9), (5, 9, 19, 9)]:
        n = max(abs(x1 - x0), abs(y1 - y0))
        for i in range(n + 1):
            x = round(x0 + (x1 - x0) * i / n)
            y = round(y0 + (y1 - y0) * i / n)
            if c[y][x] != T:
                c[y][x] = 1 if c[y][x] <= 3 else 2
    for x, y in ((8, 6), (9, 5), (8, 7), (7, 8)):
        pset(c, x, y, 5)
    return c


def b_tess():
    c = canvas(N, N)
    R_(c, 2, 2, 21, 21, 9)
    R_(c, 2, 2, 20, 3, 11)
    R_(c, 2, 2, 3, 20, 11)
    R_(c, 4, 4, 19, 19, 1)
    L(c, 4, 4, 8, 8, 10)
    L(c, 19, 4, 15, 8, 9)
    L(c, 4, 19, 8, 15, 10)
    L(c, 19, 19, 15, 15, 9)
    R_(c, 8, 8, 15, 15, 2)
    R_(c, 8, 8, 15, 8, 4)
    R_(c, 8, 8, 8, 15, 4)
    R_(c, 10, 10, 13, 13, 13)
    R_(c, 10, 10, 11, 11, 5)
    R_(c, 12, 12, 13, 13, 12)
    return c


BOSS = {'core': b_core, 'cube': b_cube, 'octa': b_octa, 'pyra': b_pyra, 'prism': b_prism,
        'hex': b_hex, 'icosa': b_icosa, 'tess': b_tess}

# ---------------- title ----------------
TP = [(5, 6, 26), (14, 18, 64), (26, 34, 104), (46, 58, 160), (90, 42, 150), (154, 60, 160), (10, 90, 120),
      (26, 138, 168), (64, 200, 216), (160, 240, 240), (255, 255, 255), (106, 58, 0), (192, 120, 8),
      (255, 192, 32), (255, 240, 144), (120, 128, 190)]


def title():
    W = 128
    img = [[0] * W for _ in range(W)]
    rng = random.Random(7)
    for y in range(W):
        for x in range(W):
            v = (math.sin(x * .07 + y * .03) + math.sin(y * .09 - x * .02 + 1.3) + math.sin((x + y) * .05 + 2) + 3) / 6
            v *= 0.35 + 0.65 * max(0, 1 - abs(y - 52) / 60)
            if y > 100:
                v *= max(0.0, 1 - (y - 100) / 16)
            lvl = v * 3.2
            i = int(lvl)
            lv = min(3, i + (1 if (lvl - i) > BAYER[y & 3][x & 3] / 16 else 0))
            if lv <= 1:
                img[y][x] = lv
            elif lv == 2:
                img[y][x] = 2 if (x * 3 + y) % 7 else 4
            else:
                img[y][x] = 3 if (x + y * 2) % 5 else 4
    for _ in range(110):
        x, y = rng.randrange(W), rng.randrange(0, 122)
        if img[y][x] <= 4:
            img[y][x] = rng.choice([15, 15, 8, 9, 10, 3])
    for _ in range(9):
        x, y = rng.randrange(4, W - 4), rng.randrange(3, 100)
        img[y][x] = 10
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            img[y + dy][x + dx] = 15 if (x + dx) % 2 else 9
    cx, cy, r = 86, 82, 24

    def ringpix(front):
        for t in range(0, 2880):
            a = t * math.pi / 1440
            if (math.sin(a) > 0) != front:
                continue
            for k in range(4):
                rx, ry = 47 + k * 1.2, 9 + k * 0.5
                x, y = rx * math.cos(a), ry * math.sin(a)
                xr = x * math.cos(-.28) - y * math.sin(-.28) + cx
                yr = x * math.sin(-.28) + y * math.cos(-.28) + cy
                X, Y = int(round(xr)), int(round(yr))
                if 0 <= X < W and 0 <= Y < W:
                    img[Y][X] = (9, 8, 7, 6)[k] if ((X + Y) % 3 or k) else 10

    ringpix(False)
    ramp = [0, 6, 6, 7, 7, 8, 8, 9]
    for y in range(cy - r - 1, cy + r + 2):
        for x in range(cx - r - 1, cx + r + 2):
            nx, ny = (x + .5 - cx) / r, (y + .5 - cy) / r
            d = nx * nx + ny * ny
            if d <= 1:
                nz = math.sqrt(1 - d)
                lum = max(0, (-nx * .55 - ny * .5 + nz * .75) * .95 + 0.05)
                lum += math.sin(ny * 9 + nx * 1.5 + math.sin(nx * 5) * .6) * .09
                f = max(0, min(.999, lum)) * (len(ramp) - 1)
                i = int(f)
                img[y][x] = ramp[i + 1] if f - i > BAYER[y & 3][x & 3] / 16 else ramp[i]
                if .93 < d and nx + ny < -.4:
                    img[y][x] = 9
    ringpix(True)
    Y0, Y1, th = 14, 50, 9

    def Cf(d, ox):
        d.ellipse([ox, Y0, ox + 26, Y1], fill=1)
        d.ellipse([ox + th, Y0 + th, ox + 26 - th, Y1 - th], fill=0)
        d.rectangle([ox + 14, Y0 + 11, ox + 27, Y1 - 11], fill=0)

    def Hf(d, ox):
        d.rectangle([ox, Y0, ox + th, Y1], fill=1)
        d.rectangle([ox + 20 - th, Y0, ox + 20, Y1], fill=1)
        d.rectangle([ox, (Y0 + Y1) // 2 - 4, ox + 20, (Y0 + Y1) // 2 + 4], fill=1)

    def If(d, ox):
        d.rectangle([ox + 4, Y0, ox + 4 + th, Y1], fill=1)
        d.rectangle([ox, Y0, ox + 17, Y0 + 7], fill=1)
        d.rectangle([ox, Y1 - 7, ox + 17, Y1], fill=1)

    def Xf(d, ox):
        d.polygon([(ox, Y0), (ox + 10, Y0), (ox + 24, Y1), (ox + 14, Y1)], fill=1)
        d.polygon([(ox + 24, Y0), (ox + 14, Y0), (ox, Y1), (ox + 10, Y1)], fill=1)

    full = Image.new('1', (W, W), 0)
    dr = ImageDraw.Draw(full)
    for fn, ox in ((Cf, 6), (Hf, 38), (If, 66), (Xf, 94)):
        fn(dr, ox)
    m = full.load()

    def on(x, y):
        return 0 <= x < W and 0 <= y < W and m[x, y]

    for y in range(W):
        for x in range(W):
            if not on(x, y):
                if any(on(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    img[y][x] = 0
                elif (on(x - 2, y - 2) or on(x - 3, y - 3)) and BAYER[y & 3][x & 3] < 11:
                    img[y][x] = 0
    for y in range(W):
        for x in range(W):
            if on(x, y):
                t = (y - Y0) / (Y1 - Y0)
                base = 14 if t < .30 else 13 if t < .55 else 12 if t < .8 else 11
                if .42 < t < .50 and (x + y) % 2 == 0:
                    base = 14 if t < .46 else 13
                if not on(x - 1, y) or not on(x, y - 1):
                    base = 10 if (not on(x, y - 1) and (x + y) % 2 == 0) else 14
                if not on(x + 1, y) or not on(x, y + 1):
                    base = 11
                img[y][x] = base
    for x, y in ((12, 18), (43, 18), (71, 18), (99, 18)):
        img[y][x] = 10
        img[y][x + 1] = 10
    return img


SHIP12 = [
    ".....oo.....", "....o44o....", "...o3ww3o...", "...o3cc3o...", "..o33dd33o..", ".o3B3gg3B3o.",
    "o33B3gg3B33o", "o3r23gg32r3o", "orR2gggg2Rro", "o..oggggo..o", "....oFFo....", ".....FF....."]
M12 = {'o': 0, 'g': 1, '2': 2, '3': 3, '4': 4, 'B': 4, 'w': 5, 'r': 7, 'R': 8, 'd': 12, 'c': 13, 'F': 10, 'f': 11, '.': T}


def ship12(frame):
    c = []
    for y, r in enumerate(SHIP12):
        row = [M12[ch] for ch in r]
        if y >= 10:                                   # the thruster flame flickers between two shapes
            row = [(11 if frame and v == 10 else v) for v in row]
            if frame and y == 11:
                row = [T, T, T, T, 10, 11, 11, 10, T, T, T, T]
        c.append(row)
    return c


def main():
    save(title(), os.path.join(HERE, 'title.png'), TP)
    items = {'ship0': ship12(0), 'ship1': ship12(1)}
    for f in range(4):
        items['spark%d' % f] = spark(f)
    for i, (rim, body, fn) in enumerate(PUS):
        items['pu%d' % i] = plate(rim, body, fn)
    for n, fn in BOSS.items():
        c = fn()
        outline(c)
        items['boss_' + n] = c
    for n, c in items.items():
        save(c, os.path.join(SPR, n + '.png'), SP)
    with open(os.path.join(SPR, 'palette.txt'), 'w', newline='\n') as f:
        for i, (r, g, b) in enumerate(SP):
            f.write('%2d  %3d %3d %3d  #%02X%02X%02X\n' % (i, r, g, b, r, g, b))
    with open(os.path.join(SPR, 'README.txt'), 'w', newline='\n') as f:
        f.write("""CHix sprites. All PNGs are mode P with the shared 16-colour palette in palette.txt.
Palette index 15 = #FF00FF magenta is TRANSPARENT (colour key). Light from the top left, index 0 outline.
ship0/ship1 12x12 (thruster flicker), spark0..3 12x12 (spin), pu0..pu9 12x12:
 0 freeze 1 speed 2 lasers 3 shield 4 slow 5 bonus 6 score x2 7 ghost 8 bomb 9 extra life
boss_core boss_cube boss_octa boss_pyra boss_prism boss_hex boss_icosa boss_tess: 24x24 (2x the old 12x12 cores).
Generated by tools/paint/paint_sprites.py.
""")
    pv = Image.new('RGB', (560, 470), (24, 24, 48))
    x = y = 4
    rowh = 0
    for n in items:
        im = Image.open(os.path.join(SPR, n + '.png')).convert('RGBA')
        px = im.load()
        for j in range(im.height):
            for i in range(im.width):
                if px[i, j][:3] == (255, 0, 255):
                    px[i, j] = (0, 0, 0, 0)
        sc = 6 if im.width < 24 else 4
        if x + im.width * sc > 556:
            x = 4
            y += rowh + 6
            rowh = 0
        big = im.resize((im.width * sc, im.height * sc), Image.Resampling.NEAREST)
        pv.paste(big, (x, y), big)
        rowh = max(rowh, im.height * sc)
        x += im.width * sc + 6
    pv.save(os.path.join(HERE, 'preview_sprites.png'))


main()
