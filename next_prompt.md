# Next prompt

Ready-to-paste prompt for the next agent session. Replaced at the end of every session.

```
Convert the Proteus board in /home/jari/dev/tube_hv_supplies_kicad to KiCad 10: finish Phase 3
(PCB) after the user's pad-size decision (Opus). Phases 0-2 are done; Phase 3 stopped on a user
decision: the board is generated (tools/make_pcb.sh: build_pcb, gerber_to_tracks, assign_nets,
pours_to_zones; 1839 tracks, 141 vias, 21 zones, 1.6 mm), the Proteus copper is clean (stage B 119
groups, 0 shorts / 0 orphans / 0 opens), check_board OK, make_pcb --check byte-identical, but the
KiCad pads of U1 U2 ADC1 ADC2 ADC3 DRV5 DRV6 J1 collide with Proteus tracks (3 shorts, 29
clearance, 3 solder-mask bridges); tools/drc_pending.py holds the DRC / copper checks meanwhile.

Read, in this order: PLAN.md, STATUS.md (phase table, "Phase 3" - steps, design rules, "Phase 3 -
pad sizes (OPEN USER DECISION)" with the per-refdes table and the tested options A / A2 / B,
remaining DRC items, negative tests -, findings 1, 6, 12-14, p2k candidates 15-19, decisions),
tools/p2k/CONVERSION_PLAYBOOK.md (sections 1, 3 "Phase 3" / "Phase 4" and 5), tools/p2k/README.md.
Reference (read only): ~/dev/tube_psu_kicad (tools/gen_footprints.py PROTEUS_PADS with refdes=
rules; STATUS.md Phase 3 / 4).

Start with tools/check_all.sh; it must print "ALL CHECKS PASSED, EXCEPT 2 PENDING USER
DECISION(S)" (15 steps; compare 158/158, 0 wrong-net pins; ERC 0 / 21; check_footprints worst
0.039 mm; make_pcb byte-identical; check_board OK; the two drc_pending lines).

Then, with the user's answer to the pad question (recorded in STATUS.md "Decisions" as a user
decision; if there is no answer in STATUS.md or in this prompt, ASK and stop):
- Apply it in tools/gen_footprints.py the way tools/pad_option_test.sh patches a scratch copy
  (a PROTEUS_PADS refdes set, refdes= rules before the general rule of each symbol, derived
  "<footprint>_ProteusPads" specs with ipc_sizes=True; drop a project spec no part uses any
  more), re-run gen_footprints, the six sheet scripts (only Footprint fields may change),
  p2k.check_footprints --pcbnew, tools/make_pcb.sh. Option A2 (the 8 parts) gave DRC 0 shorts /
  0 clearance / 0 bridges and copper 0 / 0 / 0 in the scratch test.
- Remove tools/drc_pending.py; check_all.sh runs `kipy -m p2k.assign_nets --check` and `p2k drc`
  directly. Update the Phase 2 pad table, the check_pin_order / footprint notes if anything moved.
- Negative-test the applied decision once on a scratch copy (P2K_BOARD), e.g. one part back to
  the KiCad pads -> gen_footprints --check out of date, then DRC errors.
- STATUS.md: phase table (3 done), Phase 3 section (decision applied, results, DRC table without
  the pending row), last check output (ALL CHECKS PASSED), decisions; README status.

Still open and reported only (don't change without asking): the +2V5_BIAS net name (finding 1);
finding 6 (ADC VA / VIN); finding 12 (J1 mirrored numbering); findings 7, 8, 10, 13, 14.

Rules (PLAN.md section 5): don't change tools/p2k or its pin (c5682dd); board-local workarounds in
tools/, noted in STATUS.md "p2k candidates"; don't touch other repos; report design findings,
don't fix them; never use the no_connect pin type; temporary files in build/tmp; never run the
KiCad AppImage with --version (use tools/p2k/bin/kipy and tools/p2k/bin/kicad-cli). At the end:
STATUS.md updated, next_prompt.md replaced with the prompt for Phase 4 (verification:
p2k ipc356_diff and p2k gerber_roundtrip --check in check_all.sh, every new check negative-tested;
preferably a different model), commit and push (git push origin main).
```
