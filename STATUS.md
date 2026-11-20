# Status: HV supplies v2 (`hi_voltage_suppliesv2`)

Plan: [PLAN.md](PLAN.md). Playbook: `tools/p2k/CONVERSION_PLAYBOOK.md`.

| Phase | State |
|---|---|
| 0 Skeleton and inventory | **done** 2026-11-20 (Opus 5.5) |
| 1 Schematic | preparation **done** 2026-11-20 (Opus 5.5); transcription: sheets 5, 6, 2 and 4 **done** 2026-11-20 (Fable 5.2), 82/158 parts; next: sheets 3 and 1 (`next_prompt.md`) |
| 2 Footprints | not started |
| 3 PCB | not started |
| 4 Verification | not started |
| 5 Clean-up | not started |

## Phase 1 transcription – in progress

| Sheet | Script | Parts | compare (`--sheet N`) | ERC | Session |
|---|---|---|---|---|---|
| 5 Reference and connector | `tools/sheets/sheet05.py` | 7/7 | 0 missing, 0 extra, 0 wrong-net pins | 0 errors | Fable 5.2, 2026-11-20 |
| 6 ADC | `tools/sheets/sheet06.py` | 15/15 | 0 missing, 0 extra, 0 wrong-net pins | 0 errors | Fable 5.2, 2026-11-20 |
| 2 Gate drivers | `tools/sheets/sheet02.py` | 26/26 | 0 missing, 0 extra, 0 wrong-net pins | 0 errors | Fable 5.2, 2026-11-20 |
| 4 Current measurements | `tools/sheets/sheet04.py` | 34/34 | 0 missing, 0 extra, 0 wrong-net pins | 0 errors | Fable 5.2, 2026-11-20 |
| 3 Voltage measurements | | 0/42 | | | next |
| 1 Power stage | | 0/34 | | | next |

Whole project after sheets 5, 6, 2 and 4: 82/158 parts, 265 pins compared, 0 wrong-net pins, 80
IPC nets touched, 64 complete. Every script was run twice: byte-identical files. Renders in
`reports/render/` (compared with `build/tmp/pdf/hi-N.png`).

**ERC: 0 errors, 29 warnings**:

- 27 `isolated_pin_label` ("label connected to only one pin"):
  - 18 permanent: the local labels of the unused J1 ribbon signals (single-pin nets in the IPC:
    the `*_ISO` signals, PWM_TRANS4 / PWM_TRANS6, DAB_*, ADCLK_DAB).
  - 1 permanent: `FLOATING` on ADC3-K2 (ADR0 left open; single-pin net in the IPC).
  - 8 temporary, the other end is on a sheet not drawn yet: UIN_MEAS, UC3_MEAS, V_A_MEAS,
    U_OUT_MEAS on J1 (sheet 3) and C1_CURRENT, C3_CURRENT, CURRENT_L1, CURRENT_L3 on sheet 4
    (one pin each there; the shunts are on sheet 1). The sheet 2 globals going to sheet 1
    (OUT1, OUT2, PWM1_HI, PWM1_LO, PWM3_HI, PWM3_LO) have two pins on sheet 2 already, so they
    give no warning. The 4 + 4 warnings of G1_HI ... G3_LO and of the `*_CURRENT_MEAS` J1
    globals are gone.
- 2 permanent `ground_pin_not_ground` ("Pin GND2 not connected to ground net"): DRV1-5 and
  DRV5-5. GND2 of a high-side driver is the switch node (OUT1 / OUT2), as in the PDF and the
  IPC; KiCad warns because of the pin name.

Expected at the end of Phase 1: 21 warnings (19 + 2).

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
- Rule for later symbols (sheets 3 and 1 need none): never use the `no_connect` pin type; a
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
- No new design findings came from sheets 2 and 4 (findings 2, 7 and 8 cover them).

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

`tools/check_all.sh`, 2026-11-20 (after sheets 5, 6, 2 and 4):

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
erc: 0 errors, 29 warnings (reports/erc.rpt)
== Netlist comparison vs IPC
compare: parts 82/158 present, 76 missing, 0 extra; pins compared 265, wrong-net pins 0; IPC nets touched 80, complete 64
compare: per sheet (drawn/total) 1:0/34 2:26/26 3:0/42 4:34/34 5:7/7 6:15/15
WARNING: missing parts (76): (see --verbose or --sheet N)
compare: OK

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
6. **ADC121C027 supply and input swapped (all three ADCs, to confirm):** page 6 wires the pin
   labelled VIN (Proteus COM2) to 3V3 and the pin labelled VA (A1) to the filtered analog input
   (R78-R80 2k / C35-C37). The pad geometry puts A1 on SOT-23-6 pin 1 and COM2 on pin 3, and
   the ADC121C027 pinout is 1 = VA (supply and reference), 3 = VIN (analog input), so on the
   built board the input pins sit at 3V3 and the inputs are fed into the supply pins. Unless the
   board was reworked, the ADCs cannot measure as drawn. Reproduced as drawn (the symbol keeps
   the datasheet names; VA is a passive pin so ERC does not flag the input nets). Check
   against the datasheet and the real board; a redesign item.
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

## Decisions

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
