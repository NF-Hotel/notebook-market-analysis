import json
from collections.abc import Callable
from datetime import date

from app.application.ports.model_client import ModelFailedError, ModelRequest, TimeLimits
from app.application.price_explanations import (
    PriceExplainer,
    broken_idea_rule,
    broken_rule,
    fallback_text,
)
from app.domain.analyses.price_history import YearHistory
from app.domain.analyses.price_suggestions import PriceSuggestion
from tests.unit.ai_fakes import FakeModelClient

LIMITS = TimeLimits(1.0, 2.0)
GOOD = "Christmas Day was 85 % full in 2024 and 2025, above 80 %, so a surcharge of 20 % fits."


def suggestion() -> PriceSuggestion:
    return PriceSuggestion(
        "all",
        date(2026, 12, 25),
        date(2026, 12, 25),
        "surcharge",
        "20",
        "holiday",
        "Christmas Day",
        "0.80",
        (YearHistory(2024, 17, 20), YearHistory(2025, 17, 20)),
    )


def explainer(responder: Callable[[ModelRequest], str]) -> tuple[PriceExplainer, FakeModelClient]:
    client = FakeModelClient(responder)
    return PriceExplainer(client, LIMITS, 1000), client


def text_answer(text: str) -> str:
    return json.dumps({"text": text})


def test_with_no_model_the_text_is_built_from_the_figures_and_not_marked_as_ai() -> None:
    result = PriceExplainer(None, LIMITS, 1000).explain(suggestion())
    assert result["ai_written"] is False
    assert "85 %" in result["text"]
    assert "surcharge of 20 %" in result["text"]
    assert "2026-12-25" in result["text"]


def test_a_good_answer_is_kept_and_marked_as_written_by_an_ai() -> None:
    sut, client = explainer(lambda request: text_answer(GOOD))
    assert sut.explain(suggestion()) == {"text": GOOD, "ai_written": True}
    assert len(client.requests) == 1


def test_an_answer_with_a_price_is_asked_for_again_with_the_rule_it_broke() -> None:
    answers = iter([text_answer("A surcharge to 1200 kr fits."), text_answer(GOOD)])
    sut, client = explainer(lambda request: next(answers))
    assert sut.explain(suggestion())["ai_written"] is True
    assert len(client.requests) == 2
    assert "currency or a price" in client.requests[1].user


def test_two_rejected_answers_give_the_text_from_the_figures() -> None:
    sut, client = explainer(lambda request: text_answer("Add 30 % to the rate."))
    result = sut.explain(suggestion())
    assert result["ai_written"] is False
    assert result["text"] == fallback_text(suggestion())["text"]
    assert len(client.requests) == 2


def test_a_failed_model_gives_the_text_from_the_figures() -> None:
    def fail(request: ModelRequest) -> str:
        raise ModelFailedError

    assert explainer(fail)[0].explain(suggestion())["ai_written"] is False


def test_a_number_that_is_not_one_of_the_suggestions_is_rejected() -> None:
    assert broken_rule("Raise it by 30 %.", suggestion()) is not None
    assert broken_rule("Raise it by 20 %, as in 2024.", suggestion()) is None


def test_a_month_that_is_not_in_the_period_is_rejected() -> None:
    assert broken_rule("It was busy in March.", suggestion()) is not None
    assert broken_rule("It was busy in December.", suggestion()) is None


def test_a_cause_or_a_promise_is_rejected() -> None:
    assert broken_rule("Demand will increase because of the holiday.", suggestion()) is not None


def test_an_empty_answer_gives_the_text_from_the_figures() -> None:
    assert (
        explainer(lambda request: text_answer("  "))[0].explain(suggestion())["ai_written"] is False
    )


def test_the_explainer_changes_nothing_of_the_suggestion() -> None:
    before = suggestion()
    explainer(lambda request: text_answer(GOOD))[0].explain(before)
    assert before == suggestion()


def test_ideas_are_kept_when_they_carry_no_number_and_at_most_three() -> None:
    ideas = [
        "Offer a breakfast package.",
        "Ask for two nights at least.",
        "Send a note to guests.",
        "A fourth.",
    ]
    sut, _ = explainer(lambda request: json.dumps({"ideas": ideas}))
    result = sut.ideas([suggestion()])
    assert [i["text"] for i in result] == ideas[:3]
    assert all(i["ai_written"] is True for i in result)


def test_an_idea_with_a_number_or_a_price_is_dropped() -> None:
    ideas = ["Offer a package for 99 euro.", "Give 10 % off.", "Offer a breakfast package."]
    sut, _ = explainer(lambda request: json.dumps({"ideas": ideas}))
    assert [i["text"] for i in sut.ideas([suggestion()])] == ["Offer a breakfast package."]
    assert broken_idea_rule("Give a discount in spring.") is None
    assert broken_idea_rule("Because of demand, raise it.") is not None


def test_with_no_model_or_no_suggestions_there_are_no_ideas() -> None:
    assert PriceExplainer(None, LIMITS, 1000).ideas([suggestion()]) == []
    assert explainer(lambda request: "{}")[0].ideas([]) == []


def test_a_broken_answer_gives_no_ideas() -> None:
    assert explainer(lambda request: "not json")[0].ideas([suggestion()]) == []
