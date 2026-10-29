"""Ollama: ``POST {base}/api/chat`` with a newline-delimited JSON stream."""

from __future__ import annotations

import json
import time

from app.adapters.ai.streaming import Delta, stream_answer
from app.application.ports.model_client import ModelFailedError, ModelRequest
from app.application.stream_watch import MonotonicClock


def _parse_line(line: str) -> Delta | None:
    if not line.strip():
        return None
    try:
        data = json.loads(line)
    except ValueError:
        raise ModelFailedError("Ollama sent a line that is not JSON") from None
    if not isinstance(data, dict):
        raise ModelFailedError("Ollama sent a line that is not an object")
    if data.get("error"):
        raise ModelFailedError("Ollama reported an error")
    message = data.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    text = content if isinstance(content, str) else ""
    thinking = message.get("thinking")
    is_token = bool(text) or (isinstance(thinking, str) and bool(thinking))
    return Delta(text) if is_token else None


class OllamaModelClient:
    provider = "ollama"

    def __init__(self, base_url: str, model: str, clock: MonotonicClock = time.monotonic) -> None:
        self._url = f"{base_url.rstrip('/')}/api/chat"
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
            "format": request.schema,
            "options": {"num_predict": request.max_output_tokens},
        }
        return stream_answer(self._url, body, request, _parse_line, self._clock)
