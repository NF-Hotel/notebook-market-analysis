"""Fakes of the model port for the tests: no network, no sleep, a clock the test moves."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from typing import Any

from app.application.documents import JsonObject
from app.application.insight_prompt import CHARTS_PREFIX
from app.application.ports.model_client import ModelRequest
from app.application.stream_watch import StreamWatch

Responder = Callable[[ModelRequest], str]


class FakeMonotonicClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeModelClient:
    """A model client that answers with what ``responder`` returns and keeps every request."""

    provider = "fake"
    model = "fake-1"

    def __init__(self, responder: Responder) -> None:
        self._responder = responder
        self.requests: list[ModelRequest] = []

    def generate(self, request: ModelRequest) -> str:
        self.requests.append(request)
        return self._responder(request)


def charts_of(request: ModelRequest) -> list[dict[str, Any]]:
    """The charts that the prompt of the request lists (the model reads them the same way)."""
    for line in request.user.splitlines():
        if line.startswith(CHARTS_PREFIX):
            charts: list[dict[str, Any]] = json.loads(line.removeprefix(CHARTS_PREFIX))
            return charts
    return []


def answer_json(**changes: Any) -> str:  # noqa: ANN401 - JSON values
    """An answer about one chart; the default evidence is the first share of the test series."""
    answer: JsonObject = {
        "summary": "Shares differ between the groups.",
        "evidence": "24.7",
        "recommendations": [
            {
                "suggestion": "Look at the weakest group.",
                "evidence": "It is 15.5 here.",
                "sample_size": 80,
            }
        ],
    }
    answer.update(changes)
    return json.dumps(answer)


def well_formed_answer(request: ModelRequest) -> str:
    """A good answer about the one chart of the request, naming the first figure of its series."""
    charts = charts_of(request)
    value = charts[0]["points"][0][1] if charts else 1
    label = charts[0]["points"][0][0] if charts else "the findings"
    return answer_json(
        summary=f"{label} is the first group of the chart. It is {value} here.",
        evidence=f"{value}",
        recommendations=[
            {"suggestion": "Look at the first group.", "evidence": f"{value}", "sample_size": 10}
        ],
    )


def scripted(*answers: str | Exception) -> Responder:
    """Answers one after the other; an exception is raised instead of returned."""
    remaining = list(answers)

    def respond(request: ModelRequest) -> str:
        answer = remaining.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    return respond


def streaming(clock: FakeMonotonicClock, steps: Iterable[tuple[float, str]]) -> Responder:
    """A stream of tokens: each step waits the given seconds on the fake clock, then sends text.

    The tokens go through the same ``StreamWatch`` as the real adapters use.
    """
    plan = list(steps)

    def respond(request: ModelRequest) -> str:
        watch = StreamWatch(request.limits, clock)
        parts: list[str] = []
        for seconds, text in plan:
            clock.advance(seconds)
            watch.token()
            parts.append(text)
        return "".join(parts)

    return respond
