"""Minimal IPS patch create/apply.

usage: ips.py create original patched out.ips
       ips.py apply  original patch.ips out
"""
import sys


def create(a, b):
    assert len(a) == len(b)
    out = bytearray(b'PATCH')
    i = 0
    while i < len(a):
        if a[i] == b[i]:
            i += 1
            continue
        j = i
        # merge runs separated by small equal gaps
        while j < len(a) and j - i < 0xffff:
            if a[j] != b[j]:
                j += 1
                continue
            k = j
            while k < len(a) and a[k] == b[k] and k - j < 6:
                k += 1
            if k < len(a) and k - j < 6 and a[k] != b[k] and k - i < 0xffff:
                j = k
            else:
                break
        assert i != 0x454f46  # 'EOF' offset collision
        out += i.to_bytes(3, 'big') + (j - i).to_bytes(2, 'big') + b[i:j]
        i = j
    out += b'EOF'
    return bytes(out)


def apply(a, p):
    assert p[:5] == b'PATCH', 'not an IPS file'
    o = bytearray(a)
    i = 5
    while p[i:i + 3] != b'EOF':
        off = int.from_bytes(p[i:i + 3], 'big')
        n = int.from_bytes(p[i + 3:i + 5], 'big')
        i += 5
        if n == 0:                                   # RLE record
            n = int.from_bytes(p[i:i + 2], 'big')
            o[off:off + n] = p[i + 2:i + 3] * n
            i += 3
        else:
            o[off:off + n] = p[i:i + n]
            i += n
    return bytes(o)


if __name__ == '__main__':
    cmd, x, y, z = sys.argv[1:5]
    rd = lambda f: open(f, 'rb').read()
    data = create(rd(x), rd(y)) if cmd == 'create' else apply(rd(x), rd(y))
    open(z, 'wb').write(data)
    print('wrote', z)
