"""proteus2kicad configuration of the hi_voltage_suppliesv2 board (tools in tools/p2k, see its README).

Plain Python; every value here is specific to this board. Coordinates in mm, IPC frame (Y up).
"""

PROJECT = "tube_hv_supplies"  # KiCad project / library name

# Sources (relative to the repo root). The CADCAM export with Gerber X2 attributes.
CADCAM = "source/cadcam"
IPC = "source/cadcam/hi_voltage_suppliesv2 - CADCAM Netlist.IPC"

# --- Schematic skeleton (make_skeleton) ----------------------------------------------

# (Proteus page, sheet name, file). The PDF pages have no title block (no PATH / TITLE
# field, and ROOT.DSN carries no sheet names): the names describe the page content
# (STATUS.md "Phase 0").
SHEETS = [
    (1, "Power stage", "01_power_stage.kicad_sch"),                      # B+ filter, Q3/Q4 + Q8/Q7 half-bridges, shunts, terminals
    (2, "Gate drivers", "02_gate_drivers.kicad_sch"),                    # DRV1/DRV2/DRV5/DRV6 Si8271, bootstrap D18/D2
    (3, "Voltage measurements", "03_voltage_measurements.kicad_sch"),    # U1 LMV324A dividers: UIN, UC3, V_A, U_OUT
    (4, "Current measurements", "04_current_measurements.kicad_sch"),    # U2 LT1014 shunt amplifiers
    (5, "Reference and connector", "05_reference_connector.kicad_sch"),  # REF1 +1V0_BIAS, J1 40-pin ribbon
    (6, "ADC", "06_adc.kicad_sch"),                                      # J2 16-pin, ADC1-3 ADC121C027
]
SCH_TITLE = "Tube HV supplies"
SCH_COMPANY = "Tube amplifier"
SCH_REV = "rev A (as built)"
SCH_COMMENT = "Redrawn from Proteus hi_voltage_suppliesv2"
SCH_NOTE = ("Tube HV supplies v2 - redrawn from Proteus. One sheet per Proteus PDF page.\n"
            "Net names follow the IPC-D-356A netlist (reference/pins_by_net.md).")

# --- IPC-D-356A fix-ups (ipc356) -----------------------------------------------------

# Truncated refdes (6 chars) -> full Proteus refdes (PDF page 1, TERMINAL parts). Each
# terminal has two holes, both pin 1, on one net. Each truncated name is unique on this
# board, so no coordinates needed. (VPRE is 4 characters: not truncated.)
TRUNCATED_REFDES = {
    "V_ANOD": "V_ANODE",
    "GND_PR": "GND_PRE",
    "GND_PW": "GND_PWR",
}
# Expected net per restored refdes (checked by ipc356 --check).
TRUNCATED_NETS = {
    "V_ANODE": "V_A",
    "GND_PRE": "GND",
    "GND_PWR": "GND",
}

# Full Proteus refdes -> KiCad refdes (KiCad references must start with a letter and hold
# only letters, digits and '_'). Sign replaced by P / N as in tube_psu (P400V, N5V_OUT).
KICAD_REFDES = {
    "B+": "B_P",   # HV input terminal, net B+
    "B-": "B_N",   # HV return terminal, net GND
}

# No Proteus power-net suffixes (=POWER) in this export: GND, 3V3, 15V_BOOST are plain
# names. One rename (user decision 2026-11-20, finding 1): REF1 is ISL21010CFH315Z (1.5 V) into
# R74 220 / R73 470, so the rail is about 1.0 V; the Proteus IPC and gerbers keep +2V5_BIAS.
# p2k ipc356 applies this map when it parses the IPC, so every check that reads the IPC nets
# (reference/, compare_netlists, check_symbols, check_board, assign_nets, gerber_roundtrip
# labels) sees +1V0_BIAS; ipc356_diff matches nets by pad sets. ipc356 --check fails if the
# source name is not in the IPC or the target collides with an IPC net.
# Current-measurement nets renamed to what each sense path measures (user decision 2026-11-20,
# finding 7; STATUS.md "Design fixes 2026-11-20"). Shunts: R75 under C3 (UC3 filter capacitor of
# bridge 1), R30 under C6 (UC6 filter capacitor of bridge 2), R72 in the Q4 emitter and R29 in the
# Q7 emitter (low-side IGBT + copack diode: the L1 / L3 current only while the low side conducts).
# U2:A..D amplify them to J1 (the four *_MEAS nets cross the ribbon to the control card). Style
# CURRENT_<part> as the Proteus CURRENT_L1; C3_CURRENT / C3_CURRENT_MEAS can't be targets (ipc356
# rejects an alias target that is an IPC net name, even one that is renamed itself).
NET_ALIASES = {
    "+2V5_BIAS": "+1V0_BIAS",
    "C1_CURRENT": "CURRENT_C3",              # R75: current of C3 (bridge 1 output capacitor, UC3)
    "C3_CURRENT": "CURRENT_C6",              # R30: current of C6 (bridge 2 second-stage capacitor, UC6)
    "CURRENT_L1": "CURRENT_Q4",              # R72: Q4 emitter (bridge 1 low side)
    "CURRENT_L3": "CURRENT_Q7",              # R29: Q7 emitter (bridge 2 low side)
    "C1_CURRENT_MEAS": "CURRENT_C3_MEAS",    # U2:B out, J1-8 (Proteus J1-7)
    "INPUT_CURRENT_MEAS": "CURRENT_C6_MEAS", # U2:A out, J1-6 (Proteus J1-5)
    "C2_CURRENT_MEAS": "CURRENT_Q4_MEAS",    # U2:C out, J1-2 (Proteus J1-1)
    "C3_CURRENT_MEAS": "CURRENT_Q7_MEAS",    # U2:D out, J1-4 (Proteus J1-3)
}

# Ribbon header J1 (finding 12; user decision 2026-11-20, D-PIN: "renumber the pads to standard at both
# ends, copper unchanged, square pin-1 pad on the real pin 1"): Proteus numbers J1 as the mirror image of
# a standard top-view 2x20 header (odd / even rows swapped). Proteus pin k -> KiCad pad k + 1 (odd k) /
# k - 1 (even k), so J1 is the stock KiCad header with the standard numbering and every net stays on the
# same physical pad. The control card's J11 (other repo) is renumbered the same way, so the cable still
# joins pad k to pad k (STATUS.md "Shared-tool migration 2026-11-20", J1 / J11 table). p2k ipc356 applies
# it when it parses the IPC, so every check sees the KiCad pad numbers.
IPC_PIN_IDS = {"J1": {str(k): str(k + 1 if k % 2 else k - 1) for k in range(1, 41)}}

# Blank-refdes records: a net and one of these drills = via (0.5/0.3 x139, 1.016/0.381 x2),
# no net = hole (4 plated 3.0 mm mounting holes, 6.35 mm ring on every copper layer, no net).
# No free pads.
VIA_DRILLS = (0.3, 0.381)
FREE_PAD_DRILLS = ()
HOLE_DRILLS = (3.0,)
HOLES_PLATED = True

# Expected counts in the Proteus file (PLAN.md section 1).
EXPECTED_IPC = {
    "nets": 113,          # NNAME declarations (NNAME00005..00119 without 00067/00068)
    "records": 574,
    "refdes_raw": 159,    # distinct refdes fields, incl. the blank one of vias/holes
    "tht_records": 247,   # 102 component THT pads + 141 vias + 4 holes
    "smd_records": 327,
    "smd_top": 227,
    "smd_bottom": 100,
    "nc_pads": 2,         # J1-37, J1-38 (Proteus J1-38, J1-37 after IPC_PIN_IDS)
    "vias": 141,
    "free_pads": 0,
    "holes": 4,
    "parts": 158,         # named refdes after the truncation fix-up
}

# --- Gerbers (check_sources, later the PCB tools) ------------------------------------

# Proteus copper gerber name -> KiCad copper layer, User layer for the pour outlines.
COPPER = [
    ("Top Copper", "F.Cu", "User.1"),
    ("Inner  1", "In1.Cu", "User.2"),
    ("Inner  2", "In2.Cu", "User.3"),
    ("Bottom Copper", "B.Cu", "User.4"),
]
DRILL_PLATED = "Drill TOP-BOT Plated"
DRILL_NONPLATED = None   # Proteus wrote no NonPlated drill file (the mounting holes are plated)
OUTLINE = "Mechanical 1"
OUTLINE_RECT = (-122.6, -28.26, 170.085, 56.485)  # x, y, width, height

# --- Footprints (Phase 2, tools/gen_footprints.py, p2k check_footprints) ---------------

# Pad sizes: "kicad" (KiCad library pad sizes and drills, pad centres on the Proteus positions;
# the footprints built from the IPC pads - terminals - and the KRL2012 shunt land pattern have the
# Proteus pads). Changing it is a user decision (Phase 3 DRC; STATUS.md "Phase 2 - pad sizes").
FOOTPRINT_PAD_SIZES = "kicad"
# kicad/fp-lib-table (the project footprint library) is written / checked by p2k.footprints.run.
FP_LIB_TABLE = True
# The footprint generator is frozen in tools/generate/ (generation stopped, D-STOP); p2k check_pin_order
# still imports its RULES / PROJECT specs (spec= entries of PIN_ORDER).
FOOTPRINT_SCRIPT = "tools/generate/gen_footprints.py"
# Parts drawn in the PDF without a layout part (no IPC pads): no footprint.
OFF_BOARD_PARTS = {
    "L1": "off board: 3 mH inductor (OUT1 -> UC3), wired to the L5 / L12 terminals",
    "L3": "off board: 3 mH inductor (OUT2 -> U_OUT), wired to the L11 / L6 terminals",
}

# --- PCB (Phase 3, build_pcb) ----------------------------------------------------------

# The 4 IPC 'hole' records: plated 3.0 mm holes with a 6.35 mm ring on all four copper layers,
# no net (lib/tube_hv_supplies.pretty, tools/gen_footprints.py PROJECT).
HOLE_FOOTPRINT = "tube_hv_supplies:MountingHole_3.0mm_PTH_Pad6.35mm"
HOLE_VALUE = "MountingHole_3.0mm"
# Board thickness: 1.6 mm (user decision 2026-11-20, finding 3; the CADCAM READ-ME stack of
# 2.267 mm is a Proteus default). Stack-up (agent's choice, a common 4-layer 1.6 mm build; only
# the total goes into the board, the copper layers are what the checks compare):
# F.Cu 0.035 / prepreg 0.2104 / In1.Cu 0.0152 / core 1.065 / In2.Cu 0.0152 / prepreg 0.2104 /
# B.Cu 0.035 = 1.586 mm + 2 x ~0.01 mm solder resist = 1.6 mm.
PCB_THICKNESS = 1.6
# Design rules from the Proteus copper as built (STATUS.md "Phase 3", `kipy -m p2k.measure_gaps`), mm.
PCB_RULES = dict(
    min_track=0.15,       # thinnest conductor draw 0.1524 (6 mil)
    min_via=0.5,          # vias 0.5/0.3 (139) and 1.016/0.381 (2)
    min_annular=0.1,      # (0.5 - 0.3) / 2
    min_drill=0.3,
    clearance=0.12,       # smallest different-net gap 0.1265 (5 mil: track-via, pad-track, track-track; 52 pairs < 0.14)
    hole_clearance=0.15,  # via drills: 0.1 annular + >= 0.1265 gap
    hole_to_hole=0.25,    # smallest drill-to-drill 0.401
    edge_clearance=0.2,   # copper to outline >= 0.2286 (In2.Cu pour)
    track=0.254,          # Default netclass
    via=0.5,
    via_drill=0.3,
)

# Error-severity DRC types that remain by design ({type: reason}, STATUS.md "Phase 3").
DRC_ACCEPTED = {
    "courtyards_overlap": "KiCad IPC-7351 courtyards vs the Proteus placement (parts at the Proteus positions)",
}

# Proteus copper deliberately not built (user decision 2026-11-20, finding 14; reverses the Phase 5
# keep decision). IPC frame, {(layer, x1, y1, x2, y2): reason} (p2k gerber_to_tracks; accepted by
# check_board, ipc356_diff, gerber_roundtrip).
# The two zero-length OUT1 draws are one 1e-5 mm segment drawn in both directions: one entry with the
# count 2 matches both (p2k I7; until 2026-11-20 the board-local tools/remove_dot_tracks.py and its
# REMOVED_DOT_TRACKS key; migration re-baseline accepted by the user, decision D-I7). They lie inside
# the two 0.762 mm OUT1 tracks that meet there, so the copper is unchanged.
REMOVED_TRACKS = {
    ("B.Cu", -73.6, -20.2, -72.7, -20.2): "15V_BOOST: dangling 0.9 mm stub, 0.762 mm wide (finding 14)",
    ("B.Cu", -32.85196, -11.53736, -32.85196, -11.53737): (
        "OUT1: two zero-length draws (both directions) inside the OUT1 track junction (finding 14)", 2),
}

# --- Pin order (Phase 2, p2k check_pin_order) ----------------------------------------------
# The UNMOVED KiCad base footprints with the Proteus renumbering fitted onto the IPC pads (STATUS.md
# "Phase 2 - pin order"); `spec=` takes base + renumbering from tools/gen_footprints.py PROJECT, so a
# wrong renumbering there fails here although p2k.footprints.derive moves the pads onto the IPC
# positions. Two-pad / inline patterns fit both ways (body markers by --render); dual-row SMD
# packages are symmetric under 180 deg (the nets decide pin 1, Phase 1). mirror=None = "does not fit
# on top" (unmirrored residual > 0.1 mm).
PIN_ORDER = [
    dict(name="REF1", refs="REF1", spec="SOT-23_Proteus", mirror=False, res=0.03,
         note="SOT-23 renumbered (1 = JEDEC 3): fits; Proteus 1.90 mm rows vs KiCad 1.875"),
    dict(name="REF1 plain", refs="REF1", footprint="Package_TO_SOT_SMD:SOT-23", mirror=None,
         note="SOT-23 with JEDEC numbering: does not fit (> 0.1 mm, angle not snapped)"),
    dict(name="ADC", refs="ADC1 ADC2 ADC3", spec="SOT-23-6_ADC121C027_Proteus_ProteusPads", mirror=False, res=0.19,
         note="A1 A2 COM2 K2 K1 COM1 = JEDEC 1-6: fits (rows 2.65 vs KiCad 2.275 -> 0.1875)"),
    dict(name="ADC datasheet", refs="ADC1 ADC2 ADC3", footprint="Package_TO_SOT_SMD:SOT-23-6",
         renumber={"1": "COM2", "2": "A2", "3": "A1", "4": "COM1", "5": "K1", "6": "K2"}, mirror=None,
         note="VA / VIN exchanged (COM2 on pad 1, A1 on pad 3, the datasheet wiring): fits only mirrored, "
              "i.e. not on a top-side part (finding 6)"),
    dict(name="SI8271", refs="DRV1 DRV2", spec="SOIC-8_3.9x4.9mm_P1.27mm_Proteus", mirror=True, res=0.28,
         note="bottom side, rows 5.5 vs 4.95"),
    dict(name="SI8271 Proteus pads", refs="DRV5 DRV6", spec="SOIC-8_3.9x4.9mm_P1.27mm_Proteus_ProteusPads",
         mirror=True, res=0.28, render=False,
         note="bottom side, rows 5.5 vs 4.95 (spec with the Proteus pad sizes)"),
    dict(name="TSSOP-14", refs="U1 U2", spec="TSSOP-14_4.4x5mm_P0.65mm_Proteus_ProteusPads", mirror=False, res=0.07,
         note="rows 5.85 vs 5.725"),
    dict(name="J1", refs="J1", spec="PinHeader_2x20_P1.27mm_Vertical_ProteusPads", mirror=False, res=0.01,
         polarity="1", note="standard numbering on the IPC_PIN_IDS pads: fits on top, pin 1 on the marked pad"),
    dict(name="J1 Proteus ids", refs="J1", footprint="Connector_PinHeader_1.27mm:PinHeader_2x20_P1.27mm_Vertical",
         renumber={str(k): str(k + 1 if k % 2 else k - 1) for k in range(1, 41)}, mirror=None, render=False,
         note="the Proteus odd / even numbering does not fit on top any more (the IPC pins are renumbered, finding 12)"),
    dict(name="J2", refs="J2", spec="PinHeader_2x08_P1.27mm_Vertical_ProteusPads", mirror=False, res=0.01,
         note="standard numbering fits on top (spec with the Proteus pad sizes)"),
    dict(name="TO-220", refs="Q3 Q4 Q7 Q8", spec="TO-220-3_Vertical_ProteusPads", mirror=False, res=0.01,
         note="inline: marker by render (spec with the Proteus pads)"),
    dict(name="SMA", refs="D2 D18", spec="D_SMA_AC", mirror=True, res=0.051, note="two pads: band by render"),
    dict(name="CP", refs="C1 C2 C3 C4 C5 C6 C7 C11 C26", footprint="Capacitor_THT:CP_Radial_D10.0mm_P5.00mm",
         mirror=False, res=0.01, note="two pads: '+' by render"),
]

# --- Pad decisions (Phase 5, p2k check_pads) -------------------------------------------------
# The parts that must have exactly the Proteus pads (gerber flash bbox / area, drill) on the board:
# user decisions A2 (Phase 3) + J2, Q3 Q4 Q7 Q8 and J1 round (Phase 5, 2026-11-20) except J1-1, square since
# the J1 renumbering (user decision 2026-11-20; check_all.sh accepts exactly the J1-1 area). Written out
# independently of tools/gen_footprints.py PROTEUS_PADS (the two must agree; a part taken out of the
# footprint rules fails here).
PROTEUS_PADS_CHECK = "U1 U2 ADC1 ADC2 ADC3 DRV5 DRV6 J1 J2 Q3 Q4 Q7 Q8".split()
