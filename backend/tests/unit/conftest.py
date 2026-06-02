import pytest

from app.settings import Settings, get_settings


@pytest.fixture
def settings() -> Settings:
    return get_settings()
