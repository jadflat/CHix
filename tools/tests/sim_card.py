"""CHix's save mirror in the simulator (Card.cpp putSave/getSave): every save is also written to the DAT's two last blocks
(CARD_SET, +512) as alternating records (generation, checksum); the newest good record restores a lost flash save; a block that
is neither the fill nor a record is never written; a bad record is ignored.

python tools/tests/sim_card.py   (from CHix; works on a copy of CHix/sdcard/CHIX.DAT)
The simulator's card is read-only unless $CHIX_CARDW is set; this test sets it for the sessions that should write.
"""
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "chgame" / "tools" / "chsim"))
from simsave import Session  # noqa: E402

SET = int(re.search(r"CARD_SET = (\d+)", (ROOT / "CHix" / "CardIndex.h").read_text()).group(1))
FILL = bytes([255]) * 512
tmp = Path(tempfile.mkdtemp())
card = tmp / "CHIX.DAT"
os.environ["CHSD_CARD"] = str(card)
fails = 0


def check(ok, what):
    global fails
    print(("ok   " if ok else "FAIL ") + what, flush=True)
    fails += not ok


def block(k=0):
    with open(card, "rb") as f:
        f.seek(SET + 512 * k)
        return f.read(512)


def put(b, k=0):
    with open(card, "r+b") as f:
        f.seek(SET + 512 * k)
        f.write(b)


def rec(b):                                                # (gen, payload) of a good record, else None
    if b[4:5] != b"S": return None
    n = b[5]; t = 0
    for x in b[:n + 6]: t = (t * 31 + x + 1) & 0xFFFF
    return (int.from_bytes(b[:4], "little"), b[6:6 + n]) if t == b[6 + n] | b[7 + n] << 8 and b[8 + n:] == bytes([255]) * (504 - n) else None


def state(s):
    return dict(w.split("=", 1) for w in (s.say("A") or "").split() if "=" in w)


def session(write):
    if write:
        os.environ["CHIX_CARDW"] = "1"
    else:
        os.environ.pop("CHIX_CARDW", None)
    s = Session(ROOT / "CHix")
    s.frames(10)
    return s


def reset():
    shutil.copyfile(ROOT / "CHix" / "sdcard" / "CHIX.DAT", card)


reset()
size0 = card.stat().st_size
check(block(0) == FILL and block(1) == FILL, "the fresh DAT save blocks are all 0xFF (block at %d)" % SET)

# 1. a save is written 20 frames later, then the next one alternates
s = session(True)
check(state(s)["save"] == "0", "fresh: no save")
s.say("W 3 2 4500"); s.frames(5)
check(block(0) == FILL and block(1) == FILL, "not written before the delay is over")
s.frames(30)
r = rec(block())
check(r and r[0] == 1 and block(1) == FILL, "gen 1 in the first block (%s)" % (r and r[0]))
s.say("W 4 1 9000"); s.frames(30)
r2 = rec(block(1))
check(r2 and r2[0] == 2 and rec(block())[0] == 1, "gen 2 in the second block, gen 1 kept")
s.say("W 5 3 12000"); s.frames(30)
r3 = rec(block())
check(r3 and r3[0] == 3 and rec(block(1))[0] == 2, "gen 3 back in the first block")
check(card.stat().st_size == size0, "the DAT's size is unchanged")
s.result()

# 2. a new boot (the flash save is empty in a new process): the newest record restores it
s = session(False)
st = state(s)
check(st["save"] == "1" and st["level"] == "5" and st["lives"] == "3" and st["score"] == "12000", "boot: restored from the card: %s" % st)
s.result()

# 3. a torn newest record: the older one is used; both bad: ignored
b = bytearray(block())
b[6] ^= 1
put(bytes(b))
s = session(False)
st = state(s)
check(st["save"] == "1" and st["level"] == "4", "a torn newest record: the older one is used: %s" % st)
s.result()
b = bytearray(block(1)); b[6] ^= 1
put(bytes(b), 1)
s = session(False)
check(state(s)["save"] == "0", "both records bad: ignored")
s.result()

# 4. a game over (no in-game save) is mirrored too: the record says so, the high score survives
reset()
s = session(True)
s.say("W 2 1 700"); s.frames(30)
s.say("O"); s.frames(30)
s.result()
s = session(False)
st = state(s)
check(st["save"] == "0", "the mirrored 'no game in progress' flag: no CONTINUE")
s.result()

# 5. a block that is neither the fill nor a record is never written over
foreign = bytes(range(256)) * 2
put(foreign); put(foreign, 1)
s = session(True)
s.say("W 3 2 100"); s.frames(40)
check(block() == foreign and block(1) == foreign, "foreign blocks are left alone")
s.result()
reset()

# 6. an old DAT without the block: nothing is written, nothing breaks
with open(card, "r+b") as f:
    f.truncate(SET)
s = session(True)
s.say("W 3 2 100"); s.frames(40)
check(card.stat().st_size == SET and state(s)["save"] == "1", "a DAT without the block: size unchanged, the game goes on")
s.result()

shutil.rmtree(tmp, ignore_errors=True)
raise SystemExit(1 if fails else 0)
