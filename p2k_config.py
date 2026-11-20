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
    (5, "Reference and connector", "05_reference_connector.kicad_sch"),  # REF1 +2V5_BIAS, J1 40-pin ribbon
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
# names. No renames (the +2V5_BIAS name question is a finding, STATUS.md).
NET_ALIASES = {}

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
    "nc_pads": 2,         # J1-37, J1-38
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
