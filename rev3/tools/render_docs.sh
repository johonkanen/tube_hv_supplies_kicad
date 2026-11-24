#!/usr/bin/env bash
# render_docs.sh [BOARD] : the review renders in rev3/docs/ (2D both sides with copper and outlines, 3D views).
#   layout_bottom.png      F side (THT side, faces down): KiCad's view = seen from below, front panel at the top
#   layout_plate_side.png  B side (plate side, SMD and the IGBTs on their bars), same orientation (not mirrored)
#   layout_3d_bottom_face.png (KiCad's "top" render = the F side, which faces down in the chassis),
#   layout_3d_plate_side.png (KiCad's "bottom" render = B, facing the plate), layout_3d_iso.png
set -euo pipefail
R="$(cd "$(dirname "$0")/.." && pwd)"; B="${1:-$R/kicad/tube_hv_supplies_rev3.kicad_pcb}"; D="$R/docs"
CLI="$R/../tools/p2k/bin/kicad-cli"
mkdir -p "$D"
"$R/tools/render.sh" "$B" "$R/build/render_docs" 300 >/dev/null
cp "$R/build/render_docs/f.png" "$D/layout_bottom.png"; cp "$R/build/render_docs/b.png" "$D/layout_plate_side.png"
"$CLI" pcb render --side top -w 1800 -h 2000 -o "$D/layout_3d_bottom_face.png" "$B" >/dev/null 2>&1 || true
"$CLI" pcb render --side bottom -w 1800 -h 2000 -o "$D/layout_3d_plate_side.png" "$B" >/dev/null 2>&1 || true
"$CLI" pcb render --rotate '-50,0,-30' --perspective -w 2000 -h 1500 -o "$D/layout_3d_iso.png" "$B" >/dev/null 2>&1 || true
ls -la "$D"/layout_*.png
