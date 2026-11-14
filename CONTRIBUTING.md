# Contributing

New to git? You can do everything below from the GitHub website or GitHub Desktop. Ask in the club chat if you get
stuck. Nobody minds.

## The short version

1. **Branch.** `git switch -c fin-resize` (name it after what you're doing).
2. **Change one thing.** Edit the .ork, export new CAD, add a sim result.
3. **Commit with a reason.** `git commit -m "Booster fins 25 -> 35 mm span for 1 cal off the rail"`. The message is
   for the person reading the history in six months, so say *why*, not just *what*.
4. **Push and open a pull request.** `git push -u origin fin-resize`, then open the PR on GitHub. Someone else looks
   before it merges to `main`.

## OpenRocket

- One .ork per rocket, edited in place: `yellow-jacket/openrocket/yellow-jacket.ork`. Never commit `rocket (3).ork`.
- Use OpenRocket **23.09 or newer**. Saving in an older version can drop settings.
- Before committing, check the default flight configuration has **every stage switched on**, and rerun the sims so
  the stored results match the design.
- See what changed in a .ork: run `git config diff.ork.textconv tools/ork-textconv.sh` once, then `git diff`.

## CAD (Onshape)

Onshape is the source of truth for CAD; the repo keeps STEP snapshots so the design survives account changes and opens
in any CAD tool.

```bash
# needs an Onshape API key: My account > Developer > API keys (read-only is enough)
export ONSHAPE_ACCESS_KEY=...  ONSHAPE_SECRET_KEY=...
python3 tools/onshape_export.py --doc <document id> --out yellow-jacket/cad/onshape
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/step_preview.py yellow-jacket/cad/onshape   # previews + parts.md
```

The document id is the long hex string after `/documents/` in the Onshape URL. Free and Education Onshape accounts get
2,500 API calls a year, and one Part Studio export costs about 5, so export what changed, not everything.

**Never commit API keys, passwords or tokens.** Keys go in environment variables or `~/.config/onshape/`, never in
the repo.

## Simulations and analysis

Put write-ups in `<project>/analysis/` with the date in the name (`baseline-2026-11-13.md`), and say which .ork commit
they used. The scripts in `tools/openrocket/` reproduce the numbers.

## What doesn't belong here

- Anything export-controlled or someone else's proprietary data.
- Personal info beyond what members are happy to show publicly (this repo is public).
- Big generated files (sliced G-code, renders over a few MB). Link to them instead.

## Licensing

By opening a pull request you agree your contribution is licensed like the rest of the repo: CC BY 4.0 for designs
and documents, MIT for code. See [LICENSE.md](LICENSE.md).
