# Requirements

## Scope

Two related projects in one repository: Marimo notebooks (benchmark, market analysis) and a FastAPI web API that runs them and serves results.

## Assumptions

| # | Assumption |
|---|---|
| A1 | Market data is delivered by an HTTP API as JSON. Its URL, authentication and schema are not yet specified; the reader is behind a port so the schema can be adapted without touching analysis logic. |
| A2 | "Example mode" uses CSV files in `MARKET_DATA_CSV_PATH` with equivalent columns. |
| A3 | The API is used by trusted internal clients and protected by a static bearer token plus explicit CORS. Per-user accounts are out of scope. |
| A4 | One active run per notebook; a second start request returns `409`. |
| A5 | Runs are retained 7 days, but the latest run (and latest successful run) per notebook is always kept. |
| A6 | Ollama and LM Studio run on the same machine or trusted network. |
| A7 | Marimo notebooks can be executed headlessly and export HTML. To be verified in a spike before Phase 5. |

## Functional requirements

### Benchmark notebook (FR-B)

- FR-B1: Test each model configured in `BENCHMARK_MODELS` (across Ollama and LM Studio).
- FR-B2: Use a fixed, versioned prompt set representative of our market-analysis tasks.
- FR-B3: Measure per model: time to first token where available, total latency, tokens per second, success/failure rate, timeouts, and output validity (e.g. valid JSON when JSON is requested).
- FR-B4: Run a warm-up request and repeat each prompt N times; report mean, median and spread.
- FR-B5: Store results as structured JSON.
- FR-B6: Present results in the notebook (tables and charts) and allow comparing models.
- FR-B7: Produce a ranking or recommendation with the criteria stated.

### Market analysis notebook (FR-M)

- FR-M1: Load market data from the JSON API or from CSV, selected by `DATA_SOURCE`.
- FR-M2: Validate the loaded data and report problems (missing fields, empty periods) as warnings or errors.
- FR-M3: Compute the analysis (metrics and comparisons to be specified once the data schema is known).
- FR-M4: Use a local AI model, through `AIProvider`, for narrative summaries and insights.
- FR-M5: Support LM Studio and Ollama, selected by configuration only.
- FR-M6: Produce structured JSON, human-readable output (notebook HTML and PDF) and machine-readable output.
- FR-M7: If the AI provider fails, still produce the numeric analysis and mark the narrative section as unavailable.

### Web API (FR-A)

- FR-A1: List registered notebooks.
- FR-A2: Start a run of a registered notebook as a background job and return a job id.
- FR-A3: Return job status and metadata.
- FR-A4: Return results as JSON, PDF and rendered HTML.
- FR-A5: Return the latest run for a notebook.
- FR-A6: Accept only registered notebook ids; clients cannot supply file paths or code.
- FR-A7: Adding a notebook does not require changes to routes, runner or report service, only a registry entry, schemas and a report section.
- FR-A8: Require a bearer token on all endpoints except `/health`.
- FR-A9: Clean up runs older than 7 days, keeping the latest per notebook.

### Results (FR-R)

- FR-R1: Every run has metadata: `job_id`, `notebook`, `status`, `started_at`, `completed_at`, `duration_seconds`, `provider`, `model`, `schema_version`, `warnings`, `error`.
- FR-R2: The `result` payload is typed per notebook; no shared shape is assumed.
- FR-R3: JSON is valid, structured, versioned via `schema_version`, and contains no pre-formatted display text where structured data exists.
- FR-R4: PDF contains title, notebook name, execution time, model/configuration info, summary, results, tables, charts, and errors/warnings.
- FR-R5: PDF generation is a separate component, not part of notebooks or routes.

## Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 Reproducibility | Pinned dependency ranges, `.venv`, configuration through environment, versioned prompt sets, configuration snapshot stored per run. |
| NFR-2 Maintainability | Clean Architecture layering enforced by `import-linter`; full type hints; `ruff` and `mypy --strict` clean. |
| NFR-3 Testability | Domain and use cases testable without network, filesystem or frameworks; external AI mocked in CI. |
| NFR-4 Extensibility | New AI provider = one adapter plus configuration. New notebook = registry entry, notebook file, schemas, tests. |
| NFR-5 Observability | Structured logs with `request_id` and `job_id`; durations and outcomes logged; secrets redacted. |
| NFR-6 Resilience | AI failures produce typed errors mapped to HTTP status; timeouts everywhere; a failed run never crashes the API. |
| NFR-7 Security | Allow-listed notebooks, UUID-validated ids, no client paths, bearer token, explicit CORS, request size limits, separate dev/prod configuration, no stack traces to clients. |
| NFR-8 Performance | API never blocks on notebook execution; long runs are background jobs; concurrency capped. |
| NFR-9 Portability | Works on Windows (primary), macOS and Linux; Python 3.12+. |
| NFR-10 Documentation | README, architecture, API docs and ADRs stay consistent with the implementation. |

## Out of scope

- Multi-user accounts, roles, OAuth.
- Distributed job queue (Celery, Redis); the `JobStore` and executor ports leave room for one.
- Cloud-hosted AI providers (the abstraction allows them later).
- Training or fine-tuning models.

## Open items

- Market data API URL, authentication scheme and JSON schema (needed before Phase 4).
- Exact analysis metrics for the market analysis notebook.
- Benchmark prompt set content and quality criteria.
