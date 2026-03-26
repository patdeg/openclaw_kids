# Groq Compound - Agentic AI with Built-in Tools

Use Groq's Compound system for tasks requiring web search, browser automation, code execution, or computational knowledge - all in a single API call.

## Overview

Groq Compound combines GPT-OSS 120B and Llama 4 models with integrated tools:
- **Web Search** - Real-time internet access
- **Visit Website** - Fetch and analyze web content
- **Browser Automation** - Control web interactions
- **Code Execution** - Run Python code (via E2B)
- **Wolfram Alpha** - Computational knowledge

## When to Use

Use Groq Compound when the task benefits from:
- Current/real-time information (news, prices, weather)
- Web research requiring multiple sources
- Calculations or data analysis
- Tasks that need both search AND computation

**Do NOT use for:**
- Simple conversations (use Claude directly)
- Local file operations
- Private/internal network access
- Tasks requiring custom tools

## Credentials

Environment variable: `GROQ_API_KEY`

Or via Demeterics proxy: `DEMETERICS_API_KEY`

## API Usage

### Direct Groq API

```bash
curl -s https://api.groq.com/openai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -d '{
    "model": "groq/compound",
    "messages": [{"role": "user", "content": "YOUR_QUERY_HERE"}]
  }' | jq -r '.choices[0].message.content'
```

### Via Demeterics Proxy

```bash
curl -s https://api.demeterics.com/groq/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEMETERICS_API_KEY" \
  -d '{
    "model": "groq/compound",
    "messages": [{"role": "user", "content": "YOUR_QUERY_HERE"}]
  }' | jq -r '.choices[0].message.content'
```

## Models

| Model | Latency | Tool Calls | Best For |
|-------|---------|------------|----------|
| `groq/compound` | Standard | Multiple | Complex research |
| `groq/compound-mini` | 3x faster | Single | Quick lookups |

## Restricting Tools

To limit which tools Compound can use:

```json
{
  "model": "groq/compound",
  "messages": [...],
  "compound_custom": {
    "tools": {
      "enabled_tools": ["web_search", "code_execution"]
    }
  }
}
```

Available tools: `web_search`, `visit_website`, `code_execution`, `browser_automation`, `wolfram_alpha`

## Example Queries

### Web Research
```bash
curl -s https://api.groq.com/openai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -d '{
    "model": "groq/compound",
    "messages": [{"role": "user", "content": "What are the latest volleyball tournament results for SDVBC 14U teams?"}]
  }' | jq -r '.choices[0].message.content'
```

### Code + Calculation
```bash
curl -s https://api.groq.com/openai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -d '{
    "model": "groq/compound-mini",
    "messages": [{"role": "user", "content": "Calculate the compound interest on $10000 at 5% for 10 years"}]
  }' | jq -r '.choices[0].message.content'
```

### Weather/Current Events
```bash
curl -s https://api.groq.com/openai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -d '{
    "model": "groq/compound-mini",
    "messages": [{"role": "user", "content": "What is the current weather in San Diego?"}]
  }' | jq -r '.choices[0].message.content'
```

## Viewing Executed Tools

The response includes `executed_tools` showing which tools were used:

```bash
curl -s ... | jq '.executed_tools'
```

## Response Format

Always extract the content and present it cleanly to the user. Do not show raw JSON unless debugging.

## When NOT to Use Groq Compound

- **Live price checking, booking sites, hotel/flight research** → Use the built-in `browser` tool instead (local Chromium, faster, more reliable)
- **Simple web search** → Use Tavily instead (dedicated search API)
- **Reading a known URL** → Use Tavily Extract or `web_fetch` instead
- **Anything requiring local network access** → Use the built-in `browser` (Groq runs remotely)

Groq Compound is best for: complex multi-step research tasks that need BOTH web search AND computation in a single call.

## Cost Considerations

- Groq Compound uses multiple models internally
- Web search and code execution add latency
- Use `compound-mini` for simple lookups to reduce cost/latency
- Prefer the built-in `browser` tool for private/frequent tasks (runs locally, free, full Chromium)
