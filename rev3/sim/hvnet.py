#!/usr/bin/env python3
"""HV supplies rev 3: the averaged output network of one bridge, as a linear model shared by
lc_ac.py (ngspice cross-check of the passive network), loop_digital.py (closed loop with the
control board's delay) and discharge.py.

Network (one bridge, averaged: the half-bridge is a voltage source v_sw = d * V_raw):

    sw --L1 (3 mH, DCR)-- uc --[L2 (33 uH, DCR) || Rd]-- vo --Rs (2.2 ohm fusible)-- tab -- load
                          |                              |                           |
                         Cuc (electrolytics,            Cvo                         R_load, i_inj
                          ESR each, returned            (to GND_STAR)
                          through the I_C shunt)

Two variants of the second stage:
  A  first pass (c947e82): 47 uF at uc, 33 uH, 47 uF + 100 nF at vo.  The 33 uH / 47 uF pair
     resonates at 1 / (2 pi sqrt(33u * 47u)) = 4.0 kHz, damped only by the electrolytic ESR.
  B  second pass: one 100 uF / 500 V electrolytic at uc (it replaces the two 47 uF: about the
     same stored energy, one part less per bridge for the floorplan), 33 uH with a
     5.6 ohm damping resistor in parallel, 1 uF / 630 V film at vo: the second stage moves to
     27.7 kHz with Q = Rd * sqrt(Cvo / L2) = 1.0, out of the audio band and above the loop.
     Third pass: bridge 1 (V_ANODE) has Rs = 1.0 ohm (0.7 A continuous) and the ETD39 inductor
     (DCR 1.55 ohm hot); bridge 2 keeps 2.2 ohm (variant B with Rs=2.2 is the screen bridge).
  C  as B with 2.2 uF / 3.9 ohm (18.7 kHz, Q = 1.0): twice the ripple attenuation, a larger film.

The measured quantities (interfaces.md 9, ADC channels): v_tab (V_ANODE / V_SCREEN, after Rs)
and i_C (the electrolytics' current, I_C14 / I_C24 shunt).
"""
import numpy as np

BASE = dict(L1=3e-3, RL1=1.7, L2=33e-6, RL2=0.1, Rs=2.2, ESR=0.5, Cel=47e-6)
VARIANTS = {
    "A": dict(n_uc=1, Rd=None, Cvo=[(47e-6, "ESR"), (100e-9, 0.02)]),
    "B": dict(n_uc=1, Cel=100e-6, Rd=5.6, Cvo=[(1e-6, 0.02)], Rs=1.0, RL1=1.55),
    "C": dict(n_uc=1, Cel=100e-6, Rd=3.9, Cvo=[(2.2e-6, 0.02)]),
}


def params(variant="B", **kw):
    """ESR is per electrolytic (variant B / C: one 100 uF part, so the corners 0.1 / 0.5 ohm are
    the whole intermediate capacitance; variant A: each 47 uF)."""
    p = dict(BASE)
    p.update(VARIANTS[variant])
    p.update(kw)
    p["variant"] = variant
    return p


def _zc(c, esr, s):
    return esr + 1.0 / (s * c)


def network(p, f, r_load):
    """Return dict of complex frequency responses at frequencies f (Hz):
    Gvd = v_tab / v_sw, Gid = i_C / v_sw (i_C into the electrolytics),
    Zo = v_tab / i_inj (current injected into the tab, v_sw = 0), Hic = i_C / i_inj,
    Hvu = v_tab / v_uc (ripple attenuation of the second stage, sw open)."""
    s = 2j * np.pi * np.asarray(f, dtype=float)
    esr = p["ESR"]
    z_l1 = p["RL1"] + s * p["L1"]
    y_uc = sum(1.0 / _zc(p["Cel"], esr, s) for _ in range(p["n_uc"]))
    z_l2 = p["RL2"] + s * p["L2"]
    y_l2 = 1.0 / z_l2 + (1.0 / p["Rd"] if p["Rd"] else 0.0)
    y_vo = sum(1.0 / _zc(c, esr if r == "ESR" else r, s) for c, r in p["Cvo"])
    g_s = 1.0 / p["Rs"]
    g_ld = 0.0 if r_load is None else 1.0 / r_load
    y1 = 1.0 / z_l1
    out = {k: np.zeros(len(s), complex) for k in ("Gvd", "Gid", "Zo", "Hic", "Hvu")}
    for k in range(len(s)):
        # nodal matrix for [v_uc, v_vo, v_tab]
        Y = np.array([[y1[k] + y_uc[k] + y_l2[k], -y_l2[k], 0],
                      [-y_l2[k], y_l2[k] + y_vo[k] + g_s, -g_s],
                      [0, -g_s, g_s + g_ld]], complex)
        v = np.linalg.solve(Y, np.array([y1[k], 0, 0], complex))       # v_sw = 1
        out["Gvd"][k] = v[2]
        out["Gid"][k] = v[0] * y_uc[k]
        v = np.linalg.solve(Y, np.array([0, 0, 1], complex))           # i_inj = 1
        out["Zo"][k] = v[2]
        out["Hic"][k] = v[0] * y_uc[k]
        Y2 = Y[1:, 1:]
        v = np.linalg.solve(Y2, np.array([y_l2[k], 0], complex))       # v_uc = 1 (second stage only)
        out["Hvu"][k] = v[1]
    return out
