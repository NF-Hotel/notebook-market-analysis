# MIL-001 Market analysis run API

## Metadata
| Key | Value |
| --- | --- |
| ID | MIL-001 |
| CrossReference | [BC-001], [SA-001], [PP-001] |
| Language | en |
| Domain | it |

## Version History
| Date | Status | Author | Reviewer | Change | Commit |
| --- | --- | --- | --- | --- | --- |
| 2026-10-20 | Deprecated | Claude (AI) | S02 | Initial version; the same phase as NFHotel MIL-027, planned in the repository where the code goes | [34f6b14] |
| 2026-10-20 | Accepted | Claude (AI) | AI at the request of the user, not independent | Three analyses added (occupancy, occupancy on holidays, correlations), so nine, with the number of rooms in the run request; asked for by S01 for a course assignment; accepted by the user in chat on 2026-10-20 after RC-005 Go | [d2ae4cf] |

---

## Purpose

Give the market analysis service the analysis that the website needs. NFHotel MIL-004 deployed `NF-Hotel/Notebook_Market_Analysis` and NFHotel MIL-026 was built on its `POST /analyze?insights=true`. That repository is gone from GitHub: its successor `NF-Hotel/notebook-market-analysis` is a new service of which only `/health` and the holiday calendar are built, so the image of the old pinned commit (`6c11cbf2`) can no longer be built and the release check of pull request 180 fails. The milestone builds the missing part in the new service, in its Clean Architecture layers: the nine analyses of the bookings (lead time, holidays, seasonality, cancellations, room value, guest mix, occupancy, occupancy on holidays, correlations), the AI executive summary and suggestions of each, and a run API (start, state, result) behind the key `X-API-Key`. This is the same phase as NFHotel MIL-027, planned here because the code goes in this repository and its plan-first gate needs a milestone here.

## Deliverable

- **Contract first.** `openapi/market-contract.yaml` of the market analysis service gets the run paths (`POST /api/v1/market-analysis/runs`, `GET /api/v1/market-analysis/runs/{id}`, `GET /api/v1/market-analysis/runs/{id}/result`) with the booking as input (the fields of `MarketBookingDto` of the website, an optional period) and result schema 1.1 as output (the sample `docs/test-data/market-analysis-result.json` of this repository is the first test file of both sides).
- The nine analyses over the bookings that are posted, in the domain and application layers, with unit tests; no notebook library in the image: the six of the first version (lead time, holidays, seasonality, cancellations, room value, guest mix) and three new ones, occupancy (the share of room nights that are taken, by month and overall), occupancy on holidays (the same share on holiday days against other days) and correlations (the Spearman correlation between the numeric booking fields and cancelled, as a matrix). The run request carries `room_count` (the rooms of the hotel), because the bookings do not say how many rooms there are; the result gives for each analysis the formula it used and what it cannot say (`limitations`).
- An AI port and adapters (Ollama and LM Studio, as `docs/architecture.md` of this repository plans) that write an `insight` with `executive_summary` and `improvement_suggestions` for every analysis, and one observation for every chart, what the AI sees in that series (`observations`, each with the `series` path of the group figures it reads, its text and its evidence), written in the same request as the insight of the analysis so that a run stays within its 12 minutes, with a guardrail that gives `GUARDRAIL_REJECTED` and leaves the numbers untouched.
- A background run with one run at a time, a state (`queued`, `running`, `completed`, `failed`) and the result kept in the output volume.
- Deploy: the image and `deploy/docker-compose.yml` of this repository start the service with the AI settings in its env file; the Dockerfile still needs no network at build time other than the package index.
- Unchanged: the holiday calendar paths and their contract.

## Go / No-Go Criteria

| # | Criterion (objectively checkable) | Go | No-Go |
| --- | --- | --- | --- |
| 1 | The contract file describes the three run paths and result schema 1.1, and a test fails when the implementation and the contract differ | Yes | No |
| 2 | A start with the sample bookings returns at once with a run id; the state follows `queued`, `running`, `completed`; a second start while a run is active is refused with a stable error code | Yes | No |
| 3 | The result of a completed run has schema version 1.1 with the nine analyses; a test compares each figure with a hand calculation on a small booking file, among them an occupancy of 50 % for two rooms with one room taken for the whole period, an occupancy on holidays that differs from the one on other days, and a correlation of +1 and -1 for two series built to move together and apart | Yes | No |
| 4 | With a fake AI provider every analysis has an `insight` with an executive summary and suggestions and every series of its findings (at most 8) has an observation that names the numbers it rests on, which a test finds in the series; a rejected output gives `GUARDRAIL_REJECTED` for that analysis only, and an observation that names a number not in the series is dropped; with insights off there is no `insight` and no AI call; every request to the model carries the maximum output tokens, 32768 unless the env file says otherwise | Yes | No |
| 5 | A missing or wrong `X-API-Key` gives 401 on every run path; `/health` needs no key | Yes | No |
| 6 | A body with an invalid booking, an unknown field type or an empty list is refused with 400 and a stable code, and nothing is stored | Yes | No |
| 7 | A run of 55,484 bookings completes with the fake AI provider in under 60 seconds in the tests of this repository, and the container stays within the `mem_limit` that its compose file sets (measured in the same test run) | Yes | No |
| 8 | The image builds from the repository alone (no fetch of another repository), installs hash-locked dependencies with `--only-binary :all:` (the SonarCloud rules docker:S8541 and docker:S8544 report nothing), publishes no host port and runs as a non-root user with a read-only file system | Yes | No |
| 9 | Tests pass, the linters of this repository are clean, and `qc-programming-python` and `qc-yaml` reviews have the verdict `Go` | Yes | No |

## Dependencies

| Depends on | Reason |
| --- | --- |
| NFHotel MIL-004 | The deployment pattern of the market analysis service behind the VM network |
| NFHotel ADR-0003 | The VM and the network rules |

## Traceability

| Business Case objective / KPI / user story | Reference |
| --- | --- |
| Objectives 1 to 4 of BC-001 | All tasks |
| NFHotel US-001.01 View the market analysis | Tasks 2 to 4 |

## Ownership

| Role | Stakeholder ID (SA) |
| --- | --- |
| Owner | S01 |
| Approving reviewer | S02; S03 for the container and the ports |

## Target Date

2026-11-13 — three and a half weeks from the plan, so that NFHotel MIL-026 can follow by 2026-11-27; for S01 to confirm.

## Tasks

| # | Task | Summary | Needs its own Use Case/User Story? | Reference |
| --- | --- | --- | --- | --- |
| 1 | Agree the run contract | Add the three run paths and result schema 1.1 to `openapi/market-contract.yaml` of the market analysis service, from the input of `MarketBookingDto` and the sample result `docs/test-data/market-analysis-result.json` of the NFHotel repository, and add a contract test that reads the file. Why: the website and the service are built against the same file. | No | |
| 2 | Domain and the nine analyses | Write the booking and the nine analyses (lead time, holidays, seasonality, cancellations, room value, guest mix, occupancy (the share of room nights that are taken, by month and overall), occupancy on holidays (the same share on holiday days against other days) and correlations (the Spearman correlation between the numeric booking fields and cancelled, as a matrix)) in the domain and application layers with unit tests against hand calculated figures. The holidays analyses read the holiday calendar the service already has. Occupancy is the room nights taken divided by `room_count` times the nights of the period; a night is taken from arrival to the day before departure. Each analysis returns its formula and its limitations. | No | NFHotel US-001.01 (a plain task here: the story is in the NFHotel repository) |
| 3 | AI insights | An AI port and the Ollama and LM Studio adapters; one insight per analysis with executive summary and suggestions and one observation per chart (what the AI sees in the series, with the numbers it rests on), asked in the same request as the insight; the guardrail and `GUARDRAIL_REJECTED`; a fake provider for the tests; settings in the env file, among them the maximum output tokens of a model answer, 32768 by default (a reasoning model needs the room to think and still write the answer). | No | NFHotel US-001.01 (a plain task here: the story is in the NFHotel repository) |
| 4 | Run API and result storage | The three run paths, one run at a time in the background, state and result in the output volume, `X-API-Key` on every path, stable error codes. | No | NFHotel US-001.01 (a plain task here: the story is in the NFHotel repository) |
| 5 | Image and compose | Lock the dependencies of the image with hashes and install them with `--only-binary :all:` (SonarCloud docker:S8541 and docker:S8544 failed the quality gate of pull request 2), keep the Dockerfile free of other repositories, add the AI settings to `deploy/market-analysis.env.example`, check the limits for a run of 55,484 bookings and update the README of this repository. | No | |
| 6 | Check and review | Tests, linters and the reviews against `qc-programming-python` and `qc-yaml`; record the RC. | No | |

---

[BC-001]: ../business-case.md
[SA-001]: ../stakeholder-analysis.md
[PP-001]: ../project-plan.md
[34f6b14]: https://github.com/NF-Hotel/notebook-market-analysis/commit/34f6b14a776ce9c75294979f88563378287839bf
[d2ae4cf]: https://github.com/NF-Hotel/notebook-market-analysis/commit/d2ae4cf7523aca7c5423059dea5b18c391764fda
