"""Streams a model answer over HTTP and enforces the time limits (shared by the two providers)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from app.application.ports.model_client import ModelFailedError, ModelRequest, ModelTimeoutError
from app.application.stream_watch import MonotonicClock, StreamWatch

_CONNECT_SECONDS = 10.0
_WRITE_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class Delta:
    """A generated token. ``text`` is a part of the answer; it is empty for a token of the
    thinking of a reasoning model, which counts as a sign of life but is not part of the answer.
    """

    text: str = ""


# Reads one line of the stream; None for a line that carries nothing (keep-alive, done marker).
LineParser = Callable[[str], Delta | None]


def stream_answer(
    url: str,
    body: dict[str, object],
    request: ModelRequest,
    parse_line: LineParser,
    clock: MonotonicClock = time.monotonic,
) -> str:
    """POST ``body`` and return the answer text assembled from the streamed lines."""
    watch = StreamWatch(request.limits, clock)
    # A silent connection is given up by the HTTP client after the stall timeout.
    read_seconds = min(request.limits.stall_seconds, request.limits.total_seconds)
    timeout = httpx.Timeout(
        connect=_CONNECT_SECONDS, read=read_seconds, write=_WRITE_SECONDS, pool=_CONNECT_SECONDS
    )
    parts: list[str] = []
    try:
        with (
            httpx.Client(timeout=timeout) as client,
            client.stream("POST", url, json=body) as response,
        ):
            if response.is_error:
                raise ModelFailedError(f"the model server answered HTTP {response.status_code}")
            for line in response.iter_lines():
                delta = parse_line(line)
                if delta is None:
                    continue
                watch.token()
                parts.append(delta.text)
    except httpx.TimeoutException as error:
        raise ModelTimeoutError(f"no data from the model server: {type(error).__name__}") from error
    except httpx.HTTPError as error:
        raise ModelFailedError(
            f"the model server could not be used: {type(error).__name__}"
        ) from error
    return "".join(parts)
