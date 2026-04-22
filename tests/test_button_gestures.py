"""Tests for deadband.button.ButtonGestureEngine.

Covers the full gesture matrix:
    - raw press / release
    - simple click (no multi-click handlers)
    - auto-delay disambiguation when multi-click handlers are present
    - double- and triple-click
    - on_click(immediate=True)
    - on_hold (during-press threshold)
    - on_long_click (on-release threshold)
    - hold / long_click inhibit click
    - state queries: is_pressed, press_duration
"""

from deadband.button import ButtonGestureEngine


def make(clock, **kwargs):
    return ButtonGestureEngine(clock.now, **kwargs)


# ---------------------------------------------------------------------------
# Raw events
# ---------------------------------------------------------------------------

def test_on_press_fires_on_press(clock, rec):
    g = make(clock)
    r = rec("press")
    g.on_press(r)
    g.process_press()
    assert r.count == 1


def test_on_release_fires_on_release(clock, rec):
    g = make(clock)
    r = rec("release")
    g.on_release(r)
    g.process_press()
    clock.advance(0.05)
    g.process_release()
    assert r.count == 1


def test_spurious_release_is_noop(clock, rec):
    g = make(clock)
    r_rel = rec("release")
    r_click = rec("click")
    g.on_release(r_rel)
    g.on_click(r_click)
    g.process_release()  # without a prior press
    assert r_rel.count == 0
    assert r_click.count == 0


# ---------------------------------------------------------------------------
# Simple click (no multi-click handlers)
# ---------------------------------------------------------------------------

def test_simple_click_fires_immediately_on_release(clock, rec):
    g = make(clock)
    r = rec("click")
    g.on_click(r)
    g.process_press()
    clock.advance(0.05)
    g.process_release()
    assert r.count == 1


def test_simple_click_fires_on_every_release(clock, rec):
    g = make(clock)
    r = rec("click")
    g.on_click(r)
    for _ in range(3):
        g.process_press()
        clock.advance(0.05)
        g.process_release()
        clock.advance(0.05)
    assert r.count == 3


# ---------------------------------------------------------------------------
# Multi-click disambiguation
# ---------------------------------------------------------------------------

def test_single_click_delays_when_double_click_registered(clock, rec):
    g = make(clock)
    r_click = rec("click")
    r_double = rec("double")
    g.on_click(r_click)
    g.on_double_click(r_double)

    g.process_press()
    clock.advance(0.05)
    g.process_release()

    # Window still open: nothing has fired.
    assert r_click.count == 0
    assert r_double.count == 0

    clock.advance(0.35)
    g.tick()

    assert r_click.count == 1
    assert r_double.count == 0


def test_double_click_fires_only_double(clock, rec):
    g = make(clock)
    r_click = rec("click")
    r_double = rec("double")
    g.on_click(r_click)
    g.on_double_click(r_double)

    # Two fast clicks within the window.
    g.process_press(); clock.advance(0.05); g.process_release()
    clock.advance(0.1)
    g.process_press(); clock.advance(0.05); g.process_release()

    # Window closes.
    clock.advance(0.35)
    g.tick()

    assert r_click.count == 0
    assert r_double.count == 1


def test_triple_click_fires_only_triple(clock, rec):
    g = make(clock)
    r_click = rec("click")
    r_double = rec("double")
    r_triple = rec("triple")
    g.on_click(r_click)
    g.on_double_click(r_double)
    g.on_triple_click(r_triple)

    for _ in range(3):
        g.process_press(); clock.advance(0.05); g.process_release()
        clock.advance(0.1)

    clock.advance(0.35)
    g.tick()

    assert r_click.count == 0
    assert r_double.count == 0
    assert r_triple.count == 1


def test_four_clicks_fire_nothing(clock, rec):
    g = make(clock)
    r_click = rec("click")
    r_double = rec("double")
    r_triple = rec("triple")
    g.on_click(r_click)
    g.on_double_click(r_double)
    g.on_triple_click(r_triple)

    for _ in range(4):
        g.process_press(); clock.advance(0.05); g.process_release()
        clock.advance(0.1)

    clock.advance(0.35)
    g.tick()

    assert r_click.count == 0
    assert r_double.count == 0
    assert r_triple.count == 0


def test_triple_handler_only_still_fires_on_three(clock, rec):
    """on_triple alone counts toward triple; on_click still delays."""
    g = make(clock)
    r_click = rec("click")
    r_triple = rec("triple")
    g.on_click(r_click)
    g.on_triple_click(r_triple)

    for _ in range(3):
        g.process_press(); clock.advance(0.05); g.process_release()
        clock.advance(0.1)
    clock.advance(0.35)
    g.tick()

    assert r_click.count == 0
    assert r_triple.count == 1


# ---------------------------------------------------------------------------
# immediate=True override
# ---------------------------------------------------------------------------

def test_immediate_click_fires_on_release_even_with_multi_click(clock, rec):
    g = make(clock)
    r_click = rec("click")
    r_double = rec("double")
    g.on_click(r_click, immediate=True)
    g.on_double_click(r_double)

    g.process_press(); clock.advance(0.05); g.process_release()
    assert r_click.count == 1
    assert r_double.count == 0

    clock.advance(0.35)
    g.tick()

    # immediate click doesn't also fire at window close.
    assert r_click.count == 1


def test_immediate_click_and_double_click_both_fire(clock, rec):
    g = make(clock)
    r_click = rec("click")
    r_double = rec("double")
    g.on_click(r_click, immediate=True)
    g.on_double_click(r_double)

    # Two fast clicks.
    g.process_press(); clock.advance(0.05); g.process_release()
    clock.advance(0.1)
    g.process_press(); clock.advance(0.05); g.process_release()
    clock.advance(0.35)
    g.tick()

    assert r_click.count == 2
    assert r_double.count == 1


def test_immediate_and_deferred_click_both_registered(clock, rec):
    g = make(clock)
    r_imm = rec("imm")
    r_norm = rec("norm")
    r_double = rec("double")
    g.on_click(r_imm, immediate=True)
    g.on_click(r_norm)
    g.on_double_click(r_double)

    g.process_press(); clock.advance(0.05); g.process_release()
    assert r_imm.count == 1
    assert r_norm.count == 0

    clock.advance(0.35)
    g.tick()
    assert r_imm.count == 1
    assert r_norm.count == 1
    assert r_double.count == 0


# ---------------------------------------------------------------------------
# Hold (during-press threshold)
# ---------------------------------------------------------------------------

def test_on_hold_fires_when_threshold_crossed_during_press(clock, rec):
    g = make(clock)
    r = rec("hold")
    g.on_hold(r, duration=1.0)

    g.process_press()
    clock.advance(0.5)
    g.tick()
    assert r.count == 0

    clock.advance(0.6)
    g.tick()
    assert r.count == 1


def test_on_hold_fires_exactly_once_per_press(clock, rec):
    g = make(clock)
    r = rec("hold")
    g.on_hold(r, duration=0.5)

    g.process_press()
    clock.advance(1.0)
    g.tick()
    g.tick()
    g.tick()
    assert r.count == 1


def test_multiple_hold_thresholds_fire_independently(clock, rec):
    g = make(clock)
    r_short = rec("short")
    r_long = rec("long")
    g.on_hold(r_short, duration=0.5)
    g.on_hold(r_long, duration=1.5)

    g.process_press()
    clock.advance(0.6); g.tick()
    assert r_short.count == 1
    assert r_long.count == 0

    clock.advance(1.0); g.tick()
    assert r_short.count == 1
    assert r_long.count == 1


def test_hold_inhibits_click(clock, rec):
    g = make(clock)
    r_hold = rec("hold")
    r_click = rec("click")
    g.on_hold(r_hold, duration=0.5)
    g.on_click(r_click)

    g.process_press()
    clock.advance(0.6); g.tick()   # hold fires
    g.process_release()

    # No click should fire — the hold already took effect.
    assert r_hold.count == 1
    assert r_click.count == 0


def test_short_press_does_not_inhibit_click_when_hold_registered(clock, rec):
    g = make(clock)
    r_hold = rec("hold")
    r_click = rec("click")
    g.on_hold(r_hold, duration=1.0)
    g.on_click(r_click)

    g.process_press()
    clock.advance(0.2); g.tick()   # well short of hold threshold
    g.process_release()

    assert r_hold.count == 0
    assert r_click.count == 1


# ---------------------------------------------------------------------------
# Long click (on-release threshold)
# ---------------------------------------------------------------------------

def test_long_click_fires_on_release_after_threshold(clock, rec):
    g = make(clock)
    r = rec("long")
    g.on_long_click(r, duration=1.0)

    g.process_press()
    clock.advance(1.5)
    g.process_release()

    assert r.count == 1


def test_long_click_inhibits_click(clock, rec):
    g = make(clock)
    r_click = rec("click")
    r_long = rec("long")
    g.on_click(r_click)
    g.on_long_click(r_long, duration=1.0)

    g.process_press()
    clock.advance(1.5)
    g.process_release()
    clock.advance(0.35)
    g.tick()

    assert r_click.count == 0
    assert r_long.count == 1


def test_short_press_still_clicks_with_long_click_registered(clock, rec):
    g = make(clock)
    r_click = rec("click")
    r_long = rec("long")
    g.on_click(r_click)
    g.on_long_click(r_long, duration=1.0)

    g.process_press()
    clock.advance(0.3)
    g.process_release()

    assert r_click.count == 1
    assert r_long.count == 0


# ---------------------------------------------------------------------------
# State queries
# ---------------------------------------------------------------------------

def test_is_pressed_reflects_state(clock):
    g = make(clock)
    assert g.is_pressed is False
    g.process_press()
    assert g.is_pressed is True
    clock.advance(0.1)
    g.process_release()
    assert g.is_pressed is False


def test_press_duration_zero_when_not_pressed(clock):
    g = make(clock)
    assert g.press_duration == 0.0
    g.process_press()
    clock.advance(0.3)
    g.process_release()
    assert g.press_duration == 0.0


def test_press_duration_grows_while_held(clock):
    g = make(clock)
    g.process_press()
    clock.advance(0.25)
    assert abs(g.press_duration - 0.25) < 1e-9
    clock.advance(0.5)
    assert abs(g.press_duration - 0.75) < 1e-9


# ---------------------------------------------------------------------------
# Window reset after firing
# ---------------------------------------------------------------------------

def test_window_resets_after_firing(clock, rec):
    """A click after a prior multi-click-window expiry starts fresh."""
    g = make(clock)
    r_click = rec("click")
    r_double = rec("double")
    g.on_click(r_click)
    g.on_double_click(r_double)

    # First: single click, window closes, fires.
    g.process_press(); clock.advance(0.05); g.process_release()
    clock.advance(0.35); g.tick()
    assert r_click.count == 1

    # Second: another single click well after the first.
    clock.advance(1.0)
    g.process_press(); clock.advance(0.05); g.process_release()
    clock.advance(0.35); g.tick()
    assert r_click.count == 2
    assert r_double.count == 0


# ---------------------------------------------------------------------------
# Ordering: release callbacks fire before interpreted events
# ---------------------------------------------------------------------------

def test_release_fires_before_click(clock):
    g = make(clock)
    sequence = []
    g.on_release(lambda: sequence.append("release"))
    g.on_click(lambda: sequence.append("click"))

    g.process_press()
    clock.advance(0.05)
    g.process_release()

    assert sequence == ["release", "click"]


def test_release_fires_before_long_click(clock):
    g = make(clock)
    sequence = []
    g.on_release(lambda: sequence.append("release"))
    g.on_long_click(lambda: sequence.append("long"), duration=0.5)

    g.process_press()
    clock.advance(0.6)
    g.process_release()

    assert sequence == ["release", "long"]
