#!/usr/bin/env python3
"""Hand edits after generation stopped (D-STOP), accepted exactly by the Proteus-based checks.

The board is no longer generated (STATUS.md "Decisions", D-STOP); every hand edit that makes the KiCad
design differ from the Proteus CADCAM data on purpose is listed here, and the checks that compare against
Proteus run through this wrapper so that they accept exactly these differences and nothing else.

Edit 1 - finding 6 (user decision 2026-11-20): ADC121C027 VA / VIN on ADC1-ADC3. Proteus (PDF, IPC,
gerbers) wires 3V3 to VIN (pin COM2 = SOT pad 3) and the filtered input to VA (pin A1 = SOT pad 1);
the TI pin table has VA = 1 (supply / reference), VIN = 3. The KiCad design swaps them: six pin nets
(PIN_NETS), the copper inside three small areas around the parts (AREAS: tracks rerouted on F.Cu / B.Cu,
F.Cu GND zone refilled) and six added vias (EXTRA_VIAS, all on the input nets).

How each check accepts it (the shared p2k hooks; this file only supplies the data):
  compare_netlists   compare_netlists.load_ipc replaced: the IPC pin nets with PIN_NETS applied
  check_board        p2k.pcb.configure(records=) (IPC records with PIN_NETS) + main(extra_vias=)
  assign_nets        p2k.pcb.configure(records=) (its IPC net mapping and via nets)
  ipc356_diff        p2k.pcb.configure(records=) + main(extra_vias=)
  gerber_roundtrip   p2k.pcb.configure(records=) + main(in_area=AREAS, extra_vias=) and the strict
                     roundtrip_counts with the AREAS (draws / flashes outside the areas must be equal;
                     inside, KiCad flashes = Proteus flashes + the added vias); p2k has no area hook for
                     the counts (p2k candidate 32)
The record filter fails when a listed pin does not have its recorded Proteus net (a stale entry), and
every check still fails on any other difference.

Usage (from the board root):
  python3 tools/hand_edits.py compare_netlists | ipc356_diff | gerber_roundtrip --check
  tools/p2k/bin/kipy tools/hand_edits.py check_board | assign_nets --check
Coordinates: IPC frame (mm, Y up; KiCad (x, y) = (x, -y)).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "p2k"))  # proteus2kicad

# (refdes, pin) -> (Proteus net (IPC, after NET_ALIASES), KiCad design net as an IPC net name)
PIN_NETS = {
    ("ADC1", "A1"): ("#00200", "3V3"),     # VA  (pad 1): filtered input R78 / C35 -> 3V3
    ("ADC1", "COM2"): ("3V3", "#00200"),   # VIN (pad 3): 3V3 -> filtered input
    ("ADC2", "A1"): ("#00202", "3V3"),     # VA: R79 / C36 -> 3V3
    ("ADC2", "COM2"): ("3V3", "#00202"),   # VIN: 3V3 -> R79 / C36
    ("ADC3", "A1"): ("#00204", "3V3"),     # VA: R80 / C37 -> 3V3
    ("ADC3", "COM2"): ("3V3", "#00204"),   # VIN: 3V3 -> R80 / C37
}

# Copper deviation areas, all four layers: (x_min, y_min, x_max, y_max), IPC frame.
AREAS = {
    "ADC1": (-111.30, -7.75, -107.85, -3.65),
    "ADC2": (-112.25, -12.45, -107.85, -8.60),
    "ADC3": (-113.20, -17.75, -108.15, -13.10),
}

# Added vias (0.5 / 0.3, like the Proteus vias): (x, y, IPC net name), IPC frame.
EXTRA_VIAS = [
    (-110.366, -4.134, "#00200"), (-110.45, -6.7, "#00200"),     # ADC1: input under A2 to COM2 (B.Cu)
    (-110.4, -9.058, "#00202"), (-110.4, -11.5, "#00202"),       # ADC2
    (-110.496, -13.504, "#00204"), (-110.45, -16.3, "#00204"),   # ADC3
]


def in_area(layer, x, y):
    return any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in AREAS.values())


def apply_pin_nets(recs):
    """IPC records -> the same records with PIN_NETS applied (copies); a listed pin that is missing or
    does not carry its recorded Proteus net fails (the entry would be stale)."""
    seen = {}
    out = []
    for p in recs:
        key = (p.get("refdes"), p.get("pin"))
        if p.get("kind") == "pad" and key in PIN_NETS:
            old, new = PIN_NETS[key]
            if p["net"] != old:
                raise SystemExit(f"hand_edits: {key[0]}-{key[1]}: IPC net {p['net']}, PIN_NETS says {old} (stale entry)")
            p = dict(p, net=new, net_raw=new)
            seen[key] = seen.get(key, 0) + 1
        out.append(p)
    missing = sorted(set(PIN_NETS) - set(seen))
    if missing:
        raise SystemExit(f"hand_edits: PIN_NETS pins not in the IPC: {missing}")
    return out


def _configure():
    from p2k import pcb
    pcb.configure(records=apply_pin_nets)
    print(f"hand_edits: accepted (D-STOP edit 1, finding 6): {len(PIN_NETS)} pin nets "
          + ", ".join(f"{r}-{p} {o}->{n}" for (r, p), (o, n) in PIN_NETS.items()))


def run_compare_netlists(argv):
    from p2k import compare_netlists as cn
    orig = cn.load_ipc

    def load_ipc():
        pin_net = orig()
        for key, (old, new) in PIN_NETS.items():
            if pin_net.get(key) != old:
                raise SystemExit(f"hand_edits: {key[0]}-{key[1]}: IPC net {pin_net.get(key)}, PIN_NETS says {old} (stale entry)")
            pin_net[key] = new
        return pin_net
    cn.load_ipc = load_ipc
    print(f"hand_edits: accepted (D-STOP edit 1, finding 6): {len(PIN_NETS)} pin nets "
          + ", ".join(f"{r}-{p} {o}->{n}" for (r, p), (o, n) in PIN_NETS.items()))
    sys.argv = ["compare_netlists"] + argv
    cn.main()


def run_check_board(argv):
    _configure()
    from p2k import check_board
    check_board.main(argv, extra_vias=EXTRA_VIAS)


def run_assign_nets(argv):
    _configure()
    from p2k import assign_nets
    sys.argv = ["assign_nets"] + argv
    assign_nets.main()


def run_ipc356_diff(argv):
    _configure()
    from p2k import ipc356_diff
    sys.exit(ipc356_diff.main(argv, extra_vias=EXTRA_VIAS))


def _count_check_with_areas(gr):
    """roundtrip_counts with the AREAS: per layer, the Proteus draws gerber_to_tracks builds and the KiCad
    Conductor draws with both ends outside every area must be equal in number, and so must the flashes
    outside the areas; inside the areas the KiCad flashes must be the Proteus flashes plus exactly the
    EXTRA_VIAS (one via pad per copper layer each). The track counts inside the areas are printed."""
    from p2k import gerber, gerber_to_tracks as g2t

    def inside_seg(x1, y1, x2, y2):
        return in_area(None, x1, y1) and in_area(None, x2, y2)

    def flashes(g):
        return {(o.ap.dcode, round(o.x, 3), round(o.y, 3)) for o in g.objects if isinstance(o, gerber.Flash)}

    nvia_in = sum(1 for x, y, _ in EXTRA_VIAS if in_area(None, x, y))

    def count_check(pname, klayer, user, gp, gk):
        ptr = g2t.load_layer(pname, klayer, user).tracks
        kdr = [o for o in gk.objects if isinstance(o, gerber.Draw) and (o.ap.function or "").startswith("Conductor")]
        p_in = sum(1 for t in ptr if inside_seg(*t[:4]))
        k_in = sum(1 for d in kdr if inside_seg(d.x1, d.y1, d.x2, d.y2))
        pf, kf = flashes(gp), flashes(gk)
        pf_in = sum(1 for f in pf if in_area(None, f[1], f[2]))
        kf_in = sum(1 for f in kf if in_area(None, f[1], f[2]))
        errors = []
        if len(kdr) - k_in != len(ptr) - p_in:
            errors.append(f"counts: {klayer}: {len(kdr) - k_in} KiCad track draws outside the hand-edit areas, "
                          f"gerber_to_tracks builds {len(ptr) - p_in} there from the Proteus draws")
        if len(kf) - kf_in != len(pf) - pf_in:
            errors.append(f"counts: {klayer}: {len(kf) - kf_in} KiCad flashes outside the hand-edit areas, Proteus {len(pf) - pf_in}")
        if kf_in != pf_in + nvia_in:
            errors.append(f"counts: {klayer}: {kf_in} KiCad flashes inside the hand-edit areas, "
                          f"Proteus {pf_in} + {nvia_in} added vias")
        print(f"hand_edits: counts {klayer}: inside the areas {p_in} Proteus / {k_in} KiCad track draws, "
              f"{pf_in} Proteus / {kf_in} KiCad flashes ({nvia_in} added vias)")
        return errors, (len(ptr), len(kdr), len(pf), len(kf))
    gr.count_check = count_check


def run_gerber_roundtrip(argv):
    _configure()
    from p2k import gerber_roundtrip as gr
    _count_check_with_areas(gr)
    print("hand_edits: deviation areas (IPC frame, all layers): "
          + ", ".join(f"{k} x {a[0]}..{a[2]} y {a[1]}..{a[3]}" for k, a in AREAS.items())
          + f"; {len(EXTRA_VIAS)} added vias")
    sys.exit(gr.main(argv, in_area=in_area, extra_vias=[(x, y, n, "D-STOP edit 1") for x, y, n in EXTRA_VIAS]))


TOOLS = {
    "compare_netlists": run_compare_netlists,
    "check_board": run_check_board,
    "assign_nets": run_assign_nets,
    "ipc356_diff": run_ipc356_diff,
    "gerber_roundtrip": run_gerber_roundtrip,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in TOOLS:
        sys.exit("usage: hand_edits.py {" + ",".join(TOOLS) + "} [args]")
    os.chdir(ROOT)
    TOOLS[sys.argv[1]](sys.argv[2:])
