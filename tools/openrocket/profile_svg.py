#!/usr/bin/env python3
"""Side-profile SVG of a rocket, drawn from the .ork geometry (body outline, fins, stage joints).

Usage: .venv/bin/python tools/openrocket/profile_svg.py yellow-jacket/openrocket/yellow-jacket.ork docs/assets/yellow-jacket.svg
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import start_openrocket  # noqa: E402


def main():
    src, out = sys.argv[1], sys.argv[2]
    start_openrocket()
    from java.io import File
    from net.sf.openrocket.file import GeneralRocketLoader
    from net.sf.openrocket.rocketcomponent import AxialStage, BodyTube, FinSet, Transition
    doc = GeneralRocketLoader(File(os.path.abspath(src))).load()
    rocket = doc.getRocket()
    rocket.getFlightConfiguration(doc.getSimulations()[0].getFlightConfigurationId()).setAllStages()
    upper, fins, joints = [], [], []
    stages = [c for c in rocket.getChildren() if isinstance(c, AxialStage)]
    for st in stages[1:]:
        joints.append(float(st.getComponentLocations()[0].x) * 1e3)
    stack = [rocket]
    while stack:
        c = stack.pop()
        stack.extend(list(c.getChildren()))
        x0 = float(c.getComponentLocations()[0].x) * 1e3 if not isinstance(c, AxialStage) and c is not rocket else 0
        if isinstance(c, Transition):
            L = float(c.getLength())
            for i in range(61):
                x = L * i / 60
                upper.append((x0 + x * 1e3, float(c.getRadius(x)) * 1e3))
        elif isinstance(c, BodyTube):
            r = float(c.getOuterRadius()) * 1e3
            upper += [(x0, r), (x0 + float(c.getLength()) * 1e3, r)]
        elif isinstance(c, FinSet):
            r = float(c.getParent().getOuterRadius()) * 1e3
            fins.append([(x0 + float(p.x) * 1e3, r + float(p.y) * 1e3) for p in c.getFinPoints()])
    upper.sort()
    length = max(x for x, _ in upper)
    rmax = max(max(y for _, y in f) for f in fins)
    pad = 6
    W, H = length + 2 * pad, 2 * rmax + 2 * pad
    cy = H / 2

    def path(pts, mirror=False):
        s = -1 if mirror else 1
        return " ".join(f"{'M' if i == 0 else 'L'}{x + pad:.1f},{cy - s * y:.1f}" for i, (x, y) in enumerate(pts))
    body = path(upper) + " " + " ".join(f"L{x + pad:.1f},{cy + y:.1f}" for x, y in reversed(upper)) + " Z"
    fin_paths = "".join(f'<path d="{path(f)} Z"/><path d="{path(f, True)} Z"/>' for f in fins)
    joint_lines = "".join(f'<line x1="{j + pad:.1f}" y1="{cy - 31:.1f}" x2="{j + pad:.1f}" y2="{cy + 31:.1f}"/>'
                          for j in joints)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="Yellow Jacket side profile, {length:.0f} mm long">
<g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round">{fin_paths}<path d="{body}"/></g>
<g stroke="currentColor" stroke-width="1" stroke-dasharray="3 3" opacity=".55">{joint_lines}</g>
</svg>
'''
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w").write(svg)
    print(f"wrote {out}: {length:.0f} mm long, fins to r={rmax:.1f} mm, joints at {[round(j) for j in joints]}")


if __name__ == "__main__":
    main()
