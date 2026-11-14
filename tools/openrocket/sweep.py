#!/usr/bin/env python3
"""Sensitivity sweeps on a Yellow Jacket .ork, all stages on: staging timer, wind, rail length.

Every run uses the file's own first simulation (ISA, its launch site) with a fixed random seed so the turbulence is the
same from run to run. The staging timer moves the sustainer ignition and the booster separation together (the file
ties both to launch + 4.0 s); the booster chute keeps deploying at separation, as in the file.

Usage: .venv/bin/python tools/openrocket/sweep.py yellow-jacket/openrocket/yellow-jacket.ork
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import start_openrocket  # noqa: E402


def setup(path):
    from java.io import File
    from net.sf.openrocket.file import GeneralRocketLoader
    from net.sf.openrocket.rocketcomponent import AxialStage, MotorMount, RecoveryDevice
    doc = GeneralRocketLoader(File(os.path.abspath(path))).load()
    rocket = doc.getRocket()
    sim = doc.getSimulations()[0]
    fcid = sim.getFlightConfigurationId()
    rocket.getFlightConfiguration(fcid).setAllStages()
    stages = [c for c in rocket.getChildren() if isinstance(c, AxialStage)]
    mounts, chutes = [], []
    stack = [rocket]
    while stack:
        c = stack.pop()
        if isinstance(c, MotorMount) and c.isMotorMount() and c.getMotorConfig(fcid).getMotor() is not None:
            mounts.append(c)
        if isinstance(c, RecoveryDevice):
            chutes.append(c)
        stack.extend(list(c.getChildren()))
    sus = next(m for m in mounts if m.getStage() != stages[-1])
    booster_chute = next(c for c in chutes if c.getStage() == stages[-1])
    return dict(doc=doc, rocket=rocket, sim=sim, fcid=fcid, booster=stages[-1], sus=sus, bchute=booster_chute)


def set_timer(m, t):
    m["sus"].getMotorConfig(m["fcid"]).setIgnitionDelay(t)
    m["booster"].getSeparationConfigurations().get(m["fcid"]).setSeparationDelay(t)
    m["bchute"].getDeploymentConfigurations().get(m["fcid"]).setDeployDelay(t)


def fly(m, wind=None, rail=None, seed=12345):
    from net.sf.openrocket.simulation import FlightDataType as T
    from net.sf.openrocket.simulation import FlightEvent
    o = m["sim"].getOptions()
    o.setRandomSeed(seed)
    if wind is not None:
        o.setWindSpeedAverage(wind)
    if rail is not None:
        o.setLaunchRodLength(rail)
    m["sim"].simulate()
    fd = m["sim"].getSimulatedData()
    br = fd.getBranch(0)
    col = {k: [float(x) for x in br.get(getattr(T, k))] for k in
           ("TYPE_TIME", "TYPE_ALTITUDE", "TYPE_VELOCITY_TOTAL", "TYPE_STABILITY", "TYPE_ORIENTATION_THETA",
            "TYPE_POSITION_X", "TYPE_POSITION_Y", "TYPE_MACH_NUMBER")}
    t = col["TYPE_TIME"]
    ev = {}
    for e in br.getEvents():
        ev.setdefault(str(e.getType().name()), []).append(float(e.getTime()))

    def idx(tt):
        return min(range(len(t)), key=lambda j: abs(t[j] - tt))

    rod = ev["LAUNCHROD"][0]
    burn = ev["BURNOUT"]
    ign = ev["IGNITION"]
    sus_ign = max(ign)
    apo = ev["APOGEE"][0]
    k_ign = idx(sus_ign)

    def min_margin(t0, t1):
        vals = [s for tt, s in zip(t, col["TYPE_STABILITY"]) if t0 <= tt <= t1 and s == s]
        return min(vals) if vals else float("nan")

    first = next((s for tt, s in zip(t, col["TYPE_STABILITY"]) if tt >= rod and s == s), float("nan"))
    land_x, land_y = col["TYPE_POSITION_X"][-1], col["TYPE_POSITION_Y"][-1]
    return dict(
        apogee=float(fd.getMaxAltitude()), vmax=float(fd.getMaxVelocity()), mach=float(fd.getMaxMachNumber()),
        rail_v=float(fd.getLaunchRodVelocity()), off_rail_margin=first,
        min_boost=min_margin(rod, sus_ign), min_sus=min_margin(sus_ign, apo - 2.0),
        ign_alt=col["TYPE_ALTITUDE"][k_ign], ign_v=col["TYPE_VELOCITY_TOTAL"][k_ign],
        ign_tilt=90 - col["TYPE_ORIENTATION_THETA"][k_ign] * 57.2958, t_apo=apo, booster_burnout=min(burn),
        drift=(land_x ** 2 + land_y ** 2) ** 0.5)


def main():
    path = sys.argv[1]
    start_openrocket()
    m = setup(path)

    print("== staging timer (sustainer ignition = separation = booster chute, seconds after launch); rail 1.0 m, wind 2 m/s")
    print(" timer  apogee_m  apogee_ft  ign_alt  ign_v  ign_tilt  max_v  Mach   min_margin_boost  min_margin_sus")
    for tm in (1.2, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0):
        set_timer(m, tm)
        r = fly(m, wind=2.0, rail=1.0)
        print(f" {tm:5.1f}  {r['apogee']:7.0f}  {r['apogee']*3.28084:8.0f}  {r['ign_alt']:6.0f}  {r['ign_v']:5.1f}  "
              f"{r['ign_tilt']:6.1f}  {r['vmax']:6.1f}  {r['mach']:.3f}  {r['min_boost']:8.2f}  {r['min_sus']:13.2f}")

    set_timer(m, 4.0)
    print("\n== wind x rail, timer 4.0 s (as the file has it)")
    print(" rail_m  wind  rail_v  off_rail_margin  min_margin_boost  ign_tilt  apogee_ft  landing_drift_m")
    for rail in (1.0, 1.83, 2.44):
        for wind in (0.0, 2.0, 4.0, 6.0, 8.0):
            r = fly(m, wind=wind, rail=rail)
            print(f" {rail:5.2f}  {wind:4.1f}  {r['rail_v']:5.1f}  {r['off_rail_margin']:10.2f}  {r['min_boost']:12.2f}  "
                  f"{r['ign_tilt']:7.1f}  {r['apogee']*3.28084:8.0f}  {r['drift']:10.0f}")


if __name__ == "__main__":
    main()
