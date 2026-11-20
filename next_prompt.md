# Next prompt

Ready-to-paste prompt for the next agent session. Replaced at the end of every session.

```
Convert the Proteus board in /home/jari/dev/tube_hv_supplies_kicad to KiCad 10: Phase 4,
independent verification (preferably Fable, a fresh reader who did not build the board). Phases 0-3
are done: schematic (158 parts, compare 158/158, 0 wrong-net pins, ERC 0 / 21 explained warnings),
footprints (158/158 fit, worst 0.039 mm), PCB (tools/make_pcb.sh: build_pcb, gerber_to_tracks,
assign_nets, pours_to_zones; 1839 tracks, 141 vias, 21 zones, 4 layers, 1.6 mm; copper after zone
fill 119 groups 0 shorts / 0 orphans / 0 opens; DRC 0 errors except 20 accepted courtyards_overlap).
Pad sizes: user decision A2 - Proteus pads on exactly U1 U2 ADC1 ADC2 ADC3 DRV5 DRV6 J1
(PROTEUS_PADS in tools/gen_footprints.py), KiCad pads everywhere else.

Read, in this order: PLAN.md, STATUS.md (phase table, "Phase 3" - steps, design rules, pad sizes
(decided), remaining DRC items, negative tests -, "Phase 2" pad-size table, findings, p2k
candidates, decisions), tools/p2k/CONVERSION_PLAYBOOK.md (sections 1, 3 "Phase 4" and 5),
tools/p2k/README.md (gerber_roundtrip, ipc356_diff and their config keys STACKED_VIAS,
DRILL_SMALLER, DRILL_EXCELLON, ROUNDTRIP). Reference (read only): ~/dev/tube_psu_kicad (finished
conversion: STATUS.md Phase 4, p2k_config.py ROUNDTRIP / DRILL_* keys, tools/check_all.sh).

Start with tools/check_all.sh; it must print "ALL CHECKS PASSED" (15 steps; compare 158/158, 0
wrong-net pins; ERC 0 / 21; check_footprints worst 0.039 mm; check_pin_order OK; make_pcb
byte-identical; check_board OK; assign_nets after zone fill 119 / 0 / 0 / 0; drc OK).

Then:
1. `tools/p2k/bin/p2k ipc356_diff`: kicad-cli IPC-D-356A export vs the Proteus file (every pad / via /
   hole within 0.05 mm, same side, THT / SMD, nets 1:1 by pad sets, N/C equal). Explain every
   difference; config keys only where the tool already has one (STACKED_VIAS etc.).
2. `tools/p2k/bin/p2k gerber_roundtrip` (then `--check`): KiCad gerbers + drill vs the Proteus set
   per copper layer, clusters classified (pad shape / clearance / zone fill / other), centre-line
   coverage both ways, drills. Expected differences: KiCad pad shapes on every part outside
   PROTEUS_PADS (Phase 2 pad table: larger pads and, for C1-C7 C11 C26 / Q3 Q4 Q7 Q8 / J2, larger
   drills - no KiCad drill is smaller), zone fill / clearance. Every "other" cluster or uncovered
   draw / flash is a finding to explain (or a real conversion error to fix in the generators).
   Use ROUNDTRIP config keys only as tube_psu does, each justified in STATUS.md.
3. Add both checks to tools/check_all.sh (Phase 4 steps) and make them pass.
4. Review as a fresh reader: the generating scripts (tools/gen_footprints.py, make_pcb.sh,
   p2k_config.py, the sheet scripts), spot-check the easy-to-get-wrong places (thermal reliefs,
   floating non-conductor graphics, mounting holes H1-H4, the 38 bottom-side parts, multi-pad pins
   such as the blade terminals, the KRL2012 shunts R29 R30 R72 R75, single-pin nets, J1's mirrored
   numbering), confirm or refute every earlier finding in STATUS.md.
5. Negative-test every new check on a scratch copy (P2K_BOARD in build/tmp): e.g. move a track,
   change a net, shift a pad 0.1 mm, drop a via -> the new check fails.

Still open and reported only (don't change without asking): the +2V5_BIAS net name (finding 1);
finding 6 (ADC VA / VIN); finding 12 (J1 mirrored numbering); findings 7, 8, 10, 13, 14.

Rules (PLAN.md section 5): don't change tools/p2k or its pin (c5682dd); board-local workarounds in
tools/, noted in STATUS.md "p2k candidates"; don't touch other repos; report design findings,
don't fix them; never use the no_connect pin type; temporary files in build/tmp; never run the
KiCad AppImage with --version (use tools/p2k/bin/kipy and tools/p2k/bin/kicad-cli). At the end:
STATUS.md updated (phase table, Phase 4 section, last check output, findings, p2k candidates,
decisions), README status, next_prompt.md replaced with the prompt for Phase 5 (clean-up: user
decisions first - silk, refdes placement, dangling tracks, LCSC / BOM as tube_psu), commit and push
(git push origin main).
```
