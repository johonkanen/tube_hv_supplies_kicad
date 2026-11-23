#!/usr/bin/env python3
"""HV supplies rev 3, ripple-filter / soft-switching study, step 1: the soft-switching operating mode.

1. Design sweep (analytic, tcm.py, calibrated to r1_turnoff.py): inductance, snubber capacitance
   across each IGBT and the dead time allowed for the valley transition (which sets the reverse
   current I_zvs); losses of the bridge at the M15 operating points.
2. The chosen design at every M15 operating point, for V_ANODE (330 uH) and V_SCREEN (680 uH):
   frequency, currents, losses per device and in the inductor, junction temperatures, against M15.
   Variants: frequency from the voltage only (no load adaptation), fixed dead time, hard-switched
   reference.
3. Switching-level check with the calibrated IGBT model (ngspice, swmodel.py): one bridge in TCM at
   the chosen frequency and edge timing, the snubber capacitors, the UCC21520 drive as drawn
   (15 ohm, 10 kohm, 1 nF G-E, bootstrap), raw side as drawn; the output is C1 (100 uF) with the load
   current (the rest of the filter does not change the bridge's currents). Read: zero-voltage turn-on
   (switch-node voltage left across the device when its gate crosses V_th), losses per device,
   bootstrap, the switch node dv/dt and the Miller bump on the off device.
4. The MOSFET option (class-typical 650 V superjunction and SiC values, analytic).

Run: python3 rev3/sim/r1_softsw.py   (needs r1_turnoff.json from r1_turnoff.py; writes
r1_results.md and r1_*.png; a few minutes)
"""
import os
from multiprocessing import Pool

import numpy as np

import swmodel as sm
import tcm

HERE = os.path.dirname(os.path.abspath(__file__))
D = tcm.DESIGN
DS = tcm.DESIGN_SCREEN

# M15 operating points: name, V_out, I_out, V_raw, bridge (1 = anode, 2 = screen), M15 losses Q_hs / Q_ls (W)
POINTS = [
    ("A full load 400 V 0.70 A", 400, 0.70, 420, 1, (3.54, 0.27)),
    ("A' same, raw 430 V", 400, 0.70, 430, 1, None),
    ("B peak 403 V 0.80 A (raw 420 V)", 403, 0.80, 420, 1, (3.95, 0.27)),
    ("C idle KT88 400 V 0.30 A", 400, 0.30, 430, 1, (1.57, 0.26)),
    ("D light 400 V 0.05 A", 400, 0.05, 430, 1, (0.36, 0.25)),
    ("E no load 400 V", 400, 0.0, 430, 1, (0.27, 0.27)),
    ("F half voltage 200 V 0.35 A", 200, 0.35, 425, 1, (0.66, 0.22)),
    ("G half voltage no load 200 V", 200, 0.0, 425, 1, (0.43, 0.21)),
    ("low channel 150 V 0.20 A", 150, 0.20, 425, 1, None),
    ("H ramp-down 300 V -0.80 A", 300, -0.80, 425, 1, (0.29, 1.72)),
    ("I ramp-down 400 V -0.60 A", 400, -0.60, 425, 1, (0.30, 2.52)),
    ("start-up 20 V 0.5 A (charging)", 20, 0.5, 425, 1, None),
    ("start-up 5 V 0.5 A", 5, 0.5, 425, 1, None),
    ("L screen 390 V 0.18 A", 390, 0.18, 420, 2, (1.10, 0.25)),
    ("M screen peak 390 V 0.25 A", 390, 0.25, 420, 2, (1.46, 0.25)),
    ("screen 146 V 0.08 A (low channel)", 146, 0.08, 425, 2, None),
    ("screen ramp-down 300 V -0.3 A", 300, -0.30, 425, 2, None),
]


# ------------------------------------------------------------------ 1. sweep
def sweep():
    rows = []
    pts = [p for p in POINTS if p[0][0] in "ACEFG" or p[0].startswith("low")]
    pts = [p for p in pts if not p[0].startswith("A'")]
    for L in (150e-6, 220e-6, 330e-6, 470e-6):
        for cs in (0.0, 100e-12, 220e-12, 470e-12):
            for tv in (400e-9, 600e-9):
                d = dict(D, L=L, cs=cs, izvs=tcm.izvs_for(tv, cs), dt_max=tv, N=int(round(36 * np.sqrt(L / 220e-6))))
                corner = tcm.f_tcm(403, 0.8, 420, L, d["izvs"])
                tot = [tcm.operating_point(p[1], p[2], p[3], d) for p in pts]
                rows.append((L, cs, tv, d["izvs"], corner, tot))
    return rows, pts


# ------------------------------------------------------------------ 3. switching-level check
def bridge_netlist(vo, io, vin, d, f, ton, i0, adj=(0.0, 0.0)):
    """One bridge in TCM, current controlled (as a cycle-by-cycle TCM controller would do it): a
    latch turns the high side off when the inductor current reaches the peak of the operating point
    and back on when it reaches the valley, so the frequency follows (f of the operating law). The
    gate commands get the per-edge dead time (transition time + 30 ns, at least the UCC21520's
    200 ns) through delay lines. Gates and bootstrap as M15."""
    cs = d["cs"]
    o = tcm.operating_point(vo, io, vin, d, f=f)
    dtp = min(max(tcm.tcomm(o["ipk"], cs, vin) + 30e-9, 200e-9), d["dt_max"])
    dtv = min(max(tcm.tcomm(o["ival"], cs, vin) + 30e-9, 200e-9), d["dt_max"])
    # diode transit time: the SPICE diode's stored charge is TT x I with no recombination, so at the
    # slow zero crossings of TCM (di/dt = V / L, about 1 A/us) it must be the physical carrier
    # lifetime (about 60 ns: TT at 4 A in the datasheet fit, 0.27 uC / 4 A), giving the reverse
    # charge ~ TT^2 di/dt of a few nC; only where an edge is hard (valley not reversed) is the
    # datasheet's charge at 800 A/us used (M15)
    tt_lo = sm.tt_for(o["ival"], 125.0) if o["ival"] > 0.02 else 60e-9
    tt_hi = sm.tt_for(-o["ipk"], 125.0) if o["ipk"] < -0.02 else 60e-9
    # the latch compares the current at the moment the active device turns off: the transition
    # carries the current a little further, which is small (L large)
    ipk_t, ival_t = o["ipk"] + adj[0], o["ival"] + adj[1]
    L = ["* r1 TCM bridge", sm.models(tt_hi=tt_hi, tt_lo=tt_lo, temp=sm.HOT),
         f"Vpsu psu 0 {vin}", "Rpsu psu p1 0.3", "Lpsu p1 bp 1u",
         f"C101 bp c101 47u IC={vin}", "R101e c101 0 0.3",
         "L101 bp uin 33u", "R101l uin uin_ 0.01",
         f"C201 uin_ c201 47u IC={vin}", "R201e c201 0 0.3",
         f"C202 uin_ 0 100n IC={vin}", f"C203 uin_ 0 1n IC={vin}",
         "Lloop uin_ c1 15n", "Rloop uin_ c1 50",
         "Vc1 c1 c1i 0", "Xq1 c1i gh sw IGBTH",
         f"Cs1 c1 sw {max(cs, 1e-15)}", f"Cs2 sw is {max(cs, 1e-15)}", "Csw sw 0 10p",
         "Vc2 sw c2i 0", "Xq2 c2i gl is IGBTL",
         "Rsh is ish 0.05", "Lsh ish 0 1n",
         "V12 v12 0 12", "R304 v12 bs 2.2", "D301 bs boot DES1J",
         "Cb1 boot sw 0.8u", "Cb2 boot sw 100n", "Iqa boot sw 2m",
         # latch: q = 1 high-side phase, 0 low-side phase
         f"Bq qd 0 V = (I(Vil) > {ipk_t}) ? 0 : ((I(Vil) < {ival_t}) ? 1 : (V(q) > 0.5 ? 1 : 0))",
         "Rq qd q 1", "Cq q 0 2p IC=1",
         f"Tdv q 0 qv 0 Z0=50 TD={dtv}", "Rtv qv 0 50",
         f"Tdp q 0 qp 0 Z0=50 TD={dtp}", "Rtp qp 0 50",
         "Bch ch 0 V = (V(q) > 0.5 && V(qv) > 0.5) ? 1 : 0",
         "Bcl cl 0 V = (V(q) < 0.5 && V(qp) < 0.5) ? 1 : 0",
         "Buvh uvh 0 V = (V(boot,sw) > 8.2) ? 1 : 0", "Bdh ctlh 0 V = V(ch)*V(uvh)", "Bdhn ctlhn 0 V = 1-V(ctlh)",
         "Sup boot gdh ctlh 0 SWON", "Sdn gdh sw ctlhn 0 SWOFF",
         "Rgh gdh gh 15", "Rgeh gh sw 10k", "Cgeh gh sw 1n",
         "Bdl ctll 0 V = V(cl)", "Bdln ctlln 0 V = 1-V(ctll)",
         "Supl v12 gdl ctll 0 SWON", "Sdnl gdl is ctlln 0 SWOFF",
         "Rgl gdl gl 15", "Rgel gl is 10k", "Cgel gl is 1n",
         ".model SWON SW(VT=0.5 VH=0.05 RON=1.5 ROFF=1e7)",
         ".model SWOFF SW(VT=0.5 VH=0.05 RON=0.6 ROFF=1e7)",
         sm.inductor_par("L1", "sw", "uc", l0=d["L"], isat=4.0, soft=0.4, ratio=10.0,
                         dcr=tcm.winding(d["core"], d["N"], d["litz"])[0], cw=10e-12, i0=0.5 * (ival_t + io)),
         "Vil uc uc2 0",
         f"C204 uc2 c204 100u IC={vo}", "R204e c204 c204b 0.1", "L204e c204b 0 20n",
         f"Iload uc2 0 {io}"]
    ic = (f".ic v(uin)={vin} v(uin_)={vin} v(bp)={vin} v(c1)={vin} v(c101)=0 v(c201)=0 "
          f"v(uc)={vo} v(uc2)={vo} v(c204)=0 v(boot)={11.1} v(v12)=12 v(sw)=0 v(q)=1 v(qd)=1")
    return "\n".join(L) + "\n" + ic, dtp, dtv


OUT = ["v(sw)", "i(Vil)", "v(c1)", "i(Vc1)", "i(Vc2)", "v(is)", "v(boot)", "v(gh)", "v(gl)", "v(uc2)",
       "v(ctlh)", "v(ctll)"]


def sim_point(args):
    name, vo, io, vin, bridge = args
    d = D if bridge == 1 else DS
    o = tcm.operating_point(vo, io, vin, d)
    T0 = 1.0 / o["f"]
    n_per, n_meas = 22, 10
    # the average current follows from the thresholds and the transitions (the current keeps moving
    # while the node swings): shift both thresholds together until the average is the load current
    # (what the voltage loop does), keeping the valley threshold reversed (<= -0.1 A forward, the
    # peak >= +0.1 A in reverse)
    adj = (0.0, 0.0)
    for it in range(3):
        net, dtp, dtv = bridge_netlist(vo, io, vin, d, o["f"], None, o["ival"], adj)
        r = sm.run(net, OUT, n_per * T0, "2n", "5n", uic=True)
        mm = r["t"] > (n_per - n_meas) * T0
        e = np.mean(r["i(Vil)"][mm]) - io
        if abs(e) < 0.03:
            break
        sh = adj[0] - e
        if io >= 0:
            sh = min(sh, -0.1 - o["ival"])
        else:
            sh = max(sh, 0.1 - o["ipk"])
        if abs(sh - adj[0]) < 1e-3:
            break
        adj = (sh, sh)
    t = r["t"]
    vsw = r["v(sw)"]
    # whole periods: from high-side gate rising edges
    q = r["v(ctlh)"] > 0.5
    rises = t[1:][(~q[:-1]) & q[1:]]
    rises = rises[rises > (n_per - n_meas - 1) * T0]
    t0, t1 = rises[0], rises[-1]
    T = (t1 - t0) / (len(rises) - 1)
    m = (t >= t0) & (t <= t1)
    tt = t[m]
    span = tt[-1] - tt[0]

    def avg(x):
        return np.trapezoid(x[m], tt) / span
    p1 = avg((r["v(c1)"] - vsw) * r["i(Vc1)"])
    p2 = avg((vsw - r["v(is)"]) * r["i(Vc2)"])
    il = r["i(Vil)"][m]
    vgh = (r["v(gh)"] - vsw)[m]
    vgl = (r["v(gl)"] - r["v(is)"])[m]
    vce_h = (r["v(c1)"] - vsw)[m]
    vce_l = (vsw - r["v(is)"])[m]
    zh = [vce_h[k] for k in np.where((vgh[:-1] < 4.0) & (vgh[1:] >= 4.0))[0]]
    zl = [vce_l[k] for k in np.where((vgl[:-1] < 4.0) & (vgl[1:] >= 4.0))[0]]
    with np.errstate(divide="ignore", invalid="ignore"):
        dv = np.abs(np.diff(vsw[m]) / np.diff(tt)) * 1e-9
    dv = dv[np.isfinite(dv)]
    dvdt = float(np.percentile(dv[dv > 0.2], 95)) if np.any(dv > 0.2) else 0.0
    # gate of a device commanded off for more than 200 ns (Miller injection from the node's edges)
    def settled_off(ctl):
        c = ctl[m] > 0.5
        k = np.zeros(len(c), bool)
        last_on = -1.0
        for j in range(len(c)):
            if c[j]:
                last_on = tt[j]
            k[j] = (not c[j]) and (tt[j] - last_on > 200e-9)
        return k
    kh, kl = settled_off(r["v(ctlh)"]), settled_off(r["v(ctll)"])
    off_bump = max(float(np.max(vgh[kh])) if kh.any() else -9, float(np.max(vgl[kl])) if kl.any() else -9)
    return dict(name=name, f=1.0 / T, il_avg=avg(r["i(Vil)"]), il_max=float(il.max()), il_min=float(il.min()),
                p1=p1, p2=p2, zvs_h=max(zh) if zh else float("nan"), zvs_l=max(zl) if zl else float("nan"),
                boot_min=float((r["v(boot)"] - vsw)[m].min()), dvdt=dvdt, bump=off_bump, dtp=dtp, dtv=dtv,
                ana=o, r=r, T=T, t1=t1)


def plot(res, fn):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(len(res), 1, figsize=(8, 2.3 * len(res)))
    for ax, s in zip(axs, res):
        r = s["r"]
        t = r["t"]
        m = (t >= s["t1"] - 2 * s["T"]) & (t <= s["t1"])
        ax.plot(t[m] * 1e6, r["v(sw)"][m] / 100, lw=0.8, label="switch node / 100 (V)")
        ax.plot(t[m] * 1e6, r["i(Vil)"][m], lw=0.9, label="inductor (A)")
        ax.plot(t[m] * 1e6, (r["v(gh)"] - r["v(sw)"])[m] / 5, lw=0.6, label="Vge high / 5")
        ax.plot(t[m] * 1e6, (r["v(gl)"] - r["v(is)"])[m] / 5, lw=0.6, label="Vge low / 5")
        ax.axhline(0, color="k", lw=0.4)
        ax.set_title(f"{s['name']}: {s['f'] / 1e3:.0f} kHz", fontsize=9)
        ax.legend(fontsize=6, loc="upper right")
    axs[-1].set_xlabel("time (us)")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, fn), dpi=110)
    plt.close(fig)


# ------------------------------------------------------------------ 4. MOSFET option
MOSFETS = {
    # class-typical values (to confirm against a chosen datasheet): R_on at 125 C, output charge per
    # device at 420 V, gate charge at the drive voltage, turn-off energy under ZVS (channel off in
    # ~10 ns into C_oss + C_s: I^2 tf^2 / 24 C, < 0.1 uJ), drive voltage
    "650 V superjunction, fast body diode (CFD7 class, 0.19 ohm at 25 C)": dict(ron=0.38, qoss=70e-9, qg=30e-9, vg=12.0),
    "650 V SiC MOSFET (0.12 ohm class at 25 C)": dict(ron=0.17, qoss=25e-9, qg=30e-9, vg=15.0),
}


def mosfet_point(vo, io, vin, L, fmax, m, t_dt=300e-9):
    q = 2 * m["qoss"] + 20e-12 * vin
    izvs = q / t_dt
    d = dict(L=L, izvs=izvs, fmin=25e3, fmax=fmax, mode="adaptive", io_design=0.8)
    f = tcm.law(vo, io, vin, d)
    T = 1 / f
    dcy = vo / vin
    di = vo * (1 - dcy) / (L * f)
    ival, ipk = io - di / 2, io + di / 2
    irms2 = io ** 2 + di ** 2 / 12
    pc = m["ron"] * irms2           # total, both devices (the channel conducts in both directions)
    phs, pls = pc * dcy, pc * (1 - dcy)
    eoff = lambda i: (abs(i) ** 2 * (10e-9) ** 2 / (24 * (q / vin))) if True else 0
    phs += f * eoff(ipk)
    pls += f * eoff(ival)
    hard = (ival > 0) or (ipk < 0)
    pg = 2 * m["qg"] * m["vg"] * f
    return dict(f=f, di=di, ival=ival, ipk=ipk, phs=phs, pls=pls, izvs=izvs, hard=hard, pg=pg, i12=2 * m["qg"] * f)


def main():
    L = ["# Step 1: soft-switching operating mode (generated by r1_softsw.py)", "",
         __doc__.split("\n\n")[1].strip(), ""]
    # IGBT turn-off table
    import json
    to = [r for r in json.load(open(os.path.join(HERE, "r1_turnoff.json"))) if r["tj"] == 125.0]
    L += ["## The IGBT's turn-off with snubber capacitors (r1_turnoff.py, swmodel IGBT calibrated to the datasheet, 125 C, 420 V, 15 ohm + 1 nF G-E)", "",
          "Turn-off energy (uJ) / time from the gate command to the node at the other rail (ns). Cs is across each IGBT "
          "(the node sees 2 Cs + the devices' own charge + 20 pF). Cs = 0 is the hard turn-off (the datasheet's Eoff: 20 uJ at 2 A, 150 C, 48 ohm).", "",
          "| I (A) | " + " | ".join(f"Cs {int(c * 1e12)} pF" for c in sorted(set(r["cs"] for r in to))) + " |",
          "|---|" + "---|" * len(set(r["cs"] for r in to))]
    for i in sorted(set(r["i"] for r in to)):
        row = [r for r in to if r["i"] == i]
        row.sort(key=lambda r: r["cs"])
        L.append(f"| {i} | " + " | ".join(f"{r['eoff'] * 1e6:.1f} / {r['tcomm'] * 1e9:.0f}" if r["tcomm"] == r["tcomm"]
                                          else f"{r['eoff'] * 1e6:.1f} / > 2000" for r in row) + " |")
    L += ["", "Reading: the snubber only slows the voltage rise under the tail current; the tail charge itself "
          "(about 30 nC/A in the calibrated model, consistent with the datasheet's 20 uJ at 2 A) stays. "
          "220 pF cuts the turn-off energy by 45 % at 2 A, 470 pF by 65 %, 1 nF by 80 %, but the "
          "valley edge then needs 0.5 / 1.0 / 1.9 A of reverse current to swing the node in 500 ns, and that reverse "
          "current is ripple the IGBT turns off again at the peak.", ""]

    # sweep
    rows, pts = sweep()
    L += ["## 1. Design sweep (analytic, tcm.py): bridge loss Q_hs + Q_ls (W) at the operating points", "",
          f"f = clamp(f_TCM, {D['fmin'] / 1e3:.0f} kHz, {D['fmax'] / 1e3:.0f} kHz) with the load-adaptive law; I_zvs from the dead time allowed at the valley edge; "
          f"'corner f' = f_TCM at 403 V / 0.8 A / raw 420 V (below {D['fmin'] / 1e3:.0f} kHz the valley is only partly reversed there). "
          "Losses of the two IGBTs only (the inductor is in the variants table).", "",
          "| L (uH) | Cs (pF) | valley dead time (ns) | I_zvs (A) | corner f (kHz) | " +
          " | ".join(p[0].split(" ")[0] + (" " + p[0].split(" ")[1] if p[0].startswith("low") else "") for p in pts) + " | sum |",
          "|---|---|---|---|---|" + "---|" * (len(pts) + 1)]
    for Lh, cs, tv, iz, corner, tot in rows:
        s = [o["p_hs"] + o["p_ls"] for o in tot]
        L.append(f"| {Lh * 1e6:.0f} | {cs * 1e12:.0f} | {tv * 1e9:.0f} | {iz:.2f} | {corner / 1e3:.0f} | " +
                 " | ".join(f"{x:.2f}" for x in s) + f" | {sum(s):.1f} |")
    m15 = [p[5] for p in pts]
    L.append("| M15 hard-switched, 3 mH, 50 kHz | 0 | 200 | — | — | " + " | ".join(
        f"{a + b:.2f}" if (a, b) != (None, None) and p is not None else "—" for p in m15 for a, b in [p or (None, None)]) + " | — |")
    L += ["", "Reading: the turn-off energy is roughly proportional to the current turned off, and in TCM the "
          "current turned off per second is the ripple slope V_o (1 - D) / L, whatever the frequency. So the IGBT "
          "bridge's loss at mid voltage is set by L alone (about 7 uJ per ampere x V_o (1 - D) / L), "
          "while the frequency at the top of the range falls as 1 / L: the two ends pull L in opposite directions. "
          "Raising f_max does not lower the mid-voltage loss (it only lowers the ripple and the core loss).", ""]

    # chosen design
    L += ["## 2. Chosen design", "",
          f"V_ANODE: L = {D['L'] * 1e6:.0f} uH ({D['core']}, {D['N']} turns litz {D['litz'] * 1e6:.1f} mm2), "
          f"Cs = {D['cs'] * 1e12:.0f} pF C0G 1 kV across each IGBT, valley dead time up to {D['dt_max'] * 1e9:.0f} ns "
          f"(I_zvs = {D['izvs']:.2f} A), f = clamp(f_TCM, {D['fmin'] / 1e3:.0f} kHz, {D['fmax'] / 1e3:.0f} kHz), load-adaptive. "
          f"V_SCREEN: L = {DS['L'] * 1e6:.0f} uH ({DS['core']}, {DS['N']} turns litz {DS['litz'] * 1e6:.1f} mm2), same rest. "
          "Tj at 80 C local air: on an SK 104 38.1 mm (12 K/W + 1 K/W pad + 2.2 K/W) or free-standing (62 K/W).", "",
          "| Point | f (kHz) | ripple p-p (A) | peak / valley (A) | I_rms (A) | Q_hs: total / conduction (W) | Q_ls: total / conduction (W) | "
          "hard edges per period | M15 Q_hs / Q_ls (W) | Tj Q_hs on SK 104 / Q_ls free (C) | inductor copper / core (W), B_pk (T) | gate +12 V (mA, 2 IGBTs) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    chosen = {}
    for name, vo, io, vin, br, ref in POINTS:
        d = D if br == 1 else DS
        o = tcm.operating_point(vo, io, vin, d)
        chosen[name] = o
        refs = f"{ref[0]:.2f} / {ref[1]:.2f}" if ref else "—"
        L.append(f"| {name} | {o['f'] / 1e3:.0f} | {o['di']:.2f} | {o['ipk']:.2f} / {o['ival']:.2f} | {o['irms']:.2f} | "
                 f"{o['p_hs']:.2f} / {o['pc_hs']:.2f} | {o['p_ls']:.2f} / {o['pc_ls']:.2f} | {o['hard']} | {refs} | "
                 f"{tcm.tj(o['p_hs']):.0f} / {tcm.tj(o['p_ls'], sink=False):.0f} | {o['pcu']:.2f} / {o['pcore']:.2f}, {o['bpk']:.2f} | {o['i12'] * 1e3:.1f} |")
    # variants
    L += ["", "### Variants at three points (V_ANODE bridge, total Q_hs + Q_ls + inductor, W)", "",
          "| Variant | A full load 400 V 0.70 A | C idle 400 V 0.30 A | G 200 V no load | low channel 150 V 0.2 A |", "|---|---|---|---|---|"]
    var = [("chosen (adaptive law, adaptive dead time)", D),
           ("frequency from the voltage only (designed for 0.8 A)", dict(D, mode="voltage")),
           ("fixed dead time 600 ns on both edges", dict(D, dt_adaptive=False, dt_fixed=600e-9)),
           ("f_max 100 kHz (keeps the 1 nF G-E capacitors inside the +12 V budget)", dict(D, fmax=100e3)),
           ("L 330 uH, f 25-100 kHz (lowest loss; needs R8 relaxed to >= 25 kHz)", dict(D, L=330e-6, N=44, fmin=25e3, fmax=100e3)),
           ("L 470 uH, f 25-100 kHz (valley no longer reversed at the 400 V corner)", dict(D, L=470e-6, N=52, fmin=25e3, fmax=100e3)),
           ("N87 instead of N97", dict(D, core="ETD39 N87"))]
    vp = [("A full load 400 V 0.70 A", 400, 0.7, 420), ("C", 400, 0.3, 430), ("G", 200, 0.0, 425), ("low", 150, 0.2, 425)]
    for vn, dv in var:
        cells = []
        for _, vo, io, vin in vp:
            o = tcm.operating_point(vo, io, vin, dv)
            cells.append(f"{o['p_hs'] + o['p_ls'] + o['pcu'] + o['pcore']:.2f} ({o['f'] / 1e3:.0f} kHz)")
        L.append(f"| {vn} | " + " | ".join(cells) + " |")

    # switching-level check
    sel = [p for p in POINTS if p[0][0] in "ABCEFGHL" or p[0].startswith("low") or p[0].startswith("start-up 20")]
    sel = [p for p in sel if not p[0].startswith("A'")]
    with Pool() as pool:
        sres = pool.map(sim_point, [(p[0], p[1], p[2], p[3], p[4]) for p in sel])
    plot([s for s in sres if s["name"][0] in "ACGH"], "r1_tcm_waveforms.png")
    L += ["", "## 3. Switching-level check (ngspice, calibrated IGBT model, Tj 125 C)", "",
          "Vce at turn-on = the voltage left across the device when its gate crosses 4 V (0 = full zero-voltage turn-on). "
          "Dead times per edge: the transition time + 30 ns, at least the UCC21520's 200 ns (R303 / R311 20k).", "",
          "| Point | f (kHz) | iL avg / min / max (A) | Q_hs / Q_ls model (W) | Q_hs / Q_ls analytic (W) | Vce at turn-on hs / ls (V) | "
          "dead time peak / valley edge (ns) | dv/dt (V/ns) | off-gate bump (V) | bootstrap min (V) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for s in sres:
        o = s["ana"]
        L.append(f"| {s['name']} | {s['f'] / 1e3:.0f} | {s['il_avg']:.2f} / {s['il_min']:.2f} / {s['il_max']:.2f} | "
                 f"{s['p1']:.2f} / {s['p2']:.2f} | {o['p_hs']:.2f} / {o['p_ls']:.2f} | {s['zvs_h']:.0f} / {s['zvs_l']:.0f} | "
                 f"{s['dtp'] * 1e9:.0f} / {s['dtv'] * 1e9:.0f} | {s['dvdt']:.1f} | {s['bump']:.2f} | {s['boot_min']:.2f} |")

    # MOSFET option
    L += ["", "## 4. The MOSFET option (analytic, class-typical values to confirm on a datasheet)", "",
          "Same TCM law, L = 150 uH, f 25-300 kHz (200 kHz keeps 4 gates inside the +12 V budget), 300 ns transitions. Under ZVS a MOSFET's turn-off is "
          "nearly lossless (the channel stops in about 10 ns and the current moves into C_oss), so the loss is conduction only.", "",
          "| Device | Point | f (kHz) | peak / valley (A) | Q_hs / Q_ls (W) | gate +12 V (mA, 2 devices) |", "|---|---|---|---|---|---|"]
    for mn, mm in MOSFETS.items():
        for name, vo, io, vin, br, ref in POINTS:
            if name[0] not in "ACFG" and not name.startswith("low"):
                continue
            if name.startswith("A'"):
                continue
            q = mosfet_point(vo, io, vin, 150e-6, 300e3, mm)
            L.append(f"| {mn} | {name} | {q['f'] / 1e3:.0f} | {q['ipk']:.2f} / {q['ival']:.2f} | {q['phs']:.2f} / {q['pls']:.2f} | {q['i12'] * 1e3:.1f} |")
    open(os.path.join(HERE, "r1_results.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
