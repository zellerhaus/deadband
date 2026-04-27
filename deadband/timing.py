"""Timing and scheduling — pure-Python.

`Timer` is a cancellable handle returned by the scheduler.

`Scheduler` supports one-shot timers via `after()` and repeating
timers via `every()`. The wrapping `Deadband` class will expose these
as `db.after()`, `db.every()`, and `db.on_tick()` (an alias for
`every` with named semantics).

Cancellation rules (per spec design decision #7):

  - A one-shot timer that has already fired: cancel is a no-op
  - A repeating timer cancelled during its own callback: stops future
    invocations but does not interrupt the current one
  - A timer cancelled before firing: never fires

Drift behavior: if the main loop falls behind and `tick()` is called
much later than expected, a repeating timer fires once per `tick()` and
its next fire is rescheduled past `now`. Missed fires are skipped, not
caught up. This avoids a thundering herd of callbacks if the device
is briefly busy.
"""


class Timer:
    """Cancellable handle to a scheduled timer.

    Created and managed by `Scheduler`; callers should not instantiate
    directly.
    """

    def __init__(self):
        self._active = True

    def cancel(self):
        """Cancel the timer. No-op if it has already fired or been cancelled."""
        self._active = False

    @property
    def is_active(self):
        """True if the timer is still scheduled."""
        return self._active


class Scheduler:
    """Pure-Python scheduler for one-shot and repeating timers.

    Time is injected via `now_fn` (a callable returning seconds as
    float). On device this is `lambda: supervisor.ticks_ms() / 1000`;
    in tests it is a fake clock.

    Call `tick()` from the main loop to fire any due timers.
    """

    DEFAULT_TICK_INTERVAL = 0.1

    def __init__(self, now_fn):
        self._now = now_fn
        # Each entry is [fire_at, timer, fn, interval_or_None].
        # Lists (not tuples) so fire_at can be mutated in place when a
        # repeating timer is rescheduled.
        self._timers = []

    def after(self, delay, fn):
        """Schedule `fn` to fire once after `delay` seconds.

        Returns a `Timer` handle that can be cancelled.
        """
        timer = Timer()
        self._timers.append([self._now() + delay, timer, fn, None])
        return timer

    def every(self, interval, fn):
        """Schedule `fn` to fire repeatedly every `interval` seconds.

        First fire is `interval` seconds after this call. Returns a
        `Timer` handle that can be cancelled.
        """
        timer = Timer()
        self._timers.append([self._now() + interval, timer, fn, interval])
        return timer

    def on_tick(self, fn, interval=None):
        """Alias for `every` with named-interval ergonomics.

        Default interval is 0.1 seconds.
        """
        if interval is None:
            interval = self.DEFAULT_TICK_INTERVAL
        return self.every(interval, fn)

    def tick(self):
        """Fire any due timers. Call from the main loop."""
        now = self._now()

        # Snapshot the list of due entries before firing. Callbacks may
        # add new timers (which land in self._timers but are not in this
        # snapshot, so they fire on the next tick at earliest) or cancel
        # other timers (which we re-check before firing).
        due = [e for e in self._timers if e[1].is_active and e[0] <= now]

        for entry in due:
            fire_at, timer, fn, interval = entry
            if not timer.is_active:
                # Cancelled by an earlier callback in this same tick.
                continue
            fn()
            if interval is None:
                # One-shot.
                timer._active = False
            elif timer.is_active:
                # Repeating, still active. Advance fire_at past now,
                # skipping any missed fires.
                next_fire = fire_at + interval
                while next_fire <= now:
                    next_fire += interval
                entry[0] = next_fire
            # else: cancelled during its own fire; will be pruned below.

        # Prune cancelled and one-shot-fired timers.
        self._timers = [e for e in self._timers if e[1].is_active]
