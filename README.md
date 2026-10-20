# NF Hotel Data Analysis

Status: **design phase**. This README describes the intended system. Sections marked *(planned)* are not implemented yet and will be verified in Phase 10.

## Overview

A locally run analysis platform for hotel and market data. It consists of two related projects in one repository:

| Project | Location | Purpose |
|---|---|---|
| Marimo notebooks | `notebooks/` | Reproducible, interactive analysis: a model **benchmark** and a **market analysis**. |
| Web API | `src/app/adapters/api/` | Runs registered notebooks as background jobs and serves results as JSON, PDF and HTML. |

Both projects share one Python package, `src/app`, which holds all logic. Notebooks are thin: they read configuration, call a use case, and write results. The API never imports notebook code; it starts notebooks as subprocesses and reads the files they produce.

## Purpose

- Decide which local AI model (Ollama or LM Studio) best suits our analysis work (benchmark).
- Analyse hotel market data and produce structured and human-readable results, using a local AI model for narrative insight (market analysis).
- Make both available on demand through an authenticated API.

## Project structure

```
notebooks/                 Marimo notebooks (benchmark/, market_analysis/)
src/app/
  domain/                  Entities and value objects (no dependencies)
  application/             Use cases and ports (Protocols)
  adapters/                ai/, api/, data/, executor/, reports/, storage/
  infrastructure/          config, logging, main (composition root)
tests/                     unit/ and integration/
docs/                      architecture, requirements, API, development, ADRs
output/                    Run results (git-ignored)
scripts/                   Helper scripts
```

Dependencies point inward only (`adapters -> application -> domain`). See [docs/architecture.md](docs/architecture.md) and [ADR-001](docs/decisions/ADR-001-project-structure.md).

## Architecture overview

```
Client -> FastAPI -> Notebook registry -> Job runner -> Marimo notebook (subprocess)
                                                            |
                                          use cases -> AIProvider -> Ollama | LM Studio
                                          use cases -> MarketDataReader -> JSON API | CSV
                                                            |
                                          output/<job_id>/  result.json, meta.json, notebook.html
                                                            |
                              API <- report service (JSON / PDF / HTML)
```

## Requirements

- Python 3.12 or newer
- Windows, macOS or Linux (developed on Windows)
- A local AI runtime: [Ollama](https://ollama.com) and/or [LM Studio](https://lmstudio.ai)
- Access to the market data API, or CSV files for example mode

## Installation *(planned)*

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

On macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`.

All Python commands in this project assume the `.venv` is active.

## Configuration *(planned)*

Configuration comes from environment variables, optionally loaded from `.env`, and is validated at startup. Invalid or missing required values stop the application with a clear message. `.env` is git-ignored; `.env.example` documents every variable.

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | `development` or `production`. Production requires `API_TOKEN` and explicit CORS origins. |
| `API_HOST` | `127.0.0.1` | Bind address. |
| `API_PORT` | `8000` | Port. |
| `API_TOKEN` | none | Bearer token clients must send. Required in production. |
| `CORS_ALLOWED_ORIGINS` | none | Comma-separated list of allowed origins. Empty means no cross-origin access. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `LOG_FORMAT` | `json` | `json` or `console`. |
| `OUTPUT_DIRECTORY` | `./output` | Where run results are stored. |
| `RETENTION_DAYS` | `7` | Runs older than this are deleted; the latest run per notebook is always kept. |
| `NOTEBOOK_TIMEOUT_SECONDS` | `1800` | Maximum notebook execution time. |
| `MAX_CONCURRENT_RUNS` | `2` | Concurrent notebook jobs. One active run per notebook. |
| `AI_PROVIDER` | `ollama` | `ollama` or `lmstudio`. |
| `AI_TIMEOUT_SECONDS` | `120` | Timeout per AI request. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint. |
| `OLLAMA_MODEL` | none | Model name used by market analysis. |
| `LM_STUDIO_BASE_URL` | `http://localhost:1234` | LM Studio endpoint. |
| `LM_STUDIO_MODEL` | none | Model identifier used by market analysis. |
| `BENCHMARK_MODELS` | none | Comma-separated `provider:model` pairs the benchmark compares. |
| `DATA_SOURCE` | `api` | `api` for the JSON market data API, `csv` for example mode. |
| `MARKET_DATA_API_URL` | none | Market data API base URL (when `DATA_SOURCE=api`). |
| `MARKET_DATA_API_TOKEN` | none | Token for the market data API. Never logged. |
| `MARKET_DATA_CSV_PATH` | `./data/example` | Folder with example CSV files (when `DATA_SOURCE=csv`). |

## Starting the API *(planned)*

```powershell
uvicorn app.infrastructure.main:app --host 127.0.0.1 --port 8000
```

Interactive OpenAPI docs are served at `/docs`.

## Running notebooks manually *(planned)*

```powershell
marimo edit notebooks/benchmark/benchmark.py        # interactive
marimo run  notebooks/market_analysis/market_analysis.py   # app mode
```

Notebooks read the same configuration as the API. To produce output without a UI, use `marimo export html` as the API runner does; see [docs/architecture.md](docs/architecture.md).

## Using LM Studio

1. Load a model in LM Studio and start the local server (default `http://localhost:1234`).
2. Set `AI_PROVIDER=lmstudio`, `LM_STUDIO_BASE_URL` and `LM_STUDIO_MODEL`.
3. LM Studio is called through its OpenAI-compatible `/v1/chat/completions` endpoint.

## Using Ollama

1. Install Ollama and pull a model, e.g. `ollama pull <model>`.
2. Set `AI_PROVIDER=ollama`, `OLLAMA_BASE_URL` and `OLLAMA_MODEL`.
3. Ollama is called through `/api/chat` and `/api/tags`.

## Running tests *(planned)*

```powershell
pytest                      # unit + API + integration; no AI service required
pytest tests/unit
ruff check . ; ruff format --check .
mypy src
lint-imports                # architecture (dependency direction) contracts
```

Automated tests use fake AI providers and mocked HTTP. A running Ollama or LM Studio instance is never required.

## Generating notebook output *(planned)*

Through the API, or from the command line via the runner. Each run writes to `output/<job_id>/`:

| File | Content |
|---|---|
| `meta.json` | Job id, notebook, status, timestamps, duration, configuration snapshot (no secrets). |
| `result.json` | Structured, versioned result. |
| `notebook.html` | Rendered notebook output. |

PDF is rendered on request from `result.json` and cached.

## API overview *(planned)*

All endpoints except `/health` require `Authorization: Bearer <API_TOKEN>`.

| Method | URL | Purpose |
|---|---|---|
| GET | `/api/v1/notebooks` | List registered notebooks. |
| POST | `/api/v1/notebooks/{notebook_id}/runs` | Start a run. Returns `202` and a `job_id`. |
| GET | `/api/v1/notebooks/{notebook_id}/runs/latest` | Latest run of a notebook. |
| GET | `/api/v1/runs/{job_id}` | Run status and metadata. |
| GET | `/api/v1/runs/{job_id}/result` | Result as JSON. |
| GET | `/api/v1/runs/{job_id}/result.pdf` | Result as PDF. |
| GET | `/api/v1/runs/{job_id}/result.html` | Rendered notebook output. |
| GET | `/health` | Liveness (no auth). |

Full detail: `docs/api.md` (written in Phase 6).

Example:

```bash
curl -X POST http://localhost:8000/api/v1/notebooks/benchmark/runs \
  -H "Authorization: Bearer $API_TOKEN"
# 202 {"job_id":"3f0c...","notebook":"benchmark","status":"queued"}

curl http://localhost:8000/api/v1/runs/3f0c... -H "Authorization: Bearer $API_TOKEN"
# {"job_id":"3f0c...","notebook":"benchmark","status":"completed","duration_seconds":12.4,...}
```

## Logging

Structured JSON logs (console format available for development) with `request_id` and `job_id` bound to each line. Secrets (tokens, API keys) are redacted and never logged. Notebook subprocess output is captured per job.

## Troubleshooting *(planned)*

| Symptom | Likely cause |
|---|---|
| `503` from a run | AI provider unreachable or model not loaded. Check the provider is running and the model name matches. |
| `401` | Missing or wrong bearer token. |
| Browser CORS error | Origin not in `CORS_ALLOWED_ORIGINS`. |
| `409` on run | A run of that notebook is already active. |
| App fails at startup | Configuration validation error; the message names the variable. |

## Development guidelines

- Python rules and architecture rules are defined in `.claude/agents/python-developer.md` and `.claude/skills/clean-architecture/`.
- Every function has full type annotations; `mypy --strict`, `ruff` and `pytest` must pass.
- Polars is preferred over pandas, and dataframes stay in adapters.
- Notebooks contain no business logic.
- Record significant decisions as ADRs in `docs/decisions/`.

See [docs/development.md](docs/development.md) (written in Phase 10).

## Documentation

- [Requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Decisions (ADRs)](docs/decisions/)
