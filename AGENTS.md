# Repository Guidelines

## Project Structure & Module Organization
- `PRD.md` contains the current product requirements and scope decisions.
- Source code, tests, and assets are not yet checked in. When adding them, use clear top-level folders such as `frontend/`, `backend/`, `tests/`, and `assets/`.
- Keep documentation in Markdown at the repo root (for example, `README.md`, `AGENTS.md`).

## Build, Test, and Development Commands
- Install dependencies: `pip install -r requirements.txt`
- Run the MVP client/host UI: `python -m frontend.main`

## Current Development Status
### Implemented
- MVP networking: TCP JSON line protocol, host-only controls, manual client connect (IP/port).
- Backend: `GameServer`, `GameRoom`, script loading, role assignment, state broadcast.
- Frontend (PyQt5): host start, client connect, script select, player count (4-6), assign roles, role view.
- Sample script: `data/scripts/sample-script.json`.

### Next Planned
- Add name editing flow for players (client UI + server handling).
- Expand MVP phases beyond reading (investigation/voting/result screens).
- Add basic error handling and reconnect hints.

## Coding Style & Naming Conventions
- Use 2-space indentation for Vue components and 4-space indentation for Python files.
- Favor descriptive, lowercase file names with hyphens (for example, `room-list.vue`, `game-flow.py`).
- Add linting/formatting configs when the codebase appears (for example, ESLint/Prettier for Vue and Ruff/Black for Python) and document how to run them.

## Testing Guidelines
- No test framework is configured yet.
- When tests are added, place them under `tests/` and name files with a `test_` prefix (for example, `tests/test_room_flow.py`).
- Document any minimum coverage or required test suites once established.

## Commit & Pull Request Guidelines
- No commit history or conventions are available in this repository.
- Until a standard is defined, use clear, imperative commit messages (for example, "Add room creation flow").
- Pull requests should describe scope, link any related issues, and include screenshots for UI changes.

## Scope Notes (From PRD)
- The product focuses on a desktop (Windows) experience rather than web deployment.
- No database, voice, or chat modules are required; scripts should be read from files.
- Character selection uses numeric roles; users can rename themselves after assignment.
