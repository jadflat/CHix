"""CHix marketing media from the PC simulator: the trailer, the README GIF and stills, the front-end cover and preview.

    python tools/make_trailer.py            # capture (the simulator), render the music, make everything
    python tools/make_trailer.py --no-run   # reuse the captures in out/trailer/

Captures: CHix/tools/scripts/trailer.txt and trailer_split.txt, one run a stage, every frame (30 fps), into
out/trailer/<run>/play.gif. The music is the game's own FM synth (CHix/Synth.cpp) built for the PC with g++
and rendered at its 8 kHz rate. Needs ffmpeg ($FFMPEG, else on PATH), g++ on PATH, and CHix/sdcard/CHIX.DAT.

Writes docs/CHix-trailer.mp4 (1280x720), docs/gameplay.gif, docs/shot-*.png (4x), and out/trailer/media/
CHix-image.png (512x512 cover) and CHix-video.mp4 (640x480, 15 s) for a front end's media folder.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "trailer"
DOCS = ROOT / "docs"
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FPS = 30
NEAREST = Image.Resampling.NEAREST

# The game's colours (the title picture's palette).
INK = (4, 3, 14)
DEEP = (32, 20, 66)
PINK = (255, 70, 190)
CYAN = (0, 230, 255)
GOLD = (255, 196, 40)
WHITE = (250, 250, 255)

RUNS = {  # run name: (script, defines)
    "s01": ("trailer.txt", ["CHIX_START_LEVEL=1"]),
    "f03": ("trailer.txt", ["CHIX_DEMO_FILL", "CHIX_START_LEVEL=3"]),
    "f07": ("trailer.txt", ["CHIX_DEMO_FILL", "CHIX_START_LEVEL=7"]),
    "f31": ("trailer.txt", ["CHIX_DEMO_FILL", "CHIX_START_LEVEL=31"]),
    "f45": ("trailer.txt", ["CHIX_DEMO_FILL", "CHIX_START_LEVEL=45"]),
    "s26": ("trailer.txt", ["CHIX_START_LEVEL=26"]),
    "s40": ("trailer.txt", ["CHIX_START_LEVEL=40"]),
    "x08": ("trailer_split.txt", ["CHIX_START_LEVEL=8"]),
}

# The trailer: ("card", lines, frames) or ("clip", run, first, end, caption). Frames are 30 fps.
TRAILER = [
    ("logo", None, 54),
    ("clip", "f03", 0, 60, ""),
    ("clip", "f03", 88, 180, "CLAIM THE\nPAINTED CITY"),
    ("clip", "f03", 232, 292, "STAGE\nCLEAR!"),
    ("card", ["45 STAGES"], 42),
    ("clip", "x08", 110, 240, "BOSSES SHRINK\nTO FIT"),
    ("clip", "s26", 126, 180, "WIREFRAME\nBOSSES"),
    ("clip", "s40", 126, 176, "TWIN\nBOSSES"),
    ("clip", "f07", 140, 190, "RAINY NEON\nCITYSCAPES"),
    ("clip", "f31", 140, 190, "RAINY NEON\nCITYSCAPES"),
    ("clip", "f45", 126, 172, "RAINY NEON\nCITYSCAPES"),
    ("card", ["30 FPS"], 40),
    ("clip", "s01", 380, 460, "COMBOS\nUP TO X5"),
    ("end", ["for the CHGame handheld"], 84),
]
GIF = [("f03", 0, 40), ("x08", 120, 250), ("f03", 232, 292), ("f45", 126, 170), ("f31", 140, 186), ("s26", 130, 175)]
SHOTS = {"shot-claim": ("x08", 236), "shot-clear": ("f03", 262), "shot-twins": ("f45", 150)}
PREVIEW = [("clip", "f03", 0, 50, ""), ("clip", "f03", 88, 180, ""), ("clip", "f03", 232, 280, ""),
           ("clip", "x08", 120, 245, ""), ("clip", "f45", 126, 171, ""), ("clip", "s26", 126, 166, ""), ("clip", "s40", 126, 186, "")]


def capture():
    for name, (script, defs) in RUNS.items():
        args = ["--card", "CHix/sdcard/CHIX.DAT", f"CHix/tools/scripts/{script}", str(OUT / name)]
        args += [x for d in defs for x in ("-D", d)]
        subprocess.run([sys.executable, str(ROOT / "chgame" / "tools" / "chgame.py"), "--sketch", str(ROOT / "CHix"),
                        "run"] + args, check=True, cwd=ROOT)


def frames(run):
    """A recording's frames at 1x, one a game frame (the GIF writer merges repeats into longer frames)."""
    g = Image.open(OUT / run / "play.gif")
    out = []
    for i in range(g.n_frames):
        g.seek(i)
        im = g.convert("RGB").resize((128, 128), NEAREST)
        out += [im] * max(1, round(g.info.get("duration", 16) / 16))
    return out


_cache = {}


def clip(run, a, b):
    if run not in _cache:
        _cache[run] = frames(run)
    return _cache[run][a:b]


_font = []


def font5x7():
    """The CHGame library's own 5x7 font (CHGfx_font.h: a byte a column, bit 0 the top row)."""
    if not _font:
        src = (ROOT / "chgame" / "platform" / "board" / "arduino" / "CHGame" / "libraries" / "CHGfx" / "src" /
               "CHGfx_font.h").read_text()
        body = src[src.index("{", src.index("chgfx_font5x7")) + 1:src.index("};")]
        body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
        _font.extend(int(x, 16) for x in re.findall(r"0x[0-9A-Fa-f]+", body))
    return _font


def text_image(s, scale, colour, shadow=INK):
    """Text in the CHGame 5x7 font, scaled up by whole pixels, with a drop shadow."""
    f = font5x7()
    m = Image.new("L", (len(s) * 6 - 1, 8))
    for i, ch in enumerate(s):
        c = ord(ch) - 32
        if not 0 <= c < 95:
            continue
        for x in range(5):
            col = f[c * 5 + x]
            for y in range(8):
                if col >> y & 1:
                    m.putpixel((i * 6 + x, y), 255)
    m = m.resize((m.width * scale, m.height * scale), NEAREST)
    im = Image.new("RGBA", (m.width + scale, m.height + scale))
    im.paste(shadow + (255,), (scale, scale), m)
    im.paste(colour + (255,), (0, 0), m)
    return im


def logo():
    t = Image.open(ROOT / "tools" / "paint" / "title.png").convert("RGB")
    return t.crop((0, 0, 128, 44))


def background(w, h):
    bg = Image.new("RGB", (w, h), INK)
    d = ImageDraw.Draw(bg)
    for y in range(0, h, 4):                                   # faint scanlines
        d.line([(0, y), (w, y)], fill=(10, 7, 26))
    return bg


def frame_box(img, x, y, w, h):
    d = ImageDraw.Draw(img)
    d.rectangle([x - 10, y - 10, x + w + 9, y + h + 9], outline=PINK, width=4)
    d.rectangle([x - 4, y - 4, x + w + 3, y + h + 3], outline=CYAN, width=2)


def fade(im, k):
    return im if k >= 1 else Image.blend(Image.new("RGB", im.size, (0, 0, 0)), im, max(0.0, k))


def centre(base, im, cx, cy):
    base.paste(im, (cx - im.width // 2, cy - im.height // 2), im if im.mode == "RGBA" else None)


def render(segments, size, emit):
    """Frames of a segment list at `size` (1280x720 or 640x480) to emit(image)."""
    W, H = size
    big = W >= 1280
    scale = 5 if big else 3
    gw = 128 * scale
    gx, gy = (W - gw) // 2, (H - gw) // 2 if big else H - gw - 16
    base = background(W, H)
    lg = logo().resize((256, 88) if big else (192, 66), NEAREST)
    if big:
        frame_box(base, gx, gy, gw, gw)
        centre(base, lg, gx // 2, H // 2 - 120)
    else:
        frame_box(base, gx, gy, gw, gw)
        centre(base, lg, W // 2, (gy - 10) // 2)
    groups = []                                                # consecutive clips fade in and out as one
    for s in segments:
        if s[0] == "clip" and groups and groups[-1][0][0] == "clip":
            groups[-1].append(s)
        else:
            groups.append([s])
    for grp in groups:
        if grp[0][0] == "clip":
            seq = []
            for _, run, a, b, cap in grp:
                seq += [(f, cap) for f in clip(run, a, b)]
            n = len(seq)
            for i, (f, cap) in enumerate(seq):
                im = base.copy()
                im.paste(f.resize((gw, gw), NEAREST), (gx, gy))
                if big and cap:
                    for j, line in enumerate(cap.split("\n")):
                        centre(im, text_image(line, 3, CYAN if j == 0 else GOLD), gx + gw + gx // 2, H // 2 - 30 + 44 * j)
                emit(fade(im, min((i + 1) / 6, (n - i) / 6)))
        else:
            kind, lines, n = grp[0]
            card = background(W, H)
            if kind in ("logo", "end"):
                lw = 768 if big else 384
                centre(card, logo().resize((lw, lw * 44 // 128), NEAREST), W // 2, H // 2 - (40 if lines else 0))
                if lines:
                    centre(card, text_image(lines[0], 5 if big else 3, CYAN), W // 2, H // 2 + (lw * 22 // 128) + 30)
            else:
                sc = 8 if big else 4
                for j, line in enumerate(lines):
                    col = PINK if j == 0 else CYAN
                    centre(card, text_image(line, sc, col), W // 2, H // 2 + int((j - (len(lines) - 1) / 2) * 11 * sc))
            for i in range(n):
                emit(fade(card, min((i + 1) / 8, (n - i) / 8)))


def encode(segments, size, path, audio, seconds=None):
    total = 0
    for s in segments:
        total += s[2] if s[0] != "clip" else s[3] - s[2]
    dur = seconds or total / FPS
    afade = f"afade=t=in:d=0.3,afade=t=out:st={dur - 1.5:.2f}:d=1.5"
    cmd = [FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}",
           "-r", str(FPS), "-i", "-", "-i", str(audio), "-t", f"{dur:.3f}",
           "-af", afade, "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    count = [0]

    def emit(im):
        if seconds and count[0] >= seconds * FPS:
            return
        p.stdin.write(im.tobytes())
        count[0] += 1
    render(segments, size, emit)
    p.stdin.close()
    if p.wait():
        raise SystemExit("ffmpeg failed")
    print(f"{path.name}: {count[0]} frames, {path.stat().st_size:,} B")


def music(seconds):
    """The game's synth on the PC: the title song, then the goa stage song (the synth's own crossfade), as WAV."""
    syn = OUT / "syn"
    syn.mkdir(parents=True, exist_ok=True)
    (syn / "CHGame.h").write_text(
        "#pragma once\n#include <stdint.h>\nnamespace audio { struct Step { uint16_t hz, ms, endHz; }; "
        "enum { SOFT = 16 }; struct Effect { const Step *steps; uint8_t n, flags; }; }\n", newline="\n")
    (syn / "render.cpp").write_text(r"""#include "Synth.h"
#include <cstdio>
#include <cstdlib>
namespace synth { uint8_t sample(); }
int main(int c, char **v) {      // render <out.raw> <seconds> <song> <switch at s> <song2>
    FILE *f = fopen(v[1], "wb"); long n = (long)(atof(v[2]) * 8000), sw = (long)(atof(v[4]) * 8000);
    synth::music(atoi(v[3]));
    for (long i = 0; i < n; i++) { if (i == sw) synth::music(atoi(v[5])); fputc(synth::sample(), f); }
    fclose(f);
}
""", newline="\n")
    exe = syn / "render.exe"
    subprocess.run(["g++", "-O2", "-DCHSIM", f"-I{syn}", f"-I{ROOT / 'CHix'}", "-o", str(exe), str(syn / "render.cpp"),
                    str(ROOT / "CHix" / "Synth.cpp")], check=True)
    raw = syn / "music.raw"
    subprocess.run([str(exe), str(raw), str(seconds), "0", "3.6", "3"], check=True)
    wav = OUT / "music.wav"
    # 8 kHz 8-bit -> 48 kHz, DC and rumble off, loudness to -16 LUFS with a -1.5 dBTP ceiling.
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "u8", "-ar", "8000", "-ac", "1", "-i", str(raw),
                    "-af", "aresample=48000,highpass=f=30,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000",
                    "-ac", "2", str(wav)], check=True)
    return wav


def readme_gif():
    seq = []
    for run, a, b in GIF:
        seq += clip(run, a, b)[::2]                            # 15 fps
    tmp = OUT / "gif_frames"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    for i, f in enumerate(seq):
        f.resize((256, 256), NEAREST).save(tmp / f"{i:04d}.png")
    out = DOCS / "gameplay.gif"
    subprocess.run([FFMPEG, "-v", "error", "-y", "-framerate", "15", "-i", str(tmp / "%04d.png"), "-filter_complex",
                    "split[a][b];[a]palettegen=max_colors=128:stats_mode=full[p];[b][p]paletteuse=dither=none",
                    "-loop", "0", str(out)], check=True)
    print(f"gameplay.gif: {len(seq)} frames ({len(seq) / 15:.1f} s), {out.stat().st_size:,} B")


def stills():
    for name, (run, i) in SHOTS.items():
        clip(run, i, i + 1)[0].resize((512, 512), NEAREST).save(DOCS / f"{name}.png")
    media = OUT / "media"
    media.mkdir(parents=True, exist_ok=True)
    Image.open(ROOT / "tools" / "paint" / "title.png").convert("RGBA").resize((512, 512), NEAREST).save(
        media / "CHix-image.png")


def main():
    if "--no-run" not in sys.argv:
        capture()
    wav = music(36)
    readme_gif()
    stills()
    encode(TRAILER, (1280, 720), DOCS / "CHix-trailer.mp4", wav)
    encode(PREVIEW, (640, 480), OUT / "media" / "CHix-video.mp4", wav, seconds=15)


if __name__ == "__main__":
    main()
