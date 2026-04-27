"""Pin map for the Deadband control surface.

Hardware values validated against the prototype unit on 2026-04-22.
LED outputs (PADDLE_LED, BUTTON_LED) are reserved but not yet wired
through to the MOSFET driver stage.

Importing this module requires CircuitPython's `board` — it is intended
for on-device use only. Off-device tests should not import it.
"""

import board


# Digital inputs (internal pull-up, switch to GND)
TOGGLE_1 = board.GP6
TOGGLE_2 = board.GP5
PADDLE = board.GP16
BUTTON = board.GP4

# Encoder
ENCODER_A = board.GP10
ENCODER_B = board.GP11
ENCODER_PRESS = board.GP12

# Analog input — 12-position rotary on ADC0
ROTARY = board.GP26

# PWM outputs to MOSFET gates (planned, not yet wired)
PADDLE_LED = board.GP14
BUTTON_LED = board.GP15

# Onboard module LED — used for heartbeat / debug echo
ONBOARD_LED = board.LED


# Rotary calibration — validated against the prototype's resistor ladder
# on 2026-04-22. The 11 thresholds define the boundaries between the 12
# physical positions. ROTARY_HYSTERESIS is applied around each boundary
# to prevent flicker between adjacent positions.
ROTARY_THRESHOLDS = (
    1536, 4640, 7793, 10946, 14083, 17175,
    20272, 23415, 26535, 29622, 32747,
)
ROTARY_HYSTERESIS = 500
