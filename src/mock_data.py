"""Mock data generation for inconsistency results and property listings."""

from datetime import date, datetime
from typing import Any

from src.models import (
    ConsistencyCheckResult,
    InconsistencyFinding,
    ListingInput,
    SeverityLevel,
)


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


def generate_mock_scraped_property_data(
    url: str | None = None,
    property_id: str | None = None,
) -> dict[str, Any]:
    """Generate mock scraped property data similar to what extract_property_data returns.
    
    Args:
        url: Property listing URL (optional, will generate if not provided)
        property_id: Property ID (optional, will generate if not provided)
    
    Returns:
        Dictionary containing mock scraped property data
    """
    if not url:
        url = "https://www.bezrealitky.cz/nemovitosti-byty-domy/974793-nabidka-prodej-bytu-hostynska-praha"
    
    if not property_id:
        property_id = "974793"
    
    return {
        "url": url,
        "propertyId": property_id,
        "title": "Prodej bytu 3+kk 57 m², Hostýnská, Praha - Strašnice",
        "category": "Prodej",
        "description": "Nabízím k prodeji krásný byt o dispozici 3kk po rekonstrukci v osobním vlastnictví. Byt se nachází ve velmi dobrém stavu, je plně vybavený a nachází se v blízkosti centra. Ideální pro rodinu nebo investici.",
        "descriptionEnglish": "I am offering for sale a beautiful 3-room apartment after renovation in personal ownership. The apartment is in very good condition, fully furnished and located near the center. Ideal for family or investment.",
        "price": "8 499 000 Kč",
        "priceType": "sale",
        "location": {
            "full": "Praha - Strašnice",
            "city": "Praha",
            "district": "Strašnice",
            "street": "Hostýnská",
        },
        "propertyDetails": {
            "area": "57 m²",
            "disposition": "3+kk",
            "floor": "2. podlaží z 5",
            "buildingType": "Panel",
            "condition": "Velmi dobrý",
            "ownership": "Osobní",
            "furnished": "Částečně",
            "energyRating": "C - Úsporná",
            "pricePerM2": "149 105 Kč / m2",
        },
        "attributes": {
            "Užitná plocha": "57 m²",
            "Dispozice": "3+kk",
            "Podlaží": "2. podlaží z 5",
            "Konstrukce budovy": "Panel",
            "Stav": "Velmi dobrý",
            "Vlastnictví": "Osobní",
            "Vybaveno": "Částečně",
            "PENB": "C - Úsporná",
            "Cena za jednotku": "149 105 Kč / m2",
        },
        "features": ["Částečně vybaveno", "Sklep 2 m²", "Lodžie 3 m²"],
        "amenities": ["Sklep 2 m²", "Lodžie 3 m²", "Internet", "Parkování"],
        "images": [
            "https://img.bezrealitky.cz/example1.jpg",
            "https://img.bezrealitky.cz/example2.jpg",
        ],
        "breadcrumbs": ["Domů", "Prodej", "Byt", "Praha"],
        "seller": {
            "type": "owner",
            "note": "Prodává přímo majitel - bez provize",
        },
        "scrapedAt": url,
    }


def generate_mock_listing_input(
    listing_id: str | None = None,
    url: str | None = None,
) -> ListingInput:
    """Generate a mock ListingInput object for testing.
    
    Args:
        listing_id: Listing ID (optional, will generate if not provided)
        url: Listing URL (optional, will generate if not provided)
    
    Returns:
        ListingInput object with mock data
    """
    if not url:
        url = "https://www.bezrealitky.cz/nemovitosti-byty-domy/974793-nabidka-prodej-bytu-hostynska-praha"
    
    if not listing_id:
        import hashlib
        listing_id = hashlib.md5(url.encode()).hexdigest()[:12].upper()
        listing_id = f"PRG-{listing_id}"
    
    return ListingInput(
        listing_id=listing_id,
        listing_url=url,
        property_address="Hostýnská 123, Praha - Strašnice",
        city="Praha",
        state="Czech Republic",
        zip_code="10000",
        bedrooms=3,
        bathrooms=1.0,
        square_feet=614,  # 57 m² * 10.764
        lot_size_sqft=None,
        year_built=1985,
        property_type="Apartment",
        stories=5,
        garage_spaces=0,
        list_price=8499000.0,
        has_pool=False,
        has_garage=False,
        has_basement=True,
        has_fireplace=False,
        description="Nabízím k prodeji krásný byt o dispozici 3kk po rekonstrukci v osobním vlastnictví. Byt se nachází ve velmi dobrém stavu, je plně vybavený a nachází se v blízkosti centra. Ideální pro rodinu nebo investici.",
        realtor_name=None,
        realtor_agency=None,
        listing_date=date.today(),
    )


def generate_mock_listing_inputs() -> list[ListingInput]:
    """Generate multiple mock ListingInput objects for testing.
    
    Returns:
        List of ListingInput objects with various scenarios
    """
    return [
        generate_mock_listing_input(
            listing_id="PRG-TEST-001",
            url="https://www.bezrealitky.cz/nemovitosti-byty-domy/974793-nabidka-prodej-bytu-hostynska-praha",
        ),
        ListingInput(
            listing_id="PRG-TEST-002",
            listing_url="https://www.bezrealitky.cz/nemovitosti-byty-domy/981201-nabidka-prodej-bytu-pocernicka-praha",
            property_address="Počernická 45, Praha - Malešice",
            city="Praha",
            state="Czech Republic",
            zip_code="10000",
            bedrooms=4,
            bathrooms=2.0,
            square_feet=1076,  # 100 m² * 10.764
            lot_size_sqft=None,
            year_built=2010,
            property_type="Apartment",
            stories=8,
            garage_spaces=1,
            list_price=12500000.0,
            has_pool=False,
            has_garage=True,
            has_basement=True,
            has_fireplace=True,
            description="Luxusní byt 4+1 v novostavbě s garáží a balkonem. Byt je ve výborném stavu, plně vybavený a nachází se v klidné lokalitě s výbornou dopravní dostupností.",
            listing_date=date.today(),
        ),
        ListingInput(
            listing_id="PRG-TEST-003",
            listing_url="https://www.bezrealitky.cz/nemovitosti-byty-domy/981586-nabidka-prodej-bytu-vratislavska-praha",
            property_address="Vratislavská 12, Praha 2 - Nusle",
            city="Praha",
            state="Czech Republic",
            zip_code="12000",
            bedrooms=2,
            bathrooms=1.0,
            square_feet=430,  # 40 m² * 10.764
            lot_size_sqft=None,
            year_built=1995,
            property_type="Apartment",
            stories=4,
            garage_spaces=0,
            list_price=5500000.0,
            has_pool=False,
            has_garage=False,
            has_basement=False,
            has_fireplace=False,
            description="Kompaktní byt 2+kk v panelovém domě. Byt je částečně vybavený a nachází se v blízkosti metra. Vhodné pro mladé páry nebo jako investice.",
            listing_date=date.today(),
        ),
    ]
