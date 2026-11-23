#!/usr/bin/env python3
"""HV supplies rev 3, review M20: output short and tube arc on V_ANODE and V_SCREEN.

Model (ngspice, both bridges, switching level with ideal switches: the faults last 0.1-10 ms, far
longer than an edge, and what matters is the duty, the inductor and the sense chain):
  raw 420 V (PSU 0.3 ohm + 1 uH, C101, L101, the bridge-local 47 uF); per bridge a half-bridge of
  switches (0.1 ohm) with anti-parallel diodes, 200 ns dead time, 50 kHz centre-aligned PWM; the
  50 mohm low-side emitter shunt; L201 / L203 3 mH with the ETD39 saturation (knee 2.4 A, then
  L0 / 30); C204 / C209 100 uF (ESR 0.1 ohm, 20 nH) returned through the 50 mohm I_C shunt;
  L202 33 uH || 5.6 ohm, 1 uF film, R205 1.0 ohm / R212 2.2 ohm, 220 kohm bleeders; D201 1N5408
  from V_SCREEN to V_ANODE; W04 / W05 0.5 uH to the power amp's 100 nF.
  Sense chain as drawn (sheet 04): 1k into each input of the difference amplifier (gain 10, 1.25 V
  bias), 1 nF across the inputs, MCP6004 (1 MHz, 0.6 V/us, rail to rail 0-3.3 V; its input ESD
  diodes to the rails, the clamp current is reported); LMV339 comparators (1 us response) against
  TH_OC 0.25 V (2.0 A forward: the reading below it) and TH_OCR 2.25 V; latch and the UCC21520 DIS
  (0.2 us). Forward over-current is seen on the low-side shunt, i.e. only while the low side (or
  its diode) carries the inductor current: (1 - D) of each period.
  Controller: before the fault the duty holds the operating point; 60 us after it (one sample +
  the link delay) the voltage loop is at its limit D_MAX = 0.985 (the error is hundreds of volts);
  "firmware stop": the control board stops the PWM 100 us after the fault (it sees V_tab collapse
  and I_C at full scale), unless a hardware trip came first.
Faults at t = 0.2 ms: a hard short (50 mohm) at the V_ANODE or V_SCREEN tab; an arc (20 or 50 V
in 0.1 ohm, one direction, 1 or 10 ms) at the tab (an external flashover: OT centre tap, wiring,
the screen node); a plate-to-cathode arc inside a tube, through the output transformer's half
primary (23.5 ohm DCR, the 475 ohm reflected half load, 16 mH of leakage; the power amp's 100 nF in
front of it): the realistic tube arc.
Variants: as drawn (forward / reverse 2.0 A trips on the low-side shunt only), and proposed (a
comparator on each I_C channel, trip when the electrolytic discharges faster than 2.0 A: reading
below TH_OC).

Limits: ideal switches (no IGBT saturation current: the model lets the current rise as far as the
saturated inductor allows, which is how the IGBT would be destroyed); the arc as a fixed voltage;
the 1N5408 as a standard diode model; resistor energies are adiabatic (all heat stays in the part).

Run: python3 rev3/sim/m20_short_arc.py   (writes m20_results.md, m20_*.png; a few minutes)
"""
import os
from multiprocessing import Pool

import numpy as np

import swmodel as sm

HERE = os.path.dirname(os.path.abspath(__file__))
T_F = 0.2e-3
D_MAX = 0.985


def bridge(k, v_out, i_out, rs, d0, out, trip_ic, d_fault=D_MAX):
    """One bridge, nodes suffixed with k. PWM from the triangle carrier; en{k} = 0 stops it."""
    s = str(k)
    v_uc = v_out + i_out * (rs + 0.1)
    L = [f"* bridge {k}",
         f"Rin{s} uin uin{s} 0.01",
         f"C{s}1 uin{s} c{s}1e 47u IC=420", f"R{s}1e c{s}1e 0 0.3",
         # duty: d0 until 60 us after the fault, then D_MAX
         f"Vd{s} d{s} 0 PWL(0 {d0} {T_F + 60e-6} {d0} {T_F + 61e-6} {d_fault})",
         # high / low commands with 200 ns dead time (0.02 of the triangle at 50 kHz), gated by en
         f"Bhc{s} h{s} 0 V = V(en{s})*(V(d{s}) - V(tri) > 0.02 ? 1 : 0)",
         f"Blc{s} l{s} 0 V = V(en{s})*(V(tri) - V(d{s}) > 0.02 ? 1 : 0)",
         f"Sh{s} uin{s} sw{s} h{s} 0 SWI", f"Dh{s} sw{s} uin{s} DFW",
         f"Sl{s} sw{s} is{s} l{s} 0 SWI", f"Dl{s} is{s} sw{s} DFW",
         f"Rsh{s} is{s} 0 0.05",
         # switch-node capacitance (devices, winding, layout) with a damping resistor: keeps the
         # node defined when both switches and both diodes are off
         f"Csn{s} sw{s} sn{s} 100p", f"Rsn{s} sn{s} 0 5k", f"Rsw{s} sw{s} 0 1Meg",
         sm.inductor_par(f"L{s}", f"sw{s}", f"uc{s}", dcr=1.55, cw=1e-12, i0=i_out),
         f"Vil{s} uc{s} uc{s}b 0",
         f"Cel{s} uc{s}b ce{s} 100u IC={v_uc}", f"Rel{s} ce{s} ce{s}b 0.1", f"Lel{s} ce{s}b ic{s} 20n",
         f"Ric{s} ic{s} 0 0.05",
         f"L2{s} uc{s}b l2{s} 33u IC={i_out}", f"R2{s} l2{s} vo{s} 0.1", f"Rd{s} uc{s}b vo{s} 5.6",
         f"Cf{s} vo{s} cf{s} 1u IC={v_out + i_out * rs}", f"Rcf{s} cf{s} 0 0.02",
         f"Vrs{s} vo{s} vo{s}b 0", f"Rs{s} vo{s}b {out} {rs}",
         f"Rbl{s} {out} 0 220k",
         f"Lw{s} {out} pa{s} 0.5u", f"Rw{s} pa{s} pa{s}b 0.05", f"Cpa{s} pa{s}b 0 100n IC={v_out}",
         f"Iload{s} pa{s}b 0 {i_out}",
         ]
    # sense chain for the low-side shunt (forward / reverse OC) and the I_C shunt
    for tag, node in (("q", f"is{s}"), ("c", f"ic{s}")):
        n = f"{tag}{s}"
        L += [f"Rp{n} {node} ip{n} 1k", f"Rn{n} 0 in{n} 1k", f"Cx{n} ip{n} in{n} 1n",
              f"Rpb{n} ip{n} ibias 10k", f"Rnf{n} in{n} am{n} 10k",
              # input ESD clamps of the MCP6004 (to 0 V and 3.3 V)
              f"Vcl{n}a ip{n} clp{n} 0", f"Dc{n}1 clp{n} vdd DESD", f"Dc{n}2 0 clp{n} DESD",
              # amplifier: ideal difference stage, one pole (1 MHz / 11), slew 0.6 V/us, 0-3.3 V
              f"Bt{n} tg{n} 0 V = 1.25 + 10*(V(ip{n})-V(in{n}))",
              f"Ba{n} 0 am{n} I = 1e-9*max(min(2*3.1416*91e3*(V(tg{n})-V(am{n})), 0.6e6), -0.6e6)",
              f"Ca{n} am{n} 0 1e-9", f"Dao{n}1 am{n} vdd DIDL", f"Dao{n}2 0 am{n} DIDL"]
    # comparators -> trip request (1 us response), forward OC: reading below 0.25 V; reverse: above 2.25 V
    trips = [f"(V(amq{s}) < 0.25)", f"(V(amq{s}) > 2.25)"]
    if trip_ic:
        trips.append(f"(V(amc{s}) < 0.25)")
    L += [f"Btr{s} trq{s} 0 V = ({' || '.join(trips)}) ? 1 : 0",
          f"Rtr{s} trq{s} trd{s} 1k", f"Ctr{s} trd{s} 0 1n"]          # 1 us comparator + logic
    return "\n".join(L)


def netlist(fault, where, trip_ic, va=400.0, ia=0.7, vs=390.0, is_=0.18, t_end=2.2e-3, fw_stop=100e-6):
    d1 = (va + ia * (1.55 + 0.1 + 1.0 + 0.05) + 1.0) / 420.0 + 0.004
    d2 = (vs + is_ * (1.55 + 0.1 + 2.2 + 0.05) + 1.0) / 420.0 + 0.004
    L = ["* M20 short / arc",
         sm.models().split(".subckt")[0],            # diode models only
         ".model SWI SW(VT=0.5 VH=0.01 RON=0.1 ROFF=1e8)",
         ".model DFW D(IS=2e-4 N=2.6 RS=0.045 CJO=50p)",
         ".model DESD D(IS=1e-14 N=1.2 RS=20 CJO=2p)",
         ".model DIDL D(IS=1e-12 N=1 RS=10)",
         ".model D5408 D(IS=5e-9 N=1.8 RS=0.012 CJO=50p BV=1000 IBV=5u)",
         "Vdd vdd 0 3.3", "Vib ibias 0 1.25",
         "Vpsu psu 0 420", "Rpsu psu p1 0.3", "Lpsu p1 bp 1u", "C101 bp c101e 47u IC=420", "R101e c101e 0 0.3",
         "L101 bp uin 33u",
         "Btri tri 0 V = abs(2*(time*50e3 - floor(time*50e3 + 0.5)))",
         bridge(1, va, ia, 1.0, d1, "vanode", trip_ic, D_MAX if fault[0] != "tube_arc" else d1 + 0.004),
         bridge(2, vs, is_, 2.2, d2, "vscreen", trip_ic, D_MAX if fault[0] != "tube_arc" else d2),
         "Vd201 vscreen d201a 0", "D201 d201a vanode D5408",
         # latch: any trip request after 0.5 V sets it (and stays); firmware stop at T_F + fw_stop
         "Blat 0 lat I = (V(trd1) > 0.5 || V(trd2) > 0.5 || V(lat) > 0.5) ? 1e-3*(1.2-V(lat)) : -1e-3*V(lat)",
         "Clat lat 0 10p IC=0", "Rlat lat 0 1G",
         f"Vfw fw 0 PWL(0 1 {T_F + fw_stop} 1 {T_F + fw_stop + 1e-7} 0)",
         # DIS to the drivers: 0.2 us (logic + UCC21520 disable)
         "Ben1 en1r 0 V = (V(lat) < 0.5 && V(fw) > 0.5) ? 1 : 0", "Ren1 en1r en1 200", "Cen1 en1 0 1n IC=1",
         "Ben2 en2r 0 V = (V(lat) < 0.5 && V(fw) > 0.5) ? 1 : 0", "Ren2 en2r en2 200", "Cen2 en2 0 1n IC=1",
         ]
    node = {"anode": "pa1b", "screen": "pa2b", "anode_tab": "vanode", "screen_tab": "vscreen"}[where]
    t_on = T_F
    kind, *par = fault
    if kind == "short":
        L += [f"Sf {node} fz ctlf 0 SWF", "Rf fz 0 0.05",
              f"Vctlf ctlf 0 PWL(0 0 {t_on} 0 {t_on + 10e-9} 1)", ".model SWF SW(VT=0.5 VH=0.01 RON=0.01 ROFF=1e9)"]
    elif kind == "arc":
        varc, t_arc = par
        L += [f"Sf {node} fz ctlf 0 SWF", "Darc fz fz2 DARC", f"Varc fz2 fz3 {varc}", "Rarc fz3 0 0.1",
              f"Vctlf ctlf 0 PWL(0 0 {t_on} 0 {t_on + 10e-9} 1 {t_on + t_arc} 1 {t_on + t_arc + 10e-9} 0)",
              ".model SWF SW(VT=0.5 VH=0.01 RON=0.01 ROFF=1e9)", ".model DARC D(IS=1e-6 N=1 RS=0.01)"]
    elif kind == "tube_arc":
        varc, t_arc = par
        # half primary DCR + leakage + reflected half load, from the supply node to the arcing plate
        L += ["Rot pa1b ot1 23.5", "Lot ot1 ot2 16m", "Rrefl ot2 ot3 475", f"Sf ot3 fz ctlf 0 SWF",
              "Darc fz fz2 DARC", f"Varc fz2 0 {varc}",
              f"Vctlf ctlf 0 PWL(0 0 {t_on} 0 {t_on + 10e-9} 1 {t_on + t_arc} 1 {t_on + t_arc + 10e-9} 0)",
              ".model SWF SW(VT=0.5 VH=0.01 RON=0.01 ROFF=1e9)", ".model DARC D(IS=1e-6 N=1 RS=0.01)"]
    return "\n".join(L), t_end


OUT = ["v(vanode)", "v(vscreen)", "i(Vil1)", "i(Vil2)", "i(Vrs1)", "i(Vrs2)", "i(Vd201)", "v(is1)", "v(is2)",
       "v(ic1)", "v(ic2)", "i(Vclq1a)", "i(Vclc1a)", "i(Vclq2a)", "i(Vclc2a)", "v(amq1)", "v(amc1)", "v(lat)",
       "v(en1)", "v(uin)", "v(uc1)", "v(uc2)"]


def run_case(args):
    name, fault, where, trip_ic, t_end = args
    # the firmware stops the PWM on a collapsed output (100 us); a tube arc through the output
    # transformer is only a load step for the loop: no firmware stop
    net, t_end = netlist(fault, where, trip_ic, t_end=t_end, fw_stop=100e-6 if fault[0] != "tube_arc" else 1.0)
    r = sm.run(net, OUT, t_end, "20n", "50n", uic=True, opts="")
    t = r["t"]
    m = t >= T_F - 1e-6

    def i2t(x):
        return np.trapezoid(x[m] ** 2, t[m])

    lat = r["v(lat)"]
    tt = t[np.argmax(lat > 0.5)] - T_F if (lat > 0.5).any() else np.nan
    off = (r["v(en1)"] < 0.5) & (t > T_F)
    en_off = t[np.argmax(off)] - T_F if off.any() else np.nan
    res = dict(
        trip_us=tt * 1e6, stop_us=en_off * 1e6,
        il1=np.abs(r["i(Vil1)"][m]).max(), il2=np.abs(r["i(Vil2)"][m]).max(),
        r205_pk=np.abs(r["i(Vrs1)"][m]).max(), r205_e=i2t(r["i(Vrs1)"]) * 1.0, r205_i2t=i2t(r["i(Vrs1)"]),
        r212_pk=np.abs(r["i(Vrs2)"][m]).max(), r212_e=i2t(r["i(Vrs2)"]) * 2.2, r212_i2t=i2t(r["i(Vrs2)"]),
        d201_pk=np.abs(r["i(Vd201)"][m]).max(), d201_i2t=i2t(r["i(Vd201)"]),
        shq1_pk=np.abs(r["v(is1)"][m]).max() / 0.05, shc1_pk=np.abs(r["v(ic1)"][m]).max() / 0.05,
        shc2_pk=np.abs(r["v(ic2)"][m]).max() / 0.05,
        shc1_e=np.trapezoid((r["v(ic1)"][m] / 0.05) ** 2, t[m]) * 0.05,
        shc2_e=np.trapezoid((r["v(ic2)"][m] / 0.05) ** 2, t[m]) * 0.05,
        clamp_ma=1e3 * max(np.abs(r[k][m]).max() for k in ("i(Vclq1a)", "i(Vclc1a)", "i(Vclq2a)", "i(Vclc2a)")),
        raw_max=r["v(uin)"][m].max(), va_min=r["v(vanode)"][m].min(), vs_min=r["v(vscreen)"][m].min(),
    )
    return name, res, r


def cases():
    out = []
    for trip_ic in (False, True):
        tag = "proposed (I_C trip)" if trip_ic else "as drawn"
        out += [
            (f"V_ANODE tab hard short, {tag}", ("short",), "anode_tab", trip_ic, 2.2e-3),
            (f"V_ANODE arc 20 V / 1 ms at the supply end, {tag}", ("arc", 20.0, 1e-3), "anode", trip_ic, 2.2e-3),
            (f"V_ANODE arc 50 V / 10 ms at the supply end, {tag}", ("arc", 50.0, 10e-3), "anode", trip_ic, 10.5e-3),
            (f"V_SCREEN tab hard short, {tag}", ("short",), "screen_tab", trip_ic, 2.2e-3),
            (f"V_SCREEN arc 30 V / 10 ms at the supply end, {tag}", ("arc", 30.0, 10e-3), "screen", trip_ic, 10.5e-3),
        ]
    out += [("plate-cathode arc inside a tube, 30 V / 10 ms (through the OT), as drawn", ("tube_arc", 30.0, 10e-3), "anode", False, 10.5e-3)]
    return out


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    with Pool() as pool:
        res = pool.map(run_case, cases())
    L = ["# M20: output short and tube arc (generated by m20_short_arc.py)", "",
         __doc__.split("\n\n")[1], "", __doc__.split("\n\n")[2], "", __doc__.split("\n\n")[3], "",
         "| Case | trip after (us) | PWM stopped after (us) | L201 / L203 peak (A) | R205 peak (A) / energy (J) | R212 peak (A) / energy (J) | "
         "D201 peak (A) / I2t (A2s) | shunts peak: low side 1 / I_C 1 / I_C 2 (A) | I_C shunt energy 1 / 2 (mJ) | "
         "amp input clamp current max (mA) | raw max (V) | V_ANODE / V_SCREEN min (V) |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, a, r in res:
        L.append(f"| {n} | {a['trip_us']:.1f} | {a['stop_us']:.1f} | {a['il1']:.2f} / {a['il2']:.2f} | "
                 f"{a['r205_pk']:.0f} / {a['r205_e']:.2f} | {a['r212_pk']:.0f} / {a['r212_e']:.2f} | "
                 f"{a['d201_pk']:.0f} / {a['d201_i2t']:.2f} | {a['shq1_pk']:.1f} / {a['shc1_pk']:.0f} / {a['shc2_pk']:.0f} | "
                 f"{a['shc1_e'] * 1e3:.0f} / {a['shc2_e'] * 1e3:.0f} | {a['clamp_ma']:.1f} | {a['raw_max']:.0f} | "
                 f"{a['va_min']:.0f} / {a['vs_min']:.0f} |")
    L += ["", "Ratings: ULW2 short-pulse energy about 2.5 J at 1-2.2 ohm (datasheet graph, single pulse, dR < 5 %); "
          "ULW3 / ULW4 about 9 / 7 J; ULW5 about 19 J at 1 ohm, 13 J at 2.2 ohm. 1N5408: IFSM 200 A (8.3 ms half sine), "
          "I2t = 200^2 x 0.0083 / 2 = 166 A2s. IKP08N65F5: ICpuls 24 A, no short-circuit rating. MCP6004 input "
          "current absolute maximum +-2 mA (datasheet; ESD diodes)."]
    # plot the anode short, as drawn vs proposed
    fig, ax = plt.subplots(3, 1, figsize=(8, 7), sharex=True)
    for n, a, r in res:
        if n.startswith("V_ANODE tab hard short"):
            t = (r["t"] - T_F) * 1e6
            ax[0].plot(t, r["i(Vil1)"], lw=0.8, label=n.split(", ")[1])
            ax[1].plot(t, r["i(Vrs1)"], lw=0.8, label=n.split(", ")[1])
            ax[2].plot(t, r["v(vanode)"], lw=0.8, label="V_ANODE " + n.split(", ")[1])
            ax[2].plot(t, r["v(vscreen)"], lw=0.8, ls="--", label="V_SCREEN " + n.split(", ")[1])
    ax[0].set_ylabel("L201 current (A)"); ax[1].set_ylabel("R205 current (A)"); ax[2].set_ylabel("V")
    ax[2].set_xlabel("us after the short"); ax[0].legend(fontsize=7); ax[2].legend(fontsize=7)
    ax[0].set_xlim(-20, 400)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "m20_anode_short.png"), dpi=110); plt.close(fig)
    open(os.path.join(HERE, "m20_results.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
