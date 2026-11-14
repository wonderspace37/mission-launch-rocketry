#!/usr/bin/env python3
"""Size, volume and a preview PNG for every STEP file under a folder (needs FreeCAD 1.x).

For each part: bounding box, solid volume, and the mass it would weigh in PLA/PETG at 100% infill. The previews are
flat-shaded matplotlib renders of FreeCAD's tessellation, written next to each STEP as <name>.png, and a summary goes
to <folder>/parts.md.

Usage (macOS):
    /Applications/FreeCAD.app/Contents/Resources/bin/python tools/step_preview.py yellow-jacket/cad/onshape
"""
import sys

sys.path.append("/Applications/FreeCAD.app/Contents/Resources/lib")
import FreeCAD  # noqa: E402,F401  (must come before Part/Mesh or Python segfaults)
import Part  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

PETG = 1.27  # g/cm^3


def render(shape, out):
    verts, faces = shape.tessellate(0.2)
    v = np.array([[p.x, p.y, p.z] for p in verts])
    tris = v[np.array(faces)]
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    light = np.array([0.4, -0.5, 0.75]); light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.abs(n @ light)
    base = np.array([0.18, 0.60, 0.85])           # MLR accent blue
    colors = np.clip(base[None, :] * shade[:, None] + 0.08, 0, 1)
    fig = plt.figure(figsize=(4, 4), dpi=150)
    ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(Poly3DCollection(tris, facecolors=colors, edgecolors="none"))
    lo, hi = v.min(0), v.max(0)
    mid, r = (lo + hi) / 2, (hi - lo).max() / 2 or 1
    ax.set_xlim(mid[0] - r, mid[0] + r); ax.set_ylim(mid[1] - r, mid[1] + r); ax.set_zlim(mid[2] - r, mid[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=22, azim=-55)
    ax.axis("off")
    fig.patch.set_alpha(0)
    fig.savefig(out, transparent=True, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def main():
    root = Path(sys.argv[1])
    manifest = json.loads((root / "manifest.json").read_text()) if (root / "manifest.json").exists() else {}
    names = {v["folder"]: v for v in manifest.values()}
    rows = []
    for step in sorted(root.rglob("*.step")):
        shape = Part.read(str(step))
        solids = shape.Solids
        bb = shape.BoundBox
        vol = sum(s.Volume for s in solids) / 1000.0  # cm^3
        png = step.with_suffix(".png")
        render(shape, png)
        doc = names.get(step.parent.name, {})
        rows.append((doc.get("name", step.parent.name), step.relative_to(root).as_posix(), len(solids),
                     bb.XLength, bb.YLength, bb.ZLength, vol, vol * PETG, doc.get("url", "")))
        print(f"{step.relative_to(root)}: {len(solids)} solid(s), {bb.XLength:.1f} x {bb.YLength:.1f} x "
              f"{bb.ZLength:.1f} mm, {vol:.1f} cm3")
    lines = ["# Parts exported from Onshape", "",
             "Sizes from the STEP files. Mass is solid PETG (1.27 g/cm³) at 100% infill, so a printed part with "
             "less infill weighs less. Regenerate with `tools/step_preview.py`.", "",
             "| Document | File | Solids | Size X × Y × Z (mm) | Volume (cm³) | Solid PETG (g) | Onshape |",
             "|---|---|---|---|---|---|---|"]
    for name, f, ns, x, y, z, vol, m, url in rows:
        lines.append(f"| {name} | [{f}]({f}) | {ns} | {x:.1f} × {y:.1f} × {z:.1f} | {vol:.1f} | {m:.0f} | "
                     f"{'[open](' + url + ')' if url else ''} |")
    (root / "parts.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
