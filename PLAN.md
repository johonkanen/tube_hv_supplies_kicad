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

## 1. Inventory (pre-check 2026-11-20; Phase 0 confirms and corrects it)

| Item | Value |
|---|---|
| Proteus project | `source/hi_voltage_suppliesv2.pdsprj` (values, devices, packages, pin names via `p2k.pdsprj`) |
| Schematic PDF | `source/schematic_pdf/hi_voltage_suppliesv2.PDF`, 6 pages |
| CADCAM export | `source/cadcam/` (Gerber X2, metric, with the IPC-D-356A netlist) |
| IPC netlist (the reference) | `source/cadcam/hi_voltage_suppliesv2 - CADCAM Netlist.IPC` |
| Copper layers | 4 (Top, Inner 1, Inner 2, Bottom) |
| Outline | 170.08 x 56.48 mm (Mechanical 1) |
| Parts (IPC refdes) | 158 |
| Nets (IPC) | 114 |
| Technology | mixed SMD (327 records) and through-hole (247) |
| Mounting holes | 4 (3.0 mm plated; positions in README.md "Mechanical baseline") |

## 2. Board-specific notes and expected pitfalls

- v2, built 2026; v1 (2024, same outline and holes) is not converted.
- Two half-bridge converters (V_ANODE and the second output, now V_SCREEN in the amplifier spec), gate drivers (`DRV1`-`DRV4`), ADCs (`ADC*`), magnetics (`L*`). `J1` (40 pins) is the control-card ribbon, `J2` (16 pins).
- Single-pad parts: `B+`, `B-` (HV input), `V_ANOD`, `VPRE`, `GND_PR`, `GND_PW` (outputs and returns; truncated to 6 characters), and `L5`, `L6`, `L11`, `L12` (inductor leads as separate pads: check whether each is one inductor with two single-pad halves).
- 145 IPC records without refdes (vias). Check pours on the inner layers (G36 regions, clear holes) as in tube_psu.

## 3. Phases

As in the playbook, section 3. Board-specific done criteria:

| Phase | Done when |
|---|---|
| 0 Skeleton and inventory | `p2k_config.py` complete (sheet names from the PDF title blocks, truncated-refdes table, KiCad refdes map, net aliases, expected IPC counts, layers, drills, outline); `p2k ipc356 --check` and `p2k check_sources` pass; `reference/` cheat sheets written; `tools/check_all.sh` runs; PLAN.md section 1 corrected with the measured inventory |
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
