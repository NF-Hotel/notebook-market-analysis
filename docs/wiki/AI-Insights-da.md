[English](AI-Insights) · **Dansk** · [Forside](Home-da)

# AI-indsigter

Med `insights=true` beder tjenesten den indstillede model (`AI_PROVIDER` med `OLLAMA_MODEL` eller `LM_STUDIO_MODEL`) om tekst til analyserne. Modellen beskriver tal, som tjenesten har beregnet; den beregner aldrig et tal selv.

## Hvordan der spørges

- Ét kald pr. graf. Svaret har et resumé og én til tre anbefalinger, hver med de tal, den bygger på. Tekster er Markdown: en grafs resumé er to eller tre almindelige sætninger, med fed kun til nøgletal. Skriver en model alligevel en liste, en overskrift eller en tabel, gør tjenesten det til almindelige sætninger (fed bevares). Rå HTML i et svar (tags, kommentarer, `script` og `style` med indhold) fjernes før guardrail og før lagring.
- Prognosen gives til modellen som en graf, så den må kommentere den.
- Pr. analyse beholder resultatet `executive_summary` (en Markdown-liste med et punkt pr. graf, grafens navn med fed), `improvement_suggestions` og `observations` (én pr. graf, koblet med dens `series`-id). En graf, hvis tekst afvises af guardrail, spørges én gang til med samme kald og en kort påmindelse om reglerne (ingen årsag, løfte eller forudsigelse; kun tal fra serien; almindelige sætninger). Afvises dette svar også, mister grafen sin egen tekst og ingen andre grafer. Timeout, modelfejl og dårlig struktur spørges ikke igen ud over det ene nye forsøg ved dårlig struktur.
- Prompten har en version (`PROMPT_VERSION`, nu `5`).

## Samlet fortolkning

Efter graferne får modellen ét ekstra kald med et kompakt input på højst 4.000 tegn: for hver tilgængelig analyse dens navn, første sætning af resuméet (almindelig tekst) og dens største fund (tal og enhed) samt prognosens tal (ikke bookingerne og ikke anbefalingerne). Et langt input forkortes sætning for sætning, aldrig ved at udelade en analyse, så det er inden for kontekstvinduet (`OLLAMA_NUM_CTX`). Den skriver Markdown: hovedpunkter, hvad de betyder samlet, 2 til 4 anbefalinger og forbehold. Teksten gemmes som `insights.overall` med `source: ai` og mærkaten `AI-generated`. Samme guardrail gælder, og de tal, den må nævne, er tallene i dens input. I modsætning til graferne må den samlede tekst beskrive tjenestens prognose (ordet "forecast" er tilladt) og skal kopiere prognosens tal præcis, som de står i inputtet; årsager, løfter, egne forudsigelser og tal, der ikke er i inputtet, afvises stadig. En afvist samlet tekst bliver bedt om én gang til, med reglerne lagt til samme kald; timeout og modelfejl bliver ikke bedt om igen. Er AI slået fra, har ingen analyse tekst, eller afvises svaret to gange, er `insights.overall` en kort tekst bygget af det største fund i hver tilgængelig analyse, med `source: figures`. En afvist samlet tekst ændrer aldrig analyserne.

## Guardrail

En tekst afvises, når den bruger en årsagsfrase ("because", "due to", "leads to"), et løfte ("will increase", "guarantee") eller en forudsigelse af sig selv. På prognosegrafen er ordene om tjenestens egen prognose tilladt. En tekst afvises også, når dens belæg ikke nævner et tal eller nævner et tal, der ikke står i grafens serie. To ting tæller ikke som tal: et 4-cifret årstal lige efter et månedsnavn ("April 2026", "Jul 2025", "fra July 2024 til December 2026"), og seriens antal punkter samt de to antal i en titel som "latest 30 of 102 months" (disse er tilladt). Et opfundet tal ved siden af et årstal afvises stadig. Listen er `FORBIDDEN_PHRASES` i `src/app/application/insight_guardrail.py`.

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
