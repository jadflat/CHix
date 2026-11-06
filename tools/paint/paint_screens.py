# Paints the CHix full-screen 128x128 backgrounds -> screens/*.png (indexed, own palette each).
# Palette roles: 0 bg,1/2 sky,3 gold,4 white,5 light,6 red,7-9 NEON (cycle),10 near bldg,11 text,12 far bldg,13 mid bldg,14 frame,15 glow
import numpy as np, random, math, os
from PIL import Image
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screens")
B4 = np.array([[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]])
def hx(s): return tuple(int(s[i:i+2],16) for i in (1,3,5))
def pal(c): return [hx(x) for x in c]
PALS = {
 "dusk":  "#000008 #0a1230 #2a2a6a #ffc030 #ffffff #a0e0ff #ff3050 #20e8ff #30ff90 #ff40d0 #05050f #e8f0ff #1c2050 #101840 #4060c0 #ff80ff",
 "dim":   "#000004 #080c20 #1a2048 #a07820 #d8d8e8 #6080a0 #a02838 #1890a8 #20a060 #a02890 #04040c #c0c8d8 #141838 #0c1230 #303c78 #804080",
 "clear": "#000010 #101050 #4020a0 #ffe040 #ffffff #c0f0ff #ff4060 #20ffff #60ff60 #ff30e0 #08082a #ffffff #301870 #1c1060 #6080ff #ffa0ff",
 "over":  "#000000 #04060c #0e1424 #806020 #b0b8c8 #405060 #801020 #107080 #207040 #701860 #020308 #909aa8 #0a0e1a #060810 #202838 #401040",
 "dawn":  "#100820 #402050 #c05060 #ffd040 #ffffff #fff0b0 #ff6030 #ffa020 #ffe060 #ff8080 #1a0c28 #fff8e0 #7a3050 #5a2850 #ffc060 #ffffa0",
}
def theme_pal(i):
    h = [(0,40,80),(60,0,60),(0,60,30),(80,20,0),(30,0,80),(0,50,60),(70,0,20),(20,60,0),(50,30,70),(80,50,0)][i]
    p = pal(PALS["dusk"].split())
    p[1] = (h[0]//4+4, h[1]//4+6, h[2]//4+30); p[2] = (h[0]+30, h[1]+30, h[2]+90)
    p[12] = tuple(max(0,(a+b)//2-8) for a,b in zip(p[2],p[0])); p[13] = tuple(c*2//3 for c in p[12])
    p[10] = (4,4,12); p[14] = (h[0]+60,h[1]+60,h[2]+140)
    return p
class C:
    def __init__(s, seed, p):
        s.a = np.zeros((128,128), np.uint8); s.r = random.Random(seed); s.p = p
    def px(s,x,y,c):
        if 0<=x<128 and 0<=y<128: s.a[y,x]=c
    def rect(s,x0,y0,x1,y1,c):
        s.a[max(0,y0):max(0,y1+1), max(0,x0):max(0,x1+1)] = c
    def sky(s, hy=84, top=0, mid=1, low=2):
        for y in range(hy):
            f = y/hy*32
            for x in range(128):
                if f < 16: s.a[y,x] = mid if B4[y&3,x&3] < f else top
                else: s.a[y,x] = low if B4[y&3,x&3] < f-16 else mid
    def stars(s, n, hy=50):
        for _ in range(n):
            s.px(s.r.randrange(128), s.r.randrange(hy), s.r.choice([4,4,5,3]))
    def disc(s, cx, cy, r, c=5, shade=2, ring=False):
        for y in range(cy-r, cy+r+1):
            for x in range(cx-r, cx+r+1):
                if math.hypot(x-cx, y-cy) <= r:
                    t = ((x-cx)+(y-cy))/(2*r)*8+8
                    s.px(x,y, shade if B4[y&3,x&3] < t-3 else c)
        if ring:
            for a in range(0,360,2):
                x = int(cx+math.cos(math.radians(a))*r*1.8); y = int(cy+math.sin(math.radians(a))*r*0.45)
                if a > 180 or abs(x-cx) >= r: s.px(x,y,3 if a%4 else 4)
    def skyline(s, base, lo, hi, col, edge, wmode=0, wcol=3, ww=(5,9)):
        x = 0
        while x < 128:
            w = s.r.randint(*ww); h = s.r.randint(lo,hi); top = base-h
            s.rect(x, top, x+w-1, base, col); s.rect(x, top, x+w-1, top, edge)
            if s.r.random()<.25: s.rect(x+w//2, top-s.r.randint(2,5), x+w//2, top-1, col)
            if wmode:
                for wy in range(top+3, base-1, 3):
                    for wx in range(x+1, x+w-1, 2):
                        if s.r.random() < wmode: s.px(wx,wy, s.r.choice([wcol,wcol,3,7,9]))
            x += w
    def sign(s, x, y, h, c, broken=False):
        for i in range(h):
            if broken and i%3==1: continue
            s.px(x,y+i,c); s.px(x+1,y+i,4 if i%2==0 else c)
            for gx in (x-1,x+2):
                if B4[(y+i)&3,gx&3] < 5: s.px(gx,y+i,c)
    def rain(s, n, c=5):
        for _ in range(n):
            x = s.r.randrange(128); y = s.r.randrange(110)
            for i in range(s.r.randint(3,6)):
                if B4[(y+i)&3, x&3] < 12: s.px(x-i//3,y+i,c)
    def street(s, y0):
        s.rect(0,y0,127,127,10); s.rect(0,y0,127,y0,12)
        for y in range(y0+1,128):
            for x in range(128):
                if (x+y*3)%11==0 and B4[y&3,x&3]<10: s.px(x,y,s.r.choice([7,9,8]))
        for x in range(128):
            for k in range(1, 128-y0):
                src = y0-k
                if src<0: break
                c = s.a[src,x]
                if c in (3,7,8,9) and (x+k)%2==0 and B4[(y0+k)&3,x&3]<12-k//2: s.px(x,y0+k,c)
    def burst(s, cx, cy, n, r0, r1, cols):
        for i in range(n):
            a = 2*math.pi*i/n + s.r.random()*.1
            L = s.r.randint(r0,r1); c = cols[i%len(cols)]
            for t in range(r0//2, L):
                s.px(int(cx+math.cos(a)*t), int(cy+math.sin(a)*t), 4 if t>L-3 else c)
    def save(s, name):
        im = Image.fromarray(s.a, "P")
        flat = [v for c in s.p for v in c]; im.putpalette(flat + [0]*(768-len(flat)))
        im.save(os.path.join(OUT, name))

def build_city(c, lights, hy=88, far=(22,44), mid=(30,56), near=(36,64), signs=4, broken=False):
    c.skyline(hy-2, *far, 12, 2, lights*.3, 5, (4,8))
    c.skyline(hy, *mid, 13, 12, lights*.7, 5, (5,9))
    c.skyline(hy+2, *near, 10, 13, lights, 3, (6,12))
    for i in range(signs):
        x = c.r.randrange(4,122); y = hy+2-c.r.randint(20,50)
        c.sign(x,y,c.r.randint(6,14),c.r.choice([7,8,9]), broken and i%2==0)
    c.street(hy+3)

def mk_menu():
    c = C(1, pal(PALS["dim"].split())); c.sky(86); c.stars(30); c.disc(96,26,10,5,2)
    build_city(c,.12,signs=3); c.save("menu.png")
def mk_clear():
    c = C(2, pal(PALS["clear"].split())); c.sky(86)
    c.burst(64,40,28,12,40,[7,9,3,8,4,6]); c.burst(30,26,14,5,14,[3,9,7]); c.burst(100,30,14,5,16,[8,7,3])
    for _ in range(40): c.px(c.r.randrange(128),c.r.randrange(70),c.r.choice([4,3,7,9]))
    build_city(c,.55,signs=7); c.save("clear.png")
def mk_over():
    c = C(3, pal(PALS["over"].split())); c.sky(86); c.stars(8,30)
    build_city(c,.06,signs=6,broken=True); c.rain(150,5); c.save("gameover.png")
def mk_victory():
    c = C(4, pal(PALS["dawn"].split())); c.sky(90, 1, 2, 7)
    c.disc(64,80,22,3,8)
    for a in range(0,360,12):
        for t in range(25,48):
            x=int(64+math.cos(math.radians(a))*t); y=int(78+math.sin(math.radians(a))*t)
            if y<86 and B4[y&3,x&3] < 10-(t-25)//3: c.px(x,y,8 if t%2 else 3)
    c.stars(10,25)
    build_city(c,.35,hy=96,far=(8,20),mid=(10,24),near=(14,30),signs=3); c.save("victory.png")
def mk_intro(i):
    c = C(100+i, theme_pal(i)); c.sky(86); c.stars(35,40)
    if i in (0,3,8): c.disc(18+i*9,24,5+i//2,5,2)
    if i in (1,6): c.disc(95,28,9,5,2,ring=True)
    if i == 2:
        c.rect(0,66,127,67,13)
        for x in range(0,128,16): c.rect(x,44,x+1,67,13)
        for x in range(0,128,4): c.px(x,66-int(10*math.sin(x/127*math.pi*4)**2),4)
    if i == 4: c.rect(58,30,70,70,12); c.rect(52,40,76,48,12); c.rect(61,24,67,30,12); c.px(63,26,6); c.px(65,26,6)
    if i == 5:
        for x in range(10,118): c.rect(x,40+int(14*math.sin(x/9)),x+1,44+int(14*math.sin(x/9)),12)
        c.px(112,44,6)
    if i == 7: c.rect(30,50,100,58,12); c.rect(60,40,80,50,12); c.px(95,53,7)
    if i == 9: c.disc(64,36,14,2,1); c.rect(62,32,66,40,6)
    build_city(c,.25+i*.03,hy=92,far=(18+i,40),mid=(26,50+i),near=(32,60+i*2),signs=5)
    c.rain(40+i*8,5); c.save(f"intro{i:02d}.png")
def mk_hud():
    p = pal(PALS["dusk"].split()); p[15]=(255,0,255)
    c = C(9,p); c.rect(0,0,127,127,10)
    for k,col in enumerate([14,13,12,1]):
        c.rect(k,k,127-k,k,col); c.rect(k,k,k,127-k,col)
        c.rect(k,127-k,127-k,127-k,12 if k<2 else 1); c.rect(127-k,k,127-k,127-k,12 if k<2 else 1)
    c.rect(2,2,125,12,13)
    for x in range(3,125,2): c.px(x,13,12)
    for (x0,x1,col) in [(6,45,7),(48,73,3),(76,101,9),(104,121,8)]:
        c.rect(x0-1,2,x1+1,11,col); c.rect(x0,3,x1,10,0)
        c.px(x0-1,2,4); c.px(x1+1,2,4)
    c.rect(4,14,123,125,15)
    c.rect(3,13,124,13,14); c.rect(3,126,124,126,14); c.rect(3,13,3,126,14); c.rect(124,13,124,126,14)
    c.rect(4,14,123,14,15)
    c.save("hud.png")
def main():
    os.makedirs(OUT, exist_ok=True)
    mk_menu(); mk_clear(); mk_over(); mk_victory(); mk_hud()
    for i in range(10): mk_intro(i)
    with open(os.path.join(OUT,"CYCLES.txt"),"w",newline="\n") as f:
        f.write("Palette cycling ranges (inclusive indices) per image. 7-9 = neon (cyan,green,magenta; also signs, window lights, street reflections).\n")
        for n in ["menu","clear","gameover","victory"]+[f"intro{i:02d}" for i in range(10)]:
            f.write(f"{n}.png: 7-9 neon (rotate)\n")
        f.write("hud.png: 7-9 neon (panel outlines); index 15 = #FF00FF keyed playfield window (x4..123, y14..125)\n")
        f.write("clear.png: 7-9 burst colours (fast cycle); victory.png: 7-9 ray/gold tones (slow cycle)\n")
main()
