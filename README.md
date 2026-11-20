# tube_hv_supplies_kicad

KiCad 10 migration of the high-voltage supplies board (2x half-bridge converters that set the tube voltages for power scaling) of the tube amplifier, from Proteus. The schematic is redrawn from
the Proteus PDF and the PCB is rebuilt from the Gerber X2 export, so that every pad, track,
via and pour carries a net from the new schematic. The IPC-D-356A netlist of the CADCAM export
is the reference that every check compares against.

This is **rev A, the as-built baseline**. The redesign (ribbon cables, PCB-mount pots, the new
power section) starts from it. The amplifier project, its specification and the hardware state
are in [tube_amplifier_kicad](https://github.com/johonkanen/tube_amplifier_kicad), which includes
this repo as a submodule once the conversion is verified.

## Method

The shared [proteus2kicad](https://github.com/johonkanen/proteus2kicad) tools, a submodule in
`tools/p2k` (clone with `git clone --recurse-submodules`, or run `git submodule update --init`).
The phases and checks are in `tools/p2k/CONVERSION_PLAYBOOK.md`. Everything specific to this
board is in `p2k_config.py`.

## Status

Conversion plan: [PLAN.md](PLAN.md); progress: [STATUS.md](STATUS.md); prompt for the next agent session: [next_prompt.md](next_prompt.md).

Phase 0 (skeleton and inventory) done: `p2k_config.py` complete, `reference/` cheat sheets
generated from the IPC netlist, `tools/check_all.sh` passes. Next: Phase 1 preparation.

v2, built 2026. v1 (built 2024, same outline and mounting holes) is not converted; add it as a tagged revision if it's ever needed.

## Source

`hi_voltage_suppliesv2.pdsprj` (Proteus 8.12). Exported 2026-11-19 from Proteus 8.12 SP2: schematic PDF, Gerber X2 CADCAM (metric)
with the IPC-D-356A netlist.

## Mechanical baseline

From the export (the fit reference for the redesign; the KiCad file is
`mechanical/hv_supplies_v2.kicad_pcb` in tube_amplifier_kicad):

```
outline: 170.08 x 56.48 mm, lower-left corner at (-122.600, -28.260) in the Proteus frame
copper layers: 4; components: 158; mounting holes: 4
mounting holes (relative to the lower-left outline corner, mm):
  H1: x    4.490  y   51.755  drill 3.00 plated
  H2: x    4.490  y    4.755  drill 3.00 plated
  H3: x  165.490  y    4.755  drill 3.00 plated
  H4: x  165.490  y   51.755  drill 3.00 plated
```

## Layout

```
source/         Proteus exports (read-only)
  cadcam/         Gerber X2 export with the IPC-D-356A netlist (the reference)
  schematic_pdf/  schematic PDF to redraw from
  *.pdsprj        Proteus project (schematic values, devices, packages, pin names)
reference/      tables derived from the IPC netlist (p2k ipc356; generated, don't edit)
tools/p2k/       proteus2kicad (submodule)
tools/check_all.sh  every verification step (run at the start and end of a session)
p2k_config.py   board configuration for the tools
```
