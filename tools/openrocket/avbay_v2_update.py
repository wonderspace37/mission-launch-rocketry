#!/usr/bin/env python3
"""Put the av-bay v2 / nose cone v2 / chute swap into a Yellow Jacket .ork (OpenRocket 23.09, headless).

    .venv/bin/python tools/openrocket/avbay_v2_update.py IN.ork OUT.ork [--ballast 120]

What it changes (everything else is left as the file had it):
1. Nose cone: printed Von Karman, 190 mm + 55 mm shoulder, PETG-CF 83.5 g (printmass) with the cross-pin shock-cord
   tether (5/16" x 2" dowel). The 120 g nose ballast moves into the new nose's tip cavity (or --ballast grams).
2. Av bay: one 147 mm LOC coupler centred on the 40 mm collar (was 235 mm, 320 g lump), with every part as its own
   mass at its real position: bulkheads, rods, eye bolts, terminal blocks, sled, Blue Raven 2, 1S LiPo, RunCam,
   magnetic switches, boost, wiring, clear wrap.
3. Recovery: the 36" main moves from the upper-stage tube into the nose section (main bay, Raven "Main");
   the 18" drogue moves from the nose section down into the upper-stage tube (drogue bay, Raven "Apo", with the
   H100W's ejection charge as the backup). Deploy events are kept as the file has them.

4. Measured mass: the team weighed the upper stage (with parachute and loaded motor) at 729.43 g against the model's
   666 g. The +63.4 g is added to the upper stage, spread evenly over its length (--extra-upper, --extra-upper-at).

Masses marked EST are estimates; weigh the parts and edit MASSES.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import start_openrocket  # noqa: E402

# Av-bay frame: z (mm) from the middle of the collar, + toward the nose. Values: grams, z centre, length mm, type.
COUPLER_LEN = 147.0
COLLAR_LEN = 40.0
BULKHEAD_T = 6.4
MASSES = [
    # name,                                   g,     z_mm,   len_mm, type
    ("Sled v2 (PETG-CF, printmass)",          23.7,  -0.3,   126.0, "MASSCOMPONENT"),
    ("Blue Raven 2 (EST)",                    8.0,   -40.2,  45.7,  "FLIGHTCOMPUTER"),
    ("1S LiPo 1000 mAh (EST)",                22.0,  31.0,   50.0,  "BATTERY"),
    ("RunCam Thumb Pro W + SD + cable",       18.3,  10.0,   54.0,  "PAYLOAD"),
    ("Switch, arms Raven + camera (EST)",     3.0,   -8.0,   14.0,  "MASSCOMPONENT"),
    ("5 V boost + polyfuse",                  0.7,   -25.5,  13.0,  "MASSCOMPONENT"),
    ("Wiring + XT30 + heat shrink (EST)",     8.0,   0.0,    100.0, "MASSCOMPONENT"),
    ("Threaded rods 2x #8-32 + nuts (EST)",   38.0,  0.0,    175.0, "MASSCOMPONENT"),
    ("Coupler bulkhead disk, fore (EST)",     8.7,   70.3,   6.4,   "RECOVERYHARDWARE"),
    ("Coupler bulkhead disk, aft (EST)",      8.7,   -70.3,  6.4,   "RECOVERYHARDWARE"),
    ("Tube bulkhead disk, fore (EST)",        10.0,  76.7,   6.4,   "RECOVERYHARDWARE"),
    ("Tube bulkhead disk, aft (EST)",         10.0,  -76.7,  6.4,   "RECOVERYHARDWARE"),
    ("Eye bolt fore + nut (EST)",             15.0,  85.0,   15.0,  "RECOVERYHARDWARE"),
    ("Eye bolt aft + nut (EST)",              15.0,  -85.0,  15.0,  "RECOVERYHARDWARE"),
    ("Terminals + 2 charge wells, fore (EST)", 9.5,  82.0,   8.0,   "DEPLOYMENTCHARGE"),
    ("Terminals + 2 charge wells, aft (EST)", 9.5,   -82.0,  8.0,   "DEPLOYMENTCHARGE"),
    ("Clear wrap over collar (EST)",          5.0,   0.0,    40.0,  "MASSCOMPONENT"),
]
COLLAR_MASS = 16.0      # printed collar, EST
NOSE_MASS = 83.5        # printmass, PETG-CF 5 walls 15% gyroid, tether band included
NOSE_CG_FROM_TIP = 0.159
PIN_MASS = 19.6         # 5/16" x 2" steel dowel
TETHER_HW = 12.0        # Kevlar loop + quick link at the pin, EST
PIN_FROM_TIP = 0.245 - 0.022


def find(rocket, name):
    stack = [rocket]
    while stack:
        c = stack.pop()
        if str(c.getName()) == name:
            return c
        stack.extend(list(c.getChildren()))
    raise SystemExit(f"component not found: {name}")


def add_measured_upper(rocket, grams, at="spread"):
    """The upper stage weighed 729.43 g against the model's 666 g; add the difference to the 2nd stage."""
    from net.sf.openrocket.rocketcomponent import MassComponent
    from net.sf.openrocket.rocketcomponent.position import AxialMethod
    upper = [c for c in find(rocket, "2nd Stage").getChildren()][0]   # the stage's first Blue Tube
    m = MassComponent()
    m.setName(f"Measured minus model, upper stage (+{grams:.1f} g)")
    m.setComponentMass(grams / 1000)
    m.setRadius(0.012)
    m.setAxialMethod(AxialMethod.TOP)
    if at == "spread":
        m.setLength(0.528)                                # whole 2nd stage: drogue bay + PETG tube + fin can
        m.setAxialOffset(0.0)
    else:
        m.setLength(0.150)
        m.setAxialOffset(0.528 - 0.150)                   # all of it in the 150 mm fin can at the aft end
    upper.addChild(m)


def apply_v2(rocket, ballast=None):
    from net.sf.openrocket.rocketcomponent import MassComponent, Transition
    from net.sf.openrocket.rocketcomponent.position import AxialMethod

    # ---- 1. nose cone
    nose = find(rocket, "Nose Cone")
    nose.setName("Nose Cone v2 (printed PETG-CF, Von Karman, pin tether)")
    nose.setShapeType(Transition.Shape.HAACK)
    nose.setShapeParameter(0.0)
    nose.setLength(0.190)
    nose.setAftRadiusAutomatic(True)
    nose.setAftShoulderRadius(0.0270)
    nose.setAftShoulderLength(0.055)
    nose.setAftShoulderThickness(0.002)
    nose.setThickness(0.002)
    nose.setAftShoulderCapped(False)
    nose.setMassOverridden(True)
    nose.setOverrideMass(NOSE_MASS / 1000)
    nose.setCGOverridden(True)
    nose.setOverrideCGX(NOSE_CG_FROM_TIP)
    nose_tube = find(rocket, "Nose Cone Body Tube")
    nose_tube.setName("Main bay (Blue Tube)")
    ballast_c = [c for c in nose_tube.getChildren() if str(c.getName()) == "Mass Component"][0]   # 120 g ballast
    nose_tube.removeChild(ballast_c)
    nose.addChild(ballast_c)
    ballast_c.setName("Nose ballast (lead shot + epoxy in the tip)")
    ballast_c.setAxialMethod(AxialMethod.TOP)
    ballast_c.setAxialOffset(0.030)
    ballast_c.setLength(0.045)
    if ballast is not None:
        ballast_c.setComponentMass(ballast / 1000)
    for nm, g, off in (("Tether pin 5/16 x 2 in dowel", PIN_MASS, PIN_FROM_TIP - 0.004),
                       ("Kevlar loop + quick link at the pin (EST)", TETHER_HW, PIN_FROM_TIP - 0.004)):
        m = MassComponent()
        m.setName(nm)
        m.setComponentMass(g / 1000)
        m.setLength(0.008)
        m.setRadius(0.012)
        m.setAxialMethod(AxialMethod.TOP)
        m.setAxialOffset(off)
        m.setMassComponentType(MassComponent.MassComponentType.RECOVERYHARDWARE)
        nose.addChild(m)

    # ---- 2. av bay
    collar = find(rocket, "Avionics Bay Window")
    collar.setName("Mid collar (camera window, clear wrap)")
    collar.setMassOverridden(True)
    collar.setOverrideMass(COLLAR_MASS / 1000)
    coupler = [c for c in collar.getChildren() if c.getClass().getSimpleName() == "TubeCoupler"][0]
    coupler.setName("Av bay coupler (LOC 54 mm x 147 mm)")
    coupler.setLength(COUPLER_LEN / 1000)
    coupler.setOuterRadius(0.0270)
    coupler.setThickness(0.00185)
    coupler.setMassOverridden(False)
    coupler.setAxialMethod(AxialMethod.TOP)
    coupler.setAxialOffset(-(COUPLER_LEN - COLLAR_LEN) / 2 / 1000)
    for c in list(coupler.getChildren()):
        coupler.removeChild(c)
    top_z = COUPLER_LEN / 2        # coupler top in the av-bay frame
    for name, g, z, ln, typ in MASSES:
        m = MassComponent()
        m.setName(name)
        m.setComponentMass(g / 1000)
        m.setLength(ln / 1000)
        m.setRadius(0.010)
        m.setAxialMethod(AxialMethod.TOP)
        m.setAxialOffset((top_z - z - ln / 2) / 1000)     # front of the mass, from the coupler top
        m.setMassComponentType(getattr(MassComponent.MassComponentType, typ))
        coupler.addChild(m)

    # ---- 3. chute swap
    main = find(rocket, "Main Chute")
    drogue = find(rocket, "Apogee Chute")
    main.getParent().removeChild(main)
    drogue.getParent().removeChild(drogue)
    nose_tube.addChild(main)
    main.setAxialMethod(AxialMethod.TOP)
    main.setAxialOffset(0.060)                              # just below the nose shoulder and tether pin
    main.setName("Main Chute 36in (main bay, Raven Main)")
    upper = [c for c in find(rocket, "2nd Stage").getChildren()][0]   # the stage's first Blue Tube
    upper.setName("Drogue bay (Blue Tube)")
    upper.addChild(drogue)
    drogue.setAxialMethod(AxialMethod.TOP)
    drogue.setAxialOffset(0.065)                            # below the av-bay aft bulkhead
    drogue.setName("Drogue 18in (drogue bay, Raven Apo + motor backup)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("inp")
    p.add_argument("out")
    p.add_argument("--ballast", type=float, default=None, help="nose ballast grams (default: keep the file's)")
    p.add_argument("--extra-upper", type=float, default=63.43, help="measured-minus-model upper stage mass, g")
    p.add_argument("--extra-upper-at", choices=["spread", "fincan"], default="spread",
                   help="where the extra upper-stage mass sits: spread over the stage, or all in the fin can")
    a = p.parse_args()
    start_openrocket()
    from java.io import File
    from net.sf.openrocket.file import GeneralRocketLoader, GeneralRocketSaver
    doc = GeneralRocketLoader(File(os.path.abspath(a.inp))).load()
    rocket = doc.getRocket()
    apply_v2(rocket, a.ballast)
    if a.extra_upper:
        add_measured_upper(rocket, a.extra_upper, a.extra_upper_at)
    rocket.enableEvents()
    GeneralRocketSaver().save(File(os.path.abspath(a.out)), doc)
    print(f"saved {a.out}")


if __name__ == "__main__":
    main()
