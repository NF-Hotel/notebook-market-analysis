"""The answer format asked from the model for one chart, and the check that an answer has it.

One answer is the text of one chart: a summary and recommendations. The service puts the summary
in an ``observation`` of the ``Insight`` of ``openapi/market-contract.yaml`` and the
recommendations in its ``improvement_suggestions``; a test keeps the formats in agreement.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.application.documents import JsonObject

MAX_RECOMMENDATIONS = 3
MAX_OVERALL_RECOMMENDATIONS = 4

# The texts are Markdown; raw HTML from a model is removed (script and style with their content,
# comments, then any other tag), because the texts are shown in a page.
_HTML_BLOCK = re.compile(
    r"<(script|style)\b[^>]*>.*?(?:</\1\s*>|\Z)|<!--.*?(?:-->|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAG = re.compile(r"</?[A-Za-z][^>]*>")
# A list item a model writes inside a line ("total. - **No Deposit**: ..."), a line marker (list
# item, numbered item, heading) and a table separator row.
_INLINE_ITEM = re.compile(r"(?<=\S)[ \t]+[-*+•][ \t]+(?=\*\*)")
_LINE_MARKER = re.compile(r"^\s*(?:[-*+•]\s+|\d+[.)]\s+|#+\s*)")
_RULE_LINE = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*$")

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


def strip_html(text: str) -> str:
    """The text without HTML tags, comments and the content of script and style elements."""
    return _HTML_TAG.sub("", _HTML_BLOCK.sub("", text))


def plain_sentences(text: str) -> str:
    """The text with list items, headings and tables written as plain sentences.

    The lines are joined, the markers ("-", "*", "1.", "#", table pipes) are dropped and bold is
    kept. A list a model writes inline ("... total. - **No Deposit**: 24.4% - **Other**: 3%") is
    split at its markers too.
    """
    pieces: list[str] = []
    for line in _INLINE_ITEM.sub("\n", text).splitlines():
        if _RULE_LINE.match(line):
            continue
        cells = [c.strip() for c in line.split("|")] if "|" in line else [line]
        piece = _LINE_MARKER.sub("", ", ".join(c for c in cells if c)).strip()
        if piece:
            pieces.append(piece if piece.endswith((".", "!", "?")) else f"{piece}.")
    return " ".join(pieces)


def parse_answer(text: str, *, plain: bool = True) -> Answer | None:
    """The answer of the model, or None when it is not JSON of ``ANSWER_SCHEMA``.

    With ``plain`` the summary and the recommendations are written as plain sentences; the
    overall interpretation keeps its headings and lists (``plain=False``).
    """
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
    shape = plain_sentences if plain else str.strip
    return Answer(
        shape(strip_html(summary)),
        strip_html(evidence),
        tuple(
            Suggestion(shape(strip_html(s.suggestion)), strip_html(s.evidence), s.sample_size)
            for s in suggestions
        ),
    )


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
