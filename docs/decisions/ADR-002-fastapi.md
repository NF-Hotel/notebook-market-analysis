# ADR-002: FastAPI as web framework

Status: Proposed

## Context

We need a Python HTTP API with request/response validation, generated documentation, async support for background jobs, and easy testing.

## Options Considered

1. **FastAPI**: Pydantic validation, automatic OpenAPI, async, dependency injection, `TestClient`.
2. **Flask**: simple, but validation, async and OpenAPI need extra libraries.
3. **Django REST Framework**: heavy for a small service with no relational model.

## Decision

FastAPI with Uvicorn. Pydantic models live in the API adapter only; they are not used in `domain` or `application`.

## Consequences

- OpenAPI docs come for free and must match `docs/api.md`.
- FastAPI types stay in `adapters/api`; use cases remain framework-free.
- Background execution is our own runner, not FastAPI `BackgroundTasks` (see ADR-005).
