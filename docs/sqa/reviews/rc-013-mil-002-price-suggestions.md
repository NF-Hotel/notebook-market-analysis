# RC-013 Review of MIL-002 Price suggestions from the market analysis

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-013 |
| CrossReference | [MIL-002], [QC-MIL-001], [QC-LANG-001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-11-11 | Accepted | Claude (AI) | S02 | Initial version; pre-review by the AI, not independent; accepted by the user in chat on 2026-11-11 | pending |

---

## Artifact Under Review

- Instance reviewed: [MIL-002]
- Checklist used: [QC-MIL-001]; also [QC-LANG-001] because the type is written in the PO language
- Scope: full review
- Language and domain: en / it (the Metadata rows of MIL-002)
- Language reviewer: none; the reviewer reads the language and knows the domain
- Mode: supervised (the AI wrote the milestone and the pre-review; the reviewer accepts in chat)

## Checklist Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | A concrete deliverable is defined for every gate | Pass | Deliverable lists the contract (schema 1.3), the holidays of the horizon, the history rule, the other suggestions, the AI text and the tests |
| 2 | Explicit Go/No-Go criteria are stated for each gate | Pass | 8 criteria; the rule has hand calculated figures (85 percent in two years, exactly 80 and 79.9 percent, single rooms only) and the AI has a check that it changes no price |
| 3 | Dependencies on other milestones are explicitly mapped | Pass | MIL-001 for the run API, the analyses, the AI port and the guardrail; NFHotel MIL-071, which reads the result |
| 4 | Each milestone is traceable to a Business Case objective or KPI | Pass, on condition | The Business Case of this repository (BC-001) names objectives 1 to 4 and the nine analyses, not price suggestions; the milestone traces to NFHotel objective 29. Task 1 adds the scope item to BC-001 before any code |
| 5 | Milestone owner and approving reviewer are identified | Pass | Owner S01; approving reviewer S02 |
| 6 | Milestone has a defined target date consistent with project constraints | Pass | 2026-11-27, two weeks before NFHotel MIL-071 can follow; marked for S01 to confirm |

## Language and Domain Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | `Language` and `Domain` rows exist and are no placeholders | Pass | en and it |
| 2 | BCP 47 code and a domain from the registry list | Pass | |
| 3 | Content in the stated language | Pass | English |
| 4 | Register matches the registry (IT Executive English for MIL) | Pass | |
| 5 | Domain terms are those of the dictionary, no synonyms | Pass | Surcharge, discount, season and price suggestion are the terms of NFHotel MIL-055 |
| 6 | Keys, headings, IDs and statuses in English | Pass | |
| 7 | No translated twin | Pass | One file |
| 8 | A change of language or domain has a Version History row | N-A | First version |
| 9 | A reviewer competent in the domain has confirmed the terms | Pass, on condition | The reviewer reads and confirms in chat |

## Overall Verdict

Go: every Mandatory criterion passes; two pass on condition (criterion 4 of QC-MIL-001, which needs BC-001 amended before any code, and criterion 9 of QC-LANG-001, which the reviewer's acceptance fulfils). The milestone moves a rule from NFHotel MIL-055 to the service and keeps the AI out of the price; S01 chose both in chat on 2026-11-11. The open points are in the action items.

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Amend BC-001 with the scope item "price suggestions" (task 1) and review it | S02 | before task 2 |
| Accept MIL-002 or ask for changes | S02 | 2026-11-13 |
| Confirm the target date 2026-11-27 | S01 | 2026-11-13 |
| Decide the minimum number of earlier years, the default low occupancy threshold and whether the rule reads a week or a day | S01 | before task 3 |
| Agree the contract of task 1 with NFHotel MIL-071 | S01 | before task 2 |

---

[MIL-002]: ../../milestones/mil-002-price-suggestions.md
[QC-MIL-001]: ../../../framework/qc/artifacts/qc-milestones-gateways.md
[QC-LANG-001]: ../../../framework/qc/artifacts/qc-language-domain.md
