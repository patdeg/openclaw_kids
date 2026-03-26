# Demeterics — LLM Reverse Proxy

## What It Is

[Demeterics](https://demeterics.ai) is an observability proxy that sits between your code and LLM providers. It logs every interaction (prompts, responses, tokens, costs, latency) and routes them to the right provider — all through a single API key.

**When to use it:** Any time you write a script or flow that needs to call a paid LLM API (image generation, voice synthesis, council/multi-model, knowledge base, etc.). The main OpenClaw subscription handles normal chat — Demeterics handles everything else.

**App name:** `Clawd.bot` (already configured in the Demeterics dashboard).

## Credentials

| Env Var | Required | Description |
|---------|----------|-------------|
| `DEMETERICS_API_KEY` | Yes | API key (starts with `dmt_`). This is the ONLY key you need — vendor keys are managed on the Demeterics side. |

## Base URL

```
https://api.demeterics.com
```

## How It Works

Instead of calling provider APIs directly, call Demeterics. It proxies to the real provider, logs everything, and bills through managed credits.

### Unified Endpoint (Recommended)

Works with any provider through a single endpoint. Model format: `provider/model-name`.

```bash
curl -s https://api.demeterics.com/chat/v1/chat/completions \
  -H "Authorization: Bearer $DEMETERICS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-4o",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Provider-Specific Endpoints

Use these when you need native API format (e.g., Anthropic Messages API):

| Provider | Base URL |
|----------|----------|
| OpenAI | `https://api.demeterics.com/openai/v1` |
| Anthropic | `https://api.demeterics.com/anthropic/v1` |
| Google | `https://api.demeterics.com/google/v1` |
| Groq | `https://api.demeterics.com/groq/v1` |
| Grok | `https://api.demeterics.com/grok/v1` |
| OpenRouter | `https://api.demeterics.com/openrouter/v1` |

### Available Models

```bash
curl -s https://api.demeterics.com/chat/v1/models \
  -H "Authorization: Bearer $DEMETERICS_API_KEY" | python3 -m json.tool
```

## Prompt Instrumentation (`///` Tags)

Demeterics strips lines starting with `///` before sending to the LLM — zero token cost. Use them to tag interactions for analytics.

### Format

```
/// APP Clawd.bot
/// FLOW school-brief
/// VERSION 1.0
/// PRIORITY medium

Your actual prompt here...
```

### Supported Tags

| Tag | Purpose | Example |
|-----|---------|---------|
| `APP` | Application name | `Clawd.bot` |
| `FLOW` | Feature/workflow | `school-brief`, `image-gen`, `voice-call` |
| `PRODUCT` | Product line | `alfred` |
| `USER` | User identifier | `kid1` |
| `SESSION` | Session ID | `heartbeat-2026-02-21` |
| `VERSION` | Prompt version | `1.0` |
| `VARIANT` | A/B test variant | `control`, `v2` |
| `ENVIRONMENT` | Deployment env | `production`, `dev` |
| `PRIORITY` | Importance | `low`, `medium`, `high`, `critical` |
| `TAGS` | Free-form tags | `school,email,daily` |

### Always Tag Your Calls

Every call through Demeterics should have at minimum:

```
/// APP Clawd.bot
/// FLOW <what-this-does>
```

This is how we track costs by feature on the Demeterics dashboard.

## Python Usage

### Using OpenAI SDK (works for any provider via unified endpoint)

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DEMETERICS_API_KEY"],
    base_url="https://api.demeterics.com/chat/v1"
)

response = client.chat.completions.create(
    model="openai/gpt-4o",
    messages=[
        {"role": "system", "content": "/// APP Clawd.bot\n/// FLOW my-feature\nYou are a helpful assistant."},
        {"role": "user", "content": "Hello"}
    ]
)
print(response.choices[0].message.content)
```

### Using urllib (no dependencies)

```python
import json, os, urllib.request

def demeterics_call(model, messages, max_tokens=1024):
    """Call any LLM through Demeterics. Model format: provider/model-name."""
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens
    }).encode()
    req = urllib.request.Request(
        "https://api.demeterics.com/chat/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {os.environ['DEMETERICS_API_KEY']}",
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
```

### Anthropic Native Format (Messages API)

```python
payload = json.dumps({
    "model": "claude-haiku-4-5-20251001",
    "max_tokens": 800,
    "system": "/// APP Clawd.bot\n/// FLOW my-feature\nSystem prompt here.",
    "messages": [{"role": "user", "content": "Hello"}]
}).encode()
req = urllib.request.Request(
    "https://api.demeterics.com/anthropic/v1/messages",
    data=payload,
    headers={
        "Authorization": f"Bearer {os.environ['DEMETERICS_API_KEY']}",
        "Content-Type": "application/json"
    }
)
```

## When to Use Demeterics vs. Direct Provider

| Scenario | Use |
|----------|-----|
| Normal chat with Dad via WhatsApp | OpenClaw subscription (direct Anthropic) |
| Script that calls GPT-4o for image analysis | **Demeterics** |
| Script that calls Claude for summarization | **Demeterics** |
| Voice generation (ElevenLabs via proxy) | **Demeterics** (when available) |
| Any `python3` script you write that needs an LLM | **Demeterics** |
| Multi-model council (ask 3 models, pick best) | **Demeterics** unified endpoint |

**Rule of thumb:** If it's OpenClaw's own brain talking, use the subscription. If it's a script/tool/flow calling out to an LLM, route through Demeterics.

## Streaming

Add `"stream": true` to any request. Works with all providers.

## Error Handling

| Status | Meaning |
|--------|---------|
| 401 | Bad or missing DEMETERICS_API_KEY |
| 402 | Insufficient credits — check dashboard |
| 429 | Rate limited — back off and retry |
| 404 | Model not found — check `/models` endpoint |

## Dashboard

View costs, interactions, and analytics at [demeterics.ai](https://demeterics.ai).
