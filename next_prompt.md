# Next prompt

Ready-to-paste prompt for the next agent session. Replaced at the end of every session.

```
Convert the Proteus board in /home/jari/dev/tube_hv_supplies_kicad to KiCad 10: Phase 5, clean-up
(user decisions first). Phases 0-4 are done: schematic (158 parts, compare 158/158, 0 wrong-net pins,
ERC 0 / 21 explained warnings), footprints (158/158 fit, worst 0.039 mm), PCB (tools/make_pcb.sh;
1839 tracks, 141 vias, 21 zones, 4 layers, 1.6 mm; copper after zone fill 119 groups 0 / 0 / 0; DRC 0
errors except 20 accepted courtyards_overlap), Phase 4 verification by a fresh reader (ipc356_diff OK:
574 / 574 records, 113 nets 1:1; gerber round trip: all four copper layers and the 247 drills equal to
Proteus outside the pad shapes, 0 uncovered draws / flashes, except ONE 'other' cluster - the In2.Cu
GND-plane web between J2-1..4, 0.734 mm^2, dropped because J2 has the larger KiCad pads; it connects
nothing). tools/roundtrip_pending.py passes exactly that cluster as a pending user decision.

Read, in this order: PLAN.md, STATUS.md (phase table, "Phase 4" - J2 (pending), review findings 1-4,
earlier findings table, negative tests -, "Phase 3" pad sizes and remaining DRC items, findings,
p2k candidates, decisions), tools/p2k/CONVERSION_PLAYBOOK.md (sections 1, 3 "Phase 5" and 5),
tools/p2k/README.md (place_refdes, REFDES_PLACEMENT, REMOVED_TRACKS, NONCONDUCTOR_LAYERS). Reference
(read only): ~/dev/tube_psu_kicad (finished conversion: STATUS.md Phase 5, p2k_config.py, tools/ -
silk bodies, place_refdes as the last make_pcb step, check_values, the LCSC / BOM step).

Start with tools/check_all.sh; it must print "ALL CHECKS PASSED, EXCEPT 1 PENDING USER DECISION(S)"
(17 steps; compare 158/158, 0 wrong-net pins; ERC 0 / 21; check_footprints worst 0.039 mm;
check_pin_order OK; make_pcb byte-identical; check_board OK; assign_nets after zone fill 119 / 0 / 0 / 0;
drc OK; ipc356_diff OK; round trip 619 pad shape / 7 clearance / 1 other = the pending J2 cluster).

Ask the user first (one list, with the recommendation; do nothing that changes pads or copper before
the answers):
1. J2 pads (PENDING): Proteus pads on J2 (add J2 to PROTEUS_PADS in tools/gen_footprints.py with a
   refdes rule and a PinHeader_2x08_P1.27mm_Vertical_ProteusPads spec, ipc_sizes=True; tested in
   Phase 4: round trip clean, 0 other / 0 clearance, DRC unchanged) - recommended - or keep the KiCad
   pads and accept the cluster for good. Either way remove tools/roundtrip_pending.py afterwards
   (check_all.sh then runs `tools/p2k/bin/p2k gerber_roundtrip --check`; if the cluster is accepted,
   record it in STATUS.md and keep a board-local acceptance, p2k candidate 22).
2. TO-220 pads Q3 Q4 Q7 Q8 (finding 15): Proteus 1.524 x 2.54 rounded rectangle (1.016 mm between
   pads; the collector is on the HV bus) vs KiCad 1.905 x 2.0 (0.635 mm). The IPC size (1.524 x 1.524)
   is wrong for these pads, so ipc_sizes=True does not reproduce them: a Proteus-pad variant needs an
   explicit pad size / shape in the project footprint (board-local, p2k candidates 21 / 23).
3. J1: the square pad is on the pad numbered 2 (Phase 4 review 3) - round pad, or leave; and the
   mirrored numbering itself (finding 12) stays a redesign question.
4. Other pad sizes: Proteus pads on more parts, or keep KiCad pads (Phase 2 pad table; C1-C7 C11 C26
   2.0 vs 1.524 on HV nets).
5. Silk: footprint body graphics vs the Proteus silk, reference positions (p2k place_refdes as the last
   make_pcb step, as tube_psu), the silk DRC warnings (111 / 90 / 3).
6. Dangling Proteus copper (finding 14; REMOVED_TRACKS): the two zero-length OUT1 draws and the 0.9 mm
   15V_BOOST stub on B.Cu.
7. LCSC / BOM fields as tube_psu.
8. Net name +2V5_BIAS (finding 1).

Then implement the answers in the generators (never by hand in kicad/ or lib/), re-run the sheets /
check_footprints / make_pcb as needed, tools/check_all.sh, update the accepted DRC counts, and
negative-test anything new on a scratch copy (P2K_BOARD in build/tmp).

Still open and reported only (don't change without asking): finding 6 (ADC VA / VIN, confirmed
against the datasheet), finding 12 (J1 mirrored numbering), findings 7, 8, 10, 13.

Rules (PLAN.md section 5): don't change tools/p2k or its pin (c5682dd); board-local workarounds in
tools/, noted in STATUS.md "p2k candidates"; don't touch other repos; report design findings,
don't fix them; never use the no_connect pin type; temporary files in build/tmp (don't name a scratch
script after a stdlib module); never run the KiCad AppImage with --version (use tools/p2k/bin/kipy and
tools/p2k/bin/kicad-cli). At the end: STATUS.md updated (phase table, Phase 5 section, last check
output, findings, p2k candidates, decisions), README status, next_prompt.md replaced, commit and
push (git push origin main).
```
