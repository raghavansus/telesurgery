# sim/phantoms/networks.py
#
# Four purpose-designed experimental phantoms, informed by realistic
# ImageCAS coronary-artery features (curvature, bifurcation/branch
# angles, tortuosity, diameter tapering) but deliberately kept easy
# and reliable to navigate: no stenosis, no hairpin turns, no lumens
# narrower than a few guidewire diameters.
#
# Every phantom shares the same entry geometry so the guidewire
# deployment code in sim/guidewire.py does not need to special-case
# per-phantom entry points:
#
#   start = (0, 0, -8)   BeamAdapter deployment origin
#   entry = (0, 0,  0)   formal vessel ostium
#
# A network is a dict:
#   {
#       "paths":   [[(point_xyz, radius_mm), ...], ...],
#       "targets": {name: point_xyz, ...},
#       "entry_position": point_xyz,
#   }

from sim.phantoms.engine import transform_network

START = (0.0, 0.0, -8.0)
ENTRY = (0.0, 0.0, 0.0)


def _targets_before_end(paths_by_target):
    """paths_by_target: {name: (previous_point, endpoint, distance)}"""
    from sim.phantoms.engine import target_before_end

    return {
        name: target_before_end(prev, end, dist)
        for name, (prev, end, dist) in paths_by_target.items()
    }


# ================================================================
# PHANTOM 0 — GENTLE CURVE
#
# A mildly curving trunk, then a TRIFURCATION (three children, not
# two) into left/right/middle sub-trees; left and right cascade again
# into a scored target + distractor each. The camera's dominant
# viewing axis is world Y (see sim/scene.py InteractiveCamera), so
# left swings deep into +Y and right deep into -Y -- real 3D depth,
# not just a flat curve in the viewing plane -- while middle stays
# near Y=0 as the "straight through" option. Kept the "gentlest" of
# the four phantoms via larger turn radii/smaller per-waypoint
# deltas, but with comparable branch/target count and depth to the
# other three so it is not trivially easy.
# ================================================================

def phantom_gentle_curve(variant=0):

    trunk = [
        (START, 4.5),
        (ENTRY, 4.5),
        ((3.0, 1.0, 22.0), 4.3),
        ((7.0, 3.0, 46.0), 4.1),
        ((9.0, 4.0, 66.0), 3.9),
    ]

    first_bifurcation = trunk[-1][0]

    # ------------------------------------------------------------
    # LEFT (+Y depth). Divergence rate (lateral mm per z mm) is kept
    # at or below ~0.5, matching phantom 1's proven trifurcation --
    # an earlier version diverged faster right after the split and
    # validate_burst_input.py caught the tip slipping through the gap
    # between the fanning-out tubes (same bug, same fix, phantom 2).
    # ------------------------------------------------------------

    left_common = [
        (first_bifurcation, 3.7),
        ((5.0, 9.0, 84.0), 3.6),
        ((0.0, 16.0, 98.0), 3.5),
    ]
    left_split = left_common[-1][0]

    left_upper = [
        (left_split, 3.0),
        ((-6.0, 21.0, 106.0), 3.0),
        ((-9.0, 24.0, 112.0), 2.9),
    ]
    left_upper_split = left_upper[-1][0]

    left_lower = [
        (left_split, 3.0),
        ((3.0, 20.0, 107.0), 3.0),
        ((5.0, 23.0, 113.0), 2.9),
    ]
    left_lower_split = left_lower[-1][0]

    g1_mid, g1_end = (-14.0, 28.0, 120.0), (-17.0, 31.0, 128.0)
    d1_mid, d1_end = (-5.0, 27.0, 121.0), (-3.0, 31.0, 129.0)
    g2_mid, g2_end = (3.0, 28.0, 121.0), (1.0, 32.0, 129.0)
    d2_mid, d2_end = (10.0, 26.0, 122.0), (13.0, 29.0, 130.0)

    # ------------------------------------------------------------
    # RIGHT (-Y depth), same gentler divergence rate as LEFT.
    # ------------------------------------------------------------

    right_common = [
        (first_bifurcation, 3.7),
        ((15.0, -3.0, 84.0), 3.6),
        ((21.0, -8.0, 98.0), 3.5),
    ]
    right_split = right_common[-1][0]

    right_upper = [
        (right_split, 3.0),
        ((27.0, -12.0, 106.0), 3.0),
        ((30.0, -14.0, 112.0), 2.9),
    ]
    right_upper_split = right_upper[-1][0]

    right_lower = [
        (right_split, 3.0),
        ((18.0, -11.0, 107.0), 3.0),
        ((17.0, -13.0, 113.0), 2.9),
    ]
    right_lower_split = right_lower[-1][0]

    g3_mid, g3_end = (35.0, -17.0, 120.0), (39.0, -19.0, 128.0)
    d3_mid, d3_end = (26.0, -16.0, 121.0), (24.0, -19.0, 129.0)
    g4_mid, g4_end = (19.0, -17.0, 121.0), (21.0, -20.0, 129.0)
    d4_mid, d4_end = (11.0, -15.0, 122.0), (8.0, -18.0, 130.0)

    # ------------------------------------------------------------
    # MIDDLE (the third child of the trifurcation; near Y=0, the
    # "straight ahead, minimal depth change" option)
    # ------------------------------------------------------------

    middle = [
        (first_bifurcation, 3.4),
        ((10.0, 5.0, 86.0), 3.3),
        ((11.0, 6.0, 100.0), 3.0),
    ]

    g5_mid, g5_end = (12.0, 7.0, 112.0), (13.0, 8.0, 122.0)

    def p(*pts_and_radii):
        return list(pts_and_radii)

    paths = [
        trunk,
        left_common,
        left_upper,
        p((left_upper_split, 2.7), (g1_mid, 2.7), (g1_end, 2.5)),
        p((left_upper_split, 2.7), (d1_mid, 2.7), (d1_end, 2.5)),
        left_lower,
        p((left_lower_split, 2.7), (g2_mid, 2.7), (g2_end, 2.5)),
        p((left_lower_split, 2.7), (d2_mid, 2.7), (d2_end, 2.5)),
        right_common,
        right_upper,
        p((right_upper_split, 2.7), (g3_mid, 2.7), (g3_end, 2.5)),
        p((right_upper_split, 2.7), (d3_mid, 2.7), (d3_end, 2.5)),
        right_lower,
        p((right_lower_split, 2.7), (g4_mid, 2.7), (g4_end, 2.5)),
        p((right_lower_split, 2.7), (d4_mid, 2.7), (d4_end, 2.5)),
        middle,
        p((middle[-1][0], 2.7), (g5_mid, 2.7), (g5_end, 2.5)),
    ]

    targets = _targets_before_end({
        "G1": (g1_mid, g1_end, 5.0),
        "G2": (g2_mid, g2_end, 5.0),
        "G3": (g3_mid, g3_end, 5.0),
        "G4": (g4_mid, g4_end, 5.0),
        "G5": (g5_mid, g5_end, 5.0),
    })

    network = {
        "paths": paths,
        "targets": targets,
        "entry_position": ENTRY,
    }

    return transform_network(network, variant)


# ================================================================
# PHANTOM 1 — BIFURCATION TREE
#
# The original proven study phantom: a common trunk splitting into
# left/right common branches, each of which splits again into two
# terminal routes with an unscored "distractor" branch alongside
# every scored target. Moderate difficulty; five scored targets.
# ================================================================

def phantom_bifurcation_tree(variant=0):

    R = 4.0

    trunk_mid = (0.0, 0.0, 18.0)
    first_bifurcation = (0.0, 0.0, 36.0)

    left_mid = (-7.0, 2.0, 48.0)
    left_split = (-16.0, 4.0, 61.0)
    left_upper_mid = (-25.0, 8.0, 78.0)
    left_upper_split = (-30.0, 9.0, 91.0)
    left_lower_mid = (-11.0, 11.0, 79.0)
    left_lower_split = (-9.0, 12.0, 93.0)

    g1_mid, g1_end = (-38.0, 12.0, 108.0), (-43.0, 13.0, 132.0)
    d1_mid, d1_end = (-25.0, 20.0, 108.0), (-20.0, 23.0, 130.0)
    g2_mid, g2_end = (-17.0, 17.0, 110.0), (-22.0, 20.0, 135.0)
    d2_mid, d2_end = (0.0, 9.0, 109.0), (6.0, 5.0, 130.0)

    right_mid = (7.0, -2.0, 48.0)
    right_split = (16.0, -4.0, 61.0)
    right_upper = (29.0, -8.0, 83.0)
    right_center = (18.0, 1.0, 86.0)
    right_lower = (10.0, -15.0, 83.0)

    g3_mid, g3_end = (39.0, -10.0, 106.0), (47.0, -12.0, 132.0)
    d3_mid, d3_end = (31.0, -19.0, 107.0), (34.0, -26.0, 130.0)
    g4_mid, g4_end = (19.0, 8.0, 110.0), (24.0, 12.0, 137.0)
    d4_mid, d4_end = (31.0, 4.0, 108.0), (39.0, 7.0, 130.0)
    g5_mid, g5_end = (8.0, -23.0, 108.0), (5.0, -30.0, 134.0)
    d5_mid, d5_end = (-3.0, -21.0, 106.0), (-9.0, -24.0, 128.0)

    def p(*pts):
        return [(pt, R) for pt in pts]

    paths = [
        p(START, ENTRY, trunk_mid, first_bifurcation),
        p(first_bifurcation, left_mid, left_split),
        p(left_split, left_upper_mid, left_upper_split),
        p(left_upper_split, g1_mid, g1_end),
        p(left_upper_split, d1_mid, d1_end),
        p(left_split, left_lower_mid, left_lower_split),
        p(left_lower_split, g2_mid, g2_end),
        p(left_lower_split, d2_mid, d2_end),
        p(first_bifurcation, right_mid, right_split),
        p(right_split, right_upper),
        p(right_upper, g3_mid, g3_end),
        p(right_upper, d3_mid, d3_end),
        p(right_split, right_center),
        p(right_center, g4_mid, g4_end),
        p(right_center, d4_mid, d4_end),
        p(right_split, right_lower),
        p(right_lower, g5_mid, g5_end),
        p(right_lower, d5_mid, d5_end),
    ]

    targets = _targets_before_end({
        "G1": (g1_mid, g1_end, 8.0),
        "G2": (g2_mid, g2_end, 8.0),
        "G3": (g3_mid, g3_end, 8.0),
        "G4": (g4_mid, g4_end, 8.0),
        "G5": (g5_mid, g5_end, 8.0),
    })

    network = {
        "paths": paths,
        "targets": targets,
        "entry_position": ENTRY,
    }

    return transform_network(network, variant)


# ================================================================
# PHANTOM 2 — TORTUOUS S-CURVE
#
# The trunk itself follows two consecutive S-bends before reaching a
# TRIFURCATION: left swings deep into +Y depth, right deep into -Y
# depth, middle stays shallow ("straight ahead"), mirroring PHANTOM
# 0's depth structure. Left and right each cascade again into a
# scored target + distractor. This phantom exercises axial rotation
# more heavily than the others: the guidewire tip must be actively
# steered through the S-bends before any branch/depth selection.
#
# NOTE: an earlier version of this trunk had a much tighter direction
# reversal around z=30-45 (x: 10 -> 4 in 15mm) that a burst-input
# stress test (tests/validate_burst_input.py) found could tunnel the
# guidewire through the wall under imperfect/bursty steering, not
# just under a deliberately smooth expert push. This version spreads
# the same lateral excursion over more waypoints/z-distance so the
# effective turn radius at each bend is gentler, while still
# requiring real rotation to follow.
# ================================================================

def phantom_tortuous_scurve(variant=0):

    trunk = [
        (START, 4.4),
        (ENTRY, 4.3),
        ((4.0, 0.0, 14.0), 4.2),
        ((6.0, -1.0, 26.0), 4.0),
        ((4.0, -2.0, 38.0), 3.9),
        ((-1.0, -2.5, 49.0), 3.8),
        ((-4.0, -1.0, 60.0), 3.7),
        ((-4.0, 1.0, 71.0), 3.6),
        ((-1.0, 2.5, 80.0), 3.55),
    ]

    first_bifurcation = trunk[-1][0]

    # ------------------------------------------------------------
    # LEFT (+Y depth). Divergence rate (lateral mm per z mm) is kept
    # at or below ~0.5, matching phantom 1's proven trifurcation --
    # an earlier version of this trifurcation diverged much faster
    # (~0.7) right after the split and validate_burst_input.py caught
    # the tip slipping through the gap between the fanning-out tubes.
    # ------------------------------------------------------------

    left_common = [
        (first_bifurcation, 3.4),
        ((-3.0, 9.0, 98.0), 3.3),
        ((-7.0, 16.0, 112.0), 3.2),
    ]
    left_split = left_common[-1][0]

    left_upper = [
        (left_split, 2.8),
        ((-11.0, 20.0, 120.0), 2.8),
        ((-13.0, 22.0, 126.0), 2.7),
    ]
    left_upper_split = left_upper[-1][0]

    left_lower = [
        (left_split, 2.8),
        ((-4.0, 19.0, 120.0), 2.8),
        ((-2.0, 21.0, 126.0), 2.7),
    ]
    left_lower_split = left_lower[-1][0]

    g1_mid, g1_end = (-16.0, 25.0, 132.0), (-19.0, 27.0, 138.0)
    d1_mid, d1_end = (-9.0, 24.0, 133.0), (-7.0, 27.0, 139.0)
    g2_mid, g2_end = (-1.0, 26.0, 132.0), (-3.0, 29.0, 138.0)
    d2_mid, d2_end = (4.0, 23.0, 133.0), (7.0, 25.0, 139.0)

    # ------------------------------------------------------------
    # RIGHT (-Y depth), same gentler divergence rate as LEFT.
    # ------------------------------------------------------------

    right_common = [
        (first_bifurcation, 3.4),
        ((4.0, -6.0, 98.0), 3.3),
        ((8.0, -11.0, 112.0), 3.2),
    ]
    right_split = right_common[-1][0]

    right_upper = [
        (right_split, 2.8),
        ((13.0, -14.0, 120.0), 2.8),
        ((15.0, -15.0, 126.0), 2.7),
    ]
    right_upper_split = right_upper[-1][0]

    right_lower = [
        (right_split, 2.8),
        ((5.0, -13.0, 120.0), 2.8),
        ((3.0, -14.0, 126.0), 2.7),
    ]
    right_lower_split = right_lower[-1][0]

    g3_mid, g3_end = (19.0, -18.0, 132.0), (22.0, -19.0, 138.0)
    d3_mid, d3_end = (11.0, -17.0, 133.0), (9.0, -19.0, 139.0)
    g4_mid, g4_end = (5.0, -17.0, 132.0), (7.0, -19.0, 138.0)
    d4_mid, d4_end = (-1.0, -15.0, 133.0), (-4.0, -16.0, 139.0)

    # ------------------------------------------------------------
    # MIDDLE (third child of the trifurcation; shallow Y)
    # ------------------------------------------------------------

    middle = [
        (first_bifurcation, 3.1),
        ((0.0, 4.0, 96.0), 3.0),
        ((1.0, 5.0, 110.0), 2.8),
    ]

    g5_mid, g5_end = (2.0, 6.0, 120.0), (3.0, 7.0, 128.0)

    def p(*pts_and_radii):
        return list(pts_and_radii)

    paths = [
        trunk,
        left_common,
        left_upper,
        p((left_upper_split, 2.5), (g1_mid, 2.5), (g1_end, 2.4)),
        p((left_upper_split, 2.5), (d1_mid, 2.5), (d1_end, 2.4)),
        left_lower,
        p((left_lower_split, 2.5), (g2_mid, 2.5), (g2_end, 2.4)),
        p((left_lower_split, 2.5), (d2_mid, 2.5), (d2_end, 2.4)),
        right_common,
        right_upper,
        p((right_upper_split, 2.5), (g3_mid, 2.5), (g3_end, 2.4)),
        p((right_upper_split, 2.5), (d3_mid, 2.5), (d3_end, 2.4)),
        right_lower,
        p((right_lower_split, 2.5), (g4_mid, 2.5), (g4_end, 2.4)),
        p((right_lower_split, 2.5), (d4_mid, 2.5), (d4_end, 2.4)),
        middle,
        p((middle[-1][0], 2.6), (g5_mid, 2.6), (g5_end, 2.4)),
    ]

    targets = _targets_before_end({
        "G1": (g1_mid, g1_end, 5.0),
        "G2": (g2_mid, g2_end, 5.0),
        "G3": (g3_mid, g3_end, 5.0),
        "G4": (g4_mid, g4_end, 5.0),
        "G5": (g5_mid, g5_end, 5.0),
    })

    network = {
        "paths": paths,
        "targets": targets,
        "entry_position": ENTRY,
    }

    return transform_network(network, variant)


# ================================================================
# PHANTOM 3 — MULTI-BRANCH DISTAL TREE
#
# A trunk splits into a TRIFURCATION: left/right common branches
# (each cascading twice more into a scored target + distractor, as
# before) plus a shallow middle branch straight to a fifth scored
# target. Left swings deep into +Y depth, right deep into -Y depth,
# middle stays near Y=0 -- real 3D structure, not a flat tree.
# Vessel diameter tapers from 9 mm at the ostium down to ~4.6 mm at
# the terminal targets (ImageCAS-informed diameter variation), while
# staying far above any stenosis threshold.
# ================================================================

def phantom_multi_branch(variant=0):

    trunk = [
        (START, 4.5),
        (ENTRY, 4.4),
        ((0.0, 0.0, 20.0), 4.3),
        ((0.0, 0.0, 40.0), 4.1),
    ]

    branch_point_1 = trunk[-1][0]

    # ------------------------------------------------------------
    # LEFT (+Y depth). Divergence rate (lateral mm per z mm) is kept
    # at or below ~0.5, matching phantom 1's proven trifurcation --
    # an earlier version diverged much faster (~0.8) right after the
    # split and validate_burst_input.py caught the tip slipping
    # through the gap between the fanning-out tubes (same bug as
    # phantoms 0 and 2, same fix).
    # ------------------------------------------------------------

    left_common = [
        (branch_point_1, 3.9),
        ((-4.0, 8.0, 58.0), 3.7),
        ((-10.0, 15.0, 76.0), 3.5),
    ]

    left_split = left_common[-1][0]

    left_upper = [
        (left_split, 3.0),
        ((-16.0, 20.0, 88.0), 2.9),
        ((-19.0, 22.0, 96.0), 2.7),
    ]
    left_upper_split = left_upper[-1][0]

    left_lower = [
        (left_split, 3.0),
        ((-8.0, 19.0, 89.0), 2.9),
        ((-8.0, 21.0, 97.0), 2.7),
    ]
    left_lower_split = left_lower[-1][0]

    g1_mid, g1_end = (-24.0, 25.0, 104.0), (-27.0, 27.0, 111.0)
    d1_mid, d1_end = (-15.0, 26.0, 105.0), (-12.0, 29.0, 112.0)
    g2_mid, g2_end = (-9.0, 24.0, 105.0), (-10.0, 27.0, 112.0)
    d2_mid, d2_end = (-3.0, 23.0, 106.0), (0.0, 26.0, 113.0)

    # ------------------------------------------------------------
    # RIGHT (-Y depth), same gentler divergence rate as LEFT.
    # ------------------------------------------------------------

    right_common = [
        (branch_point_1, 3.9),
        ((4.0, -8.0, 58.0), 3.7),
        ((10.0, -15.0, 76.0), 3.5),
    ]

    right_split = right_common[-1][0]

    right_upper = [
        (right_split, 3.0),
        ((16.0, -20.0, 88.0), 2.9),
        ((19.0, -22.0, 96.0), 2.7),
    ]
    right_upper_split = right_upper[-1][0]

    right_lower = [
        (right_split, 3.0),
        ((8.0, -19.0, 89.0), 2.9),
        ((8.0, -21.0, 97.0), 2.7),
    ]
    right_lower_split = right_lower[-1][0]

    g3_mid, g3_end = (24.0, -25.0, 104.0), (27.0, -27.0, 111.0)
    d3_mid, d3_end = (15.0, -26.0, 105.0), (12.0, -29.0, 112.0)
    g4_mid, g4_end = (9.0, -24.0, 105.0), (10.0, -27.0, 112.0)
    d4_mid, d4_end = (3.0, -23.0, 106.0), (0.0, -26.0, 113.0)

    # ------------------------------------------------------------
    # MIDDLE (third child of the trifurcation; shallow Y, straight
    # through to a fifth scored target, no distractor)
    # ------------------------------------------------------------

    middle = [
        (branch_point_1, 3.7),
        ((0.0, 2.0, 60.0), 3.3),
        ((0.0, 3.0, 80.0), 2.9),
    ]

    g5_mid, g5_end = (0.0, 4.0, 94.0), (0.0, 5.0, 104.0)

    def p(*pts_and_radii):
        return list(pts_and_radii)

    paths = [
        trunk,
        left_common,
        left_upper,
        p((left_upper_split, 2.4), (g1_mid, 2.4), (g1_end, 2.3)),
        p((left_upper_split, 2.4), (d1_mid, 2.4), (d1_end, 2.3)),
        left_lower,
        p((left_lower_split, 2.4), (g2_mid, 2.4), (g2_end, 2.3)),
        p((left_lower_split, 2.4), (d2_mid, 2.4), (d2_end, 2.3)),
        right_common,
        right_upper,
        p((right_upper_split, 2.4), (g3_mid, 2.4), (g3_end, 2.3)),
        p((right_upper_split, 2.4), (d3_mid, 2.4), (d3_end, 2.3)),
        right_lower,
        p((right_lower_split, 2.4), (g4_mid, 2.4), (g4_end, 2.3)),
        p((right_lower_split, 2.4), (d4_mid, 2.4), (d4_end, 2.3)),
        middle,
        p((middle[-1][0], 2.6), (g5_mid, 2.6), (g5_end, 2.4)),
    ]

    targets = _targets_before_end({
        "G1": (g1_mid, g1_end, 5.0),
        "G2": (g2_mid, g2_end, 5.0),
        "G3": (g3_mid, g3_end, 5.0),
        "G4": (g4_mid, g4_end, 5.0),
        "G5": (g5_mid, g5_end, 5.0),
    })

    network = {
        "paths": paths,
        "targets": targets,
        "entry_position": ENTRY,
    }

    return transform_network(network, variant)


# ================================================================
# REGISTRY
# ================================================================

PHANTOMS = [
    {
        "id": 0,
        "key": "gentle_curve",
        "name": "Gentle Curve",
        "description": (
            "Gently curving trunk into a TRIFURCATION (left swings "
            "into +Y depth, right into -Y depth, middle stays "
            "shallow): 5 scored targets + 4 distractors, 9 terminal "
            "routes, real 3D structure. Uses the largest turn radii "
            "of the four phantoms -- gentlest by curvature, not by "
            "branch count or depth."
        ),
        "build": phantom_gentle_curve,
    },
    {
        "id": 1,
        "key": "bifurcation_tree",
        "name": "Bifurcation Tree",
        "description": (
            "The original proven design. Trunk splitting into "
            "left/right branches (right is itself a trifurcation), "
            "cascading into 5 scored targets + 5 distractors "
            "(10 terminal routes)."
        ),
        "build": phantom_bifurcation_tree,
    },
    {
        "id": 2,
        "key": "tortuous_scurve",
        "name": "Tortuous S-Curve",
        "description": (
            "Trunk follows two consecutive S-bends, then a "
            "TRIFURCATION with the same +Y/-Y/shallow depth "
            "structure as phantom 0: 5 scored targets + 4 "
            "distractors, 9 terminal routes. Emphasizes axial "
            "rotation most of the four phantoms."
        ),
        "build": phantom_tortuous_scurve,
    },
    {
        "id": 3,
        "key": "multi_branch",
        "name": "Multi-Branch Distal Tree",
        "description": (
            "A TRIFURCATION (left +Y depth / right -Y depth / "
            "shallow middle) where left and right cascade twice more: "
            "5 scored targets + 4 distractors, 9 terminal routes, "
            "vessel diameter tapering from 9 mm to ~4.6 mm distally. "
            "Emphasizes sequential branch-selection decisions across "
            "real depth, not just a flat tree."
        ),
        "build": phantom_multi_branch,
    },
]


def get_phantom(phantom_id, variant=0):

    for entry in PHANTOMS:
        if entry["id"] == phantom_id:
            return entry["build"](variant=variant)

    raise ValueError(
        f"Unknown phantom_id={phantom_id}; "
        f"valid ids are {[e['id'] for e in PHANTOMS]}"
    )


def get_phantom_info(phantom_id):

    for entry in PHANTOMS:
        if entry["id"] == phantom_id:
            return entry

    raise ValueError(f"Unknown phantom_id={phantom_id}")
