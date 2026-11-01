"""The answer format asked from the model for one chart, and the check that an answer has it.

One answer is the text of one chart: a summary and recommendations. The service puts the summary
in an ``observation`` of the ``Insight`` of ``openapi/market-contract.yaml`` and the
recommendations in its ``improvement_suggestions``; a test keeps the formats in agreement.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.application.documents import JsonObject

MAX_RECOMMENDATIONS = 3

ANSWER_SCHEMA: JsonObject = {
    "type": "object",
    "required": ["summary", "evidence", "recommendations"],
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "evidence": {"type": "string"},
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["suggestion", "evidence", "sample_size"],
                "properties": {
                    "suggestion": {"type": "string"},
                    "evidence": {"type": "string"},
                    "sample_size": {"type": "integer"},
                },
            },
        },
    },
}


@dataclass(frozen=True, slots=True)
class Suggestion:
    suggestion: str
    evidence: str
    sample_size: int


@dataclass(frozen=True, slots=True)
class Answer:
    summary: str
    evidence: str
    suggestions: tuple[Suggestion, ...]


def parse_answer(text: str) -> Answer | None:
    """The answer of the model, or None when it is not JSON of ``ANSWER_SCHEMA``."""
    try:
        data = json.loads(_without_fence(text))
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    summary, evidence = data.get("summary"), data.get("evidence")
    suggestions = _items(data.get("recommendations"), _suggestion)
    if not isinstance(summary, str) or not isinstance(evidence, str) or suggestions is None:
        return None
    return Answer(summary, evidence, tuple(suggestions))


def _without_fence(text: str) -> str:
    """Some models wrap the JSON in a markdown fence even when told not to."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else ""
        stripped = stripped.removesuffix("```")
    return stripped.strip()


def _items[T](value: object, build: Callable[[Any], T | None]) -> list[T] | None:
    if not isinstance(value, list):
        return None
    built: list[T] = []
    for item in value:
        entry = build(item)
        if entry is None:
            return None
        built.append(entry)
    return built


def _suggestion(item: Any) -> Suggestion | None:  # noqa: ANN401 - JSON
    if not isinstance(item, dict):
        return None
    suggestion, evidence, size = (item.get(k) for k in ("suggestion", "evidence", "sample_size"))
    if not isinstance(suggestion, str) or not isinstance(evidence, str):
        return None
    if isinstance(size, bool) or not isinstance(size, int):
        return None
    return Suggestion(suggestion, evidence, size)
