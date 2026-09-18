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
# One mildly curving trunk, then a single bifurcation into two
# terminal branches at a moderate angle. Minimal tortuosity — this
# is the easiest phantom, intended for first-time users and basic
# device calibration.
# ================================================================

def phantom_gentle_curve(variant=0):

    trunk = [
        (START, 4.5),
        (ENTRY, 4.5),
        ((3.0, 1.0, 20.0), 4.3),
        ((8.0, 3.0, 45.0), 4.1),
        ((10.0, 4.0, 70.0), 3.9),
        ((10.0, 5.0, 85.0), 3.8),
    ]

    bifurcation = trunk[-1][0]

    branch_g1 = [
        (bifurcation, 3.6),
        ((20.0, 6.0, 100.0), 3.2),
        ((32.0, 7.0, 118.0), 3.0),
    ]

    branch_g2 = [
        (bifurcation, 3.6),
        ((2.0, 8.0, 102.0), 3.2),
        ((-8.0, 10.0, 120.0), 3.0),
    ]

    targets = _targets_before_end({
        "G1": (branch_g1[-2][0], branch_g1[-1][0], 8.0),
        "G2": (branch_g2[-2][0], branch_g2[-1][0], 8.0),
    })

    network = {
        "paths": [trunk, branch_g1, branch_g2],
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
# The trunk itself follows two consecutive S-bends before reaching
# a bifurcation whose two branches leave at distinctly different
# angles (one acute/shallow, one wide/lateral). This phantom
# exercises axial rotation more heavily than the others: the
# guidewire tip must be actively steered through the S-bends and
# then rotated toward the desired branch angle.
# ================================================================

def phantom_tortuous_scurve(variant=0):

    trunk = [
        (START, 4.5),
        (ENTRY, 4.4),
        ((6.0, 0.0, 15.0), 4.2),
        ((10.0, -2.0, 30.0), 4.0),
        ((4.0, -4.0, 45.0), 3.9),
        ((-4.0, -3.0, 60.0), 3.8),
        ((-8.0, 0.0, 75.0), 3.7),
        ((-4.0, 3.0, 90.0), 3.6),
        ((0.0, 4.0, 100.0), 3.5),
    ]

    bifurcation = trunk[-1][0]

    # Acute/shallow branch: continues mostly forward with a modest
    # lateral deflection.
    branch_g1 = [
        (bifurcation, 3.2),
        ((10.0, 6.0, 112.0), 3.0),
        ((22.0, 7.0, 122.0), 2.8),
    ]

    # Wide/lateral branch: turns sharply sideways.
    branch_g2 = [
        (bifurcation, 3.2),
        ((-14.0, 10.0, 108.0), 3.0),
        ((-26.0, 14.0, 112.0), 2.8),
    ]

    targets = _targets_before_end({
        "G1": (branch_g1[-2][0], branch_g1[-1][0], 8.0),
        "G2": (branch_g2[-2][0], branch_g2[-1][0], 8.0),
    })

    network = {
        "paths": [trunk, branch_g1, branch_g2],
        "targets": targets,
        "entry_position": ENTRY,
    }

    return transform_network(network, variant)


# ================================================================
# PHANTOM 3 — MULTI-BRANCH DISTAL TREE
#
# A trunk splits into left/right common branches, each of which
# splits again into an upper/lower terminal route — two cascaded
# bifurcation decisions per side, four scored targets total.
# Vessel diameter tapers from 9 mm at the ostium down to 5 mm at
# the terminal targets (ImageCAS-informed diameter variation),
# while staying far above any stenosis threshold.
# ================================================================

def phantom_multi_branch(variant=0):

    trunk = [
        (START, 4.5),
        (ENTRY, 4.4),
        ((0.0, 0.0, 20.0), 4.3),
        ((0.0, 0.0, 40.0), 4.1),
    ]

    branch_point_1 = trunk[-1][0]

    left_common = [
        (branch_point_1, 3.9),
        ((-10.0, 3.0, 55.0), 3.6),
        ((-15.0, 5.0, 68.0), 3.4),
    ]

    left_split = left_common[-1][0]

    left_upper = [
        (left_split, 3.1),
        ((-22.0, 8.0, 82.0), 2.8),
        ((-30.0, 10.0, 98.0), 2.5),
    ]

    left_lower = [
        (left_split, 3.1),
        ((-12.0, 10.0, 84.0), 2.8),
        ((-14.0, 14.0, 100.0), 2.5),
    ]

    right_common = [
        (branch_point_1, 3.9),
        ((10.0, -3.0, 55.0), 3.6),
        ((15.0, -5.0, 68.0), 3.4),
    ]

    right_split = right_common[-1][0]

    right_upper = [
        (right_split, 3.1),
        ((22.0, -8.0, 82.0), 2.8),
        ((30.0, -10.0, 98.0), 2.5),
    ]

    right_lower = [
        (right_split, 3.1),
        ((12.0, -10.0, 84.0), 2.8),
        ((14.0, -14.0, 100.0), 2.5),
    ]

    targets = _targets_before_end({
        "G1": (left_upper[-2][0], left_upper[-1][0], 8.0),
        "G2": (left_lower[-2][0], left_lower[-1][0], 8.0),
        "G3": (right_upper[-2][0], right_upper[-1][0], 8.0),
        "G4": (right_lower[-2][0], right_lower[-1][0], 8.0),
    })

    network = {
        "paths": [
            trunk,
            left_common, left_upper, left_lower,
            right_common, right_upper, right_lower,
        ],
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
            "Single mildly curving trunk ending in one bifurcation "
            "(2 targets). Easiest phantom; good for first-time users "
            "and device calibration."
        ),
        "build": phantom_gentle_curve,
    },
    {
        "id": 1,
        "key": "bifurcation_tree",
        "name": "Bifurcation Tree",
        "description": (
            "Trunk splitting into left/right branches, each splitting "
            "again into a scored target and an unscored distractor "
            "(5 targets). Moderate difficulty."
        ),
        "build": phantom_bifurcation_tree,
    },
    {
        "id": 2,
        "key": "tortuous_scurve",
        "name": "Tortuous S-Curve",
        "description": (
            "Trunk follows two consecutive S-bends before a "
            "bifurcation with an acute-angle branch and a wide-angle "
            "branch (2 targets). Emphasizes axial rotation."
        ),
        "build": phantom_tortuous_scurve,
    },
    {
        "id": 3,
        "key": "multi_branch",
        "name": "Multi-Branch Distal Tree",
        "description": (
            "Two cascaded bifurcations per side (4 targets total) "
            "with vessel diameter tapering from 9 mm to 5 mm distally. "
            "Emphasizes sequential branch-selection decisions."
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
