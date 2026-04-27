# Library Reference

API reference for the `deadband` package. For design rationale and decisions, see [spec.md](spec.md).

## Top-level

```python
from deadband import Deadband
db = Deadband()
db.run()
```

`Deadband()` instantiates every hardware component using the validated pin map in `deadband.hardware`, attaches LED instances to `paddle.led` and `button.led`, and prepares an `EventLoop` + `Scheduler`. No required arguments.

| Member | Type | Description |
|---|---|---|
| `db.toggle_1`, `db.toggle_2` | `Switch` | Non-illuminated SPST toggles |
| `db.paddle` | `IlluminatedSwitch` | Illuminated rocker (has `.led`) |
| `db.button` | `Button` | Illuminated momentary pushbutton (has `.led`) |
| `db.encoder` | `Encoder` | Rotary encoder with push switch |
| `db.rotary` | `Rotary` | 12-position rotary switch |
| `db.tick()` | method | One pass over all components and the scheduler |
| `db.run()` | method | Block forever, ticking at 5 ms cadence |
| `db.after(delay, fn)` | method | Schedule one-shot timer; returns `Timer` |
| `db.every(interval, fn)` | method | Schedule repeating timer; returns `Timer` |
| `db.on_tick(fn, interval=0.1)` | method | Alias for `every` with default 100 ms |

## Switch (`toggle_1`, `toggle_2`)

Two-state switch with software debouncing.

| Member | Signature | Notes |
|---|---|---|
| `is_on` | property → `bool` | Current debounced state |
| `on_change(fn)` | `fn(is_on: bool)` | Fires on every confirmed transition |
| `on_turn_on(fn)` | `fn()` | Fires only on off→on |
| `on_turn_off(fn)` | `fn()` | Fires only on on→off |

Initial state is seeded from the pin at construction without firing callbacks.

## IlluminatedSwitch (`paddle`)

Switch + LED. All `Switch` members above, plus:

| Member | Notes |
|---|---|
| `led` | An `LED` instance (see [LED](#led-paddleled-buttonled)) |

## Button (`button`)

Momentary pushbutton with the full gesture suite + LED.

### State

| Member | Type | Notes |
|---|---|---|
| `is_pressed` | property → `bool` | Currently held down |
| `press_duration` | property → `float` | Seconds held; `0.0` if not pressed |
| `led` | `LED` | LED sub-object |

### Raw events

| Method | Callback signature |
|---|---|
| `on_press(fn)` | `fn()` — fires immediately on press |
| `on_release(fn)` | `fn()` — fires on release |

### Interpreted gestures

| Method | Callback signature | Fires when |
|---|---|---|
| `on_click(fn, immediate=False)` | `fn()` | Press+release within hold/long-click threshold. With multi-click handlers registered, fires after the multi-click window (~500 ms) closes with count == 1. `immediate=True` overrides — fires every press+release regardless. |
| `on_hold(fn, duration=1.0)` | `fn()` | Press has been held for `duration` seconds (during press). Fires at most once per press. |
| `on_long_click(fn, duration=1.0)` | `fn()` | Press is released after being held ≥ `duration`. Fires on release. Suppresses click. |
| `on_double_click(fn)` | `fn()` | Two clicks within the multi-click window. Suppresses single click (unless `immediate=True` was used). |
| `on_triple_click(fn)` | `fn()` | Three clicks within the multi-click window. |

**Multi-click window:** 500 ms (class constant `ButtonGestureEngine.MULTI_CLICK_WINDOW`).

**Over-click rule:** four or more clicks within the window fire nothing.

**Hold/long-click suppression rule:** if `on_hold` or `on_long_click` fires for a press, that press is not a click candidate — `on_click` will not fire for it.

## Encoder (`encoder`)

24-detent rotary encoder with push switch. Rotation is incremental; press uses the same gesture suite as `Button`.

### Rotation

| Member | Signature | Notes |
|---|---|---|
| `position` | property → `int` | Accumulates indefinitely; reset by firmware if needed |
| `on_turn(fn)` | `fn(direction: int)` | `direction` is `+1` (CW) or `-1` (CCW). Fires per detent. |
| `on_clockwise(fn)` | `fn()` | Fires per CW detent only |
| `on_counterclockwise(fn)` | `fn()` | Fires per CCW detent only |

### Press

Identical to `Button`'s state queries and gesture methods: `is_pressed`, `press_duration`, `on_press`, `on_release`, `on_click`, `on_hold`, `on_long_click`, `on_double_click`, `on_triple_click`.

### Combined

| Method | Callback signature | Notes |
|---|---|---|
| `on_press_turn(fn)` | `fn(direction: int)` | Fires per detent when rotation occurs while pressed |

## Rotary (`rotary`)

12-position rotary switch. Position is absolute, not incremental.

| Member | Signature | Notes |
|---|---|---|
| `position` | property → `int` | Current position, 1–12 |
| `on_change(fn)` | `fn(new_position: int)` | Fires on confirmed position change |

Position is read via ADC against calibrated thresholds (`hardware.ROTARY_THRESHOLDS`) with hysteresis (`hardware.ROTARY_HYSTERESIS = 500`). Brief readings inside a hysteresis band do not fire callbacks.

## LED (`paddle.led`, `button.led`)

PWM-driven LED. Brightness 0.0–1.0; mapped to 16-bit duty cycle at 1 kHz.

Per design decision #8, any of `on/off/set_brightness/pulse/blink` supersedes a running animation. `stop` halts the animation and leaves brightness at its current value.

| Method | Notes |
|---|---|
| `on()` | Brightness → 1.0, mode → idle |
| `off()` | Brightness → 0.0, mode → idle |
| `set_brightness(value)` | Clamps to 0.0–1.0; mode → idle |
| `pulse(period=2.0)` | Cosine breathing waveform; brightness 0.0 → 1.0 → 0.0 over `period` seconds, repeats |
| `blink(times=3, interval=0.2)` | `times` on-pulses of duration `interval`, separated by off-gaps of the same duration. Ends with LED off. |
| `stop()` | Halts current animation; brightness unchanged |
| `brightness` | property → `float` | Current 0.0–1.0 brightness |

## Timer (returned by `db.after`, `db.every`, `db.on_tick`)

| Member | Notes |
|---|---|
| `cancel()` | Cancel the timer. No-op if already fired or cancelled. |
| `is_active` | property → `bool` | True while still scheduled |

**Cancellation rules:**
- Cancel before firing: never fires
- Cancel a one-shot after it fired: no-op
- Cancel a repeating timer during its own callback: stops future fires; current callback runs to completion

**Drift behavior:** if `tick()` is called late, a repeating timer fires once and reschedules past `now`. Missed fires are skipped, not caught up.

## Callback conventions

- Callbacks taking arguments: `on_change(fn)` for switches and rotary, `on_turn(fn)` and `on_press_turn(fn)` for encoder.
- Callbacks taking no arguments: everything else.
- Argument signatures are not auto-detected. Register callbacks with the documented signature.
- Callbacks should return quickly. The event loop is single-threaded; long-running callbacks delay every other component and timer.

## Engines (advanced)

Each interpretive component has a pure-Python engine class that does the actual work. Hardware classes wrap the engines with `digitalio` / `analogio` / `rotaryio` / `pwmio`. Use the engines directly for testing, simulation, or alternative hardware bindings.

| Engine | Purpose |
|---|---|
| `deadband.button.ButtonGestureEngine` | Click / hold / long-click / double / triple disambiguation |
| `deadband.switch.SwitchEngine` | Two-state switch with debouncing |
| `deadband.rotary.RotaryEngine` | ADC threshold + hysteresis classification |
| `deadband.encoder.RotationEngine` | Per-detent rotation events from absolute position |
| `deadband.led.LEDAnimationEngine` | Pulse / blink waveform generation |
| `deadband.timing.Scheduler` | Timer scheduling |
| `deadband.eventloop.EventLoop` | Tick coordinator |

All engines accept an injectable `now_fn` (callable returning seconds) for deterministic test timing.

## Optional networking module

```python
from deadband_net import ensure_wifi, is_connected, disconnect
```

| Function | Notes |
|---|---|
| `ensure_wifi(secrets, led=None, timeout=10)` | Connects if not already connected. `secrets` is dict-like with `"ssid"` and `"password"` keys. `led` is any LED-like object for connection feedback (pulse during, dim glow on success, blink 3× on failure). Returns `True` on success. |
| `is_connected()` | Wrapper for `wifi.radio.connected` |
| `disconnect()` | Wrapper for `wifi.radio.stop_station()` |

`deadband_net.py` lives at the same level as the `deadband/` package, not inside it. Firmware that doesn't need networking simply doesn't import it.

## Pin map

Validated 2026-04-22. See [docs/pinmap.md](pinmap.md) for full assignment and rationale.

```
GP6   toggle_1         GP4   button (press)
GP5   toggle_2         GP10  encoder A
GP16  paddle (switch)  GP11  encoder B
                       GP12  encoder press

GP26  rotary (ADC0, resistor ladder, 12 positions)

GP14  paddle.led (PWM, MOSFET gate)
GP15  button.led (PWM, MOSFET gate)
```
