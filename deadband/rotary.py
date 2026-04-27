"""12-position rotary switch on an ADC pin.

`RotaryEngine` is the pure-Python state machine. It takes raw ADC
readings, classifies them via configurable thresholds, applies
hysteresis around boundaries to prevent flicker, and fires
`on_change(position)` on confirmed transitions. Tested off-device.

`Rotary` is the hardware wrapper. It holds an `analogio.AnalogIn`,
polls in `tick()`, and forwards readings to the engine. On-device only.

Position is 1-indexed (1 through 12) per the spec.
"""


class RotaryEngine:
    """Pure-Python state machine for a 12-position rotary switch.

    Thresholds are 11 ascending boundary values defining the 12 positions:

        position 1:    raw < thresholds[0]
        position N:    thresholds[N-2] <= raw < thresholds[N-1]   (2 <= N <= 11)
        position 12:   raw >= thresholds[10]

    Hysteresis prevents flicker at boundaries: a move is only accepted
    when the reading has crossed the boundary by `hysteresis` counts.
    """

    DEFAULT_HYSTERESIS = 500

    def __init__(self, thresholds, hysteresis=None):
        thresholds = tuple(thresholds)
        if len(thresholds) != 11:
            raise ValueError(
                "thresholds must have 11 boundaries (positions 1-12)"
            )
        self._thresholds = thresholds
        self._hysteresis = (
            self.DEFAULT_HYSTERESIS if hysteresis is None else hysteresis
        )

        self._position = None
        self._on_change_cbs = []

    # -- registration -------------------------------------------------

    def on_change(self, fn):
        self._on_change_cbs.append(fn)

    # -- state --------------------------------------------------------

    @property
    def position(self):
        """Current position (1-12). Returns 1 before any reading."""
        return self._position if self._position is not None else 1

    # -- event feed ---------------------------------------------------

    def process_reading(self, raw):
        """Feed a raw ADC reading. Updates position and fires registered
        callbacks on confirmed transitions.
        """
        new_pos = self._classify(raw)

        # First reading seeds without firing callbacks.
        if self._position is None:
            self._position = new_pos
            return

        if new_pos == self._position:
            return

        if not self._past_boundary(raw, self._position, new_pos):
            return

        self._position = new_pos
        for fn in self._on_change_cbs:
            fn(new_pos)

    # -- internals ----------------------------------------------------

    def _classify(self, raw):
        for i, thr in enumerate(self._thresholds):
            if raw < thr:
                return i + 1
        return 12

    def _past_boundary(self, raw, from_pos, to_pos):
        if to_pos > from_pos:
            return raw > self._thresholds[from_pos - 1] + self._hysteresis
        else:
            return raw < self._thresholds[from_pos - 2] - self._hysteresis


# ---------------------------------------------------------------------
# Hardware wrapper. `analogio` is import-guarded so the engine remains
# importable off-device for tests.
# ---------------------------------------------------------------------

try:
    import analogio
    _HAS_ANALOGIO = True
except ImportError:
    _HAS_ANALOGIO = False


class Rotary:
    """Hardware-backed 12-position rotary switch on an ADC pin.

    Reads the panel's resistor-ladder voltage divider via `analogio`.
    Default thresholds and hysteresis come from `deadband.hardware`.
    Call `tick()` from the main loop. On-device only.
    """

    def __init__(self, pin, thresholds=None, hysteresis=None):
        if not _HAS_ANALOGIO:
            raise RuntimeError(
                "Rotary requires CircuitPython's `analogio` module"
            )
        if thresholds is None or hysteresis is None:
            from . import hardware
            if thresholds is None:
                thresholds = hardware.ROTARY_THRESHOLDS
            if hysteresis is None:
                hysteresis = hardware.ROTARY_HYSTERESIS

        self._adc = analogio.AnalogIn(pin)
        self._engine = RotaryEngine(thresholds, hysteresis=hysteresis)
        self._engine.process_reading(self._adc.value)

    @property
    def position(self):
        return self._engine.position

    def on_change(self, fn):
        self._engine.on_change(fn)

    def tick(self):
        self._engine.process_reading(self._adc.value)
