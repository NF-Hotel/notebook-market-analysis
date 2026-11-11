# RC-018 Gate review of MIL-002 (price suggestions from the market analysis)

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-018 |
| CrossReference | [MIL-002], [QC-PY-001], [QC-WIKI-001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-11-11 | Proposed | Claude (AI) | S02 | Initial version; pre-review by the AI, not independent | [208ac88] |

---

## Artifact Under Review

- Instance reviewed: the whole of [MIL-002] against its Go/No-Go criteria 1 to 8, and the wiki pages written or changed in task 6: `Price-Suggestions` (new), `Home`, `Run-API`, `Result`, `AI-Insights` and `_Sidebar`, each in English and in Danish
- Checklist used: [QC-PY-001] (`qc-programming-python`) for the code, read in [RC-015], [RC-016] and [RC-017]; [QC-WIKI-001] (`qc-wiki`) for the wiki
- Scope: gate of the milestone; no source file changed in task 6
- Mode: supervised (the AI ran the checks and wrote the pre-review; S02 reviews)

## Checks run for the gate

| Check | Result |
| --- | --- |
| `pytest` | 632 passed |
| `ruff check .` | clean |
| `ruff format --check .` | 184 files already formatted |
| `mypy src` | no issues in 71 source files |
| `lint-imports` | 3 contracts kept, 0 broken |

A real run against `phi4:latest` on the dev VM was made for [MIL-071] task 6 (156,686 bookings, thresholds 55 and 45 percent): the service gave suggestions for the holidays Christmas Day and Second Day of Christmas and for the weeks before them, with the occupancy of each year 2018 to 2025, explanations marked `ai_written` or built from the figures, and three ideas without a price. With the default thresholds (80 and 40 percent) the data of 25 to 66 percent gave no suggestion and the result had an empty list.

## Go / No-Go criteria of MIL-002

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Contract has `pricing` and `price_suggestions`, schema 1.3, a client of 1.2 still reads it, a test fails when code and contract differ | Pass | `test_contract.py`, `test_contract_schema.py`; [RC-017] |
| 2 | A holiday with 85 percent in two earlier years gives a surcharge for every size; exactly 80 percent counts, a hair above the boundary does not | Pass | `test_a_holiday_with_85_percent_in_two_earlier_years_gets_a_surcharge_for_every_size`, `test_exactly_the_high_threshold_gives_a_surcharge_and_a_hair_above_it_does_not` |
| 3 | A week at or below the low threshold gives a discount for single rooms only | Pass | `test_a_week_with_low_history_gets_a_discount_for_single_rooms_only` |
| 4 | Too few earlier years gives `not_enough_history`; no suggestion starts before the date or ends after the horizon | Pass | `test_too_few_earlier_years_give_no_suggestion_and_are_listed`, `test_no_suggestion_starts_before_the_date_or_ends_after_the_horizon` |
| 5 | Two runs give identical suggestions; changing only the fake AI answer changes none | Pass | `test_the_same_input_gives_the_same_suggestions`, `test_the_explainer_changes_nothing_of_the_suggestion`, and the run test of [RC-017] |
| 6 | Every suggestion has an explanation marked `ai_written`; a price, a percentage or a date that is not its own is rejected; with the AI off the fallback is marked as not written by an AI | Pass | `test_price_explanations.py` (rejected number, month, cause, promise; fallback with no model, after two rejections and on a failed model) |
| 7 | A run without `pricing` has no change in the other fields; 55,484 bookings complete in under 60 seconds with the fake provider | Pass | `test_a_run_of_55484_bookings_completes_in_under_60_seconds` and the run tests of [RC-017] |
| 8 | Tests pass, linters clean, architecture tests pass, `qc-programming-python` is `Go` | Pass | The checks above; [RC-015], [RC-016] and [RC-017] are `Go` |

## Wiki ([QC-WIKI-001])

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 to 7 | `_Sidebar.md` present, title and list, every page listed, no dead link | Pass | The new page is listed in both languages; the links of the new page point to `Home`, `AI-Insights`, `Result` and the Danish twins |
| 8 | A language line on each page | Pass | The new pages start with the language line |
| 9 | The wiki exists in English and in the PO language | Pass | Each English page has its Danish twin; `Price-Suggestions-da` is new |
| 10 | The page sets are identical in every language | Pass | Seven pages in each language |
| 11 to 13 | Language line first; page names; code, commands and IDs stay in English | Pass | |
| 14 | The sidebar, every page and every link checked on the published wiki | Open | Done after the merge, when the pages are published |

The facts of the new page were read against `price_suggestions.py`, `price_explanations.py`, `price_result.py` and the contract: the fields and their defaults, the ranges, the boundary, the weeks and holidays, `not_enough_history`, the fallback and the ideas. One earlier error was corrected: the wiki said the prompt version is `7`; it is `8`.

## Findings

| # | Finding | Severity | Action |
| --- | --- | --- | --- |
| F1 | The guardrail of the explanations checks numbers, months, currency, causes and promises, not every comparison: a text may say "consistently above" when one earlier year was below. Seen in the real run (2018: 41.5 percent against a threshold of 55) | Low | Written in the wiki as a known limit; a rule on such words can be a later milestone |
| F2 | The occupancy is of the whole hotel, so a discount for a size rests on all rooms | Low | A known limit, in `limitations` and in the wiki |
| F3 | The repository has no DCD ([RC-017] criterion 10 passed on condition) | Info | None |

## Overall Verdict

Go: all eight criteria of [MIL-002] are met and the three code reviews are `Go`. Open: criterion 14 of [QC-WIKI-001] (the published wiki, after the merge).

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Accept this review and the milestone [MIL-002] | S02 | with the pull request |
| Check the published wiki pages and their links | S02 | after the merge |

---

[MIL-002]: ../milestones/mil-002-price-suggestions.md
[QC-PY-001]: ../../../framework/qc/code/qc-programming-python.md
[QC-WIKI-001]: ../../../framework/qc/artifacts/qc-wiki.md
[RC-015]: ./rc-015-mil-002-tasks-2-and-3-code.md
[RC-016]: ./rc-016-mil-002-task-4-code.md
[RC-017]: ./rc-017-mil-002-task-5-code.md
[208ac88]: https://github.com/NF-Hotel/notebook-market-analysis/commit/208ac886c6489e19236a837dc7ad33132cb34201
