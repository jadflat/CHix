"""CHix scenes 04..06, v2 hero art: rainy cyberpunk night cities. Deterministic. Run: python paint_b.py

04  a colossal mecha with a glowing chest reactor striding through burning towers, blood-pale moon behind it
05  a ringed planet eclipsing the sun over a suspension bridge with lit traffic streams, wet bay below
06  a red pagoda tower, a dragon airship, crossing searchlights and lightning in a jade storm

Palette contract (docs/UPGRADE-PLAN.md): 0 near black, 3 gold, 4 white, 5 light, 6 red, 7 cyan, 8 green,
11 near-white, 14 frame, 15 glow; 1 2 9 10 12 13 are free per scene. v1 of this script is in v1/.
Writes scene04..06.png, preview_b2.png and crop_b2.png (4x sheet)."""
import math, random, os
from PIL import Image, ImageDraw

W, H = 120, 112
B4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
HERE = os.path.dirname(os.path.abspath(__file__))


def th(x, y): return (B4[int(y) & 3][int(x) & 3] + .5) / 16


def mask(pts):
    im = Image.new("L", (W, H), 0); ImageDraw.Draw(im).polygon([(float(a), float(b)) for a, b in pts], fill=255)
    return [(x, y) for y in range(H) for x in range(W) if im.getpixel((x, y))]


class Cv:
    def __init__(s, pal, seed):
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
        """Bloom by ordered dither: rmp faint..core, only ever brightens."""
        ry = ry or r
        for y in range(int(cy - ry) - 1, min(y1, int(cy + ry) + 2)):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                d = math.hypot((x - cx) / r, (y - cy) / ry)
                if d >= 1: continue
                u = (1 - d) ** pw * k * len(rmp); i = int(u)
                if i >= len(rmp): c = rmp[-1]
                else: c = rmp[i] if th(x, y) < u - i else (rmp[i - 1] if i else None)
                if 0 <= x < W and 0 <= y < H: s.lift(x, y, c)

    def cone(s, ax, ay, ang, half, ln, rmp, k=1., y1=H):
        """Light cone from (ax, ay) along angle ang (deg, 0 = right, -90 = up)."""
        a0 = math.radians(ang)
        for y in range(H if y1 > H else y1):
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


# ------------------------------------------------------------------ shared scenery pieces
def sky(c, stops, y0, y1, pw=1.):
    n = len(stops) - 1
    for y in range(y0, y1):
        t = ((y - y0) / max(1, y1 - y0 - 1)) ** pw * n; i = min(int(t), n - 1)
        for x in range(W): c.px(x, y, c.mix(x, y, stops[i], stops[i + 1], t - i))


def stars(c, pts, cols):
    for i, (x, y) in enumerate(pts):
        col = cols[i % len(cols)]
        if c.get(x, y) in (0, 1): c.px(x, y, col)


def cloud_bank(c, y, amp, seed, top, under, rim=None, y_lim=None, k=.35):
    """A rolling storm-cloud bank: dark body, dithered underside, optional lit rim on top."""
    rr = random.Random(seed)
    ph = [rr.uniform(0, 6.3) for _ in range(4)]
    for x in range(W):
        h = y + amp * (math.sin(x * .09 + ph[0]) * .6 + math.sin(x * .23 + ph[1]) * .3 + math.sin(x * .51 + ph[2]) * .15)
        for yy in range(0, int(h) + 1):
            if y_lim and yy >= y_lim: break
            f = (h - yy) / 6.
            c.px(x, yy, c.mix(x, yy, under, top, min(1, f + k)))
        if rim is not None: c.px(x, int(h) - int(amp * .2 * (1 + math.sin(x * .7 + ph[3]))), None)


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
    """A tower block: body + shaded side + rim on the lit edge, windows, setback crown, antenna."""
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


def vsign(c, x, y, h, col, hot, frame, glow_r=7, k=.5, rmp=None):
    c.rect(x - 1, y - 1, x + 3, y + h, frame)
    rr = random.Random(x * 31 + y)
    for yy in range(y, y + h):
        if (yy - y) % 4 == 3: continue
        for xx in range(x, x + 3):
            if rr.random() < .62: c.px(xx, yy, col)
        if rr.random() < .3: c.px(x + 1, yy, hot)
    c.glow(x + 1, y + h / 2, glow_r, rmp or [col], k, ry=h / 2 + glow_r * .6)


def hsign(c, x, y, w, h, col, hot, frame, rmp=None, k=.45):
    c.rect(x - 1, y - 1, x + w, y + h, frame)
    rr = random.Random(x * 17 + y * 3)
    for xx in range(x, x + w):
        if (xx - x) % 5 == 4: continue
        for yy in range(y, y + h):
            if rr.random() < .6: c.px(xx, yy, col)
    c.px(x + rr.randrange(w), y + rr.randrange(h), hot)
    c.glow(x + w / 2, y + h / 2, w / 2 + 6, rmp or [col], k, ry=h / 2 + 5)


def cable(c, x0, y0, x1, y1, sag, col, lights=None, every=4):
    n = int(abs(x1 - x0)) + 1
    for i in range(n + 1):
        t = i / n; x = x0 + (x1 - x0) * t; y = y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)
        c.px(round(x), round(y), col)
        if lights is not None and i % every == every // 2: c.px(round(x), round(y) + 1, lights)


def car(c, x, y, d, body, roof, head, tail, trail, k=.6, glow_rmp=None):
    """Flying car, 5x2, d = +1 heading right. Trail of dithered light behind."""
    for i in range(2, 12):
        tx = x - d * i + (4 if d < 0 else 0)
        if th(tx, y + 1) < (1 - i / 12) * .8: c.px(tx, y + 1, trail)
    c.rect(x, y, x + 4, y + 1, body); c.px(x + 1, y - 1, roof); c.px(x + 2, y - 1, roof); c.px(x + 3, y - 1, roof)
    c.px(x + (4 if d > 0 else 0), y, head); c.px(x + (0 if d > 0 else 4), y, tail); c.px(x + 2, y + 2, trail)
    c.glow(x + (5 if d > 0 else -1), y, 5, glow_rmp or [head], k)


def stream(c, pts, cols, gap, seed, y1=H):
    """A traffic stream: lights strung along a polyline, short dithered streaks."""
    rr = random.Random(seed); s = 0
    seg = []
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


def rain(c, n, cols, seed, y1, slant=1, lit=None):
    rr = random.Random(seed)
    for _ in range(n):
        x, y = rr.randrange(W + 8), rr.randrange(-4, y1)
        ln = rr.choice((3, 4, 4, 5, 6)); col = rr.choice(cols)
        for i in range(ln):
            X, Y = x - (i * slant) // 2, y + i
            if 0 <= Y < y1:
                cur = c.get(X, Y)
                cc = lit if (lit is not None and c.L[cur] > c.L[col]) else col
                if i == ln - 1 and ln > 3: cc = cols[0]
                c.lift(X, Y, cc) if c.L[cc] > c.L[cur] or cur in (0, 1) else None


def splashes(c, n, col, dim, seed, y0):
    rr = random.Random(seed)
    for _ in range(n):
        x, y = rr.randrange(2, W - 2), rr.randrange(y0 + 3, H - 1)
        c.px(x - 1, y, dim); c.px(x + 1, y, dim); c.px(x, y - 1, col)


def reflect(c, hor, dk, base, stretch=.5, fade=30, wob=None, ripple=4):
    """Wet street / water: mirror what is above the horizon, stretched into streaks; lights keep their colour,
    the rest darkens through dk; every ripple-th row breaks into the surface colour (base: near..far ramp)."""
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
    """Street-level shop row: awning stripe, lit glass with figures, glow onto the pavement."""
    for x in range(x0, x1 + 1):
        c.px(x, y - 6, frame); c.px(x, y - 5, awn if x % 2 else frame)
        for yy in range(y - 4, y):
            col = cols[(x // 3) % len(cols)]
            if x % 7 == 0: col = frame
            elif yy == y - 1 and x % 3 == 1: col = frame
            c.px(x, yy, col)
    c.glow((x0 + x1) / 2, y - 2, (x1 - x0) / 2 + 5, rmp, k, ry=5)


# ------------------------------------------------------------------ scene 04: the colossus
def scene04():
    pal = [(3, 2, 10), (16, 10, 34), (36, 18, 62), (255, 200, 60), (255, 255, 255), (255, 170, 220), (255, 60, 90),
           (0, 230, 255), (60, 255, 140), (128, 34, 84), (66, 30, 96), (240, 232, 255), (255, 118, 46),
           (150, 150, 222), (110, 60, 150), (255, 80, 200)]
    c = Cv(pal, 4)
    HOR = 88
    sky(c, [0, 0, 1, 2, 10, 9], 0, HOR, pw=1.05)
    stars(c, [(5, 3), (17, 9), (29, 2), (41, 7), (100, 4), (111, 11), (88, 2), (9, 18), (116, 21), (52, 3)], [13, 11, 14])
    # moon behind the colossus' head: the silhouette reads against it
    MX, MY, MR = 68, 36, 38
    c.glow(MX, MY, MR + 10, [2, 10, 14], .9, pw=1.1)
    c.disc(MX, MY, MR, lambda x, y: c.ramp(x, y, [4, 11, 11, 5, 5, 12, 9], (y - MY + MR) / (MR * 1.75)
                                           + max(0, math.hypot(x - MX, y - MY) - MR + 4) * .04))
    for dx, dy, r, ry in ((-24, -14, 6, 3), (-28, 2, 3, 5), (22, -22, 6, 3), (28, -8, 3, 4), (-10, -30, 5, 2)):
        c.disc(MX + dx, MY + dy, r, lambda x, y: c.mix(x, y, c.get(x, y), 13, .5), ry=ry)
    # fire glow on the horizon and the smoke it lights
    c.glow(64, HOR + 4, 78, [10, 9, 6, 12], 1.0, ry=26, pw=1.3)     # the whole horizon burns
    for gx, gy, gr in ((22, 70, 30), (104, 74, 24)):
        c.glow(gx, gy, gr, [9, 6, 12], .7, ry=gr * .8)

    def plume(x, y, n, drift, r0, seed):
        rr = random.Random(seed)
        for i in range(n):
            cx = x + drift * i + rr.uniform(-1.5, 1.5); cy = y - i * 3.2; r = r0 + i * .45
            for yy in range(int(cy - r), int(cy + r) + 1):
                for xx in range(int(cx - r), int(cx + r) + 1):
                    dd = math.hypot(xx - cx, yy - cy)
                    if dd > r: continue
                    lit = (yy - cy) / r * .5 + .5 - i / n * .6       # underside lit by fire
                    col = c.ramp(xx, yy, [1, 2, 10, 9, 6], max(0, lit) * .95)
                    if dd > r - 1 and th(xx, yy) < .5: continue        # dithered, soft edge
                    c.px(xx, yy, col)
    plume(20, 62, 13, 1.2, 3, 41); plume(104, 66, 11, -1.4, 2.5, 42); plume(36, 70, 7, .6, 2, 43)

    # far burning city, deep in haze
    rr = random.Random(400)
    hzf = lambda x, y, col: c.mix(x, y, col, 9, max(0, (y - 70) / 40))
    x = -2
    while x < W:
        w = rr.randint(4, 8); top = rr.randint(68, 78) if 36 < x < 98 else rr.randint(48, 66)
        tower(c, x, x + w, top, HOR, 10, 2, 9, rr, wins=[12, 6, 3], lit=.2, hz=hzf, ant=rr.choice((0, 0, 4)), dy=3)
        x += w + rr.randint(0, 2)

    # searchlights from the street, converging on the colossus
    c.cone(16, HOR, -62, 4.5, 90, [10, 14, 13], .55)
    c.cone(108, HOR, -118, 4, 90, [10, 14, 13], .5)

    # explosion bursting from a mid tower on the left
    EX, EY = 28, 47
    tower(c, 20, 32, 52, HOR, 1, 2, 14, random.Random(9), wins=[12, 3], lit=.5)
    c.glow(EX, EY, 22, [9, 6, 12, 3, 4, 4], 1.0, pw=1.9)
    rr = random.Random(77)
    for _ in range(22):
        a = rr.uniform(0, 6.283); l = rr.uniform(6, 15)
        x1, y1 = EX + l * math.cos(a), EY + l * math.sin(a) * .8
        c.line(EX + 4 * math.cos(a), EY + 4 * math.sin(a), x1, y1, lambda x, y: 3 if th(x, y) < .5 else None)
        c.px(x1, y1, rr.choice((12, 3, 4)))
    for dx, dy in ((-9, 4), (8, -2), (-4, -9), (11, 6), (2, 10)):
        c.disc(EX + dx, EY + dy, 2.2, lambda x, y: c.mix(x, y, 2, 9, .5)); c.px(EX + dx, EY + dy - 2, 12)

    # ---- the colossus
    pm = [[-1] * W for _ in range(H)]
    parts = [  # (polygon, tone) tone: 0 dark, 1 mid, 2 plate; drawn in order
        ([(56, 60), (66, 60), (60, 78), (50, 76)], 0),                            # near thigh (striding forward)
        ([(70, 60), (80, 60), (86, 75), (77, 77)], 0),                            # far thigh
        ([(49, 78), (59, 78), (58, 92), (46, 92)], 1),                            # near shin
        ([(78, 77), (89, 77), (94, 92), (81, 92)], 1),                            # far shin
        ([(46, 72), (55, 70), (58, 77), (52, 82), (46, 79)], 2),                  # near knee guard
        ([(81, 71), (89, 72), (91, 79), (85, 82), (80, 78)], 2),                  # far knee guard
        ([(60, 50), (76, 50), (78, 58), (74, 64), (62, 64), (58, 58)], 0),        # waist
        ([(55, 56), (62, 56), (63, 69), (54, 66)], 2),                            # skirt plates
        ([(74, 56), (82, 56), (83, 66), (73, 69)], 2),
        ([(52, 27), (84, 27), (88, 36), (80, 52), (56, 52), (48, 36)], 1),        # torso
        ([(57, 29), (79, 29), (82, 36), (76, 47), (60, 47), (54, 36)], 2),        # chest plate
        ([(64, 22), (72, 22), (73, 28), (63, 28)], 0),                            # neck
        ([(62, 11), (74, 11), (76, 17), (73, 24), (63, 24), (60, 17)], 1),        # head
        ([(64, 21), (72, 21), (71, 25), (65, 25)], 2),                            # mouth guard
        ([(65, 12), (59, 3), (61, 3), (68, 11)], 2), ([(71, 12), (77, 3), (79, 3), (72, 12)], 2),  # V crest
        ([(86, 34), (94, 34), (96, 50), (93, 62), (87, 62), (85, 48)], 0),        # far arm (swung back)
        ([(86, 60), (94, 60), (96, 68), (89, 70)], 2),                            # far fist
        ([(80, 21), (98, 23), (103, 32), (99, 43), (84, 41)], 2),                 # far pauldron
        ([(42, 36), (52, 36), (54, 50), (51, 58), (43, 56), (41, 46)], 0),        # near upper arm
        ([(40, 54), (53, 54), (54, 68), (42, 68)], 1),                            # near forearm
        ([(19, 62), (48, 60), (52, 67), (34, 71), (19, 69)], 1),                    # cannon
        ([(30, 58), (44, 57), (45, 61), (31, 61)], 2),                            # cannon scope
        ([(35, 20), (56, 21), (59, 38), (45, 42), (33, 32)], 2),                  # near pauldron
        ([(38, 17), (46, 11), (49, 12), (45, 21)], 2),                            # pauldron fin
    ]
    for pid, (pts, tone) in enumerate(parts):
        for x, y in mask(pts): pm[y][x] = pid
    TON = {0: [0, 1, 1, 2], 1: [1, 1, 2, 10], 2: [1, 2, 10, 14, 13]}
    ext = {}
    for y in range(H):
        for x in range(W):
            p = pm[y][x]
            if p >= 0:
                e = ext.setdefault(p, [y, y]); e[0] = min(e[0], y); e[1] = max(e[1], y)
    for y in range(H):
        for x in range(W):
            p = pm[y][x]
            if p < 0: continue
            tone = parts[p][1]; t0, t1 = ext[p]
            v = .8 - (y - t0) / max(4, t1 - t0) * .75 - (y - 30) / 160      # armour plates lit from above
            col = c.ramp(x, y, TON[tone], v)
            fx = max(0., 1 - math.hypot(x - 28, (y - 50) * 1.3) / 34)               # the blast lights its flank
            if fx > 0 and tone: col = c.mix(x, y, col, 9 if fx < .45 else 12, fx * 1.1)
            up = pm[y - 1][x] if y else -1; lf = pm[y][x - 1] if x else -1
            dn = pm[y + 1][x] if y < H - 1 else -1; rt = pm[y][x + 1] if x < W - 1 else -1
            if up < 0 or lf < 0 or rt < 0:                                   # silhouette: the moon wraps it
                bg = c.get(x, y - 1) if up < 0 else (c.get(x - 1, y) if lf < 0 else c.get(x + 1, y))
                col = 13 if c.L[bg] > 120 else 14
                if lf < 0 and x < 50 and y > 40: col = 12                    # the explosion lights the left
            elif dn < 0: col = 6 if th(x, y) < .5 else 9
            elif (dn != p and dn > p) or (rt != p and rt > p): col = 0
            elif up != p: col = 14 if tone == 2 else 10                      # bevel catches the light
            c.a[y][x] = col
    # panel lines, vents, lights
    for y in (33, 39): c.line(53 + (y - 33) // 3, y, 56, y, 0)
    for x in range(87, 96, 2): c.line(x, 29, x + 1, 36, c.mix(x, 30, 0, 12, .3))
    for y in range(42, 50, 2): c.line(60, y, 64, y, 0); c.line(72, y, 76, y, 0)
    c.rect(65, 46, 71, 48, 0)
    for x in (66, 68, 70): c.px(x, 47, 12)
    for y in range(57, 68, 3): c.line(44, y, 52, y, 0)
    c.line(21, 65, 48, 64, 2)
    for x in range(22, 34, 3): c.px(x, 66, 0)
    # visor and eyes
    c.line(64, 18, 72, 18, 9); c.px(65, 18, 6); c.px(66, 18, 4); c.px(70, 18, 6); c.px(71, 18, 4)
    c.glow(68, 18, 7, [9, 6], .7)
    # chest reactor
    RX, RY = 68, 37
    c.glow(RX, RY, 15, [10, 14, 7], .9, pw=2.0)
    c.disc(RX, RY, 4.5, 0); c.disc(RX, RY, 3.6, 7); c.disc(RX, RY, 2.2, 11); c.px(RX, RY, 4); c.px(RX - 1, RY, 4)
    for a in range(0, 360, 45):
        c.px(RX + round(5.5 * math.cos(math.radians(a))), RY + round(5.5 * math.sin(math.radians(a))), 7)
    for x in range(RX - 12, RX + 13):
        c.lift(x, RY, 7 if abs(x - RX) < 9 or th(x, RY) < .4 else None)
    # shoulder running lights and markings
    for x, y in ((46, 28), (90, 30), (98, 36)): c.px(x, y, 6); c.glow(x, y, 3, [6], .5)
    c.rect(48, 31, 52, 32, 15); c.px(53, 32, 15)
    # muzzle flash
    MZ = (17, 65)
    c.glow(MZ[0], MZ[1], 12, [9, 6, 12, 3, 4], 1., ry=8)
    for a, l in ((180, 9), (160, 5), (200, 5), (135, 4), (225, 4)):
        c.line(MZ[0], MZ[1], MZ[0] + l * math.cos(math.radians(a)), MZ[1] + l * math.sin(math.radians(a)), 4)
    c.disc(MZ[0], MZ[1], 1.5, 4)

    # mid layer: towers on fire, half in smoke
    rr = random.Random(410)
    hzm = lambda x, y, col: c.mix(x, y, col, 10, max(0, (y - 74) / 22))
    for x0, x1, top in ((0, 9, 40), (30, 38, 72), (104, 112, 44)):
        tower(c, x0, x1, top, HOR, 1, 2, 14, rr, wins=[12, 3, 9, 5], lit=.35, hz=hzm, crown=rr.choice((0, 3)),
              ant=rr.choice((0, 5)))
    for fx, fy in ((4, 40), (108, 44)):
        for i in range(7):
            h = (3, 5, 7, 6, 4, 5, 2)[i]
            for j in range(h):
                c.px(fx - 3 + i, fy - 1 - j, (4, 3, 12, 12, 6, 6, 9)[min(6, j * 7 // h + (1 if i in (0, 6) else 0))])
        c.glow(fx, fy - 3, 11, [9, 6, 12], .8)

    # near street walls framing the shot: neon, pipes, cables, AC boxes
    rr = random.Random(420)
    tower(c, 0, 13, 66, HOR, 0, 1, 14, rr, wins=[3, 5, 12], lit=.3, dx=3, dy=4, ww=2)
    tower(c, 101, 119, 58, HOR, 0, 1, 14, rr, wins=[5, 3, 7], lit=.3, dx=3, dy=4, ww=2, lside=False)
    shopfront(c, 0, 13, HOR - 1, [12, 3, 5], 15, 0, [9, 15], .5)
    shopfront(c, 101, 119, HOR - 1, [7, 13, 11], 6, 0, [10, 14, 7], .5)
    vsign(c, 10, 68, 13, 15, 5, 0, rmp=[9, 15], k=.55)
    vsign(c, 104, 61, 20, 7, 11, 0, rmp=[14, 7], k=.5)
    hsign(c, 109, 84 - 12, 8, 4, 8, 4, 0, rmp=[8], k=.3)
    for y in (72, 78): c.line(14, y, 18, y, 2)
    c.rect(3, 72, 7, 75, 2); c.rect(3, 72, 7, 72, 14); c.px(5, 74, 0)
    cable(c, 14, 70, 30, 74, 2, 0, lights=3, every=4)
    # flying traffic
    stream(c, [(-2, 46), (40, 49), (120, 44)], [3, 5, 6], 2, 7, y1=HOR)
    # police spinners hold the colossus in their spotlights
    c.cone(16, 20, 22, 4, 50, [10, 14, 13], .8); car(c, 12, 19, 1, 2, 14, 4, 6, 9, k=.5); c.px(14, 18, 7)
    c.cone(106, 14, 158, 4, 44, [10, 14, 13], .8); car(c, 104, 13, -1, 2, 14, 4, 6, 9, k=.5); c.px(106, 12, 6)
    car(c, 98, 52, -1, 2, 14, 5, 6, 9, k=.5)
    car(c, 44, 78, 1, 1, 14, 4, 6, 15, k=.6)

    # street level
    c.rect(0, HOR - 1, W - 1, HOR - 1, 14)
    reflect(c, HOR, {0: 0, 1: 0, 2: 1, 10: 2, 9: 10, 14: 10, 13: 14, 11: 13, 6: 9, 12: 6, 3: 12, 4: 11, 15: 9, 5: 15,
                     7: 7, 8: 8}, [10, 2, 1, 0], wob=lambda x, y: (1 if (y // 2 + x // 5) % 3 == 0 else 0))
    for i in range(0, W, 12):                          # lane dashes in perspective
        c.line(i + 4, 96, i + 7, 96, 14); c.line(i * 1.3 - 10, 106, i * 1.3 - 5, 106, 14)
    rain(c, 55, [10, 14, 13], 404, HOR, lit=5)
    splashes(c, 26, 13, 14, 405, HOR)
    return c


# ------------------------------------------------------------------ scene 05: eclipse over the bridge
def scene05():
    pal = [(2, 5, 14), (6, 14, 34), (14, 30, 62), (255, 196, 70), (255, 255, 255), (255, 214, 160), (255, 84, 70),
           (0, 235, 255), (70, 255, 150), (100, 54, 132), (30, 56, 104), (244, 244, 255), (96, 148, 214),
           (184, 218, 248), (70, 100, 150), (255, 150, 60)]
    c = Cv(pal, 5)
    HOR = 80
    sky(c, [0, 0, 1, 2, 10, 9, 9], 0, HOR, pw=.95)
    stars(c, [(4, 4), (14, 12), (26, 3), (9, 25), (36, 9), (95, 6), (108, 15), (116, 3), (84, 2), (112, 28),
              (3, 37), (49, 2), (74, 4)], [13, 11, 12])
    PX, PY, PR = 60, 33, 22
    # corona: soft, wide, brightest at the upper-right limb where the sun is about to break out
    c.glow(PX, PY, PR + 22, [2, 10, 14, 12], .8, pw=1.5)
    c.glow(PX + 14, PY - 15, 26, [10, 14, 12, 13, 11], .9, pw=1.5)
    # ring geometry (tilted ellipse) - back half first
    TIL = math.radians(-14)

    def ring_pts(front):
        out = []
        for t in range(1400):
            a = t / 1400 * 2 * math.pi
            for k, (rx, col) in enumerate(((44, 13), (42, 12), (40, 14), (37, 12), (35, 13))):
                ex, ey = rx * math.cos(a), rx * .22 * math.sin(a)
                x = PX + ex * math.cos(TIL) - ey * math.sin(TIL); y = PY + ex * math.sin(TIL) + ey * math.cos(TIL)
                if (math.sin(a) > 0) == front: out.append((round(x), round(y), col, k))
        return out
    for x, y, col, k in ring_pts(False):
        if math.hypot(x - PX, y - PY) > PR + .3: c.px(x, y, col if k != 2 or th(x, y) < .6 else 10)
    # the planet's dark face: banded, a thin lit crescent at the upper right
    for y in range(PY - PR, PY + PR + 1):
        for x in range(PX - PR, PX + PR + 1):
            d = math.hypot(x - PX, y - PY)
            if d > PR: continue
            band = .5 + .5 * math.sin((y - PY + (x - PX) * .25) * .62 + math.sin(x * .3) * .8)
            col = c.mix(x, y, 1, 2, band * .55)
            if 0 < (y - PY) * .9 + (x - PX) * .2 < 5 and th(x, y) < .5: col = 0          # ring shadow on the face
            lim = math.hypot(x - (PX - 4), y - (PY + 5))                                # crescent: offset disc
            if lim > PR - .2:
                e = (lim - PR + .2) / 3.2
                col = c.ramp(x, y, [10, 12, 13, 11, 4], e)
            elif d > PR - 1.2: col = c.mix(x, y, col, 10, .5)
            c.px(x, y, col)
    for x, y, col, k in ring_pts(True):
        if math.hypot(x - PX, y - PY) <= PR: col = {13: 12, 12: 14, 14: 10}[col]   # ring in the planet's shade
        c.px(x, y, col if k != 2 or th(x, y) < .6 else 2)
    # diamond-ring flare where the sun breaks the limb
    FX, FY = PX + 15, PY - 16
    c.glow(FX, FY, 9, [13, 11, 4], 1.)
    for a, l in ((0, 14), (90, 10), (180, 14), (270, 10), (45, 5), (135, 5), (225, 5), (315, 5)):
        c.line(FX, FY, FX + l * math.cos(math.radians(a)), FY + l * math.sin(math.radians(a)) * .85,
               lambda x, y: 11 if math.hypot(x - FX, y - FY) < l * .5 else (13 if th(x, y) < .7 else None))
    c.disc(FX, FY, 1.5, 4)

    # flying traffic lanes high over the bay
    stream(c, [(-2, 54), (30, 50), (70, 52), (122, 47)], [5, 3, 11], 3, 51)
    stream(c, [(122, 58), (80, 57), (40, 60), (-2, 58)], [6, 15, 6], 3, 52)

    # far skyline in the haze beyond the bridge
    rr = random.Random(500)
    hzf = lambda x, y, col: c.mix(x, y, col, 2, max(0, (y - 66) / 30))
    x = -1
    while x < W:
        w = rr.randint(6, 11); top = rr.randint(54, 66)
        if 34 < x < 82: top = rr.randint(52, 62)                        # downtown cluster under the planet
        tower(c, x, x + w, top, HOR, 2, 1, 10, rr, wins=[10, 14, 12, 14, 9], lit=.22, hz=hzf, ant=rr.choice((0, 3, 6)),
              crown=rr.choice((0, 0, 2, 4)), dy=2)
        x += w + 1
    c.glow(58, 64, 34, [10, 14], .5, ry=10)

    # suspension bridge: two great towers framing the eclipse
    DY, TT = 68, 9
    T1, T2 = 22, 98
    for tx in (T1, T2):
        for y in range(TT, HOR):                                       # twin legs, lit on the planet side
            for x in range(tx - 3, tx + 4):
                if x in (tx - 1, tx, tx + 1) and y > TT + 3: continue
                col = 1
                if x in (tx - 3, tx + 2): col = 14 if (tx < 60) == (x > tx) else 2
                if x in (tx - 2, tx + 3): col = 2 if (tx < 60) == (x > tx) else 1
                c.px(x, y, col)
        for yy, hh in ((TT + 3, 2), (26, 1), (44, 1), (DY + 5, 1)):
            c.rect(tx - 3, yy, tx + 3, yy + hh, 1); c.rect(tx - 3, yy, tx + 3, yy, 14)
            c.px(tx - 1, yy + hh + 1, 1); c.px(tx + 1, yy + hh + 1, 1)
        c.rect(tx - 4, TT, tx + 4, TT + 1, 2); c.rect(tx - 4, TT, tx + 4, TT, 14)
        c.px(tx - 3, TT - 1, 6); c.px(tx + 3, TT - 1, 6); c.px(tx, TT - 3, 6)
        c.line(tx, TT - 2, tx, TT - 1, 14); c.glow(tx, TT - 2, 5, [9, 6], .5)
        for y in range(TT + 7, DY, 6): c.px(tx - 3 if tx < 60 else tx + 3, y, 3)
    cab = []
    for x in range(T1 + 3, T2 - 2):
        t = (x - T1) / (T2 - T1); cab.append((x, round(TT + 2 + (DY - TT - 6) * (1 - (2 * t - 1) ** 2))))
    for x in range(0, T1 - 3):
        cab.append((x, round(TT + 2 + (DY - TT - 2) * (1 - x / (T1 - 3)) ** 1.15)))
    for x in range(T2 + 4, W):
        cab.append((x, round(TT + 2 + (DY - TT - 2) * ((x - T2 - 4) / (W - T2 - 4)) ** 1.15)))
    for x, y in cab:
        if x % 4 == 0 and y + 2 < DY:                                   # suspenders, faint
            for yy in range(y + 2, DY): c.px(x, yy, c.mix(x, yy, 1, 14, .3))
    for x, y in cab:
        c.px(x, y - 1, c.mix(x, y, 14, 12, .5)); c.px(x, y, 14); c.px(x, y + 1, 1)
        if x % 4 == 0: c.px(x, y, 3)
        if x % 8 == 0: c.px(x, y - 1, 5)
    # deck with two traffic streams
    c.rect(0, DY, W - 1, DY + 4, 1)
    c.rect(0, DY, W - 1, DY, 14)
    for x in range(0, W, 2): c.px(x, DY + 4, 14); c.px(x + 1, DY + 5, 2)
    for x in range(0, W, 5): c.px(x, DY + 3, 0)
    stream(c, [(-1, DY + 1), (121, DY + 1)], [5, 11, 3, 5], 1, 53)
    stream(c, [(121, DY + 2), (-1, DY + 2)], [6, 6, 15], 1, 54)
    for x in range(0, W, 2):
        if c.get(x, DY + 1) in (5, 11, 3): c.lift(x, DY - 1, 2)
    c.glow(60, DY + 1, 60, [10, 14], .35, ry=4)

    # near frame: harbour towers left and right with signs
    rr = random.Random(520)
    tower(c, 0, 9, 30, HOR, 0, 1, 14, rr, wins=[3, 5, 12, 13], lit=.3, dx=3, dy=3, ww=2, crown=5, ant=6)
    tower(c, 110, 119, 38, HOR, 0, 1, 14, rr, wins=[5, 3, 13], lit=.3, dx=3, dy=3, ww=2, lside=False, ant=8)
    vsign(c, 6, 40, 22, 7, 11, 0, rmp=[10, 7], k=.55)
    vsign(c, 111, 46, 16, 15, 5, 0, rmp=[9, 15], k=.5)
    shopfront(c, 0, 9, HOR, [15, 3, 5], 6, 0, [9, 15], .45)
    shopfront(c, 110, 119, HOR, [7, 12, 13], 8, 0, [10, 12], .45)
    car(c, 34, 76, 1, 2, 14, 4, 6, 15, k=.55)
    car(c, 84, 40, -1, 2, 14, 5, 6, 9, k=.5)

    # the bay: water mirrors the eclipse and the bridge; a quay rail at the bottom
    reflect(c, HOR, {0: 0, 1: 0, 2: 1, 10: 2, 9: 10, 14: 10, 12: 14, 13: 12, 11: 13, 4: 11, 3: 15, 5: 3, 15: 6,
                     6: 9, 7: 7, 8: 8}, [2, 1, 1, 0], stretch=.7, fade=52, ripple=3,
            wob=lambda x, y: (2 if (y // 2 + x // 6) % 4 == 0 else (-1 if (y + x // 5) % 5 == 0 else 0)))
    c.rect(0, HOR, W - 1, HOR, 14)
    # a hover-ferry crossing the bay, wake and headlight on the water
    BX, BY = 56, 89
    for i in range(1, 34):                                         # V wake behind it
        for sgn in (-1, 1):
            x, y = BX + 19 + i, BY + 3 + sgn * (i // 5)
            if th(x, y) < 1 - i / 34: c.px(x, y, 11 if i < 5 else (13 if i < 14 else 12))
    c.fill([(BX - 3, BY), (BX + 20, BY), (BX + 18, BY + 4), (BX, BY + 4)], 2)
    c.line(BX - 3, BY, BX + 20, BY, 13); c.line(BX, BY + 4, BX + 18, BY + 4, 0)
    c.line(BX - 1, BY + 2, BX + 18, BY + 2, lambda x, y: 6 if x % 3 else 2)              # hull stripe
    c.rect(BX + 4, BY - 3, BX + 16, BY - 1, 1); c.line(BX + 5, BY - 4, BX + 15, BY - 4, 14)
    for x in range(BX + 5, BX + 16, 2): c.px(x, BY - 2, 5 if x % 4 else 3)
    c.px(BX + 14, BY - 6, 6); c.line(BX + 14, BY - 5, BX + 14, BY - 5, 14)
    c.cone(BX - 3, BY + 1, 178, 7, 28, [10, 14, 12, 13], .9)
    c.px(BX - 3, BY + 1, 4); c.glow(BX - 3, BY + 1, 5, [12, 13], .7)
    c.glow(BX + 10, BY - 2, 12, [10, 14], .5, ry=5)
    for x in range(BX + 1, BX + 18, 2): c.px(x, BY + 5, c.mix(x, BY + 5, 1, 12, .5))
    c.rect(0, 106, W - 1, 106, 14); c.rect(0, 107, W - 1, H - 1, lambda x, y: c.mix(x, y, 1, 0, (y - 106) / 5))
    for x in range(4, W, 12): c.rect(x, 101, x, 106, 2); c.px(x, 101, 14)
    c.line(0, 102, W - 1, 102, lambda x, y: 2 if x % 12 != 4 else 14)
    for x in range(4, W, 24):
        c.rect(x, 96, x, 100, 2); c.px(x, 95, 5); c.glow(x, 95, 7, [10, 3, 5], .55)
    rain(c, 60, [10, 14, 12], 504, 104, lit=13)
    splashes(c, 18, 12, 14, 505, HOR)
    return c


# ------------------------------------------------------------------ scene 06: pagoda, dragon, storm
def scene06():
    pal = [(2, 8, 8), (6, 20, 22), (14, 40, 42), (255, 198, 60), (255, 255, 255), (255, 226, 170), (255, 90, 60),
           (0, 240, 240), (90, 255, 120), (150, 28, 44), (28, 68, 66), (246, 246, 230), (100, 172, 150),
           (196, 240, 218), (60, 104, 96), (255, 140, 40)]
    c = Cv(pal, 6)
    HOR = 88
    sky(c, [0, 1, 1, 2, 10, 10, 14], 0, HOR, pw=1.1)
    # lightning behind the clouds: a lit patch, then the bolt itself
    c.glow(96, 16, 28, [2, 10, 14, 12], .9, ry=22)
    cloud_bank(c, 16, 8, 61, 1, 2, y_lim=HOR, k=.15)
    for x in range(W):                                    # lit cloud rims near the strike
        for y in range(1, 40):
            if c.get(x, y) in (1, 2) and c.get(x, y + 1) not in (1, 2) and math.hypot(x - 96, y - 16) < 30:
                c.px(x, y, 12 if math.hypot(x - 96, y - 16) < 18 else 14)
    rr = random.Random(66)
    bx, by = 98, 0
    pts = [(bx, by)]
    while by < 58:
        bx += rr.choice((-3, -2, -1, 1, 2)); by += rr.randint(3, 6); pts.append((bx, by))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]): c.line(x0, y0, x1, y1, 11); c.line(x0 + 1, y0, x1 + 1, y1, 13)
    for i in (2, 5):
        x0, y0 = pts[i]; x1, y1 = x0 + 7, y0 + 6; c.line(x0, y0, x1, y1, 13); c.line(x1, y1, x1 + 3, y1 + 5, 12)
    c.glow(pts[-1][0], pts[-1][1], 10, [12, 13], .6)
    for x, y in pts[::2]: c.glow(x, y, 5, [14, 12], .45)

    # far city, mist rising from the river
    rr = random.Random(600)
    hzf = lambda x, y, col: c.mix(x, y, col, 14, max(0, (y - 64) / 26))
    x = -2
    while x < W:
        w = rr.randint(4, 8); top = rr.randint(46, 68)
        tower(c, x, x + w, top, HOR, 2, 10, 14, rr, wins=[12, 8, 3], lit=.2, hz=hzf, ant=rr.choice((0, 0, 3, 5)))
        x += w + rr.randint(0, 2)

    # dragon airship: serpentine envelope coiling in from the right, head toward the pagoda
    seg = []
    for i in range(80):
        t = i / 79
        x = 75 + t * 52; y = 31 + 8 * math.sin(t * 7.6 + .3) + t * 2
        r = 6.4 - 4.2 * t if t > .06 else 5.2 + t * 20
        seg.append((x, y, r))
    body = {}
    for k, (x, y, r) in enumerate(seg):
        for yy in range(int(y - r) - 1, int(y + r) + 2):
            for xx in range(int(x - r) - 1, int(x + r) + 2):
                if math.hypot(xx - x, (yy - y) * 1.1) <= r:
                    body[(xx, yy)] = ((y - yy) / r, k)                 # +1 top .. -1 belly
    for (x, y), (v, k) in body.items():
        col = c.ramp(x, y, [2, 10, 14, 12], v * .55 + .5)
        if v < -.35: col = 9 if (x + (y // 2) * 2) % 4 else 6     # red scaled belly
        if (x, y - 1) not in body: col = 13
        elif (x, y - 2) not in body: col = 12
        elif (x, y + 1) not in body: col = 1
        elif k % 9 == 0 and v > -.35: col = 2                       # envelope gores
        c.px(x, y, col)
    for i in range(6, 78, 4):                                      # dorsal fins, lanterns along the flank
        x, y, r = seg[i]; h = max(1, int(r * .5))
        for j in range(h + 1): c.px(x - j // 2, y - r - j, 9 if j < h else 6)
        if i % 8 == 2: c.px(x, y + r * .15, 15); c.glow(x, y + r * .15, 3, [15], .4)
    hx, hy = 75, int(seg[0][1])
    HEAD = [  # hand-drawn dragon head, facing left; its right edge meets the neck
        "......................W...",
        ".....................WL..W",
        "....................WL..WL",
        "...........WWWWW...WL..WL.",
        "........WWWHHHHHWWWL..WL..",
        ".....WWWHHLLLLLLLHHWWWWRR.",
        "...WWHHLLLMMM4rMMLLLLLLRRR",
        "..WHLLLMMMMMMrrMMMMMMLLLRR",
        ".KHLLMMMMDDDDMMMMMMMMMMLRR",
        "KLLMMDDDKKKKDDDDMMMMMMMLRR",
        "KTKTKTKTK..KKDDDDDMMMMMMLR",
        ".OYO3YOO......KDDDDDMMMMLR",
        "..TKTKTK.KKKKDDDDDDDMMMMR.",
        "..KrRRRRRRRRRRRRDDDDDMMR..",
        "...KKrRRRRRRRRRRRRDDDDR...",
        ".....KKKKKRRRRRRRRRRKK....",
    ]
    HC = {"K": 0, "D": 2, "M": 10, "L": 14, "H": 12, "W": 13, "R": 9, "r": 6, "Y": 3, "O": 15, "T": 11, "4": 4, "3": 4}
    ox, oy = hx + 3 - len(HEAD[0]), hy - 9
    for r_, row in enumerate(HEAD):
        for k, ch in enumerate(row):
            if ch != ".": c.px(ox + k, oy + r_, HC[ch])
    c.glow(ox - 2, oy + 11, 7, [9, 6, 15, 3], .9, ry=4)                                # fire breath
    for k in range(1, 7): c.px(ox - k, oy + 11 + (k % 2), 15 if k < 4 else 6)
    c.px(ox - 1, oy + 11, 4); c.px(ox - 2, oy + 11, 3)
    c.line(ox + 1, oy + 9, ox - 7, oy + 14, 5); c.line(ox - 7, oy + 14, ox - 6, oy + 18, 3)  # whiskers
    c.line(ox + 3, oy + 7, ox - 4, oy + 4, 5)
    c.glow(ox + 13, oy + 6, 3, [9, 6], .6)                                             # eye glint
    # gondola and propellers under the coil
    gx = 92; gy = int(max(y + r for x, y, r in seg if 84 < x < 100)) + 2
    c.rect(gx - 8, gy, gx + 8, gy + 3, 1); c.rect(gx - 8, gy, gx + 8, gy, 14); c.rect(gx - 6, gy + 4, gx + 6, gy + 4, 2)
    c.line(gx - 6, gy - 2, gx - 8, gy, 14); c.line(gx + 6, gy - 2, gx + 8, gy, 14)
    for x in range(gx - 6, gx + 7, 2): c.px(x, gy + 2, 15 if x % 4 else 5)
    c.glow(gx, gy + 2, 12, [10, 9, 15], .4, ry=5)
    for px_ in (gx - 11, gx + 11):
        c.line(px_, gy - 1, px_, gy + 5, 14); c.px(px_ - 1, gy + 1, 13); c.px(px_ + 1, gy + 3, 13)
    c.px(gx, gy + 5, 6); c.glow(gx, gy + 6, 4, [6], .5)

    # a distant advertising blimp drifting in the rain, its screen lit
    c.disc(13, 42, 9, lambda x, y: c.ramp(x, y, [1, 2, 10, 14], .75 - (y - 33) / 18), ry=4)
    c.line(5, 39, 20, 39, 14)
    c.rect(7, 41, 18, 43, 0); c.rect(8, 41, 17, 43, lambda x, y: (7 if (x + y) % 3 else 13) if x % 4 else 11)
    c.glow(13, 42, 12, [10, 14, 7], .45, ry=6)
    c.px(22, 41, 14); c.px(23, 40, 14); c.px(23, 43, 14); c.px(4, 42, 6); c.rect(11, 47, 15, 47, 1); c.px(13, 48, 6)

    # searchlights sweeping the storm; one pins the dragon
    c.cone(80, HOR, -76, 4, 100, [14, 12, 13, 11], 1.0)
    c.cone(110, HOR, -106, 3, 95, [14, 12, 13], .9)
    c.cone(16, HOR, -66, 3.5, 100, [14, 12, 13], .9)

    # pagoda
    P0 = 38
    tiers = [(6, 22), (8, 30), (10, 38), (12, 46), (14, 54), (16, 62), (18, 70)]
    c.rect(P0, 6, P0, 17, 14); c.px(P0, 4, 4); c.px(P0, 5, 3)
    for y in (9, 12, 15): c.px(P0 - 1, y, 3); c.px(P0 + 1, y, 3)
    c.glow(P0, 5, 9, [9, 15, 3], .9)
    c.rect(P0 - 2, 18, P0 + 2, 22, 1)
    for i, (hw, ty) in enumerate(tiers):
        bh = 6
        # storey wall with lit lattice windows
        c.rect(P0 - hw + 3, ty - bh + 1, P0 + hw - 3, ty, lambda x, y: 2 if x < P0 else 1)
        for x in range(P0 - hw + 4, P0 + hw - 3):
            for y in range(ty - bh + 2, ty - 1):
                if (x - P0) % 3 != 0 and (y - ty) % 3 != 0: c.px(x, y, 15 if (x + y + i) % 5 else 3)
        c.glow(P0, ty - 3, hw + 4, [9, 15], .32, ry=6)
        # roof: dark sweep with upturned eaves, red lacquer underside, gold trim
        for k in range(-hw - 2, hw + 3):
            a = abs(k); lift = max(0, a - hw + 2)
            y = ty + 1 - lift * 1
            c.px(P0 + k, y, 9 if a < hw else 6)
            c.px(P0 + k, y - 1, 2 if k < 0 else 1)
            if a < hw - 1: c.px(P0 + k, y - 2, 10 if k < 0 else 2)
            c.px(P0 + k, y + 1, 3 if a % 2 == 0 else 9)
        for sx in (-hw - 2, hw + 2):                               # hanging lanterns on the eave tips
            c.px(P0 + sx, ty + 1, 6); c.px(P0 + sx, ty + 2, 15); c.px(P0 + sx, ty + 3, 3)
            c.glow(P0 + sx, ty + 2, 4, [9, 15], .6)
    c.rect(P0 - 14, 72, P0 + 14, HOR, 1); c.rect(P0 - 14, 72, P0 - 14, HOR, 14)
    c.rect(P0 - 3, 77, P0 + 3, HOR, 9); c.rect(P0 - 2, 78, P0 + 2, HOR, 15); c.rect(P0 - 1, 79, P0 + 1, HOR, 3)
    c.glow(P0, 82, 10, [9, 15], .55)
    for x in range(P0 - 12, P0 + 13, 4): c.rect(x, 74, x + 1, 75, 15)
    c.rect(P0 - 17, 71, P0 + 17, 71, 9); c.rect(P0 - 18, 70, P0 + 18, 70, 2)

    # near layer: market streets with vertical signs, cables with lanterns
    rr = random.Random(620)
    tower(c, 0, 13, 56, HOR, 0, 1, 14, rr, wins=[3, 15, 12], lit=.3, dx=3, dy=4, ww=2, ant=7)
    tower(c, 62, 76, 66, HOR, 0, 1, 14, rr, wins=[15, 3, 8], lit=.3, dx=3, dy=4, ww=2, crown=3)
    tower(c, 100, 119, 52, HOR, 0, 1, 14, rr, wins=[3, 5, 7], lit=.3, dx=3, dy=4, ww=2, lside=False, ant=5)
    shopfront(c, 0, 13, HOR - 1, [15, 3, 5], 9, 0, [9, 15], .5)
    shopfront(c, 62, 76, HOR - 1, [8, 12, 13], 9, 0, [10, 8], .45)
    shopfront(c, 100, 119, HOR - 1, [7, 13, 3], 6, 0, [10, 14, 7], .5)
    vsign(c, 9, 60, 20, 8, 11, 0, rmp=[10, 8], k=.5)
    vsign(c, 102, 56, 22, 7, 11, 0, rmp=[14, 7], k=.5)
    hsign(c, 64, 70, 10, 4, 6, 5, 0, rmp=[9, 6], k=.4)
    hsign(c, 108, 80, 9, 3, 15, 3, 0, rmp=[9, 15], k=.3)
    cable(c, 13, 60, 62, 68, 4, 0, lights=6, every=5)
    cable(c, 76, 68, 100, 56, 4, 0, lights=15, every=4)
    cable(c, 13, 66, 62, 72, 3, 0, lights=3, every=7)
    car(c, 22, 60, 1, 2, 14, 4, 6, 15, k=.5); car(c, 90, 64, -1, 2, 14, 5, 6, 15, k=.5)
    stream(c, [(-2, 50), (60, 55), (122, 51)], [3, 5, 6], 3, 61, y1=HOR)

    c.rect(0, HOR - 1, W - 1, HOR - 1, 14)
    reflect(c, HOR, {0: 0, 1: 0, 2: 1, 10: 2, 14: 10, 12: 14, 13: 12, 11: 13, 4: 11, 9: 2, 6: 9, 15: 9, 3: 15,
                     5: 3, 7: 7, 8: 8}, [10, 2, 1, 0], wob=lambda x, y: (1 if (y // 2 + x // 5) % 3 == 0 else 0))
    for i in range(0, W, 12):
        c.line(i + 4, 96, i + 7, 96, 14); c.line(i * 1.3 - 10, 106, i * 1.3 - 5, 106, 14)
    rain(c, 85, [10, 14, 12], 604, HOR, lit=13)
    splashes(c, 26, 12, 14, 605, HOR)
    return c


if __name__ == "__main__":
    ims = []
    for n, f in ((4, scene04), (5, scene05), (6, scene06)):
        im = f().image(); im.save(os.path.join(HERE, "scene%02d.png" % n)); ims.append(im)
    pv = Image.new("RGB", (W * 3 + 8, H), (20, 20, 20))
    for i, im in enumerate(ims): pv.paste(im.convert("RGB"), (i * (W + 4), 0))
    pv.resize((pv.width * 3, pv.height * 3), Image.Resampling.NEAREST).save(os.path.join(HERE, "preview_b2.png"))
    sh = Image.new("RGB", (W * 4 * 3 + 16, H * 4), (20, 20, 20))
    for i, im in enumerate(ims):
        sh.paste(im.convert("RGB").resize((W * 4, H * 4), Image.Resampling.NEAREST), (i * (W * 4 + 8), 0))
    sh.save(os.path.join(HERE, "crop_b2.png"))
