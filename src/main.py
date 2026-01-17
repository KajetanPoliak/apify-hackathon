"""Sreality.cz Detail Page Scraper.

This Actor scrapes detailed information from Sreality.cz property listing pages.
"""

from __future__ import annotations

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


async def main() -> None:
    """Main entry point for the Sreality scraper Actor."""
    async with Actor:
        # Get Actor input
        actor_input = await Actor.get_input() or {}
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
            
            # Extract price first (usually prominent at top)
            price = None
            try:
                # Look for price patterns - usually "X Kč/měsíc" or "X Kč"
                page_text = await page.content()
                # Try to find price with specific pattern
                price_match = re.search(r'(\d+[\s​]*\d*[\s​]*\d*[\s​]*K[čc]/měsíc)', page_text)
                if price_match:
                    price = clean_text(price_match.group(1))
                else:
                    # Fallback: look for price element
                    price_elems = await page.query_selector_all('*')
                    for elem in price_elems[:50]:  # Check first 50 elements
                        text = await elem.text_content()
                        if text and re.search(r'\d+\s*Kč/měsíc', text) and len(text) < 50:
                            price = clean_text(text)
                            if 'Kč/měsíc' in price:
                                break
            except Exception as e:
                Actor.log.debug(f'Error extracting price: {e}')
            
            # Extract description - the main property description text (usually longer paragraph)
            description = None
            try:
                # Get all paragraphs and find the longest substantial one
                paragraphs = await page.query_selector_all('p')
                longest_text = ""
                
                for p in paragraphs:
                    text = clean_text(await p.text_content())
                    if text and len(text) > len(longest_text) and len(text) > 100:
                        # Make sure it's actual description, not footer/legal text
                        if not any(skip in text.lower() for skip in ['seznam.cz, a.s.', 'cookies', 'souhlas']):
                            longest_text = text
                
                if longest_text:
                    description = longest_text
                    Actor.log.debug(f'Found description: {len(description)} characters')
                            
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
            
            # Store data to dataset
            await context.push_data(data)

        # Run the crawler
        await crawler.run(start_urls)
        
        Actor.log.info('Scraping completed successfully!')
