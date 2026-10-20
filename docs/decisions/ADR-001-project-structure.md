# ADR-001: Project structure

Status: Proposed

## Context

The solution has two related projects (Marimo notebooks and a web API) that need the same logic: AI access, data loading, analysis, results. The initial idea was `api / notebooks / services / ai` folders under `src/app`.

## Options Considered

1. **Two repositories** with a shared published library. Clean separation but heavy overhead for one team.
2. **One repo, feature-style folders** (`api/`, `services/`, `ai/`). Simple, but nothing prevents `ai/` from importing `api/`, and business logic drifts into routes and notebooks.
3. **One repo, Clean Architecture layers** (`domain`, `application`, `adapters`, `infrastructure`) with notebooks outside `src/`.

## Decision

Option 3. One repository, one package `src/app`, layers with inward-only dependencies enforced by `import-linter`. Notebooks live in `notebooks/` and are thin; the API starts them as subprocesses and communicates through files in `output/`.

## Consequences

- Business logic is testable without FastAPI, Marimo, files or network.
- AI providers, data sources, storage and PDF are swappable adapters.
- Slightly more files and indirection than option 2.
- Contributors must learn the layer rules; `import-linter` and CI catch violations.
