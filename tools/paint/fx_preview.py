"""Render 24-frame GIFs of each effect: python tools/paint/fx_preview.py [scene N]. Output out/fx/*.gif"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import fx_palette as fx
n = int(sys.argv[1]) if len(sys.argv) > 1 else 0
root = os.path.dirname(os.path.dirname(fx.HERE)); out = os.path.join(root, "out", "fx"); os.makedirs(out, exist_ok=True)
sp = os.path.join(fx.HERE, "scene%02d.png" % n)
if os.path.exists(sp): img = Image.open(sp).convert("P")
else:   # stand-in: bands of every index so each entry is visible
    img = Image.new("P", (120, 112))
    img.putdata([ (x // 8 + (y // 14) * 3) % 16 for y in range(112) for x in range(120)])
base = fx.base_palette(n)
for name, fn in fx.EFFECTS.items():
    frames = []
    for f in range(24):
        im = img.copy(); flat = []
        for c in fn(base, f): flat += [max(0, min(255, v)) for v in c]
        im.putpalette(flat); frames.append(im.convert("RGB").resize((360, 336), Image.NEAREST))
    frames[0].save(os.path.join(out, name + ".gif"), save_all=True, append_images=frames[1:], duration=66, loop=0)
    print("wrote", name)
