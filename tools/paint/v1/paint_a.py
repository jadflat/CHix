"""CHix scenes 00..03: rainy cyberpunk night cities, 120x112 indexed. Run: python paint_a.py"""
import os, math
import numpy as np
from PIL import Image

W, H, G = 120, 112, 98          # G = street line
HERE = os.path.dirname(os.path.abspath(__file__))
B4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
FIX = {0: (4, 4, 12), 3: (255, 200, 40), 4: (255, 255, 255), 5: (190, 215, 255), 6: (255, 70, 70),
       7: (0, 230, 255), 8: (60, 255, 120), 11: (232, 240, 255), 14: (96, 108, 170), 15: (255, 60, 200)}


def H_(s):
    return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))


def mk(p, cols):
    return dict(p=p, pal=dict(zip((1, 2, 9, 10, 12, 13), map(H_, cols.split()))))


# seed, farMin, farMax, nearMin, nearMax, bb, discX, discY, discR, dens
SC = [mk((1, 30, 75, 20, 50, 7, 0, 0, 0, 3), "#1c1034 #43205a #2e2356 #15122e #ff5a3c #9a4a96"),
      mk((2, 14, 45, 10, 35, 5, 90, 30, 16, 0), "#0a1a36 #143c60 #1f3d70 #0c1c3a #ff8a30 #4c8cb4"),
      mk((3, 20, 60, 10, 40, 6, 0, 0, 0, 0), "#0c201c #1c3c34 #2a4c46 #0c2420 #e8307c #5c9c84"),
      mk((4, 25, 85, 20, 60, 8, 30, 28, 14, 4), "#240c1a #4c1c2a #5c2c3c #1e0e1e #ffa040 #b85c62")]


def hsh(a, b, s=0):
    return (((a * 73856093) ^ (b * 19349663) ^ (s * 83492791)) * 2654435761 % 4294967296) >> 12 & 255


class C:
    def __init__(s, sc):
        s.a = np.zeros((H, W), np.uint8)
        s.p = sc['p']
        s.rng = np.random.RandomState(s.p[0] * 977)

    def px(s, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            s.a[y, x] = c

    def get(s, x, y):
        return int(s.a[y, x]) if 0 <= x < W and 0 <= y < H else 0

    def rect(s, x0, y0, x1, y1, c):
        s.a[max(y0, 0):max(min(y1 + 1, H), 0), max(x0, 0):max(min(x1 + 1, W), 0)] = c

    def dpx(s, x, y, c1, c2, t):
        s.px(x, y, c2 if B4[y & 3][x & 3] < t else c1)


DARK = (0, 1, 2, 9, 10, 13)


def glow2(c, x0, y0, x1, y1, col, r=3):
    for y in range(y0 - r, y1 + r + 1):
        for x in range(x0 - r, x1 + r + 1):
            d = max(x0 - x, x - x1, y0 - y, y - y1, 0)
            if 0 < d <= r and c.get(x, y) in DARK and B4[y & 3][x & 3] < 9 - d * 3:
                c.px(x, y, col)


def sky(c, ramp, wob=0.5, off=0.0):
    n = len(ramp) - 1
    for y in range(G + 1):
        for x in range(W):
            t = (y / G) ** 1.15 * n
            t += wob * (math.sin(x * .09 + y * .21) * math.sin(y * .5 + x * .03) * .5 + math.sin(x * .27 - y * .11) * .3) * (1 - y / G) + off
            t = min(max(t, 0), n - .001)
            i = int(t)
            f = t - i
            c.px(x, y, ramp[i + 1] if B4[y & 3][x & 3] < f * 16 else ramp[i])


def stars(c, n, seed):
    r = np.random.RandomState(seed)
    for _ in range(n):
        x, y = r.randint(0, W), r.randint(0, 34)
        if c.get(x, y) in (0, 1):
            c.px(x, y, 4 if r.rand() < .3 else 5 if r.rand() < .5 else 13)


def skyline(c, lo, hi, base, col, edge, wins, kind, dens, bbn=0, haze=None, hz=13):
    r = c.rng
    x = -2
    out = []
    while x < W:
        w = (6 if kind == 2 else 4) + r.randint(0, 10 if kind == 2 else 8)
        w += 2 if kind == 0 else 0
        ht = int((lo + r.randint(0, max(hi - lo, 1))) * (1.0 if kind == 0 else .72 if kind == 1 else .62))
        top = base - ht
        x1 = min(x + w - 1, W - 1)
        bb = bool(kind == 2 and bbn and r.randint(0, bbn) == 0)
        out.append((x, w, top, bb))
        for xx in range(max(x, 0), x1 + 1):
            for yy in range(max(top, 0), base + 1):
                v = col
                if xx == max(x, 0) and edge:
                    v = edge
                if haze and B4[yy & 3][xx & 3] < haze * (yy - top) / max(ht, 1):
                    v = hz
                c.px(xx, yy, v)
        k = r.randint(0, 3)
        mid = x + w // 2
        if k == 0:
            c.rect(mid, top - 3, mid, top - 1, col)
            c.px(mid, top - 4, 6 if kind == 2 else col)
        elif k == 1:
            c.rect(x + 1, top - 2, x + 3, top - 1, col)
        elif k == 2 and w > 6:
            c.rect(x + 1, top - 1, x1 - 1, top - 1, edge or col)
        if wins:
            sx, sy = (3, 4) if kind == 2 else (3, 3) if kind == 1 else (2, 3)
            for wy in range(top + 3, base - 2, sy):
                for wx in range(max(x, 0) + 2, x1 - 1, sx):
                    h = hsh(wx, wy, x + kind)
                    if h < dens:
                        cc = wins[h % len(wins)]
                        if kind == 2:
                            c.rect(wx, wy, wx + 1, wy + 1, cc)
                        else:
                            c.px(wx, wy, cc)
        x += w
    return out


def billboard(c, x, y, w, h, col, col2, seed):
    c.rect(x - 1, y - 1, x + w, y + h, 14)
    c.rect(x, y, x + w - 1, y + h - 1, 0)
    for yy in range(y + 1, y + h - 1):
        for xx in range(x + 1, x + w - 1):
            if hsh(xx, yy, seed) < 120 and (yy - y) % 2 == 1:
                c.px(xx, yy, col if xx % 5 else col2)
    c.rect(x, y + h - 1, x + w - 1, y + h - 1, col)
    glow2(c, x - 1, y - 1, x + w, y + h, col, 2)


def disc(c, cx, cy, r, tones):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            dx, dy = x - cx + .5, y - cy + .5
            if math.hypot(dx, dy) <= r:
                l = 1 - min(max((-(dx + dy) * .7071) / r * .5 + .5, 0), 1)
                t = l * (len(tones) - 1) + (hsh(x, y, 5) / 255 - .5) * .15
                t = min(max(t, 0), len(tones) - 1.001)
                i = int(t)
                c.px(x, y, tones[i + 1] if B4[y & 3][x & 3] < (t - i) * 16 else tones[i])


def halo(c, cx, cy, r0, r1, col):
    for y in range(cy - r1, cy + r1 + 1):
        for x in range(cx - r1, cx + r1 + 1):
            d = math.hypot(x - cx, y - cy)
            if r0 < d <= r1 and c.get(x, y) in DARK and B4[y & 3][x & 3] < 7 * (1 - (d - r0) / (r1 - r0)):
                c.px(x, y, col)


def cars(c, lst):
    for x, y, d, body, tail in lst:
        c.rect(x, y, x + 4, y + 1, body)
        c.px(x + (5 if d > 0 else -1), y, 4)
        c.px(x + 1, y - 1, body)
        c.px(x + 2, y - 1, body)
        for i in range(1, 9):
            xx = x - d * i + (0 if d > 0 else 4)
            c.dpx(xx, y, c.get(xx, y), tail, 13 - i)


def street(c, wet):
    pre = c.a.copy()
    for y in range(G + 1, H):
        d = y - G
        for x in range(W):
            c.px(x, y, 0 if d > 2 else 10)
            sy = G - int(d * 2.2)
            wob = int(math.sin(y * 1.7 + x * .15) * 1.2)
            sp = int(pre[max(sy, 0), min(max(x + wob, 0), W - 1)])
            if sp in (3, 7, 8, 12, 15, 4, 5, 13, 6) and B4[y & 3][x & 3] < 13 - d:
                c.px(x, y, sp)
            elif sp in (9, 14) and B4[y & 3][x & 3] < 6 - d // 2:
                c.px(x, y, 9)
    for x in range(W):
        c.px(x, G + 1, 14 if (x // 2) % 3 else 10)
    r = c.rng
    for _ in range(10):
        x, y = r.randint(0, W - 8), r.randint(G + 4, H - 1)
        for i in range(r.randint(3, 7)):
            c.px(x + i, y, wet)
    for x in range(2, W, 14):
        c.rect(x, H - 4, x + 5, H - 4, 14)


def rain(c, seed, n=70):
    n = n * 2 // 3
    r = np.random.RandomState(seed)
    bright = (3, 12, 7, 8, 15, 6)
    for _ in range(n):
        x, y = r.randint(0, W), r.randint(0, H - 3)
        col = 13 if r.rand() < .6 else 11 if r.rand() < .3 else 14
        for i in range(3):
            if c.get(x - i // 2, y + i) not in bright and (i < 2 or r.rand() < .5):
                c.px(x - i // 2, y + i, col)
    for _ in range(18):
        x, y = r.randint(1, W - 2), r.randint(G + 3, H - 1)
        c.px(x - 1, y, 14)
        c.px(x + 1, y, 14)
        c.px(x, y - 1, 11)


def tower(c, cx, top, base, w0, col, rim):
    for y in range(top, base + 1):
        t = (y - top) / (base - top)
        hw = int(1 + (w0 - 1) * t ** 1.3)
        for x in range(cx - hw, cx + hw + 1):
            c.px(x, y, rim if x == cx - hw else col if x < cx + hw else 0)
    c.rect(cx, top - 10, cx, top, col)


def nearpass(c, nb, edge, bbcols, bbalt):
    for (x, w, top, bb) in nb:
        if bb and w >= 8:
            billboard(c, x + 1, top - 9, w - 2, 7, bbcols[x % 3], bbalt, x)
        c.rect(x, top, x + w - 1, top, edge)


# ---------------------------------------------------------------- scenes
def scene0():
    c = C(SC[0])
    p = SC[0]['p']
    sky(c, [0, 1, 2, 13], wob=.8)
    stars(c, 14, 3)
    skyline(c, p[1] - 12, p[2] - 20, G - 14, 9, 14, [13, 13, 9], 0, 70, haze=10, hz=2)
    skyline(c, (p[1] + p[3]) // 2 - 4, (p[2] + p[4]) // 2 - 6, G - 6, 10, 14, [13, 3, 13, 9], 1, 90)
    cx = 60
    tower(c, cx, 8, G, 11, 10, 14)
    for y in (22, 36, 50, 64):
        hw = int(1 + 10 * ((y - 8) / (G - 8)) ** 1.3)
        c.rect(cx - hw - 2, y, cx + hw + 2, y, 7)
        glow2(c, cx - hw - 2, y, cx + hw + 2, y, 7, 2)
    for y in range(12, G - 4, 5):
        hw = int(1 + 10 * ((y - 8) / (G - 8)) ** 1.3)
        for x in range(cx - hw + 2, cx + hw - 1, 3):
            if hsh(x, y, 9) < 110:
                c.px(x, y, 3)
    c.px(cx, 6, 6)
    c.px(cx - 1, 6, 12)
    c.px(cx + 1, 6, 12)
    halo(c, cx, 6, 1, 5, 12)
    nb = skyline(c, p[3] - 2, p[4], G, 0, 10, [3, 12, 7, 3, 13, 12], 2, 100, bbn=p[5] - 4)
    nearpass(c, nb, 14, [12, 7, 15], 3)
    cars(c, [(20, 30, 1, 5, 15), (88, 44, -1, 3, 12), (40, 56, 1, 11, 7)])
    street(c, 7)
    rain(c, 11)
    return c


def scene1():
    c = C(SC[1])
    p = SC[1]['p']
    sky(c, [0, 1, 2, 13], wob=.6, off=-.2)
    stars(c, 26, 5)
    cx, cy, r = p[6], p[7], p[8]
    halo(c, cx, cy, r, r + 9, 13)
    disc(c, cx, cy, r, [5, 13, 2, 1])
    for dx, dy, l in ((-4, -3, 5), (3, 1, 6), (-1, 5, 4)):
        for i in range(l):
            xx = cx + dx + i - 3
            c.dpx(xx, cy + dy, c.get(xx, cy + dy), 12, 5)
    for x in range(cx - 28, cx + 29):
        t = (x - cx) / 28
        dy = math.sqrt(max(1 - t * t, 0)) * 6
        for sgn in (-1, 1):
            y = int(round(cy + 2 + sgn * dy * .55 - t * 5))
            inside = math.hypot(x - cx, y - cy) < r
            if sgn > 0 or not inside:
                c.px(x, y, 12 if B4[y & 3][x & 3] < 10 else 4)
                if not inside or sgn > 0:
                    c.dpx(x, y + 1, c.get(x, y + 1), 13, 4)
    skyline(c, p[1], p[2], G - 12, 9, 14, [13, 13], 0, 60, haze=10, hz=2)
    deck, tl, tr = 76, 24, 96
    for tx in (tl, tr):
        c.rect(tx - 2, 40, tx + 1, deck + 22, 10)
        c.rect(tx - 2, 40, tx - 2, deck + 22, 14)
        c.rect(tx - 3, 38, tx + 2, 39, 14)
        c.px(tx, 36, 6)
        c.px(tx - 1, 37, 12)
        halo(c, tx, 36, 1, 4, 12)
    for x in range(-2, W + 2):
        c.px(x, deck, 14)
        c.px(x, deck + 1, 10)
        c.px(x, deck + 2, 10)
        if x % 6 == 0:
            c.px(x, deck - 1, 3)
            c.px(x, deck + 3, 13)
    for x in range(tl, tr + 1):
        t = (x - tl) / (tr - tl)
        y = int(deck - 1 - (deck - 42) * 4 * t * (1 - t))
        c.px(x, y, 14)
        c.px(x, y + 1, 9)
        if x % 4 == 0:
            for yy in range(y + 2, deck - 1):
                c.px(x, yy, 9)
    for x in range(-2, tl):
        y = int(41 + (tl - x) / (tl + 2) * (deck - 43))
        c.px(x, y, 14)
        if x % 4 == 0:
            for yy in range(y + 1, deck - 1):
                c.px(x, yy, 9)
    for x in range(tr, W + 2):
        y = int(41 + (x - tr) / (W + 2 - tr) * (deck - 43))
        c.px(x, y, 14)
        if x % 4 == 0:
            for yy in range(y + 1, deck - 1):
                c.px(x, yy, 9)
    skyline(c, (p[1] + p[3]) // 2 + 4, (p[2] + p[4]) // 2 + 4, G - 4, 10, 14, [13, 12, 13, 3], 1, 80)
    nb = skyline(c, p[3] + 8, p[4] + 14, G, 0, 10, [3, 12, 7, 12, 13, 3], 2, 100, bbn=p[5] - 2)
    nearpass(c, nb, 14, [7, 12, 8], 15)
    for y in range(52, 74):
        c.px(112, y, 15 if (y // 3) % 2 else 11)
    glow2(c, 112, 52, 112, 73, 15, 3)
    cars(c, [(10, 20, 1, 5, 12), (74, 34, -1, 4, 7), (50, 62, 1, 3, 3)])
    street(c, 7)
    rain(c, 22, 60)
    return c


def scene2():
    c = C(SC[2])
    p = SC[2]['p']
    sky(c, [0, 1, 2, 13], wob=1.0, off=.1)
    stars(c, 6, 7)
    X = 44
    for y in range(16, 90):
        if y < 30:
            hw = 5 if y > 19 else 3
        elif y < 36:
            hw = 28
        elif y < 60:
            hw = 14 - (y - 36) // 6
        else:
            hw = 7 + (y - 60) // 5 if y < 70 else 6
        for x in range(X - hw, X + hw + 1):
            v = 9 if B4[y & 3][x & 3] < 4 + (y - 16) // 8 else 2
            if x == X - hw:
                v = 13
            c.px(x, y, v)
    for i in range(10):
        c.px(X - 28 + i // 2, 33 - i, 9)
        c.px(X + 28 - i // 2, 33 - i, 9)
    c.rect(X - 1, 8, X, 15, 9)
    c.px(X, 7, 6)
    halo(c, X, 7, 1, 4, 12)
    c.rect(X - 4, 22, X + 4, 23, 8)
    glow2(c, X - 4, 22, X + 4, 23, 8, 2)
    c.rect(X - 3, 42, X + 3, 43, 12)
    c.px(X, 42, 3)
    glow2(c, X - 3, 42, X + 3, 43, 12, 3)
    c.rect(X - 16, 40, X - 14, 70, 9)
    c.rect(X + 14, 40, X + 16, 70, 9)
    c.rect(X - 8, 70, X - 3, 90, 9)
    c.rect(X + 3, 70, X + 8, 90, 9)
    skyline(c, p[1] - 4, p[2] + 6, G - 10, 9, 13, [13, 13, 8], 0, 50, haze=9, hz=2)
    skyline(c, (p[1] + p[3]) // 2 + 4, (p[2] + p[4]) // 2 + 8, G - 6, 10, 9, [13, 8, 13, 12], 1, 85)
    nb = skyline(c, p[3] + 2, p[4] + 6, G, 0, 10, [8, 12, 13, 8, 3, 12], 2, 110, bbn=p[5] - 3)
    nearpass(c, nb, 9, [12, 8, 7], 15)
    for y in range(28, 66):
        for x in range(100, 114):
            if y % 2 == 0 and hsh(x, y, 4) < 150 and abs(x - 107) < 7 - abs(y - 46) // 4:
                c.px(x, y, 7 if y % 4 else 11)
    glow2(c, 101, 32, 113, 62, 7, 2)
    cars(c, [(70, 24, -1, 3, 12), (12, 52, 1, 5, 8), (96, 70, -1, 11, 15)])
    street(c, 8)
    rain(c, 33, 95)
    return c


def scene3():
    c = C(SC[3])
    p = SC[3]['p']
    sky(c, [0, 1, 2, 13], wob=.7, off=.25)
    stars(c, 16, 9)
    cx, cy, r = p[6], p[7], p[8]
    halo(c, cx, cy, r, r + 12, 2)
    halo(c, cx, cy, r, r + 6, 13)
    disc(c, cx, cy, r, [4, 11, 5, 13])
    for dx, dy, rr in ((-4, -3, 2), (3, 2, 3), (-2, 6, 2), (5, -5, 1)):
        for yy in range(-rr, rr + 1):
            for xx in range(-rr, rr + 1):
                if math.hypot(xx, yy) <= rr:
                    c.px(cx + dx + xx, cy + dy + yy, 13 if xx + yy <= 0 else 5)
    ax, ay = 82, 22
    for y in range(-5, 6):
        hw = int(24 * math.sqrt(max(1 - (y / 5.5) ** 2, 0)))
        for x in range(-hw, hw + 1):
            v = 10 if y > -2 else 9
            if y == -5 or (y == -4 and abs(x) < hw - 2):
                v = 14
            if y > 3:
                v = 0
            c.px(ax + x, ay + y, v)
    for x in range(-18, 18, 3):
        c.px(ax + x, ay + 1, 3 if x % 2 else 12)
    for d_ in (-22, -20):
        c.rect(ax + d_, ay - 9, ax + d_ + 1, ay - 3, 10)
    c.rect(ax - 26, ay - 2, ax - 22, ay + 2, 0)
    c.rect(ax - 6, ay + 6, ax + 6, ay + 8, 0)
    c.rect(ax - 6, ay + 6, ax + 6, ay + 6, 14)
    c.px(ax + 24, ay, 6)
    c.px(ax - 25, ay - 1, 12)
    halo(c, ax + 24, ay, 1, 4, 6)
    for y in range(ay + 9, G):
        t = y - ay - 9
        hw = 1 + t // 5
        for x in range(ax + 2 - hw - t // 4, ax + 2 + hw - t // 4 + 1):
            if c.get(x, y) in DARK and B4[y & 3][x & 3] < max(7 - t // 12, 2):
                c.px(x, y, 13 if x & 1 else 5)
    skyline(c, p[1] - 14, p[2] - 18, G - 14, 9, 13, [13, 12, 13], 0, 60, haze=10, hz=2)
    skyline(c, (p[1] + p[3]) // 2 - 6, (p[2] + p[4]) // 2 - 10, G - 6, 10, 13, [3, 12, 13, 12], 1, 95)
    nb = skyline(c, p[3] - 4, p[4] - 4, G, 0, 10, [3, 12, 3, 12, 15, 13], 2, 120, bbn=p[5] - 5)
    nearpass(c, nb, 14, [12, 15, 3], 7)
    gx = 12
    c.rect(gx, 54, gx + 1, G, 12)
    c.rect(gx + 14, 54, gx + 15, G, 12)
    c.rect(gx - 3, 51, gx + 18, 52, 12)
    c.rect(gx - 1, 57, gx + 16, 57, 12)
    c.rect(gx + 5, 52, gx + 10, 57, 0)
    c.rect(gx + 6, 53, gx + 9, 56, 3)
    glow2(c, gx - 3, 51, gx + 18, G, 12, 3)
    cars(c, [(60, 38, -1, 5, 12), (22, 66, 1, 3, 6), (100, 52, -1, 11, 3)])
    street(c, 12)
    rain(c, 44, 80)
    return c


def save(c, sc, name):
    pal = {**FIX, **sc['pal']}
    im = Image.fromarray(c.a, 'P')
    flat = []
    for i in range(16):
        flat += list(pal.get(i, (0, 0, 0)))
    im.putpalette(flat)
    im.save(os.path.join(HERE, name))
    return im


if __name__ == '__main__':
    ims = []
    for i, f in enumerate((scene0, scene1, scene2, scene3)):
        ims.append(save(f(), SC[i], 'scene%02d.png' % i))
    pv = Image.new('RGB', (480, 448))
    for i, im in enumerate(ims):
        pv.paste(im.convert('RGB').resize((240, 224), Image.Resampling.NEAREST), ((i % 2) * 240, (i // 2) * 224))
    pv.save(os.path.join(HERE, 'preview_a.png'))
