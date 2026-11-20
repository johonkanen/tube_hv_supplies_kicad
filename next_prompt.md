# Next prompt

Ready-to-paste prompt for the next agent session. Replaced at the end of every session.

```
Convert the Proteus board in /home/jari/dev/tube_hv_supplies_kicad to KiCad 10: Phase 1
transcription, sheets 5 (Reference and connector) and 6 (ADC) (Fable). Phase 0 and the Phase 1
preparation are done.

Read, in this order: PLAN.md, STATUS.md (Phase 1 preparation: part map, symbols, L1/L3 decision,
pinouts, and above all "Transcription rules"; findings; decisions), tools/p2k/CONVERSION_PLAYBOOK.md
(sections 1, 3 "Phase 1" and 5), tools/p2k/README.md, tools/sheets/_common.py and
reference/pin_nets_by_component.md (the IPC nets per pin: the truth for every wire).
Examples of finished sheet scripts (read only, don't change those repos): ~/dev/tube_power_amp_kicad/
tools/sheets/sheet0[1-3].py (same _common helpers: term, sym, sh_value, P) and
~/dev/tube_psu_kicad/tools/sheets/ (sheet04.py has a 2x25 header with many labels).

Start with tools/check_all.sh; it must print ALL CHECKS PASSED (8 steps; compare 0/158 present).
Render the PDF pages for reading: pdftoppm -r 200 -png source/schematic_pdf/hi_voltage_suppliesv2.PDF build/tmp/pdf/hi

Then:
- tools/sheets/sheet05.py -> kicad/05_reference_connector.kicad_sch: REF1 (ISL21010 box,
  pins 1=GND 2=VIN 3=VOUT), C8, C21, R74, R73, C22, +2V5_BIAS; J1 (40 pins) with the IPC
  net names on every pin (J1-1..8 carry the *_MEAS nets; the ADB0-ADB7 aliases become text at
  most), no-connect flags on J1-37/38, local labels for the 18 unused signals, global labels for
  the multi-sheet nets, flagged power symbols where the rails enter (3V3, GND, 15V_BOOST on
  J1-39/40); the "15V - 15V_boost / Not yet complete" link as a text note.
- tools/sheets/sheet06.py -> kicad/06_adc.kicad_sch: J2, R78-R80, C35-C37, ADC1-ADC3 (pin ids
  A1/A2/COM1/COM2/K1/K2; draw the wiring exactly as the PDF and the IPC have it, including VIN on
  3V3 and VA on the filtered input: finding 6, reproduce, don't fix), R76/R77, C27-C29, SCL/SDA
  global labels, FLOATING local label on ADC3-K2.
- After each sheet: tools/p2k/bin/p2k compare_netlists --allow-missing --sheet N (0 missing on
  that sheet, 0 errors), tools/erc.sh (0 errors; explain each warning in STATUS.md), render with
  tools/p2k/bin/p2k render_sheet kicad/NN_*.kicad_sch and compare with build/tmp/pdf/hi-N.png.
- Running a sheet script twice must give byte-identical files (deterministic UUIDs); check it once.

Open user decisions (don't change without asking): the +2V5_BIAS net name (finding 1); the board
thickness (finding 3, Phase 3); findings 6-8 are reported only.

Rules (PLAN.md section 5): don't change tools/p2k or its pin (c5682dd); board-local workarounds in
tools/ (e.g. _common.py), noted in STATUS.md "p2k candidates"; don't touch other repos; report design
findings, don't fix them; temporary files in build/tmp; never run the KiCad AppImage with
--version (use tools/p2k/bin/kipy and tools/p2k/bin/kicad-cli). At the end: STATUS.md updated
(per-sheet result table, check output, findings, decisions), next_prompt.md replaced with the
prompt for the next transcription session (sheets 2 and 4), commit and push (git push origin main).
```
