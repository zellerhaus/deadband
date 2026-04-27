"""Tests for deadband.encoder.RotationEngine.

The press-gesture half of the encoder reuses ButtonGestureEngine and is
already covered by tests/test_button_gestures.py.
"""

from deadband.encoder import RotationEngine


# ---------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------

def test_first_observation_seeds_without_firing(rec):
    g = RotationEngine()
    r_turn = rec()
    r_cw = rec()
    g.on_turn(r_turn)
    g.on_clockwise(r_cw)
    g.process_position(5)
    assert g.position == 5
    assert r_turn.count == 0
    assert r_cw.count == 0


def test_position_default_before_any_observation():
    g = RotationEngine()
    assert g.position == 0


def test_first_observation_can_be_negative():
    g = RotationEngine()
    g.process_position(-5)
    assert g.position == -5


# ---------------------------------------------------------------------
# Single detent
# ---------------------------------------------------------------------

def test_clockwise_one_step_fires_turn_and_cw():
    g = RotationEngine()
    sequence = []
    g.on_turn(lambda d: sequence.append(("turn", d)))
    g.on_clockwise(lambda: sequence.append("cw"))
    g.on_counterclockwise(lambda: sequence.append("ccw"))

    g.process_position(0)
    g.process_position(1)

    assert sequence == [("turn", 1), "cw"]


def test_counterclockwise_one_step_fires_turn_and_ccw():
    g = RotationEngine()
    sequence = []
    g.on_turn(lambda d: sequence.append(("turn", d)))
    g.on_clockwise(lambda: sequence.append("cw"))
    g.on_counterclockwise(lambda: sequence.append("ccw"))

    g.process_position(0)
    g.process_position(-1)

    assert sequence == [("turn", -1), "ccw"]


# ---------------------------------------------------------------------
# Multi-detent deltas
# ---------------------------------------------------------------------

def test_three_detent_clockwise_fires_three_times():
    g = RotationEngine()
    fired = []
    g.on_turn(lambda d: fired.append(d))
    g.process_position(0)
    g.process_position(3)
    assert fired == [1, 1, 1]


def test_three_detent_counterclockwise_fires_three_times():
    g = RotationEngine()
    fired = []
    g.on_turn(lambda d: fired.append(d))
    g.process_position(0)
    g.process_position(-3)
    assert fired == [-1, -1, -1]


def test_large_jump_fires_per_detent():
    g = RotationEngine()
    fired = []
    g.on_turn(lambda d: fired.append(d))
    g.process_position(0)
    g.process_position(20)
    assert len(fired) == 20
    assert all(d == 1 for d in fired)


# ---------------------------------------------------------------------
# No-ops
# ---------------------------------------------------------------------

def test_same_position_is_noop(rec):
    g = RotationEngine()
    r = rec()
    g.on_turn(r)
    g.process_position(5)
    g.process_position(5)
    g.process_position(5)
    assert r.count == 0


# ---------------------------------------------------------------------
# Position tracking
# ---------------------------------------------------------------------

def test_position_tracks_observations():
    g = RotationEngine()
    g.process_position(0)
    g.process_position(5)
    assert g.position == 5
    g.process_position(2)
    assert g.position == 2
    g.process_position(-3)
    assert g.position == -3


# ---------------------------------------------------------------------
# Press-turn (combined gesture)
# ---------------------------------------------------------------------

def test_on_press_turn_only_fires_when_pressed():
    pressed = [False]
    g = RotationEngine(is_pressed_fn=lambda: pressed[0])
    fired = []
    g.on_press_turn(lambda d: fired.append(d))

    g.process_position(0)

    g.process_position(1)
    assert fired == []

    pressed[0] = True
    g.process_position(2)
    assert fired == [1]

    pressed[0] = False
    g.process_position(3)
    assert fired == [1]


def test_on_press_turn_fires_per_detent_when_pressed():
    g = RotationEngine(is_pressed_fn=lambda: True)
    fired = []
    g.on_press_turn(lambda d: fired.append(d))

    g.process_position(0)
    g.process_position(3)

    assert fired == [1, 1, 1]


def test_on_turn_fires_regardless_of_press_state():
    pressed = [False]
    g = RotationEngine(is_pressed_fn=lambda: pressed[0])
    turn_fired = []
    press_turn_fired = []
    g.on_turn(lambda d: turn_fired.append(d))
    g.on_press_turn(lambda d: press_turn_fired.append(d))

    g.process_position(0)

    g.process_position(1)
    assert turn_fired == [1]
    assert press_turn_fired == []

    pressed[0] = True
    g.process_position(2)
    assert turn_fired == [1, 1]
    assert press_turn_fired == [1]


# ---------------------------------------------------------------------
# Multiple callbacks
# ---------------------------------------------------------------------

def test_multiple_turn_callbacks(rec):
    g = RotationEngine()
    r1 = rec()
    r2 = rec()
    g.on_turn(r1)
    g.on_turn(r2)
    g.process_position(0)
    g.process_position(1)
    assert r1.calls == [(1,)]
    assert r2.calls == [(1,)]


def test_clockwise_does_not_fire_for_ccw():
    g = RotationEngine()
    cw = []
    ccw = []
    g.on_clockwise(lambda: cw.append(1))
    g.on_counterclockwise(lambda: ccw.append(1))
    g.process_position(0)
    g.process_position(-2)
    assert cw == []
    assert len(ccw) == 2


def test_counterclockwise_does_not_fire_for_cw():
    g = RotationEngine()
    cw = []
    ccw = []
    g.on_clockwise(lambda: cw.append(1))
    g.on_counterclockwise(lambda: ccw.append(1))
    g.process_position(0)
    g.process_position(2)
    assert len(cw) == 2
    assert ccw == []


# ---------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------

def test_turn_fires_before_direction_callback():
    g = RotationEngine()
    sequence = []
    g.on_turn(lambda d: sequence.append("turn"))
    g.on_clockwise(lambda: sequence.append("cw"))

    g.process_position(0)
    g.process_position(1)

    assert sequence == ["turn", "cw"]
