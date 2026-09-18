import Sofa

from guidewire_controller import GuidewireCommandController
from scenes.study_phantom import create_vessel


def createScene(rootNode):

    # ============================================================
    # GLOBAL SETTINGS
    # ============================================================

    rootNode.gravity = [
        0.0,
        0.0,
        0.0,
    ]

    rootNode.dt = 0.01


    # ============================================================
    # REQUIRED PLUGINS
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
            "Sofa.Component.Topology.Mapping",

            "Sofa.Component.Visual",
            "Sofa.Component.Setting",

            "Sofa.GL.Component.Rendering3D",
        ],
    )


    # ============================================================
    # DISPLAY
    # ============================================================

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
        color=[
            1.0,
            1.0,
            1.0,
            1.0,
        ],
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
            55.0,
            -110.0,
            85.0,
        ],

        lookAt=[
            0.0,
            0.0,
            65.0,
        ],

        fieldOfView=45,

        zNear=0.01,
        zFar=500.0,

        computeZClip=False,
    )


    # ============================================================
    # STUDY PHANTOM
    #
    # variant:
    #   0 = original
    #   1 = mirror X
    #   2 = mirror Y
    #   3 = mirror X + Y
    #
    # We are restoring the finer phantom mesh here.
    # ============================================================

    PHANTOM_VARIANT = 0

    VESSEL_DIAMETER = 8.0

    PHANTOM_GRID_SPACING = 1.75

    scene_info = create_vessel(
        rootNode,
        variant=PHANTOM_VARIANT,
        vessel_diameter=VESSEL_DIAMETER,
        grid_spacing=PHANTOM_GRID_SPACING,
    )


    # ============================================================
    # GUIDEWIRE SETTINGS
    #
    # 0.035 inch guidewire
    #
    # Diameter = 0.89 mm
    # Shaft = 165 mm
    # Tip = 15 mm
    # Total = 180 mm
    # ============================================================

    guidewire_density = 6.45e-6

    shaft_length = 172.0
    tip_length = 8.0

    total_wire_length = (
        shaft_length
        + tip_length
    )

    shaft_radius = 0.445

    tip_radius = 0.320


    # ============================================================
    # INITIAL DEPLOYMENT
    #
    # Phantom centerline begins at z = -8 mm.
    # We place the BeamAdapter deployment origin there.
    #
    # 8 mm gets us to the formal vessel entry at z = 0.
    # Another 15 mm places the initial wire tip farther inside.
    # ============================================================

    PHANTOM_ENTRY_EXTENSION = 8.0

    DESIRED_INITIAL_DEPTH = 15.0

    initial_insertion = (
        PHANTOM_ENTRY_EXTENSION
        + DESIRED_INITIAL_DEPTH
    )


    # ============================================================
    # GUIDEWIRE REST SHAPE
    # ============================================================

    rest = rootNode.addChild(
        "GuidewireRestShape"
    )


    # ============================================================
    # SHAFT SECTION
    # ============================================================

    rest.addObject(
        "RodStraightSection",
        name="ShaftSection",

        youngModulus=45000,

        poissonRatio=0.30,

        radius=shaft_radius,

        massDensity=guidewire_density,

        nbBeams=165,

        nbEdgesCollis=165,

        nbEdgesVisu=330,

        length=shaft_length,
    )


    # ============================================================
    # FLEXIBLE TIP SECTION
    # ============================================================

    rest.addObject(
        "RodSpireSection",
        name="TipSection",

        youngModulus=8000,

        poissonRatio=0.45,

        radius=tip_radius,

        massDensity=guidewire_density,

        nbBeams=12,

        nbEdgesCollis=12,

        nbEdgesVisu=48,

        length=tip_length,

        spireDiameter=16.0,

        spireHeight=0.0,
    )


    # ============================================================
    # WIRE REST SHAPE
    # ============================================================

    rest.addObject(
        "WireRestShape",
        name="BeamRestShape",

        template="Rigid3d",

        wireMaterials=(
            "@ShaftSection "
            "@TipSection"
        ),

        printLog=True,
    )


    # ============================================================
    # REST TOPOLOGY
    # ============================================================

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

        rayleighStiffness=0.10,

        rayleighMass=0.03,
    )

    wire.addObject(
        "BTDLinearSolver",
        name="LinearSolver",

        verbose=False,
    )


    # ============================================================
    # GUIDEWIRE TOPOLOGY
    #
    # 165 shaft beams
    # 24 tip beams
    # 189 total beams
    # 190 total nodes
    # ============================================================

    number_of_beams = (
        172
        + 12
    )

    number_of_nodes = (
        number_of_beams
        + 1
    )

    wire.addObject(
        "RegularGridTopology",
        name="MeshLines",

        nx=number_of_nodes,
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
            0.0,
        ],

        drawEdges=False,
    )


    # ============================================================
    # MECHANICAL STATE
    # ============================================================

    wire.addObject(
        "MechanicalObject",
        name="DOFs",

        template="Rigid3d",

        ry=-90,

        showObject=False,

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
    # BEAM FORCE FIELD + MASS
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
    # DEPLOYMENT CONTROLLER
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
            -8.0,

            0.0,
            -0.7071068,
            0.0,
            0.7071068,
        ],

        xtip=[
            initial_insertion
        ],

        rotationInstrument=[
            0.0
        ],

        step=0.5,

        angularStep=0.0349066,

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
    # REST SHAPE SPRING
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
    # GUIDEWIRE COLLISION MODEL
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

        controller="@../DeployController",

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
    # GUIDEWIRE VISUAL
    # ============================================================

    visual = wire.addChild(
        "GuidewireVisual"
    )

    visual.addObject(
        "OglModel",
        name="Visual",

        color=[
            0.25,
            0.27,
            0.30,
            1.0,
        ],

        material=(
            "texture "
            "Ambient 1 0.20 0.20 0.20 1.0 "
            "Diffuse 1 0.55 0.57 0.60 1.0 "
            "Specular 1 0.95 0.95 0.95 1.0 "
            "Emissive 0 0.0 0.0 0.0 0.0 "
            "Shininess 1 80"
        ),
    )

    visual.addObject(
        "QuadSetTopologyContainer",
        name="ContainerGuide",
    )

    visual.addObject(
        "QuadSetTopologyModifier",
        name="Modifier",
    )

    visual.addObject(
        "QuadSetGeometryAlgorithms",
        name="GeomAlgo",

        template="Vec3d",
    )


    # ============================================================
    # ROUND GUIDEWIRE SURFACE
    # ============================================================

    visual.addObject(
        "Edge2QuadTopologicalMapping",
        name="GuidewireTube",

        nbPointsOnEachCircle=12,

        radius=shaft_radius,

        input=(
            "@../../GuidewireRestShape/"
            "meshLinesBeam"
        ),

        output="@ContainerGuide",

        flipNormals=True,

        listening=True,
    )


    # ============================================================
    # VISUAL MAPPING
    # ============================================================

    visual.addObject(
        "AdaptiveBeamMapping",
        name="GuidewireVisualMapping",

        interpolation="@../BeamInterpolation",

        input="@../DOFs",

        output="@Visual",

        useCurvAbs=True,

        printLog=False,
    )


    # ============================================================
    # USER COMMAND CONTROLLER
    #
    # Ctrl + Shift + D = insert
    # Ctrl + Shift + A = retract
    # Ctrl + Shift + E = rotate +
    # Ctrl + Shift + Q = rotate -
    # ============================================================

    command_controller = GuidewireCommandController(

        name="GuidewireCommandController",

        deploy_controller=deploy_controller,

        max_length=total_wire_length,

        translation_step=0.5,

        rotation_step_degrees=2.0,
    )

    rootNode.addObject(
        command_controller
    )


    # ============================================================
    # REFERENCES
    # ============================================================

    rootNode.scene_info = scene_info

    rootNode.guidewire_command_controller = (
        command_controller
    )


    # ============================================================
    # DEBUG OUTPUT
    # ============================================================

    print(
        "STUDY SCENE | "
        f"phantom variant={PHANTOM_VARIANT} | "
        f"vessel ID={VESSEL_DIAMETER:.1f} mm | "
        f"grid spacing={PHANTOM_GRID_SPACING:.2f} mm"
    )

    print(
        "GUIDEWIRE | "
        f"diameter={shaft_radius * 2.0:.3f} mm | "
        f"length={total_wire_length:.1f} mm | "
        f"shaft={shaft_length:.1f} mm | "
        f"tip={tip_length:.1f} mm | "
        f"beams={number_of_beams}"
    )

    print(
        "START POSITION | "
        f"deployment origin z=-8.0 mm | "
        f"xtip={initial_insertion:.1f} mm | "
        f"desired depth past entry={DESIRED_INITIAL_DEPTH:.1f} mm"
    )

    return rootNode