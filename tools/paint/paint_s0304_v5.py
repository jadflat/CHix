"""CHix scene03 / scene04 clean-up (v5) from the v4/ copies.

python paint_s0304_v5.py  ->  scene03.png, scene04.png, preview_s03v5.png, preview_s04v5.png
Palettes are kept exactly; only pixels change.
"""
import os
from collections import Counter
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 120, 112
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def load(name):
    im = Image.open(os.path.join(HERE, 'v4', name))
    p = im.load()
    return im.getpalette()[:48], [[p[x, y] for x in range(W)] for y in range(H)]


def save(name, pal, g):
    im = Image.new('P', (W, H))
    im.putpalette(pal + [0] * (768 - len(pal)))
    im.putdata([g[y][x] for y in range(H) for x in range(W)])
    im.save(os.path.join(HERE, name))
    return im


def preview(name, old, new):
    a = old.convert('RGB').resize((W * 4, H * 4), Image.Resampling.NEAREST)
    b = new.convert('RGB').resize((W * 4, H * 4), Image.Resampling.NEAREST)
    out = Image.new('RGB', (W * 8 + 8, H * 4), (40, 40, 40))
    out.paste(a, (0, 0))
    out.paste(b, (W * 4 + 8, 0))
    out.save(os.path.join(HERE, name))


def ramp(level, x, y, ladder):
    """Ordered (Bayer 4x4) dither of a float level along a colour ladder."""
    level = max(0.0, min(len(ladder) - 1.0, level))
    i = int(level)
    f = level - i
    if i >= len(ladder) - 1:
        return ladder[-1]
    return ladder[i + 1] if f * 16 > BAYER[y & 3][x & 3] + 0.5 else ladder[i]


def inbox(x, y, boxes):
    return any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in boxes)


def is_orphan(g, x, y):
    c = g[y][x]
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if (dx or dy) and 0 <= x + dx < W and 0 <= y + dy < H and g[y + dy][x + dx] == c:
                return False
    for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
        if 0 <= x + dx < W and 0 <= y + dy < H and g[y + dy][x + dx] == c:
            return False
    return True


def despeckle(g, keep=(), colours=None, passes=3, strict=()):
    """Replace orphans (and, for `strict` colours, pixels with no 4-neighbour
    of their colour) by the commonest neighbour colour."""
    for _ in range(passes):
        out = [r[:] for r in g]
        for y in range(H):
            for x in range(W):
                c = g[y][x]
                if inbox(x, y, keep) or (colours is not None and c not in colours):
                    continue
                lone = is_orphan(g, x, y)
                if not lone and c in strict:
                    lone = not any(0 <= x + dx < W and 0 <= y + dy < H and g[y + dy][x + dx] == c
                                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                                                  (2, 0), (-2, 0), (0, 2), (0, -2)))
                if lone:
                    n = Counter(g[y + dy][x + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                                if (dx or dy) and 0 <= x + dx < W and 0 <= y + dy < H
                                and g[y + dy][x + dx] != c)
                    out[y][x] = n.most_common(1)[0][0]
        g = out
    return g


def unstreak(g, keep, colours):
    """Remove thin slanted 1-px lines (painted rain) of the given colours."""
    seen = set()
    out = [r[:] for r in g]
    for y in range(H):
        for x in range(W):
            c = g[y][x]
            if c not in colours or (x, y) in seen:
                continue
            comp, st = [], [(x, y)]
            seen.add((x, y))
            while st:
                px, py = st.pop()
                comp.append((px, py))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        q = (px + dx, py + dy)
                        if 0 <= q[0] < W and 0 <= q[1] < H and q not in seen and g[q[1]][q[0]] == c:
                            seen.add(q)
                            st.append(q)
            xs = [p[0] for p in comp]
            ys = [p[1] for p in comp]
            w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
            thin = len(comp) <= max(w, h) + 1
            slanted = 2 <= w <= h / 2 + 1 or 2 <= h <= w / 2 + 1
            if thin and slanted and max(w, h) >= 3 and not any(inbox(px, py, keep) for px, py in comp):
                for px, py in comp:
                    n = Counter(g[py + dy][px + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                                if 0 <= px + dx < W and 0 <= py + dy < H and g[py + dy][px + dx] != c)
                    out[py][px] = n.most_common(1)[0][0]
    return out


# ---------------------------------------------------------------- scene03
def scene03():
    pal, g = load('scene03.png')
    o = [r[:] for r in g]
    MX, MY, MR = 97.5, 19.5, 14.3          # red moon
    sky_ladder = [0, 1, 10, 2, 9]
    keep_sky = [(46, 28, 62, 32), (55, 0, 62, 4)]   # small ship, star

    def moon_d(x, y):
        return ((x - MX) ** 2 + (y - MY) ** 2) ** 0.5

    # 1. sky: a calm ordered-dither gradient, warm at the horizon, halo round the moon
    for y in range(H):
        for x in range(W):
            sky = (y <= 32 and x >= 34) or (y <= 11) or (y <= 31 and x <= 11)
            if not sky or inbox(x, y, keep_sky):
                continue
            d = moon_d(x, y)
            if d <= MR + 0.5:
                continue
            if y >= 26 and x >= 84 and o[y][x] not in (0, 1, 2, 9, 10, 13):
                continue                    # blade tip
            L = 0.1 + 1.7 * (y / 32.0) ** 1.4
            L += 1.7 * max(0.0, 1 - (d - MR) / 9.0)
            L += 0.9 * max(0.0, 1 - ((x - 10) ** 2 + (y - 40) ** 2) ** 0.5 / 34.0)
            g[y][x] = ramp(L, x, y, sky_ladder)

    # 2. de-speckle the city, blade and moon (signs and lights kept)
    keep = keep_sky + [(106, 53, 117, 72), (55, 77, 68, 87), (66, 87, 101, 91),
                       (93, 81, 104, 88), (98, 34, 110, 52)]
    g = despeckle(g, keep=keep)
    # lone sparks inside the buildings (right of the fire): strict test
    g = despeckle(g, keep=keep + [(0, 55, 56, 95)], colours={12, 6, 13, 9, 3, 4, 11, 5},
                  strict={12, 6, 13, 9, 3, 4, 11, 5}, passes=2)
    for y in range(33):
        for x in range(W):
            if g[y][x] in (13, 9) and moon_d(x, y) > MR + 0.5 and x < 84:
                g[y][x] = o[y][x] if o[y][x] in (0, 1, 2, 10) else 1

    # 3. street: clean scan-line reflection of the fire and signs
    refl = {4: 3, 3: 12, 12: 9, 6: 9, 8: 8, 7: 7, 15: 15, 5: 14, 11: 14, 14: 14}
    for y in range(96, H):
        k = y - 96
        sy = 94 - k
        for x in range(W):
            c = o[sy][x] if sy >= 33 else 0
            on = (k % 2 == 0) and (k < 8 or (x + y // 2) % 2 == 0)
            if on and c in refl:
                g[y][x] = refl[c]
            elif x < 50 and (k % 2 == 0) and k < 10 and o[sy][x] in (12, 3, 4, 6):
                g[y][x] = 9
            else:
                g[y][x] = 0

    g = despeckle(g, keep=keep, passes=2)
    # 4. a few deliberate embers drifting up from the fire
    for x, y in ((6, 49), (17, 42), (29, 51), (41, 46), (12, 35), (33, 39), (48, 56)):
        g[y][x] = g[y + 1][x - 1] = 12
        g[y + 2][x - 2] = 9
    return pal, g


# ---------------------------------------------------------------- scene04
def scene04():
    pal, g = load('scene04.png')
    MX, MY, MR = 68, 34, 36.5               # pale moon
    core = (54, 30, 82, 46)
    blast = (0, 30, 46, 62)
    flash = (0, 60, 24, 67)                 # the white muzzle flash
    signs = [(0, 66, 16, 98), (96, 58, 119, 81), (96, 82, 119, 98), (98, 42, 118, 45),
             (5, 17, 22, 21), (97, 10, 109, 15), (100, 47, 104, 56), (40, 45, 50, 49)]
    keep = [core, blast, flash] + signs
    g = despeckle(g, keep=keep)
    every = set(range(16))
    # sky outside the moon: only the dark ramp (the game draws the rain)
    for _ in range(3):
        for y in range(32):
            for x in range(W):
                if ((x - MX) ** 2 + (y - MY) ** 2) ** 0.5 > MR + 1 and not inbox(x, y, keep)                         and g[y][x] not in (0, 1, 2):
                    n = Counter(g[y + dy][x + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                                if 0 <= x + dx < W and 0 <= y + dy < H and g[y + dy][x + dx] in (0, 1, 2))
                    g[y][x] = n.most_common(1)[0][0] if n else 0
    g = unstreak(g, keep, {13, 10, 14, 5, 4, 11})
    # lit windows below the skyline: warm orange, not white dots
    for y in range(56, H):
        for x in range(W):
            if g[y][x] == 4 and not inbox(x, y, keep):
                g[y][x] = 12
    # mecha and moon edge: white / pink / lavender specks
    g = despeckle(g, keep=keep, colours={4, 5, 13, 11, 15, 3, 12, 6},
                  strict={4, 5, 13, 11, 15, 3, 12, 6}, passes=2)
    # lower third: every colour, so only windows in rows/columns stay
    lower = keep + [(0, 0, W - 1, 45), (0, 87, W - 1, 89)]
    g = despeckle(g, keep=lower, colours=every - {0, 1, 2, 10},
                  strict=every - {0, 1, 2, 10}, passes=3)
    return pal, g


def run(name, fn):
    pal, g = fn()
    new = save(name, pal, g)
    preview('preview_%sv5.png' % name[:7].replace('scene', 's'), Image.open(os.path.join(HERE, 'v4', name)), new)


if __name__ == '__main__':
    run('scene03.png', scene03)
    run('scene04.png', scene04)
