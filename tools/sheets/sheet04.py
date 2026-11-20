#!/usr/bin/env python3
"""Sheet 4 - Current measurements (PDF page 4): U2 (LT1014, units A-D) as four shunt
amplifiers. Each unit: shunt signal -> 330R -> + input, biased to +1V0_BIAS through 6.8k / 20p;
- input 330R to GND with 6.8k / 20p feedback (gain 6.8k / 330R); output through 100R / 100p to
the control card (J1, sheet 5). U2's supply pins (unit 5: 4 = 3V3, 11 = GND) are drawn once,
with C34; the PDF repeats them on every unit.

Net names as the IPC has them (PDF lower case -> upper case). They do not match what is
measured (STATUS.md finding 7): U2:A C3_CURRENT -> INPUT_CURRENT_MEAS, U2:B C1_CURRENT ->
C1_CURRENT_MEAS, U2:C CURRENT_L1 -> C2_CURRENT_MEAS, U2:D CURRENT_L3 -> C3_CURRENT_MEAS."""
from _common import *  # noqa: F401,F403

sh = sheet("04_current_measurements.kicad_sch")

#        unit pins(+,-,out) PDF pos   r_in   r_bias c_bias r_gnd  r_fb   c_fb   r_out  c_out  input         output
CELLS = [(1, (3, 2, 1), (48, 39), "R56", "R54", "C45", "R52", "R53", "C13", "R55", "C14", "C3_CURRENT", "INPUT_CURRENT_MEAS"),
         (2, (5, 6, 7), (149, 39), "R61", "R59", "C47", "R57", "R58", "C15", "R60", "C16", "C1_CURRENT", "C1_CURRENT_MEAS"),
         (3, (10, 9, 8), (48, 104), "R66", "R64", "C44", "R62", "R63", "C17", "R65", "C18", "CURRENT_L1", "C2_CURRENT_MEAS"),
         (4, (12, 13, 14), (149, 104), "R71", "R69", "C48", "R67", "R68", "C19", "R70", "C20", "CURRENT_L3", "C3_CURRENT_MEAS")]
for unit, pins, pos, *rest in CELLS:
    shunt_amp_cell(sh, "U2", unit, *P(*pos), pins, *rest)

# --- U2 supply (unit 5) and C34 (pin 2 = 3V3, pin 1 = GND) ---------------------------------------
PX, PY = P(4, 72)
u = sh.place(sym("U2"), "U2", PX, PY, unit=5, value=sh_value("U2"))
VP, VN = u.pin(4), u.pin(11)
YT, YB = VP[1] - g(2), VN[1] + g(2)
xc = VP[0] + g(14)
sh.wire(VP, (VP[0], YT), (VP[0], YT - g(2)))
power_at(sh, "3V3", (VP[0], YT - g(2)), "up")
sh.wire(VN, (VN[0], YB), (VN[0], YB + g(2)))
power_at(sh, "GND", (VN[0], YB + g(2)), "down")
_, ct, cb = vert2(sh, "C", "C34", xc, PY, sh_value("C34"), top=2)
sh.wire((VP[0], YT), (xc, YT), ct)
sh.junction(VP[0], YT)
sh.wire((VN[0], YB), (xc, YB), cb)
sh.junction(VN[0], YB)

# --- notes ---------------------------------------------------------------------------------------
NX, NY = P(4, 132)
sh.text("Net names = IPC (PDF: C3_current, input_current_meas, ...). They do not match what is measured (STATUS.md finding 7):", NX, NY)
sh.text("U2:A C3_CURRENT -> INPUT_CURRENT_MEAS, U2:C CURRENT_L1 -> C2_CURRENT_MEAS, U2:D CURRENT_L3 -> C3_CURRENT_MEAS.", NX, NY + g(2))
sh.text("U2 supply pins 4 / 11 drawn once (the PDF repeats them on every unit). PWR_FLAGs of 3V3, GND, +1V0_BIAS: sheet 5.", NX, NY + g(4))

sh.save()
print("sheet04: written")
