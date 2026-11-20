# Conversion plan: HV supplies v2 (`hi_voltage_suppliesv2`)

Goal: redraw the Proteus schematic in KiCad 10 and rebuild the PCB from the Proteus Gerber X2
export, so that every pad, track, via and pour carries a net from the new schematic, and **prove
with scripted checks** that the KiCad design is electrically identical to the Proteus one. The
result is **rev A, the as-built baseline** for the redesign (see README.md).

This plan follows the generic playbook **`tools/p2k/CONVERSION_PLAYBOOK.md`** (read it first) and
lists only what is specific to this board. The finished reference is `~/dev/tube_psu_kicad`
(same proteus2kicad version, Phases 0-5 done): look at its `tools/`, `p2k_config.py`, PLAN.md and
STATUS.md for how each step was done.

**Order:** Independent of the 2010 boards: can run in parallel with the pilot. Closest reference is `~/dev/tube_psu_kicad` (same era of Proteus 8.12 export, 4 layers, mixed SMD/THT, power stages).

## 1. Inventory (measured in Phase 0, 2026-11-20; `tools/check_all.sh` asserts it)

| Item | Value |
|---|---|
| Proteus project | `source/hi_voltage_suppliesv2.pdsprj` (Proteus 8.12 SP2; ROOT.DSN / ROOT.LYT saved 2026-09-19; values, devices, packages, pin names via `p2k.pdsprj`) |
| Schematic PDF | `source/schematic_pdf/hi_voltage_suppliesv2.PDF`, 6 pages (printed 2026-09-19, same as the project), **no title blocks** (sheet names chosen from content, `p2k_config.py` SHEETS) |
| CADCAM export | `source/cadcam/` (Gerber X2, metric, `FSLAX45Y45`, no arcs, one `SameCoordinates` id, generated 2026-11-19), 14 gerbers + IPC |
| IPC netlist (the reference) | `source/cadcam/hi_voltage_suppliesv2 - CADCAM Netlist.IPC` |
| Copper layers | 4: `Top Copper`, `Inner  1`, `Inner  2`, `Bottom Copper` (CADCAM READ-ME stack: 4 x 0.036 Cu, 0.32 prepreg / 1.483 core / 0.32 prepreg = 2.267 mm without resist, a Proteus default; **the board is 1.6 mm**, user 2026-11-20, `PCB_THICKNESS = 1.6`) |
| Outline | 170.085 x 56.485 mm, lower-left (-122.600, -28.260) (`Mechanical 1`, 4 `Profile` draws) |
| Nets (IPC NNAME) | **113** (pre-check said 114); no `=POWER` suffixes; 19 single-pin nets (18 unused J1 ribbon signals + `FLOATING` = ADC3 ADR0) |
| Records | 574: 247 THT (102 component pads + 141 vias + 4 holes), 327 SMD (227 top, 100 bottom) |
| Parts (IPC refdes) | 158 named (159 refdes fields incl. the blank one); N/C pads 2 (J1-37, J1-38) |
| Vias | 141: 139 x 0.5/0.3 mm, 2 x 1.016/0.381 mm; through (Top-Bottom) only; **no stacked duplicates** (`STACKED_VIAS` stays 0) |
| Mounting holes | 4, 3.0 mm **plated**, 6.35 mm ring on all four layers (`OtherPad` / `OtherDrill` flashes), no net (IPC blank refdes, no net); positions in README.md |
| Free pads | none |
| Drills | one file `Drill TOP-BOT Plated` (247 flashes: via 0.3 x139, 0.381 x2; component 0.5588 x56, 0.8128 x18, 1.016 x12, 1.4 x12, 1.524 x4; other 3.0 x4); **no NonPlated file** |
| Pours (G36 dark / clear regions) | Top 15 / 103, Inner 1 1 / 3, Inner 2 1 / 131, Bottom 4 / 46; no NonConductor draws on copper |
| Conductor draws | Top 2221, Inner 1 625, Inner 2 2011, Bottom 873; thinnest 0.1524 mm |

## 2. Board-specific notes and expected pitfalls

- v2, built 2026; v1 (2024, same outline and holes) is not converted.
- Two IGBT half-bridges (Q3/Q4 -> OUT1, Q8/Q7 -> OUT2, IKP08N65F5), each followed by an off-board
  3 mH inductor and an SMD 33 uH inductor (L2 -> V_A = V_ANODE, L4 -> U_OUT, then R26/R27 -> PREOUT =
  VPRE). Gate drivers `DRV1`, `DRV2`, `DRV5`, `DRV6` (Si8271; not DRV1-DRV4), bootstrap D18 / D2.
  Measurement amplifiers U1 (LMV324A, voltages) and U2 (LT1014, currents), reference REF1, ADCs
  `ADC1`-`ADC3` (ADC121C027, I2C). `J1` (40 pins) is the control-card ribbon, `J2` (16 pins) the
  ADC input header.
- **Terminals** (TERMINAL parts, two holes each, both pin 1, one net): `B+` (net B+) and `B-` (GND)
  -> KiCad `B_P` / `B_N`; `V_ANOD` -> `V_ANODE` (V_A), `GND_PR` -> `GND_PRE` (GND), `GND_PW` ->
  `GND_PWR` (GND) (6-char truncation), `VPRE` (PREOUT, not truncated).
- **`L5`, `L6`, `L11`, `L12` are single-pad TERMINAL parts** (one 1.524 mm hole, 2.54 mm pad, each):
  the wire ends of the two off-board 3 mH inductors drawn on PDF page 1 but not in the IPC: `L1`
  between L5 (OUT1) and L12 (UC3), `L3` between L11 (OUT2) and L6 (U_OUT). Phase 1 draws L1 / L3 as
  off-board parts (symbol `L_OFFBOARD`, excluded from the board; Phase 2: `OFF_BOARD_PARTS`),
  decided in Phase 1 preparation.
- ADC1-ADC3 have Proteus pin ids `A1`, `A2`, `COM1`, `COM2`, `K1`, `K2` (a diode-array style
  package): VA = A1, GND = A2, SDA = COM1, VIN = COM2, SCL = K1, ADR0 = K2. Symbols and footprints
  must use these ids.
- PDF label `15V` (page 2) is joined to `15V_boost` on page 5 ("Not yet complete" note): one IPC
  net `15V_BOOST`. J1 pins 1-8 carry the `*_meas` nets through the ADB0-ADB7 alias links of page 5.
- Pours on all four layers (Inner 2 with 131 clear holes): `pours_to_zones` as in tube_psu.

## 3. Phases

As in the playbook, section 3. Board-specific done criteria:

| Phase | Done when |
|---|---|
| 0 Skeleton and inventory (done 2026-11-20) | `p2k_config.py` complete (sheet names from the page content: the PDF has no title blocks, truncated-refdes table, KiCad refdes map, net aliases, expected IPC counts, layers, drills, outline); `p2k ipc356 --check` and `p2k check_sources` pass; `reference/` cheat sheets written; `tools/check_all.sh` runs; PLAN.md section 1 corrected with the measured inventory |
| 1 Schematic | all 158 parts drawn; `compare_netlists` 0 wrong-net pins, every IPC net complete; ERC 0 errors (warnings explained) |
| 2 Footprints | every part fits the IPC pads within 0.05 mm (`check_footprints`); pin-order oddities reported |
| 3 PCB | copper 0 shorts / 0 orphans / 0 opens after zone fill; DRC 0 shorts, 0 unconnected, 0 parity; remaining DRC items listed and justified; `make_pcb.sh --check` reproducible |
| 4 Verification | `gerber_roundtrip --check` and `ipc356_diff` pass and are in `check_all.sh`; every new check negative-tested; preferably a different session/model |
| 5 Clean-up | only the user's choices (pad sizes, silk, refdes positions) |

When all phases are done: STATUS.md says so, and the amplifier master repo can add this repo as a
submodule (that step is done from the master repo, not here).

## 4. Effort

The playbook's estimates are for a ~270-part, 4-layer, 11-sheet board. This board has
158 parts on 6 sheets and 4 copper layers: scale accordingly.

## 5. Rules for this conversion

Several board conversions run **in parallel**, each in its own repo and session. To keep them
independent:

1. **Don't change the shared tools** in `tools/p2k` (proteus2kicad), and don't move the submodule
   pin (c5682dd). If a tool can't handle something on this board, write a board-local script in
   `tools/` (or a config key the tool already has) and record it in STATUS.md under
   "p2k candidates", with what the shared tool would need. The tool changes are made later, in one
   place, with the ac_psu regression.
2. **Don't touch other repositories.** In particular not `~/dev/tube_amplifier_kicad` (the
   amplifier master repo: it adds this repo as a submodule once the conversion is verified) and not
   `~/dev/ac_psu_kicad` (another session's work in progress). `~/dev/tube_psu_kicad` is the
   finished reference: read it, don't change it.
3. **Reproduce Proteus.** Problems in the original design are reported in STATUS.md
   ("Findings"), not fixed. The redesign happens later, from this baseline.
4. **Generate, don't hand-edit** (playbook section 1): every file in `kicad/`, `lib/` and
   `reference/` is written by a script and is reproducible.
   **Ended by the user's D-STOP (2026-11-20):** since then `kicad/` and `lib/` are hand-edited (STATUS.md
   "Generation stopped 2026-11-20"); `reference/` stays generated from source/.
5. **Temporary files in `build/tmp/`** (git-ignored). Never run the KiCad AppImage with
   `--version` (it starts the GUI and hangs); use `tools/p2k/bin/kipy` and `tools/p2k/bin/kicad-cli`.
6. **Commit and push at the end of every phase** (and at the end of a session), with
   STATUS.md and next_prompt.md updated in the same commit.
7. **Ask the user** where the playbook says to (pad sizes when DRC forces them, Phase 5 choices,
   anything that changes the design).

## 6. Session protocol

- Start every session by reading PLAN.md, STATUS.md and `tools/p2k/CONVERSION_PLAYBOOK.md`, then
  run `tools/check_all.sh` (from Phase 0 on) and compare with the last result in STATUS.md.
- One session per phase (Phase 1 transcription may take several, a few sheets each).
- End every session with: `tools/check_all.sh` passing for everything done so far, STATUS.md
  updated (phase state, last check output, findings, p2k candidates, decisions), next_prompt.md
  replaced with the prompt for the next session, commit and push.
