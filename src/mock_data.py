"""Mock data generation for inconsistency results."""

from datetime import datetime

from src.models import ConsistencyCheckResult, InconsistencyFinding, SeverityLevel


def generate_mock_inconsistency_results() -> list[ConsistencyCheckResult]:
    """Generate mock inconsistency results for testing.
    
    Returns:
        List of ConsistencyCheckResult objects with various inconsistency scenarios
    """
    mock_results = [
        ConsistencyCheckResult(
            listing_id="PRG-2025-001",
            property_address="Martinská 12, Praha 1 - Staré Město",
            checked_at=datetime.now(),
            total_inconsistencies=3,
            is_consistent=False,
            findings=[
                InconsistencyFinding(
                    field_name="bedrooms",
                    description_says="3 ložnicový byt",
                    listing_data_says="4+1 (4 bedrooms)",
                    severity=SeverityLevel.CRITICAL,
                    explanation="Description mentions 3 bedrooms but structured data shows 4+1 layout with 4 bedrooms"
                ),
                InconsistencyFinding(
                    field_name="square_feet",
                    description_says="prostorný byt o ploše 180 m²",
                    listing_data_says="Užitná plocha 150 m²",
                    severity=SeverityLevel.MEDIUM,
                    explanation="Description claims 180 m² but actual usable area is 150 m² (30 m² difference)"
                ),
                InconsistencyFinding(
                    field_name="price",
                    description_says="výhodná cena 55 000 Kč/měsíc",
                    listing_data_says="55 000 Kč/měsíc + poplatky",
                    severity=SeverityLevel.LOW,
                    explanation="Description omits mention of additional fees, making the price appear lower than actual cost"
                ),
            ],
            summary="Found 3 inconsistencies: bedroom count mismatch (critical), area discrepancy (medium), and incomplete price information (low)"
        ),
        ConsistencyCheckResult(
            listing_id="PRG-2025-002",
            property_address="Václavské náměstí 45, Praha 1 - Nové Město",
            checked_at=datetime.now(),
            total_inconsistencies=2,
            is_consistent=False,
            findings=[
                InconsistencyFinding(
                    field_name="year_built",
                    description_says="novostavba z roku 2023",
                    listing_data_says="Rok výstavby: 2020",
                    severity=SeverityLevel.MEDIUM,
                    explanation="Description claims new construction from 2023, but building records show construction year as 2020"
                ),
                InconsistencyFinding(
                    field_name="has_pool",
                    description_says="bazén v zahradě",
                    listing_data_says="Bazén: Ne",
                    severity=SeverityLevel.CRITICAL,
                    explanation="Description mentions pool in garden, but structured data explicitly states no pool available"
                ),
            ],
            summary="Found 2 inconsistencies: incorrect construction year (medium) and false pool claim (critical)"
        ),
        ConsistencyCheckResult(
            listing_id="PRG-2025-003",
            property_address="Vinohradská 120, Praha 2 - Vinohrady",
            checked_at=datetime.now(),
            total_inconsistencies=1,
            is_consistent=False,
            findings=[
                InconsistencyFinding(
                    field_name="property_type",
                    description_says="rodinný dům",
                    listing_data_says="Typ: Byt",
                    severity=SeverityLevel.CRITICAL,
                    explanation="Description describes property as family house, but structured data categorizes it as apartment"
                ),
            ],
            summary="Found 1 critical inconsistency: property type mismatch between description and structured data"
        ),
        ConsistencyCheckResult(
            listing_id="PRG-2025-004",
            property_address="Letná 15, Praha 7 - Holešovice",
            checked_at=datetime.now(),
            total_inconsistencies=0,
            is_consistent=True,
            findings=[],
            summary="No inconsistencies found - all description claims match structured data"
        ),
        ConsistencyCheckResult(
            listing_id="PRG-2025-005",
            property_address="Karlínské náměstí 8, Praha 8 - Karlín",
            checked_at=datetime.now(),
            total_inconsistencies=4,
            is_consistent=False,
            findings=[
                InconsistencyFinding(
                    field_name="bathrooms",
                    description_says="2 koupelny",
                    listing_data_says="Koupelny: 1",
                    severity=SeverityLevel.CRITICAL,
                    explanation="Description claims 2 bathrooms but structured data shows only 1 bathroom"
                ),
                InconsistencyFinding(
                    field_name="has_garage",
                    description_says="garáž k dispozici",
                    listing_data_says="Parkování: Ne",
                    severity=SeverityLevel.MEDIUM,
                    explanation="Description mentions garage available, but parking information indicates no parking/garage"
                ),
                InconsistencyFinding(
                    field_name="energy_rating",
                    description_says="nízká energetická náročnost",
                    listing_data_says="Energetická náročnost: Mimořádně nehospodárná",
                    severity=SeverityLevel.MEDIUM,
                    explanation="Description claims low energy consumption, but energy rating shows extremely inefficient"
                ),
                InconsistencyFinding(
                    field_name="condition",
                    description_says="ve výborném stavu",
                    listing_data_says="Stav: K rekonstrukci",
                    severity=SeverityLevel.CRITICAL,
                    explanation="Description claims excellent condition, but structured data indicates property needs reconstruction"
                ),
            ],
            summary="Found 4 inconsistencies: bathroom count (critical), garage availability (medium), energy rating (medium), and property condition (critical)"
        ),
    ]
    
    return mock_results


def generate_mock_result_for_property(
    url: str,
    property_address: str | None = None,
    title: str | None = None,
    description: str | None = None,
    price: str | None = None,
    reason: str = "LLM analysis failed",
) -> ConsistencyCheckResult:
    """Generate a mock inconsistency result for a specific property.
    
    Args:
        url: Property listing URL
        property_address: Property address
        title: Property title
        description: Property description
        price: Property price
        reason: Reason for generating mock data
    
    Returns:
        ConsistencyCheckResult object for the property
    """
    import hashlib
    
    listing_id = hashlib.md5(url.encode()).hexdigest()[:12].upper()
    listing_id = f"PRG-{listing_id}"
    
    address = property_address or title or url
    
    return ConsistencyCheckResult(
        listing_id=listing_id,
        property_address=address,
        checked_at=datetime.now(),
        total_inconsistencies=2,
        is_consistent=False,
        findings=[
            InconsistencyFinding(
                field_name="description",
                description_says=description[:100] + "..." if description and len(description) > 100 else (description or "N/A"),
                listing_data_says=f"Title: {title or 'N/A'}, Price: {price or 'N/A'}",
                severity=SeverityLevel.MEDIUM,
                explanation=f"Mock inconsistency result generated: {reason}"
            ),
            InconsistencyFinding(
                field_name="price",
                description_says=price or "Price not specified in description",
                listing_data_says=f"Structured price: {price or 'N/A'}",
                severity=SeverityLevel.LOW,
                explanation=f"Mock inconsistency result generated due to: {reason}"
            ),
        ],
        summary=f"Mock inconsistency check result ({reason}): Found 2 inconsistencies as fallback data"
    )
