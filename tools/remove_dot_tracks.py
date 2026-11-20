#!/usr/bin/env python3
"""Delete the zero-length Proteus draws listed in p2k_config.REMOVED_DOT_TRACKS from the board
(make_pcb.sh step 2b, after gerber_to_tracks; user decision 2026-11-20, finding 14).

Board-local because p2k REMOVED_TRACKS can't express them: the OUT1 pair is one 1e-5 mm segment
drawn in both directions, one key matches both draws and gerber_to_tracks rejects the duplicate
match. Each entry {(layer, x, y): (count, reason)} (IPC frame, Y up) must match exactly `count`
tracks shorter than 0.001 mm within 0.001 mm of (x, y) on that layer, else this fails (nothing
saved). Move the entries to REMOVED_TRACKS once p2k accepts a count there (p2k candidate).

Usage: tools/p2k/bin/kipy tools/remove_dot_tracks.py     (P2K_BOARD / P2K_PCB honoured)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
import pcbnew  # noqa: E402
from p2k import pcb  # noqa: E402

TOL = 0.001  # mm


def main():
    want = getattr(pcb.cfg(), "REMOVED_DOT_TRACKS", {}) or {}
    board = pcbnew.LoadBoard(pcb.board_file())
    errors, doomed = [], []
    for (layer, x, y), (count, why) in sorted(want.items()):
        lid = board.GetLayerID(layer)
        hits = []
        for t in board.GetTracks():
            if t.GetClass() != "PCB_TRACK" or t.GetLayer() != lid:
                continue
            s, e = t.GetStart(), t.GetEnd()
            if pcbnew.ToMM(t.GetLength()) >= TOL:
                continue
            if all(abs(pcbnew.ToMM(p.x) - x) <= TOL and abs(-pcbnew.ToMM(p.y) - y) <= TOL for p in (s, e)):
                hits.append(t)
        if len(hits) != count:
            errors.append(f"{layer} ({x}, {y}): {len(hits)} zero-length tracks, expected {count} ({why})")
        doomed += hits
    for e in errors:
        print("remove_dot_tracks: ERROR " + e)
    if errors:
        sys.exit(1)
    # Delete(), not Remove() (see p2k gerber_to_tracks: SWIG proxies in pcbnew 10)
    for t in doomed:
        board.Delete(t)
    pcbnew.SaveBoard(pcb.board_file(), board)
    print(f"remove_dot_tracks: {len(doomed)} zero-length tracks deleted ({len(want)} entries, REMOVED_DOT_TRACKS)")


if __name__ == "__main__":
    main()
