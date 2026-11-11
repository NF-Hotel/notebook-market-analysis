# RC-017 Review of the code of MIL-002 task 5

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-017 |
| CrossReference | [MIL-002], [QC-PY-001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-11-11 | Proposed | Claude (AI) | S02 | Initial version; pre-review by the AI, not independent | pending |

---

## Artifact Under Review

- Instance reviewed: the wiring of the price suggestions into the run (task 5 of [MIL-002]): `runs.py`, `market_result.py`, `price_result.py`, the port `price_text_provider.py`, `PricingRequest` in `price_suggestions.py`, the route `adapters/api/v1/market_analysis.py`, `infrastructure/main.py`, and the contract (`formula`, `limitations`)
- Checklist used: [QC-PY-001] (`qc-programming-python`)
- Scope: full review of the changed and new files
- Language and domain: n/a (technical type)
- Mode: supervised (the AI wrote the code and the pre-review; the reviewer reads the pull request)

## Checklist Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | PEP 8 casing | Pass | ruff `N` rules clean |
| 2 | Names state purpose | Pass | `PricingRequest`, `price_suggestions_document`, `PriceTextProvider` |
| 3 | Formatter and linter, no unexplained suppressions | Pass | clean; one `# type: ignore[arg-type]` in `PricingRequest.settings`, where a dict of the given values is passed to the typed constructor |
| 4 | Signatures annotated | Pass | mypy strict: no issues in 71 files |
| 5 | No bare except, no swallowed exceptions | Pass | No new `except`; a value out of range raises `InvalidRequest` at the start |
| 6 | No mutable defaults, no shadowed builtins | Pass | |
| 7 | Context managers | N-A | |
| 8 | Docstrings | Pass | |
| 9 | Logging | N-A | No new logging |
| 10 | Classes trace to the DCD | Pass, on condition | The repository has no DCD; the changes follow the layers of `docs/architecture.md` |
| 11 | Tests for new behaviour | Pass | 11 new tests: a run with and without `pricing`, the contract accepts the result, 400 for an out of range or unknown value with nothing stored, the AI text changes no figure, insights off gives the text from the figures, and the run of 55,484 bookings with `pricing` stays under 60 seconds |
| 12 | Strict type checking | Pass | |
| 13 | Dependencies | Pass | None added |
| 14 | One place for each piece of knowledge | Pass | The settings are validated in one place, `PricingSettings`; `PricingRequest` only fills the defaults |
| 15 | Imports point inward | Pass | import-linter: 3 contracts kept; the route imports the domain request, not the reverse |
| 16 | SOLID | Pass | `ExecuteRun` depends on the port `PriceTextProvider`; the model is chosen in `main.py` |
| 17 | Layers and folders | Pass | |
| 18 | File names | Pass | |

## Overall Verdict

Go: every Mandatory criterion passes; criterion 10 passes on condition (no DCD exists in this repository). The result schema is now always 1.3, which adds one optional field; a client of 1.2 still reads it, and the contract test says so. The date when no `as_of` is given is the day of the start for the check and the day of the execution for the run; they differ only if a run waits past midnight. Not yet done: a run against the real model, and the service documentation (task 6).

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Accept the code of task 5 | S02 | with the pull request |
| Run one analysis with `pricing` against `phi4:latest` and read the explanations | S01 | after the merge |

---

[MIL-002]: ../milestones/mil-002-price-suggestions.md
[QC-PY-001]: ../../../framework/qc/code/qc-programming-python.md
