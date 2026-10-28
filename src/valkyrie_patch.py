"""Port the English text of The Legend of Valkyrie from the PS1 "Namco Museum Vol. 5"
(VALKYRIE.EXE) into the arcade Valkyrie no Densetsu main program ROMs (wd1mpr0/wd1mpr1).

Text format (both versions): 16-bit words; 0x20-0x7e ASCII tiles, 0xa1-0xdf kana, 0x0d newline,
0x100+ custom glyphs, 0xffff end. The arcade is big-endian, the PS1 little-endian.
"""
import struct

PB = 0x80010200 - 0x800          # PS1 file offset -> RAM address delta

# free ROM regions in the arcade 68k program (verified 0xff fill)
FREE = [(0x2dfa0, 0x30000), (0x36380, 0x38000)]

log = []


def L(s):
    log.append(s)


class Arcade:
    """68k main program = wd1mpr0 (even bytes) interleaved with wd1mpr1 (odd bytes)."""

    def __init__(self, even, odd):
        self.b = bytearray(x for pr in zip(even, odd) for x in pr)
        self.free = [list(r) for r in FREE]

    def u32(self, a):
        return struct.unpack('>I', self.b[a:a + 4])[0]

    def w32(self, a, v):
        self.b[a:a + 4] = struct.pack('>I', v)

    def alloc(self, n):
        n = (n + 1) & ~1
        for r in self.free:
            if r[1] - r[0] >= n:
                a = r[0]
                r[0] += n
                return a
        raise RuntimeError('out of free ROM space (need %d bytes)' % n)

    def put(self, data):
        a = self.alloc(len(data))
        assert all(x == 0xff for x in self.b[a:a + len(data)]), hex(a)
        self.b[a:a + len(data)] = data
        return a

    def split(self):
        return bytes(self.b[0::2]), bytes(self.b[1::2])


class PS:
    """PS1 VALKYRIE.EXE (file offsets; PB converts to RAM addresses)."""

    def __init__(self, exe):
        self.b = exe

    def u32(self, o):
        return struct.unpack('<I', self.b[o:o + 4])[0]

    def off(self, addr):
        return addr - PB

    def words(self, o):
        """read 0xffff-terminated word string at file offset o"""
        w = []
        while True:
            x = struct.unpack('<H', self.b[o:o + 2])[0]
            w.append(x)
            o += 2
            if x == 0xffff:
                return w

    def screen_entry(self, o):
        """count, then count x (col, row, string..., 0xffff)"""
        return read_entry(lambda q: struct.unpack('<H', self.b[q:q + 2])[0], o)[0]


def read_entry(rd, o):
    """returns (words, end_offset) for a screen entry"""
    n = rd(o)
    assert 1 <= n <= 8, 'bad entry count %x at %x' % (n, o)
    w = [n]
    o += 2
    for _ in range(n):
        w += [rd(o), rd(o + 2)]
        o += 4
        while True:
            x = rd(o)
            w.append(x)
            o += 2
            if x == 0xffff:
                break
    return w, o


def be(words):
    return b''.join(struct.pack('>H', w) for w in words)


def check_chars(words, where):
    bad = [w for w in words if not (0x20 <= w < 0x7f or w in (0x0d, 0xffff))]
    if bad:
        L('  note: non-ASCII codes in %s: %s' % (where, ' '.join('%x' % x for x in bad)))


# ---------------------------------------------------------------- speech bubbles
def patch_bubbles(A, P):
    ARC_TBL = 0x324b0      # record slot 1 (slot 0 at 0x324ac is null)
    PS_TBL = 0x7959c       # PS1 {hdr[4], pagelist*} 12-byte entries
    n = 0
    strcache = {}
    while True:
        slot = ARC_TBL + 4 * n
        rec = A.u32(slot)
        if not (0x32500 < rec < 0x33000):
            break
        e = PS_TBL + 12 * n
        hdr = struct.unpack('<4h', P.b[e:e + 8])
        pl = P.off(P.u32(e + 8))
        pages = []
        while P.u32(pl) != 0xffffffff:
            pages.append(P.off(P.u32(pl)))
            pl += 4
        ptrs = []
        for pg in pages:
            if pg not in strcache:
                w = P.words(pg)
                check_chars(w, 'bubble %d' % n)
                strcache[pg] = A.put(be(w))
            ptrs.append(strcache[pg])
        data = struct.pack('>4h', *hdr) + b''.join(struct.pack('>I', p) for p in ptrs) + b'\xff\xff\xff\xff'
        newrec = A.put(data)
        A.w32(slot, newrec)
        L('bubble %2d: rec %05x -> %05x hdr %s pages %d' % (n, rec, newrec, hdr, len(ptrs)))
        n += 1
    L('bubbles patched: %d' % n)


# ---------------------------------------------------------------- screen texts
def relocate_entry(A, P, ps_off, cache):
    if ps_off not in cache:
        w = P.screen_entry(ps_off)
        check_chars([x for x in w[1:] if x > 0x40], 'screen entry @%x' % ps_off)
        cache[ps_off] = A.put(be(w))
    return cache[ps_off]


def patch_ptr_table(A, P, arc_tbl, ps_tbl, stride, cache, name):
    """Tables of 32-bit pointers (with `stride` spacing) terminated by 0xffffffff."""
    i = 0
    while True:
        pa = P.u32(ps_tbl + i * stride)
        aa = A.u32(arc_tbl + i * stride)
        if pa == 0xffffffff:
            if aa != 0xffffffff:
                # PS1 has fewer pages: terminate arcade table here
                A.w32(arc_tbl + i * stride, 0xffffffff)
                L('  %s: terminated early at %d (arcade had more)' % (name, i))
            break
        if aa == 0xffffffff:
            raise RuntimeError('%s: PS1 has more entries than arcade table' % name)
        A.w32(arc_tbl + i * stride, relocate_entry(A, P, P.off(pa), cache))
        i += 1
    L('%s: %d entries' % (name, i))


def patch_ptr_list(A, P, arc_tbl, ps_tbl, count, stride, cache, name):
    for i in range(count):
        pa = P.u32(ps_tbl + i * stride)
        A.w32(arc_tbl + i * stride, relocate_entry(A, P, P.off(pa), cache))
    L('%s: %d entries' % (name, count))


def contiguous_entries(rd, start, count):
    """walk `count` contiguous screen entries starting at start; skip orphan (col,row,str) blocks"""
    out = []
    o = start
    while len(out) < count:
        if rd(o) == 0:          # PS1 4-byte alignment padding
            o += 2
            continue
        if 1 <= rd(o) <= 4 and rd(o + 2) < 0x40 and rd(o + 4) < 0x40:
            out.append(o)
            o = read_entry(rd, o)[1]
        else:
            o += 4
            while rd(o) != 0xffff:
                o += 2
            o += 2
    return out


def patch_screens(A, P):
    cache = {}
    # 12-byte-stride tables {ptr, 0, 0}
    for arc, ps in [(0x17b00, 0xeb3c0), (0x1bfa4, 0xed118), (0x1c53a, 0xed940), (0x1c952, 0xedd34),
                    (0x1ce46, 0xee9b8), (0x1d486, 0xeed2c), (0x1daf2, 0xefbd0)]:
        patch_ptr_table(A, P, arc, ps, 12, cache, 'screen tbl %05x' % arc)
    patch_ptr_table(A, P, 0x2cbdc, 0xf1bc8, 8, cache, 'screen tbl 2cbdc')
    patch_ptr_list(A, P, 0x2dae8, 0xf2354, 15, 4, cache, 'screen list 2dae8')
    patch_ptr_list(A, P, 0x2db1c, 0xf2388, 2, 4, cache, 'screen list 2db1c')
    patch_ptr_list(A, P, 0x1f238, 0xff8c4, 2, 4, cache, 'screen list 1f238')

    # entries referenced directly by `lea abs.l,a1` in code (0x1e8xx-0x1edxx).
    # Arcade cluster 1eec6.. and PS1 cluster ff654.. hold the same 10 entries in the same order.
    rdA = lambda o: struct.unpack('>H', A.b[o:o + 2])[0]
    rdP = lambda o: struct.unpack('<H', P.b[o:o + 2])[0]
    aent = contiguous_entries(rdA, 0x1eec6, 10)
    pent = contiguous_entries(rdP, 0xff654, 10)
    amap = dict(zip(aent, pent))
    leas = [0x1e822, 0x1e842, 0x1e862, 0x1e86e, 0x1eb18, 0x1ec02, 0x1ec8e, 0x1ec96, 0x1ed2c, 0x1ed34]
    for site in leas:
        assert A.b[site - 2:site] == b'\x43\xf9', hex(site)
        tgt = A.u32(site)
        if tgt not in amap:
            raise RuntimeError('lea target %x not in cluster walk %s' % (tgt, [hex(x) for x in aent]))
        A.w32(site, relocate_entry(A, P, amap[tgt], cache))
    L('lea sites: %d' % len(leas))
    L('screen entries relocated: %d' % len(cache))


def template_len(buf, o):
    """byte template: rows-1, then per row cols-1 + tiles (routine 0x246a6)"""
    rows = buf[o] + 1
    q = o + 1
    for _ in range(rows):
        q += buf[q] + 2
    return q - o


def patch_templates(A, P):
    """Small fixed tile-block bubbles (player replies, A/B/C choices). PS1 uses tile 0 as blank,
    the arcade uses 0x14."""
    pairs = [(0x257fa, 0x7a83c), (0x25832, 0x7a874), (0x258da, 0x7a91c),
             (0x258a2, 0x7a8e4), (0x2586a, 0x7a8ac), (0x25912, 0x7a954)]
    for ao, po in pairs:
        n = template_len(A.b, ao)
        assert template_len(P.b, po) == n, 'template size mismatch %x/%x' % (ao, po)
        src = bytearray(P.b[po:po + n])
        rows = src[0] + 1
        q = 1
        for _ in range(rows):
            c = src[q] + 1
            for k in range(q + 1, q + 1 + c):
                if src[k] == 0:
                    src[k] = 0x14
            q += c + 1
        changed = sum(1 for x, y in zip(src, A.b[ao:ao + n]) if x != y)
        A.b[ao:ao + n] = src
        L('template %05x <- ps %05x (%d bytes, %d changed)' % (ao, po, n, changed))


def patch_title(A, P, row=24, col=17):
    """PS1 keeps the arcade logo but adds an English subtitle line under it. The arcade title
    copyright is printed by 0x2b6a (called from 0x2b0e) via the menu-font printer 0x15c2
    into fixed layer F5 (36x28 words at word 0x4408, ROT90: chars advance -36 words).
    Hook the call: run the original routine, then print the PS1 subtitle."""
    PS_SUB = 0x100f4c
    w = P.words(PS_SUB)
    assert w[-1] == 0xffff and all(0x80 < x < 0xa0 or x == 0x14 for x in w[:-1]), 'unexpected subtitle'
    s = A.put(be(w))
    dst = 0x400000 + 2 * (0x4408 + row * 36 + col)
    code = (b'\x4e\xb9' + struct.pack('>I', 0x2b6a) +          # jsr  $2b6a
            b'\x41\xf9' + struct.pack('>I', dst) +             # lea  dst,a0
            b'\x43\xf9' + struct.pack('>I', s) +               # lea  str,a1
            b'\x4e\xb9' + struct.pack('>I', 0x15c2) +          # jsr  $15c2
            b'\x4e\x75')                                       # rts
    hook = A.put(code)
    assert A.b[0x2b0e:0x2b10] == b'\x4e\xb9' and A.u32(0x2b10) == 0x2b6a
    A.w32(0x2b10, hook)
    L('title subtitle: %d chars at F5 row %d col %d (%06x), hook %05x' % (len(w) - 1, row, col, dst, hook))


def patch_clear(A, P):
    """Cutscene text-area clear entry (blank lines, printed via 0x15e2 when a page is skipped).
    Arcade 0x17b4c clears 4 lines x 20 chars; English lines are up to 24, leaving stray chars.
    The PS1 widened it to 24 (0xeb12c). Use the PS1 entry and repoint every `lea $17b4c,a1`."""
    ARC, PSC = 0x17b4c, 0xeb12c
    rdA = lambda o: struct.unpack('>H', A.b[o:o + 2])[0]
    rdP = lambda o: struct.unpack('<H', P.b[o:o + 2])[0]
    aw, _ = read_entry(rdA, ARC)
    pw, _ = read_entry(rdP, PSC)
    assert aw[0] == pw[0] == 4
    new = A.put(be(pw))
    sites = [o for o in range(2, 0x30000, 2) if A.b[o - 2:o] == b'\x43\xf9' and A.u32(o) == ARC]
    for o in sites:
        A.w32(o, new)
    L('clear entry %05x -> %05x (PS1 %05x), %d lea sites' % (ARC, new, PSC, len(sites)))


def patch_typewriter(A):
    """Cutscene/ending page scheduler 0x17a48: the page table is one longword per 128-frame slot;
    a nonzero slot starts a page and the following zero slots belong to it (cutscene tables use
    {ptr,0,0}, the ending table 0x2cbdc uses {ptr,0}). The typewriter (one char / 4 frames) only
    advanced during a page's first slot -> max ~32 chars, cutting off longer English pages.
    Replace its continue-typing path (0x17aa0..0x17abc) with a call to a routine that walks back
    to the slot that started the current page and keeps typing it (same speed, any stride)."""
    SITE = 0x17aa0
    assert A.b[SITE:SITE + 6] == bytes.fromhex('024100036616'), 'unexpected code at %x' % SITE
    sub = bytes.fromhex(
        '02410003'      # andi.w #3,d1          ; every 4th frame
        '6610'          # bne.b  ret
        '3007'          # move.w d7,d0          ; slot (or slot-1)
        'e548'          # lsl.w  #2,d0
        '22330000'      # loop: move.l (a3,d0.w),d1
        '6b06'          # bmi.b  ret            ; -1 = end of table
        '6606'          # bne.b  found          ; slot that started this page
        '5940'          # subq.w #4,d0
        '6af4'          # bpl.b  loop
        '4e75'          # ret: rts
        '41f900408810'  # found: lea $408810,a0
        '2241'          # movea.l d1,a1
        '4eb9000185f0'  # jsr    $185f0         ; typewriter step (no-op once page is done)
        '4e75')         # rts
    new = A.put(sub)
    A.b[SITE:SITE + 8] = bytes.fromhex('4eb9') + struct.pack('>I', new) + bytes.fromhex('6014')   # jsr new; bra.b $17abc
    L('typewriter: 0x17aa0 -> jsr %05x (types for the whole page, any table stride)' % new)


def patch_quiz(A):
    """Gatekeeper quiz NPC (0x27236) enters answer-select mode once its bubble reaches page
    offset 0x10 (3rd page), freezing the bubble there. The PS1 castle quiz (record 63) splits the
    question and the A/B/C choices over pages 3 and 4, so the choices never appeared. Test for
    "current page is the last one" instead (identical for 3-page records)."""
    SITE = 0x27236
    assert A.b[SITE:SITE + 8] == bytes.fromhex('0c6800100074671a'), 'unexpected code at %x' % SITE
    sub = bytes.fromhex(
        '2f09'                  # move.l  a1,-(sp)
        '22680060'              # movea.l $60(a0),a1     ; bubble record
        'd2e80074'              # adda.w  $74(a0),a1     ; + current page offset
        '0ca9ffffffff0004'      # cmpi.l  #-1,4(a1)      ; next page = end?
        '225f'                  # movea.l (sp)+,a1
        '4e75')                 # rts
    new = A.put(sub)
    A.b[SITE:SITE + 6] = b'\x4e\xb9' + struct.pack('>I', new)       # jsr new; (beq.b follows)
    L('quiz: 0x27236 -> jsr %05x (choices on last bubble page)' % new)


def patch_quiz_mammoth(A):
    """Mammoth quiz NPC (0x2b0ec, bubble 0x11 = record 16) spawns its bubble in hold mode and
    starts the A/B/C selection as soon as page 1 ends. The arcade had question + choices on one
    page; the PS1 splits them over 2 pages, so the choices never appeared. While the bubble is
    not on its last page, advance it (state 4 = advance one page then hold, forced by expiring
    the current page) and keep waiting."""
    SITE = 0x2b114
    assert A.b[SITE:SITE + 8] == bytes.fromhex('0c2e000200326714'), 'unexpected code at %x' % SITE
    sub = bytes.fromhex(
        '0c2e00020032'          # cmpi.b  #2,$32(a6)     ; bubble finished a page?
        '662a'                  # bne.b   ret            ; Z=0: keep waiting
        '2f08'                  # move.l  a0,-(sp)
        '2f09'                  # move.l  a1,-(sp)
        '206e0064'              # movea.l $64(a6),a0     ; bubble
        '22680060'              # movea.l $60(a0),a1     ; bubble record
        'd2e80074'              # adda.w  $74(a0),a1     ; + current page offset
        '0ca9ffffffff0004'      # cmpi.l  #-1,4(a1)      ; last page?
        '670c'                  # beq.b   out            ; Z=1: start selection
        '117c00040032'          # move.b  #4,$32(a0)     ; advance one page, then hold
        '3168007e005a'          # move.w  $7e(a0),$5a(a0); expire current page now (Z=0)
        '225f'                  # out: movea.l (sp)+,a1
        '205f'                  # movea.l (sp)+,a0
        '4e75')                 # ret: rts
    new = A.put(sub)
    A.b[SITE:SITE + 6] = bytes.fromhex('4eb9') + struct.pack('>I', new)       # jsr new; (beq.b follows)
    L('quiz: 0x2b114 -> jsr %05x (mammoth choices on last bubble page)' % new)


def patch(even, odd, exe):
    """Apply all patches. Returns (new_even, new_odd, log_lines)."""
    del log[:]
    A = Arcade(even, odd)
    P = PS(exe)
    patch_bubbles(A, P)
    patch_screens(A, P)
    patch_templates(A, P)
    patch_title(A, P)
    patch_clear(A, P)
    patch_typewriter(A)
    patch_quiz(A)
    patch_quiz_mammoth(A)
    for r in A.free:
        L('free left: %05x-%05x (%d bytes)' % (r[0], r[1], r[1] - r[0]))
    e, o = A.split()
    return e, o, list(log)
