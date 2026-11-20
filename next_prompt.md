# Next prompt

The conversion of this board is **complete** (Phases 0-5, 2026-11-20), and the first design fixes are in
(2026-11-20, user decisions; STATUS.md "Design fixes 2026-11-20"): the current-measurement nets are renamed to
what they measure (finding 7: `CURRENT_C3` / `CURRENT_C6` / `CURRENT_Q4` / `CURRENT_Q7` and the `*_MEAS`
outputs on J1-1/3/5/7), the dangling Proteus stubs are removed (finding 14), the README hole numbering follows
the board H1-H4, and `make_pcb.sh --check` now stops at a failing step. Component values are unchanged (user
decision). `tools/check_all.sh` prints `ALL CHECKS PASSED` (19 steps; STATUS.md "Last check output").

**HV supplies v2 is not installed and will be redone (user, 2026-11-20): this KiCad project is the starting
point for the redesign.** Bias rail `+1V0_BIAS` (finding 1, done).

What remains (in this order, each needs its trigger):

- **Tool migration**: another session is consolidating the shared tools (proteus2kicad). When it publishes a
  new pin, bump `tools/p2k`, rerun `tools/check_all.sh`, and move the board-local workarounds into the tools
  where they now exist: `tools/remove_dot_tracks.py` + `REMOVED_DOT_TRACKS` → `REMOVED_TRACKS` with a count
  (p2k candidate 28), the name-hint guard in check_all.sh → a strict compare_netlists (27),
  `check_proteus_pads.py`, the `pads` spec key in gen_footprints.py, measure_gaps.py, check_pin_order.py
  (STATUS.md "p2k candidates").
- **J1 renumbering (finding 12)**: waits for the new shared-tool pin-renumber key (user decision). J1 is the
  control-card ribbon: four of its nets were renamed in finding 7 (J1-1 `CURRENT_Q4_MEAS`, J1-3
  `CURRENT_Q7_MEAS`, J1-5 `CURRENT_C6_MEAS`, J1-7 `CURRENT_C3_MEAS`); the control-card repo keeps its own
  names (not touched here).
- **Stop generating the board** (the user's call): today `kicad/tube_hv_supplies.kicad_pcb` is rebuilt by
  `tools/make_pcb.sh` and `make_pcb --check` requires it byte-identical. At the first hand edit, drop the
  `make_pcb --check` step from `tools/check_all.sh` (the other checks keep working on a hand-edited board)
  and record it in STATUS.md.
- **ADC VA / VIN swap (finding 6)**: a hand edit in KiCad **after generation stops** (user decision): swap the
  ADC121C027 supply / input connections of ADC1-ADC3 (pin 1 VA = 3V3, pin 3 VIN = the filtered input).
  The IPC-based checks will then report exactly those pins as differing from Proteus: record them as the
  intended deviation.
- Open for the user (not blocking): `CURRENT_Q4` / `CURRENT_Q7` name the low-side switch (the emitter shunt
  sees the L1 / L3 current only while the low side conducts); `CURRENT_L1` / `CURRENT_L3` if the inductor
  should be in the name. tube_amplifier_kicad `mechanical/hv_supplies_v2.kicad_pcb` may use the old README
  hole numbering (other repo, not checked).
- Report-only findings for the redesign: 2 (15 V "not yet complete"), 8 (LT1014 at 3.3 V, value kept), 10
  (voltage range 1 / 200), 13 (0.127 mm clearances). Not decided: LCSC / BOM fields, Proteus pads on more
  parts, silk cosmetics.

A later session that changes anything starts with `tools/check_all.sh` and follows PLAN.md section 5
(generators only, never by hand in kicad/ or lib/ while the board is generated; tools/p2k pinned at c5682dd).
