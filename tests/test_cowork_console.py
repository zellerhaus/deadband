"""Tests for examples/cowork_chords.py — the Cowork Console chord table.

The chord table is the contract between firmware (which SENDS chords) and
the Hammerspoon host config (which BINDS them). A duplicate or a gap is a
silently dead control, so these tests guard the surface:

    - all 12 rotary positions are present, no holes
    - every Hyper chord is unique (no two controls collide)
    - each toggle/paddle ON edge differs from its OFF edge
    - the chord count is exactly the documented 19
    - the native lock combo is NOT a Hyper chord and is not in the set

Only cowork_chords is imported. cowork_console.py needs usb_hid and
adafruit_hid (hardware-only libraries) and is never imported here.
"""

import os
import sys

import pytest

# cowork_chords lives in examples/, alongside the firmware that imports it.
EXAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples"
)
if EXAMPLES_DIR not in sys.path:
    sys.path.insert(0, EXAMPLES_DIR)

import cowork_chords  # noqa: E402


# ---------------------------------------------------------------------
# Rotary coverage
# ---------------------------------------------------------------------

def test_all_twelve_rotary_positions_present():
    assert sorted(cowork_chords.ROTARY_CHORDS) == list(range(1, 13))


def test_rotary_chord_keys_are_distinct():
    keys = list(cowork_chords.ROTARY_CHORDS.values())
    assert len(keys) == len(set(keys))


def test_rotary_chord_helper_carries_full_hyper():
    chord = cowork_chords.rotary_chord(1)
    assert chord == cowork_chords.HYPER + ("ONE",)


def test_rotary_chord_rejects_out_of_range():
    with pytest.raises(KeyError):
        cowork_chords.rotary_chord(13)


# ---------------------------------------------------------------------
# Toggle / paddle edges
# ---------------------------------------------------------------------

def test_every_toggle_on_off_pair_is_distinct():
    for control, edges in cowork_chords.TOGGLE_CHORDS.items():
        assert edges["on"] != edges["off"], control


def test_toggle_chord_helper_selects_edge():
    on = cowork_chords.toggle_chord("toggle_1", True)
    off = cowork_chords.toggle_chord("toggle_1", False)
    # Derive expected from the table so this stays correct if keys change.
    assert on == cowork_chords.HYPER + (cowork_chords.TOGGLE_CHORDS["toggle_1"]["on"],)
    assert off == cowork_chords.HYPER + (cowork_chords.TOGGLE_CHORDS["toggle_1"]["off"],)
    assert on != off


def test_three_state_controls_present():
    assert set(cowork_chords.TOGGLE_CHORDS) == {"toggle_1", "toggle_2", "paddle"}


# ---------------------------------------------------------------------
# Whole-surface uniqueness
# ---------------------------------------------------------------------

def test_chord_count_is_nineteen():
    # 12 rotary + 6 toggle/paddle edges + 1 button tap.
    assert len(cowork_chords.all_hyper_chords()) == 19


def test_all_hyper_chords_are_unique():
    chords = cowork_chords.all_hyper_chords()
    assert len(chords) == len(set(chords))


def test_no_rotary_chord_collides_with_a_toggle_chord():
    rotary_keys = set(cowork_chords.ROTARY_CHORDS.values())
    toggle_keys = set()
    for edges in cowork_chords.TOGGLE_CHORDS.values():
        toggle_keys.add(edges["on"])
        toggle_keys.add(edges["off"])
    assert rotary_keys.isdisjoint(toggle_keys)


def test_button_tap_does_not_collide_with_any_other_chord():
    tap = cowork_chords.button_tap_chord()
    others = [c for c in cowork_chords.all_hyper_chords() if c != tap]
    assert tap not in others


# ---------------------------------------------------------------------
# Hyper construction
# ---------------------------------------------------------------------

def test_hyper_is_four_modifiers():
    assert cowork_chords.HYPER == ("GUI", "CONTROL", "ALT", "SHIFT")


def test_every_hyper_chord_starts_with_hyper():
    for chord in cowork_chords.all_hyper_chords():
        assert chord[: len(cowork_chords.HYPER)] == cowork_chords.HYPER
        assert len(chord) == len(cowork_chords.HYPER) + 1


# ---------------------------------------------------------------------
# Native lock is separate
# ---------------------------------------------------------------------

def test_lock_native_is_cmd_ctrl_q():
    assert cowork_chords.LOCK_NATIVE == ("GUI", "CONTROL", "Q")


def test_lock_native_is_not_a_hyper_chord():
    # The lock must never be reachable through the Hyper namespace; it is
    # sent natively and Hammerspoon does not bind it.
    assert cowork_chords.LOCK_NATIVE not in cowork_chords.all_hyper_chords()
    assert cowork_chords.LOCK_NATIVE[: len(cowork_chords.HYPER)] != cowork_chords.HYPER
