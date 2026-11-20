# Status: HV supplies v2 (`hi_voltage_suppliesv2`)

Plan: [PLAN.md](PLAN.md). Playbook: `tools/p2k/CONVERSION_PLAYBOOK.md`.

| Phase | State |
|---|---|
| 0 Skeleton and inventory | **done** 2026-11-20 (Opus 5.5) |
| 1 Schematic | not started (next: Phase 1 preparation, `next_prompt.md`) |
| 2 Footprints | not started |
| 3 PCB | not started |
| 4 Verification | not started |
| 5 Clean-up | not started |

## Phase 0 – done (Opus 5.5, 2026-11-20)

- **Inventory** measured from the sources and written into PLAN.md section 1. Corrections to the
  pre-check: 113 nets, not 114; the gate drivers are DRV1/DRV2/DRV5/DRV6, not DRV1-DRV4; the
  mounting holes are plated 3.0 mm with a 6.35 mm ring on all layers and no net; there is no
  NonPlated drill file; `L5`/`L6`/`L11`/`L12` are single-pad TERMINAL parts for two off-board
  inductors (see below); there are no stacked duplicate vias. Pours on every copper layer
  (dark / clear regions: Top 15/103, Inner 1 1/3, Inner 2 1/131, Bottom 4/46), no NonConductor
  draws, no arcs, one `SameCoordinates` id.
- **PDF pages** rendered to `build/tmp/pdf/hi-N.png` (not committed; regenerate with
  `pdftoppm -r 200 -png source/schematic_pdf/hi_voltage_suppliesv2.PDF build/tmp/pdf/hi`).
  The pages have **no title block** and ROOT.DSN holds no sheet names, so the `SHEETS` names
  describe the content: 1 Power stage, 2 Gate drivers, 3 Voltage measurements, 4 Current
  measurements, 5 Reference and connector, 6 ADC. Every IPC refdes is on a PDF page. The PDF
  has two parts that are not in the IPC: `L1` and `L3` (3 mH, page 1, off-board).
- **`p2k_config.py`** complete for Phase 0: SHEETS, `TRUNCATED_REFDES` / `TRUNCATED_NETS`,
  `KICAD_REFDES`, `NET_ALIASES` (empty), via / hole drills, `EXPECTED_IPC`, `COPPER`,
  `DRILL_PLATED` (`DRILL_NONPLATED = None`), `OUTLINE`, `OUTLINE_RECT`.
- `p2k ipc356` wrote `reference/` (`ipc356_pads.{json,csv}`, `pin_nets_by_component.md`,
  `pins_by_net.md`). `--check` and `p2k check_sources` pass. Negative-tested on a copy
  (`P2K_BOARD`): a via moved 0.05 mm in the IPC fails check_sources (10 errors), and an expected
  hole count of 5 fails `ipc356 --check`.
- `tools/check_all.sh`: KiCad environment, IPC self-check, X2 vs IPC.

### Refdes tables

| IPC field | Proteus refdes | KiCad refdes | Net | Note |
|---|---|---|---|---|
| `V_ANOD` | `V_ANODE` | `V_ANODE` | V_A | truncated; terminal, 2 holes both pin 1 |
| `GND_PR` | `GND_PRE` | `GND_PRE` | GND | truncated; terminal, 2 holes both pin 1 |
| `GND_PW` | `GND_PWR` | `GND_PWR` | GND | truncated; terminal, 2 holes both pin 1 |
| `B+` | `B+` | `B_P` | B+ | sign; terminal, 2 holes both pin 1 |
| `B-` | `B-` | `B_N` | GND | sign; terminal, 2 holes both pin 1 |
| `VPRE` | `VPRE` | `VPRE` | PREOUT | 4 chars, not truncated; terminal, 2 holes both pin 1 |

### Notes for Phase 1

- **Off-board inductors:** PDF page 1 draws `L1` (3 mH, OUT1 -> UC3) and `L3` (3 mH, OUT2 ->
  U_OUT). They have no pads. Their wire ends land on the single-pad TERMINAL parts `L5` (OUT1) /
  `L12` (UC3) and `L11` (OUT2) / `L6` (U_OUT) (1.524 mm hole, 2.54 mm pad each). Drawing L1 / L3
  as ordinary parts would join OUT1-UC3 and OUT2-U_OUT into one net each, which the IPC keeps
  separate. Either leave them out (text note) or draw them excluded from the board and the
  netlist (`OFF_BOARD_PARTS` in Phase 2). Decide in Phase 1 preparation (ask the user if
  unclear).
- **ADC1-ADC3 pin ids** (ADC121C027, SOT-23-6) are `A1`, `A2`, `COM1`, `COM2`, `K1`, `K2` in the
  IPC: VA = A1, GND = A2, SDA = COM1, VIN = COM2, SCL = K1, ADR0 = K2 (PDF page 6). The symbol and
  footprint pins must use these ids. The Phase 2 fit will show which JEDEC pad each id sits on.
- Other pin-id families: D18 / D2 `A`/`C`; Q3/Q4/Q7/Q8 (IKP08N65F5, TO-220) `1`/`2`/`3`
  (1 = gate, 2 = collector, 3 = emitter by the nets); REF1 `1`/`2`/`3` (1 = GND, 2 = VIN,
  3 = VOUT); DRV* 8 pins, U1/U2 14 pins, J1 40, J2 16, all numeric.
- 38 parts are on the bottom side: the whole gate-driver page (DRV1/2/5/6, D2, D18, R21-R25,
  R31-R35, C23-C25, C30-C33, C38, C43, C46) plus C34-C37, C39-C42, C44, C45, C47, C48.
- PDF page 2: the references R23 / R25 / R32 / R35 are printed next to the GND2 pins. They belong
  to the 8R resistors on the OUT- side (IPC: DRV1-6 -> R23-1). Read the nets from the IPC
  (`reference/pin_nets_by_component.md`), not from the label positions.
- Net names: PDF `15V` (page 2) and `15V_boost` are joined on page 5 -> IPC `15V_BOOST`;
  page 1 `b+` / `BRIDGE+` -> IPC `B+` / `UIN`; the page 5 ADB0-ADB7 aliases -> J1 pins 1-8 carry
  the `*_MEAS` nets. Use the IPC names.
- 19 single-pin nets: 18 J1 ribbon signals not used on this board (`*_ISO`, `PWM_TRANS4/6`,
  `DAB_*`, `ADCLK_DAB`) and `FLOATING` (ADC3 ADR0). J1-37 / J1-38 are N/C.

## Last check output

```
== KiCad environment
pcbnew 10.0.7
== IPC-D-356A parser self-check
ipc356: nets=113, records=574, refdes_raw=159, tht_records=247, smd_records=327, smd_top=227, smd_bottom=100, nc_pads=2, vias=141, free_pads=0, holes=4, parts=158
ipc356: OK
== Gerber X2 export vs IPC (pads, vias, drills, outline)
  14 gerbers, one SameCoordinates id
  Top Copper: Draw:Conductor 2221, Draw:Profile 4, Flash:ComponentPad 102, Flash:OtherPad,Unknown 4, Flash:SMDPad,CuDef 227, Flash:ViaPad 141, Region:- 118
  Inner  1: Draw:Conductor 625, Draw:Profile 4, Flash:ComponentPad 102, Flash:OtherPad,Unknown 4, Flash:ViaPad 141, Region:- 4
  Inner  2: Draw:Conductor 2011, Draw:Profile 4, Flash:ComponentPad 102, Flash:OtherPad,Unknown 4, Flash:ViaPad 141, Region:- 132
  Bottom Copper: Draw:Conductor 873, Draw:Profile 4, Flash:ComponentPad 102, Flash:OtherPad,Unknown 4, Flash:SMDPad,CuDef 100, Flash:ViaPad 141, Region:- 50
  drills: 247 plated, 0 non-plated
  outline 170.1 x 56.5 mm at (-122.60, -28.26)
check_sources: OK

ALL CHECKS PASSED
```

## Findings about the original design

Reported, not fixed (PLAN.md section 5).

1. **`+2V5_BIAS` name vs the circuit (to confirm):** REF1 is an ISL21010CFH315Z-TK. In the
   ISL21010 ordering code, `-15` is the 1.5 V version (confirm against the fitted part).
   Its output feeds R74 220 R -> `+2V5_BIAS`, with R73 470 R to GND, which gives about
   1.5 x 470 / 690 = 1.02 V, not 2.5 V. So the net name, the part or the divider is stale. Not
   aliased: renaming the net is a user decision (tube_psu renamed its bias net to the real
   voltage, `+2V5_BIAS` -> `+1V65_BIAS`).
2. **15 V supply "Not yet complete":** PDF page 5 joins the gate drivers' `15V` label to
   `15V_boost` (J1-39/40) with the note "Not yet complete". The board is built with one net,
   `15V_BOOST`. Note for the redesign.
3. **Board thickness:** the CADCAM READ-ME stack (4 x 0.036 Cu, 0.32 prepreg, 1.483 core,
   0.32 prepreg) adds up to 2.267 mm without resist, not a standard 1.6 mm. Check the real
   board before choosing `PCB_THICKNESS` in Phase 3.
4. **No title blocks** on the six PDF pages (sheet names chosen from content).
5. The PDF and the project were saved 2026-09-19, and the CADCAM export was made 2026-11-19 from
   that project. The PDF matches the IPC: every IPC part is on a page, and only the off-board
   L1/L3 are extra.

## p2k candidates

Shared-tool limitations met on this board. Phase 0 needed no board-local workaround.

1. `ipc356`: the `pin_nets_by_component.md` header prints `Net aliases: .` when `NET_ALIASES` is
   empty. Print "none" instead (cosmetic).
2. `ipc356`: `pins_by_net.md` lists a two-hole terminal pin twice (`B_P-1 B_P-1`, pin count 5 for
   B+), because it counts records, not distinct pins. Distinct `(refdes, pin)` would read better
   (cosmetic; tube_psu has the same).

## Decisions

- KiCad refdes `B_P` / `B_N` for `B+` / `B-` (P/N for the sign, as tube_psu `P400V` /
  `N5V_OUT`). They can still be renamed before any Phase 1 sheet exists.
- Sheet names chosen from the page content (no title blocks).
- `NET_ALIASES` empty (no `=POWER` names; `+2V5_BIAS` kept until the user decides, finding 1).
