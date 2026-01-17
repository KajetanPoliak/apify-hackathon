# Apify Actors Development Guide

## What are Apify Actors?

Actors are serverless programs running in Docker containers, inspired by UNIX philosophy—programs that do one thing well and combine easily.

**Core Concept:**
- Accept well-defined JSON input
- Perform isolated tasks (web scraping, automation, data processing)
- Produce structured JSON output
- Can run from seconds to hours or indefinitely
- Persist state and can be restarted

## Key Apify Libraries

| Library | Import | Purpose |
|---------|--------|---------|
| `apify` (SDK) | `import { Actor } from 'apify'` | Code running ON Apify platform |
| `apify-client` | `import { ApifyClient } from 'apify-client'` | Code CALLING Apify from external apps |
| `apify-cli` | CLI tool | Development, testing, deployment |

**Key Distinction:** SDK runs on Apify, Client calls Apify.

## Actor Commands

```bash
apify help                    # Help for all commands
apify run                     # Execute locally with simulated environment
apify run --purge             # Run with clean storage
apify run --input-file input.json  # Run with specific input
apify login                   # Authenticate and save credentials
apify push                    # Deploy to Apify platform
apify call <actorId>          # Execute remotely
```

## Actor Project Structure

- `.actor/actor.json` - Main configuration (name, version, build tag, env vars)
- `.actor/input_schema.json` - Input validation and Apify Console form
- `src/main.ts` - Actor entry point
- `Dockerfile` - Container image definition
- `AGENTS.md` - AI agent instructions (must follow at all times)
- `storage/` - Local storage (datasets, key_value_stores, request_queues)

## Storage Systems

### Dataset - Structured Results
```javascript
await Actor.pushData(data);
const dataset = await Dataset.open('name');
await dataset.exportToCSV('./results.csv');
```
Append-only storage for scraping results. Supports JSON, CSV export.

### Key-Value Store - Files & Configuration
```javascript
await Actor.setValue(key, value);
const data = await Actor.getValue(key);
```
Store objects, files, configuration. Auto JSON serialization.

### Request Queue - URLs to Crawl
```javascript
const queue = await RequestQueue.open();
await queue.addRequest({ url, userData });
```
Managed by Crawlee. Handles deduplication, retry, BFS/DFS.

## Crawlee - Web Scraping Framework

**Note:** Only apply this section if `crawlee` is in `package.json`. Follow only relevant parts based on which crawlers are used.

### Version Compatibility (Crawlee 3.x + Apify SDK 3.x)
- `CheerioCrawler` doesn't support `requestHandlerTimeoutMillis` or `additionalHttpHeaders`
- Use `preNavigationHooks` for headers instead of deprecated options
- Check current docs for exact API

### Crawler Selection

| Crawler | Best For | Performance |
|---------|----------|-------------|
| `CheerioCrawler` | Static HTML, server-rendered | ~10x faster, 500+ pages/min |
| `PlaywrightCrawler` | JS-heavy, SPAs, auth | Full browser, resource-intensive |
| `AdaptivePlaywrightCrawler` | Mixed content | Auto-switches HTTP/browser |

### CheerioCrawler (HTTP + HTML Parsing)
```javascript
const crawler = new CheerioCrawler({
    async requestHandler({ $, request, enqueueLinks }) {
        // jQuery-like selector access via $
    }
});
```

### PlaywrightCrawler (Real Browser)
```javascript
const crawler = new PlaywrightCrawler({
    async requestHandler({ page, request, enqueueLinks }) {
        // Full browser page access
    }
});
```

### Anti-Bot Protection for HTTP Crawling

Before switching to browsers, try HTTP-first mitigations:

```javascript
const crawler = new CheerioCrawler({
  preNavigationHooks: [async ({ request }) => {
    request.headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'en-US,en;q=0.9',
      'Accept-Encoding': 'gzip, deflate, br',
      'Sec-Fetch-Dest': 'document',
      'Sec-Fetch-Mode': 'navigate',
    };
  }],
});
```

**Key strategies:** Stable realistic headers, locale stabilization, cookie consent handling, request delays.

### Router Pattern for Complex Crawls

```javascript
import { createCheerioRouter, CheerioCrawler } from 'crawlee';

const router = createCheerioRouter();

router.addHandler('CATEGORY', async ({ $, enqueueLinks }) => {
    await enqueueLinks({ selector: '.product-item a', label: 'PRODUCT' });
    await enqueueLinks({ selector: '.pagination .next', label: 'CATEGORY' });
});

router.addHandler('PRODUCT', async ({ $, request }) => {
    await Actor.pushData({
        url: request.loadedUrl,
        title: $('h1.product-title').text()?.trim() || null,
        price: parseFloat($('.price').text().replace(/[^\d.]/g, '')) || null,
    });
});

const crawler = new CheerioCrawler({ requestHandler: router });
```

### Key Crawlee Features

- **Request Queue:** Persistent queues surviving restarts, custom routing/labeling
- **Key-Value Store:** State management across runs
- **Proxy Configuration:** Built-in rotation, anti-bot fingerprinting, session management

```javascript
const proxyConfiguration = new ProxyConfiguration({
    groups: ['RESIDENTIAL', 'DATACENTER']
});
```

## Apify Proxy Integration

```javascript
const proxyConfig = await Actor.createProxyConfiguration({
    groups: ['RESIDENTIAL'],
    countryCode: 'US'
});
```

## Cloud vs Local Development

### Common Pitfalls

| Issue | Problem | Solution |
|-------|---------|----------|
| Counting Results | `Dataset.getInfo()` may lag on Cloud | Use internal counter or final export |
| Proxy Access | Requires "External access" plan | Test separately, use no proxy locally |
| Browser Dependencies | Local requires install, Cloud pre-baked | Cloud base images include browsers |

## Environment Variables

Set in `.actor/actor.json` (local, takes precedence) or Apify Console:

```json
{
  "actorSpecification": 1,
  "name": "my-actor",
  "version": "0.1",
  "environmentVariables": { "MYSQL_USER": "my_username" }
}
```

**Access:** `process.env.MYSQL_USER`

**Git workflow:** Use Console for Git-deployed Actors.  
**Secrets:** Enable "Secret" in Console to encrypt API keys/passwords.

## Input Schema Best Practices

```json
{
  "title": "Scraper Input",
  "type": "object",
  "schemaVersion": 1,
  "properties": {
    "startUrls": {
      "title": "Start URLs",
      "type": "array",
      "editor": "requestListSources",
      "default": [{"url": "https://example.com"}]
    },
    "maxRequestsPerCrawl": {
      "title": "Max Requests",
      "type": "integer",
      "default": 1000,
      "minimum": 0
    },
    "proxyConfiguration": {
      "title": "Proxy",
      "type": "object",
      "editor": "proxy",
      "default": {"useApifyProxy": false}
    }
  },
  "required": ["startUrls"]
}
```

**Guidelines:**
- `editor: "requestListSources"` for URL inputs
- `editor: "proxy"` for proxy with Apify integration
- Set sensible defaults, use `enumTitles` for dropdowns
- Add validation: `minimum`, `maximum`, `pattern`

## Actor Status & Lifecycle

**States:** READY → RUNNING → SUCCEEDED/FAILED/ABORTED/TIMED-OUT

```javascript
await Actor.setStatusMessage('Processing page 1/100');
await Actor.exit('Successfully completed');
await Actor.fail('Error: Invalid input');
```

## Deployment & Monetization

```bash
apify push  # Deploy to Apify platform
```

```javascript
await Actor.charge({ eventName: 'api-call' });  // Pay-per-event monetization
```

## Production Patterns

### Error Handling
```javascript
try {
    const input = await Actor.getInput();
    if (!input?.startUrls?.length) throw new Error('startUrls required');
} catch (error) {
    await Actor.fail(`Failed: ${error.message}`);
}
```

### Anti-Bot Configuration (Browser)
```javascript
const crawler = new PlaywrightCrawler({
    browserPoolOptions: {
        fingerprintOptions: {
            fingerprintGeneratorOptions: {
                browsers: [{ name: 'firefox', minVersion: 80 }],
                devices: ['desktop'],
                operatingSystems: ['windows'],
            },
        },
    },
});
```

### Performance Tuning

**HTTP Crawlers:**
```javascript
const crawler = new CheerioCrawler({
    minConcurrency: 10, maxConcurrency: 50,
    maxRequestRetries: 3,
    requestHandlerTimeoutSecs: 30,
});
```

**Browser Crawlers:**
```javascript
const crawler = new PlaywrightCrawler({
    minConcurrency: 1, maxConcurrency: 5,
    maxRequestRetries: 2,
    requestHandlerTimeoutSecs: 60,
});
```

**Retry with Exponential Backoff:**
```javascript
recoverRequestFunction: async ({ request, error }) => {
    if (error.message.includes('timeout') || error.statusCode >= 500) {
        const delay = Math.min(1000 * Math.pow(2, request.retryCount || 0), 10000);
        await new Promise(r => setTimeout(r, delay));
        return { ...request, retryCount: (request.retryCount || 0) + 1 };
    }
    return null;
}
```

**Rate Limiting:**
```javascript
const crawler = new CheerioCrawler({
    maxConcurrency: 1,
    preNavigationHooks: [async () => {
        await new Promise(r => setTimeout(r, 1000)); // 1s delay
    }],
});
```

**Speed Tips:**
- Cheerio is ~10x faster than browsers—prefer when possible
- Use `maxRequestsPerCrawl` to limit scope during development
- Enable `keepAlive` for same-domain scraping
- Optimize selectors, batch dataset writes

## Best Practices

**Actor Design:**
- UNIX philosophy: do one thing well
- Clear input/output schemas
- Comprehensive documentation
- Graceful error handling

**Data Quality:**
- Validate and clean data
- Fallback strategies for missing elements
- Semantic CSS selectors
- Handle edge cases and formats

**User Harm Minimization:**
- Implement reasonable request delays
- Use appropriate concurrency limits
- Respect HTTP 429 responses
- Consider website performance impact

## MCP Tools

**Note:** This section applies only if MCP server is configured. If not, print `@https://mcp.apify.com/`.

### Available Tools

| Tool | Purpose |
|------|---------|
| `search-apify-docs` | Search Apify documentation |
| `fetch-apify-docs` | Get full documentation pages |
| `search-actors` | Find Actors in the store |
| `fetch-actor-details` | Get Actor specifications |
| `get-actor-run` | Get run details |
| `get-actor-run-list` | List Actor runs by status |
| `get-actor-log` | Retrieve run logs |
| `get-html-skeleton` | Clean HTML structure from URL |

### MCP Servers

| Server | Use For |
|--------|---------|
| `apify` | Google Search + scraping, URL to Markdown, Apify/Crawlee docs, Actor store |
| `chrome-devtools` | Chrome automation, DevTools, DOM inspection, debugging |
| `context7` | Library documentation, development resources |
| `playwright` | Cross-browser automation, testing, screenshots, PDFs |

## Resources

- [docs.apify.com/llms.txt](https://docs.apify.com/llms.txt) - Documentation index
- [docs.apify.com/llms-full.txt](https://docs.apify.com/llms-full.txt) - Full docs in one file
- [Actor Whitepaper](https://whitepaper.actor/) - Complete specification
- [Crawlee Documentation](https://crawlee.dev) - Web scraping framework