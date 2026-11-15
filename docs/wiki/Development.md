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
yamllint .
```

Automated tests use fake AI providers and mocked HTTP. A running Ollama or LM Studio is never required.

## Load test

`tests/unit/adapters/api/test_market_analysis_api.py` makes one run of 55,484 generated bookings with insights on, the real insight code and a fake model (MIL-001 criterion 7). The run must complete in under 60 seconds, and the peak resident set of the test process must stay under the `mem_limit` of `deploy/docker-compose.yml`. The peak is read with the POSIX `resource` module, so the memory test is skipped on Windows; run the tests on Linux (in WSL, for example) to see it.

## Plan first

Work follows the plan-first workflow in `AGENTS.md`: the milestone in `docs/milestones/` is accepted with a `Go` review before code is written under `src/` or `tests/`. Each pull request closes the issues it completes.

## Contract

Change `openapi/market-contract.yaml` together with the code. The schema version of the result is `SCHEMA_VERSION` in `src/app/application/market_result.py`; the prompt version is `PROMPT_VERSION` in `src/app/application/insight_prompt.py`.
