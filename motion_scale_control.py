"""
motion_scale_control.py — Motion Scaling device-controlled guidewire
simulation.

Run interactively through SOFA's own GUI:

    source scripts/sofa_env.sh
    MS_PORT=/dev/tty.usbserial-XXXX runSofa motion_scale_control.py

or standalone:

    source scripts/sofa_env.sh
    python3 motion_scale_control.py --port /dev/tty.usbserial-XXXX \\
        --phantom 0 --translation-scale 1.0 --rotation-scale 1.0

Drives the guidewire from the physical Motion Scaling ID device's
serial stream (protocol derived from MS_ID_Final/MS_ID_Final.ino —
authoritative for units/direction/behavior; see
input/motion_scale_protocol.py for the exact parsing contract):
CSV lines "distance_mm,rotation_deg" at 115200 baud, both relative to
the device's own power-on zero.

This entry point builds the IDENTICAL shared simulation
keyboard_control.py does, via sim.scene.build_scene() — same
phantoms, same BeamAdapter guidewire, same physics, same
GuidewireCommandController. Only the input source differs: here it is
input.motion_scale_controller.MotionScaleInputController reading
input.motion_scale_device.MotionScaleDevice instead of SOFA key
events.

If no physical device is connected, the scene still loads; a warning
is printed and the guidewire simply will not move from device input
(hardware validation is then outstanding, per project policy of never
claiming hardware validation without the actual device attached).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sim.scene import build_scene, describe_phantoms, select_phantom
from input.motion_scale_device import MotionScaleDevice, DEFAULT_BAUDRATE
from input.motion_scale_controller import MotionScaleInputController

DEFAULT_PORT = os.environ.get("MS_PORT", "/dev/tty.usbserial-0001")


def _scale_from_env_or_argv(name, env_var, default, argv):
    value = float(os.environ.get(env_var, default))
    prefix = f"--{name}="
    for arg in argv:
        if arg.startswith(prefix):
            value = float(arg.split("=", 1)[1])
    return value


def _attach_motion_scale_input(rootNode, port, baudrate, translation_scale, rotation_scale):

    device = MotionScaleDevice(port=port, baudrate=baudrate)

    try:
        device.connect()
    except Exception as exc:
        print(
            "MOTION SCALE DEVICE | WARNING: could not connect on "
            f"{port} ({exc}). Scene will load, but the guidewire will "
            "not respond to the physical device. Hardware validation "
            "is outstanding until a device is connected."
        )

    input_controller = MotionScaleInputController(
        name="MotionScaleInputController",
        command_controller=rootNode.guidewire_command_controller,
        device=device,
        translation_scale=translation_scale,
        rotation_scale=rotation_scale,
    )

    rootNode.addObject(input_controller)

    rootNode.motion_scale_device = device
    rootNode.motion_scale_input_controller = input_controller

    return device, input_controller


def createScene(rootNode):
    """Entry point used by `runSofa motion_scale_control.py`."""

    phantom_id, variant = select_phantom(sys.argv[1:])

    build_scene(rootNode, phantom_id=phantom_id, variant=variant)

    port = os.environ.get("MS_PORT", DEFAULT_PORT)
    baudrate = int(os.environ.get("MS_BAUD", DEFAULT_BAUDRATE))
    translation_scale = _scale_from_env_or_argv(
        "translation-scale", "MS_TRANSLATION_SCALE", 1.0, sys.argv[1:]
    )
    rotation_scale = _scale_from_env_or_argv(
        "rotation-scale", "MS_ROTATION_SCALE", 1.0, sys.argv[1:]
    )

    _attach_motion_scale_input(
        rootNode, port, baudrate, translation_scale, rotation_scale
    )

    print(
        "MOTION SCALE CONTROL | "
        f"port={port} baud={baudrate} | "
        f"translation_scale={translation_scale} rotation_scale={rotation_scale}"
    )
    print("Available phantoms:")
    print(describe_phantoms())

    return rootNode


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phantom", type=int, default=0, choices=[0, 1, 2, 3])
    parser.add_argument("--variant", type=int, default=0, choices=[0, 1, 2, 3])
    parser.add_argument("--port", type=str, default=DEFAULT_PORT)
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUDRATE)
    parser.add_argument("--translation-scale", type=float, default=1.0)
    parser.add_argument("--rotation-scale", type=float, default=1.0)
    args = parser.parse_args()

    os.environ["PHANTOM_ID"] = str(args.phantom)
    os.environ["PHANTOM_VARIANT"] = str(args.variant)
    os.environ["MS_PORT"] = args.port
    os.environ["MS_BAUD"] = str(args.baud)
    os.environ["MS_TRANSLATION_SCALE"] = str(args.translation_scale)
    os.environ["MS_ROTATION_SCALE"] = str(args.rotation_scale)

    import Sofa
    import Sofa.Simulation
    import Sofa.Gui

    root = Sofa.Core.Node("root")

    root.addObject("RequiredPlugin", pluginName=["SofaGLFW"])

    createScene(root)

    Sofa.Simulation.init(root)

    Sofa.Gui.GUIManager.Init("motion_scale_control", "glfw")
    Sofa.Gui.GUIManager.createGUI(root, __file__)
    Sofa.Gui.GUIManager.SetDimension(1080, 1080)
    Sofa.Gui.GUIManager.MainLoop(root)
    Sofa.Gui.GUIManager.closeGUI()


if __name__ == "__main__":
    main()
