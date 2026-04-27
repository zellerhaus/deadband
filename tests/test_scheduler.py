"""Tests for deadband.timing.Scheduler."""

from deadband.timing import Scheduler


def make(clock):
    return Scheduler(clock.now)


# ---------------------------------------------------------------------
# after()
# ---------------------------------------------------------------------

def test_after_fires_at_delay(clock, rec):
    s = make(clock)
    r = rec()
    s.after(1.0, r)

    s.tick()
    assert r.count == 0

    clock.advance(0.5)
    s.tick()
    assert r.count == 0

    clock.advance(0.5)
    s.tick()
    assert r.count == 1


def test_after_fires_only_once(clock, rec):
    s = make(clock)
    r = rec()
    s.after(0.5, r)

    clock.advance(2.0)
    for _ in range(5):
        s.tick()

    assert r.count == 1


def test_after_zero_fires_on_next_tick(clock, rec):
    s = make(clock)
    r = rec()
    s.after(0, r)
    s.tick()
    assert r.count == 1


def test_after_negative_delay_fires_immediately(clock, rec):
    """Implementation detail: a fire_at in the past fires next tick."""
    s = make(clock)
    r = rec()
    s.after(-1.0, r)
    s.tick()
    assert r.count == 1


# ---------------------------------------------------------------------
# every() / on_tick()
# ---------------------------------------------------------------------

def test_every_fires_repeatedly(clock, rec):
    s = make(clock)
    r = rec()
    s.every(1.0, r)

    for _ in range(5):
        clock.advance(1.0)
        s.tick()

    assert r.count == 5


def test_every_first_fire_is_after_interval(clock, rec):
    s = make(clock)
    r = rec()
    s.every(1.0, r)

    s.tick()
    assert r.count == 0

    clock.advance(0.999)
    s.tick()
    assert r.count == 0

    clock.advance(0.001)
    s.tick()
    assert r.count == 1


def test_on_tick_is_alias_for_every(clock, rec):
    s = make(clock)
    r = rec()
    s.on_tick(r, interval=0.5)

    clock.advance(0.5); s.tick()
    clock.advance(0.5); s.tick()

    assert r.count == 2


def test_on_tick_default_interval(clock, rec):
    s = make(clock)
    r = rec()
    s.on_tick(r)

    clock.advance(0.1)
    s.tick()
    assert r.count == 1


# ---------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------

def test_cancel_before_firing(clock, rec):
    s = make(clock)
    r = rec()
    timer = s.after(1.0, r)
    timer.cancel()

    clock.advance(2.0)
    s.tick()

    assert r.count == 0
    assert not timer.is_active


def test_cancel_after_firing_is_noop(clock, rec):
    s = make(clock)
    r = rec()
    timer = s.after(0.5, r)

    clock.advance(1.0); s.tick()
    assert r.count == 1
    assert not timer.is_active

    timer.cancel()
    assert not timer.is_active

    clock.advance(1.0); s.tick()
    assert r.count == 1


def test_cancel_repeating_stops_future_fires(clock, rec):
    s = make(clock)
    r = rec()
    timer = s.every(1.0, r)

    clock.advance(1.0); s.tick()
    assert r.count == 1

    timer.cancel()

    clock.advance(5.0); s.tick()
    assert r.count == 1
    assert not timer.is_active


def test_cancel_during_own_callback(clock):
    s = make(clock)
    fired = []
    timer_holder = []

    def cb():
        fired.append(1)
        if len(fired) == 1:
            timer_holder[0].cancel()

    timer_holder.append(s.every(1.0, cb))

    clock.advance(1.0); s.tick()
    assert len(fired) == 1

    clock.advance(1.0); s.tick()
    assert len(fired) == 1
    assert not timer_holder[0].is_active


def test_one_callback_can_cancel_another(clock, rec):
    s = make(clock)
    r2 = rec()
    timers = {}

    def cb1():
        timers["t2"].cancel()

    timers["t1"] = s.after(0.5, cb1)
    timers["t2"] = s.after(0.5, r2)

    clock.advance(1.0); s.tick()

    # t1 fires first (registered first), cancels t2 before t2 fires.
    assert r2.count == 0


# ---------------------------------------------------------------------
# is_active
# ---------------------------------------------------------------------

def test_is_active_after_creation(clock):
    s = make(clock)
    timer = s.after(1.0, lambda: None)
    assert timer.is_active


def test_is_active_after_cancel(clock):
    s = make(clock)
    timer = s.after(1.0, lambda: None)
    timer.cancel()
    assert not timer.is_active


def test_is_active_after_one_shot_fires(clock):
    s = make(clock)
    timer = s.after(0.5, lambda: None)
    clock.advance(1.0); s.tick()
    assert not timer.is_active


def test_is_active_repeating_stays_active(clock):
    s = make(clock)
    timer = s.every(1.0, lambda: None)

    clock.advance(1.0); s.tick()
    assert timer.is_active

    clock.advance(5.0); s.tick()
    assert timer.is_active


# ---------------------------------------------------------------------
# Multiple timers, ordering
# ---------------------------------------------------------------------

def test_multiple_one_shots_fire_in_registration_order(clock):
    s = make(clock)
    sequence = []
    s.after(1.0, lambda: sequence.append("a"))
    s.after(1.0, lambda: sequence.append("b"))
    s.after(1.0, lambda: sequence.append("c"))

    clock.advance(1.0); s.tick()

    assert sequence == ["a", "b", "c"]


def test_after_fires_before_due_repeating_when_registered_first(clock):
    s = make(clock)
    sequence = []
    s.after(0.5, lambda: sequence.append("after"))
    s.every(0.5, lambda: sequence.append("every"))

    clock.advance(0.5); s.tick()

    assert sequence == ["after", "every"]


def test_cancelled_timer_does_not_block_others(clock, rec):
    s = make(clock)
    r1 = rec()
    r2 = rec()

    t1 = s.after(1.0, r1)
    s.after(1.0, r2)
    t1.cancel()

    clock.advance(1.0); s.tick()

    assert r1.count == 0
    assert r2.count == 1


# ---------------------------------------------------------------------
# Adding timers in callbacks
# ---------------------------------------------------------------------

def test_callback_can_add_new_timer(clock, rec):
    s = make(clock)
    r1 = rec()
    r2 = rec()

    def first():
        r1()
        s.after(0.5, r2)

    s.after(0.5, first)

    clock.advance(0.5); s.tick()
    assert r1.count == 1
    assert r2.count == 0  # newly scheduled, not yet due

    clock.advance(0.5); s.tick()
    assert r2.count == 1


def test_callback_added_with_zero_delay_does_not_fire_in_same_tick(clock, rec):
    """Timers scheduled mid-tick are processed on the NEXT tick at earliest,
    even if their fire_at is already due."""
    s = make(clock)
    r1 = rec()
    r2 = rec()

    def first():
        r1()
        s.after(0, r2)

    s.after(0.5, first)

    clock.advance(0.5); s.tick()
    assert r1.count == 1
    assert r2.count == 0  # newly scheduled, even with delay=0, deferred

    s.tick()
    assert r2.count == 1


# ---------------------------------------------------------------------
# Drift compensation
# ---------------------------------------------------------------------

def test_repeating_timer_skips_missed_fires(clock, rec):
    """If we tick way late, the timer fires once (not 5 times) and
    rescheduled past now."""
    s = make(clock)
    r = rec()
    s.every(1.0, r)

    clock.advance(5.0); s.tick()
    assert r.count == 1

    # Next fire should be at t=6 (next interval boundary past t=5)
    clock.advance(1.0); s.tick()
    assert r.count == 2


def test_repeating_timer_keeps_phase_after_drift(clock, rec):
    """After drift, fires should be on integer intervals from origin,
    not from the late tick."""
    s = make(clock)
    r = rec()
    s.every(1.0, r)

    # Skip to t=2.5: only 2 fires worth has passed but we tick once.
    clock.advance(2.5); s.tick()
    assert r.count == 1

    # Phase: original schedule was 1, 2, 3, 4...
    # We're at 2.5, just fired. Next fire should be at t=3.0.
    clock.advance(0.5); s.tick()
    assert r.count == 2
