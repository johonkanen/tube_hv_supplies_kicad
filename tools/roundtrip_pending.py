#!/usr/bin/env python3
"""Gerber round trip while the J2 pad-size question is open (STATUS.md "Phase 4 - J2", Decisions).
After the Phase 3 tools/drc_pending.py (git history d1c551a).

`p2k gerber_roundtrip --check` finds one 'other' cluster: on In2.Cu (the GND plane) the Proteus
copper web between the four pads J2-1 .. J2-4 (3V3, 3V3, #00206, #00206), 0.734 mm^2 at
(-119.726, -13.557). J2 kept the KiCad pads in the Phase 3 decision A2 (1.0 mm, pad 1 square;
Proteus 0.762 mm round), so KiCad's zone clearance holes around these four pads are 0.24 mm wider
than the Proteus ones, the necks between them close (1.27 mm pitch - 1.0 - 2 x 0.12 = 0.03 mm) and
the web in the middle becomes an island, which the zone fill drops. Nothing connects there (no
pad, no via; the copper check after zone fill has 0 opens). With the Proteus pads on J2 the round
trip is clean (tested on a scratch copy). Putting J2 into PROTEUS_PADS changes the user's pad
decision, so until it is made:

  python3 tools/roundtrip_pending.py     runs `p2k gerber_roundtrip --check`; passes as it does, or
        when its only failure is exactly the recorded cluster (EXPECTED: layer, side, position
        within POS_TOL, area within AREA_TOL, nearest pad of J2), 0 uncovered draws / flashes and
        0 drill mismatches -> PENDING USER DECISION (tools/check_all.sh counts these lines)

Any other failure fails. Remove this wrapper (check_all.sh then runs `p2k gerber_roundtrip
--check` directly) once the decision is made and the board rebuilt. (stdlib only.)
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.environ.get("P2K_BOARD", ROOT)
BIN = os.path.join(ROOT, "tools", "p2k", "bin")

# (layer, side, x, y, area mm^2, refdes of the nearest pad)
EXPECTED = [("In2.Cu", "Proteus", -119.726, -13.557, 0.734, "J2")]
POS_TOL = 0.1    # mm
AREA_TOL = 0.05  # mm^2
OTHER = re.compile(r"^roundtrip: (\S+) OTHER only (\S+) ([\d.]+) mm\^2 at \((-?[\d.]+), (-?[\d.]+)\) near (\S+)-\S+ \(")
FAILED = re.compile(r"^roundtrip: FAILED \((\d+) unexplained clusters, (\d+) draws/flashes without copper in the other set, "
                    r"(\d+) drill mismatches\)")


def main():
    r = subprocess.run([os.path.join(BIN, "p2k"), "gerber_roundtrip", "--check"], cwd=BOARD, capture_output=True, text=True)
    sys.stdout.write(r.stdout + r.stderr)
    if r.returncode == 0:
        print("roundtrip_pending: the round trip passes on its own: remove this wrapper from tools/check_all.sh")
        return 0
    lines = r.stdout.splitlines()
    fail = [m for m in map(FAILED.match, lines) if m]
    others = [l for l in lines if " OTHER " in l]
    left = list(EXPECTED)
    bad = []
    for l in others:
        m = OTHER.match(l)
        hit = None
        if m:
            layer, side, area, x, y, ref = m.group(1), m.group(2), float(m.group(3)), float(m.group(4)), float(m.group(5)), m.group(6)
            for e in left:
                if ((layer, side, ref) == (e[0], e[1], e[5]) and abs(x - e[2]) <= POS_TOL and abs(y - e[3]) <= POS_TOL
                        and abs(area - e[4]) <= AREA_TOL):
                    hit = e
                    break
        if hit:
            left.remove(hit)
        else:
            bad.append(l)
    ok = (len(fail) == 1 and int(fail[0].group(1)) == len(others) == len(EXPECTED) and fail[0].group(2) == "0"
          and fail[0].group(3) == "0" and not bad and not left)
    if not ok:
        print(f"roundtrip_pending: FAILED (summary {fail[0].groups() if fail else None}; {len(others)} 'other' clusters, "
              f"{len(bad)} not the recorded one, {len(left)} recorded not found)")
        return 1
    print("roundtrip_pending: PENDING USER DECISION: 1 cluster, the In2.Cu GND web between J2-1..4 (0.734 mm^2) dropped by the "
          "zone fill around J2's KiCad pads; J2 with the Proteus pads clears it (STATUS.md Phase 4 - J2)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
