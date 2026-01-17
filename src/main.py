"""
Main entry point for the Apify Actor.

This actor demonstrates the basic structure and usage of the Apify Python SDK.
"""
import asyncio

from apify import Actor


async def main() -> None:
    """
    Main function that runs the actor.

    This function:
    1. Initializes the Actor
    2. Gets the input configuration
    3. Processes the input
    4. Stores results in the dataset
    """
    async with Actor:
        # Get the actor input
        actor_input = await Actor.get_input() or {}

        # Extract configuration
        start_urls = actor_input.get('startUrls', [])
        max_requests = actor_input.get('maxRequestsPerCrawl', 100)

        # Set status message
        await Actor.set_status_message(f'Starting actor with {len(start_urls)} start URLs')

        # Process start URLs
        processed_count = 0
        for url_item in start_urls:
            if processed_count >= max_requests:
                break

            url = url_item.get('url') if isinstance(url_item, dict) else url_item

            # Example: Push data to dataset
            await Actor.push_data({
                'url': url,
                'processed': True,
                'message': f'Processed URL: {url}',
            })

            processed_count += 1

            # Update status
            await Actor.set_status_message(f'Processed {processed_count}/{max_requests} requests')

        # Store final result in key-value store
        await Actor.set_value('OUTPUT', {
            'totalProcessed': processed_count,
            'status': 'SUCCEEDED',
        })

        # Exit successfully
        await Actor.exit(exit_code=0, status_message='Successfully completed processing')


if __name__ == '__main__':
    asyncio.run(main())
