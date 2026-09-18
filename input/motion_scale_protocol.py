# input/motion_scale_protocol.py
#
# Pure parsing logic for the Motion Scaling ID device's serial
# protocol, with NO SOFA or pyserial dependency, so it can be
# unit-tested without hardware or a SOFA install.
#
# Protocol, derived from MS_ID_Final/MS_ID_Final.ino (authoritative
# source for the physical device's behavior):
#
#   Serial.begin(115200, ...)
#   ...
#   Serial.print(distanceValue);
#   Serial.print(",");
#   Serial.println(rotRelativeDeg);
#
# emitted roughly every `printInterval` (200 ms) once the device has
# captured its power-on zero (`startCaptured`). Both fields are
# floats, relative to that power-on zero, NOT deltas between messages:
#
#   distanceValue   millimeters. Derived on the device as
#                   ((rawAngle - startingAngle) + distanceOffset) *
#                   LINEAR_MM_PER_RAD. The device's own clutch/recovery
#                   mechanism (`recoveryMode`) re-anchors distanceOffset
#                   whenever the underlying rotary sensor would
#                   otherwise wrap, so distanceValue stays continuous
#                   and effectively unbounded from the host's point of
#                   view even though the physical mechanism has a
#                   limited (+-~72mm) range of motion per throw.
#
#   rotRelativeDeg  degrees, unbounded, = rotAngle - startingRotAngle
#                   in degrees (the device also computes a
#                   sliding-window bounded version internally for its
#                   own buzzer/limit logic, but that bounded value is
#                   NOT what is sent over serial).
#
# Sign convention: whatever the device reports is used as-is (positive
# distanceValue = deeper insertion, positive rotRelativeDeg = the
# device's positive rotation direction). This is the authoritative
# device behavior and must not be reinterpreted here.

from typing import Optional, Tuple


def parse_line(line: str) -> Optional[Tuple[float, float]]:
    """
    Parse one line of the device's serial output.

    Returns (distance_mm, rotation_deg) or None if the line is not a
    valid, complete reading (partial line, wrong field count, non-
    numeric field, NaN/Inf). Callers should simply skip None results
    and keep the previous reading; malformed/partial lines are
    expected during normal serial operation (buffer boundaries,
    device boot banner text, etc).
    """

    if line is None:
        return None

    stripped = line.strip()

    if not stripped:
        return None

    fields = stripped.split(",")

    if len(fields) != 2:
        return None

    try:
        distance_mm = float(fields[0])
        rotation_deg = float(fields[1])
    except ValueError:
        return None

    if not (_is_finite(distance_mm) and _is_finite(rotation_deg)):
        return None

    return distance_mm, rotation_deg


def _is_finite(value: float) -> bool:
    return value == value and value not in (
        float("inf"),
        float("-inf"),
    )
