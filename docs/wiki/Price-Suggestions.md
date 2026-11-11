**English** · [Dansk](Price-Suggestions-da)

# Price suggestions

A run that carries a `pricing` block also returns `price_suggestions` in the result (schema 1.3). The service finds the holidays and the weeks of the next two months and suggests a price change where the history of the same days says so. The NFHotel web application shows the suggestions to the Manager at `/admin/pricing/suggestions`; a Manager approves them there. The service changes no price.

## Asking for them

Add `pricing` to the body of the run. An empty object `{}` asks for the defaults. Without the block the result has no `price_suggestions`.

| Field | Meaning | Default |
| --- | --- | --- |
| `as_of` | The first day a suggestion may start | The day of the run |
| `horizon_days` | How far ahead the suggestions reach, 7 to 120 | 61 |
| `high_occupancy_threshold` | At or above this share in earlier years: a surcharge | 0.80 |
| `low_occupancy_threshold` | At or below this share in earlier years: a discount | 0.40 |
| `surcharge_percent` | The surcharge, above 0 and at most 100 | 20 |
| `discount_percent` | The discount, above 0 and below 100 | 15 |
| `discount_room_sizes` | The room sizes that get a discount | `single` |
| `min_history_years` | Fewer earlier years than this give no suggestion | 2 |

The low threshold must be below the high threshold. A value out of range answers `400 invalid_request` and nothing is stored.

## The rule

The rule is fixed and has no AI. The same bookings, date and settings always give the same suggestions.

1. For each holiday of the stored calendar in the horizon, the occupancy of the same holiday in each earlier year is taken; for each other stretch of a coming week, the occupancy of the same ISO week in each earlier year. A year counts only when all its days lie inside the bookings.
2. The occupancy is the room nights taken over `room_count` times the days, added up over the earlier years. It is the occupancy of the whole hotel; cancelled bookings take no room night.
3. At or above the high threshold: a `surcharge` for room size `all`, reason `holiday` or `high_history`. At or below the low threshold: a `discount` for each size in `discount_room_sizes`, reason `low_history`. Between the thresholds: no suggestion. The boundaries count as crossed.
4. A period with fewer earlier years than `min_history_years` gets no suggestion and is listed in `not_enough_history` with the years found.
5. A suggestion never starts before `as_of` and never ends after `horizon_end`. A suggestion is a percentage of the base rate; the service does not know a room rate, so it gives no price.

## What a suggestion holds

`room_size`, `first_date`, `last_date`, `change`, `percent`, `reason`, `holiday` (when there is one), `threshold`, `history` (the year and the occupancy of each earlier year) and `explanation`. The result also has `formula` and `limitations`, and `ideas`.

## The AI text

The AI only explains. Each suggestion has an `explanation` with `ai_written`, and the result has at most three `ideas` without a price (a package or a minimum stay), each with `ai_written: true`. A text is rejected when it names a number, a month or a date that is not the suggestion's own, a currency, a cause or a promise; an idea is rejected when it holds any number. A rejected or failed answer, or `insights=false`, gives an explanation built from the figures with `ai_written: false`, and no ideas. No text changes a figure of a suggestion. See [AI insights](AI-Insights).

## Known limits

- The occupancy is that of the whole hotel, so a discount for one size rests on the occupancy of all rooms.
- A holiday or week needs at least two earlier years inside the bookings (by default).
- The AI text can be vague, or say "consistently" where one earlier year was below the threshold; the guardrail checks the numbers and the months, not every comparison. The figures are always given beside the text.

The contract is `PricingRequest` and `PriceSuggestionSet` in `openapi/market-contract.yaml`.
