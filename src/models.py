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
    population: int = Field(..., description="Number of citizens in the district")
    kebab_index_normalized: float = Field(..., description="Normalized number (higher = better) of high-quality kebab restaurants in the district (rating > 4.5, reviews > 100)")
    crime_nasilna_normalized: float = Field(..., description="Violent crimes normalized rate (higher = worse)")
    crime_kradeze_vloupanim_normalized: float = Field(..., description="Burglary crimes normalized rate (higher = worse)")
    crime_pozary_normalized: float = Field(..., description="Fire incidents normalized rate (higher = worse)")


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
    bedrooms: int = Field(
        ..., 
        ge=0,
        description="Number of bedrooms. Must be 0 or greater. Extract from disposition (e.g., '3+kk' = 3 bedrooms)"
    )
    bathrooms: float = Field(
        ..., 
        ge=0, 
        description="Number of bathrooms (can be decimal for half-baths). Must be 0 or greater. Typically 1-2 for Czech apartments"
    )
    square_meters: int | None = Field(
        None, 
        ge=0,
        description="Property size in square meters. Must be 0 or greater if provided. Convert from m² (1 m² = 10.764 sqft)"
    )
    lot_size_sqft: int | None = Field(
        None, 
        ge=0,
        description="Lot size in square meters. Must be 0 or greater if provided"
    )
    year_built: int | None = Field(
        None, 
        ge=1800, 
        le=2030,
        description="Year the property was built. Must be between 1800 and 2030 if provided"
    )

    property_type: str | None = Field(
        None, 
        description="Property type (e.g., 'Apartment', 'Single Family', 'Condo', 'Townhouse'). For Czech listings, typically 'Apartment'"
    )
    stories: int | None = Field(
        None, 
        ge=1,
        description="Number of stories/floors. Must be 1 or greater if provided"
    )
    garage_spaces: int | None = Field(
        None, 
        ge=0,
        description="Number of garage spaces. Must be 0 or greater if provided"
    )

    # Pricing
    list_price: float = Field(
        ..., 
        gt=0,
        description="Property listing price in CZK. MUST be greater than 0. Extract numeric value from price string (e.g., '8 499 000 Kč' -> 8499000.0)"
    )

    # Features (structured)  # noqa: ERA001
    has_pool: bool | None = None
    has_garage: bool | None = None
    has_basement: bool | None = None
    has_fireplace: bool | None = None

    # The text description (what we'll fact-check against the above)
    description: str = Field(
        ..., 
        min_length=10,
        description="The full text description written by the realtor. Must be at least 10 characters long. Use the scraped description or a summary if description is missing. Use original language of the description."
    )

    # Optional metadata
    realtor_name: str | None = None
    realtor_agency: str | None = None
    listing_date: date | None = None


class InconsistencyFinding(BaseModel):
    """A single inconsistency found between description and listing data"""

    field_name: str = Field(
        ..., 
        description="Field name with the issue (e.g., 'bedrooms', 'square_meters', 'list_price')"
    )

    description_says: str = Field(
        ..., 
        max_length=200,
        description="What the description claims (keep concise, max 200 chars)"
    )
    listing_data_says: str = Field(
        ..., 
        max_length=200,
        description="What the structured data shows (keep concise, max 200 chars)"
    )

    severity: SeverityLevel = Field(
        ..., 
        description="Severity: 'critical' for major contradictions, 'medium' for notable issues, 'low' for minor discrepancies"
    )
    explanation: str = Field(
        ..., 
        max_length=300,
        description="Brief explanation of the inconsistency (keep concise, max 300 chars)"
    )


class ConsistencyCheckResult(BaseModel):
    """Result of checking a listing for internal consistency"""

    listing_id: str = Field(..., description="Listing ID from the original listing")
    property_address: str = Field(..., description="Property address")
    checked_at: datetime = Field(default_factory=datetime.now, description="Timestamp when check was performed")

    # Simple metrics
    total_inconsistencies: int = Field(
        ..., 
        ge=0,
        description="Total number of inconsistencies found (must match findings array length)"
    )
    is_consistent: bool = Field(
        ..., 
        description="True if no inconsistencies found (total_inconsistencies == 0), false otherwise"
    )

    # The findings - limit to reasonable number to avoid huge responses
    findings: list[InconsistencyFinding] = Field(
        default_factory=list,
        max_length=20,
        description="Array of inconsistency findings (max 20 items, keep most important ones)"
    )

    # Quick summary
    summary: str = Field(
        ..., 
        max_length=200,
        description="Brief one-line summary of the check (max 200 chars)"
    )


# Bezrealitky.cz Scraper Models

class CrimeStats(BaseModel):
    """Crime statistics for a district"""
    
    violentCrimes: int = Field(..., description="Number of violent crimes (násilná kriminalita)")
    burglaries: int = Field(..., description="Number of burglaries (krádeže vloupáním)")
    fires: int = Field(..., description="Number of fires (požáry)")


class DistrictStats(BaseModel):
    """Real estate and crime statistics for a Prague district"""
    
    avgPricePerSqmCzk: int = Field(..., description="Average price per square meter in CZK (Q3 2024)")
    priceChangePercent: float = Field(..., description="Year-over-year price change percentage")
    priceCategory: str = Field(..., description="Price category: premium, high, or medium")
    crimeStats: CrimeStats = Field(..., description="Crime statistics for 2025")


class LocationInfo(BaseModel):
    """Structured location information"""
    
    city: str | None = Field(None, description="City (e.g., Praha, Brno)")
    district: str | None = Field(None, description="District/neighborhood (e.g., Karlín, Malešice, Strašnice)")
    street: str | None = Field(None, description="Street name (e.g., Sokolovská, Počernická)")
    full: str | None = Field(None, description="Full location string (e.g., Praha - Strašnice)")
    pragueAdminDistrict: str | None = Field(None, description="Prague administrative district (e.g., Prague 8, Prague 10)")


class PropertyInfo(BaseModel):
    """Core property specifications"""
    
    area: str | None = Field(None, description="Usable area (e.g., 57 m², 60 m²)")
    disposition: str | None = Field(None, description="Layout/proportions (e.g., 3+kk, 2+1, 4+1)")
    floor: str | None = Field(None, description="Floor information (e.g., 2. podlaží z 5)")
    buildingType: str | None = Field(None, description="Building construction type (e.g., Panel, Brick)")
    condition: str | None = Field(None, description="Property condition (e.g., Velmi dobrý)")
    ownership: str | None = Field(None, description="Ownership type (e.g., Osobní)")
    furnished: str | None = Field(None, description="Furnished status (e.g., Částečně, Ano, Ne)")
    energyRating: str | None = Field(None, description="Energy efficiency rating (e.g., C - Úsporná)")
    availableFrom: str | None = Field(None, description="Available from date")
    pricePerM2: str | None = Field(None, description="Price per square meter")


class SellerInfo(BaseModel):
    """Information about the property seller/agent"""
    
    type: str | None = Field(None, description="Seller type: 'owner' or 'agent'")
    note: str | None = Field(None, description="Additional notes (e.g., 'bez provize')")
    name: str | None = Field(None, description="Seller or agent name")
    phone: str | None = Field(None, description="Contact phone number")
    email: str | None = Field(None, description="Contact email address")


class ScrapeOutput(BaseModel):
    """Output model for scraped Bezrealitky.cz property listing data"""
    
    # Core information
    url: str = Field(..., description="URL of the scraped listing")
    propertyId: str | None = Field(None, description="Unique property listing ID")
    title: str | None = Field(None, description="Property listing title")
    category: str | None = Field(None, description="Listing category (Prodej or Pronájem)")
    description: str | None = Field(None, description="Full property description in Czech")
    descriptionEnglish: str | None = Field(None, description="Property description in English (if available)")
    
    # Pricing
    price: str | None = Field(None, description="Property price (formatted with currency)")
    priceType: Literal["rental", "sale"] | None = Field(
        None, 
        description="Type of listing: 'rental' for rent, 'sale' for purchase"
    )
    
    # Location - ALWAYS EXTRACT THESE FIELDS
    location: LocationInfo = Field(
        default_factory=LocationInfo,
        description="Structured location information with city, district, and street"
    )
    
    # District statistics (real estate & crime data)
    districtStats: DistrictStats | None = Field(
        None,
        description="Real estate and crime statistics for Prague districts (automatically added for Prague properties)"
    )
    
    # Property specifications - ALWAYS EXTRACT THESE FIELDS
    propertyDetails: PropertyInfo = Field(
        default_factory=PropertyInfo,
        description="Core property specifications including area and disposition"
    )
    
    # Additional information
    features: list[str] = Field(
        default_factory=list,
        description="Key property features and highlights"
    )
    amenities: list[str] = Field(
        default_factory=list,
        description="Available amenities (cellar, loggia, parking, etc.)"
    )
    images: list[str] = Field(
        default_factory=list,
        description="URLs of property images"
    )
    breadcrumbs: list[str] = Field(
        default_factory=list,
        description="Navigation breadcrumbs for categorization"
    )
    
    # Raw attributes
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Dictionary of all raw property attributes"
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
                "url": "https://www.bezrealitky.cz/nemovitosti-byty-domy/974793-nabidka-prodej-bytu-hostynska-praha",
                "propertyId": "974793",
                "title": "Prodej bytu 3+kk 57 m², Hostýnská, Praha - Strašnice",
                "category": "Prodej",
                "description": "Nabízím k prodeji krásný byt o dispozici 3kk po rekonstrukci v osobním vlastnictví...",
                "descriptionEnglish": "I am offering for sale a beautiful 3-room apartment...",
                "price": "8 499 000 Kč",
                "priceType": "sale",
                "location": {
                    "city": "Praha",
                    "district": "Strašnice",
                    "street": "Hostýnská",
                    "full": "Praha - Strašnice",
                    "pragueAdminDistrict": "Prague 10"
                },
                "districtStats": {
                    "avgPricePerSqmCzk": 127800,
                    "priceChangePercent": 2.6,
                    "priceCategory": "medium",
                    "crimeStats": {
                        "violentCrimes": 125,
                        "burglaries": 549,
                        "fires": 10
                    }
                },
                "propertyDetails": {
                    "area": "57 m²",
                    "disposition": "3+kk",
                    "floor": "2. podlaží z 5",
                    "buildingType": "Panel",
                    "condition": "Velmi dobrý",
                    "energyRating": "C - Úsporná",
                    "pricePerM2": "149 105 Kč / m2"
                },
                "features": ["Částečně vybaveno", "Sklep 2 m²", "Lodžie 3 m²"],
                "amenities": ["Sklep 2 m²", "Lodžie 3 m²", "Internet"],
                "images": ["https://img.bezrealitky.cz/..."],
                "attributes": {
                    "Dostupné od": "20. 12. 2025",
                    "Konstrukce budovy": "Panel",
                    "Užitná plocha": "57 m²"
                },
                "seller": {
                    "type": "owner",
                    "note": "Prodává přímo majitel - bez provize"
                },
                "breadcrumbs": ["Domů", "Prodej", "Byt", "Praha"],
                "scrapedAt": "https://www.bezrealitky.cz/nemovitosti-byty-domy/974793-nabidka-prodej-bytu-hostynska-praha"
            }
        }
