"""Configuración común de pytest."""

from pathlib import Path

import pytest


@pytest.fixture
def raiz_proyecto() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def raiz_skills(raiz_proyecto: Path) -> Path:
    return raiz_proyecto / "skills"
