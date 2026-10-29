import json
from collections.abc import Iterator

import httpx
import pytest
import respx

from app.adapters.ai.lm_studio import LMStudioModelClient
from app.application.ports.model_client import (
    ModelFailedError,
    ModelRequest,
    ModelTimeoutError,
    TimeLimits,
)
from tests.unit.ai_fakes import FakeMonotonicClock

URL = "http://lms.test:1234/v1/chat/completions"
SCHEMA = {"type": "object", "properties": {"executive_summary": {"type": "string"}}}
LIMITS = TimeLimits(stall_seconds=600, total_seconds=14400)


def _request(limits: TimeLimits = LIMITS) -> ModelRequest:
    return ModelRequest("be careful", "the figures", SCHEMA, 32768, limits)


def _event(content: str = "", reasoning: str = "") -> bytes:
    delta: dict[str, str] = {"content": content}
    if reasoning:
        delta["reasoning_content"] = reasoning
    return b"data: " + json.dumps({"choices": [{"delta": delta}]}).encode() + b"\n\n"


DONE = b"data: [DONE]\n\n"


def _client(clock: FakeMonotonicClock | None = None) -> LMStudioModelClient:
    return LMStudioModelClient("http://lms.test:1234/", "qwen", clock or FakeMonotonicClock())


@respx.mock
def test_the_request_is_a_streamed_completion_with_the_json_schema_and_the_output_limit() -> None:
    route = respx.post(URL).mock(return_value=httpx.Response(200, content=_event("{}") + DONE))
    _client().generate(_request())
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "model": "qwen",
        "messages": [
            {"role": "system", "content": "be careful"},
            {"role": "user", "content": "the figures"},
        ],
        "stream": True,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "insight", "strict": True, "schema": SCHEMA},
        },
        "max_tokens": 32768,
    }


@respx.mock
def test_the_answer_is_assembled_from_the_server_sent_events() -> None:
    stream = b": keep-alive\n\n" + _event('{"executive_') + _event('summary": "x"}') + DONE
    respx.post(URL).mock(return_value=httpx.Response(200, content=stream))
    assert _client().generate(_request()) == '{"executive_summary": "x"}'


@respx.mock
def test_the_reasoning_of_a_model_is_not_part_of_the_answer_but_counts_as_a_token() -> None:
    clock = FakeMonotonicClock()

    def stream() -> Iterator[bytes]:
        for _ in range(5):
            clock.advance(400)
            yield _event(reasoning="hmm")
        yield _event("{}")
        yield DONE

    respx.post(URL).mock(return_value=httpx.Response(200, content=stream()))
    assert _client(clock).generate(_request()) == "{}"


@respx.mock
def test_a_stream_that_stalls_between_tokens_is_given_up() -> None:
    clock = FakeMonotonicClock()

    def stream() -> Iterator[bytes]:
        yield _event("{")
        clock.advance(LIMITS.stall_seconds)
        yield _event("}")

    respx.post(URL).mock(return_value=httpx.Response(200, content=stream()))
    with pytest.raises(ModelTimeoutError):
        _client(clock).generate(_request())


@respx.mock
def test_a_stream_that_keeps_sending_tokens_is_given_up_at_the_total_limit() -> None:
    clock = FakeMonotonicClock()
    limits = TimeLimits(stall_seconds=600, total_seconds=1000)

    def stream() -> Iterator[bytes]:
        for _ in range(20):
            clock.advance(100)
            yield _event(" ")

    respx.post(URL).mock(return_value=httpx.Response(200, content=stream()))
    with pytest.raises(ModelTimeoutError):
        _client(clock).generate(_request(limits))


@respx.mock
def test_a_silent_connection_is_given_up_by_the_read_timeout() -> None:
    respx.post(URL).mock(side_effect=httpx.ReadTimeout("no data"))
    with pytest.raises(ModelTimeoutError):
        _client().generate(_request())


@respx.mock
def test_a_server_that_cannot_be_reached_is_a_model_failure() -> None:
    respx.post(URL).mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(ModelFailedError):
        _client().generate(_request())


@respx.mock
def test_an_http_error_is_a_model_failure() -> None:
    respx.post(URL).mock(return_value=httpx.Response(500, text="oops"))
    with pytest.raises(ModelFailedError, match="500"):
        _client().generate(_request())


@respx.mock
def test_an_error_event_is_a_model_failure() -> None:
    respx.post(URL).mock(return_value=httpx.Response(200, content=b'data: {"error": "boom"}\n\n'))
    with pytest.raises(ModelFailedError):
        _client().generate(_request())


@respx.mock
def test_an_event_that_is_not_json_is_a_model_failure() -> None:
    respx.post(URL).mock(return_value=httpx.Response(200, content=b"data: nope\n\n"))
    with pytest.raises(ModelFailedError):
        _client().generate(_request())


def test_the_client_names_its_provider_and_model() -> None:
    client = _client()
    assert (client.provider, client.model) == ("lmstudio", "qwen")
