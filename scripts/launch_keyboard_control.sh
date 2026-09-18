#!/bin/sh
# Convenience launcher for the verified-working path (see
# keyboard_control.py's docstring for why: the standalone
# `python3 keyboard_control.py` path has a known rendering limitation
# on this local SOFA build).
#
# Usage: scripts/launch_keyboard_control.sh --phantom=0 --variant=0
# (select_phantom() parses --key=value; space-separated --phantom 0
# will NOT work here, because runSofa's own CLI parser -- not
# our script -- consumes everything after --argv).
cd "$(dirname "$0")/.."
. scripts/sofa_env.sh
exec runSofa -l SofaPython3 -g glfw keyboard_control.py --argv "$@"
