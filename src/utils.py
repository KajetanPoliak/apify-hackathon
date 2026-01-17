"""Utility functions for working with scraped data"""

import hashlib
import json
from pathlib import Path
from typing import List

from .models import ScrapeOutput


def generate_listing_id_from_url(url: str) -> str:
    """Generate a standardized listing ID from a URL.
    
    Args:
        url: Property listing URL
    
    Returns:
        Listing ID in format "PRG-XXXXXXXXXXXX" (12 uppercase hex characters)
    """
    listing_id = hashlib.md5(url.encode()).hexdigest()[:12].upper()
    return f"PRG-{listing_id}"


def load_scraped_listings(dataset_dir: str = "storage/datasets/default") -> List[ScrapeOutput]:
    """
    Load all scraped listings from the dataset directory and validate them with Pydantic.
    
    Args:
        dataset_dir: Path to the dataset directory
        
    Returns:
        List of validated ScrapeOutput objects
    """
    dataset_path = Path(dataset_dir)
    listings = []
    
    # Find all JSON files (excluding metadata)
    json_files = sorted([f for f in dataset_path.glob("*.json") if not f.name.startswith("__")])
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                listing = ScrapeOutput(**data)
                listings.append(listing)
        except Exception as e:
            print(f"Error loading {json_file.name}: {e}")
            continue
    
    return listings
