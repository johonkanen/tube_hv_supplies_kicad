#!/usr/bin/env python3
"""HV supplies rev 3: the closed voltage loop with the control board's delay (review M16, the
condition of the IF-2 acceptance) and the second LC stage inside it (M19, first-pass missed 6).

Controller (in the control board's FPGA): every Ts it samples V_tab (V_ANODE or V_SCREEN, after
the 2.2 ohm tab resistor) and i_C (the electrolytics' current, I_C14 / I_C24 shunt) and sets the
half-bridge voltage
    v_sw = clamp( v_ref + Kp e + Ki integral(e) - Kc i_C , 0 , D_MAX V_raw ),   e = v_ref - V_tab
(v_ref feed-forward, PI on the voltage, active damping of the 3 mH / 100 uF resonance through the
capacitor current). The new value takes effect TD = 60 us after the sample (the control board
session's total loop delay, 50-60 us: isolators, ADC conversion and transfer, computation, PWM
update) and is held until the next one (zero-order hold: Ts / 2 more on average). Ts = 32 us is
31.25 kSPS per controlled channel, the AD7689 round robin of interfaces.md 9 (the firmware may
sample the controlled channels more often than the monitors; 32 us is the conservative case).

Frequency domain: loop gain T = exp(-s (TD + Ts/2)) (Cv Gvd + Kc Gid), Cv = Kp + Ki / s, with
the averaged network of hvnet.py; margins and the closed-loop output impedance at the tab over
the corners (variant A / B, ESR 0.1 / 0.5 ohm, load 700 ohm / 4 kohm / open). Time domain:
exact discretisation (1 us) of the same network, sampled controller with the delay buffer and
the duty clamp: audio load with 0.57 A peaks (KT88 set, full overdrive, review E28), a load
step, 30 ms ramps up and down (the fastest accepted ramp), the bridge current against the
2.0 A hardware trips.

Run: python3 rev3/sim/loop_digital.py   (writes rev3/sim/loop_results.md; about 30 s)
"""
import os

import numpy as np
from scipy.linalg import expm

import hvnet

HERE = os.path.dirname(os.path.abspath(__file__))
TS, TD, D_MAX = 32e-6, 60e-6, 0.97
GAINS = dict(Kp=0.0, Ki=0.0, Kc=0.0)       # filled by tune()
F = np.logspace(0, np.log10(50e3), 3000)


_NET = {}


def net(p, f, r_load):
    key = (tuple(sorted((k, str(v)) for k, v in p.items())), r_load, len(f), float(f[0]), float(f[-1]))
    if key not in _NET:
        _NET[key] = hvnet.network(p, f, r_load)
    return _NET[key]


def loop_gain(p, r_load, g, f=F, td=TD, ts=TS):
    n = net(p, f, r_load)
    s = 2j * np.pi * f
    d = np.exp(-s * (td + ts / 2))
    cv = g["Kp"] + g["Ki"] / s
    return d * (cv * n["Gvd"] + g["Kc"] * n["Gid"]), n, d, cv


def margins(T, f=F):
    mag, ph = np.abs(T), np.unwrap(np.angle(T))
    pm, fc = 999.0, None
    for k in np.where(np.diff(np.sign(mag - 1.0)) != 0)[0]:
        m = (np.degrees(ph[k]) + 180) % 360
        m = m if m <= 180 else m - 360
        if m < pm:
            pm, fc = m, f[k]
    gm = 999.0
    phd = np.degrees(ph)
    for k in np.where(np.diff(np.floor((phd + 180) / 360)) != 0)[0]:
        gm = min(gm, -20 * np.log10(mag[k]))
    return pm, fc, gm


def zcl(p, r_load, g, f=F):
    T, n, d, cv = loop_gain(p, r_load, g, f)
    vsw = -d * (cv * n["Zo"] + g["Kc"] * n["Hic"]) / (1 + T)
    return n["Zo"] + n["Gvd"] * vsw


CORNERS = [(v, esr, rl) for v in ("A", "B") for esr in (0.1, 0.5) for rl in (700.0, 4000.0, None)]


def evaluate(g, variants=("B",)):
    worst = dict(pm=999, gm=999, z=0, fc=None)
    for v, esr, rl in CORNERS:
        if v not in variants:
            continue
        p = hvnet.params(v, ESR=esr)
        pm, fc, gm = margins(loop_gain(p, rl, g)[0])
        if pm < worst["pm"]:
            worst["pm"], worst["fc"] = pm, fc
        worst["gm"] = min(worst["gm"], gm)
        if rl == 700.0:
            m = (F >= 20) & (F <= 5e3)
            worst["z"] = max(worst["z"], np.max(np.abs(zcl(p, rl, g)[m])))
    return worst


def tune(variants=("B",)):
    best = None
    for kc in (10, 15, 20, 25, 30, 40, 50):
        for kp in (1, 2, 3, 4, 5, 6, 8):
            for ki in (1000, 2000, 4000, 6000, 10000):
                g = dict(Kp=kp, Ki=ki, Kc=kc)
                w = evaluate(g, variants)
                if w["pm"] >= 45 and w["gm"] >= 8 and (best is None or w["z"] < best[1]["z"]):
                    best = (g, w)
    return best


# ------------------------------------------------------------------ time domain
def state_space(p, r_load):
    """x = [iL1, vCuc, iL2, vCvo_k...], u = [v_sw, i_inj]; outputs y = [v_tab, i_C]."""
    cvo = [(c, p["ESR"] if r == "ESR" else r) for c, r in p["Cvo"]]
    n = 3 + len(cvo)
    cuc, esre = p["n_uc"] * p["Cel"], p["ESR"] / p["n_uc"]
    gd = 1.0 / p["Rd"] if p["Rd"] else 0.0
    gl = 0.0 if r_load is None else 1.0 / r_load

    def nodes(x, u):
        il1, vcu, il2 = x[0], x[1], x[2]
        M = np.array([[1 / esre + gd, -gd, 0],
                      [-gd, gd + sum(1 / r for _, r in cvo) + 1 / p["Rs"], -1 / p["Rs"]],
                      [0, -1 / p["Rs"], 1 / p["Rs"] + gl]])
        rhs = np.array([il1 - il2 + vcu / esre,
                        il2 + sum(x[3 + k] / r for k, (_, r) in enumerate(cvo)),
                        u[1]])
        return np.linalg.solve(M, rhs)

    def deriv(x, u):
        vu, vo, vt = nodes(x, u)
        dx = np.zeros(n)
        dx[0] = (u[0] - p["RL1"] * x[0] - vu) / p["L1"]
        dx[1] = (vu - x[1]) / esre / cuc
        dx[2] = (vu - vo - p["RL2"] * x[2]) / p["L2"]
        for k, (c, r) in enumerate(cvo):
            dx[3 + k] = (vo - x[3 + k]) / r / c
        return dx, np.array([vt, (vu - x[1]) / esre])

    A = np.zeros((n, n)); B = np.zeros((n, 2)); C = np.zeros((2, n)); D = np.zeros((2, 2))
    for k in range(n):
        e = np.zeros(n); e[k] = 1
        dx, y = deriv(e, np.zeros(2))
        A[:, k], C[:, k] = dx, y
    for k in range(2):
        e = np.zeros(2); e[k] = 1
        dx, y = deriv(np.zeros(n), e)
        B[:, k], D[:, k] = dx, y
    return A, B, C, D


def simulate(p, r_load, g, t_end, vref, iload, v_raw=430.0, dt=1e-6, v0=None):
    A, B, C, D = state_space(p, r_load)
    n = A.shape[0]
    M = expm(np.block([[A, B], [np.zeros((2, n + 2))]]) * dt)
    Ad, Bd = M[:n, :n], M[:n, n:]
    # steady state at v0
    v0 = vref(0.0) if v0 is None else v0
    i0 = iload(0.0)
    # solve x_ss for v_sw such that v_tab = v0 (linear: two solves)
    def xss(vsw):
        return np.linalg.solve(-A, B @ np.array([vsw, -i0]))
    y1, y2 = C @ xss(0.0) + D @ [0.0, -i0], C @ xss(1.0) + D @ [1.0, -i0]
    vsw0 = (v0 - y1[0]) / (y2[0] - y1[0])
    x = xss(vsw0)
    steps = int(round(t_end / dt))
    nts, ntd = int(round(TS / dt)), int(round(TD / dt))
    integ = vsw0 - v0
    pending = []                     # (apply_at_step, value)
    vsw = vsw0
    out = np.zeros((steps, 5))
    for k in range(steps):
        t = k * dt
        il = iload(t)
        y = C @ x + D @ [vsw, -il]
        if k % nts == 0:
            vr = vref(t)
            e = vr - y[0]
            u = vr + g["Kp"] * e + integ - g["Kc"] * y[1]
            hi = D_MAX * v_raw
            uc = min(max(u, 0.0), hi)
            if uc == u or (u > hi and e < 0) or (u < 0 and e > 0):
                integ += g["Ki"] * TS * e
            pending.append((k + ntd, uc))
        while pending and pending[0][0] <= k:
            vsw = pending.pop(0)[1]
        out[k] = (t, y[0], x[0], vsw, y[1])
        x = Ad @ x + Bd @ np.array([vsw, -il])
    return out


def main():
    best = tune()
    if best is None:
        raise SystemExit("no gain set meets PM >= 45 deg and GM >= 8 dB")
    g, w = best
    GAINS.update(g)
    lines = ["# Closed loop with the control board's delay (generated by loop_digital.py)", "",
             f"Delay TD = {TD * 1e6:.0f} us sample-to-PWM plus the zero-order hold (Ts / 2 = {TS / 2 * 1e6:.0f} us), "
             f"Ts = {TS * 1e6:.0f} us (31.25 kSPS per controlled channel). Duty limit {D_MAX}.", "",
             f"Gains chosen by a grid search on variant B (PM >= 45 deg, GM >= 8 dB at every corner, lowest output "
             f"impedance peak 20 Hz-5 kHz at 700 ohm): **Kp = {g['Kp']}, Ki = {g['Ki']} 1/s, Kc = {g['Kc']} ohm** "
             "(v_sw in volts per volt of error; Kc in volts per ampere of capacitor current).", "",
             "## Margins and output impedance per corner (same gains)", "",
             "| Variant | ESR (ohm) | Load | Crossover (Hz) | Phase margin (deg) | Gain margin (dB) | max closed-loop Zout 20 Hz-5 kHz (ohm) at f (Hz) | Zout at 100 Hz / 1 kHz / 4 kHz / 20 kHz (ohm) |",
             "|---|---|---|---|---|---|---|---|"]
    m = (F >= 20) & (F <= 5e3)
    for v, esr, rl in CORNERS:
        p = hvnet.params(v, ESR=esr)
        pm, fc, gm = margins(loop_gain(p, rl, g)[0])
        z = np.abs(zcl(p, rl, g))
        k = np.argmax(z[m])
        zf = [np.interp(x, F, z) for x in (100, 1000, 4000, 20000)]
        lines.append(f"| {v} | {esr} | {'open' if rl is None else f'{rl:.0f} ohm'} | {fc:.0f} | {pm:.0f} | {gm:.1f} | "
                     f"{z[m][k]:.2f} at {F[m][k]:.0f} | {zf[0]:.2f} / {zf[1]:.2f} / {zf[2]:.2f} / {zf[3]:.2f} |")
    ba = tune(("A",))
    if ba:
        lines += ["", f"Variant A tuned on its own (same rules): best Kp = {ba[0]['Kp']}, Ki = {ba[0]['Ki']}, Kc = {ba[0]['Kc']}: "
                  f"crossover {ba[1]['fc']:.0f} Hz, phase margin {ba[1]['pm']:.0f} deg, gain margin {ba[1]['gm']:.1f} dB, "
                  f"max Zout 20 Hz-5 kHz {ba[1]['z']:.2f} ohm (variant B with its gains: {w['z']:.2f} ohm)."]
    # delay sensitivity
    lines += ["", "## Delay sensitivity (variant B, ESR 0.1 ohm, 700 ohm, same gains)", "",
              "| Sample-to-PWM delay (us) | Phase margin (deg) | Gain margin (dB) | max Zout (ohm) |", "|---|---|---|---|"]
    p = hvnet.params("B", ESR=0.1)
    for td in (40e-6, 50e-6, 60e-6, 80e-6, 100e-6):
        T = loop_gain(p, 700.0, g, td=td)[0]
        pm, fc, gm = margins(T)
        n = net(p, F, 700.0)
        s = 2j * np.pi * F
        dd = np.exp(-s * (td + TS / 2)); cv = g["Kp"] + g["Ki"] / s
        z = np.abs(n["Zo"] + n["Gvd"] * (-dd * (cv * n["Zo"] + g["Kc"] * n["Hic"]) / (1 + T)))
        lines.append(f"| {td * 1e6:.0f} | {pm:.0f} | {gm:.1f} | {np.max(z[m]):.2f} |")
    # without active damping
    g0 = dict(g, Kc=0.0)
    best0 = None
    for kp in (0.05, 0.1, 0.2, 0.3, 0.5, 1.0):
        for ki in (30, 100, 300, 1000):
            gg = dict(Kp=kp, Ki=ki, Kc=0.0)
            w0 = evaluate(gg)
            if w0["pm"] >= 45 and w0["gm"] >= 8 and (best0 is None or w0["z"] < best0[1]["z"]):
                best0 = (gg, w0)
    lines += ["", "Without the capacitor-current damping (Kc = 0, voltage PI only): " +
              (f"best Kp = {best0[0]['Kp']}, Ki = {best0[0]['Ki']}: crossover {best0[1]['fc']:.0f} Hz, max Zout "
               f"{best0[1]['z']:.1f} ohm." if best0 else "no gain set meets the margins.")]

    # time domain, variant B (the drawn one) and A for comparison
    lines += ["", "## Time domain (raw 420 V unless stated, the low end of the rail: D14 headroom)", "",
              "| Case | Variant | V_tab min / max (V) | Bridge current iL1 min / max (A) | Note |", "|---|---|---|---|---|"]
    aud = lambda t: 0.60 + 0.20 * abs(np.sin(2 * np.pi * 82.4 * t))
    step = lambda t: 0.10 if t < 10e-3 else 0.80
    cases = [
        ("Overdrive load 0.60 + 0.20 |sin(2 pi 82 Hz t)| (0.7 A average, 0.8 A peaks) at 400 V", 400.0, lambda t: 400.0, aud, 4000.0, 100e-3, 40e-3, 420.0),
        ("Same at 430 V raw", 400.0, lambda t: 400.0, aud, 4000.0, 100e-3, 40e-3, 430.0),
        ("Same at 380 V setpoint", 380.0, lambda t: 380.0, aud, 4000.0, 100e-3, 40e-3, 420.0),
        ("Load step 0.10 -> 0.80 A at 380 V", 380.0, lambda t: 380.0, step, 4000.0, 40e-3, 5e-3, 420.0),
        ("Ramp up 200 -> 400 V in 30 ms, load 570 ohm (0.7 A at 400 V)", 200.0,
         lambda t: 200.0 + 200.0 * min(max((t - 5e-3) / 30e-3, 0), 1), lambda t: 0.0, 570.0, 60e-3, 0.0, 430.0),
        ("Ramp down 400 -> 200 V in 30 ms, load 2 kohm (idle)", 400.0,
         lambda t: 400.0 - 200.0 * min(max((t - 5e-3) / 30e-3, 0), 1), lambda t: 0.0, 2000.0, 60e-3, 0.0, 430.0),
        ("Ramp down 400 -> 200 V in 30 ms, no load", 400.0,
         lambda t: 400.0 - 200.0 * min(max((t - 5e-3) / 30e-3, 0), 1), lambda t: 0.0, None, 60e-3, 0.0, 430.0),
    ]
    for name, v0, vref, il, rl, tend, tmeas, vraw in cases:
        for var in ("B", "A"):
            p = hvnet.params(var, ESR=0.1)
            o = simulate(p, rl, g, tend, vref, il, v_raw=vraw, v0=v0)
            mm = o[:, 0] >= tmeas
            note = ""
            if "Ramp" in name:
                err = np.max(np.abs(o[:, 1] - np.array([vref(t) for t in o[:, 0]])))
                note = f"max tracking error {err:.1f} V"
                if "down" in name:
                    e_ret = -np.sum(np.minimum(o[:, 3] * o[:, 2], 0.0)) * 1e-6
                    note += f"; energy returned to the raw rail {e_ret:.1f} J"
            sat = np.mean(o[mm, 3] >= D_MAX * vraw - 1e-6) * 100
            if sat > 0:
                note += ("; " if note else "") + f"duty at the limit {sat:.0f} % of the time"
            lines.append(f"| {name} | {var} | {o[mm, 1].min():.1f} / {o[mm, 1].max():.1f} | "
                         f"{o[mm, 2].min():.2f} / {o[mm, 2].max():.2f} | {note} |")
            print(name, var, lines[-1])
    with open(os.path.join(HERE, "loop_results.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines[:20]))


if __name__ == "__main__":
    main()
