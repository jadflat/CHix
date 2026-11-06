# scene08 v3 for CHix: violet sky, a banded pink gas giant with a ring, twin black spires
# backlit by it, a hazy far city, an elevated highway with car light streaks, lit shopfronts
# and a wet street. Repaint from scratch (helpers copied from paint_c.py).
# Run: python paint_s08_v3.py   -> scene08.png, preview_s08v3.png (deterministic)
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
        12:(34,14,58), 13:(66,30,96)}
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
        for y in range(tip+5, H-1):
            hwy = 0.6+bw*min(1.0, (y-tip)/(SKYB-tip))**1.15
            cols = [ax] if hwy < 3 else [ax-2, ax+2]
            for i, xx in enumerate(cols):
                if s.g(xx, y) not in (0, 1): continue
                if y % 2 == 0: continue
                on = ((y//2+i*3+sd) % 7) < 4
                if on: s.px(xx, y, 7 if i == 0 and hwy < 3 else (3 if xx < ax else 7))
                elif rw.random() < .5: s.px(xx, y, 2)
        # antenna mast with red beacons, one gold mid light
        s.line(ax, tip-1, ax, tip-9, 0); s.px(ax, tip-1, 2)
        s.px(ax, tip-10, 6); s.px(ax-1, tip-10, 1); s.px(ax+1, tip-10, 1)
        s.px(ax, tip-5, 6); s.line(ax-2, tip-6, ax+2, tip-6, 0); s.px(ax-2, tip-6, 6); s.px(ax+2, tip-6, 6)
    spire(43, 12, 8.5, 1); spire(78, 18, 8.5, 4)
    # sky-bridge between the spires
    s.rect(46, 61, 75, 63, 0); s.line(46, 61, 75, 61, 10)
    for x in range(48, 74, 3): s.px(x, 62, 3 if x % 2 else 7)
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
                if (xx, yy) not in spm and r.random() < .28: s.px(xx, yy, r.choice((3, 3, 9, 7, 10)))
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
    s.rect(14, 62, 18, 65, 3); s.px(15, 63, 0); s.px(17, 64, 0)      # small gold sign
    s.rect(107, 58, 110, 60, 15); s.px(108, 59, 4)

    # ---- elevated highway: deck, rail, pillars, car light streaks
    DY = 86
    s.rect(0, DY, W-1, DY+3, 1); s.line(0, DY, W-1, DY, 10); s.line(0, DY+3, W-1, DY+3, 0)
    for x in range(0, W, 3): s.px(x, DY-1, 2)                         # guard rail posts
    s.line(0, DY-2, W-1, DY-2, 2)
    for x in range(0, W):
        if x % 8 == 0: s.px(x, DY+2, 2)
    for px_ in (8, 34, 60, 86, 112):                                   # pillars
        s.rect(px_-1, DY+4, px_+1, 98, 0); s.line(px_-1, DY+4, px_-1, 98, 2)
    cars = ((26, DY+1, 1, 3), (52, DY+1, 1, 3), (95, DY+1, 1, 3),
            (40, DY+2, -1, 6), (73, DY+2, -1, 6), (110, DY+2, -1, 6), (12, DY+2, -1, 6))
    for (x, y, d, c) in cars:
        for i in range(1, 9):
            if bay(x-d*i, y) < 1-i/9: s.px(x-d*i, y, c)
        s.px(x, y, 4 if c == 3 else 6); s.px(x+d, y, 5 if c == 3 else 6)

    # ---- street level under the highway: lit shopfronts, awnings, signs
    SY = 99                                                           # street (reflection) line
    s.rect(0, DY+4, W-1, SY-1, 0)
    xs = 0
    while xs < W:
        w = r.randint(7, 13); xe = min(W-1, xs+w-1)
        lit = r.choice((3, 9, 7, 3, 10))
        aw = r.choice((15, 10, 3, 7))
        s.line(xs+1, 92, xe-1, 92, aw if r.random() < .6 else 2)    # awning / fascia
        for xx in range(xs+1, xe):
            s.px(xx, 93, 1); s.px(xx, 94, 2 if lit == 7 else 10)
            for yy in (95, 96): s.px(xx, yy, lit if (xx-xs) % 4 else 1)
            s.px(xx, 97, 2)
        for yy in range(94, SY-1): s.px(xs+1+((xe-xs)//2), yy, 0)  # mullion
        fx = xs+r.randint(2, max(2, w-3)); s.px(fx, 95, 0); s.px(fx, 96, 0); s.px(fx, 97, 0)  # figure
        s.line(xs, 90, xs, SY-1, 1)
        xs = xe+r.choice((2, 3))
    for px_ in (8, 34, 60, 86, 112):
        s.rect(px_-1, DY+4, px_+1, SY-1, 0); s.line(px_-1, DY+4, px_-1, SY-1, 2)
    # light spill under the deck
    for y in range(DY+4, 92):
        for x in range(W):
            if s.p[y][x] == 0 and bay(x, y) < (y-(DY+3))/8*0.35: s.p[y][x] = 1
    s.rect(0, SY-1, W-1, SY-1, 2)                                     # kerb

    # ---- wet street: reflection in 12/13, light streaks keep their colour, fading
    src = [row[:] for row in s.p]
    REF = {0:0, 1:12, 2:13, 10:10, 9:9, 13:12, 12:12, 14:13, 5:10, 11:10, 4:9}
    SH = [0, 1, 0, -1]
    for y in range(SY, H):
        d = y-SY+1; sy = SY-1-int(d*0.62+0.5)
        sh = SH[d % 4] if d > 3 else 0
        for x in range(W):
            c = src[sy][min(W-1, max(0, x+sh))]
            if c in (3, 6, 7, 15, 8) and (d < 3 or bay(x, y) < 1.0-d/13): c2 = c
            elif c in (3, 6, 7, 15, 8): c2 = 10 if c in (3, 15) else 13
            else:
                c2 = REF.get(c, c)
                if bay(x, y) < (d-3)/10: c2 = {13:12, 10:13, 12:0, 9:10}.get(c2, c2)
            s.p[y][x] = c2
    rr = random.Random(508)
    for gy in range(SY+2, H, 3):                                      # ripple dashes
        for gx in range(0, W, 16):
            x = gx+rr.randint(0, 10); L = rr.randint(3, 6)
            for i in range(L):
                if s.g(x+i, gy) in (0, 12): s.px(x+i, gy, 13)
    # sparse rain in the dark sky only
    rn = random.Random(1008)
    for gy in range(-4, 84, 12):
        for gx in range(0, W, 9):
            if rn.random() > .45: continue
            x = gx+rn.randint(0, 8); y = gy+rn.randint(0, 11)
            for i in range(3):
                if s.g(x-i//3, y+i) in (0, 1): s.px(x-i//3, y+i, 2)
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
           for n in ('scene08.png', 'v2/scene08.png', 'scene00.png', 'scene06.png')]
    sh = Image.new('RGB', (960, 896))
    for i, m in enumerate(ims): sh.paste(m, ((i % 2)*480, (i//2)*448))
    sh.save(os.path.join(HERE, 'preview_s08v3.png'))
