# Changelog

## 1.5.0

- 40 frames a second instead of 30: the game runs a third faster (ship, Sparks, bosses and timers all move at the quicker pace), worst board frame stays under the 25 ms the new rate allows.
- The save is also written to the last two blocks of `CHIX.DAT` on the SD card; a save lost from flash (a re-flash, an update) is restored from the card at the next start. The DAT is 1 KB bigger: copy the new `CHIX.DAT` to the card.

## 1.4.7

- The ship turns to face the way it moves, with a short turning animation (8 angles, integer rotation).

## 1.4.6

- The public release, with every change since 1.2.3 (1.3.0 to 1.4.5 below; no code change from 1.4.5). In short:
  - Painted art read from `CHIX.DAT` on the SD card (now required): ten stage pictures, title, pause, clear, game-over and
    win screens, sprites and animations, with palette effects, rain and flying cars; the procedural art and a floating-point
    sine table are gone (about 8 KB of flash back).
  - A smooth pace: the ship and Sparks are drawn between cells, the ship a quarter faster since 1.4.4, taps and quick turns
    are kept, and a Spark and the ship that swap cells collide.
  - Bosses that resize to the room around them; 12x12 cores in fixed colours inside their cages, and what you see is what hits.
  - Faster on the board: worst frame 17.8 ms at stage 1 (31.3 ms before 1.4.3), closing a shape spread over three frames.
  - A music tune-up: even loudness, longer before a song repeats, new bars and fills, a quicker fade-in between stages.
  - Fixes: the enemy stays put after a death, Sparks restart away from you, game-over and win screens wait for a new press.

## 1.4.5

- Boss resizing: a one-step dead band so the size no longer flickers at the edge, the roaming line is capped at 1.4x, and its ends are kept inside the field.

## 1.4.4

- The ship is about a quarter faster on normal moves (2 and 3 quarter-cells a frame in turn, 2.5 on average); slow draw and SPEED UP are as before.
- The bosses breathe in real time: every stage-tick the boss eases one step toward what fits, from about 0.56x to 1.6x its old size. It is big in open ground, small as it squeezes through gaps, and its ceiling falls from 1.6x on an empty stage to 1.0x at 75% claimed. This covers the wireframe solids (twins size separately) and the roaming line (scaled about its middle, with its afterimages and its kill check). The collision uses the drawn shape. The glowing 12 px core sprite keeps its size.

- A music tune-up (judged from PC renders of the synth, levels and note counts; not yet heard on the board):
  - Even loudness: each song has its own level. The busy psytrance songs ran hard into the limiter (2 to 8% of their samples clipped, about -3.4 dB rms) while the ambient ones sat about 4 dB lower; now every song is between -5.2 and -7.0 dB rms with under 1.2% at the limit, and the sound effects stand out a little more over the music.
  - Longer before it repeats: every second time through a song the echo voice plays the lead two steps later and the sweep turns the other way, so a song only repeats exactly after 32 bars.
  - Dark psy, goa, full-on, forest, progressive and hi-tech have new bars (held calls, answers, a turnaround into the top), a chord change in the second half and bass bars that walk up or down into the next bar; dark psy's bass rolls (kick-bass-bass-bass) in its second half, and forest's lead has rests to breathe. The title gets a held answer in its last bar and a bass run every fourth bar; aurora and nebula get a slow bass that moves.
  - The drums have a small fill every fourth bar, and the last bar drops the kick for a snare roll back to the top.
  - Between stages the new song comes in quicker (from a third of its level, over 0.16 s), so its first beat is heard; the old song still fades out over half a second.

## 1.4.3

- Faster on the board (measured with `CHIX.DAT` on the card), drawing the same pixels: the perf script's worst frame at stage 1 is down from 31.3 ms to 17.8 ms and its average from about 26 ms to 16 ms; stage 45 (twin tesseracts, four Sparks) averages about 19.5 ms, and its worst frames (a death, with the screen shake) are 23.8 ms (33-35 ms before).
  - Each sprite was a separate read from the card, about 1.4 ms each and five to eight a frame. The sprites a stage uses now sit right after its picture in `CHIX.DAT`, and the frames a frame draws come in the same multi-block read as the picture, copied out to a buffer that is free while drawing.
  - The picture's cells and the sprite rows are drawn by two small functions in SRAM (flash has three wait states and no cache), and a cell's look comes from a table instead of a chain of tests.
  - The screen shake moved the frame a byte at a time (up to 11 ms a frame); it now moves words.
  - The wireframe edges step without dividing (the same pixels).
- The lives heart in the HUD is its own sprite in the game's fixed colours (red, white, black), the same on every stage; it was the extra-life pick-up remapped to each stage's palette, which made it dull on some stages (stage 10).
- Cleaner stage pictures (the 1.4.2 versions are kept in `tools/paint/v4/`): stage 3's street below the hologram geisha is redrawn as a tram line and three clear shop fronts over a wet street, and the hologram's outline is continuous; stage 4's sky loses its ember speckle (a few embers stay by the fire) and its street is a clean reflection; stage 5 loses the stray white and pink speckle; stage 10's tractor beams and lightning are clean shapes, and its window and ring lights are regular strips instead of dotted lines.
- The title with a saved game shows CONTINUE and NEW GAME in its one panel, so the lit street below stays in view (a second panel covered it).
- The new `CHIX.DAT` is required (a 1.4.2 card is refused with "NEED CHIX.DAT").

## 1.4.2

- The enemy cores are new 12x12 sprites (were 24x24) drawn in the game's fixed colours (red, gold and white, or green, with a black outline), so each enemy looks the same and stands out on every stage; they used to be remapped to each stage's palette and could fade into it (stage 7's ICOSA was a pale orb). The core now sits inside its wireframe cage (it was bigger than the cage, and only the cage could hit you): the far edges are drawn behind it and the near edges in front, and a line touching the core is hit too, so what you see is what hits.
- A slow claim shows a thin gold sheen that sweeps across it now and then, instead of gold twinkles scattered over the picture, and the rain over the claimed picture is lighter.
- After a death the enemy stays where it was. 1.4.1 put it back in the middle of the field, and if that was already claimed it could not move again for the rest of the stage. The Sparks start again on a border at least 16 cells from you (one could start on top of you, or stranded inside claimed ground).
- The game-over and win screens wait for a new press of A (holding A from the last line skipped them).
- Frame rate, measured on the board with `CHIX.DAT` on the card. Earlier 1.4.x figures were taken without the file, so they timed the "NEED CHIX.DAT" screen. In fact closing a shape took up to 69 ms a frame, and the title and other full-screen pictures about 33 ms. Now:
  - The stage picture and the full-screen pictures are read in one multi-block DMA read each, not one block at a time, and the title runs at about 14 ms.
  - The flood fill works on runs of cells and is about 3x faster.
  - Closing a shape is spread over three frames, under its white flash: the field holds still for two of them, a short hit-stop.
  - Every frame of the perf script is now under 31.5 ms, about 26 ms on average.
- The points for a claim float up below the HUD on a dark shadow (they ran over the score at the top).
- New art in `CHIX.DAT`: stage pictures 3 (the hologram geisha: the hair and the street below), 6 (the ringed planet: bolder, fewer struts and a shaded planet), 9 (a real street of shops) and 10 (storm clouds instead of brown bands) are repainted; the win screen is a darker dawn with the gold kept for its text; the level-clear fireworks burst in open sky above the city; the title has a lit, wet street below its panels. The 1.4.1 versions are kept in `tools/paint/v3/`. The unused level-intro and HUD pictures are moved to `tools/paint/unused/`: they are below the level of the rest and the game has no place for them.
- The new `CHIX.DAT` is required (a 1.4.1 card is refused with "NEED CHIX.DAT").

## 1.4.1

- The sparks are drawn on their way to their next cell instead of up to a whole cell behind their last one: a spark now reaches a cell on screen when it enters it, so a hit shows where it happens. They move just as smoothly (half, one or one and a half pixels a frame).
- The enemy's wireframe cage and the line enemy are drawn on a dark edge, so they stay readable over the busiest pictures (stages 5 and 7).
- The enemy's cage touching your line is tested every cell along each edge (it was six points an edge, which could step over the line).
- New art, all in `CHIX.DAT`: a chrome and neon CHIX title over the rainy city; new pause (a rainy skyline and ringed planet), level-clear (fireworks over the city), game-over (a fallen mecha in the rain under a broken HOPE sign) and win (a sunrise) pictures, at the same level as the stage pictures. Stage 3's picture (the hologram geisha) and stage 9's (the twin spires and banded planet) are repainted, and stage 1's wet street shows proper light reflections instead of cross-hatching. The 1.4.0 versions are kept in `tools/paint/v2/`.
- The text colours on the title, pause, clear, game-over and win pictures are fixed palette entries (white 4, accent 7, gold 3, dim 13, dark 0) instead of being guessed from each palette.
- The new `CHIX.DAT` is required (a 1.4.0 card is refused with "NEED CHIX.DAT").

## 1.4.0

- New stage pictures: all ten scenes (`tools/paint/scene00.png` .. `scene09.png`) are repainted (the first versions are kept in `tools/paint/v1/`). Each scene's palette comes with its picture in `CHIX.DAT`, and the colour turn every ten stages works as before. The new `CHIX.DAT` is required (a 1.3.x card is refused with "NEED CHIX.DAT").
- Includes the 1.3.2 smooth pace and the 1.3.3 fixes.

## 1.3.3

- A direction tapped while the ship is between cells is kept for a few frames and used at the next cell, so short taps and quick turns are not lost; it is dropped on a death, a pause or a blocked move (no step on its own after a respawn).
- A spark and the ship that swap cells in the same frame now collide (they could pass through each other).
- The spinning enemies turn smoothly: a 128-step sine read from the 32-step table, instead of a jump every few frames.
- A spark moved by a claim leaves no afterglow at its old place; a pick-up blinks for its last 3 seconds again (not 6).

## 1.3.2

- Smooth pace: the game logic runs every frame again (1.3.1 skipped one frame in three, which looked choppy). The ship now covers half a cell, one pixel, every frame when walking or drawing fast (a quarter cell slow, a whole cell with SPEED UP), drawn between cells, so crossing the field takes twice as long as in 1.3.0 with the same step every frame. A turn waits until the ship reaches its cell.
- The rest is scaled to match, so the difficulty is about the same as 1.3.0: the enemy moves at half speed (its line is drawn at pixel precision) and spins at half rate, the sparks advance a quarter cell a frame (half from stage 6, three quarters from 36) and are drawn between cells, the fuse burns one cell a frame and lights after 3 s of stalling, and power-ups, pick-ups, the pick-up wait and the combo window last twice as long. Scores and percentages are unchanged.

## 1.3.1

- The ship is smaller (12x12, was 16x16), with the thruster flicker kept.
- The level takes longer to cross: in play the game logic now runs two frames in three, so the ship, lines, enemy, sparks and fuse are all 1.5 times slower together (the difficulty is unchanged; the picture and effects still draw every frame). A finer grid did not fit in RAM (a 90x84 grid needs about 4 KB more).

## 1.3.0

- The stage pictures are now painted 120x112 images read from `CHIX.DAT` on the SD card (`tools/make_card.py` builds it from `tools/paint/sceneNN.png`; copy it to the card's root). A claimed cell shows the picture as it is; a slow claim also twinkles gold. Each stage's fill colours come from its picture's palette. Without the file (or with another build's) the game shows "NEED CHIX.DAT" and checks again each second.
- New art, all read from `CHIX.DAT`: a painted title, pause menu, level-clear, game-over and win screen (each with its own palette and a cycling neon), a new ship, sparks, power-up icons (a clearer heart and bomb) and 24x24 enemy cores (the wireframe cage is drawn over the core). Sprites are remapped to the nearest colours of each stage's palette.
- Palette effects: lightning, a fade-in at each stage, a shimmering wet street and a flickering neon sign. Rain falls at three depths, flying cars cross the claimed picture, and there are animations for a claim, a spark or ship exploding, a pick-up and the combo star.
- Version 1.3.0 adds `CHIX.DAT` (238 KB, root of the SD card) as a requirement. Flash use is 38.6 KB. Not done: parallax scrolling, the HUD picture, level intro screens.
- The procedural skyline is gone, and so is a floating-point sine table that pulled in about 8 KB of maths library: flash use falls from 50.2 KB to 41.7 KB.

## 1.2.3

- Fixed: a stage could be cleared at 100% after claiming only about 60%. If the enemy happened to be standing on the line you closed, the game found no open ground to keep and claimed all of it; it now starts from the nearest open cell (and puts the enemy back in the open).
- Fixed: the frame rate dipped as the field filled, because every claimed cell drew four picture pixels (about 53 ms a frame at 73% claimed). The picture's detail now steps down as more is claimed (full detail up to 18%, then two pixels, then one a cell), which keeps frames under 30 ms.
- The share to claim now rises faster: 70% at stage 1, two more points every stage, and 85% from stage 9 on.

## 1.2.2

The music crossfades between stages: the old song fades out over half a second and the new one fades in, instead of cutting over (and the old song's last notes and drums no longer run into the new stage). Sound effects stay at full level through the fade.

## 1.2.1

The three slow songs (the title, aurora and nebula) are rewritten with a groove and a melody, and the whole mix is about 1.4x louder, with a soft limiter on the peaks.

## 1.2

Twenty more stages (45 in all): five new solids as enemies, then twin pairs that you can blow up by walling one in, a fourth
spark and faster sparks. Three new songs (progressive, an 80 BPM nebula and hi-tech). More sizzle: combos up to x5, the field's
frame pulses on every kick, lightning in the rainy cities, rainbow lights from stage 26, and every ten stages the cities are rebuilt
and the colours turn. The arp voice now reads the lead delayed instead of its own copy, which saved 1.5 KB.

## 1.1

The music now plays on a small software FM synth: bell, pluck and arpeggio voices with drums, mixed in an interrupt, with the sound effects over the top. Six new songs (psychill and the ambient aurora at 80 BPM, then dark psy, goa, full-on and forest, from calmest to most frantic), each with its own sound and a sweeping FM index. Still about 16 ms a frame.

## 1.0

First release: 25 stages with ten detailed cityscapes drawn per pixel, eight main enemies, ten power-ups, an acid-techno soundtrack, a pause menu and a saved game. About 16 ms a frame on the board.
