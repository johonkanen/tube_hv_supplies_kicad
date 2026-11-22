#!/usr/bin/env python3
"""HV supplies rev 3: the chosen outline and floorplan (third pass, 2026-11-23).

Outline accepted by the user (L shape with SMD on the plate side), trimmed for what the D748
drawing shows behind the rear strip: the mains inlet (cutout x 633.6-661.1, 32.2-52.2 mm below the
plate, Ø4 fixing screws at x 627.3 / 667.3, 42.2 mm below the plate, nut 8-10 mm inside) and four
Ø13 rear-panel holes at x 597.6 (10 / 30 / 50 / 70 mm below the plate; a panel fuse holder there
reaches 30-45 mm inside). The rear strip is therefore kept only for x 560-585.

Chassis frame (D748 top plate, mm): x along the front from the left, y from the front panel toward
the rear. The board hangs 15 mm under the plate, THT parts downward (about 66 mm), SMD on the
plate side. The PSU's cables: W01 (raw HV) assumed down the FRONT hole (658.5, 28.6), so J101 and
the fault-network standoff H101 sit at the front notch; the rear hole (658.5, 154.6) is left to the
mains wiring from the inlet, in a corner cut out of the board (x 649-675, y 145-180).

Bottom side: the big parts are placed by hand in power-flow order (raw in at the front notch, input
filter down the east column, bridge 1 in the front half, bridge 2 in the rear half, outputs on the
arm toward the power amp); the small parts are then packed first-fit into what is left. The arm's
front band (y 127-147) is kept free of bottom-side parts: the ribbon corridor for the control
board's J7 / J5 (rear edge, x 506-550). The main body's west 10 mm (x 560-570, y 30-127) and the
arm's front band carry no HV on the bottom side (control board DGND edge 5-8 mm away).

Run: python3 rev3/mechanical/floorplan_chosen.py
  writes floorplan_chosen.md, floorplan_chosen.svg, outline_edge_cuts.kicad_pcb
"""
import os

import numpy as np
from shapely.geometry import Polygon, box

HERE = os.path.dirname(os.path.abspath(__file__))
GAP = 2

OUTLINE = [(560, 30), (649, 30), (649, 39), (668, 39), (668, 30), (675, 30), (675, 145), (649, 145),
           (649, 180), (585, 180), (585, 200), (525, 200), (525, 127), (560, 127)]
CORRIDOR = (525, 127, 35, 20)          # ribbon corridor under the arm: no bottom-side parts
LV_STRIP = (560, 30, 10, 97)           # facing the control board: no HV on the bottom side
# mounting holes (x, y, plated, note)
HOLES = [(605.0, 124.7, False, "existing plate hole"),
         (671.0, 48.0, False, "new plate hole (under the PSU)"),
         (646.0, 140.0, False, "new plate hole (under the PSU), by the mains corner"),
         (550.0, 194.0, False, "new plate hole in the arm"),
         (566.0, 122.0, False, "new plate hole by J1 (replaces 590.0, 87.0, which falls under C201)"),
         (617.0, 50.0, True, "H101: new plate hole, plated, the fault / RF network standoff by J101 / FAULT")]

# bottom side, placed by hand: name, x0, y0, w, h, height below the board, group, note
FIXED = [
    ("J1", 562, 80, 7, 34, 15, "CTL", "SHF-120-01-L-D-TH, opposite J11 (y 84-110); ribbon 8 mm west"),
    ("J103", 572, 32, 24, 10, 20, "IN", "RAW_SS2 / GND_PRE2 to the PI + FX (W03), cable west in front of the control board"),
    ("J102", 598, 32, 24, 10, 20, "IN", "RAW_SS1 / GND_PRE1 to the preamp (W02)"),
    ("FAULT", 624, 32, 23, 23, 18, "IN", "GBU8J + 100 nF Y2 (P22.5) + 100 ohm 2 W; H101 just west"),
    ("J101", 651, 41, 10, 24, 20, "IN", "B_P / B_N raw HV in, W01 down the front hole"),
    ("C101", 653, 68, 20, 20, 40, "IN", "47 uF 500 V D18"),
    ("L101", 653, 90, 13, 13, 15, "IN", "33 uH 2 A"),
    ("BLD_RAW", 653, 106, 16, 22, 7, "IN", "R103 / R104 75 kohm 2 W + R105 / D101"),
    ("HS201_Q201", 570, 63, 35, 15, 51, "B1", "Q201 on SK 104 38.1 mm, insulated mounting (heatsink not live)"),
    ("Q202", 572, 80, 12, 6, 25, "B1", "TO-220 standing, no heatsink"),
    ("C201", 572, 93, 20, 20, 40, "B1", "47 uF 500 V D18 (bridge 1 input)"),
    ("L201", 607, 58, 42, 42, 42, "B1", "3 mH, ETD39 N87, 192 t 0.5 mm, gap ~1.9 mm, 0.8 W at 0.7 A"),
    ("C204", 612, 102, 24, 24, 45, "B1", "100 uF 500 V snap-in D22"),
    ("L202", 638, 102, 13, 13, 15, "B1", "33 uH 2 A"),
    ("C205", 606, 131, 33, 12, 22, "B1", "1 uF 630 V MKP"),
    ("L203", 562, 134, 42, 42, 42, "B2", "3 mH, ETD39"),
    ("C206", 563, 178, 20, 20, 40, "B2", "47 uF 500 V D18 (bridge 2 input), in the rear strip"),
    ("Q203_Q204", 606, 145, 26, 7, 25, "B2", "two TO-220 standing, no heatsink"),
    ("C209", 606, 154, 24, 24, 45, "B2", "100 uF 500 V snap-in D22"),
    ("C210", 634, 147, 12, 31, 22, "B2", "1 uF 630 V MKP"),
    ("J201", 527, 166, 10, 24, 20, "OUT", "V_ANODE / GND_PWR, toward the power amp (5.9 mm west)"),
    ("J202", 527, 150, 10, 10, 20, "OUT", "V_SCREEN"),
    ("J501", 562, 48, 7, 7, 12, "CTL", "HV_PERMIT KK-254 (W16 twisted pair from the power amp, along the control board's east edge)"),
]
# small parts, packed into what is left (bottom side)
PACK = [
    ("BLD_OUT", 26, 14, 5, "B", "R206 / R207 / R213 / R214 110 kohm 1 W output bleeders + R215 / D202", (570, 113, 606, 133)),
    ("LINKS", 24, 16, 7, "IN", "R101 / R102 RAW_SS links (0617)", (570, 42, 612, 62)),
    ("R201", 22, 7, 7, "B1", "bridge 1 input link footprint (0617, proposal N7); the 10x38 PV fuse would need about 50 x 12 mm", (592, 78, 607, 122)),
    ("R208", 22, 7, 7, "B2", "bridge 2 input link footprint", (525, 147, 560, 200)),
    ("D201", 20, 6, 6, "B", "1N5408", (525, 147, 560, 200)),
    ("L204", 13, 13, 15, "B2", "33 uH 2 A (bridge 2 second stage, next to its output)", (525, 147, 560, 200)),
    ("R205", 16, 5, 5, "B1", "1.0 ohm ULW2 fusible, next to J201", (525, 147, 560, 200)),
    ("R212", 16, 5, 5, "B2", "2.2 ohm ULW2 fusible, next to J202", (525, 147, 560, 200)),
    ("R204", 16, 5, 5, "B1", "5.6 ohm 1 W across L202", (630, 100, 652, 136)),
    ("R211", 16, 5, 5, "B2", "5.6 ohm 1 W across L204", (525, 147, 560, 200)),
]
# plate side (SMD, <= 3 mm): name, w, h, note
PLATE = [
    ("CTRL", 36, 30, "AD7689, 3 x MCP6004, 2 x LMV339, TLP293, logic, LM4040, ~100 0603: next to J1"),
    ("DIV", 26, 14, "4 HV dividers 3 x 1 Mohm 1206 + 15k"),
    ("DRV1", 16, 20, "U301 + bootstrap + gate resistors, above Q201 / Q202"),
    ("DRV2", 16, 20, "U302 + bootstrap, above Q203 / Q204"),
    ("SHUNTS", 20, 10, "R202 / R203 / R209 / R210 50 mohm 2512 Kelvin"),
    ("PROT", 20, 12, "R5xx thresholds, NT501, decoupling"),
    ("HVCAPS", 24, 8, "C102 / C202 / C207 100 nF 630 V and C103 / C203 / C208 1 nF 1 kV, 1812 / 1206, at the bridges' inputs"),
]


def raster(poly):
    W, H = 160, 180
    occ = np.ones((H, W), bool)
    for i in range(H):
        for j in range(W):
            if poly.contains(box(525 + j, 30 + i, 526 + j, 31 + i)):
                occ[i, j] = False
    return occ


def mark(occ, x, y, w, h, g=0):
    i0, j0 = max(int(y - 30) - g, 0), max(int(x - 525) - g, 0)
    occ[i0:int(y - 30 + h) + g, j0:int(x - 525 + w) + g] = True


def free(occ, i, j, w, h):
    H, W = occ.shape
    if i - GAP < 0 or j - GAP < 0 or i + h + GAP > H or j + w + GAP > W:
        return False
    return not occ[i - GAP:i + h + GAP, j - GAP:j + w + GAP].any()


def pack(occ, items):
    placed, missing = [], []
    for item in sorted(items, key=lambda b: -b[1] * b[2]):
        n, w, h, z, gr, note = item[:6]
        rest = (z, gr, note)
        zx0, zy0, zx1, zy1 = item[6] if len(item) > 6 else (525, 30, 685, 210)
        done = False
        for ww, hh in ((w, h), (h, w)):
            for i in range(occ.shape[0]):
                for j in range(occ.shape[1]):
                    x, y = 525 + j, 30 + i
                    if x < zx0 or y < zy0 or x + ww > zx1 or y + hh > zy1:
                        continue
                    if free(occ, i, j, ww, hh):
                        mark(occ, 525 + j, 30 + i, ww, hh)
                        placed.append((n, 525 + j, 30 + i, ww, hh, *rest))
                        done = True
                        break
                if done:
                    break
            if done:
                break
        if not done:
            missing.append(n)
    return placed, missing


def main():
    poly = Polygon(OUTLINE)
    errors = []
    # fixed parts: inside, no overlap (with GAP), not in the corridor, HV not in the LV strip
    boxes = []
    for n, x, y, w, h, z, gr, note in FIXED:
        b = box(x, y, x + w, y + h)
        if not poly.buffer(-GAP + 1e-6).contains(b):
            errors.append(f"{n} outside the outline or closer than {GAP} mm to the edge")
        if b.intersects(box(*CORRIDOR[:2], CORRIDOR[0] + CORRIDOR[2], CORRIDOR[1] + CORRIDOR[3])):
            errors.append(f"{n} in the ribbon corridor")
        if gr not in ("CTL",) and b.intersects(box(LV_STRIP[0], LV_STRIP[1], LV_STRIP[0] + LV_STRIP[2] - 1e-6,
                                                     LV_STRIP[1] + LV_STRIP[3])):
            errors.append(f"{n} (HV) in the LV strip facing the control board")
        for m, bb in boxes:
            if b.buffer(GAP - 1e-6).intersects(bb):
                errors.append(f"{n} overlaps {m}")
        for hx, hy, *_ in HOLES:
            if b.buffer(GAP).intersects(box(hx - 4, hy - 4, hx + 4, hy + 4)):
                errors.append(f"{n} on the standoff at ({hx}, {hy})")
        boxes.append((n, b))
    occ = raster(poly)
    for n, x, y, w, h, *_ in FIXED:
        mark(occ, x, y, w, h)
    for hx, hy, *_ in HOLES:
        mark(occ, hx - 4, hy - 4, 8, 8)
    mark(occ, *CORRIDOR)
    mark(occ, LV_STRIP[0], LV_STRIP[1], LV_STRIP[2], LV_STRIP[3])
    placed, missing = pack(occ, PACK)
    area = poly.area
    bottom_usable = area - CORRIDOR[2] * CORRIDOR[3] - 64 * len(HOLES)
    body = sum(w * h for _, _, _, w, h, *_ in FIXED) + sum(p[3] * p[4] for p in placed)
    # plate side: anything goes except the holes
    occ2 = raster(poly)
    for hx, hy, *_ in HOLES:
        mark(occ2, hx - 4, hy - 4, 8, 8)
    mark(occ2, 525, 127, 35, 4)        # nothing within 4 mm of the arm's front edge on the plate side either
    plate, pmiss = pack(occ2, [(n, w, h, 3, "CTL", note) for n, w, h, note in PLATE])
    print("errors:", errors, "missing:", missing, "plate missing:", pmiss)
    print(f"area {area:.0f} mm2, bottom usable {bottom_usable:.0f}, bottom bodies {body}, fill {body / bottom_usable * 100:.0f} %")

    with open(os.path.join(HERE, "floorplan_chosen.md"), "w") as f:
        f.write("# Chosen outline and floorplan (generated by floorplan_chosen.py)\n\n")
        f.write(f"Outline area {area:.0f} mm²; bottom side usable {bottom_usable:.0f} mm² (minus the ribbon corridor "
                f"and the standoffs); bottom-side bodies {body} mm² = **{body / bottom_usable * 100:.0f} % fill**. "
                f"Hand-placement check: {'clean' if not errors else '; '.join(errors)}. "
                f"Packed small parts not placed: {', '.join(missing) or 'none'}; plate side not placed: {', '.join(pmiss) or 'none'}.\n\n")
        f.write("Outline (chassis frame, mm, counter-clockwise from the front-west corner):\n\n`" +
                " ".join(f"({x}, {y})" for x, y in OUTLINE) + "`\n\n")
        f.write("| Side | Block | x (mm) | y (mm) | w x h (mm) | height (mm) | note |\n|---|---|---|---|---|---|---|\n")
        for n, x, y, w, h, z, gr, note in FIXED:
            f.write(f"| bottom (fixed) | {n} | {x} | {y} | {w} x {h} | {z} | {note} |\n")
        for n, x, y, w, h, z, gr, note in placed:
            f.write(f"| bottom (packed) | {n} | {x} | {y} | {w} x {h} | {z} | {note} |\n")
        for n, x, y, w, h, z, gr, note in plate:
            f.write(f"| plate side | {n} | {x} | {y} | {w} x {h} | ≤ 3 | {note} |\n")
        f.write("\n| Standoff | x | y | plated | note |\n|---|---|---|---|---|\n")
        for hx, hy, pl, note in HOLES:
            f.write(f"| | {hx} | {hy} | {'yes' if pl else 'no'} | {note} |\n")

    # SVG (view from above, front panel at the bottom of the picture)
    s = 4
    tx = lambda x: (x - 520) * s
    ty = lambda y: (205 - y) * s
    col = {"B1": "#d9822b", "B2": "#c9a227", "IN": "#c0392b", "OUT": "#8e44ad", "CTL": "#2e86c1", "B": "#7f8c8d"}
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{165 * s}" height="{185 * s}" font-family="sans-serif" font-size="9">',
         f'<rect width="{165 * s}" height="{185 * s}" fill="white"/>',
         '<polygon points="' + " ".join(f"{tx(x)},{ty(y)}" for x, y in OUTLINE) + '" fill="#eef5e9" stroke="#2d572c" stroke-width="2"/>']
    cx, cy, cw, ch = CORRIDOR
    o.append(f'<rect x="{tx(cx)}" y="{ty(cy + ch)}" width="{cw * s}" height="{ch * s}" fill="#ddd" stroke="#888" stroke-dasharray="4"/>'
             f'<text x="{tx(cx) + 3}" y="{ty(cy + ch / 2)}">ribbon corridor</text>')
    for hx, hy in ((658.5, 28.6), (658.5, 154.6)):
        o.append(f'<circle cx="{tx(hx)}" cy="{ty(hy)}" r="{7.5 * s}" fill="none" stroke="black" stroke-dasharray="3"/>')
    for hx, hy, pl, _ in HOLES:
        o.append(f'<circle cx="{tx(hx)}" cy="{ty(hy)}" r="{1.6 * s}" fill="{"#c0392b" if pl else "white"}" stroke="black"/>')
    for n, x, y, w, h, z, gr, note in list(FIXED) + placed:
        o.append(f'<rect x="{tx(x)}" y="{ty(y + h)}" width="{w * s}" height="{h * s}" fill="{col[gr]}" fill-opacity="0.55" stroke="black"/>'
                 f'<text x="{tx(x) + 2}" y="{ty(y + h) + 10}">{n}</text>')
    for n, x, y, w, h, *_ in plate:
        o.append(f'<rect x="{tx(x)}" y="{ty(y + h)}" width="{w * s}" height="{h * s}" fill="none" stroke="#2e86c1" stroke-dasharray="5"/>'
                 f'<text x="{tx(x) + 2}" y="{ty(y) - 3}" fill="#2e86c1">{n} (plate side)</text>')
    o.append(f'<text x="8" y="{185 * s - 8}">HV supplies rev 3, chosen floorplan, view from above (front panel at the bottom); dashed blue = plate side</text></svg>')
    open(os.path.join(HERE, "floorplan_chosen.svg"), "w").write("\n".join(o))

    # KiCad Edge.Cuts: origin at chassis (525, 30), x right, KiCad y = chassis y - 30 (toward the rear),
    # i.e. the board seen from the plate side with the front panel at the top of the screen
    pts = " ".join(f"(xy {x - 525} {y - 30})" for x, y in OUTLINE)
    holes = "".join(
        f'\t(gr_circle (center {hx - 525} {hy - 30}) (end {hx - 525 + 1.6} {hy - 30}) (stroke (width 0.1) (type solid)) '
        f'(fill no) (layer "Dwgs.User"))\n' for hx, hy, *_ in HOLES)
    open(os.path.join(HERE, "outline_edge_cuts.kicad_pcb"), "w").write(
        '(kicad_pcb\n\t(version 20260206)\n\t(generator "floorplan_chosen")\n\t(general (thickness 1.6))\n'
        '\t(paper "A4")\n\t(layers (0 "F.Cu" signal) (2 "B.Cu" signal) (25 "Edge.Cuts" user) (31 "Dwgs.User" user))\n'
        f'\t(gr_poly (pts {pts}) (stroke (width 0.1) (type solid)) (fill no) (layer "Edge.Cuts"))\n' + holes + ')\n')


if __name__ == "__main__":
    main()
