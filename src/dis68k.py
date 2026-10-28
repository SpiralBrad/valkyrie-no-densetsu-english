"""Disassemble the (interleaved) arcade 68k program. Needs `pip install capstone`.

usage: python src/dis68k.py ROMDIR START END     (hex addresses; ROMDIR holds wd1mpr0/1.bin)
"""
import os, sys
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000

d, s, e = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
even = open(os.path.join(d, 'wd1mpr0.bin'), 'rb').read()
odd = open(os.path.join(d, 'wd1mpr1.bin'), 'rb').read()
code = bytes(x for p in zip(even, odd) for x in p)
md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
for ins in md.disasm(code[s:e], s):
    print('%06x: %-8s %s' % (ins.address, ins.mnemonic, ins.op_str))
