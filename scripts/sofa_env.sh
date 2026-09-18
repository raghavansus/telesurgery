#!/bin/sh
# Source this before running any script that does `import Sofa`,
# or before invoking runSofa:
#
#   source scripts/sofa_env.sh
#   python3 tests/validate_scene.py
#   runSofa -l SofaPython3 -g glfw keyboard_control.py
#
# -l SofaPython3 is required: on this build it is not in runSofa's
# default plugin autoload list, so a bare `runSofa keyboard_control.py`
# fails with "extension (py) is only supported if the plugin
# SofaPython3 is loaded" (confirmed on this machine).
#
# Adjust SOFA_ROOT if the local SOFA build lives elsewhere.

export SOFA_ROOT="${SOFA_ROOT:-/Users/Raghavan/Documents/SOFA}"
export PYTHONPATH="$SOFA_ROOT/plugins/SofaPython3/lib/python3/site-packages:$PYTHONPATH"
export DYLD_LIBRARY_PATH="$SOFA_ROOT/lib:$SOFA_ROOT/plugins/SofaPython3/lib:$DYLD_LIBRARY_PATH"
export PATH="$SOFA_ROOT/bin:$PATH"
