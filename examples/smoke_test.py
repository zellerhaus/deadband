"""Deadband full-panel smoke test.

Drop this on a freshly assembled unit as `code.py` to verify every
input. Each control prints a single event when actuated. The onboard
LED echoes the main button press.

This script reads pins directly with `digitalio` / `analogio` /
`rotaryio` rather than going through the `deadband` library — that is
intentional. The smoke test exists to validate that the hardware is
wired correctly, independent of the library being correct.
"""

import board
import digitalio
import rotaryio
import analogio
import time


onboard = digitalio.DigitalInOut(board.LED)
onboard.direction = digitalio.Direction.OUTPUT

DIGITAL_PINS = {
    "toggle_1":      board.GP6,
    "toggle_2":      board.GP5,
    "paddle":        board.GP16,
    "button":        board.GP4,
    "encoder_press": board.GP12,
}


def make_input(pin):
    io = digitalio.DigitalInOut(pin)
    io.direction = digitalio.Direction.INPUT
    io.pull = digitalio.Pull.UP
    return io


digital_inputs = {name: make_input(pin) for name, pin in DIGITAL_PINS.items()}

encoder = rotaryio.IncrementalEncoder(board.GP10, board.GP11)

rotary = analogio.AnalogIn(board.GP26)


# Calibrated against the prototype's resistor ladder on 2026-04-22.
ROTARY_THRESHOLDS = [1536, 4640, 7793, 10946, 14083, 17175,
                     20272, 23415, 26535, 29622, 32747]
ROTARY_HYSTERESIS = 500


def rotary_position(raw):
    for i, threshold in enumerate(ROTARY_THRESHOLDS):
        if raw < threshold:
            return i + 1
    return 12


print("Deadband full-panel smoke test")
print("Exercise every control. Each event prints once.")
print()

last_digital = {name: None for name in digital_inputs}
last_encoder_position = 0
last_rotary_position = 0
last_rotary_raw_change = 0

while True:
    for name, io in digital_inputs.items():
        active = not io.value
        if active != last_digital[name]:
            last_digital[name] = active
            print("{:<14} {}".format(name + ":", "ACTIVE" if active else "idle"))

    if encoder.position != last_encoder_position:
        direction = "CW" if encoder.position > last_encoder_position else "CCW"
        print("encoder:       {} (count: {})".format(direction, encoder.position))
        last_encoder_position = encoder.position

    raw = rotary.value
    new_rotary_position = rotary_position(raw)
    if new_rotary_position != last_rotary_position:
        if abs(raw - last_rotary_raw_change) > ROTARY_HYSTERESIS:
            print("rotary:        position {}".format(new_rotary_position))
            last_rotary_position = new_rotary_position
            last_rotary_raw_change = raw

    onboard.value = last_digital["button"] is True

    time.sleep(0.02)
