**English** · [Dansk](Deployment-da)

# Deployment

The service runs as one container beside the NFHotel web application. No host port is published and nginx has no route to it; the web application calls `http://market-analysis-api:8000` on the internal network with `X-API-Key`.

## Files

| File | Purpose |
| --- | --- |
| `Dockerfile` | Builds from this repository alone, with hash-locked dependencies (`requirements.lock`). |
| `deploy/docker-compose.yml` | Read-only file system, non-root user, `mem_limit: 2g`, network `nfhotel-api`. |
| `deploy/market-analysis.env.example` | The settings. Copy to `market-analysis.env` (git-ignored). |

```bash
cd deploy
docker compose --env-file market-analysis.env up -d --build
```

## Settings that matter

| Variable | Meaning |
| --- | --- |
| `API_TOKEN` | The key callers send in `X-API-Key`. The web application holds the same value. |
| `AI_PROVIDER`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | The model server and the model. An empty model name switches the AI off. |
| `AI_STALL_TIMEOUT_SECONDS`, `AI_TOTAL_TIMEOUT_SECONDS` | 600 and 14400 by default. |
| `AI_MAX_OUTPUT_TOKENS` | 32768 by default. |

The Ollama that is asked must be the one that has the model. A default model chosen in the back office that this Ollama does not have gives `MODEL_ERROR` on every insight.

## Updating

Change the version the image is built from, rebuild and start the container. A run that is active when the container restarts is interrupted.
