# Testing

## Test Setup

Test dependencies are declared in `requirements.txt`:
- `pytest==8.2.0`
- `pytest-asyncio==0.23.7`
- `httpx==0.27.0` (for FastAPI TestClient)

However, **no test files exist in the repository** — the test infrastructure is declared but never implemented.

## Test Types

| Type | Status |
|---|---|
| Unit tests | Absent |
| Integration tests | Absent |
| E2E tests | Absent |
| API contract tests | Absent |

## Coverage

No coverage tooling configured. No `.coveragerc` or coverage configuration found. Effective coverage: **0%**.

## Test Patterns

None established — no test files to derive patterns from.

## How to Run

Tests would be run with:
```bash
cd backend
pytest
```

But there is nothing to run currently.

## Implications

- CI/CD pipeline (`deploy.yml`) deploys without running any tests
- All validation is manual
- The mock infrastructure (`USE_MOCK_AZURE=true`) is designed to support testing but no tests use it
- `httpx` and `pytest-asyncio` suggest intent to write async FastAPI tests via `TestClient`
