"""Shared utilities and abstractions across all services."""

from services.common.errors import (
    SalesIntelligenceError,
    RetriableError,
    NonRetriableError,
)

__all__ = [
    "SalesIntelligenceError",
    "RetriableError",
    "NonRetriableError",
]
