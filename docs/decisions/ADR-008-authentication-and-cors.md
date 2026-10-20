# ADR-008: Bearer token authentication and explicit CORS

Status: Proposed

## Context

The API can start expensive jobs and return business data. It is used by trusted internal clients; per-user accounts are out of scope.

## Options Considered

1. **No authentication**: unacceptable once the API is reachable beyond localhost.
2. **Static bearer token** from configuration.
3. **OAuth/OIDC or per-user accounts**: more than required now.

## Decision

Static bearer token (`API_TOKEN`) checked by a FastAPI dependency on all routes except `/health`, using constant-time comparison. CORS allows only origins listed in `CORS_ALLOWED_ORIGINS`; no wildcard in production. In `production`, startup fails if the token is missing or CORS is unset. Tokens are never logged.

## Consequences

- Simple to operate and test.
- One shared token: no per-user audit or revocation except by rotation.
- The dependency is isolated in `adapters/api`, so replacing it with OIDC later does not affect use cases.
- The token should travel over HTTPS when not on localhost; TLS termination is a deployment concern.
