import json
from collections.abc import Iterator

import httpx
import pytest
import respx

from app.adapters.ai.ollama import OllamaModelClient
from app.application.ports.model_client import (
    ModelFailedError,
    ModelRequest,
    ModelTimeoutError,
    TimeLimits,
)
from tests.unit.ai_fakes import FakeMonotonicClock

URL = "http://ollama.test:11434/api/chat"
SCHEMA = {"type": "object", "properties": {"executive_summary": {"type": "string"}}}
LIMITS = TimeLimits(stall_seconds=600, total_seconds=14400)


def _request(limits: TimeLimits = LIMITS) -> ModelRequest:
    return ModelRequest("be careful", "the figures", SCHEMA, 32768, limits)


def _line(content: str = "", thinking: str = "", done: bool = False) -> bytes:
    message = {"role": "assistant", "content": content}
    if thinking:
        message["thinking"] = thinking
    return json.dumps({"model": "m", "message": message, "done": done}).encode() + b"\n"


def _client(clock: FakeMonotonicClock | None = None) -> OllamaModelClient:
    return OllamaModelClient("http://ollama.test:11434/", "phi", clock or FakeMonotonicClock())


@respx.mock
def test_the_request_is_a_streamed_chat_with_the_schema_and_the_output_limit() -> None:
    route = respx.post(URL).mock(return_value=httpx.Response(200, content=_line("{}", done=True)))
    _client().generate(_request())
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "model": "phi",
        "messages": [
            {"role": "system", "content": "be careful"},
            {"role": "user", "content": "the figures"},
        ],
        "stream": True,
        "format": SCHEMA,
        "options": {"num_predict": 32768},
    }


@respx.mock
def test_the_answer_is_assembled_from_the_streamed_lines() -> None:
    stream = [_line('{"executive_'), _line('summary": "x"}'), _line(done=True)]
    respx.post(URL).mock(return_value=httpx.Response(200, content=iter(stream)))
    assert _client().generate(_request()) == '{"executive_summary": "x"}'


@respx.mock
def test_the_thinking_of_a_reasoning_model_is_not_part_of_the_answer() -> None:
    stream = [_line(thinking="hmm"), _line(thinking="ok"), _line("{}"), _line(done=True)]
    respx.post(URL).mock(return_value=httpx.Response(200, content=iter(stream)))
    assert _client().generate(_request()) == "{}"


@respx.mock
def test_the_thinking_counts_as_a_token_for_the_stall_timeout() -> None:
    clock = FakeMonotonicClock()

    def stream() -> Iterator[bytes]:
        for _ in range(5):  # 5 x 400 s of thinking: more than the stall timeout in all
            clock.advance(400)
            yield _line(thinking="hmm")
        yield _line("{}")

    respx.post(URL).mock(return_value=httpx.Response(200, content=stream()))
    assert _client(clock).generate(_request()) == "{}"


@respx.mock
def test_a_stream_that_stalls_between_tokens_is_given_up() -> None:
    clock = FakeMonotonicClock()

    def stream() -> Iterator[bytes]:
        yield _line("{")
        clock.advance(LIMITS.stall_seconds)
        yield _line("}")

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
            yield _line(" ")

    respx.post(URL).mock(return_value=httpx.Response(200, content=stream()))
    with pytest.raises(ModelTimeoutError):
        _client(clock).generate(_request(limits))


@respx.mock
def test_a_silent_connection_is_given_up_by_the_read_timeout() -> None:
    route = respx.post(URL).mock(side_effect=httpx.ReadTimeout("no data"))
    with pytest.raises(ModelTimeoutError):
        _client().generate(_request())
    assert route.call_count == 1


@respx.mock
def test_the_read_timeout_of_the_connection_is_the_stall_timeout() -> None:
    route = respx.post(URL).mock(return_value=httpx.Response(200, content=_line("{}")))
    _client().generate(_request(TimeLimits(stall_seconds=45, total_seconds=900)))
    assert route.calls.last.request.extensions["timeout"]["read"] == 45


@respx.mock
def test_a_server_that_cannot_be_reached_is_a_model_failure() -> None:
    respx.post(URL).mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(ModelFailedError):
        _client().generate(_request())


@respx.mock
def test_an_http_error_is_a_model_failure() -> None:
    respx.post(URL).mock(return_value=httpx.Response(404, json={"error": "model not found"}))
    with pytest.raises(ModelFailedError, match="404"):
        _client().generate(_request())


@respx.mock
def test_an_error_line_in_the_stream_is_a_model_failure() -> None:
    respx.post(URL).mock(return_value=httpx.Response(200, content=b'{"error": "boom"}\n'))
    with pytest.raises(ModelFailedError):
        _client().generate(_request())


@respx.mock
def test_a_line_that_is_not_json_is_a_model_failure() -> None:
    respx.post(URL).mock(return_value=httpx.Response(200, content=b"<html>\n"))
    with pytest.raises(ModelFailedError):
        _client().generate(_request())


def test_the_client_names_its_provider_and_model() -> None:
    client = _client()
    assert (client.provider, client.model) == ("ollama", "phi")
