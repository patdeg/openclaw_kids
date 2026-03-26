# Tavily - Web Search & Content Extraction

AI-optimized web search and content extraction via Tavily API.

## Web Access Decision Tree

| Goal | Tool |
|------|------|
| Search the web (unknown URL) | Tavily **Search** |
| Get clean markdown/content from a known URL | Tavily **Extract** |
| Get raw HTML from a known URL | `web_fetch` (built-in) |
| JS-rendered pages / browser automation / live prices / booking | `browser` (built-in — ALWAYS available) |

**Never use `web_search` (Brave API) — always use Tavily for search.**
**Never claim the `browser` tool is unavailable — it is a built-in OpenClaw tool running local Chromium.**

## Overview

Tavily provides:
- **Search** - Web search across general, news, or finance topics
- **Extract** - Pull clean markdown content from any URL

## Credentials

Environment variable: `TAVILY_API_KEY`

Get a free key at: https://app.tavily.com

## Search Endpoint

### Basic Search

```bash
curl -s -X POST "https://api.tavily.com/search" \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "YOUR_SEARCH_QUERY"
  }' | jq '.results[] | {title, url, content}'
```

### Search with Topic Filter

**Topics:**
- `general` - Broad web search (default)
- `news` - Real-time news, politics, sports, events
- `finance` - Financial data, stocks, markets

```bash
# News search
curl -s -X POST "https://api.tavily.com/search" \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "latest tech news",
    "topic": "news",
    "max_results": 5
  }' | jq '.results[] | {title, url, content}'
```

```bash
# Finance search
curl -s -X POST "https://api.tavily.com/search" \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "NVIDIA stock analysis",
    "topic": "finance",
    "max_results": 5
  }' | jq '.results[] | {title, url, content}'
```

### Advanced Search with AI Answer

```bash
curl -s -X POST "https://api.tavily.com/search" \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the current price of Bitcoin?",
    "topic": "finance",
    "search_depth": "advanced",
    "include_answer": "advanced",
    "max_results": 5
  }' | jq '{answer, results: [.results[] | {title, url, content}]}'
```

### Search Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Search query |
| `topic` | enum | `general` | `general`, `news`, or `finance` |
| `search_depth` | enum | `basic` | `ultra-fast`, `fast`, `basic`, `advanced` |
| `max_results` | int | 5 | Number of results (0-20) |
| `include_answer` | bool/string | false | `true`, `"basic"`, or `"advanced"` for AI summary |
| `include_raw_content` | string | null | `"markdown"` or `"text"` for full page content |
| `time_range` | string | null | `day`, `week`, `month`, `year` |
| `include_domains` | array | null | Only search these domains |
| `exclude_domains` | array | null | Exclude these domains |

## Extract Endpoint

Pull clean content from any URL in markdown format.

### Basic Extract

```bash
curl -s -X POST "https://api.tavily.com/extract" \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": "https://example.com/article"
  }' | jq '.results[0].raw_content'
```

### Extract Multiple URLs

```bash
curl -s -X POST "https://api.tavily.com/extract" \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://example.com/page1",
      "https://example.com/page2"
    ],
    "format": "markdown"
  }' | jq '.results[] | {url, raw_content}'
```

### Extract with Query (Relevant Chunks)

```bash
curl -s -X POST "https://api.tavily.com/extract" \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": "https://en.wikipedia.org/wiki/San_Diego",
    "query": "population and climate",
    "chunks_per_source": 3,
    "format": "markdown"
  }' | jq '.results[0].raw_content'
```

### Extract Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `urls` | string/array | required | URL(s) to extract (max 20) |
| `query` | string | null | Focus extraction on relevant content |
| `chunks_per_source` | int | 3 | Chunks per URL (1-5), requires query |
| `extract_depth` | enum | `basic` | `basic` or `advanced` |
| `format` | enum | `markdown` | `markdown` or `text` |
| `include_images` | bool | false | Include image URLs |
| `timeout` | float | 10/30 | Timeout in seconds |

## Usage Patterns

### Research a Topic
```bash
# 1. Search for sources
curl -s -X POST "https://api.tavily.com/search" \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "best restaurants in San Diego", "max_results": 3}' \
  | jq '.results[] | .url'

# 2. Extract full content from best result
curl -s -X POST "https://api.tavily.com/extract" \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"urls": "https://found-url.com/article", "format": "markdown"}' \
  | jq -r '.results[0].raw_content'
```

### Get Quick Answer with Sources
```bash
curl -s -X POST "https://api.tavily.com/search" \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "When is the next SpaceX launch?",
    "include_answer": "advanced",
    "topic": "news",
    "max_results": 3
  }' | jq '{answer, sources: [.results[] | {title, url}]}'
```

### Monitor News
```bash
curl -s -X POST "https://api.tavily.com/search" \
  -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "San Diego Volleyball Club SDVBC",
    "topic": "news",
    "time_range": "week",
    "max_results": 5
  }' | jq '.results[] | {title, url, content}'
```

## Credits

- Search basic: 1 credit
- Search advanced: 2 credits
- Extract basic: 1 credit per URL
- Extract advanced: 2 credits per URL

## When to Use

| Task | Tool |
|------|------|
| Quick web lookup | Tavily Search with `include_answer` |
| Current events | Tavily Search with `topic: "news"` |
| Stock/market info | Tavily Search with `topic: "finance"` |
| Read/summarize a known URL | Tavily Extract |
| Research multiple sources | Tavily Search → Extract top results |
| Get raw HTML source of a URL | `web_fetch` (built-in) |

## Response Format

Always present results cleanly:
- Show the answer first (if available)
- List sources with titles and URLs
- Summarize key content for the user
