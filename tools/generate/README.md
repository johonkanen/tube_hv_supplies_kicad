# tools/generate – frozen history, don't run

These scripts generated rev A of this board from the Proteus data (Phases 1-5, 2026-11-20):

- `make_part_map.py` → `lib/part_map.csv` (p2k part_map)
- `gen_symbols.py` → `lib/tube_hv_supplies.kicad_sym` (p2k symgen)
- `sheets/sheetNN.py` → `kicad/0N_*.kicad_sch` (p2k sch_builder / sheetkit)
- `gen_footprints.py` → `lib/tube_hv_supplies.pretty`, `lib/footprint_map.csv`, `kicad/fp-lib-table` (p2k footprints)
- `make_pcb.sh` → `kicad/tube_hv_supplies.kicad_pcb` (p2k make_pcb)

**Generation stopped** (user decision 2026-11-20, STATUS.md "Decisions", D-STOP): since then the files in
`kicad/` and `lib/` are edited by hand (KiCad, or pcbnew / s-expression scripts), and `tools/check_all.sh`
no longer regenerates or byte-compares them. Running a generator would overwrite the hand edits, so each
one exits unless it gets `--force-regenerate` (use it only in a scratch copy to reproduce the history).

One file here is still read by a check: `gen_footprints.py` (its `RULES` / `PROJECT` specs) is imported by
`p2k check_pin_order` through `p2k_config.FOOTPRINT_SCRIPT`; importing it writes nothing.
