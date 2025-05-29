# Gottlieb Victory ROM Tournament/Competition Patch

## Background

This Python script modifies PROM1 and PROM2 from Gottlieb's Victory pinball
machine.  The initial version of the patch changes scoring in multiplayer
games to match that of single-player games.

If someone completes a race in a multiplayer game, the original ROM would
reset all other players back to checkpoint 1, give them credit for finishing
the qualifying heat, and enable the hurry-up at the start of their next ball.
As a result, all checkpoint hurry-ups for those players are at the maximum
of 800,000 points.

The patch generates ROM files so those events only affect the current player.

In addition, starting with v1.03 of the patch, it improves RACE BONUS scoring
(end of ball and lit RACE BONUS shots) and awards a multiplied 500K bonus at
the end of each race.

Starting with v1.1, FINISH target progress carries over from ball to ball,
providing more incentive for attempting those risky shots and increasing the
multiplier.

Version 1.2 changed behavior of DIP switch 30 to FREE PLAY when ON (instead
of adding 9 credits for each coin in the 3rd coin chute).  Note that PROM2
v1.2 is identical to v1.1.

Version 1.3 extends DIP switch 32's existing liberal/conservative setting to
control FUEL drop target behavior.  The "liberal" setting (switch on) is the
default behavior of resetting after hitting a flashing "L" or dropping all
targets.  The "conservative" setting (switch off) removes the behavior of
resetting the bank when all targets are down, but resets the targets on any
completed shot to the upper right ramp (100K shot) or orbit (checkpoint 3).
With this change, it shouldn't be necessary to disable the upper-right
flipper to prevent chopping wood with a "drop targets all day" strategy.

## Tournament Use

Version 1.03 debuted at INDISC in January 2025.

Version 1.2 was used the same weekend of May 2025 at both the Golden State
Pinball Festival (where I discuss the patch about 73 minutes into
Sunday's stream) and the PINDY 500 at PinVault (where it shows up in the
last round).

## Creating patched ROMs

Because of Gottlieb's copyright enforcement, this repository doesn't include
ROM images.  You'll need to dump your existing ROMs, or obtain dumps
elsewhere.

I recommend keeping the original PROMs for backup.  For EEPROM replacements,
you can use AT28C64-15PU for PROM1 (8KB) and AT28C16-15PU for PROM2 (2KB).
The obsolete -15PC and -15PI chips (commercial/industrial temperature range)
work as well, but only the -15PU (no-lead RoHS) 8KB chip is still actively
available.  UV-erasable 2764 and 2716 EPROMs also work.

### IPS Patch Files
If you're familiar with using IPS files for patching, you can use
`victory-vX.X-PROM1.ips` and `victory-vX.X-PROM2.ips`.

### Python Script
Place `PROM1.CPU` and `PROM2.CPU` in the same directory as the `patch.py`
script.  Reference the table below for file sizes/checksums.  Run `patch.py`
with Python 3.  It will perform a simple checksum on the files before
applying the patches to create `victory-vX.X-PROM1.bin` and
`victory-vX.X-PROM2.bin`.

## ROM checksums

| Setting           | Original  | v1.3        |
|-------------------|-----------|-------------|
| PROM1 file size   | 8192      | 8192        |
| PROM1 checksum    | 0xD02F2   | 0xCCE47     |
| PROM1 CRC32       | e724db90  | c94d420a    |
| PROM2 file size   | 2048      | 2048        |
| PROM2 checksum    | 0x32B32   | 0x32825     |
| PROM2 CRC32       | 6a42eaf4  | 37554592    |
| Service Menu text | TEST MODE | VICTORY 1,3 |
| in-game check-sum | 02F2      | CE47        |

## Thanks

Big thanks to PinVault for turning me on to Victory, inspiring these patches,
and letting me test ROM updates.  In particular, Matt for letting me test on
his game, and Greg and Tad for letting me visit off hours.

Thanks to Jim Belsito for reaching out before INDISC 2025 and inspiring me to
go even further with the improvements.
