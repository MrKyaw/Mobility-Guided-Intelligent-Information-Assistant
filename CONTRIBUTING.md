# Contributing

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
pytest --cov=mobility_guidance --cov-branch --cov-report=term-missing
```

## Quality bar

- Python 3.10–3.12 pass.
- 100% line and branch coverage for `mobility_guidance`.
- No new runtime dependencies in the core.
- No secrets in tracked files.
- Behaviour changes need tests and README updates.

## Pull requests

1. Branch from `main`.
2. Keep commits focused; explain the *why*.
3. Run `make check`.
4. Describe the change, tests, and trade-offs.

## Security

Do not open a public issue for credential leaks. Rotate the credential first, then contact the maintainer at kyaw.tech@gmail.com.
