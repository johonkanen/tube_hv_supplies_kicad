#!/usr/bin/env python3
"""Move the packed (low-voltage) parts of a routed board to the positions of a newly placed board, keeping the
copper already routed (the scripted power copper, HV and ground steps). Used to rerun only the low-voltage
routing after a placement change of the measurement / control block.

    tools/p2k/bin/kipy rev3/tools/replace_lv.py ROUTED.kicad_pcb PLACED.kicad_pcb OUT.kicad_pcb
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_pcb  # noqa: E402


def main():
    routed, placed, out = sys.argv[1:4]
    b = pcbnew.LoadBoard(routed)
    n = pcbnew.LoadBoard(placed)
    new = {f.GetReference(): f for f in n.GetFootprints()}
    moved = 0
    for f in b.GetFootprints():
        ref = f.GetReference()
        if ref not in make_pcb.PACKED:
            continue
        g = new[ref]
        if g.IsFlipped() != f.IsFlipped():
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        f.SetOrientation(g.GetOrientation())
        f.SetPosition(g.GetPosition())
        moved += 1
    # the router's keep-out polygons (User.2 / User.3) follow the new placement file too
    for d in [d for d in b.GetDrawings() if d.GetLayer() in (pcbnew.User_2, pcbnew.User_3)]:
        b.Delete(d)
    for d in n.GetDrawings():
        if d.GetLayer() in (pcbnew.User_2, pcbnew.User_3):
            b.Add(d.Duplicate())
    pcbnew.SaveBoard(out, b)
    print(f"{out}: {moved} parts moved")


if __name__ == "__main__":
    main()
