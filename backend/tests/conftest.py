# Global test configuration.
# Unit tests have their own conftest at tests/unit/conftest.py
# Integration tests have their own conftest at tests/integration/conftest.py

import app.dependencies


def mock_require_permission(action: str):
    async def dummy_dependency() -> None:
        return None

    return dummy_dependency


app.dependencies.require_permission = mock_require_permission
