"""Minimal reader for a MODE2/2352 raw CD image (ISO9660).

Handles Mode 2 Form 1 (2048 bytes at offset 24) and Form 2 (2324 bytes at offset 24).
"""
import struct
import sys

SECTOR = 2352


class CDImage:
    def __init__(self, path):
        self.f = open(path, "rb")
        self.f.seek(0, 2)
        self.size = self.f.tell()
        self.sectors = self.size // SECTOR

    def read_sector(self, lba):
        self.f.seek(lba * SECTOR)
        return self.f.read(SECTOR)

    def read_mode2(self, lba):
        s = self.read_sector(lba)
        if len(s) < SECTOR:
            return b""
        # subheader byte 2 lower bits: bit 5 set => Form 2 (2324 data bytes)
        sub = s[18]
        if sub & 0x20:
            return s[24:24 + 2324]
        return s[24:24 + 2048]

    def read_bytes(self, lba, length):
        out = bytearray()
        while len(out) < length:
            out += self.read_mode2(lba)
            lba += 1
        return bytes(out[:length])


def parse_dir(data):
    entries = []
    i = 0
    while i < len(data):
        reclen = data[i]
        if reclen == 0:
            # move to next sector boundary (2048)
            i = ((i // 2048) + 1) * 2048
            continue
        rec = data[i:i + reclen]
        ext_attr_len = rec[1]
        lba = struct.unpack("<I", rec[2:6])[0]
        size = struct.unpack("<I", rec[10:14])[0]
        flags = rec[25]
        name_len = rec[32]
        name = rec[33:33 + name_len]
        if name_len == 1 and name[0] in (0, 1):
            pass
        else:
            entries.append((name.decode("latin-1"), lba, size, flags))
        i += reclen
    return entries


def walk(img, lba, size, prefix="", depth=0, maxdepth=10):
    data = img.read_bytes(lba, size)
    for name, elba, esize, flags in parse_dir(data):
        path = prefix + "/" + name if prefix else name
        print(f"{esize:12d}  {path}" + ("/" if flags & 2 else ""))
        if flags & 2 and depth < maxdepth:
            walk(img, elba, esize, path, depth + 1)


if __name__ == "__main__":
    img = CDImage(sys.argv[1])
    pvd = img.read_mode2(16)
    print("PVD type:", pvd[0], "id:", pvd[1:6])
    root = pvd[156:156 + 34]
    rlba = struct.unpack("<I", root[2:6])[0]
    rsize = struct.unpack("<I", root[10:14])[0]
    print("root lba", rlba, "size", rsize)
    walk(img, rlba, rsize)
