#!/usr/bin/env bash
# render.sh BOARD OUTDIR [DPI] [X0,Y0,X1,Y1] : PNGs of the bottom side (f.png: F layers, as KiCad shows it = seen
# from below, front panel at the top, x = chassis x) and the plate side (b.png: B layers in the same orientation,
# not mirrored, so the two line up). Optional window in CHASSIS mm (crops f_win.png / b_win.png).
set -euo pipefail
B=$1; O=$2; DPI=${3:-150}; WIN=${4:-}
CLI="$(cd "$(dirname "$0")/../.." && pwd)/tools/p2k/bin/kicad-cli"
mkdir -p "$O"
$CLI pcb export pdf --mode-single -l F.Cu,F.Fab,F.Silkscreen,Edge.Cuts,User.Comments --scale 1 -o "$O/f.pdf" "$B" >/dev/null
$CLI pcb export pdf --mode-single -l B.Cu,B.Fab,B.Silkscreen,Edge.Cuts,User.Comments --scale 1 -o "$O/b.pdf" "$B" >/dev/null
for s in f b; do pdftoppm -r "$DPI" -png -singlefile "$O/$s.pdf" "$O/$s"; done
python3 - "$O" "$DPI" "$WIN" <<'PY'
import sys
from PIL import Image, ImageChops
o, dpi, win = sys.argv[1], float(sys.argv[2]), sys.argv[3]
for s in "fb":
    im = Image.open(f"{o}/{s}.png").convert("RGB")
    # the board outline spans chassis x 525-675 (KiCad 0-150), y 30-200 (0-170); KiCad's A4 sheet origin is the
    # page corner, so locate the outline by the Edge.Cuts bounding box of non-white pixels at full page
    bb = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    full = im.crop(bb)
    full.save(f"{o}/{s}.png")
    if win:
        x0, y0, x1, y1 = map(float, win.split(","))
        k = dpi / 25.4
        # page position of KiCad (0, 0) = chassis (525, 30): the PDF keeps board coordinates at scale 1
        px = lambda x: int(round((x - 525) * k))
        py = lambda y: int(round((y - 30) * k))
        im.crop((px(x0), py(y0), px(x1), py(y1))).save(f"{o}/{s}_win.png")
PY
