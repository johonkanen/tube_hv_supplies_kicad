#!/usr/bin/env python3
"""Sheet 5 - Reference and connector (PDF page 5): the reference REF1 (ISL21010) from 3V3 with
C8 / C21, R74 -> +1V0_BIAS with R73 / C22 to GND, and the control-card ribbon connector J1
(2x20, 1.27 mm).

PDF: J1 pins 1-8 are labelled ADB0-ADB7 and tied to the *_meas nets by separate terminal links
(lower left of the page); KiCad puts the IPC net names on the pins and keeps ADBn as small
texts. The four current-measurement nets on J1-2/4/6/8 (Proteus J1-1/3/5/7) are renamed through NET_ALIASES
(STATUS.md "Design fixes 2026-11-20", finding 7). The link `15V - 15V_boost` ("Not yet complete") is one IPC net, 15V_BOOST: a text note.
PDF `Gnd` (Proteus J1-34 = KiCad J1-33) = GND. J1 is drawn as in the PDF, pin 1 at the bottom (symbol
mirrored). J1 has the standard header numbering (p2k_config.IPC_PIN_IDS, finding 12): KiCad pin k + 1 /
k - 1 = Proteus pin k (odd / even), so each net is drawn on its KiCad pin, the same physical pad."""
from _common import *  # noqa: F401,F403

sh = sheet("05_reference_connector.kicad_sch")

# --- REF1: reference, 3V3 -> R74 -> +1V0_BIAS ----------------------------------------------------
ref = sh.place(sym("REF1"), "REF1", *P(38, 30), value=sh_value("REF1"))
VIN, VOUT, RGND = ref.pin(2), ref.pin(3), ref.pin(1)
Y = VIN[1]
GROW = RGND[1] + g(8)                              # ground rail under the block
xin = VIN[0] - g(4)
sh.wire(VIN, (xin, Y), (xin - g(6), Y))
power_at(sh, "3V3", (xin - g(6), Y), "left")
sh.junction(xin, Y)
_, ct, cb = vert2(sh, "C", "C8", xin, Y + g(8), sh_value("C8"), top=1)        # pin 1 = 3V3
sh.wire((xin, Y), ct)
sh.wire(cb, (xin, GROW))
xo = VOUT[0] + g(4)                                # REF1 VOUT node (#00194)
sh.wire(VOUT, (xo, Y))
sh.junction(xo, Y)
_, ct, cb = vert2(sh, "C", "C21", xo, Y + g(8), sh_value("C21"), top=1)       # pin 1 = VOUT
sh.wire((xo, Y), ct)
sh.wire(cb, (xo, GROW))
_, rl, rr = horiz2(sh, "R", "R74", xo + g(8), Y, sh_value("R74"), left=1)     # pin 1 = VOUT
sh.wire((xo, Y), rl)
xb = xo + g(16)                                    # +1V0_BIAS node
sh.wire(rr, (xb, Y))
sh.junction(xb, Y)
sh.wire((xb, Y), (xb, Y - g(6)))
power_at(sh, "+1V0_BIAS", (xb, Y - g(6)), "up")
_, rt, rb = vert2(sh, "R", "R73", xb, Y + g(8), sh_value("R73"), top=1)       # pin 1 = +1V0_BIAS
sh.wire((xb, Y), rt)
sh.wire(rb, (xb, GROW))
xc = xb + g(9)
_, ct, cb = vert2(sh, "C", "C22", xc, Y + g(8), sh_value("C22"), top=1)       # pin 1 = +1V0_BIAS
sh.wire((xb, Y), (xc, Y), ct)
sh.junction(xc, Y)
sh.wire((xc, Y), (xc, Y - g(4)))
sh.pwr_flag(xc, Y - g(4), 0)        # the power symbol's pin needs a driver: the rail comes through R74 (passive)
sh.wire(cb, (xc, GROW))
sh.wire(RGND, (RGND[0], GROW))
sh.wire((xin, GROW), (xc, GROW))
for x in (RGND[0], xo, xb):
    sh.junction(x, GROW)
sh.wire((RGND[0], GROW), (RGND[0], GROW + g(5)))
power_at(sh, "GND", (RGND[0], GROW + g(5)), "down")

# --- J1: control-card ribbon; (KiCad pin, IPC net, PDF alias or None) ------------------------------
# Standard header numbering (p2k_config.IPC_PIN_IDS, finding 12): KiCad pin = Proteus pin + 1 (odd) /
# - 1 (even); each net is on the same physical pad as in Proteus. The PDF draws the Proteus pin numbers.
J1_PINS = [
    (1, "V_A_MEAS", "ADB7"), (2, "CURRENT_Q4_MEAS", "ADB0"), (3, "UIN_MEAS", "ADB6"),
    (4, "CURRENT_Q7_MEAS", "ADB1"), (5, "UC3_MEAS", "ADB5"), (6, "CURRENT_C6_MEAS", "ADB2"),
    (7, "U_OUT_MEAS", "ADB4"), (8, "CURRENT_C3_MEAS", "ADB3"), (9, "ADASEL2_ISO", None),
    (10, "ADASEL1_ISO", None), (11, "ADASEL0_ISO", None), (12, "SCL", None), (13, "CS1_ISO", None),
    (14, "CLK1_ISO", None), (15, "PWM_TRANS1_ISO", None), (16, "PWM_TRANS2_ISO", None),
    (17, "PWM_TRANS3_ISO", None), (18, "PWM_G4_ISO", None), (19, "PWM_G2_ISO", None),
    (20, "PWM_G1_ISO", None), (21, "PWM_G3_ISO", None), (22, "DAB_PWM_PRI_HI_ISO", None),
    (23, "DAB_PWM_PRI_LO_ISO", None), (24, "ADCLK_DAB", None), (25, "PWM_TRANS4", None), (26, "SDA", None),
    (27, "DAB_PWM_HI_SEC", None), (28, "PWM_TRANS6", None), (29, "G1_LO", None), (30, "G3_LO", None),
    (31, "G1_HI", None), (32, "G3_HI", None), (33, "GND", None), (34, "GND", None), (35, "3V3", None),
    (36, "3V3", None), (37, None, None), (38, None, None), (39, "15V_BOOST", None), (40, "15V_BOOST", None),
]
GLOBAL = {"CURRENT_Q4_MEAS", "V_A_MEAS", "CURRENT_Q7_MEAS", "UIN_MEAS", "CURRENT_C6_MEAS", "UC3_MEAS",
          "CURRENT_C3_MEAS", "U_OUT_MEAS", "SCL", "SDA", "G3_LO", "G1_LO", "G3_HI", "G1_HI"}
POWER = {"GND", "3V3", "15V_BOOST"}
JX, JY = P(134, 55)
j1 = sh.place(sym("J1"), "J1", JX, JY, 0, mirror="x", value=sh_value("J1"),
             ref_at=(JX - g(4), JY - g(21.5), 0, "left"), value_at=(JX - g(4), JY + g(23.5), 0, "left"))
for pin, net, alias in J1_PINS:
    p = j1.pin(pin)
    side = "left" if pin % 2 else "right"
    if net is None:                                  # J1-37, J1-38: N/C in the IPC
        sh.no_connect(*p)
        continue
    n = 6 if (net in POWER or net in GLOBAL) else 16     # local labels clear of the global label boxes
    q = left(p, n) if side == "left" else right(p, n)
    sh.wire(p, q)
    if net in POWER:
        power_at(sh, net, q, side)
    elif net in GLOBAL:
        sh.glabel(net, *q, 180 if side == "left" else 0)
    else:
        sh.label(net, *q, 180 if side == "left" else 0)
    if alias:
        sh.text(alias, p[0] - g(3.5) if side == "left" else p[0] + g(0.7), p[1] - 0.9, size=1.0)

# --- PWR_FLAGs: the rails enter the board on J1 --------------------------------------------------
FX, FY = P(118, 86)
for i, net in enumerate(("3V3", "GND", "15V_BOOST")):
    flagged_power(sh, net, FX + g(14 * i), FY)
sh.text("PWR_FLAGs: 3V3 (J1-35/36), GND (J1-33/34) and 15V_BOOST (J1-39/40) enter on J1.", FX - g(8), FY + g(8))

# --- notes ---------------------------------------------------------------------------------------
NX, NY = P(104, 22)
sh.text("PDF: link 15V - 15V_boost, \"Not yet complete\": one net, 15V_BOOST (IPC);", NX, NY)
sh.text("the gate drivers' 15V (sheet 2) is 15V_BOOST.", NX, NY + g(2))
NX, NY = P(30, 66)
sh.text("PDF alias links (Proteus J1 pins 1-8 = ADB0-ADB7 in the PDF; Proteus names, see sheet 4; KiCad pins):", NX, NY)
for i, (a, n) in enumerate((("ADB0", "C2_current_meas  (J1-2)"), ("ADB1", "C3_current_meas  (J1-4)"),
                            ("ADB2", "input_current_meas  (J1-6)"), ("ADB3", "C1_current_meas  (J1-8)"),
                            ("ADB4", "U_out_meas  (J1-7)"), ("ADB5", "Uc3_meas  (J1-5)"),
                            ("ADB6", "Uin_meas  (J1-3)"), ("ADB7", "V_A_meas  (J1-1)"))):
    sh.text(f"{a} = {n}", NX + g(2), NY + g(2 * (i + 1)))
sh.text("Unused ribbon signals (*_ISO, PWM_TRANS4/6, DAB_*, ADCLK_DAB): label on the J1 pin only.", NX, NY + g(20))
sh.text("PDF Gnd (Proteus J1-34 = KiCad J1-33) = GND.", NX, NY + g(22))
sh.text("J1 numbering: standard header (KiCad pin = Proteus pin + 1 / - 1, odd / even), same pads (finding 12).", NX, NY + g(24))

sh.save()
print("sheet05: written")
