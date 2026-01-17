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
    
    return kebab_index
