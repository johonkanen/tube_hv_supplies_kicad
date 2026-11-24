#!/usr/bin/env python3
"""HV supplies rev 3, device choice for the TCM bridge (study 2026-11-24).

Devices (datasheet figures read 2026-11-24; sources in r5_results.md; "est." marks my estimates):
  IGBT   Infineon IKP08N65F5 (present part, TO-220 collector tab): the calibrated swmodel (r1, M15).
  SJ     Infineon IPP65R190CFD7 (TO-220, drain tab): RDS(on) 0.161 / 0.359 ohm (25 / 150 C, 10 V),
         Co(er) 41 pF, Co(tr) 424 pF (Qoss = 170 nC at 400 V), Eoss 3.3 uJ, Qg 23 nC (0-10 V),
         Qrr 0.4 uC typ / 0.8 max (400 V, 5.2 A, 100 A/us), Irrm 7.9 A, diode dv/dt 70 V/ns max, Vth 3.5-4.5 V.
  GaNc   Renesas (Transphorm) TP65H150G4PS, cascode GaN, TO-220 SOURCE tab: VDSS 650 V, VDSS(TR) 800 V
         (off state, < 30 us, non-repetitive), RDS(on)eff 150 / 307 mohm (25 / 150 C), Vth 3.3-4.8 V,
         VGS +-20 V, Qg 8 nC (0-10 V), Co(er) 43 pF, Co(tr) 85 pF, Qoss 34 nC, Qrr "negligible",
         VSD 1.6 V at 5 A, IDM 60 A (10 us), RthJC 1.5 K/W; switching test: 0-12 V gate, RG 70 ohm,
         ferrite bead 240 ohm at 100 MHz, tR 18 ns, tF 9.4 ns. No short-circuit or avalanche rating.
  SiCc   onsemi (UnitedSiC / Qorvo) UF3C065080T3S, SiC JFET cascode, TO-220 drain tab: 650 V, 80 / 111 mohm
         (25 / 125 C, 12 V gate), Vth 4-6 V, VGS +-25 V, Qg 51 nC (-5 to 15 V; 0-12 V about 35 nC est.),
         Coss(er) 77 pF, Coss(tr) 176 pF (70 nC), Eoss 6.2 uJ, Qrr 73 nC at 150 C (20 A, 2200 A/us),
         VFSD 1.75 V, EAS 33 mJ (avalanche rated), IDM 65 A, RthJC 0.79 K/W; the datasheet requires an RC
         snubber (5 ohm + 100 pF) and gives Eon 156 / Eoff 25 uJ at 400 V / 20 A, 150 C, with it.
  SiCm   Infineon IMBG65R075M2H, CoolSiC G2 (D2PAK-7; TO-247-3 siblings IMW65R...M2H): recommended
         VGS(off) 0 V, VGS(on) 18 V; RDS(on) 98 mohm at 15 V, 75 at 18 V, 123 at 18 V / 175 C; Vth 3.5-5.6 V;
         Ciss 516, Crss 3.6 pF; Qoss 32 nC, Eoss 4.4 uJ, Qg 14.9 nC (0-18 V), body diode VSD 4.3 V,
         Qfr 34 nC (1000 A/us), Eon 20 / Eoff 10 uJ (400 V, 11.9 A).
  GaNe   Infineon (GaN Systems) GS66504B, e-mode GaN, GaNPX bottom-cooled SMD: 650 V, 750 V transient
         (< 1 us), VGS -10 / +7 V (-20 / +10 transient), Vth 1.1-2.6 V, 100 / 258 mohm (6 V), Qg 3.3 nC
         (0-6 V), Ciss 120 / Crss 1.1 pF, Co(er) 47, Co(tr) 75 pF, Qoss 30 nC, Qrr 0; last-time-buy at DigiKey.
  GaNi   TI LMG3422R050, GaN with integrated driver, VQFN-54 12 x 12 mm: 43 / 73 mohm, Qoss 100 nC,
         Co(er) 155 pF, VDD 9-18 V (9 mA at 140 kHz soft-switched), internal buck-boost makes its own
         negative gate bias, overcurrent 40-60 A / short-circuit 60-90 A trip in 65-100 ns, 720 V surge.

1. Losses over the operating map at the r1 law (220 uH, I_zvs set by each device's node charge for a
   300 ns transition, f 40-150 kHz): conduction (I_rms^2 R_hot in either direction, dead-time drop),
   turn-off under ZVS (MOSFET / GaN / SiC: I^2 t_f^2 / (24 C_node), est.; IGBT: r1 tail model), gate.
2. The forced hard commutation (ngspice, generic device: the turning-on switch as a resistance falling
   over the datasheet's rise time, the freewheeling device as its Co(tr) with a charge-control diode
   carrying the datasheet Qrr; 480 V raw, loop 20 / 40 nH): 0.8 A and 2.5 A; peak current, dv/dt,
   overshoot, energy; once and every cycle for a second at 40 / 150 kHz.
3. Spurious turn-on margin (Crss / Ciss charge division and the driver's sink), the chassis tab
   (node, insulator, capacitance, common-mode current), +12 V budget.
4. The fixed-frequency hard-switched alternative (100 / 150 kHz, 470 uH) with the best device.

Run: python3 rev3/sim/r5_devices.py   (writes r5_results.md; a minute)
"""
import os
from multiprocessing import Pool

import numpy as np

import filt
import r2_filter as r2
import swmodel as sm
import tcm

HERE = os.path.dirname(os.path.abspath(__file__))

# device data: r_hot (ohm, 125 C at the drive used), qoss (C, 0-400 V, one device), eoss (J), cotr (F),
# qg (C at the drive used), vdrv (V), qrr (C, hard commutation), vsd (V, reverse conduction in dead time),
# tr / tf (s, at the gate resistance used), vth_min (V, hot), crss / ciss (F), rthjc (K/W), vmax (V
# repetitive) / vtr (V, transient), tab ("drain" / "source"), avalanche, sc (short-circuit rating)
DEV = {
    "IGBT IKP08N65F5 (present)": dict(r_hot=None, qoss=15e-9, eoss=None, cotr=40e-12, qg=34e-9, vdrv=12, qrr=0.25e-6,
                                      vsd=1.4, tr=8e-9, tf=18e-9, vth=2.0, crss=3e-12, ciss=500e-12, rthjc=2.2,
                                      vmax=650, vtr=650, tab="collector", aval="no", sc="no (Highspeed 5)", cost="~1.5"),
    "SJ CFD7 IPP65R190CFD7": dict(r_hot=0.33, qoss=170e-9, eoss=3.3e-6, cotr=424e-12, qg=23e-9 * 1.2, vdrv=12, qrr=0.4e-6,
                                  vsd=1.0, tr=10e-9, tf=8e-9, vth=2.8, crss=1e-12, ciss=1100e-12, rthjc=1.99, vmax=650, vtr=650,
                                  tab="drain", aval="yes (SJ)", sc="no", cost="~2.5"),
    "GaN cascode TP65H150G4PS": dict(r_hot=0.27, qoss=34e-9, eoss=3.4e-6, cotr=85e-12, qg=9.6e-9, vdrv=12, qrr=5e-9,
                                     vsd=1.6, tr=18e-9, tf=9.4e-9, vth=3.0, crss=1e-12, ciss=598e-12, rthjc=1.5, vmax=650,
                                     vtr=800, tab="source", aval="no (800 V transient, < 30 us)", sc="not specified", cost="~4-6"),
    "SiC cascode UF3C065080T3S": dict(r_hot=0.111, qoss=70e-9, eoss=6.2e-6, cotr=176e-12, qg=35e-9, vdrv=12, qrr=5e-9,
                                      vsd=1.75, tr=14e-9, tf=11e-9, vth=3.5, crss=2.6e-12, ciss=1500e-12, rthjc=0.79,
                                      vmax=650, vtr=650, tab="drain", aval="yes, EAS 33 mJ", sc="not specified", cost="~6-8"),
    "SiC MOSFET IMBG65R075M2H (0 V off, 18 V on)": dict(r_hot=0.11, qoss=32e-9, eoss=4.4e-6, cotr=81e-12, qg=14.9e-9, vdrv=18,
                                                        qrr=2e-9, vsd=4.3, tr=5.3e-9, tf=5.5e-9, vth=2.8, crss=3.6e-12,
                                                        ciss=516e-12, rthjc=1.2, vmax=650, vtr=650, tab="drain (SMD)",
                                                        aval="not stated", sc="not stated", cost="~5-7"),
    "e-mode GaN GS66504B (6 V)": dict(r_hot=0.23, qoss=30e-9, eoss=3.8e-6, cotr=75e-12, qg=3.3e-9, vdrv=6, qrr=0.0,
                                      vsd=2.5, tr=4e-9, tf=4e-9, vth=1.1, crss=1.1e-12, ciss=120e-12, rthjc=1.0, vmax=650,
                                      vtr=750, tab="SMD pad (source)", aval="no (750 V < 1 us)", sc="no", cost="~7 (LTB)"),
    "GaN + driver LMG3422R050": dict(r_hot=0.073, qoss=100e-9, eoss=12.4e-6, cotr=235e-12, qg=None, vdrv=12, qrr=0.0,
                                     vsd=3.8, tr=4e-9, tf=4e-9, vth=None, crss=None, ciss=None, rthjc=0.5, vmax=650,
                                     vtr=720, tab="SMD pad (source)", aval="no (720 V surge)", sc="yes, 65-100 ns internal",
                                     cost="~15-20"),
}
D = tcm.DESIGN
PTS = [("400 V 0.70 A (raw 420 V)", 400, 0.70, 420), ("400 V idle 0.30 A", 400, 0.30, 430), ("400 V no load", 400, 0.0, 430),
       ("200 V 0.35 A", 200, 0.35, 425), ("150 V 0.20 A", 150, 0.20, 425), ("ramp-down 300 V -0.8 A", 300, -0.8, 425)]
T_DT = 300e-9


def tcm_point(dev, vo, io, vin, L=220e-6, fmax=150e3, fmin=40e3):
    """Losses (W) of the high and low side of one bridge in TCM with a MOSFET-like device."""
    c_node = 2 * dev["qoss"] / 400 + 20e-12
    q = 2 * dev["qoss"] * vin / 400 + 20e-12 * vin
    izvs = q / T_DT
    d = dict(L=L, izvs=izvs, fmin=fmin, fmax=fmax, mode="adaptive", io_design=0.8)
    f = tcm.law(vo, io, vin, d)
    dcy = vo / vin
    di = vo * (1 - dcy) / (L * f)
    ipk, ival = io + di / 2, io - di / 2
    irms2 = io ** 2 + di ** 2 / 12
    pc = dev["r_hot"] * irms2
    e_off = lambda i: i ** 2 * dev["tf"] ** 2 / (24 * c_node)
    # dead time conduction: 30 ns of reverse conduction at each edge (adaptive dead time)
    pdt = 30e-9 * f * (abs(ipk) + abs(ival)) * dev["vsd"]
    hard = (ival > 0) or (ipk < 0)
    p_hs = pc * dcy + f * e_off(max(ipk, 0)) + pdt / 2
    p_ls = pc * (1 - dcy) + f * e_off(max(-ival, 0)) + pdt / 2
    return dict(f=f, izvs=izvs, ipk=ipk, ival=ival, p_hs=p_hs, p_ls=p_ls, hard=hard)


def igbt_point(vo, io, vin):
    o = tcm.operating_point(vo, io, vin, D)
    return dict(f=o["f"], izvs=D["izvs"], ipk=o["ipk"], ival=o["ival"], p_hs=o["p_hs"], p_ls=o["p_ls"], hard=o["hard"])


def gate_ma(dev, f, n=4):
    """+12 V current (mA) for n devices at f plus 6 mA of driver quiescent current; an 18 V or 6 V drive
    is made from +12 V at 80 % efficiency (power basis)."""
    if dev["qg"] is None:
        return n * 9.0 * f / 140e3 + 1.0             # LMG3422: 9 mA each at 140 kHz (datasheet), own supply
    p = n * dev["qg"] * dev["vdrv"] * f
    return (p / 12.0 / (0.8 if dev["vdrv"] != 12 else 1.0)) * 1e3 + 6.0


# ------------------------------------------------------------------ hard commutation (ngspice)
def hard_event(args):
    name, i0, lloop, vin = args[:4]
    dev = dict(DEV[name])
    if len(args) > 4:
        dev["tr"] = args[4]
    if name.startswith("IGBT"):
        return name, i0, lloop, None
    qrr = dev["qrr"]
    tt = qrr / max(i0, 0.05) if qrr > 0 else 1e-12
    tt = min(tt, 2e-6)
    ron = dev["r_hot"]
    tr = dev["tr"]
    net = "\n".join([
        "* forced hard commutation: high side turns on into the low side's reverse path",
        # bus capacitor (C202 100 nF + C203 1 nF at the bridge) and the commutation-loop inductance
        # between it and the switch (lead + board + capacitor ESL), damped only by its ESR
        f"Vin vin 0 {vin}", "Rbus vin cb 1", "Cbus cb 0 100n IC=%g" % vin,
        f"Lloop cb c1 {lloop}", "Rloopesr c1 c1x 0.0", 
        # high side: resistance from 10 Meg to Ron over tr, starting at 10 ns
        "Vsw c1x c1s 0",
        f"Bsw c1s sw I = V(c1s,sw) / ({ron} + 1e7 * exp(-max(time - 10n, 0) / ({tr} / 4.6)))",
        f"Chs c1x sw {dev['cotr']}",
        # low side: Co(tr) + charge-control diode (forward current = the load current at t = 0)
        f"Cls sw 0 {dev['cotr']}",
        f".model DFW D(IS=1e-9 N=1.5 RS=0.05 TT={tt:.4g} CJO=1p BV=2000)",
        "Dfw 0 sw DFW",
        "Rsn sw xs 5", "Csn xs 0 100p" if name.startswith("SiC cascode") else "Rsnx xs 0 1e9",
        f"Iload sw 0 {i0}",
    ])
    r = sm.run(net, ["v(sw)", "v(c1)", "i(Lloop)", "i(Vsw)"], 400e-9, "0.05n", "0.1n", uic=False)
    t, v, vc, il, isw = r["t"], r["v(sw)"], r["v(c1)"], r["i(Lloop)"], r["i(Vsw)"]
    ihs = il  # supply current ~ high-side current (Cbus small effect at these times)
    # energy in the high side: (V(c1) - V(sw)) x current through Bsw: approximate with the loop current minus Chs
    # energy in the turning-on channel (its own Co(tr) discharges through it: included)
    vc = r["v(c1)"]
    p = (vc - v) * isw
    m = t > 5e-9
    e = np.trapezoid(p[m], t[m])
    dvdt = np.max(np.diff(v) / np.diff(t)) * 1e-9
    return (name if len(args) == 4 else name + f", turn-on slowed to {args[4] * 1e9:.0f} ns"), i0, lloop, dict(ipk=isw.max(), vpk=v.max(), e=e, dvdt=dvdt)


def main():
    L = ["# Device choice for the TCM bridge (generated by r5_devices.py)", "", __doc__.split("\n\n")[1].strip(), "",
         "Sources: Renesas TP65H150G4PS datasheet R07DS1670EU0300 Rev. 3.00 (2025-11-25); onsemi UF3C065080T3S/D Rev. 4 "
         "(2025-03); Infineon IPP65R190CFD7 datasheet; Infineon IMBG65R075M2H Rev. 2.1 (2025-07-23); Infineon (GaN Systems) "
         "GS66504B Rev 200402; TI LMG3422R050 SNOSDA8D (2025-05); IKP08N65F5 Rev 2.1 (M15). Prices are rough distributor "
         "estimates (est.), to check.", ""]
    # 1. losses
    L += ["## 1. Losses in TCM (one bridge, Q_hs / Q_ls, W; L 220 uH, f 40-150 kHz, I_zvs for 300 ns)", "",
          "| Device | I_zvs (A) | " + " | ".join(p[0] for p in PTS) + " | +12 V at 150 kHz, 4 devices (mA) |",
          "|---|---|" + "---|" * len(PTS) + "---|"]
    tot = {}
    for name, dev in DEV.items():
        cells = []
        s = 0
        for pn, vo, io, vin in PTS:
            o = igbt_point(vo, io, vin) if dev["r_hot"] is None else tcm_point(dev, vo, io, vin)
            cells.append(f"{o['p_hs']:.2f} / {o['p_ls']:.2f}" + (" (hard)" if o["hard"] else ""))
            s += o["p_hs"] + o["p_ls"]
        tot[name] = s
        iz = D["izvs"] if dev["r_hot"] is None else tcm_point(dev, 400, 0.3, 430)["izvs"]
        L.append(f"| {name} | {iz:.2f} | " + " | ".join(cells) + f" | {gate_ma(dev, 150e3):.0f} |")
    L += ["", "The frequency column of r1 holds for every device (same L and law); devices with more output charge need a "
          "larger reverse current (I_zvs) to swing the node in 300 ns, which makes the ripple and the RMS current larger. "
          "Conduction dominates everything but the IGBT; the IGBT's turn-off tail is r1's.", ""]
    # 2. hard commutation
    jobs = [(n, i, l, 480.0) for n in DEV if not n.startswith("IGBT") and not n.startswith("GaN +") for i in (0.8, 2.5) for l in (20e-9, 40e-9)]
    jobs += [(n, 2.5, 40e-9, 480.0, 20e-9) for n in ("SiC cascode UF3C065080T3S", "SiC MOSFET IMBG65R075M2H (0 V off, 18 V on)",
                                                     "e-mode GaN GS66504B (6 V)", "SJ CFD7 IPP65R190CFD7")]
    with Pool() as pool:
        res = pool.map(hard_event, jobs)
    L += ["## 2. Forced hard commutation (480 V raw; the high side turns on while the low side's reverse path carries I)", "",
          "Loop inductance between the bridge's 100 nF and the switch: 20 / 40 nH. Generic model (est.): turning-on switch as a resistance falling to R_on over the datasheet's rise time; the "
          "freewheeling device as Co(tr) plus a charge-control diode holding the datasheet's Qrr (snappy: pessimistic for the "
          "overshoot; the SiC cascode's datasheet Qrr 73 nC and the SiC MOSFET's Qfr 34 nC include their output charge, which is already the Co(tr) here, so 5 / 2 nC of true recovery charge are used); no RC snubber except the SiC cascode's required 5 ohm + 100 pF. The IGBT is M15's calibrated case. "
          "Energy per event in the turning-on device; 'every cycle' = that energy x f added to its TCM loss.", "",
          "| Device | I (A) | loop (nH) | peak current (A) | dv/dt (V/ns) | V peak at the switch node (V) / rating | energy per event (uJ) | every cycle at 40 / 150 kHz (W) |",
          "|---|---|---|---|---|---|---|---|"]
    for name, i0, ll, r in res:
        dev = DEV[name.split(", turn-on")[0]]
        L.append(f"| {name} | {i0} | {ll * 1e9:.0f} | {r['ipk']:.1f} | {r['dvdt']:.0f} | {r['vpk']:.0f} / {dev['vmax']} ({dev['vtr']} transient) | "
                 f"{r['e'] * 1e6:.1f} | {r['e'] * 40e3:.2f} / {r['e'] * 150e3:.2f} |")
    L += [f"| IGBT IKP08N65F5 (present) | 0.4-1.0 | 15 | ~14-17 (M15, Irrm of the snapping SPICE diode) | 20-50 | ~5 V overshoot with the real diode (M15) | 41-49 (M15: Qrr x V) | 1.8 / 7 |",
          "", "Reading: with a reverse path that has (almost) no recovered charge (both cascodes, e-mode GaN, SiC MOSFET) a "
          "forced hard turn-on costs the Coss charge of both devices times the rail plus the overlap: 10-40 uJ at 0.8-2.5 A, "
          "repeated every cycle 0.5-6 W: survivable for a second on the chassis, and every datasheet among them shows the device "
          "hard-switched (the cascode GaN 'in both hard- and soft-switched circuits'). The superjunction part dumps "
          "Qrr x V (0.4-0.8 uC typ / max at only 100 A/us) plus its huge Co(tr): 200-400 uJ per event, 10-60 W every cycle, "
          "and its body diode is rated to 70 V/ns: this is the failure mode the user means; it is out. "
          "The overshoot is set by the hard edge's rate against the loop inductance: at the datasheets' fastest rise times "
          "(5 ns) the SiC MOSFET and the e-mode GaN ring to 700-880 V with 20-40 nH, above 650 V (and the e-mode GaN's "
          "750 V < 1 us transient rating); slowed to a 20 ns turn-on (gate resistor) they stay near 500-560 V. The cascode GaN as "
          "the maker tests it (RG 70 ohm + 240 ohm bead: 50-65 V/ns) peaks at 490-530 V, with 800 V transient rating behind it; "
          "the SiC cascode with its required RC snubber at 590-680 V, but it is the one part with an avalanche rating (33 mJ).", ""]
    # 3. spurious turn-on, tab, +12 V
    L += ["## 3. Gate margin, chassis tab, gate supply", "",
          "Spurious turn-on: the off device's gate rises by C_rss / C_iss x dV (charge division, no driver help) or by "
          "R_sink x C_rss x dv/dt (driver holding the gate through about 2 ohm): TCM edges 4 V/ns, a forced hard edge at the "
          "device's own dv/dt (section 2). Tab: TO-220 on the 2 mm plate through a 1.5 mm Al2O3 washer (about 7 pF, 1 K/W) "
          "or a 0.23 mm silicone pad (about 21 pF, 0.5-1 K/W); common-mode current = C x dv/dt.", "",
          "| Device | V_th min hot (V) | charge-division bump at 420 V (V) | driver-held bump, TCM / hard (V) | negative rail needed? | "
          "switch-node tab | CM current 7 / 21 pF, TCM 4 V/ns / hard (A) | +12 V, 4 devices at 40 / 150 kHz (mA) | aval. / SC | price (est., USD) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    hard_dvdt = {n: max([r["dvdt"] for nn, i, l, r in res if nn == n] or [40]) for n in DEV}
    slowed = {nn.split(", turn-on")[0]: r["dvdt"] for nn, i, l, r in res if "slowed" in nn}
    hard_dvdt.update(slowed)
    for name, dev in DEV.items():
        if dev["crss"]:
            cd = dev["crss"] / (dev["crss"] + dev["ciss"]) * 420
            b1 = 2.0 * dev["crss"] * 4e9
            b2 = 2.0 * dev["crss"] * hard_dvdt[name] * 1e9
            neg = "no" if cd < dev["vth"] and b2 < 0.5 * dev["vth"] else ("no in TCM; hard events marginal" if b2 < dev["vth"] else "yes for hard events")
            sp = f"{dev['vth']:.1f} | {cd:.1f} | {b1:.2f} / {b2:.2f} | {neg}"
        else:
            sp = "— | — | — | own negative bias (internal buck-boost)"
        tabn = {"collector": "low side (collector tab)", "drain": "low side (drain tab)", "source": "high side (source tab)"}.get(dev["tab"], "SMD: switch node on the board pad, no chassis tab")
        cm = f"{7e-12 * 4e9:.2f}-{21e-12 * 4e9:.2f} / {7e-12 * hard_dvdt[name] * 1e9:.1f}-{21e-12 * hard_dvdt[name] * 1e9:.1f}" if "SMD" not in dev["tab"] else "— (board-level)"
        L.append(f"| {name} | {sp} | {tabn} | {cm} | {gate_ma(dev, 40e3):.0f} / {gate_ma(dev, 150e3):.0f} | {dev['aval']} / {dev['sc']} | {dev['cost']} |")
    L += ["", "In every TO-220 half-bridge one tab is the switch node: the low side's for drain / collector-tab parts, the high "
          "side's for the source-tab cascode GaN (its low side then has a quiet tab at the shunt, i.e. ground). Budget: 25 mA.", ""]
    # 4. fixed-frequency hard-switched alternative
    L += ["## 4. Fixed-frequency hard switching (no TCM) with the cascode GaN / SiC", "",
          "L1 470 uH, fixed f, both edges as they fall: the high side's turn-on is hard whenever the valley current is "
          "positive (about Qoss x V + Eoss + overlap; est.), the other edges soft. Same output filter as recommended "
          "(its first resonance moves to 0.65 kHz with 470 uH); residue at the power amp from r2's model.", "",
          "| Device, f | point | ripple p-p (A) | valley (A) | Q_hs / Q_ls (W) | residue at the power amp, ESR 0.3 (mV p-p) |",
          "|---|---|---|---|---|---|"]
    for name in ("GaN cascode TP65H150G4PS", "SiC cascode UF3C065080T3S"):
        dev = DEV[name]
        for f in (100e3, 150e3):
            for pn, vo, io, vin in PTS[:5]:
                Lh = 470e-6
                dcy = vo / vin
                di = vo * (1 - dcy) / (Lh * f)
                ival, ipk = io - di / 2, io + di / 2
                irms2 = io ** 2 + di ** 2 / 12
                # hard turn-on: Qoss(V) x V (the low side's Coss charged from the rail, the high side's own
                # Coss dumped in its channel) + the V-I overlap during the current rise (est.)
                ehard = dev["qoss"] * vin / 400 * vin + 0.5 * vin * max(ival, 0) * dev["tr"] if ival > 0 else 0.0
                p_hs = dev["r_hot"] * irms2 * dcy + f * ehard
                p_ls = dev["r_hot"] * irms2 * (1 - dcy)
                p = dict(filt.chain(filt.REC), L1=Lh, RL1=0.12)
                rr = r2.residue(p, f, vo, vin, 0.3, vo / io if io > 0 else None)[0]
                L.append(f"| {name.split(' ')[0]} {name.split(' ')[1]}, {f / 1e3:.0f} kHz | {pn} | {di:.2f} | {ival:+.2f} | {p_hs:.2f} / {p_ls:.2f} | {rr * 1e3:.1f} |")
    L += ["", "Hard switching costs the Coss charge at every period where the valley stays positive (400 V region): with the "
          "cascode GaN about 1.5-2.2 W at 100-150 kHz at full load, against 0.3 W in TCM; at 150-250 V the 470 uH ripple "
          "reverses the current by itself and the bridge is soft anyway. The edge rate of a hard edge (30-100 V/ns) puts "
          "0.2-2 A common-mode spikes through the switch-node tab's capacitance, against 30-80 mA in TCM.", ""]
    open(os.path.join(HERE, "r5_results.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
