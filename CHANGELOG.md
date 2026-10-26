# Changelog

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
