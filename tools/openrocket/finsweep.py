#!/usr/bin/env python3
"""How big the fins have to be: static margins and off-rail margin in wind vs booster and sustainer fin span.

The fins keep the file's shape (a triangle: root chord 60 mm, swept leading edge, tip at the trailing edge) and only the
span changes. Extra fin area is charged as solid PETG (5 mm, 1.25 g/cm^3) on top of the file's fin masses.

Usage: .venv/bin/python tools/openrocket/finsweep.py yellow-jacket/openrocket/yellow-jacket.ork
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import margin, start_openrocket  # noqa: E402
from sweep import fly, setup  # noqa: E402

PETG = 1250.0
T = 0.005


def fins_of(rocket):
    from net.sf.openrocket.rocketcomponent import FreeformFinSet
    out, stack = [], [rocket]
    while stack:
        c = stack.pop()
        if isinstance(c, FreeformFinSet):
            out.append(c)
        stack.extend(list(c.getChildren()))
    return out


def set_span(fin, span, base):
    from net.sf.openrocket.util import Coordinate
    from jpype import JArray
    root = base["root"]
    pts = JArray(Coordinate)([Coordinate(0.0, 0.0), Coordinate(root, span), Coordinate(root, 0.0)])
    fin.setPoints(pts)
    extra = max(0.0, 0.5 * root * (span - base["span"])) * T * PETG * 4
    fin.setMassOverridden(True)
    fin.setOverrideMass(base["mass"] + extra)


def main():
    start_openrocket()
    m = setup(sys.argv[1])
    rocket, fcid = m["rocket"], m["fcid"]
    config = rocket.getFlightConfiguration(fcid)
    fins = fins_of(rocket)
    bfin = next(f for f in fins if f.getStage() == m["booster"])
    sfin = next(f for f in fins if f.getStage() != m["booster"])

    def base(f):
        pts = list(f.getFinPoints())
        return {"root": float(pts[-1].x), "span": max(float(p.y) for p in pts), "mass": float(f.getOverrideMass())}
    bb, sb = base(bfin), base(sfin)
    print(f"file: booster fins root {bb['root']*1e3:.0f} span {bb['span']*1e3:.1f} mm; "
          f"sustainer fins root {sb['root']*1e3:.0f} span {sb['span']*1e3:.1f} mm")

    n = len([1 for _ in range(config.getStageCount())])

    def static(active):
        for i in range(n):
            config._setStageActive(i, i in active)
        out = margin(config)[2]
        config.setAllStages()
        return out

    print("\n booster_span  sus_span  static_stack  static_sus_ign  off_rail_2ms  off_rail_4ms  off_rail_6ms  apogee_ft"
          "   (rail 1.83 m)")
    for s_span in (sb["span"], 0.045, 0.055):
        set_span(sfin, s_span, sb)
        for b_span in (bb["span"], 0.035, 0.045, 0.055, 0.065, 0.075):
            set_span(bfin, b_span, bb)
            st = static(range(n))
            ss = static(range(n - 1))
            r = [fly(m, wind=w, rail=1.83) for w in (2.0, 4.0, 6.0)]
            print(f" {b_span*1e3:9.1f}  {s_span*1e3:8.1f}  {st:10.2f}  {ss:12.2f}  {r[0]['off_rail_margin']:10.2f}  "
                  f"{r[1]['off_rail_margin']:11.2f}  {r[2]['off_rail_margin']:11.2f}  {r[0]['apogee']*3.28084:9.0f}")


if __name__ == "__main__":
    main()
