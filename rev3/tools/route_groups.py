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
    ("hvsmall", ["RAW_SS1", "RAW_SS2", "BLD1", "LED_RAW", "DS0A", "DS0B", "DS1A", "DS1B", "DV0A", "DV0B", "DV1A",
                 "DV1B", "BL1", "BL2", "LED_VA", "CD1", "CD2"]),
    ("ground", ["PGND", "GND_STAR", "CHASSIS", "BR_DC", "+12V"]),
    ("kelvin", ["KS0P", "KS0N", "KS1P", "KS1N", "KS2P", "KS2N", "KS3P", "KS3N"]),
    ("spi", ["ADC_SCK", "ADC_SCK_RET", "CS_FAST", "SDO_VA", "SDO_VS", "SDO_IC1", "SDO_IL1", "SDO_IC2", "SDO_IL2",
             "SDO_VA_L", "SDO_VS_L", "SDO_IC1_L", "SDO_IL1_L", "SDO_IC2_L", "SDO_IL2_L", "ADC_SDO", "ADC_SDO_L",
             "ADC_DIN", "ADC_CNV"]),
    ("analog", ["FA_VA", "FA_VS", "FA_IC1", "FA_IL1", "FA_IC2", "FA_IL2", "VM_A", "VM_S", "VM_RAW", "VM_UC1",
                "IM_C14", "IM_Q12", "IM_C24", "IM_Q22", "IA0P", "IA0N", "IA1P", "IA1N", "IA2P", "IA2N", "IA3P",
                "IA3N", "DV0", "DV1", "DS0", "DS1", "IBIAS", "IBIAS_D", "VREF", "+3V3_REF", "ADC_REFIN", "UBSP0",
                "ADC_IN0", "ADC_IN1", "ADC_IN2", "ADC_IN3", "ADC_IN4", "ADC_IN5", "ADC_IN6", "ADC_IN7"]),
]
POUR = ["GND", "+3V3"]


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
    groups["lv"] = sorted(n for n in names if n not in used and not short[n].startswith("unconnected-"))
    p = os.path.join(R3, "routing.json")
    cfg = json.load(open(p))
    cfg["groups"] = groups
    json.dump(cfg, open(p, "w"), indent=2)
    print({g: len(v) for g, v in groups.items()})


if __name__ == "__main__":
    main()
