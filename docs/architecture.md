# Architecture

Diagrams are PlantUML in fenced `plantuml` blocks (rendered by Gitea).

## 1. System context

```plantuml
@startuml
title System context
actor "Client\n(browser / CLI / app)" as Client
rectangle "NF Hotel Data Analysis" {
  component "Web API\n(FastAPI)" as API
  component "Marimo notebooks\n(benchmark, market_analysis)" as NB
  database "output/\nrun results" as OUT
}
cloud "Market data API\n(JSON)" as MDA
file "Example CSV files" as CSV
node "Ollama" as OLL
node "LM Studio" as LMS

Client --> API : HTTPS + bearer token
API --> NB : start (subprocess)
NB --> OUT : write result.json,\nmeta.json, notebook.html
API --> OUT : read
NB --> MDA : fetch (DATA_SOURCE=api)
NB --> CSV : read (DATA_SOURCE=csv)
NB --> OLL : AIProvider
NB --> LMS : AIProvider
@enduml
```

## 2. Layers and components

Dependencies point inward only. Enforced with `import-linter`.

```plantuml
@startuml
title Layers (dependencies point inward)
package "infrastructure" {
  [config] 
  [logging]
  [main (composition root)]
}
package "adapters" {
  [api/v1 (FastAPI)]
  [ai: OllamaProvider, LMStudioProvider]
  [data: JsonApiReader, CsvReader (polars)]
  [executor: MarimoExecutor]
  [storage: FileJobStore]
  [reports: PdfRenderer, JsonRenderer]
}
package "application" {
  [use cases: RunNotebook, GetRun, GetResult,\nRunBenchmark, AnalyzeMarket, CleanupRuns]
  [ports: AIProvider, MarketDataReader, JobStore,\nNotebookExecutor, ReportRenderer]
}
package "domain" {
  [Job, RunMetadata, BenchmarkResult,\nMarketAnalysisResult, errors]
}
[main (composition root)] ..> [api/v1 (FastAPI)]
[api/v1 (FastAPI)] --> [use cases: RunNotebook, GetRun, GetResult,\nRunBenchmark, AnalyzeMarket, CleanupRuns]
[ai: OllamaProvider, LMStudioProvider] --> [ports: AIProvider, MarketDataReader, JobStore,\nNotebookExecutor, ReportRenderer]
[data: JsonApiReader, CsvReader (polars)] --> [ports: AIProvider, MarketDataReader, JobStore,\nNotebookExecutor, ReportRenderer]
[executor: MarimoExecutor] --> [ports: AIProvider, MarketDataReader, JobStore,\nNotebookExecutor, ReportRenderer]
[storage: FileJobStore] --> [ports: AIProvider, MarketDataReader, JobStore,\nNotebookExecutor, ReportRenderer]
[reports: PdfRenderer, JsonRenderer] --> [ports: AIProvider, MarketDataReader, JobStore,\nNotebookExecutor, ReportRenderer]
[use cases: RunNotebook, GetRun, GetResult,\nRunBenchmark, AnalyzeMarket, CleanupRuns] --> [Job, RunMetadata, BenchmarkResult,\nMarketAnalysisResult, errors]
@enduml
```

### Components and responsibilities

| Component | Responsibility |
|---|---|
| `domain` | Frozen dataclasses (`Job`, `RunMetadata`, per-notebook result types) and domain errors. No I/O, no third-party imports. |
| `application` | Use cases and ports. Orchestrates domain logic; knows nothing about HTTP, files, polars or Marimo. |
| `adapters/api` | FastAPI routes, Pydantic schemas, auth dependency, error handlers. Thin: parse, call use case, respond. |
| `adapters/executor` | Starts a notebook subprocess with timeout and captures output. |
| `adapters/storage` | Stores runs in `output/<job_id>/`; implements retention. |
| `adapters/ai` | One class per provider implementing `AIProvider`. |
| `adapters/data` | Market data readers (polars) converting to domain types. |
| `adapters/reports` | JSON and PDF renderers. |
| `infrastructure` | Settings, logging setup, composition root. |
| `notebooks/` | Marimo files: build dependencies from config, call one use case, present the result. |

### Notebook registry

A registry of approved notebooks in the application layer. Each entry declares: `notebook_id`, file path (relative to `notebooks/`, fixed in code), input schema, result schema, report section builder, and default timeout. Clients pass only `notebook_id`.

## 3. API request flow

```plantuml
@startuml
title API request flow: start and fetch a run
actor Client
participant "FastAPI route" as R
participant "Auth / validation" as A
participant RunNotebook as UC
participant "Registry" as REG
participant JobStore as JS
participant "Background runner" as BG

Client -> R : POST /api/v1/notebooks/benchmark/runs
R -> A : verify bearer token, validate id
A --> R : ok
R -> UC : execute(notebook_id)
UC -> REG : get(notebook_id)
REG --> UC : definition | NotebookNotFound (404)
UC -> JS : active run for notebook?
JS --> UC : none | active (409)
UC -> JS : create Job(status=queued)
UC -> BG : schedule(job_id)
UC --> R : Job
R --> Client : 202 {job_id, status: queued}

Client -> R : GET /api/v1/runs/{job_id}
R --> Client : 200 {status, ...}
Client -> R : GET /api/v1/runs/{job_id}/result
R -> JS : load result.json
R --> Client : 200 JSON | 409 not finished | 404
@enduml
```

## 4. Notebook execution flow

```plantuml
@startuml
title Notebook execution flow
participant "Background runner" as BG
participant JobStore as JS
participant MarimoExecutor as EX
participant "marimo subprocess" as NB
participant "Use case" as UC

BG -> JS : mark running (started_at)
BG -> EX : execute(notebook, job_id, env)
EX -> NB : marimo export html notebook.py\n(env: JOB_ID, OUTPUT_DIR, config)
NB -> UC : RunBenchmark / AnalyzeMarket
UC --> NB : result
NB -> NB : write result.json (versioned)
NB --> EX : notebook.html, exit code
alt exit code 0 and result.json valid
  EX --> BG : success
  BG -> JS : mark completed, duration
else failure / timeout
  EX --> BG : NotebookExecutionFailed (stderr tail)
  BG -> JS : mark failed (error summary)
end
BG -> BG : log outcome, duration, job_id
@enduml
```

Notes:
- Execution uses Marimo's headless HTML export, which runs the notebook and produces `notebook.html`; the notebook also writes `result.json` as a side effect. **This must be verified in a spike before Phase 5**, including how parameters reach the notebook (environment variables are the planned mechanism) and how `--no-include-code` and error exit codes behave.
- The subprocess gets a minimal environment: only the variables it needs, and no unrelated secrets.
- On timeout the whole process tree is terminated (Windows requires explicit tree kill).
- Concurrency: an `asyncio.Semaphore(MAX_CONCURRENT_RUNS)` plus one active run per notebook.

## 5. Local AI interaction

```plantuml
@startuml
title Local AI interaction
participant Notebook
participant "Use case\n(AnalyzeMarket)" as UC
participant "AIProvider (port)" as P
participant OllamaProvider as O
participant LMStudioProvider as L
participant "Ollama\n/api/chat" as OS
participant "LM Studio\n/v1/chat/completions" as LS

Notebook -> UC : analyze(data)
UC -> P : generate(request)
alt AI_PROVIDER=ollama
  P <-- O
  O -> OS : POST (timeout, retry)
  OS --> O : response
else AI_PROVIDER=lmstudio
  P <-- L
  L -> LS : POST (timeout, retry)
  LS --> L : response
end
P --> UC : AIResponse(text, model, tokens, duration)\nor AIProviderError
UC --> Notebook : result (narrative unavailable if AI failed)
@enduml
```

`AIProvider` exposes `generate(request) -> AIResponse` and `list_models() -> list[str]`. Error types: `AIProviderUnavailable`, `ModelNotLoaded`, `AIProviderTimeout`, `AIInvalidResponse`. The chosen provider is created once in the composition root from `AI_PROVIDER`; the benchmark can create several.

## 6. Data flow

1. **Input:** `MarketDataReader` returns domain objects, from the JSON API (`DATA_SOURCE=api`) or CSV (`csv`). Polars is used inside the readers only.
2. **Processing:** the `AnalyzeMarket` use case computes metrics on domain objects and asks `AIProvider` for narrative text.
3. **Result:** a versioned, typed result is serialized to `result.json`.
4. **Output:** the report service renders JSON, PDF (cached in the run folder) and serves `notebook.html`.

## 7. Output generation flow

```plantuml
@startuml
title Output generation
Client -> API : GET /runs/{id}/result.pdf
API -> "GetResult use case" : load(job_id)
"GetResult use case" -> JobStore : result.json + meta.json
API -> "Report service" : render(kind=pdf, run)
"Report service" -> "Notebook section builder" : title, summary, tables, charts
"Report service" -> "PdfRenderer (ReportLab)" : build
"PdfRenderer (ReportLab)" --> API : bytes (cached as report.pdf)
API --> Client : 200 application/pdf | 500 ReportGenerationFailed
@enduml
```

The report service knows nothing about Marimo. Each registered notebook supplies a section builder that converts its typed result into generic blocks (heading, paragraph, table, chart); the PDF renderer only renders blocks. New notebooks therefore need no renderer changes.

## 8. Error handling flow

Domain errors are raised in use cases and adapters and mapped in a single FastAPI exception handler:

| Error | HTTP |
|---|---|
| `InvalidRequest` / validation | 400 / 422 |
| Missing or invalid token | 401 |
| `NotebookNotFound`, `RunNotFound` | 404 |
| `RunAlreadyActive`, result requested before completion | 409 |
| `AIProviderUnavailable`, `ModelNotLoaded`, `AIProviderTimeout` | 503 |
| `NotebookExecutionFailed`, `ReportGenerationFailed`, unexpected | 500 |

Clients receive `{"error": {"code": "...", "message": "...", "correlation_id": "..."}}`. Full details and stack traces are logged with the same `correlation_id`. Failures inside a running job are recorded on the job (`status=failed`, sanitized `error`) and never crash the API process.

## 9. Configuration flow

```plantuml
@startuml
title Configuration flow
"Environment / .env" --> Settings : pydantic-settings load + validate
Settings --> "Composition root" : typed, immutable
"Composition root" --> "AIProvider adapter" : selected by AI_PROVIDER
"Composition root" --> "MarketDataReader adapter" : selected by DATA_SOURCE
"Composition root" --> "FastAPI app" : token, CORS, limits
"Composition root" --> "MarimoExecutor" : whitelisted env for subprocess
note right of Settings : invalid config -> fail fast\nwith the offending variable name
@enduml
```

The notebook subprocess builds its own `Settings` and dependencies from its environment, using the same composition code as the API.

## 10. Retention

A cleanup use case runs at startup and then daily. It deletes run folders older than `RETENTION_DAYS` (7), except the latest run and the latest successful run of each notebook. Deletion only touches direct children of `OUTPUT_DIRECTORY` whose names are valid UUIDs.

## 11. Security summary

- Only registered notebook ids can run; no client-supplied paths, code or arguments.
- `job_id` is parsed as a UUID before use in any path; resolved paths are checked to stay inside `OUTPUT_DIRECTORY`.
- Bearer token compared in constant time; `/health` is the only unauthenticated endpoint.
- CORS uses an explicit origin list, no wildcard in production.
- Request body size and run-start rate are limited.
- Secrets are never logged; the stored configuration snapshot omits them.
- Production requires `API_TOKEN` and explicit CORS origins, or startup fails.

## 12. Extensibility

- **New notebook:** notebook file, registry entry, input and result schemas, section builder, tests, `docs/api.md` entry. Routes, runner and store are unchanged.
- **New AI provider:** one adapter implementing `AIProvider`, a config value, tests. Notebooks and use cases are unchanged.
- **New data source:** one adapter implementing `MarketDataReader`.
- **Real job queue:** replace the background runner behind `NotebookExecutor`/`JobStore`.

## 13. Differences from the initial proposal

- The layered structure replaces `api / notebooks / services / ai` so dependency direction can be enforced (ADR-001).
- Runs are a resource (`/runs/{job_id}`) rather than one result per notebook, so history and concurrent inspection work (ADR-005, ADR-006).
- The "Notebook Registry / Notebook Runner / Service Layer" boxes map to: registry and use cases in `application`, runner in `adapters/executor`, services split into use cases and adapters.
