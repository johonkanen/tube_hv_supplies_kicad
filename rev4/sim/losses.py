#!/usr/bin/env python3
"""HV supplies rev 4: power-loss and thermal check of the two hard-switched synchronous bucks.

Run from the repo root:  python3 rev4/sim/losses.py   -> rev4/sim/losses_results.md, losses_tj.png

Analytical, per-period model (no SPICE). Each 50 kHz period of the inductor current is a symmetric
triangle (centre-aligned PWM, CCM always, synchronous drive). The current is assigned to the four
conduction paths by interval and sign:
    on-interval  (HS gated): i > 0 -> HS IGBT,  i < 0 -> HS diode
    off-interval (LS gated): i > 0 -> LS diode, i < 0 -> LS IGBT
and the two edges are classified by the sign of the current at the edge:
    edge 1 (HS turn-on, i1 = i_min): i1 > 0 -> HS hard turn-on + LS diode recovery
                                     i1 < 0 -> LS IGBT hard turn-off, HS turns on after the node has
                                               swung (ZVS, partial if |i1| x t_dead < Q_node)
    edge 2 (HS turn-off, i2 = i_max): i2 > 0 -> HS IGBT hard turn-off, LS turns on (ZVS / partial)
                                     i2 < 0 -> LS hard turn-on + HS diode recovery (sinking mode)

Device data: Infineon IKP08N65F5, datasheet Rev 2.1 as transcribed in rev3/sim/swmodel.py (the PDF
was not re-fetched for this run): VCEsat / VF curve fits (swmodel HOT / COLD parameter sets, linear in
Tj between 25 and 125 C), diode Qrr 0.19 / 0.27 uC at 2 / 4 A (150 C), 0.10 / 0.14 uC (25 C),
Eon 60 / 100 uJ, Eoff 20 / 30 uJ at 2 / 4 A (150 C, 48 ohm, 400 V), QG 22 nC (15 V), RthJC IGBT 2.2 K/W.
Diode RthJC 3.5 K/W is an ESTIMATE (not in the rev3 transcription).

Turn-on energy model ("M15-calibrated", the baseline):
    E_on(I) = Qoss_node x Vin + k_rr x Qrr(I, Tj) x Vin + 0.5 x Vin x I x t_ri
with Qoss_node = 15 nC (rev3 r5_devices), k_rr = 0.85, t_ri = 10 ns (16.5 ohm gate loop). k_rr was chosen
so that the model reproduces rev3 M15's simulated Q201 losses (3 mH, 420 V, 125 C; checked below).
Qrr(I, Tj) is the rev3 power law (Qrr ~ I^0.51 through the 2 / 4 A points), interpolated in Tj.
Alternatives printed for the dominant device: "datasheet" (Eon = 20 + 20 uJ/A x I, the 48-ohm curve
extrapolated below 2 A, Vin-scaled) and "Qrr linear" (0.11 uC + 0.04 uC/A floor, rev3's pessimistic law).
Turn-off: Eoff(I) = 10 uJ/A x I below 2 A (M15 model at 16.5 ohm), 10 + 5 uJ/A x I above (datasheet).
Diode recovery loss in the recovering diode: E_rec = 0.15 x Qrr x Vin (soft Rapid diode, ESTIMATE),
plus 5 uJ per hard edge in the passive device (rev3 M15 showed ~0.25 W in the idle low side at every
operating point, even at zero current: ringing / capacitive loss; carried as a floor).
"""
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_MD = os.path.join(HERE, "losses_results.md")
OUT_PNG = os.path.join(HERE, "losses_tj.png")

F_SW = 50e3
T_DEAD = 200e-9
L_MAIN = 2.0e-3

# ---------------------------------------------------------------- device (IKP08N65F5)
VT = lambda tj: 8.617e-5 * (tj + 273.15)
HOT = dict(tj=125.0, rc=0.10, js=2.0e-6, jn=2.3, dis=2.0e-4, dn=2.6, drs=0.045)
COLD = dict(tj=25.0, rc=0.07, js=1.0e-7, jn=2.0, dis=2.0e-6, dn=2.0, drs=0.06)
RTH_JC_IGBT = 2.2
RTH_JC_DIODE = 3.5      # estimate
QOSS_NODE = 15e-9       # switch-node charge per hard edge (both devices' output charge, rev3 r5_devices)
K_RR = 0.85
T_RI = 10e-9
K_REC = 0.15
E_PASSIVE = 5e-6
QG_12V = 18e-9          # gate charge at 0..12 V (22 nC at 15 V, scaled; estimate)
C_GE = 1e-9             # optional G-E capacitor (rev3 Miller fix)


def _lerp(a, b, tj):
    w = np.clip((tj - 25.0) / 100.0, 0.0, 1.5)
    return a + (b - a) * w


def vce_sat(i, tj, vg_penalty=0.0):
    """IGBT on-state voltage (V) at current i >= 0: PNP knee (exponential) + series R (swmodel fit),
    plus a small channel penalty for gate drives below the datasheet's 15 V."""
    i = np.maximum(i, 1e-6)
    v_h = HOT["jn"] * VT(125) * np.log(i / HOT["js"]) + HOT["rc"] * i
    v_c = COLD["jn"] * VT(25) * np.log(i / COLD["js"]) + COLD["rc"] * i
    return _lerp(v_c, v_h, tj) + vg_penalty


def vf_diode(i, tj):
    i = np.maximum(i, 1e-6)
    v_h = HOT["dn"] * VT(125) * np.log(i / HOT["dis"]) + HOT["drs"] * i
    v_c = COLD["dn"] * VT(25) * np.log(i / COLD["dis"]) + COLD["drs"] * i
    return _lerp(v_c, v_h, tj)


def qrr(i, tj, law="power"):
    i = abs(i)
    w = np.clip((tj - 25.0) / 125.0, 0.0, 1.2)
    if law == "linear":
        qc, qh = 0.06e-6 + 0.02e-6 * i, 0.11e-6 + 0.04e-6 * i
        return qc + (qh - qc) * w
    q1h, q2h, q1c, q2c = 0.19e-6, 0.27e-6, 0.10e-6, 0.14e-6
    qh = q1h * (i / 2.0) ** (np.log(q2h / q1h) / np.log(2))
    qc = q1c * (i / 2.0) ** (np.log(q2c / q1c) / np.log(2))
    # datasheet hot values are at 150 C: interpolate 25..150 C
    w = np.clip((tj - 25.0) / 125.0, 0.0, 1.2)
    return qc + (qh - qc) * w


def e_on(i, vin, tj, law="power", model="m15"):
    if model == "datasheet":
        return (20e-6 + 20e-6 * i) * vin / 400.0
    return QOSS_NODE * vin + K_RR * qrr(i, tj, law) * vin + 0.5 * vin * i * T_RI


def e_off(i, vin):
    i = abs(i)
    e = 10e-6 * i if i < 2 else 10e-6 + 5e-6 * i
    return e * vin / 400.0


def zvs_residual(i_abs, vin):
    """Fraction of Vin left on the incoming device after the dead time (0 = full ZVS)."""
    swing = i_abs * T_DEAD / (QOSS_NODE * 2)   # node charge Qoss of both devices ~ 2 x 15 nC
    return max(0.0, 1.0 - swing)


# ---------------------------------------------------------------- bridge loss
def bridge(vin, vout, iout, tj, law="power", model="m15", vg_hs=11.0, vg_ls=12.0, n=4000):
    """Per-device losses (W) of one bridge. tj = dict(HS=..., LS=...) junction temperatures."""
    d = vout / vin
    di = vin * d * (1 - d) / (L_MAIN * F_SW)
    i1, i2 = iout - di / 2, iout + di / 2
    T = 1 / F_SW
    # on-interval: current rises i1 -> i2 ; off-interval: falls i2 -> i1
    t_on = np.linspace(0, 1, n)
    ion = i1 + (i2 - i1) * t_on
    ioff = i2 + (i1 - i2) * t_on
    pen = lambda vg: max(0.0, (15.0 - vg) * 0.012)   # ~0.05 V at 11 V, sub-1 A (estimate)
    tH, tL = tj["HS"], tj["LS"]
    P = {k: dict(cond_igbt=0.0, cond_diode=0.0, on=0.0, off=0.0, rec=0.0) for k in ("HS", "LS")}
    # conduction
    pos, neg = ion > 0, ion < 0
    P["HS"]["cond_igbt"] = d * np.mean(np.where(pos, ion * vce_sat(ion, tH, pen(vg_hs)), 0))
    P["HS"]["cond_diode"] = d * np.mean(np.where(neg, -ion * vf_diode(-ion, tH), 0))
    pos, neg = ioff > 0, ioff < 0
    P["LS"]["cond_diode"] = (1 - d) * np.mean(np.where(pos, ioff * vf_diode(ioff, tL), 0))
    P["LS"]["cond_igbt"] = (1 - d) * np.mean(np.where(neg, -ioff * vce_sat(-ioff, tL, pen(vg_ls)), 0))
    edges = []
    # edge 1: HS turn-on at i1
    if i1 > 0:
        P["HS"]["on"] += e_on(i1, vin, tH, law, model) * F_SW
        P["LS"]["rec"] += (K_REC * qrr(i1, tL, law) * vin + E_PASSIVE) * F_SW
        edges.append(f"HS hard on @{i1:+.2f} A")
    else:
        P["LS"]["off"] += e_off(-i1, vin) * F_SW
        r = zvs_residual(-i1, vin)
        P["HS"]["on"] += QOSS_NODE * vin * r ** 2 * F_SW
        edges.append(f"LS hard off @{i1:+.2f} A, HS {'ZVS' if r == 0 else f'partial ZVS ({r:.0%} V left)'}")
    # edge 2: HS turn-off at i2
    if i2 > 0:
        P["HS"]["off"] += e_off(i2, vin) * F_SW
        r = zvs_residual(i2, vin)
        P["LS"]["on"] += QOSS_NODE * vin * r ** 2 * F_SW
        edges.append(f"HS hard off @{i2:+.2f} A, LS {'ZVS' if r == 0 else f'partial ({r:.0%})'}")
    else:
        P["LS"]["on"] += e_on(-i2, vin, tL, law, model) * F_SW
        P["HS"]["rec"] += (K_REC * qrr(-i2, tH, law) * vin + E_PASSIVE) * F_SW
        edges.append(f"LS hard on @{i2:+.2f} A")
    # RMS for passives
    irms_off2 = (1 - d) * np.mean(ioff ** 2)
    i_ripple_rms = di / np.sqrt(12)
    irms_L = np.sqrt(iout ** 2 + i_ripple_rms ** 2)
    for k in P:
        P[k]["igbt"] = P[k]["cond_igbt"] + P[k]["on"] + P[k]["off"]
        P[k]["diode"] = P[k]["cond_diode"] + P[k]["rec"]
        P[k]["sw"] = P[k]["on"] + P[k]["off"] + P[k]["rec"]
        P[k]["cond"] = P[k]["cond_igbt"] + P[k]["cond_diode"]
        P[k]["tot"] = P[k]["igbt"] + P[k]["diode"]
    return dict(P=P, d=d, di=di, i1=i1, i2=i2, edges=edges, irms_off2=irms_off2,
                i_ripple_rms=i_ripple_rms, irms_L=irms_L)


def thermal(vin, vout, iout, t_wall, r_cw, **kw):
    """Iterate Tj. Returns bridge result plus Tj per device (IGBT and diode die, shared tab)."""
    tj = dict(HS=100.0, LS=100.0)
    for _ in range(30):
        b = bridge(vin, vout, iout, tj, **kw)
        new = {}
        tjd = {}
        for k in ("HS", "LS"):
            p = b["P"][k]
            tc = t_wall + p["tot"] * r_cw
            new[k] = tc + p["igbt"] * RTH_JC_IGBT
            tjd[k] = (tc, new[k], tc + p["diode"] * RTH_JC_DIODE)
        if max(abs(new[k] - tj[k]) for k in tj) < 0.01:
            break
        tj = {k: 0.5 * tj[k] + 0.5 * new[k] for k in tj}
    b["T"] = tjd
    return b


# ---------------------------------------------------------------- inductor (2 mH Fe-Si-Al toroid)
# Core assumed: Kool-Mu-class 27.0 OD x 14.7 ID x 11.2 HT mm (Magnetics 77071 size); 3 layers of 0.8 mm
# wire add ~2.6 mm per side -> ~32 x 16.4 mm wound, matching the part. Ae 65.6 mm2, le 63.5 mm,
# Ve 4.17 cm3. Permeability 90 assumed (60..125 bracket): AL = mu0 mu Ae / le.
CORE = dict(Ae=65.6e-6, le=63.5e-3, Ve=4.17e-6, OD=27.0e-3, ID=14.7e-3, HT=11.2e-3)
MU_CASES = (60, 90, 125)
MU_BASE = 90
D_WIRE = 0.8e-3
# Steinmetz for Kool-Mu-type sendust (ESTIMATE, fitted to ~550 mW/cm3 at 100 kHz / 0.1 T peak,
# alpha 1.46, beta 2.0, the exponents Magnetics publishes for Kool Mu): Pv = k f_kHz^a Bpk^b mW/cm3
SM_K, SM_A, SM_B = 66.0, 1.46, 2.0


def inductor_design(mu):
    al = 4e-7 * np.pi * mu * CORE["Ae"] / CORE["le"]
    N = np.sqrt(L_MAIN / al)
    build = 3 * 0.86e-3 * 0.5 + 0.3e-3      # average winding build
    mlt = 2 * ((CORE["OD"] - CORE["ID"]) / 2 + CORE["HT"]) + 2 * np.pi * build * 1.6
    length = N * mlt
    r20 = length * 1.724e-8 / (np.pi / 4 * D_WIRE ** 2)
    fill = N * np.pi / 4 * (0.86e-3) ** 2 / (np.pi / 4 * CORE["ID"] ** 2)
    return dict(mu=mu, AL=al, N=N, mlt=mlt, length=length, r20=r20, fill=fill)


def dowell_fr(f, tw, layers=2.0, eta=0.8):
    delta = 0.066 / np.sqrt(f) * np.sqrt((1 + 0.0039 * (tw - 20)))  # m
    x = (np.pi / 4) ** 0.75 * D_WIRE / delta * np.sqrt(eta)
    a = (np.sinh(2 * x) + np.sin(2 * x)) / (np.cosh(2 * x) - np.cos(2 * x))
    b = (np.sinh(x) - np.sin(x)) / (np.cosh(x) + np.cos(x))
    return x * (a + 2 * (layers ** 2 - 1) / 3 * b)


def igse_pv(dB_pp, d, f):
    """iGSE for a triangular flux with duty d; returns mW/cm3 (Steinmetz above, B peak in T)."""
    a, bexp = SM_A, SM_B
    th = np.linspace(0, 2 * np.pi, 20001)
    ki = SM_K * (1e-3) ** a / ((2 * np.pi) ** (a - 1) * np.trapezoid(np.abs(np.cos(th)) ** a * 2 ** (bexp - a), th))
    # f in Hz now (k scaled from kHz); |dB/dt| = dB/(dT) on each slope
    T = 1 / f
    pv = ki * dB_pp ** (bexp - a) * (1 / T) * ((dB_pp / (d * T)) ** a * d * T + (dB_pp / ((1 - d) * T)) ** a * (1 - d) * T)
    return pv


def inductor_loss(b, t_amb, mu=MU_BASE):
    ind = inductor_design(mu)
    area = (np.pi * 32e-3 * 16.4e-3 + 2 * np.pi / 4 * ((32e-3) ** 2 - (9.5e-3) ** 2))
    h = 13.0   # W/m2K natural convection + radiation, small horizontal cylinder (ESTIMATE)
    r_th = 1 / (h * area)
    tw = t_amb + 30
    for _ in range(20):
        r = ind["r20"] * (1 + 0.0039 * (tw - 20))
        p_dc = b["irms_L"] ** 2 * r - b["i_ripple_rms"] ** 2 * r
        p_ac = b["i_ripple_rms"] ** 2 * r * dowell_fr(F_SW, tw)
        dB = L_MAIN * b["di"] / (ind["N"] * CORE["Ae"])
        p_core = igse_pv(dB, b["d"], F_SW) * CORE["Ve"] * 1e6 * 1e-3
        tot = p_dc + p_ac + p_core
        tw_new = t_amb + tot * r_th
        if abs(tw_new - tw) < 0.01:
            break
        tw = tw_new
    return dict(ind=ind, p_dc=p_dc, p_ac=p_ac, p_core=p_core, dB=dB, tot=tot, t=tw_new, r_th=r_th,
                r_hot=r, fr=dowell_fr(F_SW, tw))


# ---------------------------------------------------------------- operating points
VIN_NOM, VIN_MAX = 425.0, 430.0
R_SHUNT = 0.05
R_L2 = 0.15         # 100 uH second-stage inductor DCR (ESTIMATE)
R_BLEED = 220e3     # per output, as rev3 M15 (assumption; rev4 value not chosen)

POINTS = [
    # name, bridge, vout, iout
    ("A1 V_ANODE 400 V / 0.8 A (peak)", 1, 400, 0.80),
    ("A2 V_ANODE 400 V / 0.7 A (overdrive, minutes)", 1, 400, 0.70),
    ("A3 V_ANODE 400 V / 0.6 A (continuous design)", 1, 400, 0.60),
    ("A4 V_ANODE 400 V / 0.3 A (idle)", 1, 400, 0.30),
    ("A5 V_ANODE 300 V / 0.5 A", 1, 300, 0.50),
    ("A6 V_ANODE 200 V / 0.35 A", 1, 200, 0.35),
    ("A7 V_ANODE 150 V / 0.2 A", 1, 150, 0.20),
    ("A8 V_ANODE 400 V / 0 A", 1, 400, 0.0),
    ("R1 ramp-down 300 V / -0.8 A (<= 1 s)", 1, 300, -0.80),
    ("S1 V_SCREEN 390 V / 0.25 A (peak)", 2, 390, 0.25),
    ("S2 V_SCREEN 390 V / 0.18 A (overdrive)", 2, 390, 0.18),
    ("S3 V_SCREEN 290 V / 0.12 A", 2, 290, 0.12),
    ("S4 V_SCREEN 150 V / 0.05 A", 2, 150, 0.05),
    ("S5 V_SCREEN 390 V / 0.03 A (idle, estimate)", 2, 390, 0.03),
]

# Average-load model (ESTIMATE): 100 W amp, peak-to-average 6 -> 17 W average audio.
#   model U (user's): extra supply power = 17 W / 0.65 above idle -> +65 mA at 400 V
#   model B (class-B amplitude): the extra current is proportional to the signal amplitude:
#           (0.7 - 0.3 A) x sqrt(1/6) x 0.85 (mean|x| / rms of music vs a sine) = +0.14 A
I_IDLE_A, I_FULL_A = 0.30, 0.70
I_IDLE_S, I_FULL_S = 0.03, 0.18
avg_U_a = I_IDLE_A + 17.0 / 0.65 / 400.0
avg_B_a = I_IDLE_A + (I_FULL_A - I_IDLE_A) * np.sqrt(1 / 6) * 0.85
avg_B_s = I_IDLE_S + (I_FULL_S - I_IDLE_S) * np.sqrt(1 / 6) * 0.85


def board_case(name, va, ia, vs, is_, vin, t_wall, r_cw, t_amb, law="power", model="m15"):
    b1 = thermal(vin, va, ia, t_wall, r_cw, law=law, model=model)
    b2 = thermal(vin, vs, is_, t_wall, r_cw, law=law, model=model)
    l1, l2 = inductor_loss(b1, t_amb), inductor_loss(b2, t_amb)
    sh = sum(R_SHUNT * (b["irms_off2"] + b["i_ripple_rms"] ** 2) for b in (b1, b2))
    l2loss = R_L2 * (ia ** 2 + is_ ** 2)
    bleed = va ** 2 / R_BLEED + vs ** 2 / R_BLEED
    caps = 0.5 * (b1["i_ripple_rms"] ** 2 + b2["i_ripple_rms"] ** 2)  # first-stage el+film, ~0.5 ohm eff. ESR
    dev = sum(b["P"][k]["tot"] for b in (b1, b2) for k in ("HS", "LS"))
    return dict(name=name, b1=b1, b2=b2, l1=l1, l2=l2, shunts=sh, l2loss=l2loss, bleed=bleed, caps=caps,
                dev=dev, total=dev + l1["tot"] + l2["tot"] + sh + l2loss + bleed + caps,
                pout=va * ia + vs * is_)


# ---------------------------------------------------------------- rev3 cross-check (3 mH, 420 V, 125 C)
def rev3_check():
    global L_MAIN
    keep = L_MAIN
    L_MAIN = 3e-3
    rows = []
    m15 = {"A 400 V / 0.70 A": (400, 0.70, 3.54, 0.61), "C 400 V / 0.30 A": (400, 0.30, 1.57, 0.20),
           "L 390 V / 0.18 A": (390, 0.18, 1.10, 0.10), "F 200 V / 0.35 A": (200, 0.35, 0.66, 0.12)}
    for k, (v, i, ptot, pcond) in m15.items():
        b = bridge(420, v, i, dict(HS=125, LS=125))
        bl = bridge(420, v, i, dict(HS=125, LS=125), law="linear")
        bd = bridge(420, v, i, dict(HS=125, LS=125), model="datasheet")
        rows.append((k, b["i1"], b["P"]["HS"]["tot"], b["P"]["HS"]["cond"], bl["P"]["HS"]["tot"],
                     bd["P"]["HS"]["tot"], ptot, pcond))
    L_MAIN = keep
    return rows


# ---------------------------------------------------------------- report
def f2(x):
    return f"{x:.2f}"


def main():
    L = []
    w = L.append
    w("# rev4 power-loss and thermal check (generated by losses.py)\n")
    w("Analytical per-period model, IKP08N65F5 data as transcribed in rev3/sim/swmodel.py (datasheet Rev 2.1; "
      "not re-fetched). 50 kHz, hard switched, synchronous CCM, dead time 200 ns, L = 2 mH, gate 15 ohm on "
      "(16.5 ohm loop), high side 11 V / low side 12 V. See the module docstring for every model term. "
      "**Estimates:** diode RthJC 3.5 K/W, the Steinmetz fit of the Fe-Si-Al core, the toroid's convection, "
      "the 100 uH DCR, the bleeders (220 kohm as rev3), and the whole low-current switching-energy model "
      "(no datasheet data below 2 A).\n")

    # rev3 check
    w("## 1. Cross-check against rev3 M15 (3 mH, 420 V, Tj 125 C, ngspice)\n")
    w("| M15 case | i at HS turn-on (A) | this model HS total / cond (W) | Qrr linear (W) | datasheet-curve Eon (W) | M15 sim total / cond (W) |")
    w("|---|---|---|---|---|---|")
    for r in rev3_check():
        w(f"| {r[0]} | {r[1]:+.2f} | {f2(r[2])} / {f2(r[3])} | {f2(r[4])} | {f2(r[5])} | {f2(r[6])} / {f2(r[7])} |")
    w("\nThe baseline reproduces M15 at full load (-8 %) and is 15-40 % above it at the light-load points "
      "(where the turn-on current is near zero and the Qrr extrapolation and the Qoss / passive-floor terms dominate), "
      "so it is on the safe side there. The datasheet-curve column (Eon 20 + 20 uJ/A, no Qrr collapse at low current) "
      "is pessimistic at light load and optimistic at full load; the Qrr-linear column is the upper bound.\n")

    # per point table
    for t_wall, r_cw, tag in ((80.0, 1.0, "wall 80 C, Rth(case-wall) 1.0 K/W"),):
        w(f"## 2. Operating points (Vin 425 V, {tag}; Tj iterated)\n")
        w("| Point | D | dI p-p (A) | i_min / i_max (A) | edges | device | cond (W) | turn-on (W) | turn-off (W) | recovery (W) | total (W) | Tcase / Tj IGBT / Tj diode (C) |")
        w("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for name, br, v, i in POINTS:
            b = thermal(VIN_NOM, v, i, t_wall, r_cw)
            for k in ("HS", "LS"):
                p = b["P"][k]
                dev = f"Q{k[0]}{br}"
                tc, tji, tjd = b["T"][k]
                head = (f"| {name} | {b['d']:.3f} | {b['di']:.2f} | {b['i1']:+.2f} / {b['i2']:+.2f} | "
                        f"{'; '.join(b['edges'])} |") if k == "HS" else "| | | | | |"
                w(f"{head} {dev} | {f2(p['cond'])} | {f2(p['on'])} | {f2(p['off'])} | {f2(p['rec'])} | "
                  f"**{f2(p['tot'])}** | {tc:.0f} / {tji:.0f} / {tjd:.0f} |")
        w("\nR1 (ramp-down) lasts <= 1 s: the TO-220's Zth(j-c) is near RthJC by then but the case / pad / wall barely "
          "warm, so the Tj shown (steady state) is pessimistic for the case part.\n")

    # sensitivity of the dominant device
    w("## 3. Dominant device QH1 at 400 V / 0.7 A: model spread and Tj vs mounting\n")
    w("| Switching model | QH1 total (W) at Tj ~ iterated, wall 80 C, 1.0 K/W | Tj (C) |")
    w("|---|---|---|")
    for lab, kw in (("baseline (M15-calibrated, Qrr power law)", {}),
                    ("pessimistic (Qrr linear with 0.11 uC floor)", dict(law="linear")),
                    ("optimistic (datasheet Eon curve extrapolated)", dict(model="datasheet"))):
        b = thermal(VIN_NOM, 400, 0.7, 80, 1.0, **kw)
        w(f"| {lab} | {f2(b['P']['HS']['tot'])} | {b['T']['HS'][1]:.0f} |")
    w("\nTj of QH1 (IGBT die, baseline model, Vin 430 V) against wall temperature and Rth(case-wall):\n")
    rcws = (0.5, 1.0, 1.5, 2.5)
    walls = (70, 80, 85, 95)
    w("| load | wall (C) | " + " | ".join(f"Rcw {r} K/W" for r in rcws) + " |")
    w("|---|---|" + "---|" * len(rcws))
    grid = {}
    for lab, ia in ((f"avg (class-B model) {avg_B_a:.2f} A", avg_B_a), ("sustained 0.7 A", 0.7), ("peak 0.8 A", 0.8)):
        for tw in walls:
            vals = []
            for r in rcws:
                b = thermal(VIN_MAX, 400, ia, tw, r)
                vals.append(b["T"]["HS"][1])
                grid[(lab, tw, r)] = b["T"]["HS"][1]
            w(f"| {lab} | {tw} | " + " | ".join(f"{x:.0f}" for x in vals) + " |")
    w("\nRequired Rth(case-wall) for Tj(QH1) <= 125 C (baseline / pessimistic Qrr law), Vin 430 V:\n")
    w("| load | wall 70 C | wall 80 C | wall 85 C |")
    w("|---|---|---|---|")
    for lab, ia in (("avg (class-B)", avg_B_a), ("sustained 0.7 A", 0.7), ("peak 0.8 A", 0.8)):
        cells = []
        for tw in (70, 80, 85):
            out = []
            for kw in ({}, dict(law="linear")):
                rr = np.linspace(0.0, 40.0, 401)
                ok = [r for r in rr if thermal(VIN_MAX, 400, ia, tw, r, **kw)["T"]["HS"][1] <= 125.0]
                out.append(f"{max(ok):.1f}" if ok else "none")
            cells.append(" / ".join(out) + " K/W")
        w(f"| {lab} | " + " | ".join(cells) + " |")

    # board cases
    w("\n## 4. Board cases\n")
    w(f"Average-load models (ESTIMATES): 17 W audio (100 W / PAR 6). Model U (user): idle + 17 W / 0.65 / 400 V = "
      f"**{avg_U_a:.3f} A**. Model B (class-B: extra current proportional to amplitude): idle + 0.4 A x sqrt(1/6) x 0.85 = "
      f"**{avg_B_a:.3f} A**; screen 0.03 A idle + 0.15 A x 0.35 = **{avg_B_s:.3f} A**. Model B is used as the average case "
      "(higher, so conservative).\n")
    cases = [
        board_case("Idle: 400 V / 0.30 A + 390 V / 0.03 A, wall 75 C, 1.0 K/W", 400, 0.30, 390, 0.03, VIN_NOM, 75, 1.0, 70),
        board_case(f"Average (model U): 400 V / {avg_U_a:.2f} A + 390 V / 0.06 A, wall 75 C, 1.0 K/W", 400, avg_U_a, 390, 0.06,
                   VIN_NOM, 75, 1.0, 70),
        board_case(f"Average (model B): 400 V / {avg_B_a:.2f} A + 390 V / {avg_B_s:.2f} A, wall 80 C, 1.0 K/W", 400, avg_B_a,
                   390, avg_B_s, VIN_NOM, 80, 1.0, 70),
        board_case("Sustained worst: 400 V / 0.7 A + 390 V / 0.18 A, Vin 430 V, wall 85 C, 1.5 K/W", 400, 0.7, 390, 0.18,
                   VIN_MAX, 85, 1.5, 70),
        board_case("Sustained worst, pessimistic Qrr law, same", 400, 0.7, 390, 0.18, VIN_MAX, 85, 1.5, 70, law="linear"),
        board_case("Mid-voltage: 200 V / 0.35 A + 290 V / 0.12 A, wall 80 C, 1.0 K/W", 200, 0.35, 290, 0.12, VIN_NOM, 80, 1.0, 70),
    ]
    w("| Case | QH1 | QL1 | QH2 | QL2 | devices (W) | toroid 1 / 2 (W) | toroid temp 1 / 2 (C) | shunts (W) | L2 + caps (W) | bleeders (W) | board total (W) | Pout (W) | eff. |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in cases:
        cells = []
        for b in (c["b1"], c["b2"]):
            for k in ("HS", "LS"):
                cells.append(f"{b['P'][k]['tot']:.2f} W / {b['T'][k][1]:.0f} C")
        w(f"| {c['name']} | " + " | ".join(cells) + f" | {c['dev']:.2f} | {c['l1']['tot']:.2f} / {c['l2']['tot']:.2f} | "
          f"{c['l1']['t']:.0f} / {c['l2']['t']:.0f} | {c['shunts']:.3f} | {c['l2loss'] + c['caps']:.2f} | {c['bleed']:.2f} | "
          f"**{c['total']:.1f}** | {c['pout']:.0f} | {c['pout'] / (c['pout'] + c['total']):.1%} |")
    w("\n(Device cells: loss / Tj of the IGBT die. Heat into the east wall = the devices column.)\n")

    # inductor
    w("## 5. Main inductor (2 mH Fe-Si-Al toroid), ambient 70 C\n")
    w("Core assumed: Kool-Mu-class 27.0 x 14.7 x 11.2 mm (Magnetics 77071 size), which three layers of 0.8 mm wire make "
      "into about 32 x 16.4 mm wound: Ae 65.6 mm2, le 63.5 mm, Ve 4.17 cm3. Free-air R_th about "
      f"{inductor_loss(bridge(425, 200, 0.35, dict(HS=100, LS=100)), 70)['r_th']:.0f} K/W "
      "(h 13 W/m2K over the wound surface, estimate).\n")
    w("| mu | AL (nH/T2) | N | wire (m) | DCR 20 C (ohm) | window fill | B_dc at 0.7 A (T, small-signal L) |")
    w("|---|---|---|---|---|---|---|")
    for mu in MU_CASES:
        d = inductor_design(mu)
        w(f"| {mu} | {d['AL'] * 1e9:.0f} | {d['N']:.0f} | {d['length']:.1f} | {d['r20']:.2f} | {d['fill']:.0%} | "
          f"{L_MAIN * 0.7 / (d['N'] * CORE['Ae']):.2f} |")
    w(f"\nLosses with mu {MU_BASE} (Steinmetz k 66 mW/cm3 at 1 kHz^1.46 T^2, alpha 1.46, beta 2.0, iGSE for the triangle: "
      "an ESTIMATE, +-50 %):\n")
    w("| Point | dI p-p (A) | dB p-p (T) | Cu DC (W) | Cu AC (W, Fr) | core (W) | total (W) | temp (C) |")
    w("|---|---|---|---|---|---|---|---|")
    for name, br, v, i in POINTS:
        b = bridge(VIN_NOM, v, i, dict(HS=100, LS=100))
        r = inductor_loss(b, 70)
        w(f"| {name} | {b['di']:.2f} | {r['dB']:.3f} | {r['p_dc']:.3f} | {r['p_ac']:.3f} ({r['fr']:.1f}) | {r['p_core']:.2f} | "
          f"{r['tot']:.2f} | {r['t']:.0f} |")
    w("\nThe core loss is set by the ripple flux, largest near D 0.5 (150-300 V); with mu 60 (more turns) dB falls by "
      "sqrt(60/90) and the core loss by about 1/1.5, with mu 125 it rises about 1.4x. At 400 V it is small.\n")

    # shunts
    w("## 6. Shunts (50 mohm)\n")
    w("| Point | low-side shunt (W) | cap shunt (W) |")
    w("|---|---|---|")
    for name, br, v, i in POINTS:
        b = bridge(VIN_NOM, v, i, dict(HS=100, LS=100))
        w(f"| {name} | {R_SHUNT * b['irms_off2'] * 1000:.1f} mW | {R_SHUNT * b['i_ripple_rms'] ** 2 * 1000:.1f} mW |")
    w("\nThe low-side shunt carries the inductor current only in the off-interval (short at 400 V). The peak shunt case is "
      "a sustained ramp-down or a short; 50 mohm at 3 A (trip) is 0.45 W: a 1 W 1225 / 2512 part is enough.\n")

    # gate drive
    w("## 7. Gate drive on the link's +12 V\n")
    qg = QG_12V
    i_g = qg * F_SW
    i_c = C_GE * 12 * F_SW
    i_rge = 12 / 10e3 * 0.5   # 10 k G-E (rev3), on about half the time on average per device
    i_q = 2.0e-3              # Si8271 VDD2 quiescent incl. switching overhead (ESTIMATE, check datasheet)
    i_boot = 0.2e-3           # bootstrap diode / leakage
    rows = [("gate charge Qg ~18 nC (0-12 V) x 50 kHz", 4 * i_g),
            ("1 nF G-E capacitors (rev3 option) x 12 V x 50 kHz", 4 * i_c),
            ("10 kohm G-E resistors (on ~50 % of the time)", 4 * i_rge),
            ("Si8271 VDD2 quiescent, ~2 mA each (estimate)", 4 * i_q),
            ("bootstrap leakage", 2 * i_boot)]
    w("| Item | +12 V current (mA) |")
    w("|---|---|")
    for k, v in rows:
        w(f"| {k} | {v * 1e3:.1f} |")
    tot = sum(v for _, v in rows)
    w(f"| **total with the 1 nF caps** | **{tot * 1e3:.1f}** |")
    w(f"| total without the 1 nF caps | {(tot - 4 * i_c) * 1e3:.1f} |")
    w(f"\nBudget 25 mA (ICD +12 V to the HV board). Gate power per device {qg * 12 * F_SW * 1e3:.0f} mW "
      f"(+{C_GE * 144 * F_SW * 1e3:.0f} mW with 1 nF), dissipated in the 15 / 8 ohm resistors and the driver, not in the IGBT. "
      "The 1 nF G-E caps slow the edges a little: rev3 M15 case P put +0.09 W (+3 %) on Q201 at full load; "
      "they cost 2.4 mA of the 12 V budget.\n")

    w("## 8. East wall: local spreading (ESTIMATE)\n")
    k_al, t_al, r1, r2 = 150.0, 2e-3, 6e-3, 40e-3
    r_sp = np.log(r2 / r1) / (2 * np.pi * k_al * t_al)
    w(f"2 mm Al wall (k 150 W/mK, 5052-class), heat source about a TO-220 tab (r 6 mm), spreading out to r 40 mm: "
      f"R_spread = ln(r2/r1) / (2 pi k t) = **{r_sp:.2f} K/W** per device. With the sustained worst case "
      f"(QH1 ~3 W, the other three ~1.2 W, pitch ~20-25 mm) the wall under QH1 sits roughly "
      f"{3.0 * r_sp + 1.2 * r_sp * 0.5:.0f} K above the wall a few cm away. So 'wall 85 C' at the device means the "
      "wall away from the devices at about 80 C. The whole wall has to take ~4-5 W (devices) into the chassis; "
      "that is the number for the chassis's own thermal budget.\n")
    with open(OUT_MD, "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))

    # plot: QH1 Tj vs load current for walls / Rcw
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        ii = np.linspace(0.0, 0.8, 33)
        fig, ax = plt.subplots(1, 2, figsize=(10, 4))
        for r, ls in ((0.5, ":"), (1.0, "-"), (1.5, "--")):
            for tw, col in ((70, "#3b7dd8"), (85, "#d8573b")):
                tj = [thermal(VIN_MAX, 400, i, tw, r)["T"]["HS"][1] for i in ii]
                ax[0].plot(ii, tj, ls, color=col, label=f"wall {tw} C, Rcw {r}")
        ax[0].axhline(125, color="k", lw=0.8)
        ax[0].set_xlabel("V_ANODE current at 400 V (A)")
        ax[0].set_ylabel("Tj QH1 (C), Vin 430 V")
        ax[0].legend(fontsize=7)
        ax[0].grid(alpha=0.3)
        for v in (400, 300, 200, 150):
            p = [bridge(VIN_NOM, v, i, dict(HS=110, LS=100))["P"]["HS"]["tot"] for i in ii]
            q = [bridge(VIN_NOM, v, i, dict(HS=110, LS=100))["P"]["LS"]["tot"] for i in ii]
            l, = ax[1].plot(ii, p, label=f"QH1 {v} V")
            ax[1].plot(ii, q, "--", color=l.get_color(), lw=0.8)
        ax[1].set_xlabel("output current (A)")
        ax[1].set_ylabel("loss (W): solid HS, dashed LS")
        ax[1].legend(fontsize=7)
        ax[1].grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(OUT_PNG, dpi=110)
    except ImportError:
        pass


if __name__ == "__main__":
    main()
