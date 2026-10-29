"""LM Studio: OpenAI-compatible ``POST {base}/v1/chat/completions`` with a server-sent stream."""

from __future__ import annotations

import json
import time

from app.adapters.ai.streaming import Delta, stream_answer
from app.application.ports.model_client import ModelFailedError, ModelRequest
from app.application.stream_watch import MonotonicClock

_DATA = "data:"
_DONE = "[DONE]"
_SCHEMA_NAME = "insight"


def _parse_line(line: str) -> Delta | None:
    if not line.startswith(_DATA):
        return None  # a comment, an event name or an empty line between events
    payload = line.removeprefix(_DATA).strip()
    if not payload or payload == _DONE:
        return None
    try:
        data = json.loads(payload)
    except ValueError:
        raise ModelFailedError("LM Studio sent an event that is not JSON") from None
    if not isinstance(data, dict):
        raise ModelFailedError("LM Studio sent an event that is not an object")
    if data.get("error"):
        raise ModelFailedError("LM Studio reported an error")
    choices = data.get("choices")
    delta = choices[0].get("delta") if isinstance(choices, list) and choices else None
    if not isinstance(delta, dict):
        return None
    content = delta.get("content")
    text = content if isinstance(content, str) else ""
    reasoning = delta.get("reasoning_content") or delta.get("reasoning")
    is_token = bool(text) or (isinstance(reasoning, str) and bool(reasoning))
    return Delta(text) if is_token else None


class LMStudioModelClient:
    provider = "lmstudio"

    def __init__(self, base_url: str, model: str, clock: MonotonicClock = time.monotonic) -> None:
        self._url = f"{base_url.rstrip('/')}/v1/chat/completions"
        self._model = model
        self._clock = clock

    @property
    def model(self) -> str:
        return self._model

    def generate(self, request: ModelRequest) -> str:
        body: dict[str, object] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            "stream": True,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": _SCHEMA_NAME, "strict": True, "schema": request.schema},
            },
            "max_tokens": request.max_output_tokens,
        }
        return stream_answer(self._url, body, request, _parse_line, self._clock)
