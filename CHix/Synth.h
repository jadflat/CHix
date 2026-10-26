// CHix's sound: a small software synth. The music is three FM voices (a lead, a bass and an arpeggio) and
// a noise-and-sine drum voice, read from step sequences (Music.h); the sound effects are a square voice
// playing the game's step tables. Everything is mixed in a timer interrupt and sent to the piezo as PWM
// (see Synth.cpp), so the music and an effect sound together.
#pragma once
#include <CHGame.h>

namespace synth {

void begin();                           // device: starts the sample interrupt (the simulator is silent)
void music(int song);                   // 0 title, 1..8 the stage songs; -1 stops
uint8_t beat();                         // call once a frame: nonzero for a few frames after each kick
void sfx(const audio::Effect &e);       // an effect from the game's table; a higher or equal priority one replaces it

}  // namespace synth
