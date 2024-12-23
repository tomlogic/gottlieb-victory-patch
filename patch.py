#!/usr/bin/env python3

"""
Modify Gottlieb Victory pinball ROMs to improve multiplayer scoring for
competitive/tournament use.

See https://github.com/tomlogic/gottlieb-victory-patch for details.

Copyright 2024 by Tom Collins <tom@tomlogic.com>, All Rights Reserved
Released under GPL-3.0 License

Version History
---------------
2024-12-23 v1.01 Initial release.  Only reset current player to checkpoint 1
                 and give credit for finishing Qualifying Heat.
"""


# Values for files created by this script.
VERSION = '1.01'
PROM1_CHECKSUM = 0xD03B4
PROM2_CHECKSUM = 0x32B4E


def load(file_in, expected_checksum):
    try:
        with open(file_in, 'rb') as f:
            source_bytes = bytearray(f.read())
    except FileNotFoundError:
        print('Error: Script requires original PROM1.CPU and PROM2.CPU files.')
        print('View instructions in README.md for details.')
        raise SystemExit
        
    actual_checksum = checksum(source_bytes)
    if actual_checksum != expected_checksum:
        raise ValueError('%s checksum 0x%X does not match expected 0x%X' %
                         (file_in, actual_checksum, expected_checksum))
    return source_bytes

    
def save(file_out, data):
    with open(file_out, 'wb') as f:
        f.write(data)


def patch(data, offset, new_bytes):
    for b in new_bytes:
        data[offset] = b
        offset += 1
        

def patch_prom1(CHECKSUM_P2):
    p1 = load('PROM1.CPU', 0xD02F2)
    
    # replace "TEST MODE" with "VCTRY 1,01" (\xB1 is 1 followed by comma)
    (major, minor) = VERSION.split('.')
    patch(p1, 0x00E8, b"VCTRY %c%s\xFF" % ((0x80 | ord(major)), str.encode(minor)))
    
    # update checksum of P2 and reset P1 checksum to 0xFFFF
    patch(p1, 0x1FF6, [(CHECKSUM_P2 >> 8) & 0xFF, CHECKSUM_P2 & 0xFF, 0xFF, 0xFF])

    # calculate new checksum, with 0xFFFF in that position
    stored_checksum = checksum(p1)
    patch(p1, 0x1FF8, [(stored_checksum >> 8) & 0xFF, stored_checksum & 0xFF])
    save('victory-v%s-PROM1.bin' % VERSION, p1)

    # re-calculate file's actual checksum
    actual_checksum = checksum(p1)
    if actual_checksum == PROM1_CHECKSUM:
        print("Success: PROM1 file checksum is expected 0x%X" % actual_checksum)
    else:
        print("Warning: modified PROM1 file checksum 0x%X != 0x%X" %
              (actual_checksum, PROM1_CHECKSUM))


def checksum(data):
    check = 0
    for b in data:
        check += b
    return check
    
    
def patch_prom2():
    p2 = load('PROM2.CPU', 0x32B32)

    # only reset current player to checkpoint 0
    """
    12FD				.reset_player_checkpoints_to_0:
    12FD : A9 00		"  "		lda	#$00
    12FF : 85 ED		"  "		sta	var_player_checkpoint[]
    1301 : 85 EE		"  "		sta	X00EE
    1303 : 85 EF		"  "		sta	X00EF
    1305 : 85 F0		"  "		sta	X00F0

    Replace with:
                        .reset_current_player_checkpoint_to_0:
    12FD : 20 91 33		"  3"		jsr	load_player_num_to_X
    1300 : A9 00		"  "		lda	#$00
    1302 : 95 ED		"  "		sta	var_player_checkpoint[],x
    1304 : EA		    " "		    nop
    1305 : EA		    " "		    nop
    1306 : EA		    " "		    nop
    """
    patch(p2, 0x2FD, b"\x20\x91\x33\xA9\x00\x95\xED\xEA\xEA\xEA")

    # only give current player credit for finishing qualifying heat
    """
    132F				.player_finished_qualifying_heat:
    132F : A9 8E		"  "		lda	#$8E
    1331 : 20 08 30		"  0"		jsr	func_update_player_lamps_for_all

    132F				.player_finished_qualifying_heat:
    132F : A9 8E		"  "		lda	#$8E
    1331 : 20 CF 2F		"  /"		jsr	func_update_player_lamp
    """
    patch(p2, 0x332, b"\xCF\x2F")
    
    save('victory-v%s-PROM2.bin' % VERSION, p2)
    actual_checksum = checksum(p2)

    if actual_checksum == PROM2_CHECKSUM:
        print("Success: PROM2 file checksum is expected 0x%X" % actual_checksum)
    else:
        print("Warning: modified PROM2 file checksum 0x%X != 0x%X" %
              (actual_checksum, PROM2_CHECKSUM))

    return actual_checksum


# patch PROM2 first because PROM1 holds a PROM2 checksum    
CHECKSUM_P2 = patch_prom2()
patch_prom1(CHECKSUM_P2)
