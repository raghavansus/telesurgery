import Sofa
import math


# ================================================================
# NUMERICAL GUIDEWIRE COMMAND CONTROLLER
# ================================================================

class GuidewireCommandController(Sofa.Core.Controller):

    def __init__(
        self,
        deploy_controller,
        max_length,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.deploy_controller = deploy_controller
        self.max_length = max_length

        self.translation_step = 0.5
        self.rotation_step = math.radians(5.0)

    def apply_command(
        self,
        translation=0.0,
        rotation=0.0
    ):

        current_xtip = list(
            self.deploy_controller.xtip.value
        )

        new_xtip = (
            float(current_xtip[0])
            + float(translation)
        )

        new_xtip = max(
            0.0,
            min(
                self.max_length,
                new_xtip
            )
        )

        current_xtip[0] = new_xtip

        self.deploy_controller.xtip.value = current_xtip

        current_rotation = list(
            self.deploy_controller.rotationInstrument.value
        )

        current_rotation[0] += float(rotation)

        self.deploy_controller.rotationInstrument.value = (
            current_rotation
        )

        print(
            "COMMAND | "
            f"translation={translation:.3f} | "
            f"rotation={math.degrees(rotation):.1f} deg | "
            f"xtip={new_xtip:.3f} | "
            f"total rotation="
            f"{math.degrees(current_rotation[0]):.1f} deg"
        )

    # ============================================================
    # TEMPORARY KEYBOARD TESTING
    #
    # Ctrl + Shift + D = insert
    # Ctrl + Shift + A = retract
    # Ctrl + Shift + E = rotate +
    # Ctrl + Shift + Q = rotate -
    # ============================================================

    def onKeypressedEvent(self, event):

        key = event["key"]

        if isinstance(key, int):
            try:
                key = chr(key)
            except:
                return

        key = str(key).lower()

        if key == "d":

            self.apply_command(
                translation=self.translation_step,
                rotation=0.0
            )

        elif key == "a":

            self.apply_command(
                translation=-self.translation_step,
                rotation=0.0
            )

        elif key == "e":

            self.apply_command(
                translation=0.0,
                rotation=self.rotation_step
            )

        elif key == "q":

            self.apply_command(
                translation=0.0,
                rotation=-self.rotation_step
            )


# ================================================================
# SCENE
# ================================================================

def createScene(rootNode):

    rootNode.gravity = [
        0.0,
        0.0,
        0.0
    ]

    rootNode.dt = 0.01

    # ============================================================
    # PLUGINS
    # ============================================================

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

            "Sofa.Component.Visual",
            "Sofa.Component.Setting",

            "Sofa.GL.Component.Rendering3D",
        ]
    )

    # ============================================================
    # DISPLAY
    # ============================================================

    rootNode.addObject(
        "VisualStyle",
        displayFlags=[
            "showVisualModels",
            "showBehaviorModels",
            "hideCollisionModels",
            "hideMappings",
            "hideForceFields",
        ],
    )

    # ============================================================
    # SOLID WHITE BACKGROUND
    # ============================================================

    rootNode.addObject(
        "BackgroundSetting",
        color=[
            1.0,
            1.0,
            1.0,
            1.0
        ]
    )

    # ============================================================
    # COLLISION SYSTEM
    # ============================================================

    rootNode.addObject(
        "FreeMotionAnimationLoop"
    )

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

    rootNode.addObject(
        "BruteForceBroadPhase"
    )

    rootNode.addObject(
        "BVHNarrowPhase"
    )

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

    rootNode.addObject(
        "DefaultVisualManagerLoop"
    )

    # ============================================================
    # CAMERA
    # ============================================================

    rootNode.addObject(
        "InteractiveCamera",
        name="Camera",

        position=[
            40.0,
            -65.0,
            30.0
        ],

        lookAt=[
            3.0,
            0.0,
            28.0
        ],

        fieldOfView=45,

        zNear=0.01,
        zFar=500.0,

        computeZClip=False,
    )

    # ============================================================
    # VESSEL GEOMETRY
    # ============================================================

    vessel = rootNode.addChild(
        "Vessel"
    )

    vessel_radius = 3.0

    points_per_ring = 24
    rings_per_segment = 5

    vessel_points = []
    vessel_edges = []
    vessel_triangles = []

    # ============================================================
    # CYLINDER SEGMENT GENERATOR
    # ============================================================

    def add_vessel_segment(
        start,
        end,
        radius
    ):

        start_index = len(
            vessel_points
        )

        sx, sy, sz = start
        ex, ey, ez = end

        dx = ex - sx
        dy = ey - sy
        dz = ez - sz

        segment_length = math.sqrt(
            dx * dx
            + dy * dy
            + dz * dz
        )

        ux = dx / segment_length
        uy = dy / segment_length
        uz = dz / segment_length

        # --------------------------------------------------------
        # PERPENDICULAR BASIS
        # --------------------------------------------------------

        if abs(uz) < 0.9:

            px = -uy
            py = ux
            pz = 0.0

        else:

            px = 1.0
            py = 0.0
            pz = 0.0

        p_length = math.sqrt(
            px * px
            + py * py
            + pz * pz
        )

        px /= p_length
        py /= p_length
        pz /= p_length

        qx = (
            uy * pz
            - uz * py
        )

        qy = (
            uz * px
            - ux * pz
        )

        qz = (
            ux * py
            - uy * px
        )

        # --------------------------------------------------------
        # BUILD RINGS
        # --------------------------------------------------------

        for ring in range(
            rings_per_segment
        ):

            t = (
                ring /
                (rings_per_segment - 1)
            )

            cx = sx + dx * t
            cy = sy + dy * t
            cz = sz + dz * t

            for i in range(
                points_per_ring
            ):

                angle = (
                    2.0
                    * math.pi
                    * i
                    / points_per_ring
                )

                cos_a = math.cos(angle)
                sin_a = math.sin(angle)

                x = (
                    cx
                    + radius * cos_a * px
                    + radius * sin_a * qx
                )

                y = (
                    cy
                    + radius * cos_a * py
                    + radius * sin_a * qy
                )

                z = (
                    cz
                    + radius * cos_a * pz
                    + radius * sin_a * qz
                )

                vessel_points.append(
                    [
                        x,
                        y,
                        z
                    ]
                )

        # --------------------------------------------------------
        # CIRCULAR EDGES
        # --------------------------------------------------------

        for ring in range(
            rings_per_segment
        ):

            ring_start = (
                start_index
                + ring * points_per_ring
            )

            for i in range(
                points_per_ring
            ):

                a = ring_start + i

                b = (
                    ring_start
                    + (
                        (i + 1)
                        % points_per_ring
                    )
                )

                vessel_edges.append(
                    [a, b]
                )

        # --------------------------------------------------------
        # LONGITUDINAL CONNECTIONS + TRIANGLES
        # --------------------------------------------------------

        for ring in range(
            rings_per_segment - 1
        ):

            current_ring = (
                start_index
                + ring
                * points_per_ring
            )

            next_ring = (
                start_index
                + (ring + 1)
                * points_per_ring
            )

            for i in range(
                points_per_ring
            ):

                a = current_ring + i

                b = (
                    current_ring
                    + (
                        (i + 1)
                        % points_per_ring
                    )
                )

                c = next_ring + i

                d = (
                    next_ring
                    + (
                        (i + 1)
                        % points_per_ring
                    )
                )

                vessel_edges.append(
                    [a, c]
                )

                vessel_triangles.append(
                    [a, c, d]
                )

                vessel_triangles.append(
                    [a, d, b]
                )

    # ============================================================
    # POLYLINE VESSEL HELPER
    # ============================================================

    def add_vessel_path(points):

        for i in range(
            len(points) - 1
        ):

            add_vessel_segment(
                points[i],
                points[i + 1],
                vessel_radius
            )

    # ============================================================
    #
    # FOUR-TARGET MOTION-SCALING COURSE
    #
    # ============================================================

    # ============================================================
    # ENTRY / CURVED TRUNK
    # ============================================================

    trunk = [

        [0.0, 0.0, 0.0],

        [0.0, 0.0, 7.0],

        [1.0, 0.0, 13.0],

        [3.0, 0.0, 18.0],

        [5.0, 0.0, 23.0],
    ]

    add_vessel_path(
        trunk
    )

    first_bifurcation = [
        5.0,
        0.0,
        23.0
    ]

    # ============================================================
    # UPPER ROUTE
    # ============================================================

    upper_route = [

        first_bifurcation,

        [10.0, 0.0, 28.0],

        [14.0, 0.0, 34.0],
    ]

    add_vessel_path(
        upper_route
    )

    upper_split = [
        14.0,
        0.0,
        34.0
    ]

    # ============================================================
    # TARGET 1
    # Gentle terminal branch
    # ============================================================

    target_1 = [
        10.0,
        0.0,
        44.0
    ]

    target_1_path = [

        upper_split,

        [12.0, 0.0, 39.0],

        target_1,
    ]

    add_vessel_path(
        target_1_path
    )

    # ============================================================
    # TARGET 2
    # More lateral terminal branch
    # ============================================================

    target_2 = [
        23.0,
        0.0,
        42.0
    ]

    target_2_path = [

        upper_split,

        [19.0, 0.0, 37.0],

        target_2,
    ]

    add_vessel_path(
        target_2_path
    )

    # ============================================================
    # LOWER ROUTE
    #
    # S-curve removed.
    # This is now a smooth gradual branch.
    # ============================================================

    lower_route = [

        first_bifurcation,

        [1.0, 0.0, 29.0],

        [-2.0, 0.0, 35.0],

        [-2.0, 0.0, 41.0],
    ]

    add_vessel_path(
        lower_route
    )

    lower_split = [
        -2.0,
        0.0,
        41.0
    ]

    # ============================================================
    # TARGET 3
    # ============================================================

    target_3 = [
        4.0,
        0.0,
        51.0
    ]

    target_3_path = [

        lower_split,

        [1.0, 0.0, 46.0],

        target_3,
    ]

    add_vessel_path(
        target_3_path
    )

    # ============================================================
    # TARGET 4
    # ============================================================

    target_4 = [
        -12.0,
        0.0,
        50.0
    ]

    target_4_path = [

        lower_split,

        [-7.0, 0.0, 45.0],

        target_4,
    ]

    add_vessel_path(
        target_4_path
    )

    # ============================================================
    # VESSEL STATE
    # ============================================================

    vessel.addObject(
        "MechanicalObject",
        name="VesselDOFs",

        template="Vec3d",

        position=vessel_points,

        showObject=False,
    )

    vessel.addObject(
        "MeshTopology",
        name="VesselTopology",

        position=vessel_points,

        triangles=vessel_triangles,
    )

    # ============================================================
    # VESSEL COLLISION
    # ============================================================

    vessel.addObject(
        "TriangleCollisionModel",
        name="VesselTriangles",

        moving=False,
        simulated=False,
    )

    vessel.addObject(
        "LineCollisionModel",
        name="VesselLines",

        moving=False,
        simulated=False,
    )

    vessel.addObject(
        "PointCollisionModel",
        name="VesselPointsCollision",

        moving=False,
        simulated=False,
    )

    # ============================================================
    # TRANSPARENT VESSEL VISUAL
    # ============================================================

    vessel.addObject(
        "OglModel",
        name="VesselVisual",

        position=vessel_points,

        edges=vessel_edges,

        color=[
            0.3,
            0.6,
            0.9,
            0.20
        ],

        lineWidth=2.0,
    )

    # ============================================================
    # FOUR TARGET MARKERS
    # ============================================================

    targets = [

        ("Target1", target_1),

        ("Target2", target_2),

        ("Target3", target_3),

        ("Target4", target_4),
    ]

    for name, position in targets:

        target_node = rootNode.addChild(
            name
        )

        target_node.addObject(
            "MechanicalObject",
            name="Marker",

            template="Vec3d",

            position=[
                position
            ],

            showObject=True,

            showObjectScale=1.0,
        )

    # ============================================================
    # GUIDEWIRE REST SHAPE
    # ============================================================

    rest = rootNode.addChild(
        "GuidewireRestShape"
    )

    straight_length = 54.0
    tip_length = 6.0

    total_wire_length = (
        straight_length
        + tip_length
    )

    # ============================================================
    # STRAIGHT SHAFT
    # ============================================================

    rest.addObject(
        "RodStraightSection",
        name="StraightSection",

        youngModulus=20000,
        poissonRatio=0.3,

        radius=0.2,

        massDensity=0.00000155,

        nbBeams=54,
        nbEdgesCollis=54,
        nbEdgesVisu=110,

        length=straight_length,
    )

    # ============================================================
    # CURVED DISTAL TIP
    # ============================================================

    rest.addObject(
        "RodSpireSection",
        name="TipSection",

        youngModulus=20000,
        poissonRatio=0.3,

        radius=0.2,

        massDensity=0.00000155,

        nbBeams=6,
        nbEdgesCollis=6,
        nbEdgesVisu=30,

        length=tip_length,

        spireDiameter=12.0,

        spireHeight=0.0,
    )

    # ============================================================
    # REST SHAPE
    # ============================================================

    rest.addObject(
        "WireRestShape",
        name="BeamRestShape",

        template="Rigid3d",

        wireMaterials=(
            "@StraightSection "
            "@TipSection"
        ),

        printLog=True,
    )

    rest.addObject(
        "EdgeSetTopologyContainer",
        name="meshLinesBeam",
    )

    rest.addObject(
        "EdgeSetTopologyModifier",
        name="Modifier",
    )

    rest.addObject(
        "EdgeSetGeometryAlgorithms",
        name="GeomAlgo",

        template="Rigid3d",
    )

    rest.addObject(
        "MechanicalObject",
        name="RestDOFs",

        template="Rigid3d",

        showObject=False,
    )

    # ============================================================
    # ACTIVE GUIDEWIRE
    # ============================================================

    wire = rootNode.addChild(
        "Guidewire"
    )

    # ============================================================
    # SOLVERS
    # ============================================================

    wire.addObject(
        "EulerImplicitSolver",
        name="ODESolver",

        rayleighStiffness=0.2,
        rayleighMass=0.1,
    )

    wire.addObject(
        "BTDLinearSolver",
        name="LinearSolver",

        verbose=False,
    )

    # ============================================================
    # COLLAPSED DEPLOYMENT TOPOLOGY
    # ============================================================

    wire.addObject(
        "RegularGridTopology",
        name="MeshLines",

        nx=61,
        ny=1,
        nz=1,

        xmin=0.0,
        xmax=0.0,

        ymin=0.0,
        ymax=0.0,

        zmin=0.0,
        zmax=0.0,

        p0=[
            0.0,
            0.0,
            0.0
        ],

        drawEdges=True,
    )

    # ============================================================
    # RIGID FRAMES
    # ============================================================

    wire.addObject(
        "MechanicalObject",
        name="DOFs",

        template="Rigid3d",

        ry=-90,

        showObject=True,

        showObjectScale=0.15,
    )

    # ============================================================
    # BEAM INTERPOLATION
    # ============================================================

    wire.addObject(
        "WireBeamInterpolation",
        name="BeamInterpolation",

        WireRestShape=(
            "@../GuidewireRestShape/"
            "BeamRestShape"
        ),

        printLog=True,
    )

    # ============================================================
    # BEAM MECHANICS
    # ============================================================

    wire.addObject(
        "AdaptiveBeamForceFieldAndMass",
        name="BeamForceField",

        interpolation="@BeamInterpolation",
    )

    # ============================================================
    # FIXED PROXIMAL NODE
    # ============================================================

    wire.addObject(
        "FixedProjectiveConstraint",
        name="FixedConstraint",

        indices=[0],
    )

    # ============================================================
    # BEAMADAPTER DEPLOYMENT CONTROLLER
    # ============================================================

    deploy_controller = wire.addObject(
        "InterventionalRadiologyController",
        name="DeployController",

        template="Rigid3d",

        instruments="BeamInterpolation",

        topology="@MeshLines",

        fixedConstraint="@FixedConstraint",

        startingPos=[
            0.0,
            0.0,
            0.0,

            0.0,
            -0.7071068,
            0.0,
            0.7071068,
        ],

        xtip=[
            10.0
        ],

        rotationInstrument=[
            0.0
        ],

        step=0.5,

        speed=0.0,

        controlledInstrument=0,

        listening=True,

        printLog=True,
    )

    # ============================================================
    # CONSTRAINT CORRECTION
    # ============================================================

    wire.addObject(
        "LinearSolverConstraintCorrection",
        name="ConstraintCorrection",

        wire_optimization=True,

        printLog=False,
    )

    # ============================================================
    # PROXIMAL SPRING
    # ============================================================

    wire.addObject(
        "RestShapeSpringsForceField",
        name="RestShapeConstraint",

        points=(
            "@DeployController."
            "indexFirstNode"
        ),

        stiffness=1e8,
        angularStiffness=1e8,
    )

    # ============================================================
    # GUIDEWIRE COLLISION
    # ============================================================

    collision = wire.addChild(
        "CollisionModel"
    )

    collision.addObject(
        "EdgeSetTopologyContainer",
        name="CollisionEdges",
    )

    collision.addObject(
        "EdgeSetTopologyModifier",
        name="CollisionModifier",
    )

    collision.addObject(
        "MechanicalObject",
        name="CollisionDOFs",

        template="Vec3d",
    )

    collision.addObject(
        "MultiAdaptiveBeamMapping",
        name="CollisionMapping",

        controller="../DeployController",

        useCurvAbs=True,

        printLog=False,
    )

    collision.addObject(
        "LineCollisionModel",
        name="GuidewireLines",
    )

    collision.addObject(
        "PointCollisionModel",
        name="GuidewirePoints",
    )

    # ============================================================
    # NUMERICAL COMMAND INTERFACE
    # ============================================================

    rootNode.addObject(
        GuidewireCommandController(
            name="GuidewireCommandController",

            deploy_controller=deploy_controller,

            max_length=total_wire_length,
        )
    )

    return rootNode