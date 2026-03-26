#!/usr/bin/env python3
"""
Demeterics — LLM reverse proxy helper.

Route any paid LLM call through Demeterics for cost tracking and observability.
Uses the unified chat endpoint so any provider works with one API key.

Usage:
  python3 demeterics.py chat --model openai/gpt-4o --prompt "Hello"
  python3 demeterics.py chat --model anthropic/claude-haiku-4-5-20251001 --prompt "Summarize this" --system "You are concise."
  python3 demeterics.py chat --model google/gemini-2.5-flash --prompt "Hello" --app Clawd.bot --flow my-feature
  python3 demeterics.py models
  python3 demeterics.py status

Env vars:
  DEMETERICS_API_KEY  (required) — API key starting with dmt_
"""

import argparse, json, os, sys, urllib.request, urllib.error

BASE_URL = "https://api.demeterics.com"


def get_api_key():
    key = os.environ.get("DEMETERICS_API_KEY", "")
    if not key:
        print(json.dumps({"error": "DEMETERICS_API_KEY not set"}))
        sys.exit(1)
    return key


def api_call(method, path, payload=None):
    """Make an API call to Demeterics."""
    key = get_api_key()
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        try:
            err = json.loads(body)
        except json.JSONDecodeError:
            err = {"error": body or str(e)}
        print(json.dumps({"error": err, "status": e.code}))
        sys.exit(1)


def inject_tags(text, app, flow, extra_tags=None):
    """Prepend /// instrumentation tags to a prompt string."""
    lines = []
    if app:
        lines.append(f"/// APP {app}")
    if flow:
        lines.append(f"/// FLOW {flow}")
    if extra_tags:
        for k, v in extra_tags.items():
            lines.append(f"/// {k.upper()} {v}")
    if lines:
        return "\n".join(lines) + "\n" + text
    return text


def cmd_chat(args):
    messages = []

    system_text = args.system or ""
    system_text = inject_tags(system_text, args.app, args.flow)
    if system_text.strip():
        messages.append({"role": "system", "content": system_text})

    # Read prompt from --prompt or stdin
    prompt = args.prompt
    if not prompt and not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    if not prompt:
        print(json.dumps({"error": "No prompt provided. Use --prompt or pipe via stdin."}))
        sys.exit(1)

    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": args.model,
        "messages": messages,
        "max_tokens": args.max_tokens,
    }
    if args.temperature is not None:
        payload["temperature"] = args.temperature
    if args.json_mode:
        payload["response_format"] = {"type": "json_object"}

    result = api_call("POST", "/chat/v1/chat/completions", payload)

    if args.raw:
        print(json.dumps(result, indent=2))
    else:
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = result.get("usage", {})
        output = {
            "content": content,
            "model": result.get("model", args.model),
            "tokens": {
                "prompt": usage.get("prompt_tokens", 0),
                "completion": usage.get("completion_tokens", 0),
                "total": usage.get("total_tokens", 0),
            }
        }
        print(json.dumps(output, indent=2))


def cmd_models(args):
    result = api_call("GET", "/chat/v1/models")
    models = result.get("data", [])
    if args.provider:
        models = [m for m in models if m.get("id", "").startswith(args.provider + "/")]
    output = [{"id": m.get("id"), "owned_by": m.get("owned_by", "")} for m in models]
    print(json.dumps(output, indent=2))


def cmd_status(args):
    result = api_call("GET", "/api/v1/status")
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Demeterics LLM reverse proxy")
    sub = parser.add_subparsers(dest="command", required=True)

    # chat
    p_chat = sub.add_parser("chat", help="Send a chat completion request")
    p_chat.add_argument("--model", required=True, help="Model in provider/name format (e.g. openai/gpt-4o)")
    p_chat.add_argument("--prompt", help="User prompt (or pipe via stdin)")
    p_chat.add_argument("--system", default="", help="System prompt")
    p_chat.add_argument("--max-tokens", type=int, default=1024, help="Max response tokens")
    p_chat.add_argument("--temperature", type=float, default=None, help="Temperature (0-2)")
    p_chat.add_argument("--app", default="Clawd.bot", help="App tag for analytics (default: Clawd.bot)")
    p_chat.add_argument("--flow", default="", help="Flow tag for analytics")
    p_chat.add_argument("--json-mode", action="store_true", help="Request JSON output format")
    p_chat.add_argument("--raw", action="store_true", help="Print raw API response")
    p_chat.set_defaults(func=cmd_chat)

    # models
    p_models = sub.add_parser("models", help="List available models")
    p_models.add_argument("--provider", help="Filter by provider (openai, anthropic, google, groq)")
    p_models.set_defaults(func=cmd_models)

    # status
    p_status = sub.add_parser("status", help="Check API key and service status")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
