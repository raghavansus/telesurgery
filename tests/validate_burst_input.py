# tests/validate_burst_input.py
#
# Reproduces the likely cause of the "guidewire escaped through the
# vessel wall" bug reported during live interactive use: OS key-repeat
# (or several keys pressed close together) can fire several
# onKeypressedEvent calls before the next physics step runs. If those
# were applied to xtip/rotation instantly, a burst could move the
# guidewire farther in one physics step than the collision system's
# alarm/contact margins are sized for, tunneling through the thin
# vessel wall.
#
# GuidewireCommandController now queues keyboard motion and drains it
# rate-limited (at most one step's worth per physics step) via
# onAnimateBeginEvent. This test simulates bursty key-repeat -- many
# onKeypressedEvent calls fired back-to-back before each animate() --
# and checks the tip never escapes the lumen and never NaNs, across
# a full traversal (not just the first ~30mm like validate_scene.py).
#
#   source scripts/sofa_env.sh
#   python3 tests/validate_burst_input.py

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Sofa
import Sofa.Simulation

from sim.scene import build_scene
from sim.phantoms import get_phantom, PHANTOMS
from sim.phantoms.engine import (
    sample_polyline,
    build_segments,
    point_segment_distance_t,
)


def nearest_lumen_clearance(point, segments):
    best = float("inf")
    for a, ra, b, rb in segments:
        distance, t = point_segment_distance_t(point, a, b)
        local_radius = ra + (rb - ra) * t
        clearance = distance - local_radius
        if clearance < best:
            best = clearance
    return best


def has_nan(values):
    for row in values:
        for v in row:
            if math.isnan(v) or math.isinf(v):
                return True
    return False


def fire_keypress(ctrl, key):
    ctrl.onKeypressedEvent({"key": key})


def validate_burst(phantom_id, variant=0, steps=400, seed=0):

    random.seed(seed)

    network = get_phantom(phantom_id, variant=variant)
    sampled_paths = [sample_polyline(p, spacing=2.0) for p in network["paths"]]
    segments = build_segments(sampled_paths)

    tolerance = 6.0

    root = Sofa.Core.Node("root")
    build_scene(root, phantom_id=phantom_id, variant=variant)
    Sofa.Simulation.init(root)

    ctrl = root.guidewire_command_controller
    dof = root.getChild("Guidewire").getObject("DOFs")

    max_clearance_seen = -float("inf")
    max_clearance_step = -1

    for step in range(steps):

        # Mostly insert (so we actually traverse the vessel), with
        # occasional retraction/rotation bursts mixed in, mimicking a
        # human mashing keys rather than one clean tap per frame.
        burst_size = random.randint(1, 6)

        for _ in range(burst_size):
            r = random.random()
            if r < 0.55:
                fire_keypress(ctrl, "d")
            elif r < 0.65:
                fire_keypress(ctrl, "a")
            elif r < 0.85:
                fire_keypress(ctrl, "e")
            else:
                fire_keypress(ctrl, "q")

        Sofa.Simulation.animate(root, root.dt.value)

        positions = dof.position.value
        assert not has_nan(positions), (
            f"phantom={phantom_id}: NaN/Inf at step {step} "
            f"(xtip={ctrl.get_insertion_depth():.2f})"
        )

        tip_position = tuple(positions[-1][:3])
        clearance = nearest_lumen_clearance(tip_position, segments)

        if clearance > max_clearance_seen:
            max_clearance_seen = clearance
            max_clearance_step = step

        assert clearance <= tolerance, (
            f"phantom={phantom_id}: tip escaped vessel at step {step}, "
            f"clearance={clearance:.2f}mm at {tip_position}, "
            f"xtip={ctrl.get_insertion_depth():.2f}"
        )

    print(
        f"OK phantom={phantom_id} variant={variant} | "
        f"{steps} bursty steps | "
        f"final xtip={ctrl.get_insertion_depth():.1f} | "
        f"worst clearance={max_clearance_seen:.2f}mm at step {max_clearance_step}"
    )


def main():
    failures = []

    for entry in PHANTOMS:
        try:
            validate_burst(entry["id"], variant=0)
        except AssertionError as exc:
            failures.append(str(exc))
            print(f"FAIL: {exc}")

    print("-" * 60)
    if failures:
        print(f"{len(failures)} FAILURE(S)")
        sys.exit(1)
    else:
        print("ALL BURST-INPUT VALIDATIONS PASSED")


if __name__ == "__main__":
    main()
