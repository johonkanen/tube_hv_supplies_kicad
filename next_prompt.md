# Next prompt

The conversion of this board is **complete** (Phases 0-5, 2026-11-20). There is no next conversion
session. `tools/check_all.sh` prints `ALL CHECKS PASSED` (18 steps; STATUS.md "Last check output").

What remains open (user decisions; nothing to do without them):

- **Stop generating the board** (the user's call): today `kicad/tube_hv_supplies.kicad_pcb` is rebuilt by
  `tools/make_pcb.sh` and `make_pcb --check` requires it byte-identical. At the first hand edit in KiCad,
  drop the `make_pcb --check` step from `tools/check_all.sh` (the other checks - check_board, copper after
  zone fill, DRC, ipc356_diff, gerber_roundtrip, check_proteus_pads - keep working on a hand-edited board)
  and record it in STATUS.md.
- Report-only design findings (STATUS.md "Findings about the original design"), for the redesign:
  1 (`+2V5_BIAS` name vs the ~1.0 V divider), 2 (15 V "not yet complete"), 6 (ADC121C027 VA / VIN swapped,
  confirmed against the datasheet), 7 (current-measurement net names), 8 (LT1014 at 3.3 V), 10 (voltage
  range 1 / 200), 12 (J1 mirrored numbering - check against the control card), 13 (0.127 mm clearances).
- Not decided, not done: LCSC / BOM fields (as tube_psu), a rename of `+2V5_BIAS`, Proteus pads on more
  parts (C1-C7 C11 C26 keep KiCad's 2.0 mm pads on HV nets, finding / review 4), silk cosmetics (5
  silk_overlap / 3 silk_over_copper warnings from the KiCad body silk; R52 R54 R69 R74 references on the
  Fab layer only).
- p2k candidates (STATUS.md "p2k candidates", 1-26) for the shared tools; the board-local workarounds
  (`check_proteus_pads.py`, the `pads` spec key in gen_footprints.py, measure_gaps.py, check_pin_order.py)
  can move there.

A later session that changes anything starts with `tools/check_all.sh` and follows PLAN.md section 5
(generators only, never by hand in kicad/ or lib/ while the board is generated; tools/p2k pinned at c5682dd).
