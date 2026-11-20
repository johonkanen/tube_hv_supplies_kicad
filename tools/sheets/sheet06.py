#!/usr/bin/env python3
"""Sheet 6 - ADC (PDF page 6): the ADC input header J2 (2x8, 1.27 mm), the input filters
R78 / C35, R79 / C36, R80 / C37, the three I2C ADCs ADC1-ADC3 (ADC121C027) with the pull-ups
R76 (SCL) / R77 (SDA) and the decoupling capacitors C27-C29.

Drawn as the PDF and the IPC have it: the pin named VIN (COM2) is on 3V3 and the pin named VA
(A1) on the filtered input (STATUS.md finding 6: reproduced, not fixed). ADR0: ADC1 on 3V3,
ADC2 on GND, ADC3 alone on the net FLOATING. J2 is drawn as in the PDF, pin 1 at the bottom
(symbol mirrored). PDF scl / sda / floating = SCL / SDA / FLOATING."""
from _common import *  # noqa: F401,F403

sh = sheet("06_adc.kicad_sch")


def X(x):
    return P(x, 0)[0]


def Yg(y):
    return P(0, y)[1]


# --- J2: ADC input header ------------------------------------------------------------------------
JX, JY = P(24, 64)
j2 = sh.place(sym("J2"), "J2", JX, JY, 0, mirror="x", value=sh_value("J2"),
             ref_at=(JX - g(4), JY - g(9.5), 0, "left"), value_at=(JX - g(4), JY + g(11.5), 0, "left"))
pin = {n: j2.pin(n) for n in range(1, 17)}
LX, RX_ = pin[1][0], pin[2][0]
# GND: odd pins 5, 9, 13, 15 on a bus left of the header, even pins 6, 10, 14, 16 on one right of it
xl, xr = LX - g(6), RX_ + g(4)
for n in (5, 9, 13, 15):
    sh.wire(pin[n], (xl, pin[n][1]))
sh.wire((xl, pin[15][1]), (xl, pin[5][1]))
sh.wire((xl, pin[15][1]), (LX - g(10), pin[15][1]))
power_at(sh, "GND", (LX - g(10), pin[15][1]), "left")
for n in (9, 13, 15):
    sh.junction(xl, pin[n][1])
for n in (6, 10, 14, 16):
    sh.wire(pin[n], (xr, pin[n][1]))
sh.wire((xr, pin[16][1]), (xr, pin[6][1]))
sh.wire((xr, pin[16][1]), (RX_ + g(8), pin[16][1]))
power_at(sh, "GND", (RX_ + g(8), pin[16][1]), "right")
for n in (10, 14, 16):
    sh.junction(xr, pin[n][1])
# 3V3: pins 1, 2
sh.wire(pin[1], (LX - g(10), pin[1][1]))
power_at(sh, "3V3", (LX - g(10), pin[1][1]), "left")
sh.wire(pin[2], (RX_ + g(8), pin[2][1]))
power_at(sh, "3V3", (RX_ + g(8), pin[2][1]), "right")
# inputs: pin pairs 11/12 -> R78, 7/8 -> R79, 3/4 -> R80 (pin 2 of each resistor on the header)
Y1, Y2, Y3 = Yg(46), pin[8][1], Yg(80)                 # rows of R78, R79, R80
xa, xb = X(44), X(49)
_, r78l, r78r = horiz2(sh, "R", "R78", X(56), Y1, sh_value("R78"), left=2, text="above")
_, r79l, r79r = horiz2(sh, "R", "R79", X(56), Y2, sh_value("R79"), left=2, text="above")
_, r80l, r80r = horiz2(sh, "R", "R80", X(56), Y3, sh_value("R80"), left=2, text="above")
sh.wire(pin[12], (xa, pin[12][1]), (xa, Y1), r78l)                       # crosses the right GND bus
sh.wire(pin[11], (LX - g(4), pin[11][1]), (LX - g(4), Y1), (xa, Y1))
sh.junction(xa, Y1)
sh.wire(pin[8], r79l)
sh.wire(pin[7], (LX - g(2), pin[7][1]), (LX - g(2), Yg(53)), (xb, Yg(53)), (xb, Y2))
sh.junction(xb, Y2)
sh.wire(pin[4], (xa, pin[4][1]), (xa, Y3), r80l)
sh.wire(pin[3], (LX - g(2), pin[3][1]), (LX - g(2), Y3), (xa, Y3))
sh.junction(xa, Y3)

# --- ADC1-ADC3 -----------------------------------------------------------------------------------
adc = {n: sh.place(sym(f"ADC{n}"), f"ADC{n}", *P(112, y), value=sh_value(f"ADC{n}"))
       for n, y in ((1, 39), (2, 66), (3, 90))}
VIN = {n: a.pin("COM2") for n, a in adc.items()}
VA = {n: a.pin("A1") for n, a in adc.items()}
AGND = {n: a.pin("A2") for n, a in adc.items()}
SCL = {n: a.pin("K1") for n, a in adc.items()}
SDA = {n: a.pin("COM1") for n, a in adc.items()}
ADR = {n: a.pin("K2") for n, a in adc.items()}

# VIN pins on 3V3 (as drawn: finding 6)
x33 = X(95)
sh.wire(VIN[1], (X(73), VIN[1][1]))
power_at(sh, "3V3", (X(73), VIN[1][1]), "left")
sh.wire((x33, VIN[1][1]), (x33, VIN[3][1]), VIN[3])
sh.wire((x33, VIN[2][1]), VIN[2])
sh.junction(x33, VIN[1][1])
sh.junction(x33, VIN[2][1])
# GND pins
xg = X(87)
sh.wire(AGND[1], (xg, AGND[1][1]), (xg, Yg(101)))
power_at(sh, "GND", (xg, Yg(101)), "down")
for n in (2, 3):
    sh.wire(AGND[n], (xg, AGND[n][1]))
    sh.junction(xg, AGND[n][1])
# VA pins on the filtered inputs (as drawn: finding 6); C35-C37 pin 2 on the input, pin 1 on GND
GROW = Yg(123)
xc1, xc2, xc3 = X(65), X(72), X(85)
sh.wire(r78r, (X(61), Y1), (X(61), VA[1][1]), VA[1])                     # crosses the 3V3 bus
_, ct, cb = vert2(sh, "C", "C35", xc1, Yg(54), sh_value("C35"), top=2)
sh.wire((xc1, VA[1][1]), ct)
sh.junction(xc1, VA[1][1])
sh.wire(cb, (xc1, GROW))
sh.wire(r79r, VA[2])                                                     # crosses C35's GND wire, the GND and 3V3 buses
_, ct, cb = vert2(sh, "C", "C36", xc2, Yg(73), sh_value("C36"), top=2)
sh.wire((xc2, VA[2][1]), ct)
sh.junction(xc2, VA[2][1])
sh.wire(cb, (xc2, GROW))
sh.wire(r80r, (xc3, Y3), (xc3, VA[3][1]), VA[3])                         # crosses the C35 / C36 GND wires, the GND bus
_, ct, cb = vert2(sh, "C", "C37", xc3, Yg(114), sh_value("C37"), top=2)
sh.wire((xc3, VA[3][1]), ct)
sh.junction(xc3, VA[3][1])
sh.wire(cb, (xc3, GROW))
sh.wire((xc1, GROW), (xc3, GROW))
sh.junction(xc2, GROW)
sh.wire((xc2, GROW), (xc2, Yg(129)))
power_at(sh, "GND", (xc2, Yg(129)), "down")

# SCL / SDA buses, pull-ups, address pins
xs, xd, xe = X(132), X(137), X(175)
sh.wire(SCL[1], (xs, SCL[1][1]), (xs, SCL[3][1]), SCL[3])
sh.wire(SCL[2], (xe, SCL[2][1]))
sh.junction(xs, SCL[2][1])
sh.glabel("SCL", xe, SCL[2][1], 0)
sh.wire(SDA[1], (xd, SDA[1][1]), (xd, SDA[3][1]), SDA[3])
sh.wire(SDA[2], (xe, SDA[2][1]))
sh.junction(xd, SDA[2][1])
sh.glabel("SDA", xe, SDA[2][1], 0)
sh.wire(ADR[1], (xe, ADR[1][1]))                                         # ADC1 ADR0 = 3V3
power_at(sh, "3V3", (xe, ADR[1][1]), "right")
for ref, x, bus in (("R76", X(151), SCL), ("R77", X(161), SDA)):         # pin 1 = 3V3
    _, rt, rb = vert2(sh, "R", ref, x, Yg(51), sh_value(ref), top=1)
    sh.wire(rt, (x, ADR[1][1]))
    sh.junction(x, ADR[1][1])
    sh.wire(rb, (x, bus[2][1]))
    sh.junction(x, bus[2][1])
sh.wire(ADR[2], (X(146), ADR[2][1]))                                     # ADC2 ADR0 = GND
power_at(sh, "GND", (X(146), ADR[2][1]), "right")
label_right(sh, "FLOATING", ADR[3], 20)                                  # ADC3 ADR0: single-pin net

# --- decoupling C27-C29 (pin 2 = 3V3, pin 1 = GND) -----------------------------------------------
YT, YB = Yg(12), Yg(25)
for ref, x in (("C27", X(134)), ("C28", X(146)), ("C29", X(160))):
    _, ct, cb = vert2(sh, "C", ref, x, Yg(18), sh_value(ref), top=2)
    sh.wire(ct, (x, YT))
    sh.wire(cb, (x, YB))
    if ref != "C27":
        sh.junction(x, YT)
        sh.junction(x, YB)
sh.wire((X(134), YT), (xe, YT))
power_at(sh, "3V3", (xe, YT), "right")
sh.wire((X(134), YB), (xe, YB))
power_at(sh, "GND", (xe, YB), "right")

# --- notes ---------------------------------------------------------------------------------------
sh.text("As drawn in the PDF (and built: IPC): VIN (COM2) on 3V3, VA (A1) on the filtered input.", X(96), Yg(104))
sh.text("ADC121C027: VA is the supply / reference, VIN the analog input (STATUS.md finding 6).", X(96), Yg(106))
sh.text("ADR0: ADC1 = 3V3, ADC2 = GND, ADC3 = open (net FLOATING, PDF 'floating').", X(96), Yg(108))
sh.text("PWR_FLAGs of 3V3 and GND: sheet 5 (J1).", X(96), Yg(110))

sh.save()
print("sheet06: written")
