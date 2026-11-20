# Status: HV supplies rev 3 (initial schematic, 2026-11-21)

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
