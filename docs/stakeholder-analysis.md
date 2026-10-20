# Stakeholder Analysis

## Metadata
| Key | Value |
| --- | --- |
| ID | SA-001 |
| CrossReference | [BC-001] |
| Language | en |
| Domain | it |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-20 | Accepted | Claude (AI) | AI at the request of the user, not independent | Initial version; accepted by the user in chat on 2026-10-20 after RC-002 Go | pending |

---

## Purpose

Name the people who gain or lose from the market analysis service of the NFHotel web application, so that the owner, the reviewer and the other readers of its documents are cited by ID. The method is the power/interest grid with FURPS+ for the concerns. The IDs are those of this project; they are not the IDs of the NFHotel repository.

## Stakeholder Summary Table

| ID | Name | Role/Title | Organization | Power Level | Interest Level | Quadrant | Primary Concern (Business Language) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | Team 2 | Owner of NF Hotel and of this service; its members are all developers; owner of the credentials | NFHotel 2.0 project | HIGH | HIGH | Manage Closely | A market report that works again and a service that builds and runs on its own |
| S02 | Valdamar | Stand-in for the Product Owner; reviewer and approver of the artifacts | NFHotel 2.0 project | HIGH | HIGH | Manage Closely | A clear plan and a result he can accept or reject |
| S03 | VM and AI runtime administrator | Runs the Proxmox VM, the Docker host and the local AI runtime (held by S01 for now) | NFHotel 2.0 project | HIGH | MEDIUM | Keep Satisfied | A container that publishes no port, stays within its limits and does not need the internet to run |
| S04 | Hotel staff | The owner or a Manager who reads the market report in the back office; represented by S01 until a real user is named | NF Hotel | MEDIUM | HIGH | Keep Informed | A report with clear charts and an executive summary he can trust |

## Power/Interest Classification Rationale

- **Manage Closely (S01, S02):** S01 builds and owns the service and its credentials. S02 reviews and accepts every artifact, so nothing moves without S02.
- **Keep Satisfied (S03):** S03 can refuse the VM resources or stop the container, but follows the work only at the points where it is deployed.
- **Keep Informed (S04):** S04 uses the report but does not decide the project; S01 speaks for S04 until a real user is named.

## Primary Concerns and FURPS+ Mapping

| Stakeholder | Concern | FURPS+ |
| --- | --- | --- |
| S01 | The six analyses and the AI summaries are returned for the bookings of the web application | Functionality |
| S01 | The image builds from this repository alone and the release check of the web application is green | Supportability |
| S02 | Each step has a plan, a review record and a clear Go or No-Go | Functionality, Supportability |
| S03 | No published host port, non-root, read-only file system, memory limit | Performance, Supportability |
| S04 | A report that opens, shows its charts and says when there is no result | Usability, Reliability |
| S04 | The AI text is checked, so a wrong summary does not reach the page | Reliability |

## Communication Requirements

| Audience | Channel | Frequency | Deliverable | Phase or milestone |
| --- | --- | --- | --- | --- |
| S01 | Chat with the AI | Each working session | Plan, pull request, summary | Every milestone |
| S02 | Review record and pull request | Once per document and per milestone | The document and its `RC-*` | Every milestone |
| S03 | Pull request and README of `deploy/` | At each deployment | Compose file, env example, limits | The first milestone |
| S04 | Via S01 | When the page changes | Report page | The web application milestone that uses the API |

## Conflicting Interests and Mitigations

| Conflict | Mitigation |
| --- | --- |
| S01 wants the AI summaries now; S03 wants the VM load limited | A run asks for insights only when told to, one run at a time, and the container has a memory limit |
| S01 wants to change the contract quickly; S04 needs a stable report | The contract is one file, agreed with the web application before the code, and a test fails on any difference |

## Traceability Analysis

| Stakeholder | Actor or use case | Business Case objective |
| --- | --- | --- |
| S01 | Starts a run through the web application | Objectives 1 to 4 of [BC-001] |
| S02 | Reviews and accepts the artifacts | Objectives 1 to 4 of [BC-001] |
| S03 | Deploys and operates the container | Objective 4 of [BC-001] |
| S04 | Reads the market report (NFHotel US-001.01) | Objectives 2 and 3 of [BC-001] |

## Sign-Off

| Stakeholder | Decision | Date |
| --- | --- | --- |
| S02 | pending (accepted by the user in chat on 2026-10-20) | pending |

---

[BC-001]: ./business-case.md
