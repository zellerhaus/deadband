"""Cowork Console firmware — the panel as a desk command surface.

A worked fork example. The panel drives a macOS workstation: media keys
go out natively over HID, everything else fires a Hyper chord that a
Hammerspoon config on the host turns into real work (launching apps,
toggling audio devices, kicking off Cowork tasks). The firmware owns the
hardware and the chords; the host owns the actions.

Two halves, one contract. The chord table lives in cowork_chords.py
(pure Python, no hardware) so the same 19 chords are unit-testable and
the Hammerspoon side can bind a matching set. This file imports that
table and wires it to the panel.

Control mapping:

    Encoder rotate CW         Volume up        (native ConsumerControl)
    Encoder rotate CCW        Volume down      (native ConsumerControl)
    Encoder click             Play / pause     (native ConsumerControl)
    Rotary (12 positions)     Arm launcher N   (Hyper + N, host dispatches)
    Toggle 1  ON / OFF        Do Not Disturb   (Hyper + U / I)
    Toggle 2  ON / OFF        Audio output     (Hyper + O / P)
    Paddle    ON / OFF        Mic mute  ON=muted (Hyper + J / K)
    Button tap                Fire armed launcher (Hyper + Space)
    Button long-click (0.6s)  Lock screen      (native Cmd+Ctrl+Q)

Button LED:

    Idle                      Dim steady at 15%
    While pressed             Full on
    On release                Back to 15%
    On tap (dispatch)         Blink 5x fast — "sent"

The encoder is media and stays native: volume and transport never route
through Hammerspoon, so they work even with the host config unloaded.
The lock combo is native too — a panic key that needs no host software.

Required: adafruit_hid in /CIRCUITPY/lib/.  Install with circup:

    circup install adafruit_hid

Host-side setup: load host/hammerspoon/deadband/init.lua from your
~/.hammerspoon/init.lua. See that bundle's README for the full wiring.

Drop on the device as code.py.
"""

try:
    import usb_hid
    from adafruit_hid.keyboard import Keyboard
    from adafruit_hid.keycode import Keycode
    from adafruit_hid.consumer_control import ConsumerControl
    from adafruit_hid.consumer_control_code import ConsumerControlCode
except ImportError as e:
    raise ImportError(
        "adafruit_hid is required. Install with: circup install adafruit_hid"
    ) from e

import supervisor

from deadband import Deadband

import cowork_chords


db = Deadband()

kbd = Keyboard(usb_hid.devices)
cc = ConsumerControl(usb_hid.devices)


# -- chord sender -------------------------------------------------------

# cowork_chords stores chords as keycode NAME STRINGS so it stays free of
# hardware imports. Resolve those names to adafruit_hid Keycode values
# once, here, where the library is available.
def _resolve(chord_names):
    return tuple(getattr(Keycode, name) for name in chord_names)


def send_chord(chord_names):
    """Send a keycode-name tuple as a single chord (all keys held)."""
    kbd.send(*_resolve(chord_names))


IDLE_BRIGHTNESS = 0.15


# -- phantom-press guard -----------------------------------------------

# On this prototype, flipping a toggle couples into the button's GPIO and
# registers a phantom press — which the gesture engine can resolve into a
# long-click (lock) or click (dispatch) the user never made. A real button
# press is never within a few hundred ms of a toggle edge, so we ignore any
# press that begins inside that window. (The proper fix is hardware: isolate
# / pull up the button line. This guard masks it.)
TOGGLE_GUARD_MS = 300

_TICKS_PERIOD = 1 << 29
_TICKS_HALF = _TICKS_PERIOD // 2

_last_state_change_ms = supervisor.ticks_ms()
_press_phantom = False


def _ticks_since(then_ms):
    # Wrap-safe elapsed ms using supervisor.ticks_ms (wraps at 2**29).
    diff = (supervisor.ticks_ms() - then_ms) & (_TICKS_PERIOD - 1)
    if diff >= _TICKS_HALF:
        diff -= _TICKS_PERIOD
    return diff


# -- encoder: native media, never via Hammerspoon ----------------------

db.encoder.on_clockwise(lambda: cc.send(ConsumerControlCode.VOLUME_INCREMENT))
db.encoder.on_counterclockwise(lambda: cc.send(ConsumerControlCode.VOLUME_DECREMENT))
db.encoder.on_click(lambda: cc.send(ConsumerControlCode.PLAY_PAUSE))

db.encoder.on_clockwise(lambda: print("MEDIA: volume up"))
db.encoder.on_counterclockwise(lambda: print("MEDIA: volume down"))
db.encoder.on_click(lambda: print("MEDIA: play/pause"))


# -- toggles + paddle: state chords ------------------------------------

# toggle_1 = Do Not Disturb. toggle_2 = audio output device switch.
# paddle = mic mute, where ON means muted. Each edge sends its own chord
# so the host tracks the exact position, not just a flip.
def _wire_state(control_name, control):
    def emit(is_on):
        global _last_state_change_ms, _press_phantom
        _last_state_change_ms = supervisor.ticks_ms()
        # If the button reads as held the instant a toggle flips, that press is
        # coupling from the flip, not a real one. Mark it so its gesture is
        # ignored. (Covers the case where the button event is seen first too,
        # via the recency check in _on_button_press.)
        if db.button.is_pressed:
            _press_phantom = True
        send_chord(cowork_chords.toggle_chord(control_name, is_on))
        edge = "ON" if is_on else "OFF"
        key = cowork_chords.TOGGLE_CHORDS[control_name]["on" if is_on else "off"]
        print("STATE: {} {} -> Hyper+{}".format(control_name, edge, key))

    control.on_change(emit)


_wire_state("toggle_1", db.toggle_1)
_wire_state("toggle_2", db.toggle_2)
_wire_state("paddle", db.paddle)


# -- rotary: arm launcher N --------------------------------------------

# Each position sends its Hyper chord. The host arms that launcher and
# waits for the button tap to fire it.
def select_launcher(position):
    send_chord(cowork_chords.rotary_chord(position))
    print("ROTARY: position {} -> Hyper+{}".format(
        position, cowork_chords.ROTARY_CHORDS[position]
    ))


db.rotary.on_change(select_launcher)


# -- button: dispatch (tap) and lock (long-click) ----------------------

# Idle is a dim glow. Pressing brings the LED full up for tactile
# feedback; releasing returns it to idle. A tap (on_click) fires the
# armed launcher and overrides the release glow with a 5-blink "sent"
# pulse — so the tap path must run AFTER on_release restores idle.
def _on_button_press():
    global _press_phantom
    # A press that lands within the guard window of a toggle edge is coupling,
    # not a real press. Flag it so its resolved gesture is suppressed.
    _press_phantom = _ticks_since(_last_state_change_ms) < TOGGLE_GUARD_MS
    db.button.led.on()


db.button.on_press(_on_button_press)
db.button.on_release(lambda: db.button.led.set_brightness(IDLE_BRIGHTNESS))


def dispatch():
    # Fire the armed rotary launcher on the host, then flash "sent".
    # This runs after on_release, so the blink supersedes the idle glow.
    global _press_phantom
    if _press_phantom:
        _press_phantom = False
        print("BUTTON: tap ignored (phantom press coupled from a toggle edge)")
        return
    send_chord(cowork_chords.button_tap_chord())
    db.button.led.blink(times=5, interval=0.06)
    print("BUTTON: tap -> Hyper+{} (dispatch)".format(cowork_chords.BUTTON_TAP))


def lock_screen():
    # Native macOS lock. Does not touch Hammerspoon.
    global _press_phantom
    if _press_phantom:
        _press_phantom = False
        print("BUTTON: long-click ignored (phantom press coupled from a toggle edge)")
        return
    send_chord(cowork_chords.LOCK_NATIVE)
    print("BUTTON: long-click -> {} (lock, native)".format(
        "+".join(cowork_chords.LOCK_NATIVE)
    ))


db.button.on_click(dispatch)
db.button.on_long_click(lock_screen, duration=0.6)


# -- boot ---------------------------------------------------------------

db.button.led.set_brightness(IDLE_BRIGHTNESS)

print()
print("=== Deadband Cowork Console ===")
print("Encoder = native media. Toggles/paddle/rotary/button = Hyper chords.")
print("Long-press the button to lock. Load the Hammerspoon config to dispatch.")
print()


db.run()
