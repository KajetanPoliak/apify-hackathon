"""Tests for LLM service functions with mock data."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Any

from src.llm_service import (
    convert_scraped_data_to_listing_input,
    check_consistency_with_structured_output,
    extract_number_from_text,
    extract_float_from_text,
)
from src.models import ListingInput, ConsistencyCheckResult
from src.mock_data import (
    generate_mock_scraped_property_data,
    generate_mock_listing_input,
)


class TestExtractHelpers:
    """Test helper functions for text extraction."""
    
    def test_extract_number_from_text(self):
        """Test extracting numbers from text."""
        assert extract_number_from_text("57 m²") == 57
        assert extract_number_from_text("3+kk") == 3
        assert extract_number_from_text("Price: 8 499 000 Kč") == 8
        assert extract_number_from_text("No numbers here") is None
        assert extract_number_from_text(None) is None
        assert extract_number_from_text("") is None
    
    def test_extract_float_from_text(self):
        """Test extracting float numbers from text."""
        assert extract_float_from_text("57.5 m²") == 57.5
        assert extract_float_from_text("3.5 bathrooms") == 3.5
        assert extract_float_from_text("Price: 8.5 million") == 8.5
        assert extract_float_from_text("No numbers") is None
        assert extract_float_from_text(None) is None


class TestConvertScrapedDataToListingInput:
    """Test conversion of scraped data to ListingInput."""
    
    @pytest.mark.asyncio
    async def test_convert_with_mock_llm_success(self, mock_scraped_property_data):
        """Test successful conversion with mocked LLM response."""
        # Create expected ListingInput from mock data
        expected_listing = generate_mock_listing_input()
        
        # Mock LLM response with structured output
        mock_llm_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": expected_listing.model_dump_json(),
                    }
                }
            ]
        }
        
        with patch("src.llm_service.call_openrouter_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response
            
            result = await convert_scraped_data_to_listing_input(
                property_data=mock_scraped_property_data,
                model="test-model",
                temperature=0.7,
            )
            
            assert result is not None
            assert isinstance(result, ListingInput)
            assert result.listing_id == expected_listing.listing_id
            assert result.bedrooms == expected_listing.bedrooms
            assert result.city == "Praha"
            assert result.list_price > 0
    
    @pytest.mark.asyncio
    async def test_convert_with_mock_llm_failure(self, mock_scraped_property_data):
        """Test conversion failure when LLM returns None."""
        with patch("src.llm_service.call_openrouter_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = None
            
            result = await convert_scraped_data_to_listing_input(
                property_data=mock_scraped_property_data,
                model="test-model",
                temperature=0.7,
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_convert_with_invalid_json(self, mock_scraped_property_data):
        """Test conversion when LLM returns invalid JSON."""
        mock_llm_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "This is not valid JSON",
                    }
                }
            ]
        }
        
        with patch("src.llm_service.call_openrouter_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response
            
            result = await convert_scraped_data_to_listing_input(
                property_data=mock_scraped_property_data,
                model="test-model",
                temperature=0.7,
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_convert_with_empty_response(self, mock_scraped_property_data):
        """Test conversion when LLM returns empty response."""
        mock_llm_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                    }
                }
            ]
        }
        
        with patch("src.llm_service.call_openrouter_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response
            
            result = await convert_scraped_data_to_listing_input(
                property_data=mock_scraped_property_data,
                model="test-model",
                temperature=0.7,
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_convert_with_tool_calls_response(self, mock_scraped_property_data):
        """Test conversion when LLM returns structured output in tool_calls."""
        expected_listing = generate_mock_listing_input()
        
        mock_llm_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "listing_input",
                                    "arguments": expected_listing.model_dump_json(),
                                }
                            }
                        ],
                    }
                }
            ]
        }
        
        with patch("src.llm_service.call_openrouter_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response
            
            result = await convert_scraped_data_to_listing_input(
                property_data=mock_scraped_property_data,
                model="test-model",
                temperature=0.7,
            )
            
            assert result is not None
            assert isinstance(result, ListingInput)


class TestCheckConsistencyWithStructuredOutput:
    """Test consistency checking with structured outputs."""
    
    @pytest.mark.asyncio
    async def test_check_consistency_success(self, mock_listing_input):
        """Test successful consistency check with mocked LLM response."""
        # Create expected ConsistencyCheckResult
        expected_result = ConsistencyCheckResult(
            listing_id=mock_listing_input.listing_id,
            property_address=mock_listing_input.property_address,
            total_inconsistencies=2,
            is_consistent=False,
            findings=[],
            summary="Found 2 inconsistencies in the listing",
        )
        
        # Mock LLM response
        mock_llm_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": expected_result.model_dump_json(),
                    }
                }
            ]
        }
        
        with patch("src.llm_service.call_openrouter_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response
            
            result = await check_consistency_with_structured_output(
                listing_input=mock_listing_input,
                model="test-model",
                temperature=0.7,
            )
            
            assert result is not None
            assert isinstance(result, ConsistencyCheckResult)
            assert result.listing_id == mock_listing_input.listing_id
            assert result.property_address == mock_listing_input.property_address
            assert result.total_inconsistencies == 2
            assert result.is_consistent is False
    
    @pytest.mark.asyncio
    async def test_check_consistency_no_inconsistencies(self, mock_listing_input):
        """Test consistency check when no inconsistencies are found."""
        expected_result = ConsistencyCheckResult(
            listing_id=mock_listing_input.listing_id,
            property_address=mock_listing_input.property_address,
            total_inconsistencies=0,
            is_consistent=True,
            findings=[],
            summary="No inconsistencies found",
        )
        
        mock_llm_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": expected_result.model_dump_json(),
                    }
                }
            ]
        }
        
        with patch("src.llm_service.call_openrouter_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response
            
            result = await check_consistency_with_structured_output(
                listing_input=mock_listing_input,
                model="test-model",
                temperature=0.7,
            )
            
            assert result is not None
            assert result.is_consistent is True
            assert result.total_inconsistencies == 0
    
    @pytest.mark.asyncio
    async def test_check_consistency_llm_failure(self, mock_listing_input):
        """Test consistency check when LLM returns None."""
        with patch("src.llm_service.call_openrouter_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = None
            
            result = await check_consistency_with_structured_output(
                listing_input=mock_listing_input,
                model="test-model",
                temperature=0.7,
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_check_consistency_invalid_json(self, mock_listing_input):
        """Test consistency check when LLM returns invalid JSON."""
        mock_llm_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Invalid JSON response",
                    }
                }
            ]
        }
        
        with patch("src.llm_service.call_openrouter_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response
            
            result = await check_consistency_with_structured_output(
                listing_input=mock_listing_input,
                model="test-model",
                temperature=0.7,
            )
            
            assert result is None


class TestIntegrationWithMockData:
    """Integration tests using mock data generators."""
    
    def test_mock_scraped_data_structure(self):
        """Test that mock scraped data has the expected structure."""
        data = generate_mock_scraped_property_data()
        
        assert "url" in data
        assert "title" in data
        assert "description" in data
        assert "price" in data
        assert "location" in data
        assert isinstance(data["location"], dict)
        assert "propertyDetails" in data
        assert isinstance(data["propertyDetails"], dict)
        assert "attributes" in data
        assert isinstance(data["attributes"], dict)
    
    def test_mock_listing_input_valid(self):
        """Test that mock ListingInput is valid."""
        listing = generate_mock_listing_input()
        
        assert isinstance(listing, ListingInput)
        assert listing.listing_id.startswith("PRG-")
        assert listing.bedrooms >= 0
        assert listing.bathrooms >= 0
        assert listing.list_price > 0
        assert len(listing.description) >= 10
        assert listing.city == "Praha"
        assert listing.state == "Czech Republic"
    
    @pytest.mark.asyncio
    async def test_full_workflow_with_mocks(self):
        """Test the full workflow: scraped data -> ListingInput -> ConsistencyCheck."""
        # Step 1: Generate mock scraped data
        scraped_data = generate_mock_scraped_property_data()
        
        # Step 2: Mock conversion to ListingInput
        expected_listing = generate_mock_listing_input()
        mock_convert_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": expected_listing.model_dump_json(),
                    }
                }
            ]
        }
        
        # Step 3: Mock consistency check
        expected_consistency = ConsistencyCheckResult(
            listing_id=expected_listing.listing_id,
            property_address=expected_listing.property_address,
            total_inconsistencies=1,
            is_consistent=False,
            findings=[],
            summary="Found 1 inconsistency",
        )
        mock_consistency_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": expected_consistency.model_dump_json(),
                    }
                }
            ]
        }
        
        with patch("src.llm_service.call_openrouter_llm", new_callable=AsyncMock) as mock_llm:
            # First call for conversion
            mock_llm.return_value = mock_convert_response
            listing_result = await convert_scraped_data_to_listing_input(
                property_data=scraped_data,
                model="test-model",
                temperature=0.7,
            )
            
            assert listing_result is not None
            assert isinstance(listing_result, ListingInput)
            
            # Second call for consistency check
            mock_llm.return_value = mock_consistency_response
            consistency_result = await check_consistency_with_structured_output(
                listing_input=listing_result,
                model="test-model",
                temperature=0.7,
            )
            
            assert consistency_result is not None
            assert isinstance(consistency_result, ConsistencyCheckResult)
            assert consistency_result.listing_id == listing_result.listing_id
