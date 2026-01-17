"""LLM service for property analysis."""

import json
import os
import re
from typing import Any

from openai import AsyncOpenAI

from apify import Actor
from src.models import ListingInput, ConsistencyCheckResult


def sanitize_json_schema_for_llm(schema: dict[str, Any]) -> dict[str, Any]:
    """Sanitize JSON schema to be compatible with LLM providers.
    
    Some LLM providers (like Azure) don't accept certain JSON schema formats.
    This function removes or fixes incompatible format specifications.
    
    Args:
        schema: JSON schema dictionary from Pydantic model
    
    Returns:
        Sanitized JSON schema compatible with LLM providers
    """
    if not isinstance(schema, dict):
        return schema
    
    # Create a copy to avoid modifying the original
    sanitized = schema.copy()
    
    # Remove or fix "uri" format (not recognized by some providers)
    if "format" in sanitized and sanitized["format"] == "uri":
        # Change to string type without format, or use "uri-reference" if supported
        sanitized.pop("format", None)
        if "type" not in sanitized:
            sanitized["type"] = "string"
    
    # Recursively sanitize nested structures
    if "properties" in sanitized:
        sanitized["properties"] = {
            key: sanitize_json_schema_for_llm(value)
            for key, value in sanitized["properties"].items()
        }
        
        # Azure requires all properties to be in the required array
        # Optional fields can still be null through their anyOf structure
        if "required" not in sanitized or not isinstance(sanitized["required"], list):
            sanitized["required"] = []
        
        # Add all properties to required array (Azure strict mode requirement)
        all_properties = set(sanitized["properties"].keys())
        current_required = set(sanitized["required"])
        sanitized["required"] = sorted(list(all_properties | current_required))
        
        # Azure requires additionalProperties to be explicitly set to false
        # This must be set for any object schema with properties
        sanitized["additionalProperties"] = False
    
    if "items" in sanitized:
        sanitized["items"] = sanitize_json_schema_for_llm(sanitized["items"])
    
    if "anyOf" in sanitized:
        sanitized["anyOf"] = [
            sanitize_json_schema_for_llm(item) for item in sanitized["anyOf"]
        ]
    
    if "oneOf" in sanitized:
        sanitized["oneOf"] = [
            sanitize_json_schema_for_llm(item) for item in sanitized["oneOf"]
        ]
    
    if "allOf" in sanitized:
        sanitized["allOf"] = [
            sanitize_json_schema_for_llm(item) for item in sanitized["allOf"]
        ]
    
    # Handle definitions/defs (for schema references)
    if "definitions" in sanitized:
        sanitized["definitions"] = {
            key: sanitize_json_schema_for_llm(value)
            for key, value in sanitized["definitions"].items()
        }
    
    if "$defs" in sanitized:
        sanitized["$defs"] = {
            key: sanitize_json_schema_for_llm(value)
            for key, value in sanitized["$defs"].items()
        }
    
    return sanitized


async def call_openrouter_llm(
    messages: list[dict[str, str]],
    model: str = "openrouter/auto",
    temperature: float = 0.7,
    response_format: dict[str, Any] | None = None,
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
        apify_token = None
        try:
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
        
        Actor.log.info(f"Calling OpenRouter actor via OpenAI client with model: {model}")
        
        # Initialize OpenAI client
        client = AsyncOpenAI(
            base_url="https://openrouter.apify.actor/api/v1",
            api_key="no-key-required-but-must-not-be-empty",
            default_headers={
                "Authorization": f"Bearer {apify_token}",
            },
            timeout=5.0,
        )
        
        # Prepare request parameters
        request_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        # Add response_format if provided (for structured outputs)
        if response_format:
            request_params["response_format"] = response_format
        
        # Call the LLM using OpenAI chat completions API
        completion = await client.chat.completions.create(**request_params)
        
        # Convert response to dict format
        # Handle structured outputs - content may be in message.content or elsewhere
        result = {
            "choices": []
        }
        for choice in completion.choices:
            choice_dict = {
                "message": {
                    "role": choice.message.role,
                    "content": choice.message.content if hasattr(choice.message, 'content') else None,
                }
            }
            # Check for tool_calls (some models use this for structured outputs)
            if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                choice_dict["message"]["tool_calls"] = [
                    {
                        "function": {
                            "name": tc.function.name if hasattr(tc.function, 'name') else None,
                            "arguments": tc.function.arguments if hasattr(tc.function, 'arguments') else None,
                        }
                    }
                    for tc in choice.message.tool_calls
                ]
            result["choices"].append(choice_dict)
        
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
    
    Args:
        property_data: Dictionary containing property information (title, description, price, etc.)
        model: Model to use
        temperature: LLM temperature
    
    Returns:
        Analysis result from LLM, or None on error
    """
    # Format location - can be dict with 'full' key or string
    location = property_data.get('location', 'N/A')
    if isinstance(location, dict):
        location_str = location.get('full') or location.get('city') or str(location)
    else:
        location_str = location or 'N/A'
    
    # Build prompt for property analysis
    prompt = f"""Analyze this real estate listing and provide insights:

Title: {property_data.get('title', 'N/A')}
Description: {property_data.get('description', 'N/A')}
Price: {property_data.get('price', 'N/A')}
Location: {location_str}
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


async def check_consistency_with_llm(
    property_data: dict[str, Any],
    model: str = "openrouter/auto",
    temperature: float = 0.7,
) -> dict[str, Any] | None:
    """Check property listing consistency using LLM.
    
    Args:
        property_data: Dictionary containing property information
        model: Model to use
        temperature: LLM temperature
    
    Returns:
        Consistency check result from LLM, or None on error
    """
    # Build prompt for consistency checking
    prompt = f"""Check this real estate listing for internal consistency between the description and structured data:

Title: {property_data.get('title', 'N/A')}
Description: {property_data.get('description', 'N/A')}
Price: {property_data.get('price', 'N/A')}
Attributes: {json.dumps(property_data.get('attributes', {}), ensure_ascii=False)}

Please identify any inconsistencies between what the description claims and what the structured data shows.
Look for mismatches in:
- Property size/area
- Number of rooms/bedrooms/bathrooms
- Property type
- Features (pool, garage, etc.)
- Price information
- Condition/state
- Year built

Respond in JSON format with keys: inconsistencies (array of objects with field_name, description_says, listing_data_says, severity, explanation).
"""
    
    messages = [
        {
            "role": "system",
            "content": "You are a real estate data quality analyst. Identify inconsistencies between property descriptions and structured data.",
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


def extract_number_from_text(text: str | None) -> int | None:
    """Extract first number from text string."""
    if not text:
        return None
    match = re.search(r'\d+', str(text))
    return int(match.group()) if match else None


def extract_float_from_text(text: str | None) -> float | None:
    """Extract first float number from text string."""
    if not text:
        return None
    match = re.search(r'\d+\.?\d*', str(text))
    return float(match.group()) if match else None


async def convert_scraped_data_to_listing_input(
    property_data: dict[str, Any],
    model: str = "openrouter/auto",
    temperature: float = 0.7,
) -> ListingInput | None:
    """Convert scraped property data to ListingInput format using structured outputs.
    
    Args:
        property_data: Dictionary containing scraped property information
        model: LLM model to use
        temperature: LLM temperature
    
    Returns:
        ListingInput object, or None on error
    """
    # Format location - can be dict with 'full' key or string
    location = property_data.get('location', {})
    if isinstance(location, dict):
        location_str = location.get('full') or location.get('city') or 'N/A'
        city = location.get('city') or 'Prague'
        district = location.get('district') or ''
    else:
        location_str = location or 'N/A'
        city = 'Prague'
        district = ''
    
    # Extract property details
    property_details = property_data.get('propertyDetails', {})
    area_str = property_details.get('area') or property_data.get('attributes', {}).get('Užitná plocha', '')
    disposition = property_details.get('disposition') or property_data.get('attributes', {}).get('Dispozice', '')
    
    # Extract numbers from text
    area_sqm = extract_number_from_text(area_str)
    # Use square meters directly (no conversion needed)
    square_meters = area_sqm
    
    # Extract bedrooms from disposition (e.g., "3+kk" -> 3)
    bedrooms = extract_number_from_text(disposition) or 0
    
    # Extract price with better parsing
    price_str = property_data.get('price', '')
    # Try to extract price - handle Czech format with spaces (e.g., "8 499 000 Kč")
    price_value = None
    if price_str:
        # Remove all spaces and non-digit characters except decimal point
        price_clean = re.sub(r'[^\d.]', '', price_str.replace(' ', '').replace('​', ''))
        if price_clean:
            try:
                price_value = float(price_clean)
            except ValueError:
                pass
    
    # Fallback: try to extract from attributes
    if not price_value:
        price_per_m2 = property_details.get('pricePerM2') or property_data.get('attributes', {}).get('Cena za jednotku', '')
        if price_per_m2:
            price_clean = re.sub(r'[^\d.]', '', str(price_per_m2).replace(' ', '').replace('​', ''))
            if price_clean:
                try:
                    price_per_m2_value = float(price_clean)
                    # Estimate total price from price per m² and area
                    if area_sqm and price_per_m2_value:
                        price_value = price_per_m2_value * area_sqm
                except ValueError:
                    pass
    
    # Generate listing ID from URL
    import hashlib
    url = property_data.get('url', '')
    listing_id = hashlib.md5(url.encode()).hexdigest()[:12].upper()
    listing_id = f"PRG-{listing_id}"
    
    # Build prompt for conversion
    prompt = f"""Convert this scraped real estate listing data into a structured ListingInput format.

Scraped Data:
- URL: {url}
- Title: {property_data.get('title', 'N/A')}
- Description: {property_data.get('description', 'N/A')}
- Price: {price_str}
- Location: {location_str}
- Area: {area_str}
- Disposition: {disposition}
- Property Details: {json.dumps(property_details, ensure_ascii=False)}
- Attributes: {json.dumps(property_data.get('attributes', {}), ensure_ascii=False)}
- Amenities: {json.dumps(property_data.get('amenities', []), ensure_ascii=False)}

CRITICAL CONSTRAINTS - MUST FOLLOW:
- list_price: MUST be greater than 0. Extract numeric value from price string (e.g., "8 499 000 Kč" -> 8499000.0). 
  If price is missing, calculate from pricePerM2 × area, or use a reasonable estimate (minimum 1,000,000 CZK for apartments).
  NEVER use 0.0 or negative values.
- bedrooms: MUST be 0 or greater. Extract from disposition (e.g., "3+kk" = 3 bedrooms).
- bathrooms: MUST be 0 or greater. Typically 1-2 for Czech apartments.
- description: MUST be at least 10 characters. Use scraped description or create a summary.
- square_meters: If provided, MUST be 0 or greater. Extract from area (already in m²).
- year_built: If provided, MUST be between 1800 and 2030.

Instructions:
1. Extract all available information from the scraped data
2. Map Czech property data to the ListingInput format
3. For missing required fields, use reasonable defaults:
   - state: "Czech Republic" or "CZ"
   - zip_code: "00000" if not available
   - bedrooms: Extract from disposition (e.g., "3+kk" = 3 bedrooms), default to 1 if unknown
   - bathrooms: Estimate from disposition (typically 1-2 for Czech apartments), default to 1.0 if unknown
   - square_meters: Extract from area (already in m², no conversion needed)
   - list_price: Extract numeric value from price string. If missing, estimate from pricePerM2 × area or use minimum 1,000,000 CZK
4. Set listing_id to: {listing_id}
5. Set listing_url to the scraped URL
6. Extract property_address from location or title
7. Extract city from location
8. Check amenities for features (has_garage, has_basement, etc.)

Return a complete ListingInput object with all fields properly filled and all constraints satisfied.
"""
    
    # Get JSON schema from Pydantic model and sanitize it for LLM compatibility
    listing_input_schema_raw = ListingInput.model_json_schema()
    listing_input_schema = sanitize_json_schema_for_llm(listing_input_schema_raw)
    
    messages = [
        {
            "role": "system",
            "content": """You are a data transformation expert. Convert scraped real estate data into structured ListingInput format.

CRITICAL: You MUST follow all field constraints:
- list_price: MUST be greater than 0 (never 0.0 or negative)
- bedrooms: MUST be 0 or greater
- bathrooms: MUST be 0 or greater  
- description: MUST be at least 10 characters
- year_built: If provided, MUST be between 1800 and 2030
- square_meters: If provided, MUST be 0 or greater

Always return valid JSON matching the schema exactly with all constraints satisfied.""",
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]
    
    # Use structured output with JSON schema
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "listing_input",
            "strict": True,
            "schema": listing_input_schema,
        }
    }
    
    try:
        Actor.log.info("Converting scraped data to ListingInput using structured outputs...")
        llm_result = await call_openrouter_llm(
            messages=messages,
            model=model,
            temperature=temperature,
            response_format=response_format,
        )
        
        if llm_result and 'choices' in llm_result and len(llm_result['choices']) > 0:
            choice = llm_result['choices'][0]
            
            # Get content from dict response
            content = None
            message = choice.get('message', {}) if isinstance(choice, dict) else getattr(choice, 'message', {})
            
            if isinstance(message, dict):
                # Check for refusal
                if message.get('refusal'):
                    Actor.log.warning(f"LLM refused request: {message.get('refusal')}")
                    return None
                
                # Get content from message dict
                content = message.get('content')
                
                # Check for tool_calls (some models use this for structured outputs)
                if not content and message.get('tool_calls'):
                    for tool_call in message['tool_calls']:
                        func = tool_call.get('function', {})
                        if func.get('arguments'):
                            content = func['arguments']
                            break
            else:
                # Handle object-style response
                if hasattr(message, 'refusal') and message.refusal:
                    Actor.log.warning(f"LLM refused request: {message.refusal}")
                    return None
                
                if hasattr(message, 'content') and message.content:
                    content = message.content
                elif hasattr(message, 'tool_calls') and message.tool_calls:
                    for tool_call in message.tool_calls:
                        if hasattr(tool_call, 'function') and hasattr(tool_call.function, 'arguments'):
                            content = tool_call.function.arguments
                            break
            
            if not content:
                Actor.log.warning("No content in LLM response")
                return None
            
            # Parse JSON content
            if isinstance(content, str):
                try:
                    listing_data = json.loads(content)
                except json.JSONDecodeError:
                    Actor.log.warning(f"Failed to parse JSON from LLM response: {content[:200]}")
                    return None
            else:
                listing_data = content
            
            # Validate and fix data before creating ListingInput
            # Fix list_price if invalid (must be > 0)
            if listing_data.get('list_price') is None or listing_data.get('list_price', 0) <= 0:
                Actor.log.warning(f"Invalid list_price from LLM: {listing_data.get('list_price')}, attempting to fix...")
                # Try to use extracted price value
                if price_value and price_value > 0:
                    listing_data['list_price'] = price_value
                    Actor.log.info(f"Fixed list_price using extracted value: {price_value}")
                else:
                    # Calculate from price per m² if available
                    price_per_m2 = property_details.get('pricePerM2') or property_data.get('attributes', {}).get('Cena za jednotku', '')
                    if price_per_m2 and area_sqm:
                        price_clean = re.sub(r'[^\d.]', '', str(price_per_m2).replace(' ', '').replace('​', ''))
                        if price_clean:
                            try:
                                price_per_m2_value = float(price_clean)
                                calculated_price = price_per_m2_value * area_sqm
                                if calculated_price > 0:
                                    listing_data['list_price'] = calculated_price
                                    Actor.log.info(f"Fixed list_price using calculated value: {calculated_price}")
                                else:
                                    listing_data['list_price'] = 1000000.0  # Minimum fallback
                                    Actor.log.warning(f"Using minimum fallback price: 1000000.0")
                            except (ValueError, TypeError):
                                listing_data['list_price'] = 1000000.0  # Minimum fallback
                                Actor.log.warning(f"Using minimum fallback price: 1000000.0")
                    else:
                        # Use minimum reasonable price for Czech apartments
                        listing_data['list_price'] = 1000000.0
                        Actor.log.warning(f"Using minimum fallback price: 1000000.0")
            
            # Fix description if too short
            if listing_data.get('description'):
                desc = listing_data['description']
                if len(desc) < 10:
                    Actor.log.warning(f"Description too short ({len(desc)} chars), extending...")
                    # Use title or create a basic description
                    title = property_data.get('title', '')
                    if title and len(title) >= 10:
                        listing_data['description'] = title
                    else:
                        listing_data['description'] = f"Property listing in {city}. {desc}"[:500]
            
            # Ensure bedrooms and bathrooms are valid
            if listing_data.get('bedrooms') is None or listing_data.get('bedrooms', -1) < 0:
                listing_data['bedrooms'] = max(0, bedrooms)  # Use extracted value or 0
            if listing_data.get('bathrooms') is None or listing_data.get('bathrooms', -1) < 0:
                listing_data['bathrooms'] = 1.0  # Default to 1 bathroom
            
            # Fix year_built if out of range
            if listing_data.get('year_built') is not None:
                year = listing_data['year_built']
                if year < 1800 or year > 2030:
                    Actor.log.warning(f"Year built out of range: {year}, setting to None")
                    listing_data['year_built'] = None
            
            # Create ListingInput from parsed and validated data
            try:
                listing_input = ListingInput(**listing_data)
                Actor.log.info(f"Successfully converted to ListingInput: {listing_input.listing_id}")
                return listing_input
            except Exception as e:
                Actor.log.exception(f"Failed to create ListingInput from LLM response: {e}")
                Actor.log.debug(f"LLM response data: {listing_data}")
                return None
        else:
            Actor.log.warning("LLM returned no result")
            return None
            
    except Exception as e:
        Actor.log.exception(f"Error converting scraped data to ListingInput: {e}")
        return None


async def check_consistency_with_structured_output(
    listing_input: ListingInput,
    model: str = "openrouter/auto",
    temperature: float = 0.7,
) -> ConsistencyCheckResult | None:
    """Check property listing consistency using structured outputs.
    
    Args:
        listing_input: ListingInput object to check for consistency
        model: LLM model to use
        temperature: LLM temperature
    
    Returns:
        ConsistencyCheckResult object, or None on error
    """
    # Build prompt for consistency checking
    prompt = f"""Check this real estate listing for internal consistency between the description and structured data.

Listing Data:
- Listing ID: {listing_input.listing_id}
- Address: {listing_input.property_address}
- City: {listing_input.city}
- Bedrooms: {listing_input.bedrooms}
- Bathrooms: {listing_input.bathrooms}
- Square Meters: {listing_input.square_meters}
- List Price: {listing_input.list_price}
- Property Type: {listing_input.property_type}
- Year Built: {listing_input.year_built}
- Features: Pool={listing_input.has_pool}, Garage={listing_input.has_garage}, Basement={listing_input.has_basement}, Fireplace={listing_input.has_fireplace}

Description:
{listing_input.description}

Please identify any inconsistencies between what the description claims and what the structured data shows.
Look for mismatches in:
- Property size/area (description vs square_meters)
- Number of rooms/bedrooms/bathrooms
- Property type
- Features (pool, garage, basement, fireplace)
- Price information
- Condition/state
- Year built
- Location details

Return a ConsistencyCheckResult with all findings properly categorized by severity.
"""
    
    # Get JSON schema from Pydantic model and sanitize it for LLM compatibility
    consistency_check_schema_raw = ConsistencyCheckResult.model_json_schema()
    consistency_check_schema = sanitize_json_schema_for_llm(consistency_check_schema_raw)
    
    messages = [
        {
            "role": "system",
            "content": "You are a real estate data quality analyst. Identify inconsistencies between property descriptions and structured data. Always return valid JSON matching the schema exactly.",
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]
    
    # Use structured output with JSON schema
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "consistency_check_result",
            "strict": True,
            "schema": consistency_check_schema,
        }
    }
    
    try:
        Actor.log.info("Checking consistency with structured outputs...")
        llm_result = await call_openrouter_llm(
            messages=messages,
            model=model,
            temperature=temperature,
            response_format=response_format,
        )
        
        if llm_result and 'choices' in llm_result and len(llm_result['choices']) > 0:
            choice = llm_result['choices'][0]
            
            # Get content from dict response
            content = None
            message = choice.get('message', {}) if isinstance(choice, dict) else getattr(choice, 'message', {})
            
            if isinstance(message, dict):
                # Check for refusal
                if message.get('refusal'):
                    Actor.log.warning(f"LLM refused request: {message.get('refusal')}")
                    return None
                
                # Get content from message dict
                content = message.get('content')
                
                # Check for tool_calls (some models use this for structured outputs)
                if not content and message.get('tool_calls'):
                    for tool_call in message['tool_calls']:
                        func = tool_call.get('function', {})
                        if func.get('arguments'):
                            content = func['arguments']
                            break
            else:
                # Handle object-style response
                if hasattr(message, 'refusal') and message.refusal:
                    Actor.log.warning(f"LLM refused request: {message.refusal}")
                    return None
                
                if hasattr(message, 'content') and message.content:
                    content = message.content
                elif hasattr(message, 'tool_calls') and message.tool_calls:
                    for tool_call in message.tool_calls:
                        if hasattr(tool_call, 'function') and hasattr(tool_call.function, 'arguments'):
                            content = tool_call.function.arguments
                            break
            
            if not content:
                Actor.log.warning("No content in LLM response")
                return None
            
            # Parse JSON content
            if isinstance(content, str):
                try:
                    consistency_data = json.loads(content)
                except json.JSONDecodeError:
                    Actor.log.warning(f"Failed to parse JSON from LLM response: {content[:200]}")
                    return None
            else:
                consistency_data = content
            
            # Create ConsistencyCheckResult from parsed data
            try:
                # Ensure checked_at is set if not provided
                if 'checked_at' not in consistency_data:
                    from datetime import datetime
                    consistency_data['checked_at'] = datetime.now().isoformat()
                
                consistency_result = ConsistencyCheckResult(**consistency_data)
                Actor.log.info(f"Successfully created ConsistencyCheckResult: {consistency_result.total_inconsistencies} inconsistencies found")
                return consistency_result
            except Exception as e:
                Actor.log.exception(f"Failed to create ConsistencyCheckResult from LLM response: {e}")
                Actor.log.debug(f"LLM response data: {consistency_data}")
                return None
        else:
            Actor.log.warning("LLM returned no result")
            return None
            
    except Exception as e:
        Actor.log.exception(f"Error checking consistency with structured outputs: {e}")
        return None
