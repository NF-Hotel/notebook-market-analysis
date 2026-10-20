# ADR-005: Notebook execution as background jobs

Status: Proposed

## Context

Benchmark and market analysis runs may take minutes because local models are slow. The API must not block, must report status, and must survive notebook failures.

## Options Considered

1. **Synchronous request**: simple, but HTTP timeouts and blocked workers.
2. **FastAPI `BackgroundTasks`**: no status tracking, tied to the request lifecycle.
3. **In-process job runner** (asyncio task + subprocess + file-backed job store).
4. **External queue (Celery/Redis, RQ)**: robust and scalable, but extra infrastructure for a local tool.

## Decision

Option 3. `POST .../runs` creates a job (`queued`), returns `202` with `job_id`. A runner executes the notebook in a subprocess (`marimo export html`) with a timeout, limited by `MAX_CONCURRENT_RUNS` and one active run per notebook (`409` otherwise). Status: `queued -> running -> completed | failed`. Clients poll `GET /runs/{job_id}`. The runner sits behind the `NotebookExecutor` and `JobStore` ports.

## Consequences

- A subprocess isolates notebook crashes and memory from the API.
- Jobs in flight are lost if the API process restarts; on startup, jobs left `queued` or `running` are marked `failed` (`interrupted`).
- Process-tree termination on timeout must work on Windows.
- Moving to a real queue later only replaces adapters.
