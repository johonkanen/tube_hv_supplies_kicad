#!/usr/bin/env python3
"""HV supplies rev 3, layout first pass: the placed board (outline, holes, every part, net classes and rules,
keep-outs, notes) from the schematic netlist, and the copper pours (--zones).

    tools/p2k/bin/kipy rev3/tools/make_pcb.py [OUT.kicad_pcb]      (default rev3/build/layout/00_placed.kicad_pcb)
    tools/p2k/bin/kipy rev3/tools/make_pcb.py --zones IN OUT       (add the pours of ZONES, fill)

Frame (README "Layout"): every position below is in the chassis frame (D748 top plate, mm: x from the left along
the front, y from the front panel's inner face to the rear). KiCad x = chassis x - 525, KiCad y = chassis y - 30
(the outline_edge_cuts.kicad_pcb frame). KiCad's F side faces DOWN (the through-hole parts, tabs and headers,
like the preamp); B faces the chassis plate (SMD <= 3 mm, the IGBTs lying on their aluminium bars). Seen in
KiCad from the front you look at the board from below, front panel at the top, x to the right = chassis x.

Placement: table PADS (two pads of a part put on two chassis points; the side's mirror and the rotation follow),
table AT (footprint origin and rotation), and the packed groups GROUPS (small SMD packed into a zone).
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pcbnew

R3 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(R3)
PROJECT = "tube_hv_supplies_rev3"
K = os.path.join(R3, "kicad")
PRO = os.path.join(K, PROJECT + ".kicad_pro")
SCH = os.path.join(K, PROJECT + ".kicad_sch")
KICAD_CLI = os.path.join(ROOT, "tools", "p2k", "bin", "kicad-cli")
STOCK = os.path.join(os.environ.get("KICAD_MOUNT") or open(f"/tmp/p2k_kicad_mount.{os.getuid()}").read().strip(),
                     "share", "kicad", "footprints")
OUT = os.path.join(R3, "build", "layout", "00_placed.kicad_pcb")
OX, OY = 525.0, 30.0                     # chassis -> KiCad offset

# ---------------------------------------------------------------- outline and holes (chassis mm)
OUTLINE = [(560, 30), (649, 30), (649, 39), (668, 39), (668, 30), (675, 30), (675, 145), (649, 145), (649, 180),
           (585, 180), (585, 200), (525, 200), (525, 127), (560, 127)]
HOLES = {"H101": (617.0, 50.0), "H102": (605.0, 124.7), "H103": (671.0, 48.0), "H104": (667.0, 138.0),
         "H105": (553.0, 195.0), "H106": (566.0, 122.0)}
# H101 plated (CHASSIS). H102 back on the existing D748 hole (605.0, 124.7) (the fourth pass had moved it to
# (600, 98) because C209 sat there; C209 is now in the rear strip, and (600, 98) is the bridge-1 driver's place)
TAB_SCREWS = [(582.0, 64.8), (595.0, 64.8), (618.5, 171.2), (631.5, 171.2)]   # in the plate; nut ~2 mm above B
BARS = [(570, 62.5, 608, 77.5), (601, 158.5, 647, 173.5)]
CORRIDOR = (525, 127, 560, 147)
LV_STRIP = (560, 30, 570, 127)

# ---------------------------------------------------------------- placement (chassis mm)
# PADS: ref -> (side, {pad: (x, y), pad: (x, y)}). The two pads fix position and rotation.
PADS = {
    # interface tabs and headers (layout sketch, interfaces.md 12.5)
    "J101": ("F", {"1": (656.0, 59.0), "2": (656.0, 47.0)}),
    "J102": ("F", {"1": (604.0, 37.0), "2": (616.0, 37.0)}),
    "J103": ("F", {"1": (578.0, 37.0), "2": (590.0, 37.0)}),
    "J201": ("F", {"1": (531.5, 170.0), "2": (531.5, 182.0)}),
    "J1": ("F", {"1": (566.37, 108.86), "40": (565.10, 84.73)}),
    "J501": ("F", {"1": (572.5, 117.5), "2": (575.04, 117.5)}),
    # fault / RF network and the star (front)
    "D102": ("F", {"1": (625.0, 34.5), "4": (640.24, 34.5)}),
    "C104": ("F", {"1": (623.5, 42.5), "2": (646.0, 42.5)}),
    "R106": ("F", {"1": (625.0, 51.0), "2": (645.32, 51.0)}),
    # input (east column) and the raw bleeder (front band)
    "C101": ("F", {"1": (659.25, 78.0), "2": (666.75, 78.0)}),
    "L101": ("F", {"1": (661.0, 96.5), "2": (666.0, 96.5)}),
    "R103": ("F", {"1": (576.0, 45.5), "2": (596.32, 45.5)}),
    "R104": ("F", {"1": (596.32, 52.5), "2": (576.0, 52.5)}),
    "R105": ("F", {"1": (655.0, 126.0), "2": (670.24, 126.0)}),
    # bridge 1: devices on bar 1 (plate side), input bulk, L1, C1, second stage
    # high side Q201 on the east hole (595, 64.8), low side Q202 on the west hole (582, 64.8): U301 on the plate
    # side has its channel A (high side) at the east end, so each gate is straight in front of its driver output
    "Q201": ("B", {"1": (592.46, 81.46), "3": (597.54, 81.46)}),
    "Q202": ("B", {"1": (579.46, 81.46), "3": (584.54, 81.46)}),
    "C201": ("F", {"1": (590.0, 106.0), "2": (582.5, 106.0)}),
    "L201": ("F", {"1": (613.0, 79.0), "2": (643.0, 79.0)}),
    "C204": ("F", {"1": (643.0, 107.0), "2": (643.0, 117.0)}),
    "C211": ("F", {"1": (628.0, 112.0), "2": (600.5, 112.0)}),
    "L202": ("F", {"1": (659.5, 112.5), "2": (670.93, 112.5)}),
    "C212": ("F", {"1": (641.25, 134.0), "2": (648.75, 134.0)}),
    "R216": ("F", {"1": (657.5, 131.9), "2": (657.5, 139.52)}),
    "C205": ("F", {"1": (604.0, 67.0), "2": (576.5, 67.0)}),     # VO1 film, front-west under bar 1
    "R205": ("F", {"1": (644.0, 166.2), "2": (644.0, 173.82)}),
    # bridge 2: devices on bar 2, input bulk, L1 (switch node pin east), C1 in the rear strip, second stage on the arm
    "Q203": ("B", {"1": (621.04, 154.54), "3": (615.96, 154.54)}),
    "Q204": ("B", {"1": (634.04, 154.54), "3": (628.96, 154.54)}),
    "C206": ("F", {"1": (619.0, 135.0), "2": (626.5, 135.0)}),
    "L203": ("F", {"1": (598.0, 155.0), "2": (568.0, 155.0)}),
    "C209": ("F", {"1": (567.5, 188.5), "2": (577.5, 188.5)}),
    "L204": ("F", {"1": (540.0, 156.7), "2": (551.43, 156.7)}),
    "C216": ("F", {"1": (541.6, 174.3), "2": (549.1, 174.3)}),
    "R217": ("F", {"1": (556.5, 170.5), "2": (556.5, 178.12)}),
    "R212": ("F", {"1": (541.0, 187.5), "2": (541.0, 195.12)}),
    "D201": ("F", {"1": (529.2, 188.3), "2": (529.2, 193.38)}),
    "C210": ("F", {"1": (609.2, 171.0), "2": (636.7, 171.0)}),   # VO2 film, rear under bar 2
    # gate drivers (plate side, outputs toward the device pins)
    "U301": ("B", {"16": (593.55, 91.35), "9": (584.66, 91.35)}),   # B mirror: OUTA (14-16) east, under Q201's gate
    "U302": ("B", {"16": (623.25, 148.15), "9": (632.14, 148.15)}),   # rows y 148.15 (outputs) / 138.85  # OUTA west, under Q203's gate
}
# AT: ref -> (side, x, y, rotation) of the footprint origin
AT = {
    "J202": ("F", 531.5, 155.0, 0),
    # bridge 1 commutation parts (F, behind the pin row y 81.46; tools/bridge_copper.py draws their copper)
    # shunt R202 and C202 on the far side of the pin row (y 77.9, under the lead bends, opposite the SW1 link on
    # the plate side at y 79.2): the commutation loop C202 -> Q201 -> SW1 link -> Q202 -> R202 is folded flat
    "C214": ("F", 579.2, 86.2, 180), "R202": ("F", 587.5, 77.9, 0), "C202": ("F", 594.5, 77.9, 180),
    "C203": ("F", 594.5, 91.0, 180), "C213": ("F", 600.6, 85.4, 0),
    # bridge 1 gate parts (plate side, between the pin row and U301)
    "R305": ("B", 592.46, 86.0, 90), "R306": ("B", 594.95, 83.9, 0), "R307": ("B", 579.46, 86.0, 90),
    "R308": ("B", 581.9, 84.2, 0), "C302": ("B", 598.6, 88.5, 90), "C303": ("B", 600.4, 88.5, 90),
    "D301": ("B", 597.5, 94.0, 270), "C305": ("F", 586.0, 93.0, 180), "C304": ("F", 586.0, 95.3, 180),
    # bridge 2 commutation parts (F, in front of the pin row y 154.54)
    "C217": ("F", 613.6, 151.0, 180), "C207": ("F", 619.0, 158.1, 0), "C208": ("F", 619.8, 146.4, 0),
    "R209": ("F", 626.0, 158.1, 180), "C218": ("F", 635.0, 150.6, 0),
    # bridge 2 gate parts (plate side)
    "R313": ("B", 621.04, 151.1, 270), "R314": ("B", 618.5, 151.3, 180), "R315": ("B", 634.04, 151.1, 270),
    "R316": ("B", 631.5, 151.3, 180), "D302": ("B", 618.6, 144.0, 90),
    "C309": ("B", 614.6, 147.6, 270), "C310": ("B", 612.6, 147.6, 270),
    # shunts of the C1 currents
    "R203": ("F", 587.5, 119.5, 90), "R210": ("B", 582.0, 193.0, 90),
    # input HF caps, links, net ties
    "C102": ("F", 663.0, 66.0, 0), "C103": ("B", 663.5, 102.5, 0),
    "R101": ("B", 606.0, 47.5, 90), "R102": ("B", 586.0, 47.5, 90),
    "R201": ("B", 612.0, 92.0, 90), "R208": ("B", 613.5, 132.0, 0),
    "NT101": ("F", 650.5, 47.0, 90),
    "D101": ("F", 672.2, 131.0, 90),
    # output bleeders (plate side, over L203's rear half) and the V_ANODE lamp (bottom side, between J202 / J201)
    "R206": ("B", 575.0, 168.0, 0), "R207": ("B", 583.5, 168.0, 0),
    "R213": ("B", 575.0, 174.0, 0), "R214": ("B", 583.5, 174.0, 0),
    "R215": ("B", 575.0, 162.0, 0), "D202": ("F", 558.0, 160.0, 90),
}
# Kelvin net ties (schematic sheet 04): pad 1 laid on the shunt's pad edge, pad 2 outward.
# ref -> (shunt, shunt pad, direction out of the pad, coordinate along the edge)
KELVIN = {"NT401": ("R203", "1", "+y", 586.2), "NT402": ("R203", "2", "-y", 588.8), "NT501": ("R203", "2", "-x", 116.2),
          "NT403": ("R202", "1", "-y", 584.3), "NT404": ("R202", "2", "-y", 590.7),
          "NT407": ("R209", "1", "+y", 629.3), "NT408": ("R209", "2", "+y", 622.8),
          "NT405": ("R210", "1", "-x", 195.4), "NT406": ("R210", "2", "-x", 190.6)}
for _r, (_x, _y) in HOLES.items():
    AT[_r] = ("F", _x, _y, 0)

# packed groups: name -> (side, zone x0, y0, x1, y1, refs). Packed in order, row by row.
GROUPS = {}


def _refs(prefix, nums):
    return [f"{prefix}{n}" for n in nums]


# divider chains (bottom side, 1206 end to end, 4.7 mm pitch). V_ANODE / V_SCREEN in the measurement area, HV end
# east (fed from the rear through the corridor x 591-599 between the control area and H102); raw UIN and UC1 in the
# band between L201 and C211 (y 102), UIN end west (fed from R201's side), UC1 end east (from C211's UC1 node)
for _x, (_t, _m, _b) in ((592.5, ("R401", "R402", "R403")), (597.0, ("R408", "R409", "R410"))):
    AT[_t], AT[_m], AT[_b] = ("F", _x, 131.1, 90), ("F", _x, 126.4, 90), ("F", _x, 121.7, 90)   # HV end south
AT["R415"], AT["R416"], AT["R417"] = ("F", 605.0, 102.0, 0), ("F", 609.7, 102.0, 0), ("F", 614.4, 102.0, 0)
AT["R420"], AT["R421"], AT["R422"] = ("F", 629.0, 102.0, 180), ("F", 624.3, 102.0, 180), ("F", 619.6, 102.0, 180)
# the six ADS7056 in a row (plate side) over C211, SCK daisy-chained along y 101.5 (tools/fast_copper.py)
ADC_ROW = ["U402", "U406", "U407", "U404", "U409", "U410"]
for _i, _r in enumerate(ADC_ROW):
    AT[_r] = ("B", 606.0 + 6.0 * _i, 104.0, 0)
AT["U411"] = ("B", 650.5, 102.2, 180)    # AD7689 at the chain's far end, SCK (pin 13) on the bus line y 102.4
AT["R456"] = ("B", 646.2, 100.4, 0)      # returned SCLK taken at the far end (J1 pad 16)
AT["R457"] = ("B", 633.0, 107.4, 0)      # CS_FAST pull-up at the end of the CS bus
# lanes kept free by the packer for the scripted buses (tools/bridge_copper.py spi()): SCLK y 102.4, CS_FAST y 105.6
RESERVED = [("B", (603.5, 101.95, 648.2, 102.85)), ("B", (603.5, 105.15, 636.2, 106.05))]
AT["U412"] = ("B", 640.0, 121.0, 0)      # REF3030

# groups: name -> (list of zones (side, x0, y0, x1, y1), refs); each part goes into the first zone with room
GROUPS["drv1"] = ([("B", 583.0, 101.8, 601.0, 109.0), ("B", 569.0, 97.0, 583.0, 108.0)],
                  ["R304", "C301", "R301", "R302", "R303"])
GROUPS["drv2"] = ([("B", 634.0, 137.0, 646.0, 149.0), ("B", 612.0, 127.5, 646.0, 138.3)],
                  ["R312", "C311", "C312", "C308", "R309", "R310", "R311"])
GROUPS["adc"] = ([("B", 603.0, 100.0, 642.0, 114.5)],
                 ["C404", "C405", "C406", "R406", "R407", "C418", "C419", "C420", "R430", "R431",
                  "C422", "C423", "C424", "R437", "R438", "C410", "C411", "C412", "R413", "R414",
                  "C427", "C428", "C429", "R444", "R445", "C431", "C432", "C433", "R451", "R452"])
GROUPS["aux"] = ([("B", 641.0, 99.5, 647.5, 126.3), ("B", 603.0, 114.5, 647.5, 126.3)],
                 ["C439", "FB401", "C435", "C436", "C440", "C437", "C438", "R455",
                  "U405", "C434", "R453", "R454", "C413", "C414", "C415", "C416", "R418", "R419", "R423", "R424"])
GROUPS["amp"] = ([("B", 603.0, 114.5, 647.5, 126.3), ("B", 569.0, 108.0, 598.5, 134.5)],
                 ["U401", "C402", "C401", "R404", "R405", "C403", "R425", "R426", "R427", "R428", "R429", "C417",
                  "U403", "C408", "C407", "R411", "R412", "C409", "R432", "R433", "R434", "R435", "R436", "C421",
                  "U408", "C425", "R439", "R440", "R441", "R442", "R443", "C426", "R446", "R447", "R448", "R449",
                  "R450", "C430"])
GROUPS["comp"] = ([("B", 569.0, 108.0, 598.5, 134.5), ("F", 569.5, 113.0, 584.0, 133.5)],
                  ["U505", "C509", "U506", "C516", "U507", "C517", "R509", "R510", "R511", "R512", "R513", "R514",
                   "R515", "R516", "R517", "R518"])
GROUPS["ctrl"] = ([("B", 560.8, 31.0, 574.5, 95.0), ("B", 569.0, 97.0, 586.0, 108.0)],
                  ["U501", "D501", "D502", "R502", "R503", "R504", "R505", "C503", "U502", "C504",
                   "U504", "C506", "U503", "C507", "U508", "C512", "U509", "C513", "U510", "C514", "U511", "C515",
                   "R501", "R506", "R507", "R519", "R520", "R521", "C505", "C510", "C511", "D504", "C501", "C502"])

# ---------------------------------------------------------------- net classes and rules
HV_RAW = ["B_P", "UIN", "UIN1", "UIN2", "RAW_SS1", "RAW_SS2"]          # one potential (links, L101)
HV_SW1 = ["SW1", "GH1", "GHD1", "BOOT1"]                                  # switch node + its floating driver
HV_SW2 = ["SW2", "GH2", "GHD2", "BOOT2"]
HV_SW = HV_SW1 + HV_SW2
HV_OUT = ["UC1", "UC2", "VO1", "VO2", "V_ANODE", "V_SCREEN", "DS0A"]
HV_MID = ["BLD1", "BL1", "BL2", "DV0B", "DV1B", "DS0B", "DS1B", "DV0A", "DV1A", "DS1A"]   # <= 300 V to anything
PWR = ["PGND", "GND_STAR", "IS1", "IS2", "IC1", "IC2", "CD1", "CD2"]
KELVIN_NETS = ["KS0P", "KS0N", "KS1P", "KS1N", "KS2P", "KS2N", "KS3P", "KS3N"]
CHASSIS = ["CHASSIS", "BR_DC"]
SUPPLY = ["+12V", "+3V3", "GND", "+3V3_REF", "VREF"]
HV_ALL = HV_RAW + HV_SW + HV_OUT
# parts whose own pad spacing is below 2.5 mm between HV nets (IPC-2221B A6, component terminations, 301-500 V: 0.8 mm)
A6_PARTS = ["Q201", "Q202", "Q203", "Q204",
            "R401", "R402", "R403", "R408", "R409", "R410", "R415", "R416", "R417", "R420", "R421", "R422",
            "D301", "D302", "U301", "U302", "R105", "R215", "D201"]


def _or(fmt, items):
    return " || ".join(fmt.format(i) for i in items)


def dru():
    hv = _or("A.NetClass == '{}'", ["HV_RAW", "HV_SW1", "HV_SW2", "HV_OUT"])
    hvb = _or("B.NetClass == '{}'", ["HV_RAW", "HV_SW1", "HV_SW2", "HV_OUT"])
    a6 = _or("(A.memberOfFootprint('{0}') && B.memberOfFootprint('{0}'))", A6_PARTS)
    pf = _or("(A.intersectsArea('PF_{0}') && B.intersectsArea('PF_{0}'))", ["Q201", "Q202", "Q203", "Q204"])
    return f"""(version 1)
# HV supplies rev 3 rules (rev3/tools/make_pcb.py; STATUS.md "Layout, first pass").
# Clearance basis: IPC-2221B table 6-1, external conductors, uncoated, sea level to 3050 m (B2):
#   301-500 V 2.5 mm, 151-300 V 1.25 mm; component leads / terminations uncoated (A6): 301-500 V 0.8 mm.
# Creepage check basis: IEC 60664-1 functional insulation, pollution degree 2, material group IIIa (FR-4,
#   CTI >= 175): 500 V working -> 2.5 mm, 250 V -> 1.25 mm. The 2.5 mm clearance rules below give the same
#   surface distance on the board, so creepage is met wherever clearance is (no slots needed; see STATUS).
# Working voltages: raw rail 480 V transient / 450 V sustained (HV_RAW), switch nodes 0-480 V with their
#   floating gate drive (HV_SW1 / HV_SW2), outputs and C1 nodes 0-440 V (trips 438 / 421 V; HV_OUT).
# JLCPCB standard 2-layer: 0.127 / 0.127 mm, 0.3 mm via drill; this board uses 0.2 / 0.2 mm, 0.6 / 0.3 vias.

(rule "HV to anything (B2, 301-500 V)"
  (condition "({hv}) && A.NetName != B.NetName")
  (constraint clearance (min 2.5mm)))

(rule "HV mid nodes (B2, 151-300 V)"
  (condition "A.NetClass == 'HV_MID' && A.NetName != B.NetName")
  (constraint clearance (min 1.25mm)))

(rule "divider tops: the top resistor's two ends (<= 160 V apart, B2 151-300 V)"
  (condition "(A.NetName == '*V_ANODE' && B.NetName == '*/DV0A') || (A.NetName == '*V_SCREEN' && B.NetName == '*/DV1A') || (A.NetName == '*UIN' && B.NetName == '*/DS0A') || (A.NetName == '*UC1' && B.NetName == '*/DS1A') || (A.NetName == '*/DS0A' && B.NetName == '*/DS0B')")
  (constraint clearance (min 1.25mm)))

(rule "HV to board edge"
  (condition "{hv}")
  (constraint edge_clearance (min 2.5mm)))

(rule "HV to the standoff holes (metal standoff r 3 mm + 2.5 mm)"
  (condition "({hv}) && B.Type == 'Pad' && B.Pad_Type == 'NPTH, mechanical'")
  (constraint hole_clearance (min 4.0mm)))

(rule "chassis net to anything (fault path)"
  (condition "A.NetClass == 'CHASSIS' && A.NetName != B.NetName")
  (constraint clearance (min 1.0mm)))

# exceptions, last so they win
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

(rule "floating NC pads (UCC21520 pins 12 / 13): the package's own spacing"
  (condition "A.NetName == '*unconnected-*' || B.NetName == '*unconnected-*'")
  (constraint clearance (min 0.15mm)))
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
               cls("CHASSIS", 1.0, 1.0, "rgba(0, 160, 0, 1.000)", 5),
               cls("SUPPLY", 0.15, 0.4, "rgba(120, 120, 0, 1.000)", 6)]
    pats = []
    for c, names in (("HV_RAW", HV_RAW), ("HV_SW1", HV_SW1), ("HV_SW2", HV_SW2), ("HV_OUT", HV_OUT), ("HV_MID", HV_MID), ("PWR", PWR),
                     ("CHASSIS", CHASSIS), ("SUPPLY", SUPPLY)):
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


def rule_area(board, pts, layers=(pcbnew.F_Cu, pcbnew.B_Cu), tracks=True, vias=True, pads=False, fps=False,
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
    # tab screws: the nut and screw tip (chassis potential) sit about 2 mm above the plate side: no B copper
    for x, y in TAB_SCREWS:
        rule_area(board, circle_pts(x, y, 5.0), layers=(pcbnew.B_Cu,))
    # ribbon corridor: no parts on the bottom (F) side; copper allowed
    x0, y0, x1, y1 = CORRIDOR
    rule_area(board, rect_pts(x0, y0, x1, y1), layers=(pcbnew.F_Cu,), tracks=False, vias=False, fill=False,
              fps=True, name="CORRIDOR")
    # named areas for the rules: the LV strip, the TO-220 pin fields
    x0, y0, x1, y1 = LV_STRIP
    rule_area(board, rect_pts(x0, y0, x1, y1), layers=(pcbnew.F_Cu,), tracks=False, vias=False, fill=False,
              name="LV_STRIP")
    for ref in ("Q201", "Q202", "Q203", "Q204"):
        ps = [p for p in fps[ref].Pads()]
        xs = [cpos(p.GetPosition())[0] for p in ps]
        y = cpos(ps[0].GetPosition())[1]
        y0, y1 = (y - 3.0, y + 3.4) if ref in ("Q201", "Q202") else (y - 3.4, y + 3.0)   # both sides of the row
        rule_area(board, rect_pts(min(xs) - 1.5, y0, max(xs) + 1.5, y1), tracks=False, vias=False, fill=False,
                  name=f"PF_{ref}")


LV_AREAS = [rect_pts(560.0, 30.0, 575.0, 97.0), rect_pts(560.0, 97.0, 584.0, 136.0)]
GND_AREAS = LV_AREAS + [rect_pts(601.5, 99.0, 648.5, 127.6)]     # also the measurement area, for the ground step


def hv_keepouts(board):
    """Polygons on User.2 that the router's HV steps keep out of (--keepout): the control, measurement and
    driver-input areas, and 6.2 mm around each non-plated standoff (4.0 mm from the hole edge, rule
    'HV to the standoff holes'). Not a DRC rule: the DRC rules above grade the result."""
    for pts in LV_AREAS:
        shape_poly(board, pts, pcbnew.User_2, 0.1, fill=True)
    for ref, (x, y) in HOLES.items():
        if ref != "H101":
            shape_poly(board, circle_pts(x, y, 6.2), pcbnew.User_2, 0.1, fill=True)
    for pts in GND_AREAS:
        shape_poly(board, pts, pcbnew.User_3, 0.1, fill=True)


def notes(board, fps):
    C = pcbnew.Cmts_User
    note(board, "HV SUPPLIES rev 3, layout first pass: KiCad = chassis - (525, 30); F faces DOWN, B faces the plate",
         527, 28.0, 1.2)
    for x0, y0, x1, y1 in BARS:
        box(board, x0, y0, x1, y1, pcbnew.B_Fab, 0.15)
        note(board, "Al bar 6 mm on the plate (plate side, 9 mm above B)", x0 + 0.5, y0 + 1.5, 0.9, pcbnew.B_Fab, True)
    for x, y in TAB_SCREWS:
        circle(board, x, y, 1.6, pcbnew.B_Fab, 0.15)
    x0, y0, x1, y1 = CORRIDOR
    box(board, x0, y0, x1, y1, C, 0.15)
    note(board, "RIBBON CORRIDOR: no F-side parts (control board J5 / J7)", x0 + 0.5, y0 + 2.0, 0.9)
    x0, y0, x1, y1 = LV_STRIP
    box(board, x0, y0, x1, y1, C, 0.15)
    note(board, "NO-HV STRIP (F)", x0 + 0.3, y1 - 1.5, 0.8)
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
    for txt, x, y in (("W01-b IF-1  B_P / B_N (red / black)", 640.0, 63.5), ("W02-a RAW_SS1 / GND (preamp)", 599.0, 42.2),
                      ("W03-a RAW_SS2 / GND (PI+FX)", 572.0, 42.2), ("W04-a V_ANODE / GND_PWR", 527.0, 188.0),
                      ("W05-a V_SCREEN", 527.0, 149.6), ("W17-b IF-2.2", 561.0, 80.5), ("W16-b HV_PERMIT", 566.0, 121.6),
                      ("DANGER 480 V", 610.0, 128.0)):
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
    keep = {"J1", "J101", "J102", "J103", "J201", "J202", "J501", "H101", "Q201", "Q202", "Q203", "Q204",
            "C101", "C201", "C206", "C204", "C209", "C211", "C205", "C210", "C212", "C216", "L101", "L201", "L202",
            "L203", "L204", "R205", "R212", "R103", "R104", "R105", "R106", "C104", "D102", "D201", "R216", "R217"}
    for f in board.GetFootprints():
        if f.GetReference() not in keep:
            f.Reference().SetLayer(pcbnew.B_Fab if f.IsFlipped() else pcbnew.F_Fab)
        if f.GetReference().startswith("H") and f.GetReference() != "H101":
            f.Reference().SetVisible(False)


# ---------------------------------------------------------------- pours (after routing)
# (net, layer, priority, polygon): the power star island (front, both sides) and the control ground under the
# low-voltage areas (plate side), plus the bottom-side LV strip facing the control board. The DRC rules keep every
# pour 2.5 mm from HV copper by themselves.
ZONES = [("GND_STAR", pcbnew.F_Cu, 1, rect_pts(586.0, 30.0, 649.0, 55.6)),
         ("GND_STAR", pcbnew.B_Cu, 1, rect_pts(586.0, 30.0, 649.0, 55.6)),
         ("GND", pcbnew.B_Cu, 1, rect_pts(560.0, 30.0, 576.0, 97.0)),
         ("GND", pcbnew.B_Cu, 1, rect_pts(560.0, 97.0, 601.5, 136.5)),
         ("GND", pcbnew.B_Cu, 1, rect_pts(601.5, 99.0, 648.5, 127.6)),
         ("GND", pcbnew.B_Cu, 1, rect_pts(611.0, 127.6, 646.0, 141.0)),
         ("GND", pcbnew.F_Cu, 1, rect_pts(560.0, 30.0, 570.0, 127.0))]


def add_zones(board):
    nets = board.GetNetsByName()
    for name, layer, prio, poly in ZONES:
        poly = list(poly)
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(nets[name])
        z.SetAssignedPriority(prio)
        z.SetMinThickness(mm(0.3))
        z.SetLocalClearance(mm(0.3))
        z.SetThermalReliefGap(mm(0.5))
        z.SetThermalReliefSpokeWidth(mm(0.8))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        o = z.Outline()
        o.NewOutline()
        for x, y in poly:
            o.Append(mm(x - OX), mm(y - OY))
        board.Add(z)


DONE = set()
PACKED = set()
for _g in GROUPS.values():
    PACKED.update(_g[1])


def main():
    if "--zones" in sys.argv:
        i = sys.argv.index("--zones")
        src, dst = sys.argv[i + 1], sys.argv[i + 2]
        b = pcbnew.LoadBoard(src)
        add_zones(b)
        zones = b.Zones()
        pcbnew.ZONE_FILLER(b).Fill(zones)
        pcbnew.SaveBoard(dst, b)
        print(f"{dst}: zones added and filled")
        return
    out = sys.argv[1] if len(sys.argv) > 1 else OUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    project_settings()
    board = pcbnew.NewBoard(out)
    board.SetCopperLayerCount(2)
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
        name = n.get("name")
        ni = pcbnew.NETINFO_ITEM(board, name)
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
                fl.SetLayer(pcbnew.B_Fab if False else pcbnew.F_Fab)
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
    for ref, (side, tg) in PADS.items():
        place_pads(fps[ref], side, tg)
    for ref, (side, x, y, rot) in AT.items():
        place_at(fps[ref], side, x, y, rot)
    for ref, (sh, pnum, d, along) in KELVIN.items():
        f, shf = fps[ref], fps[sh]
        side = "B" if shf.IsFlipped() else "F"
        pr = [p for p in shf.Pads() if p.GetNumber() == pnum][0]
        x0, y0, x1, y1 = pad_rect(pr)
        if d == "+x":
            place_at(f, side, x1 - 0.3 + 0.5, along, 0)
        elif d == "-x":
            place_at(f, side, x0 + 0.3 - 0.5, along, 0 if ref == "NT501" else 180)   # NT501: pad 2 is PGND
        elif d == "+y":
            place_at(f, side, along, y1 - 0.3 + 0.5, 270)
        else:
            place_at(f, side, along, y0 + 0.3 - 0.5, 90)
        c1 = pad_centre(f, "2" if ref == "NT501" else "1")
        if not (x0 <= c1[0] <= x1 and y0 <= c1[1] <= y1):
            raise SystemExit(f"{ref}: pad 1 at {c1} not on {sh} pad {pnum} {x0, y0, x1, y1}")
    for ref in PACKED:                          # park the packed parts off the board first
        place_at(fps[ref], "B", 700, 100, 0)
    missing = []
    for name, (zones, refs) in GROUPS.items():
        missing += pack(board, fps, name, zones, refs)
    keepouts(board, fps)
    hv_keepouts(board)
    notes(board, fps)
    silk_refs(board)
    small_fab_text(board)
    pcbnew.SaveBoard(out, board)
    # report the device tabs (must sit on the plate holes) and the interface pins
    for ref, hole in zip(("Q201", "Q202", "Q203", "Q204"), TAB_SCREWS):
        f = fps[ref]
        p1 = pad_centre(f, "1")
        print(ref, "pins", " ".join(f"{n}=({pad_centre(f, n)[0]:.2f},{pad_centre(f, n)[1]:.2f})" for n in "123"),
              "rot", f.GetOrientationDegrees(), "flipped", f.IsFlipped(), "screw", hole)
    for ref, pads in (("J1", ("1", "2", "40")), ("J501", ("1",)), ("U301", ("1", "8", "9", "16")),
                      ("U302", ("1", "8", "9", "16"))):
        print(ref, " ".join(f"{n}=({pad_centre(fps[ref], n)[0]:.2f},{pad_centre(fps[ref], n)[1]:.2f})" for n in pads))
    print(f"{out}: {len(fps)} parts, packed missing: {missing}")


if __name__ == "__main__":
    main()
