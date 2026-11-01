**English** · [Dansk](Result-da)

# Result (schema 1.2)

The result of a completed run holds the input summary, the data quality, nine analyses, notices, a `forecast` and, when asked, the AI `insights`.

## The nine analyses

| Analysis | Shows |
| --- | --- |
| `lead_time` | Days between booking and arrival, in bands, split by cancellation, month, market segment and customer type. |
| `holidays` | Bookings and arrivals on and around holidays. |
| `seasonality` | Bookings and arrivals for each month. |
| `cancellations` | The share of cancelled bookings, split by lead time, deposit, segment, customer type, month, special requests and booking changes. |
| `room_value` | An estimate of the value of a room night split by cancellation, which is not revenue, and `room_revenue` (below). |
| `guest_mix` | Repeat guests, meals, parking, special requests, room types, countries and guests for each booking. |
| `occupancy` | Occupied room nights against the rooms, for each month. |
| `occupancy_on_holidays` | The occupancy on holidays against other days. |
| `correlations` | Correlations between series that move together or apart. |

Each analysis has a `status` (`available` or `unavailable`), a `formula` (how the figures were calculated), its `findings` and `limitations`.

## Room revenue

`room_value.findings.room_revenue` is the sum of price per night times nights of the bookings that are not cancelled, the mean for each booking, a series for each month of arrival, and the number of bookings left out because they have no price. It is before taxes, fees, discounts and extras, and the currency is not known.

## Forecast

The `forecast` is calculated by the service, not by the model. Each month is the mean of the same calendar month in the history, with a band of one sample standard deviation. The horizon is 6 months for a history of 12 months or more, else 3. `history_too_short` is true below 24 months. It has no trend, and revenue months without a priced booking count as zero. Both are written in its `limitations`.

## Insights

`insights` holds `requested`, and with AI `provider`, `model` and `prompt_version`. The texts of the AI (`executive_summary`, `improvement_suggestions` and the `text` of an observation) are Markdown without raw HTML. `insights.overall` is the overall interpretation of all analyses and the forecast: `status`, `source`, `label` and `text` (Markdown). With `source: ai` (label `AI-generated`) it also has `generated_at`, `evidence` and `recommendations`; with `source: figures` it is a short text the service builds from the largest finding of each analysis, used when AI is off or the AI text is rejected. `overall` is an optional property, so the schema stays 1.2.

## Figures and limits

Money is decimal text. The service says what it could not calculate in `notices` and `limitations` instead of guessing.
