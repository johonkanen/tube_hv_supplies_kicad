#!/usr/bin/env python3
"""HV supplies rev 4, layout: the placed board (outline, holes, every part, net classes and rules, keep-outs,
notes) from the schematic netlist (rev3/tools/make_pcb.py adapted; its helpers are reused unchanged).

    tools/p2k/bin/kipy rev4/tools/make_pcb.py [OUT.kicad_pcb]      (default rev4/build/layout/00_placed.kicad_pcb)

Frame: every position below is in the chassis frame (D748 top plate, mm: x from the left along the front, y from
the front panel's inner face to the rear). KiCad x = chassis x - 525, KiCad y = chassis y - 30 (as rev3). The board
hangs below the plate: KiCad's F side faces DOWN (through-hole parts, TO-220s, films, tabs, J1); B faces the plate
(SMD). Seen in KiCad you look at the board from below, front panel at the top, x to the right = chassis x.
Board x 562-677, y 39-127 (PLAN D10, mechanical/floorplan.py). TO-220 leads at x 674.5: tab face 677.65, a 0.3 mm
insulating pad to the east wall's inner face at 678 (assumed, PLAN O1).

Placement: PADS (two pads of a part on two chassis points; side mirror and rotation follow), AT (footprint origin
and rotation), GROUPS (small SMD packed by connectivity into zones, nearest free spot to the pads they share a
signal net with).
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pcbnew

R4 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R3 = R4                                   # name used by the reused helpers (load_fp)
ROOT = os.path.dirname(R4)
PROJECT = "tube_hv_supplies_rev4"
K = os.path.join(R4, "kicad")
PRO = os.path.join(K, PROJECT + ".kicad_pro")
SCH = os.path.join(K, PROJECT + ".kicad_sch")
KICAD_CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
STOCK = os.path.join(os.environ.get("KICAD_MOUNT") or open(f"/tmp/p2k_kicad_mount.{os.getuid()}").read().strip(),
                     "share", "kicad", "footprints")
OUT = os.path.join(R4, "build", "layout", "00_placed.kicad_pcb")
OX, OY = 525.0, 30.0                     # chassis -> KiCad offset

# ---------------------------------------------------------------- outline and holes (chassis mm)
BX0, BY0, BX1, BY1 = 562.0, 39.0, 677.0, 127.0
OUTLINE = [(BX0, BY0), (BX1, BY0), (BX1, BY1), (BX0, BY1)]
# H101 plated: the chassis bond of the fault / RF network (D102 || C106 || R106), next to it. The east edge is
# held by the four TO-220s screwed to the wall; H104 takes the B_P / B_N tab insertion force.
HOLES = {"H101": (630.5, 113.5), "H102": (566.0, 43.0), "H103": (566.0, 123.0), "H104": (668.0, 42.5)}
TAB_SCREWS = []
# cable ties of the standing toroids: through the slots, along the plate face between them (no B parts there)
TIE_BANDS = [(633.5, 107.3, 656.5, 111.3), (633.5, 72.3, 656.5, 76.3)]
RESERVED = [("B", b) for b in TIE_BANDS]
WALL_X = 678.0
TO_X = 674.5                              # TO-220 lead row

# ---------------------------------------------------------------- placement (chassis mm)
PADS = {
    # bridge devices on the east edge, tabs east (rotation 270 puts the TO-220's tab side at +x): front to rear
    # QL2 (Q204), QH2 (Q203), QH1 (Q201), QL1 (Q202); pins G, C, E from front to rear
    "Q204": ("F", {"1": (TO_X, 49.46), "3": (TO_X, 54.54)}),
    "Q203": ("F", {"1": (TO_X, 63.46), "3": (TO_X, 68.54)}),
    "Q201": ("F", {"1": (TO_X, 97.46), "3": (TO_X, 102.54)}),
    "Q202": ("F", {"1": (TO_X, 111.46), "3": (TO_X, 116.54)}),
    # interface tabs and headers
    "J101": ("F", {"1": (660.0, 45.0), "2": (648.0, 45.0)}),       # B_P east, B_N west (W01 from the PSU hole)
    "J102": ("F", {"1": (595.0, 45.0), "2": (607.0, 45.0)}),       # RAW_SS1 / GND_PRE1 (W02)
    "J103": ("F", {"1": (573.5, 45.0), "2": (585.5, 45.0)}),       # RAW_SS2 / GND_PRE2 (W03)
    "J201": ("F", {"1": (588.0, 121.0), "2": (576.0, 121.0)}),     # V_ANODE / GND_PWR (W04)
    "J1": ("F", {"1": (566.37, 108.86), "40": (565.10, 84.73)}),   # facing the control board's J11
    "J501": ("F", {"1": (566.5, 57.5), "2": (566.5, 60.04)}),
    # input: B_P bulk, input inductor, UIN bulk between the high-side collectors, UIN film
    "C101": ("F", {"1": (627.25, 47.5), "2": (634.75, 47.5)}),
    "C102": ("F", {"1": (660.25, 66.0), "2": (667.75, 66.0)}),
    "L101": ("F", {"1": (656.0, 53.8), "2": (661.0, 53.8)}),
    "C104": ("F", {"1": (660.25, 84.0), "2": (667.75, 84.0)}),
    "C105": ("F", {"1": (661.75, 95.5), "2": (661.75, 118.0)}),
    "R103": ("F", {"1": (612.0, 43.5), "2": (612.0, 51.12)}),     # UIN bleeder, front strip
    "R104": ("F", {"1": (619.0, 51.12), "2": (619.0, 43.5)}),
    # main inductors standing on edge (32 mm along y)
    "L201": ("F", {"1": (645.0, 117.5), "2": (645.0, 101.1)}),
    "L203": ("F", {"1": (645.0, 82.5), "2": (645.0, 66.1)}),
    # first stage 47 uF, damping legs
    "C202": ("F", {"1": (609.25, 108.5), "2": (616.75, 108.5)}),
    "C207": ("F", {"1": (609.25, 75.0), "2": (616.75, 75.0)}),
    "C205": ("F", {"1": (625.5, 96.0), "2": (630.5, 96.0)}),
    "C210": ("F", {"1": (625.5, 64.0), "2": (630.5, 64.0)}),
    "R203": ("F", {"1": (624.5, 105.5), "2": (624.5, 113.12)}),
    "R208": ("F", {"1": (608.0, 61.0), "2": (615.62, 61.0)}),
    # films in the west column (pin 1 east)
    "C209": ("F", {"1": (600.75, 59.5), "2": (573.25, 59.5)}),
    "C208": ("F", {"1": (600.75, 75.5), "2": (573.25, 75.5)}),
    "C203": ("F", {"1": (600.75, 87.5), "2": (573.25, 87.5)}),
    "C204": ("F", {"1": (600.75, 104.5), "2": (573.25, 104.5)}),
    # fault / RF network to H101
    "D102": ("F", {"1": (613.5, 86.5), "4": (628.74, 86.5)}),
    "R106": ("F", {"1": (608.0, 95.0), "2": (615.62, 95.0)}),
    "C106": ("F", {"1": (608.5, 122.0), "2": (631.0, 122.0)}),
}
AT = {
    "J202": ("F", 600.0, 121.0, 90),
    # second-stage 100 uH (SMD, plate side) between the toroids, pad 1 (UC) toward the toroid's UC pad
    "L202": ("B", 643.0, 93.0, 90), "L204": ("B", 642.5, 57.5, 90),
    "NT101": ("B", 624.0, 57.0, 0),
    # RAW_SS links (0 ohm 2512, interfaces.md 4.2), plate side next to their tabs
    "R101": ("B", 597.0, 52.0, 0), "R102": ("B", 579.0, 52.0, 0),
}
KELVIN = {}
for _r, (_x, _y) in HOLES.items():
    AT[_r] = ("F", _x, _y, 0)


def _refs(prefix, nums):
    return [f"{prefix}{n}" for n in nums]


# packed groups: name -> (zones [(side, x0, y0, x1, y1)], refs). ICs first: their passives follow them.
GROUPS = {}
EAST_R = [("B", 650.0, 99.5, 672.6, 126.5), ("B", 636.5, 111.5, 650.0, 126.5)]
EAST_F = [("B", 650.0, 39.5, 672.6, 76.0), ("B", 636.5, 39.5, 650.0, 50.0), ("B", 636.5, 64.5, 650.0, 72.2)]
EAST_M = [("B", 650.0, 76.0, 672.6, 99.5), ("B", 636.5, 76.4, 650.0, 85.0)]
GROUPS["boost"] = (EAST_M, ["U305", "L301", "D303", "C317", "C319", "C318", "R319", "R320", "NT501"])
GROUPS["drv1"] = (EAST_R + EAST_M, ["U301", "U302", "C201", "R201", "R202", "U401", "R303", "R304", "R305", "C304", "D301",
                                     "C302", "C303", "R302", "C301", "R301", "R307", "R308", "R309", "C308", "C305",
                                     "R306", "C306", "C307", "NT401", "NT402", "NT403", "NT404", "R401", "R402",
                                     "R403", "R404", "R406", "R407", "R408", "R409", "C401", "C402", "C405", "C406",
                                     "C403"])
GROUPS["drv2"] = (EAST_F + EAST_M + EAST_R, ["U303", "U304", "C206", "C103", "R206", "R207", "U402", "R312", "R313", "R314", "C312", "D302",
                                     "C310", "C311", "R311", "C309", "R310", "R316", "R317", "R318", "C316", "C313",
                                     "R315", "C314", "C315", "NT405", "NT406", "NT407", "NT408", "R411",
                                     "R412", "R413", "R414", "R416", "R417", "R418", "R419", "C408", "C409", "C412",
                                     "C413", "C410"])
MEAS = [("B", 576.5, 56.5, 598.0, 116.5), ("B", 562.5, 62.5, 576.0, 80.5), ("B", 567.0, 80.5, 576.5, 116.5),
        ("B", 603.0, 66.0, 636.0, 72.0), ("B", 603.0, 77.0, 621.0, 101.0),
        ("B", 621.0, 72.0, 636.0, 101.0)]
GROUPS["meas"] = (MEAS, ["U408", "U409", "U411", "U407", "U410", "U412", "U403", "U404", "U405", "U406",
                         "R454", "C429", "R456", "C433", "C430", "C434", "C431", "C432", "C435", "R455", "R457",
                         "R458", "R459", "R460", "R461", "R462", "R463", "FB401", "C436", "C437", "C427", "C428",
                         "R405", "C404", "R410", "C407", "R415", "C411", "R420", "C414",
                         "R421", "R422", "R423", "R424", "C415", "R425", "R426", "R427", "R428", "R429", "C417", "R430",
                         "R431", "R432", "R433", "R434", "C418", "R435", "R436", "R437", "R438", "R439", "C420", "R440",
                         "R441", "R442", "R443", "R444", "C421", "R445", "R446", "R447", "R448", "R449", "C423", "R450",
                         "C416", "C419", "C422", "R451", "R452", "C424", "R453", "C426", "C425"])
GROUPS["iface"] = ([("B", 562.5, 47.0, 573.0, 80.5), ("B", 562.5, 112.5, 576.0, 118.0)] + MEAS,
                   ["U501", "U502", "D501", "D502", "R501", "R502", "R503", "R504", "R505", "C501", "C502", "C503",
                    "C504"])
GROUPS["bleed"] = ([("B", 603.0, 98.0, 636.0, 126.5), ("B", 603.0, 46.0, 636.0, 66.0)],
                   ["R204", "R205", "R209", "R210"])
GROUPS["lamp"] = ([("F", 640.0, 39.5, 646.0, 57.0), ("F", 621.5, 70.5, 636.0, 89.0)], ["R105", "D101"])

# ---------------------------------------------------------------- net classes and rules
HV_RAW = ["B_P", "UIN", "RAW_SS1", "RAW_SS2"]                       # one potential (links, L101)
HV_SW1 = ["SW1", "GH1", "GHON1", "GHOFF1", "BOOT1"]                # switch node + its floating driver
HV_SW2 = ["SW2", "GH2", "GHON2", "GHOFF2", "BOOT2"]
HV_SW = HV_SW1 + HV_SW2
HV_OUT = ["UC1", "UC2", "V_ANODE", "V_SCREEN"]
HV_MID = ["BLD1", "BL1", "BL2", "DV01", "DV02", "DV11", "DV12", "DV21", "DV22", "DV31", "DV32", "DV41", "DV42",
          "DV51", "DV52"]                                          # <= 300 V to anything
PWR = ["PGND", "GND_STAR", "IS1", "IS2", "IC1", "IC2", "CD1", "CD2"]
KELVIN_NETS = ["KS0P", "KS0N", "KS1P", "KS1N", "KS2P", "KS2N", "KS3P", "KS3N"]
CHASSIS = ["CHASSIS", "BR_DC"]
SUPPLY = ["+12V", "+3V3", "GND", "+3V3_REF", "VREF", "VDRV"]
HV_ALL = HV_RAW + HV_SW + HV_OUT
DIVIDERS = ["R421", "R422", "R423", "R426", "R427", "R428", "R431", "R432", "R433", "R436", "R437", "R438",
            "R441", "R442", "R443", "R446", "R447", "R448"]
# parts whose own pad spacing is below 2.5 mm between HV nets (IPC-2221B A6, component terminations, 301-500 V: 0.8 mm)
A6_PARTS = ["Q201", "Q202", "Q203", "Q204", "D301", "D302", "U301", "U303", "R105"] + DIVIDERS
TO220 = ["Q201", "Q202", "Q203", "Q204"]


def _or(fmt, items):
    return " || ".join(fmt.format(i) for i in items)


def dru():
    hv = _or("A.NetClass == '{}'", ["HV_RAW", "HV_SW1", "HV_SW2", "HV_OUT"])
    hvb = _or("B.NetClass == '{}'", ["HV_RAW", "HV_SW1", "HV_SW2", "HV_OUT"])
    a6 = _or("(A.memberOfFootprint('{0}') && B.memberOfFootprint('{0}'))", A6_PARTS)
    pf = _or("(A.intersectsArea('PF_{0}') && B.intersectsArea('PF_{0}'))", TO220)
    pfe = _or("A.memberOfFootprint('{0}')", TO220)
    tops = " || ".join(f"(A.NetName == '*{s}' && B.NetName == '*/DV{i}1')" for i, s in
                       enumerate(["V_ANODE", "UC1", "V_SCREEN", "UC2", "B_P", "UIN"]))
    return f"""(version 1)
# HV supplies rev 4 rules (rev4/tools/make_pcb.py; from rev3's).
# Clearance basis: IPC-2221B table 6-1, external conductors, uncoated, sea level to 3050 m (B2):
#   301-500 V 2.5 mm, 151-300 V 1.25 mm; component leads / terminations uncoated (A6): 301-500 V 0.8 mm.
# Creepage check basis: IEC 60664-1 functional insulation, pollution degree 2, material group IIIa (FR-4,
#   CTI >= 175): 500 V working -> 2.5 mm, 250 V -> 1.25 mm; the clearance rules give the same surface distance.
# Working voltages: raw rail <= 450 V (HV_RAW), switch nodes 0-450 V with their floating gate drive (HV_SW1 /
#   HV_SW2), outputs and first-stage nodes 0-430 V (HV_OUT). No hardware trips (PLAN D2).
# 4 layers, 0.2 / 0.2 mm, 0.6 / 0.3 mm vias.

(rule "HV to anything (B2, 301-500 V)"
  (condition "({hv}) && A.NetName != B.NetName")
  (constraint clearance (min 2.5mm)))

(rule "HV mid nodes (B2, 151-300 V)"
  (condition "A.NetClass == 'HV_MID' && A.NetName != B.NetName")
  (constraint clearance (min 1.25mm)))

(rule "divider tops: the top resistor's two ends (<= 175 V apart, B2 151-300 V)"
  (condition "{tops}")
  (constraint clearance (min 1.25mm)))

(rule "HV to board edge"
  (condition "{hv}")
  (constraint edge_clearance (min 2.5mm)))

(rule "HV to the standoff holes (metal standoff r 3 mm + 2.5 mm)"
  (condition "({hv}) && B.memberOfFootprint('H10*')")
  (constraint hole_clearance (min 4.0mm)))

(rule "chassis net to anything (fault path)"
  (condition "A.NetClass == 'CHASSIS' && A.NetName != B.NetName")
  (constraint clearance (min 1.0mm)))

# exceptions, last so they win
(rule "TO-220 leads at the east edge: the air gap that matters is pad to the wall (>= 2.5 mm), not to the edge"
  (condition "{pfe}")
  (constraint edge_clearance (min 1.0mm)))

(rule "terminations inside one part (IPC A6, 0.8 mm)"
  (condition "A.Type == 'Pad' && B.Type == 'Pad' && ({a6}) && ({hv} || {hvb})")
  (constraint clearance (min 0.8mm)))

(rule "TO-220 pin fields (IPC A6: copper at the 2.54 mm lead row)"
  (condition "({pf}) && ({hv} || {hvb})")
  (constraint clearance (min 0.8mm)))

(rule "raw rail among itself (same potential through links / L101)"
  (condition "A.NetClass == 'HV_RAW' && B.NetClass == 'HV_RAW'")
  (constraint clearance (min 0.5mm)))

(rule "bridge 1 floating driver domain (SW1 + 15 V)"
  (condition "A.NetClass == 'HV_SW1' && B.NetClass == 'HV_SW1'")
  (constraint clearance (min 0.25mm)))

(rule "bridge 2 floating driver domain (SW2 + 15 V)"
  (condition "A.NetClass == 'HV_SW2' && B.NetClass == 'HV_SW2'")
  (constraint clearance (min 0.25mm)))
"""


def project_settings():
    pro = json.load(open(PRO))

    def cls(name, clr, tw, color, prio):
        return {"name": name, "clearance": clr, "track_width": tw, "via_diameter": 0.8 if tw >= 0.5 else 0.6,
                "via_drill": 0.4 if tw >= 0.5 else 0.3, "pcb_color": color,
                "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": prio}
    classes = [cls("Default", 0.15, 0.25, "rgba(0, 0, 0, 0.000)", 2147483647),
               cls("HV_RAW", 2.5, 1.0, "rgba(220, 0, 0, 1.000)", 0),
               cls("HV_SW1", 2.5, 1.0, "rgba(255, 120, 0, 1.000)", 1),
               cls("HV_SW2", 2.5, 1.0, "rgba(255, 160, 0, 1.000)", 1),
               cls("HV_OUT", 2.5, 1.0, "rgba(200, 0, 160, 1.000)", 2),
               cls("HV_MID", 1.25, 0.4, "rgba(160, 80, 0, 1.000)", 3),
               cls("PWR", 0.25, 1.0, "rgba(0, 120, 200, 1.000)", 4),
               cls("KELVIN", 0.15, 0.25, "rgba(0, 180, 180, 1.000)", 5),
               cls("CHASSIS", 1.0, 1.0, "rgba(0, 160, 0, 1.000)", 6),
               cls("SUPPLY", 0.15, 0.4, "rgba(120, 120, 0, 1.000)", 7)]
    pats = []
    for c, names in (("HV_RAW", HV_RAW), ("HV_SW1", HV_SW1), ("HV_SW2", HV_SW2), ("HV_OUT", HV_OUT),
                     ("HV_MID", HV_MID), ("PWR", PWR), ("KELVIN", KELVIN_NETS), ("CHASSIS", CHASSIS),
                     ("SUPPLY", SUPPLY)):
        for n in names:
            pats += [{"netclass": c, "pattern": n}, {"netclass": c, "pattern": "*/" + n}]
    pro["net_settings"] = {"classes": classes, "meta": {"version": 4}, "net_colors": None,
                           "netclass_assignments": None, "netclass_patterns": pats}
    pro.setdefault("board", {})
    pro["board"]["design_settings"] = {
        "rules": {"min_clearance": 0.15, "min_track_width": 0.2, "min_connection": 0.2, "min_via_diameter": 0.6,
                  "min_via_annular_width": 0.15, "min_through_hole_diameter": 0.3, "min_hole_to_hole": 0.25,
                  "min_hole_clearance": 0.25, "min_copper_edge_clearance": 0.5, "min_silk_clearance": 0.0,
                  "min_text_height": 0.8, "min_text_thickness": 0.12, "solder_mask_to_copper_clearance": 0.0},
        "drc_exclusions": []}
    json.dump(pro, open(PRO, "w"), indent=2)
    open(os.path.join(K, PROJECT + ".kicad_dru"), "w").write(dru())


# ---------------------------------------------------------------- helpers
def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    """chassis mm -> KiCad point"""
    return pcbnew.VECTOR2I(mm(x - OX), mm(y - OY))


def T(v):
    return pcbnew.ToMM(v)


def cpos(p):
    """KiCad point -> chassis mm"""
    return T(p.x) + OX, T(p.y) + OY


def netlist():
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "n.xml")
        subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", out, SCH],
                       check=True, capture_output=True)
        return ET.parse(out)


def load_fp(lib_id):
    lib, name = lib_id.split(":")
    path = os.path.join(R3, "lib", PROJECT + ".pretty") if lib == PROJECT else os.path.join(STOCK, lib + ".pretty")
    f = pcbnew.FootprintLoad(path, name)
    if f is None:
        raise SystemExit(f"footprint {lib_id} not found in {path}")
    f.SetFPID(pcbnew.LIB_ID(lib, name))
    return f


def pad_pos(f, num):
    return [cpos(p.GetPosition()) for p in f.Pads() if p.GetNumber() == num]


def pad_centre(f, num):
    ps = pad_pos(f, num)
    return sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)


def set_side(f, side):
    if (side == "B") != f.IsFlipped():
        f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)


def place_at(f, side, x, y, rot):
    set_side(f, side)
    f.SetOrientationDegrees(rot)
    f.SetPosition(pt(x, y))


def place_pads(f, side, targets):
    (n1, (x1, y1)), (n2, (x2, y2)) = list(targets.items())
    set_side(f, side)
    want = math.atan2(y2 - y1, x2 - x1)
    best = None
    for rot in (0, 90, 180, 270):
        f.SetOrientationDegrees(rot)
        f.SetPosition(pt(OX, OY))
        a, b = pad_centre(f, n1), pad_centre(f, n2)
        got = math.atan2(b[1] - a[1], b[0] - a[0])
        err = abs(math.remainder(got - want, 2 * math.pi))
        if best is None or err < best[0]:
            best = (err, rot)
    f.SetOrientationDegrees(best[1])
    f.SetPosition(pt(OX, OY))
    a, b = pad_centre(f, n1), pad_centre(f, n2)
    f.SetPosition(pt(OX + x1 - a[0], OY + y1 - a[1]))
    d = math.hypot(b[0] - a[0], b[1] - a[1]) - math.hypot(x2 - x1, y2 - y1)
    if best[0] > 0.01 or abs(d) > 0.05:
        raise SystemExit(f"{f.GetReference()}: pads {n1}/{n2} can't land on the targets (angle {best[0]:.3f}, d {d:.2f})")


def courtyard_box(f, side):
    lay = pcbnew.B_CrtYd if side == "B" else pcbnew.F_CrtYd
    c = f.GetCourtyard(lay)
    if c.OutlineCount() == 0:
        bb = f.GetBoundingBox(False)
    else:
        bb = c.BBox()
    x0, y0 = cpos(pcbnew.VECTOR2I(bb.GetLeft(), bb.GetTop()))
    x1, y1 = cpos(pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()))
    return x0, y0, x1, y1


# ---------------------------------------------------------------- packing of small SMD groups
def short_net(n):
    return n.rsplit("/", 1)[-1]


def net_req(a, b):
    """Required clearance (mm, with margin) between two nets for the packer (mirrors the DRC rules)."""
    if not a or not b:
        return 0.3
    if a == b:
        return 0.0
    a, b = short_net(a), short_net(b)
    for dom in (HV_RAW, HV_SW1, HV_SW2):
        if a in dom and b in dom:
            return 0.6 if dom is HV_RAW else 0.3
    if a in HV_ALL or b in HV_ALL:
        return 2.6
    if a in HV_MID or b in HV_MID:
        return 1.35
    if a in CHASSIS or b in CHASSIS:
        return 1.1
    return 0.3


def pad_rect(p):
    bb = p.GetBoundingBox()
    x0, y0 = cpos(pcbnew.VECTOR2I(bb.GetLeft(), bb.GetTop()))
    x1, y1 = cpos(pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()))
    return x0, y0, x1, y1


def pad_layers(p):
    if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
        return {"F", "B"}
    return {"B"} if p.IsOnLayer(pcbnew.B_Cu) else {"F"}


def rect_gap(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0.0)
    dy = max(a[1] - b[3], b[1] - a[3], 0.0)
    return math.hypot(dx, dy)


class Space:
    """Courtyards per side and pads (with nets) in a 5 mm grid, for the packer."""
    def __init__(self):
        self.crt = {"F": [], "B": []}
        self.cells = {}

    def _keys(self, r):
        for i in range(int((r[0] - 3) // 5), int((r[2] + 3) // 5) + 1):
            for j in range(int((r[1] - 3) // 5), int((r[3] + 3) // 5) + 1):
                yield (i, j)

    def add_fp(self, f, with_courtyard=True):
        side = "B" if f.IsFlipped() else "F"
        if with_courtyard:
            self.crt[side].append(courtyard_box(f, side))
        for p in f.Pads():
            r = pad_rect(p)
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH or f.GetReference().startswith("H"):
                x, y = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
                r = (x - 4.2, y - 4.2, x + 4.2, y + 4.2)
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                for sd in ("F", "B"):
                    self.crt[sd].append(r)
            item = (r, p.GetNetname(), pad_layers(p))
            for k in self._keys(r):
                self.cells.setdefault(k, []).append(item)

    def add_rect(self, side, r, net="__keepout__"):
        item = (r, net, {side})
        for k in self._keys(r):
            self.cells.setdefault(k, []).append(item)

    def fits(self, f, side, gap):
        cb = courtyard_box(f, side)
        g = (cb[0] - gap / 2, cb[1] - gap / 2, cb[2] + gap / 2, cb[3] + gap / 2)
        if any(overlaps(g, o) for o in self.crt[side]):
            return False
        for p in f.Pads():
            r, n, ls = pad_rect(p), p.GetNetname(), pad_layers(p)
            seen = set()
            for k in self._keys(r):
                for item in self.cells.get(k, ()):
                    if id(item) in seen:
                        continue
                    seen.add(id(item))
                    r2, n2, ls2 = item
                    if not (ls & ls2):
                        continue
                    req = 0.6 if n2 == "__keepout__" else net_req(n, n2)
                    if n2 != "__keepout__" and n == n2:
                        continue
                    if rect_gap(r, r2) < req:
                        return False
        return True


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def build_space(board):
    sp = Space()
    for f in board.GetFootprints():
        if f.GetReference() in PACKED and f.GetReference() not in DONE:
            continue
        sp.add_fp(f)
    for x, y in TAB_SCREWS:
        sp.add_rect("B", (x - 5.0, y - 5.0, x + 5.0, y + 5.0))
    for side, r in RESERVED:
        sp.crt[side].append(r)
    return sp


def pack(board, fps, name, zones, refs, gap=0.8):
    sp = build_space(board)
    missing = []
    for ref in refs:
        f = fps[ref]
        done = False
        for side, x0, y0, x1, y1 in zones:
            place_at(f, side, x0, y0, 0)
            cx0, cy0, cx1, cy1 = courtyard_box(f, side)
            w, h = cx1 - cx0, cy1 - cy0
            ox, oy = x0 - cx0, y0 - cy0
            y = y0
            while y + h <= y1 and not done:
                x = x0
                while x + w <= x1:
                    place_at(f, side, x + ox, y + oy, 0)
                    if sp.fits(f, side, gap):
                        sp.add_fp(f)
                        DONE.add(ref)
                        done = True
                        break
                    x += 0.5
                y += 0.5
            if done:
                break
        if not done:
            missing.append(ref)
            place_at(f, "B", 700, 100, 0)
    if missing:
        print(f"group {name}: no room for {missing}")
    return missing


POWER_LIKE = {"GND", "+3V3", "+12V", "PGND", "VREF", "+3V3_REF", "IBIAS"}


def pack_near(board, fps, name, zones, refs, gap=1.1):
    """Connectivity-driven packing: each part goes to the free spot nearest to the pads it shares a signal net
    with (or, for a part with only supply nets, to the last IC listed before it), rotation 0 or 90."""
    sp = build_space(board)
    grid = []
    for side, x0, y0, x1, y1 in zones:
        x = x0
        while x <= x1:
            y = y0
            while y <= y1:
                grid.append((side, x, y))
                y += 0.5
            x += 0.5
    placed_pads = {}
    for f in board.GetFootprints():
        if f.GetReference() in PACKED and f.GetReference() not in DONE:
            continue
        for p in f.Pads():
            placed_pads.setdefault(p.GetNetname(), []).append(cpos(p.GetPosition()))
    missing, anchor = [], None
    for ref in refs:
        f = fps[ref]
        nets = {p.GetNetname() for p in f.Pads() if short_net(p.GetNetname()) not in POWER_LIKE and p.GetNetname()}
        pts = [q for n in nets for q in placed_pads.get(n, [])]
        if pts:
            tx, ty = sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts)
        elif anchor is not None:
            tx, ty = anchor
        else:
            side, x0, y0, x1, y1 = zones[0]
            tx, ty = (x0 + x1) / 2, (y0 + y1) / 2
        done = False
        for side, x, y in sorted(grid, key=lambda g: (g[1] - tx) ** 2 + (g[2] - ty) ** 2)[:4000]:
            for rot in (0, 90):
                place_at(f, side, x, y, rot)
                cb = courtyard_box(f, side)
                if not any(z[0] == side and z[1] <= cb[0] and z[2] <= cb[1] and cb[2] <= z[3] and cb[3] <= z[4]
                           for z in zones):
                    continue
                if sp.fits(f, side, gap):
                    sp.add_fp(f)
                    DONE.add(ref)
                    for p in f.Pads():
                        placed_pads.setdefault(p.GetNetname(), []).append(cpos(p.GetPosition()))
                    done = True
                    break
            if done:
                break
        if not done:
            missing.append(ref)
            place_at(f, "B", 700, 100, 0)
        elif ref.startswith("U"):
            anchor = cpos(f.GetPosition())
    if missing:
        print(f"group {name}: no room for {missing}")
    return missing


# ---------------------------------------------------------------- drawing helpers
def shape_poly(board, pts, layer, w=0.1, fill=False):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_POLY)
    s.SetPolyPoints([pt(*p) for p in pts])
    s.SetLayer(layer)
    s.SetWidth(mm(w))
    s.SetFilled(fill)
    board.Add(s)


def seg(board, x0, y0, x1, y1, layer, w=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pt(x0, y0))
    s.SetEnd(pt(x1, y1))
    s.SetLayer(layer)
    s.SetWidth(mm(w))
    board.Add(s)


def box(board, x0, y0, x1, y1, layer, w=0.1):
    for a, b, c, d in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        seg(board, a, b, c, d, layer, w)


def circle(board, x, y, r, layer, w=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_CIRCLE)
    s.SetCenter(pt(x, y))
    s.SetEnd(pt(x + r, y))
    s.SetLayer(layer)
    s.SetWidth(mm(w))
    board.Add(s)


def note(board, s, x, y, size=1.2, layer=pcbnew.Cmts_User, mirror=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(pt(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(size * 0.15))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    if mirror:
        t.SetMirrored(True)
    board.Add(t)


def rule_area(board, pts, layers=(pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu), tracks=True, vias=True, pads=False, fps=False,
              fill=True, name=None):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(tracks)
    z.SetDoNotAllowVias(vias)
    z.SetDoNotAllowZoneFills(fill)
    z.SetDoNotAllowPads(pads)
    z.SetDoNotAllowFootprints(fps)
    if name:
        z.SetZoneName(name)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    o = z.Outline()
    o.NewOutline()
    for x, y in pts:
        o.Append(mm(x - OX), mm(y - OY))
    board.Add(z)


def circle_pts(x, y, r, n=24):
    return [(x + r * math.cos(2 * math.pi * i / n), y + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def rect_pts(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]




# ---------------------------------------------------------------- board features
def outline(board):
    shape_poly(board, OUTLINE, pcbnew.Edge_Cuts)


def keepouts(board, fps):
    # standoffs: no copper within 4 mm of the hole (standoff body / screw head); H101 is the plated chassis pad
    for ref, (x, y) in HOLES.items():
        if ref != "H101":
            rule_area(board, circle_pts(x, y, 4.0))
    # TO-220 pin fields (named areas for the A6 rule), both sides of the lead row
    for ref in TO220:
        ys = [cpos(p.GetPosition())[1] for p in fps[ref].Pads()]
        rule_area(board, rect_pts(TO_X - 3.0, min(ys) - 1.5, TO_X + 2.0, max(ys) + 1.5), tracks=False, vias=False,
                  fill=False, name=f"PF_{ref}")


def tie_bands(board):
    for x0, y0, x1, y1 in TIE_BANDS:
        rule_area(board, rect_pts(x0, y0, x1, y1), layers=(pcbnew.B_Cu,), tracks=False, vias=False, fill=False,
                  fps=True, name="TIE_BAND")


def to220_pads(fps):
    """Narrower lead pads (1.6 x 2.4 mm, 1.1 mm drill): 0.94 mm between the 2.54 mm pitch leads (IPC A6 0.8 mm)."""
    for ref in TO220:
        for p in fps[ref].Pads():
            p.SetSize(pcbnew.VECTOR2I(mm(1.6), mm(2.4)))
            p.SetDrillSize(pcbnew.VECTOR2I(mm(1.1), mm(1.1)))


def notes(board, fps):
    C = pcbnew.Cmts_User
    note(board, "HV SUPPLIES rev 4: KiCad = chassis - (525, 30); F faces DOWN, B faces the plate", BX0, BY0 - 3.0, 1.2)
    seg(board, WALL_X, BY0 - 2, WALL_X, BY1 + 2, C, 0.3)
    note(board, "east wall inner face (assumed x 678)", WALL_X + 0.8, BY0 + 2, 1.0, C)
    # insulated receptacles hanging from the tabs (plan outline 8 x 7 mm)
    for ref in ("J101", "J102", "J103", "J201", "J202"):
        f = fps[ref]
        for num in sorted({p.GetNumber() for p in f.Pads()}):
            ps = pad_pos(f, num)
            cx, cy = sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)
            along_x = abs(ps[0][0] - ps[-1][0]) > 1
            w, h = (8.0, 7.0) if along_x else (7.0, 8.0)
            box(board, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, C, 0.12)
    S = pcbnew.F_SilkS
    for txt, x, y in (("W01-b B_P / B_N", 645.0, 51.5), ("W02-a RAW_SS1 / GND", 592.0, 51.0),
                      ("W03-a RAW_SS2 / GND", 570.0, 51.0), ("W04-a V_ANODE / GND_PWR", 572.0, 116.0),
                      ("W05-a V_SCREEN", 596.0, 116.0), ("W17-b", 562.8, 80.5), ("W16-b HV_PERMIT", 562.8, 64.0),
                      ("DANGER 450 V", 605.0, 100.0)):
        note(board, txt, x, y, 1.0, S)


def small_fab_text(board):
    for f in board.GetFootprints():
        v = f.Value()
        v.SetTextSize(pcbnew.VECTOR2I(mm(0.5), mm(0.5)))
        v.SetTextThickness(mm(0.08))
        v.SetVisible(False)
        r = f.Reference()
        if r.GetLayer() in (pcbnew.F_Fab, pcbnew.B_Fab):
            r.SetTextSize(pcbnew.VECTOR2I(mm(0.6), mm(0.6)))
            r.SetTextThickness(mm(0.1))


def silk_refs(board):
    keep = set(PADS) | {"J202", "D101"}
    for f in board.GetFootprints():
        if f.GetReference() not in keep:
            f.Reference().SetLayer(pcbnew.B_Fab if f.IsFlipped() else pcbnew.F_Fab)
        if f.GetReference().startswith("H") and f.GetReference() != "H101":
            f.Reference().SetVisible(False)


DONE = set()
PACKED = set()
for _g in GROUPS.values():
    PACKED.update(_g[1])


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else OUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    project_settings()
    board = pcbnew.NewBoard(out)
    board.SetCopperLayerCount(4)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(mm(1.6))
    ds.m_TrackMinWidth = mm(0.2)
    ds.m_MinClearance = mm(0.15)
    ds.m_ViasMinSize = mm(0.6)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_CopperEdgeClearance = mm(0.5)
    ds.m_HoleToHoleMin = mm(0.25)
    outline(board)

    t = netlist()
    nets = {}
    for n in t.iter("net"):
        ni = pcbnew.NETINFO_ITEM(board, n.get("name"))
        board.Add(ni)
        for nd in n.iter("node"):
            nets[(nd.get("ref"), nd.get("pin"))] = ni
    fps = {}
    for c in t.iter("comp"):
        ref = c.get("ref")
        f = load_fp(c.findtext("footprint"))
        f.SetReference(ref)
        f.SetValue(c.findtext("value"))
        sym = {fld.get("name"): fld.text or "" for fld in c.iter("field")}
        for fd in f.GetFields():
            if fd.GetName() in ("Datasheet", "Description"):
                fd.SetText(sym.get(fd.GetName(), ""))
        for k, v in sym.items():
            if k not in ("Reference", "Value", "Footprint", "Datasheet", "Description") and not f.HasField(k):
                f.SetField(k, v)
                fl = f.GetField(k)
                fl.SetVisible(False)
                fl.SetLayer(pcbnew.F_Fab)
        sp = c.find("sheetpath")
        f.SetPath(pcbnew.KIID_PATH(sp.get("tstamps") + c.findtext("tstamps")))
        f.SetSheetname(sp.get("names"))
        f.SetSheetfile(c.find("property[@name='Sheetfile']").get("value"))
        f.SetExcludedFromBOM(c.find("property[@name='exclude_from_bom']") is not None)
        if c.find("property[@name='dnp']") is not None:
            f.SetDNP(True)
        for p in f.Pads():
            ni = nets.get((ref, p.GetNumber()))
            if ni is not None:
                p.SetNet(ni)
        board.Add(f)
        fps[ref] = f
    unplaced = [r for r in fps if r not in PADS and r not in AT and r not in PACKED and r not in KELVIN]
    if unplaced:
        raise SystemExit(f"no position for {sorted(unplaced)}")
    to220_pads(fps)
    for ref, (side, tg) in PADS.items():
        place_pads(fps[ref], side, tg)
    for ref, (side, x, y, rot) in AT.items():
        place_at(fps[ref], side, x, y, rot)
    for ref in PACKED:                          # park the packed parts off the board first
        place_at(fps[ref], "B", 700, 100, 0)
    missing = []
    for name, (zones, refs) in GROUPS.items():
        missing += pack_near(board, fps, name, zones, refs, gap=0.6)
    for i, ref in enumerate(missing):           # spread what did not fit east of the board, for a later pass
        place_at(fps[ref], "B", 690 + 10 * (i % 4), 50 + 10 * (i // 4), 0)
    keepouts(board, fps)
    tie_bands(board)
    notes(board, fps)
    silk_refs(board)
    small_fab_text(board)
    pcbnew.SaveBoard(out, board)
    for ref in TO220:
        f = fps[ref]
        tab = [s for s in f.GraphicalItems() if s.GetLayer() == pcbnew.F_Fab]
        print(ref, "pins", " ".join(f"{n}=({pad_centre(f, n)[0]:.2f},{pad_centre(f, n)[1]:.2f})" for n in "123"),
              "rot", f.GetOrientationDegrees(), "flipped", f.IsFlipped())
    print(f"{out}: {len(fps)} parts, packed missing: {missing}")


if __name__ == "__main__":
    main()
