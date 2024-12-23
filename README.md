# Gottlieb Victory ROM Tournament/Competition Patch

## Background

This Python script modifies PROM1 and PROM2 from Gottlieb's Victory pinball
machine.  The initial version of the patch changes scoring in multiplayer
games to match that of single-player games.

If someone completes a race in a multiplayer game, the original ROM would
reset all other players back to checkpoint 1, and give them credit for
finishing the qualifying heat.  As a result, all checkpoint hurry-ups for
those players are at the maximum of 800,000 points.

The patch generates ROM files so those events (reset to checkpoint 1, credit
for finishing the qualifying heat) only affect the current player.

## Using the Script

Because of Gottlieb's copyright enforcement, this repository doesn't include
ROM images.  You'll need to dump your existing ROMs, or obtain dumps
elsewhere.

Place `PROM1.CPU` and `PROM2.CPU` in the same directory as the `patch.py`
script.  Reference the table below for file sizes/checksums.  Run `patch.py`
with Python 3.  It will perform a simple checksum on the files before
applying the patches to create `victory-v1.01-PROM1.bin` and
`victory-v1.01-PROM2.bin`.

The repository also includes IPS-formatted patch files as an alternate method
of patching.

## ROM checksums

| Setting           | Original  | v1.01      |
|-------------------|-----------|------------|
| PROM1 file size   | 8192      | 8192       |
| PROM1 checksum    | 0xD02F2   | 0xD03B4    |
| PROM1 CRC32       | e724db90  | 3d673442   |
| PROM2 file size   | 2048      | 2048       |
| PROM2 checksum    | 0x32B32   | 0x32B4E    |
| PROM2 CRC32       | 6a42eaf4  | e5e1717c   |
| enter self test   | TEST MODE | VCTRY 1,01 |
| in-game check-sum | 02F2      | 03B4       |
