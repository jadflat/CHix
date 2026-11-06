"""CHix: what the shared CHGame tools need to know (`cl run` and `cl gif` read this)."""

# One framebuffer row a DMA chunk (CHGfx's default is 2): about 500 B of RAM back; measured at 20 ms a frame on the board.
DEFINES = ["GFX_CHUNK_ROWS=1"]
TESTS = {}

# Every script needs CHIX.DAT (the stage pictures are on the SD card): ../tools/make_card.py writes it.
import os
_here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join("CHix", "tools")
CARD = dict(scripts="", file="sdcard/CHIX.DAT", build=["python", os.path.join(_here, "..", "..", "tools", "make_card.py")])
