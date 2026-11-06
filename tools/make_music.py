"""CHix's music: nine tracks (three ambient at 80 bpm, six psytrance), as step sequences for the software FM synth (CHix/Synth.cpp).

  title    psychill   80 bpm   C dorian         slow bells over a half-time dub groove
  stage 1  aurora     F lydian          long bells and a slow pulse, 80 bpm, almost no drums
  stage 2  dark psy   C phrygian        inharmonic 5:1 and 7:1 FM, falling laser runs, offbeat bass, then a rolling one
  stage 3  goa        E double-harmonic an oriental line in 3:1 metallic FM, clap on 2 and 4
  stage 4  full-on    A phrygian        the rolling bass bounces over octaves, a hypnotic lead
  stage 5  forest     D minor           swarming up-and-down arps, short plucks, rolling hats
  stages 26 on, in turn: progressive (D dorian), nebula (ambient, 80 bpm), hi-tech (F# phrygian)

A song is 16 bars of sixteen steps; three streams of one byte a step:
  lead, bass: 0 = rest (the note is released), 1 = hold, 2..127 = a MIDI note (a new note);
  drums: a bit mask, 1 kick, 2 snare, 4 closed hat, 8 open hat.
The arp voice plays the lead echoed (a delay line) a few steps later, read from the lead stream, as a psytrance producer would send it to a delay.
Every second time through, the synth echoes the lead two steps later and turns the sweep the other way, so a song only repeats
exactly after 32 bars (Synth.cpp).
Each song names its own FM instruments (the modulator's ratio, its index and how it decays), how far the index sweeps over
four bars, like a filter opening and closing, and its level (LEVEL, 255 = as mixed), which evens out the loudness between songs.

Writes CHix/Music.h (the songs, the sine table and the pitch table for the synth's sample rate).
Run: python tools/make_music.py
"""
import math
import os

RATE = 8000                        # the synth's sample rate: Synth.cpp's SYN_RATE must match
N = None                           # a rest: the note is released
H = 'H'                            # hold the note before

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


def tok(v, note):
    return 0 if v is None else 1 if v == H else note


# lead patterns: scale degrees (7 is the octave), N a rest, H a hold. shifts: semitones a bar (8 or 16 bars, repeated)
def lead_stream(root, scale, pats, order, shifts):
    out = []
    for bar, name in enumerate(order):
        for d in pats[name]:
            out.append(tok(d, 0 if d in (None, H) else root + shifts[bar % len(shifts)] + deg(scale, d)))
    return out


# bass: semitone offsets from the bar's bass root, one pattern per beat style
BASS = {
    'roll_oct': [N, 0, 12, 0] * 4,                                  # full-on: root, octave, root between the kicks
    'roll_oct_dn': [N, 0, 12, 0] * 3 + [N, 12, 10, 7],              # ... and a walk down into the next bar
    'roll_oct_up': [N, 0, 12, 0] * 3 + [N, 3, 5, 7],                # ... and a walk up
    'roll': [N, 0, 0, 7] * 4,                                       # goa
    'roll_b': [N, 0, 0, 7] * 3 + [N, 12, 7, 1],
    'roll_up': [N, 0, 0, 7] * 3 + [N, 5, 7, 8],
    'offbeat': [N, N, 0, N] * 4,                                    # dark: one note between the kicks
    'offbeat_b': [N, N, 0, N] * 3 + [N, 1, 0, 1],
    'kbbb': [N, 0, 0, 0] * 4,                                       # dark, second half: the rolling kick-bass-bass-bass
    'kbbb_b': [N, 0, 0, 0] * 3 + [N, 1, 3, 1],
    'swarm': [N, 0, 0, 12] * 4,                                     # forest
    'swarm_b': [N, 0, 12, 0, N, 0, 0, 12, N, 0, 12, 0, N, 7, 5, 3],
    'swarm_up': [N, 0, 0, 12] * 3 + [N, 3, 5, 7],
    'long': [0, N, N, N, N, N, N, N, 7, N, N, N, N, N, N, N],       # psychill
    'dub': [0, N, N, 0, N, N, 7, N, 0, N, 3, N, 7, N, 5, N],        # downtempo: a syncopated groove under the half-time kick
    'dub_b': [0, N, N, 0, N, N, 7, N, 0, N, 3, N, 5, N, 7, 10],     # ... with a run up into the next bar
    'pulse': [0, N, N, N, N, N, N, N, 0, N, N, N, 7, N, N, N],      # a slow pulse
    'pulse_b': [0, H, H, H, N, N, 7, N, 12, N, N, N, 7, N, 5, N],   # a slow pulse that moves (the root held a beat)
}


def bass_stream(root, styles, shifts, bars=16):
    """styles: one style name for every bar, or a list of 16."""
    if isinstance(styles, str):
        styles = [styles] * bars
    out = []
    for bar in range(bars):
        for o in BASS[styles[bar]]:
            out.append(tok(o, 0 if o in (None, H) else root - 12 + shifts[bar % len(shifts)] + o))
    return out


def var(base, **bars):
    """16 bass styles: `base` everywhere, with the bars named b3=..., b7=... changed."""
    s = [base] * 16
    for k, v in bars.items():
        s[int(k[1:])] = v
    return s


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
            if bar == 15:                                      # a soft turn back to the top
                d[13] |= 4; d[14] |= 2
        elif style == 'air2':                                  # a soft pulse and a hat
            if bar % 2 == 0:
                d[0] |= 1
            d[8] |= 4
            if bar % 2:
                d[12] |= 4
            if bar % 8 == 7:
                d[14] |= 4; d[15] |= 4
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
                    if bar >= 8:
                        d[7] |= 4; d[15] |= 4                  # the second half drives harder
                if style == 'forest':
                    for s in range(16):
                        if not d[s]:
                            d[s] |= 4                          # rolling hats on every free step
            if bar in (3, 11):                                 # a small fill: a snare on the last step
                d[15] = 2
            elif bar == 7:                                     # a fill into the next eight bars
                d[12] |= 1; d[13] = 4; d[14] = 2; d[15] = 2
            elif bar == 15:                                    # the kick drops for the last beat: a snare roll back to the top
                d[12] = 2; d[13] = 2; d[14] = 2; d[15] = 2
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
     'D': [10, N, N, 9, N, N, 7, N, 5, N, 7, N, 9, N, N, N],
     'E': [12, H, H, 10, H, H, 9, N, 7, H, H, N, 9, N, 7, N]}           # a held answer for the last bar
order = list('ABAD' + 'CBCD' + 'ABAD' + 'CBDE')
sh = [0, 0, 5, 5, 0, 0, 7, 7]                               # Cm, Fm, Cm, Gm
lead = lead_stream(72, 'dorian', P, order, sh)
add('TITLE', 188, 12, [(1, 28, 1, 6, 94, 1, 48), (1, 24, 3, 4, 104, 1, 74), (2, 24, 2, 3, 52, 2, 0)],
    lead, bass_stream(72, var('dub', b3='dub_b', b7='dub_b', b11='dub_b', b15='dub_b'), sh), 3, drums('down'), fixed=True)

# ---- ambient stage song: F lydian, 80 bpm. Rolling arpeggios over a slow pulse
P = {'A': [7, N, 9, N, 11, N, 9, N, 8, N, 10, N, 12, N, 10, N],
     'B': [14, N, 13, N, 11, N, 9, N, 7, N, 9, N, 11, N, N, N],
     'C': [12, N, 14, N, 15, N, 14, N, 12, N, 11, N, 9, N, N, N],
     'D': [11, N, 13, N, 14, N, 16, N, 14, N, 13, N, 11, N, N, N]}
order = list('ABAC' + 'BDAC' + 'ABCD' + 'BADC')
sh = [0, 0, -3, -3, -5, -5, 0, 0]                           # F, Dm, Bb
lead = lead_stream(65, 'lydian', P, order, sh)
add('AURORA', 188, 10, [(1, 24, 1, 4, 92, 1, 46), (1, 18, 3, 3, 104, 2, 70), (3, 22, 2, 2, 50, 2, 0)],
    lead, bass_stream(65, ['pulse'] * 4 + ['pulse_b'] * 4 + ['pulse'] * 4 + ['pulse_b'] * 4, sh), 3, drums('air2'), fixed=True)

# ---- full-on: A phrygian. A hypnotic call (held notes) and answer, moving to C, G and Bb in the second half
P = {'A': [7, N, 7, N, 8, N, 7, N, 7, N, 10, N, 9, N, 8, N],
     'B': [7, 8, 9, 8, 7, 8, 9, 10, 11, 10, 9, 8, 7, 8, 9, 8],
     'C': [14, N, N, 12, N, N, 11, N, N, 10, N, N, 9, N, 8, 7],
     'D': [7, N, 8, N, 10, N, 8, 7, N, 7, 5, N, 4, N, 3, N],
     'E': [7, H, H, N, 7, H, 8, N, 10, H, H, N, 12, N, 11, N],
     'F': [14, 12, 11, 10, 9, 8, 7, 8, 9, 10, 11, 12, 14, N, N, N]}
order = list('AEAD' + 'AEBB' + 'EDED' + 'ABCF')
sh = [0, 0, 0, 0, 0, 0, -2, 1, 0, 0, 0, 0, 3, 3, -2, 1]
lead = lead_stream(69, 'phrygian', P, order, sh)
add('FULLON', 103, 40, [(2, 54, 3, 12, 112, 2, 40), (1, 44, 6, 6, 125, 3, 75), (3, 40, 5, 3, 62, 5, 0)],
    lead, bass_stream(69, var('roll_oct', b3='roll_oct_dn', b7='roll_oct_up', b11='roll_oct_dn', b13='roll_oct_dn', b15='roll_oct_up'), sh),
    3, drums('full'))

# ---- goa: E double harmonic. Long held calls between the oriental runs; the bass moves to F and A
P = {'A': [0, 1, 4, N, 5, 4, 1, N, 0, N, 1, 4, 5, N, 7, N],
     'B': [7, 8, 7, 5, 4, N, 5, 4, 1, N, 4, N, 1, 0, N, N],
     'C': [11, N, 8, 7, N, 5, 4, N, 5, 4, 1, N, 0, 1, 4, N],
     'D': [4, 5, 7, N, 8, 7, 5, 4, N, 4, 5, N, 1, 0, H, N],
     'E': [0, H, H, 1, 4, H, 5, N, 7, H, H, 8, 7, 5, 4, N],
     'F': [7, 8, 11, 8, 7, 5, 4, 5, 7, N, 5, 4, 1, N, 0, N]}
order = list('AEAD' + 'ABCD' + 'EEAB' + 'CDBF')
lead = lead_stream(76, 'doubleharm', P, order, [0] * 8)
add('GOA', 109, 28, [(3, 48, 2, 14, 108, 2, 35), (2, 36, 5, 6, 120, 3, 70), (1, 40, 4, 4, 60, 5, 0)],
    lead, bass_stream(64, var('roll', b3='roll_b', b7='roll_up', b11='roll_b', b15='roll_up'),
                      [0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 5, 0]), 2, drums('goa'))

# ---- dark psy: C phrygian. Falling lasers and a slow held line; the bass rolls (kick-bass-bass-bass) in the second half
P = {'A': [14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, N],
     'B': [7, N, N, 7, N, N, 8, N, N, 7, N, N, 10, N, N, N],
     'C': [0, N, N, 1, N, N, 0, N, 3, N, N, 1, N, N, 0, N],
     'D': [0, N, 1, 0, N, N, 3, N, 1, 0, N, N, 8, 7, N, N],
     'E': [12, H, H, H, 11, H, H, H, 10, H, 8, H, 7, N, N, N],
     'F': [7, 6, 7, 8, 7, 6, 7, 8, 10, 8, 7, 8, 14, 13, 12, 11]}
order = list('CCBD' + 'CCAE' + 'DBDB' + 'EAFA')
lead = lead_stream(72, 'phrygian', P, order, [0] * 8)
add('DARK', 100, 50, [(5, 60, 2, 20, 105, 1, 45), (1, 50, 7, 8, 128, 4, 70), (7, 46, 4, 10, 58, 4, 0)],
    lead, bass_stream(72, var('offbeat', b3='offbeat_b', b7='offbeat_b', b8='kbbb', b9='kbbb', b10='kbbb', b11='kbbb_b',
                                b12='kbbb', b13='kbbb', b14='kbbb', b15='kbbb_b'),
                      [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, -4, -4, 1, 0]), 3, drums('dark'))

# ---- forest: D minor. The swarm breathes: sparse, syncopated bars and groups of three between the runs
P = {'A': [0, 2, 4, 2, 0, 2, 4, 7, 4, 2, 0, 2, 4, 7, 9, 7],
     'B': [7, 9, 11, 9, 7, 9, 11, 14, 11, 9, 7, 9, 11, 14, 16, 14],
     'C': [0, N, 0, N, 2, N, 2, N, 4, N, 4, N, 7, N, 9, N],
     'D': [0, N, 4, 2, N, 4, 7, N, 4, N, 2, 0, N, 2, N, N],
     'E': [9, 7, 4, N, 9, 7, 4, N, 11, 9, 7, N, 11, 9, 7, N],
     'F': [14, 11, 9, 7, 9, 11, 14, 16, 14, 11, 9, 7, 4, 2, 0, N]}
order = list('ADAE' + 'ADBC' + 'EEDA' + 'BBEF')
sh = [0, 0, 0, 0, 0, 0, -2, -2, 0, 0, 3, 3, -4, -4, -2, -2]
lead = lead_stream(74, 'minor', P, order, sh)
add('FOREST', 97, 34, [(2, 44, 4, 8, 100, 4, 20), (1, 40, 8, 5, 118, 5, 60), (4, 38, 6, 4, 56, 6, 0)],
    lead, bass_stream(62, var('swarm', b3='swarm_b', b7='swarm_up', b11='swarm_b', b15='swarm_up'), sh), 3, drums('forest'))

# ---- progressive: D dorian (stages 26 on). Held phrases, and a lift to G in the second half
P = {'A': [7, N, N, 9, N, N, 10, N, 9, N, N, 7, N, N, 5, N],
     'B': [7, 9, 10, 9, 7, 9, 10, 12, 10, 9, 7, 5, 7, 9, 10, 9],
     'C': [14, N, 12, N, 10, N, 9, N, 7, N, N, N, 9, N, 10, N],
     'D': [10, H, H, 9, H, H, 7, H, 5, H, 7, H, 9, N, N, N],
     'E': [12, N, 10, 9, N, 7, 9, N, 10, N, 12, N, 14, N, 12, N]}
order = list('AABD' + 'ABCD' + 'EBEA' + 'CDBE')
sh = [0, 0, 0, 0, -2, -2, 3, 3, 0, 0, 0, 0, 5, 5, 3, -2]
lead = lead_stream(74, 'dorian', P, order, sh)
add('PROG', 117, 32, [(2, 46, 3, 10, 108, 2, 38), (1, 42, 6, 6, 122, 3, 72), (4, 36, 5, 3, 58, 5, 0)],
    lead, bass_stream(62, var('roll_oct', b3='roll_oct_up', b7='roll_oct_dn', b11='roll_oct_up', b15='roll_oct_dn'), sh),
    3, drums('full'))

# ---- nebula: ambient, A dorian, 80 bpm. Slow rolling chords, a long delay
P = {'A': [0, N, 2, N, 4, N, 7, N, 4, N, 2, N, 0, N, N, N],
     'B': [2, N, 4, N, 6, N, 9, N, 6, N, 4, N, 2, N, N, N],
     'C': [7, N, 9, N, 11, N, 14, N, 11, N, 9, N, 7, N, N, N],
     'D': [4, N, 6, N, 7, N, 9, N, 11, N, 9, N, 7, N, 4, N]}
order = list('ABCD' + 'ACBD' + 'ABAD' + 'CDBA')
sh = [0, 0, -2, -2, -4, -4, 0, 0]
lead = lead_stream(69, 'dorian', P, order, sh)
add('NEBULA', 188, 8, [(1, 20, 1, 3, 92, 1, 48), (1, 16, 2, 2, 104, 1, 76), (3, 22, 2, 2, 50, 2, 0)],
    lead, bass_stream(57, ['pulse'] * 6 + ['pulse_b'] * 2 + ['pulse'] * 6 + ['pulse_b'] * 2, sh), 4, drums('air2'), fixed=True)

# ---- hi-tech: F# phrygian (the last stages). Stabs and runs, with a falling answer and a move to A
P = {'A': [7, N, 7, 8, 7, N, 10, 7, 7, N, 7, 8, 7, 12, 10, 8],
     'B': [14, 12, 10, 8, 7, 8, 10, 12, 14, 12, 10, 8, 7, N, N, N],
     'C': [0, N, 0, 1, N, 0, 3, N, 0, N, 0, 1, N, 3, 1, N],
     'D': [0, 1, 3, 1, 0, N, 7, N, 0, 1, 3, 1, 0, N, 8, 7],
     'E': [12, N, 10, N, 8, N, 7, N, 12, 10, 8, 7, 5, N, 3, N]}
order = list('CDAB' + 'CDAE' + 'ADAB' + 'EBEC')
sh = [0, 0, 0, 1, 0, 0, -2, 1, 0, 0, 0, 1, 3, 3, -2, 1]
lead = lead_stream(66, 'phrygian', P, order, sh)
add('HITECH', 91, 56, [(6, 58, 3, 18, 108, 2, 40), (1, 46, 7, 8, 126, 4, 74), (5, 44, 4, 8, 60, 4, 0)],
    lead, bass_stream(66, var('swarm', b3='swarm_b', b7='swarm_up', b11='swarm_b', b15='swarm_up'), sh), 2, drums('forest'))

# the stage songs play in order, building from the calmest to the most frantic: aurora (ambient), dark psy, goa, full-on, forest
byname = {sg['name']: sg for sg in SONGS}
SONGS = [byname[n] for n in ('TITLE', 'AURORA', 'DARK', 'GOA', 'FULLON', 'FOREST', 'PROG', 'NEBULA', 'HITECH')]
for sg in SONGS:                                   # a little slower: a step is a tenth longer (the ambient songs are fixed at 80 bpm)
    if not sg['fixed']:
        sg['ms'] = int(round(sg['ms'] * 1.1))

# each song's master level (255 = as mixed), measured on the PC render (tools: render the synth to WAV and compare
# the rms after the soft knee): the busy psytrance songs ran into the limiter and clipped, the ambient ones were quieter
LEVEL = {'TITLE': 224, 'AURORA': 255, 'DARK': 188, 'GOA': 180, 'FULLON': 172, 'FOREST': 192, 'PROG': 180, 'NEBULA': 248, 'HITECH': 168}

out = ["// Generated by tools/make_music.py: nine step sequences for the FM synth, the sine table and the pitch table.",
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
out.append("struct SongHdr { const uint8_t *lead, *bass, *drums; const Inst *inst; uint8_t stepMs, sweep, delay, level; };"
           "   // the arp is the lead delayed by `delay` steps; level: 255 = as mixed")
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
    out.append("    { %s_LEAD, %s_BASS, %s_DRUMS, %s_INST, %d, %d, %d, %d }," % (nm, nm, nm, nm, sg['ms'], sg['sweep'], sg['delay'], LEVEL[nm]))
out.append("};")
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'CHix', 'Music.h'), 'w', newline='').write("\n".join(out) + "\n")
print("wrote Music.h")
