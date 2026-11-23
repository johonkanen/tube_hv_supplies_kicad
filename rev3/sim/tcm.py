#!/usr/bin/env python3
"""HV supplies rev 3, ripple-filter / soft-switching study: the triangular-current-mode (TCM)
operating law and the analytic loss model, shared by r1_softsw.py, r2_filter.py, r4_residue.py.

Operating law. A synchronous buck stays soft switched when the inductor current crosses zero every
period with enough reverse current at each edge to swing the switch node through the dead time:
    valley <= -I_zvs  (the high side then turns on with its own diode conducting: zero voltage),
    peak   >= +I_zvs  (the low side likewise),
i.e. a ripple of dI = 2 (|I_o| + I_zvs). With the half-bridge at duty D = V_o / V_in the ripple is
dI = V_o (1 - D) / (L f), so the frequency that gives exactly that ripple is
    f_TCM = V_o (V_in - V_o) / (V_in L dI).
It falls to zero at both ends (V_o -> 0 and V_o -> V_in): no fixed frequency can keep the current
reversing near D = 1 or D = 0, so the frequency must vary. The law used here:
    f = clamp(f_TCM, f_min, f_max)
(above f_max the ripple is larger than needed: still soft, more circulating current; below f_min,
only reached for V_o < ~5 V or within a few volts of the rail, the valley is not fully reversed).
"adaptive": |I_o| is the bridge's own (filtered) average current; "voltage": |I_o| fixed at the
design maximum, so f depends only on V_o and V_in (slow), whatever the load.

Losses per period (analytic, calibrated to r1_turnoff.py: the swmodel IGBT at 125 C):
  the turning-off IGBT at the peak (high side) and at the valley (low side): E_off(I, C_s);
  no turn-on loss and no diode recovery while the current at the turn-on edge flows in the
  turning-on device's own diode (the diode hands over at zero current with di/dt = V/L < 1 A/us);
  if the valley is not reversed (current positive at the high side's turn-on) the edge is hard:
  M15's E_on (Qrr x V_in, about 45 uJ) is charged;
  conduction: IGBT V_CE(I) from the model at V_GE 12 V (0.65 V + ... : 0.88 V at 1 A), diode
  V_F = 0.75 + 0.07 I (datasheet 1.40 V at 9 A, 125 C);
  dead-time diode conduction at the edges; gate charge 22 nC + 1 nF G-E at 12 V.
Inductor: gapped ferrite (core and turns given), copper with an AC factor, core loss by the iGSE
with Steinmetz parameters anchored at the maker's 100 kHz / 200 mT / 100 C point.
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- device tables (r1_turnoff.py)
_TO = None


def _turnoff():
    global _TO
    if _TO is None:
        res = json.load(open(os.path.join(HERE, "r1_turnoff.json")))
        _TO = [r for r in res if r["tj"] == 125.0]
    return _TO


def eoff(i, cs):
    """Turn-off energy (J) of the IGBT at current i (A) with a snubber cs (F) across each device,
    125 C, interpolated in current (linear) and in cs (linear between the tabulated values)."""
    i = abs(i)
    rows = _turnoff()
    css = sorted(set(r["cs"] for r in rows))
    def at(c):
        rr = sorted((r for r in rows if r["cs"] == c), key=lambda r: r["i"])
        x = np.array([0.0] + [r["i"] for r in rr]); y = np.array([0.0] + [r["eoff"] for r in rr])
        return float(np.interp(i, x, y, right=y[-1] + (i - x[-1]) * (y[-1] - y[-2]) / (x[-1] - x[-2])))
    if cs in css:
        return at(cs)
    k = np.searchsorted(css, cs)
    c0, c1 = css[k - 1], css[min(k, len(css) - 1)]
    w = (cs - c0) / (c1 - c0)
    return (1 - w) * at(c0) + w * at(c1)


def qnode(cs, v=420.0):
    """Charge (C) to swing the switch node through v: 2 x cs + 20 pF, plus the two IGBTs' own
    output charge (fitted to r1_turnoff.py's commutation times: about 15 nC at 420 V)."""
    return (2 * cs + 20e-12) * v + 15e-9 * v / 420.0


def tcomm(i, cs, v=420.0):
    """Time (s) for a current i to swing the node (constant current: the inductor), plus the
    IGBT's turn-off delay (about 45 ns at 15 ohm: r1_turnoff.py)."""
    return 45e-9 + qnode(cs, v) / max(abs(i), 1e-3)


def izvs_for(t_allowed, cs, v=420.0):
    """Valley current that swings the node within t_allowed."""
    return qnode(cs, v) / max(t_allowed - 45e-9, 1e-9)


def vce(i):
    i = abs(i)
    x = [0.0, 0.1, 0.3, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0]
    y = [0.50, 0.65, 0.74, 0.79, 0.88, 0.96, 1.02, 1.15, 1.27]
    return float(np.interp(i, x, y))


def vf(i):
    return 0.75 + 0.07 * abs(i) if abs(i) > 1e-6 else 0.0


E_ON_HARD = 45e-6          # M15: Qrr x V_in, nearly independent of the current
QG = 22e-9 + 1e-9 * 12     # gate charge per edge pair at 12 V: IGBT + the 1 nF G-E capacitor


# ---------------------------------------------------------------- inductor
CORES = {
    # name: Ae (m^2), le (m), Ve (m^3), MLT (m), window for the winding (m^2), Pv(100 kHz, 200 mT, 100 C) W/m^3
    "ETD39 N97": dict(ae=125e-6, le=92.2e-3, ve=11.5e-6, mlt=69e-3, aw=125e-6, pv0=300e3, mat="N97"),
    "ETD39 N87": dict(ae=125e-6, le=92.2e-3, ve=11.5e-6, mlt=69e-3, aw=125e-6, pv0=375e3, mat="N87"),
    "ETD44 N97": dict(ae=173e-6, le=103e-3, ve=17.8e-6, mlt=77e-3, aw=170e-6, pv0=300e3, mat="N97"),
    "ETD34 N97": dict(ae=97.1e-6, le=78.6e-3, ve=7.64e-6, mlt=61e-3, aw=97e-6, pv0=300e3, mat="N97"),
}
ALPHA, BETA = 1.45, 2.6       # Steinmetz exponents of the MnZn power ferrites near 100 kHz


def _ki(k):
    th = np.linspace(0, 2 * np.pi, 4001)
    integ = np.trapezoid(np.abs(np.cos(th)) ** ALPHA, th)
    return k / ((2 * np.pi) ** (ALPHA - 1) * integ * 2 ** (BETA - ALPHA))


def core_loss(core, n, l, di, f, d):
    """iGSE core loss (W) for a triangular current dI p-p at frequency f and duty d."""
    c = CORES[core]
    k = c["pv0"] / ((100e3) ** ALPHA * 0.2 ** BETA)      # Pv = k f^a Bpk^b (sine)
    dB = l * di / (n * c["ae"])                         # peak-to-peak flux density
    ki = _ki(k)
    d = min(max(d, 1e-3), 1 - 1e-3)
    # iGSE for a two-slope triangle: Pv = ki dB^(b-a) f [ (dB/(d T))^a d T + (dB/((1-d) T))^a (1-d) T ]
    T = 1.0 / f
    pv = ki * dB ** (BETA - ALPHA) * f * ((dB / (d * T)) ** ALPHA * d * T + (dB / ((1 - d) * T)) ** ALPHA * (1 - d) * T)
    return pv * c["ve"], dB


def winding(core, n, litz_area=0.8e-6, fac_ac=1.5):
    """DC resistance (ohm, hot 100 C) and the AC factor applied to the ripple part."""
    c = CORES[core]
    r = n * c["mlt"] / (58e6 * litz_area) * 1.3
    return r, fac_ac


# ---------------------------------------------------------------- operating law
def f_tcm(vo, io, vin, l, izvs):
    di = 2 * (abs(io) + izvs)
    if vo <= 0 or vo >= vin:
        return 0.0
    return vo * (vin - vo) / (vin * l * di)


def law(vo, io, vin, d):
    """Frequency (Hz) for an operating point, design dict d (L, izvs, fmin, fmax, mode, io_design)."""
    io_l = d["io_design"] if d["mode"] == "voltage" else abs(io)
    f = f_tcm(vo, io_l, vin, d["L"], d["izvs"])
    return float(np.clip(f, d["fmin"], d["fmax"]))


def operating_point(vo, io, vin, d, f=None):
    """Waveform and losses of one bridge at (vo, io, vin) under design d. Returns a dict."""
    L, cs = d["L"], d["cs"]
    f = law(vo, io, vin, d) if f is None else f
    T = 1.0 / f
    dcy = vo / vin
    di = vo * (1 - dcy) / (L * f)
    ipk, ival = io + di / 2, io - di / 2
    n = 400
    ton = dcy * T
    t = np.linspace(0, T, n, endpoint=False)
    il = np.where(t < ton, ival + di * t / max(ton, 1e-12), ipk - di * (t - ton) / max(T - ton, 1e-12))
    hs = t < ton
    # conduction: high side interval: IGBT if il > 0 else its diode; low side: diode if il > 0 else IGBT
    p_hs = np.where(hs, np.where(il > 0, il * np.vectorize(vce)(il), -il * np.vectorize(vf)(il)), 0.0)
    p_ls = np.where(~hs, np.where(il > 0, il * np.vectorize(vf)(il), -il * np.vectorize(vce)(il)), 0.0)
    pc_hs, pc_ls = p_hs.mean(), p_ls.mean()
    # edges: at t = ton (peak): the high side turns off if ipk > 0 (soft if the node swings), the
    # low side turns on: soft if ipk > 0 (its diode conducts). If ipk < 0 the low side turn-on is
    # hard (current in the high side's diode: recovery) and the high side's turn-off is a diode's.
    e_hs = e_ls = 0.0
    hard = 0
    if ipk > 0:
        e_hs += eoff(ipk, cs)
    else:
        e_ls += E_ON_HARD; hard += 1
    # at t = 0 (valley): the low side turns off if ival < 0 (soft), the high side turns on: soft if
    # ival < 0; hard (low side diode recovering) if ival > 0
    if ival < 0:
        e_ls += eoff(ival, cs)
    else:
        e_hs += E_ON_HARD; hard += 1
    # incomplete transition (the valley / peak current too small to swing the node in the dead time
    # allowed): the remaining node charge is dumped at turn-on, about q_rem x v_rem / 2
    for icur, which in ((abs(ival), "hs"), (abs(ipk), "ls")):
        if (which == "hs" and ival < 0) or (which == "ls" and ipk > 0):
            q = qnode(cs, vin)
            qd = icur * max(d["dt_max"] - 45e-9, 0)
            if qd < q:
                vrem = vin * (1 - qd / q)
                e = 0.5 * (q / vin) * vrem ** 2
                if which == "hs":
                    e_hs += e
                else:
                    e_ls += e
    # dead-time diode conduction: (dead time - transition) x I x VF, at both edges
    for icur in (ipk, ival):
        tdt = 30e-9 if d.get("dt_adaptive") else max(d["dt_fixed"] - tcomm(icur, cs, vin), 0.0)
        e_x = tdt * abs(icur) * vf(icur)
        if icur > 0:
            e_ls += e_x
        else:
            e_hs += e_x
    p_hs = pc_hs + e_hs * f
    p_ls = pc_ls + e_ls * f
    irms = float(np.sqrt(np.mean(il ** 2)))
    ripple_rms = float(np.sqrt(np.mean((il - il.mean()) ** 2)))
    # inductor
    pcore, dB = core_loss(d["core"], d["N"], L, di, f, dcy)
    rdc, fac = winding(d["core"], d["N"], d.get("litz", 0.8e-6))
    pcu = rdc * (io ** 2 + fac * ripple_rms ** 2)
    bpk = L * max(abs(ipk), abs(ival)) / (d["N"] * CORES[d["core"]]["ae"])
    pgate = 2 * QG * 12.0 * f
    return dict(vo=vo, io=io, vin=vin, f=f, di=di, ipk=ipk, ival=ival, irms=irms, ripple_rms=ripple_rms,
                p_hs=p_hs, p_ls=p_ls, pc_hs=pc_hs, pc_ls=pc_ls, esw_hs=e_hs, esw_ls=e_ls, hard=hard,
                pcore=pcore, pcu=pcu, dB=dB, bpk=bpk, pgate=pgate, i12=2 * QG * f,
                t_valley=tcomm(ival, cs, vin), t_peak=tcomm(ipk, cs, vin))


def tj(p, sink=True):
    """Tj at 80 C local air: R_thJC 2.2 + pad 1.0 + SK 104 38.1 mm ~12 K/W; free-standing 62 K/W."""
    return 80.0 + p * ((2.2 + 1.0 + 12.0) if sink else 62.0)


# The recommended design (r1_softsw.py chooses it; r2 / r3 / r4 use it)
DESIGN = dict(L=220e-6, cs=220e-12, izvs=izvs_for(600e-9, 220e-12), fmin=40e3, fmax=150e3, mode="adaptive",
              io_design=0.8, core="ETD39 N97", N=36, litz=0.8e-6, dt_max=600e-9, dt_adaptive=True, dt_fixed=600e-9)
DESIGN_SCREEN = dict(DESIGN, L=470e-6, N=52, litz=0.5e-6)
