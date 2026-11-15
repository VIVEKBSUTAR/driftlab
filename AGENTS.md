# Project working instructions

- Keep `decisions.md` updated alongside changes to architecture, backend logic, frontend behavior, metrics, storage, dependencies, or workflows.
- After completing and verifying requested changes, commit the project changes and push the current branch to the configured GitHub remote. The user explicitly requests local and GitHub copies to stay synchronized. Report any push failure; do not force-push or discard work.
- Keep generated dependencies, build outputs, virtual environments, local databases, credentials, and evaluation run artifacts out of Git. Include source and dependency lockfiles.
- Dashboard metrics must use actual API results. Show failures and synthetic labels clearly; do not silently substitute demo evidence or successful job IDs.
- Run checks relevant to the change: `venv/bin/python -m pytest tests/` for Python behavior and `npm run build --prefix frontend` for frontend changes.
