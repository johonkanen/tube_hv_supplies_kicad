#!/usr/bin/env bash
# Run every verification step. Exit status is non-zero if any step fails.
# Each phase adds its steps here (playbook principle 5, PLAN.md section 6).
# The tools are the proteus2kicad submodule in tools/p2k; board values in p2k_config.py.
set -u
cd "$(dirname "$0")/.."
[ -x tools/p2k/bin/p2k ] || { echo "tools/p2k missing: git submodule update --init"; exit 1; }
fail=0
mkdir -p build/tmp
log=build/tmp/check_all.log; : > "$log"
step() {
    echo "== $1" | tee -a "$log"; shift
    "$@" 2>&1 | tee -a "$log"
    [ "${PIPESTATUS[0]}" -eq 0 ] || { echo "!! FAILED: $*" | tee -a "$log"; fail=1; }
}

# Phase 0: environment and sources
step "KiCad environment" tools/p2k/bin/kipy -c "import pcbnew; v = pcbnew.GetBuildVersion(); print('pcbnew', v); assert v.startswith('10.0.7'), v"
step "IPC-D-356A parser self-check" tools/p2k/bin/p2k ipc356 --check
step "Gerber X2 export vs IPC (pads, vias, drills, outline)" tools/p2k/bin/p2k check_sources
# Phase 1: schematic
step "Part map up to date" python3 tools/make_part_map.py --check
step "Symbol library up to date" python3 tools/gen_symbols.py --check
step "Symbol pin sets vs IPC" tools/p2k/bin/p2k check_symbols
step "ERC" tools/erc.sh
# all 6 sheets drawn: every part must be present (no --allow-missing)
step "Netlist comparison vs IPC" tools/p2k/bin/p2k compare_netlists
# Phase 2: footprints
step "Footprint library, map and fp-lib-table up to date" python3 tools/gen_footprints.py --check
step "Footprints vs IPC pad geometry (fit and pcbnew placement)" tools/p2k/bin/kipy -m p2k.check_footprints --pcbnew
step "Pin order vs unmoved KiCad base footprints" python3 tools/check_pin_order.py
# Phase 3: PCB (build_pcb, gerber_to_tracks, assign_nets, pours_to_zones on all four layers)
step "PCB rebuilt from schematic + gerbers, up to date" tools/make_pcb.sh --check
step "Board pads, holes, vias vs IPC (position, size, nets 1:1)" tools/p2k/bin/kipy -m p2k.check_board
# pad sizes: KiCad pads except the PROTEUS_PADS parts of tools/gen_footprints.py (user decision A2)
step "Board copper connectivity after zone fill" tools/p2k/bin/kipy -m p2k.assign_nets --check
step "DRC with schematic parity" tools/p2k/bin/p2k drc
# Phase 4: the finished board against the Proteus CADCAM files (independent of the generators)
step "IPC-D-356 from the board vs Proteus (pads, vias, holes, nets)" tools/p2k/bin/p2k ipc356_diff
# J2 pad sizes: the one 'other' cluster (In2.Cu web between J2-1..4) is a pending user decision;
# after it: tools/p2k/bin/p2k gerber_roundtrip --check
step "Gerber round trip vs Proteus (copper XOR, coverage, drills)" python3 tools/roundtrip_pending.py

echo
pending=$(grep -c "PENDING USER DECISION" "$log")
if [ $fail -ne 0 ]; then echo "SOME CHECKS FAILED"
elif [ "$pending" -ne 0 ]; then echo "ALL CHECKS PASSED, EXCEPT $pending PENDING USER DECISION(S):"; grep "PENDING USER DECISION" "$log" | sed 's/^/  /'
else echo "ALL CHECKS PASSED"; fi
exit $fail
