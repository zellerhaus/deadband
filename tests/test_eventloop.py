"""Tests for deadband.eventloop.EventLoop.

The loop's `run()` method blocks forever, so it isn't tested directly.
`tick()` is the unit of work and is exercised here against fake
tickables and a real Scheduler driven by a fake clock.
"""

from deadband.eventloop import EventLoop
from deadband.timing import Scheduler


class FakeTickable:
    def __init__(self, name, log):
        self.name = name
        self.log = log

    def tick(self):
        self.log.append(self.name)


def make(clock):
    return EventLoop(Scheduler(clock.now))


# ---------------------------------------------------------------------
# tick() ordering
# ---------------------------------------------------------------------

def test_tick_calls_each_tickable_once(clock):
    loop = make(clock)
    log = []
    loop.add(FakeTickable("a", log))
    loop.add(FakeTickable("b", log))
    loop.add(FakeTickable("c", log))

    loop.tick()

    assert log == ["a", "b", "c"]


def test_tick_calls_in_registration_order(clock):
    loop = make(clock)
    log = []
    loop.add(FakeTickable("z", log))
    loop.add(FakeTickable("a", log))
    loop.add(FakeTickable("m", log))

    loop.tick()

    assert log == ["z", "a", "m"]


def test_multiple_ticks_call_each_each_time(clock):
    loop = make(clock)
    log = []
    loop.add(FakeTickable("a", log))
    loop.add(FakeTickable("b", log))

    loop.tick()
    loop.tick()
    loop.tick()

    assert log == ["a", "b", "a", "b", "a", "b"]


# ---------------------------------------------------------------------
# Scheduler integration
# ---------------------------------------------------------------------

def test_tick_invokes_scheduler(clock, rec):
    loop = make(clock)
    r = rec()
    loop._scheduler.after(0, r)

    loop.tick()

    assert r.count == 1


def test_tickables_run_before_scheduler(clock):
    """Hardware components tick first; timer callbacks see fresh state."""
    loop = make(clock)
    log = []
    loop.add(FakeTickable("hw", log))
    loop._scheduler.after(0, lambda: log.append("timer"))

    loop.tick()

    assert log == ["hw", "timer"]


def test_repeating_timer_via_loop(clock, rec):
    loop = make(clock)
    r = rec()
    loop._scheduler.every(1.0, r)

    for _ in range(3):
        clock.advance(1.0)
        loop.tick()

    assert r.count == 3


# ---------------------------------------------------------------------
# Empty loop
# ---------------------------------------------------------------------

def test_empty_loop_tick_is_noop(clock):
    loop = make(clock)
    loop.tick()  # should not raise


# ---------------------------------------------------------------------
# Tickable can register a timer mid-tick
# ---------------------------------------------------------------------

def test_tickable_can_register_delayed_timer(clock, rec):
    """A tickable that registers a future timer: the timer fires when
    clock advances past its delay, not on the registering pass."""
    loop = make(clock)
    fired = rec()

    class Registering:
        def __init__(self):
            self.done = False

        def tick(self):
            if not self.done:
                loop._scheduler.after(1.0, fired)
                self.done = True

    loop.add(Registering())

    loop.tick()
    assert fired.count == 0  # registered but not yet due

    clock.advance(1.0)
    loop.tick()
    assert fired.count == 1
