# Quick Start Guide

## Setup

1. **Install Dependencies**
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

2. **Configure Input**

Edit `storage/key_value_stores/default/INPUT.json`:

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
  "maxRequestsPerCrawl": 10
}
```

3. **Run Locally**
```bash
source .venv/bin/activate
python -m src
```

4. **View Results**

Results are saved in `storage/datasets/default/000000001.json`

## Sample Output

The scraper now extracts 30+ data points for comprehensive property analysis:

```json
{
  "url": "https://www.bezrealitky.cz/nemovitosti-byty-domy/974793-nabidka-prodej-bytu-hostynska-praha",
  "propertyId": "974793",
  "title": "Prodej bytu 3+kk 57 m², Hostýnská, Praha - Strašnice",
  "category": "Prodej",
  "description": "Nabízím k prodeji krásný byt o dispozici 3kk po rekonstrukci...",
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
    "energyRating": "C - Úsporná",
    "pricePerM2": "149 105 Kč / m2"
  },
  "features": ["Částečně vybaveno", "Sklep 2 m²", "Lodžie 3 m²"],
  "amenities": ["Sklep 2 m²", "Lodžie 3 m²", "Internet"],
  "images": ["https://img.bezrealitky.cz/..."],
  "seller": {
    "type": "owner",
    "note": "Prodává přímo majitel - bez provize"
  },
  "breadcrumbs": ["Domů", "Prodej", "Byt", "Praha"]
}
```

## Deploying to Apify

```bash
# Login to Apify (first time only)
apify login

# Deploy the actor
apify push
```

## Troubleshooting

### Common Issues

1. **"Module not found" errors**
   - Make sure you've activated the virtual environment: `source .venv/bin/activate`
   - Reinstall dependencies: `pip install -r requirements.txt`

2. **Missing description**
   - Some listings may have minimal descriptions
   - Check the `attributes` field for additional details

3. **Page loading issues**
   - Try using Apify Proxy (set `useApifyProxy: true`)
   - Increase timeout values if needed

## Tips for Best Results

- Use residential proxies for higher success rates
- Add random delays between requests (0.5-2 seconds)
- Process listings in small batches
- Monitor the Apify Console logs for issues

