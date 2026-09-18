# PROGRESS.md — SOFA/BeamAdapter Guidewire Telesurgery Scaling Project

## Objective
Stable SOFA + BeamAdapter endovascular guidewire simulation with FOUR
purpose-designed, ImageCAS-informed but reliably-navigable vascular
phantoms, controllable via two shared-simulation entry points:
`keyboard_control.py` (dev/debug) and `motion_scale_control.py`
(physical Motion Scaling device).

## Status: STABLE CHECKPOINT — all automated validation passes, committed & pushed (`origin/main` @ `7dc3513`)

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

## Architecture (shared by both entry points)
- `sim/phantoms/engine.py` — SOFA-free implicit-surface / marching-
  tetrahedra mesh generator. A network is
  `{"paths": [[(point_xyz, radius_mm), ...], ...], "targets": {...},
  "entry_position": ...}` (radius per-waypoint → tapering). Also
  `transform_network()` (X/Y mirror variants 0-3) and
  `create_vessel_from_network()` (builds SOFA collision/visual nodes).
- `sim/phantoms/networks.py` — the FOUR phantoms + registry
  (`PHANTOMS`, `get_phantom(id, variant)`). All share
  `entry_position=(0,0,0)`, deployment origin `z=-8`: 0 Gentle Curve
  (2 targets, easiest), 1 Bifurcation Tree (5 targets, ported from the
  original proven design), 2 Tortuous S-Curve (2 targets, emphasizes
  rotation), 3 Multi-Branch Distal Tree (4 targets, cascaded
  bifurcations, 9mm→5mm taper). No stenosis anywhere (min lumen radius
  2.5mm vs 0.89mm wire).
- `sim/guidewire.py` — `add_guidewire()`: BeamAdapter guidewire
  construction, extracted unchanged from the original `mainRun.py`
  (172mm shaft + 8mm spire tip, 184 beams).
- `sim/scene.py` — `build_scene(rootNode, phantom_id, variant, ...)`:
  the ONE shared scene assembly (plugins, collision, camera, phantom,
  guidewire, `GuidewireCommandController`). Also `select_phantom(argv)`
  (env var / `--phantom=N` precedence, shared by both entry points).
- `guidewire_controller.py` (repo root, untouched) —
  `GuidewireCommandController`: the ONE control surface both entry
  points drive (`apply_command`, `set_insertion_depth`,
  `set_rotation(_degrees)`, `onKeypressedEvent` d/a/e/q).
- `input/motion_scale_protocol.py` — pure `parse_line()` for the
  Arduino's `"distance_mm,rotation_deg\n"` CSV @ 115200 baud, both
  fields absolute-from-power-on-zero (derived directly from
  `MS_ID_Final/MS_ID_Final.ino`). No SOFA/pyserial dependency.
- `input/motion_scale_device.py` — `MotionScaleDevice`: pyserial
  wrapper; `.poll()` never raises, a lost device just stops updating.
- `input/motion_scale_controller.py` — `MotionScaleInputController`
  (Sofa.Core.Controller): homes on first reading, then every step sets
  ABSOLUTE insertion/rotation = base + `translation_scale`/
  `rotation_scale` * (device delta from zero) — immune to dropped
  serial lines; the scale params are the motion-scaling-ratio
  extension point.
- `keyboard_control.py` / `motion_scale_control.py` (repo root) — the
  two mandated entry points. Both expose `createScene(rootNode)` (for
  `runSofa`) and a standalone `main()` (loads `SofaGLFW`, opens a
  `"glfw"` window). Both call the identical `sim.scene.build_scene()`;
  only the input source differs.
- `legacy/` — superseded standalone scripts, kept for reference.
- `tests/` — see Testing below.

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
- `Sofa.Gui.GUIManager.createGUI()`/`closeGUI()` confirmed to succeed
  for `keyboard_control.py`'s scene after loading `SofaGLFW` — window
  backend construction works end-to-end. The blocking interactive
  `MainLoop()` was intentionally NOT invoked by the agent (needs a
  human at the keyboard/device).
- Physical Motion Scaling hardware: NOT attached, NOT validated. Do
  not claim otherwise.

## Work remaining (polish, non-blocking)
- Human should manually run `python3 keyboard_control.py --phantom N`
  for each of the 4 phantoms and eyeball navigation feel.
- When hardware is available: `python3 motion_scale_control.py --port
  <device>`, confirm sign/scale feels correct (currently 1:1,
  unmodified from the device's own units), tune
  `--translation-scale`/`--rotation-scale` if needed.
- Optional: move `guidewire_controller.py` into `sim/` for tidiness
  (works fine where it is; no functional issue).

## Current blockers
None.

## Exact next action
Stable checkpoint, pushed. Next step is the two manual/hardware items
above — both are the "human/hardware" tasks that cannot be completed
by an automated agent, not further implementation work.
