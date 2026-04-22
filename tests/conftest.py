"""Shared pytest fixtures: fake clock + callback recorder."""

import pytest


class FakeClock:
    """Manual clock for deterministic gesture timing tests."""

    def __init__(self, start=0.0):
        self.t = start

    def now(self):
        return self.t

    def advance(self, dt):
        self.t += dt


class Recorder:
    """Captures callback invocations for assertion. Instances are callable.

    Each call records its args as a tuple; a zero-arg call records ().
    """

    def __init__(self, name=None):
        self.name = name
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)

    @property
    def count(self):
        return len(self.calls)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def rec():
    """Factory for named recorders: `r_click = rec('click')`."""
    def _make(name=None):
        return Recorder(name)
    return _make
