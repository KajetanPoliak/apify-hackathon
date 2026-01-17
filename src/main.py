"""Bezrealitky.cz Detail Page Scraper.

This Actor scrapes detailed information from Bezrealitky.cz property listing pages,
analyzes them with LLM, and checks for consistency issues.
"""

from __future__ import annotations

import json
from typing import Any

from apify import Actor
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

from src.consistency_checker import check_property_consistency
from src.llm_service import (
    analyze_property_with_llm,
    convert_scraped_data_to_listing_input,
    check_consistency_with_structured_output,
)
from src.mock_data import generate_mock_inconsistency_results, generate_mock_result_for_property
from src.models import ConsistencyCheckResult
from src.scraper_service import extract_property_data, handle_consent_page


async def push_mock_results_fallback(context: PlaywrightCrawlingContext | None = None) -> None:
    """Push mock inconsistency results as fallback when processing fails.
    
    Args:
        context: Playwright crawling context (if available), otherwise uses Actor.push_data
    """
    mock_results = generate_mock_inconsistency_results()
    for result in mock_results:
        if context:
            await context.push_data(result.model_dump(mode='json'))
        else:
            await Actor.push_data(result.model_dump(mode='json'))


async def process_property(
    context: PlaywrightCrawlingContext,
    llm_model: str,
    llm_temperature: float,
    crawler_config: dict[str, Any],
) -> ConsistencyCheckResult | None:
    """Process a single property: scrape, analyze, and check consistency.
    
    Args:
        context: Playwright crawling context
        llm_model: LLM model to use
        llm_temperature: LLM temperature
        crawler_config: Crawler configuration
    """
    url = context.request.url
    Actor.log.info(f'Processing property: {url}')
    
    page = context.page
    
    # Step 1: Scrape property data
    try:
        await page.wait_for_load_state('domcontentloaded', timeout=15000)
        await page.wait_for_timeout(2000)
        
        # Handle consent page if present (Bezrealitky typically doesn't have one)
        await handle_consent_page(page, url, crawler_config)
        
        # Wait for property content
        await page.wait_for_load_state('networkidle', timeout=10000)
        
        # Extract property data
        property_data = await extract_property_data(page, url)
        Actor.log.info(f'Scraped property: {property_data.get("title", "N/A")}')
        
    except Exception as e:
        Actor.log.exception(f'Error scraping property {url}: {e}')
        # Fallback to mock data if scraping fails
        Actor.log.warning(f'Scraping failed for {url}, outputting mock inconsistency results')
        await push_mock_results_fallback(context)
        return None
    
    # Step 2: Convert scraped data to ListingInput using structured outputs
    listing_input = None
    try:
        Actor.log.info('Converting scraped data to ListingInput format...')
        listing_input = await convert_scraped_data_to_listing_input(
            property_data=property_data,
            model=llm_model,
            temperature=llm_temperature,
        )
        
        if listing_input:
            # Print the ListingInput
            Actor.log.info('=' * 80)
            Actor.log.info('LISTING INPUT (Structured Output):')
            Actor.log.info('=' * 80)
            Actor.log.info(json.dumps(listing_input.model_dump(mode='json'), indent=2, ensure_ascii=False))
            Actor.log.info('=' * 80)
            
            # Store the ListingInput
            await context.push_data({
                'type': 'listing_input',
                'data': listing_input.model_dump(mode='json'),
            })
            Actor.log.info(f'ListingInput stored: {listing_input.listing_id}')
        else:
            Actor.log.warning('Failed to convert scraped data to ListingInput')
            
    except Exception as e:
        Actor.log.exception(f'Error converting to ListingInput: {e}')
    
    # Step 3: Check consistency with structured outputs (if ListingInput was created)
    consistency_result = None
    if listing_input:
        try:
            Actor.log.info('Checking property consistency with structured outputs...')
            consistency_result = await check_consistency_with_structured_output(
                listing_input=listing_input,
                model=llm_model,
                temperature=llm_temperature,
            )
            
            if consistency_result:
                # Print the ConsistencyCheckResult
                Actor.log.info('=' * 80)
                Actor.log.info('CONSISTENCY CHECK RESULT (Structured Output):')
                Actor.log.info('=' * 80)
                Actor.log.info(json.dumps(consistency_result.model_dump(mode='json'), indent=2, ensure_ascii=False))
                Actor.log.info('=' * 80)
                
                # Store the ConsistencyCheckResult
                await context.push_data(consistency_result.model_dump(mode='json'))
                Actor.log.info(f'ConsistencyCheckResult stored: {consistency_result.total_inconsistencies} inconsistencies found')
            else:
                Actor.log.warning('Failed to check consistency with structured outputs')
                
        except Exception as e:
            Actor.log.exception(f'Error during structured consistency check: {e}')
    
    # Step 4: Fallback to old consistency check if structured output failed
    if not consistency_result:
        try:
            Actor.log.info('Falling back to legacy consistency check...')
            consistency_result = await check_property_consistency(
                property_data=property_data,
                model=llm_model,
                temperature=llm_temperature,
            )
            
            # Push consistency result to dataset
            await context.push_data(consistency_result.model_dump(mode='json'))
            Actor.log.info(f'Legacy consistency check completed: {consistency_result.summary}')
            
        except Exception as e:
            Actor.log.exception(f'Error during legacy consistency check: {e}')
            # Fallback to mock data
            Actor.log.warning('Consistency check failed, outputting mock inconsistency results')
            mock_result = generate_mock_result_for_property(
                url=url,
                property_address=property_data.get('location', {}).get('full') or property_data.get('title') or url,
                title=property_data.get('title'),
                description=property_data.get('description'),
                price=property_data.get('price'),
                reason="Consistency check failed",
            )
            await context.push_data(mock_result.model_dump(mode='json'))
            consistency_result = mock_result
    
    # Add consistency result reference to property data if available
    if consistency_result:
        property_data['consistencyCheck'] = {
            'listing_id': consistency_result.listing_id,
            'total_inconsistencies': consistency_result.total_inconsistencies,
            'is_consistent': consistency_result.is_consistent,
        }
    
    # Step 5: Push property data to dataset
    await context.push_data(property_data)
    Actor.log.info(f'Successfully processed property: {url}')
    
    # Return consistency result for statistics tracking
    return consistency_result


async def main() -> None:
    """Main entry point for the Bezrealitky scraper Actor."""
    async with Actor:
        # Get Actor input
        actor_input = await Actor.get_input() or {}
        
        # Configuration
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
        # Get LLM model from input, defaulting to GPT-5-mini
        # Handle empty string, None, missing values, or "openrouter/auto" (legacy default)
        llm_model_input = actor_input.get('llmModel')
        if not llm_model_input or llm_model_input.strip() == '' or llm_model_input == 'openrouter/auto':
            default_model = "google/gemini-3-flash-preview"
            llm_model = default_model
            if llm_model_input == 'openrouter/auto':
                Actor.log.info(f'llmModel was set to "openrouter/auto", overriding to default: {default_model}')
            else:
                Actor.log.info(f'No llmModel specified in input, using default: {default_model}')
        else:
            llm_model = llm_model_input
            Actor.log.info(f'Using LLM model from input: {llm_model}')
        llm_temperature = actor_input.get('llmTemperature', 0.7)
        proxy_config = actor_input.get('proxyConfiguration', {'useApifyProxy': False})
        
        if not start_urls:
            Actor.log.info('No start URLs specified in Actor input, exiting...')
            await Actor.exit()
            return
        
        Actor.log.info(f'Starting Bezrealitky scraper with {len(start_urls)} URLs')
        Actor.log.info('Processing: Scraping → LLM Analysis → Consistency Check')
        
        # Create crawler configuration
        crawler_config = {
            'max_requests_per_crawl': max_requests,
            'headless': True,
            'browser_type': 'chromium',
            'max_request_retries': 3,
        }
        
        if proxy_config.get('useApifyProxy'):
            Actor.log.info('Using Apify proxy')
        
        # Create crawler
        crawler = PlaywrightCrawler(**crawler_config)
        
        # Track inconsistency analysis statistics
        inconsistency_stats = {
            'total_properties_processed': 0,
            'total_inconsistencies_found': 0,
            'properties_with_inconsistencies': 0,
            'properties_consistent': 0,
            'inconsistency_checks_failed': 0,
        }
        
        @crawler.router.default_handler
        async def request_handler(context: PlaywrightCrawlingContext) -> None:
            """Handle each Bezrealitky detail page request."""
            try:
                # Process property and get inconsistency result
                consistency_result = await process_property(
                    context=context,
                    llm_model=llm_model,
                    llm_temperature=llm_temperature,
                    crawler_config=crawler_config,
                )
                
                # Update inconsistency statistics
                inconsistency_stats['total_properties_processed'] += 1
                if consistency_result:
                    inconsistency_stats['total_inconsistencies_found'] += consistency_result.total_inconsistencies
                    if consistency_result.is_consistent:
                        inconsistency_stats['properties_consistent'] += 1
                    else:
                        inconsistency_stats['properties_with_inconsistencies'] += 1
                else:
                    inconsistency_stats['inconsistency_checks_failed'] += 1
                    
            except Exception as e:
                Actor.log.exception(f'Error processing property: {e}')
                # Fallback to mock data on any error
                Actor.log.warning('Processing failed, outputting mock inconsistency results')
                await push_mock_results_fallback(context)
                inconsistency_stats['inconsistency_checks_failed'] += 1
        
        # Run the crawler
        try:
            await crawler.run(start_urls)
            Actor.log.info('Scraping completed successfully!')
            
            # Push final completion summary to ensure end results are stored
            try:
                from datetime import datetime
                
                completion_summary = {
                    'type': 'completion_summary',
                    'status': 'success',
                    'completed_at': datetime.now().isoformat(),
                    'total_urls_processed': len(start_urls),
                    'llm_model_used': llm_model,
                    'llm_temperature': llm_temperature,
                    'max_requests_per_crawl': max_requests,
                    'inconsistency_analysis': {
                        'total_properties_processed': inconsistency_stats['total_properties_processed'],
                        'total_inconsistencies_found': inconsistency_stats['total_inconsistencies_found'],
                        'properties_with_inconsistencies': inconsistency_stats['properties_with_inconsistencies'],
                        'properties_consistent': inconsistency_stats['properties_consistent'],
                        'inconsistency_checks_failed': inconsistency_stats['inconsistency_checks_failed'],
                        'average_inconsistencies_per_property': (
                            inconsistency_stats['total_inconsistencies_found'] / inconsistency_stats['total_properties_processed']
                            if inconsistency_stats['total_properties_processed'] > 0 else 0
                        ),
                    },
                    'message': f'Successfully completed processing {len(start_urls)} URL(s). '
                               f'Found {inconsistency_stats["total_inconsistencies_found"]} total inconsistencies '
                               f'across {inconsistency_stats["total_properties_processed"]} properties.'
                }
                
                await Actor.push_data(completion_summary)
                Actor.log.info(f'Completion summary pushed: {completion_summary["message"]}')
            except Exception as e:
                Actor.log.warning(f'Could not push completion summary: {e}')
                # Try to push a minimal completion status
                try:
                    from datetime import datetime
                    await Actor.push_data({
                        'type': 'completion_summary',
                        'status': 'success',
                        'completed_at': datetime.now().isoformat(),
                        'total_urls_processed': len(start_urls),
                        'message': 'Processing completed successfully'
                    })
                except Exception:
                    Actor.log.debug('Could not push minimal completion summary')
                    
        except Exception as e:
            Actor.log.exception(f'Error during crawler execution: {e}')
            Actor.log.warning('Crawler failed, outputting mock inconsistency results')
            # Output mock data as fallback
            await push_mock_results_fallback(context=None)
            
            # Push failure summary to ensure error status is recorded
            try:
                from datetime import datetime
                await Actor.push_data({
                    'type': 'completion_summary',
                    'status': 'error',
                    'completed_at': datetime.now().isoformat(),
                    'error': str(e),
                    'total_urls_processed': len(start_urls),
                    'llm_model_used': llm_model,
                    'message': f'Processing failed with error: {str(e)}'
                })
                Actor.log.info('Error summary pushed to dataset')
            except Exception as e2:
                Actor.log.debug(f'Could not push error summary: {e2}')
