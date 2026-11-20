#!/usr/bin/env python3
"""Pads of the Proteus-pad parts on the board = the Proteus pad flashes and drills (Phase 5).

Board-local guard for the user's pad decisions (STATUS.md "Phase 3 - pad sizes" A2 and "Phase 5"):
the parts in DECIDED must have exactly the Proteus pads - on every copper layer the pad is on, the
copper of the board pad (pcbnew polygon) has the bounding box (+-0.01 mm) and area of the
Proteus gerber flash at that position (+-6 %: KiCad's rounded corners on the
A2 SMD pads, see AREA_TOL), and a THT pad has the Proteus drill (+-0.005 mm). The
Proteus side comes from the CADCAM gerbers (not the IPC, which records the TO-220 pads as 1.524 x
1.524; finding 15), so a TO-220 pad turned by 90 degrees, a square pin-1 pad (J1), a KiCad pad
size or a KiCad drill all fail here. The other checks do not see these: the gerber round trip
classifies a different pad shape as `pad shape` and ipc356_diff accepts larger KiCad drills.

DECIDED is written out here, independent of tools/gen_footprints.py PROTEUS_PADS (the two must
agree; a part taken out of PROTEUS_PADS fails this check).

Usage: tools/p2k/bin/kipy tools/check_proteus_pads.py     (P2K_BOARD / P2K_PCB honoured)
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
import pcbnew  # noqa: E402
from p2k import board, gerber, pcb  # noqa: E402

# User decisions: A2 (Phase 3) + J2, Q3 Q4 Q7 Q8 and J1 all round (Phase 5, 2026-11-20)
DECIDED = "U1 U2 ADC1 ADC2 ADC3 DRV5 DRV6 J1 J2 Q3 Q4 Q7 Q8".split()
# area: the SMD Proteus-size pads of A2 keep KiCad's rounded corners (ipc_sizes keeps the shape):
# up to 4.6 % less area than the Proteus rectangle (ADC1-3); a square pad on a round flash is +27 %
POS_TOL, BOX_TOL, AREA_TOL, DRILL_TOL = 0.05, 0.01, 0.06, 0.005


def ap_shape(f):
    """(bbox w, bbox h, area) of a flash, gerber frame."""
    ap = f.ap
    if ap.shape == "C":
        d = ap.params[0]
        return d, d, math.pi * d * d / 4
    if ap.shape == "R":
        w, h = ap.params[:2]
        return w, h, w * h
    if ap.shape == "O":
        w, h = ap.params[:2]
        d = min(w, h)
        return w, h, w * h - d * d + math.pi * d * d / 4
    pts = ap.outline
    if not pts:
        raise SystemExit(f"check_proteus_pads: aperture {ap.shape} without a single outline")
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    area = abs(sum(pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1] for i in range(len(pts) - 1))) / 2
    return max(xs) - min(xs), max(ys) - min(ys), area


def main():
    cfg = board.config()
    layers = {klayer: [f for f in gerber.parse(pcb.gerber_path(gname)).of(gerber.Flash)
                       if f.dark and f.ap.function.startswith(("ComponentPad", "SMDPad"))]
              for gname, klayer, _ in cfg.COPPER}
    drills = gerber.parse(pcb.gerber_path(cfg.DRILL_PLATED)).of(gerber.Flash)
    brd = pcbnew.LoadBoard(pcb.board_file())
    fps = {fp.GetReference(): fp for fp in brd.GetFootprints()}
    errors, n_pads, n_layers = [], 0, 0
    for ref in DECIDED:
        fp = fps.get(ref)
        if fp is None:
            errors.append(f"{ref}: not on the board")
            continue
        for pad in fp.Pads():
            n_pads += 1
            x, y = pcbnew.ToMM(pad.GetPosition().x), -pcbnew.ToMM(pad.GetPosition().y)
            name = f"{ref}-{pad.GetNumber()}"
            for klayer, flashes in layers.items():
                lid = brd.GetLayerID(klayer)
                if not pad.IsOnLayer(lid):
                    continue
                near = [f for f in flashes if math.hypot(f.x - x, f.y - y) <= POS_TOL]
                if len(near) != 1:
                    errors.append(f"{name} {klayer}: {len(near)} Proteus pad flashes within {POS_TOL} mm")
                    continue
                pw, ph, pa = ap_shape(near[0])
                poly = pad.GetEffectivePolygon(lid, pcbnew.ERROR_INSIDE)
                bb = poly.BBox()
                kw, kh = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
                ka = poly.Area() / 1e12   # nm^2 -> mm^2
                n_layers += 1
                if abs(kw - pw) > BOX_TOL or abs(kh - ph) > BOX_TOL or abs(ka - pa) > AREA_TOL * pa:
                    errors.append(f"{name} {klayer}: board pad {kw:.3f} x {kh:.3f} mm, {ka:.3f} mm^2; "
                                  f"Proteus flash ({near[0].ap.shape}) {pw:.3f} x {ph:.3f} mm, {pa:.3f} mm^2")
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                near = [f for f in drills if math.hypot(f.x - x, f.y - y) <= POS_TOL]
                kd = pcbnew.ToMM(pad.GetDrillSize().x)
                if len(near) != 1:
                    errors.append(f"{name}: {len(near)} Proteus drills within {POS_TOL} mm")
                elif abs(near[0].ap.params[0] - kd) > DRILL_TOL:
                    errors.append(f"{name}: drill board {kd:.3f} mm, Proteus {near[0].ap.params[0]:.4f} mm")
    for e in errors:
        print("check_proteus_pads: " + e)
    print(f"check_proteus_pads: {len(DECIDED)} parts, {n_pads} pads, {n_layers} pad layers compared "
          f"with the Proteus flashes and drills: " + ("OK" if not errors else f"FAILED ({len(errors)})"))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
