# Sreality.cz Property Listing Scraper

This Apify Actor scrapes detailed property information from Sreality.cz listing pages. It extracts comprehensive data including property descriptions, prices, locations, attributes, and seller information.

## Features

- **Comprehensive Data Extraction**: Scrapes property title, description, price, location, attributes, and seller details
- **JavaScript Rendering**: Uses Playwright crawler to handle dynamic content
- **Cookie Consent Handling**: Automatically attempts to handle Seznam.cz consent dialogs
- **Structured Output**: Returns well-formatted JSON data with all property details

## Input

The actor accepts the following input parameters:

```json
{
  "startUrls": [
    {
      "url": "https://www.sreality.cz/detail/pronajem/byt/4+1/praha-stare-mesto-martinska/3766952780"
    }
  ],
  "maxRequestsPerCrawl": 100,
  "proxyConfiguration": {
    "useApifyProxy": false
  }
}
```

### Input Parameters

- **startUrls** (required): Array of Sreality.cz detail page URLs to scrape
- **maxRequestsPerCrawl** (optional): Maximum number of pages to scrape (default: 100)
- **proxyConfiguration** (optional): Proxy settings for bypassing anti-bot protection

## Output

The actor stores data in the default dataset. Each item contains:

```json
{
  "url": "https://www.sreality.cz/detail/...",
  "title": "Pronájem bytu 4+1 180 m² Martinská, Praha - Staré Město",
  "description": "Klasický, prostorný, 3 ložnicový...",
  "price": "55 000 Kč/měsíc",
  "location": "Praha - Staré Město",
  "attributes": {
    "Cena": "55 000 Kč/měsíc",
    "Plocha": "Užitná plocha 180 m²",
    "Energetická náročnost": "Mimořádně nehospodárná",
    "Stavba": "Smíšená, Ve velmi dobrém stavu, 2. podlaží z 6",
    ...
  },
  "seller": {
    "name": "Marcela Skalníková",
    "phone": "+420 606 682 820",
    "email": "info@primeproperty.cz"
  },
  "scrapedAt": "https://www.sreality.cz/detail/..."
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

- **Anti-Bot Protection**: Sreality.cz uses sophisticated bot detection. For production use, it's recommended to:
  - Use Apify Proxy with residential IPs
  - Add random delays between requests
  - Rotate user agents
  
- **Cookie Consent**: The Seznam.cz consent dialog handling may occasionally fail. The actor includes multiple strategies to handle it, but success rates may vary.

## Technical Details

- **Crawler**: PlaywrightCrawler (handles JavaScript-rendered content)
- **Browser**: Chromium (headless mode)
- **Language**: Python 3.10+
- **Dependencies**: Apify SDK, Crawlee, Playwright

## Data Extracted

### Property Information
- Title and full description
- Price (monthly rent or sale price)
- Location (district, street)
- Property type and size
- Energy efficiency rating
- Building condition and floor
- Amenities and features

### Location Context
- Nearby schools, shops, restaurants
- Public transport connections
- Distance to key landmarks

### Seller Information
- Agent/Company name
- Contact phone
- Contact email
- Agency details

## Example URLs

Try these example Sreality.cz listings:

```
https://www.sreality.cz/detail/pronajem/byt/4+1/praha-stare-mesto-martinska/3766952780
https://www.sreality.cz/detail/prodej/dum/rodinny/velvary-velvary-tyrsova/2882372428
https://www.sreality.cz/detail/prodej/byt/4+kk/praha-smichov-vltavska/3683189580
```

## Support

For issues or questions:
- Check the Apify Console logs for detailed error messages
- Review the actor's run history for troubleshooting
- Ensure you're using valid Sreality.cz detail page URLs

## License

This actor is provided as-is for educational and personal use. Always respect the website's Terms of Service and robots.txt when scraping.
