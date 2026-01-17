"""Scraper service for Sreality.cz property listings."""

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


async def extract_property_data(page: Any, url: str) -> dict[str, Any]:
    """Extract property data from a Sreality.cz page.
    
    Args:
        page: Playwright page object
        url: URL of the property listing
    
    Returns:
        Dictionary containing extracted property data
    """
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
        page_text = await page.content()
        
        # Try rental price first
        rental_match = re.search(r'(\d+[\s​]*\d*[\s​]*\d*[\s​]*K[čc]/měsíc)', page_text)
        if rental_match:
            price = clean_text(rental_match.group(1))
            price_type = 'rental'
        else:
            # Try sale price
            sale_match = re.search(r'(\d+(?:[\s​]*\d+)*[\s​]*K[čc])', page_text)
            if sale_match:
                raw_price = sale_match.group(1)
                digits_only = re.sub(r'[^\d]', '', raw_price)
                if len(digits_only) >= 6:
                    price = clean_text(raw_price)
                    price_type = 'sale'
        
        # Fallback: find price element visually
        if not price:
            price_candidates = await page.query_selector_all('span, div, p')
            for elem in price_candidates[:100]:
                try:
                    text = await elem.text_content()
                    if text:
                        text = text.strip()
                        if re.match(r'^\d+\s*Kč/měsíc$', text):
                            price = clean_text(text)
                            price_type = 'rental'
                            break
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
    
    # Extract description
    description = None
    try:
        desc_candidates = []
        all_text_blocks = await page.query_selector_all('p, div[class*="description"], section')
        
        for block in all_text_blocks:
            try:
                text = await block.text_content()
                if text:
                    text = clean_text(text)
                    if (len(text) > 150 and len(text) < 5000 and
                        not any(skip in text.lower() for skip in 
                               ['seznam.cz, a.s.', 'cookies', 'souhlas', 'ochrana údajů', 
                                'smluvní podmínky', 'jakékoliv užití obsahu'])):
                        desc_candidates.append(text)
            except:
                continue
        
        if desc_candidates:
            description = max(desc_candidates, key=len)
            Actor.log.info(f'Found description: {len(description)} characters')
        else:
            paragraphs = await page.query_selector_all('p')
            text_parts = []
            for p in paragraphs[:20]:
                text = clean_text(await p.text_content())
                if text and len(text) > 50 and len(text) < 1000:
                    if not any(skip in text.lower() for skip in ['seznam.cz', 'cookies']):
                        text_parts.append(text)
            
            if text_parts:
                description = text_parts[0] if text_parts else None
                            
    except Exception as e:
        Actor.log.debug(f'Error extracting description: {e}')
    
    # Extract attributes
    attributes = {}
    try:
        page_content = await page.content()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(page_content, 'html.parser')
        attributes = extract_property_details(soup)
        
        # If price wasn't found, try to get it from attributes
        if attributes and not price or (price and len(re.sub(r'[^\d]', '', price)) < 6):
            if 'Celková cena' in attributes:
                price = clean_text(attributes['Celková cena'])
                price_type = 'sale'
                Actor.log.info(f'Corrected price from attributes: {price}')
    except Exception as e:
        Actor.log.debug(f'Error extracting attributes: {e}')
    
    # Extract location from title
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
        phone_match = re.search(r'\+\d{3}\s*\d{3}\s*\d{3}\s*\d{3}', page_content)
        if phone_match:
            seller_phone = phone_match.group()
        
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', page_content)
        if email_match:
            seller_email = email_match.group()
        
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
        'priceType': price_type,
        'location': ' '.join(location_parts) if location_parts else None,
        'attributes': attributes,
        'seller': {
            'name': seller_name,
            'phone': seller_phone,
            'email': seller_email,
        },
        'scrapedAt': page.url,
    }
    
    return data


async def handle_consent_page(page: Any, url: str, crawler_config: dict[str, Any]) -> bool:
    """Handle cookie consent page if present.
    
    Args:
        page: Playwright page object
        url: Target URL
        crawler_config: Crawler configuration
    
    Returns:
        True if consent was handled successfully, False otherwise
    """
    try:
        current_url = page.url
        if 'cmp.seznam.cz' in current_url or 'nastaveni-souhlasu' in current_url:
            Actor.log.info(f'Detected cookie consent page: {current_url}')
            await page.wait_for_timeout(3000)
            
            consent_handled = False
            
            # In non-headless mode, give user time to manually click
            if not crawler_config.get('headless', True):
                Actor.log.info('='*60)
                Actor.log.info('MANUAL ACTION REQUIRED:')
                Actor.log.info('Please click the "Souhlasím" button in the browser window')
                Actor.log.info('Waiting 20 seconds for manual click...')
                Actor.log.info('='*60)
                
                try:
                    await page.wait_for_url('**/detail/**', timeout=20000)
                    consent_handled = True
                    Actor.log.info('Successfully navigated to detail page!')
                except:
                    try:
                        current_url = page.url
                        if 'sreality.cz/detail' in current_url:
                            consent_handled = True
                            Actor.log.info('Now on detail page')
                    except:
                        Actor.log.warning('Page may have closed or navigated unexpectedly')
            
            # Try to find and click consent button automatically
            if not consent_handled:
                try:
                    await page.wait_for_function(
                        "document.body.innerText.includes('Souhlasím')",
                        timeout=10000
                    )
                    Actor.log.info('Consent dialog loaded with "Souhlasím" text')
                except Exception as e:
                    Actor.log.warning(f'Could not find "Souhlasím" text: {e}')
                
                await page.wait_for_timeout(2000)
                
                try:
                    all_clickable = await page.locator('button, a, [role="button"], div[onclick]').all()
                    Actor.log.info(f'Found {len(all_clickable)} clickable elements')
                    
                    for i, elem in enumerate(all_clickable):
                        try:
                            text = await elem.inner_text()
                            if text and 'Souhlasím' in text.strip():
                                Actor.log.info(f'Found "Souhlasím" element! Clicking...')
                                await elem.click(timeout=5000, force=True)
                                
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
                
                # Force navigation if button clicking didn't work
                if not consent_handled:
                    Actor.log.warning('Button clicking failed, forcing navigation...')
                    try:
                        await page.goto(url, wait_until='networkidle', timeout=20000)
                        Actor.log.info('Force navigated to target URL')
                    except Exception as e:
                        Actor.log.error(f'Force navigation failed: {e}')
            
            return consent_handled
        
        return True
    except Exception as e:
        Actor.log.warning(f'Error handling consent page: {e}')
        return False
