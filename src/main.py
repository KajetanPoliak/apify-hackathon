"""Sreality.cz Detail Page Scraper.

This Actor scrapes detailed information from Sreality.cz property listing pages.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

from apify import Actor
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

# Load environment variables from .env file
load_dotenv()


def clean_text(text: str | None) -> str | None:
    """Clean and normalize text by removing extra whitespace."""
    if not text:
        return None
    return re.sub(r'\s+', ' ', text.strip())


def extract_property_details(soup: Any) -> dict[str, Any]:
    """Extract all property details from the listing page."""
    details = {}
    
    # Find all property detail sections
    # Sreality uses specific structure for property attributes
    detail_items = soup.find_all('div', class_=re.compile(r'.*'))
    
    # Try to find price
    price_elem = soup.find(text=re.compile(r'Kč/měsíc|Kč'))
    if price_elem:
        details['price'] = clean_text(price_elem.strip())
    
    # Extract structured data from the page
    # Look for key-value pairs in the property details section
    for item in soup.find_all(['div', 'span', 'p']):
        text = item.get_text(strip=True)
        if ':' in text:
            parts = text.split(':', 1)
            if len(parts) == 2:
                key = clean_text(parts[0])
                value = clean_text(parts[1])
                if key and value and len(key) < 50:  # Avoid very long keys
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
    """Main entry point for the Sreality scraper Actor."""
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
                'url': 'https://www.sreality.cz/detail/test/123456',
                'title': 'Pronájem bytu 4+1 180 m² Martinská, Praha - Staré Město',
                'description': 'Klasický, prostorný, 3 ložnicový byt v historickém centru Prahy. Byt se nachází ve velmi dobrém stavu, je plně vybavený a nachází se v blízkosti Václavského náměstí. Ideální pro rodinu nebo sdílené bydlení.',
                'price': '55 000 Kč/měsíc',
                'priceType': 'rental',
                'location': 'Praha - Staré Město',
                'attributes': {
                    'Cena': '55 000 Kč/měsíc',
                    'Plocha': 'Užitná plocha 180 m²',
                    'Energetická náročnost': 'Mimořádně nehospodárná',
                    'Stavba': 'Smíšená, Ve velmi dobrém stavu, 2. podlaží z 6',
                    'Parkování': 'Možnost parkování',
                    'Balkon': 'Ano'
                },
                'seller': {
                    'name': 'Test Real Estate Agency',
                    'phone': '+420 123 456 789',
                    'email': 'test@realestate.cz'
                },
                'scrapedAt': 'https://www.sreality.cz/detail/test/123456'
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
                [{'url': 'https://www.sreality.cz/detail/prodej/dum/rodinny/velvary-velvary-tyrsova/2882372428'}],
            )
        ]
        
        max_requests = actor_input.get('maxRequestsPerCrawl', 100)
        proxy_config = actor_input.get('proxyConfiguration', {'useApifyProxy': False})

        if not start_urls:
            Actor.log.info('No start URLs specified in Actor input, exiting...')
            await Actor.exit()

        Actor.log.info(f'Starting Sreality scraper with {len(start_urls)} URLs')

        # Create crawler with better stealth configuration
        crawler_config = {
            'max_requests_per_crawl': max_requests,
            'headless': False,  # Run in headed mode to avoid detection
            'browser_type': 'chromium',
            'max_request_retries': 3,
        }
        
        if proxy_config.get('useApifyProxy'):
            # Proxy configuration would be added here
            Actor.log.info('Using Apify proxy')
        
        Actor.log.info('Starting crawler in non-headless mode to avoid bot detection')
        
        crawler = PlaywrightCrawler(**crawler_config)

        @crawler.router.default_handler
        async def request_handler(context: PlaywrightCrawlingContext) -> None:
            """Handle each Sreality detail page request."""
            url = context.request.url
            Actor.log.info(f'Scraping {url}...')
            
            page = context.page
            
            # Wait for page to load
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=15000)
                await page.wait_for_timeout(3000)
                
                # Check if we're on the consent page (cmp.seznam.cz)
                current_url = page.url
                if 'cmp.seznam.cz' in current_url or 'nastaveni-souhlasu' in current_url:
                    Actor.log.info(f'Detected cookie consent page: {current_url}')
                    
                    # Wait for the consent dialog to fully render
                    await page.wait_for_timeout(3000)
                    
                    # Take screenshot for debugging
                    try:
                        await page.screenshot(path='storage/key_value_stores/default/consent_page.png')
                        Actor.log.info('Saved screenshot of consent page')
                    except:
                        pass
                    
                    consent_handled = False
                    
                    # In non-headless mode, give user time to manually click "Souhlasím"
                    if not crawler_config.get('headless', True):
                        Actor.log.info('='*60)
                        Actor.log.info('MANUAL ACTION REQUIRED:')
                        Actor.log.info('Please click the "Souhlasím" button in the browser window')
                        Actor.log.info('Waiting 20 seconds for manual click...')
                        Actor.log.info('='*60)
                        
                        # Wait for navigation to complete
                        try:
                            # Wait for URL to change to detail page
                            await page.wait_for_url('**/detail/**', timeout=20000)
                            consent_handled = True
                            Actor.log.info('Successfully navigated to detail page!')
                        except:
                            # Check current URL anyway
                            try:
                                current_url = page.url
                                if 'sreality.cz/detail' in current_url:
                                    consent_handled = True
                                    Actor.log.info('Now on detail page')
                            except:
                                Actor.log.warning('Page may have closed or navigated unexpectedly')
                    
                    # Strategy 1: Wait for consent buttons to load automatically
                    if not consent_handled:
                        try:
                            Actor.log.info('Waiting for consent dialog to fully load...')
                            # Wait for specific consent button text to appear
                            await page.wait_for_function(
                                "document.body.innerText.includes('Souhlasím')",
                                timeout=10000
                            )
                            Actor.log.info('Consent dialog loaded with "Souhlasím" text')
                        except Exception as e:
                            Actor.log.warning(f'Could not find "Souhlasím" text: {e}')
                    
                    # Wait a bit more for buttons to be clickable
                    await page.wait_for_timeout(2000)
                    
                    # Strategy 2: Check ALL clickable elements (button, a, div with click handlers)
                    try:
                        all_clickable = await page.locator('button, a, [role="button"], div[onclick]').all()
                        Actor.log.info(f'Found {len(all_clickable)} clickable elements')
                        
                        for i, elem in enumerate(all_clickable):
                            try:
                                text = await elem.inner_text()
                                if text:
                                    text = text.strip()
                                    Actor.log.info(f'Element {i}: "{text}"')
                                    
                                    if 'Souhlasím' in text:
                                        Actor.log.info(f'Found "Souhlasím" element! Clicking...')
                                        await elem.click(timeout=5000, force=True)
                                        Actor.log.info('Clicked! Waiting for navigation...')
                                        
                                        # Wait for navigation or URL change
                                        try:
                                            await page.wait_for_url('**/detail/**', timeout=10000)
                                            consent_handled = True
                                            Actor.log.info('Successfully navigated to detail page!')
                                            break
                                        except:
                                            await page.wait_for_timeout(3000)
                                            if 'sreality.cz/detail' in page.url:
                                                consent_handled = True
                                                Actor.log.info('Now on detail page!')
                                                break
                            except Exception as e:
                                Actor.log.debug(f'Element {i} error: {str(e)[:100]}')
                                continue
                    except Exception as e:
                        Actor.log.warning(f'Error searching elements: {e}')
                    
                    # Strategy 3: Force navigation if button clicking didn't work
                    if not consent_handled:
                        Actor.log.warning('Button clicking failed, forcing navigation...')
                        try:
                            await page.goto(url, wait_until='networkidle', timeout=20000)
                            Actor.log.info('Force navigated to target URL')
                        except Exception as e:
                            Actor.log.error(f'Force navigation failed: {e}')
                
                # Now wait for the actual property content
                await page.wait_for_load_state('networkidle', timeout=10000)
                
            except Exception as e:
                Actor.log.warning(f'Error during page load/consent handling: {e}')
            
            # Extract main title (h1)
            title = None
            try:
                title_elem = await page.query_selector('h1')
                if title_elem:
                    title = clean_text(await title_elem.text_content())
            except Exception as e:
                Actor.log.debug(f'Error extracting title: {e}')
            
            # Extract price (handles both rental and sale prices)
            price = None
            price_type = None
            try:
                # Look for price patterns - rental: "X Kč/měsíc" or sale: "X Kč"
                page_text = await page.content()
                
                # Try rental price first
                rental_match = re.search(r'(\d+[\s​]*\d*[\s​]*\d*[\s​]*K[čc]/měsíc)', page_text)
                if rental_match:
                    price = clean_text(rental_match.group(1))
                    price_type = 'rental'
                else:
                    # Try sale price - look for large numbers with Kč (captures full price with multiple digit groups)
                    sale_match = re.search(r'(\d+(?:[\s​]*\d+)*[\s​]*K[čc])', page_text)
                    if sale_match:
                        raw_price = sale_match.group(1)
                        # Only accept prices with at least 6 digits (over 100k)
                        digits_only = re.sub(r'[^\d]', '', raw_price)
                        if len(digits_only) >= 6:
                            price = clean_text(raw_price)
                            price_type = 'sale'
                
                # Fallback: find price element visually
                if not price:
                    # Look for elements with large price-like text
                    price_candidates = await page.query_selector_all('span, div, p')
                    for elem in price_candidates[:100]:
                        try:
                            text = await elem.text_content()
                            if text:
                                text = text.strip()
                                # Check for rental price
                                if re.match(r'^\d+\s*Kč/měsíc$', text):
                                    price = clean_text(text)
                                    price_type = 'rental'
                                    break
                                # Check for sale price (at least 6 digits)
                                elif re.match(r'^\d+[\s​]*\d+[\s​]*\d+\s*Kč$', text):
                                    price = clean_text(text)
                                    price_type = 'sale'
                                    break
                        except:
                            continue
                
                if price:
                    Actor.log.info(f'Found {price_type} price: {price}')
                    
            except Exception as e:
                Actor.log.debug(f'Error extracting price: {e}')
            
            # Extract description - the main property description text
            description = None
            try:
                # Strategy 1: Look for description in structured elements
                desc_candidates = []
                
                # Try to find the main description block (usually after title/price)
                all_text_blocks = await page.query_selector_all('p, div[class*="description"], section')
                
                for block in all_text_blocks:
                    try:
                        text = await block.text_content()
                        if text:
                            text = clean_text(text)
                            # Valid description should be substantial and not footer/legal
                            if (len(text) > 150 and len(text) < 5000 and
                                not any(skip in text.lower() for skip in 
                                       ['seznam.cz, a.s.', 'cookies', 'souhlas', 'ochrana údajů', 
                                        'smluvní podmínky', 'jakékoliv užití obsahu'])):
                                desc_candidates.append(text)
                    except:
                        continue
                
                # Get the longest valid description
                if desc_candidates:
                    description = max(desc_candidates, key=len)
                    Actor.log.info(f'Found description: {len(description)} characters')
                else:
                    # Fallback: combine multiple smaller paragraphs
                    paragraphs = await page.query_selector_all('p')
                    text_parts = []
                    for p in paragraphs[:20]:  # Check first 20 paragraphs
                        text = clean_text(await p.text_content())
                        if text and len(text) > 50 and len(text) < 1000:
                            if not any(skip in text.lower() for skip in ['seznam.cz', 'cookies']):
                                text_parts.append(text)
                    
                    if text_parts:
                        # Take the first substantial paragraph
                        description = text_parts[0] if text_parts else None
                            
            except Exception as e:
                Actor.log.debug(f'Error extracting description: {e}')
            
            # Extract all text content for attributes
            attributes = {}
            try:
                # Get all text from the page
                page_content = await page.content()
                # Use BeautifulSoup to parse for structured data
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(page_content, 'html.parser')
                attributes = extract_property_details(soup)
                
                # If price wasn't found or seems wrong, try to get it from attributes
                if attributes and not price or (price and len(re.sub(r'[^\d]', '', price)) < 6):
                    # Look for "Celková cena" or "Cena" in attributes for sale listings
                    if 'Celková cena' in attributes:
                        price = clean_text(attributes['Celková cena'])
                        price_type = 'sale'
                        Actor.log.info(f'Corrected price from attributes: {price}')
            except Exception as e:
                Actor.log.debug(f'Error extracting attributes: {e}')
            
            # Extract location from title or page
            location_parts = []
            if title:
                location_match = re.search(r'Praha[^,]*|Brno[^,]*', title)
                if location_match:
                    location_parts.append(clean_text(location_match.group()))
            
            # Extract seller information
            seller_name = None
            seller_phone = None
            seller_email = None
            
            try:
                page_content = await page.content()
                # Look for phone numbers
                phone_match = re.search(r'\+\d{3}\s*\d{3}\s*\d{3}\s*\d{3}', page_content)
                if phone_match:
                    seller_phone = phone_match.group()
                
                # Look for email
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', page_content)
                if email_match:
                    seller_email = email_match.group()
                
                # Look for seller name
                seller_elem = await page.query_selector('[class*="seller"], [class*="prodejce"], [class*="realitka"]')
                if seller_elem:
                    seller_name = clean_text(await seller_elem.text_content())
            except Exception as e:
                Actor.log.debug(f'Error extracting seller info: {e}')
            
            # Build final data structure
            data = {
                'url': url,
                'title': title,
                'description': description,
                'price': price,
                'priceType': price_type,  # 'rental' or 'sale'
                'location': ' '.join(location_parts) if location_parts else None,
                'attributes': attributes,
                'seller': {
                    'name': seller_name,
                    'phone': seller_phone,
                    'email': seller_email,
                },
                'scrapedAt': page.url,
            }
            
            # Log what we found
            Actor.log.info(f'Extracted: {title}')
            if description:
                Actor.log.info(f'Description preview: {description[:100]}...')
            
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
