# PROGRESS.md — SOFA/BeamAdapter Guidewire Telesurgery Scaling Project

## Objective
Stable SOFA + BeamAdapter endovascular guidewire simulation with FOUR
purpose-designed, ImageCAS-informed vascular phantoms, controllable via
two shared-simulation entry points: `keyboard_control.py` (dev/debug)
and `motion_scale_control.py` (physical Motion Scaling device).

## Status: user-confirmed working via live interactive testing ("That works wonderfully!"). Committing this checkpoint now.

## Environment
- Local SOFA build at `/Users/Raghavan/Documents/SOFA`. Run
  `source scripts/sofa_env.sh` before any `python3 ...` or `runSofa ...`.
- **Use `runSofa -l SofaPython3 -g imgui keyboard_control.py`.**
  `-l SofaPython3` is required (not autoloaded on this build). `-g
  imgui` is required too — `-g glfw` opens a real, live-animating
  window but silently renders only its background grid (no vessel, no
  guidewire, no error; physics underneath still runs correctly).
  `-g imgui` renders everything correctly and adds a full editor UI
  (scene graph, viewport, log panel). `scripts/launch_keyboard_control.sh`
  wraps the correct command; usage:
  `scripts/launch_keyboard_control.sh --phantom=2 --variant=0`
  (must be `--key=value`, not space-separated — runSofa's own CLI
  parser consumes everything after `--argv`).
- pyserial installed (`pip3 install --user --break-system-packages pyserial`).
- Node.js is NOT installed on this machine (game-development skill
  tooling unusable here; screenshots/window control were done manually
  with macOS `screencapture`/`osascript`).

## Architecture (unchanged from before, still shared by both entry points)
- `sim/phantoms/engine.py` — SOFA-free marching-tetrahedra mesh
  generator + `compute_longest_route_length(network)` (caps insertion
  depth per phantom) + `transform_network()` (mirror variants).
- `sim/phantoms/networks.py` — the FOUR phantoms + registry.
- `sim/guidewire.py`, `sim/scene.py`, `guidewire_controller.py`,
  `input/*`, `keyboard_control.py`, `motion_scale_control.py` —
  structure unchanged from the original refactor; physics/collision
  tuning and phantom geometry both updated this session (see below).

## This session: three rounds of real bugs found via live user testing, all fixed
User ran the GUI directly and reported issues across three rounds;
each was root-caused and fixed, not just patched around:

1. **"guidewire escaped through the vessel wall"** — two distinct root
   causes, both fixed:
   - Every phantom's longest branch was shorter than the 180mm
     guidewire, so deep insertion just drove the tip out the open
     (uncapped) far end of a branch. Fixed:
     `compute_longest_route_length()` + `sim/scene.py::build_scene()`
     now caps `GuidewireCommandController.max_length` per phantom.
   - OS key-repeat bursts could move the wire farther in one physics
     step than collision margins were sized for. Fixed: keyboard input
     now queues and rate-limits through a new `onAnimateBeginEvent` in
     `guidewire_controller.py`; `LocalMinDistance` `alarmDistance`
     0.5→2.0 / `contactDistance` 0.2→1.0 in `sim/scene.py` (the
     margin widening turned out to be the more load-bearing fix —
     physics runs at 3000+ Hz interactively, so per-step limiting
     alone wasn't much real-time protection).
   - `tests/validate_burst_input.py` (new) reproduces bursty/randomized
     key-mashing (1-6 keypresses/step, 400 steps/phantom) and asserts
     the tip never exceeds a lumen-clearance tolerance. This test is
     what caught every escape bug this session, including the one
     below.

2. **"phantom is too easy, needs its old difficulty"** — redesigned
   phantoms 0, 2, 3 with cascading bifurcations (4 scored + 4
   distractor targets each), matching phantom 1's (the original
   design's) complexity. Also changed the guidewire's visual color
   from dull gray to bright red (`sim/guidewire.py`) — it was nearly
   invisible against the pale vessel.

3. **"add trifurcations, make it go more into the page / 3D"** — the
   camera's dominant viewing axis is world Y (see `InteractiveCamera`
   in `sim/scene.py`), and every phantom's Y range was only ~20mm, so
   everything looked flat. Fixed: phantoms 0, 2, 3 now each have a
   TRIFURCATION at their main split (left swings deep into +Y, right
   deep into -Y, middle stays shallow — a 5th scored target, G5, added
   to each), with Y ranges now 39-52mm (phantom 1, already having a
   trifurcation and ~53mm Y range, was the template). **First attempt
   at this reintroduced the escape bug**: the new branches diverged
   too steeply right after the split (~0.7-0.8mm lateral per mm
   forward) versus phantom 1's proven ~0.5 max, leaving gaps between
   the fanning-out tubes. Fixed by respacing the post-split waypoints
   to keep divergence rate ≤0.5 everywhere, matching phantom 1's
   pacing. Re-ran `validate_burst_input.py` — clean.

## Testing status
- `tests/validate_burst_input.py` — **PASSED for all 4 phantoms**
  against the final geometry (trifurcations + depth + softened
  divergence). This is the load-bearing regression test for the
  escape bug; run it first after any future geometry change.
- `tests/validate_scene.py` (all 4 phantoms × all 4 mirror variants) —
  was re-running at session end; first 2/16 combos (phantom 0,
  variant 0-1) passed before this checkpoint was written. **Confirm
  it finished clean before trusting mirror variants 1-3** (variant=0,
  what both entry points default to, is already covered by the burst
  test above).
- `tests/validate_entry_points.py`, `tests/test_motion_scale_protocol.py`
  — last known PASS (before the trifurcation/depth redesign); not yet
  re-run against tonight's final geometry. Should still pass (they
  don't depend on specific phantom coordinates) but not yet confirmed.
- **User directly confirmed** the GUI, controls, physics containment,
  and difficulty all work correctly via live interactive testing
  (`runSofa -l SofaPython3 -g imgui keyboard_control.py --argv
  --phantom=2 --variant=0` was the last phantom tried: "That works
  wonderfully!").
- Physical Motion Scaling hardware: still not attached, still not
  validated against real hardware.

## Work remaining
1. Confirm `tests/validate_scene.py`'s full 16-combo run finished
   clean (was still running when this checkpoint was written).
2. Re-run `tests/validate_entry_points.py` and
   `tests/test_motion_scale_protocol.py` for full regression coverage
   against the final phantom geometry.
3. Optionally: user may want to try phantoms 0, 1, 3 interactively too
   (only 0 and 2 were live-tested this session).
4. Physical Motion Scaling hardware: still needs a real device to
   validate sign/scale/feel.
5. Commit + push this checkpoint (in progress as this file is written).

## Current blockers
None. Waiting on item 1 (background test) before the commit, then
committing regardless of items 2-4 since those are non-blocking
follow-ups documented above.

## Exact next action
Check `tests/validate_scene.py`'s final output
(`/private/tmp/claude-501/.../tasks/bshj4zc4m.output` — path is
session-scratchpad-specific and won't exist in a future session; if
resuming cold, just re-run the test). If clean, commit and push
immediately — the user has already confirmed this works live. If it
found something in a mirror variant (1-3), that's lower priority than
what's already confirmed working (variant=0), but still worth a look.
