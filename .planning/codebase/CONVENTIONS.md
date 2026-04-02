# Code Conventions

## Style & Formatting

**Backend (Python):**
- No linter config file found (no `.flake8`, `ruff.toml`, or `pyproject.toml`)
- PEP 8 style followed informally
- Type hints used consistently on function signatures
- Docstrings in module header (triple-quoted), minimal inline comments
- Portuguese used for user-facing strings, English for code identifiers

**Frontend (TypeScript/React):**
- ESLint with `eslint-config-next`
- Prettier not configured (no `.prettierrc`)
- Tailwind CSS for all styling — no CSS modules, no styled-components

## Naming Conventions

**Backend:**
- Files: `snake_case.py`
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Pydantic models: `PascalCase` (e.g. `UploadResponse`, `StructuredResult`)
- Constants: `UPPER_SNAKE_CASE`
- Private helpers: `_leading_underscore` (e.g. `_use_mock`, `_build_entities_from_structured`)

**Frontend:**
- Files: `PascalCase.tsx` for components, `camelCase.ts` for utils
- Components: `PascalCase` function components
- Pages: `page.tsx` in App Router convention
- CSS classes: Tailwind utility classes inline

## Patterns & Idioms

- **Mock toggle pattern:** `os.getenv("USE_MOCK_AZURE", "true").lower() == "true"` — copy-pasted across ~8 service files to switch between real Azure and in-memory mocks
- **Router pattern:** Each API domain is a separate `APIRouter` imported into `main.py`
- **Service layer:** API handlers call service functions; services call Azure wrappers
- **Pydantic models:** Used for all request/response validation; `StructuredResult` wraps all pipeline output
- **Dataclasses:** Used for internal pipeline types (`PipelineResult`, `CleanResult`)
- **Dependency injection:** FastAPI `Depends(get_current_user)` for auth on all protected routes

## Error Handling

- API layer raises `HTTPException` with appropriate status codes
- Service layer raises bare exceptions that propagate to API handlers
- Some services silently swallow exceptions (RAG indexing, StructuredResult parsing) — inconsistent
- No global exception handler registered in `main.py`
- Frontend: `try/catch` around fetch calls, errors shown as user-visible strings

## Documentation

- Module-level docstrings in most backend files describing the file's purpose and flow
- Inline comments sparse but present for non-obvious logic
- README exists (not read for this mapping)
- No JSDoc on frontend functions
- API self-documented via FastAPI's OpenAPI at `/docs`
