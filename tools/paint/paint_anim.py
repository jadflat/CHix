# Generates animation sprite sheets into tools/paint/anim/ (run: python tools/paint/paint_anim.py)
import math, os, random
from PIL import Image, ImageDraw
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anim")
os.makedirs(D + "/preview", exist_ok=True)
PAL = [tuple(int(l.strip()[i:i+2], 16) for i in (0, 2, 4)) for l in open(D + "/palette.txt") if l.strip()]
K = 15
INFO = []


def sheet(name, w, h, frames, delay, note=""):
    n = len(frames)
    flat = [c for p in PAL for c in p]
    im = Image.new("P", (w * n, h), K)
    im.putpalette(flat)
    for i, f in enumerate(frames):
        fi = Image.new("P", (w, h), K)
        fi.putpalette(flat)
        d = ImageDraw.Draw(fi)
        f(d, i)
        im.paste(fi, (i * w, 0))
    im.save(f"{D}/{name}.png")
    INFO.append(f"{name}.png  frame {w}x{h}  frames {n}  delay {delay}  {note}")
    sc = 6
    fr = []
    for t in range(n * 3):
        k = t % n
        box = (k * w, 0, k * w + w, h)
        bg = Image.new("RGB", (w + 4, h + 4), (14, 18, 40))
        c = im.crop(box).convert("RGB")
        m = im.crop(box).point(lambda v: 0 if v == K else 255).convert("L")
        bg.paste(c, (2, 2), m)
        fr.append(bg.resize((bg.width * sc, bg.height * sc), Image.NEAREST))
    fr[0].save(f"{D}/preview/{name}.gif", save_all=True, append_images=fr[1:],
               duration=max(1, delay) * 33, loop=0)


def px(d, pts, c):
    for x, y in pts:
        d.point((x, y), c)


def car(kind):
    def f(d, i):
        lit = i == 0
        if kind == 0:  # sleek coupe
            d.rectangle((2, 4, 21, 7), 2)
            d.rectangle((5, 2, 16, 4), 1)
            d.rectangle((7, 3, 14, 4), 7)
            d.line((2, 4, 21, 4), 5)
            d.line((3, 8, 20, 8), 12)
            d.point((20, 5), 3 if lit else 14)
            d.point((21, 5), 4)
            d.line((1, 5, 1, 6), 6 if lit else 11)
            px(d, [(6, 9), (17, 9)], 7 if lit else 2)
        elif kind == 1:  # hover tram
            d.rectangle((0, 2, 23, 7), 13)
            d.rectangle((0, 2, 23, 3), 5)
            for x in range(2, 22, 4):
                d.rectangle((x, 4, x + 2, 5), 3 if (x // 4 + i) % 2 == 0 else 14)
            d.line((0, 6, 23, 6), 12)
            d.line((0, 7, 23, 7), 1)
            d.line((2, 8, 21, 8), 7 if lit else 2)
            d.point((23, 3), 6)
        else:  # boxy cargo
            d.rectangle((1, 2, 16, 7), 12)
            d.rectangle((17, 4, 22, 7), 9)
            d.rectangle((18, 4, 21, 5), 7)
            d.line((1, 5, 16, 5), 6)
            d.line((1, 2, 16, 2), 13)
            d.point((22, 6), 14 if lit else 3)
            d.point((0, 4), 11 if lit else 6)
            d.line((3, 8, 20, 8), 2)
            px(d, [(8, 9), (14, 9)], 7 if lit else 9)
    return f


for k, nm in enumerate(["car_coupe", "car_tram", "car_cargo"]):
    sheet(nm, 24, 10, [car(k)] * 2, 8, "light flicker")


def blimp(d, i):
    d.ellipse((0, 1, 35, 11), 13)
    d.ellipse((1, 1, 34, 6), 5)
    d.line((6, 10, 29, 10), 12)
    d.polygon([(2, 5), (0, 0), (6, 3)], 12)
    d.polygon([(2, 7), (0, 12), (6, 9)], 12)
    d.rectangle((9, 4, 28, 8), 0)
    cols = (10, 7, 3, 11)
    for x in range(20):
        for y in range(5):
            xx = x + i * 2
            if (xx * 7 + y * 3 + xx // 3 * y) % 5 < 2:
                d.point((9 + x, 4 + y), cols[xx // 5 % 4])
    d.rectangle((15, 12, 22, 14), 12)
    d.line((16, 13, 21, 13), 3)
    d.point((33, 6), 6 if i % 2 == 0 else 12)


sheet("blimp", 36, 16, [blimp] * 6, 6, "ad scrolls 2px a frame; tail light blinks")


def neon(d, i):
    d.rectangle((0, 0, 15, 7), 0)
    d.rectangle((0, 0, 15, 7), None, 12)
    a = [7, 7, 1, 7][i]
    b = [7, 10, 2, 10][i]
    on = i != 2
    d.line((3, 2, 12, 2), a)
    d.line((3, 5, 12, 5), b)
    d.line((3, 2, 3, 5), a)
    d.line((12, 2, 12, 5), b)
    d.point((7, 3), 4 if on else 1)
    d.point((8, 4), 4 if on else 1)


sheet("neon_sign", 16, 8, [neon] * 4, 4, "flicker, irregular: play 0,1,0,2,3,1")


def radar(d, i):
    a = i * math.pi / 4
    d.rectangle((5, 8, 6, 11), 12)
    d.rectangle((3, 11, 8, 11), 13)
    for t in range(-5, 6):
        x = 5.5 + t * math.cos(a) * 0.9
        y = 5 + t * math.sin(a) * 0.4
        d.point((round(x), round(y)), 5 if t < 2 else 13)
    d.line((5, 6, 5, 8), 13)
    d.point((5, 2), 6 if i % 2 == 0 else 12)


sheet("radar", 12, 12, [radar] * 8, 5, "rotating dish + blinking tip")


def rain(h):
    def f(d, i):
        for y in range(h):
            d.point((0, y), 2 if y < h - 1 else (7 if h > 2 else 5))
        if h > 3:
            d.point((0, 1), 13)
    return f


sheet("rain_far", 1, 2, [rain(2)], 1, "depth 1: fall 3 px/frame, dim")
sheet("rain_mid", 1, 3, [rain(3)], 1, "depth 2: fall 5 px/frame")
sheet("rain_near", 1, 4, [rain(4)], 1, "depth 3: fall 8 px/frame, brightest")


def ripple(d, i):
    rx = [1, 2, 3, 4][i]
    ry = [0, 1, 1, 2][i]
    col = [4, 7, 5, 2][i]
    if i == 0:
        px(d, [(3, 1), (4, 1), (5, 1)], 4)
    else:
        d.ellipse((4 - rx, 1 - ry + (1 if ry > 1 else 0), 4 + rx, 1 + ry + (1 if ry > 1 else 0)), None, col)


sheet("ripple", 9, 4, [ripple] * 4, 3, "splash ring on the street, one-shot")


def steam(d, i):
    for k in range(7):
        t = (i * 2 + k * 2) % 14
        y = 10 - t
        x = 3 + round(math.sin((t + k) * .6) * 1.5) + t // 5
        c = 4 if t < 4 else 5 if t < 9 else 13
        if t < 11:
            d.rectangle((x, y, x + (t > 3), y), c)
    d.rectangle((2, 11, 5, 11), 12)


sheet("steam", 8, 12, [steam] * 7, 4, "loops")


def bolt(shape):
    pts = [[(8, 0), (6, 6), (10, 10), (7, 16), (11, 22), (8, 31)],
           [(4, 0), (7, 7), (5, 12), (9, 19), (8, 25), (12, 31)],
           [(11, 0), (9, 5), (11, 11), (6, 17), (8, 23), (4, 31)]][shape]

    def f(d, i):
        for a, b in zip(pts, pts[1:]):
            d.line((a[0] + 1, a[1], b[0] + 1, b[1]), 2)
        for a, b in zip(pts, pts[1:]):
            d.line(a + b, 5)
        d.line((pts[2][0], pts[2][1], pts[2][0] - 4, pts[2][1] + 7), 5)
        for a in pts:
            d.point(a, 4)
    return f


sheet("lightning", 16, 32, [bolt(0), bolt(1), bolt(2)], 3, "3 alternative shapes; pick one per strike")


def burst(d, i):
    c = 8
    r = i * 1.6 + 1
    col = [4, 14, 7, 8, 7, 2][i]
    for k in range(8):
        a = k * math.pi / 4 + i * .2
        d.point((round(c + r * math.cos(a)), round(c + r * math.sin(a))), col)
        if i < 4:
            d.point((round(c + r * .5 * math.cos(a)), round(c + r * .5 * math.sin(a))), 4 if i < 2 else 7)
    if i < 2:
        d.ellipse((c - 2 + i, c - 2 + i, c + 2 - i, c + 2 - i), 4)


sheet("claim_burst", 16, 16, [burst] * 6, 2, "one-shot, cyan/white")


def boom(d, i):
    c = 12
    r = [2, 4, 6, 8, 9, 10, 10, 10][i]
    if i < 6:
        d.ellipse((c - r, c - r, c + r, c + r), [14, 3, 11, 11, 6, 6][i])
        d.ellipse((c - r // 2, c - r // 2, c + r // 2, c + r // 2), [4, 4, 14, 3, 11, 9][i])
    rnd = random.Random(i)
    for k in range(10 + i * 2):
        a = rnd.random() * 6.28
        rr = rnd.uniform(r * .6, r + 2 + i * .5)
        d.point((round(c + rr * math.cos(a)), round(c + rr * math.sin(a))), [4, 14, 3, 11, 6, 9, 12, 1][i])


sheet("spark_boom", 24, 24, [boom] * 8, 2, "one-shot")


def sparkle(d, i):
    c = 6
    arm = [1, 3, 5, 4, 2, 1][i]
    col = [4, 14, 4, 7, 7, 2][i]
    d.line((c - arm, c, c + arm, c), col)
    d.line((c, c - arm, c, c + arm), col)
    d.point((c, c), 4)
    if 1 < i < 5:
        px(d, [(c - 3, c - 3), (c + 3, c + 3), (c + 3, c - 3), (c - 3, c + 3)], 14 if i % 2 else 3)


sheet("pickup_sparkle", 12, 12, [sparkle] * 6, 3, "one-shot")


def star(d, i):
    c = 6
    s = [3, 5, 4, 5][i]
    col = [3, 14, 4, 14][i]
    d.polygon([(c, c - s), (c + 1, c - 1), (c + s, c), (c + 1, c + 1), (c, c + s),
               (c - 1, c + 1), (c - s, c), (c - 1, c - 1)], col)
    d.point((c, c), 4)
    if i == 2:
        px(d, [(c + 4, c - 4), (c - 4, c + 4)], 11)


sheet("combo_star", 12, 12, [star] * 4, 4, "pulses; loop while combo shows")

open(D + "/README.txt", "w", newline="\n").write(
    "CHix animation sheets. Indexed PNG (mode P), palette = palette.txt, index 15 (#FF00FF) = transparent.\n"
    "Frames are side by side. Delay = game frames (30 fps) per animation frame.\n"
    "Regenerate: python tools/paint/paint_anim.py\n\n" + "\n".join(INFO) + "\n")
