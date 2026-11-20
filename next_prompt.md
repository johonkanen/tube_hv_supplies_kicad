# Next prompt

Ready-to-paste prompt for the next agent session. Replaced at the end of every session.

```
Convert the Proteus board in /home/jari/dev/tube_hv_supplies_kicad to KiCad 10: Phase 1
transcription, sheets 3 (Voltage measurements) and 1 (Power stage) (Fable): the last two sheets.
Phase 0, the Phase 1 preparation and sheets 5, 6, 2 and 4 are done (82/158 parts).

Read, in this order: PLAN.md, STATUS.md ("Phase 1 transcription": per-sheet table, ERC warnings,
how the sheets were drawn, the N/C section; "Transcription rules"; "Off-board inductors L1 / L3";
findings; decisions), tools/p2k/CONVERSION_PLAYBOOK.md (sections 1, 3 "Phase 1" and 5),
tools/p2k/README.md, tools/sheets/_common.py (si8271_cell, shunt_amp_cell, _hcap, term, P,
place_mirrored), tools/sheets/sheet04.py and sheet02.py (the style to follow) and
reference/pin_nets_by_component.md (the IPC nets per pin: the truth for every wire).
Examples from other boards (read only): ~/dev/tube_psu_kicad/tools/sheets/ and
~/dev/tube_power_amp_kicad/tools/sheets/.

Start with tools/check_all.sh; it must print ALL CHECKS PASSED (8 steps; compare 82/158 present,
ERC 0 errors / 29 warnings). Render the PDF pages for reading:
pdftoppm -r 200 -png source/schematic_pdf/hi_voltage_suppliesv2.PDF build/tmp/pdf/hi

Then:
- tools/sheets/sheet03.py -> kicad/03_voltage_measurements.kicad_sch (42 parts): U1 (LMV324A;
  units 1-4 = A-D, supply unit 5 placed once with 3V3 / GND) and the four divider + difference
  amplifier blocks (cell in _common.py, x4; shunt_amp_cell shows the pattern). Global labels:
  UIN, UC3, V_A, U_OUT (sheet 1), UIN_MEAS, UC3_MEAS, V_A_MEAS, U_OUT_MEAS (sheet 5).
- tools/sheets/sheet01.py -> kicad/01_power_stage.kicad_sch (34 parts on the board + L1 / L3):
  the IGBTs Q3 / Q4 / Q7 / Q8, the inductors, capacitors, shunts and the terminals. Terminals
  with _common.term() (B_P, B_N, V_ANODE, GND_PRE, GND_PWR, VPRE, L5, L6, L11, L12); L1 / L3
  with sym("L1") = L_OFFBOARD between L5 - L12 and L11 - L6 (never the plain L symbol). Local
  labels B+, UC6, PREOUT; PDF BRIDGE+ = UIN; the PDF terminal Input_current is GND (no label).
  Global labels to sheet 2 (OUT1, OUT2, PWM1_HI, PWM1_LO, PWM3_HI, PWM3_LO), sheet 3 (UIN, UC3,
  V_A, U_OUT) and sheet 4 (C1_CURRENT, C3_CURRENT, CURRENT_L1, CURRENT_L3). C_Polarized: pin 1
  on the positive net.
- 3V3, GND, 15V_BOOST and +2V5_BIAS already have their PWR_FLAGs on sheet 5; OUT1 / OUT2 and the
  bootstrap nodes on sheet 2: plain power_at / labels. Add a PWR_FLAG only where ERC reports an
  undriven power pin, and note it in STATUS.md.
- Never use the no_connect pin type (STATUS.md "N/C pads"); the only N/C pads are J1-37 / 38.
- After each sheet: tools/p2k/bin/p2k compare_netlists --allow-missing --sheet N (0 missing on
  that sheet, 0 errors), tools/erc.sh (0 errors; explain each warning in STATUS.md; the 8
  temporary isolated-label warnings must disappear: expected at the end 21 = 19 single-pin
  labels + 2 ground_pin_not_ground on DRV1-5 / DRV5-5), render with
  tools/p2k/bin/p2k render_sheet kicad/NN_*.kicad_sch and compare with build/tmp/pdf/hi-N.png.
- Running a sheet script twice must give byte-identical files; check it once per sheet.
- Commit after each finished sheet (with its reports/render PNG).
- When both sheets are done: drop --allow-missing from the compare step in tools/check_all.sh
  (all 158 parts present, every IPC net complete, 0 wrong-net pins), negative-test the final
  check once on a scratch copy (P2K_BOARD), and mark Phase 1 done in STATUS.md.

Open user decisions (don't change without asking): the +2V5_BIAS net name (finding 1); the board
thickness (finding 3, Phase 3); findings 6-8 are reported only.

Rules (PLAN.md section 5): don't change tools/p2k or its pin (c5682dd); board-local workarounds in
tools/ (e.g. _common.py), noted in STATUS.md "p2k candidates"; don't touch other repos; report design
findings, don't fix them; temporary files in build/tmp; never run the KiCad AppImage with
--version (use tools/p2k/bin/kipy and tools/p2k/bin/kicad-cli). At the end: STATUS.md updated
(per-sheet result table, check output, findings, decisions), next_prompt.md replaced with the
prompt for Phase 2 (footprints, Opus), commit and push (git push origin main).
```
