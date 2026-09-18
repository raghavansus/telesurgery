# tests/test_motion_scale_protocol.py
#
# Pure-Python unit tests for input/motion_scale_protocol.py. No SOFA,
# no pyserial, no hardware required:
#
#   python3 tests/test_motion_scale_protocol.py

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from input.motion_scale_protocol import parse_line


def check(actual, expected, label):
    assert actual == expected, f"{label}: expected {expected!r}, got {actual!r}"


def test_normal_line():
    check(parse_line("12.34,56.78\n"), (12.34, 56.78), "normal line")
    check(parse_line("12.34,56.78"), (12.34, 56.78), "no trailing newline")


def test_negative_and_zero():
    check(parse_line("-4.50,-90.00"), (-4.5, -90.0), "negative values")
    check(parse_line("0.00,0.00"), (0.0, 0.0), "zero values")


def test_whitespace_and_carriage_return():
    check(parse_line("  1.0,2.0  \r\n"), (1.0, 2.0), "whitespace/CR")


def test_malformed_rejected():
    check(parse_line(""), None, "empty line")
    check(parse_line("\n"), None, "newline only")
    check(parse_line("12.34"), None, "missing field")
    check(parse_line("12.34,56.78,extra"), None, "extra field")
    check(parse_line("abc,56.78"), None, "non-numeric distance")
    check(parse_line("12.34,xyz"), None, "non-numeric rotation")
    check(parse_line("Basic Variables initialized"), None, "boot banner text")
    check(parse_line("nan,1.0"), None, "NaN rejected")
    check(parse_line("inf,1.0"), None, "Inf rejected")
    check(parse_line(None), None, "None input")


def test_partial_stream_reassembly():
    # Simulates how MotionScaleDevice.poll() would see bytes arrive
    # split across two reads, then rejoin at the buffer '\n' split.
    buffer = "12.3"
    buffer += "4,56.78\n7.1,8.2\n9"
    lines = buffer.split("\n")
    # Last element "9" is an incomplete trailing line and should be
    # left in the buffer by the caller, not parsed here.
    complete_lines = lines[:-1]
    parsed = [parse_line(l) for l in complete_lines]
    check(parsed, [(12.34, 56.78), (7.1, 8.2)], "reassembled stream")


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
        print(f"OK {test.__name__}")
    print(f"ALL {len(tests)} PROTOCOL TESTS PASSED")


if __name__ == "__main__":
    main()
