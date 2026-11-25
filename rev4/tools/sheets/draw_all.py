#!/usr/bin/env python3
"""Draw the five HV supplies rev 4 sheets (first draft from rev4/PLAN.md), assign the footprints
(lib/footprint_map.csv, read by p2k's sheet builder), write the BOM (bom/bom.csv) and the intended
pin -> net table (reports/intended_nets.csv, checked against KiCad's netlist by tools/check_netlist.py).

Netlist-first drawing as in rev3 / tube_preamp_kicad rev_b: every part on a grid, a wire stub and a
label on every pin (local label if the net stays on one sheet, global label if it crosses sheets, a
power symbol for GND / +3V3 / +12V). The drawing engine (Drawer) is rev3's, unchanged.

Grounds (docs/grounding.md, as rev3): PGND switching ground (B_N, input caps, shunts, low-side drivers);
GND_STAR power star (output films, damping legs, bleeders, feed returns, fault network); GND control
ground (J1, op amps, ADCs). NT101 joins PGND and GND_STAR (star point), NT501 joins GND and PGND.
Run from anywhere: python3 rev4/tools/sheets/draw_all.py
"""
import csv
import math
import os
import sys

RB = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("P2K_BOARD", RB)
sys.path.insert(0, os.path.join(RB, "..", "tools", "p2k"))
from p2k.sch_builder import Sheet, lib  # noqa: E402
from p2k.sexpr import Sym, find, find_all  # noqa: E402

POWER = {"GND", "+3V3", "+12V"}
GRID = 2.54
MULTI = {"OPA2356xxD"}
KICAD_FP = os.environ.get("KICAD_FOOTPRINTS", "/mnt/c/Program Files/KiCad/10.0/share/kicad/footprints")
LOCAL_LIB = "tube_hv_supplies_rev4"

FP_R = "Resistor_SMD:R_0603_1608Metric"
FP_R1206 = "Resistor_SMD:R_1206_3216Metric"
FP_R2512 = "Resistor_SMD:R_2512_6332Metric"
FP_SHUNT = "Resistor_SMD:R_1225_3264Metric"          # wide-terminal (long-side) shunt: low inductance
FP_AX1WV = "Resistor_THT:R_Axial_DIN0414_L11.9mm_D4.5mm_P7.62mm_Vertical"
FP_AX2W = "Resistor_THT:R_Axial_DIN0617_L17.0mm_D6.0mm_P20.32mm_Horizontal"
FP_LINK = "Resistor_SMD:R_2512_6332Metric"
FP_C = "Capacitor_SMD:C_0603_1608Metric"
FP_C0805 = "Capacitor_SMD:C_0805_2012Metric"
FP_C1206 = "Capacitor_SMD:C_1206_3216Metric"
FP_HVC = "Capacitor_SMD:C_1812_4532Metric"
FP_EL47 = "Capacitor_THT:CP_Radial_D16.0mm_P7.50mm"
FP_EL22 = "Capacitor_THT:CP_Radial_D12.5mm_P5.00mm"
FP_FILM1U = "Capacitor_THT:C_Rect_L26.5mm_W10.5mm_P22.50mm_MKS4"
FP_FILM4U7 = "Capacitor_THT:C_Rect_L31.5mm_W13.0mm_P27.50mm_MKS4"   # MKP1848C 4.7 uF 500 V class (size to confirm)
FP_FILM10U = "Capacitor_THT:C_Rect_L31.5mm_W20.0mm_P27.50mm_MKS4"   # MKP1848C 10 uF 500 V: 32 x 18 x 28 mm
FP_Y2 = "Capacitor_THT:C_Rect_L26.5mm_W8.5mm_P22.50mm_MKS4"
FP_TO220 = "Package_TO_SOT_THT:TO-220-3_Vertical"
FP_TOROID = f"{LOCAL_LIB}:L_Toroid_32mm_Standing_P16.4mm"
FP_L100U = "Inductor_THT:L_Radial_D12.0mm_P6.00mm_Murata_1900R"      # placeholder until the 100 uH part is chosen
FP_LIN = "Inductor_THT:L_Radial_D12.0mm_P5.00mm_Fastron_11P"
FP_TAB1 = f"{LOCAL_LIB}:Blade_Tab_4.8mm_1x"
FP_TAB2 = f"{LOCAL_LIB}:Blade_Tab_4.8mm_2x_P12mm"
DEFAULT_FP = {
    "R": FP_R, "C": FP_C, "C_Polarized": FP_EL47, "D": "Diode_SMD:D_SOD-123", "D_TVS": "Diode_SMD:D_SMA",
    "LED": "LED_SMD:LED_0805_2012Metric", "NetTie_2": "NetTie:NetTie-2_SMD_Pad0.5mm",
    "Q_NIGBT_GCE": FP_TO220, "Thermistor_NTC": "Resistor_SMD:R_0603_1608Metric",
    "74LVC1G17": "Package_TO_SOT_SMD:SOT-23-5", "OPA2356xxD": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    "ADS7056": "Package_DFN_QFN:Texas_UQFN-8_1.5x1.5mm_P0.5mm", "REF3030": "Package_TO_SOT_SMD:SOT-23",
    "SI8271": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    "MountingHole_Pad": "MountingHole:MountingHole_3.2mm_M3_DIN965_Pad", "MountingHole": "MountingHole:MountingHole_3.2mm_M3",
    "Conn_02x20_Odd_Even": "Connector_PinHeader_1.27mm:PinHeader_2x20_P1.27mm_Vertical",
    "Conn_01x02": "Connector_Molex:Molex_KK-254_AE-6410-02A_1x02_P2.54mm_Vertical",
}
MPN = {"74LVC1G17": "SN74LVC1G17DBVR", "TLP293": "TLP293(GB-TPL,E)", "GBU8J": "GBU8J", "Q_NIGBT_GCE": "IKP08N65F5XKSA1",
       "OPA2356xxD": "OPA2836IDR", "ADS7056": "ADS7056IRUGR", "REF3030": "REF3030AIDBZR",
       "SI8271": "SI8271DB-IS", "LM2731XMF": "LM2731XMF/NOPB"}


def g(v):
    return round(round(v / 1.27) * 1.27, 2)


def at(c, r):
    return g(30.48 + c * 20.32), g(35.56 + r * 17.78)


def unit_of(sym, pins):
    """KiCad unit that holds the given pin numbers (multi-unit symbols)."""
    for sub in find_all(lib()[sym], "symbol"):
        u = int(sub[1].rsplit("_", 2)[-2])
        nums = {str(find(p, "number")[1]) for p in find_all(sub, "pin")}
        if nums and {str(p) for p in pins} <= nums:
            return u
    return 1


def lib_fp(sym):
    p = next((x for x in find_all(lib()[sym], "property") if x[1] == "Footprint"), None)
    return p[2] if p else ""


class Drawer:
    def __init__(self, fname, mode, globals_=frozenset()):
        self.fname, self.mode, self.globals = fname, mode, globals_
        self.nets = set()
        self.sheet_no = int(fname[:2])
        self.count = {}
        self.refmap = {}
        self.parts = 0
        self.bom = []
        self.pins = []
        self.sh = Sheet(os.path.join(RB, "kicad", fname)).clear() if mode == "draw" else None
        if self.sh is not None:
            self.sh.pwr = self.sheet_no * 100

    def auto_ref(self, ref, sym):
        """Prefix + sheet x 100 + running number; refs starting with '=' are kept as given
        (J1 is the DEFINED 40-pin ref), '#' refs are kept; a multi-unit part keeps its first ref."""
        if ref.startswith("="):
            return ref[1:]
        if ref.startswith("#"):
            return ref
        if sym in MULTI and ref in self.refmap:
            return self.refmap[ref]
        pre = "".join(ch for ch in ref if ch.isalpha())
        pre = {"NT": "NT", "H": "H", "F": "F", "HS": "HS", "FB": "FB"}.get(pre, pre[:1]) if pre else "X"
        if ref.startswith(("U", "J", "Q", "D", "L", "C", "R")):
            pre = ref[0]
        self.count[pre] = self.count.get(pre, 0) + 1
        new = f"{pre}{self.sheet_no * 100 + self.count[pre]}"
        self.refmap[ref] = new
        return new

    def part(self, sym, ref, c, r, nets, value=None, rot=0, unit=None, stub=GRID, fp=None, mpn=None, dnp=False,
             note=""):
        if unit is None:
            unit = unit_of(sym, nets.keys()) if sym in MULTI else 1
        first = not (sym in MULTI and ref in self.refmap)
        ref = self.auto_ref(ref, sym)
        mpn = mpn if mpn is not None else MPN.get(sym, "")
        if first and not ref.startswith("#"):
            self.parts += 1
            foot = fp or DEFAULT_FP.get(sym) or lib_fp(sym)
            self.bom.append(dict(ref=ref, sym=sym, value=value or sym, footprint=foot, mpn=mpn, dnp=dnp, note=note))
        for pin_, n in nets.items():
            if n and n != "NC":
                self.nets.add(n)
                if not ref.startswith("#"):
                    self.pins.append((ref, str(pin_), n))
        if self.mode != "draw":
            return ref
        x, y = at(c, r)
        fields = {"MPN": mpn} if (mpn and not ref.startswith("#")) else None
        p = self.sh.place(sym, ref, x, y, rot=rot, unit=unit, value=value, fields=fields)
        if dnp:
            node = self.sh.tree[next(k for k, q in enumerate(self.sh.tree)
                                     if isinstance(q, list) and q and q[0] in ("sheet_instances", "embedded_fonts")) - 1]
            for q in node:
                if isinstance(q, list) and q and q[0] == "dnp":
                    q[1] = Sym("yes")
        dirs = {}
        for sub in find_all(lib()[sym], "symbol"):
            u = int(sub[1].rsplit("_", 2)[-2])
            if u not in (0, unit):
                continue
            for pn in find_all(sub, "pin"):
                dirs[str(find(pn, "number")[1])] = float(find(pn, "at")[3])
        for pin, net in nets.items():
            if not net:
                continue
            x0, y0 = p.pin(str(pin))
            if net == "NC":
                self.sh.no_connect(x0, y0)
                continue
            out = (dirs[str(pin)] + 180 + rot) % 360
            a = math.radians(out)
            x1, y1 = g(x0 + math.cos(a) * stub), g(y0 - math.sin(a) * stub)
            self.sh.wire((x0, y0), (x1, y1))
            lrot = int(round(out / 90.0)) * 90 % 360
            if net in POWER:
                self.sh.power(net, x1, y1)
            elif net in self.globals:
                self.sh.glabel(net, x1, y1, rot=lrot)
            else:
                self.sh.label(net, x1, y1, rot=lrot)
        return ref

    def skip(self, pre, n=1):
        """Keep the reference numbers of the later parts when a part is removed (refs stay as published)."""
        self.count[pre] = self.count.get(pre, 0) + n

    def text(self, s, c, r, size=1.27):
        if self.mode == "draw":
            self.sh.text(s, *at(c, r), size=size)

    def save(self):
        if self.mode == "draw":
            self.sh.save()


def R(d, ref, c, r, a, b, v, rot=90, **kw):
    return d.part("R", ref, c, r, {1: a, 2: b}, value=v, rot=rot, **kw)


def C(d, ref, c, r, a, b, v, rot=90, **kw):
    return d.part("C", ref, c, r, {1: a, 2: b}, value=v, rot=rot, **kw)


def CP(d, ref, c, r, plus, minus, v, rot=0, **kw):
    return d.part("C_Polarized", ref, c, r, {1: plus, 2: minus}, value=v, rot=rot, **kw)


def TAB(d, ref, c, r, nets, v):
    """Blade tabs (4.8 mm, 2 legs on 5.00 mm, 1.4 mm drill; interfaces.md 4.1): one Conn pin per tab."""
    sym = {1: "Conn_01x01", 2: "Conn_01x02"}[len(nets)]
    return d.part(sym, ref, c, r, {i + 1: n for i, n in enumerate(nets)}, value=v,
                  fp=FP_TAB1 if len(nets) == 1 else FP_TAB2, mpn="",
                  note="4.8 mm PCB blade tab(s), fully insulated receptacle; qty = tabs")


# ------------------------------------------------------------------ sheet 01
def sheet01(d):
    d.text("01 Raw HV input (W01), RAW_SS feeds to the preamp (W02) and PI + FX (W03) through 0 ohm link footprints "
           "(no fuses, interfaces.md 4.2), input filter (sim/ripple.py: B_P ripple 2-6 mV p-p), raw bleeder and HV "
           "indicator, power star, fault / RF network to the one plated mounting hole (grounding.md).", 0, -1.0, 2)
    TAB(d, "J1", 0, 1, ["B_P", "PGND"], "HV IN: B_P / B_N (W01-b, 4.8 mm tabs)")
    for k in (1, 2):
        R(d, f"R{k}", 2.5, 0.5 + 2 * (k - 1), "B_P", f"RAW_SS{k}", "0R jumper 2512 (link)", rot=0, fp=FP_LINK,
          mpn="", note="link footprint (interfaces.md 4.2): 0 ohm fitted")
    TAB(d, "J2", 5, 0.5, ["RAW_SS1", "GND_STAR"], "RAW OUT 1 to preamp J501 (W02-a): RAW_SS1 / GND_PRE1")
    TAB(d, "J3", 5, 2.5, ["RAW_SS2", "GND_STAR"], "RAW OUT 2 to PI + FX (W03-a): RAW_SS2 / GND_PRE2")
    # input filter: B_P side (PSU, RAW_SS taps) - 33 uH - UIN (bridges)
    CP(d, "C1", 0, 4.5, "B_P", "PGND", "47u/450V 105C", note="radial D16; ripple current small (B_P side)")
    CP(d, "C2", 1, 4.5, "B_P", "PGND", "47u/450V 105C", note="radial D16")
    C(d, "C3", 2, 4.5, "B_P", "PGND", "100n/630V X7R 1812", fp=FP_HVC, mpn="")
    d.part("L", "L1", 3, 4.5, {1: "B_P", 2: "UIN"}, value="33uH >= 2A", rot=90, fp=FP_LIN, mpn="",
           note="input filter inductor, radial D12 (part to choose: >= 2 A, insulation for 430 V)")
    CP(d, "C4", 4.5, 4.5, "UIN", "PGND", "47u/450V 105C", note="radial D16, between the two high-side collectors; "
       "carries the bridges' input ripple (0.2-0.3 A rms with C5): rating to check")
    C(d, "C5", 5.5, 4.5, "UIN", "PGND", "1u/630V MKP", fp=FP_FILM1U, mpn="", note="film, P22.5")
    # raw bleeder (SAFE-4: below 60 V within 60 s with about 200 uF on the raw side) and HV-present LED
    R(d, "R3", 7.5, 4, "UIN", "BLD1", "75k 2W MOX", fp=FP_AX2W, mpn="", note="0.62 W each at 430 V")
    R(d, "R4", 7.5, 5.5, "BLD1", "PGND", "75k 2W MOX", fp=FP_AX2W, mpn="")
    R(d, "R5", 8.5, 4, "UIN", "LED_RAW", "1M 2512 (500 V limiting)", fp=FP_R2512, mpn="", note="0.18 W at 430 V")
    d.part("LED", "D1", 8.5, 5.5, {2: "LED_RAW", 1: "PGND"}, value="red, 0.4 mA (HV PRESENT)", rot=90, mpn="")
    # power star
    d.part("NetTie_2", "NT1", 1, 7.5, {1: "PGND", 2: "GND_STAR"}, value="STAR POINT (power star)", mpn="",
           fp="NetTie:NetTie-2_SMD_Pad2.0mm")
    d.text("Power star GND_STAR: output films, damping legs, bleeders (sheet 02), GND_PWR / GND_PRE tabs, fault network. "
           "PGND: B_N, input capacitors, shunts, low-side drivers. GND (control) joins PGND once (sheet 05).", 0, 6.8)
    # fault / RF network to the plated mounting hole
    d.part("GBU8J", "D2", 4, 8, {2: "GND_STAR", 3: "CHASSIS", 1: "BR_DC", 4: "BR_DC"},
           value="GBU8J (+ and - joined: anti-parallel pair)")
    C(d, "C6", 6, 8, "GND_STAR", "CHASSIS", "100n Y2 300VAC", fp=FP_Y2, mpn="TDK B32023A3104M")
    R(d, "R6", 7, 8, "GND_STAR", "CHASSIS", "100 2W", fp=FP_AX2W, mpn="")
    d.part("MountingHole_Pad", "H1", 8.5, 8, {1: "CHASSIS"}, value="M3 plated: chassis bond (fault / RF network)",
           mpn="", note="star washer on cleaned aluminium (interfaces.md 14)")
    for i in range(3):
        d.part("MountingHole", f"H{i + 2}", 9.5 + i * 0.8, 8, {}, value="M3, non-plated", mpn="")
    d.part("PWR_FLAG", "#FLG101", 2.2, 7.6, {1: "PGND"}, value="PWR_FLAG")
    d.part("PWR_FLAG", "#FLG102", 2.2, 8.6, {1: "GND_STAR"}, value="PWR_FLAG")


# ------------------------------------------------------------------ sheet 02
def bridge(d, k, c0, out):
    t = str(k)
    d.text(f"Bridge {k}: {out} (synchronous buck, 50 kHz center-aligned; bridge 2 at 180 deg)", c0, 0.3, 1.8)
    C(d, f"C{k}1", c0, 2, "UIN", "PGND", "1n/1kV C0G 1812 (at the high-side collector)", fp=FP_HVC, mpn="")
    qn = ("TO-220 standing on the board's east edge, tab screwed to the chassis east wall through an insulating pad "
          "and bush (PLAN D12); collector tab live: ")
    d.part("Q_NIGBT_GCE", f"Q{k}1", c0 + 1.5, 2.5, {1: f"GH{t}", 2: "UIN", 3: f"SW{t}"}, value="IKP08N65F5",
           note=qn + "raw rail (high side)")
    d.part("Q_NIGBT_GCE", f"Q{k}2", c0 + 1.5, 5, {1: f"GL{t}", 2: f"SW{t}", 3: f"IS{t}"}, value="IKP08N65F5",
           note=qn + "switch node (low side)")
    R(d, f"R{k}1", c0 + 1.5, 7, f"IS{t}", "PGND", "50m 1W 1225 wide terminal (Kelvin)", fp=FP_SHUNT,
      mpn="Susumu KRL3264 class (to choose)", note="low-side emitter shunt: inductor current in the off-interval")
    d.part("L", f"L{k}1", c0 + 3, 3.5, {1: f"SW{t}", 2: f"UC{t}"}, value="2mH Fe-Si-Al toroid 32x16.4 (0.8mm, 6A)",
           rot=90, fp=FP_TOROID, mpn="", note="standing on edge, cable tie through the board slots")
    CP(d, f"C{k}2", c0 + 4.5, 4, f"UC{t}", f"IC{t}", "47u/450V 105C", note="first stage; 0.23-0.31 A rms (sim/ripple.py)")
    C(d, f"C{k}3", c0 + 5.5, 4, f"UC{t}", f"IC{t}", "4.7u/500V MKP DC-link", fp=FP_FILM4U7,
      mpn="Vishay MKP1848C class (size to confirm)", note="first stage film, 0.16-0.18 A rms")
    R(d, f"R{k}2", c0 + 5, 6, f"IC{t}", "PGND", "50m 1W 1225 wide terminal (Kelvin)", fp=FP_SHUNT,
      mpn="Susumu KRL3264 class (to choose)", note="first-stage capacitor shunt: both C1 parts return through it")
    d.part("L", f"L{k}2", c0 + 6.5, 3, {1: f"UC{t}", 2: out}, value="100uH >= 1.5A", rot=90, fp=FP_L100U, mpn="",
           note="second stage (part to choose: 1.5 A peak, insulation for 430 V)")
    C(d, f"C{k}4", c0 + 8, 4, out, "GND_STAR", "10u/500V MKP DC-link", fp=FP_FILM10U, mpn="Vishay MKP1848C61050JK2",
      note="output film, 32 x 18 x 28 mm")
    CP(d, f"C{k}5", c0 + 9, 4, out, f"CD{t}", "22u/450V 105C", fp=FP_EL22, note="damping leg (with R)")
    R(d, f"R{k}3", c0 + 9, 6, f"CD{t}", "GND_STAR", "2.2 1W (damping leg)", fp=FP_AX1WV, mpn="")
    R(d, f"R{k}4", c0 + 10, 4, out, f"BL{t}", "150k 2512 (500 V limiting)", fp=FP_R2512, mpn="", note="output bleeder")
    R(d, f"R{k}5", c0 + 10, 6, f"BL{t}", "GND_STAR", "150k 2512 (500 V limiting)", fp=FP_R2512, mpn="")


def sheet02(d):
    d.text("02 Two synchronous bucks from the raw rail (UIN), 50 kHz center-aligned, 180 deg apart (PLAN D5, D9). IKP08N65F5 "
           "on the chassis east wall; 2 mH toroid; filter variant D (sim/ripple.py): 47 uF + 4.7 uF film through the I_C "
           "shunt, 100 uH, 10 uF film + 22 uF / 2.2 ohm damping leg. Low-side and capacitor shunts 50 mohm (Kelvin taps "
           "on sheet 04). No protection hardware (PLAN D2).", 0, -1.0, 2)
    bridge(d, 1, 0, "V_ANODE")
    bridge(d, 2, 12, "V_SCREEN")
    TAB(d, "J1", 3, 9, ["V_ANODE", "GND_STAR"], "V_ANODE / GND_PWR (W04-a, 4.8 mm tabs)")
    TAB(d, "J2", 15, 9, ["V_SCREEN"], "V_SCREEN (W05-a, 4.8 mm tab)")


# ------------------------------------------------------------------ sheet 03
def drv(d, ref, c, r, vin, en_out, gnd2, vdd2, on, off):
    d.part("SI8271", ref, c, r, {1: vin, 2: "+3V3", 3: "GND", 4: en_out, 5: gnd2, 6: off, 7: on, 8: vdd2},
           value="Si8271DB (12 V UVLO, split outputs)")


def driver_pair(d, k, c0):
    t = str(k)
    hi, lo = f"PWM_H{t}", f"PWM_L{t}"
    d.text(f"Bridge {k}", c0, 0.3, 1.6)
    # high side (bootstrap)
    drv(d, f"U{k}1", c0 + 1.5, 2, hi, "HV_ENABLE", f"SW{t}", f"BOOT{t}", f"GHON{t}", f"GHOFF{t}")
    R(d, f"R{k}1", c0, 4, hi, "GND", "10k")
    C(d, f"C{k}1", c0 + 0.8, 4, "+3V3", "GND", "100n")
    R(d, f"R{k}2", c0 + 3.5, 1, "VDRV", f"BS{t}", "2.2", rot=0)
    d.part("D", f"D{k}1", c0 + 4.5, 1, {2: f"BS{t}", 1: f"BOOT{t}"}, value="ES1J (600 V ultrafast)", rot=0,
           fp="Diode_SMD:D_SMA", mpn="ES1J")
    C(d, f"C{k}2", c0 + 5.5, 2, f"BOOT{t}", f"SW{t}", "1u/25V X7R", fp=FP_C0805)
    C(d, f"C{k}3", c0 + 6.3, 2, f"BOOT{t}", f"SW{t}", "100n")
    R(d, f"R{k}3", c0 + 3.5, 3, f"GHON{t}", f"GH{t}", "15 (turn-on)", rot=0, fp="Resistor_SMD:R_0805_2012Metric")
    R(d, f"R{k}4", c0 + 3.5, 4, f"GHOFF{t}", f"GH{t}", "8.2 (turn-off)", rot=0, fp="Resistor_SMD:R_0805_2012Metric")
    R(d, f"R{k}5", c0 + 5.5, 4, f"GH{t}", f"SW{t}", "10k")
    C(d, f"C{k}4", c0 + 6.3, 4, f"GH{t}", f"SW{t}", "1n C0G (Miller immunity, at the IGBT)", fp=FP_C0805)
    # low side (from VDRV = 15 V, returned to PGND)
    drv(d, f"U{k}2", c0 + 1.5, 6.5, lo, "HV_ENABLE", "PGND", "VDRV", f"GLON{t}", f"GLOFF{t}")
    R(d, f"R{k}6", c0, 8.5, lo, "GND", "10k")
    C(d, f"C{k}5", c0 + 0.8, 8.5, "+3V3", "GND", "100n")
    C(d, f"C{k}6", c0 + 3.5, 5.5, "VDRV", "PGND", "1u/25V X7R", fp=FP_C0805)
    C(d, f"C{k}7", c0 + 4.3, 5.5, "VDRV", "PGND", "100n")
    R(d, f"R{k}7", c0 + 3.5, 7.5, f"GLON{t}", f"GL{t}", "15 (turn-on)", rot=0, fp="Resistor_SMD:R_0805_2012Metric")
    R(d, f"R{k}8", c0 + 3.5, 8.5, f"GLOFF{t}", f"GL{t}", "8.2 (turn-off)", rot=0, fp="Resistor_SMD:R_0805_2012Metric")
    R(d, f"R{k}9", c0 + 5.5, 8.5, f"GL{t}", f"IS{t}", "10k")
    C(d, f"C{k}8", c0 + 6.3, 8.5, f"GL{t}", f"IS{t}", "1n C0G (Miller immunity, at the IGBT)", fp=FP_C0805)
    d.part("PWR_FLAG", f"#FLG30{2 * k - 1}", c0 + 7.2, 1.5, {1: f"BOOT{t}"}, value="PWR_FLAG")
    d.part("PWR_FLAG", f"#FLG30{2 * k}", c0 + 7.2, 3.0, {1: f"SW{t}"}, value="PWR_FLAG")


def sheet03(d):
    d.text("03 Gate drive: one Si8271 per IGBT (PLAN D13). EN = HV_ENABLE (pulled down on sheet 05: link unplugged or "
           "control board off = drivers off); PWM inputs pulled down; 10k gate-emitter resistors keep the IGBTs off "
           "unpowered; 1 nF C0G G-E caps against Miller turn-on. High sides: bootstrap on VDRV.", 0, -1.0, 2)
    driver_pair(d, 1, 0)
    driver_pair(d, 2, 9)
    vdrv_boost(d, 18.5, 1)


def vdrv_boost(d, c0, r0):
    """12 V -> 15.1 V gate-drive supply (LM2731X, 1.6 MHz; TI SNVS217G section 8.2): R1 150k / R2 13.3k
    (1.23 V x 12.28), Cf 180p (zero at 5.9 kHz), 10 uH, 40 V Schottky, ceramic in / out."""
    d.text("VDRV boost 12 V -> 15.1 V. Si8271DB UVLO: on 11.0-13.5 V, off 9.6-12.1 V,", c0, r0 - 1.3, 1.6)
    d.text("so the 12 V link cannot start it; high sides about 14.2 V. +12 V about 30 mA typ, 39 mA max.", c0, r0 - 0.7, 1.6)
    C(d, "C1", c0, r0 + 1, "+12V", "PGND", "2.2u/25V X7R", fp=FP_C0805)
    d.part("L", "L1", c0 + 1.5, r0, {1: "+12V", 2: "VDRV_SW"}, value="10uH >= 0.5 A", rot=90,
           fp="Inductor_SMD:L_Bourns-SRN4018", mpn="SRN4018-100M")
    d.part("LM2731XMF", "U1", c0 + 1.5, r0 + 2, {5: "+12V", 4: "+12V", 1: "VDRV_SW", 2: "PGND", 3: "VDRV_FB"},
           value="LM2731XMF (1.6 MHz boost)", note="SHDN tied to VIN (datasheet 8.2.2: never floating)")
    d.part("D", "D1", c0 + 3, r0, {2: "VDRV_SW", 1: "VDRV"}, value="MBR0540 (40 V Schottky)", rot=0, mpn="MBR0540T1G")
    R(d, "R1", c0 + 4, r0 + 1.5, "VDRV", "VDRV_FB", "150k 1%")
    C(d, "C2", c0 + 4.8, r0 + 1.5, "VDRV", "VDRV_FB", "180p C0G (feedforward)")
    R(d, "R2", c0 + 4, r0 + 3, "VDRV_FB", "PGND", "13.3k 1%")
    C(d, "C3", c0 + 5.8, r0 + 1.5, "VDRV", "PGND", "10u/35V X7R", fp=FP_C1206)
    d.part("PWR_FLAG", "#FLG305", c0 + 6.6, r0 + 1, {1: "VDRV"}, value="PWR_FLAG")


# ------------------------------------------------------------------ sheet 04
SHUNTS = [("IS1", "IL1"), ("IC1", "IC1"), ("IS2", "IL2"), ("IC2", "IC2")]   # (shunt net, signal tag)
VOLTS = [("V_ANODE", "VA"), ("UC1", "VU1"), ("V_SCREEN", "VS"), ("UC2", "VU2"), ("B_P", "VR1"), ("UIN", "VR2")]


def opa2(d, ref, c, r, plus, minus, out):
    """OPA2836 (dual, SOIC-8, standard pinout: drawn with the OPA2356xxD symbol)."""
    pins = [(3, 2, 1), (5, 6, 7)]
    k = d.__dict__.setdefault("_o2", {}).setdefault(ref, 0)
    d._o2[ref] = k + 1
    p, m, o = pins[k]
    d.part("OPA2356xxD", ref, c, r, {p: plus, m: minus, o: out}, value="OPA2836ID")
    if k == 0:
        d.part("OPA2356xxD", ref, c, r + 1.6, {8: "+3V3", 4: "GND"}, value="OPA2836ID", unit=3)
        C(d, f"C{ref}", c + 0.8, r + 1.6, "+3V3", "GND", "100n")


def sheet04(d):
    d.text("04 Measurement (PLAN section 3): four shunt amplifiers (50 mohm, gain 6.25 around MID = 1.5 V: 0.3125 V/A, "
           "+-4 A into 0.25-2.75 V, about 20 MHz), six dividers 1/173.4 (520 V full scale) with buffers, two TMUX1308 "
           "8:1 muxes with a shared FPGA-driven address MUX_A0..2, two ADS7056 with shared ADC_CS / ADC_SCK and their "
           "own SDO. Mux 1 (bridge 1): 0 I_L1, 1 I_C1, 2 V_ANODE, 3 UC1, 4 RAW (B_P), 5 MID, 6-7 GND (zero check). Mux 2 "
           "(bridge 2): 0 I_C2, 1 I_L2, 2 V_SCREEN, 3 UC2, 4 RAW (UIN), 5 MID, 6-7 GND.", 0, -1.0, 2)
    amps = ["UA1", "UA1", "UA2", "UA2"]
    for i, (src, tag) in enumerate(SHUNTS):
        c0 = i * 4.5
        d.part("NetTie_2", f"NT{2 * i + 1}", c0 + 2.5, 1, {1: src, 2: f"KS{i}P"}, value=f"Kelvin tap {src} (at the shunt)", mpn="")
        d.part("NetTie_2", f"NT{2 * i + 2}", c0 + 2.5, 3.4, {1: "PGND", 2: f"KS{i}N"}, value="Kelvin tap PGND (at the shunt)",
               mpn="")
        R(d, f"RI{i}1", c0, 1, f"KS{i}P", f"IA{i}P", "240 0.1%", rot=0)
        R(d, f"RI{i}2", c0 + 1, 2, f"IA{i}P", "MID", "1.5k 0.1%")
        C(d, f"CI{i}1", c0 + 1.8, 2, f"IA{i}P", "MID", "10p C0G")
        R(d, f"RI{i}3", c0, 3.4, f"KS{i}N", f"IA{i}N", "240 0.1%", rot=0)
        R(d, f"RI{i}4", c0 + 1, 4.4, f"IA{i}N", f"I_{tag}", "1.5k 0.1%", rot=0)
        C(d, f"CI{i}2", c0 + 1, 5.2, f"IA{i}N", f"I_{tag}", "10p C0G", rot=0)
        opa2(d, amps[i], c0 + 1, 6.5, f"IA{i}P", f"IA{i}N", f"I_{tag}")
        R(d, f"RI{i}5", c0 + 3, 6.5, f"I_{tag}", f"MX_{tag}", "47", rot=0)
        C(d, f"CI{i}3", c0 + 3.8, 7.5, f"MX_{tag}", "GND", "100p C0G")
    bufs = ["UA3", "UA3", "UA4", "UA4", "UA5", "UA5"]
    for i, (src, tag) in enumerate(VOLTS):
        c0 = i * 3.5
        for j in range(3):
            R(d, f"RV{i}{j + 1}", c0, 10 + j * 1.3, src if j == 0 else f"DV{i}{j}", f"DV{i}{j + 1}",
              "1M 0.1% 1206 HV thin film (TNPV1206 class, >= 400 V)", fp=FP_R1206, note="<= 175 V each at 520 V")
        R(d, f"RV{i}5", c0 + 1, 13.9, f"DV{i}3", "GND", "17.4k 0.1%")
        C(d, f"CV{i}", c0 + 1.8, 13.9, f"DV{i}3", "GND", "100p C0G (tau 1.7 us)")
        opa2(d, bufs[i], c0 + 1, 15.5, f"DV{i}3", f"V_{tag}", f"V_{tag}")
        R(d, f"RV{i}6", c0 + 2.5, 17.5, f"V_{tag}", f"MX_{tag}", "47", rot=0)
    # MID = 1.5 V from the reference, buffered (feeds the eight 1.5k legs and mux channel 5)
    R(d, "RB1", 22, 10, "VREF", "MID_DIV", "10k 0.1%")
    R(d, "RB2", 22, 11.3, "MID_DIV", "GND", "10k 0.1%")
    C(d, "CB1", 22.8, 11.3, "MID_DIV", "GND", "100n")
    opa2(d, "UA7", 23.5, 13, "MID_DIV", "MID_FB", "MID_FB")
    R(d, "RB3", 25, 13, "MID_FB", "MID", "10", rot=0)
    C(d, "CB2", 26, 14, "MID", "GND", "1u X7R")
    opa2(d, "UA7", 23.5, 16.5, "GND", "SPARE_O", "SPARE_O")     # unused half: follower at ground
    # multiplexers (4051 pinout: Y0 13, Y1 14, Y2 15, Y3 12, Y4 1, Y5 5, Y6 2, Y7 4, Z 3, E 6, S1 11, S2 10, S3 9)
    chans = {1: ["MX_IL1", "MX_IC1", "MX_VA", "MX_VU1", "MX_VR1", "MID", "GND", "GND"],
             2: ["MX_IC2", "MX_IL2", "MX_VS", "MX_VU2", "MX_VR2", "MID", "GND", "GND"]}
    ypin = [13, 14, 15, 12, 1, 5, 2, 4]
    for k in (1, 2):
        c0 = (k - 1) * 14
        m = {ypin[n]: chans[k][n] for n in range(8)}
        m.update({3: f"MUXO{k}", 6: "GND", 7: "NC", 8: "GND", 11: "MUX_A0", 10: "MUX_A1", 9: "MUX_A2", 16: "+3V3"})
        d.part("NX3L4051PW", f"U{k}", c0 + 1, 21, m, value="TMUX1308PW (8:1, 4051 pinout)", mpn="TMUX1308PWR",
               fp="Package_SO:TSSOP-16_4.4x5mm_P0.65mm")
        C(d, f"CM{k}", c0 + 2.6, 22.6, "+3V3", "GND", "100n")
        opa2(d, "UA6", c0 + 4.5, 21, f"MUXO{k}", f"ADRV{k}", f"ADRV{k}")
        R(d, f"RA{k}1", c0 + 6.5, 21.5, f"ADRV{k}", f"AIN{k}", "33", rot=0)
        C(d, f"CA{k}1", c0 + 7.5, 22.5, f"AIN{k}", "GND", "680p C0G (charge bucket)")
        d.part("ADS7056", f"U{k + 2}", c0 + 9.5, 21, {1: "ADC_CS", 2: f"SDOL{k}", 3: "ADC_SCK", 4: "+3V3", 5: "GND",
                                                     6: "VREF", 7: f"AIN{k}", 8: "GND"},
               value="ADS7056 (14 bit, 2.5 MSPS)", note="X2QFN-8 (RUG); AVDD = reference = VREF 3.0 V, DVDD 3.3 V")
        C(d, f"CA{k}2", c0 + 11, 22.5, "VREF", "GND", "1u X7R")
        C(d, f"CA{k}3", c0 + 11.8, 22.5, "+3V3", "GND", "100n")
        R(d, f"RA{k}2", c0 + 11.5, 20, f"SDOL{k}", f"ADC_SDO{k}", "33", rot=0)
    R(d, "R1", 29, 21, "ADC_SCK", "ADC_SCK_RET", "33 (returned SCK: far end of the SCLK trace)", rot=0)
    R(d, "R2", 29, 22.5, "ADC_CS", "+3V3", "10k")
    R(d, "R3", 30, 22.5, "ADC_SCK", "GND", "100k")
    for i in range(3):
        R(d, f"R{4 + i}", 31 + i * 0.8, 22.5, f"MUX_A{i}", "GND", "100k")
    # 3.0 V reference
    d.part("FerriteBead", "FB1", 22, 25, {1: "+3V3", 2: "+3V3_REF"}, value="600R@100MHz 0603",
           fp="Inductor_SMD:L_0603_1608Metric", mpn="")
    C(d, "C1", 23, 25.5, "+3V3_REF", "GND", "10u", fp=FP_C0805)
    d.part("REF3030", "U5", 24.5, 25, {1: "+3V3_REF", 2: "VREF", 3: "GND"}, value="REF3030 (3.0 V)",
           note="ADS7056 AVDD x2, MID divider")
    C(d, "C2", 26, 25.5, "VREF", "GND", "1u X7R")
    d.part("PWR_FLAG", "#FLG401", 22, 26.5, {1: "+3V3_REF"}, value="PWR_FLAG")


# ------------------------------------------------------------------ sheet 05
J1MAP = {k: "NC" for k in range(1, 41)}
J1MAP.update({2: "GND", 4: "GND", 6: "GND", 11: "MUX_A0", 12: "MUX_A2", 13: "MUX_A1", 14: "ADC_SCK", 15: "ADC_CS",
              16: "ADC_SCK_RET", 17: "ADC_SDO1", 18: "GND", 19: "ADC_SDO2", 20: "GND", 22: "GND",
              29: "PWM_L1", 30: "PWM_L2", 31: "PWM_H1", 32: "PWM_H2", 33: "GND", 34: "GND", 35: "+3V3", 36: "+3V3",
              37: "HV_PERMIT_STAT", 38: "HV_ENABLE", 39: "+12V", 40: "+12V"})


def sheet05(d):
    d.text("05 J1 (W17-b, 2x20 1.27 mm), rev4 pad table PROPOSED (PLAN section 4): card -> HV PWM 29-32, HV_ENABLE 38, "
           "ADC_SCK 14, ADC_CS 15, MUX_A0 11, MUX_A1 13, MUX_A2 12 (was a back channel in IF-2.2); HV -> card ADC_SDO1 17, "
           "ADC_SDO2 19, ADC_SCK_RET 16, HV_PERMIT_STAT 37. HV_PERMIT (W16) is reported only, it gates nothing (PLAN D3).",
           0, -1.0, 2)
    d.part("Conn_02x20_Odd_Even", "=J1", 0, 3, J1MAP, value="CONTROL 40-pin (W17-b, isolated on the control board)",
           mpn="Samtec SHF-120-01-L-D-TH", note="1.27 mm 2x20 shrouded THT header")
    for i, n in enumerate(("+3V3", "+12V", "GND")):
        d.part("PWR_FLAG", f"#FLG50{i}", 2, 8 + i * 0.6, {1: n}, value="PWR_FLAG")
    C(d, "C1", 3, 7, "+3V3", "GND", "10u", fp=FP_C0805)
    C(d, "C2", 3.8, 7, "+12V", "GND", "10u/25V", fp=FP_C1206)
    d.part("NetTie_2", "NT1", 3, 9, {1: "GND", 2: "PGND"}, value="GND to PGND (one tie, at the shunts)", mpn="")
    R(d, "R1", 5, 7, "HV_ENABLE", "GND", "10k", note="drivers off when the link is unplugged or the card is off")
    # HV_PERMIT current loop (W16-b): opto input, status only
    d.part("Conn_01x02", "J2", 5, 1, {1: "HVP_P", 2: "HVP_N"}, value="HV_PERMIT +/- (W16-b, twisted pair)",
           mpn="Molex 22-27-2021")
    d.part("D_TVS", "D1", 7, 1.5, {1: "HVP_P", 2: "HVP_N"}, value="SMAJ24CA", rot=90, mpn="SMAJ24CA")
    R(d, "R2", 8, 0.5, "HVP_P", "HVP_A", "47", rot=0)
    R(d, "R3", 9, 1.5, "HVP_A", "HVP_N", "680 (threshold ~2 mA)")
    d.part("D", "D2", 10, 1.5, {1: "HVP_A", 2: "HVP_N"}, value="1N4148W (reverse)", rot=90, mpn="1N4148W")
    d.part("TLP293", "U1", 12, 1, {1: "HVP_A", 2: "HVP_N", 3: "PERMIT_E", 4: "+3V3"}, value="TLP293 (CTR >= 50 %)")
    R(d, "R4", 14, 2, "PERMIT_E", "GND", "10k")
    R(d, "R5", 15, 1, "PERMIT_E", "PERMIT_F", "1k", rot=0)
    C(d, "C3", 16, 2, "PERMIT_F", "GND", "10n")
    d.part("74LVC1G17", "U2", 17.5, 1, {1: "NC", 2: "PERMIT_F", 3: "GND", 4: "HV_PERMIT_STAT", 5: "+3V3"}, value="74LVC1G17")
    C(d, "C4", 19, 2, "+3V3", "GND", "100n")


SHEETS = [("01_input_star.kicad_sch", sheet01), ("02_bridges.kicad_sch", sheet02),
          ("03_gate_drive.kicad_sch", sheet03), ("04_measurement.kicad_sch", sheet04),
          ("05_interface.kicad_sch", sheet05)]


def check_fp(fp):
    libname, name = fp.split(":", 1)
    if libname == LOCAL_LIB:
        return os.path.exists(os.path.join(RB, "lib", LOCAL_LIB + ".pretty", name + ".kicad_mod"))
    return os.path.exists(os.path.join(KICAD_FP, libname + ".pretty", name + ".kicad_mod"))


def write_maps(bom):
    missing = sorted({b["footprint"] for b in bom if b["footprint"] and not check_fp(b["footprint"])})
    if missing:
        raise SystemExit("footprints not found: " + ", ".join(missing))
    nofp = sorted(b["ref"] for b in bom if not b["footprint"])
    if nofp:
        raise SystemExit("no footprint: " + ", ".join(nofp))
    path = os.path.join(RB, "lib", "footprint_map.csv")
    with open(path, "w", newline="") as f:
        f.write("# refdes -> footprint, generated by tools/sheets/draw_all.py (do not edit)\n")
        w = csv.writer(f)
        w.writerow(["refdes", "footprint"])
        for b in sorted(bom, key=lambda b: b["ref"]):
            w.writerow([b["ref"], b["footprint"]])
    groups = {}
    for b in bom:
        key = (b["value"], b["footprint"], b["mpn"], b["dnp"], b["sym"])
        groups.setdefault(key, []).append(b)
    os.makedirs(os.path.join(RB, "bom"), exist_ok=True)

    def refkey(r):
        pre = "".join(c for c in r if c.isalpha())
        return pre, int("".join(c for c in r if c.isdigit()) or 0)

    rows = []
    for (value, fp, mpn, dnp, sym), items in groups.items():
        refs = sorted((b["ref"] for b in items), key=refkey)
        notes = "; ".join(sorted({b["note"] for b in items if b["note"]}))
        qty = len(refs) * (2 if fp == FP_TAB2 else 1)
        placeholder = "PLACEHOLDER" in fp or "TBD" in value or "placeholder" in value
        rows.append([" ".join(refs), qty, value, fp, mpn, "DNP" if dnp else "", "yes" if placeholder else "", notes])
    rows.sort(key=lambda r: refkey(r[0].split(" ")[0]))
    with open(os.path.join(RB, "bom", "bom.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["refs", "qty", "value", "footprint", "candidate_mpn", "dnp", "placeholder", "note"])
        w.writerows(rows)
    return len(rows)


def main():
    seen = {}
    bom = []
    pins = []
    for f, fn in SHEETS:
        d = Drawer(f, "collect")
        fn(d)
        bom += d.bom
        pins += d.pins
        for n in d.nets:
            seen.setdefault(n, set()).add(f)
    lines = write_maps(bom)
    os.makedirs(os.path.join(RB, "reports"), exist_ok=True)
    with open(os.path.join(RB, "reports", "intended_nets.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ref", "pin", "net"])
        w.writerows(sorted(set(pins)))
    glob = frozenset(n for n, fs in seen.items() if len(fs) > 1 and n not in POWER)
    total = 0
    for f, fn in SHEETS:
        d = Drawer(f, "draw", glob)
        fn(d)
        d.save()
        total += d.parts
        print(f"{f}: {d.parts} parts")
    print(f"parts: {total}, nets: {len(seen)}, global: {len(glob)}, BOM lines: {lines}")


if __name__ == "__main__":
    main()
