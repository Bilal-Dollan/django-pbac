"""Adapters package."""
from django_pbac.adapters.base import ModelAdapter
from django_pbac.adapters.registry import adapter_registry

__all__ = ["ModelAdapter", "adapter_registry"]
