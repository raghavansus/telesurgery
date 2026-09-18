# sim/phantoms/engine.py
#
# Shared procedural vessel-geometry engine, extracted from the original
# scenes/study_phantom.py. Pure Python / math — no SOFA dependency, so it
# can be exercised and sanity-checked without a SOFA install.
#
# A phantom is defined as a *network*: a list of centerline paths, each
# path a list of (point_xyz, radius) waypoints. Radius is carried per
# waypoint (not a single global scalar) so a phantom can taper its vessel
# diameter along a branch; phantoms that don't need tapering just repeat
# the same radius for every waypoint (see `uniform_path`).

import math


# ================================================================
# BASIC VECTOR MATH
# ================================================================

def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def subtract(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def multiply(v, scalar):
    return (v[0] * scalar, v[1] * scalar, v[2] * scalar)


def magnitude(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def normalize(v):
    length = magnitude(v)

    if length < 1e-12:
        return (0.0, 0.0, 1.0)

    return (v[0] / length, v[1] / length, v[2] / length)


def lerp(a, b, t):
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


# ================================================================
# PATH HELPERS
# ================================================================

def uniform_path(points, radius):
    """Attach the same radius to every waypoint of a plain point list."""
    return [(p, radius) for p in points]


def sample_polyline(path, spacing=2.0):
    """
    Resample a (point, radius) path to a denser set of (point, radius)
    waypoints, linearly interpolating radius alongside position. More
    points produce a smoother implicit vessel surface.
    """

    sampled = []

    for segment_index in range(len(path) - 1):

        (a, ra) = path[segment_index]
        (b, rb) = path[segment_index + 1]

        delta = subtract(b, a)
        length = magnitude(delta)

        steps = max(1, int(math.ceil(length / spacing)))

        for i in range(steps):

            t = i / steps
            point = lerp(a, b, t)
            radius = ra + (rb - ra) * t

            if (
                not sampled
                or magnitude(subtract(point, sampled[-1][0])) > 1e-8
            ):
                sampled.append((point, radius))

    sampled.append(path[-1])

    return sampled


# ================================================================
# DISTANCE FROM POINT TO SEGMENT (with parametric t for radius lerp)
# ================================================================

def point_segment_distance_t(point, a, b):

    ab = subtract(b, a)
    ap = subtract(point, a)

    ab_squared = ab[0] * ab[0] + ab[1] * ab[1] + ab[2] * ab[2]

    if ab_squared < 1e-12:
        return magnitude(ap), 0.0

    t = (
        ap[0] * ab[0] + ap[1] * ab[1] + ap[2] * ab[2]
    ) / ab_squared

    t = max(0.0, min(1.0, t))

    closest = (
        a[0] + t * ab[0],
        a[1] + t * ab[1],
        a[2] + t * ab[2],
    )

    return magnitude(subtract(point, closest)), t


# ================================================================
# CONVERT CENTERLINES INTO SEGMENTS
#
# Each segment is (a, radius_a, b, radius_b).
# ================================================================

def build_segments(paths):

    segments = []

    for path in paths:

        for i in range(len(path) - 1):

            (a, ra) = path[i]
            (b, rb) = path[i + 1]

            if magnitude(subtract(b, a)) > 1e-9:
                segments.append((a, ra, b, rb))

    return segments


# ================================================================
# IMPLICIT VESSEL FIELD
#
# Negative = inside vessel
# Positive = outside vessel
#
# The minimum (distance - local_radius) across ALL centerline segments
# creates the union of all vessel branches automatically, with each
# segment contributing its own (possibly tapering) local radius.
# ================================================================

def vessel_field(point, segments):

    minimum_value = float("inf")

    for a, ra, b, rb in segments:

        distance, t = point_segment_distance_t(point, a, b)

        local_radius = ra + (rb - ra) * t

        value = distance - local_radius

        if value < minimum_value:
            minimum_value = value

    return minimum_value


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

    t = max(0.0, min(1.0, t))

    return lerp(p1, p2, t)


def marching_tetrahedra(segments, max_radius, grid_spacing=1.75):

    # ------------------------------------------------------------
    # DETERMINE BOUNDS
    # ------------------------------------------------------------

    all_points = []

    for a, ra, b, rb in segments:
        all_points.append(a)
        all_points.append(b)

    min_x = min(p[0] for p in all_points)
    max_x = max(p[0] for p in all_points)

    min_y = min(p[1] for p in all_points)
    max_y = max(p[1] for p in all_points)

    min_z = min(p[2] for p in all_points)
    max_z = max(p[2] for p in all_points)

    margin = max_radius + 2.0 * grid_spacing

    min_x -= margin
    max_x += margin

    min_y -= margin
    max_y += margin

    min_z -= margin
    max_z += margin

    nx = int(math.ceil((max_x - min_x) / grid_spacing)) + 1
    ny = int(math.ceil((max_y - min_y) / grid_spacing)) + 1
    nz = int(math.ceil((max_z - min_z) / grid_spacing)) + 1

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

        key = (i, j, k)

        if key not in field_cache:

            position = grid_position(i, j, k)

            field_cache[key] = vessel_field(position, segments)

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

        vertices.append([point[0], point[1], point[2]])

        vertex_lookup[key] = index

        return index

    # ------------------------------------------------------------
    # PROCESS TETRAHEDRON
    # ------------------------------------------------------------

    def process_tetrahedron(tetra_points, tetra_values):

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
                    value_b,
                )

                intersections.append(intersection)

        if len(intersections) == 3:

            indices = [get_vertex_index(p) for p in intersections]

            if len(set(indices)) == 3:
                triangles.append(indices)

        elif len(intersections) == 4:

            indices = [get_vertex_index(p) for p in intersections]

            if len(set(indices)) == 4:

                triangles.append([indices[0], indices[1], indices[2]])
                triangles.append([indices[0], indices[2], indices[3]])

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

                    cube_points.append(grid_position(gi, gj, gk))
                    cube_values.append(field_value(gi, gj, gk))

                minimum = min(cube_values)
                maximum = max(cube_values)

                if minimum > 0.0:
                    continue

                if maximum < 0.0:
                    continue

                for tetra in CUBE_TETRAHEDRA:

                    tetra_points = [cube_points[index] for index in tetra]
                    tetra_values = [cube_values[index] for index in tetra]

                    process_tetrahedron(tetra_points, tetra_values)

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
    radius=1.6,
    latitude_segments=10,
    longitude_segments=16,
):

    vertices = []
    triangles = []

    cx, cy, cz = center

    for latitude in range(latitude_segments + 1):

        theta = math.pi * latitude / latitude_segments

        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)

        for longitude in range(longitude_segments):

            phi = 2.0 * math.pi * longitude / longitude_segments

            x = cx + radius * sin_theta * math.cos(phi)
            y = cy + radius * sin_theta * math.sin(phi)
            z = cz + radius * cos_theta

            vertices.append([x, y, z])

    for latitude in range(latitude_segments):

        for longitude in range(longitude_segments):

            next_longitude = (longitude + 1) % longitude_segments

            a = latitude * longitude_segments + longitude
            b = latitude * longitude_segments + next_longitude
            c = (latitude + 1) * longitude_segments + longitude
            d = (latitude + 1) * longitude_segments + next_longitude

            triangles.append([a, c, d])
            triangles.append([a, d, b])

    return vertices, triangles


# ================================================================
# TARGET POSITION
#
# Place target before closed end of branch, so it sits inside a
# continuous navigable lumen rather than against the terminal cap.
# ================================================================

def target_before_end(previous_point, endpoint, distance_before_end=8.0):

    direction = normalize(subtract(endpoint, previous_point))

    return subtract(endpoint, multiply(direction, distance_before_end))


# ================================================================
# ROUTE LENGTH
#
# The guidewire's total physical length (shaft + tip) is fixed
# (~180mm). If a phantom's longest modeled route from the deployment
# origin to any branch's terminal waypoint is shorter than that, a
# user who keeps inserting will push the tip out through the open
# (uncapped) end of the vessel once they exceed that route's length —
# which looks identical to "escaping through the wall" but is really
# just running out of modeled anatomy. build_scene() uses this to cap
# the controller's max insertable depth at the network's own longest
# route, so full insertion always lands at (not past) a vessel end.
# ================================================================

def compute_longest_route_length(network):
    """
    Paths are authored trunk-first, branches after, each branch
    starting exactly at an earlier path's endpoint (shared
    coordinate) -- so a single forward pass chaining cumulative
    distance by matching endpoint coordinates covers every phantom
    in sim/phantoms/networks.py. Returns the longest cumulative
    distance, in mm, from the first path's first waypoint to any
    waypoint in the network.
    """

    def point_key(point):
        return (round(point[0], 4), round(point[1], 4), round(point[2], 4))

    cumulative = {}
    longest = 0.0

    pending = list(network["paths"])

    # Repeat until no path in `pending` can be resolved anymore --
    # handles paths listed before the path they connect to, though
    # every phantom currently defined is already in dependency order.
    progress = True
    while pending and progress:

        progress = False
        still_pending = []

        for path in pending:

            points = [point for point, _radius in path]
            start_key = point_key(points[0])

            if start_key in cumulative:
                base = cumulative[start_key]
            elif not cumulative:
                base = 0.0
            else:
                still_pending.append(path)
                continue

            distance = base
            cumulative[start_key] = base

            for i in range(len(points) - 1):
                distance += magnitude(subtract(points[i + 1], points[i]))
                cumulative[point_key(points[i + 1])] = distance

            longest = max(longest, distance)
            progress = True

        pending = still_pending

    return longest


# ================================================================
# MIRROR TRANSFORM
#
# Four standardized presentation variants per phantom:
#
#   0 = original
#   1 = X mirror
#   2 = Y mirror
#   3 = X + Y mirror
#
# All distances, branch angles, and path lengths remain identical;
# only left/right and up/down handedness changes. Useful for varying
# a phantom's visual presentation without altering its difficulty.
# ================================================================

def transform_point(point, variant):

    x, y, z = point

    if variant == 0:
        sx, sy = 1.0, 1.0
    elif variant == 1:
        sx, sy = -1.0, 1.0
    elif variant == 2:
        sx, sy = 1.0, -1.0
    elif variant == 3:
        sx, sy = -1.0, -1.0
    else:
        raise ValueError("variant must be 0, 1, 2, or 3")

    return (sx * x, sy * y, z)


def transform_network(network, variant):
    """Apply the mirror transform to every path, target, and named
    reference point in a network dict, leaving radii untouched."""

    if variant == 0:
        return network

    transformed_paths = [
        [(transform_point(p, variant), r) for (p, r) in path]
        for path in network["paths"]
    ]

    transformed_targets = {
        name: transform_point(pos, variant)
        for name, pos in network["targets"].items()
    }

    result = dict(network)
    result["paths"] = transformed_paths
    result["targets"] = transformed_targets
    result["entry_position"] = transform_point(
        network["entry_position"], variant
    )
    return result


# ================================================================
# BUILD SOFA VESSEL FROM A NETWORK
#
# network = {
#     "paths": [[(point, radius), ...], ...],
#     "targets": {name: point, ...},
# }
# ================================================================

DEFAULT_TARGET_COLORS = [
    [0.90, 0.20, 0.20, 1.0],
    [0.95, 0.55, 0.10, 1.0],
    [0.20, 0.75, 0.25, 1.0],
    [0.55, 0.25, 0.90, 1.0],
    [0.95, 0.20, 0.65, 1.0],
]


def build_vessel_mesh(network, grid_spacing=1.75):
    """
    Pure-geometry step (no SOFA): resample paths, build segments, and run
    marching tetrahedra. Returns (vertices, triangles). Exists as its own
    function so phantom geometry can be sanity-checked without SOFA.
    """

    sampled_paths = [
        sample_polyline(path, spacing=2.0) for path in network["paths"]
    ]

    segments = build_segments(sampled_paths)

    max_radius = max(max(ra, rb) for _, ra, _, rb in segments)

    vertices, triangles = marching_tetrahedra(
        segments=segments,
        max_radius=max_radius,
        grid_spacing=grid_spacing,
    )

    return vertices, triangles


def create_vessel_from_network(rootNode, network, grid_spacing=1.75):

    vertices, triangles = build_vessel_mesh(network, grid_spacing=grid_spacing)

    # ============================================================
    # PHYSICAL / COLLISION VESSEL
    # ============================================================

    vessel = rootNode.addChild("Vessel")

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
    # ============================================================

    visual = vessel.addChild("Visual")

    visual.addObject(
        "OglModel",
        name="VesselVisual",
        position=vertices,
        triangles=triangles,
        color=[0.30, 0.60, 0.90, 0.20],
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
    # TARGET MARKERS
    # ============================================================

    target_nodes = {}

    for index, (target_name, target_position) in enumerate(
        network["targets"].items()
    ):

        target_vertices, target_triangles = create_sphere_mesh(
            target_position,
            radius=1.6,
        )

        target_node = rootNode.addChild(f"Target_{target_name}")

        target_node.addObject(
            "OglModel",
            name=f"{target_name}_Visual",
            position=target_vertices,
            triangles=target_triangles,
            color=DEFAULT_TARGET_COLORS[index % len(DEFAULT_TARGET_COLORS)],
        )

        target_nodes[target_name] = target_node

    print(
        "PHANTOM GENERATED | "
        f"targets={len(network['targets'])} | "
        f"vertices={len(vertices)} | "
        f"triangles={len(triangles)}"
    )

    return {
        "vessel_node": vessel,
        "targets": network["targets"],
        "target_nodes": target_nodes,
        "entry_position": network["entry_position"],
    }
