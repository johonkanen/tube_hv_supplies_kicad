#!/usr/bin/env python3
"""Draw the five HV supplies rev 3 sheets (second pass, 2026-11-23: a consistent first draft),
assign the footprints (lib/footprint_map.csv, read by p2k's sheet builder) and write the BOM
(bom/bom.csv).

Sources: tube_amplifier_kicad docs/interfaces.md (IF-1.2; IF-2 on W17, section 9), docs/grounding.md,
SPECIFICATION.md PS-1..PS-5, PA-6, SAFE-2/3/4/6, ENV-2 (70 C under the plate), the review
docs/revb_first_pass_review.md (7.1 decisions U3, U4, U17, U19; K12; M16, M19), the first pass
(c947e82) and rev3/sim (loop_digital.py, lc_ac.py, discharge.py). What changed and why: rev3/STATUS.md.

Netlist-first drawing as in tube_preamp_kicad rev_b: every part on a grid, a wire stub and a label
on every pin (local label if the net stays on one sheet, global label if it crosses sheets, a
power symbol for GND / +3V3 / +12V). Exact for ERC and the netlist; a tidy layout pass comes later.
Values marked "TBD" or "PLACEHOLDER" still need a part choice (rev3/STATUS.md).

Grounds (docs/grounding.md):
  PGND      switching ground: B_N tab, input capacitors, low-side shunts, the electrolytics'
            current shunts, gate-driver low side
  GND_STAR  power star: output film capacitors, the feed returns GND_PWR / GND_PRE1 / GND_PRE2,
            bleeders, the fault / RF network to the chassis
  GND       control ground: J1 pads 33 / 34 (isolated on the control board), op amps, ADC, logic
  NT101 joins PGND and GND_STAR at one point (the star point), NT501 joins GND to PGND at the
  low-side shunts (Kelvin), so each domain has exactly one tie.
Run from anywhere: python3 rev3/tools/sheets/draw_all.py
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
MULTI = {"MCP6004", "LMV339", "OPA2356xxD"}
KICAD_FP = os.environ.get("KICAD_FOOTPRINTS", "/mnt/c/Program Files/KiCad/10.0/share/kicad/footprints")
LOCAL_LIB = "tube_hv_supplies_rev3"

# footprints by symbol (overridden per part with fp=)
FP_R = "Resistor_SMD:R_0603_1608Metric"
FP_R1206 = "Resistor_SMD:R_1206_3216Metric"
FP_R2512 = "Resistor_SMD:R_2512_6332Metric"
FP_AX1W = "Resistor_THT:R_Axial_DIN0414_L11.9mm_D4.5mm_P15.24mm_Horizontal"
FP_AX2W = "Resistor_THT:R_Axial_DIN0617_L17.0mm_D6.0mm_P20.32mm_Horizontal"
FP_AX5W = "Resistor_THT:R_Axial_DIN0918_L18.0mm_D9.0mm_P7.62mm_Vertical"   # ULW5 standing (fourth pass: board area)
FP_AX1WV = "Resistor_THT:R_Axial_DIN0414_L11.9mm_D4.5mm_P7.62mm_Vertical"
FP_LINK = "Resistor_SMD:R_2512_6332Metric"   # 0 ohm jumper (fourth pass: on the plate side, board area)
FP_C = "Capacitor_SMD:C_0603_1608Metric"
FP_C1206 = "Capacitor_SMD:C_1206_3216Metric"
FP_EL47 = "Capacitor_THT:CP_Radial_D18.0mm_P7.50mm"
FP_EL100 = "Capacitor_THT:CP_Radial_D22.0mm_P10.00mm_SnapIn"
FP_FILM100N = "Capacitor_SMD:C_1812_4532Metric"
FP_FILM1U = "Capacitor_THT:C_Rect_L31.5mm_W11.0mm_P27.50mm_MKS4"
FP_FILM4U7 = "Capacitor_THT:C_Rect_L31.5mm_W17.0mm_P27.50mm_MKS4"   # TDK B32674D6475K class (4.7 uF 630 V DC-link MKP, P27.5)
FP_EL22 = "Capacitor_THT:CP_Radial_D16.0mm_P7.50mm"
FP_TO220 = f"{LOCAL_LIB}:TO-220-3_Horizontal_TabUp_Bar"   # lying on the plate (aluminium bar), leads bent down into the board (no board hole)
FP_Y2 = "Capacitor_THT:C_Rect_L26.5mm_W8.5mm_P22.50mm_MKS4"
FP_TAB1 = f"{LOCAL_LIB}:Blade_Tab_4.8mm_1x"
FP_TAB2 = f"{LOCAL_LIB}:Blade_Tab_4.8mm_2x_P12mm"
DEFAULT_FP = {
    "R": FP_R, "C": FP_C, "C_Polarized": FP_EL47, "D": "Diode_SMD:D_SOD-123", "D_TVS": "Diode_SMD:D_SMA",
    "LED": "LED_SMD:LED_0805_2012Metric", "NetTie_2": "NetTie:NetTie-2_SMD_Pad0.5mm",
    "Q_NIGBT_GCE": "Package_TO_SOT_THT:TO-220-3_Vertical",
    "Fuse": "Fuse:Fuseholder_Clip-5x20mm_Littelfuse_100_Inline_P20.50x4.60mm_D1.30mm_Horizontal",
    "MCP6004": "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm", "LMV339": "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
    "74LVC1G10": "Package_TO_SOT_SMD:SOT-23-6", "74LVC1G17": "Package_TO_SOT_SMD:SOT-23-5",
    "74AUP1G74": "Package_SO:VSSOP-8_2.3x2mm_P0.5mm",
    "74LVC1G07": "Package_TO_SOT_SMD:SOT-23-5", "74LVC1G08": "Package_TO_SOT_SMD:SOT-23-5",
    "OPA2356xxD": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "ADS7056": "Package_DFN_QFN:Texas_UQFN-8_1.5x1.5mm_P0.5mm",
    "REF3030": "Package_TO_SOT_SMD:SOT-23",
    "MountingHole_Pad": "MountingHole:MountingHole_3.2mm_M3_DIN965_Pad", "MountingHole": "MountingHole:MountingHole_3.2mm_M3",
    "Heatsink": "Heatsink:Heatsink_Fischer_SK104-STCB_35x13mm__2xDrill3.5mm_ScrewM3",
    "Conn_02x20_Odd_Even": "Connector_PinHeader_1.27mm:PinHeader_2x20_P1.27mm_Vertical",
    "Conn_01x02": "Connector_Molex:Molex_KK-254_AE-6410-02A_1x02_P2.54mm_Vertical",
}
MPN = {"MCP6004": "MCP6004-E/SL", "LMV339": "LMV339IDR", "74LVC1G10": "SN74LVC1G10DBVR",
       "74LVC1G17": "SN74LVC1G17DBVR", "74AUP1G74": "SN74AUP1G74DCUR", "UCC21520DW": "UCC21520DWR",
       "AD7689xCP": "AD7689BCPZRL7", "TLP293": "TLP293(GB-TPL,E)", "LM4040DBZ-2.5": "LM4040A25IDBZR",
       "GBU8J": "GBU8J", "Q_NIGBT_GCE": "IKP08N65F5XKSA1", "74LVC1G07": "SN74LVC1G07DBVR",
       "74LVC1G08": "SN74LVC1G08DBVR", "OPA2356xxD": "OPA2836IDR", "ADS7056": "ADS7056IRUGR", "REF3030": "REF3030AIDBZR"}


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
        for n in nets.values():
            if n and n != "NC":
                self.nets.add(n)
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


def opamp(d, ref, c, r, plus, minus, out, v="MCP6004"):
    pins = {"MCP6004": [(3, 2, 1), (5, 6, 7), (10, 9, 8), (12, 13, 14)]}[v]
    k = d.__dict__.setdefault("_oa", {}).setdefault(ref, 0)
    d._oa[ref] = k + 1
    p, m, o = pins[k]
    d.part(v, ref, c, r, {p: plus, m: minus, o: out}, value=v)
    if k == 0:
        d.part(v, ref, c, r + 1.6, {4: "+3V3", 11: "GND"}, value=v, unit=5)


def comp(d, ref, c, r, plus, minus, out):
    pins = [(5, 4, 2), (7, 6, 1), (11, 10, 13), (9, 8, 14)]
    k = d.__dict__.setdefault("_cp", {}).setdefault(ref, 0)
    d._cp[ref] = k + 1
    p, m, o = pins[k]
    d.part("LMV339", ref, c, r, {p: plus, m: minus, o: out}, value="LMV339")
    if k == 0:
        d.part("LMV339", ref, c, r + 1.6, {3: "+3V3", 12: "GND"}, value="LMV339", unit=5)


# ------------------------------------------------------------------ sheet 01
def sheet01(d):
    d.text("01 Raw HV input (W01), RAW_SS feeds to the preamp (W02) and PI + FX (W03) through link footprints "
           "(no fuses: user 2026-11-23), input filter, power star (grounding.md section 3), fault / RF network to "
           "the plated chassis standoff next to the raw input tabs, raw bleeder and HV indicator. No brake: the "
           "ramp energy goes back into the tube PSU (user 2026-11-21); the raw over-voltage trip is on sheet 05.",
           0, -1.0, 2)
    TAB(d, "J1", 0, 1, ["B_P", "PGND"], "HV IN: B_P / B_N (W01-b, 4.8 mm tabs)")
    d.text("B_N lands on PGND: the bridges' switching loops return here and join the star only at NT101", 0, 0.4)
    # RAW_SS: taken ahead of the input filter (PSU side), so the bridges' ripple stays behind L101.
    # Link footprints (interfaces.md 4.2 PROPOSED): fitted as 0 ohm; a 10-47 ohm 2 W flameproof fusible
    # resistor can go in the same footprint to give a wiring fault a defined weak point.
    for k in (1, 2):
        R(d, f"R{k}", 3, 0.5 + 2 * (k - 1), "B_P", f"RAW_SS{k}", "0R jumper 2512 (link)",
          rot=0, fp=FP_LINK, mpn="", note="link (interfaces.md 4.2), plate side; the fusible-resistor option of the 0617 footprint is dropped (board area, fourth pass)")
    TAB(d, "J2", 5, 0.5, ["RAW_SS1", "GND_STAR"], "RAW OUT 1 to preamp J501 (W02-a): RAW_SS1 / GND_PRE1")
    TAB(d, "J3", 5, 2.5, ["RAW_SS2", "GND_STAR"], "RAW OUT 2 to PI + FX (W03-a): RAW_SS2 / GND_PRE2")
    # input filter: C101 on B_P, L101, the bridge-local 47 uF on UIN (sheet 02); lc_ac.py: peak 0.7-0.9 ohm
    # against the bridges' -616 ohm input resistance (Middlebrook: far apart)
    CP(d, "C1", 1, 4, "B_P", "PGND", "47u/500V 105C", note="radial D18, ripple rating at 70 C to check")
    C(d, "C2", 2, 4, "B_P", "PGND", "100n/630V X7R 1812", fp=FP_FILM100N, mpn="")
    d.part("L", "L1", 3, 4.5, {1: "B_P", 2: "UIN"}, value="33uH 2A", rot=90,
           fp="Inductor_THT:L_Radial_D12.0mm_P5.00mm_Fastron_11P", mpn="", note="33 uH, >= 2 A, radial D12")
    C(d, "C3", 5, 4, "UIN", "PGND", "1n/1kV C0G", fp=FP_C1206, mpn="")
    # raw bleeder and HV-present indicator (SAFE-4: below 60 V within 60 s)
    R(d, "R3", 8, 4, "UIN", "BLD1", "75k 2W MOX", fp=FP_AX2W, mpn="", note="0.62 W each at 430 V")
    R(d, "R4", 8, 5.5, "BLD1", "PGND", "75k 2W MOX", fp=FP_AX2W, mpn="")
    R(d, "R5", 9, 4, "UIN", "LED_RAW", "1M 1W HV (VR37 class)", fp=FP_AX1W, mpn="")
    d.part("LED", "D1", 9, 5.5, {2: "LED_RAW", 1: "PGND"}, value="red, 0.4 mA (HV PRESENT)", rot=90, mpn="")
    # power star: the one tie between PGND and GND_STAR
    d.part("NetTie_2", "NT1", 1, 7, {1: "PGND", 2: "GND_STAR"}, value="STAR POINT (power star)", mpn="",
           fp="NetTie:NetTie-2_SMD_Pad2.0mm")   # carries the whole return current (about 1 A)
    d.text("Power star (GND_STAR): output film capacitors and bleeders (sheet 02), GND_PWR / GND_PRE1 / GND_PRE2 tabs, "
           "fault network", 0, 6.4)
    # fault / RF network: anti-parallel diodes (bridge, + and - joined) || 100 nF Y2 || 100 ohm, to the plated
    # standoff H101 next to the raw input tabs; every other mounting hole non-plated
    d.part("GBU8J", "D2", 4, 8, {2: "GND_STAR", 3: "CHASSIS", 1: "BR_DC", 4: "BR_DC"},
           value="GBU8J (8 A 600 V, + and - joined: anti-parallel pair)")
    C(d, "C4", 6, 8, "GND_STAR", "CHASSIS", "100n Y2 300VAC", fp=FP_Y2, mpn="TDK B32023A3104M",
      note="Y2 film, P22.5 (body width to check against the TDK drawing)")
    R(d, "R6", 7, 8, "GND_STAR", "CHASSIS", "100 2W", fp=FP_AX2W, mpn="")
    d.part("MountingHole_Pad", "H1", 9, 8, {1: "CHASSIS"}, value="CHASSIS standoff, plated (fault / RF network)",
           mpn="", note="new plate hole next to J101 (mechanical/floorplan.md)")
    for i in range(5):
        d.part("MountingHole", f"H{i + 2}", 10 + i * 0.8, 8, {}, value="M3, non-plated (no chassis contact)", mpn="",
               note="standoffs (fourth pass, mechanical/floorplan_chosen.md): (600.0, 98.0) (671.0, 48.0) (667.0, 138.0) (553.0, 195.0) (566.0, 122.0)")
    d.part("PWR_FLAG", "#FLG101", 2, 7.6, {1: "PGND"}, value="PWR_FLAG")


# ------------------------------------------------------------------ sheet 02
L1_VAL = {1: "220uH ETD39 N97, 50t litz 0.8mm2, gap ~1.8mm (Isat >= 10A, DCR ~0.1R hot)",
          2: "470uH ETD39 N97, 64t litz 0.5mm2, gap ~1.4mm (Isat >= 6A, DCR ~0.2R hot)"}


def bridge(d, k, c0, out, tag):
    """One half-bridge synchronous buck in triangular-current mode (fourth pass, 2026-11-24): Q_H / Q_L
    IGBTs lying on the chassis plate (aluminium bar, 1.5 mm Al2O3 washers), low-side emitter shunt,
    220 / 470 uH main inductor, C1 = 100 uF electrolytic + 4.7 uF film both returned through the I_C shunt,
    second stage 68 uH with a 4.7 uF film output and a 22 uF + 1.0 ohm damping leg (L2-C2 8.9 kHz, damped
    peak 5 kHz / 3.5 ohm: sim/r2_filter.py), series fusible resistor to the tab, bleeders to the star.
    Reference numbers are kept from the third pass; removed parts leave their numbers unused."""
    t = str(k)
    d.text(f"Bridge {k}: {tag}", c0, 0.3, 1.8)
    R(d, f"R{k}7", c0, 1.5, "UIN", f"UIN{t}", "0R jumper 2512 (bridge input link)",
      fp=FP_LINK, mpn="", note="proposal N7: no fuse (PSU short-circuit protection + 3.0 A trips); plate side (fourth pass)")
    CP(d, f"C{k}1", c0 + 1, 2, f"UIN{t}", "PGND", "47u/500V 105C")
    C(d, f"C{k}2", c0 + 2, 2, f"UIN{t}", "PGND", "100n/630V X7R 1812", fp=FP_FILM100N, mpn="")
    C(d, f"C{k}3", c0 + 3, 2, f"UIN{t}", "PGND", "1n/1kV C0G", fp=FP_C1206, mpn="")
    qnote = ("lies on the chassis plate: 6 mm aluminium bar, 1.5 mm Al2O3 washer, PEEK shoulder bush, M3 countersunk "
             "from the plate's top with a nut on the tab (fitted before the board); leads bent down 90 deg about 5 mm into the board "
             "(STATUS fourth pass). Collector tab live: ")
    d.part("Q_NIGBT_GCE", f"Q{k}1", c0 + 1, 4, {1: f"GH{t}", 2: f"UIN{t}", 3: f"SW{t}"}, value="IKP08N65F5", fp=FP_TO220,
           note=qnote + "raw rail (high side)")
    d.part("Q_NIGBT_GCE", f"Q{k}2", c0 + 1, 6, {1: f"GL{t}", 2: f"SW{t}", 3: f"IS{t}"}, value="IKP08N65F5", fp=FP_TO220,
           note=qnote + "switch node (low side)")
    R(d, f"R{k}1", c0 + 1, 7.6, f"IS{t}", "PGND", "50m 1W 2512 metal strip (Kelvin)", fp=FP_R2512, mpn="Vishay WSL2512R0500FEA",
      note="metal element: M20 pulses up to 220 A / 0.29 J in 0.2 ms on the I_C shunt (pulse rating to confirm)")
    d.part("L", f"L{k}1", c0 + 3, 4.5, {1: f"SW{t}", 2: f"UC{t}"}, value=L1_VAL[k],
           rot=90, fp=f"{LOCAL_LIB}:L_ETD39_2pin_custom", mpn="TDK B66363G0000X197 (N97) core set + ETD39 bobbin",
           note="custom-wound; litz 0.1 mm strands; gap split or winding kept 3 mm from the gap (fringing); "
                "600 V winding-core insulation; pin positions to the chosen bobbin")
    CP(d, f"C{k}4", c0 + 4, 5.5, f"UC{t}", f"IC{t}", "100u/500V 105C 5000h snap-in", fp=FP_EL100,
       mpn="Vishay MAL215919101E3 (PUL-SI, 22 x 40)",
       note="TCM ripple 0.2-0.84 A rms at 40-150 kHz (sim/r2_filter.py); about 0.8 A at 120 Hz / 105 C rated, "
            "x1.4 at >= 10 kHz, more at 80 C: to confirm on the Vishay datasheet; alternative Rubycon 500VXT100MEFCSN22X25")
    R(d, f"R{k}2", c0 + 4, 7.2, f"IC{t}", "PGND", "50m 1W 2512 metal strip (Kelvin)", fp=FP_R2512, mpn="Vishay WSL2512R0500FEA",
      note="metal element: M20 pulses up to 220 A / 0.29 J in 0.2 ms on the I_C shunt (pulse rating to confirm)")
    d.part("L", f"L{k}2", c0 + 5, 4.5, {1: f"UC{t}", 2: f"VO{t}"}, value="68uH >= 2A", rot=90,
           fp="Inductor_THT:L_Radial_D16.8mm_P11.43mm_Vishay_IHB-1", mpn="Vishay IHB-1 68 uH (current rating to confirm >= 2 A)",
           note="second stage: carries the DC output current and the audio current, almost no ripple")
    d.skip("R")   # R204 / R211 (5.6 ohm across L202 / L204) removed: the damping is the Rd-Cd leg (bridge_extra)
    C(d, f"C{k}5", c0 + 6, 5.5, f"VO{t}", "GND_STAR", "4.7u/630V MKP DC-link", fp=FP_FILM4U7, mpn="TDK B32674D6475K",
      note="C2 of the second stage (L2-C2 8.9 kHz); ESR 7.5 mohm; ripple current small (residue mV)")
    R(d, f"R{k}3", c0 + 6, 4, f"VO{t}", out, ("1.0" if k == 1 else "2.2") + " 5W fusible, pulse (ULW5)", rot=0, fp=FP_AX5W,
      mpn=f"TT Welwyn ULW5-{'1R0' if k == 1 else '2R2'}J (ordering suffix to confirm)",
      note="M20: a hard short or external arc puts 5.8-6.7 J into it in 0.2 ms; ULW5 short-pulse capacity ~19 J (1R0) / ~13 J (2R2), "
           "500 V isolation (ULW2: 2.5 J, 250 V)")
    R(d, f"R{k}4", c0 + 8, 5.5, out, f"BL{t}", "110k 2512 1W (500 V limiting)", fp=FP_R2512, mpn="Vishay CRCW2512 class (to confirm)",
      note="output bleeder, 0.36 W at 400 V; plate side (fourth pass: board area)")
    R(d, f"R{k}5", c0 + 8, 7, f"BL{t}", "GND_STAR", "110k 2512 1W (500 V limiting)", fp=FP_R2512, mpn="Vishay CRCW2512 class (to confirm)",
      note="output bleeder, 0.36 W at 400 V; plate side (fourth pass: board area)")


def bridge_extra(d, k, c0):
    """Parts added in the fourth pass (numbered after the third pass's, so no published reference moves)."""
    t = str(k)
    if k == 1:
        C(d, f"CF{k}", c0 + 4.8, 6.5, f"UC{t}", f"IC{t}", "4.7u/630V MKP DC-link", fp=FP_FILM4U7, mpn="TDK B32674D6475K",
          note="C1 film, returned through the I_C shunt with the electrolytic: 0.2-0.76 A rms at 40-150 kHz (sim/r2); "
               "ripple rating to confirm on the TDK datasheet (DC-link series, ESR 7.5 mohm)")
    else:
        # the screen bridge's C1 film is left out (board area): its electrolytic carries 0.32-0.39 A rms and the
        # residue at V_SCREEN is 5.6 mV p-p nominal / 11 mV at the cold-ESR corner (sim/r7); C215 stays unused
        d.skip("C")
    CP(d, f"CD{k}", c0 + 7, 6.5, f"VO{t}", f"CD{t}", "22u/500V 105C", fp=FP_EL22,
       note="damping leg of the second stage (with its ESR about 1.5 ohm in all); ripple small")
    R(d, f"RD{k}", c0 + 7, 8, f"CD{t}", "GND_STAR", "1.0 1W (damping leg)", fp=FP_AX1WV, mpn="")
    C(d, f"CSH{k}", c0 + 2.2, 3.5, f"UIN{t}", f"SW{t}", "220p/1kV C0G (snubber, high side)", fp=FP_C1206, mpn="",
      note="lossless ZVS snubber across the IGBT (sim/r1); at the device pins")
    C(d, f"CSL{k}", c0 + 2.2, 6.5, f"SW{t}", "PGND", "220p/1kV C0G (snubber, low side)", fp=FP_C1206, mpn="",
      note="lossless ZVS snubber across the IGBT, returned to PGND beside the shunt (keeps its charging current off the reading)")


def sheet02(d):
    d.text("02 Two half-bridge synchronous bucks in triangular-current mode (TCM, zero-voltage turn-on on both edges; "
           "f 40-150 kHz, both bridges at one frequency, interleaved; STATUS fourth pass). IKP08N65F5 on the chassis "
           "plate, 220 pF snubbers, 220 / 470 uH, C1 = 100 uF + 4.7 uF film through the I_C shunt, second stage 68 uH / "
           "4.7 uF film / 22 uF + 1.0 ohm leg. Sized for V_ANODE 0.7 A continuous / 0.8 A peaks, V_SCREEN 0.18 A "
           "(trips +-3.0 A). Outputs: V_ANODE (W04-a) and V_SCREEN (W05-a).", 0, -1.0, 2)
    bridge(d, 1, 0, "V_ANODE", "V_ANODE 0-400 V, 0.7 A continuous (about 401 V at 420 V raw, D_max 0.97)")
    bridge(d, 2, 11, "V_SCREEN", "V_SCREEN 0-~400 V, 0.18 A continuous / 0.25 A peak")
    # V_SCREEN <= V_ANODE in hardware. 1N5408 (IFSM 200 A): in a V_ANODE short or arc the screen capacitor
    # dumps through R212 (2.2 ohm) and this diode, ~180 A peak, tau 0.2 ms (S1M's 30 A was too small)
    d.part("D", "D1", 9, 9, {1: "V_ANODE", 2: "V_SCREEN"}, value="1N5408 (clamp: V_SCREEN <= V_ANODE + 0.7 V)",
           rot=0, fp="Diode_THT:D_DO-201AD_P5.08mm_Vertical_CathodeUp", mpn="1N5408")
    TAB(d, "J1", 3, 10, ["V_ANODE", "GND_STAR"], "V_ANODE / GND_PWR (W04-a, 4.8 mm tabs)")
    TAB(d, "J2", 14, 10, ["V_SCREEN"], "V_SCREEN (W05-a, 4.8 mm tab)")
    R(d, "R1", 6, 10, "V_ANODE", "LED_VA", "1M 2512 (500 V limiting)", fp=FP_R2512, mpn="", note="0.16 W at 400 V; plate side")
    d.part("LED", "D2", 7, 10.5, {2: "LED_VA", 1: "GND_STAR"}, value="red, 0.4 mA (V_ANODE PRESENT)", rot=90, mpn="")
    bridge_extra(d, 1, 0)
    bridge_extra(d, 2, 11)


# ------------------------------------------------------------------ sheet 03
def driver(d, k, c0):
    t = str(k)
    hi, lo = {1: ("PWM_H1", "PWM_L1"), 2: ("PWM_H2", "PWM_L2")}[k]
    d.text(f"Bridge {k}: UCC21520 (dual isolated driver: dead time + overlap block on DT, DIS = HV inhibit, 8 V UVLO)",
           c0, 0.3, 1.5)
    d.part("UCC21520DW", f"U{k}", c0 + 2, 3, {1: hi, 2: lo, 3: "+3V3", 8: "+3V3", 4: "GND", 5: "DRV_DIS", 6: f"DT{t}",
                                              7: "NC", 12: "NC", 13: "NC", 9: "PGND", 10: f"GLD{t}", 11: "+12V",
                                              14: f"SW{t}", 15: f"GHD{t}", 16: f"BOOT{t}"}, value="UCC21520DW")
    R(d, f"R{k}1", c0, 5.5, hi, "GND", "10k")
    R(d, f"R{k}2", c0 + 0.8, 5.5, lo, "GND", "10k")
    R(d, f"R{k}3", c0 + 1.6, 5.5, f"DT{t}", "GND", "20k (DT 200 ns floor)",
      note="hardware minimum dead time; the per-edge dead time (200-600 ns, TCM) comes from the FPGA's PWM timing")
    C(d, f"C{k}1", c0 + 2.4, 5.5, "+3V3", "GND", "100n")
    # bootstrap (ultrafast 600 V diode)
    d.part("D", f"D{k}1", c0 + 4.5, 1.5, {2: f"BS{t}", 1: f"BOOT{t}"}, value="ES1J (600 V ultrafast)", rot=0,
           fp="Diode_SMD:D_SMA", mpn="ES1J")
    R(d, f"R{k}4", c0 + 3.5, 1.5, "+12V", f"BS{t}", "2.2", rot=0)
    C(d, f"C{k}2", c0 + 5.5, 2.5, f"BOOT{t}", f"SW{t}", "1u/25V X7R", fp="Capacitor_SMD:C_0805_2012Metric")
    C(d, f"C{k}3", c0 + 6.3, 2.5, f"BOOT{t}", f"SW{t}", "100n")
    C(d, f"C{k}4", c0 + 5.5, 5, "+12V", "PGND", "10u/25V X7R", fp=FP_C1206)
    C(d, f"C{k}5", c0 + 6.3, 5, "+12V", "PGND", "100n")
    R(d, f"R{k}5", c0 + 4.5, 3.2, f"GHD{t}", f"GH{t}", "15", rot=0, fp="Resistor_SMD:R_0805_2012Metric")
    R(d, f"R{k}6", c0 + 5.5, 4.0, f"GH{t}", f"SW{t}", "10k")
    R(d, f"R{k}7", c0 + 4.5, 6.4, f"GLD{t}", f"GL{t}", "15", rot=0, fp="Resistor_SMD:R_0805_2012Metric")
    R(d, f"R{k}8", c0 + 5.5, 7.0, f"GL{t}", f"IS{t}", "10k")
    # the 1 nF gate-emitter capacitors of the third pass (C306 / C307 / C313 / C314) are removed: in TCM the off
    # device never sees a hard dv/dt (off-gate bump 0.01-0.05 V, sim/r1), and they cost 12 nC per edge of +12 V
    d.skip("C", 2)
    d.part("PWR_FLAG", f"#FLG30{2 * k - 1}", c0 + 7.2, 1.5, {1: f"BOOT{t}"}, value="PWR_FLAG")
    d.part("PWR_FLAG", f"#FLG30{2 * k}", c0 + 7.2, 3.5, {1: f"SW{t}"}, value="PWR_FLAG")


def sheet03(d):
    d.text("03 Gate drive: one UCC21520 per bridge: hardware dead time and shoot-through block, DIS from the "
           "HV_PERMIT / HV_ENABLE / fault logic (sheet 05), 10k gate-emitter resistors so the IGBTs stay off with the "
           "drivers unpowered, PWM inputs pulled down.", 0, -1.0, 2)
    driver(d, 1, 0)
    driver(d, 2, 9)
    d.text("High side from a bootstrap: in TCM the low side conducts every period (>= 1 us), so the bootstrap is refreshed "
           "every cycle (>= 10.8 V, sim/r1); 100 % duty holds 0.5-1 ms. +12 V: 4 x 22 nC x f + 6 mA = 10-19 mA at 40-150 kHz.", 0, 8.5)


# ------------------------------------------------------------------ sheet 04
# Fast loop channels (IF-2.2): one ADS7056 each, all sampled on CS_FAST; (source, net at the amplifier output,
# fast ADC input node, SDO net, AD7689 channel)
FAST_V = [("V_ANODE", "VM_A", "FA_VA", "SDO_VA", 0, 1), ("V_SCREEN", "VM_S", "FA_VS", "SDO_VS", 3, 2)]
FAST_I = [("IC1", "IM_C14", "FA_IC1", "SDO_IC1", 7), ("IS1", "IM_Q12", "FA_IL1", "SDO_IL1", 4),
          ("IC2", "IM_C24", "FA_IC2", "SDO_IC2", 6), ("IS2", "IM_Q22", "FA_IL2", "SDO_IL2", 5)]
SLOW_V = [("UIN", "VM_RAW", 1), ("UC1", "VM_UC1", 2)]


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


def fast_adc(d, ref, c, r, ain, sdo):
    d.part("ADS7056", ref, c, r, {1: "CS_FAST", 2: f"{sdo}_L", 3: "ADC_SCK", 4: "+3V3", 5: "GND", 6: "VREF",
                                  7: ain, 8: "GND"}, value="ADS7056 (14 bit, 2.5 MSPS)",
           note="X2QFN-8 1.5 x 1.5 mm (RUG): footprint to check against TI's RUG0008A land pattern")
    C(d, f"CA{ref}", c + 1, r + 1.2, "VREF", "GND", "1u X7R", fp="Capacitor_SMD:C_0603_1608Metric")
    C(d, f"CD{ref}", c + 1.8, r + 1.2, "+3V3", "GND", "100n")
    R(d, f"RS{ref}", c + 1.5, r - 0.6, f"{sdo}_L", sdo, "33", rot=0)


def sheet04(d):
    d.text("04 Measurement (IF-2.2, fourth pass): the loop's six channels on dedicated ADS7056 converters, sampled together on "
           "CS_FAST (timed by the control board's PWM generator: mid high-side conduction for V and I_C, mid low-side for I_Q), "
           "fast front ends (OPA2836, <= 50 ns), 3.0 V reference REF3030 as their AVDD; the AD7689 keeps all eight channels as "
           "slow monitors (external 3.0 V reference). Channel order IN0..7 = interfaces.md 9.", 0, -1.0, 2)
    # fast voltage channels: 3 x 1 Mohm + 12.4 kohm (1/242.9: 440 V -> 1.81 V, inside the OPA2836's 2.2 V input range at 3.3 V)
    for i, (src, buf, ain, sdo, ch, ua) in enumerate(FAST_V):
        c0 = i * 4
        R(d, f"R{i}1", c0, 1, src, f"DV{i}A", "1M 0.1% 1206", fp=FP_R1206, note="<= 167 V each at 500 V (1206: 200 V)")
        R(d, f"R{i}2", c0, 2.3, f"DV{i}A", f"DV{i}B", "1M 0.1% 1206", fp=FP_R1206, note="<= 167 V each at 500 V (1206: 200 V)")
        R(d, f"R{i}3", c0, 3.6, f"DV{i}B", f"DV{i}", "1M 0.1% 1206", fp=FP_R1206, note="<= 167 V each at 500 V (1206: 200 V)")
        R(d, f"R{i}4", c0 + 1, 3.6, f"DV{i}", "GND", "12.4k 0.1%")
        C(d, f"C{i}1", c0 + 1.8, 3.6, f"DV{i}", "GND", "100p C0G (tau 1.2 us)")
        opa2(d, "UF1" if i == 0 else "UF2", c0 + 1, 5.5, f"DV{i}", buf, buf)
        R(d, f"R{i}5", c0 + 2, 7.5, buf, f"ADC_IN{ch}", "100", rot=0)
        C(d, f"C{i}2", c0 + 2.6, 8.5, f"ADC_IN{ch}", "GND", "2.7n C0G")
        R(d, f"R{i}6", c0 + 3, 6.5, buf, ain, "33", rot=0)
        C(d, f"C{i}3", c0 + 3.6, 7.5, ain, "GND", "680p C0G (charge bucket, 22 ns)")
        fast_adc(d, f"UA{ua}", c0 + 2, 10.5, ain, sdo)
    # slow voltage channels (MCP6004 buffers, 1/201 as before)
    for i, (src, buf, ch) in enumerate(SLOW_V):
        c0 = 8 + i * 3
        R(d, f"RS{i}1", c0, 1, src, f"DS{i}A", "1M 0.1% 1206", fp=FP_R1206, note="<= 167 V each at 500 V (1206: 200 V)")
        R(d, f"RS{i}2", c0, 2.3, f"DS{i}A", f"DS{i}B", "1M 0.1% 1206", fp=FP_R1206, note="<= 167 V each at 500 V (1206: 200 V)")
        R(d, f"RS{i}3", c0, 3.6, f"DS{i}B", f"DS{i}", "1M 0.1% 1206", fp=FP_R1206, note="<= 167 V each at 500 V (1206: 200 V)")
        R(d, f"RS{i}4", c0 + 1, 3.6, f"DS{i}", "GND", "15k 0.1%")
        C(d, f"CS{i}1", c0 + 1.8, 3.6, f"DS{i}", "GND", "1n")
        opamp(d, "UB", c0 + 1, 5.5, f"DS{i}", buf, buf)
        R(d, f"RS{i}5", c0 + 2, 7.5, buf, f"ADC_IN{ch}", "100", rot=0)
        C(d, f"CS{i}2", c0 + 2.6, 8.5, f"ADC_IN{ch}", "GND", "2.7n C0G")
    # fast current channels: out = 1.5 V + 6.8 x V(shunt) = 1.5 V + 0.34 V/A (+-4.4 A into 0-3 V); 10k / 68k inputs
    # (a short's 11 V across the I_C shunt drives about 1 mA into the input clamps); no input filter capacitor:
    # the OPA2836 at a noise gain of 7.8 has about 15 MHz of bandwidth (tau ~10 ns), the charge bucket 22 ns
    amps = ["UF1", "UF2", "UF3", "UF3"]
    for i, (src, buf, ain, sdo, ch) in enumerate(FAST_I):
        c0 = 14 + i * 4
        # Kelvin taps (layout first pass): each sense leg is its own net from a net tie placed on the shunt's pad,
        # so the router can't join a sense resistor to the power copper anywhere but at the shunt
        R(d, f"RI{i}1", c0, 1, f"KS{i}P", f"IA{i}P", "10k 0.1%", rot=0)
        R(d, f"RI{i}2", c0 + 1, 2, f"IA{i}P", "IBIAS", "68k 0.1%")
        R(d, f"RI{i}3", c0, 3.4, f"KS{i}N", f"IA{i}N", "10k 0.1%", rot=0)
        d.part("NetTie_2", f"NT{2 * i + 1}", c0 + 2, 1, {1: src, 2: f"KS{i}P"}, value=f"Kelvin tap {src} (at the shunt)", mpn="")
        d.part("NetTie_2", f"NT{2 * i + 2}", c0 + 2, 3.4, {1: "PGND", 2: f"KS{i}N"}, value="Kelvin tap PGND (at the shunt)",
               mpn="")
        R(d, f"RI{i}4", c0 + 1, 4.4, f"IA{i}N", buf, "68k 0.1%", rot=0)
        opa2(d, amps[i], c0 + 1, 5.5, f"IA{i}P", f"IA{i}N", buf)
        R(d, f"RI{i}5", c0 + 2, 7.5, buf, f"ADC_IN{ch}", "100", rot=0)
        C(d, f"CI{i}2", c0 + 2.6, 8.5, f"ADC_IN{ch}", "GND", "2.7n C0G")
        R(d, f"RI{i}6", c0 + 3, 6.5, buf, ain, "33", rot=0)
        C(d, f"CI{i}3", c0 + 3.6, 7.5, ain, "GND", "680p C0G (charge bucket, 22 ns)")
        fast_adc(d, f"UA{3 + i}", c0 + 2, 10.5, ain, sdo)
    d.text("Current amplifiers: out = 1.5 V + 0.34 V/A (50 mOhm, gain 6.8, +-4.4 A full scale); forward (freewheeling) current in "
           "the low-side shunt and a discharging capacitor read below 1.5 V. Kelvin taps at the shunts (layout). The comparators "
           "(sheet 05) and the AD7689 take the same amplifier outputs through 100 ohm / 2.7 nF.", 14, 9.4)
    # 1.5 V bias from the 3.0 V reference
    R(d, "R1", 1, 13, "VREF", "IBIAS_D", "10k 0.1%")
    R(d, "R2", 1, 14.3, "IBIAS_D", "GND", "10k 0.1%")
    opamp(d, "UB", 3, 13.5, "IBIAS_D", "IBIAS", "IBIAS")
    C(d, "C1", 4, 14.5, "IBIAS", "GND", "1u")
    opamp(d, "UB", 5, 13.5, "GND", "UBSP0", "UBSP0")
    d.part("AD7689xCP", "U1", 10, 14, {1: "+3V3", 20: "+3V3", 2: "VREF", 3: "ADC_REFIN", 4: "GND", 5: "GND", 21: "GND",
                                       16: "ADC_IN0", 17: "ADC_IN1", 18: "ADC_IN2", 19: "ADC_IN3", 6: "ADC_IN4",
                                       7: "ADC_IN5", 8: "ADC_IN6", 9: "ADC_IN7", 10: "GND", 11: "ADC_CNV",
                                       12: "ADC_DIN", 13: "ADC_SCK", 14: "ADC_SDO_L", 15: "+3V3"}, value="AD7689BCPZ",
           note="CFG: external reference on REF (3.0 V from REF3030), internal buffer off; slow monitors only")
    C(d, "C2", 13, 13, "VREF", "GND", "10u X7R", fp="Capacitor_SMD:C_0805_2012Metric")
    C(d, "C3", 13.8, 13, "ADC_REFIN", "GND", "100n")
    C(d, "C4", 14.6, 13, "+3V3", "GND", "10u", fp="Capacitor_SMD:C_0805_2012Metric")
    C(d, "C5", 15.4, 13, "+3V3", "GND", "100n")
    R(d, "R3", 13, 15, "ADC_SDO_L", "ADC_SDO", "33", rot=0)
    R(d, "R4", 13, 16, "ADC_SCK", "ADC_SCK_RET", "33 (returned SCK, J1 pad 16)", rot=0,
      note="taken at the far end of the shared SCLK trace, past the six ADS7056 (layout)")
    R(d, "R5", 16, 16, "CS_FAST", "+3V3", "10k")
    # 3.0 V reference: AVDD of the ADS7056s (their reference), the AD7689's reference, the bias and the trip thresholds
    d.part("FerriteBead", "FB1", 18, 13, {1: "+3V3", 2: "+3V3_REF"}, value="600R@100MHz 0603",
           fp="Inductor_SMD:L_0603_1608Metric", mpn="", note="with C6: the reference's input filter (LDO-derived 3V3 from the link)")
    C(d, "C6", 19, 13.5, "+3V3_REF", "GND", "10u", fp="Capacitor_SMD:C_0805_2012Metric")
    d.part("REF3030", "U2", 20.5, 13, {1: "+3V3_REF", 2: "VREF", 3: "GND"}, value="REF3030 (3.0 V, 25 mA)",
           note="load about 3 mA typ (6 ADS7056 AVDD at 100-300 kSPS, ladders, bias, AD7689 REF), 9 mA worst at 2.5 MSPS")
    C(d, "C7", 22, 13.5, "VREF", "GND", "1u X7R", fp="Capacitor_SMD:C_0603_1608Metric")
    d.part("PWR_FLAG", "#FLG401", 18, 14.5, {1: "+3V3_REF"}, value="PWR_FLAG")
    d.text("SPI on J1 (IF-2.2): AD7689 ADC_DIN pad 11, ADC_SDO pad 12, ADC_CNV pad 13; shared SCLK ADC_SCK pad 14; CS_FAST pad 15; "
           "returned SCK pad 16; SDO_VS / SDO_IC2 / SDO_IL2 pads 1 / 3 / 5; SDO_VA / SDO_IC1 / SDO_IL1 pads 17 / 19 / 21.", 10, 17.0)


# ------------------------------------------------------------------ sheet 05
J1MAP = {k: "NC" for k in range(1, 41)}
J1MAP.update({1: "SDO_VS", 2: "GND", 3: "SDO_IC2", 4: "GND", 5: "SDO_IL2", 6: "GND", 15: "CS_FAST",
              17: "SDO_VA", 18: "GND", 19: "SDO_IC1", 20: "GND", 21: "SDO_IL1", 22: "GND",
              11: "ADC_DIN", 12: "ADC_SDO", 13: "ADC_CNV", 14: "ADC_SCK", 16: "ADC_SCK_RET", 25: "HV_FAULT_N",
              29: "PWM_L1", 30: "PWM_L2", 31: "PWM_H1", 32: "PWM_H2", 33: "GND", 34: "GND", 35: "+3V3", 36: "+3V3",
              37: "HV_PERMIT_STAT", 38: "HV_ENABLE", 39: "+12V", 40: "+12V"})


def sheet05(d):
    d.text("05 J1 (W17-b, IF-2, 2x20 1.27 mm, standard numbering; interfaces.md 9), HV_PERMIT current loop (W16-b), "
           "driver enable logic, latched hardware protection (forward and reverse over-current per bridge, raw / "
           "V_ANODE / V_SCREEN over-voltage). Drivers run only when HV_PERMIT loop on AND HV_ENABLE high AND no "
           "latched fault. IF-2: never with the v2.5 control card (pad 25 contention).", 0, -1.0, 2)
    d.part("Conn_02x20_Odd_Even", "=J1", 0, 3, J1MAP, value="CONTROL 40-pin IF-2.2 (W17-b, isolated on the control board)",
           mpn="Samtec SHF-120-01-L-D-TH", note="1.27 mm 2x20 shrouded THT header (5.33 mm body, 1.91 mm tail); "
           "stock pin-header footprint, the shroud outline to add at layout; silkscreen IF-2")
    for i, n in enumerate(("+3V3", "+12V", "GND")):
        d.part("PWR_FLAG", f"#FLG50{i}", 2, 8 + i * 0.6, {1: n}, value="PWR_FLAG")
    C(d, "C1", 3, 7, "+3V3", "GND", "10u", fp="Capacitor_SMD:C_0805_2012Metric")
    C(d, "C2", 3.8, 7, "+12V", "GND", "10u/25V", fp=FP_C1206)
    d.part("NetTie_2", "NT1", 3, 9, {1: "GND", 2: "PGND"}, value="GND to PGND at the shunts (Kelvin)", mpn="")
    R(d, "R1", 5, 7, "HV_ENABLE", "GND", "100k")
    # HV_PERMIT loop input: TVS, threshold resistor, reverse diode, optocoupler
    d.part("Conn_01x02", "J2", 5, 1, {1: "HVP_P", 2: "HVP_N"}, value="HV_PERMIT +/- (W16-b, Lock-2.54, twisted pair)",
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
    # fault latch (fourth pass, with the control board's watchdogged HV_ENABLE): SET by any comparator and by
    # HV_ENABLE low (U508 open drain on FAULT_N; also the power-on set, HV_ENABLE being pulled down); CLEARED only by
    # a rising HV_ENABLE that follows at least about 6 ms of HV_ENABLE low (LL_RC / U509), and only if no comparator
    # is active (set dominates). The clock is HV_ENABLE delayed 10 us (U511), so FAULT_N has risen (10k / 100p: 1 us)
    # before the edge. A heartbeat drop-out shorter than about 4 ms latches and stays latched.
    R(d, "R6", 5, 4, "+3V3", "FAULT_N", "10k")
    C(d, "C5", 6, 4.5, "FAULT_N", "GND", "100p")
    d.part("74AUP1G74", "U3", 8, 4.5, {1: "ENA_DLY", 2: "D_LATCH", 3: "HV_FAULT_N", 4: "GND", 5: "FLT_Q",
                                       6: "+3V3", 7: "FAULT_N", 8: "+3V3"}, value="74AUP1G74")
    C(d, "C6", 10, 5.5, "+3V3", "GND", "100n")
    d.part("74LVC1G10", "U4", 13, 4.5, {1: "HV_PERMIT_STAT", 3: "HV_ENABLE", 6: "HV_FAULT_N", 4: "DRV_DIS", 2: "GND",
                                        5: "+3V3"}, value="74LVC1G10 (DIS = NAND)")
    R(d, "R7", 15, 4.5, "DRV_DIS", "+3V3", "10k")
    C(d, "C7", 15.8, 5.5, "+3V3", "GND", "100n")
    d.skip("R")   # R508 (LM4040 feed) removed: VREF is the REF3030 on sheet 04
    d.skip("D")   # D503 (LM4040) removed
    d.skip("C")   # C508 removed with it
    # thresholds from the 3.0 V reference (VREF, REF3030 on sheet 04): top / bottom resistor, threshold
    th = [("TH_OC", "10.5k", "2k", "0.480 V = 3.0 A forward (low side) / 3.0 A discharge (I_C)"),
          ("TH_OCR", "2k", "10.5k", "2.520 V = 3.0 A reverse / shoot-through"),
          ("TH_OVR", "2.7k", "10k", "2.362 V = 475 V raw (1/201)"),
          ("TH_OVA", "6.65k", "10k", "1.802 V = 438 V V_ANODE (1/242.9)"),
          ("TH_OVS", "7.32k", "10k", "1.732 V = 421 V V_SCREEN (1/242.9)")]
    for i, (n, top, bot, what) in enumerate(th):
        R(d, f"R1{i}", 3 + i * 1.6, 11, "VREF", n, top + " 0.1%")
        R(d, f"R2{i}", 3 + i * 1.6, 12.3, n, "GND", bot + " 0.1%")
        d.text(f"{n}: {what}", 3 + i * 1.6, 13.3, 1.0)
    d.text("Over-voltage thresholds against the dividers (sheet 04: raw 1/201, outputs 1/242.9); current thresholds against "
           "1.5 V +- 0.34 V/A. Comparator path: amplifier ~10 ns + 100 ohm / 2.7 nF 0.27 us + LMV339 + latch + DIS: about 1 us. "
           "The raw trip ends a ramp too fast for the PSU (interfaces.md 8): latched, no brake, no clamp.", 3, 13.8, 1.0)
    # comparators: open drain, wired-OR into FAULT_N (latched); output low when + < -
    comp(d, "UC1", 12, 8, "IM_Q12", "TH_OC", "FAULT_N")       # bridge 1 forward over-current (reading below TH_OC)
    comp(d, "UC1", 12, 10, "IM_Q22", "TH_OC", "FAULT_N")      # bridge 2 forward
    comp(d, "UC1", 15, 8, "TH_OCR", "IM_Q12", "FAULT_N")      # bridge 1 reverse / shoot-through (reading above TH_OCR)
    comp(d, "UC1", 15, 10, "TH_OCR", "IM_Q22", "FAULT_N")     # bridge 2 reverse
    comp(d, "UC2", 18, 8, "TH_OVR", "VM_RAW", "FAULT_N")      # raw over-voltage (475 V)
    comp(d, "UC2", 18, 10, "TH_OVA", "VM_A", "FAULT_N")       # V_ANODE over-voltage
    comp(d, "UC2", 21, 8, "TH_OVS", "VM_S", "FAULT_N")        # V_SCREEN over-voltage
    # output short / arc: the electrolytic discharging faster than 2.0 A (I_C reading below TH_OC); the low-side
    # forward trip only sees the current during (1 - D) of each period and is blind near full duty (sim/m20_short_arc.py)
    comp(d, "UC2", 21, 10, "IM_C14", "TH_OC", "FAULT_N")      # bridge 1 capacitor discharge (short / arc)
    comp(d, "UC3", 24, 8, "IM_C24", "TH_OC", "FAULT_N")       # bridge 2 capacitor discharge (short / arc)
    comp(d, "UC3", 24, 10, "GND", "+3V3", "NC")               # spare
    comp(d, "UC3", 27, 8, "GND", "+3V3", "NC")                # spare
    comp(d, "UC3", 27, 10, "GND", "+3V3", "NC")               # spare
    C(d, "C11", 13.6, 12.5, "+3V3", "GND", "100n")
    # latch qualification parts (fourth pass)
    d.part("74LVC1G07", "U5", 5, 15.5, {1: "NC", 2: "HV_ENABLE", 3: "GND", 4: "FAULT_N", 5: "+3V3"},
           value="74LVC1G07 (HV_ENABLE low sets the latch)")
    R(d, "R30", 7, 15.5, "HV_ENABLE", "LL_RC", "100k")
    R(d, "R31", 7, 17, "HV_ENABLE", "LL_D", "1k")
    d.part("D", "D4", 8, 17, {2: "LL_D", 1: "LL_RC"}, value="1N4148W (fast recharge)", rot=0, mpn="1N4148W")
    C(d, "C12", 9, 16, "LL_RC", "GND", "47n X7R (tau 4.7 ms)")
    d.part("74LVC1G17", "U6", 10.5, 15.5, {1: "NC", 2: "LL_RC", 3: "GND", 4: "LL_N", 5: "+3V3"},
           value="74LVC1G17 (LL_N low = HV_ENABLE was low > ~6 ms)")
    d.part("74LVC1G08", "U7", 12.5, 15.5, {1: "FLT_Q", 2: "LL_N", 3: "GND", 4: "D_LATCH", 5: "+3V3"},
           value="74LVC1G08 (D = Q AND NOT long-low)")
    R(d, "R32", 14, 15.5, "HV_ENABLE", "ENA_RC", "10k")
    C(d, "C13", 15, 16.5, "ENA_RC", "GND", "1n C0G (10 us)")
    d.part("74LVC1G17", "U8", 16.5, 15.5, {1: "NC", 2: "ENA_RC", 3: "GND", 4: "ENA_DLY", 5: "+3V3"},
           value="74LVC1G17 (clock = HV_ENABLE delayed 10 us)")
    for i, c in enumerate((18, 18.8, 19.6, 20.4)):
        C(d, f"C1{4 + i}", c, 16.5, "+3V3", "GND", "100n")
    d.text("Fault latch rule (IF-2.2): HV_ENABLE low stops the drivers at once (U504) and sets the latch; the latch clears only "
           "on a rising HV_ENABLE after >= 20 ms low (guaranteed; < 4 ms never clears) with no comparator active. Firmware: "
           "to clear, hold the heartbeat off for >= 20 ms, then restart.", 5, 18.5, 1.0)
    C(d, "C9", 12, 12.5, "+3V3", "GND", "100n")
    C(d, "C10", 12.8, 12.5, "+3V3", "GND", "100n")


SHEETS = [("01_input_star.kicad_sch", sheet01), ("02_bridges.kicad_sch", sheet02),
          ("03_gate_drive.kicad_sch", sheet03), ("04_measurement.kicad_sch", sheet04),
          ("05_interface_protection.kicad_sch", sheet05)]


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
    for f, fn in SHEETS:
        d = Drawer(f, "collect")
        fn(d)
        bom += d.bom
        for n in d.nets:
            seen.setdefault(n, set()).add(f)
    lines = write_maps(bom)
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
