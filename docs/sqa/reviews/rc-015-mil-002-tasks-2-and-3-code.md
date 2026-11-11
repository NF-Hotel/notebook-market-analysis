# RC-015 Review of the code of MIL-002 tasks 2 and 3

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-015 |
| CrossReference | [MIL-002], [QC-PY-001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-11-11 | Proposed | Claude (AI) | S02 | Initial version; pre-review by the AI, not independent | pending |

---

## Artifact Under Review

- Instance reviewed: `src/app/domain/analyses/price_history.py` and `price_suggestions.py`, with `tests/unit/domain/analyses/test_price_history.py` and `test_price_suggestions.py` (tasks 2 and 3 of [MIL-002])
- Checklist used: [QC-PY-001] (`qc-programming-python`)
- Scope: full review of the new files
- Language and domain: n/a (technical type)
- Mode: supervised (the AI wrote the code and the pre-review; the reviewer reads the pull request)

## Checklist Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | PEP 8 casing | Pass | ruff `N` rules clean |
| 2 | Names state purpose | Pass | `OccupancyHistory`, `week_blocks`, `same_holiday_in`; `_judge` is the one terse name and has a docstring-free body of 20 lines |
| 3 | Formatter and linter, no unexplained suppressions | Pass | `ruff format` and `ruff check` clean; two `# type: ignore[arg-type]` in the tests pass a dict of settings to a typed constructor |
| 4 | Signatures annotated | Pass | mypy strict: no issues in 68 files |
| 5 | No bare except, no swallowed exceptions | Pass | No `except`; settings out of range raise `InvalidRequest` |
| 6 | No mutable defaults, no shadowed builtins | Pass | Tuples and frozen dataclasses |
| 7 | Context managers | N-A | No files, locks or connections |
| 8 | Docstrings | Pass | Public functions and classes have one |
| 9 | Logging | N-A | The domain logs nothing |
| 10 | Classes trace to the DCD | Pass, on condition | The repository has no DCD; the classes follow `docs/architecture.md` (domain analyses beside `occupancy.py`) |
| 11 | Tests for new behaviour | Pass | 21 new tests with hand calculated figures (85 percent, exactly 80 and 80.1, pooled 32 of 40, Easter 2024 and 2025, week 53); no order or network dependence; the new files have 99 and 100 percent coverage |
| 12 | Strict type checking | Pass | strict mypy |
| 13 | Dependencies | Pass | None added |
| 14 | One place for each piece of knowledge | Pass | Occupancy counts come from `nightly_counts` of the occupancy analysis, not a second copy |
| 15 | Imports point inward | Pass | import-linter: 3 contracts kept; the domain imports no framework |
| 16 | SOLID | Pass | The history (what happened) and the rule (what to suggest) are two modules |
| 17 | Layers and folders | Pass | In `domain/analyses` |
| 18 | File names | Pass | `price_history.py`, `price_suggestions.py` |

## Overall Verdict

Go: every Mandatory criterion passes; criterion 10 passes on condition (no DCD exists in this repository). Known limits, stated in the code as `limitations`: the occupancy is that of the whole hotel and not by room size, and a holiday with low history gets a discount with the reason `low_history`, where MIL-002 speaks of "a note". Not yet covered: the AI text (task 4) and the wiring into the run and schema 1.3 (task 5).

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Confirm that a holiday with low history gives a discount and not only a note | S01 | before task 5 |
| Accept the code of tasks 2 and 3 | S02 | with the pull request |

---

[MIL-002]: ../milestones/mil-002-price-suggestions.md
[QC-PY-001]: ../../../framework/qc/code/qc-programming-python.md
