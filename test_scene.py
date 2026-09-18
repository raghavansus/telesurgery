import Sofa
import numpy as np


class WireController(Sofa.Core.Controller):

    def __init__(self, mechanicalObject):
        super().__init__()
        self.mechanicalObject = mechanicalObject

    def onKeypressedEvent(self, event):

        key = event["key"]

        with self.mechanicalObject.position.writeable() as positions:

            # Current shaft direction = point 0 -> point 1
            direction = positions[1] - positions[0]

            # Normalize direction
            direction = direction / np.linalg.norm(direction)

            # Advance
            if key in ["d", "D", 100, 68]:
                positions[:] += direction * 0.5

            # Retract
            elif key in ["a", "A", 97, 65]:
                positions[:] -= direction * 0.5

            # Rotate around shaft axis
            elif key in ["q", "Q", 113, 81]:
                self.rotate_about_axis(
                    positions,
                    axis=direction,
                    angle_degrees=10
                )

            elif key in ["e", "E", 101, 69]:
                self.rotate_about_axis(
                    positions,
                    axis=direction,
                    angle_degrees=-10
                )

    def rotate_about_axis(self, positions, axis, angle_degrees):

        angle = np.radians(angle_degrees)

        axis = axis / np.linalg.norm(axis)

        x, y, z = axis

        c = np.cos(angle)
        s = np.sin(angle)
        C = 1 - c

        rotation_matrix = np.array([
            [
                c + x*x*C,
                x*y*C - z*s,
                x*z*C + y*s
            ],
            [
                y*x*C + z*s,
                c + y*y*C,
                y*z*C - x*s
            ],
            [
                z*x*C - y*s,
                z*y*C + x*s,
                c + z*z*C
            ]
        ])

        # Rotate around the proximal/base point
        pivot = positions[0].copy()

        for i in range(len(positions)):
            relative_position = positions[i] - pivot
            positions[i] = (
                pivot
                + rotation_matrix @ relative_position
            )


def createScene(rootNode):

    rootNode.addObject(
        "RequiredPlugin",
        pluginName=[
            "Sofa.Component.StateContainer",
            "Sofa.Component.Topology.Container.Dynamic",
            "Sofa.Component.Visual",
            "Sofa.Component.Mapping.Linear"
        ]
    )

    rootNode.addObject("DefaultAnimationLoop")

    wire = rootNode.addChild("Wire")

    points = [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [2.0, 0.0, 0.0],
        [3.0, 0.0, 0.0],
        [4.0, 0.0, 0.0],
        [5.0, 0.0, 0.0],
        [6.0, 0.0, 0.0],
        [7.0, 0.0, 0.0],
        [8.0, 0.0, 0.0],
        [9.0, 0.0, 0.0],

        [10.0, 0.1, 0.0],
        [10.8, 0.3, 0.0],
        [11.5, 0.7, 0.0],
        [12.0, 1.2, 0.0],
        [12.3, 1.8, 0.0],
        [12.4, 2.4, 0.0],
        [12.3, 3.0, 0.0],
        [12.0, 3.5, 0.0],
        [11.6, 3.8, 0.0]
    ]

    edges = [
        [i, i + 1]
        for i in range(len(points) - 1)
    ]

    mechanicalObject = wire.addObject(
        "MechanicalObject",
        name="mechanicalState",
        template="Vec3d",
        position=points,
        showObject=True,
        showObjectScale=3.0
    )

    wire.addObject(
        "EdgeSetTopologyContainer",
        name="topology",
        edges=edges
    )

    visual = wire.addChild("Visual")

    visual.addObject(
        "OglModel",
        name="visualModel",
        position=points,
        edges=edges,
        lineWidth=5.0
    )

    visual.addObject(
        "IdentityMapping",
        input="@../mechanicalState",
        output="@visualModel"
    )

    rootNode.addObject(
        WireController(mechanicalObject)
    )

    return rootNode