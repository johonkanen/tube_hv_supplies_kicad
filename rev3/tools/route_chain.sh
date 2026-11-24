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
N=1; CUR="$W/01_bridge.kicad_pcb"
if [ -z "${FROM:-}" ]; then
python3 "$R/tools/route_groups.py" >/dev/null
"$KIPY" "$R/tools/make_pcb.py" "$W/00_placed.kicad_pcb" 2>&1 | grep -v "memory leak" | tail -1
"$KIPY" "$R/tools/bridge_copper.py" "$W/00_placed.kicad_pcb" "$CUR" 2>&1 | grep -v "memory leak" | tail -1
fi
for b in 00_placed 01_bridge; do for x in kicad_pro kicad_dru; do cp "$R/kicad/tube_hv_supplies_rev3.$x" "$W/$b.$x"; done; done
[ "$LAST" = "bridge" ] && exit 0
FROM="${FROM:-}"     # FROM=stepname: reuse the boards of the earlier steps, rerun from that step on
step() {    # step NAME GROUPS [route.py options]
    N=$((N + 1)); local out="$W/$(printf %02d "$N")_$1.kicad_pcb"
    if [ -n "$FROM" ] && [ "$FROM" != "$1" ]; then CUR="$out"; echo "== $1 (reused)"; return 0; fi
    FROM=""
    echo "== $1"
    python3 -I "$SK/route_step.py" "$CUR" "$out" "${@:2}" 2>&1 | cut -c1-300
    CUR="$out"
    kpy "$SK/lock_tracks.py" "$CUR" lock "$2" | tail -1
    if [ "$LAST" = "$1" ]; then echo "stopped after $1: $CUR"; exit 0; fi
}
HV=(--keepout --keepout-layer User.2 --board-edge-clearance 2.6 --layer-costs 1 6)
HVG=()
step hvpow hvpow "${HV[@]}" --max-iterations 20000000 --power-nets '*/UC2' 'IC2' '*/IC2' '*' --power-nets-widths 1.5 1.5 1.5 1.0
step hvsmall hvsmall "${HV[@]}" --power-nets '*/CD1' '*/CD2' '*' --power-nets-widths 0.8 0.8 0.5
step ground ground --keepout --keepout-layer User.3 --escalation board --max-iterations 5000000 --power-nets 'PGND' 'GND_STAR' '*CHASSIS' '*BR_DC' --power-nets-widths 1.2 1.2 1.0 1.0
step gate gate --track-width 0.5 --escalation board "${HVG[@]}"
step kelvin kelvin --track-width 0.3 --escalation board
step spi spi --track-width 0.25 --escalation board
step analog analog --track-width 0.25 --escalation board
step lv lv --track-width 0.25 --escalation board
step supply pour,+12V --escalation board --power-nets 'GND' '+3V3' '+12V' --power-nets-widths 0.4 0.4 0.5
# pours (star island, control ground), fill, then whatever is still open
N=$((N + 1)); P="$W/$(printf %02d "$N")_pour.kicad_pcb"
"$KIPY" "$R/tools/make_pcb.py" --zones "$CUR" "$P" 2>&1 | grep -v "memory leak" | tail -1
for x in kicad_pro kicad_dru; do cp "$R/kicad/tube_hv_supplies_rev3.$x" "${P%.kicad_pcb}.$x"; done; CUR="$P"
[ "$LAST" = "pour" ] && { echo "stopped after pour: $CUR"; exit 0; }
step leftover hvpow,hvsmall,ground,gate,kelvin,spi,analog,lv,pour --track-width 0.25 --max-iterations 20000000
N=$((N + 1)); P="$W/$(printf %02d "$N")_refill.kicad_pcb"
kpy "$SK/fill_zones.py" "$CUR" "$P" | tail -1; CUR="$P"
for x in kicad_pro kicad_dru; do cp "$R/kicad/tube_hv_supplies_rev3.$x" "${P%.kicad_pcb}.$x"; done
kpy "$SK/lock_tracks.py" "$CUR" unlock | tail -1
cp "$CUR" "$OUT"
echo "wrote $OUT"
