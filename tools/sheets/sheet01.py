#!/usr/bin/env python3
"""Sheet 1 - Power stage (PDF page 1): the input filter (B+ -> L7 -> UIN with C1 / C11 and
C26 / C2 / C9 / C10) and two IGBT half-bridges on UIN. Q3 / Q4 -> OUT1 -> off-board L1 (3 mH,
terminals L5 - L12) -> UC3 (C3 over the shunt R75) -> L2 -> V_A (C4, terminal V_ANODE).
Q8 / Q7 -> OUT2 -> off-board L3 (3 mH, terminals L11 - L6) -> U_OUT (C5) -> L4 -> UC6 (C6 over
the shunt R30) -> R26 || R27 -> PREOUT (C7, terminal VPRE). Emitter shunts R72 (Q4) and R29 (Q7).

Net names as the IPC has them (PDF b+, Uin, Uc3, V_a, U_out, uc6, preout, out1, out2,
current_L3, C1_current, C3_current). PDF BRIDGE+ is a second terminal on UIN (text note). The
PDF terminal Input_current hangs on the GND rail: GND (text note, STATUS.md finding 7).
L1 / L3 are off-board parts (symbol L_OFFBOARD, not in the netlist comparison): OUT1 / UC3 and
OUT2 / U_OUT stay separate nets, as in the IPC."""
from _common import *  # noqa: F401,F403

sh = sheet("01_power_stage.kicad_sch")

YT, YM, YB = 36, 58, 89            # UIN rail, inductor row, GND rail (PDF rows, 10 px units)


def vcap(ref, x, y, **kw):
    """Vertical capacitor, pin 1 (+ of a polarized one) at the top."""
    _, t, b = vert2(sh, sym(ref), ref, *P(x, y), sh_value(ref), top=1, **kw)
    return t, b


def hpart(ref, x, y, left=1, **kw):
    _, l, r = horiz2(sh, sym(ref), ref, *P(x, y), sh_value(ref), left=left, **kw)
    return l, r


def node(x, y):
    sh.junction(*P(x, y))


def gl_down(name, x, y):
    sh.glabel(name, *P(x, y), 270)


def gl_up(name, x, y):
    sh.glabel(name, *P(x, y), 90)


# --- rails: one wire each, so the columns that only cross them stay unconnected -------------------
l7l, l7r = hpart("L7", 29, YT)                       # L7: 1 = B+, 2 = UIN
sh.wire(P(11, YT), l7l)
sh.label("B+", *P(13, YT), 0)
sh.wire(l7r, P(145, YT))
sh.wire(P(11, YB), P(193, YB))

# --- input: B+ / B- terminals, C1, C11 (B+), C26, C2, C10, C9 (UIN) -------------------------------
term(sh, "B_P", *P(11, 24), "up")
sh.wire(P(11, 24), P(11, YT))
term(sh, "B_N", *P(11, 97), "down")
sh.wire(P(11, 97), P(11, YB))
for ref, x, y, kw in (("C1", 11, 58, {}), ("C11", 21, 58, {}), ("C26", 38, 58, {}), ("C2", 49, 58, {}),
                      ("C10", 55, 70, {"text": "left"}), ("C9", 60, 58, {})):
    t, b = vcap(ref, x, y, **kw)
    sh.wire(t, P(x, YT))
    sh.wire(b, P(x, YB))
    for yy in (YT, YB):
        if (x, yy) != (11, YB):
            node(x, yy)
sh.wire(P(63, YT), P(63, 7))                         # PDF Uin (and BRIDGE+)
node(63, YT)
gl_up("UIN", 63, 7)


# --- half-bridges ---------------------------------------------------------------------------------
def half_bridge(q_hi, q_lo, x, g_hi, g_lo, xg_hi, xg_lo, yg_hi, yg_lo, shunt, cur, x_cur, y_cur):
    """High IGBT (collector on the UIN rail) over low IGBT (emitter on `shunt` to GND), collector
    column at x; gate global labels g_hi / g_lo on columns xg_hi / xg_lo going down across the GND
    rail to rows yg_hi / yg_lo; global label `cur` from the shunt's top on column x_cur."""
    hi = sh.place(sym(q_hi), q_hi, *P(x - 2, 47), value=sh_value(q_hi))
    lo = sh.place(sym(q_lo), q_lo, *P(x - 2, 67), value=sh_value(q_lo))
    sh.wire(hi.pin(2), P(x, YT))
    sh.wire(hi.pin(3), lo.pin(2))                    # switch node, through (x, YM)
    sh.wire(hi.pin(1), P(xg_hi, 47), P(xg_hi, yg_hi))
    gl_down(g_hi, xg_hi, yg_hi)
    sh.wire(lo.pin(1), P(xg_lo, 67), P(xg_lo, yg_lo))
    gl_down(g_lo, xg_lo, yg_lo)
    _, rt, rb = vert2(sh, "R", shunt, *P(x, 82), sh_value(shunt), top=2)
    sh.wire(lo.pin(3), rt)
    sh.wire(rb, P(x, YB))
    node(x, YB)
    sh.wire(P(x, 76), P(x_cur, 76), P(x_cur, y_cur))
    node(x, 76)
    gl_down(cur, x_cur, y_cur)


half_bridge("Q3", "Q4", 83, "PWM1_HI", "PWM1_LO", 69, 72, 104, 112, "R72", "CURRENT_L1", 76, 109)
node(83, YT)
half_bridge("Q8", "Q7", 145, "PWM3_HI", "PWM3_LO", 130, 135, 100, 107, "R29", "CURRENT_L3", 154, 110)

# --- OUT1 -> L1 (off-board, L5 - L12) -> UC3 -> L2 -> V_A -----------------------------------------
term(sh, "L5", *P(70, 19), "up")
sh.wire(P(70, 19), P(70, 32), P(76, 32))
sh.glabel("OUT1", *P(76, 32), 0)
sh.wire(P(73, 32), P(73, YM), P(83, YM))             # crosses the UIN rail and the Q3 gate wire
node(73, 32)
node(83, YM)
l, r = hpart("L1", 91, YM)
sh.wire(P(83, YM), l)
sh.wire(r, P(100, YM))
node(100, YM)
sh.wire(P(100, YM), P(100, 7))                       # PDF Uc3; crosses the UIN rail
gl_up("UC3", 100, 7)
term(sh, "L12", *P(105, 19), "up")
sh.wire(P(105, 19), P(105, 43), P(100, 43))
node(100, 43)
t, b = vcap("C3", 100, 66)                           # C3: + = UC3, - = C1_CURRENT (shunt R75)
sh.wire(P(100, YM), t)
_, rt, rb = vert2(sh, "R", "R75", *P(100, 81), sh_value("R75"), top=2)
sh.wire(b, rt)
sh.wire(rb, P(100, YB), P(100, 96))
node(100, YB)
power_at(sh, "GND", P(100, 96), "down")              # PDF: terminal gnd below R75
sh.wire(P(100, 72), P(108, 72), P(108, 117))
node(100, 72)
gl_down("C1_CURRENT", 108, 117)
l, r = hpart("L2", 110, YM)                          # L2: 1 = UC3, 2 = V_A
sh.wire(P(100, YM), l)
sh.wire(r, P(128, YM), P(128, 7))                    # PDF V_a; crosses the UIN rail
gl_up("V_A", 128, 7)
term(sh, "V_ANODE", *P(119, 27), "up")
sh.wire(P(119, 27), P(119, YM))
node(119, YM)
t, b = vcap("C4", 119, 66)
sh.wire(P(119, YM), t)
sh.wire(b, P(119, YB))
node(119, YB)

# --- OUT2 -> L3 (off-board, L11 - L6) -> U_OUT -> L4 -> UC6 -> R26 || R27 -> PREOUT ---------------
term(sh, "L11", *P(133, 21), "up")
sh.wire(P(133, 21), P(133, YM), P(145, YM))          # crosses the UIN rail and the Q8 gate wire
sh.wire(P(133, 30), P(136, 30))
node(133, 30)
sh.glabel("OUT2", *P(136, 30), 0)
node(145, YM)
l, r = hpart("L3", 153, YM)
sh.wire(P(145, YM), l)
sh.wire(r, P(162, YM))
node(162, YM)
sh.wire(P(162, YM), P(162, 7))                       # PDF U_out
gl_up("U_OUT", 162, 7)
term(sh, "L6", *P(171, 21), "up")
sh.wire(P(171, 21), P(171, 44), P(162, 44))
node(162, 44)
t, b = vcap("C5", 162, 66)
sh.wire(P(162, YM), t)
sh.wire(b, P(162, YB))
node(162, YB)
l, r = hpart("L4", 170, YM)                          # L4: 1 = U_OUT, 2 = UC6
sh.wire(P(162, YM), l)
sh.wire(r, P(179, YM))
node(179, YM)
l26, r26 = hpart("R26", 186, YM, text="below")       # R26 || R27: 1 = UC6, 2 = PREOUT
l27, r27 = hpart("R27", 186, 51, text="above")
sh.wire(P(179, YM), l26)
sh.wire(P(179, YM), P(179, 51), l27)
sh.label("UC6", *P(179, 51), 0)
t, b = vcap("C6", 179, 66)                           # C6: + = UC6, - = C3_CURRENT (shunt R30)
sh.wire(P(179, YM), t)
_, rt, rb = vert2(sh, "R", "R30", *P(179, 81), sh_value("R30"), top=2)
sh.wire(b, rt)
sh.wire(rb, P(179, YB))
node(179, YB)
sh.wire(P(179, 72), P(168, 72), P(168, 117))
node(179, 72)
gl_down("C3_CURRENT", 168, 117)
term(sh, "GND_PRE", *P(179, 99), "down")
sh.wire(P(179, 99), P(179, YB))
term(sh, "VPRE", *P(193, 25), "up")
sh.wire(P(193, 25), P(193, YM))
sh.label("PREOUT", *P(193, 40), 0)
sh.wire(r27, P(193, 51))
node(193, 51)
sh.wire(r26, P(193, YM))
node(193, YM)
t, b = vcap("C7", 193, 66)
sh.wire(P(193, YM), t)
sh.wire(b, P(193, YB))
term(sh, "GND_PWR", *P(193, 99), "down")
sh.wire(P(193, 99), P(193, YB))

# --- notes ----------------------------------------------------------------------------------------
NX, NY = P(4, 128)
sh.text("Net names = IPC (PDF: b+, Uin, Uc3, V_a, U_out, uc6, preout, out1, out2). PDF BRIDGE+ (terminal above Q3) = UIN.", NX, NY)
sh.text("L1 / L3 (3 mH) are off-board, wired to the terminals L5 - L12 and L11 - L6; they are not in the netlist (OUT1 / UC3 and OUT2 / U_OUT are separate nets).", NX, NY + g(2))
sh.text("PDF terminal Input_current (below C2) is on the GND rail = GND: there is no input-current shunt (STATUS.md finding 7).", NX, NY + g(4))
sh.text("OUT1, OUT2, PWMx: sheet 2. UIN, UC3, V_A, U_OUT: sheet 3. C1_CURRENT, C3_CURRENT, CURRENT_L1, CURRENT_L3: sheet 4. PWR_FLAGs of GND (sheet 5), OUT1 / OUT2 (sheet 2).", NX, NY + g(6))

sh.save()
print("sheet01: written")
