# The Legend of Valkyrie: arcade English patch (IPS)

These patches translate the arcade game **Valkyrie no Densetsu** (Namco, 1989) into English. They
use Namco's official script from the 1997 PlayStation release in *Namco Museum Vol. 5*, where the
game is called **The Legend of Valkyrie**.

They translate all dialogue, the story screens and the ending, and add an English subtitle under
the logo on the title screen. They also fix the arcade text routines so the longer English lines
display properly.

## Files

| Patch | Applies to |
|---|---|
| `wd1mpr0.ips` | `wd1mpr0.bin` |
| `wd1mpr1.ips` | `wd1mpr1.bin` |

The patches need the original program ROMs from the MAME / FBNeo set `valkyrie`
(`valkyrie.zip`). No ROM data is included.

| File | Size | CRC32 | SHA-1 |
|---|---|---|---|
| `wd1mpr0.bin` original | 131072 | `94111a2e` | `bd0dfe362fc98c1e94422a898b4daf6a08ef7982` |
| `wd1mpr1.bin` original | 131072 | `57b5051c` | `de399381823251e2ee45f51c96be3e93ed763f94` |
| `wd1mpr0.bin` patched | 131072 | `f6e93a8c` | `fc2513935a14c994eb0d4405de1cec5d9f62b363` |
| `wd1mpr1.bin` patched | 131072 | `0f496013` | `90f8ab7930ad0e7974d63740ace93d3fc26faf89` |

## Applying

1. Copy `valkyrie.zip` to a new folder, so your original set stays untouched.
2. Extract `wd1mpr0.bin` and `wd1mpr1.bin` from the copy.
3. Apply `wd1mpr0.ips` to `wd1mpr0.bin` and `wd1mpr1.ips` to `wd1mpr1.bin`. Any IPS tool works,
   for example [Floating IPS](https://github.com/Alcaro/Flips) or Lunar IPS.
4. Check the patched CRC32s against the table above.
5. Put both patched files back into the copied `valkyrie.zip`, replacing the originals. Leave all
   the other files in the zip as they are.

## Running

MAME and FBNeo look for the set by its file name, so keep the patched zip named `valkyrie.zip`.
List its folder first in the ROM path, so it's found before your original set:

```
mame valkyrie -rompath "C:\path\to\patched;C:\path\to\roms"
```

MAME reports `WRONG CHECKSUMS` for `wd1mpr0.bin` and `wd1mpr1.bin`. That's expected, and the game
runs normally. The patch was tested with MAME 0.287. Some later MAME versions also need
`valkyrie.nv` and `lh5762.6n` in the set, the same as the unpatched game does. FBNeo hasn't been
tested and may refuse sets with the wrong CRCs.

## Credits and legal

- The English script is Namco's own translation from *Namco Museum Vol. 5* (1997). These patches
  only move it into the arcade ROMs.
- *Valkyrie no Densetsu* and *Namco Museum* are trademarks and copyright of Bandai Namco
  Entertainment. This patch isn't affiliated with or endorsed by them.
- No ROM, BIOS or disc data is distributed. You need your own legally obtained copy of the
  arcade set.
