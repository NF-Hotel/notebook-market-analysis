[English](Price-Suggestions) · **Dansk** · [Forside](Home-da)

# Prisforslag

En kørsel med en `pricing`-blok giver også `price_suggestions` i resultatet (skema 1.3). Tjenesten finder helligdagene og ugerne i de næste to måneder og foreslår en prisændring, hvor historikken for de samme dage siger det. NFHotel-webapplikationen viser forslagene til Manageren på `/admin/pricing/suggestions`; en Manager godkender dem dér. Tjenesten ændrer ingen pris.

## Sådan bedes der om dem

Tilføj `pricing` til kroppen af kørslen. Et tomt objekt `{}` beder om standardværdierne. Uden blokken har resultatet ingen `price_suggestions`.

| Felt | Betydning | Standard |
| --- | --- | --- |
| `as_of` | Den første dag, et forslag må starte | Kørslens dag |
| `horizon_days` | Hvor langt forslagene rækker, 7 til 120 | 61 |
| `high_occupancy_threshold` | Ved eller over denne andel i tidligere år: et tillæg | 0.80 |
| `low_occupancy_threshold` | Ved eller under denne andel i tidligere år: en rabat | 0.40 |
| `surcharge_percent` | Tillægget, over 0 og højst 100 | 20 |
| `discount_percent` | Rabatten, over 0 og under 100 | 15 |
| `discount_room_sizes` | De værelsesstørrelser, der får rabat | `single` |
| `min_history_years` | Færre tidligere år end dette giver intet forslag | 2 |

Den lave grænse skal være under den høje. En værdi uden for intervallet svarer `400 invalid_request`, og intet gemmes.

## Reglen

Reglen er fast og har ingen AI. De samme bookinger, den samme dato og de samme indstillinger giver altid de samme forslag.

1. For hver helligdag i den gemte kalender i horisonten tages belægningen på den samme helligdag i hvert tidligere år; for hver anden strækning af en kommende uge tages belægningen i den samme ISO-uge i hvert tidligere år. Et år tæller kun, når alle dets dage ligger inden for bookingerne.
2. Belægningen er de solgte værelsesnætter over `room_count` gange dagene, lagt sammen over de tidligere år. Det er hele hotellets belægning; annullerede bookinger tager ingen værelsesnat.
3. Ved eller over den høje grænse: et `surcharge` for størrelsen `all` med årsagen `holiday` eller `high_history`. Ved eller under den lave grænse: en `discount` for hver størrelse i `discount_room_sizes` med årsagen `low_history`. Mellem grænserne: intet forslag. Grænserne tæller som nået.
4. En periode med færre tidligere år end `min_history_years` får intet forslag og står i `not_enough_history` med de fundne år.
5. Et forslag starter aldrig før `as_of` og slutter aldrig efter `horizon_end`. Et forslag er en procent af grundprisen; tjenesten kender ingen værelsespris, så den giver ingen pris.

## Hvad et forslag indeholder

`room_size`, `first_date`, `last_date`, `change`, `percent`, `reason`, `holiday` (når der er en), `threshold`, `history` (året og belægningen for hvert tidligere år) og `explanation`. Resultatet har også `formula` og `limitations` samt `ideas`.

## AI-teksten

AI'en forklarer kun. Hvert forslag har en `explanation` med `ai_written`, og resultatet har højst tre `ideas` uden pris (en pakke eller et minimumsophold), hver med `ai_written: true`. En tekst afvises, når den nævner et tal, en måned eller en dato, der ikke er forslagets egen, en valuta, en årsag eller et løfte; en idé afvises, når den indeholder et tal. Et afvist eller fejlet svar, eller `insights=false`, giver en forklaring bygget af tallene med `ai_written: false` og ingen idéer. Ingen tekst ændrer et tal i et forslag. Se [AI-indsigter](AI-Insights-da).

## Kendte grænser

- Belægningen er hele hotellets, så en rabat til én størrelse bygger på belægningen af alle værelser.
- En helligdag eller uge kræver mindst to tidligere år inden for bookingerne (som standard).
- AI-teksten kan være vag eller skrive "konsekvent", hvor ét tidligere år lå under grænsen; guardrailen tjekker tal og måneder, ikke hver sammenligning. Tallene står altid ved siden af teksten.

Kontrakten er `PricingRequest` og `PriceSuggestionSet` i `openapi/market-contract.yaml`.
