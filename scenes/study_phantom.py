# scenes/study_phantom.py

import math


# ================================================================
# BASIC VECTOR MATH
# ================================================================

def add(a, b):
    return (
        a[0] + b[0],
        a[1] + b[1],
        a[2] + b[2],
    )


def subtract(a, b):
    return (
        a[0] - b[0],
        a[1] - b[1],
        a[2] - b[2],
    )


def multiply(v, scalar):
    return (
        v[0] * scalar,
        v[1] * scalar,
        v[2] * scalar,
    )


def magnitude(v):
    return math.sqrt(
        v[0] * v[0]
        + v[1] * v[1]
        + v[2] * v[2]
    )


def normalize(v):
    length = magnitude(v)

    if length < 1e-12:
        return (0.0, 0.0, 1.0)

    return (
        v[0] / length,
        v[1] / length,
        v[2] / length,
    )


def lerp(a, b, t):
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


# ================================================================
# MIRROR TRANSFORM
#
# Four phantom variants:
#
#   0 = original
#   1 = X mirror
#   2 = Y mirror
#   3 = X + Y mirror
#
# All distances, branch angles and path lengths remain identical.
# ================================================================

def transform_point(point, variant):

    x, y, z = point

    if variant == 0:
        sx = 1.0
        sy = 1.0

    elif variant == 1:
        sx = -1.0
        sy = 1.0

    elif variant == 2:
        sx = 1.0
        sy = -1.0

    elif variant == 3:
        sx = -1.0
        sy = -1.0

    else:
        raise ValueError(
            "variant must be 0, 1, 2, or 3"
        )

    return (
        sx * x,
        sy * y,
        z,
    )


# ================================================================
# RESAMPLE POLYLINE
#
# More centerline points produce smoother implicit vessels.
# ================================================================

def sample_polyline(points, spacing=2.0):

    sampled = []

    for segment_index in range(len(points) - 1):

        a = points[segment_index]
        b = points[segment_index + 1]

        delta = subtract(b, a)
        length = magnitude(delta)

        steps = max(
            1,
            int(math.ceil(length / spacing))
        )

        for i in range(steps):

            t = i / steps
            point = lerp(a, b, t)

            if (
                not sampled
                or magnitude(
                    subtract(point, sampled[-1])
                ) > 1e-8
            ):
                sampled.append(point)

    sampled.append(points[-1])

    return sampled


# ================================================================
# DISTANCE FROM POINT TO SEGMENT
# ================================================================

def point_segment_distance(point, a, b):

    ab = subtract(b, a)
    ap = subtract(point, a)

    ab_squared = (
        ab[0] * ab[0]
        + ab[1] * ab[1]
        + ab[2] * ab[2]
    )

    if ab_squared < 1e-12:
        return magnitude(ap)

    t = (
        ap[0] * ab[0]
        + ap[1] * ab[1]
        + ap[2] * ab[2]
    ) / ab_squared

    t = max(
        0.0,
        min(1.0, t)
    )

    closest = (
        a[0] + t * ab[0],
        a[1] + t * ab[1],
        a[2] + t * ab[2],
    )

    return magnitude(
        subtract(point, closest)
    )


# ================================================================
# CONVERT CENTERLINES INTO SEGMENTS
# ================================================================

def build_segments(paths):

    segments = []

    for path in paths:

        for i in range(len(path) - 1):

            a = path[i]
            b = path[i + 1]

            if magnitude(subtract(b, a)) > 1e-9:
                segments.append((a, b))

    return segments


# ================================================================
# IMPLICIT VESSEL FIELD
#
# Negative = inside vessel
# Positive = outside vessel
#
# The minimum distance to ANY centerline segment creates the union
# of all vessel branches automatically.
# ================================================================

def vessel_field(point, segments, radius):

    minimum_distance = float("inf")

    for a, b in segments:

        distance = point_segment_distance(
            point,
            a,
            b
        )

        if distance < minimum_distance:
            minimum_distance = distance

    return minimum_distance - radius


# ================================================================
# MARCHING TETRAHEDRA
#
# Pure Python surface extraction.
#
# Each voxel is split into six tetrahedra.
# ================================================================

CUBE_CORNERS = (
    (0, 0, 0),
    (1, 0, 0),
    (1, 1, 0),
    (0, 1, 0),
    (0, 0, 1),
    (1, 0, 1),
    (1, 1, 1),
    (0, 1, 1),
)


CUBE_TETRAHEDRA = (
    (0, 5, 1, 6),
    (0, 1, 2, 6),
    (0, 2, 3, 6),
    (0, 3, 7, 6),
    (0, 7, 4, 6),
    (0, 4, 5, 6),
)


TET_EDGES = (
    (0, 1),
    (0, 2),
    (0, 3),
    (1, 2),
    (1, 3),
    (2, 3),
)


def interpolate_isosurface(p1, p2, value1, value2):

    denominator = value1 - value2

    if abs(denominator) < 1e-12:
        t = 0.5
    else:
        t = value1 / denominator

    t = max(
        0.0,
        min(1.0, t)
    )

    return lerp(
        p1,
        p2,
        t
    )


def marching_tetrahedra(
    segments,
    radius,
    grid_spacing=1.75,
):

    # ------------------------------------------------------------
    # DETERMINE BOUNDS
    # ------------------------------------------------------------

    all_points = []

    for a, b in segments:
        all_points.append(a)
        all_points.append(b)

    min_x = min(p[0] for p in all_points)
    max_x = max(p[0] for p in all_points)

    min_y = min(p[1] for p in all_points)
    max_y = max(p[1] for p in all_points)

    min_z = min(p[2] for p in all_points)
    max_z = max(p[2] for p in all_points)

    margin = radius + 2.0 * grid_spacing

    min_x -= margin
    max_x += margin

    min_y -= margin
    max_y += margin

    min_z -= margin
    max_z += margin

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

    print(
        "Building phantom implicit surface | "
        f"grid={nx} x {ny} x {nz}"
    )

    # ------------------------------------------------------------
    # FIELD CACHE
    # ------------------------------------------------------------

    field_cache = {}

    def grid_position(i, j, k):

        return (
            min_x + i * grid_spacing,
            min_y + j * grid_spacing,
            min_z + k * grid_spacing,
        )

    def field_value(i, j, k):

        key = (
            i,
            j,
            k
        )

        if key not in field_cache:

            position = grid_position(
                i,
                j,
                k
            )

            field_cache[key] = vessel_field(
                position,
                segments,
                radius
            )

        return field_cache[key]

    vertices = []
    triangles = []

    vertex_lookup = {}

    # ------------------------------------------------------------
    # VERTEX DEDUPLICATION
    # ------------------------------------------------------------

    def get_vertex_index(point):

        key = (
            round(point[0], 5),
            round(point[1], 5),
            round(point[2], 5),
        )

        if key in vertex_lookup:
            return vertex_lookup[key]

        index = len(vertices)

        vertices.append(
            [
                point[0],
                point[1],
                point[2],
            ]
        )

        vertex_lookup[key] = index

        return index

    # ------------------------------------------------------------
    # PROCESS TETRAHEDRON
    # ------------------------------------------------------------

    def process_tetrahedron(
        tetra_points,
        tetra_values
    ):

        intersections = []

        for edge_a, edge_b in TET_EDGES:

            value_a = tetra_values[edge_a]
            value_b = tetra_values[edge_b]

            inside_a = value_a <= 0.0
            inside_b = value_b <= 0.0

            if inside_a != inside_b:

                intersection = interpolate_isosurface(
                    tetra_points[edge_a],
                    tetra_points[edge_b],
                    value_a,
                    value_b
                )

                intersections.append(
                    intersection
                )

        # One triangle
        if len(intersections) == 3:

            indices = [
                get_vertex_index(p)
                for p in intersections
            ]

            if len(set(indices)) == 3:
                triangles.append(indices)

        # Quad split into two triangles
        elif len(intersections) == 4:

            indices = [
                get_vertex_index(p)
                for p in intersections
            ]

            if len(set(indices)) == 4:

                triangles.append(
                    [
                        indices[0],
                        indices[1],
                        indices[2]
                    ]
                )

                triangles.append(
                    [
                        indices[0],
                        indices[2],
                        indices[3]
                    ]
                )

    # ------------------------------------------------------------
    # LOOP OVER VOXELS
    # ------------------------------------------------------------

    for i in range(nx - 1):

        for j in range(ny - 1):

            for k in range(nz - 1):

                cube_points = []
                cube_values = []

                for dx, dy, dz in CUBE_CORNERS:

                    gi = i + dx
                    gj = j + dy
                    gk = k + dz

                    cube_points.append(
                        grid_position(
                            gi,
                            gj,
                            gk
                        )
                    )

                    cube_values.append(
                        field_value(
                            gi,
                            gj,
                            gk
                        )
                    )

                # Skip cubes entirely inside/outside
                minimum = min(cube_values)
                maximum = max(cube_values)

                if minimum > 0.0:
                    continue

                if maximum < 0.0:
                    continue

                for tetra in CUBE_TETRAHEDRA:

                    tetra_points = [
                        cube_points[index]
                        for index in tetra
                    ]

                    tetra_values = [
                        cube_values[index]
                        for index in tetra
                    ]

                    process_tetrahedron(
                        tetra_points,
                        tetra_values
                    )

    print(
        "Phantom mesh generated | "
        f"vertices={len(vertices)} | "
        f"triangles={len(triangles)}"
    )

    return vertices, triangles


# ================================================================
# UV SPHERE FOR TARGET MARKERS
# ================================================================

def create_sphere_mesh(
    center,
    radius=2.0,
    latitude_segments=10,
    longitude_segments=16,
):

    vertices = []
    triangles = []

    cx, cy, cz = center

    for latitude in range(
        latitude_segments + 1
    ):

        theta = (
            math.pi
            * latitude
            / latitude_segments
        )

        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)

        for longitude in range(
            longitude_segments
        ):

            phi = (
                2.0
                * math.pi
                * longitude
                / longitude_segments
            )

            x = (
                cx
                + radius
                * sin_theta
                * math.cos(phi)
            )

            y = (
                cy
                + radius
                * sin_theta
                * math.sin(phi)
            )

            z = (
                cz
                + radius
                * cos_theta
            )

            vertices.append(
                [x, y, z]
            )

    for latitude in range(
        latitude_segments
    ):

        for longitude in range(
            longitude_segments
        ):

            next_longitude = (
                longitude + 1
            ) % longitude_segments

            a = (
                latitude
                * longitude_segments
                + longitude
            )

            b = (
                latitude
                * longitude_segments
                + next_longitude
            )

            c = (
                (latitude + 1)
                * longitude_segments
                + longitude
            )

            d = (
                (latitude + 1)
                * longitude_segments
                + next_longitude
            )

            triangles.append(
                [a, c, d]
            )

            triangles.append(
                [a, d, b]
            )

    return vertices, triangles


# ================================================================
# TARGET POSITION
#
# Place target before closed end of branch.
# ================================================================

def target_before_end(
    previous_point,
    endpoint,
    distance_before_end=8.0
):

    direction = normalize(
        subtract(
            endpoint,
            previous_point
        )
    )

    return subtract(
        endpoint,
        multiply(
            direction,
            distance_before_end
        )
    )


# ================================================================
# PHANTOM NETWORK DEFINITION
# ================================================================

def create_network(variant=0):

    # ------------------------------------------------------------
    # COMMON ENTRY
    # ------------------------------------------------------------

    start = (
        0.0,
        0.0,
        -8.0
    )

    entry = (
        0.0,
        0.0,
        0.0
    )

    trunk_mid = (
        0.0,
        0.0,
        18.0
    )

    first_bifurcation = (
        0.0,
        0.0,
        36.0
    )

    # ------------------------------------------------------------
    # LEFT SIDE
    #
    # First bifurcation -> secondary bifurcation
    # ------------------------------------------------------------

    left_mid = (
        -7.0,
        2.0,
        48.0
    )

    left_split = (
        -16.0,
        4.0,
        61.0
    )

    left_upper_mid = (
        -25.0,
        8.0,
        78.0
    )

    left_upper_split = (
        -30.0,
        9.0,
        91.0
    )

    left_lower_mid = (
        -11.0,
        11.0,
        79.0
    )

    left_lower_split = (
        -9.0,
        12.0,
        93.0
    )

    # ------------------------------------------------------------
    # LEFT TERMINAL ROUTES
    # ------------------------------------------------------------

    g1_mid = (
        -38.0,
        12.0,
        108.0
    )

    g1_end = (
        -43.0,
        13.0,
        132.0
    )

    d1_mid = (
        -25.0,
        20.0,
        108.0
    )

    d1_end = (
        -20.0,
        23.0,
        130.0
    )

    g2_mid = (
        -17.0,
        17.0,
        110.0
    )

    g2_end = (
        -22.0,
        20.0,
        135.0
    )

    d2_mid = (
        0.0,
        9.0,
        109.0
    )

    d2_end = (
        6.0,
        5.0,
        130.0
    )

    # ------------------------------------------------------------
    # RIGHT SIDE
    #
    # First bifurcation -> secondary trifurcation
    # ------------------------------------------------------------

    right_mid = (
        7.0,
        -2.0,
        48.0
    )

    right_split = (
        16.0,
        -4.0,
        61.0
    )

    right_upper = (
        29.0,
        -8.0,
        83.0
    )

    right_center = (
        18.0,
        1.0,
        86.0
    )

    right_lower = (
        10.0,
        -15.0,
        83.0
    )

    # ------------------------------------------------------------
    # RIGHT UPPER TERMINALS
    # ------------------------------------------------------------

    g3_mid = (
        39.0,
        -10.0,
        106.0
    )

    g3_end = (
        47.0,
        -12.0,
        132.0
    )

    d3_mid = (
        31.0,
        -19.0,
        107.0
    )

    d3_end = (
        34.0,
        -26.0,
        130.0
    )

    # ------------------------------------------------------------
    # RIGHT CENTER TERMINALS
    # ------------------------------------------------------------

    g4_mid = (
        19.0,
        8.0,
        110.0
    )

    g4_end = (
        24.0,
        12.0,
        137.0
    )

    d4_mid = (
        31.0,
        4.0,
        108.0
    )

    d4_end = (
        39.0,
        7.0,
        130.0
    )

    # ------------------------------------------------------------
    # RIGHT LOWER TERMINALS
    # ------------------------------------------------------------

    g5_mid = (
        8.0,
        -23.0,
        108.0
    )

    g5_end = (
        5.0,
        -30.0,
        134.0
    )

    d5_mid = (
        -3.0,
        -21.0,
        106.0
    )

    d5_end = (
        -9.0,
        -24.0,
        128.0
    )

    # ============================================================
    # PATHS
    #
    # Shared segments are intentionally listed independently.
    # The implicit union combines everything into one vessel.
    # ============================================================

    paths = [

        # Common trunk
        [
            start,
            entry,
            trunk_mid,
            first_bifurcation,
        ],

        # Left common
        [
            first_bifurcation,
            left_mid,
            left_split,
        ],

        # Left upper
        [
            left_split,
            left_upper_mid,
            left_upper_split,
        ],

        # Goal 1
        [
            left_upper_split,
            g1_mid,
            g1_end,
        ],

        # Distractor 1
        [
            left_upper_split,
            d1_mid,
            d1_end,
        ],

        # Left lower
        [
            left_split,
            left_lower_mid,
            left_lower_split,
        ],

        # Goal 2
        [
            left_lower_split,
            g2_mid,
            g2_end,
        ],

        # Distractor 2
        [
            left_lower_split,
            d2_mid,
            d2_end,
        ],

        # Right common
        [
            first_bifurcation,
            right_mid,
            right_split,
        ],

        # Right upper
        [
            right_split,
            right_upper,
        ],

        # Goal 3
        [
            right_upper,
            g3_mid,
            g3_end,
        ],

        # Distractor 3
        [
            right_upper,
            d3_mid,
            d3_end,
        ],

        # Right center
        [
            right_split,
            right_center,
        ],

        # Goal 4
        [
            right_center,
            g4_mid,
            g4_end,
        ],

        # Distractor 4
        [
            right_center,
            d4_mid,
            d4_end,
        ],

        # Right lower
        [
            right_split,
            right_lower,
        ],

        # Goal 5
        [
            right_lower,
            g5_mid,
            g5_end,
        ],

        # Distractor 5
        [
            right_lower,
            d5_mid,
            d5_end,
        ],
    ]

    # ============================================================
    # TARGETS
    #
    # Targets are 8 mm before the branch endpoint so the target is
    # inside a continuous navigable lumen, not sitting against the
    # closed terminal cap.
    # ============================================================

    targets = {

        "G1": target_before_end(
            g1_mid,
            g1_end,
            8.0
        ),

        "G2": target_before_end(
            g2_mid,
            g2_end,
            8.0
        ),

        "G3": target_before_end(
            g3_mid,
            g3_end,
            8.0
        ),

        "G4": target_before_end(
            g4_mid,
            g4_end,
            8.0
        ),

        "G5": target_before_end(
            g5_mid,
            g5_end,
            8.0
        ),
    }

    # ============================================================
    # APPLY MIRROR
    # ============================================================

    transformed_paths = []

    for path in paths:

        transformed_path = [
            transform_point(
                point,
                variant
            )
            for point in path
        ]

        transformed_paths.append(
            transformed_path
        )

    transformed_targets = {

        name: transform_point(
            position,
            variant
        )

        for name, position
        in targets.items()
    }

    return {

        "paths": transformed_paths,

        "targets": transformed_targets,

        "entry_position": transform_point(
            entry,
            variant
        ),

        "first_bifurcation": transform_point(
            first_bifurcation,
            variant
        ),

        "left_split": transform_point(
            left_split,
            variant
        ),

        "right_split": transform_point(
            right_split,
            variant
        ),
    }


# ================================================================
# CREATE SOFA PHANTOM
# ================================================================

def create_vessel(
    rootNode,
    variant=0,
    vessel_diameter=5.0,
    grid_spacing=1.75,
):

    # ============================================================
    # BASIC PARAMETERS
    # ============================================================

    vessel_radius = (
        vessel_diameter / 2.0
    )

    network = create_network(
        variant=variant
    )

    # ============================================================
    # RESAMPLE PATHS
    # ============================================================

    sampled_paths = []

    for path in network["paths"]:

        sampled_paths.append(
            sample_polyline(
                path,
                spacing=2.0
            )
        )

    # ============================================================
    # CENTERLINE SEGMENTS
    # ============================================================

    segments = build_segments(
        sampled_paths
    )

    # ============================================================
    # GENERATE UNIFIED SURFACE
    # ============================================================

    vertices, triangles = marching_tetrahedra(
        segments=segments,
        radius=vessel_radius,
        grid_spacing=grid_spacing,
    )

    # ============================================================
    # PHYSICAL / COLLISION VESSEL
    # ============================================================

    vessel = rootNode.addChild(
        "Vessel"
    )

    vessel.addObject(
        "MeshTopology",
        name="VesselTopology",

        position=vertices,

        triangles=triangles,
    )

    vessel.addObject(
        "MechanicalObject",
        name="VesselDOFs",

        template="Vec3d",

        position=vertices,

        showObject=False,
    )

    # ============================================================
    # STATIC COLLISION
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
        name="VesselPoints",

        moving=False,

        simulated=False,
    )

    # ============================================================
    # VISUAL
    #
    # Separate child prevents the previous BaseState warning.
    # ============================================================

    visual = vessel.addChild(
        "Visual"
    )

    visual.addObject(
        "OglModel",
        name="VesselVisual",

        position=vertices,

        triangles=triangles,

        color=[
            0.30,
            0.60,
            0.90,
            0.20
        ],

        material=(
            "texture "
            "Ambient 1 0.20 0.30 0.40 0.20 "
            "Diffuse 1 0.30 0.60 0.90 0.20 "
            "Specular 1 0.25 0.25 0.25 0.20 "
            "Emissive 0 0.0 0.0 0.0 0.0 "
            "Shininess 1 20"
        ),
    )

    # ============================================================
    # FIVE TARGET MARKERS
    # ============================================================

    target_nodes = {}

    target_colors = {

        "G1": [
            0.90,
            0.20,
            0.20,
            1.0
        ],

        "G2": [
            0.95,
            0.55,
            0.10,
            1.0
        ],

        "G3": [
            0.20,
            0.75,
            0.25,
            1.0
        ],

        "G4": [
            0.55,
            0.25,
            0.90,
            1.0
        ],

        "G5": [
            0.95,
            0.20,
            0.65,
            1.0
        ],
    }

    for target_name, target_position in network[
        "targets"
    ].items():

        target_vertices, target_triangles = (
            create_sphere_mesh(
                target_position,
                radius=1.6,
            )
        )

        target_node = rootNode.addChild(
            f"Target_{target_name}"
        )

        target_node.addObject(
            "OglModel",
            name=f"{target_name}_Visual",

            position=target_vertices,

            triangles=target_triangles,

            color=target_colors[
                target_name
            ],
        )

        target_nodes[
            target_name
        ] = target_node

    # ============================================================
    # REPORT
    # ============================================================

    print(
        "STUDY PHANTOM GENERATED | "
        f"variant={variant} | "
        f"vessel ID={vessel_diameter:.2f} mm | "
        f"radius={vessel_radius:.2f} mm | "
        f"targets={len(network['targets'])} | "
        f"terminal routes=10"
    )

    for name, position in network[
        "targets"
    ].items():

        print(
            f"  {name}: "
            f"({position[0]:.1f}, "
            f"{position[1]:.1f}, "
            f"{position[2]:.1f})"
        )

    # ============================================================
    # RETURN USEFUL SCENE INFORMATION
    # ============================================================

    return {

        "vessel_node": vessel,

        "targets": network[
            "targets"
        ],

        "target_nodes": target_nodes,

        "entry_position": network[
            "entry_position"
        ],

        "first_bifurcation": network[
            "first_bifurcation"
        ],

        "left_split": network[
            "left_split"
        ],

        "right_split": network[
            "right_split"
        ],

        "variant": variant,

        "vessel_diameter": vessel_diameter,

        "vessel_radius": vessel_radius,

        "terminal_route_count": 10,

        "scored_target_count": 5,
    }