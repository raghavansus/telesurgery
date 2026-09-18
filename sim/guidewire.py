# sim/guidewire.py
#
# Shared BeamAdapter guidewire construction, extracted from the
# original mainRun.py so keyboard_control.py, motion_scale_control.py
# and any future entry point build the exact same physical guidewire.
#
# 0.035" guidewire: diameter 0.89 mm, 172 mm shaft + 8 mm flexible
# spire tip = 180 mm total.

import Sofa

GUIDEWIRE_DENSITY = 6.45e-6

SHAFT_LENGTH = 172.0
TIP_LENGTH = 8.0
TOTAL_WIRE_LENGTH = SHAFT_LENGTH + TIP_LENGTH

SHAFT_RADIUS = 0.445
TIP_RADIUS = 0.320

NUMBER_OF_BEAMS = 172 + 12
NUMBER_OF_NODES = NUMBER_OF_BEAMS + 1

# Phantom centerline begins at z = -8 mm (see sim/phantoms/networks.py
# START). Deployment origin sits there; the wire is pushed an
# additional DESIRED_INITIAL_DEPTH past the formal vessel entry so it
# starts already inside the lumen.
PHANTOM_ENTRY_EXTENSION = 8.0
DESIRED_INITIAL_DEPTH = 15.0
INITIAL_INSERTION = PHANTOM_ENTRY_EXTENSION + DESIRED_INITIAL_DEPTH


def add_guidewire(rootNode, deployment_origin_z=-8.0):
    """
    Build the full BeamAdapter guidewire (rest shape, active wire,
    solvers, collision model, visual model, deployment controller) on
    rootNode and return (deploy_controller, total_wire_length).
    """

    # ============================================================
    # GUIDEWIRE REST SHAPE
    # ============================================================

    rest = rootNode.addChild("GuidewireRestShape")

    rest.addObject(
        "RodStraightSection",
        name="ShaftSection",
        youngModulus=45000,
        poissonRatio=0.30,
        radius=SHAFT_RADIUS,
        massDensity=GUIDEWIRE_DENSITY,
        nbBeams=165,
        nbEdgesCollis=165,
        nbEdgesVisu=330,
        length=SHAFT_LENGTH,
    )

    rest.addObject(
        "RodSpireSection",
        name="TipSection",
        youngModulus=8000,
        poissonRatio=0.45,
        radius=TIP_RADIUS,
        massDensity=GUIDEWIRE_DENSITY,
        nbBeams=12,
        nbEdgesCollis=12,
        nbEdgesVisu=48,
        length=TIP_LENGTH,
        spireDiameter=16.0,
        spireHeight=0.0,
    )

    rest.addObject(
        "WireRestShape",
        name="BeamRestShape",
        template="Rigid3d",
        wireMaterials="@ShaftSection @TipSection",
        printLog=True,
    )

    rest.addObject("EdgeSetTopologyContainer", name="meshLinesBeam")
    rest.addObject("EdgeSetTopologyModifier", name="Modifier")
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

    wire = rootNode.addChild("Guidewire")

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

    wire.addObject(
        "RegularGridTopology",
        name="MeshLines",
        nx=NUMBER_OF_NODES,
        ny=1,
        nz=1,
        xmin=0.0, xmax=0.0,
        ymin=0.0, ymax=0.0,
        zmin=0.0, zmax=0.0,
        p0=[0.0, 0.0, 0.0],
        drawEdges=False,
    )

    wire.addObject(
        "MechanicalObject",
        name="DOFs",
        template="Rigid3d",
        ry=-90,
        showObject=False,
        showObjectScale=0.15,
    )

    wire.addObject(
        "WireBeamInterpolation",
        name="BeamInterpolation",
        WireRestShape="@../GuidewireRestShape/BeamRestShape",
        printLog=True,
    )

    wire.addObject(
        "AdaptiveBeamForceFieldAndMass",
        name="BeamForceField",
        interpolation="@BeamInterpolation",
    )

    wire.addObject(
        "FixedProjectiveConstraint",
        name="FixedConstraint",
        indices=[0],
    )

    deploy_controller = wire.addObject(
        "InterventionalRadiologyController",
        name="DeployController",
        template="Rigid3d",
        instruments="BeamInterpolation",
        topology="@MeshLines",
        fixedConstraint="@FixedConstraint",
        startingPos=[
            0.0, 0.0, deployment_origin_z,
            0.0, -0.7071068, 0.0, 0.7071068,
        ],
        xtip=[INITIAL_INSERTION],
        rotationInstrument=[0.0],
        step=0.5,
        angularStep=0.0349066,
        speed=0.0,
        controlledInstrument=0,
        listening=True,
        printLog=True,
    )

    wire.addObject(
        "LinearSolverConstraintCorrection",
        name="ConstraintCorrection",
        wire_optimization=True,
        printLog=False,
    )

    wire.addObject(
        "RestShapeSpringsForceField",
        name="RestShapeConstraint",
        points="@DeployController.indexFirstNode",
        stiffness=1e8,
        angularStiffness=1e8,
    )

    # ============================================================
    # GUIDEWIRE COLLISION MODEL
    # ============================================================

    collision = wire.addChild("CollisionModel")

    collision.addObject("EdgeSetTopologyContainer", name="CollisionEdges")
    collision.addObject("EdgeSetTopologyModifier", name="CollisionModifier")
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
    collision.addObject("LineCollisionModel", name="GuidewireLines")
    collision.addObject("PointCollisionModel", name="GuidewirePoints")

    # ============================================================
    # GUIDEWIRE VISUAL
    # ============================================================

    visual = wire.addChild("GuidewireVisual")

    visual.addObject(
        "OglModel",
        name="Visual",
        color=[0.25, 0.27, 0.30, 1.0],
        material=(
            "texture "
            "Ambient 1 0.20 0.20 0.20 1.0 "
            "Diffuse 1 0.55 0.57 0.60 1.0 "
            "Specular 1 0.95 0.95 0.95 1.0 "
            "Emissive 0 0.0 0.0 0.0 0.0 "
            "Shininess 1 80"
        ),
    )

    visual.addObject("QuadSetTopologyContainer", name="ContainerGuide")
    visual.addObject("QuadSetTopologyModifier", name="Modifier")
    visual.addObject(
        "QuadSetGeometryAlgorithms",
        name="GeomAlgo",
        template="Vec3d",
    )

    visual.addObject(
        "Edge2QuadTopologicalMapping",
        name="GuidewireTube",
        nbPointsOnEachCircle=12,
        radius=SHAFT_RADIUS,
        input="@../../GuidewireRestShape/meshLinesBeam",
        output="@ContainerGuide",
        flipNormals=True,
        listening=True,
    )

    visual.addObject(
        "AdaptiveBeamMapping",
        name="GuidewireVisualMapping",
        interpolation="@../BeamInterpolation",
        input="@../DOFs",
        output="@Visual",
        useCurvAbs=True,
        printLog=False,
    )

    print(
        "GUIDEWIRE | "
        f"diameter={SHAFT_RADIUS * 2.0:.3f} mm | "
        f"length={TOTAL_WIRE_LENGTH:.1f} mm | "
        f"shaft={SHAFT_LENGTH:.1f} mm | "
        f"tip={TIP_LENGTH:.1f} mm | "
        f"beams={NUMBER_OF_BEAMS}"
    )

    return deploy_controller, TOTAL_WIRE_LENGTH
