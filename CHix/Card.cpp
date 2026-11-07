// CHIX.DAT (Card.h): block 0 holds "CHIXCARD" and the build's hash (CardIndex.h, written with the file by
// tools/make_card.py), so a card from another build is refused. One 512 B block at a time is read into CHGfx's
// scratch buffer (free while a frame is drawn); the game draws a stage picture a block of rows at a time.
#include <CHGame.h>
#include <Fat.h>
#include <SdSpi.h>
#ifndef CHSIM
#include <Arduino.h>                                // SPI1, GPIOx for the save mirror's block write (below)
#else
#include <stdio.h>
#include <stdlib.h>
#endif
#include "Card.h"
#include "CardIndex.h"

namespace card {

static uint16_t tag = 0xffff;                     // the block now in the scratch buffer
static fat::Run runs[4];
static uint8_t nRuns;
static bool open_;
static bool noWrite;                              // a save-mirror write failed: no more tries until the card is opened again

// CHIX.DAT's place on the card, found without CHSd's general FAT code (only its block reads): the first FAT16 or FAT32
// volume (at LBA 0, or the MBR's first partition), the file in its root, in up to four runs. A card that is not like
// that simply finds no file; the header check below catches the rest. About half the size of fat::open().
static uint32_t fatLba, dataLba;
static uint8_t shift;
static bool f32;
static uint32_t rd16(const uint8_t *p) { return p[0] | (uint32_t)p[1] << 8; }
static uint32_t rd32(const uint8_t *p) { return rd16(p) | rd16(p + 2) << 16; }
static uint32_t clus(uint32_t c) { return dataLba + ((c - 2) << shift); }
static uint32_t nextC(uint32_t c, uint8_t *b) {                 // the cluster after c, 0 at the end (or on a read error)
    const uint32_t off = c << (f32 ? 2 : 1);
    if (!sd::read(fatLba + (off >> 9), b)) return 0;
    const uint32_t n = f32 ? rd32(b + (off & 511)) & 0x0FFFFFFFu : rd16(b + (off & 511));
    return n >= (f32 ? 0x0FFFFFF8u : 0xFFF8u) ? 0 : n;
}
static uint8_t findDat(uint8_t *b) {
    uint32_t base = 0;
    if (!sd::init() || !sd::read(0, b)) return 0;
    if (b[0] != 0xEB && b[0] != 0xE9 && !sd::read(base = rd32(b + 454), b)) return 0;   // an MBR: its first partition
    uint32_t fsz = rd16(b + 22);
    f32 = !fsz;
    if (f32) fsz = rd32(b + 36);
    for (shift = 0; (1u << shift) < b[13]; shift++) {}
    fatLba = base + rd16(b + 14);
    const uint32_t rootSecs = (rd16(b + 17) + 15) >> 4, rootLba = fatLba + b[16] * fsz;
    dataLba = rootLba + rootSecs;
    uint32_t dir = rd32(b + 44), sec = 0;
    for (uint32_t guard = 4096; guard--;) {
        uint32_t lba;
        if (!f32) { if (sec == rootSecs) return 0; lba = rootLba + sec; }
        else { if (sec >> shift) { if ((dir = nextC(dir, b)) < 2) return 0; sec = 0; } lba = clus(dir) + sec; }
        sec++;
        if (!sd::read(lba, b)) return 0;
        for (const uint8_t *d = b; d < b + 512; d += 32) {
            if (!d[0]) return 0;
            if (d[0] == 0xE5 || (d[11] & 0x1A) || memcmp(d, "CHIX    DAT", 11)) continue;
            uint32_t c = rd16(d + 26) | (f32 ? rd16(d + 20) << 16 : 0), left = (rd32(d + 28) + 511) >> 9;
            uint8_t n = 0;
            while (left) {
                if (c < 2) return 0;
                const uint32_t at = clus(c), k = left < (1u << shift) ? left : (1u << shift);
                if (n && runs[n - 1].lba + runs[n - 1].blocks == at) runs[n - 1].blocks += k;
                else { if (n == 4) return 0; runs[n].lba = at; runs[n].blocks = k; n++; }
                left -= k;
                if (left) c = nextC(c, b);
            }
            return n;
        }
    }
    return 0;
}
__attribute__((noinline)) static uint32_t lbaOf(uint32_t k) {          // the card block of the file's block k (0: none; the file is never at block 0)
    for (uint8_t i = 0; i < nRuns; i++) { if (k < runs[i].blocks) return runs[i].lba + k; k -= runs[i].blocks; }
    return 0;
}
static bool readBlk(uint32_t k, uint8_t *dst) {
    const uint32_t lba = lbaOf(k);
    return lba && sd::read(lba, dst);
}

bool open() {
    uint8_t *b = gfx_chunkScratch();
    tag = 0xffff;
    noWrite = false;
    nRuns = findDat(b);
    open_ = nRuns && readBlk(0, b) && !memcmp(b, "CHIXCARD", 8) && !memcmp(b + 8, &CARD_HASH, 4);
    return open_;
}

bool ok() { return open_; }

void frame() { tag = 0xffff; }

bool stream(uint32_t k, uint32_t n, uint8_t *buf1, sd::BlockFn fn, void *ctx) {
    if (!open_) return false;
    tag = 0xffff;                                               // the scratch buffer is buf0
    for (uint8_t i = 0; i < nRuns && n; i++) {                 // (split where the file is split on the card)
        if (k >= runs[i].blocks) { k -= runs[i].blocks; continue; }
        const uint32_t m = n < runs[i].blocks - k ? n : runs[i].blocks - k;
        if (!sd::stream(runs[i].lba + k, m, gfx_chunkScratch(), buf1, fn, ctx)) { open_ = false; return false; }
        n -= m; k = 0;
    }
    return n == 0;
}

const uint8_t *block(uint32_t k) {
    if (!open_) return nullptr;
    uint8_t *b = gfx_chunkScratch();
    if (tag != (uint16_t)k) {
        tag = 0xffff;
        if (!readBlk(k, b)) { open_ = false; return nullptr; }
        tag = (uint16_t)k;
    }
    return b;
}

// ---- writes: the library's driver only reads, so the save mirror's blocks are written here: a single-block write (CMD24) on the same SPI1
// set-up as SdSpi.cpp (HypeRunner's clean-room driver, MIT; the helpers below are cut down from it). It touches only a block inside the file's
// own cluster runs, and only one that still holds the 0xFF fill or an earlier record.
#ifdef CHSIM
// the simulator's card is read-only (CHSd/host/sd_host.cpp): with $CHIX_CARDW set the block goes into the file $CHSD_CARD names
// (a plain file: the DAT itself), for the tests; otherwise the write is refused
static bool writeBlk(uint32_t k, const uint8_t *src) {
    const char *path = getenv("CHIX_CARDW") ? getenv("CHSD_CARD") : nullptr;
    FILE *f = path ? fopen(path, "r+b") : nullptr;
    const bool ok = f && !fseek(f, (long)k * 512, SEEK_SET) && fwrite(src, 1, 512, f) == 512;
    if (f) fclose(f);
    return ok;
}
#else
static const uint32_t SPE = 1u << 6, RXNE = 1u << 0, BSY = 1u << 7;
__attribute__((noinline)) static uint8_t xfer(uint8_t b) {
    SPI1->DATAR = b;
    while (!(SPI1->STATR & RXNE)) {}
    return (uint8_t)SPI1->DATAR;
}
__attribute__((noinline)) static void spiSet(uint32_t c1) {
    while (SPI1->STATR & BSY) {}
    SPI1->CTLR1 = (uint16_t)(c1 & ~SPE);
    SPI1->CTLR1 = (uint16_t)c1;
}
__attribute__((noinline)) static uint8_t cmd(uint8_t c, uint32_t arg) {       // as SdSpi.cpp's: the CRC is off since sd::init()
    xfer(0xFF);
    xfer((uint8_t)(0x40 | c));
    for (int sh = 24; sh >= 0; sh -= 8) xfer((uint8_t)(arg >> sh));
    xfer(0x95);
    uint8_t r;
    uint32_t k = 9;
    do r = xfer(0xFF); while ((r & 0x80) && --k);
    return r;
}
static bool writeBlk(uint32_t k, const uint8_t *src) {
    const uint32_t lba = lbaOf(k);
    if (!lba) return false;
    GPIOA->BSHR = 1u << 4;                          // SdSpi.cpp's claim(): the panel deselected, SPI1 mode 0 at 12 MHz, the card selected
    const uint16_t lcdCtlr1 = (uint16_t)SPI1->CTLR1;
    spiSet((1u << 2) | (1u << 8) | (1u << 9) | SPE | (1u << 3));
    (void)SPI1->DATAR;
    (void)SPI1->STATR;
    GPIOB->BCR = 1u << 11;
    bool ok = !cmd(58, 0);                // READ_OCR: bit 30 = block addressing, as sd::init() reads it
    if (ok) {
        uint32_t ocr = 0;
        for (int i = 0; i < 4; i++) ocr = (ocr << 8) | xfer(0xFF);
        ok = !cmd(24, (ocr >> 30 & 1) ? lba : lba << 9);
    }
    if (ok) {
        for (int i = -1; i < 514; i++) xfer(i < 0 ? 0xFE : i < 512 ? src[i] : 0xFF);   // the token, the data, the CRC (unchecked)
        ok = (xfer(0xFF) & 0x1F) == 0x05;            // "data accepted"; the card is busy programming until the read-back's wait(false) sees it done (SdSpi.cpp, 1 s at most)
    }
    GPIOB->BSHR = 1u << 11;                         // SdSpi.cpp's release()
    xfer(0xFF);
    spiSet(lcdCtlr1);
    return ok;
}
#endif

// ---- the save mirror: the two blocks after CARD_SET hold the whole save (SaveData + its flag) as two alternating records, each with a
// generation and a checksum, so a torn write leaves the other one; getSave() restores a save the flash page lost. A block: gen (4, LE),
// 'S', n, n payload bytes, 2 checksum bytes, the 0xFF fill. A block is only written if it holds the fill or a record (the file's own).
static uint32_t gen_; static uint8_t next_;
static uint16_t sum(const uint8_t *r, uint8_t n) { uint16_t s = 0; for (uint8_t i = 0; i < n + 6; i++) s = (uint16_t)(s * 31 + r[i] + 1); return s; }
static bool good(const uint8_t *r, uint8_t n) { return r[4] == 'S' && r[5] == n && sum(r, n) == (uint16_t)(r[6 + n] | r[7 + n] << 8); }
static const uint32_t SAVE0 = CARD_SET >> 9;

bool getSave(uint8_t *dst, uint8_t n) {             // the newest good record's n bytes into dst; false: none (or no card)
    bool got = false;
    gen_ = 0; next_ = 0;
    for (uint8_t k = 0; open_ && k < 2; k++) {
        const uint8_t *r = gfx_chunkScratch();
        tag = 0xffff;
        if (!readBlk(SAVE0 + k, gfx_chunkScratch()) || !good(r, n)) continue;
        const uint32_t g = r[0] | r[1] << 8 | (uint32_t)r[2] << 16 | (uint32_t)r[3] << 24;
        if (!got || g > gen_) { gen_ = g; next_ = k ^ 1; memcpy(dst, r + 6, n); got = true; }
    }
    return got;
}

__attribute__((noinline)) bool putSave(const uint8_t *p, uint8_t n) {   // n <= 64; after gfx_wait(), before the flush; false: not kept (silently: the flash has it)
    if (!open_ || noWrite) return false;
    uint8_t *b = gfx_chunkScratch(), r[72];
    const uint32_t blk = SAVE0 + next_;
    tag = 0xffff;
    bool ok = readBlk(blk, b) && (b[4] == 'S' || (b[0] & b[1] & b[2] & b[3]) == 0xFF);
    if (ok) {
        const uint32_t g = ++gen_;
        for (uint8_t i = 0; i < 4; i++) r[i] = (uint8_t)(g >> 8 * i);
        r[4] = 'S'; r[5] = n; memcpy(r + 6, p, n);
        const uint16_t s = sum(r, n);
        r[6 + n] = (uint8_t)s; r[7 + n] = (uint8_t)(s >> 8);
        memset(b, 0xFF, 512); memcpy(b, r, n + 8);
        ok = writeBlk(blk, b) && readBlk(blk, b) && !memcmp(b, r, n + 8);
    }
    if (ok) next_ ^= 1; else { noWrite = true; open_ = sd::init(); }
    return ok;
}

}  // namespace card
