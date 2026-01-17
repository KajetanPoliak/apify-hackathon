from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


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
