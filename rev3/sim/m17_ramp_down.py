#!/usr/bin/env python3
"""HV supplies rev 3, review M17: a ramp-down returning the output capacitors' energy into the
raw rail and the tube PSU's DC link, with the PSU's unknowns as ranges.

What is known about the PSU (master docs/tube_psu_questions.md item 6, interfaces.md 3.1 / 8):
bidirectional DAB, "DC link sized for it, heaters use the energy up"; 47 W heater load balances a
full step at about a 200-250 ms ramp; up to 1 A forward. Unknown (ranges here): the capacitance on
the raw side (C_psu 0-470 uF, on top of this board's C101 + C201 + C206 = 141 uF), the DAB's sink
current limit (0 = off or not sinking, 0.1-1 A), its response time (0.5-10 ms first-order lag on
the current), and how much the PSU's own DC link can take before the DAB stops sinking (E_budget
5-20 J above what the heaters use: 47 W).

Model (averaged, the outputs track the setpoint: loop_digital.py shows 4 V tracking error and 6.1 J
returned for a 30 ms 400 -> 200 V step, against 6.06 J ideal): per output the returned power is
-d/dt(1/2 C V^2) minus the tube load (none = worst case, or idle current scaling as V^1.5) and the
bleeders; the converters' own loss while sinking (about 2-3 W, M15 cases H / I) is ignored (worst).
Raw node: C_board + C_psu, RAW_SS loads 25 mA, bleeder 150 kohm, the DAB as a current source
i = clamp(2 A/V x (430 - V_raw), -I_sink, +1 A) behind a lag. The HV supplies' latched raw trip at
475 V (tolerance 470-480 V) stops both bridges (the outputs then hold; nothing more returns: the
3 mH inductors' 1 mJ is negligible).

Firmware governor (proposed): the ramp-down slope is scaled by clamp((440 V - V_raw) / 5 V, 0, 1)
from the raw reading (ADC IN1, every 32 us), so the ramp pauses above 440 V and resumes below
435 V; the converter follows the setpoint slope within about 1 ms (modelled as a 1 ms lag).

Run: python3 rev3/sim/m17_ramp_down.py   (writes m17_results.md, m17_*.png; about a minute)
"""
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
C_OUT = 101e-6            # 100 uF electrolytic + 1 uF film per output
C_BOARD = 141e-6
R_BLEED_OUT = 1 / (1 / 220e3 + 1 / 3.015e6)
DT = 20e-6

STEPS = {  # name: (anode from, to, screen from, to)
    "full step 400 -> 150 V (screen 390 -> 150 V), 13.4 J": (400.0, 150.0, 390.0, 150.0),
    "the 10 J step of the PSU note (400 -> 220 V, 390 -> 260 V)": (400.0, 220.0, 390.0, 260.0),
    "shutdown ramp to 0 V before HV_ENABLE low, 15.7 J": (400.0, 0.0, 390.0, 0.0),
}


def simulate(cases, t_end=3.0, record=None):
    """cases: list of dicts with keys step, t_ramp, c_psu, i_sink, tau, e_budget, load, governor,
    trip. Vectorised over the cases. Returns a dict of arrays per case."""
    n = len(cases)
    g = lambda k: np.array([c[k] for c in cases], float)
    va0, va1, vs0, vs1 = (np.array([STEPS[c["step"]][j] for c in cases]) for j in range(4))
    t_ramp, c_psu, i_sink, tau, e_budget, src = g("t_ramp"), g("c_psu"), g("i_sink"), g("tau"), g("e_budget"), g("src")
    load, gov, trip_v = g("load"), g("governor"), g("trip")
    c_raw = C_BOARD + c_psu
    v_raw = np.full(n, 430.0)
    va, vs = va0.copy(), vs0.copy()
    sa, ss = va0.copy(), vs0.copy()          # setpoints
    i_dab = np.full(n, 0.0)
    e_dc = np.zeros(n)                        # energy the PSU's DC link holds above the heaters' use
    tripped = np.zeros(n, bool)
    sink_ok = np.ones(n, bool)
    rate_eff = np.ones(n)                     # governor factor after the 1 ms lag
    peak = v_raw.copy()
    t_trip = np.full(n, np.nan)
    e_ret = np.zeros(n)
    t_done = np.full(n, np.nan)
    rec = {k: [] for k in ("t", "raw", "va", "vs", "idab")} if record is not None else None
    steps = int(t_end / DT)
    slope_a = (va0 - va1) / t_ramp
    slope_s = (vs0 - vs1) / t_ramp
    i_idle_a = 0.30 * load                   # KT88 idle, 4 tubes, at 400 V
    i_idle_s = 0.02 * load
    t0 = 0.01
    for k in range(steps):
        t = k * DT
        # governor: firmware scales the setpoint slope from the raw reading
        want = np.where(gov > 0, np.clip((440.0 - v_raw) / 5.0, 0.0, 1.0), 1.0)
        rate_eff += (want - rate_eff) * DT / 1e-3
        run = (t >= t0) & ~tripped
        sa = np.where(run, np.maximum(sa - slope_a * rate_eff * DT, va1), sa)
        ss = np.where(run, np.maximum(ss - slope_s * rate_eff * DT, vs1), ss)
        # outputs: follow the setpoint while the bridges run; after a trip only load and bleeders
        ia_load = i_idle_a * np.clip(va / 400.0, 0, None) ** 1.5 + va / R_BLEED_OUT
        is_load = i_idle_s * np.clip(vs / 390.0, 0, None) ** 1.5 + vs / R_BLEED_OUT
        va_new = np.where(tripped, va - ia_load * DT / C_OUT, sa)
        vs_new = np.where(tripped, vs - is_load * DT / C_OUT, np.minimum(ss, va_new + 0.7))
        # power the bridges take from (+) or return to (-) the raw rail
        p_a = np.where(tripped, 0.0, va * ia_load + C_OUT * va * (va_new - va) / DT)
        p_s = np.where(tripped, 0.0, vs * is_load + C_OUT * vs * (vs_new - vs) / DT)
        va, vs = va_new, vs_new
        i_conv = (p_a + p_s) / v_raw
        e_ret += np.maximum(-(p_a + p_s), 0.0) * DT
        # DAB: regulates 430 V; sinks up to i_sink while its DC link has room
        cmd = np.clip(2.0 * (430.0 - v_raw), -i_sink * sink_ok, src)
        i_dab += (cmd - i_dab) * DT / tau
        e_dc += (np.maximum(-i_dab, 0.0) * v_raw - 47.0) * DT
        e_dc = np.maximum(e_dc, 0.0)
        sink_ok = e_dc < e_budget
        # raw node
        i_raw = i_dab - i_conv - 0.025 - v_raw / 150e3
        v_raw = v_raw + i_raw * DT / c_raw
        peak = np.maximum(peak, v_raw)
        newly = (v_raw >= trip_v) & ~tripped
        t_trip = np.where(newly, t, t_trip)
        tripped |= newly
        done = (np.abs(sa - va1) < 0.5) & (np.abs(ss - vs1) < 0.5) & np.isnan(t_done)
        t_done = np.where(done, t - t0, t_done)
        if rec is not None and k % 25 == 0:
            rec["t"].append(t); rec["raw"].append(v_raw.copy()); rec["va"].append(va.copy())
            rec["vs"].append(vs.copy()); rec["idab"].append(i_dab.copy())
    out = dict(peak=peak, tripped=tripped, t_trip=t_trip, e_ret=e_ret, t_done=t_done, va_end=va, vs_end=vs)
    if rec is not None:
        out["rec"] = {k: np.array(v) for k, v in rec.items()}
    return out


def case(step, t_ramp, c_psu=100e-6, i_sink=0.5, tau=2e-3, e_budget=10.0, load=0.0, governor=0, trip=475.0, src=1.0):
    return dict(step=step, t_ramp=t_ramp, c_psu=c_psu, i_sink=i_sink, tau=tau, e_budget=e_budget,
                load=load, governor=governor, trip=trip, src=src)


def fmt(peak, tripped, t_trip):
    if tripped:
        return f"**trip** at {t_trip * 1e3:.0f} ms"
    return f"{peak:.0f}"


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    full = list(STEPS)[0]
    ramps = [0.03, 0.1, 0.3, 1.0]
    L = ["# M17: ramp-down into the tube PSU's DC link (generated by m17_ramp_down.py)", "",
         __doc__.split("\n\n")[1], "", __doc__.split("\n\n")[2], "", __doc__.split("\n\n")[3], ""]
    # Table 1: no governor, full step, against DAB sink and capacitance, no load
    sinks = [("PSU off (no source, no sink)", 0.0, 2e-3, -1.0), ("DAB not sinking (forward only)", 0.0, 2e-3, 0.0), ("sink 0.1 A, 2 ms", 0.1, 2e-3, 10.0),
             ("sink 0.25 A, 2 ms", 0.25, 2e-3, 10.0), ("sink 0.5 A, 2 ms", 0.5, 2e-3, 10.0),
             ("sink 1 A, 2 ms", 1.0, 2e-3, 10.0), ("sink 1 A, 10 ms lag", 1.0, 10e-3, 10.0),
             ("sink 1 A, 2 ms, DC-link budget 5 J", 1.0, 2e-3, 5.0)]
    cpsus = [0.0, 100e-6, 470e-6]
    for stepname in STEPS:
        L += [f"## Without a governor: {stepname}, tubes cut off (no load): raw rail peak (V)", "",
              "| DAB | C_psu (uF) | " + " | ".join(f"ramp {r * 1e3:.0f} ms" for r in ramps) + " |",
              "|---|---|" + "---|" * len(ramps)]
        cases = [case(stepname, r, c_psu=c, i_sink=i, tau=ta, e_budget=max(eb, 0), src=0.0 if eb < 0 else 1.0) for (nm, i, ta, eb) in sinks for c in cpsus for r in ramps]
        res = simulate(cases)
        j = 0
        for nm, i, ta, eb in sinks:
            for c in cpsus:
                cells = []
                for r in ramps:
                    cells.append(fmt(res["peak"][j], res["tripped"][j], res["t_trip"][j]))
                    j += 1
                L.append(f"| {nm} | {c * 1e6:.0f} | " + " | ".join(cells) + " |")
        L.append("")
    # Table 2: with idle load
    L += [f"## Without a governor, tubes idling (KT88, 0.3 A at 400 V scaling with V^1.5): {full}", "",
          "| DAB | C_psu (uF) | " + " | ".join(f"ramp {r * 1e3:.0f} ms" for r in ramps) + " |", "|---|---|" + "---|" * len(ramps)]
    sinks_on = [x for x in sinks if x[3] >= 0]     # with the PSU off the idling tubes just drain the raw rail
    cases = [case(full, r, c_psu=c, i_sink=i, tau=ta, e_budget=eb, load=1.0) for (nm, i, ta, eb) in sinks_on for c in (0.0, 100e-6) for r in ramps]
    res = simulate(cases)
    j = 0
    for nm, i, ta, eb in sinks_on:
        for c in (0.0, 100e-6):
            cells = []
            for r in ramps:
                cells.append(fmt(res["peak"][j], res["tripped"][j], res["t_trip"][j]))
                j += 1
            L.append(f"| {nm} | {c * 1e6:.0f} | " + " | ".join(cells) + " |")
    # Table 3: with the governor
    L += ["", f"## With the firmware governor (pause above 440 V), no load: {full}", "",
          "| DAB | C_psu (uF) | ramp asked (ms) | raw peak (V) | ramp took (ms) | outputs at the end (V) |", "|---|---|---|---|---|---|"]
    gcases = []
    for nm, i, ta, eb in sinks:
        for c in (0.0, 470e-6):
            for r in (0.03, 0.3):
                gcases.append((nm, c, r, case(full, r, c_psu=c, i_sink=i, tau=ta, e_budget=max(eb, 0), src=0.0 if eb < 0 else 1.0, governor=1)))
    res = simulate([x[3] for x in gcases], t_end=6.0)
    for j, (nm, c, r, _) in enumerate(gcases):
        took = res["t_done"][j]
        L.append(f"| {nm} | {c * 1e6:.0f} | {r * 1e3:.0f} | {fmt(res['peak'][j], res['tripped'][j], res['t_trip'][j])} | "
                 f"{'not finished in 6 s' if np.isnan(took) else f'{took * 1e3:.0f}'} | {res['va_end'][j]:.0f} / {res['vs_end'][j]:.0f} |")
    # Plots
    pc = [case(full, 0.03, c_psu=100e-6, i_sink=0.5), case(full, 0.3, c_psu=100e-6, i_sink=0.5),
          case(full, 0.03, c_psu=0.0, i_sink=0.0), case(full, 0.03, c_psu=100e-6, i_sink=0.5, governor=1),
          case(full, 0.3, c_psu=0.0, i_sink=0.1, governor=1)]
    labels = ["30 ms, sink 0.5 A, 100 uF", "300 ms, sink 0.5 A, 100 uF", "30 ms, DAB off, 0 uF",
              "30 ms + governor, sink 0.5 A", "300 ms + governor, sink 0.1 A, 0 uF"]
    res = simulate(pc, t_end=2.0, record=True)
    rec = res["rec"]
    fig, ax = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    for j, lb in enumerate(labels):
        ax[0].plot(rec["t"] * 1e3, rec["raw"][:, j], label=lb, lw=1)
        ax[1].plot(rec["t"] * 1e3, rec["va"][:, j], lw=1)
    ax[0].axhline(475, color="r", ls="--", lw=0.7); ax[0].axhline(450, color="k", ls=":", lw=0.7)
    ax[0].set_ylabel("raw rail (V)"); ax[0].legend(fontsize=7); ax[1].set_ylabel("V_ANODE (V)"); ax[1].set_xlabel("ms")
    ax[0].set_xlim(0, 2000)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "m17_raw_rail.png"), dpi=110)
    open(os.path.join(HERE, "m17_results.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
