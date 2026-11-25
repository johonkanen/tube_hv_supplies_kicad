#!/usr/bin/env python3
"""rev4 block floorplan in chassis coordinates (D748 top-plate frame, mm, y up, front panel at y = 0),
seen from above through the plate. The board hangs 15 mm below the plate, components down: the big
THT parts are on the downward face, small-signal SMD may go on the plate face (<= 3 mm).

Checks that the big parts fit a ~115 x 88 mm rectangle, with the four TO-220s standing on the east edge
and their tabs on the chassis east wall (PLAN.md D10-D12). Writes floorplan.png next to this file.
"""
import itertools
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))

BOARD = (562.0, 39.0, 677.0, 127.0)      # x0, y0, x1, y1 (115 x 88 mm)
WALL_X = 678.0                           # inner face of the east wall: ASSUMED (680 plate, 2 mm wall); measure
HOLES = [(566.0, 43.0), (566.0, 123.0), (668.0, 42.5), (668.0, 123.5)]  # M3 standoffs, placeholders

# neighbours (ICD 12.1 / rev3 layout sketch)
CTRL = (426.0, 30.0, 552.0, 122.0)
J11 = (548.5, 84.0, 551.0, 109.6)
PA = (280.0, 127.0, 519.1, 187.0)
PA_TABS = [("V_SCREEN", 512.0, 155.0), ("V_ANODE", 512.0, 170.0), ("GND_PWR", 512.0, 182.0)]
PSU = (567.0, 24.0, 677.0, 186.0)        # tube PSU on top of the plate
PSU_HOLES = [(658.5, 28.6), (658.5, 154.6)]

# big parts on the downward face: name, kind, geometry, group
# TO-220 standing, tab on the wall: plan size 4.5 (body thickness, x) x 10.2 (y); leads at about x 675.3
TO = 4.5
def to220(name, yc):
    return (name, "rect", (WALL_X - 0.3 - TO, yc - 5.1, WALL_X - 0.3, yc + 5.1), "bridge")
def tab(name, x, y):            # 4.8 mm blade + fully insulated receptacle, plan 8 x 7 mm
    return (name, "rect", (x - 4.0, y - 3.5, x + 4.0, y + 3.5), "tab")
def cap(name, x, y, d=16.0):    # 450 V electrolytic, standing
    return (name, "circle", (x, y, d / 2), "cap")
def ind10(name, x, y):          # SRP1038 class, 10 x 10
    return (name, "rect", (x - 5.5, y - 5.5, x + 5.5, y + 5.5), "ind")
def film(name, x0, y0, w, h):  # box film capacitor, plan w x h (MKP1848C 500 V class; check the datasheet)
    return (name, "rect", (x0, y0, x0 + w, y0 + h), "film")
def ind(name, x, y, a):         # 100 uH, about 13 x 13 (part to choose)
    return (name, "rect", (x - a / 2, y - a / 2, x + a / 2, y + a / 2), "ind")
def toroid(name, x, y):         # 2 mH toroid standing on edge: 32 mm diameter along y, 16.4 thick along x
    return (name, "rect", (x - 8.7, y - 16.5, x + 8.7, y + 16.5), "toroid")

PARTS = [
    # bridges: bridge 2 (V_SCREEN) at the front, bridge 1 (V_ANODE) at the rear, high sides in the middle
    to220("QL2", 52.0), to220("QH2", 66.0), to220("QH1", 100.0), to220("QL1", 114.0),
    cap("C_in_hs", 664.0, 83.0, 16.0),              # input cap between the two high-side collectors
    # raw input at the front-east corner, under the PSU's front cable hole
    tab("B_N", 648.0, 44.0), tab("B_P", 660.0, 44.0),
    cap("C_in1", 630.0, 47.5), ind10("L_in", 616.0, 46.0),
    # main inductors standing in the middle
    toroid("L_main2", 645.0, 73.0), toroid("L_main1", 645.0, 109.0),
    # filter variant D (sim/ripple.py) per output: first stage 47 uF el + 4.7 uF film (I_C shunt on the plate
    # face under them), L2 100 uH, output 10 uF film + damping leg 22 uF el + 2.2 ohm
    # bridge 1 (V_ANODE), rear half
    cap("C1_1 47u", 613.0, 110.0), film("F1_1 5u", 571.0, 85.0, 32.0, 11.0),
    ind("L2_1 100u", 612.0, 92.0, 13.0), film("F2_1 10u", 571.0, 100.0, 32.0, 18.0),
    cap("Cd_1 22u", 628.0, 96.0, 12.5),
    # bridge 2 (V_SCREEN), front half
    cap("C1_2 47u", 613.0, 75.0), film("F1_2 5u", 571.0, 69.0, 32.0, 11.0),
    ind("L2_2 100u", 612.0, 59.0, 13.0), film("F2_2 10u", 571.0, 49.0, 32.0, 18.0),
    cap("Cd_2 22u", 628.0, 64.0, 12.5),
    # output tabs at the rear-west corner, toward the power amp (its tabs at x 512, y 155-182)
    tab("V_SCREEN", 600.0, 123.0), tab("V_ANODE", 588.0, 123.0), tab("GND_PWR", 576.0, 123.0),
    # RAW_SS feeds at the front-west edge (cables forward, then west in front of the control board)
    tab("RAW_SS2", 574.5, 43.5), tab("GND_PRE2", 584.5, 43.5),
    tab("RAW_SS1", 594.5, 43.5), tab("GND_PRE1", 604.5, 43.5),
    # J1 on the west edge facing J11; W16 next to it
    ("J1 (W17)", "rect", (564.0, 81.0, 569.3, 112.0), "conn"),
    ("J501 (W16)", "rect", (564.0, 56.0, 569.8, 61.5), "conn"),
]
# plate-face (SMD) zones: drawn hatched, not overlap-checked against the down face
PLATE_ZONES = [
    ("gate drivers, bootstrap,\nlow-side shunts + amps", (650.0, 49.0, 672.5, 117.0)),
    ("measurement: 2 x mux + ADS7056,\nREF3030, dividers, buffers", (571.0, 80.0, 606.0, 96.0)),
]
COLORS = {"bridge": "#7b241c", "tab": "#b9770e", "cap": "#2874a6", "ind": "#7d3c98", "toroid": "#af601a",
          "conn": "#148f77", "film": "#1e8449"}


def bbox(p):
    _, kind, g, _ = p
    if kind == "circle":
        x, y, r = g
        return (x - r, y - r, x + r, y + r)
    return g


def overlap(a, b, gap=0.5):
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1])


def main():
    x0, y0, x1, y1 = BOARD
    problems = []
    for p in PARTS:
        bx = bbox(p)
        # the TO-220s may stand past the board edge toward the wall (their leads are inside)
        if p[3] != "bridge" and (bx[0] < x0 or bx[1] < y0 or bx[2] > x1 or bx[3] > y1):
            problems.append(f"{p[0]} outside the board")
    for hx, hy in HOLES:   # M3 head / standoff keep-out, 6.5 mm
        for p in PARTS:
            if overlap(bbox(p), (hx - 3.25, hy - 3.25, hx + 3.25, hy + 3.25), 0):
                problems.append(f"hole ({hx}, {hy}) under {p[0]}")
    for a, b in itertools.combinations(PARTS, 2):
        if overlap(bbox(a), bbox(b)):
            problems.append(f"{a[0]} overlaps {b[0]}")

    fig, ax = plt.subplots(figsize=(13, 8.5))
    for (rx0, ry0, rx1, ry1), lab, col in ((CTRL, "control board", "#2e86c1"), (PA, "power amp", "#c0392b")):
        ax.add_patch(Rectangle((rx0, ry0), rx1 - rx0, ry1 - ry0, fc=col, alpha=0.08, ec=col))
        ax.text(max(rx0, 500) + 2, ry0 + 3, lab, color=col, fontsize=8)
    ax.add_patch(Rectangle((J11[0], J11[1]), J11[2] - J11[0], J11[3] - J11[1], color="#2e86c1"))
    ax.text(J11[0] - 1, J11[3] + 1.5, "J11", color="#2e86c1", fontsize=7, ha="right")
    ax.add_patch(Rectangle((PSU[0], PSU[1]), PSU[2] - PSU[0], PSU[3] - PSU[1], fill=False, ls=":", ec="grey"))
    ax.text(PSU[0] + 1, PSU[3] - 4, "tube PSU on top of the plate", color="grey", fontsize=7)
    for hx, hy in PSU_HOLES:
        ax.add_patch(Circle((hx, hy), 7.5, fill=False, ec="grey", ls="--"))
    for n, x, y in PA_TABS:
        ax.add_patch(Rectangle((x - 3.5, y - 4), 7, 8, color=COLORS["tab"], alpha=0.5))
        ax.text(x - 5, y, n, fontsize=6, ha="right", va="center")
    ax.axvline(WALL_X, color="k", lw=3)
    ax.text(WALL_X + 0.8, 70, "east wall\n(inner face\nassumed x 678)", fontsize=7, va="center")
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=2))
    ax.text(x0, y1 + 1.5, f"rev4 board {x1 - x0:.0f} x {y1 - y0:.0f} mm (x {x0:.0f}-{x1:.0f}, y {y0:.0f}-{y1:.0f})",
            fontsize=9, weight="bold")
    for lab, (zx0, zy0, zx1, zy1) in PLATE_ZONES:
        ax.add_patch(Rectangle((zx0, zy0), zx1 - zx0, zy1 - zy0, fill=False, hatch="///", ec="#999999", lw=0.6))
        ax.text((zx0 + zx1) / 2, zy0 - 1.2, lab + " (plate face)", fontsize=5.5, ha="center", va="top",
                color="#555555")
    for p in PARTS:
        name, kind, g, grp = p
        col = COLORS[grp]
        if kind == "circle":
            ax.add_patch(Circle(g[:2], g[2], fc=col, alpha=0.35, ec=col))
            cx, cy = g[:2]
        else:
            ax.add_patch(Rectangle((g[0], g[1]), g[2] - g[0], g[3] - g[1], fc=col, alpha=0.35, ec=col))
            cx, cy = (g[0] + g[2]) / 2, (g[1] + g[3]) / 2
        ax.text(cx, cy, name, fontsize=6, ha="center", va="center", rotation=90 if grp == "bridge" else 0)
    for hx, hy in HOLES:
        ax.add_patch(Circle((hx, hy), 1.6, fc="white", ec="k"))
    # cable directions
    ax.annotate("", xy=(654, 47.5), xytext=(658.5, 28.6), arrowprops=dict(arrowstyle="->", color=COLORS["tab"]))
    ax.text(661, 33, "W01 from the PSU\nfront hole", fontsize=6.5, color=COLORS["tab"])
    ax.annotate("", xy=(540, 30), xytext=(586, 40), arrowprops=dict(arrowstyle="->", color="#cb4335"))
    ax.text(540, 33, "W02 / W03 to preamp, PI + FX", fontsize=6.5, color="#cb4335")
    ax.annotate("", xy=(516, 165), xytext=(588, 127), arrowprops=dict(arrowstyle="->", color="#7b241c"))
    ax.text(545, 150, "W04 / W05 to the power amp", fontsize=6.5, color="#7b241c")
    ax.set_xlim(505, 690)
    ax.set_ylim(15, 190)
    ax.set_aspect("equal")
    ax.grid(alpha=0.15)
    ax.set_title("rev4 block floorplan, chassis mm, seen from above (big parts on the downward face)")
    if problems:
        ax.text(506, 186, "PROBLEMS: " + "; ".join(problems), color="red", fontsize=7, va="top", wrap=True)
    out = os.path.join(HERE, "floorplan.png")
    plt.tight_layout()
    plt.savefig(out, dpi=130)
    area = (x1 - x0) * (y1 - y0)
    used = sum((bbox(p)[2] - bbox(p)[0]) * (bbox(p)[3] - bbox(p)[1]) for p in PARTS)
    print(f"board {area / 100:.1f} cm2, big-part bounding boxes {used / 100:.1f} cm2 ({100 * used / area:.0f} %)")
    print("problems:", problems or "none")


if __name__ == "__main__":
    main()
