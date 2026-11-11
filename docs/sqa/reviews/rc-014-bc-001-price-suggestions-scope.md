# RC-014 Review of BC-001 objective 5 and the contract for price suggestions (MIL-002 task 1)

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-014 |
| CrossReference | [BC-001], [QC-BC-001], [MIL-002] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-11-11 | Accepted | Claude (AI) | S02 | Initial version; pre-review by the AI, not independent; accepted by the user in chat on 2026-11-11 | pending |

---

## Artifact Under Review

- Instance reviewed: [BC-001] (objective 5 and the scope item), with the `pricing` block, `price_suggestions` and the sample file of `openapi/market-contract.yaml`
- Checklist used: [QC-BC-001]
- Scope: delta re-review of criteria 3, 4 and 8; the contract is checked by its tests (27 pass), not by a QC checklist
- Language and domain: en / it
- Language reviewer: none; the reviewer reads the language and knows the domain
- Mode: supervised (the AI wrote the change and the pre-review; the reviewer accepts in chat)

## Checklist Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 3 | Success criteria are measurable | Pass | Objective 5 names the horizon (the next two months), the determinism ("the same input always gives the same result") and the AI limit; the figures are the Go/No-Go criteria of MIL-002 |
| 4 | Scope separates In Scope vs Out of Scope | Pass | The price suggestions are an In Scope item; the page and the approval stay with NFHotel and are in Out of Scope already ("the web application's page and database") |
| 8 | Clear, unambiguous recommendation | Pass | Unchanged |

Contract: `pricing` is optional and every value has a default; `price_suggestions` is optional; `schema_version` accepts `1.2` and `1.3`, so a client of 1.2 still reads a result and the implementation, which still writes 1.2, still matches the file. A test validates the sample, a result of schema 1.3, an empty `pricing` block, an unknown field and a suggestion without its figures.

## Overall Verdict

Go: the criteria that the change touches pass, and the contract tests pass. The defaults for the open points (two earlier years at least, a low threshold of 0.40, a week as the unit) are taken from NFHotel MIL-055 and are for S01 to confirm; a change of them is a change of the defaults only.

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Accept the change of BC-001 | S02 | 2026-11-13 |
| Confirm the defaults of `pricing` (minimum of earlier years 2, low threshold 0.40, a week as the unit) | S01 | before MIL-002 task 3 |
| Agree the contract with NFHotel MIL-071 task 2 | S01 | before MIL-002 task 2 |

---

[BC-001]: ../business-case.md
[MIL-002]: ../milestones/mil-002-price-suggestions.md
[QC-BC-001]: ../../../framework/qc/artifacts/qc-business-case.md
