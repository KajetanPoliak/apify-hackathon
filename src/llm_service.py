"""LLM service for property analysis."""

import json
import os
import re
from typing import Any

from openai import AsyncOpenAI

from apify import Actor
from src.models import ListingInput, ConsistencyCheckResult


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
    # Convert m² to square feet (1 m² = 10.764 sqft)
    square_feet = int(area_sqm * 10.764) if area_sqm else None
    
    # Extract bedrooms from disposition (e.g., "3+kk" -> 3)
    bedrooms = extract_number_from_text(disposition) or 0
    
    # Extract price
    price_str = property_data.get('price', '')
    price_match = re.search(r'(\d+[\s​]+\d+[\s​]+\d+|\d+)', price_str.replace(' ', '').replace('​', ''))
    list_price = float(price_match.group(1).replace(' ', '')) if price_match else 0.0
    
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

Instructions:
1. Extract all available information from the scraped data
2. Map Czech property data to the ListingInput format
3. For missing required fields, use reasonable defaults:
   - state: "Czech Republic" or "CZ"
   - zip_code: "00000" if not available
   - bedrooms: Extract from disposition (e.g., "3+kk" = 3 bedrooms)
   - bathrooms: Estimate from disposition (typically 1-2 for Czech apartments)
   - square_feet: Convert from m² (1 m² = 10.764 sqft)
   - list_price: Extract numeric value from price string
4. Set listing_id to: {listing_id}
5. Set listing_url to the scraped URL
6. Extract property_address from location or title
7. Extract city from location
8. Check amenities for features (has_garage, has_basement, etc.)

Return a complete ListingInput object with all fields properly filled.
"""
    
    # Get JSON schema from Pydantic model
    listing_input_schema = ListingInput.model_json_schema()
    
    messages = [
        {
            "role": "system",
            "content": "You are a data transformation expert. Convert scraped real estate data into structured ListingInput format. Always return valid JSON matching the schema exactly.",
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
            
            # Create ListingInput from parsed data
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
- Square Feet: {listing_input.square_feet}
- List Price: {listing_input.list_price}
- Property Type: {listing_input.property_type}
- Year Built: {listing_input.year_built}
- Features: Pool={listing_input.has_pool}, Garage={listing_input.has_garage}, Basement={listing_input.has_basement}, Fireplace={listing_input.has_fireplace}

Description:
{listing_input.description}

Please identify any inconsistencies between what the description claims and what the structured data shows.
Look for mismatches in:
- Property size/area (description vs square_feet)
- Number of rooms/bedrooms/bathrooms
- Property type
- Features (pool, garage, basement, fireplace)
- Price information
- Condition/state
- Year built
- Location details

Return a ConsistencyCheckResult with all findings properly categorized by severity.
"""
    
    # Get JSON schema from Pydantic model
    consistency_check_schema = ConsistencyCheckResult.model_json_schema()
    
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
