# Status: HV supplies v2 (`hi_voltage_suppliesv2`)

Plan: [PLAN.md](PLAN.md). Playbook: `tools/p2k/CONVERSION_PLAYBOOK.md`.

| Phase | State |
|---|---|
| 0 Skeleton and inventory | **done** 2026-11-20 (Opus 5.5) |
| 1 Schematic | **done** 2026-11-20 (preparation Opus 5.5; transcription Fable 5.2): 158/158 parts, 0 wrong-net pins, every IPC net complete, ERC 0 errors / 21 explained warnings |
| 2 Footprints | **done** 2026-11-20 (Opus 5.5): 158/158 parts fit the IPC pads, worst residual 0.039 mm (pcbnew placement 0.039 mm); pin order checked (J1 numbering mirrored, finding 12; ADC1-3 finding 6 confirmed) |
| 3 PCB | **done** 2026-11-20 (Opus 5.5, two sessions): board generated, Proteus copper 0 shorts / 0 orphans / 0 opens, check_board OK, make_pcb reproducible; pad sizes option A2 (user): Proteus pads on U1 U2 ADC1-3 DRV5 DRV6 J1, KiCad elsewhere → DRC 0 shorts / 0 clearance / 0 mask bridges / 0 unconnected / 0 parity, copper after zone fill 0 / 0 / 0 |
| 4 Verification | not started |
| 5 Clean-up | not started |

## Phase 3 – PCB – done (Opus 5.5, 2026-11-20)

`kicad/tube_hv_supplies.kicad_pcb` is generated and its copper is the Proteus copper (0 shorts / 0
orphans / 0 opens in the Proteus geometry and after zone fill, every pad / via / hole on its IPC
position and net). **Pad sizes: user decision A2** (2026-11-20): Proteus pads on exactly U1 U2 ADC1
ADC2 ADC3 DRV5 DRV6 J1, KiCad pads everywhere else. With that, **DRC 0 shorts / 0 clearance / 0
solder-mask bridges / 0 unconnected / 0 parity** (only the accepted courtyards_overlap) and
`tools/check_all.sh` prints **`ALL CHECKS PASSED`** (15 steps).

The phase ran in two sessions: the first generated the board and stopped on the pad question (the
KiCad pads of those 8 parts gave 3 shorts, 29 clearance errors and 3 solder-mask bridges with the
Proteus tracks; per-refdes table and tested options below); the second applied the decision.

### New (all generated / re-runnable)

- **`p2k_config.py`**: `PCB_THICKNESS = 1.6` (user decision, finding 3), `PCB_RULES` (measured, below),
  `DRC_ACCEPTED` (courtyards_overlap).
- **`tools/gen_footprints.py`**: `PROTEUS_PADS = {U1 U2 ADC1 ADC2 ADC3 DRV5 DRV6 J1}`; `refdes=PROTEUS_PADS`
  rules (before the general SI8271 rule; LMV324A / LT1014 / ADC121C027 / HEADER_2X20_50MIL have only the
  refdes rule, all their parts are in the set) pointing to four `<footprint>_ProteusPads` specs
  (`ipc_sizes=True`, same base / renumbering / pad centres): `TSSOP-14_4.4x5mm_P0.65mm_Proteus_ProteusPads`
  (U1 U2), `SOT-23-6_ADC121C027_Proteus_ProteusPads` (ADC1-3), `SOIC-8_3.9x4.9mm_P1.27mm_Proteus_ProteusPads`
  (DRV5 DRV6), `PinHeader_2x20_P1.27mm_Vertical_RowsSwapped_ProteusPads` (J1, Proteus drill 0.558). The
  KiCad-pad specs `TSSOP-14_…_Proteus`, `SOT-23-6_ADC121C027_Proteus` and `PinHeader_2x20_…_RowsSwapped`
  are dropped (no part uses them); `SOIC-8_…_Proteus` stays for DRV1 / DRV2. p2k.footprints fails if a
  refdes of `PROTEUS_PADS` is taken by no such rule. 23 footprints (13 project).
- The six sheet scripts re-run: only Footprint fields changed (16 lines: U1 / U2 five units each, ADC1-3,
  DRV5 DRV6, J1); compare_netlists / ERC unchanged.
- **`tools/check_pin_order.py`**: reads the renamed specs; SI8271 split into DRV1 DRV2 (KiCad-pad spec)
  and DRV5 DRV6 (`_ProteusPads` spec), same results (mirrored 0.275).
- **`tools/make_pcb.sh`** (after tube_psu / tube_power_amp): `p2k.build_pcb`, `p2k.gerber_to_tracks`,
  `p2k.assign_nets`, `p2k.pours_to_zones` (≈ 6 s); `--check` rebuilds into `build/tmp/make_pcb_check`
  (with a copy of the `.kicad_pro`) and compares the board, `reports/pour_nets.json` and the stage A/B
  sections of `reports/assign_nets.txt` byte for byte. No place_refdes (Phase 5).
- **`tools/measure_gaps.py`** (copied unchanged from tube_psu; read-only): the Proteus copper as built.
- **`tools/check_all.sh`**: + make_pcb --check, check_board, `kipy -m p2k.assign_nets --check` (copper
  after zone fill) and `p2k drc`, log in `build/tmp/check_all.log`.
- Removed after the decision: `tools/drc_pending.py` (temporary wrapper that passed exactly the recorded
  pad conflicts as `PENDING USER DECISION`) and `tools/pad_option_test.sh` (scratch-copy option tester;
  it patched the pre-decision gen_footprints.py and no longer applies). Both are in the git history
  (commit d1c551a).

### Steps (tools/make_pcb.sh)

| Step | Tool | Result |
|---|---|---|
| 3a | `p2k.build_pcb` | 158 footprints with nets and symbol links (L1 / L3 excluded), placed from `reports/footprint_fit.csv`; 4 Cu layers (Top Copper / Inner 1 / Inner 2 / Bottom Copper → F.Cu / In1.Cu / In2.Cu / B.Cu, pour outlines on User.1-4); outline 170.085 × 56.485 mm (4 segments); **H1-H4** = `tube_hv_supplies:MountingHole_3.0mm_PTH_Pad6.35mm` (plated 3.0 mm, 6.35 mm pad on every layer, no net) at the IPC hole records; 115 nets; thickness 1.6 mm. |
| 3b | `p2k.gerber_to_tracks` | **1839 tracks** (F 847 / In1 548 / In2 40 / B 404), 3891 pour edge strokes skipped (F 1374 / In1 77 / In2 1971 / B 469), **141 vias** (IPC 141: 139 × 0.5/0.3, 2 × 1.016/0.381; no stacked duplicates), **21 pour outlines** (F 15 / In1 1 / In2 1 / B 4; clear regions 103 / 3 / 131 / 46), no NonConductor draws; every pad flash lands on a footprint pad (329 / 102 / 102 / 202), every drill on a pad hole or via. |
| 3c | `p2k.assign_nets` | stage A (no pours) 225 groups, 0 shorts, 36 orphans, 11 opens (connections through the pours, expected); **stage B (with pours) 119 groups, 0 shorts, 0 orphans, 0 opens**; 1980 tracks / vias assigned, 0 without net; 21 / 21 pours have a net (`reports/pour_nets.json`). |
| 3d | `p2k.pours_to_zones` | 21 zones (24 stroke-closed holes dropped, 259 clearance / thermal holes kept), solid pad connection, priority = Proteus draw order, filled. |
| check | `p2k.check_board` | 162 footprints, 429 pads within 0.039 mm and on their IPC nets (113 IPC nets 1:1), 4 mounting holes, 141 vias (size and net), 1839 tracks / 21 zones with a net: **OK**. |
| check | `p2k.assign_nets --check` | after zone fill: **119 groups, 0 shorts, 0 orphans, 0 opens, 0 foreign nets: OK** (with the KiCad pads on the 8 parts it was 117 groups / 1 short group: ADC1-K2 and U2-4 touched Proteus tracks). |
| check | `p2k drc` | **0 shorts, 0 clearance, 0 solder_mask_bridge, 0 unconnected, 0 parity: OK**; 20 courtyards_overlap accepted; warnings below. |

### Design rules (p2k_config.py `PCB_RULES`, stored in kicad/tube_hv_supplies.kicad_pro)

Measured (`tools/p2k/bin/kipy tools/measure_gaps.py 0.3`, assign_nets stage B geometry with the
Proteus pad flashes): smallest different-net gap **0.1265 mm** (5 mil; track–via, e.g. via
(-58.911, -23.092) Net-(U1A--) / In1.Cu C1_CURRENT track), pad–track 0.1270 (J1-29 / B.Cu 3V3),
track–track 0.1270 (In1.Cu GND / C1_CURRENT), via–via 0.2013, pad–via 0.2179, pour–via 0.2428,
pad–pad 0.2500 (U2-1 / U2-2), pour–pour 0.2540; 52 different-net pairs closer than 0.14 mm; copper to
outline ≥ **0.2286 mm** (In2.Cu pour); drill to drill ≥ 0.4013 mm; thinnest conductor 0.1524 mm.
Rules: clearance **0.12** (also the zone clearance; tube_psu had 0.15 from its 0.1524 gaps), min track
0.15, min via 0.5 / annular 0.1 / drill 0.3, hole clearance 0.15, hole-to-hole 0.25, copper-to-edge
**0.2**; Default netclass track 0.254, via 0.5 / 0.3. Board thickness 1.6 mm (stack-up in Decisions).

### Phase 3 – pad sizes (DECIDED: option A2, user, 2026-11-20)

The DRC with the Phase 2 footprints (KiCad pad sizes everywhere) had **3 shorts, 29 clearance errors
(< 0.12 mm) and 3 solder-mask bridges**, every one between a KiCad pad of one of 8 parts and a Proteus
track (Proteus routes 0.127 mm from its own, smaller pads). Per refdes (actual clearance in mm, rule 0.12):

| Part (footprint) | Proteus pad → KiCad pad | Conflicts with the KiCad pads |
|---|---|---|
| U1 (TSSOP-14_…_Proteus) | 0.4 × 1.1 → 1.475 × 0.4 | 6 clearance: pad 9 / Net-(U1C-+) 0.063, pad 14 / Net-(U1D--) 0.071-0.108, pad 7 / Net-(U1B--) 0.084-0.091 (F.Cu) |
| U2 (TSSOP-14_…_Proteus) | same | **2 shorts** pad 4 (3V3) / Net-(U2A-+) track, 2 mask bridges; 11 clearance 0.036-0.108 (pads 4, 6, 7, 8, 10, 12, 14: GND, U2B/U2C/U2D nodes) |
| ADC1 (SOT-23-6_ADC121C027_Proteus) | 0.5 × 0.65 → 1.325 × 0.6 | **1 short** K2 (3V3) / SCL track, 1 mask bridge, 2 clearance 0.073 |
| ADC2 | same | K2 (GND) / SCL track 0.102 (hidden behind ADC3 in the first DRC: KiCad reports the closest pad per track; it shows once ADC3 has the Proteus pads) |
| ADC3 | same | 3 clearance COM1 (SDA) / SCL track 0.079-0.107 |
| DRV5 (SOIC-8_…_Proteus, bottom) | 0.609 × 1.498 → 1.95 × 0.6 | 1 clearance pad 3 (GND) / B.Cu 3V3 track 0.108 |
| DRV6 (bottom) | same | 1 clearance pad 4 (3V3) / B.Cu GND track **0.031** |
| J1 (PinHeader_2x20_…_RowsSwapped) | 0.762 / drill 0.558 → 1.0 / drill 0.65 | 5 clearance with B.Cu tracks: pads 29 (G3_LO) and 31 (G3_HI) / 3V3 **0.008**, 29 / 3V3 0.087, 5 (INPUT_CURRENT_MEAS) / U_OUT_MEAS 0.093, 27 (PWM_TRANS6) / 3V3 0.110 |

Not affected (KiCad pads clear at 0.12 mm, so they keep the KiCad pads): **J2** (KiCad's 1.0 mm pads
leave 0.27 mm between neighbouring pads, no DRC error at 0.12 mm, no track closer than 0.12), DRV1 /
DRV2, REF1, every resistor / capacitor / inductor, C1-C7 C11 C26, Q3 Q4 Q7 Q8, D2 D18. A smaller
clearance rule does not help (shorts and mask bridges remain).

Options tested in the first session (scratch copies, deleted):

| Option | Parts with Proteus pads | Result |
|---|---|---|
| none | – | 3 shorts, 29 clearance, 3 mask bridges; copper check 1 short group |
| A | U1 U2 ADC1 ADC3 DRV5 DRV6 J1 (the parts the first DRC names) | 0 shorts, **1 clearance** (ADC2 K2 / SCL 0.102), 0 mask bridges; copper 0 shorts |
| **A2 (chosen)** | **U1 U2 ADC1 ADC2 ADC3 DRV5 DRV6 J1** (8 parts) | DRC 0 shorts, 0 clearance, 0 mask bridges, 0 unconnected, 0 parity; copper 0 / 0 / 0 |
| B | whole families: U1 U2, ADC1-3, DRV1 DRV2 DRV5 DRV6, J1 J2 (11 parts) | same as A2 (DRV1 / DRV2 / J2 change nothing in the DRC) |

**Applied (second session):** check_footprints 158/158, 429 pads, 23 footprints, worst residual 0.039 mm
(pcbnew 0.039); make_pcb stage B 119 / 0 / 0 / 0 and byte-identical on `--check`; check_board OK; copper
after zone fill 119 groups, 0 shorts / 0 orphans / 0 opens; DRC as in the table below (silk_over_copper
95 → 90 with the smaller pads). J1 has the Proteus drill 0.558 mm (KiCad 0.65; no `DRILL_SMALLER` entry:
that key is for KiCad drills smaller than Proteus). Reversible: remove a refdes from `PROTEUS_PADS`.

### Remaining DRC items

| Type | Count | Why it stays |
|---|---|---|
| shorting_items / clearance / solder_mask_bridge / unconnected / schematic parity | 0 | – |
| courtyards_overlap (error) | 20 | Proteus placed parts closer than KiCad's IPC-7351 courtyards: C3/R75, C6/R30, D2/C43, DRV6/C32, J1/R3, J1/R36, J1/R12, J1/R45, J2/R78, J2/R79, J2/R80, Q7/R29, R10/C12, R21/C46, R33/R32, R53/R52, R58/U2, R63/R62, R69/R68, R74/REF1; parts sit exactly at the Proteus positions. Accepted (`DRC_ACCEPTED`). |
| silk_overlap / silk_over_copper / silk_edge_clearance (warning) | 111 / 90 / 3 | KiCad footprint silk and default reference positions on the Proteus placement (edge: references of L7, H1, H2 at the bottom edge); Phase 5. |
| track_dangling (warning) | 2 | Proteus copper as drawn: two zero-length (1e-5 mm) OUT1 draws on B.Cu at (-32.852, -11.537), and a 0.9 mm, 0.762 mm wide 15V_BOOST stub on B.Cu from (-73.6, -20.2) to (-72.7, -20.2) (IPC coordinates); Phase 5 `REMOVED_TRACKS` candidates. |

### Negative tests (scratch copies in build/tmp, `P2K_BOARD`, deleted)

First session (board generation):

- T1 one GND track (F.Cu, 0.381 mm at (-3, -3.91)) given net 3V3 in the board file → **only
  `make_pcb.sh --check` fails** ("kicad/tube_hv_supplies.kicad_pcb is not up to date"); check_board OK,
  assign_nets --check unchanged (pcbnew re-derives track nets on load), DRC unchanged. Same as the
  tube_power_amp pitfall: the byte compare is the guard.
- T2 a GND via moved 0.3 mm (inside the GND pour) → make_pcb --check fails; check_board "IPC via
  (-9.804, 6.432) GND: no board via" / "board via (-9.504, 6.432) is neither an IPC via …", FAILED.
- T3 a B.Cu track added between the G3_LO and G3_HI vias → DRC "shorting_items … G3_LO and G3_HI" and
  the copper check (touching pairs) fail; check_board OK (it does not look at extra tracks).

Second session (the applied decision):

- T4 DRV6 removed from `PROTEUS_PADS` → `gen_footprints --check` "out of date: lib/footprint_map.csv"
  (exit 1); after gen_footprints + sheets + make_pcb: `make_pcb --check` against the committed board
  "not up to date"; check_footprints OK (fit is unchanged), copper check OK (the 0.031 mm gap does not
  touch), **`p2k drc` FAILED: 1 clearance, DRV6 pad 4 (3V3) / B.Cu GND track 0.031 mm** – the plain
  DRC step is the guard for a part taken back to the KiCad pads.
- T5 REF1 added to `PROTEUS_PADS` (no refdes rule for ISL21010) → gen_footprints "refdes listed in a
  rule condition but assigned by no such rule: REF1", exit 1.

## Phase 2 – done (Opus 5.5, 2026-11-20)

New (all generated; `--check` steps in `tools/check_all.sh`):

- **`tools/gen_footprints.py`** (RULES + PROJECT of this board, shared code `p2k.footprints`) →
  **`lib/footprint_map.csv`** (160 rows: 158 footprints, L1 / L3 empty with their
  `OFF_BOARD_PARTS` note) and **`lib/tube_hv_supplies.pretty`** (12 project footprints), plus
  **`kicad/fp-lib-table`** (board-local helper copied from tube_power_amp: `footprints.run` does
  not write it, p2k candidate 11).
- **`p2k_config.py`**: `FOOTPRINT_PAD_SIZES = "kicad"`, `OFF_BOARD_PARTS = {L1, L3}`,
  `HOLE_FOOTPRINT = tube_hv_supplies:MountingHole_3.0mm_PTH_Pad6.35mm` (board-only: plated 3.0 mm,
  6.35 mm pad on `*.Cu` = all four layers, pad number 1, no net; `HOLE_VALUE`) for Phase 3.
- The six sheet scripts re-run: only the Footprint fields changed (166 lines); a second run is
  byte-identical. compare_netlists and ERC unchanged (0 wrong-net pins; 0 errors / 21 warnings).
- **`tools/check_pin_order.py`** (board-local, after tube_power_amp's): the unmoved KiCad base
  footprints with the Proteus renumbering fitted onto the IPC pads, both mirror states;
  `--render` draws the fitted KiCad graphics over the Proteus silk / assembly of the part's side
  (`reports/pin_order/<refdes>.png`, 24 parts, compared by eye). Project footprints are checked
  with the base and `renumber` **taken from `gen_footprints.PROJECT`** (see the negative test T3).
- **`reports/footprint_fit.csv`** (placement input for Phase 3) and `reports/footprint_pads.csv`.

### Footprints and fit (`p2k check_footprints --pcbnew`)

**158/158 parts fitted, 429 pads, 22 footprints, worst residual 0.039 mm (limit 0.05); pcbnew
placement of 158 parts, worst pad offset 0.039 mm.** No notes (J1 fits on top with the rows-swapped footprint).
All 38 bottom-side SMD parts fit mirrored; every THT part fits on top.

| Footprint | Parts | Max res. mm | IPC pattern / why |
|---|---|---|---|
| `Resistor_SMD:R_0603_1608Metric` | R3 R12 R36 R45 R76-R80 (9) | 0.039 | 0603, Proteus pads 1.727 apart (KiCad 1.65) |
| `Resistor_SMD:R_1206_3216Metric` | R21 R31 (2) | 0.013 | RESC3216X65, 2.90 apart |
| `Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder` | 34 (R4-R9, R13-R18, R22-R27, R32-R35, R37-R42, R46-R51) | 0.025 | 1206, 3.15 apart |
| `tube_hv_supplies:R_0402_1005Metric_Proteus0.91` | 30 0402 resistors (R1 R2 R10 R11 R19 R20 R43 R44 R52-R71 R73 R74) | 0.001 | KiCad 0402 pads 1.02 apart = 0.053 off at the Proteus 0.914: derived, pads moved |
| `tube_hv_supplies:R_0508_1220Metric_KRL2012` | R29 R30 R72 R75 (4) | 0.000 | KRL2012 shunt, **Proteus land pattern** (`ipc_sizes`, as tube_psu: KiCad 0508 pads would overlap) |
| `Capacitor_SMD:C_0402_1005Metric` | C21 C22 | 0.030 | CAPC1005X55, 0.90 apart |
| `Capacitor_SMD:C_0603_1608Metric` | 25 (C8 C12-C20 C27-C29 C34-C37 C39-C42 C44 C45 C47 C48) | 0.025 | CAPC1608X87, 1.60 apart |
| `Capacitor_SMD:C_0603_1608Metric_Pad1.08x0.95mm_HandSolder` | C24 C25 C32 C33 | 0.001 | 0603, 1.727 apart (the plain C_0603 would be 0.089 off) |
| `Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder` | C23 C30 C31 C38 C43 C46 | 0.013 | 1206, 3.15 apart |
| `Capacitor_SMD:C_2220_5750Metric_Pad1.97x5.40mm_HandSolder` | C9 C10 | 0.038 | CAPC5750X230 |
| `Capacitor_THT:CP_Radial_D10.0mm_P5.00mm` | C1-C7 C11 C26 | 0.000 | 10 mm electrolytic P5; KiCad pad 1 (+) = pin 1 (positive net) |
| `tube_hv_supplies:D_SMA_AC` | D2 D18 (bottom) | 0.000 | SMA (DIOM5025X231), KiCad pad 1 (band) → C, 2 → A, centres moved (4.10 vs 4.00) |
| `Package_TO_SOT_THT:TO-220-3_Vertical` | Q3 Q4 Q7 Q8 | 0.000 | 1 = G, 2 = C, 3 = E |
| `tube_hv_supplies:SOT-23_Proteus` | REF1 | 0.000 | KiCad pads 3, 1, 2 → 1, 2, 3 (as tube_psu), centres moved |
| `tube_hv_supplies:SOT-23-6_ADC121C027_Proteus` (Phase 3: `…_ProteusPads`) | ADC1-ADC3 | 0.000 | KiCad pads 1-6 → A1 A2 COM2 K2 K1 COM1; rows 2.65 apart (KiCad 2.275): centres moved |
| `tube_hv_supplies:TSSOP-14_4.4x5mm_P0.65mm_Proteus` (Phase 3: `…_ProteusPads`) | U1 U2 | 0.000 | rows 5.85 apart (KiCad 5.725) |
| `tube_hv_supplies:SOIC-8_3.9x4.9mm_P1.27mm_Proteus` | DRV1 DRV2 DRV5 DRV6 (bottom; Phase 3: DRV5 DRV6 `…_ProteusPads`) | 0.000 | rows 5.5 apart (KiCad 4.95) |
| `tube_hv_supplies:L_Bourns_SRP1038C_10.0x10.0mm_Proteus` | L2 L4 L7 | 0.000 | SRP1038CC, pads 10.0 apart (KiCad 8.95) |
| `tube_hv_supplies:PinHeader_2x20_P1.27mm_Vertical_RowsSwapped` (Phase 3: `…_ProteusPads`) | J1 | 0.000 | KiCad 2x20 1.27 mm header with odd / even pad numbers swapped (finding 12); pins 37 / 38 N/C |
| `Connector_PinHeader_1.27mm:PinHeader_2x08_P1.27mm_Vertical` | J2 | 0.000 | standard numbering |
| `tube_hv_supplies:Terminal_2x1_P5.00mm_D2.0mm_Drill1.4mm` | B_P B_N V_ANODE GND_PRE GND_PWR VPRE | 0.000 | from the IPC pads (B_P): two holes, both pad 1 |
| `tube_hv_supplies:Terminal_1x1_D2.54mm_Drill1.524mm` | L5 L6 L11 L12 | 0.000 | from the IPC pads (L5): one 2.54 mm pad, drill 1.524 |
| `tube_hv_supplies:MountingHole_3.0mm_PTH_Pad6.35mm` | (board-only, Phase 3 H1-H4) | | plated 3.0 mm, 6.35 mm pad on every copper layer, no net |

### Pin order (`tools/check_pin_order.py`)

| Check | Unmoved KiCad base | Unmirrored | Mirrored | Result |
|---|---|---|---|---|
| REF1, renumbered 3/1/2 → 1/2/3 | SOT-23 | **0.020** | 1.890 | Proteus 1 = JEDEC 3 (GND), 2 = JEDEC 1 (VIN), 3 = JEDEC 2 (VOUT): the ISL21010 pinout, physically correct |
| REF1, JEDEC numbering | SOT-23 | 0.151 (angle not snapped) | 2.263 | does not fit: the renumbering is needed |
| ADC1-3, A1 A2 COM2 K2 K1 COM1 = 1-6 | SOT-23-6 | **0.188** (rows) | 1.909 | fits on top |
| ADC1-3, COM2 on 1 / A1 on 3 (datasheet wiring) | SOT-23-6 | 1.909 | 0.188 | fits only mirrored: impossible on a top part |
| DRV1/2/5/6 (bottom) | SOIC-8 | 3.820 | **0.275** (rows) | fits mirrored, as a bottom part should |
| U1 U2 | TSSOP-14 | **0.063** (rows) | 3.901 | fits on top |
| J1, KiCad numbering | PinHeader_2x20_P1.27mm | 1.270 | **0.000** | fits only mirrored, but J1 is a top part (finding 12) |
| J1, odd / even swapped | PinHeader_2x20_P1.27mm | **0.000** | 1.270 | fits on top: the footprint used |
| J2 | PinHeader_2x08_P1.27mm | **0.000** | 1.270 | standard numbering |
| Q3 Q4 Q7 Q8 | TO-220-3_Vertical | 0.000 | 0.000 | inline; the KiCad tab line lies on the Proteus hatched tab side (render) |
| D2 D18 (bottom), 1 → C | D_SMA | 0.050 | 0.050 | two pads; Proteus silk / assembly have no band to compare (render) |
| C1-C7 C11 C26 | CP_Radial_D10.0mm_P5.00mm | 0.000 | 0.000 | two pads; KiCad '+' at pin 1 next to the Proteus '+' (render) |

- **ADC1-ADC3 (finding 6): reproduced exactly and confirmed.** The project footprint's pads are the
  IPC pads (A1 at -109.70 / -4.80, A2 -5.75, COM2 -6.70; COM1, K1, K2 opposite at -107.05). The
  chirality test puts A1-A2-COM2-K2-K1-COM1 counter-clockwise from the top, as JEDEC 1-6. The
  SOT-23-6 pattern is symmetric under 180 deg, so the geometry alone allows A1 = 1 or A1 = 4;
  the nets decide: with A1 = 1, A2 = pad 2 = GND, K1 = pad 5 = SCL, COM1 = pad 6 = SDA all
  match the ADC121C027 (with A1 = 4 GND would be on SCL). So **A1 = JEDEC pad 1 = VA carries the
  filtered input (#00200 on ADC1) and COM2 = pad 3 = VIN sits on 3V3**: VA and VIN are swapped on
  the built board, as finding 6 says. The KiCad pin-1 triangle lands at A1; the Proteus silk /
  assembly have no pin-1 mark.
- **REF1**: confirmed as expected (Phase 1 note): renumbered, physically correct.
- **J1: Proteus numbering is the mirror image of a standard header** (finding 12).

### Pad sizes and drills vs Proteus (decided in Phase 3: option A2)

Phase 3 (user decision A2): **U1 U2 ADC1 ADC2 ADC3 DRV5 DRV6 J1 now have the Proteus pad size (and J1
the Proteus drill 0.558)**; the table below is the Phase 2 state (KiCad pads everywhere), and stays
true for every other part.

`FOOTPRINT_PAD_SIZES = "kicad"`: KiCad pad sizes and drills everywhere except the IPC-built
terminals and the KRL2012 shunt (Proteus pads). Per refdes (from `reports/footprint_pads.csv`,
IPC size → KiCad size as listed in the files, not rotated):

| Parts | Proteus pad | KiCad pad | Proteus drill | KiCad drill |
|---|---|---|---|---|
| C1-C7 C11 C26 | 1.524 round | 2.0 (pad 1 rounded square) | 0.812 | **1.0** (larger) |
| Q3 Q4 Q7 Q8 | 1.524 round | 1.905 x 2.0 | 1.016 | **1.1** (larger) |
| J1, J2 | 0.762 round | 1.0 (J1: Proteus 0.762 since Phase 3) | 0.558 | **0.65** (larger; J1: 0.558 since Phase 3); KiCad pads leave 0.27 mm between pads at 1.27 mm pitch (Proteus 0.508) |
| B_P B_N V_ANODE GND_PRE GND_PWR VPRE, L5 L6 L11 L12 | 2.0 / 2.54 | same | 1.4 / 1.524 | same |
| R29 R30 R72 R75 | 0.35 x 2.0 | same | | |
| ADC1-ADC3 | 0.5 x 0.65 | 1.325 x 0.6 (Proteus since Phase 3) | | |
| REF1 | 0.889 x 1.016 | 1.475 x 0.6 | | |
| U1 U2 | 0.4 x 1.1 | 1.475 x 0.4 (Proteus since Phase 3) | | |
| DRV1 DRV2 DRV5 DRV6 | 0.609 x 1.498 | 1.95 x 0.6 (DRV5 DRV6: Proteus since Phase 3) | | |
| D2 D18 | 1.6 x 2.26 | 2.5 x 1.8 | | |
| L2 L4 L7 | 4.1 x 3.5 | 3.55 x 3.5 | | |
| C9 C10 | 1.397 x 5.257 | 1.975 x 5.4 | | |
| C23 C30 C31 C38 C43 C46 | 1.016 x 1.524 | 1.325 x 1.8 | | |
| R4-R9 R13-R18 R22-R27 R32-R35 R37-R42 R46-R51 | 1.016 x 1.524 | 1.3 x 1.75 | | |
| R21 R31 | 1.143 x 1.803 | 1.125 x 1.75 | | |
| R3 R12 R36 R45 R76-R80 | 0.889 x 0.889 | 0.8 x 0.95 | | |
| C24 C25 C32 C33 | 0.889 x 0.889 | 1.075 x 0.95 | | |
| C8 C12-C20 C27-C29 C34-C37 C39-C42 C44 C45 C47 C48 | 0.939 x 0.99 | 0.9 x 0.95 | | |
| C21 C22 | 0.609 round | 0.56 x 0.62 | | |
| 30 0402 resistors | 0.508 x 0.762 | 0.54 x 0.64 | | |

**No KiCad drill is smaller than the Proteus drill** (so no `DRILL_SMALLER` entry is needed
yet). The differences stay open: Phase 3 DRC decides where the KiCad pads collide with the
Proteus copper (the 1.27 mm headers and the long KiCad SOT-23-6 / TSSOP / SOIC pads are the
likely ones); switching any part to the Proteus pads is a user decision.

### Negative tests (scratch copy in build/tmp, `P2K_BOARD`, deleted)

- T1 a footprint-map line edited → `gen_footprints --check` "out of date: lib/footprint_map.csv".
- T2 ADC footprint pad A1 moved 0.1 mm → check_footprints "ADC1 … residual 0.083 mm (pad A1)",
  pcbnew "placement off by 0.083 mm" (×3), FAILED; gen_footprints --check out of date.
- T3 ADC renumbering with A1 / COM2 exchanged in `gen_footprints.py` → **check_footprints
  passes** (`p2k.footprints.derive` moves the pads onto the IPC positions whatever the
  renumbering), `check_pin_order` fails ("ADC: unmirrored 1.909"), check_all SOME CHECKS
  FAILED. Hence the pin-order step reads the renumbering from gen_footprints (p2k candidate 12).
- T4 J1 with the plain KiCad header → check_footprints passes with only a note "J1: THT pad
  pattern fits only mirrored -> bottom side" (p2k candidate 13); `check_pin_order` guards it
  ("J1 KiCad" expects the mirrored fit, "J1 rows swapped" the top fit).
- T5 map changed without re-running the sheets → check_footprints "C21: schematic footprint
  … != lib/footprint_map.csv … (re-run the sheet scripts)", FAILED.
- T6 L3 removed from `OFF_BOARD_PARTS` → gen_footprints "L3: in lib/part_map.csv but has no IPC
  pads".

## Phase 1 transcription – done (Fable 5.2, 2026-11-20)

| Sheet | Script | Parts | compare (`--sheet N`) | ERC | Session |
|---|---|---|---|---|---|
| 5 Reference and connector | `tools/sheets/sheet05.py` | 7/7 | 0 missing, 0 extra, 0 wrong-net pins | 0 errors | Fable 5.2, 2026-11-20 |
| 6 ADC | `tools/sheets/sheet06.py` | 15/15 | 0 missing, 0 extra, 0 wrong-net pins | 0 errors | Fable 5.2, 2026-11-20 |
| 2 Gate drivers | `tools/sheets/sheet02.py` | 26/26 | 0 missing, 0 extra, 0 wrong-net pins | 0 errors | Fable 5.2, 2026-11-20 |
| 4 Current measurements | `tools/sheets/sheet04.py` | 34/34 | 0 missing, 0 extra, 0 wrong-net pins | 0 errors | Fable 5.2, 2026-11-20 |
| 3 Voltage measurements | `tools/sheets/sheet03.py` | 42/42 | 0 missing, 0 extra, 0 wrong-net pins | 0 errors | Fable 5.2, 2026-11-20 |
| 1 Power stage | `tools/sheets/sheet01.py` | 34/34 (+ L1, L3 off-board) | 0 missing, 0 extra, 0 wrong-net pins | 0 errors | Fable 5.2, 2026-11-20 |

**Whole project (full comparison, no `--allow-missing`): 158/158 parts, 0 missing, 0 extra, 423
pins compared, 0 wrong-net pins, 115 / 115 IPC net groups complete** (the 113 nets + the two N/C
pads J1-37 / J1-38, each its own group). Every script was run twice: byte-identical files.
Renders in `reports/render/` (compared with `build/tmp/pdf/hi-N.png`).

**ERC: 0 errors, 21 warnings** (the number expected; all permanent):

- 19 `isolated_pin_label` ("label connected to only one pin"):
  - 18: the local labels of the unused J1 ribbon signals (single-pin nets in the IPC: the
    `*_ISO` signals, PWM_TRANS4 / PWM_TRANS6, DAB_*, ADCLK_DAB).
  - 1: `FLOATING` on ADC3-K2 (ADR0 left open; single-pin net in the IPC).
- 2 `ground_pin_not_ground` ("Pin GND2 not connected to ground net"): DRV1-5 and DRV5-5. GND2
  of a high-side driver is the switch node (OUT1 / OUT2), as in the PDF and the IPC; KiCad
  warns because of the pin name.

The 8 temporary isolated-label warnings of the earlier sessions (UIN_MEAS, UC3_MEAS, V_A_MEAS,
U_OUT_MEAS, C1_CURRENT, C3_CURRENT, CURRENT_L1, CURRENT_L3) are gone. **Sheets 3 and 1 needed
no new PWR_FLAG** (no `power_pin_not_driven`): the flags are on sheet 5 (3V3, GND, 15V_BOOST,
+2V5_BIAS) and sheet 2 (bootstrap nodes, OUT1 / OUT2).

Negative test of the final check (scratch copy in build/tmp, `P2K_BOARD`, deleted): R75 not
drawn → "missing parts (1): R75", `check_all.sh` SOME CHECKS FAILED (it passed with
`--allow-missing` before); C3 reversed → "KiCad net C1_CURRENT merges IPC nets [C1_CURRENT]
[UC3]" (4 errors); a junction where the L5 wire crosses the UIN rail → "KiCad net OUT1 merges
IPC nets [UIN ...] [OUT1 ...]", 5 wrong-net pins.

How the sheets were drawn:

- **Sheet 5**: REF1 block as the PDF (3V3 → VIN with C8; VOUT node #00194 with C21; R74 →
  +2V5_BIAS with R73 and C22 to GND). **J1 with pin 1 at the bottom, as in the PDF** (the box
  symbol has pin 1 at the top, so it is placed with `place_mirrored(axis="x")`); every pin has
  its IPC net: power symbols on 33-36 (GND, 3V3) and 39/40 (15V_BOOST), global labels on the 14
  multi-sheet nets, local labels on the 18 unused signals, no-connect flags on 37 / 38. The
  PDF's ADB0-ADB7 are small texts at pins 1-8 plus a text table of the alias links; the
  `15V – 15V_boost` "Not yet complete" link is a text note. PWR_FLAGs of 3V3, GND and
  15V_BOOST in one group below J1.
- **`+2V5_BIAS` needs a PWR_FLAG after all** (the preparation notes said it would not): the
  power symbol's own pin is a power input, and the net is fed only through R74 (passive), so
  ERC reported `power_pin_not_driven` on it. One PWR_FLAG on the +2V5_BIAS node on sheet 5 (as
  tube_psu does for its bias rail).
- **Sheet 6**: wired as the PDF, including its routing of the J2 pin pairs (11/12 → R78, 7/8 →
  R79, 3/4 → R80, the GND buses on both sides of the header, 1/2 on 3V3); J2 mirrored like J1
  (pin 1 at the bottom). ADC1-ADC3 with **VIN (COM2) on 3V3 and VA (A1) on the filtered input**
  (finding 6, reproduced), ADR0 on 3V3 / GND / FLOATING, SCL and SDA as global labels with the
  pull-ups R76 / R77; C27-C29 between 3V3 and GND. The ADC symbol has its rows 2.54 mm apart
  (the PDF 5.08 mm), so the pin wires are closer together than in the PDF; the topology is the
  same.
- **Sheet 2**: one `si8271_cell()` in `_common.py`, called four times at the PDF positions
  (DRV1 over DRV2, DRV5 over DRV6). Output side as the PDF: 15R on OUT+ and 8R on OUT- (pin 1
  on the driver) joined on the gate global label, the VDD2 - GND2 capacitor in a column that
  crosses the two output wires; high side: 15V_BOOST → D18 / D2 (A → C) → R21 / R31 → VDD2
  with C46 / C30 to GND2 = OUT1 / OUT2 (global label), a PWR_FLAG on the bootstrap node and one
  on OUT1 / OUT2; low side: VDD2 on 15V_BOOST with C23 / C31 to GND. Input side laid out
  differently from the PDF: the box symbol's left pins are VDD1, Vin, EN, GND1 (PDF: Vin,
  VDD1, GND1, EN), and the PDF's shared 3V3 / GND / 15V buses between the two drivers of a
  pair are power symbols per cell (VDD1 and EN each on a 3V3 symbol, C24 / C25 / C32 / C33
  between 3V3 and GND at VDD1). The bulk capacitors C38 / C43 (15V_BOOST - GND) stand below
  each pair with their own power symbols. The R23 / R25 / R32 / R35 refdes are on the OUT-
  resistors (IPC), not where the PDF prints them.
- **Sheet 4**: one `shunt_amp_cell()` in `_common.py`, called four times at the PDF positions
  with the PDF's layout: input 330R → + node, 6.8k and 20p up to +2V5_BIAS (power symbol);
  - node with 330R to GND and 6.8k / 20p feedback below; output 100R → global label with 100p
  to GND. U2 units 1-4 = A-D; unit 5 (pins 4 / 11) once at the left with 3V3 / GND and C34
  (the PDF draws C34 alone and repeats the supply pins on every unit). IPC net names
  (finding 7 unchanged).

- **Sheet 3**: one `diff_amp_cell()` in `_common.py`, called four times at the PDF positions
  (U1:C UIN → UIN_MEAS, U1:D UC3 → UC3_MEAS, U1:B V_A → V_A_MEAS, U1:A U_OUT → U_OUT_MEAS)
  with the PDF's layout: two columns of 3 x 1M (GND on top of the left one as a GND symbol
  pointing up, the measured voltage on top of the right one as a global label), the right
  column to the + input with 15k to GND (GND symbol at the right end, as the PDF's `gnd`
  terminal), the left column to the - input with 15k feedback below; output 100R → global
  label with 100p to GND. U1 units 1-4 = A-D; unit 5 (pins 4 / 11) once at the left with
  3V3 / GND and C12 (the PDF draws C12 at U1:A and repeats the supply pins on every unit).
- **Sheet 1**: drawn at the PDF positions: the UIN rail (B+ → L7 → UIN) and the GND rail as
  **one wire each**, so the columns that only cross them (the L5 / L12 / L11 terminal wires,
  UC3, V_A, V_ANODE, the gate and current-sense columns) stay unconnected, as in the PDF;
  junctions only at real nodes (negative-tested, see above). `half_bridge()` in sheet01.py
  draws Q3 / Q4 / R72 and Q8 / Q7 / R29. L1 / L3 with `L_OFFBOARD` between the OUT1 node and
  UC3 and between OUT2 and U_OUT. Global labels: UIN, UC3, V_A, U_OUT pointing up at the top
  (the PDF's terminals), the gate and current-sense labels pointing down below the GND rail,
  **OUT1 / OUT2 on a short stub of the L5 / L11 terminal wires** (the PDF has small `out1` /
  `out2` wire labels at the switch nodes). Local labels B+, UC6, PREOUT. One GND power symbol
  below R75 (the PDF's `gnd` terminal); B_N, GND_PRE, GND_PWR hang on the rail. Not drawn:
  the PDF's second UIN terminal `BRIDGE+` and the `Input_current` terminal on the GND rail
  (text notes). Layout changes: C10 / C9 at x = 55 / 60 (PDF 59 / 64) and the PWM1 gate
  columns at 69 / 72 (PDF 67 / 71), PWM3_LO at 135 (PDF 133, the L11 column), to keep texts
  and columns apart. C_Polarized pin 1 on the positive net everywhere (C3 on UC3 over
  C1_CURRENT, C6 on UC6 over C3_CURRENT).

### N/C pads and the `no_connect` pin type (checked 2026-11-20)

Found by the preamp conversion: KiCad 10's netlist keeps a pin of electrical type `no_connect`
in its own `unconnected-(...)` net even when a wire joins it, so `compare_netlists` cannot see
such a pad wired by mistake.

- **No symbol of `lib/tube_hv_supplies.kicad_sym` uses the `no_connect` pin type** (pin types
  in the library: 73 passive, 21 input, 10 output, 15 power_in, 2 power_out, 1 bidirectional;
  `tools/gen_symbols.py` never writes it). The only N/C pads of the board, J1-37 / J1-38, are
  **passive** header pins with a no-connect flag on sheet 5. Nothing to change.
- Negative test (scratch copy in build/tmp, `P2K_BOARD`, deleted): J1-37 wired to GND without
  the flag, and J1-37 wired to GND with the flag left on → both times `compare_netlists` fails
  with "N/C mismatch: J1-37 is N/C in IPC but on KiCad net GND" and "KiCad net GND merges IPC
  nets [GND ...] [N/C: J1-37]". ERC stayed at 0 errors / 29 warnings in both cases (no
  `no_connect_connected` line), so the comparison, not ERC, is what guards the N/C pads here.
- Rule for later symbols (sheets 3 and 1 needed none): never use the `no_connect` pin type; a
  pad without a net is a passive pin with a no-connect flag.

## Phase 1 preparation – done (Opus 5.5, 2026-11-20)

New in this repo (all generated; `--check` steps in `tools/check_all.sh`):

- **`tools/make_part_map.py` → `lib/part_map.csv`**: 160 parts = 158 on the board + the 2
  off-board inductors L1 / L3. Per sheet 1:36 (34 on the board) 2:26 3:42 4:34 5:7 6:15. Columns
  `refdes` (KiCad), `sheet` (PDF page), `lib_id`, `value`, `device`, `package`, `proteus_refdes`
  (`B+` / `B-` for `B_P` / `B_N`), `off_board`.
  - value = schematic value from ROOT.DSN (`p2k.pdsprj.dsn_values`, = the PDF).
  - device and package from the **ROOT.DSN** component record (board-local `dsn_devices()`:
    the library device after the COMPONENT VALUE label and its `{PACKAGE=...}` property). The
    shared `p2k.pdsprj.lyt_parts` finds **no** record in this ROOT.LYT (p2k candidate 3).
  - sheet = PDF page from the text layer; every refdes is on exactly one page, so
    `PAGE_OVERRIDES` is empty.
  - lib_id from the Proteus device (`SYMBOL_BY_DEVICE`; U1 / U2 by value, both have the Proteus
    device LT1014).
- **`tools/gen_symbols.py` → `lib/tube_hv_supplies.kicad_sym`** (20 symbols: 15 part symbols,
  PWR_FLAG, 4 power symbols):

  | Symbol | From | Pins (= IPC ids) | Parts |
  |---|---|---|---|
  | R, C, L | Device | 1, 2 | 79 R, 39 C, L2 L4 L7 |
  | C_Polarized | Device | 1 (+), 2 | C1-C7, C11, C26 (pin 1 on the positive net in every case) |
  | D | Device:D | `A`, `C` (from 2 / 1) | D2, D18 |
  | IKP08N65F5 | Device:Q_NIGBT_GCE | 1=G 2=C 3=E | Q3 Q4 Q7 Q8 |
  | LMV324A, LT1014 | Amplifier_Operational:LM324 (5 units) | standard quad pinout; unit 5 = V+ 4, V- 11 | U1, U2 |
  | PIN | Connector:TestPoint, value TERMINAL | 1 | the 10 TERMINAL parts (B_P B_N V_ANODE GND_PRE GND_PWR VPRE: blade connector, 2 holes; L5 L6 L11 L12: one hole) |
  | L_OFFBOARD | Device:L, `on_board no` | 1, 2 | L1, L3 (3 mH) |
  | SI8271 | box (as tube_psu) | 1 Vin 2 VDD1 3 GND1 4 EN, 5 GND2 6 OUT- 7 OUT+ 8 VDD2 | DRV1 DRV2 DRV5 DRV6 |
  | ISL21010 | box | 1=GND 2=VIN 3=VOUT | REF1 |
  | ADC121C027 | box | A1=VA A2=GND COM2=VIN, COM1=SDA K1=SCL K2=ADR0 | ADC1-ADC3 |
  | HEADER_2X20_50MIL, HEADER_2X8_50MIL | box (`header`) | 1-40 / 1-16, odd left | J1, J2 |
  | GND, 3V3, 15V_BOOST, +2V5_BIAS | power | | |

  Pin types changed from the datasheet roles to keep ERC honest: ADC121C027 **VA passive**
  (the schematic feeds VA from the analog input, finding 6) and **ADR0 passive** (ADC3's ADR0
  is alone on `FLOATING`; an input pin would be an ERC "not driven" error).
- **`p2k make_skeleton`** → `kicad/` (tube_hv_supplies.kicad_pro, sym-lib-table, root sheet,
  sub-sheets `01 Power stage` … `06 ADC`, empty). **`tools/erc.sh`** (as tube_psu).
- **`tools/sheets/_common.py`**: imports `p2k.sheetkit`; board helpers from tube_power_amp:
  `part(ref)`, `sh_value(ref)`, `sym(ref)` (from the part map), `term(sh, ref, x, y, direction)`
  (terminals with the part map's symbol and value TERMINAL; `sheetkit.terminal` writes value
  "PIN"), `P(x, y)` (PDF render position in 10 px units → sheet mm on the 1.27 mm grid),
  `place_mirrored()` (`Sheet.place` has no mirror).
- **`tools/check_all.sh`**: + part map, symbol library, symbol pins vs IPC, ERC, netlist
  comparison (`--allow-missing` until all 6 sheets are drawn).

### Off-board inductors L1 / L3 (decision)

Drawn as **off-board parts** (symbol `L_OFFBOARD`, excluded from the board), exactly as the PDF
shows them: L1 between the OUT1 node (terminal L5) and the UC3 node (terminal L12), L3 between
OUT2 (L11) and U_OUT (L6). An inductor symbol keeps its two pins on two nets, and
`compare_netlists` / `check_symbols` ignore excluded parts, so **the netlist stays equal to the
IPC** (OUT1, UC3, OUT2, U_OUT separate). Phase 2: `OFF_BOARD_PARTS = {"L1": ..., "L3": ...}`.

Smoke test (scratch copy in build/tmp, deleted): L5 / L12 terminals with L1 between them, an
`OUT1` global and `UC3` local label; ADC1 with R76 / R78 / C35 and power symbols →
compare 0 wrong-net pins (L1 ignored), ERC 0 errors (3 isolated-label warnings of the partial
drawing). Negative: L1 drawn with the plain `L` symbol → compare "extra part L1"; L5 wired to
L12 → "KiCad net OUT1 merges IPC nets [OUT1] [UC3]"; R78 reversed → "merges IPC nets #00200
#00211"; a part-map line added → `make_part_map --check` and check_symbols fail; a symbol pin
renamed → `gen_symbols --check` and check_symbols fail. The first smoke run also showed that
an `input` ADR0 / SCL pin with only a label is an ERC error (hence ADR0 passive; SCL is
driven by R76 / J1 in the full sheet).

### Pinouts (Proteus ids vs datasheets; Phase 2 confirms with the pad fit)

- **ADC1-ADC3** (SOT-23-6): the IPC pad positions put A1, A2, COM2 down one side and COM1,
  K1, K2 down the other, A1 opposite COM1 and COM2 opposite K2, i.e. the standard footprint
  with A1=1 A2=2 COM2=3 K2=4 K1=5 COM1=6. With the ADC121C027 pinout (1 VA, 2 GND, 3 VIN,
  4 ADR0, 5 SCL, 6 SDA) the symbol names are right, and the wiring is not: **finding 6**.
- **REF1** (SOT-23): Proteus pin 1 is the lone pad (JEDEC 3), 2 and 3 the pair (JEDEC 1 and
  2). Proteus 1=GND 2=VIN 3=VOUT therefore sits on JEDEC 3=GND 1=VIN 2=VOUT, which is the
  ISL21010 pinout: renumbered, physically correct (same as tube_psu's ADR380). Phase 2
  footprint: KiCad SOT-23 pads 1, 2, 3 renumbered to Proteus 2, 3, 1 (the fit confirms).
- Q3/Q4/Q7/Q8: Proteus device IRGB14C40L (a different IGBT model), value IKP08N65F5; both
  TO-220 G-C-E, the nets agree (gate on PWMx, collector on UIN / OUTx).
- U1: value LMV324A, Proteus device LT1014; both standard quad pinout (V+ 4 on 3V3, V- 11 on
  GND in the IPC).
- J1: Proteus device `38 PIN HEADER 50TH`, value / package 40 pins; pins 37, 38 are N/C.

### Transcription rules (for the sheet sessions)

- **Symbols and values**: only `tube_hv_supplies:` symbols, exactly the `lib_id` and `value` of
  `lib/part_map.csv` per refdes (`_common.sym(ref)`, `sh_value(ref)`). Refdes = the `refdes`
  column: **`B_P`** (Proteus `B+`) and **`B_N`** (`B-`); the other terminals keep their names
  (`V_ANODE`, `GND_PRE`, `GND_PWR`, `VPRE`, `L5`, `L6`, `L11`, `L12`). Terminals with
  `_common.term()` (never `sheetkit.terminal`: wrong value). L1 / L3 with `sym("L1")` =
  `L_OFFBOARD` (never `L`), wired between the terminal nodes as on page 1.
- **Op-amps**: units 1-4 = A-D as in the PDF (`U1:A` = unit 1 pins 1/2/3, B = 7/6/5,
  C = 8/9/10, D = 14/13/12); the supply pins are unit 5, placed once per op-amp (on its sheet:
  U1 sheet 3, U2 sheet 4) with 3V3 / GND power symbols. The PDF repeats pins 4 / 11 on every
  unit; draw them once.
- **Power symbols** for the 4 rails: **GND**, **3V3**, **15V_BOOST**, **+2V5_BIAS** (IPC
  spelling; the PDF draws them as plain terminals). PDF aliases drawn as these symbols:
  `gnd`, `Gnd` (J1-34) → GND; `15V` (page 2) and `15V_boost` → 15V_BOOST (the page 5 link
  `15V — 15V_boost` "Not yet complete" becomes a text note). Use `flagged_power` (power symbol
  + PWR_FLAG) once per rail where ERC reports an undriven power pin: GND, 3V3 (sheet 5 or 6,
  where they enter on J1), 15V_BOOST (sheet 5, J1-39/40): all three are on sheet 5 (done), so
  the other sheets use plain `power_at`. +2V5_BIAS has its PWR_FLAG on sheet 5 too (found in
  transcription: the power symbol's pin is a power input and R74 is passive).
- **Floating driver nodes**: the high-side drivers' VDD2 (bootstrap nodes #00021 = DRV1-8 /
  C46 / R21, #00036 = DRV5-8 / C30 / R31) and GND2 (OUT1 = DRV1-5, OUT2 = DRV5-5) are power
  inputs fed by passives only: put one PWR_FLAG on each of these four nets (as tube_psu's
  si8275_cell). DRV2 / DRV6 VDD2 are on 15V_BOOST, GND2 on GND.
- **Net names = IPC names** (`reference/pins_by_net.md`), whatever the PDF writes. PDF aliases:
  `b+` → B+; `Uin` / `UIN` and **`BRIDGE+`** (page 1, on the same net) → UIN; `Uc3` → UC3;
  `V_a` → V_A; `U_out` → U_OUT; `out1` / `out2` → OUT1 / OUT2; `uc6` → UC6; `preout` →
  PREOUT; `current_L3` → CURRENT_L3; `C1_current` / `C3_current` → C1_CURRENT / C3_CURRENT;
  `*_meas` → `*_MEAS` (`Uin_meas` → UIN_MEAS, `Uc3_meas` → UC3_MEAS, `U_out_meas` →
  U_OUT_MEAS, `V_A_meas` → V_A_MEAS, `input_current_meas` → INPUT_CURRENT_MEAS, …); `scl` /
  `sda` → SCL / SDA; `floating` → FLOATING. **Page 1 `Input_current`** hangs on the GND rail:
  it is GND (no label; text note optional). **Page 5 `ADB0`-`ADB7`** are aliases of the
  `*_MEAS` nets: J1-1 C2_CURRENT_MEAS, J1-2 V_A_MEAS, J1-3 C3_CURRENT_MEAS, J1-4 UIN_MEAS,
  J1-5 INPUT_CURRENT_MEAS, J1-6 UC3_MEAS, J1-7 C1_CURRENT_MEAS, J1-8 U_OUT_MEAS: put the IPC
  name on the J1 pin, ADBn as a text note at most. Never two names on one net (ERC
  `multiple_net_names`).
- **Global labels** for the 28 named nets with pins on more than one sheet:
  sheets 1+2 OUT1, OUT2, PWM1_HI, PWM1_LO, PWM3_HI, PWM3_LO; sheets 1+3 UIN, UC3, V_A, U_OUT;
  sheets 1+4 C1_CURRENT, C3_CURRENT, CURRENT_L1, CURRENT_L3; sheets 2+5 G1_HI, G1_LO, G3_HI,
  G3_LO; sheets 3+5 UIN_MEAS, UC3_MEAS, V_A_MEAS, U_OUT_MEAS; sheets 4+5 INPUT_CURRENT_MEAS,
  C1_CURRENT_MEAS, C2_CURRENT_MEAS, C3_CURRENT_MEAS; sheets 5+6 SCL, SDA.
  **Local labels** for one-sheet named nets: sheet 1 B+, UC6, PREOUT; sheet 5 the 18 unused
  J1 signals; sheet 6 FLOATING. Auto-named `#00xxx` nets are plain wires (none crosses a
  sheet).
- **N/C pins**: J1-37, J1-38 (no-connect flags). No other pin is without a net.
- **Single-pin nets (19)**: the 18 J1 ribbon signals not used on this board (ADASEL0_ISO
  J1-12, ADASEL1_ISO J1-9, ADASEL2_ISO J1-10, ADCLK_DAB J1-23, CLK1_ISO J1-13, CS1_ISO J1-14,
  DAB_PWM_HI_SEC J1-28, DAB_PWM_PRI_HI_ISO J1-21, DAB_PWM_PRI_LO_ISO J1-24, PWM_G1_ISO J1-19,
  PWM_G2_ISO J1-20, PWM_G3_ISO J1-22, PWM_G4_ISO J1-17, PWM_TRANS1_ISO J1-16, PWM_TRANS2_ISO
  J1-15, PWM_TRANS3_ISO J1-18, PWM_TRANS4 J1-26, PWM_TRANS6 J1-27) and FLOATING (ADC3-K2): a
  local label on the pin; ERC "isolated label" warnings for them are expected (explain them).
- **Page 2 refdes positions**: R23 / R25 / R32 / R35 are printed next to the GND2 pins but are
  the 8R resistors on OUT- (DRVn-6 → R-1); read the nets from
  `reference/pin_nets_by_component.md`, not from the label positions.
- **Grid 1.27 mm** for symbols, wires and labels; `P()` keeps the layout close to the PDF.
  Use the `p2k.sheetkit` helpers (`vert2`, `horiz2`, `power_at`, `glabel_left/right`,
  `label_left/right`, `flagged_power`) and `_common` (`term`, `sym`, `sh_value`, `P`,
  `place_mirrored`); repeated blocks of this board go into `tools/sheets/_common.py` (the
  SI8271 driver cell, ×4 on page 2; the divider + difference amplifier, ×4 on page 3; the shunt
  amplifier, ×4 on page 4).
- One script per sheet: `tools/sheets/sheetNN.py` (NN = PDF page) rebuilding
  `kicad/NN_*.kicad_sch` from scratch; render with `tools/p2k/bin/p2k render_sheet
  kicad/NN_*.kicad_sch` and compare with `build/tmp/pdf/hi-N.png`.
- After each sheet: `tools/p2k/bin/p2k compare_netlists --allow-missing --sheet N` and
  `tools/erc.sh`, then `tools/check_all.sh`. Target per sheet: 0 missing on that sheet, 0
  compare errors, 0 ERC errors (warnings explained here).
- Order: 5 Reference and connector → 6 ADC → 2 Gate drivers → 4 Current measurements →
  3 Voltage measurements → 1 Power stage.
- No new design findings came from sheets 2 and 4 (findings 2, 7 and 8 cover them); sheets 3
  and 1 added findings 10 and 11.

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
  netlist (`OFF_BOARD_PARTS` in Phase 2). Decided in Phase 1 preparation: off-board parts.
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

`tools/check_all.sh`, 2026-11-20 (Phase 3 done, pad decision A2 applied):

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
== Part map up to date
make_part_map: lib/part_map.csv up to date, 160 parts (158 on the board); per sheet 1:36 2:26 3:42 4:34 5:7 6:15
== Symbol library up to date
gen_symbols: lib/tube_hv_supplies.kicad_sym up to date (20 symbols)
== Symbol pin sets vs IPC
  ADC121C027             3  pins  6  ADC1 ADC2 ADC3
  C                     39  pins  2  C9 C10 C23 C24 C25 C30 C31 C32 ...
  C_Polarized            9  pins  2  C1 C2 C3 C4 C5 C6 C7 C11 ...
  D                      2  pins  2  D2 D18
  HEADER_2X20_50MIL      1  pins 40  J1
  HEADER_2X8_50MIL       1  pins 16  J2
  IKP08N65F5             4  pins  3  Q3 Q4 Q7 Q8
  ISL21010               1  pins  3  REF1
  L                      3  pins  2  L2 L4 L7
  LMV324A                1  pins 14  U1
  LT1014                 1  pins 14  U2
  L_OFFBOARD             2  pins  2  L1 L3
  PIN                   10  pins  1  B_N B_P GND_PRE GND_PWR L5 L6 L11 L12 ...
  R                     79  pins  2  R26 R27 R29 R30 R72 R75 R21 R22 ...
  SI8271                 4  pins  8  DRV1 DRV2 DRV5 DRV6
symbols: 15 part types, 160 refdes, 4 power symbols
symbols: OK
== ERC
erc: 0 errors, 21 warnings (reports/erc.rpt)
== Netlist comparison vs IPC
compare: parts 158/158 present, 0 missing, 0 extra; pins compared 423, wrong-net pins 0; IPC nets touched 115, complete 115
compare: per sheet (drawn/total) 1:34/34 2:26/26 3:42/42 4:34/34 5:7/7 6:15/15
compare: OK
== Footprint library, map and fp-lib-table up to date
gen_footprints: 158 parts, 23 footprints (13 project), up to date
== Footprints vs IPC pad geometry (fit and pcbnew placement)
check_footprints: pcbnew placement of 158 parts, worst pad offset 0.039 mm
check_footprints: 158/158 parts fitted, 429 pads, 23 footprints, worst residual 0.039 mm (limit 0.05)
check_footprints: OK
== Pin order vs unmoved KiCad base footprints
check            KiCad base (unmoved)                           unmirrored         mirrored  result
REF1             SOT-23                                      0.020 @    90    1.890 @   270  unmirrored 0.020  (SOT-23 renumbered (1 = JEDEC 3): fits; Proteus 1.90 mm rows vs KiCad 1.875)
REF1 plain       SOT-23                                      0.151 @ 329.8    2.263 @ 80.89  no fit on its side  (SOT-23 with JEDEC numbering: does not fit (> 0.1 mm, angle not snapped))
ADC              SOT-23-6                                    0.188 @     0    1.909 @   180  unmirrored 0.188  (A1 A2 COM2 K2 K1 COM1 = JEDEC 1-6: fits (rows 2.65 vs KiCad 2.275 -> 0.1875))
ADC datasheet    SOT-23-6                                    1.909 @     0    0.188 @   180  no fit on its side  (VA / VIN exchanged (COM2 on pad 1, A1 on pad 3, the datasheet wiring): fits only mirrored, i.e. not on a top-side part)
SI8271           SOIC-8_3.9x4.9mm_P1.27mm                    3.820 @     0    0.275 @   180  mirrored 0.275  (bottom side, rows 5.5 vs 4.95)
SI8271 Proteus pads SOIC-8_3.9x4.9mm_P1.27mm                    3.820 @     0    0.275 @   180  mirrored 0.275  (bottom side, rows 5.5 vs 4.95 (spec with the Proteus pad sizes))
TSSOP-14         TSSOP-14_4.4x5mm_P0.65mm                    0.063 @    90    3.901 @   270  unmirrored 0.063  (rows 5.85 vs 5.725)
J1 rows swapped  PinHeader_2x20_P1.27mm_Vertical             0.000 @    90    1.270 @    90  unmirrored 0.000  (odd / even swapped: fits on top)
J1 KiCad         PinHeader_2x20_P1.27mm_Vertical             1.270 @    90    0.000 @    90  mirrored 0.000  (standard numbering fits only MIRRORED (bottom), but J1 is on top)
J2               PinHeader_2x08_P1.27mm_Vertical             0.000 @   180    1.270 @   180  unmirrored 0.000  (standard numbering fits on top)
TO-220           TO-220-3_Vertical                           0.000 @   180    0.000 @     0  unmirrored 0.000  (inline: marker by render)
SMA              D_SMA                                       0.050 @     0    0.050 @   180  mirrored 0.050  (two pads: band by render)
CP               CP_Radial_D10.0mm_P5.00mm                   0.000 @   270    0.000 @    90  unmirrored 0.000  (two pads: '+' by render)
check_pin_order: OK (results as recorded in STATUS.md)
== PCB rebuilt from schematic + gerbers, up to date
build_pcb: 158 footprints placed (2 excluded from board), 4 mounting holes, 115 nets, 4 outline segments
gerber_to_tracks: 1839 tracks, 141 vias (IPC 141), 21 pour outlines on User.1-4
assign_nets: stage A (no pours): 225 groups, 0 shorts, 36 orphans, 11 opens
assign_nets: stage B (with pours): 119 groups, 0 shorts, 0 orphans, 0 opens
pours_to_zones: 21 pours -> 21 zones; 24 holes closed by the stroke, 259 holes kept
make_pcb: board rebuilt from scratch, byte-identical
== Board pads, holes, vias vs IPC (position, size, nets 1:1)
check_board: 162 footprints, 429 pads, worst pad offset 0.039 mm (limit 0.05), 113 IPC nets mapped 1:1, 4 mounting holes
check_board: 1839 tracks, 141 vias, 21 zones
check_board: OK
== Board copper connectivity after zone fill
assign_nets: after zone fill: 119 groups, 0 shorts, 0 orphans, 0 opens, 0 items with a foreign net
assign_nets: OK (report reports/assign_nets.txt)
== DRC with schematic parity
drc: 226 violations, 0 shorts, 0 unconnected, 0 parity issues (reports/drc.json)
drc:     20 error    courtyards_overlap  accepted: KiCad IPC-7351 courtyards vs the Proteus placement (parts at the Proteus positions)
drc:    111 warning  silk_overlap
drc:     90 warning  silk_over_copper
drc:      3 warning  silk_edge_clearance
drc:      2 warning  track_dangling
drc: OK

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
   **Answered (user, 2026-11-20): the board is 1.6 mm**; the READ-ME stack-up is a Proteus default.
   `PCB_THICKNESS = 1.6`.
4. **No title blocks** on the six PDF pages (sheet names chosen from content).
5. The PDF and the project were saved 2026-09-19, and the CADCAM export was made 2026-11-19 from
   that project. The PDF matches the IPC: every IPC part is on a page, and only the off-board
   L1/L3 are extra.
6. **ADC121C027 supply and input swapped (all three ADCs, to confirm):** page 6 wires the pin
   labelled VIN (Proteus COM2) to 3V3 and the pin labelled VA (A1) to the filtered analog input
   (R78-R80 2k / C35-C37). The pad geometry puts A1 on SOT-23-6 pin 1 and COM2 on pin 3, and
   the ADC121C027 pinout is 1 = VA (supply and reference), 3 = VIN (analog input), so on the
   built board the input pins sit at 3V3 and the inputs are fed into the supply pins. Unless the
   board was reworked, the ADCs cannot measure as drawn. Reproduced as drawn (the symbol keeps
   the datasheet names; VA is a passive pin so ERC does not flag the input nets). Check
   against the datasheet and the real board; a redesign item.
   **Phase 2 confirmed it geometrically** (`tools/check_pin_order.py`, STATUS "Phase 2 - pin
   order"): A1 = JEDEC pad 1 and COM2 = pad 3 on all three ADCs (the only assignment with A2 on
   GND, K1 on SCL, COM1 on SDA); the footprint reproduces the IPC pads exactly.
7. **Current-measurement net names do not match what they measure:** the page 1 terminal
   `Input_current` sits on the GND rail (there is no input-current shunt; B- is GND), U2:A
   amplifies `C3_CURRENT` (shunt R30) into `INPUT_CURRENT_MEAS`, U2:C amplifies `CURRENT_L1`
   into `C2_CURRENT_MEAS`, U2:D amplifies `CURRENT_L3` into `C3_CURRENT_MEAS` (only U2:B,
   `C1_CURRENT` → `C1_CURRENT_MEAS`, matches). Names kept (IPC); note for the redesign and for
   the control-card firmware mapping of J1-1/3/5.
8. **LT1014 on a 3.3 V supply (to check):** U2 (value LT1014, the shunt amplifiers) runs from
   3V3 like U1 (LMV324A). The LT1014 is specified for 5 V single supply and up; its output
   swing and common-mode range at 3.3 V are not specified. Check the fitted part (perhaps an
   LMV324 like U1) before the redesign.
9. **Proteus library devices differ from the values:** Q3/Q4/Q7/Q8 use the device IRGB14C40L
   (value IKP08N65F5), U1 the device LT1014 (value LMV324A), REF1 the device ADR380 (value
   ISL21010CFH315Z-TK), J1 the device `38 PIN HEADER 50TH` (40-pin package, 37/38 unused).
   Pinouts agree with the values' parts (TO-220 G-C-E, quad op-amp, SOT-23 renumbered), so
   nothing changes; the KiCad symbols are named after the values.

10. **Voltage-measurement range (note for the redesign):** the four difference amplifiers
    (3 x 1M, 15k) have a gain of 15k / 3M = 1 / 200, so the 3.3 V output range of U1
    corresponds to 660 V at UIN / UC3 / V_A / U_OUT, referred to GND with no offset (only
    positive voltages can be measured). The - divider's far end is GND on the same board, so
    the amplifier is a plain 1 / 200 divider with a buffer; fine as built, noted only.
11. **R26 || R27 (1k each, 500 R) between UC6 and PREOUT, and the L4 / C6 / R30 arrangement:**
    C6 returns through the shunt R30 (`C3_CURRENT`), C5 and C7 go straight to GND, and the
    load current to VPRE passes R26 || R27 (500 R). As drawn in the PDF and the IPC;
    reproduced. **Confirmed intended by the user (2026-11-20):** the output fed the preamp, which
    draws only milliamps, so the 500 R series resistance is fine.

12. **J1 (40-pin control-card ribbon) is numbered as the mirror image of a standard header (to
    check against the control card):** J1 is a top-side part (Proteus top assembly outline and
    top silk "J1"), but its pad numbering only matches a standard 2x20 header (KiCad, and J2 on
    this board, and tube_psu's 2x25 J2) mirrored, i.e. as seen from the bottom: pin 2 sits below
    pin 1 where a standard top-view header has it on the other side (odd / even rows exchanged).
    With a standard IDC header and cable, the physical pin n would carry the net of Proteus pin
    n+1 / n-1 (pairs 1-2, 3-4, … swapped), unless the control card's connector uses the same
    mirrored footprint (then the two swaps cancel). Reproduced: KiCad footprint
    `PinHeader_2x20_P1.27mm_Vertical_RowsSwapped` (KiCad's pin-1 corner mark lands at the pad
    numbered 2). Check the control card footprint / the built cable; a redesign item.

13. **Copper clearances of 0.127 mm (5 mil) (Phase 3, note for the redesign):** the Proteus copper
    has 52 different-net pairs closer than 0.14 mm, the smallest 0.1265 mm (track–via, track–track on
    In1.Cu, J1 pads to B.Cu tracks); tube_psu's smallest was 0.1524. Copper reaches 0.2286 mm from the
    board edge (the In2.Cu pour). Both are within common 4-layer fab limits but tighter than the
    other boards; `PCB_RULES` clearance 0.12 / edge 0.2 reproduce them.
14. **Proteus copper stubs (Phase 3, cosmetic):** two zero-length OUT1 draws on B.Cu at
    (-32.852, -11.537) and a dangling 0.9 mm 15V_BOOST stub on B.Cu (-73.6 → -72.7, y -20.2) (IPC
    coordinates); KiCad DRC `track_dangling` warnings, copper as drawn.

## p2k candidates

Shared-tool limitations met on this board, with the board-local workaround used.

1. `ipc356`: the `pin_nets_by_component.md` header prints `Net aliases: .` when `NET_ALIASES` is
   empty. Print "none" instead (cosmetic).
2. `ipc356`: `pins_by_net.md` lists a two-hole terminal pin twice (`B_P-1 B_P-1`, pin count 5 for
   B+), because it counts records, not distinct pins. Distinct `(refdes, pin)` would read better
   (cosmetic; tube_psu has the same).
3. **`p2k.pdsprj.lyt_parts` finds no part record in this ROOT.LYT** (Proteus 8.12 SP2): there
   are no `EID` / `EID_A` markers. The records here read `<package> <refdes> PS "Vector Font"
   "PART REFERENCE" <value> PS "Vector Font" "PART VALUE" <pin nets...>`, with stray binary
   bytes glued to tokens (`Q74`, `TERMINALP`, `IKP08N65F54`), so a token reader is unreliable.
   Workaround: `dsn_devices()` in `tools/make_part_map.py` reads device and package from the
   ROOT.DSN component record (device = first string after `COMPONENT VALUE`, package =
   `{PACKAGE=...}` property). The shared tool would need: a `dsn_devices` reader (this one), and
   a binary (length-prefixed) reader for this LYT record format.
4. **`p2k.sheetkit.terminal` hard-codes value "PIN"** (and its left/right text justification
   draws over the circle in KiCad 10.0.7): `term()` in `tools/sheets/_common.py`, copied from
   tube_power_amp (their candidates 3 and 7).
5. **`p2k.sch_builder.Sheet.place` cannot mirror**: `place_mirrored()` in `_common.py`, copied
   from tube_power_amp (their candidate 6); used for J1 and J2 (pin 1 at the bottom, as the
   PDF draws them). `symgen.header` could also take a `bottom_up=` option. The mirrored box is
   not symmetric about its origin, so the sheet script passes `ref_at` / `value_at` (the
   library value position lands inside the box).
6. **Part-map generator** is the tube_power_amp script plus `dsn_devices()` and a value-based
   symbol choice (`SYMBOL_BY_VALUE`, two op-amps with the same Proteus device): a shared
   `p2k.part_map` would serve all boards (tube_power_amp candidate 5).
7. `symgen.box` pin length is fixed at 2.54 mm: four-character pin numbers (`COM1`, `COM2` of
   the ADC121C027) overlap the body outline in the render (cosmetic). A `pin_length=` option
   would fix it.
8. `Sheet.place` puts the reference / value of a **horizontal two-pin part** 2.54 mm above /
   below the centre line (or both on one side with `text=`). That fits a resistor, but a
   horizontal capacitor's plates are about 2 mm high, so the texts lie on them. Workaround:
   `ref_at` / `value_at` at ±3.81 mm in `_common.py` (`_hcap()`, `si8271_cell()`). The shared
   tool could take the offset from the symbol's body height.

9. `compare_netlists` prints "IPC nets touched 115, complete 115" on a board with 113 nets: the
   two N/C pads (J1-37 / 38) count as one group each. Printing "113 nets + 2 N/C pads" would
   read better (cosmetic).
10. The `SEND` / `SEND1` refdes sort crash of `compare_netlists` (reported by the FX-loop
    board) **does not occur here**: every refdes prefix of this board is either always
    numbered or never; no wrapper needed.
11. `p2k.footprints.run` does not write the project `kicad/fp-lib-table`: `fp_lib_table()` in
    `tools/gen_footprints.py` (copied from tube_power_amp, their candidate).
12. **`p2k.footprints.derive` moves the base pads onto the IPC positions however far they are**
    (negative test T3: A1 / COM2 exchanged in the ADC renumbering → the derived footprint still
    fits, check_footprints passes). The shared tool should fit the unmoved, renumbered base first
    and fail (or need an explicit `allow_move=` limit) when a pad moves more than a fraction of
    the pitch (e.g. > 0.5 mm); the board-local guard is `tools/check_pin_order.py`, which takes
    base + renumber from `gen_footprints.PROJECT`.
13. `p2k.check_footprints` accepts a THT part that fits only mirrored (bottom) with a note (J1
    with the plain KiCad header, T4). It could compare with the Proteus assembly / silk layer
    the part is drawn on, or need a config list of bottom THT parts.
14. `tools/check_pin_order.py` is board-local here and on tube_power_amp (with the tie rule for
    symmetric two-pad / inline patterns and `--render` over the Proteus silk / assembly of the
    part's side): a shared `p2k.check_pin_order` with the CHECKS table in the board repo.

15. **`tools/measure_gaps.py` copied unchanged a third time** (tube_psu, tube_pi_fxloop, here): a
    shared `p2k.measure_gaps` would do.
16. **A pending-decision mode for `p2k drc` and `p2k.assign_nets --check`:** board-local
    `tools/drc_pending.py` (as tube_pi_fxloop's; removed after the decision, in git history d1c551a)
    passed exactly the recorded conflicts while the pad decision was open. A config key (e.g. `DRC_PENDING = {refdes: reason}` with expected counts) and
    a "PENDING" exit state in the shared tools would replace the per-board wrappers.
17. **Testing Proteus pads on a refdes set:** board-local `tools/pad_option_test.sh` (removed after the
    decision, in git history d1c551a) patched
    `refdes=` rules and `<footprint>_ProteusPads` specs (`ipc_sizes=True`) into a scratch copy of
    gen_footprints.py. `p2k.footprints` could take a `PROTEUS_PADS = {refdes}` config key that does
    this (derived Proteus-pad variants for the named parts only), so the decision is one config line.
    Applied by hand here: `PROTEUS_PADS`, four `refdes=` rules and four `_ProteusPads` specs (≈ 40 lines
    in gen_footprints.py, plus the renamed specs in check_pin_order.py).
18. **A changed track net is caught only by the byte compare** (negative test T1, as tube_power_amp):
    pcbnew re-derives track nets on load, so check_board, assign_nets --check and DRC do not see it.
    check_board could read the track nets from the file (s-expression) and compare them with the
    assign_nets groups.
19. KiCad's DRC reports one violation per track against its closest pad, so a conflict can hide
    behind a neighbour (ADC2 showed only after ADC3 had the Proteus pads): `pad_option_test.sh`
    re-runs the DRC on the whole candidate set; a shared tool could measure every pad-to-track gap
    itself (as measure_gaps does for the Proteus copper).

## Decisions

- **Phase 2 footprints (agent, 2026-11-20):** KiCad library footprints where their pads land
  within 0.05 mm; otherwise derived project footprints with the pad centres on the Proteus
  positions (0402 R, SMA, SOT-23, SOT-23-6, TSSOP-14, SOIC-8, SRP1038C, J1) and IPC-built
  terminals; `FOOTPRINT_PAD_SIZES = "kicad"` (Proteus pads only on the KRL2012 shunts and the
  terminals). Pad sizes per refdes stay an open user decision (Phase 2 table).
- **J1 drawn with the rows-swapped header on the top side** (agent, 2026-11-20), not the KiCad
  header flipped to the bottom: the copper is identical either way, the part is on top in
  Proteus. Finding 12 is the user's question.
- `reports/pin_order/*.png` and `reports/footprint_fit.csv` / `footprint_pads.csv` are
  committed (as tube_power_amp).

- **Board thickness 1.6 mm (user, 2026-11-20, finding 3)**; `PCB_THICKNESS = 1.6`. The CADCAM
  READ-ME stack-up of about 2.27 mm is a Proteus default.
- **Stack-up (agent's choice, 2026-11-20):** a common 4-layer 1.6 mm build, F.Cu 0.035 / prepreg
  0.2104 / In1.Cu 0.0152 / core 1.065 / In2.Cu 0.0152 / prepreg 0.2104 / B.Cu 0.035 (1.586 mm plus
  solder resist). Only the total thickness goes into the board (`build_pcb`); the checks compare the
  copper layers, which are what matters electrically.
- **Phase 3 rules (agent):** `PCB_RULES` from the measured Proteus copper (clearance 0.12, edge 0.2;
  "Phase 3 – design rules"); `DRC_ACCEPTED = {courtyards_overlap}` (Proteus placement).
- **Pad sizes: option A2 (user, 2026-11-20, through the coordinating session):** Proteus pads on
  exactly the 8 parts U1 U2 ADC1 ADC2 ADC3 DRV5 DRV6 J1 (their KiCad pads shorted or came closer than
  0.12 mm to Proteus tracks); KiCad pads everywhere else. Applied board-locally in
  `tools/gen_footprints.py` (`PROTEUS_PADS`, `_ProteusPads` specs with `ipc_sizes=True`);
  `tools/drc_pending.py` removed, check_all.sh runs `p2k.assign_nets --check` and `p2k drc` directly.
- **Footprint names (agent, 2026-11-20):** the Proteus-pad variants are named `<footprint>_ProteusPads`
  (as tested with the option script and as tube_psu did); the unused KiCad-pad specs were dropped.

- **Finding 11, R26 || R27 (500 R) in series with the VPRE output: intended (user, 2026-11-20).** The
  output fed the preamp, which draws only milliamps.

- KiCad refdes `B_P` / `B_N` for `B+` / `B-` (P/N for the sign, as tube_psu `P400V` /
  `N5V_OUT`). They can still be renamed before any Phase 1 sheet exists.
- Sheet names chosen from the page content (no title blocks).
- `NET_ALIASES` empty (no `=POWER` names; `+2V5_BIAS` kept until the user decides, finding 1).
- **L1 / L3 drawn as off-board parts** (symbol `L_OFFBOARD`, excluded from the board and the
  netlist comparison) between their terminal pairs, as on page 1; the netlist stays equal to
  the IPC. Phase 2 lists them in `OFF_BOARD_PARTS`.
- Power symbols for GND, 3V3, 15V_BOOST, +2V5_BIAS (the PDF draws every net as a plain
  terminal); all other named nets are labels.
- KiCad symbols named after the values (IKP08N65F5, LMV324A, LT1014, ISL21010), not the Proteus
  library devices (finding 9).
- ADC121C027 VA and ADR0 are passive pins (finding 6, FLOATING net); everything else keeps the
  datasheet pin types.
- Device and package columns of the part map come from ROOT.DSN (p2k candidate 3).
- J1 and J2 are drawn with pin 1 at the bottom (mirrored symbol), as in the PDF.
- PWR_FLAGs: 3V3, GND, 15V_BOOST (they enter on J1) and +2V5_BIAS (fed through R74), all on
  sheet 5.
- J1: global labels on short wires, local labels (unused signals) on longer wires, so the
  label texts stay clear of the global label boxes; ADB0-ADB7 only as texts.
- `reports/render/*.png` (sheet renders) are committed, as in tube_psu.
- Sheet 2: the gate-driver cell keeps the PDF's output side; the input side follows the box
  symbol's pin order and uses power symbols instead of the PDF's shared buses. PWR_FLAGs on the
  two bootstrap nodes and on OUT1 / OUT2 (sheet 2).
- No symbol uses the `no_connect` pin type; N/C pads are passive pins with a no-connect flag
  (J1-37 / 38), guarded by `compare_netlists`.
- Sheet 3: U1's supply unit and C12 at the left of the sheet (the PDF draws C12 at U1:A).
- Sheet 1: rails as single wires with junctions only at real nodes; OUT1 / OUT2 global labels on
  the L5 / L11 terminal wires; `BRIDGE+` and `Input_current` only as text notes; no new
  PWR_FLAG on sheets 3 and 1.
- `tools/check_all.sh` runs the full netlist comparison (no `--allow-missing`) from now on.
