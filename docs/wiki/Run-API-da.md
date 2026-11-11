[English](Run-API) · **Dansk** · [Forside](Home-da)

# Kørsels-API

Alle stier undtagen `/health` kræver headeren `X-API-Key`. Der er kun én aktiv kørsel ad gangen.

| Metode | Sti | Formål |
| --- | --- | --- |
| POST | `/api/v1/market-analysis/runs?insights=true` | Start en kørsel over bookingerne i kroppen. Svarer `202` med kørslens id. |
| GET | `/api/v1/market-analysis/runs/{run_id}` | Tilstanden: `queued`, `running`, `completed` eller `failed`. |
| GET | `/api/v1/market-analysis/runs/{run_id}/result` | Resultatet af en afsluttet kørsel. |
| GET | `/health` | Levetegn, ingen nøgle. |

`insights=false` springer AI over: resultatet har så ingen `insight`, og der kaldes ingen model.

## Fejl

| Status | Kode | Hvornår |
| --- | --- | --- |
| 400 | `invalid_request` | En ugyldig booking, en ukendt felttype, en tom liste eller et `room_count` under 1. Intet gemmes. |
| 401 | `unauthorized` | Nøglen mangler eller er forkert. |
| 404 | `run_not_found` | Id'et er ukendt. |
| 409 | `run_active` | En anden kørsel er i kø eller kører. |
| 409 | `result_not_ready` | Kørslen er ikke færdig. |
| 409 | `run_failed` | Kørslen fejlede. |

En genstart af tjenesten afbryder en aktiv kørsel: den vises som fejlet med `error_code: interrupted`. Start den igen, og udrul ikke, mens en kørsel er i gang.

## Eksempel

```bash
curl -s -X POST "http://market-analysis-api:8000/api/v1/market-analysis/runs?insights=true" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d @bookings.json
curl -s -H "X-API-Key: $KEY" http://market-analysis-api:8000/api/v1/market-analysis/runs/$RUN_ID
curl -s -H "X-API-Key: $KEY" http://market-analysis-api:8000/api/v1/market-analysis/runs/$RUN_ID/result
```

Kroppen er beskrevet af `RunRequest` i `openapi/market-contract.yaml`. `room_count` (hotellets antal værelser) bruges til belægningsanalyserne. En valgfri `pricing`-blok beder om prisforslag; se [Prisforslag](Price-Suggestions-da).
