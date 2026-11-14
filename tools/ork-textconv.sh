#!/bin/sh
# Lets `git diff` show what changed inside an OpenRocket .ork (a zip around rocket.ork XML).
# Setup once per clone:  git config diff.ork.textconv tools/ork-textconv.sh
# Simulation data points are dropped so the diff shows the design, not 5,000 lines of telemetry.
if unzip -l "$1" >/dev/null 2>&1; then unzip -p "$1"; else cat "$1"; fi | grep -v '<datapoint>'
