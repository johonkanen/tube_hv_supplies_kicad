"""Helpers for the per-sheet transcription scripts (tools/sheets/sheetNN.py).

The generic helpers come from p2k.sheetkit (grid g(), sheet(), left/right/up/down,
glabel_*/label_*, power_at, bus_group, flagged_power, vert2, horiz2, terminal); board helpers
below. Each sheet script starts with
    from _common import *  # noqa: F401,F403
"""
import csv
import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(TOOLS, "p2k"))  # proteus2kicad
from p2k.sch_builder import Sheet  # noqa: E402,F401
from p2k.sheetkit import *  # noqa: E402,F401,F403
from p2k.sheetkit import _two_pin_rot  # noqa: E402

_PART_MAP = None


def part(ref):
    """Row of lib/part_map.csv for a KiCad refdes (keys refdes, sheet, lib_id, value, ...)."""
    global _PART_MAP
    if _PART_MAP is None:
        with open(os.path.join(os.path.dirname(TOOLS), "lib", "part_map.csv"), newline="", encoding="utf-8") as f:
            _PART_MAP = {r["refdes"]: r for r in csv.DictReader(l for l in f if not l.startswith("#"))}
    return _PART_MAP[ref]


def sh_value(ref):
    """Value of a refdes from lib/part_map.csv."""
    return part(ref)["value"]


def sym(ref):
    """Symbol name (lib_id without the library nickname) of a refdes from lib/part_map.csv."""
    return part(ref)["lib_id"].partition(":")[2]


def term(sh, ref, x, y, direction="up"):
    """Proteus TERMINAL part as sheetkit.terminal does it (connection point (x, y), circle
    pointing in `direction`, texts horizontal), but with the symbol and value of the part map
    (PIN, value TERMINAL): sheetkit.terminal always writes value "PIN" (p2k candidate). The
    texts of 'left' / 'right' terminals are justified away from the circle (sheetkit's
    justification draws them over the circle in KiCad 10.0.7, see tube_power_amp)."""
    rot = {"up": 0, "left": 90, "down": 180, "right": 270}[direction]
    kw = {}
    if direction == "right":     # KiCad mirrors justification for rot 270
        kw = dict(ref_at=(x + 5.08, y - 1.27, 90, "left"), value_at=(x + 5.08, y + 1.27, 90, "left"))
    elif direction == "left":
        kw = dict(ref_at=(x - 5.08, y - 1.27, 270, "right"), value_at=(x - 5.08, y + 1.27, 270, "right"))
    return sh.place(sym(ref), ref, x, y, rot, value=sh_value(ref), **kw)


# --- PDF coordinates ---------------------------------------------------------------------------------
# The Proteus PDF pages rendered at 200 dpi (build/tmp/pdf/hi-N.png, 2020 x 1420 px) have
# 0.127 mm pixels, so 10 px = one 1.27 mm grid unit. P(px/10, py/10) puts a point of the render on
# the A3 KiCad sheet (same scale, shifted by OX/OY grid units), which keeps the layout close to the
# PDF (the render is 257 x 180 mm; A3 is 420 x 297 mm).
OX, OY = 40, 30


def P(x, y):
    """Sheet point (mm, on the 1.27 mm grid) of PDF render position (x, y) in units of 10 px."""
    return (g(x + OX), g(y + OY))


# --- mirrored symbols --------------------------------------------------------------------------------
def place_mirrored(sh, name, ref, x, y, axis="x", **kw):
    """sh.place() at rotation 0 with the symbol mirrored: axis 'x' = about the X axis (top and
    bottom swapped), 'y' = about the Y axis (left and right swapped). p2k.sch_builder.Sheet.place has
    no mirror option (p2k candidate), so the node it wrote gets a (mirror ...) entry here and the
    returned pin points are mirrored about the symbol origin. Pass ref_at / value_at for the texts
    (KiCad keeps field positions absolute)."""
    from p2k.sexpr import Sym, find
    p = sh.place(name, ref, x, y, 0, **kw)
    unit = kw.get("unit", 1)
    for node in sh.tree:
        if (isinstance(node, list) and node and str(node[0]) == "symbol" and find(node, "unit")[1] == unit
                and any(c[1:3] == ["Reference", ref] for c in node if isinstance(c, list) and str(c[0]) == "property")):
            node.insert(next(i for i, c in enumerate(node) if isinstance(c, list) and str(c[0]) == "at") + 1,
                        [Sym("mirror"), Sym(axis)])
            break
    else:
        raise KeyError(ref)
    for num, (px, py) in list(p.pins.items()):
        p.pins[num] = (px, round(2 * y - py, 4)) if axis == "x" else (round(2 * x - px, 4), py)
    return p


# --- SI8271 gate-driver cell (sheet 2, x4) -----------------------------------------------------------
def si8271_cell(sh, ref, UX, UY, vin, cdec, r_on, r_off, gate, cvdd2, rail="15V_BOOST", boot=None, src=None):
    """SI8271 isolated gate driver with its parts, IC at (UX, UY).

    Input side: pin 1 Vin = global label `vin`; VDD1 (2) and EN (4) on 3V3, GND1 (3) on GND;
    cdec = decoupling capacitor 3V3 - GND (pin 2 on 3V3).
    Output side: r_on = 15R on OUT+ (7), r_off = 8R on OUT- (6), pin 1 on the driver, pin 2 of both
    on the global label `gate`; cvdd2 = capacitor VDD2 (8) - GND2 (5).
    Low side (boot None): VDD2 on `rail` (cvdd2 pin 1), GND2 on GND.
    High side (boot = (diode, resistor), src = global label of the switch node): `rail` -> diode
    A-C -> resistor 1-2 -> VDD2 (cvdd2 pin 2), GND2 = `src` (cvdd2 pin 1). VDD2 and GND2 are
    power inputs fed through passives only, so each of the two nets gets a PWR_FLAG."""
    u = sh.place(sym(ref), ref, UX, UY, value=sh_value(ref))
    VDD1, VIN, EN, GND1, VDD2, OUTP, OUTN, GND2 = (u.pin(n) for n in (2, 1, 4, 3, 8, 7, 6, 5))

    # --- input side ---
    glabel_left(sh, vin, VIN, 22)
    xs = UX - g(12)
    top = (xs, UY - g(7))
    sh.wire(VDD1, (xs, VDD1[1]), top, (xs, UY - g(9)))
    power_at(sh, "3V3", (xs, UY - g(9)), "up")
    fa = {0: 0, 90: 270, 180: 0, 270: 90}[_two_pin_rot("C", 1, "left")]     # texts clear of the plates
    _, cl, cr = horiz2(sh, "C", cdec, UX - g(17), top[1], sh_value(cdec), left=1,
                       ref_at=(UX - g(17), top[1] - 3.81, fa, None), value_at=(UX - g(17), top[1] + 3.81, fa, None))
    sh.wire(cr, top)
    sh.junction(*top)
    sh.wire(cl, (UX - g(22), top[1]), (UX - g(22), UY - g(6)))
    power_at(sh, "GND", (UX - g(22), UY - g(6)), "down")
    q = left(EN, 3)                       # EN tied to VDD1: own power symbol (the bus would cross Vin)
    sh.wire(EN, q)
    power_at(sh, "3V3", q, "left")
    sh.wire(GND1, (xs, GND1[1]), (xs, UY + g(5)))
    power_at(sh, "GND", (xs, UY + g(5)), "down")

    # --- output side ---
    xv, xc = UX + g(10), UX + g(13)       # VDD2 riser, capacitor column
    YT, YB = UY - g(15), UY + g(6)        # VDD2 row, GND2 row
    sh.wire(VDD2, (xv, VDD2[1]), (xv, YT), (xc, YT))
    _, ct, cb = vert2(sh, "C", cvdd2, xc, UY - g(10), sh_value(cvdd2), top=2 if boot else 1)
    sh.wire((xc, YT), ct)
    sh.wire(cb, (xc, YB))                 # crosses the OUT+ / OUT- wires, as in the PDF
    sh.wire(GND2, (xc, GND2[1]))
    sh.junction(xc, GND2[1])
    xr, xj = UX + g(19), UX + g(24)
    _, rl, rr = horiz2(sh, "R", r_on, xr, OUTP[1], sh_value(r_on), left=1, text="above")
    sh.wire(OUTP, rl)
    sh.wire(rr, (xj, OUTP[1]), (xj, OUTN[1]))
    _, rl, rr = horiz2(sh, "R", r_off, xr, OUTN[1], sh_value(r_off), left=1, text="below")
    sh.wire(OUTN, rl)
    sh.wire(rr, (xj, OUTN[1]), (UX + g(30), OUTN[1]))
    sh.junction(xj, OUTN[1])
    sh.glabel(gate, UX + g(30), OUTN[1], 0)
    if boot is None:
        sh.wire((xv, YT), (xv, YT - g(2)))
        sh.junction(xv, YT)
        power_at(sh, rail, (xv, YT - g(2)), "up")
        power_at(sh, "GND", (xc, YB), "down")
        return u
    dref, rref = boot
    _, rl, rr = horiz2(sh, "R", rref, UX + g(3), YT, sh_value(rref), left=1)
    sh.wire(rr, (xv, YT))
    sh.junction(xv, YT)
    _, da, dc = horiz2(sh, "D", dref, UX - g(6), YT, sh_value(dref), left="A")
    sh.wire(dc, rl)
    sh.wire(da, (UX - g(16), YT), (UX - g(16), YT - g(2)))
    power_at(sh, rail, (UX - g(16), YT - g(2)), "up")
    sh.wire((xv, YT), (xv, YT - g(3)))
    sh.pwr_flag(xv, YT - g(3), 0)         # bootstrap node: VDD2 fed through the diode and resistor
    sh.wire((xc, YB), (UX + g(30), YB))
    sh.glabel(src, UX + g(30), YB, 0)
    xf = UX + g(22)
    sh.wire((xf, YB), (xf, YB + g(2)))
    sh.junction(xf, YB)
    sh.pwr_flag(xf, YB + g(2), 180)       # switch node: GND2 of the high-side driver
    return u


# --- shunt amplifier cell (sheet 4, x4) --------------------------------------------------------------
def shunt_amp_cell(sh, ref, unit, UX, UY, pins, r_in, r_bias, c_bias, r_gnd, r_fb, c_fb, r_out, c_out,
                   inp, out, bias="+2V5_BIAS"):
    """One op-amp unit of the current measurements, as on PDF page 4, op-amp at (UX, UY);
    pins = (+, -, output) pin numbers of the unit.

    + node: r_in (pin 1; pin 2 = global label `inp`, the shunt signal), r_bias (pin 1) and c_bias
    (pin 2) to `bias`. - node: r_gnd (pin 1; pin 2 GND), r_fb (pin 2) and c_fb (pin 2) to the
    output. Output: r_out (pin 2) -> global label `out` with c_out (pin 1) to GND."""
    u = sh.place(sym(ref), ref, UX, UY, unit=unit, value=sh_value(ref))
    INP, INN, OUT = (u.pin(n) for n in pins)
    xn = UX - g(10)                              # input node column (+ goes up, - goes down)
    # + input
    _, rl, rr = horiz2(sh, "R", r_in, UX - g(17), INP[1], sh_value(r_in), left=2)
    sh.wire(rr, INP)
    glabel_left(sh, inp, rl, 3)
    YA, YC = UY - g(11), UY - g(18)              # r_bias row, c_bias row
    xb = UX + g(9)
    sh.wire((xn, INP[1]), (xn, YC))
    sh.junction(xn, INP[1])
    _, rl, rr = horiz2(sh, "R", r_bias, UX, YA, sh_value(r_bias), left=1)
    sh.wire((xn, YA), rl)
    sh.junction(xn, YA)
    sh.wire(rr, (xb, YA), (UX + g(15), YA))
    sh.junction(xb, YA)
    power_at(sh, bias, (UX + g(15), YA), "right")
    _, cl, cr = _hcap(sh, c_bias, UX, YC)
    sh.wire((xn, YC), cl)
    sh.wire(cr, (xb, YC), (xb, YA))
    # - input and feedback
    YF, YG = UY + g(11), UY + g(18)              # r_fb row, c_fb row
    xo = UX + g(10)
    sh.wire(INN, (xn, INN[1]), (xn, YG))
    _, rl, rr = horiz2(sh, "R", r_gnd, UX - g(17), YF, sh_value(r_gnd), left=2)
    sh.wire(rr, (xn, YF))
    sh.junction(xn, YF)
    sh.wire(rl, left(rl, 3))
    power_at(sh, "GND", left(rl, 3), "left")
    _, rl, rr = horiz2(sh, "R", r_fb, UX, YF, sh_value(r_fb), left=2)
    sh.wire((xn, YF), rl)
    sh.wire(rr, (xo, YF))
    sh.junction(xo, YF)
    _, cl, cr = _hcap(sh, c_fb, UX, YG)
    sh.wire((xn, YG), cl)
    sh.wire(cr, (xo, YG), (xo, OUT[1]))
    sh.junction(xo, OUT[1])
    # output filter
    _, rl, rr = horiz2(sh, "R", r_out, UX + g(17), OUT[1], sh_value(r_out), left=2)
    sh.wire(OUT, rl)
    xq = UX + g(26)
    sh.wire(rr, (xq, OUT[1]), (UX + g(29), OUT[1]))
    sh.junction(xq, OUT[1])
    sh.glabel(out, UX + g(29), OUT[1], 0)
    _, ct, cb = vert2(sh, "C", c_out, xq, OUT[1] + g(7), sh_value(c_out), top=1)
    sh.wire((xq, OUT[1]), ct)
    sh.wire(cb, down(cb, 2))
    power_at(sh, "GND", down(cb, 2), "down")
    return u


def _hcap(sh, ref, x, y):
    """Horizontal capacitor with pin 2 on the left, reference above and value below the plates."""
    fa = {0: 0, 90: 270, 180: 0, 270: 90}[_two_pin_rot("C", 2, "left")]
    return horiz2(sh, "C", ref, x, y, sh_value(ref), left=2,
                  ref_at=(x, y - 3.81, fa, None), value_at=(x, y + 3.81, fa, None))
