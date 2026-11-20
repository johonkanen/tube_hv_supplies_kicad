#!/usr/bin/env python3
"""HV supplies rev 3: averaged (power-balance) model of the two buck converters in ngspice.

Answers the topology questions of the rev 3 requirements check (rev3/STATUS.md):
  Q-A  Ramp-down energy: when V_ANODE / V_SCREEN are ramped down quickly by a bidirectional
       (synchronous) half-bridge, where does the output capacitors' energy go?  The PSU's DAB is
       assumed unable to sink current, so it goes into the raw-rail capacitors on this board.
  Q-B  Ramp-down with the converter limited to forward current (diode emulation): how fast
       can the outputs come down when only the tube load discharges them?
  Q-C  Ramp-up 200 -> 400 V in 30 ms: converter current, raw-rail dip.
  Q-D  Audio-rate load: V_ANODE / V_SCREEN ripple with the v2 output capacitance and an assumed
       voltage-loop crossover (1 kHz and 300 Hz).

Model (averaged, no switching): each converter is a current source into its output
capacitance, i = clamp(PI(Vref - Vout), I_NEG, I_MAX), with a 5 kHz first-order inner-loop lag
and a duty limit Vout <= D_MAX * V_RAW; the raw rail supplies Vout * i / V_RAW (lossless), and
gets current back when i < 0. PSU = 430 V behind a diode (cannot sink) and 0.3 ohm. Raw-rail
capacitance on this board = v2's C1 + C2 + C11 + C26 = 156 uF; the PSU's own output capacitance
is unknown and not counted (worst case). Output capacitance: anode C3 + C4 = 94 uF, screen
C5 + C6 + C7 = 141 uF (v2 values; the second-stage 33 uH chokes ignored).

Run: python3 rev3/sim/converter_avg.py   (writes rev3/sim/results.md; about 10 s)
"""
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
C_RAW, C_A, C_S = 156e-6, 94e-6, 94e-6
D_MAX = 0.97


def netlist(case):
    va0, va1, vs0, vs1 = case["va"] + case["vs"]
    t0, tr = case.get("t0", 5e-3), case.get("tr", 30e-3)
    ineg = case.get("ineg", -1.0)
    fc = case.get("fc", 1000.0)
    tstop = case.get("tstop", 80e-3)
    la, ls = case["load_a"], case["load_s"]
    out = [f"* {case['name']}",
           "VPSU psu 0 430",
           "DPSU psu praw DID",
           "RPSU praw raw 0.3",
           f"CRAW raw 0 {C_RAW} IC=430",
           ".model DID D(N=0.05 RS=1m)"]
    if case.get("brake"):
        # raw-rail brake chopper: R_BRAKE switched across the raw rail above V_ON (hardware comparator)
        von, rb = case["brake"]
        out += [f"BBRK raw 0 I=V(raw)/{rb}*0.5*(1+tanh((V(raw)-{von})/0.5))"]
    for tag, c, v0, v1, load in (("a", C_A, va0, va1, la), ("s", C_S, vs0, vs1, ls)):
        kp = 2 * 3.14159 * fc * c
        ki = kp * 2 * 3.14159 * fc / 5
        out += [
            f"VREF{tag} ref{tag} 0 PWL(0 {v0} {t0} {v0} {t0 + tr} {v1})",
            f"C{tag} v{tag} 0 {c} IC={v0}",
            # PI with clamped integrator (anti-windup)
            f"BERR{tag} err{tag} 0 V=V(ref{tag})-V(v{tag})",
            f"GINT{tag} 0 int{tag} VALUE={{{ki}*V(err{tag})}}",
            f"CINT{tag} int{tag} 0 1 IC={case.get('i0_' + tag, 0.2)}",
            f"RINT{tag} int{tag} 0 1G",
            f"BINT{tag}c int{tag} 0 I=(V(int{tag})>1.2 ? (V(int{tag})-1.2)*100 : 0) + (V(int{tag})<{ineg - 0.2} ? (V(int{tag})-{ineg - 0.2})*100 : 0)",
            f"BCMD{tag} cmd{tag} 0 V=min(max({kp}*V(err{tag})+V(int{tag}),{ineg}),1.0)",
            # inner current loop: 5 kHz lag
            f"RLAG{tag} cmd{tag} lag{tag} 1k",
            f"CLAG{tag} lag{tag} 0 {1 / (2 * 3.14159 * 5000 * 1e3)} IC=0.2",
            # duty limit: forward current fades out as Vout approaches D_MAX * V_raw
            f"BCONV{tag} 0 v{tag} I=V(lag{tag}) * (V(lag{tag})>0 ? min(max(({D_MAX}*V(raw)-V(v{tag}))/3,0),1) : 1)",
            f"BIN{tag} raw 0 I=V(lag{tag}) * (V(lag{tag})>0 ? min(max(({D_MAX}*V(raw)-V(v{tag}))/3,0),1) : 1) * V(v{tag})/max(V(raw),1)",
            f"BLOAD{tag} v{tag} 0 I={load}",
        ]
    out += [f".tran 10u {tstop} 0 10u uic",
            ".control", "run",
            "meas tran rawmax MAX v(raw)",
            "meas tran rawmin MIN v(raw)",
            f"meas tran vamax MAX v(va) from={case.get('mfrom', 0)}", f"meas tran vamin MIN v(va) from={case.get('mfrom', 0)}",
            f"meas tran vsmax MAX v(vs) from={case.get('mfrom', 0)}", f"meas tran vsmin MIN v(vs) from={case.get('mfrom', 0)}",
            "meas tran iamax MAX v(laga)", "meas tran iamin MIN v(laga)",
            "meas tran ismax MAX v(lags)", "meas tran ismin MIN v(lags)",
            f"meas tran vaend FIND v(va) AT={tstop}", f"meas tran vsend FIND v(vs) AT={tstop}",
            f"meas tran va_at_mute FIND v(va) AT={t0 + 30e-3}",
            "quit", ".endc", ".end"]
    return "\n".join(out) + "\n"


def run(case):
    with tempfile.NamedTemporaryFile("w", suffix=".cir", delete=False) as f:
        f.write(netlist(case))
        path = f.name
    r = subprocess.run(["ngspice", "-b", path], capture_output=True, text=True)
    os.unlink(path)
    res = {}
    for line in r.stdout.splitlines():
        if "=" in line and line.split("=")[0].strip().isidentifier():
            k, v = line.split("=", 1)
            try:
                res[k.strip()] = float(v.split()[0])
            except ValueError:
                pass
    if not res:
        raise SystemExit(r.stdout[-3000:] + r.stderr[-3000:])
    return res


# tube loads (A): anode idle about 0.2 A at 400 V (resistive model for the ramps), audio:
# class AB supply current with 0.5 A peaks at 2 x 82 Hz; screen 0.1 A average with 0.25 A peaks.
RA = "V(va)/2000"
RS = "V(vs)/20000"
AUD_A = "0.15+0.35*abs(sin(2*3.14159*82*time))"
AUD_S = "0.02+0.23*pow(abs(sin(2*3.14159*82*time)),3)+0.03"
CASES = [
    dict(name="Q-A ramp down 400->200 V (anode) / 390->250 V (screen) in 30 ms, bidirectional", va=(400, 200), vs=(390, 250),
         load_a=RA, load_s=RS, ineg=-1.0),
    dict(name="Q-A' same, ramp in 100 ms, bidirectional", va=(400, 200), vs=(390, 250), load_a=RA, load_s=RS, ineg=-1.0,
         tr=100e-3, tstop=150e-3),
    dict(name="Q-A'' ramp down in 30 ms, bidirectional, with a raw-rail brake (470 ohm above 445 V)", va=(400, 200),
         vs=(390, 250), load_a=RA, load_s=RS, ineg=-1.0, brake=(445, 470)),
    dict(name="Q-B ramp down in 30 ms, forward current only (diode emulation)", va=(400, 200), vs=(390, 250),
         load_a=RA, load_s=RS, ineg=0.0, tstop=200e-3),
    dict(name="Q-C ramp up 200->400 V / 250->390 V in 30 ms", va=(200, 400), vs=(250, 390), load_a=RA, load_s=RS,
         i0_a=0.1, i0_s=0.01),
    dict(name="Q-D audio load at 400 / 390 V, loop crossover 1 kHz", va=(400, 400), vs=(390, 390), load_a=AUD_A,
         load_s=AUD_S, fc=1000.0, mfrom=40e-3, i0_a=0.37, i0_s=0.1),
    dict(name="Q-D' audio load, loop crossover 300 Hz", va=(400, 400), vs=(390, 390), load_a=AUD_A, load_s=AUD_S,
         fc=300.0, mfrom=40e-3, i0_a=0.37, i0_s=0.1),
    dict(name="Q-D'' audio load, raw rail at 420 V (low end), 1 kHz", va=(400, 400), vs=(390, 390), load_a=AUD_A,
         load_s=AUD_S, fc=1000.0, mfrom=40e-3, i0_a=0.37, i0_s=0.1, psu=420),
]


def main():
    rows = []
    for c in CASES:
        if "psu" in c:
            global netlist
            base = netlist
            netlist = lambda case, b=base: b(case).replace("VPSU psu 0 430", f"VPSU psu 0 {case['psu']}").replace("IC=430", f"IC={case['psu']}")
            r = run(c)
            netlist = base
        else:
            r = run(c)
        rows.append((c["name"], r))
        print(c["name"])
        print("   ", {k: round(v, 3) for k, v in r.items()})
    with open(os.path.join(HERE, "results.md"), "w") as f:
        f.write("# Converter averaged-model results (generated by converter_avg.py)\n\n")
        f.write("| Case | raw max / min (V) | V_ANODE max / min (V) | V_SCREEN max / min (V) | I_anode conv max / min (A) | I_screen conv max / min (A) | V_ANODE 30 ms after ramp start | V_A / V_S at end |\n|---|---|---|---|---|---|---|---|\n")
        for n, r in rows:
            f.write(f"| {n} | {r['rawmax']:.1f} / {r['rawmin']:.1f} | {r['vamax']:.1f} / {r['vamin']:.1f} | {r['vsmax']:.1f} / {r['vsmin']:.1f} | "
                    f"{r['iamax']:.2f} / {r['iamin']:.2f} | {r['ismax']:.2f} / {r['ismin']:.2f} | {r['va_at_mute']:.1f} | {r['vaend']:.1f} / {r['vsend']:.1f} |\n")


if __name__ == "__main__":
    main()
