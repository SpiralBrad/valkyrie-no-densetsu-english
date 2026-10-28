"""Sanity checks on a patched program ROM pair (catches the classes of bugs found in playtesting).

usage: python src/audit.py OUTDIR      (directory holding the built wd1mpr0.bin / wd1mpr1.bin)

- every speech-bubble page can finish typing within its display time (1 char / 4 frames)
- every cutscene/ending page can finish typing before the next page (128-frame slots)
- every cutscene/ending line fits inside the 24-column area that is cleared between pages
"""
import os, struct, sys

d = sys.argv[1] if len(sys.argv) > 1 else 'out'
e = open(os.path.join(d, 'wd1mpr0.bin'), 'rb').read()
o = open(os.path.join(d, 'wd1mpr1.bin'), 'rb').read()
M = bytes(x for p in zip(e, o) for x in p)
u = lambda a: struct.unpack('>I', M[a:a + 4])[0]
w = lambda a: struct.unpack('>H', M[a:a + 2])[0]

BUBBLES = 0x324b0
PAGE_TABLES = [0x17b00, 0x1bfa4, 0x1c53a, 0x1c952, 0x1ce46, 0x1d486, 0x1daf2, 0x2cbdc]
CLEAR_COLS = (4, 28)            # clear entry covers columns 4..27

problems = 0


def bad(msg):
    global problems
    problems += 1
    print('  ' + msg)


def string(a):
    s = []
    while w(a) != 0xffff:
        s.append(w(a))
        a += 2
    return s


print('speech bubbles')
for n in range(66):
    rec = u(BUBBLES + 4 * n)
    dur = struct.unpack('>h', M[rec + 6:rec + 8])[0]
    q, page = rec + 8, 0
    while u(q) != 0xffffffff:
        k = len(string(u(q)))
        if k * 4 > dur:
            bad('record %d page %d: %d chars need %d frames, shown %d' % (n, page, k, k * 4, dur))
        q, page = q + 4, page + 1

print('cutscene / ending pages')
for t in PAGE_TABLES:
    slots = []
    while not slots or slots[-1] != 0xffffffff:
        slots.append(u(t + 4 * len(slots)))
    starts = [i for i, v in enumerate(slots) if v not in (0, 0xffffffff)]
    for j, i in enumerate(starts):
        nxt = starts[j + 1] if j + 1 < len(starts) else len(slots) - 1
        a = slots[i]
        chars = 0
        count, a = w(a), a + 2          # count, then count x (col, row, string, 0xffff)
        for _ in range(count):
            col = w(a)
            s = string(a + 4)
            chars += len(s)
            width = 0
            for x in s + [0x0d]:
                if x == 0x0d:
                    if col < CLEAR_COLS[0] or col + width > CLEAR_COLS[1]:
                        bad('table %05x page %d: line at col %d, %d wide, outside cleared area'
                            % (t, j, col, width))
                    width = 0
                else:
                    width += 1
            a += 4 + 2 * len(s) + 2
        if chars > (nxt - i) * 32:
            bad('table %05x page %d: %d chars, only %d typing steps' % (t, j, chars, (nxt - i) * 32))

print('%d problem(s)' % problems)
sys.exit(1 if problems else 0)
