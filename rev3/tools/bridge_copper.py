#!/usr/bin/env python3
"""Scripted copper of the two half bridges (commutation loops, switch-node links, gate and bootstrap paths) and the
fast ADC bus (SCLK daisy chain, CS_FAST), drawn deterministically and locked before the router runs.

    tools/p2k/bin/kipy rev3/tools/bridge_copper.py IN.kicad_pcb OUT.kicad_pcb

Every point is a pad ("REF.PAD") or a chassis coordinate (x, y); a track takes the net of its first pad.
Layers: F = bottom (THT side), B = plate side. STATUS.md "Layout, first pass" describes the loops.
"""
import math
import sys

import pcbnew

OX, OY = 525.0, 30.0


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(x - OX), mm(y - OY))


class Drawer:
    def __init__(self, b):
        self.b = b
        self.fp = {f.GetReference(): f for f in b.GetFootprints()}

    def pad(self, s):
        ref, num = s.split(".")
        ps = [p for p in self.fp[ref].Pads() if p.GetNumber() == num]
        if not ps:
            raise SystemExit(f"no pad {s}")
        return ps[0]

    def xy(self, p):
        if isinstance(p, str):
            q = self.pad(p).GetPosition()
            return pcbnew.ToMM(q.x) + OX, pcbnew.ToMM(q.y) + OY
        return p

    def track(self, layer, w, pts, net=None):
        if net is None:
            net = next(self.pad(p).GetNet() for p in pts if isinstance(p, str))
        elif isinstance(net, str):
            net = self.b.GetNetsByName()[net]
        L = pcbnew.F_Cu if layer == "F" else pcbnew.B_Cu
        xy = [self.xy(p) for p in pts]
        for (x0, y0), (x1, y1) in zip(xy, xy[1:]):
            if math.hypot(x1 - x0, y1 - y0) < 1e-3:
                continue
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(pt(x0, y0))
            t.SetEnd(pt(x1, y1))
            t.SetWidth(mm(w))
            t.SetLayer(L)
            t.SetNet(net)
            t.SetLocked(True)
            self.b.Add(t)
        return net

    def via(self, x, y, net, size=0.6, drill=0.3):
        if isinstance(net, str):
            net = self.pad(net).GetNet() if "." in net else self.b.GetNetsByName()[net]
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(pt(x, y))
        v.SetWidth(mm(size))
        v.SetDrill(mm(drill))
        v.SetNet(net)
        v.SetLocked(True)
        self.b.Add(v)


def bridge1(d):
    # UIN1 (F): Q201 collector -> C213 / C202 / C203 -> C201, and the feed from the R201 link
    d.track("F", 1.5, ["Q201.2", (595.4, 79.9), "C202.1"])
    d.track("F", 1.2, ["Q201.2", (596.0, 83.4), "C213.1"])
    d.track("F", 1.2, ["C213.1", "C203.1", (597.8, 93.6), (597.8, 99.0), (591.6, 105.2), "C201.1"])
    d.via(609.6, 89.04, "R201.2", 0.8, 0.4)
    d.track("B", 1.0, ["R201.2", (609.6, 89.04)])
    d.track("F", 1.0, [(609.6, 89.04), (606.3, 93.6), (597.8, 93.6)], net=d.pad("R201.2").GetNet())
    # PGND (F): C214 -> under R202 -> C203 / C202 -> R202, and down to C201's negative
    d.track("F", 1.5, ["C214.2", (577.15, 91.2), (592.45, 91.2), "C203.2"])
    d.track("F", 1.5, ["C202.2", "R202.2"])
    d.track("F", 1.2, ["R202.2", (589.6, 77.9), (588.5, 79.0), (588.5, 91.2)])
    d.track("F", 1.5, [(582.5, 91.2), "C201.2"])
    # IS1 (F): low-side emitter -> shunt R202
    d.track("F", 1.5, ["Q202.3", "R202.1"])   # straight north
    # SW1: emitter of Q201 -> L201 and C213 (F); the link to Q202's collector under the lead bends (B)
    d.track("F", 1.5, ["Q201.3", (599.5, 79.5), "L201.1"])
    d.track("F", 1.2, ["Q201.3", (602.65, 83.0), "C213.2"])
    d.track("F", 1.0, ["C214.1", "Q202.2"])
    d.track("B", 1.2, ["Q202.2", (582.0, 79.2), (597.54, 79.2), "Q201.3"])
    # gate drive, plate side: U301 OUTA -> R305 -> Q201 gate; R306 to SW1; VSSA (pin 14) up to the SW1 link
    d.track("B", 0.6, ["U301.15", (592.28, 88.4), (592.46, 88.0), "R305.1"])
    d.track("B", 0.8, ["R305.2", "Q201.1"])
    d.track("B", 0.5, ["R306.1", (592.46, 83.9)], net=d.pad("R305.2").GetNet())
    d.track("B", 0.6, ["U301.14", (591.01, 89.6), (591.01, 79.2)])
    d.track("B", 0.6, ["R306.2", (597.3, 83.9), (598.6, 82.6), "Q201.3"])
    # bootstrap: BOOT1 from pin 16 to C302 / C303 and the diode; their SW1 ends up to the emitter
    d.track("B", 0.6, ["U301.16", (593.55, 90.4), (597.5, 90.4), (597.5, 91.0)])
    d.track("B", 0.6, [(597.5, 90.4), (598.6, 90.4), "C302.1"])
    d.track("B", 0.6, [(598.6, 90.4), (600.4, 90.4), "C303.1"])
    d.track("B", 0.6, ["C302.2", (598.6, 82.6)])
    d.track("B", 0.6, ["C303.2", (600.4, 86.4), (598.6, 86.4)], net=d.pad("C302.2").GetNet())
    # low side: OUTB (pin 10) -> R307 -> Q202 gate; R308 GL1 -> IS1
    d.track("B", 0.6, ["U301.10", (585.93, 88.3), (580.2, 88.3), (579.46, 87.6), "R307.1"])
    d.track("B", 0.8, ["R307.2", "Q202.1"])
    d.track("B", 0.5, ["R308.1", (579.46, 84.2)], net=d.pad("R307.2").GetNet())
    d.track("B", 0.6, ["R308.2", (583.6, 84.2), "Q202.3"])
    # U301 decoupling on F under the driver: +12V (pin 11) and PGND (pin 9) through vias
    d.via(587.2, 92.6, "U301.11")
    d.track("B", 0.6, ["U301.11", (587.2, 92.6)])
    d.track("F", 0.6, [(587.2, 92.6), "C305.1", (587.48, 94.0), "C304.1"], net=d.pad("U301.11").GetNet())
    d.via(584.66, 92.6, "U301.9")
    d.track("B", 0.6, ["U301.9", (584.66, 92.6)])
    d.track("F", 0.8, [(584.66, 92.6), "C305.2", (584.52, 94.0), "C304.2"], net=d.pad("U301.9").GetNet())
    d.track("F", 0.8, [(584.66, 92.6), (584.66, 91.2)], net=d.pad("U301.9").GetNet())


def bridge2(d):
    # UIN2 (F): Q203 collector -> C207 / C217 / C208 -> C206
    d.track("F", 1.5, ["Q203.2", (618.1, 156.1), "C207.1"])
    d.track("F", 1.2, ["Q203.2", (618.3, 152.0), (617.75, 150.0), "C208.1", (617.75, 141.0), "C206.1"])
    d.track("F", 1.2, [(617.75, 150.0), "C217.1"])
    # PGND (F): C207 / C208 / R209 -> C206; C218's negative along y 145.6
    d.track("F", 1.5, ["C207.2", "R209.2"])
    d.track("F", 1.2, ["R209.2", (623.9, 158.1), (625.0, 157.0), (625.0, 145.6)])
    d.track("F", 1.5, ["C208.2", (621.85, 145.6), (626.5, 140.6), "C206.2"])
    d.track("F", 1.2, ["C218.2", (637.05, 145.6), (621.85, 145.6)])
    # IS2 (F): low-side emitter -> R209
    d.track("F", 1.5, ["Q204.3", "R209.1"])
    # SW2: emitter of Q203 -> C217 and L203 (F); link to Q204's collector under the lead bends (B)
    d.track("F", 1.5, ["Q203.3", (613.0, 155.6), (603.0, 155.6), "L203.1"])
    d.track("F", 1.2, [(612.0, 155.6), (611.55, 152.6), "C217.2"])
    d.track("F", 1.0, ["C218.1", (632.6, 152.6), "Q204.2"])
    d.track("B", 1.2, ["Q203.3", (615.96, 157.4), (631.5, 157.4), "Q204.2"])
    # gate drive, plate side
    d.track("B", 0.6, ["U302.15", (624.52, 150.0), (621.6, 150.0), "R313.1"])
    d.track("B", 0.8, ["R313.2", "Q203.1"])
    d.track("B", 0.5, ["R314.1", (620.2, 151.3), (620.6, 152.01)], net=d.pad("R313.2").GetNet())
    d.track("B", 0.6, ["R314.2", (616.6, 152.4), "Q203.3"])
    d.track("B", 0.6, ["U302.14", (625.79, 150.2), (625.2, 150.8), (625.2, 157.4)])
    # bootstrap: pin 16 -> D302 / C309 / C310 (BOOT2 along y 146.0), their SW2 ends north to the emitter
    d.track("B", 0.6, ["U302.16", (623.25, 147.0), (618.6, 147.0)])
    d.track("B", 0.6, [(618.6, 147.0), (615.6, 147.0), "C309.1"])
    d.track("B", 0.6, [(615.6, 147.0), (613.4, 147.0), "C310.1"])
    d.track("B", 0.6, ["C309.2", (614.6, 150.0), (615.96, 151.4), "Q203.3"])
    d.track("B", 0.6, ["C310.2", (612.6, 150.0), (614.6, 150.0)], net=d.pad("C309.2").GetNet())
    # low side
    d.track("B", 0.6, ["U302.10", (630.87, 150.0), (633.5, 150.0), "R315.1"])
    d.track("B", 0.8, ["R315.2", "Q204.1"])
    d.track("B", 0.5, ["R316.1", (633.2, 151.3), (633.6, 152.01)], net=d.pad("R315.2").GetNet())
    d.track("B", 0.6, ["R316.2", (629.6, 152.6), "Q204.3"])


def filters(d):
    """C1 and second-stage copper of bridge 1 (F): UC1 from L201 to C204 / C211 / L202, IC1 from the capacitors'
    negatives to the shunt R203 (plate side), VO1 from L202 north to C205 (front-west) and south to C212 / R205."""
    d.track("F", 1.5, ["L201.2", (643.0, 95.0), "C204.1"])
    d.track("F", 1.5, ["C204.1", (636.0, 109.5), (630.5, 109.5), "C211.1"])
    d.track("F", 1.5, ["C204.1", (652.0, 107.0), (655.0, 110.0), "L202.1"])
    d.track("F", 1.5, ["C204.2", (636.0, 117.0), (604.0, 117.0), "C211.2"])
    d.track("F", 1.5, [(604.0, 117.0), (600.0, 118.6), (589.5, 118.6), (589.5, 122.46), "R203.1"],
            net=d.pad("C211.2").GetNet())
    d.track("F", 1.5, ["R203.2", (584.0, 113.0), (582.5, 110.0), "C201.2"])     # IC1 shunt back to bridge 1
    d.track("F", 0.8, [(630.5, 109.5), "R420.1"], net=d.pad("C211.1").GetNet())     # UC1 divider top
    d.via(608.0, 95.8, "R415.1", 0.8, 0.4)                                            # raw divider top from R201
    d.track("B", 1.0, ["R201.1", (608.0, 95.8)])
    d.track("F", 0.8, [(608.0, 95.8), (603.5, 99.8), "R415.1"], net=d.pad("R201.1").GetNet())
    vo1 = d.pad("L202.2").GetNet()
    # VO1 north (F) along the east edge, between J101's tab rows, behind the fault block to C205 (front-west)
    d.track("F", 1.0, ["L202.2", (671.9, 111.0), (671.9, 62.0), (668.0, 55.0), (651.0, 55.0), (649.5, 56.5),
                       (604.0, 56.5), "C205.1"])
    # VO1 south: plate side lane x 651 (kept free of the measurement parts), back to F at C212, then to R205
    d.track("B", 1.0, ["L202.2", (670.93, 117.0), (650.6, 117.0), (650.6, 129.4), (641.25, 129.4)],
            net=vo1)
    d.via(641.25, 129.4, vo1, 0.8, 0.4)
    d.track("F", 1.0, [(641.25, 129.4), "C212.1"], net=vo1)
    d.track("F", 1.0, ["C212.1", (641.25, 140.0), (646.0, 145.0), (646.0, 163.0), "R205.1"])


ADC_ROW = ["U402", "U406", "U407", "U404", "U409", "U410"]


def spi(d):
    """The fast ADC bus on the plate side: SCLK daisy-chained along y 102.4 from the first ADS7056 to the AD7689
    (pin 13), the returned clock R456 at that far end; CS_FAST along y 105.6. Stubs to pins 3 (SCLK, north) and 1
    (CS, south); each SDO (pin 2) leaves west between them (routed by the router)."""
    sck = d.pad("U402.3").GetNet()
    cs = d.pad("U402.1").GetNet()
    xs = [d.xy(f"{u}.3")[0] for u in ADC_ROW]
    x0 = xs[0] - 1.0
    u411 = d.xy("U411.13")
    d.track("B", 0.2, [(x0, 102.4), (u411[0] - 0.8, 102.4), "U411.13"], net=sck)
    for u in ADC_ROW:
        x, y = d.xy(f"{u}.3")
        d.track("B", 0.2, [f"{u}.3", (x - 0.35, y), (x - 0.35, 102.4)], net=sck)
        x, y = d.xy(f"{u}.1")
        d.track("B", 0.2, [f"{u}.1", (x - 0.35, y), (x - 0.35, 105.6)], net=cs)
    r = d.xy("R456.1")
    d.track("B", 0.2, [(r[0], 102.4), "R456.1"], net=sck)
    r = d.xy("R457.1")
    d.track("B", 0.2, [(x0, 105.6), (xs[-1] + 0.6, 105.6), (r[0] - 0.8, 105.6), (r[0], r[1])], net=cs)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    b = pcbnew.LoadBoard(src)
    d = Drawer(b)
    bridge1(d)
    bridge2(d)
    filters(d)
    spi(d)
    pcbnew.SaveBoard(dst, b)
    print(f"{dst}: bridge copper drawn")


if __name__ == "__main__":
    main()
