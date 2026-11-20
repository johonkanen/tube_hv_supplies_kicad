#!/usr/bin/env python3
"""Pin-order check: the UNMOVED KiCad base footprints with the Proteus renumbering, fitted onto
the IPC pads (playbook Phase 2, step 2). A small residual confirms that the Proteus pin ids sit on
the pads the renumbering says; a residual of a pad pitch or more means the ids are on other pads
(chirality). Both mirror states are fitted: SMD parts must fit with the mirror of their IPC side
(bottom = mirrored), THT parts unmirrored (top).

Limits of the geometry: two-pad and inline parts always fit (a 180 deg turn reverses the pad
order), and dual-row SMD packages are symmetric under a 180 deg turn, so the geometry confirms the
chirality but not which end is pin 1. For those the nets decide (Phase 1: every pin on its IPC net,
e.g. ADC1-3 A2 = GND, K1 = SCL, COM1 = SDA only with A1 on JEDEC pad 1), and the body markers are
drawn with --render over the Proteus silk / assembly layers of the part's side
(reports/pin_order/<refdes>.png) and compared by eye (STATUS.md "Phase 2 - pin order").

Usage: python3 tools/check_pin_order.py [--render]   (--render needs matplotlib)
Exit 1 when a result differs from EXPECT (so a changed footprint or renumbering is noticed).
"""
import glob
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "p2k"))
os.chdir(ROOT)
from p2k import fpgeom, sexpr  # noqa: E402
from p2k.footprints import footprint_path  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "tools"))
from gen_footprints import PROJECT  # noqa: E402

# Project footprints are checked with THEIR base and renumbering (gen_footprints.PROJECT), so a
# wrong renumbering there fails here even though p2k.footprints.derive moves the pads onto the
# IPC positions (and check_footprints then passes).



def proj(name):
    """(base footprint, renumbering) of a project footprint spec."""
    return PROJECT[name]["base"], PROJECT[name].get("renumber", {})


# (name, refdes group, KiCad base footprint, renumbering of the base pads, expected best mirror,
#  residual upper bound mm, note)
CHECKS = [
    ("REF1", "REF1", *proj("SOT-23_Proteus"), False, 0.03,
     "SOT-23 renumbered (1 = JEDEC 3): fits; Proteus 1.90 mm rows vs KiCad 1.875"),
    ("REF1 plain", "REF1", "Package_TO_SOT_SMD:SOT-23", {}, None, None,
     "SOT-23 with JEDEC numbering: does not fit (> 0.1 mm, angle not snapped)"),
    ("ADC", "ADC1 ADC2 ADC3", *proj("SOT-23-6_ADC121C027_Proteus_ProteusPads"), False, 0.19,
     "A1 A2 COM2 K2 K1 COM1 = JEDEC 1-6: fits (rows 2.65 vs KiCad 2.275 -> 0.1875)"),
    ("ADC datasheet", "ADC1 ADC2 ADC3", "Package_TO_SOT_SMD:SOT-23-6",
     {"1": "COM2", "2": "A2", "3": "A1", "4": "COM1", "5": "K1", "6": "K2"}, None, None,
     "VA / VIN exchanged (COM2 on pad 1, A1 on pad 3, the datasheet wiring): fits only mirrored, "
     "i.e. not on a top-side part"),
    ("SI8271", "DRV1 DRV2", *proj("SOIC-8_3.9x4.9mm_P1.27mm_Proteus"), True, 0.28,
     "bottom side, rows 5.5 vs 4.95"),
    ("SI8271 Proteus pads", "DRV5 DRV6", *proj("SOIC-8_3.9x4.9mm_P1.27mm_Proteus_ProteusPads"), True, 0.28,
     "bottom side, rows 5.5 vs 4.95 (spec with the Proteus pad sizes)"),
    ("TSSOP-14", "U1 U2", *proj("TSSOP-14_4.4x5mm_P0.65mm_Proteus_ProteusPads"), False, 0.07, "rows 5.85 vs 5.725"),
    ("J1 rows swapped", "J1", *proj("PinHeader_2x20_P1.27mm_Vertical_RowsSwapped_ProteusPads"), False, 0.01,
     "odd / even swapped: fits on top"),
    ("J1 KiCad", "J1", "Connector_PinHeader_1.27mm:PinHeader_2x20_P1.27mm_Vertical", {}, True, 0.01,
     "standard numbering fits only MIRRORED (bottom), but J1 is on top"),
    ("J2", "J2", *proj("PinHeader_2x08_P1.27mm_Vertical_ProteusPads"), False, 0.01,
     "standard numbering fits on top (spec with the Proteus pad sizes)"),
    ("TO-220", "Q3 Q4 Q7 Q8", *proj("TO-220-3_Vertical_ProteusPads"), False, 0.01,
     "inline: marker by render (spec with the Proteus pads)"),
    ("SMA", "D2 D18", *proj("D_SMA_AC"), True, 0.051, "two pads: band by render"),
    ("CP", "C1 C2 C3 C4 C5 C6 C7 C11 C26", "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm", {}, False, 0.01,
     "two pads: '+' by render"),
]
RENDER = "ADC1 ADC2 ADC3 REF1 J1 J2 Q3 Q4 Q7 Q8 D2 D18 C1 C2 C3 C4 C5 C6 C7 C11 C26 U1 U2 DRV1".split()


def base_pads(fpid, ren):
    out = []
    for p in fpgeom.load_footprint(footprint_path(fpid)):
        if p["num"] == "":
            continue
        q = dict(p)
        q["num"] = ren.get(p["num"], p["num"])
        out.append(q)
    return out


def graphics(fpid):
    """F.SilkS / F.Fab polylines of a footprint (footprint frame, Y up)."""
    node = sexpr.load(footprint_path(fpid))
    lines = []

    def xy(n):
        return float(n[1]), -float(n[2])
    for g in node:
        if not isinstance(g, list) or not g or str(g[0]) not in ("fp_line", "fp_rect", "fp_circle", "fp_poly"):
            continue
        layer = sexpr.find(g, "layer")
        if layer is None or layer[1] not in ("F.SilkS", "F.Fab"):
            continue
        kind = str(g[0])
        if kind == "fp_line":
            lines.append([xy(sexpr.find(g, "start")), xy(sexpr.find(g, "end"))])
        elif kind == "fp_rect":
            (x0, y0), (x1, y1) = xy(sexpr.find(g, "start")), xy(sexpr.find(g, "end"))
            lines.append([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])
        elif kind == "fp_circle":
            (cx, cy), (ex, ey) = xy(sexpr.find(g, "center")), xy(sexpr.find(g, "end"))
            r = math.hypot(ex - cx, ey - cy)
            lines.append([(cx + r * math.cos(t / 20 * math.pi), cy + r * math.sin(t / 20 * math.pi)) for t in range(41)])
        else:
            pts = [xy(p) for p in sexpr.find(g, "pts")[1:]]
            lines.append(pts + pts[:1])
    return lines


def to_board(fr, x, y):
    a = math.radians(fr["angle"])
    x = -x if fr["mirror"] else x
    return fr["tx"] + math.cos(a) * x - math.sin(a) * y, fr["ty"] + math.sin(a) * x + math.cos(a) * y


def render(ref, fpid, fr, ipc_pads, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from p2k import gerber
    side = "Bottom" if fr["mirror"] else "Top"
    xs = [p["x_mm"] for p in ipc_pads]
    ys = [p["y_mm"] for p in ipc_pads]
    m = 4
    box = (min(xs) - m, max(xs) + m, min(ys) - m, max(ys) + m)
    fig, axs = plt.subplots(1, 2, figsize=(11, 5.5))
    for ax, layer in zip(axs, (f"{side} Silk Screen", f"{side} Assembly")):
        g = gerber.parse(glob.glob(f"source/cadcam/*{layer}.GBR")[0])
        for d in g.of(gerber.Draw):
            if box[0] <= d.x1 <= box[1] and box[2] <= d.y1 <= box[3]:
                ax.plot([d.x1, d.x2], [d.y1, d.y2], color="k", lw=1.0)
        for p in ipc_pads:
            ax.add_patch(Circle((p["x_mm"], p["y_mm"]), min(p["pad_w"], p["pad_h"]) / 2, color="orange", alpha=0.5))
            ax.text(p["x_mm"], p["y_mm"], p["pin"], ha="center", va="center", fontsize=7, color="b")
        for line in graphics(fpid):
            pts = [to_board(fr, x, y) for x, y in line]
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color="r", lw=0.8)
        ax.set_title(f"{ref} {layer}: black = Proteus, orange = IPC pads (ids)\nred = unmoved "
                     f"{fpid.split(':')[1]} ({'mirrored, ' if fr['mirror'] else ''}{fr['angle']:g} deg, "
                     f"res {fr['max_res']:.3f})", fontsize=7)
        ax.set_aspect("equal")
        ax.set_xlim(box[0], box[1])
        ax.set_ylim(box[2], box[3])
    fig.savefig(out, dpi=110, bbox_inches="tight")
    plt.close(fig)


def main():
    do_render = "--render" in sys.argv[1:]
    ipc = fpgeom.ipc_pads_by_refdes()
    bad = []
    print(f"{'check':16s} {'KiCad base (unmoved)':40s} {'unmirrored':>16s} {'mirrored':>16s}  result")
    rendered = set()
    for name, refs, fpid, ren, want_mir, lim, note in CHECKS:
        fp = base_pads(fpid, ren)
        worst = {False: None, True: None}
        for ref in refs.split():
            for mir in (False, True):
                r = fpgeom.fit(fp, ipc[ref], mir)
                if r["missing"] or r["extra"] or r["count_diff"]:
                    bad.append(f"{name} {ref}: pad numbers differ from {fpid}: {r['missing']} {r['extra']} {r['count_diff']}")
                if worst[mir] is None or r["max_res"] > worst[mir]["max_res"]:
                    worst[mir] = r
            if do_render and ref in RENDER and ref not in rendered and want_mir is not None:
                rendered.add(ref)
                os.makedirs("reports/pin_order", exist_ok=True)
                render(ref, fpid, fpgeom.fit(fp, ipc[ref], want_mir), ipc[ref], f"reports/pin_order/{ref}.png")
        u, m = worst[False], worst[True]
        cell = lambda w: f"{w['max_res']:7.3f} @{w['angle']:6.4g}"  # noqa: E731
        if want_mir is None:
            # a "does not fit" check: the unmirrored (top) fit must fail
            ok = u["max_res"] > 0.1
            result = "no fit on its side" if ok else "FITS (unexpected)"
        else:
            # symmetric patterns (two-pad, inline) fit both ways: take the mirror of the part's side
            tie = abs(m["max_res"] - u["max_res"]) < 1e-3
            best_mir = want_mir if tie else m["max_res"] < u["max_res"]
            res = m["max_res"] if best_mir else u["max_res"]
            ok = best_mir == want_mir and res <= lim
            result = f"{'mirrored' if best_mir else 'unmirrored'} {res:.3f}"
        print(f"{name:16s} {fpid.split(':')[1]:40s} {cell(u):>16s} {cell(m):>16s}  {result}  ({note})")
        if not ok:
            bad.append(f"{name}: {result}, expected "
                       + ("no unmirrored fit" if want_mir is None else
                          f"{'mirrored' if want_mir else 'unmirrored'} <= {lim}"))
    for b in bad:
        print("check_pin_order: ERROR " + b)
    print("check_pin_order: " + ("FAILED" if bad else "OK (results as recorded in STATUS.md)"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
