# Python Project Development Prompt

You are a senior Python software engineer and solution architect.

We are going to develop a solution consisting of two related Python projects:

- Marimo Notebook Project
- Web API Project

The projects must be designed as professional, maintainable software rather than as a quick prototype.

The primary goals are:

- Reproducibility
- Maintainability
- Testability
- Clear architecture
- Good documentation
- Configurable local AI models
- Detailed logging
- Error handling
- Separation of responsibilities
- Easy future extension


## 1. Start With Planning — DO NOT CODE YET

Before writing any implementation code, analyse the complete requirements and create a development plan.

The plan must explain:

- What the system is intended to do
- The responsibilities of each project
- How the two projects communicate
- Main components
- Data flow
- Dependencies
- Configuration
- Testing strategy
- Logging strategy
- Error handling
- Security considerations
- How notebooks are executed
- How notebook results are generated
- How results are returned as PDF or JSON
- How local AI models are accessed
- How the system can later support additional notebooks or AI providers

Identify ambiguities, assumptions and potential technical problems

If an important requirement is unclear, state the assumption explicitly instead of silently deciding.

## 2. Create the Project Documentation First

Before implementing functionality, create the following documentation.
README.md

Create a comprehensive README containing:

- Project overview
- Purpose
- Project structure
- Architecture overview
- Requirements
- Python version
- Installation
- Configuration
- Environment variables
- How to start the API
- How to run notebooks manually
- How to use LM Studio
- How to use Ollama
- How to run tests
- How to generate notebook output
- API overview
- Example API requests
- Example responses
- Logging
- Troubleshooting
- Development guidelines

The README should explain the relationship between the two projects.

## 3. Architecture Documentation

Create:

`docs/architecture.md`

Document the architecture of the complete solution.

Include:

- System context
- Components
- Responsibilities
- Communication between components
- Data flow
- Notebook execution flow
- AI model flow
- API flow
- Output generation flow
- Error handling flow
- Configuration flow

Use plantuml diagrams where useful.
- At minimum, create diagrams for:
  - System architecture
  - Notebook execution flow
  - API request flow
  - Local AI interaction

The architecture must clearly separate:

```text
           ┌─────────────────────┐
           │       Client        │
           │ Browser / CLI / App │
           └──────────┬──────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │      FastAPI        │
           │      Web API        │
           └──────────┬──────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │  Notebook Registry  │
           │                     │
           │  benchmark          │
           │  market_analysis    │
           └──────────┬──────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │   Notebook Runner   │
           │                     │
           │ Execute / Monitor   │
           │ Store results       │
           └──────────┬──────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
┌─────────────────┐       ┌──────────────────┐
│ Benchmark       │       │ Market Analysis  │
│ Marimo          │       │ Marimo           │
└────────┬────────┘       └─────────┬────────┘
         │                          │
         └────────────┬─────────────┘
                      ▼
          ┌─────────────────────┐
          │   Service Layer     │
          │                     │
          │ Analysis            │
          │ Benchmarking        │
          │ Result processing   │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │    AI Provider      │
          └──────────┬──────────┘
                     │
                     ▼
          ┌──────────┴──────────┐
          ▼                     ▼
    ┌─────────────┐       ┌─────────────┐
    │   Ollama    │       │ LM Studio   │
    └─────────────┘       └─────────────┘
```

Improve this architecture if a better design is identified.

## 4. Requirements Specification

Create:

`docs/requirements.md`

Define functional and non-functional requirements.

Functional requirements should include:

### Benchmark Notebook

The benchmark notebook must:

- Test configured local AI models
- Measure relevant performance metrics
- Store benchmark results
- Present benchmark results
- Make it possible to compare models
- Produce machine-readable results

The purpose is to help determine which locally available AI model is most suitable for our use.

### Market Analysis Notebook

The market analysis notebook must:

- Load the required market data
- Analyse the data
- Use a locally hosted AI model where appropriate
- Support LM Studio
- Support Ollama
- Produce structured results
- Produce human-readable results
- Produce machine-readable results
- The exact AI usage should be separated from the notebook logic so that the AI provider can be changed without rewriting the analysis.

### Web API

The API must provide:

- An endpoint to execute the benchmark notebook
- An endpoint to execute the market analysis notebook
- An endpoint to retrieve notebook results
- An endpoint to return results as JSON
- An endpoint to return results as PDF
- The API should be designed so additional notebooks can be added later without redesigning the entire API.

## 5. Project Structure
Design a professional repository structure.

Prefer a structure similar to:

```text
project/
│
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── docs/
│   ├── architecture.md
│   ├── requirements.md
│   ├── api.md
│   ├── development.md
│   └── decisions/
│       ├── ADR-001-architecture.md
│       ├── ADR-002-marimo.md
│       └── ADR-003-ai-provider.md
│
├── notebooks/
│   ├── benchmark/
│   │   └── benchmark.py
│   │
│   └── market_analysis/
│       └── market_analysis.py
│
├── src/
│   └── app/
│       │
│       ├── api/
│       │   ├── routes/
│       │   │   └── notebooks.py
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── router.py
│       │       ├── notebooks.py
│       │       └── schemas/
│       │           └── notebooks.py
│       │
│       ├── notebooks/
│       │   ├── registry.py
│       │   ├── runner.py
│       │   └── models.py
│       │
│       ├── services/
│       │   ├── benchmark.py
│       │   ├── market_analysis.py
│       │   └── reports.py
│       │
│       ├── ai/
│       │   ├── base.py
│       │   ├── ollama.py
│       │   └── lmstudio.py
│       │
│       ├── config.py
│       ├── logging.py
│       └── main.py
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── output/
│   └── .gitkeep
│
└── scripts/
```

Modify the structure if there is a technically better solution.

Explain why the chosen structure was selected.

## 6. Marimo Project

Use Marimo for the notebooks.

Do not treat the notebooks as ordinary disposable Jupyter notebooks.

They must be executable, reproducible and usable both:

- interactively
- programmatically from the API

Create:

```text
notebooks/
├── benchmark/
│   └── benchmark.py
│
└── market_analysis/
    └── market_analysis.py
```
Keep notebook-specific logic separate from reusable Python application logic.

For example:

```text
notebook
   |
   v
application/service layer
   |
   v
AI provider abstraction
   |
   +---- LM Studio
   |
   +---- Ollama
```

Do not put all application logic directly into the notebook.

## 7. AI Provider Abstraction

Create an abstraction for local AI providers.
The application should not directly depend on LM Studio or Ollama.
For example:

```text
class AIProvider:
    ...
```

Then implement providers such as:

```text
AIProvider
    |
    +── LMStudioProvider
    |
    +── OllamaProvider
```

The exact design should follow good Python practices.

The provider interface should make it possible to add another provider later without changing the notebooks.

Configuration should determine which provider is used.

## 8. Configuration

Use environment variables and/or a configuration system.

Do not hard-code:

- API URLs
- Model names
- Ports
- File paths
- Timeouts
- Output directories
- API keys
- Other environment-specific values

Create:

`.env.example`

Document all configuration variables.

For example:

```text
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=...
LM_STUDIO_BASE_URL=http://localhost:1234
LM_STUDIO_MODEL=...
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
OUTPUT_DIRECTORY=./output
```

Use appropriate validation for configuration values.

## 9. Web API

Use a modern Python web framework, preferably FastAPI, unless there is a strong reason to use another framework.

The API should have a clear structure.

For example:

```text
src/
└── api/
    ├── routes/
    ├── schemas/
    └── dependencies/
```

Use Pydantic models for request and response validation.

Create API documentation automatically through FastAPI/OpenAPI.

Create:

`docs/api.md`

Document every endpoint including:

- HTTP method
- URL
- Purpose
- Parameters
- Request body
- Response
- Error responses
- Example request
- Example response

## 10. Notebook API Design

Design the API so notebooks are treated as registered jobs rather than creating completely separate implementation logic for every notebook.

For example, consider an API design such as:

```text
POST /api/v1/notebooks/{notebook_id}/run
GET  /api/v1/notebooks/{notebook_id}/result
GET  /api/v1/notebooks/{notebook_id}/result/json
GET  /api/v1/notebooks/{notebook_id}/result/pdf
```

However, evaluate whether this is the best REST design before implementing it.

The API must prevent arbitrary filesystem paths from being supplied by clients.

Only registered/approved notebooks may be executed.

## 11. Notebook Execution

Investigate the correct way to execute Marimo notebooks programmatically.

The implementation must:

- Execute the selected notebook
- Capture execution status
- Capture errors
- Store execution metadata
- Store generated output
- Make results available to the API
- Avoid blocking the API unnecessarily if execution is long-running

Consider whether notebook execution should be:

- synchronous
- background task
- job queue

Choose the appropriate approach and document the decision.

If execution can take a significant amount of time, prefer a job-based architecture.
For example:
```text
POST /api/notebooks/benchmark/run

        |
        v

      Job ID

        |
        v

Background execution

        |
        v

Completed result
```

## 12. Results

Define a consistent result format.

Each execution should contain metadata such as:

```json
{
    "job_id": "...",
    "notebook": "benchmark",
    "status": "completed",
    "started_at": "...",
    "completed_at": "...",
    "duration_seconds": 12.4,
    "result": {}
}
```

Design the result model so that it can support different notebook types.

Do not assume every notebook will produce identical data.

## 13. JSON Output

The JSON output must be:

- Valid JSON
- Structured
- Versionable
- Machine-readable
- Suitable for later processing

Avoid putting arbitrary formatted text into JSON when structured data is available.

## 14. PDF Output

Design a separate output/reporting component responsible for PDF generation.

Do not mix PDF generation code into the notebooks or API routes.

For example:
```text
Notebook result
      |
      v
Report service
      |
      v
PDF generator
```

The PDF should contain:

- Title
- Notebook name
- Execution date/time
- Configuration/model information where appropriate
- Summary
- Results
- Relevant tables
- Relevant charts
- Errors/warnings where applicable

Choose an appropriate Python PDF library and document the choice.

## 15. Logging

Implement comprehensive structured logging.

Logging must provide enough information to diagnose problems without exposing secrets.

Log important events such as:

- Application startup
- Configuration validation
- API requests
- Notebook execution started
- Notebook execution completed
- Notebook execution failed
- AI provider selected
- AI request started
- AI request completed
- AI request duration
- Model used
- PDF generation
- JSON generation
- Unexpected exceptions

Never log:

- API keys
- passwords
- authentication tokens
- sensitive user data

Use appropriate log levels:

DEBUG
INFO
WARNING
ERROR
CRITICAL

Prefer structured logging where practical.

## 16. Error Handling

Implement centralized error handling.

### The API must return appropriate HTTP status codes.

For example:

400 Bad Request
404 Not Found
409 Conflict
422 Validation Error
500 Internal Server Error
503 Service Unavailable

### AI provider failures should be handled gracefully.

For example:

- Ollama unavailable
- LM Studio unavailable
- Model not loaded
- Timeout
- Invalid response
- Notebook execution failure
- PDF generation failure

Do not expose internal stack traces to API clients in production responses.

Log the complete diagnostic information internally.

## 17. Testing

Create a proper test strategy.

Use pytest.

Include:

```text
tests/
├── unit/
├── integration/
└── ...
```

Test at least:

### Unit tests

- Configuration
- AI provider abstraction
- LM Studio provider
- Ollama provider
- Notebook registry
- Result handling
- PDF generation
- Validation
- Error handling

### API tests

Test:

- Successful requests
- Invalid requests
- Unknown notebook
- Notebook execution failure
- Result retrieval
- JSON response
- PDF response

### Integration tests

Where practical, test the complete flow:
  - API
  - -> Notebook Runner
  - -> Notebook
  - -> AI provider
  - -> Result
  - -> API

Use mocks for external AI services in normal automated tests.

Do not require a running Ollama or LM Studio instance for ordinary unit tests.

## 18. Code Quality

Use modern Python practices.

Target:

- Python 3.12+ unless compatibility requires otherwise
- Type hints
- Dataclasses/Pydantic where appropriate
- Small focused functions
- Clear separation of concerns
- Dependency injection where appropriate
- No unnecessary global state
- No duplicated logic
- Meaningful exception types
- Consistent naming

Use a formatter and linter such as:

- Ruff
- Black if required
- MyPy or another type checker where appropriate

Prefer Ruff for formatting/linting if it satisfies the project requirements.

## 19. Dependency Management

Use `pyproject.toml`.

Do not create unnecessary dependency lists.

Separate dependencies where appropriate:

runtime dependencies
development dependencies

Document the installation procedure.

## 20. Security

Consider security from the beginning.

At minimum:

- Validate all API input
- Do not allow arbitrary notebook execution
- Do not allow arbitrary filesystem paths
- Protect against path traversal
- Do not expose secrets in logs
- Validate uploaded/generated files if applicable
- Apply sensible request limits
- Configure CORS explicitly
- Separate development and production configuration

Document security decisions.

## 21. Architecture Decision Records

For important technical decisions, create ADRs under:

docs/decisions/

Examples:
ADR-001-project-structure.md
ADR-002-fastapi.md
ADR-003-marimo.md
ADR-004-ai-provider-abstraction.md
ADR-005-notebook-execution.md
ADR-006-result-storage.md
ADR-007-pdf-generation.md

Each ADR should contain:

```markdown
# Decision

## Context

## Options Considered

## Decision

## Consequences
```

Do not create an ADR for trivial decisions.

## 22. Development Workflow

Create:

`docs/development.md`

Document:

- Setting up the development environment
- Installing dependencies
- Environment configuration
- Running Marimo
- Running the API
- Running tests
- Running linting
- Running type checking
- Generating documentation
- Debugging
- Adding a new notebook
- Adding a new AI provider

## 23. Adding a New Notebook

The architecture must make adding another notebook straightforward.

Document the process.

Ideally, adding a notebook should involve:

1. Create notebook
2. Register notebook
3. Define input schema
4. Define result schema
5. Add tests
6. Add API documentation

Avoid modifying unrelated parts of the application.

## 24. Git and CI/CD

Create a GitHub Actions workflow.

The workflow should at minimum:

```text
checkout
    |
    v
install Python
    |
    v
install dependencies
    |
    v
lint
    |
    v
type check
    |
    v
run tests
```

Do not require external AI services for the normal CI pipeline unless explicitly configured.

## 25. Documentation Quality

All public classes, important functions and modules should have useful documentation.

Use docstrings where they add value.

Document:

- Parameters
- Return values
- Exceptions
- Important side effects

Avoid meaningless comments such as:

```markdown
# increment counter
counter += 1
```

Comments should explain why, not merely repeat what the code does.

## 26. Implementation Process

After creating the planning and architecture documentation, implement the project incrementally.

Use this order:

### Phase 1 — Foundation

- Repository structure
- pyproject.toml
- Configuration
- Logging
- Basic documentation
- Testing framework

### Phase 2 — AI abstraction

- AI provider interface
- Ollama provider
- LM Studio provider
- Tests

### Phase 3 — Benchmark notebook

- Benchmark implementation
- Result model
- Output generation
- Tests

### Phase 4 — Market analysis notebook

- Data loading
- Data processing
- AI integration
- Analysis
- Results
- Tests

### Phase 5 — Notebook execution

- Notebook registry
- Notebook runner
- Execution results
- Error handling

### Phase 6 — Web API

- FastAPI
- Routes
- Schemas
- Notebook execution endpoints
- Result endpoints

### Phase 7 — Reports

- JSON output
- PDF generation
- Report service

### Phase 8 — Testing and quality

- Unit tests
- Integration tests
- API tests
- Linting
- Type checking

### Phase 9 — CI/CD

- GitHub Actions
- Automated quality checks

### Phase 10 — Documentation review

Verify that:

- README is complete
- Architecture matches implementation
- API documentation matches implementation
- ADRs document important decisions
- Setup instructions actually work

## 27. Important Development Rule

Do not generate the entire project blindly in one step.

Work incrementally.

Before implementing each major phase:

1. Explain what will be implemented.
2. Identify files that will be created or modified.
3. Explain important design decisions.
4. Implement the changes.
5. Run or describe the relevant tests.
6. Review the implementation for problems.
7. Update documentation if the implementation changed the design.

Never silently change the architecture.

If the implementation reveals that the original architecture is unsuitable, stop and explain the proposed change before proceeding.

## 28. Code Output Requirements

When producing code:

- Provide complete files where practical.
- Do not provide pseudo-code when working implementation is expected.
- Use type hints.
- Include useful docstrings.
- Include comprehensive diagnostic logging.
- Handle exceptions explicitly.
- Do not hard-code environment-specific configuration.
- Do not silently swallow exceptions.
- Do not use insecure shortcuts.
- Keep functions and classes focused.
- Avoid unnecessary abstraction.

Logging should provide enough information to debug failures, including relevant identifiers, execution duration and operation status, while never logging secrets.

## 29. Final Review

When implementation is complete, perform a final review.
Check:

### Architecture

- Is the separation between notebooks and API clear?
- Can new notebooks be added easily?
- Can new AI providers be added easily?

### Code

- Is the code maintainable?
- Is there duplicated logic?
- Are types and error handling appropriate?

### Testing

- Are important components tested?
- Are API endpoints tested?
- Are failure scenarios tested?

### Security

- Can arbitrary notebooks be executed?
- Can arbitrary filesystem paths be accessed?
- Are secrets protected?

### Documentation

- Does README match the implementation?
- Does architecture documentation match the implementation?
- Does API documentation match the actual API?
- Are important decisions documented?

### Operations

- Is logging sufficient?
- Can failures be diagnosed?
- Are configuration errors clear?

At the end, provide a concise project status report containing:

```markdown
Implemented
-----------
...

Tests
-----
...

Known limitations
-----------------
...

Future improvements
-------------------
...
```

Do not claim that something was tested or verified unless it was actually tested or verified
