#!/usr/bin/env bash
# Phase 3: rebuild kicad/tube_hv_supplies.kicad_pcb (p2k make_pcb, default PCB_STEPS: build_pcb,
# gerber_to_tracks, assign_nets, pours_to_zones, place_refdes). --check: rebuild into build/tmp and
# fail unless the board, reports/pour_nets.json and the stage A/B part of reports/assign_nets.txt
# are byte-identical. Kept as a one-liner because check_all.sh and tools/p2k/tools/regress.sh call it.
exec "$(dirname "$0")/p2k/bin/p2k" make_pcb "$@"
