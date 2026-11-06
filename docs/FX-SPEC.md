# CHix palette effects: integer recipes (model: tools/paint/fx_palette.py, GIFs: out/fx/*.gif)

Call once a frame between `gfx_wait()` and `gfx_flushAsync()`. Only the entries listed are set; set nothing when idle.
`P(i)` = the scene's base colour of entry i (RGB888, from the theme table / scene PNG); `set(i,r,g,b)` = `gfx_setPaletteEntry(i, gfx_rgb(r,g,b))`.
Priority when two effects want an entry: pause > rainbow > lightning > fade > danger > kick > neon/shimmer.
**Never touched (except pause): 0 BG, 4 EDGE, 5 PLAYER, 11 TEXT. Never touched at all: 3 TRAIL, 6 SPARK, 7 Q0, 8 Q1** (gameplay colours).
SCENE set = {1,2,9,10,12,13,14,15}.

Helpers (shared, ~70 B code):
```cpp
static inline uint8_t lift(uint8_t v, uint8_t k) { return v + (((255 - v) * k) >> 3); }       // toward white, k 0..8
static inline uint8_t mix(uint8_t a, uint8_t b, uint8_t t, uint8_t sh) { return a + (((int)(b - a) * t) >> sh); } // arithmetic >> on int
static inline uint8_t tri(uint8_t f, uint8_t per) { f %= per; uint8_t h = per >> 1; return (f < h ? f : per - f) * 8 / h; } // 0..8
```

| effect | entries set / frame | table (flash) | indices touched |
|---|---|---|---|
| neon flicker / sign blink | 1 (only on a change) | `uint32_t` 4 B | 15 |
| wet-street shimmer | 2 | 0 | 12, 13 (mix toward 9, 10) |
| lightning | 8 for 12 frames | 12 B | 1,2,9,10,12,13,14,15 |
| dawn/dusk fade | 8 for 32 frames | 0 | 1,2,9,10,12,13,14,15 |
| kick pulse | 1 for 6 frames of each beat | 6 B | 14 |
| danger pulse | 1 | 8 B | 14 |
| stage-clear rainbow | 6 | 36 B | 1,9,12,2,10,13 |
| pause dim | 13 for 7 frames, then hold | 0 | all but 4,5,11 |

## 1. Neon flicker (index 15)
Painters: put every neon sign/billboard glow in index 15 only. 32-frame loop, bit = on, off = quarter brightness.
```cpp
static const uint32_t NEON = 0xB77BEDFBu;
bool on = (NEON >> (f & 31)) & 1;                       // set only when `on` changed since last frame
set(15, on ? P15 : P15 >> 2 per channel);
```

## 2. Wet-street shimmer (12, 13)
Painters: reflections/puddles use 12 and 13 (darks), with 9/10 the lit neighbours. Period 24 f, up to half way to the light colour.
```cpp
set(12, mix(P12.c, P9.c, tri(f, 24), 4) per channel);
set(13, mix(P13.c, P10.c, tri(f + 8, 24), 4) per channel);
```
(Visible everywhere 12/13 appear; amplitude is deliberately small.)

## 3. Lightning (SCENE set)
Trigger by setting `f = 0` at a random gap (e.g. every 5-9 s). Strongest on frame 1, double flash on frame 3.
```cpp
static const uint8_t BOLT[12] = {0,7,2,6,4,2,1,1,0,0,0,0};
for each i in SCENE, channel c: set(i, lift(P(i).c, BOLT[f]));   // f 0..11, then restore base once
```

## 4. Dawn/dusk fade between stages (SCENE set)
`A` = outgoing theme, `B` = incoming; t = 0..32 over 32 frames (about 1 s) at stage change; then hold B.
```cpp
set(i, mix(A(i).c, B(i).c, t, 5));
```
Preview shows a dusk (scene to dark warm and back): dark = (r*5>>3, g*3>>3, b*4>>3).

## 5. Kick-beat pulse (14)
```cpp
static const uint8_t KICK[6] = {6,4,3,2,1,0};
if (f % BEAT < 6) set(14, lift(P14.c, KICK[f % BEAT]));         // BEAT in frames (12 = 150 bpm at 30 fps)
```

## 6. Danger pulse (14)
d = 0 (enemy near) .. 2 (far), 3 = off (restore base once). Faster the nearer.
```cpp
static const uint8_t SINE[8] = {0,2,4,6,8,6,4,2};
uint8_t s = SINE[((f * (3 - d)) >> 1) & 7];
set(14, mix(P14.c, {255,30,20}.c, s, 4));
```

## 7. Stage-clear rainbow sweep (1,9,12,2,10,13)
Run 24-48 frames over the stage-clear screen. Overrides the ramps (not used with a claimed picture needing the real colours: restore after).
```cpp
static const uint8_t HUE[12][3] = {{255,40,40},{255,150,30},{255,240,50},{140,255,50},{40,255,120},{40,230,255},
                                   {50,120,255},{130,70,255},{220,60,255},{255,60,170},{255,60,100},{255,100,60}};
static const uint8_t RAMP[6] = {1,9,12,2,10,13};
for (j = 0; j < 6; j++) set(RAMP[j], HUE[(f / 2 + 2 * j) % 12]);
```

## 8. Pause dim
k = frames since pause, capped at 7. 4, 5, 11 stay so the PAUSED text stays readable.
```cpp
for i in 0..15 except 4,5,11: set(i, (P(i).c * (8 - k)) >> 3);
```
Resume: restore all base entries in one frame (13 sets).

## Budget
Tables: NEON 4 + BOLT 12 + KICK 6 + SINE 8 + HUE 36 + RAMP 6 = 72 B. Code estimate (helpers + 8 small branches, -Os RISC-V): about 400-450 B, so about 500 B total, under 600 B. Estimate only, unmeasured; drop rainbow (about 90 B) first if tight.
Per-frame cost: at most 13 `gfx_setPaletteEntry` calls, only one effect group at a time except neon/shimmer/kick/danger (disjoint indices 15 / 12,13 / 14).
Conflicts for painters: 14 is shared by kick and danger (and lightning/fade); keep 14 the frame colour only. 15 is reserved for neon signs. Gold 3 and cyan 7 must not carry scene detail that needs to hold still... they never change, so they are safe as static detail.
