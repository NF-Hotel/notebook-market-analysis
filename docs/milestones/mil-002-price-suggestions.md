# MIL-002 Price suggestions from the market analysis

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-002 |
| CrossReference | [BC-001], [MIL-001] |
| Language | en |
| Domain | it |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-11-11 | Accepted | Jens Tirsvad Nielsen | S02 | Initial version; accepted by the user in chat on 2026-11-11 after RC-013 Go | pending |

---

## Purpose

Decide whether the market analysis service can make the room price suggestions that the hotel shows to its Manager. S01 wants the service to find the holidays of the next two months, to suggest a higher price where the history shows an occupancy above 80 percent on the same days in earlier years, and to suggest discounts and other changes inside the same two months. NFHotel MIL-055 built this as a rule inside the website; this milestone moves the rule to the service, which already holds the bookings, the holiday calendar and the occupancy figures, and NFHotel [MIL-071] only presents the suggestions at `/admin/pricing/suggestions` and lets a Manager approve them. The decision this gate supports: a fixed rule over the figures gives the price changes, so the same bookings, the same date and the same settings always give the same suggestions; the AI only explains a suggestion and may add ideas that carry no price, and everything it writes is marked as written by an AI.

## Deliverable

- **Contract first.** `openapi/market-contract.yaml` gets an optional `pricing` block in the run request (the date the suggestions start from, the horizon in days with a default of 61, the high occupancy threshold with a default of 0.80, the low occupancy threshold, the room sizes that qualify for a discount, the surcharge and discount percentages) and `price_suggestions` in the run result, as result schema 1.3 that adds the field and changes nothing else, so a client of schema 1.2 still reads the result. A sample file of the new field is the first test file of both repositories.
- **Holidays in the horizon.** The holidays of the stored calendar that fall in the next two months, with their names, as the days to look at first.
- **History rule.** A pure rule in the domain and application layers: for each holiday and each coming week of the horizon, the occupancy of the same holiday, or of the same calendar week, in earlier years of the bookings; a period at or above the high threshold gives a surcharge suggestion for all room sizes; a period at or below the low threshold gives a discount suggestion for the sizes that qualify. A suggestion states the room size, the first and the last day, the percentage, the reason (`holiday`, `high_history`, `low_history`), the name of the holiday when there is one, and the figures it rests on (the occupancy of each earlier year and the threshold it crossed). A period with no history, or with fewer than the minimum number of earlier years, gives no suggestion and is listed as `not_enough_history`.
- **Other suggestions.** From the same figures, a discount for a stretch of low occupancy in the horizon and a note for a period with a holiday and low history; each follows a fixed rule and has a reason code.
- **AI text.** The AI writes a short explanation of each suggestion and at most three further ideas without a price (for instance a package or a minimum stay), under the guardrail of MIL-001, with `ai_written: true`, and a fallback text built from the figures when the AI is off or the answer is rejected. The AI never sets a price, a percentage or a date.
- **Tests and documents.** Unit tests of the rule against hand calculated figures, tests of the contract, a test that changes only the AI text and gets the same suggestions, a raised prompt version and the service documentation.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | The contract file describes the `pricing` block and `price_suggestions`, the result has schema version 1.3, a client of 1.2 still reads it, and a test fails when the implementation and the contract differ | Yes | No |
| 2 | For a small booking file in which a holiday week had an occupancy of 85 percent in two earlier years, the run gives a surcharge suggestion for every room size for that holiday with the 20 percent surcharge, the holiday name, the dates and the two occupancy figures; at exactly 80 percent the rule gives a surcharge and at 79.9 percent it does not (a test fixes which side counts) | Yes | No |
| 3 | A week at or below the low threshold gives a discount suggestion for single rooms only, and no suggestion for the other sizes | Yes | No |
| 4 | A period with fewer earlier years than the minimum gives no suggestion and appears as `not_enough_history`; no suggestion starts before the date of the run or ends after the horizon | Yes | No |
| 5 | Two runs over the same bookings, date and settings give identical suggestions, and a test in which only the fake AI answer changes gives the same suggestions (no AI in the rule) | Yes | No |
| 6 | With a fake AI provider every suggestion has an explanation marked `ai_written`, an answer with a price, a percentage or a date that is not the suggestion's own is rejected by the guardrail, and with the AI off the fallback text is returned and marked as not written by an AI | Yes | No |
| 7 | A run without the `pricing` block gives a result of schema 1.3 with no change in the other fields, and a run of 55,484 bookings still completes in under 60 seconds with the fake provider | Yes | No |
| 8 | Tests pass, the linters are clean, the architecture tests pass and `qc-programming-python` has the verdict `Go` | Yes | No |

## Dependencies

| Depends on | Reason |
| --- | --- |
| MIL-001 | The run API, the occupancy and holiday analyses, the AI port and the guardrail |
| NFHotel MIL-071 | Reads `price_suggestions` and presents it; the contract of task 1 is agreed with it |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| NFHotel objective 29 (price suggestions) and US-001.12 | All tasks |
| NFHotel US-001.01 View the market analysis | Tasks 2 to 4 |

## Ownership

| Role | Stakeholder ID (SA) |
| --- | --- |
| Owner | S01 |
| Approving reviewer | S02 |

## Target Date

2026-11-27 — two weeks from the plan, so that NFHotel [MIL-071] can follow by 2026-12-11; for S01 to confirm.

## Tasks

| # | Task | Summary | Needs its own Use Case/User Story? | Reference |
| --- | --- | --- | --- | --- |
| 1 | Business Case scope and contract | Add the `pricing` request block, `price_suggestions` and result schema 1.3 to `openapi/market-contract.yaml`, with a sample file and a contract test; agree it with NFHotel MIL-071 before any code; add the scope item "price suggestions" to BC-001 and review it. Why: both repositories build on the contract, and BC-001 names no price suggestions. | No | |
| 2 | Holidays and history in the horizon | Domain and application code that lists the holidays of the next two months from the stored calendar and the occupancy of the same holiday or week in earlier years from the bookings; unit tests against hand calculated figures. | No | |
| 3 | Suggestion rule | Pure rule for surcharge, discount and not-enough-history with the thresholds, percentages, sizes and horizon taken from the request; boundary tests at 80 and the low threshold; the other suggestions of low stretches. No AI. | No | |
| 4 | AI explanations and ideas | Port use and prompt for a short explanation per suggestion and at most three ideas without a price, the guardrail rule for prices and dates, `ai_written`, the fallback text and a raised prompt version. | No | |
| 5 | Wire into the run | Read the `pricing` block, add `price_suggestions` to the result, keep schema 1.2 clients working, and add the performance and determinism tests. | No | |
| 6 | Documents, check and review | Service documentation, traceability, build, linters, tests, review against `qc-programming-python`; record the RC. | No | |

---

[BC-001]: ../business-case.md
[MIL-001]: ./mil-001-market-analysis-run-api.md
[MIL-071]: https://github.com/NF-Hotel/NFHotel/blob/main/docs/milestones/mil-071-price-suggestions-from-the-service.md
