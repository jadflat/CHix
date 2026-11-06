# CHix parallax for the stage pictures: spec and verdict (2026-11-06)

Prototype: `tools/paint/parallax.py` (no painted scenes existed, so it draws a synthetic scene; with
`tools/paint/scene00.png` present it splits that by row bands instead). Outputs `tools/paint/layers/scene00_{far,mid,near}.png`
and `tools/paint/preview_parallax.gif` (96 frames, claim 18% -> 70%, camera drifting 0..72 px and back).
For real paintings the painter should deliver the three layers directly (the band split of a flat picture is only a stand-in).

## Card layout (per scene, each part starts on a 512 B block)

All 4-bit, 2 px a byte, left pixel in the LOW nibble, same palette as the flat scene (16 x 3 B after the layers).

| layer | size px | rows covers | bytes/row | blocks | transparent 0 |
|---|---|---|---|---|---|
| far  | 144 x 64 | view rows 0..63   | 72 | 9  | no (opaque sky) |
| mid  | 168 x 64 | view rows 48..111 | 84 | 11 | yes |
| near | 192 x 56 | view rows 56..111 | 96 | 11 | yes |

31 blocks (15.9 KB) a scene vs 14 today; 10 scenes = 310 blocks, ~+170 KB on the card. Only the last row of each layer is
opaque to the bottom (mid and near fill down to row 111), so no layer needs rows below its range.
Index 0 is "transparent" on mid/near: the painter may not use black as a colour there (black sky stays in far, idx 1/2 are the darks).
Offsets: cam in 0..72 px, far = cam/3 (max 24 = 144-120), mid = cam*2/3 (48), near = cam (72). Even offsets are not required
(a byte holds 2 px); an odd offset costs a nibble shift, already in the per-pixel figure.

## Cost (view 120x112 = 13,440 px, claimed fraction c; renderer ~4 us/px flat, ~6 us/px with 3-layer composite)

| claimed | px | flat 4 us | composite 6 us, whole picture per frame | banded 1/8 (14 rows) per frame |
|---|---|---|---|---|
| 18% | 2,420 | 9.7 ms | 14.5 ms | 1.8 ms |
| 40% | 5,380 | 21.5 ms | 32 ms (FAIL with game logic) | 4.0 ms |
| 70% | 9,410 | 37.6 ms (FAIL) | 56 ms (FAIL) | 7.1 ms |

Card per full picture refresh: 31 blocks x 222 us = 6.9 ms plus commands. With 1 KB scratch (2 blocks, ~10 rows of the
widest layer) a 14-row band needs about 5 commands (far 1, mid 2, near 2) = 5 x 832 + ~8 blocks x 222 = ~5.9 ms a frame.
Band frame total at 70%: 7.1 + 5.9 = ~13 ms on top of today's game and incremental work: fits under 33.3 ms with margin if
the existing frame is under ~18 ms (measure with perf.txt). A whole-picture redraw in one frame is not possible beyond ~25% claimed.

## Algorithm (integer only)

State: `cam` (0..72, u8), `dir`, `tick`, `band` (0..7), scratch[1024] (reuse the card scratch), per-cell claimed bitmap already exists.
```
// once per frame, between gfx_wait and gfx_flushAsync
if (++tick == 4) { tick = 0; cam += dir; if (cam == 0 || cam == 72) dir = -dir; }  // 1 px / 4 frames
y0 = band*14; y1 = y0+14; band = (band+1)&7;
off[0] = cam/3; off[1] = (cam*2)/3; off[2] = cam;     // use cam*86>>8 for /3 if wanted
for each layer k in {far, mid, near}: rows r = max(y0, top_k) .. min(y1, bot_k)-1
    chunk the rows into groups that fit scratch (rowBytes_k * n <= 1024)
    card_read(base_k + (r-top_k)*rowBytes_k, scratch, rowBytes_k*n)   // one command
    for each row in group, for x in 0..119 where cell(x>>1, r>>1) is claimed and (k==far or px!=0):
        p = scratch[row*rowBytes_k + ((x+off[k])>>1)]; v = ((x+off[k])&1) ? p>>4 : p&15
        line[x] = v          // layers drawn far -> mid -> near into a 120-px line buffer (60 B, nibble packed) 
```
Compose each row into one 60 B line buffer then blit (far overwrites, mid/near only where non-zero), so a pixel is written once
to the screen. The 60 B line buffer is the only extra RAM (about 250 B free: ok). Newly claimed cells drawn at claim time use the
current offsets and the same row routine (one cell = 2 rows x 2 px, no card read if the band is cached; otherwise
simply wait for the band sweep, <= 8 frames = 0.27 s, a visible but acceptable pop; or draw the flat far layer immediately).
Slow-claim sparkle and the HUD are unchanged. A band is skipped when no cell in its rows is claimed (cheap early frames).

## Verdict: GO, banded and with drift only while it is cheap

Go for 3 layers with banded refresh (1/8 of the rows per frame) if the integrator measures the existing worst frame under ~18 ms
at 70% claimed. Cheaper fallbacks, in order:
1. **2 layers** (far sky + a merged mid/near 192-wide): 20 blocks, one fewer command a band (~-1.5 ms), composite ~5 us/px.
2. **Sky only**: only far scrolls (144 wide, 9 blocks), mid and near stay the flat 120 px picture: the far read is the only card
   traffic (1 command per frame), and a 24 px sweep is still a clear depth cue. ~3 ms a frame.
3. **Drift only while idle** (the player waiting or the stage clear screen): in play the picture is static (today's cost), so
   the risk to frame time is nil; use whole-picture redraw spread over 8 frames at the clear screen.
Start with 3 (zero risk), then 2/1 behind a config switch if the board measures well. Do not follow the player x: it makes every
move an update; time drift keeps the update rate constant and predictable.
