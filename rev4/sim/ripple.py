#!/usr/bin/env python3
"""rev4 switching-ripple check: two synchronous bucks at 50 kHz, center-aligned, 180 deg apart (PLAN.md D5, D9).

Each output (always continuous conduction: synchronous switches, so the network is linear):

  sw --L1 (2 mH toroid, DCR, Cw)--+-- uc --L2 (|| Rd optional, DCR)--+-- vo --cable--+-- pa
                                  |                                   |               |
                         C1 branches (I_C shunt)             C2 branches          C_pa (power amp) + load R

Input side (both bridges): PSU cable (R, L) -- B_P (C_in1, RAW_SS taps) -- L_in -- UIN (C_hs) -- bridges.

The switch node is an ideal 0 / Vin square wave with duty D = Vout / Vin (losses ignored for the ripple);
voltages and currents are summed over its harmonics (exact for a linear network in steady state). The
bridge input current is s(t) * i_L(t), rebuilt in time and transformed back for the input network.

Run: python3 rev4/sim/ripple.py   (writes rev4/sim/ripple_results.md and ripple_*.png)
"""
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

FSW = 50e3
VIN = 425.0
NH = 400                 # harmonics (to 20 MHz)
NT = 4000                # time points per period

# parts (rev3 assumptions where they exist: electrolytic ESR corners 0.1 / 0.5 ohm, cable, the power amp's 100 nF)
L1, RL1, CW1 = 2.0e-3, 0.7, 25e-12          # 2 mH toroid: DCR estimated for ~150 turns of 0.8 mm; winding C
L2, RL2, CW2 = 33e-6, 0.10, 3e-12           # SRP1038C class
ESL_EL, ESL_FILM = 15e-9, 8e-9
CABLE_R, CABLE_L = 0.05, 0.5e-6             # W04 / W05, about 0.5 m
C_PA = 100e-9                               # the power amp's supply-input capacitor
PSU_R, PSU_L = 0.3, 1.0e-6                  # W01 cable and the PSU's output (rev3 lc_ac)
ESR_CORNERS = {"hot": 0.1, "typ": 0.5, "cold": 1.5}

# filter variants. Capacitor entries: (C, ESR or "E" = the electrolytic corner [+ extra R as ("E", r)], ESL)
VARIANTS = {
    "A v2-like": dict(
        note="v2 values with 2 mH: 47 uF el at uc, 33 uH, 47 uF el at vo",
        C1=[(47e-6, "E", ESL_EL)], Rd=None, C2=[(47e-6, "E", ESL_EL)]),
    "B + film": dict(
        note="A plus 2.2 uF film at uc and 1 uF film at vo",
        C1=[(47e-6, "E", ESL_EL), (2.2e-6, 0.01, ESL_FILM)], Rd=None,
        C2=[(47e-6, "E", ESL_EL), (1.0e-6, 0.01, ESL_FILM)]),
    "C 4.7 uF film at vo": dict(
        note="47 uF el + 2.2 uF film at uc; 33 uH; 4.7 uF film at vo with a damping leg 22 uF el + 1.2 ohm",
        C1=[(47e-6, "E", ESL_EL), (2.2e-6, 0.01, ESL_FILM)], Rd=None,
        C2=[(4.7e-6, 0.01, ESL_FILM), (22e-6, ("E", 1.2), ESL_EL)]),
    "D 100 uH, 10 uF film": dict(
        note="47 uF el + 4.7 uF film at uc; 100 uH; 10 uF film at vo with a damping leg 22 uF el + 2.2 ohm",
        C1=[(47e-6, "E", ESL_EL), (4.7e-6, 0.01, ESL_FILM)], Rd=None,
        C2=[(10e-6, 0.01, ESL_FILM), (22e-6, ("E", 2.2), ESL_EL)], L2=100e-6, RL2=0.25),
}

# operating points: (output, Vout, Iout)
POINTS = [("V_ANODE", 400, 0.70), ("V_ANODE", 300, 0.50), ("V_ANODE", 200, 0.35), ("V_ANODE", 150, 0.20),
          ("V_SCREEN", 390, 0.18), ("V_SCREEN", 290, 0.12), ("V_SCREEN", 150, 0.05)]

INPUT = dict(C_in1=[(47e-6, "E", ESL_EL), (47e-6, "E", ESL_EL)], L_in=33e-6, RL_in=0.1,
             C_hs=[(47e-6, "E", ESL_EL), (1e-9, 0.05, 5e-9), (1e-9, 0.05, 5e-9), (1.0e-6, 0.01, ESL_FILM)])


def _r(r, esr):
    if isinstance(r, tuple):
        return esr + r[1]
    return esr if r == "E" else r


def z_caps(lst, s, esr):
    y = 0
    for c, r, l in lst:
        y = y + 1.0 / (_r(r, esr) + s * l + 1.0 / (s * c))
    return 1.0 / y


def branch_currents(lst, s, esr, v):
    return [v / (_r(r, esr) + s * l + 1.0 / (s * c)) for c, r, l in lst]


def output_network(p, f, r_load, esr, l1=L1):
    """Transfer from the switch node: returns dict of node voltages / currents per unit switch voltage."""
    s = 2j * np.pi * f
    zl1 = 1.0 / (1.0 / (RL1 + s * l1) + s * CW1)
    l2, rl2 = p.get("L2", L2), p.get("RL2", RL2)
    zl2 = 1.0 / (1.0 / (rl2 + s * l2) + s * CW2 + (1.0 / p["Rd"] if p["Rd"] else 0))
    z_load = 1.0 / (s * C_PA + 1.0 / r_load)
    z_pa_side = CABLE_R + s * CABLE_L + z_load
    z_vo = 1.0 / (1.0 / z_caps(p["C2"], s, esr) + 1.0 / z_pa_side)
    z_uc = 1.0 / (1.0 / z_caps(p["C1"], s, esr) + 1.0 / (zl2 + z_vo))
    i_tot = 1.0 / (zl1 + z_uc)
    i_l1 = i_tot * zl1 / (RL1 + s * l1)       # the inductive branch only (Cw edge spikes excluded)
    v_uc = i_tot * z_uc
    i_l2 = v_uc / (zl2 + z_vo)
    v_vo = i_l2 * z_vo
    v_pa = v_vo * z_load / z_pa_side
    return dict(i_l1=i_l1, v_uc=v_uc, v_vo=v_vo, v_pa=v_pa,
                i_c1=branch_currents(p["C1"], s, esr, v_uc), i_c2=branch_currents(p["C2"], s, esr, v_vo))


def sw_harmonics(vin, d, phase):
    """Complex Fourier coefficients (one-sided, n = 1..NH) of a center-aligned pulse 0 / vin, width d,
    centred at phase (fraction of the period). x(t) = sum Re(c_n exp(j n w t))."""
    n = np.arange(1, NH + 1)
    return n, 2 * vin * np.sin(np.pi * n * d) / (np.pi * n) * np.exp(-2j * np.pi * n * phase)


def to_time(n, c, t):
    return np.real(np.exp(2j * np.pi * np.outer(t, n) * FSW) @ c)


def pp(x):
    return float(np.max(x) - np.min(x))


def rms_ac(x):
    return float(np.sqrt(np.mean((x - np.mean(x)) ** 2)))


def run_output(p, vout, iout, esr, l1=L1, phase=0.0):
    d = vout / VIN
    n, c = sw_harmonics(VIN, d, phase)
    f = n * FSW
    net = output_network(p, f, vout / iout, esr, l1)
    t = np.arange(NT) / NT / FSW
    res = {k: to_time(n, c * net[k], t) for k in ("i_l1", "v_uc", "v_vo", "v_pa")}
    res["i_c1"] = [to_time(n, c * ib, t) for ib in net["i_c1"]]
    res["i_c2"] = [to_time(n, c * ib, t) for ib in net["i_c2"]]
    res["i_l1"] = res["i_l1"] + iout                       # add the DC (the network transfer is AC-only here)
    res["s"] = (((t * FSW - phase) % 1.0 + 0.5) % 1.0 - 0.5)
    res["s"] = (np.abs(res["s"]) < d / 2).astype(float)
    res["t"] = t
    res["d"] = d
    return res


def run_input(i_in_total, esr):
    """i_in_total(t): the bridges' summed input current (A). Returns UIN, B_P voltage ripple and the PSU cable current."""
    t_n = len(i_in_total)
    spec = np.fft.rfft(i_in_total) / t_n
    n = np.arange(len(spec))
    f = n * FSW
    f[0] = 1e-3
    s = 2j * np.pi * f
    z_hs = z_caps(INPUT["C_hs"], s, esr)
    z_in1 = z_caps(INPUT["C_in1"], s, esr)
    z_src = PSU_R + s * PSU_L
    z_bp = 1.0 / (1.0 / z_in1 + 1.0 / z_src)
    z_lin = INPUT["RL_in"] + s * INPUT["L_in"]
    # current source (bridges) at UIN: UIN = -I * (z_hs || (z_lin + z_bp))
    z_uin = 1.0 / (1.0 / z_hs + 1.0 / (z_lin + z_bp))
    v_uin = -spec * z_uin
    i_lin = -v_uin / (z_lin + z_bp) * -1          # current through L_in toward UIN
    v_bp = -i_lin * z_bp
    i_psu = -v_bp / z_src
    for a in (v_uin, v_bp, i_psu):
        a[0] = 0
    back = lambda a: np.fft.irfft(a * t_n, t_n)
    return back(v_uin), back(v_bp), back(i_psu)


def resonances(p, esr, r_load):
    f = np.logspace(1, 6, 4000)
    net = output_network(p, f, r_load, esr)
    s = 2j * np.pi * f
    # open-loop output impedance at the tab: sw shorted, current injected at pa (linear superposition)
    zl1 = 1.0 / (1.0 / (RL1 + s * L1) + s * CW1)
    l2, rl2 = p.get("L2", L2), p.get("RL2", RL2)
    zl2 = 1.0 / (1.0 / (rl2 + s * l2) + s * CW2 + (1.0 / p["Rd"] if p["Rd"] else 0))
    z_uc = 1.0 / (1.0 / z_caps(p["C1"], s, esr) + 1.0 / zl1)
    z_vo = 1.0 / (1.0 / z_caps(p["C2"], s, esr) + 1.0 / (zl2 + z_uc))
    z_out = 1.0 / (1.0 / (z_vo + CABLE_R + s * CABLE_L) + s * C_PA + 1.0 / r_load)
    h = np.abs(net["v_vo"])
    return f, h, np.abs(z_out)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lines = ["# rev4 switching-ripple check", "",
             f"Generated by `rev4/sim/ripple.py`. 50 kHz, center-aligned, bridges 180° apart, Vin {VIN:.0f} V; "
             f"L1 = {L1 * 1e3:.1f} mH (DCR {RL1} Ω, {CW1 * 1e12:.0f} pF), L2 = {L2 * 1e6:.0f} µH; electrolytic ESR corners "
             + ", ".join(f"{k} {v} Ω" for k, v in ESR_CORNERS.items())
             + f"; cable {CABLE_L * 1e6:.1f} µH, power amp {C_PA * 1e9:.0f} nF. Ripple values are peak-to-peak.", ""]
    lines += ["Limits: R8 (original) ≤ 0.5 V p-p on V_ANODE, ≤ 0.2 V p-p on V_SCREEN; proposed (PS-1, rev3 N22) "
              "≤ 20 mV p-p at the power amp's supply inputs.", ""]
    for name, p in VARIANTS.items():
        lines += [f"## Variant {name}", "", p["note"], ""]
        lines += ["| Output | V / A | D | ΔI_L p-p | ripple at the tab (hot / typ / cold ESR) | at the power amp (hot / typ / cold) | "
                  "uc ripple (typ) | C1 el rms (typ) | C1 film rms |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for out, v, i in POINTS:
            r = {k: run_output(p, v, i, e) for k, e in ESR_CORNERS.items()}
            typ = r["typ"]
            film = rms_ac(typ["i_c1"][1]) if len(typ["i_c1"]) > 1 else 0.0
            lines.append(
                f"| {out} | {v} / {i} | {typ['d']:.2f} | {pp(typ['i_l1']):.2f} A | "
                + " / ".join(f"{1e3 * pp(r[k]['v_vo']):.1f}" for k in ESR_CORNERS) + " mV | "
                + " / ".join(f"{1e3 * pp(r[k]['v_pa']):.1f}" for k in ESR_CORNERS) + " mV | "
                + f"{1e3 * pp(typ['v_uc']):.0f} mV | {rms_ac(typ['i_c1'][0]):.3f} A | {film:.3f} A |")
        # resonances: local peaks of the open-loop output impedance (no load, hot and typ ESR)
        from scipy.signal import find_peaks
        f, h, _ = resonances(p, ESR_CORNERS["hot"], 400 / 0.7)
        txt = []
        for corner in ("hot", "typ"):
            ff, _, zn = resonances(p, ESR_CORNERS[corner], 1e6)
            k, _ = find_peaks(zn)
            txt.append(f"{corner} ESR: " + ", ".join(f"{ff[i]:.0f} Hz ({zn[i]:.1f} Ω)" for i in k if ff[i] < 200e3))
        lines += ["", "Open-loop output-impedance peaks (no load): " + "; ".join(txt)
                  + f". Attenuation sw → tab at 50 kHz (hot ESR): {np.interp(50e3, f, h):.1e}.", ""]
    # input side, variant B, worst duty mix
    lines += ["## Input side (both bridges, 180° apart, variant B outputs, typ ESR)", "",
              "| V_ANODE | V_SCREEN | UIN ripple | B_P ripple (RAW_SS taps) | PSU cable current rms | C_hs el rms |",
              "|---|---|---|---|---|---|"]
    pB = VARIANTS["B + film"]
    for (va, ia), (vs, is_) in (((400, 0.7), (390, 0.18)), ((300, 0.5), (290, 0.12)), ((200, 0.35), (290, 0.12)),
                                ((200, 0.35), (150, 0.05))):
        a = run_output(pB, va, ia, ESR_CORNERS["typ"], phase=0.0)
        b = run_output(pB, vs, is_, ESR_CORNERS["typ"], phase=0.5)
        i_in = a["s"] * a["i_l1"] + b["s"] * b["i_l1"]
        v_uin, v_bp, i_psu = run_input(i_in, ESR_CORNERS["typ"])
        # electrolytic share at UIN: approximate as the part of the AC input current not taken by L_in
        lines.append(f"| {va} V / {ia} A | {vs} V / {is_} A | {pp(v_uin):.2f} V | {1e3 * pp(v_bp):.0f} mV | "
                     f"{1e3 * rms_ac(i_psu):.1f} mA | {rms_ac(i_in):.2f} A (total AC input current) |")
    # plot: one waveform set
    fig, axs = plt.subplots(3, 1, figsize=(9, 8), sharex=True)
    r = run_output(VARIANTS["B + film"], 200, 0.35, ESR_CORNERS["typ"])
    t = r["t"] * 1e6
    axs[0].plot(t, r["i_l1"]); axs[0].set_ylabel("i_L1 (A)")
    axs[1].plot(t, 1e3 * (r["v_uc"] - r["v_uc"].mean())); axs[1].set_ylabel("uc ripple (mV)")
    axs[2].plot(t, 1e3 * (r["v_vo"] - r["v_vo"].mean()), label="tab")
    axs[2].plot(t, 1e3 * (r["v_pa"] - r["v_pa"].mean()), label="power amp")
    axs[2].set_ylabel("output ripple (mV)"); axs[2].legend(); axs[2].set_xlabel("µs")
    fig.suptitle("variant B, V_ANODE 200 V / 0.35 A, typ ESR")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "ripple_waveforms.png"), dpi=110)
    fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    for name, p in VARIANTS.items():
        f, h, z = resonances(p, ESR_CORNERS["hot"], 1e6)
        ax[0].loglog(f, h, label=name); ax[1].loglog(f, z, label=name)
    ax[0].set_ylabel("|v_tab / v_sw|, no load, hot ESR"); ax[1].set_ylabel("open-loop |Zout| (Ω)")
    ax[1].set_xlabel("Hz"); ax[0].legend(); ax[0].axvline(50e3, color="grey", ls=":")
    for a in ax:
        a.grid(alpha=0.3, which="both")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "ripple_transfer.png"), dpi=110)
    out = os.path.join(HERE, "ripple_results.md")
    open(out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
