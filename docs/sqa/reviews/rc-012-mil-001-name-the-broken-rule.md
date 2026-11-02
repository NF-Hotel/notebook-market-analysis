# RC-012 Review of the amendment of MIL-001 (name the broken rule in the next request)

## Metadata
| Key | Value |
| --- | --- |
| ID | RC-012 |
| CrossReference | [MIL-001], [QC-MIL-001], [QC-LANG-001] |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-11-02 | Proposed | Claude (AI) | AI at the request of the user, not independent | Initial version | [18b30d4] |

---

## Artifact Under Review

- Instance reviewed: [MIL-001], amended on 2026-11-01 (task 15 and criterion 18)
- Checklist used: [QC-MIL-001]; also [QC-LANG-001] because the type is written in the PO language
- Scope: full review of the change of 2026-11-01 (the rule that rejected a text is named in the next request, up to three requests for the overall interpretation, a prompt that asks for findings in the present or past tense)
- Language and domain: en / it
- Language reviewer: none; the user's go-ahead in chat on 2026-11-01 closes criterion 9
- Mode: supervised, reviewed by the AI at the request of the user in chat; not independent

## Checklist Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | A concrete deliverable is defined for every gate | Pass | Task 15 names the four parts (the guardrail tells which rule rejected, the next request carries that reason, at most three requests for the overall interpretation, the prompt change and version), the tests and the wiki pages; the Deliverable has an entry for it |
| 2 | Explicit Go/No-Go criteria are stated for each gate | Pass | Criterion 18 is checkable with the fake model: the second request carries the forbidden word or the figure, a text is kept on the third request, and three rejections give the text from the figures |
| 3 | Dependencies on other milestones are explicitly mapped | Pass | Unchanged. Inside the milestone, task 15 changes the code of tasks 12 and 14 and needs task 14 (the second try) first |
| 4 | Each milestone is traceable to a Business Case objective or KPI | Pass | Unchanged: the nine analyses and their AI insight (BC-001 objective 6); the row "All tasks" covers task 15 |
| 5 | Milestone owner and approving reviewer are identified | Pass | Unchanged |
| 6 | Milestone has a defined target date consistent with project constraints | Pass | Unchanged |

## Language and Domain Results

| # | Criterion | Status | Evidence/Notes |
| --- | --- | --- | --- |
| 1 | The Metadata table has a `Language` row and a `Domain` row, and neither is a placeholder | Pass | `en` and `it` present |
| 2 | `Language` is a BCP 47 code and `Domain` is a value from the registry's domain list | Pass | `en`; `it` is in the registry list |
| 3 | The content (prose and table cells) is written in the stated language | Pass | The added text is English; checked by the AI, not by a person |
| 4 | The register matches the one the registry gives for the artifact type | Pass | Registry register for this type is used |
| 5 | Domain terms are the PO terms of the domain's dictionary, with no synonyms | Pass | Guardrail, rule, overall interpretation and figure are used as in the earlier tasks |
| 6 | Metadata keys, section headings, IDs and statuses are in English | Pass | Template headings kept |
| 7 | No translated twin (`<name>.<language>.md`) exists beside the document | Pass | No twin file in `docs/` |
| 8 | A change of language or domain since the previous accepted version has a Version History row and was reviewed again | Pass | No change of language or domain |
| 9 | A reviewer competent in the domain, and in the language, has confirmed that the domain terms are used correctly | Pass | The user asked for the change and gave the go-ahead in chat on 2026-11-01 (AI at the request of the user, not independent) |
| 10 | Abbreviations are spelled out on first use, in the stated language | Pass | Only established IT terms (AI) are abbreviated |

## Overall Verdict

Go — every criterion of QC-MIL-001 passes. Criterion 9 of QC-LANG-001 rests on the user's go-ahead in chat and the AI check. The cause named in the task was found by replaying the request twice against the model; another forbidden word may turn up. Criterion 18 does not claim that every overall text will pass, and a run after the deploy shows it.

## Action Items

| Action | Owner | Due |
| --- | --- | --- |
| Run a new analysis after the deploy and check that `insights.overall` has `source: ai` and names all nine analyses | S01 | After task 12 |

---

[MIL-001]: ../../milestones/mil-001-market-analysis-run-api.md
[QC-MIL-001]: ../../../framework/qc/artifacts/qc-milestones-gateways.md
[QC-LANG-001]: ../../../framework/qc/artifacts/qc-language-domain.md
[18b30d4]: https://github.com/NF-Hotel/notebook-market-analysis/commit/18b30d4ed0f6b5c57a334f0816dbca3390ec9ba3
