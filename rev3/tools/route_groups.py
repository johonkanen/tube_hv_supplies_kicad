#!/usr/bin/env python3
"""Writes the net groups of rev3/routing.json from the schematic netlist (full KiCad net names).

    python3 rev3/tools/route_groups.py
Groups (routed in this order by tools/route_chain.sh, each locked when done): see GROUPS below; every net not
named lands in 'lv' (low-voltage control), except the pour nets GND / +3V3 handled last.
"""
import json
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET

R3 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(os.path.dirname(R3), "tools", "p2k", "bin", "kicad-cli")
SCH = os.path.join(R3, "kicad", "tube_hv_supplies_rev3.kicad_sch")
GROUPS = [
    ("bridge", ["SW1", "SW2", "UIN1", "UIN2"]),
    ("hvpow", ["UC1", "UC2", "IC1", "IC2", "IS1", "IS2", "VO1", "VO2", "B_P", "UIN", "V_ANODE", "V_SCREEN"]),
    ("gate", ["GH1", "GHD1", "BOOT1", "GH2", "GHD2", "BOOT2", "GL1", "GLD1", "GL2", "GLD2", "BS1", "BS2"]),
    ("hvsmall", ["RAW_SS1", "RAW_SS2", "BLD1", "LED_RAW", "DS0A", "DS0B", "DV0A", "DV0B", "DV1A",
                 "DV1B", "BL1", "BL2", "LED_VA", "CD1", "CD2"]),
    ("ground", ["PGND", "CHASSIS", "BR_DC"]),
    ("kelvin", ["KS0P", "KS0N", "KS1P", "KS1N", "KS2P", "KS2N", "KS3P", "KS3N"]),
    ("spi", ["ADC_SCK", "ADC_SCK_RET", "CS_FAST", "SDO_ADC", "SDO_L", "MUX_CLR_N", "MUX_HOLD_N", "MUX_CLK",
             "MUX_S0", "MUX_S1", "MUX_S2", "DRV_DIS_STAT"]),
    ("analog", ["FA_DRV", "AIN_ADC", "MUX_OUT", "VM_A", "VM_S", "VM_RAW", "IM_C14", "IM_Q12", "IM_C24", "IM_Q22",
                "IA0P", "IA0N", "IA1P", "IA1N", "IA2P", "IA2N", "IA3P", "IA3N", "DV0", "DV1", "DS0", "IBIAS", "VREF",
                "+3V3_REF"]),
]
POUR = ["GND", "+3V3", "+12V"]
STAR = ["GND_STAR"]


def main():
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "n.xml")
        subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", out, SCH], check=True,
                       capture_output=True)
        names = [n.get("name") for n in ET.parse(out).iter("net")]
    short = {n: n.rsplit("/", 1)[-1] for n in names}
    groups, used = {}, set()
    for g, ss in GROUPS:
        groups[g] = sorted(n for n in names if short[n] in ss)
        used.update(groups[g])
        missing = set(ss) - {short[n] for n in groups[g]}
        if missing:
            raise SystemExit(f"{g}: no net {missing}")
    groups["pour"] = sorted(n for n in names if short[n] in POUR)
    used.update(groups["pour"])
    used.update(n for n in names if short[n] in STAR)
    groups["lv"] = sorted(n for n in names if n not in used and not short[n].startswith("unconnected-"))
    p = os.path.join(R3, "routing.json")
    cfg = json.load(open(p))
    cfg["groups"] = groups
    json.dump(cfg, open(p, "w"), indent=2)
    print({g: len(v) for g, v in groups.items()})


if __name__ == "__main__":
    main()
