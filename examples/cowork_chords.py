"""Cowork Console chord table — pure data, no hardware.

The single source of truth for the keyboard chords the Cowork Console
firmware sends to the host. Hammerspoon binds the exact same set; the
firmware sends them. Keep the two in lockstep or controls silently miss.

Every chord here is a "Hyper" chord: Command + Control + Option + Shift
held together with one key. macOS sees that four-modifier combination as
a dedicated namespace no application claims, so a Hyper binding never
collides with an app shortcut. There is no Keycode.HYPER on this
hardware — Hyper is assembled from its four modifiers at send time.

One chord is the exception: the button long-click sends a NATIVE macOS
lock (Command + Control + Q). It does not pass through Hammerspoon and is
not a Hyper chord. It lives here as data so the firmware imports one
table and tests can see the whole surface.

This module is deliberately importable with only the standard library —
no usb_hid, no adafruit_hid, no deadband. The firmware translates the
keycode NAME STRINGS below into adafruit_hid Keycode values; the strings
let this table stay testable on a plain Python interpreter.

Chord surface (19 Hyper chords + 1 native):

    Rotary 1..12          Hyper + 1 2 3 4 5 6 7 8 9 0 - =   (12 chords)
    toggle_1 ON  / OFF    Hyper + F13 / F14
    toggle_2 ON  / OFF    Hyper + F15 / F16
    paddle   ON  / OFF    Hyper + F17 / F18
    button tap            Hyper + SPACE
    button long-click     Command + Control + Q  (native lock, not Hyper)
"""

# -- Hyper -------------------------------------------------------------

# The four modifier keycode names that make up Hyper, in send order.
# The firmware maps each name to its adafruit_hid Keycode at runtime.
HYPER = ("GUI", "CONTROL", "ALT", "SHIFT")


# -- Rotary launcher chords --------------------------------------------

# Position 1..12 -> the keycode NAME the Hyper chord carries. Hammerspoon
# binds the printable form of each key ("1".."9", "0", "-", "="); the two
# lists are positional twins and must stay in the same order.
ROTARY_CHORDS = {
    1: "ONE",
    2: "TWO",
    3: "THREE",
    4: "FOUR",
    5: "FIVE",
    6: "SIX",
    7: "SEVEN",
    8: "EIGHT",
    9: "NINE",
    10: "ZERO",
    11: "MINUS",
    12: "EQUALS",
}


# -- Toggle / paddle state chords --------------------------------------

# Each control sends one chord on its ON edge and a different chord on
# its OFF edge, so the host always knows the exact state, never just that
# "something flipped".
TOGGLE_CHORDS = {
    "toggle_1": {"on": "F13", "off": "F14"},
    "toggle_2": {"on": "F15", "off": "F16"},
    "paddle": {"on": "F17", "off": "F18"},
}


# -- Button -------------------------------------------------------------

# Tap arms-and-fires the current rotary launcher on the host side.
BUTTON_TAP = "SPACE"

# Long-click locks the Mac. Native combo, sent directly — Hammerspoon
# never sees it. Stored as keycode names so the firmware translates it
# the same way it translates every other chord.
LOCK_NATIVE = ("GUI", "CONTROL", "Q")


# -- Helpers (used by firmware and tests) ------------------------------

def hyper_chord(key_name):
    """Return the full keycode-name tuple for Hyper + ``key_name``.

    e.g. ``hyper_chord("F13")`` -> ``("GUI", "CONTROL", "ALT", "SHIFT", "F13")``.
    """
    return HYPER + (key_name,)


def rotary_chord(position):
    """Hyper chord (keycode-name tuple) for a rotary position 1..12."""
    return hyper_chord(ROTARY_CHORDS[position])


def toggle_chord(control, is_on):
    """Hyper chord (keycode-name tuple) for a toggle/paddle edge.

    ``control`` is one of "toggle_1", "toggle_2", "paddle".
    """
    edge = "on" if is_on else "off"
    return hyper_chord(TOGGLE_CHORDS[control][edge])


def button_tap_chord():
    """Hyper chord (keycode-name tuple) for the button tap."""
    return hyper_chord(BUTTON_TAP)


def all_hyper_chords():
    """Every Hyper chord this console sends, as keycode-name tuples.

    The 12 rotary positions + 6 toggle/paddle edges + the button tap = 19.
    The native lock combo is intentionally excluded — it is not a Hyper
    chord and does not go through Hammerspoon.
    """
    chords = [rotary_chord(p) for p in sorted(ROTARY_CHORDS)]
    for control in ("toggle_1", "toggle_2", "paddle"):
        chords.append(toggle_chord(control, True))
        chords.append(toggle_chord(control, False))
    chords.append(button_tap_chord())
    return chords
