# Next prompt

The conversion of this board is **complete** (Phases 0-5, 2026-11-20), the first design fixes are in
(findings 1, 7, 14; STATUS.md "Design fixes 2026-11-20"; finding 6 below), and the **shared-tool migration is done**
(2026-11-20; STATUS.md "Shared-tool migration 2026-11-20"): `tools/p2k` pinned at a9a286c, every board-local
tool replaced by the shared proteus2kicad tools and `p2k_config.py` keys, no strict-check opt-outs, and the
ribbon header J1 renumbered to the standard 2x20 numbering (finding 12: `IPC_PIN_IDS`, copper unchanged
except the square pin-1 pad, user decision; the control card's J11 gets the same renumbering in its own
repo, pin mapping in STATUS.md). `tools/check_all.sh` prints `ALL CHECKS PASSED` (14 steps since D-STOP; STATUS.md "Last
check output"). Component values are unchanged (user decision).

**HV supplies v2 is not installed and will be redone (user, 2026-11-20): this KiCad project is the starting
point for the redesign.**

**Generation stopped (user decision D-STOP, 2026-11-20; STATUS.md "Generation stopped 2026-11-20"):** the
generators are frozen in `tools/generate/` (they refuse without `--force-regenerate`); `kicad/` and `lib/` are
edited by hand (KiCad, or pcbnew / s-expression scripts in `build/tmp`). `tools/check_all.sh` (14 steps) has
no regenerate / byte-compare step any more.

**Hand edit 1 done (finding 6, 2026-11-20; STATUS.md "Hand edits after generation stopped"):** ADC1-3 VA
(A1, pad 1) on 3V3, VIN (COM2, pad 3) on the filtered input; the deviation (6 pin nets, 3 copper areas, 6
vias) is listed in `tools/hand_edits.py`, through which compare_netlists, check_board, assign_nets --check,
ipc356_diff and gerber_roundtrip run. A further hand edit that differs from Proteus adds its pins / areas /
vias there (and to the STATUS.md deviation table); anything not listed fails.

What remains (in this order, each needs its trigger):

- The J1-1 pad-check exception lives in `tools/check_all.sh` (`check_pads_j1`) because `p2k.check_pads` has
  no per-pad exception key (p2k candidate 30); move it to the key if p2k adds one.
- Open for the user (not blocking): `CURRENT_L1` / `CURRENT_L3` if the inductor should be in the name (the
  user chose the switch names). The control card's J11 net names differ from J1's (STATUS.md J1 / J11 table).
- Report-only findings for the redesign: 2 (15 V "not yet complete"), 8 (LT1014 at 3.3 V, value kept), 10
  (voltage range 1 / 200), 13 (0.127 mm clearances). Not decided: LCSC / BOM fields, Proteus pads on more
  parts, silk cosmetics.

A later session that changes anything starts with `tools/check_all.sh`. Since D-STOP the design is the
committed KiCad files: edit them (never re-run the frozen generators), record every hand edit in STATUS.md
"Hand edits after generation stopped" together with how each Proteus-based check accepts it, and finish with
ALL CHECKS PASSED (tools/p2k pinned at a9a286c).
