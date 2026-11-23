#!/usr/bin/env python3
"""HV supplies rev 3, ripple-filter / soft-switching study: the output filter chain as a linear
network, shared by r2_filter.py, r3_damping.py and r4_residue.py.

    sw --L1 (DCR, Cw)-- uc --L2 (DCR) [|| damping]-- vo --Rs-- tab --W04 (0.5 uH, 50 mohm)-- pa -- load
                        |                            |                                    |
                       C1 branches                  C2 branches (incl. an Rd-Cd leg)    100 nF (power amp)
                       (electrolytic: C, ESR, ESL,
                        returned through the I_C shunt; film)

Damping of the second stage, one of: None, ("R", Rd) across L2 (as drawn: 5.6 ohm), ("RL", Rd, Ld)
(Rd in series with Ld across L2: keeps the -40 dB/decade asymptote), or an Rd-Cd leg in C2's list.
v_sw is the half-bridge's averaged (or harmonic) voltage; the load is a resistance (or open) plus an
injected current at pa for the output impedance.
"""
import numpy as np

W04 = (0.5e-6, 0.05)
C_PA = (100e-9, 0.02, 5e-9)


def chain(name):
    """Named filter chains. Each: L1, RL1, C1 list, L2 (None = no second inductor), RL2, damping,
    C2 list, Rs. Capacitor entries are (C, ESR, ESL); ESR "E" means the electrolytic's ESR corner
    (filled in by network())."""
    base = dict(L1=220e-6, RL1=0.08, Cw1=10e-12, C1=[(100e-6, "E", 20e-9)], L2=None, RL2=0.05, damp=None,
                C2=[], Rs=1.0)
    ch = {
        # today's network (sheet 02) with the old 3 mH inductor: reference
        "drawn, 3 mH": dict(base, L1=3e-3, RL1=1.55, Cw1=25e-12, L2=33e-6, RL2=0.1, damp=("R", 5.6),
                            C2=[(1e-6, 0.02, 15e-9)]),
        # TCM inductor, today's second stage
        "220 uH + drawn 2nd stage (33 uH || 5.6 ohm, 1 uF: 27.7 kHz)": dict(base, L2=33e-6, RL2=0.1, damp=("R", 5.6),
                                                                     C2=[(1e-6, 0.02, 15e-9)]),
        # TCM inductor, first stage only (C2 = the 1 uF film straight at vo, no L2)
        "first stage only (no L2)": dict(base, C2=[(1e-6, 0.02, 15e-9)]),
        # the user's placement: second resonance above the switching frequency (above f_max = 150 kHz)
        "user: f2 = 200 kHz > f_sw (6.8 uH, 100 nF, undamped)": dict(base, L2=6.8e-6, RL2=0.02, damp=None,
                                                                    C2=[(100e-9, 0.02, 5e-9)]),
        "user: f2 = 200 kHz > f_sw, damped (6.8 uH || 8.2 ohm)": dict(base, L2=6.8e-6, RL2=0.02, damp=("R", 8.2),
                                                                     C2=[(100e-9, 0.02, 5e-9)]),
        # second resonance inside the frequency band (the user's "above f_sw" at the low end of the range)
        "f2 = 60 kHz, inside the f_sw band (10 uH || 4.7 ohm, 0.68 uF)": dict(base, L2=10e-6, RL2=0.02, damp=("R", 4.7),
                                                                             C2=[(0.68e-6, 0.02, 10e-9)]),
        # recommended: f2 ~ 9 kHz, between the loop bandwidth and f_sw min, damped by an Rd-Cd leg across C2
        # (Cd an electrolytic, Rd = 1.0 ohm + its ESR about 0.5 ohm)
        "recommended: L2 68 uH, C2 4.7 uF film, Rd-Cd leg 22 uF + 1.5 ohm (f2 8.9 kHz)": dict(
            base, L2=68e-6, RL2=0.06, damp=None, C2=[(4.7e-6, 0.01, 15e-9), (22e-6, 1.5, 20e-9)],
            C1=[(100e-6, "E", 20e-9), (4.7e-6, 0.01, 15e-9)]),
        # recommended second stage, and the first resonance damped passively as well: the electrolytic in
        # series with a resistor (1.0 ohm + its ESR) behind 10 uF of film that takes the ripple
        "recommended + passive first-stage damping: C1 = 10 uF film || (100 uF + 1.0 ohm)": dict(
            base, L2=68e-6, RL2=0.06, damp=None, C2=[(4.7e-6, 0.01, 15e-9), (22e-6, 1.5, 20e-9)],
            C1=[(100e-6, ("E", 1.0), 20e-9), (10e-6, 0.005, 15e-9)]),
        # the same L2 / C2 damped by Rd + Ld across L2 (keeps the -40 dB/decade asymptote with a
        # smaller inductance)
        "same L2 / C2, Rd-Ld across L2 (3.3 ohm + 22 uH)": dict(
            base, L2=68e-6, RL2=0.06, damp=("RL", 3.3, 22e-6), C2=[(4.7e-6, 0.01, 15e-9)],
            C1=[(100e-6, "E", 20e-9), (4.7e-6, 0.01, 15e-9)]),
        # the same L2 / C2 damped like the drawn stage (Rd straight across L2): the asymptote is lost
        "same L2 / C2, Rd straight across L2 (3.9 ohm)": dict(
            base, L2=68e-6, RL2=0.06, damp=("R", 3.9), C2=[(4.7e-6, 0.01, 15e-9)],
            C1=[(100e-6, "E", 20e-9), (4.7e-6, 0.01, 15e-9)]),
    }
    return ch[name]


NAMES = ["drawn, 3 mH", "220 uH + drawn 2nd stage (33 uH || 5.6 ohm, 1 uF: 27.7 kHz)", "first stage only (no L2)",
         "user: f2 = 200 kHz > f_sw (6.8 uH, 100 nF, undamped)", "user: f2 = 200 kHz > f_sw, damped (6.8 uH || 8.2 ohm)",
         "f2 = 60 kHz, inside the f_sw band (10 uH || 4.7 ohm, 0.68 uF)",
         "recommended: L2 68 uH, C2 4.7 uF film, Rd-Cd leg 22 uF + 1.5 ohm (f2 8.9 kHz)",
         "recommended + passive first-stage damping: C1 = 10 uF film || (100 uF + 1.0 ohm)",
         "same L2 / C2, Rd-Ld across L2 (3.3 ohm + 22 uH)", "same L2 / C2, Rd straight across L2 (3.9 ohm)"]
REC = NAMES[6]
REC_P = NAMES[7]


def scaled(p, kL1=1.0, kC1=1.0, kL2=1.0, kC2=1.0):
    q = dict(p)
    q["L1"] = p["L1"] * kL1
    q["C1"] = [(c * (kC1 if k == 0 else 1.0), r, l) for k, (c, r, l) in enumerate(p["C1"])]
    if p["L2"]:
        q["L2"] = p["L2"] * kL2
    q["C2"] = [(c * (kC2 if k == 0 else 1.0), r, l) for k, (c, r, l) in enumerate(p["C2"])]
    return q


def _r(r, esr):
    """ESR entry: a number, "E" (the electrolytic's ESR corner) or ("E", x) (that plus a series resistor x)."""
    if isinstance(r, tuple):
        return esr + r[1]
    return esr if r == "E" else r


def _y_caps(lst, s, esr):
    y = 0
    for c, r, l in lst:
        r = _r(r, esr)
        y = y + 1.0 / (r + s * l + 1.0 / (s * c))
    return y


def network(p, f, r_load=None, esr=0.1):
    """Frequency responses (complex arrays over f, Hz):
    Gvd  = v_pa / v_sw,  Gtab = v_tab / v_sw, Guc = v_uc / v_sw,
    Gil  = i_L1 / v_sw (bridge current), Gic = i into the electrolytic (first C1 entry) / v_sw,
    Gic_all = i into all C1 branches / v_sw,
    Zo   = v_pa / i_inj (current into pa, v_sw = 0), Hic = i_C(electrolytic) / i_inj, Hil = i_L1 / i_inj,
    Ztab = v_tab / i_inj."""
    f = np.atleast_1d(np.asarray(f, float))
    s = 2j * np.pi * f
    yl1 = 1.0 / (p["RL1"] + s * p["L1"]) + s * p["Cw1"]
    yc1 = _y_caps(p["C1"], s, esr)
    yel = 1.0 / (_r(p["C1"][0][1], esr) + s * p["C1"][0][2] + 1.0 / (s * p["C1"][0][0]))
    if p["L2"]:
        y2 = 1.0 / (p["RL2"] + s * p["L2"]) + s * 5e-12
        d = p["damp"]
        if d is not None and d[0] == "R":
            y2 = y2 + 1.0 / d[1]
        elif d is not None and d[0] == "RL":
            y2 = y2 + 1.0 / (d[1] + s * d[2])
    else:
        y2 = np.full(len(s), 1e6 + 0j)
    yc2 = _y_caps(p["C2"], s, None) if p["C2"] else 0 * s
    gs = 1.0 / p["Rs"]
    yw = 1.0 / (W04[1] + s * W04[0])
    ypa = 1.0 / (C_PA[1] + s * C_PA[2] + 1.0 / (s * C_PA[0])) + (0 if r_load is None else 1.0 / r_load)
    out = {k: np.zeros(len(s), complex) for k in ("Gvd", "Gtab", "Guc", "Gil", "Gic", "Gic_all", "Zo", "Hic", "Hil", "Ztab")}
    for k in range(len(s)):
        Y = np.array([[yl1[k] + yc1[k] + y2[k], -y2[k], 0, 0],
                      [-y2[k], y2[k] + yc2[k] + gs, -gs, 0],
                      [0, -gs, gs + yw[k], -yw[k]],
                      [0, 0, -yw[k], yw[k] + ypa[k]]], complex)
        v = np.linalg.solve(Y, np.array([yl1[k], 0, 0, 0], complex))
        out["Gvd"][k], out["Gtab"][k], out["Guc"][k] = v[3], v[2], v[0]
        out["Gil"][k] = (1.0 - v[0]) * yl1[k]
        out["Gic"][k] = v[0] * yel[k]
        out["Gic_all"][k] = v[0] * yc1[k]
        v = np.linalg.solve(Y, np.array([0, 0, 0, 1.0], complex))
        out["Zo"][k], out["Ztab"][k] = v[3], v[2]
        out["Hic"][k] = v[0] * yel[k]
        out["Hil"][k] = -v[0] * yl1[k]
    return out


def resonances(p, esr=0.1):
    """Natural frequencies of the chain (eigenvalues of the passive network with v_sw shorted and the
    load open), as (f Hz, Q) pairs above 100 Hz."""
    f = np.logspace(2, 6, 4000)
    n = network(p, f, None, esr)
    z = np.abs(n["Zo"])
    pk = [k for k in range(1, len(f) - 1) if z[k] > z[k - 1] and z[k] > z[k + 1]]
    return [(f[k], z[k]) for k in pk]
