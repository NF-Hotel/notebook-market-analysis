"""The routes of the service match the paths of openapi/market-contract.yaml."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from app.infrastructure.config import Settings
from app.infrastructure.main import build_app

CONTRACT = Path(__file__).parents[2] / "openapi" / "market-contract.yaml"


def _load_contract_paths() -> dict[str, Any]:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    paths: dict[str, Any] = contract["paths"]
    return paths


@pytest.mark.parametrize("path", _load_contract_paths())
def test_every_contract_path_is_a_route(path: str) -> None:
    operations = _load_contract_paths()[path]
    app = build_app(Settings(_env_file=None, data_source="csv"))
    served = app.openapi()["paths"]
    for method in operations:
        assert method in served[path]
