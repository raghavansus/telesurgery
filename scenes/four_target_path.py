import math


# ================================================================
# FOUR-TARGET VASCULAR PATH
#
# This version generates ONE unified vessel surface.
#
# Instead of:
#
#     cylinder + cylinder + cylinder
#
# we define the complete vascular CENTERLINE and calculate the
# boundary of the union of all vessel segments.
#
# This eliminates internal overlapping walls at bifurcations.
# ================================================================


def create_vessel(rootNode):

    # ============================================================
    # VESSEL SETTINGS
    # ============================================================

    vessel = rootNode.addChild("Vessel")

    vessel_radius = 3.0

    # Mesh resolution.
    #
    # Smaller = smoother but slower.
    #
    # 1.0 is a good starting point.
    grid_spacing = 1.0

    vessel_points = []
    vessel_triangles = []
    vessel_edges = []

    # ============================================================
    # CENTERLINE POINTS
    # ============================================================

    entry = [
        0.0,
        0.0,
        0.0
    ]

    first_bifurcation = [
        5.0,
        0.0,
        23.0
    ]

    upper_split = [
        14.0,
        0.0,
        34.0
    ]

    lower_split = [
        -2.0,
        0.0,
        41.0
    ]

    target_1 = [
        10.0,
        0.0,
        44.0
    ]

    target_2 = [
        23.0,
        0.0,
        42.0
    ]

    target_3 = [
        4.0,
        0.0,
        51.0
    ]

    target_4 = [
        -12.0,
        0.0,
        50.0
    ]

    # ============================================================
    # PATH DEFINITIONS
    #
    # These are now CENTERLINES only.
    #
    # They do NOT directly create cylinders.
    # ============================================================

    trunk = [

        # Extend slightly behind the guidewire start.
        # This prevents the vessel surface from closing directly
        # at z = 0.
        [0.0, 0.0, -5.0],

        entry,

        [0.0, 0.0, 7.0],

        [1.0, 0.0, 13.0],

        [3.0, 0.0, 18.0],

        first_bifurcation,
    ]

    upper_route = [

        first_bifurcation,

        [10.0, 0.0, 28.0],

        upper_split,
    ]

    lower_route = [

        first_bifurcation,

        [1.0, 0.0, 29.0],

        [-2.0, 0.0, 35.0],

        lower_split,
    ]

    target_1_route = [

        upper_split,

        [12.0, 0.0, 39.0],

        target_1,

        # Small extension past target
        [8.5, 0.0, 47.5],
    ]

    target_2_route = [

        upper_split,

        [19.0, 0.0, 37.0],

        target_2,

        [26.0, 0.0, 45.0],
    ]

    target_3_route = [

        lower_split,

        [1.0, 0.0, 46.0],

        target_3,

        [6.0, 0.0, 54.5],
    ]

    target_4_route = [

        lower_split,

        [-7.0, 0.0, 45.0],

        target_4,

        [-15.0, 0.0, 53.0],
    ]

    all_paths = [

        trunk,
        upper_route,
        lower_route,

        target_1_route,
        target_2_route,
        target_3_route,
        target_4_route,
    ]

    # ============================================================
    # CONVERT PATHS INTO LINE SEGMENTS
    # ============================================================

    vessel_segments = []

    for path in all_paths:

        for i in range(
            len(path) - 1
        ):

            vessel_segments.append(
                (
                    path[i],
                    path[i + 1]
                )
            )

    # ============================================================
    # DISTANCE FROM POINT TO LINE SEGMENT
    # ============================================================

    def distance_to_segment(
        point,
        start,
        end
    ):

        px, py, pz = point

        ax, ay, az = start
        bx, by, bz = end

        abx = bx - ax
        aby = by - ay
        abz = bz - az

        apx = px - ax
        apy = py - ay
        apz = pz - az

        length_squared = (
            abx * abx
            + aby * aby
            + abz * abz
        )

        if length_squared < 1e-12:

            dx = px - ax
            dy = py - ay
            dz = pz - az

            return math.sqrt(
                dx * dx
                + dy * dy
                + dz * dz
            )

        t = (
            apx * abx
            + apy * aby
            + apz * abz
        ) / length_squared

        t = max(
            0.0,
            min(
                1.0,
                t
            )
        )

        closest_x = ax + t * abx
        closest_y = ay + t * aby
        closest_z = az + t * abz

        dx = px - closest_x
        dy = py - closest_y
        dz = pz - closest_z

        return math.sqrt(
            dx * dx
            + dy * dy
            + dz * dz
        )

    # ============================================================
    # VESSEL IMPLICIT FUNCTION
    #
    # Negative:
    #     inside vessel
    #
    # Positive:
    #     outside vessel
    #
    # IMPORTANT:
    #
    # We calculate the distance to the NEAREST vessel segment.
    #
    # That mathematically performs a UNION of all branches.
    #
    # Therefore intersecting cylinders never exist in the mesh.
    # ============================================================

    def vessel_field(point):

        minimum_distance = float("inf")

        for start, end in vessel_segments:

            distance = distance_to_segment(
                point,
                start,
                end
            )

            if distance < minimum_distance:

                minimum_distance = distance

        return (
            minimum_distance
            - vessel_radius
        )

    # ============================================================
    # CALCULATE GRID BOUNDS
    # ============================================================

    all_centerline_points = []

    for path in all_paths:

        for point in path:

            all_centerline_points.append(
                point
            )

    padding = (
        vessel_radius
        + 2.0
    )

    min_x = min(
        p[0]
        for p in all_centerline_points
    ) - padding

    max_x = max(
        p[0]
        for p in all_centerline_points
    ) + padding

    min_y = -(
        vessel_radius
        + 2.0
    )

    max_y = (
        vessel_radius
        + 2.0
    )

    min_z = min(
        p[2]
        for p in all_centerline_points
    ) - padding

    max_z = max(
        p[2]
        for p in all_centerline_points
    ) + padding

    # ============================================================
    # GRID DIMENSIONS
    # ============================================================

    nx = int(
        math.ceil(
            (max_x - min_x)
            / grid_spacing
        )
    ) + 1

    ny = int(
        math.ceil(
            (max_y - min_y)
            / grid_spacing
        )
    ) + 1

    nz = int(
        math.ceil(
            (max_z - min_z)
            / grid_spacing
        )
    ) + 1

    # ============================================================
    # GRID HELPERS
    # ============================================================

    def grid_position(
        i,
        j,
        k
    ):

        return [

            min_x
            + i * grid_spacing,

            min_y
            + j * grid_spacing,

            min_z
            + k * grid_spacing,
        ]

    def grid_id(
        i,
        j,
        k
    ):

        return (
            i,
            j,
            k
        )

    # ============================================================
    # PRECOMPUTE IMPLICIT VALUES
    # ============================================================

    field_values = {}

    for i in range(nx):

        for j in range(ny):

            for k in range(nz):

                position = grid_position(
                    i,
                    j,
                    k
                )

                field_values[
                    (i, j, k)
                ] = vessel_field(
                    position
                )

    # ============================================================
    # MARCHING TETRAHEDRA
    #
    # Each grid cube is divided into six tetrahedra.
    #
    # This extracts the surface where:
    #
    #     distance = vessel_radius
    #
    # and therefore creates ONE continuous vessel mesh.
    # ============================================================

    tetrahedra = [

        (0, 5, 1, 6),
        (0, 1, 2, 6),
        (0, 2, 3, 6),

        (0, 3, 7, 6),
        (0, 7, 4, 6),
        (0, 4, 5, 6),
    ]

    tetra_edges = [

        (0, 1),
        (1, 2),
        (2, 0),

        (0, 3),
        (1, 3),
        (2, 3),
    ]

    # Standard marching-tetrahedra cases.
    triangle_table = {

        0: [],

        1:
            [(0, 3, 2)],

        2:
            [(0, 1, 4)],

        3:
            [
                (1, 4, 2),
                (2, 4, 3),
            ],

        4:
            [(1, 2, 5)],

        5:
            [
                (0, 3, 5),
                (0, 5, 1),
            ],

        6:
            [
                (0, 2, 5),
                (0, 5, 4),
            ],

        7:
            [(5, 4, 3)],

        8:
            [(3, 4, 5)],

        9:
            [
                (4, 5, 0),
                (5, 2, 0),
            ],

        10:
            [
                (1, 5, 0),
                (5, 3, 0),
            ],

        11:
            [(5, 2, 1)],

        12:
            [
                (3, 4, 2),
                (2, 4, 1),
            ],

        13:
            [(4, 1, 0)],

        14:
            [(2, 3, 0)],

        15: [],
    }

    # ============================================================
    # SURFACE VERTEX CACHE
    #
    # Adjacent tetrahedra share vertices instead of creating
    # duplicate surfaces.
    # ============================================================

    edge_vertex_cache = {}

    def interpolate_surface_vertex(
        id_a,
        id_b,
        pos_a,
        pos_b,
        value_a,
        value_b
    ):

        key = tuple(
            sorted(
                (
                    id_a,
                    id_b
                )
            )
        )

        if key in edge_vertex_cache:

            return edge_vertex_cache[
                key
            ]

        denominator = (
            value_a
            - value_b
        )

        if abs(
            denominator
        ) < 1e-12:

            t = 0.5

        else:

            t = (
                value_a
                / denominator
            )

        t = max(
            0.0,
            min(
                1.0,
                t
            )
        )

        point = [

            pos_a[0]
            + t
            * (
                pos_b[0]
                - pos_a[0]
            ),

            pos_a[1]
            + t
            * (
                pos_b[1]
                - pos_a[1]
            ),

            pos_a[2]
            + t
            * (
                pos_b[2]
                - pos_a[2]
            ),
        ]

        vertex_index = len(
            vessel_points
        )

        vessel_points.append(
            point
        )

        edge_vertex_cache[
            key
        ] = vertex_index

        return vertex_index

    # ============================================================
    # PROCESS TETRAHEDRON
    # ============================================================

    def process_tetrahedron(
        vertex_ids,
        positions,
        values
    ):

        case = 0

        for vertex_index in range(4):

            if values[
                vertex_index
            ] < 0.0:

                case |= (
                    1
                    << vertex_index
                )

        triangles = triangle_table[
            case
        ]

        if not triangles:

            return

        edge_vertices = {}

        for triangle in triangles:

            triangle_indices = []

            for edge_number in triangle:

                if edge_number not in edge_vertices:

                    local_a, local_b = (
                        tetra_edges[
                            edge_number
                        ]
                    )

                    edge_vertices[
                        edge_number
                    ] = (
                        interpolate_surface_vertex(

                            vertex_ids[
                                local_a
                            ],

                            vertex_ids[
                                local_b
                            ],

                            positions[
                                local_a
                            ],

                            positions[
                                local_b
                            ],

                            values[
                                local_a
                            ],

                            values[
                                local_b
                            ],
                        )
                    )

                triangle_indices.append(
                    edge_vertices[
                        edge_number
                    ]
                )

            vessel_triangles.append(
                triangle_indices
            )

    # ============================================================
    # PROCESS GRID CUBES
    # ============================================================

    for i in range(
        nx - 1
    ):

        for j in range(
            ny - 1
        ):

            for k in range(
                nz - 1
            ):

                cube_grid_ids = [

                    grid_id(
                        i,
                        j,
                        k
                    ),

                    grid_id(
                        i + 1,
                        j,
                        k
                    ),

                    grid_id(
                        i + 1,
                        j + 1,
                        k
                    ),

                    grid_id(
                        i,
                        j + 1,
                        k
                    ),

                    grid_id(
                        i,
                        j,
                        k + 1
                    ),

                    grid_id(
                        i + 1,
                        j,
                        k + 1
                    ),

                    grid_id(
                        i + 1,
                        j + 1,
                        k + 1
                    ),

                    grid_id(
                        i,
                        j + 1,
                        k + 1
                    ),
                ]

                cube_positions = [

                    grid_position(
                        *grid_point
                    )

                    for grid_point
                    in cube_grid_ids
                ]

                cube_values = [

                    field_values[
                        grid_point
                    ]

                    for grid_point
                    in cube_grid_ids
                ]

                for tetra in tetrahedra:

                    tetra_ids = [

                        cube_grid_ids[
                            index
                        ]

                        for index
                        in tetra
                    ]

                    tetra_positions = [

                        cube_positions[
                            index
                        ]

                        for index
                        in tetra
                    ]

                    tetra_values = [

                        cube_values[
                            index
                        ]

                        for index
                        in tetra
                    ]

                    process_tetrahedron(

                        tetra_ids,

                        tetra_positions,

                        tetra_values,
                    )

    # ============================================================
    # GENERATE UNIQUE VISUAL EDGES
    # ============================================================

    unique_edges = set()

    for triangle in vessel_triangles:

        a, b, c = triangle

        triangle_edges = [

            (a, b),
            (b, c),
            (c, a),
        ]

        for edge in triangle_edges:

            unique_edges.add(
                tuple(
                    sorted(
                        edge
                    )
                )
            )

    vessel_edges = [

        list(edge)

        for edge in unique_edges
    ]

    # ============================================================
    # VESSEL MECHANICAL STATE
    # ============================================================

    vessel.addObject(
        "MechanicalObject",

        name="VesselDOFs",

        template="Vec3d",

        position=vessel_points,

        showObject=False,
    )

    # ============================================================
    # VESSEL TOPOLOGY
    # ============================================================

    vessel.addObject(
        "MeshTopology",

        name="VesselTopology",

        position=vessel_points,

        triangles=vessel_triangles,
    )

    # ============================================================
    # COLLISION
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
    # TRANSPARENT VISUAL
    # ============================================================

    vessel.addObject(
        "OglModel",

        name="VesselVisual",

        position=vessel_points,

        triangles=vessel_triangles,

        edges=vessel_edges,

        color=[
            0.3,
            0.6,
            0.9,
            0.20
        ],

        lineWidth=1.0,
    )

    # ============================================================
    # TARGETS
    # ============================================================

    targets = {

        "Target1":
            target_1,

        "Target2":
            target_2,

        "Target3":
            target_3,

        "Target4":
            target_4,
    }

    # ============================================================
    # TARGET MARKERS
    # ============================================================

    for name, position in targets.items():

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
    # DEBUG INFORMATION
    # ============================================================

    print(
        "Unified vessel generated | "
        f"vertices={len(vessel_points)} | "
        f"triangles={len(vessel_triangles)}"
    )

    # ============================================================
    # RETURN SCENE DATA
    # ============================================================

    return {

        "vessel_node":
            vessel,

        "targets":
            targets,

        "entry_position":
            entry,

        "first_bifurcation":
            first_bifurcation,

        "upper_split":
            upper_split,

        "lower_split":
            lower_split,
    }