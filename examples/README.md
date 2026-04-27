# Examples

Drop any of these on the device as `code.py` to run.

| File | What it does | Prereqs |
|---|---|---|
| [`smoke_test.py`](smoke_test.py) | Reads every input directly with `digitalio` / `analogio` / `rotaryio`. Verifies the hardware is wired correctly, independent of the library. Use on a freshly assembled unit. | none |
| [`full_assembly.py`](full_assembly.py) | The full `Deadband()` class, every control wired to print on every gesture, plus a 5-second heartbeat to prove the scheduler is alive. The "hello world" reference. | none |
| [`wifi_connect.py`](wifi_connect.py) | Connects to Wi-Fi using credentials from `secrets.py`, prints IP / MAC, then runs the panel's event loop alongside. Foundation for any networked firmware. | `secrets.py` (copy from `secrets.py.example`) |
| [`usb_hid_keyboard.py`](usb_hid_keyboard.py) | Panel becomes a USB HID media keyboard. Button = play/pause, encoder = volume, etc. Plug-and-play, no host-side software. | `circup install adafruit_hid` |

## Library installation with circup

Several examples need CircuitPython libraries that don't ship with the firmware. Install them with [`circup`](https://github.com/adafruit/circup):

```bash
pip install circup
circup install adafruit_hid          # for usb_hid_keyboard.py
```

`circup` auto-detects the connected `CIRCUITPY` drive, picks the matching CircuitPython version, and copies the `.mpy` files into `/CIRCUITPY/lib/`.

## Secrets

Examples that need credentials read them from `/CIRCUITPY/secrets.py`. The repo ships a [`secrets.py.example`](../secrets.py.example) template — copy it, fill in your values, never commit the result.
