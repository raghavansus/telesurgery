import Sofa
import math


class GuidewireCommandController(Sofa.Core.Controller):

    def __init__(
        self,
        deploy_controller,
        max_length,
        translation_step=0.5,
        rotation_step_degrees=5.0,
        **kwargs
    ):
        super().__init__(**kwargs)

        self.deploy_controller = deploy_controller
        self.max_length = max_length

        self.translation_step = translation_step

        self.rotation_step = math.radians(
            rotation_step_degrees
        )

        # ========================================================
        # KEYBOARD INPUT RATE LIMITING
        #
        # A single physical keypress can generate several
        # onKeypressedEvent calls before the next physics step runs
        # (OS key-repeat, or several distinct keys pressed close
        # together). If those were all applied to xtip/rotation
        # instantly, a burst could move the guidewire much farther in
        # one physics step than the collision system's alarm/contact
        # margins are sized for, letting the tip tunnel through the
        # thin vessel wall instead of being stopped by it.
        #
        # Keyboard-driven motion is therefore queued here and drained
        # by onAnimateBeginEvent at most one step's worth of motion
        # per physics step, so a burst of keypresses gets spread
        # across several physics steps instead of jumping in one.
        # apply_command()/apply_translation()/apply_rotation() remain
        # instant, unrate-limited calls for direct/programmatic use
        # (tests, motion_scale_control's absolute set_* calls).
        # ========================================================

        self.max_translation_per_step = translation_step
        self.max_rotation_per_step = self.rotation_step

        self._pending_translation = 0.0
        self._pending_rotation = 0.0

    # ============================================================
    # MAIN COMMAND INTERFACE
    #
    # This is the function that everything should eventually use:
    #
    # input
    #   ↓
    # motion scaling
    #   ↓
    # apply_command()
    #   ↓
    # BeamAdapter
    #
    # translation:
    #   positive = insert
    #   negative = retract
    #
    # rotation:
    #   radians
    # ============================================================

    def apply_command(
        self,
        translation=0.0,
        rotation=0.0
    ):

        self.apply_translation(
            translation
        )

        self.apply_rotation(
            rotation
        )

        self.print_state(
            translation,
            rotation
        )

    # ============================================================
    # TRANSLATION
    # ============================================================

    def apply_translation(
        self,
        translation
    ):

        current_xtip = list(
            self.deploy_controller.xtip.value
        )

        new_xtip = (
            float(current_xtip[0])
            + float(translation)
        )

        # Keep insertion depth within physical wire limits
        new_xtip = max(
            0.0,
            min(
                self.max_length,
                new_xtip
            )
        )

        current_xtip[0] = new_xtip

        self.deploy_controller.xtip.value = (
            current_xtip
        )

    # ============================================================
    # ROTATION
    # ============================================================

    def apply_rotation(
        self,
        rotation
    ):

        current_rotation = list(
            self.deploy_controller
            .rotationInstrument.value
        )

        current_rotation[0] += float(
            rotation
        )

        self.deploy_controller.rotationInstrument.value = (
            current_rotation
        )

    # ============================================================
    # GET CURRENT STATE
    # ============================================================

    def get_insertion_depth(self):

        return float(
            self.deploy_controller
            .xtip.value[0]
        )

    def get_rotation(self):

        return float(
            self.deploy_controller
            .rotationInstrument.value[0]
        )

    def get_rotation_degrees(self):

        return math.degrees(
            self.get_rotation()
        )

    # ============================================================
    # SET ABSOLUTE VALUES
    #
    # Useful later for:
    # - resetting trials
    # - debugging
    # - study initialization
    # ============================================================

    def set_insertion_depth(
        self,
        insertion_depth
    ):

        insertion_depth = max(
            0.0,
            min(
                self.max_length,
                float(insertion_depth)
            )
        )

        self.deploy_controller.xtip.value = [
            insertion_depth
        ]

    def set_rotation(
        self,
        rotation
    ):

        self.deploy_controller.rotationInstrument.value = [
            float(rotation)
        ]

    def set_rotation_degrees(
        self,
        rotation_degrees
    ):

        self.set_rotation(
            math.radians(
                rotation_degrees
            )
        )

    # ============================================================
    # RESET
    # ============================================================

    def reset_guidewire(
        self,
        insertion_depth=10.0,
        rotation=0.0
    ):

        self.set_insertion_depth(
            insertion_depth
        )

        self.set_rotation(
            rotation
        )

        print(
            "GUIDEWIRE RESET | "
            f"xtip={self.get_insertion_depth():.3f} | "
            f"rotation={self.get_rotation_degrees():.1f} deg"
        )

    # ============================================================
    # TERMINAL OUTPUT
    # ============================================================

    def print_state(
        self,
        translation,
        rotation
    ):

        print(
            "COMMAND | "
            f"translation={translation:.3f} | "
            f"rotation={math.degrees(rotation):.1f} deg | "
            f"xtip={self.get_insertion_depth():.3f} | "
            f"total rotation={self.get_rotation_degrees():.1f} deg"
        )

    # ============================================================
    # RATE-LIMITED QUEUE DRAIN
    #
    # Called once per physics step. Applies at most
    # max_translation_per_step / max_rotation_per_step of whatever
    # keyboard motion is pending, leaving the remainder queued for
    # the next step(s). See __init__ for why this exists.
    # ============================================================

    def onAnimateBeginEvent(
        self,
        event
    ):

        if (
            self._pending_translation == 0.0
            and self._pending_rotation == 0.0
        ):
            return

        step_translation = max(
            -self.max_translation_per_step,
            min(
                self.max_translation_per_step,
                self._pending_translation
            )
        )

        step_rotation = max(
            -self.max_rotation_per_step,
            min(
                self.max_rotation_per_step,
                self._pending_rotation
            )
        )

        self._pending_translation -= step_translation
        self._pending_rotation -= step_rotation

        self.apply_command(
            translation=step_translation,
            rotation=step_rotation
        )

    # ============================================================
    # TEMPORARY KEYBOARD INPUT
    #
    # Ctrl + Shift + D
    #     insert
    #
    # Ctrl + Shift + A
    #     retract
    #
    # Ctrl + Shift + E
    #     rotate positive
    #
    # Ctrl + Shift + Q
    #     rotate negative
    #
    # Keyboard control can be removed later when the physical
    # input device is integrated.
    #
    # Presses are queued (see onAnimateBeginEvent), not applied
    # instantly, so a burst of key-repeat events can't tunnel the
    # guidewire through the vessel wall in a single physics step.
    # ============================================================

    def onKeypressedEvent(
        self,
        event
    ):

        key = event["key"]

        if isinstance(
            key,
            int
        ):

            try:
                key = chr(key)

            except Exception:
                return

        key = str(
            key
        ).lower()

        # --------------------------------------------------------
        # INSERT
        # --------------------------------------------------------

        if key == "d":

            self._pending_translation += (
                self.translation_step
            )

        # --------------------------------------------------------
        # RETRACT
        # --------------------------------------------------------

        elif key == "a":

            self._pending_translation -= (
                self.translation_step
            )

        # --------------------------------------------------------
        # ROTATE POSITIVE
        # --------------------------------------------------------

        elif key == "e":

            self._pending_rotation += (
                self.rotation_step
            )

        # --------------------------------------------------------
        # ROTATE NEGATIVE
        # --------------------------------------------------------

        elif key == "q":

            self._pending_rotation -= (
                self.rotation_step
            )