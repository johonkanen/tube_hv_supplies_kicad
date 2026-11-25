#!/usr/bin/env python3
"""Board-local footprints for rev 4 (lib/tube_hv_supplies_rev4.pretty) and kicad/fp-lib-table.

  Blade_Tab_4.8mm_1x        one PCB blade tab: 2 legs on 5.00 mm, 1.4 mm drill, both legs pad 1
                            (interfaces.md 4.1 DEFINED; the v2 terminal footprint, copied)
  Blade_Tab_4.8mm_2x_P12mm  two such tabs side by side, 12 mm apart (pad 1, pad 2): room for
                            two fully insulated receptacles (about 8-9 mm wide) and creepage
  L_Toroid_32mm_Standing_P16.4mm  2 mH Fe-Si-Al toroid (32 mm OD, 16.4 mm thick, 0.8 mm wire) standing on
                            edge: two lead holes 16.4 mm apart (1.2 mm drill), a 33 x 18 mm courtyard and two
                            non-plated slots across the ring's thickness for a cable tie through the ring
Run: python3 rev4/tools/make_footprints.py
"""
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRETTY = os.path.join(HERE, "lib", "tube_hv_supplies_rev4.pretty")


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


def slot(x, y, w, h):
    return (f'\t(pad "" np_thru_hole oval (at {x} {y}) (size {w} {h}) (drill oval {w} {h}) '
            f'(layers "*.Cu" "*.Mask"))\n')


def main():
    os.makedirs(PRETTY, exist_ok=True)
    footprint("Blade_Tab_4.8mm_1x", "PCB blade tab 4.8 mm, 2 legs on 5.00 mm, 1.4 mm drill, both legs pad 1 "
              "(interfaces.md 4.1; the v2 terminal footprint)", (-3.5, -1, 3.5, 1),
              [pad(1, 2.5, 0), pad(1, -2.5, 0)], -2.5)
    footprint("Blade_Tab_4.8mm_2x_P12mm", "Two PCB blade tabs 4.8 mm, 12 mm apart, each 2 legs on 5.00 mm, "
              "1.4 mm drill (interfaces.md 4.1)", (-3.5, -1, 3.5, 13),
              [pad(1, 2.5, 0), pad(1, -2.5, 0), pad(2, 2.5, 12), pad(2, -2.5, 12)], -2.5)
    footprint("L_Toroid_32mm_Standing_P16.4mm", "2 mH Fe-Si-Al toroid 32 x 16.4 mm standing on edge, leads 16.4 mm "
              "apart (0.8 mm wire, 1.2 mm drill); two NPTH slots for a cable tie through the ring",
              (-16.0, -8.2, 16.0, 8.2),
              [pad(1, -8.2, 0, 2.4, 1.2), pad(2, 8.2, 0, 2.4, 1.2), slot(0, -10.4, 4.0, 1.6), slot(0, 10.4, 4.0, 1.6)],
              -12.0)
    with open(os.path.join(HERE, "kicad", "fp-lib-table"), "w") as f:
        f.write('(fp_lib_table\n\t(version 7)\n\t(lib (name "tube_hv_supplies_rev4")(type "KiCad")'
                '(uri "${KIPRJMOD}/../lib/tube_hv_supplies_rev4.pretty")(options "")'
                '(descr "rev 4 board-local footprints (tools/make_footprints.py)"))\n)\n')


if __name__ == "__main__":
    main()
