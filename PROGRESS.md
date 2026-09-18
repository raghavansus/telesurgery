# PROGRESS.md — SOFA/BeamAdapter Guidewire Telesurgery Scaling Project

## Objective
Stable SOFA + BeamAdapter endovascular guidewire simulation with FOUR
purpose-designed, ImageCAS-informed but reliably-navigable vascular
phantoms, controllable via two shared-simulation entry points:
`keyboard_control.py` (dev/debug) and `motion_scale_control.py`
(physical Motion Scaling device). See original task prompt for full spec.

## Environment (local, this machine only)
- Local SOFA build at `/Users/Raghavan/Documents/SOFA` (runSofa binary +
  SofaPython3 bindings, built for Python 3.12).
- `source scripts/sofa_env.sh` sets `SOFA_ROOT`/`PYTHONPATH`/
  `DYLD_LIBRARY_PATH`/`PATH` so plain `python3` can `import Sofa`
  headlessly (confirmed working) — this is how all automated
  validation in this project runs, without needing the runSofa GUI.
- pyserial installed via `pip3 install --user --break-system-packages
  pyserial` (system Python is externally-managed/Homebrew).
- `Sofa.Gui.GUIManager` only exposes the `"batch"` (headless) backend
  until the `SofaGLFW` plugin is loaded, which registers a `"glfw"`
  interactive backend — both entry points' `main()` load it before
  `Sofa.Simulation.init()`.

## Architecture (current, shared)
- `sim/phantoms/engine.py` — pure-Python (no SOFA) implicit-surface /
  marching-tetrahedra vessel mesh generator. Networks are
  `{"paths": [[(point_xyz, radius_mm), ...], ...], "targets": {...},
  "entry_position": ...}`; radius is per-waypoint so phantoms can
  taper diameter. Also has `transform_network()` (X/Y mirror variants
  0-3) and `create_vessel_from_network()` (builds the SOFA
  MeshTopology/collision/visual nodes + target markers).
- `sim/phantoms/networks.py` — the FOUR phantom definitions + registry
  (`PHANTOMS`, `get_phantom(id, variant)`, `get_phantom_info(id)`).
  All four share `entry_position=(0,0,0)`, deployment origin `z=-8`.
  0 Gentle Curve (2 targets, easiest), 1 Bifurcation Tree (5 targets,
  the original proven `scenes/study_phantom.py` design, ported),
  2 Tortuous S-Curve (2 targets, emphasizes rotation), 3 Multi-Branch
  Distal Tree (4 targets, two cascaded bifurcations/side, diameter
  tapers 9mm→5mm). No stenosis; min lumen radius 2.5mm vs 0.89mm wire.
- `sim/guidewire.py` — `add_guidewire(rootNode, deployment_origin_z)`,
  the exact BeamAdapter guidewire construction from the original
  `mainRun.py` (172mm shaft + 8mm spire tip, 184 beams), unchanged
  physics parameters.
- `sim/scene.py` — `build_scene(rootNode, phantom_id, variant, ...)`:
  the ONE shared scene assembly (plugins, collision pipeline, camera,
  phantom, guidewire, `GuidewireCommandController`). Also
  `select_phantom(argv)` (env var + `--phantom=N`/`--variant=M`
  precedence, shared by both entry points) and `describe_phantoms()`.
- `guidewire_controller.py` (repo root, untouched) —
  `GuidewireCommandController`: `apply_command/apply_translation/
  apply_rotation/set_insertion_depth/set_rotation(_degrees)/
  get_insertion_depth/get_rotation(_degrees)`, plus
  `onKeypressedEvent` (d/a/e/q = insert/retract/rotate+/rotate-).
  This is the ONE control surface both entry points drive.
- `input/motion_scale_protocol.py` — pure `parse_line()` for the
  Arduino's `"distance_mm,rotation_deg\n"` CSV @ 115200 baud (both
  fields absolute-from-power-on-zero, NOT deltas — see file header,
  derived directly from `MS_ID_Final/MS_ID_Final.ino`). No SOFA/
  pyserial dependency; unit-tested in isolation.
- `input/motion_scale_device.py` — `MotionScaleDevice`: pyserial
  wrapper, `.connect()/.poll()/.latest_distance_mm/.latest_rotation_deg`.
  Never raises out of `.poll()`; a lost device just stops updating.
- `input/motion_scale_controller.py` — `MotionScaleInputController`
  (Sofa.Core.Controller): on first device reading, homes to current
  wire position + device zero; every step after, sets ABSOLUTE
  insertion depth / rotation = base + `translation_scale`/
  `rotation_scale` * (device delta from zero). Absolute mapping
  chosen deliberately (immune to dropped serial lines, unlike
  delta-integration). `translation_scale`/`rotation_scale` are the
  motion-scaling-ratio extension point.
- `keyboard_control.py`, `motion_scale_control.py` (repo root) — the
  two mandated entry points. Both expose `createScene(rootNode)` (for
  `runSofa <script>.py`, phantom/variant via `select_phantom`) AND a
  standalone `main()` that loads `SofaGLFW` and opens a `"glfw"` GUI
  window directly via `Sofa.Gui.GUIManager` (untested interactively in
  this headless agent session — see Testing below). They call the
  identical `sim.scene.build_scene()`; only the input source differs
  (`onKeypressedEvent` vs `MotionScaleInputController`+`MotionScaleDevice`).
- `legacy/` — old standalone scene scripts (`mainRun.py`,
  `beam_guidewire*.py`, `four_target_path.py`, `test_scene.py`),
  superseded by the above, kept for reference only.
- `scripts/sofa_env.sh` — sourceable env setup (see Environment above).
- `tests/` — headless validation (see Testing below).

## Work completed
1. Refactored the original single-phantom `mainRun.py`/`scenes/
   study_phantom.py` into the shared `sim/` architecture above,
   preserving the exact guidewire physics parameters (confirmed via
   headless baseline test before refactor — see git history / this
   session's transcript).
2. Designed and implemented all 4 phantoms in `sim/phantoms/networks.py`.
3. Implemented `keyboard_control.py` and `motion_scale_control.py`
   sharing `sim/scene.py`.
4. Implemented the Motion Scaling serial protocol parser + device
   wrapper + SOFA bridge controller in `input/`.
5. `mainRun.py` moved to `legacy/` (superseded).
6. Wrote and ran headless tests (all passing as of last run):
   - `tests/validate_scene.py` — all 4 phantoms × variant 0 pass the
     STRICT check (straight insertion stays within the vessel lumen,
     tip clearance ≤ tolerance, no NaN, xtip/rotation respond).
     Variants 1-3 pass a lighter smoke check only (see file docstring:
     mirroring the vessel without also mirroring the BeamAdapter
     spire's fixed coil handedness means a *zero-rotation* straight
     push can legitimately need to fight a mirrored early curve — not
     a bug, real users steer). **Both entry points default to
     variant=0**, which is fully validated.
   - `tests/test_motion_scale_protocol.py` — pure parser unit tests,
     all pass.
   - `tests/validate_entry_points.py` — headless: both entry points'
     `createScene()` build and share the same
     `GuidewireCommandController`; `MotionScaleInputController` mapping
     verified against representative (fake) device input incl. a
     non-1:1 scale ratio and a duplicate/stalled reading. **Last run
     of this file was still executing after 130s+ in background
     (job id `ba8fr8cwg`) — see Blockers below; result not yet
     confirmed at time of this checkpoint.**

## Work remaining
- Confirm `tests/validate_entry_points.py` actually completes and
  passes (was slow/possibly hung — see Blockers).
- Interactive GUI smoke test of `python3 keyboard_control.py` /
  `runSofa keyboard_control.py` (needs a real display; not attempted
  from this headless agent shell — flag as outstanding, do NOT claim
  it works without running it).
- Physical Motion Scaling hardware validation: NOT done (no device
  attached). Parsing/mapping logic IS validated against representative
  input (see above). Mark hardware validation outstanding per project
  policy.
- Delete/clean the large `.venv/` (unrelated PIL/numpy env, currently
  shown as bulk-deleted in `git status` from before this session) and
  `sofa_video_r60_0001.mp4` (5.7MB demo video) — decide whether to
  keep, .gitignore, or remove; not yet actioned.
- Commit the new architecture + phantoms + both entry points once
  validate_entry_points.py is confirmed passing.
- Consider whether `guidewire_controller.py` should move into `sim/`
  for tidiness (currently left at repo root, working, imported by
  `sim/scene.py` — low priority, no functional issue).

## Current blockers / open questions
- `tests/validate_entry_points.py` took >130s and was auto-backgrounded
  (job `ba8fr8cwg`); need to check its actual output next. Suspect
  either (a) genuinely slow pure-Python marching-tetrahedra mesh
  generation run 3x for the 18.5k-vertex Bifurcation Tree phantom in
  that one test file, or (b) `MotionScaleDevice.connect()` in
  `motion_scale_control.createScene()` hanging trying to open the
  placeholder serial port `/dev/tty.usbserial-0001` (should raise
  promptly via pyserial, but not yet confirmed on this machine/OS).
  **Next action starts here.**

## Testing status summary
- Pure geometry (no SOFA): all 4 phantoms × all 4 mirror variants
  generate valid manifold meshes — PASS.
- Headless SOFA physics (variant=0, the default/canonical config):
  all 4 phantoms init, translate, retract (implicitly, translation is
  symmetric), rotate, and keep the guidewire tip inside the vessel
  lumen under straight insertion — PASS.
- Motion-scale parser unit tests — PASS.
- Entry-point sharing + fake-device mapping — result pending (see
  Blockers).
- Interactive GUI (either entry point) — NOT YET RUN.
- Physical hardware — NOT AVAILABLE, NOT CLAIMED.

## Exact next action
Check output of background job `ba8fr8cwg`
(`/private/tmp/claude-501/-Users-Raghavan-Documents-Telesurgery-Scaling/000f8199-9630-483b-8ffa-3dfb2db79141/tasks/ba8fr8cwg.output`
and
`.../scratchpad/entry_points_out.txt`). If it's hung on
`device.connect()`, add a short connect timeout / fix
`MotionScaleDevice` so a missing port fails fast, then re-run. If it
finished and passed, proceed to git commit checkpoint, then attempt
the interactive GUI smoke test and finish the remaining cleanup items
above.
