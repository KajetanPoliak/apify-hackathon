"""Pytest configuration and fixtures."""

import pytest
from typing import Any

from src.mock_data import (
    generate_mock_scraped_property_data,
    generate_mock_listing_input,
    generate_mock_listing_inputs,
)


@pytest.fixture
def mock_scraped_property_data() -> dict[str, Any]:
    """Fixture providing mock scraped property data."""
    return generate_mock_scraped_property_data()


@pytest.fixture
def mock_listing_input():
    """Fixture providing a mock ListingInput object."""
    return generate_mock_listing_input()


@pytest.fixture
def mock_listing_inputs() -> list:
    """Fixture providing multiple mock ListingInput objects."""
    return generate_mock_listing_inputs()
