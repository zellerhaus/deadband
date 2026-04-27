"""Wi-Fi connection example.

Foundation for any firmware that needs networking. Connects to Wi-Fi
using credentials from secrets.py, prints connection details, then runs
the regular event loop. Network is up alongside the panel - any
callback can issue HTTP requests, MQTT publishes, etc.

Drop on the device as code.py. Make sure /CIRCUITPY/secrets.py exists
with your real Wi-Fi credentials before running. Use secrets.py.example
as the template.

Button LED feedback (silent until the MOSFET stage is wired):
    pulse 0.3s : attempting connection
    dim glow   : connected
    blink 3x   : connection failed
"""

import wifi

from deadband import Deadband
from deadband_net import ensure_wifi
from secrets import secrets


db = Deadband()

print()
print("=== Wi-Fi connect example ===")
print("Connecting to:", secrets["ssid"])

ok = ensure_wifi(secrets, led=db.button.led)

if ok:
    print("Connected.")
    print("  IP:     ", wifi.radio.ipv4_address)
    mac = ":".join("{:02x}".format(b) for b in wifi.radio.mac_address)
    print("  MAC:    ", mac)
    if wifi.radio.ap_info is not None:
        print("  RSSI:   ", wifi.radio.ap_info.rssi, "dBm")
        print("  Channel:", wifi.radio.ap_info.channel)
else:
    print("Failed - check secrets.py.")

print()
print("Panel is live. Use any control to confirm the eventloop is running.")
print()

db.toggle_1.on_change(lambda on: print("toggle_1:", "ON" if on else "OFF"))
db.toggle_2.on_change(lambda on: print("toggle_2:", "ON" if on else "OFF"))
db.button.on_click(lambda: print("button: click"))

db.run()
