"""Full Deadband assembly demo.

Exercises the public Deadband() class with every control and every
gesture the API exposes. The heartbeat line confirms the scheduler
is running alongside the hardware tickables.

Useful as:
    - a smoke test after flashing or library updates
    - the "hello world" reference for new firmware authors
    - a one-shot way to verify every callback path on a finished panel

Drop on the device as code.py. No external dependencies beyond the
deadband package itself - no Wi-Fi, no HID, no MQTT.
"""

from deadband import Deadband


db = Deadband()

# Toggles
db.toggle_1.on_change(lambda on: print("toggle_1:", "ON" if on else "OFF"))
db.toggle_2.on_change(lambda on: print("toggle_2:", "ON" if on else "OFF"))

# Paddle (rocker)
db.paddle.on_change(lambda on: print("paddle:", "ON" if on else "OFF"))

# Button — every gesture
db.button.on_click(lambda: print("button: click"))
db.button.on_double_click(lambda: print("button: double-click"))
db.button.on_triple_click(lambda: print("button: triple-click"))
db.button.on_hold(lambda: print("button: HOLD threshold (1s)"))
db.button.on_long_click(lambda: print("button: long-click on release"))

# Encoder — rotation
db.encoder.on_clockwise(lambda: print("encoder: CW"))
db.encoder.on_counterclockwise(lambda: print("encoder: CCW"))

# Encoder — every press gesture
db.encoder.on_click(lambda: print("encoder: click"))
db.encoder.on_double_click(lambda: print("encoder: double-click"))
db.encoder.on_triple_click(lambda: print("encoder: triple-click"))
db.encoder.on_hold(lambda: print("encoder: HOLD threshold (1s)"))
db.encoder.on_long_click(lambda: print("encoder: long-click on release"))

# Encoder — combined press+turn
db.encoder.on_press_turn(
    lambda d: print("encoder: press+turn", "+1" if d > 0 else "-1")
)

# Rotary
db.rotary.on_change(lambda pos: print("rotary: position", pos))

# Scheduler heartbeat — proves the loop is alive
db.every(5.0, lambda: print("[heartbeat]"))

# LED behaviors — electrical only until MOSFETs are wired through.
db.button.led.pulse(period=2.0)
db.paddle.led.set_brightness(0.15)


print()
print("=== Deadband full assembly ===")
print("Hold a button for 1+ seconds to trigger HOLD and long-click.")
print("Click 3 times within ~500ms for triple-click.")
print("Heartbeat every 5 seconds.")
print()


db.run()
