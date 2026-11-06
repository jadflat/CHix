"""CHix scenes 00..03 (v2): rainy cyberpunk hero pictures, 120x112 indexed, 16 colours.
Run: python paint_a.py   (deterministic; writes scene00..03.png, preview_a2.png, crops_a2.png)
v1 (flat skylines) is kept in v1/.

00 dragon tower   - a colossal neon dragon coiled round a megatower, full moon behind
01 harbour duel   - a giant mecha wading through the bay, reactor blazing, gunships, ringed planet
02 storm geisha   - lightning forks over a megatower wearing a giant holographic geisha ad
03 crash site     - a starship burning in the old city under a blood moon, smoke and sparks
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


# ------------------------------------------------------------------ 00 dragon tower
DRAGON_HEAD = [   # facing left. K outline, D/m/M scales dark->light, h lit, c neon, w/W hi, r eye, g gold, p magenta, o mouth glow
    "......................pp....p.......",
    ".....................pKp...pK.......",
    "....................pKMp..pKM.......",
    "...................pKMK..pKMK.......",
    "..........KKKKK...KMMK.pKMMK........",
    ".......KKKmmmmmKKKMMMKKKMMK.........",
    ".....KKmmMMMMMMMMmMMMMMMMmKK........",
    "....KmMMMMMhhhhMMMMMMMMMMmmmKK......",
    "...KmMMhhhhhwwhMMKKKKMMMMmmmmmKK....",
    "..KmMMMMMMMMMMMMKrrrgKMMMmmmmmmmK...",
    ".KmMMMMMMMMMMMMMKrrgwKMMmmmmmmDDDK..",
    "KhMMMMMMMMMMMMMMMKKKKMMmmmmmmDDDDDK.",
    "KccccccccccccMMMMMMMMMmmmmmmDDDDDDK.",
    ".KWKWKWKWKWKcccmmmmmmmmmDDDDDDDDDK..",
    "..KoooooooooKKccmmmmmDDDDDDDDDDK....",
    "...KooooooooooKcDDDDDDDDDDDDK.......",
    "....KoooooooooKcDDDDDDDDDK..........",
    ".....KWKWKWKWKccDDDDDDK.............",
    "......KcccccccccDDDDK...............",
    ".......KKKKKKKKKKKK.................",
]
DKEY = {'K': 0, 'd': 1, 'D': 2, 'm': 9, 'M': 13, 'h': 5, 'c': 7, 'w': 11, 'W': 4, 'r': 6, 'g': 3, 'p': 15, 'o': 12}


def tube(c, pts, ramp, neon, belly, spine, out=0, spines_every=8):
    """Shaded serpent tube along pts [(x,y,r)], lit from above; outline, neon dorsal line, belly line."""
    m = np.zeros((H, W), bool)
    for x, y, r in pts:
        m |= m_ell(x, y, r * 1.08, r)
    # local shading from the nearest centre point
    t = np.zeros((H, W))
    for x, y, r in pts:
        mm = m_ell(x, y, r * 1.08, r)
        t[mm] = (((YY + .5 - y) * -.9 + (XX + .5 - x) * -.3) / r)[mm]
    c.fill(dil(m) & ~m & c.over((9, 13, 5, 11, 4)), out)          # dark outline only where it crosses bright
    c.ramp(m, 1.6 + t * 1.3, ramp)
    for i, (x, y, r) in enumerate(pts):                           # scales: dark chevrons
        if i % 4 == 0 and r > 2.2:
            for k in (-1, 0, 1):
                if m[int(min(max(y + abs(k) * .7, 0), H - 1)), int(min(max(x + k, 0), W - 1))]:
                    c.px(x + k, y + abs(k) * .7, ramp[1])
    c.fill(edge(m, 0, -1), neon)                                  # neon dorsal rim
    c.fill(edge(m, 0, -1) & sh(edge(m, 0, -1), 0, 0) & (BAY < 5), 11)
    c.fill(edge(m, 0, 1) & (BAY < 10), belly)                     # under-glow from the street
    for i, (x, y, r) in enumerate(pts):
        if i % spines_every == 0 and r > 1.8:
            c.px(x, y - r - 1, spine)
            c.px(x + 1, y - r - 2, spine)
    return m


def scene0():
    c = Cv(0)
    G = 94
    sky(c, 0, G, G, 0.0, 3.6, .12)
    stars(c, 30, 3, 40)
    MX, MY, MR = 70, 28, 20
    moon(c, MX, MY, MR, [9, 13, 5, 11], halo=(2, 10))
    # thin cloud bands across the moon
    for cx, cy, rx in ((50, 40, 30), (96, 22, 20), (74, 46, 16), (18, 30, 18)):
        m = m_ell(cx, cy, rx, 1.6) | m_ell(cx + rx * .4, cy - 1, rx * .5, 1.4)
        c.fill(m & c.over((9, 13, 5, 11)), 2)
        c.fill(m & c.over((0, 1, 10)), 10)
        c.fill(edge(m, 0, -1) & m_ell(MX, MY, MR + 3) & (BAY < 10), 13)
    # far skyline hazed into the city glow
    skyline(c, 11, 56, 72, G, 4, 9, body=2, lit=9, rimcol=None, wins=[9, 13], dens=50, wx=2, wy=3,
            side=.25, haze=(9, 9))
    TX = 64

    def hw(y):
        return 2 if y < 12 else 4 if y < 22 else 6 if y < 38 else 8 if y < 56 else 10 if y < 74 else 12

    tm = np.zeros((H, W), bool)
    for y in range(10, G + 1):
        tm[y, max(TX - hw(y), 0):TX + hw(y) + 1] = True
    # dragon: 1.5 turns round the tower, tail low, neck rising to the head at top left
    back, front = [], []
    N = 160
    for i in range(N):
        s = i / (N - 1)
        y = 86 - s * 50
        ph = s * 1.55 * 2 * math.pi - 1.2
        rad = hw(y) + 9 - 2 * s
        r = 1.4 + 3.6 * min(s * 1.6, 1)
        p = (TX + math.sin(ph) * rad, y + math.cos(ph) * 4.0, r)
        (front if math.cos(ph) >= 0 else back).append(p)
    tube(c, back, [0, 1, 10, 2, 9], 14, 1, 2, out=0)
    # tower
    l = (XX - TX) / 10.0
    c.ramp(tm, 2.0 - l * 1.5 - (YY > 70) * .3, [0, 1, 10, 2, 9])
    c.fill(edge(tm, -1, 0) & (YY > 11), 13)
    c.fill(edge(tm, 1, 0) & (YY > 11) & (BAY < 8), 15)
    for y in range(14, G - 1):                     # window columns: lit floors in bands
        if y in (22, 38, 56, 74) or y % 3 == 0:
            continue
        for x in range(TX - hw(y) + 2, TX + hw(y) - 1, 2):
            h = hsh(x, y // 3, 77)
            if h < 120 + (y > 60) * 40:
                c.px(x, y, 5 if x < TX - 2 else 3 if h < 60 else 12)
    for y in (12, 22, 38, 56, 74):                  # setback ledges with neon trim
        w2 = hw(y) + 1
        c.fill(m_rect(TX - w2, y, TX + w2, y + 1), 0)
        c.fill(m_rect(TX - w2, y, TX + w2, y), 7 if y != 38 else 15)
        c.glow(m_rect(TX - w2, y, TX + w2, y), 7 if y != 38 else 15, 3, 7, onto=(0, 1, 10, 2))
        for x in (TX - w2, TX + w2):
            c.fill(m_rect(x, y - 3, x, y - 1), 0)
            c.px(x, y - 4, 6)
    c.glyph_sign(TX - 2, 41, 3, 0, 15, 9)
    c.fill(m_rect(TX - 1, 0, TX, 11), 10)
    c.fill(m_rect(TX - 1, 0, TX - 1, 11), 13)
    for y in (4, 7, 10):
        c.fill(m_rect(TX - 3, y, TX + 2, y), 10)
    c.px(TX, 1, 6)
    c.glow(m_rect(TX, 1, TX, 1), 6, 3, 9, onto=(0, 1, 10, 2, 9, 13, 11, 5))
    # front coil and neck
    hx, hy = 6, 8
    neck = []
    sx, sy = front[-1][0], front[-1][1]
    for i in range(40):
        t = i / 39
        x = sx + (hx + 30 - sx) * t + math.sin(t * math.pi) * -4
        y = sy + (hy + 11 - sy) * t - math.sin(t * math.pi) * 8
        neck.append((x, y, 5.0 - .4 * t))
    tube(c, front + neck, [1, 10, 2, 9, 13, 5], 7, 15, 15, out=0)
    # mane flames along the neck
    for i, (x, y, r) in enumerate(neck[2::4]):
        for k in range(3):
            c.px(x + 1 + k, y - r - 1 - k, (15, 15, 12)[k])
    sprite(c, hx, hy, DRAGON_HEAD, DKEY)
    # eye glow
    c.glow(m_rect(hx + 17, hy + 9, hx + 19, hy + 10), 6, 2, 9, onto=(0, 1, 10, 2, 9, 13))
    # fire breath from the open jaw (rows 14-16), roaring down-left out of frame
    fire = np.zeros((H, W), bool)
    for i in range(14):
        fire |= m_ell(hx + 4 - i * 1.0, hy + 15 + i * .9, 1.6 + i * .3, 1.2 + i * .2)
    fire &= ~m_rect(hx + 5, 0, W, H)
    t = 3.8 - np.hypot(XX - hx - 3, YY - hy - 15) / 4.5
    c.ramp(fire, t, [6, 12, 3, 4])
    c.glow(fire, 12, 4, 8, onto=(0, 1, 10, 2, 9))
    c.glow(fire, 6, 6, 4, onto=(0, 1, 10, 2))
    # whiskers trailing back
    for i in range(16):
        c.px(hx + 2 + i, hy + 20 + int(math.sin(i * .5) * 1.5) + i // 6, 3)
    # mid skyline: dark blocks, structured window floors, signs
    nb = skyline(c, 22, 66, 82, G, 8, 15, body=1, lit=10, rimcol=None, wins=[3, 12, 5, 13], dens=80, wx=3,
                 wy=4, ww=2, wh=2, side=.2)
    for i, (x0, x1, top) in enumerate(nb):
        c.fill(m_rect(x0, top, x0, G) & (BAY < 9), 2)
        if (x1 - x0) > 8 and abs((x0 + x1) / 2 - TX) > 12 and i % 2 == 1:
            ink = (15, 7, 12, 8)[i % 4]
            c.glyph_sign(x1 - 5, top + 4, 3, 14, ink, i + 3)
            c.glow(m_rect(x1 - 6, top + 3, x1, top + 17), ink, 2, 6, onto=(0, 1, 10))
    # foreground silhouettes: a pagoda roof left, a pole and wires right
    roof = m_poly([(-2, 78), (6, 74), (20, 74), (28, 79), (24, 79), (22, 81), (-2, 81)])
    c.fill(roof, 0)
    c.fill(edge(roof, 0, -1), 2)
    c.fill(m_rect(0, 81, 20, G), 0)
    for x in range(3, 20, 5):
        c.fill(m_rect(x, 84, x + 2, 88), 12)
        c.px(x + 1, 84, 3)
    c.glow(m_rect(3, 84, 19, 88) & (BAY < 16), 12, 2, 6, onto=(0, 1, 10))
    c.fill(m_rect(108, 50, 109, G), 0)
    c.fill(m_rect(104, 54, 113, 55), 0)
    cable(c, 108, 54, 121, 60, 2, 0)
    cable(c, 104, 55, 70, 72, 6, 0)
    c.px(109, 49, 6)
    storefronts(c, 30, 104, G - 15, G, 5, [15, 7, 12, 8])
    for x, rim in ((40, 15), (58, 7), (63, 12), (86, 7), (99, 15)):
        umbrella(c, x, G, rim)
    car(c, 96, 52, -1, 14, 6)
    car(c, 30, 62, 1, 14, 15)
    car(c, 104, 74, -1, 5, 6, trail=8)
    # street
    for x in range(W):
        c.px(x, G, 2 if (x // 4) % 3 else 9)
    reflect(c, G, dark={13: 1, 9: 1, 2: 1, 14: 1, 10: 0, 5: 1}, ripple=1.0, fade=8, wet=(10, 14))
    for x in range(6, W, 18):
        c.fill(m_rect(x, H - 4, x + 8, H - 4), 14)
    rain(c, 101, 46, cols=(2, 14), hi=(13, 5))
    return c


# ------------------------------------------------------------------ 01 harbour duel
def part(c, pts, t0, ramp, k=2.8, lx=-1.0, ly=-.7, rim=None, rimdir=(1, 0), out=0):
    """Armour plate: polygon shaded by a linear light across its box, dark outline, optional rim."""
    m = m_poly(pts)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    sz = max(max(xs) - min(xs), max(ys) - min(ys), 1) / 2
    t = t0 + (((XX + .5 - cx) * lx + (YY + .5 - cy) * ly) / sz) * k * .5
    if out is not None:
        c.fill(dil(m) & ~m, out)
    c.ramp(m, t, ramp)
    if out is not None:
        c.fill(edge(m, 1, 0) | edge(m, 0, 1), out)
    c.fill(edge(m, -1, 0) & edge(m, 0, -1) | (edge(m, 0, -1) & (BAY < 10)), ramp[-1])
    if rim is not None:
        c.fill(edge(m, *rimdir) & (BAY < 12), rim)
    return m


def reflect_rows(c, src, g, y0, y1, bright=LIGHT, dark=None, ripple=1.0, fade=12, only=None, step=1.0):
    """Mirror src about line g into rows y0..y1 of c (water), lights kept with fading dither."""
    dark = dark or {}
    for y in range(y0, y1 + 1):
        d = y - g
        sy = int(round(g - d * step))
        for x in range(W):
            wob = int(round(math.sin(y * 2.3 + x * .13) * ripple * (.5 + d / 30)))
            sx = min(max(x + wob, 0), W - 1)
            if not (0 <= sy < H):
                continue
            if only is not None and not only[sy, sx]:
                continue
            v = int(src[sy, sx])
            if v in bright and BAY[y & 3, x & 3] < fade - d * .35:
                c.px(x, y, v)
            else:
                c.px(x, y, dark.get(v, 0))


def scene1():
    c = Cv(1)
    G = 74                                     # far shore / horizon
    sky(c, 0, G, G, 0.0, 3.5, .1)
    stars(c, 40, 5, 50)
    # ringed planet, upper left
    PX, PY, PR = 24, 22, 13
    ring = lambda a0, a1: [(PX + math.cos(a) * 26, PY + math.sin(a) * 6 - math.cos(a) * 4) for a in np.linspace(a0, a1, 90)]
    rb = m_line(ring(math.pi, 2 * math.pi), 2)
    c.fill(rb & (BAY < 12), 9)
    c.fill(m_line(ring(math.pi, 2 * math.pi), 1), 13)
    pm = m_ell(PX, PY, PR)
    d = dist(pm, 10)
    c.fill((d > 0) & (d < 7) & (BAY < 9 - d) & c.over((0, 1, 10)), 2)
    l = ((XX + .5 - PX) * .7 + (YY + .5 - PY) * -.7) / PR
    band = np.sin((YY - PY) * .9 + (XX - PX) * .15) * .35
    c.ramp(pm, 3.6 + l * 2.4 + band, [0, 1, 10, 2, 9, 13, 5])
    rf = m_line(ring(0, math.pi), 2)
    c.fill(rf & ~(pm & (YY < PY - 1)) & (BAY < 13), 13)
    c.fill(m_line(ring(0, math.pi), 1) & ~(pm & (YY < PY - 1)), 5)
    c.fill(m_line(ring(0, math.pi), 1) & (XX > PX + 14) & (XX < PX + 22), 11)
    # far coast city, hazed
    skyline(c, 31, 54, 66, G, 3, 7, body=2, lit=9, rimcol=None, wins=[13, 9], dens=60, wx=2, wy=2,
            side=.3, haze=(9, 11), roof=True)
    # suspension bridge across the bay
    DK = 62
    for tx in (14, 46, 98):
        c.fill(m_rect(tx - 1, 38, tx + 1, G), 10)
        c.fill(m_rect(tx - 1, 38, tx - 1, G), 9)
        c.fill(m_rect(tx - 2, 44, tx + 2, 44), 10)
        c.px(tx, 37, 6)
        c.glow(m_rect(tx, 37, tx, 37), 6, 2, 8, onto=(0, 1, 10, 2))
    for a, b in ((14, 46), (46, 98)):
        for x in range(a, b + 1):
            t = (x - a) / (b - a)
            y = 38 + (DK - 3 - 38) * 4 * t * (1 - t) * 1.0
            c.px(x, round(y), 9)
            if x % 3 == 0:
                c.fill(m_rect(x, round(y) + 1, x, DK - 1), 10)
    for x in list(range(-1, 14)) + list(range(98, W + 1)):
        a, b = (-30, 14) if x < 14 else (98, 142)
        t = (x - a) / (b - a)
        y = 38 + (DK - 3 - 38) * 4 * t * (1 - t)
        c.px(x, round(y), 9)
    c.fill(m_rect(0, DK, W - 1, DK + 1), 10)
    c.fill(m_rect(0, DK, W - 1, DK), 13)
    for x in range(0, W, 4):
        c.px(x + (DK % 2), DK + 2, 3 if x % 8 else 6)
    # water: reflection of everything above the shore
    bg = c.a.copy()
    reflect_rows(c, bg, G, G + 1, H - 1, dark={9: 1, 13: 2, 2: 1, 10: 0, 14: 1, 5: 2}, ripple=1.4, fade=11)
    for y in range(G + 1, H):                                 # horizontal wave glints
        for x in range(W):
            if (hsh(x // 5, y, 31) < 26) and c.get(x, y) in (0, 1):
                c.px(x, y, 10 if y < 90 else 2)
    # ---- the mecha (drawn above its waterline WL; reflected separately)
    WL = 90
    before = c.a.copy()
    S = [0, 1, 10, 2, 9, 13, 5]
    MX = 76
    gold = 3
    # back leg (viewer right), thigh then shin, sunk in the water
    part(c, [(80, 54), (91, 54), (95, 67), (85, 68)], 1.6, S, rim=7)
    part(c, [(85, 66), (97, 66), (100, 84), (98, 92), (88, 92), (87, 80)], 1.4, S, rim=7)
    c.fill(m_rect(89, 72, 96, 73), 0)
    c.fill(m_rect(89, 72, 96, 72), 15)
    # back arm (viewer left) holding a rifle low
    part(c, [(55, 30), (64, 31), (63, 45), (56, 45)], 2.0, S, rim=13, rimdir=(-1, 0))
    part(c, [(53, 45), (63, 45), (61, 58), (52, 58)], 2.2, S, rim=13, rimdir=(-1, 0))
    rifle = [(36, 64), (40, 60), (60, 56), (62, 59), (44, 66), (38, 67)]
    part(c, rifle, 1.4, S, rim=None)
    c.fill(m_line([(37, 64), (59, 57)], 1), 9)
    c.px(37, 66, 6)
    # waist and skirt
    part(c, [(69, 44), (87, 44), (85, 51), (71, 51)], 1.8, S)
    part(c, [(64, 49), (73, 49), (72, 60), (62, 58)], 2.4, S, rim=13, rimdir=(-1, 0))
    part(c, [(83, 49), (92, 49), (94, 58), (84, 60)], 1.6, S, rim=7)
    # front leg (viewer left) striding forward
    part(c, [(66, 54), (78, 54), (76, 68), (63, 68)], 3.0, S, rim=13, rimdir=(-1, 0))
    part(c, [(61, 66), (76, 66), (74, 84), (72, 92), (58, 92), (60, 80)], 2.9, S, rim=13, rimdir=(-1, 0))
    for y in (74, 78, 82):
        c.fill(m_rect(63, y, 71, y), 1)
    c.fill(m_rect(64, 75, 66, 76), 3)
    # torso
    part(c, [(66, 23), (90, 23), (93, 33), (87, 45), (69, 45), (63, 33)], 2.2, S, k=1.4)
    c.fill(m_line([(69, 41), (87, 41)], 1), 1)
    c.fill(m_line([(78, 36), (78, 44)], 1), 1)
    for x in (70, 72, 84, 86):
        c.fill(m_rect(x, 37, x, 39), 1)
    # armour detail: chest vents, plate seams, hazard stripes, knee caps, shin vents, lamps
    for k in range(3):
        c.fill(m_line([(68 + k * 2, 27 + k), (72 + k * 2, 27 + k)], 1), 1)
        c.fill(m_line([(84 - k * 2, 27 + k), (88 - k * 2, 27 + k)], 1), 1)
    c.fill(m_line([(66, 24), (90, 24)], 1), 13)
    c.fill(m_line([(66, 24), (90, 24)], 1) & (XX > 80), 9)
    for x in range(64, 73, 2):                                       # hazard stripes on the front thigh
        c.fill(m_line([(x, 62), (x + 2, 59)], 1) & m_rect(64, 59, 75, 62), 3)
    c.fill(m_rect(64, 58, 75, 58), 0)
    c.fill(m_rect(64, 63, 75, 63), 0)
    for x0, y0, lit in ((62, 66, 13), (86, 66, 7)):                  # knee caps
        kc = m_poly([(x0, y0), (x0 + 12, y0), (x0 + 11, y0 + 5), (x0 + 1, y0 + 5)])
        c.fill(dil(kc) & ~kc, 0)
        c.ramp(kc, 3.2 - (YY - y0) * .4 - (x0 > 80) * 1.2, S)
        c.fill(edge(kc, 0, -1), lit)
    for x in (88, 91, 94):                                           # shin vents, back leg
        c.fill(m_rect(x, 76, x, 84), 0)
    c.fill(m_rect(60, 86, 74, 86) | m_rect(88, 86, 98, 86), 0)      # ankle seam
    for x, y, col in ((65, 56, 6), (90, 56, 6), (92, 82, 7), (58, 38, 3), (100, 38, 3)):
        c.px(x, y, col)
    # reactor
    RX, RY = 78, 31
    c.fill(m_ell(RX, RY, 6), 0)
    c.ramp(m_ell(RX, RY, 5), 3.9 - np.hypot(XX + .5 - RX, YY + .5 - RY) * .8, [6, 12, 3, 4])
    c.fill(m_ell(RX, RY, 5) & ~m_ell(RX, RY, 4) & (BAY < 8), 12)
    c.glow(m_ell(RX, RY, 6), 12, 3, 6, onto=(1, 10, 2, 9))
    c.glow(m_ell(RX, RY, 6), 3, 2, 4, onto=(1, 10, 2, 9))
    # shoulders
    part(c, [(52, 21), (67, 20), (70, 30), (58, 34), (51, 28)], 2.6, S, rim=13, rimdir=(-1, 0))
    part(c, [(89, 20), (103, 21), (107, 28), (101, 34), (88, 30)], 1.8, S, rim=7)
    for x0, y0 in ((55, 25), (96, 25)):
        c.fill(m_rect(x0, y0, x0 + 5, y0), 3)
        c.glow(m_rect(x0, y0, x0 + 5, y0), 3, 1, 6, onto=(1, 10, 2))
    # head with V-fin and visor
    part(c, [(73, 14), (83, 14), (84, 21), (79, 24), (77, 24), (72, 21)], 2.4, S, k=1.2)
    c.fill(m_rect(74, 18, 82, 19), 0)
    c.fill(m_rect(75, 18, 81, 18), 6)
    c.fill(m_rect(77, 18, 79, 18), 4)
    c.glow(m_rect(75, 18, 81, 18), 6, 3, 8, onto=(0, 1, 10, 2))
    c.fill(m_line([(78, 14), (70, 6)], 1) | m_line([(78, 14), (86, 6)], 1), gold)
    c.fill(m_line([(78, 13), (71, 7)], 1), 12)
    c.px(78, 13, 6)
    # raised gun arm (viewer right) firing up at a gunship
    part(c, [(99, 30), (106, 32), (111, 41), (104, 43)], 1.6, S, rim=7)
    part(c, [(104, 40), (112, 41), (117, 28), (111, 25)], 1.8, S, rim=7)
    part(c, [(110, 26), (117, 30), (121, 18), (116, 15)], 1.6, S, rim=7)
    # cannon beam to the top-right gunship
    beam = m_line([(118, 15), (124, -2)], 3)
    c.fill(beam, 7)
    c.fill(m_line([(118, 15), (124, -2)], 1), 4)
    c.glow(beam, 7, 4, 8, onto=(0, 1, 10, 2, 9))
    mech = c.a != before
    # gunships + tracer fire hitting the left shoulder
    for gx, gy, d in ((32, 48, 1), (50, 34, 1)):
        shp = ["...........",
               "K.....5555.",
               "55..555bb55",
               ".5555hhhhh5",
               "...hhhhhhh.",
               "...h.....h."]
        sprite(c, gx - 6, gy - 3, shp, {'h': 14, '5': 5, 'b': 7, 'K': 6})
        c.px(gx + 5 * d, gy, 6)
        c.fill(m_line([(gx - 8, gy - 3), (gx + 3, gy - 3)], 1) & (BAY < 9), 13)      # rotor blur
        for i in range(2, 20, 3):
            t = i / 20
            tx_, ty_ = gx + 6 + (54 - gx - 6) * t, gy - 1 + (24 - gy + 1) * t
            c.px(tx_, ty_, 3)
            c.px(tx_ - 1, ty_ + 1, 12)
    # hit sparks and explosion on the left shoulder
    ex = m_ell(55, 22, 3, 2.5) | m_ell(53, 20, 2, 2)
    c.ramp(ex, 3.8 - np.hypot(XX + .5 - 56, YY + .5 - 23) * .9, [6, 12, 3, 4])
    c.glow(ex, 12, 5, 7, onto=(0, 1, 10, 2, 9, 13))
    for k in range(10):
        a = k * 2.4
        c.px(56 + math.cos(a) * (6 + k % 3), 23 + math.sin(a) * (4 + k % 2), 3 if k % 2 else 4)
    # smoke from the hit drifting left
    sm = np.zeros((H, W), bool)
    for i in range(8):
        sm |= m_ell(50 - i * 3, 18 - i * 1.3, 2 + i * .5, 1.5 + i * .3)
    c.fill(sm & ~mech & (BAY < 9) & c.over((0, 1, 10)), 2)
    c.fill(sm & ~mech & edge(sm, 0, 1) & (BAY < 9) & c.over((0, 1, 10, 2)), 9)
    # searchlights from the dock onto the mecha
    for ax, ay, bx, by in ((10, 92, 72, 26), (30, 94, 92, 36)):
        for i in range(100):
            t = i / 99
            cx_, cy_ = ax + (bx - ax) * t, ay + (by - ay) * t
            m = m_ell(cx_, cy_, 1 + 4 * t, 1 + 4 * t)
            m &= ~mech
            c.fill(m & (BAY < 6 + 3 * t) & c.over((0, 1, 10)), 2)
            c.fill(m & (BAY < 4 + 3 * t) & c.over((0, 1, 10, 2)), 9)
            c.fill(m_ell(cx_, cy_, .6 + 1.5 * t, .6 + 1.5 * t) & ~mech & (BAY < 2 + 3 * t) & c.over((0, 1, 10, 2, 9)), 13)
        spot = m_ell(bx, by, 6, 5) & mech & c.over((1, 10, 2, 9))
        c.fill(spot & (BAY < 7), 13)
        c.fill(spot & (BAY < 2), 5)
    # water around the legs: reflection of the mecha, foam
    reflect_rows(c, c.a.copy(), WL, WL + 1, H - 1, dark={9: 2, 13: 9, 2: 1, 10: 1, 1: 0, 5: 13}, ripple=1.6,
                 fade=10, only=mech)
    for x0, x1 in ((55, 77), (85, 103)):
        cxm = (x0 + x1) / 2
        fm = m_ell(cxm, WL, (x1 - x0) / 2, 2.2) | m_ell(cxm - 6, WL - 1, 4, 2) | m_ell(cxm + 7, WL - 1, 3, 2)
        c.fill(fm & (BAY < 9), 13)
        c.fill(fm & (BAY < 5), 5)
        c.fill(edge(fm, 0, -1), 11)
        for k in range(7):
            c.px(cxm - 9 + k * 3, WL - 3 - hsh(k, x0) % 3, (11, 5, 4)[k % 3])
    # foreground dock: crane, containers, lamps (left)
    c.fill(m_rect(0, 96, 34, H - 1), 0)
    c.fill(m_rect(0, 96, 34, 96), 14)
    for x in range(1, 34, 6):
        c.px(x, 97, 3)
    cr = 10
    lat = m_rect(cr, 34, cr + 5, 96) & ((((XX - cr + YY) % 6) == 0) | (((cr + 5 - XX + YY) % 6) == 0) |
                                        (XX == cr) | (XX == cr + 5))
    c.fill(lat, 0)
    c.fill(lat & (XX == cr) & (BAY < 10), 2)
    jib = m_rect(0, 32, 44, 35) & ((((XX + YY) % 5) == 0) | (YY == 32) | (YY == 35))
    c.fill(jib, 0)
    c.fill(m_rect(0, 32, 44, 32) & (BAY < 10), 2)
    c.fill(m_rect(cr - 1, 26, cr + 6, 31), 0)
    c.px(cr + 2, 27, 3)
    c.px(cr + 4, 27, 3)
    c.px(44, 31, 6)
    c.fill(m_rect(38, 36, 38, 52), 0)
    c.fill(m_rect(36, 52, 40, 54), 0)
    for i, (x0, y0, col) in enumerate(((0, 84, 10), (11, 84, 2), (22, 88, 10), (2, 90, 1), (14, 90, 10))):
        c.fill(m_rect(x0, y0, x0 + 10, y0 + 5), col)
        for x in range(x0 + 1, x0 + 10, 2):
            c.fill(m_rect(x, y0 + 1, x, y0 + 4), 1 if col != 1 else 0)
        c.fill(m_rect(x0, y0, x0 + 10, y0), 9 if col != 1 else 10)
    c.glyph_sign(24, 76, 2, 0, 3, 41, vertical=False)
    for lx in (6, 30):
        c.fill(m_rect(lx, 98, lx, 106), 0)
        c.px(lx, 97, 3)
        c.glow(m_rect(lx, 97, lx, 97), 3, 3, 7, onto=(0, 1, 10))
    # right foreground: buoy light and wave crests
    c.fill(m_rect(110, 100, 113, 104), 0)
    c.px(111, 99, 6)
    c.glow(m_rect(111, 99, 111, 99), 6, 3, 7, onto=(0, 1, 10, 2))
    # far-shore neon and harbour navigation lights (green starboard, red port)
    c.glyph_sign(113, 47, 3, 0, 15, 61)
    c.glow(m_rect(112, 46, 118, 60), 15, 2, 6, onto=(0, 1, 10, 2))
    c.fill(m_rect(44, 100, 47, 104), 0)
    c.px(45, 99, 8)
    c.glow(m_rect(45, 99, 45, 99), 8, 3, 7, onto=(0, 1, 10, 2))
    for x in (8, 20, 32):
        c.px(x, 95, 8)
    rain(c, 202, 40, cols=(2, 9), hi=(13, 5))
    return c


# ------------------------------------------------------------------ 02 storm geisha
GEISHA = [   # K hair, k hair sheen, w face, h face shade, p blush/liner, r lips, R lip hi, o kimono, O kimono shade, W collar, g gold pin, q pink pin
    "...........KKKKKK...........",
    ".........KKkkkkKKK..........",
    "........KkkkkkkkkKK.........",
    "...g....KkkkKKkkkkK....q....",
    "....g..KKkKKKKKKkkKK..q.....",
    ".....gKKkkKKKKKKKkkKKq......",
    "......KKKKKKKKKKKKKKKK......",
    ".....KKKkkKKKKKKKKKkkKK.....",
    "....KKKkKKKKKKKKKKKKKkKK....",
    "...KKKkKKKKKKKKKKKKKKKkKK...",
    "...KKkKKKKwwwwwwwwKKKKKkK...",
    "..KKkKKKwwwwwwwwwwwwKKKKK...",
    "..KKKKKwwwwwwwwwwwwwwKKKK...",
    "..KKKKwwKKKwwwwwKKKwwhKKK...",
    "..KKKKwwwwwwwwwwwwwwwhKKK...",
    "..KKKwwwKKKpwwwwKKKpwhhKK...",
    "..KKKwwwwwwwwwwwwwwwwhhKK...",
    "..KKKwwpwwwwwwwwwwpwwhhKK...",
    "...KKwwwwwwwwhwwwwwwhhKK....",
    "...KKKwwwwwwrrrwwwwwhhKK....",
    "....KKwwwwwwrRrwwwwhhKK.....",
    "....KKKwwwwwwwwwwwhhhKK.....",
    ".....KKKhwwwwwwwwhhhKK......",
    "......KKKhhwwwwwhhhKK.......",
    "........KKhhwwwhhKK.........",
    "..........KhwwwhK...........",
    "..........KhwwwhK...........",
    "......oooooWwwwWooooo.......",
    "....ooooqoWWwwWWoqoooo......",
    "...oooqqqooWWWWooqqqooo.....",
    "..ooooqooooOWWOooooqoooo....",
    "..ooooooOOOOWWOOOoooooooo...",
    ".oooogooOOOOWWOOOOoogooooo..",
    ".ooogggooOOOOOOOOoogggoooo..",
    ".oooogooOOOOOOOOOOoogoooooo.",
    "oooooooOOOOOOOOOOOOooooooooo",
]
GKEY = {'K': 0, 'k': 9, 'w': 11, 'h': 13, 'p': 15, 'r': 6, 'R': 4, 'o': 12, 'O': 15, 'W': 4, 'g': 3, 'q': 4}


def bolt(c, x, y, ylim, seed, w=1, depth=0, pts=None):
    """Lightning: jagged random walk with forks; returns its mask."""
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


def scene2():
    c = Cv(2)
    G = 96
    sky(c, 0, G, G, 0.2, 3.3, .1)
    # storm clouds: dark masses, lit from inside near the bolt
    BX, BY = 36, 0
    lm = bolt(c, 14, 0, 62, 5, 1)
    ld = dist(lm, 30)
    cm = np.zeros((H, W), bool)
    r = np.random.RandomState(12)
    for _ in range(26):
        cx, cy = r.randint(-10, W + 10), r.randint(-4, 34)
        cm |= m_ell(cx, cy, r.randint(8, 20), r.randint(4, 9))
    t = 1.0 + np.clip(1 - ld / 26, 0, 1) * 3.4 - np.clip((YY - 10) / 30, 0, 1) * .4
    t = t + (((XX * 3 + YY * 5) % 7) == 0) * 0
    c.ramp(cm, t, [0, 1, 10, 2, 9, 13, 5])
    c.fill(edge(cm, 0, 1) & (ld < 22), 13)                      # lit cloud undersides
    c.fill(edge(cm, 0, 1) & (ld >= 22) & (BAY < 9), 2)
    # far skyline, hazy
    skyline(c, 41, 52, 70, G, 4, 8, body=2, lit=9, rimcol=None, wins=[13, 9], dens=60, wx=2, wy=3,
            side=.3, haze=(9, 8))
    # the bolt itself: forks with a bloom
    c.glow(lm, 13, 5, 6, onto=(0, 1, 10, 2, 9))
    c.glow(lm, 5, 1, 9, onto=(0, 1, 10, 2, 9, 13))
    c.fill(lm, 4)
    # mid blocks (the tower covers the right half)
    skyline(c, 43, 50, 68, G, 7, 13, body=1, lit=10, rimcol=None, wins=[5, 13, 3, 8], dens=90, wx=3, wy=3,
            ww=1, wh=1, side=.2)
    # the megatower: roof projectors throw a giant geisha hologram into the storm
    TX0, TX1, TT = 64, 119, 68
    tw = m_rect(TX0, TT, TX1, G) | m_poly([(TX0 + 3, TT), (TX0 + 8, TT - 4), (TX1 - 6, TT - 4), (TX1, TT)])
    l = (XX - TX0) / (TX1 - TX0)
    c.ramp(tw, 2.4 - l * 2.0, [0, 1, 10, 2, 9])
    c.fill(edge(tw, -1, 0) & (BAY < 12), 13)
    c.fill(edge(tw, 0, -1), 9)
    for y in range(TT + 4, G - 2, 3):                          # window bands
        if hsh(y, 3, 9) < 110:
            for x in range(TX0 + 3, TX1 - 9, 3):
                if hsh(x, y, 9) < 170:
                    c.px(x, y, 5 if x < 80 else 3 if hsh(y, 4) < 120 else 13)
    c.glyph_sign(TX1 - 7, TT + 6, 4, 0, 15, 21)
    c.glow(m_rect(TX1 - 7, TT + 6, TX1 - 3, TT + 22), 15, 2, 7, onto=(0, 1, 10))
    c.glyph_sign(TX0 + 4, TT + 8, 3, 0, 8, 22, vertical=False)
    CX = 92
    em = [(CX - 18, TT - 5), (CX, TT - 5), (CX + 18, TT - 5)]
    hair = m_ell(CX, 24, 16, 13) | m_ell(CX, 9, 10, 6.5) | m_ell(CX - 14, 28, 6, 9) | m_ell(CX + 14, 28, 6, 9)
    face = m_ell(CX, 33, 10, 12.5) & (YY >= 23)
    neck = m_rect(CX - 4, 43, CX + 4, 51) & ~face
    kim = m_poly([(CX - 30, TT + 1), (CX - 24, 55), (CX - 8, 48), (CX + 8, 48), (CX + 24, 55), (CX + 30, TT + 1)]) & (YY <= TT - 5)
    fig = hair | face | neck | kim
    for ex, ey in em:                                            # projector beams
        for tx_ in ((CX - 30, CX - 14) if ex < CX else (CX + 14, CX + 30) if ex > CX else (CX - 8, CX + 8)):
            c.fill(m_line([(ex, ey), (tx_, 20 if abs(tx_ - CX) > 12 else 46)], 1) & ~fig & (BAY < 9), 7)
        c.fill(m_rect(ex - 2, ey, ex + 2, ey + 1), 0)
        c.px(ex, ey, 4)
        c.glow(m_rect(ex, ey, ex, ey), 7, 2, 9, onto=(0, 1, 10, 2, 9))
    c.fill(dil(fig) & ~fig, 7)                                   # cyan hologram rim
    # hair: black with sheen arcs
    c.ramp(hair, 1.6 - ((XX - CX) * .5 + (YY - 16) * .8) / 14, [0, 1, 10, 2])
    for yc, rr, ry in ((22, 13, 9), (9, 8, 4.5), (28, 5, 7)):
        for xo in ((-14, 14) if yc == 28 else (0,)):
            arc = m_ell(CX + xo - 2, yc, rr, ry) & ~m_ell(CX + xo - 1, yc + 1.5, rr, ry) & hair
            c.fill(arc, 9)
            c.fill(arc & (XX < CX + xo - 2) & (BAY < 8), 13)
    # kanzashi: gold pins with dangling tassels, a flower on the bun
    for x0, y0, x1, y1 in ((CX + 6, 8, CX + 18, 1), (CX - 6, 8, CX - 17, 2)):
        c.fill(m_line([(x0, y0), (x1, y1)], 1), 3)
        c.px(x1, y1, 4)
        for j in range(4):
            c.px(x1 + (1 if x1 > CX else -1), y1 + 1 + j, 15 if j < 3 else 4)
    fl = m_ell(CX + 8, 13, 3, 2.5)
    c.fill(fl, 15)
    c.fill(m_ell(CX + 7, 12, 1.2, 1.2), 4)
    c.px(CX + 8, 13, 3)
    # face: porcelain with soft right-side shade, blush, eyes, red lips
    c.ramp(face | neck, 2.6 - np.clip((XX - CX) / 9.0, -1, 1) * .9 - (YY > 43) * .7, [9, 13, 5, 11, 4])
    fr = face & (YY < 22 + np.abs(XX + .5 - CX) * .45 + 1.5)          # parted hairline
    c.fill(fr, 1)
    for dx in (-5, 5):                                             # eyes: closed, upswept, red liner
        s_ = 1 if dx > 0 else -1
        c.fill(m_line([(CX + dx - 2 * s_, 32), (CX + dx + 2 * s_, 31)], 1), 0)
        c.fill(m_line([(CX + dx - 1 * s_, 33), (CX + dx + 1 * s_, 33)], 1), 13)
        c.px(CX + dx + 3 * s_, 30, 6)
        c.px(CX + dx + 3 * s_, 31, 6)
        c.fill(m_line([(CX + dx - 2, 28), (CX + dx + 2, 28)], 1), 2)
        c.fill(m_ell(CX + dx, 36, 2.5, 1.5) & (BAY < 7), 15)
    c.px(CX, 35, 13)
    c.px(CX + 1, 37, 13)
    c.fill(m_rect(CX - 2, 40, CX + 1, 40), 6)
    c.fill(m_rect(CX - 1, 41, CX, 41), 6)
    c.px(CX - 1, 40, 4)
    # kimono: magenta silk, rose folds, gold crane-flower pattern, white collar
    c.ramp(kim, 2.2 + np.sin((XX - CX) * .35 + YY * .12) * .7, [10, 12, 15, 15])
    c.fill(kim & (((XX * 3 + YY * 5) % 11) == 0) & (YY > 56), 3)
    for x0, y0 in ((CX - 18, 62), (CX + 14, 60), (CX - 8, 68), (CX + 22, 70)):
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            c.px(x0 + dx, y0 + dy, 3 if (dx, dy) != (0, 0) else 4)
    c.fill(m_line([(CX - 8, 48), (CX + 3, 62)], 3) & kim, 4)
    c.fill(m_line([(CX + 8, 48), (CX - 1, 60)], 3) & kim, 11)
    c.fill(m_line([(CX + 8, 48), (CX - 1, 60)], 1) & kim, 13)
    # hologram treatment: scanlines, a glitch slice, fade into the projectors
    figp = fig | (dil(fig) & ~fig)
    for y in range(0, TT - 3):
        if y % 3 == 0:
            for x in range(CX - 34, CX + 33):
                if 0 <= x < W and figp[y, x]:
                    v = c.get(x, y)
                    c.px(x, y, {11: 5, 4: 5, 5: 13, 13: 9, 15: 12, 12: 9, 0: 1, 9: 13, 3: 12}.get(v, v))
    for y0, sx in ((30, 2), (31, 2), (52, -2)):
        row = c.a[y0, CX - 30:W - 3].copy()
        c.a[y0, CX - 30 + sx:W - 3 + sx] = row
        c.px(CX - 30 + min(sx, 0), y0, 7)
    c.fill(kim & (YY > TT - 10) & (BAY < (YY - (TT - 10)) * 3), 1)
    # left mid buildings
    # elevated rail with a train crossing in front
    RY = 72
    c.fill(m_rect(0, RY, W - 1, RY + 2), 0)
    c.fill(m_rect(0, RY, W - 1, RY), 9)
    for x in range(4, W, 22):
        c.fill(m_rect(x, RY + 3, x + 2, G), 0)
        c.fill(m_rect(x, RY + 3, x, G) & (BAY < 9), 2)
    tr = m_rect(14, RY - 7, 62, RY - 1)
    c.fill(tr, 1)
    c.fill(m_poly([(62, RY - 7), (66, RY - 4), (66, RY - 1), (62, RY - 1)]), 1)
    c.fill(m_rect(14, RY - 7, 62, RY - 7), 13)
    for x in range(16, 60, 4):
        c.fill(m_rect(x, RY - 5, x + 2, RY - 4), 3 if x % 8 else 11)
    c.fill(m_rect(14, RY - 2, 66, RY - 2), 7)
    c.px(65, RY - 4, 4)
    c.glow(m_rect(14, RY - 2, 66, RY - 2), 7, 2, 6, onto=(0, 1, 10, 2))
    c.glow(m_rect(65, RY - 4, 65, RY - 4), 11, 3, 8, onto=(0, 1, 10, 2))
    # foreground: left street-front with signs and an awning
    c.fill(m_rect(0, 74, 12, G), 0)
    c.glyph_sign(2, 76, 3, 14, 12, 33)
    c.glow(m_rect(1, 75, 7, 89), 12, 2, 6, onto=(0, 1, 10, 2))
    storefronts(c, 13, 60, G - 13, G, 9, [15, 12, 8, 7])
    for x, rim in ((20, 7), (33, 15), (47, 8)):
        umbrella(c, x, G, rim)
    car(c, 40, 30, 1, 14, 6)
    car(c, 60, 46, -1, 14, 15)
    car(c, 20, 56, 1, 5, 6, trail=8)
    # street
    for x in range(W):
        c.px(x, G, 9 if (x // 3) % 2 else 2)
    reflect(c, G, dark={13: 1, 9: 1, 2: 1, 14: 1, 10: 0, 5: 1}, ripple=1.3, fade=9, wet=(10, 16))
    # heavy rain + splashes
    rain(c, 303, 70, cols=(2, 9), hi=(13, 5), slant=2, ln=4)
    r = np.random.RandomState(44)
    for _ in range(14):
        x, y = r.randint(1, W - 2), r.randint(G + 3, H - 1)
        c.px(x - 1, y, 13)
        c.px(x + 1, y, 13)
        c.px(x, y - 1, 5)
    return c


# ------------------------------------------------------------------ 03 crash site
def plume(c, pts, ramp, lit, seed, under=None, rim=None):
    """Billowing smoke: puffs [(x,y,r)] painted far (first) to near, each shaded with its own lit underside."""
    r = np.random.RandomState(seed)
    m = np.zeros((H, W), bool)
    for x, y, rr in pts:
        for _ in range(3):
            px_, py_, pr = x + r.uniform(-rr * .7, rr * .7), y + r.uniform(-rr * .4, rr * .4), rr * r.uniform(.55, .9)
            mm = m_ell(px_, py_, pr * 1.15, pr * .9)
            t = 1.0 + ((YY + .5 - py_) / pr) * lit + ((XX + .5 - px_) / pr) * .3
            c.ramp(mm, t, ramp)
            if rim is not None:
                c.fill(edge(mm, 1, 1) & (BAY < 5), rim)
            m |= mm
    if under is not None:
        c.fill(edge(m, 0, 1) & (BAY < 11), under)
    return m


def flames(c, x0, x1, base, hmax, seed, ramp=(6, 12, 3, 4)):
    """Fire wall: jagged tongues per column, white-hot base to red tips."""
    m = np.zeros((H, W), bool)
    t = np.zeros((H, W))
    for x in range(x0, x1 + 1):
        u = (x - x0) / max(x1 - x0, 1)
        h = hmax * (math.sin(u * math.pi) * .6 + .4) * (.3 + .7 * abs(math.sin(x * .8 + seed) * math.sin(x * .31 + seed * 2))) + (hsh(x, seed) % 3)
        for y in range(int(base - h), base + 1):
            if 0 <= y < H and 0 <= x < W:
                m[y, x] = True
                t[y, x] = 3.6 * (max(y - (base - h), 0) / max(h, 1)) ** .7
    c.ramp(m, t, list(ramp))
    return m


def scene3():
    c = Cv(3)
    G = 95
    sky(c, 0, G, G, -0.8, 4.4, .05)
    stars(c, 14, 9, 22)
    MX, MY, MR = 98, 20, 14
    moon(c, MX, MY, MR, [2, 9, 13, 13, 12], halo=(9, 2), craters=False)
    mm = m_ell(MX, MY, MR)
    for dx, dy, rx, ry in ((-5, -4, 6, 3), (3, 4, 5, 3.5), (6, -6, 3, 2), (-3, 8, 3, 2)):
        c.fill(m_ell(MX + dx, MY + dy, rx, ry) & mm & (BAY < 10), 9)
    c.fill(edge(m_ell(MX, MY, MR), 1, 1) & (BAY < 10), 6)
    # descent trail across the sky (from upper right)
    trail = [(122 - i * 2.6, 26 + i * 1.5, 1.2 + i * .16) for i in range(10)]
    plume(c, trail, [10, 2, 9, 13], .6, 3)
    # far ruins / skyline hazed in fire glow
    skyline(c, 51, 58, 74, G, 4, 9, body=2, lit=9, rimcol=None, wins=[13, 12], dens=40, wx=2, wy=3,
            side=.3, haze=(9, 10))
    # great smoke column rising from the impact, drifting left
    col = [(30 - i * 1.4 - i * i * .1, 76 - i * 5.4, 4 + i * 1.5) for i in range(13)][::-1]
    sm = plume(c, col, [0, 1, 10, 2, 9], 1.2, 7, under=12, rim=12)
    c.fill(sm & (np.hypot(XX - 28, YY - 76) < 20) & (BAY < 4), 12)
    # mid buildings, fire-lit on the side facing the crash
    nb = skyline(c, 52, 62, 80, G, 7, 13, body=1, lit=10, rimcol=None, wins=[3, 12, 13], dens=60, wx=3, wy=3,
                 ww=1, wh=1, side=.25)
    for x0, x1, top in nb:
        fx = x0 if x0 > 30 else x1
        if abs(fx - 30) < 50:
            c.fill(m_rect(fx, top, fx, G) & (BAY < 2 + 6 * np.clip(1 - np.abs(XX - 30) / 50, 0, 1)), 12)
    # the starship, nose buried at lower left, tail up right
    NX, NY, TXX, TYY = 24, 84, 104, 44
    L = math.hypot(TXX - NX, TYY - NY)
    ux, uy = (TXX - NX) / L, (TYY - NY) / L
    nx, ny = uy, -ux                                      # points up-left (dorsal)
    s = ((XX + .5 - NX) * ux + (YY + .5 - NY) * uy) / L    # 0 nose .. 1 tail
    v = (XX + .5 - NX) * nx + (YY + .5 - NY) * ny         # + dorsal, - ventral
    hwd = 1.5 + 9 * np.clip(s * 2.2, 0, 1) - 2.5 * np.clip((s - .85) * 6, 0, 1)
    hull = (s > 0) & (s < 1) & (v < hwd * .9) & (v > -hwd * .75)
    sh_t = 2.3 + v / np.maximum(hwd, 1) * 1.4                 # lighter on the dorsal side (moonlight)
    c.fill(dil(hull) & ~hull, 0)
    c.ramp(hull, sh_t, [0, 1, 14, 5, 11])
    belly = hull & ~sh(hull, int(round(-ny * 2)), 1)
    c.fill(belly, 12)
    c.fill(hull & ~sh(hull, int(round(-ny * 4)), 2) & ~belly & (BAY < 6), 3)   # fire-lit belly
    c.fill(edge(hull, 1, 0) & edge(hull, 0, -1), 11)
    # panel seams across the hull and a window strip
    for k in np.arange(.14, .95, .075):
        c.fill(hull & (np.abs(s - k) < .006 + 0 * s), 1)
    win = hull & (np.abs(v - hwd * .35) < .6) & (s > .22) & (s < .8)
    c.fill(win & ((np.round(s * 60) % 2) == 0), 7)
    # dorsal fin and engines
    fin = m_poly([(NX + ux * L * .7 + nx * 7, NY + uy * L * .7 + ny * 7), (NX + ux * L * .92 + nx * 16, NY + uy * L * .92 + ny * 16),
                  (NX + ux * L * .97 + nx * 7, NY + uy * L * .97 + ny * 7)])
    c.fill(dil(fin) & ~fin & ~hull, 0)
    c.ramp(fin, 2.6 - (YY - 30) / 30, [1, 14, 5, 11])
    for off in (-4, 3):
        ex, ey = NX + ux * L * 1.0 + nx * off, NY + uy * L * 1.0 + ny * off
        e = m_ell(ex, ey, 3.2)
        c.fill(dil(e) & ~e, 0)
        c.ramp(e, 3.6 - np.hypot(XX + .5 - ex, YY + .5 - ey) * .9, [10, 7, 5, 4])
        c.glow(e, 7, 3, 8, onto=(0, 1, 10, 2, 9))
    # breaches: fires along the hull with smoke
    for k, rr in ((.32, 3.5), (.56, 2.8), (.74, 2.2)):
        fx, fy = NX + ux * L * k + nx * 2, NY + uy * L * k + ny * 2
        f = m_ell(fx, fy, rr * 1.2, rr)
        f |= m_poly([(fx - rr, fy), (fx + rr, fy), (fx + rr * .3, fy - rr * 3), (fx - rr * .2, fy - rr * 2.2)])
        c.ramp(f, 3.9 - np.clip((fy + rr - YY) / (rr * 1.3), 0, 3.9) - np.abs(XX - fx) / rr, [6, 12, 3, 4])
        c.glow(f, 12, 4, 8, onto=(0, 1, 10, 2, 9, 14))
        c.glow(f, 6, 6, 4, onto=(0, 1, 10, 2))
    # impact: crater fire wall at the nose, rubble, a toppled tower behind
    imp = flames(c, 2, 48, G, 26, 2)
    flames(c, 10, 30, G, 12, 5)
    c.glow(imp, 12, 4, 6, onto=(0, 1, 10, 2, 9))
    c.glow(imp, 6, 7, 3, onto=(0, 1, 10, 2))
    for k in range(18):                                          # sparks arcing out
        a = -math.pi * (.15 + .7 * (hsh(k, 1, 3) / 255))
        sp = 6 + hsh(k, 2, 3) % 14
        for j in range(3):
            d = sp + j
            c.px(26 + math.cos(a) * d, 82 + math.sin(a) * d + d * d * .02, (4, 3, 12)[j])
    # surviving neon: a flickering magenta sign (glyphs half dead) and a green exit sign
    c.glyph_sign(108, 56, 4, 0, 15, 71)
    c.fill(m_rect(109, 62, 111, 66), 0)
    c.glow(m_rect(107, 55, 113, 58), 15, 2, 6, onto=(0, 1, 10, 2))
    c.glyph_sign(58, 80, 2, 0, 8, 72, vertical=False)
    c.glow(m_rect(57, 79, 67, 85), 8, 2, 6, onto=(0, 1, 10, 2))
    # foreground: barricade with emergency lights, rubble silhouettes
    rub = m_poly([(0, 92), (6, 88), (10, 90), (14, 87), (20, 91), (22, G), (0, G)])
    c.fill(rub, 0)
    c.fill(edge(rub, 0, -1) & (BAY < 12), 12)
    bar = m_rect(70, 88, 100, 92)
    c.fill(bar, 0)
    for x in range(70, 101, 4):
        c.fill(m_rect(x, 89, x + 1, 90), 6 if (x // 4) % 2 else 4)
    c.fill(m_rect(72, 92, 72, G) | m_rect(98, 92, 98, G), 0)
    for x, col in ((74, 6), (96, 7)):
        c.fill(m_rect(x, 85, x + 2, 87), col)
        c.glow(m_rect(x, 85, x + 2, 87), col, 4, 8, onto=(0, 1, 10, 2, 9))
    # ambulance-drone over the barricade
    sprite(c, 80, 70, ["..KKKKKK..", ".K5555557K", "K55KK5555K", ".KKKKKKKK.", "..K....K.."], {'K': 0, '5': 5, '7': 6})
    c.fill(m_line([(79, 75), (74, 84)], 1) & (BAY < 8), 13)
    c.fill(m_line([(88, 75), (93, 84)], 1) & (BAY < 8), 13)
    car(c, 50, 30, 1, 14, 6)
    car(c, 108, 60, -1, 14, 6, trail=6)
    # street
    for x in range(W):
        c.px(x, G, 9 if (x // 4) % 3 else 2)
    reflect(c, G, dark={13: 2, 9: 1, 2: 1, 14: 1, 10: 0, 5: 1}, ripple=1.2, fade=12, wet=(2, 14))
    rain(c, 404, 46, cols=(2, 9), hi=(13, 9))
    # embers drifting up
    r = np.random.RandomState(8)
    for _ in range(26):
        x, y = r.randint(0, 70), r.randint(30, 92)
        if c.get(x, y) in (0, 1, 10, 2, 9):
            c.px(x, y, (12, 3, 6)[r.randint(0, 3)])
    return c


# ------------------------------------------------------------------ output
def save(c, name):
    p = {**FIX, **PALS[c.n]}
    im = Image.fromarray(c.a, 'P')
    flat = []
    for i in range(16):
        flat += list(p.get(i, (0, 0, 0)))
    im.putpalette(flat)
    im.save(os.path.join(HERE, name))
    return im


SCENES = [scene0, scene1, scene2, scene3]
CROPS = [(2, 0), (50, 8), (62, 0), (20, 34)]

if __name__ == '__main__':
    import sys
    only = [int(a) for a in sys.argv[1:]] or range(len(SCENES))
    ims = {}
    for i in only:
        ims[i] = save(SCENES[i](), 'scene%02d.png' % i)
    if len(ims) == len(SCENES) == 4:
        pv = Image.new('RGB', (480, 448))
        cr = Image.new('RGB', (480, 448))
        for i, im in ims.items():
            rgb = im.convert('RGB')
            pv.paste(rgb.resize((240, 224), Image.Resampling.NEAREST), ((i % 2) * 240, (i // 2) * 224))
            x, y = CROPS[i]
            cr.paste(rgb.crop((x, y, x + 60, y + 56)).resize((240, 224), Image.Resampling.NEAREST),
                     ((i % 2) * 240, (i // 2) * 224))
        pv.save(os.path.join(HERE, 'preview_a2.png'))
        cr.save(os.path.join(HERE, 'crops_a2.png'))
    for i, im in ims.items():
        im.convert('RGB').resize((480, 448), Image.Resampling.NEAREST).save(
            os.path.join(os.environ.get('TMPV', HERE), 'v_%02d.png' % i))
