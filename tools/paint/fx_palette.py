"""Integer-only model of the CHix palette effects. Mirrors docs/FX-SPEC.md exactly.
base_palette(n) -> 16 (r,g,b); fx_<name>(base, f) -> 16 (r,g,b) for frame counter f."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
# old THEMES: fast, fastL, fastD, slow, slowL, slowD, edge, frame
THEMES = [
 ((30,70,230),(130,175,255),(15,35,115),(230,130,20),(255,205,120),(115,65,10),(255,255,255),(90,90,90)),
 ((30,170,90),(130,240,170),(10,70,40),(170,70,210),(230,150,255),(70,25,95),(200,255,255),(40,110,90)),
 ((210,50,40),(255,150,90),(95,20,20),(230,190,40),(255,240,140),(110,80,10),(255,220,170),(120,50,30)),
 ((40,150,200),(160,225,250),(15,60,95),(240,110,170),(255,190,220),(110,40,75),(230,245,255),(70,100,140)),
 ((110,70,220),(180,150,255),(40,25,95),(150,220,40),(215,255,130),(60,90,10),(255,120,255),(110,60,150)),
 ((200,60,140),(255,140,200),(90,20,60),(255,150,40),(255,215,120),(110,60,10),(255,230,240),(130,50,90)),
 ((20,100,180),(100,200,255),(10,40,90),(40,200,170),(150,255,230),(10,90,75),(220,255,255),(40,90,130)),
 ((130,200,30),(210,250,110),(50,80,10),(230,60,60),(255,150,150),(100,20,20),(240,255,160),(80,110,40)),
 ((200,160,30),(255,230,130),(90,70,10),(120,70,200),(190,150,255),(50,30,95),(255,245,200),(130,100,30)),
 ((130,140,160),(210,220,235),(55,60,75),(200,70,90),(255,150,165),(90,30,40),(255,255,255),(100,105,120))]
# fixed indices (not per-theme): 0 BG, 3 gold, 5 player, 6 spark, 7 cyan, 8 green, 11 text, 15 glow
FIXED = {0:(0,0,0),3:(255,200,40),5:(255,255,255),6:(255,80,80),7:(0,255,255),8:(60,255,90),11:(235,235,235),15:(255,120,220)}
UI = (0,4,5,11)            # never touched by any effect except pause_dim (which spares 4,5,11)
SCENE = (1,2,9,10,12,13,14,15)   # entries effects may move

def base_palette(n=0):
    """Palette of scene n: tools/paint/sceneNN.png if present, else old THEMES[n]."""
    p = os.path.join(HERE, "scene%02d.png" % n)
    if os.path.exists(p):
        from PIL import Image
        raw = Image.open(p).getpalette()[:48]
        return [tuple(raw[i*3:i*3+3]) for i in range(16)]
    h = THEMES[n % 10]; pal = [(0,0,0)]*16
    for i, c in FIXED.items(): pal[i] = c
    for i, c in zip((1,9,12,2,10,13,4,14), h): pal[i] = c
    return pal

def lift(c, k, den_sh=3):            # toward white by k/8
    return tuple(v + (((255 - v) * k) >> den_sh) for v in c)
def lerp(a, b, t, sh):               # a->b, t in 0..2^sh
    return tuple(x + (((y - x) * t) >> sh) for x, y in zip(a, b))
def tri(f, per):                     # triangle wave 0..per/2..0 scaled to 0..8
    f %= per; h = per >> 1
    return ((f if f < h else per - f) * 8) // h

def fx_none(b, f): return list(b)

# 1. neon flicker / sign blink: idx 15 only. 32-frame loop, 1 bit = on.
NEON = 0b10110111_01111011_11101101_11111011
def fx_neon(b, f):
    p = list(b); on = (NEON >> (f & 31)) & 1
    if not on: p[15] = tuple(v >> 2 for v in b[15])
    return p

# 2. wet-street shimmer: idx 12,13 breathe toward idx 9 / 10 (phase offset), period 24 f.
def fx_shimmer(b, f):
    p = list(b)
    p[12] = lerp(b[12], b[9], tri(f, 24), 4)        # up to half way
    p[13] = lerp(b[13], b[10], tri(f + 8, 24), 4)
    return p

# 3. lightning: lift SCENE entries (not 3,7,8). Table of lift/8, 12 frames, trigger at f=0.
BOLT = (0, 7, 2, 6, 4, 2, 1, 1, 0, 0, 0, 0)
def fx_lightning(b, f):
    k = BOLT[f] if f < 12 else 0
    p = list(b)
    for i in SCENE: p[i] = lift(b[i], k)
    return p

# 4. dawn/dusk fade: 32-step lerp of SCENE entries from palette a to b (b passed via fx_fade)
def fx_fade(a, b, f):
    t = f if f < 32 else 32
    p = list(a)
    for i in SCENE: p[i] = lerp(a[i], b[i], t, 5)
    return p
def fx_dusk(b, f):                   # preview: fade scene to a warm-dark version and back
    dark = list(b)
    for i in SCENE:
        r, g, bl = b[i]; dark[i] = ((r * 5) >> 3, (g * 3) >> 3, (bl * 4) >> 3)
    t = f if f < 12 else 24 - f
    return fx_fade(b, dark, t * 32 // 12)

# 5. kick-beat pulse: idx 14 (frame) lifts on the beat, 6-frame decay.
KICK = (6, 4, 3, 2, 1, 0)
def fx_kick(b, f, period=12):
    p = list(b); ph = f % period
    if ph < 6: p[14] = lift(b[14], KICK[ph])
    return p

# 6. danger pulse: idx 14 to red, strength by distance (d 0..3 = near..far, 3 = off), 16f sine-ish.
SINE = (0, 2, 4, 6, 8, 6, 4, 2)    # 8-step triangle-ish, /8
def fx_danger(b, f, d=0):
    p = list(b)
    if d < 3:
        s = SINE[((f * (3 - d)) >> 1) & 7]
        p[14] = lerp(b[14], (255, 30, 20), s, 4)    # max 8/16 red
    return p

# 7. stage-clear rainbow sweep: 7 ramps get hues, 24-frame loop, 12-step hue table
HUE = ((255,40,40),(255,150,30),(255,240,50),(140,255,50),(40,255,120),(40,230,255),
       (50,120,255),(130,70,255),(220,60,255),(255,60,170),(255,60,100),(255,100,60))
def fx_rainbow(b, f):
    p = list(b)
    for j, i in enumerate((1,9,12,2,10,13)): p[i] = HUE[(f // 2 + j * 2) % 12]
    return p

# 8. pause dim: k 0..8 (frames of fade); everything but 4,5,11 scaled by (8-k)/8, floor 1/8 kept via k<=7.
def fx_pause(b, f):
    k = f if f < 7 else 7
    return [c if i in (4,5,11) else tuple((v * (8 - k)) >> 3 for v in c) for i, c in enumerate(b)]

EFFECTS = {"neon":fx_neon,"shimmer":fx_shimmer,"lightning":fx_lightning,"dusk":fx_dusk,
           "kick":fx_kick,"danger":fx_danger,"rainbow":fx_rainbow,"pause":fx_pause}
