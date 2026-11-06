"""Parallax prototype: layers + drifting GIF. Run: python tools/paint/parallax.py
Uses tools/paint/sceneNN.png if present (row-band decomposition), else a synthetic scene."""
import os, random, math
from PIL import Image
D = os.path.dirname(os.path.abspath(__file__)); L = os.path.join(D, "layers")
os.makedirs(L, exist_ok=True)
VW, VH = 120, 112
# layer: width, first row, rows
FAR, MID, NEAR = (144, 0, 64), (168, 48, 64), (192, 56, 56)
PAL = [(0,0,0),(18,10,40),(40,20,70),(255,200,40),(255,255,255),(255,120,200),(255,60,60),(0,230,255),
       (60,255,120),(80,40,110),(60,40,90),(230,230,255),(34,24,60),(24,16,44),(70,70,140),(255,90,220)]

def synth(rng):
    far = [[0]*FAR[0] for _ in range(FAR[2])]
    for y in range(FAR[2]):
        for x in range(FAR[0]):
            t = y*3//FAR[2]  # 0..2 gradient with dither
            v = 1 if (t==0 or (t==1 and (x+y)&1==0)) else (2 if t>=1 else 1)
            far[y][x] = v
    for _ in range(40): far[rng.randrange(40)][rng.randrange(FAR[0])] = 4
    cx, cy, r = 80, 22, 11
    for y in range(FAR[2]):
        for x in range(FAR[0]):
            if (x-cx)**2+(y-cy)**2 <= r*r: far[y][x] = 11 if (x-cx)**2+(y-cy)**2 < (r-2)**2 else 5
    mid = [[0]*MID[0] for _ in range(MID[2])]
    x = 0
    while x < MID[0]:
        w = rng.randrange(8, 20); h = rng.randrange(14, 40)
        for xx in range(x, min(x+w, MID[0])):
            for yy in range(MID[2]-h, MID[2]):
                mid[yy][xx] = 10 if (xx-x) < w-2 else 9
        for wy in range(MID[2]-h+3, MID[2]-2, 4):
            for wx in range(x+2, min(x+w-2, MID[0]), 4):
                if rng.random() < .35: mid[wy][wx] = 3
        x += w + rng.randrange(0, 3)
    near = [[0]*NEAR[0] for _ in range(NEAR[2])]
    x = 0
    while x < NEAR[0]:
        w = rng.randrange(16, 34); h = rng.randrange(18, 44)
        for xx in range(x, min(x+w, NEAR[0])):
            for yy in range(NEAR[2]-h, NEAR[2]):
                near[yy][xx] = 13 if (xx-x) > 1 else 14
        for wy in range(NEAR[2]-h+4, NEAR[2]-10, 6):
            for wx in range(x+3, min(x+w-3, NEAR[0]), 5):
                if rng.random() < .4: near[wy][wx] = rng.choice((3,3,7,15))
        sx = x+w//2
        if rng.random() < .6 and sx+3 < NEAR[0]:
            for i in range(6):
                near[NEAR[2]-h-3+(i//3)][sx-3+i] = rng.choice((7,15))
        x += w
    for yy in range(NEAR[2]-8, NEAR[2]):  # street, opaque
        for xx in range(NEAR[0]):
            near[yy][xx] = 12 if (xx//6+yy)%7 else 7 if yy==NEAR[2]-4 and xx%3==0 else 12
    return far, mid, near

def from_scene(path):
    """Heuristic split of a painted 120x112 scene into bands; mirror-extend sideways."""
    im = Image.open(path); px = im.load(); pal = im.getpalette()[:48]
    pal = [tuple(pal[i*3:i*3+3]) for i in range(16)]
    def band(spec, y0, y1, keep):
        W, y0_, n = spec; out = []
        for y in range(n):
            sy = min(VH-1, y0_+y); row = []
            for x in range(W):
                m = (x - (W-VW)//2) % (2*VW); m = m if m < VW else 2*VW-1-m
                v = px[m, sy]
                row.append(v if (keep or v) and y0_+y < y1 else 0)
            out.append(row)
        return out
    return pal, band(FAR,0,VH,True), band(MID,48,VH,False), band(NEAR,56,VH,False)

def save(name, grid, pal):
    im = Image.new("P", (len(grid[0]), len(grid)))
    im.putpalette([c for p in pal for c in p]); im.putdata([v for r in grid for v in r]); im.save(name)

def compose(layers, offs, rng_view=(VW, VH)):
    out = [[0]*VW for _ in range(VH)]
    for (spec, g), o in zip(layers, offs):
        W, y0, n = spec
        for y in range(n):
            if y0+y >= VH: break
            row = g[y]; dst = out[y0+y]
            for x in range(VW):
                v = row[x+o]
                if v or spec is FAR: dst[x] = v
    return out

def main():
    rng = random.Random(7)
    sc = os.path.join(D, "scene00.png")
    if os.path.exists(sc): pal, far, mid, near = from_scene(sc); src = "scene00.png"
    else: pal = PAL; far, mid, near = synth(rng); src = "synthetic"
    for n, g in (("far", far), ("mid", mid), ("near", near)): save(os.path.join(L, f"scene00_{n}.png"), g, pal)
    layers = [(FAR, far), (MID, mid), (NEAR, near)]
    # reveal mask: 2x2 cells, 60x56, blobs grow; claimed fraction by frame
    order = sorted(((x, y) for x in range(60) for y in range(56)),
                   key=lambda c: math.hypot(c[0]-30, c[1]-28) + rng.random()*14)
    frames = []; N = 96
    for f in range(N):
        frac = 0.18 + 0.52*f/(N-1)
        cells = set(order[:int(frac*3360)])
        cam = int(round(72*(1-abs(1-2*f/(N-1)))))  # 0..72..0
        offs = (cam//3, cam*2//3, cam)
        img = compose(layers, offs)
        o = Image.new("P", (VW*3, VH*3)); o.putpalette([c for p in pal for c in p])
        d = []
        for y in range(VH):
            r = [img[y][x] if ((x//2, y//2) in cells) else 0 for x in range(VW)]
            r3 = [v for v in r for _ in range(3)]
            d += r3*3
        o.putdata(d); frames.append(o)
    frames[0].save(os.path.join(D, "preview_parallax.gif"), save_all=True, append_images=frames[1:], duration=50, loop=0)
    print("source", src, "frames", N)
main()
