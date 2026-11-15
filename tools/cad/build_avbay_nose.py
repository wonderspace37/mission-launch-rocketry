#!/usr/bin/env python3
"""Yellow Jacket av-bay v2 sled and printed nose cone v2, built headless in FreeCAD 1.x.

    /Applications/FreeCAD.app/Contents/Resources/bin/python tools/cad/build_avbay_nose.py

Writes, all in mm:
  yellow-jacket/cad/nose-cone-v2/  nose-cone-v2.step/.stl, nose-bulkhead-v2.step/.stl, previews
  yellow-jacket/cad/avbay-v2/      sled-v2.step/.stl, avbay-v2-layout.step (sled + dummy parts in the coupler),
                                   fit.json (clearances), previews

Measure your own tubes and parts and edit the AIRFRAME / PARTS blocks before printing; the defaults come from the
club's parts list and the vendors' drawings, not from calipers.

Frames:
  nose: print frame. Shoulder base at z = 0, tip up (+z). Prints with no supports.
  av bay: z along the rocket axis, z = 0 at the middle of the 40 mm collar, +z toward the nose.
          The sled plate lies in the x-z plane; +y is the camera / window side, -y the shaded side.
"""
import json
import math
import os
import sys

sys.path.append("/Applications/FreeCAD.app/Contents/Resources/lib")
import FreeCAD  # noqa: E402  (import before Part/Mesh or Python segfaults)
import Part  # noqa: E402
import MeshPart  # noqa: E402
from FreeCAD import Vector as V  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_NOSE = os.path.join(REPO, "yellow-jacket", "cad", "nose-cone-v2")
OUT_BAY = os.path.join(REPO, "yellow-jacket", "cad", "avbay-v2")

# ---- AIRFRAME (measure these) ------------------------------------------------------------------------------------
BODY_OD = 57.4        # Blue Tube outer diameter (parts list: 57.4; ARR catalog 57.76)
BODY_ID = 54.4        # Blue Tube inner diameter (the 54.2 mm tube bulkhead disk slides in)
COUPLER_OD = 54.0     # LOC 54 mm coupler (parts list)
COUPLER_ID = 50.3     # = the 50.3 mm coupler bulkhead disk that fits inside it
COUPLER_LEN = 147.0   # one LOC coupler as bought
BULKHEAD_T = 6.4      # each plywood bulkhead disk (coupler disk inside + tube disk outside, at each end)
COLLAR_LEN = 40.0     # the mid collar / switch band the clear sheet wraps around

# ---- NOSE CONE ---------------------------------------------------------------------------------------------------
NOSE_LEN = 190.0      # 3.3 calibers, Von Karman (LD-Haack). Nose + shoulder must stay under 250 mm (X1C height)
HAACK_C = 0.0         # 0 = Von Karman, 1/3 = LV-Haack
NOSE_WALL = 2.0       # normal wall thickness
TIP_SOLID = 25.0      # solid tip length (fill the cavity tip with ballast if needed)
SHOULDER_LEN = 55.0   # ~1 caliber
SHOULDER_CLEAR = 0.2  # radial clearance to BODY_ID
SHOULDER_WALL = 2.0
# Shock-cord tether: a hardened 5/16" x 2" dowel pin across the shoulder, through a thickened internal band.
# Loop the Kevlar (or a quick link) around the pin, push the pin through both holes, slide the shoulder into the
# tube: the tube wall then traps the pin ends. No glue joint in the load path. Print in PETG-CF, tip up.
PIN_D = 7.94          # 5/16" dowel; 50.8 mm long, so its ends sit ~1.6 mm under the shoulder surface
PIN_HOLE = 8.1        # bearing (aft) half round, forward half pointed (teardrop) so it prints without supports
PIN_Z = 22.0          # pin centre above the shoulder's open end
BAND_R = 21.0         # band inner radius (shoulder wall 2 mm + band 4 mm = 6 mm of PETG-CF around the pin)
BAND_Z = (10.0, 34.0) # full-thickness band; 45 degree chamfers below and above

# ---- SLED --------------------------------------------------------------------------------------------------------
SLED_LEN = 126.0      # fits between the bulkheads with 4 mm to spare
PLATE_T = 3.0
PLATE_TOP_Y = -3.0    # camera-side face of the plate; lowered so the lens block clears the coupler wall
PLATE_HALF_W = 15.0
ROD_X = 19.0          # threaded rods (#8-32 or M4) at x = +-ROD_X, through both bulkheads
ROD_D = 4.17          # #8-32 major diameter (M4: 4.0)
BOSS_OD = 9.0
ROD_HOLE = 4.6

# ---- PARTS (dummy blocks for the fit check; vendor dimensions) ---------------------------------------------------
CAM_L, CAM_W, CAM_H_LENS, CAM_H_BODY, CAM_LENS_BLOCK = 54.0, 21.0, 24.5, 13.0, 20.0   # RunCam Thumb Pro W drawing
RAVEN_L, RAVEN_W, RAVEN_PCB, RAVEN_TALL = 45.7, 20.3, 1.6, 10.0   # Blue Raven 2 = Raven4 footprint 1.8" x 0.8"
RAVEN_STANDOFF = 4.0  # keeps the baro sensor (underside) off the plate
RAVEN_HOLES = [(4.0, 11.7), (17.0, 41.6)]   # (across, along) from the terminal-block corner; MEASURE your board
BATT = (50.0, 20.0, 10.0)   # 1S 1000 mAh "102050" LiPo (length, width, thickness)
SWITCH = (19.0, 14.0, 6.0)  # one switch bay: Featherweight Magnetic Switch 0.75" x 0.55", or a rocketry screw switch
BOOST = (13.1, 8.1, 3.0)    # Pololu U3V16F5 5 V step-up

# Positions along the sled (z ranges, av-bay frame)
CAM_Z0 = -CAM_LENS_BLOCK / 2          # lens block centred on the collar (z = 0)
RAVEN_Z0 = -63.0                      # terminal-block end of the Raven, toward the aft (drogue) bulkhead
SW_Z0 = -15.0                         # shaded side, under the collar: screw-switch access hole at z = -5.5
BATT_Z0 = 6.0
BOOST_Z0 = -32.0


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl_z(r, z0, z1, x=0.0, y=0.0):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0), V(0, 0, 1))


def cyl_y(r, y0, y1, x=0.0, z=0.0):
    return Part.makeCylinder(r, y1 - y0, V(x, y0, z), V(0, 1, 0))


def export(shape, path_noext, stl=True):
    shape.exportStep(path_noext + ".step")
    if stl:
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.03, AngularDeflection=0.15, Relative=False)
        mesh.write(path_noext + ".stl")


# =============================================================================================== NOSE CONE
def haack_r(s, L, R, C=HAACK_C):
    """Radius at distance s from the tip."""
    s = min(max(s, 0.0), L)
    th = math.acos(1 - 2 * s / L)
    return R / math.sqrt(math.pi) * math.sqrt(max(th - math.sin(2 * th) / 2 + C * math.sin(th) ** 3, 0.0))


def build_nose():
    R = BODY_OD / 2
    rs = BODY_ID / 2 - SHOULDER_CLEAR          # shoulder outer radius
    ri_sh = rs - SHOULDER_WALL                  # shoulder inner radius
    SH, L = SHOULDER_LEN, NOSE_LEN
    z_tip = SH + L
    ch = R - rs                                 # 45 degree chamfer from shoulder up to full diameter

    def r_out(z):                               # outer radius at height z (nose region)
        return haack_r(z_tip - z, L, R)

    def slope(z, h=0.05):
        return abs(r_out(z + h) - r_out(z - h)) / (2 * h)

    def r_in(z):
        return r_out(z) - NOSE_WALL / math.cos(math.atan(slope(z)))

    z_c = SH + ch                                # top of the chamfer
    z_solid = z_tip - TIP_SOLID
    # outer curve, base -> tip, clustered toward the tip
    n = 160
    outer = []
    for k in range(n + 1):
        u = k / n
        s = (L - ch) * (1 - u) ** 2 + 0.3       # distance from tip, from L-ch down to 0.3 mm
        z = z_tip - s
        outer.append(V(r_out(z), 0, z))
    outer[0] = V(r_out(z_c), 0, z_c)
    # inner curve, z_solid -> chamfer top
    inner = []
    for k in range(n + 1):
        z = z_solid - (z_solid - z_c) * (k / n) ** 1.3
        inner.append(V(r_in(z), 0, z))
    r_ceiling = inner[0].x
    apex = V(0, 0, z_solid + r_ceiling)          # 45 degree cone ceiling: prints without supports
    assert apex.z < z_tip - 1.0 and r_out(apex.z) > NOSE_WALL, "tip too thin for the cavity ceiling"
    e = []
    e.append(Part.LineSegment(V(ri_sh, 0, 0), V(rs, 0, 0)).toShape())
    e.append(Part.LineSegment(V(rs, 0, 0), V(rs, 0, SH)).toShape())
    e.append(Part.LineSegment(V(rs, 0, SH), outer[0]).toShape())                 # outer chamfer
    bs = Part.BSplineCurve()
    bs.interpolate(outer)
    e.append(bs.toShape())
    e.append(Part.LineSegment(outer[-1], V(0, 0, outer[-1].z)).toShape())       # 0.3 mm flat at the tip
    e.append(Part.LineSegment(V(0, 0, outer[-1].z), apex).toShape())            # along the axis (solid tip)
    e.append(Part.LineSegment(apex, inner[0]).toShape())                        # cavity ceiling cone
    bi = Part.BSplineCurve()
    bi.interpolate(inner)
    e.append(bi.toShape())
    e.append(Part.LineSegment(inner[-1], V(ri_sh, 0, SH)).toShape())            # inner chamfer (45 deg)
    # shoulder bore with the tether band: 45 deg in, full band, 45 deg out (prints without supports)
    b0, b1 = BAND_Z
    dr = ri_sh - BAND_R
    bore = [V(ri_sh, 0, SH), V(ri_sh, 0, b1 + dr), V(BAND_R, 0, b1), V(BAND_R, 0, b0), V(ri_sh, 0, b0 - dr), V(ri_sh, 0, 0)]
    for p0, p1 in zip(bore[:-1], bore[1:]):
        e.append(Part.LineSegment(p0, p1).toShape())
    wire = Part.Wire(Part.__sortEdges__(e))
    face = Part.Face(wire)
    nose = face.revolve(V(0, 0, 0), V(0, 0, 1), 360)
    nose = Part.Solid(Part.Shell(nose.Faces)) if nose.ShapeType != "Solid" else nose

    # teardrop cross hole for the dowel pin, along x: round on the aft (loaded) half, 45 deg point forward
    r = PIN_HOLE / 2
    span = 2 * rs + 2
    hole = Part.makeCylinder(r, span, V(-span / 2, 0, PIN_Z), V(1, 0, 0))
    d = r * math.sqrt(2)
    sq = Part.makePolygon([V(-span / 2, 0, PIN_Z + d), V(-span / 2, d, PIN_Z), V(-span / 2, 0, PIN_Z - d),
                           V(-span / 2, -d, PIN_Z), V(-span / 2, 0, PIN_Z + d)])
    roof = Part.Face(sq).extrude(V(span, 0, 0)).common(box(-span, span, -span, span, PIN_Z, PIN_Z + 2 * d))
    nose = nose.cut(hole.fuse(roof)).removeSplitter()

    info = {
        "length_total_mm": round(z_tip, 1), "nose_len_mm": L, "shoulder_len_mm": SH, "body_od_mm": BODY_OD,
        "shoulder_od_mm": round(2 * rs, 2), "shoulder_id_mm": round(2 * ri_sh, 2), "wall_mm": NOSE_WALL,
        "shape": "Von Karman (LD-Haack)" if HAACK_C == 0 else f"Haack C={HAACK_C}",
        "fineness": round(L / BODY_OD, 2), "tip_solid_mm": TIP_SOLID,
        "cavity_ceiling_radius_mm": round(r_ceiling, 1),
        "tether": {"pin": "5/16 in x 2 in hardened dowel", "pin_hole_mm": PIN_HOLE, "pin_z_from_shoulder_end_mm": PIN_Z,
                   "band_z_mm": list(BAND_Z), "band_inner_dia_mm": 2 * BAND_R,
                   "material_around_pin_mm": round(rs - BAND_R, 1),
                   "pin_end_depth_below_surface_mm": round((2 * rs - 50.8) / 2, 2)},
        "nose_volume_cm3": round(nose.Volume / 1000, 2), "nose_valid": nose.isValid(),
        "max_print_height_mm": round(nose.BoundBox.ZLength, 1),
    }
    return nose, info


# =============================================================================================== SLED
def build_sled():
    zt, zb = SLED_LEN / 2, -SLED_LEN / 2
    y1, y0 = PLATE_TOP_Y, PLATE_TOP_Y - PLATE_T
    ym = (y0 + y1) / 2
    plate = box(-PLATE_HALF_W, PLATE_HALF_W, y0, y1, zb, zt)
    sled = plate
    for sx in (-1, 1):
        sled = sled.fuse(cyl_z(BOSS_OD / 2, zb, zt, x=sx * ROD_X, y=ym))

    # window side: camera rails + lens-end stop, zip-tie slots beside the camera
    cz0, cz1 = CAM_Z0 - 0.6, CAM_Z0 + CAM_L + 0.6
    for sx in (-1, 1):
        x_in = sx * (CAM_W / 2 + 0.4)
        x_out = sx * (CAM_W / 2 + 2.0)
        sled = sled.fuse(box(min(x_in, x_out), max(x_in, x_out), y1, y1 + 5.0, cz0, CAM_Z0 + 18.0))
    sled = sled.fuse(box(-CAM_W / 2, CAM_W / 2, y1, y1 + 3.0, cz0 - 1.6, cz0))     # lens-end stop
    # switch + boost locating frames (1 mm lips, stick parts down with foam tape)
    for (z0, (l, w, _)) in ((BOOST_Z0, BOOST),):
        frame = box(-w / 2 - 1.0, w / 2 + 1.0, y1, y1 + 1.0, z0 - 1.0, z0 + l + 1.0)
        frame = frame.cut(box(-w / 2 - 0.2, w / 2 + 0.2, y1 - 1, y1 + 2, z0 - 0.2, z0 + l + 0.2))
        sled = sled.fuse(frame)

    # shaded side: Raven standoffs, battery cradle lips, switch frame
    raven_x0 = -RAVEN_W / 2
    for (a, b) in RAVEN_HOLES:
        sx, sz = raven_x0 + a, RAVEN_Z0 + b
        so = cyl_y(3.0, y0 - RAVEN_STANDOFF, y0, x=sx, z=sz)
        sled = sled.fuse(so)
    bl, bw, bt = BATT
    cradle = box(-bw / 2 - 1.6, bw / 2 + 1.6, y0 - 2.5, y0, BATT_Z0 - 1.6, BATT_Z0 + bl + 1.6)
    cradle = cradle.cut(box(-bw / 2 - 0.3, bw / 2 + 0.3, y0 - 4, y0 + 1, BATT_Z0 - 0.3, BATT_Z0 + bl + 0.3))
    sled = sled.fuse(cradle)
    l, w, _ = SWITCH                                         # 19 mm across (x), 14 mm along the axis (z)
    frame = box(-l / 2 - 1.0, l / 2 + 1.0, y0 - 1.0, y0, SW_Z0 - 1.0, SW_Z0 + w + 1.0)
    frame = frame.cut(box(-l / 2 - 0.2, l / 2 + 0.2, y0 - 2, y0 + 1, SW_Z0 - 0.2, SW_Z0 + w + 0.2))
    sled = sled.fuse(frame)

    # cuts: rod holes, Raven pilot holes (#4-40 self-tap, 2.3 mm), zip-tie slots, wire pass-throughs
    for sx in (-1, 1):
        sled = sled.cut(cyl_z(ROD_HOLE / 2, zb - 1, zt + 1, x=sx * ROD_X, y=ym))
    for (a, b) in RAVEN_HOLES:
        sled = sled.cut(cyl_y(1.15, y0 - RAVEN_STANDOFF - 1, y1 + 1, x=raven_x0 + a, z=RAVEN_Z0 + b))
    slots = [(CAM_Z0 + 26.0, 2.4), (CAM_Z0 + 44.0, 2.4), (BATT_Z0 + 8.0, 2.4), (BATT_Z0 + bl - 11.0, 2.4),
             (BOOST_Z0 - 4.0, 2.4), (BATT_Z0 + bl + 2.5, 2.4)]          # zip ties + wire pass-throughs at the edges
    for (z, wslot) in slots:
        for sx in (-1, 1):
            xs = sx * (CAM_W / 2 + 0.7)
            sled = sled.cut(box(min(xs, xs + sx * wslot), max(xs, xs + sx * wslot), y0 - 5, y1 + 6, z, z + 4.0))

    sled = sled.removeSplitter()
    return sled


# =============================================================================================== LAYOUT + FIT CHECK
def build_layout():
    zc = COUPLER_LEN / 2
    parts = {}
    parts["coupler"] = cyl_z(COUPLER_OD / 2, -zc, zc).cut(cyl_z(COUPLER_ID / 2, -zc - 1, zc + 1))
    collar = cyl_z(BODY_OD / 2, -COLLAR_LEN / 2, COLLAR_LEN / 2).cut(cyl_z(COUPLER_OD / 2, -50, 50))
    cam_hole = cyl_y(9.0, 0, 40, x=0, z=0)
    vents = [V(math.sin(a) * 40, math.cos(a) * 40, 0) for a in (math.radians(90), math.radians(210), math.radians(330))]
    for vdir in vents:
        collar = collar.cut(Part.makeCylinder(1.0, 40, V(0, 0, 0), vdir.normalize()))
    switch_hole = Part.makeCylinder(2.0, 40, V(0, 0, SW_Z0 + SWITCH[1] / 2), V(0, -1, 0))
    parts["collar (vents 3 x 2.0 mm, camera hole, switch access)"] = collar.cut(cam_hole).cut(switch_hole)
    parts["coupler"] = parts["coupler"].cut(cam_hole)
    for s in (-1, 1):
        zi = s * (zc - BULKHEAD_T)
        parts[f"bulkhead {'fore' if s > 0 else 'aft'} (coupler disk)"] = cyl_z(COUPLER_ID / 2 - 0.1, min(zi, s * zc), max(zi, s * zc))
        parts[f"bulkhead {'fore' if s > 0 else 'aft'} (tube disk)"] = cyl_z(54.2 / 2, min(s * zc, s * (zc + BULKHEAD_T)), max(s * zc, s * (zc + BULKHEAD_T)))
    for sx in (-1, 1):
        parts[f"rod {'+' if sx > 0 else '-'}x"] = cyl_z(ROD_D / 2, -zc - BULKHEAD_T - 6, zc + BULKHEAD_T + 6,
                                                         x=sx * ROD_X, y=PLATE_TOP_Y - PLATE_T / 2)
    y1, y0 = PLATE_TOP_Y, PLATE_TOP_Y - PLATE_T
    # camera: lens block (tall) + body
    cam = box(-CAM_W / 2, CAM_W / 2, y1, y1 + CAM_H_LENS, CAM_Z0, CAM_Z0 + CAM_LENS_BLOCK)
    cam = cam.fuse(box(-CAM_W / 2, CAM_W / 2, y1, y1 + CAM_H_BODY, CAM_Z0 + CAM_LENS_BLOCK, CAM_Z0 + CAM_L))
    parts["camera RunCam Thumb Pro W"] = cam

    l, w, t = BOOST
    parts["5 V boost U3V16F5"] = box(-w / 2, w / 2, y1, y1 + t, BOOST_Z0, BOOST_Z0 + l)
    ry1 = y0 - RAVEN_STANDOFF
    raven = box(-RAVEN_W / 2, RAVEN_W / 2, ry1 - RAVEN_PCB, ry1, RAVEN_Z0, RAVEN_Z0 + RAVEN_L)
    raven = raven.fuse(box(-RAVEN_W / 2, RAVEN_W / 2, ry1 - RAVEN_TALL, ry1 - RAVEN_PCB, RAVEN_Z0, RAVEN_Z0 + 9.0))      # terminal block
    raven = raven.fuse(box(-7.0, 7.0, ry1 - 9.0, ry1 - RAVEN_PCB, RAVEN_Z0 + 16.0, RAVEN_Z0 + 30.0))                   # supercap
    parts["Blue Raven 2"] = raven
    bl, bw, bt = BATT
    parts["1S LiPo 1000 mAh"] = box(-bw / 2, bw / 2, y0 - bt, y0, BATT_Z0, BATT_Z0 + bl)
    l, w, t = SWITCH
    parts["switch (arms Raven + camera branch)"] = box(-l / 2, l / 2, y0 - t, y0, SW_Z0, SW_Z0 + w)

    # fit checks: every internal part inside the coupler bore and between the bulkheads, no part overlaps another
    R_in = COUPLER_ID / 2
    z_lim = zc - BULKHEAD_T
    internal = [k for k in parts if not k.startswith(("coupler", "collar", "bulkhead", "rod"))]
    report = {"coupler_bore_radius_mm": R_in, "free_length_mm": round(2 * z_lim, 1), "parts": {}}
    bore_limit = cyl_z(R_in, -z_lim, z_lim)
    for k in internal + ["sled"]:
        s = SLED if k == "sled" else parts[k]
        pts = s.tessellate(0.05)[0]
        rmax = max(math.hypot(p.x, p.y) for p in pts) if pts else 0
        outside = s.cut(bore_limit).Volume
        bb = s.BoundBox
        report["parts"][k] = {"max_radius_mm": round(rmax, 2), "radial_clearance_mm": round(R_in - rmax, 2),
                              "z_range_mm": [round(bb.ZMin, 1), round(bb.ZMax, 1)],
                              "volume_outside_bore_mm3": round(outside, 3)}
    overlaps = []
    names = internal + ["sled"]
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            sa = SLED if a == "sled" else parts[a]
            sb = SLED if b == "sled" else parts[b]
            if sa.BoundBox.intersect(sb.BoundBox):
                vol = sa.common(sb).Volume
                if vol > 0.5:
                    overlaps.append({"a": a, "b": b, "overlap_mm3": round(vol, 2)})
    report["overlaps"] = overlaps
    # the camera lens face distance to the coupler wall (straight out along +y)
    report["lens_face_y_mm"] = round(PLATE_TOP_Y + CAM_H_LENS, 2)
    report["lens_face_to_coupler_wall_mm"] = round(R_in - (PLATE_TOP_Y + CAM_H_LENS), 2)
    report["lens_face_to_outer_surface_mm"] = round(BODY_OD / 2 - (PLATE_TOP_Y + CAM_H_LENS), 2)
    return parts, report


# =============================================================================================== PREVIEWS
def render(shapes, out, views, title=None, alpha=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    palette = {"sled": (0.18, 0.60, 0.85), "camera": (0.25, 0.25, 0.28), "raven": (0.10, 0.35, 0.75),
               "lipo": (0.85, 0.65, 0.15), "switch": (0.30, 0.70, 0.35), "boost": (0.55, 0.30, 0.75),
               "coupler": (0.80, 0.80, 0.80), "collar": (0.95, 0.85, 0.20), "bulkhead": (0.75, 0.60, 0.40),
               "rod": (0.55, 0.55, 0.55), "nose": (0.95, 0.85, 0.20), "plug": (0.45, 0.45, 0.45)}

    def color(name):
        for k, c in palette.items():
            if k in name.lower():
                return c
        return (0.6, 0.6, 0.6)
    fig = plt.figure(figsize=(4.2 * len(views), 4.6), dpi=150)
    for vi, (elev, azim, vt) in enumerate(views):
        ax = fig.add_subplot(1, len(views), vi + 1, projection="3d")
        lo, hi = None, None
        for name, s in shapes.items():
            verts, faces = s.tessellate(0.4)
            if not faces:
                continue
            v = np.array([[p.x, p.y, p.z] for p in verts])
            tris = v[np.array(faces)]
            n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
            n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
            light = np.array([0.4, -0.6, 0.7]); light /= np.linalg.norm(light)
            shade = 0.35 + 0.65 * np.abs(n @ light)
            c = np.array(color(name))
            a = (alpha or {}).get(name, 1.0)
            cols = np.clip(c[None, :] * shade[:, None] + 0.05, 0, 1)
            cols = np.concatenate([cols, np.full((len(cols), 1), a)], axis=1)
            ax.add_collection3d(Poly3DCollection(tris, facecolors=cols, edgecolors="none"))
            lo = v.min(0) if lo is None else np.minimum(lo, v.min(0))
            hi = v.max(0) if hi is None else np.maximum(hi, v.max(0))
        mid, r = (lo + hi) / 2, (hi - lo).max() / 2
        ax.set_xlim(mid[0] - r, mid[0] + r); ax.set_ylim(mid[1] - r, mid[1] + r); ax.set_zlim(mid[2] - r, mid[2] + r)
        ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=elev, azim=azim); ax.axis("off")
        ax.set_title(vt, fontsize=9)
    if title:
        fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(out, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT_NOSE, exist_ok=True)
    os.makedirs(OUT_BAY, exist_ok=True)
    nose, nose_info = build_nose()
    export(nose, os.path.join(OUT_NOSE, "nose-cone-v2"))
    SLED = build_sled()
    export(SLED, os.path.join(OUT_BAY, "sled-v2"))
    parts, fit = build_layout()
    layout = Part.makeCompound([SLED] + list(parts.values()))
    layout.exportStep(os.path.join(OUT_BAY, "avbay-v2-layout.step"))
    fit["sled_volume_cm3"] = round(SLED.Volume / 1000, 2)
    fit["sled_valid"] = SLED.isValid()
    with open(os.path.join(OUT_BAY, "fit.json"), "w") as f:
        json.dump(fit, f, indent=1)
    with open(os.path.join(OUT_NOSE, "nose.json"), "w") as f:
        json.dump(nose_info, f, indent=1)
    # previews
    half = nose.common(box(-40, 40, 0, 40, -1, 300))       # cut-away to show the wall, band, pin hole and cavity
    pin = Part.makeCylinder(PIN_D / 2, 50.8, V(-25.4, 0, PIN_Z), V(1, 0, 0))
    render({"nose": nose}, os.path.join(OUT_NOSE, "nose-cone-v2.png"), [(15, -60, "nose cone v2 (PETG-CF)")])
    render({"nose": half, "rod pin": pin.common(box(-40, 40, -10, 40, -1, 300))},
           os.path.join(OUT_NOSE, "nose-cone-v2-section.png"), [(0, -90, "half section: wall, tether band, pin")])
    shown = {"sled": SLED, **{k: v for k, v in parts.items() if not k.startswith(("coupler", "collar", "bulkhead", "rod"))}}
    render(shown, os.path.join(OUT_BAY, "sled-v2-layout.png"),
           [(20, -60, "window side (+y)"), (-20, 120, "shaded side (-y)"), (0, 0, "end view")])
    render({"sled": SLED, **parts}, os.path.join(OUT_BAY, "avbay-v2-assembly.png"),
           [(15, -55, "av bay v2 in the 147 mm coupler")],
           alpha={k: 0.25 for k in parts if k.startswith(("coupler", "collar"))})
    print(json.dumps({"nose": nose_info, "fit": fit}, indent=1))
