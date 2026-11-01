**English** · [Dansk](Run-API-da)

# Run API

Every path except `/health` needs the header `X-API-Key`. Only one run is active at a time.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/market-analysis/runs?insights=true` | Start a run over the bookings in the body. Answers `202` with the run id. |
| GET | `/api/v1/market-analysis/runs/{run_id}` | The state: `queued`, `running`, `completed` or `failed`. |
| GET | `/api/v1/market-analysis/runs/{run_id}/result` | The result of a completed run. |
| GET | `/health` | Liveness, no key. |

`insights=false` skips the AI: the result then has no `insight` and no model is called.

## Errors

| Status | Code | When |
| --- | --- | --- |
| 400 | `invalid_request` | An invalid booking, an unknown field type, an empty list or a `room_count` below 1. Nothing is stored. |
| 401 | `unauthorized` | The key is missing or wrong. |
| 404 | `run_not_found` | The id is not known. |
| 409 | `run_active` | Another run is queued or running. |
| 409 | `result_not_ready` | The run has not finished. |
| 409 | `run_failed` | The run failed. |

A restart of the service interrupts a run that is active: it is shown as failed with `error_code: interrupted`. Start it again, and do not deploy while a run is going.

## Example

```bash
curl -s -X POST "http://market-analysis-api:8000/api/v1/market-analysis/runs?insights=true" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d @bookings.json
curl -s -H "X-API-Key: $KEY" http://market-analysis-api:8000/api/v1/market-analysis/runs/$RUN_ID
curl -s -H "X-API-Key: $KEY" http://market-analysis-api:8000/api/v1/market-analysis/runs/$RUN_ID/result
```

The body is described by `RunRequest` in `openapi/market-contract.yaml`. `room_count` (the rooms of the hotel) is needed for the occupancy analyses.
