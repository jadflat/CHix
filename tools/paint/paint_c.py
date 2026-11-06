# Painter C (v2): scenes 07, 08, 09 for CHix, the late, grandest stages.
# Run: python paint_c.py   (deterministic: seeded random, ordered Bayer dither only)
# Writes scene07..09.png (120x112, mode P, 16 colours), preview_c2.png, crops_c2.png.
# v1 (the rough first pass) is kept in tools/paint/v1/.
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
 9: {1:(26,6,22),12:(58,14,40),2:(100,26,50),10:(160,48,46),9:(230,104,48),13:(255,186,100)},
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
            k = lv*(1-o*o)*(1-fall*t)
            if edge is not None and o > 0.86 and bay(x, y) < 0.55*(1-fall*t): s.p[y][x] = edge; continue
            if bay(x, y//streak) < k: s.p[y][x] = M.get(c, c)
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
        for (a, b) in pts[1:-1:2]:
            for (dx, dy) in ((-1, 0), (1, 0)):
                if s.g(a+dx, b+dy) not in (core, -1) and r.random() < .5: s.px(a+dx, b+dy, glow)
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
                    c2 = c if bay(x, y) < 1.05-d/18 else D[c]
                elif c in BRIGHT:
                    c2 = D[D[c]] if d < 8 else D[D[D[c]]]
                else:
                    c2 = D.get(c, c)
                    if bay(x, y) < (0.75 if d % 2 else 0.4)+d/40: c2 = D.get(c2, c2)
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
        im.putpalette(pal + [0]*(768-len(pal)))
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

# ======================================================================= 07
# Harbour at night: a giant mecha wades in, lit by the moon behind its head and the burning docks.
def scene07():
    s = C(7); hz = 84; U, Wm = s.U, s.Wm
    s.sky(0, hz, [0, 1, 12], gam=1.25)
    # cool haze low over the water on the right, fire glow low on the left
    for y in range(50, hz+1):
        for x in range(W):
            k = ((y-50)/(hz-50))**1.5
            if x > 40 and bay(x, y) < k*0.55*min(1, (x-40)/20): s.p[y][x] = U.get(s.p[y][x], s.p[y][x])
    s.lift(18, hz, 46, .75, Wm, only={0, 1, 12}, sy=0.75, gam=1.3)
    # moon behind the head
    mx, my, mr = 76, 15, 13
    s.lift(mx, my, mr+16, .45, U, only={0, 1, 12}); s.lift(mx, my, mr+6, .7, U, only={0, 1, 12, 2})
    disc = ellm(mx, my, mr, mr)
    s.shade(disc, lambda x, y: 0.55+0.5*((x+.5-mx)/mr*0.55-(y+.5-my)/mr*0.45), [2, 10, 5, 11])
    for (ox, oy, rr) in ((-5, -3, 2.6), (4, 4, 3.2), (6, -6, 1.7), (-3, 6, 2.0), (-8, 3, 1.4)):
        cm = ellm(mx+ox, my+oy, rr, rr*0.85)
        for (x, y) in cm:
            if (x, y) in disc: s.p[y][x] = 14 if (x+.5-mx-ox) < 0.6 else 10
        for (x, y) in cm:
            if (x+1, y) not in cm and (x+1, y) in disc: s.p[y][x+1] = 11
    # searchlights sweeping the sky from the far shore
    s.beam(116, hz-10, 96, 0, 0.5, 5, .45, U, only={0, 1, 12, 2}, fall=.75)
    s.beam(50, hz-6, 34, 0, 0.5, 4, .35, U, only={0, 1, 12, 2}, fall=.8)
    # smoke columns from the docks, drifting left (fire-lit underneath, moonlit on top)
    def billow(cx, cy, r, t):
        for y in range(int(cy-r)-1, int(cy+r)+2):
            for x in range(int(cx-r)-1, int(cx+r)+2):
                d = math.hypot(x+.5-cx, y+.5-cy)
                if d > r or not (0 <= x < W and 0 <= y < H): continue
                if d > r-1.4 and bay(x, y) < .45: continue
                nx, ny = (x+.5-cx)/r, (y+.5-cy)/r
                warm = (0.5+0.5*(-nx*0.3+ny*0.95))*(1-t*0.9)
                cool = 0.5+0.5*(nx*0.6-ny*0.75)
                c = 12
                if bay(x, y) < (0.55-cool)*1.6: c = 1
                if bay(x, y) < (cool-0.62)*2.2: c = 2
                if bay(x, y) < (warm-0.5)*2.0: c = 9
                if warm > .8 and bay(x, y) < (warm-.8)*2.5: c = 6
                s.p[y][x] = c
    def plume(x0, y0, dx, dy, n, r0, r1, sd):
        pts = []
        for k in range(n):
            t = k/(n-1); pts.append((x0+dx*t+2.5*math.sin(t*6+sd), y0-dy*t, r0+(r1-r0)*t, t))
        for (a, b, r, t) in reversed(pts): billow(a, b, r, t)
    plume(10, 60, -8, 58, 11, 5, 11, 0.5)
    plume(24, 56, -12, 46, 9, 4, 9, 4.0)
    plume(42, 68, -16, 40, 8, 3, 7, 2.0)
    # far city across the water: low hazy blocks, a few lights
    skyline(s, hz, 3, 11, 44, W, 12, [7, 13, 3], .05, 3, 7, step=(2, 3))
    for y in range(hz-12, hz+1):
        for x in range(44, W):
            if s.p[y][x] == 12 and bay(x, y) < (y-(hz-12))/12*0.6: s.p[y][x] = 2
    # ---- the mecha
    M = set(); A = dict(base=12, mid=2, low=1, top=10, rl=13, rl2=9, rr=7, rr2=10, grad=0.5)
    s.armor(polym([(55, 27), (59, 23), (46, 5), (42, 8)]), M, **A)            # shoulder cannon
    s.armor(polym([(39, 6), (44, 1), (49, 5), (44, 10)]), M, **A)
    s.armor(polym([(62, 24), (86, 24), (90, 30), (88, 42), (82, 49), (66, 49), (60, 42), (58, 30)]), M, **A)
    s.armor(rectm(67, 48, 80, 54), M, **A)
    for ax in (0, 1):
        f = (lambda p: p) if ax == 0 else (lambda p: mirror(p, 74))
        s.armor(polym(f([(63, 57), (72, 57), (71, 70), (64, 70)])), M, **A)
        s.armor(polym(f([(61, 73), (73, 73), (75, 92), (60, 92)])), M, **A)
        s.armor(polym(f([(62, 67), (72, 67), (73, 74), (61, 74)])), M, **A)
    s.armor(polym([(62, 51), (86, 51), (88, 60), (81, 63), (74, 58), (67, 63), (60, 60)]), M, **A)
    for ax in (0, 1):
        f = (lambda p: p) if ax == 0 else (lambda p: mirror(p, 74))
        s.armor(polym(f([(49, 34), (57, 34), (57, 48), (50, 48)])), M, **A)
        s.armor(polym(f([(45, 47), (58, 47), (59, 62), (44, 62)])), M, **A)
        s.armor(polym(f([(46, 61), (57, 61), (56, 68), (47, 68)])), M, **A)
        s.armor(polym(f([(45, 26), (57, 19), (67, 23), (66, 33), (57, 38), (44, 34)])), M, **A)
    s.armor(rectm(70, 21, 77, 24), M, **A)
    s.armor(polym([(69, 10), (79, 10), (81, 13), (81, 19), (78, 22), (70, 22), (67, 19), (67, 13)]), M, **A)
    s.armor(polym([(73, 12), (64, 3), (66, 3), (74, 9), (82, 3), (84, 3), (75, 12)]), M, **A)
    # face: visor slit, eyes, mouth vents
    s.rect(69, 16, 78, 16, 0)
    s.lift(74, 16.5, 7, .5, Wm, m=M)
    s.px(69, 16, 6); s.px(70, 16, 3); s.px(71, 16, 4); s.px(76, 16, 4); s.px(77, 16, 3); s.px(78, 16, 6)
    for x in (71, 73, 75, 77): s.px(x, 19, 1)
    # chest core with bloom
    s.lift(74, 33, 12, .7, U, m=M)
    s.put(ellm(74, 33, 3.4, 3.4), 0); s.put(ellm(74, 33, 2.6, 2.6), 7)
    s.px(73, 32, 4); s.px(74, 32, 11); s.px(73, 33, 11); s.px(75, 34, 5)
    for x in range(63, 86):
        if (x, 42) in M and abs(x-74) > 2: s.px(x, 42, 1 if x % 2 else 0)
    s.line(74, 37, 74, 47, 1)
    for y in (50, 52): s.line(68, y, 79, y, 1)
    for (a, b) in ((51, 52), (97, 52)): s.line(a-4, b, a+4, b, 1); s.line(a-4, b+1, a+4, b+1, 10)     # forearm bands
    # pauldron hazard stripes, knee lights
    for i in range(4):
        s.px(50+i*2, 31-i, 3); s.px(98-i*2, 31-i, 3)
    s.px(67, 70, 6); s.px(81, 70, 6)
    s.px(42, 6, 7); s.px(43, 5, 7); s.lift(43, 5, 5, .5, U, only={0, 1, 12, 2, 9})    # cannon muzzle
    # fire light washing the left side of the mecha
    s.lift(44, 70, 22, .45, Wm, m=M, only={12, 2, 1})
    for (x, y) in M:                                                   # mist round the shins
        if y > 77 and bay(x, y) < (y-77)/8*0.6: s.p[y][x] = 2
    # ---- gunships with spotlights on the mecha
    def ship(x, y, d):
        rows = ["..XXXX..", "XXXXXXXX", ".X....X."]
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch == 'X': s.px(x+(i if d > 0 else 7-i), y+j, 0)
        for i in range(2, 6): s.px(x+(i if d > 0 else 7-i), y, 10)
        s.px(x+(7 if d > 0 else 0), y+1, 6); s.px(x+(0 if d > 0 else 7), y+1, 7)
    s.beam(100, 10, 81, 17, 0.6, 3.0, .55, U, fall=.3)
    ship(99, 7, -1)
    s.beam(30, 40, 47, 52, 0.6, 3.0, .5, U, fall=.3)
    ship(23, 37, 1)
    # ---- burning docks (left shore)
    dock = set()
    dock |= rectm(0, 73, 17, hz)
    for i in range(4): dock |= polym([(i*4.5, 73), (i*4.5+4.5, 69), (i*4.5+4.5, 73)])
    dock |= rectm(19, 65, 24, hz) | ellm(21.5, 65, 3, 2)
    dock |= rectm(26, 68, 30, hz) | ellm(28, 68, 2.5, 1.6)
    dock |= rectm(33, 55, 34, hz) | rectm(41, 55, 42, hz) | rectm(28, 53, 52, 54) | rectm(35, 55, 40, 59)
    dock |= rectm(31, 78, 54, hz)
    s.put(dock, 0)
    for (x, y) in dock:
        if (x, y-1) not in dock: s.p[y][x] = 13 if x < 30 and bay(x, y) < .5 else 9
        elif (x-1, y) not in dock and y < hz-2 and bay(x, y) < .6: s.p[y][x] = 9
    for x in range(29, 52, 3): s.line(x, 54, x+2, 53, 9)
    s.line(36, 60, 33, 66, 0); s.line(39, 60, 42, 66, 0)
    s.line(50, 55, 50, 64, 12); s.rect(49, 64, 51, 65, 12)                 # crane hook
    s.px(37, 57, 3); s.px(38, 57, 3)
    for x in range(33, 53, 4): s.px(x, 81, 3 if x % 8 else 1)
    s.px(54, 77, 8); s.px(31, 76, 6)                                        # quay navigation lights
    for (fx, fy, fw, fh, sd) in ((8, 73, 14, 20, 0.3), (21.5, 64, 7, 13, 1.7), (29, 79, 7, 10, 2.9), (46, 79, 6, 9, 4.4)):
        s.lift(fx, fy-fh*0.35, fh*1.4, .5, Wm, only={0, 1, 12, 2, 9, 10})
        s.flame(fx, fy, fw, fh, sd)
    s.sparks(14, 50, 16, 14, 16, [13, 3], 71, only={0, 1, 12, 2, 9})
    # ---- suspension bridge across the harbour
    tl, tr, tt, deck = 19, 130, 40, 72
    def cabley(x):
        if x < tl: return tt+(tl-x)*0.9
        u = (x-(tl+tr)/2)/((tr-tl)/2); return deck-3-(deck-3-tt)*u*u
    for x in range(W):
        y = cabley(x+.5)
        if x % 4 == 1 and y+2 < deck: s.line(x, int(y)+2, x, deck-1, 1)
    for x in range(W):
        y = cabley(x+.5); s.px(x, y, 14); s.px(x, y+1, 1)
    for t in (tl,):
        tower = rectm(t-3, tt, t-2, deck+8) | rectm(t+2, tt, t+3, deck+8) | rectm(t-3, tt-2, t+3, tt) | rectm(t-3, 55, t+3, 56)
        s.put(tower, 0)
        for (x, y) in tower:
            if (x-1, y) not in tower: s.p[y][x] = 9 if t == tl else 1
            if (x+1, y) not in tower: s.p[y][x] = 13 if t == tl and bay(x, y) < .6 else (7 if t == tr else 1)
            if (x, y-1) not in tower: s.p[y][x] = 10
        s.lift(t, tt-3, 6, .45, Wm, only={0, 1, 12, 2})
        s.px(t-3, tt-3, 6); s.px(t+3, tt-3, 6)
    s.rect(0, deck, W-1, deck, 10); s.rect(0, deck+1, W-1, deck+3, 1); s.rect(0, deck+4, W-1, deck+4, 0)
    for x in range(W):
        if x % 6 == 0: s.px(x, deck+1, 3)
        if x % 6 == 3: s.px(x, deck+2, 6)
        if x % 4 == 0: s.line(x, deck+5, x+2, deck+7, 0); s.line(x+2, deck+5, x, deck+7, 1)
    s.rect(0, deck+8, W-1, deck+8, 0)
    # ---- right foreground tower with neon
    T = rectm(106, 22, 119, hz) | rectm(109, 12, 119, 22) | rectm(112, 4, 116, 12)
    s.put(T, 0)
    for (x, y) in T:
        if (x-1, y) not in T: s.p[y][x] = 2 if bay(x, y) < .7 else 1
        if (x, y-1) not in T: s.p[y][x] = 10
    s.line(114, 4, 114, 0, 0); s.lift(114, 0, 4, .5, Wm, only={0, 1, 12, 2}); s.px(114, 0, 6)
    s.windows(108, 118, 25, hz-2, 2, 4, [3, 7], .18, dim=1, only={0})
    s.windows(111, 118, 14, 20, 2, 3, [5], .3, only={0})
    s.sign(100, 34, 4, 22, 15, 4, U, lv=.6, only={0, 1, 12, 2, 9, 10})
    s.sign(108, 62, 10, 4, 8, 0, U, lv=.45, only={0, 1, 12, 2, 9, 10})
    s.sign(1, 44, 3, 12, 7, 4, U, lv=.5, only={0, 1, 12, 2, 9})
    s.rect(0, hz, W-1, hz, 12)
    s.water(hz, 1.0, stretch=1.0, ripple=12)
    s.rain(2, 10, {0, 1, 12}, cell=(8, 11), p=.6, L=(3, 5), splash=12)
    return s

# ======================================================================= 08
# A ringed giant fills the sky; twin spires anchor a space elevator; aurora; orbital ring.
def scene08():
    s = C(8); hz = 92; U, Wm = s.U, s.Wm
    s.sky(0, hz, [0, 1, 12, 2], gam=1.2)
    r = random.Random(81)
    for gy in range(0, 60, 9):
        for gx in range(0, W, 10):
            x = gx+r.randint(0, 9); y = gy+r.randint(0, 8)
            if s.g(x, y) in (0, 1): s.px(x, y, r.choice((11, 5, 14, 14)))
    # planet
    cx, cy, R = 60, 44, 37
    tilt = math.radians(-16); ct, st = math.cos(tilt), math.sin(tilt); ba = 0.25
    def ringr(x, y):
        dx, dy = x+.5-cx, y+.5-cy
        u = dx*ct+dy*st; v = -dx*st+dy*ct
        return math.hypot(u, v/ba)/R, v
    def ringcol(rn, x, y):
        if rn < 1.2 or rn > 1.95: return None
        q = (rn-1.2)/0.75
        if q < 0.14: return 10 if bay(x, y) < .55 else None
        if q < 0.2: return None
        if q < 0.36: return 13 if bay(x, y) < .7 else 9
        if q < 0.5: return 4 if bay(x, y) < .4 else 13
        if q < 0.55: return 2
        if q < 0.8: return 9 if bay(x, y) < .65 else 10
        return 14 if bay(x, y) < .45 else None
    for y in range(H):
        for x in range(W):
            rn, v = ringr(x, y)
            if v < 0:
                c = ringcol(rn, x, y)
                if c is not None: s.p[y][x] = c
    disc = ellm(cx, cy, R, R)
    ramp = [0, 1, 12, 2, 10, 9, 13]
    def pv(x, y):
        lx, ly = (x+.5-cx)/R, (y+.5-cy)/R
        lz = math.sqrt(max(0, 1-lx*lx-ly*ly))
        lam = max(0, -0.6*lx-0.5*ly+0.62*lz)
        w = ly*10+0.7*math.sin(lx*3.5+1)+0.25*math.sin(lx*9)
        band = 0.5 if math.sin(w) > 0.25 else (-0.5 if math.sin(w) < -0.55 else 0)
        return lam*1.02+band*0.13*(0.4+lam)+0.03
    s.shade(disc, pv, ramp)
    # ring shadow on the planet (light from the upper left)
    for (x, y) in disc:
        rn, v = ringr(x-3, y-4)
        if 1.2 < rn < 1.9 and v >= 0 and bay(x, y) < .8: s.p[y][x] = s.D.get(s.p[y][x], 0)
    # great storm
    sm = ellm(43, 35, 5.5, 2.6); s.put(sm, 9)
    for (x, y) in sm:
        if (x, y-1) not in sm or (x-1, y) not in sm: s.p[y][x] = 13
        elif (x, y+1) not in sm: s.p[y][x] = 2
    s.put(ellm(44, 35, 2, 1), 10)
    # bright limb + atmosphere halo on the lit side
    for (x, y) in disc:
        lx, ly = (x+.5-cx)/R, (y+.5-cy)/R
        if math.hypot(lx, ly) > 0.94 and -lx-ly > 0.3: s.p[y][x] = 4 if -lx-ly > 1.2 and bay(x, y) < .6 else 13
    for y in range(H):
        for x in range(W):
            if (x, y) in disc: continue
            d = math.hypot(x+.5-cx, y+.5-cy); side = -((x+.5-cx)+(y+.5-cy))/max(1, d)
            if d < R+5 and side > -0.2 and bay(x, y) < (R+5-d)/5*0.7*(side+0.2):
                s.p[y][x] = 9 if d < R+1.6 else (10 if d < R+3.2 else 2)
    for y in range(H):
        for x in range(W):
            rn, v = ringr(x, y)
            if v >= 0:
                c = ringcol(rn, x, y)
                if c is not None: s.p[y][x] = c
    # artificial orbital ring (thin cyan ellipse with station lights)
    ox, oy, oa, ob = 60, 70, 76, 6
    for a in range(0, 3600):
        t = a/10*math.pi/180; x = ox+math.cos(t)*oa; y = oy+math.sin(t)*ob
        if math.sin(t) > 0: s.px(x, y, 7)
        elif s.g(x, y) != 7: s.px(x, y, 14 if a % 40 < 26 else s.g(x, y))
    for a in range(10, 360, 16):
        t = math.radians(a); x = ox+math.cos(t)*oa; y = oy+math.sin(t)*ob
        if math.sin(t) > 0.1: s.px(x, y, 4); s.px(x+1, y, 5)
    # aurora: a ribbon arching over the planet, 1-px rays rising from a green hem
    for x in range(W):
        hem = 9+30*((x-60)/60.0)**2+1.5*math.sin(x*0.31)
        ray = math.sin(x*1.7+2.0*math.sin(x*0.13))
        if ray < -0.2: continue
        L = 4+12*(0.5+0.5*math.sin(x*0.23+1.0))*(0.6+0.4*ray)
        for y in range(int(hem-L), int(hem)+2):
            if not (0 <= y < H): continue
            u = (hem-y)/L
            sky_ = s.p[y][x] in (0, 1, 12, 2, 14, 5, 11)
            if not sky_ and (u > 0.2 or (x+y) % 2): continue
            if u < 0: c = 8 if (x+y) % 2 == 0 else s.p[y][x]
            elif u < 0.35: c = 8
            elif u < 0.6: c = 8 if bay(x, y//2) < 0.6-u*0.5 else 7
            elif bay(x, y//3) < (1.05-u)*1.5: c = 7 if u < 0.75 else 15
            else: continue
            if ray < 0.3 and bay(x, y//2) > .5: continue
            s.p[y][x] = c
    # far haze city, then mid city
    for y in range(hz-26, hz+1):                                   # city glow on the low sky
        for x in range(W):
            if bay(x, y) < ((y-(hz-26))/26)**1.3*0.9: s.p[y][x] = U.get(s.p[y][x], s.p[y][x])
    skyline(s, hz, 4, 12, 0, W, 2, [13], .06, 3, 6, step=(2, 3))
    skyline(s, hz, 6, 18, 0, W, 1, [9, 7, 3], .1, 4, 9, step=(2, 3), cap=12)
    for y in range(hz-8, hz+1):
        for x in range(W):
            if s.p[y][x] == 1 and bay(x, y) < (y-(hz-8))/8*0.5: s.p[y][x] = 12
    # space elevator: cable, light column, climbers, top station
    ex = 60
    s.beam(ex, hz, ex, 0, 4.5, 1.2, .5, U, fall=.55)
    for y in range(4, hz): s.px(ex, y, 5 if y % 4 else 11)
    for (py, ln) in ((18, 4), (42, 4), (62, 3)):
        s.lift(ex, py+2, 7, .55, U, only={0, 1, 12, 2, 10, 9, 13, 14})
        s.rect(ex-1, py, ex+1, py+ln, 11); s.px(ex-1, py+1, 7); s.px(ex+1, py+2, 7); s.px(ex, py+ln, 0)
        s.px(ex, py-1, 4)
    s.rect(ex-4, 0, ex+4, 2, 0); s.rect(ex-5, 3, ex+5, 3, 7); s.px(ex-3, 1, 6); s.px(ex+3, 1, 6); s.px(ex, 1, 4)
    # twin spires (true-dark silhouettes against the planet)
    def spire(ax, tip, bw):
        m = set()
        for y in range(tip, hz+1):
            t = (y-tip)/(hz-tip); hw = 0.6+bw*t
            for (yc, add) in ((tip+(hz-tip)*0.3, 1.5), (tip+(hz-tip)*0.52, 2.5), (tip+(hz-tip)*0.74, 1.5)):
                if abs(y-yc) <= 1: hw += add
            for x in range(int(round(ax-hw)), int(round(ax+hw))+1): m.add((x, y))
        m |= rectm(int(ax-bw-3), hz-5, int(ax+bw+3), hz)
        s.put(m, 0)
        for (x, y) in m:
            if (x-1, y) not in m: s.p[y][x] = 13 if bay(x, y) < .55 else 9
            if (x+1, y) not in m: s.p[y][x] = 10 if bay(x, y) < .55 else 2
            if (x, y-1) not in m: s.p[y][x] = 13
        for y in range(tip+6, hz-1, 2):
            hwy = 0.6+bw*((y-tip)/(hz-tip))
            if hwy > 2.0 and (y//2) % 3 != 0:
                s.px(ax, y, 7 if (y//6) % 4 else 15)
            if hwy > 4.5 and (y//2) % 4 == 1: s.px(ax-3, y, 3); s.px(ax+3, y, 1)
        s.line(ax, tip-1, ax, tip-8, 0); s.px(ax, tip-4, 10)
        s.lift(ax, tip-9, 5, .55, Wm, only={0, 1, 12, 2, 10, 9, 13})
        s.px(ax, tip-9, 6)
    spire(44, 12, 7); spire(77, 18, 7)
    s.rect(46, 50, 75, 52, 0); s.rect(46, 50, 75, 50, 13); s.rect(46, 53, 75, 53, 1)
    for x in range(48, 74, 2): s.px(x, 51, 7 if x % 6 else 3)
    s.put(ellm(ex+0.5, hz+1, 8, 5), 0); s.put(ellm(ex+0.5, hz+1, 8, 5) - ellm(ex+0.5, hz+2, 8, 5), 13)
    s.put(ellm(ex+0.5, hz-1, 3, 1.6), 7); s.px(ex, hz-2, 4)
    # near buildings at both edges
    for (x0, x1, top, cols) in ((0, 15, 26, [3, 9]), (16, 23, 60, [7]), (100, 107, 54, [9, 3]), (108, 119, 18, [7, 9])):
        b = rectm(x0, top, x1, hz) | rectm(x0+2, top-5, x1-2, top)
        s.put(b, 0)
        for (x, y) in b:
            if (x+1, y) not in b and x < 60: s.p[y][x] = 9 if bay(x, y) < .7 else 1
            if (x-1, y) not in b and x > 60: s.p[y][x] = 10 if bay(x, y) < .7 else 1
            if (x, y-1) not in b: s.p[y][x] = 13
        s.windows(x0+1, x1-1, top+2, hz-2, 2, 3, cols, .22, dim=1, only={0})
    s.line(7, 21, 7, 8, 0); s.px(7, 7, 6); s.line(113, 13, 113, 2, 0); s.px(113, 1, 6)
    s.line(4, 21, 4, 15, 0); s.line(111, 13, 111, 7, 0)
    s.sign(17, 64, 4, 16, 8, 0, U, lv=.5, only={0, 1, 12, 2, 10})
    s.sign(2, 34, 5, 20, 15, 4, U, lv=.55, only={0, 1, 12, 2, 10})
    s.sign(102, 30, 4, 18, 7, 4, U, lv=.55, only={0, 1, 12, 2, 10, 9})
    s.sign(97, 60, 9, 4, 3, 0, Wm, lv=.5, only={0, 1, 12, 2, 10})
    # traffic light-trails between the towers
    for (x, y, d, c) in ((28, 70, 1, 6), (92, 64, -1, 3), (34, 80, -1, 3), (88, 76, 1, 6)):
        for i in range(1, 6):
            if s.g(x-d*i, y) in (0, 1, 12, 2, 10) and bay(x-d*i, y) < 1-i/6: s.px(x-d*i, y, c)
        s.px(x, y, 4); s.px(x+d, y, 5); s.px(x, y-1, 1); s.px(x+d, y-1, 1)
    s.rect(0, hz, W-1, hz, 2)
    s.water(hz, .9, ripple=12)
    s.rain(2, 10, {0, 1, 12}, cell=(9, 12), p=.5, L=(3, 4), splash=2)
    return s

# ======================================================================= 09
# The final megastructure: ring platforms, tractor beams, a storm eye, lightning, a fleet.
BEAM9 = {0:14, 1:14, 12:14, 2:14, 10:5, 9:5, 14:5, 5:11, 13:11, 7:5, 3:4, 11:4, 6:5}
CORE9 = {0:7, 1:7, 12:7, 2:7, 14:5, 10:5, 9:5, 7:5, 5:11, 11:4, 13:11, 3:4}
def scene09():
    s = C(9); hz = 94; U, Wm = s.U, s.Wm; cx = 60
    s.sky(0, hz, [0, 1, 12], gam=1.0)
    # storm eye glow above the crown
    s.lift(cx, 0, 30, .55, U, sy=0.7, only={0, 1, 12}, gam=1.4)
    # cloud banks: scalloped billows, rim-lit on top by the eye, fire-lit underneath
    def bank(yc, x0, x1, rmin, rmax, body, top, under, low, seed, gap=None):
        r = random.Random(seed); circ = []; x = x0
        while x < x1:
            rr = r.uniform(rmin, rmax); yy = yc+r.uniform(-2.5, 2.5)
            if gap is None or abs(x-gap[0]) > gap[1]: circ.append((x, yy, rr))
            x += rr*r.uniform(0.9, 1.4)
        m = set()
        for (a, b, rr) in circ:
            for y in range(int(b-rr)-1, int(b+rmax*0.9)+1):
                for x in range(int(a-rr)-1, int(a+rr)+2):
                    if not (0 <= x < W and 0 <= y < H): continue
                    if math.hypot(x+.5-a, y+.5-b) <= rr or (y+.5 >= b and abs(x+.5-a) <= rr):
                        m.add((x, y))
        ybot = max(y for (_, y) in m)
        for (x, y) in m:
            c = body
            if bay(x, y) < (y-(ybot-rmax*0.9))/(rmax*0.9)*1.1-0.1: c = under
            if (x, y-1) not in m: c = top
            elif (x, y-2) not in m and bay(x, y) < .5: c = top
            elif (x-1, y) not in m and bay(x, y) < .4: c = top
            elif (x+1, y) not in m or (x+2, y) not in m: c = low if bay(x, y) < .6 else c
            s.p[y][x] = c
        for (x, y) in m:
            if (x, y+1) not in m and y+1 < H and bay(x, y+1) < .5: pass
        return m
    bank(9, -6, W+6, 7, 12, 12, 2, 1, 1, 11, gap=(cx, 18))
    bank(25, -8, W+8, 7, 13, 12, 10, 2, 1, 13, gap=(cx, 9))
    bank(42, -6, W+6, 6, 11, 2, 10, 10, 12, 14)
    # eye of the storm
    eye = ellm(cx, 1, 10, 4)
    for (x, y) in eye:
        d = math.hypot((x+.5-cx)/10, (y+.5-1)/4)
        s.p[y][x] = 4 if d < .35 else (11 if d < .6 else (5 if bay(x, y) < 1.1-d else 14))
    # fire-lit low sky
    for y in range(52, hz+1):
        for x in range(W):
            k = ((y-52)/(hz-52))**1.3
            if bay(x, y) < k*0.8: s.p[y][x] = Wm.get(s.p[y][x], s.p[y][x])
    # far fleet: tiny ships in formation, engines lit
    for (fx, fy, d) in ((10, 26, 1), (16, 29, 1), (22, 32, 1), (98, 24, -1), (104, 27, -1), (92, 21, -1), (20, 56, 1), (102, 52, -1)):
        s.rect(fx, fy, fx+3, fy, 1); s.px(fx+1, fy-1, 1); s.px(fx-1 if d > 0 else fx+4, fy, 7)
        s.px(fx+(3 if d > 0 else 0), fy, 2)
    # burning city behind
    tops = []
    x = 0
    while x < W:
        w = s.r.randint(3, 8); h = s.r.randint(6, 24); xe = min(W-1, x+w-1)
        s.rect(x, hz-h, xe, hz, 1); s.rect(x, hz-h, xe, hz-h, 12); tops.append((x, xe, hz-h))
        s.windows(x+1, xe-1, hz-h+2, hz-2, 2, 3, [13, 3], .05, only={1})
        x += w+s.r.choice((0, 1))
    for (x0, xe, t) in tops:
        if s.r.random() < .3 and xe-x0 >= 4:
            fx = (x0+xe)/2
            s.lift(fx, t-3, 9, .5, Wm, only={0, 1, 12, 2, 10})
            s.flame(fx, t, xe-x0, s.r.randint(5, 9), x0*0.37)
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
                    c = 1 if back else (14 if bay(x, y) < .5 else 2)
                    if e > 0.84: c = (14 if back else 5) if (x+.5-rx) > -a*0.3 else (2 if back else 10)
                    if e < q2+0.14: c = 0 if back else 1
                    if (x+.5-rx) < -a*0.62 and e > 0.75 and not back: c = 13 if bay(x, y) < .5 else 10
                    s.p[y][x] = c
                elif e > 1 and not back:
                    for k in range(1, th+1):
                        if ((x+.5-rx)/a)**2+((y-k+.5-ry)/b)**2 <= 1:
                            c = 0 if k == th else 1
                            if k == 1 and x % 3 == 0: c = 3 if (x//3) % 3 else 7
                            s.p[y][x] = c; break
    for rc in rings: platform(rc, True)
    # tractor beams under the great ring, lifting debris
    for (bx, ex) in ((27, 18), (93, 102)):
        s.beam(bx, 57, ex, hz, 3, 11, .4, BEAM9, fall=.3, edge=7, streak=3)
        s.beam(bx, 57, ex, hz, 1.5, 5, .55, CORE9, fall=.5, streak=3)
        for k in range(5):
            yy = 62+k*6; xx = bx+(ex-bx)*(yy-57)/(hz-57)+math.sin(k*2.3+bx)*4
            s.px(xx, yy, 5); s.px(xx+1, yy, 0); s.px(xx, yy+1, 1)
    s.put(body, 1)
    for (x, y) in body:
        rel = (x+.5-cx)/max(1, hw(y)); c = 1
        if rel > 0.25: c = 0 if bay(x, y) < (rel-0.25)*2.2 else 1
        if rel < -0.35 and bay(x, y) < (-rel-0.35)*1.3: c = 12
        if (x-1, y) not in body: c = 9 if bay(x, y) < .7 else 10
        elif (x-2, y) not in body and bay(x, y) < .5: c = 2
        elif (x+1, y) not in body: c = 7 if bay(x, y) < .6 else 14
        elif (x, y-1) not in body: c = 10
        elif y % 6 == 0 and abs(rel) < .8 and ((x*7+y*3) % 13) < 4: c = 3
        elif y % 6 == 0 and abs(rel) < .8: c = 0
        s.p[y][x] = c
    for sx in (-1, 1):                                             # buttress ribs
        s.line(cx+sx*13, hz, cx+sx*9, hz-33, 12 if sx < 0 else 0)
    s.line(cx, 8, cx, hz, 7)
    for y in range(10, hz, 8): s.px(cx, y, 4); s.px(cx-1, y, 5); s.px(cx+1, y, 5)
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
    # lightning
    for (lx, ly, ln, sd) in ((18, 34, 10, 7), (108, 30, 6, 9), (40, 8, 9, 3)):
        s.lift(lx, ly, 10, .35, U, only={1, 12})
        pts = s.bolt(lx, ly, ln, sd, core=4, glow=5)
    # capital ships of the fleet
    def capital(x, y, L, d, near=True):
        h = max(3, int(L/5))
        hull = polym([(x, y), (x+d*L*0.72, y), (x+d*L, y+h*0.55), (x+d*L*0.72, y+h), (x, y+h)])
        sup = polym([(x+d*L*0.12, y), (x+d*L*0.16, y-h*0.8), (x+d*L*0.34, y-h*0.8), (x+d*L*0.42, y)])
        m = hull | sup
        top_c, body_c, low_c = (5, 1, 10) if near else (14, 1, 12)
        s.put(m, body_c)
        for (a, b) in m:
            if (a, b-1) not in m: s.p[b][a] = top_c
            elif (a, b+1) not in m: s.p[b][a] = low_c
            elif (a, b+2) not in m: s.p[b][a] = 0
            elif (a-d, b) not in m and near: s.p[b][a] = 14
        for i in range(3, int(L*0.7), 2): s.px(x+d*i, y+h//2, 3 if (i//2) % 3 else 1)
        st_ = x-d
        s.lift(st_-d, y+h/2, h+4, .6, U, only={0, 1, 12, 2, 10})
        for j in range(y+1, y+h): s.px(st_, j, 5); s.px(st_-d, j, 7)
        s.px(st_, y+h//2, 4)
        s.px(x+d*int(L*0.28), int(y-h*0.8)-1, 6)
    capital(4, 34, 34, 1)
    capital(115, 21, 26, -1)
    capital(90, 40, 12, -1, near=False)
    capital(24, 46, 10, 1, near=False)
    # ---- near foreground: dark towers with signs, fire and sparks
    for (x0, x1, top) in ((0, 13, 50), (14, 19, 72), (104, 110, 66), (111, 119, 42)):
        b = rectm(x0, top, x1, hz) | rectm(x0+2, top-5, x1-2, top)
        s.put(b, 0)
        for (x, y) in b:
            if (x+1, y) not in b and x < cx: s.p[y][x] = 9 if bay(x, y) < .7 else 2
            if (x-1, y) not in b and x > cx: s.p[y][x] = 7 if bay(x, y) < .5 else 14
            if (x, y-1) not in b: s.p[y][x] = 10
        s.windows(x0+1, x1-1, top+2, hz-2, 2, 3, [3, 13, 15], .14, dim=1, only={0})
    s.line(115, 37, 115, 28, 0); s.px(115, 27, 6)
    s.lift(7, 44, 12, .5, Wm, only={0, 1, 12, 2, 10}); s.flame(7, 45, 9, 12, 1.3)
    s.sign(2, 56, 4, 18, 15, 4, U, lv=.5, only={0, 1, 12, 2, 10, 9})
    s.sign(113, 50, 4, 16, 8, 0, U, lv=.5, only={0, 1, 12, 2, 10, 9})
    s.sign(95, 78, 8, 4, 7, 0, U, lv=.5, only={0, 1, 12, 2, 10, 9})
    s.sparks(8, 30, 12, 8, 12, [13, 3], 91, only={0, 1, 12, 2, 10})
    s.sparks(36, 60, 8, 10, 10, [13, 3], 92, only={0, 1, 12, 2, 10})
    s.rect(0, hz, W-1, hz, 10)
    s.water(hz, .9, ripple=12)
    s.rain(2, 10, {0, 1, 12}, cell=(7, 9), p=.65, L=(3, 5), splash=12)
    return s

def sheet4(ims, crops, path):
    """4x crops: list of (scene index, x, y, w, h)"""
    tiles = [ims[i].convert('RGB').crop((x, y, x+w, y+h)).resize((w*4, h*4), Image.Resampling.NEAREST) for (i, x, y, w, h) in crops]
    cw = max(t.width for t in tiles); ch = max(t.height for t in tiles); cols = 3
    sh = Image.new('RGB', (cols*(cw+4), ((len(tiles)+cols-1)//cols)*(ch+4)), (0, 0, 0))
    for k, t in enumerate(tiles): sh.paste(t, ((k % cols)*(cw+4), (k//cols)*(ch+4)))
    sh.save(path)

if __name__ == '__main__':
    out = os.path.dirname(os.path.abspath(__file__)); ims = []
    for n, f in ((7, scene07), (8, scene08), (9, scene09)):
        ims.append(f().save(os.path.join(out, 'scene%02d.png' % n)))
    pv = Image.new('RGB', (W*3*3+8, H*3), (0, 0, 0))
    for i, im in enumerate(ims): pv.paste(im.convert('RGB').resize((W*3, H*3), Image.Resampling.NEAREST), (i*(W*3+4), 0))
    pv.save(os.path.join(out, 'preview_c2.png'))
    sheet4(ims, [(0, 34, 0, 60, 56), (0, 0, 50, 60, 56), (0, 60, 56, 60, 56),
                 (1, 24, 0, 60, 56), (1, 30, 46, 60, 56), (1, 60, 30, 60, 56),
                 (2, 30, 0, 60, 56), (2, 0, 20, 60, 56), (2, 40, 40, 60, 56)],
           os.path.join(out, 'crops_c2.png'))
