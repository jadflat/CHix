"""Builds CHIX.DAT (the art on the SD card) and CHix/CardIndex.h (its hash, offsets and sprite table).

  block 0            "CHIXCARD", u32 hash (CRC-32 of the rest)
  scene NN (0..9)    at CARD_SCENE + NN * CARD_SCENE_STRIDE: 14 blocks of picture (120x112, 4 bits a pixel, left pixel in
                     the LOW nibble, 60 B a row, EIGHT rows to a block so a row never crosses a block), then the scene's
                     sprite blocks (below), then a block with the scene's 16 RGB entries.
  screens (5)        title, menu, clear, gameover, victory: 128x128, 64 B a row, 8 rows a block (a block is a copy of 8 screen
                     rows), 16 blocks, then a block: 16 RGB entries, then 5 text-colour roles (light, accent, gold, dim, dark).
  CARD_SET           the last two blocks, 0xFF: the save mirror (Card.cpp putSave); not in the hash, the game writes no other block
  sprites            one region a scene, right after its picture (so one multi-block read gets both): every sprite and animation frame remapped to the
                     nearest colours of THAT scene's palette (colour 15 = transparent; the enemy cores keep their fixed indices), packed so no frame crosses a block.
                     CardIndex.h: SPR[id] = { offset in the region, w, h }.

Reads tools/paint/sceneNN.png, title.png, screens/*.png, sprites/*.png and anim/*.png. A missing scene gets a placeholder.
Run from the CHix folder: python tools/make_card.py
"""
import os, struct, zlib
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
SK = os.path.join(ROOT, 'CHix')
PAINT = os.path.join(HERE, 'paint')
PW, PH, SCENES = 120, 112, 10

SCREEN_BLKS = 17
SCREENS = [('title', 'title.png'), ('menu', 'screens/menu.png'), ('clear', 'screens/clear.png'),
           ('gameover', 'screens/gameover.png'), ('victory', 'screens/victory.png')]

PLACEHOLDER_PAL = [(0, 0, 0), (30, 70, 230), (230, 130, 20), (255, 255, 80), (255, 255, 255), (255, 50, 50), (255, 60, 255),
                   (0, 255, 255), (0, 255, 100), (130, 175, 255), (255, 205, 120), (220, 220, 220), (15, 35, 115),
                   (115, 65, 10), (90, 90, 90), (150, 30, 150)]


def placeholder(n):
    px = [[(x // 8 + y // 8) & 3 for x in range(PW)] for y in range(PH)]
    return px, PLACEHOLDER_PAL


def load_p(path):
    im = Image.open(path)
    assert im.mode == 'P', path + ': need mode P'
    raw = im.getpalette()[:48]
    raw += [0] * (48 - len(raw))
    d = list(im.getdata())
    assert max(d) < 16, path + ': more than 16 colours'
    w, h = im.size
    return [d[y * w:(y + 1) * w] for y in range(h)], [tuple(raw[i * 3:i * 3 + 3]) for i in range(16)]


def load_scene(n):
    p = os.path.join(PAINT, 'scene%02d.png' % n)
    if not os.path.exists(p):
        print('scene%02d: placeholder' % n)
        return placeholder(n)
    px, pal = load_p(p)
    assert (len(px[0]), len(px)) == (PW, PH), p
    return px, pal


def pack4(rows, w):
    """rows of pixel indices -> bytes, 2 pixels a byte, left pixel in the low nibble (odd width padded with key 15)."""
    out = bytearray()
    for row in rows:
        row = list(row) + [15] * (w - len(row) + (w & 1))
        out += bytes(row[x] | (row[x + 1] << 4) for x in range(0, len(row), 2))
    return bytes(out)


def blocks(b):
    return b + bytes(-len(b) % 512)


def lum(c):
    return (c[0] * 3 + c[1] * 6 + c[2]) // 10


def nearest(c, pal, cand):
    best, bd = cand[0], 1 << 30
    for i in cand:
        p = pal[i]
        d = 3 * (c[0] - p[0]) ** 2 + 4 * (c[1] - p[1]) ** 2 + 2 * (c[2] - p[2]) ** 2
        if d < bd:
            best, bd = i, d
    return best


def roles(pal):
    """The text colours of a full-screen picture: fixed indices from 1.4.1 (docs/ROUND1-PAINT-BRIEF.md)."""
    return bytes([4, 7, 3, 13, 0])


def roles_auto(pal):                                    # (1.4.0: picked from the palette)
    idx = range(16)
    light = max(idx, key=lambda i: lum(pal[i]))
    dark = min(idx, key=lambda i: lum(pal[i]))
    acc = max(idx, key=lambda i: (pal[i][1] + pal[i][2]) // 2 - pal[i][0] + lum(pal[i]) // 4)
    gold = max(idx, key=lambda i: (pal[i][0] + pal[i][1]) // 2 - pal[i][2] + lum(pal[i]) // 4)
    dim = min((i for i in idx if lum(pal[i]) > 40), key=lambda i: abs(lum(pal[i]) - 100))
    return bytes([light, acc, gold, dim, dark])


# ---- the sprite set: (id name, png, frame w, frame h); the frame number is the running count of the same png
SPRITES = []


FIXED = set()                                       # sprites drawn in the game's fixed indices: kept as they are on every stage


def add(name, path, w, h, fixed=False):
    SPRITES.append((name, path, w, h))
    if fixed:
        FIXED.add(path)


# The order is the order on the card, packed so no frame crosses a block: the blocks a frame needs most come first, as
# the game streams the sprite blocks it needs right after the stage picture (1.4.3: one DMA read instead of a read a sprite).
# Block 0: the two cars of THIS scene (their kind is the scene's), block 1: the ship, the Spark and the HUD heart (every
# frame), then the cores, the pick-ups and the animations.
CARS = ['anim/car_coupe.png', 'anim/car_tram.png', 'anim/car_cargo.png']
add('CARA0', 'CARA', 24, 10)
add('CARA1', 'CARA', 24, 10)
add('CARB0', 'CARB', 24, 10)
add('CARB1', 'CARB', 24, 10)
add('SHIP0', 'sprites/ship0.png', 12, 12)
add('SHIP1', 'sprites/ship1.png', 12, 12)
for i in range(4):
    add('SPARK%d' % i, 'sprites/spark%d.png' % i, 12, 12)
add('HEART', 'sprites/heart.png', 12, 12, fixed=True)              # the HUD's lives, in the fixed colours (1.4.3: was pick-up 9, remapped)
for i, b in enumerate(['core', 'cube', 'octa', 'pyra', 'prism', 'hex', 'icosa', 'tess']):   # 12x12, inside the cage (1.4.2)
    add('BOSS%d' % i, 'sprites/core_%s.png' % b, 12, 12, fixed=True)
for i in range(10):
    add('PU%d' % i, 'sprites/pu%d.png' % i, 12, 12)
for nm, path, n, w, h in (('STAR', 'anim/combo_star.png', 4, 12, 12), ('SPARKLE', 'anim/pickup_sparkle.png', 6, 12, 12),
                          ('BURST', 'anim/claim_burst.png', 6, 16, 16), ('BOOM', 'anim/spark_boom.png', 8, 24, 24)):
    for i in range(n):
        add('%s%d' % (nm, i), path, w, h)

cache = {}


def sheet(path):
    if path not in cache:
        cache[path] = load_p(os.path.join(PAINT, path))
    return cache[path]


def sprite_region(scene_pal, n):
    cand = list(range(15))
    data, table, seen = bytearray(), [], {}
    for name, path, w, h in SPRITES:
        k = seen.get(path, 0)
        seen[path] = k + 1
        if path in ('CARA', 'CARB'):                    # the scene's two car kinds (the game's old choice: n % 3 and (n + 1) % 3)
            path = CARS[(n + (path == 'CARB')) % 3]
        px, pal = sheet(path)
        assert tuple(pal[15]) == (255, 0, 255), path
        remap = list(range(16)) if path in FIXED else [15 if c == 15 else nearest(pal[c], scene_pal, cand) for c in range(16)]
        rows = [[remap[c] for c in px[y][k * w:(k + 1) * w]] for y in range(h)]
        b = pack4(rows, w)
        assert len(b) <= 512
        if len(data) % 512 + len(b) > 512:
            data += bytes(-len(data) % 512)
        table.append((name, len(data), w, h))
        data += b
    return blocks(bytes(data)), table


body = bytearray()
scene_pals, regions, table = [], [], None
for n in range(SCENES):
    px, pal = load_scene(n)
    scene_pals.append(pal)
    reg, table = sprite_region(pal, n)
    regions.append(reg)
region_len = len(regions[0])
assert all(len(r) == region_len for r in regions)
for n in range(SCENES):
    px, pal = load_scene(n)
    for b in range(14):
        blk = bytearray()
        for r in range(8):
            y = b * 8 + r
            row = px[y] if y < PH else [0] * PW
            blk += pack4([row], PW)
        body += blk + bytes(512 - len(blk))
    body += regions[n]
    body += bytes(c for rgb in pal for c in rgb) + bytes(512 - 48)
scene_stride = 14 * 512 + region_len + 512
scr_base = 512 + len(body)
for name, path in SCREENS:
    px, pal = load_p(os.path.join(PAINT, path))
    assert (len(px[0]), len(px)) == (128, 128), path
    body += b''.join(pack4([r], 128) for r in px)
    body += bytes(c for rgb in pal for c in rgb) + roles(pal)
    body += bytes(-len(body) % 512)
h = zlib.crc32(bytes(body)) & 0xffffffff
dat = (b'CHIXCARD' + struct.pack('<I', h)).ljust(512, b'\0') + bytes(body)
card_set = len(dat)
dat += bytes([0xFF]) * 1024                         # the save mirror's two blocks (Card.cpp putSave): after the hashed part, so the hash is unchanged
for d in (os.path.join(ROOT, 'dist'), os.path.join(ROOT, 'CHix', 'sdcard')):
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'CHIX.DAT'), 'wb').write(dat)
o = ["// Generated by tools/make_card.py: CHIX.DAT's hash and where its sections start (byte offsets).",
     '#pragma once', '#include <stdint.h>', '',
     'static const uint32_t CARD_HASH = 0x%08Xu;' % h,
     'static const uint32_t CARD_SCENE = 512, CARD_SCENE_STRIDE = %d;   // scene n at CARD_SCENE + n * stride: 14 picture blocks, the sprite blocks, 1 palette block' % scene_stride,
     "static const uint32_t CARD_SPR_BLKS = %d;                          // the scene's sprite blocks: 14 .. 13 + CARD_SPR_BLKS of the scene, SPR[id].off from block 14" % (region_len // 512),
     'static const uint32_t CARD_SCREEN = %d, CARD_SCREEN_STRIDE = %d;   // 0 title, 1 menu, 2 clear, 3 gameover, 4 victory: 16 blocks, then palette + roles' % (scr_base, SCREEN_BLKS * 512),
     'static const uint32_t CARD_SET = %d;                                // the save mirror: two 512 B blocks of 0xFF, the last 1024 B of the file (Card.cpp getSave/putSave)' % card_set,
     'enum SprId : uint8_t { ' + ', '.join('SP_' + t[0] for t in table) + ', SP_COUNT };',
     'struct SprInfo { uint16_t off; uint8_t w, h; };',
     'static const SprInfo SPR[SP_COUNT] = { ' + ', '.join('{ %d, %d, %d }' % (t[1], t[2], t[3]) for t in table) + ' };', '']
open(os.path.join(SK, 'CardIndex.h'), 'w', newline='').write('\n'.join(o))
print('CHIX.DAT: %d bytes (hash %08X), sprite region %d blocks' % (len(dat), h, region_len // 512))
for t in table:
    print('  %-9s block %d' % (t[0], t[1] >> 9), end='')
print()
