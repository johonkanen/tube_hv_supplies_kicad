#!/usr/bin/env bash
# FROZEN (generation stopped, STATUS.md "Decisions" D-STOP): kicad/tube_hv_supplies.kicad_pcb is edited by
# hand since then, and a rebuild would throw the hand edits away. Kept as the record of how rev A was built:
# p2k make_pcb, default PCB_STEPS (build_pcb, gerber_to_tracks, assign_nets, pours_to_zones, place_refdes).
# Runs only with --force-regenerate (first argument; use a scratch copy, P2K_BOARD / P2K_PCB).
if [ "${1:-}" != "--force-regenerate" ]; then
    echo "make_pcb.sh: frozen since generation stopped (STATUS.md Decisions, D-STOP); the board is edited by hand." >&2
    echo "make_pcb.sh: pass --force-regenerate (first argument) only to reproduce the history in a scratch copy." >&2
    exit 2
fi
shift
exec "$(dirname "$0")/../p2k/bin/p2k" make_pcb "$@"
