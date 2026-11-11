# RC-016 Review of the code of MIL-002 task 4

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-016 |
| CrossReference | [MIL-002], [QC-PY-001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-11-11 | Proposed | Claude (AI) | S02 | Initial version; pre-review by the AI, not independent | pending |

---

## Artifact Under Review

- Instance reviewed: `src/app/application/price_explanations.py` with `tests/unit/application/test_price_explanations.py`, and the prompt version 8 in `insight_prompt.py` (task 4 of [MIL-002])
- Checklist used: [QC-PY-001] (`qc-programming-python`)
- Scope: full review of the new file; the prompt version and three tests that name it
- Language and domain: n/a (technical type)
- Mode: supervised (the AI wrote the code and the pre-review; the reviewer reads the pull request)

## Checklist Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | PEP 8 casing | Pass | ruff `N` rules clean |
| 2 | Names state purpose | Pass | `PriceExplainer`, `broken_rule`, `fallback_text`, `allowed_numbers` |
| 3 | Formatter and linter, no unexplained suppressions | Pass | `ruff format` and `ruff check` clean; no suppression in the new file |
| 4 | Signatures annotated | Pass | mypy strict: no issues in 69 files |
| 5 | No bare except, no swallowed exceptions | Pass | Only the model errors and a JSON error are caught; each is logged as a warning and gives the fallback text by design |
| 6 | No mutable defaults, no shadowed builtins | Pass | |
| 7 | Context managers | N-A | No files, locks or connections |
| 8 | Docstrings | Pass | |
| 9 | Logging | Pass | `logging`; the message holds the error of the model call, no figures of the hotel |
| 10 | Classes trace to the DCD | Pass, on condition | The repository has no DCD; the class follows the pattern of `ModelInsightProvider` and the model port |
| 11 | Tests for new behaviour | Pass | 14 tests with a fake model: a good answer, a price, a second try that carries the broken rule, two rejections, a failed model, an empty answer, a number or a month that is not the suggestion's, a cause, ideas kept, dropped and limited to three, no model; coverage of the file 96 percent |
| 12 | Strict type checking | Pass | |
| 13 | Dependencies | Pass | None added |
| 14 | One place for each piece of knowledge | Pass | The claim check is `forbidden_phrase_in` of the guardrail of MIL-001, not a second list; `strip_html` and the number reader are reused |
| 15 | Imports point inward | Pass | import-linter: 3 contracts kept |
| 16 | SOLID | Pass | The explainer only asks and checks; the suggestions are not changed by it (a test shows it) |
| 17 | Layers and folders | Pass | In `application` |
| 18 | File names | Pass | |

## Overall Verdict

Go: every Mandatory criterion passes; criterion 10 passes on condition (no DCD exists in this repository). The guardrail is a narrow one for this text: it refuses what is not the suggestion's own, but it cannot tell whether a sentence is true to the figures. The AI never sets a price, a percentage or a date, since the suggestion comes from the rule and the explainer returns only text. Not yet covered: the wiring into the run and schema 1.3 (task 5).

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Accept the code of task 4 | S02 | with the pull request |
| Read a real explanation from `phi4:latest` once the run carries it (task 5) | S01 | after task 5 |

---

[MIL-002]: ../milestones/mil-002-price-suggestions.md
[QC-PY-001]: ../../../framework/qc/code/qc-programming-python.md
