#!/usr/bin/env python3
"""Sheet 2 - Gate drivers (PDF page 2): four SI8271 isolated gate drivers in two half-bridge
pairs. DRV1 (high side, G1_HI -> PWM1_HI, floating on OUT1, bootstrap D18 / R21 / C46) and DRV2
(low side, G1_LO -> PWM1_LO); DRV5 (high side, G3_HI -> PWM3_HI, floating on OUT2, bootstrap
D2 / R31 / C30) and DRV6 (low side, G3_LO -> PWM3_LO). Each driver has 15R on OUT+ and 8R on
OUT-, joined at the gate.

PDF `15V` = 15V_BOOST (one IPC net, see sheet 5), `gnd` = GND. The PDF prints the refdes R23 /
R25 / R32 / R35 next to the GND2 pins; they are the 8R resistors on OUT- (IPC). The SI8271 box
symbol has its left pins in the order VDD1, Vin, EN, GND1 (PDF: Vin, VDD1, GND1, EN), so the
input-side wiring is laid out differently; the nets are the same."""
from _common import *  # noqa: F401,F403

sh = sheet("02_gate_drivers.kicad_sch")

#        ref     PDF pos     Vin      cdec   r_on   r_off  gate       cvdd2  boot            src    bulk
CELLS = [("DRV1", (50, 60), "G1_HI", "C25", "R22", "R23", "PWM1_HI", "C46", ("D18", "R21"), "OUT1"),
         ("DRV2", (50, 98), "G1_LO", "C24", "R24", "R25", "PWM1_LO", "C23", None, None),
         ("DRV5", (152, 60), "G3_HI", "C33", "R33", "R32", "PWM3_HI", "C30", ("D2", "R31"), "OUT2"),
         ("DRV6", (152, 98), "G3_LO", "C32", "R34", "R35", "PWM3_LO", "C31", None, None)]
for ref, pos, vin, cdec, r_on, r_off, gate, cvdd2, boot, src in CELLS:
    si8271_cell(sh, ref, *P(*pos), vin, cdec, r_on, r_off, gate, cvdd2, boot=boot, src=src)

# --- bulk capacitors of the driver supply, one per pair (pin 1 = 15V_BOOST, pin 2 = GND) ----------
for ref, pos in (("C38", (24, 120)), ("C43", (126, 120))):
    x, y = P(*pos)
    _, ct, cb = vert2(sh, "C", ref, x, y, sh_value(ref), top=1)
    sh.wire(ct, up(ct, 2))
    power_at(sh, "15V_BOOST", up(ct, 2), "up")
    sh.wire(cb, down(cb, 2))
    power_at(sh, "GND", down(cb, 2), "down")

# --- notes ---------------------------------------------------------------------------------------
NX, NY = P(14, 136)
sh.text("PDF 15V = 15V_BOOST (J1-39/40, sheet 5); PDF gnd = GND. PWR_FLAGs of 15V_BOOST, 3V3, GND: sheet 5.", NX, NY)
sh.text("PWR_FLAGs here: the bootstrap nodes (DRV1-8, DRV5-8) and the switch nodes OUT1 / OUT2 (GND2 of DRV1 / DRV5).",
        NX, NY + g(2))
sh.text("R23 / R25 / R32 / R35 (8R) are on OUT- (IPC); the PDF prints their refdes next to the GND2 pins.", NX, NY + g(4))

sh.save()
print("sheet02: written")
