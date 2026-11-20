#!/usr/bin/env python3
"""Sheet 3 - Voltage measurements (PDF page 3): U1 (LMV324A, units A-D) as four difference
amplifiers. Each unit: the measured voltage through 3 x 1M to the + input with 15k to GND; GND
through 3 x 1M to the - input with 15k feedback (gain 15k / 3M = 1 / 200); output through
100R / 100p to the control card (J1, sheet 5). U1:C UIN -> UIN_MEAS, U1:D UC3 -> UC3_MEAS,
U1:B V_A -> V_A_MEAS, U1:A U_OUT -> U_OUT_MEAS. U1's supply pins (unit 5: 4 = 3V3, 11 = GND)
are drawn once, with C12; the PDF repeats them on every unit and draws C12 at U1:A.

Net names as the IPC has them (PDF Uin_meas, Uc3_meas, U_out_meas, V_A_meas; gnd = GND)."""
from _common import *  # noqa: F401,F403

sh = sheet("03_voltage_measurements.kicad_sch")

#        unit pins(+,-,out) PDF pos     GND divider            signal divider         r_pgnd r_fb   r_out  c_out  input    output
CELLS = [(3, (10, 9, 8), (52, 51), ("R4", "R5", "R6"), ("R7", "R8", "R9"), "R2", "R1", "R3", "C39", "UIN", "UIN_MEAS"),
         (4, (12, 13, 14), (144, 54), ("R13", "R14", "R15"), ("R16", "R17", "R18"), "R11", "R10", "R12", "C42", "UC3", "UC3_MEAS"),
         (2, (5, 6, 7), (48, 117), ("R37", "R38", "R39"), ("R40", "R41", "R42"), "R20", "R19", "R36", "C40", "V_A", "V_A_MEAS"),
         (1, (3, 2, 1), (140, 118), ("R46", "R47", "R48"), ("R49", "R50", "R51"), "R44", "R43", "R45", "C41", "U_OUT", "U_OUT_MEAS")]
for unit, pins, pos, *rest in CELLS:
    diff_amp_cell(sh, "U1", unit, *P(*pos), pins, *rest)

# --- U1 supply (unit 5) and C12 (pin 1 = 3V3, pin 2 = GND) ---------------------------------------
PX, PY = P(-16, 72)
u = sh.place(sym("U1"), "U1", PX, PY, unit=5, value=sh_value("U1"))
VP, VN = u.pin(4), u.pin(11)
YT, YB = VP[1] - g(2), VN[1] + g(2)
xc = VP[0] + g(14)
sh.wire(VP, (VP[0], YT), (VP[0], YT - g(2)))
power_at(sh, "3V3", (VP[0], YT - g(2)), "up")
sh.wire(VN, (VN[0], YB), (VN[0], YB + g(2)))
power_at(sh, "GND", (VN[0], YB + g(2)), "down")
_, ct, cb = vert2(sh, "C", "C12", xc, PY, sh_value("C12"), top=1)
sh.wire((VP[0], YT), (xc, YT), ct)
sh.junction(VP[0], YT)
sh.wire((VN[0], YB), (xc, YB), cb)
sh.junction(VN[0], YB)

# --- notes ---------------------------------------------------------------------------------------
NX, NY = P(4, 142)
sh.text("Net names = IPC (PDF: Uin_meas, Uc3_meas, V_A_meas, U_out_meas; gnd = GND). UIN, UC3, V_A, U_OUT: sheet 1; *_MEAS: J1, sheet 5.", NX, NY)
sh.text("U1 supply pins 4 / 11 drawn once (the PDF repeats them on every unit; C12 is drawn at U1:A there). PWR_FLAGs of 3V3, GND: sheet 5.", NX, NY + g(2))

sh.save()
print("sheet03: written")
