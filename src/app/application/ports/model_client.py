"""Port: one request to a text-generating model, answered as a stream of tokens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.application.documents import JsonObject


class ModelTimeoutError(Exception):
    """The model sent no token for the stall timeout, or ran past the total limit."""


class ModelFailedError(Exception):
    """The model server is unreachable, answered with an error, or sent a broken stream."""


@dataclass(frozen=True, slots=True)
class TimeLimits:
    """Both limits of one request, in seconds.

    ``stall_seconds`` is the longest wait for a new token; ``total_seconds`` is the longest
    time of the whole request, however many tokens arrive.
    """

    stall_seconds: float
    total_seconds: float


@dataclass(frozen=True, slots=True)
class ModelRequest:
    system: str
    user: str
    schema: JsonObject
    max_output_tokens: int
    limits: TimeLimits


class ModelClient(Protocol):
    @property
    def provider(self) -> str:
        """Name of the provider, for the result (``ollama``, ``lmstudio``)."""
        ...

    @property
    def model(self) -> str: ...

    def generate(self, request: ModelRequest) -> str:
        """The answer text, constrained to ``request.schema``.

        Raises ``ModelTimeoutError`` when a limit is reached and ``ModelFailedError`` for any
        other failure.
        """
        ...
