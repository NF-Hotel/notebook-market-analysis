[English](Result) · **Dansk** · [Forside](Home-da)

# Resultat (skema 1.2)

Resultatet af en afsluttet kørsel indeholder et resumé af input, datakvaliteten, ni analyser, bemærkninger, en `forecast` og, hvis det er bedt om, AI-`insights`.

## De ni analyser

| Analyse | Viser |
| --- | --- |
| `lead_time` | Dage mellem booking og ankomst i bånd, delt efter annullering, måned, markedssegment og kundetype. |
| `holidays` | Bookinger og ankomster på og omkring helligdage. |
| `seasonality` | Bookinger og ankomster pr. måned. |
| `cancellations` | Andelen af annullerede bookinger, delt efter leveringstid, depositum, segment, kundetype, måned, særlige ønsker og ændringer. |
| `room_value` | Et skøn over værdien af en værelsesnat delt efter annullering, som ikke er omsætning, og `room_revenue` (nedenfor). |
| `guest_mix` | Tilbagevendende gæster, måltider, parkering, særlige ønsker, værelsestyper, lande og antal gæster pr. booking. |
| `occupancy` | Belagte værelsesnætter mod antallet af værelser, pr. måned. |
| `occupancy_on_holidays` | Belægningen på helligdage mod øvrige dage. |
| `correlations` | Sammenhænge mellem serier, der bevæger sig sammen eller hver for sig. |

Hver analyse har en `status` (`available` eller `unavailable`), en `formula` (hvordan tallene er beregnet), sine `findings` og `limitations`.

## Værelsesomsætning

`room_value.findings.room_revenue` er summen af pris pr. nat gange antal nætter for de bookinger, der ikke er annulleret, gennemsnittet pr. booking, en serie pr. ankomstmåned og antallet af bookinger, der er udeladt, fordi de ikke har en pris. Beløbet er før skatter, gebyrer, rabatter og tillæg, og valutaen er ukendt.

## Prognose

`forecast` beregnes af tjenesten, ikke af modellen. Hver måned er gennemsnittet af den samme kalendermåned i historikken med et bånd på én stikprøve-standardafvigelse. Horisonten er 6 måneder ved en historik på 12 måneder eller mere, ellers 3. `history_too_short` er sand under 24 måneder. Der er ingen trend, og omsætningsmåneder uden en booking med pris tæller som nul. Begge dele står i prognosens `limitations`.

## Tal og grænser

Beløb er decimaltekst. Tjenesten skriver i `notices` og `limitations`, hvad den ikke kunne beregne, i stedet for at gætte.
