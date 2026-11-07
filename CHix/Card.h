// CHIX.DAT on the SD card (Card.cpp): the stage pictures, read a 512 B block at a time into CHGfx's scratch buffer.
// Every call reads the card over SPI1, which the panel shares: call them only between gfx_wait() and gfx_flushAsync().
#pragma once
#include <stdint.h>
#include <SdSpi.h>

namespace card {
bool open();                          // finds and checks the file; false: no card, no file or the wrong one
bool ok();                            // the file is open
void frame();                         // after gfx_wait(), each frame: the scratch buffer is stale
const uint8_t *block(uint32_t k);     // block k of the file, valid until the next call or the next flush (nullptr: the card has gone)
bool stream(uint32_t k, uint32_t n, uint8_t *buf1, sd::BlockFn fn, void *ctx);   // blocks k..k+n-1 in one multi-block read by DMA,
                                      // each to fn while the next arrives (buf0 is the scratch buffer; false: the card has gone)
bool getSave(uint8_t *dst, uint8_t n);   // the save mirror (two alternating records after CARD_SET): the newest good one; false: none
bool putSave(const uint8_t *p, uint8_t n);   // writes the next record (n <= 64, a few ms; after gfx_wait()); false: not kept
}  // namespace card
