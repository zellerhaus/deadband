"""Tests for deadband.switch.SwitchEngine.

Covers:
    - initial state seeded without firing callbacks
    - off->on and on->off transitions fire the right callbacks
    - repeated identical observations are no-ops
    - debounce: bounces within the window are ignored
    - debounce: real transitions outside the window are accepted
    - debounce=0 disables the window
    - on_change receives the new boolean state
"""

from deadband.switch import SwitchEngine


def make(clock, **kwargs):
    return SwitchEngine(clock.now, **kwargs)


# ---------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------

def test_first_observation_does_not_fire_callbacks(clock, rec):
    g = make(clock)
    r_change = rec("change")
    r_on = rec("on")
    r_off = rec("off")
    g.on_change(r_change)
    g.on_turn_on(r_on)
    g.on_turn_off(r_off)

    g.process_state(True)

    assert g.is_on is True
    assert r_change.count == 0
    assert r_on.count == 0
    assert r_off.count == 0


def test_first_observation_off_seeds_off(clock):
    g = make(clock)
    g.process_state(False)
    assert g.is_on is False


def test_is_on_default_before_first_observation(clock):
    g = make(clock)
    # Before any observation, treat as falsy.
    assert g.is_on is False


# ---------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------

def test_off_to_on_fires_change_and_turn_on(clock, rec):
    g = make(clock)
    r_change = rec()
    r_on = rec()
    r_off = rec()
    g.on_change(r_change)
    g.on_turn_on(r_on)
    g.on_turn_off(r_off)

    g.process_state(False)
    clock.advance(1.0)
    g.process_state(True)

    assert g.is_on is True
    assert r_change.calls == [(True,)]
    assert r_on.count == 1
    assert r_off.count == 0


def test_on_to_off_fires_change_and_turn_off(clock, rec):
    g = make(clock)
    r_change = rec()
    r_on = rec()
    r_off = rec()
    g.on_change(r_change)
    g.on_turn_on(r_on)
    g.on_turn_off(r_off)

    g.process_state(True)
    clock.advance(1.0)
    g.process_state(False)

    assert g.is_on is False
    assert r_change.calls == [(False,)]
    assert r_on.count == 0
    assert r_off.count == 1


def test_repeated_state_is_noop(clock, rec):
    g = make(clock)
    r = rec()
    g.on_change(r)

    g.process_state(False)   # seed
    clock.advance(0.5)
    g.process_state(False)
    g.process_state(False)
    g.process_state(False)

    assert g.is_on is False
    assert r.count == 0


def test_multiple_callbacks_all_fire(clock, rec):
    g = make(clock)
    r1 = rec("first")
    r2 = rec("second")
    r3 = rec("third")
    g.on_change(r1)
    g.on_change(r2)
    g.on_change(r3)

    g.process_state(False)
    clock.advance(1.0)
    g.process_state(True)

    assert r1.calls == [(True,)]
    assert r2.calls == [(True,)]
    assert r3.calls == [(True,)]


# ---------------------------------------------------------------------
# Debounce
# ---------------------------------------------------------------------

def test_debounce_ignores_bounce_within_window(clock, rec):
    g = make(clock, debounce=0.02)
    r = rec()
    g.on_change(r)

    g.process_state(False)
    clock.advance(0.5)
    g.process_state(True)        # accepted
    assert r.calls == [(True,)]

    clock.advance(0.005)         # 5ms < 20ms window
    g.process_state(False)       # bounce — ignored
    assert g.is_on is True
    assert r.count == 1

    clock.advance(0.005)
    g.process_state(True)        # already True, no change anyway
    assert r.count == 1


def test_debounce_accepts_transition_after_window(clock, rec):
    g = make(clock, debounce=0.02)
    r = rec()
    g.on_change(r)

    g.process_state(False)
    clock.advance(0.5)
    g.process_state(True)        # accepted, change at t=0.5
    clock.advance(0.025)         # 25ms > 20ms window
    g.process_state(False)       # accepted

    assert g.is_on is False
    assert r.calls == [(True,), (False,)]


def test_debounce_zero_accepts_every_transition(clock, rec):
    g = make(clock, debounce=0)
    r = rec()
    g.on_change(r)

    g.process_state(False)
    clock.advance(0.001)
    g.process_state(True)
    clock.advance(0.001)
    g.process_state(False)
    clock.advance(0.001)
    g.process_state(True)

    assert r.calls == [(True,), (False,), (True,)]


def test_default_debounce_is_20ms(clock, rec):
    g = make(clock)  # default debounce
    r = rec()
    g.on_change(r)

    g.process_state(False)
    clock.advance(0.1)
    g.process_state(True)        # accepted
    clock.advance(0.015)         # 15ms < default 20ms
    g.process_state(False)       # ignored
    assert r.count == 1
    assert g.is_on is True


# ---------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------

def test_change_fires_before_turn_on(clock):
    g = make(clock)
    sequence = []
    g.on_change(lambda is_on: sequence.append(("change", is_on)))
    g.on_turn_on(lambda: sequence.append(("on",)))

    g.process_state(False)
    clock.advance(1.0)
    g.process_state(True)

    assert sequence == [("change", True), ("on",)]


def test_change_fires_before_turn_off(clock):
    g = make(clock)
    sequence = []
    g.on_change(lambda is_on: sequence.append(("change", is_on)))
    g.on_turn_off(lambda: sequence.append(("off",)))

    g.process_state(True)
    clock.advance(1.0)
    g.process_state(False)

    assert sequence == [("change", False), ("off",)]
