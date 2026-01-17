"""Tests for mock data generation functions."""

import pytest
from datetime import date

from src.mock_data import (
    generate_mock_scraped_property_data,
    generate_mock_listing_input,
    generate_mock_listing_inputs,
    generate_mock_inconsistency_results,
    generate_mock_result_for_property,
)
from src.models import ListingInput, ConsistencyCheckResult


class TestMockScrapedPropertyData:
    """Test mock scraped property data generation."""
    
    def test_generate_mock_scraped_property_data_default(self):
        """Test generating mock scraped data with default values."""
        data = generate_mock_scraped_property_data()
        
        assert isinstance(data, dict)
        assert "url" in data
        assert "propertyId" in data
        assert "title" in data
        assert "description" in data
        assert "price" in data
        assert "location" in data
        assert "propertyDetails" in data
        assert "attributes" in data
        assert "amenities" in data
    
    def test_generate_mock_scraped_property_data_custom_url(self):
        """Test generating mock scraped data with custom URL."""
        custom_url = "https://www.bezrealitky.cz/test/123"
        data = generate_mock_scraped_property_data(url=custom_url)
        
        assert data["url"] == custom_url
        assert data["scrapedAt"] == custom_url
    
    def test_mock_scraped_data_location_structure(self):
        """Test that location has the correct structure."""
        data = generate_mock_scraped_property_data()
        
        location = data["location"]
        assert isinstance(location, dict)
        assert "full" in location
        assert "city" in location
        assert "district" in location
        assert "street" in location
        assert location["city"] == "Praha"
    
    def test_mock_scraped_data_property_details(self):
        """Test that property details have expected fields."""
        data = generate_mock_scraped_property_data()
        
        details = data["propertyDetails"]
        assert "area" in details
        assert "disposition" in details
        assert "floor" in details
        assert "buildingType" in details
        assert "condition" in details


class TestMockListingInput:
    """Test mock ListingInput generation."""
    
    def test_generate_mock_listing_input_default(self):
        """Test generating mock ListingInput with default values."""
        listing = generate_mock_listing_input()
        
        assert isinstance(listing, ListingInput)
        assert listing.listing_id.startswith("PRG-")
        assert listing.bedrooms >= 0
        assert listing.bathrooms >= 0
        assert listing.list_price > 0
        assert len(listing.description) >= 10
        assert listing.city == "Praha"
        assert listing.state == "Czech Republic"
        assert listing.zip_code is not None
    
    def test_generate_mock_listing_input_custom(self):
        """Test generating mock ListingInput with custom values."""
        custom_id = "CUSTOM-123"
        custom_url = "https://example.com/listing/123"
        
        listing = generate_mock_listing_input(
            listing_id=custom_id,
            url=custom_url,
        )
        
        assert listing.listing_id == custom_id
        assert str(listing.listing_url) == custom_url
    
    def test_mock_listing_input_required_fields(self):
        """Test that all required fields are present."""
        listing = generate_mock_listing_input()
        
        # Required fields
        assert listing.listing_id is not None
        assert listing.property_address is not None
        assert listing.city is not None
        assert listing.state is not None
        assert listing.zip_code is not None
        assert listing.bedrooms is not None
        assert listing.bathrooms is not None
        assert listing.list_price is not None
        assert listing.description is not None
    
    def test_mock_listing_input_optional_fields(self):
        """Test that optional fields can be None."""
        listing = generate_mock_listing_input()
        
        # Optional fields can be None
        assert listing.lot_size_sqft is None or listing.lot_size_sqft >= 0
        assert listing.year_built is None or (1800 <= listing.year_built <= 2030)
        assert listing.property_type is None or isinstance(listing.property_type, str)
        assert listing.stories is None or listing.stories >= 1
        assert listing.garage_spaces is None or listing.garage_spaces >= 0
    
    def test_generate_mock_listing_inputs(self):
        """Test generating multiple mock ListingInput objects."""
        listings = generate_mock_listing_inputs()
        
        assert isinstance(listings, list)
        assert len(listings) >= 1
        
        for listing in listings:
            assert isinstance(listing, ListingInput)
            assert listing.listing_id.startswith("PRG-")
            assert listing.bedrooms >= 0
            assert listing.list_price > 0


class TestMockConsistencyResults:
    """Test mock consistency result generation."""
    
    def test_generate_mock_inconsistency_results(self):
        """Test generating mock inconsistency results."""
        results = generate_mock_inconsistency_results()
        
        assert isinstance(results, list)
        assert len(results) > 0
        
        for result in results:
            assert isinstance(result, ConsistencyCheckResult)
            assert result.listing_id is not None
            assert result.property_address is not None
            assert result.total_inconsistencies >= 0
            assert isinstance(result.is_consistent, bool)
            assert isinstance(result.findings, list)
            assert result.summary is not None
    
    def test_generate_mock_result_for_property(self):
        """Test generating mock result for a specific property."""
        url = "https://example.com/property/123"
        address = "Test Street 123"
        title = "Test Property"
        description = "This is a test property description"
        price = "1 000 000 Kč"
        
        result = generate_mock_result_for_property(
            url=url,
            property_address=address,
            title=title,
            description=description,
            price=price,
            reason="Test reason",
        )
        
        assert isinstance(result, ConsistencyCheckResult)
        assert result.listing_id.startswith("PRG-")
        assert result.property_address == address
        assert result.total_inconsistencies == 2
        assert result.is_consistent is False
        assert len(result.findings) == 2
        assert "Test reason" in result.summary
    
    def test_mock_result_for_property_defaults(self):
        """Test generating mock result with minimal parameters."""
        url = "https://example.com/property/456"
        
        result = generate_mock_result_for_property(url=url)
        
        assert isinstance(result, ConsistencyCheckResult)
        assert result.property_address == url  # Falls back to URL
        assert result.total_inconsistencies == 2


class TestMockDataConsistency:
    """Test consistency between different mock data generators."""
    
    def test_scraped_data_to_listing_input_compatibility(self):
        """Test that scraped data can be used to generate compatible ListingInput."""
        scraped_data = generate_mock_scraped_property_data()
        listing = generate_mock_listing_input()
        
        # Both should have compatible structure
        assert scraped_data["location"]["city"] == listing.city
        assert scraped_data["price"] is not None
        assert listing.list_price > 0
    
    def test_listing_input_to_consistency_result_compatibility(self):
        """Test that ListingInput can be used to generate compatible ConsistencyCheckResult."""
        listing = generate_mock_listing_input()
        consistency = generate_mock_result_for_property(
            url=str(listing.listing_url) if listing.listing_url else "",
            property_address=listing.property_address,
        )
        
        # Both should reference the same property conceptually
        assert consistency.property_address == listing.property_address
