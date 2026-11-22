# HV supplies rev 3: first draft (third pass, 2026-11-23)

The redesign of the HV supplies board (v2, converted at the repo root, frozen) for the rev B
amplifier: two controllable outputs **V_ANODE** (0 to about 400 V, 0.5 A peak) and **V_SCREEN** (up
to about 390 V, 100 mA average, 0.25 A peak) from the tube PSU's 420-430 V raw rail, the raw HV
distribution to the preamp and PI + FX (two fused RAW_SS feeds), the power star and the fault / RF
network to the chassis. Contract: tube_amplifier_kicad `docs/interfaces.md` (IF-1.1) and
`docs/grounding.md`. rev3/ is its own p2k board root (`p2k_config.py`, PROJECT
`tube_hv_supplies_rev3`); the v2 files at the repo root are not touched.

Status, the second pass decision by decision, the interface check, rail currents, the floorplan
and open questions. Third pass: the accepted L-shaped outline (trimmed at the rear panel), the chosen
floorplan (`mechanical/floorplan_chosen.md`, KiCad outline `mechanical/outline_edge_cuts.kicad_pcb`),
V_ANODE sized for 0.7 A continuous; see: **[STATUS.md](STATUS.md)** (first pass kept below it as history).

## Build

```
python3 rev3/tools/make_lib.py          # lib/tube_hv_supplies_rev3.kicad_sym from KiCad's stock libraries (flattened)
python3 rev3/tools/make_footprints.py   # lib/tube_hv_supplies_rev3.pretty (blade tabs, ETD39 inductor), kicad/fp-lib-table
python3 rev3/tools/make_project.py      # project, root sheet, empty sub-sheets
python3 rev3/tools/sheets/draw_all.py   # all five sheets + lib/footprint_map.csv + bom/bom.csv (overwrites them)
tools/p2k/bin/kicad-cli sch erc --severity-all -o rev3/reports/erc.rpt rev3/kicad/tube_hv_supplies_rev3.kicad_sch
cd rev3/sim && python3 lc_ac.py && python3 loop_digital.py && python3 discharge.py   # ngspice + numpy/scipy
python3 rev3/mechanical/floorplan_chosen.py   # chosen outline + floorplan, KiCad Edge.Cuts outline
python3 rev3/mechanical/floorplan.py    # second-pass outline study (history)
```

The sheets are generated: edit `tools/sheets/draw_all.py`, not the `.kicad_sch` files. Drawing style
is netlist-first (parts on a grid, a wire stub and a label on every pin), as in tube_preamp_kicad
rev_b: exact for ERC and the netlist, a tidy layout pass comes later. **ERC: 0 errors, 2 warnings**
(both explained in STATUS.md). 200 parts, 113 nets. Footprints assigned on every part (stock KiCad
libraries; board-local blade tabs and the custom ETD39 inductor); BOM `bom/bom.csv`
(79 lines, candidate part numbers where chosen). No layout.

| Sheet | Contents |
|---|---|
| 01 | J101 raw HV in (B_P / B_N), R101 / R102 link footprints (0 Ω fitted, or 10-47 Ω 2 W fusible) to J102 / J103 (RAW_SS1 / RAW_SS2 with GND_PRE returns), input filter (C101 47 µF, L101 33 µH), raw bleeder 2 x 75 kΩ 2 W and HV-present LED, NT101 (the star point PGND ↔ GND_STAR), fault / RF network (GBU8J ‖ 100 nF Y2 ‖ 100 Ω) to the plated standoff H101 next to J101; H102-H106 non-plated. No brake |
| 02 | Two synchronous bucks: input link footprint (no fuse, N7), IKP08N65F5 half-bridge (Q201 on an insulated SK 104 heatsink), 50 mΩ shunt in the low-side emitter, 3 mH / 2.4 A ETD39 inductor, one 100 µF / 500 V electrolytic returned through a 50 mΩ shunt, second stage 33 µH ∥ 5.6 Ω with a 1 µF film (27.7 kHz, Q 1), 1.0 Ω (V_ANODE) or 2.2 Ω (V_SCREEN) fusible to the tab, 220 kΩ bleeders. D201 (1N5408) clamps V_SCREEN ≤ V_ANODE. J201 V_ANODE / GND_PWR, J202 V_SCREEN |
| 03 | One UCC21520 per bridge (dead time + overlap block, DIS input = hardware inhibit, 8 V UVLO), bootstrap with an ultrafast diode, 15 Ω gate resistors, 10 kΩ gate-emitter resistors, PWM pull-downs |
| 04 | Four 1/201 dividers (3x 1 MΩ + 15 kΩ) and four shunt amplifiers (0.5 V/A around 1.25 V, ±2.5 A), MCP6004 buffers, AD7689 (8 ch, 16 bit, SPI, internal 2.5 V reference); channel order per interfaces.md 9; R444 returns SCK to pad 16 (ADC_SCK_RET) |
| 05 | J1 (40-pin, IF-2), J501 HV_PERMIT current-loop input (TLP293), fault latch (74AUP1G74), driver enable NAND (74LVC1G10), comparators (2x LMV339, latched): over-current 2.0 A forward and reverse per bridge, over-voltage raw 475 V / V_ANODE 440 V / V_SCREEN 420 V; LM4040 2.5 V reference |

## Layout

```
rev3/
  p2k_config.py          board root for the p2k tools
  tools/make_lib.py      symbol library from KiCad's stock libraries
  tools/make_project.py  project skeleton
  tools/make_footprints.py  board-local footprints
  tools/sheets/draw_all.py  the five sheets, footprint map, BOM
  lib/                   generated symbol library, footprints, footprint_map.csv
  kicad/                 generated KiCad 10 project
  bom/bom.csv            first BOM (refs, value, footprint, candidate part number)
  reports/erc.rpt        ERC report
  sim/                   hvnet.py (shared network), lc_ac.py, loop_digital.py, discharge.py and their
                         *_results.md; converter_avg.py (first pass, brake cases superseded)
  mechanical/            floorplan.py, floorplan.md, floorplan_*.svg
```
