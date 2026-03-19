# Contributing to django-pbac

Thank you for considering contributing to `django-pbac`!

## Development Setup

```bash
git clone https://github.com/django-pbac/django-pbac.git
cd django-pbac
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

## Running Tests

```bash
pytest                          # run all tests
pytest tests/core/              # run core tests only
pytest --cov --cov-report=html  # with HTML coverage report
```

## Code Style

We use `black` for formatting and `ruff` for linting:

```bash
black src tests example
ruff check src tests example
mypy src
```

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Write tests for your changes
4. Ensure all tests pass and coverage stays above 90%
5. Run `pre-commit run --all-files`
6. Submit a pull request

## Reporting Bugs

Open a GitHub issue with:
- Python version
- Django version
- Minimal reproducible example
- Expected vs. actual behavior

## Security Issues

Please **do not** open public issues for security vulnerabilities.
Email security@django-pbac.dev instead.

## Code of Conduct

Be respectful and constructive. We follow the
[Contributor Covenant](https://www.contributor-covenant.org/).
