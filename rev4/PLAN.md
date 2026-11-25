# HV supplies rev 4: plan (draft, 2026-11-25)

A restart of the redesign from v2 (`kicad/` at the repo root). rev3 (`rev3/`) grew too complicated
(TCM soft switching, on-board ETD39 inductors, IGBTs on the chassis plate, six ADS7056 / IF-2.2,
an L-shaped 192 cm² outline) and is kept as history only. Goal: a board close to v2 in content and size.

## 1. Decisions so far (user, 2026-11-25)

| # | Decision |
|---|---|
| D1 | Start again from v2; target roughly the v2 size (v2: 170 x 56.5 mm, 96 cm²) |
| D2 | **All protection in the FPGA.** No comparators, latch or trip hardware on the board |
| D3 | **No HV_PERMIT hardware gate.** HV_PERMIT is only reported to the FPGA (HV_PERMIT_STAT) |
| D4 | Main inductors: two 2 mH Fe-Si-Al toroids (32 mm OD, 16.4 mm thick, 0.8 mm wire, 6 A, leads 16.4 mm apart) **on the top side of the board**, as in v2 |
| D5 | Two synchronous bucks, **constant frequency about 50 kHz, 180° apart** |
| D6 | **Bidirectional current measurement** (the output ramps down by reversing the inductor current) with fast front ends: the switched current is sampled at chosen instants |
| D7 | **Two TMUX1308 + ADS7056 chains, one per bridge**; the inductor current from the low-side shunt in one half period, the capacitor current in the other |
| D8 | **Mux address lines driven directly by the FPGA** (no counter on the board) |
| D9 | **Center-aligned PWM**, so the sample instants are fixed (carrier valley and peak) and both ADC chains share CS, SCLK and the mux address |
| D10 | Folder `rev4/`; a rectangle of about **115 x 88 mm** (101 cm²) in the envelope's main body (chassis x 560-675, y 39-127) instead of v2's 170 x 56.5, which does not fit the envelope |
| D11 | **The IGBTs are heatsinked to the chassis.** Thermal sizing to the average load: a 100 W instrument amplifier with a peak-to-average ratio of about 6, so the average output is about 17 W |
| D12 | **The four TO-220s stand in a row along the board's east edge, tabs screwed (insulated) to the chassis east side wall** (x 675). No plate holes or bars under the tube PSU; the devices can be serviced without removing the PSU. The chassis has a metal east side wall (user, 2026-11-25) |

## 2. Block list

| Block | Content | From v2 |
|---|---|---|
| Raw input | B_P / B_N blade tabs (W01), bulk electrolytics, 33 µH, 1 nF snubbers | as v2 |
| Raw distribution | RAW_SS1 / RAW_SS2 blade tabs with GND_PRE returns (W02 / W03), a 0 Ω link footprint in each | new (ICD) |
| Bridges | 2 x half bridge IKP08N65F5, TO-220 with the tabs on the chassis (insulated), low-side emitter shunts | v2 had them free-standing on the board |
| Main inductors | 2 x 2 mH toroid, top side, real footprints: 2 holes 16.4 mm apart, a 32 mm courtyard, two cable-tie slots | v2 had loose wire pads only |
| Filters | first-stage cap with its current shunt, second-stage LC on both outputs; **both bridges measure the first-stage cap** | v2 bridge 2 measured the second-stage cap (C6) and had R26‖R27 500 Ω: both go |
| Outputs | V_ANODE / GND_PWR (W04), V_SCREEN (W05) blade tabs; bleeders (no active discharge, ICD) | terminals → blade tabs |
| Gate drive | 4 x Si8271 with bootstrap from the link's +12 V, HV_ENABLE on the EN pins | as v2; the unfinished 15 V supply is gone |
| Current sense (x4) | 50 mΩ low-inductance shunt (wide-terminal), Kelvin sense, OPA2836 difference amp next to the shunt, reference = buffered AVDD/2 | replaces the 4 mΩ / LT1014 / shared 220 Ω bias |
| Voltage sense | dividers for V_ANODE, V_SCREEN, UC1, UC2 and two independent RAW dividers, buffered | replaces U1 / the 3 MΩ dividers |
| ADC | 2 x (TMUX1308 → driver → ADS7056), REF3030 as AVDD (3.0 V), buffered 1.5 V midpoint | replaces the analog ribbon, ADC1-ADC3, J2 |
| HV_PERMIT | W16 current loop into an optocoupler → HV_PERMIT_STAT | status only (D3) |
| Grounding | star point; fault / RF network (bridge ‖ Y2 ‖ 100 Ω) to one plated mounting hole as the chassis bond | per grounding.md |
| Link | J1 40-pin 1.27 mm (W17), section 4 | new pad table |

## 3. Measurement

### 3.1 Current front end (x4)

- Shunt 50 mΩ, wide-terminal (0612 / 1225 class) for low inductance: L/R corner about 8 MHz at 1 nH.
  A 4 mΩ 0508 (v2) has its corner near 640 kHz and reads di/dt spikes, not current.
- 4-terminal shunt or net-ties at the pads; the sense pair as a tight differential pair to the amplifier,
  which sits next to the shunt.
- OPA2836 (205 MHz GBW, rail-to-rail output, 3.3 V) as a difference amplifier, gain 7.5, resistors of a few hundred Ω to 1 kΩ,
  closed loop at least about 10 MHz; settles to 1 % within about 0.5 µs of a switching edge.
- Scaling 50 mΩ x 7.5 = 0.375 V/A around 1.5 V: **±4 A into 0-3 V**. Offset binary: zero current = mid-code.
- Signs: the low-side shunt carries the inductor current through the whole off-interval, negative in
  forward flow (diode), positive in reverse flow (IGBT); the FPGA inverts it. Reverse flow needs true
  synchronous drive (low side gated on during the off-interval).
- A reading at either end of the range is a trip (the FPGA cannot tell how far past full scale it is).

### 3.2 Sampling (center-aligned PWM)

The inductor current is a symmetric triangle, so its value at the middle of the on- or off-interval is
its average, and the two middles are exactly T/2 apart. **With center-aligned PWM** the middles sit at
fixed points (carrier valley and peak) for any duty cycle, and with 180° between the bridges bridge 1's
mid-off falls on bridge 2's mid-on and back. Both ADCs then convert at the same two instants, so they
**share CS, SCLK and the mux address lines**, with one SDO each. (With edge-aligned PWM the instants move with
the duty cycles and the two chains need separate CS and address lines.)

| Mux address | ADC 1 (bridge 1, V_ANODE) | ADC 2 (bridge 2, V_SCREEN) | When |
|---|---|---|---|
| 0 | I_L1 (Q low-side shunt) | I_C2 (first-stage cap shunt) | carrier instant A |
| 1 | I_C1 | I_L2 | carrier instant B = A + 10 µs |
| 2 | V_ANODE | V_SCREEN | gap |
| 3 | UC1 (first-stage cap voltage) | UC2 | gap |
| 4 | RAW (divider 1) | RAW (divider 2) | gap, every period (ramp-down governor) |
| 5 | 1.5 V midpoint | 1.5 V midpoint | gap: offset check and mux-channel proof |
| 6 | NTC, bridge 1 devices | NTC, bridge 2 devices | gap (optional) |
| 7 | spare | spare | |

Budget per 20 µs period: one ADS7056 frame is 18 SCLK = 1.8 µs at 10 MHz over the isolators, about
2.2-2.5 µs with the mux and driver settling; 2 timed + up to 6 gap conversions fill the period at 10 MHz,
so read the slow channels in rotation, or run 20 MHz / the returned clock. Tightest window: the
low-side off-interval at V_ANODE 400 V from 420-430 V (D 0.93-0.95) is 1.0-1.4 µs, sampled in its middle.

### 3.3 Raw rail

Reverse current returns through the high-side diodes into the raw rail. If the PSU's DAB doesn't sink
it, RAW rises (rev3 m17: peaks 436-447 V on ramp-downs). With protection in the FPGA (D2), RAW is a
control input: the firmware slows or pauses a ramp-down as RAW nears its limit and stops switching above
a trip level. Two independent RAW dividers, one per ADC.

## 4. Link (W17, J1 40-pin), proposal

| Direction | Signals | Count |
|---|---|---|
| card → HV | PWM_H1, PWM_L1, PWM_H2, PWM_L2 (pull-downs), HV_ENABLE (100k pull-down, to the driver EN pins), ADC_SCLK, ADC_CS, MUX_A0, MUX_A1, MUX_A2 | 10 |
| HV → card | ADC_SDO1, ADC_SDO2, ADC_SCK_RET (optional), HV_PERMIT_STAT | 3-4 |
| power | 3V3, +12V (from the isolated supply on the control board), GND between the fast lines | |

Fewer isolator channels than IF-2.2 (9 forward / 10 back). The pad numbers come with the schematic.

## 5. Floorplan (first block check)

`mechanical/floorplan.py` → `mechanical/floorplan.png` (chassis mm, seen from above). Board **x 562-677,
y 39-127 (115 x 88 mm, 101 cm²)**, 10 mm east of the control board, 1 mm from the east wall's inner face
(assumed x 678: 680 plate, 2 mm wall; to be measured). With filter variant D (O4) the big parts' bounding
boxes take **57 %** of the board (39 % with the v2-like filter), no overlaps, four M3 standoff positions clear.
Film sizes assumed: 10 µF / 500 V Vishay MKP1848C 32 x 18 mm (27.5 mm pitch, 28 mm tall); 4.7 µF / 500 V the same
series at about 32 x 13 mm (to confirm; the TDK 4.7 µF / 630 V is 31.5 x 22 mm); 100 µH about 13 x 13 mm.

- **East edge:** QL2, QH2 (bridge 2, V_SCREEN, front) and QH1, QL1 (bridge 1, V_ANODE, rear) standing with
  the tabs on the wall; the input cap between the two high-side collectors; gate drivers, bootstrap
  and low-side shunts with their amplifiers in the strip behind them (plate face).
- **Middle:** the two 2 mH toroids standing on edge (x 636-654), then per output the first-stage 47 µF and
  the 22 µF damping leg, the 100 µH, and the two films toward the west (bridge 1 in the rear half, bridge 2 in
  the front half). The measurement block sits on the plate face under the films' bodies, between their
  leads, next to J1 (HV clearance to the film leads in the layout).
- **Front edge:** B_P / B_N at the east end under the PSU's front cable hole (W01), input L and cap, the
  four RAW_SS / GND_PRE tabs at the west end (W02 / W03 leave forward, as in rev3).
- **Rear edge:** V_ANODE, V_SCREEN, GND_PWR at the west end, toward the power amp's tabs (W04 / W05).
- **West edge:** J1 facing the control board's J11, J501 (W16), the measurement block next to J1.
- TO-220 leads land at about x 675.3, so the board edge sits at x 677 (the rev3 envelope ended at 675).

## 6. Open items

| # | Item | Lean |
|---|---|---|
| O1 | Chassis fit of the board (section 5) with the coordinating session; the east wall's inner face and thickness (measure); standoff positions | — |
| O2 | East-wall mounting details (D12): insulating washer and bush, creepage to the wall, the device height below the board against the wall (board 15 mm below the plate, components down), lead length to the gate drivers; loss check at the average load and at the ICD's worst case (V_ANODE about 0.7 A for minutes) | — |
| O3 | Gate drive from the link's 12 V: the high side gets about 11 V after the bootstrap diode; the IKP08N65F5 is specified at 15 V | check Vce(sat) / switching at 11-12 V; small boost only if needed |
| O4 | Filter values. **First check done** (`sim/ripple.py`, `sim/ripple_results.md`): the second stage's attenuation at 50 kHz is set by the output capacitor's impedance against L2, so electrolytic ESR dominates. v2-like values (33 µH / 47 µF el) give 4-20 mV p-p typical but up to 175 mV with cold ESR (R8 met, the proposed 20 mV not). **Candidate D:** first stage 47 µF el + 4.7 µF film; L2 100 µH; output 10 µF film + damping leg 22 µF el + 2.2 Ω: **≤ 3.3 mV typ, ≤ 5.2 mV cold** at every point, second resonance 4.4-4.9 kHz at 2.5-2.8 Ω. The first resonance (2 mH with the first-stage C, about 390 Hz, 23-27 Ω open loop) must be damped by the loop with the I_C measurement. Still to check: the toroid's inductance under DC bias, the 100 µH part (current, insulation), film / electrolytic ripple ratings, the loop | candidate D |
| O5 | Ramp-down current and the raw rail with a CCM buck (section 3.3) | simulate once with the PSU's DC link |
| O6 | Si8271 vs a dual isolated driver (UCC21520) per bridge | Si8271 (proven on v2) |
| O7 | The ADC SCLK rate over the control board's isolators | 10 MHz plain, 20 MHz or the returned clock if the gap channels are wanted every period |

## 7. Interface changes (tube_amplifier_kicad docs/interfaces.md, section 13)

- Section 8: HV_PERMIT is no longer a hardware gate (SAFE-6 wording); no fault latch, no hardware trips;
  HV_ENABLE stays as the driver enable with its pull-down (fail-safe state: card off → HV off).
- Section 9: the IF-2.2 pad table is replaced by section 4 above (two ADS7056 behind muxes, shared CS /
  SCLK / address, two SDO); the AD7689, CS_FAST timing rules and the six data lines go.
- Section 12: the outline becomes the ~115 x 88 mm rectangle (D10, O1); the rev3 standoff holes are
  withdrawn; the bridge devices' chassis mounting (eight countersunk plate holes and two bars in rev3)
  is withdrawn: the devices go to the east side wall (D12), which the chassis work list gets (four tapped or M3 clearance holes in the wall).
- Sections 2 / 4 (tabs, RAW_SS, links, ratings) and 5 (grounding) stay.
