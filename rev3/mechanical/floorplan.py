#!/usr/bin/env python3
"""HV supplies rev 3: block-level floorplan in the D748 top-plate frame (interfaces.md 12.1:
x 560-675, y 30-180, 115 x 150 mm, numbers PROPOSED; components down, about 66 mm free below).

Every block is a rectangle with the real body size of its part(s) plus about 1 mm of courtyard;
blocks keep GAP mm from each other and from the board edge (creepage at 430 V is 2.5 mm between
HV and low-voltage copper: the gap is between bodies, the copper sits inside). The connectors,
the plated fault-network standoff and the mounting holes are placed by hand (they follow the
neighbours); the rest is packed first-fit, largest first, on a 1 mm grid. The packer ignores
electrical adjacency, so a pass here is a necessary condition for a layout, not a layout: a real
power layout needs about 1.3-1.5 times the body area (loops, creepage, routing).

Outlines tried:
  base   x 560-675, y 30-180, front notch and rear slot for the PSU's cable holes
  ext    base + x 560-632, y 180-200 (the rear strip, clear of the mains inlet at x 634-661 from
         y 185; the IF-1 envelope went to y 202)
  extL   ext + x 525-560, y 127-200 (an L behind the control board, which ends at y 122; the
         power amp is about 41 mm west of x 560, so about 6 mm stay; needs the coordinating
         session's fit check)
and each with the SMD control / measurement block on the top (plate) side instead of the bottom.

Run: python3 rev3/mechanical/floorplan.py   (writes floorplan.md and floorplan_<case>.svg)
"""
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GAP = 2
X0, Y0 = 525, 30

# name, w, h, height below the board (mm), group, note
BLOCKS = [
    ("HS201_Q201", 35, 15, 51, "B1", "IKP08N65F5 on Fischer SK 104 38.1 mm (35 x 13 mm, ~12 K/W), live at the tab"),
    ("HS_Q202", 35, 15, 51, "B1", "IKP08N65F5 on SK 104"),
    ("HS_Q203", 35, 15, 51, "B2", "IKP08N65F5 on SK 104 (may be omitted at 50 kHz)"),
    ("HS_Q204", 35, 15, 51, "B2", "IKP08N65F5 on SK 104 (may be omitted at 50 kHz)"),
    ("L201", 38, 38, 36, "B1", "3 mH / 2.4 A sat, ETD34 gapped N87 (placeholder)"),
    ("L203", 38, 38, 36, "B2", "3 mH / 2.4 A sat, ETD34"),
    ("C201", 20, 20, 40, "B1", "47 uF 500 V radial D18 (bridge 1 input)"),
    ("C206", 20, 20, 40, "B2", "47 uF 500 V D18 (bridge 2 input)"),
    ("C204", 20, 20, 40, "B1", "47 uF 500 V D18 (intermediate)"),
    ("C204b", 20, 20, 40, "B1", "47 uF 500 V D18 (intermediate)"),
    ("C209", 20, 20, 40, "B2", "47 uF 500 V D18"),
    ("C209b", 20, 20, 40, "B2", "47 uF 500 V D18"),
    ("C101", 20, 20, 40, "IN", "47 uF 500 V D18 (B_P, input filter)"),
    ("C205", 33, 12, 22, "B1", "1 uF 630 V MKP, P27.5"),
    ("C210", 33, 12, 22, "B2", "1 uF 630 V MKP, P27.5"),
    ("C102", 19, 7, 16, "IN", "100 nF 630 V film P15"),
    ("C202", 19, 7, 16, "B1", "100 nF 630 V film P15"),
    ("C207", 19, 7, 16, "B2", "100 nF 630 V film P15"),
    ("L101", 13, 13, 15, "IN", "33 uH 2 A radial D12"),
    ("L202", 13, 13, 15, "B1", "33 uH 2 A radial D12"),
    ("L204", 13, 13, 15, "B2", "33 uH 2 A radial D12"),
    ("F201", 26, 8, 12, "B1", "5x20 clip holder (fuse >= 500 VDC, TBD)"),
    ("F202", 26, 8, 12, "B2", "5x20 clip holder"),
    ("R204", 22, 7, 7, "B1", "2.2 ohm 2 W fusible, axial 0617"),
    ("R210", 22, 7, 7, "B2", "2.2 ohm 2 W fusible"),
    ("R203", 16, 5, 5, "B1", "5.6 ohm 1 W damping, axial 0414"),
    ("R209", 16, 5, 5, "B2", "5.6 ohm 1 W damping"),
    ("BLD_OUT", 34, 12, 5, "B", "4 x 110 kohm 1 W output bleeders + V_ANODE LED string"),
    ("BLD_RAW", 24, 16, 7, "IN", "2 x 75 kohm 2 W raw bleeder + 1 Mohm / LED"),
    ("LINKS", 24, 16, 7, "IN", "R101 / R102 RAW_SS links, axial 0617 (0 ohm or 10-47 ohm 2 W fusible)"),
    ("D201", 20, 6, 6, "B", "1N5408 clamp V_SCREEN <= V_ANODE"),
    ("SHUNTS", 20, 10, 2, "B", "4 x 50 mohm 2512, Kelvin"),
    ("DRV1", 16, 20, 3, "B1", "UCC21520DW + bootstrap, gate resistors (SMD)"),
    ("DRV2", 16, 20, 3, "B2", "UCC21520DW + bootstrap (SMD)"),
    ("DIV", 26, 14, 2, "CTL", "4 HV dividers 3 x 1 Mohm 1206 + 15k (SMD, creepage)"),
    ("CTRL", 36, 30, 3, "CTL", "AD7689, 3 x MCP6004, 2 x LMV339, TLP293, logic, LM4040, ~100 0603 (SMD)"),
]
# fixed: name, x, y, w, h, height, group, note (chassis coordinates of the lower-left corner)
FIXED = [
    ("J1", 561, 80, 7, 34, 15, "CTL", "IDC 1.27 mm 2x20 shrouded, mated socket ~15 mm; opposite J11 (y 84-110)"),
    ("J501", 561, 117, 7, 7, 12, "CTL", "HV_PERMIT KK-254 2-pin"),
    ("J201", 561, 132, 10, 20, 20, "OUT", "V_ANODE / GND_PWR 4.8 mm tabs, toward the power amp (west)"),
    ("J202", 561, 154, 10, 10, 20, "OUT", "V_SCREEN 4.8 mm tab"),
    ("J101", 637, 156, 10, 20, 20, "IN", "B_P / B_N raw HV in, next to the rear cable slot"),
    ("J102", 615, 168, 20, 10, 20, "IN", "RAW_SS1 / GND_PRE1 (W02)"),
    ("J103", 593, 168, 20, 10, 20, "IN", "RAW_SS2 / GND_PRE2 (W03)"),
    ("FAULT", 614, 144, 22, 22, 18, "IN", "GBU8J + 100 nF Y2 + 100 ohm 2 W + plated standoff H101"),
]
# reduced part set (second-pass choice, see README): f_sw 50 kHz, so only Q201 (1.4 W) needs a
# heatsink; Q202 / Q203 / Q204 (0.3-0.6 W) stand free (TO-220 62 K/W: Tj about 100-110 C at 70 C);
# one 100 uF 500 V D22 per bridge instead of two 47 uF.
REDUCE_DROP = {"HS_Q202", "HS_Q203", "HS_Q204", "C204b", "C209b"}
REDUCE_ADD = [
    ("Q_FREE", 36, 7, 25, "B", "Q202, Q203, Q204 standing TO-220, no heatsink (3 x 10.5 x 4.6 mm + clearance)"),
]
REDUCE_RESIZE = {"C204": (24, 24, 45, "100 uF 500 V radial D22 (intermediate, bridge 1)"),
                 "C209": (24, 24, 45, "100 uF 500 V radial D22 (intermediate, bridge 2)")}
HOLES = [(590.0, 87.0), (605.0, 124.7), (605.0, 166.6), (671.0, 48.0), (671.0, 128.0)]   # H102-H106, non-plated
KEEPOUT = [("notch", 649, 30, 19, 9), ("slot", 649, 145, 19, 35)]


def outline(ext):
    """ext: 0 = base, 1 = + rear strip, 2 = + rear strip + L behind the control board."""
    W, H = 150, 170
    occ = np.ones((H, W), bool)                  # True = not available
    occ[0:150, 35:150] = False
    if ext >= 1:
        occ[150:170, 35:107] = False
    if ext >= 2:
        occ[97:170, 0:35] = False
    return occ


def mark(occ, x, y, w, h, g=0):
    i0, j0 = max(int(y - Y0) - g, 0), max(int(x - X0) - g, 0)
    occ[i0:int(y - Y0 + h) + g, j0:int(x - X0 + w) + g] = True


def free(occ, i, j, w, h):
    H, W = occ.shape
    if i - GAP < 0 or j - GAP < 0 or i + h + GAP > H or j + w + GAP > W:
        return False
    return not occ[i - GAP:i + h + GAP, j - GAP:j + w + GAP].any()


def blocks(reduced):
    if not reduced:
        return list(BLOCKS)
    out = []
    for b in BLOCKS:
        if b[0] in REDUCE_DROP:
            continue
        if b[0] in REDUCE_RESIZE:
            w, h, z, note = REDUCE_RESIZE[b[0]]
            b = (b[0], w, h, z, b[4], note)
        out.append(b)
    return out + REDUCE_ADD


def pack(ext, ctl_top, reduced=False):
    occ = outline(ext)
    for _, x, y, w, h in KEEPOUT:
        mark(occ, x, y, w, h)
    for hx, hy in HOLES:
        mark(occ, hx - 4, hy - 4, 8, 8)
    placed = [(n, x, y, w, h, z, gr, note) for n, x, y, w, h, z, gr, note in FIXED]
    for n, x, y, w, h, *_ in FIXED:
        mark(occ, x, y, w, h)
    todo = [b for b in blocks(reduced) if not (ctl_top and b[4] == "CTL")]
    todo.sort(key=lambda b: -b[1] * b[2])
    missing = []
    for n, w, h, z, gr, note in todo:
        done = False
        for ww, hh in ((w, h), (h, w)):
            H, W = occ.shape
            for i in range(H):
                for j in range(W):
                    if free(occ, i, j, ww, hh):
                        mark(occ, X0 + j, Y0 + i, ww, hh)
                        placed.append((n, X0 + j, Y0 + i, ww, hh, z, gr, note))
                        done = True
                        break
                if done:
                    break
            if done:
                break
        if not done:
            missing.append(n)
    usable = int((~outline(ext)).sum()) - sum(w * h for _, _, _, w, h in KEEPOUT) - 64 * len(HOLES)
    body = sum(w * h for n, _, _, w, h, *_ in placed) + sum(b[1] * b[2] for b in blocks(reduced) if b[0] in missing)
    return placed, missing, usable, body


COL = {"B1": "#d9822b", "B2": "#c9a227", "IN": "#c0392b", "OUT": "#8e44ad", "CTL": "#2e86c1", "B": "#7f8c8d"}


def svg(case, placed, ext):
    s = 4
    W, H = 160 * s, 182 * s
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="sans-serif" font-size="9">',
         f'<rect width="{W}" height="{H}" fill="white"/>']
    tx = lambda x: (x - X0 + 5) * s
    ty = lambda y: (y - Y0 + 5) * s
    pts = [(560, 30), (675, 30), (675, 180)] + ([(632, 180), (632, 200)] if ext else []) + \
        ([(525, 200), (525, 127), (560, 127)] if ext >= 2 else [(560, 200)] if ext else [(560, 180)])
    o.append('<polygon points="' + " ".join(f"{tx(x)},{ty(y)}" for x, y in pts) + '" fill="#eef5e9" stroke="#2d572c" stroke-width="2"/>')
    for n, x, y, w, h in KEEPOUT:
        o.append(f'<rect x="{tx(x)}" y="{ty(y)}" width="{w * s}" height="{h * s}" fill="white" stroke="#2d572c" stroke-dasharray="4"/>')
    for cx, cy in ((658.5, 28.6), (658.5, 154.6)):
        o.append(f'<circle cx="{tx(cx)}" cy="{ty(cy)}" r="{7.5 * s}" fill="none" stroke="black" stroke-dasharray="3"/>')
    for hx, hy in HOLES:
        o.append(f'<circle cx="{tx(hx)}" cy="{ty(hy)}" r="{1.6 * s}" fill="white" stroke="black"/>')
    for n, x, y, w, h, z, gr, note in placed:
        o.append(f'<rect x="{tx(x)}" y="{ty(y)}" width="{w * s}" height="{h * s}" fill="{COL[gr]}" fill-opacity="0.55" stroke="black"/>'
                 f'<text x="{tx(x) + 2}" y="{ty(y) + 10}">{n}</text>')
    o.append(f'<text x="8" y="{H - 8}">HV supplies rev 3, {case}: chassis frame (x right, y toward the rear panel), view from above</text>')
    o.append("</svg>")
    with open(os.path.join(HERE, f"floorplan_{case}.svg"), "w") as f:
        f.write("\n".join(o))


def main():
    rows = []
    best = None
    for red in (False, True):
      for ext in (0, 1, 2):
        for top in (False, True):
            case = ("base", "ext", "extL")[ext] + ("_ctltop" if top else "") + ("_reduced" if red else "")
            placed, missing, usable, body = pack(ext, top, red)
            rows.append((case, usable, body, missing))
            svg(case, placed, ext)
            if not missing and (best is None or ("reduced" in case and "reduced" not in best[0])):
                best = (case, placed)
            print(case, usable, body, missing)
    with open(os.path.join(HERE, "floorplan.md"), "w") as f:
        f.write("# Block floorplan (generated by floorplan.py)\n\n")
        f.write("| Case | usable bottom area (mm2) | block area on the bottom (mm2) | fill | blocks that did not fit |\n|---|---|---|---|---|\n")
        for case, usable, body, missing in rows:
            f.write(f"| {case} | {usable} | {body} | {body / usable * 100:.0f} % | {', '.join(missing) or 'none'} |\n")
        if best:
            f.write(f"\nCase listed below: **{best[0]}** (floorplan_{best[0]}.svg).\n\n")
            f.write("| Block | x (mm) | y (mm) | w x h (mm) | height below the board (mm) | note |\n|---|---|---|---|---|---|\n")
            for n, x, y, w, h, z, gr, note in sorted(best[1], key=lambda r: (r[2], r[1])):
                f.write(f"| {n} | {x} | {y} | {w} x {h} | {z} | {note} |\n")


if __name__ == "__main__":
    main()
