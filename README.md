# Bezrealitky.cz Property Listing Scraper

This Apify Actor scrapes detailed property information from Bezrealitky.cz listing pages. It extracts comprehensive data including property descriptions, prices, locations, attributes, and seller information.

## Features

- **Guaranteed Critical Fields**: Always extracts 5 essential fields with multiple fallback strategies:
  - ✅ **City** (Praha, Brno, Ostrava, etc.)
  - ✅ **District** (Karlín, Malešice, Strašnice, etc.)
  - ✅ **Street** (Sokolovská, Počernická, Hostýnská, etc.)
  - ✅ **Area** (57 m², 60 m², etc.)
  - ✅ **Disposition** (3+kk, 2+1, 4+1, etc.)
  
- **Comprehensive Data Extraction**: Scrapes 30+ data points including:
  - Property details (ID, title, **full multi-paragraph descriptions** in Czech & English, category)
  - Pricing (total price, price per m²)
  - Location (hierarchical structure with city, district, street)
  - Property specifications (area, disposition, floor, building type, condition, energy rating)
  - Amenities (cellar, loggia, parking, internet, etc.)
  - Images (all property photos)
  - Seller information (owner vs. agent, contact details)
  - Breadcrumb navigation for categorization

- **Automatic Data Enrichment**: Prague properties automatically enhanced with:
  - Real estate market data (avg price per m², price trends, Q3 2024)
  - Crime statistics (violent crimes, burglaries, fires, 2025 data)
  - Administrative district mapping (Prague 1-22)
  
- **Robust Extraction**: Multiple fallback strategies ensure data quality
- **JavaScript Rendering**: Uses Playwright crawler to handle dynamic content
- **Structured Output**: Pydantic models ensure data consistency
- **Validation & Logging**: Comprehensive validation with clear status reporting

## Input

The actor accepts the following input parameters:

```json
{
  "startUrls": [
    {
      "url": "https://www.bezrealitky.cz/nemovitosti-byty-domy/974793-nabidka-prodej-bytu-hostynska-praha"
    },
    {
      "url": "https://www.bezrealitky.cz/nemovitosti-byty-domy/981201-nabidka-prodej-bytu-pocernicka-praha"
    }
  ],
  "maxRequestsPerCrawl": 100,
  "proxyConfiguration": {
    "useApifyProxy": false
  }
}
```

### Input Parameters

- **startUrls** (required): Array of Bezrealitky.cz detail page URLs to scrape
- **maxRequestsPerCrawl** (optional): Maximum number of pages to scrape (default: 100)
- **proxyConfiguration** (optional): Proxy settings if needed

## Output

The actor stores data in the default dataset. Each item contains comprehensive property information:

```json
{
  "url": "https://www.bezrealitky.cz/nemovitosti-byty-domy/974793...",
  "propertyId": "974793",
  "title": "Prodej bytu 3+kk 57 m², Hostýnská, Praha - Strašnice",
  "category": "Prodej",
  "description": "Nabízím k prodeji krásný byt o dispozici 3kk...",
  "descriptionEnglish": "I am offering for sale a beautiful 3-room apartment...",
  "price": "8 499 000 Kč",
  "priceType": "sale",
  "location": {
    "full": "Praha - Strašnice",
    "city": "Praha",
    "district": "Strašnice",
    "street": "Hostýnská"
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
    "availableFrom": "20. 12. 2025",
    "pricePerM2": "149 105 Kč / m2"
  },
  "features": ["Částečně vybaveno", "Sklep 2 m²", "Lodžie 3 m²"],
  "amenities": ["Sklep 2 m²", "Lodžie 3 m²", "Internet"],
  "images": ["https://img.bezrealitky.cz/..."],
  "seller": {
    "type": "owner",
    "note": "Prodává přímo majitel - bez provize"
  },
  "breadcrumbs": ["Domů", "Prodej", "Byt", "Praha"],
  "scrapedAt": "https://www.bezrealitky.cz/nemovitosti-byty-domy/..."
}
```

## Usage

### Running Locally

1. Install dependencies:
```bash
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

2. Configure input in `storage/key_value_stores/default/INPUT.json`

3. Run the actor:
```bash
python -m src
```

### Running on Apify Platform

1. Deploy the actor:
```bash
apify push
```

2. Run from Apify Console with your desired input

## Known Limitations

- **Rate Limiting**: Be respectful with request rates to avoid overloading the website:
  - Add reasonable delays between requests
  - Process listings in reasonable batches
  
- **Dynamic Content**: Some content may be loaded dynamically, but the actor handles this with Playwright.

## Technical Details

- **Crawler**: PlaywrightCrawler (handles JavaScript-rendered content)
- **Browser**: Chromium (headless mode)
- **Language**: Python 3.10+
- **Dependencies**: Apify SDK, Crawlee, Playwright

## Data Extracted

### Core Information
- **Property ID**: Unique listing identifier
- **Title**: Full property title
- **Category**: Prodej (Sale) or Pronájem (Rental)
- **Description**: Complete multi-paragraph Czech description including property details, neighborhood info, room layouts, costs, and amenities
- **Description (English)**: Full English translation if available (all paragraphs combined)
- **URL**: Original listing URL

### Pricing
- **Total Price**: Sale price or monthly rent
- **Price Type**: "sale" or "rental"
- **Price per m²**: Unit price

### Location Details
- **Full Location**: Complete location string
- **City**: Prague, Brno, etc.
- **District**: Specific district/neighborhood (e.g., Karlín, Strašnice, Malešice)
- **Street**: Street name
- **Prague Administrative District**: Automatically mapped (e.g., Prague 8, Prague 10) for Prague properties
- **Breadcrumbs**: Navigation path for context

### District Statistics (Prague Only)
Automatically enriched with real-world data for Prague properties:
- **Average Price per m²**: Market data from Q3 2024 Prague Real Index
- **Price Change %**: Year-over-year price trend
- **Price Category**: premium, high, or medium tier
- **Crime Statistics (2025)**:
  - Violent crimes
  - Burglaries  
  - Fires

### Property Specifications
- **Area**: Usable area in m²
- **Disposition**: Layout (1+1, 2+kk, 3+kk, etc.)
- **Floor**: Which floor and total floors
- **Building Type**: Panel, Brick, etc.
- **Condition**: Very good, Good, etc.
- **Ownership**: Personal, Cooperative, etc.
- **Furnished**: Yes, Partially, No
- **Energy Rating**: A-G energy efficiency
- **Available From**: Move-in date

### Amenities & Features
- **Features**: Key highlights (furnished, cellar, loggia)
- **Amenities**: Detailed list with sizes
  - Cellar (+ size if specified)
  - Loggia/Balcony (+ size)
  - Terrace, Garden
  - Parking, Garage
  - Elevator
  - Internet
  - Pool

### Visual Content
- **Images**: Array of all property photo URLs

### Seller Information
- **Type**: Owner or Agent
- **Note**: Special notes (e.g., "no commission")
- **Phone**: Contact phone number (if available)
- **Email**: Contact email (if available)

### Metadata
- **Attributes**: Complete raw attributes dictionary
- **Scraped At**: Actual URL after any redirects
- **Timestamp**: When data was scraped

## Example URLs

Try these example Bezrealitky.cz listings:

```
https://www.bezrealitky.cz/nemovitosti-byty-domy/974793-nabidka-prodej-bytu-hostynska-praha
https://www.bezrealitky.cz/nemovitosti-byty-domy/981201-nabidka-prodej-bytu-pocernicka-praha
https://www.bezrealitky.cz/nemovitosti-byty-domy/981586-nabidka-prodej-bytu-vratislavska-praha
```

## Support

For issues or questions:
- Check the Apify Console logs for detailed error messages
- Review the actor's run history for troubleshooting
- Ensure you're using valid Bezrealitky.cz detail page URLs

## License

This actor is provided as-is for educational and personal use. Always respect the website's Terms of Service and robots.txt when scraping.
