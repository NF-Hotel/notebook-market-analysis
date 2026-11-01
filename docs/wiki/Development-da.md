[English](Development) · **Dansk** · [Forside](Home-da)

# Udvikling

## Lag

`src/app/{domain,application,adapters,infrastructure}`. Afhængigheder peger kun indad; API'et importerer aldrig notebook-kode. Testene i `tests/` spejler `src/`.

## Checks før en pull request

```bash
pytest
ruff check .
ruff format --check .
mypy src
lint-imports
```

Automatiske tests bruger falske AI-udbydere og mockede HTTP-kald. En kørende Ollama eller LM Studio kræves aldrig.

## Plan først

Arbejdet følger plan-først-arbejdsgangen i `AGENTS.md`: milepælen i `docs/milestones/` er accepteret med et `Go`-review, før der skrives kode under `src/` eller `tests/`. Hver pull request lukker de issues, den fuldfører.

## Kontrakt

Ret `openapi/market-contract.yaml` sammen med koden. Resultatets skemaversion er `SCHEMA_VERSION` i `src/app/application/market_result.py`; promptversionen er `PROMPT_VERSION` i `src/app/application/insight_prompt.py`.
