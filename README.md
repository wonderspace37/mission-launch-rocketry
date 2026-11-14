<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/img/mlr-lockup.png">
    <img src="docs/assets/img/mlr-lockup-light.png" alt="Mission Launch Rocketry" width="420">
  </picture>
</p>

# Mission Launch Rocketry: project files

Welcome! This is where Mission Launch Rocketry keeps everything we design: OpenRocket simulations, CAD, analysis,
and the tools that tie them together. Everything here is version-controlled, so you can see what changed, when, and
why, and nothing gets lost in someone's Downloads folder.

**Mission Launch Rocketry (MLR)** is a student engineering club at Mission College in Santa Clara, CA. We design,
simulate, build and launch rockets. No experience required.
[Website](https://mission-launch-rocketry.vercel.app) ·
[Instagram](https://instagram.com/missionlaunchrocketry) ·
[missionlaunchrocketry@gmail.com](mailto:missionlaunchrocketry@gmail.com) ·
[Project page](https://wonderspace37.github.io/mission-launch-rocketry/)

## Projects

| Project | What it is | Status |
|---|---|---|
| [**Yellow Jacket**](yellow-jacket) | Two-stage 58 mm high-power rocket, H219T booster + H100W sustainer, ~5,100 ft simulated | Design rework (Nov 2026) |

## What's where

```
yellow-jacket/
  openrocket/yellow-jacket.ork   the OpenRocket design (history in git)
  cad/onshape/                   STEP snapshots from Onshape + previews + parts.md + manifest.json
  analysis/                      design reviews and simulation results
tools/
  onshape_export.py              pull CAD from Onshape into STEP files
  step_preview.py                sizes, volumes and preview images for STEP files (FreeCAD)
  openrocket/                    run OpenRocket headless: margins, flights, sweeps
  ork-textconv.sh                makes `git diff` readable for .ork files
docs/                            the project page (GitHub Pages)
```

## Getting the files

- **Just want a file?** Click it on GitHub, then **Download raw file**. Or grab everything with **Code > Download ZIP**.
- **Working on the design?** Clone it:

  ```bash
  git clone https://github.com/wonderspace37/mission-launch-rocketry.git
  cd mission-launch-rocketry
  git config diff.ork.textconv tools/ork-textconv.sh   # readable .ork diffs
  ```

## How we work

- **OpenRocket:** edit `yellow-jacket/openrocket/yellow-jacket.ork` in place and commit it. Don't save copies like
  `rocket (3).ork`; git keeps every version, and `git log --follow` shows them.
- **CAD:** Onshape is where we model. After a design change, export STEP snapshots with
  `tools/onshape_export.py` and commit them, so the repo always has a copy that opens in any CAD tool.
- **Changes:** make a branch, commit with a message that says *why*, and open a pull request so someone else can look
  before it lands on `main`. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Safety

Everything we fly follows the NAR/Tripoli safety codes and our range safety officer's calls. Simulations here are
design tools, not a substitute for a flight review.
