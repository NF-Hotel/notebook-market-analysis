**English** · [Dansk](Development-da)

# Development

## Layers

`src/app/{domain,application,adapters,infrastructure}`. Dependencies point inward only; the API never imports notebook code. Tests in `tests/` mirror `src/`.

## Checks before a pull request

```bash
pytest
ruff check .
ruff format --check .
mypy src
lint-imports
```

Automated tests use fake AI providers and mocked HTTP. A running Ollama or LM Studio is never required.

## Plan first

Work follows the plan-first workflow in `AGENTS.md`: the milestone in `docs/milestones/` is accepted with a `Go` review before code is written under `src/` or `tests/`. Each pull request closes the issues it completes.

## Contract

Change `openapi/market-contract.yaml` together with the code. The schema version of the result is `SCHEMA_VERSION` in `src/app/application/market_result.py`; the prompt version is `PROMPT_VERSION` in `src/app/application/insight_prompt.py`.
