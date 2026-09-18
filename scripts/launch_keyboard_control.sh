#!/bin/sh
# Convenience launcher for the verified-working path (see
# keyboard_control.py's docstring for why: the standalone
# `python3 keyboard_control.py` path has a known rendering limitation
# on this local SOFA build).
cd "$(dirname "$0")/.."
. scripts/sofa_env.sh
exec runSofa -l SofaPython3 -g glfw keyboard_control.py --argv "$@"
