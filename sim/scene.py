# sim/scene.py
#
# Single shared scene assembly used by BOTH entry points
# (keyboard_control.py and motion_scale_control.py). Only the input
# source differs between the two entry points; everything about the
# simulation itself — plugins, solvers, collision pipeline, camera,
# phantom geometry, guidewire physics, and the command controller —
# is built here exactly once.

import os

from guidewire_controller import GuidewireCommandController
from sim.phantoms import get_phantom, get_phantom_info, PHANTOMS
from sim.phantoms.engine import create_vessel_from_network
from sim.guidewire import add_guidewire

DEFAULT_PHANTOM_ID = 0
DEFAULT_VARIANT = 0
DEFAULT_GRID_SPACING = 1.75


def configure_root(rootNode):

    rootNode.gravity = [0.0, 0.0, 0.0]
    rootNode.dt = 0.01

    rootNode.addObject(
        "RequiredPlugin",
        pluginName=[
            "BeamAdapter",
            "Sofa.Component.AnimationLoop",
            "Sofa.Component.Collision.Detection.Algorithm",
            "Sofa.Component.Collision.Detection.Intersection",
            "Sofa.Component.Collision.Geometry",
            "Sofa.Component.Collision.Response.Contact",
            "Sofa.Component.Constraint.Projective",
            "Sofa.Component.Constraint.Lagrangian.Solver",
            "Sofa.Component.Constraint.Lagrangian.Correction",
            "Sofa.Component.LinearSolver.Direct",
            "Sofa.Component.ODESolver.Backward",
            "Sofa.Component.SolidMechanics.Spring",
            "Sofa.Component.StateContainer",
            "Sofa.Component.Topology.Container.Constant",
            "Sofa.Component.Topology.Container.Dynamic",
            "Sofa.Component.Topology.Container.Grid",
            "Sofa.Component.Topology.Mapping",
            "Sofa.Component.Visual",
            "Sofa.Component.Setting",
            "Sofa.GL.Component.Rendering3D",
        ],
    )

    rootNode.addObject(
        "VisualStyle",
        displayFlags=[
            "showVisualModels",
            "hideBehaviorModels",
            "hideCollisionModels",
            "hideMappings",
            "hideForceFields",
        ],
    )

    rootNode.addObject(
        "BackgroundSetting",
        color=[1.0, 1.0, 1.0, 1.0],
    )

    # ============================================================
    # COLLISION SYSTEM
    #
    # alarmDistance/contactDistance are sized relative to the
    # guidewire radius (0.445 mm shaft) so contact is detected before
    # the collision geometries interpenetrate, avoiding tunneling
    # through thin vessel walls at normal insertion speeds.
    # ============================================================

    rootNode.addObject("FreeMotionAnimationLoop")

    rootNode.addObject(
        "LCPConstraintSolver",
        mu=0.05,
        tolerance=1e-4,
        maxIt=1000,
        build_lcp=False,
    )

    rootNode.addObject(
        "CollisionPipeline",
        depth=6,
        draw=False,
        verbose=False,
    )

    rootNode.addObject("BruteForceBroadPhase")
    rootNode.addObject("BVHNarrowPhase")

    rootNode.addObject(
        "LocalMinDistance",
        alarmDistance=0.5,
        contactDistance=0.2,
        angleCone=0.5,
    )

    rootNode.addObject(
        "CollisionResponse",
        response="FrictionContactConstraint",
    )

    rootNode.addObject("DefaultVisualManagerLoop")

    rootNode.addObject(
        "InteractiveCamera",
        name="Camera",
        position=[55.0, -110.0, 85.0],
        lookAt=[0.0, 0.0, 65.0],
        fieldOfView=45,
        zNear=0.01,
        zFar=500.0,
        computeZClip=False,
    )


def build_scene(
    rootNode,
    phantom_id=DEFAULT_PHANTOM_ID,
    variant=DEFAULT_VARIANT,
    grid_spacing=DEFAULT_GRID_SPACING,
    translation_step=0.5,
    rotation_step_degrees=2.0,
):
    """
    Build the complete, shared SOFA scene: plugins/collision/camera,
    the selected phantom, and the BeamAdapter guidewire with its
    command controller. Returns rootNode for chaining.

    Both keyboard_control.py and motion_scale_control.py call this
    exact function; they differ only in what drives
    rootNode.guidewire_command_controller.apply_command(...) afterward.
    """

    configure_root(rootNode)

    phantom_info = get_phantom_info(phantom_id)
    network = get_phantom(phantom_id, variant=variant)

    scene_info = create_vessel_from_network(
        rootNode,
        network,
        grid_spacing=grid_spacing,
    )

    entry_z = network["entry_position"][2]
    deployment_origin_z = entry_z - 8.0

    deploy_controller, total_wire_length = add_guidewire(
        rootNode,
        deployment_origin_z=deployment_origin_z,
    )

    command_controller = GuidewireCommandController(
        name="GuidewireCommandController",
        deploy_controller=deploy_controller,
        max_length=total_wire_length,
        translation_step=translation_step,
        rotation_step_degrees=rotation_step_degrees,
    )

    rootNode.addObject(command_controller)

    rootNode.scene_info = scene_info
    rootNode.guidewire_command_controller = command_controller
    rootNode.phantom_id = phantom_id
    rootNode.phantom_variant = variant

    print(
        "SCENE | "
        f"phantom={phantom_id} ({phantom_info['name']}) | "
        f"variant={variant} | "
        f"targets={list(network['targets'].keys())}"
    )

    return rootNode


def select_phantom(argv=None):
    """
    Shared phantom/variant selection for both entry points, so
    `runSofa keyboard_control.py` (or motion_scale_control.py), plain
    `python3 keyboard_control.py --phantom N --variant M`, and
    automated tests all agree on the same precedence:

      1. --phantom=N / --variant=M in argv (if given)
      2. PHANTOM_ID / PHANTOM_VARIANT environment variables
      3. defaults (0, 0)
    """

    phantom_id = int(os.environ.get("PHANTOM_ID", DEFAULT_PHANTOM_ID))
    variant = int(os.environ.get("PHANTOM_VARIANT", DEFAULT_VARIANT))

    for arg in (argv or []):
        if arg.startswith("--phantom="):
            phantom_id = int(arg.split("=", 1)[1])
        elif arg.startswith("--variant="):
            variant = int(arg.split("=", 1)[1])

    valid_ids = [entry["id"] for entry in PHANTOMS]
    if phantom_id not in valid_ids:
        raise ValueError(f"phantom_id={phantom_id} not in {valid_ids}")
    if variant not in (0, 1, 2, 3):
        raise ValueError(f"variant={variant} must be 0, 1, 2, or 3")

    return phantom_id, variant


def describe_phantoms():
    lines = []
    for entry in PHANTOMS:
        lines.append(f"  [{entry['id']}] {entry['name']} - {entry['description']}")
    return "\n".join(lines)
