# Pin Map

Target: Raspberry Pi Pico 2 W (RP2350).

## Assignment

Validated on hardware 2026-04-22 against the prototype unit. LED outputs remain planned (board not yet wired through to the MOSFET stage).

```
Input (digital, internal pull-up, switch to GND):
  GP6   toggle_1
  GP5   toggle_2
  GP16  paddle (switch)
  GP4   button (press)
  GP10  encoder A
  GP11  encoder B
  GP12  encoder press

Input (analog):
  GP26  rotary (12-pos resistor ladder, ADC0)

Output (PWM → MOSFET gate, 12V LED on drain) — PLANNED:
  GP14  paddle.led
  GP15  button.led
```

`board.LED` (the onboard module LED) is used as a heartbeat / press echo during development.

The canonical bring-up procedure is [`examples/smoke_test.py`](../examples/smoke_test.py) — drop it on the device as `code.py` to verify every input on a freshly assembled unit.

## Pico 2 W budget

- 26 exposed GPIOs (GP0–GP22, GP26–GP28). GP23/GP24/GP25/GP29 are reserved by the W module for Wi-Fi/Bluetooth/LED/ADC_VSYS
- 12 PWM slices, each with two channels (A/B). Outputs on the same slice share frequency; channel duties are independent
- 4 ADC-capable pins on RP2350 (GP26–GP29; GP29 reserved on the W module)

## 12-position rotary: resistor ladder on ADC

A resistor ladder between 3V3 and GND; each rotary position taps a different node. The ADC reads the wiper voltage; software maps the 16-bit reading to a position 1–12.

The actual ladder doesn't span the full ADC range — it tops out around 32k of 65k, which still gives ~3100 counts of separation between adjacent positions. Plenty.

**Calibrated thresholds (validated 2026-04-22):**

```python
ROTARY_THRESHOLDS = (1536, 4640, 7793, 10946, 14083, 17175,
                     20272, 23415, 26535, 29622, 32747)
ROTARY_HYSTERESIS = 500  # counts
```

11 thresholds define the boundaries between 12 positions. The library takes a raw reading and returns the position whose threshold is the first to exceed the reading; if every threshold is below it, the position is 12.

**Firmware side:**

- Sample ADC at ~50 Hz (the smoke test loops at 50 Hz; library can drop to 20 Hz for the rotary specifically)
- Apply ±500-count hysteresis around boundaries to prevent flicker between adjacent positions
- The thresholds are unit-specific in principle but, with 1% resistors, identical units should match within tens of counts

## LEDs (planned)

Two PWM outputs driving MOSFET gates for the 12V paddle and button LEDs. GP14 and GP15 are paired on PWM slice 7 (channels A and B respectively) — they share frequency but have independent duty cycles, which is all that brightness control and smooth pulsing require.

If a future firmware needs different *pulse frequencies* on the two LEDs (e.g. one at 1 Hz breathing, one at 3 Hz blinking), move `button.led` to a different slice. GP16 is in use by the paddle switch, so consider GP17 (slice 0B) or GP18 (slice 1A).

## Schematic notes

- Every digital input uses `Pull.UP`; actuation ties the pin to GND
- 100 nF ceramic cap across each mechanical contact for passive debounce (software debouncing via `keypad.Keys` is the primary mechanism)
- MOSFETs for LEDs: 2N7000 (TO-92) or AO3400 (SOT-23)
- 10 kΩ gate-to-source pull-down on each MOSFET to hold it off during reset
- 12V rail for the LEDs comes from a separate DC input, not USB VBUS

## Considered alternatives (rotary wiring)

### Option A — one GPIO per position

12 digital inputs, one per position, with the rotary's common to GND. `keypad.Keys` debounces cleanly. Eats 12 of 26 GPIOs. Rejected to preserve headroom for future expansion.

### Option C — external priority encoder (74HC148)

Collapses 12 inputs to 4 outputs via an external chip. Adds a component and board area for no functional gain over the resistor ladder. Rejected as over-engineered.
