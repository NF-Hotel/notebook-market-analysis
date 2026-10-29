from pathlib import Path
from typing import Any

import pytest
import yaml

from app.application.insight_answer import ANSWER_SCHEMA, parse_answer
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
    asked = {k: v for k, v in properties.items() if k not in SERVICE_FIELDS}
    assert set(ANSWER_SCHEMA["properties"]) == set(asked)
    for name in ("improvement_suggestions", "observations"):
        assert ANSWER_SCHEMA["properties"][name] == _without_descriptions(asked[name])
    assert ANSWER_SCHEMA["properties"]["executive_summary"] == {"type": "string"}
    assert asked["executive_summary"]["type"] == ["string", "null"]
    assert set(ANSWER_SCHEMA["required"]) == set(asked)


def test_a_well_formed_answer_is_parsed() -> None:
    answer = parse_answer(
        answer_json(observations=[{"series": "a.groups", "text": "t", "evidence": "1"}])
    )
    assert answer is not None
    assert answer.executive_summary == "Shares differ between the groups."
    assert answer.suggestions[0].sample_size == 80
    assert answer.observations[0].series == "a.groups"


def test_a_fenced_answer_is_parsed() -> None:
    assert parse_answer(f"```json\n{answer_json()}\n```") is not None


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not json",
        "[]",
        '{"executive_summary": 1, "improvement_suggestions": [], "observations": []}',
        '{"executive_summary": "x", "observations": []}',
        '{"executive_summary": "x", "improvement_suggestions": [], "observations": [1]}',
        '{"executive_summary": "x", "observations": [],'
        ' "improvement_suggestions": [{"suggestion": "s", "evidence": "e", "sample_size": "3"}]}',
        '{"executive_summary": "x", "observations": [],'
        ' "improvement_suggestions": [{"suggestion": "s", "evidence": "e", "sample_size": true}]}',
        '{"executive_summary": "x", "improvement_suggestions": [],'
        ' "observations": [{"series": "a", "text": "t"}]}',
    ],
)
def test_an_answer_that_is_not_of_the_schema_is_not_parsed(text: str) -> None:
    assert parse_answer(text) is None
