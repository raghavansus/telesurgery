# tests/validate_entry_points.py
#
# Headless validation that:
#   - keyboard_control.createScene() and motion_scale_control.createScene()
#     both build successfully and share the exact same underlying
#     simulation (sim.scene.build_scene / GuidewireCommandController).
#   - motion_scale_control's device -> controller mapping logic works
#     correctly given REPRESENTATIVE (not real hardware) serial
#     readings, including a scaling ratio other than 1:1 and a
#     dropped-reading scenario.
#
# Run with:
#   source scripts/sofa_env.sh
#   python3 tests/validate_entry_points.py

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Sofa
import Sofa.Simulation

os.environ["PHANTOM_ID"] = "1"
os.environ["PHANTOM_VARIANT"] = "0"

import keyboard_control
import motion_scale_control
from guidewire_controller import GuidewireCommandController
from input.motion_scale_controller import MotionScaleInputController


class FakeDevice:
    """Stands in for input.motion_scale_device.MotionScaleDevice: same
    poll()/latest_distance_mm/latest_rotation_deg interface, fed a
    scripted sequence of representative (distance_mm, rotation_deg)
    readings instead of real serial bytes."""

    def __init__(self, readings):
        self.readings = list(readings)
        self.index = -1
        self.latest_distance_mm = 0.0
        self.latest_rotation_deg = 0.0
        self.connected = True

    def poll(self):
        if self.index + 1 < len(self.readings):
            self.index += 1
            self.latest_distance_mm, self.latest_rotation_deg = self.readings[self.index]
            return True
        return False


def test_keyboard_entry_point():
    root = Sofa.Core.Node("root")
    keyboard_control.createScene(root)
    Sofa.Simulation.init(root)

    ctrl = root.guidewire_command_controller
    assert isinstance(ctrl, GuidewireCommandController)

    start = ctrl.get_insertion_depth()
    ctrl.apply_command(translation=3.0, rotation=0.0)
    assert ctrl.get_insertion_depth() == start + 3.0

    print("OK keyboard_control.createScene() builds and controls the guidewire")


def test_motion_scale_entry_point_shares_simulation():
    root = Sofa.Core.Node("root")
    motion_scale_control.createScene(root)
    Sofa.Simulation.init(root)

    ctrl = root.guidewire_command_controller
    assert isinstance(ctrl, GuidewireCommandController), (
        "motion_scale_control must use the SAME GuidewireCommandController "
        "class as keyboard_control, not a separate implementation"
    )
    assert hasattr(root, "motion_scale_input_controller")
    assert root.scene_info is not None

    print("OK motion_scale_control.createScene() shares GuidewireCommandController")


def test_motion_scale_mapping_1to1():
    root = Sofa.Core.Node("root")
    from sim.scene import build_scene
    build_scene(root, phantom_id=1, variant=0)
    Sofa.Simulation.init(root)

    ctrl = root.guidewire_command_controller
    base_insertion = ctrl.get_insertion_depth()
    base_rotation = ctrl.get_rotation_degrees()

    device = FakeDevice([
        (0.0, 0.0),      # homing reading, no motion yet
        (5.0, 10.0),     # +5mm device motion, +10deg device rotation
        (5.0, 10.0),     # duplicate reading (simulates a stalled line)
        (12.0, -20.0),   # further insertion, rotate the other way
    ])

    input_ctrl = MotionScaleInputController(
        name="TestMotionScaleInputController",
        command_controller=ctrl,
        device=device,
        translation_scale=1.0,
        rotation_scale=1.0,
    )

    # Homing step: first poll() only zeroes, does not move the wire.
    input_ctrl.onAnimateBeginEvent({})
    assert ctrl.get_insertion_depth() == base_insertion

    input_ctrl.onAnimateBeginEvent({})
    assert abs(ctrl.get_insertion_depth() - (base_insertion + 5.0)) < 1e-9
    assert abs(ctrl.get_rotation_degrees() - (base_rotation + 10.0)) < 1e-9

    input_ctrl.onAnimateBeginEvent({})  # duplicate reading -> no change
    assert abs(ctrl.get_insertion_depth() - (base_insertion + 5.0)) < 1e-9

    input_ctrl.onAnimateBeginEvent({})
    assert abs(ctrl.get_insertion_depth() - (base_insertion + 12.0)) < 1e-9
    assert abs(ctrl.get_rotation_degrees() - (base_rotation - 20.0)) < 1e-9

    print("OK MotionScaleInputController 1:1 mapping matches representative input")


def test_motion_scale_mapping_ratio():
    root = Sofa.Core.Node("root")
    from sim.scene import build_scene
    build_scene(root, phantom_id=0, variant=0)
    Sofa.Simulation.init(root)

    ctrl = root.guidewire_command_controller
    base_insertion = ctrl.get_insertion_depth()

    device = FakeDevice([(0.0, 0.0), (10.0, 0.0)])

    input_ctrl = MotionScaleInputController(
        name="TestMotionScaleRatio",
        command_controller=ctrl,
        device=device,
        translation_scale=0.5,   # 2:1 down-scaling
        rotation_scale=1.0,
    )

    input_ctrl.onAnimateBeginEvent({})  # homing
    input_ctrl.onAnimateBeginEvent({})  # 10mm device motion * 0.5 scale

    expected = base_insertion + 5.0
    actual = ctrl.get_insertion_depth()
    assert abs(actual - expected) < 1e-9, f"expected {expected}, got {actual}"

    print("OK MotionScaleInputController honors a non-1:1 translation_scale")


def main():
    test_keyboard_entry_point()
    test_motion_scale_entry_point_shares_simulation()
    test_motion_scale_mapping_1to1()
    test_motion_scale_mapping_ratio()
    print("ALL ENTRY POINT VALIDATIONS PASSED")


if __name__ == "__main__":
    main()
