"""Scraper service for Bezrealitky.cz property listings."""

import re
from typing import Any

from apify import Actor
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

try:
    from .prague_districts import get_prague_admin_district
    from .prague_real_estate_data import get_info as get_district_info
except ImportError:
    # Fallback if module not available
    def get_prague_admin_district(district_name: str):
        return None
    def get_district_info(district_no: int):
        return None


def clean_text(text: str | None) -> str | None:
    """Clean and normalize text by removing extra whitespace."""
    if not text:
        return None
    return re.sub(r'\s+', ' ', text.strip())


def clean_street_name(street: str | None) -> str | None:
    """Clean and normalize street name by removing artifacts like 'bez realitky'."""
    if not street:
        return None
    
    # Remove "bez realitky" text (with or without spaces)
    street = re.sub(r'bez\s*realitky', '', street, flags=re.IGNORECASE)
    
    # Remove leading/trailing special characters and whitespace
    street = street.strip()
    
    # Remove leading bullet points, dashes, etc.
    street = re.sub(r'^[•\-\s]+', '', street)
    
    # Clean up multiple spaces
    street = re.sub(r'\s+', ' ', street)
    
    return street.strip() if street.strip() else None


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


async def extract_property_data(page: Any, url: str) -> dict[str, Any]:
    """Extract property data from a Bezrealitky.cz page.
    
    Args:
        page: Playwright page object
        url: URL of the property listing
    
    Returns:
        Dictionary containing extracted property data
    """
    # Get page content once for parsing
    page_content = await page.content()
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(page_content, 'html.parser')
    
    # Extract main title (h1)
    title = None
    try:
        title_elem = soup.find('h1')
        if title_elem:
            title = clean_text(title_elem.get_text())
            Actor.log.info(f'Found title: {title}')
    except Exception as e:
        Actor.log.debug(f'Error extracting title: {e}')
    
    # Extract property ID from URL
    property_id = None
    try:
        id_match = re.search(r'/(\d+)-', url)
        if id_match:
            property_id = id_match.group(1)
            Actor.log.info(f'Found property ID: {property_id}')
    except Exception as e:
        Actor.log.debug(f'Error extracting property ID: {e}')
    
    # Extract price
    price = None
    price_per_m2 = None
    price_type = 'sale'
    try:
        price_match = re.search(r'(\d+[\s​]+\d+[\s​]+\d+\s*Kč)', page_content)
        if price_match:
            price = clean_text(price_match.group(1))
            Actor.log.info(f'Found price: {price}')
        
        price_per_m2_match = re.search(r'([\d\s​]+Kč\s*/\s*m2)', page_content)
        if price_per_m2_match:
            price_per_m2 = clean_text(price_per_m2_match.group(1))
            Actor.log.info(f'Found price per m²: {price_per_m2}')
    except Exception as e:
        Actor.log.debug(f'Error extracting price: {e}')
    
    # Extract breadcrumbs and category
    breadcrumbs = []
    category = None
    try:
        breadcrumb_items = soup.find_all('li', recursive=True)
        for item in breadcrumb_items:
            text = clean_text(item.get_text())
            if text and len(text) < 50 and text not in breadcrumbs:
                breadcrumbs.append(text)
        
        if 'Prodej' in page_content:
            category = 'Prodej'
        elif 'Pronájem' in page_content:
            category = 'Pronájem'
            price_type = 'rental'
        
        if breadcrumbs:
            Actor.log.info(f'Found breadcrumbs: {breadcrumbs[:5]}')
    except Exception as e:
        Actor.log.debug(f'Error extracting breadcrumbs: {e}')
    
    # Extract description - get ALL paragraphs that form the complete description
    description = None
    description_english = None
    try:
        paragraphs = soup.find_all('p')
        
        # Collect all valid description paragraphs
        czech_paragraphs = []
        english_paragraphs = []
        
        for p in paragraphs:
            try:
                text = clean_text(p.get_text())
                
                # Skip if too short or contains footer/legal content
                if not text or len(text) < 50:
                    continue
                    
                # Filter out non-description content
                skip_keywords = [
                    'cookies', 'soukromí', 'podmínky', '© 20', 'seznam.cz',
                    'všechna práva', 'jakékoliv užití', 'odmítnout vše',
                    'přijmout vše', 'nastavit', 'consent', 'details',
                    'personalizovaná reklama', 'měření výkonu reklamy'
                ]
                
                if any(skip in text.lower() for skip in skip_keywords):
                    continue
                
                # Detect if it's English (starts with common English phrases)
                is_english = any(eng in text[:80] for eng in [
                    'I am offering', 'The apartment', 'The property', 'The flat',
                    'For sale', 'For rent', 'Located in', 'This property'
                ])
                
                if is_english:
                    english_paragraphs.append(text)
                else:
                    # It's Czech description
                    czech_paragraphs.append(text)
                    
            except Exception as e:
                Actor.log.debug(f'Error processing paragraph: {e}')
                continue
        
        # Combine Czech paragraphs into full description
        if czech_paragraphs:
            # Join all paragraphs with double newline for readability
            description = '\n\n'.join(czech_paragraphs)
            Actor.log.info(f'Found description: {len(description)} characters ({len(czech_paragraphs)} paragraphs)')
        
        # Combine English paragraphs if available
        if english_paragraphs:
            description_english = '\n\n'.join(english_paragraphs)
            Actor.log.info(f'Found English description: {len(description_english)} characters ({len(english_paragraphs)} paragraphs)')
            
    except Exception as e:
        Actor.log.debug(f'Error extracting description: {e}')
    
    # Extract subtitle features
    subtitle_features = []
    try:
        all_text = soup.get_text()
        features_match = re.findall(r'([^•\n]+•[^•\n]+)', all_text)
        if features_match:
            for feature_line in features_match[:3]:
                features = [clean_text(f) for f in feature_line.split('•')]
                subtitle_features.extend([f for f in features if f and len(f) < 50])
        
        if subtitle_features:
            Actor.log.info(f'Found subtitle features: {subtitle_features[:5]}')
    except Exception as e:
        Actor.log.debug(f'Error extracting subtitle features: {e}')
    
    # Extract attributes
    attributes = {}
    try:
        attributes = extract_property_details(soup)
        Actor.log.info(f'Found {len(attributes)} property attributes')
    except Exception as e:
        Actor.log.debug(f'Error extracting attributes: {e}')
    
    # Extract critical structured data
    property_details = {}
    area = None
    disposition = None
    
    try:
        # Extract area
        area = attributes.get('Užitná plocha')
        
        if not area and title:
            area_match = re.search(r'(\d+\s*m²)', title)
            if area_match:
                area = clean_text(area_match.group(1))
                Actor.log.info(f'✓ Extracted area from title: {area}')
        
        if not area:
            all_text = soup.get_text()
            area_match = re.search(r'Užitná plocha[:\s]+(\d+\s*m²)', all_text)
            if area_match:
                area = clean_text(area_match.group(1))
                Actor.log.info(f'✓ Extracted area from content: {area}')
        
        # Extract disposition
        disposition = attributes.get('Dispozice')
        
        if not disposition and title:
            disposition_match = re.search(r'\b(\d+\+(?:kk|1))\b', title, re.IGNORECASE)
            if disposition_match:
                disposition = disposition_match.group(1)
                Actor.log.info(f'✓ Extracted disposition from title: {disposition}')
        
        if not disposition:
            all_text = soup.get_text()
            disposition_match = re.search(r'Dispozice[:\s]+(\d+\+(?:kk|1))', all_text, re.IGNORECASE)
            if disposition_match:
                disposition = disposition_match.group(1)
                Actor.log.info(f'✓ Extracted disposition from content: {disposition}')
        
        # Build property details
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
        
        property_details = {k: v for k, v in property_details.items() if v}
        
        if property_details:
            Actor.log.info(f'✓ Extracted {len(property_details)} structured property details')
    except Exception as e:
        Actor.log.error(f'Error structuring property details: {e}')
    
    # Extract amenities
    amenities = []
    try:
        all_text = soup.get_text()
        amenity_keywords = [
            'Sklep', 'Lodžie', 'Balkon', 'Terasa', 'Zahrada', 
            'Parkování', 'Garáž', 'Internet', 'Výtah', 'Bazén'
        ]
        
        for keyword in amenity_keywords:
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
    
    # Extract location details
    location = None
    street = None
    district = None
    city = None
    
    try:
        if title:
            # Extract city and district from title
            city_district_match = re.search(
                r',\s*(Praha|Brno|Ostrava|Plzeň|Liberec|Olomouc|Ústí nad Labem|Hradec Králové|České Budějovice|Pardubice|Zlín|Havířov|Kladno|Most|Opava|Frýdek-Místek|Karviná|Jihlava|Teplice|Děčín|Karlovy Vary|Chomutov|Jablonec nad Nisou|Mladá Boleslav|Prostějov|Přerov)\s*[-–]\s*([^,]+?)$',
                title,
                re.IGNORECASE
            )
            
            if city_district_match:
                city = clean_text(city_district_match.group(1))
                district = clean_text(city_district_match.group(2))
                Actor.log.info(f'✓ Found city: {city}, district: {district}')
                
                # Extract street
                street_pattern = rf'(?:m²|realitky)\s*([^,]+?),\s*{re.escape(city)}'
                street_match = re.search(street_pattern, title, re.IGNORECASE)
                if street_match:
                    street = clean_street_name(street_match.group(1))
                    if street:  # Only log if we have a valid street after cleaning
                        Actor.log.info(f'✓ Found street: {street}')
            else:
                # Fallback: city only
                city_only_match = re.search(r',\s*(Praha|Brno|Ostrava|Plzeň|Liberec|Olomouc)(?:\s|$)', title, re.IGNORECASE)
                if city_only_match:
                    city = clean_text(city_only_match.group(1))
                    Actor.log.info(f'✓ Found city: {city}')
        
        # Build location
        if city and district:
            location = f"{city} - {district}"
        elif city:
            location = city
        
        # Add Prague administrative district number if available
        prague_admin_district = None
        district_stats = None
        
        if city and city.lower() == 'praha' and district:
            prague_admin_district = get_prague_admin_district(district)
            if prague_admin_district:
                Actor.log.info(f'✓ Mapped to {prague_admin_district}')
                
                # Get real estate and crime statistics for the district
                try:
                    district_number = int(prague_admin_district.split()[-1])
                    district_info = get_district_info(district_number)
                    if district_info:
                        district_stats = {
                            'avgPricePerSqmCzk': district_info.avg_price_per_sqm_czk,
                            'priceChangePercent': district_info.price_change_percent,
                            'priceCategory': district_info.price_category,
                            'crimeStats': {
                                'violentCrimes': district_info.crime_nasilna_normalized,
                                'burglaries': district_info.crime_kradeze_vloupanim_normalized,
                                'fires': district_info.crime_pozary_normalized
                            },
                            'kebabIndex': district_info.kebab_index_normalized,
                        }
                        Actor.log.info(f'✓ Added district statistics: Avg price {district_stats["avgPricePerSqmCzk"]} Kč/m², Crime: {district_stats["crimeStats"]["violentCrimes"]} violent')
                except (ValueError, AttributeError, KeyError) as e:
                    Actor.log.debug(f'Could not get district statistics: {e}')
    except Exception as e:
        Actor.log.error(f'Error extracting location: {e}')
    
    # Extract images
    images = []
    try:
        img_elements = soup.find_all('img', src=True)
        for img in img_elements:
            src = img.get('src', '')
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
    
    # Extract seller information
    seller_info = {}
    try:
        if 'bez realitky' in page_content.lower() or 'přímo majitel' in page_content.lower():
            seller_info['type'] = 'owner'
            seller_info['note'] = 'Prodává přímo majitel - bez provize'
        else:
            seller_info['type'] = 'agent'
        
        phone_match = re.search(r'\+420\s*\d{3}\s*\d{3}\s*\d{3}', page_content)
        if phone_match:
            seller_info['phone'] = clean_text(phone_match.group())
        
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', page_content)
        if email_match:
            seller_info['email'] = email_match.group()
    except Exception as e:
        Actor.log.debug(f'Error extracting seller info: {e}')
    
    # Build final data structure
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
            'pragueAdminDistrict': prague_admin_district,
        },
        'districtStats': district_stats,
        'propertyDetails': property_details,
        'attributes': attributes,
        'features': subtitle_features,
        'amenities': amenities,
        'images': images,
        'seller': seller_info,
        'breadcrumbs': breadcrumbs[:10] if breadcrumbs else [],
        'scrapedAt': page.url,
    }
    
    # Clean up empty values but keep structure
    data_cleaned = {}
    for key, value in data.items():
        if key in ['location', 'propertyDetails', 'seller']:
            data_cleaned[key] = value
        elif value not in [None, '', [], {}]:
            data_cleaned[key] = value
    
    return data_cleaned


async def handle_consent_page(page: Any, url: str, crawler_config: dict[str, Any]) -> bool:
    """Handle cookie consent page if present.
    
    Bezrealitky.cz typically doesn't have consent pages, but this is kept for compatibility.
    
    Args:
        page: Playwright page object
        url: Target URL
        crawler_config: Crawler configuration
    
    Returns:
        True (Bezrealitky doesn't typically have consent pages)
    """
    # Bezrealitky.cz doesn't typically have consent pages
    return True
