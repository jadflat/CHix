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
#include "Art.h"        // the title picture (tools/gen_art.py)
#include "Sprites.h"
#include "Bosses.h"     // the 12x12 boss cores (tools/make_bosses.py)
#include "Music.h"      // the songs (tools/make_music.py)    // the 8x8 sprites (tools/make_sprites.py)

static void blit12(int x, int y, const uint8_t *spr);

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

static const uint8_t QCOL[4] = { C_Q0, C_Q1, C_TRAIL, C_EDGE };

// ---- stage themes: the fill's colours, the border and frame, and a fill pattern each
struct Theme { uint8_t fast[3], fastL[3], fastD[3], slow[3], slowL[3], slowD[3], edge[3], frame[3]; };
static const Theme THEMES[10] = {
    { {30,70,230},  {130,175,255}, {15,35,115},  {230,130,20}, {255,205,120}, {115,65,10},  {255,255,255}, {90,90,90} },     // classic
    { {30,170,90},  {130,240,170}, {10,70,40},   {170,70,210}, {230,150,255}, {70,25,95},   {200,255,255}, {40,110,90} },    // emerald
    { {210,50,40},  {255,150,90},  {95,20,20},   {230,190,40}, {255,240,140}, {110,80,10},  {255,220,170}, {120,50,30} },    // magma
    { {40,150,200}, {160,225,250}, {15,60,95},   {240,110,170},{255,190,220}, {110,40,75},  {230,245,255}, {70,100,140} },   // ice
    { {110,70,220}, {180,150,255}, {40,25,95},   {150,220,40}, {215,255,130}, {60,90,10},   {255,120,255}, {110,60,150} },  // void
    { {200,60,140}, {255,140,200}, {90,20,60},   {255,150,40}, {255,215,120}, {110,60,10},  {255,230,240}, {130,50,90} },    // sunset
    { {20,100,180}, {100,200,255}, {10,40,90},   {40,200,170}, {150,255,230}, {10,90,75},   {220,255,255}, {40,90,130} },    // ocean
    { {130,200,30}, {210,250,110}, {50,80,10},   {230,60,60}, {255,150,150},  {100,20,20},  {240,255,160}, {80,110,40} },    // toxic
    { {200,160,30}, {255,230,130}, {90,70,10},   {120,70,200}, {190,150,255}, {50,30,95},   {255,245,200}, {130,100,30} },   // gold
    { {130,140,160}, {210,220,235}, {55,60,75},  {200,70,90}, {255,150,165},  {90,30,40},   {255,255,255}, {100,105,120} } }; // steel
static int theme;

static void buildScene(int t);
static void applyTheme(int t) {
    theme = t;
    buildScene(t);
    const Theme &h = THEMES[t];
    gfx_setPaletteEntry(1, gfx_rgb(h.fast[0], h.fast[1], h.fast[2]));
    gfx_setPaletteEntry(9, gfx_rgb(h.fastL[0], h.fastL[1], h.fastL[2]));
    gfx_setPaletteEntry(12, gfx_rgb(h.fastD[0], h.fastD[1], h.fastD[2]));
    gfx_setPaletteEntry(2, gfx_rgb(h.slow[0], h.slow[1], h.slow[2]));
    gfx_setPaletteEntry(10, gfx_rgb(h.slowL[0], h.slowL[1], h.slowL[2]));
    gfx_setPaletteEntry(13, gfx_rgb(h.slowD[0], h.slowD[1], h.slowD[2]));
    gfx_setPaletteEntry(4, gfx_rgb(h.edge[0], h.edge[1], h.edge[2]));
    gfx_setPaletteEntry(14, gfx_rgb(h.frame[0], h.frame[1], h.frame[2]));
}


static int hiScore, nextLife = 10000;
static bool won;
static int16_t fuse = -1;                       // the fuse burning down your open line (-1: none)
static uint8_t stallT;
static uint8_t g[H][W];
static uint16_t trail[640];
static int trailLen;
static State state;
static int px, py, startX, startY;
static bool drawing, slowDraw;
static int lives, level, score, areaPct, timer, frameNo;
enum { STAGES = 25 };
static inline int tgt() { return 70 + (level - 1) / 3; }            // the share to claim: 70% rising to 78%
static inline int sparkN() { return level >= 8 ? 3 : 2; }           // a third Spark from stage 8
static uint32_t rng = 12345;

struct Spark { int x, y, dx, dy; bool right; };
static Spark sp[3];
static uint8_t sh[3][3][2];                    // each Spark's last three cells, for its afterglow
static int flash, clearBonus, popVal;
static uint8_t ringT, ringCol, hitT, popT, readyT, respawnT, shakeT;   // respawnT: the closing circle after a death
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

static void placeSpark(int i) {                // on a border cell off the player's row and column
    for (int t = 0; t < 40; t++) {
        int x = rnd(W), y = rnd(H);
        if (isBorder(x, y) && x != px && y != py) { sp[i].x = x; sp[i].y = y; goto done; }
    }
    for (int y = 0; y < H; y++)
        for (int x = 0; x < W; x++)
            if (isBorder(x, y)) { sp[i].x = x; sp[i].y = y; goto done; }
done:
    for (int k = 0; k < 3; k++) { sh[i][k][0] = sp[i].x; sh[i][k][1] = sp[i].y; }
}

static void collect() {
    const PuInfo &in = PUI[pu.type];
    if (pu.type == PU_BONUS) score += 2500;
    else if (pu.type == PU_LIFE) { if (lives < 6) lives++; audio::sfx(S_LIFE); }
    else if (pu.type == PU_BOMB) {
        for (int i = 0; i < sparkN(); i++) {
            burst(OX + 2 * sp[i].x, OY + 2 * sp[i].y, 8, C_SPARK);
            placeSpark(i);
        }
        score += 1500;
        flash = 10; shakeT = 8;
    } else puT[pu.type] = in.dur;
    banner = &in; banT = 75;
    burst(OX + 2 * pu.x + 1, OY + 2 * pu.y + 1, 16, in.col);
    audio::sfx(S_POWER);
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
    for (int x = 0; x < W; x++) g[0][x] = g[H - 1][x] = FAST;
    for (int y = 0; y < H; y++) g[y][0] = g[y][W - 1] = FAST;
    areaPct = 0;
    markBorders();
}

static void resetActors() {
    px = startX = W / 2; py = startY = H - 1;
    drawing = false; trailLen = 0;
    memset(puT, 0, sizeof puT); pu.life = 0; puWait = 0; banT = 0; memset(parts, 0, sizeof parts);
    sp[0] = { 1, 0, 1, 0, false };
    sp[1] = { W - 2, 0, -1, 0, true };
    sp[2] = { W / 2, 0, 1, 0, false };
    fuse = -1; stallT = 0;
    for (int i = 0; i < 3; i++)
        for (int k = 0; k < 3; k++) { sh[i][k][0] = sp[i].x; sh[i][k][1] = sp[i].y; }
    for (int i = 0; i < 2; i++) {
        qx[i] = (W / 2 + (i ? 6 : -6)) * 16; qy[i] = (H / 2 + (i ? -5 : 5)) * 16;
        qvx[i] = i ? -11 : 10; qvy[i] = i ? 8 : -9;
    }
    for (int i = 0; i < Q_HIST; i++)
        qh[i] = { (int16_t)(qx[0] >> 4), (int16_t)(qy[0] >> 4), (int16_t)(qx[1] >> 4), (int16_t)(qy[1] >> 4) };
}

#ifdef CHIX_DEMO_FILL
static void demoFill() {                                        // a build flag for looking at the pictures: most of the field claimed
    for (int y = 6; y < 50; y++) for (int x = 4; x < 56; x++) g[y][x] = x < 30 ? FAST : SLOW;
    markBorders();
}
#endif
static void newLevel() { resetField();
#ifdef CHIX_DEMO_FILL
    demoFill();
#endif
    resetActors(); readyT = 45; applyTheme((level - 1) % 10); audio::music(SONGS[1 + (level - 1) % 4]); }
#ifndef CHIX_START_LEVEL
#define CHIX_START_LEVEL 1
#endif
static void newGame() { won = false; audio::sfx(S_START); nextLife = 10000; lives = 3; level = CHIX_START_LEVEL; score = 0; newLevel(); state = PLAY; won = false; }

static void clearTrail() {
    for (int i = 0; i < trailLen; i++) g[trail[i] >> 6][trail[i] & 63] = EMPTY;
    trailLen = 0;
}

static void die() {
    burst(OX + 2 * px, OY + 2 * py, 16, C_PLAYER);
    ringT = 14; ringX = OX + 2 * px + 1; ringY = OY + 2 * py + 1; ringCol = C_PLAYER; hitT = 8; shakeT = 10;
    burst(OX + 2 * px, OY + 2 * py, 12, C_EDGE);
    clearTrail();
    fuse = -1;
    px = startX; py = startY;
    drawing = false;
    state = DYING; timer = 40;
    audio::sfx(S_DIE);
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
    px = bx; py = by;
}

static void closeTrail() {
    uint8_t v = slowDraw ? SLOW : FAST;
    int gained = trailLen;
    for (int i = 0; i < trailLen; i++) g[trail[i] >> 6][trail[i] & 63] = v;
    trailLen = 0;
    static uint16_t q[512];
    static const int8_t D4[4][2] = { {1, 0}, {-1, 0}, {0, 1}, {0, -1} };
    int sx = qx[0] >> 4, sy = qy[0] >> 4;
    if (inb(sx, sy) && g[sy][sx] == EMPTY) {
        int head = 0, tail = 0;
        g[sy][sx] |= MARK;
        q[tail++] = (sy << 6) | sx;
        while (head != tail) {
            int c = q[head];
            head = (head + 1) & 511;
            int x = c & 63, y = c >> 6;
            for (int k = 0; k < 4; k++) {
                int nx = x + D4[k][0], ny = y + D4[k][1];
                if (inb(nx, ny) && g[ny][nx] == EMPTY) {
                    g[ny][nx] |= MARK;
                    q[tail] = (ny << 6) | nx;
                    tail = (tail + 1) & 511;
                }
            }
        }
    }
    int open = 0;
    for (int y = 1; y < H - 1; y++)
        for (int x = 1; x < W - 1; x++) {
            if (g[y][x] == EMPTY) { g[y][x] = v; gained++; }
            else if (g[y][x] & MARK) { g[y][x] &= ~MARK; open++; }
        }
    markBorders();
    score += gained * (slowDraw ? 20 : 10) * (puT[PU_X2] ? 2 : 1);
    if (score >= nextLife) { nextLife += 10000; if (lives < 6) lives++; audio::sfx(S_LIFE); }
    else audio::sfx(gained > 150 ? S_BIG : S_CLAIM);
    areaPct = 100 - open * 100 / ((W - 2) * (H - 2));
    for (int i = 0; i < sparkN(); i++) {                 // a Spark the fill swallowed starts again on a border
        if (isBorder(sp[i].x, sp[i].y)) continue;
        burst(OX + 2 * sp[i].x, OY + 2 * sp[i].y, 12, C_SPARK);           // a captured Spark blows up
        burst(OX + 2 * sp[i].x, OY + 2 * sp[i].y, 6, C_EDGE);
        score += 1000; audio::sfx(S_ZAP);
        bool found = false;
        for (int y = 0; y < H && !found; y++)
            for (int x = 0; x < W && !found; x++)
                if (isBorder(x, y)) { sp[i].x = x; sp[i].y = y; found = true; }
    }
    drawing = false;
    burst(OX + 2 * px, OY + 2 * py, gained > 150 ? 16 : 8, slowDraw ? C_SLOWL : C_FASTL);
    flash = 10;
    ringT = 14; ringX = popX = OX + 2 * px + 1; ringY = popY = OY + 2 * py + 1; ringCol = slowDraw ? C_SLOWL : C_FASTL;
    if (gained > 250) shakeT = 6;
    popT = 36; popVal = gained * (slowDraw ? 20 : 10) * (puT[PU_X2] ? 2 : 1);
    snapPlayer();
    if (areaPct >= tgt()) {
        clearBonus = (areaPct - tgt()) * 100 + 1000;
        score += clearBonus;
        state = CLEARED; timer = CLEAR_TIME;
        audio::sfx(S_CLEAR);
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
        if (!(trailLen & 3)) audio::sfx(S_STEP);
        g[ny][nx] = TRAIL; trail[trailLen++] = (ny << 6) | nx;
        px = nx; py = ny;
    } else if (claimed(nx, ny)) {
        px = nx; py = ny;
        closeTrail();
    }
}

// Wall-following: one hand on the border, the other Spark on the other hand.
static void moveSpark(int n) {
    Spark &s = sp[n];
    sh[n][2][0] = sh[n][1][0]; sh[n][2][1] = sh[n][1][1];
    sh[n][1][0] = sh[n][0][0]; sh[n][1][1] = sh[n][0][1];
    sh[n][0][0] = s.x; sh[n][0][1] = s.y;
    static const int8_t D[4][2] = { {1, 0}, {0, 1}, {-1, 0}, {0, -1} };
    static const int8_t LEFT[4] = { 3, 0, 1, 2 }, RIGHT[4] = { 1, 0, 3, 2 };
    int cur = 0;
    for (int k = 0; k < 4; k++) if (D[k][0] == s.dx && D[k][1] == s.dy) cur = k;
    for (int i = 0; i < 4; i++) {
        int k = (cur + (s.right ? RIGHT[i] : LEFT[i])) & 3;
        int nx = s.x + D[k][0], ny = s.y + D[k][1];
        if (isBorder(nx, ny)) { s.x = nx; s.y = ny; s.dx = D[k][0]; s.dy = D[k][1]; return; }
    }
}

static bool freeAt(int ax, int ay) {
    int cx = ax >> 4, cy = ay >> 4;
    return inb(cx, cy) && (g[cy][cx] == EMPTY || g[cy][cx] == TRAIL);
}

static void moveCore() {
    for (int i = 0; i < 2; i++) {
        if ((frameNo & 15) == i * 7) {
            int lim = 12 + min(level * 2 / 3, 12);              // the core gets faster
            qvx[i] = constrain(qvx[i] + rnd(5) - 2, -lim, lim);
            qvy[i] = constrain(qvy[i] + rnd(5) - 2, -lim, lim);
            if (qvx[i] == 0) qvx[i] = 3;
            if (qvy[i] == 0) qvy[i] = -3;
        }
        if (freeAt(qx[i] + qvx[i], qy[i] + qvy[i])) { qx[i] += qvx[i]; qy[i] += qvy[i]; }
        else if (freeAt(qx[i] + qvx[i], qy[i])) { qx[i] += qvx[i]; qvy[i] = -qvy[i]; }
        else if (freeAt(qx[i], qy[i] + qvy[i])) { qy[i] += qvy[i]; qvx[i] = -qvx[i]; }
        else { qvx[i] = -qvx[i]; qvy[i] = -qvy[i]; }
    }
    int ddx = qx[1] - qx[0], ddy = qy[1] - qy[0];                 // keep the line short: pull the ends together
    if (abs(ddx) + abs(ddy) > 16 * 16) {
        qvx[0] += ddx > 0; qvx[0] -= ddx < 0; qvx[1] -= ddx > 0; qvx[1] += ddx < 0;
        qvy[0] += ddy > 0; qvy[0] -= ddy < 0; qvy[1] -= ddy > 0; qvy[1] += ddy < 0;
    }
    qhead = (qhead + 1) % Q_HIST;
    qh[qhead] = { (int16_t)(qx[0] >> 4), (int16_t)(qy[0] >> 4), (int16_t)(qx[1] >> 4), (int16_t)(qy[1] >> 4) };
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
static const Shape SHAPES[7] = {
    { V_CUBE, E_CUBE, 8, 12 }, { V_OCTA, E_OCTA, 6, 12 }, { V_PYRA, E_PYRA, 5, 8 }, { V_PRISM, E_PRISM, 6, 9 },
    { V_HEX, E_HEX, 12, 18 }, { V_ICO, E_ICO, 12, 30 }, { V_TESS, E_TESS, 16, 32 } };
static const char *const ENEMY_NAMES[8] = { "ORIGIN CORE", "CUBE DRONE", "OCTA CORE", "PYRA SCOUT", "PRISM HUNTER", "HEX WARDEN", "ICOSA MIND", "TESSERACT" };
static int8_t SINT[32];                                     // sin * 64, 32 steps a turn (built in setup)
static uint16_t rot;
static int16_t polyX[16], polyY[16], polyZ[16];                // projected corners: pixels, and depth

static inline int enemyKind() { return (level - 1) % 8; }   // 0: the roaming line, 1..7: SHAPES[kind - 1]

static void projectPoly() {
    const Shape &sh = SHAPES[enemyKind() - 1];
    int ay = (rot >> 1) & 31, ax = ((rot * 3) >> 2) & 31;
    int sa = SINT[ay], ca = SINT[(ay + 8) & 31], sb = SINT[ax], cb = SINT[(ax + 8) & 31];
    int cx = OX + ((qx[0] * 2) >> 4), cy = OY + ((qy[0] * 2) >> 4);
    for (int i = 0; i < sh.nv; i++) {
        int x = sh.v[i][0], y = sh.v[i][1], z = sh.v[i][2];
        int x1 = (x * ca + z * sa) >> 6, z1 = (z * ca - x * sa) >> 6;
        int y2 = (y * cb - z1 * sb) >> 6, z2 = (y * sb + z1 * cb) >> 6;
        int f = 256 * 80 / (80 + z2);                              // a little perspective
        polyX[i] = cx + x1 * f * 3 / 2048;
        polyY[i] = cy + y2 * f * 3 / 2048;
        polyZ[i] = z2;
    }
}

static bool polyHits() {                                    // an edge crosses the open line
    const Shape &sh = SHAPES[enemyKind() - 1];
    for (int e = 0; e < sh.ne; e++) {
        int a = sh.e[e][0], b = sh.e[e][1];
        for (int t = 0; t <= 5; t++) {
            int x = (polyX[a] + (polyX[b] - polyX[a]) * t / 5 - OX) >> 1, y = (polyY[a] + (polyY[b] - polyY[a]) * t / 5 - OY) >> 1;
            if (inb(x, y) && g[y][x] == TRAIL) return true;
        }
    }
    return false;
}

static void drawPoly() {
    const Shape &sh = SHAPES[enemyKind() - 1];
    bool ice = puT[PU_FREEZE] != 0;
    for (int e = 0; e < sh.ne; e++) {
        int a = sh.e[e][0], b = sh.e[e][1];
        int x0 = polyX[a], y0 = polyY[a], x1 = polyX[b], y1 = polyY[b];
        uint8_t c = ice ? C_FASTL : (polyZ[a] + polyZ[b] < 0) ? C_EDGE : C_Q0;   // near edges bright, far edges cyan
        int n = max(abs(x1 - x0), abs(y1 - y0));
        for (int i = 0; i <= n; i++) gfx_pixel(n ? x0 + (x1 - x0) * i / n : x0, n ? y0 + (y1 - y0) * i / n : y0, c);
    }
    for (int i = 0; i < sh.nv; i++) gfx_fillRect(polyX[i] - 1, polyY[i] - 1, 2, 2, ice ? C_EDGE : C_TRAIL);
    blit12(OX + ((qx[0] * 2) >> 4) - 6, OY + ((qy[0] * 2) >> 4) - 6, BOSSES[enemyKind()]);       // the core
}

static bool coreHits() {
    if (enemyKind()) return polyHits();
    for (int s = 0; s <= 12; s++) {
        int x = ((qx[0] * (12 - s) + qx[1] * s) / 12) >> 4, y = ((qy[0] * (12 - s) + qy[1] * s) / 12) >> 4;
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
static uint8_t pauseSel, titleSel, prevBtn;
static const char *pauseNote;

static void saveProgress(bool inGame) {
    sv = { hiScore, score, nextLife, (uint8_t)level, (uint8_t)lives };
    saveFlag = inGame;
    saveDue = true;                                          // written after gfx_wait() in loop()
}

static void continueGame() {
    audio::sfx(S_START);
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
            } else { state = TITLE; titleSel = 0; resetField(); applyTheme(0); audio::music(SONGS[0]); }
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
        else if (chgame.pressed(A_BUTTON)) { resetField(); state = TITLE; applyTheme(0); audio::music(SONGS[0]); }
        return;
    }
    if (state == DYING) {
        if (--timer <= 0) {
            if (--lives <= 0) { state = OVER; timer = 30; audio::sfx(S_OVER); audio::stopMusic(); saveProgress(false); }
            else { int sx = startX, sy = startY; resetActors(); px = startX = sx; py = startY = sy; snapPlayer(); state = PLAY; respawnT = 36; audio::sfx(S_ZAP); }
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
            if (level >= STAGES) { won = true; state = OVER; timer = 120; audio::sfx(S_CLEAR); saveProgress(false); }
            else { level++; newLevel(); state = PLAY; saveProgress(true); }
        }
        return;
    }
    if (respawnT) { respawnT--; return; }                       // frozen while the circle closes in
    bool a = chgame.pressed(A_BUTTON), b = chgame.pressed(B_BUTTON);
    int dx = (int)chgame.pressed(RIGHT_BUTTON) - (int)chgame.pressed(LEFT_BUTTON);
    int dy = (int)chgame.pressed(DOWN_BUTTON) - (int)chgame.pressed(UP_BUTTON);
    static bool horiz;                              // no diagonals: a second direction held is ignored
    if (dx && dy) { if (horiz) dy = 0; else dx = 0; }
    else if (dx) horiz = true;
    else if (dy) horiz = false;
    if (banT) banT--;
    int ox = px, oy = py;
    bool slowMove = !puT[PU_SPEED] && (drawing ? slowDraw : (b && !a));
    for (int step = 0; step < (puT[PU_SPEED] ? 2 : 1); step++) {
        if ((dx || dy) && (!slowMove || (frameNo & 1))) movePlayer(dx, dy, a, b);
        if (state != PLAY) return;
    }
    if (puT[PU_SPEED] && (frameNo & 1)) burst(OX + 2 * px, OY + 2 * py, 1, C_TRAIL);
    if (drawing && !(frameNo & 3)) burst(OX + 2 * px, OY + 2 * py, 1, slowDraw ? C_SLOWL : C_FASTL);   // a comet tail
    if (drawing && level >= 4) {                          // from stage 4 a fuse burns down the line if you stall
        if (px != ox || py != oy) { fuse = -1; stallT = 0; }
        else {
            if (stallT < 255) stallT++;
            if (stallT > 45 && fuse < 0) { fuse = 0; audio::sfx(S_ZAP); }
        }
        if (fuse >= 0) {
            fuse += 2;
            if (fuse < trailLen && (frameNo & 1)) burst(OX + 2 * (trail[fuse] & 63), OY + 2 * (trail[fuse] >> 6), 1, C_TRAIL);
            if (fuse >= trailLen - 1 && !puT[PU_SHIELD]) { die(); return; }
            if (fuse >= trailLen - 1) fuse = -1;
        }
    } else fuse = -1;
    if (pu.life) {                                       // the pick-up: walk onto it, or close round it
        if (!(frameNo & 1)) pu.life--;
        if ((px == pu.x && py == pu.y) || claimed(pu.x, pu.y)) collect();
    } else if (++puWait > 200 + level * 6) { puWait = 0; spawnPickup(); }   // fewer pick-ups as stages go
    bool frozen = puT[PU_FREEZE] != 0, shield = puT[PU_SHIELD] != 0;
    bool tick = !frozen && (!puT[PU_SLOW] || (frameNo & 1));
    if (tick) { moveCore(); rot++; }
    if (enemyKind()) projectPoly();
    int period = level >= 6 ? 1 : 2;                   // the Spark speed up from stage 6
    for (int i = 0; i < sparkN(); i++) {
        if (tick && frameNo % period == 0) moveSpark(i);
        if (puT[PU_LASER] && (sp[i].x == px || sp[i].y == py)) {   // the lasers sweep the row and column
            burst(OX + 2 * sp[i].x, OY + 2 * sp[i].y, 10, C_SPARK);
            score += 500; audio::sfx(S_ZAP); placeSpark(i);
        }
        if (!shield && sp[i].x == px && sp[i].y == py) { die(); return; }
    }
    if (drawing && !frozen && !shield && !puT[PU_GHOST] && coreHits()) die();
    for (int k = 0; k < PU_COUNT; k++) if (puT[k]) puT[k]--;
}

// A claimed cell shows its stage's picture, 4 tones from the fill's colours: dark, fill, light, and
// lights (cyan on a fast claim, gold on a slow one).
static const uint8_t TONE_FAST[4] = { C_FASTD, C_FAST, C_FASTL, C_Q0 };
static const uint8_t TONE_SLOW[4] = { C_SLOWD, C_SLOW, C_SLOWL, C_TRAIL };
static uint8_t sceneTone(int px, int py);
// ---- the stage pictures: a rainy cyberpunk skyline drawn per pixel, a different one for each theme -----
// Layers, back to front: a dithered sky (with stars and a big disc), a far skyline, a near skyline of
// lit windows and billboards, and a wet street; rain and a flying car cross all of it. A claimed cell
// shows 2x2 of these pixels in 4 tones from its fill's colours: dark, fill, light, and lights.
struct Scene { uint8_t seed, nearMin, nearMax, farMin, farMax, dens, discX, discY, discR, bb; };
static const Scene SCENES[10] = {
    { 1, 30, 75, 20, 50, 7, 0, 0, 0, 3 },     { 2, 14, 45, 10, 35, 5, 90, 30, 16, 0 }, { 3, 20, 60, 10, 40, 6, 0, 0, 0, 0 },
    { 4, 25, 85, 20, 60, 8, 30, 28, 14, 4 },  { 5, 35, 95, 25, 70, 9, 0, 0, 0, 2 },    { 6, 28, 70, 15, 45, 7, 60, 40, 26, 4 },
    { 7, 15, 50, 10, 35, 6, 95, 22, 12, 0 },  { 8, 20, 65, 15, 45, 6, 0, 0, 0, 5 },    { 9, 40, 100, 30, 80, 10, 60, 45, 30, 3 },
    { 10, 50, 105, 35, 85, 11, 0, 0, 0, 2 } };
static const uint8_t BAYER4[4][4] = { { 0, 8, 2, 10 }, { 12, 4, 14, 6 }, { 3, 11, 1, 9 }, { 15, 7, 13, 5 } };
static uint8_t farH[120], midH[120], nearH[120];               // skyline heights a column; bit 7: a billboard
static const Scene *scene = &SCENES[0];

static uint8_t winBits[105];                                    // which windows are lit: 30 x 28 bits, built once a stage

static inline uint32_t mixHash(uint32_t a, uint32_t b) { return (a * 2654435761u + b * 40503u) * 2246822519u; }

static void buildScene(int t) {
    scene = &SCENES[t];
    uint32_t r = scene->seed * 2654435761u + 12345u;
    for (int layer = 0; layer < 3; layer++) {                  // far, middle, near
        uint8_t *h = layer == 0 ? farH : layer == 1 ? midH : nearH;
        int lo = layer == 0 ? scene->farMin : layer == 1 ? (scene->farMin + scene->nearMin) / 2 : scene->nearMin;
        int hi = layer == 0 ? scene->farMax : layer == 1 ? (scene->farMax + scene->nearMax) / 2 : scene->nearMax;
        for (int x = 0; x < 120;) {
            r = r * 1664525u + 1013904223u; int w = (layer == 2 ? 6 : 4) + (int)((r >> 16) % (layer == 2 ? 10 : 8));
            r = r * 1664525u + 1013904223u; int ht = lo + (int)((r >> 16) % (uint32_t)(hi - lo + 1));
            r = r * 1664525u + 1013904223u; bool bb = layer == 2 && scene->bb && (r >> 16) % scene->bb == 0;
            for (int i = 0; i < w && x < 120; i++, x++) h[x] = (uint8_t)(ht | (bb ? 128 : 0));
        }
    }
    memset(winBits, 0, sizeof winBits);
    for (int wy = 0; wy < 28; wy++)
        for (int wx = 0; wx < 30; wx++)
            if ((mixHash(wx, wy + scene->seed * 64) >> 28) < (uint32_t)((scene->dens * 3) >> 2)) {
                int idx = wy * 30 + wx;
                winBits[idx >> 3] |= (uint8_t)(1 << (idx & 7));
            }
}

// One pixel of the picture, as a tone 0-3 (dark, fill, light, lights). Kept lean: it runs for every
// pixel of the claimed ground each frame, so it only compares and looks up (the animation, the rain and the
// flying cars, is drawn over it by drawScene()).
static uint8_t sceneTone(int px, int py) {
    int fb = 111 - py;                                           // pixels above the street
    if (fb < 6) return fb < 2 ? 1 : (((px + fb * 5) & 15) == 0 ? 3 : 0);     // the wet street, with reflected lights
    uint8_t nh = nearH[px];
    int hb = nh & 127;
    if (fb < hb) {                                               // a near building
        if (fb == hb - 1) return 2;                              // a lit roof edge
        if ((nh & 128) && fb < hb - 3 && fb > hb - 22)           // a billboard
            return (fb == hb - 4 || fb == hb - 5 || fb == hb - 21) ? 2 : ((py >> 1) & 1) ? 3 : (((px >> 1) & 1) ? 2 : 0);
        if ((px & 3) < 2 && (fb & 3) < 2) {                      // a window, lit or dark
            int wr = fb >> 2, idx = (wr << 5) - (wr << 1) + (px >> 2);                   // wr * 30, with shifts: no multiplier on this chip
            return (winBits[idx >> 3] >> (idx & 7)) & 1 ? 3 : 0;
        }
        if (px && (nearH[px - 1] & 127) != hb) return 1;         // rim light on a left edge
        return 0;
    }
    int hm = midH[px] & 127;
    if (fb < hm) {                                               // a middle building
        if ((px & 3) == 1 && (fb & 3) == 1 && ((((px >> 2) + (fb >> 2) + scene->seed) & 3) == 0)) return 2;
        if (px && (midH[px - 1] & 127) != hm) return 2;
        return 1;
    }
    if (fb < farH[px]) return BAYER4[py & 3][px & 3] < 7 ? 2 : 1;           // a far building, hazy
    int t = (((py << 5) + (py << 2) + py) >> 7) + BAYER4[py & 3][px & 3];           // the sky: dark at the top, glowing at the horizon
    t >>= 4;
    if (scene->discR) {                                          // a big sun, moon or advert
        int dx = px - scene->discX, dy = py - scene->discY, r = scene->discR;
        if (dx > -r && dx < r && dy > -r && dy < r) {
            int d2 = dx * dx + dy * dy, r2 = r * r;
            if (d2 < r2 * 3 / 4 || (d2 < r2 && BAYER4[py & 3][px & 3] < 8)) t = 2;
            if (d2 < r2 / 6) t = 3;
        }
    }
    return t;
}

// The picture's animation, over the claimed ground only: rain, and flying cars with trails.
static void scenePlot(int px, int py, uint8_t light) {
    if (px < 0 || px >= 120 || py < 0 || py >= 112) return;
    uint8_t v = g[py >> 1][px >> 1] & 3;
    if (v == FAST || v == SLOW) gfx_pixel(OX + px, OY + py, light >= 3 ? (v == FAST ? C_Q0 : C_TRAIL) : (v == FAST ? C_FASTL : C_SLOWL));
}
static void drawScene() {
    for (int i = 0; i < 26; i++) {
        int x = (i * 37 + (frameNo >> 1)) & 127, y = (frameNo * 3 + i * 29) & 127;
        for (int k = 0; k < 3; k++) scenePlot(x - (k >> 1), y + k, 2);
    }
    int fx = (frameNo * 2 + scene->seed * 7) % 200 - 40, fy = 14 + (scene->seed & 15) * 3;
    for (int k = 0; k < 10; k++) scenePlot(fx - k, fy, k < 2 ? 3 : 2);
    int gx = 160 - (frameNo * 3 + scene->seed * 11) % 220, gy = 30 + (scene->seed & 7) * 5;
    for (int k = 0; k < 7; k++) scenePlot(gx + k, gy, k < 2 ? 3 : 2);
}


static void drawCells() {
    bool cl = state == CLEARED;
    int wipe = cl ? (CLEAR_TIME - timer) * H / 45 : 0;               // the scan that fills what is left
    for (int y = 0; y < H; y++) {
        uint8_t *r0 = gfx_fb + (OY + 2 * y) * GFX_FB_STRIDE + OX / 2;
        uint8_t *r1 = r0 + GFX_FB_STRIDE;
        for (int x = 0; x < W; x++) {
            uint8_t c = g[y][x], v0, v1;
            c &= 3;
            if (cl && c == EMPTY) c = y == wipe ? 0xFF : y < wipe ? FAST : EMPTY;
            if (c == 0xFF) v0 = v1 = C_EDGE;
            else if (c == EMPTY) v0 = v1 = C_BG;
            else if (c == TRAIL) v0 = v1 = (frameNo & 2) ? C_TRAIL : C_EDGE;
            else if (g[y][x] & BORD) v0 = v1 = ((x + y + (frameNo >> 1)) & 15) == 0 ? C_TRAIL : C_EDGE;   // a shimmer runs round the border
            else {
                if (flash & 2) { r0[x] = r1[x] = C_EDGE * 17; continue; }
                const uint8_t *tn = c == FAST ? TONE_FAST : TONE_SLOW;
                int qx2 = 2 * x, qy2 = 2 * y;
                r0[x] = tn[sceneTone(qx2, qy2)] | (tn[sceneTone(qx2 + 1, qy2)] << 4);
                r1[x] = tn[sceneTone(qx2, qy2 + 1)] | (tn[sceneTone(qx2 + 1, qy2 + 1)] << 4);
                continue;
            }
            r0[x] = v0 | (v0 << 4);
            r1[x] = v1 | (v1 << 4);
        }
    }
    int x0 = OX - 2, y0 = OY - 2, w = 2 * W + 4, h = 2 * H + 4;       // the frame round the field
    gfx_fillRect(x0, y0, w, 1, C_FRAME); gfx_fillRect(x0, y0 + h - 1, w, 1, C_FRAME);
    gfx_fillRect(x0, y0, 1, h, C_FRAME); gfx_fillRect(x0 + w - 1, y0, 1, h, C_FRAME);
}

// A Spark: a spinning four-point spark with a fading afterglow.
// The sprites are drawn in the HOUSE palette; the game's palette has these colours (some change
// with the stage's theme: blue and navy follow the fill, wine follows the slow fill's dark).
static const uint8_t HOUSE2GAME[14] = { C_BG, C_EDGE, C_BG, C_BG, C_BG, C_TEXT, C_PLAYER, C_SLOWD, C_TRAIL, C_BG,
                                        C_FAST, C_FASTD, C_BG, C_Q0 };
static void blit8(int x, int y, const uint8_t *spr) {
    for (int dy = 0; dy < 8; dy++) {
        int yy = y + dy;
        if (yy < 0 || yy >= 128) continue;
        for (int dx = 0; dx < 8; dx++) {
            uint8_t v = spr[dy * 8 + dx];
            int xx = x + dx;
            if (v == 255 || xx < 0 || xx >= 128) continue;
            uint8_t c = HOUSE2GAME[v], *b = gfx_fb + yy * GFX_FB_STRIDE + (xx >> 1);
            *b = (xx & 1) ? (uint8_t)((*b & 0x0F) | (c << 4)) : (uint8_t)((*b & 0xF0) | c);
        }
    }
}
static void blit12(int x, int y, const uint8_t *spr) {
    for (int dy = 0; dy < 12; dy++) {
        int yy = y + dy;
        if (yy < 0 || yy >= 128) continue;
        for (int dx = 0; dx < 12; dx++) {
            uint8_t v = spr[dy * 12 + dx];
            int xx = x + dx;
            if (v == 255 || xx < 0 || xx >= 128) continue;
            uint8_t c = HOUSE2GAME[v], *b = gfx_fb + yy * GFX_FB_STRIDE + (xx >> 1);
            *b = (xx & 1) ? (uint8_t)((*b & 0x0F) | (c << 4)) : (uint8_t)((*b & 0xF0) | c);
        }
    }
}
static const uint8_t *const ICONS[PU_COUNT] = { SPR_PU_FREEZE, SPR_PU_SPEED, SPR_PU_LASER, SPR_PU_SHIELD, SPR_PU_SLOW,
                                                SPR_PU_BONUS, SPR_PU_X2, SPR_PU_GHOST, SPR_PU_BOMB, SPR_PU_LIFE };

static const uint8_t GLYPH[4][7] = {                            // C H I X, 5x7, bit 4 = the left column
    { 0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E }, { 0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11 },
    { 0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x1F }, { 0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11 } };
static void drawLogo(int y0) {
    static const uint8_t GRAD[7] = { C_EDGE, C_Q0, C_Q0, C_FASTL, C_FAST, C_FAST, C_FASTD };   // light at the top, deep blue below
    int sweep = (frameNo * 3) % 220 - 40;                                                     // the shine's position
    for (int pass = 0; pass < 2; pass++)                                                      // 0: the shadow, 1: the letters
        for (int l = 0; l < 4; l++)
            for (int r = 0; r < 7; r++)
                for (int c = 0; c < 5; c++) {
                    if (!((GLYPH[l][r] >> (4 - c)) & 1)) continue;
                    int bx = 9 + l * 28 + c * 5, by = y0 + r * 5;
                    if (!pass) { gfx_fillRect(bx + 2, by + 2, 5, 5, C_BG); continue; }
                    uint8_t col = abs(bx + by / 2 - sweep) < 5 ? C_EDGE : GRAD[r];
                    gfx_fillRect(bx, by, 5, 5, col);
                    bool up = r > 0 && ((GLYPH[l][r - 1] >> (4 - c)) & 1), dn = r < 6 && ((GLYPH[l][r + 1] >> (4 - c)) & 1);
                    bool lf = c > 0 && ((GLYPH[l][r] >> (5 - c)) & 1), rt = c < 4 && ((GLYPH[l][r] >> (3 - c)) & 1);
                    if (!up) gfx_fillRect(bx, by, 5, 1, C_EDGE);                              // a bevel: bright on the top and left,
                    if (!lf) gfx_fillRect(bx, by, 1, 5, C_EDGE);
                    if (!dn) gfx_fillRect(bx, by + 4, 5, 1, C_FASTD);                         // dark on the bottom and right
                    if (!rt) gfx_fillRect(bx + 4, by, 1, 5, C_FASTD);
                }
    gfx_fillRect(9, y0 + 38, 110, 1, C_Q0);                                                   // an underline and the tag
    const char *tag = "TERRITORY ARCADE";
    gfx_text((128 - gfx_textWidth(tag)) / 2, y0 + 41, tag, C_SLOWL);
}

static void panelBox(int x, int y, int w, int h, uint8_t edge) {
    gfx_fillRect(x, y, w, h, edge);
    gfx_fillRect(x + 1, y + 1, w - 2, h - 2, C_BG);
}

static void drawSpark(int n) {
    for (int k = 2; k >= 0; k--) {
        int cx = OX + 2 * sh[n][k][0], cy = OY + 2 * sh[n][k][1];
        gfx_fillRect(cx, cy, 2, 2, k == 2 ? C_FRAME : C_GLOW);
    }
    blit8(OX + 2 * sp[n].x - 3, OY + 2 * sp[n].y - 3, SPR_SPARK);
}

// The player: a diamond that pulses while drawing.
static void drawPlayer() {
    int cx = OX + 2 * px, cy = OY + 2 * py;
    blit8(cx - 3, cy - 3, SPR_SHIP);
    if (drawing && (frameNo & 2)) {                               // thruster glints while drawing
        gfx_pixel(cx - 4, cy + 4, C_TRAIL); gfx_pixel(cx + 5, cy + 4, C_TRAIL);
    }
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

static void drawLine(int x0, int y0, int x1, int y1, uint8_t c) {
    int n = max(abs(x1 - x0), abs(y1 - y0));
    for (int i = 0; i <= n; i++) {
        int x = n ? x0 + (x1 - x0) * i / n : x0, y = n ? y0 + (y1 - y0) * i / n : y0;
        gfx_pixel(OX + 2 * x, OY + 2 * y, c);
    }
}

static void draw() {
    gfx_clear(C_BG);
    char s[40];
    if (state == TITLE) {
        for (int y = 0; y < 64; y++) {                              // the picture, doubled
            const uint8_t *src = TITLE_ART + y * 32;
            uint8_t *d0 = gfx_fb + 2 * y * GFX_FB_STRIDE, *d1 = d0 + GFX_FB_STRIDE;
            for (int x = 0; x < 32; x++) {
                uint8_t a = src[x] & 15, b = src[x] >> 4;
                d0[2 * x] = d1[2 * x] = a | (a << 4);
                d0[2 * x + 1] = d1[2 * x + 1] = b | (b << 4);
            }
        }
        drawLogo(8);
        panelBox(10, 72, 108, 32, C_Q0);
        gfx_text(16, 76, "A  DRAW FAST", C_Q0);
        gfx_text(16, 85, "B  DRAW SLOW  X2", C_SLOWL);
        gfx_text(16, 94, "CLAIM THE FIELD", C_TEXT);
        if (hiScore) { char h[24]; snprintf(h, sizeof h, "HI %d", hiScore); gfx_text((128 - gfx_textWidth(h)) / 2, 62, h, C_TRAIL); }
        if (hasSave) {                                               // CONTINUE or NEW GAME
            panelBox(10, 106, 108, 20, C_Q0);
            snprintf(s, sizeof s, "CONTINUE  LV %d", sv.level);
            gfx_text(24, 109, s, titleSel == 0 ? C_EDGE : C_FRAME);
            gfx_text(24, 117, "NEW GAME", titleSel == 1 ? C_EDGE : C_FRAME);
            gfx_text(14, titleSel ? 117 : 109, ">", C_TRAIL);
        } else if (frameNo & 16) { panelBox(34, 108, 60, 14, C_Q0); gfx_text((128 - gfx_textWidth("PRESS A")) / 2, 112, "PRESS A", C_TRAIL); }
        return;
    }
    drawCells();
    drawScene();
    drawAmbient();
    if ((state != DYING || (timer & 4)) && enemyKind()) drawPoly();
    else if (state != DYING || (timer & 4)) {
        for (int i = Q_HIST - 1; i >= 0; i--) {
            QLine &l = qh[(qhead + Q_HIST - i) % Q_HIST];
            drawLine(l.x1, l.y1, l.x2, l.y2, puT[PU_FREEZE] ? (i ? C_FASTL : C_EDGE) : (i ? QCOL[i & 3] : C_TRAIL));
        }
        blit12(OX + ((qx[0] + qx[1]) >> 4) - 6, OY + ((qy[0] + qy[1]) >> 4) - 6, BOSSES[0]);          // its glowing heart
    }
    if (pu.life && (pu.life > 45 || (frameNo & 4))) {                // the pick-up, bobbing
        const PuInfo &in = PUI[pu.type];
        int bx = OX + 2 * pu.x - 3, by = OY + 2 * pu.y - 3 + ((frameNo >> 3) & 1);
        blit8(bx, by, ICONS[pu.type]);
        if (frameNo & 4) {                                            // corner glints
            gfx_pixel(bx - 1, by - 1, in.col); gfx_pixel(bx + 8, by - 1, in.col);
            gfx_pixel(bx - 1, by + 8, in.col); gfx_pixel(bx + 8, by + 8, in.col);
        }
    }
    if (puT[PU_LASER]) {                                              // the beams
        uint8_t c = (frameNo & 1) ? C_PLAYER : C_EDGE;
        gfx_fillRect(OX, OY + 2 * py, 2 * W, 2, c);
        gfx_fillRect(OX + 2 * px, OY, 2, 2 * H, c);
    }
    if (fuse >= 0 && fuse < trailLen) {                              // the fuse's spark
        int fx = OX + 2 * (trail[fuse] & 63), fy = OY + 2 * (trail[fuse] >> 6);
        gfx_fillRect(fx - 1, fy - 1, 4, 4, (frameNo & 2) ? C_EDGE : C_SPARK);
    }
    for (int i = 0; i < sparkN(); i++) drawSpark(i);
    if (state != DYING || (timer & 2)) drawPlayer();
    if (puT[PU_SHIELD] && (puT[PU_SHIELD] > 40 || (frameNo & 2))) {    // the shield ring
        int cx = OX + 2 * px, cy = OY + 2 * py;
        gfx_fillRect(cx - 4, cy - 3, 1, 8, C_Q0); gfx_fillRect(cx + 5, cy - 3, 1, 8, C_Q0);
        gfx_fillRect(cx - 3, cy - 4, 8, 1, C_Q0); gfx_fillRect(cx - 3, cy + 5, 8, 1, C_Q0);
    }
    for (int i = 0; i < NPART; i++)
        if (parts[i].life) gfx_pixel(parts[i].x >> 3, parts[i].y >> 3, parts[i].life < 5 ? C_FRAME : parts[i].col);
    snprintf(s, sizeof s, "%d", score);
    gfx_text(2, 3, s, C_TEXT);
    snprintf(s, sizeof s, "%d%%", areaPct);
    gfx_text(46, 3, s, C_TEXT);
    gfx_fillRect(OX, 11, 2 * W, 1, C_FRAME);                       // progress to the 75% target
    gfx_fillRect(OX, 11, 2 * W * areaPct / 100, 1, areaPct >= tgt() ? C_Q1 : C_FAST);
    gfx_fillRect(OX + 2 * W * tgt() / 100, 10, 1, 3, C_EDGE);
    blit8(99, 1, SPR_SHIP);                                           // lives: a ship and a count
    snprintf(s, sizeof s, "x%d", lives);
    gfx_text(109, 3, s, C_TEXT);
    snprintf(s, sizeof s, "L%d", level);
    gfx_text(70, 3, s, C_TRAIL);
    if (respawnT && state == PLAY) {                                  // a circle shrinks onto the player
        int cx = OX + 2 * px + 1, cy = OY + 2 * py + 1, r = respawnT * 3 + 5;
        uint8_t c = (respawnT & 2) ? C_EDGE : C_PLAYER;
        for (int k = 0; k < 32; k++) {
            int x0 = cx + SINT[(k + 8) & 31] * r / 64, y0 = cy + SINT[k] * r / 64;
            int x1 = cx + SINT[(k + 9) & 31] * r / 64, y1 = cy + SINT[(k + 1) & 31] * r / 64;
            int n = max(abs(x1 - x0), abs(y1 - y0));
            for (int i = 0; i <= n; i++) gfx_pixel(n ? x0 + (x1 - x0) * i / n : x0, n ? y0 + (y1 - y0) * i / n : y0, c);
        }
    }
    if (ringT) {                                                      // the shockwave
        int r = (14 - ringT) * 4 + 2;
        uint8_t c = ringT < 5 ? C_FRAME : ringCol;
        for (int k = 0; k < 24; k++) gfx_pixel(ringX + COS24[k] * r / 64, ringY + COS24[(k + 18) % 24] * r / 64, c);
    }
    if (popT) {                                                       // the points, floating up
        const char *word = popVal >= 4000 ? "AWESOME " : popVal >= 1500 ? "GREAT " : popVal >= 600 ? "NICE " : "";
        snprintf(s, sizeof s, "%s+%d", word, popVal);
        gfx_text(constrain(popX - 8, 2, 128 - gfx_textWidth(s) - 2), popY - 6 - (36 - popT) / 3, s, (popT < 10 && (popT & 1)) ? C_FRAME : C_TRAIL);
    }
    if (hitT) {                                                       // a red frame when you are hit
        gfx_fillRect(0, 0, 128, 3, C_PLAYER); gfx_fillRect(0, 125, 128, 3, C_PLAYER);
        gfx_fillRect(0, 0, 3, 128, C_PLAYER); gfx_fillRect(125, 0, 3, 128, C_PLAYER);
    }
    if (readyT && state == PLAY) {                                    // the level slides in and out
        snprintf(s, sizeof s, "LEVEL %d", level);
        int w = gfx_textWidthScaled(s, 2);
        int off = readyT > 35 ? (readyT - 35) * 12 : readyT < 10 ? -(10 - readyT) * 14 : 0;
        gfx_fillRect(0, 46, 128, 32, C_BG);
        gfx_fillRect(0, 45, 128, 1, QCOL[(frameNo >> 2) & 3]); gfx_fillRect(0, 78, 128, 1, QCOL[(frameNo >> 2) & 3]);
        gfx_textScaled((128 - w) / 2 + off, 50, s, C_EDGE, 2);
        const char *nm = ENEMY_NAMES[enemyKind()];
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
    if (state == CLEARED) {                                           // the level-clear panel
        int e = CLEAR_TIME - timer;
        int open = min(44, max(0, (e - 25) * 4));
        if (timer < 10) open = min(open, timer * 4);
        if (open > 0) {
            int x = 8, y = 56 - open / 2, w = 112;
            gfx_fillRect(x - 1, y - 1, w + 2, open + 2, QCOL[(e >> 2) & 3]);
            gfx_fillRect(x, y, w, open, C_BG);
            if (open >= 44) {
                snprintf(s, sizeof s, "LEVEL %d CLEAR!", level);
                gfx_text(x + 10, y + 5, s, QCOL[(e >> 2) & 3]);
                snprintf(s, sizeof s, "AREA %d%%", areaPct);
                gfx_text(x + 10, y + 17, s, C_TEXT);
                int shown = clearBonus * min(max(e - 70, 0), 40) / 40;
                snprintf(s, sizeof s, "BONUS +%d", shown);
                gfx_text(x + 10, y + 29, s, shown == clearBonus ? C_TRAIL : C_TEXT);
            }
        }
    }
    if (state == PAUSED) {                                            // the pause menu over the frozen picture
        static const char *const LINES[3] = { "RESUME", "SAVE GAME", "RETURN TO TITLE" };
        gfx_fillRect(8, 37, 112, 62, C_Q0);
        gfx_fillRect(9, 38, 110, 60, C_BG);
        gfx_text((128 - gfx_textWidth("PAUSED")) / 2, 42, "PAUSED", C_TRAIL);
        for (int i = 0; i < 3; i++) {
            int y = 54 + i * 10;
            if (i == pauseSel) { gfx_fillRect(12, y - 2, 104, 10, C_FRAME); gfx_text(16, y, ">", C_TRAIL); }
            gfx_text(28, y, LINES[i], i == pauseSel ? C_EDGE : C_TEXT);
        }
        if (pauseNote) gfx_text((128 - gfx_textWidth(pauseNote)) / 2, 87, pauseNote, C_Q1);
    }
    if (state == OVER) { gfx_text(won ? 44 : 40, 56, won ? "YOU WIN!" : "GAME OVER", C_TRAIL); snprintf(s, sizeof s, "HI %d", hiScore); gfx_text(44, 68, s, C_TEXT); }
    if (shakeT) {                                                     // the screen shakes
        int d = (shakeT & 1) ? 2 : -2;
        if (d > 0) memmove(gfx_fb + d * GFX_FB_STRIDE, gfx_fb, (128 - d) * GFX_FB_STRIDE);
        else memmove(gfx_fb, gfx_fb - d * GFX_FB_STRIDE, (128 + d) * GFX_FB_STRIDE);
    }
}

#ifdef CHSIM
void sim_sync();
void sim_advance(uint32_t us);
void sim_waitInput();
#endif

void setup() {
    chgame.boot();
#if CHGAME_DEBUG
    dbg::begin("CHIX 1.0");
#endif
    gfx_begin(GFX_DIV2, GFX_12BPP);
    const uint16_t pal[16] = {
        gfx_rgb(0, 0, 0), gfx_rgb(30, 70, 230), gfx_rgb(230, 130, 20), gfx_rgb(255, 255, 80),
        gfx_rgb(255, 255, 255), gfx_rgb(255, 50, 50), gfx_rgb(255, 60, 255),
        gfx_rgb(0, 255, 255), gfx_rgb(0, 255, 100), gfx_rgb(130, 175, 255), gfx_rgb(255, 205, 120),
        gfx_rgb(220, 220, 220), gfx_rgb(15, 35, 115), gfx_rgb(115, 65, 10), gfx_rgb(90, 90, 90), gfx_rgb(150, 30, 150) };
    gfx_setPalette(pal, 16);
    for (int i = 0; i < 32; i++) SINT[i] = (int8_t)lroundf(64.0f * sinf(i * 6.2831853f / 32.0f));
    audio::begin(SOUNDS, S_COUNT);
    audio::setMusic(audio::LEAD);
    audio::music(SONGS[0]);
    chgame.setFrameRate(30);
    SaveData d;
    uint8_t flag = 0;
    if (save::load(MAGIC, 1, d, &flag)) {
        hiScore = d.hi;
        if (flag == 1) { hasSave = true; sv = d; }
    }
    rng ^= millis();
    state = TITLE;
    resetField();
}

void loop() {
    static bool startPrev;
    bool st = chgame.pressed(START_BUTTON);                     // START pressed in play: the pause menu
    if (st && !startPrev) {
        if (state == PLAY) { state = PAUSED; pauseSel = 0; pauseNote = nullptr; }
        else if (state == PAUSED) state = PLAY;
    }
    startPrev = st;
    dbg::markRenderStart();
    update();
    audio::update();
    gfx_wait();
    if (saveDue) {
        saveDue = false;
        save::store(MAGIC, 1, sv, saveFlag ? 1 : 0);
        hasSave = saveFlag && save::available();
        if (hasSave) titleSel = 0;
    }
    draw();
    dbg::markRenderEnd();
    gfx_flushAsync();
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
