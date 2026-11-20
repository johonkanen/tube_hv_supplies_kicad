#!/usr/bin/env python3
"""Footprint assignment and the project footprint library of the HV supplies board (stdlib only).

Writes (through the shared generator tools/p2k/p2k/footprints.py)
  lib/footprint_map.csv          refdes -> footprint for all 160 parts of lib/part_map.csv
                                 (158 on the board; L1 / L3 off board: OFF_BOARD_PARTS)
  lib/tube_hv_supplies.pretty/   project footprints: derived from KiCad library footprints (pads
                                 renumbered to the Proteus ids, pad centres moved onto the Proteus
                                 positions) or built from the IPC-D-356A pads where KiCad has nothing
  kicad/fp-lib-table             registers the project library (board-local: footprints.run does
                                 not write it; STATUS.md "p2k candidates")

Usage: python3 tools/gen_footprints.py [--check]      (needs the KiCad AppImage mount)

This file holds what is decided for this board: RULES (symbol + IPC pad pattern -> footprint)
and PROJECT (the project footprint specs); the rule syntax and the spec keys are documented in
tools/p2k/p2k/footprints.py. Pad numbers always equal the IPC pin ids.

Pad sizes: p2k_config.py FOOTPRINT_PAD_SIZES = "kicad" (KiCad library pads and drills; the
footprints built from the IPC pads - blade and wire terminals - and the KRL2012 shunt land
pattern have the Proteus pads), except the PROTEUS_PADS parts (user decision A2, Phase 3). tools/p2k check_footprints verifies every footprint against the
IPC pads (residual < 0.05 mm per pad) and reports the pad size / drill differences.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "p2k"))  # proteus2kicad
from p2k import footprints  # noqa: E402

P = "tube_hv_supplies:"

# Phase 3 pad-size decision (user, 2026-11-20, option A2; STATUS.md "Phase 3 - pad sizes",
# Decisions): these 8 parts get the Proteus pad sizes (and J1 the Proteus drill 0.558 mm) because
# their KiCad pads short or come closer than 0.12 mm to the Proteus tracks (DRC with KiCad pads:
# 3 shorts, 29 clearance, 3 solder-mask bridges, all at these parts). Every other part keeps the
# KiCad pads. The rules with `refdes=PROTEUS_PADS` come before the general rule of their symbol;
# p2k.footprints fails if a refdes listed here is taken by no such rule.
PROTEUS_PADS = frozenset("""
    U1 U2 ADC1 ADC2 ADC3 DRV5 DRV6 J1
""".split())

# (symbol, conditions, footprint, note). Conditions: n = pad count, tht, span (mm, +-0.02),
# pad = (w, h) of the IPC pads, drill, package / device (lib/part_map.csv columns), refdes.
RULES = [
    # --- resistors
    ("R", dict(tht=False, span=0.915, pad=(0.508, 0.762)), P + "R_0402_1005Metric_Proteus0.91",
     "0402 (Proteus pads 0.91 mm apart)"),
    ("R", dict(tht=False, span=0.975, pad=(0.35, 2.0)), P + "R_0508_1220Metric_KRL2012",
     "KRL2012 0508 shunt, long-side terminals, Proteus land pattern"),
    ("R", dict(tht=False, span=1.727, pad=(0.889, 0.889)), "Resistor_SMD:R_0603_1608Metric", "0603 (Proteus pads 1.73 mm apart)"),
    ("R", dict(tht=False, span=2.90, pad=(1.143, 1.803)), "Resistor_SMD:R_1206_3216Metric", "1206 (RESC3216X65)"),
    ("R", dict(tht=False, span=3.15, pad=(1.016, 1.524)), "Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder",
     "1206 (Proteus pads 3.15 mm apart)"),
    # --- capacitors
    ("C", dict(tht=False, span=0.90, pad=(0.609, 0.609)), "Capacitor_SMD:C_0402_1005Metric", "0402 (CAPC1005X55)"),
    ("C", dict(tht=False, span=1.60, pad=(0.939, 0.99)), "Capacitor_SMD:C_0603_1608Metric", "0603 (CAPC1608X87)"),
    ("C", dict(tht=False, span=1.727, pad=(0.889, 0.889)), "Capacitor_SMD:C_0603_1608Metric_Pad1.08x0.95mm_HandSolder",
     "0603 (Proteus pads 1.73 mm apart)"),
    ("C", dict(tht=False, span=3.15, pad=(1.016, 1.524)), "Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder",
     "1206 (Proteus pads 3.15 mm apart)"),
    ("C", dict(tht=False, span=5.20, pad=(1.397, 5.257)), "Capacitor_SMD:C_2220_5750Metric_Pad1.97x5.40mm_HandSolder",
     "2220 (CAPC5750X230)"),
    ("C_Polarized", dict(tht=True, span=5.00, drill=0.812), "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm",
     "10 mm radial electrolytic P5, pad 1 = + (KiCad pad 1)"),
    # --- semiconductors
    ("D", dict(tht=False, span=4.10), P + "D_SMA_AC", "SMA (DIOM5025X231), pads A/C"),
    ("IKP08N65F5", dict(tht=True, span=5.08), "Package_TO_SOT_THT:TO-220-3_Vertical", "TO-220, 1=G 2=C 3=E"),
    ("ISL21010", dict(), P + "SOT-23_Proteus", "SOT-23, Proteus pad numbering (1 = JEDEC 3, 2 = JEDEC 1, 3 = JEDEC 2)"),
    ("ADC121C027", dict(refdes=PROTEUS_PADS), P + "SOT-23-6_ADC121C027_Proteus_ProteusPads",
     "SOT-23-6, Proteus pin ids A1 A2 COM2 K2 K1 COM1 = pads 1-6, rows 2.65 mm apart, Proteus pad size"),
    ("LMV324A", dict(refdes=PROTEUS_PADS), P + "TSSOP-14_4.4x5mm_P0.65mm_Proteus_ProteusPads",
     "TSSOP-14, Proteus pad rows 5.85 mm apart, Proteus pad size"),
    ("LT1014", dict(refdes=PROTEUS_PADS), P + "TSSOP-14_4.4x5mm_P0.65mm_Proteus_ProteusPads",
     "TSSOP-14, Proteus pad rows 5.85 mm apart, Proteus pad size"),
    ("SI8271", dict(refdes=PROTEUS_PADS), P + "SOIC-8_3.9x4.9mm_P1.27mm_Proteus_ProteusPads",
     "SOIC-8, Proteus pad rows 5.5 mm apart, Proteus pad size"),
    ("SI8271", dict(), P + "SOIC-8_3.9x4.9mm_P1.27mm_Proteus", "SOIC-8, Proteus pad rows 5.5 mm apart"),
    # --- magnetics, connectors, terminals
    ("L", dict(tht=False, span=10.0), P + "L_Bourns_SRP1038C_10.0x10.0mm_Proteus",
     "Bourns SRP1038CC, Proteus pads 10.0 mm apart"),
    ("HEADER_2X20_50MIL", dict(refdes=PROTEUS_PADS), P + "PinHeader_2x20_P1.27mm_Vertical_RowsSwapped_ProteusPads",
     "2x20 1.27 mm header (IDC), Proteus numbering with the odd / even rows swapped, pins 37 / 38 N/C, "
     "Proteus pad size"),
    ("HEADER_2X8_50MIL", dict(), "Connector_PinHeader_1.27mm:PinHeader_2x08_P1.27mm_Vertical", "2x8 1.27 mm header"),
    ("PIN", dict(n=2), P + "Terminal_2x1_P5.00mm_D2.0mm_Drill1.4mm", "blade terminal, two holes both pad 1"),
    ("PIN", dict(n=1), P + "Terminal_1x1_D2.54mm_Drill1.524mm", "wire terminal of an off-board inductor, one hole"),
]

# Project footprints (spec keys: see p2k.footprints). `ipc` = refdes whose IPC pads give the
# pad centres; the footprint is built for the top side and mirrored by placement when needed.
PROJECT = {
    # KiCad's 0402 pads are 1.02 mm apart: 0.053 mm off at the Proteus 0.914 mm
    "R_0402_1005Metric_Proteus0.91": dict(
        base="Resistor_SMD:R_0402_1005Metric", ipc="R1",
        descr="0402 resistor, Proteus pad centres 0.91 mm apart"),
    # KiCad's 0508 pads (0.95 wide, 1.15 apart) would overlap at the Proteus centres 0.975 mm apart:
    # the Proteus pads (0.35 x 2.0) are the only ones that work -> ipc_sizes (as tube_psu)
    "R_0508_1220Metric_KRL2012": dict(
        base="Resistor_SMD:R_0508_1220Metric", ipc="R29", ipc_sizes=True,
        descr="KRL2012 0508 shunt resistor (long-side terminals), Proteus land pattern"),
    # SMA: KiCad pad 1 = cathode (band side)
    "D_SMA_AC": dict(
        base="Diode_SMD:D_SMA", renumber={"1": "C", "2": "A"}, ipc="D2",
        descr="SMA diode, pads C (KiCad pad 1, band) / A, Proteus pad positions"),
    # SOT-23 with Proteus pad numbering: pad 1 sits alone on one side (JEDEC pin 3), pads 2 and 3
    # are JEDEC pins 1 and 2 (check_pin_order confirms the chirality on REF1)
    "SOT-23_Proteus": dict(
        base="Package_TO_SOT_SMD:SOT-23", renumber={"3": "1", "1": "2", "2": "3"}, ipc="REF1",
        descr="SOT-23 with Proteus pad numbering: pad 1 = JEDEC pin 3 (single side), pad 2 = JEDEC pin 1, "
              "pad 3 = JEDEC pin 2; Proteus pad positions"),
    # ADC121C027 with the Proteus pin ids (diode-array style package names): JEDEC pads 1-6 =
    # A1 A2 COM2 K2 K1 COM1 (check_pin_order confirms; finding 6 for what that means)
    # Phase 3 pad decision (PROTEUS_PADS): `_ProteusPads` = ipc_sizes=True (Proteus pad size; the
    # KiCad-pad specs of ADC1-3, U1 / U2 and J1 are no longer used and were dropped)
    "SOT-23-6_ADC121C027_Proteus_ProteusPads": dict(
        base="Package_TO_SOT_SMD:SOT-23-6",
        renumber={"1": "A1", "2": "A2", "3": "COM2", "4": "K2", "5": "K1", "6": "COM1"}, ipc="ADC1", ipc_sizes=True,
        descr="SOT-23-6 (ADC121C027), Proteus pin ids A1 A2 COM2 K2 K1 COM1 on pads 1-6, "
              "Proteus pad positions (rows 2.65 mm apart); Proteus pad sizes"),
    "TSSOP-14_4.4x5mm_P0.65mm_Proteus_ProteusPads": dict(
        base="Package_SO:TSSOP-14_4.4x5mm_P0.65mm", ipc="U1", ipc_sizes=True,
        descr="TSSOP-14, Proteus pad positions (rows 5.85 mm apart); Proteus pad sizes"),
    "SOIC-8_3.9x4.9mm_P1.27mm_Proteus": dict(
        base="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", ipc="DRV1",
        descr="SOIC-8, Proteus pad positions (rows 5.5 mm apart)"),
    "SOIC-8_3.9x4.9mm_P1.27mm_Proteus_ProteusPads": dict(
        base="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", ipc="DRV5", ipc_sizes=True,
        descr="SOIC-8, Proteus pad positions (rows 5.5 mm apart); Proteus pad sizes"),
    "L_Bourns_SRP1038C_10.0x10.0mm_Proteus": dict(
        base="Inductor_SMD:L_Bourns_SRP1038C_10.0x10.0mm", ipc="L2",
        descr="Bourns SRP1038C inductor, Proteus pad centres 10.0 mm apart"),
    # J1: the Proteus IDC footprint is numbered as the mirror image of a standard header seen from
    # the top (pin 2 where KiCad has pin 1's row neighbour on the other side; check_pin_order: the
    # KiCad header fits only mirrored, i.e. as a bottom-side part, but J1 is on the top side by the
    # Proteus assembly / silk layers). Swapping the odd / even pad numbers gives the Proteus
    # pattern on the top side (STATUS.md "Phase 2 - pin order", finding 12).
    "PinHeader_2x20_P1.27mm_Vertical_RowsSwapped_ProteusPads": dict(
        base="Connector_PinHeader_1.27mm:PinHeader_2x20_P1.27mm_Vertical",
        renumber={str(k): str(k + 1 if k % 2 else k - 1) for k in range(1, 41)}, ipc="J1", ipc_sizes=True,
        descr="2x20 1.27 mm header, Proteus numbering: odd / even pad numbers swapped (pad 1 at KiCad's "
              "pad 2 position, KiCad's pin-1 marking stays at the pad now numbered 2); Proteus pad sizes"),
    "Terminal_2x1_P5.00mm_D2.0mm_Drill1.4mm": dict(
        ipc="B_P", descr="Blade wire terminal, two holes both pad 1"),
    "Terminal_1x1_D2.54mm_Drill1.524mm": dict(
        ipc="L5", descr="Wire terminal (end of an off-board inductor lead), one 2.54 mm pad, drill 1.524"),
    # Board-only (no symbol; placed by p2k.build_pcb at the 4 IPC 'hole' records)
    "MountingHole_3.0mm_PTH_Pad6.35mm": dict(
        board_only=True, pad=(6.35, 3.0), plated=True,
        descr="Plated 3.0 mm mounting hole with a 6.35 mm pad on all copper layers, no net"),
}

FP_LIB_TABLE = """(fp_lib_table
\t(version 7)
\t(lib (name "tube_hv_supplies")(type "KiCad")(uri "${KIPRJMOD}/../lib/tube_hv_supplies.pretty")(options "")(descr "Project footprints, pad numbers = IPC pin ids (tools/gen_footprints.py)"))
)
"""


def fp_lib_table(check):
    path = os.path.join(ROOT, "kicad", "fp-lib-table")
    cur = open(path).read() if os.path.exists(path) else None
    if cur == FP_LIB_TABLE:
        return True
    if check:
        print("gen_footprints: out of date: kicad/fp-lib-table")
        return False
    with open(path, "w") as f:
        f.write(FP_LIB_TABLE)
    print("gen_footprints: wrote kicad/fp-lib-table")
    return True


if __name__ == "__main__":
    ok = fp_lib_table("--check" in sys.argv[1:])
    try:
        footprints.run(RULES, PROJECT)
    except SystemExit as e:
        sys.exit(e.code if ok else 1)
