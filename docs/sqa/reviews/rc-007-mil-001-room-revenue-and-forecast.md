# RC-007 Review of the amendment of MIL-001 (room revenue and useful AI texts)

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-007 |
| CrossReference | [MIL-001], [QC-MIL-001], [QC-LANG-001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-11-01 | Proposed | Claude (AI) | AI at the request of the user, not independent | Initial version | pending |

---

## Artifact Under Review

- Instance reviewed: [MIL-001], amended on 2026-11-01 (tasks 7 and 8, criteria 10 and 11, result schema 1.2)
- Checklist used: [QC-MIL-001]; also [QC-LANG-001] because the type is written in the PO language
- Scope: full review of the change of 2026-11-01 (room revenue, one request for each chart, recommendations and a forecast)
- Language and domain: en / it
- Language reviewer: none; the user's go-ahead in chat on 2026-11-01 closes criterion 9
- Mode: supervised, reviewed by the AI at the request of the user in chat; not independent

## Checklist Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | A concrete deliverable is defined for every gate | Pass | Tasks 7 and 8 name the figures of `room_revenue`, the request for each chart, the forecast with its band, months of history and short-history flag, the guardrail change and the prompt version |
| 2 | Explicit Go/No-Go criteria are stated for each gate | Pass | The change had no criteria; criteria 10 and 11 were added during this review, each checkable by a test against a hand calculation or a fake provider |
| 3 | Dependencies on other milestones are explicitly mapped | Pass | Unchanged. Inside the milestone, the forecast of room revenue in task 8 needs `room_revenue` of task 7, so task 7 is built first |
| 4 | Each milestone is traceable to a Business Case objective or KPI | Pass | Unchanged: the nine analyses and their AI insight (BC-001 objective 6) |
| 5 | Milestone owner and approving reviewer are identified | Pass | Unchanged |
| 6 | Milestone has a defined target date consistent with project constraints | Pass | Unchanged |

## Language and Domain Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | The Metadata table has a `Language` row and a `Domain` row, and neither is a placeholder | Pass | `en` and `it` present |
| 2 | `Language` is a BCP 47 code and `Domain` is a value from the registry's domain list | Pass | `en`; `it` is in the registry list |
| 3 | The content (prose and table cells) is written in the stated language | Pass | The added text is English; checked by the AI, not by a person |
| 4 | The register matches the one the registry gives for the artifact type | Pass | Registry register for this type is used |
| 5 | Domain terms are the PO terms of the domain's dictionary, with no synonyms | Pass | Room revenue, forecast, recommendation and insight are used the same way in the deliverable, the criteria and the tasks |
| 6 | Metadata keys, section headings, IDs and statuses are in English | Pass | Template headings kept |
| 7 | No translated twin (`<name>.<language>.md`) exists beside the document | Pass | No twin file in `docs/` |
| 8 | A change of language or domain since the previous accepted version has a Version History row and was reviewed again | Pass | No change of language or domain |
| 9 | A reviewer competent in the domain, and in the language, has confirmed that the domain terms are used correctly | Pass | The user asked for the change and gave the go-ahead in chat on 2026-11-01 (AI at the request of the user, not independent) |
| 10 | Abbreviations are spelled out on first use, in the stated language | Pass | Only established IT terms (AI, API) are abbreviated |

## Overall Verdict

Go — every criterion of QC-MIL-001 passes after criteria 10 and 11 were added. Criterion 9 of QC-LANG-001 rests on the user's go-ahead in chat and the AI check.

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Show the room revenue, the recommendations and the forecast in NFHotel MIL-026 (rows still to be written) | S01 | After tasks 7 and 8 |

---

[MIL-001]: ../../milestones/mil-001-market-analysis-run-api.md
[QC-MIL-001]: ../../../framework/qc/artifacts/qc-milestones-gateways.md
[QC-LANG-001]: ../../../framework/qc/artifacts/qc-language-domain.md
