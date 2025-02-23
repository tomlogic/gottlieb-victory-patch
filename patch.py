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
      hurry-up at start of other players' balls.
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
    - No functional changes, just a public release of INDISC version.

v1.1, released 2025-02-05
    - Update code used to identify "player 1 ball 1" to free up 38 bytes.
    - Optimize code used to load checkpoint bonus and hurry-up timeouts.
    - Carry FINISH lamp progress (for multiplier) into next ball.
    - Shorten labels used in Test Mode to free up more ROM space.

v1.2, released 2024-02-22
    - Free up more space by consolidating switch handler table.
    - Change behavior of DIP switch 30 to FREE PLAY when ON (instead of
      adding 9 credits for each coin in the 3rd coin chute).
"""

import os

# Values for files created by this script.
VERSION = '1.2'
CHECKSUMS = [0xCBC2F, 0x3288D]

# shortcuts for opcodes with unique mnemonics (e.g., not LDA which has multiple versions)

# use b'\xXX' notation instead of 0xXX notation to allow for NOP * 20 or BRK * 20 notation
NOP = b'\xEA'       # replace short runs of code to skip with NOP
BRK = b'\x00'       # replace longer runs of code available for new functions

BPL = 0x10
BMI = 0x30
BVC = 0x50
BVS = 0x70
BCC = 0x90
BCS = 0xB0
BNE = 0xD0
BEQ = 0xF0

JSR = 0x20
RTS = 0x60

PHA = 0x48
PLA = 0x68

TAX = 0xAA
TXA = 0x8A
DEX = 0xCA
INX = 0xE8

TAY = 0xA8
TYA = 0x98
DEY = 0x88
INY = 0xC8

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
    elif isinstance(new_bytes, str):
        for c in new_bytes:
            data[offset + length] = ord(c)
            length += 1
    elif isinstance(new_bytes, int):
        while new_bytes or length == 0:
            data[offset + length] = new_bytes & 0xFF
            length += 1
            new_bytes >>= 8
    else:
        raise ValueError('unknown type passed to patch():', type(new_bytes))
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
    patch(rom, 0x1331, [JSR, 0x2FCF])    # change function called from jsr

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
        TAY,                # tay
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
    patch(rom, 0x1467, [BPL, 0xD0])

    # fix all func_award_bonus calls to use the new address
    for address in [0x3CA6, 0x3F07, 0x3F47]:
        patch(rom, address, [JSR, func_award_bonus])

    # **** end of patches to award_bonus()

    # **** start of code to remove func_update_player_flag_A_for_all() and free up 38 bytes

    # no-op unnecessary initialization of variable at 0x11C
    patch(rom, 0x3AF8, NOP * 3)

    # delay incrementing var_not_start_of_game
    patch(rom, 0x3B2B, NOP * 2)

    # use var_not_start_of_game instead of player flag 13 to identify player 1, ball 1
    patch(rom, 0x1559, [
        0xA5, 0xE3,                 # lda     var_not_start_of_game
        BNE, 0x156A - 0x155D,       # bne     .continue@156A
        NOP, NOP, NOP,              # unused space
    ])

    # replace code that set F13 for all players to just increment var_not_start_of_game
    # placing NOPs first, since there's potential to combine them with previous 3 NOPs
    patch(rom, 0x1565, [
        NOP, NOP, NOP,              # unused space
        0xE6, 0xE3,                 # inc     var_not_start_of_game
    ])

    # Get rid of now-unused 38-byte func_update_player_flag_A_for_all()
    patch(rom, 0x3008, BRK * 38)

    # **** end of code to remove func_update_player_flag_A_for_all() and free up 38 bytes

    # **** Always load checkpoint hurry-up with the bonus

    # new location for func_load_checkpoint_hurryup_delay
    func_load_checkpoint_hurryup_delay = 0x172F

    # new function to load a value from 0 to 7 based on player's completed checkpoints
    func_load_player_checkpoint_index_to_Y = 0x174C
    patch(rom, func_load_player_checkpoint_index_to_Y, [
        JSR, 0x3391,            # jsr load_player_num_to_X
        0xB5, 0xED,             # lda var_player_checkpoint[],x
        0xC9, 0x07,             # cmp #$07
        BCC, 2,                 # skip over next instruction if < (<=?) 7
        0xA9, 0x07,             # lda #$07
        TAY,                    # tay
        RTS                     # rts
    ])

    # update func_load_checkpoint_bonus
    patch(rom, 0x1712, [
        JSR, func_load_player_checkpoint_index_to_Y,    # jsr func_load_player_checkpoint_index_to_Y
        0xA5, 0xDF,                                     # lda var_balls_per_game
        0xC9, 0x03,                                     # cmp #$03
        BNE, 5,                                         # bne .5ball_checkpoint_value
        INY,                                            # iny
        0x84, 0xF7,                                     # sty var_checkpoint_bonus_MSB
        BNE, 15,                                        # bne func_load_checkpoint_hurryup_delay (always branches)
        # .5ball_checkpoint_value:      ; (unmodified from original code)
        0xB9, 0x246B,                                   # lda tbl_halved_checkpoint_values,y
        PHA,                                            # pha
        JSR, 0x272F,                                    # jsr A_shift_high_nibble_to_low
        0x85, 0xF7,                                     # sta var_checkpoint_bonus_MSB
        PLA,                                            # pla
        JSR, 0x272A,                                    # jsr A_shift_low_nibble_to_high
        0x85, 0xF8,                                     # sta var_checkpoint_bonus_LSB
    ])

    # update func_load_checkpoint_hurryup_delay (now just 9 bytes instead of 20)
    patch(rom, func_load_checkpoint_hurryup_delay, [
        JSR, func_load_player_checkpoint_index_to_Y,    # jsr func_load_player_checkpoint_index_to_Y
        0xB9, 0x2473,                                   # lda tbl_checkpoint_hurryup_delay,y
        0x85, 0xFD,                                     # sta var_checkpoint_hurryup_delay
        RTS,                                            # rts
        BRK * 20                                        # erase unused code
    ])

    # Remove calls to func_load_checkpoint_hurryup_delay after loading the bonus
    for address in [0x12E0, 0x3B59]:
        patch(rom, address, NOP * 3)

    # Fix remaining call to func_load_checkpoint_hurryup_delay
    patch(rom, 0x3CEA, [JSR, func_load_checkpoint_hurryup_delay])

    # **** End of loading checkpoint hurry-up with the bonus

    # **** Changes around FINISH targets -- carry status over from ball to ball

    # new version of code to set FINISH lamps at start of ball, incorporate player flags check
    func_initialize_FINISH_lamps = 0x3FDF
    patch(rom, func_initialize_FINISH_lamps, [
        0xA2, 0x05,                             # ldx #$05
        # .loop:
        0xBD, 0x2446,                           # lda tbl_FINISH_lamps[], x
        JSR, 0x307B,                            # jsr func_check_player_flag_A
        0xBD, 0x2427,                           # lda tbl_alternating_FINISH_lamps[],x
        BCC, 2,                                 # bcc .skip_or
        0x09, 0x80,                             # ora #$80          ; lamp always lit if previously scored
        # .skip_or:
        JSR, 0x2F94,                            # jsr update_single_lamp_solenoid_from_A
        DEX,                                    # dex
        BPL, (-19 & 0xFF),                      # bpl .loop
        RTS                                     # rts
    ])

    # update calls to that function
    for address in [0x3B74]:
        patch(rom, address, [JSR, func_initialize_FINISH_lamps])

    # replace existing code with a call to clear the player flags and then display the lamps
    patch(rom, 0x3EA4, [
        JSR, 0x3EAF,                            # jsr
        0x4C, func_initialize_FINISH_lamps,     # jmp func_initialize_FINISH_lamps
        NOP * 5                                 # erase remaining unused code
    ])

    # set/initialize the player flags once at the start of each player's game
    patch(rom, 0x3B59, [JSR, 0x3EAF])

    # **** End FINISH changes

    # Shorten up test menu text to make more room for game/version
    # and future strings or code.
    labels = [
        'LEFT COINS',
        'RIGHT COINS',
        'CENTER COINS',
        'PLAYS',
        'REPLAYS',
        'REPLAY PCT',
        'EXTRA BALLS',
        'TILTS',
        'SPECIALS',
        'HGTD AWARDS',
        '1ST HIGH SCORE',
        '2ND HIGH SCORE',
        '3RD HIGH SCORE',
        'HGTD',
        'AVG PLAY TIME',
        'LAMP TEST',
        'RELAY+SOLENOID TEST',
        'SWITCH TEST',
        'DIP SWITCHES',
        'DISPLAY TEST',
        'MEMORY TEST'
    ]
    address = 0x224A            # end of strings before MSB/LSB table
    index = len(labels)
    labels.reverse()
    for label in labels:
        str_len = len(label) + 1
        address -= str_len
        # next line useful for updating SYM files
        # print("string 0x%04X\tstr_%-21s %u" % (address, label.replace(' ', '_'), str_len))

        patch(rom, address, [label, 0xFF])
        # update MSB/LSB of new label
        index -= 1
        patch(rom, 0x225F + index, (address >> 8))
        patch(rom, 0x224A + index, (address & 0xFF))

    # **** Combine switch handler tables for rows 0 to 3.

    switch_handler_table_MSB = 0x2048
    switch_handler_table_LSB = 0x2040
    tbl_switch_row_3_handlers = 0x23D7      # sw30_handler followed by six 0xFFFF handlers
    tbl_switch_row_X_handlers = 0x23D9      # all 0xFFFF address handlers
    tbl_start_address = 0x23AF

    # combine row for 3 (single handler for sw30) with rows 0-2 (7 unused handlers of 0xFFFF)
    patch(rom, tbl_switch_row_3_handlers, [0x115D, [0xFFFF] * 7])

    # update pointers for rows 0 to 2
    for i in range(0, 3):
        patch(rom, switch_handler_table_MSB + i, tbl_switch_row_X_handlers >> 8)
        patch(rom, switch_handler_table_LSB + i, tbl_switch_row_X_handlers & 0xFF)

    # upgrade pointer for row 3
    patch(rom, switch_handler_table_MSB + 3, tbl_switch_row_3_handlers >> 8)
    patch(rom, switch_handler_table_LSB + 3, tbl_switch_row_3_handlers & 0xFF)

    # remove old entries
    patch(rom, tbl_start_address, BRK * (tbl_switch_row_3_handlers - tbl_start_address))

    # **** End of switch handler table changes.

    # replace "TEST MODE" with "VICTORY v1,x"
    (major, minor) = VERSION.split('.')
    unused = 0x20E8 + patch(rom, 0x20E8, [
        b"VICTORY V",
        0x80 | ord(major),                  # set top bit for comma
        str.encode(minor.replace('0', 'O')),
        0xFF
    ])

    # replace unused bytes with BRK (0x00)
    str_len = address - unused
    patch(rom, unused, BRK * str_len)
    # print("string 0x%04X\tstr_%-21s %u" % (unused, 'UNUSED', str_len))

    # --------- Start of Free Play patch using dipswitch 30

    # Replace existing DIP switch 30 code (which added 9 credits to 3rd coin chute)
    sub_check_dipsw30_freeplay = 0x35A1
    # interrupt the code that updates var_credits_bcd with our freeplay check
    patch(rom, 0x2C10, [0x4C, sub_check_dipsw30_freeplay])
    patch(rom, 0x359D, [
        0x4C, 0x35B7,               # jmp     .save_pricing_config
        BRK,                        # brk     ; wrap this new code with BRK, so it stands out
        # sub_check_dipsw30_freeplay:
        0xA9, 0x04,                 # lda     #$04
        0x24, 0xD7,                 # bit     var_dipsw_25_32
        BNE, 6,                     # bne     .free_play
        # code overwritten by JMP at 0x2C10
        0x84, 0xBF,                 # sty     var_credits_bcd
        TYA,                        # tya
        0x4C, 0x2C13,               # jmp     .update_credits       ; resume non-freeplay code
        # .free_play:
        0x85, 0xBF,                 # sta     var_credits_bcd     ; always 4 credits
        # it probably isn't necessary to update the display -- it should still be blank
        0xA9, '-',                  # lda     #$20    ; ' '
        0x85, 0x1E,                 # sta     disp_credits_ones
        0x4C, 0x2C25,               # jmp     .credits_updated
        BRK                         # brk     ; wrap this new code with BRK, so it stands out
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

try:
    from ips_util.ips_util import Patch
except ImportError:
    Patch = None
    print("Note: install ips_util to create .ips patch files.")
    pass

for i in range(0, 2):
    basename = 'victory-v%s-PROM%u' % (VERSION, i + 1)
    save('%s.bin' % basename, prom_patched[i], CHECKSUMS[i])
    if Patch:
        # Generate IPS file
        with open(os.path.join(my_dir, '%s.ips' % basename), 'wb') as ips:
            ips.write(Patch.create(prom[i], prom_patched[i]).encode())
