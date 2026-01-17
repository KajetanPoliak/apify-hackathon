"""
Prague Real Estate Data - Q3 2024
Data source: Prague Real Index
"""
from typing import TypedDict, Literal, Optional


class DistrictInfo(TypedDict):
    """Type definition for district real estate information"""
    district_no: int
    avg_price_per_sqm_czk: int
    price_change_percent: float
    price_category: Literal["premium", "high", "medium"]


InfoType = Literal["avg_price", "price_change", "price_category", "all"]

# Prague Real Index data by district
prague_real_estate = {
    "Prague 1": {
        "district": 1,
        "price_change_percent": -4.2,
        "avg_price_per_sqm_czk": 194400,
        "price_category": "premium"
    },
    "Prague 2": {
        "district": 2,
        "price_change_percent": 11.6,
        "avg_price_per_sqm_czk": 177000,
        "price_category": "high"
    },
    "Prague 3": {
        "district": 3,
        "price_change_percent": 6.2,
        "avg_price_per_sqm_czk": 155500,
        "price_category": "high"
    },
    "Prague 4": {
        "district": 4,
        "price_change_percent": 5.0,
        "avg_price_per_sqm_czk": 129500,
        "price_category": "medium"
    },
    "Prague 5": {
        "district": 5,
        "price_change_percent": 3.5,
        "avg_price_per_sqm_czk": 148300,
        "price_category": "high"
    },
    "Prague 6": {
        "district": 6,
        "price_change_percent": -9.6,
        "avg_price_per_sqm_czk": 144300,
        "price_category": "high"
    },
    "Prague 7": {
        "district": 7,
        "price_change_percent": -7.2,
        "avg_price_per_sqm_czk": 164500,
        "price_category": "high"
    },
    "Prague 8": {
        "district": 8,
        "price_change_percent": 7.6,
        "avg_price_per_sqm_czk": 134400,
        "price_category": "medium"
    },
    "Prague 9": {
        "district": 9,
        "price_change_percent": -4.3,
        "avg_price_per_sqm_czk": 122200,
        "price_category": "medium"
    },
    "Prague 10": {
        "district": 10,
        "price_change_percent": 2.6,
        "avg_price_per_sqm_czk": 127800,
        "price_category": "medium"
    }
}


def get_info(district_no: int) -> DistrictInfo:
    """Get real estate information for a specific Prague district."""
    district_key = f"Prague {district_no}"
    district_data = prague_real_estate[district_key]
    
    return DistrictInfo(
        district_no=district_no,
        avg_price_per_sqm_czk=district_data["avg_price_per_sqm_czk"],
        price_change_percent=district_data["price_change_percent"],
        price_category=district_data["price_category"]
    )
