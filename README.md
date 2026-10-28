# The Legend of Valkyrie: arcade English translation (from Namco Museum Vol. 5)

An English patch for the arcade game **Valkyrie no Densetsu** (Namco, 1989), the MAME / FBNeo set
`valkyrie`.

In 1997 Namco released the game in English on the PlayStation as part of *Namco Museum Vol. 5*,
as **The Legend of Valkyrie**. That translation is good, but it only existed on the PS1. This
project moves Namco's own English script into the original arcade ROMs, so the arcade game shows
the official translation.

The PS1 version is a port rather than emulation, but it keeps the arcade's text format. The
patch reads the English text out of the PS1 executable and relocates it into free space in the
arcade 68000 program ROM. It also adjusts the arcade code wherever the English layout differs
from the Japanese.

## What's translated

- **Speech bubbles.** All 66 dialogue records, including the PS1's larger bubble layouts.
- **Story screens.** The intro, every between-stage cutscene and the ending.
- **Quiz screens.** The quiz questions and A / B / C quiz choices.
- **Title screen.** The Japanese logo stays, with the English subtitle *"The Legend of Valkyrie"*
  under it, as on the PS1.

Code fixes the English text needed:

- **Cutscene typewriter.** The arcade only typed during the first third of a page's display time
  (about 32 characters), which cut off the longer English pages. It now types for the whole page,
  at the original speed.
- **Cutscene clear area.** The area cleared between pages is widened from 20 to 24 columns, so
  longer lines don't leave stray letters behind.
- **Quiz NPCs.** The PS1 script puts the castle gatekeeper's and mammoth's A/B/C choices on
  their own page. Both quizzes now show that page before the selection starts.

## Building the patch

No ROM or disc data is included. You need your own dumps of:

- **The arcade set** `valkyrie.zip`. Only the two program ROMs are changed:

  | File | Original CRC32 | Patched CRC32 |
  |---|---|---|
  | `wd1mpr0.bin` | `94111a2e` | `f6e93a8c` |
  | `wd1mpr1.bin` | `57b5051c` | `0f496013` |

- **Namco Museum Vol. 5 (USA)** (SLUS-00417). The `.cue`, the raw MODE2/2352 `.bin` and an
  extracted `BIN/EXE/VALKYRIE.EXE` (CRC32 `eb877e29`) all work.

You also need Python 3.8 or newer. The build only uses the standard library, so there are no
packages to install, and it runs on Windows, Linux and macOS (use `python3` where `python` is
Python 2 or missing).

```
python src/build.py valkyrie.zip "Namco Museum Vol. 5 (USA).cue"
```

Both inputs are checked by CRC first. The build writes:

- `wd1mpr0.ips` and `wd1mpr1.ips` in the repository root. These are ordinary IPS patches for the
  two program ROMs, and any IPS tool can apply them (Lunar IPS, Floating IPS, or
  `python src/ips.py apply ORIGINAL PATCH OUTPUT`).
- `out/valkyrienmv5.zip`: the full romset with the patched program ROMs.
- `out/wd1mpr0.bin` and `out/wd1mpr1.bin`: the patched ROMs on their own.
- `out/patch_log.txt`: what was patched and where.

## Running

MAME and FBNeo find a set by its file name, so `valkyrienmv5.zip` has to be named `valkyrie.zip`
to run. To keep your original set intact, put the patched copy in a folder of its own and list
that folder first in the ROM path:

```
mame valkyrie -rompath "C:\path\to\patched;C:\path\to\roms"
```

MAME reports `WRONG CHECKSUMS` for `wd1mpr0.bin` and `wd1mpr1.bin`. That's expected, and the game
runs. This was tested with MAME 0.289. Some later MAME builds also need `valkyrie.nv` and
`lh5762.6n` in the set, the same as the unpatched game does. FBNeo hasn't been tested yet, and it
may refuse sets with the wrong CRCs.

## Status and known issues

- The game has been played through to the ending on MAME, and every bug found that way is fixed
  and confirmed. Bug reports are welcome.
- One cutscene has one page fewer than the arcade original. The PS1 script does the same.
- About 1.2 KB of free space is left in the program ROM. The old Japanese script area
  (`0x325b8-0x33f82`) is now unused and can be reclaimed if more is needed.

## Source layout

| File | Purpose |
|---|---|
| `src/build.py` | Command-line build: checks inputs, patches, writes the zip, ROMs and IPS files. |
| `src/valkyrie_patch.py` | All the patches, with comments describing the arcade structures involved. |
| `src/cdfs.py` | Minimal ISO9660 reader for MODE2/2352 disc images. |
| `src/ips.py` | Creates and applies IPS patches. |
| `src/audit.py` | Checks a build for text that can't finish typing or doesn't fit the cleared area. |
| `src/dis68k.py` | 68000 disassembler for the interleaved program ROM (needs `pip install capstone`). |

### Technical notes

- **Text encoding.** 16-bit words: `0x20-0x7e` ASCII, `0xa1-0xdf` half-width kana, `0x0d`
  newline, `0x100+` custom glyphs, `0xffff` end. The arcade stores them big-endian, the PS1
  little-endian. The arcade font already has full ASCII, including lowercase.
- **Main program.** `wd1mpr0` holds the even bytes and `wd1mpr1` the odd bytes.
- **Bubble records.** The table is at `0x324b0`. Each record is a header (type, x, y, duration),
  then page pointers, then `0xffffffff`. The PS1 equivalent is at file offset `0x7959c`.
- **Story screens.** Each page table has one longword per 128-frame slot: a pointer starts a page,
  and the zero slots after it belong to that page. Cutscenes use 3 slots per page and the ending
  (`0x2cbdc`) uses 2. All of them are driven by the scheduler at `0x17a48`.
- **Bubble spawn.** `0x2481e` spawns a bubble: `d5` is the record index (record = `d5-1`) and `d1`
  is the bubble mode (1/2 normal, 3 hold the page, 4 advance once then hold).

## License

The code in this repository is under the [MIT License](LICENSE). It doesn't cover the game data
it reads or the text it moves.

## Credits and legal

- The English script is Namco's own translation from *Namco Museum Vol. 5* (1997). This project
  only moves it into the arcade ROMs.
- *Valkyrie no Densetsu* and *Namco Museum* are trademarks and copyright of Bandai Namco
  Entertainment. This project isn't affiliated with or endorsed by them.
- No ROM, BIOS or disc data is included or distributed here. You need your own legally obtained
  copies.
