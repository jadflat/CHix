// CHix's sound (Synth.h): a small software synth mixed in the sample interrupt and sent to the piezo as PWM.
//
// The hardware setup follows chgame-soundtracks (ESPboy-edu/ESPboy_CHCore, LIBS/chgame-soundtracks, BSD 3-Clause: see THIRD-PARTY.md).
// The hardware is the playbook's PWM-as-DAC recipe: TIM1 CH2 on PB10 is an 8-bit PWM carrier (187.5 kHz), and
// TIM3's update interrupt writes one sample to it SYN_RATE times a second. The music is a step sequencer over
// Music.h's streams: three 2-operator FM voices (a modulator at a whole-number ratio of the carrier, with its
// own decaying index: a bell, a pluck and a pad) and one drum voice (a sine that drops for the kick, noise for
// the snare and hats). The game's sound effects are one more voice, a square wave that plays its step tables.
#include "Synth.h"
#include "Music.h"
#if defined(__riscv) && !defined(CHSIM)
#include <Arduino.h>
#include <chgame/RamFunc.h>
#define SYN_DEVICE 1
#else
#define SYN_DEVICE 0
#define RAMFUNC(name)
#endif

namespace {

#ifndef SYN_GAIN
#define SYN_GAIN 22                                       // 1.375 x: louder, with the soft knee squashing the peaks instead of clipping them
#endif
constexpr uint16_t ENV_DIV = SYN_RATE / 122;            // samples between envelope ticks (about 8 ms)

struct Voice { uint16_t ph, mph, inc, minc; uint8_t idx, eff, vol; bool gate; };       // eff: idx plus the sweep
Voice v[3];

struct Drum { uint16_t ph, inc, lfsr; uint8_t vol, kind, decay; };      // kind 0 kick, 1 snare, 2 hat
Drum dr = { 0, 0, 0xACE1, 0, 0, 0 };
volatile uint8_t kickFlash = 0;                          // set on each kick: the picture can pulse with the beat

struct Sfx { const audio::Step *st; uint8_t n, i, ticks, prio, amp; bool soft; uint16_t inc, ph; int16_t dinc; };
Sfx sf = {};

const SongHdr *cur = nullptr;
const Inst *ins = SONGS[0].inst;                        // the instruments of the song playing (or the last one, for the release)
uint8_t sweepNow = 0;
int8_t curId = -1, pendingId = -2;                       // the song playing, and the one fading in after it (-2: none)
uint8_t fade = 255;                                      // the music's master level
int8_t fadeDir = 0;                                      // -1 fading out, +1 fading in
uint8_t pos = 0;                                        // the step in the song, 0-255
uint16_t stepCnt = 0, stepLen = 0, envCnt = 0;

inline uint16_t noteInc(uint8_t n) {
    const int o = n / 12 - 5;                           // C4 is octave 0
    const uint32_t b = NOTE_INC16[n % 12];
    return (uint16_t)(o >= 0 ? (b << o) >> 4 : b >> (4 - o));
}

void noteOn(int i, uint8_t n) {
    Voice &c = v[i];
    const Inst &in = ins[i];
    c.inc = noteInc(n);
    c.minc = (uint16_t)(c.inc * in.ratio);
    c.mph = 0;
    c.idx = in.idx0;
    c.eff = in.idx0;
    c.vol = in.amp;
    c.gate = true;
}

void drumOn(uint8_t bits) {
    if (bits & 1) { kickFlash = 3; dr.kind = 0; dr.inc = 1310; dr.vol = 175; dr.decay = 14; }              // 160 Hz, dropping
    else if (bits & 2) { dr.kind = 1; dr.inc = 1556; dr.vol = 150; dr.decay = 18; }
    else if (bits & 8) { dr.kind = 2; dr.vol = 80; dr.decay = 7; }
    else if (bits & 4) { dr.kind = 2; dr.vol = 84; dr.decay = 26; }
}

void startSong(int song) {
    for (int i = 0; i < 3; i++) { v[i].vol = 0; v[i].gate = false; }     // the last song's notes and drums do not carry into this one
    dr.vol = 0; kickFlash = 0; sweepNow = 0;
    if (song < 0 || song >= 9) { cur = nullptr; curId = -1; return; }
    cur = &SONGS[song];
    curId = (int8_t)song;
    ins = cur->inst;
    stepLen = (uint16_t)(cur->stepMs * SYN_RATE / 1000);
    stepCnt = 1;
    pos = 0;
}

void nextStep() {
    const uint8_t *s[2] = { cur->lead, cur->bass };
    for (int i = 0; i < 3; i++) {
        const uint8_t b = i == 2 ? cur->lead[(uint8_t)(pos - cur->delay)] : s[i][pos];      // the arp is the lead, delayed
        if (b == 0) v[i].gate = false;
        else if (b > 1) noteOn(i, b);
    }
    if (cur->drums[pos]) drumOn(cur->drums[pos]);
    const uint8_t t = pos & 63, tri = t < 32 ? t : 63 - t;                   // four bars: the sweep opens and closes
    sweepNow = (uint8_t)((tri * cur->sweep) >> 5);
    pos++;
}

void sfxStep() {
    if (sf.i >= sf.n) { sf.n = 0; sf.amp = 0; sf.prio = 0; return; }
    const audio::Step &s = sf.st[sf.i];
    const uint16_t inc = (uint16_t)(s.hz * 164u);       // 20 Hz units to a phase increment at SYN_RATE
    sf.ticks = (uint8_t)((s.ms * 62u >> 8) + 1);
    sf.dinc = s.endHz ? (int16_t)(((int)s.endHz * 164 - (int)inc) / sf.ticks) : 0;
    sf.inc = inc;
    sf.amp = s.hz ? (sf.soft ? 44 : 104) : 0;
}

void envTick() {
    if (fadeDir < 0) {
        if (fade > 4) fade -= 4;
        else {
            fade = 0;
            if (pendingId != -2) { startSong(pendingId); pendingId = -2; fadeDir = cur ? 1 : 0; } else fadeDir = 0;
        }
    } else if (fadeDir > 0) {
        if (fade < 251) fade += 4; else { fade = 255; fadeDir = 0; }
    }
    for (int i = 0; i < 3; i++) {
        Voice &c = v[i];
        const Inst &in = ins[i];
        if (!c.vol) continue;
        if (c.idx > in.idxFloor + in.idxDecay) c.idx -= in.idxDecay; else c.idx = in.idxFloor;
        c.eff = (i == 1) ? c.idx : (uint8_t)(c.idx + sweepNow > 255 ? 255 : c.idx + sweepNow);   // the bass keeps its tone
        if (c.gate) {
            if (c.vol > in.volFloor + in.volDecay) c.vol -= in.volDecay; else c.vol = in.volFloor;
        } else {
            c.vol = c.vol > 14 ? c.vol - 14 : 0;                                              // released
        }
    }
    if (dr.vol) {
        if (dr.kind == 0 && dr.inc > 360) dr.inc -= dr.inc >> 2;                              // the kick's pitch drops
        dr.vol = dr.vol > dr.decay ? dr.vol - dr.decay : 0;
    }
    if (sf.n) {
        sf.inc += sf.dinc;
        if (--sf.ticks == 0) { sf.i++; sfxStep(); }
    }
}

}  // namespace

namespace synth {

uint8_t sample() {                                       // runs from flash: the RAM for a RAM function is not there
    if (++envCnt >= ENV_DIV) { envCnt = 0; envTick(); }
    if (cur && --stepCnt == 0) { stepCnt = stepLen; nextStep(); }
    int mix = 0;
    for (int i = 0; i < 3; i++) {
        Voice &c = v[i];
        if (!c.vol) continue;
        c.ph += c.inc;
        c.mph += c.minc;
        const int m = (SINE[c.mph >> 8] * c.eff) >> 5;                  // the modulator bends the carrier's phase
        mix += (SINE[(uint8_t)((c.ph >> 8) + m)] * c.vol) >> 7;
    }
    if (dr.vol) {
        dr.ph += dr.inc;
        if (dr.kind) {
            uint16_t x = dr.lfsr;
            x ^= x << 7; x ^= x >> 9; x ^= x << 8;
            dr.lfsr = x;
            const int nz = (int)(x >> 8) - 128;
            mix += (nz * dr.vol) >> 7;
            if (dr.kind == 1) mix += (SINE[dr.ph >> 8] * dr.vol) >> 7;
        } else {
            mix += (SINE[dr.ph >> 8] * dr.vol) >> 8;
        }
    }
    if (fade < 255) mix = (mix * fade) >> 8;                           // the crossfade (the effects stay at full level)
    if (sf.amp) {
        sf.ph += sf.inc;
        mix += (sf.ph & 0x8000) ? sf.amp : -sf.amp;
    }
    mix = (mix * SYN_GAIN) >> 4;                                          // the master volume (16 = as mixed)
    if (mix > 96) mix = 96 + ((mix - 96) >> 2); else if (mix < -96) mix = -96 + ((mix + 96) >> 2);   // a soft knee: peaks squash, they do not clip
    return (uint8_t)(128 + (mix > 127 ? 127 : mix < -128 ? -128 : mix));
}

#if SYN_DEVICE
#define SYN_LOCK() __disable_irq()
#define SYN_UNLOCK() __enable_irq()
#else
#define SYN_LOCK()
#define SYN_UNLOCK()
#endif

void music(int song) {
    const int id = (song < 0 || song >= 9) ? -1 : song;
    SYN_LOCK();
    if (!cur) {                                          // nothing playing: start at once and fade in
        if (id >= 0) { startSong(id); fade = 0; fadeDir = 1; }
        pendingId = -2;
    } else if (id == curId) {                            // asked for the song that is playing: keep it (and cancel a fade away from it)
        pendingId = -2;
        if (fadeDir < 0) fadeDir = 1;
    } else {                                             // another song (or silence): fade this one out first
        pendingId = (int8_t)id;
        fadeDir = -1;
    }
    SYN_UNLOCK();
}

uint8_t beat() {                                          // once a frame: nonzero for a few frames after each kick
    const uint8_t k = kickFlash;
    if (k) kickFlash = k - 1;
    return k;
}

void sfx(const audio::Effect &e) {
    SYN_LOCK();
    const uint8_t prio = e.flags & 15;
    if (!sf.n || prio >= sf.prio) {
        sf.st = e.steps; sf.n = e.n; sf.i = 0; sf.prio = prio; sf.soft = (e.flags & audio::SOFT) != 0;
        sf.ph = 0;
        sfxStep();
    }
    SYN_UNLOCK();
}

}  // namespace synth

#if SYN_DEVICE
extern "C" volatile uint32_t CFGHR_tmpB;
extern "C" void TIM3_IRQHandler(void) __attribute__((interrupt("WCH-Interrupt-fast")));
extern "C" void TIM3_IRQHandler(void) {
    TIM3->INTFR = ~1u;
    TIM1->CH2CVR = synth::sample();
}

void synth::begin() {
    RCC->APB2PCENR |= RCC_APB2Periph_AFIO | RCC_APB2Periph_GPIOB | RCC_APB2Periph_TIM1;
    RCC->APB1PCENR |= RCC_APB1Periph_TIM3;
    AFIO->PCFR1 = (AFIO->PCFR1 & ~(7u << 15)) | (1u << 15);          // TIM1 partial remap: CH2 on PB10
    CFGHR_tmpB = (CFGHR_tmpB & ~(15u << 8)) | (11u << 8);            // alternate-function push-pull
    GPIOB->CFGHR = CFGHR_tmpB;
    TIM1->CTLR1 = 0; TIM1->DMAINTENR = 0; TIM1->CCER = 0;
    TIM1->PSC = 0; TIM1->ATRLR = 255; TIM1->CNT = 0;
    TIM1->CHCTLR1 = 0x6800; TIM1->CH2CVR = 128;
    TIM1->RPTCR = 0; TIM1->BDTR = 0x8000; TIM1->CCER = 0x10;
    TIM1->SWEVGR = 1; TIM1->CTLR1 = 0x81;                            // 187.5 kHz carrier
    TIM3->CTLR1 = 0; TIM3->DMAINTENR = 0;
    TIM3->PSC = 0; TIM3->ATRLR = 48000000u / SYN_RATE - 1; TIM3->CNT = 0;
    TIM3->SWEVGR = 1; TIM3->INTFR = 0; TIM3->DMAINTENR = 1;
    NVIC_SetPriority(TIM3_IRQn, 0);
    NVIC_EnableIRQ(TIM3_IRQn);
    TIM3->CTLR1 = 1;
}
#else
void synth::begin() {}
#endif
