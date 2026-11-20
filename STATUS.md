# Status: HV supplies v2 (`hi_voltage_suppliesv2`)

Plan: [PLAN.md](PLAN.md). Playbook: `tools/p2k/CONVERSION_PLAYBOOK.md`.

| Phase | State |
|---|---|
| 0 Skeleton and inventory | **done** 2026-11-20 (Opus 5.5) |
| 1 Schematic | **done** 2026-11-20 (preparation Opus 5.5; transcription Fable 5.2): 158/158 parts, 0 wrong-net pins, every IPC net complete, ERC 0 errors / 21 explained warnings |
| 2 Footprints | **done** 2026-11-20 (Opus 5.5): 158/158 parts fit the IPC pads, worst residual 0.039 mm (pcbnew placement 0.039 mm); pin order checked (J1 numbering mirrored, finding 12; ADC1-3 finding 6 confirmed) |
| 3 PCB | **done** 2026-11-20 (Opus 5.5, two sessions): board generated, Proteus copper 0 shorts / 0 orphans / 0 opens, check_board OK, make_pcb reproducible; pad sizes option A2 (user): Proteus pads on U1 U2 ADC1-3 DRV5 DRV6 J1, KiCad elsewhere → DRC 0 shorts / 0 clearance / 0 mask bridges / 0 unconnected / 0 parity, copper after zone fill 0 / 0 / 0 |
| 4 Verification | **done** 2026-11-20 (Fable 5.2, fresh session), 1 pending user decision (J2 pads, decided in Phase 5): ipc356_diff OK (574 / 574 records, 113 nets 1:1); gerber round trip: all four layers equal to Proteus outside the pad shapes except one 0.73 mm² GND-plane web at J2 on In2.Cu (KiCad pads on J2), 0 uncovered draws / flashes, drills 247 = 247; PDF re-read vs IPC: no disagreement; both checks in check_all.sh and negative-tested |
| After 5: net rename | **done** 2026-11-20 (Opus 5.5): user decision – `+2V5_BIAS` → `+1V0_BIAS` in the KiCad design through `NET_ALIASES` (finding 1); the Proteus files keep `+2V5_BIAS`; **ALL CHECKS PASSED** (18 steps). HV supplies v2 is not installed and will be redone: this conversion is the starting point for the redesign |
| Design fixes | **done** 2026-11-20 (Opus 5.5): user decisions – finding 7 current-measurement nets renamed to what they measure (8 nets, 4 of them on J1) through `NET_ALIASES`; finding 14 Proteus stubs removed (15V_BOOST stub by `REMOVED_TRACKS`, the two zero-length OUT1 draws by the board-local `tools/remove_dot_tracks.py`); README hole numbering = board H1-H4; make_pcb.sh --check step-failure bug fixed; new name-hint guard; **ALL CHECKS PASSED** (19 steps). Values unchanged |
| 5 Clean-up | **done** 2026-11-20 (Opus 5.5): user decisions applied – Proteus pads on J2 and on the TO-220s Q3 Q4 Q7 Q8 (1.524 × 2.54 rounded rectangle from the gerbers, drill 1.016), J1 / J2 all round, reference texts by `place_refdes`; round trip 0 other / 0 clearance (roundtrip_pending.py removed); new `check_proteus_pads.py`; DRC 0 errors except 20 accepted courtyards (30 violations); **ALL CHECKS PASSED** (18 steps). The board stays generated |

**HV supplies v2 is not installed and will be redone anyway (user, 2026-11-20).** This conversion is
only the starting point for the redesign; the findings below are input for it.

## Shared-tool migration 2026-11-20 – in progress (Opus 5.5, 2026-11-20)

Task: proteus2kicad `docs/CANDIDATES.md` section 7.4 (HV): bump `tools/p2k`, move the board-local tools to
the shared keys, renumber the ribbon header J1 (finding 12, D-PIN). Each commit is proven from a clean
clone with `~/dev/proteus2kicad/tools/regress.sh <pin> tube_hv_supplies_kicad` (PASS).

### Step 1 – bump to p2k a9a286c (+ D-R re-baseline, temporary strict exception)

- `tools/p2k` c5682dd → **a9a286c** (proteus2kicad main; all code is batch Z 2fb1563, later commits docs).
- **D-R** (accepted re-baseline, batch R report texts): `reference/pin_nets_by_component.md` 1 line
  (`Index:` `REF` → `REF1`), `reference/pins_by_net.md` 4 lines (B+, GND, PREOUT, V_A: the two-hole
  terminals B_P, B_N, GND_PRE, GND_PWR, VPRE, V_ANODE listed once; counts 5 → 4, 82 → 79, 5 → 4, 5 → 4).
  `.csv` / `.json` unchanged (p2k candidates 1, 2: solved in p2k a9a286c).
- **D-Z** strict checks on by default; temporary `STRICT_CHECKS_OFF = {"roundtrip_counts": ...}`: B.Cu
  401 KiCad draws vs 403 from gerber_to_tracks, because `tools/remove_dot_tracks.py` removes the two OUT1
  dot draws after gerber_to_tracks. Removed in step 2 (D-I7).
- Every other generated file byte-identical; `tools/check_all.sh` ALL CHECKS PASSED.

### Step 2 – migration to the shared tools (D-I7 re-baseline)

Every board-local tool deleted or reduced to data, each with the shared tool / key that replaces it:

| Board-local (deleted / changed) | Shared replacement (p2k a9a286c) |
|---|---|
| `tools/make_part_map.py` (generator, `dsn_devices()`) | data only, `part_map.run(SPEC)`: `LAYOUT="dsn"`, `"LT1014": None` + `SYMBOL_BY_VALUE`, `OFF_BOARD` 2-tuples, `FIELDS` with `off_board`, `COMMENT` |
| `_common.place_mirrored` | `Sheet.place(..., 0, mirror="x")` (J1, J2) |
| `_common.term()` | `sheetkit.terminal(..., symbol=sym(ref), value=sh_value(ref), justify="away")` (10 terminals, sheet 1) |
| `_common._hcap()`, the `si8271_cell` capacitor texts | `horiz2(..., text_gap=3.81)` |
| `tools/erc.sh` | `p2k erc` (no keys) |
| check_all grep guard `WARNING: name hint` | strict `net_names` (on by default) |
| gen_footprints `fp_lib_table()` | `FP_LIB_TABLE = True` |
| gen_footprints `_derive_pads` (monkeypatch) | spec key `pads` (same semantics). The hand-written `_ProteusPads` specs stay (F8 `PROTEUS_PADS` would not reproduce their names); `PROTEUS_PADS` stays a module variable of gen_footprints.py, not the config key |
| `tools/check_pin_order.py` | `p2k check_pin_order` + `PIN_ORDER` (13 entries, `spec=`, two `mirror=None`) |
| `tools/check_proteus_pads.py` | `kipy -m p2k.check_pads` + `PROTEUS_PADS_CHECK` (its `DECIDED` list) |
| `tools/remove_dot_tracks.py` + `REMOVED_DOT_TRACKS` + make_pcb step 2b | `REMOVED_TRACKS[("B.Cu", -32.85196, -11.53736, -32.85196, -11.53737)] = ("OUT1: …", 2)` |
| `tools/make_pcb.sh` (35 lines) | one-liner `exec tools/p2k/bin/p2k make_pcb "$@"` (default `PCB_STEPS`) |
| `tools/measure_gaps.py` | `tools/p2k/bin/kipy -m p2k.measure_gaps` |

`STRICT_CHECKS_OFF` removed: **no strict opt-outs** (B.Cu 401 / 401 draws, `roundtrip_counts` passes).

Generated files: all byte-identical except the **D-I7** accepted re-baseline (user decision, p2k
CANDIDATES.md "Decisions"): `kicad/tube_hv_supplies.kicad_pcb` (item order / UUIDs: 1256 lines changed;
sorted without the UUIDs identical, i.e. the same copper), `reports/assign_nets.txt` (the order of the 36
stage-A orphan via lines only), `reports/roundtrip/roundtrip.txt` (2 lines: "3 Conductor draws
(REMOVED_TRACKS)" on B.Cu, Proteus 874 draws instead of 876 - the dot draws are now recorded deviations on
both sides).

Negative tests (in place, restored): ADC renumbering with A1 / COM2 exchanged → `check_pin_order: ERROR ADC:
unmirrored 1.909, expected unmirrored <= 0.19`; J1 without the rows-swapped renumbering → `ERROR J1 rows
swapped: mirrored 0.000, expected unmirrored <= 0.01`; the OUT1 entry with count 1 → `gerber_to_tracks: ERROR
REMOVED_TRACKS: 2 listed, found 3 draws`, make_pcb FAILED at gerber_to_tracks; C1 (KiCad pads) added to
`PROTEUS_PADS_CHECK` → check_pads FAILED (10); the `C1_CURRENT_MEAS` alias dropped → `ERROR: net name: KiCad
net CURRENT_C3_MEAS = IPC net C1_CURRENT_MEAS (… strict check net_names)`.

## Design fixes 2026-11-20 – findings 7 and 14, README holes – done (Opus 5.5, 2026-11-20)

User decisions (Decisions, first entry): fix design findings in the KiCad design but leave every
component **value** as it is (HV supplies v2 is not installed; it is the redesign's starting point);
finding 7: rename the current-measurement nets to what they measure (`NET_ALIASES`); finding 14:
remove the Proteus stubs; README hole numbering = board refdes. Not now: finding 6 (ADC VA / VIN, a
hand edit after generation stops) and finding 12 (J1 renumbering, waits for a shared-tool key).
Everything in the generators; `tools/p2k` untouched (pin c5682dd).

### Finding 7 – the current-measurement nets (`p2k_config.NET_ALIASES`)

The circuit (sheet 1 / 4, IPC): bridge 1 = Q3 (UIN → OUT1) / Q4 (OUT1 → emitter shunt R72 4 m → GND),
OUT1 → off-board L1 3 mH → UC3; C3 47u from UC3 returns to GND through the shunt R75 4 m; UC3 → L2 →
V_A (C4). Bridge 2 = Q8 / Q7 (emitter shunt R29), OUT2 → off-board L3 → U_OUT (C5 straight to GND) →
L4 → UC6; C6 47u from UC6 returns through the shunt R30; UC6 → R26 || R27 → PREOUT. U2:A..D (LT1014)
amplify the four shunt voltages (330 R in, 6.8 k to +1V0_BIAS / feedback, 100 R / 100 p out) to J1.
There is no input-current shunt (the page 1 `Input_current` terminal is on GND; a text note only).

| Proteus / IPC name | KiCad name | sense path | what it measures |
|---|---|---|---|
| `C1_CURRENT` | **`CURRENT_C3`** | R75 under C3 | the current of C3, bridge 1's output capacitor (UC3); the old name used no refdes that fits (C1 is the B+ input capacitor) |
| `C3_CURRENT` | **`CURRENT_C6`** | R30 under C6 | the current of C6, the second-stage capacitor of bridge 2 (UC6); C3 is the bridge 1 capacitor |
| `CURRENT_L1` | **`CURRENT_Q4`** | R72 in the Q4 emitter | the current of the low-side switch Q4 (IGBT + its copack diode): the L1 current, with a negative sign while the low side conducts, 0 while Q3 conducts; not the L1 current at all times |
| `CURRENT_L3` | **`CURRENT_Q7`** | R29 in the Q7 emitter | the same for Q7 / L3 (bridge 2 low side) |
| `INPUT_CURRENT_MEAS` (J1-5) | **`CURRENT_C6_MEAS`** | U2:A output | amplified `CURRENT_C6`; not an input current |
| `C1_CURRENT_MEAS` (J1-7) | **`CURRENT_C3_MEAS`** | U2:B output | amplified `CURRENT_C3` |
| `C2_CURRENT_MEAS` (J1-1) | **`CURRENT_Q4_MEAS`** | U2:C output | amplified `CURRENT_Q4`; not a capacitor current |
| `C3_CURRENT_MEAS` (J1-3) | **`CURRENT_Q7_MEAS`** | U2:D output | amplified `CURRENT_Q7`; not a capacitor current |

Style: `CURRENT_<refdes>` as the Proteus `CURRENT_L1`, `_MEAS` for the amplified signal on J1 as
`UIN_MEAS` / `UC3_MEAS`. The `<refdes>_CURRENT` form (`C3_CURRENT`, `C3_CURRENT_MEAS`) can't be used:
`ipc356 --check` rejects an alias target that is an IPC net name, even when that IPC net is renamed
itself. `CURRENT_Q4` / `CURRENT_Q7` name the switch, not the inductor, because the emitter shunt only
sees the inductor current during the low-side interval (the firmware samples it there);
`CURRENT_L1` / `CURRENT_L3` would be the alternative if the user prefers the inductor in the name.
**Four renamed nets cross the J1 ribbon to the control card: J1-1 `CURRENT_Q4_MEAS`, J1-3
`CURRENT_Q7_MEAS`, J1-5 `CURRENT_C6_MEAS`, J1-7 `CURRENT_C3_MEAS`** (PDF aliases ADB0 / ADB1 / ADB2 /
ADB3); the control-card repo is not touched (its names / firmware mapping are its own question).
Pins and copper are unchanged: every renamed net has the same pins and vias as its IPC net.

Changed: `p2k_config.py` (NET_ALIASES), `tools/sheets/sheet01.py` / `sheet04.py` / `sheet05.py`
(labels and notes; the sheet 1 notes moved down 3 grid units clear of the `CURRENT_C3` label);
regenerated `reference/*`, sheets 1 / 4 / 5, the board, `reports/pour_nets.json`,
`reports/roundtrip/roundtrip.txt`, renders of sheets 1 / 4 / 5.

**New guard** (check_all.sh, after the netlist comparison): "KiCad net names = IPC names after
NET_ALIASES" fails on any `WARNING: name hint` of compare_netlists. These nets are labels, not power
symbols, so check_symbols does not see them (as it did for `+1V0_BIAS`), and compare_netlists only
warns (p2k candidate 27): without the guard a dropped or typo'd alias passed every check once
`reference/` was regenerated (negative tests below).

### Finding 14 – the Proteus stubs removed

- **15V_BOOST stub** (B.Cu, (-73.6, -20.2) → (-72.7, -20.2) IPC, 0.762 mm wide, dangling): `REMOVED_TRACKS`
  in `p2k_config.py` (the p2k key; gerber_to_tracks drops it, the round trip lists it as "1 Conductor draws
  (REMOVED_TRACKS)").
- **The two zero-length OUT1 draws** (B.Cu, (-32.85196, -11.53736) ↔ (-32.85196, -11.53737), 1e-5 mm): one
  segment drawn twice, in opposite directions. `REMOVED_TRACKS` can't express them: matching is
  direction-free with 0.001 mm tolerance, so one key matches both draws and gerber_to_tracks fails with
  "REMOVED_TRACKS: 2 listed, found 3 draws" (duplicate match), and no second key can tell them apart.
  Board-local instead (PLAN 5.1): `p2k_config.REMOVED_DOT_TRACKS = {(layer, x, y): (count, reason)}` and
  `tools/remove_dot_tracks.py`, make_pcb.sh step 2b after gerber_to_tracks: deletes exactly `count` tracks
  shorter than 0.001 mm at that point, fails (nothing saved) on any other count. The dot lies inside the
  junction of two 0.762 mm OUT1 tracks, so the copper is unchanged (round trip clean without a recorded
  deviation). p2k candidate 28.
- Result: DRC 28 violations (was 30): the two `track_dangling` warnings are gone; 20 accepted
  courtyards_overlap errors, 5 silk_overlap / 3 silk_over_copper warnings. gerber_to_tracks 1838 tracks
  (was 1839 with the stub; 1836 on the board after the dots).

### make_pcb.sh --check ignored failing steps (fixed)

`run >"$tmp/log" 2>&1 || {...}` disables `set -e` inside `run()`, so in `--check` mode a failing step
(e.g. a gerber_to_tracks `REMOVED_TRACKS` error) was skipped, its ERROR line filtered out, and the check
failed only as "not up to date" - or passed, when the board came out equal anyway (seen in this session:
the duplicate-match error above passed through as "not up to date"). The steps in `run()` are now chained
with `&&` (as the preamp b2adf22 / PI-FX da551f3 fixes). Negative test below: a bogus entry now prints the
step's ERROR and `make_pcb: FAILED`.

### README

"Mechanical baseline": the holes are numbered as the board refdes (H1 (4.49, 51.755), H2 (165.49, 51.755),
H3 (4.49, 4.755), H4 (165.49, 4.755)); the old list's H2 / H3 / H4 were board H3 / H4 / H2 (positions
unchanged). Note: tube_amplifier_kicad `mechanical/hv_supplies_v2.kicad_pcb` may follow the old README
numbering (not checked, other repo).

### Negative tests (in place, restored with `git checkout`; full `tools/check_all.sh` each)

| change | result |
|---|---|
| alias `C1_CURRENT_MEAS` removed | `ipc356 --check` FAIL (reference/ stale) |
| … and `p2k ipc356` rerun | **new guard** FAIL "name hint: KiCad net CURRENT_C3_MEAS = IPC net C1_CURRENT_MEAS"; everything else passes (pin-based) - without the guard ALL CHECKS PASSED |
| source typo `CURRENT_L01` | `ipc356 --check` FAIL "alias source net 'CURRENT_L01' not in IPC" |
| target typo `CURRENT_Q04` + `p2k ipc356` | new guard FAIL "KiCad net CURRENT_Q4 = IPC net CURRENT_Q04" (without the guard: passed) |
| target collides (`C3_CURRENT` → `C1_CURRENT`) | `ipc356 --check` FAIL "alias target 'C1_CURRENT' collides" |
| KiCad typo on one sheet (`CURRENT_Q4_MAES` on sheet 4) | compare_netlists FAIL (1 wrong-net pin), make_pcb --check, drc FAIL |
| KiCad rename on both sheets (`CURRENT_L1_MEAS` on sheets 4 and 5) | new guard FAIL (name hint), make_pcb --check not up to date, drc 3 parity issues |
| `REMOVED_TRACKS` entry removed | make_pcb --check FAIL (board and assign_nets.txt not up to date) |
| bogus `REMOVED_TRACKS` entry (x2 -72.6) | make_pcb --check prints "gerber_to_tracks: ERROR REMOVED_TRACKS: 1 listed, found 0 draws (missing …)", "make_pcb: FAILED" |
| `REMOVED_DOT_TRACKS` entry removed | make_pcb --check FAIL (not up to date) |
| `REMOVED_DOT_TRACKS` count 1 | "remove_dot_tracks: ERROR … 2 zero-length tracks, expected 1", make_pcb FAILED |
| OUT1 dot as a `REMOVED_TRACKS` key instead | "gerber_to_tracks: ERROR REMOVED_TRACKS: 2 listed, found 3 draws", make_pcb FAILED |

(The last six were run while the new guard step still matched its own header line "no name hints" and
failed every run; that is fixed - the guard now greps `WARNING: name hint` - and their make_pcb results
are unaffected. The guard tests and "entry removed" were rerun with the fixed guard: only the listed
steps fail.)

End state: **ALL CHECKS PASSED, 19 steps** ("Last check output").

## After Phase 5 – `+2V5_BIAS` renamed to `+1V0_BIAS` – done (Opus 5.5, 2026-11-20)

User decision (finding 1). The circuit checked again: REF1 is `ISL21010CFH315Z-TK` (part map, PDF
page 5), the 1.5 V version (ISL21010 ordering code `-15`). Its output (net #00194) feeds R74 220 R to the
rail, R73 470 R to GND: 1.5 × 470 / 690 = **1.02 V** unloaded. The rail also feeds the four 6.8 k bias
resistors R54 R59 R64 R69 (each 6.8 k + 330 R to a shunt at about 0 V, about 1.8 k together), which pull
it to about 0.94 V. `+1V0_BIAS` (the coordinating session's name) fits; no other value is clearly better.

Mechanism: the existing p2k key **`NET_ALIASES = {"+2V5_BIAS": "+1V0_BIAS"}`** in `p2k_config.py`
(as `GND=POWER` → `GND` on other boards). `p2k ipc356` applies it when it parses the IPC, so the
reference files (`reference/*`, `net_raw` keeps `+2V5_BIAS`) and every check that reads the IPC nets
see `+1V0_BIAS`: check_symbols (power symbol name must be an IPC net name), compare_netlists,
check_board, assign_nets, gerber_roundtrip (labels). ipc356_diff and DRC parity match nets by pad sets
(names are not compared). `ipc356 --check` fails if the alias source is not in the IPC, if the target
collides with an IPC net, or if reference/ is stale. No board-local mapping was needed.

Changed: `p2k_config.py` (NET_ALIASES), `tools/gen_symbols.py` (SUPPLIES), `tools/sheets/_common.py`
(bias default), `tools/sheets/sheet04.py` / `sheet05.py`; regenerated `reference/*`,
`lib/tube_hv_supplies.kicad_sym`, sheets 4 and 5 (diff = the name only), the board (`tools/make_pcb.sh`;
diff = the net name only), `reports/roundtrip/roundtrip.txt`, renders of sheets 4 and 5. Net
`+1V0_BIAS` has the same 11 pins as IPC `+2V5_BIAS` (C22-1 C44-1 C45-1 C47-1 C48-1 R54-2 R59-2 R64-2
R69-2 R73-1 R74-2) and 3 vias in every check.

Negative tests (in place, restored with `git checkout`):

| change | result |
|---|---|
| `NET_ALIASES = {}` | `ipc356 --check` FAIL (reference/ stale); after `p2k ipc356`: `check_symbols` FAIL "power symbol +1V0_BIAS is not an IPC net name"; compare_netlists only warns ("name hint: KiCad net +1V0_BIAS = IPC net +2V5_BIAS", p2k candidate 27); check_board, assign_nets, drc, ipc356_diff, round trip pass (pin-based) |
| source typo `{"+2V5_BIA": ...}` | `ipc356 --check` FAIL "alias source net '+2V5_BIA' not in IPC" |
| target typo `{...: "+1V0_BAIS"}` | `ipc356 --check` FAIL (stale); after regenerating: `check_symbols` FAIL "power symbol +1V0_BIAS is not an IPC net name" |
| target collides `{...: "3V3"}` | `ipc356 --check` FAIL "alias target '3V3' collides", "net names not unique after aliasing" |
| KiCad side typo `+1V0_BIA` in gen_symbols SUPPLIES | `gen_symbols --check` FAIL (out of date); after regenerating: `check_symbols` FAIL "power symbol +1V0_BIA is not an IPC net name" |

## Phase 5 – clean-up – done (Opus 5.5, 2026-11-20)

User decisions first (2026-11-20, through the coordinating session; Decisions): J2 Proteus pads;
TO-220 Q3 Q4 Q7 Q8 the Proteus pad as in the gerbers with the Proteus drill; J1 all pads round;
reference texts placed by `p2k.place_refdes`; the dangling Proteus stubs kept; body graphics, sheet
names and 1.6 mm kept; the board stays generated; the `_ProteusPads` names kept. Everything is in the
generators (nothing by hand in `kicad/` or `lib/`); `tools/p2k` untouched (pin c5682dd).

Start state: `tools/check_all.sh` printed "ALL CHECKS PASSED, EXCEPT 1 PENDING USER DECISION(S)" (17
steps, the J2 cluster). End state: **ALL CHECKS PASSED, 18 steps** ("Last check output").

### Pad changes (`tools/gen_footprints.py`)

- `PROTEUS_PADS` = U1 U2 ADC1-3 DRV5 DRV6 J1 **+ J2 + Q3 Q4 Q7 Q8** (13 parts); new `refdes=` rules for
  `IKP08N65F5` and `HEADER_2X8_50MIL` (the general TO-220 / 2x8 rules dropped: every such part is in the
  set). 23 footprints, 15 project (two new).
- **J2** → `tube_hv_supplies:PinHeader_2x08_P1.27mm_Vertical_ProteusPads` (`ipc_sizes=True`: 0.762 mm,
  Proteus drill 0.558 instead of 1.0 / 0.65). **Pad 1 round too** (agent, with decision 3's reasoning:
  "Proteus pads" = round as in Proteus; KiCad's square pad 1 left 4 corner clusters of 0.019 mm² per layer
  in the round trip and a square clearance hole in the In2.Cu plane; one line `pads={"1": …}` to undo).
- **Q3 Q4 Q7 Q8** → `tube_hv_supplies:TO-220-3_Vertical_ProteusPads`: KiCad's TO-220-3_Vertical with all
  three pads `roundrect` **1.524 × 2.54 mm, rratio 0.2** (corner radius 0.3048 mm) and **drill 1.016**.
  Taken from the gerber aperture macro `PPAD010` (outline ±0.762 × ±1.27 with 0.3048 mm corner arcs),
  which is flashed unrotated on all 12 TO-220 pads on all four copper layers (checked per pad and layer):
  the 1.524 mm side lies along the pin row, the 2.54 mm long axis across it, on all four parts (Q3 Q4 at
  180°, Q7 Q8 at 0°: symmetric pads, same orientation on the board). On the board (pcbnew): every pad
  1.524 × 2.540 mm, drill 1.016, **gap between neighbouring pads 2.54 − 1.524 = 1.016 mm** (KiCad pads
  0.635 mm). Not `ipc_sizes` (the IPC says 1.524 × 1.524, finding 15).
- **J1** pad 2 (KiCad's square pin-1 pad after the odd / even swap) → `circle`: all 40 pads round, as in
  Proteus. KiCad's silk pin-1 corner mark of the base footprint still sits at the pad numbered 2
  (cosmetic, finding 12 stays a redesign question).
- The pad shape / size / drill overrides are a board-local spec key `pads` = {pad number or `*`:
  dict(shape, size, rratio, drill)} applied after `p2k.footprints.derive` (a wrapper set in
  gen_footprints.py; p2k candidates 21 / 23 / 25). It fails if it names a pad the footprint lacks.
- Sheets 1 and 6 re-run (Footprint fields of Q3 Q4 Q7 Q8 and J2 only); `tools/check_pin_order.py` reads
  the J2 and TO-220 rows from the new specs (same results).

### Reference texts (`tools/make_pcb.sh` step 5: `p2k.place_refdes`, as tube_power_amp)

`REFDES_PLACEMENT` defaults (sizes 1.0 / 0.8 mm). 158 references: 92 kept, 64 moved, 2 at 0.8 mm (R12,
R66), **4 on the Fab layer only** (R52 R54 R69 R74: no clear place on the silk among the 0402s).
make_pcb --check compares the board byte for byte with this step included.

### Verification after the changes

| Check | Result |
|---|---|
| gen_footprints --check, sheets, compare_netlists, ERC | up to date; 158/158, 0 wrong-net pins; ERC 0 / 21 |
| check_footprints --pcbnew | 158/158, 429 pads, 23 footprints, worst 0.039 mm |
| check_pin_order | OK (TO-220 and J2 rows from the `_ProteusPads` specs) |
| make_pcb --check | byte-identical (1839 tracks, 141 vias, 21 zones; stage B 119 / 0 / 0 / 0) |
| check_board | OK (429 pads, 113 nets 1:1) |
| copper after zone fill | 119 groups, 0 shorts / 0 orphans / 0 opens / 0 foreign |
| DRC | **0 errors except 20 accepted courtyards_overlap**; warnings: silk_overlap 5, silk_over_copper 3, track_dangling 2 (before: 111 / 90 / 3 silk_edge / 2; the 226 violations of Phase 4 are now 30) |
| ipc356_diff | OK, 574 / 574, 113 nets 1:1; larger KiCad drills only 18 × 0.812 → 1.0 (C1-C7 C11 C26); the J2 and TO-220 drills are now the Proteus drills. "Pads with another size: Q 12" stays as info: the IPC records the TO-220 pads as 1.524 square |
| gerber_roundtrip --check | **OK: 0 other, 0 clearance**, 0 uncovered draws / flashes, 0 drill mismatches; pad-shape clusters F 224 / In1 18 / In2 18 / B 139 (was 268 / 78 / 67 / 206), **none at a Proteus-pad part** (In1 / In2: only the CP_Radial C1-C7 C11 C26 pads) |
| **check_proteus_pads** (new) | OK: 13 parts, 130 pads, 334 pad-layers = the Proteus flashes, drills equal |

Remaining DRC warnings: silk_overlap R58/U2, R79/J2, C6/L4, R74/REF1 (×2) and silk_over_copper U2 silk
over R58's pads (×3): KiCad footprint body silk on the Proteus placement (body graphics kept, user
decision); track_dangling: the two Proteus stubs (finding 14, kept as drawn, user decision).

### New check `tools/check_proteus_pads.py` (in check_all.sh after the round trip)

The negative tests showed that **reverting the TO-220 pads or drills or the J1 round pad passes every
other check**: the round trip classifies a different pad as `pad shape`, ipc356_diff accepts larger
KiCad drills, DRC is clean at 0.12 mm. So a board-local guard compares, for the 13 decided parts (list
written in the check, independent of `PROTEUS_PADS`), every board pad on every copper layer with the
Proteus gerber flash at its position (pcbnew polygon bounding box ±0.01 mm, area ±6 %: the A2 SMD pads
keep KiCad's rounded corners, up to 4.6 % less than the Proteus rectangle; a square pad on a round
flash is +27 %) and every THT drill with the Proteus drill gerber (±0.005 mm).

### Negative tests (scratch copies `build/tmp/neg_*` with `P2K_BOARD`, full rebuild: gen_footprints, sheets, check_footprints, make_pcb; deleted)

| Revert | gen_footprints | check_proteus_pads | DRC | ipc356_diff | gerber round trip |
|---|---|---|---|---|---|
| J2 back to the KiCad header (rule + `PROTEUS_PADS`) | exit 1 (spec unused) | **FAILED** (80: 0.991 mm pads, drill 0.65) | OK | OK (16 × 0.558 → 0.65 larger) | **FAILED**: the In2.Cu `other` 0.734 mm² at (-119.726, -13.557) again, 7 clearance |
| Q3 Q4 Q7 Q8 back to KiCad's TO-220 | exit 1 (spec unused) | **FAILED** (60: 1.905 × 1.991, drill 1.1) | OK | OK (12 × 1.016 → 1.1 larger) | OK (pad shape only) |
| TO-220 long axis turned (2.54 × 1.524) | OK | **FAILED** (48) | **FAILED: 32 shorts** (pads touch at 2.54 pitch) | OK | OK (pad shape only) |
| TO-220 drill 1.1 (pads kept) | OK | **FAILED** (12 drills) | OK | OK | OK |
| J1 pad 2 square again | OK | **FAILED** (4 layers of J1-2) | OK | OK | OK (4 more pad-shape corners) |

## Phase 4 – independent verification – done, 1 pending user decision (decided in Phase 5) (Fable 5.2, 2026-11-20, fresh session)

The reviewer did not build the board. Verified state first: `tools/check_all.sh` printed the Phase 3
handoff output (15 steps, ALL CHECKS PASSED; compare 158/158, 0 wrong-net pins; ERC 0 / 21; worst fit
0.039 mm; make_pcb byte-identical; copper after zone fill 119 / 0 / 0 / 0; DRC OK). Then the two
Phase 4 checks were run, added to `tools/check_all.sh` (17 steps) and negative-tested, the PDF was read
again independently against the IPC, and the generating scripts and every earlier finding reviewed.
`tools/p2k` untouched (pin c5682dd); no config key was needed (`STACKED_VIAS` 0, no `DRILL_SMALLER`,
no `DRILL_EXCELLON`, `ROUNDTRIP` at the defaults, as tube_psu).

**Result: the KiCad board is the Proteus board** (pads, vias, holes, nets, drills, tracks, pours on all
four layers) **except one 0.73 mm² piece of GND plane between four J2 pins on In2.Cu**, which the zone
fill drops because J2 has the larger KiCad pads. It connects nothing. Fixing it means Proteus pads on
J2, which changes the pad decision A2 → **pending user decision** ("Phase 4 – J2" below).

### IPC-D-356 diff (`p2k ipc356_diff`, ≈ 5 s): OK

Proteus 574 records, KiCad 574, **all 574 matched**: 429 pads (2 N/C: J1-37, J1-38), 141 vias, 4 holes;
worst position offset 0.040 mm (limit 0.05); side, THT / SMD and plating equal everywhere; **113 Proteus
nets ↔ 113 KiCad nets 1:1, 0 mismatches**; no stacked via records. Differences, all explained:

- KiCad drill larger (KiCad library footprint kept): 16 × 0.558 → 0.65 (J2), 18 × 0.812 → 1.0 (C1-C7 C11
  C26; KiCad's file writes 1.001, 0.0001 inch units), 12 × 1.016 → 1.1 (Q3 Q4 Q7 Q8). **No KiCad drill is
  smaller.**
- Pads with another size than the IPC (info): C 96 (all 48 capacitors), D 4, DRV 16 (DRV1 DRV2), J 16
  (J2), L 6, Q 12, R 150 (75 resistors: all but the four KRL2012 shunts), REF 3: every part outside
  `PROTEUS_PADS`, the IPC-built terminals and the shunts, as the Phase 2 pad table says. The eight
  `PROTEUS_PADS` parts (U1 U2 ADC1-3 DRV5 DRV6 J1) are not in the list: their pads are the IPC size.

### Gerber round trip (`p2k gerber_roundtrip --check`, ≈ 16 s, `reports/roundtrip/`)

| Layer | Proteus Cu | KiCad Cu | raw XOR | only Proteus > 0.05 | only KiCad > 0.05 | clusters ≥ 0.01 mm² | uncovered draws / flashes |
|---|---|---|---|---|---|---|---|
| F.Cu | 4040.7 mm² | 4069.0 mm² | 58.43 mm² | 6.29 mm² | 25.74 mm² | 268 pad shape | 0 / 0 |
| In1.Cu | 726.6 | 759.0 | 51.84 | 8.02 | 34.68 | 78 pad shape | 0 / 0 |
| In2.Cu | 1951.9 | 1975.3 | 56.90 | 11.20 | 31.71 | 67 pad shape, 7 clearance, **1 other** | 0 / 0 (132 Proteus pour-edge strokes explained) |
| B.Cu | 1787.9 | 1833.3 | 72.68 | 9.27 | 43.24 | 206 pad shape | 0 / 0 |

Outside the pad shapes and the J2 corner of In2.Cu, the KiCad copper (1839 tracks, 141 vias, the 21
filled zones with their 259 clearance / thermal holes and the Proteus spoke tracks) is the Proteus
copper to within 0.05 mm on all four layers, and the centre line of every Proteus draw (5746) and flash
(1315) lies on KiCad copper and vice versa. No `zone fill` cluster (no Proteus copper thinner than the
0.15 mm zone minimum width).

- **pad shape** (619 clusters; KiCad pad larger / another shape than Proteus; per footprint in
  `reports/roundtrip/roundtrip.txt`): CP_Radial_D10 C1-C7 C11 C26 (2.0 vs 1.524 round, pad 1 a rounded
  square: 22.6–27.6 mm² only KiCad on In1 / In2 / B), R_1206 HandSolder (18.5 F / 5.9 B), TO-220 Q3 Q4 Q7 Q8
  (both ways, see "Review" 1), J2 (1.0 vs 0.762, pad 1 square: 3.3–3.6 per layer), C_1206 HandSolder 4.4,
  DRV1 DRV2 SOIC-8 1.7, D_SMA 1.2, REF1 SOT-23 (both ways, 0.5), C_0603 HandSolder 0.3; only Proteus
  (KiCad pad smaller): R_0402 1.3, C_0603 0.5 + 0.4, R_0603 0.5, R_1206 (R21 R31) 0.1, C_0402 0.03;
  J1: 3–4 corners of 0.018 mm² per layer at the pad numbered 2 (KiCad's square pin-1 pad, "Review" 3).
  No pad-shape cluster at U1 U2 ADC1-3 DRV5 DRV6 and none at the terminals, shunts or mounting holes:
  those pads are the Proteus pads.
- **clearance** (7 clusters, 0.26 mm², all on In2.Cu at J2): the GND plane pulled back 0.12 mm from J2's
  larger KiCad pads (pins 2, 4, 7, 8, 11, 12). The 132 "explained" Proteus strokes are the pour-edge
  strokes of the clearance holes of J2's eight non-GND pins (124) and of J1-2 (8: KiCad's square pad).
- **other, 1 cluster: In2.Cu, only Proteus, 0.734 mm² at (-119.726, -13.557)** – "Phase 4 – J2".

Drills: plated **Proteus 247 = KiCad 247**, 0 mismatches (139 × 0.3 and 2 × 0.381 vias, 40 × 0.5588 →
0.558 J1, 12 × 1.4, 4 × 1.524, 4 × 3.0 equal; larger KiCad drills 16 × 0.5588 → 0.65, 18 × 0.8128 → 1.0,
12 × 1.016 → 1.1, as in the IPC diff); no non-plated file on either side.

### Phase 4 – J2 (DECIDED in Phase 5, user: Proteus pads on J2; the cluster is gone)

On In2.Cu (the GND plane) Proteus leaves a web of copper between the clearance holes of the four pins
J2-1, J2-2 (3V3), J2-3, J2-4 (#00206, the R80 / ADC3 input). J2 kept the KiCad pads in decision A2
(1.0 mm, pad 1 square; Proteus 0.762 mm round), so KiCad's clearance holes are 0.24 mm wider: the necks
between neighbouring holes close (1.27 mm pitch − 1.0 − 2 × 0.12 = 0.03 mm, under the 0.15 mm zone
minimum width), the web in the middle of the four pins becomes an island and the zone fill drops it
(0.734 mm² with the rings around the four holes). **Nothing connects there**: no pad or via of GND is
inside, the copper check after zone fill has 0 opens, DRC is clean. This is the case the playbook
warns of ("a larger KiCad pad can also make the zone fill drop Proteus copper without any DRC error");
the Phase 3 DRC could not see it.

- Tested on a scratch copy (deleted): **J2 added to `PROTEUS_PADS`** (rule
  `("HEADER_2X8_50MIL", dict(refdes=PROTEUS_PADS), P + "PinHeader_2x08_P1.27mm_Vertical_ProteusPads", …)`
  and a spec `base=…PinHeader_2x08_P1.27mm_Vertical, ipc="J2", ipc_sizes=True`; gen_footprints, the six
  sheets, check_footprints, make_pcb) → `gerber_roundtrip`: **OK, 0 other, 0 clearance** clusters on all
  layers; ipc356_diff OK (the 16 × 0.558 → 0.65 drills are gone: J2 gets the Proteus drill); copper 119 /
  0 / 0 / 0; DRC unchanged (226 violations, 20 accepted courtyards). This is J2 of the Phase 3 option B.
- Until the user decided (Phase 5; wrapper then removed), **`tools/roundtrip_pending.py`** (after the Phase 3 `drc_pending.py`) runs
  `p2k gerber_roundtrip --check` and passes exactly this cluster (In2.Cu, only Proteus, within 0.1 mm of
  the recorded position, area 0.734 ± 0.05 mm², nearest pad of J2, 0 uncovered draws / flashes, 0 drill
  mismatches) as `PENDING USER DECISION`; anything else fails. `tools/check_all.sh` then prints
  "ALL CHECKS PASSED, EXCEPT 1 PENDING USER DECISION(S)". After the decision: J2 into `PROTEUS_PADS` (or
  the cluster accepted for good), remove the wrapper, check_all runs `p2k gerber_roundtrip --check`.

### PDF read again, independently of the sheet scripts (all six pages, every pin)

Each page of `source/schematic_pdf/hi_voltage_suppliesv2.PDF` (200 / 300 dpi renders) was read wire by
wire into a pin → net list without looking at the KiCad sheets and compared with
`reference/ipc356_pads.json`: **no disagreement on any page.**

- Page 6 (ADC), every pin: J2 1 / 2 3V3, 3 / 4 → R80, 5 / 6 GND, 7 / 8 → R79, 9 / 10 GND, 11 / 12 → R78,
  13-16 GND (the wires of 11, 7 and 3 loop around the header to the junction of their even neighbour);
  ADC1-3 COM2 (VIN) on 3V3, A1 (VA) on R78 / C35, R79 / C36, R80 / C37, A2 GND, K1 on the scl column,
  COM1 on the sda column, K2 (ADR0) 3V3 / GND / `floating`; R76 3V3–scl, R77 3V3–sda; C27-C29 3V3–GND.
- Page 5, all 40 J1 pins with the ADB0-ADB7 alias table (1 C2_current_meas, 2 V_A_meas, 3 C3_current_meas,
  4 Uin_meas, 5 input_current_meas, 6 Uc3_meas, 7 C1_current_meas, 8 U_out_meas; 37 / 38 stubs without a
  terminal), REF1 with C8, C21, R74, R73, C22.
- Page 2, the four SI8271 cells: all 8 pins of each driver, D18 / D2, R21 / R31, the bootstrap capacitors
  C46 / C30 (VDD2 to GND2 = OUT1 / OUT2), C23 / C31, C38 / C43, C24 C25 C32 C33; 15R on OUT+ and 8R on
  OUT− of every driver (R23 R25 R32 R35 are the 8R resistors, printed below their symbols); the G1_HI /
  G3_HI wires cross the 15V and 3V3 columns without a junction.
- Pages 3 and 4, all four amplifier cells each (dividers, feedback, input and output networks, supply
  pins 4 / 11, C12, C34); page 1, every part (rails, both half-bridges, the L5 / L12 / L11 / L6 terminal
  wires, C3 / C6 returning through R75 / R30, R26 ∥ R27, `Input_current` on the GND rail).
- Values of all 160 parts in the KiCad sheets = `lib/part_map.csv` = the values read from the PDF.

Independent of `compare_netlists`, a pcbnew script (scratch) compared the net of every board pad with
the IPC: 429 pads, 113 nets 1:1, 0 mismatches, N/C pads on `unconnected-(…)`, worst offset 0.039 mm.

### Review of the generators and the easy-to-get-wrong places

Read: `p2k_config.py`, `tools/gen_footprints.py`, `tools/make_pcb.sh`, `tools/check_all.sh`,
`tools/erc.sh`, the sheet scripts (no exclusions besides `L_OFFBOARD`; the only no-connect flags are
J1-37 / 38; no `no_connect` pin type anywhere). Board spot-checks (pcbnew, scratch script):

- **Thermal reliefs**: all 21 zones have solid pad connection (clearance 0.12, min width 0.15); the
  Proteus thermals are its clear holes + spoke tracks, reproduced (round trip: every Proteus draw
  covered). Negative test: thermal reliefs on the In2.Cu zone → 16 uncovered spokes / many clusters.
- **Non-conductor graphics**: none on the Proteus copper layers (check_sources lists only Conductor
  and Profile draws); the board has 0 graphics on copper layers and 0 tracks / vias without a net.
- **Mounting holes H1-H4**: one plated pad each, drill 3.0, 6.35 mm on all copper layers, no net, at the
  four IPC hole records; in the round trip their flashes match on all four layers. (README's "Mechanical
  baseline" numbers the holes in another order than the board refdes: README H2 / H3 / H4 = board H3 /
  H4 / H2. Cosmetic.) **Corrected 2026-11-20 (user decision): README uses the board refdes.**
- **38 bottom-side parts**: the board's bottom list equals the IPC bottom SMD list exactly (C23 C24 C25,
  C30-C48, D2 D18, DRV1 DRV2 DRV5 DRV6, R21-R25, R31-R35); a part
  flipped to the wrong side fails ipc356_diff (negative test).
- **Multi-pad pins**: the six blade terminals have two pads numbered 1 on one net each (B+, GND, V_A,
  GND, GND, PREOUT), L5 / L6 / L11 / L12 one pad (OUT1, U_OUT, OUT2, UC3).
- **KRL2012 shunts R29 R30 R72 R75**: 0.35 × 2.0 pads (Proteus), pad 1 GND, pad 2 CURRENT_L3 / C3_CURRENT /
  CURRENT_L1 / C1_CURRENT; two-terminal parts (no Kelvin pads): the sense nets leave from pad 2.
- **Single-pin nets**: 21 one-pad nets on the board (the 18 unused J1 signals, FLOATING, J1-37 / 38
  unconnected) carry no track, via or zone.
- **J1 numbering (finding 12)**: checked from the pads and the Proteus layers: pin 1 (-98.51, -21.30),
  pin 2 below it (-98.51, -22.57), pin 3 to the right; J2 has the opposite handedness (= KiCad's). The
  Proteus **Top** Assembly has the J1 outline with its pin-1 dot at pin 1 and the Top Silk the text "J1";
  nothing of J1 on the bottom layers. Confirmed: a top-side part with mirrored numbering.

Review findings (conversion; for Phase 5 decisions):

1. **The Proteus TO-220 pads are 1.524 × 2.54 mm rounded rectangles, not 1.524 round** (gerber aperture
   macro `PPAD010` on all four layers of Q3 Q4 Q7 Q8; the IPC records only 1.524 × 1.524). A scratch
   script compared every IPC pad size with its gerber flash: these 12 pads are the only ones that
   differ. The Phase 2 pad table is corrected. Consequences: (a) the KiCad pad (1.905 × 2.0) is wider
   and shorter, so the round trip has pad-shape clusters both ways (only Proteus 2.4–10.1 mm² per layer:
   the 0.27 mm pad ends); (b) **the gap between neighbouring TO-220 pads is 0.635 mm with the KiCad
   pads, 1.016 mm in Proteus**, and pad 2 is the collector on UIN / OUT1 / OUT2 (the HV bus) next to the
   gate and emitter pads; (c) `ipc_sizes=True` would give 1.524 round pads here, not the Proteus pads
   (p2k candidate 21). User decision for Phase 5 (Proteus pads on Q3 Q4 Q7 Q8 for the HV spacing).
2. **J2 on In2.Cu** – above (pending).
3. **J1's square pad sits on the pad numbered 2** (KiCad's pin-1 pad after the odd / even swap; Proteus
   pads are all round, its pin-1 dot is at pad 1): 4 corners of 0.018 mm² per layer and a square
   clearance hole in the In2.Cu plane. Cosmetic copper, but a misleading pin-1 mark on the board;
   Phase 5 candidate (round pad, or the square on pad 1), together with finding 12.
4. The larger KiCad pads on HV nets (C1-C7 C11 C26 2.0 vs 1.524; Q above) reduce Proteus' copper
   spacing by up to 0.24 mm per pad. DRC (0.12 mm) and the round trip (no clearance cluster at these
   parts: no pour had to pull back) are clean; noted for the pad-size decision of an HV board.

### Earlier findings: confirmed / refuted

| Finding | Verdict |
|---|---|
| 1 `+2V5_BIAS` name | **Confirmed** as a question: PDF page 5 has REF1 `ISL21010CFH315Z-TK`, R74 220, R73 470 → about 1.02 V if the part is the 1.5 V version. User decision (net name). |
| 2 15 V "Not yet complete" | Confirmed (page 5 note; one net 15V_BOOST in the IPC). |
| 3 Board thickness | Answered by the user (1.6 mm); board file 1.6 mm, 4 copper layers. |
| 4 No title blocks | Confirmed. |
| 5 Dates | Confirmed (PDF 2026-09-19, gerbers `CreationDate` 2026-11-19); PDF = IPC on every page (above). |
| 6 ADC VA / VIN | **Confirmed, also against the TI datasheet** (ADC121C021/027, pin table: ADC121C027 SOT VA 1, GND 2, VIN 3, ADR0 4, SCL 5, SDA 6): the board has the filtered input on pad 1 (VA) and 3V3 on pad 3 (VIN) on all three ADCs. PDF, IPC, KiCad agree. Open (redesign). |
| 7 Current-measurement names | Confirmed from pages 1 and 4 (`Input_current` on the GND rail; C3_current → input_current_meas, CURRENT_L1 → C2_current_meas, CURRENT_L3 → C3_current_meas). Open. |
| 8 LT1014 at 3.3 V | Confirmed as drawn (U2 `LT1014`, pins 4 / 11 on 3V3 / GND). Open. |
| 9 Devices vs values | Not re-derived from ROOT.DSN; the values agree with the PDF and the pinouts with the IPC nets. |
| 10 Voltage range | Confirmed (3 × 1M, 15k: 1 / 200). |
| 11 R26 ∥ R27 | Confirmed as drawn; intended (user). |
| 12 J1 mirrored numbering | **Confirmed** (above). Open. |
| 13 0.127 mm clearances | Consistent: DRC with clearance 0.12 has 0 clearance errors on the Proteus copper; not re-measured. Open (note). |
| 14 Copper stubs | Confirmed (DRC: 2 track_dangling). Phase 5. |
| Phase 2 pad table, "Q3 Q4 Q7 Q8 1.524 round" | **Refuted**: 1.524 × 2.54 (review finding 1). |
| Phase 2 / 3 "KiCad pads on J2 change nothing" | True for DRC, **not for the copper**: the In2.Cu plane web (pending). |

### Negative tests (scratch copies `build/tmp/neg_*`, `P2K_BOARD`, board file changed with pcbnew, deleted)

| Change | ipc356_diff | gerber round trip (through `roundtrip_pending.py`) |
|---|---|---|
| F.Cu SCL track moved 0.3 mm | OK (does not look at tracks) | **FAILED**: 2 more `other` clusters, 2 uncovered draws |
| In1.Cu track deleted | OK | **FAILED**: `other` only Proteus 0.939 mm², 1 uncovered draw |
| R76-2 net SCL → SDA | **FAILED**: "pad R76-2: Proteus net SCL …, KiCad net SDA" (nets not 1:1) | pending only (no copper change) |
| J1-37 (N/C) → GND | **FAILED**: "pad J1-37: N/C in Proteus, KiCad net GND" | pending only |
| R1 moved 0.1 mm | **FAILED**: "R1-1: nearest KiCad record 0.100 mm away" (×2) | pending only (0.1 mm of an 0402 pad is inside the pad-shape class) |
| R1 flipped to the bottom | **FAILED**: "pad R1-1: side Proteus top, KiCad bottom" | pending only: **the missing pads count as pad shape** (p2k candidate 20) |
| GND via deleted | **FAILED**: "Proteus via at (-78.498, -9.384): nearest KiCad record 3.769 mm" | **FAILED**: 4 more `other`, 2 uncovered, 1 drill mismatch |
| J1 drills 0.558 → 0.5 | **FAILED**: "pad J1-n: drill Proteus 0.558, KiCad 0.5004 is smaller" (every J1 pad) | **FAILED**: "drill at …: Proteus 0.5588 mm, KiCad 0.5 mm is smaller" (every J1 pad) |
| B.Cu UC3 zone deleted | OK | **FAILED**: `other` only Proteus 38.9 mm², 14 uncovered |
| In2.Cu zone with thermal reliefs, refilled | OK | **FAILED**: 16 uncovered, many `other`; the J2 cluster changes (0.835 mm²) and is no longer the recorded one |
| J2 with the Proteus pads (scratch rebuild) | OK | plain `gerber_roundtrip --check` **OK** (the wrapper then says to remove itself) |

The two checks cover each other: nets, positions, sides and drills by the IPC diff, copper by the round
trip. `reports/roundtrip/` (report + four overlays) is committed; two runs give identical files.

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
| Q3 Q4 Q7 Q8 | **1.524 x 2.54 rounded rectangle** (gerber macro; the IPC says 1.524 x 1.524 – corrected in Phase 4, review finding 1) | 1.905 x 2.0 (wider, shorter) | 1.016 | **1.1** (larger) |
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

`tools/check_all.sh`, 2026-11-20 (after the design fixes: finding 7 renames, finding 14 stubs; 19 steps):

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
== KiCad net names = IPC names after NET_ALIASES (no name hints)
== Footprint library, map and fp-lib-table up to date
gen_footprints: 158 parts, 23 footprints (15 project), up to date
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
J2               PinHeader_2x08_P1.27mm_Vertical             0.000 @   180    1.270 @   180  unmirrored 0.000  (standard numbering fits on top (spec with the Proteus pad sizes))
TO-220           TO-220-3_Vertical                           0.000 @   180    0.000 @     0  unmirrored 0.000  (inline: marker by render (spec with the Proteus pads))
SMA              D_SMA                                       0.050 @     0    0.050 @   180  mirrored 0.050  (two pads: band by render)
CP               CP_Radial_D10.0mm_P5.00mm                   0.000 @   270    0.000 @    90  unmirrored 0.000  (two pads: '+' by render)
check_pin_order: OK (results as recorded in STATUS.md)
== PCB rebuilt from schematic + gerbers, up to date
build_pcb: 158 footprints placed (2 excluded from board), 4 mounting holes, 115 nets, 4 outline segments
gerber_to_tracks: 1838 tracks, 141 vias (IPC 141), 21 pour outlines on User.1-4; removed as recorded: 1 tracks (REMOVED_TRACKS), 0 vias (REMOVED_VIAS)
remove_dot_tracks: 2 zero-length tracks deleted (1 entries, REMOVED_DOT_TRACKS)
assign_nets: stage A (no pours): 225 groups, 0 shorts, 36 orphans, 11 opens
assign_nets: stage B (with pours): 119 groups, 0 shorts, 0 orphans, 0 opens
pours_to_zones: 21 pours -> 21 zones; 24 holes closed by the stroke, 259 holes kept
place_refdes: 4 Fab only, 92 kept, 64 moved, 2 moved, 0.8 mm text (sizes 1.0, 0.8 mm)
make_pcb: board rebuilt from scratch, byte-identical
== Board pads, holes, vias vs IPC (position, size, nets 1:1)
check_board: 162 footprints, 429 pads, worst pad offset 0.039 mm (limit 0.05), 113 IPC nets mapped 1:1, 4 mounting holes
check_board: 1836 tracks, 141 vias, 21 zones
check_board: OK
== Board copper connectivity after zone fill
assign_nets: after zone fill: 119 groups, 0 shorts, 0 orphans, 0 opens, 0 items with a foreign net
assign_nets: OK (report reports/assign_nets.txt)
== DRC with schematic parity
drc: 28 violations, 0 shorts, 0 unconnected, 0 parity issues (reports/drc.json)
drc:     20 error    courtyards_overlap  accepted: KiCad IPC-7351 courtyards vs the Proteus placement (parts at the Proteus positions)
drc:      5 warning  silk_overlap
drc:      3 warning  silk_over_copper
drc: OK
== IPC-D-356 from the board vs Proteus (pads, vias, holes, nets)
ipc356_diff: Proteus 574 records, KiCad 574; matched 574 (429 pads incl. 2 N/C, 141 vias, 4 holes), worst position offset 0.040 mm (limit 0.05)
ipc356_diff: 113 Proteus nets mapped 1:1 onto KiCad nets, 0 mismatches
ipc356_diff: KiCad drill larger (footprint kept): 18x 0.812->1.001
ipc356_diff: pads with another size in KiCad (info): C 96, D 4, DRV 16, L 6, Q 12, R 150, REF 3
ipc356_diff: OK
== Gerber round trip vs Proteus (copper XOR, coverage, drills)
roundtrip: F.Cu   XOR   46.69 mm^2, beyond 0.05 mm: only Proteus   3.89, only KiCad  19.98 mm^2; clusters >= 0.01 mm^2: 224 pad shape; draws/flashes off the other copper: 0 Proteus, 0 KiCad
roundtrip: In1.Cu XOR   31.75 mm^2, beyond 0.05 mm: only Proteus   0.00, only KiCad  27.52 mm^2; clusters >= 0.01 mm^2: 18 pad shape; draws/flashes off the other copper: 0 Proteus, 0 KiCad
roundtrip: In2.Cu XOR   33.82 mm^2, beyond 0.05 mm: only Proteus   0.00, only KiCad  27.57 mm^2; clusters >= 0.01 mm^2: 18 pad shape; draws/flashes off the other copper: 0 Proteus, 0 KiCad
roundtrip: B.Cu   XOR   52.14 mm^2, beyond 0.05 mm: only Proteus   0.99, only KiCad  36.02 mm^2; clusters >= 0.01 mm^2: 139 pad shape; draws/flashes off the other copper: 0 Proteus, 0 KiCad
roundtrip: Proteus objects not compared (recorded deviations, all layers): 1 Conductor draws (REMOVED_TRACKS)
roundtrip: drills 0 mismatches; report reports/roundtrip/roundtrip.txt, overlays reports/roundtrip/*.png
roundtrip: OK
== Proteus-pad parts: board pads = Proteus flashes and drills
check_proteus_pads: 13 parts, 130 pads, 334 pad layers compared with the Proteus flashes and drills: OK

ALL CHECKS PASSED
```

## Findings about the original design

Reported, not fixed (PLAN.md section 5). Since 2026-11-20 the user has findings fixed in the KiCad design
(values unchanged): 1 (rename), 7, 14 done; 6 and 12 later (section "Design fixes 2026-11-20").

1. **`+2V5_BIAS` name vs the circuit (to confirm):** REF1 is an ISL21010CFH315Z-TK. In the
   ISL21010 ordering code, `-15` is the 1.5 V version (confirm against the fitted part).
   Its output feeds R74 220 R -> `+2V5_BIAS`, with R73 470 R to GND, which gives about
   1.5 x 470 / 690 = 1.02 V, not 2.5 V. So the net name, the part or the divider is stale. Not
   aliased: renaming the net is a user decision (tube_psu renamed its bias net to the real
   voltage, `+2V5_BIAS` -> `+1V65_BIAS`).
   **Done (user decision 2026-11-20): renamed `+1V0_BIAS`** in the KiCad design through
   `NET_ALIASES` (section "After Phase 5"); the Proteus IPC / gerbers keep `+2V5_BIAS`. The divider
   is still the redesign's question (a 1.0 V rail from a 1.5 V reference).
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
   **Done (user decision 2026-11-20): renamed** through `NET_ALIASES` to `CURRENT_C3`, `CURRENT_C6`,
   `CURRENT_Q4`, `CURRENT_Q7` and `CURRENT_C3_MEAS` (J1-7), `CURRENT_C6_MEAS` (J1-5), `CURRENT_Q4_MEAS`
   (J1-1), `CURRENT_Q7_MEAS` (J1-3) (section "Design fixes 2026-11-20"; on closer reading `C1_CURRENT` did
   not match either: it is C3's current). The control card side keeps its own names.
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
    coordinates); KiCad DRC `track_dangling` warnings, copper as drawn. **Kept as drawn (user, Phase 5).**
    **Removed (user decision 2026-11-20, reverses Phase 5):** the stub by `REMOVED_TRACKS`, the two OUT1
    draws by `tools/remove_dot_tracks.py` (section "Design fixes 2026-11-20"); 0 track_dangling.

15. **TO-220 pads (Q3 Q4 Q7 Q8) are 1.524 × 2.54 mm in the Proteus copper; the IPC-D-356A file says
    1.524 × 1.524** (Phase 4): the gerber flashes are an aperture macro (rounded rectangle), the IPC
    records only the width. The only pads of the board whose IPC size differs from the gerber. The KiCad
    footprint's pads (1.905 × 2.0) leave 0.635 mm between the collector pad (UIN / OUT1 / OUT2) and its
    neighbours, Proteus 1.016 mm. Pad-size decision for Phase 5 ("Phase 4 – review" 1). **Done (user,
    Phase 5): the Proteus pad from the gerbers on Q3 Q4 Q7 Q8, drill 1.016; 1.016 mm between the pads.**
16. **J2 on the In2.Cu GND plane** (Phase 4): with the KiCad pads on J2 the plane loses the 0.73 mm² web
    between J2-1..4 (connects nothing). **Decided (user, Phase 5): Proteus pads on J2; the web is back.**

## p2k candidates

Shared-tool limitations met on this board, with the board-local workaround used.

1. `ipc356`: the `pin_nets_by_component.md` header prints `Net aliases: .` when `NET_ALIASES` is
   empty. Print "none" instead (cosmetic).
   **Solved in p2k a9a286c** (batch R, I3).
2. `ipc356`: `pins_by_net.md` lists a two-hole terminal pin twice (`B_P-1 B_P-1`, pin count 5 for
   B+), because it counts records, not distinct pins. Distinct `(refdes, pin)` would read better
   (cosmetic; tube_psu has the same).
   **Solved in p2k a9a286c** (batch R, I5; D-R re-baseline in step 1).
3. **`p2k.pdsprj.lyt_parts` finds no part record in this ROOT.LYT** (Proteus 8.12 SP2): there
   are no `EID` / `EID_A` markers. The records here read `<package> <refdes> PS "Vector Font"
   "PART REFERENCE" <value> PS "Vector Font" "PART VALUE" <pin nets...>`, with stray binary
   bytes glued to tokens (`Q74`, `TERMINALP`, `IKP08N65F54`), so a token reader is unreliable.
   Workaround: `dsn_devices()` in `tools/make_part_map.py` reads device and package from the
   ROOT.DSN component record (device = first string after `COMPONENT VALUE`, package =
   `{PACKAGE=...}` property). The shared tool would need: a `dsn_devices` reader (this one), and
   a binary (length-prefixed) reader for this LYT record format.
   **Solved in p2k a9a286c** (`pdsprj.dsn_devices`, `part_map` `LAYOUT="dsn"`).
4. **`p2k.sheetkit.terminal` hard-codes value "PIN"** (and its left/right text justification
   draws over the circle in KiCad 10.0.7): `term()` in `tools/sheets/_common.py`, copied from
   tube_power_amp (their candidates 3 and 7).
   **Solved in p2k a9a286c** (`terminal(symbol=, value=, justify="away")`).
5. **`p2k.sch_builder.Sheet.place` cannot mirror**: `place_mirrored()` in `_common.py`, copied
   from tube_power_amp (their candidate 6); used for J1 and J2 (pin 1 at the bottom, as the
   PDF draws them). `symgen.header` could also take a `bottom_up=` option. The mirrored box is
   not symmetric about its origin, so the sheet script passes `ref_at` / `value_at` (the
   library value position lands inside the box).
   **Solved in p2k a9a286c** (`place(mirror=)`).
6. **Part-map generator** is the tube_power_amp script plus `dsn_devices()` and a value-based
   symbol choice (`SYMBOL_BY_VALUE`, two op-amps with the same Proteus device): a shared
   `p2k.part_map` would serve all boards (tube_power_amp candidate 5).
   **Solved in p2k a9a286c** (`part_map.run`).
7. `symgen.box` pin length is fixed at 2.54 mm: four-character pin numbers (`COM1`, `COM2` of
   the ADC121C027) overlap the body outline in the render (cosmetic). A `pin_length=` option
   would fix it.
   Solved in p2k a9a286c (`box(pin_length=)`); **not migrated**: it changes the symbol library (cosmetic, not an accepted re-baseline); a redesign / later choice.
8. `Sheet.place` puts the reference / value of a **horizontal two-pin part** 2.54 mm above /
   below the centre line (or both on one side with `text=`). That fits a resistor, but a
   horizontal capacitor's plates are about 2 mm high, so the texts lie on them. Workaround:
   `ref_at` / `value_at` at ±3.81 mm in `_common.py` (`_hcap()`, `si8271_cell()`). The shared
   tool could take the offset from the symbol's body height.
   **Solved in p2k a9a286c** (`place(text_gap=)`).

9. `compare_netlists` prints "IPC nets touched 115, complete 115" on a board with 113 nets: the
   two N/C pads (J1-37 / 38) count as one group each. Printing "113 nets + 2 N/C pads" would
   read better (cosmetic).
   **Solved in p2k a9a286c** (C6: "IPC nets touched 113, complete 113 (+ 2 N/C / no-net pins)").

10. The `SEND` / `SEND1` refdes sort crash of `compare_netlists` (reported by the FX-loop
    board) **does not occur here**: every refdes prefix of this board is either always
    numbered or never; no wrapper needed.
11. `p2k.footprints.run` does not write the project `kicad/fp-lib-table`: `fp_lib_table()` in
    `tools/gen_footprints.py` (copied from tube_power_amp, their candidate).
   **Solved in p2k a9a286c** (`FP_LIB_TABLE`).
12. **`p2k.footprints.derive` moves the base pads onto the IPC positions however far they are**
    (negative test T3: A1 / COM2 exchanged in the ADC renumbering → the derived footprint still
    fits, check_footprints passes). The shared tool should fit the unmoved, renumbered base first
    and fail (or need an explicit `allow_move=` limit) when a pad moves more than a fraction of
    the pitch (e.g. > 0.5 mm); the board-local guard is `tools/check_pin_order.py`, which takes
    base + renumber from `gen_footprints.PROJECT`.
   **Solved in p2k a9a286c** (spec `max_move`, strict `derive_max_move` on by default; and `p2k check_pin_order`).
13. `p2k.check_footprints` accepts a THT part that fits only mirrored (bottom) with a note (J1
    with the plain KiCad header, T4). It could compare with the Proteus assembly / silk layer
    the part is drawn on, or need a config list of bottom THT parts.
   **Solved in p2k a9a286c** (`BOTTOM_THT`, opt-in by key presence; not set: no bottom THT part here; strict `derive_max_move` already fails a derived THT part that fits only mirrored).
14. `tools/check_pin_order.py` is board-local here and on tube_power_amp (with the tie rule for
    symmetric two-pad / inline patterns and `--render` over the Proteus silk / assembly of the
    part's side): a shared `p2k.check_pin_order` with the CHECKS table in the board repo.
   **Solved in p2k a9a286c** (`p2k check_pin_order`, `PIN_ORDER`; board script deleted).

15. **`tools/measure_gaps.py` copied unchanged a third time** (tube_psu, tube_pi_fxloop, here): a
    shared `p2k.measure_gaps` would do.
   **Solved in p2k a9a286c** (`p2k.measure_gaps`; board script deleted).
16. **A pending-decision mode for `p2k drc` and `p2k.assign_nets --check`:** board-local
    `tools/drc_pending.py` (as tube_pi_fxloop's; removed after the decision, in git history d1c551a)
    passed exactly the recorded conflicts while the pad decision was open. A config key (e.g. `DRC_PENDING = {refdes: reason}` with expected counts) and
    a "PENDING" exit state in the shared tools would replace the per-board wrappers.
   **Solved in p2k a9a286c** (`PENDING`; nothing pending here).
17. **Testing Proteus pads on a refdes set:** board-local `tools/pad_option_test.sh` (removed after the
    decision, in git history d1c551a) patched
    `refdes=` rules and `<footprint>_ProteusPads` specs (`ipc_sizes=True`) into a scratch copy of
    gen_footprints.py. `p2k.footprints` could take a `PROTEUS_PADS = {refdes}` config key that does
    this (derived Proteus-pad variants for the named parts only), so the decision is one config line.
    Applied by hand here: `PROTEUS_PADS`, four `refdes=` rules and four `_ProteusPads` specs (≈ 40 lines
    in gen_footprints.py, plus the renamed specs in check_pin_order.py).
   Solved in p2k a9a286c (`PROTEUS_PADS`, F8); **not migrated**: the hand-written `_ProteusPads` specs have other names / descr / `ipc` refdes (F8 would not reproduce them byte for byte).
18. **A changed track net is caught only by the byte compare** (negative test T1, as tube_power_amp):
    pcbnew re-derives track nets on load, so check_board, assign_nets --check and DRC do not see it.
    check_board could read the track nets from the file (s-expression) and compare them with the
    assign_nets groups.
   **Solved in p2k a9a286c** (strict `track_nets`, on by default).
19. KiCad's DRC reports one violation per track against its closest pad, so a conflict can hide
    behind a neighbour (ADC2 showed only after ADC3 had the Proteus pads): `pad_option_test.sh`
    re-runs the DRC on the whole candidate set; a shared tool could measure every pad-to-track gap
    itself (as measure_gaps does for the Proteus copper).
   Documented in the playbook (G3); per-pad gaps not implemented in p2k (B11 option, low priority).

20. **`gerber_roundtrip` classifies a missing or extra pad as `pad shape`** (Phase 4 negative test: R1
    flipped to the bottom → no `other` cluster, no uncovered flash; the pads lie inside the XOR of the two
    pad sets). ipc356_diff and check_board catch it; the round trip could require every pad flash of one
    set to overlap a pad flash of the other.
   Solved in p2k a9a286c as the opt-in strict id `roundtrip_pad_match`; **not enabled** (it fails on the KiCad library pad sizes on every board, D-Z).
21. **Proteus pad sizes are taken from the IPC** (`reports/footprint_pads.csv`, `ipc_sizes=True`, the
    "pads with another size" list of ipc356_diff), which is wrong for pads flashed with an aperture macro
    (TO-220 here: IPC 1.524 × 1.524, gerber 1.524 × 2.54 rounded rectangle). The shared tools could take
    size and shape from the gerber flash at the pad position (check_sources could compare the two).
    **Phase 5 workaround:** `TO-220-3_Vertical_ProteusPads` sets the gerber pad through the `pads` key (25).
   Not in p2k (F9, low priority); the spec key `pads` (25) covers the TO-220.
22. **A pending-decision mode for `gerber_roundtrip`** (as candidate 16 for drc / assign_nets):
    board-local `tools/roundtrip_pending.py` passes exactly one recorded `other` cluster. The tool could
    also classify a Proteus copper island that is enclosed by clearance areas of larger KiCad pads (the J2
    web: bounded on all sides by the `clearance` mask) as `clearance` or as its own category. (The wrapper
    was removed in Phase 5 after the J2 decision; in git history d666593.)
   **Solved in p2k a9a286c** (`PENDING`, gerber_roundtrip in `PENDING_TOOLS`); the enclosed-island class is X6 (not done).
23. `ipc_sizes=True` keeps the KiCad pad **shape** (J1: the square pin-1 pad, on the pad numbered 2 after
    the odd / even swap; Proteus pads are round). A `shape=` / `ipc_shapes=` option would reproduce the
    Proteus pads fully. **Phase 5 workaround:** the board-local spec key `pads` (below, 25) sets J1 pad 2
    and J2 pad 1 round.
   **Solved in p2k a9a286c** (spec key `pads`).

24. **A check that the Proteus-pad parts really have the Proteus pads** (Phase 5): board-local
    `tools/check_proteus_pads.py` compares each board pad (pcbnew polygon) with the gerber flash and drill at
    its position. Without it, a KiCad pad, a turned pad, a larger drill or a square pin-1 pad on a decided
    part passes every shared check (negative tests). A shared `p2k.check_pads` with a `PROTEUS_PADS` config key
    (candidate 17) would cover every board.
   **Solved in p2k a9a286c** (`p2k.check_pads`, `PROTEUS_PADS_CHECK`; board script deleted).
25. **Pad shape / size / drill per pad in a derived spec** (Phase 5): board-local spec key `pads` = {pad
    number or `*`: dict(shape=, size=, rratio=, drill=)} applied by a wrapper around `p2k.footprints.derive`
    in `tools/gen_footprints.py` (monkeypatched module function). The shared tool could take this key (or
    candidate 21's gerber pads) directly.
   **Solved in p2k a9a286c** (spec key `pads`; the board wrapper deleted).
26. `place_refdes` puts 4 references (R52 R54 R69 R74) on the Fab layer only: dense 0402 groups. Accepted
    (user default); a smaller third size or placement over the part body could keep them on the silk.
   Not changed (p2k X4: accepted by the user).
27. **`compare_netlists` only warns when a named net differs in name** ("name hint"): with the
    `+2V5_BIAS` → `+1V0_BIAS` alias removed it still says OK (pins match); check_symbols catches it here
    only because the net is a power symbol. A strict option (fail when a KiCad net that is not
    auto-named matches an IPC net that is not `#00xxx` under another name) would guard renamed labels too.
    (Candidate 1, the empty `Net aliases:` header, no longer shows on this board.)
    **2026-11-20:** with the finding 7 label renames this gap is real (a dropped alias passed every check);
    board-local guard in check_all.sh: fail on `WARNING: name hint`.
   **Solved in p2k a9a286c** (strict `net_names`; the check_all grep guard removed).
28. **`REMOVED_TRACKS` can't remove a segment that Proteus drew twice** (2026-11-20, finding 14): the two
    zero-length OUT1 draws are one segment in both directions; one key matches both and gerber_to_tracks
    rejects the duplicate match, two keys can't be told apart. A count in the value (`(reason, n)`) or
    "a key matches all identical draws" would do; board-local `tools/remove_dot_tracks.py` +
    `REMOVED_DOT_TRACKS` until then (then move the entry to REMOVED_TRACKS and drop the script).
   **Solved in p2k a9a286c** (`(reason, n)`; D-I7; `remove_dot_tracks.py` deleted).
29. **make_pcb.sh template:** `run ... || {...}` disables `set -e` inside `run()`; chain the steps with `&&`
    (fixed here, preamp, PI/FX). Worth fixing in the playbook's make_pcb template / other boards.
   **Solved in p2k a9a286c** (`p2k make_pcb`; make_pcb.sh is the one-liner).

## Decisions

- **User decision 2026-11-20 (through the coordinating session): the current-measurement nets are
  named after the switch (`CURRENT_Q4`, `CURRENT_Q7` and their `_MEAS` outputs), not the inductor,
  because the emitter shunt measures the switch current.** Confirms the names chosen in "Design
  fixes 2026-11-20"; `CURRENT_L1` / `CURRENT_L3` were the alternative.
- User decision 2026-11-20: the master repo's mechanical baseline (`tube_amplifier_kicad`
  `mechanical/hv_supplies_v2.kicad_pcb`) now numbers its holes H1-H4 like this board (done there,
  be5124f).

- **User decisions, 2026-11-20 (through the coordinating session), design fixes:**
  1. **Fix design findings in the KiCad design, but leave component values as they are** (finding 8,
     LT1014 at 3V3, etc. unchanged). HV supplies v2 is not installed and is the redesign's starting point.
  2. **Finding 7: rename the current-measurement nets so each name says what it measures**, worked out from
     the circuit, in the board's naming style, through `NET_ALIASES`; nets crossing the J1 ribbon may be
     renamed if listed (the control card is a separate repo, not touched).
  3. **Finding 14: remove the two zero-length OUT1 draws and the 0.9 mm 15V_BOOST stub** with
     `REMOVED_TRACKS` (reverses the Phase 5 keep decision).
  4. **README "Mechanical baseline": hole numbering = board refdes H1-H4.**
  5. **Not now:** finding 6 (ADC VA / VIN swap: a hand edit later, after generation stops) and finding 12
     (J1 renumbering: waits for a new shared-tool pin-renumber key).
  6. **Generation stops later; the board stays generated for now.**
  Also from the coordinating session (user-approved, a check bug): fix the make_pcb.sh `--check` step
  failure handling (as preamp b2adf22 / PI-FX da551f3).
- **Design fixes (agent, 2026-11-20):** names `CURRENT_<refdes>` / `CURRENT_<refdes>_MEAS` (the
  `<refdes>_CURRENT` form collides with IPC names in `ipc356 --check`); the low-side shunts named after the
  switch (`CURRENT_Q4` / `Q7`), not the inductor (open for the user: `CURRENT_L1` / `L3` instead). The OUT1
  zero-length pair by a board-local step (`REMOVED_DOT_TRACKS`, `tools/remove_dot_tracks.py`), since
  `REMOVED_TRACKS` can't express a segment drawn twice (p2k candidate 28). New check_all guard on
  compare_netlists name hints.

- **User decisions, 2026-11-20 (through the coordinating session), after Phase 5:**
  1. **Rename `+2V5_BIAS` to `+1V0_BIAS`** (finding 1; REF1 1.5 V into R74 220 / R73 470 → about
     1.02 V). Done in the KiCad design through `NET_ALIASES = {"+2V5_BIAS": "+1V0_BIAS"}`
     (p2k_config.py, the existing p2k mechanism); the Proteus IPC / gerbers keep `+2V5_BIAS` and every
     check still matches the net 1:1 by pins.
  2. **HV supplies v2 is not installed and will be redone anyway; this conversion is only the starting
     point for the redesign.**

- **Phase 5 user decisions (user, 2026-11-20, through the coordinating session):**
  1. **J2: Proteus pads** (J2 in `PROTEUS_PADS`; the round trip is then clean); `tools/roundtrip_pending.py`
     removed, check_all.sh calls `p2k gerber_roundtrip --check` directly.
  2. **TO-220 Q3 Q4 Q7 Q8: the Proteus pad shape as in the gerbers** (1.524 × 2.54 mm rounded rectangles;
     the IPC 1.524 round size is wrong, so not `ipc_sizes=True` – built from the gerber flashes, finding 15)
     **with the Proteus 1.016 mm drill**, to keep the 1.016 mm HV spacing between the pins; long-axis
     orientation checked against the gerbers on all four.
  3. **J1: all pads round** as in Proteus (no square pad on the pad numbered 2).
  4. Phase 5 defaults: reference texts placed automatically (`place_refdes` in make_pcb.sh, as the power
     amp); the dangling Proteus stubs kept as drawn (finding 14); body graphics, sheet names and 1.6 mm kept;
     **the board stays generated** (stopping generation is the user's call at the first hand edit); the
     `_ProteusPads` names kept.
- **Phase 5 (agent, 2026-11-20):** J2's pad 1 is round as well (decision 1 read with decision 3's reason:
  Proteus pads are round; KiCad's square pad 1 was the only pad-shape difference left at a Proteus-pad part).
  The TO-220 pad corner radius 0.3048 mm (rratio 0.2) is the macro's. New guard `tools/check_proteus_pads.py`
  in check_all.sh (the reverted pad decisions pass every other check). `REFDES_PLACEMENT` at the defaults.
  LCSC / BOM fields (tube_psu) and the `+2V5_BIAS` name (finding 1) were not part of the decisions: not done.

- **Phase 4 (agent, 2026-11-20):** the one `other` cluster of the round trip (J2, In2.Cu) is **not** fixed
  by changing the pad decision A2; `tools/roundtrip_pending.py` passes exactly that cluster as a pending
  user decision and `tools/check_all.sh` reports it. No Phase 4 config key was needed (`ROUNDTRIP`
  defaults, `STACKED_VIAS` 0, no `DRILL_SMALLER`). `reports/roundtrip/` is committed (as tube_psu).
- **Open user decisions after Phase 4:** J2 pads (Proteus pads → round trip clean; tested); TO-220 pads
  (finding 15); J1 square pad on pad 2 (review 3); findings 1, 6, 7, 8, 10, 12, 13, 14 as before.
  (Pads decided in Phase 5.)

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
  (Superseded 2026-11-20: `{"+2V5_BIAS": "+1V0_BIAS"}`, user decision.)
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
