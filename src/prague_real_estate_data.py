"""
Prague Real Estate Data - Q3 2024 + Crime Statistics 2025 + Kebab Index
Data sources: 
- Prague Real Index (Q3 2024)
- Czech Police Crime Data (2025)
- Prague Municipal Districts Population (https://praha.eu/mestske-casti)
- Kebab Index: Google Places API via Apify (rating > 4, reviews > 50)
"""
from typing import Literal

from src.models import DistrictInfo


InfoType = Literal["avg_price", "price_change", "price_category", "all"]

# Prague Real Index data by district (Q3 2024) + Crime data (2025)
prague_real_estate = {
    "Prague 1": {
        "district": 1,
        "price_change_percent": -4.2,
        "avg_price_per_sqm_czk": 194400,
        "price_category": "premium",
        "population": 30343,
        "kebab_index": 13,
        "crime_nasilna": 181,
        "crime_kradeze_vloupanim": 303,
        "crime_pozary": 8
    },
    "Prague 2": {
        "district": 2,
        "price_change_percent": 11.6,
        "avg_price_per_sqm_czk": 177000,
        "price_category": "high",
        "population": 49624,
        "kebab_index": 17,
        "crime_nasilna": 149,
        "crime_kradeze_vloupanim": 355,
        "crime_pozary": 3
    },
    "Prague 3": {
        "district": 3,
        "price_change_percent": 6.2,
        "avg_price_per_sqm_czk": 155500,
        "price_category": "high",
        "population": 72991,
        "kebab_index": 12,
        "crime_nasilna": 75,
        "crime_kradeze_vloupanim": 353,
        "crime_pozary": 2
    },
    "Prague 4": {
        "district": 4,
        "price_change_percent": 5.0,
        "avg_price_per_sqm_czk": 129500,
        "price_category": "medium",
        "population": 130287,
        "kebab_index": 10,
        "crime_nasilna": 142,
        "crime_kradeze_vloupanim": 526,
        "crime_pozary": 12
    },
    "Prague 5": {
        "district": 5,
        "price_change_percent": 3.5,
        "avg_price_per_sqm_czk": 148300,
        "price_category": "high",
        "population": 83573,
        "kebab_index": 8,
        "crime_nasilna": 101,
        "crime_kradeze_vloupanim": 407,
        "crime_pozary": 6
    },
    "Prague 6": {
        "district": 6,
        "price_change_percent": -9.6,
        "avg_price_per_sqm_czk": 144300,
        "price_category": "high",
        "population": 100600,
        "kebab_index": 7,
        "crime_nasilna": 93,
        "crime_kradeze_vloupanim": 173,
        "crime_pozary": 4
    },
    "Prague 7": {
        "district": 7,
        "price_change_percent": -7.2,
        "avg_price_per_sqm_czk": 164500,
        "price_category": "high",
        "population": 40843,
        "kebab_index": 11,
        "crime_nasilna": 103,
        "crime_kradeze_vloupanim": 106,
        "crime_pozary": 4
    },
    "Prague 8": {
        "district": 8,
        "price_change_percent": 7.6,
        "avg_price_per_sqm_czk": 134400,
        "price_category": "medium",
        "population": 102021,
        "kebab_index": 7,
        "crime_nasilna": 151,
        "crime_kradeze_vloupanim": 329,
        "crime_pozary": 16
    },
    "Prague 9": {
        "district": 9,
        "price_change_percent": -4.3,
        "avg_price_per_sqm_czk": 122200,
        "price_category": "medium",
        "population": 50364,
        "kebab_index": 8,
        "crime_nasilna": 74,
        "crime_kradeze_vloupanim": 215,
        "crime_pozary": 4
    },
    "Prague 10": {
        "district": 10,
        "price_change_percent": 2.6,
        "avg_price_per_sqm_czk": 127800,
        "price_category": "medium",
        "population": 110000,
        "kebab_index": 19,
        "crime_nasilna": 125,
        "crime_kradeze_vloupanim": 549,
        "crime_pozary": 10
    }
}

def get_multiplier(property: str) -> float:
    """
    Calculate a multiplier to normalize a property per capita.
    
    The multiplier scales the property values so that the maximum 
    per-capita value across all districts equals 1.
    
    Args:
        property: Name of the property field (e.g., 'kebab_index', 'crime_nasilna')
    
    Returns:
        float: Multiplier value where max_value * multiplier = 1
    """
    max_ratio = 0.0
    
    # Go through all districts
    for district_data in prague_real_estate.values():
        property_value = district_data.get(property, 0)
        population = district_data.get("population", 1)  # Avoid division by zero
        
        # Calculate per-capita ratio
        ratio = property_value / population
        
        # Track maximum
        if ratio > max_ratio:
            max_ratio = ratio
    
    # Calculate multiplier such that max_ratio * multiplier = 1
    if max_ratio > 0:
        return 1.0 / max_ratio
    else:
        return 1.0  # Return 1.0 if no valid data


def get_info(district_no: int) -> DistrictInfo:
    """Get real estate and crime information for a specific Prague district."""
    district_key = f"Prague {district_no}"
    district_data = prague_real_estate[district_key]
    
    population = district_data["population"]
    
    # Calculate normalized values: (property / population) * multiplier
    kebab_index_normalized = (district_data["kebab_index"] / population) * get_multiplier("kebab_index")
    crime_nasilna_normalized = (district_data["crime_nasilna"] / population) * get_multiplier("crime_nasilna")
    crime_kradeze_vloupanim_normalized = (district_data["crime_kradeze_vloupanim"] / population) * get_multiplier("crime_kradeze_vloupanim")
    crime_pozary_normalized = (district_data["crime_pozary"] / population) * get_multiplier("crime_pozary")
    
    return DistrictInfo(
        district_no=district_no,
        avg_price_per_sqm_czk=district_data["avg_price_per_sqm_czk"],
        price_change_percent=district_data["price_change_percent"],
        price_category=district_data["price_category"],
        population=population,
        kebab_index_normalized=kebab_index_normalized,
        crime_nasilna_normalized=crime_nasilna_normalized,
        crime_kradeze_vloupanim_normalized=crime_kradeze_vloupanim_normalized,
        crime_pozary_normalized=crime_pozary_normalized
    )
