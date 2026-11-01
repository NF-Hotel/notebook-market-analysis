from pathlib import Path
from typing import Any

import pytest
import yaml

from app.application.insight_answer import ANSWER_SCHEMA, parse_answer, plain_sentences, strip_html
from tests.unit.ai_fakes import answer_json

CONTRACT = Path(__file__).parents[3] / "openapi" / "market-contract.yaml"
SERVICE_FIELDS = {"status", "reason", "label", "provider", "model", "generated_at"}


def _contract_insight() -> dict[str, Any]:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    insight: dict[str, Any] = contract["components"]["schemas"]["Insight"]
    return insight


def _without_descriptions(node: Any) -> Any:  # noqa: ANN401 - schema tree
    if isinstance(node, dict):
        return {k: _without_descriptions(v) for k, v in node.items() if k != "description"}
    return node


def test_the_answer_schema_agrees_with_the_insight_of_the_contract() -> None:
    properties = _contract_insight()["properties"]
    suggestion = _without_descriptions(properties["improvement_suggestions"]["items"])
    observation = properties["observations"]["items"]["properties"]
    asked = ANSWER_SCHEMA["properties"]["recommendations"]["items"]
    # The service adds the chart (`series`) to each recommendation and to the observation.
    assert set(suggestion["properties"]) - {"series"} == set(asked["properties"])
    assert {k: v for k, v in suggestion["properties"].items() if k != "series"} == asked[
        "properties"
    ]
    assert suggestion["required"] == asked["required"]
    assert {"text", "evidence"} <= set(observation)
    assert ANSWER_SCHEMA["properties"]["summary"] == {"type": "string"}
    assert ANSWER_SCHEMA["properties"]["evidence"] == {"type": "string"}
    assert set(ANSWER_SCHEMA["required"]) == {"summary", "evidence", "recommendations"}


def test_a_well_formed_answer_is_parsed() -> None:
    answer = parse_answer(answer_json())
    assert answer is not None
    assert answer.summary == "Shares differ between the groups."
    assert answer.evidence == "24.7"
    assert answer.suggestions[0].sample_size == 80


def test_a_fenced_answer_is_parsed() -> None:
    assert parse_answer(f"```json\n{answer_json()}\n```") is not None


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not json",
        "[]",
        '{"summary": 1, "evidence": "1", "recommendations": []}',
        '{"summary": "x", "recommendations": []}',
        '{"summary": "x", "evidence": 1, "recommendations": []}',
        '{"summary": "x", "evidence": "1", "recommendations": [1]}',
        '{"summary": "x", "evidence": "1",'
        ' "recommendations": [{"suggestion": "s", "evidence": "e", "sample_size": "3"}]}',
        '{"summary": "x", "evidence": "1",'
        ' "recommendations": [{"suggestion": "s", "evidence": "e", "sample_size": true}]}',
    ],
)
def test_an_answer_that_is_not_of_the_schema_is_not_parsed(text: str) -> None:
    assert parse_answer(text) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Plain **24.7%** sentence.", "Plain **24.7%** sentence."),
        ("Lead.\n- **A**: 1\n* **B**: 2\n3. C", "Lead. **A**: 1. **B**: 2. C."),
        ("# Heading\nText.", "Heading. Text."),
        (
            "total. - **No Deposit**: 24.4% - **Non Refund**: 1%",
            "total. **No Deposit**: 24.4%. **Non Refund**: 1%.",
        ),
        ("| a | b |\n|---|---|\n| 1 | 2 |", "a, b. 1, 2."),
        ("Rises by -5 points.", "Rises by -5 points."),
    ],
)
def test_plain_sentences_turns_lists_headings_and_tables_into_sentences_and_keeps_bold(
    text: str, expected: str
) -> None:
    assert plain_sentences(text) == expected


def test_parse_answer_keeps_the_structure_of_the_overall_text_when_not_plain() -> None:
    text = answer_json(summary="## Key points\n- a")
    answer = parse_answer(text, plain=False)
    assert answer is not None
    assert answer.summary == "## Key points\n- a"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("<script>alert(1)</script>Hello", "Hello"),
        ("<SCRIPT src=x>unclosed", ""),
        ("a <b>bold</b> <!-- note --> word", "a bold  word"),
        ("share < 5 and 3 > 2", "share < 5 and 3 > 2"),
        ("- **Bold** list", "- **Bold** list"),
    ],
)
def test_strip_html_removes_tags_scripts_and_comments_and_keeps_markdown(
    text: str, expected: str
) -> None:
    assert strip_html(text) == expected
