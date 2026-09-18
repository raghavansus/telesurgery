# input/motion_scale_controller.py
#
# SOFA controller that drives the SAME GuidewireCommandController
# (guidewire_controller.py) used by keyboard_control.py, but from the
# Motion Scaling physical device instead of the keyboard. This is the
# only piece that differs between the two entry points; everything
# downstream (BeamAdapter guidewire, phantom, collision, physics) is
# identical, built once by sim.scene.build_scene().
#
# Mapping: on the first device reading this controller "homes" to the
# guidewire's current insertion depth/rotation and the device's
# current distance/rotation, then every step maps further device
# displacement onto further guidewire displacement:
#
#   target_insertion = base_insertion + translation_scale * (distance - zero_distance)
#   target_rotation   = base_rotation   + rotation_scale    * (rotation - zero_rotation)
#
# translation_scale / rotation_scale are the "motion scaling ratio"
# (device mm -> sim mm, device deg -> sim deg); both default to 1.0
# (1:1) and are the extension point for future motion-scaling-ratio
# experiments (task: "different motion scaling ratios").
#
# Absolute mapping (not incremental delta-per-step integration) is
# used deliberately: it is immune to dropped/garbled serial lines
# (a skipped reading just means the next good reading still lands on
# the right absolute target) rather than accumulating drift.

import Sofa


class MotionScaleInputController(Sofa.Core.Controller):

    def __init__(
        self,
        command_controller,
        device,
        translation_scale=1.0,
        rotation_scale=1.0,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.command_controller = command_controller
        self.device = device

        self.translation_scale = translation_scale
        self.rotation_scale = rotation_scale

        self._zero_distance_mm = None
        self._zero_rotation_deg = None

        self._base_insertion_depth = command_controller.get_insertion_depth()
        self._base_rotation_deg = command_controller.get_rotation_degrees()

        self.last_target_insertion = self._base_insertion_depth
        self.last_target_rotation_deg = self._base_rotation_deg

    def onAnimateBeginEvent(self, event):

        self.device.poll()

        if self._zero_distance_mm is None:
            # Home on the first reading, whatever it is, so the
            # guidewire does not jump the moment the device connects.
            self._zero_distance_mm = self.device.latest_distance_mm
            self._zero_rotation_deg = self.device.latest_rotation_deg
            return

        delta_distance_mm = (
            self.device.latest_distance_mm - self._zero_distance_mm
        )
        delta_rotation_deg = (
            self.device.latest_rotation_deg - self._zero_rotation_deg
        )

        target_insertion = (
            self._base_insertion_depth
            + self.translation_scale * delta_distance_mm
        )
        target_rotation_deg = (
            self._base_rotation_deg
            + self.rotation_scale * delta_rotation_deg
        )

        self.command_controller.set_insertion_depth(target_insertion)
        self.command_controller.set_rotation_degrees(target_rotation_deg)

        self.last_target_insertion = target_insertion
        self.last_target_rotation_deg = target_rotation_deg

    def rehome(self):
        """Re-zero to the device's current reading without moving the
        guidewire; useful after a reconnect."""

        self._zero_distance_mm = self.device.latest_distance_mm
        self._zero_rotation_deg = self.device.latest_rotation_deg
        self._base_insertion_depth = self.command_controller.get_insertion_depth()
        self._base_rotation_deg = self.command_controller.get_rotation_degrees()
