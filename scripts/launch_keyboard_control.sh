#!/bin/sh
# Convenience launcher for the verified-working path (see
# keyboard_control.py's docstring: -g glfw opens a real window but
# silently renders only its background grid on this local SOFA
# build -- no vessel, no guidewire, no error. -g imgui is confirmed
# working end-to-end, and also gives a full editor UI: scene graph,
# viewport, log panel.
#
# Usage: scripts/launch_keyboard_control.sh --phantom=0 --variant=0
# (select_phantom() parses --key=value; space-separated --phantom 0
# will NOT work here, because runSofa's own CLI parser -- not
# our script -- consumes everything after --argv).
cd "$(dirname "$0")/.."
. scripts/sofa_env.sh
exec runSofa -l SofaPython3 -g imgui keyboard_control.py --argv "$@"
