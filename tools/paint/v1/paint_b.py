"""CHix scenes 04..06: rainy cyberpunk night cities. Run: python paint_b.py"""
import math, random, os
from PIL import Image, ImageDraw
W, H, HOR = 120, 112, 86
BAY = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]
HERE = os.path.dirname(os.path.abspath(__file__))


class C:
    def __init__(s, pal, seed):
        s.im = Image.new("P", (W, H), 0); s.d = ImageDraw.Draw(s.im)
        s.pal = pal; s.r = random.Random(seed)
        flat = []
        for p in pal: flat += list(p)
        s.im.putpalette(flat)

    def lum(s, c): r, g, b = s.pal[c]; return .3*r + .59*g + .11*b

    def px(s, x, y, c):
        if 0 <= x < W and 0 <= y < H: s.im.putpixel((x, y), c)

    def get(s, x, y): return s.im.getpixel((x, y)) if 0 <= x < W and 0 <= y < H else 0

    def dth(s, x, y, a, b, f): return b if (BAY[y % 4][x % 4] + .5) / 16 < f else a

    def rect(s, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): s.px(x, y, c)

    def sky(s, stops, y1):
        n = len(stops) - 1
        for y in range(y1):
            t = (y / max(1, y1 - 1)) ** 1.15 * n; i = min(int(t), n - 1); f = t - i
            for x in range(W): s.px(x, y, s.dth(x, y, stops[i], stops[i+1], f))

    def bloom(s, cx, cy, rad, col, strength=.8):
        L = s.lum(col)
        for y in range(int(cy-rad), int(cy+rad)+1):
            for x in range(int(cx-rad), int(cx+rad)+1):
                d = math.hypot(x-cx, y-cy)
                if d < rad and y < HOR:
                    f = (1 - d/rad) ** 1.5 * strength
                    cur = s.get(x, y)
                    if s.lum(cur) < L and (BAY[y%4][x%4] + .5)/16 < f: s.px(x, y, col)


def stars(c, n, y1, cols):
    for _ in range(n):
        c.px(c.r.randrange(W), c.r.randrange(y1), c.r.choice(cols))


def buildings(c, lo, hi, wmin, wmax):
    out = []; x = -c.r.randrange(3)
    while x < W:
        w = c.r.randint(wmin, wmax); h = c.r.randint(lo, hi)
        out.append((x, w, HOR - int(h*.8))); x += w
    return out


def far_layer(c, bl, body, rim, haze, detail):
    for x0, w, top in bl:
        for x in range(x0, min(W, x0+w)):
            for y in range(top, HOR):
                f = max(0, (y - (HOR-30)) / 30)
                col = body if x > x0 else rim
                c.px(x, y, c.dth(x, y, col, haze, f*.85) if f > 0 else col)
            if x0 + w > x > x0 + 1 and (x*7+top) % 5 == 0:
                for y in range(top+3, HOR-6, 4):
                    if c.r.random() < .25: c.px(x, y, detail)
        c.px(x0, top, rim)
        if w > 6 and top % 2: c.px(x0 + w//2, top-1, rim)
        if top % 3 == 0:
            for y in range(top-5, top): c.px(x0 + w//2, y, body)
            c.px(x0 + w//2, top-6, 6)


def mid_layer(c, bl, body, rim, wins, lit):
    for x0, w, top in bl:
        c.rect(x0, top, min(W-1, x0+w-1), HOR, body)
        for x in range(x0, min(W, x0+w)): c.px(x, top, rim)
        for y in range(top, HOR): c.px(x0, y, rim if y % 2 else body)
        for y in range(top+3, HOR-8, 3):
            for x in range(x0+2, x0+w-1, 3):
                if c.r.random() < lit: c.px(x, y, c.r.choice(wins))
        if w > 7 and top % 4 == 1:
            c.rect(x0+2, top-3, x0+4, top-1, body); c.px(x0+3, top-5, 6); c.px(x0+3, top-4, body)


def near_layer(c, bl, body, rim, wins, neon, sparkle):
    for k, (x0, w, top) in enumerate(bl):
        x1 = min(W-1, x0+w-1)
        c.rect(x0, top, x1, HOR, body)
        for x in range(x0, x1+1): c.px(x, top, rim)
        for y in range(top, HOR): c.px(x0, y, rim)
        if k % 2:
            for x in range(x0+1, x1+1, 2): c.px(x, top+1, rim)
        for y in range(top+4, HOR-9, 5):
            for x in range(x0+2, x1-1, 4):
                r = c.r.random()
                if r < .42: c.rect(x, y, x+1, y+1, c.r.choice(wins))
                elif r < .5: c.rect(x, y, x+1, y+1, rim)
        col = c.r.choice(neon)
        c.rect(x0+1, HOR-6, x1, HOR-5, col)
        for x in range(x0+1, x1+1): c.px(x, HOR-4, c.dth(x, HOR-4, col, body, .6))
        c.rect(x0+1, HOR-3, x1, HOR-1, body)
        for x in range(x0+2, x1-1, 4): c.rect(x, HOR-3, x+1, HOR-2, c.r.choice(wins))
        c.px(x0 + w//2, HOR-8, col)
        c.bloom(x0 + w/2, HOR-5, 8, col, .5)
        if k % 5 == 2 and w > 6:
            sc = c.r.choice(neon); sx = x1 - 1; sy = top + 6
            ln = c.r.randint(14, 24); end = min(HOR-9, sy+ln)
            c.rect(sx-1, sy, sx+1, end, body)
            for y in range(sy, end):
                c.px(sx, y, sc if (y-sy) % 3 else 4)
                c.px(sx-1, y, c.dth(sx-1, y, body, sc, .35))
            c.bloom(sx, sy+ln/2, 9, sc, .8)


def car(c, x, y, dirn, body, tail, head, trail):
    for i in range(1, 10):
        if (BAY[y % 4][i % 4]) < 8: c.px(x - dirn*(i+2) + (3 if dirn < 0 else 0), y+1, trail)
    c.rect(x, y, x+3, y+1, body); c.px(x+1, y-1, body); c.px(x+2, y-1, body)
    c.px(x if dirn > 0 else x+3, y, tail)
    c.px(x+3 if dirn > 0 else x, y, head)
    c.px(x+1, y+2, trail)
    c.bloom(x+(3 if dirn > 0 else 0), y, 4, head, .6)


def street(c, base, dim, glint, lane, thresh):
    snap = Image.new("P", (W, H)); snap.putpalette(c.im.getpalette()); snap.paste(c.im)
    for y in range(HOR, H):
        for x in range(W):
            c.px(x, y, c.dth(x, y, base, dim, min(1, (y-HOR)/20)))
    for y in range(HOR+1, H):
        d = y - HOR; src = HOR - 1 - int(d*1.1)
        fade = max(0, 1 - d/26)
        for x in range(W):
            ox = x + (1 if (d % 3 == 0 and x % 5 < 2) else 0) - (1 if d % 5 == 0 and x % 7 < 2 else 0)
            p = snap.getpixel((max(0, min(W-1, ox)), max(0, src)))
            t = (BAY[y%4][x%4] + .5)/16
            if c.lum(p) > thresh and t < fade * .95: c.px(x, y, p)
            elif c.lum(p) > thresh*.6 and t < fade * .45: c.px(x, y, glint)
    c.rect(0, HOR, W-1, HOR, lane)
    for x in range(0, W, 2): c.px(x, HOR+1, c.dth(x, HOR+1, base, glint, .5))
    for x in range(2, W, 14):
        c.rect(x, 103, x+5, 103, lane); c.rect(x+7, 98, x+9, 98, lane)
    for _ in range(14):
        x, y = c.r.randrange(2, W-6), c.r.randrange(HOR+3, H)
        c.rect(x, y, x+c.r.randint(2, 5), y, glint)


def rain(c, n, cols):
    for _ in range(n):
        x, y = c.r.randrange(W+4), c.r.randrange(HOR+6)
        col = c.r.choice(cols)
        for i in range(5):
            if i != 3 or c.r.random() < .5: c.px(x - i//2, y+i, col if i < 4 else cols[0])
    for _ in range(30):
        x, y = c.r.randrange(W), c.r.randrange(HOR+3, H)
        c.px(x-1, y, cols[0]); c.px(x+1, y, cols[0]); c.px(x, y-1, cols[1])


# ---------------------------------------------------------------- scene 04: giant mecha in the haze
def scene04():
    pal = [(3,2,10),(12,8,26),(30,18,54),(255,200,60),(255,255,255),(255,170,220),(255,60,90),(0,230,255),
           (60,255,140),(124,44,128),(70,38,108),(240,232,255),(214,56,170),(236,116,176),(110,60,150),(255,80,200)]
    c = C(pal, 4)
    c.sky([0,1,2,10,9,13], HOR)
    stars(c, 30, 30, [4,5,13])
    for y in range(HOR):
        for x in range(W):
            d = math.hypot((x-72)/46, (y-44)/50)
            if d < 1: c.px(x, y, c.dth(x, y, c.get(x, y), 9 if d > .55 else 13, (1-d)*1.3 if d > .55 else .5+(.55-d)))
    # far layer on a scratch canvas so the mecha can sit in front of it
    cf = C(pal, 40); cf.r = c.r
    cf.im.paste(c.im)
    far_layer(cf, buildings(c, 35, 95, 4, 10), 10, 9, 13, 13)
    for y in range(HOR):
        for x in range(W):
            if cf.get(x, y) != c.get(x, y) and cf.get(x, y) in (10, 9, 13) and cf.get(x, y) != c.dth(x, y, 0, 0, 0):
                pass
    # simply paste far buildings where they differ from the sky
    sk = C(pal, 0); sk.im.paste(c.im)
    for y in range(HOR):
        for x in range(W):
            if cf.get(x, y) != sk.get(x, y): c.px(x, y, cf.get(x, y))
    # mecha
    mk = Image.new("L", (W, H), 0); md = ImageDraw.Draw(mk)
    P = lambda pts: md.polygon(pts, fill=255)
    P([(66,14),(78,14),(80,20),(76,25),(68,25),(64,20)])
    P([(64,14),(61,7),(63,7),(66,13)]); P([(78,13),(81,7),(83,7),(79,14)])
    P([(68,24),(76,24),(77,29),(67,29)])
    P([(48,27),(67,29),(66,40),(46,40),(42,33)]); P([(77,29),(96,27),(102,33),(98,40),(78,40)])
    P([(61,29),(83,29),(85,48),(80,62),(64,62),(59,48)])
    P([(42,40),(54,40),(55,60),(51,72),(41,70),(43,54)]); P([(90,40),(102,40),(103,54),(105,70),(94,72),(89,60)])
    P([(60,60),(72,60),(71,88),(60,88)]); P([(72,60),(84,60),(84,88),(73,88)])
    for y in range(H):
        row = [x for x in range(W) if mk.getpixel((x, y))]
        if not row: continue
        for x in row:
            f = max(0, (y-48)/38)
            col = 1
            if x < 68 and (x+y) % 2 == 0: col = 2
            if x > 80 and (x+y) % 3 == 0: col = 0
            c.px(x, y, c.dth(x, y, col, 10, f*.9))
        c.px(row[0], y, 13 if y < 66 else 9)
        if y % 2 == 0 and len(row) > 3: c.px(row[-1], y, 2)
    for y in range(31, 62, 4):
        for x in range(63, 82):
            if mk.getpixel((x, y)): c.px(x, y, 2)
    c.rect(67,19,70,19,6); c.rect(74,19,77,19,6); c.px(68,20,5); c.px(76,20,5)
    c.bloom(68, 19, 5, 6, .8); c.bloom(76, 19, 5, 6, .8)
    for a in range(12): c.px(72+int(round(3*math.cos(a/12*6.28))), 42+int(round(3*math.sin(a/12*6.28))), 7)
    c.rect(71,41,73,43,7); c.px(72,42,4); c.bloom(72,42,10,7,.9)
    c.rect(50,32,58,33,15); c.rect(86,32,92,33,15)
    mid_layer(c, buildings(c, 14, 40, 6, 11), 2, 14, [12,13,3,7], .3)
    near_layer(c, buildings(c, 12, 32, 8, 16), 1, 2, [3,3,5,7,15,12], [15,7,12,6,3], 13)
    for x, y, d, col in [(10,30,1,2),(95,40,-1,1),(30,50,1,2),(70,24,-1,1),(105,58,1,2)]:
        car(c, x, y, d, col, 6, 4, 6)
    street(c, 0, 1, 14, 14, 70)
    rain(c, 55, [9, 13])
    return c


# ---------------------------------------------------------------- scene 05: ringed planet + suspension bridge
def scene05():
    pal = [(2,5,14),(6,12,28),(16,30,58),(255,196,70),(255,255,255),(255,214,160),(255,84,70),(0,235,255),
           (70,255,150),(176,84,44),(34,66,112),(244,244,255),(54,112,170),(100,160,200),(70,100,150),(255,150,60)]
    c = C(pal, 5)
    c.sky([0,1,2,10,12,13], HOR)
    stars(c, 40, 40, [4,5,13,13])
    cx, cy, R = 60, 38, 26

    def ring(front):
        for t in range(0, 900):
            a = t/900*6.2832
            for k, rx in enumerate((44, 41, 37)):
                x = cx + rx*math.cos(a); y = cy + rx*.26*math.sin(a)
                x2 = x + (y-cy)*.35; y2 = y - (x-cx)*.17
                if (math.sin(a) > 0) == front:
                    xi, yi = int(round(x2)), int(round(y2))
                    if front or math.hypot(xi-cx, yi-cy) >= R - .5:
                        c.px(xi, yi, (5, 14, 9)[k] if (k < 2 or (xi + yi) % 2 == 0) else 10)
    ring(False)
    for y in range(cy-R, cy+R+1):
        for x in range(cx-R, cx+R+1):
            d = math.hypot(x-cx, y-cy)
            if d <= R:
                lit = max(0, 1 - math.hypot((x-cx+8)/R, (y-cy+8)/R)*.7)
                v = min(1, max(0, lit + .12*math.sin((y-cy)*.55 + math.sin(x*.2)*1.2)))
                stops = [2, 9, 15, 5]; t = v*3; i = min(int(t), 2)
                c.px(x, y, c.dth(x, y, stops[i], stops[i+1], t-i))
    for px_, py_, rr in [(70,30,4),(52,50,3)]:
        for a in range(0, 360, 20):
            c.px(int(px_+rr*math.cos(math.radians(a))), int(py_+rr*.5*math.sin(math.radians(a))), 6 if rr > 3 else 9)
    ring(True)
    c.bloom(cx, cy, 36, 15, .35)
    far_layer(c, buildings(c, 28, 70, 4, 9), 10, 12, 13, 13)
    mid_layer(c, buildings(c, 20, 55, 6, 11), 2, 14, [13,3,7,15], .28)
    BY = 62
    for tx in (22, 98):
        c.rect(tx-1, 36, tx+1, HOR, 1); c.rect(tx-1, 36, tx-1, HOR, 14); c.rect(tx-3, 36, tx+3, 37, 2)
        c.rect(tx-2, 50, tx+2, 50, 14); c.px(tx, 34, 6); c.px(tx, 35, 6); c.bloom(tx, 34, 6, 6, .8)
        for y in range(40, BY, 6): c.px(tx, y, 3)
    c.rect(0, BY, W-1, BY+2, 1); c.rect(0, BY, W-1, BY, 14)
    for x in range(1, W, 3): c.px(x, BY+3, 2); c.px(x, BY+2, c.dth(x, BY, 1, 3, .35))
    # main span cable (sag between towers) and side cables (tower top to deck ends)
    for x in range(22, 99):
        t = (x-22)/76; y = int(BY - 4 - (BY-42)*(2*t-1)**2)
        c.px(x, y, 3 if x % 4 == 0 else 14)
        if x % 4 == 0 and y + 1 < BY: c.rect(x, y+1, x, BY-1, 14)
    for x in range(0, 22):
        y = int(36 + (BY-38) * (1 - x/22)); c.px(x, y, 14 if x % 4 else 3)
    for x in range(99, 120):
        y = int(36 + (BY-38) * ((x-98)/21)); c.px(x, y, 14 if x % 4 else 3)
    for x in range(2, W, 6): c.px(x, BY-1, 3)
    c.bloom(60, BY, 16, 3, .25)
    near_layer(c, buildings(c, 15, 45, 8, 16), 1, 2, [3,3,5,7,15,13], [15,7,12,6,8], 13)
    for x, y, d, col in [(8,48,1,2),(80,66,-1,1),(40,57,1,2),(104,30,-1,2)]:
        car(c, x, y, d, col, 6, 4, 6)
    street(c, 0, 1, 12, 14, 70)
    rain(c, 55, [12, 13])
    return c


# ---------------------------------------------------------------- scene 06: moon, pagoda, dragon airship
def scene06():
    pal = [(2,8,8),(6,16,16),(14,36,36),(255,198,60),(255,255,255),(255,226,170),(255,90,60),(0,240,240),
           (90,255,120),(54,112,84),(30,70,66),(246,246,230),(190,150,60),(120,196,150),(60,104,96),(255,140,40)]
    c = C(pal, 6)
    c.sky([0,1,2,10,9,13], HOR)
    stars(c, 26, 36, [4,5,13])
    mx, my, R = 95, 22, 12
    for y in range(my-R, my+R+1):
        for x in range(mx-R, mx+R+1):
            d = math.hypot(x-mx, y-my)
            if d <= R:
                v = max(0, 1 - math.hypot(x-mx+4, y-my+4)/(R*1.5))
                col = c.dth(x, y, 5, 11, min(1, v*1.6))
                if d > R-1.2: col = c.dth(x, y, col, 5, .6)
                c.px(x, y, col)
    for dx, dy, r in [(-4,-2,3),(3,4,2),(4,-4,1),(-2,6,1)]:
        for y in range(-r, r+1):
            for x in range(-r, r+1):
                if x*x+y*y <= r*r: c.px(mx+dx+x, my+dy+y, c.dth(mx+dx+x, my+dy+y, 5, 12, .55))
    c.bloom(mx, my, 22, 10, .5)
    # dragon airship (head left, tail rising right)
    pts = []
    for i in range(46):
        t = i/45
        pts.append((8 + t*72, 54 + 9*math.sin(t*9.4) - t*26, 5.0 - 3.6*t))
    for x, y, r in pts:
        ri = max(1, int(round(r*.8)))
        for yy in range(-ri, ri+1):
            for xx in range(-ri, ri+1):
                if xx*xx+yy*yy <= ri*ri+1:
                    X, Y = int(x)+xx, int(y)+yy
                    c.px(X, Y, 1 if yy < ri*.2 else c.dth(X, Y, 2, 1, .5))
        if int(x) % 3 == 0: c.px(int(x), int(y)-ri-1, 14)
        c.px(int(x), int(y)-ri, 14)
    hx, hy = int(pts[0][0]), int(pts[0][1])
    c.rect(hx-6, hy-1, hx-2, hy+1, 1); c.px(hx-7, hy, 1); c.px(hx-1, hy-1, 6); c.px(hx, hy-1, 6)
    for a, b in ((-3, -4), (-2, -5), (2, -5), (3, -6)): c.px(hx+a, hy+b, 14)
    for i in range(0, 46, 6):
        x, y, r = pts[i]; c.px(int(x), int(y), 15); c.bloom(x, y, 4, 15, .5)
    far_layer(c, buildings(c, 15, 50, 4, 9), 10, 9, 13, 13)
    mid_layer(c, buildings(c, 12, 42, 6, 10), 2, 9, [13,3,8,5], .25)
    # pagoda
    p0 = 40
    c.rect(p0-1, 14, p0+1, 66, 1)
    c.rect(p0, 6, p0, 14, 1); c.px(p0, 5, 6); c.bloom(p0, 5, 7, 6, .9)
    for i, (hw, ty) in enumerate([(8, 16), (11, 26), (14, 36), (17, 47), (20, 58)]):
        c.rect(p0-hw+3, ty+2, p0+hw-3, ty+9, 1)
        for x in range(p0-hw+4, p0+hw-3, 3): c.rect(x, ty+4, x, ty+6, 3 if (x+i) % 2 else 15)
        for k in range(hw + 1):
            lift = max(0, (k-(hw-4))//2)
            c.px(p0-k, ty+1-lift, 2); c.px(p0+k, ty+1-lift, 2)
        for x in range(p0-hw, p0+hw+1): c.px(x, ty+2, 9 if x % 2 else 2)
        c.px(p0-hw, ty+3, 3); c.px(p0+hw, ty+3, 3)
        c.bloom(p0, ty+5, 12, 15, .3)
    c.rect(p0-9, 66, p0+9, HOR, 1); c.rect(p0-9, 66, p0-9, HOR, 9)
    for x in range(p0-7, p0+8, 3): c.rect(x, 70, x+1, 72, 3)
    near_layer(c, buildings(c, 10, 35, 8, 16), 1, 9, [3,3,5,7,8,15], [8,7,15,6,3], 13)
    for x0 in range(0, 119, 24):
        for x in range(x0, x0+24):
            y = int(HOR-12 + 5*math.sin((x-x0)/24*3.14159)); c.px(x, y, 14)
            if (x-x0) % 6 == 3:
                c.rect(x, y+1, x, y+2, 6 if x % 12 == 3 else 3)
    for x, y, d, col in [(14,62,1,2),(70,20,-1,1),(100,50,1,2),(28,35,-1,1),(66,70,-1,2)]:
        car(c, x, y, d, col, 6, 4, 6)
    street(c, 0, 1, 13, 14, 70)
    rain(c, 55, [9, 13])
    return c


if __name__ == "__main__":
    ims = []
    for n, f in ((4, scene04), (5, scene05), (6, scene06)):
        c = f(); c.im.save(os.path.join(HERE, "scene%02d.png" % n)); ims.append(c.im)
    pv = Image.new("RGB", (W*3 + 8, H), (20, 20, 20))
    for i, im in enumerate(ims): pv.paste(im.convert("RGB"), (i*(W+4), 0))
    pv.resize((pv.width*3, pv.height*3), Image.Resampling.NEAREST).save(os.path.join(HERE, "preview_b.png"))
    for n, im in zip((4, 5, 6), ims):
        im.resize((W*4, H*4), Image.Resampling.NEAREST).convert("RGB").save(os.path.join(HERE, "_x4_%02d.png" % n))
