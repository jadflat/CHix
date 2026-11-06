"""CHix scene05 v4 (round 2): ringed planet over a suspension bridge, wet bay. Deterministic.
Run: python paint_s05_v4.py  -> scene05.png, preview_s05v4.png (reads v3/scene05.png for the palette check).
Helpers copied from paint_b.py (never run that one). Round 2: bold shaded struts, open sky, banded lit planet."""
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



# ================================================================== scene05 v4
PAL05 = [(2, 5, 14), (6, 14, 34), (14, 30, 62), (255, 196, 70), (255, 255, 255), (255, 214, 160), (255, 84, 70),
         (0, 235, 255), (70, 255, 150), (100, 54, 132), (30, 56, 104), (244, 244, 255), (96, 148, 214),
         (184, 218, 248), (70, 100, 150), (255, 150, 60)]


def scene05():
    c = Cv(PAL05, 5)
    HOR = 80
    sky(c, [0, 0, 1, 1, 2, 10, 9], 0, HOR, pw=1.1)
    stars(c, [(4, 4), (26, 3), (9, 25), (36, 9), (95, 6), (108, 18), (116, 3), (84, 2), (3, 37), (49, 2),
              (74, 4), (22, 44), (114, 40)], [13, 12, 14])
    PX, PY, PR = 60, 34, 23
    LX, LY, LZ = .72, -.52, .46                                  # sun: upper right, slightly behind
    ln_ = math.sqrt(LX * LX + LY * LY + LZ * LZ); LX, LY, LZ = LX / ln_, LY / ln_, LZ / ln_
    TIL = math.radians(-14)
    ct, st = math.cos(TIL), math.sin(TIL)
    # atmosphere glow on the lit side, a faint wide corona
    c.glow(PX, PY, PR + 18, [1, 2, 10], .7, pw=1.4)
    c.glow(118, -6, 44, [1, 2, 10, 14], .75, pw=1.3)
    c.glow(PX + 9, PY - 7, PR + 9, [2, 10, 14, 12], .9, pw=1.5)

    def ring_at(x, y):
        """(radius in ring units, front?) for the tilted ring plane."""
        dx, dy = x + .5 - PX, y + .5 - PY
        ex = dx * ct + dy * st; ey = -dx * st + dy * ct
        return math.hypot(ex, ey / .27), ey > 0, ex

    RB = ((33.5, 36.5, 14, 12), (36.5, 40.5, 12, 13), (40.5, 41.8, None, None), (41.8, 45.5, 14, 12))

    def ring_col(x, y, r, ex, shade):
        for r0, r1, lo, hi in RB:
            if r0 <= r < r1:
                if lo is None: return None
                f = .15 + .8 * (ex / 45 + 1) / 2 + .15 * math.sin(r * 3.1)   # brighter toward the sun side
                col = c.mix(x, y, lo, hi, f)
                if r - r0 < .9 or r1 - r < .7: col = {14: 10, 12: 14, 13: 12}[col]  # soft band edges
                if shade: col = {14: 2, 12: 10, 13: 14}[col]
                return col
        return None

    # back half of the ring (behind the planet)
    for y in range(0, 70):
        for x in range(W):
            r, front, ex = ring_at(x, y)
            if front or math.hypot(x + .5 - PX, y + .5 - PY) <= PR: continue
            col = ring_col(x, y, r, ex, False)
            if col is not None: c.px(x, y, col)
    # the planet: lit gibbous, banded, terminator dithered, a storm, the ring's shadow on its face
    RMP = [0, 1, 2, 10, 14, 12, 13, 11]
    SX, SY = .30, .30                                            # storm centre (on the disc, unit coords)
    for y in range(PY - PR - 1, PY + PR + 2):
        for x in range(PX - PR - 1, PX + PR + 2):
            u, v = (x + .5 - PX) / PR, (y + .5 - PY) / PR
            d2 = u * u + v * v
            if d2 > 1: continue
            z = math.sqrt(1 - d2)
            s = u * LX + v * LY + z * LZ                             # lambert
            lat = -u * st + v * ct                                   # latitude along the ring tilt
            lon = u * ct + v * st
            band = math.sin(lat * 10.5 + .9 * math.sin(lon * 4 + lat * 6)) * .55 + math.sin(lat * 23 + lon * 2) * .2
            t = max(0., s) ** .8 * 5.6 + .7 + band * (.45 + .4 * max(0., s))
            if s < 0: t = .7 + band * .35 + s * 1.2                  # night side: faint bands only
            # storm oval with a bright rim and a darker eye
            se = math.hypot((lon - SX) / .17, (lat - SY) / .085)
            if se < 1:
                t += .9 * (1 - se) if se > .45 else -.6
            t = max(0., min(len(RMP) - 1.001, t))
            i = int(t); col = RMP[i] if th(x, y) >= t - i else RMP[min(i + 1, len(RMP) - 1)]
            # purple dust bands in the mid tones
            if col in (10, 14, 2) and math.sin(lat * 10.5 + .9 * math.sin(lon * 4 + lat * 6)) > .8:
                col = 9 if col != 2 else 2
            # ring shadow: a dark band just below the front ring, offset by the light
            rr, fr, _ = ring_at(x + 2, y - 3)
            if 33.5 <= rr <= 45.5 and fr and s > -.1 and not (40.5 <= rr < 41.8):
                col = {11: 12, 13: 14, 12: 10, 14: 2, 10: 1, 9: 2, 2: 1}.get(col, col)
            c.px(x, y, col)
    # lit limb: a crisp 1-2 px edge on the sun side, hot where the light grazes
    for y in range(PY - PR - 1, PY + PR + 2):
        for x in range(PX - PR - 1, PX + PR + 2):
            d = math.hypot(x + .5 - PX, y + .5 - PY)
            if PR - 1.6 < d <= PR:
                u, v = (x + .5 - PX) / PR, (y + .5 - PY) / PR
                s = u * LX + v * LY
                if s > .25: c.px(x, y, 13 if s < .75 or d < PR - .8 else 11)
                elif s > .05 and th(x, y) < .5: c.px(x, y, 12)
    # storm swirl detail
    for k in range(10):
        a = k * .7
        su, sv = SX + math.cos(a) * .12 * (1 - k / 14), SY + math.sin(a) * .05 * (1 - k / 14)
        x = PX + (su * ct - sv * st) * PR; y = PY + (su * st + sv * ct) * PR
        if c.get(x, y) in (12, 14, 10): c.px(x, y, 13 if k % 3 else 12)
    # front half of the ring
    for y in range(0, 70):
        for x in range(W):
            r, front, ex = ring_at(x, y)
            if not front: continue
            onp = math.hypot(x + .5 - PX, y + .5 - PY) <= PR
            col = ring_col(x, y, r, ex, False)
            if col is None: continue
            if onp:                                                   # over the face: brighter, dark-edged
                col = {14: 12, 12: 13, 13: 13, 10: 14}[col] if ex > -8 else col
                if r < 34.4 or r > 44.6: col = 1
            c.px(x, y, col)
    # a small cratered moon, upper left
    MX, MY, MR = 31, 13, 4.6
    for y in range(int(MY - MR) - 1, int(MY + MR) + 2):
        for x in range(int(MX - MR) - 1, int(MX + MR) + 2):
            u, v = (x + .5 - MX) / MR, (y + .5 - MY) / MR
            if u * u + v * v > 1: continue
            z = math.sqrt(1 - u * u - v * v)
            s = u * LX + v * LY + z * LZ
            t = max(0., s) * 4.2
            i = min(int(t), 3); col = [1, 10, 14, 12, 13][i if th(x, y) >= t - i else i + 1]
            c.px(x, y, col)
    for cx_, cy_, cr in ((MX + 1, MY - 1, 1.3), (MX - 1, MY + 2, 1.0), (MX + 2.5, MY + 1.5, .8)):
        c.disc(cx_, cy_, cr, lambda x, y: {13: 12, 12: 14, 14: 10, 10: 1}.get(c.get(x, y), c.get(x, y)))
        c.px(cx_ + 1, cy_ + 1, 13 if c.get(cx_ + 1, cy_ + 1) in (12, 13) else None)

    # far skyline in the haze beyond the bridge: big shaded blocks, few windows, foggy at the base
    rr = random.Random(500)
    hzf = lambda x, y, col: c.mix(x, y, col, 2 if col in (0, 1) else 10, max(0, (y - 64) / 22))
    x = 8
    while x < 112:
        w = rr.randint(7, 12); top = rr.randint(56, 66)
        if 36 < x < 80: top = rr.randint(54, 61)
        tower(c, x, x + w, top, HOR, 1, 0, 2, rr, wins=[10, 14, 14, 12], lit=.10, hz=hzf, ant=rr.choice((0, 0, 4)),
              crown=rr.choice((0, 0, 3)), dx=3, dy=3, ww=2)
        x += w + rr.randint(1, 3)
    # mist band over the bay's far shore
    for y in range(62, HOR):
        for x in range(W):
            f = (y - 62) / 18 * .55
            if c.get(x, y) in (0, 1, 2) and th(x, y) < f: c.px(x, y, c.get(x, y) + 1 if c.get(x, y) < 2 else 10)

    # suspension bridge: two bold towers, heavy cables, few suspenders
    DY, TT = 69, 8
    T1, T2 = 17, 103
    for tx in (T1, T2):
        lit_r = tx < PX                                          # face that sees the planet/sun
        for y in range(TT, HOR):
            for x in range(tx - 4, tx + 5):
                if abs(x - tx) <= 1 and y > TT + 4: continue         # portal between the two legs
                o = (x - tx) if lit_r else (tx - x)                  # +4 = planet-facing outer edge
                if o == 4: col = 12 if y < 60 else 14
                elif o == 3: col = 14 if th(x, y) < .55 else 2
                elif o in (1, 2, -2): col = 2 if o > 0 else 1
                else: col = 1 if o > -4 else 0
                if o in (-1, 1, 2, 3) and abs(x - tx) == 2 and o != 2: pass
                c.px(x, y, col)
        for yy in (TT + 2, 31, 52):                                 # cross beams, 3 px, shaded
            c.rect(tx - 4, yy, tx + 4, yy + 2, 1)
            c.rect(tx - 4, yy, tx + 4, yy, 14)
            c.rect(tx - 4, yy + 2, tx + 4, yy + 2, 0)
            c.px(tx + (4 if lit_r else -4), yy, 12); c.px(tx + (4 if lit_r else -4), yy + 1, 14)
        c.rect(tx - 5, TT - 1, tx + 5, TT + 1, 1); c.rect(tx - 5, TT - 1, tx + 5, TT - 1, 14)   # saddle cap
        c.rect(tx + (2 if lit_r else -5), TT - 1, tx + (5 if lit_r else -2), TT - 1, 12)
        c.rect(tx - 1, TT - 5, tx, TT - 2, 1); c.px(tx, TT - 5, 14)                            # mast
        c.rect(tx - 1, TT - 7, tx, TT - 6, 6); c.glow(tx - .5, TT - 6.5, 6, [9, 6], .55)
        for y in range(TT + 9, DY - 2, 11):                                                     # red aviation lights
            ox = tx - 5 if lit_r else tx + 5
            c.rect(ox, y, ox, y + 1, 6); c.glow(ox, y + .5, 4, [9], .45)
    # cable curves
    def cab_y(x):
        if x < T1: return TT + 1 + (DY - TT - 4) * ((T1 - x) / T1) ** 1.25
        if x > T2: return TT + 1 + (DY - TT - 4) * ((x - T2) / (W - 1 - T2)) ** 1.25
        t = (x - T1) / (T2 - T1); return TT + 1 + (DY - TT - 9) * (1 - (2 * t - 1) ** 2)
    for x in range(W):
        if abs(x - T1) <= 4 or abs(x - T2) <= 4: continue
        y = round(cab_y(x))
        if x % 8 == 4 and y + 3 < DY:                               # suspenders: few, dim, dithered
            for yy in range(y + 2, DY):
                if th(x, yy) < .7: c.px(x, yy, 2 if c.L[c.get(x, yy)] < c.L[2] + 30 else None)
    for x in range(W):
        if abs(x - T1) <= 4 or abs(x - T2) <= 4: continue
        y = round(cab_y(x)); y2 = round(cab_y(x + .5))
        c.px(x, y - 1, 12 if th(x, y) < .75 else 14); c.px(x, y, 14); c.px(x, y + 1, 1)
        if y2 != y: c.px(x, y2, 14)
    # deck: thick, with a lit fascia, two clustered traffic streams
    c.rect(0, DY, W - 1, DY + 5, 1)
    c.rect(0, DY, W - 1, DY, 14)
    c.rect(0, DY + 5, W - 1, DY + 5, 0)
    for x in range(0, W): c.px(x, DY + 4, 2 if (x // 6) % 2 else 10)
    rr = random.Random(53)
    x = -2
    while x < W:                                                  # headlights: warm pairs heading right
        col = rr.choice((5, 5, 11, 3)); n = rr.randint(2, 4)
        c.rect(x, DY + 1, x + n - 1, DY + 1, col)
        if col in (5, 11): c.px(x + n, DY + 1, 14)
        x += n + rr.randint(4, 9)
    x = -1
    while x < W:                                                  # tail lights heading left
        col = rr.choice((6, 6, 15)); n = rr.randint(2, 3)
        c.rect(x, DY + 2, x + n - 1, DY + 2, col)
        x += n + rr.randint(4, 10)
    for x in range(4, W, 16):                                     # deck lamps, 2 px
        if abs(x - T1) > 5 and abs(x - T2) > 5:
            c.rect(x, DY - 2, x, DY - 1, 2); c.rect(x - 1, DY - 3, x, DY - 3, 3)
            c.glow(x - .5, DY - 2.5, 5, [10, 15], .45)
    c.glow(60, DY + 1, 60, [10, 14], .3, ry=4)

    # near frame: harbour towers left and right with signs
    rr = random.Random(520)
    tower(c, -1, 8, 30, HOR, 0, 1, 14, rr, wins=[3, 5, 12, 13], lit=.3, dx=3, dy=3, ww=2, crown=5, ant=6, lside=False)
    tower(c, 112, 120, 38, HOR, 0, 1, 14, rr, wins=[5, 3, 13], lit=.3, dx=3, dy=3, ww=2, ant=8)
    vsign(c, 3, 40, 22, 7, 11, 0, rmp=[10, 7], k=.55)
    vsign(c, 114, 46, 16, 15, 5, 0, rmp=[9, 15], k=.5)
    shopfront(c, 0, 8, HOR, [15, 3, 5], 6, 0, [9, 15], .45)
    shopfront(c, 112, 119, HOR, [7, 12, 13], 8, 0, [10, 12], .45)
    car(c, 30, 47, 1, 2, 14, 5, 6, 9, k=.5)

    # the bay: water mirrors the planet and the bridge
    reflect(c, HOR, {0: 0, 1: 0, 2: 1, 10: 2, 9: 10, 14: 10, 12: 14, 13: 12, 11: 13, 4: 11, 3: 15, 5: 3, 15: 6,
                     6: 9, 7: 7, 8: 8}, [2, 1, 1, 0], stretch=.7, fade=52, ripple=3,
            wob=lambda x, y: (2 if (y // 2 + x // 6) % 4 == 0 else (-1 if (y + x // 5) % 5 == 0 else 0)))
    c.rect(0, HOR, W - 1, HOR, 14)
    # a hover-ferry crossing the bay, wake and headlight on the water
    BX, BY = 56, 89
    for i in range(1, 34):
        for sgn in (-1, 1):
            x, y = BX + 19 + i, BY + 3 + sgn * (i // 5)
            if th(x, y) < 1 - i / 34: c.px(x, y, 11 if i < 5 else (13 if i < 14 else 12))
    c.fill([(BX - 3, BY), (BX + 20, BY), (BX + 18, BY + 4), (BX, BY + 4)], 2)
    c.line(BX - 3, BY, BX + 20, BY, 13); c.line(BX, BY + 4, BX + 18, BY + 4, 0)
    c.line(BX - 1, BY + 2, BX + 18, BY + 2, lambda x, y: 6 if x % 3 else 2)
    c.rect(BX + 4, BY - 3, BX + 16, BY - 1, 1); c.line(BX + 5, BY - 4, BX + 15, BY - 4, 14)
    for x in range(BX + 5, BX + 16, 3): c.rect(x, BY - 2, x + 1, BY - 2, 5 if x % 2 else 3)
    c.px(BX + 14, BY - 6, 6); c.line(BX + 14, BY - 5, BX + 14, BY - 5, 14)
    c.cone(BX - 3, BY + 1, 178, 7, 28, [10, 14, 12, 13], .9)
    c.px(BX - 3, BY + 1, 4); c.glow(BX - 3, BY + 1, 5, [12, 13], .7)
    c.glow(BX + 10, BY - 2, 12, [10, 14], .5, ry=5)
    for x in range(BX + 1, BX + 18, 2): c.px(x, BY + 5, c.mix(x, BY + 5, 1, 12, .5))
    c.rect(0, 106, W - 1, 106, 14); c.rect(0, 107, W - 1, H - 1, lambda x, y: c.mix(x, y, 1, 0, (y - 106) / 5))
    for x in range(4, W, 12): c.rect(x, 101, x, 106, 2); c.px(x, 101, 14)
    c.line(0, 102, W - 1, 102, lambda x, y: 2 if x % 12 != 4 else 14)
    for x in range(4, W, 24):
        c.rect(x, 96, x, 100, 2); c.rect(x - 1, 95, x, 95, 5); c.glow(x - .5, 95, 7, [10, 3, 5], .55)
    rain(c, 22, [10, 14], 504, 104, lit=12)
    splashes(c, 12, 12, 14, 505, HOR)
    return c


def lone_gold(c):
    """Gold (3) pixels with no gold 8-neighbour become orange (15): the game's gold sheen owns lone gold."""
    out = []
    for y in range(H):
        for x in range(W):
            if c.a[y][x] == 3 and not any(c.get(x + dx, y + dy) == 3 for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                                          if dx or dy):
                out.append((x, y))
    for x, y in out: c.a[y][x] = 15
    return len(out)


if __name__ == "__main__":
    old = Image.open(os.path.join(HERE, "v3", "scene05.png"))
    c = scene05()
    n = lone_gold(c)
    im = c.image()
    assert im.getpalette()[:48] == old.getpalette()[:48]
    im.save(os.path.join(HERE, "scene05.png"))
    print("lone gold fixed:", n)
    ims = [im, old] + [Image.open(os.path.join(HERE, "scene%02d.png" % k)) for k in (0, 4, 6)]
    pv = Image.new("RGB", (W * 4 * 2 + 8, H * 4 * 3 + 16), (30, 30, 30))
    for i, m in enumerate(ims):
        pv.paste(m.convert("RGB").resize((W * 4, H * 4), Image.Resampling.NEAREST),
                 ((i % 2) * (W * 4 + 8), (i // 2) * (H * 4 + 8)))
    pv.save(os.path.join(HERE, "preview_s05v4.png"))
