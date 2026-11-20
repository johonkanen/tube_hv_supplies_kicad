# Next prompt

Ready-to-paste prompt for the next agent session. Replaced at the end of every session.

```
Convert the Proteus board in /home/jari/dev/tube_hv_supplies_kicad to KiCad 10: Phase 2,
footprints (Opus). Phases 0 and 1 are done: all 158 parts are drawn on 6 sheets (plus the
off-board L1 / L3), the netlist equals the IPC (0 wrong-net pins, every net complete), ERC 0
errors / 21 explained warnings.

Read, in this order: PLAN.md, STATUS.md (phase table, "Pinouts", "Off-board inductors L1 / L3",
the refdes table, "Notes for Phase 1" on pin-id families and the bottom-side parts, findings,
p2k candidates, decisions), tools/p2k/CONVERSION_PLAYBOOK.md (sections 1, 3 "Phase 2" and 5),
tools/p2k/README.md (p2k.footprints, check_footprints, fpgeom), lib/part_map.csv (device and
package per refdes), reference/ipc356_pads.csv and reference/pin_nets_by_component.md.
Reference (read only): ~/dev/tube_psu_kicad/tools/gen_footprints.py and its p2k_config.py
(same p2k version, Phase 2 done); ~/dev/tube_power_amp_kicad for the terminal footprints.

Start with tools/check_all.sh; it must print ALL CHECKS PASSED (8 steps; compare 158/158 parts,
423 pins, 0 wrong-net pins, 115 / 115 net groups complete; ERC 0 errors / 21 warnings).

Then:
- tools/gen_footprints.py (RULES and PROJECT of this board; the shared code is p2k.footprints)
  -> lib/footprint_map.csv (refdes -> footprint) and lib/tube_hv_supplies.pretty. Assign by
  symbol + IPC pad pattern (pad count, span, pad size, drill). Keep KiCad pad sizes
  (FOOTPRINT_PAD_SIZES = "kicad"); Proteus sizes only where DRC forces it later (user decision).
- p2k_config.py: OFF_BOARD_PARTS = L1, L3 (no footprint, excluded from the board), the
  footprint settings the tools need, the mounting-hole footprint (4 holes, 3.0 mm PLATED,
  6.35 mm ring on all four layers, no net) for Phase 3.
- Special parts: the six two-hole TERMINAL parts (B_P, B_N, V_ANODE, GND_PRE, GND_PWR, VPRE:
  both holes are pin 1) and the four one-hole ones (L5, L6, L11, L12: 1.524 mm hole, 2.54 mm
  pad); ADC1-ADC3 (SOT-23-6 with the Proteus pin ids A1, A2, COM2, K2, K1, COM1 = pads 1-6);
  REF1 (SOT-23, Proteus 1 / 2 / 3 on JEDEC 3 / 1 / 2: the pin-order fit must confirm it);
  Q3 / Q4 / Q7 / Q8 (TO-220, 1 = G, 2 = C, 3 = E); D2 / D18 (pads A / C); J1 (2x20, 1.27 mm,
  pins 37 / 38 N/C) and J2 (2x8); the 38 bottom-side parts (mirror in the fit).
- p2k check_footprints (and --pcbnew): every part fits the IPC pads within 0.05 mm; writes
  reports/footprint_fit.csv (the placement input for Phase 3). Run the pin-order check (unmoved
  KiCad base footprint with the Proteus renumbering) and report every pinout oddity in
  STATUS.md (ADC1-3: finding 6 expects A1 = pad 1 and COM2 = pad 3).
- The sheet scripts fill the Footprint field from the map: re-run all six (tools/sheets/
  sheet0N.py), then compare_netlists and ERC must be unchanged (0 wrong-net pins, 21 warnings).
- Add the new steps to tools/check_all.sh (footprint map / library up to date, footprint fit)
  and negative-test each once on a scratch copy (P2K_BOARD).

Open user decisions (don't change without asking): the +2V5_BIAS net name (finding 1); the board
thickness (finding 3, Phase 3); pad sizes (KiCad by default); findings 6-8, 10 and 11 are
reported only.

Rules (PLAN.md section 5): don't change tools/p2k or its pin (c5682dd); board-local workarounds in
tools/, noted in STATUS.md "p2k candidates"; don't touch other repos; report design findings,
don't fix them; never use the no_connect pin type (N/C pads are passive pins with no-connect
flags); temporary files in build/tmp; never run the KiCad AppImage with --version (use
tools/p2k/bin/kipy and tools/p2k/bin/kicad-cli). At the end: STATUS.md updated (phase table, fit
result, check output, findings, decisions), next_prompt.md replaced with the prompt for Phase 3
(PCB, Opus), commit and push (git push origin main).
```
