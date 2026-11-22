# Status: HV supplies rev 3

**Second pass (2026-11-23): consistent first draft.** Contract: tube_amplifier_kicad
`docs/interfaces.md` IF-1.2 with IF-2 on W17 (read at 3883bc7), the review
`docs/revb_first_pass_review.md` (7.1 decisions, K12, M16, M19, E28), SPECIFICATION ENV-2 (70 °C).
The first pass (c947e82) is kept below as history; where the two differ, this section is current.

**Done:** five generated sheets, **200 parts, 113 nets, ERC 0 errors / 2 warnings** (the same two
expected `ground_pin_not_ground` on U301 / U302 VSSA = switch node; `reports/erc.rpt`). Footprints on
every part (`lib/footprint_map.csv`, written by the sheet script, stock KiCad libraries except the
blade tabs and one marked placeholder); BOM `bom/bom.csv` (79 lines, 204 pieces, 17 lines with a
candidate part number, 5 lines marked placeholder / TBD, R444 DNP). New simulations in `sim/`
(loop with the link delay, second LC stage, output discharge) and a block floorplan in
`mechanical/`. No layout.

## S1. What changed and why (decision by decision)

| # | Decision / input | Change on the board | Where |
|---|---|---|---|
| 1 | **No fuses in the RAW_SS feeds** (user U19, 2026-11-23; interfaces 3.1, 4.2, 8) | F101 / F102 removed. **R101 / R102 link footprints** in series with RAW_SS1 / RAW_SS2 (axial 0617, 20.32 mm: a wire / 0 Ω link fitted, or a 10-47 Ω 2 W flameproof fusible resistor). Nothing on this board depends on the PSU's trip levels (lab parameters) | sheet 01 |
| 2 | **Ramp energy goes back into the tube PSU** (U4; interfaces 3.1, 8) | Brake removed (R105 470 Ω 30 W, Q101, D103, U101 UCC27511, the brake comparator and TH_BRK). **Latched raw over-voltage trip kept at 475 V** (TH_OVR now 1.1k / 19.1k: 475.1 V). **No backstop clamp:** once the trip has fired the bridges stop within about 10 µs and the only energy left to come is the 3 mH inductors' (≈ 2 mJ at 1.25 A) plus 10 µs at ≤ 0.8 A × 475 V (≈ 4 mJ): < 0.1 V on the board's raw capacitance. A clamp would only protect against the PSU itself, which has its own OVP. A ramp too fast for the PSU ends in the trip: if the PSU is off or in a fault the board's own raw capacitance (≈ 290 µF) takes ≈ 6 J from 430 to 475 V before the trip, so nothing exceeds 480 V (every raw-rail part on this board is ≥ 500 V) | sheets 01, 05 |
| 3 | **Ramp rate 30 ms to 1 s, programmable** (PS-4) | Sized for the fastest: a 30 ms 200 → 400 V ramp with the full 0.57 A load needs **1.25 A** of bridge current (`sim/loop_digital.py`), plus 0.36 A half ripple at 50 kHz = 1.6 A peak. Hardware trips raised from 1.0 A to **2.0 A forward and 2.0 A reverse** (reverse = sinking on a ramp-down, 0.78 A in simulation, and shoot-through); 3 mH inductor now **Isat ≥ 2.4 A**; shunt amplifiers 0.5 V/A (±2.5 A range, was 1 V/A ±1.25 A) | sheets 02, 04, 05 |
| 4 | **V_ANODE 0.57 A peak** (KT88, review E28) | Covered by 3. D14 unchanged: the bootstrap limit applies to the average current (≈ 0.4 A), **≈ 403 V at 420 V raw**; the 0.57 A peaks come from the output capacitor and the loop: **±0.8 V** at 400 V with 0.57 A peaks at 82 Hz, also at 420 V raw (duty never at the limit) | sim |
| 5 | **Second LC stage near 4 kHz** (first-pass missed 6, M19) | **Moved and damped:** the 47 µF output electrolytic goes to the intermediate node (now one **100 µF / 500 V** per bridge: same energy, one part less), the second stage becomes 33 µH ∥ **5.6 Ω** with a **1 µF / 630 V film** at the output: f0 = 27.7 kHz, Q = 1.0, independent of the electrolytic's ESR. `sim/lc_ac.py` (ngspice, matches the Python model to 2e-8) and `sim/loop_digital.py`: with the same loop gains the first-pass network has 8.3 dB gain margin at low ESR (18.6 dB at 0.5 Ω: it depends on the ESR) and a 6.5 Ω output-impedance peak; the moved stage gives **56° / 9.3-9.6 dB at every ESR and load, Zout ≤ 4.1 Ω from 20 Hz to 5 kHz**. Cost: switching-ripple attenuation of the second stage is 0.71 at 50 kHz / 0.30 at 100 kHz (was 0.01-0.05); ripple at the tab ≈ 0.1-0.2 V p-p (ESR-dominated), within the proposed R8. Option C (2.2 µF / 3.9 Ω) halves it if wanted | sheet 02, sim |
| 6 | **Closed loop with the control board's 50-60 µs** (M16, the condition of the IF-2 acceptance) | `sim/loop_digital.py`: 60 µs sample-to-PWM + zero-order hold at 31.25 kSPS, PI on V_tab + capacitor-current damping (I_C14 / I_C24, already on the ADC): **Kp = 2, Ki = 1000 /s, Kc = 20 Ω**, crossover 1.1 kHz, PM 56°, GM 9.3 dB at every corner (load 700 Ω / 4 kΩ / open, ESR 0.1 / 0.5 Ω). Still stable at 100 µs (PM 40°, GM 5.8 dB). Without the capacitor-current term the best is a 5 Hz loop with 20 Ω peaks: **the I_C channels are part of the control, not monitors**. Load step 0.10 → 0.57 A: −2.5 V. **The IF-2 link passes** | sim |
| 7 | **HV after an inhibit** (K12 / U14; BIAS_OK drops 22-117 ms after a lost -80 V) | `sim/discharge.py`: the bridges stop < 100 µs after HV_PERMIT drops; the 2 x 8 J left in the output capacitors go into the tubes or the bleeders. Bias lost (grid toward 0 V, ≈ 4 x 0.5 A): **below 200 V in 32 ms, below 50 V in 141 ms**; hot idle 0.4 A: 0.16 s / 0.7 s; idle 0.2 A: 0.31 s / 1.4 s; bias clamped cold: bleeders only, 13 s / 39 s. The fast fall happens exactly when the tubes conduct hard, and **all they can ever get is the stored 15.5 J (≈ 4 J per tube)**. **No active discharge needed** (it would add a part that can fail on and a resistor for 16 J); in non-fault cases the firmware ramps the outputs down (energy back to the PSU) before dropping HV_ENABLE. User decision U14 | sim |
| 8 | **70 °C under the plate** (ENV-2, U17) | Loss and thermal table S4. f_sw **50 kHz recommended** (100 kHz still fits thermally). Only Q201 (bridge 1 high side) needs a heatsink: Fischer **SK 104 38.1 mm**, live at UIN (no insulating pad); Q202-Q204 stand free. Raw bleeder R103 / R104 2 x 75 kΩ 2 W MOX (was 2 x 330 kΩ 1 W) for SAFE-4 (60 s) | sheets 01, 02 |
| 9 | **Grounding** (interfaces 5, 12.2) | Unchanged power star (NT101) and fault / RF network (D102 GBU8J ∥ C104 100 nF Y2 ∥ R106 100 Ω 2 W) to the **plated** standoff **H101 next to J101**; **H102-H106 non-plated** (MountingHole_3.2mm_M3, NPTH). The output film capacitors and the bleeders return to the star; the electrolytics return through their shunts to PGND (switching ripple off the star) | sheet 01 |
| 10 | **IF-2 40-pin** (interfaces 9) | J1 as the table, value "IF-2". **Returned ADC clock: pad 16 proposed** (N1), taken from the AD7689's SCK pin through **R444 33 Ω, DNP**: pad 16 stays N/C as interfaces.md says until the two sessions agree | sheets 04, 05 |
| 11 | **Position x 560-675, y 30-180** (12.1, PROPOSED) | Block floorplan (S6): **the power stage does not fit in 115 x 150 mm.** Proposal N2 | mechanical |
| 12 | Short-circuit check of the clamp (found this pass) | D201 S1M → **1N5408** (IFSM 200 A): in a V_ANODE short or arc the 100 µF V_SCREEN capacitor dumps through R210 2.2 Ω and D201 (≈ 180 A, τ 0.2 ms, I²t ≈ 3 A²s, the S1M's own rating) | sheet 02 |

Refs that moved with the redraw (auto-numbered): bridge 1 is Q201 / Q202, L201 (3 mH), L202 (33 µH),
C204 (100 µF), C205 (1 µF), R203 (damping), R204 (2.2 Ω); bridge 2 Q203 / Q204, L203, L204, C209, C210,
R209, R210. Interface connector refs are unchanged (S3).

## S2. Interface check against IF-1.2 / IF-2

50 rows: **43 OK, 2 problems, 5 questions.** OK rows are listed briefly; problems and questions in full.

**Problems**

- **P-a Envelope (12.1).** The block floorplan (`mechanical/floorplan.md`, real part sizes) needs
  about 15,600 mm² of component bodies on the bottom side; 115 x 150 mm minus the notch, the slot
  and the standoffs leaves 16,100 mm². Nothing gets packed beyond about 86 % fill, and a power layout
  with creepage needs about 1.4 times the body area. With the reduced part set already drawn (one
  heatsink, one 100 µF per bridge) it packs only with **both** an L-shaped envelope **and** the SMD
  control block on the plate side (62 % fill). Proposal N2.
- **P-b Raw rail above 430 V (3.1, 8).** A ramp too fast for the PSU lifts the raw rail to the trip
  level before the trip ends it: **475 V nominal, ≤ 480 V with the reference and divider tolerances.**
  The preamp and PI + FX regulators see it through RAW_SS (LND150 500 V, 820k strings "≥ 500 V" in
  preamp_regulator.md: OK but with no margin). Proposal N3.

**Questions**

- **Q-a U14 (8):** accept the tubes discharging the outputs (row 7 of S1, no active discharge) and
  a firmware ramp-down in non-fault cases? User decision with the power amp session.
- **Q-b SPI rate (9):** plain mode 0 at 10 MHz works (the card samples SDO one full period after
  the launching edge: 100 ns against ≈ 60 ns isolator round trip + 15-18 ns AD7689 data delay +
  setup, ≈ 17 ns margin; limit ≈ 12 MHz). At 10 MHz the AD7689 does about 200-230 kSPS, not 250
  (2.2 µs conversion + 1.6 µs transfer + overheads). Enough: the loop needs ≥ 31 kSPS on the four
  controlled channels (V_ANODE, I_C14, V_SCREEN, I_C24), so the firmware schedules them in two of
  every three conversions (the AD7689 takes the next channel in each CFG word on ADC_DIN) and the
  four monitors share the rest. To confirm in the control board's timing budget.
- **Q-c Returned clock pad (9, OPEN):** pad 16 proposed (N1).
- **Q-d Which PSU hole carries W01 (12.1, review Q14).** J101 is drawn next to the rear slot
  (658.5, 154.6); if W01 comes down the front hole, J101 and H101 move to the front notch. The
  rear hole may also carry the mains to the PSU: then the slot edge keeps mains creepage (≥ 6 mm)
  from the raw tabs.
- **Q-e New plate holes under the tube PSU (12.1a).** The board needs east-side support: new holes
  at (671, 48), (671, 128) and the plated H101 next to J101 (about (630, 160)) are all under the
  PSU's footprint on top (x 567-677). Screw heads on top must clear the PSU's base (or use
  press-in studs from below). The existing holes used: (590.0, 87.0), (605.0, 124.7), (605.0, 166.6).

**OK rows (43):** W01-b J101; W02-a J102 and W03-a J103 with link footprints (no fuse); the link
footprint takes 0 Ω or a 2 W fusible; W02 / W03 wire like W01 (wiring table); W04-a J201; W05-a
J202; insulated receptacles, 4.8 mm tabs (rated far above the 1.6 A peak); W16-b J501 and the
current-loop figures (X33); W17-b J1 IDC-1.27; pads 1-10, 15-24, 26-28 N/C (pad 16 only through
the unfitted R444); pads 11-14 SPI; pad 25 HV_FAULT_N; pads 29-32 PWM; pads 33 / 34 GND = power
ground; pads 35 / 36 3V3 (about 9-12 mA, budget 20); pad 37 HV_PERMIT_STAT; pad 38 HV_ENABLE
(100k pull-down, rising edge clears); pads 39 / 40 +12V (11-16 mA, budget 25; UCC21520 runs from
9.2 V); isolator fail-safe states (unpowered card: PWM and HV_ENABLE low; unpowered HV side reads
fault and no permit); IF-2 marking and the pad 25 contention note; the loop simulation with 60 µs
(passes); raw 420-430 V; ramp energy to the PSU, no brake, latched trip 475 V; ramp range 30 ms - 1 s;
V_ANODE 0-400 V (≈ 403 V at 420 V raw, D14); V_ANODE 0.57 A; V_SCREEN 290-390 V and R26 ∥ R27
gone; V_SCREEN ≤ V_ANODE (D201); HV only after HV_PERMIT AND HV_ENABLE AND no fault; power-up and
unplugged states (N55); power star, one return per feed; fault / RF network next to the raw tabs;
one plated standoff, the others non-plated; 40-pin isolated on the control board; rail row 3.2;
front notch and rear slot for the PSU cables; existing plate holes used where they fall; J1 on the
west edge at y 80-114 opposite J11 (y 84-110); clear of the mains inlet (outline stops at x 632 in
the rear strip); components down, tallest 51 mm (SK 104 with the TO-220) of about 66 mm; 70 °C
(S4); trip current levels are lab parameters (nothing here depends on them); J2 dropped; HV_PERMIT
timing (drivers off < 100 µs).

## S3. Connector refs (interfaces.md section 2)

J101 W01-b (pin 1 B_P, pin 2 B_N = PGND) · J102 W02-a (1 RAW_SS1, 2 GND_PRE1) · J103 W03-a (1 RAW_SS2,
2 GND_PRE2) · J201 W04-a (1 V_ANODE, 2 GND_PWR) · J202 W05-a (V_SCREEN) · J501 W16-b (1 HV_PERMIT+,
2 HV_PERMIT-) · J1 W17-b (IF-2) · H101 plated chassis standoff · R101 / R102 RAW_SS link footprints.
Two-tab connectors use `Blade_Tab_4.8mm_2x_P12mm` (two tabs 12 mm apart for two insulated receptacles).

## S4. Rail currents, losses and 70 °C

| Rail | Steady | Peak | Note |
|---|---|---|---|
| Raw HV (W01) | ≈ 0.48 A at full power (0.40 A x 400 V + 0.1 A x 390 V, 97 %), ≈ 0.3 A at idle; + RAW_SS 20-35 mA | ≈ 0.8 A with 0.57 A / 0.25 A peaks; ≈ 1.2 A for 30 ms on a fast ramp up at full load | ramp-down returns ≈ 6 J per output (30 ms, no load) to the PSU |
| +12V (J1 39 / 40) | ≈ 11 mA at 50 kHz | ≈ 16 mA at 100 kHz | UCC21520 output sides ≈ 6 mA + gate charge 4 x ~24 nC x f_sw (Qg to confirm); brake driver gone (was 20 mA) |
| 3V3 (J1 35 / 36) | ≈ 9 mA | ≈ 12 mA | VCCI 2 x 2 mA, AD7689 ≈ 1.5 mA, op amps 1.2 mA, LM4040 0.8 mA, opto and pull-ups |

Losses at full power, 50 kHz (100 kHz in brackets), from the IKP08N65F5 datasheet's switching
energies (Eon 0.10 mJ, Eoff 0.03 mJ at its 150 °C test point, scaled with the switched current, plus
the output capacitance) and Vce(sat); R_thJC 2.5 K/W assumed (to confirm), TO-220 free air 62 K/W,
local air 80 °C (70 °C + 10 K under the board, an estimate):

| Part | Loss | Cooling | Tj / hot spot |
|---|---|---|---|
| Q201 (bridge 1 high side) | 1.0 W (1.5 W) | SK 104 38.1 mm, ~12 K/W | 95 °C (102 °C) |
| Q202 (bridge 1 low side, mostly the diode) | 0.3-0.4 W | free | 105 °C |
| Q203 / Q204 (V_SCREEN) | 0.3 / 0.1 W | free | 99 °C / 86 °C |
| L201 / L203 | 0.4 W each (copper ≈ 0.35 W at 1.7 Ω, core ≈ 0.05 W) | free | to check with the real part |
| Raw bleeder R103 / R104 | 0.62 W each in 2 W MOX | derated to ≈ 1.6 W at 80 °C | OK |
| Output bleeders R205 / R206 / R211 / R212 | 0.36 W each in 1 W | derated ≈ 0.85 W | OK |
| R204 / R210 2.2 Ω | ≈ 0.27 W | 2 W | OK |
| Electrolytics C101, C201, C206, C204, C209 | ripple heating small | 105 °C parts | at 80 °C local air about 2^2.5 x the rated life: choose a 5,000-10,000 h series |

Board total ≈ 6.7 W at full power, 50 kHz. Every active part is rated ≥ 85 °C (ENV-2); LMV339I,
AD7689B and LM4040A..I are 85 °C parts (5 K above the assumed local air): a 125 °C grade is the
safer choice when the parts are frozen (comparator: TLV1704 class, to check).

## S5. Simulations

| File | Question | Result |
|---|---|---|
| `sim/hvnet.py` | shared averaged network (variants A first pass, B drawn, C option) | — |
| `sim/lc_ac.py` → `lc_ac_results.md` | second LC stage, input filter (ngspice, cross-checked) | second stage at 27.7 kHz, Q 1; input filter peak 0.7-0.9 Ω against −616 Ω (Middlebrook OK) |
| `sim/loop_digital.py` → `loop_results.md` | closed loop with 60 µs, margins, Zout, audio load, ramps | S1 rows 3-6 |
| `sim/discharge.py` → `discharge_results.md` | output fall after HV_PERMIT drops | S1 row 7 |
| `sim/converter_avg.py` → `results.md` | first pass: ramp energy, brake | **superseded** for the brake cases (Q-A''); Q-A / Q-A' still show what a PSU that can't sink would see |
| `mechanical/floorplan.py` → `floorplan.md`, `floorplan_*.svg` | does it fit | no (S2 P-a) |

Still missing (from the first-pass list and the review): **S1 / M15** switching-level model of one
bridge (losses, ripple, bootstrap D_max, diode recovery: the loss table above is a datasheet
estimate); **S3 / M17** ramp-down into the real PSU DC link (the PSU owner's capacitance and DAB
control) and the trip; **S4 / M18** sim/power_stage fed from this converter model; **S5 / M20**
output short and tube arc (2.2 Ω fusible I²t, D201, IGBT survival, 2.0 A trip timing); **S8 / M21**
channel-change sequence with the bias; ADC quantisation and noise in the loop; thermal check of the
real inductor; the floorplan with electrical adjacency (only after N2).

## S6. Floorplan (block level)

`mechanical/floorplan.md`: outlines tried with the parts as drawn (one heatsink, one 100 µF per
bridge) and with the first-pass set; fill = body area / usable area, the packer is first-fit on a
1 mm grid with 2 mm gaps (a necessary condition, not a layout):

| Outline | control block on the bottom | control block (SMD) on the plate side |
|---|---|---|
| base 115 x 150 (x 560-675, y 30-180) | 86 %, 13 blocks left over | 77 %, 8 left over |
| + rear strip x 560-632, y 180-200 | 79 %, 12 left over | 71 %, 4 left over |
| + rear strip + L x 525-560, y 127-200 | 69 %, 5 left over | **62 %, all placed** |

**It does not fit as proposed.** The IGBT heatsink, the two 3 mH inductors (ETD34, 38 x 38 mm, 36 mm
tall), five 500 V electrolytics (D18 / D22, 40-45 mm), two 1 µF / 630 V films, nine 4.8 mm tabs with
insulated receptacles, the fault network and the 2 W axials take the area. Ways out, in order of
preference: (1) the envelope of N2; (2) the SMD control / measurement on the plate side (15 mm free
there; the THT joints are on that side anyway); (3) smaller magnetics at 100 kHz (1.5 mH, ETD29,
twice the switching loss); (4) dropping the input filter L101 / C101 / C102 (the bridges' 50 kHz
ripple then reaches W01 and RAW_SS through the bridge-local capacitors only).

## S7. Interface changes proposed (new in this pass)

| # | What | Why | Boards | interfaces.md |
|---|---|---|---|---|
| N1 | **Pad 16 = ADC_SCK_RET** (HV → card): the AD7689's SCK returned through 33 Ω (R444, fitted only when agreed) on the reserved back channel; pads 15 and 17 stay N/C so it is one wire away from SCK (14) | 20 MHz SPI, or more margin at 10 MHz, needs the clock to come back with the data; pad 16 is two wires from SCK and next to unused wires | HV supplies, control board | 9 |
| N2 | **HV supplies envelope:** x 560-675, y 30-180 **plus** x 560-632, y 180-200 (rear strip, clear of the mains inlet) **plus** x 525-560, y 127-200 (behind the control board, which ends at y 122; about 6 mm to the power amp, to check); **and** SMD parts allowed on the plate side of the HV board (≤ 3 mm) | The power stage does not fit in 115 x 150 mm (S6) | HV supplies, mechanical (coordinating fit check), power amp and control board (neighbours) | 12.1, 12.2 |
| N3 | **Raw rail transient limit:** "During a ramp too fast for the PSU the raw rail may reach the HV supplies' latched trip level, 475 V nominal (≤ 480 V), before the trip stops it; every part on the raw rail and RAW_SS is rated ≥ 500 V" | No brake now (U4): the trip is the limit | preamp, PI + FX, tube PSU, HV supplies | 3.1, 8 |
| N4 | **HV supplies trip thresholds** (PROPOSED in 8): over-current **2.0 A forward and 2.0 A reverse** per bridge (was 1.0 A), raw 475 V, V_ANODE 440 V, V_SCREEN 420 V; bridge current up to 1.25 A on a 30 ms ramp at full load | 0.57 A peaks (E28) plus the fastest accepted ramp | HV supplies (power amp informative) | 3.1, 8 |
| N5 | **f_sw = 50 kHz** fixed, centre-aligned PWM, recommended to the control board (100 kHz allowed) | Loss and heatsink sizing at 70 °C, 12 V budget | control board | 9 |
| N6 | **New plate holes** for the HV board under the PSU: (671, 48), (671, 128) M3 non-plated, and H101 (plated, next to J101, about (630, 160)); used existing: (590.0, 87.0), (605.0, 124.7), (605.0, 166.6) | East-side support and the fault-network standoff | mechanical, tube PSU (clearance on top) | 12.1a |

## S8. Still open

1. N2 envelope (blocks the layout), N3 raw transient limit, N6 holes, Q-d W01 hole.
2. U14 (no active discharge) with the power amp; D13 / D14 unchanged (≈ 403 V at 420 V raw).
3. Part choices: 3 mH inductor (placeholder footprint), bridge fuses with a confirmed ≥ 500 VDC
   rating (5x20 holder is a placeholder; or 6.3 x 32), 2.2 Ω fusible (M20), Y2 capacitor, 500 V
   electrolytic series (105 °C, long life), 1.27 mm shrouded header for J1, R_thJC and Qg of the
   IKP08N65F5, 125 °C grades for the 85 °C parts.
4. Missing simulations S5.
5. Firmware items this board relies on: the loop gains (Kp 2, Ki 1000 /s, Kc 20 Ω at 60 µs, a
   starting point), channel scheduling (Q-b), ramp-down before HV_ENABLE low, the converter current
   limit inside the 2.0 A trip.

## S9. Next steps

1. Coordinating session: N1-N6, Q-a..Q-e.
2. After N2: a floorplan with electrical adjacency (power loops, creepage, the star), then layout.
3. M15 switching model and M20 short / arc; choose the inductor and the fuses.

---

# First pass (2026-11-21, c947e82): history


Session scope (user, 2026-11-21): initial schematic, check every interface choice that touches this
board, list what has been missed (including missing simulations and missing requirements). No
layout. Contract: tube_amplifier_kicad `docs/interfaces.md` IF-1.1 (read at commit 613937b).

**Done:** five generated sheets (README.md), 209 parts, 118 nets, ERC 0 errors / 2 warnings;
averaged converter simulation `sim/converter_avg.py` → `sim/results.md`. Footprints, layout and the
values marked TBD / placeholder are not done.

ERC warnings (both expected): `ground_pin_not_ground` on U301 / U302 pin 14 (VSSA): the UCC21520's
high-side reference is the switch node SW1 / SW2, not a ground. PWR_FLAGs are on PGND, BOOT1 / BOOT2,
SW1 / SW2 (floating gate-drive supplies) and on +3V3 / +12V / GND (they come from J1).

---

## 1. Requirements check: does the v2 topology meet rev B?

v2 (repo root, findings 1-16 in the root STATUS.md): 430 V → 33 µH input filter → two IGBT
half-bridges (IKP08N65F5, synchronous bucks), each with an off-board 3 mH inductor, an intermediate
47 µF (returned through a 4 mΩ shunt), a 33 µH second stage and a 47 µF output; bridge 2 then
R26 ‖ R27 = 500 Ω to VPRE. Four Si8271 drivers (EN tied to 3V3), bootstrap with S1M, PWM straight
from the control card, analog measurements (1/200 dividers, 4 mΩ shunts x 20.6) sent as analog
voltages on J1 pads 1-8 to the card's ADC.

**Verdict: the power topology (two synchronous bucks from the raw rail) is right and is kept. The v2
board does not meet rev B as built; it needs the changes below.** Plainly:

| Requirement | v2 | Rev 3 change and why |
|---|---|---|
| V_ANODE 0 to ~400 V, 0.5 A peak, from 420-430 V (D14) | Buck can reach it, but the bootstrap limits the duty and nothing was sized for 0.5 A | Kept. Bootstrap D_max ≈ 0.97 → about **403 V at 420 V raw and 0.5 A** (0.97 x 420 = 407 V, minus ≈ 1.5 V IGBT and ≈ 2.7 V in the inductors, shunt and the 2.2 Ω tab resistor), about 413 V at 430 V. **D14: 400 V is reachable with 2-3 V margin at 420 V**, if 420 V is the raw rail at full load. Isolated high-side supplies instead of the bootstrap would give 100 % duty (~ raw - 4 V) if more is wanted |
| V_SCREEN up to ~390 V, 100 mA avg / 0.25 A peak (D13) | R26 ‖ R27 = 500 Ω in series (50 V, 5 W at the budget); bridge 2 had a third capacitor | **R26 ‖ R27 removed**; bridge 2 built like bridge 1; a 2.2 Ω fusible in each output (fuse / arc limit, placeholder). Reaches ~400 V like V_ANODE |
| V_SCREEN ≤ V_ANODE (interfaces 3.1) | Firmware only | **Clamp diode D201** from V_SCREEN to V_ANODE: hardware, also during ramps and faults |
| Power scaling per channel with a ramp (PS-2, PS-4, CH-2) | Bidirectional bucks (the low IGBT sinks current) return the output capacitors' energy to the raw rail; nothing absorbs it | **sim Q-A: a 30 ms ramp-down (400→200 V, 390→250 V) pushes the raw rail to 540 V (495 V for 100 ms)** if the PSU can't sink: over the 450 V capacitors. **sim Q-B: without reverse current, V_SCREEN barely moves** (390→352 V in 200 ms: the screens draw only mA at idle). So downward steps need reverse current **and** somewhere for the energy: **raw-rail brake** (470 Ω switched above 445 V, hardware comparator; sim Q-A'': raw held at 445 V), capacitors raised to 500 V. Ramp-up 200→400 V in 30 ms: 0.83 A peak, fine (Q-C) |
| Audio-rate load (0.5 A peaks) | Firmware loop over an analog ribbon | sim Q-D: with 94 µF per output, a voltage-loop crossover of 1 kHz gives ±0.2 V, 300 Hz gives ±1 V. Needs a fast digital loop (below) |
| Measurement accuracy | Analog voltages on J1 to the card's ADC; 4 mΩ shunts x 20.6 = 82 mV/A (41 mV at 0.5 A); LT1014 on 3.3 V (finding 8) | **The 40-pin is now isolated on the control board, so analog lines can't cross it.** Rev 3 digitises on the board: AD7689 (8 ch, 16 bit, 250 kSPS SPI) behind MCP6004 buffers; dividers 0.1 %, 1/201 → 0-500 V into 2.5 V (0.12 V / LSB at 12 bit effective); shunts 50 mΩ x 20 = 1 V/A, ±1.25 A. Accuracy about ±0.5 % + offset (calibrated at HV off) |
| Hardware HV_PERMIT input (SAFE-6) | None (driver EN tied to 3V3) | **Current loop → TLP293 → Schmitt → NAND with HV_ENABLE and the fault latch → UCC21520 DIS** on both bridges. No loop current = drivers disabled, without firmware |
| Standby / HV enable (SAFE-3) | PWM stopped by firmware only | HV_ENABLE (pad 38, 100 k pull-down) in the same hardware AND; bleeders bring the outputs below 60 V in about 40 s (v2: τ = 280 s through the dividers only) |
| Shoot-through, unpowered states | Four independent Si8271: both IGBTs of a bridge can be driven on together; no gate-emitter resistors (gates float with the drivers unpowered); bootstrap diode S1M is standard recovery (1.8 µs) | UCC21520: dead time and overlap block in hardware, 8 V UVLO; 10 kΩ G-E on every IGBT; ES1J ultrafast bootstrap diode |
| Protection | None in hardware | Latched: low-side over-current (1.0 A) per bridge, raw > 475 V, V_ANODE > 440 V, V_SCREEN > 420 V; cleared by HV_ENABLE low → high; reported on HV_FAULT_N. Fuse per bridge input (high-side short) |
| Switch-node wiring | The 3 mH inductors are off-board: the 430 V switch node runs on wires in the chassis, not in the wiring table | **Inductors on the board** (toroid, 1.5 A without saturation; size TBD) |

---

## 2. Interface check (interfaces.md IF-1.1)

38 rows: **27 OK, 6 problems, 5 questions.**

| # | Item (section) | Result | Note |
|---|---|---|---|
| 1 | W01-b B_P / B_N, 4.8 mm tabs (2.1, 4.1) | OK | J101. Up to ~0.8 A peak (both outputs) |
| 2 | W02-a RAW_SS1 + GND_PRE1 (2.1, 4.2) | OK | J102, fuse F101 |
| 3 | W03-a RAW_SS2 + GND_PRE2 (2.1, 4.2) | OK | J103, fuse F102 |
| 4 | 100 mA slow fuse per RAW_SS feed (3.1, 4.2) | **Question** | A 100 mA time-lag fuse rated ≥ 450 VDC was not found in the usual 5x20 ranges (Littelfuse 0477 ceramic is 500 VAC / 400 VDC, from 500 mA in the listing found; 218 series is 250 V). Options: a 100 mA fuse with a confirmed ≥ 450 VDC rating, or a flameproof fusible resistor (e.g. 47-100 Ω, 1-2 W) relying on the regulators' foldback (8-10 mA into a short). User / coordinating decision. Sources checked 2026-11-21: [Littelfuse 0477 (Digi-Key)](https://www.digikey.com/en/products/detail/littelfuse-inc/0477-500MXP/1979187), [Littelfuse 0977, 500 VAC / 450 VDC (Digi-Key)](https://www.digikey.com/en/products/detail/littelfuse-inc/0977-500MXP/2664857), [Littelfuse 218](https://littelfuse.com/products/fuses/cartridge-fuses/5x20mm-fuses/218/218_1.aspx) |
| 5 | W04-a V_ANODE + GND_PWR (2.1) | OK | J201 |
| 6 | W05-a V_SCREEN, one tab, return through GND_PWR (2.1) | OK | J202 |
| 7 | Receptacles fully insulated, tab widths (4.1) | OK | |
| 8 | W16-b HV_PERMIT, Lock-2.54 2-pin, 5-10 mA loop (2.2, 8) | OK | J501. Turn-on above about 3.5-4 mA loop current (680 Ω across the LED takes ~1.8 mA), off below ~2 mA; 24 V TVS; reverse diode; opto isolates the power amp's DGND from this board |
| 9 | HV_PERMIT timing (8) | **Question** | No number for the loop-off → HV-off time. This board disables the drivers in < 100 µs (opto + 10 µs RC + logic); the outputs then fall with the load and bleeders. Need a requirement (R4) |
| 10 | W17-b J1 IDC-1.27 2x20, standard numbering (2.2, 9) | OK | Ref J1 kept |
| 11 | J1 pads 1-8 analog measurements (9) | **Problem** | The link is isolated on the control board, so analog voltages can't cross it without 8 isolation amplifiers there. Proposal P1: digitise on this board, pads 1-8 unused |
| 12 | Pad 7 → V_SCREEN_MEAS (9, proposed) | **Problem** | Superseded by P1: V_SCREEN is ADC channel IN3 (same position in v2's order) |
| 13 | Pads 12 / 26 SCL / SDA (9) | **Problem** | No I2C on rev 3 (v2's ADC121C027 and J2 dropped). P2: pad 12 = ADC_SDO; pad 26 unused |
| 14 | Pads 9-11, 13, 14 ADASEL / CS1 / CLK1 (9) | **Problem** | Unused on v2's HV side. P2: pad 11 ADC_DIN, 13 ADC_CNV, 14 ADC_SCK |
| 15 | Pads 29-32 PWM G1_LO / G3_LO / G1_HI / G3_HI (9) | OK | Unchanged: 29 PWM_L1, 30 PWM_L2, 31 PWM_H1, 32 PWM_H2 (bridge 1 = V_ANODE, bridge 2 = V_SCREEN); 10 k pull-downs; the driver blocks overlap anyway |
| 16 | Pad 37 HV_PERMIT_STAT (9, proposed) | OK | = loop current present (filtered). P5: drop "and the drivers are enabled" from the definition (that is pad 37 AND pad 38 AND pad 25, known to the firmware) |
| 17 | Pad 38 HV_ENABLE, pull-down, ANDed with HV_PERMIT (9, proposed) | OK | 100 k pull-down. P6: its rising edge also clears the fault latch |
| 18 | Fault reporting / clearing (8, 9) | **Problem** | No pin for a hardware fault. P4: pad 25 = HV_FAULT_N |
| 19 | Pads 33 / 34 GND = this board's power ground (5, 9) | OK | GND joins PGND at the shunts (NT501), one tie |
| 20 | Pads 35 / 36 3V3 (3.2, 9) | OK | About 12 mA (budget 20 mA), section 4 |
| 21 | Pads 39 / 40 12V (3.2, 9) | OK | About 20 mA (budget 25 mA). Net renamed +12V (v2 `15V_BOOST`, finding 2). Needs ≥ 9 V at the board (UCC21520 UVLO 8 V); 12 V gate drive is fine for the IKP08N65F5 |
| 22 | J1 logic level 3.3 V (9) | OK | All J1 logic on this board is 3.3 V CMOS |
| 23 | Raw HV 420-430 V (3.1) | OK | Input caps raised to 500 V (v2: 450 V) |
| 24 | Raw rail behaviour under regeneration (3.1, 8 "DAB inhibit") | **Problem** | Not in interfaces.md: whether the PSU sinks current, its output capacitance and OVP level. Without a sink the brake is required (sim Q-A). P11 |
| 25 | V_ANODE 0-400 V (3.1, D14) | OK | 0 to ~403 V at 420 V raw, ~413 V at 430 V (section 1) |
| 26 | V_SCREEN 290-390 V, 100 mA / 0.25 A, R26 ‖ R27 gone (3.1, D13) | OK | 0 to ~400 V; hardware OV trip at 420 V (adjust when D13 is fixed) |
| 27 | V_SCREEN at most V_ANODE (3.1) | OK | D201 clamp |
| 28 | HV only after HV_PERMIT and the card's enable (3.1, 3.4, 8) | OK | Hardware AND |
| 29 | Power-up: card absent / J1 unplugged with raw HV present (3.4, 6.2 rule) | OK | No 3V3 / 12V → drivers in UVLO, gates held off by 10 k G-E, outputs bleed to 0; brake can't fire (IN+ pulled down) |
| 30 | Power star, one return tab per feed (5, grounding §3, §7) | OK | GND_STAR: output caps, J102-2, J103-2, J201-2, fault network; PGND joins it only at NT101 |
| 31 | Fault / RF network to a chassis standoff near the raw tabs (5) | OK | D102 GBU8J (+ and - joined) ‖ C106 100 nF Y2 ‖ R104 100 Ω 2 W to H101 (plated). The other holes must be **non-plated** (a plated hole on a grounded standoff would be a second chassis bond) |
| 32 | 40-pin isolated on the control board (5, 9) | OK | Nothing on this board refers to DGND |
| 33 | Rail budget row (3.2) | OK | Section 4 |
| 34 | Envelope x 530-630, y 30-202 (12.1) | OK | Area is ample (estimate: ~60 % used incl. two 3 mH toroids and the brake resistor heatsink) |
| 35 | Component height / mounting side (12.2) | **Question** | Only the tube boards' 15 mm standoffs with components toward the plate are defined. This board can't work that way (500 V elkos Ø18 x 35 mm, 3 mH toroids ~45 mm, TO-220 heatsinks). Proposal P10: components facing down (toward the chassis floor), 82.5 - 15 = ~65 mm available |
| 36 | PSU cables through the holes at (658.5, 28.6) / (658.5, 154.6) (12.1) | **Question** | Outside the envelope (x ≤ 630): raw HV leads run ~30 mm to J101; put J101 / J102 / J103 at the right edge, near y 150 if the raw HV comes down the rear hole. Which hole carries W01? |
| 37 | Connector positions (12.3) | OK | J1 and J501 at the left (control board) end, RAW_SS tabs next to B_P / B_N, V_ANODE / V_SCREEN toward the power amp |
| 38 | HV supplies J2 16-pin (2.3, 14, OPEN) | **Question** | Proposal P9: drop it (no inputs need it); close the OPEN item |

---

## 3. Interface changes proposed (to the coordinating session)

| # | What | Why | Boards | interfaces.md |
|---|---|---|---|---|
| P1 | J1 pads 1-8: analog measurements → **unused (N/C)**; the 8 measurements are digitised on the HV board | Analog can't cross the decided isolation on the control board (alternative: 8 isolation amplifiers on the control board) | HV, control board | 9 |
| P2 | ADC SPI on J1: pad **11 ADC_DIN** (card → HV, was ADASEL0_ISO), **12 ADC_SDO** (HV → card, was SCL / SDATA1_ISO), **13 ADC_CNV** (card → HV, was CS1_ISO), **14 ADC_SCK** (card → HV, was CLK1_ISO); pad 26 unused. AD7689, SPI mode 0, ≤ 20 MHz through the isolators, 250 kSPS round robin (31 kSPS per channel). Channel order IN0..7 = V_ANODE, RAW, UC1 (bridge 1 intermediate), V_SCREEN, I_Q12 (bridge 1 low side), I_Q22, I_C24 (bridge 2 capacitor), I_C14 | Digital measurement path (P1); same order as v2's pads 1-8 | HV, control board (isolators: 3 forward + 1 back) | 9 |
| P3 | No I2C on J1 (pads 12 / 26 names SCL / SDA and SDATA1 / MDATA retire) | v2's I2C ADCs and J2 dropped | HV, control board | 9 |
| P4 | Pad **25 HV_FAULT_N** (HV → card, 3.3 V, low = latched hardware fault: over-current or over-voltage; set at power-up) | The card must know why HV stopped, and the latch needs a defined clear | HV, control board | 8, 9 |
| P5 | Pad 37 HV_PERMIT_STAT = the HV_PERMIT loop is on (filtered) | "drivers enabled" also depends on pads 38 and 25 | HV, control board | 9 |
| P6 | Pad 38 HV_ENABLE: drivers run only when HV_PERMIT AND HV_ENABLE AND no fault; a rising edge on HV_ENABLE clears the fault latch | Defined restart after a trip | HV, control board | 8, 9 |
| P7 | Rail figures: +12V (pads 39 / 40) about 20 mA (25 mA budget), 3V3 (pads 35 / 36) about 12 mA (20 mA budget); net name 12V | Section 3.2 row "rev 3 currents OPEN"; sizes the control board's isolated supply | control board | 3.2, 9 |
| P8 | Connector refs: J101 (W01-b), J102 (W02-a, pin 1 RAW_SS1, pin 2 GND_PRE1), J103 (W03-a), J201 (W04-a, pin 1 V_ANODE, pin 2 GND_PWR), J202 (W05-a), J501 (W16-b, pin 1 HV_PERMIT+, pin 2 HV_PERMIT-), J1 (W17-b) | Replace the P- refs | — | 2, 4.3 |
| P9 | HV supplies J2 (16-pin) dropped | Nothing needs it | — | 2.3, 14 |
| P10 | HV supplies mounting: components facing down (away from the plate), ≥ 50 mm component height; only H101 plated (the fault network's chassis standoff), other holes non-plated | Parts don't fit 15 mm; a plated hole on a standoff would be a second chassis bond | HV, mechanical | 12.2, 12.3, 5 |
| P11 | Raw rail: the HV supplies return energy when an output ramps down; rev 3 has a raw-rail brake (on above 445 V) and a latched trip at 475 V. Ask the tube PSU session: can the DAB sink current, its output capacitance and its OVP level | sim Q-A: 540 V on the raw rail without a sink | HV, tube PSU | 3.1, 8 |
| P12 | V_SCREEN ≤ V_ANODE enforced in hardware (clamp diode); HV_PERMIT / HV_ENABLE gate both outputs together | Interfaces 3.1 "at most V_ANODE" | power amp (informative) | 3.1, 8 |

Until accepted, the J1 drawn in sheet 05 follows these proposals (pads 33-40 and 29-32 are as DEFINED).

---

## 4. Rail currents (interfaces.md 3.2)

| Rail | Steady | Peak | From |
|---|---|---|---|
| Raw HV (W01) | ≈ 0.3 A at idle (power amp idle at the setting) + RAW_SS 20-35 mA | ≈ 0.55 A V_ANODE + 0.25 A V_SCREEN (x V_out / V_raw) + 35 mA; brake pulses ~1 A for ~30 ms | power stage sim, interfaces 3.3 |
| +12V (J1 39 / 40) | ≈ 15 mA (UCC21520 output sides ~8 mA, gate charge ~1.5 mA per IGBT at 50 kHz, UCC27511) | ≈ 22 mA at 100 kHz | estimate (IKP08N65F5 Qg to confirm) |
| 3V3 (J1 35 / 36) | ≈ 12 mA (UCC21520 VCCI ~5 mA, AD7689 ~2-3 mA, 12 op amps ~1.2 mA, LM4040 bias 0.8 mA, comparators, pull-ups, opto) | ≈ 14 mA | estimate |
| +15 / +5 / -15 / heaters / -80 V | — | — | not used |

---

## 5. What has been missed (ranked)

1. **Analog measurements can't cross the isolated 40-pin** (P1, P2): the decided isolation on the
   control board makes v2's J1 pads 1-8 useless; the measurement path must be redefined now, both
   boards depend on it.
2. **Ramp-down energy has nowhere to go** (sim Q-A): a bidirectional buck returning 5-6 J per output
   into 156 µF lifts the raw rail to 495-540 V (450 V capacitors in v2, 420-430 V parts elsewhere on
   the raw rail: the preamp and PI + FX regulators also see it through RAW_SS). Rev 3 adds a brake
   and 500 V capacitors; the PSU's sink capability is unknown (P11).
3. **V_SCREEN can't ramp down on its own** (sim Q-B): the screens draw milliamps at idle, so a lower
   screen setting on a channel change needs reverse current (and the brake), otherwise the screen
   stays high while the anode drops (now clamped by D201, but the setting is still wrong).
4. **Mounting side and component height are undefined for this board** (P10); with 15 mm standoffs
   and components toward the plate nothing fits.
5. **The RAW_SS fuse doesn't exist in the assumed form** (row 4): a 100 mA slow fuse needs a DC rating
   ≥ 450 V and a breaking capacity for a 430 V capacitor-backed short.
6. **The 33 µH / 47 µF second stage resonates at about 4 kHz** (1 / 2π√(33 µH · 47 µF)), inside the
   audio band and near the needed loop crossover: output impedance peaking, damped only by the
   electrolytic's ESR and the 2.2 Ω tab resistor. Needs a simulation (S6) before the values freeze.
7. **No hardware inhibit / fault path existed** on v2 (EN tied high), no fault pin on J1 (P4), and
   v2's gate drive was unsafe when unpowered (no G-E resistors), allowed shoot-through, and used a
   standard-recovery bootstrap diode.
8. **Off-board 3 mH inductors** carried the 430 V switch node on chassis wiring and were not in the
   wiring table; rev 3 puts them on the board.
9. **HV discharge** was undefined (v2: 280 s time constant through the dividers); rev 3 bleeds the
   outputs to < 60 V in ~40 s and the raw caps in ~50 s, with HV-present LEDs (R5 requirement).
10. **Plated mounting holes** would make extra chassis bonds; only the fault network's standoff may be
    plated (P10).
11. **The PSU cable holes are outside the envelope** (row 36): fine, but the raw HV lead length and
    which hole it uses should be in the wiring table.
12. **Brake resistor duty**: 5-12 J per downward step; frequent channel changes (e.g. every second)
    mean 5-12 W average in R101: the brake needs a rating decision (S8) and an over-temperature limit
    in firmware (or a minimum time between downward steps).

### 5a. Missing simulations

| # | Simulate | Question it answers | Input it needs |
|---|---|---|---|
| S1 | Switching-level model of one bridge (IGBT models, 3 mH with DCR and saturation, dead time, bootstrap) at 40-100 kHz | f_sw choice, ripple on V_ANODE / V_SCREEN, losses and heatsinking, bootstrap D_max (D14 margin), body-diode recovery | Infineon IKP08N65F5 SPICE model, inductor data, f_sw range from the control card |
| S2 | Closed-loop digital control with the real latency (AD7689 round robin 31 kSPS per channel, isolator delays, PWM update) | Can the firmware loop reach the 300 Hz-1 kHz crossover that sim Q-D needs? Else: analog loop on the board | Control card PWM / ADC timing, firmware loop structure |
| S3 | Ramp and brake with the real tube PSU output (capacitance, whether the DAB sinks, OVP) | Brake size, whether the PSU trips on regeneration | Tube PSU 5.2 output stage data (P11) |
| S4 | Power stage (sim/power_stage) fed from this supply model instead of the stiff 5 Ω / 100 µF | Sag / compression at the power settings; output capacitor sizing; whether 94 µF is enough | sim/power_stage tube currents, S2 loop |
| S5 | Output short / tube arc: 94 µF + 33 µH + 2.2 Ω fusible into a short, protection timing | Fusible resistor I²t, IGBT survival, the 1 A OC trip | S1 model |
| S6 | Second-stage LC (33 µH / 47 µF, f0 ≈ 4 kHz) with ESR and the tube load inside the voltage loop | Output impedance peaking in the audio band; damping network or different values | Electrolytic ESR, S2 |
| S7 | Brake thermal duty | R101 rating and heatsink; firmware rate limit | Expected channel-change rate (user) |
| S8 | V_SCREEN ramp-down on a real channel-change sequence with the bias change (PS-3) | Order of bias / screen / anode changes inside the 30 ms mute | Firmware sequence, bias supply response (power amp session) |

### 5b. Missing or vague requirements (proposed wording for SPECIFICATION.md)

| # | Topic | Proposed wording |
|---|---|---|
| R1 | Setpoint accuracy | "V_ANODE and V_SCREEN are set to within ±1 % or ±2 V of the commanded value (whichever is larger), with a resolution of 1 V or better, over 100 V to maximum." |
| R2 | Dynamic regulation | "Under the power stage's audio load (0.5 A peak on V_ANODE, 0.25 A peak on V_SCREEN, 20 Hz-5 kHz) each output stays within ±5 V of its setpoint; source impedance ≤ 5 Ω in the audio band (the power stage simulation's assumption)." |
| R3 | Ramp rate (PS-4 "TBD") | "A power-setting change is complete within X ms (proposed 100 ms up and down), without overshoot above 2 %; whether it must finish inside the 30 ms channel-change mute (CH-4) is stated." User decision |
| R4 | Inhibit timing (SAFE-6) | "HV_PERMIT loop off (or HV_ENABLE low, or a trip) disables both bridges within 1 ms." Whether the outputs must also be actively discharged on inhibit (they fall with the tube load and bleeders) |
| R5 | Discharge (SAFE-4) | "Every HV node on the HV supplies is below 60 V within 60 s after the raw HV is removed; an HV-present indicator is visible on the board." |
| R6 | Raw-rail limits | "No board raises the raw rail above 450 V; the tube PSU states whether it sinks current, its output capacitance and its over-voltage trip." |
| R7 | Fault limits | "A short of V_ANODE or V_SCREEN to GND_PWR, or an output above its limit, shuts the bridge down within 100 µs and latches until HV_ENABLE is cycled; nothing is damaged." Limits: V_ANODE 1.0 A, V_SCREEN 1.0 A (TBD), over-voltage 440 V / 420 V |
| R8 | Switching ripple | "Ripple at the switching frequency ≤ 0.5 V p-p on V_ANODE and ≤ 0.2 V p-p on V_SCREEN; switching frequency fixed, ≥ 40 kHz." |
| R9 | Minimum output | "Regulated from 100 V (lowest power setting, PA-6 'minimum scaled power TBD') to maximum; below that only off." |
| R10 | Environment | "Internal chassis ambient up to 60 °C at full power (the tube PSU sits above this board)." |
| R11 | Creepage (SAFE-4 "values TBD") | "PCB creepage ≥ 2.5 mm between 430 V nets and low-voltage nets, ≥ 1.5 mm between HV nets of different potential (IPC-2221B, uncoated, 301-500 V)." |
| R12 | Measurement rate | "Each output voltage and converter current is available to the firmware at ≥ 25 kSPS." |
| R13 | Unplugged / unpowered states | "With J1 unplugged, the control board unpowered, or W16 unplugged, both outputs are off and bleed to 0 V; the raw rail is passed through to RAW_SS unconditionally." |
| R14 | RAW_SS protection | "Each RAW_SS feed is fused (or current-limited) for a wiring fault at 430 V DC, with a part rated for that DC voltage and breaking capacity." |

---

## 6. Open questions / user decisions

1. **D14** (V_ANODE max): the design gives ~403 V at 420 V raw and 0.5 A (bootstrap, D_max 0.97); 400 V
   is reachable. Accept, or ask for isolated high-side supplies (~415-425 V)?
2. **D13** (V_SCREEN range): designed 0 to ~400 V, hardware over-voltage trip at 420 V.
3. **Ramp rate (R3)** and whether downward steps must finish within the 30 ms mute: decides the
   brake size (S7) or a slower down-ramp.
4. **Brake vs PSU sink** (P11): if the tube PSU's DAB can sink, the brake shrinks to an OV backstop.
5. **RAW_SS fuse part** (row 4): fuse with a confirmed DC rating, or a fusible resistor.
6. **J1 changes P1-P6** with the control card session.
7. **Mounting side / height** (P10) and which PSU hole carries W01.
8. Bootstrap diode, f_sw, inductor size: after S1.

## 7. Next steps

1. Agree P1-P12 with the coordinating session; update sheet 05 if the J1 pinout changes.
2. S1 (switching model), S2 (control latency), S6 (LC damping) before freezing values.
3. Part selection: inductors (3 mH / 1.5 A toroid on the board), 500 V electrolytics, Y2 capacitor,
   fuses, brake resistor; footprints.
4. Layout after the mounting side is decided.
