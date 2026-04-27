"""Tests for deadband.rotary.RotaryEngine.

Uses synthetic thresholds at 1000-count intervals for clarity. The
calibrated production thresholds (in deadband.hardware) live on-device
only and are not exercised here — the engine is threshold-agnostic.
"""

import pytest

from deadband.rotary import RotaryEngine


# 11 boundaries for 12 positions, evenly spaced.
THRESHOLDS = (1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000,
              9000, 10000, 11000)
HYSTERESIS = 100


def make(hysteresis=HYSTERESIS):
    return RotaryEngine(THRESHOLDS, hysteresis=hysteresis)


# ---------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected_pos", [
    (0,     1),
    (500,   1),
    (1500,  2),
    (2500,  3),
    (3500,  4),
    (4500,  5),
    (5500,  6),
    (6500,  7),
    (7500,  8),
    (8500,  9),
    (9500,  10),
    (10500, 11),
    (11500, 12),
    (65535, 12),
])
def test_classification_at_each_position(raw, expected_pos):
    g = make()
    g.process_reading(raw)
    assert g.position == expected_pos


# ---------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------

def test_initial_reading_seeds_without_firing(rec):
    g = make()
    r = rec()
    g.on_change(r)
    g.process_reading(2500)
    assert g.position == 3
    assert r.count == 0


def test_position_default_before_first_reading():
    g = make()
    assert g.position == 1


# ---------------------------------------------------------------------
# Same-position no-ops
# ---------------------------------------------------------------------

def test_same_position_is_noop(rec):
    g = make()
    g.process_reading(2500)
    r = rec()
    g.on_change(r)
    g.process_reading(2700)
    g.process_reading(2300)
    g.process_reading(2900)
    assert g.position == 3
    assert r.count == 0


# ---------------------------------------------------------------------
# Position changes
# ---------------------------------------------------------------------

def test_move_up_one_position(rec):
    g = make()
    g.process_reading(2500)
    r = rec()
    g.on_change(r)
    # threshold[2]=3000 + hysteresis(100) = need raw > 3100
    g.process_reading(3200)
    assert g.position == 4
    assert r.calls == [(4,)]


def test_move_down_one_position(rec):
    g = make()
    g.process_reading(5500)
    r = rec()
    g.on_change(r)
    # threshold[4]=5000 - hysteresis(100) = need raw < 4900
    g.process_reading(4800)
    assert g.position == 5
    assert r.calls == [(5,)]


def test_jump_multiple_positions_up(rec):
    g = make()
    g.process_reading(1500)
    r = rec()
    g.on_change(r)
    g.process_reading(8500)
    assert g.position == 9
    assert r.calls == [(9,)]


def test_jump_multiple_positions_down(rec):
    g = make()
    g.process_reading(10500)
    r = rec()
    g.on_change(r)
    g.process_reading(2500)
    assert g.position == 3
    assert r.calls == [(3,)]


# ---------------------------------------------------------------------
# Hysteresis
# ---------------------------------------------------------------------

def test_within_hysteresis_band_rejected_going_up(rec):
    g = make()
    g.process_reading(2500)
    r = rec()
    g.on_change(r)
    # threshold[2]=3000, hysteresis=100. 3050 is past threshold but in
    # the deadband — must stay at position 3.
    g.process_reading(3050)
    assert g.position == 3
    assert r.count == 0


def test_within_hysteresis_band_rejected_going_down(rec):
    g = make()
    g.process_reading(5500)
    r = rec()
    g.on_change(r)
    # threshold[4]=5000, hysteresis=100. 4950 is below threshold but in
    # the deadband — must stay at position 6.
    g.process_reading(4950)
    assert g.position == 6
    assert r.count == 0


def test_oscillation_in_deadband_does_not_fire(rec):
    g = make()
    g.process_reading(2500)
    r = rec()
    g.on_change(r)
    # Hover around the threshold[2]=3000 boundary, never crossing by
    # more than the hysteresis margin in either direction.
    for raw in (2950, 3050, 2980, 3070, 3020, 2940):
        g.process_reading(raw)
    assert g.position == 3
    assert r.count == 0


def test_clean_crossing_after_hover(rec):
    g = make()
    g.process_reading(2500)
    r = rec()
    g.on_change(r)
    # Hover then commit fully past the boundary.
    g.process_reading(3050)
    g.process_reading(2980)
    g.process_reading(3200)  # past threshold[2] + hysteresis = 3100
    assert g.position == 4
    assert r.calls == [(4,)]


# ---------------------------------------------------------------------
# Multiple callbacks
# ---------------------------------------------------------------------

def test_multiple_callbacks_all_fire(rec):
    g = make()
    g.process_reading(1500)
    r1 = rec()
    r2 = rec()
    r3 = rec()
    g.on_change(r1)
    g.on_change(r2)
    g.on_change(r3)
    g.process_reading(3500)
    assert r1.calls == [(4,)]
    assert r2.calls == [(4,)]
    assert r3.calls == [(4,)]


# ---------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------

def test_too_few_thresholds_raises():
    with pytest.raises(ValueError):
        RotaryEngine((1000, 2000, 3000))


def test_too_many_thresholds_raises():
    with pytest.raises(ValueError):
        RotaryEngine(tuple(range(0, 12000, 1000)))  # 12 values


def test_thresholds_accepted_as_list():
    """Passing a list (not a tuple) should work — it's just iterable."""
    g = RotaryEngine(list(THRESHOLDS), hysteresis=HYSTERESIS)
    g.process_reading(5500)
    assert g.position == 6
