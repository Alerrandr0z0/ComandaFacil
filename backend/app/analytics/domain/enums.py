from __future__ import annotations

from enum import Enum


class AnalyticsPeriod(Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    CUSTOM = "custom"
