#!/usr/bin/env python3
"""Baseline numbers for a Yellow Jacket .ork, read straight from OpenRocket 23.09 (headless, through JPype).

Prints the parts list with masses, the static margin of each flying configuration (full stack at liftoff, sustainer
stack after separation, booster alone), the motors, and a full two-stage flight with every stage switched on.

Usage: .venv/bin/python tools/openrocket/analyze.py yellow-jacket/openrocket/yellow-jacket.ork [--rail 1.0] [--wind 2.0] [--save out.ork]
"""
import argparse
import os
import sys

import jpype
import jpype.imports  # noqa: F401  (lets "from net.sf.openrocket ..." work)

OR_JAR = "/Applications/OpenRocket.app/Contents/Resources/app/OpenRocket.jar"
OR_JVM = "/Applications/OpenRocket.app/Contents/Resources/jre.bundle/Contents/Home/lib/server/libjvm.dylib"


def start_openrocket():
    jpype.startJVM(OR_JVM, "-Djava.awt.headless=true", classpath=[OR_JAR])
    from org.slf4j import LoggerFactory
    from ch.qos.logback.classic import Level
    LoggerFactory.getLogger("ROOT").setLevel(Level.ERROR)
    from net.sf.openrocket.startup import Application, GuiModule
    from net.sf.openrocket.plugin import PluginModule
    from com.google.inject import Guice
    gui = GuiModule()
    Application.setInjector(Guice.createInjector(gui, PluginModule()))
    gui.startLoader()
    for name in ("presetLoader", "motorLoader"):
        field = gui.getClass().getDeclaredField(name)
        field.setAccessible(True)
        field.get(gui).blockUntilLoaded()
    return Application


def walk(comp, depth=0):
    yield comp, depth
    for child in comp.getChildren():
        yield from walk(child, depth + 1)


def margin(config, mach=0.3, burnout=False):
    """(CG m, CP m, margin cal, mass kg) for the active stages of a configuration at zero angle of attack."""
    from net.sf.openrocket.aerodynamics import BarrowmanCalculator, FlightConditions
    from net.sf.openrocket.logging import WarningSet
    from net.sf.openrocket.masscalc import MassCalculator
    body = MassCalculator.calculateBurnout(config) if burnout else MassCalculator.calculateLaunch(config)
    cond = FlightConditions(config)
    cond.setMach(mach)
    cond.setAOA(0.0)
    cp = BarrowmanCalculator().getCP(config, cond, WarningSet())
    cg = body.getCM()
    return float(cg.x), float(cp.x), (float(cp.x) - float(cg.x)) / float(cond.getRefLength()), float(cg.weight), \
        float(cond.getRefLength())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("ork")
    p.add_argument("--rail", type=float, default=None, help="launch rail length, m (default: keep the file's)")
    p.add_argument("--wind", type=float, default=None, help="average wind, m/s (default: keep the file's)")
    p.add_argument("--save", default=None, help="write the all-stages-on document here")
    a = p.parse_args()

    start_openrocket()
    from java.io import File
    from net.sf.openrocket.file import GeneralRocketLoader, GeneralRocketSaver
    from net.sf.openrocket.rocketcomponent import AxialStage, MotorMount, RecoveryDevice
    from net.sf.openrocket.simulation import FlightDataType as T

    doc = GeneralRocketLoader(File(os.path.abspath(a.ork))).load()
    rocket = doc.getRocket()
    sim = doc.getSimulations()[0]
    fcid = sim.getFlightConfigurationId()
    config = rocket.getFlightConfiguration(fcid)
    stages = [c for c in rocket.getChildren() if isinstance(c, AxialStage)]

    print(f"== {os.path.basename(a.ork)}   rocket length {float(rocket.getLength())*1e3:.0f} mm")
    print("\n-- parts (mass as the file sets it; * = override) --")
    for comp, d in walk(rocket):
        if comp is rocket:
            continue
        m = float(comp.getOverrideMass()) if comp.isMassOverridden() else float(comp.getComponentMass())
        ov = "*" if comp.isMassOverridden() else " "
        extra = ""
        if isinstance(comp, MotorMount) and comp.isMotorMount():
            inst = comp.getMotorConfig(fcid)
            mot = inst.getMotor() if inst is not None else None
            if mot is not None:
                extra = f"   motor {mot.getDesignation()}"
        if isinstance(comp, RecoveryDevice):
            extra = f"   dia {float(comp.getDiameter())*1e3:.0f} mm  Cd {float(comp.getCD()):.2f}"
        print(f"{'  '*d}{str(comp.getName()):<30s} {m*1e3:7.1f} g{ov}  len {float(comp.getLength())*1e3:6.1f} mm  "
              f"front at {float(comp.getComponentLocations()[0].x)*1e3:7.1f} mm{extra}")

    print("\n-- motors --")
    for comp, _ in walk(rocket):
        if isinstance(comp, MotorMount) and comp.isMotorMount():
            inst = comp.getMotorConfig(fcid)
            mot = inst.getMotor() if inst is not None else None
            if mot is None:
                continue
            ts = [float(x) for x in mot.getTimePoints()]
            print(f"{str(comp.getStage().getName()):<12s} {mot.getManufacturer()} {str(mot.getDesignation()):<10s} "
                  f"{float(mot.getDiameter())*1e3:.0f} mm x {float(mot.getLength())*1e3:.0f} mm  "
                  f"I {float(mot.getTotalImpulseEstimate()):6.1f} Ns  avg {float(mot.getAverageThrustEstimate()):5.1f} N  "
                  f"max {float(mot.getMaxThrustEstimate()):5.1f} N  burn {ts[-1]:.2f} s  "
                  f"loaded {float(mot.getLaunchMass())*1e3:.0f} g  prop {(float(mot.getLaunchMass())-float(mot.getBurnoutMass()))*1e3:.0f} g"
                  f"   ignition {inst.getIgnitionEvent()} +{float(inst.getIgnitionDelay()):.1f} s")

    print("\n-- stages and events --")
    for i, st in enumerate(stages):
        sep = st.getSeparationConfigurations().get(fcid)
        print(f"stage {i} {str(st.getName()):<20s} active={config.isStageActive(i)}  separation {sep.getSeparationEvent()} "
              f"+{float(sep.getSeparationDelay()):.1f} s")
    for comp, _ in walk(rocket):
        if isinstance(comp, RecoveryDevice):
            dc = comp.getDeploymentConfigurations().get(fcid)
            print(f"  chute {str(comp.getName()):<18s} deploy {dc.getDeployEvent()} alt {float(dc.getDeployAltitude()):.0f} m "
                  f"+{float(dc.getDeployDelay()):.1f} s")

    # Static margins
    n = len(stages)
    config.setAllStages()
    print("\n-- static margin (Mach 0.3, AoA 0; calibers of the 58 mm body) --")
    for label, active, burn in [("full stack, liftoff", range(n), False),
                                ("full stack, booster burnout", range(n), "booster"),
                                ("sustainer stack, ignition", range(n - 1), False),
                                ("sustainer stack, burnout", range(n - 1), True),
                                ("booster alone, burnt out", [n - 1], True)]:
        config.setOnlyStage(n - 1)
        for i in range(n):
            config._setStageActive(i, i in active)
        if burn == "booster":
            # booster motor burnt, sustainer still loaded: compute burnout mass for both, then add the sustainer propellant
            cg_b, cp, m_b, mass_b, ref = margin(config, burnout=True)
            cg_l, _, _, mass_l, _ = margin(config, burnout=False)
            # sustainer propellant
            config.setOnlyStage(n - 2)
            for i in range(n):
                config._setStageActive(i, i in range(n - 1))
            _, _, _, ms_l, _ = margin(config, burnout=False)
            cg_sl = margin(config, burnout=False)[0]
            cg_sb, _, _, ms_b, _ = margin(config, burnout=True)
            prop = ms_l - ms_b
            prop_x = (cg_sl * ms_l - cg_sb * ms_b) / prop
            for i in range(n):
                config._setStageActive(i, True)
            mass = mass_b + prop
            cg = (cg_b * mass_b + prop_x * prop) / mass
            print(f"{label:<30s} mass {mass*1e3:6.0f} g  CG {cg*1e3:6.0f} mm  CP {cp*1e3:6.0f} mm  "
                  f"margin {(cp-cg)/ref:5.2f} cal")
            continue
        cg, cp, mg, mass, ref = margin(config, burnout=burn)
        print(f"{label:<30s} mass {mass*1e3:6.0f} g  CG {cg*1e3:6.0f} mm  CP {cp*1e3:6.0f} mm  margin {mg:5.2f} cal")
    config.setAllStages()

    # Full two-stage flight
    opts = sim.getOptions()
    if a.rail is not None:
        opts.setLaunchRodLength(a.rail)
    if a.wind is not None:
        opts.setWindSpeedAverage(a.wind)
    print(f"\n-- flight, all stages on (rail {float(opts.getLaunchRodLength()):.2f} m, wind "
          f"{float(opts.getWindSpeedAverage()):.1f} m/s, angle {float(opts.getLaunchRodAngle()):.1f} rad) --")
    sim.simulate()
    fd = sim.getSimulatedData()
    print(f"apogee {float(fd.getMaxAltitude()):.0f} m ({float(fd.getMaxAltitude())*3.28084:.0f} ft)  "
          f"max v {float(fd.getMaxVelocity()):.0f} m/s  max Mach {float(fd.getMaxMachNumber()):.3f}  "
          f"max accel {float(fd.getMaxAcceleration())/9.80665:.1f} g  rail exit {float(fd.getLaunchRodVelocity()):.1f} m/s  "
          f"ground hit {float(fd.getGroundHitVelocity()):.1f} m/s")
    for bi in range(fd.getBranchCount()):
        br = fd.getBranch(bi)
        t = [float(x) for x in br.get(T.TYPE_TIME)]
        alt = [float(x) for x in br.get(T.TYPE_ALTITUDE)]
        v = [float(x) for x in br.get(T.TYPE_VELOCITY_TOTAL)]
        vz = [float(x) for x in br.get(T.TYPE_VELOCITY_Z)]
        stab = [float(x) for x in br.get(T.TYPE_STABILITY)]
        zen = [float(x) for x in br.get(T.TYPE_ORIENTATION_THETA)]

        def at(tt):
            k = min(range(len(t)), key=lambda j: abs(t[j] - tt))
            return k
        print(f"\n branch '{br.getBranchName()}': max alt {max(alt):.0f} m, last t {t[-1]:.1f} s")
        for ev in br.getEvents():
            k = at(float(ev.getTime()))
            s = stab[k] if k < len(stab) else float('nan')
            print(f"   {float(ev.getTime()):7.2f} s  {str(ev.getType()):<26s} alt {alt[k]:6.0f} m  v {v[k]:6.1f} m/s  "
                  f"vz {vz[k]:6.1f}  margin {s:5.2f}  zenith {zen[k]*57.2958:5.1f} deg")
        # descent rate on the last chute: mean vz over the last 20% of the branch
        tail = [vz[j] for j in range(int(len(vz) * 0.8), len(vz))]
        if tail:
            print(f"   descent rate near landing {sum(tail)/len(tail):.1f} m/s")
        fin = [s for s in stab if s == s]
        if fin:
            print(f"   margin while flying: min {min(fin):.2f}  max {max(fin):.2f} cal")

    if a.save:
        GeneralRocketSaver().save(File(os.path.abspath(a.save)), doc)
        print(f"\nsaved {a.save}")


if __name__ == "__main__":
    main()
