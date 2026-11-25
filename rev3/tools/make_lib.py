#!/usr/bin/env python3
"""Build lib/tube_hv_supplies_rev3.kicad_sym from KiCad's standard symbol libraries: the symbols the
rev 3 sheets use, flattened (KiCad's derived 'extends' symbols resolved, since a schematic's
lib_symbols needs them whole)."""
import copy
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "..", "tools", "p2k"))
from p2k.sexpr import Sym, find, find_all, load, save  # noqa: E402

KICAD = os.environ.get("KICAD_SYMBOLS", "/mnt/c/Program Files/KiCad/10.0/share/kicad/symbols")
WANT = [
    ("Device", "R"), ("Device", "C"), ("Device", "C_Polarized"), ("Device", "D"), ("Device", "D_TVS"),
    ("Device", "L"), ("Device", "FerriteBead"), ("Device", "LED"), ("Device", "Fuse"), ("Device", "NetTie_2"), ("Device", "Q_NIGBT_GCE"),
    ("Diode_Bridge", "GBU8J"), ("Driver_FET", "UCC21520DW"), ("Analog_ADC", "AD7689xCP"),
    ("Amplifier_Operational", "MCP6004"), ("Comparator", "LMV339"), ("Isolator", "TLP293"),
    ("74xGxx", "74LVC1G10"), ("74xGxx", "74LVC1G17"), ("74xGxx", "74AUP1G74"),
    ("Reference_Voltage", "REF3030"), ("Amplifier_Operational", "OPA2356xxD"),
    ("74xGxx", "74LVC1G07"), ("74xGxx", "74LVC1G08"), ("74xGxx", "74LVC1G04"),
    ("Analog_Switch", "NX3L4051PW"), ("74xx", "74LS163"),
    ("Mechanical", "MountingHole_Pad"), ("Mechanical", "MountingHole"), ("Mechanical", "Heatsink"), ("Reference_Voltage", "LM4040DBZ-2.5"),
    ("Connector_Generic", "Conn_02x20_Odd_Even"), ("Connector_Generic", "Conn_01x02"), ("Connector_Generic", "Conn_01x01"),
    ("power", "GND"), ("power", "+3V3"), ("power", "+12V"), ("power", "PWR_FLAG"),
]
_cache = {}


def library(name):
    if name not in _cache:
        _cache[name] = {s[1]: s for s in find_all(load(os.path.join(KICAD, name + ".kicad_sym")), "symbol")}
    return _cache[name]


def flat(libname, name):
    s = copy.deepcopy(library(libname)[name])
    ext = find(s, "extends")
    if not ext:
        return s
    base = flat(libname, ext[1])
    out = copy.deepcopy(base)
    out[1] = name
    for sub in find_all(out, "symbol"):
        sub[1] = sub[1].replace(ext[1] + "_", name + "_", 1)
    props = {p[1]: p for p in find_all(s, "property")}
    for i, c in enumerate(out):
        if isinstance(c, list) and c and c[0] == "property" and c[1] in props:
            out[i] = props.pop(c[1])
    for p in props.values():
        out.insert(2, p)
    return out


# board-local symbols derived from stock ones: (lib, source, new name, {old pin number: new pin number})
# ADS7056 (TI SBAS769, X2QFN-8 RUG): 1 CS, 2 SDO, 3 SCLK, 4 DVDD, 5 GND, 6 AVDD (= reference), 7 AINP, 8 AINM;
# drawn from the ADS7049 symbol (pins 1 DVDD, 2 SCLK, 3 SDO, 4 CS, 5 AINM, 6 AINP, 7 AVDD, 8 GND)
DERIVED = [("Analog_ADC", "ADS7049", "ADS7056", {"1": "4", "2": "3", "3": "2", "4": "1", "5": "8", "6": "7", "7": "6", "8": "5"})]


def derived(libname, src, new, pinmap):
    s = flat(libname, src)
    s[1] = new
    for sub in find_all(s, "symbol"):
        sub[1] = sub[1].replace(src + "_", new + "_", 1)
        for p in find_all(sub, "pin"):
            num = find(p, "number")
            num[1] = pinmap.get(str(num[1]), num[1])
    for p in find_all(s, "property"):
        if p[1] == "Value":
            p[2] = new
        if p[1] == "Footprint":
            p[2] = "Package_DFN_QFN:Texas_UQFN-8_1.5x1.5mm_P0.5mm"
        if p[1] == "Datasheet":
            p[2] = "https://www.ti.com/lit/ds/symlink/ads7056.pdf"
    return s


def main():
    lib = [Sym("kicad_symbol_lib"), [Sym("version"), 20251024], [Sym("generator"), "make_lib"],
           [Sym("generator_version"), "10.0"]]
    for libname, name in WANT:
        lib.append(flat(libname, name))
    for libname, src, new, pm in DERIVED:
        lib.append(derived(libname, src, new, pm))
    save(os.path.join(HERE, "lib", "tube_hv_supplies_rev3.kicad_sym"), lib)
    for libname, name in WANT:
        s = flat(libname, name)
        pins = []
        for sub in find_all(s, "symbol"):
            for p in find_all(sub, "pin"):
                num, nm = find(p, "number"), find(p, "name")
                pins.append(f"{num[1]}={nm[1]}" if num and nm else "?")
        print(f"{name}: " + " ".join(pins))


if __name__ == "__main__":
    main()
