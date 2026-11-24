#!/usr/bin/env bash
# render.sh BOARD OUTDIR [DPI] : PNGs of the bottom (F, seen from below = KiCad's view) and plate side (B, mirrored
# so it reads as seen from above) with outline, fab and comments layers.
set -euo pipefail
B=$1; O=$2; DPI=${3:-150}
CLI="$(cd "$(dirname "$0")/../.." && pwd)/tools/p2k/bin/kicad-cli"
mkdir -p "$O"
$CLI pcb export pdf --mode-single -l F.Cu,F.Fab,F.Silkscreen,Edge.Cuts,User.Comments --scale 1 -o "$O/f.pdf" "$B" >/dev/null
$CLI pcb export pdf --mode-single -l B.Cu,B.Fab,B.Silkscreen,Edge.Cuts,User.Comments --mirror --scale 1 -o "$O/b.pdf" "$B" >/dev/null
for s in f b; do pdftoppm -r "$DPI" -png -singlefile "$O/$s.pdf" "$O/$s"; done
python3 - "$O" <<'PY'
import sys
from PIL import Image, ImageChops
o = sys.argv[1]
for s in "fb":
    im = Image.open(f"{o}/{s}.png").convert("RGB")
    bb = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    im.crop(bb).save(f"{o}/{s}.png")
    print(s, im.crop(bb).size)
PY
