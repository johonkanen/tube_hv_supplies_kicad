#!/usr/bin/env python3
"""HV supplies rev 3, ripple-filter / soft-switching study, step 3: active damping of the first
resonance through the isolated link, with the recommended filter chain (filt.REC) and the TCM inductors.

Controller (control board FPGA), as loop_digital.py: every Ts it samples V_tab and the first
capacitor's current i_C (electrolytic + film, both returned through the I_C shunt, sampled in the
middle of a high-side conduction interval so that the triangle's ripple reads as its average: see
the report) and sets the half-bridge's average voltage
    v_sw = clamp(v_ref + Kp e + Ki integral(e) - Kc i_C, 0, D_MAX V_raw),   e = v_ref - V_tab,
which takes effect Td after the sample, held until the next one (ZOH: Ts / 2 on average; the TCM
PWM's own period adds up to T_sw / 2 = 12.5 us at 40 kHz, included in Td here).
Link schedules: "today" Ts 32 us (31 kSPS per controlled channel, round robin), Td 60 us (the
control board session's figure); "synchronous" Ts 20 us (the four control channels converted once
per 20 us, CNV timed by the PWM generator), Td 30 us; "fast" Ts 10 us, Td 15 us.

1. Margins over the tolerance corners (L1 +-10 % (gapped ferrite), C1 electrolytic -10 / +30 %, ESR 0.1 / 0.6 ohm,
   damping-leg resistance 1.1 / 2.5 ohm, load 571 ohm / open) with gains found by a grid search
   (PM >= 45 deg, GM >= 8 dB at every corner, lowest closed-loop |Zout| 20 Hz-20 kHz).
2. Which resonance frequency each schedule can damp: C1 scaled to put f1 at 0.5-3 kHz, the same search.
3. Time domain (exact discretisation of the averaged network, sampled controller with the delay):
   the M18 load cases (stage.py tube currents, KT88 square 82 Hz / 1 kHz and the note burst), the
   0.1 -> 0.8 A step, the 82 Hz overdrive envelope; the bridge current with the TCM ripple added
   (peak = |i_avg| + dI / 2, dI = 2 (|i_avg| + I_zvs)) against the trip levels.
4. The screen bridge (470 uH, R212 2.2 ohm) with the same structure.

Run: python3 rev3/sim/r3_damping.py   (writes r3_results.md and r3_*.png; the stage.py runs take a few minutes)
"""
import os
import sys
from multiprocessing import Pool

import numpy as np
from scipy.linalg import expm

import filt
import tcm

HERE = os.path.dirname(os.path.abspath(__file__))
F = np.logspace(0, np.log10(60e3), 1500)
FZ = (F >= 20) & (F <= 20e3)
SCHED = {"today (Ts 32 us, Td 60 us)": (32e-6, 60e-6), "synchronous (Ts 20 us, Td 30 us)": (20e-6, 30e-6),
         "fast (Ts 10 us, Td 15 us)": (10e-6, 15e-6)}
D_MAX = 0.97


def chain(bridge=1, passive=False, **kw):
    p = filt.chain(filt.REC_P if passive else filt.REC)
    if bridge == 2:
        p = dict(p, L1=tcm.DESIGN_SCREEN["L"], RL1=0.12, Rs=2.2)
    p = filt.scaled(p, **{k: v for k, v in kw.items() if k in ("kL1", "kC1", "kL2", "kC2")})
    if "rd" in kw:
        p["C2"] = [p["C2"][0], (p["C2"][1][0], kw["rd"], p["C2"][1][2])]
    return p


def corners(bridge=1):
    out = []
    for kL1 in (0.9, 1.1):
        for kC1 in (0.9, 1.3):
            for esr in (0.1, 0.6):
                for rd in (1.1, 2.5):
                    for rl in (571.0 if bridge == 1 else 2200.0, None):
                        out.append((dict(kL1=kL1, kC1=kC1, rd=rd), esr, rl))
    return out


_NC = {}


def net(p, esr, rl):
    key = (repr(sorted((k, repr(v)) for k, v in p.items())), esr, rl)
    if key not in _NC:
        _NC[key] = filt.network(p, F, rl, esr)
    return _NC[key]


def loop(n, g, ts, td):
    s = 2j * np.pi * F
    d = np.exp(-s * (td + ts / 2))
    cv = g["Kp"] + g["Ki"] / s
    T = d * (cv * n["Gtab"] + g["Kc"] * n["Gic_all"])
    # closed-loop output impedance at the power amp input: v_sw responds to the injected current
    # through both measurements (v_tab: Ztab, i_C: Hic of all C1 branches ~ Hic scaled)
    hic_all = n["Hic"] * (n["Gic_all"] / n["Gic"])
    vsw = -d * (cv * n["Ztab"] + g["Kc"] * hic_all) / (1 + T)
    z = n["Zo"] + n["Gvd"] * vsw
    return T, z


def margins(T):
    mag, ph = np.abs(T), np.unwrap(np.angle(T))
    pm, fc = 999.0, None
    for k in np.where(np.diff(np.sign(mag - 1.0)) != 0)[0]:
        m = (np.degrees(ph[k]) + 180) % 360
        m = m if m <= 180 else m - 360
        if m < pm:
            pm, fc = m, F[k]
    gm = 999.0
    phd = np.degrees(ph)
    for k in np.where(np.diff(np.floor((phd + 180) / 360)) != 0)[0]:
        gm = min(gm, -20 * np.log10(mag[k]))
    return pm, fc, gm


def evaluate(g, ts, td, cs, bridge=1, base=None):
    w = dict(pm=999, gm=999, z=0, fc=0, zf=0)
    for kw, esr, rl in cs:
        p = chain(bridge, **kw) if base is None else base(kw)
        n = net(p, esr, rl)
        T, z = loop(n, g, ts, td)
        pm, fc, gm = margins(T)
        if pm < w["pm"]:
            w["pm"], w["fc"] = pm, fc or 0
        w["gm"] = min(w["gm"], gm)
        za = np.abs(z[FZ])
        if za.max() > w["z"]:
            w["z"], w["zf"] = za.max(), F[FZ][za.argmax()]
    return w


GRID = [dict(Kp=kp, Ki=ki, Kc=kc) for kc in (0.5, 1, 1.5, 2, 2.5, 3, 4) for kp in (0.1, 0.25, 0.5, 0.75, 1, 1.5, 2)
        for ki in (250, 500, 1000, 2000)]


def tune(ts, td, cs, bridge=1, base=None):
    best = None
    for g in GRID:
        w = evaluate(g, ts, td, cs, bridge, base)
        if w["pm"] >= 45 and w["gm"] >= 8 and (best is None or w["z"] < best[1]["z"]):
            best = (g, w)
    return best


# ------------------------------------------------------------------ time domain
def state_space(p, esr, r_load):
    """x = [iL1, iL2, vC1e, vC1f, vC2, vCd, vpa], u = [v_sw, i_load]; y = [v_tab, i_C (C1 total), v_uc].
    W04's 0.5 uH is left out (the tab and the power amp node are one node with the 100 nF)."""
    (c1e, r1x, _), (c1f, r1f, _) = p["C1"][0], p["C1"][1]
    r1e = filt._r(r1x, esr)
    (c2, r2, _), (cd, rd, _) = p["C2"][0], p["C2"][1]
    cpa = filt.C_PA[0]
    gl = 0.0 if r_load is None else 1.0 / r_load

    def f(x, u):
        il1, il2, v1e, v1f, v2, vd, vpa = x
        uc = (il1 - il2 + v1e / r1e + v1f / r1f) / (1 / r1e + 1 / r1f)
        vo = (il2 + v2 / r2 + vd / rd + vpa / p["Rs"]) / (1 / r2 + 1 / rd + 1 / p["Rs"])
        dx = np.array([(u[0] - p["RL1"] * il1 - uc) / p["L1"],
                       (uc - vo - p["RL2"] * il2) / p["L2"],
                       (uc - v1e) / r1e / c1e, (uc - v1f) / r1f / c1f,
                       (vo - v2) / r2 / c2, (vo - vd) / rd / cd,
                       ((vo - vpa) / p["Rs"] - vpa * gl - u[1]) / cpa])
        y = np.array([vpa, (uc - v1e) / r1e + (uc - v1f) / r1f, uc])
        return dx, y
    n = 7
    A = np.zeros((n, n)); B = np.zeros((n, 2)); C = np.zeros((3, n)); Dm = np.zeros((3, 2))
    for k in range(n):
        e = np.zeros(n); e[k] = 1
        A[:, k], C[:, k] = f(e, np.zeros(2))
    for k in range(2):
        e = np.zeros(2); e[k] = 1
        B[:, k], Dm[:, k] = f(np.zeros(n), e)
    return A, B, C, Dm


def simulate(p, esr, g, ts, td, t_end, vref, iload, v_raw=420.0, dt=0.5e-6, r_load=None):
    A, B, C, Dm = state_space(p, esr, r_load)
    n = A.shape[0]
    M = expm(np.block([[A, B], [np.zeros((2, n + 2))]]) * dt)
    Ad, Bd = M[:n, :n], M[:n, n:]
    v0, i0 = vref(0.0), iload(0.0)

    def xss(vsw):
        return np.linalg.solve(-A, B @ np.array([vsw, i0]))
    y1, y2 = C @ xss(0.0) + Dm @ [0.0, i0], C @ xss(1.0) + Dm @ [1.0, i0]
    vsw0 = (v0 - y1[0]) / (y2[0] - y1[0])
    x = xss(vsw0)
    steps = int(round(t_end / dt))
    nts, ntd = int(round(ts / dt)), int(round(td / dt))
    integ = vsw0 - v0
    pending = []
    vsw = vsw0
    out = np.zeros((steps, 5))
    for k in range(steps):
        t = k * dt
        il = iload(t)
        y = C @ x + Dm @ [vsw, il]
        if k % nts == 0:
            vr = vref(t)
            e = vr - y[0]
            u = vr + g["Kp"] * e + integ - g["Kc"] * y[1]
            hi = D_MAX * v_raw
            uc = min(max(u, 0.0), hi)
            if uc == u or (u > hi and e < 0) or (u < 0 and e > 0):
                integ += g["Ki"] * ts * e
            pending.append((k + ntd, uc))
        while pending and pending[0][0] <= k:
            vsw = pending.pop(0)[1]
        out[k] = (t, y[0], x[0], vsw, y[1])
        x = Ad @ x + Bd @ np.array([vsw, il])
    return out


def tcm_peak(i_avg, izvs=tcm.DESIGN["izvs"]):
    return np.abs(i_avg) + (np.abs(i_avg) + izvs)


def tube_waves():
    """M18's stage.py runs (KT88): t, i_anode, i_screen."""
    sys.dont_write_bytecode = True
    import m18_power_stage as m18
    cases = [c for c in m18.CASES if c[0] in ("KT88 square 82 Hz", "KT88 square 1 kHz", "KT88 note burst, 82 Hz square from idle")]
    with Pool() as pool:
        cur = dict(pool.map(m18.tube_currents, [c + (None,) for c in cases]))
    return cur


def main():
    L = ["# Step 3: active damping and the link (generated by r3_damping.py)", "", __doc__.split("\n\n")[1].strip(), "",
         __doc__.split("\n\n")[2].strip(), ""]
    p0 = chain(1)
    n0 = filt.network(p0, F, 571, 0.3)
    rs = filt.resonances(p0, 0.3)
    L += [f"Recommended chain, V_ANODE: first resonance (L1 220 uH with C1 + C2 + Cd through L2) at {rs[0][0]:.0f} Hz "
          f"(|Zo| peak {rs[0][1]:.1f} ohm open loop), second stage's damped peak {rs[1][0]:.0f} Hz ({rs[1][1]:.1f} ohm).", ""]
    # 1. margins per schedule
    cs = corners(1)
    L += ["## 1. Margins over the tolerance corners (V_ANODE)", "",
          "| Schedule | gains Kp / Ki (1/s) / Kc (ohm) | crossover (Hz) | worst PM (deg) | worst GM (dB) | max closed-loop |Zout| 20 Hz-20 kHz (ohm) at f |",
          "|---|---|---|---|---|---|"]
    best, bestp = {}, {}
    for pas in (False, True):
        for sn, (ts, td) in SCHED.items():
            b = tune(ts, td, cs, 1, lambda kw, pas=pas: chain(1, passive=pas, **kw))
            (bestp if pas else best)[sn] = b
            lab = sn + (", + passive leg (10 uF film || 100 uF + 1.0 ohm)" if pas else ", active damping only")
            if b is None:
                L.append(f"| {lab} | none meets PM 45 / GM 8 | — | — | — | — |")
                continue
            g, w = b
            L.append(f"| {lab} | {g['Kp']} / {g['Ki']} / {g['Kc']} | {w['fc']:.0f} | {w['pm']:.0f} | {w['gm']:.1f} | {w['z']:.2f} at {w['zf']:.0f} |")
    gK = dict(Kp=0.0, Ki=0.0, Kc=0.0)
    # without the capacitor-current term
    for sn, (ts, td) in list(SCHED.items())[:1]:
        bb = None
        for g in [dict(Kp=kp, Ki=ki, Kc=0.0) for kp in (0.02, 0.05, 0.1, 0.2, 0.5) for ki in (10, 30, 100, 300)]:
            w = evaluate(g, ts, td, cs, 1)
            if w["pm"] >= 45 and w["gm"] >= 8 and (bb is None or w["z"] < bb[1]["z"]):
                bb = (g, w)
        if bb:
            L += ["", f"Without the capacitor-current term (Kc = 0, {sn}): best Kp {bb[0]['Kp']}, Ki {bb[0]['Ki']}: crossover "
                  f"{bb[1]['fc']:.0f} Hz, max |Zout| {bb[1]['z']:.1f} ohm at {bb[1]['zf']:.0f} Hz: the first resonance needs the active damping."]
    # 2. damping capability against f1
    L += ["", "## 2. Which first resonance each schedule can damp (C1 scaled; same search and corners)", "",
          "| f1 (Hz) | C1 total (uF) | " + " | ".join(SCHED) + " |", "|---|---|" + "---|" * len(SCHED)]
    for f1 in (500, 625, 750, 1000, 1250, 1500):
        c_need = 1 / ((2 * np.pi * f1) ** 2 * 220e-6)
        k = (c_need - 4.7e-6 - 4.7e-6 - 22e-6) / 100e-6
        if k <= 0.02:
            k = 0.02
        cells = []
        for sn, (ts, td) in SCHED.items():
            base = lambda kw, k=k: chain(1, **dict(kw, kC1=kw["kC1"] * k))
            b = tune(ts, td, [c for c in cs if c[0]["rd"] == 1.1 and c[2] is not None], 1, base)
            cells.append("no" if b is None else f"PM {b[1]['pm']:.0f} / GM {b[1]['gm']:.1f}, |Z| {b[1]['z']:.1f}")
        L.append(f"| {f1} | {c_need * 1e6:.0f} | " + " | ".join(cells) + " |")
    # 3. time domain
    sn0 = "today (Ts 32 us, Td 60 us)"
    sn1 = "synchronous (Ts 20 us, Td 30 us)"
    runs = [("synchronous, active (recommended)", sn1, best[sn1][0], False),
            ("today + passive leg (fallback)", sn0, bestp[sn0][0], True),
            ("today, active only", sn0, best[sn0][0], False)]
    L += ["", "## 3. Time domain (V_ANODE, raw 420 V, ESR 0.3 ohm, nominal parts)", "",
          "TCM peak = |i_avg| + (|i_avg| + I_zvs): the bridge's peak current if the TCM law kept every edge soft; "
          "the law caps it at 2.5 A (above about 1.05 A average the valley stops reversing for those periods: "
          "hard edges for a few milliseconds).", "",
          "| Case | Loop | V_tab min / max (V) | i_L1 average min / max (A) | TCM peak |i_L1| uncapped (A) | C1 current max (A, averaged) |",
          "|---|---|---|---|---|---|"]
    cases = [("Load step 0.10 -> 0.80 A at 380 V", 380.0, lambda t: 0.1 + 0.7 * (t > 5e-3), 0.03),
             ("Overdrive envelope 0.6 + 0.2 |sin 82 Hz| at 400 V", 400.0, lambda t: 0.6 + 0.2 * abs(np.sin(2 * np.pi * 82.4 * t)), 0.06),
             ("Ramp 200 -> 400 V in 100 ms at 570 ohm (current follows V)", None, None, 0.15)]
    tw = tube_waves()
    for name, (t, ia, isc, vout) in tw.items():
        cases.append((f"stage.py {name} (KT88, M18)", 400.0, (lambda t0, ia=ia, t=t: float(np.interp(t0, t, ia))), float(t[-1])))
    plots = []
    for name, v, il, tend in cases:
        for lab, sn, g, pas in runs:
            ts, td = SCHED[sn]
            pp = chain(1, passive=pas)
            if v is None:
                vr = lambda t: 200 + 200 * min(max((t - 5e-3) / 0.1, 0), 1)
                o = simulate(pp, 0.3, g, ts, td, tend, vr, lambda t: 0.0, r_load=570.0)
            else:
                o = simulate(pp, 0.3, g, ts, td, tend, lambda t, v=v: v, il)
            m = o[:, 0] > 2e-3
            pk = tcm_peak(o[m, 2])
            L.append(f"| {name} | {lab} | {o[m, 1].min():.1f} / {o[m, 1].max():.1f} | {o[m, 2].min():.2f} / {o[m, 2].max():.2f} | "
                     f"{pk.max():.2f} | {np.abs(o[m, 4]).max():.2f} |")
            if lab.startswith("synchronous") and (name.startswith("Load step") or "burst" in name):
                plots.append((name, o))
    # 4. screen bridge
    cs2 = corners(2)
    L += ["", "## 4. The screen bridge (470 uH, R212 2.2 ohm, same filter values)", "",
          "| Schedule | gains Kp / Ki / Kc | crossover (Hz) | worst PM (deg) | worst GM (dB) | max |Zout| 20 Hz-20 kHz (ohm) |", "|---|---|---|---|---|---|"]
    for sn, (ts, td) in SCHED.items():
        b = tune(ts, td, cs2, 2)
        if b is None:
            L.append(f"| {sn} | none | — | — | — | — |")
        else:
            g, w = b
            L.append(f"| {sn} | {g['Kp']} / {g['Ki']} / {g['Kc']} | {w['fc']:.0f} | {w['pm']:.0f} | {w['gm']:.1f} | {w['z']:.2f} at {w['zf']:.0f} |")
    # plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(len(plots) + 1, 1, figsize=(8, 3 * (len(plots) + 1)))
    for a, (nm, o) in zip(ax, plots):
        a.plot(o[:, 0] * 1e3, o[:, 1], lw=0.8, label="V_tab (V)")
        a2 = a.twinx()
        a2.plot(o[:, 0] * 1e3, o[:, 2], "C1", lw=0.6, label="i_L1 avg (A)")
        a.set_title(nm, fontsize=9)
        a.set_xlabel("ms")
    for sn, (ts, td) in SCHED.items():
        if best[sn]:
            T, z = loop(net(p0, 0.3, 571.0), best[sn][0], ts, td)
            ax[-1].loglog(F, np.abs(z), lw=1, label=sn)
    ax[-1].loglog(F, np.abs(n0["Zo"]), "k:", lw=0.8, label="open loop")
    ax[-1].set_xlim(20, 50e3)
    ax[-1].set_ylabel("|Zout| at the power amp (ohm)")
    ax[-1].legend(fontsize=7)
    ax[-1].grid(True, which="both", lw=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "r3_loop.png"), dpi=110)
    plt.close(fig)
    open(os.path.join(HERE, "r3_results.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
