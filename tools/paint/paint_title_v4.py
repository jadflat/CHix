"""CHix title, v4: chrome/neon CHIX logo over the rainy neon megacity. Deterministic. Run: python paint_title_v4.py

Fixed indices (the title does not rotate): 0 near-black, 3 gold, 4 near-white, 7 cyan accent, 13 mid-dark.
The game draws "TERRITORY ARCADE" (3) on y56..62 and "HI" (4) on y64..70 over x18..110: that band is kept dark
and calm. Panels cover x10..117 from y72 down, so detail lives in y0..71 and the side strips x0..9, x118..127.
v4: street level below y72 (storefronts in the side strips, wet street, puddles), dark behind the panels.
Helpers copied from paint_b.py. Writes title.png and preview_title4.png (4x)."""
import math, random, os
from PIL import Image, ImageDraw

W, H = 128, 128
B4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
HERE = os.path.dirname(os.path.abspath(__file__))

PAL = [(4, 3, 14),       # 0 near-black
       (14, 10, 36),     # 1 night
       (32, 20, 66),     # 2 indigo
       (255, 196, 40),   # 3 gold
       (250, 250, 255),  # 4 near-white
       (255, 70, 190),   # 5 hot magenta neon
       (118, 28, 104),   # 6 deep magenta
       (0, 230, 255),    # 7 cyan neon (accent)
       (0, 112, 170),    # 8 deep cyan
       (255, 118, 36),   # 9 orange
       (134, 64, 12),    # 10 bronze
       (176, 224, 255),  # 11 pale ice
       (84, 98, 172),    # 12 steel
       (62, 48, 112),    # 13 mid-dark violet
       (100, 66, 150),   # 14 haze
       (12, 44, 78)]     # 15 deep teal

BAND = (16, 53, 111, 72)          # x0, y0, x1, y1 (exclusive): the text band, kept calm


def th(x, y): return (B4[int(y) & 3][int(x) & 3] + .5) / 16


def in_band(x, y): return BAND[0] <= x < BAND[2] and BAND[1] <= y < BAND[3]


class Cv:
    def __init__(s, pal):
        s.pal = pal
        s.a = [[0] * W for _ in range(H)]
        s.L = [.3 * r + .59 * g + .11 * b for r, g, b in pal]

    def px(s, x, y, c):
        x, y = int(x), int(y)
        if c is not None and 0 <= x < W and 0 <= y < H: s.a[y][x] = c

    def get(s, x, y):
        x, y = int(x), int(y)
        return s.a[y][x] if 0 <= x < W and 0 <= y < H else 0

    def mix(s, x, y, a, b, f): return b if th(x, y) < f else a

    def ramp(s, x, y, r, t):
        t = max(0., min(1., t)); u = t * (len(r) - 1); i = min(int(u), len(r) - 2)
        return s.mix(x, y, r[i], r[i + 1], u - i)

    def rect(s, x0, y0, x1, y1, c):
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1): s.px(x, y, c(x, y) if callable(c) else c)

    def disc(s, cx, cy, r, c, ry=None):
        ry = ry or r
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                if ((x - cx) / r) ** 2 + ((y - cy) / ry) ** 2 <= 1: s.px(x, y, c(x, y) if callable(c) else c)

    def lift(s, x, y, c):
        if c is not None and s.L[c] > s.L[s.get(x, y)]: s.px(x, y, c)

    def glow(s, cx, cy, r, rmp, k=1., ry=None, pw=1.6, calm=True):
        ry = ry or r
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                if calm and in_band(x, y): continue
                d = math.hypot((x - cx) / r, (y - cy) / ry)
                if d >= 1: continue
                u = (1 - d) ** pw * k * len(rmp); i = int(u)
                if i >= len(rmp): c = rmp[-1]
                else: c = rmp[i] if th(x, y) < u - i else (rmp[i - 1] if i else None)
                if 0 <= x < W and 0 <= y < H: s.lift(x, y, c)

    def image(s):
        im = Image.new("P", (W, H)); flat = []
        for p in s.pal: flat += list(p)
        im.putpalette(flat); im.putdata([v for row in s.a for v in row]); return im


def win_grid(c, x0, x1, y0, y1, cols, lit, rr, dx=2, dy=3, dim=None):
    for y in range(y0, y1, dy):
        floor_on = rr.random() < lit * 1.6
        for x in range(x0, x1, dx):
            if floor_on and rr.random() < .7 or rr.random() < lit * .3:
                col = rr.choice(cols)
                if in_band(x, y): col = dim
                c.px(x, y, col)


def tower(c, x0, x1, top, base, body, side, rim, rr, wins=(), lit=.3, dx=2, dy=3, ant=0, beacon=5, dim=None,
          lside=True):
    for y in range(top, base):
        for x in range(x0, x1 + 1):
            col = body
            if (x >= x1 - (x1 - x0) // 3) == lside: col = side
            if x == (x0 if lside else x1): col = rim if y % 2 or y < top + 6 else body
            if y == top: col = rim
            c.px(x, y, col)
    if wins: win_grid(c, x0 + 2, x1 - 1, top + 3, base - 2, wins, lit, rr, dx, dy, dim)
    if ant:
        ax = x0 + (x1 - x0) * 2 // 3
        for y in range(top - ant, top): c.px(ax, y, side)
        c.px(ax, top - ant - 1, beacon)


def vsign(c, x, y, h, col, hot, frame, glow_r=6, k=.5, rmp=None, seed=0):
    c.rect(x - 1, y - 1, x + 3, y + h, frame)
    rr = random.Random(x * 31 + y + seed)
    for yy in range(y, y + h):
        if (yy - y) % 4 == 3: continue
        for xx in range(x, x + 3):
            if rr.random() < .62: c.px(xx, yy, col)
        if rr.random() < .3: c.px(x + 1, yy, hot)
    c.glow(x + 1, y + h / 2, glow_r, rmp or [col], k, ry=h / 2 + glow_r * .6)


def car(c, x, y, d, body, roof, head, tail, trail, k=.6):
    for i in range(2, 12):
        tx = x - d * i + (4 if d < 0 else 0)
        if th(tx, y + 1) < (1 - i / 12) * .8: c.px(tx, y + 1, trail)
    c.rect(x, y, x + 4, y + 1, body); c.px(x + 1, y - 1, roof); c.px(x + 2, y - 1, roof); c.px(x + 3, y - 1, roof)
    c.px(x + (4 if d > 0 else 0), y, head); c.px(x + (0 if d > 0 else 4), y, tail); c.px(x + 2, y + 2, trail)
    c.glow(x + (5 if d > 0 else -1), y, 4, [head], k)


# ------------------------------------------------------------------ the logo
LT, LH, SHEAR = 4, 34, .15       # letter top, height, italic lean


def letter_polys(ch):
    """(fill polygons, hole polygons) in a 0..w x 0..LH box."""
    if ch == "C":
        return 22, [[(7, 0), (22, 0), (22, 10), (10, 10), (8, 12), (8, 22), (10, 24), (22, 24), (22, 34), (7, 34),
                     (0, 27), (0, 7)]], []
    if ch == "H":
        return 23, [[(0, 0), (8, 0), (8, 13), (15, 13), (15, 0), (23, 0), (23, 34), (15, 34), (15, 21), (8, 21),
                     (8, 34), (0, 34)]], []
    if ch == "I":
        return 16, [[(0, 0), (16, 0), (16, 8), (12, 8), (12, 26), (16, 26), (16, 34), (0, 34), (0, 26), (4, 26),
                     (4, 8), (0, 8)]], []
    if ch == "X":
        return 25, [[(0, 0), (8, 0), (12.5, 10), (17, 0), (25, 0), (17, 17), (25, 34), (17, 34), (12.5, 24), (8, 34),
                     (0, 34), (8, 17)]], []


def logo_mask():
    word, gap = "CHIX", 7
    ws = [letter_polys(ch)[0] for ch in word]
    total = sum(ws) + gap * (len(ws) - 1) + SHEAR * LH
    x = (W - total) / 2 - 1.5
    im = Image.new("L", (W, H), 0); dr = ImageDraw.Draw(im)
    boxes = []
    for ch in word:
        w, fills, holes = letter_polys(ch)
        tf = lambda p: (x + p[0] + (LH - p[1]) * SHEAR, LT + p[1])
        for poly in fills: dr.polygon([tf(p) for p in poly], fill=255)
        for poly in holes: dr.polygon([tf(p) for p in poly], fill=0)
        boxes.append((x, w)); x += w + gap
    return [[im.getpixel((xx, yy)) > 0 for xx in range(W)] for yy in range(H)], boxes


def draw_logo(c):
    m, boxes = logo_mask()
    inm = lambda x, y: 0 <= x < W and 0 <= y < H and m[y][x]
    # extrusion (down-right) in deep magenta, darkening away from the face
    ext = [[0] * W for _ in range(H)]
    for d in (2, 1):
        for y in range(H):
            for x in range(W):
                if inm(x - d, y - d) and not m[y][x]: ext[y][x] = d
    solid = lambda x, y: inm(x, y) or (0 <= x < W and 0 <= y < H and ext[y][x])
    # distance from the solid shape (Chebyshev) for outline + neon + glow
    INF = 99
    dist = [[0 if solid(x, y) else INF for x in range(W)] for y in range(H)]
    for _ in range(7):
        for y in range(H):
            for x in range(W):
                if dist[y][x] == INF or True:
                    best = dist[y][x]
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            X, Y = x + dx, y + dy
                            if 0 <= X < W and 0 <= Y < H and dist[Y][X] + 1 < best: best = dist[Y][X] + 1
                    dist[y][x] = best
    # soft magenta bloom first (only brightens the sky), then neon ring, then the dark keyline
    for y in range(H):
        for x in range(W):
            d = dist[y][x]
            if 3 <= d <= 5:
                f = (6 - d) / 4
                c.lift(x, y, 6 if th(x, y) < f * .9 else (13 if th(x, y) < f * 1.4 else None))
    for y in range(H):
        for x in range(W):
            d = dist[y][x]
            if d == 2: c.px(x, y, 5)
            elif d == 1: c.px(x, y, 0)
            elif d == 0 and ext[y][x]:
                c.px(x, y, {1: 6, 2: 2}[ext[y][x]])
    # chrome face: sky-ice top, white horizon, sunset gold bottom
    HZ = LT + 16
    for y in range(H):
        for x in range(W):
            if not m[y][x]: continue
            t = (y - LT) / LH
            if y < HZ:
                col = c.ramp(x, y, [4, 11, 11, 7, 8, 8], (y - LT) / (HZ - LT))
            elif y == HZ:
                col = 4
            elif y == HZ + 1:
                col = 15
            else:
                col = c.ramp(x, y, [10, 10, 9, 3, 3, 4], (y - HZ - 2) / (LT + LH - HZ - 2))
            up, lf = inm(x, y - 1), inm(x - 1, y)
            dn, rt = inm(x, y + 1), inm(x + 1, y)
            if not up or not lf: col = 4 if y < HZ else 3
            elif not dn or not rt: col = 8 if y < HZ else 10
            c.px(x, y, col)
    # star glints on corners
    for gx, gy, r in ((int(boxes[0][0] + 14), LT, 3), (int(boxes[3][0] + 34), LT + 1, 4), (int(boxes[2][0] + 9), LT + LH - 1, 2)):
        c.px(gx, gy, 4)
        for i in range(1, r + 1):
            col = 4 if i < r else 11
            for dx, dy in ((i, 0), (-i, 0), (0, i), (0, -i)): c.px(gx + dx, gy + dy, col)
        c.px(gx - 1, gy - 1, 11); c.px(gx + 1, gy + 1, 11); c.px(gx + 1, gy - 1, 11); c.px(gx - 1, gy + 1, 11)
    return m


# ------------------------------------------------------------------ the city
def paint():
    c = Cv(PAL)
    rr = random.Random(2026)
    STREET = 101
    # sky: night to magenta haze at the horizon
    stops = [0, 1, 1, 2, 13, 14]
    for y in range(0, STREET):
        t = min(1., y / 64) ** 1.1 * (len(stops) - 1); i = min(int(t), len(stops) - 2)
        for x in range(W): c.px(x, y, c.mix(x, y, stops[i], stops[i + 1], t - i))
    for _ in range(40):
        x, y = rr.randrange(W), rr.randrange(0, 34)
        if c.get(x, y) in (0, 1): c.px(x, y, rr.choice((12, 13, 11, 14)))

    # ringed planet in haze, upper right; the logo stands in front of it
    PX, PY, PR = 119, 42, 16
    c.glow(PX, PY, PR + 12, [2, 13, 14], .8, pw=1.2)
    RA = math.radians(-12)

    def ring_pts(front):
        out = []
        for i in range(720):
            a = i / 720 * 2 * math.pi
            for rr_ in (28, 27, 25, 24, 23):
                ex, ey = rr_ * math.cos(a), rr_ * .2 * math.sin(a)
                x = PX + ex * math.cos(RA) - ey * math.sin(RA); y = PY + ex * math.sin(RA) + ey * math.cos(RA)
                if (math.sin(a) > 0) == front: out.append((round(x), round(y), rr_))
        return out
    rcol = {28: 12, 27: 4, 25: 11, 24: 12, 23: 13}
    for x, y, r_ in ring_pts(False):
        if not in_band(x, y): c.px(x, y, rcol[r_])

    def planet(x, y):
        dx, dy = (x - PX) / PR, (y - PY) / PR
        r2 = dx * dx + dy * dy
        lit = (dx * .5 - dy * .7) * .75 + .4                      # lit from the upper right
        lit += .07 * math.sin((y - PY + dx * 4) * .9)             # cloud bands
        col = c.ramp(x, y, [1, 15, 15, 8, 8, 12], lit)
        if r2 > .78 and lit > .55: col = 7 if th(x, y) < .55 else 11              # sunlit limb
        if r2 > .82 and dy > .3 and dx < .3: col = c.mix(x, y, col, 5, .45)        # magenta city-glow rim
        return col
    c.disc(PX, PY, PR, planet)
    for x, y, r_ in ring_pts(True): c.px(x, y, rcol[r_])
    # ring shadow on the planet
    for x, y, r_ in ring_pts(True):
        if r_ == 23 and math.hypot(x - PX, y + 2 - PY) < PR: c.px(x, y + 2, 1)


    # far skyline in the magenta haze
    x = -2
    while x < W:
        w = rr.randint(4, 8); top = rr.randint(45, 54)
        tower(c, x, x + w, top, STREET, 13, 2, 14, rr, wins=[5, 3, 12, 14], lit=.25, dim=13, ant=rr.choice((0, 0, 5)),
              beacon=5)
        x += w + rr.randint(0, 2)
    # haze over the far layer
    for y in range(45, 62):
        for x in range(W):
            if c.get(x, y) in (13, 2) and th(x, y) < (y - 45) / 34: c.px(x, y, 14 if c.get(x, y) == 13 else 13)
    # a traffic lane across the haze, just under the logo
    tl = random.Random(31); x = 0
    while x < W:
        col = tl.choice((5, 3, 11, 7, 9)); n = tl.randint(1, 3)
        for i in range(n): c.px(x + i, 47 + (x // 40) % 2 * 0, col if i == 0 else (13 if col != 13 else 14))
        x += n + tl.randint(2, 5)
    # mid skyline, darker: tops just under the logo, windows dim in the text band
    x = -1
    while x < W:
        w = rr.randint(5, 10); top = rr.randint(53, 61)
        tower(c, x, x + w, top, STREET, 2, 1, 13, rr, wins=[3, 9, 12, 5], lit=.25, dim=13,
              ant=rr.choice((0, 0, 4, 6)), beacon=5)
        x += w + rr.randint(1, 3)
    # calm the text band: darken one step, feathered at the edges so no box shows
    DK = {14: 13, 13: 2, 12: 13, 11: 13, 3: 10, 9: 10, 5: 6, 4: 13, 7: 8, 6: 2, 8: 15}
    for y in range(BAND[1] - 3, BAND[3]):
        for x in range(BAND[0] - 4, BAND[2] + 4):
            f = min(1., (x - BAND[0] + 4) / 5, (BAND[2] + 3 - x) / 5, (y - BAND[1] + 3) / 4)
            v = c.get(x, y)
            if in_band(x, y) or th(x, y) < f: c.px(x, y, DK.get(v, v))
    for y in range(BAND[1], BAND[3]):
        for x in range(BAND[0], BAND[2]):
            v = c.get(x, y)
            if v in (3, 9, 5, 4, 7, 11): c.px(x, y, 13)
    # behind the panels (x10..118, y72 down): one to two steps darker so the menu text reads, gaps filled
    DK2 = {14: 2, 13: 1, 12: 2, 11: 13, 3: 10, 9: 10, 5: 6, 4: 13, 7: 8, 6: 2, 8: 15, 2: 1, 10: 6}
    for y in range(68, STREET):
        for x in range(8, 121):
            f = min(1., (y - 67) / 6, (x - 7) / 4, (121 - x) / 4)
            v = c.get(x, y)
            if th(x, y) < f: v = DK2.get(v, v)
            if y > 80 and th(x, y) < f * (y - 80) / 24: v = DK2.get(v, v)
            c.px(x, y, v)
    # flying cars and traffic in the sky
    car(c, 3, 49, 1, 2, 12, 4, 5, 6, .6)
    car(c, 2, 22, 1, 2, 12, 11, 5, 6, .6)
    car(c, 112, 61, -1, 1, 13, 3, 6, 6, .4)

    # near towers on the sides (the strips the panels leave): lit, signed, rim-lit
    tower(c, -1, 13, 32, STREET, 1, 0, 12, rr, wins=[3, 9, 11, 3, 5], lit=.45, dx=2, dy=3)
    tower(c, 114, 128, 62, STREET, 1, 0, 12, rr, wins=[3, 7, 11, 9], lit=.45, dx=2, dy=3, lside=False)
    # tower roofs: water tanks, antennas, beacons
    c.rect(2, 28, 7, 31, 2); c.rect(3, 27, 6, 27, 13); c.px(10, 24, 5); c.rect(10, 25, 10, 31, 13)
    c.glow(10, 24, 4, [6, 5], .6)
    c.rect(124, 55, 124, 61, 13); c.px(124, 54, 5); c.glow(124, 54, 4, [6, 5], .6)
    # vertical neon signs
    vsign(c, 2, 37, 22, 5, 4, 0, glow_r=5, k=.55, rmp=[6, 5])
    vsign(c, 3, 74, 12, 3, 4, 0, glow_r=5, k=.5, rmp=[10, 9, 3], seed=5)
    vsign(c, 122, 75, 12, 7, 4, 0, glow_r=5, k=.5, rmp=[8, 7], seed=9)
    # a gold kanji-ish box sign on the right tower and a cyan bar on the left
    c.rect(119, 66, 126, 72, 0)
    for (dx, dy) in ((1, 1), (2, 1), (3, 1), (5, 1), (2, 2), (2, 3), (1, 3), (3, 3), (5, 3), (5, 2), (5, 4), (1, 5), (2, 5),
                     (3, 5), (5, 5)):
        c.px(119 + dx, 66 + dy, 3)
    c.glow(122, 69, 7, [10, 9], .4)
    for y in range(58, 64): c.px(1, y, 7); c.px(2, y, 8 if y % 2 else 7)
    c.glow(2, 61, 5, [8], .5)

    # rain: slanted streaks over the sky and city, not on the text band
    rn = random.Random(77)
    for _ in range(170):
        x, y = rn.randrange(W + 8), rn.randrange(-4, H)
        ln = rn.choice((3, 4, 4, 5, 6)); col = rn.choice((12, 12, 13, 14))
        for i in range(ln):
            X, Y = x - i // 2, y + i
            if 0 <= Y < H and not in_band(X, Y):
                cur = c.get(X, Y)
                cc = 11 if c.L[cur] > c.L[col] + 30 else col
                if i == ln - 1 and ln > 3: cc = 14
                if c.L[cc] > c.L[cur] or cur in (0, 1): c.px(X, Y, cc)

    # the logo over everything above
    draw_logo(c)

    # street level (v4): lit storefronts in the side strips, then a wet street mirroring them, puddles, glints
    def storefront(x0, x1, sign, sign_hot, awn, glass, frame, rmp, seed):
        y0 = STREET - 12
        sr = random.Random(seed)
        for x in range(x0, x1 + 1):                                    # sign board with neon glyphs
            c.px(x, y0, 0); c.px(x, y0 + 1, 0); c.px(x, y0 + 2, 0)
            if (x - x0) % 3 != 2:
                if sr.random() < .7: c.px(x, y0 + 1, sign)
                if sr.random() < .4: c.px(x, y0 + (0 if sr.random() < .5 else 2), sign)
        c.px(x0 + 2 + sr.randrange(max(1, x1 - x0 - 3)), y0 + 1, sign_hot)
        for x in range(x0, x1 + 1):                                    # striped awning, sagging lip
            c.px(x, y0 + 3, awn[0] if (x // 2) % 2 else awn[1])
            c.px(x, y0 + 4, awn[0] if (x // 2) % 2 else awn[1])
            if x % 2: c.px(x, y0 + 5, awn[1])
        for y in range(y0 + 5, STREET):                                # lit glass, mullions, a figure inside
            for x in range(x0, x1 + 1):
                if y == y0 + 5 and x % 2: continue
                col = c.ramp(x, y, glass, (y - y0 - 5) / 7)
                if (x - x0) % 5 == 4 or y == STREET - 1: col = frame
                c.px(x, y, col)
        fx = x0 + 2 + sr.randrange(max(1, x1 - x0 - 5))
        c.rect(fx, STREET - 5, fx + 1, STREET - 2, 0); c.px(fx, STREET - 6, 0); c.px(fx + 1, STREET - 6, 0)
        c.glow((x0 + x1) / 2, STREET, (x1 - x0) / 2 + 7, rmp, .7, ry=6, calm=False)

    storefront(0, 10, 5, 4, (5, 6), [11, 7, 8], 0, [6, 5], 11)
    storefront(118, 127, 9, 3, (9, 10), [3, 9, 10], 0, [10, 9], 12)
    # a street lamp in each strip: grey post with a lit edge, bright head
    for lx, d in ((9, 1), (118, -1)):
        for y in range(STREET - 31, STREET - 12): c.px(lx, y, 12 if y % 2 else 13)
        c.px(lx + d, STREET - 32, 13); c.px(lx + 2 * d, STREET - 32, 13)
        c.px(lx + 2 * d, STREET - 31, 4); c.px(lx + d, STREET - 31, 11)
        c.glow(lx + 2 * d, STREET - 30, 6, [12, 11], .6, calm=False)
    snap = [row[:] for row in c.a]
    dk = {4: 11, 11: 12, 3: 10, 9: 10, 5: 6, 7: 8, 12: 13, 14: 13, 13: 2, 2: 1, 1: 0, 10: 6, 6: 2, 8: 15, 15: 1}
    side = lambda x: x <= 12 or x >= 115
    # wet asphalt: deep teal under the shop light, indigo to black under the panels; reflections smeared down
    for y in range(STREET, H):
        d = y - STREET
        for x in range(W):
            sd = max(0., 1 - min(abs(x - 5), abs(x - 122)) / 26)          # 1 at the shop strips, 0 mid street
            base = c.ramp(x, y, [0, 1, 15, 15], sd * (1 - d / 40) + .15)
            ox = 1 if (y // 2 + x // 4) % 3 == 0 else 0
            src = max(0, STREET - 1 - int(d * 1.15))
            p = snap[src][min(W - 1, x + ox)]
            t = th(x, y)
            col = base
            if c.L[p] > 110:
                if side(x): col = p if t < .8 - d * .015 else dk.get(p, p)
                elif t < .55 - d * .012: col = dk.get(p, p) if t < .3 else dk.get(dk.get(p, p), p)
            elif side(x) and c.L[p] > c.L[base] and t < .5: col = dk.get(p, p)
            if d % 4 == 3 and t < .5: col = base if c.L[col] > c.L[base] else 0      # ripple breaks
            c.px(x, y, col)
    # light pools spilling from the shops and lamps across the wet street
    for gx, gy, r, rmp in ((5, STREET + 4, 22, [15, 8, 7]), (122, STREET + 4, 20, [15, 10, 9]),
                           (11, STREET + 12, 9, [12, 11]), (116, STREET + 12, 9, [12, 11])):
        c.glow(gx, gy, r, rmp, .55, ry=r * .45, calm=False)
    for x in range(W):                                                   # kerb: lit at the sides, dim in the middle
        c.px(x, STREET, (11 if x % 3 == 0 else 12) if side(x) else (13 if x % 2 else 2))
        c.px(x, STREET + 1, 0 if x % 3 else 1)
    # lane lines in perspective, dashed, toward a point behind the panel
    for ex in (-40, 30, 98, 168):
        for y in range(STREET + 3, H):
            f = (y - STREET) / (H - STREET)
            x = round(64 + (ex - 64) * f)
            if (y // 3) % 2 == 0:
                c.px(x, y, 12)
                if f > .6: c.px(x + (1 if ex > 64 else -1), y, 13)
    # puddles: crisp mirrors of the shop neon, rimmed, with a white glint on the near lip
    for cx, cy, rx, ry in ((20, 110, 8, 2), (5, 119, 5, 2), (26, 122, 7, 2), (107, 110, 7, 2), (121, 118, 6, 2),
                           (102, 124, 7, 2), (48, 114, 6, 1.5), (80, 112, 6, 1.5), (64, 120, 8, 2)):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                e = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if e > 1 or not 0 <= x < W: continue
                src = max(0, STREET - 3 - int((cy - y) * 3) - int(abs(x - cx) * .3))
                sx_ = 5 if x < 64 else 122                                  # mirror the nearest shop, softly
                p = snap[src][max(0, min(W - 1, x if side(x) else sx_ + (x - cx) // 2))]
                col = p if (side(x) or th(x, y) < .4) else dk.get(p, p)
                if not (side(x) or x < 34 or x > 94): col = dk.get(col, col)
                if e > .55: col = 13 if y <= cy else 1
                c.px(x, y, col)
        c.px(cx - rx * .5, cy - ry, 4); c.px(cx - rx * .5 + 1, cy - ry, 11); c.px(cx + rx * .4, cy + ry, 12)
    # a pedestrian under a neon umbrella (lower left) and a parked cab (lower right), with reflections
    UX, UY = 22, 114
    for k in range(-4, 5): c.px(UX + k, UY - 2 + abs(k) // 3, 5 if abs(k) < 4 else 4)
    for k in range(-3, 4): c.px(UX + k, UY - 3 + abs(k) // 2, 5)
    c.px(UX, UY - 4, 4); c.px(UX - 4, UY - 1, 11)
    c.rect(UX - 1, UY, UX + 1, UY + 5, 0); c.px(UX - 1, UY + 6, 0); c.px(UX + 1, UY + 6, 0)
    c.px(UX + 1, UY + 1, 6)
    c.glow(UX, UY - 1, 7, [13, 6], .5, ry=4, calm=False)
    for k in range(-4, 5, 2): c.px(UX + k, UY + 9 + abs(k) // 3, 6)
    c.rect(UX - 1, UY + 7, UX + 1, UY + 8, 2)
    CX, CY = 100, 114                                                  # cab facing left
    c.rect(CX, CY, CX + 15, CY + 3, 10); c.rect(CX + 3, CY - 3, CX + 11, CY - 1, 1)
    c.rect(CX + 4, CY - 2, CX + 10, CY - 2, 8); c.rect(CX + 3, CY - 3, CX + 11, CY - 3, 9)
    c.rect(CX, CY, CX + 15, CY, 3); c.px(CX + 7, CY - 4, 4); c.px(CX + 6, CY - 4, 3)
    c.px(CX, CY + 1, 4); c.px(CX + 15, CY + 1, 5); c.px(CX + 15, CY + 2, 6)
    c.px(CX + 3, CY + 4, 0); c.px(CX + 12, CY + 4, 0); c.rect(CX + 1, CY + 4, CX + 14, CY + 4, 0)
    c.glow(CX - 2, CY + 1, 7, [12, 11], .6, ry=3, calm=False)
    c.glow(CX + 17, CY + 1, 5, [6, 5], .6, ry=3, calm=False)
    for x in range(CX, CX + 16):
        for k in range(1, 5):
            v = c.get(x, CY + 4 - k)
            if v in (3, 10, 4, 5, 9, 8) and th(x, CY + 5 + k) < .55 - k * .1: c.px(x, CY + 5 + k, dk.get(v, v))
    # rain on the street: short streaks and splash crowns, brighter near the shop light
    rn = random.Random(91)
    for _ in range(46):
        x, y = rn.randrange(W + 4), rn.randrange(STREET - 6, H)
        for i in range(3):
            X, Y = x - i // 2, y + i
            if 0 <= Y < H and c.get(X, Y) in (0, 1, 2, 15): c.px(X, Y, 12 if side(X) else 13)
    sp = random.Random(9)
    for _ in range(40):
        x, y = sp.randrange(1, W - 1), sp.randrange(STREET + 3, H)
        hi = 4 if side(x) or x < 34 or x > 94 else 12
        if c.get(x, y) in (0, 1, 2, 15):
            c.px(x - 1, y, 13); c.px(x + 1, y, 13); c.px(x, y - 1, hi if sp.random() < .5 else 11)
    return c.image()


def main():
    im = paint()
    im.save(os.path.join(HERE, "title.png"))
    mock = im.copy(); d = ImageDraw.Draw(mock)          # the game's overlay, roughly, to judge the layout
    mock2 = None
    for x0, y0, x1, y1 in ((10, 72, 118, 106), (34, 108, 94, 122)): d.rectangle([x0, y0, x1, y1], fill=0, outline=7)
    for i, ch in enumerate("TERRITORY ARCADE"):
        if ch != " ": d.rectangle([17 + i * 6, 56, 21 + i * 6, 62], outline=3)
    for i in range(6): d.rectangle([46 + i * 6, 64, 50 + i * 6, 70], outline=4)
    mock2 = mock.copy(); d2 = ImageDraw.Draw(mock2)
    d2.rectangle([10, 106, 126, 126], fill=0, outline=7)
    prev = Image.new("RGB", (W * 12 + 16, H * 4))
    prev.paste(im.convert("RGB").resize((W * 4, H * 4), Image.Resampling.NEAREST), (0, 0))
    prev.paste(mock.convert("RGB").resize((W * 4, H * 4), Image.Resampling.NEAREST), (W * 4 + 8, 0))
    prev.paste(mock2.convert("RGB").resize((W * 4, H * 4), Image.Resampling.NEAREST), (W * 8 + 16, 0))
    prev.save(os.path.join(HERE, "preview_title4.png"))


if __name__ == "__main__":
    main()
