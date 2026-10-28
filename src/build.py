"""Build the English arcade Valkyrie no Densetsu from your own dumps.

usage: python src/build.py ARCADE_ZIP PS1_IMAGE [-o OUTDIR]

  ARCADE_ZIP  MAME `valkyrie` romset (zip containing wd1mpr0.bin / wd1mpr1.bin)
  PS1_IMAGE   Namco Museum Vol. 5 (USA) disc: the .cue, the MODE2/2352 .bin,
              or an already-extracted VALKYRIE.EXE

Writes to OUTDIR (default: out/):
  valkyrienmv5.zip        the romset with the two program ROMs replaced
                          (rename to valkyrie.zip to run it, see README)
  wd1mpr0.bin, wd1mpr1.bin
  patch_log.txt
and the IPS patches wd1mpr0.ips / wd1mpr1.ips to the repository root.
"""
import argparse, os, re, struct, sys, zipfile, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ips
import valkyrie_patch
from cdfs import CDImage, parse_dir

ARC_CRC = {'wd1mpr0.bin': 0x94111a2e, 'wd1mpr1.bin': 0x57b5051c}
EXE_CRC = 0xeb877e29        # BIN/EXE/VALKYRIE.EXE, Namco Museum Vol. 5 (USA) SLUS-00417
ZIPNAME = 'valkyrienmv5.zip'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # IPS output
EXE_PATH = ['BIN', 'EXE', 'VALKYRIE.EXE']


def find_file(img, path):
    pvd = img.read_mode2(16)
    lba, size = struct.unpack('<I', pvd[158:162])[0], struct.unpack('<I', pvd[166:170])[0]
    for part in path:
        for name, elba, esize, flags in parse_dir(img.read_bytes(lba, size)):
            if name.split(';')[0].upper() == part:
                lba, size = elba, esize
                break
        else:
            raise SystemExit('%s not found on disc' % '/'.join(path))
    return img.read_bytes(lba, size)


def load_exe(path):
    if path.lower().endswith('.cue'):
        m = re.search(r'FILE\s+"([^"]+)"', open(path, encoding='latin-1').read())
        if not m:
            raise SystemExit('no FILE entry in %s' % path)
        d, name = os.path.dirname(path), os.path.basename(m.group(1).replace('\\', '/'))
        path = os.path.join(d, name)
        if not os.path.exists(path):        # cue written on another OS: match case-insensitively
            hits = [f for f in os.listdir(d or '.') if f.lower() == name.lower()]
            if not hits:
                raise SystemExit('%s: track file "%s" not found' % (path, name))
            path = os.path.join(d, hits[0])
    if path.lower().endswith('.exe'):
        return open(path, 'rb').read()
    return find_file(CDImage(path), EXE_PATH)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('arcade_zip')
    ap.add_argument('ps1_image')
    ap.add_argument('-o', '--outdir', default='out')
    a = ap.parse_args()

    with zipfile.ZipFile(a.arcade_zip) as z:
        rom = {n: z.read(n) for n in ARC_CRC}
    for n, crc in ARC_CRC.items():
        if zlib.crc32(rom[n]) != crc:
            raise SystemExit('%s: CRC %08x, expected %08x (need the original valkyrie set)'
                             % (n, zlib.crc32(rom[n]), crc))
    exe = load_exe(a.ps1_image)
    if zlib.crc32(exe) != EXE_CRC:
        raise SystemExit('VALKYRIE.EXE: CRC %08x, expected %08x (need Namco Museum Vol. 5 USA)'
                         % (zlib.crc32(exe), EXE_CRC))

    even, odd, log = valkyrie_patch.patch(rom['wd1mpr0.bin'], rom['wd1mpr1.bin'], exe)
    new = {'wd1mpr0.bin': even, 'wd1mpr1.bin': odd}

    os.makedirs(a.outdir, exist_ok=True)
    out = lambda f: os.path.join(a.outdir, f)
    for n, data in new.items():
        open(out(n), 'wb').write(data)
        open(os.path.join(ROOT, n[:-4] + '.ips'), 'wb').write(ips.create(rom[n], data))
    with zipfile.ZipFile(a.arcade_zip) as zi, zipfile.ZipFile(out(ZIPNAME), 'w', zipfile.ZIP_DEFLATED) as zo:
        for info in zi.infolist():
            zo.writestr(info.filename, new.get(info.filename) or zi.read(info.filename))
    open(out('patch_log.txt'), 'w').write('\n'.join(log) + '\n')

    print('\n'.join(l for l in log if not l.startswith('bubble ')))
    for n, data in new.items():
        print('%s  crc %08x' % (n, zlib.crc32(data)))
    print('wrote', out(ZIPNAME), 'and', ', '.join(os.path.join(ROOT, n[:-4] + '.ips') for n in new))


if __name__ == '__main__':
    main()
