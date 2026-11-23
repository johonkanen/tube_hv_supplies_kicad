#!/usr/bin/env python3
"""HV supplies rev 3, ripple-filter / soft-switching study, step 1a: the IGBT's turn-off and the
resonant transition of the switch node, with the calibrated model of swmodel.py (M15).

Test circuit (one edge, ngspice): raw 420 V behind 15 nH of commutation loop, Q201 (IGBTH) on for
3 us carrying a constant inductor current I out of the switch node (the inductor is a current source
at this time scale: 200 uH and 420 V give 2 A/us at most), Q202 (IGBTL) off, its gate held low by the
driver (15 ohm, 0.6 ohm sink, 10 kohm and the drawn 1 nF G-E at both IGBTs). Q201's gate is switched
off; the current then charges the node capacitance: both devices' own Coes (in the model) +
2 x Cs (a C0G snubber capacitor across each IGBT, "lossless" because in zero-voltage switching its
energy is never dumped into a channel) + 20 pF (winding, layout). Measured: Q201's turn-off energy
(channel + tail: the integral of Vce x Ic over the edge, the snubber's current not included), the time
from the gate command to the node reaching the other rail (5 % of 420 V) and the dv/dt.
The same test at small currents is the "valley" edge (the low side turning off a small negative
current), which only has to finish inside the dead time: t_comm(I) is that requirement.

Also: the hard-switched reference (Cs = 0, the other device's diode recovering: M15's 45 uJ turn-on)
and Tj 25 / 125 C.

Run: python3 rev3/sim/r1_turnoff.py   (writes r1_turnoff.json used by r1_softsw.py; about a minute)
"""
import json
import os
from multiprocessing import Pool

import numpy as np

import swmodel as sm

HERE = os.path.dirname(os.path.abspath(__file__))
V_RAW = 420.0
CURRENTS = (0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0)
CSNUB = (0.0, 100e-12, 220e-12, 470e-12, 1e-9)


def netlist(i, cs, temp, cge=1e-9, rg=15.0):
    tt = sm.tt_for(0.05, temp["tj"])
    t_off = 3e-6
    L = ["* r1 turn-off edge", sm.models(tt_hi=tt, tt_lo=tt, temp=temp),
         f"Vin vin 0 {V_RAW}", "Lloop vin c1 15n", "Rloop vin c1 50",
         "Vc1 c1 c1i 0", "Xq1 c1i gh sw IGBTH",
         "Vc2 sw c2i 0", "Xq2 c2i gl 0 IGBTL",
         f"Cs1 c1 sw {max(cs, 1e-15)}", f"Cs2 sw 0 {max(cs, 1e-15)}", "Cpar sw 0 20p",
         f"Iload sw 0 {i}",
         # high-side driver: on 0..t_off, then the 0.6 ohm sink
         f"Vdrv dh sw PULSE(15 0 {t_off} 2n 2n 10u 20u)",
         f"Rgh dh gh {rg}", "Rgeh gh sw 10k", f"Cgeh gh sw {max(cge, 1e-15)}",
         f"Rgl gl 0 {rg + 0.6}", "Rgel gl 0 10k", f"Cgel gl 0 {max(cge, 1e-15)}"]
    return "\n".join(L), t_off


def edge(args):
    i, cs, tj = args
    temp = sm.HOT if tj > 75 else sm.COLD
    net, t_off = netlist(i, cs, temp)
    r = sm.run(net, ["v(sw)", "v(c1)", "i(Vc1)", "i(Vc2)"], t_off + 2.5e-6, "0.5n", "1n", uic=False)
    t, vsw, vc1, ic1 = r["t"], r["v(sw)"], r["v(c1)"], r["i(Vc1)"]
    m = (t > t_off - 10e-9) & (t < t_off + 2.4e-6)
    p = (vc1 - vsw) * ic1
    # conduction part before the edge subtracted: only count while Vce > 2 V
    e = np.trapezoid(np.where((vc1 - vsw) > 2.0, p, 0.0)[m], t[m])
    k = np.where((t > t_off) & (vsw < 0.05 * V_RAW))[0]
    tcomm = (t[k[0]] - t_off) if len(k) else float("nan")
    k90 = np.where((t > t_off) & (vsw < 0.9 * V_RAW))[0]
    k10 = np.where((t > t_off) & (vsw < 0.1 * V_RAW))[0]
    dvdt = 0.8 * V_RAW / (t[k10[0]] - t[k90[0]]) * 1e-9 if len(k10) and len(k90) else float("nan")
    # tail charge: Q201's current after the node has left the rail by 20 V
    k20 = np.where((t > t_off) & (vsw < V_RAW - 20))[0]
    qtail = np.trapezoid(np.maximum(ic1, 0)[k20[0]:], t[k20[0]:]) if len(k20) else float("nan")
    return dict(i=i, cs=cs, tj=tj, eoff=e, tcomm=tcomm, dvdt=dvdt, qtail=qtail)


def main():
    cases = [(i, cs, tj) for tj in (125.0, 25.0) for cs in CSNUB for i in CURRENTS]
    with Pool() as pool:
        res = pool.map(edge, cases)
    json.dump(res, open(os.path.join(HERE, "r1_turnoff.json"), "w"), indent=1)
    for tj in (125.0, 25.0):
        print(f"Tj {tj}")
        for cs in CSNUB:
            row = [r for r in res if r["cs"] == cs and r["tj"] == tj]
            print(f" Cs {cs * 1e12:5.0f} pF: " + "  ".join(
                f"{r['i']:.2f}A {r['eoff'] * 1e6:5.1f}uJ {r['tcomm'] * 1e9:5.0f}ns" for r in row))


if __name__ == "__main__":
    main()
