# Pin Map — DRAFT

Status: **not yet defined.** Finalize before `hardware.py` is written.

## Pico 2 W budget

- 26 exposed GPIOs (GP0–GP22, GP26–GP28 — GP23/GP24/GP25/GP29 are reserved by the W module for Wi-Fi/Bluetooth/LED/ADC_VSYS)
- 8 PWM slices, each with two channels (A/B). Two outputs on the same channel share frequency/duty; two on the same slice but different channels share frequency only
- 3 ADC-capable pins (GP26, GP27, GP28)

## Input count (worst case, one pin per contact)

| Component | Contacts needed | Notes |
|---|---|---|
| `toggle_1` | 1 | SPST to ground, internal pull-up |
| `toggle_2` | 1 | SPST to ground, internal pull-up |
| `paddle` (switch) | 1 | SPST to ground |
| `button` (press) | 1 | Momentary to ground |
| `encoder` (A/B) | 2 | Quadrature — use `rotaryio.IncrementalEncoder` |
| `encoder` (press) | 1 | Momentary to ground |
| `rotary` (12-position) | see below | |

**Subtotal without rotary: 7 inputs.**

## 12-position rotary: three wiring strategies

Decision needed. Tradeoffs below.

### Option A — One GPIO per position (12 inputs)

Simple, robust, debounces cleanly via `keypad.Keys`. Pin cost: 12. Total inputs: 19. Total with 2 LEDs: 21.

Fits the budget but eats the majority of available pins. Leaves no headroom for a future Maker Port breakout, status LEDs, or expansion.

### Option B — Resistor ladder on ADC (1 input) ★ recommended

Each rotary position connects a different total resistance between the ADC pin and ground/Vcc. Software maps the ADC reading to a position 1–12.

Pin cost: 1 (ADC). Total inputs: 8. Total with 2 LEDs: 10.

Downside: requires a small ladder PCB or resistors wired to the rotary lugs. Positions are distinguishable if the resistor values are chosen with enough margin (e.g. binary-weighted across the ADC range, 12 levels across 0–65535 leaves ~5400 counts between positions — plenty).

### Option C — Gray-code encoded (4 inputs)

If the rotary part supports BCD/Gray encoding natively. Alpha Taiwan SR2611 and similar do not (they're single-pole multi-throw). Would require an external encoder IC like a 74HC148 or a small MCU-side decoder.

Pin cost: 4. Complexity: medium. Probably not worth it vs Option B.

**Recommendation: Option B (resistor ladder on ADC, 1 pin).** Saves 11 GPIOs for future expansion. Circuit is trivial.

## LEDs

Two PWM outputs driving MOSFET gates for the 12V paddle and button LEDs.

- `paddle.led` — 1 PWM pin
- `button.led` — 1 PWM pin

Put them on different PWM slices so animations are independent (different frequency/period possible).

## Proposed assignment (pending hardware validation)

This is a first-draft placement; verify against the Pico 2 W pinout and any Pico 2 W-specific reservations.

```
Input (digital, pull-up to 3V3, switch to GND):
  GP2   toggle_1
  GP3   toggle_2
  GP4   paddle  (switch)
  GP5   button  (press)
  GP10  encoder A
  GP11  encoder B
  GP12  encoder press

Input (analog):
  GP26  rotary  (12-position resistor ladder on ADC0)

Output (PWM to MOSFET gate):
  GP14  paddle.led   (PWM slice 7A)
  GP15  button.led   (PWM slice 7B)

  # NOTE: GP14/GP15 are on the same PWM slice (7).
  # Same slice means same frequency, but channel A and B
  # have independent duty cycles — which is all we need for
  # brightness control. If we want different pulse frequencies,
  # move one LED to a different slice, e.g. GP16 (slice 0A).
```

**Open questions:**

- Confirm Pico 2 W's exact Wi-Fi/BT reservations — RP2350 + CYW43439 may differ from RP2040 Pico W
- Confirm encoder pin pair A/B is on a valid `rotaryio` pair (adjacent pins, no special constraints on RP2350)
- Decide: same PWM slice for both LEDs, or separate slices?
- Resistor ladder values for the 12-position rotary — pick after Option B is confirmed

## Notes for schematic

- Every input pin uses internal pull-up (`Pull.UP`); switches tie to GND when actuated
- 100 nF ceramic cap across each mechanical contact helps debounce; software debouncing via `keypad.Keys` is the backstop
- MOSFETs: 2N7000 (TO-92) or AO3400 (SOT-23), gate drive direct from GPIO, 10k gate-to-source pull-down to prevent accidental turn-on during reset
- 12V rail for LEDs comes from a separate DC input or a boost converter, not from USB
