"""Event loop — ticks every registered component plus the scheduler.

`EventLoop` is a thin coordinator. It owns a list of "tickables"
(anything with a `.tick()` method) and a `Scheduler`. On each pass:

  1. Every tickable's `tick()` runs in registration order
  2. The scheduler runs (firing any due timers)

The deliberate ordering: hardware first, callbacks second. A press
event detected during the hardware tick will arrive at the registered
gesture engine and produce its callback within the same pass. Timers
that need access to the latest hardware state see it on the next pass.

Loop pacing is via `time.sleep(tick_sleep)` between passes. The
default of 5ms is fast enough for crisp button responsiveness without
saturating the CPU. The pacing is hardware-dependent — `time` is
imported lazily inside `run()` so the engine remains importable
off-device for tests.
"""


class EventLoop:
    """Coordinator that ticks registered components and a scheduler."""

    DEFAULT_TICK_SLEEP = 0.005

    def __init__(self, scheduler, tick_sleep=None):
        self._scheduler = scheduler
        self._tickables = []
        self._tick_sleep = (
            self.DEFAULT_TICK_SLEEP if tick_sleep is None else tick_sleep
        )

    def add(self, tickable):
        """Register a tickable. Must expose `.tick()`."""
        self._tickables.append(tickable)

    def tick(self):
        """One pass: tick every component, then the scheduler."""
        for t in self._tickables:
            t.tick()
        self._scheduler.tick()

    def run(self):
        """Block forever, ticking at the configured cadence."""
        import time
        while True:
            self.tick()
            time.sleep(self._tick_sleep)
