# input/motion_scale_device.py
#
# pyserial-backed reader for the Motion Scaling ID physical input
# device (see MS_ID_Final/MS_ID_Final.ino). Parsing is delegated to
# input.motion_scale_protocol so it stays testable without hardware.

from input.motion_scale_protocol import parse_line

DEFAULT_BAUDRATE = 115200


class MotionScaleDevice:
    """
    Non-blocking-ish serial reader: poll() drains whatever bytes are
    currently available, parses every complete line found, and keeps
    the most recent valid (distance_mm, rotation_deg) reading. Designed
    to be called once per SOFA animation step.
    """

    def __init__(self, port, baudrate=DEFAULT_BAUDRATE, timeout=0.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self._serial = None
        self._buffer = ""

        self.connected = False
        self.latest_distance_mm = 0.0
        self.latest_rotation_deg = 0.0
        self.reading_count = 0
        self.last_error = None

    def connect(self):
        import serial  # imported lazily so parsing/tests don't need pyserial installed as hardware

        self._serial = serial.Serial(
            self.port,
            self.baudrate,
            timeout=self.timeout,
        )
        self.connected = True
        self.last_error = None
        print(f"MOTION SCALE DEVICE | connected on {self.port} @ {self.baudrate} baud")

    def disconnect(self):
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
        self.connected = False

    def poll(self):
        """
        Read whatever is available and parse any complete lines.
        Returns True if latest_distance_mm/latest_rotation_deg were
        updated by a new valid reading. Never raises: a lost/unplugged
        device just stops producing updates and sets last_error.
        """

        if not self.connected or self._serial is None:
            return False

        try:
            waiting = self._serial.in_waiting
            if waiting:
                chunk = self._serial.read(waiting)
                self._buffer += chunk.decode("utf-8", errors="ignore")
        except Exception as exc:
            self.last_error = str(exc)
            self.connected = False
            return False

        updated = False

        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            parsed = parse_line(line)

            if parsed is not None:
                self.latest_distance_mm, self.latest_rotation_deg = parsed
                self.reading_count += 1
                updated = True

        return updated
