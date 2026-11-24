#!/usr/bin/env bash
# Routing chain of the HV supplies rev 3: placed board -> kicad/tube_hv_supplies_rev3.kicad_pcb, every step rerunnable.
#   rev3/tools/route_chain.sh [LAST_STEP_NAME]
# Steps (STATUS.md "Layout, first pass"): placement (tools/make_pcb.py) -> scripted bridge copper
# (tools/bridge_copper.py, locked) -> KiCadRoutingTools steps by net group (routing.json, tools/route_groups.py),
# each locked when done -> pours (make_pcb.py --zones) -> fill -> unlock -> fab fixes.
# Work files: rev3/build/layout/NN_step.kicad_pcb (+ .log / .json). Needs ~/dev/KiCadRoutingTools (.venv) and the
# kicad-agentic-routing skill's scripts.
set -euo pipefail
R="$(cd "$(dirname "$0")/.." && pwd)"
SK="${ROUTING_SKILL:-$HOME/.claude/skills/kicad-agentic-routing/scripts}"
source "$R/../tools/p2k/bin/kicad_env.sh"
export KICAD_PYTHON="$KICAD_MOUNT/bin/python3.11" KICAD_CLI="$R/../tools/p2k/bin/kicad-cli"
source "$SK/kenv.sh"
export ROUTING_CONFIG="$R/routing.json"
LAST="${1:-}"
W="$R/build/layout"; mkdir -p "$W"
OUT="$R/kicad/tube_hv_supplies_rev3.kicad_pcb"
KIPY="$R/../tools/p2k/bin/kipy"
python3 "$R/tools/route_groups.py" >/dev/null
"$KIPY" "$R/tools/make_pcb.py" "$W/00_placed.kicad_pcb" 2>&1 | grep -v "memory leak" | tail -1
N=1; CUR="$W/01_bridge.kicad_pcb"
"$KIPY" "$R/tools/bridge_copper.py" "$W/00_placed.kicad_pcb" "$CUR" 2>&1 | grep -v "memory leak" | tail -1
for b in 00_placed 01_bridge; do for x in kicad_pro kicad_dru; do cp "$R/kicad/tube_hv_supplies_rev3.$x" "$W/$b.$x"; done; done
[ "$LAST" = "bridge" ] && exit 0
step() {    # step NAME GROUPS [route.py options]
    N=$((N + 1)); local out="$W/$(printf %02d "$N")_$1.kicad_pcb"
    echo "== $1"
    python3 -I "$SK/route_step.py" "$CUR" "$out" "${@:2}" 2>&1 | cut -c1-300
    CUR="$out"
    kpy "$SK/lock_tracks.py" "$CUR" lock "$2" | tail -1
    if [ "$LAST" = "$1" ]; then echo "stopped after $1: $CUR"; exit 0; fi
}
HV=(--keepout --keepout-layer User.2 --board-edge-clearance 2.6)
step hvpow hvpow "${HV[@]}" --power-nets '*/UC2' 'IC2' '*/IC2' '*' --power-nets-widths 1.5 1.5 1.5 1.0
step hvsmall hvsmall "${HV[@]}" --power-nets '*/CD1' '*/CD2' '*' --power-nets-widths 0.8 0.8 0.5
step ground ground --power-nets 'PGND' 'GND_STAR' '*CHASSIS' '*BR_DC' '+12V' --power-nets-widths 1.5 1.5 1.0 1.0 0.5
step gate gate --track-width 0.5
step kelvin kelvin --track-width 0.3
step spi spi --track-width 0.25
step analog analog --track-width 0.25
step lv lv --track-width 0.25
step pour pour --power-nets 'GND' '*/GND' '+3V3' --power-nets-widths 0.4 0.4 0.4
echo "routed: $CUR"
