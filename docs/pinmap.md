# Pin Map

Target: Raspberry Pi Pico 2 W (RP2350).

## Assignment

12-position rotary uses a resistor ladder on ADC0. See [12-position rotary](#12-position-rotary-resistor-ladder-on-adc) for the rationale.

```
Input (digital, internal pull-up, switch to GND):
  GP2   toggle_1
  GP3   toggle_2
  GP4   paddle (switch)
  GP5   button (press)
  GP10  encoder A
  GP11  encoder B
  GP12  encoder press

Input (analog):
  GP26  rotary (12-pos resistor ladder, ADC0)

Output (PWM → MOSFET gate, 12V LED on drain):
  GP14  paddle.led   (PWM slice 7A)
  GP15  button.led   (PWM slice 7B)
```

Total: 8 digital inputs + 1 analog input + 2 PWM outputs = 11 pins used. 15 GPIOs free for expansion (e.g. a future Maker Port breakout).

## Pico 2 W budget

- 26 exposed GPIOs (GP0–GP22, GP26–GP28). GP23/GP24/GP25/GP29 are reserved by the W module for Wi-Fi/Bluetooth/LED/ADC_VSYS — confirm against the Pico 2 W datasheet (RP2350 + CYW43439 may differ from the RP2040 Pico W)
- 12 PWM slices, each with two channels (A/B). Outputs on the same slice share frequency; channel duties are independent
- 4 ADC-capable pins on RP2350 (GP26–GP29; note GP29 is reserved on the W module)

## 12-position rotary: resistor ladder on ADC

A linear resistor ladder between 3V3 and GND; each rotary position taps a different node. The ADC reads the wiper voltage; software maps the 16-bit reading to a position 1–12.

With 12 equally-spaced levels across the 16-bit ADC range (0–65535), positions are ~5460 counts apart. Hysteresis of ±500 counts (~±0.75%) absorbs noise without risk of ambiguous reads.

**Suggested values (finalize after prototype):**

- `R_top`: 10 kΩ from 3V3 to position 12
- `R_step`: 1 kΩ between each adjacent position (11 total)
- Rotary common connects to the ADC pin
- Position 1 connects to GND through the final step

**Firmware side:**

- Sample ADC at 20 Hz (rotary is a slow control — no need for faster)
- Median-of-3 samples to suppress crosstalk and noise
- Compare against 12 pre-computed midpoint thresholds
- Apply hysteresis of ±3% of ADC range on each boundary

## LEDs

Two PWM outputs driving MOSFET gates for the 12V paddle and button LEDs. GP14 and GP15 are paired on PWM slice 7 (channels A and B respectively) — they share frequency but have independent duty cycles, which is all that brightness control and smooth pulsing require.

If a future firmware needs different *pulse frequencies* on the two LEDs (e.g. one at 1 Hz breathing, one at 3 Hz blinking), move `button.led` to a different slice. GP16 (slice 0A) is a clean alternative.

## Schematic notes

- Every digital input uses `Pull.UP`; actuation ties the pin to GND
- 100 nF ceramic cap across each mechanical contact for passive debounce (software debouncing via `keypad.Keys` is the primary mechanism)
- MOSFETs for LEDs: 2N7000 (TO-92) or AO3400 (SOT-23)
- 10 kΩ gate-to-source pull-down on each MOSFET to hold it off during reset
- 12V rail for the LEDs comes from a separate DC input, not USB VBUS

## Verification still needed

- Pico 2 W GPIO reservations — confirm which pins are exposed on the final module pinout, and whether any RP2350-specific functions take priority on GP14/GP15/GP26
- `rotaryio.IncrementalEncoder` pair validity — GP10/GP11 need to be a contiguous pair with no RP2350-specific exclusions
- Resistor ladder tolerance — 1% resistors at 1 kΩ × 12 steps have enough margin; confirm against the prototype's actual readings

## Considered alternatives (rotary wiring)

### Option A — one GPIO per position

12 digital inputs, one per position, with the rotary's common to GND. `keypad.Keys` debounces cleanly. Eats 12 of 26 GPIOs. Rejected to preserve headroom for future expansion.

### Option C — external priority encoder (74HC148)

Collapses 12 inputs to 4 outputs via an external chip. Adds a component and board area for no functional gain over the resistor ladder. Rejected as over-engineered.
