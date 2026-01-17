"""LLM service for property analysis."""

import json
import os
from typing import Any

from openai import AsyncOpenAI

from apify import Actor


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
        
        # Call the LLM using OpenAI chat completions API
        completion = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        
        # Convert response to dict format
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
