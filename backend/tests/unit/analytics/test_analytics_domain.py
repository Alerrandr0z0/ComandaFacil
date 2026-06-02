from __future__ import annotations

import datetime

import pytest

from app.analytics.domain.enums import AnalyticsPeriod
from app.analytics.domain.value_objects import DateRange


def test_analytics_period_when_day_then_has_correct_values() -> None:
    # Arrange
    period = AnalyticsPeriod.DAY

    # Assert
    assert period.value == "day"


def test_date_range_when_valid_dates_then_creates() -> None:
    # Arrange
    start = datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC)
    end = datetime.datetime(2026, 6, 2, tzinfo=datetime.UTC)

    # Act
    dr = DateRange(start=start, end=end)

    # Assert
    assert dr.start == start
    assert dr.end == end


def test_date_range_when_end_before_start_then_raises() -> None:
    # Arrange
    start = datetime.datetime(2026, 6, 2, tzinfo=datetime.UTC)
    end = datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC)

    # Act & Assert
    with pytest.raises(ValueError, match="end must be after or equal to start"):
        DateRange(start=start, end=end)
