import os
from dotenv import load_dotenv
from apify_client import ApifyClient

# Load environment variables from .env file
load_dotenv()

# Initialize the ApifyClient with your Apify API token from .env
client = ApifyClient(os.getenv("APIFY_TOKEN"))

# e. g.:  print(f"Kebab index: {calculate_kebab_index("Strašnice, Praha, Czech Republic")}")
def calculate_kebab_index(address: str, max_places: int = 50, min_rating: float = 4.5, min_reviews: int = 100) -> int:
    """
    Calculate the kebab index for a given address.
    
    The kebab index is the number of high-quality kebab restaurants in the area:
    - Rating > min_rating (default: 4.5)
    - Reviews > min_reviews (default: 100)
    
    Args:
        address: Location to search (e.g., "Strašnice, Praha, Czech Republic")
        max_places: Maximum number of places to scrape (default: 50)
        min_rating: Minimum rating threshold (default: 4.5)
        min_reviews: Minimum number of reviews (default: 100)
    
    Returns:
        dict with:
            - kebab_index: Number of high-quality kebab places
            - total_places: Total kebab places found
            - high_quality_places: List of places that meet the criteria
            - all_places: All places found
    """
    print(f"🚀 Calculating kebab index for: {address}")
    print(f"   Criteria: Rating > {min_rating} AND Reviews > {min_reviews}")
    
    # Prepare the Actor input
    run_input = {
        "searchStringsArray": ["kebab"],
        "locationQuery": address,
        "maxCrawledPlacesPerSearch": max_places,
        "language": "cs",
        "scrapeSocialMediaProfiles": {
            "facebooks": False,
            "instagrams": False,
            "youtubes": False,
            "tiktoks": False,
            "twitters": False,
        },
        "maximumLeadsEnrichmentRecords": 0,
        "maxImages": 0,
    }
    
    # Run the Actor and wait for it to finish
    run = client.actor("compass/crawler-google-places").call(run_input=run_input)
    
    # Fetch and collect Actor results
    print(f"💾 Dataset: https://console.apify.com/storage/datasets/{run['defaultDatasetId']}")
    print("📥 Fetching results...")
    
    # Collect all results into a list
    all_places = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        all_places.append(item)
    
    print(f"✅ Found {len(all_places)} total kebab places")
    
    # Filter high-quality places
    high_quality_places = []
    for place in all_places:
        rating = place.get('totalScore')
        reviews = place.get('reviewsCount', 0)
        
        # Check if place meets criteria
        if rating is not None and rating > min_rating and reviews > min_reviews:
            high_quality_places.append(place)
    
    kebab_index = len(high_quality_places)
    
    print(f"🎯 Kebab index for {address}: {kebab_index}")
    print(f"   ({kebab_index} places with rating > {min_rating} and > {min_reviews} reviews)")
    print()
    
    return kebab_index


def calculate_kebab_indices_for_prague_districts():
    """
    Calculate kebab indices for Prague districts 1-10.
    
    Returns:
        dict: District number -> kebab index mapping
    """
    print("=" * 80)
    print("🍢 CALCULATING KEBAB INDICES FOR PRAGUE DISTRICTS 1-10")
    print("=" * 80)
    print()
    
    district_kebab_indices = {}
    
    # Prague districts 1-10 with their main neighborhoods
    districts = {
        1: "Praha 1, Czech Republic",
        2: "Praha 2, Czech Republic",
        3: "Praha 3, Czech Republic",
        4: "Praha 4, Czech Republic",
        5: "Praha 5, Czech Republic",
        6: "Praha 6, Czech Republic",
        7: "Praha 7, Czech Republic",
        8: "Praha 8, Czech Republic",
        9: "Praha 9, Czech Republic",
        10: "Praha 10, Czech Republic",
    }
    
    for district_no, address in districts.items():
        print(f"📍 Processing District {district_no}...")
        try:
            kebab_index = calculate_kebab_index(address)
            district_kebab_indices[district_no] = kebab_index
        except Exception as e:
            print(f"❌ Error calculating kebab index for District {district_no}: {e}")
            district_kebab_indices[district_no] = 0
        print("-" * 80)
    
    print()
    print("=" * 80)
    print("🎉 KEBAB INDEX CALCULATION COMPLETE")
    print("=" * 80)
    print()
    print("Results:")
    for district_no, kebab_index in sorted(district_kebab_indices.items()):
        print(f"  Prague {district_no}: {kebab_index} high-quality kebab places")
    print()
    
    return district_kebab_indices


if __name__ == "__main__":
    # Calculate kebab indices for all Prague districts
    kebab_indices = calculate_kebab_indices_for_prague_districts()
    
    # Print Python code to update prague_real_estate_data.py
    print()
    print("=" * 80)
    print("📝 CODE TO ADD TO prague_real_estate_data.py")
    print("=" * 80)
    print()
    print("Add 'kebab_index' field to each district:")
    print()
    for district_no, kebab_index in sorted(kebab_indices.items()):
        print(f'    "Prague {district_no}": {{')
        print(f'        ...')
        print(f'        "kebab_index": {kebab_index},')
        print(f'        ...')
        print(f'    }},')
    print()

