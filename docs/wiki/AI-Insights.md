**English** · [Dansk](AI-Insights-da)

# AI insights

With `insights=true` the service asks the configured model (`AI_PROVIDER` with `OLLAMA_MODEL` or `LM_STUDIO_MODEL`) for text about the analyses. The model describes figures that the service calculated; it never calculates one.

## How it is asked

- One request for each chart. The answer holds a summary and one to three recommendations, each with the figures it rests on. The texts are Markdown: the summary of a chart is two or three plain sentences, with bold only for key figures. If a model writes a list, a heading or a table anyway, the service turns it into plain sentences (the bold stays). Raw HTML in an answer (tags, comments, `script` and `style` with their content) is removed before the guardrail and before storage.
- The forecast is given to the model as a chart, so it may comment on it.
- Per analysis the result keeps `executive_summary` (a Markdown list with one item for each chart, the chart name in bold), `improvement_suggestions` and `observations` (one for each chart, matched by its `series` id). A chart whose text is rejected by the guardrail is asked one more time, with the same request, a short reminder of the rules (no cause, promise or prediction; numbers only from the series; plain sentences) and a line that names the rule that rejected the text: the forbidden word with a little context (for example `"predicted" in "rate is predicted for March"`), or the figures that are not in the input, as written. If that answer is rejected too, the chart loses its own text and no other chart. A timeout, a model error or a bad structure is not asked again beyond the one retry for a bad structure.
- The prompt has a version (`PROMPT_VERSION`, now `7`).

## Overall interpretation

After the charts, one extra request gives the model a compact input of at most 4,000 characters: for every available analysis its name, the first sentence of its summary (plain text) and its largest finding (figure and unit), and the figures of the forecast (not the bookings, and not the recommendations). A long input is shortened sentence by sentence, never by dropping an analysis, so it fits the context window (`OLLAMA_NUM_CTX`). It writes Markdown: key points, what they mean together, 2 to 4 recommendations and caveats. It is stored as `insights.overall` with `source: ai` and the label `AI-generated`. The same guardrail applies, and the numbers it may cite are the numbers written in its input. Unlike the texts of the charts, the overall text may describe the forecast of the service (the word "forecast" is allowed) and must copy its figures exactly as written in the input; causes, promises, predictions of its own and figures not in the input are still rejected. A rejected overall text is asked for again, up to three requests in all; each next request has the rules added and names the reason the previous text was rejected (the forbidden word, for example "predicted", or the figures not in the input). The prompt tells the model to write findings of the data in the present or past tense and to say "the forecast of the service shows" for the forecast. A timeout or a model error is not asked again. When AI is off, nothing has text, or the answer is rejected three times, `insights.overall` is a short text built from the largest finding of each available analysis, with `source: figures`. A rejected overall text never changes the analyses.

## Guardrail

A text is rejected when it uses a causal phrase ("because", "due to", "leads to"), a promise ("will increase", "guarantee") or a prediction of its own. On the forecast chart the words about the service's own forecast are allowed. A text is also rejected when its evidence names no number, or a number that is not in the series of the chart. Two things are not counted as figures: a 4-digit year right after a month name ("April 2026", "Jul 2025", "from July 2024 to December 2026"), and the number of points of the series with the two counts of a title such as "latest 30 of 102 months" (these are allowed). A made-up number next to a year is still rejected. The list is `FORBIDDEN_PHRASES` in `src/app/application/insight_guardrail.py`.

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
