# HV supplies rev 3: soft-switched draft (fourth pass, 2026-11-24)

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
V_ANODE sized for 0.7 A continuous. Simulation pass: the switching model, ramp-down into the PSU,
the power stage on the converter, short / arc, channel change and start-up runs, with the changes
they forced; see: **[STATUS.md](STATUS.md)** (earlier passes kept below it as history).

## Build

```
python3 rev3/tools/make_lib.py          # lib/tube_hv_supplies_rev3.kicad_sym from KiCad's stock libraries (flattened)
python3 rev3/tools/make_footprints.py   # lib/tube_hv_supplies_rev3.pretty (blade tabs, ETD39 inductor), kicad/fp-lib-table
python3 rev3/tools/make_project.py      # project, root sheet, empty sub-sheets
python3 rev3/tools/sheets/draw_all.py   # all five sheets + lib/footprint_map.csv + bom/bom.csv (overwrites them)
tools/p2k/bin/kicad-cli sch erc --severity-all -o rev3/reports/erc.rpt rev3/kicad/tube_hv_supplies_rev3.kicad_sch
cd rev3/sim && python3 lc_ac.py && python3 loop_digital.py && python3 discharge.py   # ngspice + numpy/scipy
cd rev3/sim && python3 r1_turnoff.py && for s in r1_softsw r2_filter r3_damping r4_residue r5_devices r6_sampling r7_fourth_pass; do python3 $s.py; done   # fourth pass
cd rev3/sim && for s in m15_bridge m17_ramp_down m18_power_stage m20_short_arc m21_channel_change m22_startup_failsafe; do python3 $s.py; done
#   (m18 / m21 import the power amp's stage.py from ~/dev/tube_power_amp_kicad read only; a few minutes each)
python3 rev3/mechanical/floorplan_chosen.py   # chosen outline + floorplan, KiCad Edge.Cuts outline
python3 rev3/mechanical/floorplan.py    # second-pass outline study (history)
```

The sheets are generated: edit `tools/sheets/draw_all.py`, not the `.kicad_sch` files. Drawing style
is netlist-first (parts on a grid, a wire stub and a label on every pin), as in tube_preamp_kicad
rev_b: exact for ERC and the netlist, a tidy layout pass comes later. **ERC: 0 errors, 2 warnings**
(both explained in STATUS.md). 260 parts, 139 nets (fourth pass: TCM bridges on the chassis plate, IF-2.2 fast ADCs). Footprints assigned on every part (stock KiCad
libraries; board-local blade tabs and the custom ETD39 inductor); BOM `bom/bom.csv`
(97 lines, candidate part numbers where chosen, none TBD). No layout.

| Sheet | Contents |
|---|---|
| 01 | J101 raw HV in (B_P / B_N), R101 / R102 link footprints (0 Ω fitted, or 10-47 Ω 2 W fusible) to J102 / J103 (RAW_SS1 / RAW_SS2 with GND_PRE returns), input filter (C101 47 µF, L101 33 µH), raw bleeder 2 x 75 kΩ 2 W and HV-present LED, NT101 (the star point PGND ↔ GND_STAR), fault / RF network (GBU8J ‖ 100 nF Y2 ‖ 100 Ω) to the plated standoff H101 next to J101; H102-H106 non-plated. No brake |
| 02 | Two synchronous bucks in triangular-current mode (40-150 kHz): IKP08N65F5 lying on the chassis plate (aluminium bars, 1.5 mm Al2O3), 220 pF snubbers, 220 / 470 µH ETD39 N97, C1 100 µF (+ 4.7 µF film on bridge 1) through the I_C shunt, second stage 68 µH / 4.7 µF film / 22 µF + 1.0 Ω leg (8.9 kHz), ULW5 fusibles standing, D201, J201 / J202 |
| 03 | One UCC21520 per bridge (200 ns dead-time floor, per-edge dead time from the FPGA), bootstrap, 15 Ω / 10 kΩ gate parts |
| 04 | Six ADS7056 on CS_FAST (V_ANODE, V_SCREEN, I_C14 / I_C24, I_Q12 / I_Q22) with OPA2836 front ends, REF3030 3.0 V, AD7689 for the slow monitors |
| 05 | J1 (IF-2.2), HV_PERMIT loop input, fault latch (HV_ENABLE low sets it; clears only after >= 20 ms low), comparators: ±3.0 A low side, 3.0 A capacitor discharge, raw 475 V / V_ANODE 438 V / V_SCREEN 421 V |

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
                         *_results.md; converter_avg.py (first pass, brake cases superseded);
                         swmodel.py + m15/m17/m18/m20/m21/m22_*.py (simulation pass) with results and plots
  mechanical/            floorplan.py, floorplan.md, floorplan_*.svg
```
