#!/usr/bin/env python3
"""Generate lib/tube_hv_supplies.kicad_sym, the project symbol library (helpers: p2k.symgen).

Pin numbers equal the Proteus/IPC pin ids (STATUS.md "Phase 1 preparation"); box symbols carry
the Proteus pin names printed in the PDF. Simple symbols are copied from the KiCad 10 standard
library (flattened, pins renumbered where needed):
  R, C, C_Polarized (pin 1 = +), L          1, 2
  D (S1M)                                   A, C
  IKP08N65F5 (TO-220, Device:Q_NIGBT_GCE)   1=G 2=C 3=E
  LMV324A, LT1014 (TSSOP-14 quad op-amps)   standard quad pinout, unit 5 = V+ (4) / V- (11)
  PIN (Proteus TERMINAL)                    1 (the blade connectors have two holes, both pin 1)
Box symbols:
  SI8271      1 Vin 2 VDD1 3 GND1 4 EN | 5 GND2 6 OUT- 7 OUT+ 8 VDD2 (as tube_psu)
  ISL21010    Proteus ids 1=GND 2=VIN 3=VOUT (Proteus device ADR380; the ISL21010 / ADR380
              datasheets number the SOT-23 1=VIN 2=VOUT 3=GND: the Proteus footprint is renumbered)
  ADC121C027  Proteus ids A1=VA A2=GND COM2=VIN | COM1=SDA K1=SCL K2=ADR0
  HEADER_2X20_50MIL (J1), HEADER_2X8_50MIL (J2)   odd pins left, even right
Off-board (drawn in the PDF, no pads; excluded from the board): L_OFFBOARD (L1, L3, 3 mH).
Power symbols for the four rails drawn with power symbols (transcription rules): GND, 3V3,
15V_BOOST, +1V0_BIAS (IPC +2V5_BIAS renamed through p2k_config.NET_ALIASES, user decision 2026-11-20, finding 1).

Run:  tools/gen_symbols.py           (needs the AppImage mount for the std libs)
      tools/gen_symbols.py --check   (fail if lib/tube_hv_supplies.kicad_sym is not up to date)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "p2k"))  # proteus2kicad
from p2k.symgen import *  # noqa: E402,F401,F403
from p2k.symgen import run  # noqa: E402

GROUNDS = ["GND"]
SUPPLIES = ["3V3", "15V_BOOST", "+1V0_BIAS"]


def quad_opamp(name, desc):
    # KiCad LM324 (extends LM2902): units 1-4 = A-D (1/2/3, 7/6/5, 8/9/10, 14/13/12), unit 5 = V+ 4 / V- 11
    return from_std("Amplifier_Operational", "LM324", name, "U", name, desc=desc)


def build():
    syms = [
        from_std("Device", "R", "R", "R", "R"),
        from_std("Device", "C", "C", "C", "C"),
        from_std("Device", "C_Polarized", "C_Polarized", "C", "C", desc="Polarized capacitor, pin 1 = +"),
        from_std("Device", "L", "L", "L", "L"),
        from_std("Device", "D", "D", "D", desc="Diode, pins A/C as in Proteus", pins={"1": "C", "2": "A"}),
        from_std("Device", "Q_NIGBT_GCE", "IKP08N65F5", "Q", "IKP08N65F5",
                 desc="N-channel IGBT TO-220 (IKP08N65F5; Proteus device IRGB14C40L), Proteus ids 1=G 2=C 3=E"),
        quad_opamp("LMV324A", "Quad op-amp TSSOP-14 (LMV324A), standard quad pinout; unit 5 = supply"),
        quad_opamp("LT1014", "Quad op-amp TSSOP-14 (LT1014), standard quad pinout; unit 5 = supply"),
        from_std("Connector", "TestPoint", "PIN", "J", "TERMINAL",
                 desc="Proteus TERMINAL: blade connector (two holes, both pad 1) or single-pin terminal"),
    ]
    loff = from_std("Device", "L", "L_OFFBOARD", "L", desc="Off-board inductor (drawn in the schematic, "
                    "no pads; excluded from board): wired to single-pin terminals")
    set_flag(loff, "on_board", False)
    syms.append(loff)

    syms += [
        box("SI8271", "DRV", [(2, "VDD1", PI), (1, "Vin", IN), (4, "EN", IN), (3, "GND1", PI)],
            [(8, "VDD2", PI), (7, "OUT+", OUT), (6, "OUT-", OUT), (5, "GND2", PI)],
            desc="Isolated single gate driver SOIC-8"),
        box("ISL21010", "REF", [(2, "VIN", PI)], [(3, "VOUT", PO)], bottom=[(1, "GND", PI)],
            desc="Voltage reference SOT-23 (ISL21010; Proteus device ADR380); Proteus pin ids 1=GND 2=VIN "
                 "3=VOUT (datasheet: 1=VIN 2=VOUT 3=GND)"),
        # VA is passive, not power_in: the schematic feeds VA from the analog input (R78-R80 /
        # C35-C37) and VIN from 3V3 (STATUS.md finding 6); a power_in VA would be an undriven-power
        # ERC error on the input nets. ADR0 is passive: a three-state address pin (3V3 / GND /
        # open), and ADC3's ADR0 is alone on the net FLOATING (an input would be "not driven").
        box("ADC121C027", "ADC", [("COM2", "VIN", IN), ("A1", "VA", PAS), ("A2", "GND", PI)],
            [("K1", "SCL", IN), ("COM1", "SDA", "bidirectional"), ("K2", "ADR0", PAS)],
            desc="12-bit I2C ADC SOT-23-6, Proteus pin ids A1=VA A2=GND COM2=VIN COM1=SDA K1=SCL K2=ADR0"),
    ]
    l, r = header(range(1, 41))
    syms.append(box("HEADER_2X20_50MIL", "J", l, r, show_pin_names=False,
                    desc="Control-card ribbon connector 2x20, 1.27 mm (pins 37, 38 not connected)"))
    l, r = header(range(1, 17))
    syms.append(box("HEADER_2X8_50MIL", "J", l, r, show_pin_names=False, desc="ADC input header 2x8, 1.27 mm"))

    syms.append(rename(std_symbol("power", "PWR_FLAG"), "PWR_FLAG"))
    syms += [power(n, True) for n in GROUNDS] + [power(n, False) for n in SUPPLIES]
    return syms


if __name__ == "__main__":
    if "--force-regenerate" not in sys.argv:
        sys.exit("gen_symbols: frozen since generation stopped (STATUS.md Decisions, D-STOP): the committed "
                 "KiCad files are edited by hand now. Re-running would overwrite the hand edits; pass "
                 "--force-regenerate only to reproduce the history in a scratch copy.")
    sys.argv.remove("--force-regenerate")
    sys.exit(run(build))
