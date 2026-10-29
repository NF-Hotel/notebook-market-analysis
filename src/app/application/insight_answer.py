"""The answer format asked from the model, and the check that an answer has it.

The format is the ``Insight`` of ``openapi/market-contract.yaml`` without the fields the service
fills itself (status, label, provider, model, generated_at); a test keeps the two in agreement.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.application.documents import JsonObject

ANSWER_SCHEMA: JsonObject = {
    "type": "object",
    "required": ["executive_summary", "improvement_suggestions", "observations"],
    "additionalProperties": False,
    "properties": {
        "executive_summary": {"type": "string"},
        "improvement_suggestions": {
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
        "observations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["series", "text", "evidence"],
                "properties": {
                    "series": {"type": "string"},
                    "text": {"type": "string"},
                    "evidence": {"type": "string"},
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
class Observation:
    series: str
    text: str
    evidence: str


@dataclass(frozen=True, slots=True)
class Answer:
    executive_summary: str
    suggestions: tuple[Suggestion, ...]
    observations: tuple[Observation, ...]


def parse_answer(text: str) -> Answer | None:
    """The answer of the model, or None when it is not JSON of ``ANSWER_SCHEMA``."""
    try:
        data = json.loads(_without_fence(text))
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    summary = data.get("executive_summary")
    suggestions = _items(data.get("improvement_suggestions"), _suggestion)
    observations = _items(data.get("observations"), _observation)
    if not isinstance(summary, str) or suggestions is None or observations is None:
        return None
    return Answer(summary, tuple(suggestions), tuple(observations))


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


def _observation(item: Any) -> Observation | None:  # noqa: ANN401 - JSON
    if not isinstance(item, dict):
        return None
    series, text, evidence = (item.get(k) for k in ("series", "text", "evidence"))
    if not (isinstance(series, str) and isinstance(text, str) and isinstance(evidence, str)):
        return None
    return Observation(series, text, evidence)
