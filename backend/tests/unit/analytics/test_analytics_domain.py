from __future__ import annotations

import pytest

from app.analytics.domain.enums import AnalyticsPeriod


def test_analytics_period_when_day_then_has_correct_values() -> None:
    # Arrange
    period = AnalyticsPeriod.DAY

    # Assert
    assert period.value == "day"
