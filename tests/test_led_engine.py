"""Tests for deadband.led.LEDAnimationEngine."""

from deadband.led import LEDAnimationEngine


def make(clock):
    return LEDAnimationEngine(clock.now)


# ---------------------------------------------------------------------
# Initial state and immediate-set methods
# ---------------------------------------------------------------------

def test_initial_brightness_is_zero(clock):
    e = make(clock)
    assert e.brightness == 0.0


def test_on_sets_full_brightness(clock):
    e = make(clock)
    e.on()
    assert e.brightness == 1.0


def test_off_sets_zero_brightness(clock):
    e = make(clock)
    e.on()
    e.off()
    assert e.brightness == 0.0


def test_set_brightness_mid_range(clock):
    e = make(clock)
    e.set_brightness(0.42)
    assert e.brightness == 0.42


def test_set_brightness_clamps_above_one(clock):
    e = make(clock)
    e.set_brightness(1.5)
    assert e.brightness == 1.0


def test_set_brightness_clamps_below_zero(clock):
    e = make(clock)
    e.set_brightness(-0.5)
    assert e.brightness == 0.0


# ---------------------------------------------------------------------
# Pulse
# ---------------------------------------------------------------------

def test_pulse_starts_at_zero_regardless_of_prior_brightness(clock):
    e = make(clock)
    e.set_brightness(0.7)
    e.pulse(period=2.0)
    assert e.brightness == 0.0


def test_pulse_peaks_at_half_period(clock):
    e = make(clock)
    e.pulse(period=2.0)
    clock.advance(1.0)
    e.tick()
    assert abs(e.brightness - 1.0) < 1e-6


def test_pulse_quarter_period_is_half(clock):
    e = make(clock)
    e.pulse(period=2.0)
    clock.advance(0.5)  # quarter period
    e.tick()
    # cos(pi/2) = 0, brightness = 0.5 * (1 - 0) = 0.5
    assert abs(e.brightness - 0.5) < 1e-6


def test_pulse_returns_to_zero_at_full_period(clock):
    e = make(clock)
    e.pulse(period=2.0)
    clock.advance(2.0)
    e.tick()
    assert abs(e.brightness - 0.0) < 1e-6


def test_pulse_repeats_indefinitely(clock):
    e = make(clock)
    e.pulse(period=2.0)
    # Mid-cycle peak, then peak again 2 seconds later, etc.
    clock.advance(1.0); e.tick()
    assert abs(e.brightness - 1.0) < 1e-6
    clock.advance(2.0); e.tick()
    assert abs(e.brightness - 1.0) < 1e-6
    clock.advance(2.0); e.tick()
    assert abs(e.brightness - 1.0) < 1e-6


def test_pulse_smooth_progression(clock):
    """Brightness should monotonically rise across the first quarter."""
    e = make(clock)
    e.pulse(period=4.0)
    samples = []
    for _ in range(10):
        clock.advance(0.1); e.tick()
        samples.append(e.brightness)
    for prev, curr in zip(samples, samples[1:]):
        assert curr > prev


# ---------------------------------------------------------------------
# Blink
# ---------------------------------------------------------------------

def test_blink_starts_on(clock):
    e = make(clock)
    e.blink(times=3, interval=0.2)
    assert e.brightness == 1.0


def test_blink_toggles_at_interval(clock):
    e = make(clock)
    e.blink(times=3, interval=0.2)

    clock.advance(0.1); e.tick()
    assert e.brightness == 1.0  # still on, mid-phase

    clock.advance(0.1); e.tick()
    assert e.brightness == 0.0  # toggled off at 0.2

    clock.advance(0.2); e.tick()
    assert e.brightness == 1.0  # toggled on at 0.4


def test_blink_completes_n_times_then_idles(clock):
    e = make(clock)
    e.blink(times=2, interval=0.1)

    # Pattern: on 0-0.1, off 0.1-0.2, on 0.2-0.3, off at 0.3+ (idle)
    clock.advance(0.1); e.tick()
    assert e.brightness == 0.0  # 1st blink complete
    clock.advance(0.1); e.tick()
    assert e.brightness == 1.0  # 2nd on phase
    clock.advance(0.1); e.tick()
    assert e.brightness == 0.0  # 2nd blink complete -> idle

    # No more changes, even after time passes
    clock.advance(5.0); e.tick()
    assert e.brightness == 0.0


def test_blink_zero_times_is_noop(clock):
    e = make(clock)
    e.set_brightness(0.42)
    e.blink(times=0)
    assert e.brightness == 0.42  # untouched


def test_blink_one_time(clock):
    e = make(clock)
    e.blink(times=1, interval=0.1)
    assert e.brightness == 1.0
    clock.advance(0.1); e.tick()
    assert e.brightness == 0.0  # 1st (only) blink complete -> idle
    clock.advance(5.0); e.tick()
    assert e.brightness == 0.0


# ---------------------------------------------------------------------
# Stop
# ---------------------------------------------------------------------

def test_stop_freezes_pulse_brightness(clock):
    e = make(clock)
    e.pulse(period=2.0)
    clock.advance(0.5); e.tick()
    frozen = e.brightness
    e.stop()

    clock.advance(2.0); e.tick()
    assert e.brightness == frozen


def test_stop_freezes_blink_brightness(clock):
    e = make(clock)
    e.blink(times=10, interval=0.2)
    assert e.brightness == 1.0
    e.stop()

    # Subsequent ticks should not toggle further
    for _ in range(20):
        clock.advance(0.1); e.tick()
    assert e.brightness == 1.0


def test_stop_when_idle_is_noop(clock):
    e = make(clock)
    e.set_brightness(0.5)
    e.stop()
    assert e.brightness == 0.5


# ---------------------------------------------------------------------
# Supersession (design decision #8)
# ---------------------------------------------------------------------

def test_on_supersedes_pulse(clock):
    e = make(clock)
    e.pulse(period=2.0)
    clock.advance(0.5); e.tick()
    assert e.brightness != 1.0  # mid-pulse

    e.on()
    assert e.brightness == 1.0

    # Subsequent ticks should not pulse
    clock.advance(2.0); e.tick()
    assert e.brightness == 1.0


def test_off_supersedes_blink(clock):
    e = make(clock)
    e.blink(times=10, interval=0.2)
    e.off()
    assert e.brightness == 0.0

    for _ in range(10):
        clock.advance(0.2); e.tick()
    assert e.brightness == 0.0


def test_set_brightness_supersedes_pulse(clock):
    e = make(clock)
    e.pulse(period=2.0)
    clock.advance(0.5); e.tick()
    e.set_brightness(0.3)
    assert e.brightness == 0.3

    clock.advance(2.0); e.tick()
    assert e.brightness == 0.3


def test_pulse_supersedes_blink(clock):
    e = make(clock)
    e.blink(times=10, interval=0.2)
    e.pulse(period=2.0)
    assert e.brightness == 0.0  # pulse resets to zero

    clock.advance(1.0); e.tick()
    assert abs(e.brightness - 1.0) < 1e-6


def test_blink_supersedes_pulse(clock):
    e = make(clock)
    e.pulse(period=2.0)
    clock.advance(0.5); e.tick()
    e.blink(times=3, interval=0.2)
    assert e.brightness == 1.0


def test_blink_supersedes_blink(clock):
    """A second blink call resets the count and phase."""
    # Using interval=0.25 (binary-exact in IEEE 754) so cumulative
    # clock advances don't drift below the interval threshold and
    # silently skip toggles.
    e = make(clock)
    e.blink(times=10, interval=0.25)
    clock.advance(0.25); e.tick()
    assert e.brightness == 0.0

    # Restart with new params.
    e.blink(times=2, interval=0.25)
    assert e.brightness == 1.0

    clock.advance(0.25); e.tick()
    assert e.brightness == 0.0
    clock.advance(0.25); e.tick()
    assert e.brightness == 1.0
    clock.advance(0.25); e.tick()
    assert e.brightness == 0.0  # 2nd blink complete -> idle
    # Done - no more transitions
    clock.advance(5.0); e.tick()
    assert e.brightness == 0.0


# ---------------------------------------------------------------------
# Tick is a no-op in idle mode
# ---------------------------------------------------------------------

def test_tick_in_idle_mode_does_nothing(clock):
    e = make(clock)
    e.set_brightness(0.4)
    for _ in range(10):
        clock.advance(0.5); e.tick()
    assert e.brightness == 0.4
