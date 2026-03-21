"""Loaders package."""
from django_pbac.loaders.base import PolicyLoader
from django_pbac.loaders.composite import CompositePolicyLoader

__all__ = ["CompositePolicyLoader", "PolicyLoader"]
