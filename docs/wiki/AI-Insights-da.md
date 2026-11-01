[English](AI-Insights) · **Dansk** · [Forside](Home-da)

# AI-indsigter

Med `insights=true` beder tjenesten den indstillede model (`AI_PROVIDER` med `OLLAMA_MODEL` eller `LM_STUDIO_MODEL`) om tekst til analyserne. Modellen beskriver tal, som tjenesten har beregnet; den beregner aldrig et tal selv.

## Hvordan der spørges

- Ét kald pr. graf. Svaret har et resumé på to til tre sætninger og én til tre anbefalinger, hver med de tal, den bygger på.
- Prognosen gives til modellen som en graf, så den må kommentere den.
- Pr. analyse beholder resultatet `executive_summary`, `improvement_suggestions` og `observations` (én pr. graf, koblet med dens `series`-id). En graf, hvis tekst afvises, mister kun sin egen tekst.
- Prompten har en version (`PROMPT_VERSION`).

## Guardrail

En tekst afvises, når den bruger en årsagsfrase ("because", "due to", "leads to"), et løfte ("will increase", "guarantee") eller en forudsigelse af sig selv. På prognosegrafen er ordene om tjenestens egen prognose tilladt. En tekst afvises også, når dens belæg ikke nævner et tal eller nævner et tal, der ikke står i grafens serie. Listen er `FORBIDDEN_PHRASES` i `src/app/application/insight_guardrail.py`.

## Hvorfor en indsigt kan mangle

| Årsag | Betydning |
| --- | --- |
| `AI_NOT_CONFIGURED` | Der er ikke sat et modelnavn. |
| `ANALYSIS_UNAVAILABLE` | Selve analysen har ingen tal. |
| `TIMEOUT` | Intet token i `AI_STALL_TIMEOUT_SECONDS`, eller den samlede grænse er nået. |
| `BAD_STRUCTURE` | Svaret var ikke JSON efter skemaet, to gange. |
| `GUARDRAIL_REJECTED` | Alle analysens grafer blev afvist. |
| `MODEL_ERROR` | Serveren kan ikke nås, svarede med en HTTP-fejl (en 404 betyder, at modellen ikke er installeret i den Ollama) eller svarede med ingenting. |

## Valg af model

En lille model kan give vage eller afviste tekster. Prøv en større med samme kørsel og sammenlign. Et modelnavn skal være præcis et, serveren lister, med tag (`phi4:latest`, ikke `phi4`).
