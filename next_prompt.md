# Next prompt

Ready-to-paste prompt for the next agent session. Replaced at the end of every session.

```
Convert the Proteus board in /home/jari/dev/tube_hv_supplies_kicad to KiCad 10: Phase 1
transcription, sheets 2 (Gate drivers) and 4 (Current measurements) (Fable). Phase 0, the Phase 1
preparation and sheets 5 and 6 are done (22/158 parts).

Read, in this order: PLAN.md, STATUS.md ("Phase 1 transcription": per-sheet table, ERC warnings,
how sheets 5 / 6 were drawn; "Transcription rules"; findings; decisions),
tools/p2k/CONVERSION_PLAYBOOK.md (sections 1, 3 "Phase 1" and 5), tools/p2k/README.md,
tools/sheets/_common.py, tools/sheets/sheet05.py and sheet06.py (the style to follow) and
reference/pin_nets_by_component.md (the IPC nets per pin: the truth for every wire).
Examples from other boards (read only): ~/dev/tube_psu_kicad/tools/sheets/ (its _common.py has a
si8275_cell for a gate-driver block) and ~/dev/tube_power_amp_kicad/tools/sheets/.

Start with tools/check_all.sh; it must print ALL CHECKS PASSED (8 steps; compare 22/158 present,
ERC 0 errors / 31 warnings). Render the PDF pages for reading:
pdftoppm -r 200 -png source/schematic_pdf/hi_voltage_suppliesv2.PDF build/tmp/pdf/hi

Then:
- tools/sheets/sheet02.py -> kicad/02_gate_drivers.kicad_sch (26 parts): DRV1, DRV2, DRV5, DRV6
  (SI8271 box) with D2 / D18 bootstrap, R21-R25, R31-R35, C23-C25, C30-C33, C38, C43, C46. Write
  the driver cell once in tools/sheets/_common.py (x4). The refdes R23 / R25 / R32 / R35 are
  printed next to the GND2 pins in the PDF but are the 8R resistors on OUT- (read the nets from
  the IPC table, not from the label positions). PDF 15V = 15V_BOOST (power symbol). One PWR_FLAG
  on each floating driver node: the bootstrap nodes #00021 (DRV1-8) and #00036 (DRV5-8) and the
  high-side GND2 nets OUT1 (DRV1-5) and OUT2 (DRV5-5). Global labels: OUT1, OUT2, PWM1_HI,
  PWM1_LO, PWM3_HI, PWM3_LO (sheet 1), G1_HI, G1_LO, G3_HI, G3_LO (sheet 5, already drawn).
- tools/sheets/sheet04.py -> kicad/04_current_measurements.kicad_sch (34 parts): U2 (LT1014;
  units 1-4 = A-D, supply unit 5 placed once with 3V3 / GND) and the four shunt amplifiers
  (cell in _common.py, x4). Global labels: C1_CURRENT, C3_CURRENT, CURRENT_L1, CURRENT_L3
  (sheet 1), INPUT_CURRENT_MEAS, C1_CURRENT_MEAS, C2_CURRENT_MEAS, C3_CURRENT_MEAS (sheet 5).
  The net names do not match what is measured (finding 7): keep the IPC names.
- 3V3, GND, 15V_BOOST and +2V5_BIAS already have their PWR_FLAGs on sheet 5: plain power_at.
- After each sheet: tools/p2k/bin/p2k compare_netlists --allow-missing --sheet N (0 missing on
  that sheet, 0 errors), tools/erc.sh (0 errors; explain each warning in STATUS.md; the 4 + 4
  temporary isolated-label warnings of the J1 globals must disappear with these sheets, new
  temporary ones appear for the globals going to sheet 1), render with
  tools/p2k/bin/p2k render_sheet kicad/NN_*.kicad_sch and compare with build/tmp/pdf/hi-N.png.
- Running a sheet script twice must give byte-identical files; check it once per sheet.
- Commit after each finished sheet (with its reports/render PNG).

Open user decisions (don't change without asking): the +2V5_BIAS net name (finding 1); the board
thickness (finding 3, Phase 3); findings 6-8 are reported only.

Rules (PLAN.md section 5): don't change tools/p2k or its pin (c5682dd); board-local workarounds in
tools/ (e.g. _common.py), noted in STATUS.md "p2k candidates"; don't touch other repos; report design
findings, don't fix them; temporary files in build/tmp; never run the KiCad AppImage with
--version (use tools/p2k/bin/kipy and tools/p2k/bin/kicad-cli). At the end: STATUS.md updated
(per-sheet result table, check output, findings, decisions), next_prompt.md replaced with the
prompt for the next transcription session (sheets 3 and 1), commit and push (git push origin main).
```
