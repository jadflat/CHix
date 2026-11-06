# scene08 v4 for CHix (round 2): v3's sky, planet, spires and city kept; the street level
# repainted as a place (noodle bar + holo bowl, alley, konbini, shutter, arcade, vending
# machines, bar, subway stairs; people, umbrellas, steam, wet neon reflections). Spire
# windows calmer (no 1-px cyan/white dotted columns in the middle), no lone gold pixels.
# Run: python paint_s08_v4.py   -> scene08.png, preview_s08v4.png (deterministic)
import math, random, os
from PIL import Image
W, H = 120, 112
HERE = os.path.dirname(os.path.abspath(__file__))
B4 = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]
def bay(x, y): return (B4[int(y) & 3][int(x) & 3] + 0.5) / 16.0

FIXED = {0:(4,4,12),3:(255,200,60),4:(255,255,255),5:(200,225,255),6:(255,80,60),
         7:(40,230,255),8:(60,255,120),11:(235,238,255),14:(90,100,160),15:(255,60,200)}
# free: ramp 1<2<10<9 (sky, planet, city); 12/13 wet-street darks (shimmer toward 9/10)
FREE = {1:(26,10,50), 2:(70,28,108), 10:(146,58,160), 9:(236,136,204),
        12:(34,14,58), 13:(250,128,70)}       # 12 wet-street dark, 13 warm amber (lanterns, interiors)
BRIGHT = {3,4,5,6,7,8,11,15}

def polym(pts):
    m = set(); ys = [p[1] for p in pts]
    for y in range(int(math.floor(min(ys))), int(math.ceil(max(ys)))+1):
        yc = y+0.5; xs = []
        for i in range(len(pts)):
            (a,b),(c,d) = pts[i], pts[(i+1)%len(pts)]
            if (b <= yc < d) or (d <= yc < b): xs.append(a+(yc-b)*(c-a)/(d-b))
        xs.sort()
        for i in range(0, len(xs)-1, 2):
            for x in range(int(math.ceil(xs[i]-0.5)), int(math.floor(xs[i+1]-0.5))+1):
                if 0 <= x < W and 0 <= y < H: m.add((x, y))
    return m
def rectm(x0, y0, x1, y1):
    return {(x,y) for y in range(max(0,y0), min(H-1,y1)+1) for x in range(max(0,x0), min(W-1,x1)+1)}
def ellm(cx, cy, a, b):
    return {(x,y) for y in range(int(cy-b)-1, int(cy+b)+2) for x in range(int(cx-a)-1, int(cx+a)+2)
            if 0 <= x < W and 0 <= y < H and ((x+.5-cx)/a)**2+((y+.5-cy)/b)**2 <= 1}

# smooth value noise (seeded) for cloud swirls
_rn = random.Random(808)
_G = [[_rn.random() for _ in range(64)] for _ in range(64)]
def vnoise(x, y):
    xi, yi = int(math.floor(x)), int(math.floor(y)); fx, fy = x-xi, y-yi
    fx = fx*fx*(3-2*fx); fy = fy*fy*(3-2*fy)
    g = lambda a, b: _G[b & 63][a & 63]
    a = g(xi, yi)+(g(xi+1, yi)-g(xi, yi))*fx
    b = g(xi, yi+1)+(g(xi+1, yi+1)-g(xi, yi+1))*fx
    return a+(b-a)*fy
def fbm(x, y): return 0.6*vnoise(x, y)+0.3*vnoise(x*2.1+7, y*2.1+3)+0.1*vnoise(x*4.3+1, y*4.3+9)

UP = {0:1, 1:2, 2:10, 10:9, 9:5, 13:10, 12:13, 14:5}     # one step brighter
DN = {1:0, 2:1, 10:2, 9:10, 5:9, 13:12, 12:0, 14:2, 11:5, 4:5}

class C:
    def __init__(s):
        s.p = [[0]*W for _ in range(H)]; s.r = random.Random(8003)
    def px(s, x, y, c):
        x = int(x); y = int(y)
        if 0 <= x < W and 0 <= y < H: s.p[y][x] = c
    def g(s, x, y):
        x = int(x); y = int(y)
        return s.p[y][x] if 0 <= x < W and 0 <= y < H else -1
    def put(s, m, c):
        for (x, y) in m: s.p[y][x] = c
    def rect(s, x0, y0, x1, y1, c): s.put(rectm(int(x0), int(y0), int(x1), int(y1)), c)
    def line(s, x0, y0, x1, y1, c):
        x0,y0,x1,y1 = int(round(x0)),int(round(y0)),int(round(x1)),int(round(y1))
        dx, dy = abs(x1-x0), -abs(y1-y0); sx = 1 if x0<x1 else -1; sy = 1 if y0<y1 else -1; e = dx+dy
        while True:
            s.px(x0, y0, c)
            if x0==x1 and y0==y1: break
            e2 = 2*e
            if e2 >= dy: e += dy; x0 += sx
            if e2 <= dx: e += dx; y0 += sy
    def lift(s, cx, cy, r, lv, M, only=None, sy=1.0):
        for y in range(int(cy-r*sy)-1, int(cy+r*sy)+2):
            for x in range(int(cx-r)-1, int(cx+r)+2):
                if not (0 <= x < W and 0 <= y < H): continue
                d = math.hypot(x+.5-cx, (y+.5-cy)/sy)
                if d >= r: continue
                c = s.p[y][x]
                if only is not None and c not in only: continue
                if bay(x, y) < lv*(1-d/r): s.p[y][x] = M.get(c, c)
    def save(s, path):
        im = Image.new('P', (W, H)); pal = []
        for i in range(16): pal += list(FIXED[i] if i in FIXED else FREE[i])
        im.putpalette(pal)
        im.putdata([v for row in s.p for v in row]); im.save(path)
        return im

def scene08():
    s = C(); r = s.r
    SKYB = 80                                     # far-city base / haze line
    # ---- sky: near-black top to violet low sky, ordered dither
    ramp = [0, 0, 1, 1, 2]
    for y in range(H):
        v = max(0.0, min(len(ramp)-1.001, (y/SKYB)**1.15*(len(ramp)-1))); i = int(v)
        for x in range(W): s.p[y][x] = ramp[i+1] if v-i > bay(x, y) else ramp[i]
    # stars: sparse, small, mostly away from the middle
    rs = random.Random(81)
    for _ in range(46):
        x, y = rs.randint(0, W-1), rs.randint(0, 46)
        if s.g(x, y) in (0, 1): s.px(x, y, rs.choice((2, 2, 10, 14, 5)))
    for (x, y) in ((6, 5), (113, 40), (24, 3), (97, 30)):
        s.px(x, y, 11); s.px(x-1, y, 2); s.px(x+1, y, 2); s.px(x, y-1, 2); s.px(x, y+1, 2)
    # small far moon, upper right
    mx, my, mr = 103, 13, 5.2
    for (x, y) in ellm(mx, my, mr, mr):
        lx, ly = (x+.5-mx)/mr, (y+.5-my)/mr
        lam = max(0, -0.7*lx-0.3*ly+0.6*math.sqrt(max(0, 1-lx*lx-ly*ly)))
        rp = [1, 2, 10, 9]; v = min(3.0-.001, lam*3.4); i = int(v)
        s.p[y][x] = rp[i+1] if v-i > bay(x, y) else rp[i]
    s.px(101, 12, 10); s.px(104, 15, 2); s.px(100, 15, 2)    # craters

    # ---- planet: banded gas giant, light from the upper left
    cx, cy, R = 60, 39, 34
    tilt = math.radians(-18); ct, st = math.cos(tilt), math.sin(tilt); ba = 0.27
    def ringr(x, y):
        dx, dy = x+.5-cx, y+.5-cy
        u = dx*ct+dy*st; v = -dx*st+dy*ct
        return math.hypot(u, v/ba)/R, v, u
    def ringcol(rn, x, y, u):
        if rn < 1.18 or rn > 1.9: return None
        q = (rn-1.18)/0.72
        lit = 1.0 if u < 0 else 0.75                     # left half catches more light
        if q < 0.12: return 2 if bay(x, y) < .6 else None
        if q < 0.2: return 10 if bay(x, y) < .5*lit else 2
        if q < 0.42: return (5 if u < -R*0.3 and bay(x, y) < .3 else 9) if bay(x, y) < .8*lit else 10
        if q < 0.47: return 1                             # Cassini gap
        if q < 0.7: return 10 if bay(x, y) < .8 else 9
        if q < 0.85: return 2 if bay(x, y) < .7 else 10
        return 2 if bay(x, y) < .35 else None
    for y in range(H):                                    # far half of the ring
        for x in range(W):
            rn, v, u = ringr(x, y)
            if v < 0:
                c = ringcol(rn, x, y, u)
                if c is not None: s.p[y][x] = c
    # atmosphere halo outside the disc (lit side strong, dark side faint)
    for y in range(H):
        for x in range(W):
            d = math.hypot(x+.5-cx, y+.5-cy)
            if R <= d < R+5:
                side = -((x+.5-cx)*0.75+(y+.5-cy)*0.66)/d          # +1 toward the light
                k = (R+5-d)/5*(0.35+0.65*max(0, side+0.3))
                if bay(x, y) < k:
                    s.p[y][x] = 10 if d < R+1.5 and side > 0.1 else (2 if s.p[y][x] in (0, 1) else s.p[y][x])
    disc = ellm(cx, cy, R, R)
    pr = [0, 1, 2, 10, 9]
    def pv(x, y):
        lx, ly = (x+.5-cx)/R, (y+.5-cy)/R
        lz = math.sqrt(max(0, 1-lx*lx-ly*ly))
        # banded clouds, warped by turbulence; bands follow the ring's tilt
        lat = (-lx*st+ly*ct)
        warp = (fbm(lx*3+4, lat*7+2)-0.5)*0.55
        q = (lat+warp*0.22)*5.2+0.2*math.sin(lx*6+lat*3)
        TONE = (0.10, -0.06, 0.14, -0.12, 0.04, 0.16, -0.08, 0.08, -0.14, 0.12, 0.0, -0.06)
        band = TONE[int(math.floor(q)) % len(TONE)]
        f = q-math.floor(q)
        if f > 0.82 and bay(x*3, y) < (f-0.82)*5: band = TONE[(int(math.floor(q))+1) % len(TONE)]
        swirl = (fbm(lx*5+11, lat*10+5)-0.5)*0.16
        lam = max(0, -0.62*lx-0.5*ly+0.6*lz)
        return lam*0.95+(band+swirl)*(0.35+lam)+0.05
    for (x, y) in disc:
        v = max(0.0, min(len(pr)-1.001, pv(x, y)*(len(pr)-1))); i = int(v)
        f = max(0.0, min(1.0, (v-i-0.5)*2.2+0.5))
        s.p[y][x] = pr[i+1] if f > bay(x, y) else pr[i]
    # great storm oval with a swirl tail (on the lit hemisphere)
    sx_, sy_ = 45, 50
    for (x, y) in ellm(sx_, sy_, 6, 3):
        e = ((x+.5-sx_)/6)**2+((y+.5-sy_)/3)**2
        s.p[y][x] = 9 if e > 0.55 else (10 if e > 0.2 else 2)
        if e > 0.55 and y+.5 < sy_ and bay(x, y) < .5: s.p[y][x] = 5
    s.px(44, 50, 1); s.px(45, 50, 2)
    for i in range(9):
        s.px(sx_+6+i, sy_+1-(i//4), 10 if i % 3 else 9)
    # ring shadow cast on the disc (shadow lies down-right of the front ring)
    for (x, y) in disc:
        rn, v, u = ringr(x-2, y-3)
        if 1.2 < rn < 1.86 and v >= 0 and bay(x, y) < .85:
            c = DN.get(s.p[y][x], 0); s.p[y][x] = DN.get(c, 0) if 1.35 < rn < 1.7 else c
    # terminator: deepen the night limb, then a thin cool rim on the lit limb
    for (x, y) in disc:
        lx, ly = (x+.5-cx)/R, (y+.5-cy)/R; rr = math.hypot(lx, ly); side = -lx*0.75-ly*0.66
        if rr > 0.9 and side < -0.25 and bay(x, y) < (rr-0.9)*8: s.p[y][x] = DN.get(s.p[y][x], 0)
        if rr > 0.95 and side > 0.15:
            s.p[y][x] = 5 if (side > 0.7 and bay(x, y) < .55) else 9
    # near half of the ring, over the disc
    for y in range(H):
        for x in range(W):
            rn, v, u = ringr(x, y)
            if v >= 0:
                c = ringcol(rn, x, y, u)
                if c is not None:
                    if (x, y) not in disc and u > R*0.9 and bay(x, y) < .5: c = DN.get(c, c)
                    s.p[y][x] = c

    # ---- far city in haze (smaller towers, violet, few windows)
    def tower_row(base, lo, hi, x0, x1, body, cap, wins, p, wmin, wmax):
        x = x0
        while x < x1:
            w = r.randint(wmin, wmax); h = r.randint(lo, hi); xe = min(x1, x+w-1); top = base-h
            s.rect(x, top, xe, base, body)
            if w >= 5 and r.random() < .5:
                t2 = top-r.randint(2, 5); s.rect(x+1, t2, xe-1, top, body)
                if cap is not None: s.rect(x+1, t2, xe-1, t2, cap)
                if r.random() < .6: s.line((x+xe)//2, t2-1, (x+xe)//2, t2-r.randint(2, 5), body)
            if cap is not None: s.rect(x, top, xe, top, cap)
            for yy in range(top+2, base-1, 3):
                for xx in range(x+1, xe, 2):
                    if r.random() < p: s.px(xx, yy, r.choice(wins))
            x += w + r.choice((0, 1, 1, 2))
    tower_row(SKYB, 6, 20, 0, W, 2, 10, [10, 10, 9], .12, 3, 7)
    for y in range(SKYB-14, SKYB+1):          # ground haze over the far city
        for x in range(W):
            if s.p[y][x] in (2, 1) and bay(x, y) < ((y-(SKYB-14))/14)**1.4*0.4: s.p[y][x] = UP[s.p[y][x]]

    # ---- twin spires, backlit by the planet
    spm = set()
    def spire(ax, tip, bw, sd):
        m = set()
        for y in range(tip, H):
            t = (y-tip)/(SKYB-tip); hw = 0.6+bw*min(1.0, t)**1.15
            for (yc, add) in ((0.28, 1.0), (0.5, 2.0), (0.7, 1.0)):
                if abs(y-(tip+(SKYB-tip)*yc)) <= 1: hw += add
            for x in range(int(round(ax-hw)), int(round(ax+hw))+1): m.add((x, y))
        m = {(x, y) for (x, y) in m if 0 <= x < W and 0 <= y < H}
        spm.update(m)
        # body: left facet 1 (faces the planet's light), right facet 0, ordered seam
        for (x, y) in m:
            s.p[y][x] = 1 if (x < ax or (x == ax and bay(x, y) < .5)) else 0
        # rim light: brighter where the neighbour outside is lit planet/ring
        out = {}
        for (x, y) in m:
            for dx in (-1, 1):
                if (x+dx, y) not in m:
                    nb = s.g(x+dx, y)
                    if nb in (9, 5): c = 9
                    elif nb == 10: c = 10 if bay(x, y) < .7 else 9
                    else: c = 2 if dx < 0 else 1
                    out[(x, y)] = c
            if (x, y-1) not in m: out[(x, y)] = 9
        for (x, y), c in out.items(): s.p[y][x] = c
        # ribs: dark structural rings with lit top edges
        for (yc, add) in ((0.28, 1.0), (0.5, 2.0), (0.7, 1.0)):
            yy = int(tip+(SKYB-tip)*yc)
            for x in range(ax-12, ax+13):
                if (x, yy-1) in m and s.g(x, yy-1) in (0, 1): s.px(x, yy-1, 10 if x < ax else 2)
                if (x, yy+1) in m and s.g(x, yy+1) in (0, 1): s.px(x, yy+1, 0)
        # window strips: twin vertical columns, lit in runs
        rw = random.Random(sd)
        # v4: 2-px tall window slots every 5 rows in the violet ramp, a few warm/cyan
        # 2x2 clusters; no long dotted 1-px neon columns through the middle
        for y in range(tip+6, SKYB-2):
            if (y+sd) % 5 not in (0, 1): continue
            hwy = 0.6+bw*min(1.0, (y-tip)/(SKYB-tip))**1.15
            cols = [ax] if hwy < 3 else [ax-2, ax+2]
            for i, xx in enumerate(cols):
                if s.g(xx, y) not in (0, 1): continue
                k = ((y//5)*3+i*5+sd) % 9
                if k < 4: c = 10 if xx <= ax else 2
                elif k < 6: c = 9 if xx <= ax else 10
                elif k == 6 and hwy >= 3: c = 13 if xx < ax else 7
                else: c = 1
                s.px(xx, y, c)
                if c in (13, 7) and s.g(xx+1, y) in (0, 1): s.px(xx+1, y, c)
        # antenna mast with red beacons, one gold mid light
        s.line(ax, tip-1, ax, tip-9, 0); s.px(ax, tip-1, 2)
        s.px(ax, tip-10, 6); s.px(ax-1, tip-10, 1); s.px(ax+1, tip-10, 1)
        s.px(ax, tip-5, 6); s.line(ax-2, tip-6, ax+2, tip-6, 0); s.px(ax-2, tip-6, 6); s.px(ax+2, tip-6, 6)
    spire(43, 12, 8.5, 1); spire(78, 18, 8.5, 4)
    # sky-bridge between the spires
    s.rect(46, 61, 75, 63, 0); s.line(46, 61, 75, 61, 10)
    for x in range(49, 73, 6): s.px(x, 62, 13); s.px(x+1, 62, 13)   # warm window pairs
    s.line(46, 64, 75, 64, 1)

    # ---- mid city (dark violet blocks, warm and cyan windows)
    x = 14
    while x < 106:
        w = r.randint(5, 10); h = r.randint(4, 12); xe = min(105, x+w-1); top = 84-h
        if any(s.g(xx, 84-h) == 0 and (xx, 84-h) in spm for xx in range(x, xe+1)) and h < 8: h += 3; top = 84-h
        for yy in range(top, 87):
            for xx in range(x, xe+1):
                if (xx, yy) not in spm or yy > 80: s.px(xx, yy, 1)
        for xx in range(x, xe+1):
            if (xx, top) not in spm: s.px(xx, top, 2)
        for yy in range(top+2, 84, 2):
            for xx in range(x+1, xe, 2):
                if (xx, yy) not in spm and r.random() < .28: s.px(xx, yy, r.choice((3, 3, 9, 13, 10)))
        x += w + r.choice((0, 1))

    # ---- edge towers (near, black, rim-lit toward the middle, signs)
    for (x0, x1, top, cols, side) in ((0, 12, 24, [3, 9, 10], 1), (13, 19, 54, [7, 10], 1),
                                      (106, 111, 50, [9, 10], -1), (112, 119, 18, [7, 3, 10], -1)):
        b = rectm(x0, top, x1, 87) | rectm(x0+2, top-4, x1-2, top)
        s.put(b, 0)
        for (x, y) in b:
            if side > 0 and (x+1, y) not in b: s.p[y][x] = 10 if bay(x, y) < .55 else 2
            if side < 0 and (x-1, y) not in b: s.p[y][x] = 10 if bay(x, y) < .55 else 2
            if (x, y-1) not in b: s.p[y][x] = 2
        for yy in range(top+3, 85, 3):
            for xx in range(x0+1, x1, 2):
                if s.g(xx, yy) == 0:
                    s.px(xx, yy, r.choice(cols) if r.random() < .3 else 1)
    s.line(5, 19, 5, 9, 0); s.px(5, 8, 6); s.line(116, 13, 116, 4, 0); s.px(116, 3, 6)
    # neon signs (15 flickers), compact, on the edges
    def vsign(x, y, h, c, glyph):
        s.rect(x-1, y-1, x+3, y+h, 0); s.rect(x, y, x+2, y+h-1, c)
        rg = random.Random(x*31+y)
        for yy in range(y+1, y+h-1, 3):
            pat = rg.choice(((1, 0), (1, 1), (0, 1)))
            if pat[0]: s.px(x+1, yy, glyph)
            if pat[1]: s.px(x+1, yy+1, glyph)
        for yy in range(y, y+h):                       # glow spill on the wall
            if s.g(x-2, yy) in (0, 1) and bay(x-2, yy) < .4: s.px(x-2, yy, 2)
            if s.g(x+4, yy) in (0, 1) and bay(x+4, yy) < .4: s.px(x+4, yy, 2)
    vsign(3, 33, 17, 15, 4)
    vsign(113, 28, 13, 7, 4)
    s.rect(107, 58, 110, 60, 15); s.px(108, 59, 4)

    # ======== v4 street level ========
    # ---- elevated rail deck (thinner, higher), car light streaks
    DY = 83
    s.rect(0, DY, W-1, DY+2, 1); s.line(0, DY, W-1, DY, 10); s.line(0, DY+3, W-1, DY+3, 0)
    s.line(0, DY-2, W-1, DY-2, 2)
    for x in range(1, W, 4): s.px(x, DY-1, 2)                         # guard rail posts
    for x in range(0, W, 9): s.px(x, DY+2, 2)
    cars = ((30, DY+1, 1, 3), (58, DY+1, 1, 3), (100, DY+1, 1, 3),
            (44, DY+2, -1, 6), (84, DY+2, -1, 6), (14, DY+2, -1, 6))
    for (x, y, d, c) in cars:
        for i in range(1, 9):
            if bay(x-d*i, y) < 1-i/9: s.px(x-d*i, y, c)
        s.px(x, y, 4 if c == 3 else 6); s.px(x+d, y, 5 if c == 3 else 6)

    SY = 101                    # kerb row; sidewalk 99-100; shop floor line 98
    TOP = DY+4                  # 87: under-deck shadow starts
    s.rect(0, TOP, W-1, SY, 0)
    for y in range(TOP, TOP+3):                                       # deck shadow lifts slowly
        for x in range(W):
            if bay(x, y) < (y-TOP)*0.12: s.p[y][x] = 1

    def glow(cx, cy, rx, ry, lv, M, only=(0, 1, 12)):
        s.lift(cx, cy, rx, lv, M, only=set(only), sy=ry/rx)
    WARMUP = {0:1, 1:2, 12:2, 2:10}
    PINKUP = {0:1, 1:2, 12:2, 2:10, 10:9}
    CYANUP = {0:1, 1:14, 12:14, 2:14, 14:5}

    def figure(x, yb, h=8, c=0, umb=None, uw=3):
        """standing person, feet on row yb, head at the top; umb: umbrella colour"""
        top = yb-h+1
        s.rect(x, top, x+1, top+1, c)                                 # head
        s.rect(x-1 if h > 6 else x, top+2, x+1, yb-2, c)                # coat
        s.px(x, yb-1, c); s.px(x+1, yb, c); s.px(x-1 if h > 6 else x, yb, c)   # legs
        if umb is not None:
            yu = top-1
            s.line(x-uw, yu, x+1+uw, yu, umb)
            s.line(x-uw+1, yu-1, x+uw, yu-1, umb); s.line(x-uw+2, yu-2, x+uw-1, yu-2, umb)
            s.px(x-uw, yu+1, umb); s.px(x+1+uw, yu+1, umb)               # drip tips
            hl = 5 if umb in (7, 15, 9) else 10
            s.px(x-uw+2, yu-1, hl)                                       # lit edge (single px, not gold)
            s.px(x+1, yu, 0); s.px(x+1, yu+1, 0)                          # handle

    def steam(x, y0, h, sd, w=2.0, dens=0.55):
        rs = random.Random(sd)
        ph = rs.uniform(0, 6)
        for k in range(h):
            y = y0-k; t = k/h
            cx = x+math.sin(t*5.5+ph)*(1.5+3*t); hw_ = w+t*4
            for xx in range(int(cx-hw_)-1, int(cx+hw_)+2):
                u = abs(xx+.5-cx)/hw_
                if u > 1 or not (0 <= xx < W and 0 <= y < H): continue
                puff = 0.5+0.5*math.sin(k*0.9+xx*0.7+ph)
                lv = dens*(1-u*u)*(1-t)**0.8*(0.55+0.45*puff)
                c = s.p[y][xx]
                if c in (0, 1, 12, 2) and bay(xx, y) < lv:
                    s.p[y][xx] = 5 if (lv > 0.42 and bay(xx+1, y+2) < .5) else 14

    # ---- A: noodle bar (x0-16), deep, warm, striped awning, lanterns, holo bowl above
    s.rect(0, 89, 16, 98, 12)
    for y in range(91, 98):                                           # warm interior, brighter at the top
        for x in range(1, 16):
            f = 1-(y-91)/7
            s.p[y][x] = 13 if bay(x, y) < 0.35+0.6*f else 6
    s.rect(1, 95, 15, 98, 0); s.line(1, 95, 15, 95, 10)                # counter, lit edge
    for x in (4, 13): s.rect(x, 92, x+1, 94, 0); s.rect(x, 91, x+1, 91, 0)  # cooks / customers
    s.rect(8, 93, 9, 94, 0); s.px(8, 92, 0); s.px(9, 92, 0)
    for x in (3, 7, 11, 15): s.px(x, 96, 1); s.px(x, 97, 1)            # stools
    for x in range(0, 17):                                            # awning, 2 stripes deep, scalloped
        st_ = 15 if (x//2) % 2 == 0 else 9
        s.px(x, 88, 10 if (x//2) % 2 else 2); s.px(x, 89, st_); s.px(x, 90, st_)
        if x % 2 == 0: s.px(x, 91, st_)
    for x in range(1, 16, 5):                                         # noren cloth strips
        s.rect(x, 92, x+1, 93, 2)
    for lx in (2, 9, 16):                                             # red paper lanterns
        s.rect(lx, 92 if lx != 9 else 91, lx+1, (93 if lx != 9 else 92), 6)
    s.rect(17, 89, 17, 98, 0)
    # holo bowl sign floating off the left tower (cyan, scanlined, 14 haze)
    glow(8, 73, 11, 8, .55, CYANUP, only=(0, 1, 2, 3, 9, 10, 7, 12, 13))
    bowl = {(x, y) for (x, y) in ellm(8, 72, 7, 6.5) if y >= 72}
    for (x, y) in bowl:
        e = ((x+.5-8)/7)**2+((y+.5-72)/6.5)**2
        c = 7 if (y % 2 == 0 or e > 0.7) else 14
        if (x+.5) < 5 and y % 2 == 0 and e < 0.7: c = 5
        s.p[y][x] = c
    s.line(1, 72, 15, 72, 5); s.line(2, 71, 14, 71, 7)                # rim
    s.rect(6, 79, 10, 79, 7)                                          # foot
    s.line(10, 70, 13, 65, 15); s.line(11, 70, 14, 65, 15)            # chopsticks (2 px)
    for (x, y) in ((5, 68), (6, 66), (5, 64), (9, 67), (8, 65)):    # steam glyph above the bowl
        s.px(x, y, 14)
    s.px(5, 69, 7); s.px(9, 69, 7)
    steam(14, 88, 16, 81, w=1.6, dens=.6)                             # kitchen steam out of the vent
    s.rect(13, 87, 15, 87, 2)

    # ---- B: alley stair (x18-24) with a green vertical sign
    s.rect(18, 89, 24, 98, 0)
    for k in range(5):                                                # stairs going up into the dark
        y = 97-k*2; s.line(20+k, y, 24, y, 2 if k < 3 else 1)
    s.rect(18, 87, 19, 97, 0); s.rect(18, 88, 19, 96, 8)               # sign, 2 px wide
    for y in (89, 92, 95): s.px(18, y, 0)
    glow(19, 92, 6, 7, .45, {0:1, 1:2, 12:2}, only=(0, 1, 12))

    # ---- deck pillars between shop groups (they sit in front)
    def pillar(x):
        s.rect(x, TOP, x+2, 100, 0); s.line(x, TOP, x, 100, 2); s.px(x+2, TOP, 1)
        for y in range(TOP+2, 99, 4): s.px(x+1, y, 1)

    # ---- C: konbini (x27-43): bright glass, shelves, two silhouettes and an umbrella
    s.rect(26, 87, 43, 88, 14); s.line(26, 89, 43, 89, 7)               # fascia: lit sign band
    for x in range(28, 42, 4): s.rect(x, 87, x+1, 88, 5)
    for y in range(90, 99):
        for x in range(27, 43):
            f = (y-90)/8
            s.p[y][x] = 5 if bay(x, y) < 0.9-f*0.7 else 14
    for y in (93, 96):
        s.line(27, y, 42, y, 14); s.line(27, y+1, 42, y+1, 2)
        for x in range(28, 42, 3):
            s.px(x, y-1, (8, 15, 13, 7)[(x//3+y) % 4]); s.px(x+1, y-1, (8, 15, 13, 7)[(x//3+y) % 4])
    s.line(35, 90, 35, 98, 14); s.line(26, 89, 26, 98, 0); s.line(43, 89, 43, 98, 0)
    figure(30, 100, 9)
    figure(39, 100, 8, umb=15, uw=3)

    # ---- D: closed shutter (x47-54), one lamp, a pink tag
    s.rect(46, 89, 55, 98, 0)
    for y in range(90, 98): s.line(47, y, 54, y, 2 if y % 2 else 1)
    s.rect(49, 93, 51, 94, 15); s.px(52, 94, 15); s.px(50, 95, 9)      # graffiti tag
    s.rect(50, 88, 51, 88, 3)                                          # lamp (2 px gold)
    glow(51, 92, 7, 6, .45, {1:2, 2:10, 0:1}, only=(0, 1, 2))
    s.rect(50, 88, 51, 88, 3)

    # ---- E: arcade (x57-76): pink marquee with chase lights, deep dark hall, cabinet screens
    s.rect(56, 86, 77, 90, 15)
    s.line(56, 86, 77, 86, 9); s.line(56, 90, 77, 90, 2)
    for x in range(58, 76, 4): s.rect(x, 88, x+1, 88, 4 if (x//4) % 2 else 3)  # chase lights (pairs)
    s.rect(57, 91, 76, 98, 12)
    for y in range(91, 99):                                           # hall gets darker toward the back/top
        for x in range(57, 77):
            if bay(x, y) < 0.4-(y-91)*0.05: s.p[y][x] = 1
    for i, x in enumerate(range(58, 76, 5)):                          # cabinets with glowing screens
        scr = (7, 8, 9, 13)[i % 4]
        s.rect(x, 92, x+2, 98, 2); s.rect(x, 92, x+2, 92, 10)
        s.rect(x, 93, x+1, 94, scr); s.px(x+2, 93, 5 if scr in (7, 8) else 9)
        s.line(x, 96, x+2, 96, 1)
        glow(x+1, 94, 3.5, 3, .5, {12:2, 1:2, 0:1}, only=(12, 1, 0))
    figure(62, 98, 6); figure(71, 98, 7)                              # players (dark against the screens)

    # ---- F: vending machines (x80-86)
    s.rect(79, 89, 87, 98, 0)
    for (x, c, d) in ((80, 5, 14), (84, 7, 14)):
        s.rect(x, 90, x+2, 98, c)
        for y in (92, 94, 96): s.line(x, y, x+2, y, d)
        s.px(x+2, 97, 0)
    glow(83, 94, 8, 7, .45, CYANUP, only=(0, 1, 12))

    # ---- G: bar (x89-103): protruding awning, red neon sign, warm window, two drinkers
    s.rect(88, 87, 103, 98, 1)
    s.rect(92, 87, 99, 92, 0)                                         # neon cocktail-glass sign
    glass = ((93,88),(94,88),(95,88),(96,88),(97,88),(98,88),(94,89),(95,89),(96,89),(97,89),
             (95,90),(96,90),(95,91),(96,91),(94,92),(95,92),(96,92),(97,92))
    glow(95.5, 90, 9, 5, .5, {0:1, 1:2, 2:10, 12:2}, only=(0, 1, 2, 12))
    s.rect(92, 87, 99, 92, 0)
    for (a_, b_) in glass: s.px(a_, b_, 6)
    s.px(97, 87, 8); s.px(98, 87, 8)                                  # olive pick (green pair)
    s.px(95, 89, 15); s.px(96, 89, 15)
    for y in range(93, 95):                                           # awning slants out toward us
        x0 = 88-(y-93); x1 = 103+(y-93)
        s.line(x0, y, x1, y, 9 if y == 93 else 10)
    for x in range(87, 106, 2): s.px(x, 95, 2)                         # scallop
    s.rect(89, 95, 102, 98, 0)
    for y in range(96, 99):
        for x in range(90, 102):
            s.p[y][x] = 13 if bay(x, y) < 0.8-(y-96)*0.25 else 6
    s.rect(92, 96, 93, 98, 0); s.rect(98, 97, 99, 98, 0)               # drinkers' heads/shoulders
    s.px(91, 98, 0); s.px(94, 98, 0); s.px(97, 98, 0); s.px(100, 98, 0)

    # ---- H: subway entrance (x106-119) with a cyan M box, stairs down, umbrellas
    s.rect(105, 87, 119, 98, 0)
    s.rect(107, 88, 111, 92, 7); s.rect(108, 89, 110, 91, 0)
    s.px(108, 89, 7); s.px(110, 89, 7); s.px(109, 90, 7)             # M glyph cut in
    glow(109, 90, 7, 6, .5, CYANUP, only=(0, 1, 12))
    for k in range(5):                                                # stairs down (lit from inside)
        y = 94+k; s.line(106+k, y, 113, y, 14 if k < 2 else 2)
    s.line(105, 93, 113, 93, 5)                                       # handrail
    figure(116, 100, 9, umb=7, uw=3)
    figure(111, 100, 7, umb=2, uw=2)

    for x in (24, 44, 77, 103): pillar(x)

    # ---- sidewalk (99-100) and kerb (101): spill under bright fronts
    for y in (99, 100):
        for x in range(W):
            c = s.p[y][x]
            if c in (0, 1):
                up = s.p[97][x]
                if up in (5, 13, 15, 7, 6, 9, 8) and bay(x, y) < (.55 if y == 99 else .3): s.p[y][x] = 2
                elif bay(x, y) < .25: s.p[y][x] = 1
    s.line(0, SY, W-1, SY, 2)
    for x in range(0, W, 7): s.px(x, SY, 10)

    # ---- wet street (102-111): a mirror near the kerb, then each column's dominant neon
    # smeared into a vertical streak (fading, broken by ripple rows), dark wet asphalt between
    src = [row[:] for row in s.p]
    LIT = (3, 6, 7, 15, 8, 5, 13, 9, 4, 10, 14)
    VIV = {3:9, 6:9, 7:9, 15:9, 8:8, 5:9, 13:9, 9:6, 4:9, 10:3, 14:2}   # weight: vivid neons win
    DIM = {3:13, 13:6, 6:2, 7:14, 15:10, 8:14, 5:14, 9:10, 4:5, 10:2, 14:12}
    dom = []
    for x in range(W):
        cnt = {}
        for y in range(86, 99):
            c = src[y][x]
            if c in LIT: cnt[c] = cnt.get(c, 0)+VIV[c]
        if cnt:
            c = max(cnt, key=lambda k: cnt[k]); dom.append((c, min(1.0, cnt[c]/(9*7.0))))
        else: dom.append((None, 0.0))
    for y in range(SY+1, H):
        d = y-SY
        for x in range(W):
            if d <= 2:
                c = src[SY-d-1][x]
                c2 = c if c in LIT else {0:0, 1:12, 2:12, 12:12}.get(c, 12)
            else:
                c2 = 12 if bay(x, y) < 0.32-d*0.02 else 0
                c, cov = dom[x]
                if c is not None and cov > 0.12:
                    L = 3+cov*9+((x*7) % 3)                           # streak length below the kerb
                    gap = (d % 3 == 0) and ((x+d) % 4 in (0, 1))       # ripple rows break it
                    if d < L*0.6 and not gap: c2 = c
                    elif d < L and not gap: c2 = DIM[c]
                    elif d < L+2 and bay(x, y) < .5: c2 = DIM[DIM[c]] if DIM[c] in DIM else 12
            s.p[y][x] = c2
    rr = random.Random(508)
    for gy in range(SY+3, H, 3):                                      # dark ripple dashes
        for gx in range(0, W, 13):
            x = gx+rr.randint(0, 8); L = rr.randint(3, 6)
            for i in range(L):
                if s.g(x+i, gy) in (12, 2, 14): s.px(x+i, gy, 0)
                elif s.g(x+i, gy) == 0 and i in (1, 2): s.px(x+i, gy, 12)
    # manhole steam rising over the road in front of the arcade
    s.rect(64, 105, 68, 105, 1); s.px(65, 105, 2); s.px(67, 105, 2)
    steam(66, 104, 12, 66, w=1.5, dens=.5)

    # ---- rain: sparse and subtle, dark sky only
    rn = random.Random(1008)
    for gy in range(-4, 80, 13):
        for gx in range(0, W, 11):
            if rn.random() > .32: continue
            x = gx+rn.randint(0, 10); y = gy+rn.randint(0, 12)
            for i in range(3):
                if s.g(x-i//3, y+i) in (0, 1): s.px(x-i//3, y+i, 2)

    # ---- no lone gold pixels (the game's sheen is gold): pair them or make them amber
    for y in range(H):
        for x in range(W):
            if s.p[y][x] == 3 and not any(s.g(x+a, y+b) == 3 for (a, b) in ((1,0),(-1,0),(0,1),(0,-1))):
                s.p[y][x] = 13
    return s

def meanL(path):
    im = Image.open(path).convert('RGB')
    L = [0.299*a+0.587*b+0.114*c for (a, b, c) in im.getdata()]
    return sum(L)/len(L)

if __name__ == '__main__':
    out = os.path.join(HERE, 'scene08.png')
    s = scene08(); s.save(out)
    print('meanL %.1f' % meanL(out))
    ims = [Image.open(os.path.join(HERE, n)).convert('RGB').resize((480, 448), Image.NEAREST)
           for n in ('scene08.png', 'v3/scene08.png', 'scene00.png', 'scene06.png')]
    sh = Image.new('RGB', (960, 896))
    for i, m in enumerate(ims): sh.paste(m, ((i % 2)*480, (i//2)*448))
    sh.save(os.path.join(HERE, 'preview_s08v4.png'))
