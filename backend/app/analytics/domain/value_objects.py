from __future__ import annotations

import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class DateRange:
    start: datetime.datetime
    end: datetime.datetime

    def __post_init__(self) -> None:
        if self.end < self.start:
            msg = "end must be after or equal to start"
            raise ValueError(msg)
