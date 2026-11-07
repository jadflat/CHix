// CHix: a territory-claiming arcade game for CHGame.
//
// Original C++ code. Draw a line from the border into the open field and close it back on a border: the
// side without the main enemy is claimed. Hold A to draw fast (blue, 10 points a cell) or B to draw slow
// (orange, 20). Sparks run along the borders and the main enemy roams the field; the enemy touching your
// open line, or a spark touching you, loses a life. Claim the stage's share of the field to clear it.
//
// The playfield is a 60x56 grid of 2x2-pixel cells; the frame buffer is written directly (4 bits a pixel:
// a 2-pixel cell is one byte a row).
#include <CHGame.h>
#include "Card.h"       // CHIX.DAT on the SD card: the stage pictures (Card.cpp, tools/make_card.py)
#include "CardIndex.h"
#include "Shapes.h"     // the late-game wireframes (tools/make_shapes.py)
#include <chgame/RamFunc.h>
#include "Synth.h"      // the sound: a small FM synth and a step sequencer (Synth.cpp, Music.h from tools/make_music.py)

static inline bool enemyTwin();
static inline int enemyKind();
static bool freeAt(int ax, int ay);
static void blit(uint8_t id, int x, int y, uint8_t mode = 0, int ymax = 128);

enum { W = 60, H = 56, OX = 4, OY = 14, };
enum Cell : uint8_t { EMPTY = 0, FAST = 1, SLOW = 2, TRAIL = 3, MARK = 0x10, BORD = 0x20 };   // BORD: cached border flag on claimed cells
enum Col : uint8_t { C_BG, C_FAST, C_SLOW, C_TRAIL, C_EDGE, C_PLAYER, C_SPARK, C_Q0, C_Q1, C_FASTL, C_SLOWL, C_TEXT, C_FASTD, C_SLOWD, C_FRAME, C_GLOW };
enum State : uint8_t { TITLE, PLAY, DYING, CLEARED, OVER, PAUSED };

enum Sfx : uint8_t { S_START, S_STEP, S_CLAIM, S_BIG, S_DIE, S_CLEAR, S_OVER, S_LIFE, S_POWER, S_ZAP, S_COUNT };
AUDIO_STEPS(ST_START) = { AUDIO_STEP(1047, 0, 70), AUDIO_STEP(1319, 0, 70), AUDIO_STEP(1568, 0, 70), AUDIO_STEP(2093, 0, 160) };
AUDIO_STEPS(ST_STEP)  = { AUDIO_STEP(900, 0, 8) };
AUDIO_STEPS(ST_CLAIM) = { AUDIO_STEP(700, 1400, 90), AUDIO_STEP(1400, 1800, 60) };
AUDIO_STEPS(ST_BIG)   = { AUDIO_STEP(700, 1400, 70), AUDIO_STEP(1047, 2093, 90), AUDIO_STEP(1568, 2637, 140) };
AUDIO_STEPS(ST_DIE)   = { AUDIO_STEP(1800, 900, 120), AUDIO_STEP(900, 1500, 90), AUDIO_STEP(1500, 400, 200), AUDIO_STEP(400, 120, 300) };
AUDIO_STEPS(ST_CLEAR) = { AUDIO_STEP(1047, 0, 100), AUDIO_STEP(1319, 0, 100), AUDIO_STEP(1568, 0, 100), AUDIO_STEP(2093, 0, 100), AUDIO_STEP(1568, 0, 100), AUDIO_STEP(2093, 0, 300) };
AUDIO_STEPS(ST_OVER)  = { AUDIO_STEP(600, 0, 200), AUDIO_STEP(500, 0, 200), AUDIO_STEP(400, 0, 200), AUDIO_STEP(250, 0, 450) };
AUDIO_STEPS(ST_LIFE)  = { AUDIO_STEP(1568, 0, 60), AUDIO_STEP(2093, 0, 60), AUDIO_STEP(2637, 0, 160) };
AUDIO_STEPS(ST_POWER) = { AUDIO_STEP(600, 2400, 160), AUDIO_STEP(2400, 3200, 90), AUDIO_STEP(1568, 0, 60), AUDIO_STEP(2637, 0, 160) };
AUDIO_STEPS(ST_ZAP)   = { AUDIO_STEP(3200, 700, 80) };
static const audio::Effect SOUNDS[] = {
    AUDIO_EFFECT(ST_START, 3), AUDIO_EFFECT(ST_STEP, 0 | audio::SOFT), AUDIO_EFFECT(ST_CLAIM, 4), AUDIO_EFFECT(ST_BIG, 5),
    AUDIO_EFFECT(ST_DIE, 8), AUDIO_EFFECT(ST_CLEAR, 7), AUDIO_EFFECT(ST_OVER, 8), AUDIO_EFFECT(ST_LIFE, 6), AUDIO_EFFECT(ST_POWER, 6), AUDIO_EFFECT(ST_ZAP, 5) };
static void playSfx(uint8_t id) { synth::sfx(SOUNDS[id]); }

static const uint8_t QCOL[4] = { C_Q0, C_Q1, C_TRAIL, C_EDGE };

// ---- stage themes: the fill colours come from the stage picture's own palette on the card (CHIX.DAT)
static int theme;

static uint8_t variant;                                        // 0..2: which turn of the colours this stage has (every ten stages)
static uint16_t tint(const uint8_t *c) { return gfx_rgb(c[variant % 3], c[(variant + 1) % 3], c[(variant + 2) % 3]); }
static int8_t palFor = -1;                                     // whose palette is loaded: 0..9 a scene's, 100 + n a screen's, -1: none
static uint8_t tr[5];                                          // a screen's text colours: light, accent, gold, dim, dark
static uint8_t base[16][3];                                    // the scene's palette (after the colour turn): what the effects start from
static void applyTheme(int t) { theme = t; palFor = -1; }


static int hiScore, nextLife = 1500000;
static bool won;
static int16_t fuse = -1;                       // the fuse burning down your open line (-1: none)
static uint8_t stallT;
static uint8_t g[H][W];
static uint16_t trail[640];
static int trailLen;
static State state;
static int px, py, startX, startY;
// Pace: the ship covers half a cell (one pixel) a frame, walking or drawing fast (a quarter slow, a whole cell with SPEED UP),
// so crossing the field takes twice as long as in 1.3.0 with the same step every frame. The logic moves a whole cell at
// once; prem (quarter cells) is how far the drawn ship still trails it, in direction (pdx, pdy).
static uint8_t prem, sAcc, qtick;               // sAcc: the Sparks' progress to their next cell (quarter cells); qtick: the enemy's moves
static int8_t pdx, pdy;
static uint8_t bT;                              // frames a tapped direction stays buffered (update())
static bool drawing, slowDraw;
static int lives, level, score, areaPct, timer, frameNo;
enum { STAGES = 45 };
static inline int tgt() { int t = 68 + 2 * level; return t > 85 ? 85 : t; }   // the share to claim: 70% at stage 1, 2 more a stage, 85% from stage 9 on
static inline int sparkN() { return level >= 30 ? 4 : level >= 8 ? 3 : 2; }   // a third Spark from stage 8, a fourth from 30
static uint32_t rng = 12345;

struct Spark { int x, y, dx, dy; bool right; };
static const int8_t SD4[4][2] = { {1, 0}, {0, 1}, {-1, 0}, {0, -1} };   // the Sparks' four directions, clockwise
static Spark sp[4];
static uint8_t sh[4][3][2];                    // each Spark's last three cells, for its afterglow
static int flash, clearBonus, popVal;
struct Anim { uint8_t t; int16_t x, y; };                       // one-shot animations from the card: 0 claim burst, 1 boom, 2 pickup sparkle
static Anim an[3];
static void anim(uint8_t k, int x, int y) { static const uint8_t LEN[3] = { 12, 16, 18 }; an[k].t = LEN[k]; an[k].x = (int16_t)x; an[k].y = (int16_t)y; }
static uint8_t combo, comboT;                                   // claims within four seconds of each other multiply the score
static uint8_t closing;                                         // a shape was closed: 2 closeClaim() is due next frame, 1 closeFinish()
static uint8_t ringT, ringCol, hitT, popT, readyT, respawnT, shakeT, invT;   // respawnT: the closing circle after a death; invT: invincible frames after it
static int16_t ringX, ringY, popX, popY;
static const int8_t COS24[24] = { 64, 62, 55, 45, 32, 17, 0, -17, -32, -45, -55, -62, -64, -62, -55, -45, -32, -17, 0, 17, 32, 45, 55, 62 };
enum { CLEAR_TIME = 140 };                     // the level-clear sequence, in frames
enum { Q_HIST = 6 };
struct QLine { int16_t x1, y1, x2, y2; };
static QLine qh[Q_HIST];
static int qhead;
static int qx[2], qy[2], qvx[2], qvy[2];      // 1/16 cell

static uint32_t rnd32() { rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5; return rng; }
static int rnd(int n) { return (int)(rnd32() % (uint32_t)n); }
static inline bool inb(int x, int y) { return x >= 0 && y >= 0 && x < W && y < H; }
static inline bool claimed(int x, int y) { uint8_t v = g[y][x] & 3; return v == FAST || v == SLOW; }
// A border cell touches ground that is not claimed yet (the open line counts), diagonals
// included: at an inside corner the way round is only joined diagonally, and the player and
// the Spark move in 4 directions. The flag is cached in the grid (BORD) and rebuilt only
// when ground is claimed, so the draw and the Spark do not scan neighbours every frame.
static inline bool isBorder(int x, int y) { return inb(x, y) && (g[y][x] & BORD); }

static inline bool cl(uint8_t v) { return (uint8_t)((v & 3) - 1) < 2; }      // a claimed cell, flags aside

static void markBorders() {
    for (int y = 1; y < H - 1; y++) {
        const uint8_t *a = g[y - 1];
        uint8_t *b = g[y];
        const uint8_t *c = g[y + 1];
        for (int x = 1; x < W - 1; x++) {
            if (!cl(b[x])) continue;
            bool open = !cl(a[x - 1]) || !cl(a[x]) || !cl(a[x + 1]) || !cl(b[x - 1]) || !cl(b[x + 1]) ||
                        !cl(c[x - 1]) || !cl(c[x]) || !cl(c[x + 1]);
            b[x] = (b[x] & 3) | (open ? BORD : 0);
        }
    }
    for (int y = 0; y < H; y++)                                 // the outer ring
        for (int x = 0; x < W; x += (y == 0 || y == H - 1) ? 1 : W - 1) {
            if (!claimed(x, y)) continue;
            bool open = false;
            for (int dy = -1; dy <= 1 && !open; dy++)
                for (int dx = -1; dx <= 1; dx++)
                    if (inb(x + dx, y + dy) && !claimed(x + dx, y + dy)) { open = true; break; }
            g[y][x] = (g[y][x] & 3) | (open ? BORD : 0);
        }
}

// ---- power-ups, particles, the banner ------------------------------------------------------
enum PU : uint8_t { PU_FREEZE, PU_SPEED, PU_LASER, PU_SHIELD, PU_SLOW, PU_BONUS, PU_X2, PU_GHOST, PU_BOMB, PU_LIFE, PU_COUNT };   // in the order they unlock
struct PuInfo { const char *name, *desc; char icon; uint8_t col, dur; };
static const PuInfo PUI[PU_COUNT] = {
    { "TIME FREEZE", "ENEMIES FROZEN", 'F', C_FASTL, 120 },
    { "SPEED UP", "LIGHTNING FAST", 'S', C_TRAIL, 180 },
    { "LASERS", "ZAP THE SPARKS", 'L', C_PLAYER, 150 },
    { "SHIELD", "INVINCIBLE", 'H', C_Q0, 200 },
    { "SLOW FOES", "ENEMIES SLOWED", 'Z', C_Q1, 240 },
    { "BONUS", "+2500 POINTS", '$', C_SLOWL, 0 },
    { "SCORE X2", "DOUBLE POINTS", 'X', C_SLOWL, 250 },
    { "GHOST TRAIL", "LINE IS SAFE", 'G', C_FASTL, 200 },
    { "BOMB", "SPARKS DESTROYED", 'B', C_SPARK, 0 },
    { "EXTRA LIFE", "ONE UP", '+', C_PLAYER, 0 } };
static uint8_t puT[PU_COUNT];                  // frames left of each
static struct { uint8_t x, y, type, life; } pu;   // life 0: none; counts down every 2 frames
static uint16_t puWait;
enum { NPART = 24 };
static struct Part { int16_t x, y; int8_t vx, vy; uint8_t life, col; } parts[NPART];   // 1/8 pixel
static const PuInfo *banner;
static uint8_t banT;

static void burst(int cx, int cy, int n, uint8_t col) {
    for (int i = 0; i < NPART && n > 0; i++)
        if (!parts[i].life) {
            parts[i] = { (int16_t)(cx * 8), (int16_t)(cy * 8), (int8_t)(rnd(29) - 14), (int8_t)(rnd(29) - 14),
                         (uint8_t)(14 + rnd(12)), col };
            n--;
        }
}

static void updateParts() {
    for (int i = 0; i < NPART; i++)
        if (parts[i].life) {
            parts[i].x += parts[i].vx; parts[i].y += parts[i].vy;
            if (!(frameNo & 1)) parts[i].vy++;
            parts[i].life--;
        }
}

static void placeSpark(int i) {                // on a border cell off the player's row and column, and not close to the player
    for (int t = 0; t < 60; t++) {
        int x = rnd(W), y = rnd(H);
        if (isBorder(x, y) && x != px && y != py && abs(x - px) + abs(y - py) >= 16) { sp[i].x = x; sp[i].y = y; goto done; }
    }
    {                                            // (none found: the border cell farthest from the player)
        int best = -1;
        for (int y = 0; y < H; y++)
            for (int x = 0; x < W; x++)
                if (isBorder(x, y) && abs(x - px) + abs(y - py) > best) { best = abs(x - px) + abs(y - py); sp[i].x = x; sp[i].y = y; }
    }
done:
    for (int k = 0; k < 3; k++) { sh[i][k][0] = sp[i].x; sh[i][k][1] = sp[i].y; }
}

static void collect() {
    const PuInfo &in = PUI[pu.type];
    if (pu.type == PU_BONUS) score += 2500;
    else if (pu.type == PU_LIFE) { if (lives < 6) lives++; playSfx(S_LIFE); }
    else if (pu.type == PU_BOMB) {
        for (int i = 0; i < sparkN(); i++) {
            burst(OX + 2 * sp[i].x, OY + 2 * sp[i].y, 8, C_SPARK);
            anim(1, OX + 2 * sp[i].x, OY + 2 * sp[i].y);
            placeSpark(i);
        }
        score += 1500;
        flash = 10; shakeT = 8;
    } else puT[pu.type] = in.dur;
    banner = &in; banT = 75;
    burst(OX + 2 * pu.x + 1, OY + 2 * pu.y + 1, 16, in.col);
    anim(2, OX + 2 * pu.x + 1, OY + 2 * pu.y + 1);
    playSfx(S_POWER);
    pu.life = 0;
}

static void spawnPickup() {
    for (int t = 0; t < 30; t++) {
        int x = 3 + rnd(W - 6), y = 3 + rnd(H - 6);
        if (g[y][x] == EMPTY) { pu = { (uint8_t)x, (uint8_t)y, (uint8_t)rnd(6 + (level >= 5) + (level >= 9) + (level >= 13) + (level >= 17)), 150 }; return; }
    }
}

static void resetField() {
    memset(g, EMPTY, sizeof g);
    closing = 0;
    for (int x = 0; x < W; x++) g[0][x] = g[H - 1][x] = FAST;
    for (int y = 0; y < H; y++) g[y][0] = g[y][W - 1] = FAST;
    areaPct = 0;
    markBorders();
}

static void resetActors(bool enemy = true) {          // (a respawn keeps the enemy where it is: 1.4.1 put it back in the middle, which could be claimed ground it could not leave)
    px = startX = W / 2; py = startY = H - 1; prem = sAcc = bT = 0;
    drawing = false; trailLen = 0;
    memset(puT, 0, sizeof puT); pu.life = 0; puWait = 0; banT = 0; memset(parts, 0, sizeof parts);
    sp[0] = { 1, 0, 1, 0, false };
    sp[1] = { W - 2, 0, -1, 0, true };
    sp[2] = { W / 2, 0, 1, 0, false };
    sp[3] = { 0, H / 2, 0, -1, false };
    combo = comboT = 0;
    fuse = -1; stallT = 0;
    for (int i = 0; i < 4; i++)
        for (int k = 0; k < 3; k++) { sh[i][k][0] = sp[i].x; sh[i][k][1] = sp[i].y; }
    if (!enemy) return;
    for (int i = 0; i < 2; i++) {
        qx[i] = (W / 2 + (i ? 6 : -6)) * 16; qy[i] = (H / 2 + (i ? -5 : 5)) * 16;
        qvx[i] = i ? -11 : 10; qvy[i] = i ? 8 : -9;
    }
    for (int i = 0; i < Q_HIST; i++)
        qh[i] = { (int16_t)(qx[0] >> 3), (int16_t)(qy[0] >> 3), (int16_t)(qx[1] >> 3), (int16_t)(qy[1] >> 3) };
}

#ifdef CHIX_DEMO_FILL
static void demoFill() {                                        // a build flag for looking at the pictures: most of the field claimed
    for (int y = 6; y < 50; y++) for (int x = 4; x < 56; x++) g[y][x] = x < 30 ? FAST : SLOW;
    markBorders();
    areaPct = 73;
}
#endif
static void newLevel() { resetField();
#ifdef CHIX_DEMO_FILL
    demoFill();
#endif
    resetActors(); readyT = 45; variant = (uint8_t)(((level - 1) / 10) % 3); applyTheme((level - 1) % 10); synth::music(level <= 25 ? 1 + (level - 1) % 5 : 6 + (level - 26) % 3); }
#ifndef CHIX_START_LEVEL
#define CHIX_START_LEVEL 1
#endif
static void newGame() { won = false; playSfx(S_START); nextLife = 1500000; lives = 3; level = CHIX_START_LEVEL; score = 0; newLevel(); state = PLAY; won = false;
#ifdef CHIX_TEST                                              // (simulator screenshots: 1 over, 2 won, 3 clear at 60)
    if (CHIX_TEST == 1 || CHIX_TEST == 2) { state = OVER; won = CHIX_TEST == 2; timer = 30; }
    if (CHIX_TEST == 3) { state = CLEARED; timer = 60; areaPct = 72; clearBonus = 5000; }
   
#endif
}

static void clearTrail() {
    for (int i = 0; i < trailLen; i++) g[trail[i] >> 6][trail[i] & 63] = EMPTY;
    trailLen = 0;
}

static void die() {
    burst(OX + 2 * px, OY + 2 * py, 16, C_PLAYER);
    anim(1, OX + 2 * px, OY + 2 * py);
    ringT = 14; ringX = OX + 2 * px + 1; ringY = OY + 2 * py + 1; ringCol = C_PLAYER; hitT = 8; shakeT = 10;
    burst(OX + 2 * px, OY + 2 * py, 12, C_EDGE);
    clearTrail();
    fuse = -1;
    px = startX; py = startY; prem = bT = 0;
    drawing = false;
    state = DYING; timer = 40;
    playSfx(S_DIE);
}

// The side without the main enemy is claimed: flood the open cells from it.
// Put the player on the nearest border cell: a closed shape can leave the end of the
// line, or the start, inside claimed ground, where a walk would cross into other sections.
static void snapPlayer() {
    if (isBorder(px, py)) return;
    int best = 1 << 20, bx = px, by = py;
    for (int y = 0; y < H; y++)
        for (int x = 0; x < W; x++)
            if (isBorder(x, y)) {
                int d = abs(x - px) + abs(y - py);
                if (d < best) { best = d; bx = x; by = y; }
            }
    px = bx; py = by; prem = 0;
}

// Debug builds: the perf report lists the time of each phase of closing a shape (microseconds a close).
// CHIX_DRAWPROF (with CHGAME_PROFILE=1 in tools/game.py, and a `prof` line after each `perf` in the script): the frame's
// phases instead, in us a frame: 6 update, 7 gfx_wait (the last flush), 8 cells, 9 scene and ambient, 10 enemy, pick-up and
// animations, 1 Sparks and ship, 2 particles, 3 HUD, 4 rings and texts, 5 banners, 11 the shake.
#ifdef CHIX_DRAWPROF
#define PROBE(i) ((void)0)
#define DPROBE(i) ((i) ? dbg::prof(i) : dbg::profStart())
#else
#define PROBE(i) ((i) ? dbg::prof((i) - 1) : dbg::profStart())
#define DPROBE(i) ((void)0)
#endif
enum { FLOODQ = 448 };                                          // (the scanline fill rarely needs 100; 896 B also hold a frame's sprites, sprPlan())
static uint16_t floodQ[FLOODQ];
// Mark the open cells joined to this one: a scanline fill (1.4.2: a run of open cells a step, about 5x faster on the board than
// the cell-by-cell fill, which took about 40 ms on a big first claim). The outer ring is always claimed, so no bounds checks.
// If the seed stack ever overflows, sweeps finish the job (slow but right).
static void floodFrom(int sx, int sy) {
    int sp = 0;
    bool lost = false;
    floodQ[sp++] = (sy << 6) | sx;
    while (sp) {
        const int c = floodQ[--sp], y = c >> 6;
        uint8_t *row = g[y];
        int l = c & 63, r = l;
        if (row[l] != EMPTY) continue;
        while (row[l - 1] == EMPTY) l--;
        while (row[r + 1] == EMPTY) r++;
        for (int x = l; x <= r; x++) row[x] |= MARK;
        for (int ny = y - 1; ny <= y + 1; ny += 2) {             // one seed for each open run above and below
            const uint8_t *nr = g[ny];
            bool in = false;
            for (int x = l; x <= r; x++) {
                if (nr[x] != EMPTY) { in = false; continue; }
                if (in) continue;
                in = true;
                if (sp < FLOODQ) floodQ[sp++] = (ny << 6) | x; else lost = true;
            }
        }
    }
    for (bool more = lost; more; ) {                              // (the overflow fallback)
        more = false;
        for (int y = 1; y < H - 1; y++)
            for (int x = 1; x < W - 1; x++)
                if (g[y][x] == EMPTY && ((g[y - 1][x] | g[y + 1][x] | g[y][x - 1] | g[y][x + 1]) & MARK)) { g[y][x] |= MARK; more = true; }
    }
}

static bool nearEmpty(int &sx, int &sy) {                             // this cell if it is open, else the nearest open one within 4
    for (int r = 0; r <= 4; r++)
        for (int dy = -r; dy <= r; dy++)
            for (int dx = -r; dx <= r; dx++) {
                int x = sx + dx, y = sy + dy;
                if ((abs(dx) == r || abs(dy) == r) && inb(x, y) && g[y][x] == EMPTY) { sx = x; sy = y; return true; }
            }
    return false;
}

// Closing a shape is split over three frames (1.4.2: on the board it took up to 47 ms in one, a 69 ms frame), each part
// overlapping the panel's flush: this frame floods the enemy's ground, the next claims the rest (closeClaim), the third
// marks the borders and scores (closeFinish). Nothing moves in the first two (the open cells carry MARK in between), and
// the border flags are stale in their pictures, which are both white claim-flash frames.
static bool seeded;
static int gained, openN, seedX[2], seedY[2];
static void closeTrail() {
    PROBE(0);
    const uint8_t v = slowDraw ? SLOW : FAST;
    gained = trailLen;
    for (int i = 0; i < trailLen; i++) g[trail[i] >> 6][trail[i] & 63] = v;
    trailLen = 0;
    drawing = false;
    closing = 2;
    flash = 11;                                                     // (white this frame and the next: the stale border flags do not show)
    // The ground the enemy is in stays open: flood from it. The enemy may be standing on a cell the new wall just took (the
    // line it sits on), so start from the nearest open cell; with no open cell near it nothing is claimed rather than everything.
    seedX[0] = seedX[1] = seedY[0] = seedY[1] = -1;
    seeded = false;
    for (int b = 0; b < (enemyKind() == 0 ? 2 : 1); b++) {            // the line enemy has two ends; a solid, or a twin's first body, one
        int sx = qx[b] >> 4, sy = qy[b] >> 4;
        if (inb(sx, sy) && (g[sy][sx] & MARK)) { seeded = true; continue; }       // already flooded from the other end
        if (nearEmpty(sx, sy)) { floodFrom(sx, sy); seedX[b] = sx; seedY[b] = sy; seeded = true; }
    }
    PROBE(1);
}

static void closeClaim() {
    closing = 1;
    const uint8_t v = slowDraw ? SLOW : FAST;
    openN = 0;
    for (int y = 1; y < H - 1; y++)
        for (int x = 1; x < W - 1; x++) {
            if (g[y][x] == EMPTY) { if (seeded) { g[y][x] = v; gained++; } else openN++; }
            else if (g[y][x] & MARK) { g[y][x] &= ~MARK; openN++; }
        }
    for (int b = 0; b < 2; b++)                                       // an enemy left inside claimed ground is put back in the open
        if (seedX[b] >= 0 && inb(qx[b] >> 4, qy[b] >> 4) && claimed(qx[b] >> 4, qy[b] >> 4)) { qx[b] = seedX[b] * 16 + 8; qy[b] = seedY[b] * 16 + 8; }
    PROBE(2);
}

static void closeFinish() {
    closing = 0;
    markBorders();
    PROBE(3);
    const int cm = comboT ? (combo < 5 ? combo + 1 : 5) : 1;       // each claim within four seconds of the last: x2, x3 ... x5
    combo = (uint8_t)cm; comboT = 240;
    const int pts = gained * (slowDraw ? 20 : 10) * (puT[PU_X2] ? 2 : 1) * cm;
    score += pts;
    if (score >= nextLife) { nextLife += 1500000; if (lives < 6) lives++; playSfx(S_LIFE); }
    else playSfx(gained > 150 || cm >= 3 ? S_BIG : S_CLAIM);
    areaPct = 100 - openN * 100 / ((W - 2) * (H - 2));
    for (int i = 0; i < sparkN(); i++) {                 // a Spark the fill swallowed starts again on a border
        if (isBorder(sp[i].x, sp[i].y)) continue;
        burst(OX + 2 * sp[i].x, OY + 2 * sp[i].y, 12, C_SPARK);           // a captured Spark blows up
        anim(1, OX + 2 * sp[i].x, OY + 2 * sp[i].y);
        burst(OX + 2 * sp[i].x, OY + 2 * sp[i].y, 6, C_EDGE);
        score += 1000; playSfx(S_ZAP);
        placeSpark(i);                                   // (1.5.4: away from the player, not the first border cell)
        for (int k = 0; k < 3; k++) { sh[i][k][0] = sp[i].x; sh[i][k][1] = sp[i].y; }   // no afterglow back where it was
    }
    if (enemyTwin()) {                                // a twin caught in the claimed ground blows up: it comes back beside the other
        int tx = qx[1] >> 4, ty = qy[1] >> 4;
        if (inb(tx, ty) && claimed(tx, ty)) {
            burst(OX + 2 * tx, OY + 2 * ty, 16, C_Q0);
            score += 3000; playSfx(S_ZAP);
            qx[1] = qx[0] + 5 * 16; qy[1] = qy[0] + 5 * 16;
            if (!freeAt(qx[1], qy[1])) { qx[1] = qx[0]; qy[1] = qy[0]; }
        }
    }
    PROBE(4);
    drawing = false;
    burst(OX + 2 * px, OY + 2 * py, gained > 150 ? 16 : 8, slowDraw ? C_SLOWL : C_FASTL);
    ringT = 14; ringX = popX = OX + 2 * px + 1; ringY = popY = OY + 2 * py + 1; ringCol = slowDraw ? C_SLOWL : C_FASTL; anim(0, ringX, ringY);
    if (gained > 250) shakeT = 6;
    popT = 36; popVal = pts;
    snapPlayer();
    PROBE(5);
    if (areaPct >= tgt()) {
        clearBonus = (areaPct - tgt()) * 100 + 1000;
        score += clearBonus;
        state = CLEARED; timer = CLEAR_TIME;
        playSfx(S_CLEAR);
    }
}

static void movePlayer(int dx, int dy, bool a, bool b) {
    int nx = px + dx, ny = py + dy;
    if (!inb(nx, ny)) return;
    if (!drawing) {
        if (claimed(nx, ny)) {
            if (isBorder(nx, ny)) { px = nx; py = ny; }
        } else if (g[ny][nx] == EMPTY && (a || b) && trailLen < 639) {
            slowDraw = b && !a;
            drawing = true; startX = px; startY = py;
            g[ny][nx] = TRAIL; trail[trailLen++] = (ny << 6) | nx;
            px = nx; py = ny;
        }
    } else if (g[ny][nx] == EMPTY) {
        if (trailLen >= 639) return;
        if (!(trailLen & 3)) playSfx(S_STEP);
        g[ny][nx] = TRAIL; trail[trailLen++] = (ny << 6) | nx;
        px = nx; py = ny;
    } else if (claimed(nx, ny)) {
        px = nx; py = ny;
        closeTrail();
    }
}

// Wall-following: one hand on the border, the other Spark on the other hand.
static int sparkNext(int n) {                                   // the direction (0..3) of Spark n's next cell, -1: stuck
    const Spark &s = sp[n];
    static const int8_t LEFT[4] = { 3, 0, 1, 2 }, RIGHT[4] = { 1, 0, 3, 2 };
    int cur = 0;
    for (int k = 0; k < 4; k++) if (SD4[k][0] == s.dx && SD4[k][1] == s.dy) cur = k;
    for (int i = 0; i < 4; i++) {
        int k = (cur + (s.right ? RIGHT[i] : LEFT[i])) & 3;
        if (isBorder(s.x + SD4[k][0], s.y + SD4[k][1])) return k;
    }
    return -1;
}
static void moveSpark(int n) {
    Spark &s = sp[n];
    sh[n][2][0] = sh[n][1][0]; sh[n][2][1] = sh[n][1][1];
    sh[n][1][0] = sh[n][0][0]; sh[n][1][1] = sh[n][0][1];
    sh[n][0][0] = s.x; sh[n][0][1] = s.y;
    const int k = sparkNext(n);
    if (k >= 0) { s.dx = SD4[k][0]; s.dy = SD4[k][1]; s.x += s.dx; s.y += s.dy; }
}

static bool freeAt(int ax, int ay) {
    int cx = ax >> 4, cy = ay >> 4;
    return inb(cx, cy) && (g[cy][cx] == EMPTY || g[cy][cx] == TRAIL);
}

static uint8_t bsc[2] = { 16, 16 };                             // boss size, 16 = the old size (see sizeBoss)
// An end of the roaming line, grown or shrunk about its middle (1/16 cell); p is qx or qy.
static int lineEnd(int i, const int *p) { const int m = (p[0] + p[1]) >> 1; return max(0, min(m + (p[i] - m) * bsc[0] / 16, (p == qx ? W : H) * 16 - 1)); }   // clamped to the field

static void moveCore() {                                        // (at half the 1.3.0 speed: half the velocity a frame, kept exact over two frames)
    const bool odd = ++qtick & 1;
    for (int i = 0; i < 2; i++) {
        if ((qtick & 31) == i * 14) {
            int lim = 12 + min(level * 2 / 3, 14);              // the core gets faster
            qvx[i] = constrain(qvx[i] + rnd(5) - 2, -lim, lim);
            qvy[i] = constrain(qvy[i] + rnd(5) - 2, -lim, lim);
            if (qvx[i] == 0) qvx[i] = 3;
            if (qvy[i] == 0) qvy[i] = -3;
        }
        const int vx = (qvx[i] + odd) >> 1, vy = (qvy[i] + odd) >> 1;
        if (freeAt(qx[i] + vx, qy[i] + vy)) { qx[i] += vx; qy[i] += vy; }
        else if (freeAt(qx[i] + vx, qy[i])) { qx[i] += vx; qvy[i] = -qvy[i]; }
        else if (freeAt(qx[i], qy[i] + vy)) { qy[i] += vy; qvx[i] = -qvx[i]; }
        else { qvx[i] = -qvx[i]; qvy[i] = -qvy[i]; }
    }
    if (!odd) return;                                           // the pull and the afterimages: every other move, as in 1.3.0
    int ddx = qx[1] - qx[0], ddy = qy[1] - qy[0];                 // keep the line short: pull the ends together
    if (!enemyTwin() && abs(ddx) + abs(ddy) > 16 * 16) {
        qvx[0] += ddx > 0; qvx[0] -= ddx < 0; qvx[1] -= ddx > 0; qvx[1] += ddx < 0;
        qvy[0] += ddy > 0; qvy[0] -= ddy < 0; qvy[1] -= ddy > 0; qvy[1] += ddy < 0;
    }
    qhead = (qhead + 1) % Q_HIST;
    qh[qhead] = { (int16_t)(lineEnd(0, qx) >> 3), (int16_t)(lineEnd(0, qy) >> 3), (int16_t)(lineEnd(1, qx) >> 3), (int16_t)(lineEnd(1, qy) >> 3) };   // pixels
}

// The solid breathes (1.4.4): every frame its size eases one step (16 = the old size) towards what fits: the clear room around it
// (eight probes, up to 10 cells) and the open ground left on the stage. Big in a wide open field, small as it squeezes through gaps.
static void sizeBoss() {
    static const int8_t PX[8] = { 1, 1, 0, -1, -1, -1, 0, 1 }, PY[8] = { 0, 1, 1, 1, 0, -1, -1, -1 };
    const int areaMax = 26 - areaPct * 13 / 100;                // 26 on an empty stage down to 16 at 75%
    for (int b = 0; b < (enemyTwin() ? 2 : 1); b++) {
        const int cx = (enemyKind() ? qx[b] : (qx[0] + qx[1]) >> 1) >> 4, cy = (enemyKind() ? qy[b] : (qy[0] + qy[1]) >> 1) >> 4;   // the line sizes from its middle
        int room = 10;
        for (int d = 0; d < 8 && room > 2; d++) {
            int n = 0;
            while (n < room && inb(cx + PX[d] * (n + 1), cy + PY[d] * (n + 1)) && !cl(g[cy + PY[d] * (n + 1)][cx + PX[d] * (n + 1)])) n++;
            if (n < room) room = n;
        }
        int want = room * 4 + 4;
        if (want > areaMax) want = areaMax;
        if (want < 9) want = 9;
        if (!enemyKind() && want > 22) want = 22;                // the long line stays modest
        if (bsc[b] + 1 < want) bsc[b]++; else if (bsc[b] > want + 1) bsc[b]--;   // a one-step dead band: no flicker at the edge
    }
}

// ---- the main enemy: a roaming line, then spinning wireframe solids (one kind a level) ----------
struct Shape { const int8_t (*v)[3]; const uint8_t (*e)[2]; uint8_t nv, ne; };
static const int8_t V_CUBE[8][3] = { {-16,-16,-16}, {16,-16,-16}, {16,16,-16}, {-16,16,-16}, {-16,-16,16}, {16,-16,16}, {16,16,16}, {-16,16,16} };
static const uint8_t E_CUBE[12][2] = { {0,1}, {1,2}, {2,3}, {3,0}, {4,5}, {5,6}, {6,7}, {7,4}, {0,4}, {1,5}, {2,6}, {3,7} };
static const int8_t V_OCTA[6][3] = { {22,0,0}, {-22,0,0}, {0,22,0}, {0,-22,0}, {0,0,22}, {0,0,-22} };
static const uint8_t E_OCTA[12][2] = { {0,2}, {0,3}, {0,4}, {0,5}, {1,2}, {1,3}, {1,4}, {1,5}, {2,4}, {2,5}, {3,4}, {3,5} };
static const int8_t V_PYRA[5][3] = { {-18,14,-18}, {18,14,-18}, {18,14,18}, {-18,14,18}, {0,-22,0} };
static const uint8_t E_PYRA[8][2] = { {0,1}, {1,2}, {2,3}, {3,0}, {0,4}, {1,4}, {2,4}, {3,4} };
static const int8_t V_PRISM[6][3] = { {-20,-16,0}, {-20,14,-16}, {-20,14,16}, {20,-16,0}, {20,14,-16}, {20,14,16} };
static const uint8_t E_PRISM[9][2] = { {0,1}, {1,2}, {2,0}, {3,4}, {4,5}, {5,3}, {0,3}, {1,4}, {2,5} };
static const int8_t V_HEX[12][3] = { {-14,20,0}, {-14,10,17}, {-14,-10,17}, {-14,-20,0}, {-14,-10,-17}, {-14,10,-17}, {14,20,0}, {14,10,17}, {14,-10,17}, {14,-20,0}, {14,-10,-17}, {14,10,-17} };
static const uint8_t E_HEX[18][2] = { {0,1}, {1,2}, {2,3}, {3,4}, {4,5}, {5,0}, {6,7}, {7,8}, {8,9}, {9,10}, {10,11}, {11,6}, {0,6}, {1,7}, {2,8}, {3,9}, {4,10}, {5,11} };
static const int8_t V_ICO[12][3] = { {0,12,19}, {12,19,0}, {19,0,12}, {0,12,-19}, {12,-19,0}, {-19,0,12}, {0,-12,19}, {-12,19,0}, {19,0,-12}, {0,-12,-19}, {-12,-19,0}, {-19,0,-12} };
static const uint8_t E_ICO[30][2] = { {0,1}, {0,2}, {0,5}, {0,6}, {0,7}, {1,2}, {1,3}, {1,7}, {1,8}, {2,4}, {2,6}, {2,8}, {3,7}, {3,8}, {3,9}, {3,11}, {4,6}, {4,8}, {4,9}, {4,10}, {5,6}, {5,7}, {5,10}, {5,11}, {6,10}, {7,11}, {8,9}, {9,10}, {9,11}, {10,11} };
static const int8_t V_TESS[16][3] = { {-18,-18,-18}, {18,-18,-18}, {-18,18,-18}, {18,18,-18}, {-18,-18,18}, {18,-18,18}, {-18,18,18}, {18,18,18}, {-8,-8,-8}, {8,-8,-8}, {-8,8,-8}, {8,8,-8}, {-8,-8,8}, {8,-8,8}, {-8,8,8}, {8,8,8} };
static const uint8_t E_TESS[32][2] = { {0,1}, {1,3}, {3,2}, {2,0}, {4,5}, {5,7}, {7,6}, {6,4}, {0,4}, {1,5}, {2,6}, {3,7}, {8,9}, {9,11}, {11,10}, {10,8}, {12,13}, {13,15}, {15,14}, {14,12}, {8,12}, {9,13}, {10,14}, {11,15}, {0,8}, {1,9}, {2,10}, {3,11}, {4,12}, {5,13}, {6,14}, {7,15} };
static const Shape SHAPES[12] = {
    { V_CUBE, E_CUBE, 8, 12 }, { V_OCTA, E_OCTA, 6, 12 }, { V_PYRA, E_PYRA, 5, 8 }, { V_PRISM, E_PRISM, 6, 9 },
    { V_HEX, E_HEX, 12, 18 }, { V_ICO, E_ICO, 12, 30 }, { V_TESS, E_TESS, 16, 32 },
    { V_STAR, E_STAR, 8, 12 }, { V_RING, E_RING, 16, 24 }, { V_CUBOCTA, E_CUBOCTA, 12, 24 }, { V_SPIRE, E_SPIRE, 6, 12 },
    { V_CROSS, E_CROSS, 7, 18 } };
static const char *const ENEMY_NAMES[13] = { "ORIGIN CORE", "CUBE DRONE", "OCTA CORE", "PYRA SCOUT", "PRISM HUNTER", "HEX WARDEN",
                                             "ICOSA MIND", "TESSERACT", "STAR CORE", "RING WARDEN", "CUBOCTA", "SPIRE LORD", "CROSS GATE" };
// Stages 26 to 45: five new solids, then twins of everything, ending on twin tesseracts.
static const uint8_t LATE[20] = { 8, 9, 10, 11, 12, 0x81, 0x82, 0x83, 0x84, 0x85, 0x88, 0x89, 0x8A, 0x8B, 0x8C, 0x86, 0x87, 0x86, 0x87, 0x87 };
static const int8_t SINT[32] = { 0, 12, 24, 36, 45, 53, 59, 63, 64, 63, 59, 53, 45, 36, 24, 12, 0, -12, -24, -36, -45, -53, -59, -63, -64, -63, -59, -53, -45, -36, -24, -12 };   // sin * 64, 32 steps a turn
static uint16_t rot;                                            // the spin: 1/128 turn a frame (half the 1.3.0 rate), smooth
static int sin128(int a) { a &= 127; const int i = a >> 2, f = a & 3; return SINT[i] + (((SINT[(i + 1) & 31] - SINT[i]) * f) >> 2); }
static int16_t polyX[16], polyY[16], polyZ[16];                // projected corners: pixels, and depth

static inline int enemyCode() { return level <= 25 ? (level - 1) % 8 : LATE[level - 26]; }
static inline int enemyKind() { return enemyCode() & 127; }   // 0: the roaming line, 1..12: SHAPES[kind - 1]
static inline bool enemyTwin() { return (enemyCode() & 128) != 0; }   // two solids, one at each end of the line
static inline int coreSprite() { int k = enemyKind(); return k < 8 ? k : (k - 1) % 7 + 1; }

static void projectPoly(int body) {
    const Shape &sh = SHAPES[enemyKind() - 1];
    int ay = rot, ax = (rot * 3) >> 1;
    if (body) { ay += 64; ax += 36; }                               // the twin spins out of step
    int sa = sin128(ay), ca = sin128(ay + 32), sb = sin128(ax), cb = sin128(ax + 32);
    int cx = OX + ((qx[body] * 2) >> 4), cy = OY + ((qy[body] * 2) >> 4);
    for (int i = 0; i < sh.nv; i++) {
        int x = sh.v[i][0], y = sh.v[i][1], z = sh.v[i][2];
        int x1 = (x * ca + z * sa) >> 6, z1 = (z * ca - x * sa) >> 6;
        int y2 = (y * cb - z1 * sb) >> 6, z2 = (y * sb + z1 * cb) >> 6;
        int f = 256 * 80 / (80 + z2);                              // a little perspective
        polyX[i] = cx + x1 * f * 3 * bsc[body] / 32768;
        polyY[i] = cy + y2 * f * 3 * bsc[body] / 32768;
        polyZ[i] = z2;
    }
}

static bool polyHits() {                                    // an edge crosses the open line
    const Shape &sh = SHAPES[enemyKind() - 1];
    for (int e = 0; e < sh.ne; e++) {
        int a = sh.e[e][0], b = sh.e[e][1];
        const int n = (max(abs(polyX[b] - polyX[a]), abs(polyY[b] - polyY[a])) >> 1) + 1;   // a sample every cell (1.4.0: six an edge, which could step over the line)
        for (int t = 0; t <= n; t++) {
            int x = (polyX[a] + (polyX[b] - polyX[a]) * t / n - OX) >> 1, y = (polyY[a] + (polyY[b] - polyY[a]) * t / n - OY) >> 1;
            if (inb(x, y) && g[y][x] == TRAIL) return true;
        }
    }
    return false;
}

// The points (x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n), i = 0..n, n = max(|dx|, |dy|), C's division (it truncates):
// stepped with remainders instead of two divisions a point (1.4.3: the same pixels, faster on the board).
struct Walk {                                                   // (in a struct: the Arduino builder's prototypes break a free template)
    template <class Fn> static void run(int x0, int y0, int x1, int y1, Fn f) {
        const int ax = abs(x1 - x0), ay = abs(y1 - y0), sx = x1 < x0 ? -1 : 1, sy = y1 < y0 ? -1 : 1, n = ax > ay ? ax : ay;
        int x = x0, y = y0, rx = 0, ry = 0;
        for (int i = 0;;) {
            f(x, y);
            if (++i > n) break;
            if ((rx += ax) >= n) { rx -= n; x += sx; }
            if ((ry += ay) >= n) { ry -= n; y += sy; }
        }
    }
};

static void drawPoly() {
    const Shape &sh = SHAPES[enemyKind() - 1];
    const bool ice = puT[PU_FREEZE] != 0;
    for (int body = 0; body < (enemyTwin() ? 2 : 1); body++) {
        projectPoly(body);
        for (int pass = 0; pass < 3; pass++) {                    // a dark edge right and below every line, the far edges, the core, the near edges
            if (pass == 2) blit(SP_BOSS0 + coreSprite(), OX + ((qx[body] * 2) >> 4) - 6, OY + ((qy[body] * 2) >> 4) - 6);   // the 12x12 core, inside the cage
            for (int e = 0; e < sh.ne; e++) {
                int a = sh.e[e][0], b = sh.e[e][1];
                const bool near = polyZ[a] + polyZ[b] < 0;
                if (pass && near != (pass == 2)) continue;
                const uint8_t c = ice ? C_FASTL : near ? C_EDGE : C_Q0;   // near edges bright, far edges cyan
                if (pass) Walk::run(polyX[a], polyY[a], polyX[b], polyY[b], [c](int x, int y) { gfx_pixel(x, y, c); });
                else Walk::run(polyX[a], polyY[a], polyX[b], polyY[b], [](int x, int y) { gfx_pixel(x + 1, y, C_BG); gfx_pixel(x, y + 1, C_BG); });
            }
        }
        for (int i = 0; i < sh.nv; i++) gfx_fillRect(polyX[i] - 1, polyY[i] - 1, 2, 2, ice ? C_EDGE : C_TRAIL);
    }
}

static bool coreHits() {
    if (enemyKind()) {
        for (int body = 0; body < (enemyTwin() ? 2 : 1); body++) {
            projectPoly(body);
            if (polyHits()) return true;
            const int cx = qx[body] >> 4, cy = qy[body] >> 4;          // the core inside the cage kills too (1.4.2): what you see is what hits
            for (int y = cy - 2; y <= cy + 2; y++)
                for (int x = cx - 2; x <= cx + 2; x++)
                    if (inb(x, y) && g[y][x] == TRAIL) return true;
        }
        return false;
    }
    for (int s = 0; s <= 12; s++) {
        const int ax = lineEnd(0, qx), ay = lineEnd(0, qy), bx = lineEnd(1, qx), by = lineEnd(1, qy);
        int x = ((ax * (12 - s) + bx * s) / 12) >> 4, y = ((ay * (12 - s) + by * s) / 12) >> 4;
        if (!inb(x, y)) continue;
        if (g[y][x] == TRAIL) return true;
    }
    return false;
}

// ---- saving and the pause menu --------------------------------------------------------------
// One record: the best score and the game in progress (the stage, lives and score, saved at each
// stage start and by SAVE GAME; the stage itself starts fresh on CONTINUE). A game over clears it.
struct SaveData { int32_t hi, score, nextLife; uint8_t level, lives; };
static const uint32_t MAGIC = save::magic("CHIX");
static SaveData sv;
static bool saveDue, saveFlag, hasSave;
static uint8_t cardDue;                                     // frames to the save mirror's write on the SD card (Card.cpp putSave)
static uint8_t pauseSel, titleSel, prevBtn;
static const char *pauseNote;

static void saveProgress(bool inGame) {
    sv = { hiScore, score, nextLife, (uint8_t)level, (uint8_t)lives };
    saveFlag = inGame;
    saveDue = true;                                          // written after gfx_wait() in loop()
}

static void continueGame() {
    playSfx(S_START);
    won = false;
    level = sv.level; lives = sv.lives; score = sv.score; nextLife = sv.nextLife;
    newLevel();
    state = PLAY;
}

static void update() {
    frameNo++;
    uint8_t cur = (chgame.pressed(UP_BUTTON) ? 1 : 0) | (chgame.pressed(DOWN_BUTTON) ? 2 : 0) |
                  (chgame.pressed(A_BUTTON) ? 4 : 0) | (chgame.pressed(B_BUTTON) ? 8 : 0);
    uint8_t edge = cur & ~prevBtn;
    prevBtn = cur;
    if (state == PAUSED) {
        if (edge & 1) pauseSel = (pauseSel + 2) % 3;
        if (edge & 2) pauseSel = (pauseSel + 1) % 3;
        if (edge & 12) {
            if (pauseSel == 0) state = PLAY;
            else if (pauseSel == 1) {
                saveProgress(true);
                pauseNote = save::available() ? "GAME SAVED" : "SAVING IS OFF";
            } else { state = TITLE; titleSel = 0; resetField(); variant = 0; applyTheme(0); synth::music(0); }
        }
        return;
    }
    if (flash) flash--;
    updateParts();
    if (ringT) ringT--;
    if (popT) popT--;
    if (hitT) hitT--;
    if (shakeT) shakeT--;
    if (readyT && state == PLAY) readyT--;
    if (score > hiScore) hiScore = score;
    if (state == TITLE) {
        if (hasSave && (edge & 3)) titleSel ^= 1;
        if (edge & 4) { if (hasSave && titleSel == 0) continueGame(); else newGame(); }
        return;
    }
    if (state == OVER) {
        if (won && frameNo % 8 == 0) burst(rnd(110) + 8, rnd(90) + 20, 6, QCOL[rnd(4)]);
        if (timer > 0) timer--;
        else if (edge & 4) { resetField(); state = TITLE; variant = 0; applyTheme(0); synth::music(0); }
        return;
    }
    if (state == DYING) {
        if (--timer <= 0) {
            if (--lives <= 0) { state = OVER; timer = 30; playSfx(S_OVER); synth::music(-1); saveProgress(false); }
            else {
                int sx = startX, sy = startY;
                resetActors(false); px = startX = sx; py = startY = sy; snapPlayer(); state = PLAY; respawnT = 36; invT = 60; playSfx(S_ZAP);   // then a second and a half (60 frames at 40 fps) untouchable
                for (int i = 0; i < 4; i++)                          // a Spark back at its start must be on a border and not on top of the player
                    if (!isBorder(sp[i].x, sp[i].y) || abs(sp[i].x - px) + abs(sp[i].y - py) < 16) placeSpark(i);
            }
        }
        return;
    }
    if (state == CLEARED) {
        int e = CLEAR_TIME - timer;                                  // frames into the sequence
        if (e > 20 && e % 14 == 0) {                                 // fireworks
            int fx = 12 + rnd(104), fy = 24 + rnd(70);
            burst(fx, fy, 16, QCOL[rnd(4)]);                         // (no sound: effects would cut the music)
        }
        burst(rnd(120) + 4, rnd(100) + 14, 1, QCOL[rnd(4)]);
        if (--timer <= 0) {
            if (level >= STAGES) { won = true; state = OVER; timer = 120; playSfx(S_CLEAR); saveProgress(false); }
            else { level++; newLevel(); state = PLAY; saveProgress(true); }
        }
        return;
    }
    if (closing == 2) { closeClaim(); return; }
    if (closing) { closeFinish(); if (state != PLAY) return; }
    if (respawnT) { respawnT--; return; }                       // frozen while the circle closes in
    if (invT) invT--;
    bool a = chgame.pressed(A_BUTTON), b = chgame.pressed(B_BUTTON);
    int dx = (int)chgame.pressed(RIGHT_BUTTON) - (int)chgame.pressed(LEFT_BUTTON);
    int dy = (int)chgame.pressed(DOWN_BUTTON) - (int)chgame.pressed(UP_BUTTON);
    static bool horiz;                              // no diagonals: a second direction held is ignored
    if (dx && dy) { if (horiz) dy = 0; else dx = 0; }
    else if (dx) horiz = true;
    else if (dy) horiz = false;
    static int8_t bdx, bdy, ldx, ldy;               // a direction newly pressed between cells is kept 6 frames (bT), so a short tap is not lost
    if ((dx || dy) && (dx != ldx || dy != ldy)) { bdx = (int8_t)dx; bdy = (int8_t)dy; bT = 6; }
    else if (bT) bT--;
    ldx = (int8_t)dx; ldy = (int8_t)dy;
    if (banT) banT--;
    if (comboT && !--comboT) combo = 0;
    if ((theme == 0 || theme == 6) && !(rnd32() % 420)) flash = 4;           // lightning in the rainy cities
    int ox = px, oy = py;
    bool slowMove = !puT[PU_SPEED] && (drawing ? slowDraw : (b && !a));
    bool moving = prem != 0;
    for (int go = puT[PU_SPEED] ? 4 : slowMove ? 1 : 2 + (frameNo & 1); go > 0; ) {   // 2.5 on average (1.4.4: a quarter faster); quarter cells to cover this frame
        if (!prem) {                                    // on a cell: take the next one (a turn waits for the cell to be reached)
            int mx = dx, my = dy;
            if (!(mx || my) && bT) { mx = bdx; my = bdy; }  // a tap released before the cell was reached
            if (!(mx || my)) break;
            const int bx = px, by = py;
            movePlayer(mx, my, a, b);
            bT = 0;                                     // used (or blocked: dropped)
            if (state != PLAY || closing) return;       // (a closed shape: the rest of this frame is skipped, see closeTrail)
            if (px != bx + mx || py != by + my) { prem = 0; break; }   // blocked (or put back on a border after a claim)
            pdx = (int8_t)mx; pdy = (int8_t)my; prem = 4; moving = true;
        }
        const int t = go < prem ? go : prem;
        prem -= t; go -= t;
    }
    if (puT[PU_SPEED] && (frameNo & 1)) burst(OX + 2 * px, OY + 2 * py, 1, C_TRAIL);
    if (drawing && !(frameNo & 3)) burst(OX + 2 * px, OY + 2 * py, 1, slowDraw ? C_SLOWL : C_FASTL);   // a comet tail
    if (drawing && level >= 4) {                          // from stage 4 a fuse burns down the line if you stall
        if (moving || px != ox || py != oy) { fuse = -1; stallT = 0; }
        else {
            if (stallT < 255) stallT++;
            if (stallT > 90 && fuse < 0) { fuse = 0; playSfx(S_ZAP); }
        }
        if (fuse >= 0) {
            fuse += 1;
            if (fuse < trailLen && (frameNo & 1)) burst(OX + 2 * (trail[fuse] & 63), OY + 2 * (trail[fuse] >> 6), 1, C_TRAIL);
            if (fuse >= trailLen - 1 && !puT[PU_SHIELD]) { die(); return; }
            if (fuse >= trailLen - 1) fuse = -1;
        }
    } else fuse = -1;
    if (pu.life) {                                       // the pick-up: walk onto it, or close round it
        if (!(frameNo & 3)) pu.life--;
        if ((px == pu.x && py == pu.y) || claimed(pu.x, pu.y)) collect();
    } else if (++puWait > 400 + level * 12) { puWait = 0; spawnPickup(); }   // fewer pick-ups as stages go
    bool frozen = puT[PU_FREEZE] != 0, shield = puT[PU_SHIELD] != 0 || invT;
    bool tick = !frozen && (!puT[PU_SLOW] || (frameNo & 1));
    if (tick) { moveCore(); rot++; sizeBoss(); }
    bool sMove = false;                                 // the Sparks: a quarter cell a frame, half from stage 6, three quarters from 36
    if (tick && (sAcc += level >= 36 ? 3 : level >= 6 ? 2 : 1) >= 4) { sAcc -= 4; sMove = true; }
    for (int i = 0; i < sparkN(); i++) {
        if (sMove) moveSpark(i);
        if (puT[PU_LASER] && (sp[i].x == px || sp[i].y == py)) {   // the lasers sweep the row and column
            burst(OX + 2 * sp[i].x, OY + 2 * sp[i].y, 10, C_SPARK);
            anim(1, OX + 2 * sp[i].x, OY + 2 * sp[i].y);
            score += 500; playSfx(S_ZAP); placeSpark(i);
        }
        if (!shield && ((sp[i].x == px && sp[i].y == py) ||          // (or the two swapped cells this frame: they met)
                        (sMove && sp[i].x == ox && sp[i].y == oy && sh[i][0][0] == px && sh[i][0][1] == py))) { die(); return; }
    }
    if (drawing && !frozen && !shield && !puT[PU_GHOST] && coreHits()) die();
    if (frameNo & 1) for (int k = 0; k < PU_COUNT; k++) if (puT[k]) puT[k]--;   // (power-ups last two frames a count)
}

// The picture's animation, over the claimed ground only: rain, and flying cars with trails.
static void scenePlot(int px, int py, uint8_t light, uint8_t col) {
    if (px < 0 || px >= 120 || py < 0 || py >= 112) return;
    uint8_t v = g[py >> 1][px >> 1] & 3;
    if (v == FAST || v == SLOW) gfx_pixel(OX + px, OY + py, col);
}
static void drawScene() {
    static const uint8_t RAIN[3][3] = { { 8, 3, 2 }, { 5, 5, 3 }, { 3, 8, 3 } };       // three depths: drops, fall speed, streak (the far ones dim, the near ones bright)
    static const uint8_t RCOL[3] = { C_FRAME, C_FASTL, C_TEXT };
    for (int d = 0; d < 3; d++)
        for (int i = 0; i < RAIN[d][0]; i++) {
            int x = (i * 37 + d * 53 + (frameNo >> 1)) & 127, y = (frameNo * RAIN[d][1] + i * 29 + d * 41) & 127;
            for (int k = 0; k < RAIN[d][2]; k++) scenePlot(x - (k >> 1), y + k, d + 1, RCOL[d]);
        }
    const int f = (frameNo >> 3) & 1;                                   // the flying cars (the scene's two kinds: CHIX.DAT's CARA, CARB)
    blit(SP_CARA0 + f, OX + (frameNo * 2 + theme * 71) % 200 - 64, OY + 14 + (theme & 15) * 3, 1);
    blit(SP_CARB0 + f, OX + 160 - (frameNo * 3 + theme * 11) % 220, OY + 34 + (theme & 7) * 5, 3);
}


// Palette effects (docs/FX-SPEC.md): lightning, a fade-in on a new stage, the wet street shimmering, a neon sign flickering (index 15).
static uint8_t fxBolt = 12, fxFade = 32;                       // frames into a lightning strike (12: none) and into the fade-in (32: done)
static uint16_t fxGap = 200, fxR = 1, fxLast[8];
static void fxPlay() {
    static const uint8_t SC[8] = { 1, 2, 9, 10, 12, 13, 14, 15 };
    static const uint8_t BOLT[12] = { 0, 7, 2, 6, 4, 2, 1, 1, 0, 0, 0, 0 };
    static const uint32_t NEON = 0xB77BEDFBu;
    const uint8_t k = fxBolt < 12 ? BOLT[fxBolt] : 0;
    const bool calm = fxBolt >= 12 && fxFade >= 32;
    for (uint8_t n = 0; n < 8; n++) {
        const uint8_t i = SC[n];
        uint8_t c[3];
        for (uint8_t j = 0; j < 3; j++) {
            int v = base[i][j];
            if (calm && (i == 12 || i == 13)) {                    // up to half way to the lit neighbour, a 24-frame breath
                const uint8_t f = (frameNo + (i == 13 ? 8 : 0)) % 24, h = f < 12 ? f : 24 - f;
                v += ((base[i - 3][j] - v) * (h * 8 / 12)) >> 4;
            }
            if (fxFade < 32) v = (v * (5 + fxFade)) / 37;          // from a dim version up to the real colour
            if (i == 15 && !((NEON >> (frameNo & 31)) & 1)) v >>= 2;
            c[j] = (uint8_t)(v + (((255 - v) * k) >> 3));
        }
        const uint16_t rgb = gfx_rgb(c[0], c[1], c[2]);
        if (rgb != fxLast[n]) { fxLast[n] = rgb; gfx_setPaletteEntry(i, rgb); }
    }
    if (fxBolt < 12) fxBolt++;
    if (fxFade < 32) fxFade++;
    fxR = fxR * 25173u + 13849u;
    if (state == PLAY && fxBolt >= 12 && --fxGap == 0) { fxBolt = 0; fxGap = 150 + (fxR >> 8); }
}
static void fxScreen(int scr) {                                // the neon entries 7-9 rotate on the menu, game over, clear and win pictures
    const uint8_t sh = scr == 2 ? 1 : scr == 4 ? 4 : 3;
    for (uint8_t k = 0; k < 3; k++) { const uint8_t *c = base[7 + (k + (frameNo >> sh)) % 3]; gfx_setPaletteEntry(7 + k, gfx_rgb(c[0], c[1], c[2])); }
}
static void loadPalette(int want) {                            // (between gfx_wait() and gfx_flushAsync(): it reads the card)
    const bool scr = want >= 100;
    const uint8_t *p = card::block(scr ? (CARD_SCREEN + (want - 100) * CARD_SCREEN_STRIDE) / 512 + 16 : (CARD_SCENE + want * CARD_SCENE_STRIDE) / 512 + 14 + CARD_SPR_BLKS);
    if (!p) return;
    for (uint8_t i = 0; i < 16; i++) {
        const bool turn = !scr && (i == 1 || i == 2 || i == 4 || i == 9 || i == 10 || i == 12 || i == 13 || i == 14);   // the picture's own colours turn every ten stages
        for (uint8_t c = 0; c < 3; c++) base[i][c] = turn ? p[i * 3 + (c + variant) % 3] : p[i * 3 + c];
        gfx_setPaletteEntry(i, gfx_rgb(base[i][0], base[i][1], base[i][2]));
    }
    if (scr) memcpy(tr, p + 48, 5);
    else fxFade = 0;                                               // a new stage fades in from dark
    memset(fxLast, 0xFF, sizeof fxLast);
    palFor = (int8_t)want;
}


static const uint8_t HUE[12][3] = { {255,60,60}, {255,160,40}, {255,240,60}, {160,255,60}, {60,255,100}, {60,255,220},
                                    {60,180,255}, {100,100,255}, {180,80,255}, {255,70,230}, {255,70,140}, {255,90,90} };

// The sprites a frame draws come with the stage picture: the scene's sprite blocks follow its picture on the card, so the
// same multi-block read brings the ones this frame needs (1.4.3: one 12x12 sprite read on its own cost about 1.4 ms, and a
// frame drew 5 to 8 of them). Each frame planned (sprPlan()) is copied out of its block into floodQ, which only
// closeTrail() uses (in update(), never while drawing); a frame left out is read the old way, a block at a time.
static uint8_t cId[12], cAt[12], nC, cUsed;                      // the frames planned, where each is in floodQ (8 B units, 0xFF: not there)
enum { SPR_STREAM = 8 };                                        // sprite blocks read with the picture at most (the booms beyond are rare)
static int sprBlk(uint8_t id) { return SPR[id].off >> 9; }
static void sprWant(uint8_t id) { if (nC < 12) { cId[nC] = id; cAt[nC++] = 0xFF; } }
static int sprPlan() {                                            // the frames draw() will blit; the number of sprite blocks to read
    nC = cUsed = 0;
    const int f = (frameNo >> 3) & 1;
    sprWant(SP_CARA0 + f); sprWant(SP_CARB0 + f);
    sprWant(SP_BOSS0 + (enemyKind() ? coreSprite() : 0));
    if (pu.life) sprWant(SP_PU0 + pu.type);
    static const uint8_t NF[3] = { 6, 8, 6 }, FR[3] = { 2, 2, 3 }, ID[3] = { SP_BURST0, SP_BOOM0, SP_SPARKLE0 };
    for (uint8_t k = 0; k < 3; k++) if (an[k].t) sprWant(ID[k] + (NF[k] * FR[k] - an[k].t) / FR[k]);
    sprWant(SP_SPARK0 + ((frameNo >> 1) & 3));
    sprWant(drawing && (frameNo & 4) ? SP_SHIP1 : SP_SHIP0);
    sprWant(SP_HEART);
    if (comboT && combo >= 2) sprWant(SP_STAR0 + ((frameNo >> 2) & 3));
    int n = 0;
    for (uint8_t i = 0; i < nC; i++) { const int b = sprBlk(cId[i]); if (b < SPR_STREAM && b >= n) n = b + 1; }
    return n;
}
static void sprBlock(int j, const uint8_t *blk) {                // sprite block j has arrived: copy out the frames planned from it
    for (uint8_t i = 0; i < nC; i++) {
        const SprInfo &sp = SPR[cId[i]];
        if ((sp.off >> 9) != j) continue;
        const int len = (((sp.w + 1) >> 1) * sp.h + 7) >> 3;
        if (cUsed + len > (int)sizeof floodQ / 8) continue;
        memcpy((uint8_t *)floodQ + cUsed * 8, blk + (sp.off & 511), len * 8);
        cAt[i] = (uint8_t)cUsed;
        cUsed += len;
    }
}

// What a cell shows, looked up from its grid byte (type, MARK, BORD): a colour byte (both pixels), or one of these.
enum : uint8_t { L_PIC = 1, L_SLOW = 2, L_BORD = 3 };          // (never a colour byte: those are v * 17)
struct CellCtx { uint8_t k; bool cl; int wipe; uint8_t lut[64]; };
// One cell row: two frame rows from r0 (pic: the picture's two rows, or none). In SRAM: flash has 3 wait states and no
// cache, and this runs for every cell every frame (1.4.3). A leaf: a call from SRAM would detour through flash.
RAMFUNC(cellrow) static void cellRow(uint8_t *r0, const uint8_t *gr, const uint8_t *pic, const uint8_t *lut, int ys, int yd) {
    uint8_t *r1 = r0 + GFX_FB_STRIDE;
    for (int x = 0; x < W; x++) {
        const uint8_t e = lut[gr[x] & 63];
        if (e > L_BORD || !e) { r0[x] = r1[x] = e; continue; }
        if (e == L_BORD) { r0[x] = r1[x] = ((x + ys) & 15) ? C_EDGE * 17 : C_TRAIL * 17; continue; }   // a shimmer runs round the border
        if (!pic) { r0[x] = r1[x] = C_BG * 17; continue; }
        uint8_t a = pic[x], b = pic[60 + x];
        if (e == L_SLOW && ((x + yd) & 63) == 0) a = (a & 0x0F) | (C_TRAIL << 4), b = (b & 0xF0) | C_TRAIL;   // a slow claim: a thin gold sheen sweeps across it (1.4.1: scattered twinkles)
        r0[x] = a; r1[x] = b;
    }
}
static void cellRows(const uint8_t *blk, void *ctx) {            // the four cell rows of picture block k (8 picture rows of 60 B)
    CellCtx &cc = *(CellCtx *)ctx;
    const int k = cc.k++;
    if (k >= 14) { if (blk) sprBlock(k - 14, blk); return; }    // (a sprite block)
    const int sh = frameNo >> 1;
    for (int y = 4 * k; y < 4 * k + 4; y++) {
        if (cc.cl) cc.lut[EMPTY] = cc.lut[EMPTY | MARK] = y == cc.wipe ? C_EDGE * 17 : y < cc.wipe ? cc.lut[FAST] : C_BG * 17;   // the clear's wipe
        cellRow(gfx_fb + (OY + 2 * y) * GFX_FB_STRIDE + OX / 2, g[y], blk ? blk + (y & 3) * 120 : nullptr, cc.lut, y + sh, y - sh);
    }
}

static void drawCells() {
    if (level > 25 && state != TITLE) { const uint8_t *hc = HUE[(frameNo >> 2) % 12]; gfx_setPaletteEntry(7, gfx_rgb(hc[0], hc[1], hc[2])); }   // the lights cycle
    const bool cl = state == CLEARED;
    CellCtx cc;                                                       // (wipe: the scan that fills what is left)
    cc.k = 0; cc.cl = cl; cc.wipe = cl ? (CLEAR_TIME - timer) * H / 45 : 0;
    for (int v = 0; v < 64; v++) {                                    // (1.4.3: a table instead of a chain of tests for each cell)
        const uint8_t c = v & 3;
        cc.lut[v] = c == EMPTY ? C_BG * 17 : c == TRAIL ? ((frameNo & 2) ? C_TRAIL : C_EDGE) * 17 : (v & BORD) ? L_BORD :
                    (flash & 2) ? C_EDGE * 17 : c == SLOW ? L_SLOW : L_PIC;
    }
    // The whole stage picture in one multi-block read by DMA (1.4.2: about 3 ms; fourteen single reads took about 20), each
    // block drawn while the next arrives. The second buffer is the top 8 rows of the frame, blank again afterwards (the HUD comes later).
    // (Not in a claim flash's white frames, which show no picture: the frame that floods a closed shape is one.)
    // The sprite blocks this frame needs come in the same read (sprPlan()); a white frame reads only those.
    const int ns = sprPlan(), first = (flash & 2) ? 14 : 0;
    cc.k = (uint8_t)first;
    if (card::stream((CARD_SCENE + theme * CARD_SCENE_STRIDE) / 512 + first, 14 + ns - first, gfx_fb, cellRows, &cc)) memset(gfx_fb, C_BG * 17, 8 * GFX_FB_STRIDE);
    if (first) cc.k = 0;
    while (cc.k < 14) cellRows(nullptr, &cc);                         // (a white frame, or the card went: the rest without the picture)
    int x0 = OX - 2, y0 = OY - 2, w = 2 * W + 4, h = 2 * H + 4;       // the frame round the field
    const uint8_t fc = synth::beat() ? C_Q0 : C_FRAME;                 // it lights up on every kick
    gfx_fillRect(x0, y0, w, 1, fc); gfx_fillRect(x0, y0 + h - 1, w, 1, fc);
    gfx_fillRect(x0, y0, 1, h, fc); gfx_fillRect(x0 + w - 1, y0, 1, h, fc);
}

// Sprites and animation frames are read from the card (remapped to the scene's palette; 15 = transparent), 4 bits a pixel.
// mode 1: only over claimed ground (rain, cars).
// One sprite row onto a frame row (flip: mirrored; gr: the grid row under it, drawn only over claimed cells). In SRAM, a leaf (1.4.3).
RAMFUNC(blitrow) static void blitRow(uint8_t *row, const uint8_t *src, int x, int w, bool flip, const uint8_t *gr) {
    for (int dx = 0; dx < w; dx++) {
        const int sx = flip ? w - 1 - dx : dx, xx = x + dx;
        const uint8_t v = (src[sx >> 1] >> ((sx & 1) * 4)) & 15;
        if (v == 15 || (unsigned)xx >= 128) continue;
        if (gr && (xx < OX || (xx - OX) >> 1 >= W || (uint8_t)((gr[(xx - OX) >> 1] & 3) - 1) >= 2)) continue;
        uint8_t *d = row + (xx >> 1);
        *d = (xx & 1) ? (uint8_t)((*d & 0x0F) | (v << 4)) : (uint8_t)((*d & 0xF0) | v);
    }
}

static const uint8_t *sprBits(uint8_t id) {                       // a sprite's pixels (planned with the frame's read, else its own block)
    const uint8_t *b = nullptr;
    for (uint8_t i = 0; i < nC; i++) if (cId[i] == id && cAt[i] != 0xFF) { b = (const uint8_t *)floodQ + cAt[i] * 8; break; }
    if (!b) {
        b = card::block((CARD_SCENE + theme * CARD_SCENE_STRIDE) / 512 + 14 + sprBlk(id));
        if (b) b += SPR[id].off & 511;
    }
    return b;
}

// A 12x12 sprite turned by ang eighths of a turn clockwise (0 = as drawn, pointing up), about its centre (cx, cy): integer inverse mapping.
static void blitRot(uint8_t id, int cx, int cy, uint8_t ang) {
    static const int8_t CS[8] = { 64, 45, 0, -45, -64, -45, 0, 45 }, SN[8] = { 0, 45, 64, 45, 0, -45, -64, -45 };
    const uint8_t *b = sprBits(id);
    if (!b) return;
    const int c = CS[ang & 7], s = SN[ang & 7];
    for (int j = 0; j < 16; j++) {
        const int yy = cy - 7 + j, Y = 2 * j - 15;
        if ((unsigned)yy >= 128) continue;
        for (int i = 0; i < 16; i++) {
            const int xx = cx - 7 + i, X = 2 * i - 15;
            const int u = (X * c + Y * s + 768) >> 7, v = (Y * c - X * s + 768) >> 7;
            if ((unsigned)u >= 12 || (unsigned)v >= 12 || (unsigned)xx >= 128) continue;
            const uint8_t p = (b[v * 6 + (u >> 1)] >> ((u & 1) * 4)) & 15;
            if (p == 15) continue;
            uint8_t *d = gfx_fb + yy * GFX_FB_STRIDE + (xx >> 1);
            *d = (xx & 1) ? (uint8_t)((*d & 0x0F) | (p << 4)) : (uint8_t)((*d & 0xF0) | p);
        }
    }
}

static void blit(uint8_t id, int x, int y, uint8_t mode, int ymax) {
    const SprInfo &sp = SPR[id];
    const uint8_t *b = sprBits(id);
    if (!b) return;
    const int rb = (sp.w + 1) >> 1;
    for (int dy = 0; dy < sp.h; dy++) {
        int yy = y + dy;
        if (yy < 0 || yy >= ymax) continue;
        const int cy = (yy - OY) >> 1;
        if ((mode & 1) && (yy < OY || cy >= H)) continue;              // (over claimed ground only: none on this row)
        blitRow(gfx_fb + yy * GFX_FB_STRIDE, b + dy * rb, x, sp.w, mode & 2, (mode & 1) ? g[cy] : nullptr);
    }
}

static void panelBox(int x, int y, int w, int h, uint8_t edge, uint8_t fill = C_BG) {
    gfx_fillRect(x, y, w, h, edge);
    gfx_fillRect(x + 1, y + 1, w - 2, h - 2, fill);
}

static void drawSpark(int n) {
    for (int k = 2; k >= 0; k--) {
        int cx = OX + 2 * sh[n][k][0], cy = OY + 2 * sh[n][k][1];
        gfx_fillRect(cx, cy, 2, 2, k == 2 ? C_FRAME : C_GLOW);
    }
    // Drawn on its way from its cell to the next one (sAcc quarters of it): it reaches a cell on screen when the logic
    // enters it, so a hit shows where it happens (1.4.0 drew it up to a whole cell behind).
    const int k = sparkNext(n), off = k >= 0 ? sAcc >> 1 : 0;
    const int sx = OX + 2 * sp[n].x + (k >= 0 ? SD4[k][0] * off : 0), sy = OY + 2 * sp[n].y + (k >= 0 ? SD4[k][1] * off : 0);
#ifdef CHIX_TRACE
    if (!n) fprintf(stderr, "SPARK %d %d %d %d\n", frameNo, sx, sy, (int)state);
#endif
    blit(SP_SPARK0 + ((frameNo >> 1) & 3), sx - 5, sy - 5);
}

// The player: a diamond that pulses while drawing.
static int shipX() { return OX + 2 * px - pdx * prem / 2; }    // the drawn ship: one pixel a frame behind the logic's cell, at most
static int shipY() { return OY + 2 * py - pdy * prem / 2; }
static void drawPlayer() {
    int cx = shipX(), cy = shipY();
#ifdef CHIX_TRACE
    fprintf(stderr, "SHIP %d %d %d %d\n", frameNo, cx, cy, (int)state);
#endif
    // The ship turns to face the way it goes: an eighth of a turn a frame by the short way (a right angle takes two frames, a U-turn four).
    static uint8_t ang;
    const uint8_t want = pdx ? (pdx > 0 ? 2 : 6) : pdy ? (pdy > 0 ? 4 : 0) : ang;
    if (state != PLAY) ang = want;
    else if (ang != want) ang = (uint8_t)((((want - ang) & 7) <= 4 ? ang + 1 : ang + 7) & 7);
    if (invT && state == PLAY && (frameNo & 2)) return;       // blinks while invincible
    blitRot(drawing && (frameNo & 4) ? SP_SHIP1 : SP_SHIP0, cx + 1, cy + 1, ang);
}

struct Amb { int8_t sy, dx; uint8_t col, len; };                  // fall speed, drift, colour, streak length
static const Amb AMB[10] = { { 5, -1, C_Q0, 3 }, { -1, 0, C_GLOW, 1 }, { -2, 1, C_SLOW, 1 }, { 1, 0, C_EDGE, 1 }, { 0, 0, C_FASTL, 1 },
                             { 1, 1, C_SLOWL, 1 }, { 5, -1, C_Q0, 3 }, { -1, 1, C_Q1, 1 }, { 0, 0, C_TRAIL, 1 }, { -3, 0, C_EDGE, 2 } };
static void drawAmbient() {                                      // rain, smoke, embers, snow, stars, dust, spores, sparks
    const Amb &a = AMB[theme];
    for (int i = 0; i < 18; i++) {
        int y = ((frameNo * a.sy + i * 53) % 112 + 112) % 112, x = ((i * 71 + frameNo * a.dx) % 120 + 120) % 120;
        if (a.sy == 0 && !((frameNo + i * 7) & 8)) continue;       // stars twinkle
        for (int k = 0; k < a.len; k++)
            if (y + k < 112 && g[(y + k) >> 1][x >> 1] == EMPTY) gfx_pixel(OX + x, OY + y + k, a.col);
    }
}

static void cellRect(int x, int y, uint8_t c) { gfx_fillRect(OX + 2 * x - 1, OY + 2 * y - 1, 4, 4, c); }

static void drawLine(int x0, int y0, int x1, int y1, uint8_t c) {   // (field pixels)
    Walk::run(OX + x0, OY + y0, OX + x1, OY + y1, [c](int x, int y) { gfx_pixel(x, y, c); });
}

// The text of the full-screen states, in the colours of that picture's palette (tr: light, accent, gold, dim, dark).
static void drawScreenText(int scr) {
    char s[40];
    const uint8_t light = tr[0], acc = tr[1], gold = tr[2], dim = tr[3], dark = tr[4];
    if (scr == 0) {                                                   // the title
        const char *tag = "TERRITORY ARCADE";
        gfx_text((128 - gfx_textWidth(tag)) / 2, 56, tag, gold);
        if (hiScore) { char h[24]; snprintf(h, sizeof h, "HI %d", hiScore); gfx_text((128 - gfx_textWidth(h)) / 2, 64, h, light); }
        panelBox(10, 72, 108, 34, acc, dark);
        if (hasSave) {                                               // CONTINUE or NEW GAME, in the same panel (1.4.3: a second panel below hid the street)
            snprintf(s, sizeof s, "CONTINUE  LV %d", sv.level);
            gfx_text(24, 76, s, titleSel == 0 ? light : dim);
            gfx_text(24, 85, "NEW GAME", titleSel == 1 ? light : dim);
            gfx_text(14, titleSel ? 85 : 76, ">", gold);
            gfx_text(16, 95, "A FAST B SLOW X2", acc);
        } else {
            gfx_text(16, 76, "A  DRAW FAST", acc);
            gfx_text(16, 85, "B  DRAW SLOW  X2", gold);
            gfx_text(16, 94, "CLAIM THE FIELD", light);
            if (frameNo & 16) { panelBox(34, 108, 60, 14, acc, dark); gfx_text((128 - gfx_textWidth("PRESS A")) / 2, 112, "PRESS A", gold); }
        }
    } else if (scr == 1) {                                            // the pause menu
        static const char *const LINES[3] = { "RESUME", "SAVE GAME", "RETURN TO TITLE" };
        panelBox(8, 37, 112, 62, acc, dark);
        gfx_text((128 - gfx_textWidth("PAUSED")) / 2, 42, "PAUSED", gold);
        for (int i = 0; i < 3; i++) {
            int y = 54 + i * 10;
            if (i == pauseSel) { gfx_fillRect(12, y - 2, 104, 10, dim); gfx_text(16, y, ">", gold); }
            gfx_text(24, y, LINES[i], light);
        }
        if (pauseNote) gfx_text((128 - gfx_textWidth(pauseNote)) / 2, 87, pauseNote, acc);
    } else if (scr == 2) {                                            // the level-clear panel
        int e = CLEAR_TIME - timer;
        int open = min(44, max(0, (e - 50) * 4));
        if (timer < 10) open = min(open, timer * 4);
        if (open > 0) {
            int x = 8, y = 56 - open / 2, w = 112;
            panelBox(x - 1, y - 1, w + 2, open + 2, acc, dark);
            if (open >= 44) {
                snprintf(s, sizeof s, "LEVEL %d CLEAR!", level);
                gfx_text(x + 10, y + 5, s, gold);
                snprintf(s, sizeof s, "AREA %d%%", areaPct);
                gfx_text(x + 10, y + 17, s, light);
                int shown = clearBonus * min(max(e - 70, 0), 40) / 40;
                snprintf(s, sizeof s, "BONUS +%d", shown);
                gfx_text(x + 10, y + 29, s, shown == clearBonus ? gold : light);
            }
        }
    } else {                                                          // game over, or the win
        panelBox(24, 50, 80, 26, acc, dark);
        gfx_text((128 - gfx_textWidth(won ? "YOU WIN!" : "GAME OVER")) / 2, 54, won ? "YOU WIN!" : "GAME OVER", gold);
        snprintf(s, sizeof s, "HI %d", hiScore);
        gfx_text((128 - gfx_textWidth(s)) / 2, 65, s, light);
    }
}

static void scrBlock(const uint8_t *blk, void *ctx) {           // a full-screen picture's block k: frame rows 8k..8k+7
    uint8_t *d = gfx_fb + (*(uint8_t *)ctx)++ * 512;
    if (d != blk) memcpy(d, blk, 512);                              // (the odd blocks arrive in the last one's place)
}

static void draw() {
    gfx_clear(C_BG);
    // The full-screen states show a picture from the card in its own palette, with the text on top in that palette's colours.
    const int scr = state == TITLE ? 0 : state == PAUSED ? 1 : state == OVER ? (won ? 4 : 3) : (state == CLEARED && CLEAR_TIME - timer >= 50) ? 2 : -1;
    const int want = scr >= 0 ? 100 + scr : theme;
    if (palFor != want) loadPalette(want);
    char s[40];
    if (scr >= 0) {
        if (scr) fxScreen(scr);
        uint8_t k = 0;                                              // its 16 blocks are the frame's 128 rows: one multi-block read by DMA
        card::stream((CARD_SCREEN + scr * CARD_SCREEN_STRIDE) / 512, 16, gfx_fb + 15 * 512, scrBlock, &k);   // (1.4.2: 16 single reads took ~25 ms)
        drawScreenText(scr);
        for (int i = 0; i < NPART; i++)
            if (parts[i].life) gfx_pixel(parts[i].x >> 3, parts[i].y >> 3, parts[i].life < 5 ? tr[3] : parts[i].col);
        return;
    }
    fxPlay();
    drawCells();
    DPROBE(8);
    drawScene();
    drawAmbient();
    DPROBE(9);
    if ((state != DYING || (timer & 4)) && enemyKind()) drawPoly();
    else if (state != DYING || (timer & 4)) {
        for (int i = Q_HIST - 1; i >= 0; i--) {
            QLine l = qh[(qhead + Q_HIST - i) % Q_HIST];
            if (!i) {                                                   // the line itself: where it is now, on a dark edge
                l = { (int16_t)(lineEnd(0, qx) >> 3), (int16_t)(lineEnd(0, qy) >> 3), (int16_t)(lineEnd(1, qx) >> 3), (int16_t)(lineEnd(1, qy) >> 3) };
                drawLine(l.x1 + 1, l.y1, l.x2 + 1, l.y2, C_BG); drawLine(l.x1, l.y1 + 1, l.x2, l.y2 + 1, C_BG);
            }
            drawLine(l.x1, l.y1, l.x2, l.y2, puT[PU_FREEZE] ? (i ? C_FASTL : C_EDGE) : (i ? QCOL[i & 3] : C_TRAIL));
        }
        blit(SP_BOSS0, OX + ((qx[0] + qx[1]) >> 4) - 6, OY + ((qy[0] + qy[1]) >> 4) - 6);            // its glowing heart
    }
    if (pu.life && (pu.life > 23 || (frameNo & 4))) {               // (blinks for its last 3 s)                // the pick-up, bobbing
        const PuInfo &in = PUI[pu.type];
        int bx = OX + 2 * pu.x - 5, by = OY + 2 * pu.y - 5 + ((frameNo >> 3) & 1);
        blit(SP_PU0 + pu.type, bx, by);
        if (frameNo & 4) {                                            // corner glints
            gfx_pixel(bx - 1, by - 1, in.col); gfx_pixel(bx + 12, by - 1, in.col);
            gfx_pixel(bx - 1, by + 12, in.col); gfx_pixel(bx + 12, by + 12, in.col);
        }
    }
    for (uint8_t k = 0; k < 3; k++)                                   // the one-shot animations
        if (an[k].t) {
            static const uint8_t NF[3] = { 6, 8, 6 }, FR[3] = { 2, 2, 3 }, HW[3] = { 8, 12, 6 }, ID[3] = { SP_BURST0, SP_BOOM0, SP_SPARKLE0 };
            const uint8_t f = (uint8_t)((NF[k] * FR[k] - an[k].t) / FR[k]);
            blit(ID[k] + f, an[k].x - HW[k], an[k].y - HW[k]);
            an[k].t--;
        }
    if (puT[PU_LASER]) {                                              // the beams
        uint8_t c = (frameNo & 1) ? C_PLAYER : C_EDGE;
        gfx_fillRect(OX, shipY(), 2 * W, 2, c);
        gfx_fillRect(shipX(), OY, 2, 2 * H, c);
    }
    if (fuse >= 0 && fuse < trailLen) {                              // the fuse's spark
        int fx = OX + 2 * (trail[fuse] & 63), fy = OY + 2 * (trail[fuse] >> 6);
        gfx_fillRect(fx - 1, fy - 1, 4, 4, (frameNo & 2) ? C_EDGE : C_SPARK);
    }
    DPROBE(10);
    for (int i = 0; i < sparkN(); i++) drawSpark(i);
    if (state != DYING || (timer & 2)) drawPlayer();
    if (puT[PU_SHIELD] && (puT[PU_SHIELD] > 40 || (frameNo & 2))) {    // the shield ring
        int cx = shipX(), cy = shipY();
        gfx_fillRect(cx - 4, cy - 3, 1, 8, C_Q0); gfx_fillRect(cx + 5, cy - 3, 1, 8, C_Q0);
        gfx_fillRect(cx - 3, cy - 4, 8, 1, C_Q0); gfx_fillRect(cx - 3, cy + 5, 8, 1, C_Q0);
    }
    DPROBE(1);
    for (int i = 0; i < NPART; i++)
        if (parts[i].life) gfx_pixel(parts[i].x >> 3, parts[i].y >> 3, parts[i].life < 5 ? C_FRAME : parts[i].col);
    DPROBE(2);
    snprintf(s, sizeof s, "%d", score);
    gfx_text(2, 3, s, C_TEXT);
    snprintf(s, sizeof s, "%d%%", areaPct);
    gfx_text(46, 3, s, C_TEXT);
    gfx_fillRect(OX, 11, 2 * W, 1, C_FRAME);                       // progress to the 75% target
    gfx_fillRect(OX, 11, 2 * W * areaPct / 100, 1, areaPct >= tgt() ? C_Q1 : C_FAST);
    gfx_fillRect(OX + 2 * W * tgt() / 100, 10, 1, 3, C_EDGE);
    blit(SP_HEART, 96, 0, 0, 12);                                     // lives: a heart (in the fixed colours) and a count
    snprintf(s, sizeof s, "x%d", lives);
    gfx_text(109, 3, s, C_TEXT);
    snprintf(s, sizeof s, "L%d", level);
    gfx_text(70, 3, s, C_TRAIL);
    DPROBE(3);
    if (respawnT && state == PLAY) {                                  // a circle shrinks onto the player
        int cx = OX + 2 * px + 1, cy = OY + 2 * py + 1, r = respawnT * 3 + 5;
        uint8_t c = (respawnT & 2) ? C_EDGE : C_PLAYER;
        for (int k = 0; k < 32; k++) {
            int x0 = cx + SINT[(k + 8) & 31] * r / 64, y0 = cy + SINT[k] * r / 64;
            int x1 = cx + SINT[(k + 9) & 31] * r / 64, y1 = cy + SINT[(k + 1) & 31] * r / 64;
            Walk::run(x0, y0, x1, y1, [c](int x, int y) { gfx_pixel(x, y, c); });
        }
    }
    if (ringT) {                                                      // the shockwave
        int r = (14 - ringT) * 4 + 2;
        uint8_t c = ringT < 5 ? C_FRAME : ringCol;
        for (int k = 0; k < 24; k++) gfx_pixel(ringX + COS24[k] * r / 64, ringY + COS24[(k + 18) % 24] * r / 64, c);
    }
    if (comboT && combo >= 2 && (comboT > 30 || (frameNo & 2))) {                            // the combo
        snprintf(s, sizeof s, "COMBO X%d", combo);
        gfx_text(2, 105, s, C_TRAIL);
        blit(SP_STAR0 + ((frameNo >> 2) & 3), 4 + gfx_textWidth(s), 101);
    }
    if (popT) {                                                       // the points, floating up
        const char *word = popVal >= 4000 ? "AWESOME " : popVal >= 1500 ? "GREAT " : popVal >= 600 ? "NICE " : "";
        snprintf(s, sizeof s, "%s+%d", word, popVal);
        const int tx = constrain(popX - 8, 2, 128 - gfx_textWidth(s) - 2), ty = max(OY + 2, popY - 6 - (36 - popT) / 3);   // (kept below the HUD)
        gfx_text(tx + 1, ty + 1, s, C_BG);                            // on a dark shadow, so it reads over the picture
        gfx_text(tx, ty, s, (popT < 10 && (popT & 1)) ? C_FRAME : C_TRAIL);
    }
    if (hitT) {                                                       // a red frame when you are hit
        gfx_fillRect(0, 0, 128, 3, C_PLAYER); gfx_fillRect(0, 125, 128, 3, C_PLAYER);
        gfx_fillRect(0, 0, 3, 128, C_PLAYER); gfx_fillRect(125, 0, 3, 128, C_PLAYER);
    }
    DPROBE(4);
    if (readyT && state == PLAY) {                                    // the level slides in and out
        snprintf(s, sizeof s, "LEVEL %d", level);
        int w = gfx_textWidthScaled(s, 2);
        int off = readyT > 35 ? (readyT - 35) * 12 : readyT < 10 ? -(10 - readyT) * 14 : 0;
        gfx_fillRect(0, 46, 128, 32, C_BG);
        gfx_fillRect(0, 45, 128, 1, QCOL[(frameNo >> 2) & 3]); gfx_fillRect(0, 78, 128, 1, QCOL[(frameNo >> 2) & 3]);
        gfx_textScaled((128 - w) / 2 + off, 50, s, C_EDGE, 2);
        char nb[24];
        snprintf(nb, sizeof nb, "%s%s", enemyTwin() ? "TWIN " : "", ENEMY_NAMES[enemyKind()]);
        const char *nm = nb;
        gfx_text((128 - gfx_textWidth(nm)) / 2 + off, 68, nm, C_Q0);
    }
    if (banT && state == PLAY) {                                      // the power-up text box
        int w = max(gfx_textWidth(banner->name), gfx_textWidth(banner->desc)) + 14;
        int open = min(26, (75 - banT) * 5);
        if (banT < 8) open = min(open, banT * 3);
        int x = (128 - w) / 2, y = 56 - open / 2;
        gfx_fillRect(x - 1, y - 1, w + 2, open + 2, banner->col);
        gfx_fillRect(x, y, w, open, C_BG);
        if (open >= 26) {
            gfx_text(x + 7, y + 4, banner->name, banner->col);
            gfx_text(x + 7, y + 15, banner->desc, C_TEXT);
        }
    }
    DPROBE(5);
    if (shakeT) {                                                     // the screen shakes: two rows down or up
        // (1.4.3: a word at a time; the library's memmove took up to 11 ms a frame on the board, byte by byte)
        uint32_t *f = (uint32_t *)gfx_fb;
        enum { O = 2 * GFX_FB_STRIDE / 4, N = (128 - 2) * GFX_FB_STRIDE / 4 };
        if (shakeT & 1) for (int i = N - 1; i >= 0; i--) f[i + O] = f[i];
        else for (int i = 0; i < N; i++) f[i] = f[i + O];
    }
}

#ifdef CHSIM
void sim_sync();
void sim_advance(uint32_t us);
void sim_waitInput();
#endif

// The flash save first; with none, the SD card's mirror (the DAT's last two blocks) gives it back (a save lost with the flash).
static void loadSave() {
    SaveData d;
    uint8_t flag = 0;
    hasSave = false;
    if (save::load(MAGIC, 1, d, &flag)) {
        hiScore = d.hi;
        if (flag == 1) { hasSave = true; sv = d; }
    } else {
        uint8_t m[sizeof(SaveData) + 1];
        if (card::getSave(m, sizeof m)) {
            memcpy(&d, m, sizeof d);
            hiScore = d.hi;
            if (m[sizeof d] == 1) { hasSave = true; sv = d; }
            saveFlag = m[sizeof d] == 1; sv = d; saveDue = true;   // and back into the flash
        }
    }
}

#if CHGAME_DEBUG
static bool chixHook(char cmd, const char *a) {
    switch (cmd) {
    case 'W': { int l = (int)dbg::parseNum(a, 10), v = (int)dbg::parseNum(a, 10); level = l; lives = v; score = (int)dbg::parseNum(a, 10); saveProgress(true); return true; }   // W level lives score
    case 'O': saveProgress(false); return true;
    case 'V': loadSave(); state = TITLE; titleSel = 0; return true;                    // power cycle (simsave)
    case 'A': { char b[96]; snprintf(b, sizeof b, "STATE save=%d hi=%ld level=%d lives=%d score=%ld\n", hasSave, (long)hiScore, hasSave ? sv.level : -1, hasSave ? sv.lives : -1, (long)(hasSave ? sv.score : -1)); dbg::print(b); return true; }
    }
    return false;
}
#endif

void setup() {
    chgame.boot();
#if CHGAME_DEBUG
    dbg::begin("CHIX 1.5.5");
#endif
    gfx_begin(GFX_DIV2, GFX_12BPP);
    const uint16_t pal[16] = {
        gfx_rgb(0, 0, 0), gfx_rgb(30, 70, 230), gfx_rgb(230, 130, 20), gfx_rgb(255, 255, 80),
        gfx_rgb(255, 255, 255), gfx_rgb(255, 50, 50), gfx_rgb(255, 60, 255),
        gfx_rgb(0, 255, 255), gfx_rgb(0, 255, 100), gfx_rgb(130, 175, 255), gfx_rgb(255, 205, 120),
        gfx_rgb(220, 220, 220), gfx_rgb(15, 35, 115), gfx_rgb(115, 65, 10), gfx_rgb(90, 90, 90), gfx_rgb(150, 30, 150) };
    gfx_setPalette(pal, 16);
    card::open();
    applyTheme(0);
    synth::begin();
    synth::music(0);
    chgame.setFrameRate(40);
    loadSave();
#if CHGAME_DEBUG
    dbg::hook = chixHook;
#endif
    rng ^= millis();
    state = TITLE;
    resetField();
}

void loop() {
    static bool startPrev;
    bool st = chgame.pressed(START_BUTTON);                     // START pressed in play: the pause menu
    if (st && !startPrev) {
        if (state == PLAY) { state = PAUSED; pauseSel = 0; pauseNote = nullptr; bT = 0; }
        else if (state == PAUSED) state = PLAY;
    }
    startPrev = st;
    dbg::markRenderStart();
    DPROBE(0);
    if (card::ok()) update();                                   // every frame (the pace is in the moves themselves: see prem)
    DPROBE(6);
    gfx_wait();
    DPROBE(7);
    card::frame();
    if (!card::ok() && (frameNo++ % 60) == 2) card::open();
    if (saveDue) {
        saveDue = false;
        save::store(MAGIC, 1, sv, saveFlag ? 1 : 0);
        hasSave = saveFlag && save::available();
        if (hasSave) titleSel = 0;
        cardDue = 20;
    }
    if (cardDue && (state == TITLE || state == OVER || state == PAUSED) && !--cardDue) {   // (1.5.1: only on a calm screen; the write hitched level starts on the MiSTer)                                 // 20 frames after the last change: the SD card's copy (not in the same frame as the flash write)
        uint8_t m[sizeof sv + 1];
        memcpy(m, &sv, sizeof sv);
        m[sizeof sv] = saveFlag ? 1 : 0;
        card::putSave(m, sizeof m);
    }
    if (card::ok()) draw();
    else {                                                       // no card, or another build's: say so (it is tried again each second)
        gfx_clear(C_BG);
        gfx_text((128 - gfx_textWidth("NEED CHIX.DAT")) / 2, 52, "NEED CHIX.DAT", C_TRAIL);
        gfx_text((128 - gfx_textWidth("ON THE SD CARD")) / 2, 66, "ON THE SD CARD", C_TEXT);
    }
    dbg::markRenderEnd();
    DPROBE(11);
    gfx_flushAsync();
#ifdef CHIX_FLUSHPROF
    gfx_wait();
    DPROBE(5);
#endif
#ifdef CHSIM
    uint8_t idle = 0;                                           // the simulator feeds its script between frames
    for (dbg::poll(); !chgame.nextFrame(); dbg::poll()) {
        sim_sync();
        sim_advance(1000);
        if (++idle > 2) { sim_waitInput(); idle = 0; }
    }
#else
    do { dbg::poll(); } while (!chgame.nextFrame());
#endif
    chgame.pollButtons();
    dbg::markUpdateStart();
    static uint32_t startDown;
    if (!chgame.pressed(START_BUTTON)) startDown = 0;
    else if (!startDown) startDown = millis() | 1;
    else if (millis() - startDown >= 3000) chgame.exitToMenu();
}
