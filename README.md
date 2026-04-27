# Deadband Firmware

CircuitPython library and reference firmware for the Deadband control surface.

Plug the panel in. It shows up as a USB drive. Drag a new `code.py` onto it. The device runs your firmware.

## Hardware

Six controls on a CNC-machined aluminum panel:

- Two guarded SPST toggles
- One illuminated paddle switch
- One illuminated momentary pushbutton
- One 24-detent rotary encoder with push
- One 12-position rotary switch

Driven by a Raspberry Pi Pico 2 W (RP2350) running CircuitPython 10.

## Getting started

```python
from deadband import Deadband

db = Deadband()

db.button.on_click(lambda: db.paddle.led.blink(times=2))
db.toggle_1.on_change(lambda is_on: print("toggle_1:", is_on))

db.run()
```

Component names (`toggle_1`, `paddle`, `button`, `encoder`, `rotary`) refer to the physical controls. Silkscreen labels vary by label set and don't affect the code.

## Library reference

- [docs/library-reference.md](docs/library-reference.md) — full API reference
- [docs/spec.md](docs/spec.md) — design spec
- [docs/pinmap.md](docs/pinmap.md) — pin assignments and wiring notes

## Examples

[`examples/`](examples/) holds runnable firmware. Drop any of them on the device as `code.py`.

| File | What it does |
|---|---|
| [`full_assembly.py`](examples/full_assembly.py) | All six controls, every gesture, scheduler heartbeat — the "hello world" |
| [`smoke_test.py`](examples/smoke_test.py) | Direct hardware read for fresh-unit verification |
| [`wifi_connect.py`](examples/wifi_connect.py) | Wi-Fi connection with `deadband_net.ensure_wifi()` |
| [`usb_hid_keyboard.py`](examples/usb_hid_keyboard.py) | Panel as a USB HID media keyboard |

See [`examples/README.md`](examples/README.md) for prereqs (some need a `circup install` line).

## Optional helpers

The core `deadband` package is strictly hardware abstraction. Optional modules sit alongside it for firmware that needs more:

- [`deadband_net.py`](deadband_net.py) — `ensure_wifi()`, `is_connected()`, `disconnect()`. Imported only by firmware that uses Wi-Fi.

## Default firmware

`code.py` will ship as a pomodoro focus-ritual timer. It works offline, out of the box. Replace it with your own — the device boots whatever's on the drive.

## Development

Pure-Python logic (gesture disambiguation, timing, scheduling, LED animations, rotary classification) is tested off-device. The full suite runs in under 50 ms with no hardware required:

```bash
pip install pytest
pytest tests/
```

Hardware-facing modules (anything that imports `digitalio`, `analogio`, `rotaryio`, `pwmio`, `wifi`) run only on the Pico. Flash CircuitPython 10.2 or later.

## Secrets

For firmware that needs credentials, copy `secrets.py.example` to `secrets.py` and fill it in. `secrets.py` is gitignored by default. Share `secrets.py.example`, never `secrets.py`.

## License

MIT. See [LICENSE](LICENSE).
