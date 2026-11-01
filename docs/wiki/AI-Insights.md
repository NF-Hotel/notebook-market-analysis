**English** · [Dansk](AI-Insights-da)

# AI insights

With `insights=true` the service asks the configured model (`AI_PROVIDER` with `OLLAMA_MODEL` or `LM_STUDIO_MODEL`) for text about the analyses. The model describes figures that the service calculated; it never calculates one.

## How it is asked

- One request for each chart. The answer holds a summary of two to three sentences and one to three recommendations, each with the figures it rests on.
- The forecast is given to the model as a chart, so it may comment on it.
- Per analysis the result keeps `executive_summary`, `improvement_suggestions` and `observations` (one for each chart, matched by its `series` id). A chart whose text is rejected loses only its own text.
- The prompt has a version (`PROMPT_VERSION`).

## Guardrail

A text is rejected when it uses a causal phrase ("because", "due to", "leads to"), a promise ("will increase", "guarantee") or a prediction of its own. On the forecast chart the words about the service's own forecast are allowed. A text is also rejected when its evidence names no number, or a number that is not in the series of the chart. The list is `FORBIDDEN_PHRASES` in `src/app/application/insight_guardrail.py`.

## Why an insight can be unavailable

| Reason | Meaning |
| --- | --- |
| `AI_NOT_CONFIGURED` | No model name is set. |
| `ANALYSIS_UNAVAILABLE` | The analysis itself has no figures. |
| `TIMEOUT` | No token for `AI_STALL_TIMEOUT_SECONDS`, or the total limit was reached. |
| `BAD_STRUCTURE` | The answer was not JSON of the schema, twice. |
| `GUARDRAIL_REJECTED` | Every chart of the analysis was rejected. |
| `MODEL_ERROR` | The server is unreachable, answered with an HTTP error (a 404 means the model is not installed in that Ollama) or answered with nothing. |

## Choosing a model

A small model may give vague or rejected text. Try a larger one with the same run and compare. A model name must be exactly one that the server lists, tag included (`phi4:latest`, not `phi4`).
