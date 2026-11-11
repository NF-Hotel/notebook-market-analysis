[English](Home) · **Dansk**

# NF Hotel markedsanalyse-tjeneste

En lille tjeneste, der analyserer et hotels bookinger og fortæller, hvad de viser. NFHotel-webapplikationen sender bookingerne, følger en kørsel i baggrunden og viser resultatet på administrationssiden `/admin/market-analysis`.

## Hvad den gør

- Modtager bookingerne i kroppen af en forespørgsel. Den læser ingen markedsdata selv.
- Beregner ni analyser med faste formler: leveringstid, helligdage, sæsoner, annulleringer, værelsesværdi (med værelsesomsætning), gæstemix, belægning, belægning på helligdage og korrelationer.
- Beregner en prognose for de næste 3 til 6 måneder af ankomster, belægning og værelsesomsætning ud fra historikkens sæsonmønster.
- Beder efter ønske en lokal AI-model (Ollama eller LM Studio) om at beskrive hver graf og give anbefalinger. Modellen beregner aldrig et tal.
- Foreslår efter ønske (`pricing`) prisændringer for helligdagene og ugerne i de næste to måneder ud fra historikken for de samme dage, efter en fast regel; AI'en forklarer dem kun.
- Leverer den helligdagskalender, som webapplikationen bruger.

## Læs videre

| Side | Til |
| --- | --- |
| [Kørsels-API](Run-API-da) | De tre stier, fejlene og et eksempel. |
| [Resultat](Result-da) | Hvad resultatet indeholder (skema 1.3), og hvordan hvert tal beregnes. |
| [Prisforslag](Price-Suggestions-da) | `pricing`-blokken, reglen, AI-teksten og grænserne. |
| [AI-indsigter](AI-Insights-da) | Hvordan modellen spørges, guardrailen og årsagerne til, at en indsigt mangler. |
| [Udrulning](Deployment-da) | Indstillingerne, containeren og netværket. |
| [Udvikling](Development-da) | De checks, der skal køres, lagene og plan-først-arbejdsgangen. |

Den gældende kontrakt er `openapi/market-contract.yaml`; en test fejler, når koden og kontrakten er uens.
