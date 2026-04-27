"""Illuminated rocker switch — the paddle.

`IlluminatedSwitch` is a `Switch` with an `.led` sub-object. The press
half (`is_on`, `on_change`, `on_turn_on`, `on_turn_off`) is inherited
unchanged. The `.led` attribute is `None` until the panel's MOSFET
driver stage is wired through and `led.py` lands; once it does, the
eventloop assembly populates `.led` with an LED instance.

Callers should guard with `if paddle.led is not None: paddle.led.on()`
until LED hardware is live.
"""

from .switch import Switch


class IlluminatedSwitch(Switch):
    """A Switch with an LED sub-object.

    The press behavior is identical to `Switch`. The only addition is
    `.led`, which is reserved for the LED implementation.
    """

    def __init__(self, pin, now_fn=None, debounce=None):
        super().__init__(pin, now_fn=now_fn, debounce=debounce)
        self.led = None
