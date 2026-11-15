"""The service of ``deploy/docker-compose.yml`` as the tests read it."""

import re
from pathlib import Path
from typing import Any

import yaml

COMPOSE = Path(__file__).parents[2] / "deploy" / "docker-compose.yml"
SERVICE = "market-analysis-api"
# Docker Compose counts the units of a byte value in steps of 1,024.
BYTE_UNITS = {"b": 1, "k": 1024, "m": 1024**2, "g": 1024**3}


def compose_service() -> dict[str, Any]:
    """The settings of the service in the compose file."""
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    service: dict[str, Any] = compose["services"][SERVICE]
    return service


def mem_limit_bytes() -> int:
    """The ``mem_limit`` of the service, in bytes."""
    limit = str(compose_service()["mem_limit"]).strip().lower()
    found = re.fullmatch(r"(\d+)([bkmg])b?", limit)
    if found is None:
        raise ValueError(f"mem_limit {limit!r} is not a whole number of b, k, m or g")
    return int(found[1]) * BYTE_UNITS[found[2]]
