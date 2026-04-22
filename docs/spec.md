# Deadband Library — Implementation Spec

This is the design spec for `deadband.py`, the CircuitPython library that abstracts the Deadband control surface hardware for community firmware development.

## Product context

Deadband is a premium programmable desk control surface. The hardware ships with default firmware but is designed to be reprogrammed by the end user — reprogrammability is a first-class product feature, not a hidden capability.

The end-user experience for reprogramming:

1. Plug the Deadband into a computer via the rear-mounted USB-C jack
2. Deadband appears as a USB drive running CircuitPython
3. Drag a new `code.py` onto the drive
4. The device runs the new firmware within seconds — no tools, no compiler

Community firmware will be shared via GitHub forks of a reference repo maintained by the manufacturer. The `deadband.py` library is the stable interface that all community firmware is written against.

## Target platform

- **Microcontroller:** Raspberry Pi Pico 2 W (RP2350, Wi-Fi + Bluetooth)
- **Runtime:** CircuitPython 9.2.x or later
- **Physical USB-C port:** Panel-mounted jack on the rear of the enclosure, internally wired to the Pico's USB connector

## Hardware components

The Deadband has six physical controls. The library refers to them by type-based names (not by silkscreen labels, which vary across stock and custom label sets).

| Library name | Physical control | Notes |
|:---:|:---:|:---:|
| `toggle_1` | SPST toggle with red flip guard | No LED |
| `toggle_2` | SPST toggle with red flip guard | No LED |
| `paddle`   | Illuminated SPST paddle/rocker | Built-in LED, independently controlled |
| `button`   | Apiele illuminated momentary pushbutton | Built-in LED, independently controlled |
| `encoder`  | 24-detent rotary encoder with push switch | A/B rotation + momentary press |
| `rotary`   | 12-position rotary switch | One position active at a time |

Note on the button: it's a *momentary* pushbutton, not a latch. The library implements timing-based interpretation (click, hold, long-click, double-click, triple-click) so firmware can distinguish multiple gestures from a single physical control.

## Public API

### Top-level object

A single `Deadband` class is instantiated once per firmware:

```python
from deadband import Deadband

db = Deadband()
```

`Deadband()` initializes all hardware, sets up internal state, and exposes all six components as attributes. The constructor takes no required arguments (pin assignments are baked into the library since hardware is consistent across units).

### Switch-type components (`toggle_1`, `toggle_2`)

Non-illuminated two-state switches. Persistent on/off state.

```python
db.toggle_1.is_on                  # bool: current state
db.toggle_1.on_change(fn)          # fn(is_on: bool) on any state change
db.toggle_1.on_turn_on(fn)         # fn() only when turning on
db.toggle_1.on_turn_off(fn)        # fn() only when turning off
```

### Illuminated switch (`paddle`)

Same interface as toggle, plus an `.led` sub-object.

```python
db.paddle.is_on
db.paddle.on_change(fn)
db.paddle.on_turn_on(fn)
db.paddle.on_turn_off(fn)

db.paddle.led.on()
db.paddle.led.off()
db.paddle.led.set_brightness(0.5)     # 0.0 to 1.0
db.paddle.led.pulse(period=2.0)       # breathing effect
db.paddle.led.blink(times=3, interval=0.2)
db.paddle.led.stop()                  # stop any ongoing animation
```

### Illuminated momentary (`button`)

Momentary pushbutton with LED. Full timing-based gesture suite.

```python
# State
db.button.is_pressed               # bool: currently held down
db.button.press_duration           # float: seconds held, 0 if not pressed

# Raw events
db.button.on_press(fn)             # fn() immediately on press
db.button.on_release(fn)           # fn() on release

# Interpreted events
db.button.on_click(fn)             # fn() on press+release under threshold
db.button.on_hold(fn, duration=1.0)         # fn() when threshold reached, still held
db.button.on_long_click(fn, duration=1.0)   # fn() on release after >= duration
db.button.on_double_click(fn)      # fn() on two clicks within multi-click window
db.button.on_triple_click(fn)      # fn() on three clicks within multi-click window

# LED (same interface as paddle.led)
db.button.led.on()
db.button.led.off()
db.button.led.set_brightness(0.5)
db.button.led.pulse(period=2.0)
db.button.led.blink(times=3, interval=0.2)
db.button.led.stop()

# Optional immediate override
db.button.on_click(fn, immediate=True)  # force immediate firing even with multi-click handlers
```

### Encoder (`encoder`)

Rotary encoder with push switch. Rotation events are incremental (not positional); press events use the same gesture suite as the button.

```python
# Rotation
db.encoder.position                # int: accumulates indefinitely (firmware manages bounds)
db.encoder.on_turn(fn)             # fn(direction: int) where direction is +1 or -1
db.encoder.on_clockwise(fn)        # fn() on clockwise detents only
db.encoder.on_counterclockwise(fn) # fn() on counter-clockwise detents only

# Press (identical to button API)
db.encoder.is_pressed
db.encoder.press_duration
db.encoder.on_press(fn)
db.encoder.on_release(fn)
db.encoder.on_click(fn)
db.encoder.on_hold(fn, duration=1.0)
db.encoder.on_long_click(fn, duration=1.0)
db.encoder.on_double_click(fn)
db.encoder.on_triple_click(fn)

# Combined gesture
db.encoder.on_press_turn(fn)       # fn(direction) on rotation while held
```

### Rotary switch (`rotary`)

12-position switch. Position is absolute (1-12), not incremental.

```python
db.rotary.position                 # int: 1 to 12 (1-indexed)
db.rotary.on_change(fn)            # fn(new_position: int) when position changes
```

### Framework-level API

The library provides a run loop and timing helpers.

```python
db.run()                           # blocking main loop; handles debouncing,
                                   # LED animations, timer callbacks, etc.

# Timing helpers (all return a Timer object with .cancel() and .is_active)
db.on_tick(fn, interval=0.1)       # periodic callback every `interval` seconds
db.after(delay, fn)                # fn() once after `delay` seconds
db.every(interval, fn)             # alias for on_tick with named semantics

# Timer objects
timer = db.after(5.0, expired)
timer.cancel()                     # stop a pending/repeating timer
timer.is_active                    # bool: timer still scheduled
```

## Design decisions (locked)

### 1. Click disambiguation: auto-delay

When a firmware registers multi-click handlers alongside `on_click`, the library automatically delays `on_click` firing by the multi-click window (~300ms) so it can distinguish a single click from a double/triple click.

- **If only `on_click` is registered:** fires immediately on release.
- **If `on_double_click` or `on_triple_click` is also registered:** `on_click` delays until the multi-click window has closed without additional clicks.
- **Explicit override:** `on_click(fn, immediate=True)` forces immediate firing regardless of other registered handlers.

### 2. Callback-based event model

All events use callback registration (`on_*(fn)`). No async/await, no polling flags, no signals/observers. This is the pattern Python programmers expect and is approachable for new CircuitPython users.

Complex state machines can be built on top of callbacks; the library does not provide a state-machine abstraction.

### 3. No state namespace in v1

Do not add `db.state` or any persistence helpers. Community firmware uses module-level globals or user-defined classes. Revisit in v2 after seeing actual usage patterns.

### 4. No networking helpers in the core library

`deadband.py` is strictly a hardware abstraction. Wi-Fi, Bluetooth, webhooks, and protocol handling are not included.

If networking utilities become a common need, ship them as a separate optional module (e.g., `deadband_net.py`) that community firmware imports only when needed.

### 5. Callback argument conventions

Callbacks receive arguments when the event carries information:

- `on_change(fn)` on switches: `fn(is_on: bool)`
- `on_change(fn)` on rotary: `fn(new_position: int)`
- `on_turn(fn)` on encoder: `fn(direction: int)` (+1 or -1)
- `on_press_turn(fn)` on encoder: `fn(direction: int)`

Callbacks receive no arguments when the event carries no information:

- `on_press`, `on_release`, `on_click`, `on_hold`, `on_long_click`, `on_double_click`, `on_triple_click`
- `on_turn_on`, `on_turn_off`
- `on_clockwise`, `on_counterclockwise`

Document argument signatures clearly. Do not auto-detect argument counts — simpler to require the correct signature and let first-time errors teach the convention.

### 6. Hardcoded pin assignments

Pin numbers for all components are hardcoded in the library constructor. Hardware is consistent across all shipped Deadband units (including variants with different silkscreen labels — only the graphics differ, not the components).

### 7. Timer cancellation semantics

Timers returned from `after` and `every` are always cancellable. Canceling an already-fired one-shot timer is a no-op. Canceling a repeating timer stops future invocations but does not interrupt one already in progress.

### 8. LED animation lifecycle

Only one LED animation runs at a time per LED. Calling `pulse()`, `blink()`, `on()`, `off()`, or `set_brightness()` automatically supersedes any currently running animation on that LED. `stop()` halts the current animation and leaves the LED in its current instantaneous state.

## Implementation architecture

```
deadband/
  __init__.py        # exports the Deadband class, imports everything
  hardware.py        # pin map constants
  switch.py          # Switch base class (toggle_1, toggle_2)
  illuminated.py     # IlluminatedSwitch class (paddle), inherits Switch + LED
  button.py          # Button class (momentary + gesture suite + LED)
  encoder.py         # Encoder class (rotation + press gestures)
  rotary.py          # Rotary class (12-position switch)
  led.py             # LED controller with animation state machine
  timing.py          # Timer class, scheduler
  eventloop.py       # main run() loop, debouncing, animation tick
```

The `Deadband` class in `__init__.py` is the assembly point — it instantiates all components and wires them to the shared event loop.

## Internal implementation notes

### Debouncing

All mechanical switches (toggles, paddle, button press, encoder press) need software debouncing. Use CircuitPython's built-in `keypad.Keys` module, which handles debouncing in C and exposes an event queue. Avoid rolling a 1 kHz Python poll loop.

### Encoder quadrature

Use CircuitPython's `rotaryio.IncrementalEncoder`. Most 24-detent encoders report one count per detent through this module, but verify the division factor against the specific part.

### LED PWM

Both LED pins (paddle and button) are PWM-capable via `pwmio.PWMOut`. Verify the chosen Pico pins are on independent PWM slices if simultaneous animation is desired.

### Power driving

LEDs on the paddle and button are driven through MOSFETs (e.g., 2N7000 or AO3400) because the LEDs are 12V and the Pico GPIO is 3.3V. The library just drives the gate with PWM-capable GPIO; the external MOSFET does the actual switching.

### Thread/concurrency model

CircuitPython on RP2350 is effectively single-threaded. The `run()` loop sequentially:

1. Drains `keypad.Keys` event queue (already debounced)
2. Reads `rotaryio` encoder position
3. Samples rotary switch position
4. Updates LED animation state
5. Services timer callbacks
6. Dispatches event callbacks synchronously

Community firmware callbacks run on the same thread. Callbacks should return quickly and not block (no `time.sleep()` in callbacks).

Use `supervisor.ticks_ms()` for gesture timing, not `time.monotonic()` — integer ms math is immune to float precision drift on a device that has been powered on for weeks.

## Shipped files on the device

```
/
├── code.py                  # default firmware (reference implementation)
├── secrets.py.example       # template for Wi-Fi / credentials
├── deadband/                # library package
│   └── ... (as above)
├── lib/                     # CircuitPython dependencies (adafruit_requests, etc.)
└── README.txt               # one-page orientation for new users
```

**Do not ship a `secrets.py`** — only `secrets.py.example`. This ensures the user consciously creates `secrets.py` for their own credentials.

## Secrets pattern (community convention)

```python
# secrets.py (user creates this, never committed to git)
secrets = {
    "ssid": "your-wifi-network",
    "password": "your-wifi-password",
    "webhook_url": "https://hooks.example.com/...",
}

# code.py (safe to share)
from secrets import secrets
import wifi

wifi.radio.connect(secrets["ssid"], secrets["password"])
```

README and example firmwares should consistently demonstrate this pattern.

## Wi-Fi connection pattern (community convention)

```python
def ensure_wifi():
    if not wifi.radio.connected:
        try:
            db.button.led.pulse(period=0.3)
            wifi.radio.connect(secrets["ssid"], secrets["password"])
            db.button.led.set_brightness(0.15)
            return True
        except Exception as e:
            print("Wi-Fi failed:", e)
            db.button.led.blink(times=3, interval=0.1)
            return False
    return True
```

Call `ensure_wifi()` before any network operation. Application-level code, not library code.

## Default firmware concept

The default `code.py` implements a "focus ritual" pomodoro timer:

- `toggle_1` (HUSTLE): long session preset (25 min work / 5 min break)
- `toggle_2` (COAST): short session preset (15 min work / 3 min break)
- `paddle` (DND): do-not-disturb indicator; LED on when active
- `rotary` (VIBE): number of sessions before extended break (1-12)
- `encoder` (ENERGY): +/- 1 minute adjustment to current session
- `button` (LAUNCH): click to start/pause, long-click to reset, double-click to skip to break

LED behavior:

- `button.led`: soft idle glow (~15% brightness), pulses during active session, flashes 6 times when a session completes
- `paddle.led`: on when DND is active, off otherwise

No network access required. Ships working out of the box.

## Open items (acceptable, not blocking)

1. **Global state in community firmware is ugly but acceptable.** CircuitPython doesn't have a clean alternative without forcing classes. `db.state` namespace deferred to v2.
2. **Context-dependent button interpretation is the community's problem.** The library cannot abstract this without becoming opinionated.
3. **Networking patterns are documentation, not library.** If patterns stabilize into clear idioms, consider `deadband_net.py` in v2.
4. **No simulator or headless test mode for hardware modules.** Pure-Python logic (gestures, timing) IS testable off-device; see `tests/`.

## Implementation priorities

Recommended build order:

1. Pin map and hardware module (`hardware.py`)
2. LED controller with animation state machine (`led.py`)
3. Switch base class (`switch.py`) using `keypad.Keys`
4. `IlluminatedSwitch` (`illuminated.py`) composing Switch + LED
5. Button class (`button.py`) with gesture suite — wraps `ButtonGestureEngine`
6. Encoder class (`encoder.py`) — reuses button's gesture engine for press
7. Rotary class (`rotary.py`) — simplest, do last
8. Timing infrastructure (`timing.py`) — needed for animations and gestures
9. Main loop (`eventloop.py`)
10. Deadband assembly class (`__init__.py`)
11. Default `code.py` (pomodoro timer)
12. `secrets.py.example` and `README.txt`

Steps 1–2 and 8 are foundational; most other modules depend on them.

`ButtonGestureEngine` (the pure-Python, hardware-agnostic state machine inside `button.py`) is implemented first and fully tested off-device before any hardware wrapping.
