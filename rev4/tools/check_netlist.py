#!/usr/bin/env python3
"""Compare KiCad's exported netlist with the intended pin -> net table written by tools/sheets/draw_all.py
(reports/intended_nets.csv). Catches stubs or labels that touch by accident in the netlist-first drawing:
every intended net must be exactly one KiCad net with exactly the intended pins, and no KiCad net may
join two intended nets. Run: python3 rev4/tools/check_netlist.py  (exports the netlist with kicad-cli)."""
import csv
import os
import re
import subprocess
import sys
from collections import defaultdict

RB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(RB, "..", "tools", "p2k", "bin", "kicad-cli")
SCH = os.path.join(RB, "kicad", "tube_hv_supplies_rev4.kicad_sch")
NET = os.path.join(RB, "reports", "netlist.net")


def main():
    subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", NET, SCH], check=True,
                   capture_output=True)
    t = open(NET).read()
    kic = {}
    for blk in re.split(r"\n\t\t\(net\b", t[t.index("(nets"):])[1:]:
        name = re.search(r'\(name "([^"]*)"\)', blk).group(1)
        pins = frozenset(re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk))
        if pins:
            kic[name] = pins
    want = defaultdict(set)
    for row in csv.DictReader(open(os.path.join(RB, "reports", "intended_nets.csv"))):
        want[row["net"]].add((row["ref"], row["pin"]))
    pin2kic = {p: n for n, ps in kic.items() for p in ps}
    errors = []
    for net, pins in sorted(want.items()):
        got = {pin2kic.get(p) for p in pins}
        if None in got:
            errors.append(f"{net}: pins not in any KiCad net: {sorted(p for p in pins if p not in pin2kic)}")
        got.discard(None)
        if len(got) > 1:
            errors.append(f"{net}: split over KiCad nets {sorted(got)}")
        for g in got:
            extra = kic[g] - pins
            if extra:
                errors.append(f"{net}: KiCad net {g} has extra pins {sorted(extra)}")
    print(f"intended nets {len(want)}, KiCad nets with pins {len(kic)}, errors {len(errors)}")
    for e in errors[:40]:
        print("  " + e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
