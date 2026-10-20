# ADR-004: AI provider abstraction

Status: Proposed

## Context

We use local models via Ollama and LM Studio and want to change provider or add one without rewriting notebooks or analysis logic.

## Options Considered

1. **Call each provider's HTTP API directly** from use cases. Fast, but couples logic to providers.
2. **Use one OpenAI-compatible client for both.** Ollama and LM Studio both offer compatible endpoints, but Ollama-specific features (model listing, load state, timing stats) are lost.
3. **A port (`AIProvider` Protocol) with one adapter per provider.**

## Decision

Option 3. `AIProvider` (in `application/ports`) defines `generate(request) -> AIResponse` and `list_models()`. `OllamaProvider` uses `/api/chat` and `/api/tags`; `LMStudioProvider` uses `/v1/chat/completions` and `/v1/models`. Both use `httpx` with explicit timeouts and bounded retries. Provider errors are mapped to `AIProviderUnavailable`, `ModelNotLoaded`, `AIProviderTimeout`, `AIInvalidResponse`. Selection is by `AI_PROVIDER`.

## Consequences

- Tests use a fake `AIProvider`; adapters are tested with mocked HTTP.
- `AIResponse` carries model name, token counts (if provided) and duration, which the benchmark needs.
- Adding a provider means one adapter and a config value.
