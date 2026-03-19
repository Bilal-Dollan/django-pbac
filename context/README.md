# django-pbac — Implementation Context

This folder documents the complete implementation context for the django-pbac project.
It serves as the authoritative reference for architecture decisions, module inventory,
conventions, and progress tracking.

## Contents

| File | Description |
|---|---|
| [architecture.md](architecture.md) | System architecture and design decisions |
| [modules.md](modules.md) | Complete module inventory with status |
| [conventions.md](conventions.md) | Code conventions and patterns used |
| [progress.md](progress.md) | Implementation progress log |
| [decisions.md](decisions.md) | Architecture Decision Records (ADRs) |

## Quick Navigation

- **Core engine**: `src/django_pbac/core/` — pure Python, no Django deps
- **Policy loading**: `src/django_pbac/loaders/`
- **Context injection**: `src/django_pbac/injectors/`
- **Django integration**: `src/django_pbac/integration/`
- **Main entry point**: `src/django_pbac/engine.py` → `pbac_engine` singleton
- **DB models**: `src/django_pbac/db/models.py`
- **Settings**: `src/django_pbac/conf.py` → `pbac_settings`
