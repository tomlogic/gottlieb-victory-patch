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

## Creating patched ROMs

Because of Gottlieb's copyright enforcement, this repository doesn't include
ROM images.  You'll need to dump your existing ROMs, or obtain dumps
elsewhere.

I recommend keeping the original PROMs for backup.  For EEPROM replacements,
you can use AT28C64-15PC for PROM1 (8KB) and AT28C16-15PC for PROM2 (2KB).

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

| Setting           | Original  | v1.2        |
|-------------------|-----------|-------------|
| PROM1 file size   | 8192      | 8192        |
| PROM1 checksum    | 0xD02F2   | 0xCBC2F     |
| PROM1 CRC32       | e724db90  | 0c24e956    |
| PROM2 file size   | 2048      | 2048        |
| PROM2 checksum    | 0x32B32   | 0x3288D     |
| PROM2 CRC32       | 6a42eaf4  | fbcd3463    |
| Service Menu text | TEST MODE | VICTORY 1,2 |
| in-game check-sum | 02F2      | BC2F        |
