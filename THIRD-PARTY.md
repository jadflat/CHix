# Third-party credits

## The sound output (CHix/Synth.cpp)

CHix plays its music and effects on a small software synth. Two projects, both hosted in
[ESPboy-edu/ESPboy_CHCore](https://github.com/ESPboy-edu/ESPboy_CHCore), showed that this board can do it, and are credited here:

- [LIBS/chgame-soundtracks](https://github.com/ESPboy-edu/ESPboy_CHCore/tree/main/LIBS/chgame-soundtracks) (the repository is
  [juliendorra/chgame-soundtracks](https://github.com/juliendorra/chgame-soundtracks), "ATM Soundtracks", a music demo for CHGame built on
  [ATMlib](https://github.com/T-arg/ATMlib)). The way CHix drives the piezo, an 8-bit PWM on TIM1 channel 2 (PB10) written by a timer
  interrupt, follows its design: the timer and pin setup in `CHix/Synth.cpp` uses the same registers and values. It is under the BSD 3-Clause
  licence, reproduced below as that licence requires, and ATMlib's authors (TEAM a.r.g., Davey Taylor and Joeri Gantois) are named in it.
- [Games/CHeleste/Cheleste](https://github.com/ESPboy-edu/ESPboy_CHCore/tree/main/Games/CHeleste/Cheleste) (a CHGame port of Celeste Classic with
  a software mixer, `PicoSynth`) showed that mixing several voices in software for this piezo is practical. **No code from it is used.**

Everything above the timer setup (the FM voices, the drums, the step sequencer, the songs and the crossfade) is CHix's own.

The BSD 3-Clause text of chgame-soundtracks:

```
BSD 3-Clause License

Copyright (c) 2016 - 2026, TEAM a.r.g.
Copyright (c) 2016 - 2018, Davey Taylor
Copyright (c) 2016 - 2026, Joeri Gantois
Copyright (c) 2026, CHGame demo contributors (CHGame port and demo code)
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

## CHGame

Built on CHGame, Copyright 2026 Kevin Bates (bateske), Apache-2.0: the framework is vendored in `chgame/` (see `chgame/NOTICE` and `chgame/LICENSE`).

## The pixel-art skill

The sprites and boss cores were rendered with the author's own CHGame-tuned "pixel-art-gen" Claude skill from grids drawn for this game.
