"""
keyboard_control.py — keyboard-controlled guidewire simulation.

Run interactively through SOFA's own GUI (recommended; confirmed
working end-to-end -- vessel, targets, AND guidewire all visible --
by both an agent screenshot and a live user in this project). Two
flags matter on this local SOFA build:

  -l SofaPython3   required -- not in runSofa's default plugin
                   autoload list here; without it runSofa refuses to
                   load a .py scene file at all.
  -g imgui         required -- `-g glfw` opens a real, live-animating
                   window (physics runs correctly, key presses do
                   move the wire) but silently renders ONLY its
                   background grid: no vessel, no guidewire, no
                   error. `-g imgui` renders everything correctly and
                   adds a full editor UI (scene graph, viewport, log).

    source scripts/sofa_env.sh
    runSofa -l SofaPython3 -g imgui keyboard_control.py
    runSofa -l SofaPython3 -g imgui keyboard_control.py --argv --phantom=2 --variant=0

or scripts/launch_keyboard_control.sh --phantom=2 --variant=0

or standalone (opens a GLFW window directly, no runSofa needed) --
same `-g glfw` blank-render limitation as above applies here too:

    source scripts/sofa_env.sh
    python3 keyboard_control.py --phantom 2 --variant 0

Keyboard mapping (handled by GuidewireCommandController.onKeypressedEvent
in guidewire_controller.py):

    d   insert
    a   retract
    e   rotate +
    q   rotate -

keyboard_control.py and motion_scale_control.py build the IDENTICAL
shared simulation via sim.scene.build_scene() — same phantoms, same
BeamAdapter guidewire, same physics, same GuidewireCommandController.
Only the input source differs.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sim.scene import build_scene, describe_phantoms, select_phantom


def createScene(rootNode):
    """Entry point used by `runSofa keyboard_control.py`."""

    phantom_id, variant = select_phantom(sys.argv[1:])

    build_scene(rootNode, phantom_id=phantom_id, variant=variant)

    print("KEYBOARD CONTROL | d=insert  a=retract  e=rotate+  q=rotate-")
    print("Available phantoms:")
    print(describe_phantoms())

    return rootNode


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phantom", type=int, default=0, choices=[0, 1, 2, 3])
    parser.add_argument("--variant", type=int, default=0, choices=[0, 1, 2, 3])
    args = parser.parse_args()

    os.environ["PHANTOM_ID"] = str(args.phantom)
    os.environ["PHANTOM_VARIANT"] = str(args.variant)

    import Sofa
    import Sofa.Simulation
    import Sofa.Gui

    root = Sofa.Core.Node("root")

    # Loading SofaGLFW registers the "glfw" GUIManager backend during
    # init; without it only the headless "batch" backend is available.
    #
    # KNOWN LIMITATION (this local SOFA build): a scene built and
    # init'd by a standalone script and then handed to GUIManager's
    # "glfw" backend opens a real, live-animating window (confirmed:
    # FPS counter updates), but only draws SofaGLFW's background grid
    # -- no scene geometry -- with no error. The identical scene
    # (same build_scene()) renders correctly when loaded the normal
    # way via `runSofa -l SofaPython3 keyboard_control.py` (confirmed
    # working: vessel mesh and target markers render correctly). If
    # you hit a blank grid here, use runSofa instead; see README/
    # PROGRESS.md.
    root.addObject("RequiredPlugin", pluginName=["SofaGLFW"])

    createScene(root)

    Sofa.Simulation.init(root)

    Sofa.Gui.GUIManager.Init("keyboard_control", "glfw")
    Sofa.Gui.GUIManager.createGUI(root, __file__)
    Sofa.Gui.GUIManager.SetDimension(1080, 1080)
    print("SOFA GUI WINDOW READY", flush=True)
    Sofa.Gui.GUIManager.MainLoop(root)
    Sofa.Gui.GUIManager.closeGUI()


if __name__ == "__main__":
    main()
