"""Optional networking helpers for Deadband firmware.

Sibling of the `deadband` package, not part of it. Import only when
your firmware actually needs networking - keeps the core library small
and import-free of `wifi`, `ssl`, etc. on devices that never go online.

Patterns here are starting points. Promote any that become widespread
to the core library after they prove out.

Available helpers:

    ensure_wifi(secrets, led=None, timeout=10)
        Connect to Wi-Fi if not already connected. Optional LED feedback
        per the spec convention: pulse during attempt, dim glow on
        success, blink 3x on failure.

    is_connected()
        Thin wrapper for wifi.radio.connected.

    disconnect()
        Thin wrapper for wifi.radio.stop_station().

Hardware: CircuitPython's built-in `wifi` module on a Pico 2 W
(RP2350 + CYW43439). 2.4 GHz only.
"""


def is_connected():
    """True if the radio is currently associated with an access point."""
    import wifi
    return wifi.radio.connected


def ensure_wifi(secrets, led=None, timeout=10):
    """Connect to Wi-Fi if not already connected.

    Args:
        secrets: dict-like with "ssid" and "password" keys.
        led: optional LED-like object (pulse / set_brightness / blink /
            stop methods). Used for connection feedback.
        timeout: connection timeout in seconds. Default 10.

    Returns:
        True if connected (whether already or newly).
        False on connection failure.
    """
    import wifi

    if wifi.radio.connected:
        return True

    if led is not None:
        led.pulse(period=0.3)

    try:
        wifi.radio.connect(
            secrets["ssid"],
            secrets["password"],
            timeout=timeout,
        )
    except Exception as e:
        print("Wi-Fi connect failed:", e)
        if led is not None:
            led.blink(times=3, interval=0.1)
        return False

    if led is not None:
        led.set_brightness(0.15)
    return True


def disconnect():
    """Disconnect from Wi-Fi."""
    import wifi
    wifi.radio.stop_station()
