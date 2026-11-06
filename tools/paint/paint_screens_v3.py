"""CHix full-screen pictures v3: menu, clear, gameover, victory (128x128, indexed, own 16 colours each).
Deterministic. Run: python paint_screens_v3.py  -> screens/{menu,clear,gameover,victory}.png + preview_screens3.png

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


# ================================================================== MENU: calm rainy night, ringed planet
def menu():
    pal = [(2, 4, 12), (8, 18, 38), (16, 36, 66), (255, 200, 70), (240, 248, 255), (176, 226, 244), (255, 86, 104),
           (0, 230, 255), (255, 60, 200), (80, 255, 160), (30, 66, 98), (122, 180, 206), (60, 118, 146),
           (34, 54, 86), (74, 104, 146), (255, 150, 60)]
    c = Cv(pal, 101)
    HOR = 106
    sky(c, [0, 1, 1, 2, 2, 10, 12], 0, HOR, pw=.9)
    stars(c, 34, 30, [4, 11, 5, 14], 102, (0, 1, 2))
    # ringed planet in the haze, lit from the upper left
    PX, PY, PR = 90, 17, 11
    c.glow(PX, PY, PR + 16, [2, 10, 14], .8, pw=1.3)
    TIL = math.radians(-18)

    def ring(front):
        out = []
        for t in range(900):
            a = t / 900 * 2 * math.pi
            for k, (rx, col) in enumerate(((23, 14), (21, 11), (19, 5), (17, 12))):
                ex, ey = rx * math.cos(a), rx * .24 * math.sin(a)
                x = PX + ex * math.cos(TIL) - ey * math.sin(TIL); y = PY + ex * math.sin(TIL) + ey * math.cos(TIL)
                if (math.sin(a) > 0) == front: out.append((round(x), round(y), col))
        return out
    for x, y, col in ring(False):
        if math.hypot(x - PX, y - PY) > PR + .3: c.px(x, y, col)
    for y in range(PY - PR, PY + PR + 1):
        for x in range(PX - PR, PX + PR + 1):
            d = math.hypot(x - PX, y - PY)
            if d > PR: continue
            lit = 1 - math.hypot(x - (PX - 5), y - (PY - 5)) / (PR * 1.7)
            band = .12 * math.sin((y - PY + (x - PX) * .3) * .9)
            col = c.ramp(x, y, [1, 2, 10, 12, 11, 5, 4], lit + band)
            if d > PR - 1: col = c.mix(x, y, col, 14, .5) if lit > .3 else 1
            c.px(x, y, col)
    for x, y, col in ring(True):
        c.px(x, y, {14: 10, 11: 12, 5: 11, 12: 2}[col] if math.hypot(x - PX, y - PY) <= PR and y < PY else col)
    for yy, x0, x1 in ((22, 66, 118), (26, 72, 127), (13, 58, 100)):     # haze streaks across the planet
        for x in range(x0, x1):
            if th(x, yy) < .45: c.px(x, yy, 10 if c.L[c.get(x, yy)] > c.L[10] else 2)
    # a slow airship crossing far behind
    c.disc(30, 9, 9, lambda x, y: c.ramp(x, y, [1, 2, 10, 14], .8 - (y - 5) / 9), ry=3)
    c.line(23, 7, 37, 7, 14); c.rect(25, 10, 35, 11, 0)
    c.rect(26, 10, 34, 10, lambda x, y: 7 if x % 3 else 4); c.glow(30, 10, 10, [2, 10], .5, ry=4)
    c.px(20, 9, 6); c.px(40, 9, 3)
    # far skyline, hazed
    hzf = lambda x, y, col: c.mix(x, y, col, 10, max(0, (y - 40) / 50))
    skyline(c, 110, -2, W, (28, 42), HOR, 2, 13, 14, [12, 11, 3], .25, hz=hzf, wr=(4, 8))
    # mid towers: tall, tops in the visible band, lit windows
    rr = random.Random(120)
    for x0, x1, top, cr, an in ((18, 30, 20, 3, 6), (36, 46, 26, 0, 0), (52, 64, 14, 4, 9), (70, 80, 24, 0, 4),
                                (98, 108, 22, 3, 0)):
        tower(c, x0, x1, top, HOR, 1, 13, 14, rr, wins=[3, 15, 11, 7, 9], lit=.32, crown=cr, ant=an, dy=3)
    # rooftop details on the mid towers: water tank, dish, billboard
    c.rect(38, 22, 41, 25, 13); c.line(38, 22, 41, 22, 14); c.line(38, 26, 38, 26, 1); c.line(41, 26, 41, 26, 1)
    c.disc(76, 21, 2, 13, ry=1); c.px(76, 19, 14)
    hsign(c, 66, 30, 13, 4, 8, 4, 0, rmp=[13, 12], k=.5)
    hsign(c, 99, 30, 9, 3, 9, 5, 0, rmp=[13, 12], k=.4)
    # near frame towers, edges
    tower(c, 0, 12, 6, HOR, 0, 1, 14, rr, wins=[3, 15, 5], lit=.3, dx=3, dy=4, ww=2, ant=0)
    tower(c, 112, 127, 12, HOR, 0, 1, 14, rr, wins=[5, 3, 7], lit=.3, dx=3, dy=4, ww=2, lside=False, crown=4, ant=5)
    vsign(c, 9, 12, 22, 7, 4, 0, rmp=[13, 12], k=.5)
    vsign(c, 114, 20, 16, 8, 4, 0, rmp=[13, 14], k=.5)
    hsign(c, 44, 33, 6, 3, 3, 4, 0, rmp=[13, 15], k=.35)
    for x, y in ((58, 4), (118, 6), (28, 16)):
        c.px(x, y, 6); c.glow(x, y, 4, [13, 6], .5)
    cable(c, 12, 30, 18, 32, 1, 0, lights=3, every=2)
    cable(c, 108, 34, 112, 36, 1, 0)
    # flying traffic
    stream(c, [(-2, 34), (50, 31), (130, 33)], [3, 5, 6, 11], 3, 121, y1=HOR)
    car(c, 82, 6, -1, 2, 14, 5, 6, 10, k=.5)
    car(c, 30, 28, 1, 2, 14, 4, 6, 12, k=.5)
    # street level: lit shopfronts just under the panel
    shopfront(c, 0, 12, HOR, [15, 3, 5], 6, 0, [13, 15], .5)
    shopfront(c, 18, 30, HOR, [7, 13, 11], 8, 0, [13, 12], .5)
    shopfront(c, 52, 64, HOR, [3, 15, 11], 9, 0, [13, 15], .5)
    shopfront(c, 70, 80, HOR, [9, 12, 5], 14, 0, [13, 12], .45)
    shopfront(c, 98, 108, HOR, [11, 7, 5], 6, 0, [13, 12], .45)
    shopfront(c, 112, 127, HOR, [15, 3, 13], 9, 0, [13, 15], .5)
    c.rect(0, HOR - 1, W - 1, HOR - 1, 14)
    reflect(c, HOR, {0: 0, 1: 0, 2: 1, 13: 1, 10: 2, 12: 10, 14: 13, 11: 12, 5: 11, 4: 5, 3: 15, 15: 6, 6: 13,
                     7: 7, 8: 8, 9: 9}, [13, 2, 1, 0], stretch=.6, fade=26, wob=wob1)
    lanes(c, HOR, 14)
    # a pedestrian with a neon umbrella, and her reflection
    UX, UY = 44, 113
    for k in range(-4, 5):
        c.px(UX + k, UY - 2 + abs(k) // 3, 8 if abs(k) < 4 else 4)
    for k in range(-3, 4): c.px(UX + k, UY - 3 + abs(k) // 2, 8)
    c.px(UX, UY - 4, 4); c.line(UX, UY - 1, UX, UY + 5, 0); c.rect(UX - 1, UY, UX + 1, UY + 5, 0)
    c.px(UX - 1, UY + 6, 0); c.px(UX + 1, UY + 6, 0); c.glow(UX, UY - 1, 7, [13, 12], .45, ry=4)
    for k in range(-4, 5, 2): c.px(UX + k, UY + 9 + abs(k) // 3, 8)
    c.rect(UX - 1, UY + 7, UX + 1, UY + 8, 1)
    # parked car under a street lamp
    c.rect(86, 113, 101, 116, 1); c.rect(89, 110, 98, 112, 13); c.rect(90, 111, 97, 111, 2)
    c.line(86, 113, 101, 113, 14); c.px(86, 114, 3); c.px(101, 114, 6); c.px(88, 117, 0); c.px(99, 117, 0)
    c.rect(118, 100, 118, 108, 13); c.px(117, 99, 4); c.cone(117, 100, 100, 18, 22, [13, 12, 11], .8)
    rain(c, 70, [10, 12, 11], 130, H, lit=5)
    splashes(c, 20, 11, 12, 131, HOR)
    return c


# ================================================================== CLEAR: fireworks over a lit city
def burst(c, cx, cy, r, n, cols, seed, droop=0., halo=(2, 10, 12)):
    rr = random.Random(seed)
    c.glow(cx, cy, r * 1.5, list(halo), .7, pw=1.4)
    for i in range(n):
        a = 2 * math.pi * i / n + rr.uniform(-.08, .08)
        L = r * rr.uniform(.75, 1.05); col = cols[i % len(cols)]
        steps = int(L * 1.3) + 1
        for s in range(steps):
            t = s / steps
            x = cx + math.cos(a) * L * t; y = cy + math.sin(a) * L * t + droop * (t * t) * L
            if t < .3: continue
            if th(x, y) < .35 + t * .65: c.px(x, y, col)
        tx, ty = cx + math.cos(a) * L, cy + math.sin(a) * L + droop * L
        c.px(tx, ty, 4)
        if droop:
            for k in range(1, 4):
                if th(tx, ty + k * 2) < .6 - k * .15: c.px(tx, ty + k * 2, col)
    c.glow(cx, cy, 4, [5, 4], 1.)
    c.px(cx, cy, 4)


def clear():
    pal = [(6, 2, 16), (26, 10, 54), (58, 22, 92), (255, 212, 60), (255, 255, 255), (255, 232, 176), (255, 70, 96),
           (0, 240, 255), (255, 50, 220), (120, 255, 80), (112, 38, 124), (255, 172, 96), (206, 76, 156),
           (64, 30, 96), (154, 92, 206), (255, 124, 40)]
    c = Cv(pal, 201)
    HOR = 110
    sky(c, [0, 1, 1, 2, 10, 12, 11], 0, HOR, pw=1.15)
    stars(c, 20, 30, [5, 14, 4], 202, (0, 1))
    # fireworks in the visible sky band (y0..32) and one low between towers
    burst(c, 30, 16, 14, 22, [3, 15, 11, 7], 210)
    burst(c, 96, 13, 13, 20, [8, 12, 5, 9], 211, droop=.35)
    burst(c, 63, 7, 7, 14, [9, 3, 4], 212)
    burst(c, 116, 30, 6, 12, [7, 5], 213)
    burst(c, 8, 4, 5, 10, [6, 3], 214)
    burst(c, 68, 92, 9, 16, [3, 8, 11], 215, droop=.25)
    for x0, y0, y1 in ((47, 108, 26), (80, 108, 36), (14, 108, 22)):        # rocket trails rising
        for y in range(y1, y0):
            if th(x0, y) < .5 * (y - y1) / (y0 - y1) + .1: c.px(x0 + (y % 5 == 0), y, 11)
        c.px(x0, y1 - 1, 4); c.px(x0, y1, 3)
    rr = random.Random(220)
    for _ in range(60):
        x, y = rr.randrange(W), rr.randrange(34)
        if c.get(x, y) in (0, 1, 2): c.px(x, y, rr.choice((3, 5, 7, 8, 9, 15)))
    # searchlights criss-crossing
    c.cone(20, HOR, -70, 3, 120, [2, 10, 14], .5)
    c.cone(108, HOR, -112, 3, 120, [2, 10, 14], .5)
    # far city, warm haze
    hzf = lambda x, y, col: c.mix(x, y, col, 12, max(0, (y - 70) / 45))
    skyline(c, 230, -2, W, (66, 84), HOR, 2, 10, 14, [3, 11, 15, 7, 8], .5, hz=hzf, wr=(4, 7))
    c.glow(64, HOR, 80, [10, 12, 11], .6, ry=28)
    # tall towers at the edges and a spire, tops above the panel
    rr = random.Random(240)
    tower(c, 0, 12, 20, HOR, 1, 13, 14, rr, wins=[3, 15, 5, 7], lit=.6, dx=3, dy=3, ww=2, ant=8)
    tower(c, 113, 127, 24, HOR, 1, 13, 14, rr, wins=[3, 11, 8, 9], lit=.6, dx=3, dy=3, ww=2, lside=False, crown=5)
    tower(c, 50, 60, 30, HOR, 1, 13, 14, rr, wins=[3, 5, 15], lit=.6, crown=6, ant=12, beacon=4)
    c.glow(57, 11, 4, [12, 5], .7)
    vsign(c, 9, 24, 26, 7, 4, 0, rmp=[10, 14], k=.5)
    vsign(c, 115, 28, 22, 8, 4, 0, rmp=[10, 12], k=.5)
    # mid layer below the panel: busy lit blocks with signs
    for x0, x1, top, ws in ((14, 26, 84, [3, 15, 5, 9]), (28, 40, 90, [11, 3, 7]), (64, 76, 86, [3, 5, 8]),
                            (80, 94, 82, [15, 3, 7, 11]), (96, 110, 88, [5, 3, 9])):
        tower(c, x0, x1, top, HOR, 1, 13, 14, rr, wins=ws, lit=.65, dy=3, crown=rr.choice((0, 3)))
    hsign(c, 16, 87, 9, 3, 8, 4, 0, rmp=[10, 12], k=.4)
    hsign(c, 82, 85, 10, 4, 9, 4, 0, rmp=[10, 14], k=.4)
    hsign(c, 98, 91, 8, 3, 3, 4, 0, rmp=[12, 11], k=.4)
    hsign(c, 30, 93, 8, 3, 7, 4, 0, rmp=[10, 14], k=.4)
    # festive light strings between towers
    cable(c, 12, 82, 50, 86, 4, 13, lights=[3, 7, 8, 9, 6], every=3)
    cable(c, 60, 84, 113, 82, 4, 13, lights=[9, 3, 8, 7, 15], every=3)
    cable(c, 26, 96, 64, 98, 3, 13, lights=[8, 3, 9], every=3)
    for x0, x1, cols in ((0, 12, [3, 15, 5]), (14, 26, [7, 11, 5]), (28, 40, [15, 3, 9]), (50, 60, [5, 3, 11]),
                         (64, 76, [8, 5, 3]), (80, 94, [3, 15, 7]), (96, 110, [11, 9, 5]), (113, 127, [15, 3, 8])):
        shopfront(c, x0, x1, HOR, cols, 6, 0, [12, 11], .5)
    car(c, 38, 100, 1, 2, 14, 4, 6, 11, k=.5); car(c, 90, 97, -1, 2, 14, 5, 6, 12, k=.5)
    stream(c, [(-2, 30), (40, 28), (130, 31)], [3, 5, 6], 3, 241)
    c.rect(0, HOR - 1, W - 1, HOR - 1, 14)
    reflect(c, HOR, {0: 0, 1: 0, 2: 1, 13: 1, 10: 2, 12: 10, 14: 13, 11: 12, 5: 11, 4: 5, 3: 15, 15: 6, 6: 12,
                     7: 7, 8: 8, 9: 9}, [13, 2, 1, 0], stretch=.6, fade=22, wob=wob1, ripple=3)
    # crowd silhouettes cheering on the quay, confetti
    rr = random.Random(250)
    for x in range(2, W - 2, 4):
        h = rr.randint(4, 6); x1 = x + rr.randint(0, 1)
        c.rect(x1, H - h, x1 + 2, H - 1, 0); c.px(x1 + 1, H - h - 1, 0)
        if rr.random() < .45: c.px(x1 + (3 if rr.random() < .5 else -1), H - h - 2, 0)
        c.px(x1, H - h, 13)
    for _ in range(30):
        x, y = rr.randrange(W), rr.randrange(80, H - 8)
        c.px(x, y, rr.choice((3, 5, 6, 7, 8, 9, 15, 4)))
    return c


# ================================================================== GAMEOVER: rain, ruin, the fallen mecha
def gameover():
    pal = [(4, 4, 7), (16, 18, 25), (28, 32, 41), (214, 164, 52), (222, 226, 232), (128, 138, 150), (230, 36, 36),
           (255, 40, 80), (0, 204, 236), (236, 60, 210), (44, 48, 60), (92, 100, 114), (120, 28, 32),
           (58, 62, 78), (70, 78, 94), (255, 120, 40)]
    c = Cv(pal, 301)
    HOR = 88
    sky(c, [0, 1, 1, 1, 2, 10], 0, HOR, pw=.9)
    # low storm clouds, dithered underside
    rr = random.Random(302); ph = [rr.uniform(0, 6) for _ in range(3)]
    for x in range(W):
        h = 12 + 6 * math.sin(x * .07 + ph[0]) + 3 * math.sin(x * .19 + ph[1])
        for y in range(int(h) + 1): c.px(x, y, c.mix(x, y, 2, 1, min(1, (h - y) / 8 + .2)))
        c.px(x, int(h) + 1, c.mix(x, h, 10, None, .5))
    # red glow of fires and alarms on the horizon
    c.glow(30, HOR, 60, [10, 12, 12], .6, ry=26)
    c.glow(104, HOR - 6, 40, [10, 12], .5, ry=22)
    # far ruined skyline: jagged broken tops
    hzf = lambda x, y, col: c.mix(x, y, col, 10, max(0, (y - 60) / 60))
    rr = random.Random(310); x = -2
    while x < W:
        w = rr.randint(5, 9); top = rr.randint(34, 56)
        tower(c, x, x + w, top, HOR, 1, 2, 10, rr, wins=[11, 12, 3], lit=.06, hz=hzf, dy=3)
        for k in range(w + 1):                                      # bite out a broken crown
            cut = int(abs(math.sin(k * 1.7 + x)) * rr.randint(0, 6))
            for y in range(top, top + cut): c.px(x + k, y, c.get(x + k, top - 1))
        x += w + rr.randint(0, 2)
    # smoke columns
    for sx, sy, n, dr in ((30, 78, 16, .9), (100, 72, 12, -.7)):
        for i in range(n):
            cx = sx + dr * i + math.sin(i) * 1.5; cy = sy - i * 4; r = 3 + i * .5
            c.disc(cx, cy, r, lambda x, y: None if th(x, y) < .3 else c.ramp(x, y, [1, 2, 10, 12], max(0, .7 - i / n)))
    # mid towers: a broken tower leaning, dark windows, red warning beacons
    rr = random.Random(320)
    tower(c, 0, 14, 20, HOR, 1, 2, 14, rr, wins=[11, 3, 5], lit=.12, dx=3, dy=4, ww=2, ant=8, beacon=6)
    tower(c, 108, 127, 26, HOR, 1, 2, 14, rr, wins=[11, 12, 3], lit=.1, dx=3, dy=4, ww=2, lside=False)
    for k in range(20):                                             # snapped top of the right tower
        cut = int(4 + 9 * abs(math.sin(k * .7)))
        for y in range(26, 26 + cut): c.px(108 + k, y, c.get(108 + k, 25))
        c.px(108 + k, 26 + cut, 14)
    for (x0, y0) in ((112, 38), (118, 44), (114, 50)):            # exposed girders
        c.line(x0, y0, x0 + 4, y0 - 6, 11); c.px(x0 + 4, y0 - 6, 5)
    tower(c, 52, 64, 30, HOR, 1, 2, 14, rr, wins=[11, 12], lit=.08, ant=10, beacon=6)
    tower(c, 80, 92, 40, HOR, 1, 2, 14, rr, wins=[11, 3], lit=.1, crown=4)
    for x, y in ((62, 19), (86, 35), (122, 40), (36, 48)):
        c.px(x, y, 6); c.px(x, y - 1, 4); c.glow(x, y, 5, [12], .8); c.px(x - 2, y, 12); c.px(x + 2, y, 12)
    # the broken neon sign "HOPE", hanging by one chain, tilted; the E is dead, the P flickers
    SX, SY, SW, SH = 8, 26, 47, 11
    tilt = lambda x: (x - SX) // 5
    c.line(10, 10, 10, SY - 1, 11); c.line(12, 10, 10, SY - 1, 14)               # left chains hold
    c.line(52, 12, 52, 16, 11); c.px(53, 17, 14)                                  # right chain snapped
    for x in range(SX - 1, SX + SW + 1):
        for y in range(-1, SH):
            yy = SY + y + tilt(x)
            if y in (-1, SH - 1) or x in (SX - 1, SX + SW): c.px(x, yy, 14 if y == -1 else 13)
            else: c.px(x, yy, 1)
    letters = [["X...X", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"],
               [".XXX.", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."],
               ["XXXX.", "X...X", "X...X", "XXXX.", "X....", "X....", "X...."],
               ["XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "XXXXX"]]
    for li, L in enumerate(letters):
        for ry, row in enumerate(L):
            for rx, ch in enumerate(row):
                if ch != "X": continue
                for bx in (0, 1):
                    x = SX + 2 + li * 11 + rx * 2 + bx; y = SY + 1 + ry + tilt(x)
                    col = (7, 9, 7, 13)[li]
                    if li == 2 and ry in (1, 2) and bx: col = 13                  # P: a dead tube
                    c.px(x, y, col)
    c.glow(SX + 14, SY + 6, 22, [2, 10], .6, ry=12)
    for x in range(SX, SX + 36):                                                   # light spill under the sign
        if th(x, SY + SH + tilt(x)) < .5: c.lift(x, SY + SH + tilt(x), 12)
    for k, (x, y) in enumerate(((SX + SW, SY + 12), (SX + SW + 1, SY + 16), (SX + SW - 1, SY + 21), (SX + SW + 2, SY + 27),
                                (SX + SW + 1, SY + 33))):                         # sparks from the torn end
        c.px(x, y, 4 if k < 2 else 3); c.lift(x, y + 1, 15)
    c.glow(SX + SW, SY + 12, 4, [15, 3], .7)
    # street
    c.rect(0, HOR - 1, W - 1, HOR - 1, 14)
    for x0, x1, cols in ((0, 14, [12, 2, 3]), (52, 64, [2, 12, 11]), (108, 127, [12, 6, 2])):
        shopfront(c, x0, x1, HOR - 1, cols, 12, 0, [12], .4)
    reflect(c, HOR, {0: 0, 1: 0, 2: 1, 10: 2, 13: 10, 14: 13, 11: 14, 5: 11, 4: 5, 12: 1, 6: 12, 3: 15, 15: 12,
                     7: 7, 8: 8, 9: 9}, [10, 2, 1, 1], stretch=.7, fade=30, wob=wob1)
    # red warning light pools on the wet street
    c.glow(56, 98, 18, [12], .5, ry=4)

    # wrecked police spinner, nose down in the street, burning
    car_pts = [(2, 100), (14, 94), (36, 92), (46, 97), (44, 108), (30, 114), (6, 116), (1, 110)]
    cm = set(mask(car_pts))
    for x, y in cm:
        v = .9 - (y - 92) / 22 + (x - 2) / 120
        col = c.ramp(x, y, [0, 1, 2, 13, 14], v)
        if (x, y - 1) not in cm: col = 11 if th(x, y) < .7 else 14
        elif (x, y + 1) not in cm: col = 0
        c.px(x, y, col)
    c.fill([(18, 95), (32, 94), (38, 98), (24, 101)], 0)               # smashed canopy
    c.line(19, 96, 32, 95, 14); c.line(27, 95, 33, 99, 5); c.px(30, 96, 4)
    c.line(4, 105, 44, 101, lambda x, y: 6 if x % 6 < 3 else 4)       # police stripe
    c.line(4, 106, 44, 102, lambda x, y: 12 if x % 6 < 3 else 13)
    c.disc(10, 114, 4, 0, ry=2); c.disc(36, 111, 4, 0, ry=2)            # dead thrusters
    c.disc(36, 111, 2, 12, ry=1)
    c.rect(24, 91, 29, 92, 0); c.px(25, 91, 6); c.px(26, 91, 6); c.px(27, 91, 8); c.px(28, 91, 8)  # light bar
    c.glow(25, 91, 9, [12], .6); c.px(25, 90, 4)
    for i, h in enumerate((4, 8, 11, 9, 12, 7, 5, 3)):                 # fire from the engine bay
        for j in range(h):
            c.px(4 + i, 101 - j, (4, 3, 15, 15, 6, 12, 12)[min(6, j * 7 // h + (1 if i in (0, 7) else 0))])
    c.glow(8, 97, 16, [12, 6, 15], .6)
    for i in range(14):                                                # its smoke, leaning with the wind
        c.disc(8 - i * .8 + math.sin(i * .9), 86 - i * 3.6, 2 + i * .4,
               lambda x, y: None if th(x, y) < .4 else c.ramp(x, y, [1, 2, 10], .55 - i / 30))
    # its reflection in the wet street
    for x in range(2, 47):
        for k in range(1, 7):
            if th(x, 116 + k) < .5 - k / 14 and c.get(x, 116 - k) in (6, 15, 3, 4, 8): c.px(x, 116 + k, c.get(x, 116 - k))

    # the fallen mecha: helmet sunk in the street, shoulder behind it, an arm reaching out
    pm = {}
    shapes = [
        ([(98, 90), (127, 84), (127, 116), (100, 118), (94, 104)], [1, 2, 10, 13]),          # shoulder/torso
        ([(102, 92), (124, 88), (126, 100), (106, 104)], [2, 13, 14, 11]),                   # pauldron plate
        ([(50, 115), (94, 112), (96, 120), (52, 124)], [1, 2, 13, 14]),                       # forearm
        ([(38, 113), (52, 112), (54, 125), (40, 126)], [2, 13, 14, 11]),                     # hand
    ]
    for pid, (pts, _) in enumerate(shapes):
        for p in mask(pts): pm[p] = pid
    for (x, y), p in pm.items():
        x0 = min(a for a, b in shapes[p][0]); y0 = min(b for a, b in shapes[p][0])
        v = .95 - (y - y0) / 26 - (x - x0) / 90
        col = c.ramp(x, y, shapes[p][1], v)
        up, lf, dn = pm.get((x, y - 1), -1), pm.get((x - 1, y), -1), pm.get((x, y + 1), -1)
        if up < 0 or (up != p and up < p): col = 11 if up < 0 and th(x, y) < .75 else 14    # wet sheen on top edges
        elif lf < 0 or (lf != p and lf < p): col = 12 if th(x, y) < .6 else 0               # red rim from the warning light
        elif dn < 0 or (dn != p and dn < p): col = 0
        c.px(x, y, col)
    # the helmet, hand-drawn, sunk in the street facing us
    HEAD = [
        "...........KKKKKKKKKKKK...........",
        ".........KKWWWWWWWWWWLLKK.........",
        "........KWWLLLLLLLLLLLLmmK........",
        ".......KWLLLLLLGGLLLLLLmmmK.......",
        "......KWLLLLLLLGOLLLLLLmmmMK......",
        ".....KWLLLLLLLLLLLLLLLLmmmMMK.....",
        "....KKLLLLmmmmmmmmmmmmmmmMMMKK....",
        "...KWLKKKKKKKKKKKKKKKKKKKKKKMMK...",
        "...KLKSRrrKKKKKKKKKKKKKKrDDKKMMK..",
        "...KLKRRrKKKKKKKKKKKKKKKDDKKKMMK..",
        "...KLmKKKKKKKKKKKKKKKKKKKKKKMMMK..",
        "...KLmmmmLLmmmmmmmmmmmmmmmMMMMMK..",
        "..KWLmmKmmmKmKmKmKmKmmmmmKMMMMDK..",
        "..KLLmmKmmmKmKmKmKmKmmmmmKMMMDDK..",
        "..KLmmmKmmmKmKmKmKmKmmmmmKMMDDDK..",
        "..KLmmmmKmmmmmmmmmmmmmmmKMMMDDDK..",
        "...KmmmmmKKKKKKKKKKKKKKKMMMDDDK...",
        "....KmmmmmmmmmmmmmmmmmMMMMDDDK....",
        ".....KKMMMMMMMMMMMMMMMMMDDDKK.....",
        ".......KKKKKKKKKKKKKKKKKKKK.......",
    ]
    HC = {"K": 0, "D": 1, "M": 2, "m": 13, "L": 14, "W": 11, "S": 4, "R": 6, "r": 12, "G": 3, "O": 15}
    ox, oy = 62, 90
    for ry, row in enumerate(HEAD):
        for rx, ch in enumerate(row):
            if ch != ".": c.px(ox + rx, oy + ry, HC[ch])
    c.glow(ox + 7, oy + 9, 8, [12, 6], .5)                                   # one dying eye
    # V crest: left horn intact, right one snapped off and lying in the street
    for k in range(13):
        c.px(ox + 14 - k, oy + 3 - k, 3); c.px(ox + 13 - k, oy + 3 - k, 15); c.px(ox + 15 - k, oy + 3 - k, 0)
    c.px(ox + 1, oy - 10, 5)
    c.line(ox + 17, oy + 3, ox + 21, oy - 2, 3); c.line(ox + 18, oy + 3, ox + 22, oy - 2, 15); c.px(ox + 22, oy - 3, 14)
    c.line(54, 113, 62, 111, 3); c.line(54, 114, 62, 112, 15); c.line(54, 115, 62, 113, 0)
    # shoulder detail: panel lines, a cracked plate, reactor's last flicker
    for y in range(96, 112, 4): c.line(104, y + 6, 124, y + 2, 1)
    c.line(110, 92, 114, 100, 0); c.line(114, 100, 112, 104, 0)
    c.rect(116, 104, 119, 106, 0); c.px(117, 105, 8); c.glow(117, 105, 6, [13, 14], .5)
    c.px(120, 92, 6); c.px(120, 93, 12)
    # finger joints and torn cables at the wrist, sparks
    for y in (116, 119, 122): c.line(39, y, 46, y, 0)
    for x in range(56, 92, 6): c.px(x, 116, 0); c.px(x + 1, 117, 14)
    for x0, y0, x1, y1 in ((94, 108, 99, 113), (96, 110, 100, 116)): c.line(x0, y0, x1, y1, 0)
    c.px(99, 113, 4); c.px(100, 112, 3); c.px(98, 115, 3); c.glow(99, 113, 5, [15, 3], .6)
    # its reflection
    for x in range(38, W):
        for k in range(1, 4):
            src = 124 - k * 3
            if c.get(x, src) in (11, 14, 6, 3) and th(x, 124 + k) < .45: c.px(x, min(H - 1, 124 + k), 13)
    # a warning beacon on a barrier, blinking red
    c.rect(48, 92, 62, 93, lambda x, y: 6 if (x // 2) % 2 else 4); c.line(49, 94, 49, 100, 13); c.line(61, 94, 61, 100, 13)
    c.px(55, 90, 6); c.px(55, 91, 6); c.px(55, 89, 4); c.glow(55, 90, 7, [12], .7)
    c.cone(55, 90, 200, 10, 30, [12], .7)
    # heavy rain, slanted, everywhere
    rain(c, 180, [2, 10, 13], 340, H, slant=2, lit=14, lens=(4, 5, 6, 7, 8))
    rain(c, 40, [13, 11, 5], 341, H, slant=2, lit=5, lens=(6, 8, 10))
    splashes(c, 45, 11, 13, 342, HOR)
    return c


# ================================================================== VICTORY: dawn over the city
def victory():
    pal = [(14, 6, 24), (46, 22, 72), (92, 40, 104), (255, 204, 60), (255, 255, 242), (255, 238, 176), (232, 82, 96),
           (255, 80, 190), (0, 226, 255), (170, 255, 60), (154, 62, 114), (255, 176, 140), (242, 114, 110),
           (72, 36, 82), (126, 58, 112), (255, 136, 66)]
    c = Cv(pal, 401)
    HOR = 104
    sky(c, [1, 2, 10, 12, 15, 11, 3, 5, 5], 0, HOR, pw=1.0)
    # sun rising in the gap between towers, with soft rays fanning across the sky
    SX, SY = 64, 90
    for a in range(-170, -9, 10):
        for t in range(18, 120):
            x = SX + math.cos(math.radians(a)) * t; y = SY + math.sin(math.radians(a)) * t
            if not (0 <= x < W and 0 <= y < HOR): continue
            w = abs(((a + 5) % 20) - 10) / 10
            if (a // 10) % 2 == 0 and th(x, y) < .8 - t / 150:
                cur = c.get(x, y)
                c.px(x, y, {1: 2, 2: 10, 10: 12, 12: 15, 15: 11, 11: 3, 3: 5, 5: 4}.get(cur, cur))
    c.glow(SX, SY, 46, [12, 15, 11, 3, 5], .9, ry=34, pw=1.3)
    c.disc(SX, SY, 12, lambda x, y: c.ramp(x, y, [4, 4, 5, 3], (y - SY + 12) / 30 + .1))
    # dawn clouds: puffs in a row, plum on top, lit gold/peach underneath (light comes from below)
    for cx0, cy, n, sc, seed in ((14, 20, 6, 1., 1), (92, 12, 6, .9, 2), (100, 32, 5, .8, 3), (22, 44, 5, .8, 4),
                                 (64, 6, 4, .6, 5)):
        rr = random.Random(400 + seed); puffs = []
        for i in range(n):
            puffs.append((cx0 + (i - n / 2) * 6 * sc + rr.uniform(-2, 2), cy + rr.uniform(-1.5, 1.5) - math.sin(i / (n - 1) * math.pi) * 2 * sc,
                          (3 + rr.uniform(0, 2.5)) * sc))
        pts = {}
        for px_, py_, r in puffs:
            for y in range(int(py_ - r), int(py_ + r * .6) + 1):
                for x in range(int(px_ - r * 1.4), int(px_ + r * 1.4) + 1):
                    if ((x - px_) / (r * 1.4)) ** 2 + ((y - py_) / r) ** 2 <= 1 and y <= cy + 2: pts[(x, y)] = (py_, r)
        for (x, y), (py_, r) in pts.items():
            v = (y - (py_ - r)) / (r * 1.6)                    # 0 top .. 1 underside
            col = c.ramp(x, y, [2, 10, 10, 12, 11, 5], v * 1.1)
            if (x, y + 1) not in pts: col = 5 if th(x, y) < .6 else 3
            if (x, y - 1) not in pts and th(x, y) < .5: col = 14
            c.px(x, y, col)
    # birds
    for x, y in ((22, 34), (28, 31), (33, 36), (90, 20), (96, 23), (101, 19), (40, 12), (78, 40), (16, 44)):
        c.px(x - 1, y - 1, 13); c.px(x, y, 0); c.px(x + 1, y - 1, 13); c.px(x - 2, y - 1, 0) if x % 2 else None
    # far towers in the gold haze
    hzf = lambda x, y, col: c.mix(x, y, col, 12, max(0, (y - 70) / 40))
    skyline(c, 410, -2, W, lambda x: (94, 99) if 40 < x < 84 else (66, 84), HOR, 10, 2, 11, [3, 5, 11], .15, hz=hzf,
            wr=(4, 8))
    # mid towers: silhouettes rim-lit toward the sun
    rr = random.Random(420)
    for x0, x1, top in ((0, 12, 30), (14, 24, 46), (26, 36, 62), (92, 102, 58), (104, 114, 40), (116, 127, 24)):
        lside = x0 > 64
        tower(c, x0, x1, top, HOR, 13, 1, 3, rr, wins=[3, 15, 9, 7], lit=.12, dx=3, dy=4, ww=2, lside=lside,
              crown=rr.choice((0, 4)), ant=rr.choice((0, 6)), beacon=6)
        rx = x0 if lside else x1                                     # sun-side rim: full height
        for y in range(top, HOR): c.px(rx, y, 3 if th(rx, y) < .75 - (y - top) / 160 else 15)
        for y in range(top, HOR): c.px(rx + (1 if lside else -1), y, 14 if th(rx, y + 1) < .5 else None)
        for x in range(x0, x1 + 1):                                  # top catches the dawn
            c.px(x, top, 5 if (x - rx) * (1 if lside else -1) < 3 else 11)
    vsign(c, 3, 40, 18, 8, 4, 0, rmp=[14], k=.4)
    vsign(c, 120, 34, 16, 7, 4, 0, rmp=[14], k=.4)
    hsign(c, 104, 48, 9, 3, 9, 4, 0)
    # flying cars heading into the sunrise
    car(c, 30, 18, 1, 13, 14, 5, 6, 11, k=.4); car(c, 100, 8, -1, 13, 14, 5, 6, 11, k=.4)
    stream(c, [(-2, 82), (40, 86), (130, 84)], [4, 5, 3], 3, 421, y1=HOR)
    # street + river: the sun's path in the water
    for x0, x1, cols in ((0, 12, [3, 15, 5]), (14, 24, [9, 3, 11]), (92, 102, [5, 3, 7]), (116, 127, [15, 3, 8])):
        shopfront(c, x0, x1, HOR, cols, 6, 0, [12, 15], .4)
    c.rect(0, HOR - 1, W - 1, HOR - 1, 3)
    reflect(c, HOR, {0: 0, 1: 0, 13: 1, 2: 13, 10: 2, 14: 10, 12: 10, 15: 12, 11: 15, 3: 15, 5: 3, 4: 5, 6: 12,
                     7: 7, 8: 8, 9: 9}, [10, 2, 13, 1], stretch=.8, fade=30, wob=wob1, ripple=3)
    for y in range(HOR + 1, H):                                     # glitter path under the sun
        hw = 3 + (y - HOR) * .5
        for x in range(int(SX - hw), int(SX + hw) + 1):
            if th(x, y) < .55 - abs(x - SX) / (hw * 2) and (x + y) % 3: c.px(x, y, 4 if abs(x - SX) < hw * .3 else 3)
    # quay rail silhouette with two figures watching the dawn
    c.rect(0, 120, W - 1, 120, 0); c.rect(0, 121, W - 1, H - 1, 0)
    for x in range(0, W, 8): c.rect(x, 116, x, 120, 0)
    c.line(0, 116, W - 1, 116, 0); c.line(0, 115, W - 1, 115, lambda x, y: 15 if th(x, y) < .5 else 13)
    for fx in (44, 48):
        c.rect(fx, 108, fx + 2, 120, 0); c.disc(fx + 1, 106, 1.5, 0); c.px(fx + (2 if fx == 44 else 0), 105, 3)
    c.px(46, 110, 0)
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    out = []
    for name, f in (("menu", menu), ("clear", clear), ("gameover", gameover), ("victory", victory)):
        cv = f(); im = cv.image(); im.save(os.path.join(OUT, name + ".png")); out.append((name, im, cv))
        print("%-9s mean luminance %.1f" % (name, cv.mean_lum()))
    # preview: row 1 the pictures, row 2 with the game's panel boxes (fill 0, edge 7) at 3x
    S = 3
    pv = Image.new("RGB", ((W * S + 8) * 4, (H * S + 8) * 2), (24, 24, 24))
    for i, (name, im, cv) in enumerate(out):
        rgb = im.convert("RGB")
        pv.paste(rgb.resize((W * S, H * S), Image.Resampling.NEAREST), (i * (W * S + 8), 0))
        p = rgb.copy(); d = ImageDraw.Draw(p); x0, y0, x1, y1 = PANELS[name]
        d.rectangle((x0, y0, x1, y1), fill=cv.pal[0], outline=cv.pal[7])
        d.rectangle((x0 + 4, y0 + 6, x1 - 4, y0 + 13), fill=cv.pal[13])
        for k, ci in enumerate((4, 3, 4)):
            d.rectangle((x0 + 8, y0 + 8 + k * 10, x0 + 8 + 40 - k * 8, y0 + 12 + k * 10), fill=cv.pal[ci])
        pv.paste(p.resize((W * S, H * S), Image.Resampling.NEAREST), (i * (W * S + 8), H * S + 8))
    pv.save(os.path.join(HERE, "preview_screens3.png"))


if __name__ == "__main__":
    main()
