#!/usr/bin/env python3
"""HV supplies rev 3, ripple-filter / soft-switching study, step 2: the filter chain for the TCM
operating mode (r1: 220 uH / 470 uH, 40-150 kHz, both bridges at one common frequency).

1. Placement of the second resonance: the chains of filt.py (today's network; first stage only; the
   user's placement with f2 above the switching frequency, undamped and damped; f2 inside the band;
   the recommended f2 near 10 kHz with three ways of damping it): resonances, the second stage's
   attenuation v_pa / v_uc at f_sw = 40-150 kHz and at the harmonics, and the passive output impedance
   in the audio band above the loop's reach (2-20 kHz; the closed loop below that is r3).
2. Switching residue at the power amp's input (after W04 and its 100 nF) at the TCM operating points:
   the half-bridge's rectangular switch-node voltage (harmonics 1-40) through the averaged network,
   per chain, ESR corners 0.1 / 0.3 / 0.6 ohm (hot / nominal / cold electrolytic).
3. The first capacitor's ripple current (electrolytic and film share by impedance), ESR heating and life.
4. Tolerances (L +-20 %, film C +-10 %, electrolytic -10 / +30 %, ESR corners) and the frequency band.
5. The input side: the bridges' pulsed input current through the drawn input filter (C201 / C206 47 uF,
   100 nF, 1 nF; L101 33 uH; C101 47 uF; PSU 0.3 ohm + 1 uH): ripple on the raw node and current in
   the PSU cable, one bridge and both at 0 / 180 degrees, against the hard-switched design (M15).

Run: python3 rev3/sim/r2_filter.py   (writes r2_results.md, r2_*.png; seconds)
"""
import os

import numpy as np

import filt
import tcm

HERE = os.path.dirname(os.path.abspath(__file__))
D, DS = tcm.DESIGN, tcm.DESIGN_SCREEN
NH = 40
ESRS = (0.1, 0.3, 0.6)

# operating points for the residue: (name, Vo, Io, Vin, bridge)
OPS = [("400 V 0.70 A, raw 420 V", 400, 0.70, 420, 1), ("400 V 0.30 A, raw 430 V", 400, 0.30, 430, 1),
       ("400 V no load", 400, 0.0, 430, 1), ("200 V 0.35 A", 200, 0.35, 425, 1), ("150 V 0.20 A", 150, 0.20, 425, 1),
       ("20 V 0.5 A (start-up)", 20, 0.5, 425, 1),
       ("screen 390 V 0.18 A", 390, 0.18, 420, 2), ("screen 146 V 0.08 A", 146, 0.08, 425, 2)]


def chain_for(name, bridge):
    p = filt.chain(name)
    if bridge == 2 and name != "drawn, 3 mH":
        p = dict(p, L1=DS["L"], RL1=tcm.winding(DS["core"], DS["N"], DS["litz"])[0], Rs=2.2)
    elif bridge == 2:
        p = dict(p, Rs=2.2)
    return p


def op_freq(vo, io, vin, bridge, name):
    if name == "drawn, 3 mH":
        return 50e3
    d = D if bridge == 1 else DS
    return tcm.law(vo, io, vin, d)


def residue(p, f, vo, vin, esr, r_load, nh=NH, node="Gvd"):
    """p-p of the switching residue at the node (default the power amp input), V; harmonic list."""
    dcy = vo / vin
    h = np.arange(1, nh + 1)
    a = 2 * vin / (h * np.pi) * np.sin(h * np.pi * dcy)
    n = filt.network(p, f * h, r_load, esr)
    g = n[node]
    tt = np.linspace(0, 1 / f, 1000, endpoint=False)
    v = sum(np.real(a[k] * g[k] * np.exp(2j * np.pi * f * h[k] * tt)) for k in range(nh))
    return np.ptp(v), np.abs(a * g), n


def cap_ripple(p, f, vo, vin, esr, r_load, nh=NH):
    dcy = vo / vin
    h = np.arange(1, nh + 1)
    a = 2 * vin / (h * np.pi) * np.sin(h * np.pi * dcy)
    n = filt.network(p, f * h, r_load, esr)
    i_el = np.sqrt(np.sum(np.abs(a * n["Gic"]) ** 2) / 2)
    i_all = np.sqrt(np.sum(np.abs(a * n["Gic_all"]) ** 2) / 2)
    i_l = np.sqrt(np.sum(np.abs(a * n["Gil"]) ** 2) / 2)
    return i_el, i_all, i_l


def input_side(ops_pairs, interleave=True, hard=False):
    """Bridges' input current (high-side conduction: i_L while the high side or its diode conducts)
    through the input filter; returns raw-node ripple p-p and PSU cable current ripple rms."""
    # input network: PSU (0.3 ohm + 1 uH) -> B_P with C101 47u (0.3) -> L101 33u -> UIN with C201 47u (0.3) +
    # 100n + 1n (bridge 1) and C206 the same (bridge 2) on the same UIN in this lumped model
    res = []
    for pair in ops_pairs:
        f0 = None
        spectra = []
        if not hard:
            # both bridges at one frequency: the lower of the two laws (each stays soft: more ripple only)
            fc = min(tcm.law(*pair[0][:3], D), tcm.law(*pair[1][:3], DS)) if len(pair) > 1 else tcm.law(*pair[0][:3], D)
        for k, (vo, io, vin, br) in enumerate(pair):
            if hard:
                f = 50e3
                L = 3e-3
                dcy = vo / vin
                di = vo * (1 - dcy) / (L * f)
            else:
                d = D if br == 1 else DS
                f = fc
                dcy = vo / vin
                di = vo * (1 - dcy) / (d["L"] * f)
            f0 = f
            T = 1 / f
            t = np.linspace(0, T, 4000, endpoint=False)
            ton = dcy * T
            ival = io - di / 2
            il = np.where(t < ton, ival + di * t / ton, io + di / 2 - di * (t - ton) / (T - ton))
            iin = np.where(t < ton, il, 0.0)
            if interleave and k == 1:
                iin = np.roll(iin, len(t) // 2)
            spectra.append(iin)
        itot = sum(spectra)
        c = np.fft.rfft(itot) / len(itot) * 2
        h = np.arange(1, 41)
        ih = c[1:41]
        s = 2j * np.pi * f0 * h
        zc = lambda C, R, Ls=10e-9: R + s * Ls + 1 / (s * C)
        y_uin = 2 / zc(47e-6, 0.3, 20e-9) + 2 / zc(100e-9, 0.02, 3e-9) + 2 / zc(1e-9, 0.05, 2e-9)
        z_l101 = 0.01 + s * 33e-6
        z_psu = 0.3 + s * 1e-6
        y_bp = 1 / zc(47e-6, 0.3, 20e-9) + 1 / z_psu
        z_up = z_l101 + 1 / y_bp
        z_uin = 1 / (y_uin + 1 / z_up)
        v_uin = ih * z_uin                       # (sign aside) voltage at UIN per harmonic
        i_up = v_uin / z_up
        v_bp = i_up / y_bp
        i_psu = v_bp / z_psu
        tt = np.linspace(0, 1 / f0, 1000, endpoint=False)
        wave = lambda X: sum(np.real(X[k] * np.exp(2j * np.pi * f0 * h[k] * tt)) for k in range(len(h)))
        res.append(dict(f=f0, iin_rms=np.sqrt(np.mean((itot - itot.mean()) ** 2)), uin_pp=np.ptp(wave(v_uin)),
                        bp_pp=np.ptp(wave(v_bp)), ipsu_rms=np.sqrt(np.sum(np.abs(i_psu) ** 2) / 2)))
    return res


def plots():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    f = np.logspace(2, 6, 1500)
    fig, ax = plt.subplots(2, 1, figsize=(9, 8))
    for nm in filt.NAMES[1:]:
        p = filt.chain(nm)
        n = filt.network(p, f, 571, 0.1)
        ax[0].loglog(f, np.abs(n["Gvd"] / n["Guc"]), lw=1, label=nm)
        ax[1].loglog(f, np.abs(n["Zo"]), lw=1, label=nm)
    for a in ax:
        a.axvspan(40e3, 150e3, color="0.9")
        a.grid(True, which="both", lw=0.3)
    ax[0].set_ylabel("2nd stage v_pa / v_uc")
    ax[0].set_ylim(1e-4, 10)
    ax[0].legend(fontsize=6)
    ax[1].set_ylabel("open-loop |Zout| at the power amp (ohm)")
    ax[1].set_xlabel("Hz (grey: switching-frequency band 40-150 kHz)")
    ax[1].set_ylim(1e-2, 100)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "r2_second_stage.png"), dpi=110)
    plt.close(fig)


def main():
    L = ["# Step 2: the filter chain (generated by r2_filter.py)", "", __doc__.split("\n\n")[1].strip(), ""]
    # ---------------------------------------------------------------- 1. placement
    fs = [40e3, 60e3, 100e3, 150e3]
    L += ["## 1. Placement of the second resonance", "",
          "Resonances: peaks of the passive output impedance (load open, ESR 0.1 ohm). H2 = v_pa / v_uc, the second stage's "
          "own transfer (< 1 attenuates, > 1 amplifies); the switching frequency moves over 40-150 kHz (r1). "
          "|Zo| max: passive output impedance 2-20 kHz (below about 2 kHz the loop sets it, r3).", "",
          "| Chain | resonances f (Hz) / |Zo| peak (ohm) | H2 at 40 / 60 / 100 / 150 kHz | H2 at 2 x / 3 x 40 kHz | |Zo| max 2-20 kHz (ohm) at f |",
          "|---|---|---|---|---|"]
    fz = np.logspace(np.log10(2e3), np.log10(20e3), 400)
    for nm in filt.NAMES:
        p = filt.chain(nm)
        rs = filt.resonances(p)
        n = filt.network(p, np.array(fs + [80e3, 120e3]), 571, 0.1)
        h = np.abs(n["Gvd"] / n["Guc"])
        z = np.abs(filt.network(p, fz, 571, 0.1)["Zo"])
        L.append(f"| {nm} | " + ", ".join(f"{a:.0f} / {b:.2f}" for a, b in rs[:4]) + " | " +
                 " / ".join(f"{x:.3f}" for x in h[:4]) + f" | {h[4]:.3f} / {h[5]:.3f} | {z.max():.2f} at {fz[z.argmax()]:.0f} |")
    L += ["", "Reading: an LC section only attenuates above its resonance (H2 -> (f2 / f)^2), and amplifies around it "
          "(by its Q). With f2 = 200 kHz, above the band, the second stage gains 1.1-4.3x over 40-150 kHz undamped "
          "(1.1-1.6x damped) and only starts to help above about 250 kHz: at the switching frequency it adds nothing. "
          "With f2 inside the band (60 kHz) the variable frequency sweeps through the peak. "
          "Today's stage (27.7 kHz, Rd straight across L2) gives 0.9 at 40 kHz and 0.18 at 150 kHz: the parallel "
          "resistor makes the asymptote -20 dB/decade. The recommended stage, f2 near 9 kHz with an Rd-Cd leg, "
          "gives about 0.04 at 40 kHz and 0.003 at 150 kHz with the passive output impedance peak at about 3.5 ohm (R2: 5 ohm).", ""]
    # ---------------------------------------------------------------- 2. residue
    show = ["drawn, 3 mH", "first stage only (no L2)", "220 uH + drawn 2nd stage (33 uH || 5.6 ohm, 1 uF: 27.7 kHz)",
            "user: f2 = 200 kHz > f_sw, damped (6.8 uH || 8.2 ohm)", "f2 = 60 kHz, inside the f_sw band (10 uH || 4.7 ohm, 0.68 uF)",
            filt.REC]
    L += ["## 2. Switching residue at the power amp input (mV p-p, ESR 0.1 / 0.3 / 0.6 ohm)", "",
          "'drawn, 3 mH' is today's hard-switched design at 50 kHz (M15's tab ripple); the others run the TCM law of r1. "
          "Screen points use the screen chain (470 uH, 2.2 ohm).", "",
          "| Point | f_sw (kHz) | " + " | ".join(show) + " |", "|---|---|" + "---|" * len(show)]
    worst = {nm: 0.0 for nm in show}
    for name, vo, io, vin, br in OPS:
        f = op_freq(vo, io, vin, br, "x")
        rl = vo / io if io > 0 else None
        cells = []
        for nm in show:
            fx = op_freq(vo, io, vin, br, nm)
            vals = [residue(chain_for(nm, br), fx, vo, vin, e, rl)[0] * 1e3 for e in ESRS]
            worst[nm] = max(worst[nm], max(vals))
            cells.append(" / ".join(f"{v:.0f}" if v >= 10 else f"{v:.1f}" for v in vals))
        L.append(f"| {name} | {f / 1e3:.0f} | " + " | ".join(cells) + " |")
    L += ["", "Worst case over the points and ESR corners (mV p-p): " + "; ".join(f"{k}: {v:.0f}" for k, v in worst.items()) + ".",
          "Requirement R8: 500 mV on V_ANODE, 200 mV on V_SCREEN. Proposed target for this study: <= 20 mV p-p at either "
          "power amp input at every point with the nominal ESR, <= 50 mV at the cold-ESR corner (today's design: 7 mV at 400 V, "
          "59 mV at 200 V; r4 shows what reaches the speaker).", ""]
    # harmonic table for the recommended chain at the worst points
    rec = filt.REC
    L += ["### Recommended chain: residue by harmonic (mV peak, ESR 0.3 ohm)", "",
          "| Point | f_sw | 1 | 2 | 3 | 4 | 5 | 6-40 (rss) |", "|---|---|---|---|---|---|---|---|"]
    for name, vo, io, vin, br in OPS:
        f = op_freq(vo, io, vin, br, rec)
        rl = vo / io if io > 0 else None
        pp, mag, _ = residue(chain_for(rec, br), f, vo, vin, 0.3, rl)
        L.append(f"| {name} | {f / 1e3:.0f} kHz | " + " | ".join(f"{m * 1e3:.2f}" for m in mag[:5]) +
                 f" | {np.sqrt(np.sum(mag[5:] ** 2)) * 1e3:.3f} |")
    # ---------------------------------------------------------------- 3. capacitor ripple
    L += ["", "## 3. First capacitor: ripple current, heating, life (recommended chain)", "",
          "C1 = 100 uF / 500 V electrolytic (snap-in, returned through the I_C shunt) in parallel with 4.7 uF / 630 V film. "
          "Currents rms (switching harmonics; the audio-frequency load current adds a few tens of mA rms).", "",
          "| Point | f_sw (kHz) | inductor ripple rms (A) | electrolytic rms (A), ESR 0.1 / 0.3 / 0.6 | film rms (A) at ESR 0.3 | electrolytic loss at ESR(hot) 0.1-0.15 ohm (W) |",
          "|---|---|---|---|---|---|"]
    for name, vo, io, vin, br in OPS:
        f = op_freq(vo, io, vin, br, rec)
        rl = vo / io if io > 0 else None
        p = chain_for(rec, br)
        rr = [cap_ripple(p, f, vo, vin, e, rl) for e in ESRS]
        i_film = np.sqrt(max(rr[1][1] ** 2 - rr[1][0] ** 2, 0))     # approximate split (in quadrature)
        L.append(f"| {name} | {f / 1e3:.0f} | {rr[0][2]:.2f} | " + " / ".join(f"{r[0]:.2f}" for r in rr) +
                 f" | {i_film:.2f} | {rr[0][0] ** 2 * 0.12:.2f} |")
    L += ["", "Electrolytic (100 uF / 500 V / 105 C snap-in, 22 x 40 or 25 x 35 class): ripple rating about 1.0-1.3 A rms at "
          "120 Hz / 105 C, x1.4 at 10-100 kHz, x1.7-2 at 85 C ambient: about 2.4-3 A rms allowed at the board's 80 C. "
          "The worst 0.95 A rms takes about 30-40 % of it; 0.1-0.15 W of ESR heating raises the core about 2-4 K "
          "(the R_th of a 22 x 40 can is about 20-25 K/W). Life (doubling per 10 K): 5000 h at 105 C -> about "
          "5000 x 2^((105 - 84) / 10) = 21,000 h at an 84 C core, 10,000 h parts -> 42,000 h. "
          "Film alternative for C1 (all the ripple in film, MKP 0.1 % tan d): 2 x 10 uF / 500 V DC-link film "
          "(about 42 x 20 x 40 mm each) gives f1 = 2.4 kHz with 220 uH, too high for the delayed loop to damp (r3) and "
          "less audio-band reservoir; so the electrolytic stays as the reservoir and carries the ripple, with the 4.7 uF film "
          "in parallel for the high-frequency end and the cold-ESR corner.", ""]
    # ---------------------------------------------------------------- 4. tolerances
    L += ["## 4. Tolerances and the frequency band (recommended chain, 400 V / 0.7 A at 40 kHz and 200 V / 0.35 A at 150 kHz)", "",
          "| Case | f2 (Hz) | H2 at 40 kHz | residue 400 V / 0.7 A, 40 kHz (mV p-p, ESR 0.6) | residue 200 V, 150 kHz (mV p-p, ESR 0.6) | |Zo| max 2-20 kHz (ohm) |",
          "|---|---|---|---|---|---|"]
    p0 = filt.chain(rec)
    cases = [("nominal", dict()), ("L2 -20 %", dict(kL2=0.8)), ("L2 +20 %", dict(kL2=1.2)), ("C2 -10 %", dict(kC2=0.9)),
             ("L2 -20 %, C2 -10 %", dict(kL2=0.8, kC2=0.9)), ("C1 electrolytic -10 %", dict(kC1=0.9)),
             ("C1 electrolytic +30 %", dict(kC1=1.3)), ("L1 -20 % (f_sw +25 % at the same law)", dict(kL1=0.8)),
             ("Cd cold: ESR + 1 ohm (Rd leg 2.5 ohm)", dict(rd=2.5)), ("Cd hot: Rd leg 1.1 ohm", dict(rd=1.1))]
    for cn, kw in cases:
        kw = dict(kw)
        rd = kw.pop("rd", None)
        p = filt.scaled(p0, **kw)
        if rd:
            p["C2"] = [p["C2"][0], (p["C2"][1][0], rd, p["C2"][1][2])]
        rs = filt.resonances(p)
        f2 = max([a for a, b in rs if 3e3 < a < 50e3] or [0])
        n = filt.network(p, np.array([40e3]), 571, 0.1)
        h = abs(n["Gvd"][0] / n["Guc"][0])
        r1v = residue(p, 40e3, 400, 420, 0.6, 571)[0] * 1e3
        r2v = residue(p, 150e3, 200, 425, 0.6, 571)[0] * 1e3
        z = np.abs(filt.network(p, fz, 571, 0.1)["Zo"])
        L.append(f"| {cn} | {f2:.0f} | {h:.3f} | {r1v:.1f} | {r2v:.2f} | {z.max():.2f} |")
    L += ["", "The recommended stage has no resonance in the switching band at any tolerance corner; "
          "its attenuation at the band's low end varies +-25 % with the tolerances, the residue stays below the target. "
          "A variable switching frequency is harmless to it (it sits 4x below the lowest f_sw); "
          "a series trap at f_sw would be useless with a frequency that moves 4:1.", ""]
    # ---------------------------------------------------------------- 5. input side
    L += ["## 5. Input side: raw rail and the PSU cable", "",
          "| Case | f_sw (kHz) | bridge input current ripple rms (A) | raw node UIN ripple p-p (V) | B_P ripple p-p (V) | PSU cable ripple rms (mA) |",
          "|---|---|---|---|---|---|"]
    cases = [("hard-switched today, 400 V / 0.7 A + 390 V / 0.18 A, in phase (M15)", [((400, 0.7, 420, 1), (390, 0.18, 420, 2))], dict(hard=True, interleave=False)),
             ("TCM, 400 V / 0.7 A + 390 V / 0.18 A, common f, in phase", [((400, 0.7, 420, 1), (390, 0.18, 420, 2))], dict(interleave=False)),
             ("TCM, same, interleaved 180 deg", [((400, 0.7, 420, 1), (390, 0.18, 420, 2))], dict(interleave=True)),
             ("TCM, 200 V / 0.35 A + 195 V / 0.1 A, interleaved", [((200, 0.35, 425, 1), (195, 0.1, 425, 2))], dict(interleave=True)),
             ("TCM, 400 V idle 0.3 A + 390 V 0.1 A, interleaved", [((400, 0.3, 430, 1), (390, 0.1, 430, 2))], dict(interleave=True))]
    for cn, pairs, kw in cases:
        r = input_side(pairs, **kw)[0]
        L.append(f"| {cn} | {r['f'] / 1e3:.0f} | {r['iin_rms']:.2f} | {r['uin_pp']:.2f} | {r['bp_pp']:.3f} | {r['ipsu_rms'] * 1e3:.1f} |")
    L += ["", "The input filter's own resonance (L101 33 uH with C101 and the bridge capacitors, about 3 kHz, |Z| peak 0.9 ohm) "
          "is unchanged and far below the bridges' negative input resistance (V^2 / P = 616 ohm at 300 W): it needs no "
          "active damping. The TCM bridge draws a larger input ripple current (its inductor ripple is 2 A p-p instead of "
          "0.16 A); the input capacitors C201 / C206 carry it (rated about 1.6 A at 70 C, T3) and L101 + C101 keep it off the "
          "cable.", ""]
    plots()
    open(os.path.join(HERE, "r2_results.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
