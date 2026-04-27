"""Deadband — CircuitPython library for the Deadband control surface.

The `Deadband` class is the public assembly point. Instantiating it
constructs every hardware component, wires LEDs into the illuminated
controls, and prepares an `EventLoop` + `Scheduler`. Call `db.run()`
to enter the blocking main loop, or `db.tick()` if you want to drive
your own loop.

Component access:

    db.toggle_1, db.toggle_2          - non-illuminated SPST toggles
    db.paddle                         - illuminated rocker (.led)
    db.button                         - illuminated momentary (.led)
    db.encoder                        - rotary encoder + push
    db.rotary                         - 12-position selector

Scheduler passthrough:

    db.after(delay, fn)               - one-shot timer
    db.every(interval, fn)            - repeating timer
    db.on_tick(fn, interval=0.1)      - alias for every

This module imports the hardware-facing modules. Pure-Python tests
should import the engines directly (e.g. `from deadband.button import
ButtonGestureEngine`) and avoid touching `Deadband` itself, which
needs CircuitPython's `board`, `digitalio`, `pwmio`, etc.
"""

__version__ = "0.0.1"


def _make_default_now_fn():
    import supervisor
    return lambda: supervisor.ticks_ms() / 1000


class Deadband:
    """The full panel assembly."""

    def __init__(self, now_fn=None, tick_sleep=None):
        from . import hardware
        from .switch import Switch
        from .illuminated import IlluminatedSwitch
        from .button import Button
        from .encoder import Encoder
        from .rotary import Rotary
        from .led import LED
        from .timing import Scheduler
        from .eventloop import EventLoop

        if now_fn is None:
            now_fn = _make_default_now_fn()
        self._now = now_fn

        # Inputs.
        self.toggle_1 = Switch(hardware.TOGGLE_1, now_fn=now_fn)
        self.toggle_2 = Switch(hardware.TOGGLE_2, now_fn=now_fn)
        self.paddle = IlluminatedSwitch(hardware.PADDLE, now_fn=now_fn)
        self.button = Button(hardware.BUTTON, now_fn=now_fn)
        self.encoder = Encoder(
            hardware.ENCODER_A,
            hardware.ENCODER_B,
            hardware.ENCODER_PRESS,
            now_fn=now_fn,
        )
        self.rotary = Rotary(hardware.ROTARY)

        # LEDs - attached after construction. Until the MOSFET driver
        # stage is wired, the PWM signal is electrically present but
        # no visible LED responds.
        self.paddle.led = LED(hardware.PADDLE_LED, now_fn=now_fn)
        self.button.led = LED(hardware.BUTTON_LED, now_fn=now_fn)

        # Scheduler and main loop.
        self._scheduler = Scheduler(now_fn)
        self._loop = EventLoop(self._scheduler, tick_sleep=tick_sleep)
        for component in (
            self.toggle_1, self.toggle_2, self.paddle, self.button,
            self.encoder, self.rotary,
        ):
            self._loop.add(component)

    # -- scheduler passthrough ----------------------------------------

    def after(self, delay, fn):
        return self._scheduler.after(delay, fn)

    def every(self, interval, fn):
        return self._scheduler.every(interval, fn)

    def on_tick(self, fn, interval=None):
        return self._scheduler.on_tick(fn, interval=interval)

    # -- main loop ----------------------------------------------------

    def tick(self):
        """One pass over all components and the scheduler."""
        self._loop.tick()

    def run(self):
        """Block forever, ticking at the configured cadence."""
        self._loop.run()
