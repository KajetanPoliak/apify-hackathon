# Bezrealitky.cz Property Listing Scraper with LLM Analysis

This Apify Actor scrapes detailed property information from Bezrealitky.cz listing pages, processes it with LLM-powered analysis, and performs consistency checks to identify discrepancies between property descriptions and structured data.

## Features

### Core Scraping Features

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
  - **Kebab Index**: Normalized metric for district amenities/restaurant quality (higher = better)
  - Administrative district mapping (Prague 1-22)

### LLM-Powered Analysis (Optional)

- **Structured Data Conversion**: Converts scraped data into standardized `ListingInput` format using LLM with structured outputs
  - Extracts and normalizes property attributes (bedrooms, bathrooms, square meters, price, etc.)
  - Includes district statistics (kebab index, crime rates) for fact-checking
  - Validates data constraints and formats

- **Consistency Checking**: Automated fact-checking to identify discrepancies:
  - **Mandatory Checks**: 
    - Amenities claims vs. kebab index (verifies "good restaurants/amenities" claims)
    - Safety/criminality claims vs. crime statistics (verifies "calm/safe area" claims)
  - Compares property descriptions against structured data
  - Identifies inconsistencies with severity levels (critical, medium, low)
  - Generates detailed findings with explanations

- **Multiple LLM Models**: Supports various models via OpenRouter:
  - Google Gemini 3 Flash Preview (default, used when no model specified)
  - GPT-5 Mini
  - GPT-4o
  - Gemini 2.0 Flash (Experimental)
  - Gemini 1.5 Pro/Flash
  - Gemini Pro
  - OpenRouter Auto (auto-selects model, but defaults to Gemini 3 Flash Preview)

- **Configurable Temperature**: Control LLM determinism (default: 0.01 for consistent results)

### Technical Features

- **Robust Extraction**: Multiple fallback strategies ensure data quality
- **JavaScript Rendering**: Uses Playwright crawler to handle dynamic content
- **Structured Output**: Pydantic models ensure data consistency
- **Validation & Logging**: Comprehensive validation with clear status reporting
- **Error Handling**: Graceful fallbacks with mock data when LLM processing fails

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
  },
  "useLLM": true,
  "llmModel": "google/gemini-3-flash-preview",
  "llmTemperature": 0.01,
  "skipScraping": false,
  "outputMockInconsistencies": false
}
```

### Input Parameters

#### Required
- **startUrls** (required): Array of Bezrealitky.cz detail page URLs to scrape

#### Optional - Scraping
- **maxRequestsPerCrawl** (optional): Maximum number of pages to scrape (default: 100, min: 1, max: 10000)
- **proxyConfiguration** (optional): Proxy settings for scraping (recommended for production)
- **skipScraping** (optional): Skip web scraping and only test LLM functionality with sample data (default: false)

#### Optional - LLM Configuration
- **useLLM** (optional): Enable LLM analysis of scraped property data via OpenRouter (default: false)
  - Requires `APIFY_TOKEN` environment variable with valid Apify token
  - OpenRouter API key should be configured in environment
- **llmModel** (optional): Model to use for LLM requests
  - Default behavior: If not specified or set to "openrouter/auto", uses "google/gemini-3-flash-preview"
  - Available options in input schema: GPT-5 Mini, GPT-4o, Gemini 2.0 Flash (Experimental), Gemini 1.5 Pro/Flash, Gemini Pro, OpenRouter Auto
  - Note: Any valid OpenRouter model identifier can be used, but the code defaults to "google/gemini-3-flash-preview" when not specified
- **llmTemperature** (optional): Temperature for LLM responses (default: 0.01, range: 0.0-2.0)
  - Lower values = more deterministic, higher values = more creative

#### Optional - Testing
- **outputMockInconsistencies** (optional): Generate and output mock inconsistency check results for testing (default: false)

## Output

The actor stores multiple types of data in the default dataset:

### 1. Scraped Property Data

Each scraped property is stored as a comprehensive JSON object:

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
    "street": "Hostýnská",
    "pragueAdminDistrict": "Prague 10"
  },
  "districtStats": {
    "avgPricePerSqmCzk": 127800,
    "priceChangePercent": 2.6,
    "priceCategory": "medium",
    "crimeStats": {
      "violentCrimes": 0.19,
      "burglaries": 0.50,
      "fires": 0.34
    },
    "kebabIndex": 0.40
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
  "scrapedAt": "https://www.bezrealitky.cz/nemovitosti-byty-domy/...",
  "consistencyCheck": {
    "listing_id": "PRG-E76C0DD8406F",
    "total_inconsistencies": 1,
    "is_consistent": false
  }
}
```

### 2. ListingInput (Structured Output) - When LLM is enabled

When `useLLM: true`, each property is also converted to a standardized `ListingInput` format:

```json
{
  "type": "listing_input",
  "listing_id": "PRG-E76C0DD8406F",
  "listing_url": "https://www.bezrealitky.cz/...",
  "property_address": "Hostýnská, Praha - Strašnice",
  "city": "Praha",
  "state": "Praha",
  "zip_code": "",
  "bedrooms": 3,
  "bathrooms": 1.0,
  "square_meters": 57,
  "list_price": 8499000.0,
  "description": "Nabízím k prodeji krásný byt...",
  "district_kebab_index": 0.40,
  "district_violent_crimes_rate": 0.19,
  "district_burglaries_rate": 0.50,
  "data": { /* full ListingInput object */ }
}
```

### 3. ConsistencyCheckResult - When LLM is enabled

For each property, a consistency check result is generated:

```json
{
  "listing_id": "PRG-E76C0DD8406F",
  "property_address": "Hostýnská, Praha - Strašnice",
  "checked_at": "2026-01-17T16:54:34.464275",
  "total_inconsistencies": 1,
  "is_consistent": false,
  "findings": [
    {
      "field_name": "amenities",
      "description_says": "All civic amenities can be found in the vicinity",
      "listing_data_says": "Kebab index: 0.40 (medium)",
      "severity": "medium",
      "explanation": "Description claims good amenities but kebab index is only medium (0.40)"
    }
  ],
  "summary": "Found 1 inconsistency: amenities claim vs. kebab index"
}
```

### 4. Completion Summary

At the end of processing, a summary is pushed:

```json
{
  "type": "completion_summary",
  "status": "success",
  "completed_at": "2026-01-17T16:54:34.464275",
  "total_urls_processed": 1,
  "llm_model_used": "google/gemini-3-flash-preview",
  "llm_temperature": 0.01,
  "max_requests_per_crawl": 10,
  "inconsistency_analysis": {
    "total_properties_processed": 1,
    "total_inconsistencies_found": 1,
    "properties_with_inconsistencies": 1,
    "properties_consistent": 0,
    "inconsistency_checks_failed": 0,
    "average_inconsistencies_per_property": 1.0
  },
  "message": "Successfully completed processing 1 URL(s). Found 1 total inconsistencies across 1 properties."
}
```

## Usage

### Running Locally

1. Install dependencies:
```bash
# Using uv (recommended)
uv sync

# Or using pip
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

2. Set up environment variables (for LLM features):
```bash
export APIFY_TOKEN="your-apify-token"
export OPENROUTER_API_KEY="your-openrouter-api-key"  # Optional, can use Apify secrets
```

3. Configure input in `storage/key_value_stores/default/INPUT.json`:
```json
{
  "startUrls": [
    {
      "url": "https://www.bezrealitky.cz/nemovitosti-byty-domy/974793-nabidka-prodej-bytu-hostynska-praha"
    }
  ],
  "useLLM": true,
  "llmModel": "google/gemini-3-flash-preview",
  "llmTemperature": 0.01
}
```

4. Run the actor:
```bash
# Using uv
uv run python -m src

# Or directly
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

- **LLM Requirements**: LLM features require:
  - Valid `APIFY_TOKEN` environment variable
  - OpenRouter API key configured (via environment or Apify secrets)
  - Internet connectivity for API calls
  - May incur costs based on model usage

- **District Statistics**: Currently only available for Prague properties. Other cities will not have district statistics enrichment.

- **Consistency Checks**: Mandatory fact-checks (amenities, safety) are prioritized, but other consistency checks depend on LLM model capabilities and may vary in quality.

## Technical Details

- **Crawler**: PlaywrightCrawler (handles JavaScript-rendered content)
- **Browser**: Chromium (headless mode)
- **Language**: Python 3.10+
- **Dependencies**: 
  - Apify SDK
  - Crawlee
  - Playwright
  - Pydantic (data validation)
  - OpenAI SDK (for OpenRouter LLM integration)
- **LLM Integration**: OpenRouter API with structured outputs (JSON Schema)
- **Data Models**: Pydantic models for type safety and validation

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
- **Kebab Index**: Normalized metric (0.0-1.0) for district amenities/restaurant quality
  - Higher values indicate better amenities, restaurants, and neighborhood quality
  - Used for fact-checking amenities claims in property descriptions
- **Crime Statistics (2025)**:
  - **Violent Crimes Rate**: Normalized rate (higher = worse)
  - **Burglaries Rate**: Normalized rate (higher = worse)
  - **Fires Rate**: Normalized rate (higher = worse)
  - Used for fact-checking safety/calm claims in property descriptions

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
