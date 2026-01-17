"""
Prague Real Estate Data - Q3 2024 + Crime Statistics 2025
Data sources: 
- Prague Real Index (Q3 2024)
- Czech Police Crime Data (2025)
- Prague Municipal Districts Population (https://praha.eu/mestske-casti)
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
        "crime_nasilna": 125,
        "crime_kradeze_vloupanim": 549,
        "crime_pozary": 10
    }
}


def get_info(district_no: int) -> DistrictInfo:
    """Get real estate and crime information for a specific Prague district."""
    district_key = f"Prague {district_no}"
    district_data = prague_real_estate[district_key]
    
    return DistrictInfo(
        district_no=district_no,
        avg_price_per_sqm_czk=district_data["avg_price_per_sqm_czk"],
        price_change_percent=district_data["price_change_percent"],
        price_category=district_data["price_category"],
        population=district_data["population"],
        crime_nasilna=district_data["crime_nasilna"],
        crime_kradeze_vloupanim=district_data["crime_kradeze_vloupanim"],
        crime_pozary=district_data["crime_pozary"]
    )
