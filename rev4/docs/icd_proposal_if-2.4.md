# Proposed ICD change IF-2.4 (HV supplies rev 4), draft 2026-11-27

From: HV supplies session (tube_hv_supplies_kicad, `rev4/`). To: the coordinating session, which edits
`tube_amplifier_kicad/docs/interfaces.md` (ICD section 13: board sessions propose, the coordinating
session edits). **Status: draft for the user's review.** Nothing in interfaces.md has been edited.

## What and why

The HV supplies redesign restarted from v2 as **rev 4** (user, 2026-11-25), because rev 3 had grown too
complicated: TCM soft switching, IGBTs on bars on the plate, six ADS7056 converters, and an L-shaped 192 cm²
outline. rev 3 is now history only. Every rev 3 entry in the ICD that describes the HV supplies is therefore
superseded: the IF-2.2 pad table, the proposed IF-2.3, the outline, the standoffs, the plate holes and bars,
the hardware trips and the fault latch.

User decisions behind this change (`rev4/PLAN.md` section 1, all 2026-11-25 unless marked):

- D2 all protection in the FPGA, with no trip hardware on the HV board.
- D3 HV_PERMIT is reported only, not a hardware gate.
- D5 / D9 two synchronous bucks at a fixed ~50 kHz, center-aligned, 180° apart.
- D7 / D8 two TMUX1308 + ADS7056 chains, mux address driven by the FPGA.
- D10 a 115 x 88 mm rectangle.
- D12 TO-220s screwed to the chassis east wall.
- D18 Si8271DB drivers with a 15 V boost.
- D19 link budgets raised.
- D20 (2026-11-27) W17 uses the rev 4 table, not IF-2.3; the control board's link 3V3 comes from a buck.

Boards touched: **HV supplies rev 4 and the new control board** (W17 and the W17 isolators only; the
control board's buck replaces its LM1117). Other boards are touched only through positions and cable routes
(W01-W05, W16), mechanically. No other cable changes.

---

## Section 13: new row

| **IF-2.4 for W17 (2026-11-27; decisions [USER] 2026-11-25 / 27, HV supplies rev 4):** replaces IF-2.2's table and withdraws the proposed IF-2.3 (section 14). Two ADS7056 converters, each behind an 8:1 TMUX1308, one chain per bridge; **shared ADC_CS (15) and ADC_SCK (14)**; mux address **MUX_A0 / MUX_A1 / MUX_A2 on pads 11 / 13 / 12**, driven by the FPGA; data **ADC_SDO1 (17), ADC_SDO2 (19)** against the returned clock **ADC_SCK_RET (16)**. Pads 1, 3, 5, 21 and 25 become N/C (were SDO_VS, SDO_IC2, SDO_IL2, SDO_IL1 and HV_FAULT_N); the AD7689 pads (11-13 as ADC_DIN / ADC_SDO / ADC_CNV) are redefined as above. PWM pads 29-32 keep their meaning and now carry 50 kHz center-aligned PWM. HV_PERMIT_STAT 37 and HV_ENABLE 38 stay, but **there is no fault latch**: HV_ENABLE gates the drivers directly. Budgets: +12 V **40 mA**, 3V3 **60 mA**, both continuous. Isolators: 10 forward, 4 back. Boards touched: HV supplies rev 4 and the control board, a matched pair as before | decision **DEFINED** [USER] 2026-11-27; pad table **PROPOSED** (the control board confirms) |

Compatibility matrix: replace the "HV supplies rev 3" row with **"HV supplies rev 4 | IF-1, and IF-2.4 on
W17 | only with the new control board; never with the v2.5 card (its pads 1-13 drive analog / I2C lines
into rev 4's mux and ADC pads)"**. In the "New control board" row, read IF-2.4 for IF-2.2.

## Section 9: W17 table (replaces the IF-2.2 table; title "W17, IF-2.4")

All signals are 3.3 V CMOS on the HV side. GND is the HV board's control ground, joined to PGND by one net tie
at the shunts. The link is isolated on the control board, as before.

| Pad | Signal | Direction | Level / note (HV side) |
|---|---|---|---|
| 1, 3, 5 | N/C | — | |
| 2, 4, 6 | GND | — | |
| 7-10 | N/C | — | |
| 11 | MUX_A0 | card → HV | both muxes' address bit 0; 100k pull-down |
| 12 | MUX_A2 | card → HV | address bit 2; 100k pull-down |
| 13 | MUX_A1 | card → HV | address bit 1; 100k pull-down |
| 14 | ADC_SCK | card → HV | shared SCLK of both ADS7056; 100k pull-down |
| 15 | ADC_CS | card → HV | shared CS; the converters sample on its falling edge; 10k pull-up |
| 16 | ADC_SCK_RET | HV → card | SCLK returned from the far end of the SCLK trace (33 Ω) |
| 17 | ADC_SDO1 | HV → card | chain 1 (bridge 1, V_ANODE) data (33 Ω); same isolator die as 16 |
| 18 | GND | — | |
| 19 | ADC_SDO2 | HV → card | chain 2 (bridge 2, V_SCREEN) data (33 Ω); same isolator die as 16 |
| 20, 22 | GND | — | |
| 21, 23-28 | N/C | — | pad 25: a pull-up on the card side is harmless |
| 29 | PWM_L1 | card → HV | bridge 1 low side; 10k pull-down |
| 30 | PWM_L2 | card → HV | bridge 2 low side |
| 31 | PWM_H1 | card → HV | bridge 1 high side |
| 32 | PWM_H2 | card → HV | bridge 2 high side |
| 33, 34 | GND | — | |
| 35, 36 | 3V3 | card → HV | **51 mA typical, 60 mA worst, continuous; budget 60 mA** (4 x Si8271 input side 32-40 mA, 7 x OPA2836 14 mA, converters, muxes, reference 5 mA) |
| 37 | HV_PERMIT_STAT | HV → card | high = HV_PERMIT loop current present (W16) |
| 38 | HV_ENABLE | card → HV | to the four Si8271 EN pins; 10k pull-down; low = drivers off at once |
| 39, 40 | +12V | card → HV | **30 mA typical, 39 mA worst, continuous; budget 40 mA**; 11-14 V at the HV board (LM2731 boost to 15.1 V gate drive, 14 V max input) |

Details, replacing IF-2.2's bullets (**PROPOSED** unless marked):

- **Switching** ([USER] 2026-11-25, replacing the TCM 40-150 kHz of 2026-11-24): two synchronous bucks
  (IKP08N65F5) at a **fixed ~50 kHz, center-aligned, 180° apart**, true synchronous drive (reverse inductor
  current on ramp-downs). The dead time comes from the FPGA over the PWM pads. Filter: 2 mH toroid, first stage
  47 µF + 5 µF film, 100 µH, output 10 µF film with a 22 µF + 2.2 Ω damping leg. Simulated ripple at the
  power amp ≤ 3.3 mV p-p typical, ≤ 5.2 mV with cold-electrolytic ESR (`rev4/sim/ripple.py`).
- **Measurement** (all digitised on the HV board). Current: 50 mΩ shunts with OPA2836 difference amplifiers,
  0.3125 V/A around 1.5 V, ±4 A into 0.25-2.75 V. Voltage: dividers 1/173.4 (520 V full scale) with buffers.
  Reference: REF3030, which is the ADS7056s' AVDD, with a buffered 1.5 V midpoint. Mux channels by address:

  | Address | Chain 1 (SDO1) | Chain 2 (SDO2) | When |
  |---|---|---|---|
  | 0 | I_L1 (low-side shunt) | I_C2 (first-stage capacitor) | carrier instant A |
  | 1 | I_C1 | I_L2 | instant B = A + 10 µs |
  | 2 | V_ANODE | V_SCREEN | gap |
  | 3 | UC1 (first-stage node) | UC2 | gap |
  | 4 | RAW (B_P) | RAW (UIN) | gap, every period (ramp-down governor) |
  | 5 | 1.5 V midpoint | 1.5 V midpoint | gap: offset and channel check |
  | 6, 7 | GND | GND | zero check |

- **Timing:** both converters sample on ADC_CS falling, at the carrier's valley and peak, where the
  triangle's mid-values equal the averages. With 180° between the bridges, one instant serves both chains.
  The FPGA sets the address between frames. A frame is 18 SCLK: 1.8 µs at 10 MHz plain, less with the
  returned clock. Two timed frames and up to six gap frames per 20 µs period; at 10 MHz the slow channels
  are read in rotation. The tightest window is the low-side off-interval at V_ANODE 400 V (D 0.93-0.95):
  1.0-1.4 µs, sampled in its middle.
- **Enable, permit and protection** ([USER] 2026-11-25, D2 / D3): **no comparators, no fault latch and no
  hardware trips on the HV board.** The four Si8271 drivers run while HV_ENABLE is high; HV_ENABLE low stops
  them at once (10k pull-down on the HV board, so link unplugged or card off = HV off). HV_PERMIT (W16 loop)
  is **reported only** (HV_PERMIT_STAT); the FPGA must drop HV_ENABLE when it goes low. The heartbeat
  monostable on the control board (IF-2.2) should stay: without a latch, a heartbeat drop-out stops the
  drivers, and they run again when HV_ENABLE returns, so the firmware restarts at feed-forward duty
  D = V_out / V_raw. All limits are firmware, from the converter readings:
  - a reading at either end of the current range is a trip;
  - over-voltage on V_ANODE, V_SCREEN and RAW;
  - the ramp-down governor on RAW (section 8, kept).

  Trip levels are to be set with the firmware (**OPEN**).
- **Gate drive:** Si8271DB (12 V UVLO: on 11.0-13.5 V, off 9.6-12.1 V) from a 15.1 V boost on the link's
  +12 V; high sides by bootstrap (about 14.2 V).
- **Isolators** (the control board's plan, 2026-11-26): 10 forward, 4 back on four ADuM14xE parts:
  - PWM;
  - SCLK / CS / A0 / A1;
  - one reversed part with SCK_RET, SDO1, SDO2 and HV_PERMIT_STAT on one die, so both data lines match the
    returned clock;
  - A2 and HV_ENABLE.

  The outputs default low with the input side unpowered, as before (PWM low and HV_ENABLE low = HV off).
- **Supplies across the barrier:** budgets as in the table. The control board makes the link 3V3 with a
  12 → 3.3 V buck instead of its LM1117 ([USER] 2026-11-27; the part is the control board's choice), about
  85 mA with its isolators' HV side. The ADS7056 reference is the REF3030, so buck ripple on 3V3 is not seen
  by the converters; FB401 (600 Ω bead) and 10 µF filter the REF3030's supply on the HV board.

## Section 8: rows to change

- **HV_PERMIT (HV inhibit):** HV supplies side: **status only** (HV_PERMIT_STAT, pad 37); the loop no longer
  enables the gate drivers in hardware. The inhibit acts through the firmware dropping HV_ENABLE. This changes
  SAFE-6's "hardware path, not firmware only" for the HV supplies ([USER] 2026-11-25, D3). The power amp's
  side of the loop (BIAS_OK, over-current latch, WARM_OK) is unchanged.
- **Standby / HV enable (HV_ENABLE):** the drivers run when **HV_ENABLE** is high (no AND with HV_PERMIT or a
  latch on the HV board). The pull-down is 10k (was "100k"). The heartbeat monostable stays (control board).
- **HV_FAULT_N and the fault latch:** **withdrawn** (no latch, pad 25 N/C).
- **Power ramps and raw-rail over-voltage:** the firmware rules stay. Replace "latched over-voltage trip on
  the HV supplies (raw 475 V; …)" with "**firmware** limits from the converter readings (levels **OPEN**)". The
  ramp-down governor on RAW is now the only raw-rail protection on the HV side, besides the PSU's own. The
  480 / 450 / 500 V rule is unchanged.
- **Tube PSU trip request:** "on HV_FAULT_N" → "on a firmware trip of the HV supplies".

## Section 3: HV supplies rows

- 3.2 per board, HV supplies: +12 V **30 mA typical / 39 mA worst, budget 40 mA**; 3V3 **51 / 60 mA, budget
  60 mA**; isolators' far side about 25 mA on the control board. Board loss 4.3-6.8 W (`rev4/sim/losses.py`).
  Heat into the east wall 4-5 W at most; worst device 3.0-3.5 W, Tj 96-98 °C with an 85 °C wall.
- 3.3 totals, +15 V: the HV link's share rises a little (about 1.5 W from the 2 W TMR-1212 with the buck),
  for the control board session to re-total.

## Section 12: mechanical

- **12.1 envelope:** replace the rev 3 L shape. The new entry:
  - outline **x 562-677, y 39-127, a 115 x 88 mm rectangle (101 cm²)**, components down, hanging about
    15 mm below the plate;
  - SMD only on the plate face; the big parts (films 28 mm, toroids 32 mm) on the down face;
  - 10 mm to the control board, 1 mm to the east wall;
  - the corridor under the former arm (y 127-147) is no longer needed.

  **PROPOSED**; the wall's inner face (assumed x 678, 2 mm wall) is **OPEN** (to measure).
- **12.1a chassis work list:** **withdraw** rev 3's eight countersunk plate holes, the two aluminium bars and
  the rev 3 standoff holes. **Add:**
  - four M3 holes (tapped, or clearance with a nut) in the **east side wall** for the TO-220 tabs at chassis
    y **52, 66, 100, 114**; the height on the wall comes from the board height (**OPEN**);
  - each tab mounts insulated: pad or washer plus a shoulder bush; the tabs are live;
  - new plate holes for the standoffs at **(566, 43), (566, 123), (668, 42.5)** non-plated, and **H101
    (630.5, 113.5)** plated (the fault / RF network's chassis bond).

  The devices can be serviced without removing the tube PSU. **PROPOSED.**
- **12.3 / 12.5 / 12.6 connector positions** (chassis mm, rev 4 layout stage 0):

  | Connector | Position |
  |---|---|
  | J1 (W17) pin 1 | (566.37, 108.86) |
  | J1 (W17) pin 40 | (565.10, 84.73) (unchanged, facing J11) |
  | J501 (W16) | (566.5, 57.5) |
  | J101 (W01) B_P / B_N | (660, 45) / (648, 45), under the PSU's front cable hole |
  | J102 (W02) RAW_SS1 / GND_PRE1 | (595, 45) / (607, 45) |
  | J103 (W03) RAW_SS2 / GND_PRE2 | (573.5, 45) / (585.5, 45) |
  | J201 (W04) V_ANODE / GND_PWR | (588, 121) / (576, 121) |
  | J202 (W05) V_SCREEN | (600, 121) |

  **W04 / W05 are longer** than the rev 3 jumpers: from y 121 at x 576-600 to the power amp's tabs at
  (514.5, 151.5-170.5), about 0.15-0.2 m, twisted. **W16** leaves from the west edge at y 57.5 instead of
  (572.5, 117.5). **PROPOSED.**
- **Section 5 (grounding):** remove the rev 3 TCM row (low-side tabs on the plate, 30 mA displacement
  peaks). With 50 kHz hard switching the tabs' capacitance to the wall is the path. Through the insulating pad
  that is a few pF per tab; at 20-50 V/ns that is 0.1-0.3 A spikes into the wall, returning through H101 and
  the fault / RF network (an **estimate**, to measure).

## Section 14: open items

- **Withdraw** "Proposed IF-2.3 on W17, 2026-11-25" (superseded by IF-2.4).
- HV supplies, **OPEN**:
  - the east wall's inner face and thickness, and the TO-220 hole heights on the wall (measure);
  - firmware trip levels;
  - the ADC SCLK rate over the isolators (O7: 10 MHz plain, faster with the returned clock if the slow
    channels are wanted every period).
- Control board, **OPEN**: confirm the IF-2.4 table; draw the four isolators and the 12 → 3.3 V buck (its
  user's approval); re-total the TMR-1212 load.
