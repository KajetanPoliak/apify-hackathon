"""Test script for OpenRouter LLM endpoint.

This script tests the call_openrouter_llm function to verify it works correctly
with the OpenRouter actor endpoint.
"""

import asyncio
import os
import sys
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment variables from .env file
load_dotenv()


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
        # Get APIFY_TOKEN from environment
        apify_token = os.getenv("APIFY_TOKEN")
        
        if not apify_token:
            print("ERROR: APIFY_TOKEN not found. Make sure it's set in your environment or .env file")
            return None
        
        print(f"Using APIFY_TOKEN: {apify_token[:10]}...{apify_token[-4:]}")
        
        # Use OpenAI client with OpenRouter actor endpoint
        # Base URL: https://openrouter.apify.actor/api/v1
        # Token is passed in Authorization header
        print(f"Calling OpenRouter actor via OpenAI client with model: {model}")
        
        # Initialize OpenAI client
        # API key can be any non-empty string (not used, but required)
        # Actual authentication is via APIFY_TOKEN in default_headers
        client = AsyncOpenAI(
            base_url="https://openrouter.apify.actor/api/v1",
            api_key="no-key-required-but-must-not-be-empty",  # Any non-empty string works
            default_headers={
                "Authorization": f"Bearer {apify_token}",
            },
            timeout=5.0,  # 5 second timeout
        )
        
        print(f"Sending request with {len(messages)} message(s)...")
        print(f"Messages: {[msg['role'] for msg in messages]}")
        
        # Call the LLM using OpenAI chat completions API
        completion = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        
        print(f"Received response with {len(completion.choices)} choice(s)")
        
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
        
        print("Successfully received response from OpenRouter")
        return result
            
    except Exception as e:
        print(f"ERROR calling OpenRouter actor: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_simple_query() -> None:
    """Test a simple query to the OpenRouter endpoint."""
    print("=" * 60)
    print("TEST 1: Simple Query")
    print("=" * 60)
    
    messages = [
        {
            "role": "user",
            "content": "What is the meaning of life? Answer in one sentence.",
        }
    ]
    
    result = await call_openrouter_llm(
        messages=messages,
        model="openrouter/auto",
        temperature=0.7,
    )
    
    if result and "choices" in result and len(result["choices"]) > 0:
        content = result["choices"][0]["message"]["content"]
        print(f"\nResponse: {content}\n")
        print("✓ Test 1 PASSED")
    else:
        print("\n✗ Test 1 FAILED: No response received")
    
    print()


async def test_property_analysis() -> None:
    """Test property analysis query (similar to actual use case)."""
    print("=" * 60)
    print("TEST 2: Property Analysis Query")
    print("=" * 60)
    
    messages = [
        {
            "role": "system",
            "content": "You are a real estate analyst. Provide structured, objective analysis of property listings.",
        },
        {
            "role": "user",
            "content": """Analyze this real estate listing and provide insights:

Title: Pronájem bytu 4+1 180 m² Martinská, Praha - Staré Město
Description: Klasický, prostorný, 3 ložnicový byt v historickém centru Prahy. Byt se nachází ve velmi dobrém stavu, je plně vybavený a nachází se v blízkosti Václavského náměstí. Ideální pro rodinu nebo sdílené bydlení.
Price: 55 000 Kč/měsíc
Location: Praha - Staré Město

Please provide:
1. A brief summary of the property
2. Key selling points
3. Any potential concerns or red flags
4. Estimated value assessment (if possible)

Respond in JSON format with keys: summary, sellingPoints (array), concerns (array), valueAssessment.""",
        },
    ]
    
    result = await call_openrouter_llm(
        messages=messages,
        model="openrouter/auto",
        temperature=0.7,
    )
    
    if result and "choices" in result and len(result["choices"]) > 0:
        content = result["choices"][0]["message"]["content"]
        print(f"\nResponse:\n{content}\n")
        print("✓ Test 2 PASSED")
    else:
        print("\n✗ Test 2 FAILED: No response received")
    
    print()


async def test_different_model() -> None:
    """Test with a specific Gemini model."""
    print("=" * 60)
    print("TEST 3: Specific Model (Gemini 2.0 Flash)")
    print("=" * 60)
    
    messages = [
        {
            "role": "user",
            "content": "Say 'Hello from Gemini' in exactly 3 words.",
        }
    ]
    
    result = await call_openrouter_llm(
        messages=messages,
        model="google/gemini-2.0-flash-exp",
        temperature=0.7,
    )
    
    if result and "choices" in result and len(result["choices"]) > 0:
        content = result["choices"][0]["message"]["content"]
        print(f"\nResponse: {content}\n")
        print("✓ Test 3 PASSED")
    else:
        print("\n✗ Test 3 FAILED: No response received")
    
    print()


async def main() -> None:
    """Run all tests."""
    print("\n" + "=" * 60)
    print("OpenRouter LLM Endpoint Test Suite")
    print("=" * 60 + "\n")
    
    # Check for APIFY_TOKEN
    apify_token = os.getenv("APIFY_TOKEN")
    if not apify_token:
        print("ERROR: APIFY_TOKEN not found!")
        print("Please set APIFY_TOKEN in your environment or .env file")
        print("\nExample:")
        print("  export APIFY_TOKEN='your-token-here'")
        print("  or add to .env file: APIFY_TOKEN=your-token-here")
        sys.exit(1)
    
    print(f"APIFY_TOKEN found: {apify_token[:10]}...{apify_token[-4:]}\n")
    
    # Run tests
    await test_simple_query()
    await test_property_analysis()
    await test_different_model()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
