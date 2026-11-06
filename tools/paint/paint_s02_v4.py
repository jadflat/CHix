"""CHix scene02 v4 (round 2: storm geisha; hair with form and ornaments, a misty wet street level).
Run: python paint_s02_v4.py   (deterministic; reads v3/scene02.png for the palette, writes scene02.png and
preview_s02v4.png only). Started from paint_s02_v3.py; helpers copied from paint_a.py (do not run that one).
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw

W, H = 120, 112
HERE = os.path.dirname(os.path.abspath(__file__))
B4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])
YY, XX = np.mgrid[0:H, 0:W]
BAY = B4[YY & 3, XX & 3]
# fixed roles (game meaning): 0 bg, 3 gold, 4 white, 5 pale, 6 red, 7 cyan, 8 green, 11 text, 14 frame, 15 glow
FIX = {0: (4, 4, 12), 3: (255, 200, 40), 4: (255, 255, 255), 5: (190, 215, 255), 6: (255, 70, 70),
       7: (0, 230, 255), 8: (60, 255, 120), 11: (232, 240, 255), 14: (96, 108, 170), 15: (255, 60, 200)}
R = [0, 1, 10, 2, 9, 13]          # scene hue ramp, dark -> light (free slots 1,10,2,9,13)
ACC = 12                           # scene accent (free slot)
LIGHT = {3, 4, 5, 6, 7, 8, 11, 12, 15}


def H_(s):
    return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))


def pal(s):
    return dict(zip((1, 10, 2, 9, 13, 12), map(H_, s.split())))


PALS = [pal("#110a26 #22123e #3a1d5c #5e2f84 #9a68c0 #ff7a2e"),   # violet night, orange fire
        pal("#06132c #0c2346 #17396a #285c90 #5c9ac4 #ff8c26"),   # harbour blue, reactor orange
        pal("#04181a #0a2a2c #134240 #1f6460 #5cae9c #ff3c7c"),   # storm teal, holo rose
        pal("#18060e #2c0e18 #481a26 #6e2a32 #b4645a #ff7a1e")]   # blood dusk, fire orange


# ------------------------------------------------------------------ masks
def m_poly(pts):
    im = Image.new('L', (W, H), 0)
    ImageDraw.Draw(im).polygon([(float(x), float(y)) for x, y in pts], fill=1)
    return np.array(im) > 0


def m_line(pts, w=1):
    im = Image.new('L', (W, H), 0)
    ImageDraw.Draw(im).line([(float(x), float(y)) for x, y in pts], fill=1, width=w)
    return np.array(im) > 0


def m_ell(cx, cy, rx, ry=None):
    ry = ry or rx
    return ((XX + .5 - cx) / rx) ** 2 + ((YY + .5 - cy) / ry) ** 2 <= 1


def m_rect(x0, y0, x1, y1):
    return (XX >= x0) & (XX <= x1) & (YY >= y0) & (YY <= y1)


def sh(m, dx, dy):
    """n[y,x] = m[y+dy, x+dx] (False outside)."""
    n = np.zeros_like(m)
    ys, yd = (slice(dy, None), slice(0, H - dy)) if dy >= 0 else (slice(0, H + dy), slice(-dy, None))
    xs, xd = (slice(dx, None), slice(0, W - dx)) if dx >= 0 else (slice(0, W + dx), slice(-dx, None))
    n[yd, xd] = m[ys, xs]
    return n


def edge(m, dx, dy):
    return m & ~sh(m, dx, dy)


def dil(m, n=1):
    for _ in range(n):
        m = m | sh(m, 1, 0) | sh(m, -1, 0) | sh(m, 0, 1) | sh(m, 0, -1)
    return m


def dist(m, cap=12):
    """Approximate Euclidean distance from mask m (0 inside), capped."""
    d = np.full((H, W), float(cap))
    ys, xs = np.nonzero(m)
    if len(ys) == 0:
        return d
    for i in range(0, len(ys), 400):
        y, x = ys[i:i + 400, None, None], xs[i:i + 400, None, None]
        d = np.minimum(d, np.sqrt((YY[None] - y) ** 2 + (XX[None] - x) ** 2).min(0))
    return d


class Cv:
    def __init__(s, n):
        s.a = np.zeros((H, W), np.uint8)
        s.n = n

    def px(s, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < W and 0 <= y < H:
            s.a[y, x] = c

    def get(s, x, y):
        x, y = int(x), int(y)
        return int(s.a[y, x]) if 0 <= x < W and 0 <= y < H else 0

    def fill(s, m, c):
        s.a[m] = c

    def ramp(s, m, t, ramp):
        """Dithered ramp: t (scalar or HxW) indexes ramp (float)."""
        t = np.clip(np.broadcast_to(t, (H, W)), 0, len(ramp) - 1.001)
        i = t.astype(int)
        f = t - i
        idx = np.where(BAY < f * 16, i + 1, i)
        s.a[m] = np.array(ramp, np.uint8)[idx][m]

    def over(s, cols):
        return np.isin(s.a, list(cols))

    def glow(s, src, col, r, k=9, onto=None, d=None):
        """Ordered-dither bloom of colour col around mask src, only onto colours in onto."""
        onto = onto if onto is not None else (0, 1, 10, 2)
        d = dist(src, r + 1) if d is None else d
        m = (d > 0) & (d <= r) & (BAY < k * (1 - (d - .5) / (r + .5))) & s.over(onto)
        s.a[m] = col

    def glyph_sign(s, x, y, n, frame, ink, seed, vertical=True, bg=0):
        """Sign with n kanji-like 3x3 glyphs, 1px gap, in a frame."""
        gw, gh = (5, 4 * n + 1) if vertical else (4 * n + 1, 5)
        s.fill(m_rect(x - 1, y - 1, x + gw, y + gh), frame)
        s.fill(m_rect(x, y, x + gw - 1, y + gh - 1), bg)
        for i in range(n):
            gx, gy = (x + 1, y + 1 + 4 * i) if vertical else (x + 1 + 4 * i, y + 1)
            for yy, xx in glyph(seed * 7 + i):
                s.px(gx + xx, gy + yy, ink)


GL = ["111010111", "101111101", "110011110", "111101111", "010111010", "111100111", "101010101",
      "011110011", "111010010", "100111001", "111001111", "010110011", "110111011", "101101111"]


def glyph(k):
    g = GL[(k * 2654435761 >> 5) % len(GL)]
    return [(i // 3, i % 3) for i in range(9) if g[i] == '1']


def hsh(a, b, s=0):
    return (((a * 73856093) ^ (b * 19349663) ^ (s * 83492791)) * 2654435761 % 4294967296) >> 12 & 255


def sprite(c, x0, y0, rows, key, flip=False):
    for y, row in enumerate(rows):
        if flip:
            row = row[::-1]
        for x, ch in enumerate(row):
            if ch in key:
                c.px(x0 + x, y0 + y, key[ch])


# ------------------------------------------------------------------ shared scenery
def sky(c, top, bot, horizon, t0=0.0, t1=4.6, wob=.35):
    """Gradient sky over the whole frame, with soft cloud banding."""
    yy = np.clip((YY - top) / max(bot - top, 1), 0, 1)
    t = t0 + (t1 - t0) * yy ** 1.4
    t = t + wob * (np.sin(XX * .07 + YY * .31) * np.sin(YY * .23 - XX * .02)) * (1 - yy)
    c.ramp(YY <= horizon, t, R)


def clouds(c, y0, y1, seed, lit_dir=1, lo=1, hi=2, rim=9, cover=.5):
    """Horizontal cloud banks: dark bodies with a dithered lit rim on one side."""
    r = np.random.RandomState(seed)
    m = np.zeros((H, W), bool)
    for _ in range(14):
        cx, cy = r.randint(-10, W + 10), r.randint(y0, y1)
        rx, ry = r.randint(10, 26), r.randint(2, 5)
        m |= m_ell(cx, cy, rx, ry)
    m &= (np.sin(XX * .19 + seed) * 1.2 + np.sin(XX * .07 - seed) * 1.5 + (YY - y0) * .0) > -cover * 3
    body = m & (BAY < 14)
    c.fill(body & c.over((0, 1, 10, 2)), lo)
    e = m & ~sh(m, 0, -lit_dir) & ~sh(m, 0, -2 * lit_dir)
    c.fill(e & (BAY < 10), hi)
    c.fill(edge(m, 0, -lit_dir) & (BAY < 8), rim)


def stars(c, n, seed, ymax=40):
    r = np.random.RandomState(seed)
    for _ in range(n):
        x, y = r.randint(0, W), r.randint(0, ymax)
        if c.get(x, y) in (0, 1, 10):
            c.px(x, y, (13, 5, 13, 11)[r.randint(0, 4)])
    for _ in range(max(n // 8, 1)):
        x, y = r.randint(2, W - 2), r.randint(1, ymax)
        if c.get(x, y) in (0, 1, 10):
            c.px(x, y, 4)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                c.px(x + dx, y + dy, 13)


def moon(c, cx, cy, r, tones, halo=(9, 2), craters=True, phase=None):
    m = m_ell(cx, cy, r)
    d = dist(m, 12)
    for i, col in enumerate(halo):
        rr = (i + 1) * r * .45 + 2
        mm = (d > 0) & (d < rr) & (BAY < 12 - i * 5 - d / rr * 6) & c.over((0, 1, 10, 2, 9))
        c.fill(mm, col)
    l = ((XX + .5 - cx) * -.6 + (YY + .5 - cy) * -.8) / r     # lit from top-left
    t = (l * .5 + .5) * (len(tones) - 1) + 0.0
    c.ramp(m, t, tones)
    if craters:
        for dx, dy, rr in ((-.35, -.2, .22), (.25, .3, .28), (.1, -.45, .14), (-.15, .45, .16), (.5, -.1, .12)):
            mm = m_ell(cx + dx * r, cy + dy * r, rr * r) & m
            c.fill(mm & (BAY < 9), tones[max(0, 1)])
            c.fill(edge(mm, 1, 1) & m, tones[-1])


def building(c, x0, x1, top, base, body, lit, rimcol, wins, dens, seed, wx=2, wy=3, ww=1, wh=1,
             roof=True, side=0.3, haze=None):
    """A block with a lit (left) face strip, rim light, windows and rooftop clutter."""
    m = m_rect(x0, top, x1, base)
    c.fill(m, body)
    sw = max(1, int((x1 - x0 + 1) * side))
    c.fill(m_rect(x0, top, x0 + sw - 1, base), lit)
    if rimcol is not None:
        c.fill(m_rect(x0, top, x0, base) & (BAY < 12), rimcol)
        c.fill(m_rect(x0, top, x1, top), rimcol)
    if wins:
        wc = wins[hsh(x0, seed, 3) % len(wins)]          # one light colour per block
        for y in range(top + 3, base - 1, wy):
            fl = hsh(x0, y, seed + 5)                       # whole floors lit or dark
            if fl > dens:
                continue
            for x in range(x0 + 2, x1 - ww, wx):
                h = hsh(x, y, seed)
                if h < 200:
                    c.fill(m_rect(x, y, x + ww - 1, y + wh - 1), wc if h > 30 else wins[h % len(wins)])
    if haze is not None:
        col, k = haze
        c.fill(m & (BAY < k * np.clip((YY - top) / max(base - top, 1), 0, 1)), col)
    if roof:
        r = hsh(x0, top, seed + 1) % 5
        mid = (x0 + x1) // 2
        if r == 0:
            c.fill(m_rect(mid, top - 5, mid, top - 1), body)
            c.px(mid, top - 6, 6)
        elif r == 1:
            c.fill(m_rect(x0 + 1, top - 3, x0 + 4, top - 1), body)
            c.fill(m_rect(x0 + 1, top - 3, x0 + 4, top - 3), lit)
        elif r == 2 and x1 - x0 > 6:
            c.fill(m_rect(x0 + 1, top - 1, x1 - 1, top - 1), body)
            for xx in range(x0 + 2, x1 - 1, 2):
                c.px(xx, top - 2, body)
        elif r == 3:
            c.fill(m_ell(x1 - 2, top - 2, 2, 1.5), body)
            c.px(x1 - 3, top - 3, lit)
            c.fill(m_rect(x1 - 2, top - 7, x1 - 2, top - 3), body)
        elif r == 4 and x1 - x0 > 5:                     # water tank on legs
            c.fill(m_rect(x0 + 1, top - 6, x0 + 4, top - 3), body)
            c.fill(m_rect(x0 + 1, top - 6, x0 + 1, top - 3), lit)
            c.px(x0 + 1, top - 2, body)
            c.px(x0 + 4, top - 2, body)
            c.px(x0 + 2, top - 7, body)
            c.px(x0 + 3, top - 7, body)
        if hsh(x1, top, seed + 2) % 3 == 0 and base - top > 10:   # drain pipe / fire escape
            px_ = x1 - 1
            c.fill(m_rect(px_, top + 2, px_, base), lit)
            for yy in range(top + 4, base - 2, 5):
                c.px(px_ - 1, yy, lit)


def skyline(c, seed, ymin, ymax, base, wmin, wmax, **kw):
    r = np.random.RandomState(seed)
    x = -r.randint(0, 6)
    out = []
    while x < W:
        w = r.randint(wmin, wmax + 1)
        top = r.randint(ymin, ymax + 1)
        building(c, x, x + w - 1, top, base, seed=seed + x, **kw)
        out.append((x, x + w - 1, top))
        x += w + (1 if r.rand() < .25 else 0)
    return out


def car(c, x, y, d, body, tail, head=4, trail=10):
    """Flying car: 6x3 body with light trail behind and a headlight in front."""
    pts = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (1, -1), (2, -1), (3, -1), (0, 1), (5, 1)]
    for px_, py_ in pts:
        c.px(x + (px_ if d > 0 else 5 - px_), y + py_, body)
    c.px(x + (2 if d > 0 else 3), y - 1, 5)
    c.px(x + (6 if d > 0 else -1), y, head)
    c.px(x + (7 if d > 0 else -2), y, head if True else 0)
    for i in range(1, trail):
        xx = x - d * i + (0 if d > 0 else 5)
        if BAY[y % H & 3 if 0 <= y < H else 0, xx & 3] < 16 - i * 16 // trail:
            c.px(xx, y, tail)
    c.px(x + (0 if d > 0 else 5), y + 1, tail)


def rain(c, seed, n, cols=(13, 14), hi=(5, 11), y0=0, y1=H, slant=1, ln=3, avoid=LIGHT):
    r = np.random.RandomState(seed)
    for _ in range(n):
        x, y = r.randint(0, W + 6), r.randint(y0, y1)
        near = r.rand() < .25
        L = ln + (2 if near else 0)
        col = hi[r.randint(0, len(hi))] if near else cols[r.randint(0, len(cols))]
        for i in range(L):
            xx, yy = x - (i * slant) // 2, y + i
            if c.get(xx, yy) not in avoid:
                c.px(xx, yy, col)


DIM = {4: 5, 11: 5, 5: 13, 3: 12}


def reflect(c, g, bright=LIGHT, dark=None, ripple=1.2, fade=14, step=1.0, wet=None):
    """Wet street / water: mirrored scene below line g, ripple offsets, lights stretched."""
    src = c.a.copy()
    dark = dark or {}
    for y in range(g + 1, H):
        d = y - g
        sy = int(g - d * step)
        for x in range(W):
            wob = int(round(math.sin(y * 1.9 + x * .21) * ripple * (.4 + d / (H - g))))
            sx = min(max(x + wob, 0), W - 1)
            col = 0
            for k in (0, 1, 2):
                v = int(src[min(max(sy - k, 0), g), sx])
                if v in bright:
                    col = v
                    break
            if col and BAY[y & 3, x & 3] < fade - d * fade / (H - g + 6):
                c.px(x, y, col if d < 4 else DIM.get(col, col))
            else:
                v = int(src[min(max(sy, 0), g), sx])
                c.px(x, y, dark.get(v, 0))
    if wet:
        r = np.random.RandomState(g)
        for _ in range(wet[1]):
            x, y = r.randint(0, W - 6), r.randint(g + 3, H)
            for i in range(r.randint(2, 6)):
                if c.get(x + i, y) in (0, 1, 10):
                    c.px(x + i, y, wet[0])


def storefronts(c, x0, x1, top, g, seed, cols, sign=True):
    """Street-level shops: dark wall, lit shop windows, awnings, horizontal neon glyph signs."""
    r = np.random.RandomState(seed)
    x = x0
    while x < x1:
        w = r.randint(8, 14)
        xe = min(x + w - 1, x1)
        col = cols[r.randint(0, len(cols))]
        c.fill(m_rect(x, top, xe, g), 0)
        lit = 3 if col in (12, 15, 6) else 5
        c.fill(m_rect(x + 1, g - 6, xe - 1, g - 1), 10)                 # shop window: dark interior
        c.fill(m_rect(x + 1, g - 6, xe - 1, g - 6), lit)                # lit ceiling strip
        c.fill(m_rect(x + 1, g - 5, xe - 1, g - 5) & (BAY < 8), lit)
        c.fill(m_rect(x + 1, g - 2, xe - 1, g - 2), 2)                  # counter
        for xx in range(x + 2, xe - 1, 4):
            c.px(xx, g - 4, col)
        aw = m_poly([(x, g - 8), (xe, g - 8), (xe + 1, g - 7), (x - 1, g - 7)])
        c.fill(aw, col)
        c.fill(aw & (((XX - x) % 3) == 0), 0)
        if sign and xe - x > 9 and top < g - 14:
            ink = cols[(r.randint(0, len(cols)) + 1) % len(cols)]
            c.glyph_sign(x + 1, top + 2, (xe - x - 2) // 4, 0, ink, seed + x, vertical=False)
            c.glow(m_rect(x, top + 1, xe, top + 7), ink, 2, 5, onto=(0, 1, 10, 2))
        x = xe + 2


def umbrella(c, x, y, rim, body=0):
    """Pedestrian with an umbrella, 5x7, rim-lit from the shops."""
    sprite(c, x - 3, y - 8, ["..kkk..", ".kkkkk.", "kkkkkkk", "...k...", "..kkk..", "..kkk..", "..k.k..", "..k.k.."],
           {'k': body})
    c.fill(m_rect(x - 1, y - 8, x + 1, y - 8) | m_rect(x - 2, y - 7, x + 2, y - 7), rim)
    c.px(x - 3, y - 6, rim)
    c.px(x + 3, y - 6, rim)
    c.glow(m_rect(x - 2, y - 8, x + 2, y - 7), rim, 2, 5, onto=(0, 1, 10))


def cable(c, x0, y0, x1, y1, sag, col, lamps=None):
    for x in range(min(x0, x1), max(x0, x1) + 1):
        t = (x - x0) / max(x1 - x0, 1)
        y = y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)
        c.px(x, round(y), col)
        if lamps and x % lamps[0] == lamps[1]:
            c.px(x, round(y) + 1, lamps[2])



# ================================================================== v3 additions
V2 = os.path.join(HERE, 'v2')


def load(name):
    im = Image.open(os.path.join(V2, name))
    return np.array(im), im.getpalette()[:48]


def lum_of(a, p):
    rgb = np.array(p).reshape(16, 3)[a]
    return float((0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).mean())


def street_streaks(c, src, G, y0, lights, dim, far, dark, seed, depth=20, ripple=1.0, reach=.85, breaks=8, dens=1.0):
    """Wet street below line G: per-column vertical reflection streaks of the lights above it (no mirrored
    glyphs). lights: colours that reflect; dim: colour -> mid-distance colour; far: colour -> far colour
    (12/13, which shimmer); dark: colour -> asphalt tone for the mirrored silhouettes."""
    col = np.zeros(W, int)
    stg = np.zeros(W)
    for x in range(W):
        acc = {}
        for d in range(1, depth + 1):
            y = G - d
            if y < 0:
                break
            v = int(src[y, x])
            if v in lights:
                acc[v] = acc.get(v, 0) + (1.25 - d / depth) * lights[v]
        if acc:
            v = max(acc, key=acc.get)
            col[x], stg[x] = v, min(acc[v] / 2.5, 1.0)
    n = H - G
    hc = np.array([hsh(x, 1, seed) / 255.0 for x in range(W)])
    cf = np.where(hc < .45, 0, .45 + .55 * hc)                   # some columns stay dark: streaks, not sheets
    for y in range(y0, H):
        k = y - G
        for x in range(W):
            wob = int(round(math.sin(y * 1.3 + seed + (x // 9) * .8) * ripple * (k / n)))
            sx = min(max(x + wob, 0), W - 1)
            v = col[sx]
            Lx = 1 + stg[sx] * cf[sx] * n * reach
            if k <= .6 * Lx:
                p = 1.0
            else:
                p = (Lx - k) / (.4 * Lx)
            # rain ripples: dark troughs between the dashes, and short horizontal gaps
            gap = ((k + hsh(x // 4, 2, seed)) % 3 == 0 and k > 2) or hsh(x, y, seed) < breaks + k
            if v and p > 0 and not gap and BAY[y & 3, x & 3] < 16 * min(p * dens, 1):
                c.px(x, y, v if k <= 1 else dim.get(v, v) if k <= 1 + Lx * .3 else far.get(v, dim.get(v, v)))
                continue
            m = int(src[min(max(G - k, 0), G), sx])            # dark mirrored silhouette
            t = dark.get(m, 0)
            if t and BAY[y & 3, x & 3] >= 6 + k // 2:
                t = 0
            c.px(x, y, t)
    # sheen lines (wet asphalt catching the sky) and a few puddle glints
    r = np.random.RandomState(seed)
    for _ in range(18):
        x, y = r.randint(0, W - 8), r.randint(G + 2, H)
        for i in range(r.randint(3, 8)):
            if c.get(x + i, y) == 0:
                c.px(x + i, y, (1, 10)[(i + y) % 2 if y > G + 6 else 1])


def splashes(c, n, G, seed, ring=13, drop=5):
    r = np.random.RandomState(seed)
    for _ in range(n):
        x, y = r.randint(2, W - 2), r.randint(G + 3, H - 1)
        if c.get(x, y) in (0, 1, 10):
            c.px(x - 1, y, ring)
            c.px(x + 1, y, ring)
            c.px(x, y - 1, drop)


# ------------------------------------------------------------------ scene02 v3: storm geisha
def bolt(c, x, y, ylim, seed, w=1, depth=0):
    r = np.random.RandomState(seed)
    m = np.zeros((H, W), bool)
    path = [(x, y)]
    while y < ylim:
        y += r.randint(3, 7)
        x += r.randint(-4, 5) + (2 if depth == 0 else (-3 if seed % 2 else 3))
        path.append((x, y))
        if depth < 1 and r.rand() < .3 and y > 6:
            m |= bolt(c, x, y, min(y + 18, ylim), seed * 3 + len(path), 1, depth + 1)
    m |= m_line(path, w)
    return m


def crisp(t, w=.3):
    """Narrow the dither band between ramp steps (cleaner shading on a small face)."""
    f = np.floor(t)
    return f + np.clip((t - f - .5 + w / 2) / w, 0, .999)


def blossom(c, x, y, petal, mid=3):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        c.px(x + dx, y + dy, petal)
    c.px(x, y, mid)


def scene2():
    c = Cv(2)
    G = 95
    CX = 92
    TT = 66                                                       # tower roof / projector deck
    sky(c, 0, G, G, 0.0, 2.5, .1)
    # storm clouds lit from inside by the bolt
    lm = bolt(c, 14, 0, 64, 5, 2)
    ld = dist(lm, 30)
    cm = np.zeros((H, W), bool)
    r = np.random.RandomState(12)
    for _ in range(26):
        cx, cy = r.randint(-10, W + 10), r.randint(-4, 34)
        cm |= m_ell(cx, cy, r.randint(8, 20), r.randint(4, 9))
    t = .5 + np.clip(1 - ld / 26, 0, 1) * 3.6 - np.clip((YY - 10) / 30, 0, 1) * .4
    c.ramp(cm, t, [0, 1, 10, 2, 9, 13, 5])
    c.fill(edge(cm, 0, 1) & (ld < 22), 13)
    c.fill(edge(cm, 0, 1) & (ld >= 22) & (BAY < 9), 2)
    # far skyline in the haze
    skyline(c, 41, 48, 64, G, 4, 8, body=2, lit=9, rimcol=None, wins=[13, 9], dens=50, wx=2, wy=3,
            side=.3, haze=(9, 5))
    c.glow(lm, 13, 4, 6, onto=(0, 1, 10, 2, 9))
    c.glow(lm, 5, 1, 9, onto=(0, 1, 10, 2, 9, 13))
    c.fill(lm, 5)                                                 # core in pale blue, not the cage white
    c.fill(lm & ~sh(lm, 1, 0) & (BAY < 6), 4)
    # mid skyline, left half
    nb = skyline(c, 43, 54, 66, G, 7, 12, body=1, lit=10, rimcol=None, wins=[13, 5, 3], dens=70, wx=3, wy=3,
                 ww=1, wh=1, side=.2)
    for x0, x1, top in nb:
        c.fill(m_rect(x0, top, x0, G) & (BAY < 8), 2)
        c.fill(m_rect(x0, top, x1, G) & (BAY < np.clip((YY - top) / 4.0, 0, 3)) & c.over((1, 10)), 2)  # mist
    # ---------------- megatower (right) with a lit facade
    TX0, TX1 = 66, 119
    tw = m_rect(TX0, TT, TX1, G) | m_poly([(TX0 + 3, TT), (TX0 + 7, TT - 3), (TX1 - 5, TT - 3), (TX1, TT)])
    l = (XX - TX0) / (TX1 - TX0)
    c.ramp(tw, 2.3 - l * 1.9, [0, 1, 10, 2, 9])
    c.fill(edge(tw, -1, 0) & (BAY < 12), 13)
    c.fill(edge(tw, 0, -1), 9)
    # ---------------- the hologram
    hair = m_ell(CX, 24, 16, 13) | m_ell(CX, 9, 10, 6.5) | m_ell(CX - 14, 29, 6, 9) | m_ell(CX + 14, 29, 6, 9)
    face = m_ell(CX, 33, 10, 12.5) & (YY >= 23)
    neck = m_rect(CX - 4, 43, CX + 4, 50) & ~face
    kim = m_poly([(CX - 30, TT - 2), (CX - 25, 56), (CX - 9, 48), (CX + 9, 48), (CX + 25, 56), (CX + 30, TT - 2)])
    kim &= YY <= TT - 3
    fig = hair | face | neck | kim
    # projector beams: soft fans from the three emitters on the roof
    em = [(CX - 20, TT - 4), (CX, TT - 4), (CX + 20, TT - 4)]
    for ex, ey in em:
        for k_ in range(-3, 4):
            tx_, ty_ = ex + k_ * 5 + (CX - ex) * .3, 18 + abs(k_) * 4
            bm = m_line([(ex, ey), (tx_, ty_)], 1) & ~fig
            c.fill(bm & (BAY < 5) & c.over((0, 1, 10, 2)), 9)
            c.fill(bm & (BAY < 2), 13)
    halo = dist(fig, 6)
    c.fill((halo > 1) & (halo <= 3) & (BAY < 4 - halo) & c.over((0, 1, 10, 2)), 9)
    # hair: lacquered black lobes (wings, crown, bun), each with its own shading, a combed sheen band
    # broken into strands, dark partings between lobes and neon edge light (cyan left, magenta right)
    lobes = ((CX - 14, 29, 6, 9, 1.0), (CX + 14, 29, 6, 9, 2.0), (CX, 24, 16, 13, 3.0), (CX, 19.5, 12.5, 5.2, 5.0), (CX, 9, 10, 6.5, 4.0))
    for lx, ly, rx, ry, sd in lobes:
        lm_ = m_ell(lx, ly, rx, ry)
        u = (XX + .5 - lx) / rx
        v = (YY + .5 - ly) / ry
        z = np.sqrt(np.clip(1 - u * u - v * v, 0, 1))
        lt = -u * .5 - v * .55 + z * .55                            # light from the upper left
        c.ramp(lm_, crisp(1.0 + lt * 1.9, .4), [0, 1, 10, 2, 9])
        phi = np.arctan2(u, v + 1.7)                                 # strands fan out from below the crown
        strand = .5 + .5 * np.sin(phi * (26 if rx > 12 else 18) + sd * 2.1 + np.sin(v * 3 + sd) * .6)
        vs = -.42 + .38 * u * u                                      # sheen follows the dome
        band = np.clip(1.35 - np.abs(v - vs) * ry / 2.0, 0, 1) * np.clip(1.25 - u * .6, 0, 1.5)
        sv = band * (.45 + .55 * strand)
        if sd < 3:                                                   # side loops: concentric strands, outer sheen
            sx_ = -1 if sd == 1 else 1
            rr_ = np.sqrt(u * u + v * v)
            strand = .5 + .5 * np.sin(rr_ * 19 + 1.3)
            cres = np.clip(1.2 - np.abs(rr_ - .66) / .2, 0, 1) * np.clip(u * sx_ * 1.4 + .9, 0, 1) *                 np.clip(1.1 - v * .5, 0, 1) * (1.15 if sx_ < 0 else .8)
            sv = cres * (.5 + .5 * strand)
        c.fill(lm_ & (sv > .15) & (BAY < 12) & c.over((0, 1)), 10)
        c.fill(lm_ & (sv > .28) & c.over((0, 1, 10)), 2)
        c.fill(lm_ & (sv > .45), 9)
        c.fill(lm_ & (sv > .66), 13)
        c.fill(lm_ & (sv > .9) & (u < .1), 5)
        c.fill(lm_ & (sv > 1.1) & (u < -.1), 11)
        c.fill(lm_ & (strand < .14) & (v > vs + .25) & c.over((10, 2)), 1)    # combed grooves below the sheen
        c.fill(lm_ & (strand < .14) & (v < vs - .22) & c.over((10, 2, 9)), 1)
        c.fill(edge(lm_, 0, 1) & (v > 0), 0)                          # parting line under the lobe
        c.fill(edge(lm_, 0, 1) & (v > 0) & (u < -.2) & (BAY < 8), 1)
        c.fill(edge(lm_, -1, 0) & (v < .6) & (BAY < 7), 7)         # neon edge light
        c.fill(edge(lm_, 1, 0) & (v < .7) & (v > -.6), 15)
    # loose side locks falling in front of the ears
    for sx in (-1, 1):
        lk = m_line([(CX + sx * 9, 26), (CX + sx * 11, 33), (CX + sx * 10, 42)], 2)
        c.fill(lk, 0)
        c.fill(lk & edge(lk, sx, 0), 2)
        c.fill(lk & edge(lk, sx, 0) & (YY < 34) & (BAY < 9), 13 if sx < 0 else 15)
    # face and neck: porcelain, lit from the upper left, shaded jaw, under-chin shadow
    fn = face | neck
    fd = np.hypot((XX + .5 - CX + 2.5) / 10, (YY + .5 - 31) / 13)
    tf = 4.3 - fd * 1.5 - np.clip((XX - CX) / 10.0, 0, 1) * .8 + neck * 1.2 - (neck & (YY < 45)) * 1.3
    c.ramp(fn, crisp(tf, .25), [9, 13, 5, 11, 4])
    c.fill(edge(face, 1, 0) & (YY > 26), 13)                     # jaw shadow on the right
    hl = YY < 22 + np.abs(XX + .5 - CX) * .45 + 1.5
    c.fill(face & hl, 1)                                          # parted hairline
    c.fill(edge(face & ~hl, 0, -1) & (YY < 27), 2)
    for dx in (-5, 5):
        s_ = 1 if dx > 0 else -1
        c.fill(m_line([(CX + dx - 2 * s_, 32), (CX + dx + 2 * s_, 31)], 1), 0)        # closed lid
        c.px(CX + dx + 3 * s_, 30, 6)                                                  # red liner flick
        c.px(CX + dx + 3 * s_, 31, 6)
        c.px(CX + dx - 2 * s_, 33, 0)                                                  # lashes
        c.px(CX + dx, 33, 13)
        c.fill(m_line([(CX + dx - 2, 28), (CX + dx + 2, 28)], 1), 2)                  # brows
        c.px(CX + dx + 2 * s_, 27, 2)
        c.fill(m_ell(CX + dx, 36, 2.5, 1.3) & (BAY < 6), 15)                          # blush
    c.px(CX + 1, 35, 13)                                                               # nose
    c.px(CX + 1, 36, 13)
    c.fill(m_rect(CX - 2, 40, CX + 1, 40), 6)                                          # lips
    c.fill(m_rect(CX - 1, 41, CX, 41), 6)
    c.px(CX - 1, 40, 4)
    c.px(CX, 39, 9)
    # kanzashi: lacquer comb on the bun, two long pins with tsumami flowers and bead tassels, a big flower spray
    comb = m_ell(CX, 13, 9, 3) & ~m_ell(CX, 14, 8, 2.2) & (YY <= 13)
    c.fill(comb, 3)
    c.fill(comb & (XX > CX + 2) & (BAY < 8), 12)
    for x in range(CX - 7, CX + 8, 2):
        c.px(x, 14, 0)
    for x0, y0, x1, y1 in ((CX + 6, 8, CX + 19, 1), (CX - 6, 8, CX - 18, 2)):
        c.fill(m_line([(x0, y0), (x1, y1)], 2), 3)
        c.fill(m_line([(x0, y0 + 1), (x1, y1 + 1)], 1) & ~m_line([(x0, y0 - 1), (x1, y1 - 1)], 1), 12)
        sx = 1 if x1 > CX else -1
        c.fill(m_ell(x1, y1 + 1, 2.6, 2.2), 15)                     # pin-head flower
        c.fill(m_ell(x1 - .8, y1 + .3, 1.2, 1.0), 5)
        c.px(x1, y1 + 1, 4)
        for j in range(7):                                          # dangling bead chain, gold in pairs
            c.px(x1 + sx * 3, y1 + 3 + j, (15, 3, 3, 12, 3, 3, 15)[j])
        c.px(x1 + sx * 3, y1 + 10, 4)
        c.px(x1 + sx * 3 + sx, y1 + 9, 12)
    spray = ((CX - 12, 15, 15), (CX - 9, 18, 12), (CX - 14, 19, 5), (CX - 11, 21, 15))
    for fx, fy, pc in spray:                                        # tsumami flower cluster on the left
        c.fill(m_ell(fx, fy, 2.2, 2.0), pc)
        c.fill(edge(m_ell(fx, fy, 2.2, 2.0), 0, 1), 0 if pc != 5 else 13)
        c.px(fx - 1, fy - 1, 4 if pc == 5 else 5)
        c.px(fx, fy, 3)
        c.px(fx + 1, fy, 3)
    for fx, fy, pc in ((CX + 9, 12, 15), (CX + 12, 15, 12)):
        blossom(c, fx, fy, pc, 5)
    # kimono: rose silk with folds, white/red layered collar, gold obi, sakura and a wave hem
    fold = np.sin((XX - CX) * .32 + YY * .1) * .6 + np.sin((XX - CX) * .9 - YY * .25) * .15
    c.fill(kim, 12)
    top = kim & ~sh(kim, 0, -3)                                     # light on the shoulders from above-left
    c.fill(top & (XX < CX + 6), 15)
    c.fill(top & (XX >= CX + 6) & (BAY < 8), 15)
    c.fill(kim & (XX > CX + 12) & (BAY < 5), 10)                    # right side turns away
    c.fill(kim & (np.abs(XX - CX) > 25) & (BAY < 9), 10)
    for x0, y0, x1, y1 in ((CX - 18, 54, CX - 22, 63), (CX - 11, 52, CX - 13, 59), (CX + 17, 53, CX + 21, 63),
                           (CX + 11, 52, CX + 12, 59)):            # drape folds: dark crease + lit ridge
        c.fill(m_line([(x0, y0), (x1, y1)], 1) & kim, 10)
        c.fill(m_line([(x0 - 1, y0 + 1), (x1 - 1, y1)], 1) & kim & (BAY < 10), 15)
    c.fill(edge(kim, 0, -1) & (BAY < 12), 15)                     # shoulder rim light
    for x0, y0 in ((CX - 20, 58), (CX + 17, 57), (CX - 13, 54), (CX + 23, 61), (CX - 26, 62)):
        blossom(c, x0, y0, 5, 3)
    for x in range(CX - 28, min(CX + 29, W)):                     # wave hem (seigaiha line)
        y = TT - 6 + int(round(math.sin(x * .9) * .8))
        if kim[min(y, H - 1), x] and x % 4 != 0:
            c.px(x, y, 13)
    obi = kim & (YY >= 56) & (YY <= 59) & (np.abs(XX - CX) < 15)
    c.fill(obi, 3)
    c.fill(obi & (YY == 57), 12)
    c.fill(obi & (YY == 59) & (BAY < 10), 12)
    c.fill(m_rect(CX - 1, 56, CX + 1, 59), 6)
    c.px(CX, 57, 4)
    vn = m_poly([(CX - 7, 47), (CX + 7, 47), (CX + 1, 57), (CX, 57)])
    c.fill(vn, 5)
    c.fill(vn & (XX > CX + 1) & (BAY < 8), 13)
    c.fill(m_line([(CX - 9, 48), (CX + 1, 59)], 3) & kim & (YY < 56), 4)            # white over-collar
    c.fill(m_line([(CX + 9, 48), (CX - 1, 58)], 3) & kim & (YY < 56), 11)
    c.fill(m_line([(CX - 6, 48), (CX + 1, 56)], 1) & kim, 6)                        # red under-collar
    c.fill(m_line([(CX + 6, 48), (CX + 1, 56)], 1) & kim, 6)
    c.fill(m_line([(CX + 9, 48), (CX - 1, 58)], 1) & kim & (YY < 56), 13)
    # hologram treatment: cyan rim with a broken flicker, magenta ghost, scanlines, glitch slices
    rim = dil(fig) & ~fig
    flick = hsh(YY // 2, 0, 5) < 210
    c.fill(rim & flick, 7)
    c.fill(rim & ~flick & (BAY < 8), 13)
    gh = sh(edge(fig, -1, 0), 2, 0) & ~fig & ~rim
    c.fill(gh & (BAY < 6) & (YY % 3 == 1), 15)
    figp = fig | rim
    dk = {11: 5, 4: 11, 5: 13, 13: 9, 15: 12, 12: 6, 3: 12, 9: 2, 2: 10, 10: 1, 1: 0, 6: 15}
    for y in range(0, TT - 2):
        if y % 4 == 2:
            for x in range(CX - 34, W):
                if figp[y, x]:
                    v = c.get(x, y)
                    c.px(x, y, dk.get(v, v))
    up = {9: 13, 13: 5, 2: 9, 1: 10, 0: 1, 12: 15, 10: 2}
    for x in range(CX - 34, W):                                    # bright refresh band
        if figp[37, x]:
            c.px(x, 37, up.get(c.get(x, 37), c.get(x, 37)))
    for y0, sx in ((24, 2), (25, 2), (51, -3), (52, -3)):
        row = c.a[y0, CX - 31:W - 3].copy()
        c.a[y0, CX - 31 + sx:W - 3 + sx] = row
        c.px(CX - 31 + min(sx, 0) - 1, y0, 7)
        c.px(CX - 31 + min(sx, 0) - 2, y0, 15)
    c.fill(kim & (YY > TT - 6) & (BAY < (YY - (TT - 6)) * 4), 10)    # dissolve into the beams
    # tower facade below the deck
    for y in range(TT + 3, G - 12, 3):                            # floor slabs + window bands
        c.fill(m_rect(TX0 + 1, y + 2, TX1, y + 2), 0)
        fl = hsh(y, 3, 19)
        for x in range(TX0 + 3, TX1 - 8, 3):
            h = hsh(x // 6, y, 9)
            if fl < 170 and h < 150:
                c.fill(m_rect(x, y, x + 1, y), 9 if h > 60 else 13 if x < 80 else 3)
                if h < 25:
                    c.px(x, y, 5)
            else:
                c.fill(m_rect(x, y, x + 1, y), 1)
    c.glyph_sign(TX1 - 6, TT + 4, 4, 14, 15, 21)
    c.glow(m_rect(TX1 - 7, TT + 3, TX1 - 1, TT + 21), 15, 2, 6, onto=(0, 1, 10, 2))
    # projector deck on the tower roof
    for ex, ey in em:
        c.fill(m_rect(ex - 3, ey, ex + 3, ey + 2), 0)
        c.fill(m_rect(ex - 2, ey, ex + 2, ey), 14)
        c.px(ex, ey - 1, 4)
        c.px(ex - 1, ey - 1, 7)
        c.px(ex + 1, ey - 1, 7)
    # ---------------- elevated rail with a train
    RY = 73
    c.fill(m_rect(0, RY, W - 1, RY + 2), 0)
    c.fill(m_rect(0, RY, W - 1, RY), 9)
    c.fill(m_rect(0, RY + 2, W - 1, RY + 2) & (BAY < 6), 2)
    for x in range(0, W, 3):
        c.px(x, RY + 1, 1)
    tr = m_rect(10, RY - 7, 58, RY - 1) | m_poly([(58, RY - 7), (63, RY - 3), (63, RY - 1), (58, RY - 1)])
    c.fill(tr, 1)
    c.fill(m_rect(10, RY - 7, 60, RY - 7), 13)
    c.fill(m_rect(10, RY - 6, 60, RY - 6) & (BAY < 8), 2)
    for x in range(12, 57, 4):
        wk = hsh(x, 1, 6) % 6
        c.fill(m_rect(x, RY - 5, x + 2, RY - 4), (3, 3, 5, 10, 12, 3)[wk])
        if wk in (0, 1, 5):
            c.px(x + 2, RY - 4, 15)
        if wk == 3:
            c.px(x + 1, RY - 4, 0)
    c.fill(m_rect(10, RY - 2, 63, RY - 2), 13)
    c.fill(m_rect(10, RY - 2, 63, RY - 2) & (BAY < 4), 7)
    c.px(62, RY - 4, 4)
    c.glow(m_rect(10, RY - 2, 63, RY - 2), 13, 2, 4, onto=(0, 1, 10, 2))
    c.glow(m_rect(62, RY - 4, 62, RY - 4), 11, 3, 8, onto=(0, 1, 10, 2))
    # ---------------- mid layer under the rail: deep facades sinking into rain mist
    FY = RY + 3
    for x0, x1, base, seed in ((0, 17, 1, 3), (18, 39, 0, 4), (40, 65, 1, 5), (66, 90, 0, 6), (91, 119, 1, 7)):
        c.fill(m_rect(x0, FY, x1, G), base)
        c.fill(m_rect(x0, FY, x0, G) & (BAY < 10), 2)
        for y in range(FY + 2, G - 11, 4):
            for x in range(x0 + 2, x1 - 2, 4):
                h = hsh(x, y, seed)
                if h < 70:
                    c.fill(m_rect(x, y, x + 1, y), (13, 9, 12, 3, 9)[h % 5])
    # signs at different heights and sizes, kept off the middle (the hologram owns it)
    c.glyph_sign(4, FY + 1, 3, 14, 12, 50)
    c.glow(m_rect(3, FY, 9, FY + 14), 12, 3, 6, onto=(0, 1, 10, 2))
    c.glyph_sign(26, FY + 3, 2, 14, 8, 51, vertical=False)
    c.glow(m_rect(25, FY + 2, 35, FY + 8), 8, 2, 4, onto=(0, 1, 10, 2))
    c.glyph_sign(110, FY + 1, 2, 14, 3, 53)
    c.glow(m_rect(109, FY, 115, FY + 10), 3, 3, 6, onto=(0, 1, 10, 2))
    cable(c, 40, FY + 1, 66, FY + 2, 3, 0, lamps=(5, 2, 6))         # lantern string over the noodle stand
    for lx in range(42, 66, 5):
        y = round(FY + 1 + (FY + 2 - FY - 1) * (lx - 40) / 26 + 3 * 4 * ((lx - 40) / 26) * (1 - (lx - 40) / 26))
        c.fill(m_rect(lx, y + 1, lx + 1, y + 2), 6)
        c.px(lx, y + 1, 15)
        c.glow(m_rect(lx, y + 1, lx + 1, y + 2), 6, 1, 6, onto=(0, 1, 10, 2))
    # mist: rain haze thickening toward the street, plus a drifting band
    ft = np.clip((YY - FY) / (G - FY), 0, 1)
    band_ = np.exp(-((YY - (FY + 6 + np.sin(XX * .08) * 1.5)) / 1.8) ** 2)
    zone = (YY >= FY) & (YY <= G)
    c.fill(zone & c.over((0,)) & (BAY < 2 + 7 * ft + 6 * band_), 1)
    c.fill(zone & c.over((1,)) & (BAY < 1 + 5 * ft + 6 * band_), 10)
    c.fill(zone & c.over((10,)) & (BAY < 4 * ft + 5 * band_), 2)
    # street level: two shops, a noodle stand, a dark plaza with lamps under the hologram
    storefronts(c, 0, 22, G - 10, G, 11, [15, 12, 7], sign=False)
    storefronts(c, 98, 119, G - 10, G, 13, [12, 7, 15], sign=False)
    NX0, NX1 = 40, 64                                              # noodle stand: noren, warm counter, steam
    c.fill(m_rect(NX0, G - 9, NX1, G), 0)
    c.fill(m_rect(NX0 + 1, G - 6, NX1 - 1, G - 3), 5)                 # warm lit interior
    c.fill(m_rect(NX0 + 1, G - 4, NX1 - 1, G - 3) & (BAY < 9), 3)
    c.fill(m_rect(NX0 + 1, G - 2, NX1 - 1, G - 2), 15)                # counter edge
    c.fill(m_rect(NX0 - 1, G - 9, NX1 + 1, G - 8), 6)                 # red awning, scalloped
    c.fill(m_rect(NX0 - 1, G - 9, NX1 + 1, G - 9) & (BAY < 8), 15)
    for x in range(NX0 - 1, NX1 + 2, 3):
        c.px(x, G - 7, 6)
    for x in range(NX0 + 2, NX1 - 1, 5):                              # noren curtains
        c.fill(m_rect(x, G - 6, x + 3, G - 5), 12)
        c.fill(m_rect(x + 1, G - 6, x + 1, G - 5), 15)
    for x in range(NX0 + 3, NX1 - 2, 6):                              # customers on stools, backs to us
        c.fill(m_rect(x, G - 5, x + 2, G - 2), 0)
        c.fill(m_rect(x, G - 6, x + 1, G - 6), 0)
        c.px(x + 1, G - 1, 0)
    c.glow(m_rect(NX0, G - 6, NX1, G - 2), 15, 2, 4, onto=(0, 1, 10, 2))
    for k_ in range(14):                                           # steam
        x = NX0 + 6 + (k_ * 7) % 14 + int(math.sin(k_) * 2)
        y = G - 11 - k_ // 2
        if c.get(x, y) in (0, 1, 10, 2):
            c.px(x, y, 2 if k_ > 6 else 9)
    for lx in (72, 86):                                            # street lamps over the dark plaza
        c.fill(m_rect(lx, G - 12, lx, G), 0)
        c.px(lx + 1, G - 12, 0)
        c.fill(m_rect(lx + 1, G - 11, lx + 2, G - 11), 5)
        c.glow(m_rect(lx + 1, G - 11, lx + 2, G - 11), 13, 4, 8, onto=(0, 1, 10, 2))
        cone = (YY > G - 11) & (YY <= G) & (np.abs(XX - lx - 1.5) < (YY - G + 12) * .45)
        c.fill(cone & c.over((0, 1, 10)) & (BAY < 5 - (YY - G + 11) * .3), 2)
    for vx, vc in ((26, 7), (30, 8)):                             # vending machines
        c.fill(m_rect(vx, G - 8, vx + 2, G - 1), 0)
        c.fill(m_rect(vx, G - 8, vx + 2, G - 6), vc)
        c.fill(m_rect(vx, G - 5, vx + 2, G - 5), 14)
        c.fill(m_rect(vx + 1, G - 3, vx + 1, G - 2), 3)
        c.glow(m_rect(vx, G - 8, vx + 2, G - 6), vc, 2, 6, onto=(0, 1, 10))
    for x, rim in ((11, 7), (79, 13), (108, 15)):
        umbrella(c, x, G, rim)
    car(c, 42, 34, 1, 14, 6)
    car(c, 30, 57, 1, 5, 6, trail=8)
    for x in range(W):                                             # kerb
        c.px(x, G, 9 if (x // 3) % 2 else 2)
    # ---------------- wet street: light streaks broken by ripples, ground mist, the hologram's reflection
    # asphalt: dark, a faint sheen of the mist near the kerb, puddle sheen lines
    k_ = np.clip((YY - G) / (H - G), 0, 1)
    c.ramp(YY > G, 1.6 - k_ * 1.9, [0, 1, 10])
    for y in range(G + 3, H, 3):
        c.fill((YY == y) & (np.sin(XX * .23 + y * 1.7) > .55) & c.over((0, 1)), 10)
    # reflections: one coherent streak per light source, broken by ripples, fading toward us
    refl = ((0, 21, 15, 12, 16), (4, 8, 12, 12, 16), (26, 32, 7, 13, 11), (41, 63, 3, 15, 17),
            (42, 63, 12, 12, 9), (72, 74, 5, 13, 12), (86, 88, 5, 13, 12), (99, 118, 12, 7, 16),
            (110, 114, 3, 12, 16), (CX - 18, CX + 18, 12, 15, 10))
    for i, (x0, x1, core, dimc, L) in enumerate(refl):
        for x in range(max(x0, 0), min(x1, W - 1) + 1):
            cf = .6 + .5 * (hsh(x, i, 31) / 255.0)
            if hsh(x, i, 37) < 50:
                continue
            for k in range(1, L + 1):
                y = G + k
                if y >= H:
                    break
                xx = x + int(round(math.sin(k * 1.3 + x * .4 + i) * k / 9))
                if not 0 <= xx < W or c.get(xx, y) not in (0, 1, 10):
                    continue
                if (k + hsh(x // 3, i, 41)) % 3 == 0 and k > 1:
                    continue                                            # ripple trough
                p_ = (1 - k / (L + 1)) ** .8 * cf
                if BAY[y & 3, xx & 3] < 16 * p_:
                    c.px(xx, y, core if k <= max(2, L * .3) else dimc)
                elif BAY[y & 3, xx & 3] < 16 * p_ + 3:
                    c.px(xx, y, 2)
    for y in range(G + 1, H):                                      # the lightning's reflection
        x = 10 + int(math.sin(y * 1.1) * 1.4) + (y - G) // 5
        if hsh(x, y, 2) > 60:
            c.px(x, y, 13 if y < G + 6 else 9)
    gm = np.exp(-((YY - G - 2.5) / 2.2) ** 2)                      # ground mist hugging the kerb
    c.fill((YY > G) & c.over((0, 1)) & (BAY < 7 * gm), 10)
    c.fill((YY > G) & c.over((10,)) & (BAY < 4 * gm), 2)
    # pedestrians with umbrellas in the foreground, neon on the canopy edges, dark reflections
    for x, y, rl, rr_ in ((13, 114, 7, 12), (51, 116, 15, 13), (108, 115, 12, 7)):
        dome = m_ell(x, y - 13, 7.5, 4) & (YY <= y - 13)
        body = m_rect(x - 2, y - 12, x + 2, y) | (m_rect(x, y - 13, x, y - 13))
        c.fill(dome | body, 0)
        lit = dome & (YY >= y - 15) & (BAY < 6 + (XX - x) * (-1.2 if rl in (7, 12) else 1.2))
        c.fill(lit, 1)
        top = edge(dome, 0, -1)
        c.fill(top & (XX < x), rl)
        c.fill(top & (XX >= x) & (BAY < 11), rr_)
        c.fill(sh(top, 0, -1) & dome & ~top & (BAY < 7), rl if True else 0)
        c.fill(edge(dome, -1, 0) & (XX < x), rl)
        c.fill(edge(dome, 1, 0) & (XX > x), rr_)
        c.fill(m_rect(x - 7, y - 13, x + 7, y - 13) & (np.abs(XX - x) % 3 == 1), 1)   # rib tips
        c.fill(m_rect(x - 2, y - 12, x - 2, y) & (BAY < 9), 10)     # coat edge catching the shop light
        c.fill(m_rect(x + 2, y - 12, x + 2, y) & (BAY < 5), 2)
        c.glow(top, rl, 2, 4, onto=(0, 1, 10))
    rain(c, 303, 24, cols=(2, 9), hi=(9, 13), slant=2, ln=4)
    splashes(c, 10, G, 44)
    return c


def lone_gold(c, to=12):
    """Gold (3) with no gold 8-neighbour -> rose: the game's diagonal gold sheen owns lone gold pixels."""
    g = c.a == 3
    nb = np.zeros_like(g)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx or dy:
                nb |= sh(g, dx, dy)
    m = g & ~nb
    c.a[m] = to
    return int(m.sum())


def main():
    old = Image.open(os.path.join(HERE, 'v3', 'scene02.png'))
    a2, p2 = np.array(old), old.getpalette()[:48]
    c2 = scene2()
    n = lone_gold(c2)
    im = Image.fromarray(c2.a.astype(np.uint8), 'P')
    im.putpalette(list(p2))
    im.save(os.path.join(HERE, 'scene02.png'))
    print('lone gold fixed %d; luminance %.1f -> %.1f' % (n, lum_of(a2, p2), lum_of(c2.a, p2)))

    def rgb(a, p):
        return Image.fromarray(np.array(p, np.uint8).reshape(16, 3)[a]).resize((480, 448), Image.Resampling.NEAREST)
    pv = Image.new('RGB', (970, 1364), (30, 30, 30))
    pv.paste(rgb(c2.a, p2), (0, 0))
    pv.paste(rgb(a2, p2), (490, 0))
    for i, k in enumerate((0, 4, 6)):
        s_ = Image.open(os.path.join(HERE, 'scene%02d.png' % k))
        pv.paste(rgb(np.array(s_), s_.getpalette()[:48]), ((i + 2) % 2 * 490, (i + 2) // 2 * 458))
    pv.save(os.path.join(HERE, 'preview_s02v4.png'))


if __name__ == '__main__':
    main()
