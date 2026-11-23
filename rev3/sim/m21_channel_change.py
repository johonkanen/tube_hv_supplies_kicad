#!/usr/bin/env python3
"""HV supplies rev 3, review M21: a power-setting change between channels (V_ANODE 400 <-> 150 V,
V_SCREEN following in proportion: 390 <-> 146 V) under the firmware ramp rule, heard through the
output stage.

Chain: (1) the converter's closed loop (loop_digital.py, both bridges, raw 420 V) follows a linear
setpoint ramp with the tubes' idle current as its load; (2) its V_ANODE / V_SCREEN waveforms supply
the power amp's own stage model (tube_power_amp_kicad rev_b/sim/power_stage/stage.py, read only:
4x KT88, 220 nF / 91k coupling, Hammond 1650TA, 8 ohm) as PWL sources; (3) the bias follows the
power amp's tracking law's feed-forward (Vg1 scaled with V_SCREEN; power_stage README "Tracking
law": constant idle current below the reference, the measured-current loop trims it slowly; the
trim is not modelled, so the idle current falls about as V^1.5 during the ramp). The grid sees a
bias change through the 91k grid leak against the 220 nF coupling capacitor (about 22 ms).
Audible effects: the speaker voltage. With matched tubes the supply ramp is common mode and
cancels in the output transformer; with a mismatch (idle currents +-5 % between the two sides, the
bias loop's residual or a mid-ramp state) part of it appears across the speaker. Also run with
signal (a 220 Hz sine at about 1/4 power) to see the transition itself.
Raw input current during the up-steps: from the converter's power (both bridges) plus RAW_SS and
the board loss, 1 ms average, against the PSU's 1 A, for the ramp rule's times (45 ms idle,
0.3 s full load) and faster.

Limits: one-way coupling (the tubes' idle current as the converter's load, not the stage's actual
current); feed-forward bias only (no current-loop trim); the KT88 model's errors; a thump's
loudness estimated from the speaker voltage with 100 dB SPL / 1 W / 1 m (a guitar cabinet), no
frequency weighting (most of the thump energy is below 20 Hz: an overestimate of what is heard).

Run: python3 rev3/sim/m21_channel_change.py   (writes m21_results.md, m21_*.png; a few minutes)
"""
import os
import re
import sys
import tempfile
from multiprocessing import Pool

import numpy as np

import hvnet
import loop_digital as ld

HERE = os.path.dirname(os.path.abspath(__file__))
PA = os.path.expanduser("~/dev/tube_power_amp_kicad/rev_b/sim/power_stage")
sys.dont_write_bytecode = True
sys.path.insert(0, PA)
import stage  # noqa: E402

GAINS = dict(Kp=2, Ki=1000, Kc=20)
P_STAGE = dict(cc=220e-9, rgl=91e3, rsupply=0.05, csupply=100e-9)
TUBE = "KT88"
VA_HI, VS_HI, VA_LO = 400.0, 390.0, 150.0
VS_LO = VS_HI * VA_LO / VA_HI
T0 = 0.05


def ramp(v0, v1, tr):
    return lambda t: v0 + (v1 - v0) * min(max((t - T0) / tr, 0.0), 1.0)


def converter_waveforms(v_a0, v_a1, tr, t_end, i_idle_a, i_idle_s):
    """Both bridges following the ramp; load = idle current scaling with (V_SCREEN / 390)^1.5."""
    out = {}
    for b, v0, v1, rs, ii in ((1, v_a0, v_a1, 1.0, i_idle_a), (2, v_a0 * VS_HI / VA_HI, v_a1 * VS_HI / VA_HI, 2.2, i_idle_s)):
        vr = ramp(v0, v1, tr)
        vs_of_t = ramp(v_a0 * VS_HI / VA_HI, v_a1 * VS_HI / VA_HI, tr)
        il = lambda t, ii=ii: ii * (vs_of_t(t) / VS_HI) ** 1.5
        p = hvnet.params("B", ESR=0.1, Rs=rs)
        o = ld.simulate(p, None, GAINS, t_end, vr, il, v_raw=420.0, v0=v0)
        out[b] = o
    return out


def run_stage(args):
    name, v_a0, v_a1, tr, mismatch, signal = args
    t_end = T0 + tr + 0.15
    tubes = [TUBE] * 4
    # bias at the reference (400 V) for the idle current; side A +mismatch, side B -mismatch
    ref = stage.solve_bias(tubes, VA_HI, "B", VS_HI, 0.7, dict(P_STAGE, f=100.0))
    ia0 = ref["ia"]
    if mismatch:
        target = [ia0[0] * (1 + mismatch), ia0[1] * (1 + mismatch), ia0[2] * (1 - mismatch), ia0[3] * (1 - mismatch)]
        ref = stage.solve_bias(tubes, VA_HI, "B", VS_HI, ("ia", target), dict(P_STAGE, f=100.0))
    vg1 = ref["vg1"]
    i_idle_a = sum(ref["ia"])
    i_idle_s = sum(ref["ig2"])
    conv = converter_waveforms(v_a0, v_a1, tr, t_end, i_idle_a, i_idle_s)
    ta = conv[1][:, 0][::20]
    va = conv[1][:, 1][::20]
    vs = conv[2][:, 1][::20]
    # stage netlist with PWL supplies and PWL bias (feed-forward: Vg1 x V_SCREEN / 390)
    p = dict(P_STAGE, f=220.0)
    if not signal:
        p["driver"] = "Rpi1 o1 0 10k\nRpi2 o2 0 10k"
    drive = 40.0 if signal else 0.0
    net = stage.netlist(tubes, VA_HI, "B", VS_HI, drive, vg1, p=p)
    pa = " ".join(f"{x:.6e} {y:.4f}" for x, y in zip(ta, va))
    ps = " ".join(f"{x:.6e} {y:.4f}" for x, y in zip(ta, vs))
    net = re.sub(r"^Vanode vas 0 .*$", f"Vanode vas 0 PWL({pa})", net, flags=re.M)
    net = re.sub(r"^Vscreen vss 0 .*$", f"Vscreen vss 0 PWL({ps})", net, flags=re.M)
    for n in range(1, 5):
        pb = " ".join(f"{x:.6e} {vg1[n - 1] * y / VS_HI:.4f}" for x, y in zip(ta, vs))
        net = re.sub(rf"^Vb{n} b{n} 0 DC .*$", f"Vb{n} b{n} 0 PWL({pb})", net, flags=re.M)
    a = net.index(".control")
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "o.txt")
        net = net[:a] + (".control\nset wr_singlescale\n"
                         f"tran 5u {t_end} 0 5u\nlinearize\nwrdata {out} v(out) i(Vanode) i(Vscreen)\nquit\n.endc\n.end\n")
        stage.run_ngspice(net, timeout=3000)
        z = np.loadtxt(out)
    # raw input current from the converter (both bridges), 1 ms average
    t1 = conv[1][:, 0]
    pin = conv[1][:, 3] * conv[1][:, 2] + np.interp(t1, conv[2][:, 0], conv[2][:, 3] * conv[2][:, 2])
    iraw = np.convolve(pin / 420.0 + 0.035 + 8.7 / 420.0, np.ones(1000) / 1000, mode="same")
    return name, dict(t=z[:, 0], vout=z[:, 1], ia=-z[:, 2], isc=-z[:, 3], ta=t1, va=conv[1][:, 1], vs=np.interp(t1, conv[2][:, 0], conv[2][:, 1]),
                      iraw=iraw, i_idle=i_idle_a, vg1=vg1)


def lowpass(t, x, fc):
    from scipy.signal import butter, filtfilt
    fs = 1.0 / np.median(np.diff(t))
    b, a = butter(2, fc / (fs / 2))
    return filtfilt(b, a, x)


def raw_current_table():
    """Up-steps 150 -> 400 V: raw input current (1 ms avg) for ramp times, at idle and at full load."""
    rows = []
    for load, ia, isc in (("idle (KT88, 0.29 A at 400 V)", 0.29, 0.02), ("full overdrive (0.7 A / 0.18 A at 400 V)", 0.70, 0.18)):
        for tr in (0.03, 0.045, 0.1, 0.3, 0.5):
            t_end = T0 + tr + 0.03
            res = []
            for b, v0, v1, rs, ii in ((1, VA_LO, VA_HI, 1.0, ia), (2, VS_LO, VS_HI, 2.2, isc)):
                vr = ramp(v0, v1, tr)
                # a full-load current scales with the voltage (resistive-like), idle with V^1.5
                ex = 1.5 if load.startswith("idle") else 1.0
                il = lambda t, ii=ii, vr=vr, v1=v1, ex=ex: ii * (vr(t) / v1) ** ex
                p = hvnet.params("B", ESR=0.1, Rs=rs)
                res.append(ld.simulate(p, None, GAINS, t_end, vr, il, v_raw=420.0, v0=v0))
            pin = res[0][:, 3] * res[0][:, 2] + res[1][:, 3] * res[1][:, 2]
            iraw = np.convolve(pin / 420.0 + 0.035 + 8.7 / 420.0, np.ones(1000) / 1000, mode="same")
            m = (res[0][:, 0] > T0) & (res[0][:, 0] < t_end - 2e-3)
            rows.append((load, tr, iraw[m].max(), res[0][:, 2].max()))
    return rows


CASES = [
    ("down 400 -> 150 V in 30 ms, matched, idle", VA_HI, VA_LO, 0.03, 0.0, False),
    ("down 400 -> 150 V in 30 ms, +-5 % mismatch, idle", VA_HI, VA_LO, 0.03, 0.05, False),
    ("down 400 -> 150 V in 300 ms, +-5 % mismatch, idle", VA_HI, VA_LO, 0.3, 0.05, False),
    ("up 150 -> 400 V in 45 ms, +-5 % mismatch, idle", VA_LO, VA_HI, 0.045, 0.05, False),
    ("up 150 -> 400 V in 300 ms, +-5 % mismatch, idle", VA_LO, VA_HI, 0.3, 0.05, False),
    ("down 400 -> 150 V in 100 ms, +-5 % mismatch, with signal", VA_HI, VA_LO, 0.1, 0.05, True),
    ("up 150 -> 400 V in 100 ms, +-5 % mismatch, with signal", VA_LO, VA_HI, 0.1, 0.05, True),
]


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    with Pool() as pool:
        res = dict(pool.map(run_stage, CASES))
        rawrows = pool.apply(raw_current_table)
    L = ["# M21: channel change through the output stage (generated by m21_channel_change.py)", "",
         __doc__.split("\n\n")[1], "", __doc__.split("\n\n")[2], "", __doc__.split("\n\n")[3], "",
         "## Speaker voltage", "",
         "| Case | V_ANODE tracking: max error (V) | speaker peak, all (V) | speaker peak below 20 Hz / 20-200 Hz (V) | "
         "estimated peak SPL of the thump at 1 m, 20-200 Hz (dB) | idle anode current before / after (A) |",
         "|---|---|---|---|---|---|"]
    for name, *_ in CASES:
        r = res[name]
        t, v = r["t"], r["vout"]
        m = t > T0 - 0.01
        sub = lowpass(t, v, 20.0)
        band = lowpass(t, v, 200.0) - sub
        vref = np.array([ramp(*(c[1:3] + (c[3],)))(x) for c in CASES if c[0] == name for x in r["ta"]])
        err = np.max(np.abs(r["va"] - vref))
        if "signal" in name:
            spl = "— (signal present)"
        else:
            pk = np.abs(band[m]).max()
            spl = f"{100 + 10 * np.log10(max(pk ** 2 / 2 / 8.0, 1e-12)):.0f}"
        ia = r["ia"]
        L.append(f"| {name} | {err:.1f} | {np.abs(v[m]).max():.3f} | {np.abs(sub[m]).max():.3f} / {np.abs(band[m]).max():.3f} | {spl} | "
                 f"{np.mean(ia[(t > 0.02) & (t < T0)]):.3f} / {np.mean(ia[t > t[-1] - 0.02]):.3f} |")
    L += ["", "## Raw input current on an up-step 150 -> 400 V (both outputs, 1 ms average)", "",
          "| Load | ramp (ms) | raw input peak (A) | bridge 1 current peak (A) | within the PSU's 1 A |", "|---|---|---|---|---|"]
    for load, tr, ipk, ib in dict(((r[0], r[1]), r) for r in rawrows).values():
        L.append(f"| {load} | {tr * 1e3:.0f} | {ipk:.2f} | {ib:.2f} | {'yes' if ipk <= 1.0 else 'NO'} |")
    fig, ax = plt.subplots(3, 1, figsize=(9, 7), sharex=False)
    for name in ("down 400 -> 150 V in 30 ms, +-5 % mismatch, idle", "up 150 -> 400 V in 45 ms, +-5 % mismatch, idle"):
        r = res[name]
        ax[0].plot(r["ta"] * 1e3, r["va"], lw=0.8, label=name)
        ax[1].plot(r["t"] * 1e3, r["vout"], lw=0.6, label=name)
    r = res["down 400 -> 150 V in 100 ms, +-5 % mismatch, with signal"]
    ax[2].plot(r["t"] * 1e3, r["vout"], lw=0.4, label="down in 100 ms with signal")
    ax[0].set_ylabel("V_ANODE (V)"); ax[1].set_ylabel("speaker (V), idle"); ax[2].set_ylabel("speaker (V)")
    ax[2].set_xlabel("ms"); ax[0].legend(fontsize=7); ax[1].legend(fontsize=7); ax[2].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "m21_channel_change.png"), dpi=110); plt.close(fig)
    open(os.path.join(HERE, "m21_results.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
