# scene09 v5 for CHix: v4 (paint_s09_v4.py) cleaned up. Same composition and palette.
# Changes: tractor beams and the eye beam are banded (solid core, solid body, checker edge)
# instead of Bayer speckle; lightning is a crisp 2-px bolt with solid lit cloud edges and a
# checker halo (no dithered lift); every light strip (windows, ring lights, ship ports) is
# 3 lit + 1 gap; cloud rims are solid colour bands; no painted rain or sparks (the game draws
# rain); the street reflection darkens in whole rows; a final pass removes orphan pixels.
# Run: python paint_s09_v5.py   -> scene09.png, preview_s09v5.png (v4 left, v5 right)
import math, random, os
from PIL import Image
W, H = 120, 112
B4 = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]
def bay(x, y): return (B4[int(y) & 3][int(x) & 3] + 0.5) / 16.0

# fixed slots 0,3,4,5,6,7,8,11,14,15 (game meaning); free 1,2,9,10,12,13 per scene
FIXED = {0:(4,4,12),3:(255,200,60),4:(255,255,255),5:(200,225,255),6:(255,80,60),
         7:(40,230,255),8:(60,255,120),11:(235,238,255),14:(90,100,160),15:(255,60,200)}
PAL = {
 # 07 storm-blue harbour: navy ramp 1<12<2<10, fire 9 (ember) 13 (flame orange)
 7: {1:(10,16,38),12:(24,36,68),2:(44,62,102),10:(84,112,156),9:(96,36,54),13:(244,132,50)},
 # 08 violet sky: ramp 1<12<2<10<9<13 (planet + city)
 8: {1:(20,8,42),12:(42,16,78),2:(78,30,116),10:(130,54,156),9:(204,98,180),13:(255,176,218)},
 # 09 blood storm: ramp 1<12<2<10<9<13 (clouds, fire)
 9: {1:(36,6,30),12:(94,12,50),2:(172,30,104),10:(238,90,104),9:(252,142,62),13:(255,214,146)},
}
BRIGHT = {3,4,5,6,7,8,11,15}
# one step brighter under cool (neon/moon/lightning) and warm (fire) light, one step darker
COOL = {
 7: {0:1,1:12,12:2,2:10,10:5,14:5,9:13,13:3,6:13,3:4,5:11,11:4,7:5,15:5,8:5},
 8: {0:1,1:12,12:2,2:10,10:9,9:13,13:11,14:5,5:11,11:4,7:5,15:9,8:7,6:13,3:4},
 9: {0:1,1:12,12:14,2:14,10:5,14:5,9:13,13:11,5:11,11:4,7:5,15:5,6:13,3:4,8:7},
}
WARM = {
 7: {0:1,1:9,12:9,2:9,10:13,14:13,9:6,6:13,13:3,3:4,5:4,7:5,15:13,8:3,11:4},
 8: {0:1,1:12,12:2,2:10,10:9,9:13,13:3,14:9,6:13,3:4,5:11,7:5,15:9,8:3,11:4},
 9: {0:1,1:12,12:2,2:10,10:9,9:13,13:3,3:4,6:13,14:5,5:11,7:5,15:13,8:3,11:4},
}
DARK = {
 7: {0:0,1:0,12:1,2:12,10:2,14:2,5:10,11:5,4:5,9:1,13:9,6:9,3:13,7:7,15:15,8:8},
 8: {0:0,1:0,12:1,2:12,10:2,9:10,13:9,14:2,5:14,11:5,4:5,6:6,3:3,7:7,15:15,8:8},
 9: {0:0,1:0,12:1,2:12,10:2,9:10,13:9,14:2,5:14,11:5,4:5,6:10,3:9,7:7,15:15,8:8},
}

def polym(pts):
    """pixels whose centre is inside the polygon (coordinates on pixel edges)"""
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
def mirror(pts, ax): return [(2*ax-x, y) for (x, y) in pts]

class C:
    def __init__(s, t):
        s.t = t; s.p = [[0]*W for _ in range(H)]; s.r = random.Random(t*977+13)
        s.U, s.Wm, s.D = COOL[t], WARM[t], DARK[t]
    def px(s, x, y, c):
        x = int(x); y = int(y)
        if 0 <= x < W and 0 <= y < H: s.p[y][x] = c
    def g(s, x, y):
        x = int(x); y = int(y)
        return s.p[y][x] if 0 <= x < W and 0 <= y < H else -1
    def put(s, m, c):
        for (x, y) in m:
            if 0 <= x < W and 0 <= y < H: s.p[y][x] = c
    def rect(s, x0, y0, x1, y1, c): s.put(rectm(int(x0), int(y0), int(x1), int(y1)), c)
    def line(s, x0, y0, x1, y1, c, only=None):
        x0,y0,x1,y1 = int(round(x0)),int(round(y0)),int(round(x1)),int(round(y1))
        dx, dy = abs(x1-x0), -abs(y1-y0); sx = 1 if x0<x1 else -1; sy = 1 if y0<y1 else -1; e = dx+dy
        while True:
            if only is None or s.g(x0, y0) in only: s.px(x0, y0, c)
            if x0==x1 and y0==y1: break
            e2 = 2*e
            if e2 >= dy: e += dy; x0 += sx
            if e2 <= dx: e += dx; y0 += sy
    def sky(s, y0, y1, ramp, gam=1.0):
        n = len(ramp)-1
        for y in range(y0, y1+1):
            v = max(0.0, min(n-0.001, ((y-y0)/max(1, y1-y0))**gam * n)); i = int(v)
            for x in range(W): s.p[y][x] = ramp[i+1] if v-i > bay(x, y) else ramp[i]
    def shade(s, m, f, ramp):
        """fill mask m: f(x,y) in 0..1 picks a ramp entry, ordered dither between neighbours"""
        n = len(ramp)-1
        for (x, y) in m:
            v = max(0.0, min(n-0.001, f(x, y)*n)); i = int(v)
            s.p[y][x] = ramp[i+1] if v-i > bay(x, y) else ramp[i]
    def lift(s, cx, cy, r, lv, M, only=None, sy=1.0, gam=1.0, m=None):
        for y in range(int(cy-r*sy)-1, int(cy+r*sy)+2):
            for x in range(int(cx-r)-1, int(cx+r)+2):
                if not (0 <= x < W and 0 <= y < H): continue
                if m is not None and (x, y) not in m: continue
                d = math.hypot(x+.5-cx, (y+.5-cy)/sy)
                if d >= r: continue
                c = s.p[y][x]
                if only is not None and c not in only: continue
                if bay(x, y) < lv*(1-d/r)**gam: s.p[y][x] = M.get(c, c)
    def liftm(s, m, k, M, only=None):
        for (x, y) in m:
            c = s.p[y][x]
            if (only is None or c in only) and bay(x, y) < k(x, y): s.p[y][x] = M.get(c, c)
    def beam(s, ax, ay, bx, by, w0, w1, lv, M, only=None, fall=0.6, edge=None, streak=1):
        """light cone from (ax,ay) to (bx,by), half-width w0 at the apex, w1 at the end"""
        L = math.hypot(bx-ax, by-ay); ux, uy = (bx-ax)/L, (by-ay)/L; nx, ny = -uy, ux
        pts = [(ax+nx*w0, ay+ny*w0), (bx+nx*w1, by+ny*w1), (bx-nx*w1, by-ny*w1), (ax-nx*w0, ay-ny*w0)]
        for (x, y) in polym(pts):
            px_, py_ = x+.5-ax, y+.5-ay
            t = (px_*ux+py_*uy)/L; o = abs(px_*nx+py_*ny)/(w0+(w1-w0)*max(0, t))
            c = s.p[y][x]
            if only is not None and c not in only: continue
            k = (1-o)*(1-fall*max(0, t))*lv/0.4
            if k > .62 or (k > .3 and (x+y) & 1 == 0): s.p[y][x] = M.get(c, c)
    def armor(s, m, allm, base, mid, top, rl, rl2, rr, rr2, bot=0, seam=0, grad=0.55, low=None):
        ys = [y for (_, y) in m]; y0, y1 = min(ys), max(ys); hgt = max(1, y1-y0)
        out = {}
        def bg(xx, yy): return (xx, yy) not in m and (xx, yy) not in allm
        for (x, y) in m:
            c = base; f = (y-y0)/hgt
            if bay(x, y) < (grad*0.6-f)*3.0: c = mid
            if low is not None and bay(x, y) < (f-0.62)*2.6: c = low
            if (x-2, y) not in m and (x-1, y) in m and bg(x-2, y) and bay(x, y) < .6: c = rl2
            if (x+2, y) not in m and (x+1, y) in m and bg(x+2, y) and bay(x, y) < .6: c = rr2
            if (x, y+1) not in m: c = bot if bg(x, y+1) else seam
            if (x+1, y) not in m: c = rr if bg(x+1, y) else seam
            if (x-1, y) not in m: c = rl if bg(x-1, y) else mid
            if (x, y-1) not in m: c = top if bg(x, y-1) else mid
            out[(x, y)] = c
        for (x, y), c in out.items(): s.p[y][x] = c
        allm |= m
    def windows(s, x0, x1, y0, y1, sx, sy, cols, p, dim=None, w2=False, only=None):
        s.r.random()                                   # keep v4's main rng sequence
        if not hasattr(s, 'wr'): s.wr = random.Random(4242)
        for y in range(y0, y1+1, sy):
            rp = min(.85, p*s.wr.choice((0.0, 0.6, 1.0, 1.4, 2.0, 2.6))*1.8); c = s.wr.choice(cols)
            for xs in range(x0, x1+1, 4):
                col = c if s.wr.random() < rp else dim
                if col is None: continue
                for x in range(xs, min(xs+3, x1+1)):
                    if only is None or s.g(x, y) in only: s.px(x, y, col)
    def windows_v4(s, x0, x1, y0, y1, sx, sy, cols, p, dim=None, w2=False, only=None):
        for y in range(y0, y1+1, sy):
            rp = p*s.r.choice((0.0, 0.4, 1.0, 1.0, 1.6, 2.2)); c = s.r.choice(cols)
            run = 0
            for x in range(x0, x1+1, sx):
                if only is not None and s.g(x, y) not in only: continue
                if run <= 0 and s.r.random() < rp: run = s.r.randint(1, 4)
                if run > 0:
                    run -= 1; s.px(x, y, c)
                    if w2 and (only is None or s.g(x+1, y) in only): s.px(x+1, y, c)
                elif dim is not None:
                    s.px(x, y, dim)
                    if w2 and (only is None or s.g(x+1, y) in only): s.px(x+1, y, dim)
    def flame(s, fx, fy, w, h, sd):
        ramp = [9, 6, 13, 3, 4]
        for y in range(int(fy-h), int(fy)+1):
            t = (fy-y)/h
            hw = w/2*(1-t)**0.55 + 0.4
            off = math.sin(t*4.5+sd)*w*0.18*t
            for x in range(int(fx-w), int(fx+w)+1):
                u = (x+.5-fx-off)/hw
                if abs(u) > 1: continue
                tongue = 0.5+0.5*math.sin((x-fx)*1.9+sd*2.3+t*3)
                if t > 0.35 and tongue < (t-0.35)*1.9: continue
                heat = (1-abs(u))*0.75 + (1-t)*0.7 - 0.25
                v = max(0, min(len(ramp)-1.001, heat*(len(ramp)-1))); i = int(v)
                s.px(x, y, ramp[i+1] if v-i > bay(x, y) else ramp[i])
    def bolt(s, x, y, length, seed, core=4, glow=5, branch=True):
        r = random.Random(seed); pts = [(x, y)]
        for _ in range(length):
            x += r.choice((-1, -1, 0, 1, 1, 2, -2)); y += r.choice((1, 2, 2))
            pts.append((x, y))
        for (a, b), (c, d) in zip(pts, pts[1:]): s.line(a, b, c, d, core)
        if branch:
            for k in (len(pts)//3, 2*len(pts)//3):
                bx, by = pts[k]; d = r.choice((-1, 1))
                for _ in range(r.randint(3, 6)):
                    nx_, ny_ = bx+d*r.choice((1, 2)), by+r.choice((1, 2))
                    s.line(bx, by, nx_, ny_, glow); bx, by = nx_, ny_
        return pts
    def water(s, hz, wob=1.0, stretch=0.72, ripple=2):
        src = [row[:] for row in s.p]; D = s.D; SH = [0, 1, 1, 0, -1, -1]
        for y in range(hz+1, H):
            d = y-hz; sy = max(0, hz - int(d*stretch)); sh = int(SH[d % 6]*wob*(1 if d > 2 else 0))
            for x in range(W):
                sx_ = min(W-1, max(0, x+sh)); c = src[sy][sx_]
                big = c in BRIGHT and sum(1 for (a, b) in ((sx_-1, sy), (sx_+1, sy), (sx_, sy-1), (sx_, sy+1))
                                          if 0 <= a < W and 0 <= b < H and src[b][a] in BRIGHT) >= 2
                if big:
                    c2 = c if d < 7 else D[c]
                elif c in BRIGHT:
                    c2 = D[D[c]] if d < 8 else D[D[D[c]]]
                else:
                    c2 = D.get(c, c)
                    if d % 3 != 1 or d > 10: c2 = D.get(c2, c2)
                s.p[y][x] = c2
        r = random.Random(500+s.t)
        for gy in range(hz+3, H-1, 5):
            for gx in range(0, W, 20):
                x = gx+r.randint(0, 14); y = gy+r.randint(0, 2); L = r.randint(3, 6)
                for i in range(L):
                    if s.g(x+i, y) == 0: s.px(x+i, y, ripple)
    def rain(s, c1, c2, only, cell=(7, 9), p=0.8, L=(3, 5), hz=None, splash=None):
        r = random.Random(1000+s.t)
        for gy in range(-6, H, cell[1]):
            for gx in range(0, W+6, cell[0]):
                if r.random() > p: continue
                x = gx+r.randint(0, cell[0]-1); y = gy+r.randint(0, cell[1]-1); n = r.randint(*L)
                if hz is not None and y > hz: continue
                for i in range(n):
                    xx, yy = x-i//3, y+i
                    if s.g(xx, yy) in only: s.px(xx, yy, c2 if i == n-1 else c1)
        if hz is not None and splash is not None:
            for gy in range(hz+4, H-1, 6):
                for gx in range(2, W-2, 11):
                    x = gx+r.randint(0, 6); y = gy+r.randint(0, 3)
                    if s.g(x, y) in (0, 1, 12) and s.g(x-1, y+1) in (0, 1, 12):
                        s.px(x, y, splash); s.px(x-1, y+1, splash); s.px(x+1, y+1, splash)
    def sparks(s, cx, cy, n, spread, rise, cols, seed, only=None):
        r = random.Random(seed)
        for _ in range(n):
            x = cx+r.uniform(-spread, spread); y = cy-r.uniform(0, rise)
            c = r.choice(cols)
            if only is None or s.g(x, y) in only:
                s.px(x, y, c)
                if r.random() < .5 and (only is None or s.g(x+1, y-1) in only): s.px(x+1, y-1, 9 if s.t != 8 else 10)
    def sign(s, x, y, w, h, c, glyph, halo, lv=.6, only=None):
        s.lift(x+w/2, y+h/2, max(w, h)*0.75+4, lv, halo, only=only, sy=1.0)
        s.rect(x-1, y-1, x+w, y+h, 0)
        s.rect(x, y, x+w-1, y+h-1, c)
        r = random.Random(x*31+y*7)
        if h > w:   # vertical: stacked glyph blocks
            for yy in range(y+1, y+h-1, 4):
                pat = r.choice(((1,0,1),(1,1,0),(0,1,1),(1,1,1)))
                for i, on in enumerate(pat):
                    if on and yy+i//2 < y+h-1:
                        if w >= 4: s.rect(x+1, yy+i, x+w-2, yy+i, glyph) if i != 1 else s.px(x+1+(r.random()<.5)*(w-3), yy+i, glyph)
                        else: s.px(x+1, yy+i, glyph)
        else:
            for xx in range(x+1, x+w-1, 3):
                s.px(xx, y+1, glyph);
                if h > 3: s.px(xx+1, y+h-2, glyph); s.px(xx, y+h//2, glyph)
    def save(s, path):
        im = Image.new('P', (W, H)); pal = []
        for i in range(16): pal += list(FIXED[i] if i in FIXED else PAL[s.t][i])
        im.putpalette(pal)
        im.putdata([v for row in s.p for v in row]); im.save(path)
        return im

def skyline(s, hz, lo, hi, x0, x1, body, wins, lit, wmin, wmax, dim=None, cap=None, step=(2,3)):
    x = x0
    while x < x1:
        w = s.r.randint(wmin, wmax); h = s.r.randint(lo, hi); xe = min(x1, x+w-1); top = hz-h
        s.rect(x, top, xe, hz, body)
        if w >= 6 and s.r.random() < .45:
            t2 = top-s.r.randint(2, 6); s.rect(x+2, t2, xe-2, top, body)
            if s.r.random() < .5: s.line((x+xe)//2, t2-1, (x+xe)//2, t2-s.r.randint(2, 6), body)
        if cap is not None: s.rect(x, top, xe, top, cap)
        if wins: s.windows(x+1, xe-1, top+2, hz-2, step[0], step[1], wins, lit, dim=dim, only={body})
        x += w + s.r.choice((0, 0, 1))

KEEP = {3, 4, 6, 7, 8, 15}
def despeckle(s, passes=2):
    """a pixel unlike all 8 neighbours becomes its most common 4-neighbour (checker survives)"""
    for _ in range(passes):
        src = [r[:] for r in s.p]
        for y in range(H):
            for x in range(W):
                c = src[y][x]
                if c in KEEP: continue
                nb = [src[y+b][x+a] for a in (-1, 0, 1) for b in (-1, 0, 1)
                      if (a or b) and 0 <= x+a < W and 0 <= y+b < H]
                if c in nb: continue
                n4 = [src[y+b][x+a] for (a, b) in ((1,0),(-1,0),(0,1),(0,-1)) if 0 <= x+a < W and 0 <= y+b < H]
                s.p[y][x] = max(set(n4), key=n4.count)

# smooth value noise (seeded) for cloud texture
_rn = random.Random(909)
_G = [[_rn.random() for _ in range(64)] for _ in range(64)]
def vnoise(x, y):
    xi, yi = int(math.floor(x)), int(math.floor(y)); fx, fy = x-xi, y-yi
    fx = fx*fx*(3-2*fx); fy = fy*fy*(3-2*fy)
    g = lambda a, b: _G[b & 63][a & 63]
    a = g(xi, yi)+(g(xi+1, yi)-g(xi, yi))*fx
    b = g(xi, yi+1)+(g(xi+1, yi+1)-g(xi, yi+1))*fx
    return a+(b-a)*fy
def fbm(x, y): return 0.6*vnoise(x, y)+0.3*vnoise(x*2.1+7, y*2.1+3)+0.1*vnoise(x*4.3+1, y*4.3+9)

# ======================================================================= 09 (v4)
# The final megastructure in a blood storm: layered storm clouds (lit tops, dark bellies
# above; fire-lit bellies below), crimson -> magenta -> rose -> orange sky, a crisp banded
# planet, the storm eye, lightning that lights the cloud edges, a fleet, the burning city.
BEAM9 = {0:14, 1:14, 12:14, 2:14, 10:5, 9:5, 14:5, 5:11, 13:11, 7:5, 3:4, 11:4, 6:5}
CORE9 = {0:7, 1:7, 12:7, 2:7, 14:5, 10:5, 9:5, 7:5, 5:11, 11:4, 13:11, 3:4}
def scene09():
    s = C(9); hz = 94; U, Wm = s.U, s.Wm; cx = 60
    # ---- sky: near-black crimson top, magenta, rose, orange at the horizon (Bayer between)
    s.sky(0, hz, [0, 1, 12, 2, 10, 9, 13], gam=1.55)
    # storm eye glow above the crown (cold light)
    s.lift(cx, 0, 30, .55, U, sy=0.7, only={0, 1, 12}, gam=1.4)

    # ---- banded planet, upper right, lit from the left (the eye); crisp bands, dithered terminator
    pcx, pcy, PR = 98, 19, 15
    BANDS = [13, 9, 9, 10, 13, 13, 9, 2, 10, 10, 9, 13, 2, 10]
    pm = ellm(pcx, pcy, PR, PR)
    for (x, y) in pm:
        lx, ly = (x+.5-pcx)/PR, (y+.5-pcy)/PR
        lz = math.sqrt(max(0, 1-lx*lx-ly*ly))
        lat = ly*0.96+lx*0.28
        q = (lat+1)*6.2+0.35*math.sin(lx*5+lat*4)+(fbm(lx*3+20, lat*6)-0.5)*0.9
        c = BANDS[int(q) % len(BANDS)]
        lam = -0.75*lx-0.35*ly+0.55*lz
        if lam < 0.05: c = s.D[c]
        if lam < -0.25: c = s.D[c]
        if lam < -0.5 or (lam < -0.38 and bay(x, y) < .5): c = s.D[c]
        if 0.05 > lam > -0.08 and bay(x, y) < .5: c = s.D[c]
        s.p[y][x] = c
    for (x, y) in pm:                                      # lit limb: thin pale rim, then cool halo
        if any((x+a, y+b) not in pm for (a, b) in ((1,0),(-1,0),(0,1),(0,-1))):
            lx, ly = (x+.5-pcx)/PR, (y+.5-pcy)/PR
            if -0.75*lx-0.35*ly > 0.25: s.p[y][x] = 13 if bay(x, y) < .6 else 11
    s.lift(pcx, pcy, PR+4, .45, {0:1, 1:12, 12:2}, only={0, 1, 12})
    # storm on the planet (2x3 oval, crisp)
    s.rect(91, 22, 94, 23, 13); s.px(92, 22, 9); s.px(93, 23, 2)

    # ---- storm cloud banks: puffy billows, each lit from one side, ordered dither shading
    def bank(yc, x0, x1, rmin, rmax, seed, ramp, rim, belly, light=1, gap=None, tex=0.28, jit=2.5):
        r = random.Random(seed); circ = []; x = x0
        while x < x1:
            rr = r.uniform(rmin, rmax); yy = yc+r.uniform(-jit, jit)
            if gap is None or abs(x-gap[0]) > gap[1]: circ.append((x, yy, rr))
            x += rr*r.uniform(0.85, 1.35)
        lv = {}
        for (a, b, rr) in circ:
            for y in range(int(b-rr)-1, int(b+rmax*0.8)+1):
                for x in range(int(a-rr)-1, int(a+rr)+2):
                    if not (0 <= x < W and 0 <= y < H): continue
                    inside = math.hypot(x+.5-a, y+.5-b) <= rr
                    if not (inside or (y+.5 >= b and abs(x+.5-a) <= rr)): continue
                    v = 0.5+0.5*(b-(y+.5))/rr if inside else 0.5-0.5*((y+.5)-b)/(rmax*0.8)
                    v = max(0.0, min(1.0, v))
                    if light < 0: v = 1-v
                    lv[(x, y)] = max(lv.get((x, y), 0), v) if light > 0 else max(lv.get((x, y), 0), v*0.8)
        m = set(lv)
        ybot = max(y for (_, y) in m)
        n = len(ramp)-1
        for (x, y), v in lv.items():
            v += (fbm(x*0.12+seed, y*0.22)-0.5)*tex
            if light < 0: v += max(0, (y-(ybot-4))/4)*0.3
            v = max(0.0, min(n-0.001, v*n)); i = int(v)
            c = ramp[i+1] if v-i > bay(x, y) else ramp[i]
            if (x, y-1) not in m: c = rim(x, y)
            elif (x, y+1) not in m: c = belly
            s.p[y][x] = c
        return m

    def rim_upper(x, y):                                   # cold near the eye, magenta away from it
        d = abs(x+.5-cx)
        if d < 14: return 5
        if d < 30: return 14
        return 2
    def rim_mid(x, y):
        d = abs(x+.5-cx)
        return 14 if d < 18 else 10
    def rim_low(x, y): return 12

    cl1 = bank(8, -6, 80, 7, 11, 11, [0, 1, 12, 2], rim_upper, 0, gap=(cx, 17), tex=.3)
    cl2 = bank(27, -8, 80, 7, 12, 13, [0, 1, 12, 2, 10], rim_mid, 0, gap=(cx, 8), tex=.3)
    cl2 |= bank(31, 112, W+8, 6, 9, 15, [0, 1, 12, 2, 10], rim_mid, 0, tex=.3)
    cl2 |= bank(27, 84, 108, 2.5, 3.5, 16, [1, 12, 2], rim_mid, 1, tex=.2, jit=1.0)   # wisp over the planet
    cl3 = bank(47, -6, W+6, 6, 10, 14, [1, 12, 2, 10, 9], rim_low, 13, light=-1, tex=.25)
    clouds = cl1 | cl2 | cl3

    # eye of the storm
    eye = ellm(cx, 1, 10, 4)
    for (x, y) in eye:
        d = math.hypot((x+.5-cx)/10, (y+.5-1)/4)
        s.p[y][x] = 4 if d < .35 else (11 if d < .6 else (5 if bay(x, y) < 1.1-d else 14))

    # ---- lightning (off the middle): bolts 2 px wide, cloud edges near them lit cold
    def strike(lx, ly, ln, sd, reach=11):
        pts = s.bolt(lx, ly, ln, sd, core=4, glow=5)
        for (a, b) in pts[:-1]:
            if s.g(a+1, b) not in (4, -1): s.px(a+1, b, 5)
        for (x, y) in clouds:
            dmin = min(math.hypot(x-a, y-b) for (a, b) in pts)
            if dmin > reach: continue
            edge = (x, y-1) not in clouds or (x-1, y) not in clouds or (x+1, y) not in clouds or (x, y+1) not in clouds
            c = s.p[y][x]
            if c in (4, 5, 11): continue
            if edge: s.p[y][x] = 5 if dmin < reach*0.5 else 14
            elif (dmin < 2.5 or (dmin < 4.5 and (x+y) & 1 == 0)) and c in U: s.p[y][x] = U[c]
        return pts
    strike(15, 31, 9, 7)
    strike(106, 36, 7, 9, reach=9)
    strike(31, 12, 6, 3, reach=8)

    # far fleet: tiny ships in formation, engines lit (2-px hulls on the bright sky are dark)
    for (fx, fy, d) in ((8, 40, 1), (14, 43, 1), (20, 46, 1), (96, 58, -1), (103, 61, -1), (89, 55, -1)):
        s.rect(fx, fy, fx+3, fy, 1); s.px(fx+1, fy-1, 1); s.px(fx-1 if d > 0 else fx+4, fy, 7)
        s.px(fx+(3 if d > 0 else 0), fy, 12)
    # burning city behind
    tops = []
    x = 0
    while x < W:
        w = s.r.randint(3, 8); h = s.r.randint(6, 24); xe = min(W-1, x+w-1)
        s.rect(x, hz-h, xe, hz, 1); s.rect(x, hz-h, xe, hz-h, 12); tops.append((x, xe, hz-h))
        s.windows(x+1, xe-1, hz-h+2, hz-2, 2, 3, [13, 9], .05, only={1})
        x += w+s.r.choice((0, 1))
    for (x0, xe, t) in tops:
        if s.r.random() < .3 and xe-x0 >= 4:
            fx = (x0+xe)/2
            s.lift(fx, t-3, 9, .5, Wm, only={0, 1, 12, 2, 10})
            s.flame(fx, t, xe-x0, s.r.randint(5, 9), x0*0.37)
    # haze over the far city base (orange smoke)
    for y in range(hz-10, hz+1):
        for x in range(W):
            if s.p[y][x] in (1, 12) and bay(x, y) < ((y-(hz-10))/10)*0.45: s.p[y][x] = Wm[s.p[y][x]]

    # ---- the megastructure
    def hw(y):
        if y < 14: return 1.5+y*0.07
        if y < 30: return 2.5+(y-14)*0.14
        return 4.8+(y-30)**1.5*0.024
    body = set()
    for y in range(6, hz+1):
        for x in range(int(round(cx-hw(y))), int(round(cx+hw(y)))+1): body.add((x, y))
    for sx in (-1, 1):
        body |= polym([(cx+sx*12, hz+1), (cx+sx*22, hz+1), (cx+sx*10, hz-36), (cx+sx*8, hz-30)])
    body = {(x, y) for (x, y) in body if 0 <= x < W and 0 <= y < H}
    rings = [(cx, 27, 17, 3.5, 2), (cx, 50, 40, 8.0, 3), (cx, 73, 29, 5.5, 2)]
    def platform(rc, back):
        (rx, ry, a, b, th) = rc; q2 = 0.42
        for y in range(int(ry-b)-1, int(ry+b)+th+2):
            for x in range(int(rx-a)-1, int(rx+a)+2):
                if not (0 <= x < W and 0 <= y < H): continue
                if ((y+.5-ry) < 0) != back: continue
                e = ((x+.5-rx)/a)**2+((y+.5-ry)/b)**2
                if q2 <= e <= 1:
                    c = 1 if back else (12 if bay(x, y) < .5 else 2)
                    if e > 0.84: c = (12 if back else 14) if (x+.5-rx) > -a*0.3 else (2 if back else 10)
                    if e > 0.84 and not back and (x+.5-rx) > a*0.2 and bay(x, y) < .35: c = 5
                    if e < q2+0.14: c = 0 if back else 1
                    if (x+.5-rx) < -a*0.62 and e > 0.75 and not back: c = 13 if bay(x, y) < .5 else 9
                    s.p[y][x] = c
                elif e > 1 and not back:
                    for k in range(1, th+1):
                        if ((x+.5-rx)/a)**2+((y-k+.5-ry)/b)**2 <= 1:
                            c = 0 if k == th else 1
                            if k == 1 and x % 4 != 3: c = 13                              # light strip
                            s.p[y][x] = c; break
    for rc in rings: platform(rc, True)
    # tractor beams under the great ring, lifting debris (shaded cones, no 1-px neon edges)
    for (bx, ex) in ((27, 18), (93, 102)):
        s.beam(bx, 57, ex, hz, 3, 10, .4, BEAM9, fall=.45, streak=3)
        s.beam(bx, 57, ex, hz, 1.5, 5, .38, CORE9, fall=.6, streak=3)
        for k in range(5):
            yy = 62+k*6; xx = bx+(ex-bx)*(yy-57)/(hz-57)+math.sin(k*2.3+bx)*4
            s.rect(xx, yy, xx+1, yy+1, 1); s.px(xx, yy, 5); s.px(xx+1, yy, 14)
    s.put(body, 1)
    for (x, y) in body:
        rel = (x+.5-cx)/max(1, hw(y)); c = 1
        if rel > 0.25: c = 0 if bay(x, y) < (rel-0.25)*2.2 else 1
        if rel < -0.35 and bay(x, y) < (-rel-0.35)*1.3: c = 12
        if (x-1, y) not in body: c = 9 if bay(x, y) < .7 else 10      # fire-lit left rim
        elif (x-2, y) not in body and bay(x, y) < .5: c = 2
        elif (x+1, y) not in body: c = 14 if bay(x, y) < .6 else 12   # cool right rim, dim
        elif (x, y-1) not in body: c = 10
        elif y % 6 == 0 and abs(rel) < .8 and ((x//2*7+y*3) % 13) < 2: c = 13
        elif y % 6 == 0 and abs(rel) < .8: c = 0
        s.p[y][x] = c
    for sx in (-1, 1):                                             # buttress ribs
        s.line(cx+sx*13, hz, cx+sx*9, hz-33, 12 if sx < 0 else 0)
    # the core: a shaded 3-px conduit (dark casing, dim magenta glow) with lit nodes,
    # not a 1-px cyan line
    for y in range(9, hz):
        s.px(cx-1, y, 0); s.px(cx+1, y, 0)
        s.px(cx, y, 12)
    for y in range(14, hz-2, 12):                                   # nodes: 3x2 lit blocks
        s.rect(cx-1, y, cx+1, y+1, 10); s.px(cx, y, 13); s.px(cx, y+1, 9)
        s.px(cx-2, y, 0); s.px(cx+2, y, 0)
    for sx in (-1, 1):                                             # crown prongs
        s.line(cx+sx*2, 16, cx+sx*5, 4, 0); s.line(cx+sx*3, 18, cx+sx*7, 9, 0)
        s.px(cx+sx*5, 3, 6); s.px(cx+sx*7, 8, 6)
    # beam up into the eye
    s.beam(cx, 7, cx, 0, 1.5, 4, .9, BEAM9, fall=.2, streak=3)
    s.line(cx, 0, cx, 7, 4)
    for rc in rings: platform(rc, False)
    for sx in (-1, 1):                                             # spokes to the great ring
        for k in (0.45, 0.8):
            s.line(cx+sx*(hw(50)+1), 52, cx+sx*40*k, 50+8*0.55, 0)

    # capital ships of the fleet (dark hulls against the bright mid sky)
    def capital(x, y, L, d, near=True):
        h = max(3, int(L/5))
        hull = polym([(x, y), (x+d*L*0.72, y), (x+d*L, y+h*0.55), (x+d*L*0.72, y+h), (x, y+h)])
        sup = polym([(x+d*L*0.12, y), (x+d*L*0.16, y-h*0.8), (x+d*L*0.34, y-h*0.8), (x+d*L*0.42, y)])
        m = hull | sup
        top_c, body_c, low_c = (14, 1, 10) if near else (2, 12, 10)
        s.put(m, body_c)
        for (a, b) in m:
            if (a, b-1) not in m: s.p[b][a] = top_c if bay(a, b) < .7 else 5
            elif (a, b+1) not in m: s.p[b][a] = low_c
            elif (a, b+2) not in m: s.p[b][a] = 0
            elif (a-d, b) not in m and near: s.p[b][a] = 12
        for i in range(3, int(L*0.7), 4):
            s.px(x+d*i, y+h//2, 13); s.px(x+d*(i+1), y+h//2, 13); s.px(x+d*(i+2), y+h//2, 13)
        st_ = x-d
        s.lift(st_-d, y+h/2, h+4, .6, U, only={0, 1, 12, 2, 10})
        for j in range(y+1, y+h): s.px(st_, j, 5); s.px(st_-d, j, 7)
        s.px(st_, y+h//2, 4)
        s.px(x+d*int(L*0.28), int(y-h*0.8)-1, 6)
    capital(4, 36, 30, 1)
    capital(116, 42, 22, -1)
    capital(88, 64, 11, -1, near=False)
    capital(26, 60, 9, 1, near=False)

    # ---- near foreground: dark towers with signs, fire and sparks
    for (x0, x1, top) in ((0, 13, 52), (14, 19, 72), (104, 110, 66), (111, 119, 50)):
        b = rectm(x0, top, x1, hz) | rectm(x0+2, top-5, x1-2, top)
        s.put(b, 0)
        for (x, y) in b:
            if (x+1, y) not in b and x < cx: s.p[y][x] = 9 if bay(x, y) < .7 else 2
            if (x-1, y) not in b and x > cx: s.p[y][x] = 14 if bay(x, y) < .6 else 12
            if (x, y-1) not in b: s.p[y][x] = 10
        s.windows(x0+1, x1-1, top+2, hz-2, 2, 3, [3, 13, 15], .14, dim=1, only={0}, w2=True)
    s.line(115, 45, 115, 36, 0); s.px(115, 35, 6)
    s.lift(7, 46, 12, .5, Wm, only={0, 1, 12, 2, 10}); s.flame(7, 47, 9, 12, 1.3)
    s.sign(2, 58, 4, 18, 15, 4, U, lv=.5, only={0, 1, 12, 2, 10, 9})
    s.sign(113, 56, 4, 16, 8, 0, U, lv=.5, only={0, 1, 12, 2, 10, 9})
    s.sign(95, 78, 8, 4, 7, 0, U, lv=.5, only={0, 1, 12, 2, 10, 9})
    s.rect(0, hz, W-1, hz, 10)
    s.water(hz, .9, ripple=12)
    despeckle(s)
    # no lone gold pixels (the game's moving sheen is gold): they become peach
    for y in range(H):
        for x in range(W):
            if s.p[y][x] == 3 and not any(s.g(x+a, y+b) == 3 for (a, b) in ((1,0),(-1,0),(0,1),(0,-1))):
                s.p[y][x] = 13
    return s

if __name__ == '__main__':
    out = os.path.dirname(os.path.abspath(__file__))
    scene09().save(os.path.join(out, 'scene09.png'))
    ims = [Image.open(os.path.join(out, n)).convert('RGB').resize((480, 448), Image.Resampling.NEAREST)
           for n in ('v4/scene09.png', 'scene09.png')]
    sh = Image.new('RGB', (968, 448))
    for i, m in enumerate(ims): sh.paste(m, (i*488, 0))
    sh.save(os.path.join(out, 'preview_s09v5.png'))
