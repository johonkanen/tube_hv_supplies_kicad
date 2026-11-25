#!/usr/bin/env bash
# drc.sh BOARD [JSON]: DRC with the project's rules (copies the .kicad_pro / .kicad_dru next to the board), summary
set -euo pipefail
B=$1; J=${2:-${B%.kicad_pcb}_drc.json}
R4="$(cd "$(dirname "$0")/.." && pwd)"
cp "$R4/kicad/tube_hv_supplies_rev4.kicad_dru" "${B%.kicad_pcb}.kicad_dru"
cp "$R4/kicad/tube_hv_supplies_rev4.kicad_pro" "${B%.kicad_pcb}.kicad_pro"
"$R4/../tools/p2k/bin/kicad-cli" pcb drc --severity-error --format json -o "$J" "$B" >/dev/null 2>&1 || true
python3 - "$J" <<'PY'
import json, collections, sys
d = json.load(open(sys.argv[1]))
c = collections.Counter(v['type'] for v in d['violations'])
print(dict(c), 'unconnected', len(d.get('unconnected_items', [])))
seen = set()
for v in d['violations']:
    k = (v['type'], v['items'][0]['description'][:50], v['items'][-1]['description'][:50])
    if k in seen: continue
    seen.add(k)
    print(' ', v['type'], '|', v['description'][:110], '|', ' / '.join(i['description'][:55] for i in v['items']))
PY
