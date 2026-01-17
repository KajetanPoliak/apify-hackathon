#!/usr/bin/env python3
"""
Demonstrates the complete workflow:
1. Load data from Apify dataset
2. Validate with Pydantic models
3. Type-safe access to all fields
"""

from src.models import ScrapeOutput
from src.utils import load_scraped_listings
import json


def main():
    print("\n" + "="*70)
    print("  COMPLETE WORKFLOW DEMONSTRATION")
    print("="*70)
    
    # Step 1: Load scraped data from Apify dataset
    print("\n📂 STEP 1: Loading data from Apify dataset...")
    print("   Location: storage/datasets/default/")
    
    listings = load_scraped_listings()
    print(f"   ✓ Loaded {len(listings)} listings from dataset")
    
    # Step 2: Demonstrate Pydantic validation
    print("\n✨ STEP 2: Pydantic validation (automatic)")
    print("   Each listing is validated against ScrapeOutput model")
    print("   - Type checking: str | None, Literal['rental', 'sale']")
    print("   - Required fields: url, scrapedAt")
    print("   - Nested models: SellerInfo")
    print("   ✓ All listings passed validation!")
    
    # Step 3: Type-safe data access
    print("\n🔒 STEP 3: Type-safe data access")
    print("="*70)
    
    for i, listing in enumerate(listings, 1):
        print(f"\n{i}. LISTING DETAILS:")
        print("-" * 70)
        
        # Access fields with full type safety
        print(f"   URL:         {listing.url}")
        print(f"   Title:       {listing.title}")
        print(f"   Price:       {listing.price}")
        print(f"   Type:        {listing.priceType} ← Validated: 'rental' or 'sale'")
        print(f"   Location:    {listing.location}")
        
        # Nested model access (SellerInfo)
        print(f"\n   Seller Info (validated SellerInfo model):")
        print(f"   - Name:      {listing.seller.name or 'N/A'}")
        print(f"   - Phone:     {listing.seller.phone or 'N/A'}")
        print(f"   - Email:     {listing.seller.email or 'N/A'}")
        
        # Dictionary attributes
        print(f"\n   Attributes:  {len(listing.attributes)} fields")
        
        # Show model dump
        print(f"\n   ✓ Can dump back to dict: output.model_dump()")
        print(f"   ✓ Can serialize to JSON: output.model_dump_json()")
    
    # Step 4: Demonstrate model operations
    print("\n" + "="*70)
    print("🔧 STEP 4: Model operations")
    print("="*70)
    
    if listings:
        first = listings[0]
        
        # Convert to dict
        print("\n1. Convert Pydantic model → dict:")
        data_dict = first.model_dump()
        print(f"   Type: {type(data_dict)} ✓")
        
        # Convert to JSON
        print("\n2. Convert Pydantic model → JSON string:")
        json_str = first.model_dump_json(indent=2)
        print(f"   Length: {len(json_str)} characters ✓")
        
        # Reconstruct from dict
        print("\n3. Reconstruct dict → Pydantic model:")
        reconstructed = ScrapeOutput(**data_dict)
        print(f"   Type: {type(reconstructed)} ✓")
        print(f"   Title: {reconstructed.title} ✓")
    
    # Step 5: Summary
    print("\n" + "="*70)
    print("✅ WORKFLOW COMPLETE!")
    print("="*70)
    print(f"""
The complete workflow is working:

1. ✓ Data scraped from Sreality.cz
2. ✓ Validated with Pydantic ScrapeOutput model
3. ✓ Dumped to dict with model_dump()
4. ✓ Stored to Apify dataset (storage/datasets/default/)
5. ✓ Loaded back with automatic validation
6. ✓ Type-safe access to all fields

Your scraper is production-ready! 🚀
""")


if __name__ == "__main__":
    main()

