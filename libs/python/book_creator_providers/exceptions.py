"""Custom exceptions used by provider adapters."""

from __future__ import annotations


class ProviderError(RuntimeError):
    """Base error raised for provider failures."""


class ProviderConfigError(ProviderError):
    """Raised when configuration is missing or invalid."""


class ProviderResponseError(ProviderError):
    """Raised when a provider returns an unusable response."""

