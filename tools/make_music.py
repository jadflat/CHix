"""CHix's music: nine tracks (two ambient at 80 bpm, seven psytrance), as step sequences for the software FM synth (CHix/Synth.cpp).

  title    psychill   80 bpm   C dorian         slow bells over a sparse kick
(stage 1 is ambient at 80 bpm too; the other songs run 125, 131, 136 and 140 bpm)
  stage 1  aurora     F lydian          long bells and a drone, 80 bpm, almost no drums
  stage 2  dark psy   C phrygian        inharmonic 5:1 and 7:1 FM, falling laser runs, one bass note between the kicks
  stage 3  goa        E double-harmonic an oriental line in 3:1 metallic FM, clap on 2 and 4
  stage 4  full-on    A phrygian        the rolling bass bounces over octaves, a hypnotic lead
  stage 5  forest     D minor           swarming up-and-down arps, short plucks, rolling hats
  stages 26 on, in turn: progressive (D dorian, 128 bpm), nebula (ambient, 80 bpm), hi-tech (F# phrygian, 165 bpm)

A song is 16 bars of sixteen steps; three streams of one byte a step:
  lead, bass, arp: 0 = rest (the note is released), 1 = hold, 2..127 = a MIDI note (a new note);
  drums: a bit mask, 1 kick, 2 snare, 4 closed hat, 8 open hat.
The arp voice plays the lead echoed (a delay line) a few steps later, read from the lead stream, as a psytrance producer would send it to a delay.
Each song names its own FM instruments (the modulator's ratio, its index and how it decays) and how far
the index sweeps over four bars, like a filter opening and closing.

Writes CHix/Music.h (the songs, the sine table and the pitch table for the synth's sample rate).
Run: python tools/make_music.py
"""
import math
import os

RATE = 8000                        # the synth's sample rate: Synth.cpp's SYN_RATE must match
N = None

SCALES = {
    'dorian': [0, 2, 3, 5, 7, 9, 10],
    'phrygian': [0, 1, 3, 5, 7, 8, 10],
    'doubleharm': [0, 1, 4, 5, 7, 8, 11],       # the oriental scale of goa
    'minor': [0, 2, 3, 5, 7, 8, 10],
    'lydian': [0, 2, 4, 6, 7, 9, 11],
}


def deg(scale, d):
    s = SCALES[scale]
    return s[d % 7] + 12 * (d // 7)


# lead patterns: scale degrees (7 is the octave), None a rest
def lead_stream(root, scale, pats, order, shifts):
    out = []
    for bar, name in enumerate(order):
        for d in pats[name]:
            out.append(0 if d is None else root + shifts[bar % 8] + deg(scale, d))
    return out


# bass: semitone offsets from the bar's bass root, one pattern per beat style
BASS = {
    'roll_oct': [N, 0, 12, 0] * 4,                                  # full-on: root, octave, root between the kicks
    'roll': [N, 0, 0, 7] * 4,                                       # goa
    'offbeat': [N, N, 0, N] * 4,                                    # dark: one note between the kicks
    'swarm': [N, 0, 0, 12] * 4,                                     # forest
    'long': [0, N, N, N, N, N, N, N, 7, N, N, N, N, N, N, N],       # psychill
    'dub': [0, N, N, 0, N, N, 7, N, 0, N, 3, N, 7, N, 5, N],        # downtempo: a syncopated groove under the half-time kick
    'pulse': [0, N, N, N, N, N, N, N, 0, N, N, N, 7, N, N, N],      # a slow pulse
}


def bass_stream(root, style, shifts, bars=16):
    out = []
    for bar in range(bars):
        for o in BASS[style]:
            out.append(0 if o is None else root - 12 + shifts[bar % 8] + o)
    return out


def echo(lead, delay):
    n = len(lead)
    return [lead[(i - delay) % n] for i in range(n)]


def drums(style, bars=16):
    out = []
    for bar in range(bars):
        d = [0] * 16
        intro = bar < 4
        if style == 'down':                                    # half-time: kick on 1 and the 'and' of 2, snare on 3
            d[0] |= 1; d[7] |= 1
            if bar % 2:
                d[10] |= 1
            d[8] |= 2
            for sx in (4, 12, 15):
                d[sx] |= 4
            if bar % 4 == 3:
                d[6] |= 8
        elif style == 'air2':                                  # a soft pulse and a hat
            if bar % 2 == 0:
                d[0] |= 1
            d[8] |= 4
            if bar % 2:
                d[12] |= 4
        elif style == 'air':
            if bar % 2 == 0:
                d[8] |= 4
            if bar % 4 == 3:
                d[14] |= 4
        elif style == 'chill':
            d[0] |= 1; d[8] |= 1
            for s in (4, 12):
                d[s] |= 4
        else:
            for s in (0, 4, 8, 12):
                d[s] |= 1
            for s in (2, 6, 10, 14):
                d[s] |= 8 if style != 'forest' else 4
            if not intro:
                if style in ('goa', 'full'):
                    d[4] |= 2; d[12] |= 2                      # a clap on 2 and 4
                if style == 'full':
                    for s in (1, 5, 9, 13):
                        d[s] |= 4
                if style == 'dark':
                    d[12] |= 2
                if style == 'forest':
                    for s in range(16):
                        if not d[s]:
                            d[s] |= 4                          # rolling hats on every free step
        if bar % 8 == 7 and style not in ('air', 'air2', 'down'):                    # a fill into the next eight bars
            d[12] |= 1; d[13] |= 4; d[14] |= 2; d[15] |= 2
        out.append(d)
    return [x for b in out for x in b]


SONGS = []


def add(name, ms, sweep, inst, lead, bass, delay, dr, fixed=False):
    assert len(lead) == len(bass) == len(dr) == 256, name
    SONGS.append(dict(name=name, ms=ms, sweep=sweep, inst=inst, lead=lead, bass=bass, delay=delay, drums=dr, fixed=fixed))


# ---- 0 title: downtempo dub, C dorian, 80 bpm. A hook in eighth notes over a half-time groove
P = {'A': [7, N, 9, N, 10, N, 9, N, 7, N, N, 5, N, N, 7, N],
     'B': [9, N, 10, N, 12, N, 10, N, 9, N, 7, N, 5, N, N, N],
     'C': [12, N, 10, N, 9, N, 7, N, 9, N, 10, N, 12, N, 14, N],
     'D': [10, N, N, 9, N, N, 7, N, 5, N, 7, N, 9, N, N, N]}
order = list('ABAD' + 'CBCD' + 'ABAD' + 'CBDA')
sh = [0, 0, 5, 5, 0, 0, 7, 7]                               # Cm, Fm, Cm, Gm
lead = lead_stream(72, 'dorian', P, order, sh)
add('TITLE', 188, 12, [(1, 28, 1, 6, 94, 1, 48), (1, 24, 3, 4, 104, 1, 74), (2, 24, 2, 3, 52, 2, 0)],
    lead, bass_stream(72, 'dub', sh), 3, drums('down'), fixed=True)

# ---- ambient stage song: F lydian, 80 bpm. Rolling arpeggios over a slow pulse
P = {'A': [7, N, 9, N, 11, N, 9, N, 8, N, 10, N, 12, N, 10, N],
     'B': [14, N, 13, N, 11, N, 9, N, 7, N, 9, N, 11, N, N, N],
     'C': [12, N, 14, N, 15, N, 14, N, 12, N, 11, N, 9, N, N, N],
     'D': [11, N, 13, N, 14, N, 16, N, 14, N, 13, N, 11, N, N, N]}
order = list('ABAC' + 'BDAC' + 'ABCD' + 'BADC')
sh = [0, 0, -3, -3, -5, -5, 0, 0]                           # F, Dm, Bb
lead = lead_stream(65, 'lydian', P, order, sh)
add('AURORA', 188, 10, [(1, 24, 1, 4, 92, 1, 46), (1, 18, 3, 3, 104, 2, 70), (3, 22, 2, 2, 50, 2, 0)],
    lead, bass_stream(65, 'pulse', sh), 3, drums('air2'), fixed=True)

# ---- 1 full-on: A phrygian, 145 bpm
P = {'A': [7, N, 7, N, 8, N, 7, N, 7, N, 10, N, 9, N, 8, N],
     'B': [7, 8, 9, 8, 7, 8, 9, 10, 11, 10, 9, 8, 7, 8, 9, 8],
     'C': [14, N, N, 12, N, N, 11, N, N, 10, N, N, 9, N, 8, 7]}
order = list('AABAABCB' + 'AABABCCB')
lead = lead_stream(69, 'phrygian', P, order, [0, 0, 0, 0, 0, 0, -2, 1])
add('FULLON', 103, 40, [(2, 54, 3, 12, 112, 2, 40), (1, 44, 6, 6, 125, 3, 75), (3, 40, 5, 3, 62, 5, 0)],
    lead, bass_stream(69, 'roll_oct', [0, 0, 0, 0, 0, 0, -2, 1]), 3, drums('full'))

# ---- 2 goa: E double harmonic, 138 bpm
P = {'A': [0, 1, 4, N, 5, 4, 1, N, 0, N, 1, 4, 5, N, 7, N],
     'B': [7, 8, 7, 5, 4, N, 5, 4, 1, N, 4, N, 1, 0, N, N],
     'C': [11, N, 8, 7, N, 5, 4, N, 5, 4, 1, N, 0, 1, 4, N]}
order = list('AABABBCA' + 'AABBCBCA')
lead = lead_stream(76, 'doubleharm', P, order, [0] * 8)
add('GOA', 109, 28, [(3, 48, 2, 14, 108, 2, 35), (2, 36, 5, 6, 120, 3, 70), (1, 40, 4, 4, 60, 5, 0)],
    lead, bass_stream(64, 'roll', [0, 0, 0, 0, 1, 1, 0, 0]), 2, drums('goa'))

# ---- 3 dark psy: C phrygian, 150 bpm
P = {'A': [14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, N],
     'B': [7, N, N, 7, N, N, 8, N, N, 7, N, N, 10, N, N, N],
     'C': [0, N, N, 1, N, N, 0, N, 3, N, N, 1, N, N, 0, N]}
order = list('CCBCABCA' + 'CBCBAABA')
lead = lead_stream(72, 'phrygian', P, order, [0] * 8)
add('DARK', 100, 50, [(5, 60, 2, 20, 105, 1, 45), (1, 50, 7, 8, 128, 4, 70), (7, 46, 4, 10, 58, 4, 0)],
    lead, bass_stream(72, 'offbeat', [0, 0, 1, 0, 0, 0, 1, 0]), 3, drums('dark'))

# ---- 4 forest: D minor, 155 bpm
P = {'A': [0, 2, 4, 2, 0, 2, 4, 7, 4, 2, 0, 2, 4, 7, 9, 7],
     'B': [7, 9, 11, 9, 7, 9, 11, 14, 11, 9, 7, 9, 11, 14, 16, 14],
     'C': [0, N, 0, N, 2, N, 2, N, 4, N, 4, N, 7, N, 9, N]}
order = list('AABAABBC' + 'AABABBCC')
lead = lead_stream(74, 'minor', P, order, [0, 0, 0, 0, 0, 0, -2, -2])
add('FOREST', 97, 34, [(2, 44, 4, 8, 100, 4, 20), (1, 40, 8, 5, 118, 5, 60), (4, 38, 6, 4, 56, 6, 0)],
    lead, bass_stream(62, 'swarm', [0, 0, 0, 0, 0, 0, -2, -2]), 3, drums('forest'))

# ---- progressive: D dorian, 128 bpm (stages 26 on)
P = {'A': [7, N, N, 9, N, N, 10, N, 9, N, N, 7, N, N, 5, N],
     'B': [7, 9, 10, 9, 7, 9, 10, 12, 10, 9, 7, 5, 7, 9, 10, 9],
     'C': [14, N, 12, N, 10, N, 9, N, 7, N, N, N, 9, N, 10, N]}
order = list('AABAABCB' + 'ABABCBCA')
lead = lead_stream(74, 'dorian', P, order, [0, 0, 0, 0, -2, -2, 3, 3])
add('PROG', 117, 32, [(2, 46, 3, 10, 108, 2, 38), (1, 42, 6, 6, 122, 3, 72), (4, 36, 5, 3, 58, 5, 0)],
    lead, bass_stream(62, 'roll_oct', [0, 0, 0, 0, -2, -2, 3, 3]), 3, drums('full'))

# ---- nebula: ambient, A dorian, 80 bpm. Slow rolling chords, a long delay
P = {'A': [0, N, 2, N, 4, N, 7, N, 4, N, 2, N, 0, N, N, N],
     'B': [2, N, 4, N, 6, N, 9, N, 6, N, 4, N, 2, N, N, N],
     'C': [7, N, 9, N, 11, N, 14, N, 11, N, 9, N, 7, N, N, N],
     'D': [4, N, 6, N, 7, N, 9, N, 11, N, 9, N, 7, N, 4, N]}
order = list('ABCD' + 'ACBD' + 'ABAD' + 'CDBA')
sh = [0, 0, -2, -2, -4, -4, 0, 0]
lead = lead_stream(69, 'dorian', P, order, sh)
add('NEBULA', 188, 8, [(1, 20, 1, 3, 88, 1, 46), (1, 16, 2, 2, 100, 1, 72), (3, 22, 2, 2, 48, 2, 0)],
    lead, bass_stream(57, 'pulse', sh), 4, drums('air2'), fixed=True)

# ---- hi-tech: F# phrygian, 165 bpm (the last stages)
P = {'A': [7, N, 7, 8, 7, N, 10, 7, 7, N, 7, 8, 7, 12, 10, 8],
     'B': [14, 12, 10, 8, 7, 8, 10, 12, 14, 12, 10, 8, 7, N, N, N],
     'C': [0, N, 0, 1, N, 0, 3, N, 0, N, 0, 1, N, 3, 1, N]}
order = list('CCABCCAB' + 'ABABCABB')
lead = lead_stream(66, 'phrygian', P, order, [0, 0, 0, 1, 0, 0, -2, 1])
add('HITECH', 91, 56, [(6, 58, 3, 18, 108, 2, 40), (1, 46, 7, 8, 126, 4, 74), (5, 44, 4, 8, 60, 4, 0)],
    lead, bass_stream(66, 'swarm', [0, 0, 0, 1, 0, 0, -2, 1]), 2, drums('forest'))

# the stage songs play in order, building from the calmest to the most frantic: aurora (ambient), dark psy, goa, full-on, forest
byname = {sg['name']: sg for sg in SONGS}
SONGS = [byname[n] for n in ('TITLE', 'AURORA', 'DARK', 'GOA', 'FULLON', 'FOREST', 'PROG', 'NEBULA', 'HITECH')]
for sg in SONGS:                                   # a little slower: a step is a tenth longer (the ambient songs are fixed at 80 bpm)
    if not sg['fixed']:
        sg['ms'] = int(round(sg['ms'] * 1.1))

out = ["// Generated by tools/make_music.py: six step sequences for the FM synth, the sine table and the pitch table.",
       "#pragma once", "#include <stdint.h>", "", "#define SYN_RATE %d" % RATE, ""]
out.append("static const int8_t SINE[256] = {")
sine = [int(round(127 * math.sin(i * 2 * math.pi / 256))) for i in range(256)]
for i in range(0, 256, 32):
    out.append("    " + ",".join(str(v) for v in sine[i:i + 32]) + ",")
out.append("};")
inc16 = [int(round(440 * 2 ** ((60 + k - 69) / 12) * 65536 / RATE * 16)) for k in range(12)]
assert max(inc16) < 65536
out.append("static const uint16_t NOTE_INC16[12] = { " + ", ".join(str(v) for v in inc16) + " };")
out.append("// an FM voice: the modulator's ratio to the carrier, its index at the start, how fast it falls and where it stops,")
out.append("// the voice's volume at the start, how fast it falls while held and where it stops")
out.append("struct Inst { uint8_t ratio, idx0, idxDecay, idxFloor, amp, volDecay, volFloor; };")
out.append("struct SongHdr { const uint8_t *lead, *bass, *drums; const Inst *inst; uint8_t stepMs, sweep, delay; };   // the arp is the lead delayed by `delay` steps")
for sg in SONGS:
    nm = sg['name']
    out.append("static const Inst %s_INST[3] = { %s };" % (nm, ", ".join("{ %s }" % ", ".join(str(x) for x in i) for i in sg['inst'])))
    for part in ('lead', 'bass', 'drums'):
        out.append("static const uint8_t %s_%s[256] = {" % (nm, part.upper()))
        for i in range(0, 256, 32):
            out.append("    " + ",".join(str(v) for v in sg[part][i:i + 32]) + ",")
        out.append("};")
out.append("static const SongHdr SONGS[9] = {")
for sg in SONGS:
    nm = sg['name']
    out.append("    { %s_LEAD, %s_BASS, %s_DRUMS, %s_INST, %d, %d, %d }," % (nm, nm, nm, nm, sg['ms'], sg['sweep'], sg['delay']))
out.append("};")
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'CHix', 'Music.h'), 'w', newline='').write("\n".join(out) + "\n")
print("wrote Music.h")
