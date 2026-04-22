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

Driven by a Raspberry Pi Pico 2 W (RP2350) running CircuitPython.

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

Design spec: [docs/spec.md](docs/spec.md).

Full API reference: coming with the first hardware-backed release.

## Default firmware

`code.py` ships as a pomodoro timer. It works offline, out of the box. Replace it with your own — the device boots whatever's on the drive.

## Development

Pure-Python logic (gesture disambiguation, timing, scheduling) is tested off-device:

```bash
pip install pytest
pytest tests/
```

Hardware modules run only on a Pico 2 W. Flash CircuitPython 9.2.x or later.

## Secrets

For firmware that needs credentials, copy `secrets.py.example` to `secrets.py` and fill it in. `secrets.py` is gitignored by default. Share `secrets.py.example`, never `secrets.py`.

## License

MIT. See [LICENSE](LICENSE).
