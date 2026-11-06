// CHIX.DAT (Card.h): block 0 holds "CHIXCARD" and the build's hash (CardIndex.h, written with the file by
// tools/make_card.py), so a card from another build is refused. One 512 B block at a time is read into CHGfx's
// scratch buffer (free while a frame is drawn); the game draws a stage picture a block of rows at a time.
#include <CHGame.h>
#include <Fat.h>
#include <SdSpi.h>
#include "Card.h"
#include "CardIndex.h"

namespace card {

static uint16_t tag = 0xffff;                     // the block now in the scratch buffer
static fat::Run runs[4];
static uint8_t nRuns;
static bool open_;

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
static bool readBlk(uint32_t k, uint8_t *dst) {
    for (uint8_t i = 0; i < nRuns; i++) { if (k < runs[i].blocks) return sd::read(runs[i].lba + k, dst); k -= runs[i].blocks; }
    return false;
}

bool open() {
    uint8_t *b = gfx_chunkScratch();
    tag = 0xffff;
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

}  // namespace card
