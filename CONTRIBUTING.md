# Contributing

Thanks for contributing to `eval-failure-clusterer`.

## Development setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

## Test

```bash
python -m unittest discover -s tests -v
```

## Scope

- Keep runtime dependencies at zero unless a new dependency is clearly justified.
- Preserve offline-first behavior. Do not add remote API calls for clustering or scoring.
- Prefer deterministic heuristics over opaque magic.
- Add or update tests with every behavior change.

## Pull request checklist

- Added tests for the change.
- Updated README or examples when CLI behavior changed.
- Updated CHANGELOG for user-visible changes.
