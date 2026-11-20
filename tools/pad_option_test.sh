#!/usr/bin/env bash
# Phase 3 pad-size decision helper (read-only for the repo): test the Proteus pad sizes on a set of
# refdes in a scratch copy (build/tmp/padopt_<name>), then rebuild the board there and run
# check_footprints, make_pcb, check_board, assign_nets --check and DRC.
#
#   tools/pad_option_test.sh NAME "REFDES ..."
#
# The scratch copy's tools/gen_footprints.py gets, for the named parts only, a rule with
# refdes=PROTEUS_PADS in front of the general rule of its symbol and a derived project footprint
# "<footprint>_ProteusPads" (same base / renumbering / pad centres, ipc_sizes=True: Proteus pad
# size and drill) - the way tube_psu applied its pad decision. Nothing in the repo is changed.
set -eu
cd "$(dirname "$0")/.."
name=$1; refs=$2
dst="$PWD/build/tmp/padopt_$name"
rm -rf "$dst"; mkdir -p "$dst"
tar --exclude=./build --exclude=./.git -cf - . | tar -xf - -C "$dst"
cat >> "$dst/tools/gen_footprints.py.patch" <<EOF
PROTEUS_PADS = frozenset("""$refs""".split())
# symbol -> (footprint of the general rule, spec of the Proteus-pad variant)
_VARIANTS = {
    "LMV324A": "TSSOP-14_4.4x5mm_P0.65mm_Proteus",
    "LT1014": "TSSOP-14_4.4x5mm_P0.65mm_Proteus",
    "ADC121C027": "SOT-23-6_ADC121C027_Proteus",
    "SI8271": "SOIC-8_3.9x4.9mm_P1.27mm_Proteus",
    "ISL21010": "SOT-23_Proteus",
    "HEADER_2X20_50MIL": "PinHeader_2x20_P1.27mm_Vertical_RowsSwapped",
    "HEADER_2X8_50MIL": "Connector_PinHeader_1.27mm:PinHeader_2x08_P1.27mm_Vertical",
}
import csv as _csv
_sym = {r["refdes"]: r["lib_id"].split(":")[1] for r in _csv.DictReader(
    l for l in open(os.path.join(ROOT, "lib", "part_map.csv")) if not l.startswith("#"))}
for _s in sorted({_sym[r] for r in PROTEUS_PADS}):
    _fp = _VARIANTS[_s]
    _users = sorted(r for r in PROTEUS_PADS if _sym[r] == _s)
    if ":" in _fp:
        _spec = dict(base=_fp, descr=_fp.split(":")[1])
        _vname = _fp.split(":")[1] + "_ProteusPads"
    else:
        _spec = dict(PROJECT[_fp])
        _vname = _fp + "_ProteusPads"
    _spec.update(ipc=_users[0], ipc_sizes=True, descr=_spec["descr"] + "; Proteus pad sizes")
    PROJECT.setdefault(_vname, _spec)
    _i = next(i for i, r in enumerate(RULES) if r[0] == _s)
    RULES.insert(_i, (_s, dict(RULES[_i][1], refdes=frozenset(_users)), P + _vname, RULES[_i][3] + ", Proteus pad size"))
# a project footprint whose parts all moved to the variant is no longer used
for _fp in set(_VARIANTS.values()):
    if ":" not in _fp and all(r in PROTEUS_PADS for r in _sym if _VARIANTS.get(_sym[r]) == _fp):
        PROJECT.pop(_fp, None)
EOF
python3 - "$dst/tools/gen_footprints.py" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
patch = open(p + ".patch").read()
s = s.replace('\nFP_LIB_TABLE = ', "\n" + patch + '\nFP_LIB_TABLE = ', 1)
open(p, "w").write(s)
PY
cd "$dst"
export P2K_BOARD="$dst"
python3 tools/gen_footprints.py >/dev/null
for s in tools/sheets/sheet0*.py; do python3 "$s" >/dev/null; done
tools/p2k/bin/kipy -m p2k.check_footprints --pcbnew 2>&1 | grep -E "^check_footprints: [0-9]|OK|FAIL" || true
tools/make_pcb.sh 2>&1 | grep -E "^assign_nets: stage B|pours_to_zones" || true
tools/p2k/bin/kipy -m p2k.check_board 2>&1 | tail -1 || true
tools/p2k/bin/kipy -m p2k.assign_nets --check 2>&1 | grep -E "after zone fill|OK|FAILED" | head -3 || true
tools/p2k/bin/p2k drc 2>&1 | grep -v courtyards_overlap: || true
