**English** · [Dansk](Home-da)

# NF Hotel market analysis service

A small service that analyses the bookings of a hotel and tells what they show. The NFHotel web application sends the bookings, follows a background run and shows the result in the back office page `/admin/market-analysis`.

## What it does

- Takes the bookings in the body of a request. It reads no market data of its own.
- Calculates nine analyses with fixed formulas: lead time, holidays, seasonality, cancellations, room value (with room revenue), guest mix, occupancy, occupancy on holidays and correlations.
- Calculates a forecast of the next 3 to 6 months of arrivals, occupancy and room revenue from the seasonal pattern of the history.
- On request, asks a local AI model (Ollama or LM Studio) to describe each chart and to give recommendations. The model never calculates a figure.
- On request (`pricing`), suggests price changes for the holidays and weeks of the next two months from the history of the same days, by a fixed rule; the AI only explains them.
- Serves the holiday calendar that the web application uses.

## Where to read next

| Page | For |
| --- | --- |
| [Run API](Run-API) | The three paths, the errors and an example. |
| [Result](Result) | What the result holds (schema 1.3) and how each figure is calculated. |
| [Price suggestions](Price-Suggestions) | The `pricing` block, the rule, the AI text and the limits. |
| [AI insights](AI-Insights) | How the model is asked, the guardrail and the reasons an insight is unavailable. |
| [Deployment](Deployment) | The settings, the container and the network. |
| [Development](Development) | The checks to run, the layers and the plan-first workflow. |

The authoritative contract is `openapi/market-contract.yaml`; a test fails when the code and the contract differ.
