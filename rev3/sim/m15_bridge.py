#!/usr/bin/env python3
"""HV supplies rev 3, review M15: switching-level model of one bridge (ngspice, swmodel.py).

Circuit (sheet 02 / 03 as drawn, bridge 1 unless stated):
  raw 420 V (PSU behind 0.3 ohm + 1 uH, C101 47 uF on B_P, L101 33 uH) -> UIN1 with C201 47 uF
  (ESR 0.3 ohm) + C202 100 nF + C203 1 nF and 15 nH of commutation-loop inductance;
  Q201 / Q202 IKP08N65F5 (swmodel IGBT + Rapid 1 diode, Tj 125 C), 50 mohm shunt R202 (1 nH) in
  Q202's emitter; L201 3 mH ETD39 (DCR 1.55 ohm hot, Cw 25 pF, knee 2.4 A); C204 100 uF (ESR 0.15 ohm,
  20 nH) returned through the 50 mohm I_C shunt; L202 33 uH || R204 5.6 ohm; C205 1 uF film; R205
  1.0 ohm (bridge 2: 2.2 ohm) to the tab; 220 kohm bleeder; W04 cable 0.5 uH / 50 mohm to the power
  amp's 100 nF and the load (a current source: the tubes are a current load at these time scales).
  UCC21520: high side from the bootstrap (+12 V -> 2.2 ohm -> ES1J -> 1 uF X7R (0.7 uF at 12 V bias)
  + 100 nF), 2 mA VDDA quiescent, outputs 1.5 ohm up / 0.6 ohm down, 15 ohm gate resistors, 10 kohm
  gate-emitter. Hardware dead time DT on every rising edge (R303 / R311: DT(ns) ~ 10 x R(kohm)),
  driver delay mismatch 5 ns + pulse-width distortion 6 ns applied against the dead time.
  PWM: 50 kHz centre-aligned, duty set per case; each case is run twice (the switch-node average
  of the first run corrects the duty) from the averaged steady state, so the output sits at its
  operating point without a control loop; 25 periods, the last 15 measured.

Limits: behavioural IGBT (calibrated to the datasheet's double-pulse energies at 2 / 4 A, 48 ohm,
within 10 % at 150 C, 25 % at 25 C; Irrm about 2.5x the datasheet's because the model's turn-on
di/dt is higher); diode Qrr from the datasheet trend at 800 A/us (a faster turn-on raises it:
+30 % Qrr is the sensitivity case); no layout parasitics beyond the stated ones; one temperature
(125 C) for the losses; the gate driver as switches (no propagation delay modelled except the
mismatch); the control loop is not in this model (loop_digital.py has it).

Run: python3 rev3/sim/m15_bridge.py   (writes m15_results.md, m15_*.png; a few minutes)
"""
import os
from multiprocessing import Pool

import numpy as np

import hvnet
import swmodel as sm

HERE = os.path.dirname(os.path.abspath(__file__))
F_SW = 50e3
T = 1.0 / F_SW
N_PER, N_MEAS = 25, 15

BASE = dict(v_raw=420.0, v_out=400.0, i_out=0.7, rs=1.0, dt=200e-9, v12=12.0, cboot=0.8e-6, rg=15.0,
            tj=125.0, qrr_k=1.0, qrr_law="power", esr=0.15, cw=25e-12, d=None, skew=11e-9, bridge=1)


def duty_guess(p):
    """Averaged switch-node voltage needed, and the duty that gives it (dead time and drops)."""
    i = p["i_out"]
    vsw = p["v_out"] + i * (1.55 + 0.1 + p["rs"] + 0.05)
    # forward current: the switch node sits on the low-side diode during both dead times
    dt_eff = p["dt"] / T * (1 if i > 0.36 else (0 if i < -0.36 else 0.5))
    d = (vsw + 0.9 * np.sign(i)) / p["v_raw"] + dt_eff
    return d


def lin_ripple(p, d, nh=40):
    """Switching ripple from the averaged linear network (hvnet variant B) driven by the ideal
    PWM switch-node waveform (harmonics 1..nh): tab ripple p-p and the C204 ripple current rms.
    Free of the switching model's diode-snap artefacts."""
    pp = hvnet.params("B", ESR=p["esr"], Rs=p["rs"])
    f = F_SW * np.arange(1, nh + 1)
    rl = p["v_out"] / p["i_out"] if p["i_out"] > 1e-3 else None
    n = hvnet.network(pp, f, rl)
    h = np.arange(1, nh + 1)
    ch = p["v_raw"] * 2 / (h * np.pi) * np.sin(h * np.pi * d)
    tt = np.linspace(0, 1 / F_SW, 2000, endpoint=False)
    v = sum(np.real(ch[k] * n["Gvd"][k] * np.exp(2j * np.pi * f[k] * tt)) for k in range(nh))
    i_rms = np.sqrt(np.sum(np.abs(ch * n["Gid"]) ** 2) / 2)
    return np.ptp(v), i_rms


def gate_extra(tag, drv, g, e, p):
    """Optional turn-off path (fast diode + rg_off from the gate back to the driver) and an
    external gate-emitter capacitor."""
    out = []
    if p.get("rg_off"):
        out += [f"Dgo{tag} {g} xgo{tag} DGOFF", f"Rgo{tag} xgo{tag} {drv} {p['rg_off']}"]
    if p.get("cge"):
        out += [f"Cgex{tag} {g} {e} {p['cge']}"]
    return "\n".join(out) if out else "* no extra gate parts"


def netlist(p, d):
    """ngspice netlist of one bridge at duty d (command, before the dead time)."""
    # ripple estimate for the initial inductor current and TT of the two diodes
    i = p["i_out"]
    dI = (p["v_raw"] - p["v_out"]) * p["v_out"] / p["v_raw"] / (3e-3 * F_SW)
    i_valley, i_peak = i - dI / 2, i + dI / 2
    # Q202's diode recovers at Q201's turn-on (valley current, if positive); Q201's diode recovers
    # at Q202's turn-on (the peak current, if negative)
    tt_lo = sm.tt_for(max(i_valley, 0.02), p["tj"], p["qrr_law"]) * p["qrr_k"]
    tt_hi = sm.tt_for(max(-i_peak, 0.02), p["tj"], p["qrr_law"]) * p["qrr_k"]
    temp = sm.HOT if p["tj"] > 75 else sm.COLD
    dt = p["dt"]
    # high side on (1-d)T/2 + dt .. (1+d)T/2 - skew ; low side (1+d)T/2 + dt .. T + (1-d)T/2 - skew
    # (the skew eats into the dead time at the falling edges: worst-case driver mismatch)
    h_on, h_w = (1 - d) * T / 2 + dt, d * T - dt + p["skew"]
    l_on, l_w = (1 + d) * T / 2 + dt, (1 - d) * T - dt + p["skew"]
    vout = p["v_out"]
    v_uc = vout + i * (p["rs"] + 0.1)
    L = ["* M15 bridge", sm.models(tt_hi=tt_hi, tt_lo=tt_lo, temp=temp),
         # raw side
         f"Vpsu psu 0 {p['v_raw']}", "Rpsu psu p1 0.3", "Lpsu p1 bp 1u",
         f"C101 bp c101 47u IC={p['v_raw']}", "R101e c101 0 0.3",
         "L101 bp uin 33u", "R101l uin uin_ 0.01",
         f"C201 uin_ c201 47u IC={p['v_raw']}", "R201e c201 0 0.3",
         f"C202 uin_ 0 100n IC={p['v_raw']}", f"C203 uin_ 0 1n IC={p['v_raw']}",
         "Lloop uin_ c1 15n", "Rloop uin_ c1 50",
         # bridge
         "Vc1 c1 c1i 0", "Xq1 c1i gh sw IGBTH", "Csw sw 0 20p",
         "Vc2 sw c2i 0", "Xq2 c2i gl is IGBTL",
         "Rsh is ish 0.05", "Lsh ish 0 1n",
         # gate drive: high side from the bootstrap
         f"V12 v12 0 {p['v12']}", "R304 v12 bs 2.2", "D301 bs boot DES1J",
         f"Cb1 boot sw {p['cboot']}", "Cb2 boot sw 100n",
         "Iqa boot sw 2m",
         f"Vch ch 0 PULSE(0 1 {h_on} 5n 5n {max(h_w, 1e-9)} {T})" if h_w > 0 else "Vch ch 0 0",
         f"Vcl cl 0 PULSE(0 1 {l_on} 5n 5n {max(l_w, 1e-9)} {T})" if l_w > 0 else "Vcl cl 0 0",
         # UVLO (UCC21520: VDD off 8.2 V typ, on 8.7 V typ, 9.2 V max): output low below 8.2 V
         "Buvh uvh 0 V = (V(boot,sw) > 8.2) ? 1 : 0",
         "Bdh ctlh 0 V = V(ch)*V(uvh)",
         "Bdhn ctlhn 0 V = 1-V(ctlh)",
         "Sup boot gdh ctlh 0 SWON", "Sdn gdh sw ctlhn 0 SWOFF",
         f"Rgh gdh gh {p['rg']}", "Rgeh gh sw 10k",
         gate_extra("h", "gdh", "gh", "sw", p),
         "Buvl uvl 0 V = (V(v12) > 8.2) ? 1 : 0",
         "Bdl ctll 0 V = V(cl)*V(uvl)",
         "Bdln ctlln 0 V = 1-V(ctll)",
         "Supl v12 gdl ctll 0 SWON", "Sdnl gdl 0 ctlln 0 SWOFF",
         f"Rgl gdl gl {p['rg']}", "Rgel gl is 10k",
         gate_extra("l", "gdl", "gl", "is", p),
         ".model SWON SW(VT=0.5 VH=0.05 RON=1.5 ROFF=1e7)",
         ".model DGOFF D(IS=2n N=1.8 RS=0.5 TT=4n CJO=2p)",
         ".model SWOFF SW(VT=0.5 VH=0.05 RON=0.6 ROFF=1e7)",
         # inductor and output filter
         sm.inductor("L1", "sw", "uc", dcr=1.55, cw=p["cw"], i0=i),
         "Vil uc uc2 0",
         f"C204 uc2 c204 100u IC={v_uc}", f"R204e c204 c204b {p['esr']}", "L204e c204b ic 20n",
         "Rsh2 ic 0 0.05",
         f"L202 uc2 l2 33u IC={i}", "R202l l2 vo 0.1", "R204d uc2 vo 5.6",
         f"C205 vo c205 1u IC={vout + i * p['rs']}", "R205e c205 c205b 0.02", "L205e c205b 0 15n",
         f"R205 vo tab {p['rs']}", "Rbl tab 0 220k",
         "Lw tab pa 0.5u", "Rw pa pa2 0.05", f"Cpa pa2 0 100n IC={vout}",
         f"Iload pa2 0 {i}",
         ]
    return "\n".join(L), (i_valley, i_peak)


def initial_ic(p, net):
    """Append node ICs at the averaged steady state."""
    i = p["i_out"]
    vout = p["v_out"]
    v_uc = vout + i * (p["rs"] + 0.1)
    vo = vout + i * p["rs"]
    ic = (f".ic v(uin)={p['v_raw']} v(uin_)={p['v_raw']} v(bp)={p['v_raw']} v(c1)={p['v_raw']} "
          f"v(c101)=0 v(c201)=0 v(uc)={v_uc} v(uc2)={v_uc} v(c204)=0 v(vo)={vo} "
          f"v(tab)={vout} v(pa)={vout} v(pa2)={vout} v(boot)={p['v12'] - 0.9} v(v12)={p['v12']}")
    return net + "\n" + ic + f"\n.ic v(c205)=0 v(l2)={vo}"


OUT = ["v(sw)", "i(Vil)", "v(tab)", "v(pa2)", "v(uc)", "v(vo)", "v(c1)", "i(Vc1)", "i(Vc2)", "v(is)",
       "v(boot)", "v(gh)", "v(gl)", "v(uin)", "i(v.xq1.xq.vch)", "i(v.xq2.xq.vch)", "v(ctlh)", "v(ctll)"]


def simulate(p, d):
    net, (iv, ipk) = netlist(p, d)
    net = initial_ic(p, net)
    r = sm.run(net, OUT, N_PER * T, "2n", "4n", uic=True)
    return r, (iv, ipk)


def analyse(p, r):
    t = r["t"]
    t0 = (N_PER - N_MEAS) * T
    m = t >= t0
    tt = t[m]
    span = tt[-1] - tt[0]

    def avg(x):
        return np.trapezoid(x[m], tt) / span

    v_sw = r["v(sw)"]
    il = r["i(Vil)"]
    p1 = (r["v(c1)"] - v_sw) * r["i(Vc1)"]                     # Q201 + its diode
    p2 = (v_sw - r["v(is)"]) * r["i(Vc2)"]                     # Q202 + its diode
    # conduction part: power while the device is "on" (|Vce| < 5 V), the rest is switching
    on1 = np.abs(r["v(c1)"] - v_sw) < 5.0
    on2 = np.abs(v_sw - r["v(is)"]) < 5.0
    # switching ripple: the waveform rebuilt from its 50 kHz harmonics 1-10 (to 500 kHz) over the
    # integer number of measured periods. The model's diode snaps and rings the switch node at tens
    # of MHz through the winding capacitance; that part is set by the layout and the real (soft)
    # diode, not by this model, and is left out here.
    nh = 10
    tu = np.linspace(t0, t0 + N_MEAS * T, 200 * N_MEAS, endpoint=False)

    def lp_pp(x):
        y = np.interp(tu, tt, x[m])
        y = y - np.polyval(np.polyfit(tu - tu[0], y, 2), tu - tu[0])   # slow drift out
        c = np.fft.rfft(y)
        keep = np.zeros_like(c)
        for h in range(1, nh + 1):
            keep[h * N_MEAS] = c[h * N_MEAS]
        return np.ptp(np.fft.irfft(keep, len(y)))

    def band(x):
        y = np.interp(tu, tt, x[m])
        y0 = y - np.polyval(np.polyfit(tu - tu[0], y, 2), tu - tu[0])
        c = np.fft.rfft(y0)
        keep = np.zeros_like(c)
        for h in range(1, nh + 1):
            keep[h * N_MEAS] = c[h * N_MEAS]
        return np.mean(y) + np.fft.irfft(keep, len(y))

    ilb = band(il)
    res = dict(vsw=avg(v_sw), il=avg(il), il_pp=np.ptp(ilb), il_max=ilb.max(), il_min=ilb.min(),
               p1=avg(p1), p1c=avg(np.where(on1, p1, 0.0)), p2=avg(p2), p2c=avg(np.where(on2, p2, 0.0)),
               tab_pp=lp_pp(r["v(tab)"]), pa_pp=lp_pp(r["v(pa2)"]), uc_pp=lp_pp(r["v(uc)"]),
               vo_pp=lp_pp(r["v(vo)"]), tab_hf=np.ptp(r["v(tab)"][m]), pa_hf=np.ptp(r["v(pa2)"][m]), tab=avg(r["v(tab)"]),
               boot_min=(r["v(boot)"] - v_sw)[m].min(), boot_avg=avg(r["v(boot)"] - v_sw),
               uin_pp=np.ptp(r["v(uin)"][m]), sw_max=v_sw[m].max(), sw_min=v_sw[m].min())
    # gate interlock: the off device's gate never above Vth (3.3 V hot) while the other conducts
    vth = 3.3 if p["tj"] > 75 else 4.0
    vgh = r["v(gh)"] - v_sw
    vgl = r["v(gl)"] - r["v(is)"]
    both = (vgh > vth) & (vgl > vth)
    res["overlap_ns"] = np.trapezoid(both[m].astype(float), tt) / N_MEAS * 1e9
    # dead-time margin from the channel currents: for every edge, the time from one channel
    # dropping below 50 mA to the other rising above 50 mA (the tail current is in parallel with
    # the channel and is counted with the turn-off energy, not here); negative = overlap
    ch1, ch2 = r["i(v.xq1.xq.vch)"][m], r["i(v.xq2.xq.vch)"][m]
    on1, on2 = ch1 > 0.05, ch2 > 0.05
    res["overlap_ns"] = np.trapezoid((on1 & on2).astype(float), tt) / N_MEAS * 1e9
    # per edge: from the turning-off device's channel current settling below 50 mA (after its
    # driver went low) to the other gate crossing Vth while its own driver is high. Miller blips of
    # the off device during the snap are reported as the gate bump, not here.
    ctl_h, ctl_l = r["v(ctlh)"][m] > 0.5, r["v(ctll)"][m] > 0.5
    marg = []
    for off_ctl, off_ch, on_ctl, on_vg in ((ctl_h, ch1, ctl_l, vgl[m]), (ctl_l, ch2, ctl_h, vgh[m])):
        for j in np.where(np.diff(off_ctl.astype(int)) == -1)[0]:
            k = j
            while k < len(tt) - 1 and (off_ch[k] > 0.05 or off_ch[min(k + 5, len(tt) - 1)] > 0.05):
                k += 1
            q = np.where(on_ctl[j:] & (on_vg[j:] > vth))[0]
            if len(q) and k < len(tt) - 1:
                marg.append(tt[j + q[0]] - tt[k])
    res["dt_margin_ns"] = min(marg) * 1e9 if marg else float("nan")
    # Miller-induced gate bump on the off device (dv/dt through Cgc)
    res["vgl_off_max"] = np.max(np.where(r["v(gl)"][m] - r["v(is)"][m] < 2.0, vgl[m], -9))
    res["vgh_off_max"] = np.max(np.where(vgh[m] < 2.0, vgh[m], -9))
    # switch-node edge rate: 10-90 % of the rail, median over the edges
    vr = p["v_raw"]
    up = (v_sw[m] > 0.9 * vr).astype(int)
    lo = (v_sw[m] < 0.1 * vr).astype(int)
    edges = []
    last_lo = last_hi = None
    for j in range(1, len(tt)):
        if lo[j - 1] and not lo[j]:
            last_lo = tt[j]
        if up[j] and not up[j - 1] and last_lo is not None:
            edges.append(0.8 * vr / max(tt[j] - last_lo, 1e-12)); last_lo = None
        if up[j - 1] and not up[j]:
            last_hi = tt[j]
        if lo[j] and not lo[j - 1] and last_hi is not None:
            edges.append(0.8 * vr / max(tt[j] - last_hi, 1e-12)); last_hi = None
    res["dvdt"] = float(np.median(edges)) * 1e-9 if edges else float("nan")
    return res


def run_case(args):
    name, kw = args
    p = dict(BASE, **kw)
    d0 = p["d"] if p["d"] is not None else duty_guess(p)
    r, rip = simulate(p, d0)
    a = analyse(p, r)
    d = d0
    if p["d"] is None:
        # correct the duty so the switch-node average matches what the operating point needs
        need = p["v_out"] + p["i_out"] * (1.55 + 0.1 + p["rs"]) + (a["il"] - p["i_out"]) * 0.0
        d = min(d0 + (need + p["i_out"] * 0.0 - a["vsw"]) / p["v_raw"], 0.999)
        r, rip = simulate(p, d)
        a = analyse(p, r)
    a["d"] = d
    a["name"] = name
    a["p"] = p
    return name, a, r


CASES = [
    ("A full load: 400 V, 0.70 A", dict()),
    ("B peak: 400 V, 0.80 A", dict(i_out=0.8)),
    ("C idle KT88: 400 V, 0.30 A", dict(i_out=0.30)),
    ("D light: 400 V, 0.05 A", dict(i_out=0.05)),
    ("E zero current: 400 V, 0 A", dict(i_out=0.0)),
    ("F half voltage: 200 V, 0.35 A", dict(v_out=200.0, i_out=0.35)),
    ("G half voltage, no load: 200 V, 0 A", dict(v_out=200.0, i_out=0.0)),
    ("H ramp-down: 300 V, -0.80 A (sinking)", dict(v_out=300.0, i_out=-0.8)),
    ("I ramp-down, no load at 400 V: -0.6 A", dict(v_out=400.0, i_out=-0.6)),
    ("J full load, Qrr linear trend (floor 0.11 uC)", dict(qrr_law="linear")),
    ("J2 full load, Qrr +30 % (faster turn-on than the datasheet test)", dict(qrr_k=1.3)),
    ("L2 screen bridge, Qrr linear trend", dict(v_out=390.0, i_out=0.18, rs=2.2, bridge=2, qrr_law="linear")),
    ("K full load, Tj 25 C", dict(tj=25.0)),
    ("L screen bridge: 390 V, 0.18 A, 2.2 ohm", dict(v_out=390.0, i_out=0.18, rs=2.2, bridge=2)),
    ("M screen bridge peak: 390 V, 0.25 A", dict(v_out=390.0, i_out=0.25, rs=2.2, bridge=2)),
    ("P gate 15 ohm + 1 nF C0G gate-emitter (proposed), full load", dict(cge=1e-9)),
    ("Q gate 15 ohm + 1 nF C0G gate-emitter (proposed), screen 0.18 A", dict(cge=1e-9, v_out=390.0, i_out=0.18, rs=2.2, bridge=2)),
    ("N dead time 100 ns, full load", dict(dt=100e-9)),
    ("O dead time 330 ns, full load", dict(dt=330e-9)),
]
BOOT = [  # duty sweep at the 403 V corner: raw 420 V, 0.7 A, worst +12 V
    (f"boot D={d:.3f} V12={v}", dict(d=d, v12=v, v_out=403.0)) for v in (11.5, 12.5) for d in (0.97, 0.98, 0.985, 0.99)
]


def datasheet_losses(p, f=F_SW):
    """Switching loss per IGBT from the datasheet curves, extrapolated below 2 A: Fig. 12
    (150 C, 48 ohm) Eon = 0.020 + 0.0195 I mJ, Eoff = 0.002 + 0.009 I mJ; Fig. 13 (15 ohm: Eon x 0.82,
    Eoff x 1.0); Fig. 14 (125 C: Eon x 0.93, Eoff x 0.87); Fig. 15 (420 V: x 1.05). Hard turn-on
    only where the current at that edge flows in the other device's diode; else the edge is soft
    (zero-voltage) and only the turn-off counts."""
    i = p["i_out"]
    dI = (p["v_raw"] - p["v_out"]) * p["v_out"] / p["v_raw"] / (3e-3 * f)
    iv, ipk = i - dI / 2, i + dI / 2
    eon = lambda x: (0.020 + 0.0195 * x) * 0.82 * 0.93 * 1.05e-3
    eoff = lambda x: (0.002 + 0.009 * x) * 0.87 * 1.05e-3
    hs = (eon(iv) if iv > 0 else 0.0) + (eoff(ipk) if ipk > 0 else 0.0)
    ls = (eon(-ipk) if ipk < 0 else 0.0) + (eoff(-iv) if iv < 0 else 0.0)
    return hs * f, ls * f


def miller(dvdt, rg_off=15.0, rdrv=0.6, cge_ext=0.0, temp=sm.HOT):
    """Gate bump of an off IGBT whose collector is ramped 0 -> 420 V at dvdt (V/ns), the gate held
    by the driver's sink (rdrv) through rg_off; Cge_ext an optional external gate-emitter capacitor."""
    tr = 420.0 / (dvdt * 1e9)
    net = "\n".join(["* miller", sm.models(temp=temp),
                     f"Vc c 0 PWL(0 0 10n 0 {10e-9 + tr} 420)",
                     "Xq c g 0 IGBTL", f"Rg g gd {rg_off + rdrv}", "Vgd gd 0 0", "Rge g 0 10k",
                     f"Cx g 0 {max(cge_ext, 1e-15)}"])
    r = sm.run(net, ["v(g)"], 10e-9 + tr + 100e-9, "0.1n", "0.2n", uic=False)
    return r["v(g)"].max()


def averaged_losses(i, v_raw=420.0, v_out=400.0, f=F_SW):
    """The loss figures the thermal table (STATUS T3) used: 32.5 uJ/A + 3 uJ per IGBT switching."""
    return (32.5e-6 * i + 3e-6) * f


def plot_case(name, r, fn):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = r["t"]
    m = t >= (N_PER - 2) * T
    fig, ax = plt.subplots(4, 1, figsize=(8, 8), sharex=True)
    ax[0].plot(t[m] * 1e6, r["v(sw)"][m], lw=0.8)
    ax[0].set_ylabel("switch node (V)")
    ax[1].plot(t[m] * 1e6, r["i(Vil)"][m], lw=0.8, label="L201")
    ax[1].plot(t[m] * 1e6, r["i(Vc1)"][m], lw=0.6, label="Q201 c")
    ax[1].plot(t[m] * 1e6, r["i(Vc2)"][m], lw=0.6, label="Q202 c")
    ax[1].set_ylabel("A")
    ax[1].legend(fontsize=7, loc="upper right")
    ax[2].plot(t[m] * 1e6, r["v(gh)"][m] - r["v(sw)"][m], lw=0.8, label="Vge Q201")
    ax[2].plot(t[m] * 1e6, r["v(gl)"][m] - r["v(is)"][m], lw=0.8, label="Vge Q202")
    ax[2].plot(t[m] * 1e6, r["v(boot)"][m] - r["v(sw)"][m], lw=0.8, label="bootstrap")
    ax[2].set_ylabel("V")
    ax[2].legend(fontsize=7, loc="lower right")
    ax[3].plot(t[m] * 1e6, r["v(tab)"][m] - np.mean(r["v(tab)"][m]), lw=0.8, label="tab (AC)")
    ax[3].plot(t[m] * 1e6, r["v(uc)"][m] - np.mean(r["v(uc)"][m]), lw=0.8, label="C204 node (AC)")
    ax[3].set_ylabel("ripple (V)")
    ax[3].set_xlabel("time (us)")
    ax[3].legend(fontsize=7)
    fig.suptitle(name)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, fn), dpi=110)
    plt.close(fig)


def thermal(p_q, rth_sink):
    """Tj at 80 C local air: IGBT R_thJC 2.2 K/W, pad 1 K/W, sink, or free (62 K/W J-A)."""
    if rth_sink is None:
        return 80.0 + p_q * 62.0
    return 80.0 + p_q * (2.2 + 1.0 + rth_sink)


def main():
    cal = sm.calib()
    with Pool() as pool:
        res = pool.map(run_case, CASES + BOOT)
    R = {n: a for n, a, _ in res}
    for n, a, r in res:
        if n.startswith("A ") or n.startswith("E ") or n.startswith("H ") or n.startswith("L "):
            plot_case(n, r, "m15_" + n[0] + ".png")
    L = ["# M15: switching-level model of one bridge (generated by m15_bridge.py)", "",
         __doc__.split("\n\n")[1], "", __doc__.split("\n\n")[2], "",
         "## Device model against the datasheet (double-pulse test, 400 V)", "",
         "| IC (A) | RG (ohm) | Tj (C) | Eon model / datasheet (uJ) | Eoff model / datasheet (uJ) | Qrr model (nC) | Irrm model (A) |",
         "|---|---|---|---|---|---|---|"]
    ds = {(4.0, 125.0): (100, 30), (2.0, 125.0): (60, 20), (4.0, 25.0): (70, 20), (2.0, 25.0): (40, 20)}
    for i, rg, tj, d in cal:
        e = ds.get((i, tj))
        es = f"{d['eon'] * 1e6:.0f} / {e[0]}" if e and rg == 48.0 else f"{d['eon'] * 1e6:.0f} / —"
        fs = f"{d['eoff'] * 1e6:.0f} / {e[1]}" if e and rg == 48.0 else f"{d['eoff'] * 1e6:.0f} / —"
        L.append(f"| {i} | {rg} | {tj:.0f} | {es} | {fs} | {d['qrr'] * 1e9:.0f} | {d['irrm']:.1f} |")
    L += ["", "(Datasheet 150 C figures compared with the model at 125 C. At our 16.5 ohm gate loop and "
          "0.4-1 A the turn-on energy is 41-49 uJ: it is the diode's recovered charge times the rail voltage, "
          "nearly independent of the current.)", "",
          "## Operating points (raw 420 V, 50 kHz, Tj 125 C, DT 200 ns unless stated)", "",
          "| Case | duty | iL avg / p-p (A) | iL min / max (A) | Q201 loss: total / conduction (W) | Q202 loss: total / conduction (W) | "
          "T3 estimate, switching per IGBT (W) | datasheet curves, switching Q201 / Q202 (W) | ripple p-p: C204 node / tab / power amp (V) | raw UIN p-p (V) | "
          "dead-time margin, channel currents (ns) | bootstrap min (V) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, _ in CASES:
        a = R[n]
        avgsw = averaged_losses(abs(a["p"]["i_out"]))
        L.append(f"| {n} | {a['d']:.4f} | {a['il']:.3f} / {a['il_pp']:.3f} | {a['il_min']:.2f} / {a['il_max']:.2f} | "
                 f"{a['p1']:.2f} / {a['p1c']:.2f} | {a['p2']:.2f} / {a['p2c']:.2f} | {avgsw:.2f} | "
                 f"{datasheet_losses(a['p'])[0]:.2f} / {datasheet_losses(a['p'])[1]:.2f} | "
                 f"{lin_ripple(a['p'], a['d'])[0]:.3f} | {lin_ripple(a['p'], a['d'])[1]:.3f} | {a['tab_hf']:.0f} | {a['uin_pp']:.2f} | "
                 f"{a['dt_margin_ns']:.0f} | {a['boot_min']:.2f} |")
    L += ["", "## Bootstrap against the duty (403 V, 0.7 A, raw 420 V; UVLO off 8.2 V typ / 8.7 V max)", "",
          "| Case | V_tab (V) | bootstrap min / avg (V) | high side still switching |", "|---|---|---|---|"]
    for n, _ in BOOT:
        a = R[n]
        L.append(f"| {n} | {a['tab']:.1f} | {a['boot_min']:.2f} / {a['boot_avg']:.2f} | {'yes' if a['boot_min'] > 8.2 else 'NO (UVLO)'} |")
    # Miller-induced turn-on margin (dedicated test, independent of the diode snap)
    vth_min = 2.0
    L += ["", "## Miller-induced turn-on of the off device (collector ramped 0 -> 420 V, gate held by the driver)", "",
          f"VGE(th) at 125 C: typ 2.9 V, min about {vth_min} V (datasheet Fig. 11). The real edge rate is set by the "
          "IGBT's turn-on and the soft diode (datasheet tr 4-6 ns at 2-4 A: 20-50 V/ns); the model's snap (100+ V/ns) is not real.", "",
          "| dv/dt (V/ns) | 15 ohm off path (as drawn) | 4.7 ohm off path | 15 ohm + 1 nF G-E | 4.7 ohm off path + 1 nF G-E | 15 ohm + 2.2 nF G-E |",
          "|---|---|---|---|---|---|"]
    for dv in (10, 20, 50, 100):
        L.append(f"| {dv} | {miller(dv):.2f} V | {miller(dv, rg_off=4.7):.2f} V | {miller(dv, cge_ext=1e-9):.2f} V | "
                 f"{miller(dv, rg_off=4.7, cge_ext=1e-9):.2f} V | {miller(dv, cge_ext=2.2e-9):.2f} V |")
    # thermal at full load
    a = R["A full load: 400 V, 0.70 A"]
    aj = R["J full load, Qrr linear trend (floor 0.11 uC)"]
    s = R["L screen bridge: 390 V, 0.18 A, 2.2 ohm"]
    ql = R["L2 screen bridge, Qrr linear trend"]
    dsa = datasheet_losses(a["p"])[0] + a["p1c"]
    dss = datasheet_losses(s["p"])[0] + s["p1c"]
    L += ["", "## Thermal (local air 80 C; IGBT R_thJC 2.2 K/W, pad 1 K/W, SK 104 38.1 mm ~12 K/W, free-standing 62 K/W)", "",
          "Three loss estimates for each high side: the switching model (diode Qrr by the power-law trend), the same with the "
          "linear Qrr trend (pessimistic), and the datasheet curves extrapolated below 2 A (switching) plus the model's conduction.", "",
          "| Part | Loss: model / Qrr linear / datasheet curves (W) | STATUS T3 figure (W) | Tj: model / Qrr linear / datasheet curves (C) |",
          "|---|---|---|---|",
          f"| Q201 on SK 104 (0.70 A, 400 V) | {a['p1']:.2f} / {aj['p1']:.2f} / {dsa:.2f} | 2.0 | {thermal(a['p1'], 12):.0f} / {thermal(aj['p1'], 12):.0f} / {thermal(dsa, 12):.0f} |",
          f"| Q202 free | {a['p2']:.2f} / {aj['p2']:.2f} / — | 0.55 | {thermal(a['p2'], None):.0f} / {thermal(aj['p2'], None):.0f} / — |",
          f"| Q203 free-standing, as drawn before (0.18 A, 390 V) | {s['p1']:.2f} / {ql['p1']:.2f} / {dss:.2f} | 0.61 | {thermal(s['p1'], None):.0f} / {thermal(ql['p1'], None):.0f} / {thermal(dss, None):.0f} |",
          f"| Q203 on SK 104 (now drawn: HS202) | {s['p1']:.2f} / {ql['p1']:.2f} / {dss:.2f} | — | {thermal(s['p1'], 12):.0f} / {thermal(ql['p1'], 12):.0f} / {thermal(dss, 12):.0f} |",
          f"| Q204 free | {s['p2']:.2f} / {ql['p2']:.2f} / — | 0.3 | {thermal(s['p2'], None):.0f} / {thermal(ql['p2'], None):.0f} / — |"]
    open(os.path.join(HERE, "m15_results.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
