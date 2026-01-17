"""Consistency checker for property listings."""

import json
from datetime import datetime
from typing import Any

from apify import Actor

from src.llm_service import check_consistency_with_llm
from src.mock_data import generate_mock_result_for_property
from src.models import ConsistencyCheckResult, InconsistencyFinding, SeverityLevel


async def check_property_consistency(
    property_data: dict[str, Any],
    model: str = "openrouter/openai/gpt-4o",
    temperature: float = 0.7,
) -> ConsistencyCheckResult:
    """Check property listing for internal consistency.
    
    Attempts to use LLM to check consistency. If LLM fails, returns mock data.
    
    Args:
        property_data: Dictionary containing property information
        model: LLM model to use
        temperature: LLM temperature
    
    Returns:
        ConsistencyCheckResult object
    """
    url = property_data.get('url', '')
    title = property_data.get('title')
    description = property_data.get('description')
    price = property_data.get('price')
    location = property_data.get('location')
    
    # Handle location - can be dict with 'full' key or string
    if isinstance(location, dict):
        property_address = location.get('full') or title or url
    elif isinstance(location, str):
        property_address = location or title or url
    else:
        property_address = title or url
    
    # Try to use LLM for consistency checking
    try:
        Actor.log.info('Checking property consistency with LLM...')
        llm_result = await check_consistency_with_llm(
            property_data=property_data,
            model=model,
            temperature=temperature,
        )
        
        if llm_result and 'choices' in llm_result and len(llm_result['choices']) > 0:
            content = llm_result['choices'][0].get('message', {}).get('content', '')
            
            try:
                # Try to parse LLM response as JSON
                analysis = json.loads(content)
                inconsistencies = analysis.get('inconsistencies', [])
                
                # Convert LLM inconsistencies to InconsistencyFinding objects
                findings = []
                for inc in inconsistencies:
                    severity_str = inc.get('severity', 'medium').lower()
                    severity = SeverityLevel.MEDIUM
                    if severity_str == 'critical':
                        severity = SeverityLevel.CRITICAL
                    elif severity_str == 'low':
                        severity = SeverityLevel.LOW
                    
                    findings.append(
                        InconsistencyFinding(
                            field_name=inc.get('field_name', 'unknown'),
                            description_says=inc.get('description_says', 'N/A'),
                            listing_data_says=inc.get('listing_data_says', 'N/A'),
                            severity=severity,
                            explanation=inc.get('explanation', 'No explanation provided'),
                        )
                    )
                
                # Generate listing ID from URL
                from src.utils import generate_listing_id_from_url
                listing_id = generate_listing_id_from_url(url)
                
                result = ConsistencyCheckResult(
                    listing_id=listing_id,
                    property_address=property_address,
                    checked_at=datetime.now(),
                    total_inconsistencies=len(findings),
                    is_consistent=len(findings) == 0,
                    findings=findings,
                    summary=f"Found {len(findings)} inconsistency(ies) via LLM analysis" if findings else "No inconsistencies found via LLM analysis"
                )
                
                Actor.log.info(f'LLM consistency check completed: {len(findings)} inconsistencies found')
                return result
                
            except json.JSONDecodeError:
                Actor.log.warning('LLM response was not valid JSON, falling back to mock data')
                # Fall through to mock data generation
        
        else:
            Actor.log.warning('LLM returned no result, falling back to mock data')
            # Fall through to mock data generation
            
    except Exception as e:
        Actor.log.exception(f'Error during LLM consistency check: {e}')
        Actor.log.warning('Falling back to mock data due to LLM error')
        # Fall through to mock data generation
    
    # Fallback to mock data if LLM fails
    Actor.log.info('Generating mock inconsistency result as fallback')
    return generate_mock_result_for_property(
        url=url,
        property_address=property_address,
        title=title,
        description=description,
        price=price,
        reason="LLM consistency check failed or unavailable",
    )
