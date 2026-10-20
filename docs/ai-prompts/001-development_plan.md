# Development plan (Section 1: no code yet)

## 1. What the system does

A locally run analysis platform for hotel and market data. Two Marimo notebooks hold the analysis, and a FastAPI service runs them as jobs and serves the results.

Benchmark notebook: runs a fixed prompt set against the configured local models and records latency, tokens per second, success rate and quality checks. The output tells us which local model to use.

Market analysis notebook: loads market data, computes the analysis, and uses a local model for narrative and insight text.

API: runs registered notebooks as background jobs and returns results as JSON or PDF.

## 2. Two projects, one repo

Both live in a single repo with one shared src/ package. Splitting them into two repos would force a published shared library, which is too much overhead here.

### Part	Responsibility

notebooks/	Thin UI and orchestration. They call the application layer and contain no business logic.
src/	All logic: domain, use cases, AI providers, runner, API, reports.

Communication: the API never imports notebook code. The runner starts a notebook as a subprocess. The notebook writes result.json and meta.json into output/<job_id>/. The API reads only those files.

## 3. Proposed structure (differs from your draft)

Your draft has api/ notebooks/ services/ ai/. That layering puts the AI providers and reports at the same level as the API, so nothing enforces dependency direction. It also conflicts with the python-developer agent's rules and with the clean-architecture skill. I propose:

```text
src/app/
  domain/          # Job, NotebookResult, Benchmark metrics, MarketSummary (frozen dataclasses)
  application/     # use cases: RunNotebook, GetResult, RunBenchmark, AnalyzeMarket
    ports/         # AIProvider, JobStore, NotebookExecutor, ReportRenderer, MarketDataReader (Protocols)
  adapters/
    ai/            # ollama.py, lmstudio.py
    executor/      # marimo subprocess runner
    storage/       # filesystem job store
    reports/       # PDF (+ JSON) renderers
    data/          # polars readers
    api/v1/        # FastAPI routes, Pydantic schemas
  infrastructure/  # config.py, logging.py, main.py (composition root)
notebooks/         # benchmark/, market_analysis/
```
Dependencies point inward only, enforced by import-linter. Your original structure is otherwise kept: docs, ADRs, tests/unit, tests/integration, output/, scripts/.

## 4. Components and data flow

POST /api/v1/notebooks/{id}/runs returns 202 with a job_id.
The registry checks that id is a known notebook. Clients never supply paths.
The job is stored as queued, then a background worker runs the notebook in a subprocess with a timeout.
The notebook builds its own dependencies from config, runs its use case, and writes structured JSON.
The job becomes completed or failed, with error text and the stderr tail stored internally.
GET .../runs/{job_id} returns status. .../result returns JSON. .../result.pdf renders a PDF from the stored JSON.

REST design. Your /notebooks/{id}/run plus /result is ambiguous when several runs exist. I recommend treating a run as the resource:

GET  /api/v1/notebooks                          list registered notebooks
POST /api/v1/notebooks/{notebook_id}/runs       -> 202 {job_id}
GET  /api/v1/runs/{job_id}                      status + metadata
GET  /api/v1/runs/{job_id}/result               JSON (Accept: application/json)
GET  /api/v1/runs/{job_id}/result.pdf           PDF
GET  /api/v1/notebooks/{notebook_id}/runs/latest  convenience alias

## 5. Key decisions (each gets an ADR)

Execution: a background job. An in-process asyncio task runs a subprocess, with a concurrency limit of 1–2 and a timeout. Celery or Redis is unjustified for a local tool. The JobStore port allows a real queue later.

Marimo: run the notebook as a script (python notebooks/x/x.py, since Marimo notebooks are valid Python). Parameters are passed as env vars or CLI args. To verify in the spike: whether marimo export html gives a more reliable headless run than script mode.

Result storage: the filesystem, output/<job_id>/{meta.json,result.json}. Each result has a schema_version field, and the result payload is typed per notebook, not one shared shape.

AI provider: an AIProvider Protocol with generate(prompt, options) and list_models(). Ollama uses /api/generate and /api/tags. LM Studio uses its OpenAI-compatible /v1/chat/completions. Both go through httpx with timeouts and retries.

PDF library: ReportLab, because it is pure Python with no system dependencies on Windows. Charts come from matplotlib as PNG. WeasyPrint needs GTK.

Data: polars only, per the project rules, and only in adapters.

Config: pydantic-settings with validation at startup and a fail-fast error message.

Logging: structured JSON through structlog, with job_id and request id bound to each log line and secret values redacted.

Errors: domain exceptions (NotebookNotFound, AIProviderUnavailable, ModelNotLoaded, AIProviderTimeout, NotebookExecutionFailed, ReportGenerationFailed) are mapped to 404, 409, 422, 500 and 503 in one exception handler. Clients get a generic message and a correlation id, and the stack trace goes only to the logs.

Security:

Notebooks are chosen from an allow-list.
job_id is validated as a UUID before any path is built.
CORS is an explicit config list.
There is a request size limit and a run rate limit.
Dev and prod profiles are separate.
Optional API-key auth is a config switch. A local-only tool may not need it.

## 6. Testing and quality

pytest, with fake ports and mocked HTTP (respx), so no Ollama or LM Studio is needed.
The integration test runs the API against a stub notebook and a fake AI provider.
ruff, mypy --strict, import-linter, and a GitHub Actions workflow that does none of the AI calls.

## 7. Assumptions and open questions

Please confirm or correct these, since some change the design:

Market data source: where does it come from (CSV, Excel, database, API), and what does it contain? The market analysis notebook can't be designed properly without this. This is the biggest unknown.
Auth: does the API need authentication, or is it local and trusted only?
Notebook results: do you want the run's rendered notebook output (HTML) stored as well? I assumed structured JSON only, plus the PDF.

Concurrency: I assumed one run at a time per notebook, with 409 Conflict if a run is already active. Is that right?

Retention: should old runs in output/ be cleaned up automatically? I assumed no for now.

Structure change: are you okay replacing your proposed api/services/ai layout with the layered one above?

PlantUML: it needs Java, or you can render it via a server or VS Code. I will write .puml sources embedded
in architecture.md, and no rendering step in CI. Is that acceptable?

Python and platform: I'll target Python 3.12 on Windows, developed with uv. Let me know if you use something else.

## Risks I'm flagging up front

Marimo's headless execution and how it passes parameters need a small spike before Phase 5. I'll verify this and won't assume it.

Local models are slow and nondeterministic, so benchmark scores need repeated runs and a warm-up run.
Subprocess execution on Windows needs care with process-tree termination on timeout.
Both ports are only guaranteed on localhost, so the endpoints must be configurable, not hard-coded.

Once you answer questions 1 and 6 at minimum, I'll move to Phase 0 (Sections 2–4, 21): README, docs/architecture.md with PlantUML diagrams, requirements.md and the ADRs. I won't write any implementation code before you approve those.
