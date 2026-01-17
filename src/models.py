from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class DistrictInfo(BaseModel):
    """Real estate and crime information for a Prague district"""
    
    district_no: int = Field(..., description="District number (1-10)")
    avg_price_per_sqm_czk: int = Field(..., description="Average price per square meter in CZK")
    price_change_percent: float = Field(..., description="Price change percentage")
    price_category: Literal["premium", "high", "medium"] = Field(..., description="Price category")
    crime_nasilna: int = Field(..., description="Violent crimes count")
    crime_kradeze_vloupanim: int = Field(..., description="Burglary crimes count")
    crime_pozary: int = Field(..., description="Fire incidents count")


class SeverityLevel(str, Enum):
    """How serious the inconsistency is"""
    CRITICAL = "critical"  # Major contradiction
    MEDIUM = "medium"      # Notable inconsistency
    LOW = "low"            # Minor discrepancy

class ListingInput(BaseModel):
    """Input model representing a real estate listing to be analyzed"""

    # Identifiers
    listing_id: str = Field(..., description="Unique listing identifier (e.g., MLS number)")
    listing_url: HttpUrl | None = None

    # Basic property info
    property_address: str
    city: str
    state: str
    zip_code: str

    # Structured listing data (the "facts")
    bedrooms: int = Field(..., ge=0)
    bathrooms: float = Field(..., ge=0, description="Can be decimal for half-baths")
    square_feet: int | None = Field(None, ge=0)
    lot_size_sqft: int | None = Field(None, ge=0)
    year_built: int | None = Field(None, ge=1800, le=2030)

    property_type: str | None = Field(None, description="e.g., Single Family, Condo, Townhouse")
    stories: int | None = Field(None, ge=1)
    garage_spaces: int | None = Field(None, ge=0)

    # Pricing
    list_price: float = Field(..., gt=0)

    # Features (structured)  # noqa: ERA001
    has_pool: bool | None = None
    has_garage: bool | None = None
    has_basement: bool | None = None
    has_fireplace: bool | None = None

    # The text description (what we'll fact-check against the above)
    description: str = Field(..., min_length=10,
                           description="The full text description written by the realtor")

    # Optional metadata
    realtor_name: str | None = None
    realtor_agency: str | None = None
    listing_date: date | None = None


class InconsistencyFinding(BaseModel):
    """A single inconsistency found between description and listing data"""

    field_name: str = Field(..., description="Which field has the issue (e.g., 'bedrooms', 'square_feet')")

    description_says: str = Field(..., description="What the text description claims")
    listing_data_says: str = Field(..., description="What the structured data shows")

    severity: SeverityLevel
    explanation: str = Field(..., description="Why this is inconsistent")


class ConsistencyCheckResult(BaseModel):
    """Result of checking a listing for internal consistency"""

    listing_id: str
    property_address: str
    checked_at: datetime = Field(default_factory=datetime.now)

    # Simple metrics
    total_inconsistencies: int
    is_consistent: bool = Field(..., description="True if no inconsistencies found")

    # The findings
    findings: list[InconsistencyFinding] = Field(default_factory=list)

    # Quick summary
    summary: str = Field(..., description="One-line summary of the check")


# Sreality.cz Scraper Models

class SellerInfo(BaseModel):
    """Information about the property seller/agent"""
    
    name: str | None = Field(None, description="Seller or agent name")
    phone: str | None = Field(None, description="Contact phone number")
    email: str | None = Field(None, description="Contact email address")


class ScrapeOutput(BaseModel):
    """Output model for scraped Sreality.cz property listing data"""
    
    # Core information
    url: str = Field(..., description="URL of the scraped listing")
    title: str | None = Field(None, description="Property listing title")
    description: str | None = Field(None, description="Full property description text")
    
    # Pricing
    price: str | None = Field(None, description="Property price (formatted with currency)")
    priceType: Literal["rental", "sale"] | None = Field(
        None, 
        description="Type of listing: 'rental' for rent, 'sale' for purchase"
    )
    
    # Location
    location: str | None = Field(None, description="Property location (city, district)")
    
    # Property details
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Dictionary of property attributes (area, energy rating, features, etc.)"
    )
    
    # Contact information
    seller: SellerInfo = Field(
        default_factory=SellerInfo,
        description="Seller/agent contact information"
    )
    
    # Metadata
    scrapedAt: str = Field(..., description="URL where the data was scraped from")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.sreality.cz/detail/prodej/byt/3+kk/praha-zizkov-borivojova/1241056076",
                "title": "Prodej bytu 3+kk 81 m² Bořivojova, Praha - Žižkov",
                "description": "Novostavba podkrovního bytu o celkové ploše 81,8 m²...",
                "price": "17 895 000 Kč",
                "priceType": "sale",
                "location": "Praha - Žižkov",
                "attributes": {
                    "Celková cena": "17 895 000 Kč",
                    "Plocha": "Užitná plocha 81 m²",
                    "Energetická náročnost": "Úsporná"
                },
                "seller": {
                    "name": "Petr Hnátek",
                    "phone": "+420 602 442 500",
                    "email": "hnatek@stavba-design.cz"
                },
                "scrapedAt": "https://www.sreality.cz/detail/prodej/byt/3+kk/praha-zizkov-borivojova/1241056076"
            }
        }
