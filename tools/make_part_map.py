#!/usr/bin/env python3
"""Generate lib/part_map.csv: refdes -> PDF page, symbol, value, Proteus device and package.

Sources (STATUS.md "Phase 1 preparation"):
  refdes   reference/ipc356_pads.json (`refdes` = KiCad name, `refdes_proteus` = Proteus name),
           plus OFF_BOARD (drawn in the PDF, no IPC pads)
  value    schematic value from ROOT.DSN in source/hi_voltage_suppliesv2.pdsprj (p2k.pdsprj.dsn_values;
           = the PDF)
  device, package   the schematic component record in ROOT.DSN: library device after the
           COMPONENT VALUE label, and its {PACKAGE=...} property (dsn_devices() below). The
           shared p2k.pdsprj.lyt_parts finds no record in this ROOT.LYT (no EID markers in this
           Proteus 8.12 SP2 layout file; p2k candidate, STATUS.md)
  sheet    PDF page whose text layer has the refdes (p2k.pdftext); PAGE_OVERRIDES if ambiguous
  lib_id   SYMBOL_BY_DEVICE (Proteus device -> lib/tube_hv_supplies.kicad_sym symbol)

  tools/make_part_map.py           write lib/part_map.csv
  tools/make_part_map.py --check   fail if lib/part_map.csv is not up to date
"""
import csv
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2k"))  # proteus2kicad
from p2k import board, pdftext, pdsprj  # noqa: E402

PRJ = board.path("source", "hi_voltage_suppliesv2.pdsprj")
PDF = board.path("source", "schematic_pdf", "hi_voltage_suppliesv2.PDF")
OUT = board.path("lib", "part_map.csv")
LIB = board.config().PROJECT

C, CP, R = "C", "C_Polarized", "R"
SYMBOL_BY_DEVICE = {
    "0603 CAPACITOR": C, "1206 CAP": C, "CAP": C, "C2220C102MZGACTU": C,
    "EKXJ451ELL390MJ50S": CP,
    "0603 RESISTOR": R, "0805 RES": R, "RES": R, "RES 1206": R, "9C06031A1213FKHFT": R,
    "KRL2012-C-R004-F-T1": R,
    "ELJ-FA100KF": "L",
    "S1M": "D",
    "IRGB14C40L": "IKP08N65F5",          # Proteus device of the IKP08N65F5 IGBTs (TO-220, 1=G 2=C 3=E)
    "SI8271": "SI8271",
    "LT1014": None,                      # U1 (value LMV324A) and U2 (LT1014): by value, below
    "ADR380": "ISL21010",                # REF1 value ISL21010CFH315Z-TK, Proteus device ADR380
    "ADC121C027": "ADC121C027",
    "38 PIN HEADER 50TH": "HEADER_2X20_50MIL",   # J1: device says 38 pins, value / package 40 (37, 38 N/C)
    "16 PIN HEADER 50TH": "HEADER_2X8_50MIL",
    "TERMINAL": "PIN",                   # BLADE CONNECTOR (2 holes, both pin 1) and PIN (1 hole)
}
SYMBOL_BY_VALUE = {"LMV324A": "LMV324A", "LT1014": "LT1014"}   # quad op-amps, Proteus device LT1014

# Parts drawn in the PDF without IPC pads: symbols excluded from the board (on_board no), ignored
# by check_symbols / compare_netlists; Phase 2 lists them in OFF_BOARD_PARTS.
# Proteus refdes -> (KiCad refdes, lib symbol).
OFF_BOARD = {
    "L1": ("L1", "L_OFFBOARD"),   # 3 mH, OUT1 - UC3, wired to the terminals L5 / L12 (page 1)
    "L3": ("L3", "L_OFFBOARD"),   # 3 mH, OUT2 - U_OUT, wired to the terminals L11 / L6 (page 1)
}

# Refdes whose PDF text-layer hits are ambiguous or missing (resolved on the page renders): none.
PAGE_OVERRIDES = {}

FIELDS = ["refdes", "sheet", "lib_id", "value", "device", "package", "proteus_refdes", "off_board"]


def dsn_devices(prj, refs):
    """{refdes: (device, package)} from the ROOT.DSN component records: the device is the first
    string after the COMPONENT VALUE label, the package the {PACKAGE=...} property that follows
    (None for parts without one, e.g. the off-board inductors). Same refdes search as
    p2k.pdsprj.dsn_values."""
    b = pdsprj._read(prj, "ROOT.DSN")

    def pstr(p):
        n = b[p + 1]
        s = b[p + 2:p + 2 + n]
        return s.decode("latin-1") if n and all(32 <= c < 127 for c in s) else None

    out = {}
    for m in re.finditer(rb"COMPONENT ID\x00", b):
        i = m.start()
        ref = None
        for p in range(i - 1, max(0, i - 160), -1):
            if b[p] == 0xFF:
                s = pstr(p)
                if s and s.split(":")[0] in refs and p + 2 + len(s) <= i:
                    ref = s.split(":")[0]
                    break
        if not ref:
            continue
        mv = b.find(b"COMPONENT VALUE\x00", m.end(), m.end() + 200)
        dev = None
        for p in range(mv + 16, mv + 60):
            if b[p] == 0xFF:
                dev = pstr(p)
                if dev:
                    break
        pk = re.search(rb"\{PACKAGE=([^}]*)\}", b[mv:mv + 400])
        out.setdefault(ref, set()).add((dev, pk.group(1).decode("latin-1") if pk else None))
    multi = {r: v for r, v in out.items() if len(v) > 1}
    if multi:
        raise ValueError(f"dsn_devices: parts with several records: {multi}")
    return {r: v.pop() for r, v in out.items()}


def build():
    ipc = json.load(open(board.path("reference", "ipc356_pads.json")))
    kicad = {}
    for p in ipc["pads"]:
        if p["kind"] == "pad":
            kicad[p["refdes_proteus"]] = p["refdes"]
    for ref, (kref, _) in OFF_BOARD.items():
        assert ref not in kicad, f"OFF_BOARD part {ref} has IPC pads"
        kicad[ref] = kref
    refs = set(kicad)
    values = pdsprj.dsn_values(PRJ, refs)
    devices = dsn_devices(PRJ, refs)
    pages = pdftext.refdes_pages(pdftext.pdf_words(PDF), refs)
    errors = []
    rows = []
    for ref in sorted(refs):
        page = PAGE_OVERRIDES.get(ref)
        if page is None:
            if len(pages[ref]) != 1:
                errors.append(f"{ref}: PDF pages {pages[ref]} (add to PAGE_OVERRIDES)")
                continue
            page = pages[ref][0]
        elif page not in pages[ref]:
            errors.append(f"{ref}: PAGE_OVERRIDES page {page} not among the PDF hits {pages[ref]}")
        value = values.get(ref)
        dev, pkg = devices.get(ref, (None, None))
        if not value or not dev:
            errors.append(f"{ref}: no schematic value / device ({value!r}, {dev!r})")
            continue
        if ref in OFF_BOARD:
            sym = OFF_BOARD[ref][1]
        elif dev in SYMBOL_BY_DEVICE:
            sym = SYMBOL_BY_DEVICE[dev] or SYMBOL_BY_VALUE.get(value)
        else:
            sym = None
        if not sym:
            errors.append(f"{ref}: no symbol for Proteus device {dev!r} (value {value!r})")
            continue
        if ref not in OFF_BOARD and not pkg:
            errors.append(f"{ref}: no PACKAGE property")
        rows.append({"refdes": kicad[ref], "sheet": page, "lib_id": f"{LIB}:{sym}", "value": value,
                     "device": dev, "package": pkg or "", "proteus_refdes": ref if ref != kicad[ref] else "",
                     "off_board": "yes" if ref in OFF_BOARD else ""})
    for ref in sorted(set(PAGE_OVERRIDES) - refs):
        errors.append(f"PAGE_OVERRIDES: {ref} is not a refdes")
    if errors:
        sys.exit("make_part_map:\n  " + "\n  ".join(errors))
    key = lambda r: (r["sheet"], [(0, int(t), "") if t.isdigit() else (1, 0, t)
                                  for t in re.findall(r"\d+|\D+", r["refdes"])])
    rows.sort(key=key)
    buf = io.StringIO()
    buf.write("# Generated by tools/make_part_map.py - do not edit. sheet = Proteus PDF page;"
              " value = schematic value (ROOT.DSN); device/package = Proteus schematic device and PACKAGE property"
              " (ROOT.DSN); off_board = drawn in the PDF, no pads (symbol excluded from board)\n")
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue(), rows


def main():
    text, rows = build()
    rel = os.path.relpath(OUT, board.root())
    per = {}
    for r in rows:
        per[r["sheet"]] = per.get(r["sheet"], 0) + 1
    summary = f"{len(rows)} parts ({sum(not r['off_board'] for r in rows)} on the board); per sheet " + \
        " ".join(f"{s}:{n}" for s, n in sorted(per.items()))
    if "--check" in sys.argv:
        if not os.path.exists(OUT) or open(OUT, encoding="utf-8").read() != text:
            print(f"make_part_map: {rel} is out of date, run tools/make_part_map.py")
            return 1
        print(f"make_part_map: {rel} up to date, {summary}")
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(text)
    print(f"wrote {rel}: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
