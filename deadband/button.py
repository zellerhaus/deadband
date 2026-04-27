"""Illuminated momentary pushbutton.

`ButtonGestureEngine` is the pure-Python, hardware-agnostic core of the
button and encoder-press gesture suites. It interprets raw press/release
edges as click / double-click / triple-click / hold / long-click events,
including the auto-delay disambiguation specified in design decision #1.

`Button` is the hardware wrapper. It composes `SwitchEngine` for press
debouncing and `ButtonGestureEngine` for the gesture suite. The `.led`
attribute is reserved for the LED implementation, which lands with
`led.py` once the panel's MOSFET driver stage is wired through.

Keeping the engine hardware-free means the entire gesture semantic —
the most subtle part of the API — is exercised off-device by pytest.
"""

from .switch import SwitchEngine


class ButtonGestureEngine:
    """Interprets press/release events as gestures.

    Time is injected via `now_fn` (a callable returning seconds as float).
    On device this is `lambda: supervisor.ticks_ms() / 1000`; in tests it
    is a fake clock under the test's control.
    """

    MULTI_CLICK_WINDOW = 0.5
    DEFAULT_HOLD_DURATION = 1.0

    def __init__(self, now_fn, multi_click_window=None):
        self._now = now_fn
        self._window = (
            self.MULTI_CLICK_WINDOW
            if multi_click_window is None
            else multi_click_window
        )

        self._press_cbs = []
        self._release_cbs = []
        self._click_cbs = []        # list of (fn, immediate)
        self._hold_cbs = []         # list of (fn, duration)
        self._long_click_cbs = []   # list of (fn, duration)
        self._double_click_cbs = []
        self._triple_click_cbs = []

        self._pressed = False
        self._press_start = None
        self._hold_fired = set()    # durations already fired in this press
        self._long_fired = False    # hold or long_click fired -> not a click

        self._click_count = 0
        self._click_window_deadline = None

    # -- registration -------------------------------------------------

    def on_press(self, fn):
        self._press_cbs.append(fn)

    def on_release(self, fn):
        self._release_cbs.append(fn)

    def on_click(self, fn, immediate=False):
        self._click_cbs.append((fn, bool(immediate)))

    def on_hold(self, fn, duration=None):
        self._hold_cbs.append(
            (fn, self.DEFAULT_HOLD_DURATION if duration is None else duration)
        )

    def on_long_click(self, fn, duration=None):
        self._long_click_cbs.append(
            (fn, self.DEFAULT_HOLD_DURATION if duration is None else duration)
        )

    def on_double_click(self, fn):
        self._double_click_cbs.append(fn)

    def on_triple_click(self, fn):
        self._triple_click_cbs.append(fn)

    # -- state --------------------------------------------------------

    @property
    def is_pressed(self):
        return self._pressed

    @property
    def press_duration(self):
        if not self._pressed:
            return 0.0
        return self._now() - self._press_start

    # -- event feed ---------------------------------------------------

    def process_press(self):
        self._pressed = True
        self._press_start = self._now()
        self._hold_fired = set()
        self._long_fired = False
        for fn in self._press_cbs:
            fn()

    def process_release(self):
        if not self._pressed:
            return
        now = self._now()
        duration = now - self._press_start
        self._pressed = False

        for fn in self._release_cbs:
            fn()

        for fn, d in self._long_click_cbs:
            if duration >= d:
                self._long_fired = True
                fn()

        if self._long_fired:
            # Hold or long-click fired: this press is not a click candidate.
            return

        # Click candidate. Accumulate for multi-click disambiguation.
        self._click_count += 1
        self._click_window_deadline = now + self._window

        for fn, immediate in self._click_cbs:
            if immediate:
                fn()

        if not self._has_multi_click():
            # No double/triple handlers -> no reason to wait.
            for fn, immediate in self._click_cbs:
                if not immediate:
                    fn()
            self._click_count = 0
            self._click_window_deadline = None

    def tick(self):
        now = self._now()

        if self._pressed:
            duration = now - self._press_start
            for fn, d in self._hold_cbs:
                if d not in self._hold_fired and duration >= d:
                    self._hold_fired.add(d)
                    self._long_fired = True
                    fn()

        if (
            self._click_window_deadline is not None
            and now >= self._click_window_deadline
        ):
            count = self._click_count
            self._click_count = 0
            self._click_window_deadline = None
            self._dispatch_accumulated(count)

    # -- internals ----------------------------------------------------

    def _has_multi_click(self):
        return bool(self._double_click_cbs) or bool(self._triple_click_cbs)

    def _dispatch_accumulated(self, count):
        if count == 1:
            for fn, immediate in self._click_cbs:
                if not immediate:
                    fn()
        elif count == 2:
            for fn in self._double_click_cbs:
                fn()
        elif count == 3:
            for fn in self._triple_click_cbs:
                fn()
        # count >= 4: over-clicked, no canonical interpretation.


# ---------------------------------------------------------------------
# Hardware wrapper. `digitalio` is import-guarded so this module stays
# importable off-device for the engine tests above.
# ---------------------------------------------------------------------

try:
    import digitalio
    _HAS_DIGITALIO = True
except ImportError:
    _HAS_DIGITALIO = False


class Button:
    """Hardware-backed momentary pushbutton with full gesture suite.

    Composes `SwitchEngine` for press debouncing and
    `ButtonGestureEngine` for click / double-click / triple-click /
    hold / long-click gestures. Press is active-low with internal
    pull-up.

    The `.led` attribute is reserved for the LED implementation. It is
    `None` until the MOSFET driver stage is wired through and `led.py`
    is composed in by the eventloop assembly. Callers should treat
    `if button.led is not None: button.led.blink()` as the conservative
    pattern until paddle/button LEDs are live.

    Call `tick()` from the main loop. On-device only.
    """

    def __init__(self, pin_press, now_fn=None, debounce=None):
        if not _HAS_DIGITALIO:
            raise RuntimeError(
                "Button requires CircuitPython's `digitalio` module"
            )
        if now_fn is None:
            import supervisor
            now_fn = lambda: supervisor.ticks_ms() / 1000

        self._press_io = digitalio.DigitalInOut(pin_press)
        self._press_io.direction = digitalio.Direction.INPUT
        self._press_io.pull = digitalio.Pull.UP

        self._gesture = ButtonGestureEngine(now_fn)
        self._press_switch = SwitchEngine(now_fn, debounce=debounce)
        self._press_switch.on_turn_on(self._gesture.process_press)
        self._press_switch.on_turn_off(self._gesture.process_release)
        self._press_switch.process_state(not self._press_io.value)

        self.led = None

    # -- state queries -------------------------------------------------

    @property
    def is_pressed(self):
        return self._gesture.is_pressed

    @property
    def press_duration(self):
        return self._gesture.press_duration

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
