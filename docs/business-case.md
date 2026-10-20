# Business Case

## Metadata
| Key | Value |
| --- | --- |
| ID | BC-001 |
| CrossReference | [SA-001] |
| Language | en |
| Domain | it |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-20 | Deprecated | Claude (AI) | AI at the request of the user, not independent | Initial version, written when the run API of the NFHotel web application had to move here from `Notebook_Market_Analysis`; accepted by the user in chat on 2026-10-20 after RC-001 Go | [34f6b14] |
| 2026-10-20 | Accepted | Claude (AI) | AI at the request of the user, not independent | Amended: objective 2 and the scope name nine analyses (occupancy, occupancy on holidays and correlations added), asked for by S01 for a course assignment; accepted by the user in chat on 2026-10-20 after RC-004 Go | [d2ae4cf] |

---

## Executive Summary

The NFHotel web application shows its owner a market analysis of the hotel bookings with an executive summary written by a local AI model. The service that made the analysis (`NF-Hotel/Notebook_Market_Analysis`) no longer exists on GitHub, and its successor, this repository, offers only a health check and the holiday calendar. This project builds the missing part: an authenticated HTTP API that takes the bookings, runs nine analyses, asks a local AI model for an insight on each analysis and an observation on each chart, and returns a result that the web application stores and shows. The benchmark of local models, the other half of the repository, is outside this Business Case.

## Methodological and Standards Foundation

The method is Larman's *Applying UML and Patterns*, as the NFHotel project uses it: Business Case, Stakeholder Analysis, Project Plan, milestones, then code, each step reviewed. Quality is judged against ISO/IEC 25010:2023. The code follows Clean Architecture (`docs/architecture.md`) and the contract-first rule: the OpenAPI file in `openapi/` is agreed with the web application before the code.

## Problem Statement

- The web application's market analysis page calls `POST /analyze?insights=true` on a service whose repository and pinned commit are gone; the release build of the web application fails because the image cannot be built.
- The successor service has no analysis, no AI adapter and no run API, so nothing can replace the old service.
- The belief that would kill the project if false: a local AI model (Ollama or LM Studio) can write a usable executive summary for an analysis of about 55,000 bookings within about 12 minutes.

## Business Opportunity

With the analysis in this service, the owner reads a market report in the back office again, the web application builds without fetching a repository that is not there, and the analysis can be extended (more analyses, other data sources) in one place that follows a documented structure.

## Objectives

1. Provide the run API (start, state, result) behind a key, with a contract in `openapi/market-contract.yaml` that the web application is built against.
2. Compute the nine analyses (lead time, holidays, seasonality, cancellations, room value, guest mix, occupancy, occupancy on holidays, correlations) from the bookings posted to a run and the number of rooms, with figures that a test checks by hand, each with its formula and its limitations.
3. Write an executive summary and suggestions for each analysis, and an observation of what the AI sees for each chart, with a local AI model, and keep the numbers when the model fails or its output is rejected.
4. Ship an image that builds from this repository alone and runs without a published host port.

## Scope

### In Scope

- The run API, its contract, its key, its background run and its stored result.
- The nine analyses and the AI insights with a guardrail.
- The image and the compose file on the internal network of the NFHotel VM.

### Out of Scope

- The benchmark notebook and its API (`FR-B` in `docs/requirements.md`).
- A reader of market data from a JSON API or CSV files, and PDF or HTML reports.
- User accounts: the web application is the only client.
- The web application's page and database (they belong to NFHotel MIL-026).

## Expected Benefits

### Tangible Benefits

- The release check of the web application builds the image without another repository.
- The owner gets a market analysis of the bookings with an AI summary on the back office page.

### Intangible Benefits

- One documented place for the analysis, with a contract both sides test against.
- Data stays on the hotel's own network: a local model, no cloud AI.

## Strategic Alignment

The project serves objective 6 of the NFHotel Business Case: the market analysis service that gives the owner a market analysis with an AI analysis. It keeps the NFHotel principle that guest data is not sent to an outside AI service.

## Success Criteria

| Criterion | Target |
| --- | --- |
| Contract test | The implementation and `openapi/market-contract.yaml` agree; the test fails on any difference |
| Run of the sample bookings | `completed` with nine analyses and schema version 1.1 |
| Run of 55,484 bookings with a fake AI provider | Under 60 seconds in the tests |
| Insight per analysis with a fake AI provider | One for each, `GUARDRAIL_REJECTED` for a rejected one only |
| Image | Builds from this repository, no published host port, non-root, read-only file system |

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| A local model is too slow or writes unusable text | The insights are late or missing | A run can ask for no insights; the numbers are returned even when the model fails; the guardrail rejects bad output |
| The figures of the new analyses differ from those of the old service | The web application's charts change without a reason | Hand-calculated tests, and a comparison with the sample result kept in the NFHotel repository |
| The contract changes while the web application is built | Rework on both sides | Contract first, one file, a test on both sides |
| The repository is renamed or rewritten again | The web application's build breaks again | The web application pins a commit of this repository and its pull request checks that the image builds |

## Assumptions

- The only client is the NFHotel web application, on the internal network, with a key in a header.
- The bookings are posted in the run request; the service reads no database.
- A local AI runtime is reachable from the VM (Ollama or LM Studio).
- Product Owner: S01. Reviewer and approver: S02. The people the service is for are reached by S01 only.

## Constraints

- Docker is the only tool needed on the host.
- Target date of the run API: 2026-11-13 (NFHotel MIL-028).
- Python 3.13 and the layers of `docs/architecture.md`; dependencies point inward.
- No secret is kept in git.

## Cost–Benefit Assessment

Qualitative, because no money changes hands and the work is a few working sessions.

| Costs | Benefits |
| --- | --- |
| About two weeks of engineering by S01's team, with AI help | The market report works again and the web application builds cleanly |
| Running a local AI model on the VM | No guest data leaves the hotel network |

## Stakeholders

| Stakeholder ID (SA) | Interest in this project |
| --- | --- |
| S01 | Owns the project and the credentials; needs the report in the back office |
| S02 | Reviews and approves each step as the stand-in for the Product Owner |
| S03 | Runs the VM and the AI runtime; needs a container that publishes no port |
| S04 | Reads the market report in the back office; represented by S01 until a real user is named |

## Recommendation

Proceed.

---

[SA-001]: ./stakeholder-analysis.md
[34f6b14]: https://github.com/NF-Hotel/notebook-market-analysis/commit/34f6b14a776ce9c75294979f88563378287839bf
[d2ae4cf]: https://github.com/NF-Hotel/notebook-market-analysis/commit/d2ae4cf7523aca7c5423059dea5b18c391764fda
