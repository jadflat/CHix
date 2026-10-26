"""CHix: what the shared CHGame tools need to know (`cl run` and `cl gif` read this)."""

# One framebuffer row a DMA chunk (CHGfx's default is 2): about 500 B of RAM back; measured at 20 ms a frame on the board.
DEFINES = ["GFX_CHUNK_ROWS=1"]
TESTS = {}
