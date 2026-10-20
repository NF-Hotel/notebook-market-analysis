# ADR-003: Marimo for notebooks

Status: Proposed

## Context

Analysis must be interactive for analysts and executable programmatically by the API. Notebooks must be reproducible and diff-friendly.

## Options Considered

1. **Jupyter**: ubiquitous, but JSON files diff poorly, hidden state and out-of-order execution hurt reproducibility.
2. **Marimo**: notebooks are plain Python files, reactive execution (no hidden state), can run as scripts or apps and export HTML.
3. **Plain scripts plus a UI**: reproducible but not interactive.

## Decision

Marimo. Notebooks contain presentation and orchestration only: read settings, build dependencies through the composition code, call one use case, display results, write `result.json`.

## Consequences

- Notebook files are ordinary Python and reviewable in git.
- The `python-developer` rules (typing, layering) apply to notebooks too.
- Programmatic execution is via `marimo export html` in a subprocess. Exit-code behavior, parameter passing and HTML export flags are to be verified in a spike before Phase 5; this ADR will be updated with the findings.
