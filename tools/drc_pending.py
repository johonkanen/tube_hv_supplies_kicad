#!/usr/bin/env python3
"""DRC and the copper check while the Phase 3 pad-size question is open (STATUS.md "Phase 3 -
pad sizes", Decisions). After tube_pi_fxloop's drc_pending.py.

With the KiCad pad sizes (FOOTPRINT_PAD_SIZES = "kicad") the pads of eight parts reach Proteus
tracks: U1 U2 (TSSOP-14), ADC1 ADC2 ADC3 (SOT-23-6), DRV5 DRV6 (SOIC-8), J1 (2x20 1.27 mm header).
Switching them to the Proteus pads is a user decision, so until it is made:

  tools/p2k/bin/kipy tools/drc_pending.py drc      runs `p2k drc`; passes as it does, or when the
        only unaccepted errors are exactly the recorded ones: EXPECTED_DRC per type, every one
        with a pad of a PENDING part (0 unconnected, 0 parity) -> PENDING USER DECISION
  tools/p2k/bin/kipy tools/drc_pending.py copper   runs `p2k.assign_nets --check`; passes as it
        does, or when its only failure is the recorded short group: every "touching" pair has a
        pad of a PENDING part (EXPECTED_TOUCH pairs), 0 orphans / opens / foreign nets
        -> PENDING USER DECISION

Any other failure fails. Remove this wrapper (check_all.sh runs `p2k drc` and
`p2k.assign_nets --check` directly) once the decision is made and the board rebuilt.
(stdlib only; runs under system python3 or kipy.)
"""
import json
import os
import re
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.environ.get("P2K_BOARD", ROOT)
BIN = os.path.join(ROOT, "tools", "p2k", "bin")

PENDING = ("U1", "U2", "ADC1", "ADC2", "ADC3", "DRV5", "DRV6", "J1")
EXPECTED_DRC = {"shorting_items": 3, "clearance": 29, "solder_mask_bridge": 3}
EXPECTED_TOUCH = 3
PAD = re.compile(r"^(?:PTH )?[Pp]ad \S+ \[[^]]*\] of (%s)( on .*)?$" % "|".join(PENDING))


def run(cmd):
    r = subprocess.run(cmd, cwd=BOARD, capture_output=True, text=True)
    sys.stdout.write(r.stdout + r.stderr)
    return r.returncode, r.stdout


def drc():
    rc, _ = run([os.path.join(BIN, "p2k"), "drc"])
    if rc == 0:
        return 0
    with open(os.path.join(BOARD, "reports", "drc.json")) as f:
        d = json.load(f)
    sys.path.insert(0, BOARD)
    import p2k_config
    accepted = getattr(p2k_config, "DRC_ACCEPTED", {})
    bad = []
    if d.get("unconnected_items") or d.get("schematic_parity"):
        bad.append("unconnected / parity items")
    got = Counter()
    for v in d["violations"]:
        if v["severity"] != "error" or v["type"] in accepted:
            continue
        if v["type"] in EXPECTED_DRC and any(PAD.match(i["description"]) for i in v["items"]):
            got[v["type"]] += 1
        else:
            bad.append(f"{v['type']}: {v['description']}: " + " / ".join(i["description"] for i in v["items"]))
    if bad or dict(got) != EXPECTED_DRC:
        print(f"drc_pending: FAILED (pad-size items {dict(got)}, expected {EXPECTED_DRC}; other: {bad[:5]})")
        return 1
    print("drc_pending: PENDING USER DECISION: " + ", ".join(f"{n} {t}" for t, n in sorted(got.items()))
          + " between KiCad pads of " + " ".join(PENDING) + " and Proteus tracks (STATUS.md Phase 3 - pad sizes)")
    return 0


def copper():
    rc, out = run([os.path.join(BIN, "kipy"), "-m", "p2k.assign_nets", "--check"])
    if rc == 0:
        return 0
    m = re.search(r"after zone fill: \d+ groups, (\d+) shorts, (\d+) orphans, (\d+) opens, (\d+) items with a foreign net", out)
    lines = [l for l in out.splitlines() if l.startswith("assign_nets:  touching")]
    pend = [l for l in lines if any(re.search(r"(^|\s)%s-\S+ \[" % r, l.split(": ", 2)[2]) for r in PENDING)]
    ok = (m and int(m.group(1)) >= 1 and m.group(2) == m.group(3) == m.group(4) == "0"
          and len(lines) == EXPECTED_TOUCH and len(pend) == len(lines))
    if not ok:
        print(f"drc_pending: FAILED (copper: {len(pend)}/{len(lines)} touching pairs at pending pads, "
              f"expected {EXPECTED_TOUCH}; summary {m.groups() if m else None})")
        return 1
    print(f"drc_pending: PENDING USER DECISION: {len(lines)} KiCad pads touching Proteus tracks "
          "(U2-4, ADC1-K2; STATUS.md Phase 3 - pad sizes)")
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("drc", "copper"):
        sys.exit(__doc__)
    sys.exit(drc() if mode == "drc" else copper())
