# Evaluation Rules

Rules and invariants governing policy evaluation.

---

## RULE-EVAL-001: No policies → DENY

When no policies match a request, the result is always `Effect.DENY`.
This is the "closed world assumption" (secure by default).

```python
decision = pbac_engine.evaluate(request)
# If loader returns [], decision.effect == Effect.DENY always
```

---

## RULE-EVAL-002: action format is `namespace:verb`

All actions MUST contain a `:` separator. The left side is the namespace,
the right side is the verb.

```python
# Valid
"documents:read"
"reports:write"
"admin:delete_user"

# Invalid — will raise ValueError at PolicyRequest construction
"read"
"documents"
```

---

## RULE-EVAL-003: Condition attribute roots are restricted

`Condition.attribute` MUST start with one of: `subject.`, `resource.`, `context.`

```python
# Valid
Condition(attribute="subject.attributes.role", operator="eq", value="admin")
Condition(attribute="resource.type", operator="eq", value="document")
Condition(attribute="context.environment.ip", operator="eq", value="127.0.0.1")

# Invalid — will raise ValueError
Condition(attribute="user.name", operator="eq", value="alice")
```

---

## RULE-EVAL-004: SubjectMatcher — ANY must match

If a Policy has multiple `subject_matchers`, only ONE needs to match.
(OR semantics for matchers, AND semantics for conditions within a matcher)

---

## RULE-EVAL-005: ResourceMatcher — ANY must match

Same as RULE-EVAL-004. Multiple resource_matchers are OR'd.

---

## RULE-EVAL-006: Conditions — ALL must pass

All `Condition` objects within a Policy must evaluate to True.
(AND semantics for conditions)

---

## RULE-EVAL-007: DENY_OVERRIDE — DENY beats everything

Under `ConflictResolution.DENY_OVERRIDE`:
- If any matching policy has `Effect.DENY` → final result is DENY
- Else if any matching policy has `Effect.PERMIT` → final result is PERMIT
- Else → DENY (from RULE-EVAL-001)

---

## RULE-EVAL-008: PERMIT_OVERRIDE — PERMIT beats DENY

Under `ConflictResolution.PERMIT_OVERRIDE`:
- If any matching policy has `Effect.PERMIT` → final result is PERMIT
- Else if any matching policy has `Effect.DENY` → final result is DENY
- Else → DENY (from RULE-EVAL-001)

---

## RULE-EVAL-009: FIRST_APPLICABLE — priority wins

Under `ConflictResolution.FIRST_APPLICABLE`:
- Policies are sorted by `priority` descending (higher = evaluated first)
- The first matching policy's effect is returned

---

## RULE-EVAL-010: Cross-reference with `{"ref": "path"}`

Matcher attribute values may be cross-references:
```yaml
attributes:
  owner:
    ref: "subject.id"
```
This resolves `subject.id` from the current PolicyRequest at evaluation time.
Cross-references are only followed one level (no nested refs).

---

## RULE-EVAL-011: ResourceFilter v1 operator support

`get_permitted_resource_filter()` only generates ORM Q() objects for:
- `eq` operator → `Q(field=value)`
- `in` operator → `Q(field__in=values)`

Any other operator causes `permit_all=True` fallback with a warning log.

---

## RULE-EVAL-012: Wildcard actions

Policy `actions` support:
- `*` — matches any action
- `ns:*` — matches any action in namespace `ns`
- `ns:verb` — exact match only

No partial wildcards like `doc*:read` are supported in v1.
