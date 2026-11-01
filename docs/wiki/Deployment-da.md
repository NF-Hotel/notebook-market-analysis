[English](Deployment) · **Dansk** · [Forside](Home-da)

# Udrulning

Tjenesten kører som én container ved siden af NFHotel-webapplikationen. Der er ingen udgivet værtsport, og nginx har ingen rute til den; webapplikationen kalder `http://market-analysis-api:8000` på det interne netværk med `X-API-Key`.

## Filer

| Fil | Formål |
| --- | --- |
| `Dockerfile` | Bygger ud fra dette repository alene, med hash-låste afhængigheder (`requirements.lock`). |
| `deploy/docker-compose.yml` | Skrivebeskyttet filsystem, ikke-root-bruger, `mem_limit: 2g`, netværket `nfhotel-api`. |
| `deploy/market-analysis.env.example` | Indstillingerne. Kopiér til `market-analysis.env` (git-ignoreret). |

```bash
cd deploy
docker compose --env-file market-analysis.env up -d --build
```

## Indstillinger, der betyder noget

| Variabel | Betydning |
| --- | --- |
| `API_TOKEN` | Nøglen, kaldere sender i `X-API-Key`. Webapplikationen har den samme værdi. |
| `AI_PROVIDER`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | Modelserveren og modellen. Et tomt modelnavn slår AI fra. |
| `OLLAMA_NUM_CTX` | Kontekstvinduet i tokens (standard `16384`), sendt til Ollama som `num_ctx` i hvert kald. Ollamas egen standard er for lille og afskærer starten af en prompt. LM Studio har sin egen kontekstindstilling i modelindstillingerne. |
| `AI_STALL_TIMEOUT_SECONDS`, `AI_TOTAL_TIMEOUT_SECONDS` | Som standard 600 og 14400. |
| `AI_MAX_OUTPUT_TOKENS` | Som standard 32768. |

Den Ollama, der spørges, skal være den, der har modellen. En standardmodel valgt i administrationen, som den Ollama ikke har, giver `MODEL_ERROR` på alle indsigter.

## Opdatering

Skift den version, billedet bygges fra, byg igen og start containeren. En kørsel, der er aktiv ved en genstart, afbrydes.
