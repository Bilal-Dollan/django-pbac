# Testing Rules

Rules governing the test suite organization and requirements.

---

## RULE-TEST-001: Core tests require no Django DB

Tests under `tests/core/` test pure Python code.
They must not use `@pytest.mark.django_db` or require Django models.

```python
# Good — pure unit test
def test_eq_operator():
    op = operator_registry.get("eq")
    assert op("hello", "hello") is True
```

---

## RULE-TEST-002: Use conftest fixtures for domain objects

Always use the shared fixtures from `tests/conftest.py` rather than
constructing `Subject`, `Resource`, `Policy` inline in every test.

```python
# Good
def test_permit(evaluator, subject_alice, resource_doc, permit_policy_any_doc_read):
    ...

# Avoid (unless testing specific attribute combinations)
def test_permit():
    subject = Subject(id="user:alice", type=SubjectType.USER, ...)
    ...
```

---

## RULE-TEST-003: Use factories for complex one-off objects

For tests that need objects with specific attributes not covered by standard fixtures,
use the builder functions in `tests/fixtures/factories.py`:

```python
from tests.fixtures.factories import make_subject, make_policy, make_request

def test_custom():
    subject = make_subject(id="user:custom", roles=frozenset({"superuser"}))
    ...
```

---

## RULE-TEST-004: YAML loader tests use tmp_path

Tests for `YAMLPolicyLoader` must use pytest's `tmp_path` fixture to create
temporary YAML files rather than reading from the `tests/fixtures/` folder.

---

## RULE-TEST-005: Mock pbac_engine in integration tests

Tests for middleware, decorators, and DRF permissions should mock `pbac_engine`
to avoid requiring full engine initialization:

```python
with patch("django_pbac.integration.middleware.pbac_engine", mock_engine):
    middleware = PBACMiddleware(get_response)
    middleware(request)
```

---

## RULE-TEST-006: DB tests require @pytest.mark.django_db

Any test that uses Django ORM models (PolicyModel, AuditLogModel, etc.)
MUST be marked with `@pytest.mark.django_db`.

---

## RULE-TEST-007: Test class naming

- Test classes: `TestMyFeature` (no `Test` suffix on filename, only class)
- Test methods: `test_description_of_what_is_tested`
- Fixture factories: bare functions (not classes) named `make_xxx`

---

## RULE-TEST-008: Coverage requirements

Minimum coverage targets:
- `core/` — 90%+
- `loaders/` — 80%+
- `integration/` — 70%+
- Overall — 80%+

Run with: `pytest --cov=src/django_pbac --cov-report=term-missing`

---

## Running Tests

```bash
# All tests
pytest tests/

# Core only (fast, no Django DB)
pytest tests/core/

# With coverage
pytest tests/ --cov=src/django_pbac --cov-report=html

# Single test
pytest tests/core/test_evaluator.py::TestDenyOverride::test_bob_denied_by_clearance -v
```
