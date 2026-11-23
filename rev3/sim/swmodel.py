#!/usr/bin/env python3
"""HV supplies rev 3: switching-level device models for ngspice (review M15 / M20), shared by
m15_bridge.py and m20_short_arc.py.

IKP08N65F5 (Infineon datasheet Rev 2.1, 2015-05-05; values read 2026-11-23):
  VCEsat 1.60 V (8 A, 25 C), 1.80 V (125 C), 1.90 V (175 C); VF 1.45 / 1.40 V (9 A, 25 / 125 C);
  VGE(th) 4.0 V typ (3.2-4.8) at 25 C; gfs 17 S (8 A); Cies 500 pF, Coes 16 pF, Cres 3 pF (25 V);
  QG 22 nC (520 V, 8 A, 15 V); ICpuls = IFpuls = 24 A; no short-circuit rating (Highspeed 5).
  Switching, inductive load, 400 V, VGE 0/15 V, RG 48 ohm, Lsigma 30 nH, Csigma 30 pF, energies
  "include tail and diode reverse recovery":
      150 C: 4 A Eon 0.10 / Eoff 0.03 mJ, td(off) 145 ns, tf 18 ns; 2 A Eon 0.06 / Eoff 0.02 mJ
       25 C: 4 A Eon 0.07 / Eoff 0.02 mJ;                           2 A Eon 0.04 / Eoff 0.02 mJ
  Diode (400 V, 800 A/us): 150 C Qrr 0.27 uC at 4 A, 0.19 uC at 2 A (Irrm 7.5 / 7.4 A, trr 56 / 42 ns);
                            25 C Qrr 0.14 / 0.10 uC.

Model (behavioural, not Infineon's physical model, which is not available here):
  collector -- Rc -- junction diode (the PNP's ~0.8 V knee) -- MOS channel K (Vge - Vth)^2 tanh(Vce/0.3) -- emitter
  Cge fixed; Cgc nonlinear (large when the collector is below the gate, junction-like above);
  anti-parallel diode with the Coes junction capacitance and a transit time TT (charge-control
  reverse recovery: Qrr = TT x IF); an exponential tail current after turn-off (alpha x I, tau).
  The diode's Qrr is set per operating point from the datasheet's own trend (qrr(): a power law
  through the 2 A and 4 A points, or a straight line with a floor as the pessimistic case); it is
  the dominant turn-on loss term.
  The double-pulse test of the datasheet is reproduced by calib() (m15_bridge.py prints it).

Inductor: the 3 mH ETD39 design (STATUS T5): L0 = 3 mH flat to the knee at 2.4 A, then the
gapped ferrite saturates: the incremental inductance falls to L0 / 30 over about 0.4 A (a smooth
flux model). DCR 1.2 ohm cold / 1.55 ohm hot. Winding capacitance estimated 25 pF (192 turns in
about 8 layers on an ETD39 bobbin, layer-to-layer, Cw ~ 4 C_layer / n_layers; 15-40 pF range).
"""
import os
import subprocess
import tempfile

import numpy as np

HOT = dict(tj=125.0, vth=2.9, rc=0.10, js=2.0e-6, jn=2.3, dis=2.0e-4, dn=2.6, drs=0.045)
COLD = dict(tj=25.0, vth=4.0, rc=0.07, js=1.0e-7, jn=2.0, dis=2.0e-6, dn=2.0, drs=0.06)


def qrr(i, tj=125.0, law="power"):
    """Datasheet trend of the diode's recovered charge (C) at 800 A/us. The datasheet gives two
    currents only (2 and 4 A); below them it is extrapolated: "power" fits Qrr ~ IF^0.51 through
    both points (0.134 uC at 1 A, tends to zero with the current: the baseline), "linear" fits a
    straight line (0.11 uC + 0.04 uC/A: a 0.11 uC floor at zero current, the pessimistic case)."""
    i = max(abs(i), 0.0)
    if law == "linear":
        a, b = (0.11e-6, 0.04e-6) if tj > 75 else (0.06e-6, 0.02e-6)
        return a + b * i
    q1, q2 = (0.19e-6, 0.27e-6) if tj > 75 else (0.10e-6, 0.14e-6)
    ex = np.log(q2 / q1) / np.log(2.0)
    return q1 * (i / 2.0) ** ex


def tt_for(i, tj=125.0, law="power"):
    """Transit time that makes the SPICE diode recover qrr(i) at forward current i."""
    i = max(abs(i), 0.02)
    return qrr(i, tj, law) / i


def models(tt_hi=60e-9, tt_lo=60e-9, temp=HOT, k=4.0, tail_a=0.40, tail_tau=80e-9, cw=25e-12):
    """ngspice text: IGBT subcircuit (with its anti-parallel diode; TT per instance through
    two diode models), ES1J, gate driver."""
    t = temp
    L = []
    # anti-parallel diode: SPICE charge-control diode, Qrr = TT x IF with TT from the datasheet
    # Qrr trend (qrr() above). A Lauritzen soft-recovery model was tried: it recovers the right
    # charge but puts the recovery loss into the diode, giving a turn-on energy 2-4x below the
    # datasheet's; the SPICE diode reproduces the datasheet Eon but snaps (an overshoot on the
    # switch node that the real Rapid 1 diode, dirr/dt -134 to -300 A/us, does not have).
    # Forward drop 1.40 V at 9 A hot (1.45 V cold); Coes 16 pF at 25 V on the junction.
    for name, tt in (("DFWH", tt_hi), ("DFWL", tt_lo)):
        L.append(f".model {name} D(IS={t['dis']:.3g} N={t['dn']} RS={t['drs']} TT={tt:.4g} CJO=75p VJ=0.7 M=0.5 BV=700 IBV=1u)")
    L.append(".model DCGC1 D(IS=1e-30 N=1 CJO=160p VJ=0.3 M=0.9 FC=0.5 BV=2000)")
    L.append(".model DCGC2 D(IS=1e-30 N=1 CJO=600p VJ=0.7 M=0.02 FC=0.5 BV=2000)")
    L.append(f".model DJ D(IS={t['js']:.3g} N={t['jn']} RS=0 CJO=20p)")
    # ES1J: 1 A, 600 V, trr 35 ns, VF ~ 1.0 V at 1 A
    L.append(".model DES1J D(IS=5n N=2.0 RS=0.15 TT=25n CJO=10p BV=650)")
    # IGBT: nodes c g e; tail current state in node qt
    L += [".subckt IGBT c g eo",
          "Le e eo 7n",
          "Rle e eo 50",
          f"Rc c c1 {t['rc']}",
          "Dj c1 ci DJ",
          f"Bch ci e I = {k}*pow(max(V(g,e)-{t['vth']},0),2)*tanh(V(ci,e)/0.3)",
          "Rleak ci e 1Meg",
          "Cci ci e 2p",
          "Cge g e 480p",
          # Cgc as an anti-series pair of non-conducting junctions: above the gate the collector
          # junction gives 160 pF / (1 + v/0.3)^0.9 (3.0 pF at 25 V: datasheet Cres 3 pF), below
          # it (on state) the gate junction gives about 600 pF (the oxide overlap)
          "Dgc1 xgc c DCGC1",
          "Dgc2 xgc g DCGC2",
          "Rgcx xgc g 1G",
          # tail: qt tracks alpha x channel current while on, decays with tail_tau when off
          f"Bqt 0 qt I = (V(g,e) > {t['vth']}+0.5) ? ({tail_a}*I(Vch)-V(qt))/5n : -V(qt)/{tail_tau}",
          "Cqt qt 0 1",
          "Rqt qt 0 1G",
          "Btail c e I = (V(g,e) < " + f"{t['vth']}" + ") ? max(V(qt),0)*tanh(max(V(c,e),0)/20) : 0",
          ".ends",
          ".subckt IGBTH c g e", "Xq c g e IGBT", "Dfw e c DFWH", ".ends",
          ".subckt IGBTL c g e", "Xq c g e IGBT", "Dfw e c DFWL", ".ends"]
    # the channel current probe: Bch can't be referenced by I(); use a zero-volt source
    txt = "\n".join(L)
    txt = txt.replace("Dj c1 ci DJ", "Dj c1 cj DJ\nVch cj ci 0")
    return txt


def inductor(name, a, b, l0=3e-3, isat=2.4, soft=0.4, ratio=30.0, dcr=1.55, cw=25e-12, i0=0.0, scale=1e3):
    """Saturating inductor between a and b: flux node phi (V = flux x scale) integrates the
    voltage across the ideal part, the current is i(phi). Below the knee i = phi / L0; above
    it the incremental inductance drops to L0 / ratio, smoothed over `soft` amperes."""
    ps = l0 * isat * scale
    sm = l0 * soft * scale
    n = name
    # i(phi) = phi/L0 + (ratio-1)/L0 * softplus(|phi| - ps) * sign(phi)
    expr = (f"(V({n}_phi)/{l0 * scale}) + ({ratio - 1}/{l0 * scale})*"
            f"({sm}*ln(1+exp((abs(V({n}_phi))-{ps})/{sm})))*sgn(V({n}_phi))")
    phi0 = i0 * l0 * scale
    return "\n".join([
        f"R{n} {a} {n}_m {dcr}",
        f"B{n} {n}_m {b} I = {expr}",
        f"B{n}v 0 {n}_phi I = V({n}_m,{b})",
        f"C{n}phi {n}_phi 0 {1.0 / scale} IC={phi0:.6g}",
        f"R{n}phi {n}_phi 0 1e12",
        f"C{n}w {a} {b} {cw}",
    ])


def run(netlist, outvecs, tstop, tstep, tmax, uic=True, timeout=1800, opts=""):
    """Run a transient and return a dict of numpy arrays (time + outvecs)."""
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "o.txt")
        cir = os.path.join(d, "c.cir")
        lines = [netlist,
                 f".options method=gear reltol=1e-3 abstol=1e-9 vntol=1e-4 itl4=100 {opts}",
                 ".control", "set wr_singlescale", "set wr_vecnames",
                 f"tran {tstep} {tstop} 0 {tmax}" + (" uic" if uic else ""),
                 f"wrdata {out} " + " ".join(outvecs), "quit", ".endc", ".end"]
        open(cir, "w").write("\n".join(lines) + "\n")
        r = subprocess.run(["ngspice", "-b", cir], capture_output=True, text=True, timeout=timeout)
        if not os.path.exists(out) or "aborted" in r.stdout + r.stderr:
            raise RuntimeError(r.stdout[-3000:] + r.stderr[-3000:])
        a = np.loadtxt(out, skiprows=1)
    res = {"t": a[:, 0]}
    for k, v in enumerate(outvecs):
        res[v] = a[:, k + 1]
    return res


def double_pulse(i_test, rg=48.0, temp=HOT, v=400.0, vge=15.0, rdrv=1.0, **kw):
    """Datasheet double-pulse test: low-side DUT, high-side diode (gate held off), 400 V,
    Lsigma 30 nH, Csigma 30 pF. Returns Eon, Eoff (J, the DUT; datasheet integration windows:
    from 10 % VGE to 2 % VCE (on) / 2 % IC (off), here a fixed window around each edge),
    the diode's recovered charge (C) and Irrm (A)."""
    tt = tt_for(i_test, temp["tj"])
    t1 = 3e-6
    lload = v * t1 / i_test
    t_off, t_on = t1, t1 + 2e-6
    net = "\n".join([
        "* double pulse",
        models(tt_hi=tt, tt_lo=tt, temp=temp, **kw),
        f"Vdc vdc 0 {v}",
        "Ls vdc n1 30n",
        "Rls vdc n1 100",
        "Cs n1 ncs 30p",
        "Rcs ncs 0 2",
        "Xhs n1 ghs sw IGBTH",
        "Rghs ghs sw 10",
        f"Ll n1 sw {lload}",
        "Vid sw swd 0",
        "Xls swd g 0 IGBTL",
        f"Vg gd 0 PULSE(0 {vge} 0.5u 5n 5n {t_off - 0.5e-6} 100u)",
        f"Vg2 gd2 0 PULSE(0 {vge} {t_on} 5n 5n 1u 100u)",
        f"Bgd gdd 0 V = max(V(gd), V(gd2))",
        f"Rg gdd g {rg + rdrv}",
    ])
    r = run(net, ["v(swd)", "i(Vid)", "v(g)"], t_on + 0.8e-6, "1n", "0.5n")
    t, vce, ic, vg = r["t"], r["v(swd)"], r["i(Vid)"], r["v(g)"]
    p = vce * ic
    m_off = (t > t_off - 20e-9) & (t < t_off + 0.6e-6)
    m_on = (t > t_on - 20e-9) & (t < t_on + 0.6e-6)
    eoff = np.trapezoid(p[m_off], t[m_off])
    # turn-on: subtract the conduction part after the transition (Vce sat x I) beyond 2 % VCE
    pon = np.where(vce > 0.02 * v, p, 0.0)
    eon = np.trapezoid(pon[m_on], t[m_on])
    # diode current = load current - DUT current during turn-on; reverse part = Qrr
    il = i_test + v * (t - t_on) / lload
    idio = np.where(m_on, il - ic, 0.0)
    q = -np.trapezoid(np.minimum(idio, 0.0), t)
    return dict(eon=eon, eoff=eoff, qrr=q, irrm=-idio.min(), tt=tt)


def calib(rows=((4.0, 48.0, HOT), (2.0, 48.0, HOT), (4.0, 48.0, COLD), (2.0, 48.0, COLD),
                (1.0, 16.5, HOT), (0.4, 16.5, HOT))):
    out = []
    for i, rg, temp in rows:
        out.append((i, rg, temp["tj"], double_pulse(i, rg=rg, temp=temp)))
    return out


if __name__ == "__main__":
    for i, rg, tj, d in calib():
        print(f"I {i} A RG {rg} Tj {tj}: Eon {d['eon'] * 1e6:.1f} uJ Eoff {d['eoff'] * 1e6:.1f} uJ "
              f"Qrr {d['qrr'] * 1e9:.0f} nC Irrm {d['irrm']:.2f} A (TT {d['tt'] * 1e9:.0f} ns)")
