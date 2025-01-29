#!/usr/bin/env python3

"""
Modify Gottlieb Victory pinball ROMs to improve multiplayer scoring for
competitive/tournament use.

See https://github.com/tomlogic/gottlieb-victory-patch for details.

Copyright 2024 by Tom Collins <tom@tomlogic.com>, All Rights Reserved
Released under GPL-3.0 License

Version History
---------------
v1.01, Released 2024-12-23
    - Initial release.
    - Only reset current player to checkpoint 1 and give credit for finishing
      Qualifying Heat.

v1.02, unreleased
    - Upon race completion, don't modify flag used to enable checkpoint
      hurry-up at start of ball.
    - Track count of completed checkpoints, and base bonus on that value
      instead of just the current checkpoint number.
    - Race Bonus:
      was 10K x checkpoint number
      now 50K x (completed checkpoints + 1)
          (the same as 50K x (completed races x 8 + checkpoint number))

v1.03, custom INDISC 2025 version, released 2025-01-19
    - Score multiplied 500K upon race completion (in addition to hurry-up,
      if any).

v1.04, public version of v1.03, released 2025-01-31
    - No functional changes.
"""

from ips_util.ips_util import Patch
import os

# Values for files created by this script.
VERSION = '1.04'
CHECKSUMS = [0xD0316, 0x329DF]

# shortcuts for opcodes with unique mnemonics (e.g., not LDA which has multiple versions)
NOP = b'\xEA'       # this notation allows for `NOP * 20` for 20 NOP opcodes
JSR = 0x20
RTS = 0x60
TYA = 0x98
TAY = 0xA8

# reference binary files in our directory
my_dir = os.path.dirname(__file__)


def load(file_in, expected_checksum):
    try:
        with open(os.path.join(my_dir, file_in), 'rb') as f:
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

    
def save(file_out, data, expected_checksum):
    with open(os.path.join(my_dir, file_out), 'wb') as f:
        f.write(data)

    actual_checksum = checksum(data)
    if actual_checksum == expected_checksum:
        print("Success: %s checksum is expected 0x%X" % (file_out, actual_checksum))
    else:
        print("Warning: %s file checksum 0x%X != 0x%X" %
              (file_out, actual_checksum, expected_checksum))


def patch(data, offset, new_bytes):
    length = 0
    if isinstance(new_bytes, list):
        for item in new_bytes:
            length += patch(data, offset + length, item)
    elif isinstance(new_bytes, bytes):
        for b in new_bytes:
            data[offset + length] = b
            length += 1
    elif isinstance(new_bytes, int):
        while new_bytes or length == 0:
            data[offset + length] = new_bytes & 0xFF
            length += 1
            new_bytes >>= 8
    else:
        raise ValueError('unknown type passed to patch(): ' + type(new_bytes))
    return length


def checksum(data):
    check = 0
    for b in data:
        check += b
    return check
    
    
def patch_rom(rom):
    # Get rid of all of this code from completing a race.  One player's action shouldn't
    # impact other players' games.
    """
    12FD				.reset_all_player_checkpoints:
    12FD : A9 00        "  "        lda     #$00         ; CHECKPOINT 1
    12FF : 85 ED        "  "        sta     var_player_checkpoint[]
    1301 : 85 EE        "  "        sta     X00EE
    1303 : 85 EF        "  "        sta     X00EF
    1305 : 85 F0        "  "        sta     X00F0
    1307                .clear_all_player_F16@1307:
    1307 : A9 10        "  "        lda     #$10         ; F16 [if set, no checkpoint bonus on next plunge] clear
    1309 : 20 08 30     "  0"       jsr     func_update_player_lamp_A_for_all
    130C                .set_curr_player_F16@130C:
    130C : A9 90        "  "        lda     #$90         ; F16 [if set, no checkpoint bonus on next plunge] set
    130E : 20 CF 2F     "  /"       jsr     func_update_player_lamp
    """
    reset_current_player_checkpoint = 0x12FD
    patch(rom, reset_current_player_checkpoint, [
        # this 15-byte sequence adds a multiplied, 500K bonus for completing the race
        0xA9, 0x88,             # lda #$88      ; enable multiplied score
        JSR, 0x2FCF,            # jsr func_update_player_flag

        0xA9, 0x15,             # lda #$15         ; 500,000 points
        JSR, 0x11A6,            # jsr func_add_multiplied_to_score

        0xA9, 0x08,             # lda #$08      ; disable multiplied score
        JSR, 0x2FCF,            # func_update_player_flag

        NOP * 5                 # room for even more code!
    ])

    # replace unused func_update_X_player_flags_from_Y_for_all with a new function
    func_load_player_checkpoint = 0x302E
    patch(rom, func_load_player_checkpoint, [
        JSR, 0x3391,            # jsr load_player_num_to_X
        0xA9, 0x07,             # lda #$07
        0x35, 0xED,             # and var_player_checkpoint[], x
        TAY,                    # tay
        RTS                     # rts
    ])

    """
    ; replace this section of code
    12C7 : 20 91 33         "  3"           jsr     load_player_num_to_X
    12CA : B4 ED            "  "            ldy     var_player_checkpoint[],x
    12CC : C0 07            "  "            cpy     #$07         ; CHECKPOINT 8
    12CE : F0 16            "  "            beq     .at_last_checkpoint
    12D0                            .advance_to_next_checkpoint:
    12D0 : C8               " "             iny
    12D1 : 94 ED            "  "            sty     var_player_checkpoint[],x
    12D3 : 88               " "             dey
    """
    patch(rom, 0x12C7, [
        JSR, func_load_player_checkpoint,   # jsr func_load_player_checkpoint
        0xF6, 0xED,                         # inc var_player_checkpoint[],x
    ])
    # leave existing code at 0x12CC and 0x12D0
    patch(rom, 0x12D0, [NOP, NOP, NOP, NOP])

    # only give current player credit for finishing qualifying heat
    """
    132F				.player_finished_qualifying_heat:
    132F : A9 8E		"  "		lda	#$8E         ; F14 [completed qualifying heat] set
    1331 : 20 08 30		"  0"		jsr	func_update_player_flag_for_all

    132F				.player_finished_qualifying_heat:
    132F : A9 8E		"  "		lda	#$8E         ; F14 [completed qualifying heat] set
    1331 : 20 CF 2F		"  /"		jsr	func_update_player_flag
    """
    patch(rom, 0x1332, 0x2FCF)    # change function called from jsr

    # replace code that loads the player's checkpoint with a JSR to this new code
    #   12C7 : 20 91 33         "  3"           jsr     load_player_num_to_X
    #   12CA : B4 ED            "  "            ldy     var_player_checkpoint[],x

    for address in [0x1712, 0x174E, 0x1759, 0x3BFA]:
        patch(rom, address, [
            NOP,                                    # nop
            JSR, func_load_player_checkpoint,       # jsr func_load_player_checkpoint
            NOP                                     # nop
        ])

    """
    Update func_is_player_at_checkpoint_Y, but first simplifying previous routine
    (.mult_at_max_8X_so_score_mult_100K@1254) to jump to existing code (freeing up
    some extra bytes).
    """
    """
    Reduce code used for this routine, to free up two more bytes for
    func_is_player_at_checkpoint_Y.
        1254                            .mult_at_max_8X_so_score_mult_100K@1254:
        1254 : A9 11            "  "            lda     #$11         ; 100,000 points
        1256 : 4C A6 11         "L  "           jmp     func_add_multiplied_to_score
    """
    patch_length = patch(rom, 0x1254, [
        # .mult_at_max_8X_so_score_mult_100K@1254:
        0x4C, 0x114A,       # jmp .add_100K_multiplied_to_score (either 114A or 3EFA)
    ])

    """
    Old code:
        1259                            func_is_player_at_checkpoint_Y:
        1259 : 20 91 33         "  3"           jsr     load_player_num_to_X
        125C : 98               " "             tya
        125D : D5 ED            "  "            cmp     var_player_checkpoint[],x

    New code (with new entry address):
        1257                            func_is_player_at_checkpoint_Y:
        1257 : 20 91 33         "  3"           jsr     load_player_num_to_X
        125A : 98               " "             tya
        125B : 55 ED            "U "            eor     var_player_checkpoint[],x
        125D : 29 07            ") "            and     #$07
    """
    player_at_checkpoint = 0x1254 + patch_length
    patch(rom, player_at_checkpoint, [
        # func_is_player_at_checkpoint_Y (new location)
        JSR, 0x3391,        # jsr load_player_num_to_X        ; 3 X = player number
        TYA,                # tya                             ; 1 A = checkpoint_test
        0x55, 0xED,         # eor var_player_checkpoint[],x   ; 2 A = checkpoint_test ^ checkpoint_var
        0x29, 0x07,         # and #$07                        ; 2 A = bottom three bits of that
    ])

    # fix all func_is_player_at_checkpoint_Y calls to use the new address
    for address in [0x1032, 0x1085, 0x10A8, 0x3EC8, 0x3F1B, 0x3F54, 0x3F8B]:
        patch(rom, address, [JSR, player_at_checkpoint])

    # **** Big patch to award_bonus() to consider full checkpoint count.

    # start by inserting func_toggle_bonus_lamp() before award_bonus()
    func_toggle_bonus_lamp = 0x1416
    patch_size = patch(rom, func_toggle_bonus_lamp, [
        0xA5, 0xE7,         # lda X00E7
        0x29, 0x07,         # and #$07
        0xA8,               # tay
        0xB9, 0x242D,       # lda tbl_checkpoint_lamps,y
        0x09, 0x40,         # ora #$40
        0x4C, 0x2F94        # jmp update_single_lamp_solenoid_from_A  ; chain into this function
    ])
    func_award_bonus = func_toggle_bonus_lamp + patch_size

    # now build new award_bonus() after the new function
    patch(rom, func_award_bonus, [
        JSR, 0x15D6,        # jsr     func_set_var_E4_to_0
        0xA9, 0x88,         # lda     #$88         ; F8 [Multiply Score] set
        JSR, 0x2FCF,        # jsr     func_update_player_flag
        0xA0, 0x11,         # ldy     #$11         ; L17 [CHECKPOINT #1 CAR & TARGET (2)] clear
        0xA2, 0x08,         # ldx     #$08
        JSR, 0x2FC6,        # jsr     update_X_lamps_solenoids_from_Y
        JSR, 0x3391,        # jsr     load_player_num_to_X
        0xB5, 0xED,         # lda     var_player_checkpoint[],x
        0x85, 0xE7,         # sta     X00E7
        JSR, func_toggle_bonus_lamp,      # jsr func_toggle_bonus_lamp
        0xA9, 0xEB,         # lda     #$EB         ; sound(0xEB)
        JSR, 0x2F64,        # jsr     func_play_sound_A
        0xA9, 0x8E,         # lda     #$8E         ; L14 [CENTER LAMPS: TOP RIGHT/BOTTOM LEFT (2)] set
        JSR, 0x2F94,        # jsr     update_single_lamp_solenoid_from_A
        0xA9, 0x90,         # lda     #$90         ; L16 [CENTER LAMPS: TOP LEFT/BOTTOM RIGHT (2)] set
        JSR, 0x2F94,        # jsr     update_single_lamp_solenoid_from_A
        0xA9, 0x25,         # lda     #$25         ; 50,000 points
        JSR, 0x11A6,        # jsr     func_add_multiplied_to_score
        0xA9, 0x10,         # lda     #$10
        JSR, 0x2F51,        # jsr     func_delay
        JSR, func_toggle_bonus_lamp,  # jsr func_toggle_bonus_lamp
        NOP,                # nop     ; re-align with original code
    ])

    # fix the bpl to the top of the bonus burndown loop
    patch(rom, 0x1467, [0x10, 0xD0])

    # fix all func_award_bonus calls to use the new address
    for address in [0x3CA6, 0x3F07, 0x3F47]:
        patch(rom, address, [JSR, func_award_bonus])

    # **** end of patches to award_bonus()

    # replace "TEST MODE" with "VCTRY 1,xx"
    (major, minor) = VERSION.split('.')
    patch(rom, 0x20E8, [
        b"VCTRY ",
        0x80 | ord(major),                  # set top bit for comma
        str.encode(minor.replace('0', 'O')),
        0xFF
    ])

    # update PROM2 and PROM1 checksums stored on PROM1

    p2_checksum = checksum(rom[0x1000:0x1800])

    # update checksum of PROM2 (in PROM1) and reset PROM1 checksum to 0xFFFF
    patch(rom, 0x3FF6, [
        (p2_checksum >> 8) & 0xFF, p2_checksum & 0xFF,          # reversed byte order!
        0xFFFF
    ])

    # calculate new PROM1 checksum, with 0xFFFF in that position
    stored_checksum = checksum(rom[0x2000:0x4000])
    patch(rom, 0x3FF8, [
        (stored_checksum >> 8) & 0xFF, stored_checksum & 0xFF   # reversed byte order!
    ])


# create an all 0xFF 16KB memory space to load ROMs into for patching
ROM = bytearray([0xFF] * 4 * 4096)
prom = [
    load('PROM1.CPU', 0xD02F2),
    load('PROM2.CPU', 0x32B32)
]
ROM[0x2000:0x4000] = prom[0]
ROM[0x1000:0x1800] = prom[1]

patch_rom(ROM)

prom_patched = [
    ROM[0x2000:0x4000],
    ROM[0x1000:0x1800]
]

for i in range(0, 2):
    basename = 'victory-v%s-PROM%u' % (VERSION, i + 1)
    save('%s.bin' % basename, prom_patched[i], CHECKSUMS[i])
    # Generate IPS file
    patch = Patch.create(prom[i], prom_patched[i])
    with open(os.path.join(my_dir, '%s.ips' % basename), 'wb') as ips:
        ips.write(patch.encode())
