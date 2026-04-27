"""USB HID example - panel as a media keyboard.

Maps panel gestures to keyboard and media-key events sent to the host
computer over the USB connection. Works the moment the device is
plugged in - no pairing, no extra software on the host.

Default mapping (customize freely):

    button single click       -> Play/Pause
    button double-click       -> Next track
    button triple-click       -> Previous track
    button hold (1s)          -> Mute
    encoder clockwise         -> Volume Up
    encoder counterclockwise  -> Volume Down
    encoder click             -> Play/Pause (alias for button)
    toggle_1                  -> sends Cmd+Shift+M (custom shortcut)
    paddle (rocker)           -> sends Cmd+Shift+D (custom shortcut)

Drop on the device as code.py. The host should immediately recognize
a new "CircuitPython HID" keyboard device.

Required: adafruit_hid in /CIRCUITPY/lib/. Install with circup:
    circup install adafruit_hid
"""

import usb_hid

from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

from deadband import Deadband


db = Deadband()

kbd = Keyboard(usb_hid.devices)
cc = ConsumerControl(usb_hid.devices)


# -- button: media transport ------------------------------------------

db.button.on_click(lambda: cc.send(ConsumerControlCode.PLAY_PAUSE))
db.button.on_double_click(lambda: cc.send(ConsumerControlCode.SCAN_NEXT_TRACK))
db.button.on_triple_click(lambda: cc.send(ConsumerControlCode.SCAN_PREVIOUS_TRACK))
db.button.on_hold(lambda: cc.send(ConsumerControlCode.MUTE))


# -- encoder: volume + play/pause -------------------------------------

db.encoder.on_clockwise(lambda: cc.send(ConsumerControlCode.VOLUME_INCREMENT))
db.encoder.on_counterclockwise(lambda: cc.send(ConsumerControlCode.VOLUME_DECREMENT))
db.encoder.on_click(lambda: cc.send(ConsumerControlCode.PLAY_PAUSE))


# -- toggles and paddle: custom keyboard shortcuts --------------------

# Use GUI for Cmd on macOS / Win key on Windows / Super on Linux.
def send_shortcut(*keys):
    kbd.send(*keys)


db.toggle_1.on_turn_on(
    lambda: send_shortcut(Keycode.GUI, Keycode.SHIFT, Keycode.M)
)
db.paddle.on_turn_on(
    lambda: send_shortcut(Keycode.GUI, Keycode.SHIFT, Keycode.D)
)


# -- diagnostic prints (visible in serial pane only) ------------------

db.button.on_click(lambda: print("HID: play/pause"))
db.button.on_double_click(lambda: print("HID: next track"))
db.button.on_triple_click(lambda: print("HID: previous track"))
db.button.on_hold(lambda: print("HID: mute"))
db.encoder.on_clockwise(lambda: print("HID: volume up"))
db.encoder.on_counterclockwise(lambda: print("HID: volume down"))
db.toggle_1.on_turn_on(lambda: print("HID: GUI+Shift+M"))
db.paddle.on_turn_on(lambda: print("HID: GUI+Shift+D"))


print()
print("=== Deadband USB HID example ===")
print("Panel is now a USB media keyboard.")
print("Try: button -> play/pause, encoder -> volume, toggle_1/paddle -> shortcuts.")
print()


db.run()
