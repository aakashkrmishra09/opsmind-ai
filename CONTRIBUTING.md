# Contributing to OpsMind AI

## Branching & Commits
- Create feature or milestone branches from `main` (for example, `feat/m2-auth-schema`).
- Keep commits focused on a single logical change.
- Use Conventional Commits where practical (`feat:`, `fix:`, `chore:`, `docs:`, `test:`).

## Code Quality Rules
- Never commit `.env` files, API keys, tokens, or credentials.
- Keep business logic separated from HTTP route handlers and UI components.
- Add or update automated tests alongside behavior changes.
- Verify `git status` and run linters/tests before opening a pull request.