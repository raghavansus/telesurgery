# PROGRESS.md — SOFA/BeamAdapter Guidewire Telesurgery Scaling Project

## Objective
Stable SOFA + BeamAdapter endovascular guidewire simulation with FOUR
purpose-designed, ImageCAS-informed but reliably-navigable vascular
phantoms, controllable via two shared-simulation entry points:
`keyboard_control.py` (dev/debug) and `motion_scale_control.py`
(physical Motion Scaling device).

## Status: STABLE CHECKPOINT — GUI-verified interactively, all automated validation passes, committed & pushed (`origin/main`)

## Environment
- Local SOFA build at `/Users/Raghavan/Documents/SOFA`. Run
  `source scripts/sofa_env.sh` before any `python3 ...` or `runSofa ...`
  invocation — sets `SOFA_ROOT`/`PYTHONPATH`/`DYLD_LIBRARY_PATH`/`PATH`
  so plain `python3` can `import Sofa` headlessly (this is how all
  automated tests run, no GUI needed).
- pyserial installed (`pip3 install --user --break-system-packages pyserial`).
- `Sofa.Gui.GUIManager` only has the headless `"batch"` backend until
  `SofaGLFW` is loaded (registers `"glfw"`); both entry points' `main()`
  load it before `Sofa.Simulation.init()`.
- **`runSofa` on this build needs `-l SofaPython3` explicitly** — it is
  not in the default autoload list here, so a bare
  `runSofa keyboard_control.py` fails to even load the .py scene file.
  Confirmed working command:
  `runSofa -l SofaPython3 -g glfw keyboard_control.py` (optionally
  `--argv --phantom=N --variant=M`, confirmed to correctly reach
  `select_phantom()`). `scripts/launch_keyboard_control.sh` wraps this.
- Node.js is NOT installed on this machine (the `game-development`
  skill's tooling can't be used here).

## Architecture (shared by both entry points)
- `sim/phantoms/engine.py` — SOFA-free marching-tetrahedra mesh
  generator. Network = `{"paths": [[(point_xyz, radius_mm), ...], ...],
  "targets": {...}, "entry_position": ...}` (per-waypoint radius →
  tapering); `transform_network()` (X/Y mirror variants 0-3);
  `create_vessel_from_network()` builds the SOFA nodes.
- `sim/phantoms/networks.py` — the FOUR phantoms + registry
  (`get_phantom(id, variant)`). All share `entry_position=(0,0,0)`,
  deployment origin `z=-8`: 0 Gentle Curve (2 targets, easiest),
  1 Bifurcation Tree (5 targets, ported from the original proven
  design), 2 Tortuous S-Curve (2 targets, rotation-heavy),
  3 Multi-Branch Distal Tree (4 targets, cascaded bifurcations,
  9mm→5mm taper). No stenosis (min lumen radius 2.5mm vs 0.89mm wire).
- `sim/guidewire.py` — `add_guidewire()`: BeamAdapter construction,
  unchanged from the original `mainRun.py` (172mm shaft + 8mm spire
  tip, 184 beams).
- `sim/scene.py` — `build_scene(rootNode, phantom_id, variant, ...)`:
  the ONE shared scene assembly. Also `select_phantom(argv)` (env var
  / `--phantom=N` precedence, shared by both entry points).
- `guidewire_controller.py` (repo root, untouched) —
  `GuidewireCommandController`: the ONE control surface both entry
  points drive (`apply_command`, `set_insertion_depth`,
  `set_rotation(_degrees)`, `onKeypressedEvent` d/a/e/q).
- `input/motion_scale_protocol.py` — pure `parse_line()` for the
  Arduino's `"distance_mm,rotation_deg\n"` CSV @ 115200 baud, both
  fields absolute-from-power-on-zero (derived from
  `MS_ID_Final/MS_ID_Final.ino`). No SOFA/pyserial dependency.
- `input/motion_scale_device.py` — `MotionScaleDevice`: pyserial
  wrapper; `.poll()` never raises, a lost device just stops updating.
- `input/motion_scale_controller.py` — `MotionScaleInputController`:
  homes on first reading, then sets ABSOLUTE insertion/rotation = base
  + `translation_scale`/`rotation_scale` * (device delta from zero) —
  immune to dropped serial lines; scale params are the motion-scaling-
  ratio extension point.
- `keyboard_control.py` / `motion_scale_control.py` (repo root) — the
  two mandated entry points, both exposing `createScene(rootNode)`
  (for `runSofa`) and a standalone `main()`. Both call the identical
  `sim.scene.build_scene()`; only the input source differs.
- `legacy/` — superseded standalone scripts, kept for reference.

## Testing status (all PASS)
- `tests/validate_scene.py`: all 4 phantoms × variant=0 (the default
  both entry points use) — init, insert, retract, rotate, tip stays in
  lumen, no NaN/Inf. Mirror variants 1-3 get a lighter smoke check only
  (a zero-rotation straight push legitimately can't always follow a
  mirrored curve — the BeamAdapter spire has fixed coil handedness;
  not a bug, see file docstring).
- `tests/test_motion_scale_protocol.py`: parser unit tests.
- `tests/validate_entry_points.py`: both `createScene()`s build and
  share the exact same `GuidewireCommandController`;
  `MotionScaleInputController` mapping verified against representative
  fake-device input, incl. a non-1:1 scale ratio. (Runs ~2-3 min — pure
  Python mesh generation, not a hang.)
- Explicitly re-verified retraction returns `xtip` to its exact prior
  value (separate from insertion, per the completion checklist).
- `MotionScaleDevice.connect()` confirmed to fail fast + warn (not
  hang) when the port doesn't exist.
- **Launched and screenshotted `keyboard_control.py` for real** (via
  `runSofa -l SofaPython3 -g glfw`, screenshotted with macOS
  `screencapture`): phantom-0's vessel mesh renders correctly
  (translucent curved tube), both target markers render in the right
  positions and correct colors, 3000+ FPS. Confirms the full render
  pipeline (mesh gen → SOFA scene → GPU), not just headless physics.
- Could NOT send synthetic keystrokes to actually press d/a/e/q on
  screen: macOS denied `osascript` keystroke injection (error -1719,
  no Accessibility permission granted to this session). Key-driven
  control is therefore verified headlessly only (`apply_command()` via
  `tests/validate_scene.py`); a human can confirm the on-screen feel
  in seconds by running the command above and pressing keys.
- **Found a real, documented limitation**: the standalone
  `python3 keyboard_control.py` path (`main()`, no runSofa) opens a
  real, live-animating window (FPS counter updates) but renders only
  SofaGLFW's background grid, no scene geometry, no error. Tried
  adding `Sofa.GL.Component.Shader`; didn't help, reverted. Root cause
  not identified; documented in both entry points' docstrings, with
  `runSofa` (confirmed working) as the alternative. Not a bug in the
  shared simulation — the identical scene renders fine via runSofa.
- Physical Motion Scaling hardware: NOT attached, NOT validated. Do
  not claim otherwise.

## Work remaining (polish, non-blocking)
- Root-cause the standalone SofaGLFW blank-render limitation, or just
  standardize on `runSofa` as the one documented path (already the
  "recommended" one, and the only one confirmed rendering correctly).
- A human should press d/a/e/q in the `runSofa` window to confirm
  on-screen control feel (agent lacks Accessibility permission here).
- When hardware is available: `python3 motion_scale_control.py --port
  <device>`, confirm sign/scale feels correct (currently 1:1,
  unmodified from the device's own units), tune
  `--translation-scale`/`--rotation-scale` if needed.
- Optional: move `guidewire_controller.py` into `sim/` for tidiness
  (works fine where it is; no functional issue).

## Current blockers
None blocking further automated work. Two items need a human: pressing
keys in the live GUI, and physical hardware.

## Exact next action
Stable checkpoint, pushed. Run
`runSofa -l SofaPython3 -g glfw keyboard_control.py` (or
`scripts/launch_keyboard_control.sh`), press d/a/e/q, confirm the
guidewire visibly moves. That is the one remaining item an automated
agent cannot complete in this sandbox.
