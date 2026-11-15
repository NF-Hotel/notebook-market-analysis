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
yamllint .
```

Automatiske tests bruger falske AI-udbydere og mockede HTTP-kald. En kørende Ollama eller LM Studio kræves aldrig.

## Belastningstest

`tests/unit/adapters/api/test_market_analysis_api.py` laver én kørsel af 55.484 genererede bookinger med AI-indsigter slået til, den rigtige indsigtskode og en falsk model (MIL-001 kriterium 7). Kørslen skal være færdig på under 60 sekunder, og testprocessens største hukommelsesforbrug (resident set) skal holde sig under `mem_limit` i `deploy/docker-compose.yml`. Forbruget læses med POSIX-modulet `resource`, så hukommelsestesten springes over på Windows; kør testene på Linux (fx i WSL) for at se den.

## Plan først

Arbejdet følger plan-først-arbejdsgangen i `AGENTS.md`: milepælen i `docs/milestones/` er accepteret med et `Go`-review, før der skrives kode under `src/` eller `tests/`. Hver pull request lukker de issues, den fuldfører.

## Kontrakt

Ret `openapi/market-contract.yaml` sammen med koden. Resultatets skemaversion er `SCHEMA_VERSION` i `src/app/application/market_result.py`; promptversionen er `PROMPT_VERSION` i `src/app/application/insight_prompt.py`.
