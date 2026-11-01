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
