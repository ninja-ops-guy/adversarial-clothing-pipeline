# Contributing

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
pytest
ruff check .
python -m examples.smoke_test
```

## Pull-request requirements

1. Add or update tests for behavior changes.
2. Keep production paths deterministic under a fixed seed.
3. Do not add silent mock/model fallbacks. Optional backends must fail clearly when unavailable.
4. Do not hard-code efficacy or transfer-rate claims. Benchmark output must come from supplied evaluators.
5. Keep vendor integrations out of the core package unless they target an owned/authorized lab system and are isolated behind an adapter.
6. Do not commit weights, datasets, API keys, tokens, camera URLs, or participant data.
7. Update `PRODUCTION_READINESS.md` when a release gate changes.

## Commit style

Prefer concise imperative messages, for example:

- `fix: enforce black-box query budget`
- `test: add held-out transform benchmark coverage`
- `docs: document physical validation gate`
