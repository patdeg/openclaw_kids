#!/usr/bin/env python3
"""
patch-openclaw-pi-ai.py — applied during Dockerfile.openclaw build

Fixes an OpenClaw 2026.4.15 + Demeterics-OpenAI interaction bug where tool-call
responses get silently dropped:

  1. OpenClaw (via pi-ai) calls Demeterics' /openai/v1/chat/completions with
     stream:true.
  2. Demeterics returns Content-Type: application/json (not text/event-stream).
  3. The OpenAI Node SDK's SSE iterator yields ZERO chunks on this non-SSE body.
  4. pi-ai's streamOpenAICompletions gets no chunks, so output.content stays
     empty, stopReason resets from "toolUse" to "stop", and OpenClaw reports
     `incomplete turn detected: stopReason=stop payloads=0` → "Agent couldn't
     generate a response".

The patch does two things to pi-ai's providers/openai-completions.js:

  (A) Forces non-streaming for the outbound call (params.stream = false) and
      wraps the resulting ChatCompletion in a one-element async iterable, with
      choice.delta synthesized from choice.message. This gives the existing
      parser a chunk to iterate over.

  (B) A safety net inside the parser: if a chunk arrives with choice.message
      but no choice.delta (e.g. from other OpenAI-compatible proxies that do
      the same thing), synthesize a delta so content + tool_calls are parsed.

Idempotent — safe to re-run; checks for the PATCH markers first.
"""
import sys
import os

TARGETS = [
    "/usr/local/lib/node_modules/openclaw/node_modules/@mariozechner/pi-ai/dist/providers/openai-completions.js",
]

# ---------------------------------------------------------------------------
# Patch A: force non-streaming + synthesize a chunk
# ---------------------------------------------------------------------------
PATCH_A_OLD = "            const openaiStream = await client.chat.completions.create(params, { signal: options?.signal });"
PATCH_A_NEW = """            // PATCH2(pdeglon 2026-04-18): Demeterics /chat/completions returns
            // application/json, not text/event-stream, so stream:true yields 0 chunks.
            // Force non-streaming and synthesize a one-element async iterable whose
            // choice.delta is built from choice.message. Existing parser handles it.
            params.stream = false;
            delete params.stream_options;
            const _nsResp = await client.chat.completions.create(params, { signal: options?.signal });
            async function* _synthChunks(r) {
                if (!r?.choices) return;
                for (const c of r.choices) {
                    yield {
                        id: r.id, object: r.object, model: r.model, created: r.created, usage: r.usage,
                        choices: [{
                            index: c.index,
                            delta: c.message ? {
                                role: c.message.role,
                                content: c.message.content ?? undefined,
                                tool_calls: c.message.tool_calls,
                                reasoning_content: c.message.reasoning_content,
                                reasoning: c.message.reasoning,
                                reasoning_details: c.message.reasoning_details,
                                reasoning_text: c.message.reasoning_text,
                            } : c.delta,
                            finish_reason: c.finish_reason,
                        }],
                    };
                }
            }
            const openaiStream = _synthChunks(_nsResp);"""

# ---------------------------------------------------------------------------
# Patch B: parser safety net — message→delta synthesis
# ---------------------------------------------------------------------------
PATCH_B_OLD = """                if (choice.finish_reason) {
                    const finishReasonResult = mapStopReason(choice.finish_reason);
                    output.stopReason = finishReasonResult.stopReason;
                    if (finishReasonResult.errorMessage) {
                        output.errorMessage = finishReasonResult.errorMessage;
                    }
                }
                if (choice.delta) {"""
PATCH_B_NEW = """                if (choice.finish_reason) {
                    const finishReasonResult = mapStopReason(choice.finish_reason);
                    output.stopReason = finishReasonResult.stopReason;
                    if (finishReasonResult.errorMessage) {
                        output.errorMessage = finishReasonResult.errorMessage;
                    }
                }
                // PATCH(pdeglon 2026-04-18): non-streaming proxies (e.g. Demeterics) return
                // choice.message instead of choice.delta. Synthesize a delta so the existing
                // logic processes content + tool_calls.
                if (!choice.delta && choice.message) {
                    choice.delta = {
                        content: choice.message.content ?? undefined,
                        tool_calls: choice.message.tool_calls,
                        reasoning_content: choice.message.reasoning_content,
                        reasoning: choice.message.reasoning,
                        reasoning_text: choice.message.reasoning_text,
                        reasoning_details: choice.message.reasoning_details,
                    };
                }
                if (choice.delta) {"""


def apply(path):
    if not os.path.exists(path):
        print(f"SKIP: {path} does not exist", file=sys.stderr)
        return False
    s = open(path).read()
    changed = False

    if "PATCH2(pdeglon 2026-04-18)" in s:
        print(f"  PATCH2 already applied in {path}")
    else:
        if s.count(PATCH_A_OLD) != 1:
            print(f"ERROR: PATCH2 anchor not found (or found more than once) in {path}", file=sys.stderr)
            sys.exit(1)
        s = s.replace(PATCH_A_OLD, PATCH_A_NEW)
        changed = True
        print(f"  PATCH2 applied in {path}")

    if "PATCH(pdeglon 2026-04-18)" in s and "PATCH(pdeglon 2026-04-18): non-streaming proxies" in s:
        print(f"  PATCH already applied in {path}")
    else:
        if s.count(PATCH_B_OLD) != 1:
            print(f"ERROR: PATCH anchor not found (or found more than once) in {path}", file=sys.stderr)
            sys.exit(1)
        s = s.replace(PATCH_B_OLD, PATCH_B_NEW)
        changed = True
        print(f"  PATCH applied in {path}")

    if changed:
        open(path, "w").write(s)
    return True


def main():
    any_hit = False
    for t in TARGETS:
        if apply(t):
            any_hit = True
    if not any_hit:
        print("ERROR: no target files found — pi-ai layout may have changed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
