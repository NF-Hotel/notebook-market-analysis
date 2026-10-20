"""The routes of the service match the paths of openapi/market-contract.yaml."""

from pathlib import Path

import yaml

from app.infrastructure.config import Settings
from app.infrastructure.main import build_app

CONTRACT = Path(__file__).parents[2] / "openapi" / "market-contract.yaml"


def test_every_contract_path_is_a_route() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    app = build_app(Settings(_env_file=None, data_source="csv"))
    served = app.openapi()["paths"]
    for path, operations in contract["paths"].items():
        for method in operations:
            assert method in served[path]
