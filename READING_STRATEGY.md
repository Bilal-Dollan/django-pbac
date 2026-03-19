# Reading Strategy

Follow this order — each layer builds on the previous one.

---

## 1. Understand the Domain (15 min)

Start with the pure-Python core. No Django knowledge needed yet.

1. `src/django_pbac/core/types.py` — learn the 4 enums: `Effect`, `ConflictResolution`, `SubjectType`, `PolicySourceType`
2. `src/django_pbac/core/exceptions.py` — the error hierarchy
3. `src/django_pbac/core/models.py` — **read this carefully**. Every domain object lives here: `Subject`, `Resource`, `Policy`, `PolicyRequest`, `PolicyDecision`, etc.

---

## 2. Understand Evaluation (20 min)

How a decision is made — still pure Python.

4. `src/django_pbac/core/operators.py` — skim the 22 operators, focus on `resolve_attribute()` which resolves paths like `"subject.attributes.department"`
5. `src/django_pbac/core/matchers.py` — short file, read fully: how actions/subjects/resources match policies
6. `src/django_pbac/core/evaluator.py` — **the heart of the system**. Read the `evaluate()` method step-by-step, then `get_permitted_resource_filter()`

---

## 3. Understand Configuration (10 min)

7. `src/django_pbac/conf.py` — all settings with their defaults
8. `rules/settings.md` — the complete settings reference with rules

---

## 4. Understand the Engine (10 min)

9. `src/django_pbac/engine.py` — how everything is wired together. Read `PBACEngine.__init__`, then `evaluate()`, then `_build_engine()`, then understand why `_LazyEngine` exists

---

## 5. Understand Policy Loading (20 min)

Pick the loader type most relevant to you, but read base first.

10. `src/django_pbac/loaders/base.py` — the `PolicyLoader` Protocol
11. `src/django_pbac/loaders/yaml_loader.py` — easiest loader to understand
12. `src/django_pbac/loaders/code.py` — `BaseCodePolicy` class-based API
13. `src/django_pbac/loaders/composite.py` — how all loaders are merged

---

## 6. Understand Django Integration (20 min)

14. `src/django_pbac/integration/middleware.py` — how `request.pbac_subject` and `request.pbac_context` are attached
15. `src/django_pbac/injectors/user.py` — how a Django user becomes a `Subject`
16. `src/django_pbac/integration/decorators.py` — `@require_policy` usage
17. `src/django_pbac/integration/mixins.py` — CBV and queryset filtering

---

## 7. Read a Concrete Example (10 min)

18. `example/policies/documents.yaml` — read the policies first
19. `example/docs_app/views.py` — see how the decorator and mixin map to those policies
20. `example/settings.py` — see how the full PBAC config looks wired together

---

## 8. Read the Tests (ongoing reference)

The tests are the best executable documentation:

- `tests/core/test_evaluator.py` — most important. Shows every edge case of evaluation logic
- `tests/core/test_matchers.py` — shows wildcard/cross-ref matching
- `tests/core/test_operators.py` — shows every operator with examples

---

## 9. Architecture & Decisions (reference)

Read these last, or when something confuses you:

- `context/architecture.md` — the PEP/PDP/PIP diagram and data flow
- `context/decisions.md` — **why** specific choices were made (frozen dataclasses, lazy singleton, DENY by default, etc.)
- `rules/evaluation.md` — all evaluation invariants in one place

---

## Mental Model to Build

After reading, you should be able to answer:

> "A request comes in. What happens?"

```
HttpRequest
  → PBACMiddleware    builds Subject + Context via injectors
  → @require_policy   builds PolicyRequest, calls pbac_engine.evaluate()
  → PBACEngine        checks cache, loads policies, runs PolicyEvaluator
  → PolicyEvaluator   matches action → subject → resource → conditions
  → Conflict resolution → PolicyDecision (PERMIT or DENY)
  → 403 response or view runs
```

---

## Time Estimate

| Phase | Time |
|---|---|
| Steps 1–3 (domain + evaluation + config) | ~45 min |
| Step 4 (engine) | ~10 min |
| Steps 5–6 (loaders + integration) | ~40 min |
| Steps 7–8 (example + tests) | ~20 min |
| Step 9 (architecture reference) | as needed |
| **Total** | **~2 hours** |
