# Next prompt

Ready-to-paste prompt for the next agent session. Replaced at the end of every session.

```
Convert the Proteus board in /home/jari/dev/tube_hv_supplies_kicad to KiCad 10: Phase 3,
PCB (Opus). Phases 0-2 are done: 158 parts on 6 sheets (plus the off-board L1 / L3), netlist
equal to the IPC, ERC 0 errors / 21 explained warnings; every part has a footprint that fits
the IPC pads within 0.05 mm (worst 0.039 mm, pcbnew placement checked), placement in
reports/footprint_fit.csv.

Read, in this order: PLAN.md, STATUS.md (phase table, "Phase 2" - footprints, pin order, the
per-refdes pad / drill table, negative tests -, findings 3, 6, 12, p2k candidates, decisions),
tools/p2k/CONVERSION_PLAYBOOK.md (sections 1, 3 "Phase 3" and 5), tools/p2k/README.md (the PCB
tools and the p2k_config keys PCB_THICKNESS, PCB_RULES, HOLE_FOOTPRINT, DRC_ACCEPTED, COPPER).
Reference (read only): ~/dev/tube_psu_kicad (same p2k version, 4 layers with pours on every
layer, Phase 3 done: tools/make_pcb.sh, tools/measure_gaps.py, p2k_config.py PCB_RULES /
DRC_ACCEPTED, STATUS.md Phase 3) and ~/dev/tube_power_amp_kicad (make_pcb.sh, plated mounting
holes with a 6.35 mm pad).

Start with tools/check_all.sh; it must print ALL CHECKS PASSED (11 steps; compare 158/158
parts, 423 pins, 0 wrong-net pins, 115 / 115 net groups; ERC 0 errors / 21 warnings;
check_footprints 158/158 fitted, worst 0.039 mm; check_pin_order OK).

Then:
- Ask the user for the board thickness first (finding 3: the CADCAM READ-ME stack adds up to
  2.267 mm; PCB_THICKNESS) unless STATUS.md records an answer.
- Measure the Proteus copper gaps (board-local tools/measure_gaps.py after tube_psu) and set
  PCB_RULES in p2k_config.py (vias 0.5 / 0.3 x139 and 1.016 / 0.381 x2, thinnest track
  0.1524 mm). HOLE_FOOTPRINT / HOLE_VALUE are set (plated 3.0 mm, 6.35 mm pad on all layers).
- tools/make_pcb.sh (build_pcb, gerber_to_tracks, assign_nets, pours_to_zones; pours on all
  four layers, Inner 2 with 131 clear holes; no stacked vias, STACKED_VIAS stays 0) and
  make_pcb.sh --check (byte-identical rebuild in a temporary directory).
- check_board, assign_nets --check (0 shorts / 0 orphans / 0 opens after zone fill), p2k drc
  with schematic parity (0 shorts, 0 unconnected, 0 parity); list and justify every remaining
  DRC type in DRC_ACCEPTED.
- Pads: KiCad pad sizes by default (FOOTPRINT_PAD_SIZES = "kicad"). Where DRC shows KiCad pads
  colliding with Proteus copper (likely: the 1.27 mm headers J1 / J2 with 1.0 mm KiCad pads,
  the long SOT-23-6 / TSSOP-14 / SOIC-8 pads, CP / TO-220 rings), make a per-refdes table and
  ASK THE USER before switching parts to the Proteus pads (tube_psu did it with a PROTEUS_PADS
  refdes set and `refdes=` rules). No KiCad drill is smaller than Proteus so far.
- Add the Phase 3 steps to tools/check_all.sh and negative-test each once on a scratch copy
  (P2K_BOARD).

Open user decisions (don't change without asking): the +2V5_BIAS net name (finding 1); the board
thickness (finding 3); pad sizes per refdes (STATUS.md Phase 2 table); J1 numbering (finding 12,
reproduced with the rows-swapped header on top); findings 6-8, 10 and 12 are reported only
(finding 11 answered: intended).

Rules (PLAN.md section 5): don't change tools/p2k or its pin (c5682dd); board-local workarounds in
tools/, noted in STATUS.md "p2k candidates"; don't touch other repos; report design findings,
don't fix them; never use the no_connect pin type (N/C pads are passive pins with no-connect
flags); temporary files in build/tmp; never run the KiCad AppImage with --version (use
tools/p2k/bin/kipy and tools/p2k/bin/kicad-cli). At the end: STATUS.md updated (phase table,
results, check output, findings, decisions), next_prompt.md replaced with the prompt for Phase 4
(verification, preferably a different model), commit and push (git push origin main).
```
