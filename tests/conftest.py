import os
from collections.abc import Iterator

import pytest

from app.infrastructure.config import Settings
from app.infrastructure.logging import clear_context

_SETTING_VARS = {name.upper() for name in Settings.model_fields}


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Remove every configuration variable so tests never see the developer's environment."""
    for name in list(os.environ):
        if name.upper() in _SETTING_VARS:
            monkeypatch.delenv(name)
    clear_context()
    yield
    clear_context()
