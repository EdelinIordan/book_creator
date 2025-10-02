"""Tests for the mock provider and factory."""

import asyncio
from uuid import uuid4

from book_creator_providers import (
    MockProvider,
    ProviderFactory,
    ProviderRequest,
    ProviderSettings,
    ProviderConfig,
)


async def run_generate(provider):
    request = ProviderRequest(prompt="Summarise the project")
    response = await provider.generate(request)
    assert "Mock response" in response.text
    assert response.prompt_tokens > 0


def test_mock_generate_sync() -> None:
    provider = MockProvider()
    request = ProviderRequest(prompt="Hello world")
    response = asyncio.run(provider.generate(request))
    assert response.model == "mock"


def test_factory_creates_mock_when_config_provided() -> None:
    config = ProviderConfig(
        name="mock",
        api_key="mock",
        model="mock",
        settings=ProviderSettings(),
    )
    provider = ProviderFactory.create(config)
    assert isinstance(provider, MockProvider)


def test_mock_json_mode() -> None:
    provider = MockProvider()
    request = ProviderRequest(prompt="List facts", json_schema={"type": "object"})
    response = asyncio.run(provider.generate(request))
    assert response.text.startswith("{")
