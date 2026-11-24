#!/usr/bin/env python3
"""HV supplies rev 3, ripple-filter / soft-switching study, step 4: what reaches the tubes and the
speaker, aliasing in the control loop, and the noise back onto the raw rail.

1. Supply-to-speaker transfer of the power stage at the switching frequencies: the power amp's
   stage.py (read only, 99cff1f: 4 tubes, 1650TA, 220 nF / 91k, 1k screen resistors, 8 ohm), bias
   solved for 70 % idle, PI outputs idle (10 kohm to ground), an AC source on V_ANODE or on V_SCREEN
   directly at the centre tap / screen node (the residue of r2 is already the voltage after the power
   amp's 100 nF); matched tubes and +-5 % idle mismatch between the sides; KT88 and EL34.
   Limit: the 1650TA model has leakage and DCR but no winding capacitance (its real self-resonances
   at 50-200 kHz are not modelled).
2. Residue at the speaker for the r2 operating points (recommended chain, ESR 0.3 ohm), anode and
   screen added in phase (worst), against today's hard-switched design and the proposed target.
3. Beat and intermodulation products: a transient of the same stage with V_ANODE and V_SCREEN each
   carrying a 1 V sine at different frequencies (two free-running bridges: 47.3 / 41 kHz) and a 1 kHz
   drive to about 10 W; the products f_a - f_s and f_sw +- f_audio at the speaker scale with the
   product of the two residues (bilinear), so they are reported scaled to the real residue amplitudes.
4. Aliasing in the loop: the first capacitor's current carries the TCM triangle (+-1 A); sampled
   asynchronously at 31.25 kSPS it folds into the audio band and enters v_sw through Kc. Output
   disturbance with the r3 loop, against synchronous sampling (mid-conduction CNV: no alias).
5. Conducted noise: the raw-rail figures of r2 (section 5) and the switch-node edges (r1) as common-
   mode current through the IGBT tabs' capacitance to the heatsinks / chassis.

Run: python3 rev3/sim/r4_residue.py   (writes r4_results.md and r4_*.png; a few minutes)
"""
import os
import re
import subprocess
import sys
import tempfile
from multiprocessing import Pool

import numpy as np

import filt
import r2_filter as r2
import r3_damping as r3
import tcm

HERE = os.path.dirname(os.path.abspath(__file__))
PA = os.path.expanduser("~/dev/tube_power_amp_kicad/rev_b/sim/power_stage")
sys.dont_write_bytecode = True
sys.path.insert(0, PA)
import stage  # noqa: E402

VA, VG2 = 400.0, {"KT88": 390.0, "EL34": 382.0}
P0 = dict(cc=220e-9, rgl=91e3, rsupply=1e-3, csupply=1e-12, driver="Rpi1 o1 0 10k\nRpi2 o2 0 10k")
FA = np.logspace(np.log10(1e3), np.log10(2e6), 400)


def bias(tube, mismatch):
    tubes = [tube] * 4
    ref = stage.solve_bias(tubes, VA, "B", VG2[tube], 0.7, dict(P0, f=100.0))
    if mismatch:
        ia0 = ref["ia"]
        tgt = [ia0[0] * (1 + mismatch), ia0[1] * (1 + mismatch), ia0[2] * (1 - mismatch), ia0[3] * (1 - mismatch)]
        ref = stage.solve_bias(tubes, VA, "B", VG2[tube], ("ia", tgt), dict(P0, f=100.0))
    return ref["vg1"]


def ac_transfer(args):
    tube, mismatch, which = args
    vg1 = bias(tube, mismatch)
    net = stage.netlist([tube] * 4, VA, "B", VG2[tube], 0.0, vg1, p=dict(P0, f=1000.0))
    if which == "anode":
        net = re.sub(r"^Vanode vas 0 .*$", f"Vanode vas 0 DC {VA} AC 1", net, flags=re.M)
    else:
        net = re.sub(r"^Vscreen vss 0 .*$", f"Vscreen vss 0 DC {VG2[tube]} AC 1", net, flags=re.M)
    a = net.index(".control")
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "o.txt")
        net = net[:a] + (".control\nset wr_singlescale\nac dec 40 1k 2meg\n"
                         f"wrdata {out} vm(out)\nquit\n.endc\n.end\n")
        stage.run_ngspice(net, timeout=600)
        z = np.loadtxt(out)
    return (tube, mismatch, which), (z[:, 0], z[:, 1])


def beat_run(args):
    tube, mismatch, amp_a, amp_s, fa, fs, drive = args
    vg1 = bias(tube, mismatch)
    p = dict(P0, f=1000.0)
    if drive > 0:
        p.pop("driver")
    net = stage.netlist([tube] * 4, VA, "B", VG2[tube], drive, vg1, p=p)
    net = re.sub(r"^Vanode vas 0 .*$", f"Vanode vas 0 SIN({VA} {amp_a} {fa})", net, flags=re.M)
    net = re.sub(r"^Vscreen vss 0 .*$", f"Vscreen vss 0 SIN({VG2[tube]} {amp_s} {fs})", net, flags=re.M)
    a = net.index(".control")
    t0, t1 = 10e-3, 40e-3
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "o.txt")
        net = net[:a] + (".options method=gear reltol=1e-5 abstol=1e-12 vntol=1e-7\n.control\nset wr_singlescale\n"
                         f"tran 0.25u {t1} {t0} 0.25u\nlinearize\nwrdata {out} v(out)\nquit\n.endc\n.end\n")
        stage.run_ngspice(net, timeout=3000)
        z = np.loadtxt(out)
    t, v = z[:, 0], z[:, 1]
    tu = np.linspace(t0, t1, int((t1 - t0) / 0.25e-6), endpoint=False)
    vu = np.interp(tu, t, v)
    w = np.hanning(len(vu))
    sp = np.abs(np.fft.rfft((vu - vu.mean()) * w)) / np.sum(w) * 2
    fr = np.fft.rfftfreq(len(vu), tu[1] - tu[0])
    return args, (fr, sp)


def amp_at(fr, sp, f, bw=60.0):
    m = np.abs(fr - f) < bw
    return sp[m].max() if m.any() else 0.0


def main():
    L = ["# Step 4: what reaches the tubes and the speaker (generated by r4_residue.py)", "", __doc__.split("\n\n")[1].strip(), ""]
    # ---------------------------------------------------------------- 1. transfer
    jobs = [(t, m, w) for t in ("KT88", "EL34") for m in (0.0, 0.05) for w in ("anode", "screen")]
    with Pool() as pool:
        tr = dict(pool.map(ac_transfer, jobs))
        bj = [("KT88", 0.05, 1.0, 1.0, 47.3e3, 41e3, 40.0), ("KT88", 0.05, 1.0, 0.0, 47.3e3, 41e3, 40.0),
              ("KT88", 0.05, 0.0, 1.0, 47.3e3, 41e3, 40.0), ("KT88", 0.05, 1.0, 1.0, 47.3e3, 41e3, 0.0)]
        beats = dict(pool.map(beat_run, bj))
    fq = [20e3, 40e3, 60e3, 100e3, 150e3, 300e3]
    L += ["## 1. Supply-to-speaker transfer (V at the 8 ohm load per V at the supply node)", "",
          "| Tubes | mismatch | supply | " + " | ".join(f"{f / 1e3:.0f} kHz" for f in fq) + " |", "|---|---|---|" + "---|" * len(fq)]
    H = {}
    for (t, m, w), (f, mag) in tr.items():
        H[(t, m, w)] = (f, mag)
        L.append(f"| {t} | {m * 100:.0f} % | {w} | " + " | ".join(f"{np.interp(x, f, mag):.1e}" for x in fq) + " |")
    L += ["", "Reading: the anode residue is common mode in the push-pull primary and reaches the secondary only through the "
          "mismatch and the tubes' plate resistance (tens of kilohms); the screen residue modulates both sides' plate "
          "currents through the screen transconductance and leaks through the same mismatch; above about 20 kHz the "
          "transformer's leakage inductance (64 mH) rolls everything off further.", ""]
    # ---------------------------------------------------------------- 2. speaker residue
    L += ["## 2. Residue at the speaker (uV rms, +-5 % mismatch; anode and screen added in phase)", "",
          "| Point (anode / screen) | f_sw common (kHz) | residue at the power amp: anode / screen (mV p-p) | speaker KT88 / EL34, recommended (uV rms) | "
          "speaker KT88 / EL34, today's hard-switched 50 kHz (uV rms) |", "|---|---|---|---|---|"]
    pairs = [((400, 0.7, 420), (390, 0.18, 420)), ((400, 0.3, 430), (390, 0.12, 430)), ((200, 0.35, 425), (195, 0.1, 425)),
             ((150, 0.2, 425), (146, 0.08, 425)), ((20, 0.5, 425), (19.5, 0.0, 425))]
    worst = 0.0
    for (va, ia, vin), (vs, isc, vin2) in pairs:
        f = min(tcm.law(va, ia, vin, tcm.DESIGN), tcm.law(vs, isc, vin2, tcm.DESIGN_SCREEN))
        res = []
        for name, f_use in (("rec", f), ("drawn, 3 mH", 50e3)):
            ch_a = r2.chain_for(filt.REC if name == "rec" else name, 1)
            ch_s = r2.chain_for(filt.REC if name == "rec" else name, 2)
            pa_, maga, _ = r2.residue(ch_a, f_use, va, vin, 0.3, va / ia if ia > 0 else None)
            ps_, mags, _ = r2.residue(ch_s, f_use, vs, vin2, 0.3, vs / isc if isc > 0 else None)
            h = np.arange(1, len(maga) + 1)
            spk = []
            for tube in ("KT88", "EL34"):
                fa_, ma_ = H[(tube, 0.05, "anode")]
                fs_, ms_ = H[(tube, 0.05, "screen")]
                spk.append(np.sqrt(np.sum(((maga * np.interp(h * f_use, fa_, ma_)) + (mags * np.interp(h * f_use, fs_, ms_))) ** 2) / 2))
            res.append((pa_, ps_, spk))
        worst = max(worst, max(res[0][2]))
        L.append(f"| {va:.0f} V {ia} A / {vs:.0f} V {isc} A | {f / 1e3:.0f} | {res[0][0] * 1e3:.1f} / {res[0][1] * 1e3:.1f} | "
                 f"{res[0][2][0] * 1e6:.1f} / {res[0][2][1] * 1e6:.1f} | {res[1][2][0] * 1e6:.1f} / {res[1][2][1] * 1e6:.1f} |")
    L += ["", f"Worst with the recommended chain: {worst * 1e6:.0f} uV rms, all of it at 40-150 kHz (today's design: up to about "
          "150-300 uV at mid voltage). Proposed target: switching residue at the speaker <= 50 uV rms (-86 dBV; a valve power "
          "stage's own hum and noise at the speaker is typically 0.1-1 mV, and the residue is ultrasonic), at the power amp's "
          "supply inputs <= 20 mV p-p (nominal ESR), and no product of the switching inside 20 Hz-20 kHz above 1 uV (-120 dBV).", ""]
    # ---------------------------------------------------------------- 3. beats
    L += ["## 3. Beat and intermodulation products (KT88, +-5 % mismatch, transient)", "",
          "1 V sines on V_ANODE (47.3 kHz) and V_SCREEN (41 kHz), 1 kHz drive (about 10 W) or none. Products at the speaker "
          "(V peak, Hann window over 30 ms):", "",
          "| Case | 6.3 kHz (f_a - f_s) | 47.3 kHz | 41 kHz | 46.3 / 48.3 kHz (f_a -+ 1 kHz) | 1 kHz fundamental |", "|---|---|---|---|---|---|"]
    for args, (fr, sp) in beats.items():
        _, _, aa, as_, fa, fs, dr = args
        lab = f"anode {aa:.0f} V, screen {as_:.0f} V, drive {'on' if dr else 'off'}"
        L.append(f"| {lab} | {amp_at(fr, sp, fa - fs, 20.0):.1e} | {amp_at(fr, sp, fa):.1e} | {amp_at(fr, sp, fs):.1e} | "
                 f"{amp_at(fr, sp, fa - 1e3):.1e} / {amp_at(fr, sp, fa + 1e3):.1e} | {amp_at(fr, sp, 1e3):.2f} |")
    k_both = [v for a, v in beats.items() if a[2] == 1.0 and a[3] == 1.0 and a[6] > 0][0]
    k_a = [v for a, v in beats.items() if a[2] == 1.0 and a[3] == 0.0][0]
    k_s = [v for a, v in beats.items() if a[2] == 0.0 and a[3] == 1.0][0]
    b6 = amp_at(*k_both, 6.3e3, 20.0)
    floor6 = max(amp_at(*k_a, 6.3e3, 20.0), amp_at(*k_s, 6.3e3, 20.0))
    # scale to the real residues: anode about 14 mV peak at 40 kHz, screen about 4 mV peak (r2, worst nominal)
    sc = 14e-3 * 4e-3
    L += ["", f"The difference product with both supplies carrying 1 V is {b6:.1e} V (the single-supply runs show the numerical "
          f"floor at that bin, {floor6:.1e} V). Scaled to the real residues (about 14 mV and 4 mV peak at the low end of the band: "
          f"x {sc:.1e}) it is {b6 * sc:.1e} V: far below 1 uV. The audio sidebands f_sw +- f_audio stay above 20 kHz. "
          "So with residues this small the bridges need not be synchronised for the speaker's sake; they should be for the "
          "loop's sampling (section 4) and the raw rail (r2 section 5: interleaving at a common frequency halves the input "
          "ripple current and cuts the PSU-cable ripple 4x).", ""]
    # ---------------------------------------------------------------- 4. aliasing
    L += ["## 4. Aliasing of the TCM ripple in the loop (V_ANODE, today's schedule, r3 gains)", "",
          "| f_sw (kHz) | I_C ripple fundamental after the 2 us filter (A peak) | alias frequency at 31.25 kSPS (Hz) | output disturbance, asynchronous sampling (mV peak) | synchronous mid-conduction sampling |",
          "|---|---|---|---|---|"]
    p0 = r3.chain(1)
    gk = dict(Kp=0.1, Ki=1000, Kc=0.5)
    gs = dict(Kp=0.75, Ki=2000, Kc=2)
    fs_adc = 31.25e3
    worst_alias = 0.0
    for fsw in (40e3, 47e3, 62.6e3, 94e3, 125.3e3, 150e3):
        n = filt.network(p0, np.array([fsw]), 571, 0.3)
        vo, vin = (400, 420) if fsw < 60e3 else ((400, 430) if fsw < 120e3 else (200, 425))
        a1 = 2 * vin / np.pi * np.sin(np.pi * vo / vin)
        ic = abs(a1 * n["Gic_all"][0]) / abs(1 + 2j * np.pi * fsw * 2e-6)
        fal = abs(fsw - round(fsw / fs_adc) * fs_adc)
        fal = max(fal, 1.0)
        out = []
        for g, sched in ((gk, (32e-6, 60e-6)), (gs, (20e-6, 30e-6))):
            nn = filt.network(p0, np.array([fal]), 571, 0.3)
            s = 2j * np.pi * fal
            d = np.exp(-s * (sched[1] + sched[0] / 2))
            cv = g["Kp"] + g["Ki"] / s
            T = d * (cv * nn["Gtab"][0] + g["Kc"] * nn["Gic_all"][0])
            out.append(abs(g["Kc"] * ic * d * nn["Gvd"][0] / (1 + T)))
        worst_alias = max(worst_alias, out[0])
        L.append(f"| {fsw / 1e3:.1f} | {ic:.2f} | {fal:.0f} | {out[0] * 1e3:.0f} (with the synchronous gains: {out[1] * 1e3:.0f}) | "
                 "none: the sample lands where the triangle crosses its average (offset < 50 mA for 50 ns of timing error) |")
    L += ["", f"Asynchronous sampling turns the ripple into an audio-band tone of up to {worst_alias * 1e3:.0f} mV at the output "
          "whose frequency moves with f_sw (and with the load, in the adaptive law): the TCM bridge needs the ADC's CNV "
          "timed by the PWM generator, in the middle of a high-side conduction interval of the bridge being sampled "
          "(or an anti-alias filter, which costs the phase the damping needs).", ""]
    # ---------------------------------------------------------------- 5. conducted noise
    L += ["## 5. Conducted noise", "",
          "| Quantity | Today (hard-switched, 50 kHz) | TCM (recommended) |", "|---|---|---|",
          "| Switch-node edge rate | 20-50 V/ns (datasheet t_r 4-6 ns; M15) | 1.2-4 V/ns (r1 switching model) |",
          "| Common-mode current through 20 pF (tab + heatsink to chassis) | 0.4-1.0 A peaks, ~10-20 ns | 25-80 mA, 100-400 ns |",
          "| Edge spectrum corner (1 / (pi t_r)) | 16-30 MHz | 0.8-3 MHz |",
          "| Raw node UIN ripple / PSU cable ripple (r2 sec. 5) | 0.19 V p-p / 0.7 mA rms | 0.27-0.6 V p-p / 0.4-2.1 mA rms interleaved (8 mA in phase) |",
          "", "The soft edges cut the common-mode noise above a few MHz by about 20-25 dB; the differential ripple drawn from the "
          "raw rail rises (larger, slower inductor ripple), and stays small on the PSU cable when the two bridges are "
          "interleaved at one frequency."]
    # plot transfers
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for (t, m, w), (f, mag) in H.items():
        ax.loglog(f, mag, lw=1, label=f"{t} {m * 100:.0f} % {w}")
    ax.axvspan(40e3, 150e3, color="0.9")
    ax.set_xlabel("Hz")
    ax.set_ylabel("V at the speaker per V on the supply")
    ax.grid(True, which="both", lw=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "r4_supply_to_speaker.png"), dpi=110)
    plt.close(fig)
    open(os.path.join(HERE, "r4_results.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
