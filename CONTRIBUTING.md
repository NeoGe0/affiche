# Contributing to Affiche

Thanks for wanting to help. Bug reports are the most useful thing right now, while the beta is on —
but patches are welcome too.

## Reporting bugs

Use the [bug report template](../../issues/new?template=bug_report.yml). The version, the media
server, and the logs are what make a report actionable — please fill them in.

Security problems go through [SECURITY.md](SECURITY.md), **not** the issue tracker.

## Before you write code

- **Open an issue first** for anything beyond a small fix. It avoids you building something that
  conflicts with work already planned.
- **Land your change in the right layer.** The backend goes router → service → repository →
  connector → entity, and the frontend goes pages → components → `api`/hooks/types, with pages as
  the composition root. A PR that lands in the wrong layer is the most common reason for a long
  review, so follow the shape of the code already around it.
- **Frontend specifics:** the React Compiler is on, so don't hand-write `useMemo`/`useCallback`;
  styles are CSS Modules; lint must be at zero.

## Development setup

See [Development](README.md#development) in the README.

## Before opening a PR

Everything must be green — CI runs exactly these:

```bash
cd affiche-backend  && python -m pytest -q                   # venv activated
cd affiche-frontend && npm run test
cd affiche-frontend && npx tsc --noEmit -p tsconfig.app.json
cd affiche-frontend && npm run lint
```

Also:

- **Add tests** for what you changed. Backend route tests use `TestClient` with the
  `authenticated_app` fixture; frontend tests use Vitest with `globals: false` (explicit imports)
  and never assert on CSS class names.
- **A schema change needs an Alembic migration** (`affiche-backend/affiche/alembic/versions/`). The
  app runs `alembic upgrade head` on startup, so a missing migration breaks everyone's upgrade.
- One logical change per PR, and say *why* in the description, not just *what*.

## Commit and PR style

No enforced convention — a clear imperative subject line ("Add season poster reset") is enough.
Explain the reasoning in the body when the change isn't obvious.

## License

Affiche is licensed under **AGPL-3.0**. By contributing, you agree that your contribution is
licensed under the same terms.
