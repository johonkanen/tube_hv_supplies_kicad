#!/usr/bin/env python3
"""HV supplies rev 3, review M18: the power stage fed from this converter.

Step 1 (tube currents): the power amp's own model, tube_power_amp_kicad rev_b/sim/power_stage/stage.py
(read only, imported from that repository at 99cff1f: 4 tubes, Hammond 1650TA, the decided 220 nF / 91k
coupling, 5.6k stoppers, 1k screen resistors, idle at 70 % of Pa max, 8 ohm load), run with a stiff
supply behind the power amp's own decoupling (100 nF / 630 V on V_ANODE and on V_SCREEN; the board
has no reservoir, so the HV supply's output capacitors are the reservoir). V_ANODE 400 V; V_SCREEN
390 V for KT88 (D13's upper end; the power amp's run used 400 V = V_ANODE), 382 V for EL34
(0.9 x 425 V). Drives as run_anode_current.py: the PI's soft-clipped sine at 160 V peak (deep
overdrive) and the clipped square (+-80 V, 20 us edges), 82 Hz and 1 kHz; and a note burst: the
82 Hz square switched on from idle at 50 ms for 300 ms, then off (the bias shift of the coupling
capacitors included). The supply currents i(Vanode), i(Vscreen) are recorded.

Step 2 (converter): each current waveform drives the closed loop of loop_digital.py (the same
gains Kp 2, Ki 1000 /s, Kc 20 ohm, 60 us + ZOH at 31.25 kSPS, duty limit 0.97, the drawn network:
bridge 1 with R205 1.0 ohm, bridge 2 with R212 2.2 ohm, ESR 0.1 ohm), raw 420 V (the low end).
Read: V_tab sag / overshoot, the bridge current against the 2.0 A trips, V_SCREEN against
V_ANODE (D201 conducts when V_SCREEN > V_ANODE + 0.7 V), and the raw input current
(sum of v_sw x i_L1 / V_raw, plus 35 mA RAW_SS, plus about 8.7 W of board loss) against the PSU's 1 A.

Limits: one-way coupling (the tube currents come from the stiff-supply run; the converter's
output moves by < 3 V, which changes a pentode's plate current by well under 1 %: checked by
re-running one case with the converter's V_ANODE / V_SCREEN waveforms as the stage's supplies);
the tube models' own errors (KT88 power about 23 % low, screen current about 30 % low: power amp
models README); averaged converter (no switching ripple: M15).

Run: python3 rev3/sim/m18_power_stage.py   (writes m18_results.md, m18_*.png; several minutes)
"""
import os
import re
import sys
from multiprocessing import Pool

import numpy as np

import hvnet
import loop_digital as ld

HERE = os.path.dirname(os.path.abspath(__file__))
PA = os.path.expanduser("~/dev/tube_power_amp_kicad/rev_b/sim/power_stage")
sys.dont_write_bytecode = True          # nothing is written into the power amp repository
sys.path.insert(0, PA)
import stage  # noqa: E402

VA = 400.0
VG2 = {"KT88": 390.0, "EL34": 382.0}
P_STAGE = dict(cc=220e-9, rgl=91e3, rsupply=0.05, csupply=100e-9)
GAINS = dict(Kp=2, Ki=1000, Kc=20)
V_RAW = 420.0


def drive_text(wave, burst):
    gate = " * u(time-0.05) * u(0.35-time)" if burst else ""
    if wave == "square":
        a = "80*tanh(sin(2*pi*f*time)/0.02)"
    else:
        a = "vclip*tanh(amp*sin(2*pi*f*time)/vclip)"
    return (f"Bpi1 d1 0 V = {{{a}{gate}}}\nBpi2 d2 0 V = {{-({a}){gate}}}\n"
            f"Rpi1 d1 o1 {stage.DEFAULTS['rout_pi']}\nRpi2 d2 o2 {stage.DEFAULTS['rout_pi']}")


def tube_currents(args):
    """Run stage.py with a stiff supply; return t, i_anode, i_screen (supply currents, positive out of the supply)."""
    name, tube, wave, f, t_end, burst, supply = args
    tubes = [tube] * 4
    p = dict(P_STAGE, f=f, driver=drive_text(wave, burst))
    bias = stage.solve_bias(tubes, VA, "B", VG2[tube], 0.7, dict(P_STAGE, f=f))["vg1"]
    net = stage.netlist(tubes, VA, "B", VG2[tube], 160.0, bias, p=p)
    if supply is not None:
        # re-run with the converter's output waveforms as the supplies (PWL)
        ta, va, vs = supply
        pa = " ".join(f"{x:.6e} {y:.4f}" for x, y in zip(ta, va))
        ps = " ".join(f"{x:.6e} {y:.4f}" for x, y in zip(ta, vs))
        net = re.sub(r"^Vanode vas 0 .*$", f"Vanode vas 0 PWL({pa})", net, flags=re.M)
        net = re.sub(r"^Vscreen vss 0 .*$", f"Vscreen vss 0 PWL({ps})", net, flags=re.M)
    a = net.index(".control")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "o.txt")
        net = net[:a] + (".control\nset wr_singlescale\n"
                         f"tran 5u {t_end} 0 5u\nlinearize\nwrdata {out} i(Vanode) i(Vscreen) v(out)\nquit\n.endc\n.end\n")
        stage.run_ngspice(net, timeout=3000)
        z = np.loadtxt(out)
    return name, (z[:, 0], -z[:, 1], -z[:, 2], z[:, 3])


CASES = [
    ("KT88 sine 82 Hz", "KT88", "sine", 82.4, 0.25, False),
    ("KT88 square 82 Hz", "KT88", "square", 82.4, 0.25, False),
    ("KT88 sine 1 kHz", "KT88", "sine", 1000.0, 0.15, False),
    ("KT88 square 1 kHz", "KT88", "square", 1000.0, 0.15, False),
    ("EL34 sine 82 Hz", "EL34", "sine", 82.4, 0.25, False),
    ("EL34 square 82 Hz", "EL34", "square", 82.4, 0.25, False),
    ("EL34 square 1 kHz", "EL34", "square", 1000.0, 0.15, False),
    ("KT88 note burst, 82 Hz square from idle", "KT88", "square", 82.4, 0.6, True),
    ("EL34 note burst, 82 Hz square from idle", "EL34", "square", 82.4, 0.6, True),
]


def converter(args):
    """Closed loop of one bridge driven by a load-current waveform."""
    name, bridge, t, i, v0 = args
    p = hvnet.params("B", ESR=0.1, Rs=1.0 if bridge == 1 else 2.2)
    il = lambda x: np.interp(x, t, i)
    o = ld.simulate(p, None, GAINS, t[-1], lambda x: v0, il, v_raw=V_RAW, v0=v0)
    return name, bridge, o


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ld.GAINS.update(GAINS)
    with Pool() as pool:
        cur = dict(pool.map(tube_currents, [c + (None,) for c in CASES]))
        jobs = []
        for name, tube, wave, f, t_end, burst in CASES:
            t, ia, isc, _ = cur[name]
            jobs.append((name, 1, t, ia, VA))
            jobs.append((name, 2, t, isc, VG2[tube]))
        conv = {(n, b): o for n, b, o in pool.map(converter, jobs)}
    L = ["# M18: the power stage fed from this converter (generated by m18_power_stage.py)", "",
         __doc__.split("\n\n")[1], "", __doc__.split("\n\n")[2], "", __doc__.split("\n\n")[3], "",
         "| Case | I_anode avg / peak (A) | I_screen avg / peak (A) | V_ANODE min / max (V) | V_SCREEN min / max (V) | "
         "bridge 1 / 2 current max (A) | V_SCREEN - V_ANODE max (V) | raw input avg / peak, 1 ms average (A) | output (W) |",
         "|---|---|---|---|---|---|---|---|---|"]
    summary = {}
    for name, tube, wave, f, t_end, burst in CASES:
        t, ia, isc, vout = cur[name]
        oa, os_ = conv[(name, 1)], conv[(name, 2)]
        tw0 = 0.05 if burst else t_end - 0.05          # measuring window
        ta = oa[:, 0]
        m = ta >= (0.0 if burst else tw0)
        mt = t >= (0.0 if burst else tw0)
        va, vs = oa[:, 1], np.interp(ta, os_[:, 0], os_[:, 1])
        # raw current: both bridges' power plus RAW_SS and the board loss, 1 ms moving average
        p_in = oa[:, 3] * oa[:, 2] + np.interp(ta, os_[:, 0], os_[:, 3] * os_[:, 2])
        i_raw = p_in / V_RAW + 0.035 + 8.7 / V_RAW
        k = 1000
        i_raw_1ms = np.convolve(i_raw, np.ones(k) / k, mode="same")
        mm = m & (ta > ta[0] + 1e-3) & (ta < ta[-1] - 1e-3)
        pout = np.mean(vout[mt] ** 2) / 8.0
        L.append(f"| {name} | {np.mean(ia[mt]):.3f} / {ia[mt].max():.3f} | {np.mean(isc[mt]):.3f} / {isc[mt].max():.3f} | "
                 f"{va[m].min():.1f} / {va[m].max():.1f} | {vs[m].min():.1f} / {vs[m].max():.1f} | "
                 f"{oa[m, 2].max():.2f} / {os_[:, 2][os_[:, 0] >= ta[m][0]].max():.2f} | {(vs - va)[m].max():.1f} | "
                 f"{np.mean(i_raw[m]):.2f} / {i_raw_1ms[mm].max():.2f} | {pout:.0f} |")
        summary[name] = (ta, va, vs, i_raw_1ms, t, ia, isc)
    # coupling check: KT88 square 82 Hz re-run with the converter's outputs as the supplies
    name = "KT88 square 82 Hz"
    ta, va, vs = summary[name][0], summary[name][1], summary[name][2]
    sel = slice(None, None, 20)
    c = [x for x in CASES if x[0] == name][0]
    _, (t2, ia2, is2, vo2) = tube_currents(c + ((ta[sel], va[sel], vs[sel]),))
    t1, ia1, is1, vo1 = cur[name]
    w1, w2 = t1 >= c[4] - 0.05, t2 >= c[4] - 0.05
    L += ["", f"Coupling check ({name}, converter outputs as the stage's supplies): anode current average "
          f"{np.mean(ia1[w1]):.4f} -> {np.mean(ia2[w2]):.4f} A, screen {np.mean(is1[w1]):.4f} -> {np.mean(is2[w2]):.4f} A, "
          f"output {np.mean(vo1[w1] ** 2) / 8:.1f} -> {np.mean(vo2[w2] ** 2) / 8:.1f} W."]
    # plots
    for tag, names in (("steady", ["KT88 square 82 Hz", "EL34 square 1 kHz"]),
                       ("burst", ["KT88 note burst, 82 Hz square from idle", "EL34 note burst, 82 Hz square from idle"])):
        fig, ax = plt.subplots(3, len(names), figsize=(11, 7), sharex="col")
        for j, n in enumerate(names):
            ta, va, vs, ir, t, ia, isc = summary[n]
            ax[0, j].plot(t * 1e3, ia, lw=0.6, label="I_anode"); ax[0, j].plot(t * 1e3, isc, lw=0.6, label="I_screen")
            ax[0, j].set_title(n, fontsize=9); ax[0, j].legend(fontsize=7); ax[0, j].set_ylabel("A")
            ax[1, j].plot(ta * 1e3, va, lw=0.6, label="V_ANODE"); ax[1, j].plot(ta * 1e3, vs, lw=0.6, label="V_SCREEN")
            ax[1, j].legend(fontsize=7); ax[1, j].set_ylabel("V")
            ax[2, j].plot(ta * 1e3, ir, lw=0.8); ax[2, j].axhline(1.0, color="r", ls="--", lw=0.7)
            ax[2, j].set_ylabel("raw input (A, 1 ms avg)"); ax[2, j].set_xlabel("ms")
            if tag == "steady":
                for r in range(3):
                    ax[r, j].set_xlim((t[-1] - 0.05) * 1e3, t[-1] * 1e3)
        fig.tight_layout(); fig.savefig(os.path.join(HERE, f"m18_{tag}.png"), dpi=110); plt.close(fig)
    open(os.path.join(HERE, "m18_results.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
