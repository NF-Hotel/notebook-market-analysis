# ADR-006: Result storage

Status: Proposed

## Context

Results must be shared between the notebook subprocess and the API, kept for a limited time, and support different notebook types.

## Options Considered

1. **Database** (SQLite/Postgres): queryable, but a schema and migrations for a small data volume.
2. **Filesystem folder per run.**
3. **In-memory**: lost on restart.

## Decision

Filesystem, `output/<job_id>/` with `meta.json` (metadata), `result.json` (typed payload with `schema_version`), `notebook.html` (rendered notebook), `report.pdf` (cached on first request), and captured logs. Writes are atomic (write temp file, rename). `job_id` is a UUID validated before any path is built. Runs older than `RETENTION_DAYS` (7) are deleted, except the latest run and latest successful run per notebook.

## Consequences

- Simple, inspectable, easy to back up and to test.
- No cross-run querying beyond scanning folders; acceptable at expected volume.
- A database can replace it behind the `JobStore` port if needed.
