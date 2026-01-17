"""Tests for LLM service functions with mock data."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Any

from src.llm_service import (
    convert_scraped_data_to_listing_input,
    check_consistency_with_structured_output,
    extract_number_from_text,
    extract_float_from_text,
    sanitize_json_schema_for_llm,
)
from src.models import ListingInput, ConsistencyCheckResult
from src.mock_data import (
    generate_mock_scraped_property_data,
    generate_mock_listing_input,
)


class TestSanitizeJsonSchema:
    """Test JSON schema sanitization for LLM compatibility."""
    
    def test_sanitize_removes_uri_format(self):
        """Test that uri format is removed from schema."""
        schema = {
            "type": "string",
            "format": "uri",
        }
        sanitized = sanitize_json_schema_for_llm(schema)
        assert "format" not in sanitized
        assert sanitized["type"] == "string"
    
    def test_sanitize_handles_anyof_with_uri(self):
        """Test that uri format is removed from anyOf structures."""
        schema = {
            "anyOf": [
                {
                    "type": "string",
                    "format": "uri",
                },
                {
                    "type": "null",
                },
            ],
        }
        sanitized = sanitize_json_schema_for_llm(schema)
        assert "anyOf" in sanitized
        assert len(sanitized["anyOf"]) == 2
        # First option should have format removed
        assert "format" not in sanitized["anyOf"][0]
        assert sanitized["anyOf"][0]["type"] == "string"
        # Second option should remain unchanged
        assert sanitized["anyOf"][1]["type"] == "null"
    
    def test_sanitize_preserves_other_formats(self):
        """Test that other formats like date-time are preserved."""
        schema = {
            "type": "string",
            "format": "date-time",
        }
        sanitized = sanitize_json_schema_for_llm(schema)
        # date-time format should be preserved (only uri is problematic)
        assert sanitized["format"] == "date-time"
    
    def test_sanitize_handles_nested_structures(self):
        """Test that nested properties are sanitized."""
        schema = {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "format": "uri",
                },
                "name": {
                    "type": "string",
                },
            },
        }
        sanitized = sanitize_json_schema_for_llm(schema)
        assert "format" not in sanitized["properties"]["url"]
        assert sanitized["properties"]["url"]["type"] == "string"
        assert sanitized["properties"]["name"]["type"] == "string"
    
    def test_sanitize_listing_input_schema(self):
        """Test sanitization of actual ListingInput schema."""
        from src.models import ListingInput
        
        schema = ListingInput.model_json_schema()
        sanitized = sanitize_json_schema_for_llm(schema)
        
        # Check that listing_url doesn't have uri format
        listing_url_schema = sanitized["properties"]["listing_url"]
        if "anyOf" in listing_url_schema:
            for option in listing_url_schema["anyOf"]:
                if option.get("type") == "string":
                    assert "format" != "uri" or "format" not in option
    
    def test_sanitize_adds_all_properties_to_required(self):
        """Test that all properties are added to required array (Azure requirement)."""
        schema = {
            "type": "object",
            "properties": {
                "required_field": {"type": "string"},
                "optional_field": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"},
                    ],
                },
            },
            "required": ["required_field"],
        }
        sanitized = sanitize_json_schema_for_llm(schema)
        
        # All properties should be in required array
        assert "required" in sanitized
        assert "required_field" in sanitized["required"]
        assert "optional_field" in sanitized["required"]
        assert len(sanitized["required"]) == 2
        
        # Optional field should still allow null
        optional_schema = sanitized["properties"]["optional_field"]
        assert "anyOf" in optional_schema
        null_allowed = any(item.get("type") == "null" for item in optional_schema["anyOf"])
        assert null_allowed, "Optional field should still allow null values"
    
    def test_sanitize_sets_additional_properties_false(self):
        """Test that additionalProperties is set to false (Azure requirement)."""
        schema = {
            "type": "object",
            "properties": {
                "field1": {"type": "string"},
            },
        }
        sanitized = sanitize_json_schema_for_llm(schema)
        
        # additionalProperties should be explicitly set to false
        assert "additionalProperties" in sanitized
        assert sanitized["additionalProperties"] is False
    
    def test_sanitize_additional_properties_for_actual_schemas(self):
        """Test that actual model schemas have additionalProperties set."""
        from src.models import ListingInput, ConsistencyCheckResult
        
        listing_schema = ListingInput.model_json_schema()
        consistency_schema = ConsistencyCheckResult.model_json_schema()
        
        sanitized_listing = sanitize_json_schema_for_llm(listing_schema)
        sanitized_consistency = sanitize_json_schema_for_llm(consistency_schema)
        
        # Both should have additionalProperties: false
        assert sanitized_listing.get("additionalProperties") is False
        assert sanitized_consistency.get("additionalProperties") is False


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
    
    @pytest.mark.asyncio
    async def test_convert_fixes_invalid_price(self, mock_scraped_property_data):
        """Test that invalid prices (0.0 or negative) are fixed automatically."""
        # Create a listing with invalid price
        invalid_listing_data = generate_mock_listing_input().model_dump(mode='json')
        invalid_listing_data['list_price'] = 0.0  # Invalid price
        
        mock_llm_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(invalid_listing_data),
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
            
            # Should still succeed because validation fixes the price
            assert result is not None
            assert isinstance(result, ListingInput)
            assert result.list_price > 0, "Price should be fixed to be greater than 0"
    
    @pytest.mark.asyncio
    async def test_convert_fixes_short_description(self, mock_scraped_property_data):
        """Test that descriptions shorter than 10 characters are fixed."""
        invalid_listing_data = generate_mock_listing_input().model_dump(mode='json')
        invalid_listing_data['description'] = "Short"  # Too short
        
        mock_llm_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(invalid_listing_data),
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
            
            # Should still succeed because validation fixes the description
            assert result is not None
            assert isinstance(result, ListingInput)
            assert len(result.description) >= 10, "Description should be fixed to be at least 10 characters"


class TestCheckConsistencyWithStructuredOutput:
    """Test consistency checking with structured outputs."""
    
    @pytest.mark.asyncio
    async def test_check_consistency_success(self, mock_listing_input):
        """Test successful consistency check with mocked LLM response."""
        from src.models import InconsistencyFinding, SeverityLevel
        
        # Create expected ConsistencyCheckResult with actual findings
        findings = [
            InconsistencyFinding(
                field_name="bedrooms",
                description_says="3 bedrooms",
                listing_data_says="4 bedrooms",
                severity=SeverityLevel.MEDIUM,
                explanation="Description says 3 but data shows 4",
            ),
            InconsistencyFinding(
                field_name="square_meters",
                description_says="60 m²",
                listing_data_says="57 m²",
                severity=SeverityLevel.LOW,
                explanation="Small area discrepancy",
            ),
        ]
        
        expected_result = ConsistencyCheckResult(
            listing_id=mock_listing_input.listing_id,
            property_address=mock_listing_input.property_address,
            total_inconsistencies=2,
            is_consistent=False,
            findings=findings,
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
