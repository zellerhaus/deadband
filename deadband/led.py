"""LED with animation state machine.

`LEDAnimationEngine` is the pure-Python animation core. It tracks
current brightness (0.0-1.0) and an animation mode (`idle`, `pulse`,
`blink`). Each call to `tick()` advances the animation and updates
the engine's `brightness` property.

`LED` is the hardware wrapper. It composes an `LEDAnimationEngine`
with a `pwmio.PWMOut` and writes the engine's brightness to the PWM
duty cycle on every relevant call and on every `tick()`.

Per spec design decision #8: any of `pulse`, `blink`, `on`, `off`, or
`set_brightness` supersedes a running animation. `stop` halts the
animation and leaves brightness at its current value.

Pulse uses a cosine waveform: brightness = 0.5 * (1 - cos(2π·t/period)).
That gives a smooth fade up to 1.0 at the half-period and back to 0.0
at the period boundary — the "breathing" feel.

Blink interpretation: `blink(times=N, interval=I)` produces N on-pulses,
each of duration I, with off gaps of duration I between them. The LED
is left off when the animation completes.
"""

import math


class LEDAnimationEngine:
    """Pure-Python animation state machine for an LED.

    `now_fn` is a callable returning seconds. On device this is
    `lambda: supervisor.ticks_ms() / 1000`; in tests it is a fake clock.
    """

    def __init__(self, now_fn):
        self._now = now_fn
        self._mode = "idle"           # "idle" | "pulse" | "blink"
        self._brightness = 0.0

        # Pulse state
        self._pulse_period = None
        self._pulse_started_at = None

        # Blink state
        self._blink_interval = None
        self._blink_remaining = None
        self._blink_state = None      # bool: currently lit?
        self._blink_phase_start = None

    # -- state -------------------------------------------------------

    @property
    def brightness(self):
        return self._brightness

    # -- immediate-state methods (clear any animation) ---------------

    def on(self):
        self._mode = "idle"
        self._brightness = 1.0

    def off(self):
        self._mode = "idle"
        self._brightness = 0.0

    def set_brightness(self, value):
        self._mode = "idle"
        if value < 0.0:
            value = 0.0
        elif value > 1.0:
            value = 1.0
        self._brightness = value

    # -- animations --------------------------------------------------

    def pulse(self, period=2.0):
        """Sinusoidal breathing. Resets brightness to 0 at start."""
        self._mode = "pulse"
        self._pulse_period = period
        self._pulse_started_at = self._now()
        self._brightness = 0.0

    def blink(self, times=3, interval=0.2):
        """Flash `times` on-pulses of duration `interval`, separated
        by `interval`-long off gaps. Ends with the LED off.
        """
        if times <= 0:
            return
        self._mode = "blink"
        self._blink_interval = interval
        self._blink_remaining = times
        self._blink_state = True
        self._blink_phase_start = self._now()
        self._brightness = 1.0

    def stop(self):
        """Halt the current animation. Brightness stays at its
        current instantaneous value.
        """
        self._mode = "idle"

    # -- main-loop hook ----------------------------------------------

    def tick(self):
        if self._mode == "pulse":
            self._tick_pulse()
        elif self._mode == "blink":
            self._tick_blink()

    # -- internals ---------------------------------------------------

    def _tick_pulse(self):
        elapsed = self._now() - self._pulse_started_at
        phase = (elapsed % self._pulse_period) / self._pulse_period
        self._brightness = 0.5 * (1.0 - math.cos(2.0 * math.pi * phase))

    def _tick_blink(self):
        elapsed = self._now() - self._blink_phase_start
        if elapsed < self._blink_interval:
            return

        # Phase boundary: toggle.
        self._blink_state = not self._blink_state
        self._brightness = 1.0 if self._blink_state else 0.0
        self._blink_phase_start = self._now()

        # An on -> off transition completes one blink.
        if not self._blink_state:
            self._blink_remaining -= 1
            if self._blink_remaining <= 0:
                self._mode = "idle"


# ---------------------------------------------------------------------
# Hardware wrapper. `pwmio` is import-guarded so the engine remains
# importable off-device for tests.
# ---------------------------------------------------------------------

try:
    import pwmio
    _HAS_PWMIO = True
except ImportError:
    _HAS_PWMIO = False


class LED:
    """Hardware-backed LED on a PWM-capable GPIO.

    Drives the gate of the panel's MOSFET driver via `pwmio.PWMOut`.
    The PWM signal is electrically present from the moment the
    constructor runs; whether a visible LED responds depends on the
    MOSFET stage being wired through.

    Brightness is mapped to 16-bit duty cycle (0-65535). PWM frequency
    defaults to 1 kHz, which is well above the human flicker threshold
    and well below the MOSFET's switching limits.

    Call `tick()` from the main loop. On-device only.
    """

    PWM_RESOLUTION = 65535
    DEFAULT_FREQUENCY = 1000

    def __init__(self, pin, now_fn=None, frequency=None):
        if not _HAS_PWMIO:
            raise RuntimeError("LED requires CircuitPython's `pwmio` module")
        if now_fn is None:
            import supervisor
            now_fn = lambda: supervisor.ticks_ms() / 1000
        if frequency is None:
            frequency = self.DEFAULT_FREQUENCY

        self._pwm = pwmio.PWMOut(pin, frequency=frequency, duty_cycle=0)
        self._engine = LEDAnimationEngine(now_fn)

    @property
    def brightness(self):
        return self._engine.brightness

    def on(self):
        self._engine.on()
        self._write()

    def off(self):
        self._engine.off()
        self._write()

    def set_brightness(self, value):
        self._engine.set_brightness(value)
        self._write()

    def pulse(self, period=2.0):
        self._engine.pulse(period=period)
        self._write()

    def blink(self, times=3, interval=0.2):
        self._engine.blink(times=times, interval=interval)
        self._write()

    def stop(self):
        self._engine.stop()

    def tick(self):
        self._engine.tick()
        self._write()

    def _write(self):
        self._pwm.duty_cycle = int(self._engine.brightness * self.PWM_RESOLUTION)
