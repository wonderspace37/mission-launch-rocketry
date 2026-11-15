#!/usr/bin/env python3
"""Compare the saved Yellow Jacket .ork with the av-bay v2 / nose cone v2 design, including the measured mass.

    .venv/bin/python tools/openrocket/compare_v2.py yellow-jacket/openrocket/yellow-jacket.ork [--out results.json]

Variants (all with every stage switched on, 6 ft rail, the file's own launch site, fixed turbulence seed):
  A  file as saved (model masses)
  B  file + the measured +63.4 g, spread over the upper stage
  C  v2 + 63.4 g spread, 120 g nose ballast           <- proposed
  D  v2 + 63.4 g all in the upper fin can              (worst case for stability)
  E  v2 + 63.4 g spread, 60 g ballast
  F  v2 + 63.4 g spread, no ballast
  G  C with the main at 700 ft (Blue Raven default) instead of the file's 1,500 ft
"""
import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import margin, start_openrocket  # noqa: E402
from avbay_v2_update import add_measured_upper, apply_v2, find  # noqa: E402
from sweep import fly, setup  # noqa: E402

MEASURED_EXTRA = 729.43 - 666.0


def static(doc):
    rocket = doc.getRocket()
    cfg = rocket.getFlightConfiguration(doc.getSimulations()[0].getFlightConfigurationId())
    n = cfg.getStageCount()

    def st(active):
        for i in range(n):
            cfg._setStageActive(i, i in active)
        cg, cp, mg, mass, _ = margin(cfg)
        cfg.setAllStages()
        return round(mg, 2), round(mass * 1000)
    return st(range(n)), st(range(n - 1))


def descent(m):
    """Drogue and main descent rates of the sustainer branch, from the last simulation run."""
    from net.sf.openrocket.simulation import FlightDataType as T
    br = m["sim"].getSimulatedData().getBranch(0)
    t = [float(x) for x in br.get(T.TYPE_TIME)]
    vz = [float(x) for x in br.get(T.TYPE_VELOCITY_Z)]
    dep = sorted(float(e.getTime()) for e in br.getEvents() if str(e.getType().name()) == "RECOVERY_DEVICE_DEPLOYMENT")
    apo = [float(e.getTime()) for e in br.getEvents() if str(e.getType().name()) == "APOGEE"][0]
    t_main = dep[-1] if len(dep) > 1 else None

    def mean_vz(t0, t1):
        v = [abs(b) for a, b in zip(t, vz) if t0 <= a <= t1]
        return round(sum(v) / len(v), 1) if v else None
    drogue = mean_vz(apo + 4, (t_main or t[-1]) - 1)
    main = mean_vz(t_main + 4, t[-1]) if t_main else None
    return drogue, main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ork")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    start_openrocket()
    from java.io import File
    from net.sf.openrocket.file import GeneralRocketLoader, GeneralRocketSaver

    variants = [
        ("A", "file as saved", dict(v2=False, extra=0)),
        ("B", "file + measured 63.4 g", dict(v2=False, extra=MEASURED_EXTRA)),
        ("C", "v2, 120 g ballast (proposed)", dict(v2=True, extra=MEASURED_EXTRA)),
        ("D", "v2, extra mass in fin can", dict(v2=True, extra=MEASURED_EXTRA, at="fincan")),
        ("E", "v2, 60 g ballast", dict(v2=True, extra=MEASURED_EXTRA, ballast=60)),
        ("F", "v2, no ballast", dict(v2=True, extra=MEASURED_EXTRA, ballast=0)),
        ("G", "v2, main at 700 ft", dict(v2=True, extra=MEASURED_EXTRA, main_m=213.36)),
    ]
    tmp = tempfile.mkdtemp(prefix="yj-compare-")
    rows = []
    for key, label, o in variants:
        doc = GeneralRocketLoader(File(os.path.abspath(a.ork))).load()
        rocket = doc.getRocket()
        if o.get("v2"):
            apply_v2(rocket, o.get("ballast"))
        if o.get("extra"):
            add_measured_upper(rocket, o["extra"], o.get("at", "spread"))
        if o.get("main_m"):
            fcid = doc.getSimulations()[0].getFlightConfigurationId()
            main_chute = find(rocket, "Main Chute 36in (main bay, Raven Main)")
            main_chute.getDeploymentConfigurations().get(fcid).setDeployAltitude(o["main_m"])
        rocket.enableEvents()
        path = os.path.join(tmp, f"{key}.ork")
        GeneralRocketSaver().save(File(path), doc)
        m = setup(path)                                     # reload: margins and flights both use the saved file
        (stack_m, stack_g), (sus_m, sus_g) = static(m["doc"])
        r2 = fly(m, wind=2.0, rail=1.83)
        r4 = fly(m, wind=4.0, rail=1.83)
        d_rate, m_rate = descent(m)
        row = dict(key=key, label=label, liftoff_g=stack_g, sustainer_g=sus_g, stack_static=stack_m,
                   sustainer_static=sus_m, off_rail_2=round(r2["off_rail_margin"], 2),
                   off_rail_4=round(r4["off_rail_margin"], 2), min_sus_2=round(r2["min_sus"], 2),
                   apogee_ft=round(r2["apogee"] * 3.28084), mach=round(r2["mach"], 3),
                   drogue_ms=d_rate, main_ms=m_rate, drift_4ms_m=round(r4["drift"]))
        rows.append(row)
        print(f"{key} {label:<30s} liftoff {stack_g:5d} g  stack {stack_m:5.2f}  sus {sus_m:5.2f}  "
              f"off-rail 2/4 m/s {row['off_rail_2']:5.2f}/{row['off_rail_4']:5.2f}  min sus {row['min_sus_2']:5.2f}  "
              f"apogee {row['apogee_ft']:5d} ft  drogue {d_rate} m/s  main {m_rate} m/s  drift@4 {row['drift_4ms_m']} m",
              flush=True)
    if a.out:
        with open(a.out, "w") as f:
            json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
