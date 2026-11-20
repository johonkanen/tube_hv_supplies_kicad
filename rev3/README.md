# HV supplies rev 3: initial schematic

The redesign of the HV supplies board (v2, converted at the repo root, frozen) for the rev B
amplifier: two controllable outputs **V_ANODE** (0 to about 400 V, 0.5 A peak) and **V_SCREEN** (up
to about 390 V, 100 mA average, 0.25 A peak) from the tube PSU's 420-430 V raw rail, the raw HV
distribution to the preamp and PI + FX (two fused RAW_SS feeds), the power star and the fault / RF
network to the chassis. Contract: tube_amplifier_kicad `docs/interfaces.md` (IF-1.1) and
`docs/grounding.md`. rev3/ is its own p2k board root (`p2k_config.py`, PROJECT
`tube_hv_supplies_rev3`); the v2 files at the repo root are not touched.

Status, requirements check, interface check, missed items, rail currents and open questions:
**[STATUS.md](STATUS.md)**.

## Build

```
python3 rev3/tools/make_lib.py          # lib/tube_hv_supplies_rev3.kicad_sym from KiCad's stock libraries (flattened)
python3 rev3/tools/make_project.py      # project, root sheet, empty sub-sheets
python3 rev3/tools/sheets/draw_all.py   # draws all five sheets (overwrites them)
tools/p2k/bin/kicad-cli sch erc --severity-all -o build/tmp/rev3_erc.rpt rev3/kicad/tube_hv_supplies_rev3.kicad_sch
python3 rev3/sim/converter_avg.py              # averaged converter model (ngspice), writes rev3/sim/results.md
```

The sheets are generated: edit `tools/sheets/draw_all.py`, not the `.kicad_sch` files. Drawing style
is netlist-first (parts on a grid, a wire stub and a label on every pin), as in tube_preamp_kicad
rev_b: exact for ERC and the netlist, a tidy layout pass comes later. **ERC: 0 errors, 2 warnings**
(both explained in STATUS.md). 209 parts, 118 nets. Footprints not assigned; no layout.

| Sheet | Contents |
|---|---|
| 01 | J101 raw HV in (B_P / B_N), F101 / F102 (100 mA T) to J102 / J103 (RAW_SS1 / RAW_SS2 with GND_PRE returns), input filter (v2's 33 µH, caps now 500 V), raw bleeder and HV-present LED, NT101 (the star point PGND ↔ GND_STAR), fault / RF network (GBU8J ‖ 100 nF Y2 ‖ 100 Ω) to the plated chassis standoff H101, raw-rail brake (470 Ω, IKP08N65F5, UCC27511) |
| 02 | Two synchronous bucks (v2 topology): input fuse, IKP08N65F5 half-bridge, 50 mΩ shunt in the low-side emitter, 3 mH main inductor (now on the board), 47 µF intermediate capacitor returned through a 50 mΩ shunt, 33 µH second stage, 47 µF output to GND_STAR, 2.2 Ω fusible to the tab, 220 kΩ bleeders. Bridge 2 built like bridge 1, R26 ‖ R27 gone. D201 clamps V_SCREEN ≤ V_ANODE. J201 V_ANODE / GND_PWR, J202 V_SCREEN |
| 03 | One UCC21520 per bridge (dead time + overlap block, DIS input = hardware inhibit, 8 V UVLO), bootstrap with an ultrafast diode, 15 Ω gate resistors, 10 kΩ gate-emitter resistors, PWM pull-downs |
| 04 | Four 1/201 dividers (3x 1 MΩ + 15 kΩ) and four shunt amplifiers (1 V/A around 1.25 V), MCP6004 buffers, AD7689 (8 ch, 16 bit, 250 kSPS SPI, internal 2.5 V reference); channel order = v2's J1 pads 1-8 |
| 05 | J1 (40-pin, proposed pinout), J501 HV_PERMIT current-loop input (TLP293), fault latch (74AUP1G74), driver enable NAND (74LVC1G10), comparators (2x LMV339): over-current x2, over-voltage raw / V_ANODE / V_SCREEN (latched), brake (non-latched, hysteresis), LM4040 2.5 V reference |

## Layout

```
rev3/
  p2k_config.py          board root for the p2k tools
  tools/make_lib.py      symbol library from KiCad's stock libraries
  tools/make_project.py  project skeleton
  tools/sheets/draw_all.py  the five sheets
  lib/                   generated symbol library
  kicad/                 generated KiCad 10 project
  sim/converter_avg.py   averaged converter model (ngspice); sim/results.md its output
```
