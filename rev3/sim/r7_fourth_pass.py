#!/usr/bin/env python3
"""HV supplies rev 3, fourth pass (soft-switched redraw, 2026-11-24): the re-runs the mode change invalidates.

1. Inductors as drawn: L201 220 uH, 50 turns, L203 470 uH, 64 turns on ETD39 N97 (gap for saturation
   >= 10 / >= 6 A): peak flux at the TCM peaks, the 3.0 A trips and a short; losses (tcm.py).
2. Output short and arc (M20 re-run) with the as-drawn output network: C1 = 100 uF (ESR 0.1) + 4.7 uF film,
   L2 68 uH, C2 4.7 uF, damping leg 22 uF + 1.0 ohm (+ 0.5 ohm ESR), R205 1.0 ohm / R212 2.2 ohm, W04 0.5 uH;
   the bridge as a switched source (420 V while the high side conducts, the low-side diode after the trip)
   into L1 from its 2.5 A peak; trip from the I_C discharge comparator after 1.0 us (fast front end: amplifier,
   100 ohm / 2.7 nF, LMV339, latch, DIS) or, if it failed, after one TCM period (low-side 3.0 A trip, 25 us)
   or the firmware (100 us). Faults: 50 mohm at the V_ANODE tab; a 30 V arc; V_ANODE short with the screen
   network discharging through R212 and D201 (1N5408).
3. Channel change, start-up and restart (M21 / M22 re-run) with the as-drawn network and the ADS7056 loop
   (r6 gains Kp 0.75, Ki 2000, Kc 2; Ts 25 us, Td 20 us: the slowest TCM case), TCM peak current.
4. Thermal on the plate: IGBTs on a 6 mm aluminium bar on the 2 mm plate, 1.5 mm Al2O3 washers.
5. Residue at the power amp with the as-drawn parts (r2 model) and the common-mode current into the chassis.

Run: python3 rev3/sim/r7_fourth_pass.py   (writes r7_results.md; a minute)
"""
import os

import numpy as np

import filt
import r2_filter as r2
import r3_damping as r3
import swmodel as sm
import tcm

HERE = os.path.dirname(os.path.abspath(__file__))
DA = dict(tcm.DESIGN, N=50, litz=0.8e-6)
DS = dict(tcm.DESIGN_SCREEN, N=64, litz=0.5e-6)
AE = 125e-6
BSAT = 0.38       # N97 at 100 C, about 0.38-0.41 T (est. from the TDK material data)
T_PLATE = 85.0    # plate under the tube PSU at 70 C ambient (est.)
RTH = dict(jc=2.2, washer=0.8, bar=1.0)    # K/W: IKP08N65F5 datasheet; Al2O3 1.5 mm + 2 greased interfaces (est.); bar + plate spreading (est.)


def short_case(name, l1, n_l1, rs, fault, t_trip, screen=False):
    """Returns peak values and energies (dict)."""
    v0, i0 = (400.0, 0.7) if not screen else (390.0, 0.18)
    ipk0 = 2.5 if not screen else 1.2
    lines = ["* r7 short / arc",
             "Vin vin 0 420", f"Vg g 0 PWL(0 1 {t_trip} 1 {t_trip + 50e-9} 0)", "Sh vin sw g 0 SWH",
             ".model SWH SW(VT=0.5 VH=0.1 RON=0.2 ROFF=1e9)", ".model DFW D(IS=1e-9 N=1.8 RS=0.05 CJO=50p)",
             "Dl 0 sw DFW", "Dh sw vin DFW", "Csw sw 0 200p", "Rswd sw 0 1e6",
             sm.inductor_par("L1", "sw", "uc", l0=l1, isat=BSAT * n_l1 * AE / l1, soft=0.4, ratio=10.0, dcr=0.1, cw=1e-12, i0=ipk0),
             "Vl1 uc uc2 0",
             f"Ce uc2 ce 100u IC={v0 + i0 * rs}", "Rce ce ic 0.1", f"Cf uc2 cfx 4.7u IC={v0 + i0 * rs}", "Rcf cfx ic 0.0075",
             "Vic ic ics 0", "Rshc ics 0 0.05",
             f"L2 uc2 l2 68u IC={i0}", "R2 l2 vo 0.06",
             f"C2 vo c2x 4.7u IC={v0 + i0 * rs}", "Rc2 c2x 0 0.01",
             f"Cd vo cdx 22u IC={v0 + i0 * rs}", "Rcd cdx 0 1.5",
             "Vrs vo vob 0", f"Rs vob tab {rs}", "Lw tab pa 0.5u", f"Cpa pa 0 100n IC={v0}", f"Iload pa 0 {i0}"]
    if fault == "short":
        lines += ["Sf tab 0 fl 0 SWF", "Vfl fl 0 PWL(0 0 1u 0 1.01u 1)", ".model SWF SW(VT=0.5 VH=0.1 RON=0.05 ROFF=1e9)"]
    elif fault == "arc":
        lines += ["Sf tab arc fl 0 SWF", "Varc arc 0 30", "Rarc arc 0 1e9", "Vfl fl 0 PWL(0 0 1u 0 1.01u 1 1m 1 1.01m 0)",
                  ".model SWF SW(VT=0.5 VH=0.1 RON=0.1 ROFF=1e9)"]
    net = "\n".join(lines)
    net += f"\n.ic v(uc)={v0 + i0 * rs} v(uc2)={v0 + i0 * rs} v(vo)={v0 + i0 * rs} v(tab)={v0} v(pa)={v0}"
    r = sm.run(net, ["i(Vl1)", "i(Vrs)", "i(Vic)", "v(uc2)", "v(tab)"], 3e-3, "20n", "50n", uic=True)
    t = r["t"]
    irs = r["i(Vrs)"]
    e_rs = np.trapezoid(irs ** 2 * rs, t)
    e_sh = np.trapezoid(r["i(Vic)"] ** 2 * 0.05, t)
    return dict(name=name, il_pk=r["i(Vl1)"].max(), irs_pk=np.abs(irs).max(), e_rs=e_rs, ic_pk=np.abs(r["i(Vic)"]).max(),
                e_sh=e_sh, bpk=l1 * r["i(Vl1)"].max() / (n_l1 * AE))


def screen_via_d201():
    """V_ANODE shorted: the screen network dumps through R212 2.2 ohm and D201 into the anode short."""
    net = "\n".join([
        "* screen through D201",
        "Ce uc ce 100u IC=390.4", "Rce ce 0 0.15", "Cf uc cf 4.7u IC=390.4", "Rcf cf 0 0.0075",
        "L2 uc l2 68u IC=0.18", "R2 l2 vo 0.06", "C2 vo c2 4.7u IC=390.4", "Rc2 c2 0 0.01",
        "Cd vo cd 22u IC=390.4", "Rcd cd 0 1.5", "Vrs vo vob 0", "Rs vob tabs 2.2",
        "Lw5 tabs pas 0.5u", "Cpas pas 0 100n IC=390",
        ".model D5408 D(IS=1e-8 N=1.8 RS=0.01 BV=1000 CJO=50p)",
        "Dc tabs taba D5408", "Cta taba 0 100n IC=400", "Sf taba 0 fl 0 SWF", "Vfl fl 0 PWL(0 0 1u 0 1.01u 1)",
        ".model SWF SW(VT=0.5 VH=0.1 RON=0.05 ROFF=1e9)"])
    net += "\n.ic v(uc)=390.4 v(vo)=390.4 v(tabs)=390 v(pas)=390 v(taba)=400"
    r = sm.run(net, ["i(Vrs)", "v(tabs)"], 3e-3, "20n", "50n", uic=True)
    t, i = r["t"], r["i(Vrs)"]
    return dict(ipk=np.abs(i).max(), e=np.trapezoid(i ** 2 * 2.2, t), i2t=np.trapezoid(i ** 2, t))


def main():
    L = ["# Fourth pass re-runs (generated by r7_fourth_pass.py)", "", __doc__.split("\n\n")[1].strip(), ""]
    # 1. inductors
    L += ["## 1. Inductors as drawn", "",
          "| Inductor | turns / gap (est.) | I_sat (B = 0.38 T) | B at the TCM peak 2.5 A / 1.2 A | B at the 3.0 A trip | copper + core at 400 V 0.7 A / 200 V no load (W) |",
          "|---|---|---|---|---|---|"]
    for nm, d, ipk, gap in (("L201 220 uH", DA, 2.5, 1.8), ("L203 470 uH", DS, 1.2, 1.4)):
        isat = BSAT * d["N"] * AE / d["L"]
        b = lambda i: d["L"] * i / (d["N"] * AE)
        pts = [(400, 0.7, 420), (200, 0.0, 425)] if d is DA else [(390, 0.18, 420), (146, 0.08, 425)]
        loss = [tcm.operating_point(*p, d) for p in pts]
        L.append(f"| {nm} | {d['N']} / ~{gap} mm | {isat:.1f} A | {b(ipk):.2f} T | {b(3.0):.2f} T | "
                 + " / ".join(f"{o['pcu'] + o['pcore']:.2f}" for o in loss) + " |")
    # 2. short / arc
    cases = [("V_ANODE short, I_C trip 1.0 us", 220e-6, 50, 1.0, "short", 1e-6 + 1.0e-6, False),
             ("V_ANODE short, trip at the next low-side period (25 us)", 220e-6, 50, 1.0, "short", 1e-6 + 25e-6, False),
             ("V_ANODE short, no hardware trip: firmware at 100 us", 220e-6, 50, 1.0, "short", 1e-6 + 100e-6, False),
             ("V_ANODE 30 V arc 1 ms, I_C trip 1.0 us", 220e-6, 50, 1.0, "arc", 1e-6 + 1.0e-6, False),
             ("V_SCREEN short, I_C trip 1.0 us", 470e-6, 64, 2.2, "short", 1e-6 + 1.0e-6, True)]
    L += ["", "## 2. Output short and arc (M20 re-run, as drawn)", "",
          "| Case | L1 peak (A) / B peak (T) | output resistor peak (A) / energy (J) | I_C shunt peak (A) / energy (J) |",
          "|---|---|---|---|"]
    for c in cases:
        o = short_case(*c)
        L.append(f"| {o['name']} | {o['il_pk']:.1f} / {o['bpk']:.2f} | {o['irs_pk']:.0f} / {o['e_rs']:.2f} | {o['ic_pk']:.0f} / {o['e_sh']:.3f} |")
    sd = screen_via_d201()
    L += [f"| V_ANODE short: the screen network through R212 and D201 | — | R212 {sd['ipk']:.0f} A / {sd['e']:.2f} J | D201 I^2t {sd['i2t']:.2f} A^2s (1N5408: 166 A^2s) |",
          "", "Ratings: IKP08N65F5 ICpuls 24 A (no short-circuit rating, but the inductor keeps it out of a short); "
          "ULW5-1R0 about 19 J, ULW5-2R2 about 13 J short-pulse (M20); WSL2512 metal strip pulse rating to confirm (M20: 0.29 J). "
          "With the 220 uH inductor and the trip within about 1 us the bridge stops at under 5 A; even with no hardware "
          "trip until the firmware (100 us) the inductor stays below saturation only if C1 has not yet discharged: the "
          "table shows the peak (a double failure: the I_C trip and the low-side trip both missing). The energy into R205 rises against M20 (5.8-6.0 J) because C1 now dumps through 68 uH "
          "without the old 5.6 ohm path and the damping leg adds 22 uF.", ""]
    # 3. channel change / start-up / restart
    p0 = r3.chain(1)
    g = dict(Kp=0.75, Ki=2000, Kc=2)
    ts, td = 25e-6, 20e-6
    runs = []
    # start-up 0 -> 400 V in 80 ms, cold tubes: the load is only the bleeder; the charging current is C dV/dt
    vr0 = lambda t: 400 * min(max((t - 5e-3) / 0.08, 0), 1)
    o = r3.simulate(p0, 0.3, g, ts, td, 0.1, vr0, lambda t: 0.0, r_load=220e3)
    runs.append(("start-up 0 -> 400 V, 80 ms linear, tubes cold", o, vr0))
    # channel change 400 -> 150 V in 100 ms, idle 0.3 A following V^1.5
    vr = lambda t: 400 - 250 * min(max((t - 5e-3) / 0.1, 0), 1)
    o = r3.simulate(p0, 0.3, g, ts, td, 0.13, vr, lambda t: 0.3 * (vr(t) / 400) ** 1.5)
    runs.append(("channel change 400 -> 150 V in 100 ms, idle 0.3 A x (V/400)^1.5", o, vr))
    vr2 = lambda t: 150 + 250 * min(max((t - 5e-3) / 0.1, 0), 1)
    o = r3.simulate(p0, 0.3, g, ts, td, 0.13, vr2, lambda t: 0.3 * (vr2(t) / 400) ** 1.5)
    runs.append(("channel change 150 -> 400 V in 100 ms", o, vr2))
    L += ["## 3. Start-up and channel change (ADS7056 loop, slowest TCM timing)", "",
          "| Case | V_tab tracking error max (V) | i_L1 average min / max (A) | TCM peak (A, capped at 2.5) |", "|---|---|---|---|"]
    for nm, o, vf in runs:
        m = o[:, 0] > 5e-3
        err = np.abs(o[m, 1] - np.array([vf(t) for t in o[m, 0]])).max()
        L.append(f"| {nm} | {err:.1f} | {o[m, 2].min():.2f} / {o[m, 2].max():.2f} | {min(r3.tcm_peak(o[m, 2]).max(), 2.5):.2f} |")
    L += ["", "Restart with charged outputs: the TCM modulator starts at D = V_out / V_raw at the law's frequency, so the "
          "first periods carry the TCM ripple around zero (no -2.6 A reverse step as with duty 0, M22). "
          "Fail-safe: the link or the PWM generator stops -> the heartbeat monostable drops HV_ENABLE within about 20 us -> "
          "U504 disables both drivers at once (both IGBTs off, gates held by 10 kohm) and U508 sets the latch; the inductor "
          "current (<= 2.5 A, 0.7 mJ) finishes in the diodes (positive into the output, negative back to the raw rail); "
          "the outputs then fall through the tubes and bleeders (PS-3). PWM frozen with the heartbeat still running: "
          "open loop at the last duty, the output drifts to at most 0.985 x 420 = 414 V, under the 438 / 421 V trips. "
          "+12 V lost: UVLO per channel as before.", ""]
    # 4. thermal
    rt = sum(RTH.values())
    pts = [("400 V 0.70 A (raw 420 V)", 400, 0.7, 420, DA), ("400 V idle 0.30 A", 400, 0.3, 430, DA),
           ("200 V 0.35 A", 200, 0.35, 425, DA), ("200 V no load", 200, 0.0, 425, DA), ("150 V 0.20 A", 150, 0.2, 425, DA),
           ("ramp-down 300 V -0.8 A (<= 1 s)", 300, -0.8, 425, DA),
           ("screen 390 V 0.18 A", 390, 0.18, 420, DS), ("screen 146 V 0.08 A", 146, 0.08, 425, DS)]
    L += ["## 4. Thermal on the plate", "",
          f"Plate {T_PLATE:.0f} C assumed (under the tube PSU, 70 C ambient; est.). R_th junction to plate = "
          f"{RTH['jc']} (IGBT, datasheet) + {RTH['washer']} (1.5 mm Al2O3, greased, est.) + {RTH['bar']} (6 mm bar and plate "
          f"spreading, est.) = {rt:.1f} K/W.", "",
          "| Point | Q_hs / Q_ls (W) | Tj high / low side (C) |", "|---|---|---|"]
    tot_worst = 0
    for nm, vo, io, vin, d in pts:
        o = tcm.operating_point(vo, io, vin, d)
        L.append(f"| {nm} | {o['p_hs']:.2f} / {o['p_ls']:.2f} | {T_PLATE + o['p_hs'] * rt:.0f} / {T_PLATE + o['p_ls'] * rt:.0f} |")
    L += ["", "Heat into the plate: about 1.7 W at 400 V / 0.7 A + 0.18 A (both bridges), at most about 4.5 W at 150-250 V "
          "(3.2-3.5 W in the anode bridge, 1.2 W in the screen bridge).", ""]
    # 5. residue and CM
    pa = r2.chain_for(filt.REC, 1)
    ps = r2.chain_for(filt.REC, 2)
    ra = r2.residue(pa, 40e3, 400, 420, 0.3, 571)[0]
    rs_ = r2.residue(ps, tcm.law(390, 0.18, 420, DS), 390, 420, 0.3, 2167)[0]
    c_tab = 8.85e-12 * 9.8 * 130e-6 / 1.5e-3
    L += ["## 5. Residue and common-mode current", "",
          f"Residue at the power amp with the as-drawn parts (the r2 chain is the drawn one): V_ANODE {ra * 1e3:.1f} mV p-p at "
          f"400 V / 0.7 A (40 kHz), V_SCREEN {rs_ * 1e3:.1f} mV p-p, ESR 0.3 ohm; at the speaker <= 19 uV (KT88) / 32 uV (EL34) rms "
          "(r4). Low-side tab capacitance through 1.5 mm Al2O3: "
          f"{c_tab * 1e12:.1f} pF -> {c_tab * 4e9 * 1e3:.0f} mA peaks at 4 V/ns (100-400 ns, each switching edge); the high-side tab "
          "is at the raw rail (DC). The current returns through the plate to the fault / RF network (100 nF Y2 || 100 ohm "
          "|| GBU8J at the plated standoff H101) into GND_STAR."]
    open(os.path.join(HERE, "r7_results.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
