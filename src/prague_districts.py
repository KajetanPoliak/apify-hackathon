"""Prague districts mapping utility.

Maps Prague neighborhoods (cadastral areas) to their administrative districts (Prague 1-22).
"""

import json
from pathlib import Path
from typing import Optional


# Load the mapping from JSON file
_MAPPING_FILE = Path(__file__).parent.parent / "prague_districts_mapping.json"

with open(_MAPPING_FILE, 'r', encoding='utf-8') as f:
    PRAGUE_DISTRICTS_MAPPING = json.load(f)


# Create reverse mapping: neighborhood -> administrative district
DISTRICT_TO_ADMIN_NUMBER: dict[str, str] = {}
for admin_district, neighborhoods in PRAGUE_DISTRICTS_MAPPING.items():
    for neighborhood in neighborhoods:
        # Store in lowercase for case-insensitive lookup
        DISTRICT_TO_ADMIN_NUMBER[neighborhood.lower()] = admin_district


def get_prague_admin_district(district_name: str) -> Optional[str]:
    """Get the Prague administrative district (Prague 1-22) for a given neighborhood.
    
    Args:
        district_name: Name of the Prague neighborhood/district (e.g., "Karlín", "Vinohrady")
    
    Returns:
        Administrative district name (e.g., "Prague 8") or None if not found
    
    Examples:
        >>> get_prague_admin_district("Karlín")
        'Prague 8'
        >>> get_prague_admin_district("Vinohrady")
        'Prague 2'
        >>> get_prague_admin_district("Strašnice")
        'Prague 10'
    """
    if not district_name:
        return None
    
    # Try exact match (case-insensitive)
    return DISTRICT_TO_ADMIN_NUMBER.get(district_name.lower())


def get_neighborhoods_in_admin_district(admin_district: str) -> list[str]:
    """Get all neighborhoods in a given administrative district.
    
    Args:
        admin_district: Administrative district name (e.g., "Prague 8")
    
    Returns:
        List of neighborhood names in that district
    
    Examples:
        >>> get_neighborhoods_in_admin_district("Prague 8")
        ['Karlín', 'Libeň', 'Kobylisy', 'Bohnice', ...]
    """
    return PRAGUE_DISTRICTS_MAPPING.get(admin_district, [])


def get_all_admin_districts() -> list[str]:
    """Get list of all Prague administrative districts.
    
    Returns:
        List of administrative district names (Prague 1 through Prague 22)
    """
    return sorted(PRAGUE_DISTRICTS_MAPPING.keys(), key=lambda x: int(x.split()[1]))


def get_all_neighborhoods() -> list[str]:
    """Get list of all Prague neighborhoods.
    
    Returns:
        List of all neighborhood names
    """
    all_neighborhoods = []
    for neighborhoods in PRAGUE_DISTRICTS_MAPPING.values():
        all_neighborhoods.extend(neighborhoods)
    # Remove duplicates (some neighborhoods span multiple admin districts)
    return sorted(set(all_neighborhoods))


# Example usage and statistics
if __name__ == "__main__":
    print("Prague Districts Mapping Utility")
    print("=" * 60)
    print(f"Total administrative districts: {len(get_all_admin_districts())}")
    print(f"Total unique neighborhoods: {len(get_all_neighborhoods())}")
    print()
    
    # Show some examples
    examples = [
        ("Karlín", "Prague 8"),
        ("Vinohrady", "Prague 2"),
        ("Strašnice", "Prague 10"),
        ("Malešice", "Prague 10"),
        ("Smíchov", "Prague 5"),
        ("Žižkov", "Prague 3"),
    ]
    
    print("Example lookups:")
    print("-" * 60)
    for neighborhood, expected in examples:
        result = get_prague_admin_district(neighborhood)
        status = "✓" if result == expected else "✗"
        print(f"{status} {neighborhood:20} -> {result}")
    print()
    
    # Show district breakdown
    print("Neighborhoods per administrative district:")
    print("-" * 60)
    for admin_district in get_all_admin_districts():
        neighborhoods = get_neighborhoods_in_admin_district(admin_district)
        print(f"{admin_district:12} : {len(neighborhoods):2} neighborhoods")

