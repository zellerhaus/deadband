"""Two-state switch — `toggle_1`, `toggle_2`.

`SwitchEngine` is the pure-Python state machine: takes raw observations,
applies debouncing, fires `on_change` / `on_turn_on` / `on_turn_off`
callbacks on confirmed transitions. Tested off-device.

`Switch` is the hardware wrapper. It holds a `digitalio.DigitalInOut`
configured as input with internal pull-up, polls in `tick()`, and
forwards every observation to the engine. On-device only.

The first observation seeds `is_on` without firing callbacks — initial
state is not a "change."
"""


class SwitchEngine:
    """Pure-Python state machine for a two-state switch.

    Time is injected via `now_fn` (a callable returning seconds as float).
    On device this is `lambda: supervisor.ticks_ms() / 1000`; in tests it
    is a fake clock.
    """

    DEFAULT_DEBOUNCE = 0.02  # seconds

    def __init__(self, now_fn, debounce=None):
        self._now = now_fn
        self._debounce = (
            self.DEFAULT_DEBOUNCE if debounce is None else debounce
        )

        self._is_on = None
        self._last_change_at = None

        self._on_change_cbs = []
        self._on_turn_on_cbs = []
        self._on_turn_off_cbs = []

    # -- registration -------------------------------------------------

    def on_change(self, fn):
        self._on_change_cbs.append(fn)

    def on_turn_on(self, fn):
        self._on_turn_on_cbs.append(fn)

    def on_turn_off(self, fn):
        self._on_turn_off_cbs.append(fn)

    # -- state --------------------------------------------------------

    @property
    def is_on(self):
        return bool(self._is_on)

    # -- event feed ---------------------------------------------------

    def process_state(self, raw_state):
        """Feed a raw observation. Applies debouncing and fires
        registered callbacks on confirmed transitions.
        """
        raw_state = bool(raw_state)

        # First observation seeds state without firing callbacks.
        if self._is_on is None:
            self._is_on = raw_state
            self._last_change_at = self._now()
            return

        if raw_state == self._is_on:
            return

        if self._debounce > 0 and self._last_change_at is not None:
            if (self._now() - self._last_change_at) < self._debounce:
                return

        self._is_on = raw_state
        self._last_change_at = self._now()

        for fn in self._on_change_cbs:
            fn(self._is_on)
        if self._is_on:
            for fn in self._on_turn_on_cbs:
                fn()
        else:
            for fn in self._on_turn_off_cbs:
                fn()


# ---------------------------------------------------------------------
# Hardware wrapper. Imports `digitalio` at module load; absence is fine
# off-device — the import error is caught and `Switch` raises a clearer
# message at construction time. Tests import only `SwitchEngine`.
# ---------------------------------------------------------------------

try:
    import digitalio
    _HAS_DIGITALIO = True
except ImportError:
    _HAS_DIGITALIO = False


class Switch:
    """Hardware-backed two-state switch on a single GPIO.

    Configures the pin as input with internal pull-up. Logical "on"
    corresponds to the pin reading LOW (switch closed to GND), matching
    the prototype's wiring convention.

    Call `tick()` from the main loop. On-device only.
    """

    def __init__(self, pin, now_fn=None, debounce=None):
        if not _HAS_DIGITALIO:
            raise RuntimeError(
                "Switch requires CircuitPython's `digitalio` module"
            )
        if now_fn is None:
            import supervisor
            now_fn = lambda: supervisor.ticks_ms() / 1000

        self._io = digitalio.DigitalInOut(pin)
        self._io.direction = digitalio.Direction.INPUT
        self._io.pull = digitalio.Pull.UP

        self._engine = SwitchEngine(now_fn, debounce=debounce)
        self._engine.process_state(not self._io.value)

    @property
    def is_on(self):
        return self._engine.is_on

    def on_change(self, fn):
        self._engine.on_change(fn)

    def on_turn_on(self, fn):
        self._engine.on_turn_on(fn)

    def on_turn_off(self, fn):
        self._engine.on_turn_off(fn)

    def tick(self):
        self._engine.process_state(not self._io.value)
