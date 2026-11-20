# Next prompt

Ready-to-paste prompt for the next agent session. Replaced at the end of every session.

```
Convert the Proteus board in /home/jari/dev/tube_hv_supplies_kicad to KiCad 10: Phase 1 preparation
(Opus). Phase 0 is done.

Read, in this order: PLAN.md, STATUS.md (Phase 0, "Notes for Phase 1", findings, decisions),
tools/p2k/CONVERSION_PLAYBOOK.md (sections 1, 3 "Phase 1" and 5), tools/p2k/README.md. The finished
reference conversion is ~/dev/tube_psu_kicad (same tools): read its tools/make_part_map.py,
tools/gen_symbols.py, tools/erc.sh, tools/check_all.sh, tools/sheets/_common.py and its STATUS.md
"Transcription rules" for how Phase 1 preparation was done. Read it only; don't change it.

Start with tools/check_all.sh; it must print ALL CHECKS PASSED (3 steps: KiCad environment
pcbnew 10.0.7; ipc356 nets=113 records=574 parts=158 vias=141 holes=4: OK; check_sources: OK).
Render the PDF pages for reading: pdftoppm -r 200 -png source/schematic_pdf/hi_voltage_suppliesv2.PDF build/tmp/pdf/hi

Do Phase 1 preparation as playbook section 3 describes:
- tools/make_part_map.py -> lib/part_map.csv (refdes -> sheet, lib_id, value; values from ROOT.DSN
  via p2k.pdsprj, pages via p2k.pdftext; KiCad refdes B_P / B_N for B+ / B-), with --check;
- tools/gen_symbols.py -> lib/tube_hv_supplies.kicad_sym (pins = IPC ids: ADC1-3 use A1/A2/COM1/
  COM2/K1/K2, terminals one pin "1"), with --check; p2k check_symbols passes;
- p2k make_skeleton (kicad/ project, root sheet, 6 sub-sheets from SHEETS), tools/erc.sh;
- decide how the off-board inductors L1 / L3 (PDF page 1, not in the IPC) are handled (STATUS.md
  "Notes for Phase 1"); ask the user if it changes the netlist;
- write the transcription rules into STATUS.md (power symbols, labels in IPC spelling, global
  labels for multi-sheet nets, N/C pins J1-37/38, the 19 single-pin nets, grid 1.27 mm);
- add the new steps to tools/check_all.sh (part map, symbols, check_symbols, ERC,
  compare_netlists --allow-missing) and make it pass.

Open user decisions (don't change without asking): the +2V5_BIAS net name (finding 1, REF1 looks
like the 1.5 V version); the board thickness (finding 3, Phase 3).

Rules (PLAN.md section 5): don't change tools/p2k or its pin (c5682dd); board-local workarounds,
noted in STATUS.md "p2k candidates"; don't touch other repos; report design findings, don't fix
them; temporary files in build/tmp; never run the KiCad AppImage with --version (use
tools/p2k/bin/kipy and tools/p2k/bin/kicad-cli). At the end: STATUS.md updated (result, check
output, findings, decisions), next_prompt.md replaced with the prompt for the first transcription
session (Fable, easiest sheets first: 5 and 6), commit and push (git push origin main).
```
