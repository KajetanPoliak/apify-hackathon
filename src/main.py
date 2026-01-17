"""Bezrealitky.cz Detail Page Scraper.

This Actor scrapes detailed information from Bezrealitky.cz property listing pages.
"""

from __future__ import annotations

import json
import re
from typing import Any

from apify import Actor
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext


def clean_text(text: str | None) -> str | None:
    """Clean and normalize text by removing extra whitespace."""
    if not text:
        return None
    return re.sub(r'\s+', ' ', text.strip())


def extract_property_details(soup: Any) -> dict[str, Any]:
    """Extract property details from Bezrealitky.cz listing page."""
    details = {}
    
    # Bezrealitky uses table format for property parameters
    # Look for key-value pairs in table rows
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) == 2:
            key = clean_text(cells[0].get_text())
            value = clean_text(cells[1].get_text())
            if key and value:
                details[key] = value
    
    return details


async def call_openrouter_llm(
    messages: list[dict[str, str]],
    model: str = "openrouter/auto",
    temperature: float = 0.7,
) -> dict[str, Any] | None:
    """Call OpenRouter actor to make LLM requests.
    
    Uses OpenAI client with APIFY_TOKEN for authentication.
    Works with both 'apify run' and direct Python execution.
    
    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: Model identifier (e.g., 'openrouter/auto' or 'google/gemini-2.0-flash-exp')
        temperature: Sampling temperature (0.0-2.0)
    
    Returns:
        Response dict with 'choices' containing the LLM response, or None on error
    """
    try:
        # Get APIFY_TOKEN - use Actor's environment (works with apify run)
        # Actor.get_env() provides environment variables when running with apify run
        apify_token = None
        try:
            # Try to get from Actor environment first (works with apify run)
            env = Actor.get_env()
            apify_token = env.get("APIFY_TOKEN") if env else None
        except Exception as e:
            Actor.log.debug(f"Could not get APIFY_TOKEN from Actor.get_env(): {e}")
        
        # Fallback to os.getenv (works with direct python execution and .env file)
        if not apify_token:
            apify_token = os.getenv("APIFY_TOKEN")
        
        if not apify_token:
            Actor.log.error("APIFY_TOKEN not found. Make sure it's set in your environment or .env file")
            return None
        
        # Use OpenAI client with OpenRouter actor endpoint
        # Base URL: https://openrouter.apify.actor/api/v1
        # Token is passed in Authorization header
        Actor.log.info(f"Calling OpenRouter actor via OpenAI client with model: {model}")
        
        # Initialize OpenAI client
        # API key can be any non-empty string (not used, but required)
        # Actual authentication is via APIFY_TOKEN in default_headers
        client = AsyncOpenAI(
            base_url="https://openrouter.apify.actor/api/v1",
            api_key="no-key-required-but-must-not-be-empty",  # Any non-empty string works
            default_headers={
                "Authorization": f"Bearer {apify_token}",
            },
            timeout=300.0,  # 5 minute timeout
        )
        
        # Call the LLM using OpenAI chat completions API
        completion = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        
        # Convert response to dict format (OpenAI response is already in the right format)
        result = {
            "choices": [
                {
                    "message": {
                        "role": choice.message.role,
                        "content": choice.message.content,
                    }
                }
                for choice in completion.choices
            ]
        }
        
        Actor.log.info("Successfully received response from OpenRouter")
        return result
            
    except Exception as e:
        Actor.log.exception(f"Error calling OpenRouter actor: {e}")
        return None


async def analyze_property_with_llm(
    property_data: dict[str, Any],
    model: str = "openrouter/auto",
    temperature: float = 0.7,
) -> dict[str, Any] | None:
    """Analyze a property listing using LLM.
    
    This is an example function showing how to use the OpenRouter integration
    to analyze scraped property data with a model.
    
    Uses APIFY_TOKEN from environment for authentication.
    
    Args:
        property_data: Dictionary containing property information (title, description, price, etc.)
        model: model to use
        temperature: LLM temperature
    
    Returns:
        Analysis result from LLM, or None on error
    """
    # Build prompt for property analysis
    prompt = f"""Analyze this real estate listing and provide insights:

Title: {property_data.get('title', 'N/A')}
Description: {property_data.get('description', 'N/A')}
Price: {property_data.get('price', 'N/A')}
Location: {property_data.get('location', 'N/A')}
Attributes: {json.dumps(property_data.get('attributes', {}), ensure_ascii=False)}

Please provide:
1. A brief summary of the property
2. Key selling points
3. Any potential concerns or red flags
4. Estimated value assessment (if possible)

Respond in JSON format with keys: summary, sellingPoints (array), concerns (array), valueAssessment.
"""
    
    messages = [
        {
            "role": "system",
            "content": "You are a real estate analyst. Provide structured, objective analysis of property listings.",
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]
    
    return await call_openrouter_llm(
        messages=messages,
        model=model,
        temperature=temperature,
    )


async def main() -> None:
    """Main entry point for the Bezrealitky scraper Actor."""
    async with Actor:
        # Get Actor input
        actor_input = await Actor.get_input() or {}
        
        # LLM configuration
        skip_scraping = actor_input.get('skipScraping', False)
        use_llm = actor_input.get('useLLM', False)
        llm_model = actor_input.get('llmModel', 'openrouter/auto')
        llm_temperature = actor_input.get('llmTemperature', 0.7)
        
        # If skipScraping is enabled, test LLM only
        if skip_scraping:
            Actor.log.info('=' * 60)
            Actor.log.info('SKIP SCRAPING MODE: Testing LLM functionality only')
            Actor.log.info('=' * 60)
            
            if not use_llm:
                Actor.log.warning('skipScraping is enabled but useLLM is false. Enabling LLM for test...')
                use_llm = True
            
            # Create sample property data for testing
            sample_property = {
                'url': 'https://www.bezrealitky.cz/nemovitosti-byty-domy/974793-nabidka-prodej-bytu-hostynska-praha',
                'title': 'Prodej bytu 3+kk 57 m², Hostýnská, Praha - Strašnice',
                'description': 'Nabízím k prodeji krásný byt o dispozici 3kk po rekonstrukci v osobním vlastnictví. Nemovitost se nachází v 2. podlaží zrevitalizovaného, panelového domu.',
                'price': '8 499 000 Kč',
                'priceType': 'sale',
                'location': 'Praha - Strašnice',
                'attributes': {
                    'Dostupné od': '20. 12. 2025',
                    'Konstrukce budovy': 'Panel',
                    'Užitná plocha': '57 m²',
                    'Dispozice': '3+kk',
                    'Podlaží': '2. podlaží z 5'
                },
                'seller': {
                    'type': 'owner',
                    'note': 'Prodává přímo majitel - bez provize'
                },
                'scrapedAt': 'https://www.bezrealitky.cz/nemovitosti-byty-domy/974793-nabidka-prodej-bytu-hostynska-praha'
            }
            
            Actor.log.info('Testing LLM analysis with sample property data...')
            Actor.log.info(f'Property: {sample_property["title"]}')
            
            try:
                llm_analysis = await analyze_property_with_llm(
                    property_data=sample_property,
                    model=llm_model,
                    temperature=llm_temperature,
                )
                
                if llm_analysis:
                    # Extract the response content
                    if 'choices' in llm_analysis and len(llm_analysis['choices']) > 0:
                        content = llm_analysis['choices'][0].get('message', {}).get('content', '')
                        Actor.log.info('=' * 60)
                        Actor.log.info('LLM ANALYSIS RESULT:')
                        Actor.log.info('=' * 60)
                        Actor.log.info(content)
                        Actor.log.info('=' * 60)
                        
                        try:
                            # Try to parse as JSON if it's structured
                            analysis_json = json.loads(content)
                            sample_property['llmAnalysis'] = analysis_json
                            Actor.log.info('LLM response parsed as JSON successfully')
                        except json.JSONDecodeError:
                            # If not JSON, store as text
                            sample_property['llmAnalysis'] = {'text': content}
                            Actor.log.info('LLM response stored as text (not JSON)')
                        
                        # Push the test result to dataset
                        await Actor.push_data(sample_property)
                        Actor.log.info('Test result pushed to dataset')
                    else:
                        Actor.log.warning('LLM response did not contain expected structure')
                        Actor.log.info(f'Full response: {json.dumps(llm_analysis, indent=2)[:500]}')
                else:
                    Actor.log.error('LLM analysis returned no result')
                    
            except Exception as e:
                Actor.log.exception(f'Error during LLM test: {e}')
                await Actor.fail(f'LLM test failed: {e}')
            
            Actor.log.info('LLM test completed!')
            await Actor.exit()
            return
        
        # Normal scraping mode
        start_urls = [
            url.get('url')
            for url in actor_input.get(
                'startUrls',
                [
                    {'url': 'https://www.bezrealitky.cz/nemovitosti-byty-domy/974793-nabidka-prodej-bytu-hostynska-praha'},
                    {'url': 'https://www.bezrealitky.cz/nemovitosti-byty-domy/981201-nabidka-prodej-bytu-pocernicka-praha'},
                    {'url': 'https://www.bezrealitky.cz/nemovitosti-byty-domy/981586-nabidka-prodej-bytu-vratislavska-praha'},
                ],
            )
        ]
        
        max_requests = actor_input.get('maxRequestsPerCrawl', 100)
        proxy_config = actor_input.get('proxyConfiguration', {'useApifyProxy': False})

        if not start_urls:
            Actor.log.info('No start URLs specified in Actor input, exiting...')
            await Actor.exit()

        Actor.log.info(f'Starting Bezrealitky scraper with {len(start_urls)} URLs')

        # Create crawler configuration
        crawler_config = {
            'max_requests_per_crawl': max_requests,
            'headless': True,
            'browser_type': 'chromium',
            'max_request_retries': 3,
        }
        
        if proxy_config.get('useApifyProxy'):
            # Proxy configuration would be added here
            Actor.log.info('Using Apify proxy')
        
        crawler = PlaywrightCrawler(**crawler_config)

        @crawler.router.default_handler
        async def request_handler(context: PlaywrightCrawlingContext) -> None:
            """Handle each Bezrealitky detail page request."""
            url = context.request.url
            Actor.log.info(f'Scraping {url}...')
            
            page = context.page
            
            # Wait for page to load - Bezrealitky is simpler, no consent issues
            try:
                await page.wait_for_load_state('networkidle', timeout=15000)
            except Exception as e:
                Actor.log.warning(f'Error during page load: {e}')
            
            # Get page content once for parsing
            page_content = await page.content()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(page_content, 'html.parser')
            
            # Extract main title (h1) - Bezrealitky uses h1 for property titles
            title = None
            try:
                title_elem = soup.find('h1')
                if title_elem:
                    title = clean_text(title_elem.get_text())
                    Actor.log.info(f'Found title: {title}')
            except Exception as e:
                Actor.log.debug(f'Error extracting title: {e}')
            
            # Extract property ID from URL or page
            property_id = None
            try:
                # Try to extract from URL pattern: /nemovitosti-byty-domy/{ID}-...
                id_match = re.search(r'/(\d+)-', url)
                if id_match:
                    property_id = id_match.group(1)
                    Actor.log.info(f'Found property ID: {property_id}')
            except Exception as e:
                Actor.log.debug(f'Error extracting property ID: {e}')
            
            # Extract price - Bezrealitky shows "Cena" with the price value
            price = None
            price_per_m2 = None
            price_type = 'sale'  # Bezrealitky mostly handles sales
            try:
                # Try to find price pattern (e.g., "8 499 000 Kč")
                price_match = re.search(r'(\d+[\s​]+\d+[\s​]+\d+\s*Kč)', page_content)
                if price_match:
                    price = clean_text(price_match.group(1))
                    Actor.log.info(f'Found price: {price}')
                
                # Also try to find price per m²
                price_per_m2_match = re.search(r'([\d\s​]+Kč\s*/\s*m2)', page_content)
                if price_per_m2_match:
                    price_per_m2 = clean_text(price_per_m2_match.group(1))
                    Actor.log.info(f'Found price per m²: {price_per_m2}')
                    
            except Exception as e:
                Actor.log.debug(f'Error extracting price: {e}')
            
            # Extract breadcrumbs for categorization
            breadcrumbs = []
            category = None
            try:
                # Find breadcrumb navigation
                breadcrumb_items = soup.find_all('li', recursive=True)
                for item in breadcrumb_items:
                    text = clean_text(item.get_text())
                    if text and len(text) < 50 and text not in breadcrumbs:
                        breadcrumbs.append(text)
                
                # Extract category (Prodej/Pronájem, Byt/Dům, etc.)
                if 'Prodej' in page_content:
                    category = 'Prodej'
                elif 'Pronájem' in page_content:
                    category = 'Pronájem'
                    price_type = 'rental'
                
                if breadcrumbs:
                    Actor.log.info(f'Found breadcrumbs: {breadcrumbs[:5]}')
                    
            except Exception as e:
                Actor.log.debug(f'Error extracting breadcrumbs: {e}')
            
            # Extract description - Bezrealitky shows description in paragraphs
            description = None
            description_english = None
            try:
                # Find all paragraphs
                paragraphs = soup.find_all('p')
                desc_candidates = []
                
                for p in paragraphs:
                    try:
                        text = clean_text(p.get_text())
                        # Valid description should be substantial
                        if text and len(text) > 100 and len(text) < 2000:
                            # Skip footer/legal text
                            if not any(skip in text.lower() for skip in 
                                     ['cookies', 'soukromí', 'podmínky', '© 20', 'seznam.cz']):
                                desc_candidates.append(text)
                    except:
                        continue
                
                # Get the longest valid description (Czech)
                if desc_candidates:
                    description = max(desc_candidates, key=len)
                    Actor.log.info(f'Found description: {len(description)} characters')
                    
                    # Try to find English translation if available
                    if len(desc_candidates) > 1:
                        # English descriptions often start with "I am offering" or similar
                        for desc in desc_candidates:
                            if any(eng in desc[:50] for eng in ['I am', 'The apartment', 'The property']):
                                description_english = desc
                                Actor.log.info('Found English description')
                                break
                            
            except Exception as e:
                Actor.log.debug(f'Error extracting description: {e}')
            
            # Extract subtitle features (e.g., "Částečně vybaveno • Sklep 2 m² • Lodžie 3 m²")
            subtitle_features = []
            try:
                # Look for subtitle or features list near the title
                all_text = soup.get_text()
                # Look for bullet-separated features
                features_match = re.findall(r'([^•\n]+•[^•\n]+)', all_text)
                if features_match:
                    for feature_line in features_match[:3]:  # Take first few matches
                        features = [clean_text(f) for f in feature_line.split('•')]
                        subtitle_features.extend([f for f in features if f and len(f) < 50])
                
                if subtitle_features:
                    Actor.log.info(f'Found subtitle features: {subtitle_features[:5]}')
                    
            except Exception as e:
                Actor.log.debug(f'Error extracting subtitle features: {e}')
            
            # Extract all property attributes from tables
            attributes = {}
            try:
                attributes = extract_property_details(soup)
                Actor.log.info(f'Found {len(attributes)} property attributes')
            except Exception as e:
                Actor.log.debug(f'Error extracting attributes: {e}')
            
            # Extract specific structured data - CRITICAL FIELDS
            property_details = {}
            area = None
            disposition = None
            
            try:
                # CRITICAL: Extract area (57 m², 60 m², etc.) - multiple strategies
                area = attributes.get('Užitná plocha')
                
                if not area and title:
                    # Try to extract from title: "Prodej bytu 3+kk 57 m²..."
                    area_match = re.search(r'(\d+\s*m²)', title)
                    if area_match:
                        area = clean_text(area_match.group(1))
                        Actor.log.info(f'✓ Extracted area from title: {area}')
                
                if not area:
                    # Try from page content
                    all_text = soup.get_text()
                    area_match = re.search(r'Užitná plocha[:\s]+(\d+\s*m²)', all_text)
                    if area_match:
                        area = clean_text(area_match.group(1))
                        Actor.log.info(f'✓ Extracted area from content: {area}')
                
                if not area:
                    Actor.log.warning('⚠ Could not extract area - this is a critical field!')
                
                # CRITICAL: Extract disposition (3+kk, 2+1, etc.) - multiple strategies
                disposition = attributes.get('Dispozice')
                
                if not disposition and title:
                    # Try to extract from title: "Prodej bytu 3+kk 57 m²..."
                    # Common formats: 1+kk, 1+1, 2+kk, 2+1, 3+kk, 3+1, 4+kk, 4+1, 5+kk, 5+1, 6+kk, atd.
                    disposition_match = re.search(r'\b(\d+\+(?:kk|1))\b', title, re.IGNORECASE)
                    if disposition_match:
                        disposition = disposition_match.group(1)
                        Actor.log.info(f'✓ Extracted disposition from title: {disposition}')
                
                if not disposition:
                    # Try from page content
                    all_text = soup.get_text()
                    disposition_match = re.search(r'Dispozice[:\s]+(\d+\+(?:kk|1))', all_text, re.IGNORECASE)
                    if disposition_match:
                        disposition = disposition_match.group(1)
                        Actor.log.info(f'✓ Extracted disposition from content: {disposition}')
                
                if not disposition:
                    Actor.log.warning('⚠ Could not extract disposition - this is a critical field!')
                
                # Build property details dictionary
                property_details['propertyId'] = property_id or attributes.get('Číslo inzerátu')
                property_details['area'] = area
                property_details['disposition'] = disposition
                property_details['floor'] = attributes.get('Podlaží')
                property_details['buildingType'] = attributes.get('Konstrukce budovy')
                property_details['condition'] = attributes.get('Stav')
                property_details['ownership'] = attributes.get('Vlastnictví')
                property_details['furnished'] = attributes.get('Vybaveno')
                property_details['energyRating'] = attributes.get('PENB')
                property_details['availableFrom'] = attributes.get('Dostupné od')
                property_details['pricePerM2'] = price_per_m2 or attributes.get('Cena za jednotku')
                
                # Remove None values
                property_details = {k: v for k, v in property_details.items() if v}
                
                if property_details:
                    Actor.log.info(f'✓ Extracted {len(property_details)} structured property details')
                
                # Validate critical fields
                if area and disposition:
                    Actor.log.info(f'✓✓ All critical property fields extracted: area={area}, disposition={disposition}')
                else:
                    missing = []
                    if not area:
                        missing.append('area')
                    if not disposition:
                        missing.append('disposition')
                    Actor.log.warning(f'⚠ Missing critical fields: {", ".join(missing)}')
                    
            except Exception as e:
                Actor.log.error(f'Error structuring property details: {e}')
                Actor.log.exception(e)
            
            # Extract amenities and features (cellar, loggia, parking, etc.)
            amenities = []
            try:
                # Look for "Co tato nemovitost nabízí?" section
                all_text = soup.get_text()
                
                # Common amenities to look for
                amenity_keywords = [
                    'Sklep', 'Lodžie', 'Balkon', 'Terasa', 'Zahrada', 
                    'Parkování', 'Garáž', 'Internet', 'Výtah', 'Bazén'
                ]
                
                for keyword in amenity_keywords:
                    # Look for the amenity with potential size info
                    amenity_match = re.search(rf'{keyword}(?:\s+(\d+\s*m²))?', all_text, re.IGNORECASE)
                    if amenity_match:
                        if amenity_match.group(1):
                            amenities.append(f"{keyword} {amenity_match.group(1)}")
                        else:
                            amenities.append(keyword)
                
                if amenities:
                    Actor.log.info(f'Found amenities: {amenities}')
                    
            except Exception as e:
                Actor.log.debug(f'Error extracting amenities: {e}')
            
            # === EXTRACT LOCATION DETAILS - CRITICAL FIELDS ===
            # Bezrealitky has a CONSISTENT title structure we can rely on:
            # 
            # Example: "Prodej bytu 3+kk • 57 m² bez realitkyHostýnská, Praha - Strašnice"
            #                                            ↑         ↑      ↑
            #                                         STREET    CITY   DISTRICT
            # 
            # Pattern breakdown:
            #   1. Property type and specs: "Prodej bytu 3+kk • 57 m²"
            #   2. Separator text: "bez realitky" (or sometimes space after m²)
            #   3. STREET: everything between separator and first comma
            #   4. CITY: major Czech city name after comma
            #   5. DISTRICT: everything after " - " following city
            location = None
            street = None
            district = None
            city = None
            
            try:
                # Strategy 1: Extract from title using consistent structure (most reliable)
                if title:
                    Actor.log.info(f'Parsing title: {title}')
                    
                    # The title format is: "Prodej bytu X+X • XX m² bez realitky{STREET}, {CITY} - {DISTRICT}"
                    # OR sometimes: "Prodej bytu X+X XX m², {STREET}, {CITY} - {DISTRICT}"
                    
                    # Look for pattern: {something}, {CITY} - {DISTRICT}
                    # The street is between the last property info and the first comma before city
                    
                    # First, find CITY - DISTRICT at the end
                    # Pattern: {CITY} - {DISTRICT} at the end of title
                    city_district_match = re.search(r',\s*(Praha|Brno|Ostrava|Plzeň|Liberec|Olomouc|Ústí nad Labem|Hradec Králové|České Budějovice|Pardubice|Zlín|Havířov|Kladno|Most|Opava|Frýdek-Místek|Karviná|Jihlava|Teplice|Děčín|Karlovy Vary|Chomutov|Jablonec nad Nisou|Mladá Boleslav|Prostějov|Přerov)\s*[-–]\s*([^,]+?)$', title, re.IGNORECASE)
                    
                    if city_district_match:
                        city = clean_text(city_district_match.group(1))
                        district = clean_text(city_district_match.group(2))
                        Actor.log.info(f'✓ Found city from title: {city}')
                        Actor.log.info(f'✓ Found district from title: {district}')
                        
                        # Now extract street - it's between the property details and ", {CITY}"
                        # Find everything after "m²" or "realitky" and before ", {CITY}"
                        street_pattern = rf'(?:m²|realitky)\s*([^,]+?),\s*{re.escape(city)}'
                        street_match = re.search(street_pattern, title, re.IGNORECASE)
                        if street_match:
                            street = clean_text(street_match.group(1))
                            Actor.log.info(f'✓ Found street from title: {street}')
                        else:
                            # Try alternative pattern - look for text between last space after m² and comma before city
                            alt_pattern = rf'm²\s+([^,]+?),\s*{re.escape(city)}'
                            alt_match = re.search(alt_pattern, title, re.IGNORECASE)
                            if alt_match:
                                street = clean_text(alt_match.group(1))
                                Actor.log.info(f'✓ Found street from title (alt): {street}')
                    
                    else:
                        # Fallback: Try without district (only city)
                        city_only_match = re.search(r',\s*(Praha|Brno|Ostrava|Plzeň|Liberec|Olomouc)(?:\s|$)', title, re.IGNORECASE)
                        if city_only_match:
                            city = clean_text(city_only_match.group(1))
                            Actor.log.info(f'✓ Found city from title (no district): {city}')
                            
                            # Try to extract street
                            street_pattern = rf'(?:m²|realitky)\s*([^,]+?),\s*{re.escape(city)}'
                            street_match = re.search(street_pattern, title, re.IGNORECASE)
                            if street_match:
                                street = clean_text(street_match.group(1))
                                Actor.log.info(f'✓ Found street from title: {street}')
                    
                    # Build full location string
                    if city and district:
                        location = f"{city} - {district}"
                    elif city:
                        location = city
                
                # Strategy 2: Fallback to breadcrumbs if something is missing
                if not city and breadcrumbs:
                    for crumb in breadcrumbs:
                        if any(city_name in crumb for city_name in ['Praha', 'Brno', 'Ostrava', 'Plzeň']):
                            city = crumb
                            Actor.log.info(f'✓ Found city from breadcrumbs (fallback): {city}')
                            break
                
                # Strategy 3: Try to find district from content if still missing
                if city and not district:
                    all_text = soup.get_text()
                    
                    # Look for common Prague districts if city is Praha
                    if city == 'Praha':
                        prague_districts = [
                            'Karlín', 'Vinohrady', 'Žižkov', 'Vršovice', 'Smíchov', 
                            'Holešovice', 'Dejvice', 'Malešice', 'Strašnice', 'Nusle',
                            'Michle', 'Libeň', 'Prosek', 'Chodov', 'Stodůlky', 'Modřany',
                            'Háje', 'Řepy', 'Kobylisy', 'Letňany', 'Bohnice', 'Střížkov',
                            'Vysočany', 'Hloubětín', 'Štěrboholy', 'Horní Počernice',
                            'Braník', 'Podolí', 'Pankrác', 'Záběhlice', 'Krč'
                        ]
                        for prague_district in prague_districts:
                            if prague_district in all_text:
                                district = prague_district
                                location = f"{city} - {district}"
                                Actor.log.info(f'✓ Found Prague district from content (fallback): {district}')
                                break
                
                # Final validation and logging
                Actor.log.info('Location extraction complete:')
                if city:
                    Actor.log.info(f'  ✓ City: {city}')
                else:
                    Actor.log.warning('  ⚠ City: MISSING (CRITICAL FIELD!)')
                
                if district:
                    Actor.log.info(f'  ✓ District: {district}')
                else:
                    Actor.log.warning('  ⚠ District: MISSING')
                
                if street:
                    Actor.log.info(f'  ✓ Street: {street}')
                else:
                    Actor.log.warning('  ⚠ Street: MISSING')
                    
            except Exception as e:
                Actor.log.error(f'Error extracting location: {e}')
                Actor.log.exception(e)
            
            # Extract image URLs
            images = []
            try:
                # Find all images in the gallery
                img_elements = soup.find_all('img', src=True)
                for img in img_elements:
                    src = img.get('src', '')
                    # Filter for actual property photos (not logos, icons, etc.)
                    if any(pattern in src for pattern in ['img.bezrealitky', 'images', 'foto', 'photo']):
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = 'https://www.bezrealitky.cz' + src
                        if src not in images and src.startswith('http'):
                            images.append(src)
                
                if images:
                    Actor.log.info(f'Found {len(images)} images')
                    
            except Exception as e:
                Actor.log.debug(f'Error extracting images: {e}')
            
            # Extract seller/contact information
            seller_info = {}
            contact_phone = None
            contact_email = None
            try:
                # Check if it's sold by owner (bez realitky = without realtor)
                if 'bez realitky' in page_content.lower() or 'přímo majitel' in page_content.lower():
                    seller_info['type'] = 'owner'
                    seller_info['note'] = 'Prodává přímo majitel - bez provize'
                    Actor.log.info('Property sold by owner')
                else:
                    seller_info['type'] = 'agent'
                
                # Look for phone number
                phone_match = re.search(r'\+420\s*\d{3}\s*\d{3}\s*\d{3}', page_content)
                if phone_match:
                    contact_phone = clean_text(phone_match.group())
                    seller_info['phone'] = contact_phone
                    Actor.log.info(f'Found contact phone: {contact_phone}')
                
                # Look for email
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', page_content)
                if email_match:
                    contact_email = email_match.group()
                    seller_info['email'] = contact_email
                    Actor.log.info(f'Found contact email: {contact_email}')
                    
            except Exception as e:
                Actor.log.debug(f'Error extracting seller info: {e}')
            
            # Build final data structure with all extracted information
            data = {
                'url': url,
                'propertyId': property_id,
                'title': title,
                'category': category,
                'description': description,
                'descriptionEnglish': description_english,
                'price': price,
                'priceType': price_type,
                'location': {
                    'full': location,
                    'city': city,
                    'district': district,
                    'street': street,
                },
                'propertyDetails': property_details,
                'attributes': attributes,
                'features': subtitle_features,
                'amenities': amenities,
                'images': images,
                'seller': seller_info,
                'breadcrumbs': breadcrumbs[:10] if breadcrumbs else [],
                'scrapedAt': page.url,
            }
            
            # Clean up empty values but KEEP location and propertyDetails structure
            # Remove only top-level None/empty values (not nested objects)
            data_cleaned = {}
            for key, value in data.items():
                if key in ['location', 'propertyDetails', 'seller']:
                    # Always keep these structures even if some fields are None
                    data_cleaned[key] = value
                elif value not in [None, '', [], {}]:
                    data_cleaned[key] = value
            
            data = data_cleaned
            
            # === VALIDATION: Log critical fields ===
            Actor.log.info('=' * 70)
            Actor.log.info('EXTRACTED DATA SUMMARY:')
            Actor.log.info('=' * 70)
            
            # Validate and log critical fields
            critical_fields_status = {
                'City': city,
                'District': district,
                'Street': street,
                'Area': property_details.get('area'),
                'Disposition': property_details.get('disposition'),
            }
            
            all_critical_present = all(critical_fields_status.values())
            
            if all_critical_present:
                Actor.log.info('✓✓✓ ALL CRITICAL FIELDS EXTRACTED SUCCESSFULLY ✓✓✓')
            else:
                Actor.log.warning('⚠⚠⚠ SOME CRITICAL FIELDS MISSING ⚠⚠⚠')
            
            for field_name, field_value in critical_fields_status.items():
                status = '✓' if field_value else '✗'
                Actor.log.info(f'  {status} {field_name}: {field_value or "MISSING"}')
            
            Actor.log.info('-' * 70)
            Actor.log.info(f'Property ID: {property_id}')
            Actor.log.info(f'Title: {title}')
            Actor.log.info(f'Price: {price}')
            Actor.log.info(f'Images: {len(images)}')
            Actor.log.info(f'Amenities: {len(amenities)}')
            if description:
                Actor.log.info(f'Description: {description[:80]}...')
            Actor.log.info('=' * 70)
            
            # Optionally analyze with LLM if enabled
            if use_llm:
                try:
                    Actor.log.info('Analyzing property with LLM...')
                    llm_analysis = await analyze_property_with_llm(
                        property_data=data,
                        model=llm_model,
                        temperature=llm_temperature,
                    )
                    
                    if llm_analysis:
                        # Extract the response content
                        if 'choices' in llm_analysis and len(llm_analysis['choices']) > 0:
                            content = llm_analysis['choices'][0].get('message', {}).get('content', '')
                            try:
                                # Try to parse as JSON if it's structured
                                analysis_json = json.loads(content)
                                data['llmAnalysis'] = analysis_json
                            except json.JSONDecodeError:
                                # If not JSON, store as text
                                data['llmAnalysis'] = {'text': content}
                            
                            Actor.log.info('LLM analysis completed successfully')
                        else:
                            Actor.log.warning('LLM response did not contain expected structure')
                    else:
                        Actor.log.warning('LLM analysis returned no result')
                except Exception as e:
                    Actor.log.exception(f'Error during LLM analysis: {e}')
                    # Continue even if LLM fails
            
            # Store data to dataset
            await context.push_data(data)

        # Run the crawler
        await crawler.run(start_urls)
        
        Actor.log.info('Scraping completed successfully!')
