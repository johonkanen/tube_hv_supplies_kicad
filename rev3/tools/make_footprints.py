#!/usr/bin/env python3
"""Board-local footprints for rev 3 (lib/tube_hv_supplies_rev3.pretty) and kicad/fp-lib-table.

  Blade_Tab_4.8mm_1x        one PCB blade tab: 2 legs on 5.00 mm, 1.4 mm drill, both legs pad 1
                            (interfaces.md 4.1 DEFINED; the v2 terminal footprint, copied)
  Blade_Tab_4.8mm_2x_P12mm  two such tabs side by side, 12 mm apart (pad 1, pad 2): room for
                            two fully insulated receptacles (about 8-9 mm wide) and creepage
  TO-220-3_Horizontal_TabUp_Bar  IKP08N65F5 lying tab-up on the aluminium bar (plate side, layout first
                            pass): the stock TO-220-3_Horizontal_TabUp pin row and tab position (16.66 mm),
                            without its 3.5 mm board hole (the tab screw goes into the plate, not the board),
                            1.7 mm pads on 1.1 mm drills (0.84 mm between pads: IPC-2221B A6, 301-500 V)
  L_ETD39_2pin_custom       3 mH custom inductor, ETD39 bobbin outline (42 x 42 mm), two pins 30 mm
                            apart (pad positions to the chosen bobbin)
Run: python3 rev3/tools/make_footprints.py
"""
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRETTY = os.path.join(HERE, "lib", "tube_hv_supplies_rev3.pretty")


def rect(x0, y0, x1, y1, layer, w):
    return (f'\t(fp_rect (start {x0} {y0}) (end {x1} {y1}) (stroke (width {w}) (type solid)) (fill no) '
            f'(layer "{layer}"))\n')


def text(t, x, y, layer):
    return (f'\t(property "{t[0]}" "{t[1]}" (at {x} {y} 0) (layer "{layer}") '
            f'(effects (font (size 1 1) (thickness 0.15))))\n')


def pad(num, x, y, size=2.0, drill=1.4):
    return (f'\t(pad "{num}" thru_hole circle (at {x} {y}) (size {size} {size}) (drill {drill}) '
            f'(layers "*.Cu" "*.Mask"))\n')


def footprint(name, descr, body, pads, ref_y):
    x0, y0, x1, y1 = body
    s = (f'(footprint "{name}"\n\t(version 20260206)\n\t(generator "make_footprints")\n\t(layer "F.Cu")\n'
         f'\t(descr "{descr}")\n' + text(("Reference", "REF**"), 0, ref_y, "F.SilkS") +
         text(("Value", name), 0, -ref_y, "F.Fab") + "\t(attr through_hole)\n" +
         rect(x0, y0, x1, y1, "F.Fab", 0.1) + rect(x0 - 0.12, y0 - 0.12, x1 + 0.12, y1 + 0.12, "F.SilkS", 0.12) +
         rect(x0 - 0.5, y0 - 0.5, x1 + 0.5, y1 + 0.5, "F.CrtYd", 0.05) + "".join(pads) + "\t(embedded_fonts no)\n)\n")
    with open(os.path.join(PRETTY, name + ".kicad_mod"), "w") as f:
        f.write(s)


def main():
    os.makedirs(PRETTY, exist_ok=True)
    footprint("Blade_Tab_4.8mm_1x", "PCB blade tab 4.8 mm, 2 legs on 5.00 mm, 1.4 mm drill, both legs pad 1 "
              "(interfaces.md 4.1; the v2 terminal footprint)", (-3.5, -1, 3.5, 1),
              [pad(1, 2.5, 0), pad(1, -2.5, 0)], -2.5)
    footprint("Blade_Tab_4.8mm_2x_P12mm", "Two PCB blade tabs 4.8 mm, 12 mm apart, each 2 legs on 5.00 mm, "
              "1.4 mm drill (interfaces.md 4.1)", (-3.5, -1, 3.5, 13),
              [pad(1, 2.5, 0), pad(1, -2.5, 0), pad(2, 2.5, 12), pad(2, -2.5, 12)], -2.5)
    footprint("L_ETD39_2pin_custom", "3 mH custom inductor on an ETD39 bobbin (42 x 42 mm courtyard); winding ends "
              "on two pins 30 mm apart: move the pads to the chosen bobbin's pin row", (-21, -21, 21, 21),
              [pad(1, -15, 0, 2.5, 1.3), pad(2, 15, 0, 2.5, 1.3)], -23)
    to220()
    with open(os.path.join(HERE, "kicad", "fp-lib-table"), "w") as f:
        f.write('(fp_lib_table\n\t(version 7)\n\t(lib (name "tube_hv_supplies_rev3")(type "KiCad")'
                '(uri "${KIPRJMOD}/../lib/tube_hv_supplies_rev3.pretty")(options "")'
                '(descr "rev 3 board-local footprints (tools/make_footprints.py)"))\n)\n')


def to220():
    """Pins 1-3 at x 0 / 2.54 / 5.08, y 0; the tab screw (in the plate) at (2.54, 16.66); body and tab
    10.2 mm wide from the lead exit (y 3.9) to the tab end (y 19.5). Placed on the plate side (B)."""
    name = "TO-220-3_Horizontal_TabUp_Bar"
    s = (f'(footprint "{name}"\n\t(version 20260206)\n\t(generator "make_footprints")\n\t(layer "F.Cu")\n'
         '\t(descr "TO-220-3 lying tab-up on a mounting bar, leads bent 90 deg into the board (no board hole); '
         '1.7 mm pads, 1.1 mm drill")\n' + text(("Reference", "REF**"), 2.54, -2.6, "F.SilkS") +
         text(("Value", name), 2.54, 21.0, "F.Fab") + "\t(attr through_hole)\n" +
         rect(-2.56, 3.9, 7.64, 19.5, "F.Fab", 0.1) + rect(-2.56, 13.4, 7.64, 19.5, "F.Fab", 0.1) +
         '\t(fp_circle (center 2.54 16.66) (end 4.04 16.66) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab"))\n'
         + rect(-2.68, 3.78, 7.76, 19.62, "F.SilkS", 0.12) +
         '\t(fp_circle (center -1.6 -1.6) (end -1.3 -1.6) (stroke (width 0.12) (type solid)) (fill yes) (layer "F.SilkS"))\n'
         + rect(-1.4, -1.4, 6.48, 19.75, "F.CrtYd", 0.05) +
         "".join(pad(n, 2.54 * (n - 1), 0, 1.7, 1.1) for n in (1, 2, 3)) + "\t(embedded_fonts no)\n)\n")
    with open(os.path.join(PRETTY, name + ".kicad_mod"), "w") as f:
        f.write(s)


if __name__ == "__main__":
    main()
