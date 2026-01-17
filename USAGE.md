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
      "url": "https://www.sreality.cz/detail/pronajem/byt/4+1/praha-stare-mesto-martinska/3766952780"
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

```json
{
  "url": "https://www.sreality.cz/detail/pronajem/byt/4+1/praha-stare-mesto-martinska/3766952780",
  "title": "Pronájem bytu 4+1 180 m² Martinská, Praha - Staré Město",
  "description": "Klasický, prostorný, 3 ložnicový, nezařízený byt se 2 koupelnami k pronájmu...",
  "price": "55 000 Kč/měsíc",
  "location": "Praha - Staré Město",
  "attributes": {
    "Plocha": "Užitná plocha 180 m²",
    "Energetická náročnost": "Mimořádně nehospodárná",
    "Stavba": "Smíšená, Ve velmi dobrém stavu, 2. podlaží z 6"
  },
  "seller": {
    "phone": "+420 606 682 820",
    "email": "info@primeproperty.cz"
  }
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

2. **Consent page blocking**
   - This is expected due to anti-bot protection
   - Try using Apify Proxy (set `useApifyProxy: true`)
   - Add delays between requests

3. **Missing description**
   - Some listings may have minimal descriptions
   - Check the `attributes` field for additional details

## Tips for Best Results

- Use residential proxies for higher success rates
- Add random delays between requests (0.5-2 seconds)
- Process listings in small batches
- Monitor the Apify Console logs for issues

