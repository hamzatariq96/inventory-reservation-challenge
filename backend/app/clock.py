"""Time source for the service.

All business logic reads time through a Clock instead of calling datetime.now()
directly. Production uses SystemClock; tests use FixedClock so that expiry
behaviour is exact and never depends on how fast the test machine is.

Timestamps are naive UTC throughout, which keeps comparisons identical on
PostgreSQL and SQLite.
"""

from datetime import datetime, timedelta, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)


class FixedClock:
    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs: float) -> None:
        self._now += timedelta(**kwargs)
