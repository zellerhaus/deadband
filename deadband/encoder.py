"""Rotary encoder with push switch.

`RotationEngine` is the pure-Python state machine for rotation events.
Tested off-device.

`Encoder` is the hardware wrapper. It composes:

  - `rotaryio.IncrementalEncoder` for quadrature decoding (default
    divisor of 4 reports one count per detent on the prototype's part)
  - `digitalio.DigitalInOut` for the push contact
  - `SwitchEngine` for press debouncing
  - `ButtonGestureEngine` for click / double-click / hold / long-click
    gestures on the press
  - `RotationEngine` for rotation events, including `on_press_turn`
    which fires when rotation occurs while the encoder is pressed
"""

from .button import ButtonGestureEngine
from .switch import SwitchEngine


class RotationEngine:
    """Pure-Python state machine for encoder rotation.

    Driven by `process_position(raw_pos)` where `raw_pos` is the
    current absolute count from the underlying decoder. Each detent in
    the delta from the previous position fires the rotation callbacks
    in order.

    `is_pressed_fn`, when supplied, is invoked at the start of each
    delta to decide whether `on_press_turn` should fire. The press
    state is sampled once per delta, not per detent.
    """

    def __init__(self, is_pressed_fn=None):
        self._is_pressed_fn = is_pressed_fn

        self._position = None
        self._on_turn_cbs = []
        self._on_clockwise_cbs = []
        self._on_counterclockwise_cbs = []
        self._on_press_turn_cbs = []

    # -- registration -------------------------------------------------

    def on_turn(self, fn):
        self._on_turn_cbs.append(fn)

    def on_clockwise(self, fn):
        self._on_clockwise_cbs.append(fn)

    def on_counterclockwise(self, fn):
        self._on_counterclockwise_cbs.append(fn)

    def on_press_turn(self, fn):
        self._on_press_turn_cbs.append(fn)

    # -- state --------------------------------------------------------

    @property
    def position(self):
        """Current accumulated position. 0 before any reading."""
        return self._position if self._position is not None else 0

    # -- event feed ---------------------------------------------------

    def process_position(self, raw_pos):
        if self._position is None:
            self._position = raw_pos
            return

        if raw_pos == self._position:
            return

        delta = raw_pos - self._position
        self._position = raw_pos
        direction = 1 if delta > 0 else -1
        steps = abs(delta)

        pressed = (
            self._is_pressed_fn() if self._is_pressed_fn is not None else False
        )

        for _ in range(steps):
            for fn in self._on_turn_cbs:
                fn(direction)
            if direction > 0:
                for fn in self._on_clockwise_cbs:
                    fn()
            else:
                for fn in self._on_counterclockwise_cbs:
                    fn()
            if pressed:
                for fn in self._on_press_turn_cbs:
                    fn(direction)


# ---------------------------------------------------------------------
# Hardware wrapper. `rotaryio` and `digitalio` are import-guarded so
# the engine remains importable off-device for tests.
# ---------------------------------------------------------------------

try:
    import digitalio
    import rotaryio
    _HAS_HARDWARE = True
except ImportError:
    _HAS_HARDWARE = False


class Encoder:
    """Hardware-backed rotary encoder with push switch.

    Pin A and B drive `rotaryio.IncrementalEncoder` for rotation; the
    press pin is read directly with `digitalio` (active-low, pull-up).
    Press debouncing uses `SwitchEngine`; press gestures (click, hold,
    long-click, etc.) come from `ButtonGestureEngine`.

    Call `tick()` from the main loop. On-device only.
    """

    def __init__(self, pin_a, pin_b, pin_press, now_fn=None, debounce=None):
        if not _HAS_HARDWARE:
            raise RuntimeError(
                "Encoder requires CircuitPython's `rotaryio` and `digitalio`"
            )
        if now_fn is None:
            import supervisor
            now_fn = lambda: supervisor.ticks_ms() / 1000

        self._encoder = rotaryio.IncrementalEncoder(pin_a, pin_b)
        self._press_io = digitalio.DigitalInOut(pin_press)
        self._press_io.direction = digitalio.Direction.INPUT
        self._press_io.pull = digitalio.Pull.UP

        self._gesture = ButtonGestureEngine(now_fn)
        self._press_switch = SwitchEngine(now_fn, debounce=debounce)
        # Switch transitions drive the gesture engine.
        self._press_switch.on_turn_on(self._gesture.process_press)
        self._press_switch.on_turn_off(self._gesture.process_release)

        self._rotation = RotationEngine(
            is_pressed_fn=lambda: self._gesture.is_pressed
        )

        # Seed both engines so neither fires phantom events at boot.
        self._press_switch.process_state(not self._press_io.value)
        self._rotation.process_position(self._encoder.position)

    # -- state queries -------------------------------------------------

    @property
    def position(self):
        return self._rotation.position

    @property
    def is_pressed(self):
        return self._gesture.is_pressed

    @property
    def press_duration(self):
        return self._gesture.press_duration

    # -- rotation callbacks --------------------------------------------

    def on_turn(self, fn):
        self._rotation.on_turn(fn)

    def on_clockwise(self, fn):
        self._rotation.on_clockwise(fn)

    def on_counterclockwise(self, fn):
        self._rotation.on_counterclockwise(fn)

    def on_press_turn(self, fn):
        self._rotation.on_press_turn(fn)

    # -- press callbacks (passthrough to ButtonGestureEngine) ----------

    def on_press(self, fn):
        self._gesture.on_press(fn)

    def on_release(self, fn):
        self._gesture.on_release(fn)

    def on_click(self, fn, immediate=False):
        self._gesture.on_click(fn, immediate=immediate)

    def on_hold(self, fn, duration=None):
        self._gesture.on_hold(fn, duration=duration)

    def on_long_click(self, fn, duration=None):
        self._gesture.on_long_click(fn, duration=duration)

    def on_double_click(self, fn):
        self._gesture.on_double_click(fn)

    def on_triple_click(self, fn):
        self._gesture.on_triple_click(fn)

    # -- main-loop hook ------------------------------------------------

    def tick(self):
        self._press_switch.process_state(not self._press_io.value)
        self._gesture.tick()
        self._rotation.process_position(self._encoder.position)
