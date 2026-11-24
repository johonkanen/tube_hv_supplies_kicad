#!/usr/bin/env python3
"""HV supplies rev 3: layout sketch, interfaces only (2026-11-24).

First step of the layout: every connector and tab that leaves the board, at its intended position with its real
footprint, the cables to the mating boards and their routes, the block zones (rectangles only), the keep-outs in
both directions. No detailed placement, no routing. Chassis frame (D748 top plate, mm): x along the front from the
left, y from the front panel's inner face toward the rear; drawn as seen from above (front panel at the bottom).
The board hangs 15 mm under the plate with its THT parts down; tabs and headers are on the downward face.

Inputs: floorplan_chosen.py (outline, standoffs, bars, plate holes, block positions), tube_amplifier_kicad
docs/interfaces.md 2.1, 4, 5, 12.1-12.4 and mechanical/chassis_fit.md (other boards, chassis features).

Run: python3 rev3/mechanical/layout_sketch.py   -> layout_sketch.png (board and its edges), layout_sketch_routes.png
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
from matplotlib.patches import Circle, Polygon as MPoly, Rectangle   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import floorplan_chosen as fp                         # noqa: E402

# ---------------------------------------------------------------------------------------------------------------
# connectors and tabs that leave the board (chassis mm). Blade tab: 4.8 mm, 2 legs on 5.00 mm, 1.4 mm drill
# (Blade_Tab_4.8mm_2x_P12mm / _1x); "legs" = axis of the two legs = the blade's width direction. RCPT = plan
# outline of a fully insulated 4.8 mm receptacle on the tab (8 mm along the blade width x 7 mm), hanging down.
RCPT = (8.0, 7.0)
TABS = [
    # ref, cable, pin, net, x, y, legs axis
    ("J101", "W01", 1, "B_P", 656.0, 59.0, "x"),
    ("J101", "W01", 2, "B_N", 656.0, 47.0, "x"),
    ("J102", "W02", 1, "RAW_SS1", 604.0, 37.0, "y"),
    ("J102", "W02", 2, "GND_PRE1", 616.0, 37.0, "y"),
    ("J103", "W03", 1, "RAW_SS2", 578.0, 37.0, "y"),
    ("J103", "W03", 2, "GND_PRE2", 590.0, 37.0, "y"),
    ("J201", "W04", 1, "V_ANODE", 531.5, 170.0, "x"),
    ("J201", "W04", 2, "GND_PWR", 531.5, 182.0, "x"),
    ("J202", "W05", 1, "V_SCREEN", 531.5, 155.0, "x"),
]
# J1 (W17): J11 moved 16 mm east, same rotation; Samtec SHF-120-01-L-D-TH, shroud about 5.3 x 31 mm
J1_PIN1, J1_PIN2, J1_PIN39, J1_PIN40 = (566.37, 108.86), (565.10, 108.86), (566.37, 84.73), (565.10, 84.73)
J1_SHROUD = (563.07, 81.3, 5.33, 31.0)
# J501 (W16): Molex KK-254 2-pin vertical (housing about 5.1 x 5.8 mm); option A as floorplanned, B proposed
J501_A = ((565.5, 50.0), (565.5, 52.54))
J501_B = ((572.5, 117.5), (575.04, 117.5))

# mating-board positions (proposed windows unless the board has laid them out)
PA_TABS = [("V_SCREEN", 512.0, 155.0), ("V_ANODE", 512.0, 170.0), ("GND_PWR", 512.0, 182.0)]
PA_WINDOW = (503.0, 148.0, 13.0, 38.5)        # power amp east end: blade centres x 503-516, y 148-186.5
PRE_J501 = [("BP_RAW (1)", 356.8, 81.0), ("GND (2)", 371.8, 81.0)]   # preamp layout 6d22ff2 / b953ca3
PIFX_WINDOW = (250.0, 106.0, 26.0, 14.0)      # preferred: front-east corner
PIFX_WINDOW2 = (255.0, 125.0, 21.0, 25.0)     # second: east end behind P-J_PR_*
PIFX_TABS = [("BP_RAW", 270.0, 113.0), ("GND", 258.0, 113.0)]

# other boards and chassis features (interfaces.md 12.1, chassis_fit.md, 12.4)
CTRL = (426, 30, 126, 92)
PA = (280, 127, 239.1, 60)
PIFX = (53, 104, 226, 72)
PRE = (3, 16, 383, 72)
PSU = (567, 24, 110, 162)
FRONT_BOARD = (50, 2, 510, 12)
REAR_IO = (160, 179.7, 162, 30.3)
PSU_HOLES = [(658.5, 28.6), (658.5, 154.6)]
OT_HOLE = (415.5, 90.1)
INLET = (633.6, 185.0, 27.5, 23.0)
CTRL_HDR = {  # control board headers (12.4): name, x0, y0, x1, y1
    "J11": (548.5, 84.0, 551.0, 109.6), "J1 (W10)": (544.5, 58.5, 548.5, 80.5), "J8 (W18)": (547.0, 40.5, 550.0, 55.0),
    "J5 (W15)": (510.5, 115.0, 522.0, 119.0), "J7 (W19)": (533.5, 115.0, 545.0, 119.0),
    "J6 (W33)": (500.0, 33.0, 537.2, 37.0), "J2 (W12)": (442.5, 33.0, 459.2, 37.0), "J4 (W14)": (483.5, 115.0, 500.2, 119.0),
    "J3 (W13)": (429.0, 82.5, 433.0, 99.0), "J9 RJ45": (444.0, 104.0, 466.0, 122.0),
}
CTRL_STANDOFFS = [(432.0, 36.0), (546.0, 36.0), (437.7, 108.2), (437.8, 65.3), (475.0, 111.5), (507.5, 50.0), (535.6, 103.8)]

# block zones (rectangles only): name, x0, y0, x1, y1, side, colour
ZONES = [
    ("RAW IN filter", 650, 40, 674, 129, "b", "#e8a33d"),
    ("STAR + FAULT / RF (GBU8J, Y2, 100R), H101", 612, 32, 648, 57, "b", "#c0392b"),
    ("bridge 1 (C201, C211, links; Q201/Q202 leads y 81)", 570, 77, 611, 128, "b", "#d35400"),
    ("L201 220 uH", 607, 58, 649, 100, "b", "#7d3c98"),
    ("bridge-1 filter (C204, L202, C212, C205)", 570, 44, 607, 77, "b", "#2471a3"),
    ("", 612, 100, 655, 144, "b", "#2471a3"),
    ("L203 470 uH", 562, 134, 604, 176, "b", "#7d3c98"),
    ("bridge 2 (C206, C209, C210)", 604, 127, 648, 179, "b", "#d35400"),
    ("bridge-2 filter + outputs (L204, C216, D201)", 527, 148, 560, 199, "b", "#2471a3"),
    ("CTRL", 562, 80, 592, 116, "p", "#1abc9c"),
    ("FASTADC", 572, 118, 602, 136, "p", "#1abc9c"),
]


def rect(ax, x0, y0, w, h, **kw):
    ax.add_patch(Rectangle((x0, y0), w, h, **kw))


def draw_outline(ax, lw=1.6):
    ax.add_patch(MPoly(fp.OUTLINE, closed=True, fill=True, fc="#f4f6f7", ec="black", lw=lw, zorder=1))


def tab_rect(x, y, legs):
    w, h = RCPT if legs == "x" else RCPT[::-1]
    return x - w / 2, y - h / 2, w, h


def arrow(ax, pts, color, lw=1.6, ls="-", head=True, z=6):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, lw=lw, ls=ls, zorder=z, solid_capstyle="round")
    if head:
        ax.annotate("", xy=pts[-1], xytext=pts[-2], zorder=z,
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=12))


def detail():
    fig, ax = plt.subplots(figsize=(15, 16.5))
    ax.set_xlim(500, 690)
    ax.set_ylim(-4, 216)
    ax.set_aspect("equal")
    ax.set_facecolor("white")
    # chassis walls
    ax.axhline(0, color="k", lw=3)
    ax.axhline(210, color="k", lw=3)
    ax.axvline(680, color="k", lw=3)
    ax.text(505, 1.5, "front panel inner face (y 0)", fontsize=8)
    ax.text(505, 211.5, "rear panel (y 210)", fontsize=8)
    # tube PSU on top
    rect(ax, PSU[0], PSU[1], PSU[2], PSU[3], fill=False, ec="#7f8c8d", lw=1.2, ls=(0, (6, 3)), zorder=2)
    ax.text(569, 25.5, "tube PSU 5.2 on top of the plate (x 567-677, y 24-186)", fontsize=7, color="#7f8c8d")
    # other boards
    rect(ax, *CTRL, fc="#eaf2f8", ec="#2e86c1", lw=1.2, zorder=1)
    ax.text(503, 92, "control board\n(x 426-552, y 30-122)", fontsize=8, color="#2e86c1")
    rect(ax, *PA, fc="#fdedec", ec="#c0392b", lw=1.2, zorder=1)
    ax.text(503, 129, "power amp\n(x 280-519.1,\ny 127-187)", fontsize=8, color="#c0392b")
    rect(ax, FRONT_BOARD[0], FRONT_BOARD[1], FRONT_BOARD[2], FRONT_BOARD[3], fc="#f5eef8", ec="#8e44ad", lw=1, zorder=1)
    ax.text(503, 7, "front panel board (to x 560)", fontsize=7, color="#8e44ad")
    for n, (x0, y0, x1, y1) in CTRL_HDR.items():
        if x0 < 500:
            continue
        rect(ax, x0, y0, x1 - x0, y1 - y0, fc="#5dade2", ec="#1b4f72", lw=0.8, zorder=3)
        ax.text(x0 - 0.5, y0 + (y1 - y0) / 2, n, fontsize=6.5, ha="right", va="center", color="#1b4f72", zorder=8)
    for x, y in CTRL_STANDOFFS:
        if x > 500:
            ax.add_patch(Circle((x, y), 1.6, fc="white", ec="#1b4f72", zorder=3))
    # our board
    draw_outline(ax)
    # keep-outs and strips on our board
    rect(ax, 525, 127, 35, 20, fc="none", ec="#117a65", hatch="////", lw=0.8, zorder=2)
    ax.text(526, 140.5, "ribbon corridor y 127-147:\nno bottom-side parts", fontsize=7, color="#117a65", zorder=8)
    rect(ax, 560, 30, 10, 97, fc="#d5f5e3", ec="#117a65", lw=0.8, alpha=0.6, zorder=2)
    ax.text(561, 31.5, "no-HV strip\nx 560-570", fontsize=6.5, color="#117a65", rotation=90, zorder=8, va="bottom")
    for n, x0, y0, x1, y1, side, c in ZONES:
        if side == "b":
            rect(ax, x0, y0, x1 - x0, y1 - y0, fc=c, ec=c, alpha=0.18, lw=1, zorder=2)
        else:
            rect(ax, x0, y0, x1 - x0, y1 - y0, fc="none", ec=c, ls="--", lw=1.4, zorder=4)
        if n:
            ax.text(x0 + 0.8, y1 - 2.2, n, fontsize=6.3, color=c, zorder=8, va="top",
                    wrap=True)
    # bars, devices and plate holes (plate side)
    for n, x, y, w, h, note in fp.PLATE_FIXED:
        rect(ax, x, y + 0.5, w, 15, fc="#95a5a6", ec="black", alpha=0.45, lw=1, ls="--", zorder=4)
    for (qx, qy, nm, lead_dir) in [(582, 64.8, "Q201", 1), (595, 64.8, "Q202", 1), (618.5, 171.2, "Q203", -1),
                                   (631.5, 171.2, "Q204", -1)]:
        rect(ax, qx - 5.1, qy - 4.5 if lead_dir > 0 else qy - 10.5, 10.2, 15.0, fc="#566573", ec="k", alpha=0.6,
             lw=0.8, zorder=4)
        ax.text(qx, qy + (7.5 if lead_dir > 0 else -8.5), nm, fontsize=6, ha="center", color="white", zorder=8)
    for hx, hy, _ in fp.PLATE_HOLES:
        ax.add_patch(Circle((hx, hy), 1.7, fc="black", zorder=5))
    ax.text(570.5, 56.5, "bar 1 (plate side) 38x15x6", fontsize=6.5, zorder=8)
    ax.text(601.5, 155.0, "bar 2 (plate side) 46x15x6", fontsize=6.5, zorder=8)
    for hx, hy, plated, _ in fp.HOLES:
        ax.add_patch(Circle((hx, hy), 3.2, fc="#c0392b" if plated else "white", ec="black", lw=1, zorder=5))
        ax.text(hx + 3.6, hy - 1, ("H101 " if plated else "") + f"({hx:.0f}, {hy:.0f})", fontsize=6, zorder=8)
    # PSU cable holes, mains inlet, rear panel holes
    for i, (hx, hy) in enumerate(PSU_HOLES):
        ax.add_patch(Circle((hx, hy), 7.5, fc="#fcf3cf", ec="#b7950b", lw=1.5, zorder=5))
        ax.text(hx + 8.5, hy + (2 if i == 0 else 1), ("front" if i == 0 else "rear") + f" PSU hole Ø15\n({hx}, {hy})",
                fontsize=6.5, color="#7d6608", zorder=8)
    rect(ax, *INLET, fc="#fadbd8", ec="#922b21", lw=1.2, zorder=3)
    ax.text(634.5, 203, "mains inlet\n32-52 below plate", fontsize=6.5, color="#922b21", zorder=8)
    for sx in (627.3, 667.3):
        rect(ax, sx - 3, 199, 6, 11, fc="#922b21", alpha=0.5, zorder=3)
    rect(ax, 649, 145, 31, 65, fc="none", ec="#922b21", ls=":", lw=1.2, zorder=3)
    ax.text(669.5, 166, "mains\nlane", fontsize=6.5, color="#922b21", zorder=8)
    rect(ax, 591, 203, 13, 7, fc="#f9e79f", ec="#7d6608", lw=0.8, zorder=3)
    ax.text(586, 196.5, "4 x Ø13 rear holes x 597.6:\nstay empty", fontsize=6, color="#7d6608", zorder=8)
    # tabs and receptacles
    colors = {"W01": "#b9770e", "W02": "#cb4335", "W03": "#cb4335", "W04": "#7b241c", "W05": "#7b241c"}
    for ref, w, pin, net, x, y, legs in TABS:
        x0, y0, ww, hh = tab_rect(x, y, legs)
        rect(ax, x0, y0, ww, hh, fc="#f5b041" if "GND" not in net and net != "B_N" else "#5d6d7e", ec="black",
             lw=1.2, zorder=7)
        if legs == "x":
            ax.plot([x - 2.5, x + 2.5], [y, y], "k.", ms=4, zorder=8)
        else:
            ax.plot([x, x], [y - 2.5, y + 2.5], "k.", ms=4, zorder=8)
        ax.text(x, y, str(pin), fontsize=7, ha="center", va="center", weight="bold", zorder=9)
    lab = {"J101": (662, 51, "J101 (W01-b) raw HV in\n2 B_N (656, 47)\n1 B_P (656, 59)"),
           "J102": (600, 44.5, "J102 (W02-a) to preamp\n1 RAW_SS1 (604, 37)  2 GND_PRE1 (616, 37)"),
           "J103": (571, 44.5, "J103 (W03-a) to PI+FX\n1 RAW_SS2 (578, 37)  2 GND_PRE2 (590, 37)"),
           "J201": (536.5, 176, "J201 (W04-a)\n1 V_ANODE (531.5, 170)\n2 GND_PWR (531.5, 182)"),
           "J202": (536.5, 155.5, "J202 (W05-a) 1 V_SCREEN\n(531.5, 155)")}
    for ref, (lx, ly, t) in lab.items():
        ax.text(lx, ly, t, fontsize=6.5, zorder=9, color="#4a235a",
                bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.6))
    # J1 and J501
    rect(ax, *J1_SHROUD, fc="#48c9b0", ec="black", lw=1.2, zorder=7)
    ax.add_patch(Circle(J1_PIN1, 0.9, fc="red", ec="k", zorder=9))
    ax.text(569.5, 106.5, "J1 (W17-b) 2x20 1.27\npin 1 (566.37, 108.86)\npin 40 (565.10, 84.73)\nodd row east, pin 1 rear",
            fontsize=6.3, zorder=9, bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.6))
    arrow(ax, [(550.4, 96.8), (558, 99), (563.5, 96.8)], "#148f77", lw=2.2, head=False)
    ax.text(552.3, 101.5, "W17\nU 2 in", fontsize=6, color="#148f77", zorder=9)
    for (p1, p2), style, name in [(J501_A, "-", "J501 opt. A"), (J501_B, "--", "J501 opt. B (pref.)")]:
        cx, cy = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        vert = p1[0] == p2[0]
        w, h = (5.8, 5.1) if vert else (5.1, 5.8)
        rect(ax, cx - w / 2, cy - h / 2, w, h, fc="#f7dc6f" if style == "-" else "none", ec="black", ls=style, lw=1,
             zorder=7)
        ax.add_patch(Circle(p1, 0.7, fc="red", zorder=9))
        ax.text(cx + 3.5, cy - 1, name + f"\npin 1 ({p1[0]}, {p1[1]})", fontsize=6, zorder=9)
    # power amp tab window and proposed tabs
    rect(ax, *PA_WINDOW, fc="none", ec="#7b241c", ls="--", lw=1.4, zorder=6)
    ax.text(502.5, 187.5, "power amp HV tabs:\nwindow x 503-516, y 148-186", fontsize=6.3, color="#7b241c", zorder=9)
    for n, x, y in PA_TABS:
        rect(ax, x - 4, y - 3.5, 8, 7, fc="#f5b041" if n != "GND_PWR" else "#5d6d7e", ec="#7b241c", lw=1, ls="--",
             zorder=7)
    # cable routes on this panel
    arrow(ax, [(658.5, 28.6), (658.5, 36), (656, 41), (656, 44)], colors["W01"], lw=2.2)
    ax.text(642, 22, "W01 down the front hole", fontsize=6.5, color=colors["W01"], zorder=9)
    arrow(ax, [(604, 33.5), (604, 20), (502, 20)], colors["W02"], lw=2.2)
    arrow(ax, [(578, 33.5), (578, 24), (502, 24)], colors["W03"], lw=2.2)
    ax.text(503, 20.6, "W02", fontsize=6, color=colors["W02"], zorder=9)
    ax.text(503, 24.6, "W03", fontsize=6, color=colors["W03"], zorder=9)
    ax.text(588, 16.5, "W02 / W03 (430 V, 600 V insulation): forward past y 30, up to the plate,\n"
                       "clipped at y 18-26 under the plate, west in front of the control board",
            fontsize=6.3, color=colors["W02"], zorder=9, bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.6))
    for y in (155, 170, 182):
        arrow(ax, [(527.5, y), (516, y)], colors["W04"], lw=2)
    ax.text(519.5, 160.2, "W05", fontsize=6, color=colors["W04"], zorder=9, ha="center")
    ax.text(519.5, 175.2, "W04", fontsize=6, color=colors["W04"], zorder=9, ha="center")
    # W16 option B route
    arrow(ax, [(573.8, 117.5), (573.8, 124.5), (522, 124.5), (514, 134)], "#b7950b", lw=1.6, ls="--")
    ax.text(526, 120, "W16 opt. B (pref.)", fontsize=6, color="#b7950b", zorder=9)
    arrow(ax, [(565.5, 51.3), (556, 51.3), (556, 124.5)], "#b7950b", lw=1.0, ls=":", head=False)
    ax.text(553, 60, "W16 opt. A", fontsize=6, color="#b7950b", rotation=90, zorder=9)
    # W10 / W18 lane (PSU -> control board), not ours
    arrow(ax, [(652, 28.6), (645, 27.5), (556.5, 27.5), (556.5, 41), (550, 47)], "#5d6d7e", lw=1.2, ls="-.")
    arrow(ax, [(556.5, 41), (556.5, 70), (548.5, 70)], "#5d6d7e", lw=1.2, ls="-.")
    ax.text(611, 28.3, "W10 / W18 lane (board level, y 26-29)", fontsize=6, color="#5d6d7e", zorder=9)
    # J5 / J7 ribbons
    rect(ax, 541, 119, 13, 90, fc="#a9cce3", ec="#1b4f72", alpha=0.25, lw=0.6, zorder=2)
    ax.text(547.5, 184, "J7 ribbon\n≥35 below\nboard", fontsize=5.8, color="#1b4f72", ha="center", zorder=9)
    rect(ax, 510.5, 119, 11.5, 15, fc="#a9cce3", ec="#1b4f72", alpha=0.35, lw=0.6, zorder=2)
    # dimensions
    def dim(p, q, t, off=(0, 0), rot=0):
        ax.annotate("", xy=p, xytext=q, arrowprops=dict(arrowstyle="<->", color="#0e6251", lw=1), zorder=9)
        ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], t, fontsize=7, color="#0e6251",
                ha="center", rotation=rot, zorder=9, weight="bold")
    dim((552, 60), (560, 60), "8.0", (0, 1.2))
    dim((540, 122), (540, 127), "5.0", (3, -1.5))
    dim((519.1, 193), (525, 193), "5.9", (0, 1.2))
    ax.set_title("HV supplies rev 3: layout sketch, interfaces (2026-11-24). Chassis frame, mm, seen from above "
                 "(front panel at the bottom).\nSolid fill = bottom side (down); dashed = plate side; red dot = pin 1; "
                 "numbers on tabs = pad number.", fontsize=10)
    ax.grid(True, color="#ecf0f1", lw=0.5)
    ax.set_xticks(range(500, 691, 10))
    ax.set_yticks(range(0, 216, 10))
    ax.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "layout_sketch.png"), dpi=110)


def routes():
    fig, ax = plt.subplots(figsize=(18, 7))
    ax.set_xlim(0, 690)
    ax.set_ylim(-4, 216)
    ax.set_aspect("equal")
    ax.axhline(0, color="k", lw=2.5)
    ax.axhline(210, color="k", lw=2.5)
    for (x0, y0, w, h), n, c in [(PRE, "preamp", "#27ae60"), (PIFX, "PI + FX", "#8e44ad"), (PA, "power amp", "#c0392b"),
                                 (CTRL, "control board", "#2e86c1"), (FRONT_BOARD, "front panel board", "#8e44ad"),
                                 (REAR_IO, "rear I/O", "#7f8c8d")]:
        rect(ax, x0, y0, w, h, fc=c, alpha=0.12, ec=c, lw=1.2)
        ax.text(x0 + 2, y0 + h - 7, n, fontsize=8, color=c)
    draw_outline(ax, lw=1.2)
    ax.text(600, 110, "HV supplies", fontsize=8)
    rect(ax, PSU[0], PSU[1], PSU[2], PSU[3], fill=False, ec="#7f8c8d", ls="--")
    for hx, hy in PSU_HOLES:
        ax.add_patch(Circle((hx, hy), 7.5, fc="#fcf3cf", ec="#b7950b"))
    ax.add_patch(Circle(OT_HOLE, 7, fc="#fdebd0", ec="#a04000", lw=1.2))
    ax.add_patch(Circle(OT_HOLE, 15, fill=False, ec="#a04000", ls=":"))
    ax.text(OT_HOLE[0] - 46, OT_HOLE[1] + 10, "OT lead hole (415.5, 90.1)\n15 mm circle", fontsize=6.5, color="#a04000")
    for x, y in CTRL_STANDOFFS:
        ax.add_patch(Circle((x, y), 2.5, fc="white", ec="#1b4f72"))
    # other cables that W02 / W03 meet
    rect(ax, 388, 14, 12, 82, fc="#d2b4de", alpha=0.45, ec="none")
    ax.text(389, 16, "W30-32", fontsize=6, rotation=90, color="#6c3483")
    rect(ax, 381, 40, 77, 20, fc="#aed6f1", alpha=0.45, ec="none")
    ax.text(436, 55, "W12", fontsize=6.5, color="#1b4f72")
    ax.plot([455, 430, 40], [122, 96, 96], color="#17a589", lw=1.2, ls="-.")
    ax.text(300, 92, "W20 Ethernet (y ~96)", fontsize=6.5, color="#17a589")
    ax.plot([431, 300, 280], [90, 100, 110], color="#1f618d", lw=1.2, ls=":")
    ax.text(300, 101.5, "W13", fontsize=6.5, color="#1f618d")
    ax.plot([415.5, 420, 430], [90.1, 110, 140], color="#a04000", lw=1.2, ls="--")
    ax.text(422, 128, "OT leads", fontsize=6.5, color="#a04000")
    # W02 (preamp): plate level solid, low level dotted
    c2, c3 = "#cb4335", "#e74c3c"
    arrow(ax, [(604, 37), (604, 20), (424, 20), (424, 70)], c2, lw=2.2, head=False)
    arrow(ax, [(424, 70), (372, 70), (372, 79)], c2, lw=2.0, ls=":")
    ax.text(470, 13.5, "W02 RAW_SS1 to preamp J501 (plate level ——, low ····), ~380 mm, cut 450", fontsize=7, color=c2)
    # W03 (PI + FX), option (a): plate level over the control board's west strip x 442-448
    arrow(ax, [(578, 37), (578, 24), (445, 24), (445, 120), (285, 120)], c3, lw=2.2, head=False)
    arrow(ax, [(285, 120), (285, 113), (270, 113)], c3, lw=2.0, ls=":")
    arrow(ax, [(424, 70), (424, 118)], c3, lw=1.0, ls=(0, (1, 3)), head=False)
    ax.text(290, 123, "W03 RAW_SS2 to PI + FX, option (a): plate level over the control board's west strip, "
                      "~520 mm, cut 600", fontsize=7, color=c3)
    ax.text(425.5, 108, "(b)", fontsize=6.5, color=c3)
    for n, x, y in PRE_J501:
        rect(ax, x - 3.5, y - 4, 7, 8, fc="#f5b041", ec="k", lw=0.8)
    ax.text(330, 70, "preamp J501\n(357 / 372, ~81)", fontsize=6.5)
    rect(ax, *PIFX_WINDOW, fc="none", ec="#8e44ad", ls="--", lw=1.4)
    rect(ax, *PIFX_WINDOW2, fc="none", ec="#8e44ad", ls=":", lw=1.0)
    for n, x, y in PIFX_TABS:
        rect(ax, x - 3.5, y - 4, 7, 8, fc="#f5b041" if n != "GND" else "#5d6d7e", ec="#8e44ad", ls="--", lw=0.8)
    ax.text(222, 110, "PI + FX\nraw tabs\n(window)", fontsize=6.5, color="#8e44ad")
    rect(ax, *PA_WINDOW, fc="none", ec="#7b241c", ls="--", lw=1.2)
    for y in (155, 170, 182):
        arrow(ax, [(531.5, y), (512, y)], "#7b241c", lw=1.6)
    ax.set_title("HV supplies rev 3: cable routes to the mating boards (W02 / W03 / W04 / W05), chassis frame, "
                 "seen from above", fontsize=10)
    ax.set_xticks(range(0, 691, 50))
    ax.tick_params(labelsize=7)
    ax.grid(True, color="#ecf0f1", lw=0.5)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "layout_sketch_routes.png"), dpi=100)


if __name__ == "__main__":
    detail()
    routes()
    print("wrote layout_sketch.png, layout_sketch_routes.png")
