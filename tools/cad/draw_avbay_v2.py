#!/usr/bin/env python3
"""Dimensioned 2D drawings for av-bay v2 and nose cone v2, plus the wiring diagram (PNG + SVG).

    /Applications/FreeCAD.app/Contents/Resources/bin/python tools/cad/draw_avbay_v2.py

Reads every dimension from build_avbay_nose.py, so the drawings always match the CAD.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_avbay_nose as B  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

INK, MUTED, GRID = "#1d1d1c", "#6b727d", "#c9ced6"
BLUE, YELLOW, GREEN, ORANGE, PURPLE, GREY = "#015b8f", "#f2c500", "#2e8b57", "#d9822b", "#6f42c1", "#8a8f98"


def rect(ax, x0, x1, y0, y1, fc, ec=INK, lw=0.8, alpha=1.0, hatch=None, ls="-", z=2):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=fc, ec=ec, lw=lw, alpha=alpha, hatch=hatch, ls=ls, zorder=z))


def label(ax, x, y, s, size=7.5, color=INK, ha="center", va="center", **kw):
    ax.text(x, y, s, fontsize=size, color=color, ha=ha, va=va, zorder=10, **kw)


def dim_h(ax, x0, x1, y, text, size=7):
    ax.annotate("", xy=(x0, y), xytext=(x1, y), arrowprops=dict(arrowstyle="<->", lw=0.6, color=MUTED), zorder=9)
    label(ax, (x0 + x1) / 2, y + 2.2, text, size=size, color=MUTED)


def plan(ax, side):
    """Plan view of one side of the sled. Horizontal axis = -z (nose on the left), vertical = x."""
    zc = B.COUPLER_LEN / 2
    zi = zc - B.BULKHEAD_T
    H = lambda z: -z  # noqa: E731
    # coupler bore and wall, collar band, bulkheads
    rect(ax, H(zc), H(-zc), -B.COUPLER_OD / 2, B.COUPLER_OD / 2, "white", ec=GRID, lw=0.6, z=0)
    rect(ax, H(zc), H(-zc), -B.COUPLER_ID / 2, B.COUPLER_ID / 2, "#fafbfc", ec=GRID, lw=0.6, ls="--", z=0)
    rect(ax, H(B.COLLAR_LEN / 2), H(-B.COLLAR_LEN / 2), -B.BODY_OD / 2, B.BODY_OD / 2, YELLOW, ec="none", alpha=0.18, z=0)
    label(ax, 0, B.BODY_OD / 2 + 3.5, "40 mm collar (clear wrap)", size=7, color="#8a6d00")
    for s in (-1, 1):
        rect(ax, H(s * zi), H(s * zc), -B.COUPLER_ID / 2, B.COUPLER_ID / 2, "#e8d5b5", ec=INK, lw=0.6, hatch="////", z=1)
        rect(ax, H(s * zc), H(s * (zc + B.BULKHEAD_T)), -54.2 / 2, 54.2 / 2, "#e8d5b5", ec=INK, lw=0.6, hatch="\\\\\\\\", z=1)
    label(ax, H(zc + B.BULKHEAD_T) - 1, -B.BODY_OD / 2 - 4, "FORE (main bay, nose)", size=7, ha="left", color=MUTED)
    label(ax, H(-zc - B.BULKHEAD_T) + 1, -B.BODY_OD / 2 - 4, "AFT (drogue bay)", size=7, ha="right", color=MUTED)
    # sled plate + rod bosses
    sz = B.SLED_LEN / 2
    rect(ax, H(sz), H(-sz), -B.PLATE_HALF_W, B.PLATE_HALF_W, "#d6e9f5", ec=BLUE, lw=0.9, z=2)
    for sx in (-1, 1):
        rect(ax, H(sz), H(-sz), sx * B.ROD_X - B.BOSS_OD / 2, sx * B.ROD_X + B.BOSS_OD / 2, "#bcdcf0", ec=BLUE, lw=0.7, z=2)
        ax.plot([H(zc + B.BULKHEAD_T + 6), H(-zc - B.BULKHEAD_T - 6)], [sx * B.ROD_X] * 2, color=GREY, lw=1.6, zorder=3)
    label(ax, H(sz) - 2, B.ROD_X + 6.5, f"#8-32 rods at x = ±{B.ROD_X:g}", size=6.5, ha="left", color=MUTED)
    if side == "+y":
        cz0 = B.CAM_Z0
        rect(ax, H(cz0 + B.CAM_L), H(cz0), -B.CAM_W / 2, B.CAM_W / 2, "#3a3d42", ec=INK, z=4)
        rect(ax, H(cz0 + B.CAM_LENS_BLOCK), H(cz0), -B.CAM_W / 2, B.CAM_W / 2, "#25272b", ec=INK, z=5)
        ax.add_patch(Circle((0, 0), 6.0, fc="#5b8fb9", ec="white", lw=0.8, zorder=6))
        label(ax, H(cz0 + B.CAM_L / 2 + 8), 0, "RunCam Thumb Pro W\n54 × 21, lens block 24.5 tall", size=7, color="white")
        label(ax, 0, -B.CAM_W / 2 - 3.5, "lens on collar centre", size=6.5, color=MUTED)
        l, w, _ = B.BOOST
        rect(ax, H(B.BOOST_Z0 + l), H(B.BOOST_Z0), -w / 2, w / 2, PURPLE, ec=INK, z=4)
        label(ax, H(B.BOOST_Z0 + l / 2), -w / 2 - 4.5, "5 V boost\n+ 1.1 A polyfuse", size=6.5)
        for z in (cz0 + 26.0, cz0 + 44.0):
            for sx in (-1, 1):
                xs = sx * (B.CAM_W / 2 + 0.7)
                rect(ax, H(z + 4), H(z), min(xs, xs + sx * 2.4), max(xs, xs + sx * 2.4), "white", ec=INK, lw=0.5, z=6)
        label(ax, H(cz0 + 35), B.CAM_W / 2 + 6, "zip-tie slots", size=6.5, color=MUTED)
        ax.set_title("Window side (+y): faces the collar's camera hole", fontsize=9, loc="left", color=INK)
    else:
        r0 = B.RAVEN_Z0
        rect(ax, H(r0 + B.RAVEN_L), H(r0), -B.RAVEN_W / 2, B.RAVEN_W / 2, BLUE, ec=INK, z=4)
        rect(ax, H(r0 + 9), H(r0), -B.RAVEN_W / 2, B.RAVEN_W / 2, GREEN, ec=INK, z=5)
        label(ax, H(r0 + B.RAVEN_L / 2 + 4), 0, "Blue Raven 2\n45.7 × 20.3\non 4 mm standoffs", size=7, color="white")
        label(ax, H(r0 + 4.5), B.RAVEN_W / 2 + 4, "terminals\n→ aft charges", size=6.5, color=MUTED)
        for (a, b) in B.RAVEN_HOLES:
            ax.add_patch(Circle((H(r0 + b), -B.RAVEN_W / 2 + a), 1.6, fc="white", ec=INK, lw=0.6, zorder=6))
        l, w, _ = B.SWITCH
        rect(ax, H(B.SW_Z0 + w), H(B.SW_Z0), -l / 2, l / 2, ORANGE, ec=INK, z=4)
        label(ax, H(B.SW_Z0 + w / 2), 0, "switch\n(arms all)", size=7)
        ax.add_patch(Circle((H(B.SW_Z0 + w / 2), 0), 2.0, fc="white", ec=INK, lw=0.6, zorder=6))
        label(ax, H(B.SW_Z0 + w / 2), -l / 2 - 4.5, f"screw-switch access Ø4 at z = {B.SW_Z0 + w / 2:g}", size=6.5, color=MUTED)
        bl, bw, bt = B.BATT
        rect(ax, H(B.BATT_Z0 + bl), H(B.BATT_Z0), -bw / 2, bw / 2, "#f4c95d", ec=INK, z=4)
        label(ax, H(B.BATT_Z0 + bl / 2), 0, "1S LiPo 1000 mAh\n50 × 20 × 10, XT30", size=7)
        ax.set_title("Shaded side (−y): away from the window (keeps light off the baro sensor)", fontsize=9, loc="left")
    # dimensions
    dim_h(ax, H(sz), H(-sz), -B.BODY_OD / 2 - 11, f"sled {B.SLED_LEN:g}")
    dim_h(ax, H(zi), H(-zi), -B.BODY_OD / 2 - 18, f"free length between bulkheads {2 * zi:.1f}")
    dim_h(ax, H(zc), H(-zc), -B.BODY_OD / 2 - 25, f"LOC coupler {B.COUPLER_LEN:g}")
    ax.set_xlim(H(zc + 16), H(-zc - 16))
    ax.set_ylim(-B.BODY_OD / 2 - 30, B.BODY_OD / 2 + 8)
    ax.set_aspect("equal")
    ax.axis("off")


def section(ax):
    """End section through the collar centre (z = 0), seen from the nose."""
    for r, fc, ec, ls in ((B.BODY_OD / 2, YELLOW, INK, "-"), (B.COUPLER_OD / 2, "#efe7d2", INK, "-"),
                          (B.COUPLER_ID / 2, "white", INK, "-")):
        ax.add_patch(Circle((0, 0), r, fc=fc, ec=ec, lw=0.8, ls=ls, alpha=0.9 if fc == YELLOW else 1))
    y1, y0 = B.PLATE_TOP_Y, B.PLATE_TOP_Y - B.PLATE_T
    rect(ax, -B.PLATE_HALF_W, B.PLATE_HALF_W, y0, y1, "#d6e9f5", ec=BLUE)
    for sx in (-1, 1):
        ax.add_patch(Circle((sx * B.ROD_X, (y0 + y1) / 2), B.BOSS_OD / 2, fc="#bcdcf0", ec=BLUE, lw=0.8, zorder=3))
        ax.add_patch(Circle((sx * B.ROD_X, (y0 + y1) / 2), B.ROD_D / 2, fc=GREY, ec=INK, lw=0.5, zorder=4))
    rect(ax, -B.CAM_W / 2, B.CAM_W / 2, y1, y1 + B.CAM_H_LENS, "#25272b", ec=INK, z=4)
    ax.add_patch(Circle((0, y1 + B.CAM_H_LENS - 0.5), 5.5, fc="#5b8fb9", ec="white", lw=0.6, zorder=5))
    ry1 = y0 - B.RAVEN_STANDOFF
    rect(ax, -B.RAVEN_W / 2, B.RAVEN_W / 2, ry1 - B.RAVEN_TALL, ry1, BLUE, ec=INK, ls="--", alpha=0.35, z=3)
    bl, bw, bt = B.BATT
    rect(ax, -bw / 2, bw / 2, y0 - bt, y0, "#f4c95d", ec=INK, ls="--", alpha=0.45, z=3)
    # holes through the collar: camera at +y, vents at 60/180/300 deg, switch access at -y
    ax.annotate("camera hole\n(clear wrap over it)", xy=(0, B.BODY_OD / 2), xytext=(-23, 36), fontsize=6.5,
                arrowprops=dict(arrowstyle="-", lw=0.5, color=MUTED), color=MUTED)
    for ang in (90, 210, 330):
        a = math.radians(ang)
        x, y = B.BODY_OD / 2 * math.sin(a), B.BODY_OD / 2 * math.cos(a)
        ax.add_patch(Circle((x, y), 1.8, fc="white", ec=INK, lw=0.7, zorder=6))
    label(ax, 31, -16, "3 vents Ø2.0 at\n90° / 210° / 330°\n(punch the wrap too)", size=6.5, ha="left", color=MUTED)
    ax.add_patch(Circle((0, -B.BODY_OD / 2), 2.0, fc=ORANGE, ec=INK, lw=0.7, zorder=6))
    label(ax, 7, -B.BODY_OD / 2 - 3.5, "switch access Ø4 (z = −8)", size=6.5, ha="left", color=MUTED)
    label(ax, 27, 31, f"lens corner clearance {B.COUPLER_ID / 2 - math.hypot(B.CAM_W / 2, y1 + B.CAM_H_LENS):.1f} mm",
          size=6.5, ha="left", color=MUTED)
    label(ax, 0, -36, "dashed: Raven and LiPo behind this section", size=6.5, color=MUTED)
    ax.set_xlim(-36, 46)
    ax.set_ylim(-37, 40)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Section at the collar (from the nose)", fontsize=9, loc="left")


def nose_drawing(ax):
    R, SH, L = B.BODY_OD / 2, B.SHOULDER_LEN, B.NOSE_LEN
    rs = B.BODY_ID / 2 - B.SHOULDER_CLEAR
    ri = rs - B.SHOULDER_WALL
    z_tip = SH + L
    zs = [SH + (L) * (1 - (k / 200) ** 1.6) for k in range(201)]
    outer = [(B.haack_r(z_tip - z, L, R), z) for z in zs]
    # horizontal drawing: x = z (tip on the left), y = r
    X = lambda z: z_tip - z  # noqa: E731
    top = [(X(z), r) for r, z in outer]
    prof = top + [(X(z), -r) for r, z in reversed(outer)]
    ax.add_patch(Polygon(prof, closed=True, fc=YELLOW, ec=INK, lw=0.8, alpha=0.85))
    rect(ax, X(SH), X(0), -rs, rs, YELLOW, ec=INK, alpha=0.85)
    rect(ax, X(SH), X(0), -ri, ri, "white", ec=INK, lw=0.5, ls="--")
    b0, b1 = B.BAND_Z
    rect(ax, X(b1), X(b0), -rs, -B.BAND_R, "#c9a400", ec=INK, lw=0.5)
    rect(ax, X(b1), X(b0), B.BAND_R, rs, "#c9a400", ec=INK, lw=0.5)
    rect(ax, X(B.PIN_Z) - B.PIN_D / 2, X(B.PIN_Z) + B.PIN_D / 2, -25.4, 25.4, GREY, ec=INK, z=5)
    rect(ax, B.TIP_SOLID + 3, 70, -4, 4, "#7d6b55", ec=INK, lw=0.5, hatch="xx", alpha=0.7, z=4)
    label(ax, 52, 9.5, "ballast (lead shot + epoxy)", size=6.5, color=MUTED)
    label(ax, X(B.PIN_Z), R + 9, "5/16\" × 2\" hardened dowel pin = shock-cord tether", size=7)
    label(ax, X(b1) - 3, -R - 4, f"tether band: ID {2 * B.BAND_R:g}, {b0:g}–{b1:g} mm from the open end", size=6.5,
          color=MUTED, ha="right")
    dim_h(ax, 0, X(SH), -R - 13, f"nose {L:g} (Von Kármán)")
    dim_h(ax, X(SH), X(0), -R - 13, f"shoulder {SH:g}")
    dim_h(ax, 0, X(0), -R - 21, f"overall {z_tip:g} (prints tip-up, < 250 mm)")
    label(ax, X(SH) - 3, R + 3, f"Ø{B.BODY_OD:g}", size=7, ha="right")
    label(ax, X(0) + 3, 0, f"Ø{2 * rs:g} shoulder\nwall {B.SHOULDER_WALL:g}\nopen end\n(cord exits here)", size=6.5, ha="left")
    ax.set_xlim(-5, z_tip + 42)
    ax.set_ylim(-R - 27, R + 15)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Nose cone v2: PETG-CF, 5 walls, 15% gyroid, no supports, 83.5 g (printmass)", fontsize=9, loc="left")


def wiring(ax):
    def block(x, y, w, h, text, fc, tc=INK):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6", fc=fc, ec=INK, lw=0.9))
        label(ax, x + w / 2, y + h / 2, text, size=8, color=tc)

    def wire(pts, color, lw=1.8, ls="-"):
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=color, lw=lw, ls=ls, solid_capstyle="round", zorder=1)
    RED, BLK = "#d62728", INK
    block(2, 40, 18, 12, "1S LiPo\n1000 mAh\n3.7 V nom.\n(XT30)", "#f4c95d")
    block(32, 40, 16, 12, "Switch\n(screw or\nmagnetic)", ORANGE)
    block(64, 54, 22, 14, "Blue Raven 2\n+In  Gnd\nApo  Main  3rd  4th", BLUE, "white")
    block(72, 20, 14, 10, "Polyfuse\n1.1 A hold", "#e6e6e6")
    block(92, 20, 14, 10, "Pololu\nU3V16F5\n5 V boost", PURPLE, "white")
    block(112, 18, 16, 14, "RunCam\nThumb Pro W\n5 V, <= 500 mA", "#3a3d42", "white")
    block(106, 64, 22, 12, "FORE bulkhead\nMain + 4th charges\n(main bay)", "#e8d5b5")
    block(106, 42, 22, 12, "AFT bulkhead\nApo + 3rd charges\n(drogue bay)", "#e8d5b5")
    wire([(20, 49), (32, 49)], RED)                                   # batt+ -> switch
    wire([(48, 49), (56, 49)], RED)                                   # switch out -> SW+ node
    wire([(56, 25), (56, 86)], RED)                                   # SW+ bus
    wire([(56, 61), (64, 61)], RED)                                   # -> +In
    wire([(56, 25), (72, 25)], RED)                                   # -> fuse
    wire([(86, 25), (92, 25)], RED)
    wire([(106, 25), (112, 25)], RED)                                 # 5 V -> camera
    wire([(56, 86), (101, 86), (101, 74), (106, 74)], RED, lw=1.2)    # Arm+ to fore charges
    wire([(101, 74), (101, 52), (106, 52)], RED, lw=1.2)              # Arm+ to aft charges
    wire([(86, 64), (94, 64), (94, 67), (106, 67)], GREEN, lw=1.2)    # Main/4th
    wire([(86, 58), (96, 58), (96, 45), (106, 45)], GREEN, lw=1.2)    # Apo/3rd
    wire([(11, 40), (11, 10), (120, 10), (120, 18)], BLK)             # ground bus
    wire([(68, 54), (68, 10)], BLK, lw=1.2)                           # Raven Gnd
    wire([(99, 20), (99, 10)], BLK, lw=1.2)                           # boost GND
    ax.add_patch(Circle((56, 49), 0.9, fc=RED, ec=RED, zorder=3))
    ax.add_patch(Circle((101, 74), 0.9, fc=RED, ec=RED, zorder=3))
    label(ax, 26, 51.5, "22 AWG", size=6.5, color=MUTED)
    label(ax, 59, 46.5, "SW+", size=7, color=RED, ha="left")
    label(ax, 109, 27.5, "5 V", size=7, color=RED)
    label(ax, 78, 89, "Arm+ (switched +) to one leg of every e-match", size=7, color=RED)
    label(ax, 92, 69.5, "Main/4th", size=6.5, color=GREEN)
    label(ax, 91, 47.5, "Apo/3rd", size=6.5, color=GREEN)
    label(ax, 70.5, 51.5, "Gnd", size=6.5, color=INK, ha="left")
    label(ax, 60, 6.5, "Ground (battery -): Raven Gnd, boost GND, camera GND", size=7, color=MUTED)
    label(ax, 64, 95, "One 1S pack, one switch. Raven straight off the cell (Featherweight's 1S guidance); camera on its own fused 5 V branch.",
          size=8)
    ax.set_xlim(0, 130)
    ax.set_ylim(2, 98)
    ax.axis("off")


if __name__ == "__main__":
    out_bay, out_nose = B.OUT_BAY, B.OUT_NOSE
    fig = plt.figure(figsize=(11.5, 12.5), dpi=150)
    gs = fig.add_gridspec(3, 2, width_ratios=[2.15, 1], height_ratios=[1, 1, 1.05])
    plan(fig.add_subplot(gs[0, 0]), "+y")
    plan(fig.add_subplot(gs[1, 0]), "-y")
    section(fig.add_subplot(gs[0:2, 1]))
    wiring(fig.add_subplot(gs[2, :]))
    fig.suptitle("Yellow Jacket av bay v2: sled layout (mm) and wiring", fontsize=12, x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(out_bay, f"avbay-v2-drawing.{ext}"), facecolor="white")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(11, 3.6), dpi=150)
    nose_drawing(ax)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(out_nose, f"nose-cone-v2-drawing.{ext}"), facecolor="white")
    print("drawings written")
