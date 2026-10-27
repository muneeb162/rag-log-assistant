from pathlib import Path

import pytest


@pytest.fixture
def kb_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "kb"
