"""CHix full-screen pictures v4: clear and victory only (128x128, indexed, own 16 colours each).
Deterministic. Run: python paint_screens_v4.py  -> screens/{clear,victory}.png + preview_screens4.png
(menu and gameover stay with paint_screens_v3.py; this script never writes them.)

Index rules (docs/ROUND1-PAINT-BRIEF.md): 0 near-black (panel fill), 4 near-white (text), 3 strong gold (text),
13 mid-dark (selection bar, white reads on it), 7/8/9 bright saturated neons that ROTATE (signs, windows,
reflections, sparks only). Everything else is free per screen. Helpers copied from paint_b.py (Bayer 4x4 look)."""
import math, random, os
from PIL import Image, ImageDraw

W, H = 128, 128
B4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "screens")
PANELS = {"menu": (8, 37, 119, 99), "clear": (7, 33, 120, 79), "gameover": (24, 50, 103, 75),
          "victory": (24, 50, 103, 75)}


def th(x, y): return (B4[int(y) & 3][int(x) & 3] + .5) / 16


def mask(pts):
    im = Image.new("L", (W, H), 0); ImageDraw.Draw(im).polygon([(float(a), float(b)) for a, b in pts], fill=255)
    return [(x, y) for y in range(H) for x in range(W) if im.getpixel((x, y))]


class Cv:
    def __init__(s, pal, seed):
        assert len(pal) == 16
        s.pal = pal; s.r = random.Random(seed)
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

    def fill(s, pts, c):
        for x, y in mask(pts): s.px(x, y, c(x, y) if callable(c) else c)

    def disc(s, cx, cy, r, c, ry=None):
        ry = ry or r
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                if ((x - cx) / r) ** 2 + ((y - cy) / ry) ** 2 <= 1: s.px(x, y, c(x, y) if callable(c) else c)

    def line(s, x0, y0, x1, y1, c):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            t = i / n; x, y = round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t)
            s.px(x, y, c(x, y) if callable(c) else c)

    def lift(s, x, y, c):
        if c is not None and s.L[c] > s.L[s.get(x, y)]: s.px(x, y, c)

    def glow(s, cx, cy, r, rmp, k=1., ry=None, y1=H, pw=1.6):
        ry = ry or r
        for y in range(max(0, int(cy - ry) - 1), min(y1, int(cy + ry) + 2)):
            for x in range(max(0, int(cx - r) - 1), min(W, int(cx + r) + 2)):
                d = math.hypot((x - cx) / r, (y - cy) / ry)
                if d >= 1: continue
                u = (1 - d) ** pw * k * len(rmp); i = int(u)
                if i >= len(rmp): c = rmp[-1]
                else: c = rmp[i] if th(x, y) < u - i else (rmp[i - 1] if i else None)
                s.lift(x, y, c)

    def cone(s, ax, ay, ang, half, ln, rmp, k=1., y1=H):
        a0 = math.radians(ang)
        for y in range(min(H, y1)):
            for x in range(W):
                dx, dy = x - ax, y - ay; d = math.hypot(dx, dy)
                if d < 1 or d > ln: continue
                da = abs((math.atan2(dy, dx) - a0 + math.pi) % (2 * math.pi) - math.pi)
                w = math.radians(half)
                if da > w: continue
                f = (1 - da / w) ** .7 * (1 - d / ln) ** .8 * k
                u = f * len(rmp); i = int(u)
                c = rmp[-1] if i >= len(rmp) else (rmp[i] if th(x, y) < u - i else (rmp[i - 1] if i else None))
                s.lift(x, y, c)

    def image(s):
        im = Image.new("P", (W, H)); flat = []
        for p in s.pal: flat += list(p)
        im.putpalette(flat); im.putdata([v for row in s.a for v in row]); return im

    def mean_lum(s): return sum(s.L[v] for row in s.a for v in row) / (W * H)


def sky(c, stops, y0, y1, pw=1.):
    n = len(stops) - 1
    for y in range(y0, y1):
        t = ((y - y0) / max(1, y1 - y0 - 1)) ** pw * n; i = min(int(t), n - 1)
        for x in range(W): c.px(x, y, c.mix(x, y, stops[i], stops[i + 1], t - i))


def stars(c, n, y1, cols, seed, bg):
    rr = random.Random(seed)
    for i in range(n):
        x, y = rr.randrange(W), rr.randrange(y1)
        if c.get(x, y) in bg: c.px(x, y, cols[i % len(cols)])


def win_grid(c, x0, x1, y0, y1, cols, lit, rr, dx=2, dy=3, ww=1, wh=1, hz=None):
    for y in range(y0, y1, dy):
        floor_on = rr.random() < lit * 1.6
        for x in range(x0, x1, dx):
            if floor_on and rr.random() < .7 or rr.random() < lit * .3:
                col = rr.choice(cols)
                for yy in range(y, min(y1, y + wh)):
                    for xx in range(x, min(x1, x + ww)): c.px(xx, yy, hz(xx, yy, col) if hz else col)


def tower(c, x0, x1, top, base, body, side, rim, rr, wins=(), lit=.3, hz=None, dx=2, dy=3, crown=0, ant=0,
          beacon=6, ww=1, wh=1, lside=True):
    H_ = lambda x, y, col: hz(x, y, col) if hz else col
    if crown:
        cw = max(2, (x1 - x0) // 3); cx0 = (x0 + x1) // 2 - cw // 2
        c.rect(cx0, top - crown, cx0 + cw, top - 1, lambda x, y: H_(x, y, body))
        c.px(cx0 if lside else cx0 + cw, top - crown, H_(cx0, top - crown, rim))
    for y in range(top, base):
        for x in range(x0, x1 + 1):
            col = body
            if (x >= x1 - (x1 - x0) // 3) == lside: col = side
            if x == (x0 if lside else x1): col = rim if y % 2 or y < top + 6 else body
            if y == top: col = rim
            c.px(x, y, H_(x, y, col))
    if wins: win_grid(c, x0 + 2, x1 - 1, top + 3, base - 2, wins, lit, rr, dx, dy, ww, wh, hz=hz)
    if ant:
        ax = x0 + (x1 - x0) * 2 // 3
        top2 = top - crown
        for y in range(top2 - ant, top2): c.px(ax, y, H_(ax, y, side))
        c.px(ax, top2 - ant - 1, beacon)


def skyline(c, seed, x0, x1, tops, base, body, side, rim, wins, lit, hz=None, wr=(4, 8), gap=(0, 2), **kw):
    rr = random.Random(seed); x = x0
    while x < x1:
        w = rr.randint(*wr); top = rr.randint(*tops(x)) if callable(tops) else rr.randint(*tops)
        tower(c, x, x + w, top, base, body, side, rim, rr, wins=wins, lit=lit, hz=hz,
              ant=rr.choice((0, 0, 3, 5)), crown=rr.choice((0, 0, 2, 3)), **kw)
        x += w + rr.randint(*gap)


def vsign(c, x, y, h, col, hot, frame, glow_r=7, k=.5, rmp=None, dead=()):
    c.rect(x - 1, y - 1, x + 3, y + h, frame)
    rr = random.Random(x * 31 + y)
    for yy in range(y, y + h):
        if (yy - y) % 4 == 3: continue
        for xx in range(x, x + 3):
            if rr.random() < .62: c.px(xx, yy, dead[0] if (yy - y) // 4 in dead[1:] else col) if dead else c.px(xx, yy, col)
        if rr.random() < .3 and not (dead and (yy - y) // 4 in dead[1:]): c.px(x + 1, yy, hot)
    if rmp: c.glow(x + 1, y + h / 2, glow_r, rmp, k, ry=h / 2 + glow_r * .6)


def hsign(c, x, y, w, h, col, hot, frame, rmp=None, k=.45):
    c.rect(x - 1, y - 1, x + w, y + h, frame)
    rr = random.Random(x * 17 + y * 3)
    for xx in range(x, x + w):
        if (xx - x) % 5 == 4: continue
        for yy in range(y, y + h):
            if rr.random() < .6: c.px(xx, yy, col)
    c.px(x + rr.randrange(w), y + rr.randrange(h), hot)
    if rmp: c.glow(x + w / 2, y + h / 2, w / 2 + 6, rmp, k, ry=h / 2 + 5)


def cable(c, x0, y0, x1, y1, sag, col, lights=None, every=4):
    n = int(abs(x1 - x0)) + 1
    for i in range(n + 1):
        t = i / n; x = x0 + (x1 - x0) * t; y = y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)
        c.px(round(x), round(y), col)
        if lights is not None and i % every == every // 2:
            c.px(round(x), round(y) + 1, lights[(i // every) % len(lights)] if isinstance(lights, list) else lights)


def car(c, x, y, d, body, roof, head, tail, trail, k=.6, glow_rmp=None):
    for i in range(2, 12):
        tx = x - d * i + (4 if d < 0 else 0)
        if th(tx, y + 1) < (1 - i / 12) * .8: c.px(tx, y + 1, trail)
    c.rect(x, y, x + 4, y + 1, body); c.px(x + 1, y - 1, roof); c.px(x + 2, y - 1, roof); c.px(x + 3, y - 1, roof)
    c.px(x + (4 if d > 0 else 0), y, head); c.px(x + (0 if d > 0 else 4), y, tail); c.px(x + 2, y + 2, trail)
    c.glow(x + (5 if d > 0 else -1), y, 5, glow_rmp or [head], k)


def stream(c, pts, cols, gap, seed, y1=H):
    rr = random.Random(seed); seg = []
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        n = int(math.hypot(bx - ax, by - ay)) + 1
        for i in range(n): seg.append((ax + (bx - ax) * i / n, ay + (by - ay) * i / n))
    i = 0
    while i < len(seg):
        ln = rr.randint(1, 3); col = rr.choice(cols)
        for j in range(ln):
            if i + j < len(seg):
                x, y = seg[i + j]
                if y < y1: c.px(round(x), round(y), col if j == 0 else (col if th(x, y) < .6 else None))
        i += ln + rr.randint(gap, gap + 3)


def rain(c, n, cols, seed, y1, slant=1, lit=None, y0=-4, lens=(3, 4, 4, 5, 6)):
    rr = random.Random(seed)
    for _ in range(n):
        x, y = rr.randrange(W + 8), rr.randrange(y0, y1)
        ln = rr.choice(lens); col = rr.choice(cols)
        for i in range(ln):
            X, Y = x - (i * slant) // 2, y + i
            if 0 <= Y < y1:
                cur = c.get(X, Y)
                cc = lit if (lit is not None and c.L[cur] > c.L[col]) else col
                if i == ln - 1 and ln > 3: cc = cols[0]
                if c.L[cc] > c.L[cur] or cur in (0, 1): c.px(X, Y, cc)


def splashes(c, n, col, dim, seed, y0):
    rr = random.Random(seed)
    for _ in range(n):
        x, y = rr.randrange(2, W - 2), rr.randrange(y0 + 3, H - 1)
        c.px(x - 1, y, dim); c.px(x + 1, y, dim); c.px(x, y - 1, col)


def reflect(c, hor, dk, base, stretch=.5, fade=30, wob=None, ripple=4):
    snap = [row[:] for row in c.a]
    for y in range(hor, H):
        d = y - hor
        src = max(0, hor - 1 - int(d * stretch))
        f = max(0., 1 - d / fade)
        for x in range(W):
            ox = wob(x, y) if wob else 0
            p = snap[src][max(0, min(W - 1, x + ox))]
            q = dk.get(p, p)
            b = c.ramp(x, y, base, d / (H - hor))
            t = th(x, y)
            if c.L[p] > 110: col = p if t < f * .85 else (q if t < f + .25 else b)
            else: col = q if t < f * .8 + .2 else b
            if d % ripple == ripple - 1 and t < .5: col = b
            c.px(x, y, col)


def shopfront(c, x0, x1, y, cols, awn, frame, rmp, k=.5):
    for x in range(x0, x1 + 1):
        c.px(x, y - 6, frame); c.px(x, y - 5, awn if x % 2 else frame)
        for yy in range(y - 4, y):
            col = cols[(x // 3) % len(cols)]
            if x % 7 == 0: col = frame
            elif yy == y - 1 and x % 3 == 1: col = frame
            c.px(x, yy, col)
    c.glow((x0 + x1) / 2, y - 2, (x1 - x0) / 2 + 5, rmp, k, ry=5)


def wob1(x, y): return 1 if (y // 2 + x // 5) % 3 == 0 else 0


def lanes(c, y0, col):
    for i in range(0, W + 16, 12):
        c.line(i + 4, y0 + 8, i + 7, y0 + 8, col); c.line(i * 1.3 - 10, y0 + 18, i * 1.3 - 5, y0 + 18, col)


# ================================================================== CLEAR: fireworks over the skyline (v4)
def burst(c, cx, cy, r, n, cols, seed, droop=0., halo=(2, 10, 12), inner=None, tip=4, crackle=0):
    """A chrysanthemum: halo, streaks from hot core to coloured tails, bright tips, optional inner ring."""
    rr = random.Random(seed)
    c.glow(cx, cy, r * 1.7, list(halo), .75, pw=1.3)
    for i in range(n):
        a = 2 * math.pi * i / n + rr.uniform(-.09, .09)
        L = r * rr.uniform(.8, 1.06); col = cols[i % len(cols)]
        steps = int(L * 1.4) + 1
        for s in range(steps):
            t = s / steps
            x = cx + math.cos(a) * L * t; y = cy + math.sin(a) * L * t + droop * (t * t) * L
            if t < .25: continue
            if th(x, y) < .25 + t * .75: c.px(x, y, 5 if t < .4 else col)
        tx, ty = cx + math.cos(a) * L, cy + math.sin(a) * L + droop * L
        c.px(tx, ty, tip)
        if droop:
            for k in range(1, 5):
                if th(tx, ty + k * 2) < .7 - k * .13: c.px(tx, ty + k * 2, col)
    if inner:
        ri, icols = inner
        for i in range(n // 2 + 2):
            a = 2 * math.pi * (i + .5) / (n // 2 + 2)
            for s in range(int(ri)):
                t = s / ri
                if t > .35 and th(cx + math.cos(a) * ri * t, cy + math.sin(a) * ri * t) < .8:
                    c.px(cx + math.cos(a) * ri * t, cy + math.sin(a) * ri * t, icols[i % len(icols)])
            c.px(cx + math.cos(a) * ri, cy + math.sin(a) * ri, 4)
    for _ in range(crackle):                                         # glitter crackling around the shell
        a = rr.uniform(0, 2 * math.pi); d = r * rr.uniform(.9, 1.5)
        x, y = cx + math.cos(a) * d, cy + math.sin(a) * d + droop * r
        c.px(x, y, rr.choice((4, 5, cols[0])))
    c.glow(cx, cy, 3.5, [5, 4], 1.)
    c.px(cx, cy, 4)


def trail(c, x0, y0, y1, col, hot, top_cut=None):
    """A rising rocket: sparse dithered sparks fading toward the ground."""
    for y in range(y1, y0):
        if top_cut and top_cut[0] <= y <= top_cut[1]: continue
        f = 1 - (y - y1) / (y0 - y1)
        if th(x0, y) < .15 + .6 * f: c.px(x0 + ((y // 3) % 2), y, col)
    c.px(x0, y1, hot); c.px(x0, y1 - 1, 4)


def clear():
    pal = [(6, 2, 16), (20, 8, 42), (44, 18, 80), (255, 212, 60), (255, 255, 255), (255, 236, 186), (255, 70, 96),
           (0, 240, 255), (255, 50, 220), (120, 255, 80), (96, 34, 116), (255, 172, 96), (200, 72, 150),
           (60, 28, 92), (150, 90, 206), (255, 124, 40)]
    c = Cv(pal, 201)
    HOR = 110
    sky(c, [0, 0, 1, 1, 2, 13, 10, 12], 0, HOR, pw=1.5)
    stars(c, 26, 40, [14, 5, 13], 202, (0, 1))
    # thin smoke drifting from earlier shells, lit pink from below
    for sx, sy, ln in ((4, 30, 30), (70, 31, 40), (40, 3, 22)):
        for x in range(sx, min(W, sx + ln)):
            yy = sy + int(1.5 * math.sin(x * .25))
            for k in range(3):
                if th(x, yy + k) < .45 - k * .1: c.px(x, yy + k, 13 if k < 2 else 10)
    # THE HERO: big shells in the open sky above the panel (y0..32), small ones low at the sides under it
    burst(c, 22, 15, 15, 28, [3, 15, 11], 210, droop=.3, halo=(2, 10, 15), crackle=14)
    burst(c, 106, 15, 15, 28, [8, 7, 12], 211, inner=(6, [4, 5, 9]), halo=(2, 10, 12), crackle=14)
    burst(c, 64, 12, 11, 22, [9, 7, 4], 212, inner=(4, [8, 3]), halo=(2, 13, 10), crackle=10)
    burst(c, 43, 26, 5, 12, [7, 5], 213, halo=(2, 10), crackle=4)
    burst(c, 86, 27, 5, 12, [3, 6], 214, halo=(2, 10), crackle=4)
    burst(c, 124, 2, 4, 10, [9, 5], 215, halo=(2,), crackle=3)
    burst(c, 3, 3, 4, 10, [6, 3], 216, halo=(2,), crackle=3)
    burst(c, 17, 88, 8, 18, [8, 9, 4], 217, droop=.2, halo=(2, 10, 12), crackle=6)
    burst(c, 111, 87, 8, 18, [3, 7, 11], 218, droop=.2, halo=(2, 10, 12), crackle=6)
    # glitter hanging in the top band
    rr = random.Random(220)
    for _ in range(46):
        x, y = rr.randrange(W), rr.randrange(32)
        if c.get(x, y) in (0, 1, 2, 13): c.px(x, y, rr.choice((3, 5, 7, 8, 9, 15, 4)))
    # rockets still climbing (cut where the panel covers them)
    trail(c, 34, HOR, 84, 11, 5, top_cut=None)
    trail(c, 96, HOR, 82, 12, 4)
    trail(c, 64, 33, 25, 11, 5)
    # far city, warm haze, low so the sky stays open
    hzf = lambda x, y, col: c.mix(x, y, col, 12, max(0, (y - 88) / 34))
    skyline(c, 230, -2, W, lambda x: (98, 103) if (x < 26 or x > 100) else (84, 94), HOR, 2, 10, 14,
            [3, 11, 15, 7, 8], .5, hz=hzf, wr=(4, 7))
    c.glow(64, HOR, 70, [10, 12], .5, ry=16)
    # mid blocks below the panel: busy, lit, signed; the sides stay low under the side shells
    rr = random.Random(240)
    for x0, x1, top, ws in ((0, 9, 101, [3, 15, 5]), (24, 34, 97, [3, 15, 5, 9]), (36, 46, 96, [11, 3, 7]),
                            (50, 62, 88, [3, 5, 8]), (66, 76, 94, [15, 3, 7, 11]), (80, 92, 90, [5, 3, 9]),
                            (95, 104, 97, [11, 15, 8]), (120, 127, 100, [9, 3, 5])):
        tower(c, x0, x1, top, HOR, 1, 13, 14, rr, wins=ws, lit=.65, dy=3, crown=rr.choice((0, 2)),
              ant=rr.choice((0, 3)), beacon=6)
    # edge towers framing the panel band, tops below the big shells
    tower(c, 0, 6, 40, HOR, 1, 13, 14, rr, wins=[3, 15, 7], lit=.55, dx=2, dy=3, ant=5, beacon=6)
    tower(c, 121, 127, 42, HOR, 1, 13, 14, rr, wins=[11, 8, 9], lit=.55, dx=2, dy=3, lside=False, crown=3)
    vsign(c, 2, 46, 18, 8, 4, 0, rmp=[10, 12], k=.45)
    vsign(c, 123, 50, 16, 7, 4, 0, rmp=[10, 12], k=.45)
    hsign(c, 25, 100, 7, 2, 8, 4, 0, rmp=[10, 12], k=.4)
    hsign(c, 82, 93, 8, 3, 9, 4, 0, rmp=[10, 14], k=.4)
    hsign(c, 52, 91, 8, 3, 7, 4, 0, rmp=[12, 11], k=.4)
    # festive light strings between the blocks
    cable(c, 9, 101, 24, 98, 2, 13, lights=[3, 7, 8, 9, 6], every=3)
    cable(c, 34, 94, 50, 90, 2, 13, lights=[9, 3, 8, 7, 15], every=3)
    cable(c, 76, 96, 92, 92, 2, 13, lights=[8, 3, 9], every=3)
    cable(c, 104, 99, 120, 100, 2, 13, lights=[7, 15, 9], every=3)
    for x0, x1, cols in ((0, 9, [3, 15, 5]), (24, 34, [7, 11, 5]), (36, 46, [15, 3, 9]), (50, 62, [5, 3, 11]),
                         (66, 76, [8, 5, 3]), (80, 92, [3, 15, 7]), (95, 104, [11, 9, 5]), (120, 127, [15, 3, 8])):
        shopfront(c, x0, x1, HOR, cols, 6, 0, [12, 11], .45)
    c.rect(0, HOR - 1, W - 1, HOR - 1, 14)
    reflect(c, HOR, {0: 0, 1: 0, 2: 1, 13: 1, 10: 2, 12: 10, 14: 13, 11: 12, 5: 11, 4: 5, 3: 15, 15: 6, 6: 12,
                     7: 7, 8: 8, 9: 9}, [13, 2, 1, 0], stretch=1.2, fade=20, wob=wob1, ripple=3)
    # crowd silhouettes cheering on the quay, confetti
    rr = random.Random(250)
    for x in range(2, W - 2, 4):
        h = rr.randint(4, 6); x1 = x + rr.randint(0, 1)
        c.rect(x1, H - h, x1 + 2, H - 1, 0); c.px(x1 + 1, H - h - 1, 0)
        if rr.random() < .45: c.px(x1 + (3 if rr.random() < .5 else -1), H - h - 2, 0)
        c.px(x1, H - h, 13)
    for _ in range(24):
        x, y = rr.randrange(W), rr.randrange(82, H - 8)
        c.px(x, y, rr.choice((3, 5, 6, 7, 8, 9, 15, 4)))
    return c


# ================================================================== VICTORY: a deep dawn, the sun just breaking (v4)
def victory():
    # index 3 (gold) is the game's text colour only: the picture never uses it
    pal = [(10, 4, 20), (24, 10, 42), (42, 18, 64), (255, 204, 60), (255, 250, 236), (255, 228, 168), (196, 58, 84),
           (255, 60, 190), (0, 226, 255), (150, 255, 60), (84, 30, 88), (255, 160, 102), (148, 48, 96),
           (60, 26, 76), (112, 42, 104), (236, 100, 58)]
    c = Cv(pal, 401)
    HOR = 100
    SX, SY = 64, HOR - 3
    sky(c, [0, 1, 1, 2, 13, 10, 14, 12], 0, HOR, pw=1.7)
    stars(c, 30, 46, [4, 5, 14, 13], 402, (0, 1, 2))
    # a thin old moon fading in the west
    c.disc(15, 14, 4, 5); c.disc(16.6, 13, 4, 1)
    for x in range(10, 21):
        for y in range(9, 20):
            if c.get(x, y) == 1 and math.hypot(x - 15, y - 14) <= 4 and math.hypot(x - 16.6, y - 13) <= 4:
                c.px(x, y, c.mix(x, y, 1, 0, .5))
    c.glow(15, 14, 9, [2, 13], .5)
    # horizon glow: concentrated low and around the sun
    c.glow(SX, HOR, 80, [10, 14, 12], .9, ry=34, pw=1.2)
    c.glow(SX, HOR, 50, [12, 6, 15], .95, ry=22, pw=1.3)
    c.glow(SX, SY, 22, [15, 11, 5], 1., ry=14, pw=1.5)
    # a few faint rays, kept low (under the text panel)
    for a in range(-160, -19, 14):
        for t in range(12, 46):
            x = SX + math.cos(math.radians(a)) * t; y = SY + math.sin(math.radians(a)) * t * .7
            if 0 <= x < W and 77 < y < HOR and th(x, y) < .55 - t / 90:
                cur = c.get(x, y)
                c.px(x, y, {10: 14, 14: 12, 12: 6, 6: 15, 15: 11}.get(cur, cur))
    # the sun, a sliver above the horizon
    c.disc(SX, SY, 8, lambda x, y: 4 if math.hypot(x - SX, y - SY) < 5.5 else 5)
    # long thin dawn clouds: dark plum, lined rose/peach underneath where the light reaches
    for x0, x1, cy, seed in ((-4, 54, 36, 1), (72, 132, 30, 2), (30, 98, 18, 3), (-2, 30, 46, 4), (98, 130, 44, 5)):
        rr = random.Random(400 + seed); ph = rr.uniform(0, 6)
        for x in range(x0, x1):
            e = min(x - x0, x1 - x) / 10
            if e <= 0: continue
            th_ = min(3., e * 3) * (.7 + .3 * math.sin(x * .3 + ph))
            top = cy - th_ * .6; bot = cy + th_ * .5
            near = max(0., 1 - math.hypot(x - SX, cy - SY) / 110)
            for y in range(int(top), int(bot) + 1):
                if y < 0 or y >= HOR: continue
                v = (y - top) / max(1, bot - top)
                col = c.ramp(x, y, [2, 13, 13, 10], v)
                if y == int(bot): col = 12 if th(x, y) < .4 + near else 14
                if y == int(bot) and near > .45 and th(x, y) < near - .2: col = 11
                c.px(x, y, col)
    # birds
    for x, y in ((22, 30), (28, 27), (33, 32), (92, 22), (98, 24), (103, 20), (78, 40)):
        c.px(x - 1, y - 1, 13); c.px(x, y, 0); c.px(x + 1, y - 1, 13)
    # far skyline: contre-jour silhouettes against the glow, tops just catching the light
    rr = random.Random(410); x = -2
    while x < W:
        w = rr.randint(4, 8)
        top = (rr.randint(95, 98) if abs(x + w / 2 - SX) < 12 else rr.randint(90, 95)) if 38 < x < 88 else rr.randint(74, 88)
        for y in range(top, HOR):
            for xx in range(x, x + w + 1):
                if abs(xx - SX) < 9 and math.hypot(xx - SX, y - SY) < 8.5: continue      # sun stays clear
                c.px(xx, y, 13 if y > top else (12 if abs(xx - SX) > 22 else 11))
        win_grid(c, x + 2, x + w - 1, top + 3, HOR - 2, [8, 7, 9, 11], .1, rr, dx=2, dy=3)
        if rr.random() < .3:
            ax = x + w // 2
            for y in range(top - 4, top): c.px(ax, y, 13)
            c.px(ax, top - 5, 6)
        x += w + rr.randint(0, 2)
    c.disc(SX, SY, 8, lambda x, y: (4 if math.hypot(x - SX, y - SY) < 5.5 else 5) if y < HOR else None)
    # mid towers: dark silhouettes, warm rim on the sun side only
    rr = random.Random(420)
    for x0, x1, top in ((0, 12, 26), (14, 24, 44), (26, 35, 64), (93, 102, 60), (104, 114, 40), (116, 127, 22)):
        lside = x0 > 64
        tower(c, x0, x1, top, HOR, 1, 0, 1, rr, wins=[8, 7, 9, 11, 15], lit=.12, dx=3, dy=4, ww=2, lside=lside,
              crown=rr.choice((0, 4)), ant=rr.choice((0, 6)), beacon=6)
        rx = x0 if lside else x1                                   # sun-side edge
        for y in range(top, HOR):
            f = (y - top) / max(1, HOR - top)
            col = 11 if th(rx, y) < .7 - f * .8 else (15 if th(rx, y) < .9 - f * .5 else 12)
            c.px(rx, y, col)
            if th(rx, y + 2) < .3 - f * .3: c.px(rx + (1 if lside else -1), y, 6)
        for xx in range(x0, x1 + 1):                               # roof edge catches the dawn
            d = (xx - rx) * (1 if lside else -1)
            c.px(xx, top, 5 if d < 2 else (11 if d < 5 else 12))
    vsign(c, 3, 34, 18, 8, 4, 0, rmp=[13], k=.4)
    vsign(c, 120, 30, 16, 7, 4, 0, rmp=[13], k=.4)
    hsign(c, 106, 30, 7, 3, 9, 4, 0)
    # flying cars heading into the sunrise
    car(c, 30, 14, 1, 13, 14, 5, 6, 12, k=.4); car(c, 100, 8, -1, 13, 14, 5, 6, 12, k=.4)
    stream(c, [(-2, 84), (40, 87), (130, 85)], [11, 5, 15], 3, 421, y1=HOR)
    # street + river: the sun's path in the water
    for x0, x1, cols in ((0, 12, [15, 11, 7]), (14, 24, [9, 11, 8]), (93, 102, [7, 15, 11]), (116, 127, [11, 15, 8])):
        shopfront(c, x0, x1, HOR, cols, 6, 0, [12], .35)
    c.rect(0, HOR - 1, W - 1, HOR - 1, lambda x, y: 11 if abs(x - SX) < 14 else (15 if abs(x - SX) < 30 else 12))
    reflect(c, HOR, {0: 0, 1: 0, 13: 1, 2: 1, 10: 2, 14: 10, 12: 10, 6: 12, 15: 6, 11: 15, 5: 11, 4: 5,
                     7: 7, 8: 8, 9: 9}, [10, 2, 1, 0], stretch=.8, fade=24, wob=wob1, ripple=3)
    for y in range(HOR + 1, H):                                    # glitter path under the sun
        hw = 4 + (y - HOR) * .45
        for x in range(int(SX - hw), int(SX + hw) + 1):
            if th(x, y) < .6 - abs(x - SX) / (hw * 1.6) and (x + y) % 3:
                d = abs(x - SX) / hw
                c.px(x, y, 4 if d < .25 else (5 if d < .5 else 11))
    # quay rail silhouette with two figures watching the dawn
    c.rect(0, 120, W - 1, 120, 0); c.rect(0, 121, W - 1, H - 1, 0)
    for x in range(0, W, 8): c.rect(x, 116, x, 120, 0)
    c.line(0, 116, W - 1, 116, 0)
    c.line(0, 115, W - 1, 115, lambda x, y: (11 if abs(x - SX) < 20 else 15) if th(x, y) < .5 else 12)
    for fx in (44, 48):
        c.rect(fx, 108, fx + 2, 120, 0); c.disc(fx + 1, 106, 1.5, 0); c.px(fx + (2 if fx == 44 else 0), 105, 11)
        c.px(fx + (2 if fx == 44 else 0), 109, 15)
    c.px(46, 110, 0)
    used3 = sum(v == 3 for row in c.a for v in row)
    assert used3 == 0, "index 3 must stay text-only on victory (%d px)" % used3
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    out = []
    for name, f in (("clear", clear), ("victory", victory)):
        cv = f(); im = cv.image(); im.save(os.path.join(OUT, name + ".png")); out.append((name, im, cv))
        print("%-9s mean luminance %.1f" % (name, cv.mean_lum()))
    # preview at 4x: each picture raw, then with the game's panel (fill 0, edge 7, gold + light text bars)
    S = 4
    pv = Image.new("RGB", ((W * S + 8) * 2, (H * S + 8) * 2), (24, 24, 24))
    for i, (name, im, cv) in enumerate(out):
        rgb = im.convert("RGB")
        pv.paste(rgb.resize((W * S, H * S), Image.Resampling.NEAREST), (0, i * (H * S + 8)))
        p = rgb.copy(); d = ImageDraw.Draw(p); x0, y0, x1, y1 = PANELS[name]
        d.rectangle((x0, y0, x1, y1), fill=cv.pal[0], outline=cv.pal[7])
        for k, ci in enumerate((3, 4, 3)):
            if y0 + 4 + k * 11 + 6 < y1:
                d.rectangle((x0 + 8, y0 + 4 + k * 11, x0 + 8 + 48 - k * 8, y0 + 10 + k * 11), fill=cv.pal[ci])
        if name == "victory":                                         # a few firework particles over it
            rr = random.Random(5)
            for _ in range(40): d.point((rr.randrange(W), rr.randrange(H)), fill=cv.pal[rr.choice((7, 8, 9, 4))])
        pv.paste(p.resize((W * S, H * S), Image.Resampling.NEAREST), (W * S + 8, i * (H * S + 8)))
    pv.save(os.path.join(HERE, "preview_screens4.png"))


if __name__ == "__main__":
    main()
